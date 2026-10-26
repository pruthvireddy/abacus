#!/usr/bin/env python3
"""Explicit workspace checks; planning uses only the standard library."""
from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

SUMMARY_VERSION = 1
ROOT = Path(__file__).resolve().parents[1]


def registry_api():
    """Load our sibling, without depending on caller cwd or writing bytecode."""
    directory = str(Path(__file__).resolve().parent)
    prior = sys.dont_write_bytecode
    sys.path.insert(0, directory)
    sys.dont_write_bytecode = True
    try:
        return importlib.import_module("check_registry")
    finally:
        sys.dont_write_bytecode = prior
        sys.path.remove(directory)


def expand(value, root, preview_origin=None):
    substitutions = {"{root}": str(root), "{python}": sys.executable,
                     "{preview_origin}": preview_origin or "{preview_origin}"}
    for token, replacement in substitutions.items():
        value = value.replace(token, replacement)
    return value


def child_environment(check, root, environ=None):
    """Each child gets its own environment copy, including local legacy overrides."""
    environment = dict(os.environ if environ is None else environ)
    environment.update({key: value.replace("{root}", str(root))
                        for key, value in check.get("env", {}).items()})
    return environment


def build_command(check, root, *, result_path="<temporary-result>", preview_origin=None):
    if check["kind"] == "command":
        return [expand(argument, root, preview_origin) for argument in check["argv"]]
    selection = dict(check["unittest"], start_dir=str(root / check["unittest"]["start_dir"]))
    if check["runtime"] == "standard-library":
        arguments = [sys.executable]
    else:
        arguments = [str(root / "scripts/uv"), "run", "--locked", "--no-sync", "python"]
    if selection.get("optimize", False):
        arguments.append("-O")
    arguments.extend(["-B", str(root / "scripts/unittest_child.py"),
                      "--spec", json.dumps(selection, sort_keys=True),
                      "--result", str(result_path)])
    return arguments


def valid_preview_origin(value):
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (ValueError, TypeError):
        return False
    return (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")
            and parsed.username is None and parsed.password is None
            and parsed.path == "" and not parsed.query and not parsed.fragment
            and port is not None and 1 <= port <= 65535
            and value == "http://" + parsed.netloc)


def prerequisites_for_check(check, root):
    prerequisites = list(check.get("prerequisites", []))
    locked = (check["kind"] == "unittest" and check["runtime"] == "locked-python") or (
        check["kind"] == "command" and expand(check["argv"][0], root) == str(root / "scripts/uv")
        and "--locked" in check["argv"])
    if locked:
        if not any(item["kind"] == "executable" and item["name"] == "uv" for item in prerequisites):
            prerequisites.append({"kind": "executable", "name": "uv", "description": "Prepared UV executable"})
        prerequisites.append({"kind": "file", "path": ".venv/bin/python",
                              "description": "Prepared locked Python interpreter (.venv/bin/python)"})
    return prerequisites


def missing_prerequisites(check, root, *, environ=None, preview_origin=None,
                          which=shutil.which, probe=subprocess.run):
    """Preflight only declared tools/paths; never inspect private path settings."""
    environment = child_environment(check, root, environ)
    missing = []
    prerequisites = prerequisites_for_check(check, root)
    for prerequisite in prerequisites:
        kind = prerequisite["kind"]
        description = prerequisite.get("description")
        if kind == "note":
            continue
        if kind in ("file", "directory"):
            path = root / prerequisite["path"]
            available = path.is_file() if kind == "file" else path.is_dir()
            if not available:
                missing.append(description or "Missing {}: {}".format(kind, prerequisite["path"]))
        elif kind == "executable":
            name = prerequisite["name"]
            available = which(name, path=environment.get("PATH"))
            if name == "uv":
                local = root / ".tools/uv/bin/uv"
                available = available or (local.is_file() and os.access(str(local), os.X_OK))
            if not available:
                missing.append(description or "Missing executable on child PATH: " + name)
        elif kind == "node-major":
            if not which("node", path=environment.get("PATH")):
                missing.append("Node {} is required; node is unavailable".format(prerequisite["major"]))
                continue
            try:
                version = probe(["node", "--version"], cwd=str(root / check["cwd"]),
                                env=environment, shell=False, check=False,
                                text=True, capture_output=True, timeout=10)
                match = re.fullmatch(r"v(\d+)\.\d+\.\d+\s*", version.stdout)
                if version.returncode != 0 or not match or int(match.group(1)) != prerequisite["major"]:
                    missing.append("Node {} is required on child PATH".format(prerequisite["major"]))
            except (OSError, subprocess.TimeoutExpired):
                missing.append("Unable to inspect required Node {}".format(prerequisite["major"]))
        elif kind == "argument":
            if prerequisite["name"] == "preview_origin" and not valid_preview_origin(preview_origin):
                missing.append("--preview-origin requires an explicit loopback HTTP origin and port")
    return list(dict.fromkeys(missing))


