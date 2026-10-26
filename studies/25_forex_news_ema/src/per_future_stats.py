"""Descriptive summaries of the saved per-contract News EMA Move ledger.

No prices, EMA directions, news classifications or event outcomes are rebuilt.
Every observation is one symbol/mode/event/horizon row. Modes are overlapping
alternative selections and are never pooled; simultaneous categories remain in
the exclusive source ``Mixed types (same timestamp)`` bucket (type code 13).

Outcome denominators include complete observations only. Rates and the source
``*_percent`` distances use percentage points (0..100 for rates), not fractions.
Means use ``math.fsum(values) / n`` and medians use ``statistics.median``.
Tick quantiles use linear interpolation at sorted index ``(n - 1) * p``; a
one-observation quantile equals that observation. No confidence intervals are
estimated. MFE > MAE retains the source's absolute price tolerance:
``mfe_price - mae_price > 1e-10 * max(1, mfe_price, mae_price)``.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo


SYMBOLS = ("6E", "6B", "6J", "6A", "6C", "6S")
MODES = ("combined", "us_only", "local_only")
HORIZONS = (5, 10, 15, 50, 100)
BASE_GROUP_COLUMNS = ("symbol", "mode", "horizon_bars")
CHICAGO = ZoneInfo("America/Chicago")
MEASURES = ("mfe", "mae", "close")
UNITS = ("price", "ticks", "percent")
OUTCOME_COLUMNS = tuple(f"{measure}_{unit}" for unit in UNITS for measure in MEASURES)
INTEGER_COLUMNS = ("event_epoch", "direction", "type_code", "component_count", "horizon_bars")
BOOLEAN_COLUMNS = ("complete", "has_us", "has_local")
REQUIRED_COLUMNS = (
    "symbol", "mode", "event_utc", "event_ny", "month_chicago", "entry_price",
    "side", "news_type", "component_category_codes", "event_titles",
    *INTEGER_COLUMNS, *BOOLEAN_COLUMNS, "elapsed_calendar_minutes", *OUTCOME_COLUMNS,
)
GROUP_DIMENSIONS = frozenset((
    *BASE_GROUP_COLUMNS, "news_type", "type_code", "month_chicago",
    "week_chicago", "week_start_chicago", "weekday_chicago", "hour_chicago",
    "year", "quarter", "side", "has_us", "has_local",
))
TABLE_DIMENSIONS = {
    "overall": (),
    "by_type": ("news_type",),
    "monthly": ("month_chicago",),
    "weekly": ("week_chicago",),
    "type_month": ("news_type", "month_chicago"),
    "type_week": ("news_type", "week_chicago"),
    "by_side": ("side",),
    "type_side": ("news_type", "side"),
    "weekday": ("weekday_chicago",),
    "hour": ("hour_chicago",),
    "year": ("year",),
    "quarter": ("quarter",),
}


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer, not a boolean")
    try:
        converted = int(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if isinstance(value, str):
        if str(converted) != value.strip():
            raise ValueError(f"{name} must be a canonical integer")
    elif converted != value:
        raise ValueError(f"{name} must be an integer")
    return converted


def _boolean(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    converted = _integer(value, name)
    if converted not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1")
    return bool(converted)


def _number(value: Any, name: str, *, nullable: bool = False) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        if nullable:
            return None
        raise ValueError(f"{name} must not be null")
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number, not a boolean")
    try:
        converted = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be a finite number")
    return converted


def enrich(row: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a row and add periods from its event epoch in America/Chicago.

    ``week_chicago`` uses the ISO week-year (which may differ from calendar
    year); ``week_start_chicago`` is its Monday date. ``year`` is a calendar
    integer and ``quarter`` is YYYY-QN. Validate the saved month against the
    event's Chicago date, including events near UTC and year boundaries.
    """
    result = dict(row)
    epoch = _integer(row.get("event_epoch"), "event_epoch")
    try:
        local = datetime.fromtimestamp(epoch, CHICAGO)
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError("event_epoch is outside the supported datetime range") from exc
    month = local.strftime("%Y-%m")
    if row.get("month_chicago") != month:
        raise ValueError(f"month_chicago differs from event time: expected {month}")
    iso_year, iso_week, _ = local.isocalendar()
    monday = local.date() - timedelta(days=local.weekday())
    result.update({
        "week_chicago": f"{iso_year:04d}-W{iso_week:02d}",
        "week_start_chicago": monday.isoformat(),
        "weekday_chicago": f"{local.isoweekday()} {('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')[local.weekday()]}",
        "hour_chicago": f"{local.hour:02d}:00",
        "year": local.year,
        "quarter": f"{local.year:04d}-Q{(local.month - 1) // 3 + 1}",
    })
    return result


