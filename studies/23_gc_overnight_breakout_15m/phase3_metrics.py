"""Study-owned Phase 3 saved statistics from explicit causal ledgers.

The renderer never imports this module.  Null execution, known abstention zero,
conditional open landmarks, and actual leg-entry cohorts remain distinct.
"""
from __future__ import annotations

import csv
import gzip
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median
from zoneinfo import ZoneInfo

import numpy as np
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

NY = ZoneInfo("America/New_York")
SESSIONS = ("Asia", "London", "New York", "Outside")
YEARS = ("all", *(str(y) for y in range(2018, 2027)))
SIDES = ("combined", "long", "short")
CORE = ("G1", "G2", "A20", "A50", "X1", "X2")
CORRECTED = 1 - .05 / 6


def instant(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def session_at(value):
    t = instant(value).astimezone(NY)
    minute = t.hour * 60 + t.minute
    return "Asia" if minute >= 1200 or minute < 120 else "London" if minute < 540 else "New York" if 570 <= minute < 960 else "Outside"


def anchor(value, direction):
    if not value:
        return {"year": "unknown", "session": "unknown", "side": "unknown"}
    t = instant(value).astimezone(NY)
    return {"year": str(t.year), "session": session_at(value), "side": "long" if direction == 1 else "short", "hour": t.hour, "weekday": t.strftime("%A")}


def match(row, year="all", session="all", side="combined"):
    return (year == "all" or str(row["year"]) == year) and (session == "all" or row["session"] == session) and (side == "combined" or row["side"] == side)


def dimensions():
    return ((y, s, d) for y in YEARS for s in ("all", *SESSIONS) for d in SIDES)


def key(row):
    return row["policy"], row["mode"]


def control(policy):
    return ("BASE", "half_parent") if policy in {"A20", "A50"} else ("BASE", "parent_1")


def policy_mode(policy):
    return "financed_overlay" if policy in {"A20", "A50"} else "standardized"


def pnl(row):
    if row["status"] in {"no_fill", "known_no_fill"}:
        if row.get("net_dollars") != 0:
            raise ValueError("known abstention must carry explicit zero")
        return 0.
    return row.get("net_dollars") if row["status"] == "completed" else None


def ratio(num, den):
    return num / den if den else None


def average(values):
    values = [v for v in values if v is not None]
    return mean(values) if values else None


def closed_path(trades):
    total = peak = 0.
    rows = []
    for t in sorted((x for x in trades if x["status"] == "completed"), key=lambda x: (x["exit_time"], x["trade_id"])):
        total += t["net_dollars"]
        peak = max(peak, total)
        rows.append({"trade_id": t["trade_id"], "exit_time": t["exit_time"], "cumulative_net_dollars": total, "drawdown_dollars": total - peak})
    return rows, max((-r["drawdown_dollars"] for r in rows), default=0.)


def block_intervals(values, calendar, *, weeks=4, reps=10000, seed=230015):
    """One common block draw preserves spacing and six within-episode effects.

    `values` contains (broker_day, vector) with retained nulls and no-fill zeros.
    Both interval levels use the very same draws. Empty calendar blocks remain.
    """
    if not values or not calendar:
        return []
    first = min(datetime.fromisoformat(str(d)) for d in calendar)
    last = max(datetime.fromisoformat(str(d)) for d in calendar)
    first -= timedelta(days=first.weekday())
    blocks = (last - first).days // (7 * weeks) + 1
    width = len(values[0][1])
    sums = np.zeros((blocks, width))
    counts = np.zeros((blocks, width))
    for day, vector in values:
        slot = (datetime.fromisoformat(day) - first).days // (7 * weeks)
        if not 0 <= slot < blocks:
            raise ValueError("episode outside retained block calendar")
        for i, value in enumerate(vector):
            if value is not None:
                sums[slot, i] += value
                counts[slot, i] += 1
    rng = np.random.default_rng(seed)
    samples = [[] for _ in range(width)]
    for offset in range(0, reps, 250):
        draw = rng.integers(0, blocks, size=(min(250, reps - offset), blocks))
        num, den = sums[draw].sum(axis=1), counts[draw].sum(axis=1)
        for i in range(width):
            ok = den[:, i] > 0
            samples[i].extend((num[ok, i] / den[ok, i]).tolist())
    result = []
    for sample in samples:
        qs = np.quantile(sample, [.025, .975, (1 - CORRECTED) / 2, 1 - (1 - CORRECTED) / 2]) if sample else [None] * 4
        result.append(dict(zip(("difference_low", "difference_high", "adjusted_low", "adjusted_high"), (float(v) if v is not None else None for v in qs))))
    return result


def calendar_subset(calendar, year):
    # Fixed GMT+3 broker midnight may correspond to preceding NY calendar year.
    return calendar if year == "all" else [d for d in calendar if f"{year}-01-01" <= d <= f"{int(year)+1}-01-01"]


def paired_rows(episodes, parents, calendar, *, intervals=True, policies=CORE, cohorts=None):
    maps = defaultdict(dict)
    for row in episodes:
        if row.get("scenario", "primary-one-tick") == "primary-one-tick":
            if row["episode_id"] in maps[key(row)]:
                raise ValueError("duplicate episode policy/control")
            maps[key(row)][row["episode_id"]] = row
    origins = {i: anchor(t["entry_time"], t["direction"]) for i, t in parents.items()}
    # Every policy's exact declared control must be complete; parents retain
    # unknown outcomes in the roster even if financed no-trade is known zero.
    effects = {}
    for eid in parents:
        effects[eid] = []
        for p in policies:
            alternative = maps[(p, policy_mode(p))].get(eid)
            base = maps[control(p)].get(eid)
            a = pnl(alternative) if alternative else None
            b = pnl(base) if base else None
            effects[eid].append(a - b if a is not None and b is not None else None)
    common = {eid: all(v is not None for v in vector) for eid, vector in effects.items()}
    output = []
    for y, s, d in (dimensions() if cohorts is None else cohorts):
        ids = [eid for eid in parents if match(origins[eid], y, s, d)]
        complete = [eid for eid in ids if common[eid]]
        vectors = [(parents[i]["broker_day"], effects[i] if common[i] else [None] * len(policies)) for i in ids]
        cis = block_intervals(vectors, calendar_subset(calendar, y)) if intervals else []
        for index, p in enumerate(policies):
            selected = [maps[(p, policy_mode(p))][i] for i in ids]
            vals = [effects[i][index] for i in complete]
            observed = [effects[i][index] for i in ids if effects[i][index] is not None]
            known_no_action = [i for i in ids if pnl(maps[(p, policy_mode(p))][i]) == 0 and not maps[(p, policy_mode(p))][i].get("original_fills")]
            base_values = [pnl(maps[control(p)][i]) for i in complete]
            alt_values = [pnl(maps[(p, policy_mode(p))][i]) for i in complete]
            output.append({"policy": p, "mode": policy_mode(p), "control": ":".join(control(p)), "anchor": "original_actual_entry", "year": y, "session": s, "side": d,
                "episodes": len(ids), "complete_pairs": len(complete), "missing_pairs": len(ids)-len(complete), "individual_pairs": len(observed), "individual_mean_difference": average(observed),
                "baseline_net_dollars": sum(base_values) if complete else None, "alternative_net_dollars": sum(alt_values) if complete else None,
                "mean_difference": average(vals), **(cis[index] if cis else {k: None for k in ("difference_low", "difference_high", "adjusted_low", "adjusted_high")}), "adjusted_confidence": CORRECTED,
                "improved": sum(v > 1e-8 for v in vals), "deteriorated": sum(v < -1e-8 for v in vals), "equal": sum(abs(v) <= 1e-8 for v in vals),
                "signals": sum(r.get("signals", 0) for r in selected), "original_fills": sum(r.get("original_fills", 0) for r in selected), "add_fills": sum(r.get("add_fills", 0) for r in selected),
                "opportunities":len(ids),"add_attempts":sum(r.get("add_attempts",0) for r in selected),"observed_add_contacts":sum(r.get("add_opportunity") is True for r in selected),"unknown_add_contacts":sum(r.get("add_opportunity") is None for r in selected),
                "rejections":sum(str(r.get("action_status","")).startswith("rejected_") for r in selected),"unknown_feature_slots":sum(r.get("unknown_feature_count",0) for r in selected),
                "completed": sum(r["status"] == "completed" for r in selected), "known_zero": sum(pnl(r) == 0 and r["status"] == "no_fill" for r in selected), "unknown_execution": sum(pnl(r) is None for r in selected),
                "feature_abstentions": sum(r.get("gate_feature_unknown", False) for r in selected), "blocked": sum(r.get("action_status") == "blocked_first_shadow_consumed" for r in selected),
                "cancellations": sum(r.get("pending_add_cancellations", 0) for r in selected), "quantity_skips": sum(r.get("action_status") == "original_quantity_skip" for r in selected),
                "signal_rate":ratio(sum(r.get("signals",0) for r in selected),len(ids)),"add_participation":ratio(sum(r.get("add_fills",0) for r in selected),len(ids)),
                "ambiguous": sum(bool(r.get("ambiguous")) for r in selected), "participation": ratio(sum(r.get("original_fills", 0) for r in selected), len(ids)),
                "missed_winners": sum(parents[i].get("net_dollars") is not None and parents[i]["net_dollars"] > 1e-8 for i in known_no_action),
                "avoided_losses": sum(parents[i].get("net_dollars") is not None and parents[i]["net_dollars"] < -1e-8 for i in known_no_action), "partial_year": y == "2026"})
    return output, effects, common


def trade_rows(trades, episodes, parents, exposure=()):
    output, paths, timing = [], [], []
    groups = sorted({key(r) for r in episodes})
    by_episode = defaultdict(list)
    for row in episodes:
        by_episode[key(row)].append(row)
    enriched = []
    for t in trades:
        item = dict(t, **anchor(t["entry_time"], t["direction"]))
        enriched.append(item)
    for p, m in groups:
        alltrades = [t for t in enriched if key(t) == (p, m)]
        for role in ("combined", "original", "add"):
            selected_role = [t for t in alltrades if role == "combined" or t.get("leg", "original") == role]
            fullpath, _ = closed_path(selected_role)
            paths.extend(dict(r, policy=p, mode=m, leg=role, anchor="actual_leg_fill") for r in fullpath)
            for y, s, d in dimensions():
                subset = [t for t in selected_role if match(t, y, s, d)]
                closed = [t for t in subset if t["status"] == "completed"]
                values = [t["net_dollars"] for t in closed]
                wins, losses = [v for v in values if v > 1e-8], [v for v in values if v < -1e-8]
                _, dd = closed_path(closed)
                output.append({"policy": p, "mode": m, "leg": role, "anchor": "actual_leg_fill", "year": y, "session": s, "side": d,
                    "fills": len(subset), "completed": len(closed), "censored": len(subset)-len(closed), "distinct_episodes": len({t["episode_id"] for t in subset}),
                    "wins": len(wins), "losses": len(losses), "breakevens": len(values)-len(wins)-len(losses), "win_rate": ratio(len(wins), len(values)),
                    "gross_points": sum(t.get("raw_price_points", 0) * t["quantity"] for t in closed) if closed else None,
                    "gross_dollars": sum(t.get("raw_price_dollars", t.get("gross_dollars", 0)) for t in closed) if closed else None,
                    "net_points": sum(t.get("net_points", 0) * t["quantity"] for t in closed) if closed else None, "net_dollars": sum(values) if closed else None,
                    "cost_dollars": sum(t.get("raw_price_dollars", t.get("gross_dollars", 0)) - t["net_dollars"] for t in closed) if closed else None,
                    "expectancy_dollars": average(values), "net_r": sum(t["net_r"] for t in closed if t.get("net_r") is not None) if closed else None, "r_denominator": sum(t.get("net_r") is not None for t in closed),
                    "profit_factor": sum(wins)/-sum(losses) if losses else None, "payoff": average(wins)/-average(losses) if wins and losses else None,
                    "mfe_points": average([t.get("mfe_points") for t in closed]), "mae_points": average([t.get("mae_points") for t in closed]), "holding_minutes": average([t.get("holding_minutes") for t in closed]),
                    "closed_drawdown_dollars": dd if closed else None, "annual_drawdown_path": "within-year closed P&L" if y != "all" else "full-history closed P&L", "partial_year": y == "2026"})
            for dimension, labels in (("hour", range(24)), ("weekday", ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))):
                for label in labels:
                    subset = [t for t in selected_role if t[dimension] == label]
                    closed = [t for t in subset if t["status"] == "completed"]
                    timing.append({"policy": p, "mode": m, "leg": role, "anchor": "actual_leg_fill", "dimension": dimension, "bucket": label, "fills": len(subset), "completed": len(closed), "net_dollars": sum(t["net_dollars"] for t in closed) if closed else None})
    return output, paths, timing


