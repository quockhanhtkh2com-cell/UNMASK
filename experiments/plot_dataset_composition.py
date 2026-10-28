"""Vẽ thành phần dataset theo nhóm và split — [Trúc].

Chạy từ thư mục gốc repo:
    python -m experiments.plot_dataset_composition
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

try:
    from .plot_style import apply_style, save_figure
except ImportError:
    from plot_style import apply_style, save_figure


ROOT = Path(__file__).resolve().parents[1]

GROUPS = ["G0", "G1", "G2", "G3"]
SPLITS = ["train", "val", "test"]

SPLIT_COLORS = {
    "train": "#4c78a8",
    "val": "#f2a541",
    "test": "#59a14f",
}


def plot(dataset: Path, output: Path) -> None:
    df = pd.read_csv(
        dataset,
        dtype={"sha256": str, "origin_sha256": str},
    )

    required = {"sha256", "origin_sha256", "group", "split"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset thiếu cột: {sorted(missing)}")
    if df.empty:
        raise ValueError("Dataset không có mẫu.")
    if df[list(required)].isna().any().any():
        raise ValueError("Có giá trị thiếu trong các cột bắt buộc.")
    if df["sha256"].duplicated().any():
        raise ValueError("Dataset có sha256 trùng.")
    if not df["group"].isin(GROUPS).all():
        raise ValueError("group không hợp lệ.")
    if not df["split"].isin(SPLITS).all():
        raise ValueError("split không hợp lệ.")
    if (df.groupby("origin_sha256")["split"].nunique() > 1).any():
        raise ValueError("Có origin nằm ở nhiều split.")

    counts = pd.crosstab(df["group"], df["split"]).reindex(
        index=GROUPS,
        columns=SPLITS,
        fill_value=0,
    )
    group_totals = counts.sum(axis=1)
    split_totals = counts.sum(axis=0)

    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))

    counts.plot.bar(
        stacked=True,
        ax=axes[0],
        color=[SPLIT_COLORS[s] for s in SPLITS],
        rot=0,
        width=0.65,
    )

    for container in axes[0].containers:
        axes[0].bar_label(
            container,
            labels=[
                str(int(value)) if value > 0 else ""
                for value in container.datavalues
            ],
            label_type="center",
            fontsize=10,
            color="black",
        )

    for index, total in enumerate(group_totals):
        axes[0].annotate(
            f"n={int(total)}",
            xy=(index, total),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            fontweight="bold",
        )

    axes[0].set_title("Samples by ground-truth group")
    axes[0].set_xlabel("Group")
    axes[0].set_ylabel("Number of samples")
    axes[0].set_ylim(0, max(group_totals) * 1.20)
    axes[0].legend(title="Split")
    axes[0].yaxis.set_major_locator(MaxNLocator(integer=True))
    axes[0].set_axisbelow(True)
    axes[0].grid(axis="y")

    bars = axes[1].bar(
        SPLITS,
        split_totals.to_numpy(),
        color=[SPLIT_COLORS[s] for s in SPLITS],
        width=0.6,
    )
    axes[1].bar_label(
        bars,
        labels=[
            f"{int(n)} ({n / len(df):.1%})"
            for n in split_totals
        ],
        padding=5,
        fontsize=10,
    )
    axes[1].set_title("Samples by split")
    axes[1].set_xlabel("Split")
    axes[1].set_ylabel("Number of samples")
    axes[1].set_ylim(0, max(split_totals) * 1.20)
    axes[1].yaxis.set_major_locator(MaxNLocator(integer=True))
    axes[1].set_axisbelow(True)
    axes[1].grid(axis="y")

    fig.suptitle(
        f"UNMASK — Dataset composition ({len(df)} samples)",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.025,
        f"Source: {dataset.name} | "
        "Split by origin_sha256; no origin shared across splits.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))

    save_figure(fig, output)
    plt.close(fig)

    print(counts.to_string())
    print(f"\nGroup totals: {group_totals.to_dict()}")
    print(f"Split totals: {split_totals.to_dict()}")
    print(f"Total: {len(df)}")
    print(f"Đã lưu: {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "dataset_v1.1.csv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "figs" / "fig_dataset_composition.png",
    )
    args = parser.parse_args()
    plot(args.dataset, args.out)


if __name__ == "__main__":
    main()