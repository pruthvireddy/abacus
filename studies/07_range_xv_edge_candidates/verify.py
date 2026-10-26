"""Verify staged Range XV evidence before immutable sealing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from src.engine import digest, load_chart, verify_inputs


def check_events(frame: pd.DataFrame, chart: pd.DataFrame) -> dict:
    dates = chart["session_date_proxy"].to_numpy()
    opens = chart["open_tick"].to_numpy()
    directions = chart["direction"].to_numpy()
    strict = chart["strict_completion"].to_numpy()
    checked = 0
    for (idea, cohort, horizon), group in frame.groupby(["idea", "cohort", "horizon_bars"]):
        ordered = group.sort_values("signal_index")
        if ordered["signal_index"].duplicated().any():
            raise AssertionError("duplicate signal in one cohort/horizon")
        previous_exit = -1
        for row in ordered.itertuples(index=False):
            i = int(row.signal_index)
            if not strict[i] or i + 1 >= len(chart) or dates[i + 1] != dates[i]:
                raise AssertionError("signal lacks a completion proxy")
            wait = cohort == "wait_policy"
            entry = i + (2 if wait else 1)
            exit_index = entry + int(horizon)
            if exit_index >= len(chart) or dates[exit_index] != dates[i]:
                raise AssertionError("outcome crosses session")
            if i + 1 <= previous_exit:
                raise AssertionError("overlapping selected opportunity")
            previous_exit = exit_index + (1 if cohort == "early_policy" else 0)
            confirmed = (directions[i + 1] == directions[i] and strict[i + 1] and dates[i + 2] == dates[i]) if wait else True
            if bool(row.traded) != bool(confirmed):
                raise AssertionError("wait confirmation mismatch")
            expected = int(directions[i] * (opens[exit_index] - opens[entry])) if confirmed else 0
            if int(row.return_ticks) != expected:
                raise AssertionError("signed price return mismatch")
            checked += 1
    return {"rows_checked": checked, "cohort_horizons": int(frame.groupby(["idea", "cohort", "horizon_bars"]).ngroups)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    study = Path(__file__).resolve().parent
    stage = root / "work" / study.name / args.run_id
    if not stage.is_dir():
        raise FileNotFoundError(stage)
    protocol = json.loads((stage / "protocol-1.0.1.json").read_text())
    lock = json.loads((stage / "inputs.lock.json").read_text())
    if digest(stage / "protocol-1.0.1.json") != digest(study / "protocol-1.0.1.json"):
        raise ValueError("staged protocol differs from source")
    if digest(stage / "inputs.lock.json") != digest(study / "inputs.lock.json"):
        raise ValueError("staged input lock differs from source")
    verified = verify_inputs(root, lock)
    if verified != json.loads((stage / "input-verification.json").read_text()):
        raise ValueError("input identity changed")
    audit = json.loads((stage / "extraction-audit.json").read_text())
    checks = []
    total_primary = total_secondary = 0
    for record in lock["files"]:
        if not record.get("primary"):
            continue
        product = record["product"]
        chart = load_chart(root / record["path"], protocol["primary_charts"][product]["tick_size"],
                           protocol["excluded_partial_session"])
        primary = pd.read_parquet(stage / f"events_{product}.parquet")
        secondary = pd.read_parquet(stage / f"secondary_{product}.parquet")
        checks.append({"product": product, "primary": check_events(primary, chart),
                       "secondary": check_events(secondary, chart)})
        total_primary += len(primary)
        total_secondary += len(secondary)
        if len(primary) != next(a["event_rows"] for a in audit if a["product"] == product):
            raise AssertionError("audit event count mismatch")
        if (primary["split"] == "excluded_gap").any() and primary.loc[primary["split"] == "excluded_gap", "session_date"].nunique() > 3:
            raise AssertionError("unexpected uncovered date span")
        early = primary.loc[primary["cohort"] == "early_policy", "signal_index"].to_numpy()
        wait = primary.loc[primary["cohort"] == "wait_policy", "signal_index"].to_numpy()
        if not np.array_equal(early, wait):
            raise AssertionError("early and wait policy populations differ")
    metrics = json.loads((stage / "metrics.json").read_text())
    if total_primary != metrics["event_rows"] or total_secondary != metrics["secondary_event_rows"]:
        raise AssertionError("metrics event count mismatch")
    summary = pd.read_csv(stage / "tables/primary_summary.csv")
    if set(summary["product"]) != set(protocol["primary_charts"]):
        raise AssertionError("asset coverage mismatch")
    for path in (stage / "report.md", stage / "report.html", stage / "advice.md"):
        if not path.is_file() or path.stat().st_size < 100:
            raise AssertionError(f"missing report: {path}")
    ET.parse(stage / "figures/two_tick_cost_screen.svg")
    test = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(study / "tests"), "-v"],
                          cwd=root, capture_output=True, text=True, check=False)
    (stage / "focused-tests.log").write_text(test.stdout + test.stderr)
    if test.returncode:
        raise AssertionError("focused tests failed")
    result = {"status": "passed", "run_id": args.run_id, "inputs_verified": len(verified),
              "primary_event_rows": total_primary, "secondary_event_rows": total_secondary,
              "event_checks": checks, "focused_tests": "passed", "svg_xml": "parsed"}
    (stage / "verification-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
