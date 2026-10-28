"""Driver thí nghiệm E0b, E1–E6 — [Đức]. Chạy 4 cổng (F0–F3) trên cùng dữ liệu,
cùng 1 chuông D1, xuất results_<e>_<seed>_<tilepack>.csv.

    python experiments/run_experiments.py --exp e2 --dataset mock/mock_dataset.csv \\
        --seed 0 --pack-ratio 0.5

Khung đã chạy được trên mock. Chỗ cần hoàn thiện ghi # TODO(Đức).
"""
from __future__ import annotations
import argparse
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "unmask"))  # train.py import packed_score/dual_check phang
import schema_cols as S          # noqa: E402
import eval_metrics as M         # noqa: E402
import f1_die, f2_rule           # noqa: E402
from detector import DriftDetector  # noqa: E402
from unmask.filter import UnmaskFilter, load_filter  # noqa: E402

GATES = ["F0", "F1", "F2", "F3", "F3a"]
FEATURE_NUM = [c for c in S.FEATURE_COLS if c != "section_name_class"]


def _load_dataset(dataset_path: str, manifest_path: str | None = None):
    import pandas as pd
    df = pd.read_csv(dataset_path)
    if "die_result" not in df.columns:
        mf_path = manifest_path
        if not mf_path:
            candidates = [
                dataset_path.replace("dataset", "manifest"),
                os.path.join(os.path.dirname(dataset_path), "manifest_v1.1.csv"),
                "manifest_v1.1.csv",
            ]
            for c in candidates:
                if os.path.exists(c):
                    mf_path = c
                    break
        if mf_path and os.path.exists(mf_path):
            mf = pd.read_csv(mf_path)
            if "die_result" in mf.columns and "sha256" in mf.columns:
                df = df.merge(mf[["sha256", "die_result"]], on="sha256", how="left")
    return df


def _subsample_to_ratio(df, pack_ratio: float, seed: int):
    """Điều chỉnh tỉ lệ mẫu pack trong dữ liệu đưa vào chuông = pack_ratio.

    Dùng fixed N=250 để đảm bảo tỉ lệ thực = tỉ lệ yêu cầu:
    - 0.3 → 75 packed + 175 clean
    - 0.5 → 125 packed + 125 clean
    - 0.7 → 175 packed + 75 clean
    """
    import pandas as pd
    packed = df[df.group.isin(["G1", "G3"]) | df.variant.isin(["P-low", "P-wild"])]
    clean = df[~df.index.isin(packed.index)]
    if len(packed) == 0 or len(clean) == 0:
        return df

    n_total = 250  # Fixed total samples
    n_packed = int(round(pack_ratio * n_total))
    n_clean = n_total - n_packed

    if len(packed) < n_packed or len(clean) < n_clean:
        return df  # Not enough samples, return full df

    out = pd.concat([packed.sample(n_packed, random_state=seed),
                     clean.sample(n_clean, random_state=seed)])
    return out.reset_index(drop=True)


def _build_f3(dataset: str, f3_config: str | None, seed: int, use_dualcheck: bool = True):
    import tempfile
    from unmask.filter import _load_locked
    if f3_config or _load_locked():
        return load_filter(f3_config, use_dualcheck=use_dualcheck)
    print("[CẢNH BÁO] chưa có config F3 khoá -> train TẠM từ dataset (số liệu chỉ để chạy thử, "
          "KHÔNG đưa vào báo cáo). Khoá thật: python unmask/train.py --dataset ... --out config/thresholds.locked.json")
    from unmask.train import train
    tmp = os.path.join(tempfile.mkdtemp(), "f3_tmp.json")
    train(dataset, tmp, seed)
    return load_filter(tmp, use_dualcheck=use_dualcheck)


def _gate_decisions(gate: str, df, f3_filter, f3a_filter) -> list[str]:
    if gate == "F0":
        return ["PASS"] * len(df)
    if gate == "F1":
        return f1_die.run(df)
    if gate == "F2":
        return f2_rule.run(df)
    if gate == "F3":
        return [f3_filter.decide(r)["decision"] for r in df.to_dict("records")]
    if gate == "F3a":
        return [f3a_filter.decide(r)["decision"] for r in df.to_dict("records")]
    raise ValueError(gate)


