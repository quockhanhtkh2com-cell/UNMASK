"""E5 — Quét ngưỡng packed_score để vẽ đường cong FTR/FNR — Đ3.

Quét ngưỡng F3 từ 0.05 → 0.95 (bước 0.05, 19 điểm) trên tập pack 50%.
Tính FTR, FNR_e2e_G2, FNR_e2e_G3 cho mỗi ngưỡng.

Output: results/e5_sweep.csv
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
import f1_die, f2_rule
from detector import DriftDetector
from unmask.filter import load_filter, UnmaskFilter
from unmask.packed_score import PackedScorer


def e5_sweep(dataset_path: str, f3_config_path: str, out_csv: str, seed: int = 0):
    """Quét F3 threshold trên tập pack 50%."""
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
    GATES = ["F0", "F1", "F2", "F3"]  # F0-F2 không phụ thuộc vào threshold F3

    # Lấy D1 detector
    g0_train = df[(df.group == "G0") & (df.split == "train")][FEATURE_NUM].to_numpy(float)
    g0_val = df[(df.group == "G0") & (df.split == "val")][FEATURE_NUM].to_numpy(float)
    det = DriftDetector(method="mahalanobis", seed=seed, standardize=True).fit(g0_train)
    det.lock_threshold(g0_val, p=80)

    # Chuẩn bị tập test với pack 50%
    df_test = df[df.split == "test"].reset_index(drop=True)
    if len(df_test) == 0:
        df_test = df

    # Subsample 50% pack
    packed = df_test[df_test.group.isin(["G1", "G3"]) | df_test.variant.isin(["P-low", "P-wild"])]
    clean = df_test[~df_test.index.isin(packed.index)]
    n_total = 250
    n_packed = int(round(0.5 * n_total))
    n_clean = n_total - n_packed
    if len(packed) >= n_packed and len(clean) >= n_clean:
        sample = pd.concat([packed.sample(n_packed, random_state=seed),
                            clean.sample(n_clean, random_state=seed)])
        sample = sample.reset_index(drop=True)
    else:
        sample = df_test

    # Nạp F3 config
    if not os.path.exists(f3_config_path):
        print(f"Warning: F3 config not found at {f3_config_path}"); return

    with open(f3_config_path, encoding="utf-8") as f:
        cfg = json.load(f)

    # Quét threshold
    thresholds = [0.05 + 0.05*i for i in range(19)]  # 0.05, 0.10, ..., 0.95
    rows = []

    for threshold in thresholds:
        # Tạo scorer với ngưỡng mới
        cfg_mod = cfg.copy()
        cfg_mod["packed_score"] = cfg_mod.get("packed_score", {})
        cfg_mod["packed_score"]["threshold"] = threshold
        scorer = PackedScorer.load(cfg_mod)

        # F3 với dual-check
        from unmask.dual_check import DualCheck
        dual = DualCheck.from_config(cfg_mod.get("dual_check"))
        f3_filter = UnmaskFilter(scorer, dual=dual, use_dualcheck=True)

        # Tính decisions
        dec_f3 = [f3_filter.decide(r)["decision"] for r in sample.to_dict("records")]

        # Tính metrics
        X_sample = sample[FEATURE_NUM].to_numpy(float)
        alarms = det.predict(X_sample)

        ftr_rate = M.ftr(dec_f3, list(sample.group), alarms)
        fnr_g2_e2e = M.fnr_end2end(dec_f3, alarms, list(sample.group), "G2")
        fnr_g3_e2e = M.fnr_end2end(dec_f3, alarms, list(sample.group), "G3")

        rows.append({
            "threshold": round(threshold, 2),
            "FTR": round(ftr_rate.value, 4),
            "FNR_e2e_G2": round(fnr_g2_e2e.value, 4),
            "FNR_e2e_G3": round(fnr_g3_e2e.value, 4),
        })

    df_sweep = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    df_sweep.to_csv(out_csv, index=False)
    print(df_sweep.to_string(index=False))
    print(f"[e5_sweep] -> {out_csv}")
    return df_sweep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset_v1.1.csv")
    ap.add_argument("--f3-config", default="config/thresholds.locked.json")
    ap.add_argument("--out", default="results/e5_sweep.csv")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    e5_sweep(args.dataset, args.f3_config, args.out, seed=args.seed)


if __name__ == "__main__":
    main()
