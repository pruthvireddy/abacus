"""Phase3 chronological, bounded-memory execution of frozen standalone policies.

The CLI adapter owns input/source freezing. This writer never aggregates,
selects, retunes, or automatically opens the later assessment.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from src.phase3_engine import run_episode, observe_episode, _snapshot_row, instant

NY = ZoneInfo("America/New_York")
LEDGERS = ("episodes", "events", "orders", "trades", "exposure", "monitoring", "profiles", "phase2-context")
POLICY_MODES = (("BASE", "parent_1"), ("BASE", "parent_2"),
    ("BASE", "full_parent"), ("BASE", "half_parent"),
    ("G1", "standardized"), ("G2", "standardized"),
    ("A20", "financed_overlay"), ("A50", "financed_overlay"),
    ("A20", "diagnostic_1plus1"), ("A50", "diagnostic_1plus1"),
    ("X1", "standardized"), ("X2", "standardized"), ("T50", "standardized"))
FINANCED = {"full_parent", "half_parent", "financed_overlay"}


def _year(parent):
    return instant(parent["entry_time"]).astimezone(NY).year


def _previous_equity(stage):
    """Carry actual account state across the selection boundary, including null."""
    state = {}
    path = Path(stage)/"phases/dev-validation/episodes.jsonl.gz"
    with gzip.open(path, "rt") as f:
        for line in f:
            row = json.loads(line)
            if row["mode"] in FINANCED:
                state[(row["scenario"], row["policy"], row["mode"])] = row.get("ending_equity")
    return state


def _write_stream(folder, contexts, parents, scenarios, configuration, *, initial_equities=None,
                  phase2_context=(), progress=None):
    """Write caller-supplied contexts; synthetic fixtures use this same writer."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    counts = dict.fromkeys(LEDGERS, 0)
    trace_counts = {s:{"computed_monitoring_rows":0,"retained_monitoring_rows":0,
        "computed_exposure_rows":0,"retained_exposure_rows":0} for s in scenarios}
    accounts = dict(initial_equities or {})
    selected_ids = sorted(contexts[scenarios[0]], key=lambda eid:(instant(parents[eid]["entry_time"]),eid))
    saved_context = {}
    for row in phase2_context:
        if row["episode_id"] in parents:
            saved_context.setdefault(row["episode_id"], []).append(row)
    with ExitStack() as stack:
        streams = {name:stack.enter_context(gzip.open(folder/(name+".jsonl.gz"),"xt")) for name in LEDGERS}
        def write(name, row):
            streams[name].write(json.dumps(row,allow_nan=False,separators=(",",":"))+"\n")
            counts[name] += 1
        for scenario in scenarios:
            cfg = configuration(scenario)
            if set(contexts[scenario]) != set(selected_ids):
                raise ValueError("all scenarios must retain the fixed accepted-episode roster")
            for index,eid in enumerate(selected_ids):
                day = contexts[scenario][eid]
                monitor = observe_episode(day,cfg)
                trace_counts[scenario]["computed_monitoring_rows"] += len(monitor)
                if scenario == "primary-one-tick":
                    for r in monitor:write("monitoring", {**r,"scenario":scenario})
                    trace_counts[scenario]["retained_monitoring_rows"] += len(monitor)
                parent_trace = None
                parent_result = None
                for policy,mode in POLICY_MODES:
                    key = (scenario,policy,mode)
                    eq = accounts.get(key,cfg.initial_capital)
                    result = run_episode(day,policy,cfg,mode=mode,equity_start=eq,
                        precomputed_monitoring=monitor,precomputed_parent_exposure=parent_trace)
                    if (policy,mode) == ("BASE","parent_1"):
                        parent_result, parent_trace = result, result["exposure"]
                    episode = result["episode"]
                    if mode in FINANCED:
                        if episode["status"] == "no_fill" and episode.get("net_dollars") == 0 and "ending_equity" not in episode:
                            episode["ending_equity"] = eq
                        accounts[key] = episode.get("ending_equity")
                    episode["exposure_trace_retention"] = "full_minute_path" if scenario=="primary-one-tick" else "terminal_only"
                    write("episodes",episode)
                    for name in ("events","orders","trades"):
                        for row in result[name]:write(name,row)
                    trace_counts[scenario]["computed_exposure_rows"] += len(result["exposure"])
                    retained=result["exposure"] if scenario=="primary-one-tick" else result["exposure"][-1:]
                    for r in retained:
                        write("exposure",{**r,"trace_retention":"full_minute_path" if scenario=="primary-one-tick" else "terminal_only"})
                    trace_counts[scenario]["retained_exposure_rows"] += len(retained)
                if scenario == "primary-one-tick" and parent_result is not None:
                    row=parent_result["episode"]
                    parent=day.baseline_trade
                    if parent is not None:
                        for anchor,field,at in (("original_order_decision","original_order_snapshot",parent["order_submitted_at"]),
                                               ("original_entry","entry_snapshot",parent["entry_time"])):
                            write("profiles",{"episode_id":eid,"broker_day":day.broker_day,"scenario":scenario,
                                "anchor":anchor,"decision_at":at,"snapshot":row[field]})
                    for r in monitor:
                        if r["open_position_landmark"]:
                            write("profiles",{"episode_id":eid,"broker_day":day.broker_day,"scenario":scenario,
                                "anchor":"eligible_open_position_landmark","decision_at":r["available_at"],"snapshot":r["current"]})
                    for event in saved_context.get(eid,()):
                        at = instant(event["decision_at"])
                        snapshot = _snapshot_row(day.cloud.snapshot(at,day.parent_contract),day.direction,day)
                        write("phase2-context",{**event,"broker_day":day.broker_day,"scenario":scenario,
                            "anchor":event.get("anchor","phase2_saved_event_context"),"snapshot":snapshot,
                            "scope":"saved Phase2 event timing; descriptive cloud context only, no trading combination"})
                if progress is not None:progress(scenario,index+1,len(selected_ids))
    return {"accepted_episodes":len(selected_ids),"row_counts":counts,
            "trace_counts":trace_counts,
            "account_end_states":[{"scenario":s,"policy":p,"mode":m,"equity":eq} for (s,p,m),eq in sorted(accounts.items())]}


