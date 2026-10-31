"""Hình 7.4 — điểm hoạt động FTR và FNR toàn trình theo gate.

Dùng toàn bộ test, không resample, không trung bình qua seed.
Tái sử dụng cách đánh giá trong compute_ftr_prevalence.py.
Không thay đổi cấu hình khóa hoặc bảng kết quả chính.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from compute_ftr_prevalence import run as evaluate_full_test
from experiments.plot_style import apply_style, save_figure


GATES = [
    "F0", "F1-oracle", "F1-DiE", "F1-DiE+protected",
    "F2", "F3a", "F3",
]

COLORS = {
    "F0": "#757575",
    "F1-oracle": "#8e44ad",
    "F1-DiE": "#ef5350",
    "F1-DiE+protected": "#c2185b",
    "F2": "#ef8b00",
    "F3a": "#1976d2",
    "F3": "#008c9e",
}

MARKERS = {
    "F0": "s",
    "F1-oracle": "D",
    "F1-DiE": "^",
    "F1-DiE+protected": "v",
    "F2": "P",
    "F3a": "o",
    "F3": "*",
}


def main():
    apply_style()

    dataset = ROOT / "dataset_v1.1.csv"
    config = ROOT / "config" / "thresholds.locked.json"
    die = ROOT / "results" / "die_real_v1.1.csv"
    output_dir = ROOT / "results" / "figs"

    with config.open(encoding="utf-8") as handle:
        cfg = json.load(handle)
    packed_threshold = cfg["packed_score"]["threshold"]

    # File trung gian được giữ trong thư mục tạm.
    # Không ghi đè hai CSV prevalence đã bàn giao trước đó.
    with tempfile.TemporaryDirectory(prefix="unmask_figure74_") as tmp:
        tmp_dir = Path(tmp)
        evaluate_full_test(
            dataset, config, die, 0.3, tmp_dir,
        )
        totals = pd.read_csv(
            tmp_dir / "ftr_prevalence_standardized.csv"
        )
        groups = pd.read_csv(
            tmp_dir / "ftr_prevalence_by_group.csv"
        )

    if totals["gate"].duplicated().any():
        raise ValueError("Kết quả có gate trùng.")
    if set(totals["gate"]) != set(GATES):
        raise ValueError(
            f"Danh sách gate không khớp: {totals['gate'].tolist()}"
        )
    if groups.duplicated(["gate", "group"]).any():
        raise ValueError("Kết quả có cặp gate/group trùng.")

    totals = totals.set_index("gate")
    groups = groups.set_index(["gate", "group"])

    if totals["n_test"].nunique() != 1:
        raise ValueError("Các gate không dùng cùng số mẫu test.")

    n_test = int(totals["n_test"].iloc[0])
    rows = []

    for gate in GATES:
        for group in ["G2", "G3"]:
            block = groups.loc[(gate, group)]
            n = int(block["n"])
            alarms = int(block["alarm_count_after_filter"])
            filtered = int(block["n_filtered"])

            if n <= 0 or not 0 <= alarms <= n:
                raise ValueError(f"{gate}/{group}: số đếm không hợp lệ.")
            if not 0 <= filtered <= n - alarms:
                raise ValueError(f"{gate}/{group}: số đếm mâu thuẫn.")

            rows.append({
                "gate": gate,
                "group": group,
                "n_test": n_test,
                "n_group": n,
                "ftr_num": int(totals.loc[gate, "g1_alarm_count"]),
                "ftr_den": int(totals.loc[gate, "total_alarm_count"]),
                "FTR": float(totals.loc[gate, "ftr_observed"]),
                "n_filtered": filtered,
                "FNR_filter": filtered / n,
                "n_missed_e2e": n - alarms,
                "FNR_e2e": (n - alarms) / n,
                "pack_ratio_real": (
                    groups.loc[(gate, "G1"), "n"]
                    + groups.loc[(gate, "G3"), "n"]
                ) / n_test,
                "packed_score_threshold": packed_threshold,
                "d1_threshold": totals.loc[gate, "d1_threshold"],
                "dataset": dataset.name,
                "split": "test",
            })

    summary = pd.DataFrame(rows)
    if not np.isfinite(summary[["FTR", "FNR_e2e"]]).all().all():
        raise ValueError("Có điểm hoạt động không xác định.")

    ratio = float(summary["pack_ratio_real"].iloc[0])
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    for ax, group in zip(axes, ["G2", "G3"]):
        block = summary.loc[summary["group"].eq(group)].set_index("gate")

        for gate in GATES:
            row = block.loc[gate]
            ax.scatter(
                row["FTR"],
                row["FNR_e2e"],
                s=160 if gate == "F3" else 75,
                marker=MARKERS[gate],
                color=COLORS[gate],
                edgecolors="white",
                linewidths=0.6,
                label=gate,
                zorder=5 if gate == "F3" else 3,
            )

        ax.set_title(f"FTR / FNR toàn trình — {group}")
        ax.set_xlabel("FTR (%)")
        ax.set_ylabel(f"FNR toàn trình {group} (%)")
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(1))
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1))
        ax.set_xlim(
            -0.01,
            max(0.05, float(summary["FTR"].max()) * 1.2),
        )
        ax.set_ylim(-0.04, 1.06)
        ax.grid(linestyle="--", alpha=0.4)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles, labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.10),
        ncol=4,
        frameon=True,
    )
    fig.suptitle(
        "Hình 7.4 — Điểm hoạt động của các cổng trên toàn tập test",
        fontweight="bold",
    )
    fig.text(
        0.5, 0.015,
        f"{dataset.name} | test n={n_test} | "
        f"Tỉ lệ pack thực tế (G1 + G3): {ratio:.2%}\n"
        f"Ngưỡng F3 khóa: {packed_threshold:g}. "
        "Không resample, không trung bình qua seed; "
        "các điểm trùng nhau có thể chồng lấp.\n"
        "F1-oracle: nhãn lý tưởng; F1-DiE: kết quả DiE thực. "
        "Đây là điểm hoạt động, không phải đường quét ngưỡng.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.25, 1, 0.94))

    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / "hinh_7_4_operating_points.png"
    csv_path = output_dir / "hinh_7_4_operating_points_summary.csv"

    save_figure(fig, image_path)
    plt.close(fig)
    summary.to_csv(csv_path, index=False)

    print("\nKẾT QUẢ HÌNH 7.4:")
    print(summary[[
        "gate", "group", "FTR", "FNR_filter", "FNR_e2e",
        "n_missed_e2e", "n_group",
    ]].to_string(index=False))
    print(f"\nĐã lưu: {image_path}")
    print(f"Đã lưu: {csv_path}")


if __name__ == "__main__":
    main()