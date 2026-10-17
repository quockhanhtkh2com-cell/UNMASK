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


def _build_f3(dataset: str, f3_config: str | None, seed: int):
    import tempfile
    from unmask.filter import _load_locked
    if f3_config or _load_locked():
        return load_filter(f3_config)
    print("[CẢNH BÁO] chưa có config F3 khoá -> train TẠM từ dataset (số liệu chỉ để chạy thử, "
          "KHÔNG đưa vào báo cáo). Khoá thật: python unmask/train.py --dataset ... --out config/thresholds.locked.json")
    from unmask.train import train
    tmp = os.path.join(tempfile.mkdtemp(), "f3_tmp.json")
    train(dataset, tmp, seed)
    return load_filter(tmp)


def _gate_decisions(gate: str, df, f3_filter) -> list[str]:
    if gate == "F0":
        return ["PASS"] * len(df)
    if gate == "F1":
        return f1_die.run(df)
    if gate == "F2":
        return f2_rule.run(df)
    if gate == "F3":
        return [f3_filter.decide(r)["decision"] for r in df.to_dict("records")]
    raise ValueError(gate)


def run(exp: str, dataset: str, seed: int, pack_ratio: float, out_dir: str, detector_method: str = "mahalanobis",
        f3_config: str | None = None):
    import numpy as np, pandas as pd
    df = pd.read_csv(dataset)

    # chuông D1 CHUNG: fit trên G0 (train), khoá P95 trên G0 (val).
    g0_train = df[(df.group == "G0") & (df.split == "train")][FEATURE_NUM].to_numpy(float)
    g0_val = df[(df.group == "G0") & (df.split == "val")][FEATURE_NUM].to_numpy(float)

    # Fallback an toàn nếu g0_train hoặc g0_val rỗng
    if len(g0_train) == 0:
        g0_train = df[df.group == "G0"][FEATURE_NUM].to_numpy(float)
    if len(g0_val) == 0:
        g0_val = g0_train

    det = DriftDetector(method=detector_method, seed=seed).fit(g0_train)
    det.lock_threshold(g0_val, p=95)

    # F3: nạp scorer + dual-check từ config ĐÃ KHOÁ (trọng số học trên train/val, KHÔNG thấy test).
    # Chưa có config khoá -> train tạm ra thư mục tạm (chỉ để chạy thử, in cảnh báo).
    f3_filter = _build_f3(dataset, f3_config, seed)

    sample = _subsample_to_ratio(df, pack_ratio, seed)
    ratio_real = M.pack_ratio(list(sample.group), list(sample.variant))

    rows = []
    for gate in GATES:
        dec = _gate_decisions(gate, sample, f3_filter)
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
    ap.add_argument("--detector", default="mahalanobis", choices=["mahalanobis", "isolation_forest"])
    ap.add_argument("--f3-config", default=None,
                    help="config F3 đã khoá (mặc định: config/thresholds.locked.json / UNMASK_CONFIG)")
    ap.add_argument("--out-dir", default=os.path.join(HERE, "..", "results"))
    args = ap.parse_args()
    run(args.exp, args.dataset, args.seed, args.pack_ratio, args.out_dir, detector_method=args.detector,
        f3_config=args.f3_config)


if __name__ == "__main__":
    main()
