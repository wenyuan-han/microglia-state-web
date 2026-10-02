import pandas as pd
import streamlit as st

from core.loaders import load_dag_v1, load_dag_v2, load_edge_evidence, load_path_evidence
from core.plotting import dag_figure
from core.ui import page_header, missing_cache_notice


page_header(
    "Evidence-audited mechanism graph",
    "Mechanistic DAG Explorer",
    "切换发现图 DAG-v1 与证据校准后冻结的 DAG-v2，并逐边查看证据状态、上下游层级与排除原因。",
)

dag_v1 = load_dag_v1()
dag_v2 = load_dag_v2()
evidence = load_edge_evidence()
path_evidence = load_path_evidence()

if dag_v2.empty and dag_v1.empty:
    missing_cache_notice()
    st.stop()

version = st.radio(
    "Graph version",
    ["DAG-v2", "DAG-v1"],
    horizontal=True,
)

edges = dag_v2.copy() if version == "DAG-v2" else dag_v1.copy()

if edges.empty:
    st.warning(f"{version} edge table 为空。")
    st.stop()

edge_labels = [
    f"{row.source} → {row.target}"
    for row in edges.itertuples()
]

selected_label = st.selectbox(
    "Inspect edge",
    edge_labels,
)

selected_row = edges.iloc[edge_labels.index(selected_label)]
selected_edge = (str(selected_row["source"]), str(selected_row["target"]))

left, right = st.columns([1.55, 1])

with left:
    st.plotly_chart(
        dag_figure(edges, selected_edge=selected_edge),
        use_container_width=True,
    )

with right:
    st.markdown("### Edge evidence")
    st.markdown(f"**{selected_edge[0]} → {selected_edge[1]}**")

    match = evidence[
        (evidence["source"].astype(str) == selected_edge[0])
        &
        (evidence["target"].astype(str) == selected_edge[1])
    ] if not evidence.empty else pd.DataFrame()

    if not match.empty:
        row = match.iloc[0]

        if "status" in row:
            st.metric("Evidence status", str(row["status"]))

        fields = [
            ("edge_type", "Edge type"),
            ("evidence_weight", "Evidence annotation"),
            ("context_dependence", "Context dependence"),
            ("external_evidence", "External evidence"),
            ("reason", "Reason"),
        ]

        for field, label in fields:
            if field in row.index and pd.notna(row[field]):
                st.markdown(f"**{label}**")
                st.write(row[field])
    else:
        st.info("该边没有在 STEP33 edge evidence master 中找到匹配记录。")

    if version == "DAG-v1" and not evidence.empty:
        excluded = evidence[
            (evidence["source"].astype(str) == selected_edge[0])
            &
            (evidence["target"].astype(str) == selected_edge[1])
            &
            (evidence.get("include_v2_primary", True) == False)
        ]
        if not excluded.empty:
            st.warning("该 DAG-v1 边未进入 frozen DAG-v2 primary。")

st.markdown("### Current edge table")
display_cols = [
    c for c in
    ["source", "target", "edge_type", "status", "evidence_weight", "context_dependence"]
    if c in edges.columns
]
st.dataframe(
    edges[display_cols],
    use_container_width=True,
    hide_index=True,
)

if not path_evidence.empty:
    with st.expander("Path-level evidence audit"):
        st.dataframe(path_evidence, use_container_width=True, hide_index=True)
