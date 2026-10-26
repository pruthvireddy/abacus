"""Independent verification of already saved contrasts and terminal uncertainty.

No producer imports. Bootstrap references gather explicitly sampled calendar
week indices, rather than multiply a sampled weight matrix. Session observations
are first assembled whole and then assigned by their trading-date Monday.
"""
from datetime import date, datetime, timedelta, timezone
import csv
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sys
import time

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
ROOT = STAGE.parents[2]


def record(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def number(value):
    return float(value) if value != "" else math.nan


def equal(actual, expected, message):
    if math.isnan(actual) or math.isnan(expected):
        require(math.isnan(actual) and math.isnan(expected), message + ": null disagreement")
    else:
        require(math.isclose(actual, expected, rel_tol=5e-12, abs_tol=5e-12),
                message + f": {actual} != {expected}")


def read_csv(name):
    with (STAGE / "tables" / name).open(newline="") as stream:
        return [dict(row, data_row=i, csv_line=i + 1)
                for i, row in enumerate(csv.DictReader(stream), 1)]


def guard(before):
    for item in before["pinned_files"]:
        require(record(Path(item["path"])) == item, "pinned identity changed: " + item["path"])
    inventory = json.loads((STAGE / "provenance/source-inventory.json").read_text())
    for item in inventory["sources"]:
        for path in (ROOT / item["workspace_path"], STAGE / item["snapshot_path"]):
            actual = record(path)
            require(actual["bytes"] == item["bytes"] and actual["sha256"] == item["sha256"],
                    "core source identity changed: " + str(path))


def monday(day):
    return (day - timedelta(days=day.weekday())).isoformat()


def roster():
    result, cursor = [], date(2018, 1, 1)
    while cursor <= date(2020, 12, 28):
        result.append(cursor.isoformat())
        cursor += timedelta(days=7)
    require(len(result) == 157, "development calendar must contain 157 Mondays")
    return result


def sampled_indices(n, block, resamples, seed):
    """Explicit sequential block expansion, including final truncated block."""
    rng = np.random.default_rng(seed)
    blocks = (n + block - 1) // block
    starts = rng.integers(0, n, size=(resamples, blocks))
    sampled = np.empty((resamples, n), dtype=np.int16)
    for position in range(n):
        block_number, within_block = divmod(position, block)
        sampled[:, position] = (starts[:, block_number] + within_block) % n
    return sampled


def linear_percentile(sorted_values, p):
    if not len(sorted_values):
        return math.nan
    position = p * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return float(sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower]))


def interval(draws):
    finite = np.sort(draws[np.isfinite(draws)])
    return {"ci_low": linear_percentile(finite, .025),
            "ci_high": linear_percentile(finite, .975),
            "defined_draws": len(finite), "undefined_draws": len(draws) - len(finite)}


def weekly_reference(records, key, weeks):
    product, candle, side, horizon, unit, weighting = key
    grouped = {}
    for row in records:
        if row["product"] != product or row["interval_minutes"] != candle or row["horizon"] != horizon:
            continue
        if row["status"] != "completed" or (side != "All" and row["side"] != side):
            continue
        metrics = ("mfe", "mae", "terminal_delta") if unit == "points" else ("mfe_atr", "mae_atr", "terminal_delta_atr")
        if not all(pd.notna(row[metric]) for metric in metrics):
            continue
        value = float(row[metrics[-1]])
        require(math.isfinite(value), "nonfinite evaluable terminal observation")
        if weighting == "event":
            week = monday(row["timestamp"].tz_convert("America/New_York").date())
            require(week == row["week"], "saved signal-open week mismatch")
            grouped.setdefault(week, []).append(value)
        else:
            grouped.setdefault(str(row["session"]), []).append(value)
    if weighting == "session":
        whole_sessions = grouped
        grouped = {}
        for session, values in whole_sessions.items():
            week = monday(date.fromisoformat(session))
            grouped.setdefault(week, []).append(math.fsum(values) / len(values))
    require(set(grouped).issubset(weeks), "observation assigned outside frozen calendar")
    totals = np.array([math.fsum(grouped.get(week, [])) for week in weeks], dtype=np.float64)
    counts = np.array([len(grouped.get(week, [])) for week in weeks], dtype=np.int64)
    estimate = math.fsum(totals) / int(counts.sum()) if counts.sum() else math.nan
    return totals, counts, estimate