def risk_rows(episodes, parents):
    output = []
    for p, m in sorted({key(r) for r in episodes}):
        for y, s, d in dimensions():
            rows = [r for r in episodes if key(r) == (p,m) and match(anchor(parents[r["episode_id"]]["entry_time"], parents[r["episode_id"]]["direction"]), y,s,d)]
            known = [pnl(r) for r in rows if pnl(r) is not None]
            output.append({"policy":p,"mode":m,"year":y,"session":s,"side":d,"anchor":"original_actual_entry","episodes":len(rows),"known_outcomes":len(known),"unknown_outcomes":len(rows)-len(known),
                "net_dollars":sum(known) if known else None,"original_fills":sum(r.get("original_fills",0) for r in rows),"add_fills":sum(r.get("add_fills",0) for r in rows),
                "signals":sum(r.get("signals",0) for r in rows),"add_attempts":sum(r.get("add_attempts",0) for r in rows),"support_rejections":sum(str(r.get("action_status","")).startswith("rejected_") for r in rows),"unknown_support_abstentions":sum("unknown" in str(r.get("action_status","")) and "abstention" in str(r.get("action_status","")) for r in rows),
                "original_quantity_skips":sum(r.get("action_status")=="original_quantity_skip" for r in rows),"add_quantity_skips":sum(r.get("add_quantity_skips",0) for r in rows),
                "cancellations":sum(r.get("pending_add_cancellations",0) for r in rows),"unused_reserve_dollars":sum(r.get("unused_reserve_dollars") or 0 for r in rows),
                "mean_unused_reserve_dollars":average([r.get("unused_reserve_dollars") for r in rows]),"reserve_allocation_denominator":sum(r.get("unused_reserve_dollars") is not None for r in rows),"unused_reserve_scope":"sum/mean of daily reserved risk allocations; not an account cash balance or extra capital",
                "peak_notional":max((r["peak_notional"] for r in rows if r.get("peak_notional") is not None),default=0 if rows and all(r["status"]=="no_fill" for r in rows) else None) if all(pnl(r) is not None for r in rows) else None,"episode_mtm_drawdown_dollars":max((r["max_mtm_drawdown_dollars"] for r in rows if r.get("max_mtm_drawdown_dollars") is not None),default=0 if rows and all(r["status"]=="no_fill" for r in rows) else None) if all(pnl(r) is not None for r in rows) else None,
                "observed_prefix_peak_notional":max((r["peak_notional"] for r in rows if r.get("peak_notional") is not None),default=None),"observed_prefix_episode_mtm_drawdown_dollars":max((r["max_mtm_drawdown_dollars"] for r in rows if r.get("max_mtm_drawdown_dollars") is not None),default=None),
                "unknown_exposure_episodes":sum(pnl(r) is None or r.get("peak_notional") is None and r["status"]!="no_fill" for r in rows),
                "planned_risk_overshoot_episodes":sum(bool(r.get("risk_budget_overshoot")) for r in rows),"financing_enforced":m in {"full_parent","half_parent","financed_overlay"},"partial_year":y=="2026"})
    return output


