"""Sinh mock_dataset.csv + mock_manifest.csv (file GIẢ) để cả nhóm code song song ngay.

Số liệu được bịa sao cho *hợp lý về mặt hướng*: file pack có entropy cao hơn,
import teo hơn, raw/virtual bất thường... để code phía sau chạy ra kết quả
"có vẻ đúng" trên mock. KHÔNG phải dữ liệu thật.

    python mock/make_mock_dataset.py            # -> mock/mock_dataset.csv, mock/mock_manifest.csv
    python mock/make_mock_dataset.py --n 300 --seed 0
"""
from __future__ import annotations
import argparse
import hashlib
import os
import random
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import schema_cols as S  # noqa: E402

HERE = os.path.dirname(__file__)
PACKERS_SEEN = "upx"
PACKERS_UNSEEN = ["mpress", "aspack"]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _base_core(family: str, rng: random.Random) -> dict:
    """Feature 'lõi' của một mẫu gốc — biến thể sẽ giữ gần giống phần này."""
    is_dotnet = 1 if family == "agenttesla" else rng.choice([0, 0, 1])
    return {
        "family": family,
        "is_dotnet": is_dotnet,
        "file_size": rng.randint(80_000, 400_000),
        "size_of_headers": rng.choice([512, 1024]),
        "compile_timestamp": rng.randint(1_500_000_000, 1_700_000_000),
        "num_dll_core": rng.randint(3, 8),
        "num_api_core": rng.randint(40, 120),
    }


def _row_from(core: dict, group: str, variant: str, packer: str,
              origin_sha: str, rng: random.Random) -> dict:
    packed = group in ("G1", "G3") or variant in ("P-low", "P-wild")
    low = variant == "P-low"

    if not packed:
        ent_max = rng.uniform(5.5, 6.8)
        ent_file = rng.uniform(5.0, 6.5)
        shrink = rng.uniform(0.0, 0.2)
        rv = rng.uniform(0.8, 1.05)
        sec_class = "standard"
        ep_w = 0
        num_api = core["num_api_core"]
        high_ratio = rng.uniform(0.0, 0.15)
        overlay = 0
    else:
        ent_max = rng.uniform(6.2, 7.0) if low else rng.uniform(7.1, 7.99)
        ent_file = ent_max - rng.uniform(0.3, 1.2)
        shrink = rng.uniform(0.5, 0.95)          # import teo mạnh khi pack
        rv = rng.uniform(1.5, 6.0)               # raw/virtual bất thường
        sec_class = "known_packer" if packer in ("upx", "mpress", "aspack") else "weird"
        ep_w = 1
        num_api = max(5, int(core["num_api_core"] * rng.uniform(0.05, 0.3)))
        high_ratio = rng.uniform(0.25, 0.55) if low else rng.uniform(0.55, 0.9)
        overlay = rng.randint(0, 2000)

    sha = _sha(f"{origin_sha}|{group}|{variant}|{packer}|{rng.random()}")
    return {
        "sha256": sha,
        "family": core["family"],
        "group": group,
        "variant": variant,
        "packer": packer,
        "origin_sha256": origin_sha,
        "entropy_file": round(ent_file, 3),
        "entropy_max_section": round(ent_max, 3),
        "entropy_mean_section": round(ent_file - rng.uniform(0.0, 0.5), 3),
        "high_entropy_byte_ratio": round(high_ratio, 3),
        "num_sections": rng.randint(3, 6) + (1 if packed else 0),
        "section_name_class": sec_class,
        "raw_virtual_ratio": round(rv, 3),
        "ep_section_writable": ep_w,
        "num_dll": core["num_dll_core"],
        "num_api": num_api,
        "import_table_shrink": round(shrink, 3),
        "only_dynamic_loader_imports": 1 if (packed and num_api < 15) else 0,
        "file_size": core["file_size"] + (overlay if overlay else 0),
        "size_of_headers": core["size_of_headers"],
        "checksum_valid": 0 if packed else rng.choice([0, 1]),
        "compile_timestamp": core["compile_timestamp"],
        "has_overlay": 1 if overlay else 0,
        "overlay_size": overlay,
        "is_dotnet": core["is_dotnet"],
        "is_drift_truth": S.GROUP_IS_DRIFT[group],
        # split điền tạm, split_data.py sẽ ghi đè theo origin_sha256
        "split": "train",
        # manifest extra
        "die_result": "packed" if packed else "clean",
        "removed_prepacked": 0,
        "pack_failed": 0,
        "source": "derived" if (packed or group in ("G1", "G3")) else "malwarebazaar",
        "timestamp_collected": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "MOCK",
    }


def build(n_origins: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    families_g0 = ["agenttesla"]
    families_g2 = ["njrat", "formbook", "agenttesla"]  # AgentTesla khác thời kỳ cũng tính G2

    for i in range(n_origins):
        # --- G0 lõi gốc (AgentTesla) ---
        core0 = _base_core("agenttesla", rng)
        g0_sha = _sha(f"g0|{i}|{seed}")
        rows.append(_row_from(core0, "G0", "none", "none", g0_sha, rng))
        # G1 = G0 × 3 packer
        rows.append(_row_from(core0, "G1", "P-seen", "upx", g0_sha, rng))
        for p in PACKERS_UNSEEN:
            rows.append(_row_from(core0, "G1", "P-unseen", p, g0_sha, rng))
        # P-low từ G0
        rows.append(_row_from(core0, "G1", "P-low", "upx", g0_sha, rng))

        # --- G2 đổi lõi ---
        fam = families_g2[i % len(families_g2)]
        core2 = _base_core(fam, rng)
        g2_sha = _sha(f"g2|{i}|{seed}")
        rows.append(_row_from(core2, "G2", "none", "none", g2_sha, rng))
        # G3 = G2 × 3 packer
        rows.append(_row_from(core2, "G3", "P-seen", "upx", g2_sha, rng))
        for p in PACKERS_UNSEEN:
            rows.append(_row_from(core2, "G3", "P-unseen", p, g2_sha, rng))

        # --- P-wild: AgentTesla bọc sẵn ngoài đời ---
        if i % 3 == 0:
            corew = _base_core("agenttesla", rng)
            w_sha = _sha(f"wild|{i}|{seed}")
            rows.append(_row_from(corew, "G1", "P-wild", "wild", w_sha, rng))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12, help="số mẫu gốc (mỗi mẫu đẻ nhiều biến thể)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(HERE, "mock_dataset.csv"))
    ap.add_argument("--manifest", default=os.path.join(HERE, "mock_manifest.csv"))
    args = ap.parse_args()

    try:
        import pandas as pd
    except ImportError:
        sys.exit("Cần pandas: pip install -r requirements.txt")

    rows = build(args.n, args.seed)
    df = pd.DataFrame(rows)
    df[S.DATASET_COLS].to_csv(args.out, index=False)
    df[S.MANIFEST_COLS].to_csv(args.manifest, index=False)
    print(f"[mock] {len(df)} dòng  (G0={sum(df.group=='G0')} G1={sum(df.group=='G1')} "
          f"G2={sum(df.group=='G2')} G3={sum(df.group=='G3')})")
    print(f"[mock] -> {args.out}")
    print(f"[mock] -> {args.manifest}")


if __name__ == "__main__":
    main()
