"""Trích FEATURE TĨNH từ file PE — [Tuấn].

CHỈ ĐỌC cấu trúc file (pefile/LIEF). KHÔNG chạy file. Chạy TRONG VM trên thư mục mẫu.
Xuất CSV đúng schema.md (ID + feature). import_table_shrink cần chuẩn hoá theo trung vị
cùng họ -> tính ở bước post-process (hàm add_import_shrink).

    # trong VM:
    python src/extract_features.py --in data/raw --group G0 --family agenttesla \\
        --out part_g0.csv
    # sau khi gộp các part -> chuẩn hoá import shrink:
    python src/extract_features.py --finalize dataset_raw.csv --out dataset.csv

An toàn: script này không thực thi mẫu; chỉ parse header/section/import.
"""
from __future__ import annotations
import argparse
import math
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import schema_cols as S  # noqa: E402

# Tên section hay gặp ở packer phổ thông (để phân loại section_name_class)
KNOWN_PACKER_SECTIONS = {
    "upx0", "upx1", "upx2", ".aspack", ".adata", ".mpress1", ".mpress2",
    ".packed", "pec1", ".petite", "nsp0", "nsp1",
}
STANDARD_SECTIONS = {
    ".text", ".data", ".rdata", ".rsrc", ".reloc", ".idata", ".edata",
    ".bss", ".tls", ".pdata", ".didat",
}


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = [0] * 256
    for b in data:
        freq[b] += 1
    n = len(data)
    ent = 0.0
    for c in freq:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return ent


# Tập API "loader" tối thiểu: file chỉ import những hàm này gần như chắc chắn là stub tự giải nén.
LOADER_APIS = frozenset({
    "getprocaddress", "loadlibrarya", "loadlibraryw", "loadlibraryexa", "loadlibraryexw",
    "virtualprotect", "virtualalloc", "exitprocess",
})


def only_loader_imports(api_names) -> int:
    """1 nếu có ít nhất 1 API được import theo tên và TẤT CẢ đều nằm trong LOADER_APIS.
    Import theo số thứ tự (không có tên) bị bỏ qua. Không có API nào -> 0."""
    names = {str(n).lower() for n in api_names if n}
    return 1 if names and names <= LOADER_APIS else 0


def window_entropy_ratio(raw: bytes, win: int = 1024, thr: float = 7.0) -> float:
    """Tỉ lệ cửa sổ `win` byte (không chồng lấp) có entropy Shannon > thr.
    File ngắn hơn 1 cửa sổ -> 0.0."""
    a = np.frombuffer(raw, dtype=np.uint8)
    n = len(a) // win
    if n == 0:
        return 0.0
    hi = 0
    for i in range(n):
        c = np.bincount(a[i * win:(i + 1) * win], minlength=256)
        p = c[c > 0] / win
        if -(p * np.log2(p)).sum() > thr:
            hi += 1
    return round(hi / n, 3)


IMAGE_SCN_MEM_EXECUTE = 0x20000000
IMAGE_SCN_MEM_WRITE = 0x80000000


def ep_section_wx(characteristics: int) -> int:
    """1 nếu section chứa entry point vừa Writable vừa Executable (W+X), khớp schema.md."""
    both = IMAGE_SCN_MEM_EXECUTE | IMAGE_SCN_MEM_WRITE
    return 1 if (characteristics & both) == both else 0


