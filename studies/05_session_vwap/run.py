"""Thin entry point for the frozen session VWAP statistical protocol."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from abacus_bhishma.paths import load_workspace_paths
from src.engine import PRODUCTS, YEARS, run_year, verify_inputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--warmup", type=int, choices=[20, 30, 40], default=30)
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    publication_root = load_workspace_paths(root).publication_root
    stage = root / "work/05_session_vwap" / args.run_id
    if stage.exists():
        raise FileExistsError(f"stage already exists: {stage}")
    stage.mkdir(parents=True)
    (stage / "events").mkdir()
    study = root / "studies/05_session_vwap"
    lock = json.loads((study / "inputs.lock.json").read_text())
    checks = verify_inputs(publication_root, lock)
    (stage / "input-verification.json").write_text(json.dumps(checks, indent=2) + "\n")
    shutil.copy2(study / "inputs.lock.json", stage / "inputs.lock.json")
    shutil.copy2(study / "protocol-1.0.0.md", stage / "protocol-1.0.0.md")
    config = {"study_id": "05_session_vwap", "run_id": args.run_id,
              "protocol_version": "1.0.0", "release_id": "session_anchored_vwap__1.0.0",
              "publication_root": str(publication_root),
              "strategies": ["vwap_return_after_departure", "vwap_extreme_fade",
                             "vwap_first_retest_bounce"],
              "products": list(PRODUCTS), "timeframes": ["2m", "5m"],
              "views": ["globex/globex", "asia/asia", "london/london", "ny/ny",
                        "globex/asia", "globex/london", "globex/ny"],
              "warmup_minutes": args.warmup, "horizons_minutes": [10, 30, 60],
              "sensitivity_only": args.warmup != 30,
              "barrier_sigma": 0.5, "barrier_sensitivities_sigma": [0.25, 1.0],
              "costs": None, "workers": args.workers,
              "started_at_utc": datetime.now(timezone.utc).isoformat()}
    (stage / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    tasks = [(publication_root, product, year, stage / "events", args.warmup, args.warmup != 30)
             for product in PRODUCTS for year in YEARS[product]]
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_year, *task): task[1:3] for task in tasks}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps(result), flush=True)
    (stage / "extraction-summary.json").write_text(json.dumps(sorted(results, key=lambda r: (r["product"], r["year"])), indent=2) + "\n")


if __name__ == "__main__":
    main()
