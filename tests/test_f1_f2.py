import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import f1_die as F1
import f2_rule as F2


@pytest.mark.parametrize(
    "die_result_real, variant, expected",
    [
        # F1-DiE (packed_only): chỉ loại packed
        ("packed", "packed_only", "FILTERED"),
        ("protected", "packed_only", "PASS"),
        ("PACKED", "packed_only", "FILTERED"),
        ("clean", "packed_only", "PASS"),
        ("unknown", "packed_only", "PASS"),
        # F1-DiE+protected (packed_protected): loại cả packed + protected
        ("packed", "packed_protected", "FILTERED"),
        ("protected", "packed_protected", "FILTERED"),
        ("PACKED", "packed_protected", "FILTERED"),
        ("clean", "packed_protected", "PASS"),
        ("unknown", "packed_protected", "PASS"),
    ],
)
def test_f1_decide(die_result_real, variant, expected):
    assert F1.decide({"die_result_real": die_result_real}, variant=variant) == expected


def test_f1_run_packed_only():
    df = pd.DataFrame({
        "die_result_real": ["clean", "packed", "unknown", "protected"],
    })
    assert F1.run(df, variant="packed_only") == ["PASS", "FILTERED", "PASS", "PASS"]


def test_f1_run_packed_protected():
    df = pd.DataFrame({
        "die_result_real": ["clean", "packed", "unknown", "protected"],
    })
    assert F1.run(df, variant="packed_protected") == ["PASS", "FILTERED", "PASS", "FILTERED"]


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