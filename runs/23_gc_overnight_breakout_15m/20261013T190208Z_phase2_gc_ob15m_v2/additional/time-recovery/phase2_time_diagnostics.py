"""Frozen ancillary measurement: recovery delay after a protected breach.

This requested diagnostic is declared after policy execution. It cannot alter
any order, outcome, comparison mask, selection or existing saved statistic.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
STUDY="23_gc_overnight_breakout_15m"
SESSIONS=("Asia","London","New York","Outside")


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def instant(value):return datetime.fromisoformat(value.replace("Z","+00:00")) if value else None
def write(path,value):
    with Path(path).open("x") as f:json.dump(value,f,indent=2,allow_nan=False);f.write("\n")


def measure(breach,recovery):
    b,bl=instant(breach.get("first_time")),instant(breach.get("first_time_latest"))
    r,rl=instant(recovery.get("first_time")),instant(recovery.get("first_time_latest"))
    known=breach["occurred"] is True
    if known!= (recovery["breach_occurred"] is True):raise ValueError("breach/recovery population mismatch")
    delay=lower=upper=None
    if known and recovery["occurred"] is True and b and bl and r and rl:
        if r<b:raise ValueError("recovery precedes known first breach")
        delay=(r-b).total_seconds()/60
        lower=max(0.,(r-bl).total_seconds()/60)
        upper=max(0.,(rl-b).total_seconds()/60)
    end=instant(recovery["horizon_end"])
    exposure_low=max(0.,(end-bl).total_seconds()/60) if known and bl else None
    exposure_high=max(0.,(end-b).total_seconds()/60) if known and b else None
    return {"known_breach":known,"breach_unknown":breach["occurred"] is None,"recovered":recovery["occurred"] if known else None,
            "breach_first_time":breach.get("first_time"),"breach_first_time_latest":breach.get("first_time_latest"),
            "recovery_first_time":recovery.get("first_time"),"recovery_first_time_latest":recovery.get("first_time_latest"),
            "recovery_confirmation_available_at":recovery.get("first_available_at"),
            "delay_minutes_source_estimate":delay,"delay_minutes_lower":lower,"delay_minutes_upper":upper,
            "post_breach_exposure_minutes_lower":exposure_low,"post_breach_exposure_minutes_upper":exposure_high,
            "recovery_censored":recovery["occurred"] is None if known else None,"horizon_end":recovery["horizon_end"],
            "not_executed_target_or_financial_recovery":True}


def summarize(rows):
    table=[]
    dimensions=sorted({(r["horizon"],r["level"],r["event"]) for r in rows})
    for year in ("all",*(str(y) for y in range(2018,2027))):
        for session in ("all",*SESSIONS):
            for side in ("combined","upper-first","lower-first"):
                for horizon,level,event in dimensions:
                    selected=[r for r in rows if r["horizon"]==horizon and r["level"]==level and r["event"]==event and (year=="all" or r["year"]==year) and (session=="all" or r["session"]==session) and (side=="combined" or r["side"]==side)]
                    exposed=[r for r in selected if r["known_breach"]]
                    observed=[r for r in exposed if r["recovered"] is True]
                    item=dict(year=year,session=session,side=side,horizon=horizon,level=level,event=event,original_episodes=len(selected),known_breach_episodes=len(exposed),unknown_breach_episodes=sum(r["breach_unknown"] for r in selected),known_recoveries=len(observed),known_no_recovery=sum(r["recovered"] is False for r in exposed),unknown_recovery=sum(r["recovered"] is None for r in exposed),unknown_recovery_time=sum(r["delay_minutes_source_estimate"] is None for r in observed),anchor="original_breakout_fill_cohort; elapsed_origin_first_known_protected_breach",not_executed_target_or_financial_recovery=True)
                    for field in ("delay_minutes_source_estimate","delay_minutes_lower","delay_minutes_upper","post_breach_exposure_minutes_lower","post_breach_exposure_minutes_upper"):
                        values=[r[field] for r in exposed if r[field] is not None]
                        item["mean_"+field]=sum(values)/len(values) if values else None
                        item[field+"_denominator"]=len(values)
                    table.append(item)
    return table


def prepare(stage):
    stage=Path(stage).resolve()
    if stage.parent!=ROOT/"work"/STUDY or (ROOT/"runs"/STUDY/stage.name).exists():raise ValueError("owning unsealed stage required")
    folder=stage/"additional/time-recovery";folder.mkdir(parents=True,exist_ok=False)
    files=[stage/"phases"/phase/(kind+".jsonl.gz") for phase in ("dev-validation","later") for kind in ("occurrence","recovery")]
    inputs=[{"path":str(p.relative_to(stage)),"sha256":digest(p),"bytes":p.stat().st_size} for p in files]
    source=folder/"phase2_time_diagnostics.py";shutil.copyfile(__file__,source)
    freeze={"schema_version":"study23.phase2-time-measurement/v1","run_id":stage.name,"frozen_at":datetime.now(timezone.utc).isoformat(),"post_policy_execution_declaration":True,"policy_outputs_masks_or_selection_changed":False,"source":{"path":str(source.relative_to(stage)),"sha256":digest(source)},"inputs":inputs,"settings_sha256":digest(stage/"config.json"),"selection_sha256":digest(stage/"selection.json"),"environment_lock_sha256":digest(stage/"environment.lock"),"method":"Elapsed time from first known protected one-tick breach to first known recovery. Source-OHLC time estimate plus conservative minute bounds. Unknown first times remain null; no breach is outside the recovery population. Mean delays conditional on known recovery timings, not a survival probability."}
    write(folder/"measurement-freeze.json",freeze)
    def read(path):
        with gzip.open(path,"rt") as f:return [json.loads(line) for line in f]
    occurrence=[r for p in files if p.name=="occurrence.jsonl.gz" for r in read(p)]
    recovery=[r for p in files if p.name=="recovery.jsonl.gz" for r in read(p)]
    breaches={(r["episode_id"],r["horizon"]):r for r in occurrence if r["event"]=="one_tick_breach"}
    rows=[]
    for r in recovery:
        record={k:r[k] for k in ("episode_id","broker_day","year","session","side","horizon","event")}
        record["level"]=r["recovery_level"]
        record.update(measure(breaches[r["episode_id"],r["horizon"]],r));rows.append(record)
    table=summarize(rows)
    private=folder/"episodes.jsonl.gz"
    with gzip.open(private,"xt") as f:
        for row in rows:f.write(json.dumps(row,allow_nan=False)+"\n")
    output=folder/"time-recovery.csv"
    with output.open("x",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    for pin in inputs:
        if digest(stage/pin["path"])!=pin["sha256"]:raise ValueError("input changed during measurement")
    completion={"status":"prepared","rows":len(rows),"summary_rows":len(table),"finished_at":datetime.now(timezone.utc).isoformat(),"measurement_freeze_sha256":digest(folder/"measurement-freeze.json"),"artifacts":[{"path":str(p.relative_to(stage)),"sha256":digest(p),"bytes":p.stat().st_size} for p in (private,output)]}
    write(folder/"completion.json",completion)
    return completion


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--stage",type=Path,required=True)
    print(json.dumps(prepare(parser.parse_args().stage)))
