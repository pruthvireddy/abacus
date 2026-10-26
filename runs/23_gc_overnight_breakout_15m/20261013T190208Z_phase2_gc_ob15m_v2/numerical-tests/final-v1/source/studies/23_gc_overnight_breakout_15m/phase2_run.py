"""Chronologically execute the frozen Phase2 protocol using pinned Phase1 bytes."""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd
import pyarrow.parquet as pq

from metrics import enrich, write_csv, instant, session_at, NY, SESSIONS
from phase2_metrics import origin, known_pnl, trade_summaries, paired_rows, interval_sensitivities, frequency_rows, budget_quantity, financial_recovery, match
from src.engine import Bar, BROKER
from src.phase2_engine import BaselineEpisode, DecisionBar, Phase2Config, policy_specs, prepare_context, run_policy, observe_episode, observe_levels, find_signal, execute_signal, percentage_stop
from phase2_accounts import account_results

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STUDY="23_gc_overnight_breakout_15m"


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x") as f:json.dump(value,f,indent=2,allow_nan=False);f.write("\n")


def load_gz(path):
    with gzip.open(path,"rt") as f:return [json.loads(line) for line in f]


def ledger(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    with gzip.open(path,"wt") as f:
        for row in rows:f.write(json.dumps(row,allow_nan=False)+"\n")
    return {"path":str(path.relative_to(ROOT)),"sha256":sha(path),"bytes":path.stat().st_size,"row_count":len(rows)}


def freeze(stage):
    config=json.loads((HERE/"config-phase2.json").read_text())
    if stage.name!=config["run_id"]:raise ValueError("stage/run differs from frozen settings")
    for src,name in ((HERE/"config-phase2.json","config.json"),(HERE/"protocol-phase2.md","protocol.md"),(ROOT/"uv.lock","environment.lock")):
        if (stage/name).exists():raise FileExistsError("execution already frozen")
        shutil.copyfile(src,stage/name)
    pin=json.loads((stage/"phase2-baseline-pin.json").read_text())
    if pin["status"]!="passed":raise ValueError("baseline pin not passed")
    save(stage/"inputs.lock.json",{"baseline_pin":"phase2-baseline-pin.json","sha256":sha(stage/"phase2-baseline-pin.json"),"phase1_manifest":pin["phase1_manifest"],"prepared_inputs":pin["prepared_execution_inputs"]})
    files=[HERE/"phase2_run.py",HERE/"phase2_metrics.py",HERE/"phase2_accounts.py",HERE/"metrics.py",HERE/"src/engine.py",HERE/"src/phase2_engine.py",HERE/"phase2_baseline_pin.py",*HERE.glob("tests/test_phase2*.py")]
    snapshots=[]
    for source in files:
        target=stage/"source"/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        snapshots.append({"path":str(target.relative_to(stage)),"sha256":sha(target),"bytes":target.stat().st_size})
    status=subprocess.check_output(["git","status","--porcelain=v1"],cwd=ROOT,text=True)
    (stage/"git-status.txt").write_text(status)
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    save(stage/"execution-freeze.json",dict(at=datetime.now(timezone.utc).isoformat(),revision=revision,dirty=bool(status),source_files=snapshots,settings_sha256=sha(stage/"config.json"),protocol_sha256=sha(stage/"protocol.md"),inputs_sha256=sha(stage/"inputs.lock.json"),baseline_pin_sha256=sha(stage/"phase2-baseline-pin.json"),environment_lock_sha256=sha(stage/"environment.lock"),python=sys.version,packages={p:importlib.metadata.version(p) for p in ("numpy","pandas","pyarrow")}))


def assert_freeze(stage):
    f=json.loads((stage/"execution-freeze.json").read_text())
    for name,key in (("config.json","settings_sha256"),("protocol.md","protocol_sha256"),("inputs.lock.json","inputs_sha256"),("phase2-baseline-pin.json","baseline_pin_sha256"),("environment.lock","environment_lock_sha256")):
        if sha(stage/name)!=f[key]:raise ValueError("frozen bytes changed: "+name)
    for row in f["source_files"]:
        if sha(stage/row["path"])!=row["sha256"]:raise ValueError("snapshot bytes changed")
        original=ROOT/Path(row["path"]).relative_to("source")
        runtime={"phase2_run.py","phase2_metrics.py","phase2_accounts.py","metrics.py","src/engine.py","src/phase2_engine.py"}
        if str(original.relative_to(HERE)) in runtime and sha(original)!=row["sha256"]:
            raise ValueError("executed producer changed since freeze: "+str(original))


def load_contexts(stage):
    pin=json.loads((stage/"phase2-baseline-pin.json").read_text())
    locators={x["id"]:x for x in pin["scenario_ledgers"]}
    def saved(name):
        item=locators[name]
        if sha(ROOT/item["locator"])!=item["sha256"]:raise ValueError("baseline ledger changed")
        return load_gz(ROOT/item["locator"])
    baseline={t["trade_id"]:t for t in saved("primary-one-tick-trades")}
    range_rows={r["broker_day"]:r for r in saved("primary-one-tick-days")}
    prepared={}
    for key,item in pin["prepared_execution_inputs"].items():
        if sha(ROOT/item["locator"])!=item["sha256"]:raise ValueError("prepared input changed")
        if key!="audit-missing-minutes":prepared[key]=pq.read_table(ROOT/item["locator"]).to_pandas()
    minutes=prepared["audit-minutes"]
    minutes=minutes.loc[minutes.scheduled & minutes.source_valid].copy()
    minutes["broker_day"]=minutes.timestamp.dt.tz_convert(BROKER).dt.date.astype(str)
    days_used={t["broker_day"] for t in baseline.values()}
    minutes=minutes.loc[minutes.broker_day.isin(days_used)]
    by_minute={day:[Bar(t.to_pydatetime(),float(o),float(h),float(l),float(c),str(contract),a.to_pydatetime()) for t,o,h,l,c,contract,a in df[["timestamp","open","high","low","close","contract","available_at"]].itertuples(index=False,name=None)] for day,df in minutes.groupby("broker_day",sort=True)}
    bars15=prepared["audit-bars-15m"]
    by_decision={}
    for day,df in bars15.loc[bars15.broker_date.isin(days_used)].groupby("broker_date",sort=True):
        values=[]
        for r in df.to_dict("records"):
            t=r["timestamp"].to_pydatetime()
            values.append(DecisionBar(t,*(float(r[k]) if pd.notna(r[k]) else 0. for k in ("open","high","low","close")),str(r["contract"]) if pd.notna(r["contract"]) else "unobserved",t+timedelta(minutes=15),bool(r["usable"])))
        by_decision[day]=values
    expected={int(t.value//10**9) for t in prepared["audit-expected-minutes"].timestamp}
    def expected_minute(t):return int(t.timestamp()) in expected
    contexts={key:prepare_context(BaselineEpisode.from_rows(t,range_rows[t["broker_day"]]),by_minute[t["broker_day"]],by_decision[t["broker_day"]],expected_minute) for key,t in baseline.items()}
    roster=pd.read_csv(ROOT/pin["complete_day_roster"]["path"],keep_default_na=False).to_dict("records")
    # CSV booleans are typed, not truthiness of the string "False".
    for r in roster:
        for k in ("eligible","valid_range","no_trade","unknown_outcome"):
            r[k]=str(r[k]).lower()=="true"
        r["quantity_skips"]=int(r["quantity_skips"])
    return contexts,baseline,roster,minutes


def normalize(row):
    raw=dict(row)
    status=raw["status"]
    raw["execution_status"]=status
    raw["status"]={"filled_complete":"completed","filled_censored":"censored","known_no_fill":"no_fill"}.get(status,"unknown" if status.startswith("unknown") else status)
    if raw.get("missed_before_arming"):raw["status"]="missed_before_arming"
    raw["signal_at"]=raw.get("signal_available_at")
    raw["opportunity_seen"]=True if raw.get("opportunity") else None if raw.get("unknown") else False
    raw["ambiguous"]=bool(raw.get("trade",{}).get("ambiguous")) if raw.get("trade") else bool(raw.get("ambiguous"))
    return raw


def select_primary(results,baseline):
    primary=[p.name for p in policy_specs() if p.kind=="reclaim"]
    indexed={p:{r["episode_id"]:r for r in results[p]} for p in primary}
    ids=[k for k,t in baseline.items() if origin(t)["year"] in {"2021","2022","2023"}]
    common=[k for k in ids if baseline[k]["status"]=="completed" and all(known_pnl(indexed[p][k]) is not None for p in primary)]
    candidates=[]
    for p in primary:
        completed=[indexed[p][k] for k in ids if indexed[p][k]["status"]=="completed"]
        years=sorted({origin(baseline[r["episode_id"]])["year"] for r in completed})
        differences=[known_pnl(indexed[p][k])-baseline[k]["net_dollars"] for k in common]
        average=sum(differences)/len(differences) if differences else None
        candidates.append({"policy":p,"validation_episodes":len(ids),"common_complete_pairs":len(common),"completed_fills":len(completed),"years_with_completed_fills":years,"validation_mean_difference":average,"qualifies":average is not None and average>0 and len(completed)>=100 and len(years)>=2})
    qualifying=[r for r in candidates if r["qualifies"]]
    chosen=max(qualifying,key=lambda r:(r["validation_mean_difference"],-int(r["policy"].split("q")[-1]))) if qualifying else None
    return {"selected_policy":chosen["policy"] if chosen else None,"decision":"selected_for_later_assessment" if chosen else "retain_baseline_no_qualifying_replacement","candidates":candidates,"prior_baseline_exposure":True,"later_alternative_outcomes_opened":False,"frozen_at":datetime.now(timezone.utc).isoformat()}


def execute_phase(stage,phase):
    folder=stage/"phases"/phase
    if folder.exists():raise FileExistsError("phase already executed; preserve it")
    if phase=="dev-validation":freeze(stage)
    assert_freeze(stage)
    if phase=="later":
        selection=json.loads((stage/"selection.json").read_text()); receipt=json.loads((stage/"selection-freeze.json").read_text())
        if sha(stage/"selection.json")!=receipt["selection_sha256"]:raise ValueError("selection changed before later assessment")
        if receipt["settings_sha256"]!=sha(stage/"config.json"):raise ValueError("selection belongs to other settings")
    contexts,baseline,roster,_=load_contexts(stage)
    years={"2018","2019","2020","2021","2022","2023"} if phase=="dev-validation" else {"2024","2025","2026"}
    selected={k:t for k,t in baseline.items() if origin(t)["year"] in years}
    folder.mkdir(parents=True)
    results={p.name:[] for p in policy_specs()}
    observations=[];recoveries=[];events=[];levels=[]
    for i,key in enumerate(selected):
        ctx=contexts[key]
        for p in policy_specs():results[p.name].append(normalize(run_policy(ctx,p)))
        observed=observe_episode(ctx)
        for kind,target in (("occurrence",observations),("recovery",recoveries),("events",events)):
            for r in observed[kind]:target.append(dict(r,episode_id=key,broker_day=baseline[key]["broker_day"],**origin(baseline[key])))
        for r in observe_levels(ctx):levels.append(dict(r,episode_id=key,broker_day=baseline[key]["broker_day"],**origin(baseline[key])))
        if i%100==0:print(f"{phase}: {i}/{len(selected)} episodes",flush=True)
    pins=[]
    for name,rows in (("policies",[r for rows in results.values() for r in rows]),("occurrence",observations),("recovery",recoveries),("boundary-events",events),("level-opportunities",levels)):
        pins.append(ledger(folder/(name+".jsonl.gz"),rows))
    if phase=="dev-validation":
        selection=select_primary(results,selected)
        save(stage/"selection.json",selection)
        save(stage/"selection-freeze.json",{"selection_sha256":sha(stage/"selection.json"),"settings_sha256":sha(stage/"config.json"),"development_validation_ledger":pins[0],"frozen_at":datetime.now(timezone.utc).isoformat(),"later_outcomes_opened":False})
    save(folder/"completion.json",{"finished_at":datetime.now(timezone.utc).isoformat(),"episodes":len(selected),"original_years":sorted(years),"ledgers":pins,"settings_sha256":sha(stage/"config.json"),"selection_sha256":sha(stage/"selection.json")})


def enrich_observation(row,baseline):
    item=dict(row)
    if item.get("first_time"):
        item["elapsed_minutes"]=(instant(item["first_time"])-instant(baseline[item["episode_id"]]["entry_time"])).total_seconds()/60
    else:item["elapsed_minutes"]=None
    if "recovery_level" in item:item["level"]=item["recovery_level"]
    return item


def level_summaries(raw, baseline):
    """Price-path opportunity diagnostics, never assumed executed targets."""
    rows=[dict(enrich_observation(r,baseline),horizon="remaining_broker_window",level=str(r["fraction"])) for r in raw]
    table=frequency_rows(rows,["touch","inward_close","outward_reclaim"],recovery=True)
    for item in table:
        roster=[r for r in rows if match(r,item["year"],item["session"],item["side"]) and r["level"]==item["level"] and r["event"]==item["event"]]
        touched=[r for r in roster if r["occurred"] is True]
        item.update(fraction=float(item.pop("level")),population="all_original_accepted_episodes; conditional_path_diagnostics_after_known_event",not_realized_trade_return=True)
        for field,prefix in (("range_recovery_before_opposite","range_recovery"),("excursion_success","first_1r_success")):
            yes=sum(r.get(field) is True for r in touched);no=sum(r.get(field) is False for r in touched);unknown=sum(r.get(field) is None for r in touched)
            item.update({prefix+"_successes":yes,prefix+"_known_denominator":yes+no,prefix+"_unknown":unknown,prefix+"_rate":yes/(yes+no) if yes+no else None})
        item["first_1r_reference"]="absolute_distance_from_raw_candidate_level_to_frozen_1percent_tickrounded_stop_at_that_level; price_path_from_first_touch; not_trade_R"
        for field in ("mfe_after_touch_points","mae_after_touch_points","deepest_range_fraction","event_risk_points"):
            values=[r[field] for r in touched if r.get(field) is not None]
            item["mean_"+field]=sum(values)/len(values) if values else None
            item[field+"_denominator"]=len(values)
    return table


def transition_tables(observations,events,results,baseline):
    titles={"asia":"Asia","london":"London","new_york":"New York","outside_named_sessions":"Outside"}
    breach={r["episode_id"]:r for r in observations if r["horizon"]=="remaining_broker_window" and r["event"]=="one_tick_breach"}
    reclaims={r["episode_id"]:r for r in observations if r["horizon"]=="remaining_broker_window" and r["event"]=="reclaim"}
    transitions=[]
    for key,t in baseline.items():
        original=origin(t)
        b=breach[key];reclaim=reclaims[key]
        if b["occurred"] is True:
            transitions.append(dict(episode_id=key,**original,transition="breakout_to_breach",from_session=original["session"],to_session=titles.get(b["event_session"],"Unknown"),time=b.get("first_time")))
        if reclaim["occurred"] is True:
            transitions.append(dict(episode_id=key,**original,transition="breach_to_price_reclaim",from_session=titles.get(b["event_session"],"Unknown"),to_session=titles.get(reclaim["event_session"],"Unknown"),time=reclaim.get("first_time")))
        for p,rows in results.items():
            r=next(x for x in rows if x["episode_id"]==key)
            if not r.get("trade"):continue
            entry=r["trade"]["entry_time"]
            transitions.append(dict(episode_id=key,**original,transition="breakout_to_candidate_entry:"+p,from_session=original["session"],to_session=session_at(entry),time=entry))
            if b["occurred"] is True and b.get("first_time_latest") and instant(b["first_time_latest"])<=instant(entry):
                transitions.append(dict(episode_id=key,**original,transition="breach_to_candidate_entry:"+p,from_session=titles.get(b["event_session"],"Unknown"),to_session=session_at(entry),time=entry))
    table=[]
    kinds=["breakout_to_breach","breach_to_price_reclaim",*("breakout_to_candidate_entry:"+p for p in results),*("breach_to_candidate_entry:"+p for p in results)]
    counts=Counter();unknowns=Counter()
    for row in transitions:
        for yy in (row["year"],"all"):
            for ss in (row["side"],"combined"):
                key=(yy,ss,row["transition"],row["from_session"],row["to_session"])
                counts[key]+=1;unknowns[key]+=int(row["time"] is None)
    for year in ("all",*(str(y) for y in range(2018,2027))):
        for side in ("combined","upper-first","lower-first"):
            for kind in kinds:
                for start in (*SESSIONS,"Unknown"):
                    for end in (*SESSIONS,"Unknown"):
                        key=(year,side,kind,start,end)
                        table.append(dict(year=year,side=side,transition=kind,from_session=start,to_session=end,count=counts[key],unknown=unknowns[key],anchor="original_breakout_year; actual_event_and_fill_sessions"))
    distributions=[]
    for horizon in ("original_session","remaining_broker_window"):
        for event in ("touch","one_tick_breach","close_break","reclaim"):
            for year in ("all",*(str(y) for y in range(2018,2027)),"Unknown"):
                for session in ("all",*SESSIONS,"Unknown"):
                    for side in ("combined","upper-first","lower-first"):
                        raw=[r for r in observations if r["horizon"]==horizon and r["event"]==event and r["occurred"] is True and (side=="combined" or r["side"]==side)]
                        group=[r for r in raw if (year=="all" or str(r["event_year"])==year or (year=="Unknown" and r["event_year"] is None)) and (session=="all" or titles.get(r["event_session"],"Unknown")==session)]
                        distributions.append(dict(year=year,session=session,side=side,horizon=horizon,event=event,count=len(group),total_known_events=len(raw),share=len(group)/len(raw) if raw else None,unknown_time=sum(r["first_time"] is None for r in group),anchor="actual_boundary_event"))
    return transitions,table,distributions


def summarize_all(stage):
    assert_freeze(stage)
    if (stage/"execution-completion.json").exists():raise FileExistsError("completed stage is immutable")
    paths=[stage/"phases"/name for name in ("dev-validation","later")]
    for folder in paths:
        done=json.loads((folder/"completion.json").read_text())
        for item in done["ledgers"]:
            if sha(ROOT/item["path"])!=item["sha256"]:raise ValueError("executed phase ledger changed")
    contexts,baseline,days,minutes=load_contexts(stage)
    calendar=[d["broker_day"] for d in days]
    result_rows=[r for folder in paths for r in load_gz(folder/"policies.jsonl.gz")]
    results={p.name:[r for r in result_rows if r["policy"]==p.name] for p in policy_specs()}
    observations=[enrich_observation(r,baseline) for folder in paths for r in load_gz(folder/"occurrence.jsonl.gz")]
    recovery_raw=[enrich_observation(r,baseline) for folder in paths for r in load_gz(folder/"recovery.jsonl.gz")]
    events=[r for folder in paths for r in load_gz(folder/"boundary-events.jsonl.gz")]
    levels=[r for folder in paths for r in load_gz(folder/"level-opportunities.jsonl.gz")]
    cohorts=[];timing=[];equity=[];trades=[]
    for policy,rows in results.items():
        print("Summarizing actual-entry policy "+policy,flush=True)
        t,c,h,e=trade_summaries(rows,days,policy);trades+=t;cohorts+=c;timing+=h;equity+=e
    families={"primary":[p.name for p in policy_specs() if p.kind=="reclaim"],"passive":[p.name for p in policy_specs() if p.kind=="passive"],"protected":[p.name for p in policy_specs() if p.kind.startswith("protected")]}
    paired=[];intervals=[]
    periods={"development":[2018,2019,2020],"validation":[2021,2022,2023],"later-assessment":[2024,2025],"replication":[2026],"overall":list(range(2018,2027))}
    for family,policies in families.items():
        print("Summarizing original-episode family "+family,flush=True)
        paired+=paired_rows(results,baseline,calendar,policies,family)
        if family!="passive":intervals+=interval_sensitivities(results,baseline,calendar,policies,family,periods)
    frequency=frequency_rows(observations,["touch","one_tick_breach","close_break","reclaim"])
    recoveries=frequency_rows([r for r in recovery_raw if r["breach_occurred"] is True],["touch","close_reclaim"],recovery=True,dimensions=sorted({(r["horizon"],r["level"],r["event"]) for r in recovery_raw}))
    for r in recoveries:
        roster=[x for x in recovery_raw if match(x,r["year"],r["session"],r["side"]) and x["horizon"]==r["horizon"] and x["level"]==r["level"] and x["event"]==r["event"]]
        r.update(original_episodes=len(roster),known_breach_episodes=sum(x["breach_occurred"] is True for x in roster),known_no_breach_episodes=sum(x["breach_occurred"] is False for x in roster),unknown_breach_episodes=sum(x["breach_occurred"] is None for x in roster),population="known_protected_breach_episodes; unknown_breach_support_retained_separately")
    level_table=level_summaries(levels,baseline)
    transition_rows,transitions,event_distribution=transition_tables(observations,events,results,baseline)
    raw_pin=json.loads((stage/"phase2-baseline-pin.json").read_text())
    raw_days=next(x for x in raw_pin["scenario_ledgers"] if x["id"]=="primary-one-tick-days")
    range_rows={r["broker_day"]:r for r in load_gz(ROOT/raw_days["locator"])}
    for row in days:
        if row["broker_day"] in range_rows:range_rows[row["broker_day"]]["eligible"]=row["eligible"]
    account=account_results(contexts,baseline,json.loads((stage/"selection.json").read_text()),range_roster=range_rows)
    # All costs/orderings are frozen; these sensitivity runs cannot change selection.
    cfgs=[("gross-zero-cost",Phase2Config(commission_per_side=0,slippage_ticks=0)),("net-zero-ticks",Phase2Config(slippage_ticks=0)),("net-two-ticks",Phase2Config(slippage_ticks=2)),("high-first-one-tick",Phase2Config(ordering="high_first")),("low-first-one-tick",Phase2Config(ordering="low_first")),("source-fifteen-minute-ohlc",Phase2Config(execution_minutes=15))]
    signals={(key,p.name):find_signal(ctx,p) for key,ctx in contexts.items() for p in policy_specs()}
    scenarios=[];sensitivity_pins=[]
    primary_cfg={"primary-one-tick":results}
    for name,cfg in cfgs:
        print("Executing fixed sensitivity "+name,flush=True)
        rows=[]
        for key,ctx in contexts.items():
            for p in policy_specs():
                signal=dict(signals[key,p.name],ordering=cfg.ordering,slippage_ticks=cfg.slippage_ticks,commission_per_side=cfg.commission_per_side)
                rows.append(normalize(execute_signal(signal,ctx,cfg)))
        sensitivity_pins.append(ledger(stage/"sensitivities"/(name+".jsonl.gz"),rows))
        primary_cfg[name]={p.name:[r for r in rows if r["policy"]==p.name] for p in policy_specs()}
    touch_rows=[normalize(run_policy(ctx,p)) for ctx in contexts.values() for p in policy_specs(passive_touch=True) if p.kind=="passive"]
    sensitivity_pins.append(ledger(stage/"sensitivities/passive-touch.jsonl.gz",touch_rows))
    primary_cfg["passive-touch"]={p.name:[r for r in touch_rows if r["policy"]==p.name] for p in policy_specs(passive_touch=True) if p.kind=="passive"}
    saved_baselines={"primary-one-tick":baseline}
    for name in ("gross-zero-cost","net-zero-ticks","net-two-ticks","high-first-one-tick","low-first-one-tick"):
        x=next(r for r in raw_pin["scenario_ledgers"] if r["id"]==name+"-trades")
        saved_baselines[name]={r["broker_day"]:r for r in load_gz(ROOT/x["locator"])}
    bounds=[]
    for name,by_policy in primary_cfg.items():
        for p,rows in by_policy.items():
            completed=[r["trade"] for r in rows if r["status"]=="completed"]
            base_by_day=saved_baselines.get(name)
            pairs=[]
            for r in rows:
                b=baseline[r["episode_id"]] if base_by_day is None or name=="primary-one-tick" else base_by_day.get(r["broker_day"])
                if b and b["status"]=="completed" and known_pnl(r) is not None:pairs.append(known_pnl(r)-b["net_dollars"])
            scenarios.append(dict(policy=p,scenario=name,episodes=len(rows),completed=len(completed),censored=sum(r["status"]=="censored" for r in rows),unknown=sum(r["status"]=="unknown" for r in rows),no_fill=sum(known_pnl(r)==0 and not r.get("trade") for r in rows),fills=sum(bool(r.get("trade")) for r in rows),net_dollars=sum(t["net_dollars"] for t in completed) if completed else None,gross_dollars=sum(t["raw_price_dollars"] for t in completed) if completed else None,paired_count=len(pairs),mean_difference=sum(pairs)/len(pairs) if pairs else None,baseline_comparison="matching_saved_cost_order_baseline" if name in saved_baselines else "primary_one_tick_baseline; ordering_or_fill_rule_sensitivity",slippage_ticks=next(iter(rows))["slippage_ticks"],commission_per_side=next(iter(rows))["commission_per_side"]))
    for p in results:
        high={r["episode_id"]:r for r in primary_cfg["high-first-one-tick"][p]};low={r["episode_id"]:r for r in primary_cfg["low-first-one-tick"][p]}
        for key in baseline:
            a,b=known_pnl(high[key]),known_pnl(low[key])
            bounds.append(dict(policy=p,episode_id=key,broker_day=baseline[key]["broker_day"],lower=min(a,b) if a is not None and b is not None else None,upper=max(a,b) if a is not None and b is not None else None,unknown_branch=a is None or b is None,ambiguous=a!=b,high_first=a,low_first=b))
    examples=[];example_bars=[]
    for policy in results:
        for side in ("long","short"):
            for outcome in ("win","loss"):
                pool=[r for r in results[policy] if r["status"]=="completed" and r["trade"]["side"]==side and (r["trade"]["net_dollars"]>1e-8 if outcome=="win" else r["trade"]["net_dollars"]< -1e-8)]
                if not pool:continue
                r=min(pool,key=lambda r:r["trade"]["entry_time"]);t=r["trade"];ctx=contexts[r["episode_id"]]
                examples.append(dict(policy=policy,side=side,outcome=outcome,rule="earliest_chronological_completed_net_win_loss_per_policy_actual_direction",episode_id=r["episode_id"],range_high=ctx.episode.range_high,range_low=ctx.episode.range_low,midpoint=ctx.episode.midpoint,trade=t,policy_ledger=r))
                for b in ctx.minutes:
                    if ctx.episode.entry_time<=b.timestamp<=instant(t["exit_time"]):example_bars.append(dict(policy=policy,trade_id=t["trade_id"],timestamp=b.timestamp.isoformat(),open=b.open,high=b.high,low=b.low,close=b.close,contract=b.contract))
            for outcome in ("missed_baseline_win","avoided_baseline_loss"):
                pool=[r for r in results[policy] if known_pnl(r)==0 and not r.get("trade") and baseline[r["episode_id"]]["status"]=="completed" and baseline[r["episode_id"]]["side"]==side and (baseline[r["episode_id"]]["net_dollars"]>1e-8 if outcome=="missed_baseline_win" else baseline[r["episode_id"]]["net_dollars"]< -1e-8)]
                if not pool:continue
                r=min(pool,key=lambda r:baseline[r["episode_id"]]["entry_time"]);t=baseline[r["episode_id"]];ctx=contexts[r["episode_id"]]
                examples.append(dict(policy=policy,side=side,outcome=outcome,trade_role="unchanged_baseline; alternative_known_no_fill",rule="earliest_chronological_completed_baseline_win_loss_with_known_no_fill_per_policy_direction",episode_id=r["episode_id"],range_high=ctx.episode.range_high,range_low=ctx.episode.range_low,midpoint=ctx.episode.midpoint,trade=t,policy_ledger=r))
                for b in ctx.minutes:
                    if ctx.episode.entry_time<=b.timestamp<=instant(t["exit_time"]):example_bars.append(dict(policy=policy,trade_id=t["trade_id"],timestamp=b.timestamp.isoformat(),open=b.open,high=b.high,low=b.low,close=b.close,contract=b.contract))
    selected=json.loads((stage/"selection.json").read_text())["selected_policy"]
    assessment={"selected_policy":selected,"prior_baseline_exposure":True,"decision":"baseline_retained_no_primary_qualifier"}
    if selected:
        ci=next(r for r in intervals if r["period"]=="later-assessment" and r["policy"]==selected and r["side"]=="combined" and r["block_weeks"]==4)
        fills=[r for r in results[selected] if r["status"]=="completed" and origin(baseline[r["episode_id"]])["year"] in {"2024","2025"}]
        count_years={origin(baseline[r["episode_id"]])["year"] for r in fills}
        expectancy=sum(r["trade"]["net_dollars"] for r in fills)/len(fills) if fills else None
        passed=expectancy is not None and expectancy>0 and ci["lower"] is not None and ci["lower"]>0 and len(fills)>=100 and len(count_years)>=2
        assessment.update(decision="later_criteria_passed_exposed_assessment" if passed else "later_criteria_failed_or_inconclusive",completed_fills=len(fills),years=sorted(count_years),mean_net_trade=expectancy,paired=ci,not_pristine_holdout=True)
    tables={"trade-cohorts":cohorts,"paired":paired,"timing":timing,"equity":equity,"occurrence":frequency,"recovery":recoveries,"level-opportunities":level_table,"transitions":transitions,"event-distribution":event_distribution,"interval-sensitivities":intervals,"scenarios":scenarios,"ordering-bounds":bounds,"account":account["cohorts"],"account-capacity":account["capacity_audit"],"trades":trades,"selected-example-bars":example_bars}
    for name,rows in tables.items():
        if not rows:raise ValueError("requested table has no defined row schema: "+name)
        write_csv(stage/"tables"/(name+".csv"),rows)
    save(stage/"example-selection.json",examples)
    save(stage/"assessment.json",assessment)
    save(stage/"account-settings.json",account["settings"])
    ledger(stage/"account-ledger.jsonl.gz",account["ledgers"])
    ledger(stage/"transition-ledger.jsonl.gz",transition_rows)
    save(stage/"sensitivity-completion.json",sensitivity_pins)
    save(stage/"exclusions.json",{"baseline_eligibility_roster":raw_pin["complete_day_roster"],"accepted_episodes":len(baseline),"known_no_trade_days":sum(d["no_trade"] for d in days),"unknown_first_fill_days":sum(d["eligible"] and d["unknown_outcome"] and d["accepted_breakouts"]==0 for d in days),"all_policy_unknown_censored_retained":True})
    save(stage/"metrics.json",{"run_id":stage.name,"protocol":"2.0.0","baseline_pin_sha256":sha(stage/"phase2-baseline-pin.json"),"tables":{name:{"rows":len(rows),"sha256":sha(stage/"tables"/(name+".csv"))} for name,rows in tables.items()},"assessment":assessment,"family_masks_and_semantics":"protocol.md"})
    save(stage/"execution-completion.json",{"finished_at":datetime.now(timezone.utc).isoformat(),"phase2":"computed","phase3":"uncomputed","episodes":len(baseline),"selection_sha256":sha(stage/"selection.json"),"settings_sha256":sha(stage/"config.json"),"sensitivity_scenarios":len(primary_cfg),"policy_names":list(results),"no_retuning_after_selection":True})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True)
    parser.add_argument("--phase",choices=("dev-validation","later","summarize"),required=True)
    args=parser.parse_args();stage=args.stage.resolve()
    if not stage.is_relative_to(ROOT/"work"/STUDY):raise ValueError("owning work stage required")
    if args.phase=="summarize":summarize_all(stage)
    else:execute_phase(stage,args.phase)


if __name__=="__main__":main()
