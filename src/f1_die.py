"""Cổng F1 — Detect It Easy (baseline CHÍNH) — [Trúc].

DiE nhận là packed -> LOẠI (FILTERED). Đọc cột die_result_real từ die_real_v1.1.csv.
Lý do tách F1 / F1+protected: 12/122 mẫu G0 là .NET Reactor (protected/obfuscator, không phải packer).
- F1-DiE (chính): chỉ loại packed
- F1-DiE+protected (độ nhạy): loại cả packed + protected

API chung của mọi cổng (F0–F3):
    decide(row: dict, variant: str = "packed_only") -> "PASS" | "FILTERED" | "FLAGGED"
"""
from __future__ import annotations


def decide(row: dict, variant: str = "packed_only") -> str:
    """
    variant: "packed_only" (F1-DiE chính) | "packed_protected" (F1-DiE+protected độ nhạy)
             | "oracle" (F1-oracle: nhãn lý tưởng die_result từ manifest — CẬN LÝ THUYẾT, không phải detector thật)
    """
    if variant == "oracle":
        return "FILTERED" if str(row.get("die_result", "unknown")).lower() == "packed" else "PASS"
    die = str(row.get("die_result_real", "unknown")).lower()

    if variant == "packed_only":
        if die == "packed":
            return "FILTERED"
    elif variant == "packed_protected":
        if die in ("packed", "protected"):
            return "FILTERED"

    return "PASS"


def run(df, variant: str = "packed_only"):
    """df cần có cột die_result_real (join từ die_real_v1.1.csv); variant="oracle" cần cột die_result (join từ manifest_v1.1.csv)."""
    return [decide(r, variant=variant) for r in df.to_dict("records")]
