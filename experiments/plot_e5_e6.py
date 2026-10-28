"""Vẽ kết quả E5/E6 hiện có bằng khuôn chung UNMASK.

E5 hiện tại: so sánh điểm hoạt động, không phải đường quét ngưỡng.
E6 hiện tại: so sánh theo tỉ lệ pack, không phải phân tích theo packer.

Chạy:
    python -m experiments.plot_e5_e6 --results results --out figs

Không thay đổi dataset, config, ngưỡng hoặc CSV đầu vào.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from .plot_style import (
        apply_style,
        save_figure,
        GATE_ORDER,
        GATE_LABELS,
        GATE_COLOR,
        GATE_MARKER,
    )
except ImportError:
    from plot_style import (
        apply_style,
        save_figure,
        GATE_ORDER,
        GATE_LABELS,
        GATE_COLOR,
        GATE_MARKER,
    )

apply_style()


def load_exp(results_dir: Path, exp: str) -> pd.DataFrame:
    files = sorted(results_dir.glob(f"results_{exp}_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"Không tìm thấy results_{exp}_*.csv trong {results_dir}"
        )

    frames = []
    required = [
        "gate",
        "seed",
        "pack_ratio_set",
        "pack_ratio_real",
        "FTR",
        "FNR_G2",
        "FNR_G3",
    ]
    if exp == "e6":
        required.append("correct_filter_Punseen")

    for path in files:
        frame = pd.read_csv(path)
        missing = [col for col in required if col not in frame.columns]
        if missing:
            raise ValueError(f"{path.name}: thiếu cột {missing}")
        if frame.empty:
            raise ValueError(f"{path.name}: không có dữ liệu")
        if "exp" in frame.columns and not frame["exp"].eq(exp).all():
            raise ValueError(f"{path.name}: có dòng không thuộc {exp}")

        frame["source_file"] = path.name
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)

    if not df["gate"].isin(GATE_ORDER).all():
        raise ValueError(f"{exp}: có gate không hợp lệ")

    numeric_cols = [col for col in required if col != "gate"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if not np.isfinite(df[col].to_numpy(dtype=float)).all():
            raise ValueError(
                f"{exp}/{col}: có giá trị thiếu hoặc không hữu hạn; "
                "cần làm rõ số liệu, không thay bằng 0"
            )

    for col in numeric_cols:
        if col != "seed" and not df[col].between(0, 1).all():
            raise ValueError(f"{exp}/{col}: phải nằm trong khoảng 0–1")

    if not df["seed"].mod(1).eq(0).all():
        raise ValueError(f"{exp}: seed phải là số nguyên")

    keys = ["gate", "seed", "pack_ratio_set"]
    if df.duplicated(keys).any():
        raise ValueError(
            f"{exp}: trùng gate/seed/tỉ lệ đặt. "
            "Script này chỉ đọc điểm hoạt động, chưa đọc sweep ngưỡng."
        )

    reference_seeds = None
    for key, block in df.groupby(["pack_ratio_set", "seed"]):
        if set(block["gate"]) != set(GATE_ORDER):
            raise ValueError(f"{exp}/{key}: chưa đủ 5 gate")
        if block["pack_ratio_real"].nunique() != 1:
            raise ValueError(
                f"{exp}/{key}: tỉ lệ pack thực tế khác nhau giữa các gate"
            )

    for ratio, block in df.groupby("pack_ratio_set"):
        seeds = set(block["seed"])
        if reference_seeds is None:
            reference_seeds = seeds
        elif seeds != reference_seeds:
            raise ValueError(
                f"{exp}/{ratio}: tập seed không khớp các tỉ lệ khác"
            )

    return df


def actual_ratio_text(block: pd.DataFrame) -> str:
    low = float(block["pack_ratio_real"].min())
    high = float(block["pack_ratio_real"].max())
    if np.isclose(low, high):
        return f"{low:.1%}"
    return f"{low:.1%}–{high:.1%}"


def gate_summary(block: pd.DataFrame) -> pd.DataFrame:
    return (
        block.groupby("gate")
        .agg(
            FTR_mean=("FTR", "mean"),
            FTR_std=("FTR", lambda x: x.std(ddof=0)),
            FNR_G2_mean=("FNR_G2", "mean"),
            FNR_G2_std=("FNR_G2", lambda x: x.std(ddof=0)),
            FNR_G3_mean=("FNR_G3", "mean"),
            FNR_G3_std=("FNR_G3", lambda x: x.std(ddof=0)),
        )
        .reindex(GATE_ORDER)
    )


def plot_e5_operating_points(df: pd.DataFrame, out_dir: Path):
    """Vẽ điểm hoạt động từng gate, tách riêng theo tỉ lệ pack."""
    outputs = []
    ratios = sorted(df["pack_ratio_set"].unique())

    # Vị trí nhãn theo tọa độ tương đối trong mỗi panel.
    # Đường dẫn nối nhãn với điểm dữ liệu thực tế.
    label_positions = {
        "G2": {
            "F0": (0.42, 0.10),
            "F1": (0.06, 0.35),
            "F2": (0.42, 0.43),
            "F3a": (0.42, 0.32),
            "F3": (0.42, 0.21),
        },
        "G3": {
            "F0": (0.42, 0.10),
            "F1": (0.14, 0.90),
            "F2": (0.42, 0.62),
            "F3a": (0.42, 0.51),
            "F3": (0.42, 0.40),
        },
    }

    for group in ["G2", "G3"]:
        fig, axes = plt.subplots(
            1,
            len(ratios),
            figsize=(5 * len(ratios), 5.5),
            squeeze=False,
            sharex=True,
            sharey=True,
        )

        for ax, ratio in zip(axes[0], ratios):
            block = df.loc[df["pack_ratio_set"].eq(ratio)]
            summary = gate_summary(block)

            for gate in GATE_ORDER:
                row = summary.loc[gate]
                x = float(row["FTR_mean"]) * 100
                y = float(row[f"FNR_{group}_mean"]) * 100

                ax.errorbar(
                    x,
                    y,
                    xerr=float(row["FTR_std"]) * 100,
                    yerr=float(row[f"FNR_{group}_std"]) * 100,
                    fmt=GATE_MARKER[gate],
                    color=GATE_COLOR[gate],
                    markersize=11 if gate == "F3" else 7,
                    linewidth=1.3,
                    capsize=3,
                    label=GATE_LABELS[gate],
                    zorder=3,
                )

                ax.annotate(
                    gate,
                    xy=(x, y),
                    xycoords="data",
                    xytext=label_positions[group][gate],
                    textcoords="axes fraction",
                    ha="left",
                    va="center",
                    fontsize=10,
                    color="#222222",
                    bbox={
                        "boxstyle": "round,pad=0.2",
                        "facecolor": "white",
                        "edgecolor": "none",
                        "alpha": 0.95,
                    },
                    arrowprops={
                        "arrowstyle": "-",
                        "color": "#777777",
                        "linewidth": 0.8,
                    },
                    zorder=4,
                )

            ax.set_title(
                f"Target pack: {ratio:.0%}\n"
                f"Actual pack: {actual_ratio_text(block)}"
            )
            ax.set_xlabel("FTR (%)")
            ax.set_xlim(-5, 105)
            ax.set_ylim(-5, 105)
            ax.grid(linestyle="--")

        axes[0, 0].set_ylabel(f"Filter FNR {group} (%)")

        handles, labels = axes[0, 0].get_legend_handles_labels()
        fig.legend(
            handles,
            labels,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.09),
            ncol=len(GATE_ORDER),
        )

        fig.suptitle(
            f"E5 — Gate operating points: FTR / filter FNR {group}"
        )
        fig.text(
            0.5,
            0.025,
            "Existing CSV results; no threshold sweep. "
            "Points: mean across seeds; error bars: population SD, not CI.\n"
            "These figures do not establish end-to-end FNR.",
            ha="center",
            fontsize=9,
        )
        fig.tight_layout(rect=(0, 0.19, 1, 0.91))

        path = out_dir / f"e5_operating_points_{group.lower()}.png"
        save_figure(fig, path)
        plt.close(fig)

        outputs.append(path)
        print(f"[E5] Đã lưu: {path}")

    return outputs


def plot_e6_by_pack_ratio(df: pd.DataFrame, out_dir: Path):
    """Màu biểu diễn gate; mỗi panel là một tỉ lệ pack."""
    ratios = sorted(df["pack_ratio_set"].unique())
    summary = (
        df.groupby(["pack_ratio_set", "gate"])
        .agg(
            correct_mean=("correct_filter_Punseen", "mean"),
            correct_std=(
                "correct_filter_Punseen",
                lambda x: x.std(ddof=0),
            ),
            seed_count=("seed", "nunique"),
            pack_real_min=("pack_ratio_real", "min"),
            pack_real_max=("pack_ratio_real", "max"),
        )
        .reset_index()
    )

    fig, axes = plt.subplots(
        1,
        len(ratios),
        figsize=(5 * len(ratios), 5),
        squeeze=False,
        sharey=True,
    )

    for ax, ratio in zip(axes[0], ratios):
        block = df.loc[df["pack_ratio_set"].eq(ratio)]
        rows = (
            summary.loc[summary["pack_ratio_set"].eq(ratio)]
            .set_index("gate")
            .reindex(GATE_ORDER)
        )

        values = rows["correct_mean"].to_numpy() * 100
        errors = rows["correct_std"].to_numpy() * 100
        bars = ax.bar(
            GATE_ORDER,
            values,
            color=[GATE_COLOR[gate] for gate in GATE_ORDER],
            yerr=errors,
            capsize=3,
            error_kw={"ecolor": "#444444", "linewidth": 1},
        )

        for bar, value, error in zip(bars, values, errors):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + error + 2,
                f"{value:.1f}%",
                ha="center",
                fontsize=9,
            )

        ax.set_title(
            f"Target pack: {ratio:.0%}\n"
            f"Actual pack: {actual_ratio_text(block)}"
        )
        ax.set_xlabel("Gate")
        ax.set_ylim(0, 115)
        ax.grid(axis="y", linestyle="--")

    axes[0, 0].set_ylabel("Correct filtering of G1 P-unseen (%)")
    fig.suptitle("E6 — P-unseen correct filtering by pack ratio")
    fig.text(
        0.5,
        0.025,
        "Existing CSV results grouped by pack ratio, not by packer.\n"
        "Bars: mean across seeds; error bars: population SD, not Wilson CI.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.13, 1, 0.90))

    path = out_dir / "e6_by_pack_ratio_correct_punseen.png"
    save_figure(fig, path)
    plt.close(fig)

    table_path = out_dir / "e6_by_pack_ratio_plot_summary.csv"
    summary.to_csv(table_path, index=False)

    print(f"[E6] Đã lưu: {path}")
    print(f"[E6] Đã lưu: {table_path}")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--out", type=Path, default=Path("figs"))
    args = parser.parse_args()

    # Đọc và kiểm tra cả hai đầu vào trước khi xuất hình.
    e5 = load_exp(args.results, "e5")
    e6 = load_exp(args.results, "e6")
    args.out.mkdir(parents=True, exist_ok=True)

    plot_e5_operating_points(e5, args.out)
    plot_e6_by_pack_ratio(e6, args.out)
    print("Hoàn tất xuất hình nền trắng, 300 dpi.")


if __name__ == "__main__":
    main()