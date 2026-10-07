import os
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
import core_survival as CS  # noqa: E402

SCRIPT = os.path.join(ROOT, "src", "core_survival.py")


def _df():
    base = {"family": "agenttesla", "file_size": 1000, "size_of_headers": 512,
            "compile_timestamp": 1500000000, "is_dotnet": 1, "num_api": 1, "num_dll": 1}
    rows = [
        dict(base, sha256="a", origin_sha256="a", group="G0", packer="none"),
        dict(base, sha256="b", origin_sha256="b", group="G0", packer="none"),
        # G1 cua a: file_size doi (pack nen file), cac feature loi khac giu nguyen
        dict(base, sha256="a1", origin_sha256="a", group="G1", packer="upx", file_size=500),
        dict(base, sha256="b1", origin_sha256="b", group="G1", packer="upx"),
        # G1 khong co mau goc -> bi bo qua
        dict(base, sha256="z1", origin_sha256="zz", group="G1", packer="upx"),
    ]
    return pd.DataFrame(rows)


def test_survival_table_counts_pairs_and_deviation():
    t = CS.survival_table(_df(), ["file_size", "size_of_headers"])
    fs = t[t.feature == "file_size"].iloc[0]
    sh = t[t.feature == "size_of_headers"].iloc[0]
    assert fs.n_pairs == 2 and abs(fs.identical_frac - 0.5) < 1e-9
    assert sh.identical_frac == 1.0 and sh.median_rel_dev == 0.0


def test_survival_table_empty_without_pairs():
    df = _df()
    df = df[df.group == "G0"]
    assert CS.survival_table(df).empty


def test_dotnet_lines_report_per_group():
    out = "\n".join(CS.dotnet_lines(_df()))
    assert "G0: n=2" in out and "is_dotnet=1: 2/2" in out and "num_api trung vi=1" in out


def test_cli_exit_codes(tmp_path):
    p = tmp_path / "d.csv"
    _df().to_csv(p, index=False)
    ok = subprocess.run([sys.executable, SCRIPT, str(p)], capture_output=True, text=True)
    assert ok.returncode == 0 and "packer=upx" in ok.stdout
    _df()[lambda d: d.group == "G0"].to_csv(p, index=False)
    bad = subprocess.run([sys.executable, SCRIPT, str(p)], capture_output=True, text=True)
    assert bad.returncode == 1
    usage = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
    assert usage.returncode == 2
