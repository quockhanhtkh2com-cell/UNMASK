"""FTR trên full test và chuẩn hóa prevalence G1 — [Trúc].

Prevalence ở đây là P(group == G1), không phải P(G1 hoặc G3).
Không lấy mẫu ngẫu nhiên, không chọn lại ngưỡng.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import schema_cols as S
import eval_metrics as M
from detector import DriftDetector
from unmask.filter import load_filter
from experiments.run_experiments import (
    GATES,
    _load_dataset,
    _gate_decisions,
)


def standardized_ftr(g1_alarm_rate, other_alarm_rate, prevalence):
    """P(G1 | alarm) tại prevalence G1 cố định."""
    values = [g1_alarm_rate, other_alarm_rate, prevalence]
    if not all(np.isfinite(v) and 0 <= v <= 1 for v in values):
        raise ValueError("Tỉ lệ phải hữu hạn và thuộc khoảng 0–1.")

    numerator = prevalence * g1_alarm_rate
    denominator = (
        numerator + (1 - prevalence) * other_alarm_rate
    )
    return numerator / denominator if denominator > 0 else np.nan


def run(dataset_path, config_path, die_path, prevalence, out_dir):
    if not 0 < prevalence < 1:
        raise ValueError("Prevalence phải nằm giữa 0 và 1.")

    with config_path.open(encoding="utf-8") as handle:
        cfg = json.load(handle)
    if cfg.get("locked") is not True:
        raise ValueError("Config chưa khóa.")

    d1_cfg = cfg.get("detector_D1") or {}
    if d1_cfg.get("method") != "mahalanobis":
        raise ValueError("Script yêu cầu D1 mahalanobis.")
    threshold = d1_cfg.get("threshold_value")
    if threshold is None or not np.isfinite(float(threshold)):
        raise ValueError("Thiếu ngưỡng D1 khóa hợp lệ.")

    # Dùng cùng loader và quyết định cổng với driver hiện tại.
    df = _load_dataset(
        str(dataset_path),
        die_real_path=str(die_path),
    )

    required = set(S.DATASET_COLS) | {"die_result_real"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Thiếu cột: {sorted(missing)}")
    if df.empty or df[list(required)].isna().any().any():
        raise ValueError("Dataset rỗng hoặc thiếu dữ liệu.")
    if df["sha256"].duplicated().any():
        raise ValueError("Có sha256 trùng sau khi join.")
    if not df["group"].isin(S.VALID_GROUPS).all():
        raise ValueError("group không hợp lệ.")
    if not df["split"].isin(S.VALID_SPLIT).all():
        raise ValueError("split không hợp lệ.")
    if not df["die_result_real"].isin(S.VALID_DIE).all():
        raise ValueError("Có kết quả DiE thật không hợp lệ.")
    if (df.groupby("origin_sha256")["split"].nunique() > 1).any():
        raise ValueError("Có origin nằm ở nhiều split.")

    features = [
        c for c in S.FEATURE_COLS
        if c != "section_name_class"
    ]
    numeric = df[features].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Feature số không hợp lệ.")
    df[features] = numeric

    train = df.loc[
        df["group"].eq("G0") & df["split"].eq("train"),
        features,
    ]
    test = df.loc[df["split"].eq("test")].reset_index(drop=True)
    if len(train) < 2 or test.empty:
        raise ValueError("Thiếu G0 train hoặc mẫu test.")

    g1_mask = test["group"].eq("G1").to_numpy()
    n_g1 = int(g1_mask.sum())
    n_other = int((~g1_mask).sum())
    if not n_g1 or not n_other:
        raise ValueError("Cần cả G1 và mẫu ngoài G1.")

    # Fit tham chiếu từ G0 train; dùng nguyên ngưỡng đã khóa.
    detector = DriftDetector(
        method="mahalanobis", seed=0, standardize=True,
    ).fit(train.to_numpy(dtype=float))
    detector.threshold = float(threshold)
    alarms = np.asarray(
        detector.predict(test[features].to_numpy(dtype=float)),
        dtype=bool,
    )

    f3 = load_filter(str(config_path), use_dualcheck=True)
    f3a = load_filter(str(config_path), use_dualcheck=False)

    summaries = []
    group_rows = []

    for gate in GATES:
        decisions = np.asarray(
            _gate_decisions(gate, test, f3, f3a)
        )
        if len(decisions) != len(test):
            raise ValueError(f"{gate}: số quyết định không khớp.")
        if not np.isin(
            decisions, ["PASS", "FILTERED", "FLAGGED"]
        ).all():
            raise ValueError(f"{gate}: quyết định không hợp lệ.")

        # Báo động chỉ được tính nếu mẫu không bị FILTERED.
        effective_alarm = alarms & (decisions != "FILTERED")
        g1_alarms = int((effective_alarm & g1_mask).sum())
        other_alarms = int((effective_alarm & ~g1_mask).sum())
        total_alarms = g1_alarms + other_alarms

        r_g1 = g1_alarms / n_g1
        r_other = other_alarms / n_other
        g1_ci_low, g1_ci_high = M.Rate(
            g1_alarms, n_g1
        ).wilson()

        ftr_observed = (
            g1_alarms / total_alarms
            if total_alarms else np.nan
        )
        ftr_normalized = standardized_ftr(
            r_g1, r_other, prevalence
        )

        # Khi thay prevalence bằng tỷ lệ G1 thực tế,
        # công thức chuẩn hóa phải trả lại FTR quan sát.
        reconstructed = standardized_ftr(
            r_g1, r_other, n_g1 / len(test)
        )
        if not np.isclose(
            reconstructed, ftr_observed, equal_nan=True
        ):
            raise AssertionError("FTR không khớp số đếm.")

        summaries.append({
            "gate": gate,
            "n_test": len(test),
            "n_g1": n_g1,
            "g1_alarm_count": g1_alarms,
            "g1_alarm_rate": r_g1,
            "g1_alarm_ci_low": g1_ci_low,
            "g1_alarm_ci_high": g1_ci_high,
            "n_other": n_other,
            "other_alarm_count": other_alarms,
            "other_alarm_rate": r_other,
            "total_alarm_count": total_alarms,
            "g1_prevalence_observed": n_g1 / len(test),
            "ftr_observed": ftr_observed,
            "g1_prevalence_assumed": prevalence,
            "ftr_standardized": ftr_normalized,
            "prevalence_definition": "P(group=G1)",
            "other_mix": "observed G0/G2/G3 proportions within non-G1",
            "split": "test",
            "d1_threshold": float(threshold),
            "dataset": dataset_path.name,
        })

        for group in ["G0", "G1", "G2", "G3"]:
            mask = test["group"].eq(group).to_numpy()
            n = int(mask.sum())
            count = int((effective_alarm & mask).sum())
            group_rows.append({
                "gate": gate,
                "group": group,
                "n": n,
                "alarm_count_after_filter": count,
                "alarm_rate_after_filter": count / n if n else np.nan,
                "n_filtered": int(
                    ((decisions == "FILTERED") & mask).sum()
                ),
                "split": "test",
            })

    summary = pd.DataFrame(summaries)
    breakdown = pd.DataFrame(group_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "ftr_prevalence_standardized.csv"
    groups_path = out_dir / "ftr_prevalence_by_group.csv"
    summary.to_csv(summary_path, index=False)
    breakdown.to_csv(groups_path, index=False)

    print(summary[[
        "gate", "g1_alarm_count", "n_g1", "g1_alarm_rate",
        "other_alarm_count", "ftr_observed",
        "g1_prevalence_assumed", "ftr_standardized",
    ]].to_string(index=False))
    print(
        "\nPrevalence = tỷ lệ G1; không phải tổng tỷ lệ pack."
    )
    print(
        "FTR chuẩn hóa giữ cơ cấu G0/G2/G3 của phần non-G1 "
        "trong test; không gắn Wilson CI trực tiếp cho tỷ lệ có trọng số."
    )
    print(f"Đã lưu: {summary_path}")
    print(f"Đã lưu: {groups_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path,
        default=ROOT / "dataset_v1.1.csv",
    )
    parser.add_argument(
        "--config", type=Path,
        default=ROOT / "config" / "thresholds.locked.json",
    )
    parser.add_argument(
        "--die-real", type=Path,
        default=ROOT / "results" / "die_real_v1.1.csv",
    )
    parser.add_argument("--prevalence", type=float, default=0.3)
    parser.add_argument(
        "--out-dir", type=Path,
        default=ROOT / "results",
    )
    args = parser.parse_args()
    run(
        args.dataset, args.config, args.die_real,
        args.prevalence, args.out_dir,
    )


if __name__ == "__main__":
    main()