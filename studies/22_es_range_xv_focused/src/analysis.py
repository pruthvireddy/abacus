"""Study-local grouped descriptive statistics from saved directional runs.

Groups are chosen from each run's first candle. A run remains whole when it
crosses a named clock-window boundary. Estimates use exact (uncensored) runs;
observed and censored counts remain separate and explicit.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from math import fsum
from typing import Iterable, Sequence

from timeframes import Timeframe, reporting_slices
from trends import Bar, COMPLETED_STATUSES, Trend


DIRECTIONS = ("bullish", "bearish", "all")
HISTOGRAM_BINS = (("1", 1, 1), ("2", 2, 2), ("3", 3, 3), ("4", 4, 4),
                  ("5", 5, 5), ("6-7", 6, 7), ("8-9", 8, 9),
                  ("10-14", 10, 14), ("15-19", 15, 19), ("20+", 20, None))
SURVIVAL_THRESHOLDS = (2, 3, 5, 10, 20)


@dataclass(slots=True)
class _CoverageCell:
    eligible_bar_count: int = 0
    sessions: set[date] = field(default_factory=set)


class Coverage:
    """Coverage of eligible completed source bars, independent of event starts."""

    def __init__(self, timeframes: Sequence[Timeframe]) -> None:
        self.timeframes = tuple(timeframes)
        self.cells: dict[tuple[int, int | None, str], _CoverageCell] = {}

    def observe(self, bar: Bar) -> None:
        if not bar.primary_eligible or bar.completion_status not in COMPLETED_STATUSES:
            return
        for section in reporting_slices(bar.start_timestamp, bar.session_date, self.timeframes):
            key = (bar.setting_ticks, section.year, section.timeframe_id)
            cell = self.cells.setdefault(key, _CoverageCell())
            cell.eligible_bar_count += 1
            cell.sessions.add(bar.session_date)

    def rows(self, settings: Sequence[int], years: Iterable[int] = range(2019, 2027)) -> list[dict]:
        years = tuple(years)
        return [dict(setting_ticks=setting, year=year, timeframe_id=window,
                     **self.fields((setting, year, window)))
                for setting in settings for year in (None, *years)
                for window in ("all_hours", *(frame.id for frame in self.timeframes))]

    def fields(self, key: tuple[int, int | None, str]) -> dict:
        cell = self.cells.get(key, _CoverageCell())
        return {
            "eligible_bar_count": cell.eligible_bar_count,
            "covered_sessions": len(cell.sessions),
            "first_session_date": min(cell.sessions).isoformat() if cell.sessions else None,
            "last_session_date": max(cell.sessions).isoformat() if cell.sessions else None,
        }


@dataclass(slots=True)
class _Cell:
    observed: int = 0
    left: int = 0
    right: int = 0
    censored: int = 0
    sessions: set[date] = field(default_factory=set)
    exact_sessions: set[date] = field(default_factory=set)
    lengths: Counter = field(default_factory=Counter)

    def add(self, trend: Trend) -> None:
        self.observed += 1
        self.left += int(trend.left_censored)
        self.right += int(trend.right_censored)
        self.sessions.add(trend.session_date)
        if trend.length is None:
            self.censored += 1
        else:
            self.lengths[trend.length] += 1
            self.exact_sessions.add(trend.session_date)


@dataclass(frozen=True, slots=True)
class AnalysisTables:
    summaries: list[dict]
    histograms: list[dict]
    survival: list[dict]


def _quantile(lengths: Counter, probability: float) -> float | None:
    count = sum(lengths.values())
    if not count:
        return None
    position = (count - 1) * probability
    lower = int(position)
    upper = lower + int(position > lower)
    values: dict[int, int] = {}
    cumulative = 0
    for value, frequency in sorted(lengths.items()):
        for index in (lower, upper):
            if cumulative <= index < cumulative + frequency:
                values[index] = value
        cumulative += frequency
        if upper in values:
            break
    return float(values[lower] + (values[upper] - values[lower]) * (position - lower))


def analyze(
    trends: Iterable[Trend],
    settings: Sequence[int],
    timeframes: Sequence[Timeframe],
    coverage: Coverage | None = None,
    years: Iterable[int] = range(2019, 2027),
) -> AnalysisTables:
    """Accumulate one trend stream into complete summary/histogram/tail tables.

    Counter-based aggregation avoids retaining millions of event objects in
    overlapping group lists. Probabilities use uncensored runs as denominator.
    ``year=None`` means the pooled observed history, not an averaged yearly cell.
    """
    settings = tuple(settings)
    years = tuple(years)
    if len(set(settings)) != len(settings) or any(setting not in (4, 5, 6) for setting in settings):
        raise ValueError("settings must contain distinct 4/5/6 tick charts")
    if len(set(years)) != len(years) or any(not isinstance(year, int) for year in years):
        raise ValueError("years must contain distinct integers")
    windows = ("all_hours", *(frame.id for frame in timeframes))
    if len(set(windows)) != len(windows):
        raise ValueError("timeframe ids must be distinct")
    cells: dict[tuple[int, int | None, str, str], _Cell] = {}
    for trend in trends:
        if trend.setting_ticks not in settings or trend.session_date.year not in years:
            raise ValueError("trend belongs to an undeclared setting or year")
        if trend.direction not in DIRECTIONS[:2] or trend.observed_length < 1:
            raise ValueError("invalid directional trend")
        censored = trend.left_censored or trend.right_censored
        if (trend.length is None) != censored or (trend.length is not None and trend.length != trend.observed_length):
            raise ValueError("exact trend length must be null exactly when censored")
        for section in reporting_slices(trend.start_timestamp, trend.session_date, timeframes):
            for direction in (trend.direction, "all"):
                key = (trend.setting_ticks, section.year, section.timeframe_id, direction)
                cells.setdefault(key, _Cell()).add(trend)
    summaries, histograms, survival = [], [], []
    for setting in settings:
        for year in (None, *years):
            for window in windows:
                for direction in DIRECTIONS:
                    key = (setting, year, window, direction)
                    cell = cells.get(key, _Cell())
                    lengths = cell.lengths
                    denominator = sum(lengths.values())
                    base = {"setting_ticks": setting, "year": year,
                            "timeframe_id": window, "direction": direction}
                    common = {
                        "observed_trends": cell.observed,
                        "exact_trends": denominator,
                        "censored_trends": cell.censored,
                        "left_censored_trends": cell.left,
                        "right_censored_trends": cell.right,
                        "sessions_with_trends": len(cell.sessions),
                        "sessions_with_exact_trends": len(cell.exact_sessions),
                    }
                    coverage_fields = coverage.fields(key[:3]) if coverage is not None else {
                        "eligible_bar_count": None, "covered_sessions": None,
                        "first_session_date": None, "last_session_date": None,
                    }
                    max_frequency = max(lengths.values(), default=0)
                    modes = sorted(value for value, count in lengths.items() if count == max_frequency)
                    summaries.append({
                        **base, **common, **coverage_fields, "units": "candles",
                        "mean_candles": fsum(value * count for value, count in lengths.items()) / denominator if denominator else None,
                        "median_candles": _quantile(lengths, .5),
                        "mode_candles": modes[0] if modes else None,
                        "tied_modes": "|".join(map(str, modes)),
                        "q25_candles": _quantile(lengths, .25),
                        "q75_candles": _quantile(lengths, .75),
                        "p90_candles": _quantile(lengths, .9),
                        "p95_candles": _quantile(lengths, .95),
                        "max_candles": max(lengths) if lengths else None,
                    })
                    for label, lower, upper in HISTOGRAM_BINS:
                        numerator = sum(count for value, count in lengths.items()
                                        if value >= lower and (upper is None or value <= upper))
                        histograms.append({**base, "bin": label, "lower_candles": lower,
                                           "upper_candles": upper, "numerator": numerator,
                                           "denominator": denominator,
                                           "probability": numerator / denominator if denominator else None})
                    for threshold in SURVIVAL_THRESHOLDS:
                        numerator = sum(count for value, count in lengths.items() if value >= threshold)
                        survival.append({**base, "minimum_candles": threshold,
                                         "numerator": numerator, "denominator": denominator,
                                         "probability": numerator / denominator if denominator else None})
    return AnalysisTables(summaries, histograms, survival)


def summarize(trends: Iterable[Trend], settings: Sequence[int], timeframes: Sequence[Timeframe],
              coverage: Coverage | None = None, years: Iterable[int] = range(2019, 2027)) -> list[dict]:
    """Convenience projection; use ``analyze`` when saving all three tables."""
    return analyze(trends, settings, timeframes, coverage, years).summaries
