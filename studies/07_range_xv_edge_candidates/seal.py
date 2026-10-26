"""Seal a verified Range XV evidence bundle exactly once."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shutil
import subprocess

from src.engine import digest


def command(args: list[str], root: Path) -> str:
    return subprocess.check_output(args, cwd=root, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    study = Path(__file__).resolve().parent
    stage = root / "work" / study.name / args.run_id
    dest = root / "runs" / study.name / args.run_id
    if not stage.is_dir() or dest.exists():
        raise FileNotFoundError("stage absent or destination already exists")
    verification = json.loads((stage / "verification-results.json").read_text())
    if verification.get("status") != "passed" or verification.get("run_id") != args.run_id:
        raise ValueError("staged evidence has not passed verification")
    snapshot = stage / "source-snapshot"
    if snapshot.exists():
        raise FileExistsError(snapshot)
    snapshot.mkdir()
    for name in ("plan.md", "README.md", "notes.md", "study.json", "study.yaml", "inputs.lock.json",
                 "protocol-1.0.0.json", "protocol-1.0.1.json", "run.py", "verify.py", "seal.py"):
        shutil.copy2(study / name, snapshot / name)
    for folder in ("src", "tests"):
        shutil.copytree(study / folder, snapshot / folder, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    revision = command(["git", "rev-parse", "HEAD"], root)
    (stage / "git-status.txt").write_text(command(["git", "status", "--short"], root) + "\n")
    evidence = []
    for path in sorted(stage.glob("*.parquet")):
        import pyarrow.parquet as pq
        evidence.append({"path": path.name, "rows": pq.ParquetFile(path).metadata.num_rows,
                         "bytes": path.stat().st_size, "sha256": digest(path)})
    (stage / "events.manifest.json").write_text(json.dumps({"format": "Parquet", "retention": "included_in_sealed_run",
                                                          "partitions": evidence}, indent=2) + "\n")
    checks = {"status": "passed_before_seal", "verification": "verification-results.json",
              "input_identity": "input-verification.json", "event_evidence": "events.manifest.json",
              "focused_tests": "focused-tests.log", "session_and_return_audit": "verification-results.json"}
    (stage / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    artifacts = []
    for path in sorted(stage.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            artifacts.append({"path": str(path.relative_to(stage)), "bytes": path.stat().st_size,
                              "sha256": digest(path)})
    commands = [f".venv/bin/python studies/07_range_xv_edge_candidates/run.py --run-id {args.run_id}",
                f".venv/bin/python studies/07_range_xv_edge_candidates/verify.py --run-id {args.run_id}",
                f".venv/bin/python studies/07_range_xv_edge_candidates/seal.py --run-id {args.run_id}"]
    manifest = {"schema_version": 1, "study_id": study.name, "run_id": args.run_id,
                "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
                "protocol_version": "1.0.1", "protocol_sha256": digest(stage / "protocol-1.0.1.json"),
                "git_revision": revision, "git_status_at_seal": "git-status.txt",
                "source_snapshot": "source-snapshot/", "exact_commands": commands,
                "environment": {"python": platform.python_version(), "platform": platform.platform(),
                                "dependency_lock_sha256": digest(root / "uv.lock")},
                "inputs": "input-verification.json", "exclusions": {"partial_session": "2026-09-08",
                "same_second_completion": "excluded", "cross_session_outcomes": "excluded"},
                "checks": "checks.json", "event_evidence": "events.manifest.json",
                "artifact_hashes": artifacts}
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    dest.parent.mkdir(parents=True, exist_ok=True)
    stage.rename(dest)
    print(dest)


if __name__ == "__main__":
    main()
