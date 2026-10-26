"""Causal reversal events and their separately observed candle outcomes.

The first completed opposite-colour candle is R. Its next candle is F1; R is
never included in continuation counts. Source order, completion barriers and
inferred daily sessions are preserved, including equal timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Iterator

from trends import Bar, COMPLETED_STATUSES


HORIZONS = tuple(range(1, 21))
RETRACE_LEVELS = (25, 50, 75, 100)


@dataclass(frozen=True, slots=True)
class Reversal:
    setting_ticks: int
    direction: str
    source_row: int
    previous_source_row: int
    start_timestamp: datetime
    available_at: datetime
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    prior_observed_length: int
    prior_start_known: bool
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
    def f1_known(self) -> bool:
        return self.f1_source_row is not None

    @property
    def prior_exact_length(self) -> int | None:
        """R establishes the prior leg's end, but not an unobserved start."""
        return self.prior_observed_length if self.prior_start_known else None

    def continuation_outcome(self, n: int) -> bool | None:
        """At least n uninterrupted same-colour completed followers after R."""
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise ValueError("continuation horizon must be a positive integer")
        if n <= self.follow_count:
            return True
        return None if self.right_censored else False

    def retracement_price(self, level_percent: int) -> Decimal:
        if not isinstance(level_percent, int) or isinstance(level_percent, bool) or not 0 < level_percent <= 100:
            raise ValueError("retracement percent must be an integer in 1..100")
        return self.close + (self.open - self.close) * Decimal(level_percent) / Decimal(100)

    def retracement_outcome(self, level_percent: int) -> dict:
        """F1 touches R's body level and closes favorably; path order unknown.

        Beyond-close and same-colour endpoints are distinct. A doji F1 can
        finish beyond R.close; it cannot be a same-colour follower.
        """
        price = self.retracement_price(level_percent)
        if not self.f1_known:
            return {"price": price, "touched": None, "favorable_beyond_close": None,
                    "favorable_same_colour": None}
        bullish = self.direction == "bullish"
        touched = self.f1_low <= price if bullish else self.f1_high >= price
        beyond = self.f1_close > self.close if bullish else self.f1_close < self.close
        same_colour = self.f1_close > self.f1_open if bullish else self.f1_close < self.f1_open
        return {"price": price, "touched": touched, "favorable_beyond_close": beyond,
                "favorable_same_colour": same_colour}


LEDGER_COLUMNS = (
    *(item.name for item in fields(Reversal)), "prior_exact_length", "f1_known",
    *(f"retrace_price_{level}" for level in RETRACE_LEVELS),
    *(f"touch_{level}" for level in RETRACE_LEVELS),
    "favorable_beyond_close", "favorable_same_colour",
)


def ledger_row(event: Reversal) -> dict:
    """Exact ordered CSV strings; empty is null and booleans are lowercase."""
    values = {item.name: getattr(event, item.name) for item in fields(Reversal)}
    values.update(prior_exact_length=event.prior_exact_length, f1_known=event.f1_known)
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


def extract_reversals(bars: Iterable[Bar], setting: int) -> Iterator[Reversal]:
    """Stream all reversals, retaining known outcomes before a censored tail.

    At most one active event is needed: an opposite follower terminates the
    prior event and is itself a new R. Dojis break the leg without becoming R.
    The predecessor's complete trend start need not be observed for R to exist.
    """
    if setting not in (4, 5, 6):
        raise ValueError("setting must be one of 4, 5, 6 ticks")
    last_seen: Bar | None = None
    previous: Bar | None = None
    prior_count = 0
    prior_start_known = False
    next_start_known = False
    active: tuple[Bar, Bar, int, bool] | None = None
    follow_count = 0
    f1: Bar | None = None

    def finish(censored: bool, reason: str, at: datetime | None) -> Reversal:
        if active is None:
            raise RuntimeError("cannot finish an empty reversal")
        reversal, predecessor, length, start_known = active
        return Reversal(
            setting, reversal.direction, reversal.source_row, predecessor.source_row,
            reversal.start_timestamp, reversal.completion_timestamp, reversal.session_date,
            reversal.open, reversal.high, reversal.low, reversal.close, length, start_known,
            follow_count, None if censored else follow_count, censored, reason, at,
            f1.source_row if f1 else None, f1.start_timestamp if f1 else None,
            f1.completion_timestamp if f1 else None, f1.open if f1 else None,
            f1.high if f1 else None, f1.low if f1 else None, f1.close if f1 else None,
        )

    for bar in bars:
        if bar.setting_ticks != setting:
            raise ValueError("cannot pool different Range XV settings in one reversal stream")
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
            previous = None
            prior_count = 0
            prior_start_known = next_start_known = False
            active, f1, follow_count = None, None, 0
        last_seen = bar
        if not bar.primary_eligible or bar.completion_status not in COMPLETED_STATUSES:
            if active is not None:
                yield finish(True, bar.barrier_reason or f"completion_status:{bar.completion_status or 'missing'}", None)
            previous = None
            prior_count = 0
            prior_start_known = next_start_known = False
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
            if direction == active[0].direction:
                follow_count += 1
            else:
                yield finish(False, "doji" if direction is None else "reversal", bar.completion_timestamp)
                active, f1, follow_count = None, None, 0
        if direction is None:
            prior_count = 0
            prior_start_known = False
            next_start_known = True
        elif previous is not None and previous.direction is not None and previous.direction != direction:
            active = (bar, previous, prior_count, prior_start_known)
            f1, follow_count = None, 0
            prior_count = 1
            prior_start_known = True
            next_start_known = False
        elif previous is not None and previous.direction == direction:
            prior_count += 1
        else:
            prior_count = 1
            prior_start_known = next_start_known
            next_start_known = False
        previous = bar
    if active is not None:
        yield finish(True, "export_end", None)
