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
