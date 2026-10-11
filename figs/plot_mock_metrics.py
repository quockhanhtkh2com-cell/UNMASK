"""Biểu đồ metrics F0–F3 trên test mock — [Trúc]."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import eval_metrics as M
import f1_die
import f2_rule


def draw(rows, metric, labels, output, title):
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(labels))
    width = 0.18
    colors = ["#64748b", "#2563eb", "#e5a000", "#22a06b"]

    for index, gate in enumerate(["F0", "F1", "F2", "F3"]):
        subset = rows[
            (rows["metric"] == metric) & (rows["gate"] == gate)
        ].set_index("category").reindex(labels)

        positions = x + (index - 1.5) * width
        values = subset["rate"].to_numpy(float) * 100
        low = subset["ci_low"].to_numpy(float) * 100
        high = subset["ci_high"].to_numpy(float) * 100
        valid = np.isfinite(values)

        ax.bar(
            positions[valid], values[valid], width,
            label=gate, color=colors[index],
            yerr=np.maximum(
                0,
                np.array([
                    values[valid] - low[valid],
                    high[valid] - values[valid],
                ]),
            ),
            capsize=3,
        )

        for pos, value, den in zip(
            positions, values, subset["den"]
        ):
            if np.isfinite(value):
                ax.text(
                    pos, value + 2, f"{value:.0f}%",
                    ha="center", fontsize=8,
                )
            else:
                ax.text(
                    pos, 2, "N/A", ha="center",
                    rotation=90, fontsize=8,
                )

    ax.set_xticks(x, labels)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Rate (%)")
    ax.set_title(title)
    ax.legend(
        title="Gate", ncol=1,
        loc="upper left", bbox_to_anchor=(1.01, 1),
    )
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=0.2)
    fig.text(
        0.5, 0.02,
        "MOCK test only; Wilson 95% CI; F3 uses default scorer. "
        "N/A = no samples.",
        ha="center", fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(output, dpi=200)
    plt.close(fig)
    print(f"Đã lưu: {output}")


def main():
    dataset = pd.read_csv(ROOT / "mock" / "mock_dataset_demo.csv")
    manifest = pd.read_csv(ROOT / "mock" / "mock_manifest.csv")
    demo = pd.read_csv(ROOT / "results" / "mock_demo_decisions.csv")

    if manifest["sha256"].duplicated().any():
        raise ValueError("Manifest có sha256 trùng.")
    if demo["sha256"].duplicated().any():
        raise ValueError("CSV demo có sha256 trùng.")

    df = dataset.loc[dataset["split"] == "test"].copy()
    if df.empty:
        raise ValueError("Không có mẫu test.")

    df = df.merge(
        manifest[["sha256", "die_result"]],
        on="sha256", how="left", validate="one_to_one",
    )
    df = df.merge(
        demo[["sha256", "decision"]].rename(
            columns={"decision": "F3_decision"}
        ),
        on="sha256", how="left", validate="one_to_one",
    )

    if df[["die_result", "F3_decision"]].isna().any().any():
        raise ValueError("Mẫu test thiếu kết quả manifest hoặc demo.")
    if not df["F3_decision"].isin(
        ["PASS", "FILTERED", "FLAGGED"]
    ).all():
        raise ValueError("Quyết định F3 không hợp lệ.")

    decisions = {
        "F0": ["PASS"] * len(df),
        "F1": f1_die.run(df),
        "F2": f2_rule.run(df),
        "F3": df["F3_decision"].tolist(),
    }

    groups = df["group"].tolist()
    variants = df["variant"].tolist()
    rows = []

    def add(gate, metric, category, rate):
        lo, hi = rate.wilson()
        rows.append({
            "gate": gate,
            "metric": metric,
            "category": category,
            "num": rate.num,
            "den": rate.den,
            "rate": rate.value,
            "ci_low": lo,
            "ci_high": hi,
            "data_mode": "mock",
            "split": "test",
        })

    for gate, dec in decisions.items():
        for group in ["G2", "G3"]:
            add(gate, "fnr", group, M.fnr(dec, groups, group))

        for variant in ["P-seen", "P-unseen", "P-low", "P-wild"]:
            add(
                gate, "correct_filter", variant,
                M.correct_filter_rate(
                    dec, groups, variants, variant
                ),
            )

    summary = pd.DataFrame(rows)
    summary.to_csv(
        ROOT / "results" / "mock_gate_metrics.csv", index=False
    )
    print(summary[[
        "gate", "metric", "category", "num", "den", "rate"
    ]].to_string(index=False))

    draw(
        summary, "fnr", ["G2", "G3"],
        ROOT / "figs" / "fig_mock_fnr_by_group.png",
        "MOCK — Missed true drift by gate (test)",
    )
    draw(
        summary, "correct_filter",
        ["P-seen", "P-unseen", "P-low", "P-wild"],
        ROOT / "figs" / "fig_mock_correct_filter_by_variant.png",
        "MOCK — Correct filtering of G1 by variant (test)",
    )


if __name__ == "__main__":
    main()