def main():
    began = time.monotonic()
    before = json.loads((HERE / "comparisons-uncertainty-before.json").read_text())
    guard(before)
    config = json.loads((STAGE / "config.json").read_text())
    boot_config = config["bootstrap"]
    require(boot_config["resamples"] == 10000 and boot_config["seed"] == 20261010, "frozen draw definition")
    score = read_csv("S1-T02_horizon_scorecard.csv")
    score_lookup = {(r["product"], int(r["interval_minutes"]), r["direction"], int(r["horizon"]),
                     r["unit"], r["support"]): r for r in score}
    require(len(score_lookup) == len(score), "duplicate scorecard lookup key")
    comparisons = read_csv("S1-comparisons.csv")
    comparison_receipts = []
    comparison_fields = 0
    for observed in comparisons:
        a = score_lookup[(observed["product"], 3, observed["direction"], int(observed["horizon_a"]), observed["unit"], observed["support"])]
        b = score_lookup[(observed["product"], 5, observed["direction"], int(observed["horizon_b"]), observed["unit"], observed["support"])]
        expected = {"interval_a": 3, "interval_b": 5,
                    "minutes_a": 3 * int(observed["horizon_a"]), "minutes_b": 5 * int(observed["horizon_b"]),
                    "completed_a": number(a["completed"]), "completed_b": number(b["completed"]),
                    "sessions_a": number(a["contributing_sessions"]), "sessions_b": number(b["contributing_sessions"])}
        for metric in ("mfe", "mae", "terminal_delta"):
            for prefix in ("mean_", "session_mean_"):
                field = "difference_" + prefix + metric
                expected[field] = number(a[prefix + metric]) - number(b[prefix + metric])
        for field, value in expected.items():
            equal(number(observed[field]), float(value), observed["row_id"] + "/" + field)
            comparison_fields += 1
        comparison_receipts.append({"row_id": observed["row_id"], "data_row": observed["data_row"],
            "source_a": {"row_id": a["row_id"], "data_row": a["data_row"]},
            "source_b": {"row_id": b["row_id"], "data_row": b["data_row"]},
            "independent_expected_fields": expected})
    print(json.dumps({"comparison_rows": len(comparisons), "comparison_fields": comparison_fields}), flush=True)
    manifest = json.loads((STAGE / "events.manifest.json").read_text())
    outcome_records = []
    outcomes_pins = []
    for item in manifest["records"]:
        if item["role"] != "outcomes":
            continue
        path = Path(item["path"])
        require(record(path)["sha256"] == item["sha256"], "outcome manifest pin mismatch")
        frame = pd.read_parquet(path)
        require(len(frame) == item["row_count"], "outcome manifest row mismatch")
        require(frame.timestamp.dt.tz_convert("America/New_York").dt.year.between(2018, 2020).all(), "reserved outcome record")
        outcome_records.extend(frame.to_dict("records"))
        outcomes_pins.append(record(path))
    bootstrap = read_csv("S1-bootstrap.csv")
    primary_rows = [r for r in bootstrap if r["kind"] == "cohort" and r["horizon"] == "15" and
                    r["weighting"] == "session" and r["metric"] == "terminal_delta"]
    paired_rows = [r for r in bootstrap if r["kind"] == "contrast" and
                   r["comparison"].startswith("equal_active") and r["metric"] == "terminal_delta"]
    require(len(primary_rows) == 108 and len(paired_rows) == 216, "frozen supplemental CI family counts")
    selected_rows = primary_rows + paired_rows
    weeks = roster()
    keys = set()
    for row in selected_rows:
        require(row["support"] == "all", "unexpected support family")
        if row["kind"] == "cohort":
            keys.add((row["product"], int(row["interval_minutes"]), row["direction"], int(row["horizon"]), row["unit"], row["weighting"]))
        else:
            keys.add((row["product"], 3, row["direction"], int(row["horizon_a"]), row["unit"], row["weighting"]))
            keys.add((row["product"], 5, row["direction"], int(row["horizon_b"]), row["unit"], row["weighting"]))
    weekly = {key: weekly_reference(outcome_records, key, weeks) for key in sorted(keys)}
    ci_receipts, index_receipts = [], []
    max_error = 0.0
    for block in (1, 4, 8):
        indices = sampled_indices(len(weeks), block, boot_config["resamples"], boot_config["seed"])
        index_receipts.append({"block_weeks": block, "shape": list(indices.shape), "dtype": str(indices.dtype),
            "sha256_c_order_bytes": hashlib.sha256(indices.tobytes(order="C")).hexdigest(),
            "first_draw_week_indices": indices[0].tolist()})
        draws_by_key = {}
        for key, (totals, counts, estimate) in weekly.items():
            numerator = totals[indices].sum(axis=1)
            denominator = counts[indices].sum(axis=1)
            draws = np.full(len(indices), np.nan, dtype=np.float64)
            np.divide(numerator, denominator, out=draws, where=denominator > 0)
            draws_by_key[key] = draws
        for observed in selected_rows:
            if int(observed["block_weeks"]) != block:
                continue
            if observed["kind"] == "cohort":
                key = (observed["product"], int(observed["interval_minutes"]), observed["direction"],
                       int(observed["horizon"]), observed["unit"], observed["weighting"])
                expected = {"estimate": weekly[key][2]} | interval(draws_by_key[key])
            else:
                a = (observed["product"], 3, observed["direction"], int(observed["horizon_a"]), observed["unit"], observed["weighting"])
                b = (observed["product"], 5, observed["direction"], int(observed["horizon_b"]), observed["unit"], observed["weighting"])
                expected = {"estimate": weekly[a][2] - weekly[b][2]} | interval(draws_by_key[a] - draws_by_key[b])
            expected.update(resamples=10000, seed=20261010, block_weeks=block)
            for field, value in expected.items():
                actual = number(observed[field])
                equal(actual, float(value), observed["row_id"] + "/" + field)
                if math.isfinite(actual) and math.isfinite(value):
                    max_error = max(max_error, abs(actual - value))
            ci_receipts.append({"row_id": observed["row_id"], "data_row": observed["data_row"],
                                "independent_expected_fields": expected})
        print(json.dumps({"block_weeks": block, "cumulative_ci_rows": len(ci_receipts),
                          "weekly_reference_cohorts": len(weekly), "maximum_absolute_error": max_error}), flush=True)
    guard(before)
    for item in outcomes_pins:
        require(record(Path(item["path"])) == item, "saved outcomes changed during check")
    selected_ids = {r["row_id"] for r in selected_rows}
    unverified = {}
    for row in bootstrap:
        if row["row_id"] not in selected_ids:
            family = "|".join((row["kind"], row["comparison"] or "cohort", row["metric"], row["weighting"]))
            unverified[family] = unverified.get(family, 0) + 1
    output = {"status": "passed", "run_id": STAGE.name,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.monotonic() - began,
        "before_execution": record(HERE / "comparisons-uncertainty-before.json"),
        "runtime": {"argv": sys.argv, "cwd": str(Path.cwd()), "executable": sys.executable,
          "python": sys.version, "platform": platform.platform(),
          "pandas": importlib.metadata.version("pandas"), "numpy": importlib.metadata.version("numpy"),
          "pyarrow": importlib.metadata.version("pyarrow"), "locked_without_sync": True},
        "source_guard_before": "passed", "source_guard_after": "passed", "outcomes_identities": outcomes_pins,
        "producer_modules_imported": False, "reserved_outcomes_computed_or_examined": False,
        "comparison_rows_checked": len(comparisons), "comparison_fields_checked": comparison_fields,
        "primary_session_terminal_ci_rows_checked": len(primary_rows),
        "paired_equal_active_terminal_ci_rows_checked": len(paired_rows),
        "bootstrap_total_rows": len(bootstrap), "bootstrap_rows_checked_by_this_checker": len(ci_receipts),
        "bootstrap_rows_unverified_by_this_checker": len(bootstrap) - len(ci_receipts),
        "unverified_uncertainty_families_by_this_checker": unverified,
        "maximum_absolute_numeric_error": max_error,
        "reference_method": "Explicit sampled 157-week calendar indices shared across every cohort; direct gathered weekly observations; whole contributing-session means assigned by trading-date Monday; manually interpolated sorted percentile ranks.",
        "calendar_weeks": weeks, "sampled_index_receipts": index_receipts,
        "scope_qualification": "All 486 saved comparison rows checked against exact scorecard sources. Supplemental CI scope is every product, All/Buy/Sell, points/ATR, all1/4/8 blocks: H15 session terminal and both event/session equal-active60/150 terminal contrasts. Other CI families are not certified by this checker; the main C receipt is separate.",
        "comparison_row_receipts": comparison_receipts, "uncertainty_row_receipts": ci_receipts}
    with (HERE / "comparisons-uncertainty-result.json").open("x") as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
