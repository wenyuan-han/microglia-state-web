"""Landing page for the Microglia research workspace."""
import streamlit as st

from core.loaders import load_cells, load_donors, load_dag_v2, load_manifest
from core.plotting import stage_state_box
from core.ui import (
    page_header, missing_cache_notice, section_header,
    apply_figure_style, tile, footer,
)

page_header(
    "SEA-AD  /  RESEARCH WORKSPACE",
    "Explore microglia states and mechanisms",
    "Interactive atlas, evidence-calibrated mechanism graphs, distribution transport, "
    "and exploratory expression simulation in one workspace.",
)

cells = load_cells()
donors = load_donors()
dag = load_dag_v2()
manifest = load_manifest()

if cells.empty:
    missing_cache_notice()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Atlas cells", f"{len(cells):,}")
c2.metric("Donors", f"{donors['donor'].nunique():,}" if "donor" in donors.columns else f"{len(donors):,}")
c3.metric("Selected programs", "5")
c4.metric("DAG-v2 edges", f"{len(dag):,}")

section_header("01", "Research workflow")
st.markdown(
    '<div class="micro-workflow">'
    '<strong>SEA-AD</strong> &nbsp;→&nbsp; Molecular programs &nbsp;→&nbsp; '
    'Continuous state &nbsp;→&nbsp; Evidence-audited DAG &nbsp;→&nbsp; '
    'Distribution transport &nbsp;→&nbsp; Virtual intervention &nbsp;→&nbsp; External evidence'
    '</div>',
    unsafe_allow_html=True,
)

section_header("02", "Pathology-associated state landscape")
left, right = st.columns([1.45, 1], gap="large")

with left:
    with st.container(border=True):
        if not donors.empty and {"disease_stage", "continuous_state"}.issubset(donors.columns):
            st.plotly_chart(apply_figure_style(stage_state_box(donors)), width="stretch")
        elif not cells.empty and {"disease_stage", "continuous_state"}.issubset(cells.columns):
            st.plotly_chart(apply_figure_style(stage_state_box(cells)), width="stretch")
        else:
            st.info("Continuous-state summary is not available in the current cache.")

with right:
    with st.container(border=True):
        st.markdown("#### Biological focus")
        st.markdown("**Molecular programs**")
        st.write("P1 · P4 · P6 · P7 · P10")
        st.markdown("**Mechanism nodes**")
        st.write("NLRP3 · TFEB · TREM2/SYK · APOE/LXR")
        st.divider()
        st.caption(
            "State paths are model-implied relationships across cross-sectional disease "
            "groups—not observations of the same cells over time."
        )
        if manifest:
            with st.expander("Dataset provenance"):
                st.write("**Cache built:**", manifest.get("built_at", "Unknown"))
                st.write("**Web-sampled cells:**", manifest.get("sampled_cells", "Unknown"))

section_header("03", "Explore the workspace")
a, b, c = st.columns(3, gap="medium")
with a:
    tile("EXPLORE", "Microglia Atlas", "Filter disease stage, brain region, and donor; examine UMAP and molecular program activity.")
with b:
    tile("MECHANISMS", "Mechanistic DAG", "Inspect frozen graph versions, individual edges, and their supporting evidence.")
with c:
    tile("SIMULATE", "Data & Simulation", "Upload an h5ad file for bounded expression edits or cross-group mean shifts.")

footer()
