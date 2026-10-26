"""Extract pre-signal A/C context into a new, versioned evidence run."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil

from abacus_bhishma.paths import load_workspace_paths
from src.conditional_context import build_daily_context, context_year
from src.engine import PRODUCTS, YEARS, verify_inputs


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    publication_root = load_workspace_paths(root).publication_root
    study = root / "studies/05_session_vwap"
    parent = root / "runs/05_session_vwap/20260923T015900Z_vwap3"
    stage = root / "work/05_session_vwap" / args.run_id
    if stage.exists() or (root / "runs/05_session_vwap" / args.run_id).exists():
        raise FileExistsError("run ID already exists")
    parent_manifest = json.loads((parent / "manifest.json").read_text())
    if parent_manifest["run_id"] != parent.name:
        raise ValueError("parent identity mismatch")
    parent_artifacts = {item["path"]: item["sha256"]
                        for item in parent_manifest["artifact_hashes"]}
    for product in PRODUCTS:
        for year in YEARS[product]:
            relative = f"events/events_{product}_{year}.parquet"
            if digest(parent / relative) != parent_artifacts[relative]:
                raise ValueError(f"parent event hash mismatch: {relative}")
    lock = json.loads((study / "inputs.lock.json").read_text())
    checks = verify_inputs(publication_root, lock)
    stage.mkdir(parents=True)
    (stage / "context").mkdir()
    shutil.copy2(study / "inputs.lock.json", stage / "inputs.lock.json")
    shutil.copy2(study / "protocol-1.1.0.md", stage / "protocol-1.1.0.md")
    (stage / "input-verification.json").write_text(json.dumps(checks, indent=2) + "\n")
    (stage / "parent-verification.json").write_text(json.dumps({
        "parent_run": parent.name,
        "parent_manifest_sha256": digest(parent / "manifest.json"),
        "verified_parent_event_partitions": sum(len(YEARS[p]) for p in PRODUCTS),
        "parent_protocol": "1.0.0"}, indent=2) + "\n")
    config = {"study_id": "05_session_vwap", "run_id": args.run_id,
              "protocol_version": "1.1.0", "parent_run_id": parent.name,
              "release_id": "session_anchored_vwap__1.0.0",
              "publication_root": str(publication_root),
              "products": list(PRODUCTS), "timeframes": ["2m", "5m"],
              "strategies": ["vwap_extreme_fade", "vwap_first_retest_bounce",
                             "vwap_reentry_fade_exploratory"],
              "primary_outcome": "h30_barrier_0p5", "fixed_tick_check": 8,
              "bootstrap_seed": 310733, "workers": args.workers,
              "costs": None, "started_at_utc": datetime.now(timezone.utc).isoformat()}
    (stage / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    daily, cutoffs = build_daily_context(publication_root)
    daily_file = stage / "daily_context.parquet"
    daily.to_parquet(daily_file, index=False)
    (stage / "atr-cutoffs.json").write_text(json.dumps(cutoffs, indent=2) + "\n")
    tasks = [(publication_root, parent, product, year, daily_file, stage / "context")
             for product in PRODUCTS for year in YEARS[product]]
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(context_year, *task): task[2:4] for task in tasks}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps(result), flush=True)
    (stage / "extraction-summary.json").write_text(json.dumps(
        sorted(results, key=lambda x: (x["product"], x["year"])), indent=2) + "\n")


if __name__ == "__main__":
    main()
