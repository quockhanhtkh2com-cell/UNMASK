"""Vẽ quyết định F3 từ CSV xuất bởi demo mock — [Trúc]."""
from pathlib import Path
import argparse

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default="results/mock_demo_decisions.csv"
    )
    parser.add_argument("--out-dir", default="figs")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    required = {"sha256", "group", "decision"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Thiếu cột: {sorted(missing)}")
    if df.empty:
        raise ValueError("CSV không có mẫu.")
    if not df["group"].isin(["G0", "G1", "G2", "G3"]).all():
        raise ValueError("group không hợp lệ.")
    if not df["decision"].isin(
        ["PASS", "FILTERED", "FLAGGED"]
    ).all():
        raise ValueError("decision không hợp lệ.")
    if df["sha256"].isna().any() or df["sha256"].duplicated().any():
        raise ValueError("sha256 bị thiếu hoặc trùng.")

    counts = pd.crosstab(df["group"], df["decision"]).reindex(
        index=["G0", "G1", "G2", "G3"],
        columns=["PASS", "FILTERED", "FLAGGED"],
        fill_value=0,
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    counts.plot.bar(
        stacked=True,
        ax=ax,
        color=["#22a06b", "#d9534f", "#e5a000"],
        rot=0,
    )

    for container in ax.containers:
        labels = [
            str(int(value)) if value else ""
            for value in container.datavalues
        ]
        ax.bar_label(container, labels=labels, label_type="center")

    ax.set_title("MOCK — F3 decisions by group (all splits)")
    ax.set_xlabel("Group")
    ax.set_ylabel("Number of samples")
    ax.legend(title="Decision")
    ax.set_axisbelow(True)
    ax.grid(axis="y", alpha=0.2)
    fig.text(
        0.5, 0.02,
        "Synthetic data; default scorer; no drift detector.",
        ha="center", fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "fig_mock_f3_decisions_by_group.png"
    fig.savefig(output, dpi=200)
    plt.close(fig)

    print(counts.to_string())
    print(f"Đã lưu: {output}")


if __name__ == "__main__":
    main()
    