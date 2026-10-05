"""Nguồn sự thật DUY NHẤT về tên cột — mọi file import từ đây (khớp schema.md).

Đổi cột ở đây = đổi cả nhóm. Đừng hardcode tên cột rải rác trong code.
"""

ID_COLS = [
    "sha256", "family", "group", "variant", "packer", "origin_sha256",
]

# Feature tĩnh (dùng cho packed_score, detector, F2...)
FEATURE_COLS = [
    "entropy_file", "entropy_max_section", "entropy_mean_section",
    "high_entropy_byte_ratio",
    "num_sections", "section_name_class", "raw_virtual_ratio",
    "ep_section_writable",
    "num_dll", "num_api", "import_table_shrink", "only_dynamic_loader_imports",
    "file_size", "size_of_headers", "checksum_valid", "compile_timestamp",
    "has_overlay", "overlay_size",
    "is_dotnet",
]

# Các feature "liên quan đến packing" (bước 1) — dual-check sẽ BỎ các cột này khi so lõi.
# Gồm mọi feature mà packer VIẾT LẠI: entropy, section, import table (num_dll/num_api teo),
# raw/virtual, overlay, checksum. Giữ lại phần "lõi" packer thường không đổi.
PACKING_FEATURE_COLS = [
    "entropy_file", "entropy_max_section", "entropy_mean_section",
    "high_entropy_byte_ratio", "raw_virtual_ratio", "ep_section_writable",
    "import_table_shrink", "only_dynamic_loader_imports",
    "has_overlay", "overlay_size", "section_name_class",
    "num_dll", "num_api", "num_sections", "checksum_valid",
]

# Feature "lõi" dùng cho dual-check (so phần không bị packer viết lại):
# kích thước header, timestamp biên dịch, có phải .NET, kích thước gốc.
# TODO(Tuấn/Khánh): kiểm trên dữ liệu THẬT xem feature nào thực sự sống sót qua packer
#                   (UPX/MPRESS/ASPack) — đây là giả định cốt lõi của dual-check.
CORE_FEATURE_COLS = [c for c in FEATURE_COLS if c not in PACKING_FEATURE_COLS]

LABEL_COLS = ["is_drift_truth", "split"]

DATASET_COLS = ID_COLS + FEATURE_COLS + LABEL_COLS

MANIFEST_EXTRA_COLS = [
    "die_result", "removed_prepacked", "pack_failed",
    "source", "timestamp_collected", "note",
]
MANIFEST_COLS = ID_COLS + MANIFEST_EXTRA_COLS

# Giá trị hợp lệ (dùng cho check_data.py)
VALID_GROUPS = {"G0", "G1", "G2", "G3"}
VALID_VARIANTS = {"none", "P-seen", "P-unseen", "P-low", "P-wild"}
VALID_PACKERS = {"none", "upx", "mpress", "aspack", "wild"}
VALID_SECTION_CLASS = {"standard", "known_packer", "weird"}
VALID_DIE = {"clean", "packed", "protected", "unknown"}
VALID_SPLIT = {"train", "val", "test"}

# Nhãn đúng theo nhóm: G0,G1 = không drift (0); G2,G3 = drift thật (1)
GROUP_IS_DRIFT = {"G0": 0, "G1": 0, "G2": 1, "G3": 1}
