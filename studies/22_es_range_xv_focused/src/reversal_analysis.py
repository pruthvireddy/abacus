"""Grouped empirical reversal outcomes, with explicit unknown denominators."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Sequence

from analysis import Coverage
from reversals import HORIZONS, RETRACE_LEVELS, Reversal
from timeframes import Timeframe, reporting_slices


DIRECTIONS = ("bullish", "bearish", "all")
PRIOR_LEG_BUCKETS = ("all", *(str(n) for n in range(1, 11)), "11-15", "16-20", "21+", "unknown_start")
GROUP_COLUMNS = ("setting_ticks", "year", "timeframe_id", "direction", "prior_leg_bucket")
SUMMARY_COLUMNS = (*GROUP_COLUMNS, "event_count", "exact_followup_count", "censored_followup_count",
                   "known_f1_count", "unknown_f1_count", "prior_start_known_count", "prior_start_unknown_count",
                   "sessions_with_events", "sessions_with_known_f1", "eligible_bar_count", "covered_sessions",
                   "first_session_date", "last_session_date", "bar_coverage_anchor", "event_membership_anchor")
CONTINUATION_COLUMNS = (*GROUP_COLUMNS, "n", "event_count", "success_count", "failure_count", "unknown_count",
                        "numerator", "denominator", "probability", "sessions_with_events",
                        "sessions_with_known_outcome", "sessions_with_success", "units")
RETRACEMENT_COLUMNS = (
    *GROUP_COLUMNS, "level_percent", "event_count", "valid_f1_count", "unknown_f1_count", "touch_count",
    "touch_numerator", "touch_denominator", "touch_probability", "sessions_with_events", "sessions_with_valid_f1",
    "sessions_with_touch", "beyond_close_count", "same_colour_count",
    "joint_beyond_close_numerator", "joint_beyond_close_denominator", "joint_beyond_close_probability",
    "conditional_beyond_close_numerator", "conditional_beyond_close_denominator", "conditional_beyond_close_probability",
    "joint_same_colour_numerator", "joint_same_colour_denominator", "joint_same_colour_probability",
    "conditional_same_colour_numerator", "conditional_same_colour_denominator", "conditional_same_colour_probability",
    "units",
)


@dataclass(slots=True)
class _Horizon:
    success: int = 0
    failure: int = 0
    unknown: int = 0
    known_sessions: int = 0
    success_sessions: int = 0


@dataclass(slots=True)
class _Retrace:
    touch: int = 0
    joint_beyond: int = 0
    joint_colour: int = 0
    touch_sessions: int = 0


@dataclass(slots=True)
class _Cell:
    events: int = 0
    censored: int = 0
    known_f1: int = 0
    prior_known: int = 0
    beyond: int = 0
    colour: int = 0
    sessions: int = 0
    f1_sessions: int = 0
    horizons: dict[int, _Horizon] = field(default_factory=dict)
    retraces: dict[int, _Retrace] = field(default_factory=dict)

    def add(self, event: Reversal, horizons: tuple[int, ...], levels: tuple[int, ...],
            session_bit: int, retrace_results: dict[int, dict]) -> None:
        self.events += 1
        self.censored += int(event.right_censored)
        self.prior_known += int(event.prior_start_known)
        self.sessions |= session_bit
        for n in horizons:
            cell = self.horizons.get(n)
            if cell is None:
                cell = self.horizons[n] = _Horizon()
            outcome = True if n <= event.follow_count else None if event.right_censored else False
            if outcome is None:
                cell.unknown += 1
            else:
                cell.known_sessions |= session_bit
                if outcome:
                    cell.success += 1
                    cell.success_sessions |= session_bit
                else:
                    cell.failure += 1
        if event.f1_known:
            self.known_f1 += 1
            self.f1_sessions |= session_bit
            result = retrace_results[levels[0]]
            self.beyond += int(result["favorable_beyond_close"])
            self.colour += int(result["favorable_same_colour"])
            for level in levels:
                result = retrace_results[level]
                cell = self.retraces.get(level)
                if cell is None:
                    cell = self.retraces[level] = _Retrace()
                if result["touched"]:
                    cell.touch += 1
                    cell.touch_sessions |= session_bit
                    cell.joint_beyond += int(result["favorable_beyond_close"])
                    cell.joint_colour += int(result["favorable_same_colour"])


@dataclass(frozen=True, slots=True)
class ReversalTables:
    summaries: list[dict]
    continuation: list[dict]
    retracement: list[dict]


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def prior_leg_bucket(event: Reversal) -> str:
    """Causal preceding-leg cohort; unknown starts never get exact-size bins."""
    length = event.prior_exact_length
    if length is None:
        return "unknown_start"
    if length < 1:
        raise ValueError("prior exact leg length must be positive")
    return str(length) if length <= 10 else "11-15" if length <= 15 else "16-20" if length <= 20 else "21+"


def _validate_event(event: Reversal) -> None:
    if event.direction not in DIRECTIONS[:2] or event.prior_observed_length < 1 or event.follow_count < 0:
        raise ValueError("invalid directional reversal counts")
    if (event.exact_follow_count is None) != event.right_censored:
        raise ValueError("exact follower count must be null exactly when right-censored")
    if event.exact_follow_count is not None and event.exact_follow_count != event.follow_count:
        raise ValueError("exact follower count differs from observed followers")
    f1_values = (event.f1_source_row, event.f1_start_timestamp, event.f1_available_at,
                 event.f1_open, event.f1_high, event.f1_low, event.f1_close)
    if any(value is None for value in f1_values) != all(value is None for value in f1_values):
        raise ValueError("F1 fields must all be present or all be null")
    if not event.f1_known and (event.follow_count > 0 or not event.right_censored):
        raise ValueError("an absent F1 requires a censored zero-follow event")
    if event.f1_known and event.f1_source_row != event.source_row + 1:
        raise ValueError("F1 must be the contiguous next source row")
    if event.previous_source_row != event.source_row - 1:
        raise ValueError("a reversal predecessor must be contiguous")
    if event.start_timestamp.tzinfo is not None or event.available_at.tzinfo is not None:
        raise ValueError("timestamps must be normalized naive New York wall time")
    expected = "bullish" if event.close > event.open else "bearish" if event.close < event.open else None
    if expected != event.direction:
        raise ValueError("reversal candle prices do not match its direction")


def analyze_reversals(
    events: Iterable[Reversal],
    settings: Sequence[int],
    timeframes: Sequence[Timeframe],
    coverage: Coverage | None = None,
    years: Iterable[int] = range(2019, 2027),
    horizons: Iterable[int] = HORIZONS,
    levels: Iterable[int] = RETRACE_LEVELS,
) -> ReversalTables:
    """Every overall/year/window cell, using R.available_at as event anchor.

    Each horizon uses its own known-success-plus-known-failure denominator.
    A censored leg can still be a known success at short horizons. Retracement
    joint rates use all valid F1 candles; conditional rates use touched F1s.
    """
    settings, years, horizons, levels = tuple(settings), tuple(years), tuple(horizons), tuple(levels)
    if not settings or len(set(settings)) != len(settings) or any(setting not in (4, 5, 6) for setting in settings):
        raise ValueError("settings must contain distinct 4/5/6 tick charts")
    if len(set(years)) != len(years) or any(not isinstance(year, int) or isinstance(year, bool) for year in years):
        raise ValueError("years must contain distinct integers")
    if not horizons or len(set(horizons)) != len(horizons) or any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in horizons):
        raise ValueError("horizons must contain distinct positive integers")
    if not levels or len(set(levels)) != len(levels) or any(not isinstance(level, int) or isinstance(level, bool) or not 0 < level <= 100 for level in levels):
        raise ValueError("levels must contain distinct integer percentages in 1..100")
    windows = ("all_hours", *(frame.id for frame in timeframes))
    if len(set(windows)) != len(windows):
        raise ValueError("timeframe ids must be distinct")
    cells: dict[tuple[int, int | None, str, str, str], _Cell] = {}
    session_ids: dict[date, int] = {}
    for event in events:
        if event.setting_ticks not in settings or event.session_date.year not in years:
            raise ValueError("reversal belongs to an undeclared setting or year")
        _validate_event(event)
        session_bit = 1 << session_ids.setdefault(event.session_date, len(session_ids))
        bucket = prior_leg_bucket(event)
        retrace_results = {level: event.retracement_outcome(level) for level in levels}
        for section in reporting_slices(event.available_at, event.session_date, timeframes):
            for direction in (event.direction, "all"):
                for cohort in ("all", bucket):
                    key = (event.setting_ticks, section.year, section.timeframe_id, direction, cohort)
                    cell = cells.get(key)
                    if cell is None:
                        cell = cells[key] = _Cell()
                    cell.add(event, horizons, levels, session_bit, retrace_results)
    summaries, continuation, retracement = [], [], []
    for setting in settings:
        for year in (None, *years):
            for window in windows:
                for direction in DIRECTIONS:
                    for cohort in PRIOR_LEG_BUCKETS:
                        key = (setting, year, window, direction, cohort)
                        cell = cells.get(key, _Cell())
                        base = dict(zip(GROUP_COLUMNS, key))
                        coverage_fields = coverage.fields(key[:3]) if coverage is not None else {
                            "eligible_bar_count": None, "covered_sessions": None,
                            "first_session_date": None, "last_session_date": None,
                        }
                        summaries.append({
                            **base, "event_count": cell.events, "exact_followup_count": cell.events - cell.censored,
                            "censored_followup_count": cell.censored, "known_f1_count": cell.known_f1,
                            "unknown_f1_count": cell.events - cell.known_f1,
                            "prior_start_known_count": cell.prior_known, "prior_start_unknown_count": cell.events - cell.prior_known,
                            "sessions_with_events": cell.sessions.bit_count(), "sessions_with_known_f1": cell.f1_sessions.bit_count(),
                            **coverage_fields, "bar_coverage_anchor": "bar_start_timestamp",
                            "event_membership_anchor": "reversal_completion_timestamp_proxy",
                        })
                        for n in horizons:
                            result = cell.horizons.get(n, _Horizon())
                            denominator = result.success + result.failure
                            continuation.append({
                                **base, "n": n, "event_count": cell.events, "success_count": result.success,
                                "failure_count": result.failure, "unknown_count": result.unknown,
                                "numerator": result.success, "denominator": denominator,
                                "probability": _rate(result.success, denominator), "sessions_with_events": cell.sessions.bit_count(),
                                "sessions_with_known_outcome": result.known_sessions.bit_count(),
                                "sessions_with_success": result.success_sessions.bit_count(), "units": "followers_after_R",
                            })
                        for level in levels:
                            result = cell.retraces.get(level, _Retrace())
                            retracement.append({
                                **base, "level_percent": level, "event_count": cell.events,
                                "valid_f1_count": cell.known_f1, "unknown_f1_count": cell.events - cell.known_f1,
                                "touch_count": result.touch, "touch_numerator": result.touch,
                                "touch_denominator": cell.known_f1, "touch_probability": _rate(result.touch, cell.known_f1),
                                "sessions_with_events": cell.sessions.bit_count(), "sessions_with_valid_f1": cell.f1_sessions.bit_count(),
                                "sessions_with_touch": result.touch_sessions.bit_count(), "beyond_close_count": cell.beyond,
                                "same_colour_count": cell.colour,
                                "joint_beyond_close_numerator": result.joint_beyond, "joint_beyond_close_denominator": cell.known_f1,
                                "joint_beyond_close_probability": _rate(result.joint_beyond, cell.known_f1),
                                "conditional_beyond_close_numerator": result.joint_beyond, "conditional_beyond_close_denominator": result.touch,
                                "conditional_beyond_close_probability": _rate(result.joint_beyond, result.touch),
                                "joint_same_colour_numerator": result.joint_colour, "joint_same_colour_denominator": cell.known_f1,
                                "joint_same_colour_probability": _rate(result.joint_colour, cell.known_f1),
                                "conditional_same_colour_numerator": result.joint_colour, "conditional_same_colour_denominator": result.touch,
                                "conditional_same_colour_probability": _rate(result.joint_colour, result.touch),
                                "units": "fraction_of_R_body",
                            })
    return ReversalTables(summaries, continuation, retracement)


analyze = analyze_reversals
