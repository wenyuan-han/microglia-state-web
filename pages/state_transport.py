import streamlit as st
from core.loaders import load_transport_metrics
from core.ui import page_header

page_header(
    "Distribution transport",
    "State Transport",
    "用于比较 Base、DAG-v1、DAG-v2 与 matched rewired controls 的 distribution-level transport。第一版先接入预计算结果，不在网页实时跑 RK4。",
)

df = load_transport_metrics()

if df.empty:
    st.info(
        "当前尚未生成 `data_cache/transport_metrics.parquet`。"
        "下一步可由 STEP34B 的 pair-level CSV 自动转换。"
    )
    st.markdown(
        """
        计划交互：
        - 选择 source donor / target donor
        - 比较 Base / DAG-v1 / DAG-v2
        - 查看 MSE、PCC、Program MSE、shift cosine
        - 查看 P1/P4/P6/P7/P10 的 source → predicted → target
        """
    )
else:
    st.dataframe(df.head(1000), use_container_width=True, hide_index=True)
