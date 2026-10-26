"""Study-owned execution identities and fresh-stage guards.

This companion protocol is deliberately separate from the bounded root
numerical-test recorder. It retains bytes before scoring and checks those
identities at each phase; it does not claim automatic dependency discovery.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + "\n")


def file_record(path: Path, base: Path | None = None) -> dict:
    return {"path": str(path.relative_to(base)) if base is not None else str(path),
            "bytes": path.stat().st_size, "sha256": sha256(path)}


def verify_record(record: dict, base: Path | None = None) -> Path:
    path = Path(record["path"])
    if base is not None:
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("unsafe relative identity")
        path = base / path
    if not path.is_file() or path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
        raise ValueError(f"identity mismatch: {path}")
    return path


def assert_stage(stage: Path, workspace: Path) -> None:
    expected = workspace.resolve() / "work" / "21_ema_cloud_trend_follow_opportunity"
    if stage.resolve().parent != expected or stage.is_symlink():
        raise ValueError("stage must be a fresh direct study work child")
    if (workspace / "runs" / "21_ema_cloud_trend_follow_opportunity" / stage.name).exists():
        raise ValueError("completed run identity already exists")


def snapshot_sources(stage: Path, workspace: Path, study: Path) -> dict:
    if (stage / "provenance/source-inventory.json").exists():
        raise ValueError("source snapshot already frozen")
    sources = sorted(set(
        list(study.rglob("*.py")) +
        [study / "plan.md", study / "protocol-stage1.md", study / "config-stage1.json",
         study / "reference/manifest.json", study / "reference/ema_cloud_trend_follower_user.pine"] +
        list((workspace / "packages/bhishma/src/abacus_bhishma").glob("*.py")) +
        [workspace / "pyproject.toml", workspace / "packages/bhishma/pyproject.toml",
         workspace / "packages/sahadeva/pyproject.toml", workspace / "scripts/uv",
         workspace / "scripts/unittest_child.py", workspace / "scripts/evidence_contract.py",
         workspace / "scripts/evidence_paths.py", workspace / "scripts/check-evidence-bundle.py",
         workspace / "config/workspace-checks.json"]))
    records = []
    for path in sources:
        relative = path.relative_to(workspace)
        retained = stage / "provenance/source" / relative
        retained.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, retained)
        records.append({"workspace_path": relative.as_posix(),
                        "snapshot_path": retained.relative_to(stage).as_posix(),
                        "bytes": path.stat().st_size, "sha256": sha256(path)})
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=workspace, text=True)
    (stage / "provenance/git-status.txt").write_text(status)
    shutil.copyfile(workspace / "uv.lock", stage / "provenance/uv.lock")
    environment = {"python": sys.version, "executable": sys.executable,
                   "platform": platform.platform(),
                   "packages": sorted({(d.metadata.get("Name", "unknown"), d.version)
                                       for d in importlib.metadata.distributions()}),
                   "lock_identity": file_record(stage / "provenance/uv.lock", stage),
                   "synchronized": False}
    write_json(stage / "provenance/environment.json", environment)
    inventory = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
                 "revision": revision, "dirty": bool(status), "sources": records,
                 "scope": "Study implementation/tests/protocol/Pine and all Bhishma Python source; declared orchestration/contract sources. Installed libraries separately inventoried; automatic executed dependency completeness is not claimed."}
    write_json(stage / "provenance/source-inventory.json", inventory)
    return inventory


def assert_frozen_sources(stage: Path, workspace: Path) -> dict:
    inventory = json.loads((stage / "provenance/source-inventory.json").read_text())
    for record in inventory["sources"]:
        for path in (workspace / record["workspace_path"], stage / record["snapshot_path"]):
            verify_record({"path": str(path), "bytes": record["bytes"], "sha256": record["sha256"]})
    for name, original in (("config.json", "config-stage1.json"), ("protocol.md", "protocol-stage1.md")):
        if sha256(stage / name) != sha256(workspace / "studies/21_ema_cloud_trend_follow_opportunity" / original):
            raise ValueError("frozen protocol/settings mismatch")
    return inventory


def record_command(stage: Path, argv: list[str], cwd: Path, environment: dict | None = None) -> None:
    path = stage / "provenance/commands.json"
    commands = json.loads(path.read_text()) if path.exists() else []
    entry = {"argv": argv, "cwd": str(cwd)}
    if environment:
        entry["environment"] = environment
    commands.append(entry)
    write_json(path, commands)


def assert_numerical_gate(stage: Path) -> None:
    """Require actual passing results bound to this frozen source/input stage."""
    record = json.loads((stage / "provenance/stage1-numerical.json").read_text())
    if record.get("status") != "passed":
        raise ValueError("numerical fixtures did not pass")
    for key in ("source_inventory", "input_lock"):
        verify_record(record[key], stage)
    for item in record["suites"]:
        verify_record(item["result"], stage)
        counts = item["counts"]
        if (item["status"] != "passed" or counts["tests_run"] <= 0 or
                counts["tests_run"] <= counts["skipped"] or counts["failures"] or counts["errors"]):
            raise ValueError("numerical fixtures empty, failed or wholly skipped")
    if {item["name"] for item in record["suites"]} != {"study21", "bhishma-ema"}:
        raise ValueError("required owned numerical suites missing")
