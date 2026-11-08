#!/usr/bin/env python3
"""Independent source/event/path reconstruction for saved Study 30 evidence.

Does not import the study engine or reporting calculations. The receipt covers
event vectors, episode confirmation/return ordering, all saved path outcomes,
native completed-value snapshots and selected summary cells. Bootstrap interval
re-estimation and original vendor reconstruction are outside this check.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date, datetime, time, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

STUDY = Path(__file__).resolve().parent
ROOT = STUDY.parents[1]
NY = ZoneInfo("America/New_York")
UTC = timezone.utc
SECTIONS = (("opening_range", 570, 630), ("new_york_am", 630, 750), ("new_york_pm", 750, 960))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def instant(value):
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    require(result.tzinfo is not None and result.utcoffset() is not None, "naive verification timestamp")
    return result.astimezone(UTC)


def clock(day, minute):
    return datetime.combine(date.fromisoformat(day), time(minute // 60, minute % 60), NY).astimezone(UTC)


def numeric(value):
    return value is not None and not isinstance(value, bool) and math.isfinite(float(value))


def equal(actual, expected, label):
    if expected is None:
        require(actual is None, f"{label}: expected unknown/null")
    elif isinstance(expected, bool):
        require(type(actual) is bool and actual == expected, f"{label}: boolean mismatch")
    elif isinstance(expected, (float, int)):
        require(numeric(actual) and math.isclose(float(actual), float(expected), rel_tol=1e-11, abs_tol=1e-8), f"{label}: numerical mismatch")
    else:
        require(actual == expected, f"{label}: identity mismatch")


def side(value, pivot):
    return None if not numeric(value) else (float(value) > pivot) - (float(value) < pivot)


def section(at):
    local = at.astimezone(NY)
    minute = local.hour * 60 + local.minute
    return next(name for name, start, end in SECTIONS if start <= minute < end)


def series_records(frame):
    values = frame.to_dict("records") if hasattr(frame, "to_dict") else list(frame)
    result = []
    for value in values:
        row = dict(value)
        row["open_time"], row["close_time"] = instant(row["open_time"]), instant(row["close_time"])
        result.append(row)
    result.sort(key=lambda row: row["open_time"])
    require(len({row["open_time"] for row in result}) == len(result), "duplicate native source opens")
    return result


def point(row, name, ready=None):
    if row is None or not row.get("usable", False) or (ready and not row.get(ready, False)):
        return None
    value = row.get(name)
    return float(value) if numeric(value) else None


def reconstruct_events(day, contract, pivot, minutes, bars3):
    """Independent strict-side transition vectors from native source features."""
    start, end = clock(day, 570), clock(day, 960)
    by_open = {row["open_time"]: row for row in minutes}
    by_close = {row["close_time"]: row for row in bars3}
    opening = point(by_open.get(start), "open")
    fast = point(by_close.get(start), "ema6", "ema6_ready")
    remembered = [side(opening, pivot), side(fast, pivot)]
    remembered = [value if value else None for value in remembered]
    results = {"price": [], "ema": []}
    previous = start
    for row in bars3:
        if not start <= row["open_time"] < end:
            continue
        require(row.get("contract") == contract, "event source delivery mismatch")
        if row["open_time"] != previous or not row.get("usable", False):
            remembered = [None, None]
        previous = row["close_time"]
        values = [point(row, "close"), point(row, "ema6", "ema6_ready")]
        for index, kind in enumerate(("price", "ema")):
            raw = side(values[index], pivot)
            if raw is None:
                remembered[index] = None
            elif raw:
                if remembered[index] is not None and raw != remembered[index]:
                    results[kind].append({"observed_at": row["close_time"].isoformat(), "direction": raw,
                                          "bar_open": row["open_time"].isoformat(), "section": section(row["open_time"]),
                                          "reference_price": point(row, "close")})
                remembered[index] = raw
    return results


def reconstruct_path(*, observed, reference, direction, endpoint, day_end, by_open):
    """Post-event minute opens only; exact complete horizon or explicit null."""
    elapsed = (endpoint - observed).total_seconds() / 60
    reason = "outside_rth" if endpoint > day_end else "no_followthrough_interval" if elapsed <= 0 else None
    rows = []
    cursor = observed
    while reason is None and cursor < endpoint:
        row = by_open.get(cursor)
        if row is None or not row.get("usable", False) or any(not numeric(row.get(key)) for key in ("high", "low", "close")):
            reason = "missing_or_unusable_forward_minute"
            break
        rows.append(row)
        cursor += timedelta(minutes=1)
    valid = reason is None and bool(rows)
    displacement = direction * (float(rows[-1]["close"]) - reference) if valid else None
    favorable = max([0.] + [direction * (float(row["high"] if direction > 0 else row["low"]) - reference) for row in rows]) if valid else None
    adverse = max([0.] + [-direction * (float(row["low"] if direction > 0 else row["high"]) - reference) for row in rows]) if valid else None
    result = {"valid": valid, "unknown_reason": reason, "elapsed_minutes": elapsed if elapsed > 0 else None,
              "displacement_points": displacement, "favorable_excursion_points": favorable,
              "adverse_excursion_points": adverse}
    for name, value in (("favorable", favorable), ("adverse", adverse)):
        for threshold in (5, 10, 20):
            result[f"{name}_reach_{threshold}"] = value >= threshold if value is not None else None
    return result


def _asof(rows, at, interval):
    before = [row for row in rows if row["close_time"] <= at]
    row = before[-1] if before else None
    return row if row and at - row["close_time"] < timedelta(minutes=interval) else None


def expected_context(at, price, pivot, minutes, three, five):
    """Reference-time state and exact native 15-minute endpoint changes."""
    one = next((r for r in minutes if r["close_time"] == at), None)
    fast, slow = _asof(three, at, 3), _asof(five, at, 5)
    ema6, ema20, ema50, vwap = (point(fast, "ema6", "ema6_ready"), point(slow, "ema20", "cloud_ready"),
                                point(slow, "ema50", "cloud_ready"), point(one, "vwap", "vwap_valid"))
    low, high = (min(ema20, ema50), max(ema20, ema50)) if ema20 is not None and ema50 is not None else (None, None)

    def location(value):
        return "unknown" if value is None or low is None else "above" if value > high else "below" if value < low else "inside"

    result = {"cloud_order": "unknown" if low is None else "bullish" if ema20 > ema50 else "bearish" if ema20 < ema50 else "flat",
              "price_cloud_location": location(price), "pivot_cloud_location": location(pivot),
              "vwap_side_relative_pivot": side(vwap, pivot),
              "price_side_relative_vwap": side(price, vwap) if vwap is not None else None}
    for name, value, row, rows, ready in (("ema6", ema6, fast, three, "ema6_ready"),
                                         ("ema20", ema20, slow, five, "cloud_ready"),
                                         ("ema50", ema50, slow, five, "cloud_ready"),
                                         ("vwap", vwap, one, minutes, "vwap_valid")):
        target = row["close_time"] - timedelta(minutes=15) if row else None
        earlier = next((r for r in rows if r["close_time"] == target), None)
        previous = point(earlier, name, ready)
        result[name + "_slope_15m"] = value - previous if value is not None and previous is not None else None
    target = slow["close_time"] - timedelta(minutes=15) if slow else None
    old = next((r for r in five if r["close_time"] == target), None)
    old20, old50 = point(old, "ema20", "cloud_ready"), point(old, "ema50", "cloud_ready")
    result["cloud_width_change_15m"] = abs(ema20 - ema50) - abs(old20 - old50) if low is not None and old20 is not None and old50 is not None else None
    return result


def verify_retests(events, three, pivot, end):
    lookup = {r["open_time"]: r for r in three}
    for event in events:
        observed = instant(event["observed_at"])
        requested_end = observed + timedelta(minutes=30)
        cursor, found, gap = observed, None, False
        while cursor < min(requested_end, end):
            row = lookup.get(cursor)
            if row is None or not row.get("usable", False):
                gap = True
                break
            if float(row["low"]) <= pivot <= float(row["high"]):
                found = row
                break
            cursor += timedelta(minutes=3)
        whole = requested_end <= end and all(lookup.get(observed + timedelta(minutes=n), {}).get("usable", False) for n in range(0, 30, 3))
        if found:
            close_side = side(found["close"], pivot)
            state = "equal" if close_side == 0 else "hold" if close_side == event["direction"] else "failed"
            equal(event["retest_found"], True, "first subsequent retest found")
            equal(event["retest_at"], found["close_time"].isoformat(), "first retest completion")
            equal(event["retest_close_classification"], state, "retest closing side")
            equal(event["time_to_retest_minutes"], (found["close_time"] - observed).total_seconds() / 60, "retest lag")
        else:
            equal(event["retest_found"], False if whole and not gap else None, "no retest versus censored")
            equal(event["retest_at"], None, "absent retest completion")
        equal(event["retest_window_complete"], whole, "retest observation window")
        equal(event["retest_censored"], found is None and not whole, "retest censor")


def verify_day(ledgers, *, daily, minutes, bars3, bars5):
    """Verify one eligible saved day, independent of the event producer."""
    day, contract, pivot = daily["session_date"], daily["contract"], float(daily["pivot"])
    minutes, three, five = map(series_records, (minutes, bars3, bars5))
    by_open = {row["open_time"]: row for row in minutes}
    by_close = {row["close_time"]: row for row in minutes}
    three_close = {row["close_time"]: row for row in three}
    start, end = clock(day, 570), clock(day, 960)
    context_cache = {}

    def context(at, price):
        key = (at, price)
        if key not in context_cache:
            context_cache[key] = expected_context(at, price, pivot, minutes, three, five)
        return context_cache[key]

    anchor = clock((date.fromisoformat(day) - timedelta(days=1)).isoformat(), 1080)
    cursor = anchor
    while cursor < end:
        row = by_open.get(cursor)
        require(row is not None and row.get("usable", False) and row.get("contract") == contract, "eligible anchor minute absent/invalid/wrong delivery")
        cursor += timedelta(minutes=1)
    for rows, interval, ready in ((three, 3, "ema6_ready"), (five, 5, "cloud_ready")):
        indexed = {row["open_time"]: row for row in rows}
        for offset in range(0, 390, interval):
            row = indexed.get(start + timedelta(minutes=offset))
            require(row is not None and row.get("usable", False) and row.get(ready, False)
                    and row.get("contract") == contract, "eligible native feature absent/unready/wrong delivery")
    reconstructed = reconstruct_events(day, contract, pivot, minutes, three)
    saved_events = {}
    for kind, key in (("price", "price_events"), ("ema", "ema_events")):
        saved = sorted([r for r in ledgers.get(key, []) if r["session_date"] == day], key=lambda row: row["observed_at"])
        expected = reconstructed[kind]
        equal(len(saved), len(expected), f"{kind} event count")
        per_section = Counter()
        for index, (actual, wanted) in enumerate(zip(saved, expected)):
            for field in wanted:
                equal(actual[field], wanted[field], f"{kind} {field}")
            equal(actual["contract"], contract, "event exact delivery")
            equal(actual["first_per_day"], index == 0, "first day flag")
            equal(actual["first_per_section"], per_section[wanted["section"]] == 0, "first section flag")
            per_section[wanted["section"]] += 1
            equal(actual["reference_price"], point(by_close[instant(actual["observed_at"])], "close"), "native bar/minute close parity")
            for field, value in context(instant(actual["observed_at"]), actual["reference_price"]).items():
                equal(actual[field], value, f"event reference-time {field}")
        saved_events[kind] = saved
        for suffix, value in (("", len(expected)), ("_up", sum(r["direction"] == 1 for r in expected)),
                              ("_down", sum(r["direction"] == -1 for r in expected))):
            equal(daily[f"{kind}_crosses{suffix}"], value, "daily event count")
    for row in [r for r in ledgers.get("sections", []) if r["session_date"] == day]:
        for kind in ("price", "ema"):
            group = [event for event in reconstructed[kind] if event["section"] == row["section"]]
            equal(row[f"{kind}_crosses"], len(group), "section event count")
            equal(row[f"{kind}_crosses_up"], sum(r["direction"] == 1 for r in group), "section up count")
            equal(row[f"{kind}_crosses_down"], sum(r["direction"] == -1 for r in group), "section down count")
    exposure_records = [daily, *[r for r in ledgers.get("sections", []) if r["session_date"] == day]]
    for record in exposure_records:
        label = record.get("section")
        bounds = next(((beginning, finish) for name, beginning, finish in SECTIONS if name == label), (570, 960))
        observed = [r for r in three if clock(day, bounds[0]) <= r["open_time"] < clock(day, bounds[1])]
        for kind, line, ready in (("price", "close", None), ("ema", "ema6", "ema6_ready")):
            hours = sum(point(r, line, ready) is not None for r in observed) * 3 / 60
            equal(record[kind + "_observed_hours"], hours, "independent observed exposure")
            equal(record[kind + "_crosses_per_hour"], record[kind + "_crosses"] / hours if hours else None,
                  "independent crossing exposure rate")
    confirmations = []
    verify_retests(saved_events["ema"], three, pivot, end)
    for index, event in enumerate(saved_events["price"]):
        at = instant(event["observed_at"])
        reverse = instant(saved_events["price"][index + 1]["observed_at"]) if index + 1 < len(saved_events["price"]) else None
        boundary = reverse or end
        equal(event["returned_at"], reverse.isoformat() if reverse else None, "episode return endpoint")
        equal(event["return_censored"], reverse is None, "episode return censor")
        matches = [r for r in reconstructed["ema"] if r["direction"] == event["direction"]
                   and instant(r["observed_at"]) >= at
                   and (instant(r["observed_at"]) < boundary if reverse else instant(r["observed_at"]) <= boundary)]
        confirmation = instant(matches[0]["observed_at"]) if matches else None
        equal(event["confirmation_at"], confirmation.isoformat() if confirmation else None, "actual EMA episode confirmation")
        equal(event["confirmation_kind"], ("same_close" if confirmation == at else "delayed") if confirmation else None, "confirmation kind")
        equal(event["confirmation_lag_minutes"], (confirmation - at).total_seconds() / 60 if confirmation else None, "confirmation lag")
        if confirmation:
            equal(event["confirmation_price"], point(three_close[confirmation], "close"), "confirmation source close")
            confirmations.append(event)
        path = []
        cursor = at
        while cursor < boundary:
            path.append(by_open[cursor])
            cursor += timedelta(minutes=1)
        penetration = max([0., event["direction"] * (event["reference_price"] - pivot)] +
                          [event["direction"] * (float(r["high"] if event["direction"] > 0 else r["low"]) - pivot) for r in path])
        equal(event["episode_penetration_points"], penetration, "episode penetration includes event close")
    confirmation_flags = {}
    per_section = Counter()
    for index, event in enumerate(sorted(confirmations, key=lambda row: row["confirmation_at"])):
        label = section(instant(event["confirmation_at"]) - timedelta(minutes=3))
        confirmation_flags[event["event_id"]] = (index == 0, per_section[label] == 0, label)
        per_section[label] += 1
    events = {row["event_id"]: row for rows in saved_events.values() for row in rows}
    outcomes = [row for row in ledgers.get("outcomes", []) if row["session_date"] == day]
    wanted_outcomes = {(r["event_id"], kind, horizon) for kind, rows in (("price_cross", saved_events["price"]), ("ema_cross", saved_events["ema"]), ("ema_confirmation", confirmations))
                       for r in rows for horizon in ("15m", "30m", "60m", "section_end", "day_end")}
    actual_outcomes = [(r["event_id"], r["event_type"], r["horizon"]) for r in outcomes]
    require(len(actual_outcomes) == len(set(actual_outcomes)) and set(actual_outcomes) == wanted_outcomes, "missing/duplicate outcome horizon inventory")
    for outcome in outcomes:
        event = events[outcome["event_id"]]
        confirmation = outcome["event_type"] == "ema_confirmation"
        observed = instant(event["confirmation_at"] if confirmation else event["observed_at"])
        reference = float(event["confirmation_price"] if confirmation else event["reference_price"])
        first_day, first_section, label = confirmation_flags[event["event_id"]] if confirmation else (event["first_per_day"], event["first_per_section"], event["section"])
        equal(outcome["section"], label, "outcome reference-time section")
        equal(outcome["first_per_day"], first_day, "outcome first reference-time day")
        equal(outcome["first_per_section"], first_section, "outcome first reference-time section")
        equal(outcome["reference_at"], observed.isoformat(), "outcome actual reference time")
        equal(outcome["reference_price"], reference, "outcome actual reference price")
        for field, value in context(observed, reference).items():
            equal(outcome[field], value, f"outcome reference-time {field}")
        horizon = outcome["horizon"]
        endpoint = observed + timedelta(minutes=int(horizon[:-1])) if horizon.endswith("m") else end if horizon == "day_end" else clock(day, next(finish for name, _, finish in SECTIONS if name == label))
        equal(outcome["endpoint_at"], endpoint.isoformat(), "horizon endpoint")
        expected = reconstruct_path(observed=observed, reference=reference, direction=event["direction"], endpoint=endpoint, day_end=end, by_open=by_open)
        for key, value in expected.items():
            equal(outcome[key], value, f"path {key}")
    snapshots = [row for row in ledgers.get("snapshots", []) if row["session_date"] == day]
    scheduled_labels = {"0925", "0930", "opening_range_end", "new_york_am_end", "new_york_pm_end"}
    scheduled = [row for row in snapshots if row["snapshot_label"] != "crossing"]
    require(len(scheduled) == 5 and {r["snapshot_label"] for r in scheduled} == scheduled_labels,
            "scheduled snapshot identity inventory mismatch")
    crossing = [row for row in snapshots if row["snapshot_label"] == "crossing"]
    expected_times = {row["observed_at"] for rows in reconstructed.values() for row in rows}
    actual_times = [row["snapshot_at"] for row in crossing]
    require(len(actual_times) == len(set(actual_times)) and set(actual_times) == expected_times,
            "crossing snapshot timestamp inventory mismatch")
    snapshot_ids = [row["snapshot_id"] for row in snapshots]
    require(all(isinstance(value, str) and value for value in snapshot_ids) and len(snapshot_ids) == len(set(snapshot_ids)),
            "duplicate or missing feature snapshot identity")
    snapshots_by_id = {row["snapshot_id"]: row for row in snapshots}
    for event in events.values():
        identifier = event.get("feature_snapshot_id")
        require(identifier in snapshots_by_id, "event feature snapshot link missing")
        snapshot = snapshots_by_id[identifier]
        require(snapshot["snapshot_label"] == "crossing" and snapshot["snapshot_at"] == event["observed_at"],
                "event feature snapshot link time mismatch")
        if event in saved_events["price"]:
            require("confirmation_feature_snapshot_id" in event, "confirmation feature snapshot link field missing")
            confirmation_id = event["confirmation_feature_snapshot_id"]
            if event["confirmation_at"] is None:
                equal(confirmation_id, None, "unconfirmed feature snapshot link")
            else:
                require(confirmation_id in snapshots_by_id, "confirmation feature snapshot link missing")
                confirmation_snapshot = snapshots_by_id[confirmation_id]
                require(confirmation_snapshot["snapshot_label"] == "crossing"
                        and confirmation_snapshot["snapshot_at"] == event["confirmation_at"],
                        "confirmation feature snapshot link time mismatch")
    for outcome in outcomes:
        event = events[outcome["event_id"]]
        identifier = (event["confirmation_feature_snapshot_id"] if outcome["event_type"] == "ema_confirmation"
                      else event["feature_snapshot_id"])
        equal(outcome.get("feature_snapshot_id"), identifier, "outcome reference-time feature snapshot link")
        snapshot = snapshots_by_id[identifier]
        equal(snapshot["snapshot_at"], outcome["reference_at"], "outcome linked feature information time")
        equal(snapshot["price"], outcome["reference_price"], "outcome linked reference close")
    for snapshot in snapshots:
        at = instant(snapshot["snapshot_at"])
        equal(snapshot["contract"], contract, "snapshot exact delivery")
        equal(snapshot["pivot"], pivot, "snapshot exact source pivot")
        if snapshot["snapshot_label"] == "crossing":
            equal(snapshot["snapshot_id"], f"{day}:{contract}:crossing:{at.isoformat()}", "crossing snapshot unique identity")
        one = by_close.get(at)
        fast, slow = _asof(three, at, 3), _asof(five, at, 5)
        price = point(by_open.get(at), "open") if snapshot["snapshot_label"] == "0930" else point(one, "close")
        ema6 = point(fast, "ema6", "ema6_ready")
        ema20, ema50 = point(slow, "ema20", "cloud_ready"), point(slow, "ema50", "cloud_ready")
        vwap = point(one, "vwap", "vwap_valid")
        for name, expected in (("price", price), ("ema6", point(fast, "ema6", "ema6_ready")),
                               ("ema20", point(slow, "ema20", "cloud_ready")), ("ema50", point(slow, "ema50", "cloud_ready")),
                               ("vwap", point(one, "vwap", "vwap_valid"))):
            equal(snapshot[name], expected, f"snapshot native {name}")
        low, high = (min(ema20, ema50), max(ema20, ema50)) if ema20 is not None and ema50 is not None else (None, None)
        expected_values = {"cloud_lower": low, "cloud_upper": high,
                           "cloud_spread": ema20 - ema50 if low is not None else None,
                           "cloud_width": high - low if low is not None else None,
                           "price_side_relative_pivot": side(price, pivot),
                           "ema6_side_relative_pivot": side(ema6, pivot)}
        for field, value in (("price", price), ("ema6", ema6), ("vwap", vwap), ("cloud_lower", low), ("cloud_upper", high)):
            expected_values[field + "_minus_pivot"] = value - pivot if value is not None else None
        expected_values["price_minus_vwap"] = price - vwap if price is not None and vwap is not None else None
        expected_values["price_minus_ema6"] = price - ema6 if price is not None and ema6 is not None else None
        for field, value in expected_values.items():
            equal(snapshot[field], value, f"snapshot native derived {field}")
        equal(snapshot["price_source_at"], at.isoformat() if price is not None else None, "snapshot price information time")
        for field, row in (("ema6_source_at", fast), ("cloud_source_at", slow), ("vwap_source_at", one)):
            expected = row["close_time"].isoformat() if row else None
            equal(snapshot[field], expected, "asof native completion")
            require(expected is None or instant(expected) <= at, "forming native value used")
        for field, value in context(at, price).items():
            equal(snapshot[field], value, f"snapshot reference-time {field}")
    return {"price_events": len(saved_events["price"]), "ema_events": len(saved_events["ema"]),
            "outcomes": len(outcomes), "snapshots": len(snapshots)}


def _period_contains(day, kind, period, eligible_days):
    if kind == "overall":
        return True
    if kind == "year":
        return day[:4] == period
    if kind == "calendar_month":
        return day[:7] == period
    if kind == "month_of_year":
        return day[5:7] == period
    if kind == "recent":
        return day in eligible_days[-int(period.split("_")[-1]):]
    raise ValueError("unknown saved summary period")


def _csv(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def _cell(value):
    return None if value == "" else True if value == "True" else False if value == "False" else float(value)


def verify_summaries(stage, ledgers):
    """Check selected scientific cells with independent direct sums."""
    stage = Path(stage)
    days = sorted(row["session_date"] for row in ledgers["daily"])
    checked = 0
    for row in _csv(stage / "tables/daily_summary.csv"):
        if row["metric"] not in ("price_crosses", "ema_crosses", "touch_bars",
                                  "price_crosses_per_hour", "ema_crosses_per_hour"):
            continue
        source = ledgers["daily"] if row["section"] == "all" else [r for r in ledgers["sections"] if r["section"] == row["section"]]
        picked = [r for r in source if _period_contains(r["session_date"], row["period_kind"], row["period"], days)]
        values = [float(r[row["metric"]]) for r in picked if numeric(r.get(row["metric"]))]
        expected = {"denominator": len(values), "unknown": len(picked) - len(values), "numerator": sum(values),
                    "estimate": sum(values) / len(values) if values else None,
                    "zero_count": sum(v == 0 for v in values), "zero_share": sum(v == 0 for v in values) / len(values) if values else None}
        for key, value in expected.items():
            equal(_cell(row[key]), value, f"saved recurrence {key}")
            checked += 1
    for row in _csv(stage / "tables/outcome_summary.csv"):
        if row["horizon"] != "30m" or row["direction"] != "all" or row["section"] != "all" or row["condition"] != "all":
            continue
        picked = [r for r in ledgers["outcomes"] if r["event_type"] == row["event_type"] and r["horizon"] == "30m"
                  and _period_contains(r["session_date"], row["period_kind"], row["period"], days)
                  and (row["panel"] == "all_crosses" or r.get(row["panel"]) is True)]
        valid = [r for r in picked if r["valid"] is True]
        values = [float(r["displacement_points"]) for r in valid]
        expected = {"events": len(picked), "denominator": len(valid), "unknown": len(picked) - len(valid),
                    "valid_days": len({r["session_date"] for r in valid}), "mean_points": sum(values) / len(values) if values else None,
                    "positive_count": sum(v > 0 for v in values), "negative_count": sum(v < 0 for v in values),
                    "zero_count": sum(v == 0 for v in values), "positive_rate": sum(v > 0 for v in values) / len(values) if values else None}
        for field, target in (("favorable_excursion_points", "mean_favorable_points"), ("adverse_excursion_points", "mean_adverse_points")):
            expected[target] = sum(float(r[field]) for r in valid) / len(valid) if valid else None
        for side_name in ("favorable", "adverse"):
            for threshold in (5, 10, 20):
                key = f"{side_name}_reach_{threshold}"
                count = sum(r[key] is True for r in valid)
                expected.update({key + "_count": count, key + "_denominator": len(valid), key + "_rate": count / len(valid) if valid else None})
        for key, value in expected.items():
            equal(_cell(row[key]), value, f"saved path summary {key}")
            checked += 1
    require(checked > 0, "no selected saved summary cells checked")
    return checked


def _source_quotes(root, pin, selection):
    from abacus_bhishma.verniman_consolidated import load_release
    levels = load_release(root, pin["path"], pin["sha256"], table="levels").to_pylist()
    parents = load_release(root, pin["path"], pin["sha256"], table="outlooks").to_pylist()
    grouped = defaultdict(list)
    for row in levels:
        if row.get("role") == "trigger":
            grouped[row["outlook_id"]].append(row)
    parents = {row["outlook_id"]: row for row in parents}
    for candidate in selection["candidates"]:
        parent = parents[candidate["outlook_id"]]
        day = str(parent["session_date"])
        equal(day, candidate["session_date"], "source quoted session date")
        triggers = grouped[candidate["outlook_id"]]
        require(len(triggers) == 2 and {r["side"] for r in triggers} == {"bullish", "bearish"}, "quoted paired source geometry changed")
        for trigger in triggers:
            equal(float(trigger["price_low"]), float(candidate["pivot"]), "source quoted lower price")
            equal(float(trigger["price_high"]), float(candidate["pivot"]), "source quoted upper price")
        match = re.fullmatch(r"ES([HMUZ])(\d{1,2}|\d{4})", str(parent["contract"]).strip().upper())
        require(match is not None, "source quoted maturity unsupported")
        suffix = match[2]
        years = [int(suffix)] if len(suffix) == 4 else [year for year in range(int(day[:4]) - 1, int(day[:4]) + 2) if year % (10 ** len(suffix)) == int(suffix)]
        require(len(years) == 1, "source quoted delivery year ambiguous")
        equal(candidate["contract"], f"ES{match[1]}{years[0]:04d}", "source quoted exact delivery")
    return len(selection["candidates"])


def verify(stage, write=True):
    """Verify a prepared run and optionally create one fresh scientific receipt."""
    from abacus_bhishma.es_contract_session_indicators import load_release
    stage = Path(stage).resolve()
    receipt_path = stage / "scientific-verification.json"
    require(not write or not receipt_path.exists(), "scientific receipt already exists")
    freeze = json.loads((stage / "freeze.json").read_text())
    execution = json.loads((stage / "execution.json").read_text())
    require(digest(stage / "freeze.json") == execution["freeze_sha256"], "executed freeze changed")
    for record in freeze["sources"]:
        require(digest(ROOT / record["path"]) == record["sha256"] and digest(stage / record["retained_path"]) == record["sha256"], "executed source or snapshot changed")
    own_path = str(Path(__file__).resolve().relative_to(ROOT))
    own = [record for record in freeze["sources"] if record["path"] == own_path]
    require(len(own) == 1, "independent verifier must be retained before execution")
    ledger_path = stage / "ledgers.json.gz"
    require(digest(ledger_path) == execution["ledger_sha256"], "saved ledger changed")
    with gzip.open(ledger_path, "rt") as stream:
        ledgers = json.load(stream)
    selection_path = stage / "source-selection.json"
    require(digest(selection_path) == freeze["source_selection_sha256"], "source selection changed")
    selection = json.loads(selection_path.read_text())
    root = Path(freeze["publication_root"])
    pin = freeze["inputs"]["session_indicators"]
    frames = {name: load_release(root, pin["path"], pin["sha256"], table=name) for name in ("bars1", "bars3", "bars5")}
    groups = {key: {str(day): value for day, value in frame.groupby("session_date", sort=False)} for key, frame in frames.items()}
    candidates = {row["outlook_id"]: row for row in selection["candidates"]}
    require(len({r["session_date"] for r in ledgers["daily"]}) == len(ledgers["daily"]), "duplicate eligible daily records")
    checked = Counter()
    for daily in ledgers["daily"]:
        day = daily["session_date"]
        candidate = candidates[daily["source_outlook_id"]]
        equal(daily["pivot"], candidate["pivot"], "eligible pivot source")
        equal(daily["contract"], candidate["contract"], "eligible delivery source")
        result = verify_day(ledgers, daily=daily, minutes=groups["bars1"][day], bars3=groups["bars3"][day], bars5=groups["bars5"][day])
        checked.update(result)
        checked["eligible_days"] += 1
    quotes = _source_quotes(root, freeze["inputs"]["verniman_daily_levels"], selection)
    cells = verify_summaries(stage, ledgers)
    metrics = json.loads((stage / "metrics.json").read_text())
    days = sorted(row["session_date"] for row in ledgers["daily"])
    for key, value in (("eligible_days", len(days)), ("actual_start", days[0] if days else None),
                       ("actual_end", days[-1] if days else None), ("price_events", len(ledgers["price_events"])),
                       ("ema_events", len(ledgers["ema_events"]))):
        equal(metrics[key], value, f"saved metrics {key}")
    summary_files = []
    for name, record in metrics["source_tables"].items():
        path = stage / record["artifact"]
        require(digest(path) == record["sha256"], "saved summary reference bytes changed")
        summary_files.append({"table": name, "path": record["artifact"], "sha256": record["sha256"]})
    receipt = {"status": "passed", "schema_version": "abacus.study30.scientific-verification/v1",
               "ledger_sha256": execution["ledger_sha256"], "freeze_sha256": execution["freeze_sha256"],
               "input_pins": freeze["inputs"], "verifier_source_sha256": own[0]["sha256"],
               "verifier_retained_path": own[0]["retained_path"], "checked": dict(checked),
               "source_quotes_checked": quotes, "selected_summary_cells_checked": cells,
               "summary_tables": summary_files,
               "limits": ["Bootstrap intervals are not independently re-estimated by this verifier.",
                          "Original vendor reconstruction, historical pre-open source availability and profitability remain unverified."]}
    if write:
        with receipt_path.open("x") as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    return receipt
