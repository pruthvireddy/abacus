"""Evaluate the frozen protocol using staged feature-only landmarks."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from abacus_bhishma.paths import load_workspace_paths
from src.features import PRODUCTS, YEARS, digest
from src.outcomes import evaluate_year


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    root = load_workspace_paths(workspace).publication_root
    study = workspace / "studies/06_vwap_state_dynamics"
    stage = workspace / "work/06_vwap_state_dynamics" / args.run_id
    if not stage.exists() or not (stage / "feature-feasibility.json").exists() or not (stage / "feature-source-key-audit.json").exists():
        raise FileNotFoundError("completed feature-only gate and source-key audit required")
    if (stage / "events").exists():
        raise FileExistsError("outcome extraction already started for this run ID")
    settings = json.loads((study / "protocol-1.0.0.json").read_text())
    if settings["status"] != "frozen" or settings["threshold_source_run_id"] != args.run_id:
        raise ValueError("frozen protocol must identify this feature-only gate")
    (stage / "events").mkdir()
    for name in ("protocol-1.0.0.json", "protocol-1.0.0.md", "inputs.lock.json"):
        shutil.copy2(study / name, stage / name)
    config = {**settings, "run_id": args.run_id, "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "publication_root": str(root), "workers": args.workers,
              "protocol_sha256": digest(study / "protocol-1.0.0.json")}
    (stage / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    tasks = [(root, stage, product, year, timeframe)
             for product in PRODUCTS for year in YEARS[product] for timeframe in ("2m", "5m")]
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(evaluate_year, *task): task[2:] for task in tasks}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps(result), flush=True)
    (stage / "extraction-summary.json").write_text(json.dumps(sorted(results, key=lambda r: (r["product"], r["year"], r["timeframe"])), indent=2) + "\n")


if __name__ == "__main__":
    main()
