"""M5 (Gop_y_G1.pdf) - Kiem chung gia dinh "loi chua dong goi" cho G0 va G2 bang DiE that.

Giang vien nghi ngo:
  - 39 mau AgentTesla "native" trong G0 co the la loader/crypter boc ngoai.
  - Luat entropy>7 bac bo 35/53 mau G0 chi vi bang import "day du", nhung crypter .NET
    thuong giu nguyen import va giau payload trong resource.
  - G2 khong duoc quet (Emotet, Formbook thuong bi crypt san khi phat tan), nen G3 co
    the la dong goi 2 lop.

Du lieu DiE THAT da co san (results/die_real_v1.1.csv, quet toan bo 596 mau, gom ca
G0 va G2) - KHONG can quet lai. Script nay chi doi chieu:
  - G0: 12/122 mau (.NET AgentTesla) bi DiE gan nhan "protected" (.NET Reactor,
    Control Flow + Anti-ILDASM) - DUNG nhu giang vien nghi ngo cho nhanh .NET.
    39 mau "native" (is_dotnet=0) thi 100% "clean" - BAC BO nghi ngo cho nhanh native.
  - G2: 2/165 mau bi gan nhan "packed" that (azorult, lokibot - UPX) va 5/165 mau
    "protected" (1 emotet, 4 formbook) - dung nhu giang vien du doan ve Emotet/Formbook.

Script fit lai D1 va cham lai gate F3 tren TAP "SACH DA XAC MINH" (loai het mau
protected/packed khoi G0 train+val+test va G2 test), roi so sanh FNR_G3/FNR_e2e voi
TAP DAY DU (hien dang dung, khong doi) - dung dung yeu cau M5: "bao cao lai ket qua
theo hai tap".

    python experiments/m5_verified_clean_check.py
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
from detector import DriftDetector       # noqa: E402

FEATURE_NUM = None  # gan sau khi import schema_cols


def _load(dataset_path: str):
    import pandas as pd
    df = pd.read_csv(dataset_path)
    die_candidates = [
        os.path.join("results", "die_real_v1.1.csv"),
        os.path.join(HERE, "..", "results", "die_real_v1.1.csv"),
        os.path.join(os.path.dirname(dataset_path), "die_real_v1.1.csv"),
        "die_real_v1.1.csv",
    ]
    die_path = next((c for c in die_candidates if c and os.path.exists(c)), None)
    if not die_path:
        raise FileNotFoundError(f"Khong tim thay die_real_v1.1.csv. Da tim: {die_candidates}")
    die = pd.read_csv(die_path)
    df = df.merge(die[["sha256", "die_result_real"]], on="sha256", how="left")
    return df


def _clean_mask(df):
    """True = mau 'sach da xac minh' theo M5 (loai G0-protected va G2-packed/protected).
    G1, G3 giu nguyen - M5 chi dat nghi van ve gia dinh 'loi chua dong goi' cua G0/G2,
    khong dat nghi van ve G1/G3 (von da duoc gan la 'da dong goi' tu dau)."""
    bad_g0 = (df.group == "G0") & (df.die_result_real == "protected")
    bad_g2 = (df.group == "G2") & (df.die_result_real.isin(["packed", "protected"]))
    return ~(bad_g0 | bad_g2)


def run(dataset_path: str, f3_config_path: str, out_csv: str):
    global FEATURE_NUM
    FEATURE_NUM = [c for c in S.FEATURE_COLS if c != "section_name_class"]

    df = _load(dataset_path)
    clean_mask = _clean_mask(df)

    n_g0_bad = ((df.group == "G0") & ~clean_mask).sum()
    n_g2_bad = ((df.group == "G2") & ~clean_mask).sum()
    print(f"[m5] Loai {n_g0_bad} mau G0 (protected, .NET Reactor) va "
          f"{n_g2_bad} mau G2 (packed/protected that) khoi tap 'sach da xac minh'.")

    cfg = json.load(open(f3_config_path, encoding="utf-8"))
    p_lock = float(cfg.get("detector_D1", {}).get("percentile", 80))
    f3 = load_filter(f3_config_path, use_dualcheck=True)

    rows = []
    for label, df_scope in [("Tap day du (hien dung)", df),
                             ("Tap sach da xac minh (M5)", df[clean_mask].reset_index(drop=True))]:
        g0_train = df_scope[(df_scope.group == "G0") & (df_scope.split == "train")][FEATURE_NUM].to_numpy(float)
        g0_val = df_scope[(df_scope.group == "G0") & (df_scope.split == "val")][FEATURE_NUM].to_numpy(float)
        df_test = df_scope[df_scope.split == "test"].reset_index(drop=True)

        det = DriftDetector(method="mahalanobis", seed=0, standardize=True).fit(g0_train)
        det.lock_threshold(g0_val, p=p_lock)
        alarms_test = det.predict(df_test[FEATURE_NUM].to_numpy(float))

        dec_f3 = [f3.decide(r)["decision"] for r in df_test.to_dict("records")]
        groups = list(df_test.group)

        rows.append({
            "tap_du_lieu": label,
            "n_G0_train": len(g0_train), "n_G0_val": len(g0_val),
            "n_test": len(df_test),
            "threshold_D1": round(det.threshold, 4),
            "FNR_G2_filter_F3": round(M.fnr(dec_f3, groups, "G2").value, 4),
            "FNR_G3_filter_F3": round(M.fnr(dec_f3, groups, "G3").value, 4),
            "FNR_e2e_G2_F3": round(M.fnr_end2end(dec_f3, alarms_test, groups, "G2").value, 4),
            "FNR_e2e_G3_F3": round(M.fnr_end2end(dec_f3, alarms_test, groups, "G3").value, 4),
        })

    import pandas as pd
    df_out = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    df_out.to_csv(out_csv, index=False)
    print()
    print(df_out.to_string(index=False))
    print(f"[m5_verified_clean_check] -> {out_csv}")
    print()
    print("Dien giai: so sanh 2 dong de xem gia dinh 'loi G0/G2 chua dong goi' co anh")
    print("huong toi ket luan chinh (FNR_G3 cua F3) hay khong. Neu lech it, ket luan")
    print("van dung vung sau khi loai mau nghi nhiem (.NET Reactor / UPX / crypt san).")
    return df_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset_v1.1.csv")
    ap.add_argument("--f3-config", default="config/thresholds.locked.json")
    ap.add_argument("--out", default="results/m5_verified_clean_check.csv")
    args = ap.parse_args()
    run(args.dataset, args.f3_config, args.out)


if __name__ == "__main__":
    main()
