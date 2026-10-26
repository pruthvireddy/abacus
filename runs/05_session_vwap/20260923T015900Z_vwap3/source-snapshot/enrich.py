"""Audit saved events against pinned source paths and add excursion evidence."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
from abacus_bhishma.paths import load_workspace_paths
from src.engine import PRODUCTS, YEARS
from src.enrich import enrich_year


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    publication_root = load_workspace_paths(root).publication_root
    stage = root / "work/05_session_vwap" / args.run_id
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(enrich_year, publication_root, product, year, stage)
                   for product in PRODUCTS for year in YEARS[product]]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(json.dumps(result), flush=True)
    (stage / "source-audit.json").write_text(json.dumps(sorted(results, key=lambda r: (r["product"], r["year"])), indent=2) + "\n")


if __name__ == "__main__":
    main()
