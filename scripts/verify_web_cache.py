from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data_cache"

REQUIRED = {
    "atlas/cells": CACHE / "cells_web.parquet",
    "dag/DAG-v2": CACHE / "dag" / "dag_v2_primary_edges.csv",
    "transport/model means": CACHE / "transport" / "model_metric_means.csv",
    "transport/gains": CACHE / "transport" / "gain_decomposition.csv",
    "intervention/program response": CACHE / "intervention" / "program_response.csv",
    "intervention/specificity": CACHE / "intervention" / "specificity.csv",
    "external/concordance": CACHE / "external" / "concordance_aggregate.csv",
    "external/program comparison": CACHE / "external" / "program_level_comparison.csv",
}

print("=" * 88)
print("WEB CACHE VERIFICATION")
print("=" * 88)
ok = True
for label, path in REQUIRED.items():
    exists = path.exists()
    ok &= exists
    if exists:
        try:
            if path.suffix == ".parquet":
                n = len(pd.read_parquet(path))
            else:
                n = len(pd.read_csv(path))
            print(f"[OK]      {label:34s} rows={n:<7d} {path.relative_to(ROOT)}")
        except Exception as exc:
            ok = False
            print(f"[BROKEN]  {label:34s} {exc}")
    else:
        print(f"[MISSING] {label:34s} {path.relative_to(ROOT)}")

manifest = CACHE / "manifest.json"
if manifest.exists():
    try:
        m = json.loads(manifest.read_text(encoding="utf-8"))
        print("\nBuilt at:", m.get("built_at", "unknown"))
        print("Pipeline:", m.get("final_pipeline", "unknown"))
    except Exception:
        pass

print("\nRESULT:", "READY" if ok else "INCOMPLETE")
raise SystemExit(0 if ok else 1)
