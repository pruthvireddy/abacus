"""Independent Phase 3 reconstruction and saved-evidence verification.

Producer engine, runner and metric modules are deliberately not imported.
The audited input adapter may supply immutable five-minute observations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR, ROUND_CEILING
import hashlib
import json
import math
import csv
import gzip
import argparse
import sys
import shutil
import itertools
from functools import lru_cache
from pathlib import Path
from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence
from zoneinfo import ZoneInfo

import numpy as np

UTC = timezone.utc
NY = ZoneInfo("America/New_York")
ONE = timedelta(minutes=1)
FIVE = timedelta(minutes=5)


class VerificationError(ValueError):
    pass


def instant(x):
    if x is None:
        return None
    t = datetime.fromisoformat(x.replace("Z", "+00:00")) if isinstance(x,str) else x
    if t.tzinfo is None or t.utcoffset() is None:
        raise VerificationError("naive timestamp in causal evidence")
    return t.astimezone(UTC)


def stamp(x):
    return None if x is None else instant(x).isoformat().replace("+00:00","Z")


def value(obj, key, default=None):
    return obj.get(key,default) if isinstance(obj,Mapping) else getattr(obj,key,default)


def finite(x):
    return x is not None and not isinstance(x,bool) and isinstance(x,(int,float)) and math.isfinite(x)


def tick_round(price, tick=.1):
    return float((Decimal(str(price))/Decimal(str(tick))).quantize(Decimal("1"),rounding=ROUND_HALF_UP)*Decimal(str(tick)))


def percentage_stop(anchor, direction, cfg):
    return tick_round(anchor*(1-direction*cfg["stop_percent"]/100),cfg["tick_size"])


def risk_distance(entry,stop,direction,tick):
    """Risk metadata tick identity; executable prices themselves stay raw."""
    unit=Decimal(str(tick));epsilon=unit*Decimal("1e-8")
    prices=[]
    for raw in (entry,stop):
        price=Decimal(str(raw));nearest=(price/unit).quantize(Decimal("1"),rounding=ROUND_HALF_UP)*unit
        prices.append(nearest if abs(price-nearest)<=epsilon else price)
    return float(Decimal(direction)*(prices[0]-prices[1]))


def cohort(t):
    t=instant(t); local=t.astimezone(NY); m=local.hour*60+local.minute
    session="asia" if m>=1200 or m<120 else "london" if m<540 else "new_york" if 570<=m<960 else "outside_named_sessions"
    broker=t.astimezone(timezone(timedelta(hours=3)))
    return {"entry_year":local.year,"entry_date_ny":local.date().isoformat(),"entry_time_ny":local.isoformat(),
            "entry_session":session,"entry_hour":local.hour,"entry_weekday":local.weekday(),
            "entry_weekday_name":local.strftime("%A"),
            "minutes_from_trading_start":(broker-broker.replace(hour=7,minute=0,second=0,microsecond=0)).total_seconds()/60}


@dataclass(frozen=True)
class OracleMinute:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    contract: str
    available_at: datetime | None = None
    gap_before_expected: bool = False


@dataclass(frozen=True)
class OracleDay:
    episode_id: str
    broker_day: str
    parent: Mapping[str,Any]
    minutes: Sequence[Any]
    cloud: Any
    update_times: Sequence[datetime]
    high: float
    low: float
    cutoff: datetime
    expected_minute: Callable[[datetime],bool]
    shadow_status: str = "accepted"

    @property
    def direction(self):
        return int(self.parent.get("direction",1 if self.parent["side"]=="long" else -1))

    @property
    def contract(self):
        return self.parent["contract"]


DEFAULT_ECONOMICS={"tick_size":.1,"point_value":100.,"stop_percent":1.,"commission_per_side":2.5,
                   "slippage_ticks":1,"initial_capital":10000.,"risk_percent":1.,"max_leverage":10.,
                   "margin_percent":5.,"ordering":"source_ohlc","execution_minutes":1}


def economics(config=None):
    return {**DEFAULT_ECONOMICS,**(config or {})}


def position_state(parent, at, *, before_open=False):
    """Do not collapse within-minute exit uncertainty to a false/open state."""
    at=instant(at); start=instant(parent["entry_time"])
    if at<start:
        return "not_filled"
    if parent["status"]=="completed":
        end=instant(parent["exit_time"]); upper=instant(parent.get("exit_time_latest")) or end
        if end<upper and end<=at<upper:
            return "unknown"
        if at<end:
            return "open"
        return "flat"
    censor=instant(parent.get("last_observed_at"))
    return "open" if censor is not None and (at<censor or at==censor and before_open) else "unknown"


def snapshot_row(snapshot,direction,day):
    bar=value(snapshot,"bar"); known=bool(value(snapshot,"known",False))
    fields=["slope20_3","slope50_3","aligned_count","aligned_duration_minutes","alignment_start_known", "duration_left_censored","width_change_3"]
    result={"status":value(snapshot,"status","unknown"),"reason":value(snapshot,"reason",""),"known":known,
            "expected_slot":stamp(value(snapshot,"expected_slot")),"available_at":stamp(value(bar,"available_at")),
            **{key:value(bar,key) for key in ["ema20","ema50","atr14","close"]},
            **{key:value(snapshot,key) for key in fields}}
    if not known:
        result.update(direction=None,alignment=None,upper=None,lower=None,width_points=None,width_atr=None,
                      favorable_distance_atr=None,price_cloud=None)
        return result
    a,b,c,atr=(value(bar,key) for key in ["ema20","ema50","close","atr14"])
    upper,lower=max(a,b),min(a,b); sign=(a>b)-(a<b)
    result.update(direction=sign,alignment=direction*sign,upper=upper,lower=lower,width_points=upper-lower,
        width_atr=(upper-lower)/atr if atr is not None and atr>0 else None,
        favorable_distance_atr=direction*(c-(upper if direction==1 else lower))/atr if atr is not None and atr>0 else None,
        price_cloud="above" if c>upper else "below" if c<lower else "inside")
    for key,level in [("high",day.high),("low",day.low),("midpoint",(day.high+day.low)/2)]:
        for name,ema in [("ema20",a),("ema50",b)]:
            result[f"{name}_{key}_confluence"]=abs(ema-level)<=.1*atr if atr is not None and atr>0 else None
    return result


def gate(snapshot,direction,policy):
    if policy not in {"G1","G2"}:
        raise VerificationError("unexpected gate")
    if not value(snapshot,"known",False):
        return None
    bar=value(snapshot,"bar"); fast,slow,close=(value(bar,k) for k in ["ema20","ema50","close"])
    if direction*(fast-slow)<=0 or direction*(close-(max(fast,slow) if direction==1 else min(fast,slow)))<=0:
        return False
    if policy=="G1":
        return True
    slopes=[value(snapshot,"slope20_3"),value(snapshot,"slope50_3")]
    return None if any(s is None for s in slopes) else all(direction*s>0 for s in slopes)


def reference_gate(day,policy):
    """Separate effective standing state from later same-opening candidate."""
    shadow=instant(day.parent["entry_time"]); standing=None; standing_at=None; tie=None; tied_opposite=None; orders=[]
    for at in day.update_times:
        at=instant(at)
        if at>shadow:break
        snap=day.cloud.snapshot(at,day.contract); sides={s:gate(snap,s,policy) for s in [1,-1]}
        first=standing is None; coincident=at==shadow and not first
        orders.append({"time":stamp(at),"event":"gate_candidate" if coincident else "gate_update",
            "coincident_shadow":at==shadow,"saved_initial_submission":first,
            "long_admission":sides[1],"short_admission":sides[-1],"snapshot":snapshot_row(snap,day.direction,day)})
        if coincident:tie=sides[day.direction];tied_opposite=sides[-day.direction]
        else:standing,standing_at=sides,at
    if standing is None:return {"status":"unknown","action_status":"unknown_gate_update_prefix"},orders
    admit=standing[day.direction]; opposite=standing[-day.direction]
    changed=tie is not None and (admit is True)!=(tie is True)
    # A tied None also changes known admission to rule-based abstention.
    has_tie=any(r["event"]=="gate_candidate" for r in orders)
    changed=has_tie and (admit is True)!=(tie is True)
    bar=next((b for b in day.minutes if instant(value(b,"timestamp"))==shadow),None)
    dual=bar is not None and value(bar,"high")>=day.high and value(bar,"low")<=day.low
    result={"gate_admission":admit,"gate_update_time":stamp(standing_at),
            "gate_staleness_minutes":(shadow-standing_at).total_seconds()/60,"gate_feature_unknown":admit is None,
            "tied_candidate_changes_admission":changed}
    if has_tie:result["tied_candidate_admission"]=tie
    if changed or (admit is not True and (opposite is True or tied_opposite is True) and dual):
        result.update(status="unknown",action_status="unknown_admission_cancellation" if changed else "unknown_shadow_cancel_ordering",
                      ambiguous=True,net_dollars=None,original_filled=None)
    elif admit is not True:
        result.update(status="no_fill",action_status="unknown_feature_abstention" if admit is None else "blocked_first_shadow_consumed",
                      net_dollars=0.,original_filled=False,original_fills=0,later_opposite_entry_prohibited=True)
    else:
        result.update(status=day.parent["status"],action_status="admitted_first_shadow",net_dollars=day.parent.get("net_dollars"),
                      original_filled=True,original_fills=1,source_parent_parity=True)
    return result,orders


def reference_monitoring(day,config=None):
    cfg=economics(config); parent=day.parent; d=day.direction; slip=cfg["tick_size"]*cfg["slippage_ticks"]
    lower=instant(parent["entry_time"]); upper=instant(parent.get("entry_time_latest")) or lower
    armed={20:False,50:False}; counts={20:0,50:0}; unknown={20:False,50:False}; rows=[]
    for bar in day.cloud.for_window(lower,day.cutoff,full_after=upper):
        t=instant(value(bar,"timestamp")); close_at=instant(value(bar,"available_at"))
        if t<upper or close_at>day.cutoff:continue
        before=snapshot_row(day.cloud.snapshot(t,day.contract),d,day)
        current=snapshot_row(day.cloud.snapshot(close_at,day.contract),d,day)
        usable=bool(value(bar,"usable") and value(bar,"contract")==day.contract)
        at_open=position_state(parent,t); at_close=position_state(parent,close_at,before_open=True)
        close=value(bar,"close")
        liquidation=(d*(close-d*slip-parent["entry_price"])*cfg["point_value"]-2*cfg["commission_per_side"]) if usable and at_close=="open" else None
        departure=(value(bar,"low")>before["upper"] if d==1 else value(bar,"high")<before["lower"]) if usable and before["known"] else None
        row={"episode_id":day.episode_id,"broker_day":day.broker_day,"time":stamp(t),"available_at":stamp(close_at),
            "contract":value(bar,"contract"),**{k:value(bar,k) for k in ["open","high","low","close"]},
            "usable":usable,"feature_valid":bool(value(bar,"feature_valid")),"quality_reason":value(bar,"quality_reason"),
            "known_closure_before":bool(value(bar,"known_closure_before",False)),
            "parent_state_at_open":at_open,"parent_state_at_decision":at_close,
            "parent_state_before_next_open":"open" if instant(parent.get("exit_time"))==close_at else at_close,
            "parent_decision_time_bound_ambiguous":at_close=="unknown",
            "open_position_landmark":at_open=="open" and at_close=="open",
            "parent_liquidation_net_unit":liquidation,"departure":departure,"prior":before,"current":current,"direction":d,
            **{"event_"+k:v for k,v in cohort(close_at).items()}}
        for ema in [20,50]:
            level=before[f"ema{ema}"] if before["known"] else None
            penetration=(value(bar,"low")<=level if d==1 else value(bar,"high")>=level) if usable and level is not None else None
            contact=armed[ema] and penetration is True
            if not usable or not before["known"] or not current["known"] and not contact:unknown[ema]=True
            if armed[ema] and penetration is None:unknown[ema]=True;armed[ema]=False
            if contact:counts[ema]+=1;armed[ema]=False
            if departure is True and current["known"]:armed[ema]=True
            row.update({f"ema{ema}_frozen_level":level,f"ema{ema}_penetration":penetration,
                f"ema{ema}_contact":contact,f"ema{ema}_contact_count_observed":counts[ema],
                f"ema{ema}_contact_number":counts[ema] if contact and not unknown[ema] else None,
                f"ema{ema}_contact_order_unknown":unknown[ema],f"ema{ema}_armed_after_close":armed[ema]})
        rows.append(row)
    return rows


def size_reference(equity,allocation,price,stop,direction,cfg,active_notional=0):
    entry=price
    risk=direction*(price-stop)*cfg["point_value"]
    budget=equity*cfg["risk_percent"]*.01*allocation
    free=min(equity*cfg["max_leverage"],equity/(cfg["margin_percent"]*.01))-active_notional
    risk_q=max(0,math.floor(budget/risk+1e-9)) if risk>0 and budget>0 else 0
    exposure_q=max(0,math.floor(free/(entry*cfg["point_value"]))) if entry>0 else 0
    return {"quantity":min(risk_q,exposure_q),"allocation_fraction":allocation,"budget_dollars":budget,
            "planned_risk_per_contract":risk if risk>0 else None,"risk_quantity":risk_q,"exposure_quantity":exposure_q,
            "quantity_skip":min(risk_q,exposure_q)<1,"margin_or_leverage_infeasible":exposure_q<1,"spent_risk_not_restored":True,
            "sizing_anchor":"raw_submitted_price","fees_slips_gaps_not_reserved":True,
            "estimated_roundtrip_cost_per_contract":2*cfg["commission_per_side"]+2*cfg["slippage_ticks"]*cfg["tick_size"]*cfg["point_value"]}


def authored_path(bar,ordering):
    o,h,l,c=(float(value(bar,k)) for k in ["open","high","low","close"])
    high_first=ordering=="high_first" or ordering=="source_ohlc" and abs(h-o)<abs(o-l)
    return [o,h,l,c] if high_first else [o,l,h,c]


def after_parent_fill(bar,parent,ordering):
    path=authored_path(bar,ordering)
    if parent.get("entry_time_precision")!="within_bar":return path
    raw=parent["entry_price_raw"];d=int(parent["direction"])
    for i,(a,b) in enumerate(zip(path,path[1:])):
        if d==1 and a<=raw<=b and b>a or d==-1 and b<=raw<=a and b<a:
            return [raw]+path[i+1:]
    raise VerificationError("parent fill not reproducible on declared authored path")


def compare(saved,expected,path="", *, tolerance=1e-8):
    """Strict expected-field comparisons; extra producer metadata stays separate."""
    count=0
    if isinstance(expected,dict):
        if not isinstance(saved,dict):raise VerificationError(path+": expected object")
        for k,v in expected.items():
            if k not in saved:raise VerificationError(path+":"+k+": missing field")
            count+=compare(saved[k],v,path+":"+k,tolerance=tolerance)
    elif isinstance(expected,(list,tuple)):
        if not isinstance(saved,(list,tuple)) or len(saved)!=len(expected):raise VerificationError(path+": row count mismatch")
        for i,(a,b) in enumerate(zip(saved,expected)):count+=compare(a,b,path+f"[{i}]",tolerance=tolerance)
    else:
        valid=((saved is expected) if isinstance(expected,bool) or expected is None else
            (finite(saved) and saved==expected) if isinstance(expected,int) else
            (finite(saved) and math.isclose(float(saved),float(expected),rel_tol=1e-11,abs_tol=tolerance)) if isinstance(expected,float) else saved==expected)
        if not valid:raise VerificationError(f"{path}: expected {expected!r}, got {saved!r}")
        count=1
    return count


def verify_gate_result(saved,day,policy):
    expected,orders=reference_gate(day,policy)
    comparisons=compare(saved["episode"],expected,"episode")+compare(saved["orders"],orders,"orders")
    if expected.get("original_filled") is True:
        if len(saved["trades"])!=1:raise VerificationError("admitted gate must retain one original trade")
        comparisons+=compare(saved["trades"][0],dict(day.parent),"unchanged_parent")
    elif saved["trades"]:
        raise VerificationError("blocked/unknown gate fabricated an executed trade")
    return comparisons


def verify_monitoring(saved_rows,day,config=None):
    return compare(saved_rows,reference_monitoring(day,config),"monitoring")


@dataclass
class OracleLeg:
    name: str
    quantity: int
    entry_at: datetime
    raw_entry: float
    entry: float
    initial_stop: float
    stop: float
    source_stop: float
    reset_at: datetime | None
    signal_at: datetime | None
    reset_done: bool = False
    queued_stop: bool = False
    mfe: float = 0.
    mae: float = 0.
    reset_stop: float | None = None


_UNSET=object()


def reference_execution(day,policy,config=None,*,mode="standardized",equity_start=_UNSET):
    """Independent expected-minute walk with explicit close/open phases.

    Decisions run even when the following opening price is absent. Cloud
    unknowns prohibit new actions; execution unknowns censor live positions.
    """
    if policy not in {"BASE","A20","A50","X1","X2","T50"}:
        raise VerificationError("execution reference needs isolated management policy")
    cfg=economics(config); d=day.direction; parent=day.parent
    slip=cfg["tick_size"]*cfg["slippage_ticks"]; commission=cfg["commission_per_side"]
    finance=mode in {"full_parent","half_parent","financed_overlay"}
    if finance and equity_start is None:
        return {"status":"unknown","action_status":"unknown_account_equity","original_quantity":None,
                "original_filled":None,"add_filled":None,"ending_equity":None,"net_dollars":None},[],[],[],[]
    equity=cfg["initial_capital"] if equity_start is _UNSET or equity_start is None else equity_start
    control_only=policy=="BASE" or mode in {"full_parent","half_parent","parent_1","parent_2"}
    boundary=day.high if d==1 else day.low
    sized=size_reference(equity,.5 if mode in {"half_parent","financed_overlay"} else 1.,boundary,parent["initial_stop"],d,cfg)
    q=sized["quantity"] if finance else 2 if mode=="parent_2" else 1
    if q==0:return {"status":"no_fill","net_dollars":0.,"original_fills":0,"add_fills":0,
                    "action_status":"original_quantity_skip","original_quantity":0},[],[],[],[]
    entry=instant(parent["entry_time"])
    prices={instant(value(b,"timestamp")):b for b in day.minutes}
    observations={instant(r["available_at"]):r for r in reference_monitoring(day,cfg)}
    active={}; trades=[]; signals=[]; actions=[]; exposure=[]
    realized=peak=drawdown=peak_notional=0.; peak_quantity=0; original_fills=add_fills=0
    attempted=armed=False; failure=None; cross=None; pending=None; exit_queue=None
    last_clock=None; action_status="unprocessed"; add_opportunity=False; cancellations=0; add_skip=0; unknown_add=False

    def start(name,t,raw,stop,quantity,signal_at=None):
        nonlocal original_fills,add_fills
        actual=raw+d*slip
        reset=instant(parent.get("reset_stop_active_at")) if name=="original" else t.replace(minute=t.minute//5*5,second=0,microsecond=0)+FIVE
        active[name]=OracleLeg(name,quantity,t,raw,actual,stop,stop,stop,reset,signal_at)
        if name=="original":original_fills+=1
        else:add_fills+=1
        actions.append({"event":"fill","time":stamp(t),"leg":name,"raw_price":raw,"actual_price":actual,"quantity":quantity,"initial_stop":stop})

    def finish(name,t,raw,reason,precision="observed_open",competing=False):
        nonlocal realized
        leg=active.pop(name);initial_points=risk_distance(leg.entry,leg.initial_stop,d,cfg["tick_size"])
        risk=initial_points*cfg["point_value"]*leg.quantity
        r={"leg":name,"direction":d,"quantity":leg.quantity,"entry_time":stamp(leg.entry_at),
           "entry_time_latest":parent.get("entry_time_latest") if name=="original" else stamp(leg.entry_at),
           "entry_time_precision":parent.get("entry_time_precision","observed_open") if name=="original" else "observed_open",
           "entry_price_raw":leg.raw_entry,"entry_price":leg.entry,"initial_stop":leg.initial_stop,
           "reset_stop":leg.reset_stop,"reset_stop_active_at":stamp(leg.reset_at) if leg.reset_done else None,
           "risk_initial_dollars":risk if risk>0 else None,"risk_initial_points":initial_points if initial_points>0 else None}
        if raw is None:
            r.update(status="censored",exit_time=None,exit_reason=None,net_dollars=None,last_observed_at=stamp(t),censor_reason=reason,
                observed_holding_minutes=(t-leg.entry_at).total_seconds()/60,mfe_points=leg.mfe,mae_points=leg.mae,
                holding_minutes=None,holding_minutes_lower=None,holding_minutes_upper=None,holding_bars=None,excursions_complete=False)
            effective_points=risk_distance(leg.entry,leg.stop,d,cfg["tick_size"])
            r.update(exit_time_latest=None,exit_time_precision=None,effective_stop=leg.stop,source_stop=leg.source_stop,
                risk_effective_points=effective_points if effective_points>0 else None,
                risk_effective_dollars=effective_points*cfg["point_value"]*leg.quantity if effective_points>0 else None)
        else:
            actual=raw-d*slip; gross=d*(actual-leg.entry)*cfg["point_value"]*leg.quantity
            net=gross-2*commission*leg.quantity
            r.update(status="completed",exit_time=stamp(t),exit_time_latest=stamp(t+ONE) if precision=="within_bar" else stamp(t),
                exit_time_precision=precision,exit_reason=reason,exit_price_raw=raw,exit_price=actual,
                raw_price_points=d*(raw-leg.raw_entry),raw_price_dollars=d*(raw-leg.raw_entry)*cfg["point_value"]*leg.quantity,
                gross_points=d*(actual-leg.entry),gross_dollars=gross,commission_dollars=2*commission*leg.quantity,
                net_points=net/(cfg["point_value"]*leg.quantity),net_dollars=net,
                gross_r=gross/risk if risk>0 else None,net_r=net/risk if risk>0 else None,
                effective_stop=leg.stop,source_stop=leg.source_stop,mfe_points=leg.mfe,mae_points=leg.mae,
                holding_minutes=(t-leg.entry_at).total_seconds()/60,competing_exit_orders=competing)
            entry_upper=(instant(parent.get("entry_time_latest")) or leg.entry_at) if name=="original" else leg.entry_at
            exit_upper=t+ONE if precision=="within_bar" else t
            r.update(holding_minutes_lower=max(0.,(t-entry_upper).total_seconds()/60),holding_minutes_upper=max(0.,(exit_upper-leg.entry_at).total_seconds()/60))
            period=15 if name=="original" else 5
            a=leg.entry_at.replace(minute=leg.entry_at.minute//period*period,second=0,microsecond=0)
            b=t.replace(minute=t.minute//period*period,second=0,microsecond=0)
            effective_points=risk_distance(leg.entry,leg.stop,d,cfg["tick_size"]);effective_risk=effective_points*cfg["point_value"]*leg.quantity
            r.update(holding_bars=int((b-a).total_seconds()/(period*60)),holding_decision_minutes=period,last_observed_at=stamp(t),
                observed_holding_minutes=None,censor_reason=None,excursions_complete=True,risk_effective_dollars=effective_risk if effective_risk>0 else None,
                risk_effective_points=effective_points if effective_points>0 else None,source_style_r=net/effective_risk if effective_risk>0 else None)
            realized+=net
        trades.append(r)
        actions.append({"event":"censor" if raw is None else "exit","time":stamp(t),"leg":name,"reason":reason,"raw_price":raw,"competing":competing})

    def mark(raw):
        nonlocal peak,drawdown,peak_notional,peak_quantity
        floating=0.
        for leg in active.values():
            move=d*(raw-leg.entry);leg.mfe=max(leg.mfe,move);leg.mae=max(leg.mae,-move)
            floating+=(d*(raw-d*slip-leg.entry)*cfg["point_value"]-2*commission)*leg.quantity
        mtm=realized+floating;peak=max(peak,mtm);drawdown=max(drawdown,peak-mtm)
        notional=sum(l.quantity for l in active.values())*raw*cfg["point_value"]
        peak_notional=max(peak_notional,notional)
        peak_quantity=max(peak_quantity,sum(l.quantity for l in active.values()))
        return mtm,floating,notional

    def decision(obs,t):
        nonlocal attempted,armed,failure,cross,pending,exit_queue,action_status,add_opportunity,add_skip
        if control_only or "original" not in active or t>=day.cutoff:return
        prior,current=obs["prior"],obs["current"];good=obs["usable"] and current["known"]
        slot=instant(obs["time"]);leg=active["original"]
        liquidation=(d*(obs["close"]-d*slip-leg.entry)*cfg["point_value"]-2*commission)*leg.quantity if obs["usable"] else None
        if policy.startswith("A"):
            ema=20 if policy=="A20" else 50
            if attempted:return
            known_contact=armed and obs[f"ema{ema}_penetration"] is True
            if not known_contact and (not prior["known"] or not obs["usable"] or not current["known"]):
                attempted=True;add_opportunity=None;action_status="unknown_support_prefix_abstention"
                actions.append({"event":"unknown_support_prefix","time":stamp(t),"ema":ema})
                return
            if armed and obs[f"ema{ema}_penetration"] is True:
                attempted=True;add_opportunity=True;level=obs[f"ema{ema}_frozen_level"]
                confirmed=good and current["direction"]==d and d*(obs["close"]-level)>0
                actions.append({"event":"first_contact_consumed","time":stamp(t),"ema":ema,"frozen_level":level,
                                "confirmed":confirmed,"liquidation_net":liquidation,"parent_open":True})
                if not confirmed or liquidation is None or liquidation<=1e-8:
                    action_status="rejected_confirmation" if not confirmed else "rejected_nonpositive_liquidation";return
                stop=percentage_stop(obs["close"],d,cfg)
                capacity=size_reference(equity,.5,obs["close"],stop,d,cfg,active_notional=leg.quantity*obs["close"]*cfg["point_value"])
                quantity=capacity["quantity"] if finance else 1
                order={"time":stamp(t),"frozen_level":level,"signal_close":obs["close"],"initial_stop":stop,
                       "quantity":quantity,"capacity":capacity if finance else None,"original_liquidation_net":liquidation}
                signals.append(order)
                if quantity:pending=order;action_status="pending_contingent_add"
                else:add_skip+=1;action_status="add_quantity_skip"
            elif obs["departure"] is True and good:
                armed=True;actions.append({"event":"departure_armed","time":stamp(t),"ema":ema,"prior_upper":prior["upper"],"prior_lower":prior["lower"]})
        elif policy=="X1":
            if not good or not prior["known"]:
                failure=None;actions.append({"event":"failure_confirmation_reset_unknown","time":stamp(t)});return
            if failure is not None:
                oldslot,edge=failure
                if day.cloud.adjacent(oldslot,slot) and d*(obs["close"]-edge)<0:
                    exit_queue="ema_X1";signals.append({"time":stamp(t),"frozen_edge":edge,"original_liquidation_net":liquidation});failure=None;return
                failure=None
            edge=prior["lower"] if d==1 else prior["upper"]
            if d*(obs["close"]-edge)<0:
                failure=(slot,edge);actions.append({"event":"failure_first_close","time":stamp(t),"frozen_edge":edge})
        elif policy=="X2":
            if not good:
                cross=None;actions.append({"event":"cross_confirmation_reset_unknown","time":stamp(t)});return
            state=d*current["direction"]
            if cross is not None and cross[1] in (0,1) and state==-1 and day.cloud.adjacent(cross[0],slot):
                exit_queue="ema_X2";signals.append({"time":stamp(t),"prior_alignment":cross[1],"current_alignment":state,"original_liquidation_net":liquidation})
            cross=(slot,state)
        elif policy=="T50":
            if not good or not prior["known"]:
                actions.append({"event":"trail_no_action_unknown","time":stamp(t)});return
            rounding=ROUND_FLOOR if d==1 else ROUND_CEILING
            candidate=float(((Decimal(str(prior["ema50"]))/Decimal(str(cfg["tick_size"]))).to_integral_value(rounding=rounding)-d)*Decimal(str(cfg["tick_size"])))
            if d*(candidate-leg.stop)<=0:
                actions.append({"event":"trail_preserves_tighter_stop","time":stamp(t),"proposed_stop":candidate,"effective_stop":leg.stop});return
            if d*(obs["close"]-candidate)<=0:
                exit_queue="ema_T50_already_breached";signals.append({"time":stamp(t),"proposed_stop":candidate})
            else:
                leg.stop=candidate;actions.append({"event":"trail_future_activation","time":stamp(t),"effective_stop":candidate,"proposed_stop":candidate})

    last_available=max(prices) if prices else entry
    def resets(t):
        for name,leg in list(active.items()):
            if leg.reset_done or leg.reset_at is None or t<leg.reset_at:continue
            period=15 if name=="original" else 5
            opening=leg.entry_at.replace(minute=leg.entry_at.minute//period*period,second=0,microsecond=0)
            expected=[opening+i*ONE for i in range(int((leg.reset_at-opening)/ONE))]
            if any(s not in prices or value(prices[s],"contract")!=day.contract for s in expected):
                finish(name,leg.reset_at,None,"unobservable_entry_candle_reset");continue
            proposed=parent.get("reset_stop") if name=="original" else percentage_stop(leg.entry,d,cfg)
            if proposed is None:raise VerificationError("live surviving parent reset has no frozen stop")
            leg.source_stop=proposed
            leg.stop=(max(leg.stop,proposed) if d==1 else min(leg.stop,proposed)) if policy=="T50" and name=="original" else proposed
            leg.reset_done=True;leg.reset_stop=proposed
            leg.queued_stop=d*(value(prices[leg.reset_at-ONE],"close")-leg.stop)<=0
            actions.append({"event":"stop_reset","time":stamp(leg.reset_at),"leg":name,"source_proposed_stop":proposed,
                "effective_stop":leg.stop,"decision_minutes":period,"triggered_at_creation":leg.queued_stop})
    t=entry
    while t<=last_available:
        # Resolve completed decision first; opening prices remain unread.
        resets(t)
        if t in observations:decision(observations[t],t)
        bar=prices.get(t)
        if bar is None:
            if day.expected_minute(t) and (active or pending or not original_fills):
                for name in list(active):finish(name,t,None,"missing_expected_execution_minutes")
                if pending is not None:
                    action_status="unknown_contingent_add_execution";unknown_add=True;pending=None
                    actions.append({"event":"unknown_pending_add","time":stamp(t),"reason":"missing_expected_execution_minutes"})
                break
            t+=ONE;continue
        if value(bar,"contract")!=day.contract:
            for name in list(active):finish(name,t,None,"contract_transition")
            if pending is not None:
                action_status="unknown_contingent_add_execution";unknown_add=True;pending=None
                actions.append({"event":"unknown_pending_add","time":stamp(t),"reason":"contract_transition"})
            break
        if not original_fills:
            start("original",t,parent["entry_price_raw"],parent["initial_stop"],q)
            mark(parent["entry_price_raw"])
        if "original" in active and exit_queue is not None:
            competing=active["original"].queued_stop or d*(value(bar,"open")-active["original"].stop)<=0
            finish("original",t,value(bar,"open"),exit_queue,competing=competing);exit_queue=None
        for name in list(active):
            leg=active[name]
            if t>=day.cutoff:finish(name,t,value(bar,"open"),"time",competing=leg.queued_stop or d*(value(bar,"open")-leg.stop)<=0)
            elif leg.queued_stop or d*(value(bar,"open")-leg.stop)<=0:
                if name=="original" and t==entry and parent.get("entry_time_precision")=="within_bar":continue
                finish(name,t,value(bar,"open"),"stop")
        if pending is not None:
            if "original" in active and t<day.cutoff:
                start("add",t,value(bar,"open"),pending["initial_stop"],pending["quantity"],instant(pending["time"]));action_status="add_filled"
                mark(value(bar,"open"))
                if d*(value(bar,"open")-active["add"].stop)<=0:finish("add",t,value(bar,"open"),"stop")
            else:
                cancellations+=1;action_status="contingent_add_canceled_parent_exit"
                actions.append({"event":"pending_add_cancel","time":stamp(t),"reason":"parent_exited_before_release"})
            pending=None
        path=after_parent_fill(bar,parent,cfg["ordering"]) if t==entry else authored_path(bar,cfg["ordering"])
        extrema=[]
        for a,b in zip(path,path[1:]):
            extrema.append(mark(a)[0])
            hits=[]
            for name in list(active):
                leg=active[name]
                if d*(a-leg.stop)<=0 or d*(b-leg.stop)<=0:
                    raw=a if d*(a-leg.stop)<=0 else leg.stop
                    hits.append((abs(raw-a),name,raw))
            for _,name,raw in sorted(hits):
                extrema.append(mark(raw)[0])
                finish(name,t,raw,"stop","within_bar")
            extrema.append(mark(b)[0])
        mtm,floating,notional=mark(value(bar,"close"))
        exposure.append({"time":stamp(t),"available_at":stamp(t+ONE),"closed_net_dollars":realized,
            "floating_liquidation_net_dollars":floating,"mtm_net_dollars":mtm,
            "intraminute_mtm_min":min(extrema or [mtm]),"intraminute_mtm_max":max(extrema or [mtm]),
            "running_mtm_peak":peak,"max_mtm_drawdown":drawdown,"active_quantity":sum(l.quantity for l in active.values()),
            "running_peak_notional":peak_notional,"running_peak_quantity":peak_quantity,
            "notional":notional,"concurrent_legs":len(active),"price_path":cfg["ordering"],
            "combined_active_stop_risk":sum(max(0,d*(l.entry-l.stop))*cfg["point_value"]*l.quantity for l in active.values())})
        last_clock=t+ONE
        if not active and pending is None:break
        t+=ONE
    if active:
        resets(last_clock or entry)
        if last_clock in observations:decision(observations[last_clock],last_clock)
    for name in list(active):finish(name,last_clock or entry,None,"retained_endpoint_open")
    if pending is not None:
        action_status="unknown_contingent_add_at_endpoint";unknown_add=True
        actions.append({"event":"unknown_pending_add_at_endpoint","time":stamp(last_clock or entry)})
    unknown=any(r["status"]!="completed" for r in trades)
    result={"status":"censored" if unknown else "completed","original_fills":original_fills,"add_fills":add_fills,
        "net_dollars":None if unknown else realized,"known_completed_net_dollars":realized,
        "max_mtm_drawdown_dollars":drawdown,"peak_notional":peak_notional,"original_quantity":q,
        "add_attempts":int(attempted),"add_opportunity":add_opportunity,"signals":len(signals),
        "pending_add_cancellations":cancellations,"add_quantity_skips":add_skip,"action_status":action_status,
        "original_filled":original_fills>0,"add_filled":None if unknown_add else add_fills>0,"ambiguous":unknown_add}
    if result["action_status"]=="unprocessed":result["action_status"]="no_ema_signal"
    result.update(peak_margin_dollars=peak_notional*cfg["margin_percent"]*.01,peak_concurrent_quantity=peak_quantity)
    result["financial_eligible_landmarks"]=sum(r["open_position_landmark"] for r in observations.values()) if finance else None
    return result,trades,signals,actions,exposure


CORE=("G1","G2","A20","A50","X1","X2")
SESSIONS=("Asia","London","New York","Outside")
SIDES=("combined","long","short")
YEARS=("all",*[str(y) for y in range(2018,2027)])


def origin(t,d):
    c=cohort(t)
    return {"year":str(c["entry_year"]),"session":{"asia":"Asia","london":"London","new_york":"New York",
        "outside_named_sessions":"Outside"}[c["entry_session"]],"side":"long" if d==1 else "short",
        "hour":c["entry_hour"],"weekday":c["entry_weekday_name"]}


def belongs(row,y,s,d):
    return (y=="all" or row["year"]==y) and (s=="all" or row["session"]==s) and (d=="combined" or row["side"]==d)


def dimensions():
    return [(y,s,d) for y in YEARS for s in ("all",*SESSIONS) for d in SIDES]


def known_pnl(row):
    if row is None:return None
    if row["status"] in ("no_fill","known_no_fill"):
        if row["net_dollars"]!=0. or isinstance(row["net_dollars"],bool):raise VerificationError("known abstention requires numeric zero")
        return 0.
    return row.get("net_dollars") if row["status"]=="completed" else None


def mean_defined(values):
    values=[v for v in values if v is not None]
    return sum(values)/len(values) if values else None


def fraction(a,b):
    return a/b if b else None


def bootstrap_reference(values,calendar,*,weeks=4,replications=10000,seed=230015):
    """Independent block-count weights, preserving nulls and empty blocks."""
    if not values or not calendar:return []
    days=[datetime.fromisoformat(str(d)) for d in calendar]
    anchor=min(days);anchor-=timedelta(days=anchor.weekday())
    blocks=(max(days)-anchor).days//(weeks*7)+1
    width=len(values[0][1]);sums=np.zeros((blocks,width));counts=np.zeros((blocks,width))
    for day,vector in values:
        b=(datetime.fromisoformat(day)-anchor).days//(weeks*7)
        if b<0 or b>=blocks:raise VerificationError("paired episode outside frozen calendar")
        for i,x in enumerate(vector):
            if x is not None:sums[b,i]+=x;counts[b,i]+=1
    weights=bootstrap_weights(blocks,replications,seed)
    numerator=weights@sums;denominator=weights@counts
    columns=[(numerator[denominator[:,i]>0,i]/denominator[denominator[:,i]>0,i]).tolist() for i in range(width)]
    alpha=.05/6
    output=[]
    for col in columns:
        quantiles=np.quantile(col,[.025,.975,alpha/2,1-alpha/2]) if col else [None]*4
        output.append(dict(zip(["difference_low","difference_high","adjusted_low","adjusted_high"],
            [float(q) if q is not None else None for q in quantiles])))
    return output


@lru_cache(maxsize=16)
def bootstrap_weights(blocks,replications,seed):
    # Integer multiplicities provide a separate resampling implementation.
    rng=np.random.default_rng(seed);weights=np.zeros((replications,blocks),dtype=np.uint16)
    for offset in range(0,replications,250):
        draw=rng.integers(0,blocks,size=(min(250,replications-offset),blocks))
        np.add.at(weights,(np.repeat(np.arange(offset,offset+len(draw)),blocks),draw.ravel()),1)
    weights.flags.writeable=False
    return weights


def year_calendar(calendar,y):
    return list(calendar) if y=="all" else [d for d in calendar if f"{y}-01-01"<=d<=f"{int(y)+1}-01-01"]


def paired_reference(episodes,parents,calendar,*,intervals=True,cohorts=None):
    groups=defaultdict(dict)
    for r in episodes:
        if r.get("scenario","primary-one-tick")!="primary-one-tick":continue
        k=(r["policy"],r["mode"])
        if r["episode_id"] in groups[k]:raise VerificationError("duplicate policy/episode")
        groups[k][r["episode_id"]]=r
    effects={};common={};origins={i:origin(t["entry_time"],t["direction"]) for i,t in parents.items()}
    for eid in parents:
        vector=[]
        for policy in CORE:
            mode="financed_overlay" if policy.startswith("A") else "standardized"
            control="half_parent" if policy.startswith("A") else "parent_1"
            a=known_pnl(groups[(policy,mode)].get(eid));b=known_pnl(groups[("BASE",control)].get(eid))
            vector.append(a-b if a is not None and b is not None else None)
        effects[eid]=vector;common[eid]=all(x is not None for x in vector)
    rows=[]
    for y,s,d in (dimensions() if cohorts is None else cohorts):
        ids=[i for i in parents if belongs(origins[i],y,s,d)];complete=[i for i in ids if common[i]]
        vectors=[(parents[i]["broker_day"],effects[i] if common[i] else [None]*6) for i in ids]
        cis=bootstrap_reference(vectors,year_calendar(calendar,y)) if intervals else []
        for col,policy in enumerate(CORE):
            mode="financed_overlay" if policy.startswith("A") else "standardized"
            control="half_parent" if policy.startswith("A") else "parent_1"
            selected=[groups[(policy,mode)][i] for i in ids]
            values=[effects[i][col] for i in complete]
            individual=[effects[i][col] for i in ids if effects[i][col] is not None]
            absent=[i for i in ids if known_pnl(groups[(policy,mode)][i])==0 and not groups[(policy,mode)][i].get("original_fills")]
            base=[known_pnl(groups[("BASE",control)][i]) for i in complete]
            alt=[known_pnl(groups[(policy,mode)][i]) for i in complete]
            rows.append({"policy":policy,"mode":mode,"control":"BASE:"+control,"anchor":"original_actual_entry","year":y,"session":s,"side":d,
                "episodes":len(ids),"complete_pairs":len(complete),"missing_pairs":len(ids)-len(complete),"individual_pairs":len(individual),
                "individual_mean_difference":mean_defined(individual),"baseline_net_dollars":sum(base) if complete else None,
                "alternative_net_dollars":sum(alt) if complete else None,"mean_difference":mean_defined(values),
                **(cis[col] if cis else dict.fromkeys(["difference_low","difference_high","adjusted_low","adjusted_high"])),
                "adjusted_confidence":1-.05/6,"improved":sum(v>1e-8 for v in values),"deteriorated":sum(v<-1e-8 for v in values),
                "equal":sum(abs(v)<=1e-8 for v in values),"signals":sum(r.get("signals",0) for r in selected),
                "original_fills":sum(r.get("original_fills",0) for r in selected),"add_fills":sum(r.get("add_fills",0) for r in selected),
                "opportunities":len(ids),"add_attempts":sum(r.get("add_attempts",0) for r in selected),
                "observed_add_contacts":sum(r.get("add_opportunity") is True for r in selected),"unknown_add_contacts":sum(r.get("add_opportunity") is None for r in selected),
                "rejections":sum(str(r.get("action_status","")).startswith("rejected_") for r in selected),
                "unknown_feature_slots":sum(r.get("unknown_feature_count",0) for r in selected),
                "completed":sum(r["status"]=="completed" for r in selected),"known_zero":sum(known_pnl(r)==0 and r["status"]=="no_fill" for r in selected),
                "unknown_execution":sum(known_pnl(r) is None for r in selected),"feature_abstentions":sum(r.get("gate_feature_unknown",False) for r in selected),
                "blocked":sum(r.get("action_status")=="blocked_first_shadow_consumed" for r in selected),
                "cancellations":sum(r.get("pending_add_cancellations",0) for r in selected),"quantity_skips":sum(r.get("action_status")=="original_quantity_skip" for r in selected),
                "signal_rate":fraction(sum(r.get("signals",0) for r in selected),len(ids)),"add_participation":fraction(sum(r.get("add_fills",0) for r in selected),len(ids)),
                "ambiguous":sum(bool(r.get("ambiguous")) for r in selected),"participation":fraction(sum(r.get("original_fills",0) for r in selected),len(ids)),
                "missed_winners":sum(parents[i].get("net_dollars") is not None and parents[i]["net_dollars"]>1e-8 for i in absent),
                "avoided_losses":sum(parents[i].get("net_dollars") is not None and parents[i]["net_dollars"]<-1e-8 for i in absent),"partial_year":y=="2026"})
    return rows,effects,common


def closed_drawdown_reference(trades):
    rows=[];total=peak=maximum=0.
    for t in sorted((r for r in trades if r["status"]=="completed"),key=lambda r:(instant(r["exit_time"]),r["trade_id"])):
        total+=t["net_dollars"];peak=max(peak,total);maximum=max(maximum,peak-total)
        rows.append({"trade_id":t["trade_id"],"exit_time":t["exit_time"],"cumulative_net_dollars":total,"drawdown_dollars":total-peak})
    return rows,maximum


def trade_cohorts_reference(trades,episodes):
    rows=[];paths=[];timing=[]
    for p,m in sorted({(r["policy"],r["mode"]) for r in episodes}):
        group=[{**t,**origin(t["entry_time"],t["direction"])} for t in trades if (t["policy"],t["mode"])==(p,m)]
        for role in ("combined","original","add"):
            role_trades=[t for t in group if role=="combined" or t.get("leg","original")==role]
            full,_=closed_drawdown_reference(role_trades)
            paths.extend({**r,"policy":p,"mode":m,"leg":role,"anchor":"actual_leg_fill"} for r in full)
            for y,s,d in dimensions():
                subset=[t for t in role_trades if belongs(t,y,s,d)];closed=[t for t in subset if t["status"]=="completed"]
                net=[t["net_dollars"] for t in closed];wins=[v for v in net if v>1e-8];losses=[v for v in net if v<-1e-8]
                _,dd=closed_drawdown_reference(closed)
                rows.append({"policy":p,"mode":m,"leg":role,"anchor":"actual_leg_fill","year":y,"session":s,"side":d,
                    "fills":len(subset),"completed":len(closed),"censored":len(subset)-len(closed),"distinct_episodes":len({t["episode_id"] for t in subset}),
                    "wins":len(wins),"losses":len(losses),"breakevens":len(net)-len(wins)-len(losses),"win_rate":fraction(len(wins),len(net)),
                    "gross_points":sum(t.get("raw_price_points",0)*t["quantity"] for t in closed) if closed else None,
                    "gross_dollars":sum(t.get("raw_price_dollars",t.get("gross_dollars",0)) for t in closed) if closed else None,
                    "net_points":sum(t.get("net_points",0)*t["quantity"] for t in closed) if closed else None,"net_dollars":sum(net) if closed else None,
                    "cost_dollars":sum(t.get("raw_price_dollars",t.get("gross_dollars",0))-t["net_dollars"] for t in closed) if closed else None,
                    "expectancy_dollars":mean_defined(net),"net_r":sum(t["net_r"] for t in closed if t.get("net_r") is not None) if closed else None,
                    "r_denominator":sum(t.get("net_r") is not None for t in closed),"profit_factor":sum(wins)/-sum(losses) if losses else None,
                    "payoff":mean_defined(wins)/-mean_defined(losses) if wins and losses else None,
                    "mfe_points":mean_defined([t.get("mfe_points") for t in closed]),"mae_points":mean_defined([t.get("mae_points") for t in closed]),
                    "holding_minutes":mean_defined([t.get("holding_minutes") for t in closed]),"closed_drawdown_dollars":dd if closed else None,
                    "annual_drawdown_path":"within-year closed P&L" if y!="all" else "full-history closed P&L","partial_year":y=="2026"})
            for dimension,labels in [("hour",range(24)),("weekday",["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"])]:
                for label in labels:
                    selected=[t for t in role_trades if t[dimension]==label];complete=[t for t in selected if t["status"]=="completed"]
                    timing.append({"policy":p,"mode":m,"leg":role,"anchor":"actual_leg_fill","dimension":dimension,"bucket":label,
                        "fills":len(selected),"completed":len(complete),"net_dollars":sum(t["net_dollars"] for t in complete) if complete else None})
    return rows,paths,timing


def risk_reference(episodes,parents):
    rows=[]
    for p,m in sorted({(r["policy"],r["mode"]) for r in episodes}):
        for y,s,d in dimensions():
            selected=[r for r in episodes if (r["policy"],r["mode"])==(p,m) and belongs(origin(parents[r["episode_id"]]["entry_time"],parents[r["episode_id"]]["direction"]),y,s,d)]
            known=[known_pnl(r) for r in selected if known_pnl(r) is not None]
            peaks=[r.get("peak_notional") for r in selected if r.get("peak_notional") is not None]
            dd=[r.get("max_mtm_drawdown_dollars") for r in selected if r.get("max_mtm_drawdown_dollars") is not None]
            rows.append({"policy":p,"mode":m,"year":y,"session":s,"side":d,"anchor":"original_actual_entry","episodes":len(selected),
                "known_outcomes":len(known),"unknown_outcomes":len(selected)-len(known),"net_dollars":sum(known) if known else None,
                "original_fills":sum(r.get("original_fills",0) for r in selected),"add_fills":sum(r.get("add_fills",0) for r in selected),
                "signals":sum(r.get("signals",0) for r in selected),"add_attempts":sum(r.get("add_attempts",0) for r in selected),
                "support_rejections":sum(str(r.get("action_status","")).startswith("rejected_") for r in selected),
                "unknown_support_abstentions":sum("unknown" in str(r.get("action_status","")) and "abstention" in str(r.get("action_status","")) for r in selected),
                "original_quantity_skips":sum(r.get("action_status")=="original_quantity_skip" for r in selected),
                "add_quantity_skips":sum(r.get("add_quantity_skips",0) for r in selected),"cancellations":sum(r.get("pending_add_cancellations",0) for r in selected),
                "unused_reserve_dollars":sum(r.get("unused_reserve_dollars") or 0 for r in selected),
                "mean_unused_reserve_dollars":mean_defined([r.get("unused_reserve_dollars") for r in selected]),
                "reserve_allocation_denominator":sum(r.get("unused_reserve_dollars") is not None for r in selected),
                "unused_reserve_scope":"sum/mean of daily reserved risk allocations; not an account cash balance or extra capital",
                "peak_notional":(max(peaks) if peaks else 0 if selected and all(r["status"]=="no_fill" for r in selected) else None) if len(known)==len(selected) else None,
                "episode_mtm_drawdown_dollars":(max(dd) if dd else 0 if selected and all(r["status"]=="no_fill" for r in selected) else None) if len(known)==len(selected) else None,
                "observed_prefix_peak_notional":max(peaks) if peaks else None,
                "observed_prefix_episode_mtm_drawdown_dollars":max(dd) if dd else None,
                "unknown_exposure_episodes":sum(known_pnl(r) is None or r.get("peak_notional") is None and r["status"]!="no_fill" for r in selected),
                "planned_risk_overshoot_episodes":sum(bool(r.get("risk_budget_overshoot")) for r in selected),
                "financing_enforced":m in ("full_parent","half_parent","financed_overlay"),"partial_year":y=="2026"})
    return rows


def profile_categories(state,direction):
    if not state.get("known"):return {"availability":"unknown"}
    def bin_(x,edges):
        if x is None:return "unknown"
        if x<edges[0]:return "below_"+str(edges[0])
        for low,high in zip(edges,edges[1:]):
            if x<high:return f"[{low},{high})"
        return ">="+str(edges[-1])
    slopes=[state.get("slope20_3"),state.get("slope50_3")]
    slope="unknown" if None in slopes else "both_aligned" if all(direction*x>0 for x in slopes) else "both_opposed" if all(direction*x<0 for x in slopes) else "mixed_or_flat"
    change=state.get("width_change_3")
    out={"availability":"known","ordering":"neutral" if state["direction"]==0 else "aligned" if state["direction"]==direction else "opposed",
         "price_position":state.get("price_cloud","unknown"),"slopes":slope,
         "width_atr":bin_(state.get("width_atr"),[0,.25,.5,1,2]),"distance_atr":bin_(state.get("favorable_distance_atr"),[0,.5,1,2]),
         "aligned_duration":"left_censored" if state.get("duration_left_censored") else bin_(state.get("aligned_count"),[1,4,13,37]),
         "width_change":"unknown" if change is None else "expanding" if change>0 else "contracting" if change<0 else "equal"}
    for ema in (20,50):
        for label,name in [("H","high"),("L","low"),("M","midpoint")]:
            x=state.get(f"ema{ema}_{name}_confluence")
            out[f"confluence_ema{ema}_{label}"]="yes" if x is True else "no" if x is False else "unknown"
    return out


def profiles_reference(observations,parents,calendar,*,intervals=True):
    memberships=defaultdict(list)
    for r in observations:
        eid=r["episode_id"];d=parents[eid]["direction"];where=origin(r["decision_at"],d)
        for name,group in profile_categories(r["snapshot"],d).items():
            memberships[(r["anchor"],name,group)].append((eid,where))
    roster={"availability":("known","unknown"),"ordering":("aligned","opposed","neutral"),
        "price_position":("above","inside","below"),"slopes":("both_aligned","both_opposed","mixed_or_flat","unknown"),
        "width_atr":("below_0","[0,0.25)","[0.25,0.5)","[0.5,1)","[1,2)",">=2","unknown"),
        "distance_atr":("below_0","[0,0.5)","[0.5,1)","[1,2)",">=2","unknown"),
        "aligned_duration":("below_1","[1,4)","[4,13)","[13,37)",">=37","left_censored","unknown"),
        "width_change":("expanding","contracting","equal","unknown")}
    for ema in (20,50):
        for label in ("H","L","M"):roster[f"confluence_ema{ema}_{label}"]=("yes","no","unknown")
    for anchor in {r["anchor"] for r in observations}:
        for name,buckets in roster.items():
            for bucket in buckets:memberships.setdefault((anchor,name,bucket),[])
    rows=[]
    for (a,name,group),members in sorted(memberships.items()):
        for y,s,d in dimensions():
            selected=[eid for eid,where in members if belongs(where,y,s,d)];ids=sorted(set(selected))
            known=[i for i in ids if parents[i]["status"]=="completed"]
            values=[parents[i]["net_dollars"] for i in known]
            vectors=[(parents[i]["broker_day"],[parents[i].get("net_dollars")]) for i in ids]
            ci=bootstrap_reference(vectors,year_calendar(calendar,y)) if intervals and a in ("original_order_decision","original_entry") else []
            rows.append({"anchor":a,"feature":name,"bucket":group,"year":y,"session":s,"side":d,"observations":len(selected),
                "distinct_episodes":len(ids),"completed_parent_episodes":len(values),"unknown_parent_episodes":len(ids)-len(values),
                "parent_net_dollars":sum(values) if values else None,"mean_parent_net_dollars":mean_defined(values),
                "parent_win_rate":fraction(sum(x>1e-8 for x in values),len(values)),"mean_low":ci[0]["difference_low"] if ci else None,
                "mean_high":ci[0]["difference_high"] if ci else None,"conditional_population":a=="eligible_open_position_landmark","not_calibrated_probability":True})
            for field,source_field in (("mean_parent_mfe_points","mfe_points"),("mean_parent_mae_points","mae_points"),("mean_parent_holding_minutes","holding_minutes")):
                rows[-1][field]=mean_defined([parents[i].get(source_field) for i in known]) if a in {"original_order_decision","original_entry"} else None
    return rows


def contacts_reference(monitoring,parents):
    groups=defaultdict(list)
    for r in monitoring:groups[r["episode_id"]].append(r)
    contacts=[];forwards=[]
    for eid,observations in groups.items():
        observations=sorted(observations,key=lambda r:instant(r["time"]))
        parent=parents[eid];d=parent["direction"]
        for i,row in enumerate(observations):
            if not row["open_position_landmark"]:continue
            for ema in (20,50):
                if not row[f"ema{ema}_contact"]:continue
                level=row[f"ema{ema}_frozen_level"]
                rounding=ROUND_FLOOR if d==1 else ROUND_CEILING
                threshold=float(((Decimal(str(level))/Decimal(".1")).to_integral_value(rounding=rounding)-d)*Decimal(".1"))
                breach=(row["low"]<=threshold if d==1 else row["high"]>=threshold) if row["usable"] else None
                hold=d*(row["close"]-level)>0 if row["usable"] else None
                broken=d*(row["close"]-level)<0 if row["usable"] else None
                observed_at=None;gap=False;previous=instant(row["available_at"])
                if breach is True:
                    for later in observations[i+1:]:
                        if instant(later["time"])!=previous and not later.get("known_closure_before",False):gap=True
                        previous=instant(later["available_at"])
                        if not later["usable"]:gap=True;continue
                        if d*(later["close"]-level)>0:
                            observed_at=later["available_at"];break
                    if observed_at is None and previous<instant(parent["broker_day"]+"T17:00:00Z"):gap=True
                number=row[f"ema{ema}_contact_number"]
                group="unknown" if number is None else "first" if number==1 else "second" if number==2 else "third_or_more"
                observed_delay=(instant(observed_at)-instant(row["available_at"])).total_seconds()/60 if observed_at else None
                recovered=True if observed_at else None if breach and gap else False if breach else None
                item={"episode_id":eid,"broker_day":parent["broker_day"],"event_at":row["available_at"],"contact_open":row["time"],
                    "ema":ema,"frozen_level":level,"breach_level":threshold,"contact_number":number,"contact_group":group,
                    "hold":hold,"tick_breach":breach,"close_break":broken,"reclaimed":recovered,
                    "reclaim_at":observed_at if not gap else None,"recovery_minutes":observed_delay if not gap else None,
                    "first_observed_reclaim_at":observed_at,"observed_recovery_minutes":observed_delay,
                    "recovery_time_known":bool(observed_at and not gap),"recovery_delay_lower":0. if observed_at and gap else observed_delay,
                    "recovery_delay_upper":observed_delay,"parent_liquidation_net_unit":row["parent_liquidation_net_unit"],"parent_status":"open",
                    "cloud_flip":row["prior"]["alignment"]>=0 and row["current"]["alignment"]<0 if row["prior"].get("known") and row["current"].get("known") else None,
                    **{f"confluence_{label}":row["prior"].get(f"ema{ema}_{name}_confluence") for label,name in (("H","high"),("L","low"),("M","midpoint"))},
                    "anchor":"EMA_decision_event","source_monitoring_time":row["time"],**origin(row["available_at"],d)}
                contacts.append(item)
                after={instant(r["time"]):r for r in observations[i+1:]};start=instant(row["available_at"]);price=row["close"]
                for horizon in (5,15,30,60):
                    wanted=[after.get(start+timedelta(minutes=k)) for k in range(0,horizon,5)]
                    valid=all(r is not None and r["usable"] and r["contract"]==row["contract"] for r in wanted)
                    values={"signed_points":None,"mfe_points":None,"mae_points":None}
                    if valid:
                        values={"signed_points":d*(wanted[-1]["close"]-price),
                                "mfe_points":max([0.]+[d*((r["high"] if d==1 else r["low"])-price) for r in wanted]),
                                "mae_points":max([0.]+[-d*((r["low"] if d==1 else r["high"])-price) for r in wanted])}
                    forwards.append({"episode_id":eid,"broker_day":parent["broker_day"],"event_at":row["available_at"],"ema":ema,
                        "contact_group":group,"horizon_minutes":horizon,"status":"observed" if valid else "censored",
                        "source_candle_excluded":True,"not_trade_return":True,"anchor":"EMA_decision_event",**origin(row["available_at"],d),**values})
    return contacts,forwards


def contact_cohorts_reference(records,monitoring):
    output=[]
    for ema in (20,50):
        for group in ("all","first","second","third_or_more","unknown"):
            for y,s,d in dimensions():
                selected=[r for r in records if r["ema"]==ema and (group=="all" or r["contact_group"]==group) and belongs(r,y,s,d)]
                support=[r for r in monitoring if r["open_position_landmark"] and belongs(origin(r["available_at"],r["direction"]),y,s,d)]
                for event in ("hold","tick_breach","close_break","reclaimed","cloud_flip"):
                    rows=[r for r in selected if r["tick_breach"] is True] if event=="reclaimed" else selected
                    yes=sum(r[event] is True for r in rows);no=sum(r[event] is False for r in rows);unknown=len(rows)-yes-no
                    output.append({"ema":ema,"contact_group":group,"event":event,"year":y,"session":s,"side":d,"anchor":"EMA_decision_event",
                        "contacts":len(rows),"distinct_episodes":len({r["episode_id"] for r in rows}),"known_events":yes,"known_none":no,
                        "unknown":unknown,"known_denominator":yes+no,"rate":fraction(yes,yes+no),"lower_bound":fraction(yes,len(rows)),
                        "upper_bound":fraction(yes+unknown,len(rows)),"eligible_open_landmarks":len(support),"eligible_open_episodes":len({r["episode_id"] for r in support}),
                        "mean_recovery_minutes":mean_defined([r["recovery_minutes"] for r in rows]),"recovery_timing_denominator":sum(r["recovery_time_known"] for r in rows),
                        "observed_recovery_timing_unknown":sum(r["reclaimed"] is True and not r["recovery_time_known"] for r in rows),"conditional_population":True})
    return output


def confluence_cohorts_reference(records):
    """Contact-close support conditioned on the prior frozen EMA/range level."""
    output=[]
    for ema in (20,50):
        for level in ("H","L","M"):
            for flag in ("yes","no","unknown"):
                rows=[r for r in records if r["ema"]==ema and ("yes" if r.get("confluence_"+level) is True else "no" if r.get("confluence_"+level) is False else "unknown")==flag]
                for y,s,d in dimensions():
                    cohort=[r for r in rows if belongs(r,y,s,d)]
                    for event in ("hold","tick_breach","close_break","reclaimed","cloud_flip"):
                        selected=[r for r in cohort if r["tick_breach"] is True] if event=="reclaimed" else cohort
                        true=sum(r.get(event) is True for r in selected);false=sum(r.get(event) is False for r in selected);unknown=len(selected)-true-false
                        output.append(dict(ema=ema,level=level,confluence_state=flag,event=event,year=y,session=s,side=d,
                            anchor="EMA_decision_event",contacts=len(selected),distinct_episodes=len({r["episode_id"] for r in selected}),
                            known_events=true,known_none=false,unknown=unknown,known_denominator=true+false,rate=fraction(true,true+false),
                            lower_bound=fraction(true,len(selected)),upper_bound=fraction(true+unknown,len(selected)),conditional_population=True))
    return output


def period_reference(episodes,parents,calendar):
    output=[];sensitivities=[]
    for name,years in [("development",[2018,2019,2020]),("validation",[2021,2022,2023]),("later",[2024,2025]),("replication",[2026])]:
        subset={i:t for i,t in parents.items() if int(origin(t["entry_time"],t["direction"])["year"]) in years}
        if not subset:continue
        rows=[r for r in episodes if r["episode_id"] in subset]
        dates=[d for d in calendar if f"{min(years)}-01-01"<=d<=f"{max(years)+1}-01-01"]
        paired,effects,common=paired_reference(rows,subset,dates,cohorts=[("all",s,d) for s in ("all",*SESSIONS) for d in SIDES])
        output.extend({**r,"period":name,"year":name} for r in paired)
        for d in SIDES:
            ids=[i for i,t in subset.items() if d=="combined" or origin(t["entry_time"],t["direction"])["side"]==d]
            vectors=[(subset[i]["broker_day"],effects[i] if common[i] else [None]*6) for i in ids]
            for weeks in (1,4,8):
                cis=bootstrap_reference(vectors,dates,weeks=weeks)
                for index,p in enumerate(CORE):
                    values=[effects[i][index] for i in ids if common[i]]
                    sensitivities.append({"policy":p,"period":name,"side":d,"block_weeks":weeks,"episodes":len(ids),"complete_pairs":len(values),
                        "mean_difference":mean_defined(values),**(cis[index] if cis else dict.fromkeys(["difference_low","difference_high","adjusted_low","adjusted_high"])),
                        "adjusted_confidence":1-.05/6,"anchor":"original_actual_entry"})
    return output,sensitivities


def selection_reference(paired,episodes,trades,parents):
    candidates=[]
    for policy in CORE:
        validation=next((r for r in paired if r["policy"]==policy and r["year"]=="validation" and r["session"]=="all" and r["side"]=="combined"),None)
        mode="financed_overlay" if policy.startswith("A") else "standardized"
        filled=[t for t in trades if t["policy"]==policy and t["mode"]==mode and t["status"]=="completed"
            and origin(parents[t["episode_id"]]["entry_time"],parents[t["episode_id"]]["direction"])["year"] in {"2021","2022","2023"}]
        ids={t["episode_id"] for t in filled};years=sorted({origin(parents[i]["entry_time"],parents[i]["direction"])["year"] for i in ids})
        adds=[t for t in filled if t.get("leg")=="add"]
        addyears=sorted({origin(parents[t["episode_id"]]["entry_time"],parents[t["episode_id"]]["direction"])["year"] for t in adds})
        qualified=bool(validation and validation["mean_difference"] is not None and validation["mean_difference"]>0
            and validation["adjusted_low"] is not None and validation["adjusted_low"]>0 and len(filled)>=100 and len(years)>=2
            and (not policy.startswith("A") or len(adds)>=100 and len(addyears)>=2))
        candidates.append({"policy":policy,"validation_complete_pairs":validation["complete_pairs"] if validation else 0,
            "mean_difference":validation["mean_difference"] if validation else None,"adjusted_low":validation["adjusted_low"] if validation else None,
            "completed_trades":len(filled),"validation_years_with_fills":years,"financed_add_fills":len(adds),
            "validation_years_with_financed_adds":addyears,"qualifies":qualified})
    def choose(order):
        eligible=[r for r in candidates if r["policy"] in order and r["qualifies"]]
        eligible.sort(key=lambda r:(-r["mean_difference"],order.index(r["policy"])))
        return eligible[0]["policy"] if eligible else None
    return {"candidates":candidates,"selected_gate":choose(["G1","G2"]),"selected_exit":choose(["X1","X2"]),
        "selected_adds":[r["policy"] for r in candidates if r["policy"] in {"A20","A50"} and r["qualifies"]],
        "combined_policy":None,"later_outcomes_opened":False,"prior_exposure":True}


def exposure_controls_reference(episodes,parents):
    indexed={(r["policy"],r["mode"],r["episode_id"]):r for r in episodes};rows=[]
    for policy in ("A20","A50"):
        alternatives={eid:known_pnl(indexed[(policy,"diagnostic_1plus1",eid)]) for eid in parents}
        controls={name:{eid:known_pnl(indexed[("BASE",name,eid)]) for eid in parents} for name in ("parent_1","parent_2")}
        common={eid:alternatives[eid] is not None and all(controls[name][eid] is not None for name in controls) for eid in parents}
        for name in ("parent_1","parent_2"):
            for y,s,d in dimensions():
                ids=[eid for eid,p in parents.items() if belongs(origin(p["entry_time"],p["direction"]),y,s,d)]
                complete=[eid for eid in ids if common[eid]];individual=[eid for eid in ids if alternatives[eid] is not None and controls[name][eid] is not None]
                differences=[alternatives[i]-controls[name][i] for i in complete]
                rows.append(dict(policy=policy,mode="diagnostic_1plus1",control="BASE:"+name,year=y,session=s,side=d,anchor="original_actual_entry",episodes=len(ids),
                    complete_pairs=len(complete),missing_pairs=len(ids)-len(complete),individual_pairs=len(individual),
                    alternative_net_dollars=sum(alternatives[i] for i in complete) if complete else None,control_net_dollars=sum(controls[name][i] for i in complete) if complete else None,
                    total_difference=sum(differences) if differences else None,mean_difference=mean_defined(differences),
                    individual_mean_difference=mean_defined([alternatives[i]-controls[name][i] for i in individual]),larger_exposure=True,not_equal_risk=True))
    rank={values:i for i,values in enumerate(dimensions())}
    return sorted(rows,key=lambda r:(r["policy"],rank[(r["year"],r["session"],r["side"])],r["control"]))


def forward_cohorts_reference(records):
    output=[]
    for ema in (20,50):
        for horizon in (5,15,30,60):
            for group in ("all","first","second","third_or_more","unknown"):
                for y,s,d in dimensions():
                    rows=[r for r in records if r["ema"]==ema and r["horizon_minutes"]==horizon and (group=="all" or r["contact_group"]==group) and belongs(r,y,s,d)]
                    known=[r for r in rows if r["status"]=="observed"]
                    output.append({"ema":ema,"horizon_minutes":horizon,"contact_group":group,"year":y,"session":s,"side":d,"anchor":"EMA_decision_event",
                        "events":len(rows),"observed":len(known),"censored":len(rows)-len(known),"distinct_episodes":len({r["episode_id"] for r in rows}),
                        "mean_signed_points":mean_defined([r["signed_points"] for r in known]),"mean_mfe_points":mean_defined([r["mfe_points"] for r in known]),
                        "mean_mae_points":mean_defined([r["mae_points"] for r in known]),"not_trade_return":True})
    return output


def transitions_reference(events,trades,parents):
    kinds={"first_contact_consumed","ema_exit_signal","trail_future_activation","trail_already_breached_next_open_exit"}
    selected=[r for r in events if r.get("event") in kinds];adds={(t["episode_id"],t["policy"],t["mode"]):t for t in trades if t.get("leg")=="add"}
    rows=[]
    for p,m in sorted({(r["policy"],r["mode"]) for r in selected}):
        group=[r for r in selected if (r["policy"],r["mode"])==(p,m)]
        for y in YEARS:
            for d in SIDES:
                for first in SESSIONS:
                    for event_session in SESSIONS:
                        matches=[r for r in group if (y=="all" or origin(r["time"],parents[r["episode_id"]]["direction"])["year"]==y)
                            and (d=="combined" or origin(r["time"],parents[r["episode_id"]]["direction"])["side"]==d)
                            and origin(parents[r["episode_id"]]["entry_time"],1)["session"]==first and origin(r["time"],1)["session"]==event_session]
                        for session in (*SESSIONS,"unfilled"):
                            hits=[r for r in matches if (origin(adds[(r["episode_id"],p,m)]["entry_time"],1)["session"] if (r["episode_id"],p,m) in adds else "unfilled")==session]
                            rows.append({"policy":p,"mode":m,"year":y,"side":d,"anchor":"EMA_event_year","original_session":first,
                                "event_session":event_session,"add_session":session,"events":len(hits),"distinct_episodes":len({r["episode_id"] for r in hits}),
                                "add_fills":sum((r["episode_id"],p,m) in adds for r in hits)})
    return rows


def exits_reference(episodes,parents):
    output=[]
    for p in ("X1","X2","T50"):
        for y,s,d in dimensions():
            rows=[r for r in episodes if r["policy"]==p and r["mode"]=="standardized" and belongs(origin(parents[r["episode_id"]]["entry_time"],parents[r["episode_id"]]["direction"]),y,s,d)]
            pairs=[r for r in rows if known_pnl(r) is not None and parents[r["episode_id"]].get("net_dollars") is not None]
            delta=lambda r:known_pnl(r)-parents[r["episode_id"]]["net_dollars"]
            losers=[r for r in pairs if parents[r["episode_id"]]["net_dollars"]<-1e-8];winners=[r for r in pairs if parents[r["episode_id"]]["net_dollars"]>1e-8]
            output.append({"policy":p,"year":y,"session":s,"side":d,"anchor":"original_actual_entry","episodes":len(rows),"complete_pairs":len(pairs),
                "missing_pairs":len(rows)-len(pairs),"parent_losers":len(losers),"losses_reduced":sum(delta(r)>1e-8 for r in losers),
                "losses_worsened":sum(delta(r)<-1e-8 for r in losers),"loss_dollars_saved":sum(max(0,delta(r)) for r in losers),
                "parent_winners":len(winners),"winners_cut_short":sum(delta(r)<-1e-8 for r in winners),"profit_surrendered_dollars":sum(max(0,-delta(r)) for r in winners),
                "improved":sum(delta(r)>1e-8 for r in pairs),"deteriorated":sum(delta(r)<-1e-8 for r in pairs),"mean_difference":mean_defined([delta(r) for r in pairs]),
                "mean_time_saved_minutes":mean_defined([r.get("time_saved_minutes") for r in pairs]),"mean_post_exit_favorable_points":mean_defined([r.get("post_exit_favorable_points") for r in pairs])})
    return output


def exposure_history_reference(exposure,parents):
    groups=defaultdict(lambda:defaultdict(list))
    for r in exposure:groups[(r["policy"],r["mode"])][r["episode_id"]].append(r)
    output=[]
    for (p,m),episodes in groups.items():
        closed=peak=0.
        for eid,rows in sorted(episodes.items(),key=lambda x:instant(parents[x[0]]["entry_time"])):
            rows=sorted(rows,key=lambda r:instant(r["time"]))
            for row in rows:
                low=closed+row["intraminute_mtm_min"];high=closed+row["intraminute_mtm_max"]
                worst=max(peak-low,row.get("max_mtm_drawdown",0));peak=max(peak,high);mtm=closed+row["mtm_net_dollars"]
                output.append({"policy":p,"mode":m,"episode_id":eid,"time":row["time"],"history_mtm_net_dollars":mtm,
                    "history_mtm_drawdown_dollars":max(worst,peak-mtm),"notional":row["notional"],"concurrent_legs":row["concurrent_legs"],
                    "combined_active_stop_risk":row["combined_active_stop_risk"]})
            if rows and rows[-1].get("active_quantity",0):break
            if rows:closed+=rows[-1]["closed_net_dollars"]
    return output


POLICY_MODES=(("BASE","parent_1"),("BASE","parent_2"),("BASE","full_parent"),("BASE","half_parent"),
    ("G1","standardized"),("G2","standardized"),("A20","financed_overlay"),("A50","financed_overlay"),
    ("A20","diagnostic_1plus1"),("A50","diagnostic_1plus1"),("X1","standardized"),("X2","standardized"),("T50","standardized"))
SCENARIO_COSTS={"primary-one-tick":dict(commission_per_side=2.5,slippage_ticks=1,ordering="source_ohlc"),
    "gross-zero-cost":dict(commission_per_side=0.,slippage_ticks=0,ordering="source_ohlc"),
    "net-zero-ticks":dict(commission_per_side=2.5,slippage_ticks=0,ordering="source_ohlc"),
    "net-two-ticks":dict(commission_per_side=2.5,slippage_ticks=2,ordering="source_ohlc"),
    "high-first-one-tick":dict(commission_per_side=2.5,slippage_ticks=1,ordering="high_first"),
    "low-first-one-tick":dict(commission_per_side=2.5,slippage_ticks=1,ordering="low_first")}
FINANCED={"full_parent","half_parent","financed_overlay"}


def scale_parent_reference(parent,quantity):
    row=dict(parent);ratio=quantity/parent.get("quantity",1)
    for name in ("gross_dollars","raw_price_dollars","commission_dollars","net_dollars","risk_initial_dollars","risk_effective_dollars","source_risk_dollars"):
        if row.get(name) is not None:row[name]*=ratio
    row.update(quantity=quantity,leg="original")
    return row


def exit_tradeoff_reference(day,trade,config=None):
    cfg=economics(config);parent=day.parent
    result={"time_saved_minutes":None,"time_saved_minutes_lower":None,"time_saved_minutes_upper":None,
        "post_exit_favorable_points":None,"post_exit_trace_status":"not_comparable"}
    if not trade or parent["status"]!="completed" or trade["status"]!="completed":return result
    start,end=instant(trade["exit_time"]),instant(parent["exit_time"])
    a=instant(trade.get("exit_time_latest")) or start;b=instant(parent.get("exit_time_latest")) or end
    result.update(time_saved_minutes=(end-start).total_seconds()/60,time_saved_minutes_lower=(end-a).total_seconds()/60,
                  time_saved_minutes_upper=(b-start).total_seconds()/60)
    if start>end:result["post_exit_trace_status"]="policy_exit_after_parent";return result
    if start==end and trade.get("exit_price_raw")==parent.get("exit_price_raw"):
        result.update(post_exit_favorable_points=0.,post_exit_trace_status="same_exit");return result
    prices={instant(value(m,"timestamp")):m for m in day.minutes};points=[];t=start
    def split(path,raw,after):
        for i,(x,y) in enumerate(zip(path,path[1:])):
            if day.direction*(y-x)<0 and min(x,y)<=raw<=max(x,y):return [raw]+path[i+1:] if after else path[:i+1]+[raw]
        raise VerificationError("exit diagnostic saved stop absent on authored path")
    while t<=end:
        m=prices.get(t)
        if m is None:
            if day.expected_minute(t):result["post_exit_trace_status"]="missing_expected_minute";return result
            t+=ONE;continue
        if value(m,"contract")!=day.contract:result["post_exit_trace_status"]="contract_transition";return result
        path=authored_path(m,cfg["ordering"])
        if t==start and trade.get("exit_time_precision")=="within_bar":path=split(path,trade["exit_price_raw"],True)
        if t==end:path=split(path,parent["exit_price_raw"],False) if parent.get("exit_time_precision")=="within_bar" else [value(m,"open")]
        points.extend(path);t+=ONE
    result.update(post_exit_favorable_points=max([0.,*[day.direction*(p-trade["exit_price_raw"]) for p in points]]),post_exit_trace_status="known_authored_path")
    return result


def verify_saved_execution(saved,day,config=None,*,equity_start=_UNSET,terminal_only=False):
    """Reconstruct source decisions and execution; compare all scientific fields."""
    cfg=economics(config);ep=saved["episode"];policy,mode=ep["policy"],ep["mode"];n=0
    observed_planned=[]
    for leg in saved["trades"]:
        anchor=day.high if day.direction==1 else day.low
        if leg.get("leg")=="add":
            order=next((r for r in saved["orders"] if r["event"]=="contingent_add" and r["time"]==leg.get("signal_available_at")),None)
            if order is None:raise VerificationError("observed add lacks its known frozen signal risk anchor")
            anchor=order["signal_close"]
        planned=day.direction*(anchor-leg["initial_stop"])*cfg["point_value"]*leg["quantity"]
        risk=risk_distance(leg["entry_price"],leg["initial_stop"],day.direction,cfg["tick_size"])
        stoploss=((risk+cfg["slippage_ticks"]*cfg["tick_size"])*cfg["point_value"]+2*cfg["commission_per_side"])*leg["quantity"] if risk>0 else (2*cfg["slippage_ticks"]*cfg["tick_size"]*cfg["point_value"]+2*cfg["commission_per_side"])*leg["quantity"]
        n+=compare(leg,dict(planned_stop_risk_dollars=planned,protective_initial_risk_valid=risk>0,actual_initial_stop_loss_with_costs=stoploss),"all_leg_raw_risk_metadata")
        if leg.get("leg")=="original":
            n+=compare(ep,dict(original_planned_stop_risk_dollars=planned,original_actual_initial_stop_loss_with_costs=stoploss),"original_raw_risk_metadata")
        observed_planned.append(planned)
    planned_total=sum(observed_planned) if saved["trades"] else 0. if ep["status"]=="no_fill" else None
    n+=compare(ep,dict(combined_planned_stop_risk_dollars=planned_total,
        combined_planned_stop_risk_complete=not bool(ep.get("unknown_add_fill")) and ep["status"] in {"completed","no_fill"}),"observed_combined_raw_risk")
    monitoring=reference_monitoring(day,cfg)
    n+=compare(ep.get("unknown_feature_count"),sum(not r["current"]["known"] for r in monitoring),"unknown_feature_count")
    n+=compare(ep.get("original_order_snapshot"),snapshot_row(day.cloud.snapshot(instant(day.parent["order_submitted_at"]),day.contract),day.direction,day),"original_order_snapshot")
    n+=compare(ep.get("entry_snapshot"),snapshot_row(day.cloud.snapshot(instant(day.parent["entry_time"]),day.contract),day.direction,day),"entry_snapshot")
    if policy in {"G1","G2"}:
        expected,orders=reference_gate(day,policy)
        n+=compare(ep,expected,"gate_episode")+compare(saved["orders"],orders,"gate_orders")
        if expected.get("original_filled") is not True:
            n+=compare(saved["trades"],[],"gate_no_trades")+compare(saved["exposure"],[],"gate_no_exposure")
            return n
        ref,trades,signals,actions,exposure=reference_execution(day,"BASE",cfg,mode="parent_1")
        trades=[scale_parent_reference(day.parent,1)]
    else:
        ref,trades,signals,actions,exposure=reference_execution(day,policy,cfg,mode=mode,equity_start=equity_start)
        if mode in FINANCED and equity_start is None:
            return n+compare(ep,ref,"unknown_capital")+compare(saved["trades"],[],"unknown_capital_trades")+compare(saved["exposure"],[],"unknown_capital_exposure")
        if ref.get("original_quantity")==0:
            n+=compare(ep,ref,"quantity_skip")+compare(saved["trades"],[],"quantity_skip_trades")+compare(saved["exposure"],[],"quantity_skip_exposure")
            n+=compare(ep.get("ending_equity"),cfg["initial_capital"] if equity_start is _UNSET else equity_start,"quantity_skip_equity")
            eq=cfg["initial_capital"] if equity_start is _UNSET else equity_start
            n+=compare(ep.get("original_budget"),size_reference(eq,.5 if mode in {"half_parent","financed_overlay"} else 1.,day.high if day.direction==1 else day.low,day.parent["initial_stop"],day.direction,cfg),"quantity_skip_budget")
            n+=compare(ep.get("unused_reserve_dollars"),eq*cfg["risk_percent"]/200 if mode=="financed_overlay" else None,"quantity_skip_reserve")
            return n
        if policy=="BASE":
            q=ref["original_quantity"];trades=[scale_parent_reference(day.parent,q)]
            ref.update(status=day.parent["status"],action_status="unchanged_parent_control",net_dollars=trades[0].get("net_dollars"),source_parent_parity=True)
            # Cached control branches retain identical source rows and trace.
            for name in ("signals","known_completed_net_dollars","add_attempts","add_opportunity","add_filled"):
                if name not in ep:ref.pop(name,None)
            if "financial_eligible_landmarks" not in ep:ref.pop("financial_eligible_landmarks",None)
            # A scaled precomputed unchanged trace need not repeat control
            # execution events; source parent and all trace values remain exact.
            if not saved["events"]:actions=[]
        n+=compare(ep,ref,"execution_episode")
        orders=[dict(event="contingent_add",**r) for r in signals] if policy.startswith("A") else []
        n+=compare(saved["orders"],orders,"management_orders")
    # Parent field preservation is stronger than summary agreement.
    if len(saved["trades"])!=len(trades):raise VerificationError("actual leg fill roster differs from independent replay")
    for i,(actual,expected) in enumerate(zip(saved["trades"],trades)):
        n+=compare(actual,expected,f"trade[{i}]")
        if policy!="BASE" and policy not in {"G1","G2"}:
            n+=compare(actual,cohort(expected["entry_time"]),f"trade[{i}].cohort")
            n+=compare(actual.get("slippage_ticks"),cfg["slippage_ticks"],"cost_ticks")
            n+=compare(actual.get("commission_per_side"),cfg["commission_per_side"],"fee_side")
            entry_stop_risk=risk_distance(actual["entry_price"],actual["initial_stop"],day.direction,cfg["tick_size"])
            n+=compare(actual.get("risk_initial_points"),entry_stop_risk if entry_stop_risk>0 else None,"actual_stop_risk_points")
            raw_anchor=day.high if day.direction==1 else day.low
            if actual["leg"]=="add":raw_anchor=next(r["signal_close"] for r in signals if r["time"]==actual.get("signal_available_at"))
            planned=day.direction*(raw_anchor-actual["initial_stop"])*cfg["point_value"]*actual["quantity"]
            hypothetical=max(0,entry_stop_risk)*cfg["point_value"]*actual["quantity"]+cfg["tick_size"]*cfg["slippage_ticks"]*cfg["point_value"]*actual["quantity"]+2*cfg["commission_per_side"]*actual["quantity"]
            if entry_stop_risk<=0:hypothetical=(2*cfg["tick_size"]*cfg["slippage_ticks"]*cfg["point_value"]+2*cfg["commission_per_side"])*actual["quantity"]
            n+=compare(actual.get("planned_stop_risk_dollars"),planned,"planned_raw_risk")
            n+=compare(actual.get("actual_initial_stop_loss_with_costs"),hypothetical,"cost_gap_stop_loss")
            if "protective_initial_risk_valid" in actual:n+=compare(actual["protective_initial_risk_valid"],entry_stop_risk>0,"protective_initial_risk_valid")
    if terminal_only:
        if exposure and (len(saved["exposure"])!=1 or saved["exposure"][0].get("trace_retention")!="terminal_only"):
            raise VerificationError("secondary trace must explicitly retain one terminal row")
        n+=compare(saved["exposure"],[exposure[-1]] if exposure else [],"terminal_exposure")
    else:n+=compare(saved["exposure"],exposure,"full_exposure")
    original=next((t for t in trades if t.get("leg")=="original"),None)
    n+=compare(ep,exit_tradeoff_reference(day,original,cfg),"exit_tradeoff")
    # Every consequential event is reconstructed; auxiliary preservation
    # events are checked separately through the trace/decision evidence.
    consequential={"fill","exit","censor","first_contact_consumed","departure_armed","stop_reset","pending_add_cancel", "unknown_support_prefix","unknown_pending_add","unknown_pending_add_at_endpoint",
        "failure_confirmation_reset_unknown","failure_first_close","cross_confirmation_reset_unknown","trail_no_action_unknown","trail_preserves_tighter_stop","trail_future_activation"}
    expected_actions=list(actions)
    if policy in {"X1","X2"}:expected_actions += [dict(event="ema_exit_signal",policy=policy,**r) for r in signals]
    if policy=="T50":expected_actions += [dict(event="trail_already_breached_next_open_exit",**r) for r in signals]
    target_events=consequential|{"ema_exit_signal","trail_already_breached_next_open_exit"}
    if policy in {"G1","G2"}:expected_actions=[]
    if policy not in {"G1","G2"}:
        actual=[r for r in saved["events"] if r["event"] in target_events]
        # Events at the same completed close are independently normalized by
        # causal event name, preserving their time and all reconstructed data.
        actual=sorted(actual,key=lambda r:(instant(r["time"]),r["event"],r.get("leg","")))
        expected_actions=sorted(expected_actions,key=lambda r:(instant(r["time"]),r["event"],r.get("leg","")))
        n+=compare(actual,expected_actions,"causal_events")
    if mode in FINANCED:
        eq=cfg["initial_capital"] if equity_start is _UNSET else equity_start
        expected_eq=eq+ep["net_dollars"] if ep["net_dollars"] is not None else None
        n+=compare(ep.get("ending_equity"),expected_eq,"causal_ending_equity")
        n+=compare(ep.get("original_budget"),size_reference(eq,.5 if mode in {"half_parent","financed_overlay"} else 1.,day.high if day.direction==1 else day.low,day.parent["initial_stop"],day.direction,cfg),"raw_risk_budget")
        reserve=max(0,eq*cfg["risk_percent"]/200-sum(day.direction*((next(r["signal_close"] for r in signals if r["time"]==t.get("signal_available_at")))-t["initial_stop"])*cfg["point_value"]*t["quantity"] for t in saved["trades"] if t.get("leg")=="add")) if mode=="financed_overlay" else None
        n+=compare(ep.get("unused_reserve_dollars"),reserve,"fixed_unused_reserve")
        q=original["quantity"];budget=eq*cfg["risk_percent"]*.01*(.5 if mode in {"half_parent","financed_overlay"} else 1.)
        planned=day.direction*((day.high if day.direction==1 else day.low)-original["initial_stop"])*cfg["point_value"]*q
        actual=(risk_distance(original["entry_price"],original["initial_stop"],day.direction,cfg["tick_size"])+cfg["tick_size"]*cfg["slippage_ticks"])*cfg["point_value"]*q+2*cfg["commission_per_side"]*q
        n+=compare(ep,dict(original_planned_stop_risk_dollars=planned,original_actual_initial_stop_loss_with_costs=actual,original_risk_budget_overshoot_dollars=max(0,actual-budget)),"original_budget_overshoot")
        overshoot=actual>budget+1e-8 or any((t.get("risk_budget_overshoot_dollars") or 0)>1e-8 for t in saved["trades"])
        n+=compare(ep.get("risk_budget_overshoot"),overshoot,"risk_budget_overshoot_flag")
    return n


def synthetic_day(data):
    from phase3_inputs import CloudBar,CloudTimeline
    clouds=[]
    for row in data["cloud_bars"]:
        row=dict(row)
        for k in ("timestamp","available_at"):row[k]=instant(row[k])
        clouds.append(CloudBar(**row))
    timeline=CloudTimeline(clouds,[instant(t) for t in data.get("expected_slots",data.get("cloud_expected",[]))])
    minutes=[]
    for row in data["minutes"]:
        row=dict(row)
        for k in ("timestamp","available_at"):row[k]=instant(row[k])
        minutes.append(OracleMinute(**row))
    expected=set(instant(t) for t in data.get("expected_minutes",[]))
    return OracleDay(data["episode_id"],data["broker_day"],data["parent"],minutes,timeline,[instant(t) for t in data["update_times"]],
        data["range_high"],data["range_low"],instant(data["cutoff"]),lambda t:t in expected if "expected_minutes" in data else True)


def floating_reference(exposure,parents,episodes):
    """Stream independent cohort histories, including unknowns without marks."""
    indexed={(r["policy"],r["mode"],r["episode_id"]):r for r in episodes}
    origins={i:origin(p["entry_time"],p["direction"]) for i,p in parents.items()}
    first_unknown={};states={}
    def keys(p,m,eid):
        a=origins[eid]
        return [(p,m,y,s,d) for y in ("all",a["year"]) for s in ("all",a["session"]) for d in ("combined",a["side"])]
    for (p,m,eid),row in indexed.items():
        if known_pnl(row) is None:
            for k in keys(p,m,eid):first_unknown[k]=min(instant(parents[eid]["entry_time"]),first_unknown.get(k,instant(parents[eid]["entry_time"])))
    for r in exposure:
        p,m,eid=r["policy"],r["mode"],r["episode_id"]
        for k in keys(p,m,eid):
            state=states.setdefault(k,dict(eid=None,total=0.,peak=0.,dd=0.,rows=0,notional=0.,stop=0.,concurrent=0,last=None,blocked=False))
            if k in first_unknown and instant(parents[eid]["entry_time"])>first_unknown[k]:state["blocked"]=True
            if eid!=state["eid"]:
                if state["eid"] is not None:
                    amount=known_pnl(indexed[(p,m,state["eid"])])
                    if amount is None:state["blocked"]=True
                    else:state["total"]+=amount
                state["eid"]=eid
            state["last"]=r
            if state["blocked"]:continue
            low=state["total"]+r["intraminute_mtm_min"];high=state["total"]+r["intraminute_mtm_max"]
            afterpeak=max(state["peak"],high)
            state["dd"]=max(state["dd"],state["peak"]-low,r["max_mtm_drawdown"],afterpeak-state["total"]-r["mtm_net_dollars"])
            state["peak"]=afterpeak;state["rows"]+=1
            state["notional"]=max(state["notional"],r["notional"])
            state["stop"]=max(state["stop"],r["combined_active_stop_risk"])
            state["concurrent"]=max(state["concurrent"],r["concurrent_legs"])
    output=[]
    for p,m in sorted({(r["policy"],r["mode"]) for r in episodes}):
        for y,s,d in dimensions():
            rows=[r for r in episodes if (r["policy"],r["mode"])==(p,m) and belongs(origins[r["episode_id"]],y,s,d)]
            unknown=sum(known_pnl(r) is None for r in rows);state=states.get((p,m,y,s,d))
            observed=state["dd"] if state else 0. if rows and all(r["status"]=="no_fill" for r in rows) else None
            output.append({"policy":p,"mode":m,"year":y,"session":s,"side":d,"anchor":"original_actual_entry","episodes":len(rows),
                "unknown_episode_equity":unknown,"observed_mtm_rows":state["rows"] if state else 0,
                "mtm_drawdown_dollars":observed if not unknown else None,"observed_prefix_mtm_drawdown_dollars":observed,"full_path_known":bool(rows and not unknown),
                "peak_notional":state["notional"] if state else 0. if rows and not unknown else None,
                "peak_active_stop_risk":state["stop"] if state else 0. if rows and not unknown else None,
                "peak_concurrent_legs":state["concurrent"] if state else 0 if rows and not unknown else None,"within_year_path":y!="all"})
    return output


def history_stream_reference(exposure,parents,episodes):
    outcomes={(r["policy"],r["mode"],r["episode_id"]):known_pnl(r) for r in episodes};first_unknown={};states={}
    for (p,m,eid),amount in outcomes.items():
        if amount is None:first_unknown[(p,m)]=min(instant(parents[eid]["entry_time"]),first_unknown.get((p,m),instant(parents[eid]["entry_time"])))
    for r in exposure:
        p,m,eid=r["policy"],r["mode"],r["episode_id"];k=(p,m)
        state=states.setdefault(k,dict(eid=None,last=None,total=0.,peak=0.,blocked=False,entry=None))
        date=instant(parents[eid]["entry_time"])
        if k in first_unknown and date>first_unknown[k]:state["blocked"]=True
        if eid!=state["eid"]:
            if state["entry"] and date<state["entry"]:raise VerificationError("exposure episodes not chronological")
            if state["last"] is not None:
                if state["last"]["active_quantity"] or outcomes[(p,m,state["eid"])] is None:state["blocked"]=True
                else:state["total"]+=state["last"]["closed_net_dollars"]
            state.update(eid=eid,entry=date)
        state["last"]=r
        if state["blocked"]:continue
        mtm=state["total"]+r["mtm_net_dollars"];low=state["total"]+r["intraminute_mtm_min"]
        worst=max(state["peak"]-low,r["max_mtm_drawdown"]);state["peak"]=max(state["peak"],state["total"]+r["intraminute_mtm_max"])
        yield {"policy":p,"mode":m,"episode_id":eid,"time":r["time"],"history_mtm_net_dollars":mtm,
            "history_mtm_drawdown_dollars":max(worst,state["peak"]-mtm),"notional":r["notional"],"concurrent_legs":r["concurrent_legs"],"combined_active_stop_risk":r["combined_active_stop_risk"]}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()


def read_json(path):return json.loads(Path(path).read_text())


def pin(path,base=None):
    path=Path(path)
    return {"path":str(path.relative_to(base)) if base else str(path),"bytes":path.stat().st_size,"sha256":digest(path)}


def verify_pin(base,record,key="path"):
    p=Path(base)/record[key]
    if not p.is_file() or p.is_symlink():raise VerificationError("pinned ordinary file missing: "+str(p))
    if digest(p)!=record["sha256"] or "bytes" in record and p.stat().st_size!=record["bytes"]:raise VerificationError("pinned byte identity changed: "+str(p))
    return p


def ledger(path):
    with gzip.open(path,"rt") as f:
        for number,line in enumerate(f,1):
            row=json.loads(line)
            if not isinstance(row,dict):raise VerificationError(f"{path}:{number}: non-object ledger row")
            yield row


def compare_stream(saved,expected,path):
    count=rows=0;sentinel=object()
    for i,(a,b) in enumerate(itertools.zip_longest(saved,expected,fillvalue=sentinel)):
        if a is sentinel or b is sentinel:raise VerificationError(f"{path}: row count differs at {i}")
        count+=compare(a,b,f"{path}[{i}]");rows+=1
    return count,rows


def compare_csv(path,expected):
    """Check each declared header and every saved cell, including null support."""
    with Path(path).open(newline="") as f:
        reader=csv.DictReader(f);columns=reader.fieldnames
        if not columns or len(columns)!=len(set(columns)):raise VerificationError("CSV header missing/duplicate: "+str(path))
        count=0;rows=0;sentinel=object()
        for i,(saved,want) in enumerate(itertools.zip_longest(reader,expected,fillvalue=sentinel)):
            if saved is sentinel or want is sentinel:raise VerificationError("CSV roster differs: "+str(path))
            if set(columns)!=set(want):raise VerificationError(f"{path}: scientific column roster differs {set(columns)^set(want)}")
            for k in columns:
                value_=want[k];s=saved[k]
                if value_ is None:actual=None if s=="" else s
                elif isinstance(value_,bool):actual=True if s=="True" else False if s=="False" else s
                elif isinstance(value_,int):
                    try:actual=int(s)
                    except ValueError:actual=s
                elif isinstance(value_,float):
                    try:actual=float(s)
                    except ValueError:actual=s
                else:actual=s
                count+=compare(actual,value_,f"{path}[{i}].{k}")
            rows+=1
    return count,rows


def verify_freeze(stage,root):
    f=read_json(stage/"execution-freeze.json")
    if f.get("phase3_policy_outcomes_opened") is not False or f["run_id"]!=stage.name:raise VerificationError("pre-outcome runtime freeze identity absent")
    for name,k in (("config.json","settings_sha256"),("protocol.md","protocol_sha256"),("inputs.lock.json","inputs_sha256"),("input-audit.json","input_audit_sha256"),("uv.lock","environment_lock_sha256")):
        verify_pin(stage,{"path":name,"sha256":f[k]})
    for r in f["source_files"]:verify_pin(stage,r)
    for r in f["source_files"]:
        if r.get("workspace_path"):verify_pin(Path(__file__).parent,{"path":r["workspace_path"],"sha256":r["sha256"]})
        if r.get("workspace_root_path"):verify_pin(root,{"path":r["workspace_root_path"],"sha256":r["sha256"]})
    own=next((r for r in f["source_files"] if r.get("workspace_path")=="phase3_verify.py"),None)
    if own is None or digest(__file__)!=own["sha256"]:raise VerificationError("executing independent verifier was not frozen before policy outcomes")
    lock=read_json(stage/"inputs.lock.json");audit=read_json(stage/"input-audit.json");cfg=read_json(stage/"config.json")
    from phase3_inputs import PHASE1_RUN,PHASE1_SHA,PHASE2_RUN,PHASE2_SHA
    compare(lock["primary_parent"],dict(run_id=PHASE1_RUN,manifest_sha256=PHASE1_SHA),"phase1_parent")
    compare(cfg["phase2_context"],dict(selected_policy=None,replication_parent=None),"phase2_no_trading_parent")
    if audit.get("result")!="passed":raise VerificationError("independent original input audit did not pass")
    for run,sha in ((PHASE1_RUN,PHASE1_SHA),(PHASE2_RUN,PHASE2_SHA)):
        base=root/"runs/23_gc_overnight_breakout_15m"/run;verify_pin(base,{"path":"manifest.json","sha256":sha})
    for r in lock["parent_external"]:verify_pin(root,r,"locator")
    verify_pin(root,lock["parent_roster"])
    for r in lock.get("phase2_context_pins",[]):verify_pin(root,r)
    feature=cfg["feature_release"];verify_pin(root,{"path":feature["manifest"],"sha256":feature["manifest_sha256"]})
    fm=read_json(root/feature["manifest"])
    # The adapter itself rehashes the selected physical feature file via the
    # public loader; settings preserve the exact selected GC 5m identity.
    compare(cfg["core_policies"],list(CORE),"six_core_family")
    compare(cfg["primary_parent"],dict(run_id=PHASE1_RUN,manifest_sha256=PHASE1_SHA,protocol_version="1.0.0",scenario="primary-one-tick",ordering="source_ohlc",quantity="one_contract"),"primary_native_convention")
    compare(cfg["feature_release"],dict(manifest_sha256="444043918c9b30a0d909e88328094b52936f6b379ce288b85afb6740aed0f838",selected_gc_5m_sha256="72baba948e357a89f0f68c76d9fa66b579193b89ab5aff7defce980103e834d8",timeframe_minutes=5,ema_lengths=[20,50],warmup_usable_observations=250,equal_emas="neutral",optional_source_touch_threshold_inherited=False),"exact_cloud_semantics")
    compare(cfg["uncertainty"],dict(replications=10000,seed=230015,block_weeks=4,sensitivity_block_weeks=[1,8],
        pointwise_confidence=.95,six_core_marginal_confidence=1-.05/6),"declared_resampling")
    compare(cfg["accounts"],dict(capital_dollars=10000,start_of_day_equity_total_risk_fraction=.01,parent_reserved_fraction=.5,
        add_reserved_fraction=.5,max_leverage=10,margin_fraction=.05,minimum_quantity=1,quantity_step=1,spent_risk_replenished=False),"actual_whole_GC_financing")
    return f,lock,cfg,fm


def load_oracle_material(stage,root,lock,featuremanifest):
    """Allowed immutable input adapter, independent consumer/context assembly."""
    from phase3_inputs import load_parent_frames,load_cloud,CloudTimeline,cloud_bars,expected_cloud_slots,parent_order_update_times
    frames=load_parent_frames(root);primary={r["trade_id"]:dict(r,episode_id=r["trade_id"]) for r in frames["primary-one-tick-trades"]}
    cloud=load_cloud(root);slots=expected_cloud_slots(featuremanifest["coverage_start_session"],featuremanifest["coverage_end_completion"])
    timeline=CloudTimeline(cloud_bars(cloud),[t.to_pydatetime() for t in slots.timestamp],coverage_end=instant(featuremanifest["coverage_end_completion"]))
    del cloud,slots
    used={r["broker_day"] for r in primary.values()};broker=timezone(timedelta(hours=3))
    df=frames["audit-minutes"];selected=df.loc[df.scheduled & df.source_valid]
    byday=defaultdict(list)
    for t,o,h,l,c,contract,at in selected[["timestamp","open","high","low","close","contract","available_at"]].itertuples(index=False,name=None):
        when=t.to_pydatetime();day=when.astimezone(broker).date().isoformat()
        if day in used:byday[day].append(OracleMinute(when,float(o),float(h),float(l),float(c),str(contract),at.to_pydatetime()))
    expected=set((frames["audit-expected-minutes"].timestamp.astype("int64")//10**9).tolist())
    expected_minute=lambda t:int(instant(t).timestamp()) in expected
    by15={}
    bars15=frames["audit-bars-15m"]
    days15=bars15.timestamp.dt.tz_convert(broker).dt.date.astype(str)
    for day in used:by15[day]=bars15.loc[days15==day]
    roster=[]
    with (root/lock["parent_roster"]["path"]).open(newline="") as f:
        for row in csv.DictReader(f):
            for k in ("eligible","valid_range","no_trade","unknown_outcome"):row[k]=row[k].lower()=="true"
            for k in ("accepted_breakouts","executable_fills","completed_trades","censored_trades","quantity_skips","expected_range_minutes","observed_range_minutes","later_missing_trading_minutes"):row[k]=int(row[k])
            roster.append(row)
    contexts={};saved_parent_ledgers={}
    for scenario in SCENARIO_COSTS:
        groups={}
        for kind in ("trades","days","orders","events"):
            record=next(r for r in lock["parent_external"] if r["id"]==scenario+"-"+kind)
            groups[kind]=list(ledger(root/record["locator"]))
        saved_parent_ledgers[scenario]=groups
        tradebyday={r["broker_day"]:r for r in groups["trades"]};rangebyday={r["broker_day"]:r for r in groups["days"]}
        out={}
        for eid,original in primary.items():
            day=original["broker_day"];parent=tradebyday.get(day);range_=rangebyday[day];cutoff=instant(day+"T17:00:00Z")
            if parent:
                parent=dict(parent,episode_id=eid,phase1_saved_trade_id=parent["trade_id"],**SCENARIO_COSTS[scenario])
                updates=parent_order_update_times(by15[day],first_submission=instant(parent["order_submitted_at"]),shadow_event_time=instant(parent["entry_time"]),cutoff=cutoff,contract=parent["contract"])
                shadow="accepted"
            else:updates=();shadow="unknown" if range_.get("unknown_outcome") else "no_event"
            out[eid]=OracleDay(eid,day,parent,byday.get(day,()),timeline,updates,float(range_["range_high"]),float(range_["range_low"]),cutoff,expected_minute,shadow)
        contexts[scenario]=out
    p2=[]
    for record in lock.get("phase2_context_pins",[]):
        for i,r in enumerate(ledger(root/record["path"])):
            if r["episode_id"] not in primary or r.get("occurred") is not True:continue
            if record["kind"]=="boundary-events" and r["horizon"]!="remaining_broker_window":continue
            if record["kind"]=="level-opportunities" and r["fraction"]!=.5:continue
            when=r.get("first_available_at") or r.get("first_observed_available_at")
            if when is None:continue
            p=primary[r["episode_id"]]
            kind="midpoint_"+r["event"] if record["kind"]=="level-opportunities" else "protected_"+("low" if p["direction"]==1 else "high")+"_"+r["event"]
            p2.append(dict(episode_id=r["episode_id"],event_kind=kind,decision_at=when,event_first_time=r.get("first_time"),event_first_time_latest=r.get("first_time_latest"),
                event_time_precision=r.get("time_precision"),event_ordering_ambiguous=r.get("ordering_ambiguous",False),baseline_position_status=r.get("baseline_position_status_at_event"),
                saved_level=r.get("raw_level"),anchor="phase2_saved_event_context_"+kind,source_artifact=record["path"],source_sha256=record["sha256"],source_row=i,phase2_replication_parent=None))
    return dict(parents=primary,contexts=contexts,roster=roster,phase2_context=p2,parent_ledgers=saved_parent_ledgers)


class GroupCursor:
    """Bounded consecutive episode arrays; absent groups cannot hide extras."""
    def __init__(self,rows,key):
        self.groups=iter(itertools.groupby(rows,key));self.next_=next(self.groups,None)
    def take(self,wanted):
        if self.next_ is None or self.next_[0]!=wanted:return []
        rows=list(self.next_[1]);self.next_=next(self.groups,None);return rows
    def exhausted(self):
        if self.next_ is not None:raise VerificationError("unconsumed/duplicate/out-of-order ledger group: "+str(self.next_[0]))


def tag_key(row):return row["scenario"],row["episode_id"],row["policy"],row["mode"]


def verify_phase(stage,phase,material,freeze,*,equities=None):
    folder=stage/"phases"/phase;completion=read_json(folder/"completion.json")
    if completion["phase"]!=phase or instant(completion["started_at"])<instant(freeze["at"]):raise VerificationError("phase predates frozen source/settings")
    compare(completion,dict(settings_sha256=freeze["settings_sha256"],execution_freeze_sha256=digest(stage/"execution-freeze.json"),all_accepted_roster_retained=True),"phase_frozen_binding")
    start=read_json(stage/"phase-starts"/(phase+".json"))
    compare(start,dict(phase=phase,started_at=completion["started_at"],run_id=stage.name,execution_freeze_sha256=digest(stage/"execution-freeze.json"),settings_sha256=freeze["settings_sha256"]),"phase_start_frozen_binding")
    compare(completion["policy_modes"],[dict(policy=p,mode=m) for p,m in POLICY_MODES],"policy_mode_roster")
    compare(completion["scenarios"],list(SCENARIO_COSTS),"matched_parent_scenarios")
    for record in completion["artifacts"]:verify_pin(stage,record)
    years={2018,2019,2020,2021,2022,2023} if phase=="dev-validation" else {2024,2025,2026}
    parents={i:r for i,r in material["parents"].items() if int(origin(r["entry_time"],r["direction"])["year"]) in years}
    ids=sorted(parents,key=lambda i:(instant(parents[i]["entry_time"]),i))
    compare(completion["accepted_episodes"],len(ids),"accepted_fixed_roster")
    episodes=list(ledger(folder/"episodes.jsonl.gz"));wantkeys=[(s,i,p,m) for s in SCENARIO_COSTS for i in ids for p,m in POLICY_MODES]
    if [tag_key(r) for r in episodes]!=wantkeys:raise VerificationError("policy/scenario ledger lost/reordered fixed episode roster")
    cursors={name:GroupCursor(ledger(folder/(name+".jsonl.gz")),tag_key) for name in ("events","orders","trades","exposure")}
    monitor=GroupCursor(ledger(folder/"monitoring.jsonl.gz"),lambda r:(r["scenario"],r["episode_id"]))
    profiles=list(ledger(folder/"profiles.jsonl.gz"));p2context=list(ledger(folder/"phase2-context.jsonl.gz"))
    expected_profiles=[];expected_p2=[];comparisons=0;counts=defaultdict(int);states=dict(equities or {});trades_all=[];events_all=[];primary_monitor=[]
    last=None
    for index,ep in enumerate(episodes):
        scenario,eid,p,m=tag_key(ep);day=material["contexts"][scenario][eid];key=(scenario,eid)
        if key!=last:
            savedmonitor=monitor.take(key)
            if day.parent:
                expected=reference_monitoring(day,SCENARIO_COSTS[scenario])
                retained=bool(savedmonitor) or scenario=="primary-one-tick"
                if retained:comparisons+=compare(savedmonitor,expected,"monitoring:"+str(key))
                if scenario=="primary-one-tick":
                    primary_monitor.extend(savedmonitor)
                    for anchor,when in (("original_order_decision",day.parent["order_submitted_at"]),("original_entry",day.parent["entry_time"])):
                        expected_profiles.append(dict(episode_id=eid,broker_day=day.broker_day,scenario=scenario,anchor=anchor,decision_at=when,
                            snapshot=snapshot_row(day.cloud.snapshot(instant(when),day.contract),day.direction,day)))
                    expected_profiles.extend(dict(episode_id=eid,broker_day=day.broker_day,scenario=scenario,anchor="eligible_open_position_landmark",decision_at=r["available_at"],snapshot=r["current"]) for r in expected if r["open_position_landmark"])
                    for r in material["phase2_context"]:
                        if r["episode_id"]==eid:expected_p2.append(dict(r,broker_day=day.broker_day,scenario=scenario,
                            snapshot=snapshot_row(day.cloud.snapshot(instant(r["decision_at"]),day.contract),day.direction,day)))
            elif savedmonitor:raise VerificationError("no-parent scenario fabricated monitoring")
            last=key
        arrays={name:cursor.take(tag_key(ep)) for name,cursor in cursors.items()}
        saved=dict(episode=ep,**arrays)
        if day.parent is None:
            comparisons+=compare(ep,dict(status="no_fill" if day.shadow_status=="no_event" else "unknown",net_dollars=0. if day.shadow_status=="no_event" else None,
                action_status="no_parent_event" if day.shadow_status=="no_event" else "unknown_parent_first_event",original_fills=0,add_fills=0),"absent_matched_parent")
            if any(arrays.values()):raise VerificationError("absent-parent scenario fabricated execution")
        else:
            eq=states.get((scenario,p,m),DEFAULT_ECONOMICS["initial_capital"])
            terminal=scenario!="primary-one-tick" and arrays["exposure"] and arrays["exposure"][0].get("trace_retention")=="terminal_only"
            comparisons+=verify_saved_execution(saved,day,SCENARIO_COSTS[scenario],equity_start=eq,terminal_only=bool(terminal))
        if m in FINANCED:
            eq=states.get((scenario,p,m),DEFAULT_ECONOMICS["initial_capital"])
            states[(scenario,p,m)]=ep.get("ending_equity",eq if ep["status"]=="no_fill" and ep.get("net_dollars")==0 else None)
        for name,rows in arrays.items():
            counts[name]+=len(rows)
            for row in rows:
                comparisons+=compare(row,dict(episode_id=eid,broker_day=day.broker_day,scenario=scenario,policy=p,mode=m),"ledger_tags")
                if name=="events":comparisons+=compare(row["kind"],row["event"],"event_alias")
        trades_all.extend(arrays["trades"]);events_all.extend(arrays["events"])
        if (index+1)%500==0:print(f"independent {phase}: {index+1}/{len(episodes)} episode policies; {comparisons} fields",flush=True)
    for cursor in cursors.values():cursor.exhausted()
    monitor.exhausted()
    comparisons+=compare(completion["account_end_states"],[dict(scenario=s,policy=p,mode=m,equity=eq) for (s,p,m),eq in sorted(states.items())],"independent_actual_account_end_states")
    comparisons+=compare(profiles,expected_profiles,"profile_raw_roster")+compare(p2context,expected_p2,"frozen_phase2_context")
    counts.update(episodes=len(episodes),profiles=len(profiles),**{"phase2-context":len(p2context)})
    # Physical row counts independently stream again, including intentionally
    # omitted secondary monitor/exposure arrays declared by completion.
    for name in completion["row_counts"]:
        actual=sum(1 for _ in ledger(folder/(name+".jsonl.gz")))
        comparisons+=compare(actual,completion["row_counts"][name],"completion_row_count:"+name)
    return dict(comparisons=comparisons,episodes=episodes,trades=trades_all,events=events_all,monitoring=primary_monitor,
        profiles=profiles+ p2context,parents=parents,equities=states,phase=phase)


def verify_tables(stage,phase,results,material):
    parents={i:r for result in results for i,r in result["parents"].items()}
    all_episodes=[r for result in results for r in result["episodes"]]
    primary=lambda rows:[r for r in rows if r.get("scenario")=="primary-one-tick"]
    episodes=primary(all_episodes);trades=primary([r for result in results for r in result["trades"]])
    events=primary([r for result in results for r in result["events"]])
    monitoring=[r for result in results for r in result["monitoring"]];profiles=[r for result in results for r in result["profiles"]]
    calendar=[r["broker_day"] for r in material["roster"]]
    paired,_,_=paired_reference(episodes,parents,calendar)
    periods,sensitivities=period_reference(episodes,parents,calendar)
    cohorts,equity,timing=trade_cohorts_reference(trades,episodes)
    contacts,forward=contacts_reference(monitoring,parents)
    tables=dict(paired=paired,periods=periods,**{"interval-sensitivities":sensitivities,"trade-cohorts":cohorts,"equity":equity,"timing":timing,
        "risk":risk_reference(episodes,parents),"profiles":profiles_reference(profiles,parents,calendar),"contacts":contact_cohorts_reference(contacts,monitoring),
        "confluence":confluence_cohorts_reference(contacts),
        "exposure-controls":exposure_controls_reference(episodes,parents),
        "forward":forward_cohorts_reference(forward),"transitions":transitions_reference(events,trades,parents),"exit-tradeoffs":exits_reference(episodes,parents)})
    scenarios=[]
    for scenario in sorted(SCENARIO_COSTS):
        selected=[dict(r,scenario="primary-one-tick") for r in all_episodes if r["scenario"]==scenario]
        rows,_,_=paired_reference(selected,parents,calendar,intervals=False)
        scenarios.extend(dict(r,scenario=scenario) for r in rows if r["year"]=="all" and r["session"]=="all")
    tables["scenarios"]=scenarios
    columns=("known","expected_slot","available_at","reason","ema20","ema50","atr14","close","slope20_3","slope50_3","aligned_count","alignment_start_known","duration_left_censored","width_points","width_atr","favorable_distance_atr","width_change_3","price_cloud")
    tables["decision-snapshots"]=[dict(episode_id=r["episode_id"],anchor=r["anchor"],decision_at=r["decision_at"],
        **origin(r["decision_at"],parents[r["episode_id"]]["direction"]),**{k:r["snapshot"].get(k) for k in columns}) for r in profiles]
    phases=("dev-validation","later") if phase=="all" else (phase,)
    def exposure():
        for name in phases:
            yield from (r for r in ledger(stage/"phases"/name/"exposure.jsonl.gz") if r["scenario"]=="primary-one-tick")
    tables["floating"]=floating_reference(exposure(),parents,episodes)
    tablebase=stage/"tables" if phase=="all" else stage/"phases"/phase/"tables"
    completion=read_json(tablebase/"completion.json");counts={name:len(rows) for name,rows in tables.items()}
    comparisons=compare(completion["tables"],counts,"saved_table_row_inventory")
    compare(completion,dict(phase=phase,episodes=len(parents),all_accepted_roster_retained=True,interval_replications=10000,seed=230015),"metrics_method_metadata")
    for name,rows in tables.items():
        if rows:
            print(f"independent saved {name}: {len(rows)} rows",flush=True)
            n,_=compare_csv(tablebase/(name+".csv"),rows);comparisons+=n
        elif (tablebase/(name+".csv")).exists():raise VerificationError("zero supported table has unexplained rows: "+name)
    diagnostic=stage/"diagnostics" if phase=="all" else stage/"phases"/phase/"diagnostics"
    diagnostic_counts={}
    for name,expected in (("contacts",contacts),("forward",forward),("exposure-path",history_stream_reference(exposure(),parents,episodes))):
        n,count=compare_stream(ledger(diagnostic/(name+".jsonl.gz")),iter(expected),"diagnostic:"+name);comparisons+=n;diagnostic_counts[name]=count
    if phase=="dev-validation":
        comparisons+=compare(read_json(stage/"selection-candidate.json"),selection_reference([*paired,*periods],episodes,trades,parents),"chronological_selection_candidate")
    return dict(comparisons=comparisons,table_rows=counts,diagnostic_rows=diagnostic_counts)


def verify_chronology(stage,freeze,phase):
    if phase=="dev-validation":
        if (stage/"phases/later").exists() or (stage/"selection.json").exists():raise VerificationError("development verification attempted after selection/later opened")
        return
    record=read_json(stage/"selection-freeze.json");verify_pin(stage,{"path":"selection.json","sha256":record["selection_sha256"]})
    devreceipt=verify_pin(stage,record["development_validation_receipt"])
    dev=read_json(devreceipt)
    if dev.get("status")!="passed" or dev.get("phase")!="dev-validation":raise VerificationError("later assessment lacks independent prior development pass")
    if dev["execution_freeze_sha256"]!=digest(stage/"execution-freeze.json") or record.get("later_outcomes_opened") is not False:raise VerificationError("selection before later source binding differs")
    development=read_json(stage/"phases/dev-validation/completion.json");later=read_json(stage/"phases/later/completion.json")
    if not (instant(development["finished_at"])<=instant(dev["verified_at"])<=instant(record["frozen_at"])<=instant(later["started_at"])):
        raise VerificationError("development/pass/selection/later chronology violated")
    for name in ("dev-validation","later"):
        start=read_json(stage/"phase-starts"/(name+".json"));end=read_json(stage/"phases"/name/"completion.json")
        compare(start,dict(phase=name,run_id=stage.name,execution_freeze_sha256=digest(stage/"execution-freeze.json"),started_at=end["started_at"]),"actual_phase_start")
        if name=="later":compare(start["selection"],dict(path="selection.json",sha256=digest(stage/"selection.json"),freeze_sha256=digest(stage/"selection-freeze.json"),verification_sha256=digest(devreceipt)),"later_selection_pin")


def write_new(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x") as f:f.write(json.dumps(data,indent=2,allow_nan=False)+"\n")


def verify_stage(stage,phase,attempt,*,root=None):
    stage=Path(stage).resolve();root=Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    destination=stage/"verification"/attempt
    destination.mkdir(parents=True,exist_ok=False)
    source=destination/"source";source.mkdir()
    for p in [Path(__file__),Path(__file__).parent/"tests/test_phase3_verify.py"]:
        shutil.copyfile(p,source/p.name)
    receipt=dict(schema_version="study23.phase3-independent-science/v1",run_id=stage.name,phase=phase,status="failed",
        argv=sys.argv,cwd=str(Path.cwd()),started_at=stamp(datetime.now(UTC)),producer_imports=False,
        allowed_adapter="phase3_inputs.py; independently audited immutable source/features only",scope="Independent causal replay, matched unchanged parent controls, all raw ledgers and all saved scientific table cells; no native TradingView/feed/tick parity certification")
    try:
        freeze,lock,cfg,feature=verify_freeze(stage,root);verify_chronology(stage,freeze,phase)
        material=load_oracle_material(stage,root,lock,feature)
        n,_=compare_stream(ledger(stage/"parents/baseline-trades.jsonl.gz"),iter(material["parents"].values()),"immutable_original_parents")
        n,_=compare_stream(ledger(stage/"parents/calendar-roster.jsonl.gz"),iter(material["roster"]),"immutable_calendar_roster")
        eligible=[r for r in material["roster"] if r["eligible"]]
        n2,_=compare_stream(ledger(stage/"parents/eligible-roster.jsonl.gz"),iter(eligible),"immutable_eligible_roster");n+=n2
        n+=compare(read_json(stage/"exclusions.json"),dict(all_calendar_days=len(material["roster"]),causally_eligible_days=len(eligible),accepted_original_episodes=len(material["parents"]),
            unknown_first_event_days=[r["broker_day"] for r in eligible if r["unknown_outcome"]],known_no_trade_days=[r["broker_day"] for r in eligible if r["no_trade"]],exclusions=[r for r in material["roster"] if not r["eligible"]]),"original_fixed_exclusions")
        names=("dev-validation","later") if phase=="all" else (phase,)
        results=[];equities=None
        if phase=="later":
            equities={}
            for r in ledger(stage/"phases/dev-validation/episodes.jsonl.gz"):
                if r["mode"] in FINANCED:equities[(r["scenario"],r["policy"],r["mode"])]=r.get("ending_equity")
        for name in names:
            result=verify_phase(stage,name,material,freeze,equities=equities);results.append(result);equities=result["equities"];n+=result["comparisons"]
        table_result=verify_tables(stage,phase,results,material) if phase in {"dev-validation","all"} else dict(comparisons=0,table_rows={},diagnostic_rows={})
        n+=table_result["comparisons"]
        artifacts=[]
        for name in ("config.json","protocol.md","inputs.lock.json","input-audit.json","execution-freeze.json","uv.lock","exclusions.json","parents/baseline-trades.jsonl.gz","parents/calendar-roster.jsonl.gz","parents/eligible-roster.jsonl.gz","selection-candidate.json","selection.json","selection-freeze.json","execution-completion.json"):
            if (stage/name).is_file():artifacts.append(pin(stage/name,stage))
        for name in names:
            artifacts.extend(pin(p,stage) for p in sorted((stage/"phases"/name).rglob("*")) if p.is_file())
        for folder in (stage/"tables",stage/"diagnostics",stage/"phase-starts"):
            if folder.is_dir():artifacts.extend(pin(p,stage) for p in sorted(folder.rglob("*")) if p.is_file())
        sources=[pin(p,stage) for p in sorted(source.iterdir())]
        receipt.update(status="passed",strict_field_comparisons=n,execution_freeze_sha256=digest(stage/"execution-freeze.json"),
            original_accepted_episodes=len(material["parents"]),verified_accepted_episodes=len({r["episode_id"] for result in results for r in result["episodes"]}),
            policy_modes=[dict(policy=p,mode=m) for p,m in POLICY_MODES],scenarios=list(SCENARIO_COSTS),
            table_rows=table_result["table_rows"],diagnostic_rows=table_result["diagnostic_rows"],artifacts=artifacts,source_snapshots=sources,
            checker_sha256=digest(__file__),qualifications=["2026 is partial inherited coverage","Native platform/cancellation/data-feed latency and tick ordering remain unverified",
                "Secondary sensitivity full paths independently replayed; saved traces may explicitly retain terminal-only rows","Prior Phase1/2 exposure means chronological assessment is not a pristine holdout",
                "Unknown execution/capital/event support stays null; known declared abstentions are numeric zero","Post-breach recovery after parent exit is price context, not an executable recovery trade"])
    except Exception as error:
        receipt.update(error_type=type(error).__name__,error=str(error),checker_sha256=digest(__file__),source_snapshots=[pin(p,stage) for p in sorted(source.iterdir())])
        receipt["verified_at"]=stamp(datetime.now(UTC));write_new(destination/"receipt.json",receipt)
        raise
    receipt["verified_at"]=stamp(datetime.now(UTC));write_new(destination/"receipt.json",receipt)
    print(json.dumps({k:receipt[k] for k in ("status","phase","strict_field_comparisons","table_rows","diagnostic_rows")}),flush=True)
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--stage",required=True);p.add_argument("--phase",choices=("dev-validation","later","all"),required=True)
    p.add_argument("--attempt",required=True);args=p.parse_args()
    if not args.attempt or Path(args.attempt).name!=args.attempt:raise VerificationError("single fresh attempt name required")
    verify_stage(args.stage,args.phase,args.attempt)


if __name__=="__main__":main()
