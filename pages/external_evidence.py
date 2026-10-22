import pandas as pd
import plotly.express as px
import streamlit as st

from core.loaders import (
    load_external_validation_summary,
    load_external_program_effects,
    load_virtual_program_effects,
    load_concordance_context,
    load_concordance_aggregate,
    load_concordance_program,
    load_concordance_specificity,
)
from core.ui import page_header, apply_figure_style, footer

page_header(
    "Independent perturbation evidence",
    "External Evidence",
    "Review independent perturbation evidence and compare five-program response patterns between virtual DAG-v2 interventions and external experiments.",
)

summary = load_external_validation_summary()
aggregate = load_concordance_aggregate()
program = load_concordance_program()
context = load_concordance_context()
specificity = load_concordance_specificity()
external_long = load_external_program_effects()
virtual_long = load_virtual_program_effects()

if summary.empty and aggregate.empty:
    st.info("External evidence is not available. Build the local cache with `python webapp/scripts/build_web_data.py`.")
    st.stop()

if not aggregate.empty:
    st.markdown("### Virtual ↔ experimental concordance")
    mechanisms = aggregate["mechanism"].dropna().astype(str).unique().tolist() if "mechanism" in aggregate.columns else []
    mechanism = st.selectbox("Mechanism", mechanisms) if mechanisms else None
    a = aggregate[aggregate["mechanism"].astype(str) == mechanism].copy() if mechanism else aggregate.copy()

    profile_options = a["virtual_profile"].dropna().astype(str).unique().tolist() if "virtual_profile" in a.columns else []
    profile = st.selectbox("Virtual profile", profile_options) if profile_options else None
    av = a[a["virtual_profile"].astype(str) == profile] if profile else a
    if not av.empty:
        row = av.iloc[0]
        cols = st.columns(4)
        for col, field, label in [
            (cols[0], "magnitude_spearman", "Magnitude Spearman"),
            (cols[1], "magnitude_cosine_l1", "Magnitude cosine"),
            (cols[2], "virtual_specificity", "Virtual specificity"),
            (cols[3], "external_specificity_recomputed_DAGv2", "External specificity"),
        ]:
            if field in row.index and pd.notna(row[field]):
                col.metric(label, f"{float(row[field]):.3f}")

    if mechanism and not program.empty:
        p = program[program["mechanism"].astype(str) == mechanism].copy()
        if profile and "virtual_profile" in p.columns:
            p = p[p["virtual_profile"].astype(str) == profile]
        contrasts = p["external_contrast"].dropna().astype(str).unique().tolist() if "external_contrast" in p.columns else []
        contrast = st.selectbox("External contrast", contrasts) if contrasts else None
        if contrast:
            p = p[p["external_contrast"].astype(str) == contrast]
        if {"virtual_abs_l1_fraction", "external_abs_l1_fraction", "program"}.issubset(p.columns):
            long = p.melt(
                id_vars=["program"],
                value_vars=["virtual_abs_l1_fraction", "external_abs_l1_fraction"],
                var_name="source",
                value_name="relative_response",
            )
            long["source"] = long["source"].map({
                "virtual_abs_l1_fraction": "Virtual",
                "external_abs_l1_fraction": "Experimental",
            })
            fig = px.bar(long, x="program", y="relative_response", color="source", barmode="group", title="Five-Program response structure")
            fig.update_layout(height=440, yaxis_title="L1-normalized |ΔProgram|")
            st.plotly_chart(apply_figure_style(fig), width="stretch")

            scatter = px.scatter(
                p, x="external_abs_l1_fraction", y="virtual_abs_l1_fraction", text="program",
                title="Virtual vs experimental Program response",
            )
            scatter.update_traces(textposition="top center", marker={"size": 11})
            scatter.update_layout(height=420, xaxis_title="Experimental relative |ΔProgram|", yaxis_title="Virtual relative |ΔProgram|")
            st.plotly_chart(apply_figure_style(scatter), width="stretch")

st.markdown("### Independent validation datasets")
if summary.empty:
    st.caption("Independent STEP32 summary cache not available.")
else:
    datasets = summary["dataset"].dropna().astype(str).unique().tolist() if "dataset" in summary.columns else []
    if datasets:
        tabs = st.tabs(datasets)
        for tab, ds in zip(tabs, datasets):
            with tab:
                st.dataframe(summary[summary["dataset"].astype(str) == ds], width="stretch", hide_index=True)
    else:
        st.dataframe(summary, width="stretch", hide_index=True)

with st.expander("Context-level concordance"):
    if not context.empty:
        st.dataframe(context, width="stretch", hide_index=True)

with st.expander("Specificity concordance"):
    if not specificity.empty:
        st.dataframe(specificity, width="stretch", hide_index=True)

with st.expander("Standardized external / virtual Program effects"):
    c1, c2 = st.columns(2)
    with c1:
        st.caption("External")
        if not external_long.empty:
            st.dataframe(external_long, width="stretch", hide_index=True)
    with c2:
        st.caption("Virtual")
        if not virtual_long.empty:
            st.dataframe(virtual_long, width="stretch", hide_index=True)

st.caption("GSE289721 is treated as perturbation calibration/internal interventional benchmarking in the pipeline; STEP32 datasets provide the independent external evidence layer.")

footer()
