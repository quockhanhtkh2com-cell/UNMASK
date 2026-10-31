"""M7 — dual-check có tự mâu thuẫn không (file_size bị nén làm đổi)? Phân tích THAM KHẢO.
Chạy (từ gốc repo): PYTHONPATH=src:. python experiments/m7_ablation_file_size.py --dataset dataset_v1.1.csv --f3-config config/thresholds.locked.json --out results/m7_ablation.csv
KHÔNG đổi thresholds.locked.json: ngưỡng cấu hình "bỏ file_size" được khoá lại TRONG script (P95 G0 val) chỉ để so sánh."""
from __future__ import annotations
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "src"), os.path.join(HERE, "..")]
import numpy as np, pandas as pd
from unmask.filter import load_filter
from unmask.dual_check import DualCheck, fit_from_dataframe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--f3-config", default="config/thresholds.locked.json")
    ap.add_argument("--out", default="results/m7_ablation.csv")
    a = ap.parse_args()
    df = pd.read_csv(a.dataset)
    cfg = json.load(open(a.f3_config, encoding="utf-8"))
    cols4 = cfg["dual_check"]["core_cols"]
    thr_f3 = cfg["packed_score"]["threshold"]
    outdir = os.path.dirname(a.out) or "."
    os.makedirs(outdir, exist_ok=True)

    g0 = df[df.group == "G0"].set_index("sha256")
    g1 = df[df.group == "G1"].join(g0[cols4].add_suffix("_g0"), on="origin_sha256")
    rows = []
    for c in cols4:
        x, y = g1[c + "_g0"].astype(float), g1[c].astype(float)
        r = {"col": c, "n_pairs": len(g1), "changed_all": round(float((x != y).mean()), 3)}
        for pk, gg in g1.groupby("packer"):
            r["changed_" + pk] = round(float((gg[c] != gg[c + "_g0"]).mean()), 3)
        r["median_rel_change"] = round(float(((y - x).abs() / x.abs().replace(0, np.nan)).median()), 3)
        rows.append(r)
    pc = pd.DataFrame(rows)
    pc_path = os.path.join(outdir, "m7_percol_change.csv")
    pc.to_csv(pc_path, index=False)
    print(f"Mức đổi từng cột (G0->G1 thật, n={len(g1)}):\n" + pc.to_string(index=False))

    f3 = load_filter(a.f3_config, use_dualcheck=True)
    t = df[df.split == "test"].reset_index(drop=True)
    t["packed_score"] = [f3.decide(r)["packed_score"] for r in t.to_dict("records")]
    tt = t[t.packed_score >= thr_f3]
    out = []
    for name, cols in [("4 cột (khoá)", cols4), ("bỏ file_size", [c for c in cols4 if c != "file_size"])]:
        dc, _ = fit_from_dataframe(df[df.split.isin(["train", "val"])], cols)
        sim = np.array([dc.check(v) == "similar" for v in tt[cols].to_numpy(float)])
        for g in sorted(tt.group.unique()):
            m = (tt.group == g).to_numpy()
            out.append({"config": name, "cols": "+".join(cols), "threshold": round(dc.threshold, 3), "group": g,
                        "n": int(m.sum()), "n_similar_FILTERED": int(sim[m].sum())})
    ab = pd.DataFrame(out)
    ab.to_csv(a.out, index=False)
    print(f"\nAblation (test, packed_score >= {thr_f3}):\n" + ab.to_string(index=False))
    exp = {("4 cột (khoá)", "G1"): 29, ("4 cột (khoá)", "G3"): 67, ("bỏ file_size", "G1"): 15, ("bỏ file_size", "G3"): 0}
    bad = [(k, v, int(ab[(ab.config == k[0]) & (ab.group == k[1])].n_similar_FILTERED.iloc[0])) for k, v in exp.items()
           if int(ab[(ab.config == k[0]) & (ab.group == k[1])].n_similar_FILTERED.iloc[0]) != v]
    print("\n[ĐỐI CHIẾU M2_M7_Tuan.md]", "KHỚP" if not bad else f"LỆCH: {bad}")
    print(f"(ngưỡng khoá trong config = {cfg['dual_check']['similarity_threshold']:.4f}; file config KHÔNG bị sửa)")
    print("->", a.out, "/", pc_path)


if __name__ == "__main__":
    main()
