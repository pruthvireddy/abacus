"""Stage-bound records for five explicitly owned numerical unittest selections.

This is a sealing policy around unittest_child's actual TestResult, not another
test runner. Retained declared bytes do not establish complete dependencies or
prove that the installed environment matched the retained lock.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys

from check_registry import RegistryError, validate_registry
from workspace_checks import (build_command, child_environment, interruption_handlers,
                              read_unittest_result, terminate_child)


CONTRACT = "abacus.numerical-test-record/v1"
RECORD_DIRECTORY = "numerical-tests"
STUDIES = {
    "08_countertrend_bar_continuation": ("study-08", ("src/engine.py", "summarize.py")),
    "09_range_xv_c2_confirmation": ("study-09", ("src/engine.py",)),
    "10_range_xv_session_overlay": ("study-10", ("src/stats.py",)),
    "12_gc_ema_band_excursions": ("study-12", ("src/engine.py",)),
    "13_gc_ema_band_filter_validation": (
        "study-13", ("src/engine.py", "pine/gc_band_mae_mfe_study_panel.pine")),
}
MECHANICS = (
    "scripts/numerical_test_record.py", "scripts/record-numerical-tests.py",
    "scripts/unittest_child.py", "scripts/workspace_checks.py",
    "scripts/check_registry.py", "scripts/uv",
)
RUNTIME_PROBE = """import json, os, platform, runpy, sys
from pathlib import Path
child, runtime, *arguments = sys.argv[1:]
sys.argv = [child, *arguments]
observations = {"executable": sys.executable, "version": sys.version,
                "implementation": platform.python_implementation(),
                "optimize": sys.flags.optimize, "argv": list(sys.argv),
                "cwd": os.getcwd()}
with Path(runtime).open("x", encoding="utf-8") as stream:
    stream.write(json.dumps(observations, sort_keys=True) + "\\n")
