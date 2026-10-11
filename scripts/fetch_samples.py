"""fetch_samples.py — Tải mẫu từ MalwareBazaar theo tag, LỌC exe, ĐA DẠNG reporter,
ghi manifest tái lập. TẢI DẠNG ZIP KHÓA — KHÔNG giải nén (giải nén làm trong VM).

An toàn: script chỉ tải file .zip (mật khẩu 'infected') + ghi metadata. Không mở,
không giải nén, không chạy mẫu. Di chuyển cả thư mục zip vào VM rồi mới giải nén.

Chuẩn bị:
  1. Lấy Auth-Key free ở https://auth.abuse.ch/  (đăng ký email).
  2. Đặt key vào biến môi trường MB_AUTH_KEY, hoặc tạo file scripts/auth_key.txt chứa key.
     (ĐỪNG commit key lên git — thêm 'scripts/auth_key.txt' vào .gitignore.)

Dùng:
  # G0 - AgentTesla, mục tiêu 130 mẫu exe, tối đa 3 mẫu / reporter
  python scripts/fetch_samples.py --tag AgentTesla --group G0 --n 130 --out data/raw_zips

  # G2 - njRAT / Formbook
  python scripts/fetch_samples.py --tag njrat   --group G2 --n 60 --out data/raw_zips
  python scripts/fetch_samples.py --tag Formbook --group G2 --n 60 --out data/raw_zips
"""
from __future__ import annotations
import argparse
import csv
import os
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone

API = "https://mb-api.abuse.ch/api/v1/"


def load_key() -> str:
    key = os.environ.get("MB_AUTH_KEY", "").strip()
    if not key:
        p = os.path.join(os.path.dirname(__file__), "auth_key.txt")
        if os.path.exists(p):
            key = open(p, encoding="utf-8").read().strip()
    if not key:
        sys.exit("Thiếu Auth-Key. Đặt MB_AUTH_KEY hoặc tạo scripts/auth_key.txt "
                 "(lấy key ở https://auth.abuse.ch/).")
    return key


def get_tag_list(session, key, tag, limit=1000):
    r = session.post(API, headers={"Auth-Key": key},
                     data={"query": "get_taginfo", "tag": tag, "limit": str(limit)},
                     timeout=60)
    r.raise_for_status()
    js = r.json()
    if js.get("query_status") != "ok":
        sys.exit(f"API get_taginfo lỗi: {js.get('query_status')} "
                 f"(kiểm tra Auth-Key / tag '{tag}').")
    return js.get("data", [])


def pick(rows, n, per_reporter, seed):
    """Lọc exe, unique, cap theo reporter, random trải."""
    rng = random.Random(seed)
    exe = [r for r in rows if (r.get("file_type") or "").lower() == "exe"]
    # unique theo sha256
    seen, uniq = set(), []
    for r in exe:
        h = r.get("sha256_hash")
        if h and h not in seen:
            seen.add(h); uniq.append(r)
    rng.shuffle(uniq)
    cap, chosen = Counter(), []
    for r in uniq:
        rep = r.get("reporter") or "unknown"
        if cap[rep] >= per_reporter:
            continue
        cap[rep] += 1
        chosen.append(r)
        if len(chosen) >= n:
            break
    return chosen


def download(session, key, h, out_dir):
    r = session.post(API, headers={"Auth-Key": key},
                     data={"query": "get_file", "sha256_hash": h}, timeout=120)
    ctype = r.headers.get("Content-Type", "")
    if "application/zip" in ctype or r.content[:2] == b"PK":
        path = os.path.join(out_dir, f"{h}.zip")
        with open(path, "wb") as f:
            f.write(r.content)
        return True, len(r.content)
    # không phải zip -> lỗi (file_not_found / limit...)
    try:
        return False, r.json().get("query_status", "unknown")
    except Exception:
        return False, "unknown"


def load_existing(manifest, out_dir):
    """Hash đã có (trong manifest HOẶC đã tải trên đĩa) -> để không tải/ghi trùng."""
    have = set()
    if os.path.exists(manifest):
        with open(manifest, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                h = (row.get("sha256") or "").lower()
                if h:
                    have.add(h)
    if os.path.isdir(out_dir):
        for name in os.listdir(out_dir):
            if name.lower().endswith(".zip"):
                have.add(name[:-4].lower())
    return have


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="AgentTesla | njrat | Formbook ...")
    ap.add_argument("--group", required=True, help="G0 | G2 (ghi vào manifest)")
    ap.add_argument("--n", type=int, default=130)
    ap.add_argument("--per-reporter", type=int, default=3, help="chống thiên lệch chiến dịch")
    ap.add_argument("--out", default="data/raw_zips")
    ap.add_argument("--manifest", default="data/raw_manifest.csv")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=1.0, help="giây nghỉ giữa mỗi lần tải")
    args = ap.parse_args()

    try:
        import requests
    except ImportError:
        sys.exit("Cần requests: pip install requests")

    key = load_key()
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.dirname(args.manifest) or ".", exist_ok=True)
    session = requests.Session()

    print(f"[1] Lấy danh sách tag '{args.tag}'...")
    rows = get_tag_list(session, key, args.tag)
    have = load_existing(args.manifest, args.out)
    before = len(rows)
    rows = [r for r in rows if (r.get("sha256_hash") or "").lower() not in have]
    chosen = pick(rows, args.n, args.per_reporter, args.seed)
    print(f"[2] {before} bản ghi API, đã có sẵn {len(have)} hash → còn {len(rows)} mẫu MỚI "
          f"→ lọc exe/unique/đa reporter → chọn {len(chosen)} mẫu.")
    print(f"    Phân bố reporter: {dict(Counter(r.get('reporter') for r in chosen))}")

    new = not os.path.exists(args.manifest)
    ok = fail = 0
    with open(args.manifest, "a", newline="", encoding="utf-8") as mf:
        w = csv.writer(mf)
        if new:
            w.writerow(["sha256", "family", "group", "variant", "packer", "origin_sha256",
                        "die_result", "source", "first_seen", "reporter", "signature",
                        "file_name", "downloaded_at", "note"])
        for i, r in enumerate(chosen, 1):
            h = r["sha256_hash"]
            good, info = download(session, key, h, args.out)
            if good:
                ok += 1
                w.writerow([h, args.tag.lower(), args.group, "none", "none", h,
                            "", "MalwareBazaar", r.get("first_seen", ""),
                            r.get("reporter", ""), r.get("signature", ""),
                            r.get("file_name", ""),
                            datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "zip chua giai nen"])
                print(f"  ({i}/{len(chosen)}) OK {h[:12]}… {info} bytes")
            else:
                fail += 1
                print(f"  ({i}/{len(chosen)}) FAIL {h[:12]}… -> {info}")
                if info == "no_sample_found":
                    pass
                elif "limit" in str(info).lower():
                    print("  !! Đụng giới hạn tải/ngày — dừng, mai chạy tiếp (manifest đã lưu).")
                    break
            time.sleep(args.sleep)

    print(f"\n[xong] Tải OK {ok}, lỗi {fail}. Zip ở: {args.out}")
    print(f"       Manifest: {args.manifest}")
    print("⚠️  KHÔNG giải nén ở đây. Chép cả thư mục zip vào VM rồi giải nén (mật khẩu: infected).")


if __name__ == "__main__":
    main()
