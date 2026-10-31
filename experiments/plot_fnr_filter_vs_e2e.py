"""So sánh FNR do bộ lọc và FNR toàn trình trên full test — [Trúc].

Chạy:
    python -m experiments.plot_fnr_filter_vs_e2e
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import schema_cols as S
import f1_die
import f2_rule
from detector import DriftDetector
from unmask.filter import load_filter

from experiments.plot_style import (
    apply_style, save_figure, GATE_COLOR,
)

# Script này chỉ tính quyết định cho 5 cổng F0/F1/F2/F3a/F3 (không có F1+,
# vốn chỉ dùng cho phân tích độ nhạy D1 riêng). GATE_ORDER của plot_style.py
# có cả F1+ nên không dùng trực tiếp ở đây để tránh KeyError.
GATE_ORDER = ["F0", "F1", "F2", "F3a", "F3"]
from experiments.plot_e0b_alarm_by_group import wilson


def plot(dataset_path, manifest_path, config_path, output, die_real_path=None):
    dtype = {"sha256": str, "origin_sha256": str}
    df = pd.read_csv(dataset_path, dtype=dtype)
    manifest = pd.read_csv(manifest_path, dtype=dtype)
    die_real = pd.read_csv(die_real_path, dtype=dtype) if die_real_path else None

    with config_path.open(encoding="utf-8") as handle:
        cfg = json.load(handle)

    if cfg.get("locked") is not True:
        raise ValueError("Config chưa khóa.")

    threshold = (cfg.get("detector_D1") or {}).get(
        "threshold_value"
    )
    if threshold is None or not np.isfinite(float(threshold)):
        raise ValueError("Config thiếu ngưỡng D1 hữu hạn.")

    method = cfg["detector_D1"].get("method")
    if method != "mahalanobis":
        raise ValueError("Script yêu cầu D1 mahalanobis.")

    required = set(S.DATASET_COLS)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset thiếu cột: {sorted(missing)}")
    if df.empty or df[list(required)].isna().any().any():
        raise ValueError("Dataset rỗng hoặc thiếu giá trị.")
    if df["sha256"].duplicated().any():
        raise ValueError("Dataset trùng sha256.")
    if not df["group"].isin(S.VALID_GROUPS).all():
        raise ValueError("group không hợp lệ.")
    if not df["split"].isin(S.VALID_SPLIT).all():
        raise ValueError("split không hợp lệ.")
    if (df.groupby("origin_sha256")["split"].nunique() > 1).any():
        raise ValueError("Có origin nằm ở nhiều split.")

    if not {"sha256", "die_result"} <= set(manifest.columns):
        raise ValueError("Manifest thiếu sha256 hoặc die_result.")
    if manifest["sha256"].isna().any():
        raise ValueError("Manifest thiếu sha256.")
    if manifest["sha256"].duplicated().any():
        raise ValueError("Manifest trùng sha256.")

    features = [
        c for c in S.FEATURE_COLS
        if c != "section_name_class"
    ]
    numeric = df[features].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Feature số không hợp lệ.")
    df[features] = numeric

    train = df.loc[
        df["group"].eq("G0") & df["split"].eq("train"),
        features,
    ]
    test = df.loc[df["split"].eq("test")].copy()
    if len(train) < 2 or test.empty:
        raise ValueError("Thiếu G0 train hoặc mẫu test.")

    # Luôn lấy kết quả DiE từ manifest được chỉ định.
    test = test.drop(columns=["die_result"], errors="ignore")
    test = test.merge(
        manifest[["sha256", "die_result"]],
        on="sha256",
        how="left",
        validate="one_to_one",
    )
    if not test["die_result"].isin(S.VALID_DIE).all():
        raise ValueError("Mẫu test thiếu kết quả DiE hợp lệ.")

    # Cổng F1 (f1_die.decide) đọc cột die_result_real, lấy từ bộ quét
    # pefile thật (results/die_real_v1.1.csv) -- khác cột die_result ở trên
    # (nhãn suy ra từ quá trình sinh mẫu). Thiếu merge này khiến f1_die luôn
    # trả "unknown" -> mọi mẫu bị coi là PASS, làm sai lệch cổng F1.
    if die_real is not None:
        test = test.drop(columns=["die_result_real"], errors="ignore")
        test = test.merge(
            die_real[["sha256", "die_result_real"]],
            on="sha256",
            how="left",
            validate="one_to_one",
        )
        if test["die_result_real"].isna().any():
            raise ValueError("Thiếu die_result_real cho một số mẫu test.")

    detector = DriftDetector(
        method=method, seed=0, standardize=True,
    ).fit(train.to_numpy(dtype=float))
    detector.threshold = float(threshold)
    alarms = np.asarray(
        detector.predict(test[features].to_numpy(dtype=float)),
        dtype=bool,
    )

    f3 = load_filter(str(config_path), use_dualcheck=True)
    f3a = load_filter(str(config_path), use_dualcheck=False)
    records = test.to_dict("records")

    decisions = {
        "F0": ["PASS"] * len(test),
        "F1": f1_die.run(test),
        "F2": f2_rule.run(test),
        "F3a": [f3a.decide(r)["decision"] for r in records],
        "F3": [f3.decide(r)["decision"] for r in records],
    }

    rows = []
    for gate in GATE_ORDER:
        dec = np.asarray(decisions[gate])
        if len(dec) != len(test):
            raise ValueError(f"{gate}: số quyết định không khớp.")
        if not np.isin(dec, ["PASS", "FILTERED", "FLAGGED"]).all():
            raise ValueError(f"{gate}: quyết định không hợp lệ.")

        filtered = dec == "FILTERED"
        for group in ["G2", "G3"]:
            mask = test["group"].eq(group).to_numpy()
            den = int(mask.sum())
            if den == 0:
                raise ValueError(f"Test không có {group}.")

            for metric, missed in [
                ("filter", filtered),
                ("e2e", filtered | ~alarms),
            ]:
                num = int((mask & missed).sum())
                low, high = wilson(num, den)
                rows.append({
                    "gate": gate,
                    "group": group,
                    "metric": metric,
                    "num": num,
                    "den": den,
                    "rate": num / den,
                    "ci_low": low,
                    "ci_high": high,
                    "split": "test",
                    "dataset": dataset_path.name,
                    "d1_threshold": float(threshold),
                })

    summary = pd.DataFrame(rows)
    apply_style()
    fig, axes = plt.subplots(
        1, 2, figsize=(13, 6), sharey=True,
    )

    x = np.arange(len(GATE_ORDER))
    width = 0.34

    for ax, group in zip(axes, ["G2", "G3"]):
        for metric, offset, hatch in [
            ("filter", -width / 2, None),
            ("e2e", width / 2, "///"),
        ]:
            subset = summary.loc[
                summary["group"].eq(group)
                & summary["metric"].eq(metric)
            ].set_index("gate").reindex(GATE_ORDER)

            values = subset["rate"].to_numpy() * 100
            low = subset["ci_low"].to_numpy() * 100
            high = subset["ci_high"].to_numpy() * 100
            positions = x + offset

            ax.bar(
                positions, values, width,
                color=[GATE_COLOR[g] for g in GATE_ORDER],
                edgecolor="#444444",
                linewidth=0.7,
                hatch=hatch,
                yerr=np.maximum(
                    0, np.vstack([values - low, high - values])
                ),
                capsize=3,
                error_kw={"ecolor": "#333333"},
            )

            for pos, value, upper in zip(
                positions, values, high
            ):
                ax.text(
                    pos, upper + 2,
                    f"{value:.1f}",
                    ha="center", va="bottom",
                    fontsize=8, rotation=90,
                )

        den = int(
            summary.loc[summary["group"].eq(group), "den"].iloc[0]
        )
        ax.set_title(f"{group} — {den} test samples")
        ax.set_xticks(x, GATE_ORDER)
        ax.set_xlabel("Gate")
        ax.set_ylim(0, 122)
        ax.grid(axis="y")
        ax.set_axisbelow(True)

    axes[0].set_ylabel("False-negative rate (%)")
    fig.suptitle(
        "UNMASK — Filter-only vs end-to-end FNR",
        fontsize=15, fontweight="bold",
    )
    fig.legend(
        handles=[
            Patch(
                facecolor="white", edgecolor="#444444",
                label="Filter-only",
            ),
            Patch(
                facecolor="white", edgecolor="#444444",
                hatch="///", label="End-to-end",
            ),
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, 0.09),
        ncol=2,
    )
    fig.text(
        0.5, 0.055,
        "Full test set; Wilson 95% CI. "
        "Filter-only: FILTERED. "
        "End-to-end: FILTERED or no D1 alarm.",
        ha="center", fontsize=9,
    )
    fig.text(
        0.5, 0.022,
        f"Source: {dataset_path.name} | "
        f"Locked D1 threshold={float(threshold):.4f} | "
        "Rates computed directly on full test, not averaged subsamples.",
        ha="center", fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.18, 1, 0.93))

    save_figure(fig, output)
    plt.close(fig)

    csv_path = output.with_name(output.stem + "_summary.csv")
    summary.to_csv(csv_path, index=False)

    print(summary[[
        "gate", "group", "metric", "num", "den",
        "rate", "ci_low", "ci_high",
    ]].to_string(index=False))
    print(f"\nĐã lưu: {output}")
    print(f"Đã lưu: {csv_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path,
        default=ROOT / "dataset_v1.1.csv",
    )
    parser.add_argument(
        "--manifest", type=Path,
        default=ROOT / "manifest_v1.1.csv",
    )
    parser.add_argument(
        "--config", type=Path,
        default=ROOT / "config" / "thresholds.locked.json",
    )
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "figs" / "fig_fnr_filter_vs_e2e.png",
    )
    parser.add_argument(
        "--die-real", type=Path,
        default=ROOT / "results" / "die_real_v1.1.csv",
    )
    args = parser.parse_args()
    plot(
        args.dataset, args.manifest, args.config, args.out,
        die_real_path=args.die_real,
    )


if __name__ == "__main__":
    main()