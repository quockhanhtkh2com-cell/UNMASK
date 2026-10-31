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
    def __init__(self, method: str = "mahalanobis", seed: int = 0, standardize: bool = True,
                 cov_estimator: str = "sample"):
        assert method in ("mahalanobis", "isolation_forest")
        assert cov_estimator in ("sample", "ledoit_wolf")
        self.method = method
        self.seed = seed
        self.standardize = standardize
        self.cov_estimator = cov_estimator  # M4 (Gop_y_G1.pdf): shrinkage Ledoit-Wolf
        self.shrinkage_ = None  # he so shrinkage da hoc, chi co khi cov_estimator="ledoit_wolf"
        self._scaler_mean = None
        self._scaler_std = None
        self._mean = None
        self._inv_cov = None
        self._model = None
        self.threshold = None

    def fit(self, X: np.ndarray):
        X = np.asarray(X, dtype=float)
        if self.standardize:
            self._scaler_mean = X.mean(axis=0)
            self._scaler_std = X.std(axis=0)
            self._scaler_std[self._scaler_std == 0] = 1.0
            X = (X - self._scaler_mean) / self._scaler_std

        if self.method == "mahalanobis":
            self._mean = X.mean(axis=0)
            if self.cov_estimator == "ledoit_wolf":
                # M4 (Gop_y_G1.pdf): uoc luong hiep phuong sai co shrinkage, on dinh hon
                # np.cov thuong khi so mau it (vd 62 mau) so voi so chieu (18 chieu).
                from sklearn.covariance import LedoitWolf
                lw = LedoitWolf().fit(X)
                cov = lw.covariance_
                self.shrinkage_ = float(lw.shrinkage_)
            else:
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
        if self.standardize and self._scaler_mean is not None:
            X = (X - self._scaler_mean) / self._scaler_std

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
