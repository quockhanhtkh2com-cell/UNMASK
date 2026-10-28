"""E6 — Phân tích FNR_G3 theo packer và gia đình malware — Đ4.

Tách kết quả trên 404 mẫu test theo:
- Packer (UPX vs MPRESS)
- Platform (native vs .NET)
- Gia đình (từ family column)

Output: results/e6_per_packer.csv, results/e6_per_family.csv
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
import schema_cols as S
import eval_metrics as M
from detector import DriftDetector
from unmask.filter import load_filter


def e6_breakdown(dataset_path: str, f3_config_path: str, out_packer: str, out_family: str, seed: int = 0):
    """Phân tích FNR theo packer + platform + family."""
    import pandas as pd

    df = pd.read_csv(dataset_path)
    if "die_result" not in df.columns:
        mf_path = os.path.join(os.path.dirname(dataset_path), "manifest_v1.1.csv")
        if not os.path.exists(mf_path):
            mf_path = "manifest_v1.1.csv"
        if os.path.exists(mf_path):
            mf = pd.read_csv(mf_path)
            if "die_result" in mf.columns and "sha256" in mf.columns:
                df = df.merge(mf[["sha256", "die_result"]], on="sha256", how="left")

    FEATURE_NUM = [c for c in S.FEATURE_COLS if c != "section_name_class"]

    # Lấy D1 detector
    g0_train = df[(df.group == "G0") & (df.split == "train")][FEATURE_NUM].to_numpy(float)
    g0_val = df[(df.group == "G0") & (df.split == "val")][FEATURE_NUM].to_numpy(float)
    det = DriftDetector(method="mahalanobis", seed=seed, standardize=True).fit(g0_train)
    det.lock_threshold(g0_val, p=80)

    # Tập test 404 mẫu
    df_test = df[df.split == "test"].reset_index(drop=True)
    if len(df_test) == 0:
        df_test = df

    # Nạp F3
    f3 = load_filter(f3_config_path, use_dualcheck=True)

    # Tính decisions F3 trên 404 mẫu test
    dec_f3 = [f3.decide(r)["decision"] for r in df_test.to_dict("records")]
    X_test = df_test[FEATURE_NUM].to_numpy(float)
    alarms = det.predict(X_test)

    # ===== E6 per packer =====
    # Lọc G3 samples theo packer type + platform
    packer_groups = {}

    if "packer" in df_test.columns:
        for packer_val in df_test[df_test.group == "G3"]["packer"].dropna().unique():
            packer_groups[f"packer={packer_val}"] = df_test[(df_test.group == "G3") & (df_test.packer == packer_val)]

    if "is_dotnet" in df_test.columns:
        packer_groups["native"] = df_test[(df_test.group == "G3") & (df_test.is_dotnet == 0)]
        packer_groups[".NET"] = df_test[(df_test.group == "G3") & (df_test.is_dotnet == 1)]

    if not packer_groups:
        packer_groups["All G3"] = df_test[df_test.group == "G3"]

    rows_packer = []
    for category, packer_df in packer_groups.items():
        if len(packer_df) == 0:
            continue
        idx = packer_df.index
        dec_sub = [dec_f3[i] for i in idx]
        alarm_sub = [alarms[i] for i in idx]

        # FNR_G3: missed / total
        g3_missed = sum(1 for d, alarm in zip(dec_sub, alarm_sub)
                       if d == "FILTERED" or not alarm)
        fnr_g3 = g3_missed / len(packer_df)

        # Wilson CI
        rate = M.Rate(g3_missed, len(packer_df))
        ci_lo, ci_hi = rate.wilson()

        rows_packer.append({
            "category": category,
            "n": len(packer_df),
            "FNR_G3": round(fnr_g3, 4),
            "CI_lo": round(ci_lo, 4),
            "CI_hi": round(ci_hi, 4),
        })

    # ===== E6 per family =====
    # Phân tích theo malware family
    rows_family = []
    if "family" in df_test.columns:
        families = sorted(df_test[df_test.group == "G3"]["family"].dropna().unique())
        for fam in families:
            fam_df = df_test[(df_test.group == "G3") & (df_test.family == fam)]
            if len(fam_df) == 0:
                continue
            idx = fam_df.index
            dec_sub = [dec_f3[i] for i in idx]
            alarm_sub = [alarms[i] for i in idx]

            g3_missed = sum(1 for d, alarm in zip(dec_sub, alarm_sub)
                           if d == "FILTERED" or not alarm)
            fnr_g3 = g3_missed / len(fam_df)

            rate = M.Rate(g3_missed, len(fam_df))
            ci_lo, ci_hi = rate.wilson()

            rows_family.append({
                "family": str(fam),
                "n": len(fam_df),
                "FNR_G3": round(fnr_g3, 4),
                "CI_lo": round(ci_lo, 4),
                "CI_hi": round(ci_hi, 4),
            })

    df_packer = pd.DataFrame(rows_packer)
    df_family = pd.DataFrame(rows_family)

    os.makedirs(os.path.dirname(out_packer) or ".", exist_ok=True)
    df_packer.to_csv(out_packer, index=False)
    if len(rows_family) > 0:
        df_family.to_csv(out_family, index=False)

    print("=== Per Packer/Platform ===")
    print(df_packer.to_string(index=False))
    print(f"\n[e6_per_packer] -> {out_packer}")

    if len(rows_family) > 0:
        print("\n=== Per Family ===")
        print(df_family.to_string(index=False))
        print(f"\n[e6_per_family] -> {out_family}")
    else:
        print("\n[e6_per_family] No family column found")

    return df_packer, df_family


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset_v1.1.csv")
    ap.add_argument("--f3-config", default="config/thresholds.locked.json")
    ap.add_argument("--out-packer", default="results/e6_per_packer.csv")
    ap.add_argument("--out-family", default="results/e6_per_family.csv")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    e6_breakdown(args.dataset, args.f3_config, args.out_packer, args.out_family, seed=args.seed)


if __name__ == "__main__":
    main()
