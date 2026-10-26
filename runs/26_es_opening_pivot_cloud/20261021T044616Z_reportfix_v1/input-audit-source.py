"""Pinned, read-only inputs and retrospective session eligibility for study 26.

This module audits inputs only. It neither generates candidates nor computes P&L.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from importlib import import_module
import hashlib
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow.compute as pc

from abacus_bhishma.calendar import holiday_sessions
from abacus_bhishma.continuous_loader import open_continuous_dataset, price_to_float
from abacus_bhishma.ema_cloud_loader_v2 import load_release as load_cloud
from abacus_bhishma.paths import load_workspace_paths

NY = ZoneInfo("America/New_York")
YEARS = {2022: ("6.0.0", "verniman_history_2022"),
         2023: ("5.0.0", "verniman_history_2023"),
         2024: ("4.0.0", "verniman_history_2024"),
         2025: ("3.0.0", "verniman_history_2025"),
         2026: ("2.0.0", "verniman_history")}
MONTH_CODES = "FGHJKMNQUVXZ"
INSPIRATION_DATE = "2026-09-15"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_quoted_contract(value: str) -> str | None:
    """Decode the literal quoted ES delivery year; never infer it from price."""
    match = re.fullmatch(r"/?ES([FGHJKMNQUVXZ])(\d{2}|\d{4})", str(value).upper())
    if not match:
        return None
    code, year = match.groups()
    year = int(year) + (2000 if len(year) == 2 else 0)
    return f"ES{code}{year}"


def canonical_feature_contract(value: str) -> str | None:
    """Use published maturity year/month, not Databento's one-digit suffix."""
    fields = str(value).split(":")
    try:
        if len(fields) != 5 or fields[0] != "ES":
            return None
        year, month = int(fields[2]), int(fields[3])
        return f"ES{MONTH_CODES[month - 1]}{year}" if 1 <= month <= 12 else None
    except (ValueError, IndexError):
        return None


def build_plan(outlooks: list[dict], levels: list[dict]) -> tuple[dict | None, str]:
    """Skip every duplicate source date, even if only one row parsed completely."""
    if not outlooks:
        return None, "no_source_levels"
    if len(outlooks) != 1:
        return None, "ambiguous_duplicate_source_date"
    outlook = outlooks[0]
    if (outlook.get("content_kind") != "daily_outlook"
            or outlook.get("extraction_status") != "complete"
            or outlook.get("parsed_branch_count") != 2):
        return None, "incomplete_daily_plan"
    own = [row for row in levels if row["outlook_id"] == outlook["outlook_id"]]
    triggers = [row for row in own if row["role"] == "trigger"]
    if Counter(row["side"] for row in triggers) != {"bullish": 1, "bearish": 1}:
        return None, "incomplete_daily_plan"
    if not canonical_quoted_contract(outlook["contract"]):
        return None, "unresolved_quoted_contract"
    if any(row["contract"] != outlook["contract"] for row in own):
        return None, "conflicting_plan_contract"
    if outlook.get("available_at") is not None or any(row.get("available_at") is not None for row in own):
        raise ValueError("Unexpected verified availability: requires separately frozen cohort")
    lower = min(float(row["price_low"]) for row in triggers)
    upper = max(float(row["price_high"]) for row in triggers)
    if not (math.isfinite(lower) and math.isfinite(upper) and 0 < lower <= upper):
        return None, "invalid_pivot_bounds"
    descriptions = list(dict.fromkeys(row["source_label"] for row in triggers))
    known = {"YVAL", "YPOC", "YVAH", "HVE", "PBT", "GAP", "VPOC", "ONH", "ONL", "YHOD", "YLOD"}
    labels = set()
    for label in descriptions:
        tokens = set(re.split(r"[^A-Z0-9]+", label.upper()))
        recognized = tokens & known
        labels.update(recognized or {"UNKNOWN"})
    targets = {}
    for source_side, side in (("bullish", "long"), ("bearish", "short")):
        selected = sorted((row for row in own if row["role"] == "target" and row["side"] == source_side),
                          key=lambda row: row["ordinal"])[:2]
        targets[side] = [dict(lower=float(row["price_low"]), upper=float(row["price_high"]),
                             description=row["source_label"], source_text=row["source_text"],
                             ordinal=int(row["ordinal"]), source_row_id=row.get("source_row_id")) for row in selected]
    return dict(pivot_lower=lower, pivot_upper=upper, description=" + ".join(descriptions),
                label_group="+".join(sorted(labels)), original_descriptions=descriptions,
                pivot_source_texts=[row["source_text"] for row in triggers],
                pivot_is_zone=lower != upper, targets=targets, quoted_contract=outlook["contract"],
                canonical_contract=canonical_quoted_contract(outlook["contract"]),
                outlook_id=outlook["outlook_id"], source_url=outlook["source_url"],
                source_post_id=outlook["source_post_id"], available_at=None,
                timing_status=outlook["timing_status"],
                source_rows=[_plain(row) for row in own], source_outlook=_plain(outlook)), ""


