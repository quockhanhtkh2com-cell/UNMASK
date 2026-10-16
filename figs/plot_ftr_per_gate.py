"""Vẽ FTR theo cổng từ các CSV E2, không chạy lại thí nghiệm."""
from pathlib import Path
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
GATES = ["F0", "F1", "F2", "F3"]
COLORS = ["#757575", "#1976d2", "#f9a825", "#388e3c"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=ROOT / "results")
    parser.add_argument("--out", type=Path, default=ROOT / "figs")
    parser.add_argument(
        "--label",
        default="DRAFT - result source not verified",
    )
    args = parser.parse_args()

    files = sorted(args.results.glob("results_e2_*.csv"))
    if not files:
        raise ValueError("Không tìm thấy results_e2_*.csv.")

    frames = []
    required = [
        "exp", "gate", "seed",
        "pack_ratio_set", "pack_ratio_real", "FTR",
    ]

    for path in files:
        frame = pd.read_csv(path)
        missing = [col for col in required if col not in frame.columns]
        if missing:
            raise ValueError(f"{path.name}: thiếu cột {missing}.")
        if frame.empty:
            raise ValueError(f"{path.name}: file rỗng.")
        frame["source_file"] = path.name
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)

    if not df["exp"].eq("e2").all():
        raise ValueError("Có dòng không thuộc E2.")
    if not df["gate"].isin(GATES).all():
        raise ValueError("Có gate không hợp lệ.")

    for col in ["seed", "pack_ratio_set", "pack_ratio_real", "FTR"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if not np.isfinite(df[col].to_numpy(dtype=float)).all():
            raise ValueError(f"{col}: có giá trị thiếu hoặc không hữu hạn.")

    if not df["seed"].mod(1).eq(0).all():
        raise ValueError("seed phải là số nguyên.")

    for col in ["pack_ratio_set", "pack_ratio_real", "FTR"]:
        if not df[col].between(0, 1).all():
            raise ValueError(f"{col}: giá trị ngoài khoảng 0–1.")

    keys = ["pack_ratio_set", "seed", "gate"]
    if df.duplicated(keys).any():
        raise ValueError("Trùng dòng theo tỉ lệ đặt, seed và gate.")

    for key, block in df.groupby(["pack_ratio_set", "seed"]):
        if set(block["gate"]) != set(GATES):
            raise ValueError(f"{key}: không đủ bốn gate.")
        if block["pack_ratio_real"].nunique() != 1:
            raise ValueError(f"{key}: tỉ lệ pack thực tế khác nhau giữa gate.")

    seed_sets = df.groupby("pack_ratio_set")["seed"].apply(
        lambda values: set(values)
    )
    if any(values != seed_sets.iloc[0] for values in seed_sets):
        raise ValueError("Các tỉ lệ đặt không có cùng tập seed.")

    summary = df.groupby(
        ["pack_ratio_set", "gate"], as_index=False
    ).agg(
        ftr_mean=("FTR", "mean"),
        ftr_min=("FTR", "min"),
        ftr_max=("FTR", "max"),
        seed_count=("seed", "nunique"),
        pack_real_min=("pack_ratio_real", "min"),
        pack_real_max=("pack_ratio_real", "max"),
    )

    ratios = sorted(df["pack_ratio_set"].unique())
    fig, axes = plt.subplots(
        1, len(ratios),
        figsize=(5 * len(ratios), 5),
        sharey=True,
        squeeze=False,
    )

    for ax, ratio in zip(axes[0], ratios):
        block = summary.loc[
            summary["pack_ratio_set"].eq(ratio)
        ].set_index("gate").reindex(GATES)

        values = block["ftr_mean"].to_numpy() * 100
        errors = np.vstack([
            (block["ftr_mean"] - block["ftr_min"]).to_numpy(),
            (block["ftr_max"] - block["ftr_mean"]).to_numpy(),
        ]) * 100

        bars = ax.bar(
            GATES, values, color=COLORS,
            yerr=errors, capsize=4,
        )
        for bar, value, upper in zip(
            bars, values, block["ftr_max"].to_numpy() * 100
        ):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                upper + 3,
                f"{value:.1f}%",
                ha="center", fontsize=10,
            )

        lo = block["pack_real_min"].min() * 100
        hi = block["pack_real_max"].max() * 100
        actual = f"{lo:.1f}%" if np.isclose(lo, hi) else f"{lo:.1f}–{hi:.1f}%"
        seeds = int(block["seed_count"].iloc[0])

        ax.set_title(
            f"Target pack: {ratio:.0%}\n"
            f"Actual pack: {actual} | {seeds} seeds"
        )
        ax.set_ylim(0, 115)
        ax.set_xlabel("Gate")
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)

    axes[0, 0].set_ylabel("FTR (%)")
    fig.suptitle(f"FTR by gate — {args.label}", fontsize=13)
    fig.text(
        0.5, 0.02,
        "Bars: mean across seeds. Whiskers: min–max across seeds, "
        "not Wilson confidence intervals.",
        ha="center", fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.91))

    args.out.mkdir(parents=True, exist_ok=True)
    image_path = args.out / "fig_ftr_per_gate_draft.png"
    table_path = args.out / "ftr_per_gate_draft_summary.csv"
    fig.savefig(image_path, dpi=200)
    plt.close(fig)
    summary.to_csv(table_path, index=False)

    print(summary.to_string(index=False))
    print(f"Đã lưu: {image_path}")
    print(f"Đã lưu: {table_path}")


if __name__ == "__main__":
    main()