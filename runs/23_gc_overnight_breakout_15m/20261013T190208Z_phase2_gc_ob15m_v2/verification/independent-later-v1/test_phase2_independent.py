"""Meaningful causal and arithmetic fixtures for the independent Phase2 oracle."""
import importlib.util
from pathlib import Path
import sys
import unittest
from datetime import datetime,timedelta,timezone

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("phase2_verify_independent",ROOT/"phase2_verify.py")
oracle=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=oracle
spec.loader.exec_module(oracle)


def fixture(*,direction=1,high=100.,low=90.,precision="observed_open"):
    start=datetime(2024,1,2,4,tzinfo=timezone.utc)
    price=high if direction==1 else low
    episode=dict(trade_id="original",broker_day="2024-01-02",contract="GCG4",direction=direction,range_high=high,range_low=low,entry_time=start,entry_price_raw=price,entry_time_precision=precision,status="completed",exit_time=start+timedelta(minutes=8),exit_time_latest=start+timedelta(minutes=9),exit_time_precision="within_bar",net_dollars=-100.)
    minutes=[dict(timestamp=start+timedelta(minutes=i),open=price,high=price,low=price,close=price,contract="GCG4") for i in range(781)]
    return episode,minutes


def candle(minutes,index,*,close=None,open=None,high=None,low=None):
    for i in range(index*15,(index+1)*15):
        if i>=len(minutes):break
        price=close if close is not None else minutes[i]["close"]
        minutes[i].update(open=price,high=price,low=price,close=price)
    first=minutes[index*15]
    if open is not None:first["open"]=open
    if high is not None:first["high"]=high
    if low is not None:first["low"]=low
    for i in range(index*15,min((index+1)*15,len(minutes))):
        row=minutes[i]
        row["high"]=max(row["high"],row["open"],row["close"])
        row["low"]=min(row["low"],row["open"],row["close"])


def context(episode,minutes,*,missing=(),roll=None):
    expected={x["timestamp"] for x in minutes}
    if roll is not None:
        for r in minutes:
            if r["timestamp"]>=roll:r["contract"]="GCJ4"
    retained=[x for x in minutes if x["timestamp"] not in set(missing)]
    groups={}
    for row in retained:
        groups.setdefault(oracle.floor15(row["timestamp"]),[]).append(row)
    bars=[]
    for key,rows in groups.items():
        bars.append(dict(timestamp=key,open=rows[0]["open"],high=max(r["high"] for r in rows),low=min(r["low"] for r in rows),close=rows[-1]["close"],contract=rows[0]["contract"],complete=len(rows)==15 and len({r["contract"] for r in rows})==1))
    return oracle.OracleInput(episode,retained,bars,expected)


