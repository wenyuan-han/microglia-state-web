# ============================================================
# Build lightweight web-ready cache from the existing DAG-Agent
# SEA-AD / frozen DAG-v2 project.
#
# Run locally from anywhere:
#   python D:\PycharmProjects\DAG-Agent\webapp\scripts\build_web_data.py
#
# The scientific pipeline stays outside Streamlit. This script only
# copies/normalizes final outputs into webapp/data_cache.
# ============================================================

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(r"D:\PycharmProjects\DAG-Agent")
WEBAPP = PROJECT / "webapp"
CACHE = WEBAPP / "data_cache"
DAG_CACHE = CACHE / "dag"
TRANSPORT_CACHE = CACHE / "transport"
INTERVENTION_CACHE = CACHE / "intervention"
EXTERNAL_CACHE = CACHE / "external"

for p in [CACHE, DAG_CACHE, TRANSPORT_CACHE, INTERVENTION_CACHE, EXTERNAL_CACHE]:
    p.mkdir(parents=True, exist_ok=True)

MAX_WEB_CELLS = 30000
RANDOM_SEED = 20260921
PROGRAMS = ["P1", "P4", "P6", "P7", "P10"]


def log(msg):
    print(f"[web-cache] {msg}")


def first_existing(paths):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None


def canonical_stage(x):
    if pd.isna(x):
        return np.nan
    raw = str(x).strip()
    key = raw.lower().replace("-", " ").replace("_", " ").strip()
    return {
        "not ad": "Not AD", "notad": "Not AD", "low": "Low",
        "intermediate": "Intermediate", "high": "High",
    }.get(key, raw)


