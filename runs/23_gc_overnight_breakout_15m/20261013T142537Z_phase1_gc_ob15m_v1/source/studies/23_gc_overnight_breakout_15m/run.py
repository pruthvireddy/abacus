"""Execute only frozen Phase 1 scenarios against already audited saved inputs."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from metrics import enrich, cohort, summarize, write_csv
from prepare_inputs import load_prepared
from src.engine import Bar, EngineConfig, run_backtest, ordering_bounds

STUDY = "23_gc_overnight_breakout_15m"
HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def snapshot(stage):
    files = [*(HERE / name for name in ("run.py", "metrics.py", "prepare_inputs.py")),
             *HERE.glob("*.json"), *HERE.glob("*.md"),
             *HERE.glob("src/*.py"), *HERE.glob("tests/*.py"), *HERE.glob("sources/*")]
    # Explicit consumer dependencies; this is a bounded snapshot, not automatic
    # dependency discovery or a claim of full execution-environment equivalence.
    files += [WORKSPACE / "packages/bhishma/src/abacus_bhishma" / name for name in
              ("continuous_loader.py", "manifest_selection.py", "paths.py", "ema_cloud.py", "calendar.py")]
    rows = []
    for file in files:
        relative = file.relative_to(WORKSPACE)
        target = stage / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, target)
        rows.append({"path": str(target.relative_to(stage)), "sha256": sha(target)})
    shutil.copyfile(WORKSPACE / "uv.lock", stage / "environment.lock")
    status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=WORKSPACE, text=True)
    (stage / "git-status.txt").write_text(status)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    save(stage / "execution-freeze.json", {"study_id": STUDY, "run_id": stage.name,
         "frozen_before_outcomes_at": datetime.now(timezone.utc).isoformat(),
         "revision": revision, "dirty": bool(status), "source_files": rows,
         "settings_sha256": sha(HERE / "config-phase1.json"),
         "inputs_sha256": sha(HERE / "phase1-inputs.lock.json"),
         "python": sys.version, "packages": {name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "pyarrow")}})
    shutil.copyfile(HERE / "config-phase1.json", stage / "config.json")
    shutil.copyfile(HERE / "phase1-inputs.lock.json", stage / "inputs.lock.json")
    shutil.copyfile(HERE / "protocol-phase1.md", stage / "protocol.md")


def serialize_ledger(retained, name, rows):
    target = retained / (name + ".jsonl.gz")
    if target.exists():
        raise FileExistsError(target)
    with gzip.open(target, "wt") as stream:
        for row in rows:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
    return {"id": name, "locator": str(target.relative_to(WORKSPACE)),
            "row_count": len(rows), "bytes": target.stat().st_size, "sha256": sha(target),
            "schema": "study23-phase1-dictionary-ledger/v1", "retention": "retained_private_outside_ordinary_git"}


def complete_roster(result, coverage):
    by_day = {d["broker_day"]: d for d in result.days}
    rows = []
    for source in coverage.to_dict("records"):
        day = source["broker_date"]
        row = dict(by_day.get(day, dict(broker_day=day, accepted_breakouts=0,
            executable_fills=0, completed_trades=0, censored_trades=0,
            quantity_skips=0, no_trade=False, unknown_outcome=False)))
        # Valid-range and eligibility support come from the independently frozen
        # causal audit, including entirely unobserved/closed calendar days.
        row.update(valid_range=bool(source["valid_range"]), eligible=bool(source["eligible"]),
            exclusion_reason=source["reason"], expected_range_minutes=source["expected_range_minutes"],
            observed_range_minutes=source["observed_range_minutes"],
            calendar_event=source["calendar_event"], later_missing_trading_minutes=source["later_missing_trading_minutes"],
            decision_available_at=source["decision_available_at"])
        if source["eligible"] and day not in by_day:
            row["unknown_outcome"] = True
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    if not stage.is_relative_to(WORKSPACE / "work" / STUDY):
        raise ValueError("execution stage must belong to this study")
    if (stage / "execution-freeze.json").exists():
        raise FileExistsError("this execution stage has already been frozen")
    audit = stage / "input-audit"
    inventory = json.loads((audit / "audit-artifacts.json").read_text())
    for item in inventory:
        path = audit / item["path"]
        if sha(path) != item["sha256"]:
            raise ValueError(f"audited prepared bytes changed: {path}")
    snapshot(stage)
    minutes, bars15, coverage, expected = load_prepared(audit)
    audit_summary = json.loads((audit / "input-summary.json").read_text())
    schedule_ns = expected.timestamp.astype("int64").to_numpy()
    # 24 source records outside pinned normal market schedule remain retained
    # as an explicit audit limitation; they are not signal or fill evidence.
    use = minutes.timestamp.isin(expected.timestamp)
    minutes = minutes.loc[use].reset_index(drop=True)
    calendar_seconds = set((schedule_ns // 10**9).tolist())
    del expected
    def expected_minute(value):
        return int(value.timestamp()) in calendar_seconds
    bars = [Bar(t.to_pydatetime(), float(o), float(h), float(l), float(c), str(contract),
                available.to_pydatetime()) for t,o,h,l,c,contract,available in
            minutes[["timestamp","open","high","low","close","contract","available_at"]].itertuples(index=False, name=None)]
    source15 = [Bar(t.to_pydatetime(),float(o),float(h),float(l),float(c),str(contract),a.to_pydatetime())
                for t,o,h,l,c,contract,a in bars15.loc[bars15.observed_count.gt(0) & bars15.contract_count.eq(1),
                   ["timestamp","open","high","low","close","contract","available_at"]].itertuples(index=False,name=None)]
    eligibility = {r["broker_date"]:r for r in coverage.to_dict("records")}
    retained = WORKSPACE / "data/research/sahadeva" / STUDY / stage.name
    retained.mkdir(parents=True, exist_ok=False)
    inventories, scenarios, bounds_results = [], [], {}
    base = dict(commission_per_side=2.5, slippage_ticks=1)
    configs = [
        ("primary-one-tick", EngineConfig(**base), bars),
        ("gross-zero-cost", EngineConfig(commission_per_side=0,slippage_ticks=0), bars),
        ("net-zero-ticks", EngineConfig(commission_per_side=2.5,slippage_ticks=0), bars),
        ("net-two-ticks", EngineConfig(commission_per_side=2.5,slippage_ticks=2), bars),
        ("high-first-one-tick", EngineConfig(**base,ordering="high_first"),bars),
        ("low-first-one-tick", EngineConfig(**base,ordering="low_first"),bars),
        ("native-observed-one-minute", EngineConfig(**base,model="native_strategy_approx"),bars),
        ("source-fifteen-minute-ohlc", EngineConfig(**base,model="native_strategy_approx",execution_minutes=15),source15),
        ("source-account", EngineConfig(model="native_strategy_approx",sizing="source_account",
            commission_per_side=0,commission_cash_per_order=.4,slippage_ticks=0),bars),
    ]
    elapsed = time.monotonic()
    for name, config, scenario_bars in configs:
        print(f"Executing frozen scenario {name}", flush=True)
        result = run_backtest(scenario_bars,config,range_eligibility=eligibility,expected_minute=expected_minute)
        for kind in ("trades","orders","events","days"):
            inventories.append(serialize_ledger(retained,name+"-"+kind,getattr(result,kind)))
        days = complete_roster(result,coverage) if config.model=="validated_native" else result.days
        selected = [enrich(t) for t in result.trades]
        summary = cohort(selected,days,intervals=False)
        scenario = {"scenario":name,"completed":summary["completed"],"censored":summary["censored"],
            "ambiguous":summary["ambiguous"],"net_dollars":summary["net_dollars"],"net_points":summary["net_points"],
            "mean_net_dollars":summary["mean_net_dollars"],"net_r":summary["net_r"],
            "r_denominator":summary["r_denominator"],"win_rate":summary["win_rate"],"wins":summary["wins"],
            "losses":summary["losses"],"breakevens":summary["breakevens"],"profit_factor":summary["profit_factor"],
            "dd_dollars":summary["max_drawdown_dollars"],"fills":len(result.trades),
            "quantity_skip_side_days":sum(d["quantity_skips"] for d in result.days),
            "quantity_skip_days":sum(d["quantity_skips"]>0 for d in result.days),
            "slippage_ticks":config.slippage_ticks,"commission_per_side":config.commission_per_side,
            "execution_model":config.model,"execution_minutes":config.execution_minutes}
        scenarios.append(scenario)
        save(stage / "scenario-configs" / (name+".json"),asdict(config))
        if name == "primary-one-tick":
            primary, cohorts, timing, equity = summarize(result.trades,days)
            write_csv(stage / "tables/primary-trades.csv",primary)
            write_csv(stage / "tables/days.csv",days)
            write_csv(stage / "tables/cohorts.csv",cohorts)
            write_csv(stage / "tables/timing.csv",timing)
            write_csv(stage / "tables/equity.csv",equity)
            write_csv(stage / "tables/annual-coverage.csv",audit_summary["annual"])
            save(stage / "metrics.json",{"cohorts":cohorts,"timing":timing,
                 "metric_conventions":"protocol.md", "uncertainty_seed":230015})
            save(stage / "exclusions.json",[{k:d.get(k) for k in
                ("broker_day","eligible","exclusion_reason","unknown_outcome","later_missing_trading_minutes")}
                for d in days])
            examples, selections = [], []
            for side in ("long","short"):
                for outcome in ("win","loss"):
                    candidates = [t for t in primary if t["side"]==side and t["status"]=="completed"
                                  and (t["net_dollars"]>1e-8 if outcome=="win" else t["net_dollars"] < -1e-8)]
                    if not candidates: continue
                    trade = min(candidates,key=lambda x:x["entry_time"])
                    start = pd.Timestamp(trade["broker_day"]+"T00:00:00+03:00").tz_convert("UTC")
                    end = pd.Timestamp(trade["exit_time"]) + pd.Timedelta(minutes=1)
                    view = minutes.loc[(minutes.timestamp>=start)&(minutes.timestamp<end)&minutes.contract.eq(trade["contract"]),
                         ["timestamp","open","high","low","close","contract"]].copy()
                    view["trade_id"]=trade["trade_id"]
                    examples += view.to_dict("records")
                    selections.append({"side":side,"outcome":outcome,"trade_id":trade["trade_id"],
                                       "rule":"earliest chronological completed net win/loss per side", "trade":trade})
            for row in examples: row["timestamp"]=row["timestamp"].isoformat()
            write_csv(stage / "tables/selected-example-bars.csv",examples)
            save(stage / "example-selection.json",selections)
        if name in ("high-first-one-tick","low-first-one-tick"):
            bounds_results[name]=result
        print(json.dumps(scenario,allow_nan=False),flush=True)
    write_csv(stage / "tables/scenarios.csv",scenarios)
    bounds = ordering_bounds(bounds_results["high-first-one-tick"],bounds_results["low-first-one-tick"])
    write_csv(stage / "tables/ordering-bounds.csv",bounds)
    save(stage / "events.manifest.json",inventories)
    save(stage / "execution-completion.json",{"finished_at":datetime.now(timezone.utc).isoformat(),
        "seconds":time.monotonic()-elapsed,"scenarios":len(scenarios),"source_account_attainability":"separate_whole_contract_sizing",
        "excluded_outside_normal_schedule_source_rows":int((~use).sum()),"phase2":"uncomputed"})


if __name__ == "__main__":
    main()
