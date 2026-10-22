"""Lightweight, model-free analysis of user-uploaded h5ad datasets.

IMPORTANT: These routines are exploratory expression transformations, NOT a
causal model, biological perturbation prediction, or patient diagnostic tool.

Public API:
    inspect_h5ad(path)
    run_simulation(path, output_path, ...)

Reads the X matrix in backed mode and caps sampled cells/genes. The original
h5ad file is never modified.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional

import numpy as np
import pandas as pd
from scipy import sparse


MAX_CELLS_PER_GROUP = 1200
MAX_GENES = 2000
MIN_REFERENCE_CELLS = 20


@dataclass
class SimulationResult:
    output_path: str
    mode: str
    n_source: int
    n_target: int
    n_genes: int
    gene_summary: pd.DataFrame
    embedding: pd.DataFrame
    description: str
    gene_resolution: Optional[str] = None


@contextmanager
def _open_h5ad(path):
    import anndata as ad
    adata = ad.read_h5ad(str(path), backed="r")
    try:
        yield adata
    finally:
        if adata.file is not None:
            adata.file.close()


# These are *identifiers*, not arbitrary biological aliases/synonyms.
# No external synonym mapping is attempted because it could edit the wrong gene.
GENE_COLUMN_PRIORITY = (
    "gene_symbol", "gene_symbols", "symbol", "hgnc_symbol",
    "external_gene_name", "gene_name", "gene_names", "gene",
    "feature_name", "feature_names", "gene_id", "gene_ids",
    "feature_id", "feature_ids", "name", "names",
)


@dataclass(frozen=True)
class GeneResolution:
    index: int
    var_name: str
    match_column: str
    matched_value: str


def _gene_annotation_columns(var: pd.DataFrame) -> list[str]:
    """Return only plausible identifier/symbol columns, in a stable priority order."""
    columns = [str(c) for c in var.columns]
    prioritized = [
        next((c for c in columns if c.casefold() == wanted), None)
        for wanted in GENE_COLUMN_PRIORITY
    ]
    result = [c for c in prioritized if c is not None]
    for col in columns:
        lower = col.casefold().replace(" ", "_")
        plausible = ("symbol" in lower or ("gene" in lower and any(
            fragment in lower for fragment in ("name", "id", "label")
        )) or ("feature" in lower and any(
            fragment in lower for fragment in ("name", "id")
        )))
        if plausible and col not in result:
            result.append(col)
    return [c for c in result if (
        pd.api.types.is_string_dtype(var[c].dtype)
        or isinstance(var[c].dtype, pd.CategoricalDtype)
        or var[c].dtype == object
    )]


def _to_gene_strings(values) -> np.ndarray:
    return np.asarray(pd.Series(values, dtype="string").fillna("").str.strip().tolist(), dtype=str)


def _ensembl_root(s: str) -> str:
    # Version stripping is safe for explicit Ensembl IDs only, e.g. ENSG...12.3
    return re.sub(r"\.\d+$", "", s) if re.fullmatch(
        r"ENS[A-Z]*G\d+(?:\.\d+)?", s, flags=re.IGNORECASE
    ) else s


def _resolve_gene(adata, gene: str) -> GeneResolution:
    query = str(gene or "").strip()
    if not query:
        raise ValueError("Enter a gene symbol or gene ID.")
    var_names = _to_gene_strings(adata.var_names)
    columns = _gene_annotation_columns(adata.var)

    # First, try exact matches. Then try case-insensitive matches; finally
    # Ensembl version-insensitive matches. Ambiguities are never silently picked.
    for tier in ("exact", "casefold", "ensembl_version"):
        for col in [None] + columns:
            values = var_names if col is None else _to_gene_strings(adata.var[col])
            if tier == "exact":
                matching = np.flatnonzero(values == query)
            elif tier == "casefold":
                matching = np.flatnonzero(np.char.lower(values) == query.casefold())
            else:
                if _ensembl_root(query) == query and not re.fullmatch(r"ENS[A-Z]*G\d+", query, flags=re.I):
                    continue
                matching = np.flatnonzero([
                    _ensembl_root(v).casefold() == _ensembl_root(query).casefold()
                    for v in values
                ])
            if len(matching) > 1:
                samples = ", ".join(var_names[matching[:5]])
                source = "var_names" if col is None else f"var[{col!r}]"
                raise ValueError(
                    f"Gene {query!r} matches {len(matching)} expression columns in {source} ({samples}). "
                    "The match is ambiguous. Specify a unique var_name or Ensembl ID."
                )
            if len(matching) == 1:
                idx = int(matching[0])
                return GeneResolution(idx, str(var_names[idx]),
                                      "var_names" if col is None else f"var[{col!r}]",
                                      str(values[idx]))

    raw = getattr(adata, "raw", None)
    raw_hint = ""
    if raw is not None:
        raw_vals = _to_gene_strings(raw.var_names)
        raw_columns = _gene_annotation_columns(raw.var)
        found_raw = np.any(np.char.lower(raw_vals) == query.casefold())
        if not found_raw:
            for col in raw_columns:
                if np.any(np.char.lower(_to_gene_strings(raw.var[col])) == query.casefold()):
                    found_raw = True
                    break
        if found_raw:
            raw_hint = ("This gene is present in adata.raw, but the simulator uses adata.X. "
                        "Export an X matrix containing the gene and upload it again.")
    sample = ", ".join(var_names[:6])
    col_hint = ", ".join(columns[:8]) if columns else "None found"
    raise ValueError(
        f"Gene {query!r} was not found in var_names or supported annotations for adata.X. "
        f"Example var_names: {sample}; searchable columns: {col_hint}. "
        + (raw_hint or "If the gene was removed by HVG selection, upload an expression matrix that includes it.")
    )


def lookup_gene(path: str, query: str) -> dict:
    """Look up a gene in the X axis without loading the expression matrix."""
    with _open_h5ad(path) as adata:
        result = _resolve_gene(adata, query)
        return {
            "gene_query": str(query).strip(),
            "var_name": result.var_name,
            "var_index": result.index,
            "matched_column": result.match_column,
            "matched_value": result.matched_value,
        }


def _display_gene_labels(adata, gene_indices: np.ndarray) -> list[str]:
    var = adata.var.iloc[gene_indices]
    names = _to_gene_strings(adata.var_names[gene_indices]).tolist()
    label_cols = [c for c in _gene_annotation_columns(var)
                  if c.casefold() in {
                      "gene_symbol", "gene_symbols", "symbol", "hgnc_symbol",
                      "external_gene_name", "gene_name", "gene_names", "feature_name",
                  }]
    if label_cols:
        values = _to_gene_strings(var[label_cols[0]])
        return [label if label else name for label, name in zip(values, names)]
    return names


def inspect_h5ad(path: str) -> dict:
    """Inspect metadata without materializing the full expression matrix."""
    with _open_h5ad(path) as adata:
        candidates = {}
        for col in adata.obs.columns:
            series = adata.obs[col]
            if pd.api.types.is_numeric_dtype(series) and series.nunique(dropna=True) > 25:
                continue
            counts = series.astype("string").value_counts(dropna=True)
            if 2 <= len(counts) <= 25:
                candidates[str(col)] = {str(k): int(v) for k, v in counts.items()}
        return {
            "n_obs": int(adata.n_obs),
            "n_vars": int(adata.n_vars),
            "obs_columns": [str(c) for c in adata.obs.columns],
            "categorical_columns": candidates,
            "layers": list(map(str, adata.layers.keys())),
            "has_hvg": "highly_variable" in adata.var.columns,
            "has_umap": "X_umap" in adata.obsm.keys(),
            "unique_genes": bool(adata.var_names.is_unique),
            "var_name_examples": [str(x) for x in adata.var_names[:8]],
            "gene_annotation_columns": _gene_annotation_columns(adata.var),
            "has_raw": getattr(adata, "raw", None) is not None,
            "file_size_mb": round(Path(path).stat().st_size / (1024 ** 2), 2),
        }


def _dense(matrix) -> np.ndarray:
    if sparse.issparse(matrix):
        matrix = matrix.toarray()
    arr = np.asarray(matrix, dtype=np.float32)
    if arr.ndim != 2:
        raise ValueError("Expression data must be a 2D cells-by-genes matrix.")
    return arr


def _get_rows(adata, rows: np.ndarray, genes: Optional[np.ndarray] = None) -> np.ndarray:
    """Small sorted HDF5 row batches to bound peak memory.

    Read rows first, then select genes in memory. This also avoids two-vector
    fancy indexing errors in backed dense HDF5 datasets.
    """
    rows = np.asarray(rows, dtype=int)
    if len(rows) == 0:
        ncols = adata.n_vars if genes is None else len(genes)
        return np.empty((0, ncols), dtype=np.float32)
    blocks = []
    for block in np.array_split(np.sort(rows), max(1, (len(rows) + 63) // 64)):
        mat = _dense(adata.X[block, :])
        if genes is not None:
            mat = mat[:, genes]
        blocks.append(mat)
    return np.concatenate(blocks, axis=0)


def _library_sizes(adata, rows: np.ndarray) -> np.ndarray:
    """Full-gene library sums; never normalize using only selected genes."""
    blocks = []
    for block in np.array_split(np.sort(np.asarray(rows, dtype=int)),
                                max(1, (len(rows) + 63) // 64)):
        X = adata.X[block, :]
        blocks.append(np.asarray(X.sum(axis=1)).ravel().astype(np.float64))
    return np.concatenate(blocks)


def _choose_genes(adata, rows: np.ndarray, max_genes: int, focus_index: Optional[int]) -> np.ndarray:
    n = int(adata.n_vars)
    if n <= max_genes:
        chosen = np.arange(n, dtype=int)
    else:
        hvg = None
        if "highly_variable" in adata.var:
            hv = adata.var["highly_variable"].fillna(False).astype(bool).to_numpy()
            idx = np.flatnonzero(hv)
            if len(idx) >= max_genes:
                hvg = idx[:max_genes]
        if hvg is not None:
            chosen = hvg
        else:
            # Rank genes by empirical variation in a small, seeded probe.
            # This is for efficient exploration, not reproducible HVG inference.
            rng = np.random.default_rng(173)
            probe = np.sort(rng.choice(rows, min(240, len(rows)), replace=False))
            X = _get_rows(adata, probe)
            variances = np.var(X.astype(np.float64), axis=0)
            variances = np.nan_to_num(variances, nan=-np.inf)
            chosen = np.argpartition(variances, -max_genes)[-max_genes:]
    if focus_index is not None and focus_index not in chosen:
        chosen = np.asarray(chosen).copy()
        chosen[-1] = int(focus_index)
    return np.unique(np.sort(chosen.astype(int)))


def _expression_to_log(adata, rows: np.ndarray, genes: np.ndarray, input_kind: str) -> np.ndarray:
    X = _get_rows(adata, rows, genes)
    if not np.isfinite(X).all():
        raise ValueError("Input contains NaN or infinity; clean it locally first.")
    if np.min(X) < -1e-6:
        raise ValueError("adata.X contains negative values. Upload raw counts or non-negative log1p expression, not scaled data.")
    if input_kind == "counts":
        # Validation: integer-like counts; use true full-matrix library totals.
        if (np.abs(X - np.rint(X)) > 1e-3).mean() > 0.001:
            raise ValueError("Raw counts were selected, but many X values are non-integers. Check the input expression type.")
        depth = _library_sizes(adata, rows)
        if not np.isfinite(depth).all() or (depth <= 0).any():
            raise ValueError("Some cells have zero or invalid total counts. Apply QC before uploading.")
        X = np.log1p(X / depth[:, None] * 10000.0)
    elif input_kind != "log1p":
        raise ValueError("Only raw counts or non-negative log1p expression is supported.")
    if not np.isfinite(X).all():
        raise ValueError("Expression conversion produced invalid values.")
    return X.astype(np.float32, copy=False)


def mean_shift(source: np.ndarray, target: np.ndarray, strength: float) -> np.ndarray:
    """Unpaired, unadjusted distribution mean shift (NOT causal transport)."""
    if len(source) == 0 or len(target) == 0:
        raise ValueError("Both source and target groups must contain cells.")
    delta = np.mean(target, axis=0) - np.mean(source, axis=0)
    return np.maximum(0.0, source + np.float32(strength) * delta).astype(np.float32)


def edit_single_gene(source: np.ndarray, gene_index: int, multiplier: float) -> np.ndarray:
    """Direct edit of a single log1p expression column; no network response."""
    if not (0 <= gene_index < source.shape[1]):
        raise ValueError("Invalid gene index.")
    if not (0 <= multiplier <= 3):
        raise ValueError("Expression multiplier must be between 0 and 3.")
    result = source.copy()
    x = source[:, gene_index].astype(np.float64)
    if x.max(initial=0) > 30:
        raise ValueError("Log1p values are unexpectedly large. Check whether raw counts were mislabeled as log1p.")
    result[:, gene_index] = np.log1p(np.expm1(x) * multiplier).astype(np.float32)
    return result


def _embedding(groups: dict, seed: int) -> pd.DataFrame:
    """Small 2D PCA of common source / result / target coordinates."""
    rng = np.random.default_rng(seed)
    subset, labels = [], []
    for label, block in groups.items():
        if block is None or len(block) == 0:
            continue
        idx = np.sort(rng.choice(len(block), min(180, len(block)), replace=False))
        subset.append(block[idx])
        labels.extend([label] * len(idx))
    if not subset:
        return pd.DataFrame(columns=["PC1", "PC2", "Group"])
    X = np.concatenate(subset, axis=0).astype(np.float64)
    if X.shape[1] > 160:
        keep = np.argsort(X.var(axis=0))[-160:]
        X = X[:, keep]
    X -= X.mean(axis=0, keepdims=True)
    # Robust PCA: sparse svds on centered dense data, with small-matrix fallback.
    try:
        from scipy.sparse.linalg import svds
        if min(X.shape) < 4:
            raise ValueError("Too few observations for SVD")
        U, S, _ = svds(X, k=2)
        order = np.argsort(S)[::-1]
        coords = U[:, order] * S[order]
    except Exception:
        U, S, _ = np.linalg.svd(X, full_matrices=False)
        coords = np.zeros((len(X), 2), dtype=float)
        dim = min(2, len(S))
        coords[:, :dim] = U[:, :dim] * S[:dim]
    return pd.DataFrame({"PC1": coords[:, 0], "PC2": coords[:, 1], "Group": labels})


def _subset_rows(obs: pd.DataFrame, stage_col: Optional[str],
                 from_stage: Optional[str], filter_col: Optional[str],
                 filter_value: Optional[str]) -> np.ndarray:
    mask = np.ones(len(obs), dtype=bool)
    if stage_col and from_stage:
        mask &= (obs[stage_col].astype("string").to_numpy(dtype=str) == from_stage)
    if filter_col and filter_value:
        mask &= (obs[filter_col].astype("string").to_numpy(dtype=str) == filter_value)
    return np.flatnonzero(mask)



def _build_safe_export_metadata(adata, source_rows, gene_indices, display_genes,
                                stage_col=None, filter_col=None):
    """Construct a minimal, predictable AnnData metadata schema for h5ad export.

    The input may contain heterogeneous columns, nested values and names such as
    ``QC/pass``; only selected scalar biological labels are copied. This avoids
    HDF5 group-key issues without renaming gene IDs or changing expression.
    """
    source_obs = adata.obs.iloc[source_rows]
    out_obs = pd.DataFrame(index=pd.Index(source_obs.index.astype(str)).rename(None))

    semantic_columns = {
        "disease_stage": [stage_col, "disease_stage", "Overall AD neuropathological Change",
                          "AD stage", "stage"],
        "donor_id": ["Donor ID", "donor_id", "donor", "Donor"],
        "brain_region": ["Brain Region", "brain_region", "Region", "region"],
        "cell_type": ["cell_type", "Celltype", "Cell Type", "Subclass"],
        "sample_id": ["sample_id", "Sample ID", "sample"],
    }
    kept = {}
    for dest, possibilities in semantic_columns.items():
        source_name = next((c for c in possibilities if c and c in source_obs.columns), None)
        if source_name is not None:
            # Convert to plain strings so complex categorical metadata doesn't
            # carry extra HDF5 groups/categories into this small output file.
            out_obs[dest] = source_obs[source_name].astype("string").fillna("").to_numpy(dtype=str)
            kept[dest] = str(source_name)

    if filter_col and filter_col in source_obs.columns:
        out_obs["selected_filter_value"] = (
            source_obs[filter_col].astype("string").fillna("").to_numpy(dtype=str)
        )
        kept["selected_filter_value"] = str(filter_col)

    out_var = pd.DataFrame(index=pd.Index(
        adata.var_names[gene_indices].astype(str)).rename(None)
    )
    out_var["gene_symbol"] = [str(x) for x in display_genes]
    return out_obs, out_var, kept


def run_simulation(
    path: str, output_path: str, *, mode: str,
    input_kind: str = "log1p", stage_col: Optional[str] = None,
    source_stage: Optional[str] = None, target_stage: Optional[str] = None,
    filter_col: Optional[str] = None, filter_value: Optional[str] = None,
    strength: float = 1.0, focus_gene: Optional[str] = None,
    max_cells: int = 800, max_genes: int = 1000, seed: int = 42,
) -> SimulationResult:
    """Run bounded simulation; write a new h5ad without editing original data."""
    import anndata as ad
    if mode not in ("stage_mean_shift", "single_gene_edit"):
        raise ValueError("Unknown simulation mode")
    if max_cells < MIN_REFERENCE_CELLS or max_cells > MAX_CELLS_PER_GROUP:
        raise ValueError("Sample size is outside the permitted range.")
    if max_genes < 20 or max_genes > MAX_GENES:
        raise ValueError("Gene count is outside the permitted range.")
    if not np.isfinite(strength):
        raise ValueError("Simulation strength must be finite.")
    if mode == "stage_mean_shift" and not (0 <= strength <= 1.5):
        raise ValueError("Stage shift strength must be between 0 and 1.5.")
    rng = np.random.default_rng(seed)
    with _open_h5ad(path) as adata:
        if not adata.var_names.is_unique:
            raise ValueError("Duplicate gene identifiers in var_names. Apply adata.var_names_make_unique() locally.")
        if stage_col and stage_col not in adata.obs.columns:
            raise ValueError("Selected disease-stage variable is absent from obs.")
        if filter_col and filter_col not in adata.obs.columns:
            raise ValueError("Selected filter variable is absent from obs.")
        if mode == "stage_mean_shift":
            if not stage_col or not source_stage or not target_stage:
                raise ValueError("Stage mean shift requires a disease-stage variable, source group, and target group.")
            if source_stage == target_stage:
                raise ValueError("Source and target groups must be different.")
        if mode == "single_gene_edit" and not focus_gene:
            raise ValueError("Single-gene editing requires a gene identifier.")
        source_all = _subset_rows(adata.obs, stage_col, source_stage,
                                  filter_col, filter_value)
        if len(source_all) < MIN_REFERENCE_CELLS:
            raise ValueError(f"Source has {len(source_all)} cells; at least {MIN_REFERENCE_CELLS} are required.")
        source_rows = np.sort(rng.choice(source_all, size=min(max_cells, len(source_all)), replace=False))
        target_rows = np.asarray([], dtype=int)
        if mode == "stage_mean_shift":
            target_all = _subset_rows(adata.obs, stage_col, target_stage,
                                      filter_col, filter_value)
            if len(target_all) < MIN_REFERENCE_CELLS:
                raise ValueError(f"Target has {len(target_all)} cells; at least {MIN_REFERENCE_CELLS} are required.")
            target_rows = np.sort(rng.choice(target_all, size=min(max_cells, len(target_all)), replace=False))
        resolved_gene = (_resolve_gene(adata, focus_gene)
                         if mode == "single_gene_edit" else None)
        sampled = np.unique(np.concatenate([source_rows, target_rows]))
        gene_indices = _choose_genes(adata, sampled, max_genes,
                                     resolved_gene.index if resolved_gene else None)
        gene_names = adata.var_names[gene_indices].astype(str).tolist()
        display_genes = _display_gene_labels(adata, gene_indices)
        source = _expression_to_log(adata, source_rows, gene_indices, input_kind)
        target = (_expression_to_log(adata, target_rows, gene_indices, input_kind)
                  if len(target_rows) else None)
        if mode == "stage_mean_shift":
            simulated = mean_shift(source, target, strength)
            description = (
                "Exploratory stage mean shift: applies an unpaired, unadjusted "
                "target_mean minus source_mean shift per gene; not a trained model, causal effect, or actual cell-state forecast."
            )
        else:
            index = int(np.flatnonzero(gene_indices == resolved_gene.index)[0])
            simulated = edit_single_gene(source, index, strength)
            description = (
                "Numerical single-gene edit: changes only the selected gene's log1p expression; "
                "all other genes are unchanged. No CRISPR or drug downstream response is inferred."
            )
        gene_summary = pd.DataFrame({
            "gene": display_genes,
            "gene_id": gene_names,
            "source_mean": source.mean(axis=0),
            "simulated_mean": simulated.mean(axis=0),
            "target_mean": target.mean(axis=0) if target is not None else np.full(len(gene_names), np.nan),
        })
        gene_summary["simulated_minus_source"] = (
            gene_summary["simulated_mean"] - gene_summary["source_mean"]
        )
        gene_summary["abs_change"] = gene_summary["simulated_minus_source"].abs()
        gene_summary = gene_summary.sort_values("abs_change", ascending=False).reset_index(drop=True)
        embedding = _embedding({"Source": source, "Simulated": simulated, "Target reference": target}, seed)
        out_obs, out_var, preserved_columns = _build_safe_export_metadata(
            adata, source_rows, gene_indices, display_genes,
            stage_col=stage_col, filter_col=filter_col,
        )
        out_obs["simulated_mode"] = str(mode)
        out_obs["simulation_strength"] = float(strength)
        if mode == "stage_mean_shift":
            out_obs["simulated_target_stage"] = str(target_stage)
        else:
            out_obs["simulated_target_gene"] = str(focus_gene)
        # Export schema intentionally omits other original obs/var columns;
        # upload source is left untouched. Data values are never guessed.
        out = ad.AnnData(
            X=simulated.astype(np.float32),
            obs=out_obs,
            var=out_var,
        )
        out.layers["original_log1p"] = source.astype(np.float32)
        out.uns["export_metadata_policy"] = "essential_scalar_annotations_only"
        out.uns["preserved_metadata_columns"] = ", ".join(
            f"{k} <- {v}" for k, v in preserved_columns.items()
        )
        out.uns["original_source_stage_column"] = str(stage_col or "")
        out.uns["original_filter_column"] = str(filter_col or "")
        out.uns["simulation_method"] = mode
        out.uns["interpretation_warning"] = description
        out.uns["input_expression_interpretation"] = input_kind
        out.uns["output_expression_interpretation"] = "log1p normalized expression"
        out.uns["simulation_seed"] = int(seed)
        out.uns["n_reference_target_cells"] = int(len(target_rows))
        out.uns["n_genes_used"] = int(len(gene_indices))
        out.uns["simulator_version"] = "exploratory-1.2-safe-h5ad-export"
        gene_resolution = None
        if resolved_gene is not None:
            gene_resolution = (
                f"{focus_gene.strip()} → {resolved_gene.var_name} "
                f"(via {resolved_gene.match_column})"
            )
            out.uns["resolved_gene_query"] = str(focus_gene).strip()
            out.uns["resolved_gene_var_name"] = resolved_gene.var_name
            out.uns["resolved_gene_match_column"] = resolved_gene.match_column
        final_path = Path(output_path)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = final_path.with_name(final_path.stem + ".partial.h5ad")
        try:
            out.write_h5ad(str(temp_path), compression="gzip")
            temp_path.replace(final_path)
        finally:
            # Never leave a half-written h5ad masquerading as a valid output.
            temp_path.unlink(missing_ok=True)
        return SimulationResult(
            output_path=str(output_path), mode=mode,
            n_source=len(source_rows), n_target=len(target_rows),
            n_genes=len(gene_indices), gene_summary=gene_summary,
            embedding=embedding, description=description,
            gene_resolution=gene_resolution,
        )
