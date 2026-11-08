"""Price-blind exact-contract input requirements for the pivot study.

This module inventories retained minute identities, not market outcomes. Normal
session rules are a qualified planning calendar, never annual exchange-calendar
certification or proof that prices/volume and indicator warmup are valid.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable, Mapping
from zoneinfo import ZoneInfo

from abacus_bhishma.calendar import holiday_sessions


NY = ZoneInfo("America/New_York")
UTC = timezone.utc
MINUTE_NS = 60_000_000_000
FULL_CONTRACT = re.compile(r"ES[HMUZ][0-9]{4}\Z")
MONTH_CODE = {3: "H", 6: "M", 9: "U", 12: "Z"}
IDENTITY_COLUMNS = ["ts_event", "session_date", "instrument_id", "raw_symbol", "roll_id"]
MASTER_COLUMNS = ["product", "roll_id", "instrument_id", "raw_symbol", "maturity_year", "maturity_month"]
QUALIFICATIONS = [
    "Normal electronic-session rules are not annual exchange-calendar certification.",
    "Holiday and possible shortened sessions are calendar-uncertified; no normal full session is asserted for them.",
    "A complete timestamp roster verifies minute presence and contract identity only; OHLCV quality and feature readiness are unassessed.",
    "Retained coverage describes the selected continuous contract, not a complete historical outright-contract archive.",
    "Five prior nominal full sessions are a minimum acquisition window, not proof of 250 consecutive valid five-minute observations.",
]


def _day(value: str | date) -> date:
    if isinstance(value, str):
        return date.fromisoformat(value)
    if type(value) is date:
        return value
    raise TypeError("session date must be an ISO date or datetime.date")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def session_bounds(session_date: str | date) -> tuple[datetime, datetime]:
    """Normal full Globex bounds in UTC; the end is exclusive."""
    day = _day(session_date)
    opening = datetime.combine(day - timedelta(days=1), time(18), NY)
    closing = datetime.combine(day, time(17), NY)
    return opening.astimezone(UTC), closing.astimezone(UTC)


def session_calendar(session_date: str | date) -> dict:
    """Return the existing conservative ES planning-calendar qualification."""
    day = _day(session_date)
    events = holiday_sessions("ES", day.year, day.year).get(day, [])
    normal = day.weekday() < 5 and not events
    return {
        "session_date": day.isoformat(),
        "calendar_status": "normal_schedule_rule_only" if normal else "calendar_uncertified",
        "calendar_events": events or (["weekend"] if day.weekday() >= 5 else []),
        "expected_minutes": (1365 if day < date(2021, 6, 28) else 1380) if normal else None,
        "exchange_calendar_certified": False,
    }


def prior_nominal_full_sessions(session_date: str | date, count: int = 5) -> tuple[list[str], list[dict]]:
    """Select previous rule-normal sessions, recording skipped uncertainty.

    These dates require subsequent source-minute validation. They are not
    presented as observed complete sessions merely because they are weekdays.
    """
    if type(count) is not int or count < 0:
        raise ValueError("prior session count must be a nonnegative integer")
    current = _day(session_date)
    selected, skipped = [], []
    while len(selected) < count:
        current -= timedelta(days=1)
        state = session_calendar(current)
        if state["calendar_status"] == "normal_schedule_rule_only":
            selected.append(current.isoformat())
        else:
            skipped.append(state)
    return sorted(selected), sorted(skipped, key=lambda row: row["session_date"])


def _expected_timestamp_ns(day: date) -> set[int]:
    state = session_calendar(day)
    if state["expected_minutes"] is None:
        return set()
    opening, closing = session_bounds(day)
    timestamps = set(range(int(opening.timestamp()) * 1_000_000_000,
                           int(closing.timestamp()) * 1_000_000_000, MINUTE_NS))
    if day < date(2021, 6, 28):
        pause = datetime.combine(day, time(16, 15), NY).astimezone(UTC)
        timestamps.difference_update(range(int(pause.timestamp()) * 1_000_000_000,
                                          int(pause.timestamp()) * 1_000_000_000 + 15 * MINUTE_NS,
                                          MINUTE_NS))
    return timestamps


def _pinned_file(root: Path, record: Mapping, verify: bool) -> Path:
    path = (root / record["path"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("declared input path escapes publication root")
    if not path.is_file():
        raise FileNotFoundError(path)
    if verify and _sha256(path) != record["sha256"]:
        raise ValueError(f"input checksum mismatch: {record['path']}")
    return path


def inspect_continuous_coverage(
    publication_root: str | Path,
    manifest_path: str | Path,
    expected_manifest_sha256: str,
    *,
    start_date: str,
    end_date: str,
    verify_selected_files: bool = True,
) -> dict:
    """Read only pinned ES minute timestamps and delivery identities.

    Dates are inclusive start/exclusive end. Numeric OHLCV fields are never
    selected or used. File hashes can verify their bytes without interpreting
    those fields. Raw-symbol decades are resolved from the pinned master.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    root = Path(publication_root)
    manifest_file = Path(manifest_path)
    if not manifest_file.is_absolute():
        manifest_file = root / manifest_file
    if _sha256(manifest_file) != expected_manifest_sha256:
        raise ValueError("continuous manifest checksum mismatch")
    manifest = json.loads(manifest_file.read_text())
    if (manifest.get("dataset") != "volume_lead_unadjusted_v1"
            or manifest.get("adjusted") is not False):
        raise ValueError("expected the pinned unadjusted continuous dataset")
    start, end = _day(start_date), _day(end_date)
    if start >= end:
        raise ValueError("coverage range must be nonempty")
    records = manifest["output_files"]
    master_records = [r for r in records if r["path"].endswith("/instrument_master.parquet")]
    if len(master_records) != 1:
        raise ValueError("manifest must declare one instrument master")
    master_path = _pinned_file(root, master_records[0], verify_selected_files)
    master = pq.ParquetFile(master_path).read(columns=MASTER_COLUMNS).to_pylist()
    identities = {}
    for row in master:
        if row["product"] != "ES":
            continue
        month = int(row["maturity_month"])
        if month not in MONTH_CODE:
            raise ValueError("ES master maturity is not quarterly")
        key = int(row["roll_id"])
        identity = (int(row["instrument_id"]), row["raw_symbol"],
                    f"ES{MONTH_CODE[month]}{int(row['maturity_year']):04d}")
        if key in identities and identities[key] != identity:
            raise ValueError("ambiguous ES roll identity in pinned master")
        identities[key] = identity
    pattern = re.compile(r"data/curated/continuous/1m/product=ES/roll=volume_lead_v1/variant=unadjusted/year=([0-9]{4})/part-[^/]+\.parquet\Z")
    selected = []
    accumulators = {}
    for record in records:
        match = pattern.fullmatch(record["path"])
        if not match or not (start.year <= int(match[1]) <= (end - timedelta(days=1)).year):
            continue
        path = _pinned_file(root, record, verify_selected_files)
        selected.append({**record, "checksum_verified": verify_selected_files})
        for batch in pq.ParquetFile(path).iter_batches(columns=IDENTITY_COLUMNS, batch_size=65536):
            values = batch.to_pydict()
            ts_ns = batch.column(batch.schema.get_field_index("ts_event")).cast(pa.int64()).to_pylist()
            for day_value, instrument, raw, roll, timestamp in zip(
                values["session_date"], values["instrument_id"], values["raw_symbol"], values["roll_id"], ts_ns
            ):
                day = _day(day_value)
                if not start <= day < end:
                    continue
                identity = identities.get(int(roll))
                if identity is None or identity[:2] != (int(instrument), raw):
                    raise ValueError("minute contract identity disagrees with pinned master")
                acc = accumulators.setdefault(day, {"timestamps": [], "contracts": set(), "instrument_ids": set(), "raw_symbols": set()})
                acc["timestamps"].append(timestamp)
                acc["contracts"].add(identity[2])
                acc["instrument_ids"].add(int(instrument))
                acc["raw_symbols"].add(raw)
    sessions = []
    for day, acc in sorted(accumulators.items()):
        timestamps = set(acc["timestamps"])
        expected = _expected_timestamp_ns(day)
        calendar = session_calendar(day)
        complete = (calendar["expected_minutes"] is not None and timestamps == expected
                    and len(acc["timestamps"]) == len(timestamps) and len(acc["contracts"]) == 1)
        sessions.append({
            **calendar,
            "full_contracts": sorted(acc["contracts"]),
            "instrument_ids": sorted(acc["instrument_ids"]),
            "raw_symbols": sorted(acc["raw_symbols"]),
            "observed_minutes": len(acc["timestamps"]),
            "unique_minutes": len(timestamps),
            "duplicate_minutes": len(acc["timestamps"]) - len(timestamps),
            "missing_expected_minutes": len(expected - timestamps) if expected else None,
            "outside_expected_minutes": len(timestamps - expected) if expected else None,
            "complete_nominal_roster": complete,
        })
    return {
        "dataset_id": manifest["dataset"],
        "manifest": {"path": str(manifest_path), "sha256": expected_manifest_sha256},
        "coverage_start": start_date, "coverage_end_exclusive": end_date,
        "selected_files": [*selected, {**master_records[0], "checksum_verified": verify_selected_files}],
        "read_columns": {"minute_partitions": IDENTITY_COLUMNS, "instrument_master": MASTER_COLUMNS},
        "sessions": sessions,
        "qualifications": QUALIFICATIONS,
    }


