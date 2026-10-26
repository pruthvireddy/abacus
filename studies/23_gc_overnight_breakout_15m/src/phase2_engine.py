"""Causal Phase 2 replacement policies and protected-boundary observations.

No input loading, selection, aggregation, publication, account compounding or
Phase 3 calculation lives here. Phase 1 engine/evidence stays unchanged. All
interfaces consume pinned frozen episodes and independently audited candles.
"""
from __future__ import annotations

from bisect import bisect_left
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from fractions import Fraction
import math
from typing import Any, Callable, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .engine import Bar, BROKER, NY, UTC, entry_cohort, iso, regular_gc_expected

MINUTE = timedelta(minutes=1)
QUARTER = timedelta(minutes=15)
EPS = 1e-8


def instant(value: datetime | str | None) -> datetime | None:
    if value is None or value == "":
        return None
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("aware UTC timestamps required")
    return result.astimezone(UTC)


def bucket(value: datetime) -> datetime:
    return value.replace(minute=(value.minute // 15) * 15, second=0, microsecond=0)


def relation(price: float, level: float) -> int:
    delta = price - level
    return 0 if abs(delta) <= EPS else 1 if delta > 0 else -1


def tick_price(price: float, tick: float, *, direction: int | None = None) -> float:
    # Canonicalize only float noise far smaller than an executable tick.
    ticks = Decimal(str(price)) / Decimal(str(tick))
    nearest = ticks.to_integral_value(rounding=ROUND_HALF_UP)
    if abs(ticks - nearest) < Decimal("0.000001"):
        ticks = nearest
    mode = ROUND_HALF_UP if direction is None else ROUND_FLOOR if direction == 1 else ROUND_CEILING
    return float(ticks.to_integral_value(rounding=mode) * Decimal(str(tick)))


def percentage_stop(anchor: float, direction: int, percent: float, tick: float) -> float:
    canonical=Decimal(str(anchor))
    ticks=canonical/Decimal(str(tick))
    nearest=ticks.to_integral_value(rounding=ROUND_HALF_UP)
    if abs(ticks-nearest)<Decimal("0.000001"):
        canonical=nearest*Decimal(str(tick))
    # Raw rational descriptive levels remain fractional ticks. Only binary
    # noise around an already executable tick is removed from an anchor.
    value = canonical * (Decimal(1) - Decimal(direction) * Decimal(str(percent)) / Decimal(100))
    return float((value / Decimal(str(tick))).to_integral_value(rounding=ROUND_HALF_UP) * Decimal(str(tick)))


@dataclass(frozen=True)
class BaselineEpisode:
    episode_id: str
    broker_day: str
    contract: str
    direction: int
    range_high: float
    range_low: float
    entry_time: datetime
    entry_price_raw: float
    entry_time_latest: datetime | None = None
    entry_time_precision: str = "within_bar"
    baseline_status: str = "completed"
    baseline_exit_time: datetime | None = None
    baseline_exit_time_latest: datetime | None = None
    baseline_exit_time_precision: str = "within_bar"
    baseline_net_dollars: float | None = None
    baseline_censor_at: datetime | None = None
    ambiguous: bool = False

    def __post_init__(self):
        if type(self.direction) is not int or self.direction not in {-1, 1} or not all(math.isfinite(v) and v>0 for v in [self.range_high,self.range_low,self.entry_price_raw]) or self.range_high <= self.range_low:
            raise ValueError("positive frozen range and original direction required")
        if self.entry_time.tzinfo is None or self.entry_time.second or self.entry_time.microsecond:
            raise ValueError("original entry must have aware minute timestamp")
        if self.entry_time.astimezone(BROKER).date().isoformat() != self.broker_day:
            raise ValueError("original broker date mismatch")

    @property
    def breakout_bar_open(self) -> datetime:
        return bucket(self.entry_time)

    @property
    def direction_available_at(self) -> datetime:
        return self.breakout_bar_open + QUARTER

    @property
    def cutoff(self) -> datetime:
        return datetime.combine(date.fromisoformat(self.broker_day), time(20), BROKER).astimezone(UTC)

    @property
    def protected_boundary(self) -> float:
        return self.range_low if self.direction == 1 else self.range_high

    @property
    def original_boundary(self) -> float:
        return self.range_high if self.direction == 1 else self.range_low

    @property
    def midpoint(self) -> float:
        return (self.range_high + self.range_low) / 2

    def level(self, fraction: float) -> float:
        # Rational arithmetic retains theoretical quarter-tick levels rather
        # than silently turning confirmed-close thresholds into order prices.
        q = Fraction(str(fraction))
        high, low = Fraction(str(self.range_high)), Fraction(str(self.range_low))
        return float(high - q*(high-low) if self.direction == 1 else low + q*(high-low))

    @classmethod
    def from_rows(cls, trade: Mapping[str, Any], range_row: Mapping[str, Any]):
        def numeric(key):
            value = trade.get(key)
            return None if value in {None, ""} else float(value)
        return cls(str(trade["trade_id"]), str(trade["broker_day"]), str(trade["contract"]),
            int(trade.get("direction", 1 if trade["side"] == "long" else -1)),
            float(range_row["range_high"]), float(range_row["range_low"]),
            instant(trade["entry_time"]), float(trade["entry_price_raw"]),
            instant(trade.get("entry_time_latest")), str(trade.get("entry_time_precision", "within_bar")),
            str(trade["status"]), instant(trade.get("exit_time")), instant(trade.get("exit_time_latest")),
            str(trade.get("exit_time_precision", "within_bar")), numeric("net_dollars"),
            instant(trade.get("last_observed_at")), str(trade.get("ambiguous", False)).lower() == "true")


@dataclass(frozen=True)
class DecisionBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    contract: str
    available_at: datetime | None = None
    complete: bool = True

    @property
    def end(self) -> datetime:
        return self.timestamp + QUARTER


@dataclass(frozen=True)
class Phase2Config:
    tick_size: float = 0.1
    point_value: float = 100.0
    stop_percent: float = 1.0
    commission_per_side: float = 2.5
    slippage_ticks: int = 1
    ordering: str = "source_ohlc"
    execution_minutes: int = 1
    stop_mode: str = "percent"
    fill_model: str = "scheduled_open"
    timed_exit_priority: str = "market_first"

    def __post_init__(self):
        if not all(math.isfinite(v) for v in [self.tick_size,self.point_value,self.stop_percent,self.commission_per_side]) or min(self.tick_size, self.point_value, self.stop_percent) <= 0 or self.commission_per_side < 0:
            raise ValueError("positive economics and nonnegative fees required")
        if self.ordering not in {"source_ohlc", "high_first", "low_first"} or type(self.slippage_ticks) is not int or self.slippage_ticks not in {0,1,2}:
            raise ValueError("unregistered ordering or slippage scenario")
        if type(self.execution_minutes) is not int or self.execution_minutes not in {1,15} or self.stop_mode not in {"percent", "opposite_boundary"}:
            raise ValueError("unsupported observation/stop convention")
        if self.fill_model not in {"scheduled_open", "next_observed_open_sensitivity"}:
            raise ValueError("source fallback must be explicitly labeled sensitivity")
        if self.timed_exit_priority not in {"market_first", "stop_first"}:
            raise ValueError("unsupported competing exit ordering")


@dataclass(frozen=True)
class PolicySpec:
    name: str
    kind: str
    fraction: float = 0.0
    trade_through_ticks: int = 1

    def __post_init__(self):
        if self.kind not in {"reclaim", "passive", "protected_touch_hold", "protected_failed_break_reclaim", "protected_reversal"}:
            raise ValueError("unsupported Phase 2 policy")
        if self.kind == "reclaim" and self.fraction not in {0,.25,.5,.75}:
            raise ValueError("primary family is fixed to four fractions")
        if self.kind == "passive" and self.fraction not in {.25,.5,.75}:
            raise ValueError("passive family has three fixed fractions")
        if self.trade_through_ticks not in {0,1}:
            raise ValueError("only trade-through and touch sensitivity are declared")


def policy_specs(*, passive_touch: bool = False) -> list[PolicySpec]:
    policies = [PolicySpec(f"reclaim-q{int(q*100):03d}", "reclaim", q) for q in [0,.25,.5,.75]]
    policies += [PolicySpec(f"passive-q{int(q*100):03d}" + ("-touch" if passive_touch else ""), "passive", q, 0 if passive_touch else 1) for q in [.25,.5,.75]]
    policies += [PolicySpec(name.replace("_", "-"), name) for name in ["protected_touch_hold", "protected_failed_break_reclaim", "protected_reversal"]]
    return policies


def baseline_state(episode: BaselineEpisode, at: datetime) -> dict[str, Any]:
    exit_time = episode.baseline_exit_time
    if episode.baseline_status == "completed" and exit_time is not None:
        latest = episode.baseline_exit_time_latest or exit_time
        if episode.baseline_exit_time_precision == "within_bar":
            known_at = max(latest, bucket(exit_time) + QUARTER)
        else:
            # An order scheduled at this same opening has not yet filled when
            # a preceding-candle signal is submitted at that close.
            known_at = latest
        flat = known_at <= at if episode.baseline_exit_time_precision == "within_bar" else known_at < at
        if flat:
            return {"baseline_position_status": "flat", "baseline_loss_known": episode.baseline_net_dollars is not None and episode.baseline_net_dollars < -EPS,
                    "baseline_realized_net_dollars": episode.baseline_net_dollars, "baseline_exit_known_at": iso(known_at)}
        return {"baseline_position_status": "open", "baseline_loss_known": False, "baseline_realized_net_dollars": None, "baseline_exit_known_at": iso(known_at)}
    if episode.baseline_censor_at is not None and at >= episode.baseline_censor_at:
        return {"baseline_position_status": "unknown", "baseline_loss_known": None, "baseline_realized_net_dollars": None, "baseline_exit_known_at": None}
    return {"baseline_position_status": "open", "baseline_loss_known": False, "baseline_realized_net_dollars": None, "baseline_exit_known_at": None}


def session_horizon_end(entry_time: datetime, cutoff: datetime) -> tuple[datetime, str, bool]:
    local = entry_time.astimezone(NY)
    minute = local.hour*60 + local.minute
    day = local.date()
    if minute >= 1200:
        end = datetime.combine(day + timedelta(days=1), time(2), NY)
        session = "Asia"
    elif minute < 120:
        end = datetime.combine(day, time(2), NY)
        session = "Asia"
    elif minute < 540:
        end = datetime.combine(day, time(9), NY)
        session = "London"
    elif minute < 570:
        end = datetime.combine(day, time(9,30), NY)
        session = "Outside"
    elif minute < 960:
        end = datetime.combine(day, time(16), NY)
        session = "New York"
    else:
        end = datetime.combine(day, time(20), NY)
        session = "Outside"
    end = end.astimezone(UTC)
    return min(end, cutoff), session, cutoff < end


def price_path(bar: Bar | DecisionBar, ordering: str) -> tuple[float, ...]:
    high_first = ordering == "high_first" or (ordering == "source_ohlc" and relation(bar.high-bar.open,bar.open-bar.low)<0)
    return (bar.open,bar.high,bar.low,bar.close) if high_first else (bar.open,bar.low,bar.high,bar.close)


def post_fill_path(bar: Bar, episode: BaselineEpisode, ordering: str) -> tuple[float, ...]:
    path = price_path(bar, ordering)
    if bar.timestamp != episode.entry_time or episode.entry_time_precision == "observed_open":
        return path
    target, direction = episode.entry_price_raw, episode.direction
    for index,(a,b) in enumerate(zip(path,path[1:])):
        crosses = relation(a,target) <= 0 <= relation(b,target) if direction == 1 and b >= a else relation(b,target) <= 0 <= relation(a,target) if direction == -1 and b <= a else False
        if crosses:
            return (target, b, *path[index+2:])
    raise ValueError("pinned original fill is not traceable to its minute path")


@dataclass
class EpisodeContext:
    episode: BaselineEpisode
    minutes: Sequence[Bar]
    candles: Sequence[DecisionBar]
    expected_minute: Callable[[datetime], bool] = regular_gc_expected
    minute_index: dict[datetime, Bar] = field(init=False)
    candle_index: dict[datetime, DecisionBar] = field(init=False)
    missing: list[datetime] = field(init=False)
    contract_barrier: datetime | None = field(init=False)

    def __post_init__(self):
        self.minutes = tuple(self.minutes)
        self.candles = tuple(self.candles)
        previous = None
        for bar in self.minutes:
            if bar.timestamp.tzinfo is None or bar.timestamp.second or bar.timestamp.microsecond:
                raise ValueError("minute-aligned aware execution input required")
            if previous is not None and bar.timestamp <= previous:
                raise ValueError("duplicate or descending execution timestamp")
            values = (bar.open,bar.high,bar.low,bar.close)
            if not all(math.isfinite(x) and x > 0 for x in values) or bar.low > min(bar.open,bar.close) or bar.high < max(bar.open,bar.close) or bar.low > bar.high:
                raise ValueError("invalid unadjusted execution candle")
            if bar.available_at is not None and bar.available_at < bar.timestamp + MINUTE:
                raise ValueError("early OHLC availability")
            previous = bar.timestamp
        if any(b.timestamp.tzinfo is None or b.timestamp != bucket(b.timestamp) for b in self.candles):
            raise ValueError("signal input must have aware regular 15m opens")
        if any(a.timestamp >= b.timestamp for a,b in zip(self.candles,self.candles[1:])):
            raise ValueError("duplicate or descending decision candles")
        if any(b.available_at is not None and b.available_at != b.end for b in self.candles):
            raise ValueError("frozen decision availability is scheduled 15m completion")
        for bar in self.candles:
            if bar.complete and (not all(math.isfinite(x) and x > 0 for x in (bar.open,bar.high,bar.low,bar.close))
                    or bar.low > min(bar.open,bar.close) or bar.high < max(bar.open,bar.close) or bar.low > bar.high):
                raise ValueError("complete decision candle requires valid unadjusted OHLC")
        self.minute_index = {bar.timestamp:bar for bar in self.minutes}
        self.candle_index = {bar.timestamp:bar for bar in self.candles}
        if self.episode.entry_time not in self.minute_index:
            raise ValueError("original accepted fill minute absent from pinned observation")
        self.contract_barrier = next((bar.timestamp for bar in self.minutes if self.episode.entry_time <= bar.timestamp < self.episode.cutoff and bar.contract != self.episode.contract),None)
        self.missing = []
        cursor = self.episode.breakout_bar_open
        while cursor <= self.episode.cutoff:
            if self.expected_minute(cursor) and cursor not in self.minute_index:
                self.missing.append(cursor)
            cursor += MINUTE

    def uncertain(self, start: datetime, end: datetime) -> bool:
        index = bisect_left(self.missing,start)
        return (index < len(self.missing) and self.missing[index] < end) or (self.contract_barrier is not None and start <= self.contract_barrier < end)

    def first_uncertain(self, start: datetime, end: datetime) -> tuple[datetime,str] | None:
        candidates=[]
        index=bisect_left(self.missing,start)
        if index<len(self.missing) and self.missing[index]<end:
            candidates.append((self.missing[index],"missing_expected_execution_minutes"))
        if self.contract_barrier is not None and start<=self.contract_barrier<end:
            candidates.append((self.contract_barrier,"contract_transition"))
        return min(candidates,key=lambda pair:pair[0]) if candidates else None

    def complete(self, bar: DecisionBar) -> bool:
        return (bar.complete and bar.contract == self.episode.contract and not self.uncertain(bar.timestamp,bar.end)
                and (self.contract_barrier is None or self.contract_barrier >= bar.end))

    def direction_is_available(self) -> bool:
        bar = self.candle_index.get(self.episode.breakout_bar_open)
        return bar is not None and self.complete(bar)

    def observed_after_fill(self, end: datetime) -> list[Bar]:
        return [bar for bar in self.minutes if self.episode.entry_time <= bar.timestamp < end and
                (self.contract_barrier is None or bar.timestamp < self.contract_barrier)]


def prepare_context(episode: BaselineEpisode, minutes: Iterable[Bar], candles15: Iterable[DecisionBar],
                    expected_minute: Callable[[datetime],bool] | None = None) -> EpisodeContext:
    return EpisodeContext(episode,tuple(minutes),tuple(candles15),expected_minute or regular_gc_expected)


def _base_policy_row(ctx: EpisodeContext, policy: PolicySpec, cfg: Phase2Config) -> dict[str,Any]:
    e = ctx.episode
    return {"episode_id":e.episode_id,"broker_day":e.broker_day,"contract":e.contract,
        "policy":policy.name,"policy_kind":policy.kind,"fraction":policy.fraction,
        "trade_through_ticks":policy.trade_through_ticks,"original_direction":e.direction,
        "original_side":"long" if e.direction==1 else "short","original_entry_time":iso(e.entry_time),
        "direction_available_at":iso(e.direction_available_at),"cutoff":iso(e.cutoff),
        "raw_level":e.level(policy.fraction) if policy.kind in {"reclaim","passive"} else e.protected_boundary,
        "status":"known_no_fill","reason":None,"opportunity":False,"armed":False,"signal":False,
        "arming_at":None,"signal_available_at":None,"submitted_at":None,"expected_fill_time":None,
        "order_type":None,"direction":-e.direction if policy.kind=="protected_reversal" else e.direction,
        "initial_stop_anchor":None,"initial_stop":None,"submitted_limit":None,
        "planned_risk_points":None,"missed_before_arming":False,"unknown":False,
        "net_dollars":0.0,"trade":None,"events":[],"ordering":cfg.ordering,
        "slippage_ticks":cfg.slippage_ticks,"commission_per_side":cfg.commission_per_side}


def _status(row: dict[str,Any], status: str, reason: str) -> dict[str,Any]:
    row.update(status=status,reason=reason,unknown=status.startswith("unknown"),
               net_dollars=None if status.startswith("unknown") else 0.0)
    return row


def _submitted(row: dict[str,Any], ctx: EpisodeContext, policy: PolicySpec, cfg: Phase2Config,
               at: datetime, anchor: float, *, order_type: str, limit: float | None = None) -> dict[str,Any]:
    direction = row["direction"]
    stop = (ctx.episode.range_low if direction==1 else ctx.episode.range_high) if cfg.stop_mode=="opposite_boundary" else percentage_stop(anchor,direction,cfg.stop_percent,cfg.tick_size)
    risk = direction*(anchor-stop)
    row.update(signal=True,signal_available_at=iso(at),
               initial_stop_anchor=anchor,initial_stop=stop,planned_risk_points=risk,
               order_type=order_type,submitted_limit=limit)
    row.update({key+"_at_signal":value for key,value in baseline_state(ctx.episode,at).items()})
    clock = at.astimezone(BROKER)
    if clock.date().isoformat()!=ctx.episode.broker_day or not 7<=clock.hour<20 or at>=ctx.episode.cutoff:
        row["events"].append({"event":"first_setup_rejected","time":iso(at),"reason":"no_eligible_next_open"})
        return _status(row,"known_no_fill","first_setup_has_no_eligible_next_open")
    if risk<=EPS:
        row["events"].append({"event":"first_setup_rejected","time":iso(at),"reason":"invalid_planned_risk"})
        return _status(row,"known_no_fill","invalid_planned_risk_before_submission")
    row.update(status="submitted",reason=None,net_dollars=None,submitted_at=iso(at),expected_fill_time=iso(at))
    row["events"].append({"event":"order_submitted","time":iso(at),"anchor":anchor,"stop":stop,"order_type":order_type})
    return row


def _reached_before_arming(ctx: EpisodeContext, level: float) -> bool | None:
    e = ctx.episode
    if ctx.uncertain(e.entry_time,e.direction_available_at):
        return None
    outcomes=[]
    for ordering in ("high_first","low_first"):
        reached=False
        for bar in ctx.observed_after_fill(e.direction_available_at):
            path=post_fill_path(bar,e,ordering)
            if any(e.direction*relation(p,level)<=0 for p in path):
                reached=True
                break
        outcomes.append(reached)
    return outcomes[0] if outcomes[0]==outcomes[1] else None


def _breached_through(ctx: EpisodeContext, end: datetime, tick: float) -> bool | None:
    e=ctx.episode
    level=e.protected_boundary-e.direction*tick
    outcomes=[]
    for ordering in ("high_first","low_first"):
        hit=any(any(e.direction*relation(p,level)<=0 for p in post_fill_path(bar,e,ordering)) for bar in ctx.observed_after_fill(end))
        outcomes.append(hit)
    if outcomes==[True,True]:
        return True
    if outcomes[0]!=outcomes[1] or ctx.uncertain(e.entry_time,end):
        return None
    return False


def find_signal(ctx: EpisodeContext, policy: PolicySpec, config: Phase2Config | None = None) -> dict[str,Any]:
    """Return first causal setup/order, or known no-fill versus unknown prefix."""
    cfg=config or Phase2Config()
    e=ctx.episode
    row=_base_policy_row(ctx,policy,cfg)
    if not ctx.direction_is_available():
        return _status(row,"unknown_signal","original_direction_candle_incomplete_or_unusable")
    if policy.kind=="passive":
        raw=e.level(policy.fraction)
        level=tick_price(raw,cfg.tick_size,direction=e.direction)
        row["submitted_limit"]=level
        reached=_reached_before_arming(ctx,raw)
        if reached is None:
            return _status(row,"unknown_signal","post_fill_pre_submission_chronology_unknown")
        if reached:
            row.update(opportunity=True,missed_before_arming=True)
            return _status(row,"known_no_fill","missed_before_arming")
        row.update(armed=True,arming_at=iso(e.direction_available_at))
        return _submitted(row,ctx,policy,cfg,e.direction_available_at,level,order_type="limit",limit=level)
    armed_bar=None
    if policy.kind=="protected_failed_break_reclaim":
        row["prior_breach_before_actionable"]=_breached_through(ctx,e.direction_available_at,cfg.tick_size)
    if policy.kind=="protected_touch_hold" and _breached_through(ctx,e.direction_available_at,cfg.tick_size) is True:
        row["prior_breach_before_actionable"]=True
        return _status(row,"known_no_fill","one_tick_breach_disqualifies_touch_hold")
    for bar in ctx.candles:
        if bar.timestamp<=e.breakout_bar_open or bar.timestamp>=e.cutoff:
            continue
        if ctx.uncertain(e.direction_available_at,bar.end) or not ctx.complete(bar):
            return _status(row,"unknown_signal","uncertain_prefix_before_first_actionable_setup")
        inward=e.direction*relation(bar.close,row["raw_level"])
        if policy.kind=="reclaim":
            if armed_bar is None and (inward<0 if policy.fraction==0 else inward<=0):
                armed_bar=bar.timestamp
                row.update(opportunity=True,armed=True,arming_at=iso(bar.end))
                row["events"].append({"event":"armed","time":iso(bar.end),"close":bar.close})
            elif armed_bar is not None and bar.timestamp>armed_bar and inward>0:
                return _submitted(row,ctx,policy,cfg,bar.end,bar.close,order_type="market")
        elif policy.kind=="protected_touch_hold":
            breached=_breached_through(ctx,bar.end,cfg.tick_size)
            if breached is True:
                return _status(row,"known_no_fill","one_tick_breach_disqualifies_touch_hold")
            touches=e.direction*relation(bar.low if e.direction==1 else bar.high,e.protected_boundary)<=0
            if touches and inward>0:
                row.update(opportunity=True,armed=True,arming_at=iso(bar.end))
                if breached is None:
                    return _status(row,"unknown_signal","touch_hold_no_prior_breach_unresolved")
                return _submitted(row,ctx,policy,cfg,bar.end,bar.close,order_type="market")
        elif policy.kind=="protected_failed_break_reclaim":
            threshold=e.protected_boundary-e.direction*cfg.tick_size
            breached=e.direction*relation(bar.low if e.direction==1 else bar.high,threshold)<=0
            if armed_bar is None and breached:
                armed_bar=bar.timestamp
                row.update(opportunity=True,armed=True,arming_at=iso(bar.end))
                row["events"].append({"event":"armed_on_first_post_available_breach","time":iso(bar.end)})
            elif armed_bar is not None and bar.timestamp>armed_bar and inward>0:
                return _submitted(row,ctx,policy,cfg,bar.end,bar.close,order_type="market")
        else:
            if inward<0:
                row.update(opportunity=True,armed=True,arming_at=iso(bar.end))
                return _submitted(row,ctx,policy,cfg,bar.end,bar.close,order_type="market")
    if ctx.uncertain(e.direction_available_at,e.cutoff):
        return _status(row,"unknown_signal","unobserved_remaining_first_setup")
    return _status(row,"known_no_fill","no_first_qualifying_setup_before_cutoff")


def _execution_bars(ctx: EpisodeContext,cfg: Phase2Config) -> list[Bar]:
    if cfg.execution_minutes==1:
        return list(ctx.minutes)
    return [Bar(b.timestamp,b.open,b.high,b.low,b.close,b.contract,b.end) for b in ctx.candles if math.isfinite(b.open)]


def execute_signal(signal: Mapping[str,Any], ctx: EpisodeContext, config: Phase2Config | None = None,
                   *, quantity: float = 1.0) -> dict[str,Any]:
    """Execute submitted first order; unknown fill is never an unfilled zero.

    Market orders require the exact scheduled opening minute in the primary.
    ``quantity`` supports an independently budgeted executable account leg, but
    must be an actual whole GC quantity. This function does not allocate risk.
    """
    cfg=config or Phase2Config()
    row=deepcopy(dict(signal))
    if row["status"]!="submitted":
        return row
    if type(quantity) is bool or not math.isfinite(quantity) or quantity<0 or not float(quantity).is_integer():
        raise ValueError("only nonnegative whole executable GC quantities")
    if quantity<1:
        row.update(quantity_skipped=True,submitted_at=None,expected_fill_time=None)
        for event in row["events"]:
            if event["event"]=="order_submitted":
                event["event"]="candidate_order_terms_not_executed"
        row["events"].append({"event":"quantity_skip","time":row["signal_available_at"],"quantity":quantity})
        return _status(row,"known_no_fill","quantity_below_one_contract")
    e=ctx.episode
    due=instant(row["expected_fill_time"])
    assert due is not None
    direction=int(row["direction"])
    slip=cfg.tick_size*cfg.slippage_ticks
    execution=_execution_bars(ctx,cfg)
    pos=None
    last_end=due
    pending=True
    source_gap=cfg.fill_model=="next_observed_open_sensitivity"
    fill_is_market=row["order_type"]=="market"
    complete_fields={"execution_minutes":cfg.execution_minutes,"fill_model":cfg.fill_model,
                     "quantity":quantity,"stop_mode":cfg.stop_mode}
    row.update(complete_fields)

    def start(raw: float, at: datetime, precision: str, *, path_ambiguous: bool=False):
        nonlocal pos,pending
        price=raw+direction*slip
        stop=float(row["initial_stop"])
        risk=direction*(price-stop)
        trade={"trade_id":f"{e.episode_id}:{row['policy']}:{cfg.ordering}:{cfg.slippage_ticks}",
            "episode_id":e.episode_id,"broker_day":e.broker_day,"contract":e.contract,
            "policy":row["policy"],"policy_kind":row["policy_kind"],"fraction":row["fraction"],
            "original_side":"long" if e.direction==1 else "short","original_entry_time":iso(e.entry_time),
            "direction":direction,"side":"long" if direction==1 else "short","quantity":quantity,
            "status":"open","order_submitted_at":row["submitted_at"],"order_active_at":row["submitted_at"],
            "signal_available_at":row["signal_available_at"],"arming_at":row["arming_at"],
            "entry_time":iso(at),"entry_time_latest":iso(at+timedelta(minutes=cfg.execution_minutes)) if precision=="within_bar" else iso(at),
            "entry_time_precision":precision,"entry_price_raw":raw,"entry_price":price,
            "initial_stop":stop,"initial_stop_anchor":row["initial_stop_anchor"],
            "initial_stop_active_at":row["submitted_at"],"reset_stop":None,"reset_stop_active_at":None,
            "planned_risk_points":row["planned_risk_points"],
            "risk_initial_points":risk if risk>EPS else None,
            "risk_initial_dollars":risk*cfg.point_value*quantity if risk>EPS else None,
            "risk_effective_points":risk if risk>EPS else None,
            "risk_effective_dollars":risk*cfg.point_value*quantity if risk>EPS else None,
            "source_risk_dollars":abs(price-stop)*cfg.point_value*quantity if abs(price-stop)>EPS else None,
            "gap_entry":raw != (row["submitted_limit"] if row["order_type"]=="limit" else row["initial_stop_anchor"]),
            "ambiguous":path_ambiguous,"excursion_ambiguous":False,
            "mfe_points":0.0,"mae_points":0.0,"slippage_ticks":cfg.slippage_ticks,
            "commission_per_side":cfg.commission_per_side,"ordering":cfg.ordering,
            "execution_minutes":cfg.execution_minutes,"fill_model":cfg.fill_model,
            "entry_after_baseline_exit":baseline_state(e,at)["baseline_position_status"]=="flat" if baseline_state(e,at)["baseline_position_status"]!="unknown" else None,
            "entry_improvement_points":direction*(e.entry_price_raw-raw) if direction==e.direction else None,
            "censor_reason":None}
        trade.update(entry_cohort(at))
        trade.update({key+"_at_signal":value for key,value in baseline_state(e,instant(row["signal_available_at"])).items()})
        pos={"trade":trade,"stop":stop,"entry":price,"entry_bucket":bucket(at),"entry_time":at,
             "mfe":0.0,"mae":0.0,"reset":False,"market_queued":False,"reset_queued":False}
        row.update(fill=True,fill_time=iso(at),fill_time_precision=precision,opportunity=True)
        row["events"].append({"event":"fill","time":iso(at),"raw_price":raw,"actual_price":price,"initial_stop":stop,"risk_initial_points":trade["risk_initial_points"]})
        pending=False

    def mark(price: float):
        if pos is None:
            return
        move=direction*(price-pos["entry"])
        pos["mfe"]=max(pos["mfe"],move)
        pos["mae"]=max(pos["mae"],-move)

    def finish(at: datetime,reason: str,raw: float | None=None,precision="observed_open",*,censored=False,competing=False):
        nonlocal pos
        assert pos is not None
        trade=pos["trade"]
        if raw is not None:
            mark(raw)
        trade.update(status="censored" if censored else "completed",censor_reason=reason if censored else None,
            exit_reason=None if censored else reason,last_observed_at=iso(at),
            mfe_points=pos["mfe"],mae_points=pos["mae"],excursions_complete=not censored,
            competing_exit_orders=competing)
        if censored:
            trade.update(exit_time=None,exit_time_latest=None,exit_price_raw=None,exit_price=None,
                gross_points=None,gross_dollars=None,raw_price_points=None,raw_price_dollars=None,
                commission_dollars=None,net_points=None,net_dollars=None,gross_r=None,net_r=None,
                source_style_r=None,holding_minutes=None,holding_bars=None,
                holding_minutes_lower=None,holding_minutes_upper=None,
                observed_holding_minutes=(at-pos["entry_time"]).total_seconds()/60)
            row.update(status="filled_censored",unknown=True,net_dollars=None,reason=reason)
        else:
            assert raw is not None
            actual=raw-direction*slip
            gross=direction*(actual-pos["entry"])
            raw_points=direction*(raw-trade["entry_price_raw"])
            cost=2*cfg.commission_per_side*quantity
            net=gross*cfg.point_value*quantity-cost
            risk=trade["risk_initial_dollars"]
            active_risk=abs(pos["entry"]-pos["stop"])*cfg.point_value*quantity
            entry_latest=instant(trade["entry_time_latest"])
            exit_latest=at+timedelta(minutes=cfg.execution_minutes) if precision=="within_bar" else at
            trade.update(exit_time=iso(at),exit_time_latest=iso(exit_latest),exit_time_precision=precision,
                exit_price_raw=raw,exit_price=actual,gross_points=gross,gross_dollars=gross*cfg.point_value*quantity,
                raw_price_points=raw_points,raw_price_dollars=raw_points*cfg.point_value*quantity,
                commission_dollars=cost,net_points=net/(cfg.point_value*quantity),net_dollars=net,
                gross_r=gross*cfg.point_value*quantity/risk if risk else None,net_r=net/risk if risk else None,
                source_style_r=net/active_risk if active_risk>EPS else None,
                source_risk_dollars=active_risk if active_risk>EPS else None,
                holding_minutes=(at-pos["entry_time"]).total_seconds()/60,
                holding_bars=int((bucket(at)-pos["entry_bucket"]).total_seconds()/900),
                holding_minutes_lower=max(0,(at-entry_latest).total_seconds()/60),
                holding_minutes_upper=max(0,(exit_latest-pos["entry_time"]).total_seconds()/60))
            row.update(status="filled_complete",unknown=False,net_dollars=net,reason=None)
        row["trade"]=trade
        row["events"].append({"event":"censor" if censored else "exit","time":iso(at),"reason":reason,"raw_price":raw})
        pos=None

    for bar in execution:
        if bar.timestamp<due:
            continue
        if bar.timestamp>e.cutoff+QUARTER:
            break
        if pending and bar.timestamp>=e.cutoff:
            break
        uncertain=ctx.first_uncertain(last_end,bar.timestamp+MINUTE)
        if uncertain and not source_gap:
            if pos is not None:
                finish(uncertain[0],uncertain[1],censored=True)
                return row
            return _status(row,"unknown_fill",uncertain[1])
        if ctx.contract_barrier is not None and bar.timestamp>=ctx.contract_barrier:
            if pos is not None:
                finish(ctx.contract_barrier,"contract_transition",censored=True)
                return row
            return _status(row,"unknown_fill","contract_transition")
        if bar.contract!=e.contract:
            continue
        if pending and fill_is_market:
            # The scheduled opening PRICE is independent of whether the rest
            # of that 15m candle later becomes incomplete.
            expected=ctx.minute_index.get(due)
            if expected is None and not source_gap:
                return _status(row,"unknown_fill","scheduled_open_price_missing")
            if bar.timestamp>due and not source_gap:
                return _status(row,"unknown_fill","scheduled_execution_open_missing")
            raw=expected.open if expected is not None and bar.timestamp==due else bar.open
            start(raw,bar.timestamp,"observed_open")
        if pos is not None:
            through=direction*relation(bar.open,pos["stop"])<=0
            competing=pos["market_queued"] and (through or pos["reset_queued"])
            if pos["market_queued"]:
                finish(bar.timestamp,"stop" if competing and cfg.timed_exit_priority=="stop_first" else "time",bar.open,competing=competing)
                return row
            if pos["reset_queued"] or through:
                finish(bar.timestamp,"stop",bar.open)
                return row
        opening_relation=direction*relation(bar.open,row["submitted_limit"]) if row["submitted_limit"] is not None else 1
        if pending and not fill_is_market and (opening_relation<0 or opening_relation==0 and row["trade_through_ticks"]==0):
            # Favorable opening gaps fill at the actual open without requiring
            # an extra tick; preserve even gap-through-initial-stop entries.
            start(bar.open,bar.timestamp,"observed_open")
            if direction*relation(bar.open,pos["stop"])<=0:
                finish(bar.timestamp,"stop",bar.open)
                return row
        if cfg.execution_minutes==15:
            decision=ctx.candle_index.get(bar.timestamp)
            if decision is None or not ctx.complete(decision):
                first=ctx.first_uncertain(bar.timestamp,bar.timestamp+QUARTER)
                if pos is not None:
                    finish(first[0] if first else bar.timestamp,"source_15m_candle_unusable",censored=True)
                    return row
                return _status(row,"unknown_fill","source_15m_candle_unusable")
        path=price_path(bar,cfg.ordering)
        for a,b in zip(path,path[1:]):
            if pending:
                level=row["submitted_limit"]
                trigger=level-direction*row["trade_through_ticks"]*cfg.tick_size
                crossing=direction*relation(a,trigger)>0 and direction*relation(b,trigger)<=0
                if crossing:
                    ambiguous=(relation(bar.low,row["initial_stop"])<=0 if direction==1 else relation(bar.high,row["initial_stop"])>=0)
                    start(level,bar.timestamp,"within_bar",path_ambiguous=ambiguous)
                    # Fill requires evidence at the trade-through price. The
                    # standing limit itself executes at its submitted price.
                    a=trigger
            if pos is not None:
                mark(a)
                through_a=direction*relation(a,pos["stop"])<=0
                through_b=direction*relation(b,pos["stop"])<=0
                if through_a or through_b:
                    favorable=bar.high if direction==1 else bar.low
                    pos["trade"]["excursion_ambiguous"]|=direction*(favorable-pos["entry"])>pos["mfe"]+EPS
                    finish(bar.timestamp,"stop",a if through_a else pos["stop"],"within_bar")
                    return row
                mark(b)
        end=bar.timestamp+timedelta(minutes=cfg.execution_minutes)
        last_end=end
        if pos is not None and end==bucket(bar.timestamp)+QUARTER:
            decision=ctx.candle_index.get(bucket(bar.timestamp))
            if decision is None or not ctx.complete(decision):
                if not source_gap:
                    finish(end,"incomplete_decision_candle",censored=True)
                    return row
            if not pos["reset"] and pos["entry_bucket"]==bucket(bar.timestamp):
                if cfg.stop_mode=="percent":
                    reset=percentage_stop(pos["entry"],direction,cfg.stop_percent,cfg.tick_size)
                    pos["stop"]=reset
                    effective=direction*(pos["entry"]-reset)
                    pos["trade"].update(reset_stop=reset,reset_stop_active_at=iso(end),
                        risk_effective_points=effective if effective>EPS else None,
                        risk_effective_dollars=effective*cfg.point_value*quantity if effective>EPS else None,
                        source_risk_dollars=abs(pos["entry"]-reset)*cfg.point_value*quantity)
                    pos["reset_queued"]=direction*relation(bar.close,reset)<=0
                    row["events"].append({"event":"stop_reset","time":iso(end),"stop":reset,"triggered_at_creation":pos["reset_queued"]})
                pos["reset"]=True
            if end>=e.cutoff:
                pos["market_queued"]=True
    if pos is not None:
        missing=ctx.first_uncertain(last_end,e.cutoff+MINUTE)
        finish(missing[0] if missing else last_end,missing[1] if missing else "retained_endpoint_open",censored=True)
        return row
    if pending:
        missing=ctx.first_uncertain(due,e.cutoff)
        if missing:
            return _status(row,"unknown_fill",missing[1])
        return _status(row,"known_no_fill","resting_order_expired_unfilled")
    return row


def run_policy(ctx: EpisodeContext, policy: PolicySpec, config: Phase2Config | None = None,
               *, quantity: float=1.0) -> dict[str,Any]:
    cfg=config or Phase2Config()
    return execute_signal(find_signal(ctx,policy,cfg),ctx,cfg,quantity=quantity)


def _detail(ctx: EpisodeContext,bar: Bar,price: float,index: int,*,exact: bool) -> dict[str,Any]:
    at=bar.timestamp
    opening=index==0 and at!=ctx.episode.entry_time
    latest=at if opening else at+MINUTE
    return {"time":iso(at),"time_latest":iso(latest),"available_at":iso(bar.available_at or at+MINUTE),
        "precision":"observed_open" if opening else "within_1m","price":price,
        "bar_open":iso(bucket(at)),"exact_first":exact}


def _close_detail(ctx: EpisodeContext,bar: DecisionBar,*,exact: bool) -> dict[str,Any]:
    return {"time":iso(bar.end),"time_latest":iso(bar.end),"available_at":iso(bar.end),
        "precision":"confirmed_15m_close","price":bar.close,"bar_open":iso(bar.timestamp),"exact_first":exact}


def _nodes(ctx: EpisodeContext,end: datetime,ordering: str):
    for bar in ctx.observed_after_fill(end):
        path=post_fill_path(bar,ctx.episode,ordering)
        previous=None
        for index,price in enumerate(path):
            if previous is not None and relation(price,previous)==0:
                continue
            yield bar,index,price
            previous=price


def _confirmations(ctx: EpisodeContext,end: datetime,include_endpoint: bool):
    for bar in ctx.candles:
        if bar.timestamp<ctx.episode.breakout_bar_open or bar.end<=ctx.episode.entry_time or bar.timestamp>=end:
            continue
        if bar.end<end or (include_endpoint and bar.end==end):
            if ctx.complete(bar):
                yield bar


def _protected_branch(ctx: EpisodeContext,end: datetime,include_endpoint: bool,ordering: str,tick: float) -> dict[str,Any]:
    e=ctx.episode
    first={key:None for key in ["touch","one_tick_breach","close_break","reclaim"]}
    recovery_levels={"opposite_boundary":e.protected_boundary,"midpoint":e.midpoint,"original_boundary":e.original_boundary}
    recovery={key:{"touch":None,"close_reclaim":None} for key in recovery_levels}
    counts={"touch":0,"one_tick_breach":0}
    active={"touch":False,"one_tick_breach":False}
    for bar,index,price in _nodes(ctx,end,ordering):
        exact=not ctx.uncertain(e.entry_time,bar.timestamp+MINUTE) and not e.ambiguous
        for event,threshold in [("touch",e.protected_boundary),("one_tick_breach",e.protected_boundary-e.direction*tick)]:
            now=e.direction*relation(price,threshold)<=0
            if now and not active[event]:
                counts[event]+=1
                if first[event] is None:
                    first[event]=_detail(ctx,bar,threshold if index else price,index,exact=exact)
            active[event]=now
        if first["one_tick_breach"] is not None:
            for level,reference in recovery_levels.items():
                if recovery[level]["touch"] is None and e.direction*relation(price,reference)>=0:
                    recovery[level]["touch"]=_detail(ctx,bar,reference if index else price,index,exact=exact)
    breach_bar=instant(first["one_tick_breach"]["bar_open"]) if first["one_tick_breach"] else None
    for bar in _confirmations(ctx,end,include_endpoint):
        exact=not ctx.uncertain(e.entry_time,bar.end) and not e.ambiguous
        distance=e.direction*relation(bar.close,e.protected_boundary)
        if distance<0 and first["close_break"] is None:
            first["close_break"]=_close_detail(ctx,bar,exact=exact)
        if breach_bar is not None and bar.timestamp>breach_bar:
            if distance>0 and first["reclaim"] is None:
                first["reclaim"]=_close_detail(ctx,bar,exact=exact)
            for level,reference in recovery_levels.items():
                if e.direction*relation(bar.close,reference)>0 and recovery[level]["close_reclaim"] is None:
                    recovery[level]["close_reclaim"]=_close_detail(ctx,bar,exact=exact)
    complete=not ctx.uncertain(e.entry_time,end)
    states={key:True if detail else False if complete else None for key,detail in first.items()}
    recovery_states={level:{kind:True if detail else False if complete and states["one_tick_breach"] else None
        for kind,detail in record.items()} for level,record in recovery.items()}
    return {"states":states,"first":first,"counts":counts,"recovery":recovery,
            "recovery_states":recovery_states,"complete":complete}


def _merge_event(ctx: EpisodeContext,event: str,branches: Sequence[dict[str,Any]],primary: dict[str,Any],
                 *,details_key="first",states_key="states") -> dict[str,Any]:
    e=ctx.episode
    states=[branch[states_key][event] for branch in branches]
    state=states[0] if states[0]==states[1] else None
    details=[branch[details_key][event] for branch in branches]
    primary_detail=primary[details_key][event]
    known_same=state is True and all(detail is not None and detail["exact_first"] for detail in details) and all(details[0][key]==details[1][key] for key in ["time","time_latest","available_at"])
    observed=primary_detail or next((detail for detail in details if detail is not None),None)
    first_time=details[0]["time"] if known_same else None
    first_latest=details[0]["time_latest"] if known_same else None
    at=instant(first_time)
    observed_at=instant(observed["time"]) if observed else None
    cohort=entry_cohort(at) if at else {}
    observed_cohort=entry_cohort(observed_at) if observed_at else {}
    entry_latest=e.entry_time_latest or e.entry_time
    return {"event":event,"occurred":state,"ordering_ambiguous":states[0]!=states[1],
        "first_time":first_time,"first_time_latest":first_latest,
        "first_available_at":details[0]["available_at"] if known_same else None,
        "first_time_exact_observation":known_same,
        "first_observed_time":observed["time"] if observed else None,
        "first_observed_available_at":observed["available_at"] if observed else None,
        "time_precision":observed["precision"] if observed else None,
        "source_ohlc_estimated_first_time":primary_detail["time"] if primary_detail else None,
        "elapsed_minutes_lower":max(0,(at-entry_latest).total_seconds()/60) if at else None,
        "elapsed_minutes_upper":max(0,(instant(first_latest)-e.entry_time).total_seconds()/60) if at else None,
        "event_year":cohort.get("entry_year"),"event_session":cohort.get("entry_session"),
        "observed_event_year":observed_cohort.get("entry_year"),"observed_event_session":observed_cohort.get("entry_session"),
        **({key+"_at_event":value for key,value in baseline_state(e,at).items()} if at else
           {"baseline_position_status_at_event":None,"baseline_loss_known_at_event":None})}


def observe_episode(ctx: EpisodeContext, config: Phase2Config | None = None) -> dict[str,list[dict[str,Any]]]:
    """Protected occurrence and price recovery on both prespecified horizons.

    True observed events survive subsequent gaps. False requires complete
    exposure. Two feasible OHLC orders are compared; disagreement is null. Exact
    first event timing is withheld after any unobserved prefix. Repeated contacts
    describe the episode and never become independent observations.
    """
    cfg=config or Phase2Config()
    e=ctx.episode
    same_end,session,clamped=session_horizon_end(e.entry_time,e.cutoff)
    horizons=[("original_session",same_end,clamped),("remaining_broker_window",e.cutoff,True)]
    occurrence,recovery,events=[],[],[]
    original_cohort=entry_cohort(e.entry_time)
    for horizon,end,include in horizons:
        high=_protected_branch(ctx,end,include,"high_first",cfg.tick_size)
        low=_protected_branch(ctx,end,include,"low_first",cfg.tick_size)
        source=_protected_branch(ctx,end,include,cfg.ordering,cfg.tick_size)
        scheduled=observed=0
        cursor=e.entry_time
        while cursor<end:
            if ctx.expected_minute(cursor):
                scheduled+=1
                if cursor in ctx.minute_index and ctx.minute_index[cursor].contract==e.contract and (ctx.contract_barrier is None or cursor<ctx.contract_barrier):
                    observed+=1
            cursor+=MINUTE
        base={"episode_id":e.episode_id,"broker_day":e.broker_day,"contract":e.contract,
            "original_direction":e.direction,"original_side":"long" if e.direction==1 else "short",
            "protected_side":"low" if e.direction==1 else "high","original_entry_time":iso(e.entry_time),
            "original_year":original_cohort["entry_year"],"original_session":original_cohort["entry_session"],
            "horizon":horizon,"horizon_end":iso(end),"close_confirmation_endpoint_included":include,
            "complete_observation":high["complete"] and low["complete"],
            "scheduled_exposure_minutes":scheduled,"observed_exposure_minutes":observed,
            "wall_exposure_minutes":max(0,(end-e.entry_time).total_seconds()/60)}
        for event in ["touch","one_tick_breach","close_break","reclaim"]:
            row={**base,**_merge_event(ctx,event,[high,low],source)}
            if event in {"touch","one_tick_breach"}:
                counts=[high["counts"][event],low["counts"][event]]
                known_count=counts[0] if counts[0]==counts[1] and base["complete_observation"] else None
                row.update(contact_count=known_count,repeat_contacts=max(known_count-1,0) if known_count is not None else None,
                    observed_contacts_lower=min(counts),observed_contacts_upper=max(counts),
                    total_contacts_upper=max(counts) if base["complete_observation"] else None,
                    observed_repeat_contacts_lower=max(min(counts)-1,0),observed_repeat_contacts_upper=max(max(counts)-1,0),
                    total_repeat_contacts_upper=max(max(counts)-1,0) if base["complete_observation"] else None)
            occurrence.append(row)
            if row["first_observed_time"]:
                events.append({**row,"event_family":"protected_boundary"})
        breach_known=high["states"]["one_tick_breach"] if high["states"]["one_tick_breach"]==low["states"]["one_tick_breach"] else None
        for level,reference in [("opposite_boundary",e.protected_boundary),("midpoint",e.midpoint),("original_boundary",e.original_boundary)]:
            for kind in ["touch","close_reclaim"]:
                # Reuse the event merge for level-specific branch dictionaries.
                branches=[{"states":{kind:b["recovery_states"][level][kind]},"first":{kind:b["recovery"][level][kind]}} for b in [high,low]]
                primary={"states":{kind:source["recovery_states"][level][kind]},"first":{kind:source["recovery"][level][kind]}}
                row={**base,"recovery_level":level,"reference_price":reference,"breach_occurred":breach_known,
                    "not_executed_trade_target":True,**_merge_event(ctx,kind,branches,primary)}
                recovery.append(row)
    return {"occurrence":occurrence,"recovery":recovery,"events":events}


def _level_branch(ctx: EpisodeContext,fraction: float,end: datetime,include_endpoint: bool,ordering: str,cfg: Phase2Config) -> dict[str,Any]:
    e=ctx.episode
    level=e.level(fraction)
    stop=percentage_stop(level,e.direction,cfg.stop_percent,cfg.tick_size)
    risk=e.direction*(level-stop)
    first={"touch":None,"inward_close":None,"outward_reclaim":None}
    contacts=0
    active=False
    recovery=None
    excursion=None
    max_mfe=max_mae=0.0
    deepest=0.0
    first_touch_time=None
    for bar,index,price in _nodes(ctx,end,ordering):
        penetration=e.direction*(e.original_boundary-price)/(e.range_high-e.range_low)
        deepest=max(deepest,penetration)
        at_initial=bar.timestamp==e.entry_time and index==0
        now=e.direction*relation(price,level)<=0
        if now and not active and not (fraction==0 and at_initial):
            contacts+=1
            if first["touch"] is None:
                exact=not ctx.uncertain(e.entry_time,bar.timestamp+MINUTE) and not e.ambiguous
                first["touch"]=_detail(ctx,bar,level if index else price,index,exact=exact)
                first_touch_time=bar.timestamp
        # Original q0 boundary fill itself never becomes a return opportunity.
        active=now if not (fraction==0 and at_initial) else False
        if first["touch"] is not None:
            move=e.direction*(price-level)
            max_mfe=max(max_mfe,move)
            max_mae=max(max_mae,-move)
            complete_since_touch=not ctx.uncertain(first_touch_time,bar.timestamp+MINUTE)
            if recovery is None:
                if e.direction*relation(price,e.protected_boundary)<=0:
                    recovery=False if complete_since_touch else None
                elif e.direction*relation(price,e.original_boundary)>=0:
                    recovery=True if complete_since_touch else None
            if excursion is None and risk>EPS:
                if relation(move,risk)>=0:
                    excursion="favorable" if complete_since_touch else "unknown"
                elif relation(move,-risk)<=0:
                    excursion="adverse" if complete_since_touch else "unknown"
    arm_bar=None
    for bar in _confirmations(ctx,end,include_endpoint):
        inward=e.direction*relation(bar.close,level)
        exact=not ctx.uncertain(e.entry_time,bar.end) and not e.ambiguous
        if first["inward_close"] is None and inward<=0:
            first["inward_close"]=_close_detail(ctx,bar,exact=exact)
            arm_bar=bar.timestamp
        elif arm_bar is not None and bar.timestamp>arm_bar and inward>0 and first["outward_reclaim"] is None:
            first["outward_reclaim"]=_close_detail(ctx,bar,exact=exact)
    complete=not ctx.uncertain(e.entry_time,end)
    if recovery is None and first["touch"] is not None and complete:
        recovery=False
    if excursion is None and first["touch"] is not None and complete:
        excursion="neither"
    states={key:True if value else False if complete else None for key,value in first.items()}
    return {"states":states,"first":first,"contacts":contacts,"complete":complete,
        "range_recovery":recovery,"excursion_first":excursion,"event_risk_points":risk if risk>EPS else None,
        "mfe_after_touch_points":max_mfe if first["touch"] else None,
        "mae_after_touch_points":max_mae if first["touch"] else None,
        "deepest_range_fraction":deepest}


def observe_levels(ctx: EpisodeContext, config: Phase2Config | None=None) -> list[dict[str,Any]]:
    """Raw post-fill returns/reclaims and conditional path diagnostics to cutoff."""
    cfg=config or Phase2Config()
    e=ctx.episode
    original=entry_cohort(e.entry_time)
    rows=[]
    for q in [0,.25,.5,.75]:
        high=_level_branch(ctx,q,e.cutoff,True,"high_first",cfg)
        low=_level_branch(ctx,q,e.cutoff,True,"low_first",cfg)
        source=_level_branch(ctx,q,e.cutoff,True,cfg.ordering,cfg)
        recovery=high["range_recovery"] if high["range_recovery"]==low["range_recovery"] else None
        excursion=high["excursion_first"] if high["excursion_first"]==low["excursion_first"] else "unknown"
        for event in ["touch","inward_close","outward_reclaim"]:
            merged=_merge_event(ctx,event,[high,low],source)
            known_count=high["contacts"] if high["contacts"]==low["contacts"] and high["complete"] else None
            rows.append({"episode_id":e.episode_id,"broker_day":e.broker_day,"contract":e.contract,
                "original_direction":e.direction,"original_year":original["entry_year"],"original_session":original["entry_session"],
                "fraction":q,"raw_level":e.level(q),"horizon_end":iso(e.cutoff),
                "complete_observation":high["complete"] and low["complete"],**merged,
                "contact_count":known_count,"repeat_contacts":max(known_count-1,0) if known_count is not None else None,
                "observed_contacts_lower":min(high["contacts"],low["contacts"]),
                "observed_contacts_upper":max(high["contacts"],low["contacts"]),
                "observed_repeat_contacts_lower":max(min(high["contacts"],low["contacts"])-1,0),
                "observed_repeat_contacts_upper":max(max(high["contacts"],low["contacts"])-1,0),
                "range_recovery_before_opposite":recovery,"excursion_first_1R":excursion,
                "excursion_success":True if excursion=="favorable" else False if excursion in {"adverse","neither"} else None,
                "event_risk_points":source["event_risk_points"],
                "mfe_after_touch_points":source["mfe_after_touch_points"],"mae_after_touch_points":source["mae_after_touch_points"],
                "deepest_range_fraction":source["deepest_range_fraction"],"not_realized_trade_return":True})
    return rows