def independent_feature_audit(frame: pd.DataFrame) -> dict:
    """Independent scalar recurrence over all retained history, without calling producer math."""
    errors = {"ema20": 0.0, "ema50": 0.0, "atr14": 0.0}
    mismatches = Counter()
    prior_contract = prior_close = prior_time = None
    e20 = e50 = atr = None
    count = 0
    seed = []
    checked = 0
    representatives = []
    selected_years = set()
    for row in frame.itertuples(index=False):
        valid = bool(row.usable) and row.contract is not None and not pd.isna(row.contract)
        unknown_gap = (prior_time is not None and row.timestamp - prior_time > pd.Timedelta(minutes=5)
                       and not bool(row.known_closure_before))
        switch = prior_contract is not None and row.contract != prior_contract
        reset = (not valid) or count == 0 or unknown_gap or switch
        if bool(row.feature_reset) != reset:
            mismatches["feature_reset"] += 1
        if pd.Timestamp(row.available_at) != pd.Timestamp(row.timestamp) + pd.Timedelta(minutes=5):
            mismatches["available_at"] += 1
        if not valid:
            e20 = e50 = atr = prior_close = prior_contract = None
            seed, count = [], 0
            prior_time = row.timestamp
            if row.feature_valid:
                mismatches["feature_valid"] += 1
            if any(not pd.isna(getattr(row, key)) for key in errors):
                mismatches["invalid_slot_nulls"] += 1
            continue
        if reset:
            e20 = e50 = atr = prior_close = None
            seed, count = [], 0
        close, high, low = float(row.close), float(row.high), float(row.low)
        tr = high - low if prior_close is None else max(high - low, abs(high - prior_close), abs(low - prior_close))
        # Numerically equivalent recurrence, written independently from producer.
        e20 = close if e20 is None else e20 + (2 / 21) * (close - e20)
        e50 = close if e50 is None else e50 + (2 / 51) * (close - e50)
        count += 1
        if count <= 14:
            seed.append(tr)
            if count == 14:
                atr = sum(seed) / 14
        else:
            atr += (tr - atr) / 14
        for key, expected in (("ema20", e20), ("ema50", e50), ("atr14", atr)):
            actual = getattr(row, key)
            if expected is None:
                mismatches[key] += int(not pd.isna(actual))
            elif pd.isna(actual):
                mismatches[key] += 1
            else:
                error = abs(float(actual) - expected)
                errors[key] = max(errors[key], error)
                mismatches[key] += int(error > 1e-8)
        mismatches["consecutive_count"] += int(row.consecutive_count != count)
        mismatches["feature_valid"] += int(bool(row.feature_valid) != (count >= 250))
        checked += 1
        ny = row.timestamp.tz_convert(NY)
        if ny.year >= 2022 and ny.hour == 9 and ny.minute == 25:
            inspired = ny.date().isoformat() == INSPIRATION_DATE
            if inspired or (count >= 250 and ny.year not in selected_years):
                representatives.append(dict(time=ny.isoformat(), available_at=row.available_at.isoformat(),
                                            contract=row.contract, consecutive_count=count, feature_valid=count >= 250,
                                            ema20=float(row.ema20), ema50=float(row.ema50), atr14=float(row.atr14)))
                selected_years.add(ny.year)
        prior_contract, prior_close, prior_time = row.contract, close, row.timestamp
    result = dict(status="passed" if not any(mismatches.values()) else "failed",
                  scope="All retained ES 5-minute slots, full-history independent scalar recurrences and reset/readiness/timing checks",
                  scheduled_rows=len(frame), usable_rows_checked=checked, tolerance=1e-8,
                  max_absolute_error=errors, mismatch_counts=dict(mismatches), representatives=representatives,
                  native_tradingview_parity="not_established")
    if result["status"] != "passed":
        raise ValueError(f"Independent feature audit failed: {result}")
    return result