def contact_diagnostics(monitoring, parents):
    """Saved frozen-contact path records, retaining post-exit recovery censoring."""
    by_episode=defaultdict(list)
    for row in monitoring: by_episode[row["episode_id"]].append(row)
    records=[]; forwards=[]
    for eid,bars in by_episode.items():
        bars.sort(key=lambda r:r["time"])
        parent=parents[eid];direction=parent["direction"]
        for index,row in enumerate(bars):
            if not row["open_position_landmark"]: continue
            for ema in (20,50):
                if not row[f"ema{ema}_contact"]: continue
                level=row[f"ema{ema}_frozen_level"]
                ticks=(Decimal(str(level))/Decimal("0.1")).to_integral_value(rounding=ROUND_FLOOR if direction==1 else ROUND_CEILING)
                breach_level=float((ticks-direction)*Decimal("0.1"))
                breached=(row["low"]<=breach_level if direction==1 else row["high"]>=breach_level) if row["usable"] else None
                hold=direction*(row["close"]-level)>0 if row["usable"] else None
                closebreak=direction*(row["close"]-level)<0 if row["usable"] else None
                recovery_at=None;unavailable=False
                if breached is True:
                    prior=instant(row["available_at"])
                    for later in bars[index+1:]:
                        if instant(later["time"])!=prior and not later.get("known_closure_before",False): unavailable=True
                        prior=instant(later["available_at"])
                        if not later["usable"]: unavailable=True;continue
                        if direction*(later["close"]-level)>0:
                            recovery_at=later["available_at"];break
                    if not recovery_at and prior<instant(parent["broker_day"]+"T17:00:00+00:00"): unavailable=True
                number=row[f"ema{ema}_contact_number"]
                prior_cloud=row.get("prior",{});current_cloud=row.get("current",{})
                cloud_flip=(prior_cloud["alignment"]>=0 and current_cloud["alignment"]<0) if prior_cloud.get("known") and current_cloud.get("known") else None
                item={"episode_id":eid,"broker_day":parent["broker_day"],"event_at":row["available_at"],"contact_open":row["time"],"ema":ema,"frozen_level":level,"breach_level":breach_level,
                    "contact_number":number,"contact_group":"unknown" if number is None else "first" if number==1 else "second" if number==2 else "third_or_more",
                    "hold":hold,"tick_breach":breached,"close_break":closebreak,"reclaimed":True if recovery_at else None if breached and unavailable else False if breached else None,
                    "reclaim_at":recovery_at if not unavailable else None,"recovery_minutes":(instant(recovery_at)-instant(row["available_at"])).total_seconds()/60 if recovery_at and not unavailable else None,
                    "first_observed_reclaim_at":recovery_at,"observed_recovery_minutes":(instant(recovery_at)-instant(row["available_at"])).total_seconds()/60 if recovery_at else None,
                    "recovery_time_known":bool(recovery_at and not unavailable),"recovery_delay_lower":0. if recovery_at and unavailable else (instant(recovery_at)-instant(row["available_at"])).total_seconds()/60 if recovery_at else None,"recovery_delay_upper":(instant(recovery_at)-instant(row["available_at"])).total_seconds()/60 if recovery_at else None,
                    "parent_liquidation_net_unit":row["parent_liquidation_net_unit"],"parent_status":"open","cloud_flip":cloud_flip,
                    **{f"confluence_{label}":prior_cloud.get(f"ema{ema}_{name}_confluence") for label,name in (("H","high"),("L","low"),("M","midpoint"))},
                    "anchor":"EMA_decision_event","source_monitoring_time":row["time"],**anchor(row["available_at"],direction)}
                records.append(item)
                start=instant(row["available_at"]);price=row["close"]
                bytime={instant(b["time"]):b for b in bars[index+1:]}
                for horizon in (5,15,30,60):
                    wanted=[start+timedelta(minutes=i) for i in range(0,horizon,5)]
                    future=[bytime.get(t) for t in wanted]
                    valid=all(b is not None and b["usable"] and b["contract"]==row["contract"] for b in future)
                    values={"signed_points":None,"mfe_points":None,"mae_points":None}
                    if valid:
                        values={"signed_points":direction*(future[-1]["close"]-price),"mfe_points":max(0.,max(direction*((b["high"] if direction==1 else b["low"])-price) for b in future)),"mae_points":max(0.,max(-direction*((b["low"] if direction==1 else b["high"])-price) for b in future))}
                    forwards.append({"episode_id":eid,"broker_day":parent["broker_day"],"event_at":row["available_at"],"ema":ema,"contact_group":item["contact_group"],"horizon_minutes":horizon,"status":"observed" if valid else "censored","source_candle_excluded":True,"not_trade_return":True,"anchor":"EMA_decision_event",**anchor(row["available_at"],direction),**values})
    return records,forwards


