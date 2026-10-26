"""Build and validate the volume-led, unadjusted continuous futures layer.

This module deliberately performs no price adjustment. It uses Databento's
date-scoped ``v.0`` mappings and changes contracts only at Globex session opens.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from .paths import PathConfigurationError, resolve_publication_root
from typing import Any, Iterable, Iterator, Sequence
from zoneinfo import ZoneInfo

import databento as db
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

METHODOLOGY = "volume_lead_v1"
DATASET_NAME = "volume_lead_unadjusted_v1"
ALGORITHM_VERSION = "1.0.0"
PRICE_SCALE = "1e-9"
PRODUCTS = ("ES", "NQ", "GC")
CONTINUOUS_SYMBOLS = {"ES": "ES.v.0", "NQ": "NQ.v.0", "GC": "GC.v.0"}
EXPECTED_INTERVALS = {"ES": 67, "NQ": 67, "GC": 82}
EXPECTED_TRANSITIONS = {"ES": 66, "NQ": 66, "GC": 81}
SOURCE_START = date(2010, 6, 6)
SOURCE_END_EXCLUSIVE = date(2026, 9, 20)
NY = ZoneInfo("America/New_York")
UTC = timezone.utc
EPOCH_DATE = date(1970, 1, 1)
OHLCV_BATCH = "GLBX-20260920-577W4VCSK7"
DEFINITION_BATCH = "GLBX-20260920-QQQSGCKWES"


class Phase1Error(RuntimeError):
    """Raised when a Phase 1 invariant is not satisfied."""


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    ohlcv_dbn: Path
    ohlcv_raw: Path
    definition_raw: Path
    roll_map: Path
    temp_root: Path
    manifest: Path
    quality_report: Path

    @classmethod
    def from_root(cls, root: Path | str) -> "ProjectPaths":
        root = Path(root).resolve()
        return cls(
            root=root,
            ohlcv_dbn=root / "data/staging/databento/GLBX.MDP3/ohlcv-1m" / OHLCV_BATCH
            / "glbx-mdp3-20100606-20260919.ohlcv-1m.dbn",
            ohlcv_raw=root / "data/raw/databento/GLBX.MDP3/ohlcv-1m" / OHLCV_BATCH,
            definition_raw=root / "data/raw/databento/GLBX.MDP3/definition" / DEFINITION_BATCH,
            roll_map=root
            / "data/raw/databento/GLBX.MDP3/symbology/continuous/volume-rank-0"
            / "2010-06-06_2026-09-20.json",
            temp_root=root / "data/curated" / f".{DATASET_NAME}.part",
            manifest=root / "catalog/datasets" / f"{DATASET_NAME}.json",
            quality_report=root / "reports/quality" / f"{DATASET_NAME}.md",
        )

    def product_output(self, product: str, *, temporary: bool = False) -> Path:
        base = self.temp_root if temporary else self.root / "data/curated"
        return (
            base
            / "continuous/1m"
            / f"product={product}"
            / f"roll={METHODOLOGY}"
            / "variant=unadjusted"
        )

    def instrument_output(self, *, temporary: bool = False) -> Path:
        base = self.temp_root if temporary else self.root / "data/curated"
        return base / "instruments" / f"roll={METHODOLOGY}"

    def schedule_output(self, *, temporary: bool = False) -> Path:
        base = self.temp_root if temporary else self.root / "data/curated"
        return base / "continuous/1m" / f"roll={METHODOLOGY}"


@dataclass(frozen=True)
class RollInterval:
    product: str
    continuous_symbol: str
    roll_id: int
    mapping_start: date
    mapping_end: date
    instrument_id: int
    effective_start_ns: int
    effective_end_ns: int
    raw_symbol: str = ""
    asset: str = ""
    instrument_class: str = ""
    security_type: str = ""
    cfi: str = ""
    activation: int = 0
    expiration: int = 0
    maturity_year: int = 0
    maturity_month: int = 0
    maturity_day: int = 0
    min_price_increment: int = 0
    contract_multiplier: int = 0
    definition_date: date | None = None


@dataclass(frozen=True)
class SelectionModel:
    product: str
    starts_ns: np.ndarray
    ends_ns: np.ndarray
    instrument_ids: np.ndarray
    raw_symbols: np.ndarray
    mapping_start_days: np.ndarray
    mapping_end_days: np.ndarray


@dataclass(frozen=True)
class SessionCalendar:
    session_days: np.ndarray
    opens_ns: np.ndarray
    closes_ns: np.ndarray
    years: np.ndarray

    @classmethod
    def build(cls, first: date, end_exclusive: date) -> "SessionCalendar":
        dates: list[date] = []
        opens: list[int] = []
        closes: list[int] = []
        years: list[int] = []
        current = first - timedelta(days=2)
        last = end_exclusive + timedelta(days=2)
        while current <= last:
            open_local = datetime.combine(current - timedelta(days=1), time(18), NY)
            close_local = datetime.combine(current, time(17), NY)
            dates.append(current)
            opens.append(_datetime_ns(open_local.astimezone(UTC)))
            closes.append(_datetime_ns(close_local.astimezone(UTC)))
            years.append(current.year)
            current += timedelta(days=1)
        return cls(
            session_days=np.asarray([(d - EPOCH_DATE).days for d in dates], dtype=np.int32),
            opens_ns=np.asarray(opens, dtype=np.int64),
            closes_ns=np.asarray(closes, dtype=np.int64),
            years=np.asarray(years, dtype=np.int16),
        )

    def locate(self, timestamps_ns: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        ts = np.asarray(timestamps_ns, dtype=np.int64)
        indices = np.searchsorted(self.opens_ns, ts, side="right") - 1
        valid = (indices >= 0) & (indices < len(self.opens_ns))
        safe = np.clip(indices, 0, len(self.opens_ns) - 1)
        session_days = self.session_days[safe]
        maintenance = valid & (ts >= self.closes_ns[safe])
        return safe, session_days, maintenance

    def open_ns(self, session_date: date) -> int:
        local = datetime.combine(session_date - timedelta(days=1), time(18), NY)
        return _datetime_ns(local.astimezone(UTC))


OUTPUT_SCHEMA = pa.schema(
    [
        pa.field("ts_event", pa.timestamp("ns", tz="UTC"), nullable=False),
        pa.field("session_date", pa.date32(), nullable=False),
        pa.field("product", pa.string(), nullable=False),
        pa.field("continuous_symbol", pa.string(), nullable=False),
        pa.field("instrument_id", pa.uint32(), nullable=False),
        pa.field("raw_symbol", pa.string(), nullable=False),
        pa.field("open", pa.int64(), nullable=False),
        pa.field("high", pa.int64(), nullable=False),
        pa.field("low", pa.int64(), nullable=False),
        pa.field("close", pa.int64(), nullable=False),
        pa.field("volume", pa.uint64(), nullable=False),
        pa.field("mapping_start", pa.date32(), nullable=False),
        pa.field("mapping_end", pa.date32(), nullable=False),
        pa.field("roll_id", pa.int16(), nullable=False),
        pa.field("is_roll", pa.bool_(), nullable=False),
        pa.field("source_batch", pa.string(), nullable=False),
    ],
    metadata={
        b"dataset": DATASET_NAME.encode(),
        b"methodology": METHODOLOGY.encode(),
        b"algorithm_version": ALGORITHM_VERSION.encode(),
        b"price_encoding": b"signed int64 fixed-point",
        b"price_scale": PRICE_SCALE.encode(),
        b"timezone": b"UTC",
        b"session_timezone": b"America/New_York",
        b"adjusted": b"false",
    },
)

MASTER_SCHEMA = pa.schema(
    [
        pa.field("product", pa.string(), False),
        pa.field("continuous_symbol", pa.string(), False),
        pa.field("roll_id", pa.int16(), False),
        pa.field("mapping_start", pa.date32(), False),
        pa.field("mapping_end", pa.date32(), False),
        pa.field("instrument_id", pa.uint32(), False),
        pa.field("raw_symbol", pa.string(), False),
        pa.field("asset", pa.string(), False),
        pa.field("instrument_class", pa.string(), False),
        pa.field("security_type", pa.string(), False),
        pa.field("cfi", pa.string(), False),
        pa.field("activation", pa.timestamp("ns", tz="UTC"), False),
        pa.field("expiration", pa.timestamp("ns", tz="UTC"), False),
        pa.field("maturity_year", pa.uint16(), False),
        pa.field("maturity_month", pa.uint8(), False),
        pa.field("maturity_day", pa.uint8(), False),
        pa.field("min_price_increment", pa.int64(), False),
        pa.field("contract_multiplier", pa.int64(), False),
        pa.field("definition_date", pa.date32(), False),
        pa.field("definition_source_batch", pa.string(), False),
    ],
    metadata={
        b"methodology": METHODOLOGY.encode(),
        b"definition_resolution": b"mapping interval plus date-scoped instrument_id",
        b"fixed_point_scale": PRICE_SCALE.encode(),
    },
)

SCHEDULE_SCHEMA = pa.schema(
    [
        pa.field("product", pa.string(), False),
        pa.field("continuous_symbol", pa.string(), False),
        pa.field("roll_id", pa.int16(), False),
        pa.field("mapping_start", pa.date32(), False),
        pa.field("mapping_end", pa.date32(), False),
        pa.field("effective_session_date", pa.date32(), False),
        pa.field("effective_timestamp_utc", pa.timestamp("ns", tz="UTC"), False),
        pa.field("old_instrument_id", pa.uint32(), False),
        pa.field("old_raw_symbol", pa.string(), False),
        pa.field("new_instrument_id", pa.uint32(), False),
        pa.field("new_raw_symbol", pa.string(), False),
        pa.field("source_mapping_file", pa.string(), False),
        pa.field("algorithm_version", pa.string(), False),
    ],
    metadata={b"methodology": METHODOLOGY.encode(), b"session_timezone": b"America/New_York"},
)

SOURCE_DIGEST_DTYPE = np.dtype(
    [
        ("ts_event", "<u8"),
        ("instrument_id", "<u4"),
        ("open", "<i8"),
        ("high", "<i8"),
        ("low", "<i8"),
        ("close", "<i8"),
        ("volume", "<u8"),
    ],
    align=False,
)


def _datetime_ns(value: datetime) -> int:
    return int(value.timestamp()) * 1_000_000_000 + value.microsecond * 1_000


def _date_from_text(value: str) -> date:
    return date.fromisoformat(value)


def _text(value: Any) -> str:
    if isinstance(value, (bytes, np.bytes_)):
        return bytes(value).decode("ascii", errors="strict").rstrip("\x00 ")
    return str(value).rstrip("\x00 ")


def _date32(values: np.ndarray | Sequence[int]) -> pa.Array:
    return pa.array(np.asarray(values, dtype=np.int32), type=pa.int32()).cast(pa.date32())


def _timestamp_array(values: np.ndarray | Sequence[int]) -> pa.Array:
    return pa.array(np.asarray(values, dtype=np.int64), type=pa.timestamp("ns", tz="UTC"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _close_store(store: db.DBNStore) -> None:
    """Close Databento 0.64's file source (the pinned release has no public close method)."""

    getattr(store, "_data_source").reader.close()


