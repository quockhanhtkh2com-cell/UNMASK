"""Vẽ Hình 7.2 (Report): FTR theo cổng lọc tại ba tỉ lệ đóng gói mục tiêu 0,3 / 0,5 / 0,7.

Nguồn dữ liệu: results/bang_chinh.csv (cột gate, FTR@30, FTR@50, FTR@70).
Dùng khuôn vẽ chung của nhóm (experiments/plot_style.py) để đồng bộ font/định dạng
với các hình khác (fig_e0b_alarm_by_group.png, fig_fnr_filter_vs_e2e.png,
e5_ftr_fnr_curve.png, fig_e6_breakdown.png).

Chạy: python experiments/plot_ftr_by_gate.py
Input: results/bang_chinh.csv
Output: figs/fig_ftr_by_gate.png
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plot_style import GATE_LABELS, apply_style, save_figure

ROOT = Path(__file__).resolve().parent.parent
RESULTS_CSV = ROOT / "results" / "bang_chinh.csv"
OUT_PNG = ROOT / "figs" / "fig_ftr_by_gate.png"

# Thứ tự hiển thị theo đúng Bảng 7.2 trong Report (bảng đó chỉ có 5 cổng, không có F1+)
GATES = ["F0", "F1", "F2", "F3", "F3a"]
COLS = ["FTR@30", "FTR@50", "FTR@70"]
COL_COLOR = {"FTR@30": "#90caf9", "FTR@50": "#1e88e5", "FTR@70": "#0d47a1"}


def main():
    apply_style()
    df = pd.read_csv(RESULTS_CSV).set_index("gate")

    x = np.arange(len(GATES))
    width = 0.25

    fig, ax = plt.subplots(figsize=(7, 4.2))
    for i, col in enumerate(COLS):
        values = [df.loc[g, col] for g in GATES]
        ax.bar(x + (i - 1) * width, values, width=width, label=col, color=COL_COLOR[col])

    ax.set_xticks(x)
    ax.set_xticklabels([GATE_LABELS.get(g, g) for g in GATES], rotation=10)
    ax.set_ylabel("FTR")
    ax.set_title("FTR theo cổng lọc và tỉ lệ đóng gói (tập test, 404 mẫu)")
    ax.legend(title="Tỉ lệ đóng gói mục tiêu")
    ax.grid(axis="y")

    save_figure(fig, OUT_PNG)
    print("Saved:", OUT_PNG)


if __name__ == "__main__":
    main()