def contact_rows(records,monitoring):
    output=[]
    for ema in (20,50):
        for group in ("all","first","second","third_or_more","unknown"):
            for y,s,d in dimensions():
                rows=[r for r in records if r["ema"]==ema and (group=="all" or r["contact_group"]==group) and match(r,y,s,d)]
                support=[r for r in monitoring if r["open_position_landmark"] and match(anchor(r["available_at"],r["direction"]),y,s,d)]
                for event in ("hold","tick_breach","close_break","reclaimed","cloud_flip"):
                    # Recovery denominator contains breached contacts only.
                    eventrows=[r for r in rows if r["tick_breach"] is True] if event=="reclaimed" else rows
                    yes=sum(r[event] is True for r in eventrows);no=sum(r[event] is False for r in eventrows);unknown=len(eventrows)-yes-no
                    output.append({"ema":ema,"contact_group":group,"event":event,"year":y,"session":s,"side":d,"anchor":"EMA_decision_event","contacts":len(eventrows),"distinct_episodes":len({r["episode_id"] for r in eventrows}),"known_events":yes,"known_none":no,"unknown":unknown,"known_denominator":yes+no,"rate":ratio(yes,yes+no),"lower_bound":ratio(yes,len(eventrows)),"upper_bound":ratio(yes+unknown,len(eventrows)),"eligible_open_landmarks":len(support),"eligible_open_episodes":len({r["episode_id"] for r in support}),"mean_recovery_minutes":average([r["recovery_minutes"] for r in eventrows]),"recovery_timing_denominator":sum(r["recovery_time_known"] for r in eventrows),"observed_recovery_timing_unknown":sum(r["reclaimed"] is True and not r["recovery_time_known"] for r in eventrows),"conditional_population":True})
    return output


def confluence_rows(records):
    """Frozen prior-EMA proximity; contact events remain a conditional cohort."""
    output=[]
    for ema in (20,50):
        for level in ("H","L","M"):
            for state in ("yes","no","unknown"):
                grouped=[r for r in records if r["ema"]==ema and ("yes" if r.get("confluence_"+level) is True else "no" if r.get("confluence_"+level) is False else "unknown")==state]
                for y,s,d in dimensions():
                    rows=[r for r in grouped if match(r,y,s,d)]
                    for event in ("hold","tick_breach","close_break","reclaimed","cloud_flip"):
                        selected=[r for r in rows if r["tick_breach"] is True] if event=="reclaimed" else rows
                        yes=sum(r[event] is True for r in selected);no=sum(r[event] is False for r in selected);unknown=len(selected)-yes-no
                        output.append(dict(ema=ema,level=level,confluence_state=state,event=event,year=y,session=s,side=d,anchor="EMA_decision_event",contacts=len(selected),distinct_episodes=len({r["episode_id"] for r in selected}),known_events=yes,known_none=no,unknown=unknown,known_denominator=yes+no,rate=ratio(yes,yes+no),lower_bound=ratio(yes,len(selected)),upper_bound=ratio(yes+unknown,len(selected)),conditional_population=True))
    return output


def exposure_control_rows(episodes,parents):
    """Unfunded 1+1 diagnostics versus 1/2 originals on a fixed known mask."""
    indexed={(r["episode_id"],r["policy"],r["mode"]):r for r in episodes};output=[]
    for policy in ("A20","A50"):
        for y,s,d in dimensions():
            ids=[i for i,p in parents.items() if match(anchor(p["entry_time"],p["direction"]),y,s,d)]
            alternatives={i:pnl(indexed[(i,policy,"diagnostic_1plus1")]) for i in ids}
            controls={mode:{i:pnl(indexed[(i,"BASE",mode)]) for i in ids} for mode in ("parent_1","parent_2")}
            common=[i for i in ids if alternatives[i] is not None and all(controls[m][i] is not None for m in controls)]
            for mode,values in controls.items():
                individual=[i for i in ids if alternatives[i] is not None and values[i] is not None]
                diffs=[alternatives[i]-values[i] for i in common]
                output.append(dict(policy=policy,mode="diagnostic_1plus1",control="BASE:"+mode,year=y,session=s,side=d,anchor="original_actual_entry",episodes=len(ids),complete_pairs=len(common),missing_pairs=len(ids)-len(common),individual_pairs=len(individual),alternative_net_dollars=sum(alternatives[i] for i in common) if common else None,control_net_dollars=sum(values[i] for i in common) if common else None,total_difference=sum(diffs) if common else None,mean_difference=average(diffs),individual_mean_difference=average([alternatives[i]-values[i] for i in individual]),larger_exposure=True,not_equal_risk=True))
    return output


def forward_rows(records):
    output=[]
    for ema in (20,50):
        for horizon in (5,15,30,60):
            for group in ("all","first","second","third_or_more","unknown"):
                for y,s,d in dimensions():
                    rows=[r for r in records if r["ema"]==ema and r["horizon_minutes"]==horizon and (group=="all" or r["contact_group"]==group) and match(r,y,s,d)]
                    valid=[r for r in rows if r["status"]=="observed"]
                    output.append({"ema":ema,"horizon_minutes":horizon,"contact_group":group,"year":y,"session":s,"side":d,"anchor":"EMA_decision_event","events":len(rows),"observed":len(valid),"censored":len(rows)-len(valid),"distinct_episodes":len({r["episode_id"] for r in rows}),"mean_signed_points":average([r["signed_points"] for r in valid]),"mean_mfe_points":average([r["mfe_points"] for r in valid]),"mean_mae_points":average([r["mae_points"] for r in valid]),"not_trade_return":True})
    return output


