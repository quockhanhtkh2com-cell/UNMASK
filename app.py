"""Demo Streamlit — CHỈ chạy localhost. Hiển thị packed_score + evidence.

⚠️ Công cụ chỉ ĐỌC feature tĩnh, KHÔNG chạy file.

    streamlit run app.py
"""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st  # noqa: E402
import pandas as pd     # noqa: E402
from unmask.filter import UnmaskFilter  # noqa: E402
from unmask.packed_score import PackedScorer  # noqa: E402
from unmask.dual_check import DualCheck  # noqa: E402
import schema_cols as S  # noqa: E402

st.set_page_config(page_title="UNMASK — demo", layout="wide")
st.title("UNMASK — Vỏ đổi hay lõi đổi?")
st.caption("⚠️ Công cụ chỉ đọc feature tĩnh, KHÔNG chạy file. Demo localhost.")

default = os.path.join("mock", "mock_dataset.csv")
path = st.text_input("Đường dẫn dataset.csv", default)

if os.path.exists(path):
    df = pd.read_csv(path)
    use_dc = st.checkbox("Bật dual-check (F3 đầy đủ)", value=True)

    scorer = PackedScorer()
    core_cols = [c for c in S.CORE_FEATURE_COLS if c != "section_name_class"]
    ref = df[df.group == "G0"][core_cols].to_numpy(float)
    dual = None
    if use_dc and len(ref) >= 3:
        dual = DualCheck(ref); dual.lock_threshold(ref, p=95)
    f = UnmaskFilter(scorer, dual=dual, use_dualcheck=use_dc and dual is not None)

    results = [f.decide(r) for r in df.to_dict("records")]
    view = df[["sha256", "group", "variant", "packer"]].copy()
    view["packed_score"] = [r["packed_score"] for r in results]
    view["decision"] = [r["decision"] for r in results]

    c1, c2, c3 = st.columns(3)
    c1.metric("PASS", int((view.decision == "PASS").sum()))
    c2.metric("FILTERED", int((view.decision == "FILTERED").sum()))
    c3.metric("FLAGGED", int((view.decision == "FLAGGED").sum()))

    st.dataframe(view, use_container_width=True)

    st.subheader("Evidence của 1 mẫu")
    i = st.number_input("Chỉ số dòng", 0, len(df) - 1, 0)
    st.json({"decision": results[i]["decision"],
             "packed_score": results[i]["packed_score"],
             "evidence": results[i]["evidence"]})
else:
    st.warning("Chưa thấy file. Chạy `python mock/make_mock_dataset.py` trước.")
