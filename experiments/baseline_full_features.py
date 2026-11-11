"""Baseline ML — F3-LR(full) / F3-RF(full) — [Khánh].

Mục đích: kiểm tra xem việc chọn tay 8 đặc trưng domain-knowledge cho packed_score
(xem unmask/packed_score.py) có thực sự tốt hơn việc đưa TOÀN BỘ các đặc trưng cùng
họ "packing" (PACKING_FEATURE_COLS trong src/schema_cols.py, 15 cột) cho một model
chuẩn (Logistic Regression / Random Forest) tự học hay không.

Thiết kế để so sánh CÔNG BẰNG với F3:
- Cùng tập train/val (G0 + G1-P-seen, đúng như unmask/train.py đang làm)
- Cùng cách chuẩn hoá (StandardScaler fit trên train)
- Cùng cách khoá ngưỡng (Youden J trên validation, giống hệt unmask/train.py)
- Cùng dual_check đã khoá sẵn trong config/thresholds.locked.json (KHÔNG train lại
  dual_check — chỉ thay phần packed_score để cô lập đúng 1 biến: tập đặc trưng +
  thuật toán của bước tính điểm "khả năng bị pack")
- Cùng chuông D1 (Mahalanobis, ngưỡng khoá 6,9111) và cùng cách đo FTR/FNR như
  experiments/run_experiments.py (pack_ratio=0.5, subsample N=250, giống Bảng 7.3)

KHÔNG ghi đè config/thresholds.locked.json của F3. Output riêng:
    results/baseline_full_features.csv

Dùng:
    python experiments/baseline_full_features.py --dataset dataset_v1.1.csv \\
        --config config/thresholds.locked.json --out results/baseline_full_features.csv
"""
from __future__ import annotations
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, ".."))

import numpy as np
import pandas as pd

import schema_cols as S          # noqa: E402
import eval_metrics as M         # noqa: E402
from detector import DriftDetector  # noqa: E402
from unmask.filter import UnmaskFilter, load_filter  # noqa: E402
from unmask.dual_check import DualCheck  # noqa: E402
from unmask.packed_score import SECTION_CLASS_WEIGHT  # noqa: E402

# "Full" = toàn bộ họ đặc trưng packing (cùng NHÓM với 8 cột packed_score đang dùng),
# KHÔNG trộn core_cols (file_size, size_of_headers, compile_timestamp, is_dotnet) vào
# đây — core_cols là phần dual_check cố tình giữ riêng để so lõi. Trộn vào sẽ làm
# thí nghiệm không còn là "ablation tập đặc trưng packing" nữa mà phá luôn ranh giới
# kiến trúc packing-feature vs core-feature mà F3 đang dựa vào.
FULL_PACKING_COLS = list(S.PACKING_FEATURE_COLS)  # 15 cột, bao gồm section_name_class
NUMERIC_FULL = [c for c in FULL_PACKING_COLS if c != "section_name_class"]


def featurize(df: pd.DataFrame) -> np.ndarray:
    X = []
    for r in df.to_dict("records"):
        row = [float(r.get(k, 0) or 0) for k in NUMERIC_FULL]
        row.append(SECTION_CLASS_WEIGHT.get(r.get("section_name_class", "standard"), 0.5))
        X.append(row)
    return np.asarray(X, dtype=float)


