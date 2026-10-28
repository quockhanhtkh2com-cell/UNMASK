#!/usr/bin/env python3
"""T1 + T2 — giải thích F3 so với F2 và mở các ca dual-check cứu được — [Tuấn].

Chỉ ĐỌC config khóa và dataset; không train, không đổi ngưỡng nào (F3=0.475, D1=6.9111).
Chạy từ thư mục gốc repo:

    python3 experiments/explain_f3.py

Đầu ra:
    results/f3_vs_f2_decisions.csv   F2 vs F3 theo nhóm x packer (tập test)
    results/f3_vs_f2_disagree.csv    từng mẫu F2 và F3 quyết định khác nhau
    results/f3_weights.csv           trọng số logistic + đóng góp trung bình
    results/dualcheck_cases.csv      mẫu F3a loại nhưng F3 giữ lại nhờ dual-check
    results/dualcheck_by_group.csv   dual-check similar/novel theo nhóm x packer
    docs/f3_interpretability.md      bảng + số cho Report
    docs/dualcheck_cases.md          bảng các ca dual-check
"""
from __future__ import annotations
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
import f2_rule  # noqa: E402
from unmask.filter import load_filter  # noqa: E402
from unmask.packed_score import NUMERIC  # noqa: E402


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |",
           "|" + "|".join(":---:" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(_fmt(r[c]) for c in cols) + " |")
    return "\n".join(out)


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def gapply(g, fn):
    """groupby.apply tương thích pandas cũ/mới (include_groups chỉ có từ pandas 2.2)."""
    try:
        return g.apply(fn, include_groups=False).reset_index()
    except TypeError:
        return g.apply(fn).reset_index()


