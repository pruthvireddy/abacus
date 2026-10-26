"""Separately pinned, selection-only expansion of the frozen Stage 1 checks.

This checker never changes frozen scientific code/configuration or scores dates
outside the first min(5, available) accepted 2018 events per cell. Full causal prefix signal
IDs are checked independently before the selected outcomes are computed.
"""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
import time

import pandas as pd

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
WORKSPACE = STAGE.parents[2]
sys.path.insert(0, str(WORKSPACE / "studies/21_ema_cloud_trend_follow_opportunity"))

from src.execution import assert_frozen_sources, file_record, verify_record
from src.engine import generate_events, map_features
from src.outcomes import score_outcomes
from src.reference import scalar_acceptance, scalar_outcomes
from abacus_bhishma.ema_cloud import load_release
from abacus_bhishma.paths import load_workspace_paths


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False, default=str)
        handle.write("\n")


def equal(actual, expected, context):
    if pd.isna(actual) or pd.isna(expected):
        if not (pd.isna(actual) and pd.isna(expected)):
            raise AssertionError(context + ": unequal nulls")
    elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
        if not math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12):
            raise AssertionError(context + ": unequal scalar values")
    elif actual != expected:
        raise AssertionError(context + ": unequal values")


def check_every_outcome_field(bars, sample, measured, horizons):
    independent = scalar_outcomes(bars, sample, horizons, roster_end_is_endpoint=False)
    expected_by_key = {(row["event_id"], row["horizon"]): row for row in independent.to_dict("records")}
    event_by_id = {row["event_id"]: row for row in sample.to_dict("records")}
    roster = bars.to_dict("records")
    checked = 0
    for observed in measured.to_dict("records"):
        event = event_by_id[observed["event_id"]]
        scalar = expected_by_key[(observed["event_id"], observed["horizon"])]
        expected = {key: event[key] for key in observed if key in event}
        expected.update(scalar)
        expected.update(horizon_minutes=int(observed["horizon"]) * int(event["interval_minutes"]),
                        terminal_at=pd.NaT, elapsed_minutes=math.nan,
                        crosses_closure=None, same_session=None,
                        mfe_attainment_end=pd.NaT, mae_attainment_end=pd.NaT)
        if scalar["status"] == "completed":
            position = int(event["signal_idx"])
            following = roster[position + 1:position + int(observed["horizon"]) + 1]
            expected["terminal_at"] = following[-1]["available_at"]
            expected["elapsed_minutes"] = (pd.Timestamp(following[-1]["available_at"]) - pd.Timestamp(event["entry_at"])).total_seconds() / 60
            expected["crosses_closure"] = any(bool(slot["known_closure_before"]) for slot in following)
            expected["same_session"] = all(str(slot["session"]) == str(event["session"]) for slot in following)
            for metric in ("mfe", "mae"):
                first = scalar[metric + "_attainment_start"]
                if pd.notna(first):
                    expected[metric + "_attainment_end"] = next(slot["available_at"] for slot in following if slot["timestamp"] == first)
        if set(observed) - set(expected):
            raise AssertionError("unreconciled output fields: " + str(set(observed) - set(expected)))
        for field, value in observed.items():
            equal(value, expected[field], f"{observed['event_id']}/{observed['horizon']}/{field}")
            checked += 1
    if len(measured) != len(independent) or len(measured) != len(sample) * len(set(horizons)):
        raise AssertionError("selected outcome population mismatch")
    return checked


