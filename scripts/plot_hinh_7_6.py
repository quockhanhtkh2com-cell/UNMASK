"""Hình 7.6 — Packed score theo group và is_dotnet — [Trúc].

Chạy từ thư mục gốc repo:
    python scripts/plot_hinh_7_6.py

Chỉ đọc dataset và mô hình khóa; không huấn luyện lại.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import schema_cols as S
from unmask.filter import load_filter
from experiments.plot_style import apply_style, save_figure


GROUPS = ["G0", "G1", "G2", "G3"]
TYPES = {
    0: ("Native", "#4c78a8", -0.19),
    1: (".NET", "#f28e2b", 0.19),
}


def run(dataset_path: Path, config_path: Path, out_dir: Path):
    df = pd.read_csv(
        dataset_path,
        dtype={"sha256": str, "origin_sha256": str},
    )

    missing = set(S.DATASET_COLS) - set(df.columns)
    if missing:
        raise ValueError(f"Dataset thiếu cột: {sorted(missing)}")
    if df.empty:
        raise ValueError("Dataset không có mẫu.")
    if df[S.DATASET_COLS].isna().any().any():
        raise ValueError("Dataset thiếu giá trị bắt buộc.")
    if df["sha256"].duplicated().any():
        raise ValueError("Dataset có sha256 trùng.")
    if not df["group"].isin(GROUPS).all():
        raise ValueError("group không hợp lệ.")
    if not df["split"].isin(S.VALID_SPLIT).all():
        raise ValueError("split không hợp lệ.")
    if (df.groupby("origin_sha256")["split"].nunique() > 1).any():
        raise ValueError("Có origin nằm ở nhiều split.")

    numeric_cols = [
        c for c in S.FEATURE_COLS
        if c != "section_name_class"
    ]
    numeric = df[numeric_cols].apply(
        pd.to_numeric, errors="coerce"
    )
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Feature số không hợp lệ.")
    df[numeric_cols] = numeric

    if not df["is_dotnet"].isin([0, 1]).all():
        raise ValueError("is_dotnet phải là 0 hoặc 1.")
    if not df["section_name_class"].isin(
        S.VALID_SECTION_CLASS
    ).all():
        raise ValueError("section_name_class không hợp lệ.")

    test = df.loc[df["split"].eq("test")].copy()
    if test.empty:
        raise ValueError("Không có mẫu test.")

    # load_filter yêu cầu config đã khóa.
    model = load_filter(str(config_path), use_dualcheck=True)
    threshold = float(model.scorer.threshold)

    # Dùng điểm đầy đủ khi vẽ, không dùng điểm đã làm tròn.
    records = test.to_dict("records")
    scores = np.asarray(
        [model.scorer.score(row) for row in records],
        dtype=float,
    )
    if (
        not np.isfinite(scores).all()
        or (scores < 0).any()
        or (scores > 1).any()
    ):
        raise ValueError("Packed score ngoài khoảng 0–1.")

    test["packed_score"] = scores
    test["decision"] = [
        model.decide(row)["decision"] for row in records
    ]
    test["sample_type"] = test["is_dotnet"].map({
        0: "Native",
        1: ".NET",
    })

    rows = []
    for group in GROUPS:
        for dotnet in TYPES:
            part = test.loc[
                test["group"].eq(group)
                & test["is_dotnet"].eq(dotnet)
            ]
            n = len(part)
            filtered = int(part["decision"].eq("FILTERED").sum())
            rows.append({
                "group": group,
                "is_dotnet": dotnet,
                "sample_type": TYPES[dotnet][0],
                "n": n,
                "n_filtered": filtered,
                "filtered_rate": filtered / n if n else np.nan,
                "packed_score_median": (
                    part["packed_score"].median()
                    if n else np.nan
                ),
                "split": "test",
                "packed_score_threshold": threshold,
            })

    summary = pd.DataFrame(rows)

    apply_style()
    fig, ax = plt.subplots(figsize=(11, 6))
    rng = np.random.default_rng(0)

    for dotnet, (label, color, offset) in TYPES.items():
        first = True
        for index, group in enumerate(GROUPS):
            part = test.loc[
                test["group"].eq(group)
                & test["is_dotnet"].eq(dotnet)
            ]
            center = index + offset
            n = len(part)

            if n:
                # Jitter chỉ dịch ngang để thấy các điểm trùng nhau.
                # Giá trị packed_score trên trục dọc được giữ nguyên.
                x = center + rng.uniform(-0.10, 0.10, n)
                ax.scatter(
                    x,
                    part["packed_score"],
                    s=23,
                    alpha=0.65,
                    color=color,
                    edgecolors="none",
                    label=label if first else None,
                    zorder=3,
                )
                first = False

                median = float(part["packed_score"].median())
                ax.plot(
                    [center - 0.10, center + 0.10],
                    [median, median],
                    color="#222222",
                    linewidth=2.0,
                    zorder=4,
                )

            ax.text(
                center, 1.055, f"n={n}",
                ha="center", fontsize=9, color=color,
            )

    ax.axhline(
        threshold,
        color="#555555",
        linestyle="--",
        linewidth=1.2,
        label=f"Locked threshold = {threshold:g}",
    )

    ax.set_xticks(np.arange(len(GROUPS)), GROUPS)
    ax.set_xlim(-0.6, len(GROUPS) - 0.4)
    ax.set_ylim(-0.05, 1.13)
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.set_xlabel("Ground-truth group")
    ax.set_ylabel("Packed score")
    ax.set_title(
        "Figure 7.6 — Packed score distribution by group and sample type"
    )
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.13),
        ncol=3,
    )

    fig.text(
        0.5, 0.025,
        f"Full test set: n={len(test)} | "
        "Each point is one sample; horizontal jitter only. "
        "Black ticks indicate medians.",
        ha="center", fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.10, 1, 1))

    out_dir.mkdir(parents=True, exist_ok=True)
    image_path = out_dir / "hinh_7_6_packed_score_distribution.png"
    data_path = out_dir / "hinh_7_6_packed_score_data.csv"
    summary_path = out_dir / "hinh_7_6_packed_score_summary.csv"

    save_figure(fig, image_path)
    plt.close(fig)

    test[[
        "sha256", "group", "variant", "packer",
        "is_dotnet", "sample_type", "split",
        "packed_score", "decision",
    ]].to_csv(data_path, index=False)

    summary.to_csv(summary_path, index=False)

    print(summary.to_string(index=False))
    print(f"\nTổng mẫu test: {len(test)}")
    print(f"Ngưỡng packed score: {threshold}")
    for path in [image_path, data_path, summary_path]:
        print(f"Đã lưu: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", type=Path,
        default=ROOT / "dataset_v1.1.csv",
    )
    parser.add_argument(
        "--config", type=Path,
        default=ROOT / "config" / "thresholds.locked.json",
    )
    parser.add_argument(
        "--out-dir", type=Path,
        default=ROOT / "results" / "figs",
    )
    args = parser.parse_args()
    run(args.dataset, args.config, args.out_dir)


if __name__ == "__main__":
    main()