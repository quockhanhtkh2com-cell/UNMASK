"""prepare_g2.py — Lọc đúng 119 mẫu G2 từ thư mục MOTIF đã giải nén (CHẠY TRONG VM).

MOTIF.7z giải nén ra ~3095 file tên MOTIF_<md5>. Script này đọc g2_motif_roster.csv,
copy ĐÚNG các file có trong roster sang một thư mục riêng, đổi tên theo sha256 cho
khớp pipeline (origin_sha256). KHÔNG chạy mẫu, chỉ copy + đổi tên.

Chạy TRONG VM (vì đụng file độc, dù đã disarmed):
  python prepare_g2.py --motif-dir "C:/MOTIF_extracted" ^
                       --roster "D:/.../Datasets/g2_motif_roster.csv" ^
                       --out "C:/g2_samples"

Sau đó trích feature:
  python extract_features.py --in "C:/g2_samples" --group G2 ...
"""
from __future__ import annotations
import argparse, csv, os, shutil, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--motif-dir", required=True, help="thu muc MOTIF da giai nen (chua file MOTIF_<md5>)")
    ap.add_argument("--roster", required=True, help="duong dan g2_motif_roster.csv")
    ap.add_argument("--out", required=True, help="thu muc dich cho 119 mau G2")
    ap.add_argument("--rename-sha256", action="store_true",
                    help="doi ten file dich thanh <sha256>.bin (khop origin_sha256)")
    args = ap.parse_args()

    if not os.path.isdir(args.motif_dir):
        sys.exit(f"Khong thay thu muc MOTIF: {args.motif_dir}")
    os.makedirs(args.out, exist_ok=True)

    with open(args.roster, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    ok = miss = 0
    missing = []
    for r in rows:
        name = r["motif_filename"]              # MOTIF_<md5>
        src = os.path.join(args.motif_dir, name)
        if not os.path.exists(src):
            miss += 1; missing.append(name); continue
        dst_name = (r["sha256"] + ".bin") if args.rename_sha256 else name
        shutil.copy2(src, os.path.join(args.out, dst_name))
        ok += 1

    print(f"[xong] Copy {ok}/{len(rows)} mau G2 -> {args.out}")
    if miss:
        print(f"[!] Thieu {miss} file (khong thay trong MOTIF-dir): {missing[:5]}...")
        print("    Kiem tra lai da giai nen het MOTIF.7z chua.")

if __name__ == "__main__":
    main()