def main():
    started = time.monotonic()
    if (HERE / "result.json").exists():
        raise ValueError("existing supplemental result must be preserved")
    frozen = json.loads((HERE / "before-execution.json").read_text())
    for record in frozen["checker_sources"] + frozen["settings_and_inputs"]:
        verify_record(record)
    assert_frozen_sources(STAGE, WORKSPACE)
    selector = json.loads((HERE / "selector.json").read_text())
    config = json.loads((STAGE / "config.json").read_text())
    lock = json.loads((STAGE / "inputs.lock.json").read_text())
    delivery = lock["delivery"]
    paths = load_workspace_paths(WORKSPACE)
    verify_record(delivery, paths.publication_root)
    write_new(HERE / "execution-start.json", {"started_at_utc": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv, "cwd": str(Path.cwd()), "before_execution": file_record(HERE / "before-execution.json"),
        "frozen_guard_before": "passed", "selector_identity": file_record(HERE / "selector.json"),
        "runtime": {"executable": sys.executable, "python": sys.version, "platform": platform.platform(),
                    "pandas": importlib.metadata.version("pandas"), "numpy": importlib.metadata.version("numpy"),
                    "pyarrow": importlib.metadata.version("pyarrow"), "locked_without_sync": True}})
    prefix_end = pd.Timestamp(selector["prefix_endpoint_ny"]).tz_convert("UTC")
    cells, output_files = [], []
    for product in selector["products"]:
        five = load_release(paths.publication_root, product=product, interval=5,
            manifest_path=delivery["path"], expected_manifest_sha256=delivery["sha256"], verify_selected_files=True)
        five = five.loc[five.available_at.le(prefix_end)].reset_index(drop=True)
        for interval in selector["interval_minutes"]:
            bars = five if interval == 5 else load_release(paths.publication_root, product=product, interval=3,
                manifest_path=delivery["path"], expected_manifest_sha256=delivery["sha256"], verify_selected_files=True)
            bars = bars.loc[bars.available_at.le(prefix_end)].reset_index(drop=True)
            mapped = map_features(bars, five, interval)
            technical, full_events = generate_events(mapped, interval, config["minimum_width_points"])
            reference_ids = scalar_acceptance(mapped, interval, thresholds=config["minimum_width_points"])
            if reference_ids != full_events.event_id.tolist():
                raise AssertionError(f"{product}/{interval}: full-prefix scalar acceptance mismatch")
            development = full_events.loc[full_events.timestamp.dt.tz_convert("America/New_York").dt.year.eq(2018)]
            sample = development.sort_values(["timestamp", "event_id"], kind="stable").head(selector["accepted_events_per_cell"]).copy()
            if len(sample) < selector["minimum_accepted_events_per_cell"]:
                raise AssertionError(f"{product}/{interval}: no accepted development events in verification prefix")
            # Save the chronological selected roster before viewing any path.
            sample_path = HERE / f"{product}_{interval}m_selected-events.parquet"
            sample.to_parquet(sample_path, index=False, compression="zstd")
            output_files.append(file_record(sample_path))
            horizons = config[f"horizons_{interval}m"]
            outcomes = score_outcomes(mapped, sample, horizons, interval,
                development_start=config["development_start_ny"], endpoint=selector["prefix_endpoint_ny"],
                roster_end_is_endpoint=False)
            # Scalar reference default endpoint is 2021; samples must all have
            # enough prefix support, so no endpoint reinterpretation is needed.
            if outcomes.censor_reason.eq("development_endpoint").any():
                raise AssertionError("selected sample extends beyond frozen verification prefix")
            checked_fields = check_every_outcome_field(mapped, sample, outcomes, horizons)
            sample_slots = set()
            for event in sample.to_dict("records"):
                i = int(event["signal_idx"])
                sample_slots.update(range(i, min(len(technical), i + max(horizons) + 1)))
            path_rows = technical.iloc[sorted(sample_slots)].copy()
            if not path_rows.timestamp.dt.tz_convert("America/New_York").dt.year.eq(2018).all():
                raise AssertionError("sample illustration/outcome path outside 2018")
            for role, frame in (("outcomes", outcomes), ("sample-bars", path_rows)):
                dest = HERE / f"{product}_{interval}m_{role}.parquet"
                frame.to_parquet(dest, index=False, compression="zstd")
                output_files.append(file_record(dest))
            cells.append({"product": product, "interval_minutes": interval, "prefix_slots": len(mapped),
                "full_prefix_accepted": len(full_events), "development_prefix_accepted": len(development),
                "selected_events": len(sample), "selected_first": sample.timestamp.min().isoformat(),
                "selected_last": sample.timestamp.max().isoformat(), "outcome_rows": len(outcomes),
                "completed_by_horizon": {str(h): int(group.status.eq("completed").sum()) for h, group in outcomes.groupby("horizon")},
                "censor_reasons": {str(k): int(v) for k, v in outcomes.loc[outcomes.status.eq("censored"), "censor_reason"].value_counts().items()},
                "every_outcome_field_checked": checked_fields, "full_prefix_scalar_acceptance": "passed",
                "sample_scalar_outcomes": "passed"})
            print(json.dumps(cells[-1]), flush=True)
    assert_frozen_sources(STAGE, WORKSPACE)
    for record in frozen["checker_sources"] + frozen["settings_and_inputs"]:
        verify_record(record)
    for record in output_files:
        verify_record(record)
    write_new(HERE / "result.json", {"status": "passed", "study_id": "21_ema_cloud_trend_follow_opportunity",
        "run_id": STAGE.name, "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - started, "before_execution": file_record(HERE / "before-execution.json"),
        "execution_start": file_record(HERE / "execution-start.json"), "selector": file_record(HERE / "selector.json"),
        "core_source_inventory": file_record(STAGE / "provenance/source-inventory.json"),
        "input_lock": file_record(STAGE / "inputs.lock.json"), "guard_before": "passed", "guard_after": "passed",
        "reserved_outcomes_computed": False, "optional_2010_2017_outcomes_computed": False,
        "selection_uses_outcomes": False, "cells": cells, "output_files": output_files,
        "qualification": "Supplementary support-qualified first min(5, available) chronological acceptance sample only; no parameter/method amendment and no replacement of the zero-event fixed June 4–15 verification slice."})


if __name__ == "__main__":
    main()
