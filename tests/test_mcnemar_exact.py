"""Kiểm thử McNemar chính xác cho số cặp bất đồng nhỏ."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from eval_metrics import mcnemar_exact


def test_four_discordant_pairs():
    result = mcnemar_exact(
        [True] * 4,
        [False] * 4,
    )
    assert result["b"] == 4
    assert result["c"] == 0
    assert result["p_value"] == pytest.approx(0.125)
    assert math.isnan(result["stat"])


def test_swapping_methods_preserves_two_sided_p_value():
    a = [True, True, True, False, True]
    b = [False, False, False, True, True]

    forward = mcnemar_exact(a, b)
    reverse = mcnemar_exact(b, a)

    assert forward["b"] == reverse["c"]
    assert forward["c"] == reverse["b"]
    assert forward["p_value"] == reverse["p_value"]


def test_no_discordant_pairs():
    result = mcnemar_exact(
        [True, False],
        [True, False],
    )
    assert result["b"] == result["c"] == 0
    assert result["p_value"] == 1.0


def test_unequal_lengths_rejected():
    with pytest.raises(ValueError):
        mcnemar_exact([True], [])