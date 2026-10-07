import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import f1_die as F1
import f2_rule as F2


@pytest.mark.parametrize(
    "die_result, expected",
    [
        ("packed", "FILTERED"),
        ("protected", "FILTERED"),
        ("PACKED", "FILTERED"),
        ("clean", "PASS"),
        ("unknown", "PASS"),
    ],
)
def test_f1_decide(die_result, expected):
    assert F1.decide({"die_result": die_result}) == expected


def test_f1_run_preserves_order():
    df = pd.DataFrame({
        "die_result": ["clean", "packed", "unknown", "protected"],
    })
    assert F1.run(df) == ["PASS", "FILTERED", "PASS", "FILTERED"]


@pytest.mark.parametrize(
    "entropy, section_class, expected",
    [
        (7.1, "weird", "FILTERED"),
        (7.1, "known_packer", "FILTERED"),
        (7.1, "standard", "PASS"),
        (7.0, "weird", "PASS"),
        (6.9, "known_packer", "PASS"),
    ],
)
def test_f2_decide(entropy, section_class, expected):
    row = {
        "entropy_max_section": entropy,
        "section_name_class": section_class,
    }
    assert F2.decide(row) == expected


def test_f2_custom_threshold():
    row = {
        "entropy_max_section": 6.8,
        "section_name_class": "known_packer",
    }
    assert F2.decide(row) == "PASS"
    assert F2.decide(row, thr=6.5) == "FILTERED"


def test_f2_run_preserves_order():
    df = pd.DataFrame({
        "entropy_max_section": [7.5, 7.5, 6.5],
        "section_name_class": ["weird", "standard", "known_packer"],
    })
    assert F2.run(df) == ["FILTERED", "PASS", "PASS"]