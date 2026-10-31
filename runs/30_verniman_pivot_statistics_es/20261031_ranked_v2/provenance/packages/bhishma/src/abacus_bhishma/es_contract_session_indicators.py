"""Retained-input ES indicators; no acquisition or study outcome calculations.

Reuse published 3m OHLCV and 5m EMA20/50 exactly. Add a causal 3m EMA6,
one-minute HLC3 Globex VWAP, and completed-value joins. Retained volume-lead
coverage is a fragment of each delivery's history, never another contract's
substitute. Existing publications are never changed or rebuilt.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import re
import shutil

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .calendar import holiday_sessions
from .ema_cloud_loader_v2 import load_release as load_cloud
from .manifest_selection import read_pinned_manifest, selected_files
from .provenance import (git_version, publication_sources, retain_sources,
                         sha256_file, verify_retained_sources)
from .publication_safety import check_absent, check_path, write_new_bytes

DATASET_ID = "es_contract_session_indicators__1.0.0"
VERSION = "1.0.0"
NY = "America/New_York"
MONTHS = {3: "H", 6: "M", 9: "U", 12: "Z"}
TABLES = ("bars1", "bars3", "bars5", "quality")


def _canonical_identity(value):
    if value is None or pd.isna(value):
        return None
    parts = str(value).split(":")
    if len(parts) != 5 or parts[0] != "ES" or int(parts[3]) not in MONTHS:
        raise ValueError("unrecognized pinned ES contract identity")
    return f"ES{MONTHS[int(parts[3])]}{int(parts[2]):04d}"


def native_bars(frame: pd.DataFrame, interval: int) -> pd.DataFrame:
    """Add delivery/time aliases without changing saved OHLCV or cloud values."""
    result = frame.copy()
    if interval not in (3, 5) or result.timestamp.duplicated().any() or not result.timestamp.is_monotonic_increasing:
        raise ValueError("native bars must be chronological unique 3m/5m observations")
    result["contract_identity"] = result.contract
    result["contract"] = result.contract.map(_canonical_identity)
    result["session_date"] = result["session"].astype(str)
    result["open_time"] = pd.to_datetime(result.timestamp, utc=True)
    result["close_time"] = pd.to_datetime(result.available_at, utc=True)
    if not result.close_time.eq(result.open_time + pd.Timedelta(minutes=interval)).all():
        raise ValueError("native bar completion does not match interval")
    return result


def add_ema6(bars: pd.DataFrame, *, preceding_bars: int = 250) -> pd.DataFrame:
    """Same valid-slot/contract/gap recurrence as the pinned cloud, at 3m."""
    if type(preceding_bars) is not int or preceding_bars < 0:
        raise ValueError("preceding bar requirement must be nonnegative")
    if bars.timestamp.duplicated().any() or not bars.timestamp.is_monotonic_increasing:
        raise ValueError("EMA bars must be unique and chronological")
    result = bars.copy()
    n = len(result)
    ema = np.full(n, np.nan)
    counts = np.zeros(n, dtype=np.int32)
    resets = np.zeros(n, dtype=bool)
    reasons = np.full(n, "", dtype=object)
    segments = np.zeros(n, dtype=np.int64)
    previous_time = previous_contract = value = None
    count = segment = 0
    columns = ["timestamp", "contract", "close", "usable", "known_closure_before", "quality_reason"]
    for i, (timestamp, contract, close, usable, known, quality) in enumerate(result[columns].itertuples(index=False, name=None)):
        unknown_gap = previous_time is not None and timestamp - previous_time > pd.Timedelta(minutes=3) and not known
        changed = previous_contract is not None and contract != previous_contract
        if not usable or contract is None or pd.isna(contract) or not np.isfinite(close):
            count, value, previous_contract = 0, None, None
            segment += 1
            resets[i], reasons[i] = True, str(quality or "invalid_bar")
            previous_time = timestamp
            segments[i] = segment
            continue
        if count == 0 or unknown_gap or changed:
            segment += 1
            count, value = 0, None
            resets[i] = True
            reasons[i] = "unknown_feature_gap" if unknown_gap else "contract_switch" if changed else "segment_start"
        value = float(close) if value is None else 2 / 7 * float(close) + 5 / 7 * value
        count += 1
        ema[i], counts[i], segments[i] = value, count, segment
        previous_contract, previous_time = contract, timestamp
    result["ema6"] = ema
    result["ema6_consecutive_count"] = counts
    result["ema6_ready"] = counts > preceding_bars
    result["ema6_reset"] = resets
    result["ema6_reset_reason"] = reasons
    result["ema6_segment"] = segments
    return result


def add_exact_slope(frame: pd.DataFrame, line: str, ready: str, segment: str) -> pd.DataFrame:
    """Exact 15-minute native endpoint difference, within one valid segment."""
    result = frame.copy()
    lookup = frame.set_index("available_at")
    earlier = lookup.reindex(pd.DatetimeIndex(frame.available_at - pd.Timedelta(minutes=15)))
    same = (frame.contract.to_numpy(object) == earlier.contract.to_numpy(object))
    same &= frame[segment].to_numpy() == earlier[segment].to_numpy()
    usable = frame[ready].to_numpy(bool) & earlier[ready].eq(True).to_numpy(bool) & same
    values = frame[line].to_numpy(float) - earlier[line].to_numpy(float)
    result[line + "_slope_15m"] = np.where(usable, values, np.nan)
    return result


def derive_minute_vwap(minutes: pd.DataFrame) -> pd.DataFrame:
    """Causal anchor-complete one-minute HLC3 VWAP on unadjusted prices.

    A missing expected minute invalidates subsequent VWAP observations in that
    session. Future gaps cannot alter earlier values. Price-bar usability and
    VWAP validity are separate, as zero cumulative volume is undefined.
    """
    result = minutes.copy().sort_values("timestamp").reset_index(drop=True)
    if result.empty or result.timestamp.duplicated().any():
        raise ValueError("minute data must be nonempty with unique timestamps")
    result["timestamp"] = pd.to_datetime(result.timestamp, utc=True)
    result["available_at"] = result.timestamp + pd.Timedelta(minutes=1)
    result["open_time"], result["close_time"] = result.timestamp, result.available_at
    result["session_date"] = result.session_date.astype(str)
    days = sorted(result.session_date.unique())
    holiday = holiday_sessions("ES", int(days[0][:4]), int(days[-1][:4]))
    calendar = {day: date.fromisoformat(day).weekday() < 5 and date.fromisoformat(day) not in holiday for day in days}
    result["calendar_valid"] = result.session_date.map(calendar).astype(bool)
    local = result.timestamp.dt.tz_convert(NY)
    clock = local.dt.hour * 60 + local.dt.minute
    local_dates = local.dt.strftime("%Y-%m-%d")
    same_date = local_dates.eq(result.session_date)
    previous_dates = result.session_date.map({day: (date.fromisoformat(day) - timedelta(days=1)).isoformat() for day in days})
    previous_date = local_dates.eq(previous_dates)
    allowed = (same_date & clock.lt(1020)) | (previous_date & clock.ge(1080))
    allowed &= ~((result.session_date < "2021-06-28") & same_date & clock.ge(975) & clock.lt(990))
    allowed &= result.timestamp.astype("int64").mod(60_000_000_000).eq(0)
    numeric = result[["open", "high", "low", "close", "volume"]].to_numpy(float)
    valid = np.isfinite(numeric).all(axis=1) & (numeric[:, :4] > 0).all(axis=1) & (numeric[:, 4] >= 0)
    valid &= (numeric[:, 1] >= numeric[:, [0, 3]].max(axis=1)) & (numeric[:, 2] <= numeric[:, [0, 3]].min(axis=1))
    valid &= (numeric[:, 1] >= numeric[:, 2])
    tick = result.get("tick_valid", pd.Series(True, index=result.index)).to_numpy(bool)
    result["usable"] = valid & tick & allowed.to_numpy() & result.calendar_valid.to_numpy() & result.contract.notna().to_numpy()
    previous = result.groupby("session_date", sort=False).timestamp.shift()
    first = previous.isna()
    anchors = {day: (pd.Timestamp(day, tz=NY) - pd.Timedelta(days=1) + pd.Timedelta(hours=18)).tz_convert("UTC") for day in days}
    expected_step = result.timestamp.sub(previous).eq(pd.Timedelta(minutes=1))
    historical_pause = ((result.session_date < "2021-06-28") & local.dt.hour.eq(16) & local.dt.minute.eq(30)
                        & result.timestamp.sub(previous).eq(pd.Timedelta(minutes=16)))
    step_valid = expected_step | historical_pause | (first & result.timestamp.eq(result.session_date.map(anchors)))
    first_contract = result.groupby("session_date", sort=False).contract.transform("first")
    prefix = (result.usable & step_valid & result.contract.eq(first_contract)).groupby(result.session_date, sort=False).cummin()
    result["anchor_prefix_complete"] = prefix
    hlc3 = (result.high + result.low + result.close) / 3
    numerator = (hlc3 * result.volume).groupby(result.session_date, sort=False).cumsum()
    volume = result.volume.groupby(result.session_date, sort=False).cumsum()
    result["cumulative_volume"] = volume
    result["vwap_valid"] = prefix & volume.gt(0)
    result["globex_vwap"] = (numerator / volume.where(volume.gt(0))).where(result.vwap_valid)
    result["vwap"] = result.globex_vwap
    result["vwap_segment"] = pd.factorize(result.session_date)[0]
    result = add_exact_slope(result, "globex_vwap", "vwap_valid", "vwap_segment")
    result["vwap_slope_15m"] = result.globex_vwap_slope_15m
    return result


def join_completed_features(bars3: pd.DataFrame, bars5: pd.DataFrame, bars1: pd.DataFrame) -> pd.DataFrame:
    """Last completed native values only; never use a currently forming bar."""
    left = bars3.copy()
    cloud_columns = ["available_at", "contract", "ema20", "ema50", "cloud_ready", "ema20_slope_15m", "ema50_slope_15m"]
    cloud = bars5.loc[bars5.contract.notna(), cloud_columns].rename(columns={"available_at": "cloud_available_at"})
    left = pd.merge_asof(left, cloud, left_on="available_at", right_on="cloud_available_at", by="contract", direction="backward")
    columns = ["available_at", "contract", "session_date", "globex_vwap", "vwap_valid", "vwap_slope_15m"]
    vwap = bars1.loc[bars1.contract.notna(), columns].rename(columns={"available_at": "vwap_available_at"})
    left = pd.merge_asof(left, vwap, left_on="available_at", right_on="vwap_available_at",
                         by=["contract", "session_date"], direction="backward")
    left["cloud_ready"] = left.cloud_ready.eq(True)
    left["vwap_valid"] = left.vwap_valid.eq(True)
    left["vwap"] = left.globex_vwap
    left["cloud_lower"] = left[["ema20", "ema50"]].min(axis=1)
    left["cloud_upper"] = left[["ema20", "ema50"]].max(axis=1)
    left["cloud_width"] = left.cloud_upper - left.cloud_lower
    left["cloud_spread"] = left.ema20 - left.ema50
    left["feature_ready"] = left.usable & left.ema6_ready & left.cloud_ready & left.vwap_valid
    return left


def session_quality(bars1: pd.DataFrame, bars3: pd.DataFrame) -> pd.DataFrame:
    """Saved full-session/anchor-to-16:00/RTH roster qualifications."""
    grouped = {str(day): rows for day, rows in bars1.groupby("session_date", sort=False)}
    records = []
    for day, bars in bars3.groupby("session_date", sort=True):
        rows = grouped.get(day)
        calendar_valid = bool(bars.calendar_valid.all())
        contracts = sorted(bars.contract.dropna().unique())
        nominal = 1365 if day < "2021-06-28" else 1380
        observed = len(rows) if rows is not None else 0
        if rows is not None:
            local = rows.timestamp.dt.tz_convert(NY)
            clock = local.dt.hour * 60 + local.dt.minute
            rth = rows[clock.ge(570) & clock.lt(960)]
            before_close = rows[local.dt.date.lt(date.fromisoformat(day)) | clock.lt(960)]
            rth_complete = len(rth) == 390 and bool(rth.usable.all())
            anchor_complete = len(before_close) == 1320 and bool(before_close.anchor_prefix_complete.all())
            full = observed == nominal and bool(rows.anchor_prefix_complete.all())
        else:
            rth_complete = anchor_complete = full = False
            before_close = []
        records.append({"session_date": day, "contract": contracts[0] if len(contracts) == 1 else None,
                        "calendar_valid": calendar_valid, "observed_minutes": observed,
                        "expected_full_globex_minutes": nominal,
                        "rth_complete": bool(calendar_valid and rth_complete),
                        "anchor_to_rth_end_complete": bool(calendar_valid and anchor_complete),
                        "full_globex_complete": bool(calendar_valid and full),
                        "missing_minutes_to_rth_end": max(0, 1320 - len(before_close)),
                        "last_available_at": rows.available_at.max() if rows is not None else pd.NaT,
                        "quality_reason": "" if calendar_valid and anchor_complete else "calendar_uncertified_or_incomplete_anchor_to_rth_end"})
    return pd.DataFrame(records)


def prepare_frames(root, *, cloud_manifest_path, cloud_manifest_sha256, minute_manifest_path,
                   minute_manifest_sha256, start_session="2020-01-01", end_session_exclusive="2026-10-31") -> dict:
    """Prepare new features using only the existing pinned ES publications."""
    root = Path(root).resolve()
    cloud_manifest = read_pinned_manifest(root, cloud_manifest_path, cloud_manifest_sha256, True)
    source_manifest = read_pinned_manifest(root, minute_manifest_path, minute_manifest_sha256, True)
    if source_manifest.get("dataset") != "volume_lead_unadjusted_v1" or source_manifest.get("adjusted") is not False:
        raise ValueError("unadjusted retained source required")
    bars3 = native_bars(load_cloud(root, product="ES", interval=3, manifest_path=cloud_manifest_path,
                                  expected_manifest_sha256=cloud_manifest_sha256), 3)
    bars5 = native_bars(load_cloud(root, product="ES", interval=5, manifest_path=cloud_manifest_path,
                                  expected_manifest_sha256=cloud_manifest_sha256), 5)
    bars3 = add_ema6(bars3)
    bars3 = add_exact_slope(bars3, "ema6", "ema6_ready", "ema6_segment")
    bars5["cloud_ready"] = bars5.usable & bars5.consecutive_count.ge(251)
    bars5["cloud_segment"] = bars5.feature_reset.cumsum()
    for line in ("ema20", "ema50"):
        bars5 = add_exact_slope(bars5, line, "cloud_ready", "cloud_segment")
    bar_records = [record for record in cloud_manifest["output_files"] if record.get("product") == "ES"]
    pattern = re.compile(r"data/curated/continuous/1m/product=ES/roll=volume_lead_v1/variant=unadjusted/year=([0-9]{4})/part-[^/]+\.parquet\Z")
    first_year, last_year = int(start_session[:4]), int(end_session_exclusive[:4])
    source_records = [record for record in source_manifest["output_files"]
                      if (match := pattern.fullmatch(record["path"])) and first_year <= int(match[1]) <= last_year]
    master_records = [record for record in source_manifest["output_files"] if record["path"].endswith("/instrument_master.parquet")]
    if len(master_records) != 1 or not source_records:
        raise ValueError("required retained minute/master records absent")
    paths = selected_files(root, source_manifest, lambda name: name in {r["path"] for r in source_records + master_records}, verify=True)
    path_by_name = {str(path.relative_to(root)): path for path in paths}
    master = pq.ParquetFile(path_by_name[master_records[0]["path"]]).read().to_pandas()
    master = master[master["product"].eq("ES")].set_index("roll_id")
    columns = ["ts_event", "session_date", "instrument_id", "raw_symbol", "roll_id", "open", "high", "low", "close", "volume", "source_batch"]
    minutes = pa.concat_tables([pq.ParquetFile(path_by_name[r["path"]]).read(columns=columns) for r in source_records]).to_pandas()
    minutes["session_date"] = minutes.session_date.astype(str)
    minutes = minutes[minutes.session_date.ge(start_session) & minutes.session_date.lt(end_session_exclusive)].copy()
    minutes.rename(columns={"ts_event": "timestamp"}, inplace=True)
    mapped = master.reindex(minutes.roll_id)
    if not np.array_equal(mapped.instrument_id.to_numpy(), minutes.instrument_id.to_numpy()) or not np.array_equal(mapped.raw_symbol.to_numpy(), minutes.raw_symbol.to_numpy()):
        raise ValueError("retained minute delivery identity does not match master")
    minutes["contract"] = [f"ES{MONTHS[int(month)]}{int(year):04d}" for month, year in zip(mapped.maturity_month, mapped.maturity_year)]
    minutes["tick_valid"] = np.logical_and.reduce([minutes[line].to_numpy(dtype=np.int64) % 250_000_000 == 0 for line in ("open", "high", "low", "close")])
    for line in ("open", "high", "low", "close"):
        minutes[line] = minutes[line].to_numpy(float) * 1e-9
    bars1 = derive_minute_vwap(minutes)
    bars3 = bars3[bars3.session_date.ge(start_session) & bars3.session_date.lt(end_session_exclusive)].reset_index(drop=True)
    bars5 = bars5[bars5.session_date.ge(start_session) & bars5.session_date.lt(end_session_exclusive)].reset_index(drop=True)
    bars3 = join_completed_features(bars3, bars5, bars1)
    quality = session_quality(bars1, bars3)
    return {"bars1": bars1, "bars3": bars3, "bars5": bars5, "quality": quality,
            "input_files": [*bar_records, *source_records, *master_records],
            "input_manifests": [{"path": str(cloud_manifest_path), "sha256": cloud_manifest_sha256},
                                {"path": str(minute_manifest_path), "sha256": minute_manifest_sha256}],
            "reused_5m_ema_values": True,
            "qualifications": ["Retained volume-lead contract fragments only; no new data acquired.",
                               "Existing cloud values unchanged; readiness requires 250 preceding bars, current bar excluded.",
                               "Historical calendar exclusions and unknown gaps remain unusable; annual exchange certification and native chart parity are unverified."]}


def build_release(root, *, release_id, request_path="requests/inbox/es_contract_session_indicators__1.0.0.yaml", **settings) -> Path:
    """Publish this new ES-only release once; never overwrite any final output."""
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", release_id):
        raise ValueError("unsafe release id")
    destination = root / "data/features/es_contract_session_indicators/version=1.0.0"
    manifest_path = root / f"catalog/datasets/{DATASET_ID}.json"
    schema_path = root / f"catalog/schemas/{DATASET_ID}.json"
    quality_path = root / f"reports/quality/{DATASET_ID}.md"
    stage = root / "data/staging/es_contract_session_indicators" / release_id
    for path in (destination, manifest_path, schema_path, quality_path, stage):
        check_absent(path, root)
    stage.mkdir(parents=True)
    declared = publication_sources(Path(__file__).resolve(), ("calendar.py", "ema_cloud_loader_v2.py", "ema_cloud.py", "manifest_selection.py", "provenance.py", "publication_safety.py"), workspace=root)
    declared.append((request_path, root / request_path))
    retained = retain_sources(stage / "provenance", declared, artifact_id=DATASET_ID, root=root)
    frames = prepare_frames(root, **settings)
    files, schemas = [], {}
    for table in TABLES:
        output = stage / f"table={table}/part-000.parquet"
        output.parent.mkdir()
        arrow = pa.Table.from_pandas(frames[table], preserve_index=False)
        pq.write_table(arrow, output, compression="zstd")
        final_path = destination / output.relative_to(stage)
        files.append({"path": str(final_path.relative_to(root)), "sha256": sha256_file(output),
                      "bytes": output.stat().st_size, "rows": len(frames[table]), "table": table})
        schemas[table] = [{"name": field.name, "type": str(field.type)} for field in arrow.schema]
    verify_retained_sources(stage / "provenance", declared, retained)
    metadata = {"dataset_id": DATASET_ID, "version": VERSION, "release_id": release_id,
                "created_at": datetime.now(timezone.utc).isoformat(), "product": "ES", **git_version(root),
                "settings": settings, "source_manifest_pins": frames["input_manifests"],
                "input_files": frames["input_files"], "output_files": files,
                "schema_path": str(schema_path.relative_to(root)), "quality_report_path": str(quality_path.relative_to(root)),
                "qualifications": frames["qualifications"], "reused_5m_ema_values": True,
                "market_outcomes_computed": False, "data_acquired": False,
                "coverage_start_session": frames["quality"].session_date.min(),
                "coverage_end_session": frames["quality"].session_date.max(),
                "provenance": retained}
    schema_bytes = (json.dumps({"dataset_id": DATASET_ID, "tables": schemas}, indent=2) + "\n").encode()
    q = frames["quality"]
    quality_bytes = (f"# Retained ES session indicators 1.0.0\n\nNew ES-only delivery; existing releases unchanged. No external acquisition or market outcomes.\n\n"
                     f"Coverage: {q.session_date.min()} through {q.session_date.max()}. Sessions: {len(q)}; complete anchor-to-16:00 rosters: {int(q.anchor_to_rth_end_complete.sum())}.\n\n"
                     + "\n\n".join(frames["qualifications"]) + "\n").encode()
    for path in (destination, manifest_path, schema_path, quality_path):
        check_absent(path, root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(stage), str(destination))
    write_new_bytes(schema_path, schema_bytes, root)
    write_new_bytes(quality_path, quality_bytes, root)
    metadata["auxiliary_files"] = []
    for path in [schema_path, quality_path, *sorted((destination / "provenance").rglob("*"))]:
        if path.is_file():
            metadata["auxiliary_files"].append({"path": str(path.relative_to(root)), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_new_bytes(manifest_path, (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode(), root)
    return manifest_path


def load_release(root, manifest_path, expected_manifest_sha256, *, table="bars3", verify_selected_files=True):
    """Load one explicitly pinned newly published table; no repair or discovery."""
    if table not in TABLES:
        raise ValueError("unsupported ES indicator table")
    manifest = read_pinned_manifest(root, manifest_path, expected_manifest_sha256, verify_selected_files)
    if manifest.get("dataset_id") != DATASET_ID or manifest.get("version") != VERSION:
        raise ValueError("unsupported ES indicator release")
    records = [record for record in manifest["output_files"] if record.get("table") == table]
    if len(records) != 1:
        raise ValueError("release must declare one requested table")
    files = selected_files(Path(root), manifest, lambda name: name == records[0]["path"], verify=verify_selected_files)
    result = pq.ParquetFile(files[0]).read().to_pandas()
    if len(result) != records[0]["rows"]:
        raise ValueError("ES indicator table row count mismatch")
    return result
