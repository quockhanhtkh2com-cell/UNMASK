import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import check_data as C


@pytest.fixture
def mock_data():
    dataset = pd.read_csv(ROOT / "mock" / "mock_dataset.csv")
    manifest = pd.read_csv(ROOT / "mock" / "mock_manifest.csv")
    return dataset, manifest


def run_check(tmp_path, dataset, manifest):
    dataset_path = tmp_path / "dataset.csv"
    manifest_path = tmp_path / "manifest.csv"
    dataset.to_csv(dataset_path, index=False)
    manifest.to_csv(manifest_path, index=False)
    return C.run(str(dataset_path), str(manifest_path))


def test_valid_mock_passes(tmp_path, mock_data):
    dataset, manifest = mock_data
    assert run_check(tmp_path, dataset, manifest)


def test_missing_column_fails(tmp_path, mock_data):
    dataset, manifest = mock_data
    dataset = dataset.drop(columns=["group"])
    assert not run_check(tmp_path, dataset, manifest)


def test_invalid_numeric_fails(tmp_path, mock_data):
    dataset, manifest = mock_data
    dataset["entropy_file"] = dataset["entropy_file"].astype(object)
    dataset.loc[0, "entropy_file"] = "not_a_number"
    assert not run_check(tmp_path, dataset, manifest)


def test_train_val_leak_fails(tmp_path, mock_data):
    dataset, manifest = mock_data
    counts = dataset["origin_sha256"].value_counts()
    origin = counts[counts >= 2].index[0]
    rows = dataset.index[dataset["origin_sha256"] == origin]

    dataset.loc[rows, "split"] = "train"
    dataset.loc[rows[0], "split"] = "val"

    assert not run_check(tmp_path, dataset, manifest)


def test_manifest_identity_mismatch_fails(tmp_path, mock_data):
    dataset, manifest = mock_data
    sha = dataset.loc[0, "sha256"]
    manifest.loc[manifest["sha256"] == sha, "family"] = "wrong_family"

    assert not run_check(tmp_path, dataset, manifest)