def _typed_row(row: Mapping[str, Any]) -> dict[str, Any]:
    missing = set(REQUIRED_COLUMNS) - row.keys()
    if missing:
        raise ValueError(f"missing columns: {', '.join(sorted(missing))}")
    result = dict(row)
    for name in INTEGER_COLUMNS:
        result[name] = _integer(row[name], name)
    for name in BOOLEAN_COLUMNS:
        result[name] = _boolean(row[name], name)
    result["entry_price"] = _number(row["entry_price"], "entry_price")
    for name in (*OUTCOME_COLUMNS, "elapsed_calendar_minutes"):
        result[name] = _number(row[name], name, nullable=True)
    if result["symbol"] not in SYMBOLS or result["mode"] not in MODES:
        raise ValueError("unrecognized symbol or mode")
    if result["horizon_bars"] not in HORIZONS:
        raise ValueError("unrecognized horizon_bars")
    if result["direction"] not in (-1, 1):
        raise ValueError("direction must be -1 or 1")
    if result["side"] != ("Long" if result["direction"] == 1 else "Short"):
        raise ValueError("side does not match direction")
    if result["entry_price"] <= 0:
        raise ValueError("entry_price must be positive")
    for name in ("news_type", "event_titles"):
        if not isinstance(result[name], str) or not result[name].strip():
            raise ValueError(f"{name} must be nonempty text")
    for name in ("event_utc", "event_ny"):
        try:
            parsed = datetime.fromisoformat(str(result[name]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{name} must be an offset-aware ISO timestamp") from exc
        if parsed.tzinfo is None or parsed.timestamp() != result["event_epoch"]:
            raise ValueError(f"{name} differs from event_epoch or lacks an offset")
    try:
        codes = tuple(_integer(part, "component_category_codes") for part in str(result["component_category_codes"]).split(";"))
    except ValueError as exc:
        raise ValueError("invalid component_category_codes") from exc
    if len(set(codes)) != len(codes) or any(code not in range(0, 13) for code in codes):
        raise ValueError("component_category_codes must contain unique codes 0..12")
    if result["component_count"] < len(codes):
        raise ValueError("component_count is smaller than distinct component codes")
    expected_code = 13 if len(codes) > 1 else codes[0]
    if result["type_code"] != expected_code:
        raise ValueError("type_code must preserve the exclusive Mixed category")
    if result["has_us"] != any(code <= 5 for code in codes) or result["has_local"] != any(code > 5 for code in codes):
        raise ValueError("has_us/has_local differs from selected component codes")
    if result["mode"] == "us_only" and result["has_local"]:
        raise ValueError("us_only contains a local component")
    if result["mode"] == "local_only" and result["has_us"]:
        raise ValueError("local_only contains a U.S. component")
    outcome_values = [result[name] for name in (*OUTCOME_COLUMNS, "elapsed_calendar_minutes")]
    if result["complete"]:
        if any(value is None for value in outcome_values):
            raise ValueError("complete observation has null outcomes or elapsed time")
        if result["elapsed_calendar_minutes"] < result["horizon_bars"] * 15:
            raise ValueError("elapsed time is shorter than its actual 15-minute candles")
        for unit in UNITS:
            if result[f"mfe_{unit}"] < 0 or result[f"mae_{unit}"] < 0:
                raise ValueError("MFE and MAE must be nonnegative")
        # A sign disagreement would change the favorable-close denominator
        # depending on the selected display unit.
        if len({(result[f"close_{unit}"] > 0) - (result[f"close_{unit}"] < 0) for unit in UNITS}) != 1:
            raise ValueError("close sign differs between source units")
    elif any(value is not None for value in outcome_values):
        raise ValueError("pending observation must have null outcomes and elapsed time")
    return enrich(result)


def _prepare_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    prepared = []
    seen: set[tuple[Any, ...]] = set()
    labels: dict[tuple[str, int], str] = {}
    event_metadata: dict[tuple[str, str, int], tuple[Any, ...]] = {}
    stable_columns = ("entry_price", "direction", "side", "type_code", "news_type", "component_category_codes", "component_count", "has_us", "has_local", "event_titles")
    for index, row in enumerate(rows, start=2):
        try:
            typed = _typed_row(row)
            key = tuple(typed[name] for name in ("symbol", "mode", "event_epoch", "horizon_bars"))
            if key in seen:
                raise ValueError(f"duplicate observation key {key!r}")
            seen.add(key)
            label_key = (typed["symbol"], typed["type_code"])
            if labels.setdefault(label_key, typed["news_type"]) != typed["news_type"]:
                raise ValueError("news_type label changes within one symbol/type_code")
            event_key = key[:3]
            metadata = tuple(typed[name] for name in stable_columns)
            if event_metadata.setdefault(event_key, metadata) != metadata:
                raise ValueError("event metadata differs across horizons")
            prepared.append(typed)
        except ValueError as exc:
            raise ValueError(f"ledger row {index}: {exc}") from exc
    return prepared


def load_ledger(path: str | Path) -> list[dict[str, Any]]:
    """Read an explicit horizon CSV, validate it, and return typed enriched rows.

    Source integer fields become ``int``; complete/has flags become ``bool``;
    outcomes and entry prices become finite ``float`` or (pending only) None.
    Extra source columns are retained unchanged. Duplicate event/horizon keys,
    contradictory labels, invalid periods and incomplete outcome tuples fail.
    """
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("ledger header is absent or contains duplicate columns")
        if set(REQUIRED_COLUMNS) - set(reader.fieldnames):
            raise ValueError(f"ledger missing columns: {', '.join(sorted(set(REQUIRED_COLUMNS) - set(reader.fieldnames)))}")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("ledger row has a different number of fields than its header")
    return _prepare_rows(rows)


def _quantile(ordered: list[float], probability: float) -> float | None:
    if not ordered:
        return None
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in rows if row["complete"]]
    n = len(completed)
    result: dict[str, Any] = {
        "signals": len(rows), "completed": n, "pending": len(rows) - n,
        "long_signals": sum(row["direction"] == 1 for row in rows),
        "short_signals": sum(row["direction"] == -1 for row in rows),
        "sample_support": "n<10" if n < 10 else "n>=10",
    }
    for unit in UNITS:
        for measure in MEASURES:
            values = [row[f"{measure}_{unit}"] for row in completed]
            result[f"average_{measure}_{unit}"] = math.fsum(values) / n if n else None
            result[f"median_{measure}_{unit}"] = median(values) if n else None
    for measure in MEASURES:
        ordered = sorted(row[f"{measure}_ticks"] for row in completed)
        for label, probability in (("p10", .1), ("p25", .25), ("p75", .75), ("p90", .9)):
            result[f"{label}_{measure}_ticks"] = _quantile(ordered, probability)
    for label, predicate in (
        ("favorable", lambda value: value > 0),
        ("adverse", lambda value: value < 0),
        ("flat", lambda value: value == 0),
    ):
        count = sum(predicate(row["close_price"]) for row in completed)
        result[f"{label}_close_count"] = count
        result[f"{label}_close_percent"] = 100 * count / n if n else None
    above = sum(row["mfe_price"] - row["mae_price"] > 1e-10 * max(1.0, row["mfe_price"], row["mae_price"]) for row in completed)
    result["mfe_above_mae_count"] = above
    result["mfe_above_mae_percent"] = 100 * above / n if n else None
    denominator = result["average_mae_price"]
    result["mfe_mae_ratio"] = result["average_mfe_price"] / denominator if denominator else None
    close_values = [row["close_ticks"] for row in completed]
    elapsed = [row["elapsed_calendar_minutes"] for row in completed]
    result["min_close_ticks"] = min(close_values) if n else None
    result["max_close_ticks"] = max(close_values) if n else None
    result["average_elapsed_minutes"] = math.fsum(elapsed) / n if n else None
    result["median_elapsed_minutes"] = median(elapsed) if n else None
    result["max_elapsed_minutes"] = max(elapsed) if n else None
    return result


def _group_columns(group_columns: Iterable[str]) -> tuple[str, ...]:
    columns = tuple(group_columns)
    if len(columns) != len(set(columns)):
        raise ValueError("group_columns contains duplicates")
    unsupported = set(columns) - GROUP_DIMENSIONS
    if unsupported:
        raise ValueError(f"unsupported group columns: {', '.join(sorted(unsupported))}")
    return (*BASE_GROUP_COLUMNS, *(column for column in columns if column not in BASE_GROUP_COLUMNS))


def _aggregate(rows: list[dict[str, Any]], group_columns: Iterable[str]) -> list[dict[str, Any]]:
    columns = _group_columns(group_columns)
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[column] for column in columns)].append(row)
    def sort_key(key: tuple[Any, ...]) -> tuple[Any, ...]:
        return (SYMBOLS.index(key[0]), MODES.index(key[1]), key[2], *key[3:])
    result = []
    for key in sorted(groups, key=sort_key):
        members = groups[key]
        prefix = dict(zip(columns, key))
        if "news_type" in columns and "type_code" not in columns:
            codes = {row["type_code"] for row in members}
            if len(codes) != 1:
                raise ValueError("news_type groups more than one exclusive source type_code")
            prefix["type_code"] = next(iter(codes))
        if "week_chicago" in columns and "week_start_chicago" not in columns:
            prefix["week_start_chicago"] = members[0]["week_start_chicago"]
        result.append({**prefix, **_summarize(members)})
    return result


def aggregate(rows: Iterable[Mapping[str, Any]], group_columns: list[str]) -> list[dict[str, Any]]:
    """Return deterministic summaries with mandatory symbol/mode/horizon keys.

    Additional supported dimensions are declared in ``GROUP_DIMENSIONS``. The
    base keys are always inserted, even if ``group_columns`` is empty; thus a
    caller cannot accidentally pool modes, contracts or measurement horizons.
    Empty input returns no groups, rather than fabricated zero-signal cells.
    """
    return _aggregate(_prepare_rows(rows), group_columns)


def build_tables(rows: Iterable[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Build all twelve declared table families after one shared validation."""
    prepared = _prepare_rows(rows)
    return {name: _aggregate(prepared, dimensions) for name, dimensions in TABLE_DIMENSIONS.items()}
