#!/usr/bin/env python3
"""Quét DiE thật, match file bằng cách TỰ HASH (không dựa tên file vì G1/G3 đặt tên khác sha256)."""
import csv, hashlib, os, subprocess, sys
from collections import Counter

MANIFEST = "manifest_v1.1.csv"
DATASETS_ROOT = os.path.expanduser("~/IAM302t/Datasets")
SEARCH_DIRS = ["g0_all", "g1_upx_v11", "g1_mpress_v11", "g2_live", "g3_mpress"]
OUT_CSV = "results/die_real_v1.1.csv"
OUT_NOTES = "docs/die_real_notes.md"
DIEC = os.path.expanduser("~/die_portable/die_linux_portable/diec.sh")

def sha256_of(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def index_by_hash():
    idx = {}
    for d in SEARCH_DIRS:
        root = os.path.join(DATASETS_ROOT, d)
        if not os.path.isdir(root):
            print(f"[!] thieu thu muc: {root}")
            continue
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if fn.lower().endswith((".csv", ".txt", ".json", ".md")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    h = sha256_of(path)
                except Exception:
                    continue
                idx[h] = path
    return idx

def classify(raw_out: str) -> str:
    low = raw_out.lower()
    if "protector" in low:
        return "protected"
    if "packer:" in low:
        return "packed"
    first_line = raw_out.strip().splitlines()[0].lower() if raw_out.strip() else ""
    if not raw_out.strip() or "unknown" in first_line:
        return "unknown"
    return "clean"

def main():
    print("[+] Hashing file that trong 5 thu muc nguon (vai phut)...")
    idx = index_by_hash()
    print(f"[+] Da hash {len(idx)} file")

    with open(MANIFEST, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    rows_out, missing = [], []
    for i, r in enumerate(rows, 1):
        sha = r["sha256"].lower().strip()
        group = r.get("group", "")
        path = idx.get(sha)
        if not path:
            missing.append((sha, group))
            continue
        try:
            proc = subprocess.run([DIEC, path], capture_output=True, text=True, timeout=30)
            raw_out = proc.stdout.strip() or proc.stderr.strip()
        except Exception as e:
            raw_out = f"ERROR: {e}"
        result = classify(raw_out)
        detect_line = next((l.strip() for l in raw_out.splitlines()
                             if "packer" in l.lower() or "protector" in l.lower()), "")
        rows_out.append({
            "sha256": sha, "group": group, "die_version": "die 3.21",
            "die_raw": raw_out.replace("\n", " | "),
            "die_detect": detect_line, "die_result_real": result,
        })
        if i % 50 == 0 or i == len(rows):
            print(f"[{i}/{len(rows)}] done, {len(missing)} missing so far")

    os.makedirs("results", exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sha256", "group", "die_version", "die_raw", "die_detect", "die_result_real"])
        w.writeheader()
        w.writerows(rows_out)

    by_group = {}
    for r in rows_out:
        by_group.setdefault(r["group"], Counter())[r["die_result_real"]] += 1
    keys = sorted({k for c in by_group.values() for k in c})

    with open(OUT_NOTES, "w", encoding="utf-8") as f:
        f.write("# DiE real scan notes\n\n")
        f.write("- Tool: Detect It Easy (diec) v3.21, portable Linux build\n")
        f.write(f"- Scanned: {len(rows_out)}/{len(rows)} mau (thieu {len(missing)})\n\n")
        f.write("## Bang dem theo nhom\n\n| Group | " + " | ".join(keys) + " |\n")
        f.write("|---|" + "---|" * len(keys) + "\n")
        for g, c in sorted(by_group.items()):
            f.write(f"| {g} | " + " | ".join(str(c.get(k, 0)) for k in keys) + " |\n")
        if missing:
            f.write(f"\n## Thieu raw file ({len(missing)})\n")
            for sha, g in missing[:80]:
                f.write(f"- {g}: {sha}\n")

    print(f"\n[OK] -> {OUT_CSV} ({len(rows_out)} dong), thieu {len(missing)}")

if __name__ == "__main__":
    sys.exit(main())
