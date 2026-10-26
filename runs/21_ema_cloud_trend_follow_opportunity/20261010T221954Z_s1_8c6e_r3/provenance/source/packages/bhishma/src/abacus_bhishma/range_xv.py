"""Lossless ATAS OHLC import using the established Range XV research schema.

Export clocks are *inferred* fixed UTC-04:00, not verified ATAS settings.
No bars are removed, no volume is invented, and prices remain source strings.
"""

from __future__ import annotations

from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import os
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo


EXPORT_ZONE = timezone(timedelta(hours=-4))
NEW_YORK = ZoneInfo("America/New_York")
HEADER = (
    b"source_row;source_timestamp;bar_start_timestamp;"
    b"bar_completion_timestamp_proxy;bar_duration_seconds_proxy;"
    b"completion_proxy_status;session_date_proxy;open;high;low;close\n"
)
FLAGS_HEADER = b"source_row;source_timestamp;bar_start_timestamp;flag\n"
SESSIONS_HEADER = (
    b"session_date_proxy;rows;first_source_row;last_source_row;"
    b"first_bar_start_timestamp;last_bar_start_timestamp;export_edge_status\n"
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def session_day(instant: datetime) -> date:
    return instant.date() + (timedelta(days=1) if instant.hour >= 18 else timedelta())


@dataclass(frozen=True)
class SourceBar:
    fields: tuple[bytes, ...]
    export_time: datetime
    new_york_time: datetime
    prices: tuple[Decimal, ...]


def parse_source(line: bytes, path: Path, row: int) -> SourceBar:
    fields = tuple(line.rstrip(b"\r\n").split(b";"))
    if len(fields) != 5:
        raise ValueError(f"{path}:{row}: expected timestamp and four OHLC columns")
    stamp = fields[0]
    if (len(stamp) != 19 or stamp[4:5] != b"-" or stamp[7:8] != b"-"
            or stamp[10:11] != b" " or stamp[13:14] != b":" or stamp[16:17] != b":"):
        raise ValueError(f"{path}:{row}: invalid YYYY-DD-MM timestamp layout")
    try:
        export_time = datetime(
            int(stamp[:4]), int(stamp[8:10]), int(stamp[5:7]),
            int(stamp[11:13]), int(stamp[14:16]), int(stamp[17:19]),
        )
        prices = tuple(Decimal(value.decode("ascii")) for value in fields[1:])
    except (ValueError, InvalidOperation, UnicodeError) as error:
        raise ValueError(f"{path}:{row}: invalid timestamp or OHLC") from error
    if not all(value.is_finite() and value > 0 for value in prices):
        raise ValueError(f"{path}:{row}: nonfinite or nonpositive OHLC")
    opening, high, low, close = prices
    if not low <= min(opening, close) <= max(opening, close) <= high:
        raise ValueError(f"{path}:{row}: invalid OHLC ordering")
    normalized = export_time.replace(tzinfo=EXPORT_ZONE).astimezone(NEW_YORK).replace(tzinfo=None)
    return SourceBar(fields, export_time, normalized, prices)


def _enhanced_rows(source: Path) -> Iterator[tuple[int, SourceBar, bytes, str, int | None]]:
    with source.open("rb", buffering=8 * 1024 * 1024) as stream:
        first_line = stream.readline()
        if not first_line:
            raise ValueError(f"empty export: {source}")
        number = 1
        current = parse_source(first_line, source, number)
        while True:
            next_line = stream.readline()
            following = parse_source(next_line, source, number + 1) if next_line else None
            now = current.new_york_time
            day = session_day(now)
            if following is not None:
                if following.export_time < current.export_time or following.new_york_time < now:
                    raise ValueError(f"{source}:{number + 1}: timestamp regression")
            delta = None
            if following is None:
                completion = duration = b""
                status = "unavailable_export_end"
            elif session_day(following.new_york_time) != day:
                completion = duration = b""
                status = "unavailable_session_boundary"
            else:
                delta = int((following.new_york_time - now).total_seconds())
                completion = following.new_york_time.isoformat(sep=" ").encode("ascii")
                duration = str(delta).encode("ascii")
                status = "next_bar_start_same_second" if delta == 0 else "next_bar_start_proxy"
            line = b";".join((
                str(number).encode("ascii"), current.fields[0], now.isoformat(sep=" ").encode("ascii"),
                completion, duration, status.encode("ascii"), day.isoformat().encode("ascii"),
                *current.fields[1:],
            )) + b"\n"
            yield number, current, line, status, delta
            if following is None:
                break
            current = following
            number += 1


def enhance_range_xv(source: Path, enhanced: Path, flags: Path, sessions: Path) -> dict:
    """Write new files exclusively; preserve every raw row and flag anomalies."""
    outputs = (enhanced, flags, sessions)
    if any(path.exists() for path in outputs):
        raise FileExistsError("enhanced/quality outputs must be new paths")
    created = []
    complete = False
    counts: Counter[str] = Counter()
    flag_counts: Counter[str] = Counter()
    openings: Counter[str] = Counter()
    seasonal_openings: Counter[str] = Counter()
    days: dict[str, dict] = {}
    same_second_records: set[tuple[bytes, ...]] = set()
    previous_stamp = None
    first = last = None
    shifted = long_gaps = 0
    largest_gaps: list[tuple[int, str, str]] = []
    minimum = maximum = None
    rows = 0
    try:
        with ExitStack() as stack:
            writers = []
            for path in outputs:
                path.parent.mkdir(parents=True, exist_ok=True)
                writer = stack.enter_context(path.open("xb", buffering=8 * 1024 * 1024))
                created.append(path)
                writers.append(writer)
            output, flag_output, session_output = writers
            output.write(HEADER)
            flag_output.write(FLAGS_HEADER)
            session_output.write(SESSIONS_HEADER)
            for number, bar, line, status, delta in _enhanced_rows(source):
                output.write(line)
                rows = number
                stamp = bar.new_york_time.isoformat(sep=" ")
                day = session_day(bar.new_york_time).isoformat()
                if first is None:
                    first = bar
                last = bar
                counts[status] += 1
                shifted += int(bar.export_time != bar.new_york_time)
                minimum = bar.prices[2] if minimum is None else min(minimum, bar.prices[2])
                maximum = bar.prices[1] if maximum is None else max(maximum, bar.prices[1])
                if day not in days:
                    days[day] = {"rows": 0, "first_row": number, "first_stamp": stamp}
                    openings[bar.new_york_time.strftime("%H:%M:%S")] += 1
                    seasonal_openings[bar.export_time.strftime("%m %H:%M:%S")] += 1
                days[day].update(rows=days[day]["rows"] + 1, last_row=number, last_stamp=stamp)
                if previous_stamp != bar.export_time:
                    same_second_records.clear()
                row_flags = []
                if bar.fields in same_second_records:
                    row_flags.append("repeated_timestamp_ohlc_record")
                if bar.prices[1] == bar.prices[2]:
                    row_flags.append("zero_range_bar")
                for flag in row_flags:
                    flag_counts[flag] += 1
                    flag_output.write(b";".join((str(number).encode(), bar.fields[0], stamp.encode(), flag.encode())) + b"\n")
                same_second_records.add(bar.fields)
                previous_stamp = bar.export_time
                if delta is not None and delta >= 3600:
                    long_gaps += 1
                    largest_gaps.append((delta, stamp, line.split(b";")[3].decode("ascii")))
                    largest_gaps = sorted(largest_gaps, reverse=True)[:3]
            first_day, last_day = min(days), max(days)
            for day, values in days.items():
                edge = "export_end_session_partial" if day == last_day else (
                    "export_start_session_completeness_unverified" if day == first_day else "observed_session_completeness_unverified"
                )
                session_output.write(
                    f"{day};{values['rows']};{values['first_row']};{values['last_row']};"
                    f"{values['first_stamp']};{values['last_stamp']};{edge}\n".encode("ascii")
                )
            for writer in writers:
                writer.flush()
                os.fsync(writer.fileno())
        complete = True
    finally:
        if not complete:
            for path in created:
                path.unlink(missing_ok=True)
    assert first is not None and last is not None
    return {
        "rows": rows,
        "first_source_timestamp": first.fields[0].decode("ascii"),
        "last_source_timestamp": last.fields[0].decode("ascii"),
        "first_bar_start_timestamp": first.new_york_time.isoformat(sep=" "),
        "last_bar_start_timestamp": last.new_york_time.isoformat(sep=" "),
        "first_session_date_proxy": min(days), "last_session_date_proxy": max(days),
        "session_dates_with_data": len(days), "session_dates": sorted(days),
        "completion_proxy_status_counts": dict(sorted(counts.items())),
        "quality_flag_counts": dict(sorted(flag_counts.items())),
        "winter_rows_shifted": shifted,
        "price_low": str(minimum), "price_high": str(maximum),
        "normalized_session_opening_clock_counts": dict(sorted(openings.items())),
        "source_session_opening_month_clock_counts": dict(sorted(seasonal_openings.items())),
        "same_session_gaps_at_least_one_hour": long_gaps,
        "largest_same_session_gaps": [
            {"seconds": seconds, "from": start, "to": end}
            for seconds, start, end in largest_gaps
        ],
        "validation": {"schema": "pass", "timestamps": "pass", "ohlc": "pass", "row_exclusions": 0},
    }


def verify_enhanced(source: Path, enhanced: Path) -> int:
    """Check every enhanced row against retained source bytes and timing rules."""
    rows = 0
    with enhanced.open("rb", buffering=8 * 1024 * 1024) as stream:
        if stream.readline() != HEADER:
            raise ValueError(f"unexpected enhanced header: {enhanced}")
        for number, _, expected, _, _ in _enhanced_rows(source):
            if stream.readline() != expected:
                raise ValueError(f"enhanced/source or derived-label mismatch: {enhanced}:{number}")
            rows = number
        if stream.read(1):
            raise ValueError(f"extra enhanced rows: {enhanced}")
    return rows
