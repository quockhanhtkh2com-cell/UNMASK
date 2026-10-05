"""F3 — Bước 2: dual-check (chống lỗi L1) — [Tuấn].

Điểm pack cao chỉ nói "có vẻ bị pack", CHƯA nói "lõi không đổi". Bỏ các feature
liên quan đến packing, so phần LÕI còn lại (.NET metadata, header không bị viết lại,
kích thước gốc...) với tập THAM CHIẾU mẫu đã biết (AgentTesla).

- Gần mẫu tham chiếu  -> FILTERED (chỉ đổi vỏ)
- Không gần / pattern khác hẳn -> FLAGGED (vẫn vào chuông + cờ)

⚠️ Chỗ cần đo kỹ nhất: njRAT cũng là .NET -> dual-check có thể tưởng "giống
AgentTesla" -> FILTERED nhầm -> chuông mù trước malware mới (L1). F3a (bỏ dual-check)
dùng để đo riêng công của bước này.

API:
    dc = DualCheck(reference_core_matrix, threshold)   # fit trên CORE_FEATURE_COLS của G0
    verdict = dc.check(core_feature_dict) -> "similar" | "novel"
"""
from __future__ import annotations
import numpy as np


class DualCheck:
    def __init__(self, ref_matrix: np.ndarray, threshold: float | None = None):
        """ref_matrix: ndarray (n_ref × n_core_feature) của mẫu THAM CHIẾU đã biết."""
        self.ref = np.asarray(ref_matrix, dtype=float)
        self.mean = self.ref.mean(axis=0)
        self.std = self.ref.std(axis=0) + 1e-9
        self.threshold = threshold

    def _dist(self, x: np.ndarray) -> float:
        """Khoảng cách Euclid chuẩn hoá tới mẫu tham chiếu GẦN NHẤT."""
        xz = (np.asarray(x, dtype=float) - self.mean) / self.std
        refz = (self.ref - self.mean) / self.std
        d = np.sqrt(((refz - xz) ** 2).sum(axis=1))
        return float(d.min())

    def lock_threshold(self, core_val: np.ndarray, p: float = 95) -> float:
        """Khoá ngưỡng: P95 khoảng cách của validation G0 tới tham chiếu."""
        dists = [self._dist(row) for row in np.asarray(core_val, dtype=float)]
        self.threshold = float(np.percentile(dists, p))
        return self.threshold

    def check(self, core_feat: np.ndarray) -> str:
        if self.threshold is None:
            raise RuntimeError("Chưa khoá ngưỡng dual-check.")
        return "similar" if self._dist(core_feat) <= self.threshold else "novel"
