from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from core.paths import (
    CELLS_FILE,
    DONORS_FILE,
    DAG_V1_FILE,
    DAG_V2_FILE,
    EDGE_EVIDENCE_FILE,
    PATH_EVIDENCE_FILE,
    TRANSPORT_FILE,
    INTERVENTION_FILE,
    EXTERNAL_EVIDENCE_FILE,
    MANIFEST_FILE,
)


def _empty(columns=None):
    return pd.DataFrame(columns=columns or [])


@st.cache_data(show_spinner=False)
def load_manifest():
    if not MANIFEST_FILE.exists():
        return {}
    try:
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data(show_spinner=False)
def load_cells():
    if not CELLS_FILE.exists():
        return _empty(
            [
                "cell_id",
                "donor",
                "brain_region",
                "disease_stage",
                "stage_progression",
                "continuous_state",
                "umap1",
                "umap2",
                "P1",
                "P4",
                "P6",
                "P7",
                "P10",
            ]
        )
    return pd.read_parquet(CELLS_FILE)


@st.cache_data(show_spinner=False)
def load_donors():
    if not DONORS_FILE.exists():
        return _empty()
    return pd.read_parquet(DONORS_FILE)


@st.cache_data(show_spinner=False)
def load_dag_v1():
    if not DAG_V1_FILE.exists():
        return _empty(["source", "target"])
    return pd.read_csv(DAG_V1_FILE)


@st.cache_data(show_spinner=False)
def load_dag_v2():
    if not DAG_V2_FILE.exists():
        return _empty(["source", "target"])
    return pd.read_csv(DAG_V2_FILE)


@st.cache_data(show_spinner=False)
def load_edge_evidence():
    if not EDGE_EVIDENCE_FILE.exists():
        return _empty(["source", "target", "status"])
    return pd.read_csv(EDGE_EVIDENCE_FILE)


@st.cache_data(show_spinner=False)
def load_path_evidence():
    if not PATH_EVIDENCE_FILE.exists():
        return _empty()
    return pd.read_csv(PATH_EVIDENCE_FILE)


@st.cache_data(show_spinner=False)
def load_transport_metrics():
    if not TRANSPORT_FILE.exists():
        return _empty()
    return pd.read_parquet(TRANSPORT_FILE)


@st.cache_data(show_spinner=False)
def load_intervention_summary():
    if not INTERVENTION_FILE.exists():
        return _empty()
    return pd.read_parquet(INTERVENTION_FILE)


@st.cache_data(show_spinner=False)
def load_external_evidence():
    if not EXTERNAL_EVIDENCE_FILE.exists():
        return _empty()
    return pd.read_parquet(EXTERNAL_EVIDENCE_FILE)


def cache_ready():
    return CELLS_FILE.exists() and DAG_V2_FILE.exists()
