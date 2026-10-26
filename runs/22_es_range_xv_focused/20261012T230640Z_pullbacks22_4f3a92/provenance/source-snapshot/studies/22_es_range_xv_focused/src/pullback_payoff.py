"""Gross OHLC price-path scenarios, not executable fills or portfolio P&L.

The reference is immediate completed F1.open. Structural stops lie a nominal
0.25 price points beyond B/R. Ambiguous dual-touch bars retain payoff bounds.
"""

from __future__ import annotations

from collections import deque
import csv
from dataclasses import dataclass, fields
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from pullbacks import LEDGER_COLUMNS as PULLBACK_LEDGER_COLUMNS, Pullback, ledger_row as pullback_ledger_row
from pullback_analysis import DIRECTIONS, EARLIER_LEG_BUCKETS, GROUP_COLUMNS, _validate_event, earlier_leg_bucket
from timeframes import Timeframe, reporting_slices
from trends import Bar, COMPLETED_STATUSES

TARGET_MULTIPLES = (1, 2)
HORIZON_CANDLES = 10
STOP_BUFFER = Decimal("0.25")


@dataclass(frozen=True, slots=True)
class Payoff:
    setting_ticks: int
    direction: str
    source_row: int
    available_at: datetime
    session_date: date
    earlier_observed_length: int
    earlier_start_known: bool
    target_multiple: int
    horizon_candles: int
    entry_source_row: int | None
    entry_start_timestamp: datetime | None
    entry_price: Decimal | None
    stop_price: Decimal
    target_price: Decimal | None
    risk_points: Decimal | None
    status: str
    exit_reason: str
    bars_observed: int
    exit_source_row: int | None
    exit_available_at: datetime | None
    exit_price: Decimal | None
    payoff_lower_r: Decimal | None
    payoff_upper_r: Decimal | None

    @property
    def earlier_exact_length(self) -> int | None:
        return self.earlier_observed_length if self.earlier_start_known else None


PAYOFF_LEDGER_COLUMNS = (*(item.name for item in fields(Payoff)), "earlier_exact_length")
LEDGER_COLUMNS = PAYOFF_LEDGER_COLUMNS
PAYOFF_COLUMNS = (
    *GROUP_COLUMNS, "target_multiple", "horizon_candles", "event_count", "valid_entry_count",
    "invalid_entry_count", "unknown_entry_count", "known_outcome_count", "unknown_outcome_count",
    "resolved_count", "ambiguous_count", "marked_count", "target_touch_count", "stop_touch_count",
    "gap_target_count", "gap_stop_count", "win_lower_numerator", "win_upper_numerator", "denominator",
    "win_rate_lower", "win_rate_upper", "payoff_lower_sum_r", "payoff_upper_sum_r",
    "mean_lower_r", "mean_upper_r", "sessions_with_events", "sessions_with_valid_entry",
    "sessions_with_known_outcome", "units",
)


def payoff_ledger_row(result: Payoff) -> dict[str, str]:
    values = {item.name: getattr(result, item.name) for item in fields(Payoff)}
    values["earlier_exact_length"] = result.earlier_exact_length
    def serialize(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, datetime):
            return value.isoformat(sep=" ")
        return str(value)
    return {name: serialize(values[name]) for name in PAYOFF_LEDGER_COLUMNS}


ledger_row = payoff_ledger_row


def load_pullback_ledger(path: Path | str) -> Iterator[Pullback]:
    """Read exact typed core rows and refuse schema/computed-field drift."""
    previous = 0
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(PULLBACK_LEDGER_COLUMNS):
            raise ValueError("pullback ledger header does not match the frozen schema")
        for raw in reader:
            if None in raw or any(value is None for value in raw.values()):
                raise ValueError("pullback ledger row has wrong column count")
            values = {}
            for item in fields(Pullback):
                value, kind = raw[item.name], str(item.type)
                if value == "" and "None" in kind:
                    parsed = None
                elif kind == "bool":
                    if value not in ("true", "false"):
                        raise ValueError("pullback ledger booleans must be lowercase literals")
                    parsed = value == "true"
                elif kind.startswith("datetime"):
                    parsed = datetime.fromisoformat(value)
                    if parsed.tzinfo is not None:
                        raise ValueError("pullback ledger timestamps must be naive NY wall time")
                elif kind == "date":
                    parsed = date.fromisoformat(value)
                elif kind.startswith("Decimal"):
                    parsed = Decimal(value)
                    if not parsed.is_finite():
                        raise ValueError("pullback ledger prices must be finite")
                elif kind.startswith("int"):
                    parsed = int(value)
                else:
                    parsed = value
                values[item.name] = parsed
            event = Pullback(**values)
            _validate_event(event)
            if event.source_row <= previous or pullback_ledger_row(event) != raw:
                raise ValueError("pullback ledger order or exact derived strings changed")
            previous = event.source_row
            yield event


