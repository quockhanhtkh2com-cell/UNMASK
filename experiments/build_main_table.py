"""Ghép BẢNG CHÍNH F0–F3 từ các results_*.csv — [Đức].

Mỗi dòng 1 cổng; cột: FTR@50%, lọc đúng P-seen/unseen/low/wild, FNR G2, FNR G3.
Bảng này trả lời cả RQ1–RQ4. Trung bình trên các seed, kèm Wilson CI (TODO).

    python experiments/build_main_table.py --results results --out results/bang_chinh
"""
from __future__ import annotations
import argparse
import glob
import os


def build(results_dir: str, out_prefix: str, ftr_ratio: int = 50):
    import pandas as pd
    files = glob.glob(os.path.join(results_dir, "results_*.csv"))
    if not files:
        print("Chưa có results_*.csv — chạy run_experiments.py trước."); return
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    ftr50 = df[df.pack_ratio_set == ftr_ratio / 100]
    agg = df.groupby("gate").agg(
        FNR_G2=("FNR_G2", "mean"), FNR_G3=("FNR_G3", "mean"),
        correct_Pseen=("correct_filter_Pseen", "mean"),
        correct_Punseen=("correct_filter_Punseen", "mean"),
        correct_Plow=("correct_filter_Plow", "mean"),
        correct_Pwild=("correct_filter_Pwild", "mean"),
        flagged=("flagged_rate", "mean"),
    )
    agg[f"FTR@{ftr_ratio}%"] = ftr50.groupby("gate")["FTR"].mean()
    order = ["FTR@%d%%" % ftr_ratio, "correct_Pseen", "correct_Punseen",
             "correct_Plow", "correct_Pwild", "FNR_G2", "FNR_G3", "flagged"]
    agg = agg.reindex(["F0", "F1", "F2", "F3"])[order].round(3)

    agg.to_csv(out_prefix + ".csv")
    with open(out_prefix + ".md", "w") as f:
        f.write("# Bảng chính F0–F3 (trung bình trên seed × tỉ lệ pack)\n\n")
        f.write(agg.to_markdown())
        f.write("\n\n> FTR kèm tỉ lệ pack; FNR tách riêng G2/G3. "
                "TODO(Đức): thêm Wilson CI + McNemar F3 vs F1.\n")
    print(agg.to_string())
    print(f"[bang_chinh] -> {out_prefix}.csv / .md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="results/bang_chinh")
    args = ap.parse_args()
    build(args.results, args.out)


if __name__ == "__main__":
    main()
