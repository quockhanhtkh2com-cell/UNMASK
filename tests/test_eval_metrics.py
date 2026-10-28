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


def test_fnr_end2end():
    # G2 sample 1: FILTERED (missed by gate) -> missed
    # G2 sample 2: PASS, alarm=True -> detected
    # G2 sample 3: PASS, alarm=False (missed by alarm) -> missed
    # G2 sample 4: FLAGGED, alarm=True -> detected
    dec = ["FILTERED", "PASS", "PASS", "FLAGGED"]
    alarm = [True, True, False, True]
    grp = ["G2", "G2", "G2", "G2"]
    r = M.fnr_end2end(dec, alarm, grp, "G2")
    assert r.num == 2 and r.den == 4 and r.value == 0.5


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
    assert out["stat"] == 0.0
    assert out["p_value"] == 1.0


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

import math
import pytest


def test_rate_zero_denominator():
    rate = M.Rate(0, 0)
    assert math.isnan(rate.value)
    lo, hi = rate.wilson()
    assert math.isnan(lo)
    assert math.isnan(hi)


def test_wilson_known_interval():
    lo, hi = M.Rate(5, 10).wilson()
    assert lo == pytest.approx(0.23659, abs=0.00001)
    assert hi == pytest.approx(0.76341, abs=0.00001)


def test_ftr_no_alarm():
    rate = M.ftr(
        ["PASS", "FLAGGED"],
        ["G1", "G3"],
        [False, False],
    )
    assert rate.num == 0
    assert rate.den == 0
    assert math.isnan(rate.value)


def test_ftr_flagged_enters_detector():
    rate = M.ftr(
        ["FLAGGED", "FLAGGED", "FILTERED"],
        ["G1", "G3", "G1"],
        [True, True, True],
    )
    assert rate.num == 1
    assert rate.den == 2


def test_fnr_missing_target_group():
    rate = M.fnr(["PASS"], ["G0"], "G3")
    assert rate.num == 0
    assert rate.den == 0
    assert math.isnan(rate.value)


def test_correct_filter_rate_ignores_g3():
    rate = M.correct_filter_rate(
        ["FILTERED", "PASS", "FILTERED"],
        ["G1", "G1", "G3"],
        ["P-seen", "P-seen", "P-seen"],
        "P-seen",
    )
    assert rate.num == 1
    assert rate.den == 2


def test_correct_filter_rate_missing_variant():
    rate = M.correct_filter_rate(
        ["FILTERED"],
        ["G1"],
        ["P-seen"],
        "P-wild",
    )
    assert rate.den == 0
    assert math.isnan(rate.value)


def test_flagged_rate():
    rate = M.flagged_rate(
        ["PASS", "FLAGGED", "FILTERED", "FLAGGED"]
    )
    assert rate.num == 2
    assert rate.den == 4
    assert rate.value == 0.5


def test_flagged_rate_empty():
    assert math.isnan(M.flagged_rate([]).value)


def test_pack_ratio_empty():
    assert math.isnan(M.pack_ratio([], []))


def test_mcnemar_identical_predictions():
    result = M.mcnemar(
        [True, False, True],
        [True, False, True],
    )
    assert result["b"] == 0
    assert result["c"] == 0
    assert result["stat"] == 0
    assert result["p_value"] == 1

def test_mcnemar_rejects_different_lengths():
    with pytest.raises(ValueError):
        M.mcnemar([True, False], [True])