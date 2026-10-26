"""Phase 2 causal synthetic fixtures; no retained-history outcomes."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.engine import Bar, BROKER
from src.phase2_engine import (BaselineEpisode, DecisionBar, Phase2Config, PolicySpec,
    baseline_state, execute_signal, find_signal, observe_episode, observe_levels,
    percentage_stop, policy_specs, prepare_context, price_path, run_policy,
    session_horizon_end, tick_price)

UTC=timezone.utc
MINUTE=timedelta(minutes=1)


def clock(hour,minute=0,day="2024-01-03"):
    return datetime.fromisoformat(day).replace(hour=hour,minute=minute,tzinfo=BROKER).astimezone(UTC)


def original(**kwargs):
    defaults=dict(episode_id="frozen-original",broker_day="2024-01-03",contract="GCG4",direction=1,
        range_high=100.,range_low=90.,entry_time=clock(7,5),entry_price_raw=100.,
        entry_time_latest=clock(7,6),entry_time_precision="within_bar",baseline_status="completed",
        baseline_exit_time=clock(10),baseline_exit_time_latest=clock(10),baseline_exit_time_precision="observed_open",baseline_net_dollars=-100.)
    defaults.update(kwargs)
    return BaselineEpisode(**defaults)


def fixture(*,end=clock(20),episode=None,price=100.5):
    episode=episode or original()
    bars=[]
    start=episode.breakout_bar_open
    current=start
    while current<=end:
        if current<episode.entry_time:
            bars.append(Bar(current,99.,99.5,98.5,99.,episode.contract,current+MINUTE))
        elif current==episode.entry_time:
            bars.append(Bar(current,99.5,100.5,99.2,100.2,episode.contract,current+MINUTE))
        else:
            bars.append(Bar(current,price,price,price,price,episode.contract,current+MINUTE))
        current+=MINUTE
    return episode,bars


def set_minute(bars,hour,minute=0,*,o,h=None,l=None,c=None,contract=None):
    at=clock(hour,minute)
    index=next(i for i,b in enumerate(bars) if b.timestamp==at)
    bars[index]=replace(bars[index],open=o,high=o if h is None else h,
        low=o if l is None else l,close=o if c is None else c,
        contract=contract or bars[index].contract)


def after(bars,hour,minute=0,price=100.5):
    at=clock(hour,minute)
    for i,b in enumerate(bars):
        if b.timestamp>=at:
            bars[i]=replace(b,open=price,high=price,low=price,close=price)


def decision_candles(bars):
    groups={}
    for bar in bars:
        opening=bar.timestamp.replace(minute=bar.timestamp.minute//15*15)
        groups.setdefault(opening,[]).append(bar)
    return [DecisionBar(t,values[0].open,max(b.high for b in values),min(b.low for b in values),values[-1].close,
        values[0].contract,t+timedelta(minutes=15),len(values)==15 and len({b.contract for b in values})==1)
        for t,values in sorted(groups.items())]


def context(ep,bars,*,calendar=lambda t: True,candles=None):
    return prepare_context(ep,bars,decision_candles(bars) if candles is None else candles,calendar)


def cfg(**kwargs):
    return Phase2Config(commission_per_side=0,slippage_ticks=0,**kwargs)


def reclaim_context(*,q=.5):
    ep,bars=fixture()
    level=ep.level(q)
    set_minute(bars,7,29,o=level)
    set_minute(bars,7,44,o=level+.2)
    return ep,bars,context(ep,bars)


def event(rows,event,horizon="remaining_broker_window"):
    return next(row for row in rows if row["event"]==event and row["horizon"]==horizon)


class SignalPolicyTests(unittest.TestCase):
    def test_fixed_policy_families_and_no_search_parameters(self):
        self.assertEqual(len(policy_specs()),10)
        with self.assertRaises(ValueError):PolicySpec("new","reclaim",.3)
        with self.assertRaises(ValueError):PolicySpec("zero","passive",0)
        with self.assertRaises(ValueError):Phase2Config(stop_percent=float("nan"))
        with self.assertRaises(ValueError):Phase2Config(slippage_ticks=True)

    def test_rational_levels_and_conservative_executable_limits(self):
        ep=original(range_high=100.1,range_low=98.)
        self.assertAlmostEqual(ep.level(.25),99.575)
        self.assertEqual(tick_price(ep.level(.25),.1,direction=1),99.5)
        mirror=replace(ep,direction=-1,entry_price_raw=98)
        self.assertAlmostEqual(mirror.level(.25),98.525)
        self.assertEqual(tick_price(mirror.level(.25),.1,direction=-1),98.6)

    def test_percentage_stop_preserves_raw_quarter_tick_anchor(self):
        self.assertEqual(percentage_stop(100.05,1,1,.1),99.0)
        self.assertEqual(percentage_stop(100.0000000002,1,1,.1),99.0)
        self.assertEqual(percentage_stop(1020,1,1,.1),1009.8)

    def test_source_tie_low_first_ignores_binary_float_noise(self):
        b=Bar(clock(8),100.1,100.3,99.9,100.1,"GCG4")
        self.assertEqual(price_path(b,"source_ohlc"),(100.1,99.9,100.3,100.1))

    def test_complete_decision_candle_requires_usable_ohlc(self):
        ep,bars=fixture()
        candles=decision_candles(bars)
        candles[0]=replace(candles[0],close=float("nan"))
        with self.assertRaises(ValueError):context(ep,bars,candles=candles)
        candles[0]=replace(candles[0],complete=False)
        result=find_signal(context(ep,bars,candles=candles),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["status"],"unknown_signal")

    def test_decision_timestamps_require_timezone(self):
        ep,bars=fixture()
        candles=decision_candles(bars)
        candles[0]=replace(candles[0],timestamp=candles[0].timestamp.replace(tzinfo=None))
        with self.assertRaises(ValueError):context(ep,bars,candles=candles)

    def test_confirmed_reclaim_requires_later_arm_and_later_reclaim(self):
        ep,bars,ctx=reclaim_context()
        signal=find_signal(ctx,PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(signal["arming_at"],"2024-01-03T04:30:00Z")
        self.assertEqual(signal["signal_available_at"],"2024-01-03T04:45:00Z")
        self.assertEqual(signal["initial_stop_anchor"],95.2)
        self.assertEqual(signal["status"],"submitted")

    def test_original_candle_cannot_arm_confirmed_policy(self):
        ep,bars=fixture()
        set_minute(bars,7,14,o=94)
        signal=find_signal(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(signal["status"],"known_no_fill")
        self.assertFalse(signal["armed"])

    def test_invalid_rounded_planned_risk_is_rejected_before_order(self):
        ep=original(range_high=.2,range_low=.1,entry_price_raw=.2)
        ep,bars=fixture(episode=ep,price=.2)
        for i,b in enumerate(bars):
            if b.timestamp<ep.entry_time:bars[i]=replace(b,open=.1,high=.1,low=.1,close=.1)
            elif b.timestamp==ep.entry_time:bars[i]=replace(b,open=.1,high=.2,low=.1,close=.2)
        set_minute(bars,7,29,o=.1)
        signal=find_signal(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(signal["status"],"known_no_fill")
        self.assertEqual(signal["reason"],"invalid_planned_risk_before_submission")
        self.assertTrue(signal["signal"])
        self.assertIsNone(signal["submitted_at"])

    def test_q0_requires_strict_inward_close(self):
        ep,bars=fixture()
        set_minute(bars,7,29,o=100)
        set_minute(bars,7,44,o=99.9)
        set_minute(bars,7,59,o=100)
        set_minute(bars,8,14,o=100.1)
        result=find_signal(context(ep,bars),PolicySpec("boundary","reclaim",0),cfg())
        self.assertEqual(result["arming_at"],"2024-01-03T04:45:00Z")
        self.assertEqual(result["signal_available_at"],"2024-01-03T05:15:00Z")

    def test_positive_q_inward_is_inclusive_outward_is_strict(self):
        ep,bars=fixture()
        set_minute(bars,7,29,o=95)
        set_minute(bars,7,44,o=95)
        set_minute(bars,7,59,o=95.1)
        result=find_signal(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["arming_at"],"2024-01-03T04:30:00Z")
        self.assertEqual(result["signal_available_at"],"2024-01-03T05:00:00Z")

    def test_opposite_touch_does_not_cancel_waiting_percent_policy(self):
        ep,bars=fixture()
        set_minute(bars,7,29,o=89)
        set_minute(bars,7,44,o=96)
        signal=find_signal(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(signal["status"],"submitted")

    def test_symmetry_of_mirrored_confirmed_signals(self):
        ep,bars,ctx=reclaim_context()
        long=find_signal(ctx,PolicySpec("mid","reclaim",.5),cfg())
        mirror=replace(ep,direction=-1,entry_price_raw=90)
        reflected=[replace(b,open=190-b.open,high=190-b.low,low=190-b.high,close=190-b.close) for b in bars]
        short=find_signal(context(mirror,reflected),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(short["signal_available_at"],long["signal_available_at"])
        self.assertEqual(short["arming_at"],long["arming_at"])
        self.assertEqual(short["direction"],-1)

    def test_missing_original_confirmation_disables_actionability(self):
        ep,bars=fixture()
        bars=[b for b in bars if b.timestamp!=clock(7,14)]
        result=find_signal(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["status"],"unknown_signal")
        self.assertIsNone(result["net_dollars"])

    def test_missing_prefix_after_original_exit_is_still_unknown(self):
        ep,bars=fixture(episode=original(baseline_exit_time=clock(7,15),baseline_exit_time_latest=clock(7,15)))
        bars=[b for b in bars if b.timestamp!=clock(7,20)]
        result=find_signal(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["status"],"unknown_signal")

    def test_last_cutoff_reclaim_is_first_signal_rejected_before_order(self):
        ep,bars=fixture()
        set_minute(bars,19,44,o=95)
        set_minute(bars,19,59,o=96)
        result=find_signal(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertTrue(result["signal"])
        self.assertEqual(result["status"],"known_no_fill")
        self.assertIsNone(result["submitted_at"])

    def test_limit_skips_known_postfill_prearming_touch(self):
        ep,bars=fixture()
        set_minute(bars,7,10,o=95)
        result=find_signal(context(ep,bars),PolicySpec("midlimit","passive",.5),cfg())
        self.assertEqual((result["status"],result["reason"]),("known_no_fill","missed_before_arming"))
        self.assertTrue(result["missed_before_arming"])

    def test_limit_does_not_use_prefill_level_visits(self):
        ep,bars=fixture()
        set_minute(bars,7,4,o=94, h=99,l=94,c=99)
        result=find_signal(context(ep,bars),PolicySpec("midlimit","passive",.5),cfg())
        self.assertEqual(result["status"],"submitted")

    def test_limit_prearming_same_minute_order_is_unknown(self):
        ep,bars=fixture()
        set_minute(bars,7,5,o=99.5,h=101,l=94,c=100.2)
        result=find_signal(context(ep,bars),PolicySpec("midlimit","passive",.5),cfg())
        self.assertEqual(result["status"],"unknown_signal")

    def test_touch_hold_exact_boundary_without_prior_breach(self):
        ep,bars=fixture()
        set_minute(bars,7,20,o=95,h=96,l=90,c=95)
        set_minute(bars,7,29,o=95)
        result=find_signal(context(ep,bars),PolicySpec("hold","protected_touch_hold"),cfg())
        self.assertEqual(result["status"],"submitted")
        self.assertEqual(result["signal_available_at"],"2024-01-03T04:30:00Z")
        self.assertEqual(result["direction"],1)

    def test_touch_hold_one_tick_breach_disqualifies_forever(self):
        ep,bars=fixture()
        set_minute(bars,7,10,o=95,h=96,l=89.9,c=95)
        bars=[b for b in bars if b.timestamp!=clock(9)]
        result=find_signal(context(ep,bars),PolicySpec("hold","protected_touch_hold"),cfg())
        self.assertEqual(result["status"],"known_no_fill")
        self.assertEqual(result["reason"],"one_tick_breach_disqualifies_touch_hold")

    def test_failed_break_requires_distinct_later_reclaim(self):
        ep,bars=fixture()
        set_minute(bars,7,20,o=95,h=96,l=89.9,c=95)
        set_minute(bars,7,29,o=95)
        result=find_signal(context(ep,bars),PolicySpec("failed","protected_failed_break_reclaim"),cfg())
        self.assertEqual(result["arming_at"],"2024-01-03T04:30:00Z")
        self.assertEqual(result["signal_available_at"],"2024-01-03T04:45:00Z")

    def test_earlier_breach_does_not_arm_failed_policy_on_original_b(self):
        ep,bars=fixture()
        set_minute(bars,7,10,o=95,h=96,l=89.9,c=95)
        result=find_signal(context(ep,bars),PolicySpec("failed","protected_failed_break_reclaim"),cfg())
        self.assertTrue(result["prior_breach_before_actionable"])
        self.assertFalse(result["armed"])
        self.assertEqual(result["status"],"known_no_fill")

    def test_opposite_reversal_mirrors_direction(self):
        ep,bars=fixture()
        set_minute(bars,7,29,o=89.9)
        result=find_signal(context(ep,bars),PolicySpec("reverse","protected_reversal"),cfg())
        self.assertEqual(result["direction"],-1)
        self.assertEqual(result["signal_available_at"],"2024-01-03T04:30:00Z")


class ExecutionTests(unittest.TestCase):
    def test_market_next_scheduled_open_not_signal_close(self):
        ep,bars,ctx=reclaim_context()
        result=run_policy(ctx,PolicySpec("mid","reclaim",.5),cfg())
        trade=result["trade"]
        self.assertEqual(result["status"],"filled_complete")
        self.assertEqual(trade["entry_time"],"2024-01-03T04:45:00Z")
        self.assertEqual(trade["entry_price_raw"],100.5)
        self.assertEqual(trade["initial_stop_anchor"],95.2)
        self.assertEqual(trade["exit_reason"],"time")

    def test_actual_adverse_slippage_fees_risk_and_reset(self):
        ep,bars,ctx=reclaim_context()
        result=run_policy(ctx,PolicySpec("mid","reclaim",.5),Phase2Config())
        trade=result["trade"]
        self.assertAlmostEqual(trade["entry_price"],100.6)
        self.assertAlmostEqual(trade["exit_price"],100.4)
        self.assertEqual(trade["commission_dollars"],5)
        self.assertAlmostEqual(trade["net_dollars"],-25)
        self.assertEqual(trade["reset_stop_active_at"],"2024-01-03T05:00:00Z")
        self.assertAlmostEqual(trade["risk_initial_dollars"],(100.6-trade["initial_stop"])*100)

    def test_submitted_market_gap_through_stop_is_retained_with_null_r(self):
        ep,bars,ctx=reclaim_context()
        set_minute(bars,7,45,o=90)
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),Phase2Config())
        self.assertEqual(result["status"],"filled_complete")
        self.assertEqual(result["trade"]["entry_price_raw"],90)
        self.assertEqual(result["trade"]["exit_price_raw"],90)
        self.assertIsNone(result["trade"]["risk_initial_dollars"])
        self.assertIsNone(result["trade"]["net_r"])
        self.assertAlmostEqual(result["net_dollars"],-25)

    def test_expected_market_fill_missing_is_unknown_not_unfilled(self):
        ep,bars,ctx=reclaim_context()
        bars=[b for b in bars if b.timestamp!=clock(7,45)]
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["status"],"unknown_fill")
        self.assertTrue(result["signal"])
        self.assertIsNone(result["net_dollars"])

    def test_explicit_next_observed_open_is_separate_sensitivity(self):
        ep,bars,ctx=reclaim_context()
        bars=[b for b in bars if b.timestamp!=clock(7,45)]
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg(fill_model="next_observed_open_sensitivity"))
        self.assertEqual(result["trade"]["entry_time"],"2024-01-03T04:46:00Z")
        self.assertEqual(result["trade"]["fill_model"],"next_observed_open_sensitivity")

    def test_later_missing_censors_accepted_trade(self):
        ep,bars,ctx=reclaim_context()
        bars=[b for b in bars if b.timestamp!=clock(8)]
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["status"],"filled_censored")
        self.assertEqual(result["trade"]["entry_time"],"2024-01-03T04:45:00Z")
        self.assertIsNone(result["trade"]["net_dollars"])

    def test_missing_entry_close_does_not_fabricate_stop_reset(self):
        ep,bars,ctx=reclaim_context()
        bars=[b for b in bars if b.timestamp!=clock(7,59)]
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["status"],"filled_censored")
        self.assertIsNone(result["trade"]["reset_stop"])

    def test_observed_entry_close_retained_before_following_gap(self):
        ep,bars,ctx=reclaim_context()
        bars=[b for b in bars if b.timestamp!=clock(8)]
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertIsNotNone(result["trade"]["reset_stop"])

    def test_same_candle_stop_never_retroactively_resets(self):
        ep,bars,ctx=reclaim_context()
        set_minute(bars,7,46,o=100.5,h=102,l=90,c=100)
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["trade"]["exit_reason"],"stop")
        self.assertIsNone(result["trade"]["reset_stop"])
        self.assertEqual(result["trade"]["holding_bars"],0)

    def test_known_stop_before_later_missing_remains_completed(self):
        ep,bars,ctx=reclaim_context()
        set_minute(bars,7,46,o=90)
        bars=[b for b in bars if b.timestamp!=clock(9)]
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["status"],"filled_complete")

    def test_reset_triggered_at_creation_exits_rebounded_next_open(self):
        ep,bars,ctx=reclaim_context()
        set_minute(bars,7,59,o=100.5,h=100.5,l=98,c=98)
        set_minute(bars,8,o=103)
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["trade"]["exit_price_raw"],103)
        self.assertEqual(result["trade"]["exit_time"],"2024-01-03T05:00:00Z")
        self.assertEqual(result["trade"]["exit_reason"],"stop")

    def test_queued_time_and_stop_compete_same_open(self):
        ep,bars,ctx=reclaim_context()
        set_minute(bars,20,o=90)
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["trade"]["exit_reason"],"time")
        self.assertTrue(result["trade"]["competing_exit_orders"])

    def test_stale_order_does_not_trade_another_contract(self):
        ep,bars,ctx=reclaim_context()
        for i,b in enumerate(bars):
            if b.timestamp>=clock(7,45):bars[i]=replace(b,contract="GCJ4",open=500,high=500,low=500,close=500)
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["status"],"unknown_fill")
        self.assertIsNone(result["trade"])

    def test_roll_after_fill_censors_before_new_contract_prices(self):
        ep,bars,ctx=reclaim_context()
        for i,b in enumerate(bars):
            if b.timestamp>=clock(8):bars[i]=replace(b,contract="GCJ4",open=500,high=500,low=500,close=500)
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["status"],"filled_censored")
        self.assertEqual(result["trade"]["censor_reason"],"contract_transition")
        self.assertEqual(result["trade"]["mfe_points"],0)

    def test_passive_trade_through_and_touch_only_are_distinct(self):
        ep,bars=fixture()
        set_minute(bars,8,o=98,h=99,l=97.5,c=98)
        ctx=context(ep,bars)
        through=run_policy(ctx,PolicySpec("passive","passive",.25,1),cfg())
        touch=run_policy(ctx,PolicySpec("touch","passive",.25,0),cfg())
        self.assertEqual(through["status"],"known_no_fill")
        self.assertFalse(through["opportunity"])
        self.assertTrue(touch["opportunity"])
        self.assertEqual(touch["trade"]["entry_price_raw"],97.5)

    def test_passive_submission_without_level_contact_is_not_opportunity(self):
        ep,bars=fixture()
        result=run_policy(context(ep,bars),PolicySpec("passive","passive",.25,1),cfg())
        self.assertTrue(result["armed"])
        self.assertTrue(result["signal"])
        self.assertFalse(result["opportunity"])
        self.assertEqual(result["status"],"known_no_fill")

    def test_passive_exact_open_requires_primary_trade_through(self):
        ep,bars=fixture()
        set_minute(bars,8,o=97.5,h=98,l=97.5,c=98)
        through=run_policy(context(ep,bars),PolicySpec("passive","passive",.25,1),cfg())
        self.assertEqual(through["status"],"known_no_fill")

    def test_passive_favorable_gap_through_stop_keeps_fill_and_cost(self):
        ep,bars=fixture()
        set_minute(bars,8,o=90)
        result=run_policy(context(ep,bars),PolicySpec("passive","passive",.25,1),Phase2Config())
        self.assertEqual(result["trade"]["entry_price_raw"],90)
        self.assertIsNone(result["trade"]["risk_initial_points"])
        self.assertAlmostEqual(result["net_dollars"],-25)

    def test_passive_trade_through_fill_at_limit_not_low(self):
        ep,bars=fixture()
        set_minute(bars,8,o=98,h=98,l=97.4,c=98)
        result=run_policy(context(ep,bars),PolicySpec("passive","passive",.25,1),cfg())
        self.assertEqual(result["trade"]["entry_price_raw"],97.5)
        self.assertTrue(result["opportunity"])
        self.assertEqual(result["trade"]["initial_stop_anchor"],97.5)

    def test_whole_quantity_skip_never_invents_fractional_execution(self):
        ep,bars,ctx=reclaim_context()
        signal=find_signal(ctx,PolicySpec("mid","reclaim",.5),cfg())
        result=execute_signal(signal,ctx,cfg(),quantity=0)
        self.assertEqual(result["status"],"known_no_fill")
        self.assertTrue(result["quantity_skipped"])
        self.assertIsNone(result["trade"])
        with self.assertRaises(ValueError):execute_signal(signal,ctx,cfg(),quantity=.5)

    def test_source_15m_execution_preserves_15m_decisions_and_time_open(self):
        ep,bars,ctx=reclaim_context()
        result=run_policy(ctx,PolicySpec("mid","reclaim",.5),cfg(execution_minutes=15))
        self.assertEqual(result["trade"]["entry_time"],"2024-01-03T04:45:00Z")
        self.assertEqual(result["trade"]["reset_stop_active_at"],"2024-01-03T05:00:00Z")
        self.assertEqual(result["trade"]["exit_time"],"2024-01-03T17:00:00Z")

    def test_partial_retained_endpoint_open_trade_is_censored(self):
        ep,bars,ctx=reclaim_context()
        bars=[b for b in bars if b.timestamp<=clock(7,50)]
        result=run_policy(context(ep,bars),PolicySpec("mid","reclaim",.5),cfg())
        self.assertEqual(result["status"],"filled_censored")
        self.assertIsNone(result["trade"]["reset_stop"])


class BoundaryObservationTests(unittest.TestCase):
    def test_two_horizons_and_each_occurrence_event_retained(self):
        ep,bars=fixture()
        result=observe_episode(context(ep,bars),cfg())
        self.assertEqual(len(result["occurrence"]),8)
        self.assertEqual(len(result["recovery"]),12)
        self.assertFalse(event(result["occurrence"],"one_tick_breach")["occurred"])

    def test_touch_is_distinct_from_one_tick_breach(self):
        ep,bars=fixture()
        set_minute(bars,8,o=95,h=96,l=90,c=95)
        rows=observe_episode(context(ep,bars),cfg())["occurrence"]
        self.assertTrue(event(rows,"touch")["occurred"])
        self.assertFalse(event(rows,"one_tick_breach")["occurred"])

    def test_known_breach_survives_later_gap_and_recovery_unknown(self):
        ep,bars=fixture()
        after(bars,8,price=89)
        bars=[b for b in bars if b.timestamp!=clock(9)]
        result=observe_episode(context(ep,bars),cfg())
        breached=event(result["occurrence"],"one_tick_breach")
        self.assertTrue(breached["occurred"])
        self.assertFalse(breached["complete_observation"])
        self.assertEqual(breached["first_time"],"2024-01-03T05:00:00Z")
        recover=next(r for r in result["recovery"] if r["horizon"]=="remaining_broker_window" and r["recovery_level"]=="original_boundary" and r["event"]=="touch")
        self.assertIsNone(recover["occurred"])

    def test_event_after_gap_has_known_occurrence_but_no_exact_first(self):
        ep,bars=fixture()
        bars=[b for b in bars if b.timestamp!=clock(8)]
        set_minute(bars,9,o=89)
        rows=observe_episode(context(ep,bars),cfg())["occurrence"]
        breach=event(rows,"one_tick_breach")
        self.assertTrue(breach["occurred"])
        self.assertIsNone(breach["first_time"])
        self.assertIsNotNone(breach["first_observed_time"])
        self.assertIsNone(breach["event_session"])

    def test_incomplete_no_event_is_null_not_false(self):
        ep,bars=fixture()
        bars=[b for b in bars if b.timestamp!=clock(8)]
        rows=observe_episode(context(ep,bars),cfg())["occurrence"]
        self.assertIsNone(event(rows,"touch")["occurred"])

    def test_repeat_contacts_are_within_episode_not_new_episodes(self):
        ep,bars=fixture()
        set_minute(bars,8,o=95,h=95,l=90,c=95)
        set_minute(bars,9,o=95,h=95,l=90,c=95)
        row=event(observe_episode(context(ep,bars),cfg())["occurrence"],"touch")
        self.assertEqual(row["contact_count"],2)
        self.assertEqual(row["repeat_contacts"],1)
        self.assertEqual(row["observed_repeat_contacts_lower"],1)

    def test_prefill_protected_visit_excluded(self):
        ep,bars=fixture()
        set_minute(bars,7,4,o=95,h=99,l=89,c=99)
        row=event(observe_episode(context(ep,bars),cfg())["occurrence"],"touch")
        self.assertFalse(row["occurred"])

    def test_same_entry_minute_ordering_uncertainty_is_null(self):
        ep,bars=fixture()
        set_minute(bars,7,5,o=99.5,h=100.5,l=89,c=100.2)
        row=event(observe_episode(context(ep,bars),cfg())["occurrence"],"one_tick_breach")
        self.assertIsNone(row["occurred"])
        self.assertTrue(row["ordering_ambiguous"])

    def test_price_recovery_is_not_an_executed_trade_target(self):
        ep,bars=fixture()
        set_minute(bars,8,o=89)
        result=observe_episode(context(ep,bars),cfg())
        for row in result["recovery"]:
            self.assertTrue(row["not_executed_trade_target"])
        full=[r for r in result["recovery"] if r["horizon"]=="remaining_broker_window" and r["event"]=="touch"]
        self.assertTrue(all(r["occurred"] for r in full))

    def test_reclaim_confirmation_requires_separate_later_candle(self):
        ep,bars=fixture()
        set_minute(bars,8,o=95,h=96,l=89.9,c=95)
        set_minute(bars,8,14,o=95)
        row=event(observe_episode(context(ep,bars),cfg())["occurrence"],"reclaim")
        self.assertEqual(row["first_time"],"2024-01-03T05:30:00Z")

    def test_roll_barrier_never_compares_incoming_contract_price(self):
        ep,bars=fixture()
        for i,b in enumerate(bars):
            if b.timestamp>=clock(8):bars[i]=replace(b,contract="GCJ4",open=50,high=50,low=50,close=50)
        row=event(observe_episode(context(ep,bars),cfg())["occurrence"],"one_tick_breach")
        self.assertIsNone(row["occurred"])
        self.assertIsNone(row["first_observed_time"])

    def test_level_returns_exclude_original_q0_fill_and_prefill(self):
        ep,bars=fixture()
        rows=observe_levels(context(ep,bars),cfg())
        q0=next(r for r in rows if r["fraction"]==0 and r["event"]=="touch")
        self.assertFalse(q0["occurred"])
        self.assertTrue(q0["not_realized_trade_return"])

    def test_previous_close_at_original_open_cannot_be_prefill_confirmation(self):
        ep=original(entry_time=clock(7),entry_time_latest=clock(7),entry_time_precision="observed_open")
        ep,bars=fixture(episode=ep)
        set_minute(bars,7,o=100.5)
        candles=decision_candles(bars)
        candles.insert(0,DecisionBar(clock(6,45),95,99,94,95,"GCG4",clock(7),True))
        rows=observe_levels(context(ep,bars,candles=candles),cfg())
        mid=next(r for r in rows if r["fraction"]==.5 and r["event"]=="inward_close")
        self.assertFalse(mid["occurred"])

    def test_level_recovery_before_opposite_is_separate_from_net_profit(self):
        ep,bars=fixture()
        set_minute(bars,8,o=98,h=98,l=95,c=96)
        row=next(r for r in observe_levels(context(ep,bars),cfg()) if r["fraction"]==.5 and r["event"]=="touch")
        self.assertTrue(row["range_recovery_before_opposite"])
        self.assertAlmostEqual(row["event_risk_points"],.9)

    def test_close_at_original_session_end_excluded_then_next_session_in_full_window(self):
        ep,bars=fixture()
        set_minute(bars,9,59,o=89)
        rows=observe_episode(context(ep,bars),cfg())["occurrence"]
        self.assertFalse(event(rows,"close_break","original_session")["occurred"])
        self.assertTrue(event(rows,"one_tick_breach","original_session")["occurred"])
        full=event(rows,"close_break")
        self.assertTrue(full["occurred"])
        self.assertEqual(full["event_session"],"london")

    def test_final_broker_confirmation_allowed_when_cutoff_clamps_named_session(self):
        ep=original(entry_time=clock(18,5),entry_time_latest=clock(18,6))
        ep,bars=fixture(episode=ep)
        set_minute(bars,19,59,o=89)
        rows=observe_episode(context(ep,bars),cfg())["occurrence"]
        same=event(rows,"close_break","original_session")
        self.assertTrue(same["occurred"])
        self.assertTrue(same["close_confirmation_endpoint_included"])
        self.assertEqual(same["first_time"],"2024-01-03T17:00:00Z")

    def test_same_minute_recovery_order_disagreement_remains_unknown(self):
        ep,bars=fixture()
        after(bars,8,price=99)
        set_minute(bars,8,o=99,h=100,l=89.9,c=99)
        result=observe_episode(context(ep,bars),cfg())
        row=next(r for r in result["recovery"] if r["horizon"]=="remaining_broker_window" and r["recovery_level"]=="original_boundary" and r["event"]=="touch")
        self.assertIsNone(row["occurred"])
        self.assertTrue(row["ordering_ambiguous"])

    def test_lower_first_protected_high_mirror(self):
        ep,bars=fixture()
        set_minute(bars,8,o=95,h=96,l=89.9,c=95)
        upper=observe_episode(context(ep,bars),cfg())
        mirror=replace(ep,direction=-1,entry_price_raw=90)
        reflected=[replace(b,open=190-b.open,high=190-b.low,low=190-b.high,close=190-b.close) for b in bars]
        lower=observe_episode(context(mirror,reflected),cfg())
        self.assertEqual(event(upper["occurrence"],"one_tick_breach")["occurred"],event(lower["occurrence"],"one_tick_breach")["occurred"])
        self.assertEqual(event(lower["occurrence"],"touch")["protected_side"],"high")

    def test_scheduled_closure_absence_does_not_censor_observation(self):
        ep,bars=fixture()
        missing=clock(8)
        bars=[b for b in bars if b.timestamp!=missing]
        row=event(observe_episode(context(ep,bars,calendar=lambda t:t!=missing),cfg())["occurrence"],"touch")
        self.assertTrue(row["complete_observation"])
        self.assertFalse(row["occurred"])


class CausalClockTests(unittest.TestCase):
    def test_asia_cross_midnight_session_instance(self):
        ny=ZoneInfo("America/New_York")
        entry=datetime(2024,1,2,23,30,tzinfo=ny).astimezone(UTC)
        cutoff=entry+timedelta(hours=12)
        end,session,clamped=session_horizon_end(entry,cutoff)
        self.assertEqual(end.astimezone(ny),datetime(2024,1,3,2,tzinfo=ny))
        self.assertEqual(session,"Asia")
        self.assertFalse(clamped)

    def test_outside_interval_ends_at_next_named_session(self):
        ny=ZoneInfo("America/New_York")
        entry=datetime(2024,6,3,9,10,tzinfo=ny).astimezone(UTC)
        end,session,_=session_horizon_end(entry,entry+timedelta(hours=3))
        self.assertEqual(end.astimezone(ny).hour,9)
        self.assertEqual(end.astimezone(ny).minute,30)
        self.assertEqual(session,"Outside")

    def test_original_flat_loss_known_only_after_exit_availability(self):
        ep=original(baseline_exit_time=clock(8,2),baseline_exit_time_latest=clock(8,3),baseline_exit_time_precision="within_bar")
        self.assertEqual(baseline_state(ep,clock(8,14))["baseline_position_status"],"open")
        self.assertTrue(baseline_state(ep,clock(8,15))["baseline_loss_known"])

    def test_same_next_open_exit_not_prior_flat_at_signal(self):
        ep=original(baseline_exit_time=clock(8),baseline_exit_time_latest=clock(8),baseline_exit_time_precision="observed_open")
        self.assertEqual(baseline_state(ep,clock(8))["baseline_position_status"],"open")
        self.assertEqual(baseline_state(ep,clock(8,15))["baseline_position_status"],"flat")

    def test_dst_changes_reporting_not_fixed_broker_cutoff(self):
        ny=ZoneInfo("America/New_York")
        self.assertEqual(original().cutoff.astimezone(ny).hour,12)
        summer=original(broker_day="2024-07-03",entry_time=clock(7,5,"2024-07-03"),entry_time_latest=clock(7,6,"2024-07-03"))
        self.assertEqual(summer.cutoff.astimezone(ny).hour,13)


if __name__=="__main__":unittest.main()