def transition_rows(events,trades,parents):
    """Independent original/event/actual-add anchors, with unfilled add unknown."""
    output=[]
    candidates=[e for e in events if e.get("event") in {"first_contact_consumed","ema_exit_signal","trail_future_activation","trail_already_breached_next_open_exit"}]
    adds={(t["episode_id"],t["policy"],t["mode"]):t for t in trades if t.get("leg")=="add"}
    for p,m in sorted({key(e) for e in candidates}):
        group=[e for e in candidates if key(e)==(p,m)]
        for y in YEARS:
            for d in SIDES:
                for first in SESSIONS:
                    for event_session in SESSIONS:
                        rows=[e for e in group if (y=="all" or anchor(e["time"],parents[e["episode_id"]]["direction"])["year"]==y) and (d=="combined" or anchor(e["time"],parents[e["episode_id"]]["direction"])["side"]==d) and session_at(parents[e["episode_id"]]["entry_time"])==first and session_at(e["time"])==event_session]
                        for addsession in (*SESSIONS,"unfilled"):
                            chosen=[e for e in rows if (session_at(adds[(e["episode_id"],p,m)]["entry_time"]) if (e["episode_id"],p,m) in adds else "unfilled")==addsession]
                            output.append({"policy":p,"mode":m,"year":y,"side":d,"anchor":"EMA_event_year","original_session":first,"event_session":event_session,"add_session":addsession,"events":len(chosen),"distinct_episodes":len({e["episode_id"] for e in chosen}),"add_fills":sum((e["episode_id"],p,m) in adds for e in chosen)})
    return output


def exit_tradeoff_rows(episodes,parents):
    output=[]
    for p in ("X1","X2","T50"):
        for y,s,d in dimensions():
            rows=[r for r in episodes if r["policy"]==p and r["mode"]=="standardized" and match(anchor(parents[r["episode_id"]]["entry_time"],parents[r["episode_id"]]["direction"]),y,s,d)]
            pairs=[r for r in rows if pnl(r) is not None and parents[r["episode_id"]].get("net_dollars") is not None]
            loser=[r for r in pairs if parents[r["episode_id"]]["net_dollars"]< -1e-8]
            winner=[r for r in pairs if parents[r["episode_id"]]["net_dollars"]>1e-8]
            delta=lambda r:pnl(r)-parents[r["episode_id"]]["net_dollars"]
            output.append({"policy":p,"year":y,"session":s,"side":d,"anchor":"original_actual_entry","episodes":len(rows),"complete_pairs":len(pairs),"missing_pairs":len(rows)-len(pairs),"parent_losers":len(loser),"losses_reduced":sum(delta(r)>1e-8 for r in loser),"losses_worsened":sum(delta(r)<-1e-8 for r in loser),"loss_dollars_saved":sum(max(0,delta(r)) for r in loser),"parent_winners":len(winner),"winners_cut_short":sum(delta(r)<-1e-8 for r in winner),"profit_surrendered_dollars":sum(max(0,-delta(r)) for r in winner),"improved":sum(delta(r)>1e-8 for r in pairs),"deteriorated":sum(delta(r)<-1e-8 for r in pairs),"mean_difference":average([delta(r) for r in pairs]),"mean_time_saved_minutes":average([r.get("time_saved_minutes") for r in pairs]),"mean_post_exit_favorable_points":average([r.get("post_exit_favorable_points") for r in pairs])})
    return output


def exposure_paths(exposure,parents):
    """History MTM keeps closed episodes and within-minute peak/trough order."""
    output=[]
    groups=defaultdict(lambda:defaultdict(list))
    for r in exposure: groups[key(r)][r["episode_id"]].append(r)
    for (p,m),episodes in groups.items():
        cumulative=peak=0.
        for eid,rows in sorted(episodes.items(),key=lambda item:parents[item[0]]["entry_time"]):
            rows.sort(key=lambda r:r["time"])
            for r in rows:
                low=cumulative+r["intraminute_mtm_min"];high=cumulative+r["intraminute_mtm_max"]
                # Native saved within-minute drawdown already preserves path;
                # cross-episode high carried before each minute is independent.
                worst=max(peak-low,r.get("max_mtm_drawdown",0))
                peak=max(peak,high)
                mtm=cumulative+r["mtm_net_dollars"]
                output.append({"policy":p,"mode":m,"episode_id":eid,"time":r["time"],"history_mtm_net_dollars":mtm,"history_mtm_drawdown_dollars":max(worst,peak-mtm),"notional":r["notional"],"concurrent_legs":r["concurrent_legs"],"combined_active_stop_risk":r["combined_active_stop_risk"]})
            # A censored episode cannot imply a known later closed equity path.
            if rows and rows[-1].get("active_quantity",0): break
            if rows: cumulative+=rows[-1]["closed_net_dollars"]
    return output


def stream_exposure_paths(exposure,parents,outcomes=None):
    """Equivalent history projection from chronologically streamed policy rows.

    A policy's unknown open equity prefix stops its later known-history path.
    Other independent policies remain observable; no rows from another policy
    or cost scenario share accumulated capital/P&L.
    """
    states={};unknown_first={}
    for (p,m,eid),value in (outcomes or {}).items():
        if value is None:
            date=parents[eid]["entry_time"];unknown_first[(p,m)]=min(date,unknown_first.get((p,m),date))
    for r in exposure:
        p,m=key(r);eid=r["episode_id"]
        state=states.setdefault((p,m),dict(episode=None,cumulative=0.,peak=0.,last=None,blocked=False,last_entry=None))
        if (p,m) in unknown_first and parents[eid]["entry_time"]>unknown_first[(p,m)]:state["blocked"]=True
        if eid!=state["episode"]:
            if state["last"] is not None:
                if state["last"].get("active_quantity",0) or outcomes is not None and outcomes.get((p,m,state["episode"])) is None:state["blocked"]=True
                else:state["cumulative"]+=state["last"]["closed_net_dollars"]
            entry=parents[eid]["entry_time"]
            if state["last_entry"] and entry<state["last_entry"]:raise ValueError("streamed exposure is not chronological")
            state.update(episode=eid,last_entry=entry)
        state["last"]=r
        if state["blocked"]:continue
        cumulative,peak=state["cumulative"],state["peak"]
        low=cumulative+r["intraminute_mtm_min"];high=cumulative+r["intraminute_mtm_max"]
        worst=max(peak-low,r.get("max_mtm_drawdown",0));peak=max(peak,high)
        state["peak"]=peak
        mtm=cumulative+r["mtm_net_dollars"]
        yield {"policy":p,"mode":m,"episode_id":eid,"time":r["time"],"history_mtm_net_dollars":mtm,"history_mtm_drawdown_dollars":max(worst,peak-mtm),"notional":r["notional"],"concurrent_legs":r["concurrent_legs"],"combined_active_stop_risk":r["combined_active_stop_risk"]}


