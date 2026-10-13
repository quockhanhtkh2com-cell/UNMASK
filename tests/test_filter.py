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
    out = filter_file("mau.exe", cfg, use_dualcheck=False)
    # num_api = trung vi -> shrink 0 -> diem = sigmoid(-5) rat thap -> PASS.
    # Neu van dung num_api tho (60) thi diem ~ 1.0.
    assert out["decision"] == "PASS" and out["packed_score"] < 0.1


def test_filter_row_without_dualcheck_config_raises_instead_of_silent_f3a():
    from unmask.filter import filter_row
    import pytest
    with pytest.raises(ValueError):
        filter_row({"num_api": 1}, {"locked": True, "packed_score": {"weights": {"bias": 0.0}}})


def test_filter_row_f3a_allowed_when_explicit():
    from unmask.filter import filter_row
    out = filter_row({"section_name_class": "standard"},
                     {"locked": True, "packed_score": {"weights": {"bias": 5.0}, "threshold": 0.5}},
                     use_dualcheck=False)
    assert out["decision"] == "FILTERED"   # diem cao, F3a -> loai


def test_filter_row_full_f3_pass_filtered_flagged(tmp_path):
    """Config khoa that tu mock: diem cao + loi giong tham chieu -> FILTERED; loi la -> FLAGGED."""
    import json
    import train as TR
    from unmask.filter import filter_row
    out = tmp_path / "lock.json"
    TR.train(os.path.join(HERE, "..", "mock", "mock_dataset.csv"), str(out))
    cfg = json.load(open(out))
    cols = cfg["dual_check"]["core_cols"]
    ref0 = dict(zip(cols, cfg["dual_check"]["reference"][0]))
    packed = {"section_name_class": "known_packer", "entropy_max_section": 7.9,
              "entropy_file": 7.9, "high_entropy_byte_ratio": 1.0, "raw_virtual_ratio": 0.1,
              "ep_section_writable": 1, "import_table_shrink": 0.9,
              "only_dynamic_loader_imports": 1, "overlay_size": 50000}
    same = {**packed, **ref0}
    novel = {**packed, **{c: v * 100 + 12345 for c, v in ref0.items()}}
    assert filter_row(same, cfg)["decision"] == "FILTERED"
    assert filter_row(novel, cfg)["decision"] == "FLAGGED"
    benign = {"section_name_class": "standard", "entropy_max_section": 5.0, "entropy_file": 5.0}
    assert filter_row(benign, cfg)["decision"] == "PASS"


def test_baseline_api_by_dotnet_and_backward_compat():
    from unmask.packed_score import baseline_api
    cfg = {"median_api": 50.0, "median_api_by_dotnet": {"0": 164.0, "1": 1.0}}
    assert baseline_api(cfg, 0) == 164.0
    assert baseline_api(cfg, 1) == 1.0
    assert baseline_api({"median_api": 50.0}, 1) == 50.0   # config cu
    assert baseline_api(None, 0) is None


def test_filter_file_uses_native_baseline(monkeypatch):
    fake = types.ModuleType("extract_features")
    fake.extract_one = lambda p: {"num_api": 164, "is_dotnet": 0, "section_name_class": "standard"}
    monkeypatch.setitem(sys.modules, "extract_features", fake)
    from unmask.filter import filter_file
    cfg = {"locked": True,
           "packed_score": {"weights": {"import_table_shrink": 10.0, "bias": -5.0}, "threshold": 0.5},
           "import_shrink": {"median_api": 1.0, "median_api_by_dotnet": {"0": 164.0, "1": 1.0}}}
    out = filter_file("mau.exe", cfg, use_dualcheck=False)
    assert out["decision"] == "PASS"   # native co 164 API = binh thuong, khong phai bi pack


def test_load_filter_requires_locked():
    import pytest
    from unmask.filter import load_filter
    with pytest.raises(ValueError):
        load_filter({"locked": False})
