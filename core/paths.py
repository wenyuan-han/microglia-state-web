from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = WEBAPP_ROOT / "data_cache"

CELLS_FILE = CACHE_DIR / "cells_web.parquet"
DONORS_FILE = CACHE_DIR / "donors_web.parquet"
PROGRAMS_FILE = CACHE_DIR / "programs_web.parquet"

DAG_V1_FILE = CACHE_DIR / "dag_v1_edges.csv"
DAG_V2_FILE = CACHE_DIR / "dag_v2_edges.csv"
EDGE_EVIDENCE_FILE = CACHE_DIR / "edge_evidence.csv"
PATH_EVIDENCE_FILE = CACHE_DIR / "path_evidence.csv"

TRANSPORT_FILE = CACHE_DIR / "transport_metrics.parquet"
INTERVENTION_FILE = CACHE_DIR / "intervention_summary.parquet"
EXTERNAL_EVIDENCE_FILE = CACHE_DIR / "external_evidence.parquet"

MANIFEST_FILE = CACHE_DIR / "manifest.json"
