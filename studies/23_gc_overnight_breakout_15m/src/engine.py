"""Causal 15-minute decisions with observed 1-minute execution evidence.

This is an authored approximation, not native TradingView verification. No
Phase 2 entry or filter is implemented. Datetimes are aware UTC; ledgers use ISO
strings. The caller owns pinned inputs and the expected-market-minute calendar.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Any, Callable, Iterable, Mapping
from zoneinfo import ZoneInfo

UTC = timezone.utc
BROKER = timezone(timedelta(hours=3))
NY = ZoneInfo("America/New_York")
MINUTE = timedelta(minutes=1)


def iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def round_tick(price: float, tick: float = 0.1) -> float:
    """Positive instrument price; ties round upward, as Pine mintick rounding."""
    if tick <= 0 or not math.isfinite(price):
        raise ValueError("finite price and positive tick required")
    return float((Decimal(str(price)) / Decimal(str(tick))).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal(str(tick)))


def quantity_at_boundary(equity: float, boundary: float, stop: float, *,
                         point_value: float = 100, risk_percent: float = 1,
                         max_leverage: float = 10, step: float = 1,
                         minimum: float = 1) -> float:
    if step <= 0 or minimum <= 0 or point_value <= 0:
        raise ValueError("positive contract economics required")
    risk = abs(boundary - stop)
    if equity <= 0 or boundary <= 0 or risk <= 0:
        return 0.0
    raw = equity * risk_percent / 100 / (risk * point_value)
    capped = min(raw, equity * max_leverage / (boundary * point_value))
    quantity = math.floor(max(capped, 0) / step + 1e-9) * step
    return quantity if quantity >= minimum else 0.0


def entry_cohort(timestamp: datetime) -> dict[str, Any]:
    if timestamp.tzinfo is None:
        raise ValueError("entry time must be timezone-aware")
    local = timestamp.astimezone(NY)
    minutes = local.hour * 60 + local.minute
    session = ("asia" if minutes >= 1200 or minutes < 120 else
               "london" if minutes < 540 else
               "new_york" if 570 <= minutes < 960 else "outside_named_sessions")
    broker = timestamp.astimezone(BROKER)
    start = broker.replace(hour=7, minute=0, second=0, microsecond=0)
    return {"entry_year": local.year, "entry_date_ny": local.date().isoformat(),
            "entry_time_ny": local.isoformat(), "entry_session": session,
            "entry_hour": local.hour, "entry_weekday": local.weekday(),
            "entry_weekday_name": local.strftime("%A"),
            "minutes_from_trading_start": (broker - start).total_seconds() / 60}


def regular_gc_expected(timestamp: datetime) -> bool:
    """Regular weekly schedule only; caller must supply holiday-aware calendar."""
    local = timestamp.astimezone(NY)
    weekday = local.weekday()
    if weekday == 5 or (weekday == 6 and local.hour < 18):
        return False
    if weekday == 4 and local.hour >= 17:
        return False
    return not (17 <= local.hour < 18)


@dataclass(frozen=True, slots=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    contract: str
    available_at: datetime | None = None
    # True means the input audit identified missing EXPECTED evidence before
    # this bar. Scheduled closures must not set it.
    gap_before_expected: bool = False


@dataclass(frozen=True)
class EngineConfig:
    model: str = "validated_native"
    ordering: str = "source_ohlc"
    sizing: str = "one_contract"
    tick_size: float = 0.1
    point_value: float = 100.0
    minimum_quantity: float = 1.0
    quantity_step: float = 1.0
    stop_percent: float = 1.0
    commission_per_side: float = 2.5
    commission_cash_per_order: float | None = None
    slippage_ticks: int = 1
    initial_capital: float = 10000.0
    risk_percent: float = 1.0
    max_leverage: float = 10.0
    signal_minutes: int = 15
    execution_minutes: int = 1
    timed_exit_priority: str = "market_first"

    def __post_init__(self) -> None:
        if self.model not in {"validated_native", "native_strategy_approx", "indicator_approx"}:
            raise ValueError("unknown execution model")
        if self.ordering not in {"source_ohlc", "high_first", "low_first"}:
            raise ValueError("unknown intrabar ordering")
        if self.sizing not in {"one_contract", "source_account"}:
            raise ValueError("unknown sizing model")
        if self.signal_minutes != 15 or self.execution_minutes not in {1, 15}:
            raise ValueError("Phase 1 requires 15m decisions and 1m or source15m execution")
        if self.slippage_ticks not in {0, 1, 2}:
            raise ValueError("only prespecified 0/1/2 tick scenarios permitted")
        if min(self.tick_size, self.point_value, self.minimum_quantity, self.quantity_step, self.stop_percent) <= 0:
            raise ValueError("positive instrument/settings values required")
        if self.commission_per_side < 0 or (self.commission_cash_per_order is not None and self.commission_cash_per_order < 0):
            raise ValueError("costs must be nonnegative")
        if self.timed_exit_priority not in {"market_first", "stop_first"}:
            raise ValueError("unknown competing exit priority")


@dataclass
class ExecutionResult:
    trades: list[dict[str, Any]] = field(default_factory=list)
    orders: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    days: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class _Orders:
    day: str
    contract: str
    high: float
    low: float
    long_stop: float
    short_stop: float
    long_quantity: float
    short_quantity: float
    submitted: datetime


@dataclass
class _Position:
    row: dict[str, Any]
    direction: int
    entry: float
    stop: float
    entry_bucket: datetime
    entry_timestamp: datetime
    quantity: float
    mfe: float = 0.0
    mae: float = 0.0
    reset_done: bool = False
    market_queued: bool = False
    reset_stop_queued: bool = False


def _bucket(timestamp: datetime) -> datetime:
    return timestamp.replace(minute=(timestamp.minute // 15) * 15, second=0, microsecond=0)


def _mark(pos: _Position, price: float) -> None:
    move = pos.direction * (price - pos.entry)
    pos.mfe = max(pos.mfe, move)
    pos.mae = max(pos.mae, -move)


def _path(bar: Bar, ordering: str) -> tuple[float, float, float, float]:
    high_first = ordering == "high_first" or (ordering == "source_ohlc" and bar.high - bar.open < bar.open - bar.low)
    return (bar.open, bar.high, bar.low, bar.close) if high_first else (bar.open, bar.low, bar.high, bar.close)


def run_backtest(bars: Iterable[Bar], config: EngineConfig | None = None, *,
                 range_eligibility: Mapping[str, Mapping[str, Any]] | None = None,
                 expected_minute: Callable[[datetime], bool] | None = None) -> ExecutionResult:
    """Run one frozen baseline scenario without reading/writing any files.

    ``range_eligibility`` is keyed by fixed-GMT+3 ISO broker date, with ``eligible``
    and ``reason`` (or ``exclusion_reason``), expected/observed_range_minutes.
    Consume it only at scheduled 07:00 range completion. Never include later
    outcome missingness in that causal mask. Missing bars can be annotated with
    ``gap_before_expected`` or detected using the explicit expected-minute
    predicate. With neither, regular weekly GC hours are the conservative default;
    a historical run MUST provide a holiday-aware predicate or audit annotations.
    Native approximation ignores gap censoring, but all models enforce roll
    barriers before comparing different-contract prices.
    """
    cfg = config or EngineConfig()
    calendar = expected_minute or regular_gc_expected
    result = ExecutionResult()
    roster: dict[str, dict[str, Any]] = {}
    first_day: str | None = None
    range_day: str | None = None
    range_high: float | None = None
    range_low: float | None = None
    range_contract: str | None = None
    range_mixed = False
    range_minutes = 0
    traded_days: set[str] = set()
    unknown_days: set[str] = set()
    roll_blocked_days: set[str] = set()
    orders: _Orders | None = None
    position: _Position | None = None
    equity = cfg.initial_capital
    previous: Bar | None = None
    candle: dict[str, Any] | None = None
    slip = cfg.tick_size * cfg.slippage_ticks

    def day_row(day: str) -> dict[str, Any]:
        if day not in roster:
            roster[day] = {"broker_day": day, "range_high": None, "range_low": None,
                "range_width": None, "valid_range": False, "eligible": False,
                "exclusion_reason": "first_loaded_broker_day" if day == first_day else None, "accepted_breakouts": 0,
                "executable_fills": 0, "completed_trades": 0, "censored_trades": 0,
                "quantity_skips": 0, "quantity_skip_long": False,
                "quantity_skip_short": False, "no_trade": False,
                "unknown_outcome": False, "observed_range_minutes": 0,
                "expected_range_minutes": None, "model": cfg.model,
                "ordering": cfg.ordering, "sizing": cfg.sizing}
        return roster[day]

    def order_event(action: str, when: datetime, reason: str | None = None) -> None:
        if orders is None:
            return
        result.orders.append({"broker_day": orders.day, "contract": orders.contract,
            "action": action, "time": iso(when), "reason": reason,
            "range_high": orders.high, "range_low": orders.low,
            "long_stop": orders.long_stop, "short_stop": orders.short_stop,
            "long_quantity": orders.long_quantity, "short_quantity": orders.short_quantity,
            "submitted_at": iso(orders.submitted), "oca_group": "RB"})

    def close_position(raw: float | None, when: datetime, reason: str,
                       precision: str = "observed_open", *, censored: bool = False,
                       competing: bool = False) -> None:
        nonlocal position, equity
        if position is None:
            return
        p = position
        row = p.row
        row.update({"status": "censored" if censored else "completed",
                    "exit_reason": None if censored else reason,
                    "censor_reason": reason if censored else None,
                    "last_observed_at": iso(when), "competing_exit_orders": competing,
                    "mfe_points": p.mfe, "mae_points": p.mae,
                    "excursions_complete": not censored})
        if censored:
            row.update({"exit_time": None, "exit_time_latest": None,
                        "exit_price_raw": None, "exit_price": None,
                        "gross_points": None, "gross_dollars": None,
                        "raw_price_points": None, "raw_price_dollars": None,
                        "commission_dollars": None, "net_points": None, "net_dollars": None,
                        "gross_r": None, "net_r": None, "source_style_r": None,
                        "holding_minutes": None, "holding_bars": None,
                        "holding_minutes_lower": None, "holding_minutes_upper": None,
                        "observed_holding_minutes": (when - p.entry_timestamp).total_seconds() / 60})
            day_row(row["broker_day"])["censored_trades"] += 1
            day_row(row["broker_day"])["unknown_outcome"] = True
        else:
            assert raw is not None
            exit_price = raw - p.direction * slip
            _mark(p, raw)
            gross = p.direction * (exit_price - p.entry)
            raw_move = p.direction * (raw - row["entry_price_raw"])
            commission = (2 * cfg.commission_cash_per_order if cfg.commission_cash_per_order is not None else 2 * cfg.commission_per_side * p.quantity)
            net_dollars = gross * cfg.point_value * p.quantity - commission
            risk = row["risk_initial_dollars"]
            source_risk = abs(p.entry - p.stop) * cfg.point_value * p.quantity
            entry_latest = p.entry_timestamp + timedelta(minutes=cfg.execution_minutes) if row["entry_time_precision"] == "within_bar" else p.entry_timestamp
            exit_latest = when + timedelta(minutes=cfg.execution_minutes) if precision == "within_bar" else when
            row.update({"exit_time": iso(when), "exit_time_latest": iso(when + timedelta(minutes=cfg.execution_minutes)) if precision == "within_bar" else iso(when),
                "exit_time_precision": precision, "exit_price_raw": raw, "exit_price": exit_price,
                "gross_points": gross, "gross_dollars": gross * cfg.point_value * p.quantity,
                "raw_price_points": raw_move, "raw_price_dollars": raw_move * cfg.point_value * p.quantity,
                "commission_dollars": commission, "net_points": net_dollars / (cfg.point_value * p.quantity),
                "net_dollars": net_dollars, "gross_r": gross * cfg.point_value * p.quantity / risk if risk else None,
                "net_r": net_dollars / risk if risk else None,
                "source_style_r": net_dollars / source_risk if source_risk > 0 else None,
                "source_risk_dollars": source_risk if source_risk > 0 else None,
                "holding_minutes": (when - p.entry_timestamp).total_seconds() / 60,
                "holding_minutes_lower": max(0, (when - entry_latest).total_seconds() / 60),
                "holding_minutes_upper": max(0, (exit_latest - p.entry_timestamp).total_seconds() / 60),
                "holding_bars": int((_bucket(when) - p.entry_bucket).total_seconds() / 900),
                "mfe_points": p.mfe, "mae_points": p.mae})
            day_row(row["broker_day"])["completed_trades"] += 1
            equity += net_dollars
        result.trades.append(row)
        result.events.append({"trade_id": row["trade_id"], "event": "censor" if censored else "exit", "time": iso(when), "reason": reason, "raw_price": raw})
        position = None

    def start_position(direction: int, raw: float, bar: Bar, precision: str) -> None:
        nonlocal position, orders
        assert orders is not None
        o = orders
        day = bar.timestamp.astimezone(BROKER).date().isoformat()
        quantity = o.long_quantity if direction == 1 else o.short_quantity
        initial_stop = o.long_stop if direction == 1 else o.short_stop
        entry = raw + direction * slip
        risk = direction * (entry - initial_stop)
        row = {"trade_id": f"{cfg.model}:{cfg.sizing}:{cfg.ordering}:{day}:{len(result.trades) + 1}",
            "broker_day": day, "order_broker_day": o.day, "contract": o.contract,
            "side": "long" if direction == 1 else "short", "direction": direction,
            "quantity": quantity, "status": "open", "order_submitted_at": iso(o.submitted),
            "order_active_at": iso(o.submitted), "entry_time": iso(bar.timestamp),
            "entry_time_latest": iso(bar.timestamp + timedelta(minutes=cfg.execution_minutes)) if precision == "within_bar" else iso(bar.timestamp),
            "entry_time_precision": precision, "signal_available_at": iso(_bucket(bar.timestamp) + timedelta(minutes=15)),
            "entry_price_raw": raw, "entry_price": entry, "initial_stop": initial_stop,
            "initial_stop_active_at": iso(o.submitted), "reset_stop": None, "reset_stop_active_at": None,
            "risk_initial_points": risk if risk > 0 else None,
            "risk_initial_dollars": risk * cfg.point_value * quantity if risk > 0 else None,
            "risk_effective_points": risk if risk > 0 else None,
            "risk_effective_dollars": risk * cfg.point_value * quantity if risk > 0 else None,
            "source_risk_dollars": risk * cfg.point_value * quantity if risk > 0 else None,
            "planned_boundary_risk_points": direction * ((o.high if direction == 1 else o.low) - initial_stop),
            "mfe_points": 0.0, "mae_points": 0.0, "ambiguous": False,
            "excursion_ambiguous": False, "gap_entry": raw != (o.high if direction == 1 else o.low),
            "stale_entry": o.day != day or not 7 <= bar.timestamp.astimezone(BROKER).hour < 20,
            "model": cfg.model, "ordering": cfg.ordering, "sizing": cfg.sizing,
            "slippage_ticks": cfg.slippage_ticks, "commission_per_side": cfg.commission_per_side,
            "account_equity_at_submission": equity, "censor_reason": None}
        row.update(entry_cohort(bar.timestamp))
        latest_cohort = entry_cohort(bar.timestamp + timedelta(minutes=cfg.execution_minutes) - timedelta(microseconds=1)) if precision == "within_bar" else entry_cohort(bar.timestamp)
        row["entry_cohort_ambiguous"] = any(row[k] != latest_cohort[k] for k in ("entry_year", "entry_session", "entry_hour", "entry_weekday"))
        position = _Position(row, direction, entry, initial_stop, _bucket(bar.timestamp), bar.timestamp, quantity)
        # Native source detects an entry at the candle close, using current day;
        # same-candle exits also consume that current day. Immediate marking is
        # equivalent on regular data and preserves one-trade-per-day after gaps.
        traded_days.add(day)
        dr = day_row(day)
        dr["accepted_breakouts"] += 1
        dr["executable_fills"] += 1
        order_event("first_fill_cancels_opposite", bar.timestamp, "oca")
        result.events.append({"trade_id": row["trade_id"], "event": "entry", "time": iso(bar.timestamp), "raw_price": raw, "actual_price": entry})
        orders = None

    def flush_candle() -> None:
        nonlocal orders, range_high, range_low, range_day, range_contract, range_mixed, range_minutes
        if candle is None:
            return
        opening = candle["start"].astimezone(BROKER)
        end = candle["start"] + timedelta(minutes=15)
        next_clock = end.astimezone(BROKER)
        day = opening.date().isoformat()
        dr = day_row(day)
        if range_day != day:
            range_day, range_high, range_low = day, None, None
            range_contract, range_mixed, range_minutes = None, False, 0
        if opening.hour < 7:
            range_high = candle["high"] if range_high is None else max(range_high, candle["high"])
            range_low = candle["low"] if range_low is None else min(range_low, candle["low"])
            range_minutes += candle["observed_minutes"]
            if range_contract is None:
                range_contract = candle["contract"]
            range_mixed |= range_contract != candle["contract"] or candle["mixed"]
        dr.update({"range_high": range_high, "range_low": range_low,
                   "range_width": range_high - range_low if range_high is not None and range_low is not None else None,
                   "observed_range_minutes": range_minutes})
        range_ready = range_high is not None and range_low is not None and range_high > range_low and not range_mixed
        audit = (range_eligibility or {}).get(day, {})
        if next_clock.hour >= 7:
            dr["expected_range_minutes"] = audit.get("expected_range_minutes", audit.get("expected_minutes"))
            allowed = audit.get("eligible", True) if cfg.model == "validated_native" else True
            reason = audit.get("reason", audit.get("exclusion_reason"))
            dr["valid_range"] = bool(range_ready and allowed)
            dr["eligible"] = bool(range_ready and allowed and day != first_day)
            dr["exclusion_reason"] = ("first_loaded_broker_day" if day == first_day else
                "range_contract_transition" if range_mixed else
                reason or "range_quality" if not allowed else
                "invalid_or_missing_range" if not range_ready else None)
        decision_observable = cfg.model != "validated_native" or not candle.get("incomplete_expected", False)
        if not decision_observable:
            # The primary quality overlay does not invent a scheduled close
            # from an earlier minute's last price. Gaps are handled before
            # this call, so affected positions/opportunities are retained as
            # censored/unknown rather than receiving a fabricated decision.
            return
        if position is not None and position.entry_bucket == candle["start"] and not position.reset_done:
            new_stop = round_tick(position.entry * (1 - position.direction * cfg.stop_percent / 100), cfg.tick_size)
            position.stop = new_stop
            position.reset_done = True
            risk = position.direction * (position.entry - new_stop)
            position.row.update({"reset_stop": new_stop, "reset_stop_active_at": iso(end),
                "risk_effective_points": risk if risk > 0 else None,
                "risk_effective_dollars": risk * cfg.point_value * position.quantity if risk > 0 else None,
                "source_risk_dollars": abs(position.entry - new_stop) * cfg.point_value * position.quantity})
            position.reset_stop_queued = position.direction * (candle["close"] - new_stop) <= 0
            result.events.append({"trade_id": position.row["trade_id"], "event": "stop_reset", "time": iso(end), "stop": new_stop, "triggered_at_creation": position.reset_stop_queued})
        if position is not None:
            if next_clock.hour >= 20 or next_clock.hour < 7:
                position.market_queued = True
            if orders is not None:
                order_event("cancel", end, "position_open")
                orders = None
        else:
            next_window = 7 <= next_clock.hour < 20
            if cfg.model == "indicator_approx":
                next_window &= next_clock.date().isoformat() == day
            can_trade = range_ready and next_window and day != first_day and day not in traded_days
            can_trade &= day not in roll_blocked_days and range_contract == candle["contract"]
            if cfg.model == "validated_native":
                can_trade &= dr["eligible"] and day not in unknown_days
            if can_trade:
                assert range_high is not None and range_low is not None and range_contract is not None
                long_stop = round_tick(range_high * (1 - cfg.stop_percent / 100), cfg.tick_size)
                short_stop = round_tick(range_low * (1 + cfg.stop_percent / 100), cfg.tick_size)
                qlong = qshort = 1.0
                if cfg.sizing == "source_account":
                    kw = {"point_value": cfg.point_value, "risk_percent": cfg.risk_percent,
                          "max_leverage": cfg.max_leverage, "step": cfg.quantity_step, "minimum": cfg.minimum_quantity}
                    qlong = quantity_at_boundary(equity, range_high, long_stop, **kw)
                    qshort = quantity_at_boundary(equity, range_low, short_stop, **kw)
                if range_high <= long_stop:
                    qlong = 0
                if range_low >= short_stop:
                    qshort = 0
                dr["quantity_skip_long"] |= qlong < cfg.minimum_quantity
                dr["quantity_skip_short"] |= qshort < cfg.minimum_quantity
                dr["quantity_skips"] = int(dr["quantity_skip_long"]) + int(dr["quantity_skip_short"])
                new = _Orders(day, range_contract, range_high, range_low, long_stop, short_stop, qlong, qshort, end)
                if qlong > 0 or qshort > 0:
                    # Preserve the first submission time when unchanged orders
                    # are resubmitted at later 15m closes.
                    if orders is None or (orders.day, orders.contract, orders.high, orders.low, orders.long_quantity, orders.short_quantity) != (new.day, new.contract, new.high, new.low, new.long_quantity, new.short_quantity):
                        orders = new
                        order_event("submit", end)
                elif orders is not None:
                    order_event("cancel", end, "quantity_below_minimum")
                    orders = None
            elif orders is not None:
                order_event("cancel", end, "setup_ineligible")
                orders = None

    for bar in bars:
        if bar.timestamp.tzinfo is None or (bar.available_at is not None and bar.available_at.tzinfo is None):
            raise ValueError("UTC-aware timestamps required")
        if bar.timestamp.second or bar.timestamp.microsecond or bar.timestamp.minute % cfg.execution_minutes:
            raise ValueError("execution bars must align to minute openings")
        prices = (bar.open, bar.high, bar.low, bar.close)
        if not all(math.isfinite(x) and x > 0 for x in prices) or bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(bar.open, bar.close, bar.high):
            raise ValueError("invalid unadjusted OHLC")
        if not bar.contract:
            raise ValueError("contract identity required")
        if bar.available_at is not None and bar.available_at < bar.timestamp + timedelta(minutes=cfg.execution_minutes):
            raise ValueError("OHLC cannot be available before execution candle closes")
        if previous is not None and bar.timestamp <= previous.timestamp:
            raise ValueError("duplicate or descending timestamp")
        local = bar.timestamp.astimezone(BROKER)
        day = local.date().isoformat()
        if first_day is None:
            first_day = day
        day_row(day)
        bucket = _bucket(bar.timestamp)
        # A fully observed previous candle has a real scheduled close before
        # an ensuing gap. Retain that known decision/reset, then censor the
        # unobserved future. If its closing minute itself is absent, detect
        # and censor the gap first so an earlier price cannot become a close.
        if (candle is not None and candle["start"] != bucket and previous is not None
                and previous.timestamp + timedelta(minutes=cfg.execution_minutes) >= candle["start"] + timedelta(minutes=15)):
            flush_candle()
            candle = None
        if previous is not None:
            changed_contract = bar.contract != previous.contract
            if changed_contract:
                if position is not None:
                    close_position(None, previous.timestamp + timedelta(minutes=cfg.execution_minutes), "contract_transition", censored=True)
                if orders is not None:
                    unknown_days.add(orders.day)
                    day_row(orders.day)["unknown_outcome"] = True
                    order_event("cancel", bar.timestamp, "contract_transition")
                    orders = None
                # A range split across contracts is never execution-eligible.
                if day == previous.timestamp.astimezone(BROKER).date().isoformat():
                    roll_blocked_days.add(day)
                    if local.hour < 7:
                        range_mixed = True
            gap_expected = bar.gap_before_expected
            if not gap_expected and bar.timestamp > previous.timestamp + timedelta(minutes=cfg.execution_minutes):
                cursor = previous.timestamp + timedelta(minutes=cfg.execution_minutes)
                while cursor < bar.timestamp:
                    if calendar(cursor):
                        gap_expected = True
                        break
                    cursor += MINUTE
            if gap_expected and cfg.model == "validated_native":
                if candle is not None:
                    candle["incomplete_expected"] = True
                if position is not None:
                    close_position(None, previous.timestamp + timedelta(minutes=cfg.execution_minutes), "missing_expected_execution_minutes", censored=True)
                if orders is not None:
                    unknown_days.add(orders.day)
                    unknown_days.add(day)
                    day_row(orders.day)["unknown_outcome"] = True
                    order_event("cancel", bar.timestamp, "unobserved_first_fill_unknown")
                    orders = None
                result.events.append({"event": "missing_expected_evidence", "start": iso(previous.timestamp + timedelta(minutes=cfg.execution_minutes)), "end": iso(bar.timestamp), "broker_day": day})
        if candle is not None and candle["start"] != bucket:
            flush_candle()
            candle = None
        if cfg.model == "indicator_approx":
            if position is not None and (position.market_queued or day != position.row["broker_day"] or local.hour >= 20 or local.hour < 7):
                close_position(bar.open, bar.timestamp, "time" if position.market_queued else "indicator_missing_bar_fallback")
            if orders is not None and (orders.day != day or not 7 <= local.hour < 20 or day in traded_days):
                order_event("cancel", bar.timestamp, "indicator_actual_window_gate")
                orders = None
        if position is not None:
            p = position
            through = p.direction * (bar.open - p.stop) <= 0
            competing = p.market_queued and (through or p.reset_stop_queued)
            if p.market_queued:
                reason = "stop" if competing and cfg.timed_exit_priority == "stop_first" else "time"
                close_position(bar.open, bar.timestamp, reason, competing=competing)
            elif p.reset_stop_queued or through:
                close_position(bar.open, bar.timestamp, "stop")
        # Open gap stop entry precedes inferred segments; OCA is consumed once.
        if position is None and orders is not None:
            direction = 1 if bar.open >= orders.high and orders.long_quantity > 0 else -1 if bar.open <= orders.low and orders.short_quantity > 0 else 0
            if direction:
                start_position(direction, bar.open, bar, "observed_open")
        path = _path(bar, cfg.ordering)
        dual = orders is not None and bar.high >= orders.high and bar.low <= orders.low and orders.long_quantity > 0 and orders.short_quantity > 0
        for a, b in zip(path, path[1:]):
            if position is None and orders is not None:
                direction = 1 if b > a and a <= orders.high <= b and orders.long_quantity > 0 else -1 if b < a and b <= orders.low <= a and orders.short_quantity > 0 else 0
                if direction:
                    boundary = orders.high if direction == 1 else orders.low
                    initial = orders.long_stop if direction == 1 else orders.short_stop
                    # Opposite extreme before versus after this inferred fill
                    # may change whether an entry-candle stop executes.
                    ambiguous = dual or (bar.low <= initial if direction == 1 else bar.high >= initial)
                    start_position(direction, boundary, bar, "within_bar")
                    assert position is not None
                    position.row["ambiguous"] = ambiguous
                    a = boundary
            if position is not None:
                p = position
                _mark(p, a)
                through_a = p.direction * (a - p.stop) <= 0
                through_b = p.direction * (b - p.stop) <= 0
                if through_a or through_b:
                    favorable_extreme = bar.high if p.direction == 1 else bar.low
                    p.row["excursion_ambiguous"] |= p.direction * (favorable_extreme - p.entry) > p.mfe
                    close_position(a if through_a else p.stop, bar.timestamp, "stop", "within_bar")
                else:
                    _mark(p, b)
        if candle is None:
            candle = {"start": bucket, "high": bar.high, "low": bar.low, "close": bar.close,
                      "contract": bar.contract, "mixed": False, "observed_minutes": cfg.execution_minutes}
        else:
            candle["high"] = max(candle["high"], bar.high)
            candle["low"] = min(candle["low"], bar.low)
            candle["close"] = bar.close
            candle["mixed"] |= candle["contract"] != bar.contract
            candle["observed_minutes"] += cfg.execution_minutes
        previous = bar
    # An input endpoint inside a still-forming chart candle cannot prove its
    # future close, reset stop, or submission decision.
    if previous is not None and previous.timestamp + timedelta(minutes=cfg.execution_minutes) >= _bucket(previous.timestamp) + timedelta(minutes=15):
        flush_candle()
    if previous is not None and position is not None:
        close_position(None, previous.timestamp + timedelta(minutes=cfg.execution_minutes), "retained_endpoint_open", censored=True)
    if previous is not None and orders is not None:
        dr = day_row(orders.day)
        dr["unknown_outcome"] = True
        order_event("pending_at_endpoint", previous.timestamp + timedelta(minutes=cfg.execution_minutes), "retained_endpoint")
    for day, row in sorted(roster.items()):
        if row["eligible"] and row["accepted_breakouts"] == 0 and not row["unknown_outcome"]:
            row["no_trade"] = True
        result.days.append(row)
    return result


def ordering_bounds(high_first: ExecutionResult, low_first: ExecutionResult) -> list[dict[str, Any]]:
    """Daywise first-fill ordering envelope; censored branches are null.

    On complete regular days, a single stop/no-target baseline can branch in
    its first-fill minute. Later high/low order changes excursions, not P&L.
    Neither this envelope nor a source-OHLC path establishes native parity.
    """
    def index(result: ExecutionResult) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for trade in result.trades:
            out.setdefault(trade["broker_day"], []).append(trade)
        return out
    high, low = index(high_first), index(low_first)
    days = sorted(set(high) | set(low))
    rows = []
    for day in days:
        branches = [high.get(day, []), low.get(day, [])]
        valid = all(len(b) == 1 and b[0]["status"] == "completed" for b in branches)
        net = [b[0]["net_dollars"] for b in branches] if valid else []
        rows.append({"broker_day": day, "high_first_net_dollars": net[0] if valid else None,
                     "low_first_net_dollars": net[1] if valid else None,
                     "adverse_net_dollars": min(net) if valid else None,
                     "favorable_net_dollars": max(net) if valid else None,
                     "outcome_ordering_sensitive": net[0] != net[1] if valid else None,
                     "side_ordering_sensitive": branches[0][0]["side"] != branches[1][0]["side"] if valid else None,
                     "unknown_branch": not valid})
    return rows