def find_obs_column(obs, candidates):
    for c in candidates:
        if c in obs.columns:
            return c
    lower_map = {str(c).lower(): c for c in obs.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def detect_h5ad():
    candidates = [
        PROJECT / "Glial_transition" / "data" / "outputs" / "SEAAD_Microglia_State.h5ad",
        PROJECT / "data" / "SEAAD" / "processed" / "SEAAD_Microglia_State.h5ad",
        PROJECT / "data" / "SEAAD" / "processed" / "SEAAD_Microglia_only.h5ad",
    ]
    found = first_existing(candidates)
    if found:
        return found
    hits = list(PROJECT.rglob("*SEAAD*Microglia*.h5ad"))
    return hits[0] if hits else None


def load_program_matrix(n_cells):
    candidates = [
        PROJECT / "data" / "SEAAD" / "processed" / "nmf" / "projection" / "NMF_K12_all_cells_W.npy",
        PROJECT / "data" / "SEAAD" / "processed" / "nmf" / "NMF_K12_all_cells_W.npy",
        PROJECT / "data" / "SEAAD" / "processed" / "nmf" / "NMF_K12_W.npy",
        PROJECT / "data" / "SEAAD" / "processed" / "NMF_K12_W.npy",
    ]
    for p in candidates:
        if not p.exists():
            continue
        try:
            W = np.load(p, mmap_mode="r")
        except Exception:
            continue
        if W.ndim == 2 and W.shape[0] == n_cells and W.shape[1] >= 12:
            return p, W, [0, 3, 5, 6, 9]
    return None, None, None


def stratified_sample_indices(meta, n_max, seed):
    n = len(meta)
    if n <= n_max:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    grouping_cols = [c for c in ["disease_stage", "brain_region"] if c in meta.columns]
    if not grouping_cols:
        return np.sort(rng.choice(n, size=n_max, replace=False))
    groups = list(meta.groupby(grouping_cols, dropna=False).groups.values())
    sizes = np.asarray([len(g) for g in groups], dtype=float)
    expected = sizes / sizes.sum() * n_max
    alloc = np.maximum(np.floor(expected).astype(int), 1)
    while alloc.sum() > n_max:
        candidates = np.where(alloc > 1)[0]
        if not len(candidates):
            break
        j = candidates[np.argmax(alloc[candidates] - expected[candidates])]
        alloc[j] -= 1
    while alloc.sum() < n_max:
        room = np.asarray([len(groups[i]) - alloc[i] for i in range(len(groups))])
        candidates = np.where(room > 0)[0]
        if not len(candidates):
            break
        residual = expected[candidates] - alloc[candidates]
        alloc[candidates[np.argmax(residual)]] += 1
    selected = []
    for g, k in zip(groups, alloc):
        arr = np.asarray(list(g), dtype=int)
        selected.extend(rng.choice(arr, size=min(int(k), len(arr)), replace=False).tolist())
    if len(selected) > n_max:
        selected = rng.choice(np.asarray(selected), size=n_max, replace=False).tolist()
    return np.sort(np.asarray(selected, dtype=int))


def merge_continuous_state(base):
    state_file = first_existing([
        PROJECT / "data" / "SEAAD" / "processed" / "nmf" / "continuous_state" / "continuous_disease_state.csv",
        PROJECT / "data" / "SEAAD" / "processed" / "nmf" / "continuous_state" / "21D_continuous_disease_state.csv",
    ])
    if state_file is None:
        return base, None
    state = pd.read_csv(state_file)
    donor_col = next((c for c in ["donor", "Donor ID", "donor_id"] if c in state.columns), None)
    state_col = next((c for c in ["continuous_state_scaled", "continuous_state"] if c in state.columns), None)
    if donor_col is None or state_col is None:
        return base, str(state_file)
    donor_map = (
        state[[donor_col, state_col]].dropna(subset=[donor_col]).drop_duplicates(donor_col)
        .set_index(donor_col)[state_col]
    )
    mapped = base["donor"].map(donor_map)
    if "continuous_state" not in base.columns:
        base["continuous_state"] = mapped
    else:
        base["continuous_state"] = pd.to_numeric(base["continuous_state"], errors="coerce").fillna(mapped)
    return base, str(state_file)


def build_cells_and_donors():
    h5ad = detect_h5ad()
    if h5ad is None:
        raise FileNotFoundError("Could not find SEA-AD Microglia h5ad. Edit detect_h5ad() candidates.")
    log(f"source h5ad: {h5ad}")
    try:
        import anndata as ad
    except ImportError as exc:
        raise RuntimeError("Please install anndata in the causflow environment.") from exc

    adata = ad.read_h5ad(h5ad, backed="r")
    obs = adata.obs.copy()
    n_cells = adata.n_obs
    donor_col = find_obs_column(obs, ["Donor ID", "donor_id", "donor"])
    region_col = find_obs_column(obs, ["Brain Region", "brain_region", "Region"])
    stage_col = find_obs_column(obs, ["disease_stage", "Overall AD neuropathological Change"])
    progression_col = find_obs_column(obs, ["stage_progression", "disease_progression"])
    state_col = find_obs_column(obs, ["continuous_state_scaled", "continuous_state", "state_z"])

    base = pd.DataFrame(index=np.arange(n_cells))
    base["cell_id"] = obs.index.astype(str).to_numpy()
    base["donor"] = obs[donor_col].astype(str).to_numpy() if donor_col else "Unknown"
    base["brain_region"] = obs[region_col].astype(str).to_numpy() if region_col else "Unknown"
    base["disease_stage"] = obs[stage_col].map(canonical_stage).to_numpy() if stage_col else "Unknown"
    if progression_col:
        base["stage_progression"] = pd.to_numeric(obs[progression_col], errors="coerce").to_numpy()
    else:
        base["stage_progression"] = base["disease_stage"].map({"Not AD": 0., "Low": 1/3, "Intermediate": 2/3, "High": 1.})
    base["continuous_state"] = pd.to_numeric(obs[state_col], errors="coerce").to_numpy() if state_col else np.nan
    base, state_source = merge_continuous_state(base)

    if "X_umap" in adata.obsm:
        umap = np.asarray(adata.obsm["X_umap"])
        base["umap1"], base["umap2"] = umap[:, 0], umap[:, 1]
    else:
        base["umap1"], base["umap2"] = np.nan, np.nan

    have_programs = all(p in obs.columns for p in PROGRAMS)
    program_source = "obs" if have_programs else "not found"
    if have_programs:
        for p in PROGRAMS:
            base[p] = pd.to_numeric(obs[p], errors="coerce").to_numpy()
    else:
        w_path, W, cols = load_program_matrix(n_cells)
        if W is not None:
            for p, col in zip(PROGRAMS, cols):
                base[p] = np.asarray(W[:, col], dtype=np.float32)
            program_source = str(w_path)
            log(f"Program matrix: {w_path}")
        else:
            log("WARNING: matching all-cell NMF W matrix not found.")

    sample_idx = stratified_sample_indices(base, MAX_WEB_CELLS, RANDOM_SEED)
    cells = base.iloc[sample_idx].reset_index(drop=True)
    cells.to_parquet(CACHE / "cells_web.parquet", index=False)

    numeric_cols = [c for c in ["continuous_state", "stage_progression"] + PROGRAMS if c in base.columns]
    donor_numeric = base.groupby("donor", dropna=False)[numeric_cols].mean(numeric_only=True).reset_index()
    donor_meta = base.groupby("donor", dropna=False).agg(
        brain_region=("brain_region", lambda x: x.mode().iloc[0] if len(x.mode()) else x.iloc[0]),
        disease_stage=("disease_stage", lambda x: x.mode().iloc[0] if len(x.mode()) else x.iloc[0]),
        n_cells=("cell_id", "size"),
    ).reset_index()
    donors = donor_meta.merge(donor_numeric, on="donor", how="left")
    donors.to_parquet(CACHE / "donors_web.parquet", index=False)

    try:
        adata.file.close()
    except Exception:
        pass
    log(f"cells_web.parquet: {len(cells):,} rows")
    log(f"donors_web.parquet: {len(donors):,} rows")
    return {
        "source_h5ad": str(h5ad), "source_n_cells": int(n_cells),
        "sampled_cells": int(len(cells)), "program_source": program_source,
        "continuous_state_source": state_source,
    }


def copy_csv(source, dest, optional=True, add_columns=None):
    source, dest = Path(source), Path(dest)
    if not source.exists():
        if optional:
            log(f"optional source missing: {source}")
            return False
        raise FileNotFoundError(source)
    df = pd.read_csv(source)
    for k, v in (add_columns or {}).items():
        if k not in df.columns:
            df.insert(0, k, v)
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, index=False)
    log(f"{dest.relative_to(CACHE)}: {len(df):,} rows")
    return True


