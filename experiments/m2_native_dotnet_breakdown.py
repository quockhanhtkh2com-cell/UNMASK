"""M2 — F3 có mù .NET+MPRESS không? Tách kết quả F3 theo (group × packer × native/.NET) trên TẬP TEST.
Chạy (từ gốc repo): PYTHONPATH=src:. python experiments/m2_native_dotnet_breakdown.py --dataset dataset_v1.1.csv --f3-config config/thresholds.locked.json --out results/m2_packed_score_breakdown.csv
Chỉ ĐỌC config khoá, không sửa."""
from __future__ import annotations
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "src"), os.path.join(HERE, "..")]
import pandas as pd
from unmask.filter import load_filter

EXPECT = {("G1", "upx", "native"): (15, 15), ("G1", "mpress", "native"): (14, 14), ("G1", "mpress", ".NET"): (0, 21),
          ("G3", "mpress", "native"): (67, 71), ("G3", "mpress", ".NET"): (0, 82)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--f3-config", default="config/thresholds.locked.json")
    ap.add_argument("--out", default="results/m2_packed_score_breakdown.csv")
    a = ap.parse_args()
    df = pd.read_csv(a.dataset)
    f3 = load_filter(a.f3_config, use_dualcheck=True)
    t = df[df.split == "test"].reset_index(drop=True)
    res = [f3.decide(r) for r in t.to_dict("records")]
    t["packed_score"] = [r["packed_score"] for r in res]
    t["decision"] = [r["decision"] for r in res]
    t["kind"] = t.is_dotnet.map({1: ".NET", 0: "native"})
    t["filtered"] = t.decision == "FILTERED"
    out = (t.groupby(["group", "packer", "kind"])
             .agg(n=("filtered", "size"), n_filtered=("filtered", "sum"),
                  packed_score_median=("packed_score", "median"),
                  packed_score_min=("packed_score", "min"), packed_score_max=("packed_score", "max"))
             .reset_index())
    out["rate_filtered"] = (out.n_filtered / out.n).round(3)
    for c in ["packed_score_median", "packed_score_min", "packed_score_max"]:
        out[c] = out[c].round(4)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    out.to_csv(a.out, index=False)
    print(out.to_string(index=False))
    tr = df[df.split.isin(["train", "val"])]
    tr = tr[(tr.group == "G0") | ((tr.group == "G1") & (tr.variant == "P-seen"))]
    comp = tr.groupby(["group", "packer", "is_dotnet"]).size().rename("n").reset_index()
    comp_path = os.path.join(os.path.dirname(a.out) or ".", "m2_train_composition.csv")
    comp.to_csv(comp_path, index=False)
    print("\nThành phần train packed_score:\n" + comp.to_string(index=False))
    bad = []
    for key, (k, n) in EXPECT.items():
        row = out[(out.group == key[0]) & (out.packer == key[1]) & (out.kind == key[2])]
        got = (int(row.n_filtered.iloc[0]), int(row.n.iloc[0])) if len(row) else None
        if got != (k, n):
            bad.append((key, (k, n), got))
    print("\n[ĐỐI CHIẾU M2_M7_Tuan.md]", "KHỚP tất cả 5 ô" if not bad else f"LỆCH: {bad}")
    print("->", a.out, "/", comp_path)


if __name__ == "__main__":
    main()
