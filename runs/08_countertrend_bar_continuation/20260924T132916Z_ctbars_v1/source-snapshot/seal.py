"""Seal a checked staging directory as a new immutable local evidence bundle."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SOURCE_FILES = ["README.md", "plan.md", "study.yaml", "study.json", "notes.md",
                "inputs.lock.json", "run.py", "summarize.py", "verify.py", "render.py",
                "seal.py", "src/engine.py", "tests/test_engine.py"]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    study = Path(__file__).resolve().parent
    stage = args.stage.resolve()
    if not stage.is_relative_to((root / "work" / study.name).resolve()) or not stage.is_dir():
        raise ValueError("stage must exist under this study's work directory")
    run_id = stage.name
    destination = root / "runs" / study.name / run_id
    if destination.exists():
        raise FileExistsError(destination)
    required = ["audit.json", "checks.json", "config.json", "inputs.lock.json",
                "metrics.json", "report.md", "report.html", "advice.md", "focused-tests.log"]
    if not all((stage / file).is_file() for file in required):
        raise FileNotFoundError("staged evidence is incomplete")
    audit = json.loads((stage / "audit.json").read_text())
    checks = json.loads((stage / "checks.json").read_text())
    if checks.get("status") != "pass" or len(audit.get("charts", {})) != 7:
        raise ValueError("verification is not complete")
    if "Ran 8 tests" not in (stage / "focused-tests.log").read_text() or "OK" not in (stage / "focused-tests.log").read_text():
        raise ValueError("focused test log is missing or failed")
    snapshot = stage / "source-snapshot"
    snapshot.mkdir()
    for name in SOURCE_FILES:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(study / name, target)
    status = subprocess.check_output(["git", "status", "--short"], cwd=root, text=True)
    (stage / "git-status.txt").write_text(status)
    event_files = sorted((stage / "tables").glob("events_*.parquet"))
    if len(event_files) != 7:
        raise ValueError("expected seven event ledgers")
    events = []
    for path in event_files:
        chart = path.stem.removeprefix("events_")
        events.append({"chart": chart, "path": path.relative_to(stage).as_posix(),
                       "rows": audit["charts"][chart]["events"], "bytes": path.stat().st_size,
                       "sha256": digest(path)})
    (stage / "events.manifest.json").write_text(json.dumps({
        "schema_version": 1, "retention": "within_completed_run", "format": "Parquet/Zstandard",
        "event_definition": "C1 ledger with signal-time fields, outcomes, exclusions, and source_row",
        "files": events}, indent=2) + "\n")
    lock = json.loads((stage / "inputs.lock.json").read_text())
    commands = [
        ".venv/bin/python -m unittest discover -s studies/08_countertrend_bar_continuation/tests -v",
        f".venv/bin/python studies/08_countertrend_bar_continuation/run.py --stage work/08_countertrend_bar_continuation/{run_id}",
        f".venv/bin/python studies/08_countertrend_bar_continuation/summarize.py --stage work/08_countertrend_bar_continuation/{run_id}",
        f".venv/bin/python studies/08_countertrend_bar_continuation/verify.py --stage work/08_countertrend_bar_continuation/{run_id}",
        f".venv/bin/python studies/08_countertrend_bar_continuation/render.py --stage work/08_countertrend_bar_continuation/{run_id}",
        f".venv/bin/python studies/08_countertrend_bar_continuation/seal.py --stage work/08_countertrend_bar_continuation/{run_id}",
    ]
    artifacts = []
    for path in sorted(p for p in stage.rglob("*") if p.is_file() and p.name != "manifest.json"):
        artifacts.append({"path": path.relative_to(stage).as_posix(),
                          "bytes": path.stat().st_size, "sha256": digest(path)})
    manifest = {
        "schema_version": 1, "study_id": study.name, "run_id": run_id,
        "executed_at_utc": audit["executed_at_utc"],
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_version": "1.0.0", "protocol_frozen_at_utc": "2026-09-24T05:47:00Z",
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "git_status_at_seal": "git-status.txt", "dirty_study_source_snapshot": "source-snapshot/",
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "pandas": importlib.metadata.version("pandas"),
                        "numpy": importlib.metadata.version("numpy"),
                        "pyarrow": importlib.metadata.version("pyarrow"),
                        "dependency_lock_sha256": digest(root / "uv.lock")},
        "inputs": {"lock": "inputs.lock.json", "manifest_sha256": lock["manifest"]["sha256"],
                   "verified_files": audit["verified_inputs"]},
        "config": "config.json", "checks": "checks.json", "test_log": "focused-tests.log",
        "exclusions": {"signal_or_outcome_completion": "same-second and unavailable boundaries excluded",
                       "larger_equal_second": "excluded from primary paired analysis",
                       "gc_sessions": ["2026-01-28", "2026-02-04", "2026-02-20",
                                       "2026-03-19", "2026-04-02"]},
        "exact_commands": commands, "event_evidence": "events.manifest.json",
        "artifact_hashes": artifacts,
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(stage, destination)
    print(destination)


if __name__ == "__main__":
    main()
