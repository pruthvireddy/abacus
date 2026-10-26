"""Earlier trend A, exactly one opposite candle B, then trend-resuming R.

These events retain A's observed boundaries separately from B and R. A may
have an unknown start; it is never assigned an invented exact-length cohort.
Continuation and immediate F1 retracement retain the reversal definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Iterator

from reversals import HORIZONS, RETRACE_LEVELS, Reversal
from trends import Bar, COMPLETED_STATUSES


@dataclass(frozen=True, slots=True)
class Pullback:
    setting_ticks: int
    direction: str
    earlier_start_source_row: int
    earlier_end_source_row: int
    earlier_start_timestamp: datetime
    earlier_end_timestamp: datetime
    earlier_observed_length: int
    earlier_start_known: bool
    pullback_source_row: int
    pullback_start_timestamp: datetime
    pullback_available_at: datetime
    pullback_open: Decimal
    pullback_high: Decimal
    pullback_low: Decimal
    pullback_close: Decimal
    source_row: int
    previous_source_row: int
    start_timestamp: datetime
    available_at: datetime
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    follow_count: int
    exact_follow_count: int | None
    right_censored: bool
    end_reason: str
    termination_available_at: datetime | None
    f1_source_row: int | None
    f1_start_timestamp: datetime | None
    f1_available_at: datetime | None
    f1_open: Decimal | None
    f1_high: Decimal | None
    f1_low: Decimal | None
    f1_close: Decimal | None

    @property
    def earlier_exact_length(self) -> int | None:
        return self.earlier_observed_length if self.earlier_start_known else None

    @property
    def f1_known(self) -> bool:
        return self.f1_source_row is not None

    # These outcome methods reference R/F1 fields only. Earlier-trend metadata
    # does not masquerade as the previous reversal study's preceding B leg.
    continuation_outcome = Reversal.continuation_outcome
    retracement_price = Reversal.retracement_price
    retracement_outcome = Reversal.retracement_outcome


LEDGER_COLUMNS = (
    *(item.name for item in fields(Pullback)), "earlier_exact_length", "f1_known",
    *(f"retrace_price_{level}" for level in RETRACE_LEVELS),
    *(f"touch_{level}" for level in RETRACE_LEVELS),
    "favorable_beyond_close", "favorable_same_colour",
)


def ledger_row(event: Pullback) -> dict[str, str]:
    values = {item.name: getattr(event, item.name) for item in fields(Pullback)}
    values.update(earlier_exact_length=event.earlier_exact_length, f1_known=event.f1_known)
    for level in RETRACE_LEVELS:
        result = event.retracement_outcome(level)
        values[f"retrace_price_{level}"] = result["price"]
        values[f"touch_{level}"] = result["touched"]
    values["favorable_beyond_close"] = result["favorable_beyond_close"]
    values["favorable_same_colour"] = result["favorable_same_colour"]

    def serialize(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, datetime):
            return value.isoformat(sep=" ")
        if isinstance(value, date):
            return value.isoformat()
        return str(value)

    return {name: serialize(values[name]) for name in LEDGER_COLUMNS}


event_to_row = ledger_row


@dataclass(frozen=True, slots=True)
class _Leg:
    first: Bar
    last: Bar
    length: int
    start_known: bool


def extract_pullbacks(bars: Iterable[Bar], setting: int) -> Iterator[Pullback]:
    """Stream selected A→B→R setups and their observed future outcomes.

    A is an observed nonempty uninterrupted leg; B is exactly one opposite
    completed candle with both flips observed. Selection is causal at R's
    completion and does not depend on R's future end or F1 availability.
    """
    if setting not in (4, 5, 6):
        raise ValueError("setting must be one of 4, 5, 6 ticks")
    last_seen: Bar | None = None
    first: Bar | None = None
    last: Bar | None = None
    length = 0
    start_known = False
    next_start_known = False
    earlier: _Leg | None = None
    active: tuple[_Leg, Bar, Bar] | None = None
    follow_count = 0
    f1: Bar | None = None

    def finish(censored: bool, reason: str, at: datetime | None) -> Pullback:
        if active is None:
            raise RuntimeError("cannot finish an empty pullback setup")
        a, b, r = active
        return Pullback(
            setting, r.direction, a.first.source_row, a.last.source_row,
            a.first.start_timestamp, a.last.start_timestamp, a.length, a.start_known,
            b.source_row, b.start_timestamp, b.completion_timestamp,
            b.open, b.high, b.low, b.close,
            r.source_row, b.source_row, r.start_timestamp, r.completion_timestamp,
            r.session_date, r.open, r.high, r.low, r.close,
            follow_count, None if censored else follow_count, censored, reason, at,
            f1.source_row if f1 else None, f1.start_timestamp if f1 else None,
            f1.completion_timestamp if f1 else None, f1.open if f1 else None,
            f1.high if f1 else None, f1.low if f1 else None, f1.close if f1 else None,
        )

    for bar in bars:
        if bar.setting_ticks != setting:
            raise ValueError("cannot pool different Range XV settings in one pullback stream")
        if not isinstance(bar.source_row, int) or isinstance(bar.source_row, bool) or bar.source_row < 1:
            raise ValueError("source rows must be positive integers")
        boundary: str | None = None
        if last_seen is not None:
            if bar.source_row <= last_seen.source_row:
                raise ValueError("source rows must be strictly increasing")
            if bar.source_row != last_seen.source_row + 1:
                boundary = "source_row_gap"
            elif bar.session_date != last_seen.session_date:
                boundary = "session_boundary"
        if boundary is not None:
            if active is not None:
                yield finish(True, boundary, None)
            first = last = earlier = None
            length = 0
            start_known = next_start_known = False
            active, f1, follow_count = None, None, 0
        last_seen = bar
        if not bar.primary_eligible or bar.completion_status not in COMPLETED_STATUSES:
            if active is not None:
                yield finish(True, bar.barrier_reason or f"completion_status:{bar.completion_status or 'missing'}", None)
            first = last = earlier = None
            length = 0
            start_known = next_start_known = False
            active, f1, follow_count = None, None, 0
            continue
        if bar.completion_timestamp is None:
            raise ValueError("a completed eligible bar must have a completion timestamp")
        if bar.start_timestamp.tzinfo is not None or bar.completion_timestamp.tzinfo is not None:
            raise ValueError("timestamps must be normalized naive New York wall time")
        direction = bar.direction
        if active is not None:
            if f1 is None:
                f1 = bar
            if direction == active[2].direction:
                follow_count += 1
            else:
                yield finish(False, "doji" if direction is None else "reversal", bar.completion_timestamp)
                active, f1, follow_count = None, None, 0
        if direction is None:
            first = last = earlier = None
            length = 0
            start_known = False
            next_start_known = True
            continue
        if first is not None and direction != first.direction:
            if length == 1 and earlier is not None and direction == earlier.first.direction:
                if earlier.last.source_row + 1 != last.source_row or last.source_row + 1 != bar.source_row:
                    raise RuntimeError("pullback selection lost contiguous A→B→R rows")
                active = (earlier, last, bar)
                f1, follow_count = None, 0
            earlier = _Leg(first, last, length, start_known)
            first = last = bar
            length, start_known, next_start_known = 1, True, False
        elif first is not None:
            last = bar
            length += 1
        else:
            first = last = bar
            length = 1
            start_known, next_start_known = next_start_known, False
    if active is not None:
        yield finish(True, "export_end", None)