class BaselineScorer:
    """Interface tương thích PackedScorer: .score(feat)->[0,1], .threshold, .evidence()."""

    def __init__(self, model, scaler_mean, scaler_scale, threshold: float, cols: list):
        self.model = model
        self.mean = scaler_mean
        self.scale = scaler_scale
        self.threshold = threshold
        self.cols = cols  # NUMERIC_FULL + ["section_class"]

    def _vector(self, feat: dict) -> np.ndarray:
        row = [float(feat.get(k, 0) or 0) for k in NUMERIC_FULL]
        row.append(SECTION_CLASS_WEIGHT.get(feat.get("section_name_class", "standard"), 0.5))
        x = np.asarray(row, dtype=float)
        nnum = len(NUMERIC_FULL)
        x[:nnum] = (x[:nnum] - self.mean) / self.scale
        return x.reshape(1, -1)

    def score(self, feat: dict) -> float:
        x = self._vector(feat)
        return float(self.model.predict_proba(x)[0, 1])

    def evidence(self, feat: dict, top: int = 3) -> list[dict]:
        # Không bắt buộc cho pipeline quyết định, chỉ để tương thích interface.
        if hasattr(self.model, "coef_"):
            x = self._vector(feat)[0]
            contrib = {c: float(w * v) for c, w, v in zip(self.cols, self.model.coef_[0], x)}
            ranked = sorted(contrib.items(), key=lambda kv: abs(kv[1]), reverse=True)
            return [{"feature": k, "contribution": round(v, 3)} for k, v in ranked[:top]]
        return []

    def is_packed(self, feat: dict) -> bool:
        return self.score(feat) >= self.threshold


def _youden_threshold(probs: np.ndarray, y: np.ndarray) -> float:
    grid = np.linspace(0.1, 0.9, 33)
    js = []
    for thr in grid:
        pred = probs >= thr
        tpr = (pred & (y == 1)).sum() / max(1, (y == 1).sum())
        fpr = (pred & (y == 0)).sum() / max(1, (y == 0).sum())
        js.append(tpr - fpr)
    js = np.asarray(js)
    best_j = js.max()
    return float(np.median(grid[js >= best_j - 1e-9]))


def train_baseline(df: pd.DataFrame, algo: str, seed: int = 0) -> BaselineScorer:
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler

    prep = df[df.split.isin(["train", "val"])].copy()
    prep = prep[(prep.group == "G0") | ((prep.group == "G1") & (prep.variant == "P-seen"))]
    if prep.empty:
        sys.exit("Không có dữ liệu đề ôn (G0 + G1 P-seen) trong train/val.")

    train_df = prep[prep.split == "train"]
    val_df = prep[prep.split == "val"] if (prep.split == "val").any() else prep

    y_train = (train_df.group == "G1").astype(int).to_numpy()
    X_train_raw = featurize(train_df)

    nnum = len(NUMERIC_FULL)
    scaler = StandardScaler().fit(X_train_raw[:, :nnum])
    X_train = X_train_raw.copy()
    X_train[:, :nnum] = (X_train[:, :nnum] - scaler.mean_) / scaler.scale_

    if algo == "lr":
        clf = LogisticRegression(max_iter=1000, random_state=seed)
    elif algo == "rf":
        clf = RandomForestClassifier(n_estimators=300, random_state=seed)
    else:
        raise ValueError(algo)
    clf.fit(X_train, y_train)

    X_val_raw = featurize(val_df)
    X_val = X_val_raw.copy()
    X_val[:, :nnum] = (X_val[:, :nnum] - scaler.mean_) / scaler.scale_
    y_val = (val_df.group == "G1").astype(int).to_numpy()
    probs_val = clf.predict_proba(X_val)[:, 1]
    thr = _youden_threshold(probs_val, y_val)

    cols = NUMERIC_FULL + ["section_class"]
    return BaselineScorer(clf, scaler.mean_, scaler.scale_, thr, cols)


def _subsample_to_ratio(df, pack_ratio: float, seed: int):
    packed = df[df.group.isin(["G1", "G3"]) | df.variant.isin(["P-low", "P-wild"])]
    clean = df[~df.index.isin(packed.index)]
    if len(packed) == 0 or len(clean) == 0:
        return df
    n_total = 250
    n_packed = int(round(pack_ratio * n_total))
    n_clean = n_total - n_packed
    if len(packed) < n_packed or len(clean) < n_clean:
        return df
    out = pd.concat([packed.sample(n_packed, random_state=seed),
                     clean.sample(n_clean, random_state=seed)])
    return out.reset_index(drop=True)


