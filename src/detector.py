"""D1 — CHUÔNG BÁO DRIFT dùng CHUNG cho mọi cổng — [Đức].

Fit trên tập tham chiếu "bình thường" (G0 + nền), tính khoảng cách Mahalanobis
hoặc điểm Isolation Forest. Mẫu vượt phân vị 95 của validation -> báo drift.
Ngưỡng chọn trên validation rồi KHOÁ (ghi vào config/thresholds.locked.json).

API (hợp đồng với experiments/):
    d = DriftDetector(method="mahalanobis")
    d.fit(X_ref)                      # X_ref: ndarray feature của mẫu "bình thường"
    d.lock_threshold(X_val, p=95)     # khoá ngưỡng P95 trên validation
    alarms = d.predict(X_new)         # -> list[bool] (True = báo drift)
"""
from __future__ import annotations
import numpy as np


class DriftDetector:
    def __init__(self, method: str = "mahalanobis", seed: int = 0):
        assert method in ("mahalanobis", "isolation_forest")
        self.method = method
        self.seed = seed
        self._mean = None
        self._inv_cov = None
        self._model = None
        self.threshold = None

    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=float)
        if self.method == "mahalanobis":
            self._mean = X.mean(axis=0)
            cov = np.cov(X, rowvar=False)
            cov += np.eye(cov.shape[0]) * 1e-6  # ổn định số học
            self._inv_cov = np.linalg.pinv(cov)
        else:
            from sklearn.ensemble import IsolationForest
            self._model = IsolationForest(random_state=self.seed, n_estimators=200)
            self._model.fit(X)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        """Điểm bất thường, CÀNG CAO càng lạ."""
        X = np.asarray(X, dtype=float)
        if self.method == "mahalanobis":
            d = X - self._mean
            return np.sqrt(np.einsum("ij,jk,ik->i", d, self._inv_cov, d))
        return -self._model.score_samples(X)  # đảo dấu: cao = lạ

    def lock_threshold(self, X_val: np.ndarray, p: float = 95) -> float:
        self.threshold = float(np.percentile(self.score(X_val), p))
        return self.threshold

    def predict(self, X: np.ndarray) -> list[bool]:
        if self.threshold is None:
            raise RuntimeError("Chưa khoá ngưỡng — gọi lock_threshold() trên validation trước.")
        return [bool(s > self.threshold) for s in self.score(X)]


# TODO(Đức): D2 — CADE nếu chạy được code công khai. Nếu không, chỉ dùng D1 và ghi rõ
# trong báo cáo (rủi ro đã lường trước). Giao diện nên giống DriftDetector để thay nóng.