def exposure_cohorts(exposure,parents,episodes):
    outcomes={(r["policy"],r["mode"],r["episode_id"]):pnl(r) for r in episodes}
    states={};unknown_first={}
    for row in episodes:
        if pnl(row) is not None:continue
        p,m=key(row);eid=row["episode_id"];date=parents[eid]["entry_time"];a=anchor(date,parents[eid]["direction"])
        for y in ("all",a["year"]):
            for s in ("all",a["session"]):
                for d in ("combined",a["side"]):
                    k=(p,m,y,s,d);unknown_first[k]=min(date,unknown_first.get(k,date))
    for r in exposure:
        p,m=key(r);eid=r["episode_id"];a=anchor(parents[eid]["entry_time"],parents[eid]["direction"])
        for y in ("all",a["year"]):
            for s in ("all",a["session"]):
                for d in ("combined",a["side"]):
                    k=(p,m,y,s,d);state=states.setdefault(k,dict(episode=None,last=None,cumulative=0.,peak=0.,drawdown=0.,blocked=False,rows=0,notional=0.,stoprisk=0.,concurrent=0))
                    if k in unknown_first and parents[eid]["entry_time"]>unknown_first[k]:state["blocked"]=True
                    if state["episode"]!=eid:
                        if state["last"] is not None:
                            if outcomes[(p,m,state["episode"])] is None:state["blocked"]=True
                            else:state["cumulative"]+=outcomes[(p,m,state["episode"])]
                        state["episode"]=eid
                    state["last"]=r
                    if state["blocked"]:continue
                    peak=state["peak"];low=state["cumulative"]+r["intraminute_mtm_min"];high=state["cumulative"]+r["intraminute_mtm_max"]
                    state["drawdown"]=max(state["drawdown"],peak-low,r.get("max_mtm_drawdown",0),max(peak,high)-(state["cumulative"]+r["mtm_net_dollars"]))
                    state["peak"]=max(peak,high);state["rows"]+=1
                    state["notional"]=max(state["notional"],r["notional"]);state["stoprisk"]=max(state["stoprisk"],r["combined_active_stop_risk"]);state["concurrent"]=max(state["concurrent"],r["concurrent_legs"])
    result=[]
    for p,m in sorted({key(r) for r in episodes}):
        for y,s,d in dimensions():
            state=states.get((p,m,y,s,d));selected=[r for r in episodes if key(r)==(p,m) and match(anchor(parents[r["episode_id"]]["entry_time"],parents[r["episode_id"]]["direction"]),y,s,d)]
            unknown=sum(pnl(r) is None for r in selected)
            observed_dd=state["drawdown"] if state else 0. if selected and all(r["status"]=="no_fill" for r in selected) else None
            result.append({"policy":p,"mode":m,"year":y,"session":s,"side":d,"anchor":"original_actual_entry","episodes":len(selected),"unknown_episode_equity":unknown,"observed_mtm_rows":state["rows"] if state else 0,"mtm_drawdown_dollars":observed_dd if not unknown else None,"observed_prefix_mtm_drawdown_dollars":observed_dd,"full_path_known":bool(selected and not unknown),"peak_notional":state["notional"] if state else 0. if selected and not unknown else None,"peak_active_stop_risk":state["stoprisk"] if state else 0. if selected and not unknown else None,"peak_concurrent_legs":state["concurrent"] if state else 0 if selected and not unknown else None,"within_year_path":y!="all"})
    return result


def profile_values(snapshot, direction):
    if not snapshot.get("known"):
        return {"availability":"unknown"}
    direction_state = snapshot.get("direction")
    alignment = "neutral" if direction_state == 0 else "aligned" if direction_state == direction else "opposed"
    def bins(v, edges):
        if v is None: return "unknown"
        if v < edges[0]: return "below_" + str(edges[0])
        for a,b in zip(edges,edges[1:]):
            if v < b: return f"[{a},{b})"
        return ">="+str(edges[-1])
    s20,s50 = snapshot.get("slope20_3"), snapshot.get("slope50_3")
    slopes = "unknown" if s20 is None or s50 is None else "both_aligned" if direction*s20>0 and direction*s50>0 else "both_opposed" if direction*s20<0 and direction*s50<0 else "mixed_or_flat"
    change = snapshot.get("width_change_3")
    return {"availability":"known","ordering":alignment,"price_position":snapshot.get("price_cloud","unknown"),"slopes":slopes,
        "width_atr":bins(snapshot.get("width_atr"),[0,.25,.5,1,2]),"distance_atr":bins(snapshot.get("favorable_distance_atr"),[0,.5,1,2]),
        "aligned_duration":"left_censored" if snapshot.get("duration_left_censored") else bins(snapshot.get("aligned_count"),[1,4,13,37]),
        "width_change":"unknown" if change is None else "expanding" if change>0 else "contracting" if change<0 else "equal",
        **{f"confluence_ema{length}_{level}":"yes" if snapshot.get(f"ema{length}_{name}_confluence") is True else "no" if snapshot.get(f"ema{length}_{name}_confluence") is False else "unknown" for length in (20,50) for level,name in (("H","high"),("L","low"),("M","midpoint"))}}


