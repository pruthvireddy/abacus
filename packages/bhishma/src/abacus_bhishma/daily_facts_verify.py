"""Independent retained-minute checks for Daily Facts v1 publication."""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
import math
from zoneinfo import ZoneInfo

import pyarrow.dataset as ds

from .daily_facts import BASE, MINUTE_COLUMNS, output_schema, previous_weekday
from .daily_facts_loader import ASSETS, DATASET_ID, VERSION, WINDOWS

NY = ZoneInfo("America/New_York")
MINUTE = timedelta(minutes=1)
NANO = 10**9
SAMPLE_DAYS = tuple(datetime.strptime(value, "%Y-%m-%d").date() for value in (
    "2021-06-28", "2021-08-02", "2021-09-13", "2021-09-15",
    "2021-11-05", "2021-11-08", "2022-07-05", "2023-05-31",
    "2025-03-10", "2026-09-18",
))


def _bounds(asset, day):
    def instant(day, hour, minute=0):
        return datetime.combine(day, time(hour, minute), NY).astimezone(timezone.utc)
    evening = instant(day - timedelta(days=1), 18)
    open_time = instant(day, 8, 20) if asset == "GC" else instant(day, 9, 30)
    close_time = instant(day, 13, 30) if asset == "GC" else instant(day, 16)
    return {
        "globex": (evening, instant(day, 17)), "overnight": (evening, open_time),
        "rth": (open_time, close_time), "or15": (open_time, open_time + 15 * MINUTE),
        "first60": (open_time, open_time + 60 * MINUTE),
        "last60": (close_time - 60 * MINUTE, close_time),
        "globex_to_rth_end": (evening, close_time),
    }


def _price(value):
    return Decimal(value) / NANO


