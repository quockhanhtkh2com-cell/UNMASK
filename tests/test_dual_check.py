import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "unmask"))
import dual_check as DC  # noqa: E402
import train as TR  # noqa: E402

MOCK = os.path.join(HERE, "..", "mock", "mock_dataset.csv")
LOCKED_TEMPLATE = os.path.join(HERE, "..", "config", "thresholds.locked.json")


def _ref():
    rng = np.random.default_rng(0)
    return rng.normal(size=(30, 3))


def test_same_set_threshold_is_zero_but_loo_is_positive():
    """Loi cu: khoa nguong tren CHINH tap tham chieu -> khoang cach = 0 -> nguong 0."""
    ref = _ref()
    a = DC.DualCheck(ref)
    assert a.lock_threshold(ref, p=95) == 0.0
    b = DC.DualCheck(ref)
    assert b.lock_threshold_loo(p=95) > 0.0


def test_loo_needs_two_references():
    with pytest.raises(ValueError):
        DC.DualCheck(np.zeros((1, 3))).lock_threshold_loo()


def test_config_roundtrip_keeps_decision():
    ref = _ref()
    a = DC.DualCheck(ref, core_cols=["a", "b", "c"])
    a.lock_threshold_loo()
    b = DC.DualCheck.from_config(json.loads(json.dumps(a.to_config())))
    x = ref[0] + 0.01
    assert a.check(x) == b.check(x) and b.core_cols == ["a", "b", "c"]


def test_from_config_missing_raises():
    with pytest.raises(ValueError):
        DC.DualCheck.from_config(None)
    with pytest.raises(ValueError):
        DC.DualCheck.from_config({"similarity_threshold": None, "reference": None})


def test_fit_from_dataframe_uses_train_ref_and_val_threshold():
    import pandas as pd
    rng = np.random.default_rng(1)
    cols = ["x", "y"]
    rows = []
    for i in range(10):
        rows.append({"group": "G0", "split": "train", "x": rng.normal(), "y": rng.normal()})
    for i in range(5):
        rows.append({"group": "G0", "split": "val", "x": rng.normal(), "y": rng.normal()})
    rows.append({"group": "G0", "split": "test", "x": 99.0, "y": 99.0})
    dc, info = DC.fit_from_dataframe(pd.DataFrame(rows), cols)
    assert info["n_ref"] == 10 and info["n_val"] == 5 and info["threshold_source"] == "G0 val"
    assert dc.threshold > 0 and dc.ref.max() < 50   # khong dung dong split=test


def test_fit_from_dataframe_without_val_uses_loo():
    import pandas as pd
    rng = np.random.default_rng(2)
    rows = [{"group": "G0", "split": "train", "x": rng.normal(), "y": rng.normal()}
            for _ in range(8)]
    dc, info = DC.fit_from_dataframe(pd.DataFrame(rows), ["x", "y"])
    assert "leave-one-out" in info["threshold_source"] and dc.threshold > 0


def test_train_locks_full_config_on_mock(tmp_path):
    out = tmp_path / "lock.json"
    TR.train(MOCK, str(out))
    # Luon chi dinh encoding="utf-8" khi doc JSON: tren Windows, open() khong co
    # encoding se dung codepage he thong (cp1252/charmap) thay vi UTF-8, va vo khi
    # gap tieng Viet co dau (vd "KHOA DE THI" trong config/thresholds.locked.json).
    cfg = json.load(open(out, encoding="utf-8"))
    assert cfg["locked"] is True
    assert cfg["packed_score"]["scaler"] and cfg["import_shrink"]["median_api"]
    assert cfg["dual_check"]["similarity_threshold"] > 0 and cfg["dual_check"]["reference"]


def test_template_has_every_key_that_train_writes(tmp_path):
    out = tmp_path / "lock.json"
    TR.train(MOCK, str(out))
    cfg = json.load(open(out, encoding="utf-8"))
    tpl = json.load(open(LOCKED_TEMPLATE, encoding="utf-8"))
    assert set(tpl["dual_check"]) <= set(cfg["dual_check"])
    assert set(tpl["import_shrink"]) <= set(cfg["import_shrink"])
    assert "scaler" in tpl["packed_score"]
