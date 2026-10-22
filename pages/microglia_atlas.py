import numpy as np
import pandas as pd
import streamlit as st

from core.loaders import load_cells
from core.plotting import umap_figure, program_bar, PROGRAMS
from core.ui import page_header, missing_cache_notice, apply_figure_style, footer


page_header(
    "SEA-AD microglia",
    "Microglia Atlas",
    "Explore the microglia state landscape across disease stages, brain regions, and donors, with five selected molecular programs.",
)

df = load_cells()

if df.empty:
    missing_cache_notice()
    st.stop()

def options_with_all(series):
    vals = sorted(series.dropna().astype(str).unique().tolist())
    return ["All"] + vals

f1, f2, f3, f4 = st.columns([1, 1, 1, 1])

with f1:
    stage_options = options_with_all(df["disease_stage"]) if "disease_stage" in df.columns else ["All"]
    current = st.session_state.get("selected_stage", "All")
    if current not in stage_options:
        current = "All"
    stage = st.selectbox(
        "Disease stage",
        stage_options,
        index=stage_options.index(current),
        key="atlas_stage",
    )
    st.session_state.selected_stage = stage

with f2:
    region_options = options_with_all(df["brain_region"]) if "brain_region" in df.columns else ["All"]
    current = st.session_state.get("selected_region", "All")
    if current not in region_options:
        current = "All"
    region = st.selectbox(
        "Brain region",
        region_options,
        index=region_options.index(current),
        key="atlas_region",
    )
    st.session_state.selected_region = region

working = df.copy()

if stage != "All" and "disease_stage" in working.columns:
    working = working[working["disease_stage"].astype(str) == stage]

if region != "All" and "brain_region" in working.columns:
    working = working[working["brain_region"].astype(str) == region]

with f3:
    donor_options = options_with_all(working["donor"]) if "donor" in working.columns else ["All"]
    current = st.session_state.get("selected_donor", "All")
    if current not in donor_options:
        current = "All"
    donor = st.selectbox(
        "Donor",
        donor_options,
        index=donor_options.index(current),
        key="atlas_donor",
    )
    st.session_state.selected_donor = donor

if donor != "All" and "donor" in working.columns:
    working = working[working["donor"].astype(str) == donor]

color_candidates = [
    c
    for c in [
        "continuous_state",
        "disease_stage",
        "brain_region",
        "donor",
        "P1",
        "P4",
        "P6",
        "P7",
        "P10",
    ]
    if c in working.columns
]

with f4:
    default_color = "continuous_state" if "continuous_state" in color_candidates else color_candidates[0]
    color_by = st.selectbox(
        "Color by",
        color_candidates,
        index=color_candidates.index(default_color),
    )

st.caption(f"Current selection: {len(working):,} sampled microglia cells")

left, right = st.columns([1.65, 1])

with left:
    if len(working) == 0:
        st.warning("No cells match the selected filters.")
    else:
        st.plotly_chart(
            apply_figure_style(umap_figure(working, color_by)),
            width="stretch",
        )

with right:
    st.markdown("### Program profile")
    available_programs = [p for p in PROGRAMS if p in working.columns]

    if available_programs and len(working):
        values = {
            p: float(pd.to_numeric(working[p], errors="coerce").mean())
            for p in available_programs
        }
        st.plotly_chart(
            apply_figure_style(program_bar(values, title="Mean program activity")),
            width="stretch",
        )

        program = st.selectbox(
            "Inspect Program",
            available_programs,
            index=available_programs.index(
                st.session_state.selected_program
                if st.session_state.selected_program in available_programs
                else available_programs[0]
            ),
        )
        st.session_state.selected_program = program

        values_numeric = pd.to_numeric(working[program], errors="coerce")
        c1, c2, c3 = st.columns(3)
        c1.metric("Mean", f"{values_numeric.mean():.4f}")
        c2.metric("Median", f"{values_numeric.median():.4f}")
        c3.metric("95th pct", f"{values_numeric.quantile(.95):.4f}")
    else:
        st.info("Program activity is not available in the current atlas cache.")

st.markdown("### Filtered metadata")
cols = [
    c
    for c in [
        "cell_id",
        "donor",
        "brain_region",
        "disease_stage",
        "continuous_state",
        "P1",
        "P4",
        "P6",
        "P7",
        "P10",
    ]
    if c in working.columns
]
st.dataframe(
    working[cols].head(500),
    width="stretch",
    hide_index=True,
)

footer()