def _reference(rows, start, end, contract, eligible):
    selected = sorted((row for row in rows if start <= row["ts_event"] < end),
                      key=lambda row: row["ts_event"])
    grid = [start + offset * MINUTE for offset in range((end - start) // MINUTE)]

    def usable(row):
        return ((row["instrument_id"], row["raw_symbol"], row["roll_id"]) == contract
                and all(row[key] is not None for key in ("open", "high", "low", "close", "volume"))
                and row["low"] <= min(row["open"], row["close"])
                and row["high"] >= max(row["open"], row["close"])
                and all(abs(row[key]) < 2**63 - 1 for key in ("open", "high", "low", "close")))

    values = dict.fromkeys(BASE)
    first = [row for row in selected if row["ts_event"] == start]
    if eligible and len(first) == 1 and usable(first[0]):
        values["open"] = _price(first[0]["open"])
    complete = (eligible and [row["ts_event"] for row in selected] == grid
                and all(usable(row) for row in selected))
    vwap = None
    if complete:
        high, low = max(row["high"] for row in selected), min(row["low"] for row in selected)
        opening, closing = first[0]["open"], selected[-1]["close"]
        volume = sum(row["volume"] for row in selected)
        values.update(high=_price(high), low=_price(low), close=_price(closing), volume=volume,
                      range_points=_price(high - low), net_change_points=_price(closing - opening),
                      return_fraction=Fraction(closing, opening) - 1 if opening else None)
        if volume:
            vwap = sum(Fraction((r["high"] + r["low"] + r["close"]) * r["volume"], 3 * NANO)
                       for r in selected) / volume
    return values, complete, vwap, len(set(grid) - {r["ts_event"] for r in selected})


def _same(actual, expected, label):
    if isinstance(expected, Fraction):
        match = actual is not None and math.isclose(actual, float(expected), rel_tol=1e-12, abs_tol=1e-9)
    else:
        match = actual == expected
    if not match:
        raise ValueError(f"{label}: expected {expected!r}, found {actual!r}")


def verify_tables(tables, datasets, days, audit_rows, schedule_identity, calendar_status, contexts,
                  *, full):
    """Check the complete release roster and independently recalculate a pinned sample."""
    coverage, samples = [], []
    for asset in ASSETS:
        table = tables[asset]
        table.validate(full=True)
        if not table.schema.equals(output_schema(), check_metadata=True):
            raise ValueError(f"{asset}: unexpected Daily Facts schema")
        rows = table.to_pylist()
        _same([r["session_date"] for r in rows], list(days), f"{asset} roster")
        eligible = [r for r in rows if r["calendar_status"] == "eligible"]
        for row in rows:
            day = row["session_date"]
            _same((row["release_id"], row["definition_version"], row["asset"]),
                  (DATASET_ID, VERSION, asset), f"{asset}/{day} identity")
            _same(row["calendar_status"], calendar_status(asset, day)[0], f"{asset}/{day} calendar")
            _same((row["source_contract_id"], row["source_contract_symbol"], row["roll_id"]),
                  schedule_identity(asset, day), f"{asset}/{day} contract")
            for window in WINDOWS:
                prefix = window + "_"
                open_ready = row[prefix + "open"] is not None
                complete = row[prefix + "status"] == "complete"
                _same(row[prefix + "open_ready"], open_ready, prefix + "open readiness")
                _same(row[prefix + "aggregate_ready"], complete, prefix + "aggregate readiness")
                for name in ("high", "low", "close", "volume", "range_points", "net_change_points"):
                    _same(row[prefix + name] is not None, complete, f"{asset}/{day} {prefix}{name} null")
                if complete:
                    opening, closing = row[prefix + "open"], row[prefix + "close"]
                    _same(row[prefix + "net_change_points"], closing - opening, prefix + "change")
                    _same(row[prefix + "range_points"], row[prefix + "high"] - row[prefix + "low"],
                          prefix + "range")
        for window in (*WINDOWS, "globex_to_rth_end"):
            completed = sum(r[window + "_status"] == "complete" for r in eligible)
            record = {"asset": asset, "window": window, "eligible": len(eligible), "complete": completed,
                      "missing_minutes": sum(r[window + "_missing_minutes"] for r in eligible)}
            coverage.append(record)
            if full:
                expected = audit_rows[(asset, window)]
                for field, audit_field in (("eligible", "candidate_sessions"),
                                           ("complete", "complete_sessions"),
                                           ("missing_minutes", "missing_minutes_total")):
                    _same(record[field], int(expected[audit_field]), f"{asset}/{window} audit {field}")
                if window in WINDOWS:
                    _same(sum(r[window + "_open_ready"] for r in eligible),
                          int(expected["open_ready_sessions"]), f"{asset}/{window} audit opening")

        for day in SAMPLE_DAYS:
            if day not in days:
                continue
            row = rows[days.index(day)]
            prior = previous_weekday(day)
            source = datasets[asset].to_table(
                columns=list(MINUTE_COLUMNS), filter=ds.field("session_date").isin([day, prior]),
            ).to_pylist()
            minute_rows = [r for r in source if r["session_date"] == day]
            identity = schedule_identity(asset, day)
            is_eligible = calendar_status(asset, day)[0] == "eligible"
            windows, vwaps = {}, {}
            for window, (start, end) in _bounds(asset, day).items():
                expected, complete, vwap, missing = _reference(minute_rows, start, end, identity, is_eligible)
                windows[window], vwaps[window] = expected, vwap
                label = f"{asset}/{day}/{window}"
                _same(row[window + "_missing_minutes"], missing, label + " missing minutes")
                _same(row[window + "_status"] == "complete", complete, label + " completeness")
                if window in WINDOWS:
                    for name, value in expected.items():
                        _same(row[f"{window}_{name}"], value, label + "/" + name)
                    _same(row[window + "_open_available_at"], start + MINUTE, label + " open timing")
                    _same(row[window + "_aggregate_available_at"], end, label + " aggregate timing")
            for name, window in (("globex_vwap_at_rth_open", "overnight"),
                                 ("globex_vwap_at_rth_close", "globex_to_rth_end"),
                                 ("globex_vwap_at_globex_close", "globex"), ("rth_vwap", "rth")):
                _same(row[name], vwaps[window], f"{asset}/{day}/{name}")
                _same(row[name + "_available_at"], _bounds(asset, day)[window][1], name + " timing")
            for name, close_window, vwap_window in (
                ("rth_close_minus_globex_vwap_points", "rth", "globex_to_rth_end"),
                ("rth_close_minus_rth_vwap_points", "rth", "rth"),
                ("globex_close_minus_globex_vwap_points", "globex", "globex"),
            ):
                close, vwap = windows[close_window]["close"], vwaps[vwap_window]
                expected = Fraction(close) - vwap if close is not None and vwap is not None else None
                _same(row[name], expected, name)
            for name, left, right in (("first60_volume_share", "first60", "rth"),
                                      ("last60_volume_share", "last60", "rth"),
                                      ("first60_to_last60_volume_ratio", "first60", "last60")):
                num, den = windows[left]["volume"], windows[right]["volume"]
                _same(row[name], Fraction(num, den) if num is not None and den else None, name)
                _same(row[name + "_available_at"], _bounds(asset, day)["rth"][1], name + " timing")

            prior_identity = schedule_identity(asset, prior)
            prior_values, *_ = _reference([r for r in source if r["session_date"] == prior],
                                          *_bounds(asset, prior)["rth"], prior_identity,
                                          calendar_status(asset, prior)[0] == "eligible")
            prior_close = prior_values["close"] if is_eligible and prior_identity == identity else None
            opening = windows["rth"]["open"]
            gap = opening - prior_close if opening is not None and prior_close is not None else None
            _same(row["prior_session_date"], prior, "prior reference date")
            _same(row["is_roll_session"], prior_identity != identity, "roll flag")
            _same(row["prior_rth_close"], prior_close, "prior close")
            _same(row["rth_gap_points"], gap, "opening gap")
            _same(row["rth_gap_fraction"], Fraction(gap) / Fraction(prior_close)
                  if gap is not None and prior_close else None, "opening gap fraction")
            _same(row["rth_gap_available_at"], _bounds(asset, day)["rth"][0] + MINUTE, "gap timing")
            cutoff = _bounds(asset, day)["rth"][0]
            selected = [r for r in contexts[asset] if r["available_at"] <= cutoff]
            latest = selected[-1] if is_eligible and selected else None
            close = (latest["close"] if latest and cutoff - latest["available_at"] <= timedelta(days=7)
                     and latest["close"] is not None and math.isfinite(latest["close"]) else None)
            _same(row["vol_index_close_preopen"], close, "preopen context close")
            _same(row["vol_index_source_available_at"], latest["available_at"] if latest else None,
                  "preopen context source timing")
            _same(row["vol_index_available_at"], cutoff, "preopen context cutoff")
            samples.append({"asset": asset, "session_date": str(day), "roll": row["is_roll_session"],
                            "globex_complete": row["globex_aggregate_ready"],
                            "rth_complete": row["rth_aggregate_ready"]})
    return {"status": "passed", "full_audit_reconciled": full, "coverage": coverage,
            "independent_source_sessions": samples, "float_relative_tolerance": 1e-12,
            "float_absolute_tolerance": 1e-9}
