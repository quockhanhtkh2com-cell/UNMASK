"""Vẽ số cặp bất đồng trong kiểm định McNemar — [Trúc].

Chạy:
    python -m experiments.plot_mcnemar
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

try:
    from .plot_style import apply_style, save_figure, GATE_COLOR
except ImportError:
    from plot_style import apply_style, save_figure, GATE_COLOR


ROOT = Path(__file__).resolve().parents[1]
COMPARATORS = ["F1", "F2", "F3a"]


def plot(input_path, output):
    df = pd.read_csv(input_path)

    required = {"comparison", "b", "c", "p_value"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV thiếu cột: {sorted(missing)}")
    if df.empty:
        raise ValueError("CSV không có kết quả kiểm định.")
    if df[list(required)].isna().any().any():
        raise ValueError("CSV thiếu giá trị bắt buộc.")

    # Nhận tên như "F3 vs F1 (DiE)".
    parsed = df["comparison"].astype(str).str.extract(
        r"^\s*F3\s+vs\s+(F3a|F1|F2)(?=\s|\(|$)"
    )[0]

    if parsed.isna().any():
        raise ValueError(
            "Có comparison ngoài phạm vi F3 vs F1/F2/F3a."
        )
    df["comparator"] = parsed
    if df["comparator"].duplicated().any():
        raise ValueError("Có so sánh bị trùng.")
    if set(df["comparator"]) != set(COMPARATORS):
        raise ValueError("Cần đủ F3 vs F1, F2 và F3a.")

    for col in ["b", "c", "p_value"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if not np.isfinite(
        df[["b", "c", "p_value"]].to_numpy(dtype=float)
    ).all():
        raise ValueError("b, c hoặc p_value không hữu hạn.")

    counts = df[["b", "c"]].to_numpy(dtype=float)
    if (counts < 0).any() or (counts != np.floor(counts)).any():
        raise ValueError("b và c phải là số nguyên không âm.")
    if not df["p_value"].between(0, 1).all():
        raise ValueError("p_value phải nằm trong khoảng 0–1.")

    df = df.set_index("comparator").loc[COMPARATORS].reset_index()

    apply_style()
    fig, axes = plt.subplots(
        1, 3, figsize=(13, 5.8), sharey=True,
    )

    max_count = float(df[["b", "c"]].to_numpy().max())
    upper = max(10, max_count * 1.22)

    for ax, row in zip(axes, df.to_dict("records")):
        comparator = row["comparator"]
        values = [int(row["b"]), int(row["c"])]

        bars = ax.bar(
            [0, 1],
            values,
            width=0.60,
            color=[
                GATE_COLOR["F3"],
                GATE_COLOR[comparator],
            ],
            edgecolor="#444444",
            linewidth=0.7,
        )
        ax.bar_label(
            bars,
            labels=[str(v) for v in values],
            padding=5,
            fontsize=12,
            fontweight="bold",
        )
        ax.set_xticks([0, 1], ["b", "c"])
        ax.set_ylim(0, upper)
        ax.set_title(
            f"F3 vs {comparator}\n"
            f"Unadjusted p = {row['p_value']:.4g}",
            fontsize=12,
        )
        ax.set_xlabel("Discordant pair type")
        ax.grid(axis="y")
        ax.set_axisbelow(True)

    axes[0].set_ylabel("Number of paired samples")

    fig.suptitle(
        "UNMASK — McNemar paired comparisons",
        fontsize=15,
        fontweight="bold",
    )
    fig.legend(
        handles=[
            Patch(
                facecolor=GATE_COLOR["F3"],
                edgecolor="#444444",
                label="b: F3 correct, comparator incorrect",
            ),
            Patch(
                facecolor="white",
                edgecolor="#444444",
                label="c: F3 incorrect, comparator correct",
            ),
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, 0.13),
        ncol=2,
        fontsize=9,
    )
    fig.text(
        0.5, 0.085,
        "Only discordant pairs are shown; "
        "pairs where both methods agree are omitted.",
        ha="center",
        fontsize=9,
    )
    fig.text(
        0.5, 0.05,
        "p-values are read from the source CSV, "
        "without Holm adjustment; no significance stars are added.",
        ha="center",
        fontsize=9,
    )
    fig.text(
        0.5, 0.018,
        f"Source: {input_path.name}. "
        "Correctness follows the source evaluation definition.",
        ha="center",
        fontsize=9,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.23, 1, 0.91))

    save_figure(fig, output)
    plt.close(fig)

    summary_path = output.with_name(
        output.stem + "_summary.csv"
    )
    summary = df[[
        "comparison", "comparator", "b", "c", "p_value",
    ]].copy()
    summary["p_adjustment"] = "none"
    summary["source"] = input_path.name
    summary.to_csv(summary_path, index=False)

    print(summary.to_string(index=False))
    print(f"\nĐã lưu: {output}")
    print(f"Đã lưu: {summary_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "results" / "stats_mcnemar.csv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "figs" / "fig_mcnemar.png",
    )
    args = parser.parse_args()
    plot(args.input, args.out)


if __name__ == "__main__":
    main()