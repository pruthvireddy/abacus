"""Independent standard-library audit of Study 22 saved directional-run evidence.

This verifier deliberately does not import the analytical engine or timeframe
helper. It reconstructs runs from the pinned input rows and projects retained
run lengths into the independently evaluated reporting windows.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable, Iterator
from itertools import zip_longest


COMPLETED = {"next_bar_start_proxy", "next_bar_start_same_second"}


@dataclass(frozen=True)
class ObservedBar:
    row: int
    start: datetime
    session: date
    direction: str | None
    completion: datetime | None
    status: str


def read_bars(path: Path) -> Iterator[ObservedBar]:
    """Read retained source order with exact prices and basic schema validation."""
    previous_start: datetime | None = None
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        required = {
            "source_row", "bar_start_timestamp", "session_date_proxy",
            "completion_proxy_status", "bar_completion_timestamp_proxy",
            "open", "high", "low", "close",
        }
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError(f"{path}: incomplete enhanced input schema")
        for ordinal, record in enumerate(reader, 1):
            try:
                row = int(record["source_row"])
                start = datetime.fromisoformat(record["bar_start_timestamp"])
                session = date.fromisoformat(record["session_date_proxy"])
                completion = (
                    datetime.fromisoformat(record["bar_completion_timestamp_proxy"])
                    if record["bar_completion_timestamp_proxy"] else None
                )
                opening, high, low, closing = (
                    Decimal(record[column]) for column in ("open", "high", "low", "close")
                )
            except (TypeError, ValueError, InvalidOperation) as exc:
                raise ValueError(f"{path}: malformed source row {ordinal}") from exc
            if row != ordinal:
                raise ValueError(f"{path}: source row identity is not sequential at {ordinal}")
            if start.tzinfo is not None or (completion and completion.tzinfo is not None):
                raise ValueError(f"{path}: timestamp must be normalized naive wall time")
            if previous_start is not None and start < previous_start:
                raise ValueError(f"{path}: bar timestamps regress at {ordinal}")
            if not all(value.is_finite() for value in (opening, high, low, closing)):
                raise ValueError(f"{path}: nonfinite price at {ordinal}")
            if not low <= min(opening, closing) <= max(opening, closing) <= high:
                raise ValueError(f"{path}: invalid OHLC ordering at {ordinal}")
            expected_session = start.date() + timedelta(days=start.hour >= 18)
            if session != expected_session:
                raise ValueError(f"{path}: session rollover mismatch at {ordinal}")
            direction = "bullish" if closing > opening else "bearish" if closing < opening else None
            yield ObservedBar(row, start, session, direction, completion, record["completion_proxy_status"])
            previous_start = start


def validate_completion(bars: Iterable[ObservedBar]) -> Iterator[ObservedBar]:
    """Check the proxy against the adjacent original row, including equal seconds."""
    pending: ObservedBar | None = None
    for current in bars:
        if pending is not None:
            same_session = pending.session == current.session
            expected_status = (
                "next_bar_start_same_second" if pending.start == current.start
                else "next_bar_start_proxy"
            ) if same_session else "unavailable_session_boundary"
            expected_completion = current.start if same_session else None
            if pending.status != expected_status or pending.completion != expected_completion:
                raise ValueError(f"completion metadata disagrees with next source row after {pending.row}")
            yield pending
        pending = current
    if pending is not None:
        if pending.status != "unavailable_export_end" or pending.completion is not None:
            raise ValueError("terminal source row must have unavailable_export_end completion")
        yield pending


def reconstruct_runs(
    bars: Iterable[ObservedBar], setting_ticks: int, excluded_session: date,
) -> Iterator[dict[str, object]]:
    """Independently reconstruct maximal same-body-sign runs and their censors.

    A reversal or doji establishes a known end and the next run's known start.
    Ineligible rows and session changes break continuity. The first observed
    directional segment has an unknown start; an unobserved end has unknown
    length even when every observed candle in the segment has a usable proxy.
    """
    active: list[ObservedBar] = []
    left_unknown = True
    active_left_unknown = True
    previous_session: date | None = None

    def finish(reason: str, right_unknown: bool, terminator: ObservedBar | None = None) -> dict[str, object]:
        first, last = active[0], active[-1]
        return {
            "setting_ticks": setting_ticks,
            "direction": first.direction,
            "start_source_row": first.row,
            "end_source_row": last.row,
            "start_timestamp": first.start.isoformat(sep=" "),
            "end_timestamp": last.start.isoformat(sep=" "),
            "session_date": first.session.isoformat(),
            "observed_length": len(active),
            "length": None if active_left_unknown or right_unknown else len(active),
            "left_censored": active_left_unknown,
            "right_censored": right_unknown,
            "end_reason": reason,
            "termination_available_at": (
                terminator.completion.isoformat(sep=" ") if terminator and terminator.completion else None
            ),
        }

    for bar in bars:
        if previous_session is not None and bar.session != previous_session:
            if active:
                yield finish("session_boundary", True)
                active = []
            left_unknown = True
        previous_session = bar.session
        barrier = (
            "excluded_session" if bar.session == excluded_session
            else f"completion_status:{bar.status or 'missing'}" if bar.status not in COMPLETED else None
        )
        if barrier:
            if active:
                yield finish(barrier, True)
                active = []
            left_unknown = True
            continue
        if bar.direction is None:
            if active:
                yield finish("doji", False, bar)
                active = []
            left_unknown = False
            continue
        if active and active[0].direction != bar.direction:
            yield finish("reversal", False, bar)
            active = []
            left_unknown = False
        if not active:
            active_left_unknown = left_unknown
        active.append(bar)
    if active:
        yield finish("export_end", True)


def window_ids(timestamp: str, windows: list[dict[str, object]]) -> list[str]:
    """Independent wall-clock membership; overnight ranges wrap midnight."""
    clock = datetime.fromisoformat(timestamp).time()
    seconds = clock.hour * 3600 + clock.minute * 60 + clock.second + clock.microsecond / 1_000_000
    result = ["all_hours"]
    for window in windows:
        start_hour, start_minute = map(int, str(window["start"]).split(":"))
        end_hour, end_minute = map(int, str(window["end"]).split(":"))
        start, end = start_hour * 3600 + start_minute * 60, end_hour * 3600 + end_minute * 60
        if (start <= seconds < end) if start < end else (seconds >= start or seconds < end):
            result.append(str(window["id"]))
    return result


def quantile(values: list[int], probability: float) -> float | None:
    """Linear sample quantile, with independently coded adjacent-rank weighting."""
    if not values:
        return None
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


HISTOGRAM = (
    ("1", 1, 1), ("2", 2, 2), ("3", 3, 3), ("4", 4, 4), ("5", 5, 5),
    ("6-7", 6, 7), ("8-9", 8, 9), ("10-14", 10, 14),
    ("15-19", 15, 19), ("20+", 20, None),
)
TAIL_THRESHOLDS = (2, 3, 5, 10, 20)


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def compare_row(expected: dict[str, object], actual: dict[str, str], context: str) -> None:
    """Require matching schemas and values, allowing only float roundoff."""
    if set(expected) != set(actual):
        raise ValueError(f"{context}: columns differ; expected {sorted(expected)}, observed {sorted(actual)}")
    for name, value in expected.items():
        saved = actual[name]
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
                matches = math.isfinite(float(saved)) and math.isclose(float(saved), value, rel_tol=1e-12, abs_tol=1e-12)
            except ValueError:
                pass
        elif name in {"start_timestamp", "end_timestamp", "termination_available_at"}:
            try:
                matches = datetime.fromisoformat(saved) == datetime.fromisoformat(str(value))
            except ValueError:
                pass
        else:
            matches = saved == str(value)
        if not matches:
            raise ValueError(f"{context}: {name}: expected {value!r}, saved {saved!r}")


def compare_csv(expected_rows: Iterable[dict[str, object]], path: Path) -> int:
    count = 0
    with path.open(newline="", encoding="utf-8") as handle:
        for ordinal, (expected, actual) in enumerate(zip_longest(expected_rows, csv.DictReader(handle)), 1):
            if expected is None or actual is None:
                raise ValueError(f"{path}: saved row count differs at {ordinal}")
            compare_row(expected, actual, f"{path.name}: row {ordinal}")
            count += 1
    return count


def empty_cell() -> dict[str, object]:
    return {
        "runs": 0, "left": 0, "right": 0, "unknown": 0,
        "lengths": [], "sessions": set(), "exact_sessions": set(),
    }


def collect_run(cells: dict, run: dict[str, object], windows: list[dict[str, object]]) -> None:
    session = str(run["session_date"])
    year = int(session[:4])
    for window in window_ids(str(run["start_timestamp"]), windows):
        for section_year in (None, year):
            for direction in (run["direction"], "all"):
                key = (run["setting_ticks"], section_year, window, direction)
                cell = cells.get(key)
                if cell is None:
                    cell = cells[key] = empty_cell()
                cell["runs"] += 1
                cell["left"] += int(run["left_censored"])
                cell["right"] += int(run["right_censored"])
                cell["sessions"].add(session)
                if run["length"] is None:
                    cell["unknown"] += 1
                else:
                    cell["lengths"].append(run["length"])
                    cell["exact_sessions"].add(session)


def collect_coverage(coverage: dict, bar: ObservedBar, setting: int, windows: list[dict[str, object]]) -> None:
    for window in window_ids(bar.start.isoformat(), windows):
        for year in (None, bar.session.year):
            key = (setting, year, window)
            cell = coverage.get(key)
            if cell is None:
                cell = coverage[key] = {"bars": 0, "sessions": set()}
            cell["bars"] += 1
            cell["sessions"].add(bar.session.isoformat())


def expected_tables(
    cells: dict, coverage: dict, settings: list[int], years: list[int], windows: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    """Recompute every cell from independent lists, never subgroup averages."""
    result = {"summary": [], "histogram": [], "survival": [], "coverage": []}
    for setting in settings:
        for year in (None, *years):
            for window in ("all_hours", *(str(row["id"]) for row in windows)):
                covered = coverage.get((setting, year, window), {"bars": 0, "sessions": set()})
                dates = sorted(covered["sessions"])
                coverage_fields = {
                    "eligible_bar_count": covered["bars"], "covered_sessions": len(dates),
                    "first_session_date": dates[0] if dates else None,
                    "last_session_date": dates[-1] if dates else None,
                }
                result["coverage"].append({"setting_ticks": setting, "year": year, "timeframe_id": window, **coverage_fields})
                for direction in ("bullish", "bearish", "all"):
                    cell = cells.get((setting, year, window, direction), empty_cell())
                    values = cell["lengths"]
                    denominator = len(values)
                    counts = Counter(values)
                    greatest_frequency = max(counts.values(), default=0)
                    modes = sorted(value for value, count in counts.items() if count == greatest_frequency)
                    base = {"setting_ticks": setting, "year": year, "timeframe_id": window, "direction": direction}
                    result["summary"].append({
                        **base,
                        "observed_trends": cell["runs"], "exact_trends": denominator,
                        "censored_trends": cell["unknown"], "left_censored_trends": cell["left"],
                        "right_censored_trends": cell["right"], "sessions_with_trends": len(cell["sessions"]),
                        "sessions_with_exact_trends": len(cell["exact_sessions"]), **coverage_fields,
                        "units": "candles", "mean_candles": sum(values) / denominator if denominator else None,
                        "median_candles": quantile(values, .5), "mode_candles": modes[0] if modes else None,
                        "tied_modes": "|".join(map(str, modes)), "q25_candles": quantile(values, .25),
                        "q75_candles": quantile(values, .75), "p90_candles": quantile(values, .9),
                        "p95_candles": quantile(values, .95), "max_candles": max(values) if values else None,
                    })
                    for label, lower, upper in HISTOGRAM:
                        count = sum(1 for value in values if value >= lower and (upper is None or value <= upper))
                        result["histogram"].append({
                            **base, "bin": label, "lower_candles": lower, "upper_candles": upper,
                            "numerator": count, "denominator": denominator,
                            "probability": count / denominator if denominator else None,
                        })
                    for threshold in TAIL_THRESHOLDS:
                        count = sum(1 for value in values if value >= threshold)
                        result["survival"].append({
                            **base, "minimum_candles": threshold, "numerator": count,
                            "denominator": denominator, "probability": count / denominator if denominator else None,
                        })
    return result


def audit_stage(
    stage: Path, ledger_dir: Path, publication_root: Path, settings_path: Path,
    lock_path: Path, excluded_session: date = date(2026, 9, 24),
) -> dict[str, object]:
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    windows = settings["reporting"]["timeframes"]
    entries = sorted((row for row in lock["files"] if row["role"] == "enhanced"), key=lambda row: row["setting_ticks"])
    if [row["setting_ticks"] for row in entries] != [4, 5, 6]:
        raise ValueError("audit requires exactly the three pinned ES 4/5/6 enhanced inputs")
    first_year = min(int(row["first_session_date_proxy"][:4]) for row in entries)
    last_year = max(int(row["last_session_date_proxy"][:4]) for row in entries)
    years = list(range(first_year, last_year + 1))
    cells, coverage, source_results, artifact_hashes = {}, {}, [], {}
    for entry in entries:
        setting = entry["setting_ticks"]
        source = publication_root / entry["path"]
        source_hash = digest(source)
        if source_hash != entry["sha256"] or source.stat().st_size != entry["bytes"]:
            raise ValueError(f"pinned source bytes changed for {setting} ticks")
        ledger_path = ledger_dir / f"trends_{setting}t.csv"
        try:
            ledger_relative = ledger_path.resolve().relative_to(stage.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError("ledger directory must be inside the audited stage for artifact receipts") from exc
        totals = {"input_rows": 0, "eligible_bars": 0, "eligible_doji_bars": 0, "eligible_same_second_bars": 0, "eligible_directional_bars": 0, "observed_run_candles": 0}

        def observed_source() -> Iterator[ObservedBar]:
            for bar in validate_completion(read_bars(source)):
                totals["input_rows"] += 1
                if bar.session != excluded_session and bar.status in COMPLETED:
                    collect_coverage(coverage, bar, setting, windows)
                    totals["eligible_bars"] += 1
                    totals["eligible_same_second_bars"] += int(bar.status == "next_bar_start_same_second")
                    totals["eligible_doji_bars" if bar.direction is None else "eligible_directional_bars"] += 1
                yield bar

        def observed_runs() -> Iterator[dict[str, object]]:
            for run in reconstruct_runs(observed_source(), setting, excluded_session):
                collect_run(cells, run, windows)
                totals["observed_run_candles"] += run["observed_length"]
                yield run

        trend_count = compare_csv(observed_runs(), ledger_path)
        if totals["input_rows"] != entry["rows"]:
            raise ValueError(f"source row inventory differs for {setting} ticks")
        if totals["observed_run_candles"] != totals["eligible_directional_bars"]:
            raise ValueError(f"directional-run candle conservation failed for {setting} ticks")
        ledger_hash = digest(ledger_path)
        artifact_hashes[ledger_relative] = ledger_hash
        source_results.append({
            "setting_ticks": setting, "input_path": entry["path"], "input_sha256": source_hash,
            "ledger_sha256": ledger_hash, "reconstructed_runs": trend_count, **totals,
        })

    expected = expected_tables(cells, coverage, [4, 5, 6], years, windows)
    table_results = {}
    for name in ("summary", "histogram", "survival"):
        table = stage / "tables" / f"trend_{name}.csv"
        count = compare_csv(expected[name], table)
        table_hash = digest(table)
        table_results[name] = {"rows": count, "sha256": table_hash}
        artifact_hashes[table.relative_to(stage).as_posix()] = table_hash
    coverage_path = stage / "tables" / "coverage.csv"
    count = compare_csv(expected["coverage"], coverage_path)
    coverage_hash = digest(coverage_path)
    table_results["coverage"] = {"rows": count, "sha256": coverage_hash}
    artifact_hashes[coverage_path.relative_to(stage).as_posix()] = coverage_hash
    input_audit_path = stage / "input-audit.json"
    saved_input_audits = json.loads(input_audit_path.read_text(encoding="utf-8"))
    if isinstance(saved_input_audits, dict):
        if saved_input_audits.get("study_id") != lock["study_id"] or saved_input_audits.get("run_id") != stage.name:
            raise ValueError("saved input-audit identity differs from the audited stage")
        input_audits = [{"setting_ticks": int(key), **value} for key, value in saved_input_audits["settings"].items()]
    else:
        input_audits = saved_input_audits
    if not isinstance(input_audits, list) or sorted(row["setting_ticks"] for row in input_audits) != [4, 5, 6]:
        raise ValueError("saved input audit requires exactly ES 4/5/6 records")
    for source_result in source_results:
        saved_audit = next(row for row in input_audits if row["setting_ticks"] == source_result["setting_ticks"])
        for saved_key, independent_key in (
            ("input_rows", "input_rows"), ("primary_eligible_bars", "eligible_bars"),
            ("doji_eligible_bars", "eligible_doji_bars"), ("same_second_eligible_bars", "eligible_same_second_bars"),
        ):
            if saved_audit.get(saved_key) != source_result[independent_key]:
                raise ValueError(f"saved input-audit {saved_key} differs for {source_result['setting_ticks']} ticks")
    artifact_hashes["input-audit.json"] = digest(input_audit_path)
    return {
        "audit_version": "1.0.0", "status": "pass", "result": "passed",
        "study_id": lock["study_id"], "run_id": stage.name,
        "verifier": {"path": "studies/22_es_range_xv_focused/audit.py", "sha256": digest(Path(__file__))},
        "settings_sha256": digest(settings_path), "inputs_lock_sha256": digest(lock_path),
        "excluded_session": excluded_session.isoformat(), "sources": source_results,
        "tables": table_results, "artifact_hashes": artifact_hashes,
        "verified_scope": [
            "pinned enhanced-input bytes, complete source-row order and adjacent completion metadata",
            "independent maximal directional-run reconstruction, doji handling and censor classification",
            "every saved ledger identity, observed/exact length and termination availability",
            "directional candle conservation across all observed runs",
            "all source-bar coverage cells, pooled/yearly independent first-open window grouping",
            "saved input-row, eligible-bar, eligible-doji and same-second counts",
            "all exact-run summary estimates, integer histogram/tail numerators and denominators",
        ],
        "limits": "Descriptive source reproduction does not verify ATAS construction, inferred timezone, contract/roll treatment, market completeness or predictive validity.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--ledger-dir", required=True, type=Path)
    parser.add_argument("--publication-root", required=True, type=Path)
    parser.add_argument("--settings", type=Path, default=Path(__file__).parent / "study.yaml")
    parser.add_argument("--inputs-lock", type=Path, default=Path(__file__).parent / "inputs.lock.json")
    parser.add_argument("--exclude-session", type=date.fromisoformat, default=date(2026, 9, 24))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = audit_stage(args.stage, args.ledger_dir, args.publication_root, args.settings, args.inputs_lock, args.exclude_session)
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
