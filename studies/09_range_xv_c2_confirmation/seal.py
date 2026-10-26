"""Seal a checked staging directory as a new immutable local evidence bundle."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


_SCRIPT_DIRECTORY = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(_SCRIPT_DIRECTORY))
from numerical_test_record import check_path, require_test_evidence


SOURCE_FILES = ["README.md", "plan.md", "study.yaml", "study.json", "notes.md",
                "inputs.lock.json", "run.py", "summarize.py", "verify.py", "render.py",
                "seal.py", "src/engine.py", "tests/test_engine.py"]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--legacy-test-log", action="store_true",
                        help="Explicit old log-only compatibility; refuses adopted structured stages")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    study = Path(__file__).resolve().parent
    stage = check_path(args.stage, kind="directory")
    if not stage.is_relative_to((root / "work" / study.name).resolve()) or not stage.is_dir():
        raise ValueError("stage must exist under this study's work directory")
    run_id = stage.name
    destination = root / "runs" / study.name / run_id
    check_path(destination, absent=True)
    required = ["audit.json", "checks.json", "config.json", "inputs.lock.json",
                "metrics.json", "report.md", "report.html", "advice.md"]
    if not all((stage / file).is_file() for file in required):
        raise FileNotFoundError("staged evidence is incomplete")
    for name in required:
        check_path(stage / name, kind="file")
    audit = json.loads((stage / "audit.json").read_text())
    checks = json.loads((stage / "checks.json").read_text())
    if checks.get("status") != "pass" or len(audit.get("charts", {})) != 7:
        raise ValueError("verification is not complete")
    test_evidence = require_test_evidence(stage, root, study.name,
                                          legacy_test_log=args.legacy_test_log)
    for name in ("source-snapshot", "git-status.txt", "events.manifest.json", "manifest.json"):
        check_path(stage / name, absent=True)
        check_path(stage / (name + ".part"), absent=True)
    check_path(stage / "tables", kind="directory")
    event_files = sorted((stage / "tables").glob("opportunities_*.parquet")) + sorted(
        (stage / "tables").glob("ordinary_*.parquet"))
    if len(event_files) != 14:
        raise ValueError("expected seven C1 and seven ordinary-pair ledgers")
    for path in event_files:
        check_path(path, kind="file")
    snapshot = stage / "source-snapshot"
    snapshot.mkdir()
    for name in SOURCE_FILES:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(study / name, target)
    status = subprocess.check_output(["git", "status", "--short"], cwd=root, text=True)
    (stage / "git-status.txt").write_text(status)
    events = []
    for path in event_files:
        kind, chart = path.stem.split("_", 1)
        events.append({"chart": chart, "kind": kind,
                       "path": path.relative_to(stage).as_posix(),
                       "rows": audit["charts"][chart]["ordinary_pairs" if kind == "ordinary" else kind],
                       "bytes": path.stat().st_size,
                       "sha256": digest(path)})
    (stage / "events.manifest.json").write_text(json.dumps({
        "schema_version": 1, "retention": "within_completed_run", "format": "Parquet/Zstandard",
        "event_definition": "C1 opportunity and ordinary-pair ledgers with timing, outcomes, exclusions, and source rows",
        "files": events}, indent=2) + "\n")
    lock = json.loads((stage / "inputs.lock.json").read_text())
    commands = [
        ".venv/bin/python -m unittest discover -s studies/09_range_xv_c2_confirmation/tests -v",
        f".venv/bin/python studies/09_range_xv_c2_confirmation/run.py --stage work/09_range_xv_c2_confirmation/{run_id}",
        f".venv/bin/python studies/09_range_xv_c2_confirmation/summarize.py --stage work/09_range_xv_c2_confirmation/{run_id}",
        f".venv/bin/python studies/09_range_xv_c2_confirmation/verify.py --stage work/09_range_xv_c2_confirmation/{run_id}",
        f".venv/bin/python studies/09_range_xv_c2_confirmation/render.py --stage work/09_range_xv_c2_confirmation/{run_id}",
        f".venv/bin/python studies/09_range_xv_c2_confirmation/seal.py --stage work/09_range_xv_c2_confirmation/{run_id}",
    ]
    if test_evidence["mode"] == "structured":
        commands[0] = shlex.join(test_evidence["command"]["argv"])
    artifacts = []
    for path in sorted(p for p in stage.rglob("*") if p.is_file() and p.name != "manifest.json"):
        artifacts.append({"path": path.relative_to(stage).as_posix(),
                          "bytes": path.stat().st_size, "sha256": digest(path)})
    manifest = {
        "schema_version": 1, "study_id": study.name, "run_id": run_id,
        "executed_at_utc": audit["executed_at_utc"],
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_version": "1.0.0", "protocol_frozen_at_utc": "2026-09-24T13:56:47Z",
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "git_status_at_seal": "git-status.txt", "dirty_study_source_snapshot": "source-snapshot/",
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "pandas": importlib.metadata.version("pandas"),
                        "numpy": importlib.metadata.version("numpy"),
                        "pyarrow": importlib.metadata.version("pyarrow"),
                        "dependency_lock_sha256": digest(root / "uv.lock")},
        "inputs": {"lock": "inputs.lock.json", "manifest_sha256": lock["manifest"]["sha256"],
                   "verified_files": audit["verified_inputs"]},
        "config": "config.json", "checks": "checks.json", "test_log": test_evidence["log"],
        "numerical_test_evidence": test_evidence,
        "exclusions": {"signal_or_outcome_completion": "C1 through C4 same-second and unavailable boundaries excluded",
                       "larger_equal_second": "excluded from one-bar aligned snapback estimate; sensitivity retained",
                       "gc_sessions": ["2026-01-28", "2026-02-04", "2026-02-20",
                                       "2026-03-19", "2026-04-02"]},
        "exact_commands": commands, "event_evidence": "events.manifest.json",
        "artifact_hashes": artifacts,
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    current_test_evidence = require_test_evidence(stage, root, study.name,
                                                  legacy_test_log=args.legacy_test_log)
    if current_test_evidence != test_evidence:
        raise ValueError("numerical test evidence changed while preparing the seal")
    check_path(destination, absent=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    current_test_evidence = require_test_evidence(stage, root, study.name,
                                                  legacy_test_log=args.legacy_test_log)
    if current_test_evidence != test_evidence:
        raise ValueError("numerical test evidence changed before the final move")
    check_path(destination, absent=True)
    os.replace(stage, destination)
    print(destination)


if __name__ == "__main__":
    main()
