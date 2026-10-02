# ============================================================
# Build lightweight web-ready cache from the existing DAG-Agent
# SEA-AD / DAG-v2 project.
#
# Run from anywhere:
#
#   python D:\PycharmProjects\DAG-Agent\webapp\scripts\build_web_data.py
#
# This script NEVER modifies source analysis files.
# ============================================================

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(r"D:\PycharmProjects\DAG-Agent")
WEBAPP = PROJECT / "webapp"
CACHE = WEBAPP / "data_cache"
CACHE.mkdir(parents=True, exist_ok=True)

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


def detect_h5ad():
    candidates = [
        PROJECT / "Glial_transition" / "data" / "outputs" / "SEAAD_Microglia_State.h5ad",
        PROJECT / "data" / "SEAAD" / "processed" / "SEAAD_Microglia_State.h5ad",
        PROJECT / "data" / "SEAAD" / "processed" / "SEAAD_Microglia_only.h5ad",
    ]

    found = first_existing(candidates)
    if found is not None:
        return found

    hits = list(PROJECT.rglob("*SEAAD*Microglia*.h5ad"))
    return hits[0] if hits else None


def canonical_stage(x):
    if pd.isna(x):
        return np.nan

    raw = str(x).strip()
    key = raw.lower().replace("-", " ").replace("_", " ").strip()

    mapping = {
        "not ad": "Not AD",
        "notad": "Not AD",
        "low": "Low",
        "intermediate": "Intermediate",
        "high": "High",
    }
    return mapping.get(key, raw)