def extract_one(path: str) -> dict:
    """Trả dict feature cho 1 file PE. import_table_shrink để tạm = số API thô (chuẩn hoá sau)."""
    import pefile
    pe = pefile.PE(path, fast_load=False)  # chỉ parse, không execute
    with open(path, "rb") as f:
        raw = f.read()

    file_size = len(raw)
    sec_entropies, names, ep_writable = [], [], 0
    ep = pe.OPTIONAL_HEADER.AddressOfEntryPoint
    raw_total = virt_total = 0
    for s in pe.sections:
        d = s.get_data()
        sec_entropies.append(shannon_entropy(d))
        nm = s.Name.rstrip(b"\x00").decode("latin-1", "ignore").lower()
        names.append(nm)
        raw_total += s.SizeOfRawData
        virt_total += max(1, s.Misc_VirtualSize)
        if s.contains_rva(ep):
            ep_writable = ep_section_wx(s.Characteristics)  # W+X theo schema.md

    def classify(nm: str) -> str:
        if nm in KNOWN_PACKER_SECTIONS:
            return "known_packer"
        if nm in STANDARD_SECTIONS:
            return "standard"
        return "weird"
    classes = [classify(n) for n in names]
    sec_class = ("known_packer" if "known_packer" in classes
                 else "weird" if "weird" in classes else "standard")

    num_dll = num_api = 0
    api_names = []
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        num_dll = len(pe.DIRECTORY_ENTRY_IMPORT)
        num_api = sum(len(e.imports) for e in pe.DIRECTORY_ENTRY_IMPORT)
        api_names = [i.name.decode("latin-1", "ignore") for e in pe.DIRECTORY_ENTRY_IMPORT
                     for i in e.imports if i.name]

    # overlay = phần dữ liệu sau section cuối
    last_end = max((s.PointerToRawData + s.SizeOfRawData) for s in pe.sections) if pe.sections else 0
    overlay_size = max(0, file_size - last_end)

    is_dotnet = 0
    try:
        de = pe.OPTIONAL_HEADER.DATA_DIRECTORY[14]  # COM descriptor
        is_dotnet = 1 if de.VirtualAddress else 0
    except Exception:
        pass

    try:
        checksum_valid = 1 if pe.verify_checksum() else 0
    except Exception:
        checksum_valid = 0

    feat = {
        "entropy_file": round(shannon_entropy(raw), 3),
        "entropy_max_section": round(max(sec_entropies) if sec_entropies else 0, 3),
        "entropy_mean_section": round(sum(sec_entropies) / len(sec_entropies), 3) if sec_entropies else 0,
        "high_entropy_byte_ratio": window_entropy_ratio(raw),
        "num_sections": len(pe.sections),
        "section_name_class": sec_class,
        "raw_virtual_ratio": round(raw_total / virt_total, 3) if virt_total else 0,
        "ep_section_writable": ep_writable,
        "num_dll": num_dll,
        "num_api": num_api,
        "import_table_shrink": float(num_api),  # tạm thời; finalize sẽ chuẩn hoá
        "only_dynamic_loader_imports": only_loader_imports(api_names),
        "file_size": file_size,
        "size_of_headers": pe.OPTIONAL_HEADER.SizeOfHeaders,
        "checksum_valid": checksum_valid,
        "compile_timestamp": int(pe.FILE_HEADER.TimeDateStamp),
        "has_overlay": 1 if overlay_size else 0,
        "overlay_size": overlay_size,
        "is_dotnet": is_dotnet,
    }
    pe.close()
    return feat


def add_import_shrink(df):
    """Chuẩn hoá import_table_shrink = 1 - (num_api / trung vị num_api của mẫu CHƯA PACK cùng họ).
    Càng gần 1 = import teo mạnh (dấu hiệu pack)."""
    import numpy as np
    base = df[df["group"].isin(["G0", "G2"])].groupby("family")["num_api"].median()
    def shrink(row):
        med = base.get(row["family"], np.nan)
        if not med or med != med:
            return 0.0
        return round(max(0.0, 1 - row["num_api"] / med), 3)
    df = df.copy()
    df["import_table_shrink"] = df.apply(shrink, axis=1)
    return df


def load_origin_map(path: str) -> dict:
    """Đọc CSV 2 cột `filename,origin_sha256` -> dict {filename: origin_sha256}."""
    import csv
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        need = {"filename", "origin_sha256"}
        if not rd.fieldnames or not need <= set(rd.fieldnames):
            raise ValueError(f"{path}: cần cột {sorted(need)}, có {rd.fieldnames}")
        return {r["filename"]: r["origin_sha256"].strip() for r in rd if r["origin_sha256"].strip()}