def terminate_child(process):
    """Stop the owned process group and reap the child, including UV descendants."""
    if process.poll() is not None and os.name != "posix":
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
        process.wait()
    if os.name == "posix":
        # The leader can exit before a descendant which ignored SIGTERM.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def execute_child(argv, cwd, environment, result_path=None):
    """Separate process, inherited output, no shell, owned lifetime."""
    process = subprocess.Popen(argv, cwd=str(cwd), env=environment, shell=False,
                               start_new_session=(os.name == "posix"))
    try:
        return {"exit_code": process.wait(), "interrupted": False}
    except KeyboardInterrupt:
        terminate_child(process)
        return {"exit_code": 130, "interrupted": True}
    except BaseException:
        terminate_child(process)
        raise


@contextlib.contextmanager
def interruption_handlers():
    previous = {}
    def interrupt(_number, _frame):
        raise KeyboardInterrupt
    try:
        for number in (signal.SIGINT, signal.SIGTERM):
            previous[number] = signal.signal(number, interrupt)
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def read_unittest_result(path):
    """The result channel, rather than human stdout, determines unittest outcomes."""
    result = json.loads(path.read_text(encoding="utf-8"))
    allowed = {"passed", "failed", "all_skipped", "empty", "discovery_error", "interrupted"}
    if (not isinstance(result, dict) or type(result.get("schema_version")) is not int
            or result["schema_version"] != 1 or result.get("outcome") not in allowed):
        raise ValueError("invalid unittest result version/outcome")
    counts = result.get("counts")
    fields = ("discovered", "tests_run", "failures", "errors", "skipped",
              "expected_failures", "unexpected_successes")
    if not isinstance(counts, dict) or any(type(counts.get(key)) is not int or counts[key] < 0
                                          for key in fields):
        raise ValueError("invalid unittest counts")
    successes = result.get("successful_callbacks")
    if type(successes) is not int or successes < 0:
        raise ValueError("invalid unittest successful callbacks")
    skips = result.get("skips")
    if (not isinstance(skips, list) or len(skips) != counts["skipped"]
            or any(not isinstance(item, dict) or not isinstance(item.get("test"), str)
                   or not isinstance(item.get("reason"), str) for item in skips)):
        raise ValueError("invalid unittest skip records")
    if result["outcome"] == "passed" and (counts["discovered"] == 0 or counts["tests_run"] == 0
            or counts["failures"] or counts["errors"] or counts["unexpected_successes"]
            or (counts["skipped"] and not successes and not counts["expected_failures"])):
        raise ValueError("inconsistent passing unittest result")
    return result


def planned_check(check, root, preview_origin=None):
    return {"id": check["id"], "owner": check["owner"], "kind": check["kind"],
            "argv": build_command(check, root, preview_origin=preview_origin),
            "cwd": str(root / check["cwd"]), "scope": list(check["scope"]),
            "environment_overrides": {key: value.replace("{root}", str(root))
                                      for key, value in check.get("env", {}).items()},
            "prerequisites": prerequisites_for_check(check, root)}


def run_checks(registry, selection, root, *, requested=None, executor=execute_child,
               prerequisite_checker=missing_prerequisites, environ=None, preview_origin=None,
               output=None):
    output = sys.stdout if output is None else output
    root = Path(root).resolve()
    summary = {"schema_version": SUMMARY_VERSION,
               "requested": requested or {"profiles": [registry["default_profile"]], "checks": []},
               "selection": [check["id"] for check in selection], "checks": [],
               "outcome": "passed", "exit_code": 0,
               "limitations": ["Only selected checks were executed.",
                               "Unittest counts come from the child TestResult; command checks have no test counts.",
                               "Configured-input diagnostics do not verify every partition or reproduce research."]}
    halted = False
    for check in selection:
        record = planned_check(check, root, preview_origin)
        record.update({"outcome": "not_run", "exit_code": None, "duration_seconds": 0.0,
                       "missing_prerequisites": [], "unittest": None})
        summary["checks"].append(record)
        if halted:
            record["reason"] = "Unexecuted after fail-fast"
            continue
        started = time.monotonic()
        try:
            missing = prerequisite_checker(check, root, environ=environ, preview_origin=preview_origin)
            if missing:
                record.update(outcome="prerequisite_missing", exit_code=1, missing_prerequisites=missing)
                print("[{}] Missing prerequisites: {}".format(check["id"], "; ".join(missing)), file=output)
            else:
                with tempfile.TemporaryDirectory(prefix="abacus-check-") as directory:
                    result_path = Path(directory) / "unittest-result.json"
                    record["argv"] = build_command(check, root, result_path=result_path,
                                                   preview_origin=preview_origin)
                    print("[{}] {}".format(check["id"], json.dumps(record["argv"])), file=output, flush=True)
                    execution = executor(record["argv"], Path(record["cwd"]),
                                         child_environment(check, root, environ),
                                         result_path if check["kind"] == "unittest" else None)
                    code = execution["exit_code"]
                    record["exit_code"] = code
                    if execution.get("interrupted"):
                        record["outcome"] = "interrupted"
                    elif check["kind"] == "unittest":
                        try:
                            child_result = read_unittest_result(result_path)
                        except (OSError, ValueError, TypeError):
                            record.update(outcome="failed", reason="Missing or invalid unittest result channel")
                            if code == 0:
                                record["exit_code"] = 1
                        else:
                            record["unittest"] = child_result
                            record["outcome"] = child_result["outcome"] if code == 0 else (
                                "interrupted" if code in (130, -signal.SIGINT, -signal.SIGTERM) else
                                child_result["outcome"] if child_result["outcome"] != "passed" else "failed")
                    else:
                        record["outcome"] = "passed" if code == 0 else "failed"
        except KeyboardInterrupt:
            record.update(outcome="interrupted", exit_code=130)
        except OSError as error:
            record.update(outcome="failed", exit_code=1, reason="Unable to execute check: " + str(error))
        record["duration_seconds"] = round(time.monotonic() - started, 6)
        print("[{}] {}".format(check["id"], record["outcome"]), file=output, flush=True)
        if record["outcome"] != "passed":
            halted = True
            summary["outcome"] = "interrupted" if record["outcome"] == "interrupted" else "failed"
            summary["exit_code"] = 130 if record["outcome"] == "interrupted" else (record["exit_code"] or 1)
    return summary


