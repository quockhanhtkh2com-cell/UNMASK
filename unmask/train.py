"""F3 — Học trọng số packed_score + quét ngưỡng -> KHOÁ — [Tuấn].

Chỉ học trên G0 + G1-UPX (P-seen) của tập train/val. KHÔNG thấy P-unseen/low/wild.
Bước 3 (chống L2): quét ngưỡng trên validation -> vẽ đường FTR–FNR -> chọn điểm vận
hành (vd FNR G3 < 5%) rồi ghi vào config/thresholds.locked.json.

    python unmask/train.py --dataset mock/mock_dataset.csv --out config/thresholds.locked.json
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import schema_cols as S  # noqa: E402
from packed_score import NUMERIC, SECTION_CLASS_WEIGHT  # type: ignore  # noqa: E402


def _featurize(df):
    import numpy as np
    X = []
    for r in df.to_dict("records"):
        row = [float(r.get(k, 0) or 0) for k in NUMERIC]
        row.append(SECTION_CLASS_WEIGHT.get(r.get("section_name_class", "standard"), 0.5))
        X.append(row)
    return np.asarray(X, dtype=float)


def train(dataset: str, out: str, seed: int = 0):
    import numpy as np, pandas as pd
    from sklearn.linear_model import LogisticRegression

    df = pd.read_csv(dataset)
    # đề ôn: G0 (nhãn pack=0) + G1-UPX/P-seen (nhãn pack=1). Chỉ train/val.
    prep = df[(df.split.isin(["train", "val"]))].copy()
    prep = prep[(prep.group == "G0") |
                ((prep.group == "G1") & (prep.variant == "P-seen"))]
    if prep.empty:
        sys.exit("Không có dữ liệu đề ôn (G0 + G1 P-seen) trong train/val. "
                 "Chạy src/split_data.py trước.")
    y = ((prep.group == "G1")).astype(int).to_numpy()
    X = _featurize(prep)

    clf = LogisticRegression(max_iter=1000, random_state=seed)
    clf.fit(X, y)
    cols = NUMERIC + ["section_class"]
    weights = {c: float(w) for c, w in zip(cols, clf.coef_[0])}
    weights["bias"] = float(clf.intercept_[0])

    # quét ngưỡng trên validation -> chọn điểm vận hành (ở đây: Youden J trên đề ôn,
    # nhóm thay bằng mục tiêu FNR G3 < 5% khi có đủ G2/G3 trong val THẬT).
    val = prep[prep.split == "val"] if (prep.split == "val").any() else prep
    probs = 1 / (1 + np.exp(-(_featurize(val) @ clf.coef_[0] + clf.intercept_[0])))
    yv = (val.group == "G1").astype(int).to_numpy()
    best_thr, best_j = 0.5, -1
    for thr in np.linspace(0.1, 0.9, 33):
        pred = probs >= thr
        tpr = (pred & (yv == 1)).sum() / max(1, (yv == 1).sum())
        fpr = (pred & (yv == 0)).sum() / max(1, (yv == 0).sum())
        if tpr - fpr > best_j:
            best_j, best_thr = tpr - fpr, float(thr)

    cfg_path = out
    base = {}
    if os.path.exists(cfg_path):
        base = json.load(open(cfg_path))
    base.update({
        "locked": True,
        "locked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "locked_by": "train.py",
        "packed_score": {
            "model": "logistic",
            "weights": weights,
            "threshold": round(best_thr, 4),
            "train_groups": ["G0", "G1"],
            "train_packer_seen": "upx",
        },
    })
    base.setdefault("detector_D1", {"method": "mahalanobis", "percentile": 95,
                                    "fitted_on": ["G0", "val"], "threshold_value": None})
    base.setdefault("dual_check", {"similarity_threshold": None})
    base["seeds"] = [0, 1, 2]
    json.dump(base, open(cfg_path, "w"), indent=2, ensure_ascii=False)
    print(f"[train] threshold={best_thr:.3f}  weights={ {k: round(v,2) for k,v in weights.items()} }")
    print(f"[train] ĐÃ KHOÁ -> {cfg_path}")
    print("⚠️  Commit file này TRƯỚC khi chạy E3–E5. Không sửa sau khi nhìn đề thi.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..",
                                                  "config", "thresholds.locked.json"))
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    train(args.dataset, args.out, args.seed)


if __name__ == "__main__":
    main()
