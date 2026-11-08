"""Saved, study-specific S01–S20 summaries; no report-time calculations.

The common long table keeps each population and observation unit explicit.
One-way section, direction and panel slices are deliberate; these are not a
Cartesian set of every condition. Bootstrap draws whole eligible days, including
days producing no selected event, before applying the condition.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from reporting import block_weights, clean, write_csv, write_json, sha

START, CUTOFF = "2020-01-01", "2026-10-30"
NY = ZoneInfo("America/New_York")
COHORTS = ("pivot_matched_rth", "vwap_only_rth", "vwap_only_full_globex")
PANELS = ("all_crosses", "first_per_day", "first_per_section")
SECTIONS = ("opening_range", "new_york_am", "new_york_pm")
DIMENSIONS = ("statistic_id", "reference", "series", "session_mode", "cohort",
              "period_kind", "period", "section", "direction", "panel", "horizon",
              "condition", "condition_value", "metric", "unit")


def numeric(value):
    return isinstance(value, (int, float, np.number)) and not isinstance(value, bool) and math.isfinite(float(value))


def windows(days):
    """Recent and preceding populations are disjoint for each window size."""
    days = sorted(set(days))
    result = [("overall", "all", set(days))]
    for year in range(2020, 2027):
        result.append(("year", str(year), {d for d in days if d[:4] == str(year)}))
    for year in range(2020, 2027):
        for month in range(1, 13):
            label = f"{year:04d}-{month:02d}"
            if label <= CUTOFF[:7]:
                result.append(("calendar_month", label, {d for d in days if d[:7] == label}))
    for size in (20, 60, 120):
        recent = set(days[-size:])
        result.extend((("recent", f"last_{size}", recent),
                       ("preceding", f"before_last_{size}", set(days) - recent)))
    return result


def memberships(row, mode=None):
    mode = mode or row.get("session_mode", "rth")
    by_mode = row.get("cohorts_by_mode", row.get("cohort_membership", {}))
    value = by_mode.get(mode) if isinstance(by_mode, dict) else None
    if value is None:
        value = row.get("cohorts", [])
    return [c for c in value if c in COHORTS and (c.endswith("globex") == (mode == "globex"))]


def _observation(row, stat, metric, value, unit, *, reference=None, series=None,
                 mode=None, cohort=None, panel="all_crosses", horizon="none",
                 condition="all", condition_value="all", section=None,
                 censored=None, **extra):
    return {"session_date": row["session_date"], "statistic_id": stat,
            "reference": reference or row.get("reference", "pivot"),
            "series": series or row.get("series", "ema6"),
            "session_mode": mode or row.get("session_mode", "rth"),
            "cohort": cohort, "section": section or row.get("section", "all"),
            "direction": row.get("direction", "all"), "panel": panel,
            "horizon": horizon, "condition": condition,
            "condition_value": str(condition_value), "metric": metric,
            "unit": unit, "value": value,
            "censored": bool(row.get("censored", False) if censored is None else censored), **extra}


def _bucket(count):
    return "0" if count == 0 else "1" if count == 1 else "2" if count == 2 else "3–4" if count < 5 else "5+"


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(NY) if value else None


def _event_panels(row, mode="rth"):
    result = ["all_crosses"]
    ordinal = row.get(f"{mode}_ordinal", row.get(f"ordinal_{mode}", row.get("ordinal", row.get("crossing_ordinal"))))
    if row.get("first_per_day") is True or ordinal == 1:
        result.append("first_per_day")
    if row.get("first_per_section") is True or row.get("section_ordinal", row.get("ordinal_section")) == 1:
        result.append("first_per_section")
    return result


def observations(ranked, baseline):
    """Retain candidate observations before denominator/missing aggregation."""
    result = []
    def add(row, stat, metric, value, unit, **kwargs):
        mode = kwargs.get("mode", row.get("session_mode", "rth"))
        cohorts = [kwargs.pop("cohort")] if kwargs.get("cohort") else memberships(row, mode)
        for cohort in cohorts:
            result.append(_observation(row, stat, metric, value, unit, cohort=cohort, **kwargs))

    daily = ranked.get("daily", [])
    sections = ranked.get("sections", [])
    for row in [*daily, *sections]:
        count = row.get("crosses")
        exposure = row.get("observed_hours")
        valid = numeric(exposure) and exposure > 0 and numeric(count)
        count = count if valid else None
        stat = "S01" if row.get("reference") == "vwap" else "S02"
        if row.get("series") == "ema6":
            add(row, stat, "crosses", count, "crossings/session")
            add(row, "S04", "crosses_per_hour", count / exposure if valid else None, "crossings/hour")
            for bucket in ("0", "1", "2", "3–4", "5+"):
                add(row, "S03", "count_bucket", _bucket(count) == bucket if count is not None else None,
                    "fraction", condition="cross_count", condition_value=bucket)
            first = _time(row.get("first_cross_at"))
            origin = 18 * 60 if row.get("session_mode") == "globex" else 570
            minute = (first.hour * 60 + first.minute - origin) % 1440 if first else None
            add(row, "S12", "first_cross_minutes", minute, "minutes")
            direction = row.get("first_cross_direction")
            for category in ("up", "down", "no_cross"):
                value = None if not valid else (direction == 1 if category == "up" else direction == -1 if category == "down" else count == 0)
                add(row, "S12", "first_cross_direction", value, "fraction", condition="first_direction", condition_value=category)
            # Half-hour bins use bar-open information for section assignment;
            # displayed first-cross time is when the completed bar is known.
            if row.get("section", "all") == "all":
                bins = range(0, 1380 if row.get("session_mode") == "globex" else 390, 30)
                for left in bins:
                    last = (1380 if row.get("session_mode") == "globex" else 390)
                    value = (left <= minute < left + 30 or minute == last and left + 30 == last) if minute is not None else False if valid and count == 0 else None
                    label=f"{left}–{left+30} inclusive" if left+30==last else f"{left}–<{left+30}"
                    add(row, "S12", "first_cross_timing", value, "fraction", condition="minutes_from_session_start", condition_value=label)
                add(row, "S12", "first_cross_timing", count == 0 if count is not None else None, "fraction", condition="minutes_from_session_start", condition_value="no_cross")
            for direction_key, label in (("crosses_up", "up"), ("crosses_down", "down")):
                directional = {**row, "direction": label}
                add(directional, stat, "crosses", row.get(direction_key) if valid else None, "crossings/session")
        # Additional price back-and-forth is paired within each day/section.
        add(row, "S05", "crosses", count, "crossings/session")
        if row.get("series") == "ema6" and row.get("session_mode") == "rth":
            for condition in ("opening_configuration", "opening_separation_band"):
                family = "S15" if condition == "opening_configuration" else "S17"
                if "pivot_matched_rth" in memberships(row):
                    add(row, family, "crosses", count, "crossings/session", cohort="pivot_matched_rth",condition=condition,
                        condition_value=row.get(condition, "unknown"))
            if row.get("section", "all") == "all" and "pivot_matched_rth" in memberships(row):
                for metric, unit in (("opening_separation_points", "points"), ("opening_separation_bps", "basis points")):
                    add(row, "S17", metric, row.get(metric), unit,cohort="pivot_matched_rth")
    paired = defaultdict(dict)
    for row in [*daily, *sections]:
        key = (row["session_date"], row.get("contract"), row.get("reference"), row.get("session_mode"), row.get("section", "all"))
        paired[key][row.get("series")] = row
    for pair in paired.values():
        if "ema6" in pair and "price" in pair:
            a, b = pair["price"], pair["ema6"]
            valid = all(numeric(r.get("observed_hours")) and r["observed_hours"] > 0 and numeric(r.get("crosses")) for r in (a, b))
            add(b, "S05", "additional_price_crosses", a["crosses"] - b["crosses"] if valid else None, "crossings/session")

    event_index = {r["event_id"]: r for r in ranked.get("events", [])}
    for source in ranked.get("outcomes", []):
        row = {**event_index.get(source.get("event_id"), {}), **source}
        if row.get("session_mode", "rth") != "rth":
            continue
        value = row.get("displacement_points") if row.get("valid") is True else None
        horizon = str(row.get("horizon", "30m"))
        for panel in _event_panels(row):
            for metric, amount, unit in (("displacement", value, "points"), ("positive_movement", value > 0 if numeric(value) else None, "fraction")):
                add(row, "S09", metric, amount, unit, panel=panel, horizon=horizon, censored=not row.get("valid", False))
            for side in ("favorable", "adverse"):
                add(row, "S10", side + "_excursion", row.get(side + "_excursion_points") if row.get("valid") is True else None, "points", panel=panel, horizon=horizon, censored=not row.get("valid", False))
                for threshold in (5, 10, 20):
                    add(row, "S10", f"{side}_reach_{threshold}", row.get(f"{side}_reach_{threshold}") if row.get("valid") is True else None, "fraction", panel=panel, horizon=horizon, censored=not row.get("valid", False))
            if row.get("series") == "ema6":
                ordinal = row.get("rth_ordinal", row.get("ordinal_rth", row.get("ordinal", row.get("crossing_ordinal"))))
                if ordinal:
                    add(row, "S13", "displacement", value, "points", panel=panel, horizon=horizon,
                        condition="crossing_ordinal", condition_value="1" if ordinal == 1 else "2" if ordinal == 2 else "3+",censored=not row.get("valid",False))
            if horizon == "30m":
                for condition, family in (("opening_configuration", "S15"), ("cloud_support", "S16"), ("opening_separation_band", "S17")):
                    kwargs={"cohort":"pivot_matched_rth"} if family in ("S15","S17") else {}
                    if family in ("S15","S17") and "pivot_matched_rth" not in memberships(row):
                        continue
                    add(row, family, "displacement", value, "points", panel=panel, horizon=horizon, condition=condition,**kwargs,
                        condition_value=row.get(condition, "unknown"), censored=not row.get("valid", False))
                    add(row, family, "positive_movement", value > 0 if numeric(value) else None, "fraction", panel=panel, horizon=horizon,**kwargs,
                        condition=condition, condition_value=row.get(condition, "unknown"), censored=not row.get("valid", False))

    for source in ranked.get("recrosses", []):
        row = {**event_index.get(source.get("event_id"), {}), **source}
        for panel in _event_panels(row):
            add(row, "S11", "no_recross", row.get("no_recross"), "fraction", panel=panel,
                horizon=row.get("horizon", "30m"), censored=row.get("no_recross") is None)
            if row.get("horizon", "30m") == "30m":
                delay = row.get("next_recross_minutes", row.get("minutes_to_recross", row.get("recross_minutes")))
                add(row, "S11", "time_to_recross", delay if row.get("valid") is True and numeric(delay) and delay <= 30 else None, "minutes", panel=panel, horizon="30m")
    sequence_categories = ("second_before_recross", "recross_first", "simultaneous", "already_beyond_other", "other_equal_at_start", "neither_within_30m", "simultaneous_endpoint", "unknown_other_line", "censored_missing_observation", "censored_no_endpoint")
    for row in ranked.get("sequences", []):
        outcome = row.get("result", row.get("sequence_result"))
        for panel in _event_panels(row):
            for category in sequence_categories:
                # Dispositions have a common candidate denominator. Conditional
                # traversal probability excludes simultaneous/already beyond.
                add(row, "S14", "sequence_disposition", outcome == category if outcome is not None else None, "fraction", panel=panel, horizon="30m", condition="sequence_result", condition_value=category)
            resolved = outcome in ("second_before_recross", "recross_first", "neither_within_30m")
            add(row, "S14", "second_before_recross", outcome == "second_before_recross" if resolved else None, "fraction", panel=panel, horizon="30m", condition="first_reference", condition_value=row.get("first_reference", row.get("reference", "unknown")), censored=bool(row.get("censored")))
    for row in ranked.get("transitions", []):
        left, right = row.get("from_state"), row.get("to_state")
        valid = left not in (None, "unknown") and right not in (None, "unknown")
        condition_value = f"{row.get('from_section', 'opening_range')}→{row.get('to_section', 'new_york_am')}:{row.get('metric', 'ema6_side')}:{left}"
        add(row, "S19", "state_persists", row.get("persistent") if valid else None, "fraction", condition="section_state", condition_value=condition_value)
        add(row, "S19", "state_reverses", row.get("reversed") if valid else None, "fraction", condition="section_state", condition_value=condition_value)

    # Existing fixed-pivot episodes/retests retain their original interface.
    for source in baseline.get("price_events", []):
        row = {**source, "reference": "pivot", "series": "price", "session_mode": "rth", "cohorts": ["pivot_matched_rth"]}
        state = row.get("ema_state_at_cross")
        initially = state in ("opposite", "equal_with_remembered_side", "unavailable_uninitialized")
        resolved = row.get("confirmation_at") is not None or row.get("returned_at") is not None
        returned = row.get("returned_at") is not None and row.get("confirmation_at") is None
        for panel in _event_panels(row):
            if initially:
                add(row, "S06", "returned_before_confirmation", returned if resolved else None, "fraction", panel=panel, censored=not resolved)
                add(row, "S07", "returned_unconfirmed_depth", row.get("episode_penetration_points") if returned else None, "points", panel=panel, censored=not resolved)
            for metric, key, unit in (("confirmation_delay", "confirmation_lag_minutes", "minutes"), ("movement_before_confirmation", "price_movement_to_confirmation_points", "points"), ("distance_at_confirmation", "confirmation_distance_from_pivot", "points")):
                add(row, "S08", metric, row.get(key), unit, panel=panel, condition="confirmation_kind", condition_value=row.get("confirmation_kind") or "unconfirmed", censored=not resolved)
    for source in baseline.get("ema_events", []):
        row = {**source, "reference": "pivot", "series": "ema6", "session_mode": "rth", "cohorts": ["pivot_matched_rth"]}
        complete = row.get("retest_window_complete") is True
        for panel in _event_panels(row):
            add(row, "S18", "pivot_retest", row.get("retest_found") if complete else None, "fraction", panel=panel, horizon="30m", censored=not complete)
            add(row, "S18", "time_to_retest", row.get("time_to_retest_minutes", row.get("retest_minutes")), "minutes", panel=panel, horizon="30m")
            for category in ("hold", "failed", "equal"):
                found = row.get("retest_found") is True
                add(row, "S18", "retest_close", row.get("retest_close_classification", row.get("retest_close_class")) == category if found else None, "fraction", panel=panel, horizon="30m", condition="retest_close", condition_value=category)
    baseline_events = {r["event_id"]:r for r in baseline.get("price_events",[])}
    for source in baseline.get("outcomes",[]):
        if source.get("event_type") != "ema_confirmation":
            continue
        row = {**baseline_events.get(source["event_id"],{}), **source,
               "reference":"pivot", "series":"ema6", "session_mode":"rth", "cohorts":["pivot_matched_rth"]}
        displacement = row.get("displacement_points") if row.get("valid") is True else None
        for panel in _event_panels(row):
            add(row,"S08","post_confirmation_displacement",displacement,"points",panel=panel,horizon=row["horizon"],
                condition="confirmation_kind",condition_value=row.get("confirmation_kind") or "unknown",censored=not row.get("valid",False))
            add(row,"S08","post_confirmation_positive_movement",displacement>0 if numeric(displacement) else None,"fraction",panel=panel,horizon=row["horizon"],
                condition="confirmation_kind",condition_value=row.get("confirmation_kind") or "unknown",censored=not row.get("valid",False))
    for row in ranked.get("events",[]):
        if row.get("series") != "ema6" or "rth" not in row.get("scopes",[]):
            continue
        for panel in _event_panels(row):
            for category in ("support","opposition","mixed","unknown"):
                add(row,"S16","crossing_context_share",row.get("cloud_support","unknown")==category,"fraction",mode="rth",panel=panel,
                    condition="cloud_support",condition_value=category)
    return result


def _slice_records(records):
    """One-way slices, with all-event and first-event panels already explicit."""
    yield "all", "all", records
    for direction, label in ((1, "up"), (-1, "down")):
        subset = [r for r in records if r.get("direction") in (direction, label)]
        if subset:
            yield label, "all", subset
    # Session/section observations carry their own section and cannot be pooled
    # together; event observations can additionally be selected by section.
    for section in SECTIONS:
        subset = [r for r in records if r.get("section") == section]
        if subset:
            yield "all", section, subset


def _summarize_group(records, *, days, weights):
    valid = [r for r in records if numeric(r.get("value")) or isinstance(r.get("value"), bool)]
    values = np.asarray([float(r["value"]) for r in valid], dtype=float)
    dates = sorted({r["session_date"] for r in valid})
    low = high = None
    if len(dates) >= 2 and weights is not None:
        position = {d: i for i, d in enumerate(days)}
        sums = np.zeros(len(days)); counts = np.zeros(len(days))
        for row in valid:
            index = position[row["session_date"]]
            sums[index] += float(row["value"]); counts[index] += 1
        top, bottom = weights @ sums, weights @ counts
        estimates = top[bottom > 0] / bottom[bottom > 0]
        if len(estimates):
            low, high = [float(v) for v in np.quantile(estimates, [0.025, 0.975])]
    return {"estimate": float(values.mean()) if len(values) else None,
            "median": float(np.median(values)) if len(values) else None,
            "p25": float(np.quantile(values, .25)) if len(values) else None,
            "p75": float(np.quantile(values, .75)) if len(values) else None,
            "p90": float(np.quantile(values, .90)) if len(values) else None,
            "numerator": float(values.sum()) if len(values) else 0,
            "denominator": len(valid), "days": len(dates), "candidates": len(records),
            "unknown": len(records) - len(valid), "censored": sum(r.get("censored", False) for r in records),
            "earliest_session": dates[0] if dates else None, "latest_session": dates[-1] if dates else None,
            "sparse": len(dates) < 30, "ci95_low": low, "ci95_high": high,
            "requested_start": START, "requested_cutoff": CUTOFF}


def summarize(ranked, baseline, *, bootstrap_replicates=2000, bootstrap_seed=20261031):
    records = observations(ranked, baseline)
    cohort_days = {c: sorted({r["session_date"] for r in ranked.get("daily", []) if c in memberships(r)}) for c in COHORTS}
    # Baseline populations are retained even when a synthetic test omits daily
    # ranked rows. Production coverage checks require their exact equality.
    if not cohort_days["pivot_matched_rth"]:
        cohort_days["pivot_matched_rth"] = sorted({r["session_date"] for r in baseline.get("daily", [])})
    grouped = defaultdict(list)
    fixed = ("statistic_id", "reference", "series", "session_mode", "cohort", "panel", "horizon", "condition", "condition_value", "metric", "unit")
    for row in records:
        # Daily/section records are kept separate before one-way event slicing.
        kind = "session" if row["statistic_id"] in ("S01", "S02", "S03", "S04", "S05", "S12") or row["metric"] in ("crosses", "opening_separation_points", "opening_separation_bps") else "event"
        source_section = row.get("section", "all") if kind == "session" else "event"
        grouped[tuple(row[k] for k in fixed) + (source_section,)].append(row)
    result = []
    weights_cache = {}
    for key, group in sorted(grouped.items(), key=lambda item: str(item[0])):
        base = dict(zip(fixed, key[:-1])); source_section = key[-1]
        days = cohort_days[base["cohort"]]
        if not days:
            days = sorted({r["session_date"] for r in group})
        for period_kind, period, selected in windows(days):
            if period_kind != "overall" and base["horizon"] not in ("none", "30m"):
                continue
            selected_rows = [r for r in group if r["session_date"] in selected]
            slices = [("all", source_section, selected_rows)] if source_section != "event" else _slice_records(selected_rows)
            for direction, section, rows in slices:
                # A direction already encoded in daily observation is retained
                # separately rather than accidentally pooled into its all row.
                if source_section != "event":
                    directional = defaultdict(list)
                    for row in rows:
                        directional[str(row.get("direction", "all"))].append(row)
                    slices2 = [(d, rs) for d, rs in directional.items()] or [("all", [])]
                else:
                    slices2 = [(direction, rows)]
                for actual_direction, actual_rows in slices2:
                    bootstrap = period_kind == "overall" and section == "all" and actual_direction == "all"
                    weights = None
                    if bootstrap:
                        cache_key = tuple(days)
                        if cache_key not in weights_cache:
                            weights_cache[cache_key] = block_weights(days, bootstrap_replicates, 5, bootstrap_seed)
                        weights = weights_cache[cache_key]
                    item = {**base, "period_kind": period_kind, "period": period,
                            "direction": actual_direction, "section": section,
                            **_summarize_group(actual_rows, days=days, weights=weights)}
                    result.append(item)
                    if period_kind in ("recent", "preceding") and base["statistic_id"] in ("S01", "S02", "S04", "S09", "S11", "S18") and base["condition"] == "all" and (base["horizon"] in ("none", "30m")):
                        result.append({**item, "statistic_id": "S20", "condition": "source_statistic", "condition_value": base["statistic_id"]})
    return clean(result)


def write_statistics(stage, ranked, baseline, *, bootstrap_replicates=2000, bootstrap_seed=20261031):
    stage = Path(stage)
    target = stage / "tables/ranked_summary.csv"
    if target.exists():
        raise FileExistsError("Refusing to overwrite ranked summaries")
    rows = summarize(ranked, baseline, bootstrap_replicates=bootstrap_replicates, bootstrap_seed=bootstrap_seed)
    write_csv(target, rows)
    metadata = {"schema_version": "abacus.study30.ranked-statistics/v1", "rows": len(rows),
                "artifact": "tables/ranked_summary.csv", "sha256": sha(target),
                "statistic_ids": sorted({r["statistic_id"] for r in rows}),
                "bootstrap": {"replicates": bootstrap_replicates, "block_observed_sessions": 5,
                              "seed": bootstrap_seed, "intervals": "overall pooled estimates only; complete eligible days sampled before conditions; undefined for <=5 eligible days or <2 contributing days"},
                "qualifications": ["Historical pivot availability unverified.", "Cohorts are never pooled.",
                                   "Calendar and conditional comparisons are exploratory.", "No trade simulation or profitability inference."]}
    write_json(stage / "ranked-metrics.json", metadata)
    return {"ranked_summary": rows}
