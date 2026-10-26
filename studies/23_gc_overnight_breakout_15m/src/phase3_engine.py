"""Study 23 Phase 3 causal cloud policies, using the immutable Phase 1 parent.

No files or historical inputs are opened here.  The caller supplies pinned parent
rows and a latest-expected-slot cloud timeline.  ``source_ohlc`` deliberately
uses the unchanged Phase 1 authored path, including its binary distance rule.
Native cancellation latency and intraminute ordering remain unverified.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_UP
import math
from typing import Any, Callable, Mapping, Protocol, Sequence

from .engine import Bar, EngineConfig, _path, entry_cohort, iso, round_tick, quantity_at_boundary

UTC = timezone.utc
MINUTE = timedelta(minutes=1)
FIVE = timedelta(minutes=5)
POLICIES = ("BASE", "G1", "G2", "A20", "A50", "X1", "X2", "T50")
MODES = ("standardized", "full_parent", "half_parent", "financed_overlay",
         "diagnostic_1plus1", "parent_1", "parent_2")
_DEFAULT_EQUITY = object()


class CloudTimelineProtocol(Protocol):
    def snapshot(self, at: datetime, contract: str | None = None) -> Any: ...
    def adjacent(self, left: datetime, right: datetime) -> bool: ...
    def for_window(self, start: datetime, end: datetime, *, full_after: datetime | None = None) -> Sequence[Any]: ...


def instant(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    result = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("aware UTC timestamp required")
    return result.astimezone(UTC)


@dataclass(frozen=True)
class Phase3Config:
    scenario: str = "primary-one-tick"
    ordering: str = "source_ohlc"
    tick_size: float = 0.1
    point_value: float = 100.0
    stop_percent: float = 1.0
    commission_per_side: float = 2.5
    slippage_ticks: int = 1
    initial_capital: float = 10000.0
    risk_percent: float = 1.0
    max_leverage: float = 10.0
    margin_percent: float = 5.0
    execution_minutes: int = 1

    def __post_init__(self):
        if self.ordering not in {"source_ohlc", "high_first", "low_first"}:
            raise ValueError("unknown authored ordering")
        if self.execution_minutes != 1 or self.slippage_ticks not in {0, 1, 2}:
            raise ValueError("unsupported frozen execution/cost scenario")
        if min(self.tick_size, self.point_value, self.stop_percent, self.initial_capital,
               self.risk_percent, self.max_leverage, self.margin_percent) <= 0 or self.commission_per_side < 0:
            raise ValueError("positive economics and nonnegative costs required")

    @property
    def slip(self) -> float:
        return self.tick_size * self.slippage_ticks


@dataclass(frozen=True)
class Phase1DayData:
    episode_id: str
    broker_day: str
    baseline_trade: Mapping[str, Any] | None
    minutes: Sequence[Bar]
    cloud: CloudTimelineProtocol
    update_times: Sequence[datetime]
    range_high: float
    range_low: float
    cutoff: datetime
    expected_minute: Callable[[datetime], bool] | None = None
    parent_orders: Sequence[Mapping[str, Any]] = ()
    parent_events: Sequence[Mapping[str, Any]] = ()
    shadow_status: str = "accepted"
    contract: str | None = None

    def __post_init__(self):
        if self.range_high <= self.range_low or instant(self.cutoff) != self.cutoff:
            raise ValueError("frozen positive range and UTC cutoff required")
        if any(b.timestamp <= a.timestamp for a, b in zip(self.minutes, self.minutes[1:])):
            raise ValueError("chronological unique execution bars required")
        if any(b <= a for a, b in zip(self.update_times, self.update_times[1:])):
            raise ValueError("chronological unique source decision updates required")
        if self.shadow_status not in {"accepted", "no_event", "unknown"}:
            raise ValueError("unknown fixed shadow status")
        if self.baseline_trade is None and self.shadow_status == "accepted":
            raise ValueError("accepted shadow requires the frozen parent row")

    @property
    def direction(self) -> int:
        if self.baseline_trade is None:
            return 0
        return int(self.baseline_trade["direction"]) if "direction" in self.baseline_trade else (1 if self.baseline_trade["side"] == "long" else -1)

    @property
    def parent_contract(self) -> str | None:
        return self.contract or (self.baseline_trade.get("contract") if self.baseline_trade else None)


def _parent_state(day: Phase1DayData, at: datetime, *, before_open: bool = True) -> str:
    parent = day.baseline_trade
    if parent is None:
        return "unknown" if day.shadow_status == "unknown" else "not_filled"
    entry = instant(parent["entry_time"])
    if at < entry:
        return "not_filled"
    if parent.get("status") == "completed":
        exit_at = instant(parent["exit_time"])
        exit_upper = instant(parent.get("exit_time_latest")) or exit_at
        if at < exit_at:
            return "open"
        if parent.get("exit_time_precision") == "within_bar" and exit_at <= at < exit_upper:
            return "unknown"
        return "flat"
    censor = instant(parent.get("last_observed_at"))
    return "open" if censor is not None and (at < censor or at == censor and before_open) else "unknown"


def _snapshot_row(snapshot: Any, direction: int, day: Phase1DayData) -> dict[str, Any]:
    bar = getattr(snapshot, "bar", None)
    known = bool(getattr(snapshot, "known", False))
    row = {"status": getattr(snapshot, "status", "unknown"),
           "reason": getattr(snapshot, "reason", ""), "known": known,
           "expected_slot": iso(getattr(snapshot, "expected_slot", None)),
           "available_at": iso(getattr(bar, "available_at", None)),
           "ema20": getattr(bar, "ema20", None), "ema50": getattr(bar, "ema50", None),
           "atr14": getattr(bar, "atr14", None), "close": getattr(bar, "close", None),
           "slope20_3": getattr(snapshot, "slope20_3", None),
           "slope50_3": getattr(snapshot, "slope50_3", None),
           "aligned_count": getattr(snapshot, "aligned_count", None),
           "aligned_duration_minutes": getattr(snapshot, "aligned_duration_minutes", None),
           "alignment_start_known": getattr(snapshot, "alignment_start_known", None),
           "duration_left_censored": getattr(snapshot, "duration_left_censored", None),
           "width_change_3": getattr(snapshot, "width_change_3", None)}
    if not known:
        row.update(direction=None, alignment=None, upper=None, lower=None, width_points=None,
                   width_atr=None, favorable_distance_atr=None, price_cloud=None)
        return row
    fast, slow, close, atr = bar.ema20, bar.ema50, bar.close, bar.atr14
    upper, lower = max(fast, slow), min(fast, slow)
    cloud_direction = 1 if fast > slow else -1 if fast < slow else 0
    row.update(direction=cloud_direction, alignment=direction * cloud_direction if direction else None,
               upper=upper, lower=lower, width_points=upper - lower,
               width_atr=(upper - lower) / atr if atr and atr > 0 else None,
               favorable_distance_atr=direction * (close - (upper if direction == 1 else lower)) / atr if direction and atr and atr > 0 else None,
               price_cloud="above" if close > upper else "below" if close < lower else "inside")
    for name, level in [("high", day.range_high), ("low", day.range_low),
                        ("midpoint", (day.range_high + day.range_low) / 2)]:
        for ema, value in [("ema20", fast), ("ema50", slow)]:
            row[f"{ema}_{name}_confluence"] = abs(value - level) <= .10 * atr if atr and atr > 0 else None
    return row


def gate_admission(snapshot: Any, direction: int, policy: str) -> bool | None:
    if policy not in {"G1", "G2"} or direction not in {-1, 1}:
        raise ValueError("gate policy and side required")
    if not getattr(snapshot, "known", False):
        return None
    bar = snapshot.bar
    aligned = direction * (bar.ema20 - bar.ema50) > 0
    outside = bar.close > max(bar.ema20, bar.ema50) if direction == 1 else bar.close < min(bar.ema20, bar.ema50)
    if not aligned or not outside:
        return False
    if policy == "G1":
        return True
    slopes = (getattr(snapshot, "slope20_3", None), getattr(snapshot, "slope50_3", None))
    return None if any(value is None for value in slopes) else all(direction * value > 0 for value in slopes)


def observe_episode(day: Phase1DayData, config: Phase3Config | None = None) -> list[dict[str, Any]]:
    """All full post-fill 5m observations through cutoff, including invalid slots.

    These are standardized-parent landmarks/context, never financed add signals.
    Raw prior levels price contacts; close-derived cloud only confirms/describes.
    """
    cfg = config or Phase3Config()
    if day.baseline_trade is None:
        return []
    parent = day.baseline_trade
    lower = instant(parent["entry_time"])
    upper = instant(parent.get("entry_time_latest")) or lower
    direction = day.direction
    rows = []
    armed = {20: False, 50: False}
    count = {20: 0, 50: 0}
    contact_unknown = {20: False, 50: False}
    for bar in day.cloud.for_window(lower, day.cutoff, full_after=upper):
        if bar.timestamp < upper or bar.available_at > day.cutoff:
            continue
        prior = day.cloud.snapshot(bar.timestamp, day.parent_contract)
        current = day.cloud.snapshot(bar.available_at, day.parent_contract)
        p = _snapshot_row(prior, direction, day)
        c = _snapshot_row(current, direction, day)
        usable = bool(bar.usable and bar.contract == day.parent_contract)
        open_start = _parent_state(day, bar.timestamp, before_open=False)
        open_close = _parent_state(day, bar.available_at, before_open=True)
        liquidation = (direction * (bar.close - direction * cfg.slip - float(parent["entry_price"])) * cfg.point_value
                       - 2 * cfg.commission_per_side) if usable and open_close == "open" else None
        departed = ((bar.low > p["upper"] if direction == 1 else bar.high < p["lower"])
                    if usable and p["known"] else None)
        row = {"episode_id": day.episode_id, "broker_day": day.broker_day,
               "time": iso(bar.timestamp), "available_at": iso(bar.available_at),
               "contract": bar.contract, "open": bar.open, "high": bar.high,
               "low": bar.low, "close": bar.close, "usable": usable,
               "feature_valid": bool(bar.feature_valid), "quality_reason": bar.quality_reason,
               "known_closure_before": bool(getattr(bar, "known_closure_before", False)),
               "parent_state_at_open": open_start, "parent_state_at_decision": open_close,
               "parent_state_before_next_open": "open" if day.baseline_trade and
                   instant(day.baseline_trade.get("exit_time")) == bar.available_at else open_close,
               "parent_decision_time_bound_ambiguous": open_close == "unknown",
               "open_position_landmark": open_start == "open" and open_close == "open",
               "population": "standardized_parent_post_fill_context",
               "parent_liquidation_net_unit": liquidation, "departure": departed,
               "prior": p, "current": c, "direction": direction}
        row.update({"event_" + k: v for k, v in entry_cohort(bar.available_at).items()})
        for ema in (20, 50):
            level = p[f"ema{ema}"] if p["known"] else None
            penetration = ((bar.low <= level if direction == 1 else bar.high >= level)
                           if usable and level is not None else None)
            contact = bool(armed[ema] and penetration is True)
            if not usable or not p["known"] or (not c["known"] and not contact):
                contact_unknown[ema] = True
            if armed[ema] and penetration is None:
                contact_unknown[ema] = True
                armed[ema] = False
            if contact:
                count[ema] += 1
                armed[ema] = False
            if departed is True and c["known"]:
                armed[ema] = True
            row.update({f"ema{ema}_frozen_level": level, f"ema{ema}_penetration": penetration,
                        f"ema{ema}_contact": contact, f"ema{ema}_contact_count_observed": count[ema],
                        f"ema{ema}_contact_number": count[ema] if contact and not contact_unknown[ema] else None,
                        f"ema{ema}_contact_order_unknown": contact_unknown[ema],
                        f"ema{ema}_armed_after_close": armed[ema]})
        rows.append(row)
    return rows


def _scale_parent(row: Mapping[str, Any], quantity: int) -> dict[str, Any]:
    result = deepcopy(dict(row))
    old_quantity = float(row.get("quantity", 1))
    if old_quantity <= 0:
        raise ValueError("pinned standardized parent requires positive quantity")
    for key in ("gross_dollars", "raw_price_dollars", "commission_dollars", "net_dollars",
                "risk_initial_dollars", "risk_effective_dollars", "source_risk_dollars"):
        if result.get(key) is not None:
            result[key] *= quantity / old_quantity
    result["quantity"] = quantity
    result["leg"] = "original"
    return result


def planned_quantity(equity: float, allocation: float, price: float, stop: float, direction: int,
                     config: Phase3Config, *, active_notional: float = 0) -> dict[str, Any]:
    """Whole-contract sizing at known submitted terms; gaps do not retroresize."""
    # Inherit native raw submission-anchor sizing. Costs and gaps can overshoot
    # this budget and are recorded rather than quietly reducing the controls.
    planned_entry = price
    risk_unit = direction * (price - stop) * config.point_value
    budget = equity * config.risk_percent / 100 * allocation
    free_notional = min(equity * config.max_leverage, equity / (config.margin_percent / 100)) - active_notional
    inherited = int(quantity_at_boundary(equity, price, stop, point_value=config.point_value,
        risk_percent=config.risk_percent * allocation, max_leverage=config.max_leverage)) if risk_unit > 0 else 0
    by_risk = math.floor(budget / risk_unit + 1e-9) if risk_unit > 0 and budget > 0 else 0
    by_exposure = math.floor(max(0, free_notional) / (planned_entry * config.point_value)) if planned_entry > 0 else 0
    quantity = max(0, min(inherited, by_risk, by_exposure))
    return {"quantity": quantity, "allocation_fraction": allocation, "budget_dollars": budget,
            "planned_risk_per_contract": risk_unit if risk_unit > 0 else None,
            "risk_quantity": by_risk, "exposure_quantity": by_exposure,
            "quantity_skip": quantity < 1, "margin_or_leverage_infeasible": by_exposure < 1,
            "spent_risk_not_restored": True, "sizing_anchor": "raw_submitted_price",
            "fees_slips_gaps_not_reserved": True,
            "estimated_roundtrip_cost_per_contract": 2 * config.commission_per_side + 2 * config.slip * config.point_value}


def _base_result(day: Phase1DayData, policy: str, mode: str) -> dict[str, Any]:
    return {"episode": {"episode_id": day.episode_id, "broker_day": day.broker_day,
            "policy": policy, "mode": mode, "direction": day.direction,
            "original_side": "long" if day.direction == 1 else "short" if day.direction == -1 else None,
            "status": "no_fill" if day.shadow_status == "no_event" else "unknown",
            "action_status": "unprocessed", "signals": 0, "original_fills": 0,
            "add_fills": 0, "net_dollars": 0.0 if day.shadow_status == "no_event" else None,
            "unknown_feature_count": 0, "ambiguous": False},
            "events": [], "orders": [], "trades": [], "exposure": [], "monitoring": []}


@dataclass
class _Leg:
    row: dict[str, Any]
    direction: int
    entry: float
    stop: float
    source_stop: float
    quantity: int
    entry_at: datetime
    reset_at: datetime | None
    reset_done: bool = False
    stop_queued: bool = False
    mfe: float = 0.0
    mae: float = 0.0


def _stop(anchor: float, direction: int, cfg: Phase3Config) -> float:
    return round_tick(anchor * (1 - direction * cfg.stop_percent / 100), cfg.tick_size)


def _risk_points(entry: float, stop: float, direction: int, cfg: Phase3Config) -> float:
    """Risk-only tick identity; raw fills, paths and source sizing stay untouched."""
    step=Decimal(str(cfg.tick_size))
    def metric_price(value):
        value=Decimal(str(value))
        canonical=(value/step).to_integral_value(rounding=ROUND_HALF_UP)*step
        return canonical if abs(value-canonical)<=step*Decimal("1e-8") else value
    return float(direction*(metric_price(entry)-metric_price(stop)))


def _trail(snapshot: Any, direction: int, cfg: Phase3Config) -> float:
    rounding = ROUND_FLOOR if direction == 1 else ROUND_CEILING
    ticks = (Decimal(str(snapshot.bar.ema50)) / Decimal(str(cfg.tick_size))).to_integral_value(rounding=rounding)
    return float((ticks - direction) * Decimal(str(cfg.tick_size)))


def _post_fill_path(bar: Bar, parent: Mapping[str, Any], cfg: Phase3Config) -> tuple[float, ...]:
    path = _path(bar, cfg.ordering)
    if parent.get("entry_time_precision") != "within_bar":
        return path
    raw, direction = float(parent["entry_price_raw"]), int(parent["direction"])
    for index, (a, b) in enumerate(zip(path, path[1:])):
        if (direction == 1 and b > a and a <= raw <= b) or (direction == -1 and b < a and b <= raw <= a):
            return (raw,) + path[index + 1:]
    raise ValueError("pinned parent intrabar fill does not occur on its inherited path")


def _exit_path(path: tuple[float, ...], raw: float, direction: int, *, after: bool) -> tuple[float, ...]:
    """Split an authored adverse stop crossing without including earlier visits."""
    for index, (a, b) in enumerate(zip(path, path[1:])):
        if direction * (b - a) < 0 and min(a, b) <= raw <= max(a, b):
            return (raw,) + path[index + 1:] if after else path[:index + 1] + (raw,)
    raise ValueError("saved stop exit has no crossing on inherited authored path")


def _exit_tradeoff(day: Phase1DayData, trade: Mapping[str, Any] | None, cfg: Phase3Config) -> dict[str, Any]:
    result = {"time_saved_minutes": None, "time_saved_minutes_lower": None,
              "time_saved_minutes_upper": None, "post_exit_favorable_points": None,
              "post_exit_trace_status": "not_comparable",
              "post_exit_trace_scope": "raw inherited minute path, EMA signal candle excluded; no profit target"}
    parent = day.baseline_trade
    if parent is None or trade is None or parent.get("status") != "completed" or trade.get("status") != "completed":
        return result
    start, end = instant(trade["exit_time"]), instant(parent["exit_time"])
    start_upper = instant(trade.get("exit_time_latest")) or start
    end_upper = instant(parent.get("exit_time_latest")) or end
    result.update(time_saved_minutes=(end-start).total_seconds()/60,
                  time_saved_minutes_lower=(end-start_upper).total_seconds()/60,
                  time_saved_minutes_upper=(end_upper-start).total_seconds()/60)
    if start > end:
        result["post_exit_trace_status"] = "policy_exit_after_parent"
        return result
    if start == end and trade.get("exit_price_raw") == parent.get("exit_price_raw"):
        result.update(post_exit_favorable_points=0., post_exit_trace_status="same_exit")
        return result
    prices = {b.timestamp:b for b in day.minutes}
    cursor, values = start, []
    while cursor <= end:
        bar = prices.get(cursor)
        if bar is None:
            if day.expected_minute is None or day.expected_minute(cursor):
                result["post_exit_trace_status"] = "missing_expected_minute"
                return result
            cursor += MINUTE
            continue
        if bar.contract != day.parent_contract:
            result["post_exit_trace_status"] = "contract_transition"
            return result
        path = _path(bar, cfg.ordering)
        if cursor == start and trade.get("exit_time_precision") == "within_bar":
            path = _exit_path(path, float(trade["exit_price_raw"]), day.direction, after=True)
        if cursor == end:
            if parent.get("exit_time_precision") == "within_bar":
                path = _exit_path(path, float(parent["exit_price_raw"]), day.direction, after=False)
            else:
                path = (bar.open,)
        values.extend(path)
        cursor += MINUTE
    anchor = float(trade["exit_price_raw"])
    result.update(post_exit_favorable_points=max([0., *[day.direction*(v-anchor) for v in values]]),
                  post_exit_trace_status="known_authored_path")
    return result


def _run_episode(day: Phase1DayData, policy: str, config: Phase3Config | None = None, *,
                mode: str | None = None, equity_start: Any = _DEFAULT_EQUITY,
                precomputed_monitoring: Sequence[Mapping[str, Any]] | None = None,
                precomputed_parent_exposure: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Execute one standalone policy on the fixed original boundary episode.

    A policies default to the financed 50/50 overlay.  Their forced 1+1 view is
    explicitly ``diagnostic_1plus1``.  ``full_parent``/``half_parent`` and
    ``parent_1``/``parent_2`` are controls.  The caller carries account equity
    between chronological episodes; an unknown ending equity stays unknown.
    """
    cfg = config or Phase3Config()
    if policy not in POLICIES:
        raise ValueError("unknown standalone policy")
    mode = mode or ("financed_overlay" if policy in {"A20", "A50"} else "standardized")
    if mode not in MODES:
        raise ValueError("unknown financing/control mode")
    out = _base_result(day, policy, mode)
    row = out["episode"]
    row.update(population="fixed_first_unfiltered_boundary_episode",
               native_cancel_latency_verified=False, execution_minutes=cfg.execution_minutes)
    if day.baseline_trade is None:
        row["action_status"] = "no_parent_event" if day.shadow_status == "no_event" else "unknown_parent_first_event"
        return out
    parent = day.baseline_trade
    direction = day.direction
    entry_at = instant(parent["entry_time"])
    entry_upper = instant(parent.get("entry_time_latest")) or entry_at
    contract = day.parent_contract
    if "slippage_ticks" in parent and parent["slippage_ticks"] != cfg.slippage_ticks:
        raise ValueError("cost scenario must use its matching frozen parent")
    if "commission_per_side" in parent and parent["commission_per_side"] != cfg.commission_per_side:
        raise ValueError("fee scenario must use its matching frozen parent")
    if "ordering" in parent and parent["ordering"] != cfg.ordering:
        raise ValueError("ordering scenario must use its matching frozen parent")
    if "direction" not in parent:
        parent = {**parent, "direction": direction}
    monitoring = observe_episode(day, cfg) if precomputed_monitoring is None else list(precomputed_monitoring)
    out["monitoring"] = monitoring
    row["unknown_feature_count"] = sum(not r["current"]["known"] for r in monitoring)
    row["original_order_snapshot"] = _snapshot_row(day.cloud.snapshot(instant(parent["order_submitted_at"]), contract), direction, day)
    row["entry_snapshot"] = _snapshot_row(day.cloud.snapshot(entry_at, contract), direction, day)
    finance = mode in {"full_parent", "half_parent", "financed_overlay"}
    if finance and equity_start is None:
        row.update(status="unknown", action_status="unknown_account_equity", original_quantity=None,
                   original_filled=None, add_filled=None, ending_equity=None, net_dollars=None)
        return out
    equity = cfg.initial_capital if equity_start is _DEFAULT_EQUITY or equity_start is None else equity_start
    allocation = .5 if mode in {"half_parent", "financed_overlay"} else 1.0
    boundary = day.range_high if direction == 1 else day.range_low
    sizing = planned_quantity(equity, allocation, boundary, float(parent["initial_stop"]), direction, cfg)
    quantity = sizing["quantity"] if finance else 2 if mode == "parent_2" else 1
    row.update(original_quantity=quantity, original_budget=sizing if finance else None,
               financing_enforced=finance, exposure_diagnostic=mode in {"diagnostic_1plus1", "parent_2"},
               budget_start_equity=equity if finance else None, add_attempts=0,
               add_quantity_skips=0, pending_add_cancellations=0, add_opportunity=False)
    if finance and quantity == 0:
        row.update(status="no_fill", action_status="original_quantity_skip", net_dollars=0.0,
                   original_fills=0, add_fills=0, financial_eligible_landmarks=0,
                   original_filled=False, add_filled=False, ending_equity=equity,
                   unused_reserve_dollars=equity * cfg.risk_percent / 200 if mode == "financed_overlay" else None)
        out["events"].append({"episode_id": day.episode_id, "event": "original_quantity_skip",
                              "time": parent["order_submitted_at"], "budget": sizing})
        return out
    if policy in {"G1", "G2"}:
        standing = None
        standing_time = None
        changed_tie = False
        tied_opposite = None
        for at in day.update_times:
            if at > entry_at:
                break
            snapshot = day.cloud.snapshot(at, contract)
            values = {side: gate_admission(snapshot, side, policy) for side in (1, -1)}
            first = standing is None
            tied = at == entry_at and not first
            out["orders"].append({"episode_id": day.episode_id, "event": "gate_candidate" if tied else "gate_update",
                "time": iso(at), "coincident_shadow": at == entry_at, "saved_initial_submission": first,
                "long_admission": values[1], "short_admission": values[-1],
                "snapshot": _snapshot_row(snapshot, direction, day),
                "schedule_provenance": "saved_initial_submit_plus_reconstructed_complete15m_source_calls"})
            if tied:
                changed_tie = bool(standing[direction] is True) != bool(values[direction] is True)
                tied_opposite = values[-direction]
                row["tied_candidate_admission"] = values[direction]
            else:
                standing, standing_time = values, at
        if standing is None:
            row.update(status="unknown", action_status="unknown_gate_update_prefix")
            return out
        admitted = standing[direction] is True
        opposite = standing[-direction] is True
        row.update(gate_admission=standing[direction], gate_update_time=iso(standing_time),
                   gate_staleness_minutes=(entry_at - standing_time).total_seconds() / 60,
                   gate_feature_unknown=standing[direction] is None,
                   tied_candidate_changes_admission=changed_tie)
        entry_bar = next((b for b in day.minutes if b.timestamp == entry_at), None)
        dual = entry_bar is not None and entry_bar.high >= day.range_high and entry_bar.low <= day.range_low
        opposite_may_fill = opposite or tied_opposite is True
        if changed_tie or (not admitted and opposite_may_fill and dual):
            row.update(status="unknown", action_status="unknown_admission_cancellation" if changed_tie else "unknown_shadow_cancel_ordering",
                       ambiguous=True, net_dollars=None, original_filled=None,
                       branch_evidence={"abstention_net_dollars": 0.0,
                                        "parent_fill_net_dollars": parent.get("net_dollars") if changed_tie else None,
                                        "opposite_order_may_fill": not admitted and opposite_may_fill and dual})
            return out
        if not admitted:
            row.update(status="no_fill", action_status="unknown_feature_abstention" if standing[direction] is None else "blocked_first_shadow_consumed",
                       net_dollars=0.0, original_filled=False, original_fills=0,
                       shadow_cancellation_model="virtual_first_boundary_OCA_monitor_on_authored1m_path",
                       later_opposite_entry_prohibited=True)
            return out
        control = _run_episode(day, "BASE", cfg, mode="parent_1",
            precomputed_monitoring=monitoring, precomputed_parent_exposure=precomputed_parent_exposure)
        out["trades"] = control["trades"]
        out["exposure"] = control["exposure"]
        trade = out["trades"][0]
        row.update(status=trade["status"], action_status="admitted_first_shadow",
                   original_fills=1, original_filled=True, net_dollars=trade.get("net_dollars"),
                   ambiguous=bool(trade.get("ambiguous")), source_parent_parity=True)
        for name in ["max_mtm_drawdown_dollars", "peak_notional", "peak_margin_dollars", "peak_concurrent_quantity"]:
            row[name] = control["episode"].get(name)
        return out
    control_only = policy == "BASE" or mode in {"full_parent", "half_parent", "parent_1", "parent_2"}
    if control_only and precomputed_parent_exposure is not None:
        trade = _scale_parent(parent, quantity)
        out["trades"] = [trade]
        out["exposure"] = deepcopy(list(precomputed_parent_exposure))
        for exposure in out["exposure"]:
            for key in ["closed_net_dollars", "floating_liquidation_net_dollars", "mtm_net_dollars",
                        "intraminute_mtm_min", "intraminute_mtm_max", "running_mtm_peak", "max_mtm_drawdown",
                        "active_quantity", "notional", "running_peak_notional", "running_peak_quantity", "combined_active_stop_risk"]:
                if exposure.get(key) is not None:
                    exposure[key] *= quantity
        row.update(status=trade["status"], action_status="unchanged_parent_control",
                   original_fills=1, original_filled=True, net_dollars=trade.get("net_dollars"),
                   source_parent_parity=True,
                   max_mtm_drawdown_dollars=max((r.get("max_mtm_drawdown", 0) for r in out["exposure"]), default=0),
                   peak_notional=max((r.get("running_peak_notional", r.get("notional", 0)) for r in out["exposure"]), default=0),
                   ending_equity=equity + trade["net_dollars"] if finance and trade.get("net_dollars") is not None else None)
        row["peak_margin_dollars"] = row["peak_notional"] * cfg.margin_percent / 100
        row["peak_concurrent_quantity"] = max((r.get("running_peak_quantity", r["active_quantity"]) for r in out["exposure"]), default=0)
        return out
    # Execution and source-price evidence stay separate from cloud availability.
    prices = {b.timestamp: b for b in day.minutes}
    observed = {instant(r["available_at"]): r for r in monitoring}
    decision_times = sorted(observed)
    decision_cursor = 0
    legs: dict[str, _Leg] = {}
    realized = 0.0
    peak_mtm = 0.0
    max_mtm_dd = 0.0
    max_notional = 0.0
    peak_quantity = 0
    pending_add: dict[str, Any] | None = None
    queued_ema_exit: str | None = None
    attempted = False
    armed = False
    failure_edge = None
    failure_slot = None
    previous_cross = None
    previous_cross_slot = None
    last_bar = None
    source_reset_at = instant(parent.get("reset_stop_active_at"))
    source_reset = parent.get("reset_stop")
    source_exit_at = instant(parent.get("exit_time"))
    source_censor_at = instant(parent.get("last_observed_at")) if parent.get("status") == "censored" else None

    def event(kind: str, at: datetime, **values):
        out["events"].append({"episode_id": day.episode_id, "event": kind, "time": iso(at), **values})

    def start_leg(name: str, at: datetime, raw: float, stop: float, qty: int, signal: dict[str, Any] | None = None):
        actual = raw + direction * cfg.slip
        risk = _risk_points(actual,stop,direction,cfg)
        template = _scale_parent(parent, qty) if name == "original" else {}
        template.update(trade_id=f"phase3:{policy}:{mode}:{day.episode_id}:{name}", episode_id=day.episode_id,
            leg=name, side="long" if direction == 1 else "short", direction=direction, quantity=qty,
            status="open", entry_time=iso(at), entry_time_latest=parent.get("entry_time_latest") if name == "original" else iso(at),
            entry_time_precision=parent.get("entry_time_precision", "observed_open") if name == "original" else "observed_open",
            entry_price_raw=raw, entry_price=actual, initial_stop=stop, reset_stop=None, reset_stop_active_at=None,
            effective_stop=stop,source_stop=stop,
            risk_initial_points=risk if risk > 0 else None, risk_initial_dollars=risk * cfg.point_value * qty if risk > 0 else None,
            slippage_ticks=cfg.slippage_ticks, commission_per_side=cfg.commission_per_side,
            signal_available_at=signal["time"] if signal else parent.get("signal_available_at"),
            entry_commission_paid=cfg.commission_per_side * qty, financing_enforced=finance,
            exit_time=None, exit_price=None, net_dollars=None)
        template.update(entry_cohort(at))
        for key in ["exit_time_latest", "exit_price_raw", "gross_points", "gross_dollars",
                    "raw_price_points", "raw_price_dollars", "commission_dollars", "net_points",
                    "net_dollars", "gross_r", "net_r", "source_style_r", "holding_minutes",
                    "holding_minutes_lower", "holding_minutes_upper", "holding_bars",
                    "observed_holding_minutes", "last_observed_at", "censor_reason", "exit_time_precision",
                    "risk_effective_points", "risk_effective_dollars", "source_risk_dollars"]:
            template[key] = None
        template["planned_stop_risk_dollars"] = direction * ((boundary if name == "original" else signal["signal_close"]) - stop) * cfg.point_value * qty
        template["protective_initial_risk_valid"] = risk > 0
        template["actual_initial_stop_loss_with_costs"] = ((risk + cfg.slip) * cfg.point_value * qty + 2 * cfg.commission_per_side * qty
            if risk > 0 else 2 * (cfg.slip * cfg.point_value + cfg.commission_per_side) * qty)
        budget_for_leg = equity * cfg.risk_percent / 100 * (allocation if name == "original" else .5)
        template["risk_budget_overshoot_dollars"] = max(0, template["actual_initial_stop_loss_with_costs"] - budget_for_leg) if finance else None
        reset_at = source_reset_at if name == "original" else at.replace(minute=at.minute // 5 * 5, second=0, microsecond=0) + FIVE
        legs[name] = _Leg(template, direction, actual, stop, stop, qty, at, reset_at)
        row["original_fills" if name == "original" else "add_fills"] += 1
        event("fill", at, leg=name, raw_price=raw, actual_price=actual, quantity=qty, initial_stop=stop)

    def finish(name: str, at: datetime, reason: str, raw: float | None, *, precision="observed_open", competing=False):
        nonlocal realized
        leg = legs.pop(name)
        trade = leg.row
        censored = raw is None
        effective_points = _risk_points(leg.entry,leg.stop,direction,cfg)
        effective_risk = effective_points*cfg.point_value*leg.quantity
        trade.update(effective_stop=leg.stop,source_stop=leg.source_stop,
            risk_effective_points=effective_points if effective_points>0 else None,
            risk_effective_dollars=effective_risk if effective_risk>0 else None)
        if censored:
            trade.update(status="censored", exit_reason=None, censor_reason=reason,
                         exit_time=None,exit_time_latest=None,exit_time_precision=None,
                         net_dollars=None, exit_price_raw=None, exit_price=None,
                         last_observed_at=iso(at), excursions_complete=False,
                         observed_holding_minutes=(at-leg.entry_at).total_seconds()/60,
                         mfe_points=leg.mfe,mae_points=leg.mae)
            for key in ["gross_points", "gross_dollars", "raw_price_points", "raw_price_dollars",
                        "commission_dollars", "net_points", "gross_r", "net_r", "source_style_r",
                        "holding_minutes", "holding_minutes_lower", "holding_minutes_upper", "holding_bars"]:
                trade[key] = None
        else:
            actual = raw - direction * cfg.slip
            gross_points = direction * (actual - leg.entry)
            gross = gross_points * cfg.point_value * leg.quantity
            commission = 2 * cfg.commission_per_side * leg.quantity
            net = gross - commission
            initial_risk = trade["risk_initial_dollars"]
            entry_latest = instant(trade.get("entry_time_latest")) or leg.entry_at
            exit_latest = at + MINUTE if precision == "within_bar" else at
            decision_minutes = 15 if name == "original" else 5
            entry_bucket = leg.entry_at.replace(minute=leg.entry_at.minute//decision_minutes*decision_minutes,second=0,microsecond=0)
            exit_bucket = at.replace(minute=at.minute//decision_minutes*decision_minutes,second=0,microsecond=0)
            trade.update(status="completed", exit_reason=reason, censor_reason=None,
                exit_time=iso(at), exit_time_latest=iso(at + MINUTE) if precision == "within_bar" else iso(at),
                exit_time_precision=precision, exit_price_raw=raw, exit_price=actual,
                raw_price_points=direction * (raw - trade["entry_price_raw"]),
                raw_price_dollars=direction * (raw - trade["entry_price_raw"]) * cfg.point_value * leg.quantity,
                gross_points=gross_points, gross_dollars=gross, commission_dollars=commission,
                net_points=net / (cfg.point_value * leg.quantity), net_dollars=net,
                gross_r=gross / initial_risk if initial_risk else None, net_r=net / initial_risk if initial_risk else None,
                risk_effective_dollars=effective_risk if effective_risk > 0 else None,
                source_risk_dollars=effective_risk if effective_risk>0 else None,
                source_style_r=net/effective_risk if effective_risk>0 else None,
                effective_stop=leg.stop, source_stop=leg.source_stop,
                mfe_points=leg.mfe, mae_points=leg.mae, excursions_complete=True,
                holding_minutes=(at - leg.entry_at).total_seconds() / 60,
                holding_minutes_lower=max(0.,(at-entry_latest).total_seconds()/60),
                holding_minutes_upper=max(0.,(exit_latest-leg.entry_at).total_seconds()/60),
                holding_bars=int((exit_bucket-entry_bucket).total_seconds()/(decision_minutes*60)),
                holding_decision_minutes=decision_minutes,last_observed_at=iso(at),observed_holding_minutes=None,
                competing_exit_orders=competing)
            realized += net
        out["trades"].append(trade)
        event("censor" if censored else "exit", at, leg=name, reason=reason, raw_price=raw, competing=competing)

    def mark(raw: float):
        nonlocal peak_mtm, max_mtm_dd, max_notional, peak_quantity
        floating = 0.0
        for leg in legs.values():
            move = direction * (raw - leg.entry)
            leg.mfe, leg.mae = max(leg.mfe, move), max(leg.mae, -move)
            floating += (direction * (raw - direction * cfg.slip - leg.entry) * cfg.point_value - 2 * cfg.commission_per_side) * leg.quantity
        mtm = realized + floating
        peak_mtm = max(peak_mtm, mtm)
        max_mtm_dd = max(max_mtm_dd, peak_mtm - mtm)
        notional = sum(leg.quantity for leg in legs.values()) * raw * cfg.point_value
        max_notional = max(max_notional, notional)
        peak_quantity = max(peak_quantity, sum(leg.quantity for leg in legs.values()))
        return mtm, floating, notional

    def apply_resets(known_through: datetime):
        for name, leg in list(legs.items()):
            if leg.reset_done or leg.reset_at is None or leg.reset_at > known_through:
                continue
            close_bar = prices.get(leg.reset_at - MINUTE)
            length = 15 if name == "original" else 5
            start = leg.entry_at.replace(minute=leg.entry_at.minute // length * length, second=0, microsecond=0)
            complete = close_bar is not None and all(t in prices and prices[t].contract == contract
                for t in (start + i * MINUTE for i in range(int((leg.reset_at - start) / MINUTE))))
            if not complete:
                finish(name, leg.reset_at, "unobservable_entry_candle_reset", None)
                continue
            proposed = float(source_reset) if name == "original" else _stop(leg.entry, direction, cfg)
            leg.source_stop = proposed
            leg.stop = (max(leg.stop, proposed) if direction == 1 else min(leg.stop, proposed)) if policy == "T50" and name == "original" else proposed
            leg.reset_done = True
            leg.stop_queued = direction * (close_bar.close - leg.stop) <= 0
            leg.row.update(reset_stop=proposed, reset_stop_active_at=iso(leg.reset_at), effective_stop=leg.stop)
            event("stop_reset", leg.reset_at, leg=name, source_proposed_stop=proposed,
                  effective_stop=leg.stop, decision_minutes=length, triggered_at_creation=leg.stop_queued)

    def decide(observation: dict[str, Any], at: datetime):
        nonlocal pending_add, attempted, armed, queued_ema_exit, failure_edge, failure_slot, previous_cross, previous_cross_slot
        if control_only or "original" not in legs or at >= day.cutoff:
            return
        prior, current = observation["prior"], observation["current"]
        valid = observation["usable"] and current["known"]
        slot = instant(observation["time"])
        original = legs["original"]
        liquidation = (direction * (observation["close"] - direction * cfg.slip - original.entry) * cfg.point_value - 2 * cfg.commission_per_side) * original.quantity if observation["usable"] else None
        if policy in {"A20", "A50"}:
            selected = 20 if policy == "A20" else 50
            if attempted:
                return
            known_contact = armed and prior["known"] and observation["usable"] and observation[f"ema{selected}_penetration"] is True
            if not known_contact and (not prior["known"] or not observation["usable"] or not current["known"]):
                attempted = True
                row.update(add_opportunity=None, action_status="unknown_support_prefix_abstention", add_attempts=1,
                           unknown_support_prefix=True)
                event("unknown_support_prefix", at, ema=selected, original_protection_preserved=True)
                return
            level = observation[f"ema{selected}_frozen_level"]
            if armed and observation[f"ema{selected}_penetration"] is True:
                attempted = True
                row.update(add_opportunity=True, add_attempts=1)
                confirm = valid and current["direction"] == direction and direction * (observation["close"] - level) > 0
                profitable = liquidation is not None and liquidation > 1e-8
                event("first_contact_consumed", at, ema=selected, frozen_level=level,
                      confirmed=confirm, liquidation_net=liquidation, parent_open=True,
                      parent_status_convention="survived_confirmation_close_before_next_open",
                      parent_decision_time_bound_ambiguous=observation["parent_decision_time_bound_ambiguous"])
                if not confirm or not profitable:
                    row["action_status"] = "rejected_confirmation" if not confirm else "rejected_nonpositive_liquidation"
                    return
                row["signals"] += 1
                stop = _stop(observation["close"], direction, cfg)
                capacity = planned_quantity(equity, .5, observation["close"], stop, direction, cfg,
                    active_notional=original.quantity * observation["close"] * cfg.point_value)
                qty = capacity["quantity"] if finance else 1
                signal = {"time": iso(at), "frozen_level": level, "signal_close": observation["close"],
                          "initial_stop": stop, "quantity": qty, "capacity": capacity if finance else None,
                          "original_liquidation_net": liquidation}
                out["orders"].append({"episode_id": day.episode_id, "event": "contingent_add", **signal})
                if qty == 0:
                    row["add_quantity_skips"] += 1
                    row["action_status"] = "add_quantity_skip"
                else:
                    pending_add = signal
                    row["action_status"] = "pending_contingent_add"
            elif observation["departure"] is True and valid:
                armed = True
                event("departure_armed", at, ema=selected, prior_upper=prior["upper"], prior_lower=prior["lower"])
        elif policy == "X1":
            if not valid or not prior["known"]:
                failure_edge, failure_slot = None, None
                event("failure_confirmation_reset_unknown", at)
                return
            if failure_edge is not None and (not day.cloud.adjacent(failure_slot, slot) or direction * (observation["close"] - failure_edge) >= 0):
                failure_edge, failure_slot = None, None
            if failure_edge is not None:
                queued_ema_exit = "ema_X1"
                row["signals"] += 1
                event("ema_exit_signal", at, policy=policy, frozen_edge=failure_edge, original_liquidation_net=liquidation,
                      original_open_at_signal=True,
                      parent_status_convention="survived_confirmation_close_before_next_open")
                failure_edge, failure_slot = None, None
            else:
                edge = prior["lower"] if direction == 1 else prior["upper"]
                if direction * (observation["close"] - edge) < 0:
                    failure_edge, failure_slot = edge, slot
                    event("failure_first_close", at, frozen_edge=edge)
        elif policy == "X2":
            if not valid:
                previous_cross, previous_cross_slot = None, None
                event("cross_confirmation_reset_unknown", at)
                return
            state = direction * current["direction"]
            if previous_cross in {0, 1} and state == -1 and day.cloud.adjacent(previous_cross_slot, slot):
                queued_ema_exit = "ema_X2"
                row["signals"] += 1
                event("ema_exit_signal", at, policy=policy, original_open_at_signal=True,
                      parent_status_convention="survived_confirmation_close_before_next_open", prior_alignment=previous_cross,
                      current_alignment=state, original_liquidation_net=liquidation)
            previous_cross, previous_cross_slot = state, slot
        elif policy == "T50":
            if not valid or not prior["known"]:
                event("trail_no_action_unknown", at, original_protection_preserved=True)
                return
            candidate = _trail(day.cloud.snapshot(slot, contract), direction, cfg)
            if direction * (candidate - original.stop) <= 0:
                event("trail_preserves_tighter_stop", at, proposed_stop=candidate, effective_stop=original.stop)
            elif direction * (observation["close"] - candidate) <= 0:
                queued_ema_exit = "ema_T50_already_breached"
                row["signals"] += 1
                event("trail_already_breached_next_open_exit", at, proposed_stop=candidate)
            else:
                original.stop = candidate
                event("trail_future_activation", at, proposed_stop=candidate, effective_stop=candidate)

    for bar in day.minutes:
        if bar.timestamp < entry_at:
            continue
        at = bar.timestamp
        gap = False
        roll = False
        if last_bar is not None:
            gap = bar.gap_before_expected
            cursor = last_bar.timestamp + MINUTE
            while not gap and cursor < at:
                gap = day.expected_minute(cursor) if day.expected_minute is not None else True
                cursor += MINUTE
            roll = bar.contract != last_bar.contract
        # Process a known completed close even when its next expected opening
        # is absent. Do not advance decisions beyond the first unknown prefix.
        decision_limit = last_bar.timestamp + MINUTE if last_bar is not None and (gap or roll) else at
        while decision_cursor < len(decision_times) and decision_times[decision_cursor] <= decision_limit:
            decision_at = decision_times[decision_cursor]
            apply_resets(decision_at)
            decide(observed[decision_at], decision_at)
            decision_cursor += 1
        apply_resets(decision_limit)
        if last_bar is not None:
            if gap or roll:
                reason = "contract_transition" if roll else "missing_expected_execution_minutes"
                for name in tuple(legs):
                    finish(name, last_bar.timestamp + MINUTE, reason, None)
                if pending_add is not None:
                    row.update(action_status="unknown_contingent_add_execution", ambiguous=True, unknown_add_fill=True)
                    event("unknown_pending_add", last_bar.timestamp + MINUTE, reason=reason)
                    pending_add = None
                if not legs:
                    break
        if not legs and row["original_fills"] == 0:
            if at != entry_at or bar.contract != contract:
                row.update(status="unknown", action_status="missing_parent_fill_evidence")
                return out
            start_leg("original", at, float(parent["entry_price_raw"]), float(parent["initial_stop"]), quantity)
            mark(float(parent["entry_price_raw"]))
        # Completed previous candles decide before the new opening.  The new
        # opening's price is not used to choose the preceding EMA signal.
        if cfg.execution_minutes == 15 and (pending_add is not None or queued_ema_exit is not None):
            for name in tuple(legs):
                finish(name, at, "unresolved_5m_action_on_15m_execution", None)
            row.update(action_status="unknown_resolution_ordering", ambiguous=True)
            row["unknown_add_fill"] = pending_add is not None
            break
        if "original" in legs and queued_ema_exit is not None:
            competing = legs["original"].stop_queued or direction * (bar.open - legs["original"].stop) <= 0
            finish("original", at, queued_ema_exit, bar.open, competing=competing)
            queued_ema_exit = None
        for name in tuple(legs):
            leg = legs[name]
            if at >= day.cutoff:
                finish(name, at, "time", bar.open, competing=leg.stop_queued or direction * (bar.open - leg.stop) <= 0)
            elif leg.stop_queued or direction * (bar.open - leg.stop) <= 0:
                if name == "original" and at == entry_at and parent.get("entry_time_precision") == "within_bar":
                    continue
                finish(name, at, "stop", bar.open)
        if pending_add is not None:
            if "original" not in legs or at >= day.cutoff:
                row["pending_add_cancellations"] += 1
                row["action_status"] = "contingent_add_canceled_parent_exit"
                event("pending_add_cancel", at, reason="parent_exited_before_release")
            else:
                start_leg("add", at, bar.open, pending_add["initial_stop"], pending_add["quantity"], pending_add)
                mark(bar.open)
                row["action_status"] = "add_filled"
                if direction * (bar.open - legs["add"].stop) <= 0:
                    finish("add", at, "stop", bar.open)
            pending_add = None
        path = _post_fill_path(bar, parent, cfg) if at == entry_at else _path(bar, cfg.ordering)
        minute_values = []
        for a, b in zip(path, path[1:]):
            minute_values.append(mark(a)[0])
            hits = []
            for name in tuple(legs):
                leg = legs[name]
                if direction * (a - leg.stop) <= 0 or direction * (b - leg.stop) <= 0:
                    raw = a if direction * (a - leg.stop) <= 0 else leg.stop
                    hits.append((abs(raw - a), name, raw))
            for _, name, raw in sorted(hits):
                    minute_values.append(mark(raw)[0])
                    leg = legs[name]
                    move = direction * (raw - leg.entry)
                    leg.mfe, leg.mae = max(leg.mfe, move), max(leg.mae, -move)
                    finish(name, at, "stop", raw, precision="within_bar")
            minute_values.append(mark(b)[0])
        mtm, floating, notional = mark(bar.close)
        out["exposure"].append({"episode_id": day.episode_id, "time": iso(at), "available_at": iso(at + MINUTE),
            "closed_net_dollars": realized, "floating_liquidation_net_dollars": floating,
            "mtm_net_dollars": mtm, "intraminute_mtm_min": min(minute_values or [mtm]),
            "intraminute_mtm_max": max(minute_values or [mtm]), "running_mtm_peak": peak_mtm,
            "max_mtm_drawdown": max_mtm_dd, "active_quantity": sum(l.quantity for l in legs.values()),
            "running_peak_notional": max_notional,
            "running_peak_quantity": peak_quantity,
            "notional": notional, "concurrent_legs": len(legs), "price_path": cfg.ordering,
            "combined_active_stop_risk": sum(max(0, direction * (l.entry - l.stop)) * cfg.point_value * l.quantity for l in legs.values())})
        last_bar = bar
        if not legs and pending_add is None:
            break
    if last_bar is not None and legs:
        while decision_cursor < len(decision_times) and decision_times[decision_cursor] <= last_bar.timestamp + MINUTE:
            decision_at = decision_times[decision_cursor]
            apply_resets(decision_at)
            decide(observed[decision_at], decision_at)
            decision_cursor += 1
        apply_resets(last_bar.timestamp + MINUTE)
    if legs:
        at = last_bar.timestamp + MINUTE if last_bar else entry_at
        for name in tuple(legs):
            finish(name, at, "retained_endpoint_open", None)
    if pending_add is not None:
        row.update(action_status="unknown_contingent_add_at_endpoint", unknown_add_fill=True)
        event("unknown_pending_add_at_endpoint", last_bar.timestamp + MINUTE if last_bar else entry_at)
    unknown = any(t["status"] != "completed" for t in out["trades"])
    if control_only:
        # The unchanged native parent row is authoritative. The new trace is
        # retained separately for floating exposure and compared independently.
        out["trades"] = [_scale_parent(parent, quantity)]
        unknown = parent.get("status") != "completed"
        realized = float(parent["net_dollars"]) * quantity if not unknown else 0.0
        row.update(action_status="unchanged_parent_control", source_parent_parity=True)
    row.update(status="censored" if unknown else "completed", original_filled=row["original_fills"] > 0,
               add_filled=None if row.get("unknown_add_fill") else row["add_fills"] > 0, net_dollars=None if unknown else realized,
               known_completed_net_dollars=realized, max_mtm_drawdown_dollars=max_mtm_dd,
               peak_notional=max_notional, financial_eligible_landmarks=sum(r["open_position_landmark"] for r in monitoring) if finance else None,
               ending_equity=None if unknown else equity + realized if finance else None,
               unused_reserve_dollars=max(0, equity * cfg.risk_percent / 200 - sum(t.get("planned_stop_risk_dollars", 0) for t in out["trades"] if t.get("leg") == "add")) if mode == "financed_overlay" else None)
    if row["action_status"] == "unprocessed":
        row["action_status"] = "no_ema_signal"
    row["risk_budget_overshoot"] = any((t.get("risk_budget_overshoot_dollars") or 0) > 1e-8 for t in out["trades"])
    row["combined_planned_stop_risk_dollars"] = sum(t.get("planned_stop_risk_dollars", 0) for t in out["trades"])
    row["peak_margin_dollars"] = max_notional * cfg.margin_percent / 100
    row["peak_concurrent_quantity"] = peak_quantity
    return out


def run_episode(day: Phase1DayData, policy: str, config: Phase3Config | None = None, *,
                mode: str | None = None, equity_start: Any = _DEFAULT_EQUITY,
                precomputed_monitoring: Sequence[Mapping[str, Any]] | None = None,
                precomputed_parent_exposure: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    cfg = config or Phase3Config()
    result = _run_episode(day, policy, cfg, mode=mode, equity_start=equity_start,
        precomputed_monitoring=precomputed_monitoring,
        precomputed_parent_exposure=precomputed_parent_exposure)
    mode = result["episode"]["mode"]
    tags = {"episode_id": day.episode_id, "broker_day": day.broker_day,
            "policy": policy, "mode": mode, "scenario": cfg.scenario}
    result["episode"].update(tags)
    result["episode"]["exposure_full_path_known"] = result["episode"]["status"] in {"completed","no_fill"}
    result["episode"]["observed_prefix_max_mtm_drawdown_dollars"] = result["episode"].get("max_mtm_drawdown_dollars",0. if result["episode"]["status"]=="no_fill" else None)
    result["episode"]["observed_prefix_peak_notional"] = result["episode"].get("peak_notional",0. if result["episode"]["status"]=="no_fill" else None)
    original = next((t for t in result["trades"] if t.get("leg") == "original"), None)
    result["episode"].update(_exit_tradeoff(day, original, cfg))
    if original is not None:
        boundary = day.range_high if day.direction == 1 else day.range_low
        qty = original["quantity"]
        planned = day.direction*(boundary-float(original["initial_stop"]))*cfg.point_value*qty
        signed_risk = _risk_points(float(original["entry_price"]),float(original["initial_stop"]),day.direction,cfg)
        actual = ((signed_risk+cfg.slip)*cfg.point_value*qty+2*cfg.commission_per_side*qty if signed_risk>0
                  else 2*(cfg.slip*cfg.point_value+cfg.commission_per_side)*qty)
        budget = result["episode"]["original_budget"]["budget_dollars"] if mode in {"full_parent", "half_parent", "financed_overlay"} else None
        overshoot = max(0.,actual-budget) if budget is not None else None
        original.update(planned_stop_risk_dollars=planned,protective_initial_risk_valid=signed_risk>0,
            actual_initial_stop_loss_with_costs=actual,risk_budget_overshoot_dollars=overshoot)
        result["episode"].update(original_planned_stop_risk_dollars=planned,
            original_actual_initial_stop_loss_with_costs=actual,
            original_risk_budget_overshoot_dollars=overshoot,
            risk_budget_overshoot=bool(result["episode"].get("risk_budget_overshoot")) or (overshoot or 0)>1e-8)
    result["episode"]["combined_planned_stop_risk_dollars"] = sum(t["planned_stop_risk_dollars"] for t in result["trades"]) if result["trades"] else 0. if result["episode"]["status"]=="no_fill" else None
    result["episode"]["planned_raw_stop_risk_scope"] = "observed filled legs; unobserved contingent fills excluded"
    result["episode"]["combined_planned_stop_risk_complete"] = not bool(result["episode"].get("unknown_add_fill")) and result["episode"]["status"] in {"completed","no_fill"}
    for name in ["events", "orders", "trades", "exposure"]:
        for row in result[name]:
            row.update(tags)
            if name == "events":
                row["kind"] = row["event"]
    return result
