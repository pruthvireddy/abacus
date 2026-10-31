"""Study-owned aggregation and saved-evidence rendering for ES pivot behavior.

The numerical phase calls ``write_statistics`` once from complete engine
ledgers. ``render`` reads only saved summaries. Narada export is separate and
also reads saved evidence only; the browser never aggregates research rows.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date, datetime
import hashlib
import html
import json
import math
from pathlib import Path
import subprocess

import numpy as np

SID = "30_verniman_pivot_statistics_es"
CUTOFF = "2026-10-30"
START = "2020-01-01"
SECTIONS = ("opening_range", "new_york_am", "new_york_pm")
PANELS = ("all_crosses", "first_per_day", "first_per_section")
HORIZONS = ("15m", "30m", "60m", "section_end", "day_end")
SCHEDULED_SNAPSHOTS = frozenset(("0925", "0930", "opening_range_end", "new_york_am_end", "new_york_pm_end"))
CONDITIONS = (
    "ema_state_at_cross", "confirmation_kind", "cloud_order",
    "price_cloud_location", "pivot_cloud_location", "vwap_side_relative_pivot",
    "price_side_relative_vwap", "ema6_slope_sign",
    "actual_ema_cross_at_reference", "ema_cloud_aligned", "ema_vwap_aligned",
    "ema_cloud_vwap_aligned",
)
LIMITS = (
    "Repository-retained ES data only; requested coverage ends 2026-10-30, "
    "while retained market data ends 2026-09-18. Missing dates/contracts and "
    "retrospective full-day eligibility limit generalization.",
    "Historical pivot available_at remains unverified. Nominal 09:25 timing "
    "does not establish a historically executable pre-open signal.",
    "Returned-without-EMA and eventual confirmation labels are known later. "
    "Already-aligned EMA6 is distinct from an actual new line crossing.",
    "Signed displacement and excursions describe price paths. No entries, "
    "fills, costs or net profitability are tested. Broad slices are exploratory.",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    return value


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(clean(value), ensure_ascii=False, indent=2,
                                    allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows):
    """Preserve booleans, observed zero and null (empty cell) without NaN."""
    rows = [clean(dict(r)) for r in rows]
    columns = list(dict.fromkeys(k for row in rows for k in row)) or ["session_date"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, separators=(",", ":"), ensure_ascii=False)
                             if isinstance(v, (dict, list)) else v for k, v in row.items()})
    return columns


def csv_value(raw):
    if raw == "":
        return None
    if raw == "True":
        return True
    if raw == "False":
        return False
    # Dates, periods, IDs and labels remain strings. Only canonical numeric
    # serialization is converted; integer-looking period columns are handled
    # separately by read_csv's explicit textual fields.
    try:
        result = float(raw)
    except ValueError:
        return raw
    require(math.isfinite(result), "Non-finite saved CSV number")
    return int(result) if result.is_integer() else result


TEXT_COLUMNS = {
    "session_date", "period", "period_kind", "panel", "direction", "section",
    "condition", "condition_value", "event_type", "horizon", "metric",
    "earliest_session", "latest_session", "requested_cutoff", "from_section",
    "to_section", "from_state", "to_state", "state", "snapshot", "category",
}


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return [{k: (v if k in TEXT_COLUMNS and v != "" else csv_value(v))
                 for k, v in row.items()} for row in csv.DictReader(stream)]


def number(value):
    return isinstance(value, (int, float, np.number)) and not isinstance(value, bool) and math.isfinite(float(value))


def describe(values):
    values = np.asarray([float(v) for v in values if number(v)], dtype=float)
    if not len(values):
        return {"mean": None, "median": None, "p25": None, "p75": None, "p90": None}
    q = np.quantile(values, [0.25, 0.5, 0.75, 0.9])
    return {"mean": float(values.mean()), "median": float(q[1]), "p25": float(q[0]),
            "p75": float(q[2]), "p90": float(q[3])}


def period_windows(days, start=START, cutoff=CUTOFF):
    """Calendar windows include empty months; recent windows use eligible days."""
    days = sorted(set(str(d) for d in days if start <= str(d) <= cutoff))
    windows = [("overall", "all", set(days))]
    for year in range(int(start[:4]), int(cutoff[:4]) + 1):
        windows.append(("year", str(year), {d for d in days if d[:4] == str(year)}))
    year, month = int(start[:4]), int(start[5:7])
    while f"{year:04d}-{month:02d}" <= cutoff[:7]:
        label = f"{year:04d}-{month:02d}"
        windows.append(("calendar_month", label, {d for d in days if d[:7] == label}))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    for month in range(1, 13):
        label = f"{month:02d}"
        windows.append(("month_of_year", label, {d for d in days if d[5:7] == label}))
    for n in (20, 60, 120):
        windows.append(("recent", f"last_{n}", set(days[-n:])))
    return windows


def block_weights(days, replicates=2000, block=5, seed=20261031):
    """Non-circular moving blocks of chronological observed sessions.

    Draw complete within-day records by integer day multiplicities. All
    conditional groups reuse these weights, rather than resampling only days
    that happened to produce a selected event.
    """
    n = len(days)
    if n <= block or replicates <= 0:
        return None
    b = min(block, n)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n - b + 1, size=(replicates, math.ceil(n / b)))
    indices = (starts[..., None] + np.arange(b)).reshape(replicates, -1)[:, :n]
    weights = np.zeros((replicates, n), dtype=float)
    np.add.at(weights, (np.repeat(np.arange(replicates), n), indices.ravel()), 1)
    return weights


def bootstrap_ratio(rows, value_key, days, weights, predicate=None):
    if weights is None:
        return None, None
    if len({r["session_date"] for r in rows if number(r.get(value_key)) or isinstance(r.get(value_key), bool)}) < 2:
        return None, None
    positions = {d: i for i, d in enumerate(days)}
    sums = np.zeros(len(days), dtype=float)
    counts = np.zeros(len(days), dtype=float)
    for row in rows:
        value = row.get(value_key)
        if number(value) or isinstance(value, bool):
            if row["session_date"] in positions:
                i = positions[row["session_date"]]
                sums[i] += float(predicate(value) if predicate else value)
                counts[i] += 1
    top, bottom = weights @ sums, weights @ counts
    results = top[bottom > 0] / bottom[bottom > 0]
    if not len(results):
        return None, None
    return tuple(float(v) for v in np.quantile(results, [0.025, 0.975]))


def base_row(kind, period, rows, *, panel="all_crosses", direction="all", section="all", condition="all", condition_value="all"):
    dates = sorted({r["session_date"] for r in rows})
    return {"period_kind": kind, "period": period, "panel": panel, "direction": direction,
            "section": section, "condition": condition, "condition_value": str(condition_value),
            "condition_timing": "retrospective_episode" if condition == "confirmation_kind" else "reference_time" if condition != "all" else "unconditional",
            "days": len(dates), "sparse": len(dates) < 30,
            "earliest_session": dates[0] if dates else None,
            "latest_session": dates[-1] if dates else None, "requested_cutoff": CUTOFF}


def panel_rows(rows, panel):
    return list(rows) if panel == "all_crosses" else [r for r in rows if r.get(panel) is True]


def group_selections(rows):
    """One-way section or direction panels, not an unbounded Cartesian cube."""
    yield "all", "all", list(rows)
    for direction, label in ((1, "up"), (-1, "down")):
        yield label, "all", [r for r in rows if r.get("direction") == direction]
    for section in SECTIONS:
        yield "all", section, [r for r in rows if r.get("section") == section]


def attach_context(ledgers):
    events = {r["event_id"]: r for key in ("price_events", "ema_events") for r in ledgers.get(key, [])}
    result = []
    for raw in ledgers.get("outcomes", []):
        row = {**events.get(raw.get("event_id"), {}), **raw}
        slope = row.get("ema6_slope_15m")
        row["ema6_slope_sign"] = "positive" if number(slope) and slope > 0 else "negative" if number(slope) and slope < 0 else "zero" if number(slope) else "unknown"
        actual = row.get("event_type") in ("ema_cross", "ema_confirmation") or row.get("ema_state_at_cross") == "same_close_actual_crossing"
        direction = row.get("direction")
        ema_side = direction if row.get("event_type") in ("ema_cross", "ema_confirmation") else row.get("ema_raw_side")
        ema_agrees = None if ema_side is None else ema_side == direction
        cloud = row.get("cloud_order")
        cloud_agrees = None if cloud not in ("bullish", "bearish", "flat") else cloud == ("bullish" if direction == 1 else "bearish")
        slopes = [row.get(key) for key in ("ema20_slope_15m", "ema50_slope_15m")]
        slopes_agree = None if not all(number(value) for value in slopes) else all(direction * value > 0 for value in slopes)
        relative_vwap = row.get("price_side_relative_vwap")
        vwap_agrees = None if relative_vwap is None else relative_vwap == direction
        row["actual_ema_cross_at_reference"] = actual
        row["ema_cloud_aligned"] = None if any(value is None for value in (ema_agrees, cloud_agrees, slopes_agree)) else all((ema_agrees, cloud_agrees, slopes_agree))
        row["ema_vwap_aligned"] = None if any(value is None for value in (ema_agrees, vwap_agrees)) else all((ema_agrees, vwap_agrees))
        row["ema_cloud_vwap_aligned"] = None if row["ema_cloud_aligned"] is None or row["ema_vwap_aligned"] is None else row["ema_cloud_aligned"] and row["ema_vwap_aligned"]
        ref = row.get("reference_price")
        displacement = row.get("displacement_points")
        row["displacement_bps"] = 10000 * displacement / ref if number(ref) and ref > 0 and number(displacement) else None
        for side in ("favorable", "adverse"):
            points = row.get(side + "_excursion_points")
            row[side + "_excursion_bps"] = 10000 * points / ref if number(ref) and ref > 0 and number(points) else None
        result.append(row)
    return result


def daily_summaries(ledgers, windows, days, weights):
    metric_keys = (
        "price_crosses", "price_crosses_up", "price_crosses_down", "ema_crosses",
        "ema_crosses_up", "ema_crosses_down", "touch_bars", "occupancy_above_share",
        "occupancy_below_share", "occupancy_equal_share", "longest_above_run_3m",
        "longest_below_run_3m", "opening_gap_points", "opening_gap_bps",
        "cloud_order_changes", "cloud_width_mean", "cloud_width_min", "cloud_width_max",
        "price_crosses_per_hour", "ema_crosses_per_hour",
    )
    output = []
    for kind, period, selected in windows:
        for section in ("all", *SECTIONS):
            source = ledgers.get("daily", []) if section == "all" else [r for r in ledgers.get("sections", []) if r.get("section") == section]
            rows = [r for r in source if r["session_date"] in selected]
            for metric in metric_keys:
                # Optional context fields remain absent rather than invented.
                if metric not in {"price_crosses", "ema_crosses", "touch_bars"} and not any(metric in r for r in source):
                    continue
                valid = [r for r in rows if number(r.get(metric))]
                values = [r[metric] for r in valid]
                stats = describe(values)
                low, high = bootstrap_ratio(valid, metric, days, weights) if kind == "overall" else (None, None)
                item = base_row(kind, period, rows, section=section)
                item.update(metric=metric, denominator=len(valid), unknown=len(rows) - len(valid),
                            sparse=len(valid) < 30,
                            numerator=float(sum(values)) if values else 0,
                            estimate=stats.pop("mean"), zero_count=sum(v == 0 for v in values),
                            zero_share=sum(v == 0 for v in values) / len(values) if values else None,
                            ci95_low=low, ci95_high=high, **stats)
                output.append(item)
    return output


def outcome_record(rows, base, days, weights, bootstrap=False):
    valid = [r for r in rows if r.get("valid") is True and number(r.get("displacement_points"))]
    values = [r["displacement_points"] for r in valid]
    stats = describe(values)
    low, high = bootstrap_ratio(valid, "displacement_points", days, weights) if bootstrap else (None, None)
    plow, phigh = bootstrap_ratio(valid, "displacement_points", days, weights, lambda v: v > 0) if bootstrap else (None, None)
    item = {**base, "events": len(rows), "denominator": len(valid), "unknown": len(rows) - len(valid),
            "valid_days": len({r["session_date"] for r in valid}),
            "sparse": len({r["session_date"] for r in valid}) < 30,
            "mean_points": stats["mean"], "median_points": stats["median"],
            "p25_points": stats["p25"], "p75_points": stats["p75"], "p90_points": stats["p90"],
            "positive_count": sum(v > 0 for v in values), "zero_count": sum(v == 0 for v in values),
            "negative_count": sum(v < 0 for v in values),
            "positive_rate": sum(v > 0 for v in values) / len(values) if values else None,
            "mean_ci95_low": low, "mean_ci95_high": high,
            "positive_ci95_low": plow, "positive_ci95_high": phigh}
    for source, target in (("favorable_excursion_points", "mean_favorable_points"),
                           ("adverse_excursion_points", "mean_adverse_points"),
                           ("favorable_excursion_bps", "mean_favorable_bps"),
                           ("adverse_excursion_bps", "mean_adverse_bps"),
                           ("displacement_bps", "mean_bps"), ("elapsed_minutes", "mean_elapsed_minutes")):
        item[target] = describe([r.get(source) for r in valid])["mean"]
    for side in ("favorable", "adverse"):
        for threshold in (5, 10, 20):
            key = f"{side}_reach_{threshold}"
            flags = [r[key] for r in valid if isinstance(r.get(key), bool)]
            item[key + "_count"] = sum(flags)
            item[key + "_denominator"] = len(flags)
            item[key + "_rate"] = sum(flags) / len(flags) if flags else None
    return item


def outcome_summaries(ledgers, windows, days, weights):
    rows = attach_context(ledgers)
    output = []
    by_date = defaultdict(list)
    for row in rows:
        by_date[row["session_date"]].append(row)
    for kind, period, selected in windows:
        period_rows = [r for d in selected for r in by_date[d]]
        for event_type in ("price_cross", "ema_cross", "ema_confirmation"):
            typed = [r for r in period_rows if r.get("event_type") == event_type]
            for panel in PANELS:
                # Supplemental EMA calendar panels retain the main 30m window;
                # all horizons and event panels are present in overall results.
                if kind != "overall" and event_type != "price_cross" and panel != "all_crosses":
                    continue
                picked = panel_rows(typed, panel)
                for direction, section, group in group_selections(picked):
                    for horizon in HORIZONS if kind == "overall" or event_type == "price_cross" else ("30m",):
                        subset = [r for r in group if r.get("horizon") == horizon]
                        if not subset:
                            continue
                        base = base_row(kind, period, subset, panel=panel, direction=direction, section=section)
                        base.update(event_type=event_type, horizon=horizon)
                        output.append(outcome_record(subset, base, days, weights, kind == "overall" and horizon == "30m"))
        if kind != "overall":
            continue
        for event_type in ("price_cross", "ema_cross", "ema_confirmation"):
            typed = [r for r in period_rows if r.get("event_type") == event_type and r.get("horizon") == "30m"]
            for panel in PANELS:
                picked = panel_rows(typed, panel)
                for condition in CONDITIONS:
                    values = sorted({str(r.get(condition) if r.get(condition) is not None else "unknown") for r in picked})
                    for value in values:
                        subset = [r for r in picked if str(r.get(condition) if r.get(condition) is not None else "unknown") == value]
                        base = base_row(kind, period, subset, panel=panel, condition=condition, condition_value=value)
                        base.update(event_type=event_type, horizon="30m")
                        output.append(outcome_record(subset, base, days, weights, True))
    return output


def episode_summaries(ledgers, windows):
    events = []
    for source in ledgers.get("price_events", []):
        row = dict(source)
        state = row.get("ema_state_at_cross")
        row["initial_confirmation_state"] = "initially_unconfirmed" if state in ("opposite", "equal_with_remembered_side", "unavailable_uninitialized") else "already_aligned" if state == "already_aligned" else "same_close_actual_crossing" if state == "same_close_actual_crossing" else "unknown"
        events.append(row)
    output = []
    for kind, period, selected in windows:
        source = [r for r in events if r["session_date"] in selected]
        for panel in PANELS:
            picked = panel_rows(source, panel)
            for direction, section, group in group_selections(picked):
                groups = [("all", "all", group)]
                if kind == "overall" and direction == "all" and section == "all":
                    for key in ("ema_state_at_cross", "initial_confirmation_state", "confirmation_kind"):
                        for value in sorted({str(r.get(key) if r.get(key) is not None else "unknown") for r in group}):
                            groups.append((key, value, [r for r in group if str(r.get(key) if r.get(key) is not None else "unknown") == value]))
                for condition, value, subset in groups:
                    if not subset:
                        continue
                    returned = [r for r in subset if r.get("returned_at")]
                    confirmed = [r for r in subset if r.get("confirmation_at")]
                    returned_without = [r for r in returned if not r.get("confirmation_at")]
                    censored = [r for r in subset if r.get("return_censored") is True]
                    known_confirmation = len(confirmed) + len(returned_without)
                    item = base_row(kind, period, subset, panel=panel, direction=direction, section=section,
                                    condition=condition, condition_value=value)
                    item.update(events=len(subset), returned=len(returned), return_censored=len(censored),
                                actual_confirmed=len(confirmed), returned_without_new_cross=len(returned_without),
                                confirmation_denominator=known_confirmation,
                                returned_without_new_cross_rate=len(returned_without) / known_confirmation if known_confirmation else None,
                                unknown_or_censored_confirmation=len(subset) - known_confirmation,
                                actual_confirmation_rate=len(confirmed) / known_confirmation if known_confirmation else None,
                                mean_returned_unconfirmed_penetration_points=describe([r.get("episode_penetration_points") for r in returned_without])["mean"],
                                mean_penetration_points=describe([r.get("episode_penetration_points") for r in subset])["mean"],
                                median_penetration_points=describe([r.get("episode_penetration_points") for r in subset])["median"],
                                mean_confirmation_lag_minutes=describe([r.get("confirmation_lag_minutes") for r in confirmed])["mean"],
                                mean_returned_duration_minutes=describe([r.get("episode_duration_minutes") for r in returned])["mean"])
                    output.append(item)
    return output


def retest_summaries(ledgers, windows):
    events = ledgers.get("ema_events", [])
    output = []
    for kind, period, selected in windows:
        picked = [r for r in events if r["session_date"] in selected]
        for direction, section, group in group_selections(picked):
            if not group:
                continue
            found = [r for r in group if r.get("retest_found") is True]
            known = [r for r in group if isinstance(r.get("retest_found"), bool)]
            complete = [r for r in group if r.get("retest_window_complete") is True]
            # A positive observed touch is factual even in a shorter window;
            # incidence uses full-window observations only to avoid bias.
            complete_touch = [r for r in complete if r.get("retest_found") is True]
            item = base_row(kind, period, group, direction=direction, section=section)
            item.update(events=len(group), observed_touches=len(found), complete_windows=len(complete),
                        complete_window_touches=len(complete_touch), unknown=len(group) - len(known),
                        censored=len(group) - len(complete),
                        touch_rate=len(complete_touch) / len(complete) if complete else None,
                        mean_touch_minutes=describe([r.get("time_to_retest_minutes") for r in found])["mean"])
            for state in ("hold", "failed", "equal"):
                n = sum(r.get("retest_close_classification") == state for r in found)
                item[state + "_count"] = n
                item[state + "_rate"] = n / len(found) if found else None
            output.append(item)
    return output


def transition_summaries(ledgers):
    rows = ledgers.get("sections", [])
    by_day = defaultdict(dict)
    for row in rows:
        by_day[row["session_date"]][row.get("section")] = row
    counts = Counter()
    for sections in by_day.values():
        for left, right in zip(SECTIONS, SECTIONS[1:]):
            if left not in sections or right not in sections:
                continue
            for key, source_key in (("closing_side", "end_price_side_relative_pivot"), ("cloud_order_end", "end_cloud_order")):
                a, b = sections[left].get(source_key), sections[right].get(source_key)
                if a is not None and b is not None:
                    counts[(left, right, key, str(a), str(b))] += 1
    result = []
    for (left, right, metric, a, b), n in sorted(counts.items()):
        denominator = sum(v for (l, r, m, source, _), v in counts.items() if (l, r, m, source) == (left, right, metric, a))
        result.append({"from_section": left, "to_section": right, "metric": metric,
                       "from_state": a, "to_state": b, "days": n,
                       "denominator": denominator, "rate": n / denominator,
                       "sparse": denominator < 30})
    return result


def opening_summaries(ledgers, windows):
    snapshots = [r for r in ledgers.get("snapshots", []) if r.get("snapshot_label") in ("0925", "0930")]
    result = []
    keys = ("cloud_order", "price_cloud_location", "pivot_cloud_location", "price_side_relative_pivot", "ema6_side_relative_pivot", "vwap_side_relative_pivot")
    for kind, period, selected in windows:
        for snapshot in sorted({str(r.get("snapshot_label")) for r in snapshots}):
            source = [r for r in snapshots if r["session_date"] in selected and str(r.get("snapshot_label")) == snapshot]
            for metric in keys:
                counts = Counter(str(r.get(metric)) if r.get(metric) is not None else "unknown" for r in source)
                for category, n in sorted(counts.items()):
                    result.append({"period_kind": kind, "period": period, "snapshot": snapshot,
                                   "metric": metric, "category": category, "days": n,
                                   "denominator": len(source), "rate": n / len(source),
                                   "sparse": n < 30, "requested_cutoff": CUTOFF})
    return result


def snapshot_numeric_summaries(ledgers, windows):
    snapshots = [row for row in ledgers.get("snapshots", []) if row.get("snapshot_label") in SCHEDULED_SNAPSHOTS]
    fields = ("price_minus_pivot", "ema6_minus_pivot", "vwap_minus_pivot",
              "cloud_lower_minus_pivot", "cloud_upper_minus_pivot", "price_minus_vwap",
              "price_minus_ema6", "cloud_width", "cloud_spread", "cloud_width_change_15m",
              "ema6_slope_15m", "ema20_slope_15m", "ema50_slope_15m", "vwap_slope_15m")
    result = []
    for kind, period, selected in windows:
        # Full calendar detail is already in retained snapshots. These numeric
        # contextual distributions cover overall/year/recent, keeping the
        # presentation set bounded rather than multiplying every dimension.
        if kind not in ("overall", "year", "recent"):
            continue
        for snapshot in sorted({str(r.get("snapshot_label")) for r in snapshots}):
            source = [r for r in snapshots if r["session_date"] in selected and str(r.get("snapshot_label")) == snapshot]
            for metric in fields:
                for unit in ("points", "bps_of_pivot"):
                    values = []
                    for row in source:
                        value, pivot = row.get(metric), row.get("pivot")
                        if number(value) and (unit == "points" or number(pivot) and pivot > 0):
                            values.append(float(value) if unit == "points" else 10000 * value / pivot)
                    stats = describe(values)
                    result.append({"period_kind": kind, "period": period, "snapshot": snapshot,
                                   "metric": metric, "unit": unit, "denominator": len(values),
                                   "unknown": len(source) - len(values), "estimate": stats.pop("mean"),
                                   **stats, "sparse": len(values) < 30, "requested_cutoff": CUTOFF})
    return result


def summarize(ledgers, *, bootstrap_replicates=2000, bootstrap_seed=20261031, start=START, cutoff=CUTOFF):
    ledgers = {key: [dict(row) for row in rows] for key, rows in ledgers.items()}
    for row in ledgers.get("daily", []):
        gap, pivot = row.get("opening_gap_points"), row.get("pivot")
        row["opening_gap_bps"] = 10000 * gap / pivot if number(gap) and number(pivot) and pivot > 0 else None
    days = sorted({r["session_date"] for r in ledgers.get("daily", [])})
    require(all(start <= d <= cutoff for d in days), "Daily ledger outside requested calendar")
    require(len(days) == len(ledgers.get("daily", [])), "Duplicate daily rows")
    windows = period_windows(days, start, cutoff)
    weights = block_weights(days, bootstrap_replicates, 5, bootstrap_seed)
    return {"daily_summary": daily_summaries(ledgers, windows, days, weights),
            "outcome_summary": outcome_summaries(ledgers, windows, days, weights),
            "episode_summary": episode_summaries(ledgers, windows),
            "retest_summary": retest_summaries(ledgers, windows),
            "opening_summary": opening_summaries(ledgers, windows),
            "snapshot_numeric_summary": snapshot_numeric_summaries(ledgers, windows),
            "section_transitions": transition_summaries(ledgers)}


def write_statistics(stage, ledgers, *, bootstrap_replicates=2000, bootstrap_seed=20261031):
    stage = Path(stage)
    tables = summarize(ledgers, bootstrap_replicates=bootstrap_replicates, bootstrap_seed=bootstrap_seed)
    for name, rows in tables.items():
        target = stage / "tables" / f"{name}.csv"
        require(not target.exists(), f"Refusing to overwrite saved statistics: {target}")
        write_csv(target, rows)
    dates = sorted(r["session_date"] for r in ledgers.get("daily", []))
    coverage = [{"requested_start": START, "requested_cutoff": CUTOFF,
                 "retained_market_data_end": "2026-09-18",
                 "requested_calendar_dates": (date.fromisoformat(CUTOFF) - date.fromisoformat(START)).days + 1,
                 "eligible_sessions": len(dates), "actual_eligible_start": dates[0] if dates else None,
                 "actual_eligible_end": dates[-1] if dates else None,
                 "historical_availability": "unverified",
                 "scope": "Calendar dates include nontrading days; eligible sessions are a selected sample, not all requested dates. Detailed reasons are retained in the run's source/eligibility audit."}]
    coverage_target = stage / "tables/coverage_summary.csv"
    require(not coverage_target.exists(), "Refusing to overwrite coverage summary")
    write_csv(coverage_target, coverage)
    tables["coverage_summary"] = coverage
    primary = [r for r in tables["outcome_summary"] if r["period_kind"] == "overall" and r["panel"] == "all_crosses" and r["event_type"] == "price_cross" and r["horizon"] == "30m" and r["direction"] == "all" and r["section"] == "all" and r["condition"] == "all"]
    metrics = {"schema_version": "abacus.study30.statistics/v1", "study_id": SID,
               "requested_start": START, "requested_cutoff": CUTOFF,
               "actual_start": dates[0] if dates else None, "actual_end": dates[-1] if dates else None,
               "eligible_days": len(dates), "price_events": len(ledgers.get("price_events", [])),
               "ema_events": len(ledgers.get("ema_events", [])), "primary_horizon": "30m",
               "primary": primary, "qualifications": list(LIMITS),
               "bootstrap": {"replicates": bootstrap_replicates, "block_observed_sessions": 5,
                             "seed": bootstrap_seed, "method": "non_circular_moving_blocks",
                             "intervals": "95% descriptive; overall daily means and overall 30m outcome means/positive shares only; undefined for <=5 total sessions or <2 contributing days"},
               "table_rows": {k: len(v) for k, v in tables.items()},
               "source_tables": {k: {"artifact": f"tables/{k}.csv", "sha256": sha(stage / "tables" / f"{k}.csv")} for k in tables}}
    require(not (stage / "metrics.json").exists(), "Refusing to overwrite metrics")
    write_json(stage / "metrics.json", metrics)
    return tables


def md_table(rows, columns, limit=25):
    def fmt(v):
        if v is None:
            return "—"
        if isinstance(v, float):
            return f"{v:.3f}"
        return str(v).replace("|", "/").replace("\n", " ")
    return "| " + " | ".join(columns) + " |\n| " + " | ".join("---" for _ in columns) + " |\n" + "\n".join("| " + " | ".join(fmt(r.get(k)) for k in columns) + " |" for r in rows[:limit])


def render(stage):
    """Report and figures are derived solely from saved summary CSVs."""
    stage = Path(stage)
    metrics = json.loads((stage / "metrics.json").read_text(encoding="utf-8"))
    outcomes = read_csv(stage / "tables/outcome_summary.csv")
    episodes = read_csv(stage / "tables/episode_summary.csv")
    daily = read_csv(stage / "tables/daily_summary.csv")
    primary = [r for r in outcomes if r["period_kind"] == "overall" and r["panel"] == "all_crosses" and r["event_type"] == "price_cross" and r["horizon"] == "30m" and r["direction"] == "all" and r["section"] == "all" and r["condition"] == "all"]
    ema = [r for r in outcomes if r["period_kind"] == "overall" and r["panel"] == "all_crosses" and r["event_type"] == "price_cross" and r["condition"] == "ema_state_at_cross"]
    episode = [r for r in episodes if r["period_kind"] == "overall" and r["panel"] == "all_crosses" and r["direction"] == "all" and r["section"] == "all"]
    recurrence = [r for r in daily if r["period_kind"] == "overall" and r["section"] == "all" and r["metric"] in ("price_crosses", "ema_crosses", "touch_bars")]
    lines = ["# Verniman Pivot Statistics — ES", "",
             f"Requested calendar: {START}–{CUTOFF}. Actual eligible sample: {metrics['actual_start']}–{metrics['actual_end']}; {metrics['eligible_days']} days. Repository-only descriptive research; no purchases or external data extension.", "",
             "## Price breaks and actual EMA6 crossings", "",
             "The first distinction is whether EMA6 actually crosses the pivot, was already aligned, or remains opposite when price closes through it. An eventual return without a new EMA crossing is a later path label; compare its measured penetration rather than assuming that label was known at the break.", "",
             md_table(episode, ["condition", "condition_value", "events", "days", "returned_without_new_cross", "actual_confirmed", "return_censored", "mean_penetration_points"]), "",
             "Return censoring means the price episode did not reverse before the observed endpoint. A return-censored episode may already have an actual EMA confirmation; return censoring and confirmation censoring are different and their counts can overlap.", "",
             "## Primary 30-minute price-path baseline", "",
             md_table(primary, ["denominator", "valid_days", "unknown", "mean_points", "median_points", "positive_rate", "mean_ci95_low", "mean_ci95_high"]), "",
             md_table(ema, ["condition_value", "denominator", "valid_days", "mean_points", "positive_rate", "mean_favorable_points", "mean_adverse_points"]), "",
             "These conditional differences are exploratory. A result near zero, a broad interval, sparse support or a weaker recent/calendar slice is retained as negative or inconclusive evidence, not removed from the report. No classification is promoted to a tradable edge by this report.", "",
             "## Recurrence and repetition", "",
             md_table(recurrence, ["metric", "denominator", "estimate", "median", "p90", "zero_share", "ci95_low", "ci95_high"]), "",
             "All raw crosses are retained. First-per-day and first-per-section panels are saved alongside them; repeated events on the same day are not independent sessions.", "",
             "## Calendar, indicators and retests", "",
             "Saved tables include every calendar year/month, month of year and trailing 20/60/120 eligible observed sessions at the requested cutoff. Opening states, cloud/VWAP conditions, fixed 15/30/60-minute horizons, section/day endpoints, EMA-cross retests and section transitions retain explicit support and unknown counts. Curated web controls select saved rows only.", "",
             "## Methods and limits", "", *["- " + s for s in LIMITS],
             "- Five-minute EMA20/50 and three-minute EMA6 use full-session same-contract closes, with 250 preceding valid native bars. Globex VWAP uses one-minute HLC3/volume and resets at 18:00 New York.",
             "- Price/EMA events are strict side changes on completed three-minute closes. Equality retains the previous strict side; the opening state is not a cross. Section membership follows bar open, while information arrives at close.",
             "- Fixed horizons require complete RTH paths. Signal-bar earlier highs/lows are excluded; late/unknown outcomes remain null. Retests use subsequent three-minute bars and do not infer intrabar order.",
             f"- Overall mean and primary 30-minute mean/positive-rate intervals use {metrics['bootstrap']['replicates']:,} non-circular moving-block replicates of five observed sessions, seed {metrics['bootstrap']['seed']}. Whole-day records retain dependence among repeated events. Intervals do not correct source selection or multiple exploration.",
             "- Fewer than 30 distinct days is a sparse cell. Sampled close occupancy is not exact time above/below a line. Point/basis-point changes are not realized P&L.", "",
             "Reproduce from the retained settings/input/source/environment freeze and exact run commands. Numerical verification, source-cell transfer integrity and website checks are separate evidence.", ""]
    markdown = "\n".join(lines)
    (stage / "report.md").write_text(markdown, encoding="utf-8")
    (stage / "advice.md").write_text("# Interpretation — Verniman Pivot Statistics — ES\n\n" + "\n\n".join(LIMITS) + "\n\nUse the saved support, first-event panels and calendar stability before proposing a separate executable strategy. No profitable edge is established by this descriptive release.\n", encoding="utf-8")
    (stage / "report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Verniman Pivot Statistics — ES</title><style>body{max-width:1100px;margin:32px auto;padding:0 20px;font:16px/1.6 system-ui;background:#f5f7fa;color:#182b45}pre{white-space:pre-wrap;overflow-wrap:anywhere}img{max-width:100%}</style><body><pre>' + html.escape(markdown) + '</pre></body></html>', encoding="utf-8")
    figure_dir = stage / "figures"
    figure_dir.mkdir(exist_ok=True)
    figure = figure_dir / "price-ema-30m.png"
    source_rows = [i for i, row in enumerate(outcomes) if row in ema]
    chart_input = {"schema_version": "abacus.study30.saved-chart-inputs/v1", "artifact": "tables/outcome_summary.csv",
                   "sha256": sha(stage / "tables/outcome_summary.csv"), "source_row_base": 0,
                   "source_rows": source_rows, "rows": ema,
                   "actual_start": metrics["actual_start"], "actual_end": metrics["actual_end"],
                   "eligible_days": metrics["eligible_days"], "requested_cutoff": metrics["requested_cutoff"],
                   "note": "Saved 30m all-price-cross means and day-block 95% intervals by reference-time EMA6 state. No statistics are calculated by the chart renderer."}
    input_path = figure_dir / "price-ema-30m-inputs.json"
    write_json(input_path, chart_input)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        script = Path(__file__).resolve().parents[1] / "render_chart.mjs"
        command = ["node", str(script), "--input", str(input_path.resolve()), "--output", str(figure.resolve())]
        rendered = subprocess.run(command, capture_output=True, text=True)
        require(rendered.returncode == 0, "Saved-chart Sharp fallback failed: " + rendered.stderr.strip())
        receipt = json.loads(rendered.stdout)
        receipt.update(command=command, renderer_source_sha256=sha(script),
                       input_artifact=str(input_path.relative_to(stage)), input_sha256=sha(input_path),
                       source_artifact="tables/outcome_summary.csv", source_sha256=sha(stage / "tables/outcome_summary.csv"),
                       png_sha256=sha(figure), qualification="Matplotlib absent; existing Narada Sharp rasterizes authored SVG from saved numbers only. No dependencies installed or synchronized.")
        write_json(figure_dir / "price-ema-30m-render.json", receipt)
        return {"figures": [str(figure.relative_to(stage))], "renderer": receipt["renderer"], "fallback": "matplotlib_unavailable_sharp_used"}
    labels = [str(r["condition_value"]).replace("_", " ") for r in ema]
    values = [r["mean_points"] if r["mean_points"] is not None else float("nan") for r in ema]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(labels, values, color="#315d8f")
    ax.axvline(0, color="#23364b", linewidth=0.8)
    ax.set(xlabel="Mean signed ES points · 30 minutes", title="Price break: EMA6 state known at the close")
    for i, row in enumerate(ema):
        value = row["mean_points"]
        if value is not None:
            ax.annotate(f"n={row['denominator']} / {row['valid_days']} days", (value, i), xytext=(5 if value >= 0 else -5, 0), textcoords="offset points", va="center", ha="left" if value >= 0 else "right", fontsize=8)
    fig.text(0.02, 0.01, "Descriptive selected sample; unverified historical pivot availability; no costs/fills. Sparse <30 days.", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(figure, dpi=130)
    plt.close(fig)
    write_json(figure_dir / "price-ema-30m-render.json", {"renderer": "matplotlib", "version": matplotlib.__version__,
               "input_artifact": str(input_path.relative_to(stage)), "input_sha256": sha(input_path),
               "source_artifact": "tables/outcome_summary.csv", "source_sha256": sha(stage / "tables/outcome_summary.csv"), "png_sha256": sha(figure)})
    return {"figures": [str(figure.relative_to(stage))]}
