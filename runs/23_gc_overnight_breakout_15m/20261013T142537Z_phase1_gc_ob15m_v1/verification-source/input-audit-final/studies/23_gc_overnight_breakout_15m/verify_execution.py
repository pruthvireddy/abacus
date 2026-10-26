"""Independent Phase 1 minute-path and saved-metric reconciliation.

No imports from the strategy engine, runner, or metrics producer are permitted.
The primary oracle uses the frozen complete-range audit, independently walks
every qualified day, and records unknown opportunities before any observed fill.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

NY = ZoneInfo("America/New_York")
BROKER = "Etc/GMT-3"


def moment(value):
    return pd.Timestamp(value).tz_convert("UTC")


def tick_round(price):
    return float((Decimal(str(price)) / Decimal("0.1")).quantize(Decimal("1"),
                 rounding=ROUND_HALF_UP) * Decimal("0.1"))


def stamp(value):
    return moment(value).isoformat().replace("+00:00", "Z")


def cohort_time(value):
    local = moment(value).tz_convert("America/New_York")
    clock = local.hour * 60 + local.minute
    session = "Asia" if clock >= 1200 or clock < 120 else "London" if clock < 540 else "New York" if 570 <= clock < 960 else "Outside"
    return dict(year=str(local.year), session=session, hour=local.hour,
                weekday=local.strftime("%A"), entry_ny=local.isoformat())


def oracle_day(frame, coverage, expected_times, config):
    """Independently reconstruct one quality-qualified daily first fill.

    Uses minute-opening integer keys and state only within a known broker day.
    The quality overlay censors the first unavailable execution minute; it never
    invents the indicator's next-observed-open fallback exit.
    """
    if not bool(coverage["eligible"]):
        return None, "excluded"
    start = moment(coverage["decision_available_at"])
    cutoff = moment(coverage["trading_end_utc"])
    high, low = float(coverage["range_high"]), float(coverage["range_low"])
    slip = float(config["slippage_ticks"]) * .1
    fee = float(config["commission_per_side"])
    fixed_contract = coverage["range_contract"]
    bars = {int(r.timestamp.value): r for r in frame.itertuples(index=False)}
    step = 60_000_000_000
    stop = entry = initial = None
    position = None
    reset = None
    reset_at = None
    reset_queued = False
    entry_bucket = None
    mfe = mae = 0.
    last_close = None
    last_observed = None
    status = "no_trade"

    def mark(price):
        nonlocal mfe, mae
        excursion = position * (float(price) - entry)
        mfe = max(mfe, excursion)
        mae = max(mae, -excursion)

    def complete(raw_exit, when, reason, precision):
        mark(raw_exit)
        exit_price = float(raw_exit) - position * slip
        gross = position * (exit_price - entry)
        raw_points = position * (float(raw_exit) - result["entry_price_raw"])
        risk = position * (entry - initial)
        net = 100 * gross - 2 * fee
        source_risk = abs(entry - stop) * 100
        result.update(status="completed", exit_time=stamp(when), exit_price_raw=float(raw_exit),
            exit_price=exit_price, exit_reason=reason, exit_time_precision=precision,
            initial_stop=initial, reset_stop=reset, reset_stop_active_at=reset_at,
            risk_initial_points=risk if risk > 0 else None,
            risk_initial_dollars=risk*100 if risk > 0 else None,
            risk_effective_points=position*(entry-stop) if position*(entry-stop)>0 else None,
            risk_effective_dollars=position*(entry-stop)*100 if position*(entry-stop)>0 else None,
            source_risk_dollars=source_risk if source_risk>0 else None,
            raw_price_points=raw_points, raw_price_dollars=raw_points*100,
            gross_points=gross, gross_dollars=gross*100, commission_dollars=2*fee,
            net_points=net/100, net_dollars=net,
            gross_r=gross/risk if risk>0 else None,
            net_r=net/(risk*100) if risk>0 else None,
            source_style_r=net/source_risk if source_risk>0 else None,
            holding_minutes=(moment(when)-moment(result["entry_time"])).total_seconds()/60,
            holding_bars=int((moment(when).floor("15min")-entry_bucket).total_seconds()/900),
            mfe_points=mfe, mae_points=mae, censor_reason=None)
        return result, "completed"

    result = None
    # One additional minute at cutoff supplies the scheduled market-open exit.
    for ns in range(int(start.value), int(cutoff.value)+step, step):
        current = pd.Timestamp(ns, tz="UTC")
        row = bars.get(ns)
        if ns not in expected_times:
            continue
        # The preceding entry candle can be complete even when this next minute
        # is absent. Its observed final close still supports the reset decision.
        if result is not None and reset is None and current == entry_bucket+pd.Timedelta(minutes=15):
            reset = tick_round(entry*(1-position*.01))
            reset_at = stamp(current)
            stop = reset
            reset_queued = position*(last_close-stop) <= 0
        if row is None:
            if result is None:
                return None, "unknown"
            result.update(status="censored", censor_reason="missing_expected_execution_minutes",
                exit_time=None, exit_reason=None, reset_stop=reset, reset_stop_active_at=reset_at,
                last_observed_at=stamp(last_observed+pd.Timedelta(minutes=1)),
                mfe_points=mfe, mae_points=mae)
            return result, "censored"
        if row.contract != fixed_contract:
            if result is None:
                return None, "unknown_contract_transition"
            result.update(status="censored", censor_reason="contract_transition", exit_time=None,
                exit_reason=None, reset_stop=reset, reset_stop_active_at=reset_at)
            return result, "censored"
        # At the boundary, all previous minutes have been observed. Only now is
        # an entry-candle close decision available to this independent oracle.
        if result is not None:
            through_open = position*(float(row.open)-stop) <= 0
            if current >= cutoff:
                reason = "stop" if (through_open or reset_queued) and config["timed_exit_priority"]=="stop_first" else "time"
                return complete(row.open, current, reason, "observed_open")
            if through_open or reset_queued:
                return complete(row.open, current, "stop", "observed_open")
        if current >= cutoff:
            return None, "no_trade"
        source_first_high = float(row.high)-float(row.open) < float(row.open)-float(row.low)
        high_first = config["ordering"] == "high_first" or (config["ordering"]=="source_ohlc" and source_first_high)
        path = [float(row.open), float(row.high) if high_first else float(row.low),
                float(row.low) if high_first else float(row.high), float(row.close)]
        if result is None and (float(row.open)>=high or float(row.open)<=low):
            position = 1 if float(row.open)>=high else -1
            raw_entry = float(row.open)
            initial = tick_round((high if position==1 else low)*(1-position*.01))
            entry = raw_entry+position*slip
            stop = initial
            entry_bucket = current.floor("15min")
            result = dict(broker_day=coverage["broker_date"], side="long" if position==1 else "short",
                contract=fixed_contract, entry_time=stamp(current), entry_price_raw=raw_entry,
                entry_price=entry, entry_time_precision="observed_open", order_active_at=stamp(start),
                signal_available_at=stamp(entry_bucket+pd.Timedelta(minutes=15)), quantity=1.,
                gap_entry=raw_entry != (high if position==1 else low))
        for left, right in zip(path, path[1:]):
            if result is None:
                direction = 1 if right>left and left<=high<=right else -1 if right<left and right<=low<=left else 0
                if direction:
                    position = direction
                    raw_entry = high if position==1 else low
                    initial = tick_round(raw_entry*(1-position*.01))
                    entry = raw_entry+position*slip
                    stop = initial
                    entry_bucket = current.floor("15min")
                    result = dict(broker_day=coverage["broker_date"], side="long" if position==1 else "short",
                        contract=fixed_contract, entry_time=stamp(current), entry_price_raw=raw_entry,
                        entry_price=entry, entry_time_precision="within_bar", order_active_at=stamp(start),
                        signal_available_at=stamp(entry_bucket+pd.Timedelta(minutes=15)), quantity=1., gap_entry=False)
                    left = raw_entry
            if result is not None:
                mark(left)
                if position*(left-stop)<=0 or position*(right-stop)<=0:
                    return complete(left if position*(left-stop)<=0 else stop, current, "stop", "within_bar")
                mark(right)
        last_close = float(row.close)
        last_observed = current
    if result is not None:
        result.update(status="censored", censor_reason="retained_endpoint_open", exit_time=None,
            exit_reason=None, reset_stop=reset, reset_stop_active_at=reset_at)
        return result, "censored"
    return None, status


class Comparisons:
    def __init__(self):
        self.cells = 0
        self.mismatches = []

    def equal(self, actual, expected, context, *, tolerance=1e-7):
        self.cells += 1
        if isinstance(actual, str) and actual == "": actual = None
        if isinstance(expected, str) and expected == "": expected = None
        if isinstance(expected, bool) and isinstance(actual, str) and actual.lower() in ("true","false"):
            actual = actual.lower()=="true"
        if isinstance(expected, (int, float, np.integer, np.floating)) and not isinstance(expected, bool):
            try:
                passed = math.isfinite(float(actual)) and math.isclose(float(actual),float(expected),abs_tol=tolerance,rel_tol=1e-10)
            except (TypeError, ValueError):
                passed = False
        else:
            passed = actual == expected
        if not passed and len(self.mismatches)<200:
            self.mismatches.append(dict(context=context, actual=actual, expected=expected))


def read_ledger(path):
    with gzip.open(path,"rt") as stream:
        return [json.loads(line) for line in stream]


def independent_stats(trades):
    closed = sorted([t for t in trades if t["status"]=="completed"],key=lambda t:(t["exit_time"],t["trade_id"]))
    values = [float(t["net_dollars"]) for t in closed]
    wins = [v for v in values if v>1e-8]
    losses = [v for v in values if v<-1e-8]
    zeros = [v for v in values if abs(v)<=1e-8]
    valid_r = [float(t["net_r"]) for t in closed if t.get("net_r") is not None]
    source_r = [float(t["source_style_r"]) for t in closed if t.get("source_style_r") is not None]
    cumulative = np.cumsum(np.r_[0.,values])
    dd = float(np.max(np.maximum.accumulate(cumulative)-cumulative)) if values else None
    streak = maximum = 0
    for value in values:
        streak = streak+1 if value < -1e-8 else 0
        maximum = max(maximum,streak)
    n = len(values)
    if n:
        z = 1.959963984540054
        probability = len(wins)/n
        center=(probability+z*z/(2*n))/(1+z*z/n)
        half=z*math.sqrt(probability*(1-probability)/n+z*z/(4*n*n))/(1+z*z/n)
        rate_low,rate_high=center-half,center+half
    else:
        rate_low=rate_high=None
    def summation(field): return sum(float(t[field]) for t in closed) if closed else None
    return dict(accepted_breakouts=len(trades), executable_fills=len(trades), fills=len(trades),
        completed=len(closed),censored=len(trades)-len(closed),wins=len(wins),losses=len(losses),breakevens=len(zeros),
        ambiguous=sum(bool(t.get("ambiguous")) for t in trades),win_rate=len(wins)/n if n else None,
        win_rate_low=rate_low,win_rate_high=rate_high,gross_points=summation("raw_price_points"),
        gross_dollars=summation("raw_price_dollars"),net_points=summation("net_points"),net_dollars=sum(values) if n else None,
        cost_dollars=sum(float(t["raw_price_dollars"])-float(t["net_dollars"]) for t in closed) if n else None,
        net_r=sum(valid_r) if valid_r else None,r_denominator=len(valid_r),invalid_r=n-len(valid_r),
        expectancy_r=mean(valid_r) if valid_r else None,source_style_net_r=sum(source_r) if source_r else None,
        source_style_r_denominator=len(source_r),mean_net_dollars=mean(values) if values else None,
        median_net_dollars=median(values) if values else None,average_win_dollars=mean(wins) if wins else None,
        average_loss_dollars=mean(losses) if losses else None,win_sum_dollars=sum(wins),loss_sum_dollars=sum(losses),
        profit_factor=sum(wins)/-sum(losses) if losses else None,payoff_ratio=mean(wins)/-mean(losses) if wins and losses else None,
        mfe_points=mean(float(t["mfe_points"]) for t in closed) if closed else None,
        mae_points=mean(float(t["mae_points"]) for t in closed) if closed else None,
        holding_minutes=mean(float(t["holding_minutes"]) for t in closed) if closed else None,
        median_holding_minutes=median(float(t["holding_minutes"]) for t in closed) if closed else None,
        stop_exits=sum(t["exit_reason"] in ("stop","reset_stop") for t in closed),
        timed_exits=sum(t["exit_reason"] in ("time","timed") for t in closed),
        max_drawdown_dollars=dd,dd_dollars=dd,max_losing_streak=maximum if closed else None,
        distinct_broker_days=len({t["broker_day"] for t in trades}))


def independent_interval(trades,field,days):
    if not trades or not days: return None,None
    origin=min(datetime.fromisoformat(d["broker_day"]) for d in days)
    limit=max(datetime.fromisoformat(d["broker_day"]) for d in days)
    block_count=(limit-origin).days//28+1
    numerator=np.zeros(block_count)
    denominator=np.zeros(block_count)
    for trade in trades:
        if trade["status"]!="completed" or trade.get(field) is None:continue
        block=(datetime.fromisoformat(trade["broker_day"])-origin).days//28
        numerator[block]+=float(trade[field]); denominator[block]+=1
    if not denominator.sum():return None,None
    random=np.random.default_rng(230015)
    draws=random.integers(0,block_count,size=(10000,block_count))
    sampled_num=numerator[draws].sum(axis=1)
    sampled_den=denominator[draws].sum(axis=1)
    valid=sampled_den>0
    return tuple(float(x) for x in np.quantile(sampled_num[valid]/sampled_den[valid],[.025,.975]))


def verify_selected_tables(stage):
    """Check remaining selected evidence against retained byte identities/rows."""
    stage=Path(stage).resolve()
    workspace=Path(__file__).resolve().parents[2]
    checks=Comparisons()
    inventory=json.loads((stage/"events.manifest.json").read_text())
    index={item["id"]:workspace/item["locator"] for item in inventory}
    lock=json.loads((stage/"inputs.lock.json").read_text())
    for record in lock["files"]:
        path=workspace/record["path"]
        checks.equal(path.stat().st_size,record["bytes"],"pinned_size:"+record["path"])
        digest=hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda:stream.read(1024*1024),b""):digest.update(block)
        checks.equal(digest.hexdigest(),record["sha256"],"pinned_sha256:"+record["path"])
    summary=json.loads((stage/"input-audit/input-summary.json").read_text())
    annual=pd.read_csv(stage/"tables/annual-coverage.csv",dtype=str,keep_default_na=False).to_dict("records")
    checks.equal(len(annual),len(summary["annual"]),"annual_coverage_rows")
    for actual,expected in zip(annual,summary["annual"]):
        for field,value in expected.items():checks.equal(actual[field],value,"annual_coverage:"+str(expected["year"])+":"+field)
    high={trade["broker_day"]:trade for trade in read_ledger(index["high-first-one-tick-trades"])}
    low={trade["broker_day"]:trade for trade in read_ledger(index["low-first-one-tick-trades"])}
    bounds=pd.read_csv(stage/"tables/ordering-bounds.csv",dtype=str,keep_default_na=False).to_dict("records")
    checks.equal(len(bounds),len(high.keys()|low.keys()),"ordering_bound_rows")
    for row in bounds:
        day=row["broker_day"]
        h,l=high.get(day),low.get(day)
        valid=h is not None and l is not None and h["status"]==l["status"]=="completed"
        values=[h["net_dollars"],l["net_dollars"]] if valid else []
        expected=dict(high_first_net_dollars=values[0] if valid else None,
            low_first_net_dollars=values[1] if valid else None,
            adverse_net_dollars=min(values) if valid else None,
            favorable_net_dollars=max(values) if valid else None,
            outcome_ordering_sensitive=values[0]!=values[1] if valid else None,
            side_ordering_sensitive=h["side"]!=l["side"] if valid else None,
            unknown_branch=not valid)
        for field,value in expected.items():checks.equal(row[field],value,"ordering_bounds:"+day+":"+field)
    primary=read_ledger(index["primary-one-tick-trades"])
    selection=json.loads((stage/"example-selection.json").read_text())
    for example in selection:
        side,outcome=example["side"],example["outcome"]
        candidates=[t for t in primary if t["status"]=="completed" and t["side"]==side
            and (t["net_dollars"]>1e-8 if outcome=="win" else t["net_dollars"]<-1e-8)]
        selected=min(candidates,key=lambda t:t["entry_time"])
        checks.equal(example["trade_id"],selected["trade_id"],"example_selection:"+side+":"+outcome)
        for field,value in selected.items():checks.equal(example["trade"][field],value,"example_ledger:"+example["trade_id"]+":"+field)
    minutes=pq.ParquetFile(stage/"input-audit/minutes.parquet").read().to_pandas()
    # The runner explicitly excluded outside-normal-schedule prints for execution
    # and therefore for empirical example paths.
    minutes=minutes.loc[minutes.scheduled].set_index("timestamp")
    examples=pd.read_csv(stage/"tables/selected-example-bars.csv",dtype=str,keep_default_na=False).to_dict("records")
    for row in examples:
        timestamp=moment(row["timestamp"])
        source=minutes.loc[timestamp]
        for field in ("open","high","low","close","contract"):
            checks.equal(row[field],source[field],"example_pinned_minute:"+row["trade_id"]+":"+row["timestamp"]+":"+field)
    for example in selection:
        trade=example["trade"]
        start=moment(trade["broker_day"]+"T00:00:00+03:00")
        end=moment(trade["exit_time"])+pd.Timedelta(minutes=1)
        expected_count=int(((minutes.index>=start)&(minutes.index<end)&minutes.contract.eq(trade["contract"])).sum())
        checks.equal(sum(row["trade_id"]==trade["trade_id"] for row in examples),expected_count,"example_path_count:"+trade["trade_id"])
    exclusions=json.loads((stage/"exclusions.json").read_text())
    days=pd.read_csv(stage/"tables/days.csv",dtype=str,keep_default_na=False).to_dict("records")
    checks.equal(len(exclusions),len(days),"exclusion_roster_count")
    for saved,day in zip(exclusions,days):
        for field,value in saved.items():checks.equal(day[field],value,"exclusion_roster:"+saved["broker_day"]+":"+field)
    return dict(status="passed" if not checks.mismatches else "failed",checked_at=datetime.now(timezone.utc).isoformat(),
        comparison_cells=checks.cells,mismatches=checks.mismatches,tolerance=dict(absolute=1e-7,relative=1e-10),
        scope="all selected immutable input file bytes, annual coverage, daywise ordering bounds, deterministic example selection and every empirical example OHLC/source minute, full exclusions roster")


def verify(stage):
    stage=Path(stage).resolve()
    workspace=Path(__file__).resolve().parents[2]
    comparison=Comparisons()
    inventory=json.loads((stage/"events.manifest.json").read_text())
    ledger_index={item["id"]:workspace/item["locator"] for item in inventory}
    for item in inventory:
        data=(workspace/item["locator"]).read_bytes()
        comparison.equal(len(data),item["bytes"],f"ledger_bytes:{item['id']}")
        comparison.equal(hashlib.sha256(data).hexdigest(),item["sha256"],f"ledger_hash:{item['id']}")
    audit=stage/"input-audit"
    minutes=pq.ParquetFile(audit/"minutes.parquet").read().to_pandas()
    minutes=minutes.loc[minutes.scheduled].copy()
    minutes["broker_date"]=minutes.timestamp.dt.tz_convert(BROKER).dt.date.astype(str)
    groups={key:part for key,part in minutes.groupby("broker_date",sort=False)}
    coverage=pd.read_csv(audit/"coverage-roster.csv",keep_default_na=False).to_dict("records")
    expected=pq.ParquetFile(audit/"expected-minutes.parquet").read().to_pandas()
    expected_times=set(expected.timestamp.astype("int64").tolist())
    scenario_rows=pd.read_csv(stage/"tables/scenarios.csv",keep_default_na=False).to_dict("records")
    scenario_reports=[]
    primary=[]
    for scenario in scenario_rows:
        name=scenario["scenario"]
        config=json.loads((stage/"scenario-configs"/(name+".json")).read_text())
        trades=read_ledger(ledger_index[name+"-trades"])
        days=read_ledger(ledger_index[name+"-days"])
        events=read_ledger(ledger_index[name+"-events"])
        orders=read_ledger(ledger_index[name+"-orders"])
        for trade in trades:
            context=f"{name}:{trade['trade_id']}"
            economics=cohort_time(trade["entry_time"])
            comparison.equal(trade["entry_year"],int(economics["year"]),context+":year")
            sessions={"Asia":"asia","London":"london","New York":"new_york","Outside":"outside_named_sessions"}
            comparison.equal(trade["entry_session"],sessions[economics["session"]],context+":session")
            comparison.equal(trade["entry_hour"],economics["hour"],context+":hour")
            comparison.equal(trade["entry_weekday_name"],economics["weekday"],context+":weekday")
            direction=1 if trade["side"]=="long" else -1
            risk=direction*(float(trade["entry_price"])-float(trade["initial_stop"]))
            comparison.equal(trade["risk_initial_points"],risk if risk>0 else None,context+":risk_points")
            comparison.equal(trade["risk_initial_dollars"],risk*100*trade["quantity"] if risk>0 else None,context+":risk_dollars")
            if trade["status"]=="completed":
                movement=direction*(float(trade["exit_price"])-float(trade["entry_price"]))
                commission=2*config["commission_cash_per_order"] if config["commission_cash_per_order"] is not None else 2*config["commission_per_side"]*trade["quantity"]
                net=movement*100*trade["quantity"]-commission
                comparison.equal(trade["gross_points"],movement,context+":gross_points")
                comparison.equal(trade["commission_dollars"],commission,context+":commission")
                comparison.equal(trade["net_dollars"],net,context+":net_dollars")
                comparison.equal(trade["net_points"],net/(100*trade["quantity"]),context+":net_points")
                comparison.equal(trade["net_r"],net/(risk*100*trade["quantity"]) if risk>0 else None,context+":net_r")
                effective=trade["reset_stop"] if trade["reset_stop"] is not None else trade["initial_stop"]
                source_risk=abs(float(trade["entry_price"])-float(effective))*100*trade["quantity"]
                comparison.equal(trade["source_style_r"],net/source_risk if source_risk>0 else None,context+":source_r")
            else:
                for field in ("exit_time","net_dollars","net_r","gross_points","source_style_r"):
                    comparison.equal(trade[field],None,context+":censored_null:"+field)
        counts={day:[] for day in {d["broker_day"] for d in days}}
        for trade in trades:counts.setdefault(trade["broker_day"],[]).append(trade)
        for day in days:
            assigned=counts[day["broker_day"]]
            comparison.equal(day["accepted_breakouts"],len(assigned),name+":day_accept:"+day["broker_day"])
            comparison.equal(day["completed_trades"],sum(t["status"]=="completed" for t in assigned),name+":day_complete:"+day["broker_day"])
            comparison.equal(day["censored_trades"],sum(t["status"]=="censored" for t in assigned),name+":day_censor:"+day["broker_day"])
            comparison.equal(len(assigned)<=1,True,name+":one_per_day:"+day["broker_day"])
        for trade in trades:
            related=[e for e in events if e.get("trade_id")==trade["trade_id"]]
            comparison.equal(sum(e["event"]=="entry" for e in related),1,name+":entry_event:"+trade["trade_id"])
            comparison.equal(sum(e["event"] in ("exit","censor") for e in related),1,name+":exit_event:"+trade["trade_id"])
            comparison.equal(sum(e["event"]=="stop_reset" for e in related),int(trade["reset_stop"] is not None),name+":reset_event:"+trade["trade_id"])
        comparison.equal(sum(o["action"]=="first_fill_cancels_opposite" for o in orders),len(trades),name+":OCA_count")
        stats=independent_stats(trades)
        for field in scenario.keys() & stats.keys():comparison.equal(scenario[field],stats[field],name+":summary:"+field)
        oracle_count=0
        if config["model"]=="validated_native":
            actual_by_day={t["broker_day"]:t for t in trades}
            day_index={d["broker_day"]:d for d in days}
            for row in coverage:
                if not bool(row["eligible"]):continue
                expected_trade,status=oracle_day(groups[row["broker_date"]],row,expected_times,config)
                actual_trade=actual_by_day.get(row["broker_date"])
                comparison.equal(actual_trade is not None,expected_trade is not None,name+":oracle_fill:"+row["broker_date"])
                if expected_trade is not None and actual_trade is not None:
                    oracle_count+=1
                    for field,value in expected_trade.items():
                        if field in actual_trade:comparison.equal(actual_trade[field],value,name+":oracle:"+row["broker_date"]+":"+field)
                elif expected_trade is None:
                    comparison.equal(day_index[row["broker_date"]]["unknown_outcome"],status.startswith("unknown"),name+":oracle_unknown:"+row["broker_date"])
                    comparison.equal(day_index[row["broker_date"]]["no_trade"],status=="no_trade",name+":oracle_no_trade:"+row["broker_date"])
        if name=="source-account":
            comparison.equal(len(trades),0,"source_account_no_executable_fills")
            for day in days:
                if day["quantity_skips"]:
                    for boundary,sign in ((day["range_high"],1),(day["range_low"],-1)):
                        stop=tick_round(boundary*(1-sign*.01))
                        raw=10000*.01/(abs(boundary-stop)*100)
                        leverage=10000*10/(boundary*100)
                        rounded=math.floor(min(raw,leverage)+1e-9)
                        comparison.equal(rounded,0,"source_account_quantity:"+day["broker_day"]+":"+str(sign))
        scenario_reports.append(dict(scenario=name,ledger_trades=len(trades),oracle_trades=oracle_count,
            path_oracle="all_quality_qualified_days" if config["model"]=="validated_native" else "saved_accounting_and_events_only"))
        if name=="primary-one-tick":primary=trades
    metrics=json.loads((stage/"metrics.json").read_text())
    for kind in ("cohorts","timing"):
        table=pd.read_csv(stage/"tables"/(kind+".csv"),keep_default_na=False).to_dict("records")
        comparison.equal(len(table),len(metrics[kind]),kind+":csv_row_count")
        for index,(saved,record) in enumerate(zip(table,metrics[kind])):
            for field,value in record.items():
                comparison.equal(saved.get(field),value,f"{kind}:csv_cell:{index}:{field}")
    primary=[dict(t,**cohort_time(t["entry_time"])) for t in primary]
    # CSV has lexical fields such as year; retain their saved strings rather
    # than allowing Pandas to turn a cohort identity into an inferred integer.
    primary_table=pd.read_csv(stage/"tables/primary-trades.csv",keep_default_na=False,dtype=str).to_dict("records")
    comparison.equal(len(primary_table),len(primary),"primary_trade_csv_count")
    for index,(saved,record) in enumerate(zip(primary_table,primary)):
        for field in record.keys() & saved.keys():
            comparison.equal(saved[field],record[field],f"primary_trade_csv:{index}:{field}")
    day_rows=pd.read_csv(stage/"tables/days.csv",keep_default_na=False).to_dict("records")
    for metric in metrics["cohorts"]:
        y,s,side=metric["year"],metric["session"],metric["side"]
        subset=[t for t in primary if (y=="all" or t["year"]==y) and (s=="all" or t["session"]==s) and (side=="combined" or t["side"]==side)]
        stats=independent_stats(subset)
        key=f"cohort:{y}:{s}:{side}"
        for field in stats.keys() & metric.keys():comparison.equal(metric[field],stats[field],key+":"+field)
        comparison.equal(metric["entry_share"],len(subset)/len(primary) if primary else None,key+":entry_share")
        calendar_days=[d for d in day_rows if y=="all" or str(moment(d["broker_day"]+"T04:00Z").tz_convert("America/New_York").year)==y]
        for field,source in (("eligible_days","eligible"),("valid_ranges","valid_range"),("no_trade_days","no_trade"),("unknown_days","unknown_outcome")):
            value=sum(str(d[source]).lower()=="true" for d in calendar_days) if s=="all" and side=="combined" else None
            comparison.equal(metric[field],value,key+":"+field)
        for field,lower,upper in (("net_dollars","mean_dollars_low","mean_dollars_high"),("net_r","expectancy_r_low","expectancy_r_high")):
            lo,hi=independent_interval(subset,field,calendar_days)
            comparison.equal(metric[lower],lo,key+":"+lower)
            comparison.equal(metric[upper],hi,key+":"+upper)
    for metric in metrics["timing"]:
        bucket=metric["bucket"]
        selected=[t for t in primary if t[metric["dimension"]]==bucket and (metric["side"]=="combined" or t["side"]==metric["side"])]
        stats=independent_stats(selected)
        for field in stats.keys() & metric.keys():comparison.equal(metric[field],stats[field],f"timing:{metric['dimension']}:{bucket}:{metric['side']}:{field}")
        comparison.equal(metric["entry_share"],len(selected)/len(primary) if primary else None,f"timing:{bucket}:share")
    path_rows=pd.read_csv(stage/"tables/equity.csv",keep_default_na=False).to_dict("records")
    closed=sorted([t for t in primary if t["status"]=="completed"],key=lambda t:(t["exit_time"],t["trade_id"]))
    comparison.equal(len(path_rows),len(closed),"equity_path_rows")
    total=peak=0.
    for row,trade in zip(path_rows,closed):
        total+=trade["net_dollars"];peak=max(total,peak)
        comparison.equal(row["trade_id"],trade["trade_id"],"equity_trade")
        comparison.equal(row["cumulative_net_dollars"],total,"equity_cumulative")
        comparison.equal(row["drawdown_dollars"],total-peak,"equity_drawdown")
    return dict(status="passed" if not comparison.mismatches else "failed",checked_at=datetime.now(timezone.utc).isoformat(),
        independent_engine_imports=False,comparison_cells=comparison.cells,mismatches=comparison.mismatches,
        tolerance=dict(absolute=1e-7,relative=1e-10,identities_and_counts="exact"),scenarios=scenario_reports,
        scope="separate per-day minute-path reconstruction for every validated scenario; all scenario ledger accounting/events/day counts and all primary cohort/timing metrics/intervals/closed P&L path",
        limits="No native TradingView or tick-level validation; native observed/15m models have accounting/event reconciliation, not an independent full replay; holiday certification and raw reconstruction remain unverified.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=verify(args.stage)
    with args.output.open("x") as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write("\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    if result["status"]!="passed":raise SystemExit(1)


if __name__=="__main__":main()
