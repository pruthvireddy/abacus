"""Pinned holiday exclusions shared by VWAP and VP/HVN builders.

The rules retain the existing product behavior; session regimes and expected
minute policies remain with their respective builders.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta


def _easter(year: int) -> date:
    """Return Gregorian Easter using the Meeus/Jones/Butcher algorithm."""

    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    last = next_month - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(value: date) -> date:
    if value.weekday() == 5:
        return value - timedelta(days=1)
    if value.weekday() == 6:
        return value + timedelta(days=1)
    return value


def holiday_sessions(product: str, start_year: int, end_year: int) -> dict[date, list[str]]:
    """Generate the pinned CME holiday/shortened-session exclusion set."""

    result: dict[date, list[str]] = defaultdict(list)
    for year in range(start_year, end_year + 1):
        new_year = date(year, 1, 1)
        # CME does not shift a Saturday New Year's closure back onto Friday;
        # for Sunday it observes the following Monday.
        new_year_session = (
            new_year + timedelta(days=1) if new_year.weekday() == 6 else new_year
        )
        fixed = (
            (new_year_session, "New Year's"),
            (_observed(date(year, 7, 4)), "Independence Day"),
            (_observed(date(year, 12, 25)), "Christmas"),
        )
        for value, name in fixed:
            result[value].append(name)
        result[_nth_weekday(year, 1, 0, 3)].append("Martin Luther King Jr. Day")
        result[_nth_weekday(year, 2, 0, 3)].append("Presidents Day")
        result[_easter(year) - timedelta(days=2)].append("Good Friday")
        result[_last_weekday(year, 5, 0)].append("Memorial Day")
        if year >= 2022:
            result[_observed(date(year, 6, 19))].append("Juneteenth")
        result[_nth_weekday(year, 9, 0, 1)].append("Labor Day")
        thanksgiving = _nth_weekday(year, 11, 3, 4)
        result[thanksgiving].append("Thanksgiving")
        result[thanksgiving + timedelta(days=1)].append("Thanksgiving Friday early close")
        adjacent = [(12, 24, "Christmas Eve early close")]
        if product in {"ES", "NQ"}:
            adjacent.append((7, 3, "Independence Day adjacent equity early close"))
        for month, day, name in adjacent:
            value = date(year, month, day)
            if value.weekday() < 5:
                result[value].append(name)
    result[date(2018, 12, 5)].append("National day of mourning")
    result[date(2025, 1, 9)].append("National day of mourning")
    return dict(result)
