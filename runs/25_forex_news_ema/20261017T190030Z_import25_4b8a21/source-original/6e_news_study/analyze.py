#!/usr/bin/env python3
"""Reproduce the descriptive 6E calendar event study (Python standard library).

All price timestamps are native TradingView 15-minute bar OPEN times in UTC.
Results are associated price movements, not estimates of causal news effects.
Run: python3 analyze.py
"""
from __future__ import annotations

import argparse
import bisect
import calendar
import collections
import csv
import datetime as dt
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import statistics
from zoneinfo import ZoneInfo

UTC = dt.timezone.utc
NY = ZoneInfo("America/New_York")
TICK = 0.00005
PIP = 0.0001
BAR = 900
OHLC = ("open", "high", "low", "close")
START = int(dt.datetime(2025, 10, 17, tzinfo=NY).timestamp())
END = int(dt.datetime(2026, 10, 17, tzinfo=NY).timestamp())
ROOT = Path(__file__).resolve().parent


def stamp(value):
    if isinstance(value, (int, float)):
        return int(value / 1000 if value > 10**11 else value)
    value = str(value)
    if value.isdigit():
        return stamp(int(value))
    return int(dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def iso(value):
    return dt.datetime.fromtimestamp(value, UTC).isoformat().replace("+00:00", "Z")


def quantile(values, p):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * p
    a, b = math.floor(pos), math.ceil(pos)
    return values[a] + (values[b] - values[a]) * (pos - a)


def rounded(value, digits=6):
    return None if value is None else round(value, digits)


def write_csv(name, rows):
    rows = list(rows)
    with (ROOT / name).open("w", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def write_json(name, obj):
    (ROOT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def read_prices():
    """Anchor at recent export; reconcile older exports by overlap OHLC offsets."""
    files = sorted(ROOT.glob("prices_*_native.csv"), key=lambda p: ("recent" not in p.name, p.name))
    if not files:
        raise RuntimeError("No native price exports found")
    prices, invalid, audits = {}, set(), []
    for path in files:
        original = list(csv.DictReader(path.open()))
        local = {}
        invalid_ohlc, off_grid, off_tick, duplicate_rows = [], [], [], []
        for raw in original:
            t = stamp(raw["time"])
            row = {k: float(raw[k]) for k in OHLC}
            if not all(math.isfinite(v) for v in row.values()) or not (
                row["low"] <= min(row["open"], row["close"]) + 1e-10
                and row["high"] + 1e-10 >= max(row["open"], row["close"])
                and row["low"] <= row["high"]
            ):
                invalid_ohlc.append(t)
                invalid.add(t)
            if t % BAR:
                off_grid.append(t)
                invalid.add(t)
            if any(abs(v / TICK - round(v / TICK)) > 1e-5 for v in row.values()):
                off_tick.append(t)
                invalid.add(t)
            if t in local:
                duplicate_rows.append(t)
                if any(abs(local[t][k] - row[k]) > 1e-8 for k in OHLC):
                    invalid.add(t)
            local[t] = row
        overlap = sorted(prices.keys() & local.keys())
        differences = [prices[t][k] - local[t][k] for t in overlap for k in OHLC]
        offset = statistics.median(differences) if differences else 0.0
        constant_offset = bool(differences) and max(differences) - min(differences) < 1e-8
        inconsistent = []
        if differences and not constant_offset:
            offset = 0.0
            inconsistent = [t for t in overlap if any(abs(prices[t][k] - local[t][k]) > 1e-8 for k in OHLC)]
            invalid.update(inconsistent)
        for t, row in local.items():
            if t not in prices:
                prices[t] = {**{k: v + offset for k, v in row.items()}, "source": path.name}
        audits.append({
            "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows": len(original), "unique_timestamps": len(local),
            "first_bar_open_utc": iso(min(local)), "last_bar_open_utc": iso(max(local)),
            "overlap_bars_with_anchor": len(overlap), "overlap_all_ohlc_constant_difference": constant_offset if overlap else None,
            "offset_added_to_this_file_ticks": rounded(offset / TICK),
            "inconsistent_overlap_bars_excluded": len(inconsistent),
            "invalid_ohlc_rows": len(invalid_ohlc), "off_grid_rows": len(off_grid),
            "off_tick_rows": len(off_tick), "duplicate_timestamps": len(duplicate_rows),
        })
    times = sorted(prices)
    gaps = collections.Counter((b - a) // 60 for a, b in zip(times, times[1:]) if b - a != BAR)
    jumps = []
    for a, b in zip(times, times[1:]):
        if b - a == BAR:
            jump = abs(prices[b]["open"] - prices[a]["close"]) / TICK
            if jump >= 40 - 1e-5:
                jumps.append({"bar_open_utc": iso(b), "opening_gap_ticks": rounded(jump), "source_change": prices[a]["source"] != prices[b]["source"]})
    study_times = [t for t in times if START <= t < END]
    audit = {
        "files": audits, "combined_unique_bars": len(times), "study_bars": len(study_times),
        "study_first_bar_open_utc": iso(min(study_times)), "study_last_bar_open_utc": iso(max(study_times)),
        "native_interval_minutes": 15, "price_floor": min(prices[t]["low"] for t in study_times),
        "price_ceiling": max(prices[t]["high"] for t in study_times),
        "zero_range_bars": sum(abs(prices[t]["high"] - prices[t]["low"]) < 1e-10 for t in study_times),
        "minimum_positive_bar_range_ticks": rounded(min((prices[t]["high"] - prices[t]["low"]) / TICK for t in study_times if prices[t]["high"] > prices[t]["low"] + 1e-10)),
        "non_15_minute_gap_histogram_minutes": dict(sorted(gaps.items())),
        "contiguous_opening_gaps_at_least_40_ticks": jumps,
        "invalid_or_conflicting_bar_count": len(invalid),
    }
    return prices, invalid, audit


def read_calendar():
    raw = json.loads((ROOT / "calendar_raw.json").read_text())
    classified = json.loads((ROOT / "calendar_classification.json").read_text())
    # The classification file preserves original rows and adds study labels.
    rows = classified if isinstance(classified, list) else classified.get("events", classified.get("rows", []))
    if not rows:
        raise RuntimeError("calendar_classification.json has no event rows")
    result, seen, duplicates = [], set(), []
    for row in rows:
        event = dict(row)
        original = event.get("event", event.get("raw", {}))
        if original:
            event = {**original, **event}
        t = stamp(event.get("date", event.get("timestamp", event.get("time"))))
        event["ts"] = t
        event["study_category"] = event.get("study_category", event.get("event_category", event.get("family", event.get("news_category", event.get("category")))))
        if not event["study_category"]:
            # A plain `category` from the raw calendar (mny/prc/lbr...) is not sufficient.
            raise RuntimeError("Classified event missing study_category/family: " + str(event)[:300])
        event["is_speech"] = bool(event.get("is_speech", "speech" in str(event.get("title", "")).lower()))
        event["is_core"] = bool(event.get("is_core", event.get("core_category", event.get("core", event.get("include_in_study", True)))))
        event["exclude_reason"] = (event.get("exclusion_reason") or "excluded_from_analysis") if event.get("excluded_from_analysis") else (event.get("exclude_reason") or "")
        key = (t, str(event.get("country", "")), str(event.get("title", "")), str(event.get("period", "")), str(event["study_category"]))
        if key in seen:
            duplicates.append(key)
            continue
        seen.add(key)
        result.append(event)
    result.sort(key=lambda e: e["ts"])
    collisions = []
    for key, group in itertools.groupby(sorted(result, key=lambda e: (e["ts"], e.get("country", ""), e.get("title", ""))), key=lambda e: (e["ts"], e.get("country", ""), e.get("title", ""))):
        group = list(group)
        if len(group) > 1:
            collisions.append({"utc": iso(key[0]), "country": key[1], "title": key[2], "rows": len(group), "periods": sorted(set(str(e.get("period", "")) for e in group))})
    return result, {"raw_rows": len(raw["events"]), "classified_rows": len(rows), "deduplicated_rows": len(result),
                    "raw_sha256": hashlib.sha256((ROOT / "calendar_raw.json").read_bytes()).hexdigest(),
                    "classification_sha256": hashlib.sha256((ROOT / "calendar_classification.json").read_bytes()).hexdigest(),
                    "excluded_rows": [{"id": e.get("id"), "utc": iso(e["ts"]), "title": e.get("title"), "reason": e["exclude_reason"]} for e in result if e["exclude_reason"]],
                    "exact_title_country_period_timestamp_category_duplicates_removed": len(duplicates), "same_title_timestamp_distinct_period_collisions": collisions}


def measure(t, minutes, prices, invalid):
    if t % BAR:
        return None, "event_not_on_15_minute_grid"
    if not START <= t < END:
        return None, "outside_study"
    needed = list(range(t, t + minutes * 60, BAR))
    if t + minutes * 60 > END:
        return None, "window_crosses_study_end"
    if t - BAR not in prices:
        return None, "missing_adjacent_pre_release_bar"
    if any(s not in prices for s in needed):
        return None, "missing_post_release_bar"
    if any(s in invalid for s in [t - BAR] + needed):
        return None, "invalid_or_conflicting_price_bar"
    reference = prices[t - BAR]["close"]
    high = max(prices[s]["high"] for s in needed)
    low = min(prices[s]["low"] for s in needed)
    close = prices[needed[-1]]["close"]
    return {
        "pre_close": rounded(reference, 8), "high": rounded(high, 8), "low": rounded(low, 8), "end_close": rounded(close, 8),
        "excursion_ticks": rounded(max(abs(high - reference), abs(low - reference)) / TICK),
        "range_ticks": rounded((high - low) / TICK),
        "abs_close_ticks": rounded(abs(close - reference) / TICK),
        "signed_close_ticks": rounded((close - reference) / TICK),
        "opening_gap_ticks": rounded((prices[t]["open"] - reference) / TICK),
    }, "valid"


def build_events(calendar_rows):
    included = [e for e in calendar_rows if e["is_core"] and not e["exclude_reason"]]
    groups = collections.defaultdict(list)
    for event in included:
        if START <= event["ts"] < END:
            groups[event["ts"]].append(event)
    # One observation per timestamp. A multi-family timestamp is a release bundle.
    observations = []
    all_core = collections.defaultdict(set)
    all_speech = collections.defaultdict(set)
    for event in calendar_rows:
        if event["exclude_reason"]:
            continue
        if event["is_speech"]:
            all_speech[event["ts"]].add(event["study_category"])
        elif event["is_core"]:
            all_core[event["ts"]].add(event["study_category"])
    core_times, speech_times = sorted(all_core), sorted(all_speech)
    def nearby(index, t, before, after):
        # Strict lower bound excludes an earlier event exactly `before` minutes ago.
        a = bisect.bisect_right(index, t - before * 60)
        b = bisect.bisect_left(index, t + after * 60)
        return index[a:b]
    for t, events in sorted(groups.items()):
        categories = sorted(set(e["study_category"] for e in events))
        non_speech = sorted(set(e["study_category"] for e in events if not e["is_speech"]))
        speech = sorted(set(e["study_category"] for e in events if e["is_speech"]))
        category = " + ".join(categories)
        ny = dt.datetime.fromtimestamp(t, NY)
        item = {
            "timestamp_utc": iso(t), "timestamp_ny": ny.isoformat(), "ny_date": ny.date().isoformat(),
            "ny_month": ny.strftime("%Y-%m"), "ny_year": ny.year, "ny_weekday": ny.strftime("%A"),
            "ts": t, "category": category,
            "category_label": " + ".join(sorted(set(e.get("category_label", e["study_category"]) for e in events))),
            "category_count": len(categories), "is_bundle": len(categories) > 1,
            "is_speech_only": bool(speech) and not non_speech,
            "countries": "; ".join(sorted(set(str(e.get("country", "")) for e in events))),
            "titles": "; ".join(sorted(set(str(e.get("title", "")) for e in events))),
            "component_rows": len(events), "event_ids": ";".join(str(e.get("id", "")) for e in events),
        }
        for minutes in (15, 30, 60):
            other = [(s, c) for s in nearby(core_times, t, 30, minutes) for c in all_core[s] if s != t or c not in categories]
            speech_near = [(s, c) for s in nearby(speech_times, t, 30, minutes) for c in all_speech[s] if s != t or c not in categories]
            item[f"other_core_{minutes}m"] = "; ".join(f"{iso(s)} {c}" for s, c in other)
            item[f"nearby_speech_{minutes}m"] = "; ".join(f"{iso(s)} {c}" for s, c in speech_near)
            item[f"isolated_{minutes}m"] = not other and not item["is_bundle"]
            item[f"isolated_no_speech_{minutes}m"] = not other and not speech_near and not item["is_bundle"]
        observations.append(item)
    return observations


def bootstrap_median_ci(values, seed, repetitions=2000):
    if len(values) < 5:
        return (None, None)
    rng = random.Random(seed)
    samples = [statistics.median(rng.choices(values, k=len(values))) for _ in range(repetitions)]
    return quantile(samples, .025), quantile(samples, .975)


def summarize(measurements, split=None):
    groups = collections.defaultdict(list)
    for row in measurements:
        if row["status"] != "valid":
            continue
        for sample in ("all", "isolated", "isolated_no_speech"):
            if sample != "all" and not row[f"{sample}_{row['horizon_minutes']}m"]:
                continue
            if sample != "all" and row["is_speech_only"]:
                continue
            key = (row["category"], row["horizon_minutes"], sample, row.get(split) if split else "full_year")
            groups[key].append(row)
    rankings = []
    for (category, minutes, sample, period), rows in groups.items():
        values = [r["excursion_ticks"] for r in rows]
        control_rows = [r for r in rows if r["control_status"] == "valid"]
        ci = bootstrap_median_ci(values, f"{category}|{minutes}|{sample}|{period}")
        median = statistics.median(values)
        rankings.append({
            "category": category, "category_label": rows[0]["category_label"], "horizon_minutes": minutes, "sample": sample,
            "period": period, "n": len(rows), "small_sample_n_lt_10": len(rows) < 10,
            "primary_eligible_n_ge_5": len(rows) >= 5 and sample == "isolated" and minutes == 30,
            "is_bundle": rows[0]["is_bundle"], "is_speech_only": rows[0]["is_speech_only"],
            "median_excursion_ticks": rounded(median), "median_excursion_pips": rounded(median / 2),
            "p25_excursion_ticks": rounded(quantile(values, .25)), "p75_excursion_ticks": rounded(quantile(values, .75)),
            "p90_excursion_ticks": rounded(quantile(values, .90)),
            "bootstrap_median_95ci_low_ticks": rounded(ci[0]), "bootstrap_median_95ci_high_ticks": rounded(ci[1]),
            "share_excursion_ge_40_ticks": rounded(sum(v >= 40 - 1e-5 for v in values) / len(values)),
            "share_excursion_ge_80_ticks": rounded(sum(v >= 80 - 1e-5 for v in values) / len(values)),
            "median_range_ticks": rounded(statistics.median(r["range_ticks"] for r in rows)),
            "median_abs_close_ticks": rounded(statistics.median(r["abs_close_ticks"] for r in rows)),
            "control_matched_events": len(control_rows),
            "median_control_excursion_ticks": rounded(statistics.median(r["control_median_excursion_ticks"] for r in control_rows)) if control_rows else None,
            "median_event_control_uplift_ratio": rounded(statistics.median(r["control_uplift_ratio"] for r in control_rows if r["control_uplift_ratio"] is not None)) if any(r["control_uplift_ratio"] is not None for r in control_rows) else None,
        })
    rankings.sort(key=lambda r: (r["horizon_minutes"], r["sample"], str(r["period"]), -r["median_excursion_ticks"], r["category"]))
    rank = collections.Counter()
    for row in rankings:
        key = (row["horizon_minutes"], row["sample"], row["period"])
        rank[key] += 1
        row["descriptive_rank"] = rank[key]
    return rankings


def attach_controls(measurements, calendar_rows, prices, invalid):
    # Source query min_importance=0 supplies medium (0) and high (1) events.
    # Every supplied event, including speeches/non-core categories, blocks controls.
    blockers = sorted(set(e["ts"] for e in calendar_rows if not e["exclude_reason"]))
    cached, matches = {}, []
    for row in measurements:
        row.update(control_status="price_window_invalid", control_n=0, control_same_weekday_n=0,
                   control_median_excursion_ticks=None, control_uplift_ratio=None)
        if row["status"] != "valid":
            continue
        t, minutes = row["ts"], row["horizon_minutes"]
        local = dt.datetime.fromtimestamp(t, NY)
        key = (local.year, local.month, local.hour, local.minute, minutes)
        if key not in cached:
            pool = []
            for day in range(1, calendar.monthrange(local.year, local.month)[1] + 1):
                candidate = dt.datetime(local.year, local.month, day, local.hour, local.minute, tzinfo=NY)
                if candidate.weekday() > 4:
                    continue
                s = int(candidate.timestamp())
                if not START <= s < END:
                    continue
                # Inclusive +/-60-minute exclusion; no future event at +60m is a control.
                a, b = bisect.bisect_left(blockers, s - 3600), bisect.bisect_right(blockers, s + 3600)
                if a != b:
                    continue
                outcome, status = measure(s, minutes, prices, invalid)
                if status == "valid":
                    pool.append((s, outcome["excursion_ticks"], candidate.weekday()))
            cached[key] = pool
        controls = [(s, v, weekday) for s, v, weekday in cached[key] if dt.datetime.fromtimestamp(s, NY).date() != local.date()]
        row["control_n"] = len(controls)
        row["control_same_weekday_n"] = sum(w == local.weekday() for _, _, w in controls)
        row["control_status"] = "valid" if len(controls) >= 10 else "fewer_than_10_clean_same_month_controls"
        if len(controls) >= 10:
            baseline = statistics.median(v for _, v, _ in controls)
            row["control_median_excursion_ticks"] = rounded(baseline)
            row["control_uplift_ratio"] = rounded(row["excursion_ticks"] / baseline) if baseline > 0 else None
            for s, v, weekday in controls:
                matches.append({"event_utc": row["timestamp_utc"], "category": row["category"], "horizon_minutes": minutes,
                                "control_utc": iso(s), "control_ny": dt.datetime.fromtimestamp(s, NY).isoformat(),
                                "same_weekday": weekday == local.weekday(), "control_excursion_ticks": v})
    return matches


def comparison_rows(measurements, rankings, primary_only):
    """Keep each category's primary 30m event cohort fixed across sensitivities."""
    selected = [r for r in rankings if r["horizon_minutes"] == 30 and r["sample"] == ("isolated" if primary_only else "all")
                and r["n"] >= 5 and not r["is_bundle"] and not r["is_speech_only"]]
    index = {(r["ts"], r["horizon_minutes"]): r for r in measurements}
    output = []
    for ranking in sorted(selected, key=lambda r: -r["median_excursion_ticks"]):
        cohort = [r for r in measurements if r["horizon_minutes"] == 30 and r["category"] == ranking["category"] and r["status"] == "valid"
                  and (r["isolated_30m"] or not primary_only)]
        row = {"category": ranking["category"], "category_label": ranking["category_label"], "n_30m": len(cohort)}
        for minutes in (15, 30, 60):
            matched = [index[(r["ts"], minutes)] for r in cohort if index[(r["ts"], minutes)]["status"] == "valid"]
            row[f"n_{minutes}m_valid"] = len(matched)
            row[f"median_{minutes}m_excursion_ticks"] = rounded(statistics.median(r["excursion_ticks"] for r in matched)) if matched else None
            row[f"median_{minutes}m_range_ticks"] = rounded(statistics.median(r["range_ticks"] for r in matched)) if matched else None
            row[f"n_{minutes}m_core_overlap"] = sum(bool(r[f"other_core_{minutes}m"]) for r in matched)
            row[f"n_{minutes}m_speech_overlap"] = sum(bool(r[f"nearby_speech_{minutes}m"]) for r in matched)
        row.update({k: ranking[k] for k in ("p25_excursion_ticks", "p75_excursion_ticks", "p90_excursion_ticks", "share_excursion_ge_40_ticks", "median_abs_close_ticks", "bootstrap_median_95ci_low_ticks", "bootstrap_median_95ci_high_ticks", "control_matched_events", "median_control_excursion_ticks", "median_event_control_uplift_ratio")})
        output.append(row)
    return output


def self_checks():
    # Gap at the event is included in excursion; end-boundary bar is excluded.
    t = START + 8 * 3600
    synthetic = {
        t - BAR: {"open": 1., "high": 1., "low": 1., "close": 1.},
        t: {"open": 1.001, "high": 1.002, "low": 1.001, "close": 1.0015},
        t + BAR: {"open": 1.0015, "high": 1.003, "low": 1.001, "close": 1.002},
        t + 2 * BAR: {"open": 1.01, "high": 1.02, "low": 1.01, "close": 1.02},
    }
    result, status = measure(t, 30, synthetic, set())
    assert status == "valid" and result["excursion_ticks"] == 60 and result["range_ticks"] == 40
    assert measure(t, 15, synthetic, set())[0]["excursion_ticks"] == 40
    assert measure(t + 1, 30, synthetic, set())[1] == "event_not_on_15_minute_grid"
    assert measure(t, 30, {k: v for k, v in synthetic.items() if k != t + BAR}, set())[1] == "missing_post_release_bar"
    assert measure(t, 30, synthetic, {t - BAR})[1] == "invalid_or_conflicting_price_bar"
    events = [dict(ts=t, is_core=True, exclude_reason="", is_speech=False, study_category="decision", title="decision"),
              dict(ts=t + 1800, is_core=True, exclude_reason="", is_speech=False, study_category="conference", title="conference")]
    built = build_events(events)
    assert built[0]["isolated_30m"] and not built[0]["isolated_60m"]
    return {"synthetic_measurement_and_boundary_checks": "passed"}


def main():
    checks = self_checks()
    prices, invalid, price_audit = read_prices()
    calendar_rows, calendar_audit = read_calendar()
    observations = build_events(calendar_rows)
    measurements = []
    for observation in observations:
        for minutes in (15, 30, 60):
            outcome, status = measure(observation["ts"], minutes, prices, invalid)
            row = {**observation, "horizon_minutes": minutes, "status": status}
            row.update(outcome or {k: None for k in ("pre_close", "high", "low", "end_close", "excursion_ticks", "range_ticks", "abs_close_ticks", "signed_close_ticks", "opening_gap_ticks")})
            measurements.append(row)
    matches = attach_controls(measurements, calendar_rows, prices, invalid)
    rankings = summarize(measurements)
    monthly = summarize(measurements, "ny_month")
    yearly = summarize(measurements, "ny_year")
    write_csv("measurements.csv", [{k: v for k, v in r.items() if k != "ts"} for r in measurements])
    write_csv("rankings.csv", rankings)
    write_csv("monthly_rankings.csv", monthly)
    write_csv("yearly_rankings.csv", yearly)
    write_csv("control_matches.csv", matches)
    primary_comparison = comparison_rows(measurements, rankings, True)
    all_single_comparison = comparison_rows(measurements, rankings, False)
    write_csv("primary_comparison.csv", primary_comparison)
    write_csv("all_single_category_comparison.csv", all_single_comparison)
    write_csv("largest_30m_events.csv", [{k: v for k, v in r.items() if k != "ts"} for r in sorted(
        (r for r in measurements if r["horizon_minutes"] == 30 and r["status"] == "valid"), key=lambda r: -r["excursion_ticks"])])
    primary = sorted([r for r in rankings if r["primary_eligible_n_ge_5"]], key=lambda r: -r["median_excursion_ticks"])
    all30 = sorted([r for r in rankings if r["sample"] == "all" and r["horizon_minutes"] == 30], key=lambda r: -r["median_excursion_ticks"])
    validation = {
        "price_audit": price_audit, "calendar_audit": calendar_audit,
        "study": {"start_inclusive_utc": iso(START), "end_exclusive_utc": iso(END), "start_inclusive_ny_date": "2025-10-17", "end_exclusive_ny_date": "2026-10-17", "last_partial_day_excluded": "2026-10-17", "tick_size": TICK, "pip_size": PIP, "ticks_per_pip": 2},
        "self_checks": checks,
        "measurement_status_counts": {str(h): dict(collections.Counter(r["status"] for r in measurements if r["horizon_minutes"] == h)) for h in (15, 30, 60)},
        "control_status_counts": dict(collections.Counter(r["control_status"] for r in measurements)),
        "timestamp_observations": len(observations), "simultaneous_multi_category_bundles": sum(r["is_bundle"] for r in observations),
        "events_with_exact_15_minute_grid": sum(r["ts"] % BAR == 0 for r in observations),
        "valid_30m_non_speech_single_category_events": sum(r["status"] == "valid" and r["horizon_minutes"] == 30 and not r["is_bundle"] and not r["is_speech_only"] for r in measurements),
        "isolated_valid_30m_events": sum(r["status"] == "valid" and r["horizon_minutes"] == 30 and r["isolated_30m"] and not r["is_speech_only"] for r in measurements),
        "control_unique_dates": len(set(r["control_ny"][:10] for r in matches)),
        "method": {
            "window": "Half-open [announcement, announcement+horizon); bars at the end boundary are excluded. All bars including adjacent pre-release close must exist and be valid.",
            "reference": "Close of the immediately adjacent 15-minute bar starting t-15 minutes; includes the opening jump at the release.",
            "primary_outcome": "Maximum absolute excursion from pre-release close: max(abs(window high-reference), abs(window low-reference)).",
            "range_sensitivity": "Window high minus window low, which does not include a jump completely outside the post-release range.",
            "isolation": "Single core category at the timestamp and no other non-speech core category in (t-30min,t+horizon). Same-family earlier/later events are still overlaps. Speech overlap reported separately; isolated_no_speech excludes those overlaps.",
            "bundles": "All distinct categories scheduled at identical timestamps are combined into one labeled package. They do not contribute to the isolated category ranking.",
            "central_bank_boundary": "Decision and press-conference categories remain separate. A conference exactly t+30m is outside the decision's 30m outcome and inside its 60m outcome; horizon-specific isolation flags reflect this.",
            "controls": "For each event: same New York wall-clock time, same year/month, Monday-Friday, distinct date, valid contiguous price window, no supplied calendar event within inclusive +/-60m. Source min_importance=0 supplies medium(0)/high(1); all categories and speeches block controls, with audited canceled artifacts excluded. Require at least 10 controls. Aggregate event-level baseline medians and ratios. Weekdays are mixed and control dates are reused across events, so these are descriptive seasonal baselines, not independent causal controls.",
            "sensitivity_comparison": "primary_comparison.csv fixes each category's isolated 30m cohort and measures all 15/30/60m outcomes on those same timestamps. Its horizon-specific overlap counts warn that a 60m result may include a later announcement. all_single_category_comparison.csv uses all single-category 30m cohorts regardless of neighboring announcements.",
            "bootstrap": "2,000 deterministic nonparametric bootstrap replicates of event timestamp/packages within each category. Percentile median intervals are descriptive, especially fragile at n<10; no hypothesis tests or multiple-comparison correction.",
        },
        "limitations": [
            "One year of continuous back-adjusted CME:6E1! 15-minute bars; not individual contract executions or a one-minute/tick study.",
            "Scheduled calendar associations cannot identify causal effects, trade profitability, or whether actual/forecast surprises drove the move.",
            "Unscheduled headlines, geopolitical events, positioning and non-calendar releases remain unobserved confounders.",
            "Calendar corrections, unavailable/canceled releases, and provider time/importance errors can affect event matching; classification audit records exclusions and timing repairs.",
            "The first study month and last calendar year are partial; yearly/monthly splits are descriptive and unequal in length.",
            "Rank selection across many categories is exploratory. Sparse quarterly/central-bank samples and overlapping uncertainty intervals limit claims about a single winner.",
        ],
    }
    write_json("validation.json", validation)
    write_json("summary.json", {"study": validation["study"], "price_source": price_audit,
                                "primary_30m_isolated_n_ge_5": primary, "all_30m_including_bundles": all30,
                                "primary_same_cohort_sensitivities": primary_comparison,
                                "measurement_status_counts": validation["measurement_status_counts"],
                                "limitations": validation["limitations"]})
    print(json.dumps({"study_bars": price_audit["study_bars"], "observations": len(observations), "primary_categories": len(primary),
                      "top_primary": [{k: r[k] for k in ("category", "n", "median_excursion_ticks", "median_range_ticks")} for r in primary[:15]],
                      "controls": validation["control_status_counts"]}, indent=2))


if __name__ == "__main__":
    main()
