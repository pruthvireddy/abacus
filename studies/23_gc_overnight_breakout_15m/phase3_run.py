"""Frozen Phase3 stage and pinned parent/cloud adapter; chronological CLI.

No outcomes are computed on import or freeze. Independent verification precedes
selection freezing; later execution is a separate explicit action.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime,timedelta,timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd

from phase3_inputs import (PHASE1_RUN,PHASE1_SHA,PHASE2_RUN,PHASE2_SHA,
    CloudTimeline,cloud_bars,expected_cloud_slots,load_cloud,load_parent_frames,
    parent_order_update_times,verify_record)
from src.engine import Bar,BROKER
from src.phase3_engine import Phase1DayData,Phase3Config

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STUDY="23_gc_overnight_breakout_15m"
AUDIT=ROOT/"work"/STUDY/"phase3-preparation/input-audit-v4/phase3-input-audit.json"
SCENARIOS={"primary-one-tick":dict(commission_per_side=2.5,slippage_ticks=1,ordering="source_ohlc"),
    "gross-zero-cost":dict(commission_per_side=0.,slippage_ticks=0,ordering="source_ohlc"),
    "net-zero-ticks":dict(commission_per_side=2.5,slippage_ticks=0,ordering="source_ohlc"),
    "net-two-ticks":dict(commission_per_side=2.5,slippage_ticks=2,ordering="source_ohlc"),
    "high-first-one-tick":dict(commission_per_side=2.5,slippage_ticks=1,ordering="high_first"),
    "low-first-one-tick":dict(commission_per_side=2.5,slippage_ticks=1,ordering="low_first")}
RUNTIME=("phase3_run.py","phase3_execution.py","phase3_inputs.py","phase3_metrics.py","phase3_verify.py","src/phase3_engine.py","src/engine.py")


def instant(value):return datetime.fromisoformat(str(value).replace("Z","+00:00"))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x") as f:json.dump(value,f,indent=2,allow_nan=False);f.write("\n")


def ledger(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    count=0
    with gzip.open(path,"xt") as f:
        for row in rows:f.write(json.dumps(row,allow_nan=False,separators=(",",":"))+"\n");count+=1
    return {"path":str(path),"bytes":path.stat().st_size,"sha256":sha(path),"row_count":count}


def load_ledger(path):
    with gzip.open(path,"rt") as f:return [json.loads(line) for line in f]


def stage_path(stage):
    stage=Path(stage).resolve()
    if not stage.is_relative_to(ROOT/"work"/STUDY) or stage.name!=json.loads((HERE/"config-phase3.json").read_text())["run_id"]:raise ValueError("dedicated current Phase3 stage identity required")
    return stage


def freeze(stage):
    stage=stage_path(stage)
    if (stage/"execution-freeze.json").exists():raise FileExistsError("retain existing freeze")
    config=json.loads((HERE/"config-phase3.json").read_text());audit=json.loads(AUDIT.read_text())
    if audit["result"]!="passed" or audit["phase1"]["manifest_sha256"]!=PHASE1_SHA or audit["phase2"]["selected_policy"] is not None:raise ValueError("verified fixed parents required")
    if sha(AUDIT)!="d5226043b0ce33922d5e1ad0d6b6f3fd2a5f4753ee58ebd7929903b651418a3b":raise ValueError("input receipt changed")
    for name in RUNTIME:
        if not (HERE/name).is_file():raise ValueError("complete computational source required: "+name)
    stage.mkdir(parents=True,exist_ok=True)
    for source,target in ((HERE/"config-phase3.json","config.json"),(HERE/"protocol-phase3.md","protocol.md"),(ROOT/"uv.lock","uv.lock"),(AUDIT,"input-audit.json")):
        if (stage/target).exists():raise FileExistsError("earlier partial freeze remains")
        shutil.copyfile(source,stage/target)
    request=ROOT/"work"/STUDY/"phase3-preparation/authorized-user-request.txt"
    shutil.copyfile(request,stage/"authorized-user-request.txt")
    parentroot=ROOT/"runs"/STUDY/PHASE1_RUN
    manifest=json.loads((parentroot/"manifest.json").read_text())
    verify_record(parentroot,{"path":"manifest.json","sha256":PHASE1_SHA})
    selected=[r for r in manifest["external_artifacts"] if r["id"] in {"audit-minutes","audit-bars-15m","audit-expected-minutes"} or any(r["id"]==name+"-"+kind for name in SCENARIOS for kind in ("trades","orders","events","days"))]
    for r in selected:verify_record(ROOT,r,key="locator")
    inputs={"schema_version":"study23.phase3-input-lock/v1","primary_parent":{"run_id":PHASE1_RUN,"manifest_sha256":PHASE1_SHA},"phase2":{"run_id":PHASE2_RUN,"manifest_sha256":PHASE2_SHA,"replication_parent":None},"input_audit_sha256":sha(stage/"input-audit.json"),"feature":audit["cloud"],"parent_external":selected,"parent_roster":{"path":str((parentroot/"tables/days.csv").relative_to(ROOT)),"sha256":sha(parentroot/"tables/days.csv")},"scope":"Reuse immutable parent and causal public feature release; no release rebuild."}
    phase2root=ROOT/"runs"/STUDY/PHASE2_RUN
    verify_record(phase2root,{"path":"manifest.json","sha256":PHASE2_SHA})
    phase2manifest=json.loads((phase2root/"manifest.json").read_text())
    contextpins=[]
    for phase in ("dev-validation","later"):
        for kind in ("boundary-events","level-opportunities"):
            path=f"events/phases/{phase}/{kind}.jsonl.gz"
            record=next(r for r in phase2manifest["artifacts"] if r["path"]==path)
            verify_record(phase2root,record)
            contextpins.append({**record,"path":str((phase2root/path).relative_to(ROOT)),"phase":phase,"kind":kind})
    inputs["phase2_context_pins"]=contextpins
    save(stage/"inputs.lock.json",inputs)
    snapshots=[]
    sources=[*(HERE/name for name in RUNTIME),*sorted((HERE/"tests").glob("test_phase3*.py"))]
    # Audited reusable Python loader code is retained without modifying it.
    aux=[ROOT/"packages/bhishma/src/abacus_bhishma"/name for name in ("ema_cloud_loader_v2.py","ema_cloud.py","manifest_selection.py","provenance.py","publication_safety.py","calendar.py")]
    for source in [*sources,*[p for p in aux if p.is_file()]]:
        dest=stage/"source"/source.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        r={"path":str(dest.relative_to(stage)),"bytes":dest.stat().st_size,"sha256":sha(dest)}
        if source.is_relative_to(HERE):r["workspace_path"]=str(source.relative_to(HERE))
        else:r["workspace_root_path"]=str(source.relative_to(ROOT))
        snapshots.append(r)
    status=subprocess.check_output(["git","status","--porcelain=v1"],cwd=ROOT,text=True)
    (stage/"git-status.txt").write_text(status)
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    save(stage/"execution-freeze.json",{"schema_version":"study23.phase3-execution-freeze/v1","run_id":stage.name,"at":datetime.now(timezone.utc).isoformat(),"revision":revision,"dirty":bool(status),"source_files":snapshots,"settings_sha256":sha(stage/"config.json"),"protocol_sha256":sha(stage/"protocol.md"),"inputs_sha256":sha(stage/"inputs.lock.json"),"input_audit_sha256":sha(stage/"input-audit.json"),"environment_lock_sha256":sha(stage/"uv.lock"),"python":sys.version,"packages":{p:importlib.metadata.version(p) for p in ("numpy","pandas","pyarrow")},"phase3_policy_outcomes_opened":False,"scope":"Actual computational source frozen before any historical Phase3 policy scoring; presentation sources retained separately before seal."})
    save(stage/"commands.json",[{"argv":sys.argv,"cwd":str(Path.cwd()),"scope":"settings/source/input freeze, no policy outcomes"}])
    return json.loads((stage/"execution-freeze.json").read_text())


def assert_freeze(stage):
    stage=Path(stage);f=json.loads((stage/"execution-freeze.json").read_text())
    for name,field in (("config.json","settings_sha256"),("protocol.md","protocol_sha256"),("inputs.lock.json","inputs_sha256"),("input-audit.json","input_audit_sha256"),("uv.lock","environment_lock_sha256")):
        if sha(stage/name)!=f[field]:raise ValueError("frozen bytes changed: "+name)
    for r in f["source_files"]:
        verify_record(stage,r)
        if r.get("workspace_path") in RUNTIME:verify_record(HERE,{"path":r["workspace_path"],"sha256":r["sha256"]})
        if "workspace_root_path" in r:verify_record(ROOT,{"path":r["workspace_root_path"],"sha256":r["sha256"]})
    return f


def config_for_scenario(name):return Phase3Config(scenario=name,**SCENARIOS[name])


def load_material(stage):
    stage=Path(stage);assert_freeze(stage)
    lock=json.loads((stage/"inputs.lock.json").read_text())
    prepared=load_parent_frames(ROOT)
    cloudframe=load_cloud(ROOT)
    featuremanifest=json.loads((ROOT/"catalog/datasets/same_contract_ema_cloud__1.1.0.json").read_text())
    expected=expected_cloud_slots(featuremanifest["coverage_start_session"],featuremanifest["coverage_end_completion"])
    timeline=CloudTimeline(cloud_bars(cloudframe),[t.to_pydatetime() for t in expected.timestamp],coverage_end=instant(featuremanifest["coverage_end_completion"]))
    del cloudframe,expected
    parents={t["trade_id"]:dict(t,episode_id=t["trade_id"]) for t in prepared["primary-one-tick-trades"]}
    used={t["broker_day"] for t in parents.values()}
    rawminutes=prepared["audit-minutes"]
    # The inherited source study used scheduled observed raw minutes. Invalid
    # execution prices are unavailable evidence for new actions, not zero fills.
    selected=rawminutes.loc[rawminutes.scheduled & rawminutes.source_valid].copy()
    selected["broker_day"]=selected.timestamp.dt.tz_convert(BROKER).dt.date.astype(str)
    selected=selected.loc[selected.broker_day.isin(used)]
    minutes={day:[Bar(t.to_pydatetime(),float(o),float(h),float(l),float(c),str(contract),at.to_pydatetime()) for t,o,h,l,c,contract,at in rows[["timestamp","open","high","low","close","contract","available_at"]].itertuples(index=False,name=None)] for day,rows in selected.groupby("broker_day",sort=True)}
    bars15=prepared["audit-bars-15m"]
    bars15["broker_day"]=bars15.timestamp.dt.tz_convert(BROKER).dt.date.astype(str)
    by15={day:rows for day,rows in bars15.loc[bars15.broker_day.isin(used)].groupby("broker_day",sort=True)}
    seconds=set((prepared["audit-expected-minutes"].timestamp.astype("int64")//10**9).tolist())
    expected_minute=lambda t:int(t.timestamp()) in seconds
    roster=pd.read_csv(ROOT/lock["parent_roster"]["path"],keep_default_na=False).to_dict("records")
    for r in roster:
        for k in ("eligible","valid_range","no_trade","unknown_outcome"):r[k]=str(r[k]).lower()=="true"
        r["quantity_skips"]=int(r["quantity_skips"])
    scenarios={};orders={};events={};days={}
    for name in SCENARIOS:
        for kind,target in (("trades",scenarios),("orders",orders),("events",events),("days",days)):
            record=next(r for r in lock["parent_external"] if r["id"]==name+"-"+kind)
            verify_record(ROOT,record,key="locator")
            rows=prepared[name+"-"+kind] if name=="primary-one-tick" else load_ledger(ROOT/record["locator"])
            target[name]=rows
    contexts=[]
    for pinrow in lock["phase2_context_pins"]:
        verify_record(ROOT,pinrow)
        for index,row in enumerate(load_ledger(ROOT/pinrow["path"])):
            if row["episode_id"] not in parents or row.get("occurred") is not True:continue
            if pinrow["kind"]=="boundary-events" and row["horizon"]!="remaining_broker_window":continue
            if pinrow["kind"]=="level-opportunities" and row["fraction"]!=.5:continue
            at=row.get("first_available_at") or row.get("first_observed_available_at")
            if not at:continue
            parent=parents[row["episode_id"]]
            kind="midpoint_"+row["event"] if pinrow["kind"]=="level-opportunities" else "protected_"+("low" if parent["direction"]==1 else "high")+"_"+row["event"]
            contexts.append({"episode_id":row["episode_id"],"event_kind":kind,"decision_at":at,"event_first_time":row.get("first_time"),"event_first_time_latest":row.get("first_time_latest"),"event_time_precision":row.get("time_precision"),"event_ordering_ambiguous":row.get("ordering_ambiguous",False),"baseline_position_status":row.get("baseline_position_status_at_event"),"saved_level":row.get("raw_level"),"anchor":"phase2_saved_event_context_"+kind,"source_artifact":pinrow["path"],"source_sha256":pinrow["sha256"],"source_row":index,"phase2_replication_parent":None})
    material={"parents":parents,"minutes":minutes,"bars15":by15,"cloud":timeline,"expected_minute":expected_minute,"roster":roster,"scenarios":scenarios,"orders":orders,"events":events,"days":days,"phase2_context":contexts}
    return material


def group_parent_events(records,trades):
    """Saved Phase1 gaps carry a day; trade lifecycle events carry a trade ID."""
    by_id={t["trade_id"]:t["broker_day"] for t in trades}
    grouped=defaultdict(list)
    for record in records:
        day=record.get("broker_day")
        if "trade_id" in record:
            if record["trade_id"] not in by_id:raise ValueError("parent event references unknown saved trade")
            trade_day=by_id[record["trade_id"]]
            if day is not None and day!=trade_day:raise ValueError("parent event day/trade mismatch")
            day=trade_day
        if day is None:raise ValueError("parent event lacks a saved day or trade identity")
        grouped[day].append(record)
    return grouped


def contexts_for_scenario(material,scenario="primary-one-tick"):
    traded={t["broker_day"]:t for t in material["scenarios"][scenario]}
    ranges={d["broker_day"]:d for d in material["days"][scenario]}
    orderdays=defaultdict(list);eventdays=group_parent_events(material["events"][scenario],material["scenarios"][scenario])
    for r in material["orders"][scenario]:orderdays[r["broker_day"]].append(r)
    result={}
    for eid,original in material["parents"].items():
        day=original["broker_day"];parent=traded.get(day);range_row=ranges.get(day)
        if not range_row:raise ValueError("saved parent scenario day missing")
        cutoff=instant(day+"T17:00:00Z")
        if parent:
            parent=dict(parent,episode_id=eid,phase1_saved_trade_id=parent["trade_id"],**SCENARIOS[scenario])
            updates=parent_order_update_times(material["bars15"][day],first_submission=instant(parent["order_submitted_at"]),shadow_event_time=instant(parent["entry_time"]),cutoff=cutoff,contract=parent["contract"])
            shadow="accepted"
        else:
            updates=();shadow="unknown" if range_row.get("unknown_outcome") else "no_event"
        result[eid]=Phase1DayData(eid,day,parent,material["minutes"].get(day,()),material["cloud"],updates,float(range_row["range_high"]),float(range_row["range_low"]),cutoff,material["expected_minute"],orderdays[day],eventdays[day],shadow,parent["contract"] if parent else original["contract"])
    return result


def load_contexts(stage):
    material=load_material(stage)
    return contexts_for_scenario(material),material["parents"],material["roster"],material


def retain_parent_rosters(stage,material):
    stage=Path(stage)
    if (stage/"parents").exists():raise FileExistsError("preserve retained rosters")
    ledger(stage/"parents/baseline-trades.jsonl.gz",material["parents"].values())
    ledger(stage/"parents/calendar-roster.jsonl.gz",material["roster"])
    eligible=[r for r in material["roster"] if r["eligible"]]
    ledger(stage/"parents/eligible-roster.jsonl.gz",eligible)
    save(stage/"exclusions.json",{"all_calendar_days":len(material["roster"]),"causally_eligible_days":len(eligible),"accepted_original_episodes":len(material["parents"]),"unknown_first_event_days":[r["broker_day"] for r in eligible if r["unknown_outcome"]],"known_no_trade_days":[r["broker_day"] for r in eligible if r["no_trade"]],"exclusions":[r for r in material["roster"] if not r["eligible"]],"scope":"Exact inherited eligibility, full calendar/eligible/accepted rosters; no alternative-quality filtering."})


def freeze_selection(stage,verification):
    stage=Path(stage);assert_freeze(stage)
    receiptpath=Path(verification);receipt=json.loads(receiptpath.read_text())
    if receipt.get("status",receipt.get("result"))!="passed" or receipt.get("phase")!="dev-validation":raise ValueError("independent development/validation verification required")
    if receipt.get("run_id")!=stage.name or receipt.get("execution_freeze_sha256")!=sha(stage/"execution-freeze.json"):raise ValueError("development verification belongs to another frozen run")
    if (stage/"phases/later").exists():raise ValueError("later outcomes already opened")
    candidate=stage/"selection-candidate.json";selected=json.loads(candidate.read_text())
    bound=next((r for r in receipt.get("artifacts",[]) if r["path"]=="selection-candidate.json"),None)
    if not bound or bound["sha256"]!=sha(candidate):raise ValueError("independently verified selection candidate bytes required")
    verify_record(stage,bound)
    if selected["later_outcomes_opened"] is not False:raise ValueError("causal selection scope required")
    selected["frozen_at"]=datetime.now(timezone.utc).isoformat();save(stage/"selection.json",selected)
    save(stage/"selection-freeze.json",{"run_id":stage.name,"selection_sha256":sha(stage/"selection.json"),"settings_sha256":sha(stage/"config.json"),"development_validation_receipt":{"path":str(receiptpath.relative_to(stage)),"sha256":sha(receiptpath)},"candidate_sha256":sha(candidate),"later_outcomes_opened":False,"frozen_at":selected["frozen_at"]})
    return selected


def main():
    p=argparse.ArgumentParser();p.add_argument("--stage",type=Path,required=True);p.add_argument("--action",choices=("freeze","dev-validation","freeze-selection","later"),required=True);p.add_argument("--verification",type=Path);a=p.parse_args()
    if a.action=="freeze":result=freeze(a.stage)
    elif a.action=="freeze-selection":result=freeze_selection(a.stage,a.verification)
    else:
        from phase3_execution import execute_phase
        result=execute_phase(a.stage,a.action)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":main()
