"""Independent saved-table equations and primary sampled-index verification.

No study/research producer imports; no signal/path calculation or result-table writes.
Execute only after a separately retained before-execution input/checker receipt.
"""
from pathlib import Path
import csv
import datetime as dt
import hashlib
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "work/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4"
HERE = Path(__file__).resolve().parent
T0 = time.perf_counter()


def pin(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def rows(name):
    with (RUN / "tables" / name).open(newline="") as file:
        return list(csv.DictReader(file))


def num(value):
    if value in (None, "", "nan", "NaN"):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def equal(actual, expected, field, row_id):
    actual, expected = num(actual), num(expected)
    if actual is None or expected is None:
        assert actual is None and expected is None, (row_id, field, actual, expected)
    else:
        assert math.isclose(actual, expected, rel_tol=2e-10, abs_tol=2e-10), (row_id, field, actual, expected)


def score_key(row, branch=None):
    return tuple(row[k] for k in ("product", "interval_minutes", "direction", "horizon", "unit", "support")) + (branch or row["touch_mode"],)


before = json.loads((HERE / "saved-results-before.json").read_text())
assert pin(Path(__file__)) == before["checker_source"]
for record in before["inputs"]:
    assert pin(Path(record["path"])) == record
config = json.loads((RUN / "config.json").read_text())
score_rows = rows("S2-T02_horizon_scorecard.csv")
contrast = rows("S2-T08_branch_contrasts.csv")
annual = rows("S2-T04_stability.csv")
union = rows("S2-T10_union_overlap.csv")
episode = rows("S2-T09_episode_pairing.csv")
score = {score_key(r): r for r in score_rows}
assert len(score) == len(score_rows) == 1620
assert len({r["row_id"] for r in contrast}) == len(contrast) == 14598
fields = ("product", "interval_minutes", "direction", "horizon", "unit", "support", "metric", "weighting", "block_weeks", "interval_type")
expected_keys = set()
for product in config["products"]:
    for interval in config["interval_minutes"]:
        for h in config[f"horizons_{interval}m"]:
            for side in ("All", "Buy", "Sell"):
                for unit in ("points", "atr"):
                    for support in ("all", "uninterrupted", "same_session"):
                        for metric in ("mfe", "mae", "terminal_delta", "favorable", "mfe_gt_mae"):
                            for weighting in ("event", "session"):
                                expected_keys.add(tuple(map(str, (product, interval, side, h, unit, support, metric, weighting, 0, "descriptive"))))
        for h in ((15, 20, 50) if interval == 3 else (15, 12, 30)):
            for side in ("All", "Buy", "Sell"):
                for unit in ("points", "atr"):
                    for support in ("all", "uninterrupted"):
                        for metric in ("mfe", "mae", "terminal_delta", "favorable", "mfe_gt_mae"):
                            for weighting in ("event", "session"):
                                for block in (1, 4, 8):
                                    key = tuple(map(str, (product, interval, side, h, unit, support, metric, weighting, block)))
                                    expected_keys.add(key + ("pointwise95",))
                                    if (side, h, unit, support, metric, weighting) == ("All", 15, "points", "all", "terminal_delta", "event"):
                                        expected_keys.add(key + ("bonferroni",))
assert {tuple(r[k] for k in fields) for r in contrast} == expected_keys
equations = 0
for row in contrast:
    branch_estimates = {}
    for branch in ("fast", "slow"):
        base = score[score_key(row, branch)]
        metric = row["metric"]
        if metric in ("mfe", "mae", "terminal_delta"):
            column = ("mean_" if row["weighting"] == "event" else "session_mean_") + metric
        else:
            column = ("" if row["weighting"] == "event" else "session_") + metric + "_share"
        branch_estimates[branch] = num(base[column])
        equal(row[branch + "_estimate"], base[column], branch + "_estimate", row["row_id"])
        for saved, original in (("accepted", "accepted"), ("completed", "completed"), ("censored", "censored"),
                                ("evaluable", "evaluable"), ("sessions", "contributing_sessions"), ("weeks", "contributing_weeks")):
            equal(row[branch + "_" + saved], base[original], branch + "_" + saved, row["row_id"])
            equations += 1
        equations += 1
    estimate = branch_estimates["fast"] - branch_estimates["slow"] if all(v is not None for v in branch_estimates.values()) else None
    equal(row["estimate"], estimate, "estimate", row["row_id"])
    equations += 1
    if row["interval_type"] == "descriptive":
        assert row["ci_low"] == row["ci_high"] == ""
    else:
        assert int(float(row["defined_draws"])) + int(float(row["undefined_draws"])) == 10000
        assert int(float(row["resamples"])) == 10000 and int(float(row["seed"])) == 20261010
        low, high = num(row["ci_low"]), num(row["ci_high"])
        assert (low is None and high is None) or low <= high

# All count partition verifies separate side supports; session means are not
# recombined from side-level session counts because a session may contain both.
side_partitions = 0
for row in score_rows:
    if row["direction"] != "All":
        continue
    buy, sell = [score[score_key(row | {"direction": side})] for side in ("Buy", "Sell")]
    for field in ("accepted", "completed", "censored", "evaluable", "normalization_missing"):
        equal(row[field], num(buy[field]) + num(sell[field]), field, row["row_id"])
        side_partitions += 1

# Direct sampled-week-index reference from saved outcomes, separate from
# producer multiplicity-matrix code and saved sufficient-statistic tables.
manifest = json.loads((RUN / "events.manifest.json").read_text())
outcome_records = [r for r in manifest["records"] if r["role"] == "outcomes"]
parts = [pd.read_parquet(r["path"]) for r in outcome_records]
outcomes = pd.concat(parts, ignore_index=True)
local = pd.to_datetime(outcomes.timestamp, utc=True).dt.tz_convert("America/New_York")
assert local.dt.year.between(2018, 2020).all()
assert not outcomes.duplicated(["event_id", "horizon"]).any()
assert (pd.to_datetime(outcomes.terminal_at, utc=True).dropna() <= pd.Timestamp("2021-01-01", tz="America/New_York").tz_convert("UTC")).all()
dates = [dt.date(2018, 1, 1) + dt.timedelta(days=7 * n) for n in range(157)]
week_position = {d.isoformat(): i for i, d in enumerate(dates)}
indices = {}
for block in (1, 4, 8):
    random = np.random.default_rng(20261010)
    starts = random.integers(0, 157, size=(10000, math.ceil(157 / block)))
    indices[block] = ((starts[:, :, None] + np.arange(block)) % 157).reshape(10000, -1)[:, :157]
reference = {}
checked_ci_rows = []
for product in config["products"]:
    for interval in (3, 5):
        for weighting in ("event", "session"):
            branch_draws = {}
            for branch in ("fast", "slow"):
                data = outcomes[(outcomes["product"] == product) & (outcomes.interval_minutes == interval) &
                                (outcomes.horizon == 15) & (outcomes.touch_mode == branch) & (outcomes.status == "completed")]
                data = data[np.isfinite(data[["mfe", "mae", "terminal_delta"]].astype(float)).all(axis=1)]
                if weighting == "event":
                    observations = [(str(w), float(v)) for w, v in zip(data.week, data.terminal_delta)]
                else:
                    sessions = {}
                    for session, value in zip(data.session, data.terminal_delta):
                        sessions.setdefault(str(session), []).append(float(value))
                    observations = []
                    for session, values in sessions.items():
                        date = dt.date.fromisoformat(session)
                        week = (date - dt.timedelta(days=date.weekday())).isoformat()
                        observations.append((week, math.fsum(values) / len(values)))
                buckets = {week: [] for week in week_position}
                for week, value in observations:
                    assert week in buckets
                    buckets[week].append(value)
                sums = np.array([math.fsum(buckets[w]) for w in week_position])
                counts = np.array([len(buckets[w]) for w in week_position])
                for block, sampled in indices.items():
                    denominator = counts[sampled].sum(axis=1)
                    numerator = sums[sampled].sum(axis=1)
                    branch_draws[(branch, block)] = np.divide(numerator, denominator,
                        out=np.full(10000, np.nan), where=denominator > 0)
            for block in (1, 4, 8):
                difference = branch_draws[("fast", block)] - branch_draws[("slow", block)]
                reference[(product, str(interval), weighting, str(block))] = difference[np.isfinite(difference)]
for row in contrast:
    if not (row["direction"] == "All" and row["horizon"] == "15" and row["unit"] == "points" and
            row["support"] == "all" and row["metric"] == "terminal_delta" and row["block_weeks"] != "0"):
        continue
    draws = reference[(row["product"], row["interval_minutes"], row["weighting"], row["block_weeks"])]
    tail = .05 / 12 if row["interval_type"] == "bonferroni" else .025
    low, high = np.quantile(draws, [tail, 1 - tail], method="linear") if len(draws) else (None, None)
    for field, value in (("ci_low", low), ("ci_high", high), ("defined_draws", len(draws)),
                         ("undefined_draws", 10000 - len(draws)), ("tail_low", tail), ("tail_high", 1 - tail)):
        equal(row[field], value, field, row["row_id"])
    checked_ci_rows.append(row["row_id"])
assert len(checked_ci_rows) == 54

frequency = [r for r in union if r["summary_kind"] == "frequency"]
assert len(frequency) == 18
for row in frequency:
    fast, slow, both, total = [num(row[f]) for f in ("fast_accepted", "slow_accepted", "both_accepted", "union_accepted")]
    equal(total, fast + slow - both, "union identity", row["row_id"])
    equal(row["incremental_vs_slow"], total - slow, "incremental", row["row_id"])
    equal(row["incremental_vs_slow"], row["fast_only"], "incremental fast-only", row["row_id"])
    for branch in ("fast", "slow"):
        base = score[score_key(row | {"horizon": "15", "unit": "points", "support": "all"}, branch)]
        equal(row[branch + "_accepted"], base["accepted"], branch + " accepted", row["row_id"])

def subset(row, **criteria):
    return all(row.get(k) == str(v) for k, v in criteria.items())

primary = [r for r in contrast if subset(r, direction="All", horizon=15, unit="points", support="all", metric="terminal_delta", weighting="event")]
branch_h15 = [r for r in score_rows if subset(r, horizon=15, unit="points", support="all")]
annual_h15 = [r for r in annual if subset(r, period_kind="year", direction="All", unit="points", support="all")]
matched = [r for r in contrast if r["horizon"] in (("20", "50") if r["interval_minutes"] == "3" else ("12", "30")) and
           subset(r, direction="All", unit="points", metric="terminal_delta", weighting="event", block_weeks=4, interval_type="pointwise95")]
session_primary = [r for r in contrast if subset(r, direction="All", horizon=15, unit="points", support="all", metric="terminal_delta", weighting="session", block_weeks=4, interval_type="pointwise95")]
pair_summary = [r for r in episode if subset(r, direction="All")]
for record in before["inputs"]:
    assert pin(Path(record["path"])) == record
result = {"status": "passed", "run_id": RUN.name, "command": before["command"],
    "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "runtime_seconds": time.perf_counter() - T0,
    "checker_source": before["checker_source"], "input_pins": before["inputs"],
    "software": {"numpy": np.__version__, "pandas": pd.__version__, "python": sys.version,
        "thread_environment": {k: os.environ.get(k) for k in ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}},
    "checked_scope": {"all_T08_scientific_key_inventory": len(contrast), "all_T08_point_estimate_and_support_equations": equations,
        "All_Buy_Sell_count_partition_equations": side_partitions, "independent_CI_rows": len(checked_ci_rows),
        "independent_CI_row_inventory": checked_ci_rows, "union_frequency_rows": len(frequency),
        "saved_outcome_scope_rows": len(outcomes)},
    "reference_method": "Independent per-event or intact-session reductions from saved outcomes; math.fsum week sums; direct gathered sampled-week indices; full157 weeks; linear percentile tails.",
    "numeric_tolerance": {"relative": 2e-10, "absolute": 2e-10},
    "primary_and_sensitivity_rows": primary, "H15_All_Buy_Sell_event_session_score_rows": branch_h15,
    "H15_session_pointwise_4week_rows": session_primary, "annual_coverage_rows": annual_h15,
    "equal_active_primary_block_secondary_rows": matched, "union_frequency_rows": frequency,
    "episode_All_summary_rows": pair_summary,
    "limits": ["No paths rescored or study producer imported; every original result table/outcome is read-only.",
        "Independent interval recalculation here covers only54 pooledH15/points/all terminal rows: six primary event families95%+Bonferroni at1/4/8weeks and session-balanced95% at1/4/8weeks.",
        "All other paired/inherited interval families require the separately pinned full C independent checker; this receipt does not claim their interval endpoints independently reproduced.",
        "Interpretation/visual/report transfer review is separate from these numerical equations and subset interval calculations."]}
with (HERE / "saved-results-audit.json").open("x") as file:
    json.dump(result, file, indent=2, allow_nan=False)
    file.write("\n")
print(json.dumps({"status": "passed", "contrast_rows": len(contrast), "independent_CI_rows": len(checked_ci_rows),
    "runtime_seconds": result["runtime_seconds"], "receipt": str(HERE / "saved-results-audit.json")}))