def find_obs_column(obs, candidates):
    for c in candidates:
        if c in obs.columns:
            return c
    lower_map = {str(c).lower(): c for c in obs.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    return None


def load_program_matrix(n_cells):
    # First preference: a W array matching the current h5ad cell count.
    candidates = [
        PROJECT / "data" / "SEAAD" / "processed" / "nmf" / "NMF_K12_W.npy",
        PROJECT / "data" / "SEAAD" / "processed" / "nmf" / "NMF_W.npy",
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
            # Frozen known NMF rows/columns: P1,P4,P6,P7,P10 correspond
            # to K12 columns 0,3,5,6,9.
            cols = [0, 3, 5, 6, 9]
            return p, W, cols

    return None, None, None


def stratified_sample_indices(meta, n_max, seed):
    n = len(meta)
    if n <= n_max:
        return np.arange(n)

    rng = np.random.default_rng(seed)

    grouping_cols = [
        c for c in ["disease_stage", "brain_region"]
        if c in meta.columns
    ]

    if not grouping_cols:
        return np.sort(rng.choice(n, size=n_max, replace=False))

    groups = list(meta.groupby(grouping_cols, dropna=False).groups.values())
    sizes = np.asarray([len(g) for g in groups], dtype=float)
    expected = sizes / sizes.sum() * n_max

    alloc = np.floor(expected).astype(int)
    alloc = np.maximum(alloc, 1)

    while alloc.sum() > n_max:
        candidates = np.where(alloc > 1)[0]
        j = candidates[np.argmax(alloc[candidates] - expected[candidates])]
        alloc[j] -= 1

    while alloc.sum() < n_max:
        room = np.asarray([len(groups[i]) - alloc[i] for i in range(len(groups))])
        candidates = np.where(room > 0)[0]
        if len(candidates) == 0:
            break
        residual = expected[candidates] - alloc[candidates]
        j = candidates[np.argmax(residual)]
        alloc[j] += 1

    selected = []
    for g, k in zip(groups, alloc):
        arr = np.asarray(list(g), dtype=int)
        k = min(int(k), len(arr))
        selected.extend(rng.choice(arr, size=k, replace=False).tolist())

    if len(selected) > n_max:
        selected = rng.choice(np.asarray(selected), size=n_max, replace=False).tolist()

    return np.sort(np.asarray(selected, dtype=int))


def build_cells_and_donors():
    h5ad = detect_h5ad()
    if h5ad is None:
        raise FileNotFoundError(
            "Could not find SEA-AD Microglia h5ad automatically. "
            "Edit detect_h5ad() candidates in build_web_data.py."
        )

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
    stage_col = find_obs_column(
        obs,
        [
            "disease_stage",
            "Overall AD neuropathological Change",
            "overall_ad_neuropathological_change",
        ],
    )
    progression_col = find_obs_column(obs, ["stage_progression", "disease_progression"])
    state_col = find_obs_column(
        obs,
        [
            "continuous_state",
            "state",
            "molecular_state",
            "disease_state",
            "state_z",
        ],
    )

    base = pd.DataFrame(index=np.arange(n_cells))
    base["cell_id"] = obs.index.astype(str).to_numpy()

    if donor_col is not None:
        base["donor"] = obs[donor_col].astype(str).to_numpy()
    else:
        base["donor"] = "Unknown"

    if region_col is not None:
        base["brain_region"] = obs[region_col].astype(str).to_numpy()
    else:
        base["brain_region"] = "Unknown"

    if stage_col is not None:
        base["disease_stage"] = obs[stage_col].map(canonical_stage).to_numpy()
    else:
        base["disease_stage"] = "Unknown"

    if progression_col is not None:
        base["stage_progression"] = pd.to_numeric(obs[progression_col], errors="coerce").to_numpy()
    else:
        stage_map = {"Not AD": 0.0, "Low": 1/3, "Intermediate": 2/3, "High": 1.0}
        base["stage_progression"] = base["disease_stage"].map(stage_map)

    if state_col is not None:
        base["continuous_state"] = pd.to_numeric(obs[state_col], errors="coerce").to_numpy()
    else:
        base["continuous_state"] = np.nan

    # UMAP.
    if "X_umap" in adata.obsm:
        umap = np.asarray(adata.obsm["X_umap"])
        if umap.shape[1] >= 2:
            base["umap1"] = umap[:, 0]
            base["umap2"] = umap[:, 1]
    else:
        base["umap1"] = np.nan
        base["umap2"] = np.nan

    # Prefer preexisting Program columns if present.
    have_programs = True
    for p in PROGRAMS:
        if p in obs.columns:
            base[p] = pd.to_numeric(obs[p], errors="coerce").to_numpy()
        else:
            have_programs = False
            break

    program_source = "obs"

    if not have_programs:
        for p in PROGRAMS:
            if p in base.columns:
                base.drop(columns=[p], inplace=True)

        w_path, W, cols = load_program_matrix(n_cells)
        if W is not None:
            for p, col in zip(PROGRAMS, cols):
                base[p] = np.asarray(W[:, col], dtype=np.float32)
            program_source = str(w_path)
            log(f"Program matrix: {w_path}")
        else:
            program_source = "not found"
            log("WARNING: matching NMF W matrix not found; Program columns will be absent.")

    sample_idx = stratified_sample_indices(
        base,
        n_max=MAX_WEB_CELLS,
        seed=RANDOM_SEED,
    )

    cells = base.iloc[sample_idx].reset_index(drop=True)
    cells.to_parquet(CACHE / "cells_web.parquet", index=False)
    log(f"cells_web.parquet: {len(cells):,} rows")

    # Donor table from full obs-level metadata / Program means.
    numeric_cols = [c for c in ["continuous_state", "stage_progression"] + PROGRAMS if c in base.columns]
    donor_numeric = base.groupby("donor", dropna=False)[numeric_cols].mean(numeric_only=True).reset_index()

    donor_meta = (
        base.groupby("donor", dropna=False)
        .agg(
            brain_region=("brain_region", lambda x: x.mode().iloc[0] if len(x.mode()) else x.iloc[0]),
            disease_stage=("disease_stage", lambda x: x.mode().iloc[0] if len(x.mode()) else x.iloc[0]),
            n_cells=("cell_id", "size"),
        )
        .reset_index()
    )

    donors = donor_meta.merge(donor_numeric, on="donor", how="left")
    donors.to_parquet(CACHE / "donors_web.parquet", index=False)
    log(f"donors_web.parquet: {len(donors):,} rows")

    try:
        adata.file.close()
    except Exception:
        pass

    return {
        "source_h5ad": str(h5ad),
        "source_n_cells": int(n_cells),
        "sampled_cells": int(len(cells)),
        "program_source": program_source,
    }


def copy_csv(source, dest_name, optional=True):
    source = Path(source)
    if source.exists():
        df = pd.read_csv(source)
        df.to_csv(CACHE / dest_name, index=False)
        log(f"{dest_name}: {len(df):,} rows")
        return True

    if optional:
        log(f"optional source missing: {source}")
        return False

    raise FileNotFoundError(source)


def build_dag_cache():
    step33 = PROJECT / "data" / "SEAAD" / "processed" / "33_DAG_v2_evidence_integration"

    sources = {
        "dag_v1_edges.csv": step33 / "33_DAG_v1_edges.csv",
        "dag_v2_edges.csv": step33 / "33_DAG_v2_primary_edges.csv",
        "edge_evidence.csv": step33 / "33_edge_evidence_master.csv",
        "path_evidence.csv": step33 / "33_path_evidence_master.csv",
    }

    status = {}
    for dest, src in sources.items():
        status[dest] = copy_csv(src, dest, optional=True)
    return status


def try_build_transport_cache():
    source = (
        PROJECT
        / "data"
        / "SEAAD"
        / "processed"
        / "causflow_transition"
        / "34_DAG_v2_topology"
        / "evaluation"
        / "34B_pair_metrics.csv"
    )
    if source.exists():
        df = pd.read_csv(source)
        df.to_parquet(CACHE / "transport_metrics.parquet", index=False)
        log(f"transport_metrics.parquet: {len(df):,} rows")
        return True
    log(f"optional STEP34B pair metrics missing: {source}")
    return False


def try_build_intervention_cache():
    source = (
        PROJECT
        / "data"
        / "SEAAD"
        / "processed"
        / "causflow_transition"
        / "35_virtual_intervention"
        / "35A_specificity_summary.csv"
    )
    if source.exists():
        df = pd.read_csv(source)
        df.to_parquet(CACHE / "intervention_summary.parquet", index=False)
        log(f"intervention_summary.parquet: {len(df):,} rows")
        return True
    log(f"optional STEP35A summary missing: {source}")
    return False


def build_external_evidence_cache():
    rows = []

    candidates = [
        (
            "STEP32B",
            "TREM2/SYK",
            PROJECT / "data" / "SEAAD" / "processed" / "32B_GSE158469_TREM2_mechanism_validation" / "32B_specificity_by_contrast.csv",
        ),
        (
            "STEP32C",
            "APOE/LXR",
            PROJECT / "data" / "SEAAD" / "processed" / "32C_GSE226076_LXR_mechanism_validation" / "32C_specificity_by_contrast.csv",
        ),
        (
            "STEP32D",
            "NLRP3",
            PROJECT / "data" / "SEAAD" / "processed" / "32D_GSE271192_NLRP3_P7_validation" / "32D_specificity_by_contrast.csv",
        ),
    ]

    for step, mechanism, path in candidates:
        if not path.exists():
            continue

        df = pd.read_csv(path)
        df.insert(0, "step", step)
        df.insert(1, "mechanism", mechanism)
        rows.append(df)

    if rows:
        out = pd.concat(rows, ignore_index=True, sort=False)
        out.to_parquet(CACHE / "external_evidence.parquet", index=False)
        log(f"external_evidence.parquet: {len(out):,} rows")
        return True

    log("No STEP32B-D specificity tables detected for external evidence cache.")
    return False


def main():
    log(f"project: {PROJECT}")
    log(f"cache:   {CACHE}")

    metadata = build_cells_and_donors()
    dag_status = build_dag_cache()
    transport = try_build_transport_cache()
    intervention = try_build_intervention_cache()
    external = build_external_evidence_cache()

    manifest = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        **metadata,
        "dag_files": dag_status,
        "transport_cache": transport,
        "intervention_cache": intervention,
        "external_evidence_cache": external,
    }

    (CACHE / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    log("DONE")
    print()
    print("Next:")
    print(f"  cd {WEBAPP}")
    print("  streamlit run app.py")


if __name__ == "__main__":
    main()