@dataclass(slots=True)
class _Scenario:
    event: Pullback
    multiple: int
    horizon: int
    stop: Decimal
    entry_bar: Bar | None = None
    risk: Decimal | None = None
    target: Decimal | None = None
    observed: int = 0
    result: Payoff | None = None

    def finish(self, status: str, reason: str, bar: Bar | None = None,
               price: Decimal | None = None, lower: Decimal | None = None,
               upper: Decimal | None = None, *, at_open: bool = False) -> None:
        event, entry = self.event, self.entry_bar
        self.result = Payoff(
            event.setting_ticks, event.direction, event.source_row, event.available_at, event.session_date,
            event.earlier_observed_length, event.earlier_start_known, self.multiple, self.horizon,
            entry.source_row if entry else None, entry.start_timestamp if entry else None,
            entry.open if entry else None, self.stop, self.target, self.risk, status, reason, self.observed,
            bar.source_row if bar else None,
            (bar.start_timestamp if at_open else bar.completion_timestamp) if bar else None,
            price, lower, upper,
        )

    def observe(self, bar: Bar) -> None:
        if self.result is not None:
            return
        bullish = self.event.direction == "bullish"
        sign = Decimal(1 if bullish else -1)
        if self.entry_bar is None:
            if bar.source_row != self.event.source_row + 1:
                self.finish("unknown", "f1_unavailable")
                return
            if (bar.source_row, bar.start_timestamp, bar.completion_timestamp, bar.open, bar.high, bar.low, bar.close) != (
                self.event.f1_source_row, self.event.f1_start_timestamp, self.event.f1_available_at,
                self.event.f1_open, self.event.f1_high, self.event.f1_low, self.event.f1_close,
            ):
                raise ValueError("core event F1 differs from the payoff source bar")
            self.entry_bar = bar
            self.risk = sign * (bar.open - self.stop)
            if self.risk <= 0:
                self.finish("invalid", "nonpositive_entry_to_stop_risk")
                return
            self.target = bar.open + sign * self.risk * Decimal(self.multiple)
        self.observed += 1
        stop_open = bar.open <= self.stop if bullish else bar.open >= self.stop
        target_open = bar.open >= self.target if bullish else bar.open <= self.target
        if stop_open or target_open:
            value = sign * (bar.open - self.entry_bar.open) / self.risk
            self.finish("resolved", "stop_open_gap" if stop_open else "target_open_gap", bar,
                        bar.open, value, value, at_open=True)
            return
        stop_touch = bar.low <= self.stop if bullish else bar.high >= self.stop
        target_touch = bar.high >= self.target if bullish else bar.low <= self.target
        if stop_touch and target_touch:
            self.finish("ambiguous", "both_touch", bar, lower=Decimal(-1), upper=Decimal(self.multiple))
        elif stop_touch:
            self.finish("resolved", "stop_touch", bar, self.stop, Decimal(-1), Decimal(-1))
        elif target_touch:
            self.finish("resolved", "target_touch", bar, self.target, Decimal(self.multiple), Decimal(self.multiple))
        elif self.observed == self.horizon:
            value = sign * (bar.close - self.entry_bar.open) / self.risk
            self.finish("marked", "horizon_close", bar, bar.close, value, value)