def profile_rows(observations, parents, calendar, *, intervals=True):
    """Episode outcomes conditional on an available original decision snapshot.

    Open landmarks carry frequency support rather than treating repeated rows
    as independent trades. Four-week episode draws retain repeated membership.
    """
    buckets = defaultdict(list)
    for item in observations:
        eid = item["episode_id"]
        direction = parents[eid]["direction"]
        cohort = anchor(item["decision_at"], direction)
        for name, value in profile_values(item["snapshot"], direction).items():
            buckets[(item["anchor"],name,value)].append((eid,cohort))
    # Preserve prespecified categories even when a whole-history category has
    # no observations. Missing cloud is reported in availability, not imputed
    # into a known ordering or price state.
    roster={"availability":("known","unknown"),"ordering":("aligned","opposed","neutral"),
        "price_position":("above","inside","below"),"slopes":("both_aligned","both_opposed","mixed_or_flat","unknown"),
        "width_atr":("below_0","[0,0.25)","[0.25,0.5)","[0.5,1)","[1,2)",">=2","unknown"),
        "distance_atr":("below_0","[0,0.5)","[0.5,1)","[1,2)",">=2","unknown"),
        "aligned_duration":("below_1","[1,4)","[4,13)","[13,37)",">=37","left_censored","unknown"),
        "width_change":("expanding","contracting","equal","unknown"),
        **{f"confluence_ema{ema}_{level}":("yes","no","unknown") for ema in (20,50) for level in ("H","L","M")}}
    for a in {r["anchor"] for r in observations}:
        for feature,values in roster.items():
            for value in values:buckets.setdefault((a,feature,value),[])
    result=[]
    for (a,name,value),members in sorted(buckets.items()):
        for y,s,d in dimensions():
            filtered=[eid for eid,c in members if match(c,y,s,d)]
            ids=sorted(set(filtered))
            known=[i for i in ids if parents[i]["status"]=="completed"]
            vals=[parents[i]["net_dollars"] for i in known]
            vectors=[(parents[i]["broker_day"],[parents[i].get("net_dollars")]) for i in ids]
            cis=block_intervals(vectors,calendar_subset(calendar,y)) if intervals and a in {"original_order_decision","original_entry"} else []
            result.append({"anchor":a,"feature":name,"bucket":value,"year":y,"session":s,"side":d,"observations":len(filtered),"distinct_episodes":len(ids),"completed_parent_episodes":len(vals),"unknown_parent_episodes":len(ids)-len(vals),
                "parent_net_dollars":sum(vals) if vals else None,"mean_parent_net_dollars":average(vals),"parent_win_rate":ratio(sum(v>1e-8 for v in vals),len(vals)),
                **{f"mean_parent_{field}":average([parents[i].get(field) for i in known]) if a in {"original_order_decision","original_entry"} else None for field in ("mfe_points","mae_points","holding_minutes")},
                "mean_low":cis[0]["difference_low"] if cis else None,"mean_high":cis[0]["difference_high"] if cis else None,"conditional_population":a=="eligible_open_position_landmark","not_calibrated_probability":True})
    return result


def selection(paired, episodes, trades, parents):
    output=[]
    for p in CORE:
        values=[r for r in paired if r["policy"]==p and r["year"] in {"2021","2022","2023"} and r["session"]=="all" and r["side"]=="combined"]
        # Validation mean/interval is computed together over the full interval
        # by the caller, never averaged across annual confidence intervals.
        validation=next((r for r in paired if r["policy"]==p and r["year"]=="validation" and r["session"]=="all" and r["side"]=="combined"),None)
        filled=[t for t in trades if t["policy"]==p and t["mode"]==policy_mode(p) and t["status"]=="completed" and anchor(parents[t["episode_id"]]["entry_time"],parents[t["episode_id"]]["direction"])["year"] in {"2021","2022","2023"}]
        ids={t["episode_id"] for t in filled}
        years=sorted({anchor(parents[i]["entry_time"],parents[i]["direction"])["year"] for i in ids})
        adds=[t for t in filled if t.get("leg")=="add"]
        addyears=sorted({anchor(parents[t["episode_id"]]["entry_time"],parents[t["episode_id"]]["direction"])["year"] for t in adds})
        qualifies=bool(validation and validation["mean_difference"] is not None and validation["mean_difference"]>0 and validation["adjusted_low"] is not None and validation["adjusted_low"]>0 and len(filled)>=100 and len(years)>=2 and (p not in {"A20","A50"} or len(adds)>=100 and len(addyears)>=2))
        output.append({"policy":p,"validation_complete_pairs":validation["complete_pairs"] if validation else 0,"mean_difference":validation["mean_difference"] if validation else None,"adjusted_low":validation["adjusted_low"] if validation else None,"completed_trades":len(filled),"validation_years_with_fills":years,"financed_add_fills":len(adds),"validation_years_with_financed_adds":addyears,"qualifies":qualifies})
    def best(policies):
        eligible=[r for r in output if r["policy"] in policies and r["qualifies"]]
        return max(eligible,key=lambda r:(r["mean_difference"],-policies.index(r["policy"]))) ["policy"] if eligible else None
    return {"candidates":output,"selected_gate":best(["G1","G2"]),"selected_exit":best(["X1","X2"]),"selected_adds":[r["policy"] for r in output if r["policy"] in {"A20","A50"} and r["qualifies"]],"combined_policy":None,"later_outcomes_opened":False,"prior_exposure":True}


def period_rows(episodes,parents,calendar):
    groups={"development":{2018,2019,2020},"validation":{2021,2022,2023},"later":{2024,2025},"replication":{2026}}
    output=[];sensitivities=[]
    for name,years in groups.items():
        sub={i:t for i,t in parents.items() if int(anchor(t["entry_time"],t["direction"])["year"]) in years}
        if not sub: continue
        rows=[r for r in episodes if r["episode_id"] in sub]
        dates=[d for d in calendar if f"{min(years)}-01-01"<=d<=f"{max(years)+1}-01-01"]
        paired,effects,common=paired_rows(rows,sub,dates,cohorts=(("all",s,d) for s in ("all",*SESSIONS) for d in SIDES))
        for r in paired:
            if r["year"]=="all":output.append(dict(r,period=name,year=name))
        for d in SIDES:
            ids=[i for i in sub if d=="combined" or anchor(sub[i]["entry_time"],sub[i]["direction"])["side"]==d]
            vectors=[(sub[i]["broker_day"],effects[i] if common[i] else [None]*6) for i in ids]
            for weeks in (1,4,8):
                cis=block_intervals(vectors,dates,weeks=weeks)
                for index,p in enumerate(CORE):
                    values=[effects[i][index] for i in ids if common[i]]
                    sensitivities.append({"policy":p,"period":name,"side":d,"block_weeks":weeks,"episodes":len(ids),"complete_pairs":len(values),"mean_difference":average(values),**(cis[index] if cis else {k:None for k in ("difference_low","difference_high","adjusted_low","adjusted_high")}),"adjusted_confidence":CORRECTED,"anchor":"original_actual_entry"})
    return output,sensitivities


def save_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")


