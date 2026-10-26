#!/usr/bin/env python3
"""Verify relocated storage without requiring the original project directories."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

DEFAULT_MANIFEST = "docs/migration/storage-files-20260922.json"
CLOCK_REPAIR = "docs/migration/range-xv-clock-normalization-20260924.json"


def _relative(value: object, label: str, *, allow_dot: bool = False) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"{label} must be a nonempty relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or (not path.parts and not allow_dot):
        raise ValueError(f"{label} must stay within its root: {value!r}")
    return value


def _count(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _records(value: object, label: str) -> list[dict]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{label} must be an array of objects")
    return value


def validate_manifest(value: object) -> dict:
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("Expected storage manifest schema_version 1")
    groups = _records(value.get("groups"), "groups")
    files = _records(value.get("files"), "files")
    by_id = {}
    for group in groups:
        name = group.get("id")
        if not isinstance(name, str) or not name or name in by_id:
            raise ValueError("Group IDs must be unique nonempty strings")
        source = group.get("source_root")
        if not isinstance(source, str) or "\x00" in source or not Path(source).is_absolute():
            raise ValueError(f"Group {name}: source_root must be absolute")
        _relative(group.get("destination_root"), "destination_root", allow_dot=True)
        _count(group.get("files"), "group files")
        _count(group.get("bytes"), "group bytes")
        directories = group.get("directories")
        if not isinstance(directories, list):
            raise ValueError(f"Group {name}: directories must be an array")
        seen_directories = set()
        for directory in directories:
            canonical = str(Path(_relative(directory, "directory", allow_dot=True)))
            if canonical in seen_directories:
                raise ValueError(f"Group {name}: duplicate directory {directory}")
            seen_directories.add(canonical)
        by_id[name] = group
    totals = {name: [0, 0] for name in by_id}
    destinations, sources = set(), set()
    for record in files:
        group_id = record.get("group")
        if not isinstance(group_id, str) or group_id not in by_id:
            raise ValueError("File references an unknown group")
        source = str(Path(_relative(record.get("source_relative"), "source_relative")))
        destination = str(Path(_relative(record.get("destination"), "destination")))
        size = _count(record.get("bytes"), "file bytes")
        digest = record.get("sha256")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"Invalid SHA-256 for {destination}")
        if destination in destinations or (group_id, source) in sources:
            raise ValueError("Duplicate destination or source file record")
        destinations.add(destination)
        sources.add((group_id, source))
        totals[group_id][0] += 1
        totals[group_id][1] += size
    for name, group in by_id.items():
        if totals[name] != [group["files"], group["bytes"]]:
            raise ValueError(f"Group {name}: declared file/byte totals disagree with records")
    if _count(value.get("total_files"), "total_files") != len(files):
        raise ValueError("total_files disagrees with records")
    if _count(value.get("total_bytes"), "total_bytes") != sum(item["bytes"] for item in files):
        raise ValueError("total_bytes disagrees with records")
    seen_links = set()
    for link in _records(value.get("internal_links", []), "internal_links"):
        name = str(Path(_relative(link.get("path"), "link path")))
        target = link.get("target")
        if not isinstance(target, str) or not target or "\x00" in target or Path(target).is_absolute():
            raise ValueError(f"Link {name}: target must be relative")
        if name in seen_links:
            raise ValueError(f"Duplicate internal link: {name}")
        seen_links.add(name)
    return value


def _contained(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("resolved path escapes its root")
    return path


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clock_repair_expectations(root: Path, manifest: dict) -> dict[str, dict]:
    """Apply the approved Range XV byte migration without changing the old inventory."""
    path = root / CLOCK_REPAIR
    if not path.exists():
        return {}
    repair = json.loads(path.read_text(encoding="utf-8"))
    if repair.get("schema_version") != 1 or not isinstance(repair.get("files"), list):
        raise ValueError("invalid Range XV clock migration record")
    historical = {item["destination"]: item for item in manifest["files"]}
    result = {}
    for item in repair["files"]:
        if item.get("collection") != "old":
            continue
        name = _relative(item.get("path"), "clock migration path")
        if not name.startswith("data/range_xv/") or name.count("/") != 2 or name in result:
            raise ValueError(f"unexpected or duplicate Range XV clock migration path: {name}")
        original = historical.get(name)
        if original is None or original["sha256"] != item.get("old_sha256") or original["bytes"] != item.get("old_bytes"):
            raise ValueError(f"historical hash/size disagrees for {name}")
        digest = item.get("enhanced_sha256")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"invalid corrected SHA-256 for {name}")
        result[name] = {"bytes": _count(item.get("enhanced_bytes"), "corrected file bytes"), "sha256": digest}
    if len(result) != 7:
        raise ValueError("expected seven short-history Range XV CSV migrations")
    name = "data/range_xv/range_xv_exports_manifest.json"
    original = historical.get(name)
    hashes = repair.get("new_manifest_sha256")
    if (original is None or original["sha256"] != repair.get("old_manifest_sha256")
            or not isinstance(hashes, dict) or hashes.get("old") != hashes.get("legacy")
            or not isinstance(hashes.get("old"), str)
            or re.fullmatch(r"[0-9a-f]{64}", hashes["old"]) is None):
        raise ValueError("short-history manifest migration does not match historical inventory")
    result[name] = {"bytes": (root / name).stat().st_size, "sha256": hashes["old"]}
    legacy = root / "legacy/sahadeva/data/range_xv_exports_manifest.json"
    if not legacy.is_symlink() or legacy.resolve() != (root / name).resolve():
        raise ValueError("legacy Range XV manifest is not linked to the canonical manifest")
    documentation = repair.get("documentation_changes")
    if not isinstance(documentation, list) or len(documentation) != 1:
        raise ValueError("expected one Range XV documentation migration")
    item = documentation[0]
    name = "data/range_xv/README.md"
    original = historical.get(name)
    if (item.get("path") != name or original is None
            or original["sha256"] != item.get("old_sha256")
            or original["bytes"] != item.get("old_bytes")
            or item.get("legacy_link") != "legacy/sahadeva/data/README.md"):
        raise ValueError("Range XV documentation migration disagrees with historical inventory")
    digest = item.get("new_sha256")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("invalid corrected Range XV README SHA-256")
    result[name] = {"bytes": _count(item.get("new_bytes"), "corrected README bytes"), "sha256": digest}
    legacy = root / item["legacy_link"]
    if not legacy.is_symlink() or legacy.resolve() != (root / name).resolve():
        raise ValueError("legacy Range XV README is not linked to the canonical README")
    return result


def verify(workspace: Path, manifest_path: Path | None = None, verify_sources: bool = False) -> dict:
    root = workspace.resolve()
    manifest_path = manifest_path or Path(DEFAULT_MANIFEST)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "status": "fail",
        "workspace_root": str(root), "manifest": str(manifest_path),
        "verify_sources": verify_sources, "files_checked": 0, "files_verified": 0,
        "bytes_checked": 0, "directories_checked": 0, "internal_links_checked": 0,
        "source_files_checked": 0, "source_bytes_checked": 0,
        "source_inventories_checked": 0, "failures": [],
    }

    def fail(location: str, reason: str) -> None:
        result["failures"].append({"path": location, "reason": reason})

    if not root.is_dir():
        fail(str(root), "workspace root is missing or not a directory")
        return result
    try:
        manifest = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        fail(str(manifest_path), f"invalid manifest: {exc}")
        return result
    result["expected_files"] = manifest["total_files"]
    result["expected_bytes"] = manifest["total_bytes"]
    try:
        clock_expectations = _clock_repair_expectations(root, manifest)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        fail(CLOCK_REPAIR, f"invalid clock migration: {exc}")
        return result
    result["clock_normalized_files"] = len(clock_expectations)
    result["expected_current_bytes"] = sum(clock_expectations.get(item["destination"], item)["bytes"] for item in manifest["files"])
    groups = {group["id"]: group for group in manifest["groups"]}

    def check_file(base: Path, relative: str, record: dict, *, source: bool = False) -> None:
        prefix = "source_" if source else ""
        result[prefix + "files_checked"] += 1
        try:
            path = _contained(base, relative)
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("target is not a regular file")
            digest = _digest(path)
            result[prefix + "bytes_checked"] += info.st_size
            if info.st_size != record["bytes"] or digest != record["sha256"]:
                raise ValueError("size or SHA-256 mismatch")
            if not source:
                result["files_verified"] += 1
        except (OSError, ValueError, RuntimeError) as exc:
            fail(str(base / relative), str(exc))

    for record in manifest["files"]:
        check_file(root, record["destination"], clock_expectations.get(record["destination"], record))
    for group in groups.values():
        directories = {str(Path(".")), *map(str, map(Path, group["directories"]))}
        for relative in sorted(directories):
            name = str(Path(group["destination_root"]) / relative)
            result["directories_checked"] += 1
            try:
                if not _contained(root, name).is_dir():
                    raise ValueError("preserved directory is missing or not a directory")
            except (OSError, ValueError, RuntimeError) as exc:
                fail(name, str(exc))
    for link in manifest.get("internal_links", []):
        result["internal_links_checked"] += 1
        path = root / link["path"]
        try:
            if not path.is_symlink() or os.readlink(path) != link["target"]:
                raise ValueError("relative symlink target differs from manifest")
            if not _contained(root, link["path"]).exists():
                raise ValueError("internal symlink target is missing")
        except (OSError, ValueError, RuntimeError) as exc:
            fail(link["path"], str(exc))
    if verify_sources:
        for group in groups.values():
            try:
                source_root = Path(group["source_root"]).resolve()
            except (OSError, RuntimeError) as exc:
                fail(group["source_root"], str(exc))
                continue
            if not source_root.is_dir():
                fail(str(source_root), "original source root is missing or not a directory")
                continue
            expected = {str(Path(record["source_relative"])) for record in manifest["files"] if record["group"] == group["id"]}
            actual = set()
            def walk_error(exc: OSError) -> None:
                fail(str(source_root), f"source inventory: {exc}")
            for parent, _, names in os.walk(source_root, followlinks=False, onerror=walk_error):
                actual.update(str((Path(parent) / name).relative_to(source_root)) for name in names)
            result["source_inventories_checked"] += 1
            if actual != expected:
                fail(str(source_root), f"source inventory differs: {len(expected - actual)} missing, {len(actual - expected)} extra files")
            for record in manifest["files"]:
                if record["group"] == group["id"]:
                    check_file(source_root, record["source_relative"], record, source=True)
    result["status"] = "fail" if result["failures"] else "pass"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path, default=Path(DEFAULT_MANIFEST))
    parser.add_argument("--verify-sources", action="store_true", help="Also require and verify the original source inventories")
    parser.add_argument("--output", type=Path, help="Optionally save the JSON report")
    args = parser.parse_args(argv)
    result = verify(args.workspace_root, args.manifest, args.verify_sources)
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            result["status"] = "fail"
            result["failures"].append({"path": str(args.output), "reason": f"cannot write report: {exc}"})
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
