"""Demo UNMASK trên dataset v1.1 và cấu hình đã khóa.

Chạy localhost:
    python -X utf8 -m streamlit run app.py --server.address 127.0.0.1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
import streamlit as st

import schema_cols as S
from unmask.filter import load_filter


st.set_page_config(
    page_title="UNMASK — Locked model demo",
    layout="wide",
)
st.title("UNMASK — Vỏ đổi hay lõi đổi?")
st.caption(
    "Demo trên bảng đặc trưng tĩnh và cấu hình đã khóa. "
    "Không chạy file PE."
)


def stop(message):
    st.error(message)
    st.stop()


dataset_text = st.text_input(
    "Đường dẫn dataset",
    str(ROOT / "dataset_v1.1.csv"),
)
config_text = st.text_input(
    "Đường dẫn cấu hình khóa",
    str(ROOT / "config" / "thresholds.locked.json"),
)

dataset_path = Path(dataset_text).expanduser()
config_path = Path(config_text).expanduser()

if not dataset_path.is_file():
    stop("Không tìm thấy dataset. Kiểm tra lại đường dẫn.")
if not config_path.is_file():
    stop("Không tìm thấy file cấu hình khóa.")

try:
    with config_path.open(encoding="utf-8") as handle:
        cfg = json.load(handle)

    if not isinstance(cfg, dict):
        raise ValueError("Cấu hình phải là một JSON object.")
    if cfg.get("locked") is not True:
        raise ValueError("Cấu hình chưa khóa: locked phải là true.")

    packed = cfg.get("packed_score")
    if not isinstance(packed, dict):
        raise ValueError("Thiếu cấu hình packed_score.")
    if not isinstance(packed.get("weights"), dict):
        raise ValueError("Thiếu trọng số packed score đã học.")
    if not packed["weights"]:
        raise ValueError("Trọng số packed score đang rỗng.")

    score_threshold = float(packed["threshold"])
    if not np.isfinite(score_threshold):
        raise ValueError("Ngưỡng packed score không hữu hạn.")
    if not 0 < score_threshold < 1:
        raise ValueError("Ngưỡng packed score phải nằm giữa 0 và 1.")

    weights = np.asarray(
        list(packed["weights"].values()), dtype=float
    )
    if not np.isfinite(weights).all():
        raise ValueError("Trọng số chứa giá trị không hữu hạn.")

    dual_cfg = cfg.get("dual_check")
    if not isinstance(dual_cfg, dict):
        raise ValueError("Thiếu cấu hình dual_check.")

    core_cols = dual_cfg.get("core_cols")
    if (
        not isinstance(core_cols, list)
        or not core_cols
        or not all(isinstance(c, str) for c in core_cols)
    ):
        raise ValueError("dual_check thiếu danh sách core_cols.")
    if len(core_cols) != len(set(core_cols)):
        raise ValueError("core_cols có cột trùng.")
    if not set(core_cols) <= set(S.CORE_FEATURE_COLS):
        raise ValueError("core_cols có cột ngoài schema lõi.")

    reference = np.asarray(
        dual_cfg.get("reference"), dtype=float
    )
    if (
        reference.ndim != 2
        or reference.shape[0] < 3
        or reference.shape[1] != len(core_cols)
    ):
        raise ValueError("Ma trận tham chiếu dual-check không hợp lệ.")
    if not np.isfinite(reference).all():
        raise ValueError("Tham chiếu dual-check không hữu hạn.")

    dual_threshold = float(dual_cfg["similarity_threshold"])
    if not np.isfinite(dual_threshold) or dual_threshold < 0:
        raise ValueError("Ngưỡng dual-check không hợp lệ.")

except Exception as exc:
    stop(f"Cấu hình không hợp lệ: {exc}")

try:
    df = pd.read_csv(
        dataset_path,
        dtype={
            "sha256": str,
            "origin_sha256": str,
        },
    )

    missing = [
        c for c in S.DATASET_COLS
        if c not in df.columns
    ]
    if missing:
        raise ValueError(f"Thiếu cột: {missing}")
    if df.empty:
        raise ValueError("Dataset không có mẫu.")
    if df[S.DATASET_COLS].isna().any().any():
        raise ValueError("Dataset thiếu giá trị bắt buộc.")

    for col in ["sha256", "origin_sha256"]:
        if not df[col].str.fullmatch(
            r"[0-9a-fA-F]{64}", na=False
        ).all():
            raise ValueError(f"{col} phải là SHA-256 gồm 64 ký tự hex.")
        df[col] = df[col].str.lower()

    if df["sha256"].duplicated().any():
        raise ValueError("Dataset có sha256 trùng.")
    if not df["group"].isin(S.VALID_GROUPS).all():
        raise ValueError("group không hợp lệ.")
    if not df["variant"].isin(S.VALID_VARIANTS).all():
        raise ValueError("variant không hợp lệ.")
    if not df["packer"].isin(S.VALID_PACKERS).all():
        raise ValueError("packer không hợp lệ.")
    if not df["section_name_class"].isin(
        S.VALID_SECTION_CLASS
    ).all():
        raise ValueError("section_name_class không hợp lệ.")
    if not df["split"].isin(S.VALID_SPLIT).all():
        raise ValueError("split phải là train, val hoặc test.")

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
        raise ValueError("Feature số không hợp lệ hoặc không hữu hạn.")
    df[numeric_cols] = numeric

    truth = pd.to_numeric(
        df["is_drift_truth"], errors="coerce"
    )
    if not truth.isin([0, 1]).all():
        raise ValueError("is_drift_truth chỉ được chứa 0/1.")
    if not truth.eq(df["group"].map(S.GROUP_IS_DRIFT)).all():
        raise ValueError("is_drift_truth không khớp group.")
    df["is_drift_truth"] = truth.astype(int)

except Exception as exc:
    stop(f"Dataset không hợp lệ: {exc}")

mode = st.radio(
    "Cổng minh họa",
    ["F3 — Có dual-check", "F3a — Không dual-check"],
    horizontal=True,
)
use_dualcheck = mode.startswith("F3 —")
gate_name = "F3" if use_dualcheck else "F3a"

try:
    model = load_filter(
        str(config_path),
        use_dualcheck=use_dualcheck,
    )
    results = [
        model.decide(row)
        for row in df.to_dict("records")
    ]

    scores = np.asarray(
        [r["packed_score"] for r in results],
        dtype=float,
    )
    decisions = [r["decision"] for r in results]

    if (
        not np.isfinite(scores).all()
        or (scores < 0).any()
        or (scores > 1).any()
    ):
        raise ValueError("Mô hình trả packed score không hợp lệ.")
    if not set(decisions) <= {"PASS", "FILTERED", "FLAGGED"}:
        raise ValueError("Mô hình trả quyết định không hợp lệ.")

except Exception as exc:
    stop(f"Không chạy được mô hình khóa: {exc}")

st.success(
    f"Đã đọc cấu hình khóa: {config_path.name} · "
    f"Ngưỡng packed score: {score_threshold:.4f}"
)
st.caption(
    f"Dataset: {dataset_path.name} · {len(df)} mẫu. "
    "Tham chiếu và ngưỡng dual-check được lấy từ config; "
    "demo không huấn luyện hoặc chọn lại ngưỡng."
)
if use_dualcheck:
    st.caption(
        f"Dual-check: {len(reference)} mẫu tham chiếu · "
        f"Ngưỡng khoảng cách: {dual_threshold:.6g}"
    )
else:
    st.warning(
        "F3a là chế độ ablation: bỏ dual-check. "
        "Điểm pack cao sẽ bị FILTERED."
    )

view = df[[
    "sha256", "group", "variant", "packer", "split",
]].copy()
view["packed_score"] = scores
view["decision"] = decisions
view.insert(0, "row_id", np.arange(len(view)))

split_options = [
    s for s in ["test", "train", "val"]
    if s in set(view["split"])
]
split_choice = st.selectbox(
    "Tập hiển thị",
    ["Tất cả"] + split_options,
    index=1 if "test" in split_options else 0,
)
group_choice = st.selectbox(
    "Nhóm hiển thị",
    ["Tất cả"] + [
        g for g in ["G0", "G1", "G2", "G3"]
        if g in set(view["group"])
    ],
)

shown = view.copy()
if split_choice != "Tất cả":
    shown = shown.loc[shown["split"].eq(split_choice)]
if group_choice != "Tất cả":
    shown = shown.loc[shown["group"].eq(group_choice)]

st.caption(
    f"Đang hiển thị {len(shown)} mẫu · Cổng {gate_name}. "
    "PASS và FLAGGED được chuyển tiếp tới D1 trong pipeline. "
    "Demo này chỉ hiển thị quyết định bộ lọc, chưa chạy D1."
)

c1, c2, c3 = st.columns(3)
c1.metric("PASS", int(shown["decision"].eq("PASS").sum()))
c2.metric("FILTERED", int(shown["decision"].eq("FILTERED").sum()))
c3.metric("FLAGGED", int(shown["decision"].eq("FLAGGED").sum()))

st.dataframe(shown, use_container_width=True)

if shown.empty:
    st.info("Không có mẫu phù hợp với lựa chọn hiển thị.")
else:
    st.subheader("Evidence của một mẫu")

    row_id = st.selectbox(
        "Chọn mẫu",
        shown["row_id"].tolist(),
        format_func=lambda idx: (
            f"Dòng {idx} · {view.iloc[idx]['group']} · "
            f"{view.iloc[idx]['sha256'][:16]}…"
        ),
    )
    selected = view.iloc[int(row_id)]

    st.write(
        f"Nhóm: {selected['group']} · "
        f"Biến thể: {selected['variant']} · "
        f"Packer: {selected['packer']} · "
        f"Split: {selected['split']}"
    )
    st.code(selected["sha256"], language=None)
    st.json(results[int(row_id)])

st.download_button(
    "Tải bảng quyết định đang hiển thị",
    data=shown.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"demo_{gate_name.lower()}_decisions.csv",
    mime="text/csv",
)