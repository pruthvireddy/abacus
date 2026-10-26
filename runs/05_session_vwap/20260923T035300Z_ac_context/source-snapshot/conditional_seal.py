"""Seal a verified version-1.1.0 A/C context run without editing its parent."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import shutil
import subprocess


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    stage = root / "work/05_session_vwap" / args.run_id
    dest = root / "runs/05_session_vwap" / args.run_id
    if not stage.is_dir() or dest.exists():
        raise FileNotFoundError("stage missing or completed run ID already exists")
    required = ["config.json", "inputs.lock.json", "protocol-1.1.0.md",
                "input-verification.json", "parent-verification.json",
                "daily_context.parquet", "atr-cutoffs.json", "opening-balance-cutoffs.json",
                "extraction-summary.json", "context-audit.json", "verification-results.json",
                "events.manifest.json", "metrics.json", "advice.md", "report.md", "report.html",
                "publication.json", "tables/cuts.csv", "tables/ny_early.csv",
                "tables/interactions.csv", "tables/control_comparisons.csv",
                "tables/reentry.csv", "tables/examples.csv",
                "figures/ny-early.svg", "figures/c-peak.svg"]
    for relative in required:
        if not (stage / relative).is_file():
            raise FileNotFoundError(stage / relative)
    if json.loads((stage / "context-audit.json").read_text()).get("status") != "passed":
        raise ValueError("context audit did not pass")
    if json.loads((stage / "verification-results.json").read_text()).get("status") != "passed":
        raise ValueError("verification results did not pass")
    for kind in ("context", "reentry"):
        if len(list((stage / "context").glob(f"{kind}_*.parquet"))) != 23:
            raise ValueError(f"incomplete {kind} evidence")
    study = root / "studies/05_session_vwap"
    snapshot = stage / "source-snapshot"
    snapshot.mkdir()
    for name in ("conditional_run.py", "conditional_audit.py", "conditional_summarize.py",
                 "conditional_seal.py", "protocol-1.1.0.md", "study.yaml", "study.json",
                 "inputs.lock.json", "README.md", "notes.md"):
        shutil.copy2(study / name, snapshot / name)
    shutil.copytree(study / "src", snapshot / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(study / "tests", snapshot / "tests", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    status = subprocess.check_output(["git", "status", "--short"], cwd=root, text=True)
    (stage / "git-status.txt").write_text(status)
    artifacts = []
    for file in sorted(stage.rglob("*")):
        if file.is_file() and file.name != "manifest.json":
            artifacts.append({"path": str(file.relative_to(stage)),
                              "bytes": file.stat().st_size, "sha256": digest(file)})
    parent = root / "runs/05_session_vwap/20260923T015900Z_vwap3/manifest.json"
    manifest = {"schema_version": 1, "study_id": "05_session_vwap",
                "run_id": args.run_id, "protocol_version": "1.1.0",
                "template_version": "2026-09-23",
                "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
                "parent_run_id": "20260923T015900Z_vwap3",
                "parent_manifest_sha256": digest(parent),
                "release_id": "session_anchored_vwap__1.0.0",
                "git_revision": revision, "git_status_at_seal": "git-status.txt",
                "source_snapshot": "source-snapshot/",
                "environment": {"python": platform.python_version(), "platform": platform.platform(),
                                "dependency_lock_sha256": digest(root / "uv.lock")},
                "bootstrap_seed": 310733,
                "exact_commands": [
                    f".venv/bin/python studies/05_session_vwap/conditional_run.py --run-id {args.run_id} --workers 3",
                    f".venv/bin/python studies/05_session_vwap/conditional_audit.py --run-id {args.run_id}",
                    f".venv/bin/python studies/05_session_vwap/conditional_summarize.py --run-id {args.run_id}",
                    ".venv/bin/python -m unittest discover -s studies/05_session_vwap/tests -v",
                    f".venv/bin/python studies/05_session_vwap/conditional_seal.py --run-id {args.run_id}"],
                "checks": "verification-results.json",
                "inputs": "input-verification.json",
                "events": "events.manifest.json",
                "artifact_hashes": artifacts}
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    dest.parent.mkdir(parents=True, exist_ok=True)
    stage.rename(dest)
    print(dest)


if __name__ == "__main__":
    main()
