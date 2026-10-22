"""English-first presentation for the existing exploratory h5ad simulator.

The underlying functions and numerical algorithms in core.user_simulator are
unchanged by this page. The original input file is never modified.
"""
from pathlib import Path
import logging
import shutil
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st

from core.ui import page_header, section_header, apply_figure_style, footer
from core.user_simulator import inspect_h5ad, lookup_gene, run_simulation

MAX_UPLOAD_MB = 150
KEY_DATA = "upload_sim_input"
KEY_RESULT = "upload_sim_result"


def clear_loaded():
    info = st.session_state.pop(KEY_DATA, None)
    st.session_state.pop(KEY_RESULT, None)
    if info and info.get("tempdir"):
        shutil.rmtree(info["tempdir"], ignore_errors=True)


page_header(
    "INTERACTIVE WORKSPACE  /  EXPRESSION SANDBOX",
    "Data & Simulation",
    "Import an AnnData dataset, explore its structure, and run lightweight expression "
    "transformations with exportable results.",
)
st.markdown(
    '<div class="micro-note"><strong>Exploratory methods only.</strong> '
    'These operations do not use trained CausFlow weights or infer causal effects.</div>',
    unsafe_allow_html=True,
)

section_header("01", "Import a dataset", "Upload a .h5ad file (150 MB maximum).")
with st.container(border=True):
    uploaded = st.file_uploader("AnnData file (.h5ad)", type=["h5ad"], key="upload_sim_file")
    if uploaded is not None:
        size_mb = uploaded.size / (1024 * 1024)
        st.caption(f"{uploaded.name} · {size_mb:.1f} MB")
        if size_mb > MAX_UPLOAD_MB:
            st.error(f"File exceeds the {MAX_UPLOAD_MB} MB upload limit. Please create a smaller subset first.")
        if st.button("Load dataset", type="primary", disabled=size_mb > MAX_UPLOAD_MB):
            clear_loaded()
            tempdir = tempfile.mkdtemp(prefix="microglia_user_")
            path = Path(tempdir) / "uploaded.h5ad"
            try:
                uploaded.seek(0)
                with path.open("wb") as dest:
                    while True:
                        chunk = uploaded.read(1024 * 1024)
                        if not chunk:
                            break
                        dest.write(chunk)
                meta = inspect_h5ad(str(path))
                st.session_state[KEY_DATA] = {
                    "path": str(path), "tempdir": tempdir,
                    "filename": uploaded.name, "bytes": uploaded.size,
                    "meta": meta,
                }
                st.success("Dataset loaded.")
            except Exception as exc:
                shutil.rmtree(tempdir, ignore_errors=True)
                logging.exception("Could not load user h5ad")
                st.error(f"Could not read this .h5ad: {exc}")

loaded = st.session_state.get(KEY_DATA)
if not loaded:
    st.caption("Select a dataset and click **Load dataset** to continue.")
    footer()
    st.stop()

if uploaded is None or (uploaded.name, uploaded.size) != (loaded["filename"], loaded["bytes"]):
    st.info("The uploaded file has changed. Click **Load dataset** to continue.")
    st.stop()

meta = loaded["meta"]
a, b, c, d = st.columns(4, gap="small")
a.metric("Cells", f"{meta['n_obs']:,}")
b.metric("Genes", f"{meta['n_vars']:,}")
c.metric("HVG flags", "Available" if meta["has_hvg"] else "None")
d.metric("UMAP", "Available" if meta["has_umap"] else "None")

with st.expander("Dataset metadata", expanded=False):
    st.write("**Observation columns**", meta["obs_columns"])
    st.write("**Categorical variables**", list(meta["categorical_columns"]))
    st.write("**Layers**", meta["layers"] or "None")
    st.write("**Gene ID examples**", meta.get("var_name_examples", []))
    st.write("**Gene annotation columns**", meta.get("gene_annotation_columns", []) or "None")
    st.write("**adata.raw**", "Available" if meta.get("has_raw") else "Not available")
    st.caption("The simulator reads adata.X, not raw, layers, or embeddings.")

