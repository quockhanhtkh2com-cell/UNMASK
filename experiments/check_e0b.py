"""E0b — Kiểm tra độ nhạy chuông báo drift D1 trên nhóm G2 (với cổng F0) — [Đức].

Tiêu chí đạt (PASS): Chuông D1 phải báo drift trên phần lớn G2 (alarm_rate >= 50%).
Nếu FAIL: dừng, báo nhóm vì các chỉ số FNR/FTR sau đó sẽ không còn ý nghĩa.

Chạy:
    python experiments/check_e0b.py --dataset dataset_v1.1.csv --config config/thresholds.locked.json
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import pandas as pd
import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, ".."))
from detector import DriftDetector  # noqa: E402
import schema_cols as S            # noqa: E402
import eval_metrics as M           # noqa: E402

FEATURE_NUM = [c for c in S.FEATURE_COLS if c != "section_name_class"]


def check_e0b(dataset_path: str, config_path: str | None = None, p: float = 80,
              min_sensitivity: float = 0.5) -> dict:
    df = pd.read_csv(dataset_path)

    g0_train = df[(df.group == "G0") & (df.split == "train")][FEATURE_NUM].to_numpy(float)
    g0_val = df[(df.group == "G0") & (df.split == "val")][FEATURE_NUM].to_numpy(float)

    if len(g0_train) == 0:
        g0_train = df[df.group == "G0"][FEATURE_NUM].to_numpy(float)
    if len(g0_val) == 0:
        g0_val = g0_train

    det = DriftDetector(method="mahalanobis", seed=0, standardize=True).fit(g0_train)

    if config_path and os.path.exists(config_path):
        cfg = json.load(open(config_path, encoding="utf-8"))
        d1_cfg = cfg.get("detector_D1", {})
        if d1_cfg.get("threshold_value"):
            det.threshold = float(d1_cfg["threshold_value"])
        else:
            det.lock_threshold(g0_val, p=p)
    else:
        det.lock_threshold(g0_val, p=p)

    df_test = df[df.split == "test"].reset_index(drop=True)
    if len(df_test) == 0:
        df_test = df

    g2_samples = df_test[df_test.group == "G2"]
    X_g2 = g2_samples[FEATURE_NUM].to_numpy(float)
    alarms_g2 = det.predict(X_g2)
    n_alarms_g2 = sum(alarms_g2)
    n_total_g2 = len(g2_samples)
    sensitivity_g2 = n_alarms_g2 / n_total_g2 if n_total_g2 > 0 else 0.0

    # Kiểm tra thêm trên G0 test (false alarm rate trên mẫu sạch)
    g0_samples = df_test[df_test.group == "G0"]
    X_g0 = g0_samples[FEATURE_NUM].to_numpy(float)
    alarms_g0 = det.predict(X_g0)
    fa_rate_g0 = sum(alarms_g0) / len(g0_samples) if len(g0_samples) > 0 else 0.0

    passed = sensitivity_g2 >= min_sensitivity

    res = {
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "threshold": det.threshold,
        "n_alarms_g2": n_alarms_g2,
        "n_total_g2": n_total_g2,
        "sensitivity_g2": sensitivity_g2,
        "false_alarm_rate_g0": fa_rate_g0,
        "min_required": min_sensitivity,
    }

    print("=" * 60)
    print(f"KIỂM TRA E0b — ĐỘ NHẠY CHUÔNG D1 TRÊN DRIFT THẬT (G2)")
    print("=" * 60)
    print(f"Ngưỡng D1:                 {det.threshold:.5f}")
    print(f"Số mẫu G2 báo drift:       {n_alarms_g2}/{n_total_g2} ({sensitivity_g2:.1%})")
    print(f"Tiêu chuẩn tối thiểu:      >= {min_sensitivity:.1%}")
    print(f"Báo nhầm trên G0 sạch:     {sum(alarms_g0)}/{len(g0_samples)} ({fa_rate_g0:.1%})")
    print(f"Kết luận E0b:              [{res['status']}]")
    print("=" * 60)

    if not passed:
        print("[CẢNH BÁO] Chuông D1 chưa đủ nhạy trên G2! Cần kiểm tra lại chuẩn hóa/ngưỡng.")

    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset_v1.1.csv")
    ap.add_argument("--config", default="config/thresholds.locked.json")
    ap.add_argument("--p", type=float, default=80)
    ap.add_argument("--min-sensitivity", type=float, default=0.5)
    args = ap.parse_args()
    res = check_e0b(args.dataset, args.config, args.p, args.min_sensitivity)
    sys.exit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