runpy.run_path(child, run_name="__main__")
"""


class NumericalRecordError(ValueError):
    """An absent, stale, malformed or nonpassing numerical gate."""


def _relative(value):
    if not isinstance(value, str) or not value or "\\" in value or "%" in value:
        raise NumericalRecordError("unsafe relative path")
    parts = value.split("/")
    if PurePosixPath(value).is_absolute() or any(part in ("", ".", "..") for part in parts):
        raise NumericalRecordError("unsafe relative path: " + value)
    return value


def check_path(path, *, kind=None, absent=False):
    """Reject redirected ancestors and broken links before reading or writing."""
    if ".." in Path(path).parts:
        raise NumericalRecordError("unsafe original path traversal: " + str(path))
    path = Path(os.path.abspath(path))
    for parent in reversed(path.parents):
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise NumericalRecordError("unsafe path ancestor: " + str(parent))
    if path.is_symlink():
        raise NumericalRecordError("symlink path: " + str(path))
    if absent:
        if os.path.lexists(path):
            raise NumericalRecordError("existing evidence must be preserved: " + str(path))
    elif kind == "file":
        try:
            mode = path.stat().st_mode
        except OSError as error:
            raise NumericalRecordError("missing required file: " + str(path)) from error
        if not stat.S_ISREG(mode):
            raise NumericalRecordError("expected ordinary file: " + str(path))
    elif kind == "directory" and not path.is_dir():
        raise NumericalRecordError("missing required directory: " + str(path))
    return path


def _stage(root, stage, study_id):
    if study_id not in STUDIES:
        raise NumericalRecordError("unsupported numerical study: " + str(study_id))
    root = check_path(root, kind="directory")
    stage = check_path(stage, kind="directory")
    parent = root / "work" / study_id
    if stage.parent != parent or not stage.name or stage.name in (".", ".."):
        raise NumericalRecordError("stage must be a direct new identity under work/" + study_id)
    return root, stage


def _loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise NumericalRecordError("duplicate JSON key: " + key)
            result[key] = value
        return result
    def constant(value):
        raise NumericalRecordError("nonfinite JSON value: " + value)
    def number(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise NumericalRecordError("nonfinite JSON value: " + value)
        return parsed
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=number)
    except (ValueError, UnicodeError) as error:
        raise NumericalRecordError("invalid numerical record JSON: " + str(error)) from error


def _read_json(path):
    return _loads(check_path(path, kind="file").read_text(encoding="utf-8"))


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _identity(path, relative):
    raw = check_path(path, kind="file").read_bytes()
    return {"path": _relative(relative), "bytes": len(raw), "sha256": _sha(raw)}


def _fields(record, names, label):
    if not isinstance(record, dict) or set(record) != set(names):
        raise NumericalRecordError("invalid fields in " + label)


def _pin(record, base):
    _fields(record, ("path", "bytes", "sha256"), "file identity")
    relative = _relative(record["path"])
    if type(record["bytes"]) is not int or record["bytes"] < 0:
        raise NumericalRecordError("invalid byte count")
    if not isinstance(record["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
        raise NumericalRecordError("invalid SHA-256")
    if _identity(base / relative, relative) != record:
        raise NumericalRecordError("changed retained bytes: " + relative)


def _check(root, study_id):
    check_id = STUDIES[study_id][0]
    registry = _read_json(root / "config/workspace-checks.json")
    _fields(registry, ("schema_version", "default_profile", "profiles", "owners", "checks"), "registry")
    if (type(registry["schema_version"]) is not int or registry["schema_version"] != 1
            or not isinstance(registry["checks"], list) or not isinstance(registry["owners"], dict)):
        raise NumericalRecordError("invalid owned-check registry")
    matches = [record for record in registry["checks"]
               if isinstance(record, dict) and record.get("id") == check_id]
    check = matches[0] if len(matches) == 1 else None
    selection = {"start_dir": "studies/" + study_id + "/tests", "pattern": "test*.py", "optimize": False}
    if (check is None or check.get("owner") != check_id or check.get("kind") != "unittest"
            or check.get("runtime") != "locked-python" or check.get("cwd") != "."
            or check.get("unittest") != selection or check.get("env") != {}):
        raise NumericalRecordError("owned registry selection changed; review recorder scope")
    # Reuse registry validation on the explicitly selected owner/check only.
    # Unrelated study prerequisites and entry points are outside this recorder.
    owner = registry["owners"].get(check_id)
    if not isinstance(owner, dict):
        raise NumericalRecordError("missing numerical check owner")
    owner = dict(owner, related_checks=[])
    fragment = {"schema_version": 1, "default_profile": "numerical",
                "profiles": {"numerical": {"description": "Selected owned numerical gate", "checks": [check_id]}},
                "owners": {check_id: owner}, "checks": [check]}
    try:
        validate_registry(root, fragment)
    except RegistryError as error:
        raise NumericalRecordError(str(error)) from error
    return check


def tested_source_paths(root, study_id):
    """Explicit exercised methods plus all Python files in the bounded test root."""
    owner = "studies/" + study_id + "/"
    directory = check_path(root / owner / "tests", kind="directory")
    paths = set(MECHANICS)
    paths.update(owner + name for name in STUDIES[study_id][1])
    # Test growth and sibling test helpers must invalidate an older receipt.
    for current, directories, files in os.walk(directory, followlinks=False):
        for name in directories:
            check_path(Path(current) / name, kind="directory")
        for name in files:
            if name.endswith(".py"):
                path = check_path(Path(current) / name, kind="file")
                paths.add(path.relative_to(root).as_posix())
    if study_id.startswith(("12_", "13_")):
        paths.add("packages/sahadeva/src/abacus_sahadeva/cooldown.py")
    return sorted(paths)


def _inventory(root, study_id):
    return [_identity(root / name, name) for name in tested_source_paths(root, study_id)]


def _argv(check, root, directory):
    command = build_command(check, root, result_path=directory / "child-result.json")
    index = command.index("-B")
    return command[:index + 1] + ["-c", RUNTIME_PROBE, command[index + 1],
                                str(directory / "runtime.json")] + command[index + 2:]


def _write_new(path, payload):
    check_path(path, absent=True)
    check_path(Path(str(path) + ".part"), absent=True)
    with Path(path).open("xb") as stream:
        stream.write(payload)


def _json_bytes(record):
    return (json.dumps(record, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _execute(argv, cwd, environment, log):
    with log.open("xb") as stream:
        process = subprocess.Popen(argv, cwd=str(cwd), env=environment,
                                   stdout=stream, stderr=subprocess.STDOUT, shell=False,
                                   start_new_session=(os.name == "posix"))
        try:
            with interruption_handlers():
                code = process.wait()
            return {"exit_code": code, "interrupted": False, "error": None}
        except KeyboardInterrupt:
            terminate_child(process)
            return {"exit_code": 130, "interrupted": True, "error": "interrupted"}
        except BaseException:
            terminate_child(process)
            raise


def record_numerical_tests(stage, root, study_id, *, executor=None):
    """Run the existing owned suite once; preserve failed/incomplete new evidence."""
    root, stage = _stage(root, stage, study_id)
    check = _check(root, study_id)
    directory = stage / RECORD_DIRECTORY
    check_path(directory, absent=True)
    check_path(stage / (RECORD_DIRECTORY + ".part"), absent=True)
    sources = _inventory(root, study_id)
    lock = _identity(root / "uv.lock", "uv.lock")
    # Source reads and declared-path checks precede the adoption/output directory.
    source_bytes = [(item, (root / item["path"]).read_bytes()) for item in sources]
    lock_bytes = (root / "uv.lock").read_bytes()
    directory.mkdir()
    retained = []
    for item, raw in source_bytes:
        path = "source-snapshot/" + item["path"]
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if _sha(raw) != item["sha256"] or len(raw) != item["bytes"]:
            raise NumericalRecordError("source changed before retention: " + item["path"])
        _write_new(target, raw)
        retained.append(_identity(target, path))
    if _sha(lock_bytes) != lock["sha256"] or len(lock_bytes) != lock["bytes"]:
        raise NumericalRecordError("environment lock changed before retention")
    _write_new(directory / "uv.lock", lock_bytes)
    command = _argv(check, root, directory)
    started = _now()
    environment = child_environment(check, root)
    environment.pop("PYTHONOPTIMIZE", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    execute = _execute if executor is None else executor
    outcome = {"exit_code": None, "interrupted": False, "error": None}
    try:
        outcome = execute(command, root, environment, directory / "log.txt")
    except OSError as error:
        outcome["error"] = str(error)
    completed = _now()
    after_error = None
    try:
        after = _inventory(root, study_id)
        lock_after = _identity(root / "uv.lock", "uv.lock")
    except (OSError, NumericalRecordError) as error:
        after, lock_after, after_error = [], None, str(error)
    child, runtime = None, None
    record_error = None
    try:
        # Reuse the existing machine-readable TestResult validation boundary.
        child = read_unittest_result(directory / "child-result.json")
        if _read_json(directory / "child-result.json") != child:
            raise NumericalRecordError("ambiguous child result")
        runtime = _read_json(directory / "runtime.json")
    except (OSError, ValueError, TypeError) as error:
        record_error = str(error)
    log = (_identity(directory / "log.txt", "log.txt")
           if (directory / "log.txt").is_file() else None)
    passed = (outcome.get("exit_code") == 0 and not outcome.get("interrupted")
              and not outcome.get("error") and not record_error and not after_error
              and sources == after and lock == lock_after)
    record = {
        "contract": CONTRACT, "study_id": study_id, "stage_id": stage.name,
        "stage_path": stage.relative_to(root).as_posix(), "check_id": check["id"],
        "selection": dict(check["unittest"]), "argv": command, "cwd": str(root),
        "environment_overrides": {**check["env"], "PYTHONDONTWRITEBYTECODE": "1"},
        "started_at": started, "completed_at": completed,
        "state": "completed" if passed else "failed",
        "process": outcome, "runtime": runtime, "log": log,
        "lock_before": lock, "lock_after": lock_after,
        "retained_lock": _identity(directory / "uv.lock", "uv.lock"),
        "source_scope": "Declared numerical methods, selected test directory Python files, and executed recorder mechanics; incomplete dependency closure.",
        "sources_before": sources, "sources_after": after, "retained_sources": retained,
        "child_result": child,
        "child_result_file": (_identity(directory / "child-result.json", "child-result.json")
                              if child is not None else None),
        "runtime_file": (_identity(directory / "runtime.json", "runtime.json")
                         if runtime is not None else None),
        "diagnostics": [value for value in (outcome.get("error"), after_error, record_error) if value],
    }
    # Strict sealing eligibility also rejects mixed skips and expected failures.
    try:
        _require_pass(record)
    except NumericalRecordError as error:
        record["state"] = "failed"
        record["diagnostics"].append(str(error))
    _write_new(directory / "record.json", _json_bytes(record))
    return record


def _require_pass(record):
    process = record.get("process")
    _fields(process, ("exit_code", "interrupted", "error"), "process outcome")
    if (type(process["exit_code"]) is not int or process["exit_code"] != 0
            or process["interrupted"] is not False or process["error"] is not None
            or record.get("state") != "completed" or record.get("diagnostics") != []):
        raise NumericalRecordError("numerical execution did not complete successfully")
    runtime = record.get("runtime")
    _fields(runtime, ("executable", "version", "implementation", "optimize", "argv", "cwd"), "runtime")
    if (type(runtime["optimize"]) is not int or runtime["optimize"] != 0
            or any(not isinstance(runtime[name], str) or not runtime[name]
                   for name in ("executable", "version", "implementation", "cwd"))
            or not isinstance(runtime["argv"], list)
            or any(not isinstance(item, str) for item in runtime["argv"])):
        raise NumericalRecordError("ordinary numerical runtime observations are required")
    child = record.get("child_result")
    _fields(child, ("schema_version", "outcome", "successful_callbacks", "counts", "skips"), "child result")
    fields = ("discovered", "tests_run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes")
    counts = child["counts"]
    _fields(counts, fields, "TestResult counts")
    if (type(child["schema_version"]) is not int or child["schema_version"] != 1
            or child["outcome"] != "passed"
            or any(type(counts[name]) is not int or counts[name] < 0 for name in fields)
            or type(child["successful_callbacks"]) is not int or child["successful_callbacks"] <= 0
            or counts["discovered"] <= 0 or counts["tests_run"] <= 0
            or counts["tests_run"] != counts["discovered"]
            or child["successful_callbacks"] < counts["tests_run"]
            or any(counts[name] for name in fields[2:]) or child["skips"] != []):
        raise NumericalRecordError("numerical suite requires nonempty ordinary execution without failures, skips or expected failures")


def require_numerical_record(stage, root, study_id):
    """Read-only strict gate, including stage binding and current declared bytes."""
    root, stage = _stage(root, stage, study_id)
    check = _check(root, study_id)
    directory = check_path(stage / RECORD_DIRECTORY, kind="directory")
    check_path(stage / (RECORD_DIRECTORY + ".part"), absent=True)
    record = _read_json(directory / "record.json")
    required = ("contract", "study_id", "stage_id", "stage_path", "check_id", "selection",
                "argv", "cwd", "environment_overrides", "started_at", "completed_at", "state",
                "process", "runtime", "log", "lock_before", "lock_after", "retained_lock",
                "source_scope", "sources_before", "sources_after", "retained_sources",
                "child_result", "child_result_file", "runtime_file", "diagnostics")
    _fields(record, required, "numerical envelope")
    if (record["contract"] != CONTRACT or record["study_id"] != study_id
            or record["stage_id"] != stage.name or record["stage_path"] != stage.relative_to(root).as_posix()
            or record["check_id"] != check["id"] or record["selection"] != check["unittest"]
            or record["argv"] != _argv(check, root, directory) or record["cwd"] != str(root)
            or record["environment_overrides"] != {**check["env"], "PYTHONDONTWRITEBYTECODE": "1"}):
        raise NumericalRecordError("wrong study, stage, suite, selection or actual command binding")
    for name in ("started_at", "completed_at"):
        try:
            value = datetime.fromisoformat(record[name])
        except (TypeError, ValueError) as error:
            raise NumericalRecordError("invalid execution timestamp") from error
        if value.tzinfo is None or value.utcoffset() is None:
            raise NumericalRecordError("execution timestamp must carry UTC offset")
    if datetime.fromisoformat(record["completed_at"]) < datetime.fromisoformat(record["started_at"]):
        raise NumericalRecordError("completion precedes execution")
    _require_pass(record)
    # The runtime wrapper records unittest_child's actual argv, not its probe argv.
    command = record["argv"]
    probe = command.index("-c")
    expected = [command[probe + 2]] + command[probe + 4:]
    if record["runtime"]["cwd"] != str(root) or record["runtime"]["argv"] != expected:
        raise NumericalRecordError("runtime command differs from retained actual argv")
    if not isinstance(record["source_scope"], str) or not record["source_scope"].strip():
        raise NumericalRecordError("declared tested-source scope is missing")
    current = _inventory(root, study_id)
    if not isinstance(record["selection"], dict) or type(record["selection"].get("optimize")) is not bool:
        raise NumericalRecordError("invalid discovery selection types")
    for name in ("sources_before", "sources_after"):
        if not isinstance(record[name], list):
            raise NumericalRecordError("invalid tested-source inventory")
        for item in record[name]:
            _pin(item, root)
    if record["sources_before"] != current or record["sources_after"] != current:
        raise NumericalRecordError("tested-source inventory changed before, during or after execution")
    expected_retained = [dict(item, path="source-snapshot/" + item["path"]) for item in current]
    if record["retained_sources"] != expected_retained:
        raise NumericalRecordError("retained source inventory differs from executed scope")
    for item in record["retained_sources"]:
        _pin(item, directory)
    lock = _identity(root / "uv.lock", "uv.lock")
    for name in ("lock_before", "lock_after"):
        _pin(record[name], root)
    _pin(record["retained_lock"], directory)
    if any(record[name] != lock for name in ("lock_before", "lock_after", "retained_lock")):
        raise NumericalRecordError("environment lock changed")
    for name in ("retained_lock", "log", "child_result_file", "runtime_file"):
        _pin(record[name], directory)
    if record["log"]["path"] != "log.txt" or record["child_result_file"]["path"] != "child-result.json" or record["runtime_file"]["path"] != "runtime.json":
        raise NumericalRecordError("unexpected retained record/log path")
    if _read_json(directory / "child-result.json") != record["child_result"] or _read_json(directory / "runtime.json") != record["runtime"]:
        raise NumericalRecordError("embedded observations differ from retained records")
    for name in ("record.json", "log.txt", "child-result.json", "runtime.json", "uv.lock"):
        check_path(directory / (name + ".part"), absent=True)
    return record


def require_test_evidence(stage, root, study_id, *, legacy_test_log=False):
    """08/09/10's explicit historical boundary; never fall back from adoption."""
    root, stage = _stage(root, stage, study_id)
    adopted = any(os.path.lexists(stage / name) for name in (RECORD_DIRECTORY, RECORD_DIRECTORY + ".part"))
    if legacy_test_log:
        if study_id not in tuple(STUDIES)[:3]:
            raise NumericalRecordError("legacy test logs are limited to studies 08/09/10")
        if adopted:
            raise NumericalRecordError("legacy mode cannot bypass an adopted numerical-record workflow")
        log = check_path(stage / "focused-tests.log", kind="file")
        check_path(stage / "focused-tests.log.part", absent=True)
        expected = 6 if study_id.startswith("10_") else 8
        text = log.read_text(encoding="utf-8")
        if "Ran " + str(expected) + " tests" not in text or "OK" not in text:
            raise NumericalRecordError("legacy focused test log is missing or failed")
        return {"mode": "legacy/log-only", "source_binding": "unbound", "log": "focused-tests.log",
                "legacy_literal_count": expected, "sha256": _sha(log.read_bytes())}
    record = require_numerical_record(stage, root, study_id)
    return {"mode": "structured", "contract": CONTRACT, "record": RECORD_DIRECTORY + "/record.json",
            "sha256": _sha((stage / RECORD_DIRECTORY / "record.json").read_bytes()),
            "log": RECORD_DIRECTORY + "/log.txt", "counts": record["child_result"]["counts"],
            "command": {"argv": record["argv"], "cwd": record["cwd"]}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, choices=tuple(STUDIES))
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--check", action="store_true", help="Read-only validation of the explicit stage record")
    options = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        if options.check:
            record = require_numerical_record(options.stage, root, options.study)
        else:
            record = record_numerical_tests(options.stage, root, options.study)
        print(json.dumps({"study_id": options.study, "stage_id": record["stage_id"],
                          "state": record["state"], "record": RECORD_DIRECTORY + "/record.json"}))
        return 0 if record["state"] == "completed" else 1
    except (OSError, NumericalRecordError) as error:
        print("Numerical test evidence refused: " + str(error), file=sys.stderr)
        return 1

