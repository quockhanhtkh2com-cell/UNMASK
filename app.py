"""Demo UNMASK trên dữ liệu mock, chỉ chạy localhost."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
import streamlit as st

from unmask.filter import UnmaskFilter
from unmask.packed_score import PackedScorer
from unmask.dual_check import DualCheck
import schema_cols as S


st.set_page_config(page_title="UNMASK — Mock demo", layout="wide")
st.title("UNMASK — Vỏ đổi hay lõi đổi?")
st.caption(
    "MOCK DEMO — dữ liệu giả lập, không phải kết quả trên malware thật. "
    "Chỉ đọc feature tĩnh, không chạy file."
)

path = st.text_input(
    "Đường dẫn dataset mock",
    str(ROOT / "mock" / "mock_dataset_demo.csv"),
)

if not os.path.isfile(path):
    st.warning("Không tìm thấy dataset. Kiểm tra lại đường dẫn.")
    st.stop()

try:
    df = pd.read_csv(path)
except Exception as exc:
    st.error(f"Không đọc được CSV: {exc}")
    st.stop()

missing = [c for c in S.DATASET_COLS if c not in df.columns]
if missing:
    st.error(f"Dataset thiếu cột: {missing}")
    st.stop()

if df.empty:
    st.error("Dataset không có mẫu.")
    st.stop()

numeric_cols = [
    c for c in S.FEATURE_COLS if c != "section_name_class"
]
numeric = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

if not np.isfinite(numeric.to_numpy(dtype=float)).all():
    st.error("Feature số chứa giá trị trống, không phải số hoặc vô cực.")
    st.stop()

df[numeric_cols] = numeric

if not df["split"].isin(S.VALID_SPLIT).all():
    st.error("split phải là train, val hoặc test.")
    st.stop()

if df["origin_sha256"].isna().any():
    st.error("Có mẫu thiếu origin_sha256.")
    st.stop()

if (df.groupby("origin_sha256")["split"].nunique() > 1).any():
    st.error("Có origin nằm ở nhiều tập. Chạy check_data.py để kiểm tra.")
    st.stop()

use_dc = st.checkbox("Bật dual-check (F3)", value=True)

scorer = PackedScorer()
st.info(
    "Packed score dùng trọng số thủ công mặc định và ngưỡng 0.5. "
    "Đây là bản minh họa, chưa dùng mô hình đã train và khóa cấu hình."
)

core_cols = [
    c for c in S.CORE_FEATURE_COLS if c != "section_name_class"
]

dual = None
if use_dc:
    ref = df.loc[
        (df["group"] == "G0") & (df["split"] == "train"),
        core_cols,
    ].to_numpy(dtype=float)

    val = df.loc[
        (df["group"] == "G0") & (df["split"] == "val"),
        core_cols,
    ].to_numpy(dtype=float)

    if len(ref) < 3 or len(val) == 0:
        st.error(
            "Dual-check cần ít nhất 3 mẫu G0 train "
            "và 1 mẫu G0 val. Kiểm tra lại split."
        )
        st.stop()

    dual = DualCheck(ref)
    dual.lock_threshold(val, p=95)

    st.caption(
        f"Tham chiếu: {len(ref)} mẫu G0 train. "
        f"Chọn ngưỡng P95: {len(val)} mẫu G0 val."
    )
else:
    st.warning(
        "Chế độ F3a: bỏ dual-check; điểm pack cao sẽ bị FILTERED."
    )

f = UnmaskFilter(scorer, dual=dual, use_dualcheck=use_dc)
results = [f.decide(row) for row in df.to_dict("records")]

view = df[["sha256", "group", "variant", "packer", "split"]].copy()
view["packed_score"] = [r["packed_score"] for r in results]
view["decision"] = [r["decision"] for r in results]

st.caption(
    "Bảng hiển thị toàn bộ mẫu để minh họa. "
    "PASS và FLAGGED được chuyển tiếp tới detector; FILTERED bị loại. "
    "Demo này chưa chạy drift detector."
)

c1, c2, c3 = st.columns(3)
c1.metric("PASS", int(view["decision"].eq("PASS").sum()))
c2.metric("FILTERED", int(view["decision"].eq("FILTERED").sum()))
c3.metric("FLAGGED", int(view["decision"].eq("FLAGGED").sum()))

st.dataframe(view, use_container_width=True)

st.subheader("Evidence của một mẫu")
i = int(st.number_input(
    "Chỉ số dòng",
    min_value=0,
    max_value=len(df) - 1,
    value=0,
    step=1,
))

st.write(
    f"Nhóm: {view.iloc[i]['group']} · "
    f"Biến thể: {view.iloc[i]['variant']} · "
    f"Tập: {view.iloc[i]['split']}"
)
st.json(results[i])

st.download_button(
    "Tải bảng quyết định mock",
    data=view.to_csv(index=False).encode("utf-8-sig"),
    file_name="mock_demo_decisions.csv",
    mime="text/csv",
)