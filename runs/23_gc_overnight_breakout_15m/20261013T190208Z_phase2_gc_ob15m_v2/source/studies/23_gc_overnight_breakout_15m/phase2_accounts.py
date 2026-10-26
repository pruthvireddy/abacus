"""Actual whole-contract Phase 2 accounts on the conditional episode roster.

Each policy/mode is a separate chronological account. The frozen production
settings are deliberately distinct from standardized one-contract outcomes.
Risk allocations use start-of-day realized equity and never replenish; capacity
uses currently known realized equity and concurrent exposure at signal close.
No input loading, policy selection or historical execution occurs on import.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import math
from statistics import mean
from typing import Any, Iterable, Mapping

from src.engine import entry_cohort, iso
from src.phase2_engine import (EPS, EpisodeContext, Phase2Config, baseline_state,
    bucket, execute_signal, find_signal, instant, percentage_stop, policy_specs)

MODES=("original_only","replacement_only","same_direction_concurrent_add_on",
       "post_exit_reentry","post_realized_loss_recovery","flat_only_opposite_reversal")
SIDES=("combined","upper-first","lower-first")
SESSIONS=("all","Asia","London","New York","Outside")
SESSION_LABELS={"asia":"Asia","london":"London","new_york":"New York","outside_named_sessions":"Outside"}


@dataclass(frozen=True)
class AccountConfig:
    initial_capital: float = 10000.0
    daily_equity_risk_percent: float = 1.0
    maximum_leverage: float = 10.0
    margin_percent: float = 5.0
    minimum_quantity: int = 1
    quantity_step: int = 1

    def __post_init__(self):
        if not all(math.isfinite(x) and x>0 for x in (self.initial_capital,self.daily_equity_risk_percent,self.maximum_leverage,self.margin_percent)):
            raise ValueError("finite positive account settings required")
        if self.minimum_quantity!=1 or self.quantity_step!=1 or type(self.minimum_quantity) is not int or type(self.quantity_step) is not int:
            raise ValueError("GC executable minimum/step must remain whole contract one")


def budget_quantity(day_equity: float | None, reference: float, stop: float, *, fraction: float,
                    capacity_equity: float | None=None, active_notional: float=0.0,
                    active_margin: float=0.0, account: AccountConfig | None=None,
                    economics: Phase2Config | None=None) -> dict[str,Any]:
    """Frozen nominal-risk size; favorable fills never create extra budget."""
    a=account or AccountConfig(); c=economics or Phase2Config()
    capacity_equity=day_equity if capacity_equity is None else capacity_equity
    if fraction not in {.5,1.}:
        raise ValueError("only frozen full and half allocations")
    if day_equity is None or capacity_equity is None:
        return {"quantity":None,"risk_budget_dollars":None,"risk_quantity":None,"leverage_quantity":None,
                "margin_quantity":None,"planned_risk_dollars":None,"reason":"account_equity_unknown"}
    if not all(math.isfinite(x) for x in (day_equity,capacity_equity,reference,stop,active_notional,active_margin)):
        raise ValueError("finite account capacity inputs required")
    risk=abs(reference-stop)*c.point_value
    budget=max(day_equity,0)*a.daily_equity_risk_percent/100*fraction
    notional=reference*c.point_value
    margin=notional*a.margin_percent/100
    if min(day_equity,capacity_equity,reference,risk)<=0:
        return {"quantity":0,"risk_budget_dollars":budget,"risk_quantity":0,"leverage_quantity":0,
                "margin_quantity":0,"planned_risk_dollars":0.,"reason":"nonpositive_equity_price_or_risk"}
    risk_q=math.floor(budget/risk+1e-9)
    leverage_q=math.floor(max(0,capacity_equity*a.maximum_leverage-active_notional)/notional+1e-9)
    margin_q=math.floor(max(0,capacity_equity-active_margin)/margin+1e-9)
    q=max(0,min(risk_q,leverage_q,margin_q))
    reason=None if q else "risk_budget_below_one_contract" if risk_q==0 else "leverage_capacity_below_one_contract" if leverage_q==0 else "margin_capacity_below_one_contract"
    return {"quantity":q,"risk_budget_dollars":budget,"risk_quantity":risk_q,"leverage_quantity":leverage_q,
            "margin_quantity":margin_q,"planned_risk_dollars":q*risk,"reason":reason}


def financial_recovery(original_net: float | None,later_net: float | None,*,loss_known: bool,
                       actually_executed: bool) -> dict[str,Any] | None:
    if not loss_known or not actually_executed or original_net is None or later_net is None or original_net>=-EPS:
        return None
    combined=original_net+later_net
    category=("full_recovery" if combined>=-EPS else "partial_recovery" if later_net>EPS
              else "further_loss" if later_net< -EPS else "no_improvement")
    return {"category":category,"combined_net_dollars":combined,"recovery_dollars":later_net,
            "loss_recovered_dollars":min(max(later_net,0.),-original_net),
            "unrecovered_loss_dollars":max(-combined,0.)}


def _scaled_original(unit: Mapping[str,Any],quantity: int) -> dict[str,Any] | None:
    if quantity<=0:
        return None
    prior=float(unit.get("quantity",1))
    if prior<=0 or not math.isfinite(prior):
        raise ValueError("saved standardized baseline quantity must be positive")
    factor=quantity/prior
    trade=deepcopy(dict(unit))
    trade.update(quantity=quantity,source_standardized_quantity=prior,actual_account_execution=True)
    for key,value in list(trade.items()):
        if key.endswith("_dollars") and value is not None:
            trade[key]=float(value)*factor
    return trade


def _policies(selection: Mapping[str,Any] | str | None):
    chosen=selection if isinstance(selection,str) else selection.get("selected_policy") if selection else None
    specs=policy_specs()
    primary=[p for p in specs if p.kind=="reclaim" and p.name==chosen]
    if chosen is not None and not primary:
        raise ValueError("selection must name one frozen primary or null")
    return primary+[p for p in specs if p.kind.startswith("protected_")]


def _account_original_state(ctx: EpisodeContext,trade: Mapping[str,Any] | None,at: datetime):
    if trade is None:
        return {"position":"flat","loss_known":False,"realized_net_dollars":0.,"exit_known_at":None}
    state=baseline_state(ctx.episode,at)
    flat=state["baseline_position_status"]=="flat"
    return {"position":state["baseline_position_status"],
            "loss_known":flat and trade.get("net_dollars") is not None and trade["net_dollars"]< -EPS,
            "realized_net_dollars":trade.get("net_dollars") if flat else None,
            "exit_known_at":state["baseline_exit_known_at"]}


def _eligible(mode: str,original: Mapping[str,Any] | None,state: Mapping[str,Any],same_direction: bool):
    if mode=="replacement_only":return True,None
    if state["position"]=="unknown":return None,"original_position_unknown_at_first_signal"
    if mode=="same_direction_concurrent_add_on":
        return (True,None) if original is not None and state["position"]=="open" and same_direction else (False,"first_signal_not_same_direction_concurrent_original")
    if mode=="post_exit_reentry":
        return (True,None) if original is not None and state["position"]=="flat" and same_direction else (False,"first_signal_not_same_direction_post_exit")
    if mode=="post_realized_loss_recovery":
        return (True,None) if original is not None and state["position"]=="flat" and state["loss_known"] else (False,"actual_original_net_loss_not_realized_and_known_at_first_signal")
    if mode=="flat_only_opposite_reversal":
        return (True,None) if state["position"]=="flat" and not same_direction else (False,"first_signal_not_flat_opposite_reversal")
    raise ValueError("unknown account mode")


def _known_total(original,later,*,uncertain: bool):
    if uncertain:return None
    trades=[trade for trade in (original,later) if trade is not None]
    if any(t.get("status")!="completed" or t.get("net_dollars") is None for t in trades):return None
    return sum(float(t["net_dollars"]) for t in trades)


def _account_path(contexts,baseline,policy,mode,a,c):
    equity=a.initial_capital
    daily_starts={}
    ledgers=[]
    for ctx in contexts:
        e=ctx.episode; unit=baseline[e.episode_id]
        day_equity=daily_starts.setdefault(e.broker_day,equity)
        cohort=entry_cohort(e.entry_time)
        row={"episode_id":e.episode_id,"broker_day":e.broker_day,"policy":policy.name if policy else "baseline",
             "mode":mode,"year":cohort["entry_year"],"session":SESSION_LABELS[cohort["entry_session"]],
             "side":"upper-first" if e.direction==1 else "lower-first","contract":e.contract,
             "original_entry_time":iso(e.entry_time),"population":"conditional_phase1_accepted_episode",
             "cohort_anchor":"original_breakout_fill",
             "day_start_equity":day_equity,"equity_before_episode":equity,
             "standardized_baseline_net_dollars":unit.get("net_dollars"),
             "original_quantity":0,"second_quantity":0,"original_filled":False,"second_filled":False,
             "signal":False,"opportunity":False,"eligible_signal":False,"eligible_loss":False,
             "quantity_skips":0,"original_quantity_skipped":False,"second_quantity_skipped":False,
             "original_trade":None,"second_trade":None,"second_result":None,"completed_pair":False,
             "recovery_category":None,"recovery_dollars":None,"loss_recovered_dollars":None,
             "recovery_minutes":None,"unknown":False,"censored":False,"net_dollars":None,
             "known_closed_net_dollars":0.,"reason":None,"account_settings":asdict(a)}
        if equity is None or day_equity is None:
            row.update(unknown=True,reason="account_equity_unknown_from_prior_episode",equity_after_episode=None,
                       original_quantity=None if mode!="replacement_only" else 0,
                       second_quantity=None if mode!="original_only" else 0,eligible_signal=None,
                       original_filled=None if mode!="replacement_only" else False,
                       second_filled=None if mode!="original_only" else False,
                       eligible_loss=None if mode!="replacement_only" and (unit.get("net_dollars") is None or unit["net_dollars"]< -EPS) else False,
                       original_net_dollars=None if mode!="replacement_only" else 0.,second_net_dollars=None if mode!="original_only" else 0.)
            if policy is not None:
                signal=find_signal(ctx,policy,c)
                row.update(signal=bool(signal["signal"]),opportunity=bool(signal["opportunity"]),
                           signal_available_at=signal["signal_available_at"],arming_at=signal["arming_at"],
                           first_signal_status=signal["status"],first_signal_reason=signal["reason"],
                           candidate_direction=signal["direction"],second_result=signal)
                if signal["status"]=="known_no_fill":
                    row.update(second_filled=False,second_quantity=0)
            ledgers.append(row);continue
        original=None
        if mode!="replacement_only":
            size=budget_quantity(day_equity,e.original_boundary,float(unit["initial_stop"]),fraction=1. if mode=="original_only" else .5,
                                 capacity_equity=equity,account=a,economics=c)
            q=size["quantity"]
            row.update(original_sizing=size,original_quantity=q,original_quantity_skipped=q==0)
            if q==0:row["quantity_skips"]+=1
            original=_scaled_original(unit,q)
            row.update(original_trade=original,original_filled=original is not None)
        row["eligible_loss"]=(False if original is None else original["net_dollars"]< -EPS
                              if original.get("status")=="completed" and original.get("net_dollars") is not None else None)
        later=None; uncertain=False
        if mode!="original_only":
            signal=find_signal(ctx,policy,c)
            row.update(signal=bool(signal["signal"]),opportunity=bool(signal["opportunity"]),
                       signal_available_at=signal["signal_available_at"],arming_at=signal["arming_at"],
                       first_signal_status=signal["status"],first_signal_reason=signal["reason"],
                       candidate_direction=signal["direction"],second_result=signal)
            if signal["status"]=="unknown_signal":
                # No known order is invented. A missing first setup can still
                # conceal an executable leg, so total account outcome is null.
                structurally_ineligible=(original is None and mode in {"same_direction_concurrent_add_on","post_exit_reentry","post_realized_loss_recovery"}) or (mode=="flat_only_opposite_reversal" and signal["direction"]==e.direction)
                uncertain=not structurally_ineligible
                if uncertain:row.update(second_quantity=None,second_filled=None)
                row["reason"]="actual_original_leg_not_executed" if structurally_ineligible and original is None else "candidate_direction_not_opposite" if structurally_ineligible else signal["reason"]
            elif signal["status"]=="submitted":
                at=instant(signal["signal_available_at"])
                state=_account_original_state(ctx,original,at)
                eligible,reason=_eligible(mode,original,state,signal["direction"]==e.direction)
                row.update(original_position_at_signal=state["position"],original_loss_known_at_signal=state["loss_known"],
                           actual_original_realized_net_at_signal=state["realized_net_dollars"],eligible_signal=eligible,
                           original_exit_known_at=state["exit_known_at"])
                if eligible is None:
                    uncertain=True;row.update(reason=reason,second_quantity=None,second_filled=None)
                elif not eligible:
                    row["reason"]=reason
                else:
                    realized=state["realized_net_dollars"] if original is not None and state["position"]=="flat" else 0.
                    signal_equity=equity+realized
                    anchor=float(signal["initial_stop_anchor"])
                    active_q=int(original["quantity"]) if original is not None and state["position"]=="open" else 0
                    active_notional=active_q*anchor*c.point_value
                    size=budget_quantity(day_equity,anchor,float(signal["initial_stop"]),fraction=1. if mode=="replacement_only" else .5,
                                         capacity_equity=signal_equity,active_notional=active_notional,
                                         active_margin=active_notional*a.margin_percent/100,account=a,economics=c)
                    row.update(second_sizing=size,second_quantity=size["quantity"],equity_at_signal=signal_equity,
                               active_original_notional_at_signal=active_notional,
                               active_original_margin_at_signal=active_notional*a.margin_percent/100,
                               second_quantity_skipped=size["quantity"]==0)
                    if size["quantity"]==0:row["quantity_skips"]+=1
                    result=execute_signal(signal,ctx,c,quantity=size["quantity"])
                    later=result.get("trade")
                    row.update(second_result=result,second_trade=later,second_filled=None if result["status"]=="unknown_fill" else later is not None,
                               opportunity=bool(result["opportunity"]),reason=result["reason"] or size["reason"])
                    uncertain=result["status"] in {"unknown_fill","filled_censored"}
        if original is not None and original.get("status")!="completed":
            uncertain=True
        trades=[t for t in (original,later) if t is not None]
        row["known_closed_net_dollars"]=sum(float(t["net_dollars"]) for t in trades if t.get("status")=="completed" and t.get("net_dollars") is not None)
        row.update(censored=any(t.get("status")=="censored" for t in trades),
                   original_net_dollars=original.get("net_dollars") if original else 0.,
                   second_net_dollars=later.get("net_dollars") if later else None if uncertain else 0.,
                   completed_pair=original is not None and later is not None and all(t.get("status")=="completed" for t in trades),
                   unknown=uncertain,net_dollars=_known_total(original,later,uncertain=uncertain))
        recovery=financial_recovery(original.get("net_dollars") if original else None,later.get("net_dollars") if later else None,
                                   loss_known=bool(row.get("original_loss_known_at_signal")),
                                   actually_executed=row["completed_pair"])
        if recovery:
            row.update(recovery_category=recovery["category"],recovery_dollars=recovery["recovery_dollars"],
                       loss_recovered_dollars=recovery["loss_recovered_dollars"],
                       combined_pair_net_dollars=recovery["combined_net_dollars"],
                       unrecovered_loss_dollars=recovery["unrecovered_loss_dollars"])
            exit_at=instant(later["exit_time"])
            exit_latest=instant(later.get("exit_time_latest") or later["exit_time"])
            known_at=max(exit_latest,bucket(exit_at)+timedelta(minutes=15)) if later.get("exit_time_precision")=="within_bar" else exit_latest
            loss_at=instant(row["original_exit_known_at"])
            row.update(recovery_time=iso(exit_at),recovery_time_latest=iso(exit_latest),recovery_known_at=iso(known_at),
                       recovery_minutes=(known_at-loss_at).total_seconds()/60 if known_at and loss_at else None,
                       recovery_minutes_lower=max(0,(exit_at-loss_at).total_seconds()/60) if loss_at else None,
                       recovery_minutes_upper=max(0,(exit_latest-loss_at).total_seconds()/60) if loss_at else None)
        equity=None if uncertain else equity+row["net_dollars"]
        row["equity_after_episode"]=equity
        ledgers.append(row)
    return ledgers


def _cohorts(ledgers):
    output=[]
    accounts=sorted({(r["policy"],r["mode"]) for r in ledgers})
    years=["all",*sorted({str(r["year"]) for r in ledgers})]
    for policy,mode in accounts:
        for year in years:
            for session in SESSIONS:
                for side in SIDES:
                    rows=[r for r in ledgers if r["policy"]==policy and r["mode"]==mode and
                          (year=="all" or str(r["year"])==year) and (session=="all" or r["session"]==session) and (side=="combined" or r["side"]==side)]
                    recovered=[r for r in rows if r["recovery_category"] is not None]
                    completed=[r for r in rows if r["net_dollars"] is not None]
                    loss_unknown=sum(r["eligible_loss"] is True and r["unknown"] for r in rows)
                    unknown_loss=sum(r["eligible_loss"] is None for r in rows)
                    loss=sum(r["eligible_loss"] is True for r in rows)
                    full=sum(r["recovery_category"]=="full_recovery" for r in rows)
                    output.append({"policy":policy,"mode":mode,"year":year,"session":session,"side":side,
                        "population":"conditional_phase1_accepted_episode","episodes":len(rows),
                        "signals":sum(r["signal"] for r in rows),"eligible_signals":sum(r["eligible_signal"] is True for r in rows),
                        "opportunities":sum(r["opportunity"] for r in rows),"eligible_loss":loss,
                        "original_fills":sum(r["original_filled"] is True for r in rows),"second_fills":sum(r["second_filled"] is True for r in rows),
                        "unknown_original_fills":sum(r["original_filled"] is None for r in rows),
                        "unknown_second_fills":sum(r["second_filled"] is None for r in rows),
                        "quantity_skips":sum(r["quantity_skips"] for r in rows),"completed_pairs":sum(r["completed_pair"] for r in rows),
                        "completed_financial_recovery_pairs":len(recovered),"full_recovery":full,
                        **{key:sum(r["recovery_category"]==key for r in rows) for key in ("partial_recovery","no_improvement","further_loss")},
                        "net_dollars":sum(r["net_dollars"] for r in completed) if rows and len(completed)==len(rows) else None,
                        "net_completed_known_dollars":sum(r["net_dollars"] for r in completed) if completed else None,
                        "net_known_episodes":len(completed),"known_closed_net_dollars":sum(r["known_closed_net_dollars"] for r in rows),
                        "recovery_rate":full/len(recovered) if recovered else None,
                        "full_recovery_per_eligible_loss":full/loss if loss and not loss_unknown and not unknown_loss else None,
                        "eligible_loss_unknown_outcome":loss_unknown,
                        "unknown_eligible_loss":unknown_loss,
                        "recovery_dollars":sum(r["recovery_dollars"] for r in recovered) if recovered else None,
                        "loss_recovered_dollars":sum(r["loss_recovered_dollars"] for r in recovered) if recovered else None,
                        "mean_recovery_minutes":mean(r["recovery_minutes"] for r in recovered if r["recovery_minutes"] is not None) if any(r["recovery_minutes"] is not None for r in recovered) else None,
                        "unknown":sum(r["unknown"] for r in rows),"censored":sum(r["censored"] for r in rows)})
    return output


def _capacity(range_roster,contexts,a,c):
    if range_roster is None:
        range_roster={ctx.episode.broker_day:{"range_high":ctx.episode.range_high,"range_low":ctx.episode.range_low,"eligible":True} for ctx in contexts}
        population="conditional_accepted_episode_ranges"
    else:population="full_causally_eligible_day_roster"
    rows=[]
    roster=range_roster if not isinstance(range_roster,Mapping) else ({"broker_day":day,**values} for day,values in range_roster.items())
    for record in sorted(roster,key=lambda r:r["broker_day"]):
        eligible=record.get("eligible",False)
        if eligible not in {True,"true","True",1}:continue
        for direction,side,key in [(1,"long","range_high"),(-1,"short","range_low")]:
            reference=float(record[key]);stop=percentage_stop(reference,direction,c.stop_percent,c.tick_size)
            full=budget_quantity(a.initial_capital,reference,stop,fraction=1.,account=a,economics=c)
            half=budget_quantity(a.initial_capital,reference,stop,fraction=.5,account=a,economics=c)
            rows.append({"broker_day":str(record["broker_day"]),"side":side,"direction":direction,
                "population":population,"reference_equity":a.initial_capital,"reference_price":reference,"initial_stop":stop,
                "risk_points":abs(reference-stop),"risk_dollars_per_contract":abs(reference-stop)*c.point_value,
                "notional_per_contract":reference*c.point_value,"margin_per_contract":reference*c.point_value*a.margin_percent/100,
                "full_budget_dollars":full["risk_budget_dollars"],"half_budget_dollars":half["risk_budget_dollars"],
                "full_quantity":full["quantity"],"half_quantity":half["quantity"],
                "full_skip_reason":full["reason"],"half_skip_reason":half["reason"],
                "static_initial_capital_capacity_audit":True})
    return rows


def account_results(contexts: Iterable[EpisodeContext] | Mapping[str,EpisodeContext],
                    baseline_by_episode_id: Mapping[str,Mapping[str,Any]],
                    selection: Mapping[str,Any] | str | None,*,range_roster=None,
                    config: Phase2Config | None=None,account_config: AccountConfig | None=None) -> dict[str,Any]:
    """Separate actual accounts; overrides are for synthetic accounting fixtures.

    Standardized source rows never become actual executed losses when their
    allocated quantity is zero. An unknown actual account outcome cannot seed
    later equity. The input roster stays all accepted original episodes.
    """
    c=config or Phase2Config();a=account_config or AccountConfig()
    ordered=sorted(contexts.values() if isinstance(contexts,Mapping) else contexts,key=lambda ctx:ctx.episode.entry_time)
    ids=[ctx.episode.episode_id for ctx in ordered]
    if len(ids)!=len(set(ids)) or any(eid not in baseline_by_episode_id for eid in ids):
        raise ValueError("unique accepted episodes with exact saved baseline rows required")
    if len({ctx.episode.broker_day for ctx in ordered})!=len(ordered):
        raise ValueError("one original accepted episode per broker day required")
    policies=_policies(selection)
    ledgers=_account_path(ordered,baseline_by_episode_id,None,"original_only",a,c)
    for policy in policies:
        for mode in MODES[1:]:
            ledgers.extend(_account_path(ordered,baseline_by_episode_id,policy,mode,a,c))
    return {"schema_version":"study23.phase2-actual-accounts/v1","settings":asdict(a),
            "economics":asdict(c),"selected_policies":[p.name for p in policies],
            "population":"conditional_phase1_accepted_episode","episodes":len(ordered),
            "ledgers":ledgers,"cohorts":_cohorts(ledgers),"capacity_audit":_capacity(range_roster,ordered,a,c)}
