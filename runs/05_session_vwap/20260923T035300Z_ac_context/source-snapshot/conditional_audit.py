"""Independently reconcile derived A/C context to the sealed parent events."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.engine import PRODUCTS, YEARS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    parent = root / "runs/05_session_vwap/20260923T015900Z_vwap3/events"
    stage = root / "work/05_session_vwap" / args.run_id
    counts = {key: 0 for key in ("A", "C", "A_control", "C_near")}
    statuses = {}
    early_local_ny = 0
    for product in PRODUCTS:
        for year in YEARS[product]:
            name = f"{product}_{year}.parquet"
            original = pd.read_parquet(parent / f"events_{name}")
            original = original[original.strategy.isin(counts)]
            context = pd.read_parquet(stage / "context" / f"context_{name}")
            reentry = pd.read_parquet(stage / "context" / f"reentry_{name}")
            if len(context) != len(original) or context.event_id.duplicated().any():
                raise ValueError(f"context population mismatch {name}")
            keys = original.set_index("event_id")
            linked = keys.loc[context.event_id]
            for column in ("strategy", "product", "session_date", "timeframe", "anchor",
                           "window", "signal_ts", "h30_evaluable", "h30_barrier_0p5",
                           "h30_barrier_8ticks"):
                a = context[column].reset_index(drop=True).astype(str)
                b = linked[column].reset_index(drop=True).astype(str)
                if not a.equals(b):
                    raise ValueError(f"parent value changed: {name} {column}")
            for strategy, amount in context.strategy.value_counts().items():
                counts[strategy] += int(amount)
            c = context[context.strategy == "C"]
            if (c.c_peak_close_sigma + 1e-9 < c.c_departure_strength_sigma).any() or (
                c.c_peak_to_touch_minutes > c.c_departure_to_touch_minutes).any() or (
                c.c_peak_to_touch_minutes < 0).any():
                raise ValueError(f"C pre-touch context invalid {name}")
            before_ob = context[context.window_age_minutes < 30]
            if (before_ob.opening_balance_location != "unavailable").any():
                raise ValueError(f"future opening balance used {name}")
            early_local_ny += int(((context.strategy == "A") & (context.window == "ny") &
                                   (context.anchor == "ny") & (context.window_age_minutes < 30)).sum())
            a_ids = set(context.loc[context.strategy == "A", "event_id"])
            if len(reentry) != len(a_ids) or set(reentry.original_event_id) != a_ids:
                raise ValueError(f"reentry A denominator mismatch {name}")
            for status, amount in reentry.status.value_counts().items():
                statuses[status] = statuses.get(status, 0) + int(amount)
            confirmed = reentry[reentry.confirmed == True]
            if (pd.to_datetime(confirmed.reentry_signal_ts) <=
                    pd.to_datetime(confirmed.original_signal_ts)).any():
                raise ValueError(f"reentry not later than original A {name}")
    if early_local_ny != 0:
        raise ValueError("NY local anchor emitted an event before maturity")
    result = {"status": "passed", "parent_event_counts": counts,
              "reentry_status_counts": statuses,
              "ny_local_anchor_first_30m_events": early_local_ny,
              "partition_pairs": sum(len(YEARS[p]) for p in PRODUCTS)}
    (stage / "context-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