def aggregate(stage,*,phase="all"):
    """Materialize saved tables; chronological selection is a separate action."""
    stage=Path(stage)
    names=("dev-validation","later") if phase=="all" else (phase,)
    buckets={name:[] for name in ("episodes","events","orders","trades","exposure","monitoring","profiles","phase2-context")}
    for name in names:
        folder=stage/"phases"/name
        if not (folder/"completion.json").is_file():raise ValueError("phase not complete")
        for ledger in buckets:
            if ledger=="exposure":continue
            path=folder/(ledger+".jsonl.gz")
            if path.exists():
                if ledger in {"monitoring","profiles","phase2-context"}:
                    buckets[ledger].extend(r for r in iter_ledger(path) if r.get("scenario","primary-one-tick")=="primary-one-tick")
                else:buckets[ledger].extend(read_ledger(path))
    parentpath=stage/"parents"/"baseline-trades.jsonl.gz"
    parents={r.get("episode_id",r["trade_id"]):r for r in read_ledger(parentpath)}
    if phase!="all":
        selected={r["episode_id"] for r in buckets["episodes"]}
        parents={i:t for i,t in parents.items() if i in selected}
    calendar=[r["broker_day"] for r in read_ledger(stage/"parents"/"calendar-roster.jsonl.gz")]
    primary=lambda rows:[r for r in rows if r.get("scenario","primary-one-tick")=="primary-one-tick"]
    episodes,trades,events,monitoring=map(primary,(buckets["episodes"],buckets["trades"],buckets["events"],buckets["monitoring"]))
    paired,_,_=paired_rows(episodes,parents,calendar)
    periods,sensitivity=period_rows(episodes,parents,calendar)
    tradecohorts,equity,timing=trade_rows(trades,episodes,parents)
    contacts,forward=contact_diagnostics(monitoring,parents)
    profiles=buckets["profiles"]
    if not profiles:
        for r in episodes:
            if key(r)!=("BASE","parent_1"):continue
            parent=parents[r["episode_id"]]
            for a,field,at in (("original_order_decision","original_order_snapshot",parent["order_submitted_at"]),("original_entry","entry_snapshot",parent["entry_time"])):
                profiles.append({"episode_id":r["episode_id"],"decision_at":at,"anchor":a,"snapshot":r[field]})
        profiles.extend({"episode_id":r["episode_id"],"decision_at":r["available_at"],"anchor":"eligible_open_position_landmark","snapshot":r["current"]} for r in monitoring if r["open_position_landmark"])
    profiles.extend(buckets["phase2-context"])
    tables={"paired":paired,"periods":periods,"interval-sensitivities":sensitivity,"trade-cohorts":tradecohorts,"equity":equity,"timing":timing,
        "risk":risk_rows(episodes,parents),"exposure-controls":exposure_control_rows(episodes,parents),"profiles":profile_rows(profiles,parents,calendar),"contacts":contact_rows(contacts,monitoring),"confluence":confluence_rows(contacts),"forward":forward_rows(forward),
        "transitions":transition_rows(events,trades,parents),"exit-tradeoffs":exit_tradeoff_rows(episodes,parents)}
    # Sensitivities retain the same fixed original roster and known/null masks;
    # matching saved scenario parents are loaded from runner scenario controls.
    scenarios=[]
    for scenario in sorted({r.get("scenario","primary-one-tick") for r in buckets["episodes"]}):
        rows=[dict(r,scenario="primary-one-tick") for r in buckets["episodes"] if r.get("scenario","primary-one-tick")==scenario]
        summarized,_,_=paired_rows(rows,parents,calendar,intervals=False)
        scenarios.extend(dict(r,scenario=scenario) for r in summarized if r["year"]=="all" and r["session"]=="all")
    tables["scenarios"]=scenarios
    snapshots=[]
    for row in profiles:
        state=row["snapshot"]
        snapshots.append({"episode_id":row["episode_id"],"anchor":row["anchor"],"decision_at":row["decision_at"],**anchor(row["decision_at"],parents[row["episode_id"]]["direction"]),**{k:state.get(k) for k in ("known","expected_slot","available_at","reason","ema20","ema50","atr14","close","slope20_3","slope50_3","aligned_count","alignment_start_known","duration_left_censored","width_points","width_atr","favorable_distance_atr","width_change_3","price_cloud")}})
    tables["decision-snapshots"]=snapshots
    output=stage/"tables" if phase=="all" else stage/"phases"/phase/"tables"
    if output.exists():raise FileExistsError("preserve earlier numerical outputs")
    for name,rows in tables.items():
        if rows:write_csv(output/(name+".csv"),rows)
    diagnosticfolder=stage/"diagnostics" if phase=="all" else stage/"phases"/phase/"diagnostics"
    diagnosticfolder.mkdir(parents=True,exist_ok=False)
    def exposure_stream():
        for phase_name in names:
            for row in iter_ledger(stage/"phases"/phase_name/"exposure.jsonl.gz"):
                if row.get("scenario","primary-one-tick")=="primary-one-tick":yield row
    outcomes={(r["policy"],r["mode"],r["episode_id"]):pnl(r) for r in episodes}
    for name,rows in (("contacts",contacts),("forward",forward),("exposure-path",stream_exposure_paths(exposure_stream(),parents,outcomes))):
        with gzip.open(diagnosticfolder/(name+".jsonl.gz"),"xt") as f:
            for row in rows:f.write(json.dumps(row,allow_nan=False,separators=(",",":"))+"\n")
    floating=exposure_cohorts(exposure_stream(),parents,episodes)
    write_csv(output/"floating.csv",floating);tables["floating"]=floating
    if phase=="dev-validation":
        decision=selection([*paired,*periods],episodes,trades,parents)
        save_json(stage/"selection-candidate.json",decision)
    completion={"phase":phase,"episodes":len(parents),"tables":{name:len(rows) for name,rows in tables.items()},"all_accepted_roster_retained":True,"core_policy_controls":{p:":".join(control(p)) for p in CORE},"interval_replications":10000,"seed":230015}
    save_json(output/"completion.json",completion)
    return completion



def read_ledger(path):
    opener=gzip.open if str(path).endswith(".gz") else open
    with opener(path,"rt") as f:
        return [json.loads(line) for line in f]


def iter_ledger(path):
    opener=gzip.open if str(path).endswith(".gz") else open
    with opener(path,"rt") as f:
        for line in f:yield json.loads(line)


def write_csv(path, rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not rows: raise ValueError("empty schema requires explicit zero-support rows")
    columns=list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=columns)
        writer.writeheader();writer.writerows(rows)


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",type=Path,required=True)
    parser.add_argument("--phase",choices=("dev-validation","all"),default="all")
    args=parser.parse_args()
    print(json.dumps(aggregate(args.stage,phase=args.phase),indent=2))

