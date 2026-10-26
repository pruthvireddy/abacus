#!/usr/bin/env python3
"""Normalize historical ATAS Range XV enhanced CSV clocks in place, with audit.

The export clock is inferred to be a fixed UTC-04:00 offset. `source_timestamp`
remains verbatim; the three derived timestamp/session columns become New York
wall time. Use prepare then apply so no original file changes before validation.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
OLD_MANIFEST = Path("data/range_xv/range_xv_exports_manifest.json")
LEGACY_MANIFEST = Path("legacy/sahadeva/data/range_xv_exports_manifest.json")
LONG_MANIFEST = Path("data/range_xv/20191101_20260924/range_xv_exports_manifest.json")
TRACKED_LONG_MANIFEST = Path("docs/data/range_xv_long_history_20191101_20260924.json")
MIGRATION_RECORD = Path("docs/migration/range-xv-clock-normalization-20260924.json")
EXPORT_ZONE = timezone(timedelta(hours=-4))
NEW_YORK = ZoneInfo("America/New_York")
HEADER = b"source_row;source_timestamp;bar_start_timestamp;bar_completion_timestamp_proxy;bar_duration_seconds_proxy;completion_proxy_status;session_date_proxy;open;high;low;close\n"


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_stamp(export_stamp: bytes) -> datetime:
    instant = datetime.fromisoformat(export_stamp.decode("ascii"))
    return instant.replace(tzinfo=EXPORT_ZONE).astimezone(NEW_YORK).replace(tzinfo=None)


def session_day(instant: datetime) -> date:
    return instant.date() + (timedelta(days=1) if instant.hour >= 18 else timedelta())


def record_path(record: dict) -> Path:
    return Path(record.get("enhanced_path") or "data/range_xv/" + record["enhanced_file"])


def parse_row(line: bytes, path: Path, number: int) -> list[bytes]:
    fields = line.rstrip(b"\r\n").split(b";")
    if len(fields) != 11 or int(fields[0]) != number:
        raise ValueError(f"{path}:{number}: invalid schema or row order")
    return fields


def normalize_file(source: Path, destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    rows = 0
    first = last = previous = None
    sessions = set()
    statuses: Counter[str] = Counter()
    openings: Counter[str] = Counter()
    shifted = changed_session = changed_status = 0
    with source.open("rb", buffering=8 * 1024 * 1024) as reader, destination.open("xb", buffering=8 * 1024 * 1024) as writer:
        if reader.readline() != HEADER:
            raise ValueError(f"unexpected header: {source}")
        writer.write(HEADER)
        current_line = reader.readline()
        if not current_line:
            raise ValueError(f"empty file: {source}")
        current = parse_row(current_line, source, 1)
        while True:
            following_line = reader.readline()
            following = parse_row(following_line, source, rows + 2) if following_line else None
            raw = datetime.fromisoformat(current[2].decode("ascii"))
            now = canonical_stamp(current[2])
            after = canonical_stamp(following[2]) if following is not None else None
            if previous is not None and now < previous:
                raise ValueError(f"normalized time regresses: {source}:{rows + 1}")
            previous = now
            day = session_day(now).isoformat()
            if day not in sessions:
                openings[now.strftime("%H:%M:%S")] += 1
                sessions.add(day)
            if day != current[6].decode("ascii"):
                changed_session += 1
            if now != raw:
                shifted += 1
            if first is None:
                first = now
            last = now
            if after is None:
                completion, duration, status = b"", b"", "unavailable_export_end"
            elif session_day(after).isoformat() != day:
                completion, duration, status = b"", b"", "unavailable_session_boundary"
            else:
                seconds = int((after - now).total_seconds())
                if seconds < 0:
                    raise ValueError(f"negative duration: {source}:{rows + 1}")
                completion = after.isoformat(sep=" ").encode("ascii")
                duration = str(seconds).encode("ascii")
                status = "next_bar_start_same_second" if seconds == 0 else "next_bar_start_proxy"
            if status.encode("ascii") != current[5]:
                changed_status += 1
            statuses[status] += 1
            writer.write(b";".join((current[0], current[1], now.isoformat(sep=" ").encode("ascii"),
                                    completion, duration, status.encode("ascii"), day.encode("ascii"),
                                    *current[7:])) + b"\n")
            rows += 1
            if following is None:
                break
            current = following
        writer.flush()
        os.fsync(writer.fileno())
    if changed_session or changed_status:
        raise ValueError(f"session/status identity changed for {source}: {changed_session}/{changed_status}")
    assert first is not None and last is not None
    return {"rows": rows, "first_bar_start_timestamp": first.isoformat(sep=" "),
            "last_bar_start_timestamp": last.isoformat(sep=" "),
            "first_session_date_proxy": min(sessions), "last_session_date_proxy": max(sessions),
            "session_dates_with_data": len(sessions),
            "completion_proxy_status_counts": dict(sorted(statuses.items())),
            "winter_rows_shifted": shifted, "changed_session_dates": changed_session,
            "changed_completion_statuses": changed_status,
            "opening_clock_counts": dict(sorted(openings.items())),
            "enhanced_sha256": digest(destination), "enhanced_bytes": destination.stat().st_size}


def expected_records() -> tuple[dict, dict, list[dict]]:
    old = json.loads((ROOT / OLD_MANIFEST).read_text())
    long = json.loads((ROOT / LONG_MANIFEST).read_text())
    if old.get("timestamp_normalization") or long.get("timestamp_normalization"):
        raise ValueError("dataset already clock-normalized")
    if (ROOT / LEGACY_MANIFEST).read_bytes() != (ROOT / OLD_MANIFEST).read_bytes():
        raise ValueError("legacy and physical short-history manifests differ")
    if (ROOT / TRACKED_LONG_MANIFEST).read_bytes() != (ROOT / LONG_MANIFEST).read_bytes():
        raise ValueError("tracked and physical long-history manifests differ")
    records = [("old", item) for item in old["files"]] + [("long", item) for item in long["files"]]
    return old, long, records


def prepare(stage: Path) -> None:
    if stage.exists() or (ROOT / MIGRATION_RECORD).exists():
        raise FileExistsError("stage or migration record already exists")
    old, long, records = expected_records()
    stage.mkdir(parents=True)
    old_manifest_hash = digest(ROOT / OLD_MANIFEST)
    long_manifest_hash = digest(ROOT / LONG_MANIFEST)
    transformed = []
    for collection, record in records:
        relative = record_path(record)
        source = ROOT / relative
        old_hash = record["enhanced_sha256"]
        if digest(source) != old_hash or source.stat().st_size != record.get("enhanced_bytes", source.stat().st_size):
            raise ValueError(f"input does not match pinned manifest: {relative}")
        destination = stage / "files" / relative
        result = normalize_file(source, destination)
        if result["rows"] != record["rows"] or result["session_dates_with_data"] != record["session_dates_with_data"]:
            raise ValueError(f"coverage changed: {relative}")
        if result["completion_proxy_status_counts"] != record["completion_proxy_status_counts"]:
            raise ValueError(f"completion categories changed: {relative}")
        transformed.append({"collection": collection, "path": str(relative),
                            "old_sha256": old_hash, "old_bytes": source.stat().st_size, **result})
        print(f"prepared {relative}: {result['rows']:,} rows; {result['winter_rows_shifted']:,} shifted", flush=True)
    plan = {"schema_version": 1, "old_manifest_sha256": old_manifest_hash,
            "legacy_manifest_sha256": digest(ROOT / LEGACY_MANIFEST),
            "long_manifest_sha256": long_manifest_hash,
            "conversion": "Interpret raw export-clock timestamps as fixed UTC-04:00; convert to America/New_York wall time",
            "timezone_status": "inferred_from_session_open_Dst_pattern_not_ATAS_configuration_verified",
            "files": transformed}
    (stage / "prepared.json").write_text(json.dumps(plan, indent=2) + "\n")


def apply(stage: Path) -> None:
    plan = json.loads((stage / "prepared.json").read_text())
    if (ROOT / MIGRATION_RECORD).exists():
        raise FileExistsError(ROOT / MIGRATION_RECORD)
    old, long, _ = expected_records()
    if (digest(ROOT / OLD_MANIFEST) != plan["old_manifest_sha256"]
            or digest(ROOT / LEGACY_MANIFEST) != plan["legacy_manifest_sha256"]
            or digest(ROOT / LONG_MANIFEST) != plan["long_manifest_sha256"]):
        raise ValueError("manifests changed after preparation")
    for item in plan["files"]:
        target = ROOT / item["path"]
        staged = stage / "files" / item["path"]
        if digest(target) != item["old_sha256"] or digest(staged) != item["enhanced_sha256"]:
            raise ValueError(f"input or staged output changed: {item['path']}")
    for item in plan["files"]:
        os.replace(stage / "files" / item["path"], ROOT / item["path"])
    timestamp = datetime.now(timezone.utc).isoformat()
    normalization = {"source_export_clock_assumption": "fixed_UTC_minus_04:00",
                     "canonical_timestamp_zone": "America/New_York",
                     "timezone_status": plan["timezone_status"],
                     "source_timestamp_column": "verbatim_ATAS_export_clock",
                     "bar_start_timestamp_column": "converted_New_York_wall_time",
                     "applied_at_utc": timestamp, "migration_record": str(MIGRATION_RECORD),
                     "script": "scripts/normalize-range-xv-clock.py"}
    for collection, manifest, target in (("old", old, OLD_MANIFEST), ("long", long, LONG_MANIFEST)):
        for record in manifest["files"]:
            item = next(x for x in plan["files"] if x["collection"] == collection and x["path"] == str(record_path(record)))
            for key in ("enhanced_sha256", "enhanced_bytes", "first_bar_start_timestamp", "last_bar_start_timestamp",
                        "first_session_date_proxy", "last_session_date_proxy", "session_dates_with_data",
                        "completion_proxy_status_counts"):
                record[key] = item[key]
            record["winter_rows_shifted"] = item["winter_rows_shifted"]
        manifest["schema_version"] = 2
        manifest["timestamp_normalization"] = normalization
        manifest["enhanced_timestamp_format"] = "%Y-%m-%d %H:%M:%S America/New_York wall time"
        manifest["session_date_proxy_basis"] = "18:00 America/New_York wall-time boundary after inferred fixed-UTC-04 export-clock conversion"
        manifest["bar_completion_timestamp_proxy_basis"] = "next bar's normalized New York opening time within the same inferred session; not exact completion"
        if "completion_proxy_basis" in manifest:
            manifest["completion_proxy_basis"] = manifest["bar_completion_timestamp_proxy_basis"]
        manifest["bar_start_timestamp_basis"] = "ATAS opening timestamp converted from inferred fixed UTC-04 export clock to America/New_York wall time"
        body = json.dumps(manifest, indent=2) + "\n"
        target_path = ROOT / target
        temp = target_path.with_name("." + target_path.name + ".clock-normalized")
        temp.write_text(body)
        os.replace(temp, target_path)
        if collection == "old":
            legacy = ROOT / LEGACY_MANIFEST
            legacy_temp = legacy.with_name("." + legacy.name + ".clock-normalized")
            legacy_temp.symlink_to("../../../data/range_xv/range_xv_exports_manifest.json")
            os.replace(legacy_temp, legacy)
        if collection == "long":
            tracked = ROOT / TRACKED_LONG_MANIFEST
            tracked_temp = tracked.with_name("." + tracked.name + ".clock-normalized")
            tracked_temp.write_text(body)
            os.replace(tracked_temp, tracked)
    plan["applied_at_utc"] = timestamp
    plan["new_manifest_sha256"] = {"old": digest(ROOT / OLD_MANIFEST),
                                   "legacy": digest(ROOT / LEGACY_MANIFEST),
                                   "long": digest(ROOT / LONG_MANIFEST)}
    migration = ROOT / MIGRATION_RECORD
    migration.parent.mkdir(parents=True, exist_ok=True)
    migration.write_text(json.dumps(plan, indent=2) + "\n")
    print(migration)


def verify() -> None:
    migration = json.loads((ROOT / MIGRATION_RECORD).read_text())
    manifests = {
        "old": json.loads((ROOT / OLD_MANIFEST).read_text()),
        "long": json.loads((ROOT / LONG_MANIFEST).read_text()),
    }
    for collection, path in (("old", OLD_MANIFEST), ("long", LONG_MANIFEST)):
        manifest = manifests[collection]
        if manifest["schema_version"] != 2 or digest(ROOT / path) != migration["new_manifest_sha256"][collection]:
            raise ValueError(f"incorrect current manifest: {path}")
    if (ROOT / TRACKED_LONG_MANIFEST).read_bytes() != (ROOT / LONG_MANIFEST).read_bytes():
        raise ValueError("long-history manifest mirror differs")
    for alias, target in ((LEGACY_MANIFEST, OLD_MANIFEST),
                          (Path("legacy/sahadeva/data/README.md"), Path("data/range_xv/README.md"))):
        link = ROOT / alias
        if not link.is_symlink() or link.resolve() != (ROOT / target).resolve():
            raise ValueError(f"legacy link differs: {alias}")
    documentation = migration["documentation_changes"]
    if len(documentation) != 1 or documentation[0]["path"] != "data/range_xv/README.md":
        raise ValueError("unexpected Range XV documentation migration")
    readme = ROOT / documentation[0]["path"]
    if digest(readme) != documentation[0]["new_sha256"] or readme.stat().st_size != documentation[0]["new_bytes"]:
        raise ValueError("Range XV README differs from migration record")
    files = migration["files"]
    if len(files) != 14 or len({item["path"] for item in files}) != 14:
        raise ValueError("migration must cover 14 unique enhanced files")
    for item in files:
        record = next((record for record in manifests[item["collection"]]["files"]
                       if str(record_path(record)) == item["path"]), None)
        if record is None:
            raise ValueError(f"file absent from current manifest: {item['path']}")
        path = ROOT / item["path"]
        if (digest(path) != item["enhanced_sha256"]
                or path.stat().st_size != item["enhanced_bytes"]
                or record["enhanced_sha256"] != item["enhanced_sha256"]
                or record["rows"] != item["rows"]):
            raise ValueError(f"current enhanced file differs: {path}")
        if "source_path" in record and digest(ROOT / record["source_path"]) != record["source_sha256"]:
            raise ValueError(f"source export differs: {record['source_path']}")
    print(json.dumps({"status": "pass", "files": len(files),
                      "rows": sum(item["rows"] for item in files),
                      "winter_rows_shifted": sum(item["winter_rows_shifted"] for item in files)}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "apply", "verify"))
    parser.add_argument("--stage", type=Path)
    args = parser.parse_args()
    if args.mode == "verify":
        verify()
        return
    if args.stage is None:
        parser.error("--stage is required for prepare and apply")
    stage = args.stage.resolve()
    if not stage.is_relative_to((ROOT / "work").resolve()):
        raise ValueError("stage must be under work/")
    if args.mode == "prepare":
        prepare(stage)
    else:
        apply(stage)


if __name__ == "__main__":
    main()
