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


class TranscendPValueDetector:
    """D2 — bộ đánh giá drift kiểu Transcend (conformal prediction) — [M4 sensitivity check].

    KHÔNG phải một detector độc lập: dùng lại NGUYÊN công thức Mahalanobis của
    DriftDetector làm Non-Conformity Measure (NCM). Khác D1 ở BƯỚC ĐỌC kết quả:
    D1 so trực tiếp NCM với 1 ngưỡng cứng (percentile); D2 đổi NCM thành **p-value**
    (đếm rank trong tập reference K), rồi so p-value với mức ý nghĩa alpha.

    QUAN TRỌNG để so sánh công bằng với D1: tập reference K PHẢI là G0-VAL (cùng tập
    D1 dùng để lock_threshold), KHÔNG phải G0-train — nếu không 2 detector sẽ so với
    2 "lớp học" khác nhau, làm sai lệch chênh lệch quan sát được. Vì vậy K được gán ở
    lock_threshold(X_val, ...), KHÔNG phải ở fit(X_train).

    Công thức p-value lấy đúng từ Conformal Evaluator của Transcend
    (Jordaney et al., "Transcend: Detecting Concept Drift in Malware Classification
    Models", USENIX Security 2017, Eq. 1–3), KHÔNG làm trơn (+1) như bản textbook CP gốc:

        p(x) = |{ z thuộc K : NCM(z) ≥ NCM(x) }| / |K|

    p(x) THẤP (x hiếm/lạ so với K) -> báo drift.
    p(x) CAO  (x phổ biến, giống K) -> bình thường.

    Khác biệt so với paper gốc (phải ghi rõ khi trích dẫn trong report): Transcend
    dùng NCM từ 1 classifier có giám sát (khoảng cách tới hyperplane / -prob); ở đây
    NCM = khoảng cách Mahalanobis không giám sát, để tương thích với D1 hiện có.

    API (giữ tương tự DriftDetector để "cắm nóng" — đúng TODO ban đầu của Đức):
        d2 = TranscendPValueDetector(standardize=True)
        d2.fit(X_ref)                        # X_ref: mẫu "bình thường" -> tập reference K
        d2.lock_threshold(X_val, alpha=0.2)  # khoá mức ý nghĩa alpha
        alarms = d2.predict(X_new)            # -> list[bool] (True = báo drift)
    """

    def __init__(self, seed: int = 0, standardize: bool = True):
        self.seed = seed
        self.standardize = standardize
        self._base = DriftDetector(method="mahalanobis", seed=seed, standardize=standardize)
        self._ncm_ref = None  # NCM của tập reference K (G0-VAL, gán ở lock_threshold) — dùng để đếm rank
        self.alpha = None
        self.threshold = None  # == alpha, giữ tên "threshold" để script đọc chung với D1

    def fit(self, X: np.ndarray):
        """Học mean/cov (giống D1) từ G0-train. KHÔNG gán tập reference K ở đây —
        K phải lấy từ G0-val, xem lock_threshold(), để so sánh công bằng với D1."""
        X = np.asarray(X, dtype=float)
        self._base.fit(X)
        return self

    def ncm(self, X: np.ndarray) -> np.ndarray:
        """NCM = điểm Mahalanobis, dùng lại nguyên công thức của D1 (score())."""
        return self._base.score(np.asarray(X, dtype=float))

    def pvalue(self, X: np.ndarray) -> np.ndarray:
        """p(x) = |{z in K: NCM(z) >= NCM(x)}| / |K|  (Transcend Eq. 3, không +1)."""
        if self._ncm_ref is None:
            raise RuntimeError("Chưa fit() — gọi fit(X_ref) trước.")
        scores_x = self.ncm(X)
        K = self._ncm_ref
        n = len(K)
        return np.array([np.sum(K >= s) / n for s in scores_x])

    def lock_threshold(self, X_val: np.ndarray, alpha: float = 0.2) -> float:
        """Gán tập reference K = NCM(X_val) — CÙNG tập G0-val mà D1 dùng để
        lock_threshold(p=...) — để 2 detector so với cùng 1 "lớp học", chỉ khác
        cách đọc kết quả (percentile vs p-value). Rồi khoá mức ý nghĩa alpha
        (Transcend chọn alpha trực tiếp/qua grid-search, không nội suy percentile)."""
        self._ncm_ref = self.ncm(X_val)
        self.alpha = float(alpha)
        self.threshold = self.alpha
        return self.alpha

    def predict(self, X: np.ndarray) -> list[bool]:
        if self.alpha is None:
            raise RuntimeError("Chưa khoá alpha — gọi lock_threshold() trước.")
        p = self.pvalue(X)
        return [bool(pv < self.alpha) for pv in p]


# TODO(Đức): CADE nếu chạy được code công khai (train lại autoencoder contrastive —
# rủi ro cao, chưa làm). D2 hiện tại = TranscendPValueDetector (xem class trên).