def auc(score: pd.Series, y: pd.Series) -> float:
    """AUC (Mann-Whitney) của score phân biệt y=1 với y=0."""
    r = score.rank(method="average")
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=os.path.join(ROOT, "dataset_v1.1.csv"))
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "thresholds.locked.json"))
    ap.add_argument("--split", default="test")
    ap.add_argument("--results", default=os.path.join(ROOT, "results"))
    ap.add_argument("--docs", default=os.path.join(ROOT, "docs"))
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    thr = cfg["packed_score"]["threshold"]
    df = pd.read_csv(a.dataset)
    df = df[df["split"] == a.split].reset_index(drop=True)
    df["packer"] = df["packer"].fillna("none").astype(str).str.lower()
    n = len(df)
    print(f"[explain_f3] split={a.split} n={n} F3 threshold={thr}")

    f3 = load_filter(a.config)
    f3a = load_filter(a.config, use_dualcheck=False)
    rows = df.to_dict("records")
    res3 = [f3.decide(r) for r in rows]
    df["f2"] = f2_rule.run(df)
    df["f3"] = [r["decision"] for r in res3]
    df["f3a"] = [f3a.decide(r)["decision"] for r in rows]
    df["score"] = [r["packed_score"] for r in res3]
    df["evidence"] = [json.dumps(r["evidence"], ensure_ascii=False) for r in res3]
    df["sha12"] = df["sha256"].str[:12]
    packed_truth = df["group"].isin(["G1", "G3"]).astype(int)  # nhãn pack do nhóm kiểm soát

    # ---------------- T1: trọng số + đóng góp ----------------
    w = cfg["packed_score"]["weights"]
    contrib = pd.DataFrame([f3.scorer._linear(r) for r in rows])
    wt = pd.DataFrame({"feature": list(w.keys())})
    wt = wt[wt["feature"] != "bias"].copy()
    wt["weight_std"] = wt["feature"].map(w)
    wt["abs_weight"] = wt["weight_std"].abs()
    wt["mean_abs_contrib"] = wt["feature"].map(lambda k: float(contrib[k].abs().mean()) if k in contrib else np.nan)
    wt["mean_contrib_packed"] = wt["feature"].map(lambda k: float(contrib.loc[packed_truth == 1, k].mean()) if k in contrib else np.nan)
    wt["mean_contrib_unpacked"] = wt["feature"].map(lambda k: float(contrib.loc[packed_truth == 0, k].mean()) if k in contrib else np.nan)
    wt = wt.sort_values("abs_weight", ascending=False).reset_index(drop=True)
    wt.insert(0, "rank", range(1, len(wt) + 1))
    os.makedirs(a.results, exist_ok=True)
    wt.to_csv(os.path.join(a.results, "f3_weights.csv"), index=False)

    # F3 có "chỉ là entropy" không?
    sect = df["section_name_class"].map({"standard": 0.0, "known_packer": 1.0, "weird": 0.7}).fillna(0.5)
    sim = {
        "corr(packed_score, entropy_max_section)": float(np.corrcoef(df["score"], df["entropy_max_section"])[0, 1]),
        "AUC packed_score (pack G1+G3 vs G0+G2)": auc(df["score"], packed_truth),
        "AUC entropy_max_section": auc(df["entropy_max_section"], packed_truth),
        "AUC ep_section_writable": auc(df["ep_section_writable"], packed_truth),
        "AUC section_name_class (0/0.7/1)": auc(sect, packed_truth),
    }
    f2f = (df["f2"] == "FILTERED").astype(int)
    f3f = (df["f3"] == "FILTERED").astype(int)
    f3p = (df["score"] >= thr).astype(int)
    sim["tỉ lệ F2 và F3 cùng quyết định FILTERED/không"] = float((f2f == f3f).mean())
    sim["tỉ lệ F2(FILTERED) và packed_score>=ngưỡng trùng nhau"] = float((f2f == f3p).mean())

    # ---------------- T1: bảng quyết định theo nhóm x packer ----------------
    g = df.groupby(["group", "packer"])
    tab = gapply(g, lambda d: pd.Series({
        "n": len(d),
        "F2_FILTERED": int((d["f2"] == "FILTERED").sum()),
        "F3_FILTERED": int((d["f3"] == "FILTERED").sum()),
        "F3_FLAGGED": int((d["f3"] == "FLAGGED").sum()),
        "F3_PASS": int((d["f3"] == "PASS").sum()),
        "F3a_FILTERED": int((d["f3a"] == "FILTERED").sum()),
        "ca_khac_nhau(F2 vs F3 FILTERED)": int(((d["f2"] == "FILTERED") != (d["f3"] == "FILTERED")).sum()),
    }))
    tab.to_csv(os.path.join(a.results, "f3_vs_f2_decisions.csv"), index=False)

    dis = df[(df["f2"] == "FILTERED") != (df["f3"] == "FILTERED")]
    keep = ["sha12", "group", "family", "variant", "packer", "is_dotnet", "entropy_max_section",
            "section_name_class", "ep_section_writable", "score", "f2", "f3", "evidence"]
    keep = [c for c in keep if c in dis.columns]
    dis[keep].sort_values(["group", "packer", "score"]).to_csv(
        os.path.join(a.results, "f3_vs_f2_disagree.csv"), index=False)

    # ---------------- T2: dual-check ----------------
    dual = f3.dual
    cols = dual.core_cols
    hi = df[df["score"] >= thr].copy()
    dists, nearest, topfeat = [], [], []
    refz = (dual.ref - dual.mean) / dual.std
    for r in hi.to_dict("records"):
        x = np.array([float(r.get(c, 0) or 0) for c in cols])
        xz = (x - dual.mean) / dual.std
        d = np.sqrt(((refz - xz) ** 2).sum(axis=1))
        j = int(d.argmin())
        dists.append(float(d[j]))
        nearest.append(j)
        topfeat.append(cols[int(np.abs(xz - refz[j]).argmax())])
    hi["dist"] = dists
    hi["nearest_ref"] = nearest
    hi["lech_nhat"] = topfeat
    hi["dual_threshold"] = dual.threshold
    hi["dist/threshold"] = hi["dist"] / dual.threshold
    by = gapply(hi.groupby(["group", "packer"]), lambda d: pd.Series({
        "n_score>=thr": len(d),
        "similar(FILTERED)": int((d["dist"] <= dual.threshold).sum()),
        "novel(FLAGGED)": int((d["dist"] > dual.threshold).sum()),
        "dist_median": float(d["dist"].median()),
    }))
    cnt = [c for c in by.columns if c not in ("group", "packer", "dist_median")]
    by[cnt] = by[cnt].astype(int)  # đếm số ca nên in số nguyên
    by.to_csv(os.path.join(a.results, "dualcheck_by_group.csv"), index=False)

    resc = df[(df["f3a"] == "FILTERED") & (df["f3"] != "FILTERED")].copy()
    back = df[(df["f3a"] != "FILTERED") & (df["f3"] == "FILTERED")]
    resc = resc.merge(hi[["sha256", "dist", "nearest_ref", "lech_nhat", "dist/threshold"]], on="sha256", how="left")
    for c in cols:
        resc[f"core_{c}"] = resc[c]
    ck = ["sha12", "group", "family", "packer", "score", "dist", "dist/threshold", "nearest_ref", "lech_nhat"] \
         + [f"core_{c}" for c in cols] + ["evidence"]
    resc[ck].to_csv(os.path.join(a.results, "dualcheck_cases.csv"), index=False)

    # ---------------- ghi docs ----------------
    os.makedirs(a.docs, exist_ok=True)
    L = []
    L.append("# F3 so với F2 — giải thích (T1)\n")
    L.append(f"Dữ liệu: dataset v1.1, split `{a.split}` (n={n}). Config khóa: `packed_score.threshold = {thr}`. "
             "Script `experiments/explain_f3.py` chỉ đọc config, không train, không đổi ngưỡng.\n")
    L.append("## 1. Trọng số logistic của packed_score (feature đã chuẩn hóa nên so sánh được độ lớn)\n")
    L.append(md_table(wt.round(3)) + "\n")
    L.append("`mean_contrib_*` = đóng góp trung bình của feature vào điểm (trọng số x giá trị chuẩn hóa) "
             "trên nhóm bị pack (G1+G3) và không pack (G0+G2) của tập test. Dấu âm của trọng số nghĩa là feature "
             "đó kéo điểm xuống khi các feature khác cố định.\n")
    L.append("## 2. packed_score có thực chất là luật entropy không?\n")
    L.append(md_table(pd.DataFrame({"chỉ số": list(sim.keys()), "giá trị": list(sim.values())})) + "\n")
    L.append("## 3. Quyết định F2 và F3 theo nhóm x packer (tập test)\n")
    L.append(md_table(tab) + "\n")
    L.append("FILTERED = loại khỏi chuông D1. F3 chia điểm cao thành FILTERED (dual-check `similar`) và "
             "FLAGGED (`novel`, vẫn vào chuông). Danh sách từng ca khác nhau: `results/f3_vs_f2_disagree.csv`.\n")
    L.append(f"Tổng số mẫu F2 và F3 quyết định FILTERED khác nhau: **{len(dis)}/{n}**.\n")
    L.append("## 4. Nhận xét (điền sau khi đọc số)\n")
    L.append("- TODO: chỗ F3 khác F2 (nhóm nào, bao nhiêu mẫu).\n- TODO: nếu packed_score gần với entropy thì ghi trung thực.\n")
    open(os.path.join(a.docs, "f3_interpretability.md"), "w", encoding="utf-8").write("\n".join(L))

    M = []
    M.append("# Dual-check — các ca cứu được (T2)\n")
    M.append(f"Dữ liệu: split `{a.split}` (n={n}). Ngưỡng dual-check khóa: `{dual.threshold:.4f}`; "
             f"đặc trưng lõi: `{', '.join(cols)}`; số mẫu tham chiếu: {len(dual.ref)}.\n")
    M.append(f"**Ca cứu** = F3a (không dual-check) loại, F3 giữ lại (FLAGGED): **{len(resc)}** mẫu. "
             f"Chiều ngược lại (F3a giữ, F3 loại): {len(back)} mẫu.\n")
    M.append("## 1. Bảng các ca\n")
    show = resc[["sha12", "group", "family", "packer", "score", "dist", "dist/threshold", "lech_nhat"]].round(3)
    M.append(md_table(show) + "\n")
    M.append("`dist` = khoảng cách Euclid chuẩn hóa tới mẫu tham chiếu gần nhất; `dist/threshold` > 1 nghĩa là "
             "'novel'. `lech_nhat` = đặc trưng lõi lệch nhiều nhất so với mẫu tham chiếu gần nhất.\n")
    M.append("## 2. Dual-check trên mọi mẫu có packed_score >= ngưỡng\n")
    M.append(md_table(by.round(3)) + "\n")
    M.append("## 3. Giá trị đặc trưng lõi của các ca cứu\n")
    M.append(md_table(resc[["sha12"] + [f"core_{c}" for c in cols]]) + "\n")
    M.append("## 4. Nhận xét (điền sau khi đọc số)\n")
    M.append("- TODO: cơ chế (đặc trưng nào làm các mẫu này thành 'novel').\n- TODO: giới hạn (4 đặc trưng lõi; p=0.13 chưa có ý nghĩa thống kê).\n")
    open(os.path.join(a.docs, "dualcheck_cases.md"), "w", encoding="utf-8").write("\n".join(M))

    print("\n=== TÓM TẮT (dán lại cho Claude) ===")
    print(wt.round(3).to_string(index=False))
    print()
    for k, v in sim.items():
        print(f"{k}: {v:.3f}")
    print()
    print(tab.to_string(index=False))
    print(f"\nF2 vs F3 FILTERED khác nhau: {len(dis)}/{n}")
    print("\n--- dual-check theo nhóm ---")
    print(by.round(3).to_string(index=False))
    print(f"\nCa cứu (F3a loại, F3 giữ): {len(resc)}; ngược lại: {len(back)}")
    print(resc[["sha12", "group", "family", "packer", "score", "dist", "dist/threshold", "lech_nhat"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
