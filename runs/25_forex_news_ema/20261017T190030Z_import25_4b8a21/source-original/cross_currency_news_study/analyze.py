#!/usr/bin/env python3
"""Compare frozen pre-news EMA20/50 observations in native TradingView CSVs.

Run with no arguments to discover native_6*.csv beside this script and the
previously verified 6E export. Or pass repeated --input SYMBOL=PATH arguments.
All calculations use the standard library and write only inside this folder
(or the explicit --output directory), never the prior 6E validator's outputs.
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
from statistics import fmean, median
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
UTC = timezone.utc
NY = ZoneInfo("America/New_York")
CHICAGO = ZoneInfo("America/Chicago")
BAR = 900
HORIZONS = (5, 10, 15, 50, 100)
SYMBOLS = ("6E", "6B", "6J", "6S", "6C", "6A")
# Standard outright futures minimum fluctuations; independently checked by the
# accompanying product-specification review. No spread or micro assumptions.
TICKS = {"6E": .00005, "6B": .0001, "6J": .0000005,
         "6S": .00005, "6C": .00005, "6A": .00005}
NAMES = {"6E": "Euro", "6B": "British pound", "6J": "Japanese yen",
         "6S": "Swiss franc", "6C": "Canadian dollar", "6A": "Australian dollar"}
OHLC = ("open", "high", "low", "close")


def stamp(value):
    text = str(value)
    try:
        number = float(text)
    except ValueError:
        return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
    return int(round(number / 1000 if abs(number) > 1e11 else number))


def iso(t, zone=UTC):
    return datetime.fromtimestamp(t, zone).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        if not rows:
            return
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def archive_events(path):
    archive = json.loads(path.read_text())
    groups = defaultdict(list)
    labels = {r["category"]: r["label"] for r in archive["category_map"]}
    for row in archive["components"]:
        if row["category_code"] <= 5:
            groups[row["timestamp_ms"] // 1000].append(row)
    return dict(groups), labels, {
        "path": str(path.resolve()), "sha256": digest(path),
        "selected_categories": sorted({r["category"] for g in groups.values() for r in g}),
        "coverage_start_inclusive": archive["coverage_start_inclusive"],
        "coverage_end_exclusive": archive["coverage_end_exclusive"],
        "schedule_caveat": archive["schedule_caveat"],
    }


def excursion(side, entry, bars):
    highest = max(r["high"] for r in bars)
    lowest = min(r["low"] for r in bars)
    return (max(0., highest-entry) if side == 1 else max(0., entry-lowest),
            max(0., entry-lowest) if side == 1 else max(0., highest-entry),
            side * (bars[-1]["close"] - entry))


def read_export(symbol, path, tick, pip, archive, lookback_days):
    with path.open(newline="") as handle:
        raw = list(csv.DictReader(handle))
    if not raw:
        raise ValueError(f"{symbol}: empty export: {path}")
    names = list(raw[0])

    def column(wanted):
        if wanted in names:
            return wanted
        matches = [n for n in names if n.lower().endswith(wanted.lower())]
        if len(matches) != 1:
            raise ValueError(f"{symbol}: missing/ambiguous column {wanted!r}: {names}")
        return matches[0]

    fields = {k: column(k) for k in ("Fast EMA (15m)", "Slow EMA (15m)",
              "News entry side", "News measured side", "News event timestamp",
              "News release components")}
    bars = []
    for original in raw:
        t = stamp(original["time"])
        if t % BAR:
            raise AssertionError(f"{symbol}: off-grid bar {iso(t)}")
        row = {key: float(original[key]) for key in OHLC}
        assert all(math.isfinite(value) for value in row.values()), (symbol, t)
        assert row["low"] <= min(row["open"], row["close"]) + 1e-12, (symbol, t)
        assert row["high"] + 1e-12 >= max(row["open"], row["close"]), (symbol, t)
        row.update(time=t, source=original)
        for name, length in (("Fast EMA (15m)", 20), ("Slow EMA (15m)", 50)):
            cell = original[fields[name]]
            row[f"ema{length}"] = float(cell) if cell else None
        bars.append(row)
    bars.sort(key=lambda r: r["time"])
    by_time = {row["time"]: row for row in bars}
    assert len(by_time) == len(bars), f"{symbol}: duplicate bar timestamps"
    indices = {r["time"]: i for i, r in enumerate(bars)}
    start = bars[-1]["time"] - lookback_days * 86400
    recurrence = {}
    for length in (20, 50):
        errors = [abs(current[f"ema{length}"] - (prior[f"ema{length}"] +
                  (current["close"]-prior[f"ema{length}"]) * 2/(length+1)))
                  for prior, current in zip(bars, bars[1:])
                  if prior[f"ema{length}"] is not None and current[f"ema{length}"] is not None]
        assert errors and max(errors) < 1e-10, (symbol, "EMA recurrence", length, max(errors, default=None))
        recurrence[str(length)] = {"pairs": len(errors), "max_abs_error": max(errors)}
    entries, horizons = [], []
    raw_selected = 0
    for i, bar in enumerate(bars):
        original = bar["source"]
        side = int(float(original[fields["News measured side"]] or 0))
        selected = int(float(original[fields["News entry side"]] or 0))
        assert selected in (-1, 0, 1) and side in (-1, 0, 1)
        raw_selected += selected != 0
        assert selected == side, f"{symbol}: Signals to measure must be All"
        if not side:
            continue
        event = stamp(original[fields["News event timestamp"]])
        assert event == bar["time"] + BAR, (symbol, "Entry must close at event", iso(event))
        assert event >= start, (symbol, "Signal before lookback", iso(event))
        fast, slow = bar["ema20"], bar["ema50"]
        assert fast is not None and slow is not None
        cloud = 1 if fast > slow else -1 if fast < slow else 0
        assert cloud == side, (symbol, "Pre-news EMA direction", iso(event))
        assert event in archive, (symbol, "Unexpected selected calendar event", iso(event))
        components = archive[event]
        count = int(float(original[fields["News release components"]]))
        assert count == len(components), (symbol, "Calendar component count", iso(event), count, len(components))
        categories = "; ".join(sorted({r["category"] for r in components}))
        entry = {"symbol": symbol, "event_epoch": event, "event_utc": iso(event),
                 "event_ny": iso(event, NY), "entry_bar_open_utc": iso(bar["time"]),
                 "entry_month_chicago": datetime.fromtimestamp(event, CHICAGO).strftime("%Y-%m"),
                 "side": "Long" if side == 1 else "Short", "direction": side,
                 "entry_price": bar["close"], "fast_ema20": fast, "slow_ema50": slow,
                 "component_count": count, "categories": categories,
                 "event_titles": "; ".join(sorted({r["title"] for r in components}))}
        entries.append(entry)
        for h in HORIZONS:
            window = bars[i+1:i+1+h]
            complete = len(window) == h
            mfe, mae, change = excursion(side, bar["close"], window) if complete else (None,)*3
            row = {**entry, "horizon_bars": h, "complete": int(complete),
                   "exit_close_utc": iso(window[-1]["time"]+BAR) if complete else "",
                   "calendar_elapsed_minutes": (window[-1]["time"]+BAR-event)/60 if complete else None,
                   "mfe_price": mfe, "mae_price": mae, "close_price": change}
            for unit, divisor in (("ticks", tick), ("pips", pip), ("percent", bar["close"]/100)):
                for name, value in (("mfe", mfe), ("mae", mae), ("close", change)):
                    row[f"{name}_{unit}"] = value/divisor if divisor is not None and value is not None else None
            horizons.append(row)
    accepted = {r["event_epoch"] for r in entries}
    expected, exclusions = set(), []
    for event in sorted(archive):
        if not start <= event <= bars[-1]["time"]+BAR:
            continue
        bar = by_time.get(event-BAR)
        reason = ("entry_bar_unavailable" if bar is None else
                  "EMA_not_ready" if bar["ema20"] is None or bar["ema50"] is None else
                  "flat_cloud" if bar["ema20"] == bar["ema50"] else None)
        if reason:
            exclusions.append({"symbol": symbol, "event_utc": iso(event), "reason": reason})
        else:
            expected.add(event)
    assert expected == accepted, {"symbol": symbol,
        "missing_native_events": [iso(t) for t in sorted(expected-accepted)],
        "extra_native_events": [iso(t) for t in sorted(accepted-expected)]}
    assert len(accepted) == len(entries), f"{symbol}: simultaneous reports not collapsed"
    audit = {"symbol": symbol, "name": NAMES.get(symbol, symbol),
             "path": str(path.resolve()), "sha256": digest(path), "bars": len(bars),
             "first_bar_utc": iso(bars[0]["time"]), "last_bar_utc": iso(bars[-1]["time"]),
             "lookback_start_inclusive_utc": iso(start), "tick_size": tick, "pip_size": pip,
             "raw_selected_entries": raw_selected, "measured_entries": len(entries),
             "first_event_utc": iso(min(accepted)) if accepted else None,
             "last_event_utc": iso(max(accepted)) if accepted else None,
             "direction_counts": dict(Counter(r["side"] for r in entries)),
             "EMA_recurrence": recurrence, "exact_default_archive_event_parity": True,
             "expected_events_unavailable_or_not_ready": exclusions,
             "all_sides_match_pre_news_cloud": True, "all_entry_closes_equal_scheduled_UTC_time": True,
             "one_observation_per_event_timestamp": True,
             "largest_adjacent_bar_gap_minutes": max((b["time"]-a["time"])/60 for a,b in zip(bars,bars[1:]))}
    return entries, horizons, audit


def summarize(rows, allowed_complete=None):
    done = [r for r in rows if r["complete"] and (allowed_complete is None or r["event_epoch"] in allowed_complete)]
    result = {"signals": len(rows), "complete": len(done), "excluded_or_pending": len(rows)-len(done),
              "long_signals": sum(r["direction"] == 1 for r in rows),
              "short_signals": sum(r["direction"] == -1 for r in rows),
              "favorable_close_percent": 100*fmean(r["close_price"] > 0 for r in done) if done else None,
              "mfe_above_mae_percent": 100*fmean(r["mfe_price"]-r["mae_price"] >
                                       1e-10*max(1., r["mfe_price"], r["mae_price"]) for r in done) if done else None}
    for unit in ("price", "ticks", "pips", "percent"):
        available = [r for r in done if r[f"mfe_{unit}"] is not None]
        for statistic, func in (("average", fmean), ("median", median)):
            for measure in ("mfe", "mae", "close"):
                result[f"{statistic}_{measure}_{unit}"] = func(r[f"{measure}_{unit}"] for r in available) if available else None
    result["mfe_mae_ratio"] = (result["average_mfe_price"]/result["average_mae_price"]
                               if result["average_mae_price"] else None)
    return result


def aggregate(all_rows, all_entries, symbols):
    event_sets = {s: {r["event_epoch"] for r in all_entries if r["symbol"] == s} for s in symbols}
    common = set.intersection(*(event_sets[s] for s in symbols))
    common_complete = {h: set.intersection(*(
        {r["event_epoch"] for r in all_rows if r["symbol"] == s and r["horizon_bars"] == h and r["complete"]}
        for s in symbols)) for h in HORIZONS}
    overall, categories, months = [], [], []
    for scope in ("all_available", "common_events"):
        for s in symbols:
            for h in HORIZONS:
                rows = [r for r in all_rows if r["symbol"] == s and r["horizon_bars"] == h
                        and (scope == "all_available" or r["event_epoch"] in common)]
                allowed = common_complete[h] if scope == "common_events" else None
                group = {"scope": scope, "symbol": s, "horizon_bars": h}
                overall.append({**group, **summarize(rows, allowed)})
                for category in sorted({r["categories"] for r in rows}):
                    categories.append({**group, "categories": category,
                                       **summarize([r for r in rows if r["categories"] == category], allowed)})
                for month in sorted({r["entry_month_chicago"] for r in rows}):
                    months.append({**group, "entry_month_chicago": month,
                                   **summarize([r for r in rows if r["entry_month_chicago"] == month], allowed)})
    comparison = {"symbols": symbols, "common_signal_timestamps": len(common),
                  "common_first_event_utc": iso(min(common)) if common else None,
                  "common_last_event_utc": iso(max(common)) if common else None,
                  "common_complete_count_by_horizon": {str(h): len(common_complete[h]) for h in HORIZONS},
                  "common_event_times_utc": [iso(t) for t in sorted(common)],
                  "noncommon_event_times_by_symbol": {s: [iso(t) for t in sorted(event_sets[s]-common)] for s in symbols},
                  "fair_comparison_rule": "For each horizon, use exactly the same UTC event timestamps with a complete horizon in every instrument. EMA direction remains instrument-specific."}
    return overall, categories, months, comparison


def semantic_checks():
    post = [{"high": 104, "low": 98, "close": 103}, {"high": 105, "low": 97, "close": 101}]
    assert excursion(1, 100, post) == (5, 3, 1)
    assert excursion(-1, 100, post) == (3, 5, -1)
    # The intentionally huge pre-event wick is not part of the post-entry slice.
    fixture = [{"high": 1000, "low": 0, "close": 100}, *post]
    assert excursion(-1, fixture[0]["close"], fixture[1:3]) == (3, 5, -1)
    assert stamp("1791462600000") == stamp("1791462600")
    assert stamp("2026-10-08T12:30:00Z") == stamp("2026-10-08T08:30:00-04:00")
    assert datetime.fromtimestamp(stamp("2026-04-01T03:45:00Z"), CHICAGO).strftime("%Y-%m") == "2026-03"
    return {"long_short_excursion_signs": True, "entry_candle_extremes_excluded": True,
            "UTC_epoch_and_timezone_equivalence": True, "entry_period_ownership": True}


def write_report(path, report, categories):
    comparison = report["comparison"]
    lines = ["News EMA Move: currency futures test", "",
             "Rule: use EMA20/50 direction on the 15-minute candle closing at the",
             "scheduled release, enter at that close, and freeze the side. Measure",
             "the next H actual chart candles, including the release candle.", "",
             "News sample: U.S. employment, CPI, FOMC decision/projections, FOMC",
             "conference, flash PMI, and ISM manufacturing. One entry per timestamp.",
             "The same U.S. timestamps are tested across all supplied currencies.", "",
             f"Common event timestamps: {comparison['common_signal_timestamps']}",
             f"First event UTC: {comparison['common_first_event_utc']}",
             f"Last event UTC: {comparison['common_last_event_utc']}", "",
             "Distances below are standard outright futures TICKS, not dollars.",
             "Close is the signed directional price change at H; positive is favorable.",
             "Ratio is average MFE / average MAE; it is not profit factor.", ""]
    def number(row, key, digits=2):
        return f"{row[key]:.{digits}f}" if row[key] is not None else "--"
    header = "Symbol   N    Avg MFE   Avg MAE   Avg Close  Favorable %  MFE/MAE"
    for horizon in HORIZONS:
        lines += [f"H = {horizon} following 15-minute chart candles", header]
        for symbol in report["symbols"]:
            row = next(r for r in report["overall"] if r["scope"] == "common_events" and
                       r["symbol"] == symbol and r["horizon_bars"] == horizon)
            lines.append(f"{symbol:<7} {row['complete']:>3} {number(row,'average_mfe_ticks'):>10}"
                         f" {number(row,'average_mae_ticks'):>9} {number(row,'average_close_ticks'):>11}"
                         f" {number(row,'favorable_close_percent',1):>12} {number(row,'mfe_mae_ratio',3):>8}")
        lines.append("")
    lines += ["H = 5 detail by news category", ""]
    labels = report["category_labels"]
    for category in sorted({r["categories"] for r in categories}):
        label = " + ".join(labels.get(k,k) for k in category.split("; "))
        lines += [label, header]
        for symbol in report["symbols"]:
            row = next((r for r in categories if r["scope"] == "common_events" and
                        r["symbol"] == symbol and r["horizon_bars"] == 5 and r["categories"] == category), None)
            if row is not None:
                lines.append(f"{symbol:<7} {row['complete']:>3} {number(row,'average_mfe_ticks'):>10}"
                             f" {number(row,'average_mae_ticks'):>9} {number(row,'average_close_ticks'):>11}"
                             f" {number(row,'favorable_close_percent',1):>12} {number(row,'mfe_mae_ratio',3):>8}")
        lines.append("")
    lines += ["All category/horizon values, including medians and percent-normalized",
              "distances, are in by_category.csv. Month/horizon values are in monthly.csv.", "",
              "No fees, spreads, slippage, stops, or targets are modeled. FOMC decision",
              "and conference windows can overlap; observations are not independent.",
              "The historical schedule includes later corrections. These descriptive",
              "results do not establish event causality or future profitability.", ""]
    path.write_text("\n".join(lines))


def parse_assignments(values, numeric=False):
    parsed = {}
    for value in values:
        symbol, assigned = value.split("=", 1)
        symbol = symbol.upper()
        if symbol in parsed:
            raise ValueError(f"Duplicate assignment: {symbol}")
        parsed[symbol] = float(assigned) if numeric else Path(assigned)
        if numeric and parsed[symbol] <= 0:
            raise ValueError("Unit sizes must be positive")
    return parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", default=[], metavar="SYMBOL=PATH")
    parser.add_argument("--tick", action="append", default=[], metavar="SYMBOL=SIZE")
    parser.add_argument("--pip", action="append", default=[], metavar="SYMBOL=SIZE")
    parser.add_argument("--lookback-days", type=int, default=365)
    parser.add_argument("--calendar", type=Path, default=ROOT.parent/"news_ema_move_checks"/"news_ema_calendar_archive.json")
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    inputs = parse_assignments(args.input)
    if not inputs:
        inputs = {s: ROOT/f"native_{s}.csv" for s in SYMBOLS if (ROOT/f"native_{s}.csv").exists()}
        if "6E" not in inputs:
            inputs["6E"] = ROOT.parent/"news_ema_move_checks"/"native_news_ema_move_archive.csv"
    symbols = [s for s in SYMBOLS if s in inputs] + sorted(set(inputs)-set(SYMBOLS))
    ticks = {**TICKS, **parse_assignments(args.tick, numeric=True)}
    # Euro pips retained only to reconcile the prior 6E report. Tick and percent
    # metrics are comparable without applying spot-JPY pip conventions to 6J.
    pips = {"6E": .0001, **parse_assignments(args.pip, numeric=True)}
    calendar, labels, calendar_audit = archive_events(args.calendar)
    entries, rows, audits = [], [], []
    for symbol in symbols:
        e, r, audit = read_export(symbol, inputs[symbol], ticks.get(symbol), pips.get(symbol), calendar, args.lookback_days)
        entries.extend(e)
        rows.extend(r)
        audits.append(audit)
    overall, categories, months, comparison = aggregate(rows, entries, symbols)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in (("events", entries), ("horizons", rows), ("overall", overall),
                       ("by_category", categories), ("monthly", months)):
        write_csv(args.output/f"{name}.csv", data)
    report = {"schema_version": 1, "symbols": symbols, "input_audit": audits,
              "calendar_audit": calendar_audit, "category_labels": labels,
              "semantic_checks": semantic_checks(), "comparison": comparison,
              "overall": overall,
              "method": "Entry at confirmed 15-minute candle close exactly at scheduled news time. Direction is the same candle's EMA20 versus EMA50. Freeze that side and measure only the next H actual chart bars, including the release bar. Independent observations never truncate each other.",
              "units": {"ticks": ticks, "percent": "Each observation's distance divided by its own entry price times 100, then averaged.",
                        "pips": pips, "price": "Raw futures price units. 6J uses USD per JPY; spot USDJPY pip conventions are not applied.",
                        "tick_specification_source": "https://www.cmegroup.com/markets/fx/fx-product-guide",
                        "tick_specification_note": "Standard outright minimum increments verified against official CME product specifications; no dollar values or contract quantities assumed."},
              "limitations": ["The default sample contains the same six U.S. event groups selected in News EMA Move, not each country's domestic releases.",
                              "The archive is a corrected historical schedule, not an as-announced vintage available before each event.",
                              "Back-adjusted continuous futures prices and pre-news closes are analytical benchmarks, not executable fill promises.",
                              "Excursion windows can overlap, especially FOMC decision and conference; observations are dependent.",
                              "No commissions, spreads, slippage, financing or targets/stops are modeled. MFE/MAE ratio is not profit factor.",
                              "H means chart bars rather than wall-clock minutes; exchange breaks and weekends extend elapsed time.",
                              "Full exported bars are treated as confirmed. These exports were taken after the Friday market close.",
                              "Per-instrument available histories may differ. Use common_events rows for comparisons; no unavailable event is filled in.",
                              "The same release can contain several simultaneous report components; one observation is counted per timestamp.",
                              "Statistics describe this sample and do not establish causation or future profitability."]}
    (args.output/"summary.json").write_text(json.dumps(report, indent=2)+"\n")
    write_report(args.output/"report.txt", report, categories)
    print(json.dumps({"symbols": symbols, "common_events": comparison["common_signal_timestamps"],
                      "common_complete_count_by_horizon": comparison["common_complete_count_by_horizon"],
                      "h5": [{k:r[k] for k in ("scope", "symbol", "signals", "complete", "average_mfe_ticks",
                              "average_mae_ticks", "average_close_ticks", "favorable_close_percent", "mfe_mae_ratio")}
                             for r in overall if r["horizon_bars"] == 5]}, indent=2))


if __name__ == "__main__":
    main()
