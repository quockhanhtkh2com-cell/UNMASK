"""Vẽ tỉ lệ D1 báo drift theo nhóm trên toàn bộ test — [Trúc].

Chạy:
    python -m experiments.plot_e0b_alarm_by_group

Chỉ đọc dataset/config; không thay đổi ngưỡng khóa.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import schema_cols as S
from detector import DriftDetector

try:
    from .plot_style import apply_style, save_figure
except ImportError:
    from plot_style import apply_style, save_figure


GROUPS = ["G0", "G1", "G2", "G3"]
FEATURE_NUM = [
    col for col in S.FEATURE_COLS
    if col != "section_name_class"
]


def wilson(num, den):
    z = 1.959963984540054
    p = num / den
    scale = 1 + z * z / den
    center = (p + z * z / (2 * den)) / scale
    margin = (
        z * np.sqrt(
            p * (1 - p) / den + z * z / (4 * den * den)
        ) / scale
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def plot(dataset_path, config_path, output):
    df = pd.read_csv(
        dataset_path,
        dtype={"sha256": str, "origin_sha256": str},
    )
    with config_path.open(encoding="utf-8") as handle:
        cfg = json.load(handle)

    if cfg.get("locked") is not True:
        raise ValueError("Config chưa khóa; dừng vẽ.")

    d1_cfg = cfg.get("detector_D1") or {}
    threshold = d1_cfg.get("threshold_value")
    if threshold is None:
        raise ValueError("Config thiếu ngưỡng D1 đã khóa.")

    threshold = float(threshold)
    if not np.isfinite(threshold):
        raise ValueError("Ngưỡng D1 không hữu hạn.")

    method = d1_cfg.get("method")
    if method != "mahalanobis":
        raise ValueError(
            f"Script này dành cho D1 mahalanobis, nhận được: {method!r}"
        )

    required = {
        "sha256", "origin_sha256", "group", "split",
        *FEATURE_NUM,
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Thiếu cột: {sorted(missing)}")
    if df.empty:
        raise ValueError("Dataset không có mẫu.")
    if df[list(required)].isna().any().any():
        raise ValueError("Có giá trị thiếu trong cột bắt buộc.")
    if df["sha256"].duplicated().any():
        raise ValueError("Dataset có sha256 trùng.")
    if not df["group"].isin(GROUPS).all():
        raise ValueError("group không hợp lệ.")
    if not df["split"].isin(["train", "val", "test"]).all():
        raise ValueError("split không hợp lệ.")
    if (df.groupby("origin_sha256")["split"].nunique() > 1).any():
        raise ValueError("Có origin nằm ở nhiều split.")

    numeric = df[FEATURE_NUM].apply(
        pd.to_numeric, errors="coerce"
    )
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Feature số không hợp lệ hoặc không hữu hạn.")
    df[FEATURE_NUM] = numeric

    train = df.loc[
        (df["group"] == "G0") & (df["split"] == "train"),
        FEATURE_NUM,
    ]
    test = df.loc[df["split"] == "test"].copy()

    if len(train) < 2:
        raise ValueError("Không đủ mẫu G0 train để dựng D1.")
    if test.empty:
        raise ValueError("Dataset không có mẫu test.")

    # Dựng D1 từ G0 train; dùng nguyên ngưỡng config.
    detector = DriftDetector(
        method=method,
        seed=0,
        standardize=True,
    ).fit(train.to_numpy(dtype=float))
    detector.threshold = threshold

    test["alarm"] = detector.predict(
        test[FEATURE_NUM].to_numpy(dtype=float)
    )

    rows = []
    for group in GROUPS:
        samples = test.loc[test["group"] == group]
        den = len(samples)
        if den == 0:
            raise ValueError(f"Không có {group} trong test.")

        num = int(samples["alarm"].sum())
        low, high = wilson(num, den)
        rows.append({
            "group": group,
            "num_alarms": num,
            "num_samples": den,
            "alarm_rate": num / den,
            "ci_low": low,
            "ci_high": high,
            "split": "test",
            "gate": "F0",
            "d1_threshold": threshold,
            "dataset": dataset_path.name,
        })

    summary = pd.DataFrame(rows)
    values = summary["alarm_rate"].to_numpy() * 100
    low = summary["ci_low"].to_numpy() * 100
    high = summary["ci_high"].to_numpy() * 100

    apply_style()
    fig, ax = plt.subplots(figsize=(9, 5.8))
    positions = np.arange(len(GROUPS))

    bars = ax.bar(
        positions,
        values,
        width=0.60,
        color="#4c78a8",
        yerr=np.maximum(
            0,
            np.vstack([values - low, high - values]),
        ),
        capsize=5,
        error_kw={"ecolor": "#333333", "linewidth": 1.2},
    )

    for bar, row in zip(bars, rows):
        top = row["ci_high"] * 100
        ax.annotate(
            f"{row['alarm_rate']:.1%}\n"
            f"{row['num_alarms']}/{row['num_samples']}",
            xy=(bar.get_x() + bar.get_width() / 2, top),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax.set_xticks(positions, GROUPS)
    ax.set_ylim(0, 119)
    ax.set_xlabel("Ground-truth group")
    ax.set_ylabel("D1 alarm rate (%)")
    ax.set_title("E0b — D1 alarms by group (full test set)")
    ax.grid(axis="y")
    ax.set_axisbelow(True)

    fig.text(
        0.5, 0.055,
        f"F0: no filtering | n={len(test)} test samples | "
        f"Locked D1 threshold={threshold:.4f}",
        ha="center",
        fontsize=9,
    )
    fig.text(
        0.5, 0.022,
        "Error bars: Wilson 95% CI. "
        "G0/G1 are non-drift; G2/G3 are true drift.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.11, 1, 1))

    save_figure(fig, output)
    plt.close(fig)

    csv_path = output.with_name(
        output.stem + "_summary.csv"
    )
    summary.to_csv(csv_path, index=False)

    print(summary[[
        "group", "num_alarms", "num_samples",
        "alarm_rate", "ci_low", "ci_high",
    ]].to_string(index=False))
    print(f"\nĐã lưu: {output}")
    print(f"Đã lưu: {csv_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "dataset_v1.1.csv",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "thresholds.locked.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "figs" / "fig_e0b_alarm_by_group.png",
    )
    args = parser.parse_args()
    plot(args.dataset, args.config, args.out)


if __name__ == "__main__":
    main()