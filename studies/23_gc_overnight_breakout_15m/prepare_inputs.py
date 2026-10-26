"""Freeze and audit Phase 1 inputs without computing strategy outcomes.

This is a study consumer of an immutable Bhishma release, not a data publisher.
It preserves prices and distinguishes expected closures from omitted trade bars.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from abacus_bhishma.continuous_loader import open_continuous_dataset, price_to_float
from abacus_bhishma.ema_cloud import expected_minutes
from abacus_bhishma.paths import load_workspace_paths

STUDY_ID = "23_gc_overnight_breakout_15m"
MANIFEST_PATH = "catalog/datasets/volume_lead_unadjusted_v1.json"
START = pd.Timestamp("2017-12-31T21:00:00Z")
END = pd.Timestamp("2026-09-18T21:00:00Z")
BROKER = "Etc/GMT-3"
TICK_FIXED = 100_000_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def descriptor(root: Path, relative: str, role: str) -> dict:
    path = root / relative
    return dict(path=relative, root_alias="publication_root", role=role,
                bytes=path.stat().st_size, sha256=sha256(path))


def validate_contracts(source: pd.DataFrame, master: pd.DataFrame,
                       rolls: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Reconcile selected published minute identity to published roll/master bytes.

    Composite contract identity includes maturity because historical numeric IDs
    and decade-shortened symbols can be reused. Raw reconstruction is separate.
    """
    fields = ["product", "roll_id", "instrument_id", "raw_symbol", "maturity_year",
              "maturity_month", "mapping_start", "mapping_end", "instrument_class",
              "min_price_increment"]
    joined = source.merge(master[fields], on=["product", "roll_id"], how="left",
                          suffixes=("", "_master"), validate="many_to_one")
    mismatch = ((joined.instrument_id != joined.instrument_id_master)
                | (joined.raw_symbol != joined.raw_symbol_master)
                | joined.maturity_year.isna() | joined.instrument_class.ne("F")
                | (joined.mapping_start != joined.mapping_start_master)
                | (joined.mapping_end != joined.mapping_end_master))
    sessions = pd.to_datetime(joined.session_date)
    bounds = ((sessions < pd.to_datetime(joined.mapping_start))
              | (sessions >= pd.to_datetime(joined.mapping_end)))
    selected_rolls = rolls.loc[rolls["product"].eq("GC")].set_index("roll_id")
    support = joined.roll_id.gt(0)
    roll_bad = (joined.loc[support, "instrument_id"].to_numpy()
                != selected_rolls.loc[joined.loc[support, "roll_id"], "new_instrument_id"].to_numpy())
    duplicates = int(source.ts_event.duplicated(keep=False).sum())
    if mismatch.any() or bounds.any() or roll_bad.any() or duplicates:
        raise ValueError("published minute identity, mapping, roll, or duplicate failure")
    if not joined.min_price_increment.eq(TICK_FIXED).all():
        raise ValueError("selected GC master does not uniformly declare the verified 0.1 tick")
    prices = joined[["open", "high", "low", "close"]].to_numpy(dtype=np.int64)
    invalid = ((prices <= 0).any(axis=1) | (prices[:, 1] < prices[:, 0])
               | (prices[:, 1] < prices[:, 3]) | (prices[:, 2] > prices[:, 0])
               | (prices[:, 2] > prices[:, 3]) | (prices[:, 1] < prices[:, 2])
               | joined.volume.lt(0).to_numpy())
    tick_invalid = ((prices % TICK_FIXED) != 0).any(axis=1)
    transformed = source.rename(columns={"ts_event": "timestamp"}).copy()
    transformed["source_valid"] = ~(invalid | tick_invalid)
    transformed["contract"] = [f"GC:{int(i)}:{int(y)}:{int(m)}:{s}" for i, y, m, s in
        zip(joined.instrument_id, joined.maturity_year, joined.maturity_month, joined.raw_symbol)]
    transformed["available_at"] = transformed.timestamp + pd.Timedelta(minutes=1)
    for name in ("open", "high", "low", "close"):
        transformed[name + "_fixed"] = source[name].to_numpy()
        transformed[name] = price_to_float(source[name])
    return transformed, dict(status="passed", rows=len(source), identity_mismatches=0,
        mapping_bound_failures=0, roll_schedule_mismatches=0, duplicate_timestamps=0,
        invalid_ohlcv_rows=int(invalid.sum()), tick_deviation_rows=int(tick_invalid.sum()),
        contract_count=int(transformed.contract.nunique()),
        contract_multiplier_master_sentinel_values=sorted(master.loc[master["product"].eq("GC"), "contract_multiplier"].unique().tolist()))


