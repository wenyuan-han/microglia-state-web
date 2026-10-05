from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

from core.paths import *


def _empty(columns=None):
    return pd.DataFrame(columns=columns or [])


def _first_existing(paths: Iterable[Path]):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None


def _read_csv(paths, columns=None):
    path = _first_existing(paths)
    if path is None:
        return _empty(columns)
    try:
        return pd.read_csv(path)
    except Exception:
        return _empty(columns)


def _read_parquet(paths, columns=None):
    path = _first_existing(paths)
    if path is None:
        return _empty(columns)
    try:
        return pd.read_parquet(path)
    except Exception:
        return _empty(columns)


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
    return _read_parquet(
        [CELLS_FILE],
        [
            "cell_id", "donor", "brain_region", "disease_stage",
            "stage_progression", "continuous_state", "umap1", "umap2",
            "P1", "P4", "P6", "P7", "P10",
        ],
    )


@st.cache_data(show_spinner=False)
def load_donors():
    return _read_parquet([DONORS_FILE])


@st.cache_data(show_spinner=False)
def load_dag_v1():
    return _read_csv([DAG_V1_FILE, LEGACY_DAG_V1_FILE], ["source", "target"])


@st.cache_data(show_spinner=False)
def load_dag_v2():
    return _read_csv([DAG_V2_FILE, LEGACY_DAG_V2_FILE], ["source", "target"])


@st.cache_data(show_spinner=False)
def load_dag_v2_core():
    return _read_csv([DAG_V2_CORE_FILE], ["source", "target"])


@st.cache_data(show_spinner=False)
def load_edge_evidence():
    return _read_csv([EDGE_EVIDENCE_FILE, LEGACY_EDGE_EVIDENCE_FILE], ["source", "target", "status"])


@st.cache_data(show_spinner=False)
def load_path_evidence():
    return _read_csv([PATH_EVIDENCE_FILE, LEGACY_PATH_EVIDENCE_FILE])


@st.cache_data(show_spinner=False)
def load_transport_pair_metrics():
    df = _read_csv([TRANSPORT_PAIR_FILE])
    if df.empty and LEGACY_TRANSPORT_FILE.exists():
        return _read_parquet([LEGACY_TRANSPORT_FILE])
    return df


@st.cache_data(show_spinner=False)
def load_transport_model_metrics():
    return _read_csv([TRANSPORT_MODEL_FILE])


@st.cache_data(show_spinner=False)
def load_transport_gain_decomposition():
    return _read_csv([TRANSPORT_GAIN_FILE])


@st.cache_data(show_spinner=False)
def load_transport_statistics():
    return _read_csv([TRANSPORT_STATS_FILE])


# Backward-compatible alias used by older code.
@st.cache_data(show_spinner=False)
def load_transport_metrics():
    return load_transport_pair_metrics()


@st.cache_data(show_spinner=False)
def load_intervention_pair_response():
    return _read_csv([INTERVENTION_PAIR_FILE])


@st.cache_data(show_spinner=False)
def load_intervention_program_response():
    return _read_csv([INTERVENTION_PROGRAM_FILE])


@st.cache_data(show_spinner=False)
def load_intervention_specificity():
    df = _read_csv([INTERVENTION_SPECIFICITY_FILE])
    if df.empty and LEGACY_INTERVENTION_FILE.exists():
        return _read_parquet([LEGACY_INTERVENTION_FILE])
    return df


@st.cache_data(show_spinner=False)
def load_intervention_dose_response():
    return _read_csv([INTERVENTION_DOSE_FILE])


@st.cache_data(show_spinner=False)
def load_intervention_summary():
    return load_intervention_specificity()


@st.cache_data(show_spinner=False)
def load_external_validation_summary():
    df = _read_csv([EXTERNAL_SUMMARY_FILE])
    if df.empty and LEGACY_EXTERNAL_EVIDENCE_FILE.exists():
        return _read_parquet([LEGACY_EXTERNAL_EVIDENCE_FILE])
    return df


@st.cache_data(show_spinner=False)
def load_external_program_effects():
    return _read_csv([EXTERNAL_PROGRAM_FILE])


@st.cache_data(show_spinner=False)
def load_virtual_program_effects():
    return _read_csv([VIRTUAL_PROGRAM_FILE])


@st.cache_data(show_spinner=False)
def load_concordance_context():
    return _read_csv([CONCORDANCE_CONTEXT_FILE])


@st.cache_data(show_spinner=False)
def load_concordance_aggregate():
    return _read_csv([CONCORDANCE_AGGREGATE_FILE])


@st.cache_data(show_spinner=False)
def load_concordance_program():
    return _read_csv([CONCORDANCE_PROGRAM_FILE])


@st.cache_data(show_spinner=False)
def load_concordance_specificity():
    return _read_csv([CONCORDANCE_SPECIFICITY_FILE])


@st.cache_data(show_spinner=False)
def load_external_evidence():
    return load_external_validation_summary()


def cache_ready():
    return CELLS_FILE.exists() and _first_existing([DAG_V2_FILE, LEGACY_DAG_V2_FILE]) is not None
