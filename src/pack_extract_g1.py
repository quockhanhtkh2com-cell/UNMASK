"""pack_extract_g1.py — Pack G0 -> G1 (UPX) + trích feature + GHI origin_sha256.

G1 = "đổi vỏ": lấy mẫu G0 (lõi sạch) pack bằng UPX. Mỗi G1 phải nhớ nó sinh ra
từ G0 nào (origin_sha256) -> để split chống leakage (G0 & G1 cùng origin KHÔNG
được tách 2 phía train/test).

CHẠY TRONG VM. Pack là thao tác trên file (không chạy mẫu). Dùng extract_features
.extract_one() -> feature nhất quán với G0/G2.

  python3 src/pack_extract_g1.py \
      --in  ~/IAM302t/Datasets/g0_unpacked \
      --packed-out ~/IAM302t/Datasets/g1_packed \
      --out part_g1.csv --packer upx --variant P-seen

Cần: upx (which upx), pefile, pandas.
"""
from __future__ import annotations
import argparse, csv, hashlib, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_features as EF  # noqa: E402


def sha256_of(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def is_pe(path):
    try:
        with open(path, "rb") as f:
            return f.read(2) == b"MZ"
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", required=True, help="thu muc G0 da giai nen")
    ap.add_argument("--packed-out", required=True, help="thu muc luu file G1 da pack")
    ap.add_argument("--out", required=True, help="CSV feature G1")
    ap.add_argument("--upx", default="upx")
    ap.add_argument("--packer", default="upx")
    ap.add_argument("--variant", default="P-seen")
    ap.add_argument("--family", default="agenttesla")
    args = ap.parse_args()
    import pandas as pd

    os.makedirs(args.packed_out, exist_ok=True)
    rows, packed_ok, pack_fail, parse_fail = [], 0, [], []

    for fn in sorted(os.listdir(args.indir)):
        src = os.path.join(args.indir, fn)
        if not os.path.isfile(src) or not is_pe(src):
            continue
        origin = sha256_of(src)                      # sha256 cua G0 GOC
        packed = os.path.join(args.packed_out, f"{origin}_{args.packer}.exe")
        if os.path.exists(packed):
            os.remove(packed)
        r = subprocess.run([args.upx, "--best", "--force", "-o", packed, src],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(packed):
            msg = (r.stderr or r.stdout or "").strip().splitlines()
            pack_fail.append((fn, msg[-1] if msg else f"rc={r.returncode}"))
            continue
        packed_ok += 1
        try:
            feat = EF.extract_one(packed)
        except Exception as e:
            parse_fail.append((fn, str(e))); continue
        feat.update({
            "sha256": sha256_of(packed),             # danh tinh file G1 (da pack)
            "family": args.family, "group": "G1",
            "variant": args.variant, "packer": args.packer,
            "origin_sha256": origin,                 # <-- tro ve G0 goc (chong leakage)
        })
        rows.append(feat)

    pd.DataFrame(rows).to_csv(args.out, index=False)
    print(f"[pack_g1] pack OK {packed_ok} | feature {len(rows)} -> {args.out}")
    if pack_fail:
        print(f"[!] UPX KHONG pack duoc {len(pack_fail)} mau (hay gap voi .NET):")
        for fn, m in pack_fail: print(f"     {fn[:20]}... -> {m}")
    if parse_fail:
        print(f"[!] Parse loi {len(parse_fail)}: {parse_fail[:3]}")


if __name__ == "__main__":
    main()
