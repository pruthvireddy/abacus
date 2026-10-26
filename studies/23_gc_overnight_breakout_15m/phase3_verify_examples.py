"""Independent saved-case selection and raw empirical trace verification.

This post-execution presentation checker does not import any research producer,
exporter or selector. The frozen independent scientific checker supplies its
audited read-only input consumer and byte/typed-cell verification primitives.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import shutil
import sys

from phase3_verify import (VerificationError,compare,compare_csv,digest,instant,stamp,
    value,read_json,pin,verify_pin,ledger,verify_freeze,load_oracle_material,write_new)

RULES={"A20":("add_win","add_loss","rejected_support"),"A50":("add_win","add_loss","rejected_support"),
       "X1":("loss_saved","winner_cut_short"),"X2":("loss_saved","winner_cut_short")}


def case_qualifies(kind,parent,episode,trades,events):
    adds=[r for r in trades if r.get("leg")=="add" and r["status"]=="completed"]
    if kind=="add_win":return bool(adds and adds[0]["net_dollars"]>1e-8)
    if kind=="add_loss":return bool(adds and adds[0]["net_dollars"]<-1e-8)
    if kind=="rejected_support":
        return any(r["event"]=="first_contact_consumed" and (r["confirmed"] is False or r.get("liquidation_net") is not None and r["liquidation_net"]<=0) for r in events)
    a,b=episode.get("net_dollars"),parent.get("net_dollars")
    if a is None or b is None:return False
    if kind=="loss_saved":return b<-1e-8 and a>b+1e-8
    if kind=="winner_cut_short":return b>1e-8 and a<b-1e-8
    raise VerificationError("undeclared empirical case kind")


def selection_reference(parents,episodes,trades,events):
    indexed={(r["episode_id"],r["policy"],r["mode"]):r for r in episodes}
    legs=defaultdict(list);actions=defaultdict(list)
    for r in trades:legs[(r["episode_id"],r["policy"],r["mode"])].append(r)
    for r in events:actions[(r["episode_id"],r["policy"],r["mode"])].append(r)
    selected=[];absent=[]
    chronological=sorted(parents,key=lambda i:(instant(parents[i]["entry_time"]),i))
    for policy,kinds in RULES.items():
        mode="diagnostic_1plus1" if policy in {"A20","A50"} else "standardized"
        for kind in kinds:
            for direction in (1,-1):
                identifier=policy.lower()+"-"+kind.replace("_","-")+"-"+("long" if direction==1 else "short")
                chosen=None
                for eid in chronological:
                    if parents[eid]["direction"]!=direction:continue
                    k=(eid,policy,mode)
                    if k not in indexed:raise VerificationError("full original roster missing empirical policy episode")
                    if case_qualifies(kind,parents[eid],indexed[k],legs[k],actions[k]):chosen=eid;break
                if chosen is None:absent.append(dict(id=identifier,policy=policy,mode=mode,kind=kind,direction=direction,status="no_qualifying_saved_case"))
                else:selected.append(dict(id=identifier,episode_id=chosen,policy=policy,mode=mode,kind=kind,direction=direction))
    return selected,absent,indexed,legs,actions


def case_reference(record,day,parent,episode,trades,events):
    policy=record["policy"];signal=next((r for r in events if r["event"] in {"first_contact_consumed","ema_exit_signal"}),None)
    if signal is None:raise VerificationError("selected saved case lacks its first known causal signal")
    role="add" if policy in {"A20","A50"} else "original"
    action=next((r for r in trades if r.get("leg")==role and (role=="add" or r["status"]=="completed")),None)
    t=instant(signal["time"]);contact=t-timedelta(minutes=5)
    level=signal.get("frozen_level",signal.get("frozen_edge"));frozen_open=contact
    extra={}
    if policy=="X1":
        first=[r for r in events if r["event"]=="failure_first_close" and instant(r["time"])<t and r["frozen_edge"]==level]
        if not first:raise VerificationError("X1 figure has no known first frozen adverse edge")
        frozen_open=instant(first[-1]["time"])-timedelta(minutes=5);extra["frozen_level_contact_open"]=frozen_open.isoformat()
    prior=day.cloud.snapshot(frozen_open,day.contract)
    available=prior.bar.available_at.isoformat() if prior.known else None
    result={**record,"contract":parent["contract"],"leg":role,"parent_entry":parent["entry_time"],
        "parent_fill_upper":parent.get("entry_time_latest",parent["entry_time"]),"parent_entry_price":parent["entry_price"],
        "parent_initial_stop":parent["initial_stop"],"parent_reset_stop":parent.get("reset_stop"),"parent_reset_at":parent.get("reset_stop_active_at"),
        "parent_exit":parent.get("exit_time"),"parent_exit_price":parent.get("exit_price"),"parent_net_dollars":parent.get("net_dollars"),
        "signal_at":signal["time"],"contact_open":contact.isoformat(),"frozen_level":level,
        "liquidation_net":signal.get("liquidation_net",signal.get("original_liquidation_net")),
        "parent_open_at_signal":signal.get("parent_open",signal.get("original_open_at_signal")),"policy_net_dollars":episode.get("net_dollars"),
        "action_at":action["entry_time" if role=="add" else "exit_time"] if action else None,
        "action_price":action["entry_price" if role=="add" else "exit_price"] if action else None,
        "window_start":(instant(parent["entry_time"])-timedelta(minutes=15)).isoformat(),"window_end":day.cutoff.isoformat(),
        "legs":trades,"signal":signal,"range_high":day.high,"range_low":day.low,"midpoint":(day.high+day.low)/2,
        "frozen_level_available_at":available,**extra}
    if instant(result["parent_fill_upper"])>contact:raise VerificationError("empirical confirmation includes a partial pre-fill candle")
    if result["parent_open_at_signal"] is not True:raise VerificationError("empirical EMA action lacks known actual parent at confirmation close")
    if available is None or instant(available)>frozen_open:raise VerificationError("empirical frozen prior cloud was unavailable at first contact candle opening")
    if action and instant(result["action_at"])<t:raise VerificationError("empirical action precedes its confirmed signal")
    if role=="add" and action and instant(action["signal_available_at"])!=t:raise VerificationError("added-leg fill does not use the selected first confirmed support signal")
    return result


def raw_window_reference(case,day):
    start,end=instant(case["window_start"]),instant(case["window_end"])
    minutes=[];cloud=[];known={value(r,"timestamp"):r for r in day.minutes};t=start.replace(second=0,microsecond=0)
    while t+timedelta(minutes=1)<=end:
        if day.expected_minute(t):
            r=known.get(t)
            minutes.append(dict(case_id=case["id"],episode_id=case["episode_id"],contract=value(r,"contract") if r else case["contract"],
                timestamp=t.isoformat(),available_at=(t+timedelta(minutes=1)).isoformat(),
                **{k:value(r,k) if r else None for k in ("open","high","low","close")},usable=r is not None))
        t+=timedelta(minutes=1)
    for r in day.cloud.for_window(start-timedelta(minutes=5),end):
        if start<=r.available_at<=end:
            cloud.append(dict(case_id=case["id"],episode_id=case["episode_id"],contract=r.contract or case["contract"],timestamp=r.timestamp.isoformat(),available_at=r.available_at.isoformat(),
                **{k:value(r,k) for k in ("open","high","low","close","ema20","ema50","feature_valid","usable","quality_reason")}))
    return minutes,cloud


def verify(stage,attempt,science_receipt,*,root=None):
    stage=Path(stage).resolve();root=Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    science=Path(science_receipt).resolve()
    if not science.is_relative_to(stage):raise VerificationError("scientific receipt must belong to the current ordinary stage")
    passed=read_json(science)
    compare(passed,dict(run_id=stage.name,phase="all",status="passed"),"all-phase scientific prerequisite")
    for r in passed["artifacts"]:verify_pin(stage,r)
    freeze,lock,config,feature=verify_freeze(stage,root)
    if passed["execution_freeze_sha256"]!=digest(stage/"execution-freeze.json"):raise VerificationError("empirical science/source freeze differs")
    output=stage/"verification"/attempt;output.mkdir(parents=True,exist_ok=False)
    sources=output/"source";sources.mkdir()
    for p in [Path(__file__),Path(__file__).parent/"tests/test_phase3_verify_examples.py"]:shutil.copyfile(p,sources/p.name)
    result=dict(schema_version="study23.phase3-independent-example-traces/v1",status="failed",run_id=stage.name,
        started_at=stamp(datetime.now(timezone.utc)),argv=sys.argv,cwd=str(Path.cwd()),science_receipt=pin(science,stage),
        source_snapshots=[pin(p,stage) for p in sorted(sources.iterdir())],scope="Independent chronological saved-case selection and exact immutable raw1m/5m/feature traces plus signal/fill/reset causality; no policy or statistical recalculation")
    try:
        material=load_oracle_material(stage,root,lock,feature);parents=material["parents"];episodes=[];trades=[];events=[];pins=[]
        for phase in ("dev-validation","later"):
            for name,target in (("episodes",episodes),("trades",trades),("events",events)):
                path=stage/"phases"/phase/(name+".jsonl.gz");pins.append(dict(path=str(path.relative_to(stage)),sha256=digest(path)))
                target.extend(r for r in ledger(path) if r["scenario"]=="primary-one-tick")
        selected,absent,indexed,legs,actions=selection_reference(parents,episodes,trades,events)
        saved=read_json(stage/"example-selection.json")
        n=compare(saved,dict(schema_version="study23.phase3-balanced-examples/v1",run_id=stage.name,
            rules={k:list(v) for k,v in RULES.items()},absent_cases=absent,ledger_pins=pins,selection_is_not_trading_rule_selection=True,config_sha256=digest(stage/"config.json")),"saved_empirical_selection")
        if len(saved["cases"])!=len(selected):raise VerificationError("empirical selected case roster is incomplete or enlarged")
        minute_rows=[];cloud_rows=[]
        for actual,record in zip(saved["cases"],selected):
            eid=record["episode_id"];k=(eid,record["policy"],record["mode"]);day=material["contexts"]["primary-one-tick"][eid]
            expected=case_reference(record,day,parents[eid],indexed[k],legs[k],actions[k])
            n+=compare(actual,expected,"case:"+record["id"])
            a,b=raw_window_reference(expected,day);minute_rows.extend(a);cloud_rows.extend(b)
        for name,rows in (("selected-example-minutes",minute_rows),("selected-example-cloud",cloud_rows)):
            path=stage/"tables"/(name+".csv")
            if rows:n2,_=compare_csv(path,rows);n+=n2
            elif path.exists():raise VerificationError("absent empirical cases must not invent raw traces")
        outputs=[pin(stage/"example-selection.json",stage)]
        outputs.extend(pin(stage/"tables"/(name+".csv"),stage) for name,rows in (("selected-example-minutes",minute_rows),("selected-example-cloud",cloud_rows)) if rows)
        result.update(status="passed",strict_field_comparisons=n,cases=len(selected),absent_cases=len(absent),
            minute_rows=len(minute_rows),unknown_minute_rows=sum(not r["usable"] for r in minute_rows),cloud_rows=len(cloud_rows),
            unusable_cloud_rows=sum(not r["usable"] for r in cloud_rows),feature_unavailable_cloud_rows=sum(not r["feature_valid"] for r in cloud_rows),
            outputs=outputs,artifacts=[*outputs,pin(stage/"config.json",stage),pin(stage/"inputs.lock.json",stage),pin(stage/"execution-freeze.json",stage),*[pin(stage/r["path"],stage) for r in pins]],
            selection_rule="earliest chronological qualifying saved case per declared policy/kind/direction; absent categories explicit",
            qualifications=["A examples use diagnostic1plus1 extra exposure, not financed equal-risk gains","All expected unavailable minutes/cloud rows retain null prices/flags","Frozen first X1 edge is separate from second confirmation candle","Native cancellation/feed/tick latency remains unverified","Display geometry/raster/browser is a separate publication gate"])
    except Exception as e:
        result.update(error_type=type(e).__name__,error=str(e),verified_at=stamp(datetime.now(timezone.utc)));write_new(output/"receipt.json",result);raise
    result["verified_at"]=stamp(datetime.now(timezone.utc));write_new(output/"receipt.json",result)
    print({k:result[k] for k in ("status","cases","absent_cases","strict_field_comparisons","minute_rows","cloud_rows")},flush=True)
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--stage",required=True);p.add_argument("--attempt",required=True);p.add_argument("--science",required=True);args=p.parse_args()
    if Path(args.attempt).name!=args.attempt:raise VerificationError("fresh single attempt name required")
    verify(args.stage,args.attempt,args.science)
