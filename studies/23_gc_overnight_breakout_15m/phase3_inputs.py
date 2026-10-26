"""Pinned Phase 3 inputs and causal five-minute cloud access.

This module audits inputs only. It does not submit orders, score policies or
rebuild any Bhishma release. Parent evidence remains at its immutable locator.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from abacus_bhishma.calendar import holiday_sessions
from abacus_bhishma.ema_cloud_loader_v2 import load_release

STUDY = "23_gc_overnight_breakout_15m"
PHASE1_RUN = "20261013T142537Z_phase1_gc_ob15m_v1"
PHASE1_SHA = "d2f93832610ca6e6284838ce22ca9547b8c848a1b0f06a740a345df39d94c027"
PHASE2_RUN = "20261013T190208Z_phase2_gc_ob15m_v2"
PHASE2_SHA = "ffe43f2403520d9ba058720908ad711b88e665b0d8d3928bdaa5342ad7cb3c4a"
CLOUD_MANIFEST = "catalog/datasets/same_contract_ema_cloud__1.1.0.json"
CLOUD_SHA = "444043918c9b30a0d909e88328094b52936f6b379ce288b85afb6740aed0f838"
UTC = timezone.utc
FIVE = timedelta(minutes=5)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ordinary(root: Path, relative: str) -> Path:
    p = PurePosixPath(relative)
    if p.is_absolute() or str(p) != relative or ".." in p.parts or "\\" in relative:
        raise ValueError("ordinary relative locator required")
    target = root
    for part in p.parts:
        target /= part
        if target.is_symlink():
            raise ValueError("symlink input is not an ordinary pinned file")
    if not target.is_file():
        raise ValueError("missing input: " + relative)
    return target


def verify_record(root: Path, record: dict, *, key: str = "path") -> dict:
    path = ordinary(root, record[key])
    if "bytes" in record and path.stat().st_size != record["bytes"]:
        raise ValueError("input size changed: " + record[key])
    actual = digest(path)
    if actual != record["sha256"]:
        raise ValueError("input SHA changed: " + record[key])
    return {"path": record[key], "bytes": path.stat().st_size, "sha256": actual}


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("aware timestamp required")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class CloudBar:
    timestamp: datetime
    available_at: datetime
    contract: str | None
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    ema20: float | None
    ema50: float | None
    atr14: float | None
    usable: bool
    feature_valid: bool
    consecutive_count: int
    feature_reset: bool = False
    feature_reset_reason: str = ""
    quality_reason: str = ""
    calendar_valid: bool = True
    known_closure_before: bool = False

    @property
    def direction(self) -> int | None:
        if not self.feature_valid or self.ema20 is None or self.ema50 is None:
            return None
        return 1 if self.ema20 > self.ema50 else -1 if self.ema20 < self.ema50 else 0

    @property
    def upper(self) -> float | None:
        return None if self.direction is None else max(self.ema20, self.ema50)

    @property
    def lower(self) -> float | None:
        return None if self.direction is None else min(self.ema20, self.ema50)


@dataclass(frozen=True, slots=True)
class CloudSnapshot:
    decision_at: datetime
    expected_slot: datetime | None
    bar: CloudBar | None
    status: str
    reason: str
    slope20_3: float | None = None
    slope50_3: float | None = None
    aligned_count: int | None = None
    aligned_duration_minutes: float | None = None
    width_change_3: float | None = None
    alignment_start_known: bool | None = None
    duration_left_censored: bool | None = None

    @property
    def known(self) -> bool:
        return self.status == "known"

    @property
    def timestamp(self) -> datetime | None:
        return self.expected_slot

    @property
    def available_at(self) -> datetime | None:
        return None if self.bar is None else self.bar.available_at

    @property
    def feature_valid(self) -> bool:
        return self.known

    @property
    def ema20(self) -> float | None:
        return self.bar.ema20 if self.known else None

    @property
    def ema50(self) -> float | None:
        return self.bar.ema50 if self.known else None

    @property
    def atr14(self) -> float | None:
        return self.bar.atr14 if self.known else None

    @property
    def close(self) -> float | None:
        return self.bar.close if self.known else None

    @property
    def direction(self) -> int | None:
        return self.bar.direction if self.known else None

    @property
    def upper(self) -> float | None:
        return self.bar.upper if self.known else None

    @property
    def lower(self) -> float | None:
        return self.bar.lower if self.known else None


def cloud_bars(frame: pd.DataFrame) -> tuple[CloudBar, ...]:
    """Adapt saved rows without recalculating features or dropping quality slots."""
    def number(x):
        return None if pd.isna(x) else float(x)
    columns = tuple(CloudBar.__dataclass_fields__)
    values = []
    for row in frame.loc[:, columns].itertuples(index=False, name=None):
        r = dict(zip(columns, row))
        for key in ("timestamp", "available_at"):
            r[key] = r[key].to_pydatetime() if hasattr(r[key], "to_pydatetime") else r[key]
        r["contract"] = None if pd.isna(r["contract"]) else str(r["contract"])
        for key in ("open", "high", "low", "close", "ema20", "ema50", "atr14"):
            r[key] = number(r[key])
        for key in ("usable", "feature_valid", "feature_reset", "calendar_valid", "known_closure_before"):
            r[key] = bool(r[key])
        r["consecutive_count"] = int(r["consecutive_count"])
        values.append(CloudBar(**r))
    return tuple(values)


class CloudTimeline:
    """Latest expected completed slot, including unavailable quality records.

    A known scheduled closure does not introduce an expected slot. An absent
    expected slot never falls back to an older usable cloud. Slopes require the
    current observation and three earlier adjacent expected valid observations.
    """
    def __init__(self, bars: Iterable[CloudBar], expected_slots: Iterable[datetime], *,
                 coverage_end: datetime | None = None):
        self.expected = tuple(utc(t) for t in expected_slots)
        if not self.expected or any(b <= a for a, b in zip(self.expected, self.expected[1:])):
            raise ValueError("expected slots must be nonempty, unique and ordered")
        self.indices = {t: i for i, t in enumerate(self.expected)}
        self.bars = tuple(bars)
        self.by_time = {}
        previous = None
        for bar in self.bars:
            t = utc(bar.timestamp)
            if t != bar.timestamp or t not in self.indices or (previous is not None and t <= previous):
                raise ValueError("cloud rows must be unique chronological expected UTC slots")
            if int(t.timestamp()) % 300 or t.microsecond or utc(bar.available_at) != t + FIVE:
                raise ValueError("five-minute open/completion mapping required")
            if bar.feature_valid and (not bar.usable or not bar.calendar_valid or bar.consecutive_count < 250):
                raise ValueError("valid cloud requires 250 usable calendar-qualified observations")
            if bar.usable:
                prices = (bar.open, bar.high, bar.low, bar.close)
                if (not bar.contract or any(x is None or not math.isfinite(x) or x <= 0 for x in prices)
                        or bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close)
                        or bar.high < bar.low):
                    raise ValueError("usable cloud requires valid same-contract OHLC")
            if bar.feature_valid and any(x is None or not math.isfinite(x) for x in (bar.ema20, bar.ema50, bar.atr14)):
                raise ValueError("valid feature requires finite saved EMA/ATR values")
            self.by_time[t] = bar
            previous = t
        self.coverage_end = utc(coverage_end) if coverage_end else self.expected[-1] + FIVE
        self.alignment = {}
        self.prefix_gap = set()
        aligned_count, aligned_start, prior_direction, prior_contract = 0, None, None, None
        start_known = False
        gap_count = None
        for t in self.expected:
            bar = self.by_time.get(t)
            if bar is None:
                gap_count = 0
            elif gap_count is not None:
                gap_count = gap_count + 1 if bar.usable else 0
                if gap_count < 250:
                    self.prefix_gap.add(t)
                else:
                    gap_count = None
            direction = None if bar is None or not bar.usable or not bar.feature_valid or t in self.prefix_gap else bar.direction
            if direction in (None, 0):
                aligned_count, aligned_start = 0, None
                start_known = direction == 0
            elif direction == prior_direction and bar.contract == prior_contract:
                aligned_count += 1
            else:
                aligned_count, aligned_start = 1, t + FIVE
                start_known = prior_direction is not None and bar.contract == prior_contract
            if bar is not None:
                self.alignment[t] = (aligned_count, 0. if aligned_start is None else ((t + FIVE) - aligned_start).total_seconds() / 60,
                                     start_known, not start_known)
            prior_direction = direction
            prior_contract = None if bar is None else bar.contract

    def snapshot(self, at: datetime, contract: str | None = None) -> CloudSnapshot:
        at = utc(at)
        if at > self.coverage_end:
            return CloudSnapshot(at, None, None, "unknown", "outside_retained_coverage")
        i = bisect_right(self.expected, at - FIVE) - 1
        if i < 0:
            return CloudSnapshot(at, None, None, "unknown", "before_first_completion")
        t = self.expected[i]
        bar = self.by_time.get(t)
        reason = ("missing_latest_expected_slot" if bar is None else
                  "contract_mismatch" if contract is not None and bar.contract != contract else
                  "unusable_latest_expected_slot" if not bar.usable else
                  "warmup_or_invalid_feature" if not bar.feature_valid else
                  "unknown_feature_prefix_gap" if t in self.prefix_gap else "")
        if reason:
            return CloudSnapshot(at, t, bar, "unknown", reason)
        slopes = [self.by_time.get(t0) for t0 in self.expected[max(0, i - 3):i + 1]]
        good = len(slopes) == 4 and all(b is not None and b.usable and b.feature_valid and b.contract == bar.contract and b.timestamp not in self.prefix_gap for b in slopes)
        aligned_count, aligned_duration, start_known, left_censored = self.alignment[t]
        return CloudSnapshot(at, t, bar, "known", "", bar.ema20 - slopes[0].ema20 if good else None,
                             bar.ema50 - slopes[0].ema50 if good else None, aligned_count, aligned_duration,
                             (bar.upper - bar.lower) - (slopes[0].upper - slopes[0].lower) if good else None,
                             start_known, left_censored)

    def adjacent(self, left: datetime, right: datetime) -> bool:
        return left in self.indices and right in self.indices and self.indices[right] == self.indices[left] + 1

    def for_window(self, start: datetime, end: datetime, *, full_after: datetime | None = None) -> tuple[CloudBar, ...]:
        start, end = utc(start), utc(end)
        if full_after is not None:
            start = max(start, utc(full_after))
        slots = self.expected[bisect_left(self.expected, start):bisect_left(self.expected, end)]
        return tuple(self.by_time.get(t) or CloudBar(t, t + FIVE, None, None, None, None, None,
                    None, None, None, False, False, 0, True, "missing_expected_slot", "missing_expected_slot") for t in slots)


def expected_cloud_slots(start_session: str, end_completion: str) -> pd.DataFrame:
    """Independent 5m roster for the pinned GC normal-calendar policy.

    Holidays are the existing pinned rule candidates, not exchange-certified
    closures. Their nominal slots are retained with calendar_valid=False.
    """
    start = date.fromisoformat(start_session)
    last = pd.Timestamp(end_completion).tz_convert("America/New_York").date()
    holidays = holiday_sessions("GC", start.year, last.year)
    pieces = []
    for session in pd.date_range(start, last, freq="B"):
        day = session.date()
        opening = pd.Timestamp(str(day - timedelta(days=1)) + " 18:00", tz="America/New_York")
        closing = pd.Timestamp(str(day) + " 17:00", tz="America/New_York")
        times = pd.date_range(opening, closing, freq="5min", inclusive="left").tz_convert("UTC")
        event = ";".join(holidays.get(day, []))
        pieces.append(pd.DataFrame({"timestamp": times, "session": day.isoformat(),
                                    "calendar_event": event, "calendar_valid": not bool(event)}))
    roster = pd.concat(pieces, ignore_index=True)
    return roster.loc[roster.timestamp + pd.Timedelta(minutes=5) <= pd.Timestamp(end_completion)].reset_index(drop=True)


def load_cloud(root: Path) -> pd.DataFrame:
    return load_release(root, product="GC", interval=5, manifest_path=CLOUD_MANIFEST,
                        expected_manifest_sha256=CLOUD_SHA, verify_selected_files=True)


def parent_order_update_times(bars15: pd.DataFrame, *, first_submission: datetime,
                              shadow_event_time: datetime, cutoff: datetime,
                              contract: str) -> tuple[datetime, ...]:
    """Reconstruct source calls, leaving the compact saved order ledger intact.

    The first saved submission is authoritative. Later complete same-contract
    15m closes through the shadow opening and before cutoff are inferred source
    recalculations while flat. A later coincident close is a candidate update:
    changed admission versus the preceding standing gate requires unknown/bounds,
    not a retrospective refresh. Native cancellation latency is not certified.
    """
    first, shadow, end = map(utc, (first_submission, shadow_event_time, cutoff))
    if not first <= shadow <= end:
        raise ValueError("ordered submission/shadow/cutoff required")
    times = [first]
    for row in bars15[["timestamp", "contract", "usable"]].itertuples(index=False):
        close = utc(row.timestamp.to_pydatetime() if hasattr(row.timestamp, "to_pydatetime") else row.timestamp) + timedelta(minutes=15)
        if row.usable and row.contract == contract and first < close <= shadow and close < end:
            times.append(close)
    if len(set(times)) != len(times) or any(b <= a for a,b in zip(times,times[1:])):
        raise ValueError("source decision updates must be unique and chronological")
    return tuple(times)


def parent_order_updates(bars15: pd.DataFrame, *, first_submission: datetime,
                         shadow_event_time: datetime, cutoff: datetime,
                         contract: str) -> tuple[dict, ...]:
    """Preserve effective-prefix versus tied-candidate provenance explicitly."""
    times = parent_order_update_times(bars15, first_submission=first_submission,
        shadow_event_time=shadow_event_time, cutoff=cutoff, contract=contract)
    shadow = utc(shadow_event_time)
    return tuple({"time": t, "kind": "saved_initial_submission" if i == 0 else "inferred_source_recalculation",
                  "coincident_shadow": t == shadow,
                  "timing_rule": "inherited_initial_availability" if i == 0 else
                    "candidate_update_requires_admission_tie_resolution" if t == shadow else "prospective_update"}
                 for i,t in enumerate(times))


def load_parent_frames(root: Path) -> dict:
    """Hash-checked raw parent ledgers and prepared frames for DayData adapters."""
    parent = root / "runs" / STUDY / PHASE1_RUN
    verify_record(parent, {"path": "manifest.json", "sha256": PHASE1_SHA})
    records = json.loads((parent / "manifest.json").read_text())["external_artifacts"]
    selected = [r for r in records if r["id"].startswith("primary-one-tick-") or r["id"] in
                {"audit-minutes", "audit-bars-15m", "audit-expected-minutes"}]
    result = {}
    for row in selected:
        verify_record(root, row, key="locator")
        path = root / row["locator"]
        if row["locator"].endswith(".gz"):
            with gzip.open(path,"rt") as stream:
                result[row["id"]] = [json.loads(line) for line in stream]
        else:
            result[row["id"]] = pq.ParquetFile(path).read().to_pandas()
    return result


def audit_cloud_contracts(frame: pd.DataFrame, master: pd.DataFrame) -> dict:
    """Every observed single-contract slot, including the 2017 warmup prefix."""
    single = frame.loc[frame.contract_count.eq(1), ["contract", "raw_symbol", "roll_id", "session"]]
    identity = master.loc[master["product"].eq("GC"), ["roll_id", "instrument_id", "maturity_year",
                    "maturity_month", "raw_symbol", "mapping_start", "mapping_end"]].copy()
    joined = single.merge(identity, on="roll_id", how="left", suffixes=("", "_master"), validate="many_to_one")
    if joined.instrument_id.isna().any():
        raise ValueError("cloud contract missing from pinned master")
    expected = pd.Series([f"GC:{int(i)}:{int(y)}:{int(m)}:{s}" for i,y,m,s in
                          zip(joined.instrument_id,joined.maturity_year,joined.maturity_month,joined.raw_symbol_master)])
    if not joined.contract.reset_index(drop=True).eq(expected).all() or not joined.raw_symbol.eq(joined.raw_symbol_master).all():
        raise ValueError("cloud full-maturity contract/master mismatch")
    session = pd.to_datetime(joined.session)
    if not ((session >= pd.to_datetime(joined.mapping_start)) & (session < pd.to_datetime(joined.mapping_end))).all():
        raise ValueError("cloud contract mapping bounds mismatch")
    if not frame.loc[~frame.contract_count.eq(1), "contract"].isna().all():
        raise ValueError("empty/mixed cloud slot cannot provide a contract identity")
    return {"result":"passed", "observed_single_contract_rows":len(single),
            "composite_contracts":int(single.contract.nunique()), "prefix_2017_included":True}


def audit_feature_recurrence(frame: pd.DataFrame) -> dict:
    """Independent scalar EMA/Wilder recurrence across full retained history."""
    size = len(frame)
    expected = {key: np.full(size, np.nan) for key in ("ema20", "ema50", "atr14", "true_range")}
    counts = np.zeros(size, dtype=np.int64)
    valid = np.zeros(size, dtype=bool)
    resets = np.zeros(size, dtype=bool)
    reset_reasons = np.full(size, "", dtype=object)
    prior_contract = prior_close = prior_time = None
    e20 = e50 = atr = None
    count = 0
    tr_seed = []
    fields = ["timestamp", "contract", "usable", "known_closure_before", "close", "high", "low"]
    for i, (t, contract, usable, known_closure, close, high, low) in enumerate(frame[fields].itertuples(index=False, name=None)):
        if not usable or pd.isna(contract):
            count = 0
            e20 = e50 = atr = prior_close = prior_contract = None
            tr_seed = []
            prior_time = t
            resets[i] = True
            reset_reasons[i] = str(frame.quality_reason.iloc[i] or "invalid_bar") if "quality_reason" in frame else "invalid_bar"
            continue
        gap = prior_time is not None and t - prior_time > pd.Timedelta(minutes=5) and not known_closure
        if count == 0 or (prior_contract is not None and contract != prior_contract) or gap:
            reset_reasons[i] = "unknown_feature_gap" if gap else "contract_switch" if prior_contract is not None and contract != prior_contract else "segment_start"
            count = 0
            e20 = e50 = atr = prior_close = None
            tr_seed = []
            resets[i] = True
        tr = high - low if prior_close is None else max(high - low, abs(high - prior_close), abs(low - prior_close))
        e20 = close if e20 is None else (2 * close + 19 * e20) / 21
        e50 = close if e50 is None else (2 * close + 49 * e50) / 51
        count += 1
        if count <= 14:
            tr_seed.append(tr)
            if count == 14:
                atr = sum(tr_seed) / 14
        else:
            atr = (13 * atr + tr) / 14
        for key, value in [("ema20", e20), ("ema50", e50), ("atr14", atr), ("true_range", tr)]:
            expected[key][i] = np.nan if value is None else value
        counts[i], valid[i] = count, count >= 250
        prior_contract, prior_close, prior_time = contract, close, t
    errors = {}
    for key, calculated in expected.items():
        actual = frame[key].to_numpy(dtype=float)
        if not np.isclose(actual, calculated, atol=1e-10, rtol=1e-12, equal_nan=True).all():
            raise ValueError("independent feature recurrence mismatch: " + key)
        finite = np.isfinite(actual) & np.isfinite(calculated)
        errors[key] = float(np.max(np.abs(actual[finite] - calculated[finite]))) if finite.any() else 0.
    for key, values in [("consecutive_count", counts), ("feature_valid", valid), ("feature_reset", resets)]:
        if not np.array_equal(frame[key].to_numpy(), values):
            raise ValueError("independent feature chronology mismatch: " + key)
    if "feature_reset_reason" in frame and not np.array_equal(frame.feature_reset_reason.to_numpy(), reset_reasons):
        raise ValueError("independent feature reset-reason mismatch")
    field_count = 8 if "feature_reset_reason" in frame else 7
    return {"result": "passed", "rows": size, "fields": field_count, "comparisons": size * field_count,
            "absolute_tolerance": 1e-10, "relative_tolerance": 1e-12, "maximum_errors": errors,
            "scope": "input features only; no strategy signals or outcomes"}


def audit(root: Path) -> dict:
    """Verify actual parent/input bytes and input-only numerical semantics."""
    parent = root / "runs" / STUDY / PHASE1_RUN
    verify_record(parent, {"path": "manifest.json", "sha256": PHASE1_SHA})
    manifest = json.loads((parent / "manifest.json").read_text())
    local = [verify_record(parent, row) for row in manifest["artifacts"]]
    external = [verify_record(root, row, key="locator") for row in manifest["external_artifacts"]]
    config = json.loads((parent / "config.json").read_text())
    if (config["protocol_version"] != "1.0.0" or config["broker_timezone"] != "fixed_UTC_plus_03:00"
            or config["signal_minutes"] != 15 or config["execution_minutes"] != 1
            or config["range_hours"] != [0, 7] or config["entry_hours"] != [7, 20]
            or config["costs"]["primary_adverse_ticks_per_fill"] != 1
            or config["costs"]["commission_fees_dollars_per_contract_per_side"] != 2.5):
        raise ValueError("authoritative parent protocol/settings mismatch")
    execution_freeze = json.loads((parent / "execution-freeze.json").read_text())
    current_runtime = []
    core = {"run.py", "metrics.py", "prepare_inputs.py", "src/engine.py"}
    for row in execution_freeze["source_files"]:
        prefix = "source/studies/" + STUDY + "/"
        if row["path"].startswith(prefix) and row["path"][len(prefix):] in core:
            current_runtime.append(verify_record(root, {"path": row["path"][len("source/"):], "sha256": row["sha256"]}))
    if len(current_runtime) != 4:
        raise ValueError("authoritative Phase 1 core source freeze incomplete")
    publication = json.loads((parent / "publication.json").read_text())
    publication_manifest = json.loads((parent / "publication-manifest.json").read_text())
    if (publication["id"] != "gc-overnight-breakout-15m-phase1-20261013-v1"
            or publication["source"]["runId"] != PHASE1_RUN
            or publication_manifest["source_run_id"] != PHASE1_RUN
            or publication_manifest["study_id"] != STUDY):
        raise ValueError("authoritative parent publication attribution changed")
    science = json.loads((parent / "scientific-verification.json").read_text())
    if science["status"] != "passed" or science["run_id"] != PHASE1_RUN:
        raise ValueError("authoritative parent verification receipt changed")
    phase2 = root / "runs" / STUDY / PHASE2_RUN
    phase2_manifest = verify_record(phase2, {"path": "manifest.json", "sha256": PHASE2_SHA})
    phase2_records = json.loads((phase2 / "manifest.json").read_text())["artifacts"]
    selection_pin = next(x for x in phase2_records if x["path"] == "selection.json")
    verify_record(phase2, selection_pin)
    selection = json.loads((phase2 / "selection.json").read_text())
    if selection["selected_policy"] is not None or selection["decision"] != "retain_baseline_no_qualifying_replacement":
        raise ValueError("expected null Phase 2 selected-parent authority changed")
    cloud_pin = verify_record(root, {"path": CLOUD_MANIFEST, "sha256": CLOUD_SHA})
    cloud_manifest = json.loads((root / CLOUD_MANIFEST).read_text())
    market_lock = json.loads((parent / "inputs.lock.json").read_text())
    selected_source = [x for x in market_lock["files"] if x["role"] == "selected_minute_partition"]
    source_manifest = next(x for x in cloud_manifest["source_manifest_pins"] if x["path"] == "catalog/datasets/volume_lead_unadjusted_v1.json")
    if source_manifest["sha256"] != market_lock["manifest_sha256"]:
        raise ValueError("cloud minute manifest differs from frozen parent")
    cloud_sources = {x["path"]: x for x in cloud_manifest["source_files"]}
    for row in selected_source:
        actual = cloud_sources.get(row["path"])
        if actual is None or any(actual[k] != row[k] for k in ("bytes", "sha256")):
            raise ValueError("cloud minute partition differs from frozen parent")
    source_pins = [verify_record(root, x) for x in market_lock["files"]]
    selected_cloud = [x for x in cloud_manifest["output_files"] if x["product"] == "GC" and x["interval_minutes"] == 5]
    cloud_file = verify_record(root, selected_cloud[0])
    auxiliary = [verify_record(root, x) for x in cloud_manifest["auxiliary_files"]]
    loader_record = next(x for x in auxiliary if x["path"].endswith("/provenance/ema_cloud_loader_v2.py"))
    current_loader = verify_record(root, {"path": "packages/bhishma/src/abacus_bhishma/ema_cloud_loader_v2.py",
                                        "sha256": loader_record["sha256"], "bytes": loader_record["bytes"]})
    schema_path = cloud_manifest["schema_path"]
    schema = json.loads(ordinary(root, schema_path).read_text())
    actual_schema = pq.ParquetFile(root / cloud_file["path"]).schema_arrow
    declared_schema = schema["interval_schemas"]["5"]
    if [(f.name, str(f.type), f.nullable) for f in actual_schema] != [(f["name"], f["type"], f["nullable"]) for f in declared_schema]:
        raise ValueError("cloud declared Arrow schema mismatch")
    frame = load_cloud(root)
    roster = expected_cloud_slots(cloud_manifest["coverage_start_session"], cloud_manifest["coverage_end_completion"])
    if not frame.timestamp.equals(roster.timestamp):
        raise ValueError("cloud expected roster mismatch")
    for key in ("session", "calendar_event", "calendar_valid"):
        if not np.array_equal(frame[key].to_numpy(), roster[key].to_numpy()):
            raise ValueError("cloud calendar metadata mismatch: " + key)
    if not frame.available_at.eq(frame.timestamp + pd.Timedelta(minutes=5)).all():
        raise ValueError("cloud completion availability mismatch")
    known_closure = frame.timestamp.diff().gt(pd.Timedelta(minutes=5)).fillna(False)
    if not frame.known_closure_before.eq(known_closure).all():
        raise ValueError("cloud scheduled-closure flag mismatch")
    usable = (frame.calendar_valid & frame.expected_count.eq(5) & frame.source_count.eq(5)
              & frame.distinct_count.eq(5) & frame.contract_count.eq(1)
              & ~frame.bad_source & ~frame.duplicate_source & frame.missing_offsets.eq("")
              & frame.contract.notna())
    if not frame.usable.eq(usable).all():
        raise ValueError("cloud complete-slot usable predicate mismatch")
    if not frame.feature_valid.eq(frame.usable & frame.consecutive_count.ge(250)).all():
        raise ValueError("cloud warmup-valid predicate mismatch")
    recurrence = audit_feature_recurrence(frame)
    master_pin = next(x for x in market_lock["files"] if x["path"].endswith("instrument_master.parquet"))
    master = pq.ParquetFile(root / master_pin["path"]).read().to_pandas()
    contract_audit = audit_cloud_contracts(frame, master)
    prepared_pin = next(x for x in manifest["external_artifacts"] if x["id"] == "audit-minutes")
    cols = ["timestamp", "open_fixed", "high_fixed", "low_fixed", "close_fixed", "volume", "contract", "scheduled"]
    minutes = pq.ParquetFile(root / prepared_pin["locator"]).read(columns=cols).to_pandas()
    minutes = minutes.loc[minutes.scheduled].copy()
    minutes["bucket"] = minutes.timestamp.dt.floor("5min")
    grouped = minutes.groupby("bucket", sort=True).agg(open_fixed=("open_fixed", "first"), high_fixed=("high_fixed", "max"),
        low_fixed=("low_fixed", "min"), close_fixed=("close_fixed", "last"), volume=("volume", "sum"),
        source_count=("timestamp", "size"), contract=("contract", "first"), contract_count=("contract", "nunique"))
    observed = frame.set_index("timestamp").reindex(grouped.index)
    if observed.source_count.isna().any():
        raise ValueError("parent scheduled source candle absent from cloud roster")
    for key in ("open", "high", "low", "close"):
        integer = np.rint(observed[key].to_numpy() * 1e9).astype(np.int64)
        if not np.array_equal(integer, grouped[key + "_fixed"].to_numpy()):
            raise ValueError("cloud differs from unadjusted parent aggregation: " + key)
    for key in ("volume", "source_count", "contract_count"):
        if not np.array_equal(observed[key].to_numpy(), grouped[key].to_numpy()):
            raise ValueError("cloud parent aggregation metadata mismatch: " + key)
    single = grouped.contract_count.eq(1)
    if not observed.loc[single, "contract"].eq(grouped.loc[single, "contract"]).all():
        raise ValueError("cloud full maturity contract identity mismatch")
    if not observed.loc[~single, "contract"].isna().all():
        raise ValueError("mixed-contract quality slot must not name a valid contract")
    prefix_pin = next(x for x in selected_source if "/year=2017/" in x["path"])
    prefix = pq.ParquetFile(root / prefix_pin["path"]).read().to_pandas()
    prefix["bucket"] = prefix.ts_event.dt.floor("5min")
    prefix_cloud = frame.loc[frame.timestamp.lt(pd.Timestamp("2018-01-01T00:00:00Z"))].set_index("timestamp")
    prefix = prefix.loc[prefix.bucket.isin(prefix_cloud.index)]
    prefix_group = prefix.groupby("bucket",sort=True).agg(open=("open","first"),high=("high","max"),
        low=("low","min"),close=("close","last"),volume=("volume","sum"),source_count=("ts_event","size"))
    prefix_observed = prefix_cloud.reindex(prefix_group.index)
    for key in ("open","high","low","close"):
        actual = np.rint(prefix_observed[key].to_numpy()*1e9).astype(np.int64)
        if not np.array_equal(actual,prefix_group[key].to_numpy()):
            raise ValueError("2017 cloud warmup raw aggregation mismatch: "+key)
    for key in ("volume","source_count"):
        if not np.array_equal(prefix_observed[key].to_numpy(),prefix_group[key].to_numpy()):
            raise ValueError("2017 cloud warmup raw metadata mismatch: "+key)
    critical = [x for x in manifest["external_artifacts"] if x["id"].startswith("primary-one-tick-") or x["id"].startswith("audit-")]
    def ledger(name):
        row = next(x for x in critical if x["id"] == name)
        with gzip.open(root / row["locator"], "rt") as stream:
            return [json.loads(line) for line in stream]
    trades = ledger("primary-one-tick-trades")
    statuses = {s: sum(t["status"] == s for t in trades) for s in sorted({t["status"] for t in trades})}
    if len(trades) != 880 or statuses != {"censored": 17, "completed": 863}:
        raise ValueError("authoritative original episode roster changed")
    user_source = "studies/21_ema_cloud_trend_follow_opportunity/reference/ema_cloud_trend_follower_user.pine"
    source = ordinary(root, user_source)
    reference_manifest_path = "studies/21_ema_cloud_trend_follow_opportunity/reference/manifest.json"
    reference_manifest = json.loads(ordinary(root, reference_manifest_path).read_text())
    user_source_pin = verify_record(root, {"path": user_source, "bytes": reference_manifest["bytes"], "sha256": reference_manifest["sha256"]})
    parent_sources = json.loads((parent / "source/studies/23_gc_overnight_breakout_15m/inputs.lock.json").read_text())["sources"]
    current_parent_sources = [verify_record(root, x) for x in parent_sources]
    return {"schema_version": "study23.phase3-input-audit/v1", "result": "passed",
        "checked_at": datetime.now(UTC).isoformat(), "scope": "read-only parent pins, source identity, input aggregation/calendar/features; no Phase 3 policy outcomes",
        "phase1": {"run_id": PHASE1_RUN, "manifest_sha256": PHASE1_SHA, "protocol_version": config["protocol_version"],
                   "local_files": len(local), "external_files": len(external), "verified_local": local, "verified_external": external,
                   "critical_ledgers_and_prepared": critical, "original_episodes": len(trades), "statuses": statuses,
                   "settings_sha256": digest(parent / "config.json"), "input_lock_sha256": digest(parent / "inputs.lock.json"),
                   "current_core_runtime_matches_frozen_bytes": current_runtime,
                   "publication_id": publication["id"], "publication_source_run_id": publication["source"]["runId"],
                   "scientific_verification_status": science["status"],
                   "order_ledger": "compact initial submission and cancellation; source-call refresh times are separately inferred from usable 15m closes"},
        "phase2": {"run_id": PHASE2_RUN, "manifest": phase2_manifest, "selection": selection_pin,
                   "selected_policy": None, "replication_parent": None, "reason": "no preselected qualifying Phase 2 replacement"},
        "cloud": {"manifest": cloud_pin, "selected_file": cloud_file, "source_manifest": source_manifest,
                  "source_pins": source_pins, "auxiliary_pins": auxiliary, "rows": len(frame),
                  "current_public_loader": current_loader,
                  "schema": {"path": schema_path, "sha256": digest(root / schema_path), "fields": len(declared_schema), "actual_arrow_types_and_nullability": "passed"},
                  "start": frame.timestamp.iloc[0].isoformat(), "completion": frame.available_at.iloc[-1].isoformat(),
                  "usable_rows": int(frame.usable.sum()), "valid_feature_rows": int(frame.feature_valid.sum()),
                  "warmup_usable_rows": int((frame.usable & ~frame.feature_valid).sum()),
                  "reset_rows": int(frame.feature_reset.sum()), "quality_reasons": {str(k): int(v) for k,v in frame.quality_reason.value_counts().items()},
                  "expected_calendar": "complete nominal GC 18–17 New York weekday slots; uncertified holidays retained invalid",
                  "calendar_rows_compared": len(roster), "available_at_comparisons": len(frame),
                  "usable_and_warmup_predicate_comparisons": 2 * len(frame),
                  "parent_aggregation": {"observed_candles": len(grouped), "compared_fields": 8, "integer_price_tolerance": 0,
                                         "scheduled_parent_minutes": len(minutes), "unadjusted_prices_and_contracts": "passed"},
                  "feature_recurrence": recurrence, "feature_state_not_reset_at_year_or_fold": True,
                  "contract_master_mapping": contract_audit,
                  "warmup_2017_raw_aggregation": {"result":"passed", "source_minutes":len(prefix),
                    "observed_candles":len(prefix_group), "compared_fields":6, "integer_price_tolerance":0}},
        "user_cloud_source": {**user_source_pin, "reference_manifest_path": reference_manifest_path,
                              "reference_manifest_sha256": digest(root / reference_manifest_path),
                              "lower_timeframe_chart_display": "last intrabar; source touch signals disabled when selected EMA timeframe is lower than chart timeframe",
                              "neutral_equality": "neutral analytical direction despite green source display",
                              "inherited_touch_gate": None},
        "current_parent_source_pins": current_parent_sources,
        "qualifications": cloud_manifest["qualifications"],
        "adapter_contract": {"snapshot": "latest expected completed 5m slot; invalid/missing latest remains unknown",
                             "contact": "prior opening snapshot then close confirmation; full post-fill candles only",
                             "slopes": "current minus three prior adjacent expected valid same-contract observations",
                             "aligned_duration": "count/time lower bounds left-censored after unavailable prefix; known sign transition establishes start",
                             "parent_order_updates": "saved initial submission plus usable same-contract 15m closes through first shadow opening; later tied candidate retained separately and changed admission is unknown/bounded",
                             "warmup": 250, "known_closures": "no synthetic slots and no feature reset",
                             "unknown_before_gate": "declared abstention", "unknown_while_open": "no new cloud action; inherited protection persists"}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    target = args.output_directory / "phase3-input-audit.json"
    if target.exists():
        raise ValueError("refusing to overwrite an existing audit receipt")
    result = audit(args.root.resolve())
    result["checker"] = {"path": str(Path(__file__).resolve().relative_to(args.root.resolve())),
                         "bytes": Path(__file__).stat().st_size, "sha256": digest(Path(__file__))}
    with target.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"result": result["result"], "receipt": str(target), "sha256": digest(target),
                      "cloud_rows": result["cloud"]["rows"], "parent_episodes": result["phase1"]["original_episodes"]}))


if __name__ == "__main__":
    main()
