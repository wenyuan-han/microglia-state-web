import streamlit as st
from core.loaders import load_intervention_summary
from core.ui import page_header

page_header(
    "Mechanism-aware model audit",
    "Virtual Intervention",
    "从 STEP35A 的预计算结果读取机制传递干预，不在第一版网页中实时调用 GPU。",
)

df = load_intervention_summary()

if df.empty:
    st.info(
        "当前尚未生成 `data_cache/intervention_summary.parquet`。"
        "完成 STEP35A 后即可接入 NLRP3 / TFEB / TREM2-SYK / APOE-LXR 的 α 干预结果。"
    )

    mechanism = st.selectbox(
        "Mechanism",
        ["NLRP3", "TFEB", "TREM2/SYK", "APOE/LXR"],
    )
    alpha = st.select_slider(
        "Intervention strength α",
        options=[0.0, 0.5, 1.0, 1.5, 2.0],
        value=1.0,
    )
    st.caption(f"Preview only: {mechanism}, α={alpha}")
else:
    mechanisms = sorted(df["mechanism_short"].dropna().astype(str).unique().tolist())
    mechanism = st.selectbox("Mechanism", mechanisms)
    sub = df[df["mechanism_short"].astype(str) == mechanism]

    alpha_options = sorted(sub["alpha"].dropna().astype(float).unique().tolist())
    alpha = st.select_slider("Intervention strength α", options=alpha_options, value=alpha_options[0])
    view = sub[sub["alpha"].astype(float) == float(alpha)]

    st.dataframe(view, use_container_width=True, hide_index=True)
