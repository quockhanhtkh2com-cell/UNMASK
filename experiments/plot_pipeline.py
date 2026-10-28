"""Vẽ pipeline UNMASK: các cổng thay thế nhau, dùng chung D1 — [Trúc].

Chạy:
    python -m experiments.plot_pipeline
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

try:
    from .plot_style import (
        apply_style,
        save_figure,
        GATE_COLOR,
    )
except ImportError:
    from plot_style import (
        apply_style,
        save_figure,
        GATE_COLOR,
    )


ROOT = Path(__file__).resolve().parents[1]


def box(ax, x, y, width, height, text, color="#666666",
        fill="white", fontsize=10):
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.6,
        edgecolor=color,
        facecolor=fill,
        zorder=3,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color="#222222",
        zorder=4,
    )


def arrow(ax, start, end, color="#666666", style="-"):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=13,
        linewidth=1.4,
        linestyle=style,
        color=color,
        zorder=2,
    )
    ax.add_patch(patch)


def plot(output: Path):
    apply_style()
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis("off")

    fig.suptitle(
        "UNMASK — Shared-detector evaluation pipeline",
        fontsize=16,
        fontweight="bold",
        y=0.97,
    )

    # Input: static analysis only.
    box(
        ax, 0.25, 4.10, 2.0, 1.1,
        "PE file\nStatic features only",
    )
    arrow(ax, (2.27, 4.65), (2.80, 4.65))

    # Input bus distributes the same samples to alternative gates.
    ax.plot(
        [2.80, 2.80], [1.65, 7.65],
        color="#888888", linewidth=1.3, zorder=1,
    )

    ax.text(
        4.45, 8.45,
        "Alternative gates — evaluated separately",
        ha="center", fontsize=11, fontweight="bold",
    )

    gates = [
        ("F0", 7.20, "F0 — No filter\nAll samples PASS"),
        ("F1", 5.70, "F1 — Detect It Easy\npacked/protected → FILTERED"),
        ("F2", 4.20, "F2 — Entropy rule\nentropy > 7 + unusual section"),
        ("F3a", 2.70, "F3a — Ablation\nPacked score; no dual-check"),
        ("F3", 1.20, "F3 — UNMASK\nPacked score + dual-check"),
    ]

    for gate, y, text in gates:
        center_y = y + 0.45
        arrow(
            ax,
            (2.80, center_y),
            (3.10, center_y),
            color=GATE_COLOR[gate],
        )
        box(
            ax, 3.10, y, 2.75, 0.90,
            text,
            color=GATE_COLOR[gate],
            fontsize=9,
        )
        arrow(
            ax,
            (5.87, center_y),
            (6.65, center_y),
            color=GATE_COLOR[gate],
        )

    # Shared routing rule for all gates.
    box(
        ax, 6.65, 1.20, 1.80, 6.90,
        "Decision\nrouting\n\n"
        "PASS\nor\nFLAGGED\n→ D1\n\n"
        "FILTERED\n→ log only",
        fontsize=11,
    )

    arrow(ax, (8.47, 5.65), (9.15, 5.65))
    ax.text(
        8.80, 6.02,
        "PASS /\nFLAGGED",
        ha="center", fontsize=9,
    )

    box(
        ax, 9.15, 5.05, 2.05, 1.20,
        "Common detector D1\n"
        "Same model and threshold\n"
        "for every gate",
        fontsize=10,
    )

    arrow(ax, (11.22, 5.65), (11.85, 5.65))
    box(
        ax, 11.85, 5.05, 1.85, 1.20,
        "Drift alarm\nor\nNo alarm",
        fontsize=10,
    )

    arrow(
        ax,
        (8.47, 2.45),
        (9.15, 2.45),
        color="#b04444",
    )
    box(
        ax, 9.15, 1.85, 2.05, 1.20,
        "FILTERED\nExcluded from D1\nDecision recorded",
        color="#b04444",
        fontsize=10,
    )

    ax.text(
        10.20, 4.25,
        "D1 fit: G0 train\n"
        "Threshold fixed before test evaluation",
        ha="center",
        va="center",
        fontsize=9,
        color="#555555",
    )

    fig.text(
        0.5, 0.055,
        "F3: low packed score → PASS; "
        "high score + similar core → FILTERED; "
        "high score + novel core → FLAGGED.",
        ha="center",
        fontsize=10,
    )
    fig.text(
        0.5, 0.025,
        "Static analysis only. PE files are never executed. "
        "F3a is the ablation baseline without dual-check.",
        ha="center",
        fontsize=9,
        color="#555555",
    )

    fig.tight_layout(rect=(0, 0.10, 1, 0.94))
    save_figure(fig, output)
    plt.close(fig)
    print(f"Đã lưu: {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "figs" / "fig_pipeline.png",
    )
    args = parser.parse_args()
    plot(args.out)


if __name__ == "__main__":
    main()