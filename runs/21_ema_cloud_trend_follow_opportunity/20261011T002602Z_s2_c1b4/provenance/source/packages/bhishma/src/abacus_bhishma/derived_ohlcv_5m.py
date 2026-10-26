"""Build the versioned DR/IDR five-minute OHLCV delivery.

This is a request-specific, immutable derivation of
``volume_lead_back_adjusted_v1``. It deliberately does not calculate DR/IDR
features or labels. Source OHLC values stay in Databento's exact int64 1e-9
fixed-point representation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from .paths import PathConfigurationError, resolve_publication_root
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo

import numpy as np
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from . import provenance as _provenance
from .provenance import git_version as _git_version, sha256_file as _sha256
from .publication_safety import check_absent, check_path, write_new_bytes

DATASET_ID = "tv_indicators__dridr_ohlcv_5m__v1"
FEATURE_SET = "dridr_ohlcv_5m"
FEATURE_SET_VERSION = "1.0.0"
ALGORITHM_VERSION = "1.0.0"
SOURCE_DATASET = "volume_lead_back_adjusted_v1"
SOURCE_ROLL = "volume_lead_v1"
SOURCE_VARIANT = "back_adjusted"
SOURCE_ADJUSTMENT = "prior_session_close_additive_v1"
PRODUCTS = ("ES", "GC", "NQ")
PRICE_SCALE = 1e-9
MINUTE_NS = 60_000_000_000
FIVE_MINUTES_NS = 5 * MINUTE_NS
HOUR_NS = 60 * MINUTE_NS
DAY_NS = 24 * HOUR_NS
UTC = timezone.utc
NY = ZoneInfo("America/New_York")
EPOCH_DATE = date(1970, 1, 1)
DEFAULT_REQUEST = Path(
    "requests/fulfilled/tv_indicators__dridr_ohlcv_5m__v1.yaml"
)
OHLCV_DOC = "https://databento.com/docs/schemas-and-data-formats/ohlcv"


class DeliveryError(RuntimeError):
    """Raised when the request or a delivery invariant is violated."""


@dataclass(frozen=True)
class DeliveryPaths:
    root: Path
    request_snapshot: Path
    source_manifest: Path
    instrument_master: Path
    roll_schedule: Path
    adjustment_schedule: Path
    adjustment_factors: Path
    output_root: Path
    temporary_output_root: Path
    manifest: Path
    quality_report: Path

    @classmethod
    def from_root(cls, root: Path | str) -> "DeliveryPaths":
        root = Path(root).resolve()
        source_audit = (
            root
            / "data/curated/continuous/1m/roll=volume_lead_v1"
            / "adjustment=prior_session_close_additive_v1"
        )
        return cls(
            root=root,
            request_snapshot=root / "requests/fulfilled" / f"{DATASET_ID}.yaml",
            source_manifest=root / "catalog/datasets" / f"{SOURCE_DATASET}.json",
            instrument_master=root
            / "data/curated/instruments/roll=volume_lead_v1/instrument_master.parquet",
            roll_schedule=root
            / "data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.parquet",
            adjustment_schedule=source_audit / "adjustment_schedule.parquet",
            adjustment_factors=source_audit / "adjustment_factors.parquet",
            output_root=root
            / "data/features/bars/5m"
            / f"feature_set={FEATURE_SET}"
            / f"version={FEATURE_SET_VERSION}",
            temporary_output_root=root / "data/features" / f".{DATASET_ID}.part",
            manifest=root / "catalog/datasets" / f"{DATASET_ID}.json",
            quality_report=root / "reports/quality" / f"{DATASET_ID}.md",
        )

    def source_partition(self, product: str, year: int) -> Path:
        return (
            self.root
            / "data/curated/continuous/1m"
            / f"product={product}"
            / f"roll={SOURCE_ROLL}"
            / f"variant={SOURCE_VARIANT}"
            / f"adjustment={SOURCE_ADJUSTMENT}"
            / f"year={year}"
            / "part-000.parquet"
        )

    @staticmethod
    def output_partition(base: Path, product: str, year: int) -> Path:
        return base / f"product={product}" / f"year={year}" / "part-000.parquet"


def output_schema(source_manifest_sha256: str, request_sha256: str) -> pa.Schema:
    return pa.schema(
        [
            pa.field("ts_event", pa.timestamp("ns", tz="UTC"), False),
            pa.field("session_date", pa.date32(), False),
            pa.field("product", pa.string(), False),
            pa.field("open", pa.int64(), False),
            pa.field("high", pa.int64(), False),
            pa.field("low", pa.int64(), False),
            pa.field("close", pa.int64(), False),
            pa.field("volume", pa.uint64(), False),
            pa.field("continuous_symbol", pa.string(), False),
            pa.field("raw_symbol", pa.string(), True),
            pa.field("instrument_id", pa.uint32(), True),
            pa.field("roll_id", pa.int16(), True),
            pa.field("contains_roll", pa.bool_(), False),
            pa.field("price_adjustment", pa.int64(), True),
            pa.field("first_raw_symbol", pa.string(), False),
            pa.field("last_raw_symbol", pa.string(), False),
            pa.field("source_bar_count", pa.uint8(), False),
            pa.field("is_partial_bar", pa.bool_(), False),
            pa.field("min_tick", pa.float64(), False),
            pa.field("is_mixed_contract_bar", pa.bool_(), False),
            pa.field("is_mixed_adjustment_bar", pa.bool_(), False),
        ],
        metadata={
            b"dataset_id": DATASET_ID.encode(),
            b"feature_set": FEATURE_SET.encode(),
            b"feature_set_version": FEATURE_SET_VERSION.encode(),
            b"algorithm_version": ALGORITHM_VERSION.encode(),
            b"source_dataset": SOURCE_DATASET.encode(),
            b"source_manifest_sha256": source_manifest_sha256.encode(),
            b"request_sha256": request_sha256.encode(),
            b"timeframe": b"5m",
            b"timestamp_label": b"bar_open",
            b"interval_semantics": b"[start,end)",
            b"timezone": b"UTC",
            b"session_timezone": b"America/New_York",
            b"price_encoding": b"signed int64 fixed-point",
            b"price_scale": b"1e-9",
            b"volume_units": b"contracts",
            b"min_tick_units": b"price units",
            b"adjusted": b"true",
        },
    )


def _load_yaml_with_ruby(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    ruby = shutil.which("ruby")
    if ruby is None:
        raise DeliveryError("Ruby is required to parse the YAML request on this host")
    program = (
        "require 'json'; require 'yaml'; "
        "d=YAML.safe_load(STDIN.read, aliases: false); STDOUT.write(JSON.generate(d))"
    )
    completed = subprocess.run(
        [ruby, "-e", program], input=raw, capture_output=True, check=False
    )
    if completed.returncode:
        raise DeliveryError(
            "failed to parse request YAML: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    parsed = json.loads(completed.stdout)
    if not isinstance(parsed, dict):
        raise DeliveryError("request YAML must have a mapping at its root")
    return parsed, raw


def _validate_request(request: dict[str, Any]) -> None:
    checks = {
        "request.id": (request.get("request", {}).get("id"), DATASET_ID),
        "base_data.dataset": (
            request.get("base_data", {}).get("dataset"),
            SOURCE_DATASET,
        ),
        "base_data.variant": (
            request.get("base_data", {}).get("variant"),
            SOURCE_VARIANT,
        ),
        "base_data.source_timeframe": (
            request.get("base_data", {}).get("source_timeframe"),
            "1m",
        ),
        "base_data.requested_timeframe": (
            request.get("base_data", {}).get("requested_timeframe"),
            "5m",
        ),
        "output.feature_set_name": (
            request.get("output", {}).get("feature_set_name"),
            FEATURE_SET,
        ),
        "output.feature_set_version": (
            request.get("output", {}).get("feature_set_version"),
            FEATURE_SET_VERSION,
        ),
        "output.format": (request.get("output", {}).get("format"), "parquet"),
        "output.compression": (
            request.get("output", {}).get("compression"),
            "zstd",
        ),
        "output.overwrite_existing_version": (
            request.get("output", {}).get("overwrite_existing_version"),
            False,
        ),
        "delivery.keep_inside_abacus_bhishma": (
            request.get("delivery", {}).get("keep_inside_abacus_bhishma"),
            True,
        ),
        "delivery.copy_into_requesting_repository": (
            request.get("delivery", {}).get("copy_into_requesting_repository"),
            False,
        ),
    }
    failures = [f"{key}: got {actual!r}, expected {expected!r}" for key, (actual, expected) in checks.items() if actual != expected]
    if tuple(request.get("base_data", {}).get("products", [])) != PRODUCTS:
        failures.append(f"base_data.products must be {list(PRODUCTS)!r}")
    if request.get("features") != []:
        failures.append("features must be empty for this delivery")
    labels = request.get("research_labels", {})
    if labels.get("requested") != [] or labels.get("allow_forward_looking_columns") is not False:
        failures.append("research labels and forward-looking columns must be disabled")
    aggregation = request.get("aggregation", {})
    aggregation_checks = {
        "timezone": "America/New_York",
        "anchor": "session_open",
        "timestamp_label": "bar_open",
        "interval_semantics": "[start, end)",
        "missing_minutes": "do_not_fill",
        "partial_bars": "keep_and_flag",
    }
    for key, expected in aggregation_checks.items():
        if aggregation.get(key) != expected:
            failures.append(f"aggregation.{key}: got {aggregation.get(key)!r}, expected {expected!r}")
    if failures:
        raise DeliveryError("unsupported or changed request contract:\n- " + "\n- ".join(failures))


def _date_bounds(request: dict[str, Any]) -> tuple[int, int, date, date]:
    date_range = request["base_data"]["date_range"]
    first = date.fromisoformat(date_range["start"])
    end = date.fromisoformat(date_range["end"])
    if date_range.get("end_is_exclusive") is not True:
        raise DeliveryError("the request end boundary must be exclusive")
    start_local = datetime.combine(first, time.min, NY)
    end_local = datetime.combine(end, time.min, NY)
    return (
        int(start_local.timestamp() * 1_000_000_000),
        int(end_local.timestamp() * 1_000_000_000),
        first,
        end,
    )


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _iso_ns(value: int | None) -> str | None:
    if value is None:
        return None
    seconds, nanos = divmod(int(value), 1_000_000_000)
    base = datetime.fromtimestamp(seconds, UTC)
    return base.strftime("%Y-%m-%dT%H:%M:%S") + f".{nanos:09d}Z"


def _timestamp_array(values: np.ndarray) -> pa.Array:
    return pa.array(values.astype(np.int64, copy=False), type=pa.timestamp("ns", tz="UTC"))


def _atomic_bytes(path: Path, content: bytes) -> None:
    write_new_bytes(path, content, Path(path.absolute().anchor), error=DeliveryError)


def _atomic_text(path: Path, content: str) -> None:
    _atomic_bytes(path, content.encode("utf-8"))


def _table_digest(table: pa.Table) -> str:
    sink = pa.BufferOutputStream()
    combined = table.combine_chunks()
    with pa.ipc.new_stream(sink, combined.schema) as writer:
        writer.write_table(combined)
    return hashlib.sha256(sink.getvalue().to_pybytes()).hexdigest()


def _local_clock(ts_ns: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return local epoch-day and minute-of-day using timezone-aware offsets."""

    hours = np.floor_divide(ts_ns, HOUR_NS)
    unique_hours, inverse = np.unique(hours, return_inverse=True)
    offsets = np.asarray(
        [
            int(
                datetime.fromtimestamp(int(hour) * 3600, UTC)
                .astimezone(NY)
                .utcoffset()
                .total_seconds()
                * 1_000_000_000
            )
            for hour in unique_hours
        ],
        dtype=np.int64,
    )
    local_ns = ts_ns + offsets[inverse]
    local_days = np.floor_divide(local_ns, DAY_NS).astype(np.int32)
    local_minutes = np.floor_divide(np.mod(local_ns, DAY_NS), MINUTE_NS).astype(np.int16)
    return local_days, local_minutes


