"""Demo UNMASK: đọc dataset feature và cấu hình F3 đã khóa."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
import streamlit as st

import schema_cols as S
from unmask.filter import filter_row


st.set_page_config(page_title="UNMASK — Demo", layout="wide")
st.title("UNMASK — Vỏ đổi hay lõi đổi?")
st.caption(
    "Chỉ đọc feature tĩnh, không chạy file PE. "
    "Demo không huấn luyện mô hình hoặc chọn lại ngưỡng."
)


def resolve_path(value: str) -> Path:
    path = Path(value.strip()).expanduser()
    return path if path.is_absolute() else ROOT / path


def finite_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and np.isfinite(value)
    )


dataset_input = st.text_input(
    "Đường dẫn dataset CSV",
    "dataset_v1.0.csv",
)
config_input = st.text_input(
    "Đường dẫn config đã khóa",
    "config/thresholds.locked.json",
)

mode = st.radio(
    "Cổng lọc",
    ["F3 — có dual-check", "F3a — bỏ dual-check"],
)
use_dualcheck = mode.startswith("F3 —")

dataset_path = resolve_path(dataset_input)
config_path = resolve_path(config_input)

if not dataset_path.is_file():
    st.error(f"Không tìm thấy dataset: {dataset_path}")
    st.stop()

try:
    df = pd.read_csv(dataset_path)
except Exception as exc:
    st.error(f"Không đọc được dataset: {exc}")
    st.stop()

missing = [col for col in S.DATASET_COLS if col not in df.columns]
if missing:
    st.error(f"Dataset thiếu cột: {missing}")
    st.stop()

if df.empty:
    st.error("Dataset không có mẫu.")
    st.stop()

required = S.ID_COLS + S.LABEL_COLS
if df[required].isna().any().any():
    st.error("Có giá trị trống trong cột định danh, nhãn hoặc split.")
    st.stop()

if df["sha256"].duplicated().any():
    st.error("Dataset có SHA-256 trùng.")
    st.stop()

for col, allowed in [
    ("group", S.VALID_GROUPS),
    ("variant", S.VALID_VARIANTS),
    ("packer", S.VALID_PACKERS),
    ("split", S.VALID_SPLIT),
    ("section_name_class", S.VALID_SECTION_CLASS),
]:
    if not df[col].isin(allowed).all():
        st.error(f"Cột {col} chứa giá trị không hợp lệ.")
        st.stop()

numeric_cols = [
    col for col in S.FEATURE_COLS
    if col != "section_name_class"
]
numeric = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

if not np.isfinite(numeric.to_numpy(dtype=float)).all():
    st.error("Feature số chứa giá trị trống, không phải số hoặc vô cực.")
    st.stop()

df[numeric_cols] = numeric

truth = pd.to_numeric(df["is_drift_truth"], errors="coerce")
if not truth.eq(df["group"].map(S.GROUP_IS_DRIFT)).all():
    st.error("is_drift_truth không khớp group.")
    st.stop()

if (df.groupby("origin_sha256")["split"].nunique() > 1).any():
    st.error("Có origin xuất hiện ở nhiều split.")
    st.stop()

st.write(f"Dataset: **{dataset_path.name}** · **{len(df)} mẫu**")
st.dataframe(
    pd.crosstab(df["group"], df["split"]),
    use_container_width=True,
)
st.caption(
    "Kiểm tra đầu vào của demo không thay thế kiểm tra E0 "
    "và đối chiếu manifest."
)

if not config_path.is_file():
    st.warning(f"Chưa tìm thấy config: {config_path}")
    st.stop()

try:
    with config_path.open(encoding="utf-8-sig") as handle:
        config = json.load(handle)
except Exception as exc:
    st.error(f"Không đọc được config JSON: {exc}")
    st.stop()

if not isinstance(config, dict):
    st.error("Config phải là một JSON object.")
    st.stop()

if config.get("locked") is not True:
    st.warning(
        "Config chưa khóa. Chờ config chính thức từ người phụ trách F3. "
        "Demo chưa tính packed score hoặc quyết định."
    )
    st.stop()

ps = config.get("packed_score")
if not isinstance(ps, dict):
    st.error("Config thiếu packed_score hợp lệ.")
    st.stop()

weights = ps.get("weights")
threshold = ps.get("threshold")

if (
    not isinstance(weights, dict)
    or not weights
    or not all(finite_number(v) for v in weights.values())
):
    st.error("Trọng số packed score bị thiếu hoặc không hợp lệ.")
    st.stop()

if not finite_number(threshold) or not 0 < threshold <= 1:
    st.error("Ngưỡng packed score phải lớn hơn 0 và không vượt quá 1.")
    st.stop()

if use_dualcheck:
    dc = config.get("dual_check")
    if not isinstance(dc, dict):
        st.error("F3 cần cấu hình dual_check đã khóa.")
        st.stop()

    if not dc.get("reference") or not dc.get("core_cols"):
        st.error("Config thiếu reference hoặc core_cols của dual-check.")
        st.stop()

    dc_threshold = dc.get("similarity_threshold")
    if not finite_number(dc_threshold) or dc_threshold < 0:
        st.error("Ngưỡng dual-check bị thiếu hoặc không hợp lệ.")
        st.stop()

    absent = [col for col in dc["core_cols"] if col not in df.columns]
    if absent:
        st.error(f"Dataset thiếu feature lõi trong config: {absent}")
        st.stop()

st.success("Đã đọc config có locked=true.")
st.caption(
    "Trạng thái locked được đọc từ config; "
    "demo không xác nhận lịch sử commit khóa ngưỡng."
)

if not use_dualcheck:
    st.warning("F3a đang bỏ dual-check.")

try:
    with st.spinner("Đang tính kết quả từ config đã khóa..."):
        results = [
            filter_row(
                row,
                locked_config=config,
                use_dualcheck=use_dualcheck,
            )
            for row in df.to_dict("records")
        ]
except Exception as exc:
    st.error(f"Không chạy được cổng lọc với config này: {exc}")
    st.stop()

view = df[
    ["sha256", "group", "variant", "packer", "split"]
].copy()
view["packed_score"] = [result["packed_score"] for result in results]
view["decision"] = [result["decision"] for result in results]
view["evidence"] = [
    json.dumps(result["evidence"], ensure_ascii=False)
    for result in results
]

st.caption(
    "Kết quả bên dưới chỉ là quyết định cổng lọc. "
    "PASS/FLAGGED được chuyển tiếp tới detector; FILTERED bị loại. "
    "Demo này chưa chạy detector hoặc tính FTR."
)

split_choice = st.selectbox(
    "Tập hiển thị",
    ["Tất cả", "train", "val", "test"],
)

shown = (
    view if split_choice == "Tất cả"
    else view.loc[view["split"].eq(split_choice)]
)

c1, c2, c3 = st.columns(3)
c1.metric("PASS", int(shown["decision"].eq("PASS").sum()))
c2.metric("FILTERED", int(shown["decision"].eq("FILTERED").sum()))
c3.metric("FLAGGED", int(shown["decision"].eq("FLAGGED").sum()))

st.dataframe(
    shown.drop(columns="evidence"),
    use_container_width=True,
)

st.subheader("Evidence của một mẫu")

if shown.empty:
    st.info("Không có mẫu trong tập đã chọn.")
else:
    selected = st.selectbox(
        "Chọn mẫu",
        shown.index.tolist(),
        format_func=lambda index: (
            f"Dòng {index} · {view.loc[index, 'group']} · "
            f"{view.loc[index, 'sha256'][:16]}…"
        ),
    )
    st.json({
        "sha256": view.loc[selected, "sha256"],
        **results[selected],
    })

gate = "f3" if use_dualcheck else "f3a"
st.download_button(
    "Tải kết quả tập đang hiển thị",
    data=shown.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"demo_{gate}_decisions.csv",
    mime="text/csv",
)