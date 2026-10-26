"""Independent denominator and integrity audit of extracted study evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.reporting import read_evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    stage = args.workspace_root.resolve() / "work/05_session_vwap" / args.run_id
    events, windows = read_evidence(stage)
    product_days = windows[["product", "session_date"]].drop_duplicates()
    expected_windows = 14 * len(product_days)
    if len(windows) != expected_windows:
        raise AssertionError(f"window count {len(windows)} != {expected_windows}")
    keys = ["product", "session_date", "timeframe", "anchor", "window"]
    if windows.duplicated(keys).any():
        raise AssertionError("duplicate window key")
    b = events[events.strategy == "B"]
    departures = windows[windows.departure == True]
    if len(b) != len(departures) or b.duplicated(keys).any():
        raise AssertionError("B first-departure denominator mismatch")
    if len(b.merge(departures[keys], on=keys, how="inner")) != len(b):
        raise AssertionError("B event missing corresponding departure window")
    outcomes = {}
    for strategy in ("A", "C"):
        part = events[(events.strategy == strategy) & (events.exclusion.isna()) &
                      (events.h30_evaluable == True)]
        counts = part.h30_barrier_0p5.value_counts()
        if int(counts.sum()) != len(part) or set(counts.index) - {
                "favorable", "adverse", "neither", "ambiguous"}:
            raise AssertionError(f"non-exhaustive {strategy} barrier outcomes")
        outcomes[strategy] = {name: int(counts.get(name, 0)) for name in
                              ("favorable", "adverse", "neither", "ambiguous")}
        if (part.window_minutes_remaining < 30).any():
            raise AssertionError(f"late {strategy} in primary cohort")
    if (events[(events.exclusion.isna()) & (events.source_reference_audited != True)].shape[0]):
        raise AssertionError("unevaluated source reference")
    audit = {"eligible_product_days": len(product_days), "windows": len(windows),
             "expected_windows": expected_windows, "B_departures": len(departures),
             "B_first_events": len(b), "primary_barrier_outcomes": outcomes,
             "unique_event_ids": True, "source_reference_audited": True,
             "status": "passed"}
    (stage / "denominator-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
