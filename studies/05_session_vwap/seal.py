"""Seal a verified staged VWAP evidence bundle under a unique immutable run ID."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def output(cmd: list[str], root: Path) -> str:
    return subprocess.check_output(cmd, cwd=root, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    stage = root / "work/05_session_vwap" / args.run_id
    dest = root / "runs/05_session_vwap" / args.run_id
    if not stage.is_dir() or dest.exists():
        raise FileNotFoundError("stage missing or completed run already exists")
    required = ["config.json", "inputs.lock.json", "protocol-1.0.0.md", "input-verification.json",
                "extraction-summary.json", "source-audit.json", "denominator-audit.json", "events.manifest.json",
                "metrics.json", "report.md", "report.html", "advice.md", "publication.json",
                "verification-results.json",
                "tables/scorecards.csv", "tables/breakdowns.csv", "tables/stability.csv",
                "tables/baselines.csv",
                "tables/paths.csv", "tables/threshold_times.csv", "tables/departure_classes.csv",
                "tables/window_populations.csv",
                "tables/exclusions.csv",
                "tables/eligibility.csv",
                "tables/warmup_sensitivity.csv",
                "figures/barrier-outcomes.svg", "figures/barrier-outcomes.png"]
    for name in required:
        if not (stage / name).is_file():
            raise FileNotFoundError(stage / name)
    denominator_audit = json.loads((stage / "denominator-audit.json").read_text())
    if denominator_audit.get("status") != "passed":
        raise ValueError("denominator audit has not passed")
    source_audit = json.loads((stage / "source-audit.json").read_text())
    if len(source_audit) != 23 or any(row["references_audited"] <= 0 for row in source_audit):
        raise ValueError("source audit is incomplete")
    verification = json.loads((stage / "verification-results.json").read_text())
    if verification.get("status") != "passed":
        raise ValueError("verification results have not passed")
    events = sorted((stage / "events").glob("events_*.parquet"))
    windows = sorted((stage / "events").glob("windows_*.parquet"))
    if len(events) != 23 or len(windows) != 23:
        raise ValueError(f"expected 23 product-year partitions each, found {len(events)} and {len(windows)}")
    warmup_ids = {}
    for minutes in (20, 40):
        sensitivity = stage / "sensitivity" / f"warmup_{minutes}"
        files = list((sensitivity / "events").glob("events_*.parquet"))
        if len(files) != 23:
            raise ValueError(f"expected 23 warm-up {minutes} event partitions, found {len(files)}")
        warmup_ids[minutes] = json.loads((sensitivity / "config.json").read_text())["run_id"]
    study = root / "studies/05_session_vwap"
    snapshot = stage / "source-snapshot"
    snapshot.mkdir()
    for relative in ("run.py", "summarize.py", "enrich.py", "audit.py", "warmup_sensitivity.py", "seal.py", "protocol-1.0.0.md",
                     "study.yaml", "study.json", "inputs.lock.json", "README.md", "notes.md"):
        shutil.copy2(study / relative, snapshot / relative)
    shutil.copytree(study / "src", snapshot / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(study / "tests", snapshot / "tests", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    revision = output(["git", "rev-parse", "HEAD"], root)
    status = output(["git", "status", "--short"], root)
    (stage / "git-status.txt").write_text(status + "\n")
    (stage / "checks.json").write_text(json.dumps({
        "focused_tests": ".venv/bin/python -m unittest discover -s studies/05_session_vwap/tests -v",
        "input_identity": "input-verification.json",
        "partition_audit": "source-audit.json",
        "denominator_audit": "denominator-audit.json",
        "verification_results": "verification-results.json",
        "status": "passed_before_seal"}, indent=2) + "\n")
    artifacts = []
    for path in sorted(stage.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            artifacts.append({"path": str(path.relative_to(stage)), "bytes": path.stat().st_size,
                              "sha256": digest(path)})
    manifest = {"schema_version": 1, "study_id": "05_session_vwap", "run_id": args.run_id,
                "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
                "protocol_version": "1.0.0", "template_version": "2026-09-22",
                "git_revision": revision, "git_status_at_seal": "git-status.txt",
                "source_snapshot": "source-snapshot/",
                "environment": {"python": platform.python_version(), "platform": platform.platform(),
                                "dependency_lock_sha256": digest(root / "uv.lock")},
                "release_id": "session_anchored_vwap__1.0.0",
                "bootstrap_seeds": {"session": 310729, "week": 310730,
                                    "baseline_conditional": 310731},
                "exact_commands": [
                    f".venv/bin/python studies/05_session_vwap/run.py --run-id {args.run_id} --workers 3",
                    f".venv/bin/python studies/05_session_vwap/enrich.py --run-id {args.run_id} --workers 3",
                    f".venv/bin/python studies/05_session_vwap/audit.py --run-id {args.run_id}",
                    f".venv/bin/python studies/05_session_vwap/summarize.py --run-id {args.run_id}",
                    f".venv/bin/python studies/05_session_vwap/run.py --run-id {warmup_ids[20]} --warmup 20 --workers 2",
                    f".venv/bin/python studies/05_session_vwap/run.py --run-id {warmup_ids[40]} --warmup 40 --workers 2",
                    f".venv/bin/python studies/05_session_vwap/warmup_sensitivity.py --primary-run-id {args.run_id} --warmup-20-run-id {warmup_ids[20]} --warmup-40-run-id {warmup_ids[40]}",
                    ".venv/bin/python -m unittest discover -s studies/05_session_vwap/tests -v",
                    f".venv/bin/python studies/05_session_vwap/seal.py --run-id {args.run_id}"],
                "checks": "checks.json", "inputs": "input-verification.json",
                "artifact_hashes": artifacts}
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    dest.parent.mkdir(parents=True, exist_ok=True)
    stage.rename(dest)
    print(dest)


if __name__ == "__main__":
    main()
