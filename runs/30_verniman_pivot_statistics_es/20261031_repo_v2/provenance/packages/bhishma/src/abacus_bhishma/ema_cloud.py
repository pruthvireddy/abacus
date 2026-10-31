"""Causal same-contract fixed-clock bars and EMA/Wilder features.

Quality slots are never synthetic candles. Rule-generated holiday sessions
retain invalid nominal slots; normal known closures are omitted.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .calendar import holiday_sessions
from .manifest_selection import read_pinned_manifest, selected_files
from .provenance import sha256_file

NY = "America/New_York"
MINUTE_NS = 60_000_000_000
DATASET_ID = "same_contract_ema_cloud__1.0.0"
VERSION = "1.0.0"


def expected_minutes(product: str, start_session: date | str,
                     end_session: date | str) -> pd.DataFrame:
    """Inclusive start/exclusive end weekday nominal electronic minute roster.

    Supported from 2015-09-21. Omit normal 17:00–18:00 and weekends;
    ES/NQ's historical 16:15–16:30 pause is omitted before 2021-06-28.
    Uncertified holiday/early-close sessions remain invalid nominal slots.
    """
    product = product.upper()
    if product not in {"ES", "NQ", "GC"}:
        raise ValueError("unsupported product")
    start, end = date.fromisoformat(str(start_session)), date.fromisoformat(str(end_session))
    if start < date(2015, 9, 21) or end <= start:
        raise ValueError("unsupported calendar range")
    holidays = holiday_sessions(product, start.year, end.year)
    pieces = []
    for day in pd.date_range(start, end - timedelta(days=1), freq="B"):
        session = day.date()
        opening = pd.Timestamp(datetime.combine(session - timedelta(days=1), time(18)), tz=NY)
        closing = pd.Timestamp(datetime.combine(session, time(17)), tz=NY)
        ts = pd.date_range(opening, closing, freq="min", inclusive="left")
        if product in {"ES", "NQ"} and session < date(2021, 6, 28):
            minute = ts.hour * 60 + ts.minute
            ts = ts[(minute < 975) | (minute >= 990)]
        event = ";".join(holidays.get(session, []))
        pieces.append(pd.DataFrame({"timestamp": ts.tz_convert("UTC"),
                                   "session": session.isoformat(),
                                   "calendar_event": event,
                                   "calendar_valid": not bool(event)}))
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(
        columns=["timestamp", "session", "calendar_event", "calendar_valid"])


def aggregate_minutes(source: pd.DataFrame, interval: int, schedule: pd.DataFrame,
                      product: str) -> pd.DataFrame:
    """Aggregate independently and preserve every expected clock slot.

    Source requires timestamp, contract, OHLCV, and may contain raw_symbol,
    roll_id/source_batch/is_roll. Partial observed prices remain unusable;
    empty prices and volume remain null. Missing minutes are never filled.
    """
    if interval not in {3, 5}:
        raise ValueError("interval must be 3 or 5")
    source, schedule = source.copy(), schedule.copy()
    source["timestamp"] = pd.to_datetime(source["timestamp"], utc=True)
    schedule["timestamp"] = pd.to_datetime(schedule["timestamp"], utc=True)
    if schedule.timestamp.duplicated().any() or not schedule.timestamp.is_monotonic_increasing:
        raise ValueError("minute roster must be unique and strictly sorted")
    if not source.timestamp.is_monotonic_increasing:
        raise ValueError("source minutes must be sorted")
    for frame in (source, schedule):
        frame["_bucket"] = frame.timestamp.dt.floor(f"{interval}min")
        frame["_offset"] = ((frame.timestamp.astype("int64") - frame._bucket.astype("int64")) // MINUTE_NS).astype(int)
    expected = schedule.groupby("_bucket", sort=True).agg(
        expected_count=("timestamp", "size"), session=("session", "first"),
        calendar_event=("calendar_event", "first"), calendar_valid=("calendar_valid", "all"))
    src = source[source.timestamp.isin(schedule.timestamp)].copy()
    for column in ("raw_symbol", "roll_id", "source_batch", "is_roll"):
        if column not in src:
            src[column] = False if column == "is_roll" else ""
    numeric = src[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float)
    src["_bad"] = (~np.isfinite(numeric).all(axis=1) | (numeric[:, :4] <= 0).any(axis=1)
                   | (numeric[:, 4] < 0) | (numeric[:, 1] < numeric[:, 0])
                   | (numeric[:, 1] < numeric[:, 3]) | (numeric[:, 2] > numeric[:, 0])
                   | (numeric[:, 2] > numeric[:, 3]) | (numeric[:, 1] < numeric[:, 2]))
    if "source_valid" in src:
        src["_bad"] |= ~src.source_valid.astype(bool)
    src["_missing_contract"] = src.contract.isna() | src.contract.astype("string").str.strip().eq("").fillna(True)
    src["_duplicate"] = src.timestamp.duplicated(keep=False)
    groups = src.groupby("_bucket", sort=True)
    actual = groups.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                        close=("close", "last"), volume=("volume", "sum"),
                        source_count=("timestamp", "size"), distinct_count=("timestamp", "nunique"),
                        contract=("contract", "first"), contract_count=("contract", "nunique"),
                        raw_symbol=("raw_symbol", "first"), roll_id=("roll_id", "first"),
                        source_batch=("source_batch", "first"), contains_roll=("is_roll", "any"),
                        bad_source=("_bad", "any"), duplicate_source=("_duplicate", "any"),
                        missing_contract_source=("_missing_contract", "any"))
    actual["_offset_mask"] = groups["_offset"].agg(lambda x: sum(1 << int(v) for v in set(x)))
    result = expected.join(actual).reset_index().rename(columns={"_bucket": "timestamp"})
    for name in ("source_count", "distinct_count", "contract_count", "_offset_mask"):
        result[name] = result[name].fillna(0).astype(int)
    for name in ("contains_roll", "bad_source", "duplicate_source", "missing_contract_source"):
        result[name] = result[name].astype("boolean").fillna(False).astype(bool)
    masks = result._offset_mask.to_numpy()
    result["missing_offsets"] = [",".join(str(j) for j in range(interval) if not (int(mask) >> j) & 1) for mask in masks]
    result["contract"] = result.contract.where(result.contract_count == 1, None)
    reason = np.full(len(result), "", dtype=object)
    checks = [(~result.calendar_valid, "calendar_uncertified"),
              (result.expected_count != interval, "scheduled_partial_bucket"),
              (result.source_count == 0, "empty_bucket"),
              ((result.source_count > 0) & (result.distinct_count != result.expected_count), "missing_source_minutes"),
              (result.contract_count > 1, "mixed_contract"),
              ((result.source_count > 0) & (result.missing_contract_source | (result.contract_count == 0)), "missing_contract_identity"),
              (result.bad_source, "invalid_source_ohlcv"),
              (result.duplicate_source, "duplicate_source_minute")]
    for mask, label in checks:
        indices = np.asarray(mask, dtype=bool)
        reason[indices] = [f"{old};{label}" if old else label for old in reason[indices]]
    result["quality_reason"] = reason
    result["usable"] = reason == ""
    result["available_at"] = result.timestamp + pd.Timedelta(minutes=interval)
    result["product"] = product.upper()
    result["interval_minutes"] = interval
    result["ny_offset_minutes"] = [int(x.utcoffset().total_seconds() // 60) for x in result.timestamp.dt.tz_convert(NY)]
    result["known_closure_before"] = (result.timestamp.diff() > pd.Timedelta(minutes=interval)).fillna(False)
    result["lineage"] = [f"{c}|roll={r}|batch={b}" if n else "" for c, r, b, n in
                         zip(result.contract, result.roll_id, result.source_batch, result.source_count)]
    return result.drop(columns=["_offset_mask"]).reset_index(drop=True)


def add_features(bars: pd.DataFrame, warmup: int = 250) -> pd.DataFrame:
    """First-close EMA20/50; Wilder ATR14; conservative segment warmup.

    First segment TR is high-low. ATR seeds from first 14 valid TR values.
    Unknown omitted slots reset unless explicitly known_closure_before.
    EMA outputs during warmup are retained but feature_valid remains false.
    """
    if warmup < 14:
        raise ValueError("warmup must be at least 14")
    if bars.timestamp.duplicated().any() or not bars.timestamp.is_monotonic_increasing:
        raise ValueError("bars must be unique and strictly sorted")
    result = bars.copy()
    n = len(result)
    output = {k: np.full(n, np.nan) for k in ("ema20", "ema50", "atr14", "true_range")}
    valid, reset = np.zeros(n, bool), np.zeros(n, bool)
    reason, counts = np.full(n, "", object), np.zeros(n, np.int32)
    previous_contract, previous_close, previous_timestamp = None, None, None
    count = 0
    ema20 = ema50 = atr = None
    seed_tr = []
    for i, row in enumerate(result.itertuples(index=False)):
        unknown_gap = (previous_timestamp is not None and row.timestamp - previous_timestamp > pd.Timedelta(minutes=5)
                       and not bool(getattr(row, "known_closure_before", False)))
        contract_switch = previous_contract is not None and row.contract != previous_contract
        if not row.usable or row.contract is None or pd.isna(row.contract):
            reset[i] = True
            reason[i] = str(row.quality_reason or "invalid_bar")
            count, ema20, ema50, atr, previous_close, previous_contract, seed_tr = 0, None, None, None, None, None, []
            previous_timestamp = row.timestamp
            continue
        if count == 0 or contract_switch or unknown_gap:
            reason[i] = "unknown_feature_gap" if unknown_gap else "contract_switch" if contract_switch else "segment_start"
            reset[i] = True
            count, ema20, ema50, atr, previous_close, seed_tr = 0, None, None, None, None, []
        close, high, low = float(row.close), float(row.high), float(row.low)
        tr = high-low if previous_close is None else max(high-low, abs(high-previous_close), abs(low-previous_close))
        ema20 = close if ema20 is None else 2 / 21 * close + 19 / 21 * ema20
        ema50 = close if ema50 is None else 2 / 51 * close + 49 / 51 * ema50
        count += 1
        if count <= 14:
            seed_tr.append(tr)
            if count == 14:
                atr = float(np.mean(seed_tr))
        else:
            atr = (13 * atr + tr) / 14
        for k, value in (("ema20", ema20), ("ema50", ema50), ("atr14", atr), ("true_range", tr)):
            output[k][i] = np.nan if value is None else value
        counts[i], valid[i] = count, count >= warmup
        previous_contract, previous_close, previous_timestamp = row.contract, close, row.timestamp
    for key, values in output.items():
        result[key] = values
    result["feature_valid"], result["feature_reset"] = valid, reset
    result["feature_reset_reason"], result["consecutive_count"] = reason, counts
    return result


def load_release(project_root: Path | str, *, product: str, interval: int,
                 manifest_path: Path | str, expected_manifest_sha256: str,
                 verify_selected_files: bool = True) -> pd.DataFrame:
    """Read only declared immutable delivery bytes with explicit manifest pin."""
    manifest = read_pinned_manifest(project_root, manifest_path, expected_manifest_sha256, verify_selected_files)
    if manifest.get("dataset_id") != DATASET_ID or manifest.get("version") != VERSION:
        raise ValueError("unsupported same-contract cloud release")
    selected = [r for r in manifest["output_files"] if r["product"] == product.upper() and r["interval_minutes"] == interval]
    if len(selected) != 1:
        raise ValueError("release must declare exactly one selected product/interval file")
    record = selected[0]
    path = Path(project_root) / record["path"]
    if verify_selected_files and sha256_file(path) != record["sha256"]:
        raise ValueError("delivery partition checksum mismatch")
    return pq.ParquetFile(path).read().to_pandas()


def load_pinned_5m(project_root: Path, manifest_path: Path, expected_hash: str,
                   product: str, years: tuple[int, ...]) -> pd.DataFrame:
    """Pinned public reader for retained five-minute reconciliation support."""
    manifest = read_pinned_manifest(project_root, manifest_path, expected_hash, False)
    if manifest.get("dataset_id") != "tv_indicators__dridr_ohlcv_5m__v1":
        raise ValueError("wrong retained five-minute identity")
    files = selected_files(project_root, manifest,
                           lambda name: f"/product={product}/" in name and any(f"/year={y}/" in name for y in years), verify=True)
    return pa.concat_tables([pq.ParquetFile(f).read() for f in sorted(files)]).to_pandas()