if not meta["unique_genes"]:
    st.error("Gene IDs in var_names are not unique. Run adata.var_names_make_unique() before uploading.")
    st.stop()

section_header("02", "Configure a simulation", "Choose a transformation and set its parameters.")
with st.container(border=True):
    mode_text = st.radio(
        "Simulation method",
        ["Stage mean shift", "Single-gene editing"],
        horizontal=True,
        help="Stage mean shift translates source expression by the target–source mean difference. "
             "Single-gene editing changes one expression column only.",
    )
    mode = "stage_mean_shift" if mode_text == "Stage mean shift" else "single_gene_edit"
    input_kind_text = st.radio(
        "Input expression (adata.X)",
        ["Log1p-normalized (non-negative)", "Raw counts (non-negative integers)"],
        horizontal=True,
        help="For raw counts, the simulator normalizes using full-gene library sizes and applies log1p.",
    )
    input_kind = "counts" if input_kind_text.startswith("Raw counts") else "log1p"

cat_cols = meta["categorical_columns"]
stage_col = None
source_stage = None
target_stage = None
focus_gene = None

with st.container(border=True):
    if mode == "stage_mean_shift":
        if not cat_cols:
            st.error("No suitable grouping variable (2–25 levels) was found in adata.obs.")
            st.stop()
        common_names = ["disease_stage", "Overall AD neuropathological Change", "AD stage", "stage"]
        preferred = next((x for x in common_names if x in cat_cols), next(iter(cat_cols)))
        stage_col = st.selectbox(
            "Disease-stage variable", list(cat_cols),
            index=list(cat_cols).index(preferred),
        )
        counts = cat_cols[stage_col]
        options = list(counts)
        x, y = st.columns(2, gap="medium")
        with x:
            source_stage = st.selectbox("Source group", options,
                                        format_func=lambda s: f"{s} ({counts[s]:,})")
        with y:
            target_options = [s for s in options if s != source_stage]
            target_stage = st.selectbox("Target reference", target_options,
                                        format_func=lambda s: f"{s} ({counts[s]:,})")
        strength = st.slider("Shift strength (α)", 0.0, 1.5, 1.0, 0.1)
        st.caption("X_sim = max(0, X_source + α × [mean_target − mean_source]) in log1p space.")
    else:
        if cat_cols:
            stage_choice = st.selectbox("Source cell group", ["All cells"] + list(cat_cols))
            if stage_choice != "All cells":
                stage_col = stage_choice
                counts = cat_cols[stage_col]
                source_stage = st.selectbox("Group", list(counts),
                                            format_func=lambda s: f"{s} ({counts[s]:,})")
        focus_gene = st.text_input(
            "Gene symbol or ID", value="TREM2",
            help="Matches var_names or supported gene annotations. For example, TREM2, APOE, or Ensembl IDs.",
        )
        if st.button("Check gene"):
            try:
                found = lookup_gene(loaded["path"], focus_gene)
                st.success(
                    f"Matched {found['gene_query']} to {found['var_name']} "
                    f"via {found['matched_column']} (column {found['var_index'] + 1})."
                )
            except ValueError as exc:
                st.warning(str(exc))
        strength = st.slider("Expression multiplier", 0.0, 3.0, 0.5, 0.1)
        st.caption("0× removes the selected gene's expression; 1× leaves it unchanged. No downstream genes are predicted.")

    filter_cols = [c for c in cat_cols if c != stage_col]
    filter_col = st.selectbox("Optional subgroup filter", ["No filter"] + filter_cols)
    filter_value = None
    if filter_col == "No filter":
        filter_col = None
    else:
        filter_value = st.selectbox(
            "Filter value", list(cat_cols[filter_col]),
            format_func=lambda s: f"{s} ({cat_cols[filter_col][s]:,})",
        )

