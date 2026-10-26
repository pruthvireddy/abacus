#!/usr/bin/env python3
"""Independent OHLC oracle for the pre-news EMA20/50 15-minute observation.

This file deliberately does not import the new Pine indicator or the earlier
descriptive event-study implementation. It uses archived native chart prices
and the separately classified TradingView calendar. The final Pine indicator
uses that audited archive for history, then ForexFactory after the archive's
end. The rejected ForexFactory-only build remains available as audit evidence.

Run: python3 forex_news/news_ema_move_checks/validate.py
Optional: --include-ecb, --native-export PATH (new indicator's native CSV),
          --require-archive-parity (strict final historical signal/result check).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import fmean, median
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT.parent / "6e_news_study"
UTC = timezone.utc
NY = ZoneInfo("America/New_York")
CHICAGO = ZoneInfo("America/Chicago")
BAR = 900
PIP = 0.0001
TICK = 0.00005
START = int(datetime(2025, 10, 17, tzinfo=NY).timestamp())
END = int(datetime(2026, 10, 17, tzinfo=NY).timestamp())
HORIZONS = (5, 10, 15, 50, 100)
DEFAULT_CATEGORIES = {
    "us_employment_report", "us_cpi", "us_fomc_decision",
    "us_fomc_press_conference", "us_sp_pmi_flash", "us_ism_manufacturing",
}
ECB_CATEGORIES = {"eu_ecb_decision", "eu_ecb_press_conference"}
OHLC = ("open", "high", "low", "close")


def timestamp(value):
    if isinstance(value, (int, float)):
        return int(value / 1000 if value > 10**11 else value)
    if str(value).isdigit():
        number = int(value)
        return number // 1000 if number > 10**11 else number
    return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())


def iso(value, zone=UTC):
    return datetime.fromtimestamp(value, zone).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_prices():
    """Anchor prices to latest adjustment, carry older native EMA state forward."""
    paths = sorted(SOURCES.glob("prices_*_native.csv"),
                   key=lambda p: ("recent" not in p.name, p.name))
    if not paths:
        raise RuntimeError("No native price exports")
    merged, audit = {}, []
    for path in paths:
        raw_rows = list(csv.DictReader(path.open()))
        local = {}
        for raw in raw_rows:
            t = timestamp(raw["time"])
            row = {name: float(raw[name]) for name in OHLC}
            if t % BAR or not all(math.isfinite(x) for x in row.values()):
                raise AssertionError(f"Invalid native price row {path.name}: {t}")
            if not row["low"] <= min(row["open"], row["close"]) + 1e-10:
                raise AssertionError("Low exceeds open/close")
            if not row["high"] + 1e-10 >= max(row["open"], row["close"]):
                raise AssertionError("High below open/close")
            if t in local:
                raise AssertionError("Unexpected duplicate native timestamp")
            row.update(native_fast=float(raw["Fast EMA"]) if raw.get("Fast EMA") else None,
                       native_slow=float(raw["Slow EMA"]) if raw.get("Slow EMA") else None,
                       source=path.name)
            local[t] = row
        recurrence = {}
        ordered = sorted(local)
        for key, length in (("native_fast", 20), ("native_slow", 50)):
            errors = []
            for a, b in zip(ordered, ordered[1:]):
                previous, current = local[a][key], local[b][key]
                if previous is not None and current is not None:
                    expected = previous + (local[b]["close"] - previous) * 2 / (length + 1)
                    errors.append(abs(expected - current))
            recurrence[key] = {"length": length, "pairs": len(errors),
                               "maximum_abs_error": max(errors, default=None)}
            assert errors and max(errors) < 1e-12, recurrence
        overlaps = sorted(merged.keys() & local.keys())
        differences = [merged[t][k] - local[t][k] for t in overlaps for k in OHLC]
        offset = median(differences) if differences else 0.0
        if differences and max(differences) - min(differences) > 1e-10:
            raise AssertionError("Price exports conflict beyond a constant adjustment")
        for t, row in local.items():
            if t not in merged:
                adjusted = dict(row)
                for key in (*OHLC, "native_fast", "native_slow"):
                    if adjusted[key] is not None:
                        adjusted[key] += offset
                merged[t] = adjusted
        audit.append({"file": str(path), "sha256": sha(path), "rows": len(local),
                      "first_bar_utc": iso(min(local)), "last_bar_utc": iso(max(local)),
                      "overlap_bars": len(overlaps), "offset_to_anchor": offset,
                      "native_ema_recurrence": recurrence})

    times = sorted(merged)
    seed = next(t for t in times if merged[t]["native_fast"] is not None
                and merged[t]["native_slow"] is not None)
    fast, slow = merged[seed]["native_fast"], merged[seed]["native_slow"]
    for t in times:
        row = merged[t]
        if t < seed:
            row["fast"] = row["slow"] = None
            continue
        if t > seed:
            fast += (row["close"] - fast) * (2 / 21)
            slow += (row["close"] - slow) * (2 / 51)
        row["fast"], row["slow"] = fast, slow
    audit.append({"continuous_ema_seed_utc": iso(seed),
                  "seed_source": merged[seed]["source"],
                  "explanation": "Native older EMA seed, recursively continued through merged OHLC; "
                                 "recent export independently warm-started and initially has blank EMAs.",
                  "total_bars": len(times),
                  "study_bars": sum(START <= t < END for t in times)})
    return merged, times, audit


def read_events(categories):
    path = SOURCES / "calendar_classification.json"
    source = json.loads(path.read_text())
    groups, skipped, duplicate_rows, seen = defaultdict(list), [], [], set()
    for event in source["events"]:
        category = event["category"]
        if category not in categories:
            continue
        t = timestamp(event["date"])
        if not START <= t < END:
            continue
        if event.get("excluded_from_analysis"):
            skipped.append({"event_utc": iso(t), "category": category,
                            "reason": event.get("exclusion_reason")})
            continue
        key = (t, event.get("country"), event["title"], event.get("period"), category)
        if key in seen:
            duplicate_rows.append(key)
            continue
        seen.add(key)
        groups[t].append(event)
    audit = {"source": str(path), "sha256": sha(path),
             "provider": "TradingView historical economic calendar (archived)",
             "provider_coverage_note": "The final chart indicator uses the audited archive "
             "for history through 2026-10-17, and ForexFactory thereafter. An earlier "
             "ForexFactory-only build had correct statistics arithmetic but inaccurate "
             "historical event coverage and was replaced.",
             "selected_categories": sorted(categories), "selected_component_rows": len(seen),
             "unique_event_timestamps": len(groups), "duplicate_source_rows_removed": len(duplicate_rows),
             "excluded_source_rows": skipped,
             "simultaneous_component_rows_collapsed": sum(len(x)-1 for x in groups.values()),
             "no_isolation_filter": True}
    return groups, audit


def audit_embedded_archive():
    """Audit generated archive against original classified rows without builder imports."""
    path = ROOT / "news_ema_calendar_archive.json"
    if not path.exists():
        return {"available": False}
    archive = json.loads(path.read_text())
    source = json.loads((SOURCES / "calendar_classification.json").read_text())
    code_for = {row['category']: row['code'] for row in archive['category_map']}
    begin = timestamp(archive['coverage_start_inclusive'])
    end = timestamp(archive['coverage_end_exclusive'])
    expected = {}
    for row in source['events']:
        t = timestamp(row['date'])
        if row['category'] not in code_for or not begin <= t < end or row.get('excluded_from_analysis'):
            continue
        key = (t*1000, row['currency'], row['title'])
        value = (code_for[row['category']], row['importance'])
        if key in expected:
            assert expected[key] == value
        expected[key] = value
    actual = {(r['timestamp_ms'], r['currency'], r['title']):
                  (r['category_code'], r['importance']) for r in archive['components']}
    assert expected == actual, "Generated archive components differ from classified input"
    counts = Counter((key[0], value[0], value[1]) for key, value in expected.items())
    recorded = {(r['timestamp_ms'], r['category_code'], r['importance']): r['components']
                for r in archive['compact_records']}
    assert dict(counts) == recorded, "Compact archive counts differ from distinct source titles"
    pine_path = ROOT.parent / "news_ema_move.pine"
    packed = re.search(r'string packed = "([^"\n]+)"', pine_path.read_text())
    assert packed, "No embedded historical calendar in Pine"
    embedded = {}
    for text in packed[1].split(';'):
        t, code, impact, count = map(int, text.split(':'))
        assert (t, code, impact) not in embedded
        embedded[t, code, impact] = count
    assert embedded == recorded, "Embedded Pine archive differs from audited generated JSON"
    assert all(t % (BAR*1000) == 0 for t, _, _ in embedded)
    return {"available": True, "classified_input_sha256": sha(SOURCES / "calendar_classification.json"),
            "generated_archive_sha256": sha(path), "indicator_sha256": sha(pine_path),
            "distinct_title_components": len(expected), "compact_records": len(recorded),
            "all_category_timestamps": len({t for t, _, _ in recorded}),
            "default_us_timestamps": len({t for t, code, _ in recorded if code <= 5}),
            "exact_source_component_equality": True, "exact_compact_count_equality": True,
            "exact_embedded_pine_record_equality": True, "all_timestamps_on_15m_grid": True}


def excursion(side, entry, bars):
    high = max(x["high"] for x in bars)
    low = min(x["low"] for x in bars)
    if side == 1:
        mfe, mae = max(0.0, high-entry), max(0.0, entry-low)
    else:
        mfe, mae = max(0.0, entry-low), max(0.0, high-entry)
    return mfe/PIP, mae/PIP, side*(bars[-1]["close"]-entry)/PIP


def observations(groups, prices, times):
    indices = {t: i for i, t in enumerate(times)}
    accepted, skipped, long_rows = [], [], []
    for t, components in sorted(groups.items()):
        reason = None
        if t % BAR:
            reason = "event_not_on_15_minute_grid"
        elif t-BAR not in prices:
            reason = "missing_candle_closing_exactly_at_event"
        elif t not in prices:
            reason = "missing_event_bar"
        elif prices[t-BAR]["fast"] is None or prices[t-BAR]["slow"] is None:
            reason = "cloud_not_ready"
        elif prices[t-BAR]["fast"] == prices[t-BAR]["slow"]:
            reason = "flat_cloud"
        if reason:
            skipped.append({"event_utc": iso(t), "reason": reason,
                            "titles": "; ".join(sorted({e['title'] for e in components}))})
            continue
        source = prices[t-BAR]
        side = 1 if source["fast"] > source["slow"] else -1
        index = indices[t]
        row = {"event_epoch": t, "event_utc": iso(t), "event_ny": iso(t, NY),
               "entry_close_utc": iso(t), "entry_bar_open_utc": iso(t-BAR),
               "entry_month_chicago": datetime.fromtimestamp(t, CHICAGO).strftime("%Y-%m"),
               "side": "Long" if side == 1 else "Short", "direction": side,
               "entry_price": source["close"], "fast_ema20": source["fast"],
               "slow_ema50": source["slow"], "component_rows": len(components),
               "categories": "; ".join(sorted({e['category'] for e in components})),
               "event_titles": "; ".join(sorted({e['title'] for e in components})),
               "event_ids": "; ".join(sorted({str(e.get('id', '')) for e in components}))}
        for horizon in HORIZONS:
            window = [prices[s] for s in times[index:index+horizon]]
            # Measurement horizons are existing chart bars, matching Pine [H].
            complete = len(window) == horizon and times[index+horizon-1] + BAR <= END
            end = times[index+horizon-1] + BAR if complete else None
            mfe, mae, delta = excursion(side, source["close"], window) if complete else (None,)*3
            for key, value in (("closed", int(complete)), ("mfe_pips", mfe),
                               ("mae_pips", mae), ("close_pips", delta),
                               ("exit_close_utc", iso(end) if complete else "")):
                row[f"h{horizon}_{key}"] = value
            long_rows.append({**{k: row[k] for k in ("event_epoch", "event_utc", "entry_close_utc",
                           "entry_bar_open_utc", "entry_month_chicago", "side", "direction",
                           "entry_price", "fast_ema20", "slow_ema50", "event_titles", "categories")},
                              "horizon_bars": horizon, "closed": int(complete),
                              "exit_close_utc": iso(end) if complete else "",
                              "mfe_pips": mfe, "mae_pips": mae, "close_pips": delta})
        accepted.append(row)
    assert len({x["event_epoch"] for x in accepted}) == len(accepted)
    return accepted, skipped, long_rows


def summarize(rows, signals=None):
    done = [r for r in rows if r["closed"]]
    return {"signals": len(rows) if signals is None else signals, "closed": len(done),
            "pending": len(rows)-len(done),
            "average_mfe_pips": fmean(r["mfe_pips"] for r in done) if done else None,
            "average_mae_pips": fmean(r["mae_pips"] for r in done) if done else None,
            "average_close_pips": fmean(r["close_pips"] for r in done) if done else None,
            "favorable_close_percent": 100*fmean(r["close_pips"] > 0 for r in done) if done else None,
            "mfe_above_mae_percent": 100*fmean(r["mfe_pips"]-r["mae_pips"] > 1e-6
                                                    for r in done) if done else None}


def display_expectations(summary, historical_source_corrected):
    """Reviewable raw numbers and expected strings for the two default tables."""
    def cell(value, digits=2, suffix=""):
        return {"raw": value, "display": f"{value:.{digits}f}"+suffix if value is not None else "—"}
    overall = []
    for row in summary['overall']:
        mfe, mae = row['average_mfe_pips'], row['average_mae_pips']
        ratio = mfe/mae if mae is not None and mae > 0 else None
        overall.append({"Bars": cell(row['horizon_bars'], 0), "N": cell(row['closed'], 0),
                        "AVG MFE (pips)": cell(mfe), "AVG MAE (pips)": cell(mae),
                        "AVG CLOSE Δ (pips)": cell(row['average_close_pips']),
                        "FAVORABLE CLOSE": cell(row['favorable_close_percent'], 1, "%"),
                        "MFE > MAE": cell(row['mfe_above_mae_percent'], 1, "%"),
                        "MFE / MAE": cell(ratio, 3, "x")})
    monthly = []
    for row in reversed(summary['monthly_h5_displayed_last8']):
        mfe, mae = row['average_mfe_pips'], row['average_mae_pips']
        ratio = mfe/mae if mae is not None and mae > 0 else None
        monthly.append({"Month": row['month_chicago'], "Signals": cell(row['signals'], 0),
                        "Closed": cell(row['closed'], 0), "Avg MAE (pips)": cell(mae),
                        "Avg MFE (pips)": cell(mfe), "Avg Δ (MFE−MAE)": cell(mfe-mae if mfe is not None else None),
                        "Avg Candles": cell(5 if row['closed'] else None),
                        "Favorable Close %": cell(row['favorable_close_percent'], 1, "%"),
                        "MFE / MAE": cell(ratio, 3, "x")})
    return {"historical_source_corrected": historical_source_corrected,
            "status": "Historical archive replaces inaccurate old ForexFactory seed history."
                      if historical_source_corrected else "Rejected historical source; arithmetic-only fixture.",
            "native_export_sha256": summary.get('sha256'),
            "rounding": "Raw independent OHLC averages shown alongside fixed display precision: "
                        "distances 2 decimals, percentages 1 decimal, ratios 3 decimals. "
                        "Binary half-cent ties can differ in the last digit; raw values retained for review.",
            "overall_rows": overall, "monthly_h5_rows_newest_first": monthly}


def semantic_checks():
    """Small counterexamples for mistakes that a populated table can conceal."""
    prior = {"high": 10000, "low": 0, "close": 100}
    after = [{"high": 104, "low": 98, "close": 103},
             {"high": 105, "low": 97, "close": 101}]
    assert excursion(1, prior["close"], after) == (50000, 30000, 10000)
    assert excursion(-1, prior["close"], after) == (30000, 50000, -10000)
    # Post-release cloud changes cannot change a frozen short observation.
    frozen_side = -1 if 99 < 100 else 1
    hypothetical_next_fast, hypothetical_next_slow = 102, 100
    assert hypothetical_next_fast > hypothetical_next_slow
    assert excursion(frozen_side, 100, after) == (30000, 50000, -10000)
    # The timestamp of entry determines ownership even if exit crosses a month.
    entry = int(datetime(2026, 3, 31, 23, 45, tzinfo=CHICAGO).timestamp())
    finish = entry + 5*BAR
    assert datetime.fromtimestamp(entry, CHICAGO).strftime("%Y-%m") == "2026-03"
    assert datetime.fromtimestamp(finish, CHICAGO).strftime("%Y-%m") == "2026-04"
    # Exercise the complete observation path with deliberately extreme entry
    # wicks, a subsequent opposite cloud, duplicate simultaneous components,
    # and a month boundary. None may alter the frozen short or its ownership.
    fixture = {entry-BAR: {**prior, "open": 100, "fast": 99, "slow": 100}}
    for i, bar in enumerate([after[0]] + [after[1]]*4):
        fixture[entry+i*BAR] = {**bar, "open": 100, "fast": 102, "slow": 100}
    components = [{"title": title, "category": "test", "id": i}
                  for i, title in enumerate(("Payrolls", "Unemployment"))]
    full, skipped, _ = observations({entry: components}, fixture, sorted(fixture))
    assert not skipped and len(full) == 1
    assert full[0]['direction'] == -1
    assert full[0]['h5_mfe_pips'] == 30000 and full[0]['h5_mae_pips'] == 50000
    assert full[0]['h5_closed'] == 1 and full[0]['h10_closed'] == 0
    assert full[0]['entry_month_chicago'] == "2026-03"
    partial_fixture = {k: v for k, v in fixture.items() if k != max(fixture)}
    incomplete, _, _ = observations({entry: components}, partial_fixture,
                                   sorted(partial_fixture))
    assert incomplete[0]['h5_closed'] == 0
    assert incomplete[0]['h5_mfe_pips'] is None
    return {"entry_candle_extremes_excluded": True, "frozen_entry_direction": True,
            "long_and_short_excursion_signs": True, "entry_period_ownership": True,
            "incomplete_horizon_excluded": True, "simultaneous_components_collapse": True}


def compare_native_export(path, oracle_events, stitched_prices, require_archive_parity=False):
    """Use the indicator's own exported signal times, independently measure OHLC."""
    raw = list(csv.DictReader(path.open()))
    if not raw:
        raise RuntimeError("Empty native indicator CSV")
    names = list(raw[0])
    def field(wanted, required=True):
        if wanted in names:
            return wanted
        candidates = [x for x in names if x.lower().endswith(wanted.lower())]
        if len(candidates) == 1:
            return candidates[0]
        if required:
            raise RuntimeError(f"Native export missing/ambiguous {wanted!r}; fields={names}")
        return None
    side_field = field("News measured side")
    raw_side_field = field("News entry side")
    event_field = field("News event timestamp")
    fast_field = field("Fast EMA (15m)")
    slow_field = field("Slow EMA (15m)")
    components_field = field("News release components", required=False)
    rows, times, actual_events, actual_horizons = {}, [], [], []
    for original in raw:
        t = timestamp(original['time'])
        if t in rows or t % BAR:
            raise AssertionError("Duplicate/off-grid native indicator OHLC")
        row = {key: float(original[key]) for key in OHLC}
        row['source'] = original
        rows[t] = row
        times.append(t)
    times.sort()
    archived = {r['event_epoch']: r for r in oracle_events}
    direction_checks, timestamp_checks, prices_errors, ema_errors = [], [], [], []
    raw_selected_count = 0
    for i, t in enumerate(times):
        raw_row = rows[t]['source']
        raw_side = int(float(raw_row[raw_side_field] or 0))
        raw_selected_count += raw_side != 0
        side = int(float(raw_row[side_field] or 0))
        if not side:
            continue
        if side not in (-1, 1):
            raise AssertionError("Unexpected native signal side")
        event_t = timestamp(float(raw_row[event_field])) if raw_row[event_field] else t+BAR
        fast, slow = float(raw_row[fast_field]), float(raw_row[slow_field])
        direction_checks.append(side == (1 if fast > slow else -1 if fast < slow else 0))
        timestamp_checks.append(event_t == t+BAR)
        row = {"event_epoch": event_t, "event_utc": iso(event_t),
               "event_ny": iso(event_t, NY), "entry_close_utc": iso(t+BAR),
               "entry_bar_open_utc": iso(t),
               "entry_month_chicago": datetime.fromtimestamp(event_t, CHICAGO).strftime("%Y-%m"),
               "side": "Long" if side == 1 else "Short", "direction": side,
               "entry_price": rows[t]['close'], "fast_ema20": fast, "slow_ema50": slow,
               "component_rows": raw_row.get(components_field, "") if components_field else "",
               "archived_calendar_match": event_t in archived,
               "event_titles": archived[event_t]['event_titles'] if event_t in archived else "Live ForexFactory event absent from archived selected calendar"}
        if t in stitched_prices:
            prices_errors.extend(abs(rows[t][k] - stitched_prices[t][k]) for k in OHLC)
            if stitched_prices[t]['fast'] is not None:
                ema_errors.extend((abs(fast-stitched_prices[t]['fast']),
                                   abs(slow-stitched_prices[t]['slow'])))
        for horizon in HORIZONS:
            window_times = times[i+1:i+1+horizon]
            complete = len(window_times) == horizon
            values = [rows[s] for s in window_times]
            mfe, mae, delta = excursion(side, rows[t]['close'], values) if complete else (None,)*3
            for key, value in (("closed", int(complete)), ("mfe_pips", mfe),
                               ("mae_pips", mae), ("close_pips", delta)):
                row[f"h{horizon}_{key}"] = value
            actual_horizons.append({"event_epoch": event_t, "event_utc": iso(event_t),
                                    "entry_month_chicago": row['entry_month_chicago'],
                                    "side": row['side'], "direction": side,
                                    "entry_price": row['entry_price'], "horizon_bars": horizon,
                                    "closed": int(complete),
                                    "exit_close_utc": iso(window_times[-1]+BAR) if complete else "",
                                    "mfe_pips": mfe, "mae_pips": mae, "close_pips": delta})
        actual_events.append(row)
    assert all(direction_checks), "Native entry did not follow preceding confirmed EMA cloud"
    assert all(timestamp_checks), "Native event timestamp not at preceding bar close"
    assert len({r['event_epoch'] for r in actual_events}) == len(actual_events)
    overall = [{"horizon_bars": h,
                **summarize([r for r in actual_horizons if r['horizon_bars'] == h])}
               for h in HORIZONS]
    months = sorted({r['entry_month_chicago'] for r in actual_events})
    monthly = [{"month_chicago": m, "horizon_bars": 5,
                **summarize([r for r in actual_horizons if r['horizon_bars'] == 5
                             and r['entry_month_chicago'] == m])} for m in months]
    actual = {r['event_epoch']: r for r in actual_events}
    # Calendar comparison applies only where the native export has the entry bar.
    expected_times = {t for t in archived if t-BAR in rows}
    actual_times = set(actual)
    shared = expected_times & actual_times
    coverage = {
        "native_export_first_bar_utc": iso(min(times)),
        "native_export_last_bar_utc": iso(max(times)),
        "native_rows": len(times), "raw_selected_entries": raw_selected_count,
        "measured_entries": len(actual_events),
        "archived_selected_events_with_entry_bar_in_export": len(expected_times),
        "shared_calendar_event_times": len(shared),
        "native_only_event_times": [iso(t) for t in sorted(actual_times-expected_times)],
        "archived_only_event_times": [iso(t) for t in sorted(expected_times-actual_times)],
        "shared_direction_disagreements": [{"event_utc": iso(t), "native": actual[t]['direction'],
                          "archived_oracle": archived[t]['direction']} for t in sorted(shared)
                                          if actual[t]['direction'] != archived[t]['direction']],
        "max_abs_native_vs_archived_entry_ohlc_difference": max(prices_errors, default=None),
        "max_abs_native_vs_stitched_ema_difference_at_entries": max(ema_errors, default=None),
    }
    # Reconcile every complete native observation to independent archived-event
    # OHLC measurements, rather than merely checking its aggregate table.
    mismatches = []
    comparisons = 0
    for t in sorted(shared):
        expected, observed = archived[t], actual[t]
        for horizon in HORIZONS:
            for key in ("closed", "mfe_pips", "mae_pips", "close_pips"):
                name = f"h{horizon}_{key}"
                a, b = expected[name], observed[name]
                comparisons += 1
                if (a is None) != (b is None) or (a is not None and abs(a-b) > 1e-8):
                    mismatches.append({"event_utc": iso(t), "field": name,
                                       "archived_oracle": a, "native_ohlc": b})
    strict_pass = (expected_times == actual_times and not coverage['shared_direction_disagreements']
                   and not mismatches)
    write_csv(ROOT / "native_events.csv", actual_events)
    write_csv(ROOT / "native_horizons.csv", actual_horizons)
    write_csv(ROOT / "native_overall.csv", overall)
    write_csv(ROOT / "native_monthly_h5.csv", monthly)
    result = {"path": str(path), "sha256": sha(path), "coverage": coverage,
              "method": "Native exported News measured side fixes entry timestamps and sides; "
                        "independent Python OHLC slicing supplies all horizon excursions.",
              "checks": {"entry_side_matches_same_bar_ema_cloud": all(direction_checks),
                         "news_timestamp_equals_entry_close": all(timestamp_checks),
                         "one_entry_per_timestamp": True,
                         "exact_archived_event_timestamp_set": expected_times == actual_times,
                         "all_shared_directions_match_archive": not coverage['shared_direction_disagreements'],
                         "all_shared_horizon_values_match_archive": not mismatches},
              "archive_parity": {"required": require_archive_parity, "passed": strict_pass,
                                 "compared_horizon_fields": comparisons, "mismatches": mismatches},
              "direction_counts": dict(Counter(r['side'] for r in actual_events)),
              "overall": overall, "monthly_h5": monthly,
              "monthly_h5_displayed_last8": monthly[-8:]}
    (ROOT / "native_summary.json").write_text(json.dumps(result, indent=2)+"\n")
    (ROOT / "native_table_display_expectations.json").write_text(
        json.dumps(display_expectations(result, require_archive_parity), indent=2)+"\n")
    if require_archive_parity:
        assert strict_pass, "Historical archive native export differs from exact oracle timestamps/directions/results"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-ecb", action="store_true")
    parser.add_argument("--native-export", type=Path)
    parser.add_argument("--require-archive-parity", action="store_true")
    args = parser.parse_args()
    categories = DEFAULT_CATEGORIES | (ECB_CATEGORIES if args.include_ecb else set())
    prices, times, price_audit = read_prices()
    groups, calendar_audit = read_events(categories)
    events, skipped, horizons = observations(groups, prices, times)
    overall = [{"horizon_bars": h, **summarize([r for r in horizons if r['horizon_bars'] == h])}
               for h in HORIZONS]
    months = sorted({r['entry_month_chicago'] for r in events})
    monthly = [{"month_chicago": m, "horizon_bars": 5,
                **summarize([r for r in horizons if r['horizon_bars'] == 5
                             and r['entry_month_chicago'] == m])} for m in months]
    checks = semantic_checks()
    checks["one_observation_per_timestamp"] = len(events) == len({r['event_epoch'] for r in events})
    checks["all_entries_precede_event_bar"] = all(timestamp(r['entry_bar_open_utc'])+BAR
                                                    == r['event_epoch'] for r in events)
    checks["all_directions_match_preceding_cloud"] = all(r['direction'] ==
               (1 if r['fast_ema20'] > r['slow_ema50'] else -1) for r in events)
    assert all(checks.values())
    prefix = "oracle_with_ecb" if args.include_ecb else "oracle"
    write_csv(ROOT / f"{prefix}_events.csv", events)
    write_csv(ROOT / f"{prefix}_horizons.csv", horizons)
    write_csv(ROOT / f"{prefix}_overall.csv", overall)
    write_csv(ROOT / f"{prefix}_monthly_h5.csv", monthly)
    write_csv(ROOT / f"{prefix}_skipped_events.csv", skipped)
    summary = {"schema_version": 1,
               "method": "Frozen preceding 15m EMA20/50 direction; entry at its close; "
                         "each H observes event bar through Hth next confirmed chart bar; "
                         "no stop/target, fee, slippage or overlapping-observation suppression.",
               "study_start_inclusive_ny": iso(START, NY), "study_end_exclusive_ny": iso(END, NY),
               "table_timezone": "America/Chicago", "period_owner": "entry close/event timestamp",
               "units": "pips (0.0001); 2 6E standard ticks per pip",
               "price_audit": price_audit, "calendar_audit": calendar_audit,
               "embedded_archive_audit": audit_embedded_archive(),
               "accepted_observations": len(events), "skipped_observations": skipped,
               "direction_counts": dict(Counter(r['side'] for r in events)),
               "overall": overall, "monthly_h5_all": monthly,
               "monthly_h5_displayed_last8": monthly[-8:], "checks": checks,
               "native_indicator_comparison": "Not supplied; use --native-export and "
                                               "--require-archive-parity for the final historical build.",
               "limitations": ["Associated excursions after scheduled releases do not estimate causality.",
                               "Observation windows can overlap and are not separate executable trades.",
                               "Back-adjusted continuous futures prices; no assumed fill improvement."]}
    if args.native_export:
        summary["native_indicator_comparison"] = compare_native_export(args.native_export,
                                             events, prices, args.require_archive_parity)
    (ROOT / f"{prefix}_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"events": len(events), "directions": summary['direction_counts'],
                      "skipped": len(skipped), "checks": checks, "overall": overall}, indent=2))


if __name__ == "__main__":
    main()
