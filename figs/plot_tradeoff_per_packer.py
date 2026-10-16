"""Vẽ E5/E6 từ CSV đã xuất; không chạy thí nghiệm hoặc chọn ngưỡng."""
from pathlib import Path
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


GATES = ["F0", "F1", "F2", "F3", "F3a"]


def read_data(path, extra):
    df = pd.read_csv(path)
    required = [
        "gate", "seed", "pack_ratio_set", "pack_ratio_real",
        "FTR", "FNR_G2", "FNR_G3",
    ] + extra
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Thiếu cột: {missing}")
    if df.empty:
        raise ValueError("CSV không có dữ liệu.")
    if df[required].isna().any().any():
        raise ValueError("Các cột bắt buộc có giá trị trống.")
    if not df["gate"].isin(GATES).all():
        raise ValueError("Gate không hợp lệ.")

    numeric = [
        "seed", "pack_ratio_set", "pack_ratio_real",
        "FTR", "FNR_G2", "FNR_G3",
    ]
    if "threshold" in extra:
        numeric.append("threshold")

    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if not np.isfinite(df[col].to_numpy(dtype=float)).all():
            raise ValueError(f"{col}: có giá trị số không hợp lệ.")

    for col in ["pack_ratio_set", "pack_ratio_real",
                "FTR", "FNR_G2", "FNR_G3"]:
        if not df[col].between(0, 1).all():
            raise ValueError(f"{col}: phải nằm trong khoảng 0–1.")

    if not df["seed"].mod(1).eq(0).all():
        raise ValueError("seed phải là số nguyên.")
    return df


def ratio_text(df):
    low = df["pack_ratio_real"].min()
    high = df["pack_ratio_real"].max()
    return (
        f"{low:.1%}" if np.isclose(low, high)
        else f"{low:.1%}–{high:.1%}"
    )


def draw_tradeoff(df, out, label):
    keys = ["gate", "seed", "pack_ratio_set", "threshold"]
    if df.duplicated(keys).any():
        raise ValueError("E5 trùng gate/seed/tỉ lệ/ngưỡng.")

    # Chỉ nối điểm khi mỗi ngưỡng có cùng tập seed.
    for key, block in df.groupby(["pack_ratio_set", "gate"]):
        seeds = block.groupby("threshold")["seed"].apply(set)
        if len(seeds) < 2:
            raise ValueError(f"{key}: cần ít nhất hai ngưỡng.")
        if any(s != seeds.iloc[0] for s in seeds):
            raise ValueError(f"{key}: tập seed khác nhau giữa các ngưỡng.")

    for ratio, block in df.groupby("pack_ratio_set"):
        fig, axes = plt.subplots(1, 2, figsize=(11, 5))
        for ax, group in zip(axes, ["G2", "G3"]):
            for gate, part in block.groupby("gate"):
                means = part.groupby("threshold")[
                    ["FTR", f"FNR_{group}"]
                ].mean().sort_index()
                ax.plot(
                    means["FTR"] * 100,
                    means[f"FNR_{group}"] * 100,
                    marker="o", label=gate,
                )
            ax.set(
                xlabel="FTR (%)", ylabel=f"FNR {group} (%)",
                xlim=(-3, 103), ylim=(-3, 103),
                title=f"True drift: {group}",
            )
            ax.grid(alpha=0.25)
            ax.legend(title="Gate")
        fig.suptitle(
            f"FTR–FNR — {label}\n"
            f"Target pack {ratio:.1%}; actual {ratio_text(block)}"
        )
        fig.text(
            0.5, 0.02,
            "Mean across seeds at each threshold; "
            "points connected in threshold order. No confidence intervals.",
            ha="center", fontsize=9,
        )
        fig.tight_layout(rect=(0, 0.07, 1, 0.87))
        target = out / f"fig_ftr_fnr_draft_{ratio:.6f}.png"
        fig.savefig(target, dpi=200)
        plt.close(fig)
        print(f"Đã lưu: {target}")


def draw_packer(df, out, label):
    keys = ["gate", "seed", "pack_ratio_set", "packer"]
    if df.duplicated(keys).any():
        raise ValueError("E6 trùng gate/seed/tỉ lệ/packer.")
    if df["packer"].astype(str).str.strip().eq("").any():
        raise ValueError("packer không được để trống.")

    metrics = ["FTR", "FNR_G2", "FNR_G3"]
    for ratio, block in df.groupby("pack_ratio_set"):
        packers = sorted(block["packer"].unique())
        gates = [g for g in GATES if g in set(block["gate"])]
        expected = set(block["seed"])
        for packer in packers:
            for gate in gates:
                part = block[
                    block["packer"].eq(packer) & block["gate"].eq(gate)
                ]
                if set(part["seed"]) != expected:
                    raise ValueError(
                        f"{ratio}/{packer}/{gate}: thiếu seed hoặc gate."
                    )

        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        x = np.arange(len(packers))
        width = 0.8 / len(gates)

        for ax, metric in zip(axes, metrics):
            for i, gate in enumerate(gates):
                values = (
                    block.loc[block["gate"].eq(gate)]
                    .groupby("packer")[metric].mean()
                    .reindex(packers).to_numpy() * 100
                )
                ax.bar(
                    x + (i - (len(gates) - 1) / 2) * width,
                    values, width, label=gate,
                )
            ax.set_xticks(x)
            ax.set_xticklabels(packers, rotation=20)
            ax.set(title=metric, ylabel="Rate (%)", ylim=(0, 105))
            ax.grid(axis="y", alpha=0.25)
            ax.set_axisbelow(True)

        axes[-1].legend(title="Gate", loc="upper left",
                        bbox_to_anchor=(1.02, 1))
        fig.suptitle(
            f"Per-packer — {label}\n"
            f"Target pack {ratio:.1%}; actual range {ratio_text(block)}"
        )
        fig.text(
            0.5, 0.02,
            "Mean across seeds within each packer and gate. "
            "No confidence intervals.",
            ha="center", fontsize=9,
        )
        fig.tight_layout(rect=(0, 0.07, 1, 0.87))
        target = out / f"fig_per_packer_draft_{ratio:.6f}.png"
        fig.savefig(target, dpi=200)
        plt.close(fig)
        print(f"Đã lưu: {target}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["e5", "e6"], required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("figs"))
    parser.add_argument(
        "--label", default="DRAFT - result source not verified"
    )
    args = parser.parse_args()

    extra = ["threshold"] if args.kind == "e5" else ["packer"]
    df = read_data(args.input, extra)
    args.out.mkdir(parents=True, exist_ok=True)

    if args.kind == "e5":
        draw_tradeoff(df, args.out, args.label)
    else:
        draw_packer(df, args.out, args.label)


if __name__ == "__main__":
    main()
    