with st.expander("Advanced settings", expanded=False):
    x, y, z = st.columns([1, 1, 1])
    with x:
        max_cells = st.slider("Max cells per group", 100, 1200, 800, 100)
    with y:
        max_genes = st.slider("Max genes", 100, 2000, 1000, 100)
    with z:
        seed = st.number_input("Random seed", min_value=0, max_value=999999, value=42, step=1)

if st.button("Run simulation", type="primary", width="stretch"):
    if mode == "single_gene_edit" and not (focus_gene or "").strip():
        st.error("Enter a gene symbol or gene ID.")
    else:
        try:
            with st.spinner("Computing the exploratory simulation…"):
                output_path = str(Path(loaded["tempdir"]) / "simulation_result.h5ad")
                result = run_simulation(
                    loaded["path"], output_path,
                    mode=mode, input_kind=input_kind, stage_col=stage_col,
                    source_stage=source_stage, target_stage=target_stage,
                    filter_col=filter_col, filter_value=filter_value,
                    strength=float(strength), focus_gene=(focus_gene or "").strip() or None,
                    max_cells=int(max_cells), max_genes=int(max_genes), seed=int(seed),
                )
            st.session_state[KEY_RESULT] = result
            st.success("Simulation complete. Results are available below.")
        except Exception as exc:
            logging.exception("Microglia simulation failed (mode=%s)", mode)
            st.session_state.pop(KEY_RESULT, None)
            st.error(f"Simulation failed: {exc}")
            st.caption("Detailed error information is available in the Streamlit app logs.")

result = st.session_state.get(KEY_RESULT)
if result:
    section_header("03", "Simulation results", "Compare original and transformed expression and export the output.")
    st.caption(result.description)
    if result.gene_resolution:
        st.info("Gene mapping: " + result.gene_resolution)
    a, b, c = st.columns(3)
    a.metric("Source cells", f"{result.n_source:,}")
    b.metric("Target reference", f"{result.n_target:,}" if result.n_target else "Not applicable")
    c.metric("Output genes", f"{result.n_genes:,}")

    left, right = st.columns([1.15, 1], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("#### Expression-space PCA")
            fig = px.scatter(
                result.embedding, x="PC1", y="PC2", color="Group",
                opacity=0.72,
                color_discrete_sequence=["#4966E9", "#078C91", "#E69C42"],
            )
            fig.update_traces(marker={"size": 5})
            fig.update_layout(margin=dict(l=5, r=5, t=10, b=12))
            st.plotly_chart(apply_figure_style(fig, height=355), width="stretch")
            st.caption("PCA is computed on the current sample, not on the original UMAP.")
    with right:
        with st.container(border=True):
            st.markdown("#### Top expression changes")
            chart = result.gene_summary.head(15).sort_values("abs_change")
            fig = px.bar(
                chart, x="simulated_minus_source", y="gene", orientation="h",
                labels={"simulated_minus_source": "Mean change (log1p)", "gene": ""},
            )
            fig.update_traces(marker_color="#4966E9")
            fig.update_layout(margin=dict(l=5, r=5, t=10, b=12))
            st.plotly_chart(apply_figure_style(fig, height=355), width="stretch")

    with st.expander("Gene-level results", expanded=True):
        st.dataframe(result.gene_summary.head(200), width="stretch", hide_index=True)

    a, b = st.columns(2)
    with a:
        st.download_button(
            "Download simulated h5ad", data=Path(result.output_path).read_bytes(),
            file_name="microglia_simulated.h5ad", mime="application/octet-stream",
            width="stretch",
        )
    with b:
        st.download_button(
            "Download gene summary CSV",
            data=result.gene_summary.to_csv(index=False).encode("utf-8-sig"),
            file_name="simulation_gene_summary.csv", mime="text/csv",
            width="stretch",
        )
    st.caption(
        "The exported X matrix contains simulated non-negative log1p values; "
        "layers['original_log1p'] preserves sampled source expression."
    )

st.divider()
if st.button("Clear current dataset and results"):
    clear_loaded()
    st.rerun()

footer()
