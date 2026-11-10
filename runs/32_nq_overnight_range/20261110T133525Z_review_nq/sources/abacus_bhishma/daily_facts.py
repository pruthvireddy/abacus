"""Daily Facts v1 session aggregation and typed output contract."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import math
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from .daily_facts_loader import DATASET_ID, VERSION, WINDOWS

NY = ZoneInfo("America/New_York")
MINUTE = timedelta(minutes=1)
MINUTE_NS = 60_000_000_000
PRICE_SCALE = 10**9
PRICE = pa.decimal128(20, 9)
TS = pa.timestamp("us", tz="UTC")
BASE = {
    "open": PRICE, "high": PRICE, "low": PRICE, "close": PRICE,
    "volume": pa.uint64(), "range_points": PRICE, "net_change_points": PRICE,
    "return_fraction": pa.float64(),
}
QUALITY_COUNTS = ("expected_minutes", "observed_rows", "unique_minutes", "missing_minutes",
                  "duplicate_rows", "off_grid_rows", "invalid_rows", "contract_mismatch_rows")
CHECKPOINTS = {
    "globex_vwap_at_rth_open": "overnight",
    "globex_vwap_at_rth_close": "globex_to_rth_end",
    "globex_vwap_at_globex_close": "globex",
    "rth_vwap": "rth",
}
DISTANCES = {
    "rth_close_minus_globex_vwap_points": ("rth", "globex_vwap_at_rth_close"),
    "rth_close_minus_rth_vwap_points": ("rth", "rth_vwap"),
    "globex_close_minus_globex_vwap_points": ("globex", "globex_vwap_at_globex_close"),
}
VOLUME_COMPARISONS = {
    "first60_volume_share": ("first60", "rth"),
    "last60_volume_share": ("last60", "rth"),
    "first60_to_last60_volume_ratio": ("first60", "last60"),
}
MINUTE_COLUMNS = ("ts_event", "session_date", "open", "high", "low", "close",
                  "volume", "instrument_id", "raw_symbol", "roll_id")


def utc_at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), NY).astimezone(timezone.utc)


def window_bounds(asset: str, day: date) -> dict[str, tuple[datetime, datetime]]:
    globex = utc_at(day - timedelta(days=1), 18)
    rth_open = utc_at(day, 8, 20) if asset == "GC" else utc_at(day, 9, 30)
    rth_close = utc_at(day, 13, 30) if asset == "GC" else utc_at(day, 16)
    return {
        "globex": (globex, utc_at(day, 17)), "overnight": (globex, rth_open),
        "rth": (rth_open, rth_close), "or15": (rth_open, rth_open + 15 * MINUTE),
        "first60": (rth_open, rth_open + 60 * MINUTE),
        "last60": (rth_close - 60 * MINUTE, rth_close),
        "globex_to_rth_end": (globex, rth_close),
    }


def previous_weekday(day: date) -> date:
    prior = day - timedelta(days=1)
    return prior - timedelta(days=2) if prior.weekday() == 6 else prior


def weekday_roster(start: date, end: date) -> list[date]:
    days = (start + timedelta(days=offset) for offset in range((end - start).days))
    return [day for day in days if day.weekday() < 5]


def _ns(value: datetime) -> int:
    return int(value.timestamp()) * 10**9


def _points(value: int) -> Decimal:
    return Decimal(value).scaleb(-9)


def minute_arrays(table: pa.Table) -> dict[str, np.ndarray]:
    if table["ts_event"].null_count or table["session_date"].null_count:
        raise ValueError("source minutes require timestamps and session dates")
    result = {"ts_event": table["ts_event"].cast(pa.int64()).to_numpy()}
    valid = np.ones(len(table), dtype=bool)
    for name in MINUTE_COLUMNS[2:]:
        column = table[name]
        if name in ("open", "high", "low", "close", "volume"):
            valid &= pc.is_valid(column).to_numpy()
        result[name] = pc.fill_null(column, "" if name == "raw_symbol" else 0).to_numpy()
    high, low = result["high"], result["low"]
    valid &= (low <= result["open"]) & (result["open"] <= high)
    valid &= (low <= result["close"]) & (result["close"] <= high)
    for name in ("open", "high", "low", "close"):
        valid &= (result[name] != np.iinfo(np.int64).max) & (result[name] != np.iinfo(np.int64).min)
    result["valid"] = valid
    return result


def _slice(arrays, left: int, right: int):
    return {name: values[left:right] for name, values in arrays.items()}


def minute_groups(table: pa.Table):
    """Yield chronological arrays per published session label."""
    if not len(table):
        return
    table = table.sort_by([("session_date", "ascending"), ("ts_event", "ascending")])
    arrays = minute_arrays(table)
    dates = table["session_date"].cast(pa.int32()).to_numpy()
    breaks = np.r_[0, np.flatnonzero(dates[1:] != dates[:-1]) + 1, len(dates)]
    epoch = date(1970, 1, 1)
    for left, right in zip(breaks[:-1], breaks[1:]):
        yield epoch + timedelta(days=int(dates[left])), _slice(arrays, left, right)


def measure_window(arrays, start, end, identity, calendar_status, *, vwap: bool = False):
    """Evaluate one independent grid and return facts, quality and optional VWAP."""
    begin, finish = _ns(start), _ns(end)
    left, right = arrays["ts_event"].searchsorted([begin, finish])
    values = _slice(arrays, left, right)
    timestamps = values["ts_event"]
    aligned = (timestamps - begin) % MINUTE_NS == 0
    unique = np.unique(timestamps)
    unique_minutes = len(np.unique(timestamps[aligned]))
    expected = (finish - begin) // MINUTE_NS
    valid = values["valid"]
    contract = ((values["instrument_id"] == identity[0])
                & (values["raw_symbol"] == identity[1]) & (values["roll_id"] == identity[2]))
    counts = dict(zip(QUALITY_COUNTS, (
        expected, len(timestamps), unique_minutes, expected - unique_minutes,
        len(timestamps) - len(unique), int((~aligned).sum()),
        int((~valid).sum()), int((~contract).sum()),
    )))
    status = calendar_status
    if status == "eligible":
        status = next((reason for name, reason in (
            ("duplicate_rows", "duplicate_minutes"), ("off_grid_rows", "off_grid_minutes"),
            ("invalid_rows", "invalid_ohlcv"), ("contract_mismatch_rows", "contract_mismatch"),
            ("missing_minutes", "missing_minutes"),
        ) if counts[name]), "complete")
    first = timestamps.searchsorted(begin, side="right")
    open_status = calendar_status
    if open_status == "eligible":
        if first != 1:
            open_status = "missing_open" if first == 0 else "duplicate_open"
        elif not valid[0]:
            open_status = "invalid_ohlcv"
        elif not contract[0]:
            open_status = "contract_mismatch"
        else:
            open_status = "ready"

    facts = dict.fromkeys(BASE)
    if open_status == "ready":
        facts["open"] = _points(int(values["open"][0]))
    vwap_value, vwap_status = None, status
    if status == "complete":
        opening, closing = int(values["open"][0]), int(values["close"][-1])
        high, low = int(values["high"].max()), int(values["low"].min())
        volume = sum(map(int, values["volume"]))
        facts.update(high=_points(high), low=_points(low), close=_points(closing),
                     volume=volume, range_points=_points(high - low),
                     net_change_points=_points(closing - opening),
                     return_fraction=(closing - opening) / opening if opening else None)
        if vwap:
            if volume:
                numerator = sum((int(h) + int(l) + int(c)) * int(v)
                                for h, l, c, v in zip(values["high"], values["low"],
                                                      values["close"], values["volume"]))
                vwap_value, vwap_status = numerator / (3 * volume * PRICE_SCALE), "ready"
            else:
                vwap_status = "zero_denominator"
    return {
        **facts, **counts, "start": start, "end": end,
        "open_available_at": start + MINUTE, "aggregate_available_at": end,
        "open_ready": open_status == "ready", "open_status": open_status,
        "aggregate_ready": status == "complete", "status": status,
        "return_status": "zero_denominator" if status == "complete" and facts["open"] == 0 else status,
    }, vwap_value, vwap_status


def context_facts(source, symbol, source_symbol, cutoff, calendar_status):
    result = {
        "vol_index_symbol": symbol, "vol_index_source_symbol": source_symbol,
        "vol_index_close_preopen": None, "vol_index_source_day": None,
        "vol_index_source_available_at": None, "vol_index_age_hours": None,
        "vol_index_available_at": cutoff, "vol_index_status": calendar_status,
    }
    if calendar_status != "eligible":
        return result
    if source is None:
        return {**result, "vol_index_status": "missing_context"}
    age = (cutoff - source["available_at"]).total_seconds() / 3600
    if age < 0:
        raise ValueError("preopen context cannot use a future observation")
    close = source["close"]
    status = "valid"
    if age > 168:
        status = "stale_context"
    elif close is None or not math.isfinite(close):
        status = "invalid_context"
    return {**result, "vol_index_close_preopen": close if status == "valid" else None,
            "vol_index_source_day": source["trading_day"],
            "vol_index_source_available_at": source["available_at"],
            "vol_index_age_hours": age, "vol_index_status": status}


def session_facts(asset, day, arrays, identity, prior_identity, roll, calendar_id,
                  calendar_status, calendar_reasons, prior_row):
    bounds = window_bounds(asset, day)
    row = {
        "release_id": DATASET_ID, "definition_version": VERSION, "asset": asset,
        "session_date": day, "series_id": "volume_lead_unadjusted_v1",
        "source_contract_id": identity[0], "source_contract_symbol": identity[1],
        "roll_id": identity[2], "is_roll_session": roll,
        "prior_session_date": previous_weekday(day), "prior_contract_id": prior_identity[0],
        "prior_contract_symbol": prior_identity[1], "calendar_id": calendar_id,
        "calendar_status": calendar_status, "calendar_reasons": calendar_reasons,
    }
    checkpoints = {}
    for window, (start, end) in bounds.items():
        facts, value, status = measure_window(
            arrays, start, end, identity, calendar_status, vwap=window in CHECKPOINTS.values(),
        )
        if window in WINDOWS:
            row.update({f"{window}_{name}": value for name, value in facts.items()})
        else:
            row["globex_to_rth_end_status"] = facts["status"]
            row["globex_to_rth_end_missing_minutes"] = facts["missing_minutes"]
        checkpoints[window] = (value, status, end)
    for name, window in CHECKPOINTS.items():
        row[name], row[name + "_status"], row[name + "_available_at"] = checkpoints[window]
    for name, (window, checkpoint) in DISTANCES.items():
        close, vwap = row[f"{window}_close"], row[checkpoint]
        row[name] = float(close) - vwap if close is not None and vwap is not None else None
        row[name + "_status"] = (
            row[checkpoint + "_status"] if close is not None else row[f"{window}_status"]
        )
        row[name + "_available_at"] = row[checkpoint + "_available_at"]
    for name, (left, right) in VOLUME_COMPARISONS.items():
        num, den = row[f"{left}_volume"], row[f"{right}_volume"]
        row[name] = num / den if num is not None and den else None
        row[name + "_status"] = (
            row[f"{left}_status"] if num is None else row[f"{right}_status"] if den is None
            else "zero_denominator" if den == 0 else "ready"
        )
        row[name + "_available_at"] = row["rth_end"]

    reference_status = calendar_status
    if reference_status == "eligible":
        if roll or identity != prior_identity:
            reference_status = "roll_reference"
        elif prior_row is None:
            reference_status = "prior_outside_pilot"
        elif prior_row["rth_close"] is None:
            reference_status = "prior_rth_unavailable"
        else:
            reference_status = "ready"
    prior_close = prior_row["rth_close"] if reference_status == "ready" else None
    opening = row["rth_open"]
    gap = opening - prior_close if opening is not None and prior_close is not None else None
    gap_status = reference_status if prior_close is None else row["rth_open_status"]
    row.update(
        prior_rth_close=prior_close, prior_rth_close_status=reference_status,
        prior_rth_close_available_at=row["globex_start"],
        rth_gap_points=gap, rth_gap_points_status=gap_status,
        rth_gap_fraction=float(gap / prior_close) if gap is not None and prior_close else None,
        rth_gap_fraction_status="zero_denominator" if gap is not None and prior_close == 0 else gap_status,
        rth_gap_available_at=row["rth_open_available_at"],
    )
    return row


def output_schema() -> pa.Schema:
    fields = [
        ("release_id", pa.string()), ("definition_version", pa.string()), ("asset", pa.string()),
        ("session_date", pa.date32()), ("series_id", pa.string()),
        ("source_contract_id", pa.uint32()), ("source_contract_symbol", pa.string()),
        ("roll_id", pa.int16()), ("is_roll_session", pa.bool_()),
        ("prior_session_date", pa.date32()), ("prior_contract_id", pa.uint32()),
        ("prior_contract_symbol", pa.string()), ("calendar_id", pa.string()),
        ("calendar_status", pa.string()),
        ("calendar_reasons", pa.list_(pa.field("element", pa.string()))),
    ]
    for window in WINDOWS:
        fields.extend((f"{window}_{name}", kind) for name, kind in BASE.items())
        fields.extend((f"{window}_{name}", pa.int16()) for name in QUALITY_COUNTS)
        fields.extend((f"{window}_{name}", TS) for name in
                      ("start", "end", "open_available_at", "aggregate_available_at"))
        fields.extend((f"{window}_{name}", pa.bool_()) for name in ("open_ready", "aggregate_ready"))
        fields.extend((f"{window}_{name}", pa.string()) for name in
                      ("status", "open_status", "return_status"))
    fields.extend((("globex_to_rth_end_status", pa.string()),
                   ("globex_to_rth_end_missing_minutes", pa.int16())))
    for name in (*CHECKPOINTS, *DISTANCES, *VOLUME_COMPARISONS):
        fields.extend(((name, pa.float64()), (name + "_status", pa.string()),
                       (name + "_available_at", TS)))
    fields.extend((
        ("prior_rth_close", PRICE), ("prior_rth_close_status", pa.string()),
        ("prior_rth_close_available_at", TS),
        ("rth_gap_points", PRICE), ("rth_gap_points_status", pa.string()),
        ("rth_gap_fraction", pa.float64()), ("rth_gap_fraction_status", pa.string()),
        ("rth_gap_available_at", TS), ("vol_index_symbol", pa.string()),
        ("vol_index_source_symbol", pa.string()), ("vol_index_close_preopen", pa.float64()),
        ("vol_index_source_day", pa.date32()), ("vol_index_source_available_at", TS),
        ("vol_index_age_hours", pa.float64()), ("vol_index_available_at", TS),
        ("vol_index_status", pa.string()),
    ))
    return pa.schema(fields, metadata={
        b"dataset_id": DATASET_ID.encode(), b"definition_version": VERSION.encode(),
        b"price_basis": b"unadjusted selected contract", b"session_timezone": b"America/New_York",
        b"availability": b"logical completed-bar timing; quality counts are retrospective",
    })
