import pandas as pd
import plotly.express as px
import streamlit as st

from core.loaders import (
    load_intervention_program_response,
    load_intervention_specificity,
    load_intervention_dose_response,
    load_intervention_pair_response,
)
from core.ui import page_header, apply_figure_style, footer

page_header(
    "Frozen DAG-v2 mechanism-transmission audit",
    "Virtual Intervention",
    "Adjust mechanism-to-program transmission strength in the frozen DAG-v2 model. α=1 is the reference; lower values suppress transmission and higher values amplify it.",
)

program_df = load_intervention_program_response()
spec_df = load_intervention_specificity()
dose_df = load_intervention_dose_response()
pair_df = load_intervention_pair_response()

if program_df.empty:
    st.info("Intervention results are not available. Build the local cache with `python webapp/scripts/build_web_data.py`.")
    st.stop()

mechanism_col = "mechanism_short" if "mechanism_short" in program_df.columns else "mechanism"
mechanisms = program_df[mechanism_col].dropna().astype(str).unique().tolist()
mechanism = st.selectbox("Mechanism", mechanisms)
sub = program_df[program_df[mechanism_col].astype(str) == mechanism].copy()

alpha_values = sorted(pd.to_numeric(sub["alpha"], errors="coerce").dropna().unique().tolist())
default_alpha = 1.0 if 1.0 in alpha_values else alpha_values[0]
alpha = st.select_slider("Transmission strength α", options=alpha_values, value=default_alpha)
view = sub[pd.to_numeric(sub["alpha"], errors="coerce") == float(alpha)].copy()

st.caption("α=1.0 is the factual frozen model; ΔProgram is measured relative to α=1.0.")

if not view.empty and {"program", "mean_signed_delta_program"}.issubset(view.columns):
    view["Program class"] = view.get("is_descendant", False).map({True: "Frozen descendant", False: "Non-descendant"}) if "is_descendant" in view.columns else "Program"
    fig = px.bar(
        view,
        x="program",
        y="mean_signed_delta_program",
        color="Program class",
        text_auto=".4f",
        title=f"{mechanism}: Program response at α={alpha}",
    )
    fig.add_hline(y=0, line_width=1)
    fig.update_layout(height=440, xaxis_title="Program", yaxis_title="Δ Program vs factual α=1")
    st.plotly_chart(apply_figure_style(fig), width="stretch")

    c1, c2, c3 = st.columns(3)
    if "mean_abs_delta_program" in view.columns:
        c1.metric("Total |ΔProgram|", f"{view['mean_abs_delta_program'].sum():.4f}")
    desc = view[view["is_descendant"] == True] if "is_descendant" in view.columns else pd.DataFrame()
    nondesc = view[view["is_descendant"] == False] if "is_descendant" in view.columns else pd.DataFrame()
    if not desc.empty and "mean_abs_delta_program" in view.columns:
        c2.metric("Descendant |Δ|", f"{desc['mean_abs_delta_program'].sum():.4f}")
    if not nondesc.empty and "mean_abs_delta_program" in view.columns:
        c3.metric("Non-descendant |Δ|", f"{nondesc['mean_abs_delta_program'].sum():.4f}")

if not spec_df.empty:
    spec_mech_col = "mechanism_short" if "mechanism_short" in spec_df.columns else "mechanism"
    s = spec_df[(spec_df[spec_mech_col].astype(str) == mechanism) & (pd.to_numeric(spec_df["alpha"], errors="coerce") == float(alpha))]
    if not s.empty:
        row = s.iloc[0]
        st.markdown("### Path specificity")
        cols = st.columns(4)
        for col, field, label in [
            (cols[0], "mean_pair_specificity", "Mean specificity"),
            (cols[1], "specificity_excess", "Specificity excess"),
            (cols[2], "descendant_to_nondescendant_ratio", "Desc./non-desc. ratio"),
            (cols[3], "fraction_pairs_specificity_excess_gt_0", "Pairs excess > 0"),
        ]:
            if field in row.index and pd.notna(row[field]):
                col.metric(label, f"{float(row[field]):.3f}")
        with st.expander("Specificity statistics"):
            st.dataframe(s, width="stretch", hide_index=True)

st.markdown("### Dose / transmission response")
mech_program = program_df[program_df[mechanism_col].astype(str) == mechanism].copy()
if {"alpha", "program", "mean_abs_delta_program"}.issubset(mech_program.columns):
    fig = px.line(mech_program, x="alpha", y="mean_abs_delta_program", color="program", markers=True)
    fig.update_layout(height=420, yaxis_title="Mean |ΔProgram|", xaxis_title="Transmission α")
    st.plotly_chart(apply_figure_style(fig), width="stretch")

if not dose_df.empty:
    with st.expander("Dose-response summary"):
        dm = "mechanism_short" if "mechanism_short" in dose_df.columns else "mechanism"
        st.dataframe(dose_df[dose_df[dm].astype(str) == mechanism], width="stretch", hide_index=True)

with st.expander("Pair-level intervention responses"):
    if not pair_df.empty:
        pcol = "mechanism_short" if "mechanism_short" in pair_df.columns else "mechanism"
        q = pair_df[pair_df[pcol].astype(str) == mechanism] if pcol in pair_df.columns else pair_df
        st.dataframe(q.head(1500), width="stretch", hide_index=True)

st.caption("This is a model-based mechanism-transmission sensitivity analysis, not an experimentally identified do-effect.")

footer()
