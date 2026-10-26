"""Seal one verified local segment-overlay run without touching source runs."""
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
                "inputs.lock.json", "run.py", "verify.py", "render.py", "seal.py",
                "src/stats.py", "tests/test_stats.py"]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    study = Path(__file__).resolve().parent
    root = study.parents[1]
    stage = args.stage.resolve()
    if not stage.is_relative_to((root / "work" / study.name).resolve()) or not stage.is_dir():
        raise ValueError("stage must exist under this study's work directory")
    destination = root / "runs" / study.name / stage.name
    if destination.exists():
        raise FileExistsError(destination)
    required = ["audit.json", "checks.json", "config.json", "inputs.lock.json",
                "metrics.json", "report.md", "report.html", "advice.md",
                "focused-tests.log"]
    if not all((stage / name).is_file() for name in required):
        raise FileNotFoundError("incomplete stage")
    audit = json.loads((stage / "audit.json").read_text())
    checks = json.loads((stage / "checks.json").read_text())
    if checks.get("status") != "pass" or checks.get("verified_input_files") != 34:
        raise ValueError("verification did not pass")
    test_log = (stage / "focused-tests.log").read_text()
    if "Ran 6 tests" not in test_log or "OK" not in test_log:
        raise ValueError("focused tests missing or failed")
    if (stage / "inputs.lock.json").read_bytes() != (study / "inputs.lock.json").read_bytes():
        raise ValueError("staged input lock differs from study lock")
    snapshot = stage / "source-snapshot"
    snapshot.mkdir()
    for name in SOURCE_FILES:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(study / name, target)
    (stage / "git-status.txt").write_text(subprocess.check_output(
        ["git", "status", "--short"], cwd=root, text=True))
    lock = json.loads((stage / "inputs.lock.json").read_text())
    external = [item for item in lock["files"] if item["role"].endswith("_events")]
    if len(external) != 24:
        raise ValueError("expected 24 referenced primary event ledgers")
    (stage / "events.manifest.json").write_text(json.dumps({
        "schema_version": 1, "retention": "referenced_immutable_source_runs",
        "source_runs": lock["source_runs"], "files": external}, indent=2) + "\n")
    commands = [
        ".venv/bin/python -m unittest discover -s studies/10_range_xv_session_overlay/tests -v",
        f".venv/bin/python studies/10_range_xv_session_overlay/run.py --stage work/10_range_xv_session_overlay/{stage.name}",
        f".venv/bin/python studies/10_range_xv_session_overlay/verify.py --stage work/10_range_xv_session_overlay/{stage.name}",
        f".venv/bin/python studies/10_range_xv_session_overlay/render.py --stage work/10_range_xv_session_overlay/{stage.name}",
        f".venv/bin/python studies/10_range_xv_session_overlay/seal.py --stage work/10_range_xv_session_overlay/{stage.name}",
    ]
    artifacts = [{"path": file.relative_to(stage).as_posix(),
                  "bytes": file.stat().st_size, "sha256": digest(file)}
                 for file in sorted(stage.rglob("*")) if file.is_file() and file.name != "manifest.json"]
    manifest = {"schema_version": 1, "study_id": study.name, "run_id": stage.name,
        "executed_at_utc": audit["executed_at_utc"],
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_version": "1.0.0", "inference_status": "exploratory_after_source_runs_inspected",
        "post_result_diagnostic": "study 09 ordinary pairs at run age two; not in headline screens",
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                               cwd=root, text=True).strip(),
        "git_status_at_seal": "git-status.txt",
        "dirty_study_source_snapshot": "source-snapshot/",
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
            "pandas": importlib.metadata.version("pandas"),
            "numpy": importlib.metadata.version("numpy"),
            "pyarrow": importlib.metadata.version("pyarrow"),
            "dependency_lock_sha256": digest(root / "uv.lock")},
        "inputs": {"lock": "inputs.lock.json", "verified_files": audit["verified_inputs"],
                   "external_event_evidence": "events.manifest.json"},
        "config": "config.json", "checks": "checks.json", "test_log": "focused-tests.log",
        "exclusions": {"transition": "16:00-18:00 retained but outside three-segment contrasts",
                       "study07_partial_session": "2026-09-08 excluded in source run",
                       "study08_09_gc_sessions": ["2026-01-28", "2026-02-04", "2026-02-20",
                                                   "2026-03-19", "2026-04-02"]},
        "exact_commands": commands, "artifact_hashes": artifacts}
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(stage, destination)
    print(destination)


if __name__ == "__main__":
    main()