def resolve_origin(group: str, sha: str, filename: str, origin_map: dict):
    """G0/G2 (chưa pack): mẫu gốc tự trỏ về chính nó. G1/G3 (đã pack): lấy từ origin_map.
    Trả None nếu G1/G3 mà không có trong map (người gọi phải ghi lỗi, không được để trống)."""
    if group in ("G0", "G2"):
        return sha
    return origin_map.get(filename) or None


def add_drift_truth(df):
    """Thêm is_drift_truth theo GROUP_IS_DRIFT (G0,G1=0; G2,G3=1). Group lạ -> ValueError."""
    bad = sorted(set(df["group"]) - set(S.GROUP_IS_DRIFT))
    if bad:
        raise ValueError(f"group không hợp lệ: {bad}")
    df = df.copy()
    df["is_drift_truth"] = df["group"].map(S.GROUP_IS_DRIFT).astype(int)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", help="thư mục chứa mẫu (trong VM)")
    ap.add_argument("--group"); ap.add_argument("--family")
    ap.add_argument("--variant", default="none"); ap.add_argument("--packer", default="none")
    ap.add_argument("--finalize", help="CSV thô -> chuẩn hoá import_shrink")
    ap.add_argument("--origin-map", dest="origin_map", help="CSV filename,origin_sha256 (bắt buộc cho G1/G3)")
    ap.add_argument("--errors", help="file ghi lỗi (mặc định: extract_errors.csv cạnh --out, ghi nối)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import pandas as pd

    if args.finalize:
        df = add_drift_truth(add_import_shrink(pd.read_csv(args.finalize)))
        df.to_csv(args.out, index=False)
        print(f"[finalize] chuẩn hoá import_shrink + is_drift_truth -> {args.out}")
        return

    import csv
    import hashlib
    if not args.indir or not args.group:
        ap.error("cần --in và --group (hoặc dùng --finalize)")
    for nm, val, ok in (("group", args.group, S.VALID_GROUPS),
                        ("variant", args.variant, S.VALID_VARIANTS),
                        ("packer", args.packer, S.VALID_PACKERS)):
        if val not in ok:
            ap.error(f"--{nm} '{val}' không hợp lệ, hợp lệ: {sorted(ok)}")
    origin_map = load_origin_map(args.origin_map) if args.origin_map else {}
    err_path = args.errors or os.path.join(os.path.dirname(os.path.abspath(args.out)), "extract_errors.csv")

    rows, errors = [], []
    for fn in sorted(os.listdir(args.indir)):
        p = os.path.join(args.indir, fn)
        if not os.path.isfile(p):
            continue
        try:
            feat = extract_one(p)
            with open(p, "rb") as fh:
                sha = hashlib.sha256(fh.read()).hexdigest()
        except Exception as e:  # không parse được -> ghi lại, không chết
            errors.append({"file": fn, "group": args.group, "family": args.family, "reason": f"parse: {e}"})
            print(f"  [skip] {fn}: {e}")
            continue
        origin = resolve_origin(args.group, sha, fn, origin_map)
        if origin is None:
            errors.append({"file": fn, "group": args.group, "family": args.family,
                           "reason": "thiếu origin_sha256 trong --origin-map"})
            print(f"  [skip] {fn}: thiếu origin_sha256")
            continue
        feat.update({
            "sha256": sha, "family": args.family, "group": args.group,
            "variant": args.variant, "packer": args.packer, "origin_sha256": origin,
        })
        rows.append(feat)

    if errors:
        new_file = not os.path.exists(err_path)
        with open(err_path, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["file", "group", "family", "reason"])
            if new_file:
                w.writeheader()
            w.writerows(errors)
    if not rows:
        print(f"[extract] 0 file hợp lệ, {len(errors)} lỗi -> {err_path} (không ghi {args.out})")
        sys.exit(1)
    pd.DataFrame(rows).to_csv(args.out, index=False)
    print(f"[extract] {len(rows)} file, {len(errors)} lỗi -> {args.out}")


if __name__ == "__main__":
    main()