def _plain(row: dict) -> dict:
    """JSON-safe source retention preserves nulls, exact decimal strings and timing."""
    result = {}
    for key, value in row.items():
        if value is None:
            result[key] = None
        elif isinstance(value, (date, datetime, pd.Timestamp)):
            result[key] = value.isoformat()
        elif isinstance(value, (str, int, float, bool)):
            result[key] = value
        else:
            result[key] = str(value)
    return result


def _bar(row: dict) -> dict:
    timestamp = row["timestamp"].tz_convert(NY).to_pydatetime()
    names = ["open", "high", "low", "close", "ema20", "ema50", "atr14", "ema20_lag3", "ema50_lag3"]
    result = {key: float(row[key]) if not pd.isna(row[key]) else None for key in names}
    return dict(time=timestamp, open_time=timestamp, available_at=row["available_at"].tz_convert(NY).to_pydatetime(),
                contract=row["contract"], raw_symbol=row["raw_symbol"], lineage=row["lineage"],
                feature_valid=bool(row["feature_valid"]), consecutive_count=int(row["consecutive_count"]), **result)


def audit_session(day: date, outlooks: list[dict], levels: list[dict], features: pd.DataFrame,
                  minutes: pd.DataFrame, *, calendar_event: str = "", cash_session: bool = True) -> tuple[dict, dict]:
    """Fixed-window input gate; no rule depends on signals or later returns."""
    day_string = day.isoformat()
    plan, plan_reason = build_plan(outlooks, levels)
    feature_times = [pd.Timestamp(datetime.combine(day, time(9, 10)), tz=NY) + pd.Timedelta(minutes=5 * i) for i in range(10)]
    minute_times = pd.date_range(pd.Timestamp(datetime.combine(day, time(9, 30)), tz=NY), periods=90, freq="min")
    f = features.set_index("timestamp", drop=False) if not features.empty else features
    m = minutes.set_index("timestamp", drop=False) if not minutes.empty else minutes
    unique_features = not features.empty and not features.timestamp.duplicated().any()
    unique_minutes = not minutes.empty and not minutes.timestamp.duplicated().any()
    feature_present = unique_features and all(t.tz_convert("UTC") in f.index for t in feature_times)
    minute_present = unique_minutes and all(t.tz_convert("UTC") in m.index for t in minute_times)
    selected = f.loc[[t.tz_convert("UTC") for t in feature_times]] if feature_present else features.iloc[:0]
    selected_minutes = m.loc[minute_times.tz_convert("UTC")] if minute_present else minutes.iloc[:0]
    calendar_certified = bool(cash_session and not calendar_event)
    usable = bool(feature_present and selected.usable.all() and selected.calendar_valid.all())
    readiness = bool(usable and selected.feature_valid.all() and selected.consecutive_count.ge(250).all()
                     and np.isfinite(selected[["ema20", "ema50", "atr14", "ema20_lag3", "ema50_lag3"]].to_numpy(dtype=float)).all())
    contracts = set(selected.contract.dropna()) if feature_present else set()
    quote_match = bool(plan and len(contracts) == 1 and canonical_feature_contract(next(iter(contracts))) == plan["canonical_contract"])
    complete_execution = bool(minute_present)
    if complete_execution:
        values = selected_minutes[["open", "high", "low", "close"]].to_numpy(dtype=float)
        complete_execution = bool(np.isfinite(values).all() and (values > 0).all()
                                  and (values[:, 1] >= values[:, [0, 3]].max(axis=1)).all()
                                  and (values[:, 2] <= values[:, [0, 3]].min(axis=1)).all())
        if quote_match:
            contract = next(iter(contracts)).split(":")
            complete_execution &= bool(selected_minutes.instrument_id.eq(int(contract[1])).all()
                                       and selected_minutes.raw_symbol.eq(contract[4]).all())
    reason = ("cash_session_closed" if not cash_session else "published_calendar_uncertified" if not calendar_certified
              else plan_reason if plan_reason else "contract_mismatch" if not quote_match
              else "unusable_opening_bars" if not usable else "feature_not_ready" if not readiness
              else "incomplete_execution_window" if not complete_execution else "")
    # Preserve original level rows in every plan, even when another gate excludes it.
    ledger = dict(date=day_string, year=day.year, exchange_session=cash_session, calendar_event=calendar_event,
                  calendar_certified=calendar_certified, source_levels=bool(outlooks), source_post_count=len(outlooks),
                  unique_complete_plan=plan is not None, ambiguous_duplicate_date=len(outlooks) > 1,
                  quote_contract_match=quote_match, usable_opening_bars=usable, ema_atr_ready=readiness,
                  complete_execution_data=complete_execution, input_eligible=not bool(reason), exclusion_reason=reason,
                  quoted_contract=plan["quoted_contract"] if plan else None,
                  actual_contract=next(iter(contracts)) if len(contracts) == 1 else None,
                  opening_feature_min_count=int(selected.consecutive_count.min()) if feature_present else None,
                  available_at=None, verified_preopen_available=False, inspired_date=day_string == INSPIRATION_DATE)
    bars = []
    chart_bars = []
    if not features.empty:
        for row in features.to_dict("records"):
            ny = row["timestamp"].tz_convert(NY)
            if time(9, 25) <= ny.time() <= time(9, 55):
                bars.append(_bar(row))
            if time(9, 25) <= ny.time() <= time(10, 5):
                chart_bars.append(_bar(row))
    minute_rows = []
    if minute_present:
        for row in selected_minutes.to_dict("records"):
            minute_rows.append(dict(time=row["timestamp"].tz_convert(NY).to_pydatetime(),
                                    **{key: float(row[key]) for key in ("open", "high", "low", "close")},
                                    raw_symbol=row["raw_symbol"], instrument_id=int(row["instrument_id"])))
    return dict(date=day_string, plan=plan, bars5=bars, minutes=minute_rows, chart_bars=chart_bars,
                eligible=not bool(reason), reason=reason, inspired_date=ledger["inspired_date"],
                calendar_event=calendar_event, source_rows=[_plain(row) for row in levels]), ledger


