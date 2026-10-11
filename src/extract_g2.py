"""extract_g2.py — Trích feature G2 từ mẫu MOTIF đã giải nén, GẮN NHÃN theo roster.

Vì sao cần riêng (không dùng thẳng extract_features.py):
  1. G2 có NHIỀU họ (azorult, njrat, ...) — extract_features chỉ gán 1 --family/lần.
  2. File MOTIF tên theo md5 GỐC (trước disarm); sha256 nội dung sau disarm khác đi,
     nên danh tính (sha256, origin_sha256) phải lấy từ ROSTER, không tính lại.

Script dùng CHÍNH extract_features.extract_one() -> feature nhất quán với G0/G1.
CHỈ parse tĩnh, KHÔNG chạy mẫu.

Chạy (host nếu chấp nhận vì mẫu disarmed KHÔNG chạy được, hoặc trong VM cho đúng SAFETY):
  python src/extract_g2.py \
      --motif-dir "<thư mục MOTIF_defanged đã giải nén>" \
      --roster   "<...>/g2_motif_roster.csv" \
      --out      part_g2.csv

Cần: pip install pefile pandas
"""
from __future__ import annotations
import argparse, csv, hashlib, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # để import được extract_features
import extract_features as EF  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--motif-dir", required=True, help="thu muc MOTIF_defanged (chua file MOTIF_<md5>)")
    ap.add_argument("--roster", required=True, help="g2_motif_roster.csv")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import pandas as pd

    if not os.path.isdir(args.motif_dir):
        sys.exit(f"Khong thay thu muc: {args.motif_dir}")

    with open(args.roster, encoding="utf-8") as f:
        roster = list(csv.DictReader(f))

    rows, miss, skip = [], [], []
    for r in roster:
        path = os.path.join(args.motif_dir, r["motif_filename"])
        if not os.path.exists(path):
            miss.append(r["motif_filename"]); continue
        try:
            feat = EF.extract_one(path)          # feature TĨNH, cùng tool với G0/G1
        except Exception as e:
            skip.append((r["motif_filename"], str(e))); continue
        # danh tinh + nhan LAY TU ROSTER (chuan)
        feat.update({
            "sha256": r["sha256"],               # sha256 goc (khop threat report)
            "family": r["family"],               # nhan ground-truth tung mau
            "group": "G2",
            "variant": "none",
            "packer": "none",
            "origin_sha256": r["sha256"],         # G2 la loi goc -> tu lam origin
            # provenance them: hash that cua file disarmed (de minh bach)
            "disarmed_sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(),
            "source": "MOTIF",
            "first_seen": r.get("first_seen", ""),
        })
        rows.append(feat)

    pd.DataFrame(rows).to_csv(args.out, index=False)
    print(f"[extract_g2] OK {len(rows)}/{len(roster)} mau -> {args.out}")
    if miss:
        print(f"[!] Thieu {len(miss)} file (chua giai nen het?): {miss[:5]}...")
    if skip:
        print(f"[!] Parse loi {len(skip)} mau (disarm lam hong PE?): {skip[:3]}...")
    # phan bo ho de kiem nhanh
    if rows:
        import collections
        c = collections.Counter(x["family"] for x in rows)
        print("    Phan bo ho:", dict(c))


if __name__ == "__main__":
    main()
