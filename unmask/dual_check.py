"""F3 — Bước 2: dual-check (chống lỗi L1) — [Tuấn].

Điểm pack cao chỉ nói "có vẻ bị pack", CHƯA nói "lõi không đổi". Bỏ các feature
liên quan đến packing, so phần LÕI còn lại (.NET metadata, header không bị viết lại,
kích thước gốc...) với tập THAM CHIẾU mẫu đã biết (AgentTesla).

- Gần mẫu tham chiếu  -> FILTERED (chỉ đổi vỏ)
- Không gần / pattern khác hẳn -> FLAGGED (vẫn vào chuông + cờ)

⚠️ Chỗ cần đo kỹ nhất: njRAT cũng là .NET -> dual-check có thể tưởng "giống
AgentTesla" -> FILTERED nhầm -> chuông mù trước malware mới (L1). F3a (bỏ dual-check)
dùng để đo riêng công của bước này.

API:
    dc = DualCheck(reference_core_matrix, threshold)   # fit trên CORE_FEATURE_COLS của G0
    verdict = dc.check(core_feature_dict) -> "similar" | "novel"
"""
from __future__ import annotations
import numpy as np


class DualCheck:
    def __init__(self, ref_matrix: np.ndarray, threshold: float | None = None,
                 core_cols: list | None = None):
        """ref_matrix: ndarray (n_ref × n_core_feature) của mẫu THAM CHIẾU đã biết.
        core_cols: tên cột lõi theo đúng thứ tự các cột của ref_matrix."""
        self.core_cols = list(core_cols) if core_cols else None
        self.ref = np.asarray(ref_matrix, dtype=float)
        self.mean = self.ref.mean(axis=0)
        self.std = self.ref.std(axis=0) + 1e-9
        self.threshold = threshold

    def _dist(self, x: np.ndarray) -> float:
        """Khoảng cách Euclid chuẩn hoá tới mẫu tham chiếu GẦN NHẤT."""
        xz = (np.asarray(x, dtype=float) - self.mean) / self.std
        refz = (self.ref - self.mean) / self.std
        d = np.sqrt(((refz - xz) ** 2).sum(axis=1))
        return float(d.min())

    def lock_threshold(self, core_val: np.ndarray, p: float = 95) -> float:
        """Khoá ngưỡng: P95 khoảng cách của validation G0 tới tham chiếu."""
        dists = [self._dist(row) for row in np.asarray(core_val, dtype=float)]
        self.threshold = float(np.percentile(dists, p))
        return self.threshold

    def lock_threshold_loo(self, p: float = 95) -> float:
        """Phương án tạm khi CHƯA có G0 validation (vd mock): leave-one-out — khoảng cách của
        từng mẫu tham chiếu tới các mẫu tham chiếu CÒN LẠI (không tính chính nó), lấy P95.
        Dữ liệu thật phải dùng G0 val (lock_threshold)."""
        refz = (self.ref - self.mean) / self.std
        if len(refz) < 2:
            raise ValueError("Cần ít nhất 2 mẫu tham chiếu để khoá ngưỡng leave-one-out.")
        dists = []
        for i in range(len(refz)):
            others = np.delete(refz, i, axis=0)
            dists.append(float(np.sqrt(((others - refz[i]) ** 2).sum(axis=1)).min()))
        self.threshold = float(np.percentile(dists, p))
        return self.threshold

    def to_config(self) -> dict:
        return {"similarity_threshold": self.threshold, "core_cols": self.core_cols,
                "reference": self.ref.tolist()}

    @classmethod
    def from_config(cls, cfg: dict | None) -> "DualCheck":
        if not cfg or cfg.get("similarity_threshold") is None or not cfg.get("reference"):
            raise ValueError("Config khoá chưa có dual_check (reference + similarity_threshold). "
                             "Chạy unmask/train.py trên dữ liệu đã chia split, hoặc dùng "
                             "use_dualcheck=False (F3a).")
        return cls(np.asarray(cfg["reference"], dtype=float), cfg["similarity_threshold"],
                   cfg.get("core_cols"))

    def check(self, core_feat: np.ndarray) -> str:
        if self.threshold is None:
            raise RuntimeError("Chưa khoá ngưỡng dual-check.")
        return "similar" if self._dist(core_feat) <= self.threshold else "novel"


def fit_from_dataframe(df, core_cols, p: float = 95):
    """Dựng DualCheck từ dataset: tham chiếu = G0 thuộc split 'train'; khoá ngưỡng bằng P95
    khoảng cách của G0 split 'val' tới tham chiếu. Chưa có G0 val -> leave-one-out.
    Dataset chưa có cột split (chưa chia) -> dùng toàn bộ G0. KHÔNG dùng split 'test'.
    Trả (DualCheck, info)."""
    g0 = df[df["group"] == "G0"]
    if "split" in df.columns:
        ref_df = g0[g0["split"] == "train"]
        val_df = g0[g0["split"] == "val"]
        if ref_df.empty:
            raise ValueError("Không có G0 thuộc split 'train' để làm tham chiếu dual-check.")
    else:
        ref_df, val_df = g0, g0.iloc[0:0]
    if len(ref_df) < 3:
        raise ValueError(f"Cần ít nhất 3 mẫu G0 tham chiếu, chỉ có {len(ref_df)}.")
    dc = DualCheck(ref_df[core_cols].to_numpy(dtype=float), core_cols=core_cols)
    if len(val_df):
        dc.lock_threshold(val_df[core_cols].to_numpy(dtype=float), p=p)
        source = "G0 val"
    else:
        dc.lock_threshold_loo(p=p)
        source = "leave-one-out (chưa có G0 val)"
    info = {"threshold_source": source, "n_ref": int(len(ref_df)), "n_val": int(len(val_df)),
            "percentile": p}
    return dc, info
