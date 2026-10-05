"""Cổng F2 — luật entropy cũ (như proposal) — [Trúc].

FILTERED nếu: entropy_max_section > 7.0 VÀ section_name_class == 'weird'/'known_packer'.
Đây là "luật cứng" để so với F3 (điểm đa đặc trưng + dual-check).
"""
from __future__ import annotations

ENTROPY_MAX_THRESHOLD = 7.0


def decide(row: dict, thr: float = ENTROPY_MAX_THRESHOLD) -> str:
    weird = str(row.get("section_name_class", "standard")) in ("weird", "known_packer")
    if float(row.get("entropy_max_section", 0)) > thr and weird:
        return "FILTERED"
    return "PASS"


def run(df, thr: float = ENTROPY_MAX_THRESHOLD):
    return [decide(r, thr) for r in df.to_dict("records")]
