"""Study-local reporting groups; no market-data loading or statistics.

The authoritative ``study.yaml`` uses JSON syntax, a YAML 1.2 subset, so these
settings can be read with the standard library. Timestamps must already be
normalized naive New York wall time. The caller supplies the retained input's
``session_date_proxy``; this module does not infer or validate that trading date.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
import json
from pathlib import Path
import re
from typing import Sequence


_GROUPS = frozenset({"sessions", "subwindows"})
_CLOCK_PATTERN = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]")


def _nonempty_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be nonempty text without outer whitespace")
    return value


@dataclass(frozen=True, slots=True)
class Timeframe:
    """An independent daily window with inclusive start and exclusive end."""

    id: str
    label: str
    group: str
    start: time
    end: time

    def __post_init__(self) -> None:
        _nonempty_text(self.id, "timeframe id")
        _nonempty_text(self.label, "timeframe label")
        if self.id == "all_hours":
            raise ValueError("all_hours is reserved for the complete sample")
        if self.group not in _GROUPS:
            raise ValueError("timeframe group must be sessions or subwindows")
        for field in ("start", "end"):
            value = getattr(self, field)
            if not isinstance(value, time) or value.tzinfo is not None:
                raise ValueError(f"timeframe {field} must be a naive time")
        if self.start == self.end:
            raise ValueError("timeframe start and end must differ")


@dataclass(frozen=True, slots=True)
class ReportingSlice:
    """A pooled (year=None) or trading-session-year reporting section."""

    year: int | None
    timeframe_id: str


def _clock(value: object, field: str) -> time:
    if not isinstance(value, str) or _CLOCK_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} must be a valid HH:MM clock time")
    return time.fromisoformat(value)


def load_timeframes(settings_path: Path) -> tuple[Timeframe, ...]:
    """Read and validate windows from the study's JSON-subset YAML settings."""

    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("study.yaml must use the documented JSON syntax subset") from exc
    if not isinstance(settings, dict):
        raise ValueError("study settings must be an object")
    reporting = settings.get("reporting")
    if not isinstance(reporting, dict):
        raise ValueError("reporting must be an object")
    if reporting.get("timezone") != "America/New_York":
        raise ValueError("reporting timezone must be America/New_York")
    if reporting.get("interval_bounds") != "start_inclusive_end_exclusive":
        raise ValueError("reporting interval_bounds must be start_inclusive_end_exclusive")
    rows = reporting.get("timeframes")
    if not isinstance(rows, list) or not rows:
        raise ValueError("reporting timeframes must be a nonempty list")

    result: list[Timeframe] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"timeframes[{index}] must be an object")
        frame = Timeframe(
            id=_nonempty_text(row.get("id"), f"timeframes[{index}].id"),
            label=_nonempty_text(row.get("label"), f"timeframes[{index}].label"),
            group=_nonempty_text(row.get("group"), f"timeframes[{index}].group"),
            start=_clock(row.get("start"), f"timeframes[{index}].start"),
            end=_clock(row.get("end"), f"timeframes[{index}].end"),
        )
        if frame.id in seen:
            raise ValueError(f"duplicate timeframe id: {frame.id}")
        seen.add(frame.id)
        result.append(frame)
    return tuple(result)


def timeframe_ids(
    bar_start: datetime, timeframes: Sequence[Timeframe]
) -> tuple[str, ...]:
    """Return every matching window in config order, without rounding the time.

    Overnight windows wrap across midnight. Overlap creates independent matches;
    a bar outside every configured window returns an empty tuple. Aware datetimes
    are rejected to avoid converting already-normalized retained timestamps again.
    """

    if not isinstance(bar_start, datetime):
        raise TypeError("bar_start must be a datetime")
    if bar_start.tzinfo is not None:
        raise ValueError("bar_start must be normalized naive New York wall time")
    clock = bar_start.time()
    matches: list[str] = []
    for frame in timeframes:
        if frame.start < frame.end:
            inside = frame.start <= clock < frame.end
        else:
            inside = clock >= frame.start or clock < frame.end
        if inside:
            matches.append(frame.id)
    return tuple(matches)


def reporting_slices(
    bar_start: datetime,
    session_date: date,
    timeframes: Sequence[Timeframe],
) -> tuple[ReportingSlice, ...]:
    """Return pooled/yearly all-hours and independent matching-window sections.

    ``session_date`` is the caller's authoritative ``session_date_proxy`` and must
    be a date, not a datetime. Its year is used unchanged: a December 31 evening
    bar whose session date is January 1 belongs to the following reporting year.
    Unassigned clock hours remain in both all-hours sections.
    """

    if not isinstance(session_date, date) or isinstance(session_date, datetime):
        raise TypeError("session_date must be a date, not a datetime")
    matches = timeframe_ids(bar_start, timeframes)
    year = session_date.year
    return (
        ReportingSlice(None, "all_hours"),
        ReportingSlice(year, "all_hours"),
        *(ReportingSlice(None, frame_id) for frame_id in matches),
        *(ReportingSlice(year, frame_id) for frame_id in matches),
    )