def aggregate_15m(minutes: pd.DataFrame, schedule: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Fixed UTC quarter-hours equal fixed GMT+3 wall-clock quarter-hours.

    Retain missing/unusable nominal slots; never synthesize prices. Independent
    integer NumPy reductions reconcile every observed aggregate, not just a sample.
    """
    source = minutes.loc[minutes.timestamp.isin(schedule.timestamp)].copy()
    source["bucket"] = source.timestamp.dt.floor("15min")
    roster = schedule.copy()
    roster["bucket"] = roster.timestamp.dt.floor("15min")
    expected = roster.groupby("bucket", sort=True).agg(
        expected_count=("timestamp", "size"), calendar_valid=("calendar_valid", "all"),
        calendar_event=("calendar_event", lambda x: ";".join(sorted(set(x) - {""}))))
    agg = source.groupby("bucket", sort=True).agg(
        open_fixed=("open_fixed", "first"), high_fixed=("high_fixed", "max"),
        low_fixed=("low_fixed", "min"), close_fixed=("close_fixed", "last"),
        volume=("volume", "sum"), observed_count=("timestamp", "size"),
        contract=("contract", "first"), contract_count=("contract", "nunique"),
        raw_symbol=("raw_symbol", "first"), roll_id=("roll_id", "first"),
        source_valid=("source_valid", "all"), contains_roll=("is_roll", "any"))
    # An independent array reduction follows sorted minute groups. Compare fixed
    # integers before conversion so floating-point tolerances cannot hide drift.
    buckets = source.bucket.astype("int64").to_numpy()
    starts = np.r_[0, np.flatnonzero(np.diff(buckets)) + 1] if len(source) else np.array([], dtype=int)
    ends = np.r_[starts[1:] - 1, len(source) - 1] if len(source) else np.array([], dtype=int)
    checks = {"open_fixed": source.open_fixed.to_numpy()[starts],
              "high_fixed": np.maximum.reduceat(source.high_fixed.to_numpy(), starts),
              "low_fixed": np.minimum.reduceat(source.low_fixed.to_numpy(), starts),
              "close_fixed": source.close_fixed.to_numpy()[ends],
              "volume": np.add.reduceat(source.volume.to_numpy(), starts),
              "observed_count": ends - starts + 1}
    mismatches = {name: int(np.count_nonzero(agg[name].to_numpy() != values))
                  for name, values in checks.items()}
    if any(mismatches.values()):
        raise ValueError("independent integer 15m aggregation mismatch")
    result = expected.join(agg).reset_index().rename(columns={"bucket": "timestamp"})
    for name in ("observed_count", "contract_count"):
        result[name] = result[name].fillna(0).astype(int)
    result["source_valid"] = result.source_valid.fillna(False).astype(bool)
    result["contains_roll"] = result.contains_roll.fillna(False).astype(bool)
    result["available_at"] = result.timestamp + pd.Timedelta(minutes=15)
    result["bar_close_ts"] = result.available_at
    result["missing_expected_count"] = result.expected_count - result.observed_count
    reasons = []
    for row in result.itertuples(index=False):
        reason = []
        if not row.calendar_valid: reason.append("calendar_uncertified")
        if row.expected_count != 15: reason.append("scheduled_partial_bucket")
        if row.observed_count != row.expected_count: reason.append("missing_expected_source_minutes")
        if row.contract_count > 1: reason.append("mixed_contract")
        if row.observed_count and not row.source_valid: reason.append("invalid_source_price")
        reasons.append(";".join(reason))
    result["quality_reason"] = reasons
    result["usable"] = result.quality_reason.eq("")
    for name in ("open", "high", "low", "close"):
        result[name] = result[name + "_fixed"] * 1e-9
    result["broker_date"] = result.timestamp.dt.tz_convert(BROKER).dt.date.astype(str)
    return result, dict(status="passed", tolerance=0, observed_bars=len(agg),
        compared_fields=list(checks), compared_cells=len(agg)*len(checks),
        mismatch_counts=mismatches, alignment="UTC/GMT+3 quarter-hour [open,close)",
        timestamp_is="inclusive bar open", available_at="modeled exclusive 15m close",
        vendor_receipt_latency_known=False)


def coverage_roster(minutes: pd.DataFrame, schedule: pd.DataFrame, start=START,
                    end=END) -> pd.DataFrame:
    """Eligibility uses range-prefix information plus known calendar at 07:00.

    Trading-window omissions are saved separately and never decide eligibility.
    Calendar invalidity is a conservative known qualification rule, not a claim
    that each named holiday closes the market for the whole nominal day.
    """
    observed = minutes.set_index("timestamp", drop=False)
    expected = schedule.set_index("timestamp", drop=False)
    first_loaded = minutes.timestamp.min().tz_convert(BROKER).date().isoformat()
    dates = pd.date_range(start.tz_convert(BROKER).normalize(),
                          (end - pd.Timedelta(nanoseconds=1)).tz_convert(BROKER).normalize(), freq="D")
    rows = []
    for date in dates:
        opening = date.tz_convert("UTC")
        decision = opening + pd.Timedelta(hours=7)
        cutoff = opening + pd.Timedelta(hours=20)
        range_exp = expected.loc[opening:decision-pd.Timedelta(nanoseconds=1)]
        trade_exp = expected.loc[decision:cutoff-pd.Timedelta(nanoseconds=1)]
        range_src = observed.loc[opening:decision-pd.Timedelta(nanoseconds=1)]
        range_src = range_src.loc[range_src.index.isin(range_exp.index)]
        trade_src = observed.loc[decision:cutoff-pd.Timedelta(nanoseconds=1)]
        trade_src = trade_src.loc[trade_src.index.isin(trade_exp.index)]
        missing_range = len(range_exp.index.difference(range_src.index))
        missing_trade = len(trade_exp.index.difference(trade_src.index))
        range_count = int(range_src.contract.nunique())
        events = sorted((set(range_exp.calendar_event) | set(trade_exp.calendar_event)) - {""})
        events = [x for x in events if x]
        valid_range = bool(len(range_exp) and missing_range == 0 and range_count == 1
                           and range_src.source_valid.all() and range_exp.calendar_valid.all()
                           and range_src.high.max() > range_src.low.min())
        reasons = []
        if not len(trade_exp): reasons.append("scheduled_no_trading_window")
        if events: reasons.append("calendar_uncertified")
        if opening < start or decision > end: reasons.append("partial_range_endpoint")
        if not len(range_exp): reasons.append("no_scheduled_range")
        if missing_range: reasons.append("missing_range_source_minutes")
        if range_count > 1: reasons.append("range_contract_transition")
        if len(range_src) and not range_src.source_valid.all(): reasons.append("invalid_range_source_price")
        if len(range_src) and range_src.high.max() <= range_src.low.min(): reasons.append("zero_width_range")
        broker_date = date.date().isoformat()
        if broker_date == first_loaded: reasons.append("first_loaded_broker_day")
        rows.append(dict(broker_date=broker_date, decision_available_at=decision.isoformat(),
            eligible=not reasons and valid_range, reason=";".join(reasons), valid_range=valid_range,
            expected_range_minutes=len(range_exp), observed_range_minutes=len(range_src),
            missing_range_minutes=missing_range, expected_trading_minutes=len(trade_exp),
            observed_trading_minutes=len(trade_src), later_missing_trading_minutes=missing_trade,
            later_missing_is_eligibility_filter=False, calendar_event=";".join(events),
            range_contract_count=range_count,
            range_contract=range_src.contract.iloc[0] if range_count == 1 else None,
            range_high=float(range_src.high.max()) if len(range_src) else None,
            range_low=float(range_src.low.min()) if len(range_src) else None,
            first_loaded_broker_day=broker_date == first_loaded,
            range_start_utc=opening.isoformat(), trading_end_utc=cutoff.isoformat(),
            ny_utc_offset_minutes=int(decision.tz_convert("America/New_York").utcoffset().total_seconds()/60)))
    return pd.DataFrame(rows)


def prepare(workspace: Path, stage: Path, lock_path: Path) -> dict:
    if lock_path.exists() or stage.exists():
        raise FileExistsError("fresh input lock and audit stage required")
    stage.mkdir(parents=True)
    paths = load_workspace_paths(workspace)
    root = paths.publication_root
    manifest_hash = sha256(root / MANIFEST_PATH)
    manifest = json.loads((root / MANIFEST_PATH).read_text())
    if manifest["dataset"] != "volume_lead_unadjusted_v1" or not manifest["validation"]["passed"]:
        raise ValueError("wrong or invalid published primary input")
    dataset = open_continuous_dataset(root, "GC", manifest_path=MANIFEST_PATH,
        expected_manifest_sha256=manifest_hash, verify_selected_files=True)
    source = dataset.to_table(filter=(pc.field("year") >= 2017) & (pc.field("year") <= 2026)).to_pandas()
    source = source.loc[source.ts_event.ge(START) & source.ts_event.lt(END)].sort_values("ts_event").reset_index(drop=True)
    auxiliary_paths = ["data/curated/instruments/roll=volume_lead_v1/instrument_master.parquet",
        "data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.parquet",
        "data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.csv"]
    consumed = [descriptor(root, MANIFEST_PATH, "input_manifest")]
    for record in manifest["output_files"]:
        selected = ("/product=GC/" in record["path"] and any(f"/year={y}/" in record["path"] for y in range(2017,2027)))
        if selected or record["path"] in auxiliary_paths:
            actual = descriptor(root, record["path"], "selected_minute_partition" if selected else "roll_contract_identity")
            if actual["bytes"] != record["bytes"] or actual["sha256"] != record["sha256"]:
                raise ValueError("selected declared output bytes differ")
            consumed.append(actual)
    for relative in ("catalog/calendars/cme_fixed_clock_session_v1.json",
        "packages/bhishma/src/abacus_bhishma/calendar.py",
        "packages/bhishma/src/abacus_bhishma/ema_cloud.py",
        "packages/bhishma/src/abacus_bhishma/continuous_loader.py",
        "packages/bhishma/src/abacus_bhishma/manifest_selection.py",
        "packages/bhishma/src/abacus_bhishma/paths.py"):
        consumed.append(descriptor(root, relative, "calendar_or_loader_semantics"))
    master = pq.ParquetFile(root / auxiliary_paths[0]).read().to_pandas()
    rolls = pq.ParquetFile(root / auxiliary_paths[1]).read().to_pandas()
    minutes, identity_check = validate_contracts(source, master, rolls)
    schedule = expected_minutes("GC", "2017-12-31", "2026-09-20")
    schedule = schedule.loc[schedule.timestamp.ge(START) & schedule.timestamp.lt(END)].reset_index(drop=True)
    outside = minutes.loc[~minutes.timestamp.isin(schedule.timestamp)]
    minutes["scheduled"] = minutes.timestamp.isin(schedule.timestamp)
    schedule_by_time = schedule.set_index("timestamp")
    minutes["calendar_valid"] = minutes.timestamp.map(schedule_by_time.calendar_valid).fillna(False).astype(bool)
    minutes["calendar_event"] = minutes.timestamp.map(schedule_by_time.calendar_event).fillna("outside_normal_schedule")
    bars, aggregation = aggregate_15m(minutes, schedule)
    roster = coverage_roster(minutes, schedule)
    missing = schedule.loc[~schedule.timestamp.isin(minutes.timestamp)].copy()
    missing["qualification"] = np.where(missing.calendar_valid, "missing_expected_trade_bar_no_trade_or_gap_unknown", "uncertified_holiday_nominal_slot")
    pq.write_table(pa.Table.from_pandas(minutes, preserve_index=False), stage / "minutes.parquet", compression="zstd")
    pq.write_table(pa.Table.from_pandas(schedule, preserve_index=False), stage / "expected-minutes.parquet", compression="zstd")
    pq.write_table(pa.Table.from_pandas(bars, preserve_index=False), stage / "bars-15m.parquet", compression="zstd")
    pq.write_table(pa.Table.from_pandas(missing, preserve_index=False), stage / "missing-minutes.parquet", compression="zstd")
    roster.to_csv(stage / "coverage-roster.csv", index=False)
    outside[["timestamp", "session_date", "contract", "is_roll"]].to_csv(stage / "outside-normal-schedule.csv", index=False)
    selected_master = master.loc[master["product"].eq("GC") & master.mapping_end.astype(str).ge("2017-12-31")]
    selected_master.to_csv(stage / "selected-contract-master.csv", index=False)
    rolls.loc[rolls["product"].eq("GC")].to_csv(stage / "selected-roll-schedule.csv", index=False)
    annual = []
    for year, group in roster.groupby(pd.to_datetime(roster.broker_date).dt.year):
        selected = minutes.loc[minutes.timestamp.dt.tz_convert(BROKER).dt.year.eq(year)]
        annual.append(dict(year=int(year), broker_date_start=group.broker_date.min(), broker_date_end=group.broker_date.max(),
            actual_minute_start=selected.timestamp.min().isoformat() if len(selected) else None,
            actual_minute_end=selected.timestamp.max().isoformat() if len(selected) else None,
            partial_year=int(year)==2026, calendar_days=len(group), eligible_days=int(group.eligible.sum()),
            valid_ranges=int(group.valid_range.sum()), missing_range_days=int(group.missing_range_minutes.gt(0).sum()),
            later_missing_trading_days=int(group.later_missing_trading_minutes.gt(0).sum()),
            calendar_uncertified_days=int(group.calendar_event.ne("").sum()),
            range_roll_barriers=int(group.range_contract_count.gt(1).sum()),
            first_loaded_day_exclusions=int(group.first_loaded_broker_day.sum())))
    raw_status = []
    for record in manifest.get("source_files", []):
        raw_status.append(dict(path=record["path"], recorded_sha256=record["sha256"],
            exists=(root / record["path"]).is_file(),
            verification="existence_only_not_byte_verified_not_used_for_reconstruction"))
    summary = dict(study_id=STUDY_ID, outcome_calculation=False, created_at=datetime.now(timezone.utc).isoformat(),
        requested_start=START.isoformat(), selected_endpoint_exclusive=END.isoformat(),
        first_observed_minute=minutes.timestamp.min().isoformat(), last_observed_minute=minutes.timestamp.max().isoformat(),
        last_modeled_available_at=minutes.available_at.max().isoformat(), selected_minute_rows=len(minutes),
        expected_nominal_minutes=len(schedule), missing_qualified_expected_minutes=int(missing.calendar_valid.sum()),
        missing_uncertified_holiday_nominal_minutes=int((~missing.calendar_valid).sum()),
        outside_normal_schedule_rows=len(outside), source_checks=identity_check, aggregation_check=aggregation,
        eligible_days=int(roster.eligible.sum()), valid_ranges=int(roster.valid_range.sum()), annual=annual,
        raw_prerequisite_existence=raw_status,
        limitations=["Annual historical holiday/early-close certification is unavailable; pinned rule-generated candidate sessions are conservatively excluded before orders.",
            "Missing expected trade bars can mean no trades or delivery gaps; they are never filled or inferred as closures.",
            "available_at is modeled candle completion, not measured live vendor/contract-mapping receipt latency.",
            "Published leader mapping is retained historical symbology; its publication is not proof of real-time mapping availability.",
            "Native TradingView parity, tick-level ordering, original raw reconstruction, and off-device backup are unverified."])
    lock = dict(schema_version="abacus.study-market-lock/v1", study_id=STUDY_ID,
        state="frozen_before_phase1_outcomes", approved_on="2026-10-13", phase=1,
        dataset_id=manifest["dataset"], version=manifest["algorithm_version"],
        methodology=manifest["methodology"], adjusted=False, manifest_sha256=manifest_hash,
        public_loader="abacus_bhishma.continuous_loader.open_continuous_dataset",
        files=consumed, exact_coverage=dict(start_inclusive=START.isoformat(), end_exclusive=END.isoformat(),
            first_observed=summary["first_observed_minute"], last_observed=summary["last_observed_minute"],
            first_loaded_broker_day=roster.loc[roster.first_loaded_broker_day,"broker_date"].iloc[0],
            annual=annual), timestamp_semantics=dict(ts_event="inclusive 1m bar start from trade ts_recv; not exchange event exact fill",
            minute_available_at="bar start +1m modeled", signal_timeframe="15m", alignment="fixed UTC/GMT+3 quarter-hour",
            signal_available_at="exclusive 15m close", vendor_latency_certified=False),
        instrument=dict(product="GC", contract_unit_troy_ounces=100, dollars_per_point_per_contract=100,
            tick_size=0.1, tick_value_dollars=10, minimum_executable_quantity=1, quantity_step=1,
            master_multiplier_sentinel=2147483647, multiplier_authority="CME COMEX rulebook Chapter113",
            minimum_quantity_basis="one indivisible listed GC futures contract; whole-contract baseline and source-account step"),
        primary_sources=[dict(title="CME COMEX Gold futures rulebook113", url="https://www.cmegroup.com/rulebook/COMEX/1a/113.pdf", checked_on="2026-10-13", use="100troy ounces and0.10$/ounce minimum fluctuation"),
            dict(title="CME15-387 closing-hour change", url="https://www.cmegroup.com/market-regulation/files/15-387.pdf", checked_on="2026-10-13", use="17:00NY close effective2015-09-21, reopen18:00NY"),
            dict(title="Databento OHLCV schema", url="https://databento.com/docs/schemas-and-data-formats/ohlcv", checked_on="2026-10-13", use="ts_event inclusive interval start; absent no-trade intervals;1e-9 price scale")],
        causal_eligibility="complete qualified expected range prefix, single contract, valid OHLC/ticks, positive range, known calendar qualification, first loaded day excluded; later trading omissions never remove eligible day",
        roll_policy="exclude mixed-contract range; censor live order/trade path at first observed contract transition before new-contract prices; no adjusted P&L",
        calendar_policy="normal GC weekday session18:00 prior NY day to17:00NY;17–18NY and weekends scheduled closures; rule-generated holiday/early-close sessions retained nominal but calendar_invalid",
        raw_reconstruction="unavailable_prerequisites_not_rebuilt", prior_exposure="Phase1 later-year descriptive outcomes become prior exposure for Phase2; no untouched holdout claim", phase2_outcomes_computed=False)
    write_json(stage / "input-summary.json", summary)
    write_json(stage / "aggregation-check.json", aggregation)
    write_json(lock_path, lock)
    write_json(stage / "phase1-inputs.lock.json", lock)
    write_json(stage / "audit-artifacts.json", [dict(path=p.name, bytes=p.stat().st_size, sha256=sha256(p)) for p in sorted(stage.iterdir()) if p.is_file()])
    return summary


def load_prepared(stage: Path | str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read frozen saved inputs; return minutes,15m bars,roster,expected schedule."""
    stage = Path(stage)
    return (pq.ParquetFile(stage / "minutes.parquet").read().to_pandas(),
        pq.ParquetFile(stage / "bars-15m.parquet").read().to_pandas(),
        pd.read_csv(stage / "coverage-roster.csv", keep_default_na=False),
        pq.ParquetFile(stage / "expected-minutes.parquet").read().to_pandas())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    args = parser.parse_args()
    summary = prepare(args.workspace, args.stage, args.lock)
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
