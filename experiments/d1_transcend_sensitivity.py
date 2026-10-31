"""M4 (Gop_y_G1.pdf) - So sanh D1 (Mahalanobis + percentile) voi D2
(Transcend-style conformal p-value, Jordaney et al. USENIX Sec 2017) - sensitivity check.

Giang vien de nghi thu them it nhat 1 bo phat hien drift chuan cua linh vuc (CADE hay
Transcend/Transcendent), roi kiem tra ket luan ve cac cong loc (F3) co con dung vung
khi thay D1 hay khong.

Script nay KHONG dong den D1 chinh/bang_chinh.csv da chot - chi chay D2 RIENG, tren
CUNG mot test set, roi so sanh FNR_G3/FNR_e2e cua gate F3 giua D1 va D2.

    python experiments/d1_transcend_sensitivity.py
"""
from __future__ import annotations
import argparse
import json
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, ".."))
import schema_cols as S            # noqa: E402
import eval_metrics as M           # noqa: E402
from unmask.filter import load_filter    # noqa: E402
from detector import DriftDetector, TranscendPValueDetector  # noqa: E402


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
    df_test = df[df.split == "test"].reset_index(drop=True)
    if len(df_test) == 0:
        df_test = df

    # Quyet dinh cua gate F3 KHONG phu thuoc D1/D2 (chi phu thuoc packed_score) -
    # chi tinh 1 lan, dung chung cho ca 2 kich ban.
    f3 = load_filter(f3_config_path, use_dualcheck=True)
    dec_f3 = [f3.decide(r)["decision"] for r in df_test.to_dict("records")]
    groups = list(df_test.group)

    cfg = json.load(open(f3_config_path, encoding="utf-8"))
    p_lock = float(cfg.get("detector_D1", {}).get("percentile", 80))
    alpha_equiv = round(1.0 - p_lock / 100.0, 4)  # P80 <-> alpha=0.2, de so sanh cong bang

    rows = []

    # --- D1: Mahalanobis + percentile (hien tai, production) ---
    d1 = DriftDetector(method="mahalanobis", seed=0, standardize=True).fit(g0_train)
    d1.lock_threshold(g0_val, p=p_lock)
    alarms_d1 = d1.predict(df_test[FEATURE_NUM].to_numpy(float))
    rows.append({
        "detector": "D1 (Mahalanobis + percentile, hien tai)",
        "threshold_or_alpha": round(d1.threshold, 4),
        "FNR_G3_filter_F3": round(M.fnr(dec_f3, groups, "G3").value, 4),
        "FNR_e2e_G3_F3": round(M.fnr_end2end(dec_f3, alarms_d1, groups, "G3").value, 4),
        "FNR_e2e_G2_F3": round(M.fnr_end2end(dec_f3, alarms_d1, groups, "G2").value, 4),
    })

    # --- D2: Mahalanobis + Transcend-style conformal p-value (moi, sensitivity check) ---
    d2 = TranscendPValueDetector(seed=0, standardize=True).fit(g0_train)
    d2.lock_threshold(g0_val, alpha=alpha_equiv)
    alarms_d2 = d2.predict(df_test[FEATURE_NUM].to_numpy(float))
    rows.append({
        "detector": "D2 (Mahalanobis + p-value Transcend, M4)",
        "threshold_or_alpha": d2.alpha,
        "FNR_G3_filter_F3": round(M.fnr(dec_f3, groups, "G3").value, 4),
        "FNR_e2e_G3_F3": round(M.fnr_end2end(dec_f3, alarms_d2, groups, "G3").value, 4),
        "FNR_e2e_G2_F3": round(M.fnr_end2end(dec_f3, alarms_d2, groups, "G2").value, 4),
    })

    df_out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    df_out.to_csv(out_csv, index=False)
    print(df_out.to_string(index=False))
    print(f"[d1_transcend_sensitivity] -> {out_csv}")
    print()
    print(f"alpha tuong duong voi P{p_lock:.0f} hien tai: alpha = 1 - {p_lock:.0f}/100 = {alpha_equiv}")
    print("Dien giai: FNR_G3_filter_F3 KHONG doi vi quyet dinh cua gate F3 khong phu")
    print("thuoc D1/D2. Chi FNR_e2e_* (phu thuoc chuong co keu hay khong) co the doi")
    print("giua 2 dong - neu lech it, ket luan ve F3 van dung vung khi thay D1 bang D2.")
    return df_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset_v1.1.csv")
    ap.add_argument("--f3-config", default="config/thresholds.locked.json")
    ap.add_argument("--out", default="results/d1_transcend_sensitivity.csv")
    args = ap.parse_args()
    run(args.dataset, args.f3_config, args.out)


if __name__ == "__main__":
    main()
