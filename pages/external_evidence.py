import streamlit as st
from core.loaders import load_external_evidence
from core.ui import page_header

page_header(
    "Independent biological validation",
    "External Evidence",
    "用于集中展示 STEP32A–32D 的独立扰动证据，并与 frozen DAG-v2 hypothesis 对齐。",
)

df = load_external_evidence()

if df.empty:
    st.info(
        "当前尚未生成 `data_cache/external_evidence.parquet`。"
        "下一步可把 GSE244209、GSE158469、GSE226076、GSE271192 的 summary CSV 统一转换。"
    )
    st.markdown(
        """
        计划内容：
        - INPP5D / GSE244209
        - TREM2 / GSE158469
        - APOE-LXR / GSE226076
        - NLRP3 / GSE271192
        - specificity、context dependence、Program-level effects
        """
    )
else:
    st.dataframe(df, use_container_width=True, hide_index=True)