def _group_change(values: np.ndarray, starts: np.ndarray) -> np.ndarray:
    changed = np.zeros(len(values), dtype=np.bool_)
    changed[1:] = values[1:] != values[:-1]
    changed[starts] = False
    return np.logical_or.reduceat(changed, starts)


def _tick_lookup(master: pa.Table) -> tuple[dict[tuple[str, int], int], dict[str, list[int]]]:
    lookup: dict[tuple[str, int], int] = {}
    ticks: dict[str, set[int]] = {product: set() for product in PRODUCTS}
    for row in master.select(["product", "roll_id", "min_price_increment"]).to_pylist():
        key = (row["product"], int(row["roll_id"]))
        value = int(row["min_price_increment"])
        if value <= 0:
            raise DeliveryError(f"non-positive minimum tick for {key}")
        if key in lookup and lookup[key] != value:
            raise DeliveryError(f"conflicting minimum tick for {key}")
        lookup[key] = value
        ticks[row["product"]].add(value)
    return lookup, {product: sorted(values) for product, values in ticks.items()}


def _source_file_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["path"]: item for item in manifest.get("output_files", [])}


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _verify_inputs(
    paths: DeliveryPaths,
    request: dict[str, Any],
) -> tuple[dict[str, Any], str, pa.Table, list[tuple[str, int, Path]], dict[str, Any]]:
    required = [
        paths.source_manifest,
        paths.instrument_master,
        paths.roll_schedule,
        paths.adjustment_schedule,
        paths.adjustment_factors,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise DeliveryError("missing required source artifacts: " + ", ".join(missing))
    manifest = json.loads(paths.source_manifest.read_text(encoding="utf-8"))
    if manifest.get("dataset") != SOURCE_DATASET or not manifest.get("validation", {}).get("passed"):
        raise DeliveryError("source manifest is not the expected validated Phase 2 dataset")
    source_manifest_hash = _sha256(paths.source_manifest)
    index = _source_file_index(manifest)
    _, _, first, end = _date_bounds(request)
    partitions: list[tuple[str, int, Path]] = []
    verified_files: list[dict[str, Any]] = []
    for product in PRODUCTS:
        for year in range(first.year, end.year + 1):
            path = paths.source_partition(product, year)
            if not path.is_file():
                continue
            relative = _relative(path, paths.root)
            item = index.get(relative)
            if item is None:
                raise DeliveryError(f"source partition is absent from Phase 2 manifest: {relative}")
            actual_hash = _sha256(path)
            if path.stat().st_size != item["bytes"] or actual_hash != item["sha256"]:
                raise DeliveryError(f"source partition checksum mismatch: {relative}")
            partitions.append((product, year, path))
            verified_files.append({**item, "verified_sha256": actual_hash})
    if not partitions:
        raise DeliveryError("no source partitions overlap the request")
    for audit_path in (
        paths.instrument_master,
        paths.roll_schedule,
        paths.adjustment_schedule,
        paths.adjustment_factors,
    ):
        relative = _relative(audit_path, paths.root)
        item = index.get(relative)
        if item is None:
            # The instrument master and roll schedule are inherited Phase 1 outputs;
            # Phase 2 records them in source_phase1 rather than output_files.
            inherited = {
                candidate["path"]: candidate
                for candidate in manifest.get("source_phase1", {}).get("output_files", [])
            }.get(relative)
            item = inherited
        actual_hash = _sha256(audit_path)
        if item is not None and (audit_path.stat().st_size != item["bytes"] or actual_hash != item["sha256"]):
            raise DeliveryError(f"audit artifact checksum mismatch: {relative}")
        verified_files.append(
            {
                "path": relative,
                "bytes": audit_path.stat().st_size,
                "sha256": actual_hash,
            }
        )
    master = pq.read_table(paths.instrument_master)
    audit = {
        "verified_files": verified_files,
        "source_manifest_sha256": source_manifest_hash,
    }
    return manifest, source_manifest_hash, master, partitions, audit


def _aggregate_table(
    source: pa.Table,
    product: str,
    year: int,
    tick_by_roll: dict[tuple[str, int], int],
    schema: pa.Schema,
    start_ns: int,
    end_ns: int,
) -> tuple[pa.Table, dict[str, Any]]:
    source = source.combine_chunks()
    ts_all = source["ts_event"].to_numpy(zero_copy_only=False).astype("datetime64[ns]").astype(np.int64)
    in_range = (ts_all >= start_ns) & (ts_all < end_ns)
    if not np.all(in_range):
        source = source.filter(pa.array(in_range)).combine_chunks()
    if source.num_rows == 0:
        return pa.Table.from_pylist([], schema=schema), {
            "product": product,
            "year": year,
            "source_rows": 0,
            "rows": 0,
        }

    ts = source["ts_event"].to_numpy(zero_copy_only=False).astype("datetime64[ns]").astype(np.int64)
    session_days = source["session_date"].to_numpy(zero_copy_only=False).astype("datetime64[D]").astype(np.int32)
    source_products = np.asarray(source["product"].to_numpy(zero_copy_only=False), dtype=object)
    continuous = np.asarray(source["continuous_symbol"].to_numpy(zero_copy_only=False), dtype=object)
    instruments = source["instrument_id"].to_numpy(zero_copy_only=False).astype(np.uint32)
    raw_symbols = np.asarray(source["raw_symbol"].to_numpy(zero_copy_only=False), dtype=object)
    opens = source["open"].to_numpy(zero_copy_only=False).astype(np.int64)
    highs = source["high"].to_numpy(zero_copy_only=False).astype(np.int64)
    lows = source["low"].to_numpy(zero_copy_only=False).astype(np.int64)
    closes = source["close"].to_numpy(zero_copy_only=False).astype(np.int64)
    volumes = source["volume"].to_numpy(zero_copy_only=False).astype(np.uint64)
    roll_ids = source["roll_id"].to_numpy(zero_copy_only=False).astype(np.int16)
    is_roll = source["is_roll"].to_numpy(zero_copy_only=False).astype(np.bool_)
    adjustments = source["price_adjustment"].to_numpy(zero_copy_only=False).astype(np.int64)

    if not np.all(source_products == product):
        raise DeliveryError(f"{product} {year}: source product column mismatch")
    if not np.all(continuous == f"{product}.v.0"):
        raise DeliveryError(f"{product} {year}: unexpected continuous symbol")
    deltas = np.diff(ts)
    duplicate_count = int(np.count_nonzero(deltas == 0))
    ordering_failures = int(np.count_nonzero(deltas <= 0))
    minute_alignment_failures = int(np.count_nonzero(np.mod(ts, MINUTE_NS)))
    ohlc_failures = int(
        np.count_nonzero(
            (lows > opens)
            | (lows > closes)
            | (highs < opens)
            | (highs < closes)
            | (lows > highs)
        )
    )
    if duplicate_count or ordering_failures or minute_alignment_failures or ohlc_failures:
        raise DeliveryError(
            f"{product} {year}: rejected invalid source rows: duplicates={duplicate_count}, "
            f"ordering={ordering_failures}, minute_alignment={minute_alignment_failures}, "
            f"ohlc={ohlc_failures}"
        )

    try:
        ticks = np.asarray([tick_by_roll[(product, int(value))] for value in roll_ids], dtype=np.int64)
    except KeyError as exc:
        raise DeliveryError(f"{product} {year}: roll is absent from instrument master: {exc}") from exc
    raw_tick_alignment_failures = 0
    for values in (opens, highs, lows, closes):
        raw_tick_alignment_failures += int(np.count_nonzero(np.mod(values - adjustments, ticks)))
    if raw_tick_alignment_failures:
        raise DeliveryError(
            f"{product} {year}: {raw_tick_alignment_failures} source prices fail raw tick alignment"
        )

    buckets = np.floor_divide(ts, FIVE_MINUTES_NS) * FIVE_MINUTES_NS
    starts = np.flatnonzero(np.r_[True, buckets[1:] != buckets[:-1]]).astype(np.int64)
    ends = np.r_[starts[1:], len(ts)].astype(np.int64)
    counts = (ends - starts).astype(np.uint8)
    if np.any(counts > 5):
        raise DeliveryError(f"{product} {year}: a bucket contains more than five unique minutes")

    instrument_min = np.minimum.reduceat(instruments, starts)
    instrument_max = np.maximum.reduceat(instruments, starts)
    raw_changed = _group_change(raw_symbols, starts)
    instrument_changed = instrument_min != instrument_max
    mixed_contract = raw_changed | instrument_changed
    adjustment_min = np.minimum.reduceat(adjustments, starts)
    adjustment_max = np.maximum.reduceat(adjustments, starts)
    mixed_adjustment = adjustment_min != adjustment_max
    roll_min = np.minimum.reduceat(roll_ids, starts)
    roll_max = np.maximum.reduceat(roll_ids, starts)
    mixed_roll = roll_min != roll_max
    tick_min = np.minimum.reduceat(ticks, starts)
    tick_max = np.maximum.reduceat(ticks, starts)
    mixed_tick = tick_min != tick_max
    session_min = np.minimum.reduceat(session_days, starts)
    session_max = np.maximum.reduceat(session_days, starts)
    if np.any(session_min != session_max):
        raise DeliveryError(f"{product} {year}: five-minute bucket crosses session_date")

    exact_five = (
        (counts == 5)
        & (ts[starts] == buckets[starts])
        & (ts[ends - 1] == buckets[starts] + 4 * MINUTE_NS)
    )
    partial = ~exact_five
    contains_roll = np.logical_or.reduceat(is_roll, starts)
    volume_sum = np.add.reduceat(volumes, starts, dtype=np.uint64)
    table = pa.Table.from_arrays(
        [
            _timestamp_array(buckets[starts]),
            pa.array(session_min, type=pa.date32()),
            pa.array(np.repeat(product, len(starts)), type=pa.string()),
            pa.array(opens[starts], type=pa.int64()),
            pa.array(np.maximum.reduceat(highs, starts), type=pa.int64()),
            pa.array(np.minimum.reduceat(lows, starts), type=pa.int64()),
            pa.array(closes[ends - 1], type=pa.int64()),
            pa.array(volume_sum, type=pa.uint64()),
            pa.array(continuous[starts], type=pa.string()),
            pa.array(raw_symbols[starts], type=pa.string(), mask=mixed_contract),
            pa.array(instruments[starts], type=pa.uint32(), mask=mixed_contract),
            pa.array(roll_ids[starts], type=pa.int16(), mask=mixed_roll),
            pa.array(contains_roll, type=pa.bool_()),
            pa.array(adjustments[starts], type=pa.int64(), mask=mixed_adjustment),
            pa.array(raw_symbols[starts], type=pa.string()),
            pa.array(raw_symbols[ends - 1], type=pa.string()),
            pa.array(counts, type=pa.uint8()),
            pa.array(partial, type=pa.bool_()),
            pa.array(tick_min.astype(np.float64) * PRICE_SCALE, type=pa.float64()),
            pa.array(mixed_contract, type=pa.bool_()),
            pa.array(mixed_adjustment, type=pa.bool_()),
        ],
        schema=schema,
    )

    within_session = (session_days[1:] == session_days[:-1]) & (deltas > MINUTE_NS)
    source_gap_events = int(np.count_nonzero(deltas > MINUTE_NS))
    within_session_gap_events = int(np.count_nonzero(within_session))
    unpublished_minutes = int(np.sum(np.floor_divide(deltas[within_session], MINUTE_NS) - 1))
    source_local_days, source_local_minutes = _local_clock(ts)
    output_local_days, output_local_minutes = _local_clock(buckets[starts])
    maintenance_source = (source_local_minutes >= 17 * 60) & (source_local_minutes < 18 * 60)
    maintenance_output = (output_local_minutes >= 17 * 60) & (output_local_minutes < 18 * 60)

    stats: dict[str, Any] = {
        "product": product,
        "year": year,
        "source_rows": int(len(ts)),
        "rows": int(table.num_rows),
        "source_coverage_start": _iso_ns(int(ts[0])),
        "source_coverage_end": _iso_ns(int(ts[-1])),
        "coverage_start": _iso_ns(int(buckets[starts][0])),
        "coverage_end": _iso_ns(int(buckets[starts][-1])),
        "session_dates": int(len(np.unique(session_days))),
        "duplicate_source_timestamps": duplicate_count,
        "invalid_source_rows": ohlc_failures + minute_alignment_failures + ordering_failures,
        "source_gap_events_over_one_minute": source_gap_events,
        "within_session_gap_events_over_one_minute": within_session_gap_events,
        "unpublished_source_minutes_within_session": unpublished_minutes,
        "complete_bars": int(np.count_nonzero(exact_five)),
        "partial_bars": int(np.count_nonzero(partial)),
        "mixed_contract_bars": int(np.count_nonzero(mixed_contract)),
        "mixed_adjustment_bars": int(np.count_nonzero(mixed_adjustment)),
        "roll_bars": int(np.count_nonzero(contains_roll)),
        "source_zero_volume_rows": int(np.count_nonzero(volumes == 0)),
        "zero_volume_bars": int(np.count_nonzero(volume_sum == 0)),
        "source_rows_in_nominal_maintenance_window": int(np.count_nonzero(maintenance_source)),
        "bars_in_nominal_maintenance_window": int(np.count_nonzero(maintenance_output)),
        "ny_five_minute_alignment_failures": int(np.count_nonzero(output_local_minutes % 5)),
        "raw_tick_alignment_failures": raw_tick_alignment_failures,
        "source_bar_count_sum": int(np.sum(counts, dtype=np.uint64)),
        "record_digest": _table_digest(table),
        "last_bar_complete": bool(not partial[-1]),
    }

    if year == 2024:
        boundary_checks: list[dict[str, Any]] = []
        targets = ((19, 30), (20, 30), (3, 0), (4, 0), (9, 30), (10, 25), (10, 30))
        jan_first = (date(2024, 1, 1) - EPOCH_DATE).days
        for hour, minute in targets:
            target = hour * 60 + minute
            matches = np.flatnonzero(
                (output_local_days >= jan_first)
                & (output_local_minutes == target)
                & exact_five
            )
            if len(matches):
                index = int(matches[0])
                boundary_checks.append(
                    {
                        "local_time": f"{hour:02d}:{minute:02d}",
                        "bar_open_utc": _iso_ns(int(buckets[starts][index])),
                        "first_source_open_utc": _iso_ns(int(ts[starts[index]])),
                        "last_source_open_utc": _iso_ns(int(ts[ends[index] - 1])),
                        "source_bar_count": int(counts[index]),
                    }
                )
        stats["boundary_spot_checks"] = boundary_checks

        dst_checks: list[dict[str, Any]] = []
        for label, start_day, stop_day in (
            ("spring_2024", date(2024, 3, 4), date(2024, 3, 18)),
            ("fall_2024", date(2024, 10, 28), date(2024, 11, 11)),
        ):
            low_day = (start_day - EPOCH_DATE).days
            high_day = (stop_day - EPOCH_DATE).days
            mask = (output_local_days >= low_day) & (output_local_days < high_day)
            dst_checks.append(
                {
                    "period": label,
                    "local_date_start": start_day.isoformat(),
                    "local_date_end_exclusive": stop_day.isoformat(),
                    "bars": int(np.count_nonzero(mask)),
                    "ny_alignment_failures": int(np.count_nonzero(output_local_minutes[mask] % 5)),
                }
            )
        stats["dst_spot_checks"] = dst_checks

        holiday_checks: list[dict[str, Any]] = []
        for session_day in (date(2024, 11, 28), date(2024, 11, 29)):
            day_number = (session_day - EPOCH_DATE).days
            mask = session_min == day_number
            holiday_checks.append(
                {
                    "session_date": session_day.isoformat(),
                    "bars": int(np.count_nonzero(mask)),
                    "partial_bars": int(np.count_nonzero(mask & partial)),
                    "first_bar_open_utc": _iso_ns(int(buckets[starts][np.flatnonzero(mask)[0]])) if np.any(mask) else None,
                    "last_bar_open_utc": _iso_ns(int(buckets[starts][np.flatnonzero(mask)[-1]])) if np.any(mask) else None,
                }
            )
        stats["holiday_early_close_spot_checks"] = holiday_checks

        roll_matches = np.flatnonzero(contains_roll)
        if len(roll_matches):
            index = int(roll_matches[0])
            stats["roll_spot_check"] = {
                "bar_open_utc": _iso_ns(int(buckets[starts][index])),
                "contains_roll": True,
                "first_raw_symbol": str(raw_symbols[starts[index]]),
                "last_raw_symbol": str(raw_symbols[ends[index] - 1]),
                "is_mixed_contract_bar": bool(mixed_contract[index]),
                "is_mixed_adjustment_bar": bool(mixed_adjustment[index]),
                "price_adjustment": None if mixed_adjustment[index] else int(adjustments[starts[index]]),
            }

    return table, stats


def _write_partition(table: pa.Table, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        path,
        compression="zstd",
        use_dictionary=[
            "product",
            "continuous_symbol",
            "raw_symbol",
            "first_raw_symbol",
            "last_raw_symbol",
        ],
        write_statistics=True,
        version="2.6",
        data_page_version="2.0",
        row_group_size=131_072,
    )


def _summarize_products(stats: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    sum_fields = (
        "source_rows",
        "rows",
        "session_dates",
        "duplicate_source_timestamps",
        "invalid_source_rows",
        "source_gap_events_over_one_minute",
        "within_session_gap_events_over_one_minute",
        "unpublished_source_minutes_within_session",
        "complete_bars",
        "partial_bars",
        "mixed_contract_bars",
        "mixed_adjustment_bars",
        "roll_bars",
        "source_zero_volume_rows",
        "zero_volume_bars",
        "source_rows_in_nominal_maintenance_window",
        "bars_in_nominal_maintenance_window",
        "ny_five_minute_alignment_failures",
        "raw_tick_alignment_failures",
        "source_bar_count_sum",
    )
    for product in PRODUCTS:
        rows = sorted((item for item in stats if item["product"] == product), key=lambda item: item["year"])
        nonempty = [item for item in rows if item.get("rows", 0)]
        if not nonempty:
            raise DeliveryError(f"{product}: no output rows")
        summary: dict[str, Any] = {field: sum(int(item.get(field, 0)) for item in rows) for field in sum_fields}
        summary.update(
            {
                "coverage_start": nonempty[0]["coverage_start"],
                "coverage_end": nonempty[-1]["coverage_end"],
                "source_coverage_start": nonempty[0]["source_coverage_start"],
                "source_coverage_end": nonempty[-1]["source_coverage_end"],
                "last_bar_complete": bool(nonempty[-1]["last_bar_complete"]),
                "years": {str(item["year"]): int(item.get("rows", 0)) for item in rows},
            }
        )
        for optional in (
            "boundary_spot_checks",
            "dst_spot_checks",
            "holiday_early_close_spot_checks",
            "roll_spot_check",
        ):
            candidates = [item[optional] for item in rows if optional in item]
            if candidates:
                summary[optional] = candidates[0]
        summaries[product] = summary
    return summaries


def _validate_replay(
    paths: DeliveryPaths,
    output_root: Path,
    partitions: Sequence[tuple[str, int, Path]],
    tick_by_roll: dict[tuple[str, int], int],
    schema: pa.Schema,
    start_ns: int,
    end_ns: int,
) -> dict[str, Any]:
    failures: list[str] = []
    replayed = 0
    prior_end: dict[str, int] = {}
    for product, year, source_path in partitions:
        output_path = paths.output_partition(output_root, product, year)
        if not output_path.is_file():
            failures.append(f"missing output partition: {output_path}")
            continue
        source = pq.read_table(source_path)
        expected, _ = _aggregate_table(
            source, product, year, tick_by_roll, schema, start_ns, end_ns
        )
        actual = pq.read_table(output_path).combine_chunks()
        if actual.schema != schema:
            failures.append(f"{product} {year}: schema mismatch")
        if _table_digest(actual) != _table_digest(expected):
            failures.append(f"{product} {year}: deterministic source replay mismatch")
        if actual.num_rows:
            ts = actual["ts_event"].to_numpy().astype("datetime64[ns]").astype(np.int64)
            if np.any(np.diff(ts) <= 0):
                failures.append(f"{product} {year}: timestamps are not strictly increasing")
            if product in prior_end and int(ts[0]) <= prior_end[product]:
                failures.append(f"{product} {year}: timestamp overlaps prior partition")
            prior_end[product] = int(ts[-1])
            source_count = actual["source_bar_count"].to_numpy().astype(np.uint64)
            if int(source_count.sum()) != source.num_rows:
                failures.append(f"{product} {year}: source row reconciliation failed")
            partial = actual["is_partial_bar"].to_numpy().astype(np.bool_)
            if not np.array_equal(partial, source_count != 5):
                failures.append(f"{product} {year}: partial-bar flag mismatch")
            opens = actual["open"].to_numpy().astype(np.int64)
            highs = actual["high"].to_numpy().astype(np.int64)
            lows = actual["low"].to_numpy().astype(np.int64)
            closes = actual["close"].to_numpy().astype(np.int64)
            if np.any((lows > opens) | (lows > closes) | (highs < opens) | (highs < closes)):
                failures.append(f"{product} {year}: invalid OHLC envelope")
        replayed += 1
    for product in PRODUCTS:
        product_files = sorted((output_root / f"product={product}").glob("year=*/part-*.parquet"))
        if product_files:
            last = pq.read_table(product_files[-1], columns=["is_partial_bar"])
            if last.num_rows and last["is_partial_bar"][-1].as_py():
                failures.append(f"{product}: unfinished final five-minute bar")
    return {
        "passed": not failures,
        "failures": failures,
        "partitions_replayed": replayed,
        "deterministic_rebuild": not failures,
        "phase2_lineage_verified": not failures,
        "no_synthetic_rows": not failures,
    }


def _schema_manifest(schema: pa.Schema) -> list[dict[str, Any]]:
    units = {
        "ts_event": "UTC inclusive five-minute bar open",
        "session_date": "exchange session label inherited from Phase 2",
        "open": "price; int64 fixed-point scale 1e-9",
        "high": "price; int64 fixed-point scale 1e-9",
        "low": "price; int64 fixed-point scale 1e-9",
        "close": "price; int64 fixed-point scale 1e-9",
        "volume": "contracts; exact sum of published source-minute volume",
        "price_adjustment": "price; int64 fixed-point scale 1e-9; null when mixed",
        "min_tick": "price units",
        "source_bar_count": "unique published one-minute source bars",
    }
    return [
        {
            "name": field.name,
            "type": str(field.type),
            "nullable": field.nullable,
            "units_or_meaning": units.get(field.name),
        }
        for field in schema
    ]


def _loader_example(paths: DeliveryPaths) -> str:
    return f'''from pathlib import Path
import pyarrow.dataset as ds

root = Path("{paths.output_root}")
bars = ds.dataset(root, format="parquet", partitioning="hive")

# Load one product and a bounded period. Partition filters prune files.
table = bars.to_table(
    filter=(ds.field("product") == "ES") & (ds.field("year") == 2024),
    columns=[
        "ts_event", "session_date", "product", "open", "high", "low",
        "close", "volume", "raw_symbol", "price_adjustment",
        "source_bar_count", "is_partial_bar", "contains_roll",
    ],
)

# OHLC and price_adjustment are exact int64 fixed-point values at scale 1e-9.
# Convert only at the consumer boundary when floats are required:
close_float = table["close"].to_numpy() * 1e-9
print(table.num_rows, table["ts_event"][0], close_float[0])'''


def _report_markdown(manifest: dict[str, Any], stats: list[dict[str, Any]], paths: DeliveryPaths) -> str:
    lines = [
        f"# {DATASET_ID} quality report",
        "",
        "## Result",
        "",
        "**PASS** — the requested immutable five-minute OHLCV delivery was built and independently replayed from every pinned Phase 2 source partition.",
        "",
        "No DR/IDR features, labels, outcomes, statistics, or Pine payloads are present.",
        "",
        "## Coverage",
        "",
        "| Product | 5m rows | Source 1m rows | Session dates | First 5m open UTC | Last 5m open UTC | Last source minute UTC | Partial | Roll |",
        "|---|---:|---:|---:|---|---|---|---:|---:|",
    ]
    for product in PRODUCTS:
        item = manifest["products"][product]
        lines.append(
            f"| {product} | {item['rows']:,} | {item['source_rows']:,} | {item['session_dates']:,} | "
            f"{item['coverage_start']} | {item['coverage_end']} | {item['source_coverage_end']} | "
            f"{item['partial_bars']:,} | {item['roll_bars']:,} |"
        )
    lines += [
        "",
        "The request boundaries are midnight America/New_York instants. Coverage was not truncated to common overlap; the table reports each product independently.",
        "",
        "## Construction contract",
        "",
        f"Databento documents `ts_event` as the inclusive start of an OHLCV interval and emits no record when no trade occurs: {OHLCV_DOC}",
        "",
        "Five-minute buckets are fixed New York-clock-aligned `:00/:05/.../:55` opens with `[start, end)` semantics. Because New York UTC offsets are integral hours, flooring the UTC nanosecond bar-open to five minutes is exactly the same alignment; timezone-aware spot checks cover both 2024 DST transition weeks.",
        "",
        "OHLCV uses first/max/min/last/sum. Empty buckets are absent. Nonempty buckets are complete only when all five distinct opens at offsets 0–4 are present; other nonempty buckets are retained and flagged. No prices, closes, or zero-volume rows are synthesized.",
        "",
        "## Schema",
        "",
        "| Column | Arrow type | Nullable | Units / meaning |",
        "|---|---|---:|---|",
    ]
    for field in manifest["schema"]:
        lines.append(
            f"| `{field['name']}` | `{field['type']}` | {str(field['nullable']).lower()} | {field['units_or_meaning'] or ''} |"
        )
    lines += [
        "",
        "Scalar `raw_symbol`, `instrument_id`, `roll_id`, and `price_adjustment` are null only when the respective source value is not constant in the bucket. `first_raw_symbol` and `last_raw_symbol` always preserve time order. The adjustment regime identity is the exact fixed-point `price_adjustment` together with `prior_session_close_additive_v1`; `is_mixed_adjustment_bar` means more than one adjustment value occurred.",
        "",
        "## Product/year reconciliation",
        "",
        "| Product | Year | Source rows | 5m rows | Complete | Partial | Missing-minute events* | Unpublished minutes* | Mixed contract | Mixed adjustment | Roll | Break-window bars |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in sorted(stats, key=lambda value: (value["product"], value["year"])):
        lines.append(
            f"| {item['product']} | {item['year']} | {item.get('source_rows', 0):,} | {item.get('rows', 0):,} | "
            f"{item.get('complete_bars', 0):,} | {item.get('partial_bars', 0):,} | "
            f"{item.get('within_session_gap_events_over_one_minute', 0):,} | "
            f"{item.get('unpublished_source_minutes_within_session', 0):,} | "
            f"{item.get('mixed_contract_bars', 0):,} | {item.get('mixed_adjustment_bars', 0):,} | "
            f"{item.get('roll_bars', 0):,} | {item.get('bars_in_nominal_maintenance_window', 0):,} |"
        )
    lines += [
        "",
        "\\* These are observed absences between published bars within the inherited session label. Without a versioned historical exchange calendar they are not asserted to be vendor data loss; they may be no-trade intervals, venue closures, or unknown absences.",
        "",
        "Duplicate source timestamps, invalid source OHLC rows, timestamp-order failures, New York five-minute alignment failures, and raw-price tick-alignment failures were all zero; otherwise the build would have failed.",
        "",
        "## Spot checks",
        "",
    ]
    for product in PRODUCTS:
        item = manifest["products"][product]
        lines += [f"### {product}", "", "Boundary buckets:", ""]
        for check in item.get("boundary_spot_checks", []):
            lines.append(
                f"- {check['local_time']} NY → `{check['bar_open_utc']}`; source opens `{check['first_source_open_utc']}` through `{check['last_source_open_utc']}` ({check['source_bar_count']} bars)."
            )
        lines += ["", "DST transition windows:", ""]
        for check in item.get("dst_spot_checks", []):
            lines.append(
                f"- {check['period']}: {check['bars']:,} bars; {check['ny_alignment_failures']} NY alignment failures."
            )
        lines += ["", "Holiday / early-close observation checks (not calendar certification):", ""]
        for check in item.get("holiday_early_close_spot_checks", []):
            lines.append(
                f"- session `{check['session_date']}`: {check['bars']:,} bars, {check['partial_bars']:,} partial; `{check['first_bar_open_utc']}` to `{check['last_bar_open_utc']}`."
            )
        roll = item.get("roll_spot_check")
        if roll:
            lines += [
                "",
                f"Roll check: `{roll['bar_open_utc']}` contains the roll marker; `{roll['first_raw_symbol']}` → `{roll['last_raw_symbol']}`, mixed-contract={str(roll['is_mixed_contract_bar']).lower()}, mixed-adjustment={str(roll['is_mixed_adjustment_bar']).lower()}.",
            ]
        lines.append("")
    lines += [
        "## Roll and adjustment provenance",
        "",
        f"- Source manifest: `{manifest['source']['manifest']['path']}` (`{manifest['source']['manifest']['sha256']}`)",
        f"- Roll schedule: `{manifest['source']['roll_schedule']['path']}` (`{manifest['source']['roll_schedule']['sha256']}`)",
        f"- Adjustment schedule: `{manifest['source']['adjustment_schedule']['path']}` (`{manifest['source']['adjustment_schedule']['sha256']}`)",
        f"- Adjustment factors: `{manifest['source']['adjustment_factors']['path']}` (`{manifest['source']['adjustment_factors']['sha256']}`)",
        f"- Phase 2 adjustment snapshot/as-of: `{manifest['source']['adjustment_snapshot_as_of']}`",
        "- Roll selection is prior-day Databento volume rank 0, effective at the mapped Globex session boundary.",
        "- Back-adjustment is cumulative additive prior-shared-session-close adjustment. Historical bars use later roll information and are not point-in-time certified.",
        "",
        "## Calendar and absence classification",
        "",
        "No authoritative versioned historical CME product calendar was available to this build. Observed source bars were therefore preserved even in the nominal 17:00–18:00 America/New_York maintenance window, including older schedule regimes. No closure was manufactured or filled. Provider condition reports, including degraded dates and dates with no published records, remain pinned through the Phase 2 manifest.",
        "",
        "## Determinism and validation",
        "",
        f"- Request SHA-256: `{manifest['request']['sha256']}`",
        f"- Canonical request/config SHA-256: `{manifest['request']['canonical_config_sha256']}`",
        f"- Partitions independently replayed: {manifest['validation']['partitions_replayed']}",
        f"- Deterministic replay: {str(manifest['validation']['deterministic_rebuild']).lower()}",
        f"- Phase 2 lineage verified: {str(manifest['validation']['phase2_lineage_verified']).lower()}",
        f"- Synthetic market rows: 0",
        "",
        "## PyArrow loader",
        "",
        "```python",
        manifest["loader_example"],
        "```",
        "",
        "## Known limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in manifest["known_limitations"])
    lines.append("")
    return "\n".join(lines)


def _audit_descriptor(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": _relative(path, root),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _check_publication_absent(paths: DeliveryPaths, *, include_stage: bool = True) -> None:
    metadata = (paths.request_snapshot, paths.manifest, paths.quality_report)
    outputs = [paths.output_root, *metadata, *(p.with_name(p.name + ".part") for p in metadata)]
    if include_stage:
        outputs.append(paths.temporary_output_root)
    for output in outputs:
        check_absent(output, paths.root, error=DeliveryError)


def build(root: Path | str, request_path: Path | str) -> dict[str, Any]:
    paths = DeliveryPaths.from_root(root)
    _check_publication_absent(paths)
    request_path = Path(request_path).resolve()
    request, request_raw = _load_yaml_with_ruby(request_path)
    _validate_request(request)
    request_sha256 = hashlib.sha256(request_raw).hexdigest()
    config_sha256 = _canonical_hash(request)
    start_ns, end_ns, requested_start, requested_end = _date_bounds(request)

    declared_sources = _provenance.publication_sources(Path(__file__), ("provenance.py", "publication_safety.py", "paths.py"))
    retained = _provenance.retain_sources(
        paths.temporary_output_root / "provenance",
        declared_sources,
        artifact_id=DATASET_ID, root=paths.root, error=DeliveryError,
    )

    source_manifest, source_manifest_hash, master, partitions, source_audit = _verify_inputs(paths, request)
    tick_by_roll, ticks_by_product = _tick_lookup(master)
    schema = output_schema(source_manifest_hash, request_sha256)

    stats: list[dict[str, Any]] = []
    for product, year, source_path in partitions:
        source = pq.read_table(source_path)
        table, details = _aggregate_table(
            source, product, year, tick_by_roll, schema, start_ns, end_ns
        )
        if table.num_rows == 0:
            continue
        output_path = paths.output_partition(paths.temporary_output_root, product, year)
        _write_partition(table, output_path)
        stats.append(details)

    validation = _validate_replay(
        paths,
        paths.temporary_output_root,
        partitions,
        tick_by_roll,
        schema,
        start_ns,
        end_ns,
    )
    if not validation["passed"]:
        raise DeliveryError("delivery validation failed: " + "; ".join(validation["failures"]))

    _provenance.verify_retained_sources(
        paths.temporary_output_root / "provenance", declared_sources, retained, error=DeliveryError)
    _check_publication_absent(paths, include_stage=False)
    check_path(paths.temporary_output_root, paths.root, error=DeliveryError)
    paths.output_root.parent.mkdir(parents=True, exist_ok=True)
    os.replace(paths.temporary_output_root, paths.output_root)
    _atomic_bytes(paths.request_snapshot, request_raw)

    output_files: list[dict[str, Any]] = []
    for path in sorted(paths.output_root.glob("product=*/year=*/part-*.parquet")):
        output_files.append(_audit_descriptor(path, paths.root))
    products = _summarize_products(stats)
    generated_at = datetime.now(UTC).isoformat()
    source_output_index = _source_file_index(source_manifest)
    source_partitions = []
    for product, year, path in partitions:
        relative = _relative(path, paths.root)
        source_partitions.append({"product": product, "year": year, **source_output_index[relative]})

    known_limitations = [
        "The source is a final backward-adjusted snapshot. Historical adjusted prices incorporate later rolls and are not point-in-time certified or directly tradable.",
        "This delivery uses the source-observed session_date and preserves observed bars, but it does not certify historical CME holiday, early-close, or maintenance calendars.",
        "Databento omits OHLCV intervals with no trades. Missing source minutes remain absent; partial five-minute bars are flagged rather than filled.",
        "The volume-led roll and additive adjustment methodology is reproducible but is not claimed to match TradingView exactly.",
        "A future Phase 2 roll can change all earlier adjusted prices. Consumers must pin this manifest and its checksums.",
    ]
    manifest: dict[str, Any] = {
        "dataset_id": DATASET_ID,
        "feature_set": FEATURE_SET,
        "feature_set_version": FEATURE_SET_VERSION,
        "algorithm_version": ALGORITHM_VERSION,
        "build_timestamp_utc": generated_at,
        "generation_cutoff_utc": generated_at,
        "request": {
            "source_path": str(request_path),
            "snapshot_path": _relative(paths.request_snapshot, paths.root),
            "sha256": request_sha256,
            "canonical_config_sha256": config_sha256,
            "requested_start_local": f"{requested_start.isoformat()}T00:00:00 America/New_York",
            "requested_end_exclusive_local": f"{requested_end.isoformat()}T00:00:00 America/New_York",
            "requested_start_utc": _iso_ns(start_ns),
            "requested_end_exclusive_utc": _iso_ns(end_ns),
        },
        "source": {
            "dataset": SOURCE_DATASET,
            "variant": SOURCE_VARIANT,
            "manifest": {
                "path": _relative(paths.source_manifest, paths.root),
                "sha256": source_manifest_hash,
            },
            "adjustment_snapshot_as_of": source_manifest.get("build_timestamp_utc"),
            "source_timestamp_convention": "Databento ts_event is the inclusive start/open of each OHLCV interval",
            "source_no_trade_representation": "no record is emitted when no trade occurs in the one-minute interval",
            "source_ohlcv_documentation": OHLCV_DOC,
            "roll_selection_rule": "Databento volume-rank-0 mapping applied at mapped Globex session boundary",
            "adjustment_method": SOURCE_ADJUSTMENT,
            "adjustment_formula": source_manifest.get("adjustment_formula"),
            "point_in_time_certified": False,
            "uses_later_roll_information_for_historical_prices": True,
            "instrument_master": _audit_descriptor(paths.instrument_master, paths.root),
            "roll_schedule": _audit_descriptor(paths.roll_schedule, paths.root),
            "adjustment_schedule": _audit_descriptor(paths.adjustment_schedule, paths.root),
            "adjustment_factors": _audit_descriptor(paths.adjustment_factors, paths.root),
            "partitions": source_partitions,
            "condition_reports": source_manifest.get("condition_reports"),
        },
        "aggregation": {
            "source_timeframe": "1m",
            "output_timeframe": "5m",
            "timezone": "America/New_York",
            "timestamp_label": "bar_open",
            "interval_semantics": "[start,end)",
            "alignment": "fixed :00/:05/.../:55 New York-clock bar opens",
            "ohlcv": {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"},
            "missing_minutes": "not filled",
            "empty_buckets": "not emitted",
            "partial_bars": "nonempty buckets retained and flagged unless terminal; terminal buckets must be complete",
            "roll_buckets": "retained unsplit; contains_roll is any source is_roll",
            "calendar_policy": "preserve observed source bars; no authoritative historical holiday calendar applied",
        },
        "partitioning": ["product", "year(session_date)"],
        "portable_partition_glob": f"data/features/bars/5m/feature_set={FEATURE_SET}/version={FEATURE_SET_VERSION}/product=*/year=*/part-*.parquet",
        "absolute_dataset_path": str(paths.output_root),
        "schema": _schema_manifest(schema),
        "price_encoding": {"type": "int64", "scale": PRICE_SCALE, "rounding": "none"},
        "minimum_ticks_fixed_point": ticks_by_product,
        "minimum_ticks_price_units": {
            product: [value * PRICE_SCALE for value in values]
            for product, values in ticks_by_product.items()
        },
        "historical_min_tick_exceptions": {
            product: [] if len(values) == 1 else [value * PRICE_SCALE for value in values]
            for product, values in ticks_by_product.items()
        },
        "products": products,
        "product_year_quality": stats,
        "output_files": output_files,
        "retained_provenance": dict(retained, path=str((paths.output_root / "provenance").relative_to(paths.root))),
        "code_version": {
            "builder": "src/abacus_bhishma/derived_ohlcv_5m.py",
            "builder_sha256": _sha256(Path(__file__)),
            "helper_source_sha256": {
                "abacus_bhishma.provenance": _sha256(Path(_provenance.__file__)),
            },
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pyarrow": pa.__version__,
            **_git_version(paths.root),
        },
        "validation": validation,
        "loader_example": _loader_example(paths),
        "known_limitations": known_limitations,
        "quality_report_path": _relative(paths.quality_report, paths.root),
    }
    report = _report_markdown(manifest, stats, paths)
    report_bytes = report.encode("utf-8")
    manifest["quality_report_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    _atomic_bytes(paths.quality_report, report_bytes)
    _atomic_text(paths.manifest, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def validate(root: Path | str) -> dict[str, Any]:
    paths = DeliveryPaths.from_root(root)
    if not paths.manifest.is_file() or not paths.request_snapshot.is_file():
        raise DeliveryError("delivery manifest or request snapshot is missing")
    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    request, request_raw = _load_yaml_with_ruby(paths.request_snapshot)
    _validate_request(request)
    request_sha256 = hashlib.sha256(request_raw).hexdigest()
    if request_sha256 != manifest["request"]["sha256"]:
        raise DeliveryError("request snapshot checksum mismatch")
    source_manifest, source_manifest_hash, master, partitions, _ = _verify_inputs(paths, request)
    if source_manifest_hash != manifest["source"]["manifest"]["sha256"]:
        raise DeliveryError("pinned Phase 2 manifest checksum changed")
    for item in manifest["output_files"]:
        path = paths.root / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or _sha256(path) != item["sha256"]:
            raise DeliveryError(f"output checksum mismatch: {item['path']}")
    if _sha256(paths.quality_report) != manifest["quality_report_sha256"]:
        raise DeliveryError("quality report checksum mismatch")
    start_ns, end_ns, _, _ = _date_bounds(request)
    tick_by_roll, _ = _tick_lookup(master)
    result = _validate_replay(
        paths,
        paths.output_root,
        partitions,
        tick_by_roll,
        output_schema(source_manifest_hash, request_sha256),
        start_ns,
        end_ns,
    )
    if not result["passed"]:
        raise DeliveryError("delivery validation failed: " + "; ".join(result["failures"]))
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Publication project root; otherwise use configured storage")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build", help="build the immutable delivery")
    build_parser.add_argument("--request", type=Path, help="Request file; defaults to the publication root's fulfilled request")
    subparsers.add_parser("validate", help="independently replay and validate the delivery")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        args.root = resolve_publication_root(args.root)
        if args.command == "build":
            args.request = args.request if args.request is not None else args.root / DEFAULT_REQUEST
            result = build(args.root, args.request)
            print(
                json.dumps(
                    {
                        "dataset_id": result["dataset_id"],
                        "path": result["absolute_dataset_path"],
                        "rows": {product: result["products"][product]["rows"] for product in PRODUCTS},
                    },
                    indent=2,
                )
            )
        else:
            print(json.dumps(validate(args.root), indent=2, sort_keys=True))
    except (DeliveryError, PathConfigurationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
