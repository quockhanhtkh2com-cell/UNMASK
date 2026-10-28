"""Vẽ đường cong E5 (FTR–FNR đánh đổi theo cổng) và bảng E6 per-packer.

Usage:
    python experiments/plot_e5_e6.py --results results/ --out figs/
"""
from __future__ import annotations
import argparse, glob, os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

GATE_ORDER  = ["F0", "F1", "F2", "F3a", "F3"]
GATE_LABELS = {"F0": "F0 (baseline)", "F1": "F1 (DiE)", "F2": "F2 (entropy rule)",
               "F3a": "F3a (ablation)", "F3": "F3 (proposed)"}
GATE_COLOR  = {"F0": "#9e9e9e", "F1": "#ef5350", "F2": "#ff9800",
               "F3a": "#42a5f5", "F3": "#26c6da"}
GATE_MARKER = {"F0": "s", "F1": "^", "F2": "D", "F3a": "o", "F3": "*"}
GATE_SIZE   = {"F0": 80,  "F1": 80,  "F2": 80,  "F3a": 80,  "F3": 140}


def load_exp(results_dir: str, exp: str) -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(results_dir, f"results_{exp}_*.csv")))
    if not files:
        raise FileNotFoundError(f"Không tìm thấy CSV cho {exp} trong {results_dir}")
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def plot_e5_curve(results_dir: str, out_dir: str):
    """Đường cong đánh đổi FTR–FNR_G3 theo cổng F0–F3 (mean ± std qua seed × pack_ratio)."""
    df = load_exp(results_dir, "e5")
    os.makedirs(out_dir, exist_ok=True)

    # ─── Figure 1: FTR vs FNR_G3 (scatter các điểm hoạt động) ───
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#161b22")

    for gate in GATE_ORDER:
        gd = df[df.gate == gate]
        xs = gd["FTR"].values
        ys = gd["FNR_G3"].values
        mx, my = xs.mean(), ys.mean()
        sx, sy = xs.std(ddof=0), ys.std(ddof=0)
        # vẽ error bars
        ax.errorbar(mx, my, xerr=sx, yerr=sy,
                    fmt=GATE_MARKER[gate], color=GATE_COLOR[gate],
                    markersize=10 if gate == "F3" else 7,
                    linewidth=1.5, capsize=4, alpha=0.9,
                    label=GATE_LABELS[gate])
        ax.annotate(gate, (mx, my),
                    textcoords="offset points", xytext=(8, 4),
                    fontsize=8, color=GATE_COLOR[gate], fontweight="bold")

    # Đường thẳng ideal FTR=0 (không có false alarm)
    ax.axvline(0, color="#ffffff22", linestyle="--", linewidth=0.8)

    ax.set_xlabel("FTR (False-Trigger Rate)", color="#c9d1d9", fontsize=11)
    ax.set_ylabel("FNR G3 (Miss Rate — packer mới)", color="#c9d1d9", fontsize=11)
    ax.set_title("E5 — Đánh đổi FTR / FNR_G3 theo cổng\n(mean ± std qua 3 seed × 3 pack-ratio)", 
                 color="#f0f6fc", fontsize=12, fontweight="bold")
    ax.tick_params(colors="#8b949e")
    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")
    ax.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="#c9d1d9",
              fontsize=8.5, loc="upper right")
    ax.grid(color="#21262d", linestyle="--", linewidth=0.6)

    # annotate locked operating point
    f3_d = df[df.gate == "F3"]
    f3_ftr = f3_d["FTR"].mean()
    f3_fnr = f3_d["FNR_G3"].mean()
    ax.annotate("← Điểm hoạt động\n   khoá (F3=0.475)",
                xy=(f3_ftr, f3_fnr), xytext=(f3_ftr + 0.025, f3_fnr + 0.07),
                fontsize=7.5, color="#26c6da",
                arrowprops=dict(arrowstyle="->", color="#26c6da", lw=1.2))

    plt.tight_layout()
    out1 = os.path.join(out_dir, "e5_ftr_fnr_curve.png")
    plt.savefig(out1, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close()
    print(f"[E5] đường cong FTR–FNR_G3 → {out1}")

    # ─── Figure 2: FTR vs FNR_G2 ───
    fig2, ax2 = plt.subplots(figsize=(7, 5))
    fig2.patch.set_facecolor("#0d1117")
    ax2.set_facecolor("#161b22")
    for gate in GATE_ORDER:
        gd = df[df.gate == gate]
        mx = gd["FTR"].mean(); my = gd["FNR_G2"].mean()
        sx = gd["FTR"].std(ddof=0); sy = gd["FNR_G2"].std(ddof=0)
        ax2.errorbar(mx, my, xerr=sx, yerr=sy,
                     fmt=GATE_MARKER[gate], color=GATE_COLOR[gate],
                     markersize=10 if gate == "F3" else 7,
                     linewidth=1.5, capsize=4, alpha=0.9,
                     label=GATE_LABELS[gate])
        ax2.annotate(gate, (mx, my), textcoords="offset points", xytext=(8, 4),
                     fontsize=8, color=GATE_COLOR[gate], fontweight="bold")
    ax2.set_xlabel("FTR (False-Trigger Rate)", color="#c9d1d9", fontsize=11)
    ax2.set_ylabel("FNR G2 (Miss Rate — packing đã học)", color="#c9d1d9", fontsize=11)
    ax2.set_title("E5 — FTR / FNR_G2 theo cổng", color="#f0f6fc", fontsize=12, fontweight="bold")
    ax2.tick_params(colors="#8b949e")
    for spine in ax2.spines.values():
        spine.set_edgecolor("#30363d")
    ax2.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="#c9d1d9", fontsize=8.5)
    ax2.grid(color="#21262d", linestyle="--", linewidth=0.6)
    plt.tight_layout()
    out2 = os.path.join(out_dir, "e5_ftr_fnr_g2_curve.png")
    plt.savefig(out2, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close()
    print(f"[E5] đường cong FTR–FNR_G2 → {out2}")

    return out1, out2


def plot_e6_per_packer(results_dir: str, out_dir: str):
    """E6 bonus: FTR và correct_Punseen theo tỉ lệ pack (per-packer proxy)."""
    df = load_exp(results_dir, "e6")
    os.makedirs(out_dir, exist_ok=True)

    ratios = sorted(df["pack_ratio_set"].unique())
    gates  = GATE_ORDER

    # Bảng mean ± std qua seed
    summary = (df.groupby(["gate", "pack_ratio_set"])
               .agg(FTR_mean=("FTR", "mean"), FTR_std=("FTR", "std"),
                    FNR_G3_mean=("FNR_G3", "mean"), FNR_G3_std=("FNR_G3", "std"),
                    Pu_mean=("correct_filter_Punseen", "mean"),
                    Pu_std=("correct_filter_Punseen", "std"))
               .reset_index())

    # grouped bar: correct_Punseen theo cổng × pack_ratio
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#161b22")

    n_gate   = len(gates)
    n_ratio  = len(ratios)
    bar_w    = 0.18
    x_base   = np.arange(n_gate)
    ratio_colors = ["#4fc3f7", "#81c784", "#ffb74d"]

    for ri, ratio in enumerate(ratios):
        rd = summary[summary.pack_ratio_set == ratio]
        vals, errs = [], []
        for g in gates:
            row = rd[rd.gate == g]
            if len(row):
                vals.append(float(row["Pu_mean"].iloc[0]))
                errs.append(float(row["Pu_std"].iloc[0]) if not pd.isna(row["Pu_std"].iloc[0]) else 0)
            else:
                vals.append(0); errs.append(0)
        offset = (ri - n_ratio / 2 + 0.5) * bar_w
        bars = ax.bar(x_base + offset, vals, bar_w, yerr=errs, capsize=3,
                      color=ratio_colors[ri], alpha=0.85,
                      label=f"pack={int(ratio*100)}%",
                      error_kw=dict(ecolor="#ffffff80", lw=1))

    ax.set_xticks(x_base)
    ax.set_xticklabels([GATE_LABELS.get(g, g) for g in gates],
                       color="#c9d1d9", fontsize=8.5, rotation=10)
    ax.set_ylabel("correct_Punseen (packer chưa thấy)", color="#c9d1d9", fontsize=10)
    ax.set_title("E6 — Tỉ lệ nhận đúng Packer chưa thấy theo cổng × tỉ lệ pack\n(mean ± std, 3 seed)",
                 color="#f0f6fc", fontsize=11, fontweight="bold")
    ax.tick_params(colors="#8b949e")
    ax.set_ylim(0, 1.1)
    ax.axhline(0.5, color="#ffffff30", linestyle="--", linewidth=0.8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#30363d")
    ax.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="#c9d1d9", fontsize=9)
    ax.grid(axis="y", color="#21262d", linestyle="--", linewidth=0.6)
    plt.tight_layout()
    out3 = os.path.join(out_dir, "e6_per_packer_correct_punseen.png")
    plt.savefig(out3, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close()
    print(f"[E6] per-packer correct_Punseen → {out3}")

    # Xuất bảng tóm tắt E6
    tbl = summary[summary.gate == "F3"][["pack_ratio_set", "FTR_mean", "FTR_std",
                                          "FNR_G3_mean", "FNR_G3_std", "Pu_mean", "Pu_std"]]
    tbl_path = os.path.join(results_dir, "e6_summary.csv")
    tbl.to_csv(tbl_path, index=False, float_format="%.4f")
    print(f"[E6] bảng summary F3 → {tbl_path}")
    return out3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results/")
    ap.add_argument("--out", default="figs/")
    args = ap.parse_args()
    plot_e5_curve(args.results, args.out)
    plot_e6_per_packer(args.results, args.out)
    print("✓ Đã xuất tất cả hình vào", args.out)


if __name__ == "__main__":
    main()