class IndependentPhase2Tests(unittest.TestCase):
    def test_reclaim_separate_later_candles_strict_q0(self):
        e,m=fixture()
        candle(m,1,close=100.,low=99.,high=101.) # equality does not arm q0
        candle(m,2,close=99.,high=102.) # intrabar return does not confirm reclaim
        candle(m,3,close=100.1)
        result=oracle.oracle_signal(context(e,m),"reclaim-q000")
        self.assertEqual(result["arming_at"],oracle.iso(e["entry_time"]+timedelta(minutes=45)))
        self.assertEqual(result["submitted_at"],oracle.iso(e["entry_time"]+timedelta(minutes=60)))

    def test_fraction_threshold_not_order_tick_rounding(self):
        e,m=fixture(high=100.1)
        candle(m,1,close=97.6)
        candle(m,2,close=97.5)
        candle(m,3,close=97.6)
        row=oracle.oracle_signal(context(e,m),"reclaim-q025")
        self.assertEqual(row["raw_level"],97.575)
        self.assertEqual(row["arming_at"],oracle.iso(e["entry_time"]+timedelta(minutes=45)))
        self.assertEqual(row["submitted_at"],oracle.iso(e["entry_time"]+timedelta(minutes=60)))

    def test_missing_prefix_never_later_setup_zero(self):
        e,m=fixture()
        candle(m,1,close=94.)
        candle(m,2,close=96.)
        result=oracle.oracle_policy(context(e,m,missing=[m[18]["timestamp"]]),"reclaim-q050")
        self.assertEqual(result["status"],"unknown_signal")
        self.assertIsNone(result["net_dollars"])
        self.assertFalse(result["signal"])

    def test_original_b_requires_complete_direction(self):
        e,m=fixture()
        result=oracle.oracle_signal(context(e,m,missing=[m[3]["timestamp"]]),"passive-q025")
        self.assertEqual(result["reason"],"original_direction_candle_incomplete_or_unusable")

    def test_gap_through_passive_stop_retains_dollars_invalid_R(self):
        e,m=fixture(high=100.1)
        candle(m,1,close=98.,open=96.)
        result=oracle.oracle_policy(context(e,m),"passive-q025")
        self.assertEqual(result["submitted_limit"],97.5)
        self.assertEqual(result["trade"]["entry_price_raw"],96.)
        self.assertIsNone(result["trade"]["risk_initial_dollars"])
        self.assertIsNone(result["trade"]["net_r"])
        self.assertAlmostEqual(result["net_dollars"],-25.)

    def test_same_candle_stop_prevents_reset(self):
        e,m=fixture()
        candle(m,1,close=94.)
        candle(m,2,close=96.)
        candle(m,3,close=97.,low=94.)
        result=oracle.oracle_policy(context(e,m),"reclaim-q050")
        self.assertEqual(result["trade"]["exit_reason"],"stop")
        self.assertEqual(result["trade"]["initial_stop"],95.)
        self.assertIsNone(result["trade"]["reset_stop"])
        self.assertAlmostEqual(result["trade"]["net_dollars"],-225.)

    def test_surviving_reset_uses_actual_fill_then_next_open_stop(self):
        e,m=fixture()
        candle(m,1,close=94.)
        candle(m,2,close=96.)
        candle(m,3,close=97.)
        candle(m,4,close=95.5)
        result=oracle.oracle_policy(context(e,m),"reclaim-q050")
        self.assertEqual(result["trade"]["reset_stop"],96.1)
        self.assertEqual(result["trade"]["reset_stop_active_at"],oracle.iso(e["entry_time"]+timedelta(minutes=60)))
        self.assertEqual(result["trade"]["exit_price_raw"],95.5)
        self.assertEqual(result["trade"]["exit_time_precision"],"observed_open")

    def test_contract_barrier_before_incoming_price(self):
        e,m=fixture()
        candle(m,1,close=94.)
        candle(m,2,close=96.)
        candle(m,3,close=97.)
        roll=m[48]["timestamp"]
        result=oracle.oracle_policy(context(e,m,roll=roll),"reclaim-q050")
        self.assertEqual(result["status"],"filled_censored")
        self.assertEqual(result["reason"],"contract_transition")
        self.assertEqual(result["trade"]["last_observed_at"],oracle.iso(roll))
        self.assertIsNone(result["net_dollars"])

    def test_postfill_path_excludes_prefill_on_low_first(self):
        e,m=fixture(precision="within_bar")
        m[0].update(open=99.,high=101.,low=94.,close=100.)
        self.assertEqual(oracle.after_original_fill(m[0],e,"low_first"),(100.,101.,100.))
        self.assertEqual(oracle.after_original_fill(m[0],e,"high_first"),(100.,101.,94.,100.))
        row=oracle.oracle_signal(context(e,m),"passive-q050")
        self.assertEqual(row["status"],"unknown_signal")
        self.assertIsNone(row["net_dollars"])

    def test_protected_hold_disqualified_by_earlier_breach(self):
        e,m=fixture()
        m[10]["low"]=89.9
        candle(m,1,close=91.,low=90.)
        row=oracle.oracle_signal(context(e,m),"protected-touch-hold")
        self.assertEqual(row["reason"],"one_tick_breach_disqualifies_touch_hold")
        self.assertFalse(row["signal"])

    def test_protected_breach_arm_requires_separate_return_candle(self):
        e,m=fixture()
        candle(m,1,close=91.,low=89.9)
        candle(m,2,close=91.)
        row=oracle.oracle_signal(context(e,m),"protected-failed-break-reclaim")
        self.assertEqual(row["arming_at"],oracle.iso(e["entry_time"]+timedelta(minutes=30)))
        self.assertEqual(row["submitted_at"],oracle.iso(e["entry_time"]+timedelta(minutes=45)))

    def test_protected_reversal_uses_opposite_direction(self):
        e,m=fixture(direction=-1)
        candle(m,1,close=100.1)
        row=oracle.oracle_signal(context(e,m),"protected-reversal")
        self.assertEqual(row["direction"],1)
        self.assertEqual(row["initial_stop"],99.1)

    def test_session_instances_DST_and_endpoint_strictness(self):
        entry=datetime.fromisoformat("2024-12-31T23:30:00-05:00")
        end,inclusive=oracle.horizon_end(entry,datetime.fromisoformat("2025-01-01T12:00:00Z"))
        self.assertEqual(oracle.iso(end),"2025-01-01T07:00:00Z")
        self.assertFalse(inclusive)
        self.assertEqual(oracle.cohort_at(datetime.fromisoformat("2025-01-01T00:30:00-05:00"))["year"],"2025")
        summer=datetime.fromisoformat("2024-07-02T00:30:00-04:00")
        self.assertEqual(oracle.iso(oracle.horizon_end(summer,summer+timedelta(hours=12))[0]),"2024-07-02T06:00:00Z")

    def test_baseline_flat_loss_availability_not_retroactive(self):
        e,m=fixture()
        e["exit_time_latest"]=e["entry_time"]+timedelta(minutes=9)
        self.assertEqual(oracle.baseline_state(e,e["entry_time"]+timedelta(minutes=10))["baseline_position_status"],"open")
        self.assertTrue(oracle.baseline_state(e,e["entry_time"]+timedelta(minutes=15))["baseline_loss_known"])
        e["exit_time_precision"]="observed_open"
        e["exit_time_latest"]=e["exit_time"]
        self.assertEqual(oracle.baseline_state(e,e["exit_time"])["baseline_position_status"],"open")

    def test_whole_account_zero_and_real_two_leg_risk_constraints(self):
        self.assertEqual(oracle.whole_quantity(10000,2000,1980),0)
        self.assertEqual(oracle.whole_quantity(100000,1000,998,budget_fraction=.5),2)
        self.assertEqual(oracle.whole_quantity(100000,1000,998,budget_fraction=.5,active_notional=900000),1)
        self.assertEqual(oracle.whole_quantity(100000,1000,998,budget_fraction=.5,active_margin=100000),0)
        self.assertEqual(oracle.recovery_class(-205,230,loss_known=True,actually_executed=True)["category"],"full_recovery")
        self.assertEqual(oracle.recovery_class(-205,100,loss_known=True,actually_executed=True)["category"],"partial_recovery")
        self.assertEqual(oracle.recovery_class(-205,-25,loss_known=True,actually_executed=True)["category"],"further_loss")
        self.assertIsNone(oracle.recovery_class(-205,230,loss_known=False,actually_executed=True))
        self.assertIsNone(oracle.recovery_class(-205,230,loss_known=True,actually_executed=False))

    def test_joint_bootstrap_calendar_spacing_mask_and_zeros(self):
        values=[("2024-01-01",[0.,0.]),("2024-02-12",[10.,20.]),("2024-03-25",[None,None])]
        result=oracle.aligned_intervals(values,["2024-01-01","2024-03-25"],weeks=1,replications=10000)
        self.assertEqual(result[0],(0.,10.))
        self.assertEqual(result[1],(0.,20.))
        self.assertEqual(oracle.aligned_intervals([("2024-01-01",[None,None])],["2024-01-01"]),[(None,None),(None,None)])

    def test_selection_support_positive_mean_and_shallow_tie(self):
        rows=[dict(policy="reclaim-q025",fraction=.25,mean_difference=10.,completed_fills=100,completed_years=2),dict(policy="reclaim-q000",fraction=0.,mean_difference=10.,completed_fills=101,completed_years=2),dict(policy="reclaim-q050",fraction=.5,mean_difference=20.,completed_fills=99,completed_years=3)]
        self.assertEqual(oracle.selection_from_validation(rows),"reclaim-q000")
        self.assertIsNone(oracle.selection_from_validation([dict(policy="reclaim-q000",fraction=0,mean_difference=0.,completed_fills=500,completed_years=3)]))

    def test_observed_event_survives_gap_without_exact_first_time(self):
        e,m=fixture()
        m[50]["low"]=89.9 # observed well after original completed stop
        observations=oracle.oracle_protected(context(e,m,missing=[m[30]["timestamp"]]))
        row=next(x for x in observations["occurrence"] if x["horizon"]=="remaining_broker_window" and x["event"]=="one_tick_breach")
        self.assertIs(row["occurred"],True)
        self.assertIsNone(row["first_time"])
        self.assertEqual(row["first_observed_time"],oracle.iso(m[50]["timestamp"]))
        self.assertFalse(row["complete_observation"])
        self.assertIsNone(row["repeat_contacts"])

    def test_absent_event_null_under_incomplete_observation(self):
        e,m=fixture()
        rows=oracle.oracle_protected(context(e,m,missing=[m[30]["timestamp"]]))["occurrence"]
        row=next(x for x in rows if x["horizon"]=="remaining_broker_window" and x["event"]=="touch")
        self.assertIsNone(row["occurred"])
        full=oracle.oracle_protected(context(e,m))["occurrence"]
        self.assertIs(next(x for x in full if x["horizon"]=="remaining_broker_window" and x["event"]=="touch")["occurred"],False)

    def test_session_end_close_excluded_broker_cutoff_confirmation_included(self):
        e,m=fixture()
        # Original NY 23:00 fill has an Asia instance ending UTC07:00.
        candle(m,11,close=89.9) # UTC06:45→07:00
        candle(m,51,close=89.9) # UTC16:45→17:00 broker cutoff
        rows=oracle.oracle_protected(context(e,m))["occurrence"]
        original=next(x for x in rows if x["horizon"]=="original_session" and x["event"]=="close_break")
        remaining=next(x for x in rows if x["horizon"]=="remaining_broker_window" and x["event"]=="close_break")
        self.assertIs(original["occurred"],False)
        self.assertFalse(original["close_confirmation_endpoint_included"])
        self.assertIs(remaining["occurred"],True)
        self.assertEqual(remaining["first_observed_time"],"2024-01-02T07:00:00Z")

    def test_recovery_separate_close_and_not_trade_target(self):
        e,m=fixture()
        candle(m,1,close=91.,low=89.9)
        candle(m,2,close=96.)
        rows=oracle.oracle_protected(context(e,m))["recovery"]
        mid=next(x for x in rows if x["horizon"]=="remaining_broker_window" and x["recovery_level"]=="midpoint" and x["event"]=="close_reclaim")
        self.assertIs(mid["occurred"],True)
        self.assertEqual(mid["first_time"],"2024-01-02T04:45:00Z")
        self.assertTrue(mid["not_executed_trade_target"])
        no_breach=oracle.oracle_protected(context(*fixture()))["recovery"]
        self.assertTrue(all(x["occurred"] is None for x in no_breach))

    def test_ordering_ambiguous_prefill_event_not_false_or_exact(self):
        e,m=fixture(precision="within_bar")
        m[0].update(open=99.,high=101.,low=89.9,close=100.)
        rows=oracle.oracle_protected(context(e,m))["occurrence"]
        breach=next(x for x in rows if x["horizon"]=="remaining_broker_window" and x["event"]=="one_tick_breach")
        self.assertIsNone(breach["occurred"])
        self.assertTrue(breach["ordering_ambiguous"])
        self.assertIsNone(breach["first_time"])

    def test_level_diagnostics_are_original_path_not_policy_success(self):
        e,m=fixture()
        candle(m,1,close=94.)
        candle(m,2,close=100.1)
        rows=oracle.oracle_levels(context(e,m))
        midpoint=next(x for x in rows if x["fraction"]==.5 and x["event"]=="touch")
        self.assertIs(midpoint["occurred"],True)
        self.assertTrue(midpoint["not_realized_trade_return"])
        self.assertIs(midpoint["range_recovery_before_opposite"],True)
        self.assertEqual(midpoint["excursion_first_1R"],"adverse")

    def test_trade_cohort_invalid_R_and_annual_closed_drawdown(self):
        def trade(key,entry,exit,pnl,r):
            return dict(trade_id=key,broker_day=entry[:10],entry_time=entry,exit_time=exit,status="completed",side="long",net_dollars=pnl,raw_price_points=pnl/100+.25,raw_price_dollars=pnl+25,net_points=pnl/100,net_r=r,source_style_r=r,mfe_points=2.,mae_points=1.,holding_minutes=30.,exit_reason="stop",ambiguous=False)
        trades=[trade("prior","2023-12-30T04:00:00Z","2023-12-30T05:00:00Z",500.,5.),trade("win","2024-01-02T04:00:00Z","2024-01-02T05:00:00Z",100.,1.),trade("gap","2024-01-03T04:00:00Z","2024-01-03T05:00:00Z",-200.,None)]
        row=oracle.trade_statistics(trades,["2023-12-30","2024-01-02","2024-01-03"],year="2024")
        self.assertEqual(row["completed"],2)
        self.assertEqual(row["invalid_r"],1)
        self.assertEqual(row["r_denominator"],1)
        self.assertEqual(row["expectancy_r"],1.)
        self.assertEqual(row["net_dollars"],-100.)
        self.assertEqual(row["max_drawdown_dollars"],200.)
        self.assertEqual(row["entry_share"],2/3)

    def test_common_family_mask_keeps_no_fill_zero_and_unknown_null(self):
        base={str(i):dict(trade_id=str(i),broker_day=f"2024-01-0{i+2}",entry_time=f"2024-01-0{i+2}T04:00:00Z",entry_price=100.,direction=1,status="completed",net_dollars=100.) for i in range(2)}
        results={p:[dict(episode_id="0",status="no_fill",trade=None,opportunity_seen=False),dict(episode_id="1",status="no_fill",trade=None,opportunity_seen=False)] for p in oracle.PRIMARY}
        results[oracle.PRIMARY[-1]][1]["status"]="unknown"
        rows=oracle.paired_statistics(results,base,["2024-01-02","2024-01-03"],oracle.PRIMARY,"primary",intervals=False)
        for row in rows:
            self.assertEqual(row["complete_pairs"],1)
            self.assertEqual(row["missing_pairs"],1)
            self.assertEqual(row["alternative_net_dollars"],0.)
            self.assertEqual(row["mean_difference"],-100.)
        self.assertEqual(rows[0]["individual_pairs"],2)
        self.assertEqual(rows[-1]["individual_pairs"],1)

    def test_confirmation_at_original_open_is_prefill_not_event(self):
        e,m=fixture()
        original=e["entry_time"]+timedelta(minutes=15)
        e["entry_time"]=original
        candle(m,0,close=89.9)
        rows=oracle.oracle_protected(context(e,m))["occurrence"]
        close_break=next(x for x in rows if x["horizon"]=="remaining_broker_window" and x["event"]=="close_break")
        self.assertIs(close_break["occurred"],False)
        self.assertTrue(all(bar["timestamp"]>=oracle.floor15(original) for bar in oracle.confirmed_bars(context(e,m),original+timedelta(hours=1),True)))

    def test_genuinely_executed_whole_contract_two_leg_recovery_after_costs(self):
        # Synthetic GC-price fixture; retained historical account remains $10k.
        # Both legs really execute the independent minute oracle with 50/50
        # frozen daily budgets, whole quantities and their own two-sided costs.
        e,m=fixture(high=20.,low=19.)
        e.update(net_dollars=-45.,exit_time=e["entry_time"],exit_time_latest=e["entry_time"]+timedelta(minutes=1))
        m[0]["low"]=19.8
        candle(m,1,close=19.4)
        candle(m,2,close=19.6)
        for i in range(3,52):candle(m,i,close=20.5)
        m[45]["open"]=19.6
        m[45]["low"]=19.6
        m[-1].update(open=20.5,high=20.5,low=20.5,close=20.5)
        ctx=context(e,m)
        first=oracle.oracle_signal(ctx,"reclaim-q000")
        first.update(status="submitted",reason=None,unknown=False,net_dollars=None,policy="original-synthetic",direction=1,signal=True,submitted_at=oracle.iso(e["entry_time"]),expected_fill_time=oracle.iso(e["entry_time"]),signal_available_at=oracle.iso(e["entry_time"]),initial_stop_anchor=20.,initial_stop=19.8,planned_risk_points=.2,order_type="market")
        original_qty=oracle.whole_quantity(10000,20.,19.8,budget_fraction=.5)
        self.assertEqual(original_qty,2) # submitted anchor risk20$/contract
        original=oracle.oracle_execute(ctx,first,quantity=original_qty)["trade"]
        self.assertEqual(original["status"],"completed")
        self.assertAlmostEqual(original["commission_dollars"],10.)
        self.assertAlmostEqual(original["net_dollars"],-90.)
        second_signal=oracle.oracle_signal(ctx,"reclaim-q050")
        qty=oracle.whole_quantity(10000,second_signal["initial_stop_anchor"],second_signal["initial_stop"],budget_fraction=.5)
        replacement=oracle.oracle_execute(ctx,second_signal,quantity=qty)["trade"]
        self.assertEqual(replacement["status"],"completed")
        self.assertEqual(qty,2)
        self.assertAlmostEqual(replacement["commission_dollars"],10.)
        self.assertAlmostEqual(replacement["net_dollars"],130.)
        recovered=oracle.recovery_class(original["net_dollars"],replacement["net_dollars"],loss_known=True,actually_executed=True)
        self.assertEqual(recovered["category"],"full_recovery")
        self.assertAlmostEqual(recovered["combined_net_dollars"],40.)

    def test_repeated_contacts_exclude_first_contact(self):
        e,m=fixture()
        m[20]["low"]=89.9
        rows=oracle.oracle_protected(context(e,m))["occurrence"]
        touch=next(x for x in rows if x["horizon"]=="remaining_broker_window" and x["event"]=="touch")
        self.assertEqual(touch["contact_count"],1)
        self.assertEqual(touch["repeat_contacts"],0)
        m[30]["low"]=89.9
        rows=oracle.oracle_protected(context(e,m))["occurrence"]
        touch=next(x for x in rows if x["horizon"]=="remaining_broker_window" and x["event"]=="touch")
        self.assertEqual(touch["contact_count"],2)
        self.assertEqual(touch["repeat_contacts"],1)

    def test_source15_opening_gap_stop_known_before_missing_tail(self):
        e,m=fixture()
        candle(m,1,close=94.)
        candle(m,2,close=96.)
        candle(m,3,close=97.,open=94.)
        result=oracle.oracle_policy(context(e,m,missing=[m[46]["timestamp"]]),"reclaim-q050",execution_minutes=15)
        self.assertEqual(result["status"],"filled_complete")
        self.assertEqual(result["trade"]["entry_time_precision"],"observed_open")
        self.assertEqual(result["trade"]["exit_time_precision"],"observed_open")
        self.assertAlmostEqual(result["net_dollars"],-25.)

    def test_source15_cutoff_opening_exit_known_without_later_candle(self):
        e,m=fixture()
        candle(m,1,close=94.)
        candle(m,2,close=96.)
        for i in range(3,52):candle(m,i,close=97.)
        m[-1].update(open=97.,high=97.,low=97.,close=97.)
        result=oracle.oracle_policy(context(e,m),"reclaim-q050",execution_minutes=15)
        self.assertEqual(result["status"],"filled_complete")
        self.assertEqual(result["trade"]["exit_reason"],"time")
        self.assertEqual(result["trade"]["exit_time"],"2024-01-02T17:00:00Z")

    def test_one_tick_passive_does_not_fill_equal_open_or_touch(self):
        e,m=fixture()
        candle(m,1,close=98.,open=97.5,low=97.5)
        native=oracle.oracle_policy(context(e,m),"passive-q025")
        touch=oracle.oracle_policy(context(e,m),"passive-q025-touch")
        self.assertEqual(native["status"],"known_no_fill")
        self.assertEqual(native["net_dollars"],0.)
        self.assertIsNotNone(touch["trade"])
        self.assertEqual(touch["trade"]["entry_time_precision"],"observed_open")


if __name__=="__main__":unittest.main()
