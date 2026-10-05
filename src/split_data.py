"""Chia tập theo MẪU GỐC (origin_sha256) — [Trúc]. Chống rò rỉ: mọi biến thể của
1 mẫu nằm CÙNG 1 tập. Đề ôn (train/val) = G0 + G1-UPX (P-seen). Đề thi (test) =
phần còn lại (P-unseen, P-low, P-wild, G2, G3).

    python src/split_data.py --dataset mock/mock_dataset.csv --out mock/mock_dataset.csv
"""
from __future__ import annotations
import argparse
import random
import sys


def assign_split(df, seed: int = 0, val_frac: float = 0.2, test_frac_g0: float = 0.3):
    """Chia tập theo ORIGIN — mọi biến thể của 1 mẫu gốc nằm CÙNG 1 tập (chống rò rỉ).

    Nguyên tắc (bám hướng dẫn):
    - Origin "đổi lõi" (sinh G2/G3) -> TOÀN BỘ vào test: đây là đề thi để đo FNR,
      và giữ G2+G3 của cùng origin ở cùng chỗ.
    - Origin "lõi gốc" (AgentTesla, sinh G0/G1/P-low/P-wild) -> chia train/val/test.
      Scorer chỉ HỌC trên các dòng G0 + G1-P-seen thuộc train/val (train.py lọc tiếp);
      phần P-unseen/P-low/P-wild của origin test dùng để đo tổng quát (E3).

    => Không origin nào nằm ở cả {train,val} lẫn test.
    """
    rng = random.Random(seed)
    df = df.copy()

    # Phân loại origin theo các group mà nó sinh ra
    groups_per_origin = df.groupby("origin_sha256")["group"].agg(set)
    drift_origins = {o for o, gs in groups_per_origin.items() if gs & {"G2", "G3"}}
    core_origins = [o for o in groups_per_origin.index if o not in drift_origins]
    rng.shuffle(core_origins)

    n_test = int(len(core_origins) * test_frac_g0)
    n_val = int(len(core_origins) * val_frac)
    test_core = set(core_origins[:n_test])
    val_core = set(core_origins[n_test:n_test + n_val])
    # phần còn lại -> train

    def decide(origin):
        if origin in drift_origins or origin in test_core:
            return "test"
        if origin in val_core:
            return "val"
        return "train"

    df["split"] = df["origin_sha256"].map(decide)
    return df


def check_no_leak(df) -> list[str]:
    """Trả list lỗi: 1 origin không được xuất hiện ở cả {train/val} lẫn test."""
    errors = []
    for origin, sub in df.groupby("origin_sha256"):
        splits = set(sub["split"])
        if "test" in splits and ({"train", "val"} & splits):
            errors.append(f"RÒ RỈ: origin {origin[:12]}… nằm ở cả {splits}")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    import pandas as pd
    df = pd.read_csv(args.dataset)
    df = assign_split(df, seed=args.seed)
    errs = check_no_leak(df)
    if errs:
        print("\n".join(errs)); sys.exit(1)
    df.to_csv(args.out, index=False)
    print(f"[split] train={sum(df.split=='train')} val={sum(df.split=='val')} "
          f"test={sum(df.split=='test')}  -> {args.out}  (0 rò rỉ)")


if __name__ == "__main__":
    main()
