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
import schema_cols as S          # noqa: E402
import eval_metrics as M         # noqa: E402
import f1_die, f2_rule           # noqa: E402
from detector import DriftDetector  # noqa: E402
from unmask.filter import UnmaskFilter  # noqa: E402
from unmask.packed_score import PackedScorer  # noqa: E402
from unmask.dual_check import DualCheck  # noqa: E402

GATES = ["F0", "F1", "F2", "F3"]
FEATURE_NUM = [c for c in S.FEATURE_COLS if c != "section_name_class"]


def _subsample_to_ratio(df, pack_ratio: float, seed: int):
    """Điều chỉnh tỉ lệ mẫu pack trong dữ liệu đưa vào chuông = pack_ratio."""
    import pandas as pd
    packed = df[df.group.isin(["G1", "G3"]) | df.variant.isin(["P-low", "P-wild"])]
    clean = df[~df.index.isin(packed.index)]
    if len(packed) == 0 or len(clean) == 0:
        return df
    n_total = len(df)
    n_packed = min(len(packed), int(round(pack_ratio * n_total)))
    n_clean = min(len(clean), n_total - n_packed)
    out = pd.concat([packed.sample(n_packed, random_state=seed),
                     clean.sample(n_clean, random_state=seed)])
    return out.reset_index(drop=True)


def _gate_decisions(gate: str, df, scorer, dual) -> list[str]:
    if gate == "F0":
        return ["PASS"] * len(df)
    if gate == "F1":
        return f1_die.run(df)
    if gate == "F2":
        return f2_rule.run(df)
    if gate == "F3":
        f = UnmaskFilter(scorer, dual=dual, use_dualcheck=dual is not None)
        return [f.decide(r)["decision"] for r in df.to_dict("records")]
    raise ValueError(gate)


def run(exp: str, dataset: str, seed: int, pack_ratio: float, out_dir: str):
    import numpy as np, pandas as pd
    df = pd.read_csv(dataset)

    # chuông D1 CHUNG: fit trên G0, khoá P95 trên G0 (mock). TODO(Đức): dùng val thật + nền EMBER.
    g0 = df[df.group == "G0"][FEATURE_NUM].to_numpy(float)
    det = DriftDetector(method="mahalanobis", seed=seed).fit(g0)
    det.lock_threshold(g0, p=95)

    # F3 scorer + dual-check
    scorer = PackedScorer()  # TODO(Tuấn/Đức): load config/thresholds.locked.json khi đã khoá
    core_cols = [c for c in S.CORE_FEATURE_COLS if c != "section_name_class"]
    ref = df[df.group == "G0"][core_cols].to_numpy(float)
    dual = None
    if len(ref) >= 3:
        dual = DualCheck(ref); dual.lock_threshold(ref, p=95)

    sample = _subsample_to_ratio(df, pack_ratio, seed)
    ratio_real = M.pack_ratio(list(sample.group), list(sample.variant))

    rows = []
    for gate in GATES:
        dec = _gate_decisions(gate, sample, scorer, dual)
        X = sample[FEATURE_NUM].to_numpy(float)
        alarms = det.predict(X)   # chuông chạy trên TẤT CẢ; FTR bỏ mẫu FILTERED
        rows.append({
            "exp": exp, "gate": gate, "seed": seed,
            "pack_ratio_set": pack_ratio, "pack_ratio_real": round(ratio_real, 3),
            "FTR": M.ftr(dec, list(sample.group), alarms).value,
            "FNR_G2": M.fnr(dec, list(sample.group), "G2").value,
            "FNR_G3": M.fnr(dec, list(sample.group), "G3").value,
            "correct_filter_Pseen": M.correct_filter_rate(dec, list(sample.group), list(sample.variant), "P-seen").value,
            "correct_filter_Punseen": M.correct_filter_rate(dec, list(sample.group), list(sample.variant), "P-unseen").value,
            "correct_filter_Plow": M.correct_filter_rate(dec, list(sample.group), list(sample.variant), "P-low").value,
            "correct_filter_Pwild": M.correct_filter_rate(dec, list(sample.group), list(sample.variant), "P-wild").value,
            "flagged_rate": M.flagged_rate(dec).value,
        })

    out_df = pd.DataFrame(rows)
    os.makedirs(out_dir, exist_ok=True)
    fn = os.path.join(out_dir, f"results_{exp}_{seed}_{int(pack_ratio*100)}.csv")
    out_df.to_csv(fn, index=False)
    print(out_df.to_string(index=False))
    print(f"[{exp}] -> {fn}")
    return fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="e2",
                    help="e0b|e1|e2|e3|e4|e5|e6 (khung chung; nội dung chi tiết TODO Đức)")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--pack-ratio", type=float, default=0.5)
    ap.add_argument("--out-dir", default=os.path.join(HERE, "..", "results"))
    args = ap.parse_args()
    run(args.exp, args.dataset, args.seed, args.pack_ratio, args.out_dir)


if __name__ == "__main__":
    main()
