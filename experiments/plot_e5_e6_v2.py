#!/usr/bin/env python3
"""Ve lai E5 (duong cong FTR-FNR that, 19 diem sweep) va E6 (breakdown theo
packer/platform/family) dung so lieu moi cua Duc. KHONG dung de chon lai
nguong F3 - van khoa 0.4750, duong cong chi de mo ta he thong."""
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "font.size": 11,
})

LOCKED_THRESHOLD = 0.4750


def plot_e5_sweep():
    df = pd.read_csv("results/e5_sweep.csv")
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    ax.plot(df["threshold"], df["FTR"], marker="o", label="FTR (bao nham G0)", color="#1f77b4")
    ax.plot(df["threshold"], df["FNR_e2e_G2"], marker="s", label="FNR toan trinh G2", color="#ff7f0e")
    ax.plot(df["threshold"], df["FNR_e2e_G3"], marker="^", label="FNR toan trinh G3", color="#d62728")
    ax.axvline(LOCKED_THRESHOLD, color="gray", linestyle="--", linewidth=1.2,
               label=f"Nguong F3 da khoa ({LOCKED_THRESHOLD})")
    ax.set_xlabel("Nguong packed_score (F3)")
    ax.set_ylabel("Ty le")
    ax.set_title("E5 - Duong cong FTR-FNR theo nguong F3 (19 diem quet, chi mo ta he thong)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.legend(loc="center right", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("figs/fig_e5_sweep.png", dpi=300)
    plt.close(fig)
    print("[OK] figs/fig_e5_sweep.png")


def plot_e6_breakdown():
    pack = pd.read_csv("results/e6_per_packer.csv")
    fam = pd.read_csv("results/e6_per_family.csv")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), dpi=300)

    ax = axes[0]
    x = range(len(pack))
    yerr = [pack["FNR_G3"] - pack["CI_lo"], pack["CI_hi"] - pack["FNR_G3"]]
    ax.bar(x, pack["FNR_G3"], yerr=yerr, capsize=4, color="#4c72b0")
    ax.set_xticks(list(x))
    ax.set_xticklabels(pack["category"], rotation=20, ha="right")
    for i, (n, v) in enumerate(zip(pack["n"], pack["FNR_G3"])):
        ax.text(i, v + 0.03, f"n={n}", ha="center", fontsize=9)
    ax.set_ylabel("FNR_G3 (Wilson 95% CI)")
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_title("E6a - FNR_G3 theo packer / platform")
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    x = range(len(fam))
    yerr = [fam["FNR_G3"] - fam["CI_lo"], fam["CI_hi"] - fam["FNR_G3"]]
    ax.bar(x, fam["FNR_G3"], yerr=yerr, capsize=4, color="#dd8452")
    ax.set_xticks(list(x))
    ax.set_xticklabels(fam["family"], rotation=30, ha="right")
    for i, (n, v) in enumerate(zip(fam["n"], fam["FNR_G3"])):
        ax.text(i, v + 0.03, f"n={n}", ha="center", fontsize=8)
    ax.set_ylabel("FNR_G3 (Wilson 95% CI)")
    ax.set_ylim(0, 1.1)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.set_title("E6b - FNR_G3 theo ho ma doc (G2 goc)")
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("E6 - Breakdown FNR_G3 (404 mau test)", fontsize=13)
    fig.tight_layout()
    fig.savefig("figs/fig_e6_breakdown.png", dpi=300)
    plt.close(fig)
    print("[OK] figs/fig_e6_breakdown.png")


if __name__ == "__main__":
    os.makedirs("figs", exist_ok=True)
    plot_e5_sweep()
    plot_e6_breakdown()