def read_dbn_array(path: Path) -> np.ndarray:
    store = db.DBNStore.from_file(path)
    try:
        return store.to_ndarray()
    finally:
        _close_store(store)


def iter_dbn_arrays(path: Path, *, count: int) -> Iterator[np.ndarray]:
    store = db.DBNStore.from_file(path)
    try:
        yield from store.to_ndarray(count=count)
    finally:
        _close_store(store)


def _ensure_sources(paths: ProjectPaths) -> None:
    required = [paths.ohlcv_dbn, paths.ohlcv_raw, paths.definition_raw, paths.roll_map]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise Phase1Error("missing source inputs: " + ", ".join(missing))
    for label, condition_path in (
        ("OHLCV", paths.ohlcv_raw / "condition.json"),
        ("definition", paths.definition_raw / "condition.json"),
    ):
        conditions = json.loads(condition_path.read_text(encoding="utf-8"))
        degraded = sum(row["condition"] == "degraded" for row in conditions)
        if degraded != 32:
            raise Phase1Error(f"{label} condition report: expected 32 degraded dates, got {degraded}")


def load_roll_intervals(paths: ProjectPaths, calendar: SessionCalendar) -> dict[str, list[RollInterval]]:
    payload = json.loads(paths.roll_map.read_text(encoding="utf-8"))
    result = payload["response"]["result"]
    by_product: dict[str, list[RollInterval]] = {}
    for product in PRODUCTS:
        symbol = CONTINUOUS_SYMBOLS[product]
        raw_intervals = result[symbol]
        intervals: list[RollInterval] = []
        for raw in raw_intervals:
            original_start = _date_from_text(raw["d0"])
            original_end = _date_from_text(raw["d1"])
            start = max(original_start, SOURCE_START)
            end = min(original_end, SOURCE_END_EXCLUSIVE)
            if start >= end:
                continue
            intervals.append(
                RollInterval(
                    product=product,
                    continuous_symbol=symbol,
                    roll_id=len(intervals),
                    mapping_start=start,
                    mapping_end=end,
                    instrument_id=int(raw["s"]),
                    effective_start_ns=calendar.open_ns(start),
                    effective_end_ns=calendar.open_ns(end),
                )
            )
        if len(intervals) != EXPECTED_INTERVALS[product]:
            raise Phase1Error(
                f"{product}: expected {EXPECTED_INTERVALS[product]} mapping intervals, got {len(intervals)}"
            )
        for previous, current in zip(intervals, intervals[1:]):
            if previous.mapping_end != current.mapping_start:
                raise Phase1Error(f"{product}: mapping intervals are not contiguous")
            if previous.effective_end_ns != current.effective_start_ns:
                raise Phase1Error(f"{product}: session-effective mappings are not contiguous")
        by_product[product] = intervals
    return by_product


