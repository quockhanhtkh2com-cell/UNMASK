"""Kiểm tra công thức FTR chuẩn hóa prevalence."""
import math

import pytest

from scripts.compute_ftr_prevalence import standardized_ftr


def test_weighted_alarm_probability():
    # G1: 0.3 × 0.5; non-G1: 0.7 × 0.25.
    assert standardized_ftr(0.5, 0.25, 0.3) == pytest.approx(6 / 13)


def test_no_g1_alarms():
    assert standardized_ftr(0.0, 0.5, 0.3) == 0.0


def test_only_g1_alarms():
    assert standardized_ftr(0.5, 0.0, 0.3) == 1.0


def test_no_alarms_is_undefined():
    assert math.isnan(standardized_ftr(0.0, 0.0, 0.3))


@pytest.mark.parametrize(
    "rates",
    [
        (-0.1, 0.5, 0.3),
        (0.5, 1.1, 0.3),
        (0.5, 0.5, 1.1),
        (float("nan"), 0.5, 0.3),
    ],
)
def test_invalid_rates_rejected(rates):
    with pytest.raises(ValueError):
        standardized_ftr(*rates)