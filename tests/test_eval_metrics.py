"""Unit test eval_metrics trên dữ liệu giả — [Trúc]. pytest -q"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import eval_metrics as M  # noqa: E402


def test_ftr_counts_only_g1_false_alarms():
    dec = ["PASS", "PASS", "PASS", "FILTERED"]
    grp = ["G1", "G2", "G1", "G1"]
    alarm = [True, True, True, True]
    # vào chuông: 3 mẫu (mẫu FILTERED bị bỏ). báo drift do G1 = 2/3
    r = M.ftr(dec, grp, alarm)
    assert r.num == 2 and r.den == 3


def test_fnr_separates_g2_g3():
    dec = ["FILTERED", "PASS", "FILTERED", "FLAGGED"]
    grp = ["G2", "G2", "G3", "G3"]
    assert M.fnr(dec, grp, "G2").value == 0.5
    assert M.fnr(dec, grp, "G3").value == 0.5


def test_wilson_bounds():
    lo, hi = M.Rate(5, 10).wilson()
    assert 0 <= lo < 0.5 < hi <= 1


def test_pack_ratio():
    grp = ["G0", "G1", "G2", "G3"]
    var = ["none", "P-seen", "none", "P-seen"]
    assert M.pack_ratio(grp, var) == 0.5  # G1, G3 là pack


def test_mcnemar_symmetric():
    a = [True, False, True, False]
    b = [False, True, True, False]
    out = M.mcnemar(a, b)
    # b == c => bất đối xứng = 0 => không có ý nghĩa thống kê (p cao)
    assert out["b"] == out["c"] == 1
    assert out["p_value"] > 0.3


def test_mcnemar_asymmetric_significant():
    # a đúng nhiều hơn b rõ rệt => p nhỏ
    a = [True] * 20 + [False] * 2
    b = [False] * 20 + [True] * 2
    out = M.mcnemar(a, b)
    assert out["b"] == 20 and out["c"] == 2
    assert out["p_value"] < 0.01


def test_correct_filter_rate_by_variant():
    dec = ["FILTERED", "PASS", "FILTERED"]
    grp = ["G1", "G1", "G1"]
    var = ["P-seen", "P-unseen", "P-seen"]
    assert M.correct_filter_rate(dec, grp, var, "P-seen").value == 1.0
    assert M.correct_filter_rate(dec, grp, var, "P-unseen").value == 0.0
