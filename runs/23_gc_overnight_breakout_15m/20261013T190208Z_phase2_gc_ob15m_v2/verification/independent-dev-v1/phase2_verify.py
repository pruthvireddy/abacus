"""Independent Phase 2 oracle and saved evidence reconciliation.

This verifier deliberately imports neither the Phase 2 producer engine nor its
metrics/runner. It walks the pinned minute calendar using dictionary state and
Decimal thresholds. No alternative-policy results are created in a completed
Phase 1 directory. Verification receipts are append-only in the new work stage.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
import gzip
import hashlib
import json
import math
import csv
from pathlib import Path
from statistics import mean, median
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

UTC = timezone.utc
NY = ZoneInfo("America/New_York")
BROKER = timezone(timedelta(hours=3))
ONE = timedelta(minutes=1)
FIFTEEN = timedelta(minutes=15)
TICK = Decimal("0.1")
PRIMARY = ("reclaim-q000", "reclaim-q025", "reclaim-q050", "reclaim-q075")
PROTECTED = ("protected-touch-hold", "protected-failed-break-reclaim", "protected-reversal")
PASSIVE = ("passive-q025", "passive-q050", "passive-q075")


def dt(value):
    if value in (None, ""):
        return None
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("aware timestamps required")
    return result.astimezone(UTC)


def iso(value):
    return None if value is None else dt(value).isoformat().replace("+00:00", "Z")


def floor15(value):
    value = dt(value)
    return value.replace(minute=value.minute//15*15, second=0, microsecond=0)


def decimal(value):
    # Prices are pinned multiples of 0.1 or rational derived thresholds. This
    # removes only machine noise <1e-9, never rounds theoretical q thresholds.
    return Decimal(str(round(float(value), 9)))


def cmp(a, b):
    a, b = decimal(a), decimal(b)
    return (a > b) - (a < b)


def stop_price(anchor, direction, percent=1):
    ticks = decimal(anchor)*(Decimal(1)-Decimal(direction)*decimal(percent)/100)/TICK
    return float(ticks.to_integral_value(rounding=ROUND_HALF_UP)*TICK)


def limit_price(raw, direction):
    return float((decimal(raw)/TICK).to_integral_value(rounding=ROUND_FLOOR if direction==1 else ROUND_CEILING)*TICK)


def cohort_at(value):
    local=dt(value).astimezone(NY)
    clock=local.hour*60+local.minute
    session="Asia" if clock>=1200 or clock<120 else "London" if clock<540 else "New York" if 570<=clock<960 else "Outside"
    return {"year":str(local.year),"session":session,"hour":local.hour,"weekday":local.strftime("%A"),"entry_ny":local.isoformat()}


def source_cohort(value):
    c=cohort_at(value)
    local=dt(value).astimezone(NY)
    broker=dt(value).astimezone(BROKER)
    names={"Asia":"asia","London":"london","New York":"new_york","Outside":"outside_named_sessions"}
    return {"entry_year":int(c["year"]),"entry_date_ny":local.date().isoformat(),"entry_time_ny":c["entry_ny"],"entry_session":names[c["session"]],"entry_hour":c["hour"],"entry_weekday":local.weekday(),"entry_weekday_name":c["weekday"],"minutes_from_trading_start":(broker-broker.replace(hour=7,minute=0,second=0,microsecond=0)).total_seconds()/60}


def horizon_end(entry, cutoff):
    local=dt(entry).astimezone(NY)
    clock=local.hour*60+local.minute
    day=local.date()
    if clock>=1200:
        end=datetime.combine(day+timedelta(days=1),time(2),NY)
    elif clock<120:
        end=datetime.combine(day,time(2),NY)
    elif clock<540:
        end=datetime.combine(day,time(9),NY)
    elif clock<570:
        end=datetime.combine(day,time(9,30),NY)
    elif clock<960:
        end=datetime.combine(day,time(16),NY)
    else:
        end=datetime.combine(day,time(20),NY)
    end=end.astimezone(UTC)
    return min(end,dt(cutoff)), dt(cutoff)<end


def route(bar, ordering="source_ohlc"):
    o,h,l,c=(float(bar[k]) for k in ("open","high","low","close"))
    first_high=ordering=="high_first" or ordering=="source_ohlc" and decimal(h)-decimal(o)<decimal(o)-decimal(l)
    return (o,h,l,c) if first_high else (o,l,h,c)


def after_original_fill(bar, episode, ordering="source_ohlc"):
    points=route(bar,ordering)
    if dt(bar["timestamp"])!=dt(episode["entry_time"]) or episode.get("entry_time_precision")=="observed_open":
        return points
    trigger=float(episode["entry_price_raw"])
    direction=int(episode["direction"])
    for i,(a,b) in enumerate(zip(points,points[1:])):
        if direction==1 and a<=trigger<=b or direction==-1 and b<=trigger<=a:
            return (trigger,*points[i+1:])
    raise ValueError("original pinned fill cannot be traced in observed candle")


@dataclass
class OracleInput:
    episode: dict
    minutes: list[dict]
    candles: list[dict]
    expected: set[datetime]

    def __post_init__(self):
        self.episode=dict(self.episode)
        e=self.episode
        e["entry_time"]=dt(e["entry_time"])
        e["b"]=floor15(e["entry_time"])
        e["available"]=e["b"]+FIFTEEN
        e["cutoff"]=datetime.combine(datetime.fromisoformat(e["broker_day"]).date(),time(20),BROKER).astimezone(UTC)
        self.minutes=[dict(x,timestamp=dt(x["timestamp"])) for x in self.minutes]
        self.candles=[dict(x,timestamp=dt(x["timestamp"])) for x in self.candles]
        if len({x["timestamp"] for x in self.minutes})!=len(self.minutes):
            raise ValueError("duplicate minute")
        self.m={x["timestamp"]:x for x in self.minutes}
        self.bars={x["timestamp"]:x for x in self.candles}
        self.expected={dt(x) for x in self.expected}
        self.missing=sorted(x for x in self.expected if e["b"]<=x<=e["cutoff"] and x not in self.m)
        self.roll=next((x["timestamp"] for x in sorted(self.minutes,key=lambda x:x["timestamp"]) if e["entry_time"]<=x["timestamp"]<e["cutoff"] and x["contract"]!=e["contract"]),None)

    def uncertain(self, start, end):
        bad=[(x,"missing_expected_execution_minutes") for x in self.missing if dt(start)<=x<dt(end)]
        if self.roll is not None and dt(start)<=self.roll<dt(end):
            bad.append((self.roll,"contract_transition"))
        return min(bad) if bad else None

    def complete(self, bar):
        t=bar["timestamp"]
        return bool(bar.get("complete",bar.get("usable",False))) and bar["contract"]==self.episode["contract"] and self.uncertain(t,t+FIFTEEN) is None and (self.roll is None or self.roll>=t+FIFTEEN)

    def postfill(self, end, ordering):
        e=self.episode
        return [(x,after_original_fill(x,e,ordering)) for x in self.minutes if e["entry_time"]<=x["timestamp"]<end and (self.roll is None or x["timestamp"]<self.roll)]


def baseline_state(e, when):
    when=dt(when)
    exit_time=dt(e.get("exit_time",e.get("baseline_exit_time")))
    if e.get("status",e.get("baseline_status"))=="completed" and exit_time is not None:
        latest=dt(e.get("exit_time_latest",e.get("baseline_exit_time_latest"))) or exit_time
        precision=e.get("exit_time_precision",e.get("baseline_exit_time_precision","within_bar"))
        known=max(latest,floor15(exit_time)+FIFTEEN) if precision=="within_bar" else latest
        flat=known<=when if precision=="within_bar" else known<when
        net=e.get("net_dollars",e.get("baseline_net_dollars"))
        return {"baseline_position_status":"flat" if flat else "open","baseline_loss_known":net is not None and net<0 if flat else False,"baseline_realized_net_dollars":net if flat else None,"baseline_exit_known_at":iso(known)}
    censor=dt(e.get("last_observed_at",e.get("baseline_censor_at")))
    unknown=censor is not None and when>=censor
    return {"baseline_position_status":"unknown" if unknown else "open","baseline_loss_known":None if unknown else False,"baseline_realized_net_dollars":None,"baseline_exit_known_at":None}


def policy_details(name):
    if name.startswith("reclaim-") or name.startswith("passive-"):
        fraction=int(name.split("q")[1][:3])/100
        return name.split("-")[0],fraction,0 if name.endswith("-touch") else 1
    if name not in PROTECTED:
        raise ValueError("unregistered policy")
    return name.replace("-","_"),0.,1


def original_contact(ctx, threshold, end):
    direction=int(ctx.episode["direction"])
    outcomes=[any(any(direction*cmp(p,threshold)<=0 for p in path) for _,path in ctx.postfill(end,o)) for o in ("high_first","low_first")]
    if outcomes==[True,True]:
        return True
    if outcomes[0]!=outcomes[1] or ctx.uncertain(ctx.episode["entry_time"],end):
        return None
    return False


def oracle_signal(ctx, policy, *, stop_mode="percent"):
    e=ctx.episode
    kind,q,through=policy_details(policy)
    d=int(e["direction"])
    h,l=decimal(e["range_high"]),decimal(e["range_low"])
    theoretical=h-decimal(q)*(h-l) if d==1 else l+decimal(q)*(h-l)
    protected=l if d==1 else h
    level=float(theoretical) if kind in {"reclaim","passive"} else float(protected)
    row={"episode_id":e.get("trade_id",e.get("episode_id")),"policy":policy,"status":"known_no_fill","reason":None,"opportunity":False,"armed":False,"signal":False,"arming_at":None,"signal_available_at":None,"submitted_at":None,"expected_fill_time":None,"initial_stop_anchor":None,"initial_stop":None,"planned_risk_points":None,"submitted_limit":None,"order_type":None,"raw_level":level,"direction":-d if kind=="protected_reversal" else d,"fraction":q,"trade_through_ticks":through,"missed_before_arming":False,"unknown":False,"net_dollars":0.,"trade":None}
    row.update(broker_day=e["broker_day"],contract=e["contract"],policy_kind=kind,original_direction=d,original_side="long" if d==1 else "short",original_entry_time=iso(e["entry_time"]),direction_available_at=iso(e["available"]),cutoff=iso(e["cutoff"]))

    def end(status,reason):
        row.update(status=status,reason=reason,unknown=status.startswith("unknown"),net_dollars=None if status.startswith("unknown") else 0.)
        return row

    def submit(at,anchor,order_type,limit=None):
        direction=row["direction"]
        stop=float(l if direction==1 else h) if stop_mode=="opposite_boundary" else stop_price(anchor,direction)
        risk=direction*(anchor-stop)
        row.update(signal=True,signal_available_at=iso(at),initial_stop_anchor=anchor,initial_stop=stop,planned_risk_points=risk,order_type=order_type,submitted_limit=limit)
        row.update({k+"_at_signal":v for k,v in baseline_state(e,at).items()})
        if at>=e["cutoff"] or at.astimezone(BROKER).date().isoformat()!=e["broker_day"] or not 7<=at.astimezone(BROKER).hour<20:
            return end("known_no_fill","first_setup_has_no_eligible_next_open")
        if risk<=0:
            return end("known_no_fill","invalid_planned_risk_before_submission")
        row.update(status="submitted",net_dollars=None,submitted_at=iso(at),expected_fill_time=iso(at))
        return row

    b=ctx.bars.get(e["b"])
    if b is None or not ctx.complete(b):
        return end("unknown_signal","original_direction_candle_incomplete_or_unusable")
    if kind=="passive":
        limit=limit_price(level,d)
        row["submitted_limit"]=limit
        # A gap before b close invalidates the chronology even if later contact
        # was observed: passive eligibility requires a known unvisited prefix.
        if ctx.uncertain(e["entry_time"],e["available"]):
            return end("unknown_signal","post_fill_pre_submission_chronology_unknown")
        reached=original_contact(ctx,level,e["available"])
        if reached is None:
            return end("unknown_signal","post_fill_pre_submission_chronology_unknown")
        if reached:
            row.update(opportunity=True,missed_before_arming=True)
            return end("known_no_fill","missed_before_arming")
        row.update(armed=True,arming_at=iso(e["available"]))
        return submit(e["available"],limit,"limit",limit)
    breach_level=float(protected-Decimal(d)*TICK)
    if kind=="protected_failed_break_reclaim":
        row["prior_breach_before_actionable"]=original_contact(ctx,breach_level,e["available"])
    if kind=="protected_touch_hold" and original_contact(ctx,breach_level,e["available"]) is True:
        row["prior_breach_before_actionable"]=True
        return end("known_no_fill","one_tick_breach_disqualifies_touch_hold")
    first=None
    for bar in ctx.candles:
        t=bar["timestamp"]
        if t<=e["b"] or t>=e["cutoff"]:
            continue
        if ctx.uncertain(e["available"],t+FIFTEEN) or not ctx.complete(bar):
            return end("unknown_signal","uncertain_prefix_before_first_actionable_setup")
        inward=d*cmp(bar["close"],level)
        if kind=="reclaim":
            if first is None and (inward<0 if q==0 else inward<=0):
                first=t
                row.update(opportunity=True,armed=True,arming_at=iso(t+FIFTEEN))
            elif first is not None and t>first and inward>0:
                return submit(t+FIFTEEN,float(bar["close"]),"market")
        elif kind=="protected_touch_hold":
            breached=original_contact(ctx,breach_level,t+FIFTEEN)
            if breached is True:
                return end("known_no_fill","one_tick_breach_disqualifies_touch_hold")
            touched=d*cmp(bar["low" if d==1 else "high"],protected)<=0
            if touched and inward>0:
                row.update(opportunity=True,armed=True,arming_at=iso(t+FIFTEEN))
                if breached is None:
                    return end("unknown_signal","touch_hold_no_prior_breach_unresolved")
                return submit(t+FIFTEEN,float(bar["close"]),"market")
        elif kind=="protected_failed_break_reclaim":
            breached=d*cmp(bar["low" if d==1 else "high"],breach_level)<=0
            if first is None and breached:
                first=t
                row.update(opportunity=True,armed=True,arming_at=iso(t+FIFTEEN))
            elif first is not None and t>first and inward>0:
                return submit(t+FIFTEEN,float(bar["close"]),"market")
        elif inward<0:
            row.update(opportunity=True,armed=True,arming_at=iso(t+FIFTEEN))
            return submit(t+FIFTEEN,float(bar["close"]),"market")
    if ctx.uncertain(e["available"],e["cutoff"]):
        return end("unknown_signal","unobserved_remaining_first_setup")
    return end("known_no_fill","no_first_qualifying_setup_before_cutoff")


def oracle_execute(ctx, signal, *, ordering="source_ohlc", slippage_ticks=1, commission=2.5,
                   execution_minutes=1, fill_model="scheduled_open", stop_mode="percent",
                   timed_exit_priority="market_first", quantity=1):
    row=dict(signal)
    if row["status"]!="submitted":
        return row
    if quantity<1:
        row.update(status="known_no_fill",reason="quantity_below_one_contract",submitted_at=None,expected_fill_time=None,net_dollars=0.,quantity_skipped=True)
        return row
    if not float(quantity).is_integer():
        raise ValueError("whole GC quantities only")
    e=ctx.episode
    d=row["direction"]
    slip=.1*slippage_ticks
    due=dt(row["submitted_at"])
    source_gap=fill_model=="next_observed_open_sensitivity"
    row.update(execution_minutes=execution_minutes,fill_model=fill_model,quantity=quantity,stop_mode=stop_mode)
    sequence=ctx.minutes if execution_minutes==1 else ctx.candles
    position=None
    previous_end=due
    mfe=mae=0.
    reset_queued=market_queued=False

    def unknown(at,reason):
        nonlocal position
        if position is None:
            row.update(status="unknown_fill",reason=reason,unknown=True,net_dollars=None)
        else:
            position.update(status="censored",censor_reason=reason,last_observed_at=iso(at),exit_time=None,exit_price_raw=None,exit_price=None,exit_reason=None,mfe_points=mfe,mae_points=mae,excursions_complete=False)
            for key in ("raw_price_points","raw_price_dollars","gross_points","gross_dollars","commission_dollars","net_points","net_dollars","gross_r","net_r","source_style_r","holding_minutes","holding_bars","holding_minutes_lower","holding_minutes_upper"):
                position[key]=None
            position["observed_holding_minutes"]=(at-dt(position["entry_time"])).total_seconds()/60
            row.update(status="filled_censored",reason=reason,unknown=True,net_dollars=None,trade=position)
        return row

    def mark(price):
        nonlocal mfe,mae
        move=d*(price-position["entry_price"])
        mfe=max(mfe,move)
        mae=max(mae,-move)

    def fill(raw,t,precision,ambiguous=False):
        nonlocal position
        actual=raw+d*slip
        initial=row["initial_stop"]
        risk=d*(actual-initial)
        position={"episode_id":row["episode_id"],"broker_day":e["broker_day"],"contract":e["contract"],"policy":row["policy"],"direction":d,"side":"long" if d==1 else "short","quantity":quantity,"entry_time":iso(t),"entry_time_latest":iso(t+timedelta(minutes=execution_minutes)) if precision=="within_bar" else iso(t),"entry_time_precision":precision,"entry_price_raw":raw,"entry_price":actual,"initial_stop":initial,"initial_stop_anchor":row["initial_stop_anchor"],"initial_stop_active_at":row["submitted_at"],"reset_stop":None,"reset_stop_active_at":None,"planned_risk_points":row["planned_risk_points"],"risk_initial_points":risk if risk>0 else None,"risk_initial_dollars":risk*100*quantity if risk>0 else None,"risk_effective_points":risk if risk>0 else None,"risk_effective_dollars":risk*100*quantity if risk>0 else None,"source_risk_dollars":abs(actual-initial)*100*quantity if actual!=initial else None,"gap_entry":cmp(raw,row["submitted_limit"] if row["order_type"]=="limit" else row["initial_stop_anchor"])!=0,"ambiguous":ambiguous,"excursion_ambiguous":False,"censor_reason":None,"stop":initial}
        position.update(trade_id=f"{row['episode_id']}:{row['policy']}:{ordering}:{slippage_ticks}",policy_kind=row["policy_kind"],fraction=row["fraction"],original_side="long" if e["direction"]==1 else "short",original_entry_time=iso(e["entry_time"]),order_submitted_at=row["submitted_at"],order_active_at=row["submitted_at"],signal_available_at=row["signal_available_at"],arming_at=row["arming_at"],slippage_ticks=slippage_ticks,commission_per_side=commission,ordering=ordering,execution_minutes=execution_minutes,fill_model=fill_model)
        position.update({k+"_at_signal":v for k,v in baseline_state(e,row["signal_available_at"]).items()})
        position.update(source_cohort(t))
        state=baseline_state(e,t)
        position["entry_after_baseline_exit"]=state["baseline_position_status"]=="flat" if state["baseline_position_status"]!="unknown" else None
        position["entry_improvement_points"]=d*(float(e["entry_price_raw"])-raw) if d==e["direction"] else None
        row.update(fill=True,fill_time=iso(t),fill_time_precision=precision,opportunity=True)

    def finish(raw,t,reason,precision="observed_open",competing=False):
        mark(raw)
        actual=raw-d*slip
        gross=d*(actual-position["entry_price"])
        raw_points=d*(raw-position["entry_price_raw"])
        net=gross*100*quantity-2*commission*quantity
        risk=position["risk_initial_dollars"]
        active=abs(position["entry_price"]-position["stop"])*100*quantity
        latest=t+timedelta(minutes=execution_minutes) if precision=="within_bar" else t
        start=dt(position["entry_time"])
        position.update(status="completed",exit_time=iso(t),exit_time_latest=iso(latest),exit_time_precision=precision,exit_price_raw=raw,exit_price=actual,exit_reason=reason,last_observed_at=iso(t),gross_points=gross,gross_dollars=gross*100*quantity,raw_price_points=raw_points,raw_price_dollars=raw_points*100*quantity,commission_dollars=2*commission*quantity,net_points=net/(100*quantity),net_dollars=net,gross_r=gross*100*quantity/risk if risk else None,net_r=net/risk if risk else None,source_style_r=net/active if active else None,source_risk_dollars=active if active else None,mfe_points=mfe,mae_points=mae,excursions_complete=True,competing_exit_orders=competing,holding_minutes=(t-start).total_seconds()/60,holding_bars=int((floor15(t)-floor15(start)).total_seconds()/900),holding_minutes_lower=max(0,(t-dt(position["entry_time_latest"])).total_seconds()/60),holding_minutes_upper=max(0,(latest-start).total_seconds()/60))
        row.update(status="filled_complete",reason=None,unknown=False,net_dollars=net,trade=position)
        return row

    for bar in sequence:
        t=bar["timestamp"]
        if t<due:
            continue
        if t>e["cutoff"]+FIFTEEN:
            break
        if position is None and t>=e["cutoff"]:
            break
        gap=ctx.uncertain(previous_end,t+ONE)
        if gap and not source_gap:
            return unknown(*gap)
        if ctx.roll is not None and t>=ctx.roll:
            return unknown(ctx.roll,"contract_transition")
        if bar["contract"]!=e["contract"]:
            continue
        if position is None and row["order_type"]=="market":
            opening=ctx.m.get(due)
            if opening is None and not source_gap:
                return unknown(due,"scheduled_open_price_missing")
            if t>due and not source_gap:
                return unknown(due,"scheduled_execution_open_missing")
            fill(float(opening["open"]) if opening is not None and t==due else float(bar["open"]),t,"observed_open")
        if position is not None:
            through=d*cmp(bar["open"],position["stop"])<=0
            competing=market_queued and (through or reset_queued)
            if market_queued:
                return finish(float(bar["open"]),t,"stop" if competing and timed_exit_priority=="stop_first" else "time",competing=competing)
            if through or reset_queued:
                return finish(float(bar["open"]),t,"stop")
        opening_relation=d*cmp(bar["open"],row["submitted_limit"]) if row["submitted_limit"] is not None else 1
        if position is None and row["order_type"]=="limit" and (opening_relation<0 or opening_relation==0 and row["trade_through_ticks"]==0):
            fill(float(bar["open"]),t,"observed_open")
            if d*cmp(bar["open"],position["stop"])<=0:
                return finish(float(bar["open"]),t,"stop")
        if execution_minutes==15 and not ctx.complete(bar):
            gap=ctx.uncertain(t,t+FIFTEEN)
            return unknown(gap[0] if gap else t,"source_15m_candle_unusable")
        for a,b in zip(route(bar,ordering),route(bar,ordering)[1:]):
            if position is None:
                trigger=float(decimal(row["submitted_limit"])-Decimal(d)*decimal(row["trade_through_ticks"])*TICK)
                if d*cmp(a,trigger)>0 and d*cmp(b,trigger)<=0:
                    ambiguous=cmp(bar["low"],row["initial_stop"])<=0 if d==1 else cmp(bar["high"],row["initial_stop"])>=0
                    fill(float(row["submitted_limit"]),t,"within_bar",ambiguous)
                    a=trigger
            if position is not None:
                mark(a)
                through_a=d*cmp(a,position["stop"])<=0
                through_b=d*cmp(b,position["stop"])<=0
                if through_a or through_b:
                    favorable=float(bar["high" if d==1 else "low"])
                    position["excursion_ambiguous"]|=d*(favorable-position["entry_price"])>mfe+1e-8
                    return finish(a if through_a else position["stop"],t,"stop","within_bar")
                mark(b)
        end=t+timedelta(minutes=execution_minutes)
        previous_end=end
        if position is not None and end==floor15(t)+FIFTEEN:
            decision=ctx.bars.get(floor15(t))
            if (decision is None or not ctx.complete(decision)) and not source_gap:
                return unknown(end,"incomplete_decision_candle")
            if position["reset_stop_active_at"] is None and floor15(dt(position["entry_time"]))==floor15(t):
                if stop_mode=="percent":
                    reset=stop_price(position["entry_price"],d)
                    position.update(stop=reset,reset_stop=reset,reset_stop_active_at=iso(end),risk_effective_points=d*(position["entry_price"]-reset) if d*(position["entry_price"]-reset)>0 else None,risk_effective_dollars=d*(position["entry_price"]-reset)*100*quantity if d*(position["entry_price"]-reset)>0 else None,source_risk_dollars=abs(position["entry_price"]-reset)*100*quantity)
                    reset_queued=d*cmp(bar["close"],reset)<=0
            if end>=e["cutoff"]:
                market_queued=True
    if position is not None:
        gap=ctx.uncertain(previous_end,e["cutoff"]+ONE)
        return unknown(gap[0] if gap else previous_end,gap[1] if gap else "retained_endpoint_open")
    gap=ctx.uncertain(due,e["cutoff"])
    if gap:
        return unknown(*gap)
    row.update(status="known_no_fill",reason="resting_order_expired_unfilled",net_dollars=0.)
    return row


def oracle_policy(ctx,policy,**settings):
    signal=oracle_signal(ctx,policy,stop_mode=settings.get("stop_mode","percent"))
    return oracle_execute(ctx,signal,**settings)


def whole_quantity(equity,reference,stop,*,budget_fraction=1.,active_notional=0.,active_margin=0.):
    """Independent risk, gross-notional, margin and whole-contract caps."""
    risk=abs(reference-stop)*100
    if equity<=0 or reference<=0 or risk<=0:
        return 0
    risk_cap=equity*.01*budget_fraction/risk
    leverage_cap=max(0,equity*10-active_notional)/(reference*100)
    margin_cap=max(0,equity-active_margin)/(reference*100*.05)
    return max(0,math.floor(min(risk_cap,leverage_cap,margin_cap)+1e-9))


def recovery_class(original_net,later_net,*,loss_known,actually_executed):
    if not loss_known or not actually_executed or original_net is None or later_net is None or original_net>=-1e-8:
        return None
    combined=original_net+later_net
    label="full_recovery" if combined>=-1e-8 else "partial_recovery" if later_net>1e-8 else "further_loss" if later_net< -1e-8 else "no_improvement"
    return {"category":label,"combined_net_dollars":combined,"recovery_dollars":later_net}


def aligned_intervals(values,calendar,*,weeks=4,confidence=.95,replications=10000,seed=230015):
    """Separate calendar-block reconstruction using one joint seeded draw array.

    Empty blocks preserve calendar spacing. The common mask must be supplied
    before this calculation. Unlike producer chunking, all draws are generated
    once; NumPy's identical seed/shape stream makes receipts exactly comparable.
    """
    if not values or not calendar:
        return []
    dates=[datetime.fromisoformat(str(x)) for x in calendar]
    beginning=min(dates)
    beginning-=timedelta(days=beginning.weekday())
    n=(max(dates)-beginning).days//(7*weeks)+1
    width=len(values[0][1])
    numerator=np.zeros((n,width));denominator=np.zeros((n,width))
    for date,vector in values:
        slot=(datetime.fromisoformat(str(date))-beginning).days//(7*weeks)
        for column,value in enumerate(vector):
            if value is not None:
                numerator[slot,column]+=value
                denominator[slot,column]+=1
    if not np.any(denominator):
        return [(None,None)]*width
    draw=np.random.default_rng(seed).integers(0,n,size=(replications,n))
    sums=numerator[draw].sum(axis=1)
    counts=denominator[draw].sum(axis=1)
    alpha=(1-confidence)/2
    result=[]
    for column in range(width):
        sample=sums[:,column][counts[:,column]>0]/counts[:,column][counts[:,column]>0]
        result.append(tuple(float(x) for x in np.quantile(sample,[alpha,1-alpha])) if len(sample) else (None,None))
    return result


def selection_from_validation(rows):
    """Frozen selection uses support and common-mask paired improvement only."""
    eligible=[x for x in rows if x["mean_difference"] is not None and x["mean_difference"]>0 and x["completed_fills"]>=100 and x["completed_years"]>=2]
    return min(eligible,key=lambda x:(-x["mean_difference"],x["fraction"]))["policy"] if eligible else None


def observed_points(ctx,end,ordering):
    """Independent post-fill price-node stream, suppressing flat segments."""
    for bar,path in ctx.postfill(end,ordering):
        previous=None
        for position,price in enumerate(path):
            if previous is None or cmp(price,previous)!=0:
                yield bar,position,price
            previous=price


def price_detail(ctx,bar,node,price):
    t=bar["timestamp"]
    opening=node==0 and t!=ctx.episode["entry_time"]
    return {"time":iso(t),"time_latest":iso(t if opening else t+ONE),"available_at":iso(bar.get("available_at") or t+ONE),"precision":"observed_open" if opening else "within_1m","price":price,"bar_open":iso(floor15(t)),"exact_first":ctx.uncertain(ctx.episode["entry_time"],t+ONE) is None and not bool(ctx.episode.get("ambiguous",False))}


def confirmed_bars(ctx,end,include):
    for bar in ctx.candles:
        t=bar["timestamp"]
        close=t+FIFTEEN
        if t>=ctx.episode["b"] and close>ctx.episode["entry_time"] and t<end and (close<end or include and close==end) and ctx.complete(bar):
            yield bar


def confirmation_detail(ctx,bar):
    t=bar["timestamp"]+FIFTEEN
    return {"time":iso(t),"time_latest":iso(t),"available_at":iso(t),"precision":"confirmed_15m_close","price":float(bar["close"]),"bar_open":iso(bar["timestamp"]),"exact_first":ctx.uncertain(ctx.episode["entry_time"],t) is None and not bool(ctx.episode.get("ambiguous",False))}


def merge_observation(ctx,event,branches,source):
    """An observed event is independent of exact first-time identification."""
    flags=[x["state"] for x in branches]
    occurred=flags[0] if flags[0]==flags[1] else None
    details=[x["detail"] for x in branches]
    exact=occurred is True and all(x is not None and x["exact_first"] for x in details) and all(details[0][k]==details[1][k] for k in ("time","time_latest","available_at"))
    estimate=source["detail"]
    observed=estimate or next((x for x in details if x is not None),None)
    first=details[0] if exact else None
    e=ctx.episode
    entry_latest=dt(e.get("entry_time_latest")) or e["entry_time"]
    actual_cohort=source_cohort(first["time"]) if first else {}
    seen_cohort=source_cohort(observed["time"]) if observed else {}
    row={"event":event,"occurred":occurred,"ordering_ambiguous":flags[0]!=flags[1],"first_time":first["time"] if first else None,"first_time_latest":first["time_latest"] if first else None,"first_available_at":first["available_at"] if first else None,"first_time_exact_observation":bool(exact),"first_observed_time":observed["time"] if observed else None,"first_observed_available_at":observed["available_at"] if observed else None,"time_precision":observed["precision"] if observed else None,"source_ohlc_estimated_first_time":estimate["time"] if estimate else None,"elapsed_minutes_lower":max(0,(dt(first["time"])-entry_latest).total_seconds()/60) if first else None,"elapsed_minutes_upper":max(0,(dt(first["time_latest"])-e["entry_time"]).total_seconds()/60) if first else None,"event_year":actual_cohort.get("entry_year"),"event_session":actual_cohort.get("entry_session"),"observed_event_year":seen_cohort.get("entry_year"),"observed_event_session":seen_cohort.get("entry_session")}
    if first:
        row.update({k+"_at_event":v for k,v in baseline_state(e,first["time"]).items()})
    else:
        row.update(baseline_position_status_at_event=None,baseline_loss_known_at_event=None)
    return row


def protected_branch(ctx,end,include,ordering):
    e=ctx.episode
    d=e["direction"]
    opposite=float(e["range_low"] if d==1 else e["range_high"])
    reference={"opposite_boundary":opposite,"midpoint":(float(e["range_high"])+float(e["range_low"]))/2,"original_boundary":float(e["range_high"] if d==1 else e["range_low"])}
    thresholds={"touch":opposite,"one_tick_breach":float(decimal(opposite)-Decimal(d)*TICK)}
    first={name:None for name in ("touch","one_tick_breach","close_break","reclaim")}
    contacts={name:0 for name in thresholds}
    active={name:False for name in thresholds}
    recovery={(level,kind):None for level in reference for kind in ("touch","close_reclaim")}
    for bar,node,price in observed_points(ctx,end,ordering):
        for name,threshold in thresholds.items():
            beyond=d*cmp(price,threshold)<=0
            if beyond and not active[name]:
                contacts[name]+=1
                if first[name] is None:first[name]=price_detail(ctx,bar,node,threshold if node else price)
            active[name]=beyond
        if first["one_tick_breach"]:
            for level,threshold in reference.items():
                if recovery[(level,"touch")] is None and d*cmp(price,threshold)>=0:
                    recovery[(level,"touch")]=price_detail(ctx,bar,node,threshold if node else price)
    breached_in=dt(first["one_tick_breach"]["bar_open"]) if first["one_tick_breach"] else None
    for bar in confirmed_bars(ctx,end,include):
        outward=d*cmp(bar["close"],opposite)
        if outward<0 and first["close_break"] is None:
            first["close_break"]=confirmation_detail(ctx,bar)
        if breached_in is not None and bar["timestamp"]>breached_in:
            if outward>0 and first["reclaim"] is None:first["reclaim"]=confirmation_detail(ctx,bar)
            for level,threshold in reference.items():
                if d*cmp(bar["close"],threshold)>0 and recovery[(level,"close_reclaim")] is None:
                    recovery[(level,"close_reclaim")]=confirmation_detail(ctx,bar)
    complete=ctx.uncertain(e["entry_time"],end) is None
    events={name:{"detail":value,"state":True if value else False if complete else None} for name,value in first.items()}
    recoveries={key:{"detail":value,"state":True if value else False if complete and events["one_tick_breach"]["state"] else None} for key,value in recovery.items()}
    return events,recoveries,contacts,complete


def oracle_protected(ctx,*,ordering="source_ohlc"):
    e=ctx.episode
    d=e["direction"]
    original=source_cohort(e["entry_time"])
    same_end,include=horizon_end(e["entry_time"],e["cutoff"])
    occurrences=[];recoveries=[];event_rows=[]
    for horizon,end,included in (("original_session",same_end,include),("remaining_broker_window",e["cutoff"],True)):
        branches=[protected_branch(ctx,end,included,o) for o in ("high_first","low_first",ordering)]
        expected=[t for t in ctx.expected if e["entry_time"]<=t<end]
        observed=[t for t in expected if t in ctx.m and ctx.m[t]["contract"]==e["contract"] and (ctx.roll is None or t<ctx.roll)]
        base={"episode_id":e.get("trade_id",e.get("episode_id")),"broker_day":e["broker_day"],"contract":e["contract"],"original_direction":d,"original_side":"long" if d==1 else "short","protected_side":"low" if d==1 else "high","original_entry_time":iso(e["entry_time"]),"original_year":original["entry_year"],"original_session":original["entry_session"],"horizon":horizon,"horizon_end":iso(end),"close_confirmation_endpoint_included":included,"complete_observation":branches[0][3] and branches[1][3],"scheduled_exposure_minutes":len(expected),"observed_exposure_minutes":len(observed),"wall_exposure_minutes":max(0,(end-e["entry_time"]).total_seconds()/60)}
        for name in ("touch","one_tick_breach","close_break","reclaim"):
            row={**base,**merge_observation(ctx,name,[x[0][name] for x in branches[:2]],branches[2][0][name])}
            if name in ("touch","one_tick_breach"):
                counts=[x[2][name] for x in branches[:2]]
                known_count=counts[0] if counts[0]==counts[1] and base["complete_observation"] else None
                row.update(contact_count=known_count,repeat_contacts=max(known_count-1,0) if known_count is not None else None,observed_contacts_lower=min(counts),observed_contacts_upper=max(counts),total_contacts_upper=max(counts) if base["complete_observation"] else None,observed_repeat_contacts_lower=max(min(counts)-1,0),observed_repeat_contacts_upper=max(max(counts)-1,0),total_repeat_contacts_upper=max(max(counts)-1,0) if base["complete_observation"] else None)
            occurrences.append(row)
            if row["first_observed_time"]:event_rows.append({**row,"event_family":"protected_boundary"})
        breach_flags=[x[0]["one_tick_breach"]["state"] for x in branches[:2]]
        breach=breach_flags[0] if breach_flags[0]==breach_flags[1] else None
        for level,price in (("opposite_boundary",float(e["range_low"] if d==1 else e["range_high"])),("midpoint",(float(e["range_high"])+float(e["range_low"]))/2),("original_boundary",float(e["range_high"] if d==1 else e["range_low"]))):
            for kind in ("touch","close_reclaim"):
                key=(level,kind)
                recoveries.append({**base,"recovery_level":level,"reference_price":price,"breach_occurred":breach,"not_executed_trade_target":True,**merge_observation(ctx,kind,[x[1][key] for x in branches[:2]],branches[2][1][key])})
    return {"occurrence":occurrences,"recovery":recoveries,"events":event_rows}


def level_branch(ctx,q,ordering):
    e=ctx.episode;d=e["direction"];end=e["cutoff"]
    h,l=decimal(e["range_high"]),decimal(e["range_low"])
    original=float(h if d==1 else l);opposite=float(l if d==1 else h)
    level=float(h-decimal(q)*(h-l) if d==1 else l+decimal(q)*(h-l))
    risk=d*(level-stop_price(level,d))
    first={name:None for name in ("touch","inward_close","outward_reclaim")}
    active=False;contacts=0;recovery=None;excursion=None
    mfe=mae=deepest=0.;touch_time=None
    for bar,node,price in observed_points(ctx,end,ordering):
        deepest=max(deepest,d*(original-price)/float(h-l))
        initial=bar["timestamp"]==e["entry_time"] and node==0
        now=d*cmp(price,level)<=0
        if now and not active and not (q==0 and initial):
            contacts+=1
            if first["touch"] is None:
                first["touch"]=price_detail(ctx,bar,node,level if node else price)
                touch_time=bar["timestamp"]
        active=now if not (q==0 and initial) else False
        if first["touch"] is not None:
            move=d*(price-level)
            mfe=max(mfe,move);mae=max(mae,-move)
            complete_since=ctx.uncertain(touch_time,bar["timestamp"]+ONE) is None
            if recovery is None:
                if d*cmp(price,opposite)<=0:recovery=False if complete_since else None
                elif d*cmp(price,original)>=0:recovery=True if complete_since else None
            if excursion is None and risk>0:
                if cmp(move,risk)>=0:excursion="favorable" if complete_since else "unknown"
                elif cmp(move,-risk)<=0:excursion="adverse" if complete_since else "unknown"
    arm=None
    for bar in confirmed_bars(ctx,end,True):
        inward=d*cmp(bar["close"],level)
        if first["inward_close"] is None and inward<=0:
            first["inward_close"]=confirmation_detail(ctx,bar)
            arm=bar["timestamp"]
        elif arm is not None and bar["timestamp"]>arm and inward>0 and first["outward_reclaim"] is None:
            first["outward_reclaim"]=confirmation_detail(ctx,bar)
    complete=ctx.uncertain(e["entry_time"],end) is None
    if first["touch"] is not None and complete:
        if recovery is None:recovery=False
        if excursion is None:excursion="neither"
    events={name:{"detail":value,"state":True if value else False if complete else None} for name,value in first.items()}
    return {"events":events,"contacts":contacts,"complete":complete,"range_recovery":recovery,"excursion_first":excursion,"event_risk_points":risk if risk>0 else None,"mfe_after_touch_points":mfe if first["touch"] else None,"mae_after_touch_points":mae if first["touch"] else None,"deepest_range_fraction":deepest}


def oracle_levels(ctx,*,ordering="source_ohlc"):
    e=ctx.episode;d=e["direction"]
    original=source_cohort(e["entry_time"])
    rows=[]
    for q in (0,.25,.5,.75):
        branches=[level_branch(ctx,q,o) for o in ("high_first","low_first",ordering)]
        recovery=branches[0]["range_recovery"] if branches[0]["range_recovery"]==branches[1]["range_recovery"] else None
        excursion=branches[0]["excursion_first"] if branches[0]["excursion_first"]==branches[1]["excursion_first"] else "unknown"
        level=float(decimal(e["range_high"])-decimal(q)*(decimal(e["range_high"])-decimal(e["range_low"]))) if d==1 else float(decimal(e["range_low"])+decimal(q)*(decimal(e["range_high"])-decimal(e["range_low"])))
        for event in ("touch","inward_close","outward_reclaim"):
            counts=[x["contacts"] for x in branches[:2]]
            known_count=counts[0] if counts[0]==counts[1] and branches[0]["complete"] else None
            rows.append({"episode_id":e.get("trade_id",e.get("episode_id")),"broker_day":e["broker_day"],"contract":e["contract"],"original_direction":d,"original_year":original["entry_year"],"original_session":original["entry_session"],"fraction":q,"raw_level":level,"horizon_end":iso(e["cutoff"]),"complete_observation":branches[0]["complete"] and branches[1]["complete"],**merge_observation(ctx,event,[x["events"][event] for x in branches[:2]],branches[2]["events"][event]),"contact_count":known_count,"repeat_contacts":max(known_count-1,0) if known_count is not None else None,"observed_contacts_lower":min(counts),"observed_contacts_upper":max(counts),"observed_repeat_contacts_lower":max(min(counts)-1,0),"observed_repeat_contacts_upper":max(max(counts)-1,0),"range_recovery_before_opposite":recovery,"excursion_first_1R":excursion,"excursion_success":True if excursion=="favorable" else False if excursion in ("adverse","neither") else None,"event_risk_points":branches[2]["event_risk_points"],"mfe_after_touch_points":branches[2]["mfe_after_touch_points"],"mae_after_touch_points":branches[2]["mae_after_touch_points"],"deepest_range_fraction":branches[2]["deepest_range_fraction"],"not_realized_trade_return":True})
    return rows


def normalized_trade(trade):
    item=dict(trade)
    item.update(cohort_at(item["entry_time"]))
    start=dt(item["broker_day"]+"T04:00:00Z")
    item["minutes_since_trading_start"]=(dt(item["entry_time"])-start).total_seconds()/60
    return item


def closed_equity(trades):
    accumulated=peak=0.
    rows=[]
    for trade in sorted((x for x in trades if x["status"]=="completed"),key=lambda x:(x["exit_time"],x["trade_id"])):
        accumulated+=trade["net_dollars"]
        peak=max(peak,accumulated)
        rows.append(dict(trade_id=trade["trade_id"],exit_time=trade["exit_time"],entry_year=cohort_at(trade["entry_time"])["year"],cumulative_net_dollars=accumulated,drawdown_dollars=accumulated-peak))
    return rows


def conditional_trade_interval(trades,calendar,field):
    """Inherited Phase1 conditional 28-day calendar-block interval, separate
    from the Monday-aligned Phase2 paired-family interval."""
    usable=[x for x in trades if x["status"]=="completed" and x.get(field) is not None]
    if not calendar or not usable:return None,None
    first=min(datetime.fromisoformat(d) for d in calendar)
    last=max(datetime.fromisoformat(d) for d in calendar)
    n=(last-first).days//28+1
    sums=np.zeros(n);counts=np.zeros(n)
    for trade in usable:
        slot=(datetime.fromisoformat(trade["broker_day"])-first).days//28
        sums[slot]+=trade[field];counts[slot]+=1
    draw=np.random.default_rng(230015).integers(0,n,size=(10000,n))
    numerators=sums[draw].sum(axis=1);denominators=counts[draw].sum(axis=1)
    samples=numerators[denominators>0]/denominators[denominators>0]
    return tuple(float(x) for x in np.quantile(samples,[.025,.975])) if len(samples) else (None,None)


def trade_statistics(trades,calendar,*,year="all",session="all",side="combined",intervals=False):
    normalized=[normalized_trade(x) for x in trades]
    selected=[x for x in normalized if (year=="all" or x["year"]==year) and (session=="all" or x["session"]==session) and (side=="combined" or x["side"]==side)]
    closed=[x for x in selected if x["status"]=="completed"]
    pnl=[x["net_dollars"] for x in closed]
    winners=[v for v in pnl if v>1e-8];losers=[v for v in pnl if v< -1e-8]
    rs=[x["net_r"] for x in closed if x.get("net_r") is not None]
    source_rs=[x["source_style_r"] for x in closed if x.get("source_style_r") is not None]
    if pnl:
        z=1.959963984540054;n=len(pnl);p=len(winners)/n
        factor=1+z*z/n;center=(p+z*z/(2*n))/factor
        radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/factor
        winlow,winhigh=center-radius,center+radius
    else:winlow=winhigh=None
    equity=closed_equity(closed)
    maximum=streak=0
    for x in sorted(closed,key=lambda x:(x["exit_time"],x["trade_id"])):
        streak=streak+1 if x["net_dollars"]< -1e-8 else 0
        maximum=max(maximum,streak)
    days=[x for x in calendar if year=="all" or cohort_at(x+"T04:00:00Z")["year"]==year]
    calendar_support=session=="all" and side=="combined"
    result=dict(year=year,session=session,side=side,accepted_breakouts=len(selected),executable_fills=len(selected),completed=len(closed),censored=len(selected)-len(closed),ambiguous=sum(bool(x.get("ambiguous")) for x in selected),wins=len(winners),losses=len(losers),breakevens=sum(abs(v)<=1e-8 for v in pnl),win_rate=len(winners)/len(pnl) if pnl else None,win_rate_low=winlow,win_rate_high=winhigh,gross_points=sum(x["raw_price_points"] for x in closed) if closed else None,gross_dollars=sum(x["raw_price_dollars"] for x in closed) if closed else None,net_points=sum(x["net_points"] for x in closed) if closed else None,net_dollars=sum(pnl) if pnl else None,cost_dollars=sum(x["raw_price_dollars"]-x["net_dollars"] for x in closed) if closed else None,net_r=sum(rs) if rs else None,r_denominator=len(rs),invalid_r=len(closed)-len(rs),expectancy_r=mean(rs) if rs else None,source_style_net_r=sum(source_rs) if source_rs else None,source_style_r_denominator=len(source_rs),mean_net_dollars=mean(pnl) if pnl else None,median_net_dollars=median(pnl) if pnl else None,average_win_dollars=mean(winners) if winners else None,average_loss_dollars=mean(losers) if losers else None,win_sum_dollars=sum(winners),loss_sum_dollars=sum(losers),profit_factor=sum(winners)/-sum(losers) if losers else None,payoff_ratio=mean(winners)/-mean(losers) if winners and losers else None,mfe_points=mean(x["mfe_points"] for x in closed) if closed else None,mae_points=mean(x["mae_points"] for x in closed) if closed else None,holding_minutes=mean(x["holding_minutes"] for x in closed) if closed else None,median_holding_minutes=median(x["holding_minutes"] for x in closed) if closed else None,stop_exits=sum(x["exit_reason"] in ("stop","reset_stop") for x in closed),timed_exits=sum(x["exit_reason"] in ("time","timed") for x in closed),max_drawdown_dollars=-min([0.,*(x["drawdown_dollars"] for x in equity)]) if closed else None,max_losing_streak=maximum if closed else None,entry_share=len(selected)/len(trades) if trades else None,distinct_broker_days=len({x["broker_day"] for x in selected}),mean_minutes_since_start=mean(x["minutes_since_trading_start"] for x in selected) if selected else None,eligible_days=None,valid_ranges=None,no_trade_days=None,unknown_days=None,exclusions=None,quantity_skips=None,day_coverage_start=min(days) if days and calendar_support else None,day_coverage_end=max(days) if days and calendar_support else None,entry_coverage_start=min((x["entry_ny"] for x in selected),default=None),entry_coverage_end=max((x["entry_ny"] for x in selected),default=None),partial_year=year=="2026" if year!="all" else None)
    if intervals:
        result["mean_dollars_low"],result["mean_dollars_high"]=conditional_trade_interval(selected,days,"net_dollars")
        result["expectancy_r_low"],result["expectancy_r_high"]=conditional_trade_interval(selected,days,"net_r")
    return result


def policy_pnl(row):
    if row["status"]=="completed":return row["trade"]["net_dollars"]
    if row["status"] in ("no_fill","missed_before_arming","invalid_planned_risk"):return 0.
    return None


def normalized_policy(row):
    result=dict(row)
    result["execution_status"]=row["status"]
    result["signal_at"]=result.get("signal_available_at")
    result["opportunity_seen"]=True if row["opportunity"] else None if row["unknown"] else False
    result["ambiguous"]=bool(row.get("trade",{}).get("ambiguous",False)) if row.get("trade") else False
    if row["status"]=="filled_complete":result["status"]="completed"
    elif row["status"]=="filled_censored":result["status"]="censored"
    elif row["status"].startswith("unknown"):result["status"]="unknown"
    elif row["reason"]=="missed_before_arming":result["status"]="missed_before_arming"
    else:result["status"]="no_fill"
    return result


def original_cohort(trade):
    c=cohort_at(trade["entry_time"])
    return dict(year=c["year"],session=c["session"],side="upper-first" if trade["direction"]==1 else "lower-first")


def paired_statistics(results,baseline,calendar,policies,family,*,year="all",session="all",side="combined",intervals=True):
    origins={key:original_cohort(x) for key,x in baseline.items()}
    ids=[key for key,c in origins.items() if (year=="all" or c["year"]==year) and (session=="all" or c["session"]==session) and (side=="combined" or c["side"]==side)]
    maps={p:{x["episode_id"]:x for x in results[p]} for p in policies}
    common={key:baseline[key]["status"]=="completed" and all(policy_pnl(maps[p][key]) is not None for p in policies) for key in ids}
    paired=[key for key in ids if common[key]]
    vectors=[(baseline[key]["broker_day"],[policy_pnl(maps[p][key])-baseline[key]["net_dollars"] if common[key] else None for p in policies]) for key in ids]
    days=[d for d in calendar if year=="all" or f"{year}-01-01"<=d<=f"{int(year)+1}-01-01"]
    point=aligned_intervals(vectors,days) if intervals else [(None,None)]*len(policies)
    confidence=.9875 if family=="primary" else .9833333333333333
    simultaneous=family=="primary" or family=="protected" and side=="upper-first"
    corrected=aligned_intervals(vectors,days,confidence=confidence) if intervals and simultaneous else [(None,None)]*len(policies)
    rows=[]
    for index,p in enumerate(policies):
        chosen=[maps[p][key] for key in ids]
        fills=[x for x in chosen if x.get("trade")]
        no_fill=[key for key in ids if policy_pnl(maps[p][key])==0 and not maps[p][key].get("trade")]
        individual=[key for key in ids if baseline[key]["status"]=="completed" and policy_pnl(maps[p][key]) is not None]
        differences=[policy_pnl(maps[p][key])-baseline[key]["net_dollars"] for key in paired]
        delays=[(dt(x["trade"]["entry_time"])-dt(baseline[x["episode_id"]]["entry_time"])).total_seconds()/60 for x in fills]
        improvements=[baseline[x["episode_id"]]["direction"]*(baseline[x["episode_id"]]["entry_price"]-x["trade"]["entry_price"]) for x in fills if x["trade"]["direction"]==baseline[x["episode_id"]]["direction"]]
        rows.append(dict(policy=p,family=family,year=year,session=session,side=side,anchor="original_breakout_fill",episodes=len(ids),complete_pairs=len(paired),missing_pairs=len(ids)-len(paired),missing_rate=(len(ids)-len(paired))/len(ids) if ids else None,opportunities=sum(x.get("opportunity_seen") is True for x in chosen),opportunity_unknown=sum(x.get("opportunity_seen") is None for x in chosen),armed=sum(bool(x.get("arming_at")) for x in chosen),signals=sum(bool(x.get("signal_at")) for x in chosen),fills=len(fills),completed=sum(x["status"]=="completed" for x in chosen),censored=sum(x["status"]=="censored" for x in chosen),unknown=sum(x["status"]=="unknown" for x in chosen),no_fill=len(no_fill),ambiguous=sum(bool(x.get("ambiguous")) for x in chosen),participation_rate=len(fills)/len(ids) if ids else None,signal_rate=sum(bool(x.get("signal_at")) for x in chosen)/len(ids) if ids else None,baseline_net_dollars=sum(baseline[key]["net_dollars"] for key in paired) if paired else None,alternative_net_dollars=sum(policy_pnl(maps[p][key]) for key in paired) if paired else None,mean_difference=mean(differences) if differences else None,difference_low=point[index][0] if point else None,difference_high=point[index][1] if point else None,adjusted_low=corrected[index][0] if corrected else None,adjusted_high=corrected[index][1] if corrected else None,adjusted_confidence=confidence if simultaneous else None,individual_pairs=len(individual),individual_mean_difference=mean([policy_pnl(maps[p][key])-baseline[key]["net_dollars"] for key in individual]) if individual else None,improved=sum(x>1e-8 for x in differences),deteriorated=sum(x< -1e-8 for x in differences),equal=sum(abs(x)<=1e-8 for x in differences),missed_winners=sum(baseline[key]["status"]=="completed" and baseline[key]["net_dollars"]>1e-8 for key in no_fill),avoided_losses=sum(baseline[key]["status"]=="completed" and baseline[key]["net_dollars"]< -1e-8 for key in no_fill),mean_entry_delay=mean(delays) if delays else None,mean_price_improvement=mean(improvements) if improvements else None))
    return rows


def frequency_statistics(rows,*,year="all",session="all",side="combined"):
    yes=[x for x in rows if x["occurred"] is True]
    no=[x for x in rows if x["occurred"] is False]
    unknown=[x for x in rows if x["occurred"] is None]
    elapsed=[x["elapsed_minutes"] for x in yes if x.get("elapsed_minutes") is not None]
    exposure=[x["scheduled_exposure_minutes"] for x in rows if x.get("scheduled_exposure_minutes") is not None]
    observed=[x["observed_exposure_minutes"] for x in rows if x.get("observed_exposure_minutes") is not None]
    lower=[x["elapsed_minutes_lower"] for x in yes if x.get("elapsed_minutes_lower") is not None]
    upper=[x["elapsed_minutes_upper"] for x in yes if x.get("elapsed_minutes_upper") is not None]
    repeat=[x["repeat_contacts"] for x in rows if x.get("repeat_contacts") is not None]
    return dict(year=year,session=session,side=side,episodes=len(rows),known_events=len(yes),known_none=len(no),unknown=len(unknown),known_denominator=len(yes)+len(no),rate=len(yes)/(len(yes)+len(no)) if yes or no else None,lower_bound=len(yes)/len(rows) if rows else None,upper_bound=(len(yes)+len(unknown))/len(rows) if rows else None,mean_elapsed_minutes=mean(elapsed) if elapsed else None,elapsed_denominator=len(elapsed),mean_elapsed_lower_minutes=mean(lower) if lower else None,mean_elapsed_upper_minutes=mean(upper) if upper else None,mean_exposure_minutes=mean(exposure) if exposure else None,mean_observed_exposure_minutes=mean(observed) if observed else None,repeat_contacts=sum(repeat) if repeat else None,repeat_known_episodes=len(repeat),anchor="original_breakout_fill")


PERIODS={"development":(2018,2019,2020),"validation":(2021,2022,2023),"later-assessment":(2024,2025),"replication":(2026,),"overall":tuple(range(2018,2027))}


def interval_statistics(results,baseline,calendar,policies,family,period,side,weeks):
    years=PERIODS[period]
    ids=[key for key,t in baseline.items() if int(original_cohort(t)["year"]) in years and (side=="combined" or original_cohort(t)["side"]==side)]
    maps={p:{x["episode_id"]:x for x in results[p]} for p in policies}
    vectors=[]
    for key in ids:
        valid=baseline[key]["status"]=="completed" and all(policy_pnl(maps[p][key]) is not None for p in policies)
        vectors.append((baseline[key]["broker_day"],[policy_pnl(maps[p][key])-baseline[key]["net_dollars"] if valid else None for p in policies]))
    days=[d for d in calendar if f"{min(years)}-01-01"<=d<=f"{max(years)+1}-01-01"]
    point=aligned_intervals(vectors,days,weeks=weeks) or [(None,None)]*len(policies)
    corrected=aligned_intervals(vectors,days,weeks=weeks,confidence=.9875 if family=="primary" else .9833333333333333) if family=="primary" or family=="protected" and side=="upper-first" else [(None,None)]*len(policies)
    output=[]
    for i,p in enumerate(policies):
        vals=[values[i] for _,values in vectors if values[i] is not None]
        output.append(dict(policy=p,family=family,period=period,side=side,block_weeks=weeks,episodes=len(ids),complete_pairs=len(vals),mean_difference=mean(vals) if vals else None,lower=point[i][0],upper=point[i][1],adjusted_lower=corrected[i][0] if corrected else None,adjusted_upper=corrected[i][1] if corrected else None))
    return output


def read_csv(path):
    with Path(path).open(newline="") as stream:
        reader=csv.DictReader(stream,strict=True)
        keys=reader.fieldnames or []
        if not keys or len(keys)!=len(set(keys)):raise ValueError("distinct CSV columns required")
        rows=list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):raise ValueError("CSV row width")
    return rows


def member(row,year,session,side):
    return (year=="all" or row["year"]==year) and (session=="all" or row["session"]==session) and (side=="combined" or row["side"]==side)


def enriched_observations(rows,baseline):
    enriched=[]
    for raw in rows:
        row=dict(raw)
        row["elapsed_minutes"]=(dt(row["first_time"])-dt(baseline[row["episode_id"]]["entry_time"])).total_seconds()/60 if row.get("first_time") else None
        if "recovery_level" in row:row["level"]=row["recovery_level"]
        enriched.append(row)
    return enriched


def verify_saved_tables(stage,baseline,roster,results,phase_records):
    """Recalculate every trade/paired/event/level summary cell independently."""
    metrics=json.loads((stage/"metrics.json").read_text())
    tables={}
    for name,record in metrics["tables"].items():
        path=stage/"tables"/(name+".csv")
        equal(sha256(path),record["sha256"],"saved table "+name)
        tables[name]=read_csv(path)
        equal(len(tables[name]),record["rows"],"saved table rows "+name)
    calendar=[row["broker_day"] for row in roster]
    trades={p:[row["trade"] for row in rows if row.get("trade")] for p,rows in results.items()}
    comparisons=0
    equal(len(tables["trade-cohorts"]),1500,"allactualentrycohorts")
    for row in tables["trade-cohorts"]:
        expected=trade_statistics(trades[row["policy"]],calendar,year=row["year"],session=row["session"],side=row["side"],intervals=True)
        expected.update(policy=row["policy"],anchor="candidate_actual_fill")
        comparisons+=compare_record(row,expected,"trade-cohorts")
    for row in tables["timing"]:
        alltrades=trades[row["policy"]]
        selected=[trade for trade in alltrades if str(cohort_at(trade["entry_time"])[row["dimension"]])==row["bucket"]]
        expected=trade_statistics(selected,calendar,side=row["side"])
        expected.update(policy=row["policy"],dimension=row["dimension"],bucket=row["bucket"],entry_share=expected["executable_fills"]/len(alltrades) if alltrades else None,anchor="candidate_actual_fill")
        comparisons+=compare_record(row,expected,"timing")
    expected_equity=[dict(row,policy=p) for p in results for row in closed_equity(trades[p])]
    equal(len(tables["equity"]),len(expected_equity),"closed equity row count")
    for row,expected in zip(tables["equity"],expected_equity):comparisons+=compare_record(row,expected,"equity")
    normalized={trade["trade_id"]:normalized_trade(trade) for ts in trades.values() for trade in ts}
    equal(len(tables["trades"]),len(normalized),"saved actual candidate trades")
    for row in tables["trades"]:comparisons+=compare_record(row,normalized[row["trade_id"]],"trades")
    families={"primary":PRIMARY,"passive":PASSIVE,"protected":PROTECTED}
    cache={}
    for row in tables["paired"]:
        key=(row["family"],row["year"],row["session"],row["side"])
        if key not in cache:
            cache[key]={x["policy"]:x for x in paired_statistics(results,baseline,calendar,families[row["family"]],row["family"],year=row["year"],session=row["session"],side=row["side"])}
        comparisons+=compare_record(row,cache[key][row["policy"]],"paired")
    cache={}
    for row in tables["interval-sensitivities"]:
        key=(row["family"],row["period"],row["side"],int(row["block_weeks"]))
        if key not in cache:cache[key]={x["policy"]:x for x in interval_statistics(results,baseline,calendar,families[row["family"]],row["family"],row["period"],row["side"],int(row["block_weeks"]))}
        comparisons+=compare_record(row,cache[key][row["policy"]],"interval-sensitivities")
    occurrence=enriched_observations([row for records in phase_records.values() for row in records["occurrence"]],baseline)
    recovery=enriched_observations([row for records in phase_records.values() for row in records["recovery"]],baseline)
    levels=enriched_observations([row for records in phase_records.values() for row in records["level-opportunities"]],baseline)
    for row in tables["occurrence"]:
        selected=[x for x in occurrence if member(x,row["year"],row["session"],row["side"]) and x["horizon"]==row["horizon"] and x["event"]==row["event"]]
        expected=frequency_statistics(selected,year=row["year"],session=row["session"],side=row["side"])
        expected.update(horizon=row["horizon"],event=row["event"])
        comparisons+=compare_record(row,expected,"occurrence")
    for row in tables["recovery"]:
        selected=[x for x in recovery if member(x,row["year"],row["session"],row["side"]) and x["horizon"]==row["horizon"] and x["level"]==row["level"] and x["event"]==row["event"]]
        at_risk=[x for x in selected if x["breach_occurred"] is True]
        expected=frequency_statistics(at_risk,year=row["year"],session=row["session"],side=row["side"])
        expected.update(horizon=row["horizon"],level=row["level"],event=row["event"],original_episodes=len(selected),known_breach_episodes=len(at_risk),known_no_breach_episodes=sum(x["breach_occurred"] is False for x in selected),unknown_breach_episodes=sum(x["breach_occurred"] is None for x in selected),population="known_protected_breach_episodes; unknown_breach_support_retained_separately")
        comparisons+=compare_record(row,expected,"recovery")
    for row in tables["level-opportunities"]:
        selected=[x for x in levels if member(x,row["year"],row["session"],row["side"]) and x["fraction"]==float(row["fraction"]) and x["event"]==row["event"]]
        expected=frequency_statistics(selected,year=row["year"],session=row["session"],side=row["side"])
        expected.update(horizon="remaining_broker_window",fraction=float(row["fraction"]),event=row["event"],population="all_original_accepted_episodes; conditional_path_diagnostics_after_known_event",not_realized_trade_return=True)
        seen=[x for x in selected if x["occurred"] is True]
        for field,prefix in (("range_recovery_before_opposite","range_recovery"),("excursion_success","first_1r_success")):
            yes=sum(x[field] is True for x in seen);no=sum(x[field] is False for x in seen)
            expected.update({prefix+"_successes":yes,prefix+"_known_denominator":yes+no,prefix+"_unknown":sum(x[field] is None for x in seen),prefix+"_rate":yes/(yes+no) if yes+no else None})
        for field in ("mfe_after_touch_points","mae_after_touch_points","deepest_range_fraction"):
            vals=[x[field] for x in seen if x.get(field) is not None]
            expected["mean_"+field]=sum(vals)/len(vals) if vals else None
            expected[field+"_denominator"]=len(vals)
        comparisons+=compare_record(row,expected,"level-opportunities")
    return {"status":"passed","comparisons":comparisons,"verified_tables":["trade-cohorts","timing","equity","trades","paired","interval-sensitivities","occurrence","recovery","level-opportunities"],"all_table_hashes":{name:dict(path="tables/"+name+".csv",bytes=(stage/"tables"/(name+".csv")).stat().st_size,sha256=sha256(stage/"tables"/(name+".csv")),rows=len(rows)) for name,rows in tables.items()}},tables


def read_gz(path):
    with gzip.open(path,"rt") as handle:
        return [json.loads(line) for line in handle]


def load_pinned_inputs(workspace,stage):
    """Load exact frozen inputs without invoking any producer adapter."""
    import pandas as pd
    import pyarrow.parquet as pq
    pin=json.loads((stage/"phase2-baseline-pin.json").read_text())
    if pin.get("status")!="passed":raise ValueError("baseline pin has not passed")
    locks=json.loads((stage/"inputs.lock.json").read_text())
    equal(sha256(stage/"phase2-baseline-pin.json"),locks["sha256"],"baseline pin frozen hash")
    ledgers={row["id"]:row for row in pin["scenario_ledgers"]}
    def original(name):
        record=ledgers[name];path=workspace/record["locator"]
        equal(sha256(path),record["sha256"],"Phase1 "+name)
        records=read_gz(path)
        equal(len(records),record["row_count"],"Phase1 "+name+" rows")
        return records
    original_trades=original("primary-one-tick-trades")
    ranges={row["broker_day"]:row for row in original("primary-one-tick-days")}
    baseline={row["trade_id"]:row for row in original_trades}
    equal(len(baseline),880,"accepted baseline episodes")
    equal(sum(x["status"]=="censored" for x in baseline.values()),17,"baseline censor retention")
    prepared={}
    for key,record in pin["prepared_execution_inputs"].items():
        path=workspace/record["locator"]
        equal(sha256(path),record["sha256"],key+" frozen bytes")
        if key!="audit-missing-minutes":prepared[key]=pq.read_table(path).to_pandas()
    minutes=prepared["audit-minutes"]
    minutes=minutes[minutes.scheduled & minutes.source_valid].copy()
    minutes["broker_date"]=minutes.timestamp.dt.tz_convert(BROKER).dt.date.astype(str)
    dates={row["broker_day"] for row in original_trades}
    minutes=minutes[minutes.broker_date.isin(dates)]
    minfields=["timestamp","open","high","low","close","contract","available_at"]
    byminute={day:df[minfields].to_dict("records") for day,df in minutes.groupby("broker_date")}
    decisions=prepared["audit-bars-15m"]
    bybar={}
    for day,df in decisions[decisions.broker_date.isin(dates)].groupby("broker_date"):
        values=[]
        for r in df.to_dict("records"):
            values.append(dict(timestamp=r["timestamp"],**{k:float(r[k]) if pd.notna(r[k]) else 0. for k in ("open","high","low","close")},contract=str(r["contract"]) if pd.notna(r["contract"]) else "unobserved",available_at=r["timestamp"]+FIFTEEN,complete=bool(r["usable"])))
        bybar[day]=values
    schedule=prepared["audit-expected-minutes"]
    schedule["broker_date"]=schedule.timestamp.dt.tz_convert(BROKER).dt.date.astype(str)
    byexpected={day:set(df.timestamp) for day,df in schedule[schedule.broker_date.isin(dates)].groupby("broker_date")}
    contexts={}
    for key,trade in baseline.items():
        episode=dict(trade)
        episode.update(range_high=ranges[trade["broker_day"]]["range_high"],range_low=ranges[trade["broker_day"]]["range_low"])
        day=trade["broker_day"]
        contexts[key]=OracleInput(episode,byminute[day],bybar[day],byexpected[day])
    roster_path=workspace/pin["complete_day_roster"]["path"]
    equal(sha256(roster_path),pin["complete_day_roster"]["sha256"],"complete calendar roster bytes")
    with roster_path.open() as handle:roster=list(csv.DictReader(handle))
    equal(len(roster),3183,"complete baseline calendar")
    equal(sum(x["eligible"].lower()=="true" for x in roster),994,"eligible baseline calendar")
    return contexts,baseline,roster,pin


def compare_record(actual,expected,path):
    count=0
    for key,value in expected.items():
        if key=="stop":continue # internal independent replay state
        if isinstance(value,dict):
            if not isinstance(actual.get(key),dict):raise ValueError(path+":"+key+" missing object")
            count+=compare_record(actual[key],value,path+":"+key)
        else:
            equal(actual.get(key),value,path+":"+key)
            count+=1
    return count


def verify_phase(workspace,stage,phase,contexts,baseline):
    folder=stage/"phases"/phase
    completion=json.loads((folder/"completion.json").read_text())
    years={"2018","2019","2020","2021","2022","2023"} if phase=="dev-validation" else {"2024","2025","2026"}
    original={key:trade for key,trade in baseline.items() if original_cohort(trade)["year"] in years}
    equal(completion["episodes"],len(original),phase+" canonical roster")
    records={}
    for record in completion["ledgers"]:
        path=workspace/record["path"]
        equal(sha256(path),record["sha256"],phase+" retained "+path.name)
        rows=read_gz(path)
        equal(len(rows),record["row_count"],phase+" row count "+path.name)
        records[path.name.split(".")[0]]=rows
    actual={(x["episode_id"],x["policy"]):x for x in records["policies"]}
    equal(len(actual),len(records["policies"]),phase+" duplicate policy episodes")
    equal(len(actual),len(original)*10,phase+" all prespecified policies retained")
    observation_indexes={name:{(x["episode_id"],x.get("horizon"),x.get("recovery_level"),x.get("fraction"),x["event"]):x for x in records[name]} for name in ("occurrence","recovery","boundary-events","level-opportunities")}
    for name,index in observation_indexes.items():equal(len(index),len(records[name]),phase+" duplicate "+name)
    comparisons=0
    event_count=0
    result={p:[] for p in (*PRIMARY,*PASSIVE,*PROTECTED)}
    for i,(key,trade) in enumerate(original.items()):
        ctx=contexts[key]
        for policy in result:
            expected=normalized_policy(oracle_policy(ctx,policy))
            comparisons+=compare_record(actual[(key,policy)],expected,f"{phase}:{key}:{policy}")
            result[policy].append(actual[(key,policy)])
        observed=oracle_protected(ctx)
        event_count+=len(observed["events"])
        for kind,name in (("occurrence","occurrence"),("recovery","recovery"),("events","boundary-events")):
            for row in observed[kind]:
                row.update(original_cohort(trade))
                index=(key,row.get("horizon"),row.get("recovery_level"),row.get("fraction"),row["event"])
                comparisons+=compare_record(observation_indexes[name][index],row,f"{phase}:{name}:{index}")
        for row in oracle_levels(ctx):
            row.update(original_cohort(trade))
            index=(key,None,None,row["fraction"],row["event"])
            comparisons+=compare_record(observation_indexes["level-opportunities"][index],row,f"{phase}:levels:{index}")
        if i%100==0:print(f"independent {phase}: {i}/{len(original)} episodes",flush=True)
    for name,multiple in (("occurrence",8),("recovery",12),("level-opportunities",12)):
        equal(len(records[name]),len(original)*multiple,phase+" "+name+" complete roster")
    equal(len(records["boundary-events"]),event_count,phase+" exact observed boundary event count")
    return {"phase":phase,"episodes":len(original),"policy_rows":len(actual),"comparisons":comparisons,"status":"passed"},result,records


def verify_selection(stage,results,baseline):
    saved=json.loads((stage/"selection.json").read_text())
    receipt=json.loads((stage/"selection-freeze.json").read_text())
    equal(sha256(stage/"selection.json"),receipt["selection_sha256"],"frozen selection bytes")
    equal(sha256(stage/"config.json"),receipt["settings_sha256"],"selection settings")
    equal(saved["later_alternative_outcomes_opened"],False,"selection before later alternatives")
    equal(receipt["later_outcomes_opened"],False,"selection freeze before later alternatives")
    original={key:trade for key,trade in baseline.items() if original_cohort(trade)["year"] in {"2021","2022","2023"}}
    maps={policy:{row["episode_id"]:row for row in results[policy]} for policy in PRIMARY}
    ids=list(original)
    common=[key for key in ids if original[key]["status"]=="completed" and all(policy_pnl(maps[p][key]) is not None for p in PRIMARY)]
    comparisons=0;candidates=[]
    equal(len(saved["candidates"]),4,"all four selection candidates")
    for i,p in enumerate(PRIMARY):
        fills=[maps[p][key] for key in ids if maps[p][key]["status"]=="completed"]
        years=sorted({original_cohort(original[row["episode_id"]])["year"] for row in fills})
        differences=[policy_pnl(maps[p][key])-original[key]["net_dollars"] for key in common]
        average=sum(differences)/len(differences) if differences else None
        expected=dict(policy=p,validation_episodes=len(ids),common_complete_pairs=len(common),completed_fills=len(fills),years_with_completed_fills=years,validation_mean_difference=average,qualifies=average is not None and average>0 and len(fills)>=100 and len(years)>=2)
        actual=saved["candidates"][i]
        for key,value in expected.items():
            if isinstance(value,list):
                if actual[key]!=value:raise ValueError("selection "+p+" "+key)
                comparisons+=1
            else:
                equal(actual[key],value,"selection "+p+" "+key);comparisons+=1
        candidates.append(dict(policy=p,fraction=int(p.split("q")[1])/100,mean_difference=average,completed_fills=len(fills),completed_years=len(years)))
    selected=selection_from_validation(candidates)
    equal(saved["selected_policy"],selected,"independent selected policy")
    equal(saved["decision"],"selected_for_later_assessment" if selected else "retain_baseline_no_qualifying_replacement","selection fallback")
    equal(saved["prior_baseline_exposure"],True,"published baseline exposure")
    frozen=json.loads((stage/"execution-freeze.json").read_text())
    ordered=[dt(frozen["at"]),dt(saved["frozen_at"]),dt(receipt["frozen_at"]),dt(json.loads((stage/"phases/dev-validation/completion.json").read_text())["finished_at"])]
    if ordered!=sorted(ordered):raise ValueError("selection chronology inconsistent")
    later=stage/"phases/later/completion.json"
    if later.exists():
        if dt(json.loads(later.read_text())["finished_at"])<ordered[-1]:raise ValueError("later completion precedes frozen selection")
    return {"status":"passed","selected_policy":selected,"validation_episodes":len(ids),"common_complete_pairs":len(common),"comparisons":comparisons+6,"chronology":"saved settings → development/validation → hashed selection → later completion","prior_baseline_exposure":True}


def verify_runtime_freeze(stage):
    record=json.loads((stage/"execution-freeze.json").read_text())
    checks=0
    for file,key in (("config.json","settings_sha256"),("protocol.md","protocol_sha256"),("inputs.lock.json","inputs_sha256"),("phase2-baseline-pin.json","baseline_pin_sha256"),("environment.lock","environment_lock_sha256")):
        equal(sha256(stage/file),record[key],"frozen "+file);checks+=1
    for file in record["source_files"]:
        equal(sha256(stage/file["path"]),file["sha256"],"retained executed code "+file["path"]);checks+=1
    config=json.loads((stage/"config.json").read_text())
    equal(config["baseline_manifest_sha256"],"d2f93832610ca6e6284838ce22ca9547b8c848a1b0f06a740a345df39d94c027","authoritative baseline")
    equal(config["phase3_state"],"unimplemented_uncomputed","Phase3 excluded")
    equal(config["uncertainty"]["replications"],10000,"10000 aligned draws")
    equal(config["uncertainty"]["seed"],230015,"frozen seed")
    return {"status":"passed","hash_checks":checks,"phase3_uncomputed_by_scope":True}


def main():
    import argparse
    import shutil
    import sys
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True)
    parser.add_argument("--phase",choices=("dev-validation","later","all"),required=True)
    parser.add_argument("--attempt",required=True,help="new immutable attempt name")
    args=parser.parse_args()
    workspace=Path(__file__).resolve().parents[2]
    stage=args.stage.resolve()
    if not stage.is_relative_to(workspace/"work/23_gc_overnight_breakout_15m"):
        raise ValueError("verification writes only the owning new work stage")
    if not args.attempt.replace("-","").replace("_","").isalnum():raise ValueError("plain attempt name required")
    target=stage/"verification"/("independent-"+args.attempt)
    target.mkdir(parents=True,exist_ok=False)
    snapshots=[]
    for source in (Path(__file__),Path(__file__).parent/"tests/test_phase2_independent.py"):
        destination=target/source.name
        shutil.copyfile(source,destination)
        snapshots.append(dict(path=str(destination.relative_to(stage)),sha256=sha256(destination)))
    receipt={"schema_version":"study23-phase2-independent-verification/v1","attempt":args.attempt,"phase":args.phase,"command":sys.argv,"source_snapshots":snapshots,"started_at":iso(datetime.now(UTC))}
    try:
        receipt["runtime_freeze"]=verify_runtime_freeze(stage)
        contexts,baseline,roster,pin=load_pinned_inputs(workspace,stage)
        phases=("dev-validation","later") if args.phase=="all" else (args.phase,)
        phase_results={};phase_records={};summaries=[]
        for phase in phases:
            summary,results,records=verify_phase(workspace,stage,phase,contexts,baseline)
            summaries.append(summary);phase_results[phase]=results;phase_records[phase]=records
        receipt["phases"]=summaries
        combined={p:[row for phase in phases for row in phase_results[phase][p]] for p in (*PRIMARY,*PASSIVE,*PROTECTED)}
        if "dev-validation" in phases:
            receipt["selection"]=verify_selection(stage,combined,baseline)
        receipt.update(status="passed",finished_at=iso(datetime.now(UTC)),baseline_accepted_episodes=len(baseline),eligible_calendar_days=994,limits=["Historical OHLC replay checks the frozen modeled path, not native tick ordering or TradingView execution.","Annual holiday certification and live mapping receipt remain unresolved.","Published Phase1 baseline years were previously exposed; later outcomes are not pristine holdouts."])
    except Exception as error:
        receipt.update(status="failed",finished_at=iso(datetime.now(UTC)),error=type(error).__name__+": "+str(error))
        (target/"receipt.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
        raise
    (target/"receipt.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n")
    print(json.dumps(receipt,indent=2,allow_nan=False))


def sha256(path):
    digest=hashlib.sha256()
    with open(path,"rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def equal(actual,expected,path="root"):
    if expected is None:
        if actual not in (None,""):
            raise ValueError(f"{path}: expected null, got {actual!r}")
    elif isinstance(expected,bool):
        if actual is not expected and str(actual).lower()!=str(expected).lower():
            raise ValueError(f"{path}: expected {expected!r}, got {actual!r}")
    elif isinstance(expected,(int,float)):
        if actual in (None,"") or not math.isclose(float(actual),float(expected),rel_tol=1e-10,abs_tol=1e-7):
            raise ValueError(f"{path}: expected {expected!r}, got {actual!r}")
    elif str(actual)!=str(expected):
        raise ValueError(f"{path}: expected {expected!r}, got {actual!r}")


if __name__=="__main__":main()

