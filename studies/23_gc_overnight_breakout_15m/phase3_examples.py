"""Balanced, earliest chronological empirical case selection after evaluation.

This is a traceable presentation projection of completed ledgers and pinned raw
prices/features. It does not select trading rules or optimize chart examples.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import timedelta
import json
from pathlib import Path

from phase3_run import load_contexts,load_ledger,save,sha,instant
from phase3_metrics import write_csv

CASE_RULES={"A20":("add_win","add_loss","rejected_support"),"A50":("add_win","add_loss","rejected_support"),"X1":("loss_saved","winner_cut_short"),"X2":("loss_saved","winner_cut_short")}


def prepare(stage):
    stage=Path(stage)
    if not (stage/"execution-completion.json").exists():raise ValueError("all chronological assessment must complete before empirical selection")
    contexts,parents,roster,material=load_contexts(stage)
    episodes=[];trades=[];events=[];pins=[]
    for phase in ("dev-validation","later"):
        for name,target in (("episodes",episodes),("trades",trades),("events",events)):
            path=stage/"phases"/phase/(name+".jsonl.gz")
            pins.append({"path":str(path.relative_to(stage)),"sha256":sha(path)})
            target.extend(r for r in load_ledger(path) if r["scenario"]=="primary-one-tick")
    indexed={(r["episode_id"],r["policy"],r["mode"]):r for r in episodes}
    legs=defaultdict(list);signals=defaultdict(list)
    for t in trades:legs[(t["episode_id"],t["policy"],t["mode"])].append(t)
    for e in events:signals[(e["episode_id"],e["policy"],e["mode"])].append(e)
    cases=[];absent=[];minute_rows=[];cloud_rows=[]
    for policy,kinds in CASE_RULES.items():
        mode="diagnostic_1plus1" if policy.startswith("A") else "standardized"
        for kind in kinds:
            for direction in (1,-1):
                chosen=None
                for eid,parent in sorted(parents.items(),key=lambda item:(item[1]["entry_time"],item[0])):
                    if parent["direction"]!=direction:continue
                    k=(eid,policy,mode);episode=indexed[k];ownlegs=legs[k];ownevents=signals[k]
                    adds=[t for t in ownlegs if t.get("leg")=="add" and t["status"]=="completed"]
                    qualifying=kind=="add_win" and adds and adds[0]["net_dollars"]>1e-8 or kind=="add_loss" and adds and adds[0]["net_dollars"]<-1e-8 or kind=="rejected_support" and any(e["event"]=="first_contact_consumed" and (not e["confirmed"] or e["liquidation_net"]<=0) for e in ownevents)
                    if kind in {"loss_saved","winner_cut_short"}:
                        alternative=episode.get("net_dollars");baseline=parent.get("net_dollars")
                        qualifying=alternative is not None and baseline is not None and ((kind=="loss_saved" and baseline< -1e-8 and alternative>baseline+1e-8) or (kind=="winner_cut_short" and baseline>1e-8 and alternative<baseline-1e-8))
                    if qualifying:chosen=(eid,parent,episode,ownlegs,ownevents);break
                case_id=f"{policy.lower()}-{kind.replace('_','-')}-{'long' if direction==1 else 'short'}"
                if chosen is None:absent.append({"id":case_id,"policy":policy,"mode":mode,"kind":kind,"direction":direction,"status":"no_qualifying_saved_case"});continue
                eid,parent,episode,ownlegs,ownevents=chosen;day=contexts[eid]
                signal=next((e for e in ownevents if e["event"] in {"first_contact_consumed","ema_exit_signal"}),None)
                if signal is None:raise ValueError("selected empirical case lacks its known causal signal")
                start=instant(parent["entry_time"])-timedelta(minutes=15);end=day.cutoff
                state={"id":case_id,"episode_id":eid,"contract":parent["contract"],"policy":policy,"mode":mode,"leg":"add" if policy.startswith("A") else "original","kind":kind,"direction":direction,"parent_entry":parent["entry_time"],"parent_fill_upper":parent.get("entry_time_latest",parent["entry_time"]),"parent_entry_price":parent["entry_price"],"parent_initial_stop":parent["initial_stop"],"parent_reset_stop":parent.get("reset_stop"),"parent_reset_at":parent.get("reset_stop_active_at"),"parent_exit":parent.get("exit_time"),"parent_exit_price":parent.get("exit_price"),"parent_net_dollars":parent.get("net_dollars"),"signal_at":signal["time"],"contact_open":(instant(signal["time"])-timedelta(minutes=5)).isoformat(),"frozen_level":signal.get("frozen_level",signal.get("frozen_edge")),"liquidation_net":signal.get("liquidation_net",signal.get("original_liquidation_net")),"parent_open_at_signal":signal.get("parent_open",True),"policy_net_dollars":episode.get("net_dollars"),"action_at":next((t["entry_time"] if policy.startswith("A") else t["exit_time"] for t in ownlegs if t.get("leg")==("add" if policy.startswith("A") else "original") and (policy.startswith("A") or t["status"]=="completed")),None),"action_price":next((t["entry_price"] if policy.startswith("A") else t["exit_price"] for t in ownlegs if t.get("leg")==("add" if policy.startswith("A") else "original") and (policy.startswith("A") or t["status"]=="completed")),None),"window_start":start.isoformat(),"window_end":end.isoformat(),"legs":ownlegs,"signal":signal,"selection_rule":"first chronological qualifying saved case, separately by sign/kind and direction; not best magnitude"}
                state.update(range_high=day.range_high,range_low=day.range_low,midpoint=(day.range_high+day.range_low)/2)
                state["parent_open_at_signal"]=signal.get("parent_open",signal.get("original_open_at_signal"))
                frozen_open=instant(state["contact_open"])
                if policy=="X1":
                    firsts=[e for e in ownevents if e["event"]=="failure_first_close" and e["time"]<signal["time"] and e["frozen_edge"]==state["frozen_level"]]
                    if not firsts:raise ValueError("X1 example lacks its independently frozen first edge")
                    frozen_open=instant(firsts[-1]["time"])-timedelta(minutes=5)
                    state["frozen_level_contact_open"]=frozen_open.isoformat()
                prior=day.cloud.snapshot(frozen_open,day.parent_contract)
                state["frozen_level_available_at"]=prior.bar.available_at.isoformat() if prior.known else None
                cases.append(state)
                source_minutes={b.timestamp:b for b in day.minutes}
                t=start.replace(second=0,microsecond=0)
                while t+timedelta(minutes=1)<=end:
                    if day.expected_minute(t):
                        bar=source_minutes.get(t)
                        minute_rows.append({"case_id":case_id,"episode_id":eid,"contract":bar.contract if bar else parent["contract"],"timestamp":t.isoformat(),"available_at":(t+timedelta(minutes=1)).isoformat(),"open":bar.open if bar else None,"high":bar.high if bar else None,"low":bar.low if bar else None,"close":bar.close if bar else None,"usable":bar is not None})
                    t+=timedelta(minutes=1)
                for bar in day.cloud.for_window(start-timedelta(minutes=5),end):
                    if not start<=bar.available_at<=end:continue
                    cloud_rows.append({"case_id":case_id,"episode_id":eid,"contract":bar.contract or parent["contract"],"timestamp":bar.timestamp.isoformat(),"available_at":bar.available_at.isoformat(),"open":bar.open,"high":bar.high,"low":bar.low,"close":bar.close,"ema20":bar.ema20,"ema50":bar.ema50,"feature_valid":bar.feature_valid,"usable":bar.usable,"quality_reason":bar.quality_reason})
    save(stage/"example-selection.json",{"schema_version":"study23.phase3-balanced-examples/v1","run_id":stage.name,"rules":CASE_RULES,"cases":cases,"absent_cases":absent,"ledger_pins":pins,"selection_is_not_trading_rule_selection":True,"source_selection":"earliest chronological, by frozen case kind and side; no chart popularity or best P&L selection","config_sha256":sha(stage/"config.json")})
    if minute_rows:write_csv(stage/"tables/selected-example-minutes.csv",minute_rows)
    if cloud_rows:write_csv(stage/"tables/selected-example-cloud.csv",cloud_rows)
    return {"status":"prepared","cases":len(cases),"absent_cases":len(absent),"minute_rows":len(minute_rows),"cloud_rows":len(cloud_rows)}


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--stage",type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.stage),indent=2))
