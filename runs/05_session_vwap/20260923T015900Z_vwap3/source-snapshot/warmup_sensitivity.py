"""Retain and summarize full 20/40-minute warm-up reruns beside the primary run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import pandas as pd
from abacus_bhishma.paths import load_workspace_paths

from src.reporting import read_evidence, scorecards
from src.engine import verify_inputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--primary-run-id", required=True)
    parser.add_argument("--warmup-20-run-id", required=True)
    parser.add_argument("--warmup-40-run-id", required=True)
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    publication_root = load_workspace_paths(root).publication_root
    base = root / "work/05_session_vwap"
    primary = base / args.primary_run_id
    if not primary.is_dir():
        raise FileNotFoundError(primary)
    rows = []
    for minutes, run_id in ((30, args.primary_run_id), (20, args.warmup_20_run_id),
                            (40, args.warmup_40_run_id)):
        stage = base / run_id
        config = json.loads((stage / "config.json").read_text())
        if config["warmup_minutes"] != minutes:
            raise ValueError(f"warm-up configuration mismatch: {stage}")
        lock = json.loads((stage / "inputs.lock.json").read_text())
        checks = verify_inputs(publication_root, lock)
        (stage / "input-verification.json").write_text(json.dumps(checks, indent=2) + "\n")
        events, windows = read_evidence(stage)
        cards = scorecards(events, windows)
        for row in cards.itertuples(index=False):
            rows.append({"warmup_minutes": minutes, "strategy": row.strategy,
                         "product": row.product, "events": int(row.events),
                         "evaluable": int(row.evaluable), "successes": int(row.successes),
                         "rate": row.rate, "ci_low": row.ci_low, "ci_high": row.ci_high})
        if minutes != 30:
            dest = primary / "sensitivity" / f"warmup_{minutes}"
            if dest.exists():
                raise FileExistsError(dest)
            dest.mkdir(parents=True)
            for name in ("config.json", "inputs.lock.json", "protocol-1.0.0.md",
                         "input-verification.json", "extraction-summary.json"):
                shutil.copy2(stage / name, dest / name)
            shutil.move(str(stage / "events"), dest / "events")
            shutil.rmtree(stage)
    table = pd.DataFrame(rows)
    table.to_csv(primary / "tables/warmup_sensitivity.csv", index=False)
    print(table[["warmup_minutes", "strategy", "product", "events", "evaluable", "rate"]].to_string(index=False))


if __name__ == "__main__":
    main()
