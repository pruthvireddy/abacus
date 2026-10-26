"""Saved Phase2 trade, original-episode comparison and account summaries.

Producer functions consume canonical ledgers; publication code never imports this.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean
import math

import numpy as np

from metrics import cohort, enrich, closed_path, session_at, instant, SESSIONS, SIDES, NY
from src.engine import quantity_at_boundary

FIRST_SIDES = ("combined", "upper-first", "lower-first")
YEARS = ("all", *(str(i) for i in range(2018,2027)))


def origin(trade):
    t = instant(trade["entry_time"]).astimezone(NY)
    return {"year":str(t.year), "session":session_at(trade["entry_time"]),
            "side":"upper-first" if trade["direction"]==1 else "lower-first"}


def match(row, year="all", session="all", side="combined"):
    return (year=="all" or row["year"]==year) and (session=="all" or row["session"]==session) and (side=="combined" or row["side"]==side)


def known_pnl(row):
    if row["status"] == "completed":
        return row["trade"]["net_dollars"]
    if row["status"] in ("no_fill", "missed_before_arming", "invalid_planned_risk"):
        return 0.0
    return None


def paired_intervals(values, calendar_days, *, weeks=4, confidence=.95, reps=10000, seed=230015):
    """Aligned block draws of saved sums/counts, with full calendar spacing.

    Each values entry is (broker_day, vector whose nulls share the family mask).
    Complete empty blocks remain; no-fill zero contributes to the episode count.
    """
    if not values or not calendar_days:
        return []
    first=min(datetime.fromisoformat(str(d)) for d in calendar_days)
    last=max(datetime.fromisoformat(str(d)) for d in calendar_days)
    # Monday-aligned calendar weeks, not adjacent-observation blocks.
    first-=timedelta(days=first.weekday())
    span=7*weeks
    blocks=(last-first).days//span+1
    width=len(values[0][1])
    sums=np.zeros((blocks,width)); counts=np.zeros((blocks,width))
    for day,vector in values:
        slot=(datetime.fromisoformat(day)-first).days//span
        for i,value in enumerate(vector):
            if value is not None:
                sums[slot,i]+=value;counts[slot,i]+=1
    if not np.any(counts):
        return [(None,None)]*width
    rng=np.random.default_rng(seed)
    samples=[[] for _ in range(width)]
    for offset in range(0,reps,500):
        draw=rng.integers(0,blocks,size=(min(500,reps-offset),blocks))
        num=sums[draw].sum(axis=1);den=counts[draw].sum(axis=1)
        for i in range(width):
            ok=den[:,i]>0
            samples[i].extend((num[ok,i]/den[ok,i]).tolist())
    tail=(1-confidence)/2
    return [(tuple(float(v) for v in np.quantile(x,[tail,1-tail])) if x else (None,None)) for x in samples]


def trade_summaries(rows, days, policy):
    trades=[enrich(r["trade"]) for r in rows if r.get("trade")]
    tables=[]
    for y in YEARS:
        for s in ("all",*SESSIONS):
            for side in SIDES:
                item=cohort(trades,days,year=y,session=s,side=side,intervals=True)
                # Day opportunities belong to the original cohort, not a no-fill's
                # nonexistent candidate entry session.
                for key in ("eligible_days","valid_ranges","no_trade_days","unknown_days","exclusions","quantity_skips"):
                    item[key]=None
                item.update(policy=policy,anchor="candidate_actual_fill")
                tables.append(item)
    timing=[]
    for dimension,labels in (("hour",range(24)),("weekday",("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"))):
        for label in labels:
            for side in SIDES:
                subset=[t for t in trades if t[dimension]==label]
                item=cohort(subset,days,side=side,intervals=False)
                for key in ("eligible_days","valid_ranges","no_trade_days","unknown_days","exclusions","quantity_skips"):
                    item[key]=None
                item.update(policy=policy,dimension=dimension,bucket=label,entry_share=item["executable_fills"]/len(trades) if trades else None,anchor="candidate_actual_fill")
                timing.append(item)
    equity,_=closed_path(trades)
    for row in equity:row["policy"]=policy
    return trades,tables,timing,equity


def paired_rows(results, baseline, calendar, policies, family, *, intervals=True):
    indexed={p:{r["episode_id"]:r for r in results[p]} for p in policies}
    origins={key:origin(t) for key,t in baseline.items()}
    common={key:t["status"]=="completed" and all(known_pnl(indexed[p][key]) is not None for p in policies) for key,t in baseline.items()}
    output=[]
    confidence=.9875 if family=="primary" else .9833333333333333
    for y in YEARS:
        # Winter broker 07:00 is previous-NY-date 23:00. Include the next
        # Jan1 broker date so actual Dec31 NY fills keep their calendar slot.
        calendar_subset=[d for d in calendar if y=="all" or f"{y}-01-01"<=d<=f"{int(y)+1}-01-01"]
        for s in ("all",*SESSIONS):
            for side in FIRST_SIDES:
                ids=[key for key in baseline if match(origins[key],y,s,side)]
                paired=[key for key in ids if common[key]]
                vectors=[(baseline[k]["broker_day"],[known_pnl(indexed[p][k])-baseline[k]["net_dollars"] if common[k] else None for p in policies]) for k in ids]
                point=(paired_intervals(vectors,calendar_subset) or [(None,None)]*len(policies)) if intervals else [(None,None)]*len(policies)
                simultaneous=family=="primary" or (family=="protected" and side=="upper-first")
                corrected=(paired_intervals(vectors,calendar_subset,confidence=confidence) or [(None,None)]*len(policies)) if intervals and simultaneous else [(None,None)]*len(policies)
                for pi,p in enumerate(policies):
                    selected=[indexed[p][k] for k in ids]
                    differences=[known_pnl(indexed[p][k])-baseline[k]["net_dollars"] for k in paired]
                    individual=[k for k in ids if baseline[k]["status"]=="completed" and known_pnl(indexed[p][k]) is not None]
                    fills=[r for r in selected if r.get("trade")]
                    known_zero=[k for k in ids if known_pnl(indexed[p][k])==0 and not indexed[p][k].get("trade")]
                    delays=[(instant(r["trade"]["entry_time"])-instant(baseline[r["episode_id"]]["entry_time"])).total_seconds()/60 for r in fills]
                    prices=[baseline[r["episode_id"]]["direction"]*(baseline[r["episode_id"]]["entry_price"]-r["trade"]["entry_price"]) for r in fills if r["trade"]["direction"]==baseline[r["episode_id"]]["direction"]]
                    output.append(dict(policy=p,family=family,year=y,session=s,side=side,anchor="original_breakout_fill",episodes=len(ids),complete_pairs=len(paired),missing_pairs=len(ids)-len(paired),missing_rate=(len(ids)-len(paired))/len(ids) if ids else None,
                        opportunities=sum(r.get("opportunity_seen") is True for r in selected),opportunity_unknown=sum(r.get("opportunity_seen") is None for r in selected),armed=sum(bool(r.get("arming_at")) for r in selected),signals=sum(bool(r.get("signal_at")) for r in selected),fills=len(fills),completed=sum(r["status"]=="completed" for r in selected),censored=sum(r["status"]=="censored" for r in selected),unknown=sum(r["status"]=="unknown" for r in selected),no_fill=len(known_zero),ambiguous=sum(bool(r.get("ambiguous")) for r in selected),
                        participation_rate=len(fills)/len(ids) if ids else None,signal_rate=sum(bool(r.get("signal_at")) for r in selected)/len(ids) if ids else None,
                        baseline_net_dollars=sum(baseline[k]["net_dollars"] for k in paired) if paired else None,alternative_net_dollars=sum(known_pnl(indexed[p][k]) for k in paired) if paired else None,
                        mean_difference=mean(differences) if differences else None,difference_low=point[pi][0],difference_high=point[pi][1],adjusted_low=corrected[pi][0],adjusted_high=corrected[pi][1],adjusted_confidence=confidence if simultaneous else None,
                        individual_pairs=len(individual),individual_mean_difference=mean([known_pnl(indexed[p][k])-baseline[k]["net_dollars"] for k in individual]) if individual else None,
                        improved=sum(v>1e-8 for v in differences),deteriorated=sum(v< -1e-8 for v in differences),equal=sum(abs(v)<=1e-8 for v in differences),
                        missed_winners=sum(baseline[k]["status"]=="completed" and baseline[k]["net_dollars"]>1e-8 for k in known_zero),avoided_losses=sum(baseline[k]["status"]=="completed" and baseline[k]["net_dollars"]< -1e-8 for k in known_zero),mean_entry_delay=mean(delays) if delays else None,mean_price_improvement=mean(prices) if prices else None))
    return output


def interval_sensitivities(results, baseline, calendar, policies, family, periods):
    output=[]
    for period,years in periods.items():
        sub={k:t for k,t in baseline.items() if origin(t)["year"] in {str(y) for y in years}}
        maps={p:{r["episode_id"]:r for r in results[p]} for p in policies}
        days=[d for d in calendar if f"{min(years)}-01-01"<=d<=f"{max(years)+1}-01-01"]
        for side in FIRST_SIDES:
            ids=[k for k,t in sub.items() if side=="combined" or origin(t)["side"]==side]
            vectors=[(sub[k]["broker_day"],[known_pnl(maps[p][k])-sub[k]["net_dollars"] if sub[k]["status"]=="completed" and all(known_pnl(maps[q][k]) is not None for q in policies) else None for p in policies]) for k in ids]
            for weeks in (1,4,8):
                point=paired_intervals(vectors,days,weeks=weeks)
                corrected=paired_intervals(vectors,days,weeks=weeks,confidence=.9875 if family=="primary" else .9833333333333333) if family=="primary" or side=="upper-first" else [(None,None)]*len(policies)
                for i,p in enumerate(policies):
                    vals=[v[i] for _,v in vectors if v[i] is not None]
                    output.append(dict(policy=p,family=family,period=period,side=side,block_weeks=weeks,episodes=len(ids),complete_pairs=len(vals),mean_difference=mean(vals) if vals else None,lower=point[i][0] if point else None,upper=point[i][1] if point else None,adjusted_lower=corrected[i][0] if corrected else None,adjusted_upper=corrected[i][1] if corrected else None))
    return output


def financial_recovery(original_net, later_net, *, loss_known, actually_executed):
    if not loss_known or original_net is None or original_net>=-1e-8 or not actually_executed or later_net is None:
        return None
    combined=original_net+later_net
    category="full_recovery" if combined>=-1e-8 else "partial_recovery" if later_net>1e-8 else "further_loss" if later_net< -1e-8 else "no_improvement"
    return {"category":category,"combined_net_dollars":combined,"recovery_dollars":later_net}


def budget_quantity(equity, reference, stop, *, fraction=1., active_notional=0., active_margin=0.):
    quantity=quantity_at_boundary(equity,reference,stop,risk_percent=fraction,max_leverage=10,step=1,minimum=1,point_value=100)
    if reference<=0 or equity<=0:return 0.
    leverage=max(0,equity*10-active_notional)/(reference*100)
    margin=max(0,equity-active_margin)/(reference*100*.05)
    return float(max(0,min(quantity,math.floor(leverage+1e-9),math.floor(margin+1e-9))))


def frequency_rows(observations, event_names, *, recovery=False, dimensions=None):
    """Input records are one event/horizon/episode, preserving tri-state flags."""
    output=[]
    dimensions=dimensions if dimensions is not None else sorted({(r["horizon"],r.get("level",""),r["event"]) for r in observations})
    for y in YEARS:
        for session in ("all",*SESSIONS):
            for side in FIRST_SIDES:
                for horizon,level,event in dimensions:
                    rows=[r for r in observations if match(r,y,session,side) and r["horizon"]==horizon and r.get("level","")==level and r["event"]==event]
                    yes=[r for r in rows if r["occurred"] is True];no=[r for r in rows if r["occurred"] is False];unknown=[r for r in rows if r["occurred"] is None]
                    elapsed=[r["elapsed_minutes"] for r in yes if r.get("elapsed_minutes") is not None]
                    exposure=[r["scheduled_exposure_minutes"] for r in rows if r.get("scheduled_exposure_minutes") is not None]
                    observed=[r["observed_exposure_minutes"] for r in rows if r.get("observed_exposure_minutes") is not None]
                    lower=[r["elapsed_minutes_lower"] for r in yes if r.get("elapsed_minutes_lower") is not None]
                    upper=[r["elapsed_minutes_upper"] for r in yes if r.get("elapsed_minutes_upper") is not None]
                    repeat=[r["repeat_contacts"] for r in rows if r.get("repeat_contacts") is not None]
                    output.append(dict(year=y,session=session,side=side,horizon=horizon,event=event,**({"level":level} if recovery else {}),episodes=len(rows),known_events=len(yes),known_none=len(no),unknown=len(unknown),known_denominator=len(yes)+len(no),rate=len(yes)/(len(yes)+len(no)) if yes or no else None,lower_bound=len(yes)/len(rows) if rows else None,upper_bound=(len(yes)+len(unknown))/len(rows) if rows else None,mean_elapsed_minutes=mean(elapsed) if elapsed else None,elapsed_denominator=len(elapsed),mean_elapsed_lower_minutes=mean(lower) if lower else None,mean_elapsed_upper_minutes=mean(upper) if upper else None,mean_exposure_minutes=mean(exposure) if exposure else None,mean_observed_exposure_minutes=mean(observed) if observed else None,repeat_contacts=sum(repeat) if repeat else None,repeat_known_episodes=len(repeat),anchor="original_breakout_fill"))
    return output