def evaluate_payoffs(events: Iterable[Pullback] | Path | str, bars: Iterable[Bar], setting: int,
                     *, targets: Iterable[int] = TARGET_MULTIPLES,
                     horizon: int = HORIZON_CANDLES, buffer: Decimal = STOP_BUFFER) -> Iterator[Payoff]:
    """Join ordered selected setups to a second original-bar stream.

    Results are in R source-row order then target order even when a later
    setup resolves sooner. At most the physical horizon's setups stay active.
    """
    targets = tuple(targets)
    if setting not in (4, 5, 6):
        raise ValueError("setting must be one of 4, 5, 6 ticks")
    if not targets or len(set(targets)) != len(targets) or any(type(n) is not int or n < 1 for n in targets):
        raise ValueError("targets must be distinct positive integer R multiples")
    if type(horizon) is not int or horizon < 1 or not isinstance(buffer, Decimal) or not buffer.is_finite() or buffer <= 0:
        raise ValueError("horizon must be positive and stop buffer a finite positive Decimal")
    iterator = iter(load_pullback_ledger(events) if isinstance(events, (Path, str)) else events)
    candidate = next(iterator, None)
    queued: deque[list[_Scenario]] = deque()
    previous: Bar | None = None
    last_event_row = 0

    def drain() -> Iterator[Payoff]:
        while queued and all(item.result is not None for item in queued[0]):
            for item in queued.popleft():
                yield item.result

    for bar in bars:
        if bar.setting_ticks != setting or type(bar.source_row) is not int or bar.source_row < 1:
            raise ValueError("bar setting or source row does not match the payoff stream")
        boundary = None
        if previous is not None:
            if bar.source_row <= previous.source_row:
                raise ValueError("bar source rows must be strictly increasing")
            if bar.source_row != previous.source_row + 1:
                boundary = "source_row_gap"
            elif bar.session_date != previous.session_date:
                boundary = "session_boundary"
        previous = bar
        barrier = boundary or (None if bar.primary_eligible and bar.completion_status in COMPLETED_STATUSES
                               else bar.barrier_reason or f"completion_status:{bar.completion_status or 'missing'}")
        if barrier is not None:
            for scenarios in queued:
                for scenario in scenarios:
                    if scenario.result is None:
                        scenario.finish("unknown", barrier)
        else:
            if bar.completion_timestamp is None or bar.start_timestamp.tzinfo is not None or bar.completion_timestamp.tzinfo is not None:
                raise ValueError("eligible completed payoff bars need naive completion timestamps")
            for scenarios in queued:
                for scenario in scenarios:
                    scenario.observe(bar)
        yield from drain()
        if candidate is not None and candidate.source_row < bar.source_row:
            raise ValueError("selected event row is absent from the payoff bar stream")
        if candidate is not None and candidate.source_row == bar.source_row:
            event = candidate
            _validate_event(event)
            if event.setting_ticks != setting or event.source_row <= last_event_row:
                raise ValueError("events must be distinct and ordered within one setting")
            if barrier or event.session_date != bar.session_date or event.available_at != bar.completion_timestamp:
                raise ValueError("selected R does not match its eligible payoff source bar")
            if (event.open, event.high, event.low, event.close) != (bar.open, bar.high, bar.low, bar.close):
                raise ValueError("selected R prices differ from the payoff source bar")
            stop = min(event.pullback_low, event.low) - buffer if event.direction == "bullish" else max(event.pullback_high, event.high) + buffer
            scenarios = [_Scenario(event, multiple, horizon, stop) for multiple in targets]
            if not event.f1_known:
                for scenario in scenarios:
                    scenario.finish("unknown", "f1_unavailable")
            queued.append(scenarios)
            last_event_row = event.source_row
            candidate = next(iterator, None)
            yield from drain()
    if candidate is not None:
        raise ValueError("selected event row is absent from the payoff bar stream")
    for scenarios in queued:
        for scenario in scenarios:
            if scenario.result is None:
                scenario.finish("unknown", "export_end")
    yield from drain()


