#!/usr/bin/env python3
"""Import the seven September 2026 long-history ATAS Range XV exports."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "data/range_xv/20191101_20260924"
EXPORTS = (
    ("ES", 4, "es-4rxv.csv", 1_281_962),
    ("ES", 5, "es-5xrv.csv", 885_222),
    ("ES", 6, "es-6rxv.csv", 647_911),
    ("GC", 6, "gc-6rxv.csv", 1_661_279),
    ("GC", 10, "gc-10rxv.csv", 737_194),
    ("NQ", 10, "nq-10rxv.csv", 4_646_126),
    ("NQ", 20, "nq-20-rxv.csv", 1_343_643),
)
HEADER = (
    b"source_row;source_timestamp;bar_start_timestamp;"
    b"bar_completion_timestamp_proxy;bar_duration_seconds_proxy;"
    b"completion_proxy_status;session_date_proxy;open;high;low;close\n"
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def parse(line: bytes, path: Path, row: int) -> tuple[datetime, list[bytes]]:
    fields = line.rstrip(b"\r\n").split(b";")
    if len(fields) != 5:
        raise ValueError(f"{path}:{row}: expected five columns")
    stamp = fields[0]
    if (
        len(stamp) != 19
        or stamp[4:5] != b"-"
        or stamp[7:8] != b"-"
        or stamp[10:11] != b" "
        or stamp[13:14] != b":"
        or stamp[16:17] != b":"
    ):
        raise ValueError(f"{path}:{row}: invalid timestamp layout")
    try:
        instant = datetime(
            int(stamp[0:4]), int(stamp[8:10]), int(stamp[5:7]),
            int(stamp[11:13]), int(stamp[14:16]), int(stamp[17:19])
        )
    except ValueError as exc:
        raise ValueError(f"{path}:{row}: invalid timestamp") from exc
    return instant, fields


def session_day(instant: datetime) -> date:
    return instant.date() + (timedelta(days=1) if instant.hour >= 18 else timedelta())


def copy_source(download: Path, destination: Path) -> None:
    original_hash = digest(download)
    if destination.exists():
        if digest(destination) != original_hash:
            raise ValueError(f"existing source differs from download: {destination}")
        return
    temporary = destination.with_name(f".{destination.name}.copying")
    if temporary.exists():
        raise FileExistsError(temporary)
    try:
        with download.open("rb") as reader, temporary.open("xb") as writer:
            shutil.copyfileobj(reader, writer, 4 * 1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
        if digest(temporary) != original_hash:
            raise ValueError(f"copy hash differs: {download}")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def enhance(source: Path, destination: Path) -> dict[str, object]:
    if destination.exists():
        raise FileExistsError(destination)
    temporary = destination.with_name(f".{destination.name}.building")
    if temporary.exists():
        raise FileExistsError(temporary)
    rows = 0
    first = last = None
    sessions: set[str] = set()
    statuses: Counter[str] = Counter()
    try:
        with source.open("rb") as reader, temporary.open("xb", buffering=8 * 1024 * 1024) as writer:
            writer.write(HEADER)
            current_line = reader.readline()
            if not current_line:
                raise ValueError(f"empty export: {source}")
            current, fields = parse(current_line, source, 1)
            while True:
                next_line = reader.readline()
                following = next_fields = None
                if next_line:
                    following, next_fields = parse(next_line, source, rows + 2)
                    if following < current:
                        raise ValueError(f"{source}:{rows + 2}: timestamp regression")
                current_session = session_day(current)
                session_text = current_session.isoformat()
                sessions.add(session_text)
                if first is None:
                    first = current
                last = current
                rows += 1
                if following is None:
                    completion = duration = b""
                    status = "unavailable_export_end"
                elif session_day(following) != current_session:
                    completion = duration = b""
                    status = "unavailable_session_boundary"
                else:
                    completion = following.isoformat(sep=" ").encode("ascii")
                    delta = int((following - current).total_seconds())
                    duration = str(delta).encode("ascii")
                    status = "next_bar_start_same_second" if delta == 0 else "next_bar_start_proxy"
                statuses[status] += 1
                writer.write(b";".join((
                    str(rows).encode("ascii"), fields[0], current.isoformat(sep=" ").encode("ascii"),
                    completion, duration, status.encode("ascii"), session_text.encode("ascii"),
                    *fields[1:]
                )) + b"\n")
                if following is None:
                    break
                current, fields = following, next_fields
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    assert first is not None and last is not None
    return {
        "rows": rows,
        "first_bar_start_timestamp": first.isoformat(sep=" "),
        "last_bar_start_timestamp": last.isoformat(sep=" "),
        "first_session_date_proxy": min(sessions),
        "last_session_date_proxy": max(sessions),
        "session_dates_with_data": len(sessions),
        "completion_proxy_status_counts": dict(sorted(statuses.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()
    source_dir = DESTINATION / "source"
    enhanced_dir = DESTINATION / "enhanced"
    manifest_path = DESTINATION / "range_xv_exports_manifest.json"
    tracked_manifest = ROOT / "docs/data/range_xv_long_history_20191101_20260924.json"
    if manifest_path.exists() or tracked_manifest.exists():
        raise FileExistsError("long-history manifest already exists")
    source_dir.mkdir(parents=True, exist_ok=True)
    enhanced_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for product, setting, original_name, expected_rows in EXPORTS:
        name = f"{product}_rangexv_{setting}t_20191101_20260924.csv"
        download = args.source_dir / original_name
        source = source_dir / name
        enhanced = enhanced_dir / name
        copy_source(download, source)
        result = enhance(source, enhanced)
        if (
            result["rows"] != expected_rows
            or result["first_session_date_proxy"] != "2019-11-01"
            or result["last_session_date_proxy"] != "2026-09-24"
        ):
            raise ValueError(f"unexpected coverage: {source}: {result}")
        records.append({
            "product": product,
            "setting_ticks": setting,
            "original_download_name": original_name,
            "source_path": str(source.relative_to(ROOT)),
            "enhanced_path": str(enhanced.relative_to(ROOT)),
            "source_sha256": digest(source),
            "enhanced_sha256": digest(enhanced),
            "source_bytes": source.stat().st_size,
            "enhanced_bytes": enhanced.stat().st_size,
            **result,
        })
        print(f"{product} {setting}: {expected_rows:,} rows", flush=True)
    payload = {
        "schema_version": 1,
        "dataset_id": "atas_range_xv_long_history_20191101_20260924",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_timestamp_format": "%Y-%d-%m %H:%M:%S",
        "enhanced_timestamp_format": "%Y-%m-%d %H:%M:%S",
        "session_date_proxy_basis": "18:00-based inferred session; timezone and configured trading session unverified",
        "completion_proxy_basis": "next bar start within inferred session, not verified exact completion time",
        "import_script": "scripts/import-range-xv-20260924.py",
        "historical_snapshot_manifest": "data/range_xv/range_xv_exports_manifest.json",
        "files": records,
    }
    body = json.dumps(payload, indent=2) + "\n"
    tracked_manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(body)
    tracked_manifest.write_text(body)
    print(manifest_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
