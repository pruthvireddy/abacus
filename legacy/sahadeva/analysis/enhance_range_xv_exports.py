from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, time, timedelta
from pathlib import Path


SOURCE_TIMESTAMP_FORMAT = "%Y-%d-%m %H:%M:%S"
ISO_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
SESSION_START = time(18, 0)

EXPORTS = {
    "ESU6-5XV-540.csv": "ESU6_rangexv_5t_20240814_20260908.csv",
    "ESU6-6XV-540.csv": "ESU6_rangexv_6t_20240814_20260908.csv",
    "GCZ6-6XRV-540.csv": "GCZ6_rangexv_6t_20240814_20260908.csv",
    "GCZ6-10XV-540.csv": "GCZ6_rangexv_10t_20240814_20260908.csv",
    "GCZ6-20XV-540.csv": "GCZ6_rangexv_20t_20240814_20260908.csv",
    "NQU6-10XV-540.csv": "NQU6_rangexv_10t_20240814_20260908.csv",
    "NQU6-20XV-540.csv": "NQU6_rangexv_20t_20240814_20260908.csv",
}

OUTPUT_COLUMNS = [
    "source_row",
    "source_timestamp",
    "bar_start_timestamp",
    "bar_completion_timestamp_proxy",
    "bar_duration_seconds_proxy",
    "completion_proxy_status",
    "session_date_proxy",
    "open",
    "high",
    "low",
    "close",
]


def parse_source_row(line: str, source: Path, row_number: int) -> tuple[datetime, list[str]]:
    values = line.rstrip("\r\n").split(";")
    if len(values) != 5:
        raise ValueError(f"{source}:{row_number}: expected 5 fields, found {len(values)}")

    try:
        raw_timestamp = values[0]
        if (
            len(raw_timestamp) != 19
            or raw_timestamp[4] != "-"
            or raw_timestamp[7] != "-"
            or raw_timestamp[10] != " "
            or raw_timestamp[13] != ":"
            or raw_timestamp[16] != ":"
        ):
            raise ValueError
        timestamp = datetime(
            int(raw_timestamp[0:4]),
            int(raw_timestamp[8:10]),
            int(raw_timestamp[5:7]),
            int(raw_timestamp[11:13]),
            int(raw_timestamp[14:16]),
            int(raw_timestamp[17:19]),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{source}:{row_number}: invalid timestamp {values[0]!r}") from exc

    return timestamp, values


def session_date(timestamp: datetime) -> str:
    session_day = timestamp.date()
    if timestamp.time() >= SESSION_START:
        session_day += timedelta(days=1)
    return session_day.isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def enhance(source: Path, destination: Path) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    )
    temp_path = Path(temp_handle.name)

    row_count = 0
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    sessions: set[str] = set()
    statuses: Counter[str] = Counter()

    try:
        writer = csv.writer(temp_handle, delimiter=";", lineterminator="\n")
        writer.writerow(OUTPUT_COLUMNS)

        with source.open("r", encoding="utf-8", newline="") as input_handle:
            current_line = input_handle.readline()
            if not current_line:
                raise ValueError(f"{source}: export is empty")

            current_timestamp, current_values = parse_source_row(current_line, source, 1)
            next_line = input_handle.readline()
            next_row_number = 2

            while True:
                if first_timestamp is None:
                    first_timestamp = current_timestamp
                last_timestamp = current_timestamp
                row_count += 1

                current_session = session_date(current_timestamp)
                sessions.add(current_session)

                if next_line:
                    next_timestamp, next_values = parse_source_row(
                        next_line, source, next_row_number
                    )
                    if next_timestamp < current_timestamp:
                        raise ValueError(
                            f"{source}:{next_row_number}: timestamp regression "
                            f"from {current_timestamp} to {next_timestamp}"
                        )

                    next_session = session_date(next_timestamp)
                    if next_session != current_session:
                        completion_proxy = ""
                        duration_proxy: str | int = ""
                        status = "unavailable_session_boundary"
                    else:
                        completion_proxy = next_timestamp.strftime(ISO_TIMESTAMP_FORMAT)
                        duration_proxy = int((next_timestamp - current_timestamp).total_seconds())
                        status = (
                            "next_bar_start_same_second"
                            if duration_proxy == 0
                            else "next_bar_start_proxy"
                        )
                else:
                    next_timestamp = None
                    next_values = None
                    completion_proxy = ""
                    duration_proxy = ""
                    status = "unavailable_export_end"

                statuses[status] += 1
                writer.writerow(
                    [
                        row_count,
                        current_values[0],
                        current_timestamp.strftime(ISO_TIMESTAMP_FORMAT),
                        completion_proxy,
                        duration_proxy,
                        status,
                        current_session,
                        *current_values[1:],
                    ]
                )

                if next_timestamp is None or next_values is None:
                    break

                current_timestamp = next_timestamp
                current_values = next_values
                next_line = input_handle.readline()
                next_row_number += 1

        temp_handle.flush()
        os.fsync(temp_handle.fileno())
        temp_handle.close()
        os.replace(temp_path, destination)
        destination.chmod(0o644)
    except Exception:
        temp_handle.close()
        temp_path.unlink(missing_ok=True)
        raise

    assert first_timestamp is not None
    assert last_timestamp is not None
    return {
        "source_file": source.name,
        "enhanced_file": destination.name,
        "source_sha256": sha256(source),
        "enhanced_sha256": sha256(destination),
        "rows": row_count,
        "first_bar_start_timestamp": first_timestamp.strftime(ISO_TIMESTAMP_FORMAT),
        "last_bar_start_timestamp": last_timestamp.strftime(ISO_TIMESTAMP_FORMAT),
        "first_session_date_proxy": min(sessions),
        "last_session_date_proxy": max(sessions),
        "session_dates_with_data": len(sessions),
        "completion_proxy_status_counts": dict(sorted(statuses.items())),
    }


def write_manifest(output_dir: Path, results: list[dict[str, object]]) -> Path:
    manifest_path = output_dir / "range_xv_exports_manifest.json"
    payload = {
        "schema_version": 1,
        "chart_type": "ATAS Range XV",
        "source_timestamp_format": SOURCE_TIMESTAMP_FORMAT,
        "enhanced_timestamp_format": ISO_TIMESTAMP_FORMAT,
        "bar_start_timestamp_basis": (
            "The ATAS IndicatorCandle.Time property is documented as candle opening time; "
            "the source export's sole timestamp is interpreted as that property."
        ),
        "bar_completion_timestamp_proxy_basis": (
            "Within the same 18:00-based session, the next bar's opening timestamp is used "
            "as a proxy for the current bar's completion. It is not the omitted ATAS "
            "IndicatorCandle.LastTime value and is limited to one-second precision."
        ),
        "session_date_proxy_basis": (
            "Timestamps at or after 18:00 are assigned to the following date. The export "
            "does not encode timezone or ATAS session configuration."
        ),
        "files": results,
    }

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{manifest_path.name}.",
        suffix=".tmp",
        dir=output_dir,
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, manifest_path)
    manifest_path.chmod(0o644)
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enhance ATAS Range XV OHLC exports with timestamp proxies."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    results: list[dict[str, object]] = []
    for source_name, enhanced_name in EXPORTS.items():
        source = args.data_dir / source_name
        destination = args.data_dir / enhanced_name
        if not source.exists():
            raise FileNotFoundError(source)
        results.append(enhance(source, destination))

    manifest = write_manifest(args.data_dir, results)
    print(json.dumps({"manifest": str(manifest), "files": results}, indent=2))


if __name__ == "__main__":
    main()