def resolve_instrument_master(
    paths: ProjectPaths, intervals: dict[str, list[RollInterval]]
) -> dict[str, list[RollInterval]]:
    files = {
        datetime.strptime(path.name.split(".")[0].rsplit("-", 1)[1], "%Y%m%d").date(): path
        for path in paths.definition_raw.glob("*.definition.dbn.zst")
    }
    cache: dict[date, np.ndarray] = {}

    def records_on(day: date) -> np.ndarray | None:
        path = files.get(day)
        if path is None:
            return None
        if day not in cache:
            cache[day] = read_dbn_array(path)
        return cache[day]

    resolved: dict[str, list[RollInterval]] = {}
    for product, product_intervals in intervals.items():
        output: list[RollInterval] = []
        for interval in product_intervals:
            day = interval.mapping_start
            chosen: tuple[date, np.void] | None = None
            while day < interval.mapping_end:
                records = records_on(day)
                if records is not None:
                    matches = records[records["instrument_id"] == interval.instrument_id]
                    if len(matches):
                        chosen = (day, matches[np.argmax(matches["ts_recv"])])
                        break
                day += timedelta(days=1)
            if chosen is None:
                raise Phase1Error(
                    f"{product} roll_id={interval.roll_id}: instrument {interval.instrument_id} "
                    "has no definition snapshot inside its mapping interval"
                )
            definition_date, record = chosen
            asset = _text(record["asset"])
            instrument_class = _text(record["instrument_class"])
            security_type = _text(record["security_type"])
            leg_count = int(record["leg_count"])
            if not (
                asset == product
                and instrument_class == "F"
                and security_type == "FUT"
                and leg_count == 0
            ):
                raise Phase1Error(
                    f"{product} roll_id={interval.roll_id}: definition is not an outright future "
                    f"(asset={asset!r}, class={instrument_class!r}, type={security_type!r}, legs={leg_count})"
                )
            output.append(
                replace(
                    interval,
                    raw_symbol=_text(record["raw_symbol"]),
                    asset=asset,
                    instrument_class=instrument_class,
                    security_type=security_type,
                    cfi=_text(record["cfi"]),
                    activation=int(record["activation"]),
                    expiration=int(record["expiration"]),
                    maturity_year=int(record["maturity_year"]),
                    maturity_month=int(record["maturity_month"]),
                    maturity_day=int(record["maturity_day"]),
                    min_price_increment=int(record["min_price_increment"]),
                    contract_multiplier=int(record["contract_multiplier"]),
                    definition_date=definition_date,
                )
            )
        resolved[product] = output
    if sum(map(len, resolved.values())) != 216:
        raise Phase1Error("instrument master did not resolve exactly 216 intervals")
    return resolved


def _selection_models(intervals: dict[str, list[RollInterval]]) -> dict[str, SelectionModel]:
    output: dict[str, SelectionModel] = {}
    for product, rows in intervals.items():
        output[product] = SelectionModel(
            product=product,
            starts_ns=np.asarray([row.effective_start_ns for row in rows], dtype=np.int64),
            ends_ns=np.asarray([row.effective_end_ns for row in rows], dtype=np.int64),
            instrument_ids=np.asarray([row.instrument_id for row in rows], dtype=np.uint32),
            raw_symbols=np.asarray([row.raw_symbol for row in rows], dtype=object),
            mapping_start_days=np.asarray(
                [(row.mapping_start - EPOCH_DATE).days for row in rows], dtype=np.int32
            ),
            mapping_end_days=np.asarray(
                [(row.mapping_end - EPOCH_DATE).days for row in rows], dtype=np.int32
            ),
        )
    return output


def select_indices(records: np.ndarray, model: SelectionModel) -> tuple[np.ndarray, np.ndarray]:
    """Return source row positions and mapping indices selected for one product."""

    timestamps = records["ts_event"].astype(np.int64, copy=False)
    mapping_indices = np.searchsorted(model.starts_ns, timestamps, side="right") - 1
    safe = np.clip(mapping_indices, 0, len(model.starts_ns) - 1)
    selected = (
        (mapping_indices >= 0)
        & (timestamps < model.ends_ns[safe])
        & (records["instrument_id"] == model.instrument_ids[safe])
    )
    positions = np.flatnonzero(selected)
    return positions, safe[positions]


def _master_table(intervals: dict[str, list[RollInterval]]) -> pa.Table:
    rows: list[dict[str, Any]] = []
    for product in PRODUCTS:
        for interval in intervals[product]:
            rows.append(
                {
                    "product": product,
                    "continuous_symbol": interval.continuous_symbol,
                    "roll_id": interval.roll_id,
                    "mapping_start": interval.mapping_start,
                    "mapping_end": interval.mapping_end,
                    "instrument_id": interval.instrument_id,
                    "raw_symbol": interval.raw_symbol,
                    "asset": interval.asset,
                    "instrument_class": interval.instrument_class,
                    "security_type": interval.security_type,
                    "cfi": interval.cfi,
                    "activation": datetime.fromtimestamp(interval.activation / 1e9, UTC),
                    "expiration": datetime.fromtimestamp(interval.expiration / 1e9, UTC),
                    "maturity_year": interval.maturity_year,
                    "maturity_month": interval.maturity_month,
                    "maturity_day": interval.maturity_day,
                    "min_price_increment": interval.min_price_increment,
                    "contract_multiplier": interval.contract_multiplier,
                    "definition_date": interval.definition_date,
                    "definition_source_batch": DEFINITION_BATCH,
                }
            )
    return pa.Table.from_pylist(rows, schema=MASTER_SCHEMA)