def execute_phase(stage,phase):
    from phase3_run import (assert_freeze,load_material,contexts_for_scenario,
        config_for_scenario,retain_parent_rosters,SCENARIOS,save,sha)
    stage=Path(stage)
    if phase not in {"dev-validation","later"}:raise ValueError("explicit chronological phase required")
    freeze=assert_freeze(stage)
    folder=stage/"phases"/phase
    if folder.exists():raise FileExistsError("retain existing/failed phase attempt")
    selection_pin=None
    if phase=="dev-validation":
        if (stage/"phases/later").exists() or (stage/"selection.json").exists():
            raise ValueError("development/validation must precede selection and later assessment")
    else:
        selection=json.loads((stage/"selection-freeze.json").read_text())
        if sha(stage/"selection.json")!=selection["selection_sha256"] or selection.get("later_outcomes_opened") is not False:
            raise ValueError("frozen independently verified selection required")
        receipt=stage/selection["development_validation_receipt"]["path"]
        if sha(receipt)!=selection["development_validation_receipt"]["sha256"]:
            raise ValueError("development verification bytes changed")
        dev=json.loads((stage/"phases/dev-validation/completion.json").read_text())
        if instant(selection["frozen_at"])<instant(dev["finished_at"]):
            raise ValueError("selection chronology violated")
        selection_pin={"path":"selection.json","sha256":sha(stage/"selection.json"),
            "freeze_sha256":sha(stage/"selection-freeze.json"),"verification_sha256":sha(receipt)}
    started=datetime.now(timezone.utc).isoformat()
    starts=stage/"phase-starts"
    starts.mkdir(exist_ok=True)
    save(starts/(phase+".json"),{"phase":phase,"started_at":started,"run_id":stage.name,
        "execution_freeze_sha256":sha(stage/"execution-freeze.json"),
        "settings_sha256":freeze["settings_sha256"],"selection":selection_pin,
        "argv":sys.argv,"python_executable":sys.executable,"cwd":str(Path.cwd()),
        "environment":{"UV_CACHE_DIR":os.environ.get("UV_CACHE_DIR"),
                       "PYTHONDONTWRITEBYTECODE":os.environ.get("PYTHONDONTWRITEBYTECODE")},
        "scope":"standalone frozen policies; no selection/aggregation in execution"})
    material=load_material(stage)
    if phase=="dev-validation":retain_parent_rosters(stage,material)
    config=json.loads((stage/"config.json").read_text())
    years=set(config["evaluation"]["development_years"]+config["evaluation"]["validation_years"]) if phase=="dev-validation" else set(config["evaluation"]["later_years"]+[config["evaluation"]["replication_year"]])
    parents={i:r for i,r in material["parents"].items() if _year(r) in years}
    contexts={s:{i:d for i,d in contexts_for_scenario(material,s).items() if i in parents} for s in SCENARIOS}
    state=_previous_equity(stage) if phase=="later" else None
    def progress(scenario,done,total):
        if done==1 or done%50==0 or done==total:print(f"{phase} {scenario}: {done}/{total} fixed episodes",flush=True)
    result=_write_stream(folder,contexts,parents,tuple(SCENARIOS),config_for_scenario,
        initial_equities=state,phase2_context=material.get("phase2_context",()),progress=progress)
    artifacts=[{"path":str((folder/(name+".jsonl.gz")).relative_to(stage)),
        "sha256":sha(folder/(name+".jsonl.gz")),"bytes":(folder/(name+".jsonl.gz")).stat().st_size,
        "row_count":result["row_counts"][name]} for name in LEDGERS]
    result.update(schema_version="study23.phase3-phase-completion/v1",run_id=stage.name,
        phase=phase,status="computed",started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),
        settings_sha256=freeze["settings_sha256"],execution_freeze_sha256=sha(stage/"execution-freeze.json"),
        policy_modes=[{"policy":p,"mode":m} for p,m in POLICY_MODES],scenarios=list(SCENARIOS),
        years=sorted(years),artifacts=artifacts,selection=selection_pin,all_accepted_roster_retained=True,
        monitoring_computed_once_per_scenario_episode=True,
        trace_retention={"primary-one-tick":"full minute exposure and full expected5m monitoring",
            "sensitivities":"all episode/events/orders/trades, terminal exposure and full-trace episode extrema; full secondary paths independently reconstructed from pinned inputs"})
    assert_freeze(stage)
    save(folder/"completion.json",result)
    if phase=="later":
        save(stage/"execution-completion.json",{"schema_version":"study23.phase3-execution-completion/v1",
            "run_id":stage.name,"phase3":"computed","finished_at":result["finished_at"],
            "phases":[{"path":f"phases/{p}/completion.json","sha256":sha(stage/"phases"/p/"completion.json")} for p in ("dev-validation","later")],
            "selection_sha256":sha(stage/"selection.json"),"execution_freeze_sha256":sha(stage/"execution-freeze.json")})
    return result
