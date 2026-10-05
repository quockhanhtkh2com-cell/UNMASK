"""F3 — Cổng UNMASK: gộp packed_score + dual_check -> 3 quyết định — [Tuấn].

    PASS      điểm pack thấp -> không bị pack -> vào chuông
    FILTERED  pack cao + lõi giống mẫu đã biết -> chỉ đổi vỏ -> loại, ghi log
    FLAGGED   pack cao + lõi lạ -> vào chuông + cờ (không làm hệ thống mù trước L1)

Đầu ra mỗi file: {packed_score, decision, evidence}.

Dùng:
    # trên 1 file PE thật (trong VM):
    from unmask import filter_file
    filter_file("mau.exe")

    # trên dataset.csv (CLI, cho thí nghiệm / mock):
    python -m unmask.filter --dataset mock/mock_dataset.csv --out results/demo_f3.csv
    python -m unmask.filter --dataset mock/mock_dataset.csv --no-dualcheck   # = F3a
"""
from __future__ import annotations
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import schema_cols as S  # noqa: E402
from .packed_score import PackedScorer
from .dual_check import DualCheck


class UnmaskFilter:
    def __init__(self, scorer: PackedScorer, dual: DualCheck | None = None,
                 use_dualcheck: bool = True):
        self.scorer = scorer
        self.dual = dual
        self.use_dualcheck = use_dualcheck and dual is not None

    def decide(self, feat: dict) -> dict:
        score = self.scorer.score(feat)
        evidence = self.scorer.evidence(feat)
        if score < self.scorer.threshold:
            decision = "PASS"
        elif not self.use_dualcheck:
            decision = "FILTERED"      # F3a: không dual-check -> pack cao là loại
        else:
            core = [float(feat.get(c, 0) or 0) for c in S.CORE_FEATURE_COLS
                    if c not in ("section_name_class",)]
            verdict = self.dual.check(core)
            decision = "FILTERED" if verdict == "similar" else "FLAGGED"
        return {"packed_score": round(score, 4), "decision": decision, "evidence": evidence}


# ---- API cho module pip ----
def filter_row(feat: dict, locked_config: dict | None = None) -> dict:
    """Chạy F3 trên 1 dict feature (đã trích sẵn)."""
    scorer = PackedScorer.load(locked_config) if locked_config else PackedScorer()
    return UnmaskFilter(scorer, dual=None, use_dualcheck=False).decide(feat)


def filter_file(path: str, locked_config: dict | None = None) -> dict:
    """Chạy F3 trên 1 file PE thật: trích feature tĩnh rồi quyết định. KHÔNG chạy file."""
    from extract_features import extract_one
    feat = extract_one(path)
    out = filter_row(feat, locked_config)
    out["file"] = os.path.basename(path)
    return out


def _load_locked() -> dict | None:
    p = os.path.join(os.path.dirname(__file__), "..", "config", "thresholds.locked.json")
    if os.path.exists(p):
        cfg = json.load(open(p))
        return cfg if cfg.get("locked") else None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-dualcheck", action="store_true", help="chạy ở chế độ F3a (ablation)")
    args = ap.parse_args()
    import numpy as np, pandas as pd

    df = pd.read_csv(args.dataset)
    locked = _load_locked()
    scorer = PackedScorer.load(locked) if locked else PackedScorer()

    # dual-check: fit tham chiếu trên G0 (lõi AgentTesla đã biết) của tập train/val
    dual = None
    if not args.no_dualcheck:
        core_cols = [c for c in S.CORE_FEATURE_COLS if c != "section_name_class"]
        ref = df[(df.group == "G0")][core_cols].to_numpy(dtype=float)
        if len(ref) >= 3:
            dual = DualCheck(ref)
            val = df[(df.group == "G0")][core_cols].to_numpy(dtype=float)
            dual.lock_threshold(val, p=95)

    f = UnmaskFilter(scorer, dual=dual, use_dualcheck=not args.no_dualcheck)
    results = [f.decide(r) for r in df.to_dict("records")]
    out_df = df[["sha256", "group", "variant", "packer"]].copy()
    out_df["packed_score"] = [r["packed_score"] for r in results]
    out_df["decision"] = [r["decision"] for r in results]
    out_df["evidence"] = [json.dumps(r["evidence"], ensure_ascii=False) for r in results]

    from collections import Counter
    print("[F3%s] phân bố quyết định: %s" % ("a" if args.no_dualcheck else "",
                                             dict(Counter(out_df["decision"]))))
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        out_df.to_csv(args.out, index=False)
        print(f"[F3] -> {args.out}")


if __name__ == "__main__":
    main()
