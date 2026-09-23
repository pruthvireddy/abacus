"""Build and validate the immutable session-anchored VWAP research release.

Eligibility is deliberately separate from the causal indicator engine.  A day is
selected retrospectively only when every expected published source minute is
present and all session-level lineage and quality invariants hold.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .continuous_phase1 import _git_version, _sha256

FEATURE_SET = "session_anchored_vwap"
VERSION = "1.0.0"
RELEASE_ID = "session_anchored_vwap__1.0.0"
SOURCE_DATASET = "volume_lead_back_adjusted_v1"
PRODUCTS = ("ES", "NQ", "GC")
INTERVALS = (2, 5)
PRICE_SCALE = 1e-9
MINUTE_NS = 60_000_000_000
UTC = timezone.utc
NY = ZoneInfo("America/New_York")
EPOCH = date(1970, 1, 1)
FLOAT_FEATURES = (
    "vwap",
    "sigma",
    "upper_1sigma",
    "lower_1sigma",
    "upper_2sigma",
    "lower_2sigma",
    "upper_3sigma",
    "lower_3sigma",
    "distance_points",
    "distance_ticks",
    "distance_sigma",
)
EVENTS = (
    "cross_above_vwap",
    "cross_below_vwap",
    "exit_above_upper_2sigma",
    "exit_below_lower_2sigma",
    "reenter_from_above_2sigma",
    "reenter_from_below_2sigma",
)
ANCHORS = ("globex", "asia", "london", "ny")
ANCHOR_OFFSETS_MINUTES = {"globex": 0, "asia": 120, "london": 540, "ny": 930}


class FeatureBuildError(RuntimeError):
    """Raised when an immutable release invariant is violated."""


@dataclass(frozen=True)
class Paths:
    root: Path
    source_manifest: Path
    source_root: Path
    instrument_master: Path
    condition_report: Path
    request: Path
    calendar: Path
    indicator: Path
    schema: Path
    audit: Path
    report: Path
    release_manifest: Path

    @classmethod
    def from_root(cls, root: Path | str) -> "Paths":
        root = Path(root).resolve()
        return cls(
            root=root,
            source_manifest=root / "catalog/datasets/volume_lead_back_adjusted_v1.json",
            source_root=root / "data/curated/continuous/1m",
            instrument_master=root
            / "data/curated/instruments/roll=volume_lead_v1/instrument_master.parquet",
            condition_report=root
            / "data/raw/databento/GLBX.MDP3/ohlcv-1m/GLBX-20260920-577W4VCSK7/condition.json",
            request=root / "requests/fulfilled/session_anchored_vwap__1.0.0.yaml",
            calendar=root / "catalog/calendars/cme_fixed_clock_session_v1.json",
            indicator=root / "catalog/indicators/session_anchored_vwap__1.0.0.json",
            schema=root / "catalog/schemas/session_anchored_vwap__1.0.0.json",
            audit=root
            / "data/features/audits/feature_set=session_anchored_vwap/version=1.0.0/product_day_eligibility.parquet",
            report=root / "reports/quality/session_anchored_vwap__1.0.0.md",
            release_manifest=root / "catalog/datasets/session_anchored_vwap__1.0.0.release.json",
        )

    def output_root(self, interval: int, temporary: bool = False) -> Path:
        version = f"version={VERSION}{'.tmp' if temporary else ''}"
        return (
            self.root
            / f"data/features/bars/{interval}m/feature_set={FEATURE_SET}"
            / version
        )

    def manifest(self, interval: int) -> Path:
        return self.root / f"catalog/datasets/session_anchored_vwap_{interval}m_v1.json"

    def source_partition(self, product: str, year: int) -> Path:
        return (
            self.source_root
            / f"product={product}/roll=volume_lead_v1/variant=back_adjusted"
            / f"adjustment=prior_session_close_additive_v1/year={year}/part-000.parquet"
        )

    def output_partition(self, interval: int, product: str, year: int, *, temporary: bool) -> Path:
        return self.output_root(interval, temporary) / f"product={product}/year={year}/part-000.parquet"


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _relative(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def _descriptor(path: Path, root: Path) -> dict[str, Any]:
    return {"path": _relative(path, root), "bytes": path.stat().st_size, "sha256": _sha256(path)}


def _ts_ns(value: datetime) -> int:
    return int(value.timestamp() * 1_000_000_000)


def session_bounds(session_date: date) -> tuple[int, int]:
    start = datetime.combine(session_date - timedelta(days=1), time(18), NY)
    end = datetime.combine(session_date, time(17), NY)
    return _ts_ns(start.astimezone(UTC)), _ts_ns(end.astimezone(UTC))


def _easter(year: int) -> date:
    """Return Gregorian Easter using the Meeus/Jones/Butcher algorithm."""

    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    last = next_month - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(value: date) -> date:
    if value.weekday() == 5:
        return value - timedelta(days=1)
    if value.weekday() == 6:
        return value + timedelta(days=1)
    return value


def holiday_sessions(product: str, start_year: int, end_year: int) -> dict[date, list[str]]:
    """Generate the pinned CME holiday/shortened-session exclusion set."""

    result: dict[date, list[str]] = defaultdict(list)
    for year in range(start_year, end_year + 1):
        new_year = date(year, 1, 1)
        # CME does not shift a Saturday New Year's closure back onto Friday;
        # for Sunday it observes the following Monday.
        new_year_session = (
            new_year + timedelta(days=1) if new_year.weekday() == 6 else new_year
        )
        fixed = (
            (new_year_session, "New Year's"),
            (_observed(date(year, 7, 4)), "Independence Day"),
            (_observed(date(year, 12, 25)), "Christmas"),
        )
        for value, name in fixed:
            result[value].append(name)
        result[_nth_weekday(year, 1, 0, 3)].append("Martin Luther King Jr. Day")
        result[_nth_weekday(year, 2, 0, 3)].append("Presidents Day")
        result[_easter(year) - timedelta(days=2)].append("Good Friday")
        result[_last_weekday(year, 5, 0)].append("Memorial Day")
        if year >= 2022:
            result[_observed(date(year, 6, 19))].append("Juneteenth")
        result[_nth_weekday(year, 9, 0, 1)].append("Labor Day")
        thanksgiving = _nth_weekday(year, 11, 3, 4)
        result[thanksgiving].append("Thanksgiving")
        result[thanksgiving + timedelta(days=1)].append("Thanksgiving Friday early close")
        adjacent = [(12, 24, "Christmas Eve early close")]
        if product in {"ES", "NQ"}:
            adjacent.append((7, 3, "Independence Day adjacent equity early close"))
        for month, day, name in adjacent:
            value = date(year, month, day)
            if value.weekday() < 5:
                result[value].append(name)
    result[date(2018, 12, 5)].append("National day of mourning")
    result[date(2025, 1, 9)].append("National day of mourning")
    return dict(result)


def calendar_regime(product: str, session_date: date) -> tuple[str, bool]:
    if product in {"ES", "NQ"}:
        if session_date < date(2021, 6, 28):
            return "cme_equity_pause_1615_1630_v1", False
        return "cme_equity_23h_v1", True
    if session_date < date(2015, 9, 21):
        return "comex_close_1715_v1", False
    return "comex_23h_v1", True


def expected_minutes(product: str, session_date: date) -> np.ndarray:
    """Return actual-regime expected minute opens for audit comparisons."""

    start, end = session_bounds(session_date)
    regime, _ = calendar_regime(product, session_date)
    if regime == "comex_close_1715_v1":
        end += 15 * MINUTE_NS
    values = np.arange(start, end, MINUTE_NS, dtype=np.int64)
    if regime == "cme_equity_pause_1615_1630_v1":
        pause_start = _ts_ns(datetime.combine(session_date, time(16, 15), NY).astimezone(UTC))
        pause_end = pause_start + 15 * MINUTE_NS
        values = values[(values < pause_start) | (values >= pause_end)]
    return values


def output_schema(source_hash: str, calendar_hash: str, indicator_hash: str, interval: int) -> pa.Schema:
    fields = [
        pa.field("ts_event", pa.timestamp("ns", tz="UTC"), False),
        pa.field("bar_close_ts", pa.timestamp("ns", tz="UTC"), False),
        pa.field("available_at", pa.timestamp("ns", tz="UTC"), False),
        pa.field("session_date", pa.date32(), False),
        pa.field("product", pa.string(), False),
        pa.field("timeframe", pa.string(), False),
        pa.field("continuous_symbol", pa.string(), False),
        pa.field("instrument_id", pa.uint32(), False),
        pa.field("raw_symbol", pa.string(), False),
        pa.field("open", pa.int64(), False),
        pa.field("high", pa.int64(), False),
        pa.field("low", pa.int64(), False),
        pa.field("close", pa.int64(), False),
        pa.field("volume", pa.uint64(), False),
        pa.field("mapping_start", pa.date32(), False),
        pa.field("mapping_end", pa.date32(), False),
        pa.field("roll_id", pa.int16(), False),
        pa.field("is_roll", pa.bool_(), False),
        pa.field("contains_roll", pa.bool_(), False),
        pa.field("source_batch", pa.string(), False),
        pa.field("price_adjustment", pa.int64(), False),
        pa.field("min_tick", pa.int64(), False),
        pa.field("source_bar_count", pa.uint16(), False),
        pa.field("calendar_regime", pa.string(), False),
        pa.field("is_asia_session", pa.bool_(), False),
        pa.field("is_london_session", pa.bool_(), False),
        pa.field("is_ny_session", pa.bool_(), False),
    ]
    for anchor in ANCHORS:
        fields.extend(
            [
                pa.field(f"{anchor}_anchor_ts", pa.timestamp("ns", tz="UTC"), True),
                *[pa.field(f"{anchor}_{name}", pa.float64(), True) for name in FLOAT_FEATURES],
                pa.field(f"{anchor}_cumulative_volume", pa.uint64(), True),
                pa.field(f"{anchor}_contributing_bar_count", pa.uint32(), True),
                pa.field(f"{anchor}_minutes_since_anchor", pa.int32(), True),
                pa.field(f"{anchor}_anchor_active", pa.bool_(), False),
                *[pa.field(f"{anchor}_{name}", pa.bool_(), True) for name in EVENTS],
            ]
        )
    metadata = {
        b"dataset_release": RELEASE_ID.encode(),
        b"feature_set": FEATURE_SET.encode(),
        b"feature_set_version": VERSION.encode(),
        b"source_dataset": SOURCE_DATASET.encode(),
        b"source_manifest_sha256": source_hash.encode(),
        b"calendar_sha256": calendar_hash.encode(),
        b"indicator_sha256": indicator_hash.encode(),
        b"timeframe_minutes": str(interval).encode(),
        b"calculation_basis": b"output-bar HLC3",
        b"price_encoding": b"OHLC and price_adjustment int64 scale 1e-9",
        b"availability": b"available_at equals exclusive bar_close_ts",
    }
    return pa.schema(fields, metadata=metadata)


AUDIT_SCHEMA = pa.schema(
    [
        pa.field("product", pa.string(), False),
        pa.field("session_date", pa.date32(), False),
        pa.field("session_year", pa.int16(), False),
        pa.field("expected_open", pa.timestamp("ns", tz="UTC"), False),
        pa.field("expected_close", pa.timestamp("ns", tz="UTC"), False),
        pa.field("calendar_regime", pa.string(), False),
        pa.field("calendar_supported", pa.bool_(), False),
        pa.field("calendar_event", pa.string(), True),
        pa.field("eligible", pa.bool_(), False),
        pa.field("exclusion_reasons", pa.list_(pa.string()), False),
        pa.field("expected_minute_count", pa.int32(), False),
        pa.field("observed_minute_count", pa.int32(), False),
        pa.field("missing_expected_minute_count", pa.int32(), False),
        pa.field("outside_expected_minute_count", pa.int32(), False),
        pa.field("duplicate_timestamp_count", pa.int32(), False),
        pa.field("invalid_ohlcv_count", pa.int32(), False),
        pa.field("invalid_volume_count", pa.int32(), False),
        pa.field("contract_count", pa.int16(), False),
        pa.field("adjustment_count", pa.int16(), False),
        pa.field("first_observed_ts", pa.timestamp("ns", tz="UTC"), True),
        pa.field("last_observed_ts", pa.timestamp("ns", tz="UTC"), True),
        pa.field("source_condition_preceding_date", pa.string(), False),
        pa.field("source_condition_session_date", pa.string(), False),
        pa.field("source_quality_provenance", pa.string(), False),
        pa.field("calendar_provenance", pa.string(), False),
    ],
    metadata={
        b"release": RELEASE_ID.encode(),
        b"selection_timing": b"retrospective after session end; not a causal feature",
    },
)


def _float_array(values: np.ndarray) -> pa.Array:
    values = np.asarray(values, dtype=np.float64)
    return pa.array(values, type=pa.float64(), mask=~np.isfinite(values))


def _nullable_timestamp(values: np.ndarray) -> pa.Array:
    values = np.asarray(values, dtype=np.int64)
    return pa.array(values, type=pa.timestamp("ns", tz="UTC"), mask=values == np.iinfo(np.int64).min)


def _nullable_unsigned(values: np.ndarray, arrow_type: pa.DataType) -> pa.Array:
    values = np.asarray(values, dtype=np.int64)
    return pa.array(np.maximum(values, 0), type=arrow_type, mask=values < 0)


def _nullable_bool(values: np.ndarray) -> pa.Array:
    values = np.asarray(values, dtype=np.int8)
    return pa.array(values == 1, type=pa.bool_(), mask=values < 0)


def classify_events(
    previous_close: float,
    current_close: float,
    previous_vwap: float,
    current_vwap: float,
    previous_upper_2sigma: float,
    current_upper_2sigma: float,
    previous_lower_2sigma: float,
    current_lower_2sigma: float,
    previous_sigma: float,
    current_sigma: float,
) -> dict[str, bool | None]:
    """Apply the documented close/event equality rules to two valid bars."""

    result: dict[str, bool | None] = {
        "cross_above_vwap": current_close > current_vwap and previous_close <= previous_vwap,
        "cross_below_vwap": current_close < current_vwap and previous_close >= previous_vwap,
        "exit_above_upper_2sigma": None,
        "exit_below_lower_2sigma": None,
        "reenter_from_above_2sigma": None,
        "reenter_from_below_2sigma": None,
    }
    if previous_sigma <= 0 or current_sigma <= 0:
        return result
    result.update(
        {
            "exit_above_upper_2sigma": current_close > current_upper_2sigma
            and previous_close <= previous_upper_2sigma,
            "exit_below_lower_2sigma": current_close < current_lower_2sigma
            and previous_close >= previous_lower_2sigma,
            "reenter_from_above_2sigma": current_close <= current_upper_2sigma
            and previous_close > previous_upper_2sigma,
            "reenter_from_below_2sigma": current_close >= current_lower_2sigma
            and previous_close < previous_lower_2sigma,
        }
    )
    return result


def anchored_features(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray,
    min_tick: float,
    bar_open_ns: np.ndarray,
    interval: int,
    anchor_offset_minutes: int,
) -> dict[str, np.ndarray]:
    """Calculate one causal anchor group using stable weighted Welford state."""

    n = len(close)
    start_index = anchor_offset_minutes // interval
    result: dict[str, np.ndarray] = {
        name: np.full(n, np.nan, dtype=np.float64) for name in FLOAT_FEATURES
    }
    result["anchor_ts"] = np.full(n, np.iinfo(np.int64).min, dtype=np.int64)
    result["cumulative_volume"] = np.full(n, -1, dtype=np.int64)
    result["contributing_bar_count"] = np.full(n, -1, dtype=np.int64)
    result["minutes_since_anchor"] = np.full(n, -1, dtype=np.int32)
    result["anchor_active"] = np.zeros(n, dtype=np.bool_)
    for event in EVENTS:
        result[event] = np.full(n, -1, dtype=np.int8)
    if start_index >= n:
        return result

    anchor_ts = int(bar_open_ns[start_index])
    total_weight = 0
    mean = 0.0
    m2 = 0.0
    contributing = 0
    price = (high.astype(np.float64) + low.astype(np.float64) + close.astype(np.float64)) / 3.0
    for index in range(start_index, n):
        weight = int(volume[index])
        if weight < 0 or not np.isfinite(price[index]):
            raise FeatureBuildError("negative volume or invalid HLC3 passed to indicator engine")
        if weight > 0:
            if total_weight == 0:
                total_weight = weight
                mean = float(price[index])
                m2 = 0.0
            else:
                new_weight = total_weight + weight
                delta = float(price[index]) - mean
                new_mean = mean + (weight / new_weight) * delta
                m2 += weight * delta * (float(price[index]) - new_mean)
                total_weight = new_weight
                mean = new_mean
            contributing += 1
        result["anchor_active"][index] = True
        result["anchor_ts"][index] = anchor_ts
        result["cumulative_volume"][index] = total_weight
        result["contributing_bar_count"][index] = contributing
        result["minutes_since_anchor"][index] = (index - start_index + 1) * interval
        if total_weight == 0:
            continue
        sigma = math.sqrt(max(m2 / total_weight, 0.0))
        distance = float(close[index]) - mean
        result["vwap"][index] = mean
        result["sigma"][index] = sigma
        for multiplier in (1, 2, 3):
            result[f"upper_{multiplier}sigma"][index] = mean + multiplier * sigma
            result[f"lower_{multiplier}sigma"][index] = mean - multiplier * sigma
        result["distance_points"][index] = distance
        result["distance_ticks"][index] = distance / min_tick
        if sigma > 0:
            result["distance_sigma"][index] = distance / sigma

        if index == start_index or not np.isfinite(result["vwap"][index - 1]):
            continue
        events = classify_events(
            float(close[index - 1]),
            float(close[index]),
            result["vwap"][index - 1],
            mean,
            result["upper_2sigma"][index - 1],
            result["upper_2sigma"][index],
            result["lower_2sigma"][index - 1],
            result["lower_2sigma"][index],
            result["sigma"][index - 1],
            sigma,
        )
        for event, value in events.items():
            if value is not None:
                result[event][index] = int(value)
    return result


SOURCE_COLUMNS = (
    "ts_event",
    "session_date",
    "product",
    "continuous_symbol",
    "instrument_id",
    "raw_symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "mapping_start",
    "mapping_end",
    "roll_id",
    "is_roll",
    "source_batch",
    "price_adjustment",
)


def _read_session_year(paths: Paths, product: str, year: int) -> pa.Table:
    """Read a session-date year, including the prior local-year evening."""

    tables = []
    for source_year in (year - 1, year):
        path = paths.source_partition(product, source_year)
        if path.is_file():
            tables.append(pq.read_table(path, columns=list(SOURCE_COLUMNS)))
    if not tables:
        return pa.table({name: [] for name in SOURCE_COLUMNS})
    table = pa.concat_tables(tables)
    start = pa.scalar(date(year, 1, 1), pa.date32())
    end = pa.scalar(date(year + 1, 1, 1), pa.date32())
    return table.filter(
        pc.and_(pc.greater_equal(table["session_date"], start), pc.less(table["session_date"], end))
    ).sort_by([("ts_event", "ascending")])


def _session_groups(table: pa.Table) -> dict[date, pa.Table]:
    if table.num_rows == 0:
        return {}
    values = table["session_date"].to_numpy(zero_copy_only=False).astype("datetime64[D]")
    changes = np.flatnonzero(np.r_[True, values[1:] != values[:-1]])
    ends = np.r_[changes[1:], len(values)]
    return {
        values[start].astype(object): table.slice(int(start), int(end - start))
        for start, end in zip(changes, ends)
    }


def _condition_index(path: Path) -> dict[date, str]:
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {date.fromisoformat(item["date"]): str(item["condition"]) for item in entries}


def _source_coverage(source_manifest: Mapping[str, Any], product: str) -> tuple[int, int]:
    item = source_manifest["products"][product]
    start = np.datetime64(item["coverage_start"].replace("Z", ""), "ns").astype(np.int64)
    last = np.datetime64(item["coverage_end"].replace("Z", ""), "ns").astype(np.int64)
    return int(start), int(last + MINUTE_NS)


def _audit_one(
    product: str,
    day: date,
    table: pa.Table | None,
    source_coverage: tuple[int, int],
    conditions: Mapping[date, str],
    holidays: Mapping[date, list[str]],
) -> dict[str, Any]:
    expected = expected_minutes(product, day)
    regime, supported = calendar_regime(product, day)
    observed = (
        np.asarray([], dtype=np.int64)
        if table is None
        else table["ts_event"].cast(pa.int64()).to_numpy(zero_copy_only=False)
    )
    unique, counts = np.unique(observed, return_counts=True) if len(observed) else (observed, observed)
    duplicates = int(np.sum(np.maximum(counts - 1, 0))) if len(observed) else 0
    missing = int(len(np.setdiff1d(expected, unique, assume_unique=True)))
    outside = int(len(np.setdiff1d(unique, expected, assume_unique=True)))
    invalid_ohlcv = 0
    invalid_volume = 0
    contract_count = 0
    adjustment_count = 0
    if table is not None and table.num_rows:
        columns = {
            name: table[name].to_numpy(zero_copy_only=False)
            for name in ("open", "high", "low", "close", "volume")
        }
        invalid_ohlcv = int(
            np.count_nonzero(
                (columns["high"] < columns["low"])
                | (columns["high"] < columns["open"])
                | (columns["high"] < columns["close"])
                | (columns["low"] > columns["open"])
                | (columns["low"] > columns["close"])
            )
        )
        # Source volume is uint64; this explicit check documents the invariant.
        invalid_volume = int(np.count_nonzero(columns["volume"].astype(np.float64) < 0))
        contracts = np.unique(
            np.rec.fromarrays(
                [
                    table["instrument_id"].to_numpy(zero_copy_only=False),
                    table["raw_symbol"].to_numpy(zero_copy_only=False),
                    table["roll_id"].to_numpy(zero_copy_only=False),
                ]
            )
        )
        contract_count = len(contracts)
        adjustment_count = len(np.unique(table["price_adjustment"].to_numpy(zero_copy_only=False)))
    preceding_condition = conditions.get(day - timedelta(days=1), "not_listed")
    session_condition = conditions.get(day, "not_listed")
    reasons: list[str] = []
    if not supported:
        reasons.append("unsupported_historical_schedule_regime")
    if day in holidays:
        reasons.append("exchange_holiday_or_shortened_session")
    if source_coverage[0] > int(expected[0]) or source_coverage[1] < int(expected[-1] + MINUTE_NS):
        reasons.append("source_history_partial_session")
    if preceding_condition == "degraded" or session_condition == "degraded":
        reasons.append("source_condition_degraded")
    if table is None or table.num_rows == 0:
        reasons.append("no_source_rows")
    if missing:
        reasons.append("missing_expected_published_minute")
    if outside:
        reasons.append("source_rows_outside_expected_schedule")
    if duplicates:
        reasons.append("duplicate_timestamp")
    if invalid_ohlcv:
        reasons.append("invalid_ohlcv")
    if invalid_volume:
        reasons.append("invalid_volume")
    if contract_count > 1:
        reasons.append("intraday_contract_change")
    if adjustment_count > 1:
        reasons.append("intraday_adjustment_change")
    first = None if not len(observed) else datetime.fromtimestamp(int(observed.min()) / 1e9, UTC)
    last = None if not len(observed) else datetime.fromtimestamp(int(observed.max()) / 1e9, UTC)
    return {
        "product": product,
        "session_date": day,
        "session_year": day.year,
        "expected_open": datetime.fromtimestamp(int(expected[0]) / 1e9, UTC),
        "expected_close": datetime.fromtimestamp(int(expected[-1] + MINUTE_NS) / 1e9, UTC),
        "calendar_regime": regime,
        "calendar_supported": supported,
        "calendar_event": "; ".join(holidays.get(day, [])) or None,
        "eligible": not reasons,
        "exclusion_reasons": reasons,
        "expected_minute_count": len(expected),
        "observed_minute_count": 0 if table is None else table.num_rows,
        "missing_expected_minute_count": missing,
        "outside_expected_minute_count": outside,
        "duplicate_timestamp_count": duplicates,
        "invalid_ohlcv_count": invalid_ohlcv,
        "invalid_volume_count": invalid_volume,
        "contract_count": contract_count,
        "adjustment_count": adjustment_count,
        "first_observed_ts": first,
        "last_observed_ts": last,
        "source_condition_preceding_date": preceding_condition,
        "source_condition_session_date": session_condition,
        "source_quality_provenance": "Databento batch GLBX-20260920-577W4VCSK7 condition.json",
        "calendar_provenance": "cme_fixed_clock_session_v1@1.0.0",
    }


def build_eligibility_audit(
    paths: Paths, source_manifest: Mapping[str, Any]
) -> tuple[pa.Table, dict[str, set[date]]]:
    conditions = _condition_index(paths.condition_report)
    rows: list[dict[str, Any]] = []
    eligible: dict[str, set[date]] = {product: set() for product in PRODUCTS}
    for product in PRODUCTS:
        holidays = holiday_sessions(product, 2010, 2027)
        coverage_start, coverage_end = _source_coverage(source_manifest, product)
        first_date = datetime.fromtimestamp(coverage_start / 1e9, UTC).astimezone(NY).date()
        if datetime.fromtimestamp(coverage_start / 1e9, UTC).astimezone(NY).time() >= time(18):
            first_date += timedelta(days=1)
        last_date = datetime.fromtimestamp((coverage_end - 1) / 1e9, UTC).astimezone(NY).date()
        for year in range(first_date.year, last_date.year + 1):
            groups = _session_groups(_read_session_year(paths, product, year))
            start = max(first_date, date(year, 1, 1))
            end = min(last_date, date(year, 12, 31))
            day = start
            while day <= end:
                if day.weekday() < 5:
                    row = _audit_one(
                        product,
                        day,
                        groups.get(day),
                        (coverage_start, coverage_end),
                        conditions,
                        holidays,
                    )
                    rows.append(row)
                    if row["eligible"]:
                        eligible[product].add(day)
                day += timedelta(days=1)
    return pa.Table.from_pylist(rows, schema=AUDIT_SCHEMA), eligible


def _tick_lookup(master_path: Path) -> dict[tuple[str, int], int]:
    table = pq.read_table(master_path, columns=["product", "roll_id", "min_price_increment"])
    return {
        (str(product), int(roll_id)): int(tick)
        for product, roll_id, tick in zip(
            table["product"].to_pylist(),
            table["roll_id"].to_pylist(),
            table["min_price_increment"].to_pylist(),
        )
    }


def _repeat(value: Any, count: int, arrow_type: pa.DataType) -> pa.Array:
    return pa.array([value] * count, type=arrow_type)


def aggregate_session(
    source: pa.Table,
    product: str,
    interval: int,
    min_tick_fixed: int,
    schema: pa.Schema,
) -> pa.Table:
    """Aggregate one already-eligible source session and calculate features."""

    expected_count = 1380
    if source.num_rows != expected_count or expected_count % interval:
        raise FeatureBuildError(f"{product}: ineligible source session reached aggregation")
    bars = expected_count // interval
    ts = source["ts_event"].cast(pa.int64()).to_numpy(zero_copy_only=False).reshape(bars, interval)
    opens_fixed = source["open"].to_numpy(zero_copy_only=False).reshape(bars, interval)[:, 0]
    highs_fixed = source["high"].to_numpy(zero_copy_only=False).reshape(bars, interval).max(axis=1)
    lows_fixed = source["low"].to_numpy(zero_copy_only=False).reshape(bars, interval).min(axis=1)
    closes_fixed = source["close"].to_numpy(zero_copy_only=False).reshape(bars, interval)[:, -1]
    volumes = source["volume"].to_numpy(zero_copy_only=False).reshape(bars, interval).sum(axis=1, dtype=np.uint64)
    bar_open = ts[:, 0]
    bar_close = bar_open + interval * MINUTE_NS
    day = source["session_date"][0].as_py()
    regime, supported = calendar_regime(product, day)
    if not supported:
        raise FeatureBuildError("unsupported regime reached aggregation")
    clock_minutes = (18 * 60 + np.arange(bars) * interval) % (24 * 60)
    data: dict[str, pa.Array] = {
        "ts_event": pa.array(bar_open, type=pa.timestamp("ns", tz="UTC")),
        "bar_close_ts": pa.array(bar_close, type=pa.timestamp("ns", tz="UTC")),
        "available_at": pa.array(bar_close, type=pa.timestamp("ns", tz="UTC")),
        "session_date": _repeat(day, bars, pa.date32()),
        "product": _repeat(product, bars, pa.string()),
        "timeframe": _repeat(f"{interval}m", bars, pa.string()),
        "continuous_symbol": _repeat(source["continuous_symbol"][0].as_py(), bars, pa.string()),
        "instrument_id": _repeat(source["instrument_id"][0].as_py(), bars, pa.uint32()),
        "raw_symbol": _repeat(source["raw_symbol"][0].as_py(), bars, pa.string()),
        "open": pa.array(opens_fixed, type=pa.int64()),
        "high": pa.array(highs_fixed, type=pa.int64()),
        "low": pa.array(lows_fixed, type=pa.int64()),
        "close": pa.array(closes_fixed, type=pa.int64()),
        "volume": pa.array(volumes, type=pa.uint64()),
        "mapping_start": _repeat(source["mapping_start"][0].as_py(), bars, pa.date32()),
        "mapping_end": _repeat(source["mapping_end"][0].as_py(), bars, pa.date32()),
        "roll_id": _repeat(source["roll_id"][0].as_py(), bars, pa.int16()),
        "is_roll": pa.array(
            source["is_roll"].to_numpy(zero_copy_only=False).reshape(bars, interval).any(axis=1),
            type=pa.bool_(),
        ),
        "contains_roll": pa.array(
            source["is_roll"].to_numpy(zero_copy_only=False).reshape(bars, interval).any(axis=1),
            type=pa.bool_(),
        ),
        "source_batch": _repeat(source["source_batch"][0].as_py(), bars, pa.string()),
        "price_adjustment": _repeat(source["price_adjustment"][0].as_py(), bars, pa.int64()),
        "min_tick": _repeat(min_tick_fixed, bars, pa.int64()),
        "source_bar_count": _repeat(interval, bars, pa.uint16()),
        "calendar_regime": _repeat(regime, bars, pa.string()),
        "is_asia_session": pa.array((clock_minutes >= 20 * 60) | (clock_minutes < 3 * 60)),
        "is_london_session": pa.array((clock_minutes >= 3 * 60) & (clock_minutes < 9 * 60)),
        "is_ny_session": pa.array((clock_minutes >= 9 * 60 + 30) & (clock_minutes < 16 * 60)),
    }
    high = highs_fixed.astype(np.float64) * PRICE_SCALE
    low = lows_fixed.astype(np.float64) * PRICE_SCALE
    close = closes_fixed.astype(np.float64) * PRICE_SCALE
    tick = min_tick_fixed * PRICE_SCALE
    for anchor in ANCHORS:
        values = anchored_features(
            high,
            low,
            close,
            volumes,
            tick,
            bar_open,
            interval,
            ANCHOR_OFFSETS_MINUTES[anchor],
        )
        data[f"{anchor}_anchor_ts"] = _nullable_timestamp(values["anchor_ts"])
        for name in FLOAT_FEATURES:
            data[f"{anchor}_{name}"] = _float_array(values[name])
        data[f"{anchor}_cumulative_volume"] = _nullable_unsigned(
            values["cumulative_volume"], pa.uint64()
        )
        data[f"{anchor}_contributing_bar_count"] = _nullable_unsigned(
            values["contributing_bar_count"], pa.uint32()
        )
        data[f"{anchor}_minutes_since_anchor"] = pa.array(
            np.maximum(values["minutes_since_anchor"], 0),
            type=pa.int32(),
            mask=values["minutes_since_anchor"] < 0,
        )
        data[f"{anchor}_anchor_active"] = pa.array(values["anchor_active"], type=pa.bool_())
        for name in EVENTS:
            data[f"{anchor}_{name}"] = _nullable_bool(values[name])
    return pa.Table.from_arrays([data[field.name] for field in schema], schema=schema)


def aggregate_partition(
    source: pa.Table,
    product: str,
    interval: int,
    eligible: set[date],
    tick_by_roll: Mapping[tuple[str, int], int],
    schema: pa.Schema,
) -> tuple[pa.Table, dict[str, Any]]:
    tables: list[pa.Table] = []
    source_volume = 0
    for day, session in _session_groups(source).items():
        if day not in eligible:
            continue
        roll_id = int(session["roll_id"][0].as_py())
        tick = tick_by_roll[(product, roll_id)]
        table = aggregate_session(session, product, interval, tick, schema)
        tables.append(table)
        source_volume += int(np.sum(session["volume"].to_numpy(zero_copy_only=False), dtype=np.uint64))
    if not tables:
        return pa.Table.from_arrays([pa.array([], type=f.type) for f in schema], schema=schema), {
            "rows": 0,
            "sessions": 0,
            "source_volume": 0,
            "output_volume": 0,
        }
    output = pa.concat_tables(tables)
    output_volume = int(np.sum(output["volume"].to_numpy(zero_copy_only=False), dtype=np.uint64))
    return output, {
        "rows": output.num_rows,
        "sessions": len(tables),
        "source_volume": source_volume,
        "output_volume": output_volume,
        "coverage_start": output["ts_event"][0].as_py().isoformat(),
        "coverage_end": output["bar_close_ts"][-1].as_py().isoformat(),
    }


def _write_parquet(table: pa.Table, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        path,
        compression="zstd",
        compression_level=9,
        use_dictionary=True,
        write_statistics=True,
        version="2.6",
    )


def _schema_contract(schema: pa.Schema) -> dict[str, Any]:
    units: dict[str, str] = {
        "open": "signed int64 fixed-point, scale 1e-9 price units",
        "high": "signed int64 fixed-point, scale 1e-9 price units",
        "low": "signed int64 fixed-point, scale 1e-9 price units",
        "close": "signed int64 fixed-point, scale 1e-9 price units",
        "price_adjustment": "signed int64 fixed-point, scale 1e-9 price units",
        "min_tick": "signed int64 fixed-point, scale 1e-9 price units",
        "volume": "contracts",
    }
    fields = []
    for field in schema:
        name = field.name
        if name.endswith(("_vwap", "_sigma", "_points")) or "upper_" in name or "lower_" in name:
            unit = "float64 price points"
        elif name.endswith("_distance_ticks"):
            unit = "float64 minimum ticks"
        elif name.endswith("_distance_sigma"):
            unit = "float64 standard deviations"
        elif name.endswith("_cumulative_volume"):
            unit = "contracts"
        elif name.endswith("_minutes_since_anchor"):
            unit = "minutes measured at exclusive bar close"
        else:
            unit = units.get(name)
        fields.append(
            {
                "name": name,
                "arrow_type": str(field.type),
                "nullable": field.nullable,
                "unit_or_semantics": unit,
            }
        )
    return {
        "schema_id": "session_anchored_vwap__1.0.0",
        "version": VERSION,
        "fields": fields,
        "key": ["product", "timeframe", "ts_event"],
        "timestamp_semantics": {
            "ts_event": "inclusive bar open",
            "bar_close_ts": "exclusive bar end",
            "available_at": "logical earliest completed-bar availability; equals bar_close_ts",
        },
        "null_semantics": "See catalog/indicators/session_anchored_vwap__1.0.0.json",
    }


def _audit_summary(audit: pa.Table) -> dict[str, Any]:
    rows = audit.to_pylist()
    by_product: dict[str, Any] = {}
    reasons_by_product: dict[str, Counter[str]] = {p: Counter() for p in PRODUCTS}
    reasons_by_year: dict[str, Counter[str]] = defaultdict(Counter)
    unique_by_reason: Counter[str] = Counter()
    for row in rows:
        product = row["product"]
        for reason in row["exclusion_reasons"]:
            reasons_by_product[product][reason] += 1
            reasons_by_year[f"{product}:{row['session_year']}"][reason] += 1
            unique_by_reason[reason] += 1
    for product in PRODUCTS:
        selected = [row for row in rows if row["product"] == product]
        included = sum(bool(row["eligible"]) for row in selected)
        by_product[product] = {
            "candidate_days": len(selected),
            "included_days": included,
            "excluded_days_unique": len(selected) - included,
            "overlapping_reason_counts": dict(sorted(reasons_by_product[product].items())),
        }
    return {
        "by_product": by_product,
        "overlapping_reason_counts_all_products": dict(sorted(unique_by_reason.items())),
        "by_product_year_overlapping_reason_counts": {
            key: dict(sorted(value.items())) for key, value in sorted(reasons_by_year.items())
        },
    }


def _output_files(paths: Paths, interval: int) -> list[dict[str, Any]]:
    return [
        _descriptor(path, paths.root)
        for path in sorted(paths.output_root(interval).glob("product=*/year=*/part-*.parquet"))
    ]


def _product_stats(stats: list[dict[str, Any]], product: str) -> dict[str, Any]:
    selected = [item for item in stats if item["product"] == product]
    rows = sum(item["rows"] for item in selected)
    sessions = sum(item["sessions"] for item in selected)
    starts = [item["coverage_start"] for item in selected if item["rows"]]
    ends = [item["coverage_end"] for item in selected if item["rows"]]
    return {
        "rows": rows,
        "eligible_session_dates": sessions,
        "coverage_start": min(starts) if starts else None,
        "coverage_end": max(ends) if ends else None,
        "source_volume": sum(item["source_volume"] for item in selected),
        "output_volume": sum(item["output_volume"] for item in selected),
        "year_rows": {str(item["year"]): item["rows"] for item in selected if item["rows"]},
    }


def _manifest(
    paths: Paths,
    interval: int,
    hashes: Mapping[str, str],
    source_manifest: Mapping[str, Any],
    stats: list[dict[str, Any]],
    audit_summary: Mapping[str, Any],
    audit_descriptor: Mapping[str, Any],
    schema: pa.Schema,
) -> dict[str, Any]:
    return {
        "dataset_id": f"session_anchored_vwap_{interval}m_v1",
        "dataset_version": VERSION,
        "release_id": RELEASE_ID,
        "feature_set": FEATURE_SET,
        "timeframe": f"{interval}m",
        "build_timestamp_utc": datetime.now(UTC).isoformat(),
        "absolute_dataset_path": str(paths.output_root(interval)),
        "portable_partition_glob": _relative(paths.output_root(interval), paths.root)
        + "/product=*/year=*/part-*.parquet",
        "partitioning": ["product", "year(session_date)"],
        "source": {
            "dataset": SOURCE_DATASET,
            "manifest": _descriptor(paths.source_manifest, paths.root),
            "batch": source_manifest["source_batches"]["ohlcv_1m"],
            "back_adjustment_method": source_manifest["adjustment_methodology"],
            "price_representation": "signed int64 fixed-point scale 1e-9",
            "point_in_time_certified_absolute_prices": False,
            "later_roll_information_used": True,
            "contract_truth_join": "Join product + session_date (and raw_symbol/instrument_id) to volume_lead_unadjusted_v1; use unadjusted prices for fills and P&L.",
        },
        "lineage_hashes": dict(hashes),
        "calculation": {
            "basis": "output-bar HLC3",
            "source_timeframe": "1m",
            "aggregation": "independently direct from 1m",
            "interval_semantics": "[start,end)",
            "alignment": "fixed America/New_York clock",
            "variance": "stable online volume-weighted population variance",
            "anchors": {"globex": "18:00 D-1", "asia": "20:00 D-1", "london": "03:00 D", "ny": "09:30 D"},
        },
        "availability": {
            "ts_event": "bar open",
            "bar_close_ts": "exclusive bar end",
            "available_at": "equals bar_close_ts; modeling convention, not feed-latency claim",
        },
        "eligibility": {
            "timing": "retrospective whole-day research sample selection known after session end; not a predictive feature or live eligibility signal",
            "shared_between_2m_and_5m": True,
            "missing_minute_policy": "exclude whole product-day; never synthesize or fill",
            "no_trade_intervals": "Databento omits intervals with no trades; absence is labeled missing expected published minute and is not asserted to be corruption",
            "audit": dict(audit_descriptor),
            "summary": audit_summary,
        },
        "calendar": {
            "identity": "cme_fixed_clock_session_v1@1.0.0",
            "definition": _descriptor(paths.calendar, paths.root),
            "timezone": "America/New_York",
            "normal_session": "[18:00 D-1,17:00 D)",
            "historical_regime_policy": "exclude unsupported or target-bar-incompatible product-days",
        },
        "indicator": _descriptor(paths.indicator, paths.root),
        "schema_contract": _descriptor(paths.schema, paths.root),
        "schema": _schema_contract(schema)["fields"],
        "products": {product: _product_stats(stats, product) for product in PRODUCTS},
        "product_year_stats": stats,
        "output_files": _output_files(paths, interval),
        "software": {
            "builder": "src/abacus_bhishma/session_anchored_vwap.py",
            "builder_sha256": _sha256(Path(__file__)),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pyarrow": pa.__version__,
            **_git_version(paths.root),
        },
        "validation": {
            "passed": True,
            "volume_conservation": all(item["source_volume"] == item["output_volume"] for item in stats),
            "no_partial_output_bars": True,
            "excluded_product_days_absent": True,
            "finite_float_values": True,
        },
        "limitations": [
            "Historical calendar support begins 2015-09-21 for GC and 2021-06-28 for ES/NQ under this fixed-clock specification; earlier product-days remain in the audit but are excluded.",
            "Conservative completeness excludes no-trade minutes as well as any true delivery gaps; missing expected minutes are not by themselves evidence of vendor corruption.",
            "Eligibility is retrospective sample selection and must not be used as a causal live-trading feature.",
            "Adjusted absolute price history incorporates later rolls and is not point-in-time certified or appropriate for execution/P&L.",
            "VWAP is an output-bar HLC3 approximation, not exact trade-price VWAP.",
            "Formula behavior was compared to the Pine HLC3 definition; live TradingView vendor/bar parity was not measured.",
        ],
    }


def _report(
    manifests: Mapping[int, Mapping[str, Any]], audit_summary: Mapping[str, Any]
) -> str:
    lines = [
        "# Session-anchored VWAP 1.0.0 quality report",
        "",
        "Status: **published and validated**.",
        "",
        "The release applies whole-product-day eligibility retrospectively to the pinned one-minute source, then independently builds 2-minute and 5-minute bars. Eligibility is a research sample-selection rule known after the session ends; it is not present among predictive feature columns.",
        "",
        "## Published coverage",
        "",
        "| Interval | Product | Eligible days | Rows | UTC coverage |",
        "|---|---|---:|---:|---|",
    ]
    for interval in INTERVALS:
        for product in PRODUCTS:
            item = manifests[interval]["products"][product]
            lines.append(
                f"| {interval}m | {product} | {item['eligible_session_dates']:,} | {item['rows']:,} | {item['coverage_start']} – {item['coverage_end']} |"
            )
    lines += [
        "",
        "## Eligibility",
        "",
        "| Product | Candidate days | Included | Excluded (unique days) |",
        "|---|---:|---:|---:|",
    ]
    for product in PRODUCTS:
        item = audit_summary["by_product"][product]
        lines.append(
            f"| {product} | {item['candidate_days']:,} | {item['included_days']:,} | {item['excluded_days_unique']:,} |"
        )
    lines += [
        "",
        "Overlapping exclusion reason counts (a day can contribute to more than one reason):",
        "",
        "| Reason | Product | Count |",
        "|---|---|---:|",
    ]
    for product in PRODUCTS:
        for reason, count in sorted(
            audit_summary["by_product"][product]["overlapping_reason_counts"].items(),
            key=lambda item: (-item[1], item[0]),
        ):
            lines.append(f"| `{reason}` | {product} | {count:,} |")
    lines += [
        "",
        "Per-product/year overlapping reason counts are machine-readable in both manifests. The audit has one row for every candidate weekday and records expected/observed counts, missing/duplicate/invalid counts, observed bounds, all reasons, source condition, and calendar provenance.",
        "",
        "## Calculation and causality",
        "",
        "OHLCV bars are independently aggregated from one-minute data using fixed New York-clock `[start,end)` buckets. `ts_event` is the bar open; `bar_close_ts` and `available_at` are the exclusive end. VWAP uses each completed output bar's HLC3 and volume. Sigma is the weighted population standard deviation computed by stable Welford updates. Anchors accumulate independently to the same Globex close.",
        "",
        "Close-based crossings use contemporaneous levels. Equality stays on the prior side for exits/crosses and counts as re-entry (`<= upper` from above; `>= lower` from below). Two same-anchor consecutive valid bars are required; band events also require positive sigma on both bars.",
        "",
        "## Calendar coverage",
        "",
        "CME notices establish the GC 17:15-to-17:00 close change effective 2015-09-21 and elimination of the ES/NQ 16:15–16:30 ET pause effective 2021-06-28. Earlier GC days do not match the fixed 17:00 specification; earlier ES/NQ days cannot form complete aligned 2-minute bars around the scheduled pause. They are explicitly audited and excluded rather than relabeled.",
        "",
        "## Validation",
        "",
        "The test suite covers unequal-volume hand fixtures, all anchors, zero volume/sigma, event equality/reset rules, aggregation and volume conservation, timestamp availability, DST/session assignment, holiday and missing-minute exclusion, roll/adjustment rules, product independence, shift invariance, truncation causality, deterministic replay, partition invariance, schema/order/key checks, and finite outputs. Full validation checks every published part checksum and every output product-day for complete bars and audit eligibility.",
        "",
        "## Provenance and limitations",
        "",
        "The back-adjusted source is appropriate for analytical features but its absolute historical prices use later roll information. Adding a session-constant adjustment shifts VWAP/bands with price while leaving sigma and point/tick distances invariant. Consumers should join the unadjusted continuous dataset by product/session/raw contract identity for executions and P&L.",
        "",
        "Databento omits one-minute intervals with no trades. Therefore `missing_expected_published_minute` is a conservative exclusion label, not a claim of corruption. Live TradingView parity was not measured; formula comparison is limited to identical OHLCV inputs and matching anchor lifetime, with the Pine display-only first-two-bar suppression intentionally omitted.",
        "",
        "## Rebuild and validation",
        "",
        "```bash",
        "./scripts/build-session-anchored-vwap",
        "./scripts/validate-session-anchored-vwap",
        ".venv/bin/python -m unittest discover -s tests -v",
        "```",
        "",
    ]
    return "\n".join(lines)


def _verify_inputs(paths: Paths) -> tuple[dict[str, Any], dict[str, str]]:
    required = (
        paths.source_manifest,
        paths.instrument_master,
        paths.condition_report,
        paths.request,
        paths.calendar,
        paths.indicator,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FeatureBuildError("missing inputs: " + ", ".join(missing))
    source_manifest = json.loads(paths.source_manifest.read_text(encoding="utf-8"))
    if source_manifest.get("dataset") != SOURCE_DATASET or not source_manifest.get("validation", {}).get("passed"):
        raise FeatureBuildError("pinned source manifest is not the validated back-adjusted dataset")
    hashes = {
        "source_manifest_sha256": _sha256(paths.source_manifest),
        "request_configuration_sha256": _sha256(paths.request),
        "calendar_definition_sha256": _sha256(paths.calendar),
        "indicator_definition_sha256": _sha256(paths.indicator),
        "source_code_sha256": _sha256(Path(__file__)),
        "pyproject_sha256": _sha256(paths.root / "pyproject.toml"),
    }
    return source_manifest, hashes


def build(root: Path | str) -> dict[str, Any]:
    paths = Paths.from_root(root)
    protected = [
        *(paths.output_root(interval) for interval in INTERVALS),
        *(paths.output_root(interval, True) for interval in INTERVALS),
        *(paths.manifest(interval) for interval in INTERVALS),
        paths.release_manifest,
        paths.audit,
        paths.schema,
        paths.report,
    ]
    existing = [str(path) for path in protected if path.exists()]
    if existing:
        raise FeatureBuildError("refusing to overwrite completed or partial version: " + ", ".join(existing))
    source_manifest, hashes = _verify_inputs(paths)
    audit, eligible = build_eligibility_audit(paths, source_manifest)
    if not any(eligible.values()):
        raise FeatureBuildError("eligibility produced no rows; refusing to publish empty dataset")
    tick_by_roll = _tick_lookup(paths.instrument_master)
    schemas = {
        interval: output_schema(
            hashes["source_manifest_sha256"],
            hashes["calendar_definition_sha256"],
            hashes["indicator_definition_sha256"],
            interval,
        )
        for interval in INTERVALS
    }
    # One logical contract serves both intervals; timestamp metadata differs only in Parquet.
    _atomic_json(paths.schema, _schema_contract(schemas[2]))
    hashes["schema_contract_sha256"] = _sha256(paths.schema)
    stats: dict[int, list[dict[str, Any]]] = {interval: [] for interval in INTERVALS}
    years = range(2010, 2027)
    try:
        for product in PRODUCTS:
            for year in years:
                source = _read_session_year(paths, product, year)
                if source.num_rows == 0:
                    continue
                for interval in INTERVALS:
                    table, details = aggregate_partition(
                        source, product, interval, eligible[product], tick_by_roll, schemas[interval]
                    )
                    if table.num_rows == 0:
                        continue
                    output_path = paths.output_partition(
                        interval, product, year, temporary=True
                    )
                    _write_parquet(table, output_path)
                    stats[interval].append({"product": product, "year": year, **details})
        for interval in INTERVALS:
            paths.output_root(interval).parent.mkdir(parents=True, exist_ok=True)
            os.replace(paths.output_root(interval, True), paths.output_root(interval))
    except Exception:
        # Leave temporary output as visible evidence; the immutable build refuses reuse.
        raise
    paths.audit.parent.mkdir(parents=True, exist_ok=True)
    _write_parquet(audit, paths.audit)
    audit_descriptor = _descriptor(paths.audit, paths.root)
    audit_summary = _audit_summary(audit)
    manifests = {
        interval: _manifest(
            paths,
            interval,
            hashes,
            source_manifest,
            stats[interval],
            audit_summary,
            audit_descriptor,
            schemas[interval],
        )
        for interval in INTERVALS
    }
    report = _report(manifests, audit_summary)
    _atomic_bytes(paths.report, report.encode())
    for interval in INTERVALS:
        manifests[interval]["quality_report"] = _descriptor(paths.report, paths.root)
        _atomic_json(paths.manifest(interval), manifests[interval])
    release = {
        "release_id": RELEASE_ID,
        "version": VERSION,
        "feature_set": FEATURE_SET,
        "datasets": {
            f"{interval}m": _descriptor(paths.manifest(interval), paths.root)
            for interval in INTERVALS
        },
        "audit": audit_descriptor,
        "quality_report": _descriptor(paths.report, paths.root),
        "shared_eligible_product_days": True,
    }
    _atomic_json(paths.release_manifest, release)
    validate(paths.root)
    return release


def _validate_output_file(
    path: Path,
    interval: int,
    eligible: Mapping[str, set[date]],
    expected_schema: pa.Schema,
) -> list[str]:
    failures: list[str] = []
    table = pq.read_table(path)
    if not table.schema.equals(expected_schema, check_metadata=True):
        failures.append(f"schema mismatch: {path}")
        return failures
    if table.num_rows == 0:
        failures.append(f"empty published partition: {path}")
        return failures
    product_values = set(table["product"].to_pylist())
    if len(product_values) != 1:
        failures.append(f"multiple products in partition: {path}")
        return failures
    product = next(iter(product_values))
    ts = table["ts_event"].cast(pa.int64()).to_numpy(zero_copy_only=False)
    close_ts = table["bar_close_ts"].cast(pa.int64()).to_numpy(zero_copy_only=False)
    available = table["available_at"].cast(pa.int64()).to_numpy(zero_copy_only=False)
    if np.any(np.diff(ts) <= 0):
        failures.append(f"non-unique or unordered keys: {path}")
    if np.any(close_ts != ts + interval * MINUTE_NS) or np.any(available != close_ts):
        failures.append(f"availability timestamp failure: {path}")
    if np.any(table["source_bar_count"].to_numpy(zero_copy_only=False) != interval):
        failures.append(f"partial output bars: {path}")
    sessions = table["session_date"].to_numpy(zero_copy_only=False).astype("datetime64[D]")
    days, counts = np.unique(sessions, return_counts=True)
    if np.any(counts != 1380 // interval):
        failures.append(f"incomplete output session: {path}")
    if any(day.astype(object) not in eligible[product] for day in days):
        failures.append(f"excluded product-day present: {path}")
    for field in expected_schema:
        if pa.types.is_floating(field.type):
            values = table[field.name].to_numpy(zero_copy_only=False)
            valid = pc.is_valid(table[field.name]).to_numpy(zero_copy_only=False)
            if np.any(~np.isfinite(values[valid])):
                failures.append(f"non-finite float in {field.name}: {path}")
    return failures


def validate(root: Path | str) -> dict[str, Any]:
    paths = Paths.from_root(root)
    source_manifest, hashes = _verify_inputs(paths)
    required = [
        paths.audit,
        paths.schema,
        paths.report,
        paths.release_manifest,
        *(paths.manifest(interval) for interval in INTERVALS),
        *(paths.output_root(interval) for interval in INTERVALS),
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FeatureBuildError("published release is incomplete: " + ", ".join(missing))
    audit = pq.read_table(paths.audit)
    # Parquet normalizes the list child label from ``item`` to ``element``.
    if not audit.schema.equals(AUDIT_SCHEMA, check_metadata=False) or audit.schema.metadata != AUDIT_SCHEMA.metadata:
        raise FeatureBuildError("eligibility audit schema mismatch")
    audit_rows = audit.to_pylist()
    eligible: dict[str, set[date]] = {product: set() for product in PRODUCTS}
    for row in audit_rows:
        if row["eligible"]:
            eligible[row["product"]].add(row["session_date"])
    if not any(eligible.values()):
        raise FeatureBuildError("published audit contains no eligible days")
    failures: list[str] = []
    checked_files = 0
    for interval in INTERVALS:
        manifest = json.loads(paths.manifest(interval).read_text(encoding="utf-8"))
        schema = output_schema(
            hashes["source_manifest_sha256"],
            hashes["calendar_definition_sha256"],
            hashes["indicator_definition_sha256"],
            interval,
        )
        if manifest.get("release_id") != RELEASE_ID or manifest.get("dataset_version") != VERSION:
            failures.append(f"manifest identity mismatch: {interval}m")
        if manifest.get("lineage_hashes", {}).get("source_code_sha256") != hashes["source_code_sha256"]:
            failures.append(f"builder fingerprint mismatch: {interval}m")
        if manifest.get("lineage_hashes", {}).get("schema_contract_sha256") != _sha256(paths.schema):
            failures.append(f"schema fingerprint mismatch: {interval}m")
        file_paths = set()
        for item in manifest.get("output_files", []):
            path = paths.root / item["path"]
            file_paths.add(path.resolve())
            if (
                not path.is_file()
                or path.stat().st_size != item["bytes"]
                or _sha256(path) != item["sha256"]
            ):
                failures.append(f"output checksum mismatch: {path}")
                continue
            failures.extend(_validate_output_file(path, interval, eligible, schema))
            checked_files += 1
        actual = {path.resolve() for path in paths.output_root(interval).glob("product=*/year=*/part-*.parquet")}
        if actual != file_paths:
            failures.append(f"unmanifested or missing output files: {interval}m")
        for product in PRODUCTS:
            stated = manifest["products"][product]["eligible_session_dates"]
            if stated != len(eligible[product]):
                failures.append(f"eligible population mismatch for {product} {interval}m")
            if manifest["products"][product]["source_volume"] != manifest["products"][product]["output_volume"]:
                failures.append(f"volume conservation mismatch for {product} {interval}m")
    release = json.loads(paths.release_manifest.read_text(encoding="utf-8"))
    for interval in INTERVALS:
        item = release["datasets"][f"{interval}m"]
        manifest_path = paths.root / item["path"]
        if _sha256(manifest_path) != item["sha256"]:
            failures.append(f"release manifest checksum mismatch: {interval}m")
    if failures:
        raise FeatureBuildError("validation failed: " + "; ".join(failures[:20]))
    return {
        "passed": True,
        "checked_files": checked_files,
        "eligible_days": {product: len(eligible[product]) for product in PRODUCTS},
        "tests": [
            "manifest and output checksums",
            "schema metadata",
            "unique strictly ordered keys",
            "bar close and availability semantics",
            "no partial bars",
            "eligible-only product-days",
            "finite numeric features",
            "identical 2m/5m populations",
            "volume conservation",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build", help="build and atomically publish version 1.0.0")
    subparsers.add_parser("validate", help="validate the published immutable release")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            result = build(args.root)
        else:
            result = validate(args.root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except FeatureBuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
