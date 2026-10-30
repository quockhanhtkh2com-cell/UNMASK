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
    from pathlib import Path
    import json
    import numpy as np

    try:
        from .plot_style import apply_style, save_figure
    except ImportError:
        from plot_style import apply_style, save_figure

    apply_style()

    root = Path(__file__).resolve().parents[1]
    source = root / "results" / "e5_sweep.csv"
    config_path = root / "config" / "thresholds.locked.json"

    df = pd.read_csv(source)
    required = ["threshold", "FTR", "FNR_e2e_G2", "FNR_e2e_G3"]

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"CSV thiếu cột: {missing}")
    if df.empty:
        raise ValueError("CSV sweep không có dữ liệu.")

    numeric = df[required].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("CSV chứa giá trị thiếu, không phải số hoặc vô cực.")
    if not numeric.ge(0).all().all() or not numeric.le(1).all().all():
        raise ValueError("Ngưỡng và các tỉ lệ phải nằm trong khoảng 0–1.")
    if numeric["threshold"].duplicated().any():
        raise ValueError(
            "Có nhiều dòng cho cùng một ngưỡng. "
            "Cần xác nhận cách tổng hợp trước khi vẽ."
        )

    df = numeric.sort_values("threshold").reset_index(drop=True)

    with config_path.open(encoding="utf-8") as file:
        config = json.load(file)

    if config.get("locked") is not True:
        raise ValueError("Cấu hình F3 chưa được khóa.")

    threshold = config.get("packed_score", {}).get("threshold")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not np.isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise ValueError("Ngưỡng packed_score trong cấu hình không hợp lệ.")

    fig, ax = plt.subplots(figsize=(9, 5.8))

    curves = [
        ("FTR", "FTR", "o", "#1f77b4"),
        ("FNR_e2e_G2", "End-to-end FNR — G2", "s", "#ff7f0e"),
        ("FNR_e2e_G3", "End-to-end FNR — G3", "^", "#d62728"),
    ]

    for column, label, marker, color in curves:
        ax.plot(
            df["threshold"], df[column],
            marker=marker,
            markersize=4,
            linewidth=1.6,
            color=color,
            label=label,
        )

    ax.axvline(
        threshold,
        color="#555555",
        linestyle="--",
        linewidth=1.3,
        label=f"Locked F3 threshold = {threshold:g}",
    )

    has_locked_row = np.isclose(
        df["threshold"].to_numpy(),
        threshold,
        rtol=0,
        atol=1e-10,
    ).any()

    ax.set_xlabel("Packed score threshold")
    ax.set_ylabel("Rate (%)")
    ax.set_title(
        "DRAFT — E5 threshold sweep\n"
        "Descriptive analysis; locked configuration unchanged"
    )
    ax.set_ylim(0, 1.05)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1))
    ax.grid(axis="both", linestyle="--", alpha=0.4)
    ax.legend(loc="best")

    note = (
        f"Source: results/e5_sweep.csv | {len(df)} thresholds.\n"
        "Awaiting updated full-test results; pack-ratio context "
        "must accompany the final FTR figure."
    )
    if not has_locked_row:
        note += (
            f"\nNo measured row at {threshold:g}; "
            "the dashed line marks the threshold only."
        )

    fig.text(0.5, 0.02, note, ha="center", va="bottom", fontsize=8)
    fig.tight_layout(rect=(0, 0.15, 1, 1))

    output = root / "figs" / "fig_e5_sweep_draft.png"
    save_figure(fig, output)
    plt.close(fig)

    print(f"[E5] Đã lưu bản nháp: {output}")
    print(f"[E5] Ngưỡng khóa đọc từ config: {threshold:g}")
    if not has_locked_row:
        print("[E5] CSV chưa có kết quả đo tại đúng ngưỡng khóa.")


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