def build_dag_cache():
    step33 = PROJECT / "data" / "SEAAD" / "processed" / "33_DAG_v2_evidence_integration"
    sources = {
        "dag_v1_edges.csv": step33 / "33_DAG_v1_edges.csv",
        "dag_v2_primary_edges.csv": step33 / "33_DAG_v2_primary_edges.csv",
        "dag_v2_core_intervention_edges.csv": step33 / "33_DAG_v2_core_intervention_edges.csv",
        "edge_evidence.csv": step33 / "33_edge_evidence_master.csv",
        "path_evidence.csv": step33 / "33_path_evidence_master.csv",
    }
    return {name: copy_csv(src, DAG_CACHE / name) for name, src in sources.items()}


def build_transport_cache():
    src = PROJECT / "data" / "SEAAD" / "processed" / "causflow_transition" / "34_DAG_v2_topology" / "evaluation"
    mapping = {
        "34B_pair_metrics.csv": "pair_metrics.csv",
        "34B_model_metric_means.csv": "model_metric_means.csv",
        "34B_gain_decomposition.csv": "gain_decomposition.csv",
        "34B_matched_statistics.csv": "matched_statistics.csv",
    }
    return {dst: copy_csv(src / source, TRANSPORT_CACHE / dst) for source, dst in mapping.items()}


