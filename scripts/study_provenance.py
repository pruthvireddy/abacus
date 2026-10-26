"""Bounded phase records for future Study 12/13 work stages.

These records retain declared bytes and callback outcomes. They are not an
adoption of abacus.evidence/v1, dependency discovery, or an environment audit.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone


CONTRACT = "abacus.study-phase-record/v1"
STUDIES = {"12_gc_ema_band_excursions", "13_gc_ema_band_filter_validation"}
PHASES = {"execution", "rendering", "verification", "sealing"}
REPORTS = ("report.html", "report.md", "advice.md")
COMMON = ("config.json", "inputs.lock.json", "metrics.json")
OUTPUTS = {
    "12_gc_ema_band_excursions": COMMON + (
        "tables/events.parquet", "tables/cohorts.csv", "tables/yearly.csv"),
    "13_gc_ema_band_filter_validation": COMMON + (
        "decision.json", "tables/candidate_context.parquet",
        "tables/candidate_outcomes.parquet", "tables/primary.csv",
        "tables/sensitivity.csv"),
}


class ProvenanceError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "%" in value:
        raise ProvenanceError("unsafe relative path")
    if any(part in {"", ".", ".."} for part in value.split("/")) or value.startswith("/"):
        raise ProvenanceError(f"unsafe relative path: {value}")
    return value


def ordinary(path: Path, *, missing: bool = False) -> Path:
    """Check the original lexical path, including redirected ancestors."""
    if ".." in Path(path).parts:
        raise ProvenanceError("path traversal is refused before normalization")
    path = Path(os.path.abspath(path))
    for ancestor in reversed((path, *path.parents)):
        if ancestor.is_symlink():
            raise ProvenanceError(f"symlink path component: {ancestor}")
        if ancestor.exists() and ancestor != path and not ancestor.is_dir():
            raise ProvenanceError(f"non-directory ancestor: {ancestor}")
    if path.exists() and not path.is_file():
        raise ProvenanceError(f"not an ordinary file: {path}")
    if not missing and not path.is_file():
        raise ProvenanceError(f"missing retained file: {path}")
    return path


def directory(path: Path, *, absent: bool = False) -> Path:
    if ".." in Path(path).parts:
        raise ProvenanceError("path traversal is refused before normalization")
    path = Path(os.path.abspath(path))
    for ancestor in reversed((path, *path.parents)):
        if ancestor.is_symlink():
            raise ProvenanceError(f"symlink path component: {ancestor}")
        if ancestor.exists() and not ancestor.is_dir():
            raise ProvenanceError(f"not a directory: {ancestor}")
    if absent and path.exists():
        raise FileExistsError(f"destination already exists: {path}")
    if not absent and not path.is_dir():
        raise ProvenanceError(f"missing stage directory: {path}")
    return path


def stage_path(root: Path, stage: Path, study_id: str, *, fresh: bool = False) -> Path:
    root = directory(root)
    if study_id not in STUDIES:
        raise ProvenanceError("unsupported study provenance owner")
    stage = directory(stage, absent=fresh)
    if stage.parent != root / "work" / study_id:
        raise ProvenanceError("stage must be a direct child of this study's work directory")
    _relative(stage.name)
    return stage


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with ordinary(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def identity(base: Path, relative: str) -> dict:
    relative = _relative(relative)
    path = ordinary(base / relative)
    return {"path": relative, "bytes": path.stat().st_size, "sha256": digest(path)}


def _pins(base: Path, rows: object) -> None:
    if not isinstance(rows, list) or not rows:
        raise ProvenanceError("missing nonempty artifact/source inventory")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise ProvenanceError("malformed file identity")
        path = _relative(row["path"])
        if path in seen:
            raise ProvenanceError("duplicate inventoried path")
        seen.add(path)
        if type(row["bytes"]) is not int or row["bytes"] < 0:
            raise ProvenanceError("invalid byte count")
        if not isinstance(row["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ProvenanceError("invalid SHA-256")
        if identity(base, path) != row:
            raise ProvenanceError(f"changed declared bytes: {path}")


def write_new(path: Path, data: bytes) -> None:
    ordinary(path, missing=True)
    if path.exists():
        raise FileExistsError(f"evidence already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    ordinary(path, missing=True)
    with path.open("xb") as stream:
        stream.write(data)


def write_json(path: Path, value: object) -> None:
    write_new(path, (json.dumps(value, indent=2, allow_nan=False) + "\n").encode())


def _pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise ProvenanceError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def read_json(path: Path) -> dict:
    def bad(value):
        raise ProvenanceError(f"non-finite JSON: {value}")
    def finite(value):
        result = float(value)
        if not math.isfinite(result):
            bad(value)
        return result
    try:
        value = json.loads(ordinary(path).read_text(), object_pairs_hook=_pairs,
                           parse_constant=bad, parse_float=finite)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"invalid record {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProvenanceError("record must be an object")
    return value


def sources(root: Path, study_id: str, phase: str) -> list[str]:
    """Explicit exercised scope; no automatic import or repository crawling."""
    study = f"studies/{study_id}"
    helper = "scripts/study_provenance.py"
    loader = ["packages/bhishma/src/abacus_bhishma/feature_loader.py",
              "packages/bhishma/src/abacus_bhishma/paths.py",
              "packages/bhishma/src/abacus_bhishma/manifest_selection.py",
              "packages/bhishma/src/abacus_bhishma/provenance.py",
              "packages/bhishma/src/abacus_bhishma/publication_safety.py"]
    engine = [f"{study}/src/engine.py", f"{study}/src/__init__.py",
              "packages/sahadeva/src/abacus_sahadeva/cooldown.py"]
    if phase == "execution":
        names = [f"{study}/run.py", helper, *engine, *loader]
    elif phase == "rendering":
        names = [f"{study}/render.py", helper]
    elif phase == "verification":
        names = [f"{study}/verify.py", helper]
        names += ([f"{study}/run.py", *loader, *engine]
                  if study_id.startswith("12_") else engine)
    elif phase == "sealing":
        names = [f"{study}/seal.py", helper, "scripts/numerical_test_record.py"]
    else:
        raise ProvenanceError("unknown phase")
    return sorted(set(names))


def _observe(root: Path) -> dict:
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                           text=True, stderr=subprocess.DEVNULL).strip()
        status = subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=all"],
                                         cwd=root, text=True, stderr=subprocess.DEVNULL)
        return {"status": "observed", "revision": revision, "dirty": bool(status),
                "porcelain": status}
    except (OSError, subprocess.CalledProcessError) as exc:
        return {"status": "not_run", "reason": f"git observation unavailable: {type(exc).__name__}"}


def _base(root: Path, stage: Path, study_id: str, phase: str, source_names: list[str]) -> dict:
    folder = stage / "provenance" / phase
    directory(folder, absent=True)
    declared = source_names + ([f"studies/{study_id}/{name}" for name in
                               ("plan.md", "study.yaml", "inputs.lock.json")]
                              if phase == "execution" else []) + ["uv.lock"]
    declared = sorted(set(declared))
    original = [identity(root, name) for name in declared]
    # Finish all source reads before creating this phase directory.
    contents = [(row, ordinary(root / row["path"]).read_bytes()) for row in original]
    for row, data in contents:
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ProvenanceError("source changed while retaining provenance")
    folder.mkdir(parents=True)
    retained = []
    for row, data in contents:
        name = f"provenance/{phase}/source/{row['path']}"
        write_new(stage / name, data)
        retained.append(identity(stage, name))
    git = _observe(root)
    if git["status"] == "observed":
        write_new(folder / "git-status.txt", git.pop("porcelain").encode())
        git["status_file"] = identity(stage, f"provenance/{phase}/git-status.txt")
    return {"contract": CONTRACT, "study_id": study_id, "stage_id": stage.name,
            "stage_path": stage.relative_to(root).as_posix(), "stage_location": str(stage), "phase": phase,
            "started_at_utc": now(), "state": "started", "status": "not_run",
            "reason": "phase has not returned successfully",
            "command": {"argv": list(getattr(sys, "orig_argv", [sys.executable, *sys.argv])),
                        "cwd": os.getcwd(),
                        "argv_scope": "sys.orig_argv" if hasattr(sys, "orig_argv") else
                                      "interpreter plus sys.argv; interpreter switches unavailable"},
            "runtime": {"executable": sys.executable, "version": sys.version,
                        "implementation": platform.python_implementation(),
                        "optimization": sys.flags.optimize},
            "git": git, "source_scope": "explicit declared phase sources and retained lock bytes",
            "original_sources": original, "retained_sources": retained}


def _same_sources(root: Path, stage: Path, record: dict) -> None:
    _pins(root, record["original_sources"])
    _pins(stage, record["retained_sources"])
    original = record["original_sources"]
    retained = record["retained_sources"]
    expected = [{"path": f"provenance/{record['phase']}/source/{row['path']}",
                 "bytes": row["bytes"], "sha256": row["sha256"]} for row in original]
    if retained != expected:
        raise ProvenanceError("retained source inventory does not match declared original scope")


def require_phase(root: Path, stage: Path, study_id: str, phase: str) -> dict:
    stage = stage_path(root, stage, study_id)
    failed = ordinary(stage / "provenance" / phase / "failed.json", missing=True)
    if failed.exists():
        raise ProvenanceError(f"{phase} has a retained failure record")
    record = read_json(stage / "provenance" / phase / "completed.json")
    required = {"contract", "study_id", "stage_id", "stage_path", "stage_location", "phase",
                "started_at_utc", "completed_at_utc", "state", "status", "command", "runtime",
                "git", "source_scope", "original_sources", "retained_sources", "dependencies",
                "artifacts", "outcome", "started_record"}
    required |= ({"inputs"} if phase == "rendering" else
                 {"scientific_checks"} if phase == "verification" else set())
    if set(record) != required:
        raise ProvenanceError("missing or unknown phase record fields")
    for key, expected in {"contract": CONTRACT, "study_id": study_id,
                          "stage_id": stage.name, "stage_path": stage.relative_to(root).as_posix(),
                          "stage_location": str(stage),
                          "phase": phase, "state": "completed", "status": "passed"}.items():
        if record.get(key) != expected:
            raise ProvenanceError(f"invalid {phase} identity/outcome: {key}; old stages need new execution")
    outcome = record.get("outcome")
    if (outcome != {"kind": "callback_returned", "exit_code": 0}
            or type(outcome.get("exit_code")) is not int):
        raise ProvenanceError("phase did not return successfully")
    times = []
    for key in ("started_at_utc", "completed_at_utc"):
        try:
            value = record[key]
            if not isinstance(value, str):
                raise ValueError("timestamp is not a string")
            stamp = datetime.fromisoformat(value)
            if stamp.utcoffset() is None:
                raise ValueError("timestamp has no timezone")
            times.append(stamp)
        except (ValueError, TypeError) as exc:
            raise ProvenanceError("invalid timezone-aware execution timestamp") from exc
    if times[1] < times[0]:
        raise ProvenanceError("completion precedes start")
    runtime = record.get("runtime")
    if (not isinstance(runtime, dict) or set(runtime) != {"executable", "version", "implementation", "optimization"}
            or type(runtime.get("optimization")) is not int or runtime["optimization"] < 0
            or any(not isinstance(runtime.get(key), str) or not runtime[key] for key in
                   ("executable", "version", "implementation")) or not Path(runtime["executable"]).is_absolute()):
        raise ProvenanceError("invalid runtime observation")
    if phase == "verification" and runtime["optimization"] != 0:
        raise ProvenanceError("optimized verification is not an ordinary scientific pass")
    command = record.get("command")
    if (not isinstance(command, dict) or set(command) != {"argv", "cwd", "argv_scope"}
            or command["argv_scope"] not in {"sys.orig_argv", "interpreter plus sys.argv; interpreter switches unavailable"}
            or not isinstance(command.get("argv"), list)
            or not command["argv"] or any(not isinstance(x, str) or not x for x in command["argv"])
            or not isinstance(command.get("cwd"), str) or not Path(command["cwd"]).is_absolute()):
        raise ProvenanceError("invalid actual command observation")
    _pins(stage, [record["started_record"]])
    if record["started_record"]["path"] != f"provenance/{phase}/started.json":
        raise ProvenanceError("wrong started-record binding")
    started = read_json(stage / record["started_record"]["path"])
    started_fields = required - {"completed_at_utc", "artifacts", "outcome", "started_record", "scientific_checks"}
    if (set(started) != started_fields | {"reason"} or started.get("state") != "started"
            or started.get("status") != "not_run" or not isinstance(started.get("reason"), str)
            or not started["reason"]):
        raise ProvenanceError("malformed retained start record")
    for key in started_fields - {"state", "status"}:
        if started[key] != record[key]:
            raise ProvenanceError(f"completed observation differs from retained start: {key}")
    if not isinstance(record["source_scope"], str) or not record["source_scope"]:
        raise ProvenanceError("missing declared source scope")
    _same_sources(root, stage, record)
    git = record.get("git")
    if not isinstance(git, dict) or git.get("status") not in {"observed", "not_run"}:
        raise ProvenanceError("missing Git observation")
    if git["status"] == "observed":
        if (type(git.get("dirty")) is not bool or not isinstance(git.get("revision"), str)
                or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", git["revision"])):
            raise ProvenanceError("invalid Git revision/dirty observation")
        _pins(stage, [git.get("status_file")])
        if git["status_file"]["path"] != f"provenance/{phase}/git-status.txt":
            raise ProvenanceError("wrong retained Git-status path")
    elif not isinstance(git.get("reason"), str) or not git["reason"]:
        raise ProvenanceError("not-run Git observation requires a reason")
    required_sources = set(sources(root, study_id, phase)) | {"uv.lock"}
    if phase == "execution":
        required_sources |= {f"studies/{study_id}/{name}" for name in ("plan.md", "study.yaml", "inputs.lock.json")}
    if {row["path"] for row in record["original_sources"]} != required_sources:
        raise ProvenanceError("missing or changed explicit phase source scope")
    _pins(stage, record.get("artifacts"))
    expected_artifacts = set(OUTPUTS[study_id]) if phase == "execution" else set(REPORTS)
    if phase == "verification":
        expected_artifacts = set(OUTPUTS[study_id]) | set(REPORTS) | {"checks.json"}
    if phase in {"execution", "rendering", "verification"} and {row["path"] for row in record["artifacts"]} != expected_artifacts:
        raise ProvenanceError("phase artifact scope is incomplete or changed")
    if phase == "rendering":
        _pins(stage, record.get("inputs"))
        if {row["path"] for row in record["inputs"]} != set(OUTPUTS[study_id]):
            raise ProvenanceError("rendering input scope is incomplete")
    if not isinstance(record["dependencies"], list):
        raise ProvenanceError("phase dependencies must be a list")
    if record["dependencies"]:
        _pins(stage, record["dependencies"])
    if phase == "rendering":
        expected_dependencies = {"provenance/execution/completed.json"}
    elif phase == "verification":
        expected_dependencies = {"provenance/execution/completed.json", "provenance/rendering/completed.json"}
    else:
        expected_dependencies = set()
    if phase != "sealing" and {row["path"] for row in record.get("dependencies", [])} != expected_dependencies:
        raise ProvenanceError("missing phase receipt dependency")
    if phase == "verification":
        checks = read_json(stage / "checks.json")
        if not isinstance(record["scientific_checks"], dict):
            raise ProvenanceError("malformed recorded scientific checks")
        _scientific(study_id, record["scientific_checks"])
        if record["scientific_checks"] != checks:
            raise ProvenanceError("scientific receipt differs from retained checks")
    return record


def _scientific(study_id: str, checks: dict) -> None:
    key, count = (("statistic_cells", 595) if study_id.startswith("12_")
                  else ("baseline_cells_matching_sealed_study_12", 70))
    if checks.get("status") != "pass" or type(checks.get(key)) is not int or checks[key] != count:
        raise ProvenanceError("required study scientific verification did not pass")


def run_phase(root: Path, study_id: str, stage: Path, phase: str, callback, *, source_names=None):
    """Execute one study-owned callback with append-only, phase-specific evidence."""
    stage = stage_path(root, stage, study_id, fresh=phase == "execution")
    if phase == "verification" and sys.flags.optimize:
        raise ProvenanceError("scientific verification requires ordinary Python; python -O is refused")
    dependencies = []
    if phase in {"rendering", "verification"}:
        require_phase(root, stage, study_id, "execution")
        dependencies.append(identity(stage, "provenance/execution/completed.json"))
    if phase == "verification":
        require_phase(root, stage, study_id, "rendering")
        dependencies.append(identity(stage, "provenance/rendering/completed.json"))
    if phase == "execution":
        stage.mkdir(parents=True)
    record = _base(root, stage, study_id, phase,
                   sources(root, study_id, phase) if source_names is None else source_names)
    record["dependencies"] = dependencies
    if phase == "rendering":
        record["inputs"] = [identity(stage, name) for name in OUTPUTS[study_id]]
    names = (OUTPUTS[study_id] if phase == "execution" else REPORTS)
    if phase == "verification":
        names = OUTPUTS[study_id] + REPORTS
        before = [identity(stage, name) for name in names]
    write_json(stage / "provenance" / phase / "started.json", record)
    record["started_record"] = identity(stage, f"provenance/{phase}/started.json")
    try:
        result = callback()
        _same_sources(root, stage, record)
        if dependencies:
            _pins(stage, dependencies)
        if phase == "rendering":
            _pins(stage, record["inputs"])
        artifacts = [identity(stage, name) for name in names]
        if phase == "verification":
            if artifacts != before:
                raise ProvenanceError("staged artifacts changed during scientific verification")
            if not isinstance(result, dict):
                raise ProvenanceError("verifier must return its actual study checks")
            _scientific(study_id, result)
            write_json(stage / "checks.json", result)
            artifacts.append(identity(stage, "checks.json"))
        record.update(state="completed", status="passed", completed_at_utc=now(),
                      outcome={"kind": "callback_returned", "exit_code": 0}, artifacts=artifacts)
        record.pop("reason", None)
        if phase == "verification":
            record["scientific_checks"] = result
        write_json(stage / "provenance" / phase / "completed.json", record)
        return result
    except BaseException as exc:
        record.update(state="failed", status="failed", completed_at_utc=now(),
                      outcome={"kind": "callback_failed", "exception": type(exc).__name__},
                      reason=str(exc))
        write_json(stage / "provenance" / phase / "failed.json", record)
        raise


def preflight(root: Path, stage: Path, study_id: str, *, numerical: bool = True) -> dict:
    stage = stage_path(root, stage, study_id)
    destination = directory(root / "runs" / study_id / stage.name, absent=True)
    for phase in ("execution", "rendering", "verification"):
        require_phase(root, stage, study_id, phase)
    receipt = read_json(stage / "provenance/verification/completed.json")
    checks = read_json(stage / "checks.json")
    _scientific(study_id, checks)
    if receipt.get("scientific_checks") != checks:
        raise ProvenanceError("checks differ from the verifier's retained receipt")
    for name in ("events.manifest.json", "manifest.json"):
        path = ordinary(stage / name, missing=True)
        if path.exists():
            raise FileExistsError(f"sealing metadata already exists: {path}")
    directory(stage / "provenance/sealing", absent=True)
    if numerical:
        from numerical_test_record import require_numerical_record
        numerical_record = require_numerical_record(stage, root, study_id)
    else:
        numerical_record = None
    return {"stage": stage, "destination": destination, "checks": checks,
            "verification": receipt, "numerical_record": numerical_record}


def seal_stage(root: Path, study_id: str, stage: Path, event_manifest) -> Path:
    """Preflight before any completed-run directory; numerical policy stays separate."""
    ready = preflight(root, stage, study_id)
    stage, destination = ready["stage"], ready["destination"]
    # Reading Parquet metadata is a study-local callback, after all required gates.
    events = event_manifest(stage)
    record = _base(root, stage, study_id, "sealing", sources(root, study_id, "sealing"))
    record["dependencies"] = [identity(stage, f"provenance/{phase}/completed.json")
                              for phase in ("execution", "rendering", "verification")]
    record["dependencies"].append(identity(stage, "numerical-tests/record.json"))
    write_json(stage / "provenance/sealing/started.json", record)
    record["started_record"] = identity(stage, "provenance/sealing/started.json")
    try:
        # Repeat byte/gate checks after metadata reads and source retention.
        for phase in ("execution", "rendering", "verification"):
            require_phase(root, stage, study_id, phase)
        from numerical_test_record import require_numerical_record
        require_numerical_record(stage, root, study_id)
        directory(destination, absent=True)
        _same_sources(root, stage, record)
        write_json(stage / "events.manifest.json", events)
        record.update(state="prepared", status="passed", completed_at_utc=now(),
                      outcome={"kind": "callback_returned", "exit_code": 0},
                      artifacts=[identity(stage, "events.manifest.json")],
                      completion_scope="sealing preparation completed; move outcome is observed by caller")
        record.pop("reason", None)
        write_json(stage / "provenance/sealing/prepared.json", record)
        inventory = []
        for path in sorted(stage.rglob("*")):
            if path.is_symlink():
                raise ProvenanceError(f"symlink in staged evidence: {path}")
            if path.is_file():
                inventory.append(identity(stage, path.relative_to(stage).as_posix()))
        manifest = {
            "study_id": study_id, "run_id": stage.name, "sealed_at_utc": now(),
            "manifest_family": "study-local retained phase records; abacus.evidence/v1 adoption deferred",
            "execution_provenance": "provenance/execution/completed.json",
            "rendering_provenance": "provenance/rendering/completed.json",
            "verification_receipt": "provenance/verification/completed.json",
            "sealing_provenance": "provenance/sealing/prepared.json",
            "sealing_provenance_scope": "pre-move preparation; caller observes final move outcome",
            "checks": ready["checks"],
            "required_checks": [
                {"name": "study_scientific_verification", "status": "passed",
                 "record": "provenance/verification/completed.json"},
                {"name": "owned_numerical_suite", "status": "passed", "record": "numerical-tests/record.json"}],
            "supplementary_checks": [{"name": "workspace_gate", "status": "not_run",
                                      "reason": "sealing does not execute the workspace harness"},
                                     {"name": "browser_report_inspection", "status": "not_run",
                                      "reason": "not recorded by this study sealer"}],
            "inputs_lock_sha256": digest(stage / "inputs.lock.json"),
            "config_sha256": digest(stage / "config.json"), "artifacts": inventory}
        write_json(stage / "manifest.json", manifest)
        # No locks or multi-artifact transaction: preserve the diagnostic stage on failure.
        for phase in ("execution", "rendering", "verification"):
            require_phase(root, stage, study_id, phase)
        require_numerical_record(stage, root, study_id)
        _same_sources(root, stage, record)
        _pins(stage, record["dependencies"])
        _pins(stage, [record["started_record"]])
        directory(destination, absent=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        directory(destination, absent=True)
        stage.rename(destination)
        return destination
    except BaseException as exc:
        record.update(state="failed", status="failed", completed_at_utc=now(),
                      outcome={"kind": "sealing_failed", "exception": type(exc).__name__}, reason=str(exc))
        write_json(stage / "provenance/sealing/failed.json", record)
        raise
