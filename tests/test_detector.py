"""Unit test cho DriftDetector (D1) — [Đức]. pytest -q"""
import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from detector import DriftDetector  # noqa: E402


def test_invalid_method():
    with pytest.raises(AssertionError):
        DriftDetector(method="invalid_method")


def test_predict_before_lock_threshold_raises_error():
    np.random.seed(42)
    X = np.random.randn(20, 5)
    det = DriftDetector(method="mahalanobis")
    det.fit(X)
    with pytest.raises(RuntimeError, match="Chưa khoá ngưỡng"):
        det.predict(X)


def test_mahalanobis_detector_fit_lock_predict():
    np.random.seed(42)
    # 100 mẫu lành tính
    X_train = np.random.randn(100, 4)
    X_val = np.random.randn(50, 4)
    
    det = DriftDetector(method="mahalanobis", seed=42)
    det.fit(X_train)
    
    # Khóa ngưỡng P95 trên validation
    thresh = det.lock_threshold(X_val, p=95)
    assert thresh > 0
    assert det.threshold == thresh
    
    # Dự đoán trên tập bình thường
    preds_normal = det.predict(X_val)
    assert len(preds_normal) == 50
    # ~5% báo True trên val
    assert sum(preds_normal) <= 5
    
    # Dự đoán trên tập drift mạnh (mean shift lớn)
    X_drift = np.random.randn(20, 4) + 10.0
    preds_drift = det.predict(X_drift)
    assert sum(preds_drift) == 20  # 100% báo drift


def test_isolation_forest_detector_fit_lock_predict():
    np.random.seed(42)
    X_train = np.random.randn(100, 4)
    X_val = np.random.randn(50, 4)
    
    det = DriftDetector(method="isolation_forest", seed=42)
    det.fit(X_train)
    
    thresh = det.lock_threshold(X_val, p=95)
    assert det.threshold == thresh
    
    preds_normal = det.predict(X_val)
    assert len(preds_normal) == 50
    assert sum(preds_normal) <= 5
    
    X_drift = np.random.randn(20, 4) + 10.0
    preds_drift = det.predict(X_drift)
    assert sum(preds_drift) >= 18
