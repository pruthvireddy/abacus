#!/usr/bin/env python3
"""Independent retained-feature checks; never reads pivots or market outcomes."""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


STUDY = Path(__file__).resolve().parent
WORKSPACE = STUDY.parents[1]
NY = ZoneInfo("America/New_York")
MINUTE_NS = 60_000_000_000
OHLCV = ("open", "high", "low", "close", "volume")
MONTHS = {3: "H", 6: "M", 9: "U", 12: "Z"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def compare_columns(actual: pd.DataFrame, expected: pd.DataFrame,
                    columns: list[str], label: str, tolerance: float = 0.) -> dict:
    check(len(actual) == len(expected), f"{label}: row count mismatch")
    maximum = 0.
    for name in columns:
        left, right = actual[name].reset_index(drop=True), expected[name].reset_index(drop=True)
        if pd.api.types.is_numeric_dtype(left) and pd.api.types.is_numeric_dtype(right):
            a, b = left.to_numpy(float), right.to_numpy(float)
            same_null = np.isnan(a) == np.isnan(b)
            finite = np.isfinite(a) & np.isfinite(b)
            error = np.abs(a[finite] - b[finite])
            difference = float(error.max()) if len(error) else 0.
            maximum = max(maximum, difference)
            equal = bool(same_null.all() and np.array_equal(np.isinf(a), np.isinf(b))
                         and np.array_equal(a[np.isinf(a)], b[np.isinf(b)]) and difference <= tolerance)
        else:
            equal = bool((left.eq(right) | (left.isna() & right.isna())).all())
        check(equal, f"{label}: {name} differs")
    return {"status": "passed", "rows": len(actual), "columns": columns,
            "cells": len(actual) * len(columns), "maximum_absolute_error": maximum,
            "tolerance": tolerance}


def oracle_ema6(frame: pd.DataFrame, preceding: int = 250) -> pd.DataFrame:
    """Independent scalar recurrence from the complete inherited 2017 roster."""
    values, counts, readiness = [], [], []
    state, last_time, identity = None, None, None
    count = 0
    alpha = 2. / (6. + 1.)
    for stamp, contract, close, usable, known in frame[
            ["timestamp", "contract", "close", "usable", "known_closure_before"]].itertuples(index=False, name=None):
        valid = bool(usable) and pd.notna(contract) and pd.notna(close) and math_finite(close)
        if not valid:
            state, count, identity = None, 0, None
            values.append(np.nan)
            counts.append(0)
            readiness.append(False)
            last_time = stamp
            continue
        interrupted = last_time is not None and stamp - last_time > pd.Timedelta(minutes=3) and not bool(known)
        switched = identity is not None and identity != contract
        if interrupted or switched:
            state, count = None, 0
        ready_before_current = count >= preceding
        state = float(close) if state is None else alpha * float(close) + (1. - alpha) * state
        count += 1
        values.append(state)
        counts.append(count)
        readiness.append(ready_before_current)
        identity, last_time = contract, stamp
    return pd.DataFrame({"timestamp": frame.timestamp.to_numpy(), "ema6": values,
                         "ema6_consecutive_count": counts, "ema6_ready": readiness})


def math_finite(value) -> bool:
    return bool(np.isfinite(float(value)))


def oracle_vwap(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Independent per-session prefix and NumPy cumulative HLC3 calculation.

    The saved calendar flag remains the pinned qualified calendar input, not a
    claim of independently certified annual exchange schedules.
    """
    n = len(frame)
    expected_values = np.full(n, np.nan)
    expected_prefix = np.zeros(n, bool)
    expected_valid = np.zeros(n, bool)
    expected_usable = np.zeros(n, bool)
    stamps = frame.timestamp.astype("int64").to_numpy()
    numeric = frame[list(OHLCV)].to_numpy(float)
    contracts = frame.contract.to_numpy(object)
    calendar = frame.calendar_valid.to_numpy(bool)
    numeric_valid = np.isfinite(numeric).all(axis=1) & (numeric[:, :4] > 0).all(axis=1) & (numeric[:, 4] >= 0)
    numeric_valid &= numeric[:, 1] >= numeric[:, [0, 3]].max(axis=1)
    numeric_valid &= numeric[:, 2] <= numeric[:, [0, 3]].min(axis=1)
    numeric_valid &= numeric[:, 1] >= numeric[:, 2]
    tick = np.isclose(numeric[:, :4] * 4, np.round(numeric[:, :4] * 4), rtol=0., atol=1e-7).all(axis=1)
    for text, positions in frame.groupby("session_date", sort=False).indices.items():
        day = date.fromisoformat(str(text))
        anchor = datetime.combine(day - timedelta(days=1), time(18), NY)
        finish = datetime.combine(day, time(17), NY)
        anchor_ns, finish_ns = int(anchor.timestamp()) * 10**9, int(finish.timestamp()) * 10**9
        local_stamps = stamps[positions]
        allowed = (local_stamps >= anchor_ns) & (local_stamps < finish_ns) & (local_stamps % MINUTE_NS == 0)
        pause_end_ns = int(datetime.combine(day, time(16, 30), NY).timestamp()) * 10**9
        if day < date(2021, 6, 28):
            pause_start_ns = pause_end_ns - 15 * MINUTE_NS
            allowed &= ~((local_stamps >= pause_start_ns) & (local_stamps < pause_end_ns))
        usable = numeric_valid[positions] & tick[positions] & calendar[positions] & allowed & pd.notna(contracts[positions])
        expected_usable[positions] = usable
        steps = np.empty(len(positions), bool)
        steps[0] = local_stamps[0] == anchor_ns
        if len(positions) > 1:
            differences = np.diff(local_stamps)
            steps[1:] = differences == MINUTE_NS
            if day < date(2021, 6, 28):
                steps[1:] |= (local_stamps[1:] == pause_end_ns) & (differences == 16 * MINUTE_NS)
        same_delivery = contracts[positions] == contracts[positions][0]
        prefix = np.logical_and.accumulate(usable & steps & same_delivery)
        with np.errstate(invalid="ignore", divide="ignore"):
            hlc3 = numeric[positions, 1:4].sum(axis=1) / 3.
            volumes = np.cumsum(numeric[positions, 4])
            weights = np.cumsum(hlc3 * numeric[positions, 4])
            valid = prefix & (volumes > 0)
            values = np.where(valid, weights / volumes, np.nan)
        expected_prefix[positions], expected_valid[positions], expected_values[positions] = prefix, valid, values
    oracle = pd.DataFrame({"usable": expected_usable, "anchor_prefix_complete": expected_prefix,
                           "vwap_valid": expected_valid, "globex_vwap": expected_values})
    return oracle, {"sessions": frame.session_date.nunique(), "rows": n,
                    "valid_vwap_rows": int(expected_valid.sum()),
                    "invalid_or_undefined_rows": int((~expected_valid).sum())}


def _availability(frame, interval, label):
    check(not frame.timestamp.duplicated().any() and frame.timestamp.is_monotonic_increasing,
          f"{label}: native timestamps are not unique chronological")
    expected = frame.timestamp + pd.Timedelta(minutes=interval)
    for name in ("available_at", "close_time"):
        check(frame[name].eq(expected).all(), f"{label}: modeled completion mismatch")
    check(frame.open_time.eq(frame.timestamp).all(), f"{label}: opening alias mismatch")
    return {"status": "passed", "rows": len(frame), "interval_minutes": interval}


def _asof_cloud(three, five):
    expected_ns = np.full(len(three), np.iinfo(np.int64).min, dtype=np.int64)
    expected20, expected50 = np.full(len(three), np.nan), np.full(len(three), np.nan)
    expected_ready = np.zeros(len(three), bool)
    left_ns = three.available_at.astype("int64").to_numpy()
    for contract, positions in three.groupby("contract", dropna=True, sort=False).indices.items():
        selected = five.loc[five.contract.eq(contract)]
        native = selected.available_at.astype("int64").to_numpy()
        lookup = np.searchsorted(native, left_ns[positions], side="right") - 1
        found = lookup >= 0
        expected_ns[positions[found]] = native[lookup[found]]
        expected20[positions[found]] = selected.ema20.to_numpy()[lookup[found]]
        expected50[positions[found]] = selected.ema50.to_numpy()[lookup[found]]
        expected_ready[positions[found]] = selected.cloud_ready.to_numpy()[lookup[found]]
    observed_ns = three.cloud_available_at.astype("int64").to_numpy()
    check(np.array_equal(observed_ns, expected_ns), "3m cloud join is not the latest completed same-contract 5m value")
    check(bool(((observed_ns <= left_ns) | (observed_ns == np.iinfo(np.int64).min)).all()), "future cloud value joined to 3m")
    result = compare_columns(three, pd.DataFrame({"ema20": expected20, "ema50": expected50, "cloud_ready": expected_ready}),
                             ["ema20", "ema50", "cloud_ready"], "completed cloud values")
    return {**result, "joined_rows": int((expected_ns != np.iinfo(np.int64).min).sum())}


def _snapshots(output: Path | None, lock_path: Path):
    paths = [Path(__file__).resolve(), STUDY / "tests/test_verify_features.py", lock_path, WORKSPACE / "uv.lock"]
    paths += [WORKSPACE / "packages/bhishma/src/abacus_bhishma" / name for name in
              ("es_contract_session_indicators.py", "ema_cloud_loader_v2.py", "ema_cloud.py", "manifest_selection.py")]
    records = []
    for path in paths:
        record = {"path": str(path.relative_to(WORKSPACE)), "sha256": digest(path), "bytes": path.stat().st_size}
        if output:
            destination = output / "provenance" / path.relative_to(WORKSPACE)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            record["retained_path"] = str(destination.relative_to(output))
        records.append(record)
    return records


def verify(root, lock_path, output=None) -> dict:
    """Verify pinned features, read-only unless a fresh receipt path is explicit."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    from abacus_bhishma.es_contract_session_indicators import load_release
    from abacus_bhishma.ema_cloud_loader_v2 import load_release as load_old

    root, lock_path = Path(root).resolve(), Path(lock_path).resolve()
    destination = Path(output).resolve() if output else None
    if destination:
        check(destination.is_relative_to(WORKSPACE / "work" / STUDY.name), "feature receipt must be a new study work directory")
        destination.mkdir(parents=True, exist_ok=False)
    sources = _snapshots(destination, lock_path)
    lock = json.loads(lock_path.read_text())
    pins = {name: lock["inputs"][name] for name in ("session_indicators", "retained_cloud_reference", "retained_continuous_minutes")}
    manifests = {}
    for name, pin in pins.items():
        check(digest(root / pin["path"]) == pin["sha256"], f"{name}: manifest pin mismatch")
        manifests[name] = json.loads((root / pin["path"]).read_text())
    new, cloud = pins["session_indicators"], pins["retained_cloud_reference"]
    start = manifests["session_indicators"]["settings"]["start_session"]
    end = manifests["session_indicators"]["settings"]["end_session_exclusive"]
    checks = {}
    three = load_release(root, new["path"], new["sha256"], table="bars3")
    old = load_old(root, product="ES", interval=3, manifest_path=cloud["path"], expected_manifest_sha256=cloud["sha256"])
    selected = old.session.astype(str).ge(start) & old.session.astype(str).lt(end)
    expected = old.loc[selected].reset_index(drop=True).rename(columns={"contract": "contract_identity"})
    columns = ["timestamp", *OHLCV, "usable", "available_at", "session", "contract_identity", "known_closure_before", "calendar_valid"]
    checks["all_reused_3m_bars"] = compare_columns(three, expected, columns, "reused 3m")
    oracle = oracle_ema6(old)
    checks["independent_ema6_full_history"] = compare_columns(three, oracle.loc[selected].reset_index(drop=True),
                                                           ["timestamp", "ema6", "ema6_consecutive_count", "ema6_ready"], "EMA6", tolerance=1e-10)
    checks["independent_ema6_full_history"]["source_history_rows"] = len(old)
    checks["availability_3m"] = _availability(three, 3, "3m")
    del old, expected, oracle
    five = load_release(root, new["path"], new["sha256"], table="bars5")
    old = load_old(root, product="ES", interval=5, manifest_path=cloud["path"], expected_manifest_sha256=cloud["sha256"])
    selected = old.session.astype(str).ge(start) & old.session.astype(str).lt(end)
    expected = old.loc[selected].reset_index(drop=True).rename(columns={"contract": "contract_identity"})
    checks["all_reused_5m_bars_and_emas"] = compare_columns(five, expected,
        [*columns, "ema20", "ema50", "consecutive_count", "feature_reset"], "reused 5m/cloud")
    check(five.cloud_ready.eq(five.usable & five.consecutive_count.gt(250)).all(), "5m cloud readiness does not require 250 preceding valid observations")
    checks["availability_5m"] = _availability(five, 5, "5m")
    checks["completed_cloud_join"] = _asof_cloud(three, five)
    del old, expected
    quality = load_release(root, new["path"], new["sha256"], table="quality")
    sample_dates = []
    for year in range(int(start[:4]), int(end[:4]) + 1):
        for month in (1, 7):
            choices = quality.loc[quality.session_date.str.startswith(f"{year:04d}-{month:02d}") & quality.full_globex_complete, "session_date"]
            if len(choices):
                sample_dates.append(str(choices.min()))
    sampled_native = {interval: frame.loc[frame.session_date.isin(sample_dates), ["timestamp", *OHLCV]].copy()
                      for interval, frame in ((3, three), (5, five))}
    del three, five
    one = load_release(root, new["path"], new["sha256"], table="bars1")
    checks["availability_1m"] = _availability(one, 1, "1m")
    source = manifests["retained_continuous_minutes"]
    pattern = re.compile(r"data/curated/continuous/1m/product=ES/roll=volume_lead_v1/variant=unadjusted/year=([0-9]{4})/part-[^/]+\.parquet\Z")
    records = [record for record in source["output_files"] if (match := pattern.fullmatch(record["path"])) and int(start[:4]) <= int(match[1]) <= int(end[:4])]
    master_records = [record for record in source["output_files"] if record["path"].endswith("/instrument_master.parquet")]
    check(len(master_records) == 1, "one pinned instrument master required")
    for record in [*records, *master_records]:
        check(digest(root / record["path"]) == record["sha256"], "source minute/master checksum mismatch")
    raw_columns = ["ts_event", "session_date", "instrument_id", "raw_symbol", "roll_id", "source_batch", *OHLCV]
    raw = pa.concat_tables([pq.ParquetFile(root / record["path"]).read(columns=raw_columns) for record in records]).to_pandas()
    raw.session_date = raw.session_date.astype(str)
    raw = raw.loc[raw.session_date.ge(start) & raw.session_date.lt(end)].sort_values("ts_event").reset_index(drop=True)
    raw.rename(columns={"ts_event": "timestamp"}, inplace=True)
    for name in OHLCV[:4]:
        raw[name] = raw[name].to_numpy(float) * 1e-9
    checks["all_minute_ohlcv_and_identities"] = compare_columns(one, raw, ["timestamp", "session_date", "instrument_id", "raw_symbol", "roll_id", "source_batch", *OHLCV], "1m source")
    master = pq.ParquetFile(root / master_records[0]["path"]).read(columns=["product", "roll_id", "instrument_id", "raw_symbol", "maturity_year", "maturity_month"]).to_pandas()
    master = master.loc[master["product"].eq("ES")].set_index("roll_id")
    check(master.index.is_unique, "instrument master has duplicate ES roll identities")
    mapped = master.reindex(one.roll_id)
    expected_contracts = np.array([f"ES{MONTHS[int(month)]}{int(year):04d}" for month, year in zip(mapped.maturity_month, mapped.maturity_year)])
    check(np.array_equal(expected_contracts, one.contract.to_numpy()), "full-maturity contract mapping differs from master")
    checks["minute_full_maturity_mapping"] = {"status": "passed", "rows": len(one)}
    vwap, vwap_counts = oracle_vwap(one)
    checks["independent_globex_vwap"] = compare_columns(one, vwap, ["usable", "anchor_prefix_complete", "vwap_valid", "globex_vwap"], "Globex VWAP", tolerance=1e-8)
    checks["independent_globex_vwap"].update(vwap_counts)
    aggregation = []
    for day in sample_dates:
        minute_sample = raw.loc[raw.session_date.eq(day)].set_index("timestamp")
        for interval in (3, 5):
            groups = minute_sample.groupby(minute_sample.index.floor(f"{interval}min"), sort=True)
            independently_aggregated = groups.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), volume=("volume", "sum"))
            expected = sampled_native[interval].set_index("timestamp").reindex(independently_aggregated.index)
            result = compare_columns(expected, independently_aggregated, list(OHLCV), "sampled native aggregation")
            aggregation.append({"session_date": day, "interval_minutes": interval, **result})
    checks["independent_native_aggregation"] = {"status": "passed", "selection": "first full-Globex-complete January/July session per year; no outcome selection", "samples": aggregation,
                                                "sessions": len(sample_dates), "bars": sum(row["rows"] for row in aggregation)}
    for record in sources:
        check(digest(WORKSPACE / record["path"]) == record["sha256"], "verification source/lock changed during execution")
    receipt = {"schema_version": "abacus.study30.independent-feature-verification/v1", "status": "passed",
               "created_at": datetime.now(timezone.utc).isoformat(), "argv": sys.argv, "cwd": str(Path.cwd()),
               "python": sys.version, "platform": platform.platform(), "sources": sources,
               "input_manifests": pins, "checks": checks,
               "source_files_verified": [*records, *master_records],
               "market_outcomes_read": False, "pivot_levels_read": False,
               "scope": "All reused native values, EMA6 recurrence/readiness, one-minute source identity/VWAP, modeled timing and deterministic aggregation samples.",
               "qualifications": ["Calendar rules remain qualified, not independently exchange-certified.", "Actual feed receipt times and native chart equivalence are not established.", "NumPy cumulative VWAP is compared within 1e-8 ES points for summation-order differences."]}
    if destination:
        with (destination / "receipt.json").open("x") as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=WORKSPACE)
    parser.add_argument("--lock", type=Path, default=STUDY / "inputs.lock.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    receipt = verify(args.root, args.lock, args.output)
    print(json.dumps({"status": receipt["status"], "checks": {name: {key: value for key, value in check.items() if key in ("rows", "cells", "maximum_absolute_error", "sessions", "bars", "source_history_rows")} for name, check in receipt["checks"].items()}, "receipt": str(args.output / "receipt.json") if args.output else None}, sort_keys=True))


if __name__ == "__main__":
    main()
