"""Pilot: feature loi nao GIU NGUYEN khi pack + kiem gia thuyet .NET. Chi doc CSV.

Dung (chay tu thu muc goc repo, sau khi extract + --finalize):
    python src/core_survival.py pilot_dataset.csv

Ghep cap: moi dong G1 duoc so voi dong G0 co CUNG origin_sha256 (G0 tu tro ve chinh no).
Voi moi packer va moi feature loi in ra: ti le cap "giong het" va do lech tuong doi (trung vi).
Script KHONG ghi file va KHONG dong den mau.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_cols as S  # noqa: E402


def survival_table(df, core_cols=None):
    """Bang (packer, feature, n_pairs, identical_frac, median_rel_dev). Rong neu khong co cap."""
    core = [c for c in (core_cols or S.CORE_FEATURE_COLS) if c in df.columns]
    g0 = df[df["group"] == "G0"].drop_duplicates("origin_sha256").set_index("origin_sha256")
    rows = []
    for _, r in df[df["group"] == "G1"].iterrows():
        if r["origin_sha256"] in g0.index:
            o = g0.loc[r["origin_sha256"]]
            for c in core:
                base = abs(o[c]) if o[c] else 1
                rows.append({"packer": r["packer"], "feature": c,
                             "dev": abs(r[c] - o[c]) / base})
    if not rows:
        return pd.DataFrame(columns=["packer", "feature", "n_pairs", "identical_frac",
                                     "median_rel_dev"])
    res = pd.DataFrame(rows)
    out = res.groupby(["packer", "feature"])["dev"].agg(
        n_pairs="size", identical_frac=lambda s: float((s == 0).mean()),
        median_rel_dev="median").reset_index()
    return out


def dotnet_lines(df):
    """Kiem gia thuyet .NET: file .NET chi import ~1 API nen 2 feature import vo nghia."""
    lines = []
    for g, d in df.groupby("group"):
        parts = [f"{g}: n={len(d)}"]
        if "is_dotnet" in d:
            parts.append(f"is_dotnet=1: {int((d['is_dotnet'] == 1).sum())}/{len(d)}")
        for c in ("num_dll", "num_api", "import_table_shrink", "only_dynamic_loader_imports"):
            if c in d:
                parts.append(f"{c} trung vi={d[c].median():g}")
        lines.append("  " + "  ".join(parts))
    return lines


def main(argv):
    if len(argv) != 2:
        print("Cach dung: python src/core_survival.py <dataset.csv>")
        return 2
    df = pd.read_csv(argv[1])
    print("Kiem gia thuyet .NET (cau 1):")
    print("\n".join(dotnet_lines(df)))
    t = survival_table(df)
    if t.empty:
        print("\nKhong co cap G0-G1 nao khop origin_sha256 (kiem lai --origin-map).")
        return 1
    print("\nFeature loi hien tai:", [c for c in S.CORE_FEATURE_COLS if c in df.columns])
    for pk, g in t.groupby("packer"):
        print(f"\npacker={pk}")
        for _, r in g.iterrows():
            print(f"  {r['feature']:20s} so cap={int(r['n_pairs']):3d}  "
                  f"giong het: {r['identical_frac']:4.0%}  "
                  f"lech tuong doi (trung vi): {r['median_rel_dev']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
