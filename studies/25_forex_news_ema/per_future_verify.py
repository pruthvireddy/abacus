#!/usr/bin/env python3
"""Independently verify the frozen per-future descriptive aggregate tables.

This implementation reads retained observations directly. It does not import the
production statistics module, rebuild price paths or execute original scripts.
It verifies the new aggregation, not the original market-data reconstruction.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from zoneinfo import ZoneInfo


CONTRACTS = ("6E", "6B", "6J", "6A", "6C", "6S")
SELECTIONS = ("combined", "us_only", "local_only")
WINDOWS = (5, 10, 15, 50, 100)
TICK_SIZE = {"6E": .00005, "6B": .0001, "6J": .0000005,
             "6A": .00005, "6C": .00005, "6S": .00005}
PERIOD_ZONE = ZoneInfo("America/Chicago")
NEW_YORK = ZoneInfo("America/New_York")
DIMENSIONS = {
    "overall": (), "by_type": ("news_type",),
    "monthly": ("month_chicago",), "weekly": ("week_chicago",),
    "type_month": ("news_type", "month_chicago"),
    "type_week": ("news_type", "week_chicago"),
    "by_side": ("side",), "type_side": ("news_type", "side"),
    "weekday": ("weekday_chicago",), "hour": ("hour_chicago",),
    "year": ("year",), "quarter": ("quarter",),
}
BASE_KEY = ("symbol", "mode", "horizon_bars")
DISTANCES = tuple(f"{measure}_{unit}" for measure in ("mfe", "mae", "close")
                  for unit in ("price", "ticks", "percent"))
START = datetime(2025, 10, 17, tzinfo=NEW_YORK).timestamp()
END = datetime(2026, 10, 17, tzinfo=NEW_YORK).timestamp()


class VerificationError(ValueError):
    pass


def require(condition, detail):
    if not condition:
        raise VerificationError(detail)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        names = reader.fieldnames
        require(names and len(set(names)) == len(names), f"{path}: missing/duplicate header")
        result = list(reader)
    require(all(None not in row and all(value is not None for value in row.values())
                for row in result), f"{path}: malformed CSV row")
    return result, tuple(names)


def integer(value, context):
    try:
        result = int(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise VerificationError(f"{context}: invalid integer {value!r}") from exc
    require(str(result) == str(value), f"{context}: noncanonical integer {value!r}")
    return result


def finite(value, context, nullable=False):
    if value == "" or value is None:
        require(nullable, f"{context}: unexpected null")
        return None
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise VerificationError(f"{context}: invalid number {value!r}") from exc
    require(math.isfinite(result), f"{context}: nonfinite number")
    return result


def timestamp(text, context):
    try:
        result = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError) as exc:
        raise VerificationError(f"{context}: invalid timestamp") from exc
    require(result.tzinfo is not None, f"{context}: timestamp lacks timezone")
    return result


def close_enough(actual, expected, context):
    require(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10),
            f"{context}: {actual!r} differs from {expected!r}")


def parse_observations(source):
    original, columns = csv_rows(source / "study/horizons.csv")
    events, event_columns = csv_rows(source / "study/events.csv")
    require(original and events, "source ledgers are empty")
    require(set(event_columns) <= set(columns), "event columns absent from horizon ledger")
    indexed_events = {}
    for line, event in enumerate(events, 2):
        identity = (event["symbol"], event["mode"], integer(event["event_epoch"], "event epoch"))
        require(identity not in indexed_events, f"events.csv:{line}: repeated event {identity}")
        indexed_events[identity] = event
    observations, identities = [], set()
    event_windows = defaultdict(set)
    type_names = {}
    for line, raw in enumerate(original, 2):
        context = f"horizons.csv:{line}"
        row = dict(raw)
        for field in ("event_epoch", "direction", "type_code", "component_count", "horizon_bars", "complete", "has_us", "has_local"):
            row[field] = integer(raw[field], f"{context} {field}")
        require(row["symbol"] in CONTRACTS and row["mode"] in SELECTIONS, f"{context}: unexpected contract/mode")
        require(row["horizon_bars"] in WINDOWS, f"{context}: unexpected horizon")
        require(all(row[field] in (0, 1) for field in ("complete", "has_us", "has_local")), f"{context}: invalid flag")
        event_id = (row["symbol"], row["mode"], row["event_epoch"])
        identity = (*event_id, row["horizon_bars"])
        require(identity not in identities, f"{context}: repeated outcome {identity}")
        identities.add(identity)
        require(event_id in indexed_events, f"{context}: absent event ledger identity")
        require(all(raw[field] == indexed_events[event_id][field] for field in event_columns),
                f"{context}: event metadata disagrees with events.csv")
        event_windows[event_id].add(row["horizon_bars"])
        epoch = row["event_epoch"]
        require(START <= epoch < END and epoch % 900 == 0, f"{context}: release outside interval or off grid")
        for field, zone in (("event_utc", timezone.utc), ("event_ny", NEW_YORK)):
            parsed = timestamp(raw[field], context)
            require(parsed.timestamp() == epoch and parsed.utcoffset() == datetime.fromtimestamp(epoch, zone).utcoffset(),
                    f"{context}: {field} offset/epoch mismatch")
        require(timestamp(raw["entry_bar_open_utc"], context).timestamp() == epoch - 900,
                f"{context}: entry candle does not end at release")
        row["entry_price"] = finite(raw["entry_price"], context)
        fast = finite(raw["fast_ema20"], context)
        slow = finite(raw["slow_ema50"], context)
        require(row["entry_price"] > 0 and fast != slow, f"{context}: invalid entry/flat cloud")
        require(row["direction"] == (1 if fast > slow else -1), f"{context}: EMA direction mismatch")
        require(row["side"] == ("Long" if row["direction"] == 1 else "Short"), f"{context}: side mismatch")
        codes = [integer(value, context) for value in raw["component_category_codes"].split(";")]
        require(codes and codes == sorted(set(codes)) and all(0 <= code <= 12 for code in codes),
                f"{context}: invalid category codes")
        require(row["component_count"] >= len(codes), f"{context}: too few components")
        require(row["type_code"] == (13 if len(codes) > 1 else codes[0]), f"{context}: Mixed attribution mismatch")
        require(bool(row["has_us"]) == any(code < 6 for code in codes) and
                bool(row["has_local"]) == any(code >= 6 for code in codes), f"{context}: regional flags mismatch")
        require(row["mode"] != "us_only" or not row["has_local"], f"{context}: local component in USD mode")
        require(row["mode"] != "local_only" or not row["has_us"], f"{context}: USD component in local mode")
        require(raw["news_type"].strip() and raw["event_titles"].strip(), f"{context}: missing source label/title")
        require((row["type_code"] == 13) == (row["news_type"] == "Mixed types (same timestamp)"),
                f"{context}: incorrect exclusive Mixed label")
        label_key = (row["symbol"], row["type_code"])
        require(type_names.setdefault(label_key, row["news_type"]) == row["news_type"], f"{context}: type label changed")
        for field in (*DISTANCES, "elapsed_calendar_minutes"):
            row[field] = finite(raw[field], f"{context} {field}", nullable=not row["complete"])
        if row["complete"]:
            require(all(row[f"{measure}_{unit}"] >= 0 for measure in ("mfe", "mae")
                        for unit in ("price", "ticks", "percent")), f"{context}: negative excursion")
            require(row["elapsed_calendar_minutes"] >= 15 * row["horizon_bars"], f"{context}: horizon shorter than bars")
            exit_time = timestamp(raw["exit_close_utc"], context).timestamp()
            close_enough((exit_time - epoch) / 60, row["elapsed_calendar_minutes"], f"{context} elapsed")
            for measure in ("mfe", "mae", "close"):
                close_enough(row[f"{measure}_price"] / TICK_SIZE[row["symbol"]], row[f"{measure}_ticks"], f"{context} tick conversion")
                close_enough(row[f"{measure}_price"] * 100 / row["entry_price"], row[f"{measure}_percent"], f"{context} percent conversion")
        else:
            require(not raw["exit_close_utc"] and all(row[field] is None for field in (*DISTANCES, "elapsed_calendar_minutes")),
                    f"{context}: pending row contains outcomes")
        chicago = datetime.fromtimestamp(epoch, PERIOD_ZONE)
        require(row["month_chicago"] == chicago.strftime("%Y-%m"), f"{context}: source month mismatch")
        iso = chicago.isocalendar()
        row.update(week_chicago=f"{iso.year:04d}-W{iso.week:02d}",
                   week_start_chicago=(chicago.date() - timedelta(days=chicago.weekday())).isoformat(),
                   weekday_chicago=f"{chicago.isoweekday()} {('Mon','Tue','Wed','Thu','Fri','Sat','Sun')[chicago.weekday()]}",
                   hour_chicago=f"{chicago.hour:02d}:00", year=chicago.year,
                   quarter=f"{chicago.year:04d}-Q{1 + (chicago.month - 1) // 3}")
        observations.append(row)
    require(set(indexed_events) == set(event_windows), "event-horizon ledger event coverage differs")
    require(all(windows == set(WINDOWS) for windows in event_windows.values()), "event lacks its five distinct horizons")
    require({(row["symbol"], row["mode"]) for row in observations} ==
            {(symbol, mode) for symbol in CONTRACTS for mode in SELECTIONS}, "missing contract/mode selection")
    return observations, len(events)


def midpoint(ordered):
    n = len(ordered)
    return (ordered[(n - 1) // 2] + ordered[n // 2]) / 2 if n else None


def distribution(ordered, probability):
    if not ordered:
        return None
    location = probability * (len(ordered) - 1)
    low = int(location)
    fraction = location - low
    return ordered[low] if not fraction else ordered[low] + fraction * (ordered[low + 1] - ordered[low])


def derive_statistics(members):
    completed = [member for member in members if member["complete"] == 1]
    count = len(completed)
    result = {"signals": len(members), "completed": count, "pending": len(members) - count,
              "long_signals": sum(member["direction"] > 0 for member in members),
              "short_signals": sum(member["direction"] < 0 for member in members),
              "sample_support": "n<10" if count < 10 else "n>=10"}
    for field in DISTANCES:
        ordered = sorted(member[field] for member in completed)
        result[f"average_{field}"] = math.fsum(ordered) / count if count else None
        result[f"median_{field}"] = midpoint(ordered)
        if field.endswith("_ticks"):
            for probability in (.1, .25, .75, .9):
                result[f"p{round(probability * 100)}_{field}"] = distribution(ordered, probability)
    close = [member["close_price"] for member in completed]
    counts = {"favorable": sum(value > 0 for value in close),
              "adverse": sum(value < 0 for value in close), "flat": sum(value == 0 for value in close)}
    for label, value in counts.items():
        result[f"{label}_close_count"] = value
        result[f"{label}_close_percent"] = value / count * 100 if count else None
    above = sum(member["mfe_price"] - member["mae_price"] >
                1e-10 * max(1, member["mfe_price"], member["mae_price"]) for member in completed)
    result.update(mfe_above_mae_count=above, mfe_above_mae_percent=above / count * 100 if count else None)
    mae = result["average_mae_price"]
    result["mfe_mae_ratio"] = result["average_mfe_price"] / mae if mae else None
    ticks = [member["close_ticks"] for member in completed]
    minutes = sorted(member["elapsed_calendar_minutes"] for member in completed)
    result.update(min_close_ticks=min(ticks) if ticks else None, max_close_ticks=max(ticks) if ticks else None,
                  average_elapsed_minutes=math.fsum(minutes) / count if count else None,
                  median_elapsed_minutes=midpoint(minutes), max_elapsed_minutes=max(minutes) if minutes else None)
    return result


def summarize_family(observations, dimensions):
    key_fields = (*BASE_KEY, *dimensions)
    members = defaultdict(list)
    for observation in observations:
        members[tuple(observation[field] for field in key_fields)].append(observation)
    result = {}
    for key, selected in members.items():
        labels = dict(zip(key_fields, key))
        if "news_type" in dimensions:
            require(len({row["type_code"] for row in selected}) == 1, "one type label combines multiple type codes")
            labels["type_code"] = selected[0]["type_code"]
        if "week_chicago" in dimensions:
            require(len({row["week_start_chicago"] for row in selected}) == 1, "ISO week combines different Mondays")
            labels["week_start_chicago"] = selected[0]["week_start_chicago"]
        result[key] = {**labels, **derive_statistics(selected)}
    return result


def compare_table(path, expected, dimensions, counters, *, original=False):
    rows, fields = csv_rows(path)
    key_fields = (*BASE_KEY, *dimensions)
    seen = set()
    for line, actual in enumerate(rows, 2):
        typed = dict(actual)
        for name in ("horizon_bars", "year"):
            if name in typed:
                typed[name] = integer(typed[name], f"{path}:{line} {name}")
        key = tuple(typed[field] for field in key_fields)
        require(key not in seen, f"{path}:{line}: duplicate group {key}")
        seen.add(key)
        require(key in expected, f"{path}:{line}: unexpected group {key}")
        target = expected[key]
        require(set(fields) <= set(target) if original else set(fields) == set(target),
                f"{path}: unexpected/missing columns {set(fields) ^ set(target)}")
        for field in fields:
            wanted = target[field]
            value = actual[field]
            context = f"{path}:{line} {field}"
            if wanted is None:
                require(value == "", f"{context}: null was changed to {value!r}")
                counters["null_cells"] += 1
            elif isinstance(wanted, str):
                require(value == wanted, f"{context}: wrong label {value!r}; expected {wanted!r}")
                counters["label_cells"] += 1
            elif isinstance(wanted, int):
                require(integer(value, context) == wanted, f"{context}: wrong integer {value!r}; expected {wanted}")
                counters["integer_cells"] += 1
            else:
                close_enough(finite(value, context), wanted, context)
                counters["numeric_cells"] += 1
        counters["rows"] += 1
    require(seen == set(expected), f"{path}: group coverage differs; {len(set(expected)-seen)} missing groups")
    return len(rows)


def verify_partitions(expected):
    overall = expected["overall"]
    by_type = expected["by_type"]
    for base, total in overall.items():
        pieces = [row for key, row in by_type.items() if key[:3] == base]
        for count in ("signals", "completed", "pending", "long_signals", "short_signals",
                      "favorable_close_count", "adverse_close_count", "flat_close_count", "mfe_above_mae_count"):
            require(sum(piece[count] for piece in pieces) == total[count], f"{base}: type partition fails for {count}")
        require(total["favorable_close_count"] + total["adverse_close_count"] + total["flat_close_count"] == total["completed"],
                f"{base}: completed close denominators differ")


def validate_exclusions(source, observations):
    rows, _ = csv_rows(source / "study/exclusions.csv")
    accepted = {(row["symbol"], row["mode"], row["event_epoch"]) for row in observations}
    identities = set()
    for line, row in enumerate(rows, 2):
        epoch = integer(row["event_epoch"], "excluded epoch")
        identity = (row["symbol"], row["mode"], epoch, integer(row["category_code"], "excluded category"))
        require(identity not in identities, f"exclusions.csv:{line}: duplicate category/timestamp")
        identities.add(identity)
        require(identity[:3] not in accepted, f"exclusions.csv:{line}: excluded timestamp also accepted")
        require(row["symbol"] in CONTRACTS and row["mode"] in SELECTIONS and START <= epoch < END,
                f"exclusions.csv:{line}: invalid identity or interval")
        require(timestamp(row["event_utc"], "excluded timestamp").timestamp() == epoch, "exclusion timestamp differs")
        require(row["reason"] in ("off_15m_grid", "unknown_or_tentative_release_time", "entry_bar_unavailable"),
                f"exclusions.csv:{line}: unexpected reason")
        require(integer(row["component_count"], "excluded components") > 0 and row["titles"].strip(), "invalid exclusion components")
        require(row["reason"] != "off_15m_grid" or epoch % 900 != 0, "off-grid exclusion is on grid")
    return len(rows)


def verify_stage(stage):
    source = stage / "source-original/per_future_news"
    config = json.loads((stage / "config.json").read_text())
    require(config["protocol"] == "per-future-descriptive-2" and config["period_timezone"] == "America/Chicago", "wrong frozen protocol/timezone")
    require(tuple(config["symbols"]) == CONTRACTS and tuple(config["modes"]) == SELECTIONS and tuple(config["horizons"]) == WINDOWS,
            "wrong frozen contracts/modes/horizons")
    lock = json.loads((stage / "inputs.lock.json").read_text())
    source_hashes = {}
    for declared in lock["files"]:
        path = source / declared["path"]
        require(path.is_file() and path.stat().st_size == declared["bytes"], f"{path}: input size mismatch")
        observed = sha256(path)
        require(observed == declared["sha256"], f"{path}: input SHA256 mismatch")
        source_hashes[declared["path"]] = observed
    required_inputs = {f"study/{name}" for name in ("horizons.csv", "events.csv", "overall.csv", "by_type.csv", "monthly.csv", "exclusions.csv")}
    require(required_inputs <= set(source_hashes), "lock lacks required observed/aggregate/exclusion inputs")
    observations, event_count = parse_observations(source)
    expected = {family: summarize_family(observations, dimensions) for family, dimensions in DIMENSIONS.items()}
    verify_partitions(expected)
    exclusion_count = validate_exclusions(source, observations)
    new_counts, old_counts = Counter(), Counter()
    output_hashes, family_counts = {}, {}
    for contract in CONTRACTS:
        for family, dimensions in DIMENSIONS.items():
            path = stage / "tables" / f"{contract}-{family}.csv"
            selected = {key: value for key, value in expected[family].items() if key[0] == contract}
            count = compare_table(path, selected, dimensions, new_counts)
            family_counts[f"{contract}-{family}"] = count
            output_hashes[path.relative_to(stage).as_posix()] = sha256(path)
    for filename, family in (("overall.csv", "overall"), ("by_type.csv", "by_type"), ("monthly.csv", "monthly")):
        compare_table(source / "study" / filename, expected[family], DIMENSIONS[family], old_counts, original=True)
    counts = Counter((row["symbol"], row["mode"]) for row in observations if row["horizon_bars"] == 5)
    return {
        "status": "passed", "protocol": config["protocol"],
        "scope": "Independent numerical verification of descriptive aggregation from retained observations; does not re-execute original price/EMA/calendar/outcome reconstruction or TradingView validation.",
        "tolerance": {"relative": 1e-10, "absolute": 1e-10},
        "source_observation_rows": len(observations), "source_event_rows": event_count,
        "source_exclusion_rows": exclusion_count, "table_files_verified": len(output_hashes),
        "new_tables": dict(new_counts), "original_summary_parity": dict(old_counts),
        "family_row_counts": family_counts,
        "events_by_contract_and_mode": {symbol: {mode: counts[symbol, mode] for mode in SELECTIONS} for symbol in CONTRACTS},
        "source_hashes": source_hashes, "output_hashes": output_hashes,
        "frozen_protocol_sha256": sha256(stage / "protocol.md"),
        "frozen_config_sha256": sha256(stage / "config.json"),
        "frozen_input_lock_sha256": sha256(stage / "inputs.lock.json"),
        "independent_checker_sha256": sha256(__file__),
        "independent_checker": str(Path(__file__).resolve()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    args = parser.parse_args(argv)
    stage = args.stage.resolve()
    require(stage.is_dir() and stage.parent.name == "25_forex_news_ema" and stage.parent.parent.name == "work",
            "target must be an explicit study-25 staging directory under work/")
    try:
        report = verify_stage(stage)
    except (VerificationError, OSError, KeyError, ValueError) as exc:
        report = {"status": "failed", "error": str(exc), "independent_checker_sha256": sha256(__file__)}
    report["verified_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["command"] = [sys.executable, str(Path(__file__).resolve()), str(stage)]
    (stage / "scientific-verification.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "table_files_verified", "source_observation_rows", "error") if key in report}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