def build_intervention_cache():
    src = PROJECT / "data" / "SEAAD" / "processed" / "causflow_transition" / "35_virtual_intervention"
    mapping = {
        "35A_pair_level_intervention_response.csv": "pair_response.csv",
        "35A_program_response_summary.csv": "program_response.csv",
        "35A_specificity_summary.csv": "specificity.csv",
        "35A_dose_response_summary.csv": "dose_response.csv",
    }
    return {dst: copy_csv(src / source, INTERVENTION_CACHE / dst) for source, dst in mapping.items()}


def build_external_cache():
    processed = PROJECT / "data" / "SEAAD" / "processed"
    candidates = [
        ("INPP5D", "GSE244209", processed / "32A_GSE244209_INPP5D_external_validation" / "32A_primary_INPP5D_summary.csv"),
        ("TREM2/SYK", "GSE158469", processed / "32B_GSE158469_TREM2_mechanism_validation" / "32B_aggregate_topology_summary.csv"),
        ("APOE/LXR", "GSE226076", processed / "32C_GSE226076_LXR_mechanism_validation" / "32C_aggregate_topology_summary.csv"),
        ("NLRP3", "GSE271192", processed / "32D_GSE271192_NLRP3_P7_validation" / "32D_aggregate_topology_summary.csv"),
    ]
    # Some STEP32 scripts changed summary filenames during development.
    fallback_patterns = {
        "INPP5D": ["32A_*summary.csv"],
        "TREM2/SYK": ["32B_*summary.csv"],
        "APOE/LXR": ["32C_*summary.csv"],
        "NLRP3": ["32D_*summary.csv"],
    }
    rows = []
    source_files = []
    for mechanism, dataset, path in candidates:
        chosen = path if path.exists() else None
        if chosen is None and path.parent.exists():
            for pattern in fallback_patterns[mechanism]:
                hits = sorted(path.parent.glob(pattern))
                if hits:
                    chosen = hits[0]
                    break
        if chosen is None:
            log(f"optional external summary missing for {mechanism}: {path.parent}")
            continue
        df = pd.read_csv(chosen)
        df.insert(0, "mechanism", mechanism)
        df.insert(1, "dataset", dataset)
        df.insert(2, "source_file", chosen.name)
        rows.append(df)
        source_files.append(str(chosen))
    if rows:
        out = pd.concat(rows, ignore_index=True, sort=False)
        out.to_csv(EXTERNAL_CACHE / "external_validation_summary.csv", index=False)
        log(f"external/external_validation_summary.csv: {len(out):,} rows")

    concord = processed / "causflow_transition" / "35_virtual_intervention" / "35B_external_concordance"
    mapping = {
        "35B_external_program_effects_standardized.csv": "external_program_effects.csv",
        "35B_virtual_program_effects_standardized.csv": "virtual_program_effects.csv",
        "35B_concordance_by_external_context.csv": "concordance_by_context.csv",
        "35B_concordance_aggregate.csv": "concordance_aggregate.csv",
        "35B_program_level_comparison.csv": "program_level_comparison.csv",
        "35B_specificity_concordance.csv": "specificity_concordance.csv",
    }
    status = {dst: copy_csv(concord / src, EXTERNAL_CACHE / dst) for src, dst in mapping.items()}
    status["independent_summary"] = bool(rows)
    status["independent_sources"] = source_files
    return status


def main():
    log(f"project: {PROJECT}")
    log(f"cache:   {CACHE}")
    metadata = build_cells_and_donors()
    dag = build_dag_cache()
    transport = build_transport_cache()
    intervention = build_intervention_cache()
    external = build_external_cache()
    manifest = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "final_pipeline": "DAG-v2 -> STEP34B transport -> STEP35A v2 intervention -> STEP35B external concordance",
        **metadata,
        "dag_files": dag,
        "transport_files": transport,
        "intervention_files": intervention,
        "external_files": external,
    }
    (CACHE / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log("DONE")
    print(f"\nNext:\n  cd {WEBAPP}\n  streamlit run app.py")


if __name__ == "__main__":
    main()