def run(exp: str, dataset: str, seed: int, pack_ratio: float, out_dir: str, detector_method: str = "mahalanobis",
        f3_config: str | None = None, manifest: str | None = None):
    import numpy as np, pandas as pd
    df = _load_dataset(dataset, manifest)

    # chuông D1 CHUNG: fit trên G0 (train), khoá trên G0 (val) hoặc nạp từ f3_config nếu có.
    g0_train = df[(df.group == "G0") & (df.split == "train")][FEATURE_NUM].to_numpy(float)
    g0_val = df[(df.group == "G0") & (df.split == "val")][FEATURE_NUM].to_numpy(float)

    # Fallback an toàn nếu g0_train hoặc g0_val rỗng
    if len(g0_train) == 0:
        g0_train = df[df.group == "G0"][FEATURE_NUM].to_numpy(float)
    if len(g0_val) == 0:
        g0_val = g0_train

    det = DriftDetector(method=detector_method, seed=seed, standardize=True).fit(g0_train)

    # Nạp ngưỡng D1 từ config khoá nếu có, hoặc tính P80 trên G0 val
    cfg_p = f3_config or os.path.join(HERE, "..", "config", "thresholds.locked.json")
    if os.path.exists(cfg_p):
        import json
        cdata = json.load(open(cfg_p, encoding="utf-8"))
        d1_cfg = cdata.get("detector_D1", {})
        if d1_cfg.get("threshold_value"):
            det.threshold = float(d1_cfg["threshold_value"])
        else:
            p_val = d1_cfg.get("percentile", 80)
            det.lock_threshold(g0_val, p=p_val)
    else:
        det.lock_threshold(g0_val, p=80)

    # F3: nạp scorer + dual-check từ config ĐÃ KHOÁ. F3a: ablation không dual-check.
    f3_filter = _build_f3(dataset, f3_config, seed, use_dualcheck=True)
    f3a_filter = _build_f3(dataset, f3_config, seed, use_dualcheck=False)

    # Đánh giá CHỈ trên tập test (404 mẫu test chống rò rỉ)
    df_test = df[df.split == "test"].reset_index(drop=True)
    if len(df_test) == 0:
        df_test = df

    sample = _subsample_to_ratio(df_test, pack_ratio, seed)
    ratio_real = M.pack_ratio(list(sample.group), list(sample.variant))

    # Chạy các cổng trên dữ liệu subsampled (để tính FTR, FNR theo tỉ lệ pack)
    # Nhưng correct_* metrics phải dùng full test set (Đ8) để nhất quán

    rows = []
    for gate in GATES:
        dec_sample = _gate_decisions(gate, sample, f3_filter, f3a_filter)
        X = sample[FEATURE_NUM].to_numpy(float)
        alarms = det.predict(X)   # chuông chạy trên subsampled; FTR bỏ mẫu FILTERED

        # Tính correct_* trên FULL test set cho nhất quán (Đ8)
        dec_full = _gate_decisions(gate, df_test, f3_filter, f3a_filter)

        rows.append({
            "exp": exp, "gate": gate, "seed": seed,
            "pack_ratio_set": pack_ratio, "pack_ratio_real": round(ratio_real, 3),
            "FTR": M.ftr(dec_sample, list(sample.group), alarms).value,
            "FNR_G2": M.fnr(dec_sample, list(sample.group), "G2").value,
            "FNR_G3": M.fnr(dec_sample, list(sample.group), "G3").value,
            "FNR_e2e_G2": M.fnr_end2end(dec_sample, alarms, list(sample.group), "G2").value,
            "FNR_e2e_G3": M.fnr_end2end(dec_sample, alarms, list(sample.group), "G3").value,
            "correct_filter_Pseen": M.correct_filter_rate(dec_full, list(df_test.group), list(df_test.variant), "P-seen").value,
            "correct_filter_Punseen": M.correct_filter_rate(dec_full, list(df_test.group), list(df_test.variant), "P-unseen").value,
            "correct_filter_Plow": M.correct_filter_rate(dec_full, list(df_test.group), list(df_test.variant), "P-low").value,
            "correct_filter_Pwild": M.correct_filter_rate(dec_full, list(df_test.group), list(df_test.variant), "P-wild").value,
            "flagged_rate": M.flagged_rate(dec_full).value,
        })

    out_df = pd.DataFrame(rows)
    os.makedirs(out_dir, exist_ok=True)
    pr_str = f"0_{int(round(pack_ratio*100)):02d}"
    fn = os.path.join(out_dir, f"results_{exp}_{seed}_{pr_str}.csv")
    out_df.to_csv(fn, index=False)
    print(out_df.to_string(index=False))
    print(f"[{exp}] -> {fn}")
    return fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="e2",
                    help="e0b|e1|e2|e3|e4|e5|e6")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--pack-ratio", type=float, default=0.5)
    ap.add_argument("--detector", default="mahalanobis", choices=["mahalanobis", "isolation_forest"])
    ap.add_argument("--f3-config", default=None,
                    help="config F3 đã khoá (mặc định: config/thresholds.locked.json / UNMASK_CONFIG)")
    ap.add_argument("--out-dir", default=os.path.join(HERE, "..", "results"))
    ap.add_argument("--all", action="store_true",
                    help="Chạy toàn bộ lưới (seed: 0,1,2 x pack-ratio: 0.3, 0.5, 0.7)")
    ap.add_argument("--all-exps", action="store_true",
                    help="Chạy toàn bộ thí nghiệm e1..e6")
    args = ap.parse_args()

    exps = ["e1", "e2", "e3", "e4", "e5", "e6"] if args.all_exps else [args.exp]
    seeds = [0, 1, 2] if (args.all or args.all_exps) else [args.seed]
    ratios = [0.3, 0.5, 0.7] if (args.all or args.all_exps) else [args.pack_ratio]

    for e in exps:
        for s in seeds:
            for r in ratios:
                run(e, args.dataset, s, r, args.out_dir, detector_method=args.detector,
                    f3_config=args.f3_config, manifest=args.manifest)


if __name__ == "__main__":
    main()
