"""F3 — Bước 1: điểm "khả năng bị pack" (packed_score) — [Tuấn].

Thay luật cứng (entropy>7 AND section lạ) bằng điểm từ NHIỀU dấu hiệu, trọng số
học bằng logistic regression TRÊN G0 + G1-UPX (chỉ P-seen). KHÔNG được thấy
P-unseen/P-low/P-wild khi học.

Dấu hiệu -> tăng điểm: entropy cao · raw/virtual bất thường · EP section ghi được ·
import teo · tên section lạ/packer · overlay lớn.

API:
    scorer = PackedScorer.load(locked_config)   # hoặc train rồi lock
    s = scorer.score(feature_dict) -> float trong [0,1]
    evidence = scorer.evidence(feature_dict)    # dấu hiệu đóng góp nhiều nhất
"""
from __future__ import annotations
import math

# Feature số đưa vào mô hình (khớp schema; section_name_class mã hoá riêng)
NUMERIC = [
    "entropy_max_section", "entropy_file", "high_entropy_byte_ratio",
    "raw_virtual_ratio", "ep_section_writable", "import_table_shrink",
    "only_dynamic_loader_imports", "overlay_size",
]
SECTION_CLASS_WEIGHT = {"standard": 0.0, "known_packer": 1.0, "weird": 0.7}

# Trọng số thủ công mặc định (fallback khi chưa train). train.py sẽ thay bằng số học được.
DEFAULT_WEIGHTS = {
    "entropy_max_section": 1.1, "entropy_file": 0.4, "high_entropy_byte_ratio": 1.0,
    "raw_virtual_ratio": 0.5, "ep_section_writable": 1.2, "import_table_shrink": 1.5,
    "only_dynamic_loader_imports": 0.8, "overlay_size": 0.0002,
    "section_class": 1.3, "bias": -8.0,
}


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-max(-30, min(30, x))))


class PackedScorer:
    def __init__(self, weights: dict | None = None, threshold: float = 0.5,
                 scaler: dict | None = None):
        """scaler: {"mean": {feature: m}, "scale": {feature: s}} - chuẩn hoá feature số
        TRƯỚC khi nhân trọng số (train.py lưu cùng trọng số). None = giá trị thô (bộ trọng
        số thủ công mặc định)."""
        self.w = dict(DEFAULT_WEIGHTS if weights is None else weights)
        self.threshold = threshold
        self.trained = weights is not None
        self.scaler = scaler

    def _value(self, feat: dict, k: str) -> float:
        v = float(feat.get(k, 0) or 0)
        if self.scaler:
            s = self.scaler["scale"].get(k) or 1.0
            v = (v - self.scaler["mean"].get(k, 0.0)) / s
        return v

    def _linear(self, feat: dict) -> dict:
        """Trả đóng góp từng dấu hiệu (để vừa tính điểm vừa làm evidence)."""
        contrib = {}
        for k in NUMERIC:
            contrib[k] = self.w.get(k, 0.0) * self._value(feat, k)
        sc = feat.get("section_name_class", "standard")
        contrib["section_class"] = self.w.get("section_class", 0.0) * SECTION_CLASS_WEIGHT.get(sc, 0.5)
        return contrib

    def score(self, feat: dict) -> float:
        z = sum(self._linear(feat).values()) + self.w.get("bias", 0.0)
        return _sigmoid(z)

    def evidence(self, feat: dict, top: int = 3) -> list[dict]:
        contrib = self._linear(feat)
        ranked = sorted(contrib.items(), key=lambda kv: abs(kv[1]), reverse=True)
        return [{"feature": k, "contribution": round(v, 3)} for k, v in ranked[:top] if v != 0]

    def is_packed(self, feat: dict) -> bool:
        return self.score(feat) >= self.threshold

    @classmethod
    def load(cls, locked: dict) -> "PackedScorer":
        ps = locked.get("packed_score", {})
        return cls(weights=ps.get("weights"), threshold=ps.get("threshold") or 0.5,
                   scaler=ps.get("scaler"))
