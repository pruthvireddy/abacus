"""Streaming, exact-price directional candle runs for Study 22.

The completed-bar definition uses the retained next-bar-start proxies. It does
not assert an exact completion time. Barriers remain in the stream so excluding
a row can never join runs on its two sides.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Iterator, MutableMapping


COMPLETED_STATUSES = frozenset({"next_bar_start_proxy", "next_bar_start_same_second"})
_COLUMNS = (
    "source_row", "source_timestamp", "bar_start_timestamp",
    "bar_completion_timestamp_proxy", "bar_duration_seconds_proxy",
    "completion_proxy_status", "session_date_proxy", "open", "high", "low", "close",
)


@dataclass(frozen=True, slots=True)
class Bar:
    setting_ticks: int
    source_row: int
    start_timestamp: datetime
    completion_timestamp: datetime | None
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    completion_status: str
    primary_eligible: bool = True
    barrier_reason: str | None = None

    @property
    def direction(self) -> str | None:
        return "bullish" if self.close > self.open else "bearish" if self.close < self.open else None


@dataclass(frozen=True, slots=True)
class Trend:
    setting_ticks: int
    direction: str
    start_source_row: int
    end_source_row: int
    start_timestamp: datetime
    end_timestamp: datetime
    session_date: date
    observed_length: int
    length: int | None
    left_censored: bool
    right_censored: bool
    end_reason: str
    termination_available_at: datetime | None


def inferred_session_date(stamp: datetime) -> date:
    """Apply the pinned normalized-wall-time 18:00 trading-date convention."""
    if stamp.tzinfo is not None:
        raise ValueError("timestamps must be normalized naive New York wall time")
    return stamp.date() + timedelta(days=int(stamp.time() >= time(18)))


def _timestamp(raw: str, field: str, row: int) -> datetime:
    try:
        stamp = datetime.fromisoformat(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"source row {row}: invalid {field}") from exc
    if stamp.tzinfo is not None:
        raise ValueError(f"source row {row}: {field} must be naive New York wall time")
    return stamp


def _price(raw: str, field: str, row: int) -> Decimal:
    try:
        price = Decimal(raw)
    except (TypeError, InvalidOperation) as exc:
        raise ValueError(f"source row {row}: invalid {field}") from exc
    if not price.is_finite():
        raise ValueError(f"source row {row}: {field} must be finite")
    return price


def _increment(audit: MutableMapping, category: str, key: str) -> None:
    counts = audit.setdefault(category, {})
    counts[key] = counts.get(key, 0) + 1


def load_bars(
    path: Path | str,
    setting: int,
    exclude_session_dates: Iterable[date | str] = (),
    *,
    audit: MutableMapping | None = None,
) -> Iterator[Bar]:
    """Validate and stream every semicolon-delimited row, including barriers.

    Identical adjacent timestamp+OHLC rows are flagged, never removed: the
    second-resolution export cannot prove that they are duplicate records.
    All same-second candles retain original order. An optional mutable audit
    receives counts and bounded identical-row examples.
    """
    if setting not in (4, 5, 6):
        raise ValueError("setting must be one of 4, 5, 6 ticks")
    excluded = frozenset(date.fromisoformat(value) if isinstance(value, str) else value
                         for value in exclude_session_dates)
    if any(not isinstance(value, date) or isinstance(value, datetime) for value in excluded):
        raise ValueError("excluded session dates must be ISO dates or date objects")
    if audit is None:
        audit = {}
    audit.setdefault("input_rows", 0)
    audit.setdefault("primary_eligible_bars", 0)
    audit.setdefault("doji_eligible_bars", 0)
    audit.setdefault("same_second_eligible_bars", 0)
    audit.setdefault("duplicate_adjacent_rows", 0)
    previous: Bar | None = None
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if reader.fieldnames != list(_COLUMNS):
            raise ValueError("enhanced Range XV CSV header does not match the pinned schema")
        for row_number, raw in enumerate(reader, start=1):
            if None in raw or any(value is None for value in raw.values()):
                raise ValueError(f"source row {row_number}: wrong column count")
            if raw["source_row"] != str(row_number):
                raise ValueError(f"source row {row_number}: source_row sequence is not contiguous")
            try:
                datetime.strptime(raw["source_timestamp"], "%Y-%d-%m %H:%M:%S")
            except (TypeError, ValueError) as exc:
                raise ValueError(f"source row {row_number}: invalid source_timestamp") from exc
            stamp = _timestamp(raw["bar_start_timestamp"], "bar_start_timestamp", row_number)
            try:
                session = date.fromisoformat(raw["session_date_proxy"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"source row {row_number}: invalid session_date_proxy") from exc
            if session != inferred_session_date(stamp):
                raise ValueError(f"source row {row_number}: session date disagrees with 18:00 rollover")
            prices = tuple(_price(raw[field], field, row_number) for field in ("open", "high", "low", "close"))
            open_price, high, low, close = prices
            if not low <= min(open_price, close) <= max(open_price, close) <= high:
                raise ValueError(f"source row {row_number}: invalid OHLC ordering")
            status = raw["completion_proxy_status"]
            completion = (_timestamp(raw["bar_completion_timestamp_proxy"], "completion proxy", row_number)
                          if raw["bar_completion_timestamp_proxy"] else None)
            if completion is not None and completion < stamp:
                raise ValueError(f"source row {row_number}: completion precedes opening")
            if status in COMPLETED_STATUSES:
                if completion is None or inferred_session_date(completion) != session:
                    raise ValueError(f"source row {row_number}: completed proxy needs a same-session timestamp")
                if (status == "next_bar_start_same_second") != (completion == stamp):
                    raise ValueError(f"source row {row_number}: completion status disagrees with timestamp")
                duration = _price(raw["bar_duration_seconds_proxy"], "bar_duration_seconds_proxy", row_number)
                if duration != Decimal(str((completion - stamp).total_seconds())):
                    raise ValueError(f"source row {row_number}: duration disagrees with completion proxy")
            elif raw["bar_duration_seconds_proxy"]:
                _price(raw["bar_duration_seconds_proxy"], "bar_duration_seconds_proxy", row_number)
            if previous is not None:
                if stamp < previous.start_timestamp:
                    raise ValueError(f"source row {row_number}: opening timestamps regress")
                if previous.completion_status in COMPLETED_STATUSES and (
                    previous.completion_timestamp != stamp or previous.session_date != session
                ):
                    raise ValueError(f"source row {row_number}: previous completion proxy is not this bar's opening")
            duplicate = previous is not None and (
                stamp, open_price, high, low, close
            ) == (
                previous.start_timestamp, previous.open, previous.high, previous.low, previous.close
            )
            if session in excluded:
                reason = "excluded_session"
            elif status not in COMPLETED_STATUSES:
                reason = f"completion_status:{status or 'missing'}"
            else:
                reason = None
            bar = Bar(setting, row_number, stamp, completion, session, open_price,
                      high, low, close, status, reason is None, reason)
            audit["input_rows"] += 1
            _increment(audit, "completion_status_counts", status or "missing")
            if duplicate:
                audit["duplicate_adjacent_rows"] += 1
                examples = audit.setdefault("duplicate_examples", [])
                if len(examples) < 10:
                    examples.append({"source_row": row_number, "previous_source_row": row_number - 1,
                                     "start_timestamp": stamp.isoformat(sep=" ")})
            if reason is None:
                audit["primary_eligible_bars"] += 1
                audit["doji_eligible_bars"] += int(bar.direction is None)
                audit["same_second_eligible_bars"] += int(status == "next_bar_start_same_second")
            else:
                _increment(audit, "barrier_counts", reason)
                if reason == "excluded_session":
                    _increment(audit, "excluded_session_counts", session.isoformat())
            previous = bar
            yield bar
    if previous is not None and previous.completion_status in COMPLETED_STATUSES:
        raise ValueError("final source row claims a completion proxy without a following row")


def extract_trends(bars: Iterable[Bar], setting: int) -> Iterator[Trend]:
    """Yield maximal same-direction runs without crossing eligibility barriers.

    A reversal or a completed doji establishes an observed right boundary. The
    first non-doji run after a barrier lacks a known left boundary. Only runs
    with both boundaries known receive an exact ``length``.
    """
    if setting not in (4, 5, 6):
        raise ValueError("setting must be one of 4, 5, 6 ticks")
    first: Bar | None = None
    last: Bar | None = None
    count = 0
    left_censored = True
    known_start = False
    session: date | None = None

    def finish(right_censored: bool, reason: str, available_at: datetime | None) -> Trend:
        if first is None or last is None:
            raise RuntimeError("cannot finish an empty run")
        return Trend(setting, first.direction, first.source_row, last.source_row,
                     first.start_timestamp, last.start_timestamp, first.session_date,
                     count, None if left_censored or right_censored else count,
                     left_censored, right_censored, reason, available_at)

    for bar in bars:
        if bar.setting_ticks != setting:
            raise ValueError("cannot pool different Range XV settings in one trend stream")
        if session is not None and bar.session_date != session:
            if first is not None:
                yield finish(True, "session_boundary", None)
            first = last = None
            count = 0
            known_start = False
        session = bar.session_date
        if not bar.primary_eligible or bar.completion_status not in COMPLETED_STATUSES:
            if first is not None:
                yield finish(True, bar.barrier_reason or f"completion_status:{bar.completion_status or 'missing'}", None)
            first = last = None
            count = 0
            known_start = False
            continue
        direction = bar.direction
        if direction is None:
            if first is not None:
                yield finish(False, "doji", bar.completion_timestamp)
            first = last = None
            count = 0
            known_start = True
            continue
        if first is not None and direction != first.direction:
            yield finish(False, "reversal", bar.completion_timestamp)
            first = last = None
            count = 0
            known_start = True
        if first is None:
            first = bar
            left_censored = not known_start
        last = bar
        count += 1
    if first is not None:
        yield finish(True, "export_end", None)
