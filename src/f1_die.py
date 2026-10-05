"""Cổng F1 — Detect It Easy (baseline CHÍNH) — [Trúc].

DiE nhận là packed/protected -> LOẠI (FILTERED). Đọc cột die_result trong manifest.
Đây là baseline để trả lời RQ4: UNMASK có hơn "dùng DiE loại mẫu pack" không?

API chung của mọi cổng (F0–F3):
    decide(row: dict) -> "PASS" | "FILTERED" | "FLAGGED"
"""
from __future__ import annotations


def decide(row: dict) -> str:
    die = str(row.get("die_result", "unknown")).lower()
    if die in ("packed", "protected"):
        return "FILTERED"
    return "PASS"


def run(df):
    """df cần có cột die_result (join từ manifest nếu dataset.csv không có)."""
    return [decide(r) for r in df.to_dict("records")]
