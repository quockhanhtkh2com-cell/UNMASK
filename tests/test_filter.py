import os
import sys
import types

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "unmask"))
import packed_score as PS  # noqa: E402


def test_import_shrink_matches_extract_formula():
    assert PS.import_shrink(30, 60) == 0.5
    assert PS.import_shrink(60, 60) == 0.0
    assert PS.import_shrink(90, 60) == 0.0   # nhieu hon trung vi -> khong am


def test_import_shrink_without_median_is_zero():
    assert PS.import_shrink(60, None) == 0.0
    assert PS.import_shrink(60, 0) == 0.0
    assert PS.import_shrink(60, float("nan")) == 0.0


def test_filter_file_normalizes_import_shrink(monkeypatch):
    fake = types.ModuleType("extract_features")
    fake.extract_one = lambda p: {"num_api": 60, "section_name_class": "standard"}
    monkeypatch.setitem(sys.modules, "extract_features", fake)
    from unmask.filter import filter_file
    cfg = {"locked": True,
           "packed_score": {"weights": {"import_table_shrink": 10.0, "bias": -5.0}, "threshold": 0.5},
           "import_shrink": {"median_api": 60.0}}
    out = filter_file("mau.exe", cfg)
    # num_api = trung vi -> shrink 0 -> diem = sigmoid(-5) rat thap -> PASS.
    # Neu van dung num_api tho (60) thi diem ~ 1.0.
    assert out["decision"] == "PASS" and out["packed_score"] < 0.1
