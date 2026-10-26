"""Independent source reconstruction for Study 22 one-candle-pullback evidence.

Only the standard library is used. This verifier does not import the reversal
engine, its aggregation, the existing bar loader, or the reporting-window helper.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from itertools import zip_longest
import json
import math
from pathlib import Path, PurePosixPath
import sys
from typing import Iterable, Iterator
from zoneinfo import ZoneInfo


STUDY_ID = "22_es_range_xv_focused"
WORKSPACE = Path(__file__).resolve().parents[2]
COMPLETED = {"next_bar_start_proxy", "next_bar_start_same_second"}
INPUT_COLUMNS = [
    "source_row", "source_timestamp", "bar_start_timestamp",
    "bar_completion_timestamp_proxy", "bar_duration_seconds_proxy",
    "completion_proxy_status", "session_date_proxy", "open", "high", "low", "close",
]


@dataclass(frozen=True)
class IndependentBar:
    row: int
    start: datetime
    session: date
    opening: Decimal
    high: Decimal
    low: Decimal
    closing: Decimal
    completion: datetime | None
    status: str

    @property
    def direction(self) -> str | None:
        if self.closing > self.opening:
            return "bullish"
        if self.closing < self.opening:
            return "bearish"
        return None


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with regular(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def regular(path: Path) -> Path:
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError(f"Symlinked audit path refused: {path}")
    if not path.is_file():
        raise ValueError(f"Regular audit file required: {path}")
    return path


def located(root: Path, locator: str) -> Path:
    if (not isinstance(locator, str) or not locator or "\\" in locator
            or PurePosixPath(locator).is_absolute()
            or any(piece in ("", ".", "..") for piece in locator.split("/"))):
        raise ValueError("Unsafe audit locator")
    return regular(root / locator)


def read_json(path: Path) -> dict:
    value = json.loads(regular(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON audit object required: {path}")
    return value


def _stamp(raw: str, ordinal: int) -> datetime:
    try:
        value = datetime.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Malformed timestamp at source row {ordinal}") from exc
    if value.tzinfo is not None:
        raise ValueError(f"Aware timestamp at source row {ordinal}")
    return value


def _decimal(raw: str, ordinal: int) -> Decimal:
    try:
        value = Decimal(raw)
    except (TypeError, InvalidOperation) as exc:
        raise ValueError(f"Malformed price/duration at source row {ordinal}") from exc
    if not value.is_finite():
        raise ValueError(f"Nonfinite price/duration at source row {ordinal}")
    return value


def read_bars(path: Path, *, raw_path: Path | None = None) -> Iterator[IndependentBar]:
    """Validate every retained input field, optionally against each original row.

    Validation uses adjacent original rows, including same-second records. The
    one-row delay leaves a completed bar's proxy checked before it is yielded.
    """
    previous: IndependentBar | None = None
    source_handle = regular(raw_path).open(newline="", encoding="utf-8-sig") if raw_path else None
    raw_reader = csv.reader(source_handle, delimiter=";") if source_handle else None
    try:
        with regular(path).open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            if reader.fieldnames != INPUT_COLUMNS:
                raise ValueError(f"{path}: enhanced input columns differ")
            for ordinal, record in enumerate(reader, 1):
                if None in record or any(value is None for value in record.values()):
                    raise ValueError(f"{path}: input column count differs at {ordinal}")
                if record["source_row"] != str(ordinal):
                    raise ValueError(f"{path}: source-row identity differs at {ordinal}")
                try:
                    raw_stamp = datetime.strptime(record["source_timestamp"], "%Y-%d-%m %H:%M:%S")
                    session = date.fromisoformat(record["session_date_proxy"])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{path}: invalid source clock/session at {ordinal}") from exc
                stamp = _stamp(record["bar_start_timestamp"], ordinal)
                normalized = raw_stamp.replace(tzinfo=timezone(timedelta(hours=-4))).astimezone(ZoneInfo("America/New_York")).replace(tzinfo=None)
                if normalized != stamp:
                    raise ValueError(f"{path}: inferred clock normalization differs at {ordinal}")
                completion = (_stamp(record["bar_completion_timestamp_proxy"], ordinal)
                              if record["bar_completion_timestamp_proxy"] else None)
                opening, high, low, closing = [_decimal(record[key], ordinal) for key in ("open", "high", "low", "close")]
                if not low <= min(opening, closing) <= max(opening, closing) <= high:
                    raise ValueError(f"{path}: invalid OHLC at {ordinal}")
                if session != stamp.date() + timedelta(days=stamp.hour >= 18):
                    raise ValueError(f"{path}: session rollover differs at {ordinal}")
                status = record["completion_proxy_status"]
                if completion is not None and completion < stamp:
                    raise ValueError(f"{path}: completion precedes opening at {ordinal}")
                if status in COMPLETED:
                    if completion is None or completion.date() + timedelta(days=completion.hour >= 18) != session:
                        raise ValueError(f"{path}: completed proxy outside session at {ordinal}")
                    duration = _decimal(record["bar_duration_seconds_proxy"], ordinal)
                    if duration != Decimal(str((completion - stamp).total_seconds())):
                        raise ValueError(f"{path}: duration differs at {ordinal}")
                elif record["bar_duration_seconds_proxy"]:
                    _decimal(record["bar_duration_seconds_proxy"], ordinal)
                if raw_reader is not None:
                    original = next(raw_reader, None)
                    expected_raw = [record[key] for key in ("source_timestamp", "open", "high", "low", "close")]
                    if original != expected_raw:
                        raise ValueError(f"{path}: original/enhanced row differs at {ordinal}")
                current = IndependentBar(ordinal, stamp, session, opening, high, low, closing, completion, status)
                if previous:
                    if stamp < previous.start:
                        raise ValueError(f"{path}: input timestamps regress at {ordinal}")
                    same_session = previous.session == current.session
                    expected_status = (
                        "next_bar_start_same_second" if previous.start == current.start else "next_bar_start_proxy"
                    ) if same_session else "unavailable_session_boundary"
                    if previous.status != expected_status or previous.completion != (stamp if same_session else None):
                        raise ValueError(f"{path}: adjacent completion differs after {previous.row}")
                    yield previous
                previous = current
            if previous:
                if previous.status != "unavailable_export_end" or previous.completion is not None:
                    raise ValueError(f"{path}: final completion is unsupported")
                yield previous
            if raw_reader is not None and next(raw_reader, None) is not None:
                raise ValueError(f"{path}: original/enhanced row count differs")
    finally:
        if source_handle:
            source_handle.close()


def barrier(bar: IndependentBar, excluded_sessions: set[date]) -> str | None:
    if bar.session in excluded_sessions:
        return "excluded_session"
    if bar.status not in COMPLETED:
        return f"completion_status:{bar.status or 'missing'}"
    return None


def observe_inputs(bars: Iterable[IndependentBar], excluded_sessions: set[date], totals: dict) -> Iterator[IndependentBar]:
    """Reproduce all loader diagnostics, without importing its implementation."""
    totals.update({"input_rows": 0, "primary_eligible_bars": 0, "doji_eligible_bars": 0,
                   "same_second_eligible_bars": 0, "duplicate_adjacent_rows": 0})
    previous: IndependentBar | None = None

    def increment(category: str, key: str) -> None:
        cell = totals.setdefault(category, {})
        cell[key] = cell.get(key, 0) + 1

    for bar in bars:
        totals["input_rows"] += 1
        increment("completion_status_counts", bar.status or "missing")
        if previous and (bar.start, bar.opening, bar.high, bar.low, bar.closing) == (previous.start, previous.opening, previous.high, previous.low, previous.closing):
            totals["duplicate_adjacent_rows"] += 1
            examples = totals.setdefault("duplicate_examples", [])
            if len(examples) < 10:
                examples.append({"source_row": bar.row, "previous_source_row": bar.row - 1,
                                 "start_timestamp": bar.start.isoformat(sep=" ")})
        reason = barrier(bar, excluded_sessions)
        if reason:
            increment("barrier_counts", reason)
            if reason == "excluded_session":
                increment("excluded_session_counts", bar.session.isoformat())
        else:
            totals["primary_eligible_bars"] += 1
            totals["doji_eligible_bars"] += bar.direction is None
            totals["same_second_eligible_bars"] += bar.status == "next_bar_start_same_second"
        previous = bar
        yield bar


def window_ids(stamp: datetime, windows: list[dict]) -> list[str]:
    """Independent inclusive-start/exclusive-end normalized clock membership."""
    seconds = stamp.hour * 3600 + stamp.minute * 60 + stamp.second + stamp.microsecond / 1_000_000
    result = ["all_hours"]
    for window in windows:
        hour, minute = map(int, window["start"].split(":"))
        start = hour * 3600 + minute * 60
        hour, minute = map(int, window["end"].split(":"))
        end = hour * 3600 + minute * 60
        if (start <= seconds < end) if start < end else (seconds >= start or seconds < end):
            result.append(window["id"])
    return result


def compare_row(expected: dict, actual: dict[str, str], context: str) -> None:
    if set(expected) != set(actual):
        raise ValueError(f"{context}: saved columns differ")
    for key, value in expected.items():
        saved = actual[key]
        matches = False
        if value is None:
            matches = saved == ""
        elif isinstance(value, bool):
            matches = saved.lower() == str(value).lower()
        elif isinstance(value, int):
            try:
                matches = int(saved) == value
            except ValueError:
                pass
        elif isinstance(value, float):
            try:
                parsed = float(saved)
                matches = math.isfinite(parsed) and math.isclose(parsed, value, rel_tol=1e-12, abs_tol=1e-12)
            except ValueError:
                pass
        elif isinstance(value, Decimal):
            try:
                matches = Decimal(saved) == value
            except InvalidOperation:
                pass
        elif isinstance(value, (datetime, date)):
            try:
                matches = type(value).fromisoformat(saved) == value
            except ValueError:
                pass
        else:
            matches = str(value) == saved
        if not matches:
            raise ValueError(f"{context}: {key}: expected {value!r}, saved {saved!r}")


def compare_csv(expected: Iterable[dict], path: Path) -> int:
    count = 0
    with regular(path).open(newline="", encoding="utf-8") as handle:
        for ordinal, (wanted, actual) in enumerate(zip_longest(expected, csv.DictReader(handle)), 1):
            if wanted is None or actual is None:
                raise ValueError(f"{path}: saved row count differs at {ordinal}")
            compare_row(wanted, actual, f"{path.name}: row {ordinal}")
            count += 1
    return count


def verify_frozen_stage(stage: Path, settings_path: Path, lock_path: Path) -> dict:
    """Require settings, input lock and verifier bytes retained before execution."""
    if settings_path.absolute() != (stage / "config.json").absolute() or lock_path.absolute() != (stage / "inputs.lock.json").absolute():
        raise ValueError("Audit settings and input lock must be the frozen stage files")
    receipt = read_json(stage / "provenance/execution-start.json")
    if receipt.get("study_id") != STUDY_ID or receipt.get("run_id") != stage.name:
        raise ValueError("Execution provenance identity differs from audited stage")
    inventory = [*receipt.get("execution_sources", []), *receipt.get("frozen_inputs", [])]
    if not inventory:
        raise ValueError("Frozen source/protocol inventory required")
    own_path = f"studies/{STUDY_ID}/pullback_audit.py"
    if not any(item.get("path") == own_path for item in receipt.get("execution_sources", [])):
        raise ValueError("Independent verifier must be retained in pre-execution source snapshot")
    snapshot_names = set()
    for item in inventory:
        canonical = located(WORKSPACE, item["path"])
        retained = located(stage, item["snapshot_path"])
        if retained.relative_to(stage).as_posix() in snapshot_names:
            raise ValueError("Duplicate frozen snapshot locator")
        snapshot_names.add(retained.relative_to(stage).as_posix())
        if (digest(canonical) != item["sha256"] or digest(retained) != item["sha256"]
                or canonical.stat().st_size != item["bytes"] or retained.stat().st_size != item["bytes"]):
            raise ValueError(f"Frozen source/protocol bytes changed: {item['path']}")
    if "inputs.lock.json" not in snapshot_names:
        raise ValueError("Frozen input lock absent from execution provenance")
    config_pins = [item for item in inventory if item["snapshot_path"] in ("study.yaml", "reversal.yaml", "pullback.yaml", "config.json")]
    if not config_pins or digest(settings_path) not in {item["sha256"] for item in config_pins}:
        raise ValueError("Frozen configuration does not match executed protocol settings")
    return {"execution_start_sha256": digest(stage / "provenance/execution-start.json"),
            "settings_sha256": digest(settings_path), "inputs_lock_sha256": digest(lock_path),
            "source_inventory": [{"path": item["path"], "sha256": item["sha256"],
                                  "snapshot_path": item["snapshot_path"]} for item in inventory]}


def verify_input_pins(lock: dict, publication_root: Path) -> list[dict]:
    files = lock.get("files", [])
    if len(files) != 6 or {(item.get("role"), item.get("setting_ticks")) for item in files} != {(role, setting) for role in ("source", "enhanced") for setting in (4, 5, 6)}:
        raise ValueError("Independent reversal audit requires all six pinned ES source/enhanced files")
    if len(lock.get("manifests", [])) != 1 or not isinstance(lock.get("clock_migration"), dict):
        raise ValueError("Pinned export manifest and clock migration are required")
    result = []
    for item in [*files, *lock["manifests"], lock["clock_migration"]]:
        root_alias = item["root_alias"]
        if root_alias not in ("publication_root", "workspace_root"):
            raise ValueError("Unsupported pinned root alias")
        path = located(publication_root if root_alias == "publication_root" else WORKSPACE, item["path"])
        actual_hash = digest(path)
        if actual_hash != item["sha256"] or ("bytes" in item and path.stat().st_size != item["bytes"]):
            raise ValueError(f"Pinned input bytes changed: {item['path']}")
        result.append({"path": item["path"], "root_alias": root_alias,
                       "sha256": actual_hash, "bytes": path.stat().st_size,
                       "role": item.get("role", "clock_migration")})
    return result


HORIZONS = tuple(range(1, 21))
LEVELS = (25, 50, 75, 100)
COHORTS = ("all", *(str(n) for n in range(1, 11)), "11-15", "16-20", "21+", "unknown_start")


def reconstruct_segment(segment: list[IndependentBar], setting: int, ending: str, payoff_sink=None) -> Iterator[dict]:
    """Select A→one B→R by independent backward scans within observed segments."""
    if len(segment) < 3:
        return
    signs = [bar.direction for bar in segment]
    for index in range(2, len(segment)):
        direction = signs[index]
        if (direction is None or signs[index - 1] is None
                or direction == signs[index - 1] or signs[index - 2] != direction):
            continue
        # B cannot belong to a larger opposite leg because A is immediately
        # before it and its direction equals R. Selection uses no future row.
        a_first = index - 2
        while a_first > 0 and signs[a_first - 1] == direction:
            a_first -= 1
        earlier_first, earlier_last = segment[a_first], segment[index - 2]
        b, r = segment[index - 1], segment[index]
        a_length = index - 1 - a_first
        last = index
        while last + 1 < len(segment) and signs[last + 1] == direction:
            last += 1
        breaker = segment[last + 1] if last + 1 < len(segment) else None
        f1 = segment[index + 1] if index + 1 < len(segment) else None
        count = last - index
        event = {
            "setting_ticks": setting, "direction": direction,
            "earlier_start_source_row": earlier_first.row,
            "earlier_end_source_row": earlier_last.row,
            "earlier_start_timestamp": earlier_first.start,
            "earlier_end_timestamp": earlier_last.start,
            "earlier_observed_length": a_length,
            "earlier_start_known": a_first > 0,
            "pullback_source_row": b.row, "pullback_start_timestamp": b.start,
            "pullback_available_at": b.completion, "pullback_open": b.opening,
            "pullback_high": b.high, "pullback_low": b.low, "pullback_close": b.closing,
            "source_row": r.row, "previous_source_row": b.row,
            "start_timestamp": r.start, "available_at": r.completion,
            "session_date": r.session, "open": r.opening,
            "high": r.high, "low": r.low, "close": r.closing,
            "follow_count": count, "exact_follow_count": count if breaker else None,
            "right_censored": breaker is None,
            "end_reason": ("doji" if breaker.direction is None else "reversal") if breaker else ending,
            "termination_available_at": breaker.completion if breaker else None,
            "f1_source_row": f1.row if f1 else None, "f1_start_timestamp": f1.start if f1 else None,
            "f1_available_at": f1.completion if f1 else None, "f1_open": f1.opening if f1 else None,
            "f1_high": f1.high if f1 else None, "f1_low": f1.low if f1 else None,
            "f1_close": f1.closing if f1 else None,
            "earlier_exact_length": a_length if a_first > 0 else None, "f1_known": f1 is not None,
        }
        bullish = direction == "bullish"
        for level in LEVELS:
            price = r.closing + (r.opening - r.closing) * Decimal(level) / 100
            event[f"retrace_price_{level}"] = price
            event[f"touch_{level}"] = (f1.low <= price if bullish else f1.high >= price) if f1 else None
        event["favorable_beyond_close"] = (f1.closing > r.closing if bullish else f1.closing < r.closing) if f1 else None
        event["favorable_same_colour"] = (f1.closing > f1.opening if bullish else f1.closing < f1.opening) if f1 else None
        if payoff_sink is not None:
            for target in (1, 2):
                payoff_sink(reconstruct_payoff(event, segment[index + 1:], target, ending))
        yield event


def reconstruct_events(bars: Iterable[IndependentBar], setting: int, excluded_sessions: set[date], *, payoff_sink=None) -> Iterator[dict]:
    """Retain all source barriers; buffer only one eligible inferred session."""
    segment = []
    previous: IndependentBar | None = None
    for bar in bars:
        reason = None
        if previous:
            if bar.row <= previous.row:
                raise ValueError("Independent source rows must increase")
            if bar.row != previous.row + 1:
                reason = "source_row_gap"
            elif bar.session != previous.session:
                reason = "session_boundary"
        if reason:
            yield from reconstruct_segment(segment, setting, reason, payoff_sink)
            segment = []
        previous = bar
        reason = barrier(bar, excluded_sessions)
        if reason:
            yield from reconstruct_segment(segment, setting, reason, payoff_sink)
            segment = []
        else:
            if bar.completion is None:
                raise ValueError("Completed pullback audit row lacks availability")
            segment.append(bar)
    yield from reconstruct_segment(segment, setting, "export_end", payoff_sink)

def empty_cell() -> dict:
    return {"events": 0, "censored": 0, "known_f1": 0, "earlier_known": 0,
            "sessions": 0, "f1_sessions": 0, "beyond": 0, "colour": 0,
            "outcomes": {n: {"success": 0, "failure": 0, "unknown": 0, "known_sessions": 0, "success_sessions": 0} for n in HORIZONS},
            "retracement": {level: {"touch": 0, "beyond": 0, "colour": 0, "sessions": 0} for level in LEVELS}}


def earlier_bucket(event: dict) -> str:
    if not event["earlier_start_known"]:
        return "unknown_start"
    length = event["earlier_exact_length"]
    if length is None or length < 1 or length != event["earlier_observed_length"]:
        raise ValueError("Independent exact prior-leg identity is invalid")
    if length <= 10:
        return str(length)
    if length <= 15:
        return "11-15"
    if length <= 20:
        return "16-20"
    return "21+"


def collect_event(cells: dict, event: dict, windows: list[dict]) -> None:
    session = event["session_date"]
    offset = (session - date(2019, 1, 1)).days
    if offset < 0 or offset > 2921:
        raise ValueError("Independent reversal session outside declared observed years")
    session_bit = 1 << offset
    keys = ((event["setting_ticks"], year, window, direction, bucket)
            for window in window_ids(event["available_at"], windows)
            for year in (None, session.year) for direction in (event["direction"], "all")
            for bucket in ("all", earlier_bucket(event)))
    for key in keys:
        if key not in cells:
            cells[key] = empty_cell()
        cell = cells[key]
        cell["events"] += 1
        cell["censored"] += event["right_censored"]
        cell["earlier_known"] += event["earlier_start_known"]
        cell["sessions"] |= session_bit
        for n in HORIZONS:
            horizon = cell["outcomes"][n]
            if n <= event["follow_count"]:
                horizon["success"] += 1
                horizon["success_sessions"] |= session_bit
                horizon["known_sessions"] |= session_bit
            elif event["right_censored"]:
                horizon["unknown"] += 1
            else:
                horizon["failure"] += 1
                horizon["known_sessions"] |= session_bit
        if event["f1_known"]:
            cell["known_f1"] += 1
            cell["f1_sessions"] |= session_bit
            cell["beyond"] += event["favorable_beyond_close"]
            cell["colour"] += event["favorable_same_colour"]
            for level in LEVELS:
                retracement = cell["retracement"][level]
                if event[f"touch_{level}"]:
                    retracement["touch"] += 1
                    retracement["sessions"] |= session_bit
                    retracement["beyond"] += event["favorable_beyond_close"]
                    retracement["colour"] += event["favorable_same_colour"]


def collect_coverage(coverage: dict, bar: IndependentBar, setting: int, windows: list[dict]) -> None:
    for window in window_ids(bar.start, windows):
        for year in (None, bar.session.year):
            key = (setting, year, window)
            if key not in coverage:
                coverage[key] = {"bars": 0, "sessions": set()}
            coverage[key]["bars"] += 1
            coverage[key]["sessions"].add(bar.session.isoformat())


def verify_group_conservation(cells: dict) -> None:
    """Assert disjoint prior cohorts, directions and years preserve pooled counts."""
    def merge(parts: list[dict]) -> dict:
        merged = empty_cell()
        for part in parts:
            for key in ("events", "censored", "known_f1", "earlier_known", "beyond", "colour"):
                merged[key] += part[key]
            for key in ("sessions", "f1_sessions"):
                merged[key] |= part[key]
            for n in HORIZONS:
                for key in ("success", "failure", "unknown"):
                    merged["outcomes"][n][key] += part["outcomes"][n][key]
                for key in ("known_sessions", "success_sessions"):
                    merged["outcomes"][n][key] |= part["outcomes"][n][key]
            for level in LEVELS:
                for key in ("touch", "beyond", "colour"):
                    merged["retracement"][level][key] += part["retracement"][level][key]
                merged["retracement"][level]["sessions"] |= part["retracement"][level]["sessions"]
        return merged

    empty = empty_cell()
    for key, cell in cells.items():
        setting, year, window, direction, bucket = key
        if bucket == "all":
            parts = [cells.get((setting, year, window, direction, name), empty) for name in COHORTS[1:]]
            if merge(parts) != cell:
                raise ValueError("Independent prior-leg cohort conservation failed")
        if direction == "all":
            parts = [cells.get((setting, year, window, name, bucket), empty) for name in ("bullish", "bearish")]
            if merge(parts) != cell:
                raise ValueError("Independent pooled direction conservation failed")
        if year is None:
            parts = [cells.get((setting, value, window, direction, bucket), empty) for value in range(2019, 2027)]
            if merge(parts) != cell:
                raise ValueError("Independent annual-to-overall conservation failed")
        successes = [cell["outcomes"][n]["success"] for n in HORIZONS]
        if successes != sorted(successes, reverse=True):
            raise ValueError("Independent horizon success counts increase")
        touches = [cell["retracement"][level]["touch"] for level in LEVELS]
        if touches != sorted(touches, reverse=True):
            raise ValueError("Independent retracement touch counts increase with depth")
        for level in LEVELS:
            result = cell["retracement"][level]
            if not (0 <= result["beyond"] <= result["touch"] <= cell["known_f1"]
                    and 0 <= result["colour"] <= result["touch"]):
                raise ValueError("Independent joint retracement count bounds failed")


def expected_tables(cells: dict, coverage: dict, settings: list[int], years: list[int], windows: list[dict]) -> dict:
    tables = {"summary": [], "continuation": [], "retracement": [], "coverage": []}
    for setting in settings:
        for year in (None, *years):
            for window in ("all_hours", *(row["id"] for row in windows)):
                covered = coverage.get((setting, year, window), {"bars": 0, "sessions": set()})
                dates = sorted(covered["sessions"])
                coverage_fields = {"eligible_bar_count": covered["bars"], "covered_sessions": len(dates),
                                   "first_session_date": dates[0] if dates else None,
                                   "last_session_date": dates[-1] if dates else None}
                tables["coverage"].append({"setting_ticks": setting, "year": year, "timeframe_id": window, **coverage_fields})
                for direction in ("bullish", "bearish", "all"):
                    for bucket in COHORTS:
                        cell = cells.get((setting, year, window, direction, bucket))
                        if cell is None:
                            cell = empty_cell()
                        base = {"setting_ticks": setting, "year": year, "timeframe_id": window, "direction": direction, "earlier_leg_bucket": bucket}
                        tables["summary"].append({
                            **base, "event_count": cell["events"], "exact_followup_count": cell["events"] - cell["censored"],
                            "censored_followup_count": cell["censored"], "known_f1_count": cell["known_f1"],
                            "unknown_f1_count": cell["events"] - cell["known_f1"], "earlier_start_known_count": cell["earlier_known"],
                            "earlier_start_unknown_count": cell["events"] - cell["earlier_known"],
                            "sessions_with_events": cell["sessions"].bit_count(), "sessions_with_known_f1": cell["f1_sessions"].bit_count(),
                            **coverage_fields, "bar_coverage_anchor": "bar_start_timestamp",
                            "event_membership_anchor": "setup_R_completion_timestamp_proxy",
                        })
                        for n in HORIZONS:
                            horizon = cell["outcomes"][n]
                            successes, failures, unknown = (horizon[key] for key in ("success", "failure", "unknown"))
                            denominator = successes + failures
                            if successes + failures + unknown != cell["events"]:
                                raise ValueError("Independent continuation count conservation failed")
                            tables["continuation"].append({
                                **base, "n": n, "event_count": cell["events"], "success_count": successes,
                                "failure_count": failures, "unknown_count": unknown, "numerator": successes,
                                "denominator": denominator, "probability": successes / denominator if denominator else None,
                                "sessions_with_events": cell["sessions"].bit_count(), "sessions_with_known_outcome": horizon["known_sessions"].bit_count(),
                                "sessions_with_success": horizon["success_sessions"].bit_count(), "units": "followers_after_R",
                            })
                        for level in LEVELS:
                            result = cell["retracement"][level]
                            touched = result["touch"]
                            valid = cell["known_f1"]
                            tables["retracement"].append({
                                **base, "level_percent": level, "event_count": cell["events"],
                                "valid_f1_count": valid, "unknown_f1_count": cell["events"] - valid,
                                "touch_count": touched, "touch_numerator": touched, "touch_denominator": valid,
                                "touch_probability": touched / valid if valid else None,
                                "sessions_with_events": cell["sessions"].bit_count(), "sessions_with_valid_f1": cell["f1_sessions"].bit_count(),
                                "sessions_with_touch": result["sessions"].bit_count(), "beyond_close_count": cell["beyond"],
                                "same_colour_count": cell["colour"],
                                "joint_beyond_close_numerator": result["beyond"], "joint_beyond_close_denominator": valid,
                                "joint_beyond_close_probability": result["beyond"] / valid if valid else None,
                                "conditional_beyond_close_numerator": result["beyond"], "conditional_beyond_close_denominator": touched,
                                "conditional_beyond_close_probability": result["beyond"] / touched if touched else None,
                                "joint_same_colour_numerator": result["colour"], "joint_same_colour_denominator": valid,
                                "joint_same_colour_probability": result["colour"] / valid if valid else None,
                                "conditional_same_colour_numerator": result["colour"], "conditional_same_colour_denominator": touched,
                                "conditional_same_colour_probability": result["colour"] / touched if touched else None,
                                "units": "fraction_of_R_body",
                            })
    return tables


def reconstruct_payoff(event: dict, following: list[IndependentBar], target: int, ending: str) -> dict:
    """Independent finite-path evaluation, retaining dual-touch order bounds."""
    bullish = event['direction'] == 'bullish'
    sign = Decimal(1 if bullish else -1)
    stop = min(event['pullback_low'], event['low']) - Decimal('0.25') if bullish else max(event['pullback_high'], event['high']) + Decimal('0.25')
    result = {key: event[key] for key in ('setting_ticks','direction','source_row','available_at','session_date',
                                        'earlier_observed_length','earlier_start_known','earlier_exact_length')}
    result.update(target_multiple=target, horizon_candles=10, entry_source_row=None,
                  entry_start_timestamp=None, entry_price=None, stop_price=stop,
                  target_price=None, risk_points=None, status='unknown', exit_reason='f1_unavailable',
                  bars_observed=0, exit_source_row=None, exit_available_at=None, exit_price=None,
                  payoff_lower_r=None, payoff_upper_r=None)
    if not following:
        return result
    first = following[0]
    if first.row != event['source_row'] + 1:
        raise ValueError('Independent F1 is not contiguous with R')
    risk = sign * (first.opening-stop)
    result.update(entry_source_row=first.row, entry_start_timestamp=first.start,
                  entry_price=first.opening, risk_points=risk)
    if risk <= 0:
        result.update(status='invalid', exit_reason='nonpositive_entry_to_stop_risk')
        return result
    target_price = first.opening + sign * risk * target
    result['target_price'] = target_price
    for count, bar in enumerate(following[:10], 1):
        result['bars_observed'] = count
        stop_open = bar.opening <= stop if bullish else bar.opening >= stop
        target_open = bar.opening >= target_price if bullish else bar.opening <= target_price
        if stop_open or target_open:
            value = sign * (bar.opening-first.opening) / risk
            result.update(status='resolved', exit_reason='stop_open_gap' if stop_open else 'target_open_gap',
                          exit_source_row=bar.row, exit_available_at=bar.start, exit_price=bar.opening,
                          payoff_lower_r=value, payoff_upper_r=value)
            return result
        stop_touch = bar.low <= stop if bullish else bar.high >= stop
        target_touch = bar.high >= target_price if bullish else bar.low <= target_price
        if stop_touch or target_touch:
            status = 'ambiguous' if stop_touch and target_touch else 'resolved'
            reason = 'both_touch' if status == 'ambiguous' else 'stop_touch' if stop_touch else 'target_touch'
            lower = Decimal(-1) if stop_touch else Decimal(target)
            upper = Decimal(target) if target_touch else Decimal(-1)
            price = None if status == 'ambiguous' else stop if stop_touch else target_price
            result.update(status=status, exit_reason=reason, exit_source_row=bar.row,
                          exit_available_at=bar.completion, exit_price=price,
                          payoff_lower_r=lower, payoff_upper_r=upper)
            return result
        if count == 10:
            value = sign*(bar.closing-first.opening)/risk
            result.update(status='marked', exit_reason='horizon_close', exit_source_row=bar.row,
                          exit_available_at=bar.completion, exit_price=bar.closing,
                          payoff_lower_r=value, payoff_upper_r=value)
            return result
    result['exit_reason'] = ending
    return result


def empty_payoff_cell() -> dict:
    return {'events':0, 'valid':0, 'invalid':0, 'unknown_entry':0, 'known':0, 'unknown':0,
            'resolved':0, 'ambiguous':0, 'marked':0, 'target_touch':0, 'stop_touch':0,
            'gap_target':0, 'gap_stop':0, 'win_lower':0, 'win_upper':0,
            'lower_sum':Decimal(0), 'upper_sum':Decimal(0), 'sessions':0,
            'valid_sessions':0, 'known_sessions':0}


def collect_payoff(cells: dict, result: dict, windows: list[dict]) -> None:
    session = result['session_date']
    bit = 1 << (session-date(2019,1,1)).days
    for window in window_ids(result['available_at'], windows):
        for year in (None,session.year):
            for direction in (result['direction'],'all'):
                for bucket in ('all',earlier_bucket(result)):
                    key=(result['setting_ticks'],year,window,direction,bucket,result['target_multiple'])
                    if key not in cells:
                        cells[key]=empty_payoff_cell()
                    c=cells[key]
                    c['events']+=1
                    c['sessions']|=bit
                    if result['risk_points'] is not None and result['risk_points']>0:
                        c['valid']+=1;c['valid_sessions']|=bit
                    status=result['status']
                    if status=='invalid':
                        c['invalid']+=1
                    elif status=='unknown':
                        c['unknown']+=1;c['unknown_entry']+=result['entry_price'] is None
                    else:
                        c['known']+=1;c['known_sessions']|=bit;c[status]+=1
                        c['lower_sum']+=result['payoff_lower_r'];c['upper_sum']+=result['payoff_upper_r']
                        c['win_lower']+=result['payoff_lower_r']>0;c['win_upper']+=result['payoff_upper_r']>0
                        c['target_touch']+=result['exit_reason']=='target_touch'
                        c['stop_touch']+=result['exit_reason']=='stop_touch'
                        c['gap_target']+=result['exit_reason']=='target_open_gap'
                        c['gap_stop']+=result['exit_reason']=='stop_open_gap'


def expected_payoff_tables(cells: dict, settings: list[int], years: list[int], windows: list[dict]) -> list[dict]:
    rows=[]
    for setting in settings:
        for year in (None,*years):
            for window in ('all_hours',*(w['id'] for w in windows)):
                for direction in ('bullish','bearish','all'):
                    for bucket in COHORTS:
                        for target in (1,2):
                            c=cells.get((setting,year,window,direction,bucket,target),empty_payoff_cell())
                            n=c['known'];lo=c['lower_sum'];hi=c['upper_sum']
                            rows.append({'setting_ticks':setting,'year':year,'timeframe_id':window,
                                'direction':direction,'earlier_leg_bucket':bucket,'target_multiple':target,
                                'horizon_candles':10,'event_count':c['events'],'valid_entry_count':c['valid'],
                                'invalid_entry_count':c['invalid'],'unknown_entry_count':c['unknown_entry'],
                                'known_outcome_count':n,'unknown_outcome_count':c['unknown'],
                                'resolved_count':c['resolved'],'ambiguous_count':c['ambiguous'],'marked_count':c['marked'],
                                'target_touch_count':c['target_touch'],'stop_touch_count':c['stop_touch'],
                                'gap_target_count':c['gap_target'],'gap_stop_count':c['gap_stop'],
                                'win_lower_numerator':c['win_lower'],'win_upper_numerator':c['win_upper'],
                                'denominator':n,'win_rate_lower':c['win_lower']/n if n else None,
                                'win_rate_upper':c['win_upper']/n if n else None,
                                'payoff_lower_sum_r':lo,'payoff_upper_sum_r':hi,
                                'mean_lower_r':float(lo/n) if n else None,'mean_upper_r':float(hi/n) if n else None,
                                'sessions_with_events':c['sessions'].bit_count(),
                                'sessions_with_valid_entry':c['valid_sessions'].bit_count(),
                                'sessions_with_known_outcome':c['known_sessions'].bit_count(),
                                'units':'gross_ohlc_price_path_R_proxy'})
    return rows


def verify_payoff_conservation(cells: dict, event_cells: dict) -> None:
    empty=empty_payoff_cell()
    bit_fields={'sessions','valid_sessions','known_sessions'}
    def merge(parts):
        result=empty_payoff_cell()
        for part in parts:
            for key,value in part.items():
                if key in bit_fields:result[key]|=value
                else:result[key]+=value
        return result
    def matches(a,b):
        # Reordering additions of recurring Decimal R moves can differ at the
        # final context digit; counts and session masks remain exact.
        for key in a:
            if key in ('lower_sum','upper_sum'):
                if abs(a[key]-b[key])>Decimal('1e-20'):
                    return False
            elif a[key]!=b[key]:return False
        return True
    for key,c in cells.items():
        setting,year,window,direction,bucket,target=key
        if c['events']!=c['known']+c['unknown']+c['invalid']:
            raise ValueError('Independent payoff status count conservation failed')
        if c['known']!=c['resolved']+c['ambiguous']+c['marked']:
            raise ValueError('Independent payoff known-outcome count conservation failed')
        if c['events']!=c['valid']+c['invalid']+c['unknown_entry']:
            raise ValueError('Independent payoff entry count conservation failed')
        if not 0<=c['win_lower']<=c['win_upper']<=c['known'] or c['lower_sum']>c['upper_sum']:
            raise ValueError('Independent payoff bound conservation failed')
        if c['events']!=event_cells.get(key[:5],empty_cell())['events']:
            raise ValueError('Independent payoff/setup event alignment failed')
        if bucket=='all' and not matches(c,merge([cells.get((setting,year,window,direction,name,target),empty) for name in COHORTS[1:]])):
            raise ValueError('Independent payoff earlier-leg cohort conservation failed')
        if direction=='all' and not matches(c,merge([cells.get((setting,year,window,name,bucket,target),empty) for name in ('bullish','bearish')])):
            raise ValueError('Independent payoff direction conservation failed')
        if year is None and not matches(c,merge([cells.get((setting,y,window,direction,bucket,target),empty) for y in range(2019,2027)])):
            raise ValueError('Independent payoff annual-to-overall conservation failed')

def validate_protocol(settings: dict) -> tuple[list[dict], set[date]]:
    """Refuse declarations outside the independent verifier's frozen semantics."""
    if settings.get("study_id") != STUDY_ID or settings.get("protocol_version") != "0.4.0":
        raise ValueError("Unsupported independent pullback audit protocol version")
    scope = settings.get("scope", {})
    if scope.get("product") != "ES" or scope.get("selected_analysis_settings_ticks") != [4, 5, 6] or scope.get("pool_settings") is not False:
        raise ValueError("Unsupported independent pullback audit scope")
    reporting = settings.get("reporting", {})
    required_reporting = {
        "timezone": "America/New_York", "input_timestamp_basis": "already_normalized_inferred_new_york_wall_time",
        "interval_bounds": "start_inclusive_end_exclusive", "year_basis": "session_date_proxy",
        "session_rollover": "18:00", "event_membership_timestamp": "reversal_completion_timestamp_proxy",
        "bar_membership_timestamp": "bar_start_timestamp", "timeframe_membership": "independent_overlapping_filters",
        "outside_timeframes": "retain_in_all_hours_and_yearly_totals",
        "required_sections": ["overall", "yearly", "timeframes", "yearly_by_timeframe"],
        "empty_cells": {"count": 0, "estimate": None},
    }
    if any(reporting.get(key) != value for key, value in required_reporting.items()):
        raise ValueError("Unsupported independent pullback grouping/coverage declaration")
    windows = reporting.get("timeframes", [])
    expected_windows = [("asia", "20:00", "02:00"), ("london", "02:00", "09:00"),
                        ("ny", "09:30", "16:00"), ("asia_open", "19:30", "21:30"),
                        ("ny_open", "09:30", "10:30"), ("ny_am", "10:30", "12:30"),
                        ("ny_pm", "12:30", "16:00")]
    if [(row.get("id"), row.get("start"), row.get("end")) for row in windows] != expected_windows:
        raise ValueError("Unsupported independent pullback reporting windows")
    data = settings.get("data", {})
    if data.get("excluded_session_dates") != ["2026-09-24"] or data.get("availability") != "completion_proxy_only":
        raise ValueError("Unsupported independent pullback completion/exclusion declaration")
    expected_definition = {'available_at': 'R.bar_completion_timestamp_proxy',
     'barrier': 'unknown above observed followers; retain already-known successes',
     'body_retracement_percent': [25, 50, 75, 100],
     'conditional_denominator': 'known F1 candles touching the selected retracement level',
     'continuation': 'n uninterrupted additional completed candles with the same close-open sign as R',
     'earlier_leg_buckets': ['all',
                             '1',
                             '2',
                             '3',
                             '4',
                             '5',
                             '6',
                             '7',
                             '8',
                             '9',
                             '10',
                             '11-15',
                             '16-20',
                             '21+',
                             'unknown_start'],
     'earlier_leg_membership': 'exact known-start A length before B; otherwise unknown_start; all overlaps '
                               'disjoint buckets',
     'earlier_start_unknown': 'retain A with unknown start in unknown_start; never assign an exact-length cohort',
     'favorable_primary': 'strict F1.close beyond R.close in R direction',
     'favorable_secondary': 'F1 close-open sign equals R direction, saved separately',
     'horizons': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
     'joint_denominator': 'all reversals with known eligible completed F1',
     'n_excludes_reversal': True,
     'opposite_or_doji': 'observed failure for every larger horizon',
     'retracement_horizon': 'F1 only, immediate next original candle, completed eligible and same inferred '
                            'session',
     'selection': 'nonempty completed directional earlier leg A, exactly one completed opposite candle B, then '
                  'completed R in A direction; contiguous original rows in one eligible inferred session',
     'touch': 'inclusive F1 low/high reaches R.close toward R.open by the selected fraction of exact R body',
     'uncertainty': 'empirical descriptive rates only; no iid confidence intervals, no population forecast, no '
                    'profitability claim',
     'unknown': 'blank estimates; never count unknown as failure',
     'window_boundary': 'full follow-up within same inferred session; never truncate at named windows'}
    if settings.get("pullback_definition") != expected_definition:
        raise ValueError("Unsupported independent pullback event/outcome declaration")
    expected_payoff = {'barrier': 'unresolved before ten candles is unknown; already resolved outcomes remain known',
     'both_extrema_cross': 'unknown intrabar order; payoff lower=-1R and upper=target_r',
     'costs': 'none; gross reference-price moves only',
     'denominator': 'known proxy outcomes only; retain missing_entry, invalid_risk and unresolved_unknown counts '
                    'separately',
     'entry': 'F1.open of immediate completed eligible next source candle in the same inferred session',
     'favorable': 'strictly positive R payoff; ambiguous outcomes contribute conservative lower and upper win '
                  'bounds',
     'horizon_bars': 10,
     'nominal_price_buffer': '0.25',
     'opening_cross': 'evaluate open before extrema; crossed stop or target exits at observed exported open, '
                      'yielding signed open-minus-entry divided by risk',
     'path': 'first ten contiguous completed eligible physical candles starting F1, including opposite and doji '
             'candles',
     'pooling': 'each target is a separate scenario; overlapping setups retained, no portfolio equity or '
                'simultaneous-position claim',
     'risk': 'positive direction-signed entry-minus-stop distance; otherwise invalid_risk',
     'single_extremum_cross': 'stop only yields -1R; target only yields target_r',
     'status': 'gross_ohlc_price_path_proxy_not_executable_pnl',
     'stop': 'bullish min(B.low,R.low)-0.25; bearish max(B.high,R.high)+0.25',
     'target_r': [1, 2],
     'timeout': 'no level crossed by tenth completed candle; use direction-signed tenth close-minus-entry '
                'divided by risk',
     'uncertainty': 'exploratory descriptive history, no independent-trade confidence intervals, no executable '
                    'fills, net returns or dollars'}
    if settings.get("payoff_proxy_definition") != expected_payoff:
        raise ValueError("Unsupported independent pullback payoff-proxy declaration")
    trend = settings.get("trend_definition", {})
    if (trend.get("direction") != "exact_decimal_sign_close_minus_open"
            or trend.get("doji") != "breaks_run_and_is_not_a_directional_candle"
            or trend.get("primary_completed_statuses") != ["next_bar_start_proxy", "next_bar_start_same_second"]
            or trend.get("identical_rows") != "retain_original_rows_and_flag_only"
            or trend.get("same_second_rows") != "retain_source_row_order"):
        raise ValueError("Unsupported independent pullback body-sign/source-order declaration")
    return windows, {date(2026, 9, 24)}