def evaluate_gate(name: str, decide_fn, df_test, det, pack_ratio: float, seed: int, rows: list):
    sample = _subsample_to_ratio(df_test, pack_ratio, seed)
    ratio_real = M.pack_ratio(list(sample.group), list(sample.variant))

    FEATURE_NUM = [c for c in S.FEATURE_COLS if c != "section_name_class"]
    dec_sample = [decide_fn(r)["decision"] for r in sample.to_dict("records")]
    X = sample[FEATURE_NUM].to_numpy(float)
    alarms = det.predict(X)

    dec_full = [decide_fn(r)["decision"] for r in df_test.to_dict("records")]

    rows.append({
        "gate": name, "seed": seed,
        "pack_ratio_set": pack_ratio, "pack_ratio_real": round(ratio_real, 3),
        "FTR": M.ftr(dec_sample, list(sample.group), alarms).value,
        "FNR_G2": M.fnr(dec_sample, list(sample.group), "G2").value,
        "FNR_G3": M.fnr(dec_sample, list(sample.group), "G3").value,
        "FNR_e2e_G2": M.fnr_end2end(dec_sample, alarms, list(sample.group), "G2").value,
        "FNR_e2e_G3": M.fnr_end2end(dec_sample, alarms, list(sample.group), "G3").value,
        "correct_filter_Pseen": M.correct_filter_rate(dec_full, list(df_test.group), list(df_test.variant), "P-seen").value,
        "correct_filter_Punseen": M.correct_filter_rate(dec_full, list(df_test.group), list(df_test.variant), "P-unseen").value,
        "flagged_rate": M.flagged_rate(dec_full).value,
    })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--config", default=os.path.join(HERE, "..", "config", "thresholds.locked.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "results", "baseline_full_features.csv"))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--pack-ratio", type=float, default=0.5)
    args = ap.parse_args()

    df = pd.read_csv(args.dataset)
    cfg = json.load(open(args.config, encoding="utf-8"))

    # Chuông D1 chung — y hệt run_experiments.py
    FEATURE_NUM = [c for c in S.FEATURE_COLS if c != "section_name_class"]
    g0_train = df[(df.group == "G0") & (df.split == "train")][FEATURE_NUM].to_numpy(float)
    g0_val = df[(df.group == "G0") & (df.split == "val")][FEATURE_NUM].to_numpy(float)
    det = DriftDetector(method="mahalanobis", seed=args.seed, standardize=True).fit(g0_train)
    d1_cfg = cfg.get("detector_D1", {})
    if d1_cfg.get("threshold_value"):
        det.threshold = float(d1_cfg["threshold_value"])
    else:
        det.lock_threshold(g0_val, p=d1_cfg.get("percentile", 80))

    # dual_check: dùng LẠI nguyên bản đã khoá của F3, không train lại
    dual = DualCheck.from_config(cfg["dual_check"])

    # F3 / F3a gốc, để in ra so sánh trực tiếp trong cùng 1 lần chạy
    f3_filter = load_filter(cfg, use_dualcheck=True)
    f3a_filter = load_filter(cfg, use_dualcheck=False)

    df_test = df[df.split == "test"].reset_index(drop=True)

    rows = []
    evaluate_gate("F3", lambda r: f3_filter.decide(r), df_test, det, args.pack_ratio, args.seed, rows)
    evaluate_gate("F3a", lambda r: f3a_filter.decide(r), df_test, det, args.pack_ratio, args.seed, rows)

    for algo, label in [("lr", "F3-LR(full)"), ("rf", "F3-RF(full)")]:
        scorer = train_baseline(df, algo, seed=args.seed)
        gate = UnmaskFilter(scorer, dual=dual, use_dualcheck=True)
        evaluate_gate(label, lambda r, g=gate: g.decide(r), df_test, det, args.pack_ratio, args.seed, rows)

    out_df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    out_df.to_csv(args.out, index=False)
    print(out_df.to_string(index=False))
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
