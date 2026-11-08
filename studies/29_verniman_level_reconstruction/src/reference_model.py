"""Synthetic specification oracle for Study 29; not a Pine interpreter.

Only generated test bars are consumed. This module proves neither TradingView
compilation nor provider history, execution order, or Bar Replay behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from math import floor, isfinite
from typing import Iterable
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
UTC = timezone.utc
DAY = timedelta(days=1)
EMPTY_LEVELS = (None, None, None)


def local(day: date, hour: int, minute: int = 0) -> datetime:
    """Construct civil NY boundaries, never by adding 24 hours to UTC."""
    return datetime.combine(day, time(hour, minute), NY)


@dataclass(frozen=True)
class Clock:
    trading_date: date
    futures_start: datetime
    futures_end: datetime
    rth_start: datetime
    rth_end: datetime
    week_start: datetime
    week_end: datetime


def clock(stamp: datetime) -> Clock | None:
    if stamp.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    civil = stamp.astimezone(NY)
    trade_day = civil.date() + (DAY if civil.hour >= 18 else timedelta())
    start, end = local(trade_day - DAY, 18), local(trade_day, 17)
    if trade_day.weekday() > 4 or not start <= civil < end:
        return None
    monday = trade_day - timedelta(days=trade_day.weekday())
    return Clock(
        trade_day, start, end, local(trade_day, 9, 30), local(trade_day, 16),
        local(monday - DAY, 18), local(monday + timedelta(days=4), 17),
    )


def allowed_gap(previous_close: datetime, next_open: datetime) -> bool:
    """Only an exact maintenance break is harmless within a weekly profile."""
    if previous_close == next_open:
        return True
    before, after = previous_close.astimezone(NY), next_open.astimezone(NY)
    return (
        before.weekday() < 4
        and before.time().replace(tzinfo=None) == time(17)
        and after.date() == before.date()
        and after.time().replace(tzinfo=None) == time(18)
    )


def prior_trading_date(trading_date: date) -> date:
    """Calendar expectation, intentionally without inferring holiday sessions."""
    return trading_date - timedelta(days=3 if trading_date.weekday() == 0 else 1)


@dataclass(frozen=True)
class Bar:
    opened: datetime
    closed: datetime
    high: float
    low: float
    close: float
    volume: float | None
    confirmed: bool = True


@dataclass
class Profile:
    row_size: float = 4.0
    va_pct: float = 70.0
    max_bins: int = 6000
    bins: dict[int, float] = field(default_factory=dict)
    total: float = 0.0
    bad: bool = False

    def __post_init__(self) -> None:
        if self.row_size <= 0 or not 0 < self.va_pct <= 100 or self.max_bins < 1:
            raise ValueError("invalid profile settings")

    def reset(self) -> None:
        self.bins.clear()
        self.total = 0.0
        self.bad = False

    def add(self, high: float, low: float, volume: float | None) -> None:
        if self.bad:
            return
        if (volume is None or not all(isfinite(x) for x in (high, low, volume))
                or volume < 0 or low > high):
            self.bad = True
            self.bins.clear()
            self.total = 0.0
            return
        lo, hi = floor(low / self.row_size), floor(high / self.row_size)
        min_key = min(lo, min(self.bins, default=lo))
        max_key = max(hi, max(self.bins, default=hi))
        if max_key - min_key + 1 > self.max_bins:
            self.bad = True
            self.bins.clear()
            self.total = 0.0
            return
        for key in range(min_key, max_key + 1):
            self.bins.setdefault(key, 0.0)
        per_bin = volume / (hi - lo + 1)
        for key in range(lo, hi + 1):
            self.bins[key] += per_bin
        self.total += volume

    def levels(self) -> tuple[float | None, float | None, float | None]:
        """VAH, POC, VAL use bin lower edges, as in the supplied baseline."""
        if self.bad or not self.bins or self.total <= 0:
            return EMPTY_LEVELS
        # Lowest-price POC wins equal maxima. VA expansion ties go upward.
        poc = min(self.bins, key=lambda key: (-self.bins[key], key))
        lo = hi = poc
        cumulative = self.bins[poc]
        while (cumulative < self.total * self.va_pct / 100
               and (lo > min(self.bins) or hi < max(self.bins))):
            below, above = self.bins.get(lo - 1, -1), self.bins.get(hi + 1, -1)
            if above >= below:
                hi += 1
                cumulative += self.bins[hi]
            else:
                lo -= 1
                cumulative += self.bins[lo]
        return hi * self.row_size, poc * self.row_size, lo * self.row_size


@dataclass(frozen=True)
class Reference:
    start: datetime
    end: datetime
    coverage: bool
    levels: tuple[float | None, float | None, float | None]
    high: float | None
    low: float | None
    close: float | None


@dataclass
class Window:
    start: datetime
    end: datetime
    profile: Profile
    weekly: bool = False
    last_close: datetime | None = None
    coverage: bool = True
    high: float | None = None
    low: float | None = None
    close: float | None = None

    def add(self, bar: Bar) -> None:
        if not bar.confirmed:
            return
        if not (self.start <= bar.opened < bar.closed <= self.end):
            self.coverage = False
            return
        expected = self.start if self.last_close is None else self.last_close
        continuity = allowed_gap(expected, bar.opened) if self.weekly else expected == bar.opened
        self.coverage = self.coverage and continuity
        self.last_close = bar.closed
        self.high = bar.high if self.high is None else max(self.high, bar.high)
        self.low = bar.low if self.low is None else min(self.low, bar.low)
        self.close = bar.close
        self.profile.add(bar.high, bar.low, bar.volume)

    def reference(self, through: datetime | None = None) -> Reference:
        boundary = self.end if through is None else through
        ready = self.coverage and self.last_close == boundary
        return Reference(
            self.start, boundary, ready,
            self.profile.levels() if ready else EMPTY_LEVELS,
            self.high if ready else None, self.low if ready else None,
            self.close if ready else None,
        )


@dataclass(frozen=True)
class Snapshot:
    trading_date: date
    cutoff: datetime
    last_open: datetime
    last_close: datetime
    values: tuple[float | None, ...]
    references: tuple[tuple[str, datetime | None, datetime | None], ...]


class CandidateEngine:
    """Small independent oracle for availability and frozen-map properties.

    Candidate order is previous full H/L, current week VAH/POC/VAL,
    previous week VAH/POC/VAL, latest completed RTH VAH/POC/VAL,
    overnight VAH/POC/VAL, overnight H/L, latest RTH H/L/last close.
    """

    def __init__(self, *, minutes: int = 5, row_size: float = 4,
                 va_pct: float = 70, cutoff: tuple[int, int] = (9, 25)):
        if minutes not in (1, 5):
            raise ValueError("only 1- and 5-minute charts supported")
        if not (0 <= cutoff[0] <= 9 and 0 <= cutoff[1] <= 59
                and cutoff < (9, 30)):
            raise ValueError("cutoff must be a pre-open NY civil time")
        self.minutes, self.row_size, self.va_pct, self.cutoff = minutes, row_size, va_pct, cutoff
        self.futures: Window | None = None
        self.overnight: Window | None = None
        self.rth: Window | None = None
        self.week: Window | None = None
        self.previous_full: Reference | None = None
        self.completed_rth: Reference | None = None
        self.previous_week: Reference | None = None
        self.snapshot: Snapshot | None = None
        self.snapshot_status = "waiting"
        self.trade_day: date | None = None

    def window(self, start: datetime, end: datetime, *, weekly: bool = False) -> Window:
        return Window(start, end, Profile(self.row_size, self.va_pct), weekly)

    def accept(self, bar: Bar) -> None:
        if not bar.confirmed:
            return
        if bar.closed.astimezone(UTC) - bar.opened.astimezone(UTC) != timedelta(minutes=self.minutes):
            raise ValueError("bar duration differs from declared timeframe")
        identity = clock(bar.opened)
        if identity is None:
            return
        if self.trade_day != identity.trading_date:
            prior_is_adjacent = self.trade_day == prior_trading_date(identity.trading_date)
            self.previous_full = self.futures.reference() if self.futures is not None and prior_is_adjacent else None
            self.completed_rth = self.rth.reference() if self.rth is not None and prior_is_adjacent else None
            self.futures = self.window(identity.futures_start, identity.futures_end)
            self.overnight = self.window(identity.futures_start, identity.rth_start)
            self.rth = self.window(identity.rth_start, identity.rth_end)
            self.trade_day = identity.trading_date
            self.snapshot = None
            self.snapshot_status = "waiting"
        if self.week is None or self.week.start != identity.week_start:
            expected_week = local(identity.week_start.date() - timedelta(days=7), 18)
            self.previous_week = self.week.reference() if self.week is not None and self.week.start == expected_week else None
            self.week = self.window(identity.week_start, identity.week_end, weekly=True)

        self.futures.add(bar)
        self.week.add(bar)
        if bar.opened < identity.rth_start:
            self.overnight.add(bar)
        if identity.rth_start <= bar.opened < identity.rth_end:
            self.rth.add(bar)
        if bar.closed == identity.rth_end:
            self.completed_rth = self.rth.reference()
        if bar.closed == identity.futures_end:
            self.previous_full = self.futures.reference()

        cutoff = local(identity.trading_date, *self.cutoff)
        if self.snapshot_status == "waiting" and bar.closed >= cutoff:
            if bar.closed != cutoff:
                self.snapshot_status = "missing exact cutoff bar"
            else:
                self.snapshot = self.freeze(bar, cutoff)
                self.snapshot_status = "captured; family readiness is independent"

    def freeze(self, bar: Bar, cutoff: datetime) -> Snapshot:
        def levels(ref: Reference | None) -> tuple:
            return EMPTY_LEVELS if ref is None else ref.levels

        def prices(ref: Reference | None) -> tuple:
            return (None, None) if ref is None else (ref.high, ref.low)

        week = self.week.reference(cutoff)
        overnight = self.overnight.reference(cutoff)
        refs = (self.previous_full, week, self.previous_week, self.completed_rth, overnight)
        values = (
            *prices(self.previous_full), *levels(week), *levels(self.previous_week),
            *levels(self.completed_rth), *levels(overnight), *prices(overnight),
            *prices(self.completed_rth), None if self.completed_rth is None else self.completed_rth.close,
        )
        sources = tuple((name, None if ref is None else ref.start, None if ref is None else ref.end)
                        for name, ref in zip(("full", "week", "previous week", "RTH", "overnight"), refs))
        return Snapshot(self.trade_day, cutoff, bar.opened, bar.closed, values, sources)

    def feed(self, bars: Iterable[Bar]) -> None:
        for bar in bars:
            self.accept(bar)
