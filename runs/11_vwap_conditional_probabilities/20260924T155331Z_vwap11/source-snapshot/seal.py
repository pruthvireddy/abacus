"""Seal a verified study 11 bundle once, with hashes and source snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shutil
import subprocess

import pyarrow.parquet as pq

from src.features import digest


def command(arguments, cwd):
    return subprocess.check_output(arguments, cwd=cwd, text=True).strip()


def parquet_manifest(stage: Path, folder: str) -> dict:
    partitions = []
    for path in sorted((stage / folder).glob("*.parquet")):
        parquet = pq.ParquetFile(path)
        partitions.append({
            "path": str(path.relative_to(stage)), "rows": parquet.metadata.num_rows,
            "bytes": path.stat().st_size, "sha256": digest(path),
        })
    return {
        "location": folder + "/", "format": "Parquet",
        "retention": "included_in_sealed_run",
        "row_count": sum(item["rows"] for item in partitions),
        "partitions": partitions,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    study = workspace / "studies/11_vwap_conditional_probabilities"
    stage = workspace / "work/11_vwap_conditional_probabilities" / args.run_id
    destination = workspace / "runs/11_vwap_conditional_probabilities" / args.run_id
    if not stage.is_dir() or destination.exists():
        raise FileNotFoundError("stage missing or destination already exists")
    verification = json.loads((stage / "verification-results.json").read_text())
    if verification.get("status") != "passed":
        raise ValueError("verification has not passed")
    events_manifest = parquet_manifest(stage, "events")
    features_manifest = parquet_manifest(stage, "features")
    (stage / "events.manifest.json").write_text(json.dumps(events_manifest, indent=2) + "\n")
    (stage / "features.manifest.json").write_text(json.dumps(features_manifest, indent=2) + "\n")

    snapshot = stage / "source-snapshot"
    if snapshot.exists():
        raise FileExistsError(snapshot)
    snapshot.mkdir()
    files = (
        "README.md", "plan.md", "notes.md", "study.json", "study.yaml",
        "inputs.lock.json", "protocol-1.0.0.json", "protocol-1.0.0.md",
        "pilot.py", "run.py", "summarize.py", "render.py", "verify.py", "seal.py",
    )
    for name in files:
        shutil.copy2(study / name, snapshot / name)
    for folder in ("src", "tests"):
        shutil.copytree(study / folder, snapshot / folder,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    revision = command(["git", "rev-parse", "HEAD"], workspace)
    status = command(["git", "status", "--short"], workspace)
    (stage / "git-status.txt").write_text(status + "\n")
    exact_commands = [
        f".venv/bin/python studies/11_vwap_conditional_probabilities/pilot.py --run-id {args.run_id}",
        f".venv/bin/python studies/11_vwap_conditional_probabilities/run.py --run-id {args.run_id} --workers 3",
        f".venv/bin/python studies/11_vwap_conditional_probabilities/summarize.py --run-id {args.run_id}",
        f".venv/bin/python studies/11_vwap_conditional_probabilities/render.py --run-id {args.run_id}",
        f".venv/bin/python studies/11_vwap_conditional_probabilities/verify.py --run-id {args.run_id}",
        f".venv/bin/python studies/11_vwap_conditional_probabilities/seal.py --run-id {args.run_id}",
    ]
    checks = {
        "status": "passed_before_seal", "verification": "verification-results.json",
        "focused_tests": "focused-tests.log", "independent_recount": "numerical-audit.json",
        "input_identity": "input-verification.json", "denominators": "tables/funnel.csv",
        "report_and_svg_validation": "verification-results.json",
    }
    (stage / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    artifacts = []
    for path in sorted(stage.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            artifacts.append({"path": str(path.relative_to(stage)),
                              "bytes": path.stat().st_size, "sha256": digest(path)})
    manifest = {
        "schema_version": 1, "study_id": "11_vwap_conditional_probabilities",
        "run_id": args.run_id, "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_version": "1.0.0", "protocol_sha256": digest(stage / "protocol-1.0.0.json"),
        "template_version": "2026-09-24", "git_revision": revision,
        "git_status_at_seal": "git-status.txt", "source_snapshot": "source-snapshot/",
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "dependency_lock_sha256": digest(workspace / "uv.lock")},
        "release_id": "session_anchored_vwap__1.0.0",
        "uncertainty": {"unit": "shared_iso_week", "seed": 1111, "repetitions": 400},
        "exact_commands": exact_commands,
        "abandoned_feature_only_runs": ["20260924T154346Z_vwap11"],
        "checks": "checks.json", "input_verification": "input-verification.json",
        "event_evidence": "events.manifest.json", "feature_evidence": "features.manifest.json",
        "artifact_hashes": artifacts,
    }
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage.rename(destination)
    print(destination)


if __name__ == "__main__":
    main()

