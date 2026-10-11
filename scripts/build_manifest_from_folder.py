"""build_manifest_from_folder.py — KHAI SINH NGƯỢC provenance cho các mẫu đã tải tay.

Quét một thư mục chứa các file <sha256>.zip (chuẩn tên của MalwareBazaar),
truy vấn lại metadata (get_info) cho từng hash rồi ghi/bổ sung vào manifest —
để MỌI mẫu trong dataset đều có nguồn gốc truy vết được (first_seen, reporter,
signature...). Không mở, không giải nén, không chạy mẫu.

Vì sao cần: 12 mẫu G0 tải tay không đi qua fetch_samples.py nên thiếu dòng
manifest. Thiếu provenance = reviewer trừ điểm "không tái lập / không truy vết".

Chuẩn bị: giống fetch_samples.py — Auth-Key ở MB_AUTH_KEY hoặc scripts/auth_key.txt.

Dùng:
  # Khai sinh cho 12 mẫu G0 đang nằm ở thư mục Datasets
  python scripts/build_manifest_from_folder.py ^
      --folder "D:/FPT/FALL_5/IAM302t/Datasets" --group G0 ^
      --manifest "D:/FPT/FALL_5/IAM302t/Datasets/raw_manifest.csv"

Chạy được nhiều lần: mẫu nào đã có trong manifest sẽ được BỎ QUA (không trùng).
"""
from __future__ import annotations
import argparse
import csv
import os
import re
import sys
import time
from datetime import datetime, timezone

API = "https://mb-api.abuse.ch/api/v1/"
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
COLS = ["sha256", "family", "group", "variant", "packer", "origin_sha256",
        "die_result", "source", "first_seen", "reporter", "signature",
        "file_name", "downloaded_at", "note"]


def load_key() -> str:
    key = os.environ.get("MB_AUTH_KEY", "").strip()
    if not key:
        p = os.path.join(os.path.dirname(__file__), "auth_key.txt")
        if os.path.exists(p):
            key = open(p, encoding="utf-8").read().strip()
    if not key:
        sys.exit("Thieu Auth-Key. Dat MB_AUTH_KEY hoac tao scripts/auth_key.txt "
                 "(lay key o https://auth.abuse.ch/).")
    return key


def existing_hashes(manifest: str) -> set[str]:
    have = set()
    if os.path.exists(manifest):
        with open(manifest, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                h = (row.get("sha256") or "").lower()
                if h:
                    have.add(h)
    return have


def get_info(session, key, h):
    r = session.post(API, headers={"Auth-Key": key},
                     data={"query": "get_info", "hash": h}, timeout=60)
    r.raise_for_status()
    js = r.json()
    if js.get("query_status") != "ok":
        return None, js.get("query_status", "unknown")
    data = js.get("data") or []
    return (data[0] if data else None), "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True, help="thu muc chua cac file <sha256>.zip")
    ap.add_argument("--group", default="G0", help="nhom ghi vao manifest (G0/G2...)")
    ap.add_argument("--family", default="", help="ghi de ten ho (vd agenttesla); bo trong = lay tag dau tu MB")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--sleep", type=float, default=1.0)
    args = ap.parse_args()

    try:
        import requests
    except ImportError:
        sys.exit("Can requests: pip install requests")

    if not os.path.isdir(args.folder):
        sys.exit(f"Khong thay thu muc: {args.folder}")

    key = load_key()
    session = requests.Session()
    have = existing_hashes(args.manifest)

    # tim cac file .zip co ten la sha256
    zips, bad = [], []
    for name in os.listdir(args.folder):
        if not name.lower().endswith(".zip"):
            continue
        stem = name[:-4]
        if SHA256_RE.match(stem):
            zips.append(stem.lower())
        else:
            bad.append(name)
    if bad:
        print(f"[!] Bo qua {len(bad)} file ten KHONG phai sha256: {bad[:3]}...")
    todo = [h for h in zips if h not in have]
    print(f"[1] Thu muc co {len(zips)} zip hop le, {len(have)} da co trong manifest "
          f"-> can khai sinh {len(todo)} mau.")
    if not todo:
        print("[xong] Khong co gi moi. Manifest da day du.")
        return

    new_file = not os.path.exists(args.manifest)
    os.makedirs(os.path.dirname(args.manifest) or ".", exist_ok=True)
    ok = miss = 0
    with open(args.manifest, "a", newline="", encoding="utf-8") as mf:
        w = csv.writer(mf)
        if new_file:
            w.writerow(COLS)
        for i, h in enumerate(todo, 1):
            info, status = get_info(session, key, h)
            if info is None:
                miss += 1
                print(f"  ({i}/{len(todo)}) MISS {h[:12]}... -> {status}")
                time.sleep(args.sleep)
                continue
            ftype = (info.get("file_type") or "").lower()
            tags = info.get("tags") or []
            family = args.family or (tags[0].lower() if tags else "unknown")
            note = "backfill tu folder (tai tay)"
            if ftype and ftype != "exe":
                note += f" | CANH BAO: file_type={ftype} (khong phai exe)"
            w.writerow([h, family, args.group, "none", "none", h, "",
                        "MalwareBazaar", info.get("first_seen", ""),
                        info.get("reporter", ""), info.get("signature", ""),
                        info.get("file_name", ""),
                        datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        note])
            ok += 1
            print(f"  ({i}/{len(todo)}) OK {h[:12]}... ho={family} type={ftype or '?'}")
            time.sleep(args.sleep)

    print(f"\n[xong] Khai sinh {ok} mau, khong tim thay {miss}. Manifest: {args.manifest}")
    if miss:
        print("  (MISS = MB khong con metadata/hash sai — kiem tra lai file do.)")


if __name__ == "__main__":
    main()
