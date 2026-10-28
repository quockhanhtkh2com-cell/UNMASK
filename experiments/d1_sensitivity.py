"""Phân tích độ nhạy D1 với các percentile khác nhau — Đ6.

Chạy D1 ở các ngưỡng P80 (hiện tại), P85, P90, P95 và so sánh:
- Threshold value
- % bắt G2 (FNR_G2)
- % báo nhầm G0 (flagged_rate trên val + test)

Output: results/d1_sensitivity.csv
"""
from __future__ import annotations
import argparse
import json
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, ".."))
import schema_cols as S
import eval_metrics as M
from detector import DriftDetector


def compute_sensitivity(dataset_path: str, f3_config_path: str, out_csv: str):
    """Tính độ nhạy cho các percentile khác nhau."""
    import pandas as pd

    df = pd.read_csv(dataset_path)
    if "die_result_real" not in df.columns:
        die_real_path = os.path.join(os.path.dirname(dataset_path), "die_real_v1.1.csv")
        if not os.path.exists(die_real_path):
            die_real_path = "die_real_v1.1.csv"
        if os.path.exists(die_real_path):
            die_real = pd.read_csv(die_real_path)
            if "die_result_real" in die_real.columns and "sha256" in die_real.columns:
                df = df.merge(die_real[["sha256", "die_result_real"]], on="sha256", how="left")

    FEATURE_NUM = [c for c in S.FEATURE_COLS if c != "section_name_class"]

    # Tách tập val và test
    g0_train = df[(df.group == "G0") & (df.split == "train")][FEATURE_NUM].to_numpy(float)
    g0_val = df[(df.group == "G0") & (df.split == "val")][FEATURE_NUM].to_numpy(float)
    df_val = df[df.split == "val"].reset_index(drop=True)
    df_test = df[df.split == "test"].reset_index(drop=True)
    if len(df_test) == 0:
        df_test = df
    if len(df_val) == 0:
        df_val = df

    # Khởi tạo detector (base)
    det = DriftDetector(method="mahalanobis", seed=0, standardize=True).fit(g0_train)

    # Tính ngưỡng cho các percentile
    percentiles = [80, 85, 90, 95]
    rows = []

    for p in percentiles:
        det_p = DriftDetector(method="mahalanobis", seed=0, standardize=True).fit(g0_train)
        det_p.lock_threshold(g0_val, p=p)
        threshold = det_p.threshold

        # Chạy chuông trên val + test
        X_val = df_val[FEATURE_NUM].to_numpy(float)
        X_test = df_test[FEATURE_NUM].to_numpy(float)
        alarms_val = det_p.predict(X_val)
        alarms_test = det_p.predict(X_test)

        # Tính metrics trên val
        g0_val_full = list(df_val[df_val.group == "G0"].index)
        g2_val_full = list(df_val[df_val.group == "G2"].index)

        # False alarm rate trên G0 (val)
        false_alarms_val = sum(1 for i, alarm in enumerate(alarms_val)
                               if df_val.iloc[i].group == "G0" and alarm)
        n_g0_val = len(g0_val_full)
        false_alarm_rate_val = false_alarms_val / n_g0_val if n_g0_val > 0 else 0.0

        # Detection rate trên G2 (test)
        detected_g2_test = sum(1 for i, alarm in enumerate(alarms_test)
                               if df_test.iloc[i].group == "G2" and alarm)
        n_g2_test = len(df_test[df_test.group == "G2"])
        detection_rate_g2 = detected_g2_test / n_g2_test if n_g2_test > 0 else 0.0

        # False alarm rate trên G0 (test)
        false_alarms_test = sum(1 for i, alarm in enumerate(alarms_test)
                                if df_test.iloc[i].group == "G0" and alarm)
        n_g0_test = len(df_test[df_test.group == "G0"])
        false_alarm_rate_test = false_alarms_test / n_g0_test if n_g0_test > 0 else 0.0

        rows.append({
            "percentile": p,
            "threshold": round(threshold, 4),
            "detect_rate_G2_test": round(detection_rate_g2, 4),
            "false_alarm_G0_val": round(false_alarm_rate_val, 4),
            "false_alarm_G0_test": round(false_alarm_rate_test, 4),
            "n_G0_val": n_g0_val,
            "n_G2_test": n_g2_test,
            "n_G0_test": n_g0_test,
        })

    df_sens = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    df_sens.to_csv(out_csv, index=False)
    print(df_sens.to_string(index=False))
    print(f"[d1_sensitivity] -> {out_csv}")
    return df_sens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset_v1.1.csv")
    ap.add_argument("--f3-config", default="config/thresholds.locked.json")
    ap.add_argument("--out", default="results/d1_sensitivity.csv")
    args = ap.parse_args()
    compute_sensitivity(args.dataset, args.f3_config, args.out)


if __name__ == "__main__":
    main()
