"""Hình 7.2 — FTR theo gate và tỉ lệ đóng gói mục tiêu.

Nguồn: results/bang_chinh.csv.
Chỉ đọc kết quả có sẵn, không chạy lại thí nghiệm.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

try:
    from .plot_style import apply_style, save_figure
except ImportError:
    from plot_style import apply_style, save_figure


ROOT = Path(__file__).resolve().parents[1]
RESULTS_CSV = ROOT / "results" / "bang_chinh.csv"
OUT_PNG = ROOT / "figs" / "fig_ftr_by_gate.png"

GATES = [
    "F0",
    "F1-oracle",
    "F1-DiE",
    "F1-DiE+protected",
    "F2",
    "F3",
    "F3a",
]

LABELS = {
    "F0": "F0",
    "F1-oracle": "F1-oracle",
    "F1-DiE": "F1-DiE",
    "F1-DiE+protected": "F1-DiE\n+protected",
    "F2": "F2",
    "F3": "F3",
    "F3a": "F3a",
}

SERIES = [
    ("FTR@30", "30%", "#90caf9"),
    ("FTR@50", "50%", "#1e88e5"),
    ("FTR@70", "70%", "#0d47a1"),
]


def main():
    apply_style()
    df = pd.read_csv(RESULTS_CSV)

    required = ["gate"] + [col for col, _, _ in SERIES]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Bảng kết quả thiếu cột: {missing}")
    if df["gate"].duplicated().any():
        raise ValueError("Bảng kết quả có gate trùng.")

    df = df.set_index("gate")
    missing_gates = [gate for gate in GATES if gate not in df.index]
    if missing_gates:
        raise ValueError(f"Thiếu kết quả gate: {missing_gates}")

    cols = [col for col, _, _ in SERIES]
    rates = df.loc[GATES, cols].apply(pd.to_numeric, errors="coerce")

    if not np.isfinite(rates.to_numpy(dtype=float)).all():
        raise ValueError("FTR có giá trị thiếu hoặc không hợp lệ.")
    if not rates.ge(0).all().all() or not rates.le(1).all().all():
        raise ValueError("FTR phải nằm trong khoảng 0–1.")

    x = np.arange(len(GATES))
    width = 0.24
    fig, ax = plt.subplots(figsize=(11, 5.5))

    for index, (column, label, color) in enumerate(SERIES):
        ax.bar(
            x + (index - 1) * width,
            rates[column].to_numpy(dtype=float),
            width=width,
            label=label,
            color=color,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[gate] for gate in GATES])
    ax.set_ylabel("FTR (%)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_ylim(0, min(1.05, max(0.05, rates.to_numpy().max() * 1.2)))
    ax.set_title("Hình 7.2 — FTR theo cổng lọc")
    ax.legend(title="Tỉ lệ đóng gói mục tiêu", ncol=3)
    ax.grid(axis="y")

    fig.text(
        0.5, 0.02,
        "Nguồn: results/bang_chinh.csv. "
        "F1-oracle dùng nhãn lý tưởng từ manifest;\n"
        "F1-DiE dùng kết quả DiE thực, chỉ loại packed; "
        "biến thể +protected loại cả packed và protected.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.12, 1, 1))

    save_figure(fig, OUT_PNG)
    plt.close(fig)

    print(rates.to_string())
    print(f"Đã lưu: {OUT_PNG}")


if __name__ == "__main__":
    main()