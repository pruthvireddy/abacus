#!/usr/bin/env python3
"""Independent native-source reconstruction for the Study 30 ranked extension.

Imports neither ranked_engine nor ranked_statistics. Numerical source and path
helpers come from the independently maintained baseline checker. Bootstrap
intervals are checked for support/order and algorithm tests, not re-estimated.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date, timedelta
import json
import math
from pathlib import Path
import sys

STUDY = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY / "src"))
import verify_saved as independent

MATCHED, RTH, GLOBEX = "pivot_matched_rth", "vwap_only_rth", "vwap_only_full_globex"
SECTIONS = (("opening_range", 570, 630), ("new_york_am", 630, 750), ("new_york_pm", 750, 960))


def _members(row, mode=None):
    mode = mode or row.get("session_mode", "rth")
    return row.get("cohorts_by_mode", {}).get(mode, row.get("cohorts", []))


def _side(value, reference):
    return None if value is None or reference is None else (value > reference) - (value < reference)


def _scan(day, contract, minutes, bars, pivot, mode, reference, series):
    start = independent.clock(day, 570) if mode == "rth" else independent.clock((date.fromisoformat(day)-timedelta(days=1)).isoformat(), 1080)
    end = independent.clock(day, 960 if mode == "rth" else 1020)
    by_open = {r["open_time"]: r for r in minutes}
    minute_close = {r["close_time"]: r for r in minutes}
    by_close = {r["close_time"]: r for r in bars}
    seed = independent.point(by_open.get(start), "open") if series == "price" else independent.point(by_close.get(start), "ema6", "ema6_ready")
    line = pivot if reference == "pivot" else independent.point(minute_close.get(start), "vwap", "vwap_valid")
    remembered = _side(seed, line) if mode == "rth" else None
    remembered = remembered or None
    previous, vector, valid = start, [], {}
    pause_start,pause_end=(independent.clock(day,975),independent.clock(day,990))
    for bar in bars:
        if not start <= bar["open_time"] < end:
            continue
        pause = day < "2021-06-28" and previous == pause_start and bar["open_time"] == pause_end
        if bar["open_time"] != previous and not pause:
            remembered = None
        previous = bar["close_time"]
        amount = independent.point(bar, "close") if series == "price" else independent.point(bar, "ema6", "ema6_ready")
        line = pivot if reference == "pivot" else independent.point(minute_close.get(previous), "vwap", "vwap_valid")
        side = _side(amount, line)
        valid[previous] = side is not None
        if side is None:
            remembered = None
        elif side:
            if remembered is not None and side != remembered:
                vector.append({"observed_at": previous.isoformat(), "bar_open": bar["open_time"].isoformat(),
                               "direction": side, "reference_price": independent.point(bar, "close"),
                               "reference_line_value": line, "crossing_value": amount,
                               "difference": amount-line, "previous_strict_side": remembered})
            remembered = side
    return vector, valid


def _pair_complete(start, end, valid):
    cursor = start + timedelta(minutes=3)
    while cursor <= end:
        if not valid.get(cursor, False):
            return False
        cursor += timedelta(minutes=3)
    return True


def verify_cohort(day,q,minutes,three,five,coverage):
    """Readiness is reconstructed before selecting any event/outcome labels."""
    if q is None:
        independent.equal(coverage["vwap_only_rth"],False,"absent RTH cohort")
        independent.equal(coverage["vwap_only_full_globex"],False,"absent Globex cohort")
        return
    minutes,three,five=(independent.series_records(r) for r in (minutes,three,five))
    by_open={r["open_time"]:r for r in minutes}
    fast_open={r["open_time"]:r for r in three};slow_open={r["open_time"]:r for r in five}
    anchor=independent.clock((date.fromisoformat(day)-timedelta(days=1)).isoformat(),1080)
    start,end=independent.clock(day,570),independent.clock(day,960)
    complete=True;cursor=anchor
    while cursor<end:
        row=by_open.get(cursor)
        if any(independent.point(row,k) is None for k in ("open","high","low","close")):complete=False;break
        cursor+=timedelta(minutes=1)
    ready=True
    for rows,interval,fields,flag in ((fast_open,3,("ema6",),"ema6_ready"),(slow_open,5,("ema20","ema50"),"cloud_ready")):
        cursor=start
        while cursor<end:
            row=rows.get(cursor)
            if any(independent.point(row,k,flag) is None for k in fields) or any(independent.point(row,k) is None for k in ("open","high","low","close")):ready=False;break
            cursor+=timedelta(minutes=interval)
    minute_close={r["close_time"]:r for r in minutes}
    for clock in (565,570):
        at=independent.clock(day,clock)
        if independent.point(independent._asof(three,at,3),"ema6","ema6_ready") is None:ready=False
        for field in ("ema20","ema50"):
            if independent.point(independent._asof(five,at,5),field,"cloud_ready") is None:ready=False
        if independent.point(minute_close.get(at),"vwap","vwap_valid") is None:ready=False
    cursor=start
    while cursor<end:
        if independent.point(by_open.get(cursor),"vwap","vwap_valid") is None:ready=False;break
        cursor+=timedelta(minutes=1)
    expected_rth=bool(q.get("calendar_valid") and q.get("rth_complete") and q.get("anchor_to_rth_end_complete") and complete and ready)
    expected_full=bool(q.get("full_globex_complete") and three and minutes and all(independent.point(r,"ema6","ema6_ready") is not None for r in three) and all(independent.point(r,"vwap","vwap_valid") is not None for r in minutes))
    independent.equal(coverage["vwap_only_rth"],expected_rth,"independent RTH cohort")
    independent.equal(coverage["vwap_only_full_globex"],expected_full,"independent full Globex cohort")


def verify_day(day, contract, minutes, three, five, ranked, baseline):
    """Check every event, native exposure, outcome, recross and sequence for day."""
    counts = Counter()
    minutes, three, five = (independent.series_records(r) for r in (minutes, three, five))
    native = {r["open_time"]: r for r in minutes}
    pivot = next((r["pivot"] for r in baseline.get("daily", []) if r["session_date"] == day), None)
    opening_at=independent.clock(day,570)
    close_lookup={r["close_time"]:r for r in minutes}
    opening_price=independent.point(native.get(opening_at),"open")
    opening_vwap=independent.point(close_lookup.get(opening_at),"vwap","vwap_valid")
    opening_ema=independent.point(independent._asof(three,opening_at,3),"ema6","ema6_ready")
    def configuration(value):
        a,b=_side(value,pivot),_side(value,opening_vwap)
        return "unknown" if a is None or b is None else "equal" if a==0 or b==0 else "above_both" if a==b==1 else "below_both" if a==b==-1 else "between"
    separation=abs(pivot-opening_vwap) if pivot is not None and opening_vwap is not None else None
    bps=10000*separation/pivot if separation is not None and pivot>0 else None
    band="unknown" if bps is None else "<5" if bps<5 else "5–<15" if bps<15 else "15–<30" if bps<30 else "≥30"
    opening_expected={"opening_configuration":configuration(opening_price),"opening_ema6_configuration":configuration(opening_ema),"opening_separation_points":separation,"opening_separation_bps":bps,"opening_separation_band":band}
    for table in ("daily","sections","events","outcomes","recrosses","sequences"):
        for row in ranked.get(table,[]):
            if row["session_date"]!=day:continue
            for field,value in opening_expected.items():
                if field in row:
                    independent.equal(row[field],value,"opening configuration/separation/"+field)
                    counts["opening_cells"]+=1
    events = [r for r in ranked.get("events", []) if r["session_date"] == day]
    observed = [r for r in ranked.get("daily", []) if r["session_date"] == day]
    scans = {}
    physical_registry=defaultdict(dict)
    for row in observed:
        key = (row["session_mode"], row["reference"], row["series"])
        vector, valid = _scan(day, contract, minutes, three, pivot, *key)
        scans[key] = vector, valid
        for event in vector:
            physical_registry[(key[1],key[2],event["observed_at"])][key[0]]=sorted(row["cohorts"])
        selected = [r for r in events if r["reference"] == key[1] and r["series"] == key[2] and key[0] in r["scopes"]]
        selected.sort(key=lambda r: r["observed_at"])
        independent.require(len(selected) == len(vector), f"{day}/{key}: event count")
        for ordinal, (event, expected) in enumerate(zip(selected, vector), 1):
            for field, value in expected.items():
                independent.equal(event[field], value, f"{day}/{key}/{field}")
            independent.equal(sorted(event["cohorts_by_mode"][key[0]]),sorted(row["cohorts"]),"event cohort membership")
            independent.equal(event[f"{key[0]}_ordinal"], ordinal, "crossing ordinal")
            counts["events"] += 1
        for exposure in [row] + [r for r in ranked.get("sections", []) if r["session_date"] == day and (r["session_mode"], r["reference"], r["series"]) == key]:
            name = exposure["section"]
            if name == "all":
                a = independent.clock(day, 570) if key[0] == "rth" else independent.clock((date.fromisoformat(day)-timedelta(days=1)).isoformat(),1080)
                b = independent.clock(day, 960 if key[0] == "rth" else 1020)
            else:
                _, left, right = next(s for s in SECTIONS if s[0] == name)
                a, b = independent.clock(day, left), independent.clock(day, right)
            subset = [r for r in vector if a <= independent.instant(r["bar_open"]) < b]
            n = sum(a < at <= b and available for at, available in valid.items())
            expected = {"crosses": len(subset), "crosses_up": sum(r["direction"] == 1 for r in subset),
                        "crosses_down": sum(r["direction"] == -1 for r in subset), "observed_hours": n*3/60,
                        "valid_observations": n, "crosses_per_hour": len(subset)/(n*3/60) if n else None,
                        "first_cross_at": subset[0]["observed_at"] if subset else None,
                        "first_cross_direction": subset[0]["direction"] if subset else None}
            for field, value in expected.items():
                independent.equal(exposure[field], value, f"{day}/{key}/{name}/{field}")
                counts["exposure_cells"] += 1
    physical_keys=[(r["reference"],r["series"],r["observed_at"]) for r in events]
    independent.require(len(physical_keys)==len(set(physical_keys)),"duplicate physical crossing")
    independent.equal(sorted(physical_keys),sorted(physical_registry),"exact physical crossing registry")
    for event in events:
        key=(event["reference"],event["series"],event["observed_at"])
        expected_modes=physical_registry[key]
        independent.equal(sorted(event["scopes"]),sorted(expected_modes),"physical crossing scopes")
        independent.equal(event["event_id"],f"{day}:{contract}:ranked:{key[0]}:{key[1]}:{key[2]}","stable physical event identity")
        independent.equal(sorted(event["cohorts"]),sorted({c for cohorts in expected_modes.values() for c in cohorts}),"physical crossing cohort union")
    event_index = {r["event_id"]: r for r in events}
    end = independent.clock(day, 960)
    snapshots = {r["snapshot_id"]: r for r in ranked.get("snapshots", []) if r["session_date"] == day}
    for event in events:
        snap = snapshots.get(event["feature_snapshot_id"])
        independent.require(snap is not None, "missing event snapshot link")
        at = independent.instant(event["observed_at"])
        independent.equal(snap["snapshot_at"],at.isoformat(),"snapshot observation time")
        for field, value in independent.expected_context(at, event["reference_price"], pivot or 0., minutes, three, five).items():
            if pivot is None and "pivot" in field:
                continue
            independent.equal(event.get(field), value, f"{day}/event context/{field}")
        context=independent.expected_context(at,event["reference_price"],pivot or 0.,minutes,three,five)
        order=context["cloud_order"]
        slopes=[context["ema20_slope_15m"],context["ema50_slope_15m"]]
        direction=event["direction"]
        ordering=1 if order=="bullish" else -1 if order=="bearish" else 0
        support="unknown" if order=="unknown" or any(s is None for s in slopes) else "support" if ordering==direction and all(direction*s>0 for s in slopes) else "opposition" if ordering==-direction and all(direction*s<0 for s in slopes) else "mixed"
        independent.equal(event["cloud_support"],support,"native cloud support/opposition")
        for label, interval, rows, ready, fields in (("ema6", 3, three, "ema6_ready", ("ema6",)), ("cloud", 5, five, "cloud_ready", ("ema20", "ema50")), ("vwap",1,minutes,"vwap_valid",("vwap",))):
            source = independent._asof(rows, at, interval)
            independent.equal(snap[label+"_source_at"], source["close_time"].isoformat() if source else None, "snapshot completion time")
            for field in fields:
                independent.equal(snap[field], independent.point(source,field,ready), "snapshot value")
                counts["snapshot_cells"] += 1
    outcome_rows=[r for r in ranked.get("outcomes", []) if r["session_date"] == day]
    expected_outcomes=sorted((e["event_id"],h) for e in events if "rth" in e["scopes"] for h in ("15m","30m","60m","section_end","day_end"))
    independent.equal(sorted((r["event_id"],r["horizon"]) for r in outcome_rows),expected_outcomes,"complete forward outcome roster")
    for row in outcome_rows:
        event = event_index[row["event_id"]]
        for field in ("direction","section","first_per_day","first_per_section","cloud_support"):
            independent.equal(row[field],event[field],"outcome event context/"+field)
        independent.equal(sorted(row["cohorts"]),sorted(event["cohorts_by_mode"]["rth"]),"outcome cohort membership")
        independent.equal(row["reference_at"],event["observed_at"],"event-close outcome origin")
        independent.equal(row["reference_price"],event["reference_price"],"event-close outcome price")
        at=independent.instant(event["observed_at"])
        if row["horizon"] in ("15m","30m","60m"):endpoint=at+timedelta(minutes=int(row["horizon"][:-1]))
        elif row["horizon"]=="day_end":endpoint=end
        else:endpoint=independent.clock(day,next(right for name,_,right in SECTIONS if name==event["section"]))
        independent.equal(row["endpoint_at"],endpoint.isoformat(),"exact outcome horizon")
        independent.equal(row["feature_snapshot_id"], event["feature_snapshot_id"], "outcome snapshot link")
        expected = independent.reconstruct_path(observed=independent.instant(row["reference_at"]), reference=row["reference_price"], direction=row["direction"], endpoint=independent.instant(row["endpoint_at"]), day_end=end, by_open=native)
        for field, value in expected.items():
            independent.equal(row[field],value,"ranked forward path/"+field)
            counts["outcome_cells"] += 1
    recross_rows=[r for r in ranked.get("recrosses", []) if r["session_date"] == day]
    expected_recrosses=sorted((e["event_id"],h) for e in events if e["series"]=="ema6" and "rth" in e["scopes"] for h in ("15m","30m","60m"))
    independent.equal(sorted((r["event_id"],r["horizon"]) for r in recross_rows),expected_recrosses,"complete recross roster")
    for row in recross_rows:
        event = event_index[row["event_id"]]
        at = independent.instant(event["observed_at"])
        deadline = at + timedelta(minutes=int(row["horizon"][:-1]))
        vector, valid = scans[("rth",row["reference"],"ema6")]
        later = next((r for r in vector if independent.instant(r["observed_at"]) > at and r["direction"]==-event["direction"]), None)
        reverse = later is not None and independent.instant(later["observed_at"]) <= min(deadline,end)
        complete = _pair_complete(at,min(deadline,end),valid)
        expected = not reverse if complete and deadline <= end else None
        independent.equal(row["no_recross"], expected,"EMA recross versus price reversal")
        independent.equal(row["censored"], expected is None,"EMA recross censoring")
        independent.equal(row["valid"],expected is not None,"EMA recross validity")
        independent.equal(row["next_recross_at"],later["observed_at"] if later else None,"next EMA recross instant")
        independent.equal(row["next_recross_minutes"],(independent.instant(later["observed_at"])-at).total_seconds()/60 if later else None,"next EMA recross delay")
        counts["recrosses"] += 1
    sequence_rows=[r for r in ranked.get("sequences", []) if r["session_date"] == day]
    expected_sequences=sorted(e["event_id"] for e in events if e["series"]=="ema6" and MATCHED in _members(e,"rth"))
    independent.equal(sorted(r["event_id"] for r in sequence_rows),expected_sequences,"complete sequence roster")
    for row in sequence_rows:
        event = event_index[row["event_id"]]
        at = independent.instant(event["observed_at"]); deadline = at+timedelta(minutes=30)
        other = "vwap" if row["reference"] == "pivot" else "pivot"
        first, valid_first = scans[("rth",row["reference"],"ema6")]
        second_vector, valid_second = scans[("rth",other,"ema6")]
        simultaneous = any(r["observed_at"] == event["observed_at"] for r in second_vector)
        second = next((r for r in second_vector if at < independent.instant(r["observed_at"]) <= min(deadline,end) and r["direction"] == event["direction"]),None)
        reverse = next((r for r in first if at < independent.instant(r["observed_at"]) <= min(deadline,end) and r["direction"]==-event["direction"]),None)
        endpoint = min([independent.instant(r["observed_at"]) for r in (second,reverse) if r] or [min(deadline,end)])
        snap = snapshots[event["feature_snapshot_id"]]
        other_side = _side(snap["ema6"], pivot if other == "pivot" else snap["vwap"])
        if simultaneous: expected = "simultaneous"
        elif other_side is None: expected = "unknown_other_line"
        elif other_side == event["direction"]: expected = "already_beyond_other"
        elif other_side == 0: expected = "other_equal_at_start"
        elif not (_pair_complete(at,endpoint,valid_first) and _pair_complete(at,endpoint,valid_second)): expected = "censored_missing_observation"
        elif second and reverse and second["observed_at"] == reverse["observed_at"]: expected = "simultaneous_endpoint"
        elif second and (not reverse or second["observed_at"] < reverse["observed_at"]): expected = "second_before_recross"
        elif reverse: expected = "recross_first"
        elif deadline > end: expected = "censored_no_endpoint"
        else: expected = "neither_within_30m"
        independent.equal(row["result"],expected,"pivot/VWAP sequence ordering")
        independent.equal(row["second_cross_at"],second["observed_at"] if second else None,"paired second crossing time")
        independent.equal(row["first_recross_at"],reverse["observed_at"] if reverse else None,"paired first recross time")
        independent.equal(row["second_before_recross"],expected=="second_before_recross" if expected in ("second_before_recross","recross_first","neither_within_30m") else None,"paired traversal denominator")
        independent.equal(row["cohorts"],[MATCHED],"paired matched cohort")
        for flag in ("first_per_day","first_per_section"):
            independent.equal(row[flag],event[flag],"paired per-reference selection")
        counts["sequences"] += 1
    expected_transitions={}
    for reference in {r["reference"] for r in observed if r["session_mode"]=="rth"}:
        states=[]
        for name,_,clock in SECTIONS:
            at=independent.clock(day,clock)
            price=independent.point(close_lookup.get(at),"close")
            vwap=independent.point(close_lookup.get(at),"vwap","vwap_valid")
            fast=independent.point(independent._asof(three,at,3),"ema6","ema6_ready")
            cloud=independent.expected_context(at,price,pivot or 0.,minutes,three,five)["cloud_order"]
            line=pivot if reference=="pivot" else vwap
            states.append((name,{"price_side":_side(price,line),"ema6_side":_side(fast,line),"cloud_order":cloud}))
        for left,right in ((0,1),(1,2),(0,2)):
            for metric in ("price_side","ema6_side","cloud_order"):
                a,b=states[left][1][metric],states[right][1][metric]
                valid=a is not None and b is not None and a!="unknown" and b!="unknown"
                reversed_state=a==-b if valid and isinstance(a,int) and isinstance(b,int) and a!=0 and b!=0 else {a,b}=={"bullish","bearish"} if valid and metric=="cloud_order" else False if valid else None
                expected_transitions[(reference,states[left][0],states[right][0],metric)]={"from_state":a,"to_state":b,"valid":valid,"persistent":a==b if valid else None,"reversed":reversed_state}
    transitions=[r for r in ranked.get("transitions",[]) if r["session_date"]==day]
    independent.require(len(transitions)==len(expected_transitions),"native section transition roster")
    for row in transitions:
        key=(row["reference"],row["from_section"],row["to_section"],row["metric"])
        expected=expected_transitions.pop(key,None)
        independent.require(expected is not None,"duplicate/unexpected transition")
        for field,value in expected.items():
            independent.equal(row[field],value,"native section transition/"+field)
            counts["transition_cells"]+=1
    return counts


def _read_csv(path):
    text = {"period_kind","period","statistic_id","reference","series","session_mode","cohort","section","direction","panel","horizon","condition","condition_value","metric","unit","earliest_session","latest_session","requested_start","requested_cutoff"}
    def parse(key,value):
        if not value:return None
        if key in text:return value
        if value in ("True","False"):return value == "True"
        number = float(value)
        return int(number) if number.is_integer() else number
    with Path(path).open(newline="") as stream:
        return [{k:parse(k,v) for k,v in row.items()} for row in csv.DictReader(stream)]


def _source_indexes(ranked,baseline):
    """Index retained records once; no metric or eligibility is inferred here."""
    result={"events":{r["event_id"]:r for r in ranked.get("events",[])},
            "session":defaultdict(list),"price_pairs":{},"outcomes":defaultdict(list),
            "recrosses":defaultdict(list),"sequences":defaultdict(list),"transitions":defaultdict(list),
            "crossing_context":defaultdict(list),"confirmations":defaultdict(list)}
    for table in ("daily","sections"):
        for row in ranked.get(table,[]):
            for cohort in _members(row):
                result["session"][(row["reference"],row["series"],row["session_mode"],cohort)].append(row)
            if row["series"]=="price":
                key=tuple(row.get(k) for k in ("session_date","contract","reference","session_mode","section"))
                independent.require(key not in result["price_pairs"],"duplicate paired price exposure")
                result["price_pairs"][key]=row
    for raw in ranked.get("outcomes",[]):
        row={**result["events"].get(raw["event_id"],{}),**raw}
        for cohort in _members(row):result["outcomes"][(row["reference"],row["series"],row["horizon"],cohort)].append(row)
    for raw in ranked.get("recrosses",[]):
        row={**result["events"].get(raw["event_id"],{}),**raw}
        for cohort in _members(row):result["recrosses"][(row["reference"],row["horizon"],cohort)].append(row)
    for row in ranked.get("sequences",[]):
        for cohort in _members(row):result["sequences"][(row["reference"],cohort)].append(row)
    for row in ranked.get("transitions",[]):
        label=f"{row['from_section']}→{row['to_section']}:{row['metric']}:{row['from_state']}"
        for cohort in _members(row):result["transitions"][(row["reference"],row["series"],cohort,label)].append(row)
    for row in ranked.get("events",[]):
        if "rth" in row["scopes"]:
            for cohort in _members(row,"rth"):result["crossing_context"][(row["reference"],row["series"],cohort)].append(row)
    baseline_events={r["event_id"]:r for r in baseline.get("price_events",[])}
    for raw in baseline.get("outcomes",[]):
        if raw.get("event_type")=="ema_confirmation":
            row={**baseline_events.get(raw["event_id"],{}),**raw}
            result["confirmations"][(row["horizon"],row.get("confirmation_kind") or "unknown")].append(row)
    return result


def _source_candidates(summary, ranked, baseline, indexes=None):
    """Derive each displayed estimand independently from underlying evidence."""
    stat, metric = summary["statistic_id"], summary["metric"]
    if stat == "S20": stat = summary["condition_value"]
    reference, series, mode, cohort = (summary[k] for k in ("reference","series","session_mode","cohort"))
    condition, category = summary["condition"], summary["condition_value"]
    if summary["statistic_id"] == "S20":condition,category="all","all"
    indexes=indexes if indexes is not None else _source_indexes(ranked,baseline)
    values = []
    def append(row, value, censored=False):
        values.append((row,value,censored))
    if stat in ("S01","S02","S03","S04","S05","S12") or stat in ("S15","S17") and metric in ("crosses","opening_separation_points","opening_separation_bps"):
        source = indexes["session"].get((reference,series,mode,cohort),[])
        for row in source:
            if condition != "all" and condition not in ("cross_count","first_direction","minutes_from_session_start") and str(row.get(condition,"unknown")) != category:continue
            count,hours = row.get("crosses"),row.get("observed_hours")
            valid = independent.numeric(count) and independent.numeric(hours) and hours > 0
            if metric == "crosses":
                key = "crosses_up" if summary["direction"] == "up" else "crosses_down" if summary["direction"] == "down" else "crosses"
                value = row.get(key) if valid else None
            elif metric == "crosses_per_hour":value=count/hours if valid else None
            elif metric == "count_bucket":
                bucket="0" if count == 0 else "1" if count == 1 else "2" if count == 2 else "3–4" if count < 5 else "5+"
                value=bucket == category if valid else None
            elif metric == "additional_price_crosses":
                pair_key=tuple(row.get(k) for k in ("session_date","contract","reference","session_mode","section"))
                price=indexes["price_pairs"].get(pair_key)
                value=price["crosses"]-count if valid and price and price.get("observed_hours",0)>0 else None
            elif metric in ("opening_separation_points","opening_separation_bps"):value=row.get(metric)
            elif metric == "first_cross_minutes":
                at=independent.instant(row["first_cross_at"]).astimezone(independent.NY) if row.get("first_cross_at") else None
                value=(at.hour*60+at.minute-(1080 if mode=="globex" else 570))%1440 if at else None
            elif metric == "first_cross_direction":
                value=(count==0 if category=="no_cross" else row.get("first_cross_direction")== (1 if category=="up" else -1)) if valid else None
            elif metric == "first_cross_timing":
                if row.get("section") != "all":continue
                at=independent.instant(row["first_cross_at"]).astimezone(independent.NY) if row.get("first_cross_at") else None
                minute=(at.hour*60+at.minute-(1080 if mode=="globex" else 570))%1440 if at else None
                if category=="no_cross":value=count==0 if valid else None
                else:
                    if category.endswith(" inclusive"):left,right=map(int,category.removesuffix(" inclusive").split("–"))
                    else:left,right=map(int,category.split("–<"))
                    last=1380 if mode=="globex" else 390
                    value=(left<=minute<right or minute==last and right==last) if minute is not None else False if valid and count==0 else None
            else:raise ValueError("unknown session metric "+metric)
            append(row,value)
    elif stat=="S16" and metric=="crossing_context_share":
        for row in indexes["crossing_context"].get((reference,series,cohort),[]):
            append(row,row.get("cloud_support","unknown")==category)
    elif stat in ("S09","S10","S13","S15","S16","S17"):
        for row in indexes["outcomes"].get((reference,series,summary["horizon"],cohort),[]):
            if condition=="crossing_ordinal":
                ordinal=row.get("ordinal",row.get("rth_ordinal")); value="1" if ordinal==1 else "2" if ordinal==2 else "3+"
                if value!=category:continue
            elif condition!="all" and str(row.get(condition,"unknown"))!=category:continue
            displacement=row.get("displacement_points") if row.get("valid") is True else None
            if metric=="displacement":value=displacement
            elif metric=="positive_movement":value=displacement>0 if displacement is not None else None
            elif metric.endswith("_excursion"):value=row.get(metric+"_points") if row.get("valid") else None
            else:value=row.get(metric) if row.get("valid") else None
            append(row,value,not row.get("valid",False))
    elif stat=="S11":
        for row in indexes["recrosses"].get((reference,summary["horizon"],cohort),[]):
            delay=row.get("next_recross_minutes")
            append(row,row.get("no_recross") if metric=="no_recross" else delay if row.get("valid") is True and delay is not None and delay<=30 else None, row.get("no_recross") is None if metric=="no_recross" else bool(row.get("censored",False)))
    elif stat=="S14":
        for row in indexes["sequences"].get((reference,cohort),[]):
            if metric=="sequence_disposition":value=row["result"]==category;censored=bool(row.get("censored",False))
            else:
                if row["first_reference"]!=category:continue
                value=row.get("second_before_recross");censored=row.get("censored",False)
            append(row,value,censored)
    elif stat=="S19":
        for row in indexes["transitions"].get((reference,series,cohort,category),[]):
            append(row,row.get("persistent" if metric=="state_persists" else "reversed"))
    elif stat in ("S06","S07","S08","S18"):
        if stat=="S08" and metric.startswith("post_confirmation_"):
            for row in indexes["confirmations"].get((summary["horizon"],category),[]):
                displacement=row.get("displacement_points") if row.get("valid") is True else None
                append(row,displacement if metric=="post_confirmation_displacement" else displacement>0 if displacement is not None else None,not row.get("valid",False))
            return values
        source=baseline.get("ema_events" if stat=="S18" else "price_events",[])
        for row in source:
            resolved=row.get("confirmation_at") is not None or row.get("returned_at") is not None
            returned=row.get("returned_at") is not None and row.get("confirmation_at") is None
            if stat in ("S06","S07"):
                if row.get("ema_state_at_cross") not in ("opposite","equal_with_remembered_side","unavailable_uninitialized"):continue
                value=returned if resolved else None if stat=="S06" else None
                if stat=="S07":value=row.get("episode_penetration_points") if returned else None
                append(row,value,not resolved)
            elif stat=="S08":
                if (row.get("confirmation_kind") or "unconfirmed")!=category:continue
                key={"confirmation_delay":"confirmation_lag_minutes","movement_before_confirmation":"price_movement_to_confirmation_points","distance_at_confirmation":"confirmation_distance_from_pivot"}[metric]
                append(row,row.get(key),not resolved)
            else:
                complete=row.get("retest_window_complete") is True
                if metric=="pivot_retest":append(row,row.get("retest_found") if complete else None,not complete)
                elif metric=="time_to_retest":append(row,row.get("time_to_retest_minutes",row.get("retest_minutes")))
                else:append(row,row.get("retest_close_classification",row.get("retest_close_class"))==category if row.get("retest_found") is True else None)
    else:raise ValueError("unhandled statistic "+stat)
    return values


def verify_summaries(rows,ranked,baseline):
    counts=Counter();cache={};cohort_days={};period_days={};seen=set()
    indexes=_source_indexes(ranked,baseline)
    for cohort in (MATCHED,RTH,GLOBEX):
        cohort_days[cohort]=sorted({r["session_date"] for r in ranked.get("daily",[]) if cohort in _members(r)})
        if cohort==MATCHED and not cohort_days[cohort]:cohort_days[cohort]=sorted({r["session_date"] for r in baseline.get("daily",[])})
    for summary in rows:
        identity=tuple(summary.get(k) for k in ("statistic_id","reference","series","session_mode","cohort","period_kind","period","section","direction","panel","horizon","condition","condition_value","metric","unit"))
        independent.require(identity not in seen,"duplicate summary identity")
        seen.add(identity)
        cache_key=tuple(summary.get(k) for k in ("statistic_id","metric","reference","series","session_mode","cohort","condition","condition_value","horizon","direction"))
        if cache_key not in cache:
            by_date=defaultdict(list)
            for candidate in _source_candidates(summary,ranked,baseline,indexes):
                by_date[candidate[0]["session_date"]].append(candidate)
            cache[cache_key]=by_date
        source=cache[cache_key];days=cohort_days[summary["cohort"]]
        kind,period=summary["period_kind"],summary["period"]
        window_key=(summary["cohort"],kind,period)
        if window_key not in period_days:
            chosen=set(days)
            if kind=="year":chosen={d for d in days if d[:4]==period}
            elif kind=="calendar_month":chosen={d for d in days if d[:7]==period}
            elif kind in ("recent","preceding"):
                n=int(period.rsplit("_",1)[1]);recent=set(days[-n:]);chosen=recent if kind=="recent" else set(days)-recent
            period_days[window_key]=chosen
        chosen=period_days[window_key]
        picked=[]
        is_session=summary["statistic_id"] in ("S01","S02","S03","S04","S05","S12") or summary["metric"] in ("crosses","opening_separation_points","opening_separation_bps") or summary["statistic_id"]=="S20" and summary["condition_value"] in ("S01","S02","S04")
        for row,value,censored in (candidate for day in chosen for candidate in source.get(day,())):
            if summary["section"]!="all" and row.get("section")!=summary["section"]:continue
            if is_session and summary["section"]=="all" and row.get("section","all")!="all":continue
            if not is_session and summary["direction"]!="all" and row.get("direction")!=(1 if summary["direction"]=="up" else -1):continue
            panel=summary["panel"]
            if panel!="all_crosses" and row.get(panel) is not True and not (panel=="first_per_day" and row.get("ordinal",row.get("rth_ordinal"))==1):continue
            picked.append((row,value,censored))
        valid=[(r,float(v)) for r,v,_ in picked if independent.numeric(v) or isinstance(v,bool)]
        numbers=[v for _,v in valid];dates=sorted({r["session_date"] for r,_ in valid})
        expected={"numerator":sum(numbers),"denominator":len(valid),"days":len(dates),"candidates":len(picked),
                  "unknown":len(picked)-len(valid),"censored":sum(c for _,_,c in picked),
                  "estimate":sum(numbers)/len(numbers) if numbers else None,
                  "earliest_session":dates[0] if dates else None,"latest_session":dates[-1] if dates else None,"sparse":len(dates)<30}
        # Quantiles use independently spelled linear order interpolation.
        numbers.sort()
        for field,q in (("median",.5),("p25",.25),("p75",.75),("p90",.9)):
            pos=(len(numbers)-1)*q;left=int(pos);right=math.ceil(pos)
            expected[field]=numbers[left]+(numbers[right]-numbers[left])*(pos-left) if numbers else None
        for field,value in expected.items():
            independent.equal(summary[field],value,f"summary/{summary['statistic_id']}/{summary['metric']}/{field}")
            counts["summary_cells"]+=1
        low,high=summary.get("ci95_low"),summary.get("ci95_high")
        independent.require((low is None)==(high is None),"incomplete interval")
        if low is not None:independent.require(low<=high and len(dates)>=2 and len(days)>5,"invalid bootstrap support")
    counts["summary_rows"]=len(rows)
    return counts


def verify(stage,write=True):
    from ranked_lifecycle import load_inputs,read_ranked
    from lifecycle import read_ledgers,digest,dump,load
    stage=Path(stage)
    ranked,baseline=read_ranked(stage),read_ledgers(stage)
    _,grouped,quality=load_inputs(stage)
    counts=Counter()
    calendar=[];cursor=date(2020,1,1)
    while cursor<=date(2026,10,30):calendar.append(cursor.isoformat());cursor+=timedelta(days=1)
    coverage=ranked.get("coverage",[])
    independent.equal([r["session_date"] for r in coverage],calendar,"complete requested coverage roster")
    matched={r["session_date"] for r in baseline["daily"]}
    expected_daily=[];expected_sections=[]
    for row in coverage:
        day=row["session_date"]
        verify_cohort(day,quality.get(day),*(grouped[k].get(day,[]) for k in ("bars1","bars3","bars5")),row)
        independent.equal(row["pivot_matched_rth"],day in matched,"baseline matched cohort")
        rth_members=([MATCHED] if day in matched else [])+([RTH] if row["vwap_only_rth"] else [])
        for mode,members in (("rth",rth_members),("globex",[GLOBEX] if row["vwap_only_full_globex"] else [])):
            if not members:continue
            refs=["vwap"]+(["pivot"] if mode=="rth" and day in matched else [])
            for reference in refs:
                cohorts=members if reference=="vwap" else [MATCHED]
                for series in ("price","ema6"):
                    identity=(day,quality[day]["contract"],mode,reference,series,tuple(sorted(cohorts)))
                    expected_daily.append(identity)
                    if mode=="rth":expected_sections.extend((identity+(name,)) for name,_,_ in SECTIONS)
        counts["cohort_days"]+=1
    def identity(row):return (row["session_date"],row["contract"],row["session_mode"],row["reference"],row["series"],tuple(sorted(row["cohorts"])))
    independent.equal(sorted(identity(r) for r in ranked["daily"]),sorted(expected_daily),"complete daily cohort roster")
    independent.equal(sorted(identity(r)+(r["section"],) for r in ranked["sections"]),sorted(expected_sections),"complete section cohort roster")
    dates=sorted({r["session_date"] for r in ranked.get("daily",[])})
    # Partition evidence once. Passing only a day's rows preserves every native
    # reconstruction and tamper check while avoiding repeated whole-run scans.
    ranked_by_day=defaultdict(lambda:defaultdict(list))
    baseline_by_day=defaultdict(lambda:defaultdict(list))
    for table,records in ranked.items():
        for row in records:
            if "session_date" in row:ranked_by_day[row["session_date"]][table].append(row)
    for row in baseline.get("daily",[]):baseline_by_day[row["session_date"]]["daily"].append(row)
    for day in dates:
        counts.update(verify_day(day,quality[day]["contract"],*(grouped[k][day] for k in ("bars1","bars3","bars5")),ranked_by_day[day],baseline_by_day[day]))
    table=stage/"tables/ranked_summary.csv"
    counts.update(verify_summaries(_read_csv(table),ranked,baseline))
    receipt={"schema_version":"abacus.study30.ranked-independent/v1","status":"passed",
             "freeze_sha256":digest(stage/"freeze.json"),"ledger_sha256":load(stage/"ranked-execution.json")["ledger_sha256"],
             "ranked_execution_sha256":digest(stage/"ranked-execution.json"),
             "summary_tables":[{"path":"tables/ranked_summary.csv","sha256":digest(table)}],
             "checked":dict(counts),"actual_start":dates[0] if dates else None,"actual_end":dates[-1] if dates else None,
             "qualification":"Independent native event/exposure, completed snapshot, forward path, EMA recross, paired sequence and all summary numerator/denominator/support/quantile reconstruction. Bootstrap intervals not independently re-estimated; original vendor reconstruction remains unverified."}
    if write:dump(stage/"ranked-verification.json",receipt)
    return receipt


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("stage");args=parser.parse_args()
    print(json.dumps(verify(args.stage),indent=2))