def _session_requirement(day: str, contract: str, retained: Mapping | None, purpose: str) -> dict:
    calendar = session_calendar(day)
    opening, closing = session_bounds(day)
    if retained is None:
        status = "missing_retained_session"
    elif contract not in retained["full_contracts"]:
        status = "selected_delivery_mismatch"
    elif retained.get("complete_nominal_roster"):
        status = "retained_identity_roster_complete"
    else:
        status = "retained_roster_incomplete_or_uncertified"
    return {
        **calendar, "full_contract": contract, "purpose": purpose,
        "start_utc": opening.isoformat(), "end_utc_exclusive": closing.isoformat(),
        "retained_status": status,
        "retained_full_contracts": retained["full_contracts"] if retained else [],
        "requires_acquisition_or_review": status != "retained_identity_roster_complete",
    }


def build_contract_windows(
    candidates: Iterable[Mapping], continuous_coverage: Mapping, *, prior_full_sessions: int = 5
) -> dict:
    """Build exact-delivery acquisition windows without consuming pivot prices.

    Candidate inputs need ``session_date``, explicit quarterly ``full_contract``
    (for example ESH2020), and optionally ``candidate_id``. Unresolved dates or
    contracts remain visible in the result instead of being silently inferred.
    """
    if type(prior_full_sessions) is not int or prior_full_sessions < 5:
        raise ValueError("at least five prior nominal full sessions are required")
    retained = {r["session_date"]: r for r in continuous_coverage["sessions"]}
    requirements = []
    intervals = []
    for candidate in candidates:
        day_value, contract = candidate.get("session_date"), candidate.get("full_contract")
        identifier = candidate.get("candidate_id", candidate.get("outlook_id"))
        if not identifier:
            raise ValueError("candidate_id or outlook_id is required")
        try:
            day = _day(day_value) if day_value else None
        except (ValueError, TypeError):
            day = None
        if day is None or not isinstance(contract, str) or not FULL_CONTRACT.fullmatch(contract):
            requirements.append({"candidate_id": identifier, "session_date": day_value,
                                 "full_contract": contract, "status": "unresolved_candidate_identity",
                                 "sessions": [], "skipped_calendar_dates": []})
            continue
        prior, skipped = prior_nominal_full_sessions(day, prior_full_sessions)
        requested = [*prior, day.isoformat()]
        rows = [_session_requirement(value, contract, retained.get(value),
                                     "analysis_session" if value == day.isoformat() else "minimum_warmup")
                for value in requested]
        needs = any(row["requires_acquisition_or_review"] for row in rows)
        requirements.append({
            "candidate_id": identifier, "session_date": day.isoformat(), "full_contract": contract,
            "status": "requires_acquisition_or_review" if needs else "retained_identity_rosters_complete",
            "prior_nominal_full_sessions": prior_full_sessions,
            "sessions": rows, "skipped_calendar_dates": skipped,
            "feature_readiness_verified": False,
        })
        intervals.append({"full_contract": contract, "start_session": requested[0], "end_session": requested[-1],
                          "start_utc": rows[0]["start_utc"], "end_utc_exclusive": rows[-1]["end_utc_exclusive"],
                          "candidate_ids": [identifier], "sessions": rows})
    windows = []
    for interval in sorted(intervals, key=lambda row: (row["full_contract"], row["start_utc"], row["end_utc_exclusive"])):
        # One continuous envelope per explicit delivery. Missing pivot dates
        # cannot create artificial EMA resets or separate acquisition islands.
        if windows and windows[-1]["full_contract"] == interval["full_contract"]:
            previous = windows[-1]
            previous["end_session"] = max(previous["end_session"], interval["end_session"])
            previous["end_utc_exclusive"] = max(previous["end_utc_exclusive"], interval["end_utc_exclusive"])
            previous["candidate_ids"].extend(interval["candidate_ids"])
            previous["sessions"].extend(interval["sessions"])
        else:
            windows.append({**interval, "sessions": list(interval["sessions"])})
    for window in windows:
        rows = {row["session_date"]: row for row in window.pop("sessions")}
        current, last = _day(window["start_session"]), _day(window["end_session"])
        while current <= last:
            value = current.isoformat()
            if current.weekday() < 5 and value not in rows:
                rows[value] = _session_requirement(value, window["full_contract"], retained.get(value),
                                                   "continuous_indicator_history")
            current += timedelta(days=1)
        missing = [row for _, row in sorted(rows.items()) if row["requires_acquisition_or_review"]]
        window["candidate_ids"] = sorted(set(window["candidate_ids"]))
        window["required_session_dates"] = sorted(rows)
        window["requires_acquisition_or_review"] = bool(missing)
        window["missing_or_uncertified_session_dates"] = [row["session_date"] for row in missing]
        window["missing_reason_counts"] = dict(sorted(Counter(row["retained_status"] for row in missing).items()))
        window["purpose"] = "exact_contract_minute_input_and_minimum_warmup"
        window["history_policy"] = "continuous_per_delivery_including_intervening_sessions_without_pivots"
        window["feature_readiness_requirement"] = "250 preceding valid observations independently for 3m and 5m; current observation excluded"
    counts = Counter(row["status"] for row in requirements)
    return {
        "schema_version": 1,
        "candidate_requirements": requirements,
        "contract_windows": windows,
        "summary": {"candidates": len(requirements), "candidate_status_counts": dict(sorted(counts.items())),
                    "contract_windows": len(windows),
                    "windows_requiring_acquisition_or_review": sum(row["requires_acquisition_or_review"] for row in windows)},
        "qualifications": QUALIFICATIONS,
    }
