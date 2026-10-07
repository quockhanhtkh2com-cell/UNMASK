import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def test_pyproject_ships_src_modules_that_unmask_imports():
    """unmask import schema_cols/extract_features từ src/ -> pip phải cài cả hai (lỗi cũ:
    ModuleNotFoundError: schema_cols sau pip install)."""
    tomllib = pytest.importorskip("tomllib")
    cfg = tomllib.load(open(os.path.join(ROOT, "pyproject.toml"), "rb"))
    st = cfg["tool"]["setuptools"]
    assert {"schema_cols", "extract_features"} <= set(st["py-modules"])
    assert st["package-dir"][""] == "src" and st["package-dir"]["unmask"] == "unmask"
    for m in st["py-modules"]:
        assert os.path.exists(os.path.join(ROOT, "src", m + ".py")), m


def test_load_locked_prefers_env_var(tmp_path, monkeypatch):
    from unmask import filter as F
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"locked": True, "packed_score": {"threshold": 0.3}}))
    monkeypatch.setenv("UNMASK_CONFIG", str(p))
    assert F._load_locked()["packed_score"]["threshold"] == 0.3


def test_load_locked_ignores_unlocked_config(tmp_path, monkeypatch):
    from unmask import filter as F
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"locked": False}))
    monkeypatch.setenv("UNMASK_CONFIG", str(p))
    assert F._load_locked() is None