def audit_stage(stage: Path, ledger_dir: Path, publication_root: Path, settings_path: Path, lock_path: Path) -> dict:
    """Compare every input diagnostic, event identity/outcome and saved table cell."""
    if sys.flags.optimize:
        raise ValueError("Ordinary Python independent pullback verification is required")
    stage, ledger_dir, publication_root = stage.absolute(), ledger_dir.absolute(), publication_root.absolute()
    frozen = verify_frozen_stage(stage, settings_path, lock_path)
    settings, lock = read_json(settings_path), read_json(lock_path)
    windows, exclusions = validate_protocol(settings)
    if lock.get("study_id") != STUDY_ID:
        raise ValueError("Independent pullback audit input-lock identity differs")
    pins = verify_input_pins(lock, publication_root)
    try:
        ledger_dir.relative_to(stage)
    except ValueError as exc:
        raise ValueError("Independent pullback ledger directory must be inside the stage") from exc
    expected_artifacts = {f"evidence/pullbacks_{setting}t.csv" for setting in (4, 5, 6)} | {f"evidence/payoff_{setting}t.csv" for setting in (4,5,6)} | {
        "tables/pullback_summary.csv", "tables/pullback_continuation.csv",
        "tables/pullback_retracement.csv", "tables/pullback_payoff.csv", "tables/coverage.csv", "input-audit.json",
    }
    executed = read_json(stage / "provenance/execution-complete.json")
    if (executed.get("result") != "passed" or executed.get("study_id") != STUDY_ID
            or executed.get("run_id") != stage.name or set(executed.get("artifact_hashes", {})) != expected_artifacts):
        raise ValueError("Complete stage-bound pullback execution receipt required")
    artifact_hashes = {name: digest(located(stage, name)) for name in expected_artifacts}
    if artifact_hashes != executed["artifact_hashes"]:
        raise ValueError("Saved pullback artifacts differ from execution receipt")
    audits = read_json(stage / "input-audit.json")
    if (audits.get("schema_version") != 1 or audits.get("study_id") != STUDY_ID
            or audits.get("run_id") != stage.name or set(audits.get("settings", {})) != {"4", "5", "6"}):
        raise ValueError("Complete stage-bound pullback input diagnostic identity required")
    cells, coverage, payoff_cells, source_results = {}, {}, {}, []
    entries = sorted((item for item in lock["files"] if item["role"] == "enhanced"), key=lambda item: item["setting_ticks"])
    years = list(range(min(int(item["first_session_date_proxy"][:4]) for item in entries),
                       max(int(item["last_session_date_proxy"][:4]) for item in entries) + 1))
    if years != list(range(2019, 2027)):
        raise ValueError("Independent pullback audit requires declared 2019–2026 coverage")
    for entry in entries:
        setting = entry["setting_ticks"]
        source = located(publication_root, entry["path"])
        original_entry = next(item for item in lock["files"] if item["role"] == "source" and item["setting_ticks"] == setting)
        original = located(publication_root, original_entry["path"])
        ledger_path = located(ledger_dir, f"pullbacks_{setting}t.csv")
        ledger_relative = ledger_path.relative_to(stage).as_posix()
        if ledger_relative != f"evidence/pullbacks_{setting}t.csv":
            raise ValueError("Independent pullback audit requires the executed event ledger locators")
        totals = {}
        observed_dates = set()
        first_session = None
        last_session = None

        def observed_source() -> Iterator[IndependentBar]:
            nonlocal first_session, last_session
            for bar in observe_inputs(read_bars(source, raw_path=original), exclusions, totals):
                if first_session is None:
                    first_session = bar.session.isoformat()
                last_session = bar.session.isoformat()
                observed_dates.add(bar.session)
                if barrier(bar, exclusions) is None:
                    collect_coverage(coverage, bar, setting, windows)
                yield bar

        event_totals = Counter()
        payoff_path = located(ledger_dir, f"payoff_{setting}t.csv")
        if payoff_path.relative_to(stage).as_posix() != f"evidence/payoff_{setting}t.csv":
            raise ValueError("Independent payoff audit requires executed ledger locators")
        with regular(payoff_path).open(newline="", encoding="utf-8") as payoff_handle:
            payoff_reader = csv.DictReader(payoff_handle)
            payoff_count = 0
            def observe_payoff(expected: dict) -> None:
                nonlocal payoff_count
                payoff_count += 1
                actual = next(payoff_reader, None)
                if actual is None:
                    raise ValueError("Saved payoff ledger is shorter than independent setups")
                compare_row(expected, actual, f"{payoff_path.name}: row {payoff_count}")
                collect_payoff(payoff_cells, expected, windows)
                event_totals[f"proxy_status:{expected['status']}"] += 1

            def observed_events() -> Iterator[dict]:
                previous_row = 0
                for event in reconstruct_events(observed_source(), setting, exclusions, payoff_sink=observe_payoff):
                    if event["source_row"] <= previous_row:
                        raise ValueError("Independent pullback event order regressed")
                    previous_row = event["source_row"]
                    collect_event(cells, event, windows)
                    event_totals["events"] += 1
                    event_totals["right_censored"] += event["right_censored"]
                    event_totals["known_f1"] += event["f1_known"]
                    yield event

            count = compare_csv(observed_events(), ledger_path)
            if next(payoff_reader, None) is not None or payoff_count != 2*count:
                raise ValueError("Saved payoff ledger row count differs from two scenarios per setup")
        if totals != audits["settings"][str(setting)]:
            different = sorted(key for key in set(totals) | set(audits["settings"][str(setting)]) if totals.get(key) != audits["settings"][str(setting)].get(key))
            raise ValueError(f"Independent pullback loader diagnostics differ for {setting} ticks: {different}")
        if totals["input_rows"] != entry["rows"] or totals["input_rows"] != original_entry["rows"]:
            raise ValueError(f"Independent source row inventory differs for {setting} ticks")
        observed_inventory = {"first_session_date_proxy": first_session,
                              "last_session_date_proxy": last_session,
                              "session_dates_with_data": len(observed_dates)}
        for pinned in (entry, original_entry):
            if any(key in pinned and pinned[key] != value for key, value in observed_inventory.items()):
                raise ValueError(f"Independent source session inventory differs for {setting} ticks")
        source_results.append({"setting_ticks": setting, "input_path": entry["path"],
                               "input_sha256": entry["sha256"], "original_input_sha256": original_entry["sha256"],
                               "reconstructed_events": count, "reconstructed_payoffs": payoff_count, "event_counts": dict(event_totals),
                               "input_diagnostics": totals, "session_inventory": observed_inventory,
                               "ledger_sha256": artifact_hashes[ledger_relative],
                               "payoff_ledger_sha256": artifact_hashes[payoff_path.relative_to(stage).as_posix()]})
        print(json.dumps({"independent_audit_setting_ticks": setting, "input_rows": totals["input_rows"], "reconstructed_setups": count}), flush=True)
    verify_group_conservation(cells)
    verify_payoff_conservation(payoff_cells, cells)
    expected = expected_tables(cells, coverage, [4, 5, 6], years, windows)
    expected["payoff"] = expected_payoff_tables(payoff_cells, [4,5,6], years, windows)
    table_results = {}
    for name in ("summary", "continuation", "retracement", "coverage", "payoff"):
        relative = f"tables/pullback_{name}.csv" if name != "coverage" else "tables/coverage.csv"
        count = compare_csv(expected[name], located(stage, relative))
        table_results[name] = {"rows": count, "sha256": artifact_hashes[relative]}
    if verify_frozen_stage(stage, settings_path, lock_path) != frozen or verify_input_pins(lock, publication_root) != pins:
        raise ValueError("Independent pullback source/protocol changed during verification")
    if {name: digest(located(stage, name)) for name in expected_artifacts} != artifact_hashes:
        raise ValueError("Independent pullback artifacts changed during verification")
    return {
        "audit_version": "1.0.0", "status": "pass", "result": "passed", "study_id": STUDY_ID,
        "run_id": stage.name, "checked_at": datetime.now(timezone.utc).isoformat(),
        "command": {"argv": [sys.executable, *sys.argv], "cwd": str(Path.cwd()),
                    "python": {"executable": sys.executable, "version": sys.version,
                               "implementation": sys.implementation.name, "optimize": sys.flags.optimize}},
        "verifier": {"path": f"studies/{STUDY_ID}/pullback_audit.py", "sha256": digest(Path(__file__))},
        **frozen, "input_pins": pins, "excluded_sessions": [item.isoformat() for item in sorted(exclusions)],
        "sources": source_results, "tables": table_results, "artifact_hashes": artifact_hashes,
        "verified_scope": [
            "all six pinned source/enhanced file bytes, export manifest and clock-migration pins",
            "every enhanced input field, original raw-row parity, source order, adjacent completion and all loader diagnostics",
            "independent backward-scan A→exactly one B→R selection, earlier-start flags, full same-colour follower counts and tail censors",
            "every ordered event ledger cell, mirrored inclusive body touches and both strict beyond-close/same-colour endpoints",
            "all completion-anchored overall/year/window groups, all twenty known/unknown horizon denominators",
            "all fifteen exact/unknown earlier-A cohorts and disjoint cohort, direction and annual-to-overall conservation",
            "all two ordered payoff scenarios per setup; F1 reference, structural risk, gap-open precedence, dual-touch bounds, ten physical candles, censors",
            "all payoff counts, positive-payoff bounds, exact Decimal R sums, known-denominator means and matching scenario/setup cohorts",
            "all four retracement depths, marginal/joint/conditional rates and all source-opening coverage cells",
            "pre-execution frozen verifier/protocol/input lock and before/after artifact-byte stability",
        ],
        "limits": "Descriptive source reproduction does not verify ATAS construction, inferred clock, contract/roll treatment, market completeness, intrabar sequencing, executable fills, or predictive validity.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--ledger-dir", required=True, type=Path)
    parser.add_argument("--publication-root", required=True, type=Path)
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--inputs-lock", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    settings = args.settings or args.stage / "config.json"
    lock = args.inputs_lock or args.stage / "inputs.lock.json"
    if args.output and args.output.exists():
        raise ValueError("Independent pullback audit receipt overwrite refused")
    report = audit_stage(args.stage, args.ledger_dir, args.publication_root, settings, lock)
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
