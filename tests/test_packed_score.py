import json
import os
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "unmask"))
import packed_score as PS  # noqa: E402
import train as TR  # noqa: E402

MOCK = os.path.join(HERE, "..", "mock", "mock_dataset.csv")


def test_without_scaler_uses_raw_values():
    s = PS.PackedScorer(weights={"entropy_max_section": 1.0, "bias": 0.0})
    assert s._value({"entropy_max_section": 7.0}, "entropy_max_section") == 7.0


def test_scaler_standardizes_before_weights():
    sc = {"mean": {"entropy_max_section": 6.0}, "scale": {"entropy_max_section": 2.0}}
    s = PS.PackedScorer(weights={"entropy_max_section": 1.0, "bias": 0.0}, scaler=sc)
    assert s._value({"entropy_max_section": 8.0}, "entropy_max_section") == 1.0
    # feature = mean -> dong gop 0 -> diem = sigmoid(bias) = 0.5
    assert abs(s.score({"entropy_max_section": 6.0}) - 0.5) < 1e-9


def test_scaler_zero_scale_does_not_divide_by_zero():
    sc = {"mean": {"overlay_size": 0.0}, "scale": {"overlay_size": 0.0}}
    s = PS.PackedScorer(weights={"overlay_size": 1.0, "bias": 0.0}, scaler=sc)
    assert s._value({"overlay_size": 5.0}, "overlay_size") == 5.0


def test_load_reads_scaler_from_locked_config():
    locked = {"packed_score": {"weights": {"bias": 0.0}, "threshold": 0.4,
                               "scaler": {"mean": {"x": 1.0}, "scale": {"x": 2.0}}}}
    s = PS.PackedScorer.load(locked)
    assert s.scaler == locked["packed_score"]["scaler"] and s.threshold == 0.4


def test_train_on_mock_saves_scaler_and_separates_groups(tmp_path):
    import pandas as pd
    out = tmp_path / "lock.json"
    TR.train(MOCK, str(out))
    cfg = json.load(open(out))
    ps = cfg["packed_score"]
    assert set(ps["scaler"]["mean"]) == set(PS.NUMERIC)
    assert max(abs(v) for k, v in ps["weights"].items() if k != "bias") > 0.1
    scorer = PS.PackedScorer.load(cfg)
    df = pd.read_csv(MOCK)
    g0 = df[df.group == "G0"].to_dict("records")
    g1 = df[(df.group == "G1") & (df.variant == "P-seen")].to_dict("records")
    m0 = sum(scorer.score(r) for r in g0) / len(g0)
    m1 = sum(scorer.score(r) for r in g1) / len(g1)
    assert m1 > m0 + 0.3, (m0, m1)
