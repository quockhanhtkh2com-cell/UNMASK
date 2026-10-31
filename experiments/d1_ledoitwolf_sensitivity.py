"""M4 (Gop_y_G1.pdf) - Kiem tra do nhay cua D1 voi Ledoit-Wolf shrinkage.

Giang vien de nghi: "Dung uoc luong hiep phuong sai co shrinkage (Ledoit-Wolf)"
va "Kiem tra xem ket luan ve cac cong loc co con dung vung khi thay D1 hay khong".

Script nay KHONG thay D1 chinh thuc dang dung trong bang_chinh.csv/.md
(tranh phai chay lai toan bo pipeline + khoa lai nguong, rui ro cao, sat han nop).
Thay vao do, no fit D1-Ledoit-Wolf RIENG, chay tren CUNG mot test set, va so sanh
FNR_G3 cua gate F3 (ket luan chinh cua bai) giua 2 cach uoc luong hiep phuong sai
(sample thuong vs Ledoit-Wolf) de xem ket luan co con dung vung hay khong.

    python experiments/d1_ledoitwolf_sensitivity.py
"""
from __future__ import annotations
import argparse
import json
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "unmask"))
import schema_cols as S          # noqa: E402
import eval_metrics as M         # noqa: E402
import f1_die, f2_rule           # noqa: E402
from unmask.filter import load_filter  # noqa: E402
from detector import DriftDetector     # noqa: E402


def run(dataset_path: str, f3_config_path: str, out_csv: str):
    import pandas as pd

    df = pd.read_csv(dataset_path)
    if "die_result_real" not in df.columns:
        candidates = [
            os.path.join("results", "die_real_v1.1.csv"),
            os.path.join(HERE, "..", "results", "die_real_v1.1.csv"),
            os.path.join(os.path.dirname(dataset_path), "die_real_v1.1.csv"),
            "die_real_v1.1.csv",
        ]
        die_real_path = next((c for c in candidates if c and os.path.exists(c)), None)
        if not die_real_path:
            raise FileNotFoundError(f"Khong tim thay die_real_v1.1.csv. Da tim: {candidates}")
        die_real = pd.read_csv(die_real_path)
        df = df.merge(die_real[["sha256", "die_result_real"]], on="sha256", how="left")

    FEATURE_NUM = [c for c in S.FEATURE_COLS if c != "section_name_class"]

    g0_train = df[(df.group == "G0") & (df.split == "train")][FEATURE_NUM].to_numpy(float)
    g0_val = df[(df.group == "G0") & (df.split == "val")][FEATURE_NUM].to_numpy(float)
    df_val = df[df.split == "val"].reset_index(drop=True)
    df_test = df[df.split == "test"].reset_index(drop=True)
    if len(df_test) == 0:
        df_test = df
    if len(df_val) == 0:
        df_val = df

    # Quyet dinh cua F3/F3a KHONG phu thuoc D1 (chi phu thuoc packed_score) -
    # chi can tinh 1 lan, dung chung cho ca 2 kich ban D1.
    f3 = load_filter(f3_config_path, use_dualcheck=True)
    dec_f3 = [f3.decide(r)["decision"] for r in df_test.to_dict("records")]
    groups = list(df_test.group)

    cfg = json.load(open(f3_config_path, encoding="utf-8"))
    p_lock = float(cfg.get("detector_D1", {}).get("percentile", 80))

    rows = []
    for label, cov_estimator in [("sample (goc, dang dung)", "sample"),
                                  ("ledoit_wolf (M4)", "ledoit_wolf")]:
        det = DriftDetector(method="mahalanobis", seed=0, standardize=True,
                             cov_estimator=cov_estimator).fit(g0_train)
        det.lock_threshold(g0_val, p=p_lock)
        alarms_test = det.predict(df_test[FEATURE_NUM].to_numpy(float))

        fnr_g3 = M.fnr(dec_f3, groups, "G3")
        fnr_e2e_g3 = M.fnr_end2end(dec_f3, alarms_test, groups, "G3")
        fnr_e2e_g2 = M.fnr_end2end(dec_f3, alarms_test, groups, "G2")

        rows.append({
            "cov_estimator": label,
            "shrinkage_coef": round(det.shrinkage_, 4) if det.shrinkage_ is not None else "-",
            "threshold_locked": round(det.threshold, 4),
            "FNR_G3_filter_F3": round(fnr_g3.value, 4),
            "FNR_e2e_G3_F3": round(fnr_e2e_g3.value, 4),
            "FNR_e2e_G2_F3": round(fnr_e2e_g2.value, 4),
        })

    df_out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    df_out.to_csv(out_csv, index=False)
    print(df_out.to_string(index=False))
    print(f"[d1_ledoitwolf_sensitivity] -> {out_csv}")
    print()
    print("Dien giai: FNR_G3_filter_F3 KHONG doi vi quyet dinh cua gate F3 khong phu")
    print("thuoc D1. Chi FNR_e2e_* (phu thuoc chuong D1 co keu hay khong) co the doi")
    print("giua 2 dong - neu lech it, ket luan ve F3 van dung vung khi thay D1.")
    return df_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset_v1.1.csv")
    ap.add_argument("--f3-config", default="config/thresholds.locked.json")
    ap.add_argument("--out", default="results/d1_ledoitwolf_sensitivity.csv")
    args = ap.parse_args()
    run(args.dataset, args.f3_config, args.out)


if __name__ == "__main__":
    main()