def _schedule_rows(paths: ProjectPaths, intervals: dict[str, list[RollInterval]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_mapping = str(paths.roll_map.relative_to(paths.root))
    for product in PRODUCTS:
        product_rows = intervals[product]
        for previous, current in zip(product_rows, product_rows[1:]):
            rows.append(
                {
                    "product": product,
                    "continuous_symbol": current.continuous_symbol,
                    "roll_id": current.roll_id,
                    "mapping_start": current.mapping_start,
                    "mapping_end": current.mapping_end,
                    "effective_session_date": current.mapping_start,
                    "effective_timestamp_utc": datetime.fromtimestamp(
                        current.effective_start_ns / 1e9, UTC
                    ),
                    "old_instrument_id": previous.instrument_id,
                    "old_raw_symbol": previous.raw_symbol,
                    "new_instrument_id": current.instrument_id,
                    "new_raw_symbol": current.raw_symbol,
                    "source_mapping_file": source_mapping,
                    "algorithm_version": ALGORITHM_VERSION,
                }
            )
    if len(rows) != 213:
        raise Phase1Error(f"expected 213 transitions, got {len(rows)}")
    return rows


def _write_reference_outputs(
    paths: ProjectPaths, intervals: dict[str, list[RollInterval]], *, temporary: bool
) -> None:
    instrument_dir = paths.instrument_output(temporary=temporary)
    schedule_dir = paths.schedule_output(temporary=temporary)
    instrument_dir.mkdir(parents=True, exist_ok=True)
    schedule_dir.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        _master_table(intervals),
        instrument_dir / "instrument_master.parquet",
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
    )
    schedule_rows = _schedule_rows(paths, intervals)
    schedule_table = pa.Table.from_pylist(schedule_rows, schema=SCHEDULE_SCHEMA)
    pq.write_table(
        schedule_table,
        schedule_dir / "roll_schedule.parquet",
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
    )
    csv_path = schedule_dir / "roll_schedule.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(schedule_rows[0])
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in schedule_rows:
            writer.writerow(
                {
                    **row,
                    "effective_timestamp_utc": row["effective_timestamp_utc"].isoformat(),
                }
            )


def _digest_records(records: np.ndarray, positions: np.ndarray, digest: Any) -> None:
    selected = records[positions]
    packed = np.empty(len(selected), dtype=SOURCE_DIGEST_DTYPE)
    for field in SOURCE_DIGEST_DTYPE.names or ():
        packed[field] = selected[field]
    digest.update(packed.tobytes())


def _build_output_table(
    records: np.ndarray,
    positions: np.ndarray,
    mapping_indices: np.ndarray,
    model: SelectionModel,
    calendar: SessionCalendar,
    seen_rolls: set[int],
) -> tuple[pa.Table, np.ndarray, np.ndarray]:
    selected = records[positions]
    timestamps = selected["ts_event"].astype(np.int64, copy=False)
    session_indices, session_days, _ = calendar.locate(timestamps)
    is_roll = np.zeros(len(selected), dtype=np.bool_)
    for roll_id in np.unique(mapping_indices):
        value = int(roll_id)
        if value > 0 and value not in seen_rolls:
            is_roll[int(np.flatnonzero(mapping_indices == roll_id)[0])] = True
            seen_rolls.add(value)
    schema = OUTPUT_SCHEMA
    table = pa.Table.from_arrays(
        [
            _timestamp_array(timestamps),
            _date32(session_days),
            pa.array(np.full(len(selected), model.product), type=pa.string()),
            pa.array(np.full(len(selected), CONTINUOUS_SYMBOLS[model.product]), type=pa.string()),
            pa.array(selected["instrument_id"], type=pa.uint32()),
            pa.array(model.raw_symbols[mapping_indices].tolist(), type=pa.string()),
            pa.array(selected["open"], type=pa.int64()),
            pa.array(selected["high"], type=pa.int64()),
            pa.array(selected["low"], type=pa.int64()),
            pa.array(selected["close"], type=pa.int64()),
            pa.array(selected["volume"], type=pa.uint64()),
            _date32(model.mapping_start_days[mapping_indices]),
            _date32(model.mapping_end_days[mapping_indices]),
            pa.array(mapping_indices.astype(np.int16), type=pa.int16()),
            pa.array(is_roll, type=pa.bool_()),
            pa.array(np.full(len(selected), OHLCV_BATCH), type=pa.string()),
        ],
        schema=schema,
    )
    return table, calendar.years[session_indices], is_roll


def stitch_series(
    paths: ProjectPaths,
    intervals: dict[str, list[RollInterval]],
    calendar: SessionCalendar,
    *,
    chunk_size: int,
) -> dict[str, Any]:
    models = _selection_models(intervals)
    writers: dict[tuple[str, int], pq.ParquetWriter] = {}
    seen_rolls = {product: set() for product in PRODUCTS}
    digests = {product: hashlib.sha256() for product in PRODUCTS}
    rows = Counter()
    year_rows: dict[str, Counter[int]] = {product: Counter() for product in PRODUCTS}
    maintenance = Counter()
    source_maintenance = 0
    try:
        for records in iter_dbn_arrays(paths.ohlcv_dbn, count=chunk_size):
            timestamps = records["ts_event"].astype(np.int64, copy=False)
            _, _, in_break = calendar.locate(timestamps)
            source_maintenance += int(np.count_nonzero(in_break))
            for product in PRODUCTS:
                positions, mapping_indices = select_indices(records, models[product])
                if not len(positions):
                    continue
                _digest_records(records, positions, digests[product])
                table, years, roll_flags = _build_output_table(
                    records,
                    positions,
                    mapping_indices,
                    models[product],
                    calendar,
                    seen_rolls[product],
                )
                rows[product] += len(positions)
                maintenance[product] += int(np.count_nonzero(in_break[positions]))
                for year in np.unique(years):
                    mask = years == year
                    year_value = int(year)
                    year_table = table.filter(pa.array(mask))
                    key = (product, year_value)
                    if key not in writers:
                        directory = paths.product_output(product, temporary=True) / f"year={year_value}"
                        directory.mkdir(parents=True, exist_ok=True)
                        writers[key] = pq.ParquetWriter(
                            directory / "part-000.parquet",
                            OUTPUT_SCHEMA,
                            compression="zstd",
                            use_dictionary=["product", "continuous_symbol", "raw_symbol", "source_batch"],
                            write_statistics=True,
                        )
                    writers[key].write_table(year_table, row_group_size=250_000)
                    year_rows[product][year_value] += int(np.count_nonzero(mask))
    finally:
        for writer in writers.values():
            writer.close()
    for product in PRODUCTS:
        expected = set(range(1, EXPECTED_INTERVALS[product]))
        if seen_rolls[product] != expected:
            missing = sorted(expected - seen_rolls[product])
            raise Phase1Error(f"{product}: no emitted first bar for roll IDs {missing}")
    return {
        "rows": dict(rows),
        "year_rows": {product: dict(sorted(counts.items())) for product, counts in year_rows.items()},
        "selected_source_sha256": {product: digests[product].hexdigest() for product in PRODUCTS},
        "maintenance_break_bars": dict(maintenance),
        "all_source_maintenance_break_bars": source_maintenance,
    }


def _read_output_batches(product_path: Path) -> Iterator[pa.RecordBatch]:
    files = sorted(product_path.glob("year=*/part-*.parquet"))
    if not files:
        raise Phase1Error(f"no Parquet output files under {product_path}")
    for path in files:
        parquet = pq.ParquetFile(path)
        if parquet.schema_arrow != OUTPUT_SCHEMA:
            raise Phase1Error(f"schema mismatch: {path}")
        yield from parquet.iter_batches(batch_size=500_000)


def _digest_output_batch(batch: pa.RecordBatch, digest: Any) -> None:
    packed = np.empty(batch.num_rows, dtype=SOURCE_DIGEST_DTYPE)
    for field in SOURCE_DIGEST_DTYPE.names or ():
        values = batch.column(batch.schema.get_field_index(field)).to_numpy(zero_copy_only=False)
        if field == "ts_event":
            values = values.astype("datetime64[ns]").astype(np.uint64)
        packed[field] = values
    digest.update(packed.tobytes())


def _scan_source_truth(
    paths: ProjectPaths,
    models: dict[str, SelectionModel],
    calendar: SessionCalendar,
    *,
    chunk_size: int,
) -> dict[str, Any]:
    digests = {product: hashlib.sha256() for product in PRODUCTS}
    counts = Counter()
    source_maintenance = 0
    for records in iter_dbn_arrays(paths.ohlcv_dbn, count=chunk_size):
        timestamps = records["ts_event"].astype(np.int64, copy=False)
        _, _, in_break = calendar.locate(timestamps)
        source_maintenance += int(np.count_nonzero(in_break))
        for product in PRODUCTS:
            positions, _ = select_indices(records, models[product])
            counts[product] += len(positions)
            if len(positions):
                _digest_records(records, positions, digests[product])
    return {
        "counts": dict(counts),
        "digests": {product: digests[product].hexdigest() for product in PRODUCTS},
        "all_source_maintenance_break_bars": source_maintenance,
    }


def validate_outputs(
    paths: ProjectPaths,
    intervals: dict[str, list[RollInterval]],
    calendar: SessionCalendar,
    *,
    temporary: bool,
    chunk_size: int,
    compare_source: bool = True,
) -> dict[str, Any]:
    models = _selection_models(intervals)
    failures: list[str] = []
    metrics: dict[str, Any] = {"products": {}}

    master_path = paths.instrument_output(temporary=temporary) / "instrument_master.parquet"
    schedule_path = paths.schedule_output(temporary=temporary) / "roll_schedule.parquet"
    if pq.read_table(master_path).num_rows != 216:
        failures.append("instrument master does not contain 216 rows")
    schedule_table = pq.read_table(schedule_path)
    if schedule_table.num_rows != 213:
        failures.append("roll schedule does not contain 213 rows")

    for product in PRODUCTS:
        digest = hashlib.sha256()
        row_count = 0
        duplicate_count = 0
        ordering_failures = 0
        ohlc_failures = 0
        mapping_failures = 0
        session_failures = 0
        adjustment_failures = 0
        roll_counts = Counter()
        coverage_min: int | None = None
        coverage_max: int | None = None
        last_ts: int | None = None
        last_session_day: int | None = None
        gap_count = 0
        within_session_gaps = 0
        max_gap_minutes = 0
        year_rows = Counter()
        maintenance_count = 0
        model = models[product]
        for batch in _read_output_batches(paths.product_output(product, temporary=temporary)):
            _digest_output_batch(batch, digest)
            data = {name: batch.column(batch.schema.get_field_index(name)).to_numpy(zero_copy_only=False) for name in (
                "ts_event", "session_date", "instrument_id", "open", "high", "low", "close", "volume",
                "mapping_start", "mapping_end", "roll_id", "is_roll"
            )}
            ts = data["ts_event"].astype("datetime64[ns]").astype(np.int64)
            session_days = data["session_date"].astype("datetime64[D]").astype(np.int32)
            mapping_start_days = data["mapping_start"].astype("datetime64[D]").astype(np.int32)
            mapping_end_days = data["mapping_end"].astype("datetime64[D]").astype(np.int32)
            if len(ts):
                coverage_min = int(ts[0]) if coverage_min is None else min(coverage_min, int(ts[0]))
                coverage_max = int(ts[-1]) if coverage_max is None else max(coverage_max, int(ts[-1]))
                differences = np.diff(ts)
                duplicate_count += int(np.count_nonzero(differences == 0))
                ordering_failures += int(np.count_nonzero(differences < 0))
                if last_ts is not None:
                    cross_diff = int(ts[0]) - last_ts
                    duplicate_count += int(cross_diff == 0)
                    ordering_failures += int(cross_diff < 0)
                    if cross_diff > 60_000_000_000:
                        gap_count += 1
                        max_gap_minutes = max(max_gap_minutes, cross_diff // 60_000_000_000)
                        if int(session_days[0]) == last_session_day:
                            within_session_gaps += 1
                gap_mask = differences > 60_000_000_000
                gap_count += int(np.count_nonzero(gap_mask))
                if np.any(gap_mask):
                    max_gap_minutes = max(
                        max_gap_minutes, int(np.max(differences[gap_mask]) // 60_000_000_000)
                    )
                    within_session_gaps += int(
                        np.count_nonzero(gap_mask & (session_days[1:] == session_days[:-1]))
                    )
                last_ts = int(ts[-1])
                last_session_day = int(session_days[-1])
            ohlc_failures += int(
                np.count_nonzero(
                    (data["high"] < data["open"])
                    | (data["high"] < data["close"])
                    | (data["high"] < data["low"])
                    | (data["low"] > data["open"])
                    | (data["low"] > data["close"])
                )
            )
            mapping_indices = np.searchsorted(model.mapping_start_days, session_days, side="right") - 1
            safe = np.clip(mapping_indices, 0, len(model.mapping_start_days) - 1)
            valid_mapping = (
                (mapping_indices >= 0)
                & (session_days < model.mapping_end_days[safe])
                & (data["instrument_id"] == model.instrument_ids[safe])
                & (data["roll_id"] == safe)
                & (mapping_start_days == model.mapping_start_days[safe])
                & (mapping_end_days == model.mapping_end_days[safe])
            )
            mapping_failures += int(np.count_nonzero(~valid_mapping))
            _, derived_session_days, in_break = calendar.locate(ts)
            session_failures += int(np.count_nonzero(derived_session_days != session_days))
            maintenance_count += int(np.count_nonzero(in_break))
            roll_ids = data["roll_id"][data["is_roll"]]
            roll_counts.update(map(int, roll_ids))
            row_count += batch.num_rows
            for year, count in zip(*np.unique(calendar.years[calendar.locate(ts)[0]], return_counts=True)):
                year_rows[int(year)] += int(count)
            # Phase 1's output values are exact integers; the source digest below proves no adjustment.
            adjustment_failures += 0
        expected_rolls = set(range(1, EXPECTED_INTERVALS[product]))
        observed_rolls = set(roll_counts)
        bad_roll_marks = sum(count != 1 for count in roll_counts.values())
        if observed_rolls != expected_rolls or bad_roll_marks:
            failures.append(f"{product}: is_roll markers do not match all transitions exactly once")
        for label, count in (
            ("duplicate timestamps", duplicate_count),
            ("ordering failures", ordering_failures),
            ("OHLC failures", ohlc_failures),
            ("mapping failures", mapping_failures),
            ("session-date failures", session_failures),
            ("adjustment failures", adjustment_failures),
        ):
            if count:
                failures.append(f"{product}: {label}={count}")
        metrics["products"][product] = {
            "rows": row_count,
            "coverage_start": _iso_ns(coverage_min),
            "coverage_end": _iso_ns(coverage_max),
            "year_rows": {str(year): count for year, count in sorted(year_rows.items())},
            "output_source_record_sha256": digest.hexdigest(),
            "duplicate_timestamps": duplicate_count,
            "ordering_failures": ordering_failures,
            "ohlc_failures": ohlc_failures,
            "mapping_failures": mapping_failures,
            "session_date_failures": session_failures,
            "is_roll_rows": sum(roll_counts.values()),
            "timestamp_gaps_over_one_minute": gap_count,
            "within_session_gaps_over_one_minute": within_session_gaps,
            "maximum_gap_minutes": max_gap_minutes,
            "maintenance_break_bars": maintenance_count,
        }

    if compare_source:
        source_truth = _scan_source_truth(
            paths, models, calendar, chunk_size=chunk_size
        )
        metrics["source_truth"] = source_truth
        for product in PRODUCTS:
            current = metrics["products"][product]
            if current["rows"] != source_truth["counts"][product]:
                failures.append(f"{product}: output/source row counts differ")
            if current["output_source_record_sha256"] != source_truth["digests"][product]:
                failures.append(f"{product}: OHLCV output differs from selected source records")
    metrics["failures"] = failures
    metrics["passed"] = not failures
    if failures:
        raise Phase1Error("validation failed:\n- " + "\n- ".join(failures))
    return metrics


def _iso_ns(value: int | None) -> str | None:
    if value is None:
        return None
    seconds, nanos = divmod(value, 1_000_000_000)
    base = datetime.fromtimestamp(seconds, UTC)
    return base.strftime("%Y-%m-%dT%H:%M:%S") + f".{nanos:09d}Z"


def _condition_summary(path: Path, start: date, end_exclusive: date) -> dict[str, Any]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    counts = Counter(row["condition"] for row in rows)
    delivered = {_date_from_text(row["date"]) for row in rows}
    all_dates: set[date] = set()
    current = start
    while current < end_exclusive:
        all_dates.add(current)
        current += timedelta(days=1)
    degraded = [row["date"] for row in rows if row["condition"] == "degraded"]
    return {
        "entries": len(rows),
        "available": counts.get("available", 0),
        "degraded": counts.get("degraded", 0),
        "degraded_dates": degraded,
        "no_delivered_file_no_published_records": len(all_dates - delivered),
        "first_condition_date": min(delivered).isoformat(),
        "last_condition_date": max(delivered).isoformat(),
    }


def _source_files(paths: ProjectPaths) -> list[dict[str, Any]]:
    candidates = [
        paths.ohlcv_dbn,
        paths.ohlcv_raw / "glbx-mdp3-20100606-20260919.ohlcv-1m.dbn.zst",
        paths.ohlcv_raw / f"{OHLCV_BATCH}.zip",
        paths.roll_map,
        paths.definition_raw / f"{DEFINITION_BATCH}.zip",
        paths.ohlcv_raw / "condition.json",
        paths.definition_raw / "condition.json",
    ]
    return [
        {
            "path": str(path.relative_to(paths.root)),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in candidates
    ]


def _output_files(paths: ProjectPaths) -> list[dict[str, Any]]:
    files: list[Path] = []
    for product in PRODUCTS:
        files.extend(sorted(paths.product_output(product).glob("year=*/part-*.parquet")))
    files.extend(
        [
            paths.instrument_output() / "instrument_master.parquet",
            paths.schedule_output() / "roll_schedule.parquet",
            paths.schedule_output() / "roll_schedule.csv",
        ]
    )
    return [
        {
            "path": str(path.relative_to(paths.root)),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in files
    ]


def _git_version(root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip()
        )
        return {"git_commit": commit, "git_worktree_dirty": dirty}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"git_commit": None, "repository_state": "not_a_git_repository"}


def build_manifest(
    paths: ProjectPaths,
    intervals: dict[str, list[RollInterval]],
    validation: dict[str, Any],
) -> dict[str, Any]:
    ohlcv_conditions = _condition_summary(
        paths.ohlcv_raw / "condition.json", SOURCE_START, SOURCE_END_EXCLUSIVE
    )
    definition_conditions = _condition_summary(
        paths.definition_raw / "condition.json", SOURCE_START, SOURCE_END_EXCLUSIVE
    )
    module_path = Path(__file__).resolve()
    return {
        "dataset": DATASET_NAME,
        "methodology": METHODOLOGY,
        "algorithm_version": ALGORITHM_VERSION,
        "build_timestamp_utc": datetime.now(UTC).isoformat(),
        "adjusted": False,
        "price_encoding": {"storage": "int64", "scale": PRICE_SCALE},
        "source_batches": {
            "ohlcv_1m": OHLCV_BATCH,
            "definition": DEFINITION_BATCH,
        },
        "source_files": _source_files(paths),
        "session_convention": {
            "timezone": "America/New_York",
            "normal_open": "18:00 on preceding calendar date",
            "normal_close": "17:00 on session date",
            "maintenance_break": "17:00-18:00 ET",
            "mapping_effective_rule": "mapping d0 becomes effective at the open of session d0",
            "mapping_end": "exclusive",
            "holiday_policy": "do not synthesize missing or early-close bars",
        },
        "counts": {
            "mapping_intervals": {product: len(intervals[product]) for product in PRODUCTS},
            "mapping_intervals_total": sum(len(intervals[p]) for p in PRODUCTS),
            "transitions": EXPECTED_TRANSITIONS,
            "transitions_total": sum(EXPECTED_TRANSITIONS.values()),
        },
        "output_schema": [
            {"name": field.name, "type": str(field.type), "nullable": field.nullable}
            for field in OUTPUT_SCHEMA
        ],
        "products": validation["products"],
        "condition_reports": {
            "ohlcv_1m": ohlcv_conditions,
            "definition": definition_conditions,
        },
        "source_integrity": validation.get("source_truth", {}),
        "validation": {"passed": validation["passed"], "failures": validation["failures"]},
        "output_files": _output_files(paths),
        "code_version": {
            **_git_version(paths.root),
            "builder": str(module_path.relative_to(paths.root)),
            "builder_sha256": _sha256(module_path),
            "pyproject_sha256": _sha256(paths.root / "pyproject.toml"),
            "python": sys.version.split()[0],
            "databento": db.__version__,
            "numpy": np.__version__,
            "pyarrow": pa.__version__,
        },
    }


def _report_markdown(
    paths: ProjectPaths,
    intervals: dict[str, list[RollInterval]],
    manifest: dict[str, Any],
) -> str:
    lines = [
        f"# Quality report: `{DATASET_NAME}`",
        "",
        "## Result",
        "",
        "**PASS.** The published Phase 1 data is a source-identical, volume-led, unadjusted continuous series.",
        "",
        "## Methodology and session convention",
        "",
        f"Databento `v.0` mappings select the active outright contract. `{METHODOLOGY}` applies a mapping "
        "dated `D` at 18:00 America/New_York on the preceding calendar day, the open of the Globex "
        "session labeled `D`. The normal close is 17:00 ET and 17:00–18:00 ET is treated as the "
        "maintenance break. DST is timezone-aware. Mapping `d1` is exclusive.",
        "",
        "OHLC prices remain Databento signed int64 fixed-point values at scale `1e-9`; volume and prices "
        "are copied unchanged. No rows are aggregated, filled, interpolated, or adjusted.",
        "",
        "## Source provenance",
        "",
        f"- OHLCV batch: `{OHLCV_BATCH}` (`GLBX.MDP3`, `ohlcv-1m`)",
        f"- Definition batch: `{DEFINITION_BATCH}` (`GLBX.MDP3`, `definition`)",
        f"- Roll map: `{paths.roll_map.relative_to(paths.root)}`",
        "- Full filenames, byte sizes, and SHA-256 checksums are in the dataset manifest.",
        "",
        "## Counts and coverage",
        "",
        "| Product | Mapping intervals | Rolls | Rows | First timestamp UTC | Last timestamp UTC | First contract | Last contract |",
        "| --- | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for product in PRODUCTS:
        data = manifest["products"][product]
        lines.append(
            f"| {product} | {len(intervals[product]):,} | {EXPECTED_TRANSITIONS[product]:,} | "
            f"{data['rows']:,} | {data['coverage_start']} | {data['coverage_end']} | "
            f"`{intervals[product][0].raw_symbol}` | `{intervals[product][-1].raw_symbol}` |"
        )
    lines.extend(["", "### Rows by product and year", ""])
    years = sorted({int(y) for p in PRODUCTS for y in manifest["products"][p]["year_rows"]})
    lines.extend(
        [
            "| Year | ES | NQ | GC |",
            "| ---: | ---: | ---: | ---: |",
            *[
                "| " + str(year) + " | " + " | ".join(
                    f"{manifest['products'][product]['year_rows'].get(str(year), 0):,}"
                    for product in PRODUCTS
                ) + " |"
                for year in years
            ],
        ]
    )
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "| Product | Duplicates | Ordering failures | Mapping failures | Session failures | "
            "OHLC failures | Roll markers | Gaps >1m | Within-session gaps >1m | Break bars |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for product in PRODUCTS:
        data = manifest["products"][product]
        lines.append(
            f"| {product} | {data['duplicate_timestamps']:,} | {data['ordering_failures']:,} | "
            f"{data['mapping_failures']:,} | {data['session_date_failures']:,} | "
            f"{data['ohlc_failures']:,} | {data['is_roll_rows']:,} | "
            f"{data['timestamp_gaps_over_one_minute']:,} | "
            f"{data['within_session_gaps_over_one_minute']:,} | {data['maintenance_break_bars']:,} |"
        )
    lines.extend(
        [
            "",
            "Output counts and a canonical record digest were compared with a fresh streaming selection "
            "from the source DBN. Therefore all reported timestamp gaps are inherited from published source "
            "bars; the transformation introduced no unexplained gaps or artificial rows. Weekends, exchange "
            "closures, and the daily maintenance break are not classified as missing data.",
            "",
            "Within-session gaps are source-observed intervals without a published bar, not rows lost by this "
            "pipeline. The validator found zero unexplained transformation gaps because the selected-source "
            "counts and record digests match the outputs exactly.",
            "",
            "Bars timestamped during the configured 17:00–18:00 ET maintenance window were retained and "
            "reported above, as required. They occur in the source (notably in older history, when venue hours "
            "differed) and were not silently discarded.",
            "",
            "## Source conditions",
            "",
        ]
    )
    for label, key in (("OHLCV", "ohlcv_1m"), ("Definition", "definition")):
        condition = manifest["condition_reports"][key]
        lines.append(
            f"- {label}: {condition['available']:,} available dates, {condition['degraded']:,} degraded "
            f"dates, and {condition['no_delivered_file_no_published_records']:,} requested calendar dates "
            "without a delivered file because no records were published."
        )
    degraded = manifest["condition_reports"]["definition"]["degraded_dates"]
    lines.extend(
        [
            "",
            "The 32 degraded dates were retained and are explicitly carried in the manifest:",
            "",
            ", ".join(f"`{value}`" for value in degraded),
            "",
            "## Roll schedule",
            "",
            "| Product | Session date | Effective UTC | Old | New |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in _schedule_rows(paths, intervals):
        lines.append(
            f"| {row['product']} | {row['effective_session_date']} | "
            f"{row['effective_timestamp_utc'].isoformat()} | `{row['old_raw_symbol']}` | "
            f"`{row['new_raw_symbol']}` |"
        )
    lines.extend(
        [
            "",
            "## Known limitations",
            "",
            "- The session calendar uses the documented recurring Globex boundary rule; it does not invent "
            "holiday or early-close bars.",
            "- Volume-ranked rolls are Databento mappings and are not claimed to reproduce TradingView exactly.",
            "- Prices are real selected-contract prices and therefore jump at contract rolls.",
            "- Degraded source dates remain present and must be considered by downstream research.",
            "",
            "## Reproduce",
            "",
            "```bash",
            "./scripts/bootstrap",
            "./scripts/build-continuous-phase1",
            "./scripts/validate-continuous-phase1",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _safe_remove(path: Path, root: Path) -> None:
    resolved = path.resolve()
    curated = (root / "data/curated").resolve()
    if resolved == curated or curated not in resolved.parents:
        raise Phase1Error(f"refusing unsafe removal: {resolved}")
    if resolved.is_dir():
        shutil.rmtree(resolved)
    elif resolved.exists():
        resolved.unlink()


def _prepare_build(paths: ProjectPaths, *, force: bool) -> None:
    outputs = [
        paths.instrument_output(),
        paths.schedule_output(),
        *(paths.product_output(product) for product in PRODUCTS),
    ]
    completed = paths.manifest.exists()
    existing = [path for path in outputs if path.exists()]
    if (completed or existing) and not force:
        raise Phase1Error(
            "a completed or partial Phase 1 build already exists; pass --force to replace only its known outputs"
        )
    if force:
        if paths.temp_root.exists():
            _safe_remove(paths.temp_root, paths.root)
    elif paths.temp_root.exists():
        raise Phase1Error(f"stale temporary build exists: {paths.temp_root}; inspect it or rerun with --force")
    paths.temp_root.mkdir(parents=True)


def _publish(paths: ProjectPaths) -> None:
    moves = [
        (paths.instrument_output(temporary=True), paths.instrument_output()),
        (paths.schedule_output(temporary=True), paths.schedule_output()),
        *(
            (paths.product_output(product, temporary=True), paths.product_output(product))
            for product in PRODUCTS
        ),
    ]
    backup_root = paths.root / "data/curated" / f".{DATASET_NAME}.backup"
    if backup_root.exists():
        _safe_remove(backup_root, paths.root)
    backed_up: list[tuple[Path, Path]] = []
    published: list[Path] = []
    curated_root = paths.root / "data/curated"
    try:
        for source, destination in moves:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                backup = backup_root / destination.relative_to(curated_root)
                backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(destination, backup)
                backed_up.append((backup, destination))
            os.replace(source, destination)
            published.append(destination)
    except Exception:
        for destination in reversed(published):
            if destination.exists():
                _safe_remove(destination, paths.root)
        for backup, destination in reversed(backed_up):
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(backup, destination)
        raise
    finally:
        if backup_root.exists():
            shutil.rmtree(backup_root)
    shutil.rmtree(paths.temp_root)


def build(paths: ProjectPaths, *, force: bool, chunk_size: int) -> dict[str, Any]:
    _ensure_sources(paths)
    _prepare_build(paths, force=force)
    calendar = SessionCalendar.build(SOURCE_START, SOURCE_END_EXCLUSIVE)
    try:
        mappings = load_roll_intervals(paths, calendar)
        intervals = resolve_instrument_master(paths, mappings)
        _write_reference_outputs(paths, intervals, temporary=True)
        stitch_series(paths, intervals, calendar, chunk_size=chunk_size)
        validate_outputs(
            paths,
            intervals,
            calendar,
            temporary=True,
            chunk_size=chunk_size,
            compare_source=True,
        )
        _publish(paths)
        validation = validate_outputs(
            paths,
            intervals,
            calendar,
            temporary=False,
            chunk_size=chunk_size,
            compare_source=True,
        )
        manifest = build_manifest(paths, intervals, validation)
        _atomic_text(paths.manifest, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        _atomic_text(paths.quality_report, _report_markdown(paths, intervals, manifest))
        return manifest
    except Exception:
        # Validated public outputs are never left behind before _publish. Preserve a failed
        # temporary build for diagnosis; --force removes it explicitly on the next run.
        raise


def validate(paths: ProjectPaths, *, chunk_size: int) -> dict[str, Any]:
    _ensure_sources(paths)
    calendar = SessionCalendar.build(SOURCE_START, SOURCE_END_EXCLUSIVE)
    intervals = resolve_instrument_master(paths, load_roll_intervals(paths, calendar))
    result = validate_outputs(
        paths,
        intervals,
        calendar,
        temporary=False,
        chunk_size=chunk_size,
        compare_source=True,
    )
    if paths.manifest.exists():
        recorded = json.loads(paths.manifest.read_text(encoding="utf-8"))
        actual = _output_files(paths)
        if recorded.get("output_files") != actual:
            raise Phase1Error("published output checksums differ from the dataset manifest")
    else:
        raise Phase1Error(f"dataset manifest does not exist: {paths.manifest}")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "validate"))
    parser.add_argument("--project-root", type=Path, help="Publication project root; otherwise use configured storage")
    parser.add_argument("--chunk-size", type=int, default=1_000_000)
    parser.add_argument("--force", action="store_true", help="replace only known Phase 1 outputs")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        paths = ProjectPaths.from_root(resolve_publication_root(arguments.project_root))
        if arguments.command == "build":
            manifest = build(paths, force=arguments.force, chunk_size=arguments.chunk_size)
            counts = ", ".join(
                f"{product}={manifest['products'][product]['rows']:,}" for product in PRODUCTS
            )
            print(f"Phase 1 build passed validation ({counts})")
        else:
            result = validate(paths, chunk_size=arguments.chunk_size)
            counts = ", ".join(
                f"{product}={result['products'][product]['rows']:,}" for product in PRODUCTS
            )
            print(f"Phase 1 validation passed ({counts})")
        return 0
    except (Phase1Error, PathConfigurationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
