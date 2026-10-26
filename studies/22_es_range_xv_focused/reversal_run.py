"""Execute, render and seal the frozen ES Range XV reversal continuation and retracement study."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, fields
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

STUDY_DIRECTORY = Path(__file__).resolve().parent
WORKSPACE = STUDY_DIRECTORY.parents[1]
STUDY_ID = "22_es_range_xv_focused"
SETTINGS = (4, 5, 6)
TABLE_ROWS = {"reversal_summary.csv": 9720, "reversal_continuation.csv": 194400,
              "reversal_retracement.csv": 38880, "coverage.csv": 216}
SOURCE_FILES = ("reversal_run.py", "reversal_audit.py", "src/timeframes.py", "src/trends.py", "src/analysis.py", "src/reversals.py", "src/reversal_analysis.py", "src/reversal_reporting.py")
SUPPORTED_DEFINITION = {'selection': 'completed non-doji R directly follows a completed opposite non-doji candle, contiguous '
              'original source rows within the same eligible inferred session',
 'available_at': 'R.bar_completion_timestamp_proxy',
 'minimum_prior_candles': 1,
 'prior_start_unknown': 'retain event and flag prior run start unknown',
 'horizons': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
 'n_excludes_reversal': True,
 'continuation': 'n uninterrupted additional completed candles with the same close-open sign as R',
 'opposite_or_doji': 'observed failure for every larger horizon',
 'barrier': 'unknown above observed followers; retain already-known successes',
 'window_boundary': 'full follow-up within same inferred session; never truncate at named windows',
 'retracement_horizon': 'F1 only, immediate next original candle, completed eligible and same inferred '
                        'session',
 'body_retracement_percent': [25, 50, 75, 100],
 'touch': 'inclusive F1 low/high reaches R.close toward R.open by the selected fraction of exact R body',
 'favorable_primary': 'strict F1.close beyond R.close in R direction',
 'favorable_secondary': 'F1 close-open sign equals R direction, saved separately',
 'joint_denominator': 'all reversals with known eligible completed F1',
 'conditional_denominator': 'known F1 candles touching the selected retracement level',
 'unknown': 'blank estimates; never count unknown as failure',
 'uncertainty': 'empirical descriptive rates only; no iid confidence intervals, no population forecast, no '
                'profitability claim',
 'prior_leg_buckets': ['all',
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
 'prior_leg_membership': 'exact known-start length before R; otherwise unknown_start; all overlaps disjoint '
                         'buckets'}
SUPPORTED_REPORTING = {'timezone': 'America/New_York',
 'year_basis': 'session_date_proxy',
 'session_rollover': '18:00',
 'event_membership_timestamp': 'reversal_completion_timestamp_proxy',
 'timeframes': [{'id': 'asia', 'label': 'Asia', 'group': 'sessions', 'start': '20:00', 'end': '02:00'},
                {'id': 'london', 'label': 'London', 'group': 'sessions', 'start': '02:00', 'end': '09:00'},
                {'id': 'ny', 'label': 'NY', 'group': 'sessions', 'start': '09:30', 'end': '16:00'},
                {'id': 'asia_open',
                 'label': 'Asia Open',
                 'group': 'subwindows',
                 'start': '19:30',
                 'end': '21:30'},
                {'id': 'ny_open',
                 'label': 'NY Open',
                 'group': 'subwindows',
                 'start': '09:30',
                 'end': '10:30'},
                {'id': 'ny_am', 'label': 'NY AM', 'group': 'subwindows', 'start': '10:30', 'end': '12:30'},
                {'id': 'ny_pm', 'label': 'NY PM', 'group': 'subwindows', 'start': '12:30', 'end': '16:00'}]}
sys.path.insert(0, str(STUDY_DIRECTORY / "src"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def regular(path: Path) -> Path:
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise ValueError(f"Symlinked evidence/input path refused: {path}")
    if not path.is_file():
        raise ValueError(f"Regular file required: {path}")
    return path


def located(root: Path, name: str) -> Path:
    if not isinstance(name, str):
        raise ValueError("Unsafe evidence/input locator")
    part = PurePosixPath(name)
    if not isinstance(name, str) or not name or part.is_absolute() or any(piece in (".", "..") for piece in name.split("/")) or "\\" in name:
        raise ValueError("Unsafe evidence/input locator")
    return regular(root / part)


def record(path: Path, root: Path, *, rows: int | None = None) -> dict:
    regular(path)
    result = {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)}
    if rows is not None:
        result["rows"] = rows
    return result


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def read_json(path: Path) -> dict:
    value = json.loads(regular(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def stage_path(path: Path, *, existing: bool) -> Path:
    candidate = path.expanduser().absolute()
    expected_parent = WORKSPACE / "work" / STUDY_ID
    if candidate.parent != expected_parent or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,159}", candidate.name):
        raise ValueError("Stage must be a direct unique child of work/22_es_range_xv_focused")
    for ancestor in (candidate, *candidate.parents):
        if ancestor.is_symlink():
            raise ValueError("Symlinked stage path refused")
    if existing:
        if not candidate.is_dir():
            raise ValueError("Existing study stage required")
    elif os.path.lexists(candidate):
        raise ValueError("Stage overwrite refused; choose a new run ID")
    return candidate


def command_record(argv: list[str] | None = None) -> dict:
    return {"argv": [sys.executable, *sys.argv] if argv is None else argv,
            "cwd": str(Path.cwd()), "python": {"executable": sys.executable,
            "version": sys.version, "implementation": sys.implementation.name,
            "optimize": sys.flags.optimize}, "recorded_at": now()}


def git_identity() -> dict:
    def git(*arguments):
        return subprocess.run(["git", *arguments], cwd=WORKSPACE, check=True,
                              capture_output=True, text=True).stdout.strip()
    return {"revision": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain")),
            "dirty_snapshot_scope": "Exact declared execution-source bytes and frozen protocol; not a whole-repository dependency closure."}


def freeze(stage: Path, publication_root: Path, argv: list[str] | None = None) -> None:
    inventory = []
    for name in SOURCE_FILES:
        source = regular(STUDY_DIRECTORY / name)
        relative = source.relative_to(WORKSPACE).as_posix()
        destination = stage / "provenance/source-snapshot" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(source.read_bytes())
        item = record(source, WORKSPACE)
        item["snapshot_path"] = destination.relative_to(stage).as_posix()
        if digest(destination) != item["sha256"]:
            raise ValueError("Source changed while retaining execution bytes")
        inventory.append(item)
    frozen = []
    for original, destination in ((STUDY_DIRECTORY / "reversal.yaml", "study.yaml"),
                                  (STUDY_DIRECTORY / "reversal-plan.md", "plan.md"),
                                  (STUDY_DIRECTORY / "notes.md", "notes.md"),
                                  (STUDY_DIRECTORY / "inputs.lock.json", "inputs.lock.json"),
                                  (WORKSPACE / "uv.lock", "uv.lock")):
        source = regular(original)
        with (stage / destination).open("xb") as stream:
            stream.write(source.read_bytes())
        frozen.append({**record(source, WORKSPACE), "snapshot_path": destination})
    shutil.copyfile(stage / "study.yaml", stage / "config.json")
    shutil.copyfile(stage / "plan.md", stage / "protocol.md")
    write_json(stage / "provenance/execution-start.json", {
        "schema_version": 1, "study_id": STUDY_ID, "run_id": stage.name,
        "started_at": now(), "command": command_record(argv), "git": git_identity(),
        "publication_root": str(publication_root), "execution_sources": inventory,
        "frozen_inputs": frozen, "environment_lock": record(stage / "uv.lock", stage),
        "source_scope": "Declared study execution modules only; independent verification has its own receipt."})
    assert_frozen(stage)


def assert_frozen(stage: Path) -> dict:
    receipt = read_json(stage / "provenance/execution-start.json")
    if receipt.get("study_id") != STUDY_ID or receipt.get("run_id") != stage.name:
        raise ValueError("Execution receipt belongs to another study/stage")
    expected = {f"studies/{STUDY_ID}/{name}" for name in SOURCE_FILES}
    if {item["path"] for item in receipt["execution_sources"]} != expected:
        raise ValueError("Execution source inventory is incomplete")
    for item in (*receipt["execution_sources"], *receipt["frozen_inputs"]):
        source = located(WORKSPACE, item["path"])
        retained = located(stage, item["snapshot_path"])
        if digest(source) != item["sha256"] or source.stat().st_size != item["bytes"] or digest(retained) != item["sha256"]:
            raise ValueError(f"Frozen execution/protocol source changed: {item['path']}")
    if digest(stage / "config.json") != digest(stage / "study.yaml") or digest(stage / "protocol.md") != digest(stage / "plan.md"):
        raise ValueError("Frozen config/protocol aliases changed")
    return receipt


def verify_inputs(stage: Path, publication_root: Path) -> dict:
    lock = read_json(stage / "inputs.lock.json")
    files = lock.get("files", [])
    if len(files) != 6 or {(item.get("role"), item.get("setting_ticks")) for item in files} != {(role, setting) for role in ("source", "enhanced") for setting in SETTINGS}:
        raise ValueError("Exactly six pinned source/enhanced ES inputs are required")
    entries = []
    for item in (*lock.get("manifests", []), *files, lock["clock_migration"]):
        root = WORKSPACE if item["root_alias"] == "workspace_root" else publication_root
        if item["root_alias"] not in ("workspace_root", "publication_root"):
            raise ValueError("Unsupported input root alias")
        path = located(root, item["path"])
        actual = record(path, root)
        if actual["sha256"] != item["sha256"] or ("bytes" in item and actual["bytes"] != item["bytes"]):
            raise ValueError(f"Pinned input bytes changed: {item['path']}")
        entries.append({**actual, "root_alias": item["root_alias"], "role": item.get("role", "clock_migration")})
    if len(lock.get("manifests", [])) != 1:
        raise ValueError("Exactly one pinned export manifest is required")
    result = {"result": "passed", "checked_at": now(), "files": entries,
              "market_statistics_recomputed": False, "all_six_input_files_verified": True}
    write_json(stage / "input-verification.json", result)
    return lock


def csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_table(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Empty table refused")
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(value) for key, value in row.items()})


def execute(stage: Path, publication_root: Path, argv: list[str] | None = None) -> dict:
    if sys.flags.optimize:
        raise ValueError("Ordinary Python execution is required")
    stage = stage_path(stage, existing=False)
    stage.mkdir(parents=True, exist_ok=False)
    freeze(stage, publication_root, argv)
    lock = verify_inputs(stage, publication_root)
    from timeframes import load_timeframes
    from trends import load_bars
    from reversals import extract_reversals, ledger_row, LEDGER_COLUMNS
    from analysis import Coverage
    from reversal_analysis import analyze_reversals
    frames = load_timeframes(stage / "study.yaml")
    settings = read_json(stage / "study.yaml")
    if tuple(settings["scope"]["selected_analysis_settings_ticks"]) != SETTINGS or len(frames) != 7:
        raise ValueError("Frozen reversal-analysis scope must select 4/5/6 and seven windows")
    definition = settings["reversal_definition"]
    if definition != SUPPORTED_DEFINITION or any(settings["reporting"].get(k) != v for k, v in SUPPORTED_REPORTING.items()):
        raise ValueError("Unsupported reversal protocol or reporting declaration")
    if definition["horizons"] != list(range(1, 21)) or definition["body_retracement_percent"] != [25, 50, 75, 100] or definition["favorable_primary"] != "strict F1.close beyond R.close in R direction":
        raise ValueError("Unsupported reversal metric declaration")
    if definition["prior_leg_buckets"] != ["all", *[str(n) for n in range(1, 11)], "11-15", "16-20", "21+", "unknown_start"] or definition["prior_leg_membership"] != "exact known-start length before R; otherwise unknown_start; all overlaps disjoint buckets":
        raise ValueError("Unsupported preceding-leg cohort declaration")
    coverage = Coverage(frames)
    tables = {name: [] for name in TABLE_ROWS}
    audits, artifacts = {}, []
    (stage / "evidence").mkdir()
    (stage / "tables").mkdir()
    for setting in SETTINGS:
        selected = next(item for item in lock["files"] if item["role"] == "enhanced" and item["setting_ticks"] == setting)
        audit = {}
        ledger = stage / "evidence" / f"reversals_{setting}t.csv"
        ledger_rows = 0
        with ledger.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
            writer.writeheader()
            def observed_bars():
                for bar in load_bars(publication_root / selected["path"], setting,
                                     settings["data"]["excluded_session_dates"], audit=audit):
                    coverage.observe(bar)
                    yield bar
            def saved_reversals():
                nonlocal ledger_rows
                for event in extract_reversals(observed_bars(), setting):
                    writer.writerow(ledger_row(event))
                    ledger_rows += 1
                    yield event
            result = analyze_reversals(saved_reversals(), [setting], frames, coverage)
        if audit["input_rows"] != selected["rows"]:
            raise ValueError("Input row count differs from pinned inventory")
        tables["reversal_summary.csv"].extend(result.summaries)
        tables["reversal_continuation.csv"].extend(result.continuation)
        tables["reversal_retracement.csv"].extend(result.retracement)
        artifacts.append(record(ledger, stage, rows=ledger_rows))
        audits[str(setting)] = audit
        print(json.dumps({"setting_ticks": setting, "input_rows": audit["input_rows"], "observed_reversals": ledger_rows}), flush=True)
    tables["coverage.csv"] = coverage.rows(SETTINGS)
    for name, rows in tables.items():
        if len(rows) != TABLE_ROWS[name]:
            raise ValueError(f"Unexpected complete table row count for {name}")
        path = stage / "tables" / name
        write_table(path, rows)
        artifacts.append(record(path, stage, rows=len(rows)))
    write_json(stage / "input-audit.json", {"schema_version": 1, "study_id": STUDY_ID, "run_id": stage.name, "settings": audits})
    artifacts.append(record(stage / "input-audit.json", stage))
    assert_frozen(stage)
    result = {"result": "passed", "study_id": STUDY_ID, "run_id": stage.name, "completed_at": now(),
              "artifacts": artifacts, "artifact_hashes": {item["path"]: item["sha256"] for item in artifacts},
              "independent_verification_performed": False}
    write_json(stage / "provenance/execution-complete.json", result)
    return result


def verify_artifacts(stage: Path) -> dict:
    assert_frozen(stage)
    receipt = read_json(stage / "provenance/execution-complete.json")
    if receipt.get("result") != "passed" or receipt.get("run_id") != stage.name or receipt.get("study_id") != STUDY_ID:
        raise ValueError("Successful stage-bound execution required")
    expected = {f"tables/{name}" for name in TABLE_ROWS} | {f"evidence/reversals_{setting}t.csv" for setting in SETTINGS} | {"input-audit.json"}
    if {item["path"] for item in receipt["artifacts"]} != expected or len(receipt["artifacts"]) != len(expected):
        raise ValueError("Execution artifact inventory is incomplete")
    for item in receipt["artifacts"]:
        path = located(stage, item["path"])
        if digest(path) != item["sha256"] or path.stat().st_size != item["bytes"] or receipt["artifact_hashes"].get(item["path"]) != item["sha256"]:
            raise ValueError(f"Executed artifact changed: {item['path']}")
    return receipt


def render(stage: Path) -> dict:
    stage = stage_path(stage, existing=True)
    verify_artifacts(stage)
    from reversal_reporting import build_reports
    result = build_reports(stage)
    verify_artifacts(stage)
    return result


def require_receipt(stage: Path, name: str, required: set[str]) -> dict:
    receipt = read_json(stage / name)
    hashes = receipt.get("artifact_hashes")
    if receipt.get("result") != "passed" or not isinstance(hashes, dict) or not hashes or not required.issubset(hashes):
        raise ValueError(f"Passed artifact-bound receipt required: {name}")
    for name, expected in hashes.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected) or digest(located(stage, name)) != expected:
            raise ValueError("Verification receipt consumed bytes have changed")
    return receipt


def require_numerical_result(stage: Path) -> dict:
    child = read_json(stage / "verification/numerical-test-result.json")
    counts = child.get("counts", {})
    keys = ("discovered", "tests_run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes")
    if type(child.get("schema_version")) is not int or child["schema_version"] != 1 or child.get("outcome") != "passed" or child.get("skips") != [] or any(type(counts.get(key)) is not int or counts[key] < 0 for key in keys):
        raise ValueError("Actual successful numerical TestResult required")
    if counts["tests_run"] <= 0 or counts["tests_run"] != counts["discovered"] or any(counts[key] for key in keys[2:]) or type(child.get("successful_callbacks")) is not int or child["successful_callbacks"] < counts["tests_run"]:
        raise ValueError("Numerical tests must execute with positive counts and no failures/skips")
    return child


def seal(stage: Path, publication_root: Path, argv: list[str] | None = None) -> Path:
    stage = stage_path(stage, existing=True)
    if sys.flags.optimize:
        raise ValueError("Ordinary Python sealing is required")
    executed = verify_artifacts(stage)
    tables = {f"tables/{name}" for name in TABLE_ROWS}
    ledgers = {f"evidence/reversals_{setting}t.csv" for setting in SETTINGS}
    independent = require_receipt(stage, "verification.json", tables | ledgers)
    publications = sorted(path.relative_to(stage).as_posix() for path in stage.glob("publications/*/publication.json"))
    if len(publications) != 6:
        raise ValueError("Six pre-seal chart/analysis publication sources required")
    for relative in publications:
        report = read_json(stage / relative)
        if report.get("source", {}).get("runId") != stage.name:
            raise ValueError("Publication source-run attribution mismatch")
    publication = require_receipt(stage, "publication-verification.json", set(publications) | tables)
    preseal = require_receipt(stage, "preseal-checks.json", {"verification.json", "publication-verification.json", "verification/numerical-test-result.json"})
    child = require_numerical_result(stage)
    destination = WORKSPACE / "runs" / STUDY_ID / stage.name
    retained = publication_root / "data/research/sahadeva" / STUDY_ID / stage.name
    for path in (destination, retained):
        if os.path.lexists(path):
            raise ValueError("Completed run or retained-ledger overwrite refused")
        for ancestor in path.parents:
            if ancestor.is_symlink():
                raise ValueError("Symlinked seal destination refused")
    if publication_root != Path(assert_frozen(stage)["publication_root"]):
        raise ValueError("Sealing publication root differs from execution")
    # All gates and destination checks finish before retained evidence moves.
    write_json(stage / "provenance/sealing.json", {"command": command_record(argv),
        "sealer": record(regular(Path(__file__).resolve()), WORKSPACE),
        "destination": destination.relative_to(WORKSPACE).as_posix(), "recorded_at": now()})
    retained.mkdir(parents=True, exist_ok=False)
    events = []
    for item in executed["artifacts"]:
        if item["path"] not in ledgers:
            continue
        source = stage / item["path"]
        target = retained / source.name
        shutil.move(str(source), str(target))
        events.append({**record(target, publication_root, rows=item["rows"]),
            "original_stage_path": item["path"], "root_alias": "publication_root",
            "role": "ordered_reversal_event_ledger", "retention_status": "retained_local_external_research_evidence_backup_not_certified"})
    write_json(stage / "events.manifest.json", {"schema_version": 1, "study_id": STUDY_ID, "run_id": stage.name,
        "files": events, "publication_root": str(publication_root), "ledgers_removed_from_run_git_payload": True})
    artifacts = [record(path, stage) for path in sorted(stage.rglob("*")) if path.is_file()]
    write_json(stage / "manifest.json", {"schema_version": 1, "study_id": STUDY_ID, "run_id": stage.name,
        "sealed_at": now(), "execution": read_json(stage / "provenance/execution-start.json"),
        "input_verification": read_json(stage / "input-verification.json"), "artifacts": artifacts,
        "checks": {"independent": independent["result"], "publication": publication["result"], "preseal": preseal["result"], "numerical_counts": child["counts"]},
        "events_manifest": "events.manifest.json", "limitations": ["Descriptive reversal continuation and F1 retracement rates; no trading profitability claim.", "Continuation uses horizon-specific known outcomes and explicitly retains unknowns; F1 joint and conditional rates have different denominators; no generic evidence-contract adoption."]})
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(stage), str(destination))
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("describe", "execute", "render", "seal"))
    parser.add_argument("--out", type=Path, help="Explicit unique work-stage directory")
    parser.add_argument("--publication-root", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "describe":
            from timeframes import load_timeframes
            settings = read_json(STUDY_DIRECTORY / "reversal.yaml")
            lock = read_json(STUDY_DIRECTORY / "inputs.lock.json")
            print(json.dumps({"study_id": STUDY_ID, "status": settings["status"], "protocol_version": settings["protocol_version"], "scope": settings["scope"], "reporting": settings["reporting"], "timeframe_count": len(load_timeframes(STUDY_DIRECTORY / "reversal.yaml")), "dataset_id": lock["dataset_id"], "input_byte_verification": "not_performed_by_describe"}, indent=2))
            return 0
        if args.out is None:
            raise ValueError("--out is required for execution/rendering/sealing")
        command = [sys.executable, str(Path(__file__).resolve()), *(sys.argv[1:] if argv is None else argv)]
        if args.command == "render":
            result = render(args.out)
        else:
            from abacus_bhishma.paths import resolve_publication_root
            root = resolve_publication_root(args.publication_root, workspace=WORKSPACE)
            result = execute(args.out, root, command) if args.command == "execute" else {"sealed_run": str(seal(args.out, root, command))}
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Study 22 lifecycle refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
