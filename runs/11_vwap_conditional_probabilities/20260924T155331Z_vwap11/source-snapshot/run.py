"""Execute frozen study 11 outcomes from the feature-only gate."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import pandas as pd

from abacus_bhishma.paths import load_workspace_paths
from src.features import PRODUCTS, YEARS, digest, select_corridor_events
from src.outcomes import evaluate_partition


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    root = load_workspace_paths(workspace).publication_root
    study = workspace / "studies/11_vwap_conditional_probabilities"
    stage = workspace / "work/11_vwap_conditional_probabilities" / args.run_id
    if not stage.is_dir() or not (stage / "feature-feasibility.json").is_file():
        raise FileNotFoundError("completed feature-only gate required")
    if (stage / "events").exists():
        raise FileExistsError("outcome extraction already started for this run ID")
    config = json.loads((study / "protocol-1.0.0.json").read_text())
    if config.get("status") != "frozen" or config.get("threshold_source_run_id") != args.run_id:
        raise ValueError("frozen protocol must identify this feature-only run")
    for name in ("protocol-1.0.0.json", "protocol-1.0.0.md", "inputs.lock.json"):
        shutil.copy2(study / name, stage / name)
    executed = {
        **config, "run_id": args.run_id,
        "outcome_execution_started_at_utc": datetime.now(timezone.utc).isoformat(),
        "publication_root": str(root), "workers": args.workers,
        "protocol_sha256": digest(study / "protocol-1.0.0.json"),
    }
    (stage / "config.json").write_text(json.dumps(executed, indent=2) + "\n")

    selection_rows = []
    corridor = config["question_c"]
    for product in PRODUCTS:
        for timeframe in ("2m", "5m"):
            path = stage / "features" / f"candidates_c_{product}_{timeframe}.parquet"
            candidates = pd.read_parquet(path)
            selected, suppressed = select_corridor_events(
                candidates, corridor["minimum_corridor_ticks"],
                corridor["minimum_corridor_day_sigma"], corridor["event_lockout_minutes"],
            )
            selected.to_parquet(stage / "features" / f"events_c_{product}_{timeframe}.parquet", index=False)
            selection_rows.append({
                "product": product, "timeframe": timeframe,
                "base_candidates": len(candidates), "selected_events": len(selected),
                "suppressed_during_lockout": suppressed,
                "product_sessions": int(selected[["product", "session_date"]].drop_duplicates().shape[0]),
            })
    pd.DataFrame(selection_rows).to_csv(stage / "corridor-selection.csv", index=False)
    (stage / "events").mkdir()
    tasks = [
        (root, stage, product, year, timeframe)
        for product in PRODUCTS for year in YEARS[product] for timeframe in ("2m", "5m")
    ]
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(evaluate_partition, *task): task[2:] for task in tasks}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps(result, default=str), flush=True)
    results.sort(key=lambda row: (row["product"], row["year"], row["timeframe"]))
    (stage / "extraction-summary.json").write_text(json.dumps(results, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()

