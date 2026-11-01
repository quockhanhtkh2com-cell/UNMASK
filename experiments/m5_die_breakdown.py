"""M5 (Gop_y_G1.pdf) - Bang chung "truoc": muc do nhiem pack/protected THAT trong G0/G2,
do DiE (Detect It Easy) quet that tren toan bo 596 mau (results/die_real_v1.1.csv) - KHONG
quet lai, chi doi chieu voi dataset_v1.1.csv de ra bang thong ke.

Day la du lieu dung lam dau vao cho m5_verified_clean_check.py (buoc sau). Chay script
nay TRUOC de co anh chup man hinh "bang chung nhiem ban" cho Phu luc M5.

    python experiments/m5_die_breakdown.py
"""
from __future__ import annotations
import os
import sys

import pandas as pd

HERE = os.path.dirname(__file__)


def _find(path, fname):
    cands = [
        os.path.join("results", fname),
        os.path.join(HERE, "..", "results", fname),
        os.path.join(os.path.dirname(path), fname),
        fname,
    ]
    f = next((c for c in cands if c and os.path.exists(c)), None)
    if not f:
        raise FileNotFoundError(f"Khong tim thay {fname}. Da tim: {cands}")
    return f


def run(dataset_path: str = "dataset_v1.1.csv"):
    df = pd.read_csv(dataset_path)
    die = pd.read_csv(_find(dataset_path, "die_real_v1.1.csv"))
    df = df.merge(die[["sha256", "die_result_real"]], on="sha256", how="left")

    print("=" * 70)
    print("M5 - DiE that: phan bo clean/protected/packed theo nhom (G0, G2)")
    print("=" * 70)
    for g in ["G0", "G2"]:
        sub = df[df.group == g]
        print(f"\n--- {g} (n={len(sub)}) ---")
        print(sub.die_result_real.value_counts().to_string())

    print("\n" + "=" * 70)
    print("Chi tiet G0: AgentTesla native (is_dotnet=0) vs .NET (is_dotnet=1)")
    print("=" * 70)
    g0 = df[df.group == "G0"]
    for is_net, label in [(0, "native (is_dotnet=0)"), (1, ".NET (is_dotnet=1)")]:
        sub = g0[g0.is_dotnet == is_net]
        print(f"\n--- G0 {label} (n={len(sub)}) ---")
        print(sub.die_result_real.value_counts().to_string())

    print("\n" + "=" * 70)
    print("Chi tiet mau G0 bi gan 'protected' (ten family + split)")
    print("=" * 70)
    bad_g0 = g0[g0.die_result_real == "protected"]
    print(bad_g0[["sha256", "family", "split"]].to_string(index=False))

    print("\n" + "=" * 70)
    print("Chi tiet mau G2 bi gan 'packed'/'protected' that (ten family + split)")
    print("=" * 70)
    g2 = df[df.group == "G2"]
    bad_g2 = g2[g2.die_result_real.isin(["packed", "protected"])]
    print(bad_g2[["sha256", "family", "die_result_real", "split"]].to_string(index=False))

    print("\n" + "=" * 70)
    print("Phan bo mau nhiem theo split (train/val/test) - quyet dinh cach xu ly M5")
    print("=" * 70)
    print("\nG0 protected theo split:")
    print(bad_g0.split.value_counts().to_string())
    print("\nG2 packed/protected theo split:")
    print(bad_g2.split.value_counts().to_string())


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="dataset_v1.1.csv")
    args = ap.parse_args()
    run(args.dataset)
