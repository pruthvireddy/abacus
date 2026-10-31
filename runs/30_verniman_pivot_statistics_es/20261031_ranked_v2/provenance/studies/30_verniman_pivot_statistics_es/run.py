#!/usr/bin/env python3
"""Phase 1 source/identity audit; deliberately no market-outcome command."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

STUDY_ID = "30_verniman_pivot_statistics_es"
STUDY = Path(__file__).resolve().parent
WORKSPACE = STUDY.parents[1]
sys.path.insert(0, str(STUDY / "src"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def csv_bytes(rows: list[dict]) -> bytes:
    columns = sorted({key for row in rows for key in row})
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
                         for key, value in row.items()})
    return output.getvalue().encode("utf-8")


def stage_for_run(run_id: str, workspace: Path = WORKSPACE) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", run_id):
        raise ValueError("run ID must contain only letters, digits, underscores or hyphens")
    parent = workspace.resolve() / "work" / STUDY_ID
    stage = parent / run_id
    if not stage.resolve().is_relative_to(workspace.resolve() / "work"):
        raise ValueError("audit stage escapes workspace work directory")
    if stage.exists() or stage.is_symlink():
        raise FileExistsError("audit stage already exists; choose a fresh run ID")
    return stage


def provenance(stage: Path) -> list[dict]:
    paths = [STUDY / "run.py", STUDY / "inputs.lock.json", STUDY / "study.yaml",
             STUDY / "plan.md", STUDY / "protocol-1.0.0.md", STUDY / "statistics.md",
             WORKSPACE / "uv.lock",
             WORKSPACE / "requests/inbox/es_contract_session_indicators__1.0.0.yaml"]
    paths.extend(WORKSPACE / "packages/bhishma/src/abacus_bhishma" / name for name in
                 ("calendar.py", "paths.py", "provenance.py", "publication_safety.py", "verniman_consolidated.py"))
    paths.extend(sorted((STUDY / "src").glob("*.py")))
    paths.extend(sorted((STUDY / "tests").glob("test*.py")))
    records = []
    for path in paths:
        relative = path.relative_to(WORKSPACE)
        destination = stage / "provenance" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        records.append({"path": relative.as_posix(), "retained_path": destination.relative_to(stage).as_posix(),
                        "sha256": sha256(path), "bytes": path.stat().st_size})
    return records


def git_state() -> dict:
    def read(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=WORKSPACE, capture_output=True, text=True, check=True)
        return result.stdout
    return {"head": read("rev-parse", "HEAD").strip(), "status_porcelain": read("status", "--porcelain=v1"),
            "qualification": "Declared executed/audit sources retained; this is not complete dependency discovery."}


def audit(run_id: str, publication_root: str | None = None) -> Path:
    from abacus_bhishma.paths import resolve_publication_root
    from abacus_bhishma.verniman_consolidated import load_release
    from data_requirements import build_contract_windows, inspect_continuous_coverage
    from source_audit import audit_sources

    lock = json.loads((STUDY / "inputs.lock.json").read_text())
    root = resolve_publication_root(publication_root, workspace=WORKSPACE)
    for pin in lock["inputs"].values():
        path = (root / pin["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or path.stat().st_size != pin["bytes"] or sha256(path) != pin["sha256"]:
            raise ValueError("pinned input catalog bytes do not match")
    stage = stage_for_run(run_id)
    stage.mkdir(parents=True, exist_ok=False)
    sources = provenance(stage)
    settings = lock["requested_interval"]
    start, end = settings["start_date"], settings["end_date"]
    level_pin = lock["inputs"]["verniman_daily_levels"]
    continuous_pin = lock["inputs"]["retained_continuous_minutes"]
    tables = {}
    for name in ("outlooks", "levels", "issues", "coverage", "observations", "observation_levels"):
        tables[name] = load_release(root, level_pin["path"], level_pin["sha256"], table=name).to_pylist()
    source_audit = audit_sources(**tables, start_date=start, end_date=end)
    retained = inspect_continuous_coverage(
        root, continuous_pin["path"], continuous_pin["sha256"],
        start_date=lock["retained_inventory_start"], end_date=lock["requested_interval"]["end_exclusive"],
    )
    # Source review candidates are included in acquisition planning; this does
    # not promote them to scientific eligibility or pick a duplicate revision.
    candidates = [{"session_date": row["session_date"], "full_contract": row["normalized_contract"],
                   "candidate_id": row["candidate_id"]}
                  for row in source_audit["outlook_audit"]
                  if row["in_requested_range"] and row["source_shape"] == "single_shared_trigger"]
    requirements = build_contract_windows(candidates, retained, prior_full_sessions=5)
    payloads = {"source-audit.json": source_audit, "retained-coverage.json": retained,
                "data-requirements.json": requirements}
    for name, value in payloads.items():
        save_json(stage / name, value)
    csvs = {"source-audit.csv": source_audit["outlook_audit"],
            "calendar-audit.csv": source_audit["calendar_audit"],
            "observation-audit.csv": source_audit["observation_audit"],
            "observation-level-audit.csv": source_audit["observation_level_audit"],
            "candidate-requirements.csv": requirements["candidate_requirements"]}
    for name, rows in csvs.items():
        (stage / name).write_bytes(csv_bytes(rows))
    save_json(stage / "costing.json", {
        "status": "not_applicable_repository_only", "estimated_cost_usd": None, "paid_order_authorized": False,
        "approved_max_cost_usd": None,
        "reason": "User requested repository-only inputs; no external quote, purchase or data extension is required or authorized.",
        "provider": "Databento", "dataset": "GLBX.MDP3", "schema": "ohlcv-1m",
        "scope_artifact": "data-requirements.json",
        "prerequisites": [],
        "documentation": "https://databento.com/docs/api-historical/metadata/metadata-get-cost?lang=python",
    })
    for record in sources:
        if sha256(WORKSPACE / record["path"]) != record["sha256"]:
            raise RuntimeError("an audit source changed during execution; stage remains incomplete")
    files = [path for path in sorted(stage.rglob("*")) if path.is_file()]
    manifest = {
        "schema_version": "abacus.study30.phase1-inventory/v1", "study_id": STUDY_ID,
        "run_id": run_id, "phase": "source_and_input_identity_inventory",
        "status": "inventory_completed_repository_only_source_review_pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requested_interval": settings, "publication_root": str(root),
        "commands": {"argv": sys.argv, "cwd": str(Path.cwd())},
        "environment": {"python": sys.version, "executable": sys.executable,
                        "platform": platform.platform(), "environment_lock_sha256": sha256(WORKSPACE / "uv.lock")},
        "git": git_state(), "sources": sources,
        "input_identities": lock["inputs"],
        "artifacts": [{"path": path.relative_to(stage).as_posix(), "sha256": sha256(path),
                       "bytes": path.stat().st_size} for path in files],
        "market_outcomes_computed": False, "features_published": False,
        "paid_requests_submitted": False, "sealed_research_run": False,
    }
    save_json(stage / "audit-manifest.json", manifest)
    verify_audit(stage)
    return stage


def verify_audit(stage: Path) -> dict:
    """Reconcile retained inventory accounting/CSV bytes, not research results."""
    stage = stage.resolve()
    manifest = json.loads((stage / "audit-manifest.json").read_text())
    if manifest.get("schema_version") != "abacus.study30.phase1-inventory/v1" or manifest.get("study_id") != STUDY_ID:
        raise ValueError("unsupported audit manifest identity")
    names = set()
    for record in manifest["artifacts"]:
        relative = Path(record["path"])
        path = stage / relative
        if relative.is_absolute() or ".." in relative.parts or record["path"] in names or not path.resolve().is_relative_to(stage):
            raise ValueError("unsafe or duplicate artifact path")
        names.add(record["path"])
        if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            raise ValueError(f"audit artifact mismatch: {record['path']}")
    required = {"source-audit.json", "retained-coverage.json", "data-requirements.json", "costing.json",
                "source-audit.csv", "calendar-audit.csv", "observation-audit.csv",
                "observation-level-audit.csv", "candidate-requirements.csv"}
    if not required.issubset(names):
        raise ValueError("incomplete audit artifact inventory")
    for record in manifest["sources"]:
        if record["retained_path"] not in names or sha256(stage / record["retained_path"]) != record["sha256"]:
            raise ValueError("retained audit source mismatch")
    source = json.loads((stage / "source-audit.json").read_text())
    requirements = json.loads((stage / "data-requirements.json").read_text())
    summary = source["summary"]
    if len(source["outlook_audit"]) != summary["canonical_outlook_rows_input"]:
        raise ValueError("canonical outlook accounting mismatch")
    if sum(row["source_level_row_count"] for row in source["outlook_audit"]) != summary["canonical_level_rows_input"]:
        raise ValueError("canonical level accounting mismatch")
    selected = [row for row in source["outlook_audit"] if row["in_requested_range"]]
    if len(selected) != summary["canonical_outlook_rows_in_range"]:
        raise ValueError("requested source range accounting mismatch")
    interval = source["requested_interval"]
    if any(interval.get(key) != manifest["requested_interval"].get(key) for key in ("start_date", "end_date", "end_inclusive")):
        raise ValueError("manifest/source requested interval mismatch")
    first_date, last_date = date.fromisoformat(interval["start_date"]), date.fromisoformat(interval["end_date"])
    expected_dates = (last_date - first_date).days + 1
    days = source["calendar_audit"]
    if expected_dates <= 0 or [row["session_date"] for row in days] != [(first_date + timedelta(days=n)).isoformat() for n in range(expected_dates)]:
        raise ValueError("calendar accounting mismatch")
    for row in source["outlook_audit"]:
        actually_selected = row["session_date"] is not None and interval["start_date"] <= row["session_date"] <= interval["end_date"]
        if row["in_requested_range"] is not actually_selected:
            raise ValueError("outlook interval membership mismatch")
        if row["point_in_time_eligible"] is not False:
            raise ValueError("Phase 1 must not assert verified historical timing eligibility")
    outlooks_by_day = {}
    for row in selected:
        outlooks_by_day.setdefault(row["session_date"], []).append(row["outlook_id"])
    observations_by_day = Counter(row["session_date"] for row in source["observation_audit"])
    for row in days:
        identities = sorted(outlooks_by_day.get(row["session_date"], []))
        if (row["canonical_outlook_ids"] != identities or row["canonical_outlook_count"] != len(identities)
                or row["duplicate_date"] is not (len(identities) > 1)
                or row["user_observation_count"] != observations_by_day[row["session_date"]]):
            raise ValueError("calendar source-record accounting mismatch")
    counts = lambda rows, key: dict(sorted(Counter(str(row.get(key)) for row in rows).items()))
    expected_summary = {
        "canonical_outlook_rows_accounted": len(source["outlook_audit"]),
        "canonical_outlook_rows_undated": sum(row["session_date"] is None for row in source["outlook_audit"]),
        "canonical_level_rows_accounted": sum(row["source_level_row_count"] for row in source["outlook_audit"]),
        "calendar_dates_accounted": len(days),
        "source_shapes_in_range": counts(selected, "source_shape"),
        "source_dispositions_in_range": counts(selected, "source_only_disposition"),
        "calendar_dispositions": counts(days, "source_only_disposition"),
        "duplicate_dates_in_range": sum(row["duplicate_date"] for row in days),
        "normalized_contract_outlooks_in_range": sum(row["normalized_contract"] is not None for row in selected),
        "null_available_at_outlooks_in_range": sum(row["null_available_at"] for row in selected),
        "point_in_time_eligible_outlooks": sum(bool(row["point_in_time_eligible"]) for row in selected),
        "user_observation_rows_accounted": len(source["observation_audit"]),
        "user_observation_level_rows_accounted": len(source["observation_level_audit"]),
        "user_observation_basis_counts": counts(source["observation_audit"], "source_evidence_basis"),
    }
    if any(summary.get(key) != value for key, value in expected_summary.items()):
        raise ValueError("source summary accounting mismatch")
    expected_candidates = {row["candidate_id"] for row in selected if row["source_shape"] == "single_shared_trigger"}
    actual_candidates = [row["candidate_id"] for row in requirements["candidate_requirements"]]
    if set(actual_candidates) != expected_candidates or len(actual_candidates) != len(expected_candidates):
        raise ValueError("data-request candidate accounting mismatch")
    sources_by_id = {row["candidate_id"]: row for row in selected}
    for row in requirements["candidate_requirements"]:
        original = sources_by_id[row["candidate_id"]]
        if row["session_date"] != original["session_date"] or row["full_contract"] != original["normalized_contract"]:
            raise ValueError("data-request candidate date/contract mismatch")
    expected_requirement_summary = {
        "candidates": len(actual_candidates),
        "candidate_status_counts": counts(requirements["candidate_requirements"], "status"),
        "contract_windows": len(requirements["contract_windows"]),
        "windows_requiring_acquisition_or_review": sum(row["requires_acquisition_or_review"] for row in requirements["contract_windows"]),
    }
    if requirements["summary"] != expected_requirement_summary:
        raise ValueError("data-requirement summary accounting mismatch")
    pairs = [("source-audit.csv", source["outlook_audit"]), ("calendar-audit.csv", days),
             ("observation-audit.csv", source["observation_audit"]),
             ("observation-level-audit.csv", source["observation_level_audit"]),
             ("candidate-requirements.csv", requirements["candidate_requirements"])]
    for name, rows in pairs:
        if (stage / name).read_bytes() != csv_bytes(rows):
            raise ValueError(f"CSV/JSON projection mismatch: {name}")
    if any(manifest.get(key) is not False for key in ("market_outcomes_computed", "features_published", "paid_requests_submitted", "sealed_research_run")):
        raise ValueError("Phase 1 inventory must not assert outcome execution, acquisition or sealing")
    return {"status": "passed", "scope": "inventory_bytes_accounting_and_projection_only",
            "artifact_count": len(names), "outlooks_accounted": len(source["outlook_audit"]),
            "calendar_dates_accounted": len(days), "data_candidates_accounted": len(actual_candidates)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("audit", help="Create a fresh source/identity-only inventory stage.")
    run.add_argument("--run-id", required=True)
    run.add_argument("--publication-root")
    verify = commands.add_parser("verify-audit", help="Read-only retained inventory verification.")
    verify.add_argument("--stage", type=Path, required=True)
    features = commands.add_parser("prepare-features", help="Publish new indicators from retained prebuilt inputs only.")
    features.add_argument("--release-id", required=True)
    frozen = commands.add_parser("freeze", help="Freeze sources, source selection and numerical tests before outcomes.")
    frozen.add_argument("--run-id", required=True)
    for command in ("execute", "render", "verify", "seal"):
        item = commands.add_parser(command)
        item.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "audit":
        stage = audit(args.run_id, args.publication_root)
        print(json.dumps({"stage": str(stage), "verification": verify_audit(stage)}, sort_keys=True))
    elif args.command == "verify-audit":
        print(json.dumps(verify_audit(args.stage), sort_keys=True))
    else:
        import lifecycle
        if args.command == "prepare-features":
            result = lifecycle.prepare_features(args.release_id)
        elif args.command == "freeze":
            result = lifecycle.freeze_run(args.run_id)
        elif args.command == "verify":
            import verify_saved
            result = verify_saved.verify(args.stage)
        else:
            result = getattr(lifecycle, args.command)(args.stage)
        print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
