import pandas as pd
import streamlit as st

from core.loaders import (
    load_dag_v1,
    load_dag_v2,
    load_dag_v2_core,
    load_edge_evidence,
    load_path_evidence,
)
from core.plotting import dag_figure
from core.ui import page_header, missing_cache_notice

page_header(
    "Evidence-calibrated hierarchical graph",
    "Mechanistic DAG Explorer",
    "默认展示 STEP33 冻结的 DAG-v2 primary；可切换 discovery DAG-v1 与用于机制传递干预的 DAG-v2 core。图是 evidence-audited / mechanism-informed hypothesis graph，不等同于实验已证实的因果 DAG。",
)

dag_v1 = load_dag_v1()
dag_v2 = load_dag_v2()
dag_core = load_dag_v2_core()
evidence = load_edge_evidence()
path_evidence = load_path_evidence()

if dag_v2.empty and dag_v1.empty and dag_core.empty:
    missing_cache_notice()
    st.stop()

versions = {
    "DAG-v2 primary": dag_v2,
    "DAG-v2 core intervention": dag_core,
    "DAG-v1 discovery": dag_v1,
}
available = [k for k, v in versions.items() if not v.empty]
version = st.radio("Graph version", available, horizontal=True)
edges = versions[version].copy()

c1, c2, c3 = st.columns(3)
c1.metric("Edges", f"{len(edges):,}")
c2.metric("Source nodes", f"{edges['source'].astype(str).nunique():,}" if "source" in edges.columns else "-")
c3.metric("Target nodes", f"{edges['target'].astype(str).nunique():,}" if "target" in edges.columns else "-")

edge_labels = [f"{row.source} → {row.target}" for row in edges.itertuples()]
selected_label = st.selectbox("Inspect edge", edge_labels)
selected_row = edges.iloc[edge_labels.index(selected_label)]
selected_edge = (str(selected_row["source"]), str(selected_row["target"]))

left, right = st.columns([1.55, 1])
with left:
    st.plotly_chart(dag_figure(edges, selected_edge=selected_edge), use_container_width=True)

with right:
    st.markdown("### Edge evidence")
    st.markdown(f"**{selected_edge[0]} → {selected_edge[1]}**")
    match = evidence[
        (evidence["source"].astype(str) == selected_edge[0]) &
        (evidence["target"].astype(str) == selected_edge[1])
    ] if not evidence.empty else pd.DataFrame()
    if not match.empty:
        row = match.iloc[0]
        for field, label in [
            ("status", "Evidence status"),
            ("edge_type", "Edge type"),
            ("evidence_weight", "Evidence annotation"),
            ("context_dependence", "Context dependence"),
            ("external_evidence", "External evidence"),
            ("reason", "Reason"),
        ]:
            if field in row.index and pd.notna(row[field]):
                if field == "status":
                    st.metric(label, str(row[field]))
                else:
                    st.markdown(f"**{label}**")
                    st.write(row[field])
    else:
        st.info("该边在 STEP33 edge evidence master 中没有匹配记录。")

st.markdown("### Current edge table")
display_cols = [c for c in [
    "source", "target", "edge_type", "status", "evidence_weight",
    "context_dependence", "include_v2_primary", "include_core_intervention",
] if c in edges.columns]
st.dataframe(edges[display_cols] if display_cols else edges, use_container_width=True, hide_index=True)

if not path_evidence.empty:
    with st.expander("Path-level evidence calibration"):
        st.dataframe(path_evidence, use_container_width=True, hide_index=True)
