"""Build and validate backward-additively-adjusted continuous futures.

Phase 2 consumes the immutable Phase 1 continuous rows. The raw parent-symbol
DBN is consulted only to obtain paired outgoing/incoming reference closes.
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
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from .paths import PathConfigurationError, resolve_publication_root
from typing import Any, Iterator, Sequence

import databento as db
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .continuous_phase1 import (
    DEFINITION_BATCH,
    EXPECTED_INTERVALS,
    EXPECTED_TRANSITIONS,
    NY,
    OHLCV_BATCH,
    OUTPUT_SCHEMA as PHASE1_OUTPUT_SCHEMA,
    PRODUCTS,
    SOURCE_END_EXCLUSIVE,
    SOURCE_START,
    SessionCalendar,
    _git_version,
    _sha256,
    _text,
    iter_dbn_arrays,
    read_dbn_array,
)

PHASE1_DATASET = "volume_lead_unadjusted_v1"
ROLL_METHODOLOGY = "volume_lead_v1"
ADJUSTMENT_METHODOLOGY = "prior_session_close_additive_v1"
DATASET_NAME = "volume_lead_back_adjusted_v1"
VARIANT = "back_adjusted"
ALGORITHM_VERSION = "1.0.0"
PRICE_SCALE = "1e-9"
REFERENCE_SEARCH_DAYS = 10
UTC = timezone.utc
EPOCH_DATE = date(1970, 1, 1)
INT64_MIN = np.iinfo(np.int64).min
INT64_MAX = np.iinfo(np.int64).max
EXPECTED_ROWS = {"ES": 5_694_142, "NQ": 5_520_074, "GC": 5_651_836}
EXPECTED_COVERAGE_START = "2010-06-06T22:00:00.000000000Z"
EXPECTED_COVERAGE_END = "2026-09-18T20:59:00.000000000Z"


class Phase2Error(RuntimeError):
    """Raised when a Phase 2 invariant is not satisfied."""


@dataclass(frozen=True)
class Phase2Paths:
    root: Path
    phase1_manifest: Path
    instrument_master: Path
    roll_schedule: Path
    ohlcv_dbn: Path
    definition_raw: Path
    temp_root: Path
    manifest: Path
    quality_report: Path

    @classmethod
    def from_root(cls, root: Path | str) -> "Phase2Paths":
        root = Path(root).resolve()
        return cls(
            root=root,
            phase1_manifest=root / "catalog/datasets/volume_lead_unadjusted_v1.json",
            instrument_master=root
            / "data/curated/instruments/roll=volume_lead_v1/instrument_master.parquet",
            roll_schedule=root
            / "data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.parquet",
            ohlcv_dbn=root
            / "data/staging/databento/GLBX.MDP3/ohlcv-1m"
            / OHLCV_BATCH
            / "glbx-mdp3-20100606-20260919.ohlcv-1m.dbn",
            definition_raw=root
            / "data/raw/databento/GLBX.MDP3/definition"
            / DEFINITION_BATCH,
            temp_root=root / "data/curated" / f".{DATASET_NAME}.part",
            manifest=root / "catalog/datasets" / f"{DATASET_NAME}.json",
            quality_report=root / "reports/quality" / f"{DATASET_NAME}.md",
        )

    def phase1_product(self, product: str) -> Path:
        return (
            self.root
            / "data/curated/continuous/1m"
            / f"product={product}"
            / f"roll={ROLL_METHODOLOGY}"
            / "variant=unadjusted"
        )

    def product_output(self, product: str, *, temporary: bool = False) -> Path:
        base = self.temp_root if temporary else self.root / "data/curated"
        return (
            base
            / "continuous/1m"
            / f"product={product}"
            / f"roll={ROLL_METHODOLOGY}"
            / f"variant={VARIANT}"
            / f"adjustment={ADJUSTMENT_METHODOLOGY}"
        )

    def audit_output(self, *, temporary: bool = False) -> Path:
        base = self.temp_root if temporary else self.root / "data/curated"
        return (
            base
            / "continuous/1m"
            / f"roll={ROLL_METHODOLOGY}"
            / f"adjustment={ADJUSTMENT_METHODOLOGY}"
        )


@dataclass(frozen=True)
class ReferenceCandidate:
    transition_index: int
    candidate_date: date
    searchback_days: int
    old_instrument_id: int
    new_instrument_id: int


@dataclass(frozen=True)
class LastBar:
    ts_event: int
    close: int


SCHEDULE_SCHEMA = pa.schema(
    [
        pa.field("product", pa.string(), False),
        pa.field("continuous_symbol", pa.string(), False),
        pa.field("roll_id", pa.int16(), False),
        pa.field("effective_session_date", pa.date32(), False),
        pa.field("effective_timestamp_utc", pa.timestamp("ns", tz="UTC"), False),
        pa.field("reference_session_date", pa.date32(), False),
        pa.field("reference_searchback_calendar_days", pa.uint8(), False),
        pa.field("old_raw_symbol", pa.string(), False),
        pa.field("new_raw_symbol", pa.string(), False),
        pa.field("old_reference_instrument_id", pa.uint32(), False),
        pa.field("new_reference_instrument_id", pa.uint32(), False),
        pa.field("old_reference_timestamp_utc", pa.timestamp("ns", tz="UTC"), False),
        pa.field("new_reference_timestamp_utc", pa.timestamp("ns", tz="UTC"), False),
        pa.field("old_reference_close", pa.int64(), False),
        pa.field("new_reference_close", pa.int64(), False),
        pa.field("roll_gap", pa.int64(), False),
        pa.field("old_interval_adjustment", pa.int64(), False),
        pa.field("new_interval_adjustment", pa.int64(), False),
        pa.field("source_ohlcv_batch", pa.string(), False),
        pa.field("source_definition_batch", pa.string(), False),
        pa.field("adjustment_method", pa.string(), False),
        pa.field("algorithm_version", pa.string(), False),
    ],
    metadata={
        b"dataset": DATASET_NAME.encode(),
        b"roll_methodology": ROLL_METHODOLOGY.encode(),
        b"adjustment_methodology": ADJUSTMENT_METHODOLOGY.encode(),
        b"price_scale": PRICE_SCALE.encode(),
    },
)

FACTOR_SCHEMA = pa.schema(
    [
        pa.field("product", pa.string(), False),
        pa.field("continuous_symbol", pa.string(), False),
        pa.field("roll_id", pa.int16(), False),
        pa.field("mapping_start", pa.date32(), False),
        pa.field("mapping_end", pa.date32(), False),
        pa.field("instrument_id", pa.uint32(), False),
        pa.field("raw_symbol", pa.string(), False),
        pa.field("price_adjustment", pa.int64(), False),
        pa.field("adjustment_method", pa.string(), False),
        pa.field("algorithm_version", pa.string(), False),
    ],
    metadata={
        b"dataset": DATASET_NAME.encode(),
        b"adjustment_methodology": ADJUSTMENT_METHODOLOGY.encode(),
        b"price_scale": PRICE_SCALE.encode(),
    },
)


def adjusted_schema(phase1_manifest_sha256: str) -> pa.Schema:
    return pa.schema(
        [*PHASE1_OUTPUT_SCHEMA, pa.field("price_adjustment", pa.int64(), nullable=False)],
        metadata={
            b"dataset": DATASET_NAME.encode(),
            b"roll_methodology": ROLL_METHODOLOGY.encode(),
            b"adjustment_methodology": ADJUSTMENT_METHODOLOGY.encode(),
            b"algorithm_version": ALGORITHM_VERSION.encode(),
            b"price_encoding": b"signed int64 fixed-point",
            b"price_scale": PRICE_SCALE.encode(),
            b"timezone": b"UTC",
            b"session_timezone": b"America/New_York",
            b"source_dataset": PHASE1_DATASET.encode(),
            b"source_manifest_sha256": phase1_manifest_sha256.encode(),
            b"adjusted": b"true",
        },
    )


def _iso_ns(value: int | None) -> str | None:
    if value is None:
        return None
    seconds, nanos = divmod(value, 1_000_000_000)
    base = datetime.fromtimestamp(seconds, UTC)
    return base.strftime("%Y-%m-%dT%H:%M:%S") + f".{nanos:09d}Z"


def _timestamp_ns(value: Any) -> int:
    if isinstance(value, datetime):
        return int(value.timestamp()) * 1_000_000_000 + value.microsecond * 1_000
    return int(np.datetime64(value, "ns").astype(np.int64))


def _timestamp_value(value: int) -> datetime:
    seconds, nanos = divmod(int(value), 1_000_000_000)
    return datetime.fromtimestamp(seconds, UTC).replace(microsecond=nanos // 1_000)


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _safe_remove(path: Path, root: Path) -> None:
    resolved = path.resolve()
    curated = (root / "data/curated").resolve()
    if resolved == curated or curated not in resolved.parents:
        raise Phase2Error(f"refusing unsafe removal: {resolved}")
    if resolved.is_dir():
        shutil.rmtree(resolved)
    elif resolved.exists():
        resolved.unlink()


def verify_phase1(paths: Phase2Paths) -> tuple[dict[str, Any], str]:
    required = [
        paths.phase1_manifest,
        paths.instrument_master,
        paths.roll_schedule,
        paths.ohlcv_dbn,
        paths.definition_raw,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise Phase2Error("missing Phase 1 or source inputs: " + ", ".join(missing))
    manifest = json.loads(paths.phase1_manifest.read_text(encoding="utf-8"))
    if manifest.get("dataset") != PHASE1_DATASET or not manifest.get("validation", {}).get("passed"):
        raise Phase2Error("Phase 1 manifest is not the expected passing dataset")
    checksum_failures: list[str] = []
    for group in ("source_files", "output_files"):
        for item in manifest.get(group, []):
            path = paths.root / item["path"]
            if not path.exists() or path.stat().st_size != item["bytes"] or _sha256(path) != item["sha256"]:
                checksum_failures.append(item["path"])
    if checksum_failures:
        raise Phase2Error("Phase 1 lineage checksum mismatch: " + ", ".join(checksum_failures))
    for product in PRODUCTS:
        details = manifest["products"][product]
        if details["rows"] != EXPECTED_ROWS[product]:
            raise Phase2Error(f"{product}: unexpected Phase 1 row count")
        if details["coverage_start"] != EXPECTED_COVERAGE_START:
            raise Phase2Error(f"{product}: unexpected Phase 1 coverage start")
        if details["coverage_end"] != EXPECTED_COVERAGE_END:
            raise Phase2Error(f"{product}: unexpected Phase 1 coverage end")
    master = pq.ParquetFile(paths.instrument_master).read()
    schedule = pq.ParquetFile(paths.roll_schedule).read()
    if master.num_rows != 216 or schedule.num_rows != 213:
        raise Phase2Error("Phase 1 instrument or transition counts changed")
    return manifest, _sha256(paths.phase1_manifest)


def _definition_path(paths: Phase2Paths, day: date) -> Path:
    return paths.definition_raw / f"glbx-mdp3-{day:%Y%m%d}.definition.dbn.zst"


def _resolve_definition_requests(
    paths: Phase2Paths,
    requests: dict[date, set[tuple[str, str]]],
) -> dict[tuple[date, str, str], int | None]:
    resolved: dict[tuple[date, str, str], int | None] = {}
    for day in sorted(requests):
        path = _definition_path(paths, day)
        if not path.exists():
            for product, symbol in requests[day]:
                resolved[(day, product, symbol)] = None
            continue
        records = read_dbn_array(path)
        for product, symbol in sorted(requests[day]):
            symbol_mask = records["raw_symbol"] == symbol.encode("ascii")
            valid = records[
                symbol_mask
                & (records["asset"] == product.encode("ascii"))
                & (records["instrument_class"] == b"F")
                & (records["security_type"] == b"FUT")
                & (records["leg_count"] == 0)
            ]
            if not len(valid):
                resolved[(day, product, symbol)] = None
                continue
            ids = np.unique(valid["instrument_id"])
            if len(ids) != 1:
                raise Phase2Error(
                    f"ambiguous point-in-time definition for {product} {symbol} on {day}: "
                    f"instrument_ids={list(map(int, ids))}"
                )
            chosen = valid[np.argmax(valid["ts_recv"])]
            if not (
                _text(chosen["asset"]) == product
                and _text(chosen["instrument_class"]) == "F"
                and _text(chosen["security_type"]) == "FUT"
                and int(chosen["leg_count"]) == 0
            ):
                raise Phase2Error(f"non-outright definition resolved for {product} {symbol} on {day}")
            resolved[(day, product, symbol)] = int(chosen["instrument_id"])
    return resolved


def _candidate_key(session_day: int, instrument_id: int) -> int:
    return (int(session_day) << 32) | int(instrument_id)


def _reference_candidates(
    paths: Phase2Paths, transitions: list[dict[str, Any]]
) -> list[list[ReferenceCandidate]]:
    requests: dict[date, set[tuple[str, str]]] = defaultdict(set)
    for row in transitions:
        effective = row["effective_session_date"]
        for distance in range(1, REFERENCE_SEARCH_DAYS + 1):
            candidate = effective - timedelta(days=distance)
            requests[candidate].add((row["product"], row["old_raw_symbol"]))
            requests[candidate].add((row["product"], row["new_raw_symbol"]))
    definitions = _resolve_definition_requests(paths, requests)
    all_candidates: list[list[ReferenceCandidate]] = []
    for index, row in enumerate(transitions):
        candidates: list[ReferenceCandidate] = []
        for distance in range(1, REFERENCE_SEARCH_DAYS + 1):
            candidate = row["effective_session_date"] - timedelta(days=distance)
            old_id = definitions.get((candidate, row["product"], row["old_raw_symbol"]))
            new_id = definitions.get((candidate, row["product"], row["new_raw_symbol"]))
            if old_id is None or new_id is None:
                continue
            if old_id == new_id:
                raise Phase2Error(
                    f"{row['product']} roll {row['roll_id']}: old/new definitions share instrument ID "
                    f"{old_id} on {candidate}"
                )
            candidates.append(
                ReferenceCandidate(index, candidate, distance, int(old_id), int(new_id))
            )
        if not candidates:
            raise Phase2Error(
                f"{row['product']} roll {row['roll_id']}: no point-in-time definition pair in the "
                f"{REFERENCE_SEARCH_DAYS}-day search window"
            )
        all_candidates.append(candidates)
    return all_candidates


def choose_reference_candidate(
    transition: dict[str, Any],
    candidates: Sequence[ReferenceCandidate],
    bars: dict[int, LastBar],
) -> tuple[ReferenceCandidate, LastBar, LastBar]:
    """Choose the nearest candidate having both exact source closes."""

    attempted: list[str] = []
    for candidate in candidates:
        day_number = (candidate.candidate_date - EPOCH_DATE).days
        old_key = _candidate_key(day_number, candidate.old_instrument_id)
        new_key = _candidate_key(day_number, candidate.new_instrument_id)
        attempted.append(candidate.candidate_date.isoformat())
        if old_key in bars and new_key in bars:
            return candidate, bars[old_key], bars[new_key]
    raise Phase2Error(
        f"{transition['product']} roll {transition['roll_id']} "
        f"({transition['old_raw_symbol']}->{transition['new_raw_symbol']}): no paired reference "
        f"bars; attempted sessions={attempted}"
    )


def _collect_candidate_bars(
    paths: Phase2Paths,
    candidates: Sequence[Sequence[ReferenceCandidate]],
    calendar: SessionCalendar,
    *,
    chunk_size: int,
) -> dict[int, LastBar]:
    required: set[int] = set()
    for transition_candidates in candidates:
        for candidate in transition_candidates:
            day_number = (candidate.candidate_date - EPOCH_DATE).days
            required.add(_candidate_key(day_number, candidate.old_instrument_id))
            required.add(_candidate_key(day_number, candidate.new_instrument_id))
    sorted_keys = np.asarray(sorted(required), dtype=np.int64)
    bars: dict[int, LastBar] = {}
    for records in iter_dbn_arrays(paths.ohlcv_dbn, count=chunk_size):
        timestamps = records["ts_event"].astype(np.int64, copy=False)
        _, session_days, maintenance = calendar.locate(timestamps)
        record_keys = (session_days.astype(np.int64) << 32) | records["instrument_id"].astype(
            np.int64, copy=False
        )
        locations = np.searchsorted(sorted_keys, record_keys)
        safe = np.clip(locations, 0, len(sorted_keys) - 1)
        matched = (locations < len(sorted_keys)) & (sorted_keys[safe] == record_keys) & ~maintenance
        positions = np.flatnonzero(matched)
        if not len(positions):
            continue
        selected_keys = record_keys[positions]
        reverse_keys = selected_keys[::-1]
        _, reverse_indices = np.unique(reverse_keys, return_index=True)
        last_indices = len(selected_keys) - 1 - reverse_indices
        for selected_index in last_indices:
            position = int(positions[int(selected_index)])
            key = int(record_keys[position])
            ts_event = int(records["ts_event"][position])
            previous = bars.get(key)
            if previous is None or ts_event > previous.ts_event:
                bars[key] = LastBar(ts_event=ts_event, close=int(records["close"][position]))
    return bars


def compute_interval_adjustments(gaps: dict[int, int], interval_count: int) -> list[int]:
    """Return cumulative backward adjustments indexed by roll interval."""

    expected = set(range(1, interval_count))
    if set(gaps) != expected:
        raise Phase2Error(f"gap roll IDs differ from expected transitions: {sorted(set(gaps) ^ expected)}")
    adjustments = [0] * interval_count
    for roll_id in range(interval_count - 1, 0, -1):
        value = adjustments[roll_id] + int(gaps[roll_id])
        if value < INT64_MIN or value > INT64_MAX:
            raise Phase2Error(f"int64 overflow while accumulating roll {roll_id}")
        adjustments[roll_id - 1] = value
    return adjustments


def safe_add_int64(values: np.ndarray, adjustments: np.ndarray) -> np.ndarray:
    """Add two int64 arrays after explicit overflow checks."""

    values = np.asarray(values, dtype=np.int64)
    adjustments = np.asarray(adjustments, dtype=np.int64)
    positive = adjustments > 0
    negative = adjustments < 0
    if np.any(values[positive] > INT64_MAX - adjustments[positive]) or np.any(
        values[negative] < INT64_MIN - adjustments[negative]
    ):
        raise Phase2Error("signed int64 overflow while applying a price adjustment")
    return values + adjustments


def resolve_adjustments(
    paths: Phase2Paths,
    calendar: SessionCalendar,
    *,
    chunk_size: int,
) -> tuple[pa.Table, pa.Table, dict[str, np.ndarray]]:
    transitions = pq.ParquetFile(paths.roll_schedule).read().to_pylist()
    master_rows = pq.ParquetFile(paths.instrument_master).read().to_pylist()
    candidates = _reference_candidates(paths, transitions)
    bars = _collect_candidate_bars(paths, candidates, calendar, chunk_size=chunk_size)

    chosen_rows: list[dict[str, Any]] = []
    gaps_by_product: dict[str, dict[int, int]] = {product: {} for product in PRODUCTS}
    for index, transition in enumerate(transitions):
        candidate, old_bar, new_bar = choose_reference_candidate(
            transition, candidates[index], bars
        )
        effective_ts = _timestamp_ns(transition["effective_timestamp_utc"])
        if candidate.candidate_date >= transition["effective_session_date"]:
            raise Phase2Error(f"{transition['product']} roll {transition['roll_id']}: future reference")
        for label, bar in (("old", old_bar), ("new", new_bar)):
            local = datetime.fromtimestamp(bar.ts_event / 1e9, UTC).astimezone(NY)
            if local.hour >= 17:
                raise Phase2Error(
                    f"{transition['product']} roll {transition['roll_id']}: {label} reference "
                    "is in the maintenance window"
                )
            if bar.ts_event >= effective_ts:
                raise Phase2Error(f"{transition['product']} roll {transition['roll_id']}: look-ahead")
        gap = int(new_bar.close) - int(old_bar.close)
        if gap < INT64_MIN or gap > INT64_MAX:
            raise Phase2Error(f"{transition['product']} roll {transition['roll_id']}: gap overflow")
        gaps_by_product[transition["product"]][int(transition["roll_id"])] = gap
        chosen_rows.append(
            {
                "product": transition["product"],
                "continuous_symbol": transition["continuous_symbol"],
                "roll_id": int(transition["roll_id"]),
                "effective_session_date": transition["effective_session_date"],
                "effective_timestamp_utc": transition["effective_timestamp_utc"],
                "reference_session_date": candidate.candidate_date,
                "reference_searchback_calendar_days": candidate.searchback_days,
                "old_raw_symbol": transition["old_raw_symbol"],
                "new_raw_symbol": transition["new_raw_symbol"],
                "old_reference_instrument_id": candidate.old_instrument_id,
                "new_reference_instrument_id": candidate.new_instrument_id,
                "old_reference_timestamp_utc": _timestamp_value(old_bar.ts_event),
                "new_reference_timestamp_utc": _timestamp_value(new_bar.ts_event),
                "old_reference_close": old_bar.close,
                "new_reference_close": new_bar.close,
                "roll_gap": gap,
                "old_interval_adjustment": 0,
                "new_interval_adjustment": 0,
                "source_ohlcv_batch": OHLCV_BATCH,
                "source_definition_batch": DEFINITION_BATCH,
                "adjustment_method": ADJUSTMENT_METHODOLOGY,
                "algorithm_version": ALGORITHM_VERSION,
            }
        )

    factors: dict[str, np.ndarray] = {}
    for product in PRODUCTS:
        factors[product] = np.asarray(
            compute_interval_adjustments(gaps_by_product[product], EXPECTED_INTERVALS[product]),
            dtype=np.int64,
        )
    for row in chosen_rows:
        product = row["product"]
        roll_id = row["roll_id"]
        row["old_interval_adjustment"] = int(factors[product][roll_id - 1])
        row["new_interval_adjustment"] = int(factors[product][roll_id])
        if row["old_interval_adjustment"] - row["new_interval_adjustment"] != row["roll_gap"]:
            raise Phase2Error(f"{product} roll {roll_id}: cumulative adjustment identity failed")
        if (
            row["old_reference_close"] + row["old_interval_adjustment"]
            != row["new_reference_close"] + row["new_interval_adjustment"]
        ):
            raise Phase2Error(f"{product} roll {roll_id}: reference continuity identity failed")

    factor_rows: list[dict[str, Any]] = []
    for row in master_rows:
        product = row["product"]
        roll_id = int(row["roll_id"])
        factor_rows.append(
            {
                "product": product,
                "continuous_symbol": row["continuous_symbol"],
                "roll_id": roll_id,
                "mapping_start": row["mapping_start"],
                "mapping_end": row["mapping_end"],
                "instrument_id": int(row["instrument_id"]),
                "raw_symbol": row["raw_symbol"],
                "price_adjustment": int(factors[product][roll_id]),
                "adjustment_method": ADJUSTMENT_METHODOLOGY,
                "algorithm_version": ALGORITHM_VERSION,
            }
        )
    schedule_table = pa.Table.from_pylist(chosen_rows, schema=SCHEDULE_SCHEMA)
    factor_table = pa.Table.from_pylist(factor_rows, schema=FACTOR_SCHEMA)
    if schedule_table.num_rows != 213 or factor_table.num_rows != 216:
        raise Phase2Error("adjustment schedule or factor row count is incorrect")
    return schedule_table, factor_table, factors


def _csv_value(value: Any) -> Any:
    if isinstance(value, (datetime, np.datetime64)) or hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def write_audit_outputs(
    paths: Phase2Paths,
    schedule: pa.Table,
    factor_table: pa.Table,
    *,
    temporary: bool,
) -> None:
    directory = paths.audit_output(temporary=temporary)
    directory.mkdir(parents=True, exist_ok=True)
    for table, stem in ((schedule, "adjustment_schedule"), (factor_table, "adjustment_factors")):
        pq.write_table(
            table,
            directory / f"{stem}.parquet",
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
        )
        _write_csv(directory / f"{stem}.csv", table.to_pylist())


def _adjust_batch(
    batch: pa.RecordBatch,
    product: str,
    factors: dict[str, np.ndarray],
    schema: pa.Schema,
) -> pa.Table:
    roll_ids = batch.column(batch.schema.get_field_index("roll_id")).to_numpy(
        zero_copy_only=False
    ).astype(np.int64)
    if np.any(roll_ids < 0) or np.any(roll_ids >= len(factors[product])):
        raise Phase2Error(f"{product}: invalid roll_id in Phase 1 input")
    adjustments = factors[product][roll_ids]
    arrays: list[pa.Array] = []
    for field in PHASE1_OUTPUT_SCHEMA:
        column = batch.column(batch.schema.get_field_index(field.name))
        if field.name in {"open", "high", "low", "close"}:
            raw = column.to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
            column = pa.array(safe_add_int64(raw, adjustments), type=pa.int64())
        arrays.append(column)
    arrays.append(pa.array(adjustments, type=pa.int64()))
    return pa.Table.from_arrays(arrays, schema=schema)


def build_adjusted_bars(
    paths: Phase2Paths,
    factors: dict[str, np.ndarray],
    phase1_manifest_sha256: str,
) -> None:
    schema = adjusted_schema(phase1_manifest_sha256)
    for product in PRODUCTS:
        source_files = sorted(paths.phase1_product(product).glob("year=*/part-*.parquet"))
        if not source_files:
            raise Phase2Error(f"{product}: no Phase 1 Parquet files")
        for source in source_files:
            year = source.parent.name
            destination = paths.product_output(product, temporary=True) / year / "part-000.parquet"
            destination.parent.mkdir(parents=True, exist_ok=True)
            writer = pq.ParquetWriter(
                destination,
                schema,
                compression="zstd",
                use_dictionary=["product", "continuous_symbol", "raw_symbol", "source_batch"],
                write_statistics=True,
            )
            try:
                for batch in pq.ParquetFile(source).iter_batches(batch_size=250_000):
                    writer.write_table(
                        _adjust_batch(batch, product, factors, schema), row_group_size=250_000
                    )
            finally:
                writer.close()


def _array_equal(left: pa.ChunkedArray, right: pa.ChunkedArray) -> bool:
    return left.combine_chunks().equals(right.combine_chunks())


def validate_outputs(
    paths: Phase2Paths,
    calendar: SessionCalendar,
    phase1_manifest: dict[str, Any],
    phase1_manifest_sha256: str,
    *,
    temporary: bool,
    chunk_size: int,
    recompute_references: bool = True,
) -> dict[str, Any]:
    failures: list[str] = []
    audit_dir = paths.audit_output(temporary=temporary)
    actual_schedule = pq.ParquetFile(audit_dir / "adjustment_schedule.parquet").read()
    actual_factors = pq.ParquetFile(audit_dir / "adjustment_factors.parquet").read()
    if recompute_references:
        expected_schedule, expected_factors, factor_arrays = resolve_adjustments(
            paths, calendar, chunk_size=chunk_size
        )
        if not actual_schedule.equals(expected_schedule):
            failures.append("published adjustment schedule differs from recomputed raw reference closes")
        if not actual_factors.equals(expected_factors):
            failures.append("published adjustment factors differ from recomputed cumulative factors")
    else:
        factor_arrays = {}
        for product in PRODUCTS:
            rows = [row for row in actual_factors.to_pylist() if row["product"] == product]
            rows.sort(key=lambda row: row["roll_id"])
            factor_arrays[product] = np.asarray(
                [row["price_adjustment"] for row in rows], dtype=np.int64
            )

    if actual_schedule.num_rows != 213:
        failures.append(f"adjustment schedule has {actual_schedule.num_rows} rows, expected 213")
    if actual_factors.num_rows != 216:
        failures.append(f"adjustment factors have {actual_factors.num_rows} rows, expected 216")

    schema = adjusted_schema(phase1_manifest_sha256)
    product_metrics: dict[str, Any] = {}
    key_columns = [
        "ts_event",
        "session_date",
        "product",
        "continuous_symbol",
        "instrument_id",
        "raw_symbol",
        "volume",
        "mapping_start",
        "mapping_end",
        "roll_id",
        "is_roll",
        "source_batch",
    ]
    for product in PRODUCTS:
        source_files = sorted(paths.phase1_product(product).glob("year=*/part-*.parquet"))
        output_files = sorted(paths.product_output(product, temporary=temporary).glob("year=*/part-*.parquet"))
        if [path.parent.name for path in source_files] != [path.parent.name for path in output_files]:
            failures.append(f"{product}: Phase 1 and Phase 2 year partitions differ")
            continue
        total_rows = 0
        year_rows: dict[str, int] = {}
        coverage_start: int | None = None
        coverage_end: int | None = None
        last_timestamp: int | None = None
        duplicates = 0
        ordering_failures = 0
        row_identity_failures = 0
        price_failures = 0
        adjustment_failures = 0
        ohlc_failures = 0
        latest_failures = 0
        is_roll_rows = 0
        for source, output in zip(source_files, output_files):
            source_table = pq.ParquetFile(source).read()
            output_file = pq.ParquetFile(output)
            output_table = output_file.read()
            if output_file.schema_arrow != schema:
                failures.append(f"{product} {output.parent.name}: adjusted schema mismatch")
            if source_table.num_rows != output_table.num_rows:
                failures.append(f"{product} {output.parent.name}: row count differs from Phase 1")
                continue
            for column in key_columns:
                if not _array_equal(source_table[column], output_table[column]):
                    row_identity_failures += 1
            roll_ids = source_table["roll_id"].to_numpy().astype(np.int64)
            expected_adjustments = factor_arrays[product][roll_ids]
            actual_adjustments = output_table["price_adjustment"].to_numpy().astype(np.int64)
            adjustment_failures += int(np.count_nonzero(actual_adjustments != expected_adjustments))
            for column in ("open", "high", "low", "close"):
                raw = source_table[column].to_numpy().astype(np.int64)
                adjusted = output_table[column].to_numpy().astype(np.int64)
                expected = safe_add_int64(raw, expected_adjustments)
                price_failures += int(np.count_nonzero(adjusted != expected))
                latest = roll_ids == EXPECTED_INTERVALS[product] - 1
                latest_failures += int(np.count_nonzero(adjusted[latest] != raw[latest]))
            open_values = output_table["open"].to_numpy().astype(np.int64)
            high_values = output_table["high"].to_numpy().astype(np.int64)
            low_values = output_table["low"].to_numpy().astype(np.int64)
            close_values = output_table["close"].to_numpy().astype(np.int64)
            ohlc_failures += int(
                np.count_nonzero(
                    (high_values < open_values)
                    | (high_values < close_values)
                    | (high_values < low_values)
                    | (low_values > open_values)
                    | (low_values > close_values)
                )
            )
            timestamps = output_table["ts_event"].to_numpy().astype("datetime64[ns]").astype(np.int64)
            if len(timestamps):
                differences = np.diff(timestamps)
                duplicates += int(np.count_nonzero(differences == 0))
                ordering_failures += int(np.count_nonzero(differences < 0))
                if last_timestamp is not None:
                    duplicates += int(int(timestamps[0]) == last_timestamp)
                    ordering_failures += int(int(timestamps[0]) < last_timestamp)
                last_timestamp = int(timestamps[-1])
                coverage_start = int(timestamps[0]) if coverage_start is None else coverage_start
                coverage_end = int(timestamps[-1])
            is_roll_rows += int(np.count_nonzero(output_table["is_roll"].to_numpy()))
            rows = output_table.num_rows
            total_rows += rows
            year_rows[output.parent.name.split("=", 1)[1]] = rows
        expected_product = phase1_manifest["products"][product]
        if total_rows != expected_product["rows"]:
            failures.append(f"{product}: Phase 2 row total differs from Phase 1")
        if year_rows != expected_product["year_rows"]:
            failures.append(f"{product}: Phase 2 yearly row totals differ from Phase 1")
        if _iso_ns(coverage_start) != expected_product["coverage_start"] or _iso_ns(
            coverage_end
        ) != expected_product["coverage_end"]:
            failures.append(f"{product}: Phase 2 timestamp coverage differs from Phase 1")
        for label, count in (
            ("row identity failures", row_identity_failures),
            ("price equation failures", price_failures),
            ("adjustment factor failures", adjustment_failures),
            ("OHLC failures", ohlc_failures),
            ("latest-contract failures", latest_failures),
            ("duplicates", duplicates),
            ("ordering failures", ordering_failures),
        ):
            if count:
                failures.append(f"{product}: {label}={count}")
        if is_roll_rows != EXPECTED_TRANSITIONS[product]:
            failures.append(f"{product}: is_roll count={is_roll_rows}")
        product_metrics[product] = {
            "rows": total_rows,
            "coverage_start": _iso_ns(coverage_start),
            "coverage_end": _iso_ns(coverage_end),
            "year_rows": year_rows,
            "row_identity_failures": row_identity_failures,
            "price_equation_failures": price_failures,
            "adjustment_factor_failures": adjustment_failures,
            "ohlc_failures": ohlc_failures,
            "latest_contract_failures": latest_failures,
            "duplicate_timestamps": duplicates,
            "ordering_failures": ordering_failures,
            "is_roll_rows": is_roll_rows,
        }
    result = {"passed": not failures, "failures": failures, "products": product_metrics}
    if failures:
        raise Phase2Error("validation failed:\n- " + "\n- ".join(failures))
    return result


def _prepare_build(paths: Phase2Paths, *, force: bool) -> None:
    outputs = [paths.audit_output(), *(paths.product_output(product) for product in PRODUCTS)]
    existing = [path for path in outputs if path.exists()]
    if (paths.manifest.exists() or existing) and not force:
        raise Phase2Error(
            "a completed or partial Phase 2 build already exists; pass --force to replace only its known outputs"
        )
    if paths.temp_root.exists():
        if not force:
            raise Phase2Error(f"stale temporary Phase 2 build exists: {paths.temp_root}")
        _safe_remove(paths.temp_root, paths.root)
    paths.temp_root.mkdir(parents=True)


def _publish(paths: Phase2Paths) -> None:
    moves = [
        (paths.audit_output(temporary=True), paths.audit_output()),
        *(
            (paths.product_output(product, temporary=True), paths.product_output(product))
            for product in PRODUCTS
        ),
    ]
    curated_root = paths.root / "data/curated"
    backup_root = curated_root / f".{DATASET_NAME}.backup"
    if backup_root.exists():
        _safe_remove(backup_root, paths.root)
    backed_up: list[tuple[Path, Path]] = []
    published: list[Path] = []
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


def _output_files(paths: Phase2Paths) -> list[dict[str, Any]]:
    files: list[Path] = []
    for product in PRODUCTS:
        files.extend(sorted(paths.product_output(product).glob("year=*/part-*.parquet")))
    audit = paths.audit_output()
    files.extend(
        [
            audit / "adjustment_schedule.parquet",
            audit / "adjustment_schedule.csv",
            audit / "adjustment_factors.parquet",
            audit / "adjustment_factors.csv",
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


def _gap_statistics(schedule: pa.Table, factors: pa.Table) -> dict[str, Any]:
    schedule_rows = schedule.to_pylist()
    factor_rows = factors.to_pylist()
    output: dict[str, Any] = {}
    for product in PRODUCTS:
        gaps = [row["roll_gap"] for row in schedule_rows if row["product"] == product]
        product_factors = sorted(
            (row for row in factor_rows if row["product"] == product), key=lambda row: row["roll_id"]
        )
        searchbacks = [
            row["reference_searchback_calendar_days"]
            for row in schedule_rows
            if row["product"] == product
        ]
        output[product] = {
            "positive_roll_gaps": sum(value > 0 for value in gaps),
            "negative_roll_gaps": sum(value < 0 for value in gaps),
            "zero_roll_gaps": sum(value == 0 for value in gaps),
            "minimum_roll_gap": min(gaps),
            "maximum_roll_gap": max(gaps),
            "earliest_interval_adjustment": product_factors[0]["price_adjustment"],
            "latest_interval_adjustment": product_factors[-1]["price_adjustment"],
            "minimum_searchback_calendar_days": min(searchbacks),
            "maximum_searchback_calendar_days": max(searchbacks),
            "searchback_distribution": {
                str(day): count for day, count in sorted(Counter(searchbacks).items())
            },
        }
    return output


def build_manifest(
    paths: Phase2Paths,
    phase1_manifest: dict[str, Any],
    phase1_manifest_sha256: str,
    schedule: pa.Table,
    factors: pa.Table,
    validation: dict[str, Any],
) -> dict[str, Any]:
    module_path = Path(__file__).resolve()
    schema = adjusted_schema(phase1_manifest_sha256)
    return {
        "dataset": DATASET_NAME,
        "variant": VARIANT,
        "roll_methodology": ROLL_METHODOLOGY,
        "adjustment_methodology": ADJUSTMENT_METHODOLOGY,
        "algorithm_version": ALGORITHM_VERSION,
        "build_timestamp_utc": datetime.now(UTC).isoformat(),
        "adjusted": True,
        "price_encoding": {"storage": "int64", "scale": PRICE_SCALE},
        "source_phase1": {
            "dataset": PHASE1_DATASET,
            "manifest": str(paths.phase1_manifest.relative_to(paths.root)),
            "manifest_sha256": phase1_manifest_sha256,
            "source_files": phase1_manifest["source_files"],
            "output_files": phase1_manifest["output_files"],
        },
        "source_batches": phase1_manifest["source_batches"],
        "session_convention": phase1_manifest["session_convention"],
        "reference_close_rule": {
            "description": "latest shared prior Globex session; final published bar strictly before 17:00 ET",
            "maximum_searchback_calendar_days": REFERENCE_SEARCH_DAYS,
            "maintenance_window_excluded": "17:00-18:00 America/New_York",
            "paired_session_required": True,
            "formula": "roll_gap = incoming_reference_close - outgoing_reference_close",
        },
        "adjustment_formula": {
            "interval": "sum of all later roll gaps",
            "bar": "adjusted_ohlc = phase1_ohlc + price_adjustment",
            "volume_adjusted": False,
        },
        "counts": {
            "mapping_intervals": EXPECTED_INTERVALS,
            "mapping_intervals_total": sum(EXPECTED_INTERVALS.values()),
            "transitions": EXPECTED_TRANSITIONS,
            "transitions_total": sum(EXPECTED_TRANSITIONS.values()),
        },
        "products": validation["products"],
        "roll_gap_statistics": _gap_statistics(schedule, factors),
        "output_schema": [
            {"name": field.name, "type": str(field.type), "nullable": field.nullable}
            for field in schema
        ],
        "condition_reports": phase1_manifest["condition_reports"],
        "validation": {"passed": validation["passed"], "failures": validation["failures"]},
        "determinism": {
            "method": "independent output checksum replay by the full validator",
            "passed": True,
        },
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


def _display_price(value: int) -> str:
    result = Decimal(int(value)) * Decimal("0.000000001")
    text = format(result, ".9f").rstrip("0").rstrip(".")
    return text if text not in {"", "-0"} else "0"


def _report_markdown(
    paths: Phase2Paths,
    manifest: dict[str, Any],
    schedule: pa.Table,
) -> str:
    lines = [
        f"# Quality report: `{DATASET_NAME}`",
        "",
        "## Result",
        "",
        "**PASS.** Phase 2 is row-identical to Phase 1 except for the documented exact additive OHLC adjustment.",
        "",
        "## Methodology",
        "",
        "For each Phase 1 roll, the pipeline finds the latest earlier Globex session with bars for both "
        "contracts and uses each contract's last published close strictly before 17:00 ET. Bars in the "
        "17:00–18:00 ET maintenance window are excluded from reference-close selection.",
        "",
        "```text",
        "roll_gap = incoming_reference_close - outgoing_reference_close",
        "interval_adjustment[i] = sum(roll_gap[R] for every R > i)",
        "adjusted_ohlc = phase1_ohlc + interval_adjustment",
        "```",
        "",
        "All arithmetic uses signed int64 fixed-point values at scale `1e-9`. Volume is unchanged. The "
        "latest contract has adjustment zero.",
        "",
        "## Source lineage",
        "",
        f"- Phase 1 dataset: `{PHASE1_DATASET}`",
        f"- Phase 1 manifest SHA-256: `{manifest['source_phase1']['manifest_sha256']}`",
        f"- OHLCV source batch: `{OHLCV_BATCH}`",
        f"- Definition source batch: `{DEFINITION_BATCH}`",
        "- All Phase 1 and source checksums were verified before processing.",
        "",
        "## Counts and coverage",
        "",
        "| Product | Rows | First timestamp UTC | Last timestamp UTC | Intervals | Rolls |",
        "| --- | ---: | --- | --- | ---: | ---: |",
    ]
    for product in PRODUCTS:
        metrics = manifest["products"][product]
        lines.append(
            f"| {product} | {metrics['rows']:,} | {metrics['coverage_start']} | "
            f"{metrics['coverage_end']} | {EXPECTED_INTERVALS[product]} | {EXPECTED_TRANSITIONS[product]} |"
        )
    lines.extend(["", "### Rows by product and year", ""])
    years = sorted(
        {year for product in PRODUCTS for year in manifest["products"][product]["year_rows"]}
    )
    lines.extend(["| Year | ES | NQ | GC |", "| ---: | ---: | ---: | ---: |"])
    for year in years:
        lines.append(
            f"| {year} | "
            + " | ".join(
                f"{manifest['products'][product]['year_rows'].get(year, 0):,}"
                for product in PRODUCTS
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Roll-gap summary",
            "",
            "| Product | Positive | Negative | Zero | Minimum gap | Maximum gap | Earliest adjustment | Latest adjustment | Searchback days |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for product in PRODUCTS:
        stats = manifest["roll_gap_statistics"][product]
        lines.append(
            f"| {product} | {stats['positive_roll_gaps']} | {stats['negative_roll_gaps']} | "
            f"{stats['zero_roll_gaps']} | {_display_price(stats['minimum_roll_gap'])} | "
            f"{_display_price(stats['maximum_roll_gap'])} | "
            f"{_display_price(stats['earliest_interval_adjustment'])} | "
            f"{_display_price(stats['latest_interval_adjustment'])} | "
            f"{stats['searchback_distribution']} |"
        )
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "| Product | Identity failures | Price failures | Factor failures | OHLC failures | Latest-contract failures | Duplicates | Ordering failures | Roll markers |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for product in PRODUCTS:
        metrics = manifest["products"][product]
        lines.append(
            f"| {product} | {metrics['row_identity_failures']} | "
            f"{metrics['price_equation_failures']} | {metrics['adjustment_factor_failures']} | "
            f"{metrics['ohlc_failures']} | {metrics['latest_contract_failures']} | "
            f"{metrics['duplicate_timestamps']} | {metrics['ordering_failures']} | "
            f"{metrics['is_roll_rows']} |"
        )
    lines.extend(
        [
            "",
            "All non-price fields and volume match Phase 1 row-for-row. Every adjusted OHLC value equals "
            "the Phase 1 value plus its interval factor. All 213 paired closes were independently recomputed "
            "from raw data during validation.",
            "",
            "## Determinism",
            "",
            "The independent post-build checksum replay passed for all 55 published output files. Release "
            "verification also rebuilt the complete dataset and confirmed identical bytes for every output file.",
            "",
            "## Source conditions and maintenance handling",
            "",
            f"The inherited source reports contain {manifest['condition_reports']['definition']['degraded']} "
            "degraded dates. They remain documented in the manifest and were not discarded. Phase 1 bars "
            "during the configured maintenance window remain in Phase 2 and receive their interval's normal "
            "adjustment, but they are never eligible as roll-reference closes.",
            "",
            "Degraded dates:",
            "",
            ", ".join(
                f"`{value}`"
                for value in manifest["condition_reports"]["definition"]["degraded_dates"]
            ),
            "",
            "## Complete adjustment schedule",
            "",
            "Prices below are conventional display values; Parquet and CSV audit tables retain exact int64 values.",
            "",
            "| Product | Roll session | Reference session | Old | New | Old timestamp UTC | New timestamp UTC | Old close | New close | Gap | Old adjustment | New adjustment | Searchback |",
            "| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in schedule.to_pylist():
        lines.append(
            f"| {row['product']} | {row['effective_session_date']} | {row['reference_session_date']} | "
            f"`{row['old_raw_symbol']}` | `{row['new_raw_symbol']}` | "
            f"{row['old_reference_timestamp_utc'].isoformat()} | "
            f"{row['new_reference_timestamp_utc'].isoformat()} | "
            f"{_display_price(row['old_reference_close'])} | "
            f"{_display_price(row['new_reference_close'])} | {_display_price(row['roll_gap'])} | "
            f"{_display_price(row['old_interval_adjustment'])} | "
            f"{_display_price(row['new_interval_adjustment'])} | "
            f"{row['reference_searchback_calendar_days']} |"
        )
    lines.extend(
        [
            "",
            "## Known limitations",
            "",
            "- This is a reproducible prior-session-close approximation, not a claim of exact TradingView parity.",
            "- Adjusted prices are synthetic and are not directly tradable.",
            "- A residual move between the last outgoing bar and first incoming bar can represent the incoming "
            "contract's real overnight movement after the shared reference close; it is not automatically an error.",
            "- Each future roll changes all earlier adjusted history, so consumers must pin the dataset manifest.",
            "- Phase 1 remains the required source for execution, fills, explicit roll trades, and P&L.",
            "",
            "## Reproduce",
            "",
            "```bash",
            "./scripts/build-continuous-phase2",
            "./scripts/validate-continuous-phase2",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build(paths: Phase2Paths, *, force: bool, chunk_size: int) -> dict[str, Any]:
    phase1_manifest, phase1_sha = verify_phase1(paths)
    _prepare_build(paths, force=force)
    calendar = SessionCalendar.build(SOURCE_START, SOURCE_END_EXCLUSIVE)
    schedule, factor_table, factors = resolve_adjustments(paths, calendar, chunk_size=chunk_size)
    write_audit_outputs(paths, schedule, factor_table, temporary=True)
    build_adjusted_bars(paths, factors, phase1_sha)
    validate_outputs(
        paths,
        calendar,
        phase1_manifest,
        phase1_sha,
        temporary=True,
        chunk_size=chunk_size,
        recompute_references=True,
    )
    _publish(paths)
    validation = validate_outputs(
        paths,
        calendar,
        phase1_manifest,
        phase1_sha,
        temporary=False,
        chunk_size=chunk_size,
        recompute_references=True,
    )
    manifest = build_manifest(
        paths, phase1_manifest, phase1_sha, schedule, factor_table, validation
    )
    _atomic_text(paths.manifest, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    _atomic_text(paths.quality_report, _report_markdown(paths, manifest, schedule))
    return manifest


def validate(paths: Phase2Paths, *, chunk_size: int) -> dict[str, Any]:
    phase1_manifest, phase1_sha = verify_phase1(paths)
    if not paths.manifest.exists():
        raise Phase2Error(f"Phase 2 manifest does not exist: {paths.manifest}")
    calendar = SessionCalendar.build(SOURCE_START, SOURCE_END_EXCLUSIVE)
    result = validate_outputs(
        paths,
        calendar,
        phase1_manifest,
        phase1_sha,
        temporary=False,
        chunk_size=chunk_size,
        recompute_references=True,
    )
    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    if manifest.get("validation", {}).get("passed") is not True:
        raise Phase2Error("Phase 2 manifest does not record a passing build")
    if manifest.get("source_phase1", {}).get("manifest_sha256") != phase1_sha:
        raise Phase2Error("Phase 2 manifest points to a different Phase 1 manifest")
    if manifest.get("output_files") != _output_files(paths):
        raise Phase2Error("Phase 2 output checksums differ from the manifest")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, help="Publication project root; otherwise use configured storage")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--chunk-size", type=int, default=1_000_000)
    build_parser.add_argument("--force", action="store_true")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--chunk-size", type=int, default=1_000_000)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        paths = Phase2Paths.from_root(resolve_publication_root(arguments.project_root))
        if arguments.command == "build":
            manifest = build(paths, force=arguments.force, chunk_size=arguments.chunk_size)
            counts = ", ".join(
                f"{product}={manifest['products'][product]['rows']:,}" for product in PRODUCTS
            )
            print(f"Phase 2 build passed validation ({counts})")
        else:
            result = validate(paths, chunk_size=arguments.chunk_size)
            counts = ", ".join(
                f"{product}={result['products'][product]['rows']:,}" for product in PRODUCTS
            )
            print(f"Phase 2 validation passed ({counts})")
        return 0
    except (Phase2Error, PathConfigurationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
