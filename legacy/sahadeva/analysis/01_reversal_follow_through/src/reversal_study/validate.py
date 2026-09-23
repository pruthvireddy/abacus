from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from .events import detect_events_bruteforce


def reconciliation_sample(
    bars_by_chart: dict[tuple[str, int], pd.DataFrame],
    events_by_chart: dict[tuple[str, int], pd.DataFrame],
    seed: int,
    sample_per_chart: int = 12,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    checks = {
        "sampled_events": 0,
        "event_scan_matches": 0,
        "threshold_logic_matches": 0,
        "failures": [],
    }
    rng = np.random.default_rng(seed)
    for key, events in events_by_chart.items():
        bars = bars_by_chart[key]
        if events.empty:
            continue
        candidates = events.index.to_numpy()
        take = min(sample_per_chart, len(candidates))
        selected_event_rows = rng.choice(candidates, size=take, replace=False)
        positions = events.loc[selected_event_rows, "bar_index"].astype(int).tolist()
        brute = detect_events_bruteforce(bars, positions)
        for event_row, simple in zip(selected_event_rows, brute):
            event = events.loc[event_row]
            scan_match = (
                int(event["prior_opposite_run"]) == int(simple["prior_opposite_run"])
                and int(event["observed_L"]) == int(simple["observed_L"])
                and bool(event["run_censored"]) == bool(simple["run_censored"])
            )
            threshold_match = True
            for threshold in (1, 2, 3, 4, 5, 10):
                if bool(event[f"eligible_L_ge_{threshold}"]):
                    threshold_match &= bool(event[f"success_L_ge_{threshold}"]) == (int(simple["observed_L"]) >= threshold)
            checks["sampled_events"] += 1
            checks["event_scan_matches"] += int(scan_match)
            checks["threshold_logic_matches"] += int(threshold_match)
            if not scan_match or not threshold_match:
                checks["failures"].append(str(event["event_id"]))
            rows.append(
                {
                    "event_id": event["event_id"],
                    "asset": event["asset"],
                    "contract": event["contract"],
                    "range_setting": int(event["range_setting"]),
                    "chart_identity_status": event["chart_identity_status"],
                    "date_window": event["export_date"],
                    "split": event["split"],
                    "direction": event["signal_side"],
                    "cohort": "seeded real-event reconciliation sample",
                    "denominator": take,
                    "horizon": "natural run and thresholds 1/2/3/4/5/10",
                    "units": "bars",
                    "timing_status": event["timing_status"],
                    "source_file": event["source_file"],
                    "source_row": int(event["source_row"]),
                    "optimized_prior_run": int(event["prior_opposite_run"]),
                    "bruteforce_prior_run": int(simple["prior_opposite_run"]),
                    "optimized_observed_L": int(event["observed_L"]),
                    "bruteforce_observed_L": int(simple["observed_L"]),
                    "optimized_censored": bool(event["run_censored"]),
                    "bruteforce_censored": bool(simple["run_censored"]),
                    "event_scan_match": scan_match,
                    "threshold_logic_match": threshold_match,
                }
            )
    checks["all_checks_pass"] = (
        checks["sampled_events"] == checks["event_scan_matches"] == checks["threshold_logic_matches"]
    )
    return pd.DataFrame(rows), checks


def aggregate_invariants(all_events: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for threshold in config["thresholds"]:
        eligible = all_events[f"eligible_L_ge_{threshold}"].fillna(False)
        success = all_events[f"success_L_ge_{threshold}"].fillna(False)
        if (success & ~eligible).any():
            failures.append(f"success_without_eligibility_L_ge_{threshold}")
    common = all_events.loc[all_events["shared_eligible_10"]]
    previous = None
    for threshold in config["thresholds"]:
        probability = float(common[f"success_L_ge_{threshold}"].mean()) if len(common) else np.nan
        if previous is not None and probability > previous + 1e-12:
            failures.append(f"nonmonotone_common_cohort_at_{threshold}")
        previous = probability
    fixed_mae_columns = [c for c in all_events if c.startswith("mae_h")]
    fixed_mfe_columns = [c for c in all_events if c.startswith("mfe_h")]
    if fixed_mae_columns and (all_events[fixed_mae_columns].min(numeric_only=True) < 0).any():
        failures.append("negative_fixed_horizon_mae")
    if fixed_mfe_columns and (all_events[fixed_mfe_columns].min(numeric_only=True) < 0).any():
        failures.append("negative_fixed_horizon_mfe")
    return {
        "events": int(len(all_events)),
        "common_cohort_events": int(len(common)),
        "failures": failures,
        "all_checks_pass": not failures,
    }


def write_json(path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