def coverage_waterfall(rows: list[dict]) -> list[dict]:
    result = []
    stages = [("exchange_sessions_in_scope", "exchange_session"), ("calendar_certified_sessions", "calendar_certified"),
              ("dates_with_source_levels", "source_levels"), ("unique_complete_daily_plans", "unique_complete_plan"),
              ("quote_contract_matches", "quote_contract_match"), ("usable_opening_bars", "usable_opening_bars"),
              ("ema_atr_readiness", "ema_atr_ready"), ("complete_execution_data", "complete_execution_data"),
              ("final_input_eligible_sessions", "input_eligible")]
    for year in range(2022, 2027):
        population = [row for row in rows if row["year"] == year]
        surviving = population
        for stage, key in stages:
            before = len(surviving)
            surviving = [row for row in surviving if row[key]]
            result.append(dict(year=year, stage=stage, sessions=len(surviving), removed=before - len(surviving),
                               ambiguous_duplicate_dates=sum(row["ambiguous_duplicate_date"] for row in population if row["exchange_session"]),
                               partial_year=year in (2022, 2026)))
    return result


def load_inputs(workspace_root: Path | str, lock_path: Path | str | None = None, *, verify_features: bool = True) -> dict:
    """Load pinned public releases and return all nominal weekdays and exclusion rows."""
    paths = load_workspace_paths(workspace_root)
    study = paths.workspace_root / "studies/26_es_opening_pivot_cloud"
    lock = json.loads(Path(lock_path or study / "inputs.lock.json").read_text())
    publication = paths.publication_root
    if lock.get("schema_version") != "opening-pivot-cloud-inputs/v1":
        raise ValueError("Unsupported input lock")
    for record in lock["manifests"]:
        if sha256(publication / record["path"]) != record["sha256"]:
            raise ValueError(f"Manifest pin mismatch: {record['path']}")
    records = {record["dataset_id"]: record for record in lock["manifests"]}
    all_outlooks, all_levels = [], []
    verified_source_files = []
    for year, (version, module_name) in YEARS.items():
        record = records[f"verniman_daily_levels__{version}"]
        module = import_module(f"abacus_bhishma.{module_name}")
        manifest = module.verify_release(publication, record["path"], record["sha256"], verify_bytes=True)
        # The supported loader is used for each consumed table. Full bytes were
        # just checked once; the second pass retains contract/schema validation.
        outlooks = module.load_release(publication, record["path"], record["sha256"], table="outlooks", verify_bytes=False).to_pylist()
        levels = module.load_release(publication, record["path"], record["sha256"], table="levels", verify_bytes=False).to_pylist()
        for index, row in enumerate(outlooks):
            row["source_row_id"] = f"{record['dataset_id']}:outlooks:{index + 1}"
        for index, row in enumerate(levels):
            row["source_row_id"] = f"{record['dataset_id']}:levels:{index + 1}"
        if any(row["session_date"] is not None and row["session_date"].year != year for row in outlooks):
            raise ValueError("Annual source release contains an unexpected source-session year")
        all_outlooks.extend(outlooks)
        all_levels.extend(levels)
        verified_source_files.extend([*manifest["files"], manifest["crawl_manifest"], manifest["request"], *manifest["raw_files"]])
    cloud_pin = records["same_contract_ema_cloud__1.1.0"]
    cloud = load_cloud(publication, product="ES", interval=5, manifest_path=cloud_pin["path"],
                       expected_manifest_sha256=cloud_pin["sha256"], verify_selected_files=True)
    parity = independent_feature_audit(cloud) if verify_features else {"status": "not_run", "reason": "explicit caller option"}
    cloud["ema20_lag3"] = cloud.ema20.shift(3)
    cloud["ema50_lag3"] = cloud.ema50.shift(3)
    base_pin = records["volume_lead_unadjusted_v1"]
    dataset = open_continuous_dataset(publication, "ES", "unadjusted", manifest_path=base_pin["path"],
                                      expected_manifest_sha256=base_pin["sha256"], verify_selected_files=True)
    base_manifest = json.loads((publication / base_pin["path"]).read_text())
    cutoff = min(pd.Timestamp(base_manifest["products"]["ES"]["coverage_end"]).tz_convert(NY).date(),
                 cloud.timestamp.iloc[-1].tz_convert(NY).date(), max(row["session_date"] for row in all_outlooks if row["session_date"]))
    start = date(2022, 1, 1)
    source = dataset.to_table(filter=pc.field("year") >= 2022,
                              columns=["ts_event", "session_date", "instrument_id", "raw_symbol", "open", "high", "low", "close", "volume"]).to_pandas()
    source = source.rename(columns={"ts_event": "timestamp"})
    for field in ("open", "high", "low", "close"):
        source[field] = price_to_float(source[field])
    ny = source.timestamp.dt.tz_convert(NY)
    source = source.loc[(ny.dt.hour * 60 + ny.dt.minute).between(9 * 60 + 10, 11 * 60 - 1)].copy()
    source["date"] = source.timestamp.dt.tz_convert(NY).dt.date
    cloud_ny = cloud.timestamp.dt.tz_convert(NY)
    cloud_window = cloud.loc[(cloud_ny.dt.hour * 60 + cloud_ny.dt.minute).between(9 * 60 + 10, 10 * 60 + 5)].copy()
    cloud_window["date"] = cloud_window.timestamp.dt.tz_convert(NY).dt.date
    grouped_cloud = {key: value for key, value in cloud_window.groupby("date")}
    grouped_source = {key: value for key, value in source.groupby("date")}
    grouped_outlooks, grouped_levels = defaultdict(list), defaultdict(list)
    for row in all_outlooks:
        grouped_outlooks[row["session_date"]].append(row)
    for row in all_levels:
        grouped_levels[row["session_date"]].append(row)
    holidays = holiday_sessions("ES", 2022, 2026)
    sessions, ledger = [], []
    for day in pd.date_range(start, cutoff, freq="B"):
        day = day.date()
        events = holidays.get(day, [])
        cash_session = not any("early close" not in event for event in events)
        session, row = audit_session(day, grouped_outlooks[day], grouped_levels[day],
                                    grouped_cloud.get(day, cloud_window.iloc[:0]), grouped_source.get(day, source.iloc[:0]),
                                    calendar_event=";".join(events), cash_session=cash_session)
        sessions.append(session)
        ledger.append(row)
    # Independent source-price aggregation for every retained eligible opening bar.
    aggregation_errors = Counter()
    aggregate = source.assign(bucket=source.timestamp.dt.floor("5min")).groupby("bucket").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), n=("open", "size"))
    aggregate_checked = 0
    for session in sessions:
        if not session["eligible"]:
            continue
        for bar in session["bars5"]:
            stamp = pd.Timestamp(bar["time"]).tz_convert("UTC")
            if stamp not in aggregate.index or aggregate.loc[stamp, "n"] != 5:
                aggregation_errors["source_count"] += 1
                continue
            for field in ("open", "high", "low", "close"):
                aggregation_errors[field] += int(abs(bar[field] - aggregate.loc[stamp, field]) > 1e-8)
            aggregate_checked += 1
    if any(aggregation_errors.values()):
        raise ValueError(f"Opening aggregation audit failed: {aggregation_errors}")
    parity["opening_aggregation"] = dict(status="passed", bars_checked=aggregate_checked,
                                        tolerance=1e-8, mismatch_counts=dict(aggregation_errors))
    source_dates = sorted(row["session_date"] for row in all_outlooks if row["session_date"] and row["session_date"] <= cutoff)
    actual_eligible = [row["date"] for row in ledger if row["input_eligible"]]
    inspiration = next(row for row in ledger if row["date"] == INSPIRATION_DATE)
    audit = dict(requested_start="2022-01-01", actual_cutoff=cutoff.isoformat(), observed_level_start=source_dates[0].isoformat(),
                 final_eligible_start=min(actual_eligible) if actual_eligible else None,
                 final_eligible_end=max(actual_eligible) if actual_eligible else None,
                 nominal_weekdays=len(ledger), eligible_sessions=len(actual_eligible),
                 exclusions=dict(Counter(row["exclusion_reason"] for row in ledger if row["exclusion_reason"])),
                 source_availability="historical_availability_unverified; all available_at values remain null",
                 verified_preopen_availability_sessions=0, feature_audit=parity, inspiration_date=inspiration,
                 minute_completeness="09:30–10:59 inclusive, 90 unique valid one-minute bars; flatten 10:59 close available 11:00",
                 feature_completeness="09:10–09:55 inclusive, 10 usable 250-bar-ready feature slots; lag3 computed globally",
                 calendar_policy="Pinned Bhishma cash holiday rules; shortened and uncertified sessions excluded under published cloud policy",
                 verified_verne_artifact_records=len(verified_source_files),
                 source_row_count=len(all_levels), outlook_row_count=len(all_outlooks))
    return dict(sessions=sessions, coverage=ledger, waterfall=coverage_waterfall(ledger), audit=audit)