def print_plan(selection, root, *, preview_origin=None, output=None):
    output = sys.stdout if output is None else output
    for check in selection:
        print(json.dumps(planned_check(check, root, preview_origin), sort_keys=True), file=output)


def print_context(registry, selector, root, *, output=None):
    output = sys.stdout if output is None else output
    owner = registry_api().owner_for_context(registry, selector)
    identity = owner["id"]
    print("{}: {}".format(identity, owner["description"]), file=output)
    for label, field in (("Read first", "read_first"), ("Entry points", "entry_points"),
                         ("Preservation", "preservation")):
        print(label + ":", file=output)
        for value in owner[field]:
            print("  " + value, file=output)
    checks = [check for check in registry["checks"] if check["owner"] == identity
              or check["id"] in owner.get("related_checks", [])]
    if not checks:
        print("Checks: " + owner.get("no_suite_reason", "No local executable suite."), file=output)
    else:
        print("Focused checks:", file=output)
        print_plan(checks, root, output=output)
    print("Deeper context: " + ", ".join(owner["guides"]), file=output)


def parser():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--list", action="store_true", help="List explicit profiles and check plans without executing")
    arguments.add_argument("--profile", action="append", default=[], help="Select an explicit profile (repeatable)")
    arguments.add_argument("--check", action="append", default=[], help="Select an explicit check (repeatable)")
    arguments.add_argument("--dry-run", action="store_true", help="Print selected argv/cwd/scope/prerequisites without executing")
    arguments.add_argument("--context", help="Print bounded context for an explicit owner/study")
    arguments.add_argument("--report", type=Path, help="Persist execution summary at this explicit path (parent must exist)")
    arguments.add_argument("--preview-origin", help="Explicit running loopback HTTP origin for selected preview smoke")
    return arguments


def main(argv=None, *, root=None, registry=None, executor=execute_child):
    arguments = parser()
    options = arguments.parse_args(argv)
    root = ROOT if root is None else Path(root).resolve()
    if options.context and (options.list or options.dry_run or options.profile or options.check):
        arguments.error("--context cannot be combined with list/dry-run/check/profile selection")
    if options.list and (options.dry_run or options.profile or options.check):
        arguments.error("--list cannot be combined with dry-run/check/profile selection")
    if options.report and (options.list or options.dry_run or options.context):
        arguments.error("--report is available only for execution")
    api = registry_api()
    try:
        registry = api.load_registry(root) if registry is None else registry
        if options.context:
            print_context(registry, options.context, root)
            return 0
        if options.list:
            for name, profile in registry["profiles"].items():
                print("{}: {} [{}]".format(name, profile["description"], ", ".join(profile["checks"])))
            print_plan(registry["checks"], root, preview_origin=options.preview_origin)
            return 0
        selection = api.select_checks(registry, profiles=options.profile, checks=options.check,
                                      use_default=not (options.profile or options.check))
        if not selection:
            arguments.error("Selection must contain at least one check")
        if options.dry_run:
            print_plan(selection, root, preview_origin=options.preview_origin)
            return 0
    except api.RegistryError as error:
        print("Registry/selection error: " + str(error), file=sys.stderr)
        return 2
    requested = {"profiles": options.profile or ([registry["default_profile"]] if not options.check else []),
                 "checks": options.check}
    with interruption_handlers():
        summary = run_checks(registry, selection, root, requested=requested, executor=executor,
                             preview_origin=options.preview_origin)
    print("Selected checks: {} ({} selected)".format(summary["outcome"], len(selection)))
    if options.report:
        try:
            options.report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        except OSError as error:
            print("Unable to write explicit report: " + str(error), file=sys.stderr)
            return 1
    return summary["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
