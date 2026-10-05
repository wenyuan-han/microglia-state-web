from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = WEBAPP_ROOT / "data_cache"

# Existing atlas cache
CELLS_FILE = CACHE_DIR / "cells_web.parquet"
DONORS_FILE = CACHE_DIR / "donors_web.parquet"
PROGRAMS_FILE = CACHE_DIR / "programs_web.parquet"
MANIFEST_FILE = CACHE_DIR / "manifest.json"

# Final graph cache
DAG_DIR = CACHE_DIR / "dag"
DAG_V1_FILE = DAG_DIR / "dag_v1_edges.csv"
DAG_V2_FILE = DAG_DIR / "dag_v2_primary_edges.csv"
DAG_V2_CORE_FILE = DAG_DIR / "dag_v2_core_intervention_edges.csv"
EDGE_EVIDENCE_FILE = DAG_DIR / "edge_evidence.csv"
PATH_EVIDENCE_FILE = DAG_DIR / "path_evidence.csv"

# Final state-transport cache (STEP34B)
TRANSPORT_DIR = CACHE_DIR / "transport"
TRANSPORT_PAIR_FILE = TRANSPORT_DIR / "pair_metrics.csv"
TRANSPORT_MODEL_FILE = TRANSPORT_DIR / "model_metric_means.csv"
TRANSPORT_GAIN_FILE = TRANSPORT_DIR / "gain_decomposition.csv"
TRANSPORT_STATS_FILE = TRANSPORT_DIR / "matched_statistics.csv"

# Final virtual-intervention cache (STEP35A v2)
INTERVENTION_DIR = CACHE_DIR / "intervention"
INTERVENTION_PAIR_FILE = INTERVENTION_DIR / "pair_response.csv"
INTERVENTION_PROGRAM_FILE = INTERVENTION_DIR / "program_response.csv"
INTERVENTION_SPECIFICITY_FILE = INTERVENTION_DIR / "specificity.csv"
INTERVENTION_DOSE_FILE = INTERVENTION_DIR / "dose_response.csv"

# External perturbation validation / concordance (STEP32A-D + STEP35B)
EXTERNAL_DIR = CACHE_DIR / "external"
EXTERNAL_SUMMARY_FILE = EXTERNAL_DIR / "external_validation_summary.csv"
EXTERNAL_PROGRAM_FILE = EXTERNAL_DIR / "external_program_effects.csv"
VIRTUAL_PROGRAM_FILE = EXTERNAL_DIR / "virtual_program_effects.csv"
CONCORDANCE_CONTEXT_FILE = EXTERNAL_DIR / "concordance_by_context.csv"
CONCORDANCE_AGGREGATE_FILE = EXTERNAL_DIR / "concordance_aggregate.csv"
CONCORDANCE_PROGRAM_FILE = EXTERNAL_DIR / "program_level_comparison.csv"
CONCORDANCE_SPECIFICITY_FILE = EXTERNAL_DIR / "specificity_concordance.csv"

# Legacy flat-cache paths retained as fallback for older clones.
LEGACY_DAG_V1_FILE = CACHE_DIR / "dag_v1_edges.csv"
LEGACY_DAG_V2_FILE = CACHE_DIR / "dag_v2_edges.csv"
LEGACY_EDGE_EVIDENCE_FILE = CACHE_DIR / "edge_evidence.csv"
LEGACY_PATH_EVIDENCE_FILE = CACHE_DIR / "path_evidence.csv"
LEGACY_TRANSPORT_FILE = CACHE_DIR / "transport_metrics.parquet"
LEGACY_INTERVENTION_FILE = CACHE_DIR / "intervention_summary.parquet"
LEGACY_EXTERNAL_EVIDENCE_FILE = CACHE_DIR / "external_evidence.parquet"