def analyze_payoffs(results: Iterable[Payoff], settings: Sequence[int], timeframes: Sequence[Timeframe],
                    years: Iterable[int] = range(2019, 2027), targets: Iterable[int] = TARGET_MULTIPLES,
                    horizon: int = HORIZON_CANDLES) -> list[dict]:
    """All chart/year/window/direction/earlier-A cells, recomputed from counts."""
    settings, years, targets = tuple(settings), tuple(years), tuple(targets)
    if not settings or len(set(settings)) != len(settings) or any(setting not in (4, 5, 6) for setting in settings):
        raise ValueError("settings must be distinct 4/5/6 tick charts")
    if len(set(years)) != len(years) or any(type(year) is not int for year in years):
        raise ValueError("years must contain distinct integers")
    if not targets or len(set(targets)) != len(targets) or any(type(n) is not int or n < 1 for n in targets):
        raise ValueError("targets must contain distinct positive integers")
    if type(horizon) is not int or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    windows = ("all_hours", *(frame.id for frame in timeframes))
    if len(set(windows)) != len(windows):
        raise ValueError("timeframe ids must be distinct")
    cells: dict[tuple, dict] = {}
    session_ids: dict[date, int] = {}
    for result in results:
        if result.setting_ticks not in settings or result.session_date.year not in years or result.target_multiple not in targets or result.horizon_candles != horizon:
            raise ValueError("payoff belongs to an undeclared chart/year/target/horizon")
        if result.status not in ("resolved", "ambiguous", "marked", "unknown", "invalid") or result.direction not in DIRECTIONS[:2]:
            raise ValueError("invalid payoff status or direction")
        known = result.status in ("resolved", "ambiguous", "marked")
        bounds = (result.payoff_lower_r, result.payoff_upper_r)
        if any(value is None for value in bounds) != all(value is None for value in bounds) or known != all(value is not None for value in bounds):
            raise ValueError("known payoffs require both bounds; unresolved payoffs have no bounds")
        if known and any(not isinstance(value, Decimal) or not value.is_finite() for value in bounds):
            raise ValueError("payoff bounds must be finite Decimals")
        if known and (result.payoff_lower_r > result.payoff_upper_r or result.risk_points is None or result.risk_points <= 0):
            raise ValueError("known payoff bounds or risk are invalid")
        bit = 1 << session_ids.setdefault(result.session_date, len(session_ids))
        bucket = earlier_leg_bucket(result)
        for section in reporting_slices(result.available_at, result.session_date, timeframes):
            for direction in (result.direction, "all"):
                for cohort in ("all", bucket):
                    key = (result.setting_ticks, section.year, section.timeframe_id, direction, cohort, result.target_multiple)
                    cell = cells.setdefault(key, {"events": 0, "valid": 0, "invalid": 0, "unknown_entry": 0,
                        "known": 0, "unknown": 0, "resolved": 0, "ambiguous": 0, "marked": 0,
                        "target_touch": 0, "stop_touch": 0, "gap_target": 0, "gap_stop": 0,
                        "win_lower": 0, "win_upper": 0, "lower_sum": Decimal(0), "upper_sum": Decimal(0),
                        "sessions": 0, "valid_sessions": 0, "known_sessions": 0})
                    cell["events"] += 1
                    cell["sessions"] |= bit
                    if result.risk_points is not None and result.risk_points > 0:
                        cell["valid"] += 1
                        cell["valid_sessions"] |= bit
                    if result.status == "invalid":
                        cell["invalid"] += 1
                    elif result.status == "unknown":
                        cell["unknown"] += 1
                        cell["unknown_entry"] += int(result.entry_price is None)
                    else:
                        cell["known"] += 1
                        cell["known_sessions"] |= bit
                        cell[result.status] += 1
                        cell["lower_sum"] += result.payoff_lower_r
                        cell["upper_sum"] += result.payoff_upper_r
                        cell["win_lower"] += int(result.payoff_lower_r > 0)
                        cell["win_upper"] += int(result.payoff_upper_r > 0)
                        cell["target_touch"] += int(result.exit_reason == "target_touch")
                        cell["stop_touch"] += int(result.exit_reason == "stop_touch")
                        cell["gap_target"] += int(result.exit_reason == "target_open_gap")
                        cell["gap_stop"] += int(result.exit_reason == "stop_open_gap")
    rows = []
    for setting in settings:
        for year in (None, *years):
            for window in windows:
                for direction in DIRECTIONS:
                    for cohort in EARLIER_LEG_BUCKETS:
                        for target in targets:
                            key = (setting, year, window, direction, cohort, target)
                            c = cells.get(key, {})
                            known = c.get("known", 0)
                            lower, upper = c.get("lower_sum", Decimal(0)), c.get("upper_sum", Decimal(0))
                            rows.append({**dict(zip(GROUP_COLUMNS, key[:5])), "target_multiple": target,
                                "horizon_candles": horizon, "event_count": c.get("events", 0), "valid_entry_count": c.get("valid", 0),
                                "invalid_entry_count": c.get("invalid", 0), "unknown_entry_count": c.get("unknown_entry", 0),
                                "known_outcome_count": known, "unknown_outcome_count": c.get("unknown", 0),
                                "resolved_count": c.get("resolved", 0), "ambiguous_count": c.get("ambiguous", 0), "marked_count": c.get("marked", 0),
                                "target_touch_count": c.get("target_touch", 0), "stop_touch_count": c.get("stop_touch", 0),
                                "gap_target_count": c.get("gap_target", 0), "gap_stop_count": c.get("gap_stop", 0),
                                "win_lower_numerator": c.get("win_lower", 0), "win_upper_numerator": c.get("win_upper", 0), "denominator": known,
                                "win_rate_lower": c.get("win_lower", 0)/known if known else None,
                                "win_rate_upper": c.get("win_upper", 0)/known if known else None,
                                "payoff_lower_sum_r": lower, "payoff_upper_sum_r": upper,
                                "mean_lower_r": float(lower/known) if known else None,
                                "mean_upper_r": float(upper/known) if known else None,
                                "sessions_with_events": c.get("sessions", 0).bit_count(),
                                "sessions_with_valid_entry": c.get("valid_sessions", 0).bit_count(),
                                "sessions_with_known_outcome": c.get("known_sessions", 0).bit_count(),
                                "units": "gross_ohlc_price_path_R_proxy"})
    return rows
