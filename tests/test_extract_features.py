import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import extract_features as E  # noqa: E402


def test_random_data_is_all_high_entropy():
    assert E.window_entropy_ratio(os.urandom(8192)) == 1.0


def test_zero_data_is_low_entropy():
    assert E.window_entropy_ratio(bytes(8192)) == 0.0


def test_half_random_half_zero():
    assert E.window_entropy_ratio(os.urandom(4096) + bytes(4096)) == 0.5


def test_shorter_than_one_window_returns_zero():
    assert E.window_entropy_ratio(os.urandom(500)) == 0.0


def test_loader_only_true():
    assert E.only_loader_imports(["GetProcAddress", "LoadLibraryA", "VirtualProtect"]) == 1


def test_loader_only_case_insensitive():
    assert E.only_loader_imports(["getprocaddress", "EXITPROCESS"]) == 1


def test_loader_plus_normal_api_is_false():
    assert E.only_loader_imports(["GetProcAddress", "CreateFileA"]) == 0


def test_few_normal_apis_is_false():
    # truong hop heuristic cu (num_api <= 10) danh dau sai
    assert E.only_loader_imports(["CreateFileA", "ReadFile", "CloseHandle"]) == 0


def test_no_named_imports_is_false():
    assert E.only_loader_imports([]) == 0


def test_origin_self_for_unpacked_groups():
    assert E.resolve_origin("G0", "abc", "a.exe", {}) == "abc"
    assert E.resolve_origin("G2", "abc", "a.exe", {}) == "abc"


def test_origin_from_map_for_packed_groups():
    assert E.resolve_origin("G1", "x", "a_upx.exe", {"a_upx.exe": "orig"}) == "orig"
    assert E.resolve_origin("G3", "x", "a_upx.exe", {"a_upx.exe": "orig"}) == "orig"


def test_origin_missing_for_packed_group_is_none():
    assert E.resolve_origin("G1", "x", "a_upx.exe", {}) is None


def test_drift_truth_by_group():
    import pandas as pd
    df = E.add_drift_truth(pd.DataFrame({"group": ["G0", "G1", "G2", "G3"]}))
    assert list(df["is_drift_truth"]) == [0, 0, 1, 1]


def test_drift_truth_bad_group_raises():
    import pandas as pd
    import pytest
    with pytest.raises(ValueError):
        E.add_drift_truth(pd.DataFrame({"group": ["G9"]}))


def test_load_origin_map(tmp_path):
    f = tmp_path / "m.csv"
    f.write_text("filename,origin_sha256\na.exe,aaa\nb.exe,\n", encoding="utf-8")
    assert E.load_origin_map(str(f)) == {"a.exe": "aaa"}


def test_ep_section_wx_true_for_rwx():
    assert E.ep_section_wx(0xE0000020) == 1  # kieu section UPX1: R+W+X


def test_ep_section_wx_false_for_normal_text():
    assert E.ep_section_wx(0x60000020) == 0  # .text: R+X


def test_ep_section_wx_false_for_data():
    assert E.ep_section_wx(0xC0000040) == 0  # .data: R+W


def test_ep_section_wx_false_for_write_only():
    assert E.ep_section_wx(0x80000000) == 0
