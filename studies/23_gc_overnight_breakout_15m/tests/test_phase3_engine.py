"""Causal Phase 3 fixtures; parent trades come from unchanged Phase 1 source."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import Bar, EngineConfig, run_backtest
from src.phase3_engine import Phase1DayData, Phase3Config, gate_admission, observe_episode, planned_quantity, run_episode
from phase3_inputs import CloudBar, CloudTimeline

UTC = timezone.utc
T = datetime(2018, 1, 3, 4, tzinfo=UTC)
ONE = timedelta(minutes=1)
FIVE = timedelta(minutes=5)


def fixture(*, side=1, edits=None, feature_edits=None, missing=(), cloud_missing=(),
            entry_minute=1, cfg=None, unknown_features=()):
    cfg = cfg or Phase3Config()
    edits, feature_edits = edits or {}, feature_edits or {}
    def mirror(price): return price if side == 1 else 200 - price
    bars = [Bar(T - timedelta(days=1), mirror(99), mirror(100) if side==1 else mirror(98),
                mirror(98) if side==1 else mirror(100), mirror(99), "GC:test")]
    start = T - timedelta(hours=7)
    for i in range(7 * 60):
        bars.append(Bar(start + i * ONE, mirror(99.5), 100 if side==1 else 102,
                        98 if side==1 else 100, mirror(99.5), "GC:test"))
    for i in range(13 * 60 + 1):
        prices = (104.,104.2,103.8,104.)
        if i < entry_minute: prices=(99.5,99.8,99.4,99.6)
        if i == entry_minute: prices=(99.5,100.5,99.2,100.2)
        if 10 <= i < 15 and i > entry_minute: prices=(104.,104.2,102.9,103.5)
        prices = edits.get(i, prices)
        if i in missing: continue
        o,h,l,c = prices
        bars.append(Bar(T+i*ONE,mirror(o),mirror(h) if side==1 else mirror(l),
                        mirror(l) if side==1 else mirror(h),mirror(c),"GC:test"))
    engine_cfg=EngineConfig(ordering=cfg.ordering,slippage_ticks=cfg.slippage_ticks,
                            commission_per_side=cfg.commission_per_side)
    parent_result=run_backtest(bars,engine_cfg,range_eligibility={"2018-01-03":{"eligible":True}},expected_minute=lambda _:True)
    parent=next(r for r in parent_result.trades if r["broker_day"]=="2018-01-03")
    bytime={b.timestamp:b for b in bars}
    slots=[T-timedelta(minutes=20)+i*FIVE for i in range(13*12+4)]
    clouds=[]
    for at in slots:
        if at in cloud_missing: continue
        minutes=[bytime.get(at+i*ONE) for i in range(5)]
        usable=all(b is not None for b in minutes)
        fast,slow=(98.5,98.) if at<T else (102.,101.) if at<T+FIVE else (103.,101.)
        fast,slow=feature_edits.get(at,(fast,slow))
        valid=usable and at not in unknown_features
        clouds.append(CloudBar(at,at+FIVE,"GC:test",
            minutes[0].open if usable else None,max(b.high for b in minutes) if usable else None,
            min(b.low for b in minutes) if usable else None,minutes[-1].close if usable else None,
            mirror(fast),mirror(slow),1.,usable,valid,300 if valid else 0,
            quality_reason="" if usable else "missing_source_minute"))
    timeline=CloudTimeline(clouds,slots)
    update_times=[T]
    update_times.extend(T+timedelta(minutes=i) for i in range(15,13*60,15) if T+timedelta(minutes=i)<=datetime.fromisoformat(parent["entry_time"].replace('Z','+00:00')))
    return Phase1DayData(parent["trade_id"],"2018-01-03",parent,tuple(bars),timeline,tuple(update_times),
        100 if side==1 else 102,98 if side==1 else 100,T+timedelta(hours=13),lambda _:True)


class Phase3EngineTests(unittest.TestCase):
    def test_parent_control_exact_and_exposure(self):
        day=fixture(); result=run_episode(day,"BASE",mode="parent_1")
        self.assertEqual(result["episode"]["net_dollars"],day.baseline_trade["net_dollars"])
        self.assertTrue(result["exposure"])
        self.assertGreater(result["episode"]["max_mtm_drawdown_dollars"],0)
        self.assertGreater(result["episode"]["peak_notional"],10000)
        self.assertTrue(all(r["policy"]=="BASE" for r in result["trades"]+result["exposure"]))
        self.assertAlmostEqual(result["episode"]["combined_planned_stop_risk_dollars"],100)
        self.assertAlmostEqual(result["trades"][0]["planned_stop_risk_dollars"],100)
        self.assertNotIn("planned_stop_risk_dollars",day.baseline_trade)

    def test_parent_control_scaling_and_cache(self):
        day=fixture(); one=run_episode(day,"BASE",mode="parent_1")
        two=run_episode(day,"BASE",mode="parent_2",precomputed_monitoring=one["monitoring"],precomputed_parent_exposure=one["exposure"])
        self.assertAlmostEqual(two["episode"]["net_dollars"],2*one["episode"]["net_dollars"])
        self.assertAlmostEqual(two["episode"]["max_mtm_drawdown_dollars"],2*one["episode"]["max_mtm_drawdown_dollars"])
        self.assertAlmostEqual(two["episode"]["peak_notional"],2*one["episode"]["peak_notional"])
        self.assertEqual(two["episode"]["peak_concurrent_quantity"],2)
        self.assertAlmostEqual(two["episode"]["combined_planned_stop_risk_dollars"],200)

    def test_source15_resolution_not_silently_refined(self):
        with self.assertRaisesRegex(ValueError,"unsupported"):
            Phase3Config(execution_minutes=15)

    def test_gate_alignment_no_source_width_threshold(self):
        day=fixture(); snapshot=day.cloud.snapshot(T,"GC:test")
        self.assertTrue(gate_admission(snapshot,1,"G1"))
        self.assertFalse(gate_admission(snapshot,-1,"G1"))
        self.assertFalse(gate_admission(snapshot,1,"G2"))
        result=run_episode(day,"G1")
        self.assertEqual(result["episode"]["net_dollars"],day.baseline_trade["net_dollars"])
        self.assertGreater(result["episode"]["peak_notional"],0)
        self.assertAlmostEqual(result["episode"]["combined_planned_stop_risk_dollars"],100)

    def test_equal_cloud_blocks_and_unknown_is_declared_abstention(self):
        day=fixture(feature_edits={T-FIVE:(100,100)})
        self.assertFalse(gate_admission(day.cloud.snapshot(T),1,"G1"))
        self.assertEqual(run_episode(day,"G1")["episode"]["status"],"no_fill")
        day=fixture(unknown_features=(T-FIVE,))
        result=run_episode(day,"G1")["episode"]
        self.assertEqual(result["net_dollars"],0)
        self.assertEqual(result["action_status"],"unknown_feature_abstention")

    def test_three_changes_slopes(self):
        changes={T-timedelta(minutes=20-i*5):(97+i*.5,96+i*.5) for i in range(4)}
        day=fixture(feature_edits=changes)
        self.assertTrue(gate_admission(day.cloud.snapshot(T),1,"G2"))

    def test_later_tied_changed_admission_unknown(self):
        changes={T+timedelta(minutes=10):(104,104)}
        day=fixture(entry_minute=15,feature_edits=changes)
        result=run_episode(day,"G1")["episode"]
        self.assertEqual(result["action_status"],"unknown_admission_cancellation")
        self.assertIsNone(result["net_dollars"])

    def test_full_postfill_no_entry_bucket_contacts(self):
        day=fixture(); rows=observe_episode(day)
        self.assertEqual(rows[0]["time"],"2018-01-03T04:05:00Z")
        self.assertTrue(all(r["population"]=="standardized_parent_post_fill_context" for r in rows))

    def test_fast_touch_does_not_consume_slow_attempt(self):
        day=fixture(); fast=run_episode(day,"A20",mode="diagnostic_1plus1")
        slow=run_episode(day,"A50",mode="diagnostic_1plus1")
        self.assertEqual(fast["episode"]["add_fills"],1)
        self.assertEqual(slow["episode"]["add_fills"],0)
        self.assertEqual(len([e for e in fast["events"] if e["event"]=="first_contact_consumed"]),1)

    def test_frozen_prior_level_not_contact_close_ema(self):
        day=fixture(feature_edits={T+timedelta(minutes=10):(104.5,101)})
        result=run_episode(day,"A20",mode="diagnostic_1plus1")
        contact=next(e for e in result["events"] if e["event"]=="first_contact_consumed")
        self.assertEqual(contact["frozen_level"],103)
        self.assertEqual(result["episode"]["add_fills"],1)

    def test_rejected_first_touch_no_later_cherry_pick(self):
        edits={i:(104,104.2,102.9,102.9) for i in range(10,15)}
        edits.update({i:(104,104.2,102.9,103.8) for i in range(20,25)})
        result=run_episode(fixture(edits=edits),"A20",mode="diagnostic_1plus1")
        self.assertEqual(result["episode"]["add_fills"],0)
        self.assertEqual(result["episode"]["add_attempts"],1)
        self.assertEqual(result["episode"]["action_status"],"rejected_confirmation")

    def test_unknown_prefix_irrevocable(self):
        day=fixture(cloud_missing=(T,),edits={i:(104,104.2,102.9,103.5) for i in range(20,25)})
        result=run_episode(day,"A20",mode="diagnostic_1plus1")
        self.assertEqual(result["episode"]["add_fills"],0)
        self.assertTrue(result["episode"]["unknown_support_prefix"])
        self.assertFalse(any(r["ema20_contact"] for r in result["monitoring"]))

    def test_unknown_feature_prefix_later_contacts_not_first(self):
        day=fixture(unknown_features=(T,),edits={i:(104,104.2,102.9,103.5) for i in range(20,25)})
        result=run_episode(day,"A20",mode="diagnostic_1plus1")
        self.assertEqual(result["episode"]["add_fills"],0)
        self.assertTrue(result["episode"]["unknown_support_prefix"])
        later=[r for r in result["monitoring"] if r["ema20_contact"]]
        self.assertTrue(later and later[0]["ema20_contact_number"] is None)

    def test_default_capital_no_hypothetical_financial_signals(self):
        result=run_episode(fixture(),"A20")
        self.assertEqual(result["episode"]["original_quantity"],0)
        self.assertEqual(result["episode"]["signals"],0)
        self.assertEqual(result["episode"]["financial_eligible_landmarks"],0)
        self.assertEqual(result["episode"]["net_dollars"],0)

    def test_raw_reserved_sizing_cost_overshoot(self):
        cfg=Phase3Config(initial_capital=20000)
        size=planned_quantity(20000,.5,100,99,1,cfg)
        self.assertEqual(size["quantity"],1)
        result=run_episode(fixture(cfg=cfg),"A20",cfg)
        self.assertEqual(result["episode"]["add_fills"],1)
        self.assertTrue(result["episode"]["risk_budget_overshoot"])
        self.assertAlmostEqual(result["episode"]["net_dollars"],sum(t["net_dollars"] for t in result["trades"]))

    def test_unknown_equity_is_not_default_capital(self):
        result=run_episode(fixture(),"A20",equity_start=None)["episode"]
        self.assertIsNone(result["original_quantity"])
        self.assertIsNone(result["original_filled"])
        self.assertIsNone(result["net_dollars"])

    def test_parent15_and_add5_reset(self):
        result=run_episode(fixture(),"A20",mode="diagnostic_1plus1")
        resets=[e for e in result["events"] if e["event"]=="stop_reset"]
        parent=next(e for e in resets if e["leg"]=="original")
        added=next(e for e in resets if e["leg"]=="add")
        self.assertEqual(parent["time"],"2018-01-03T04:15:00Z")
        self.assertEqual(added["time"],"2018-01-03T04:20:00Z")
        self.assertEqual((parent["decision_minutes"],added["decision_minutes"]),(15,5))

    def test_missing_opening_keeps_known_signal_and_reset(self):
        result=run_episode(fixture(missing=(15,)),"A20",mode="diagnostic_1plus1")
        self.assertEqual(result["episode"]["signals"],1)
        self.assertIsNone(result["episode"]["add_filled"])
        self.assertTrue(any(e["event"]=="stop_reset" for e in result["events"]))
        self.assertEqual(result["episode"]["status"],"censored")

    def test_missing_closing_minute_no_signal_or_reset(self):
        result=run_episode(fixture(missing=(14,)),"A20",mode="diagnostic_1plus1")
        self.assertEqual(result["episode"]["signals"],0)
        self.assertFalse(any(e["event"]=="stop_reset" for e in result["events"]))

    def test_parent_opening_stop_cancels_pending_add(self):
        result=run_episode(fixture(edits={15:(98,98.2,97.8,98)}),"A20",mode="diagnostic_1plus1")
        self.assertEqual(result["episode"]["signals"],1)
        self.assertEqual(result["episode"]["add_fills"],0)
        self.assertEqual(result["episode"]["pending_add_cancellations"],1)

    def test_filled_add_preserved_when_parent_stops_later_same_minute(self):
        result=run_episode(fixture(edits={15:(104,104.2,98,100)}),"A20",mode="diagnostic_1plus1")
        self.assertEqual(result["episode"]["add_fills"],1)
        self.assertEqual(result["episode"]["pending_add_cancellations"],0)
        self.assertEqual(len(result["trades"]),2)

    def test_long_short_add_mirror(self):
        long=run_episode(fixture(side=1),"A20",mode="diagnostic_1plus1")
        short=run_episode(fixture(side=-1),"A20",mode="diagnostic_1plus1")
        self.assertEqual(long["episode"]["add_fills"],short["episode"]["add_fills"])
        self.assertAlmostEqual(long["episode"]["net_dollars"],short["episode"]["net_dollars"])

    def test_positive_raw_move_can_fail_net_liquidation(self):
        edits={i:(100.3,100.4,99.9,100.2) for i in range(10,15)}
        changes={T+FIVE:(100,99.5),T+2*FIVE:(100,99.5)}
        result=run_episode(fixture(edits=edits,feature_edits=changes),"A20",mode="diagnostic_1plus1")
        contact=next(e for e in result["events"] if e["event"]=="first_contact_consumed")
        self.assertTrue(contact["confirmed"])
        self.assertLess(contact["liquidation_net"],0)
        self.assertEqual(result["episode"]["action_status"],"rejected_nonpositive_liquidation")

    def test_add_stopped_in_entry5m_is_not_reset_or_retried(self):
        result=run_episode(fixture(edits={16:(104,104.2,102.4,103)}),"A20",mode="diagnostic_1plus1")
        add=next(t for t in result["trades"] if t["leg"]=="add")
        self.assertEqual(add["exit_reason"],"stop")
        self.assertIsNone(add["reset_stop"])
        self.assertEqual(result["episode"]["add_attempts"],1)

    def test_favorable_gap_through_add_initial_stop_keeps_both_fills(self):
        result=run_episode(fixture(edits={15:(101,101.2,100.8,101)}),"A20",mode="diagnostic_1plus1")
        add=next(t for t in result["trades"] if t["leg"]=="add")
        self.assertEqual(add["entry_time"],add["exit_time"])
        self.assertAlmostEqual(add["net_dollars"],-25)
        self.assertIsNone(add["net_r"])
        self.assertFalse(add["protective_initial_risk_valid"])
        self.assertAlmostEqual(add["actual_initial_stop_loss_with_costs"],25)

    def test_binary_tick_equal_add_stop_has_null_initial_r_without_changing_fill(self):
        day=fixture(edits={15:(102.40000000000002,102.6,102.3,102.4)})
        result=run_episode(day,"A20",mode="diagnostic_1plus1")
        add=next(t for t in result["trades"] if t["leg"]=="add")
        self.assertGreater(add["entry_price"],add["initial_stop"])
        self.assertFalse(add["protective_initial_risk_valid"])
        self.assertIsNone(add["risk_initial_dollars"])
        self.assertIsNone(add["net_r"])
        self.assertAlmostEqual(add["net_dollars"],-25)

    def test_binary_tick_equal_trailing_stop_keeps_initial_r_and_null_effective_r(self):
        day=fixture(edits={1:(100.00000000000001,100.5,99.2,100.2),20:(104,104.2,100,101)},
            feature_edits={T:(102,100.2),T+FIVE:(103,100.2),T+2*FIVE:(103,100.2),T+3*FIVE:(103,100.2)})
        result=run_episode(day,"T50")
        trade=result["trades"][0]
        self.assertGreater(trade["entry_price"],trade["effective_stop"])
        self.assertAlmostEqual(trade["effective_stop"],100.1)
        self.assertIsNone(trade["risk_effective_points"])
        self.assertIsNone(trade["source_style_r"])
        self.assertAlmostEqual(trade["net_r"],trade["net_dollars"]/trade["risk_initial_dollars"])

    def test_x1_uses_same_frozen_edge_and_cuts_winner(self):
        edits={i:(104,104.2,100.2,100.5) for i in range(5,10)}
        edits.update({i:(101,101.2,100.4,100.6) for i in range(10,15)})
        edits[15]=(101,101.2,100.8,101)
        day=fixture(edits=edits,feature_edits={T+FIVE:(103,99)})
        result=run_episode(day,"X1")
        trade=result["trades"][0]
        self.assertEqual(trade["exit_reason"],"ema_X1")
        self.assertEqual(trade["exit_time"],"2018-01-03T04:15:00Z")
        self.assertLess(trade["net_dollars"],day.baseline_trade["net_dollars"])
        signal=next(e for e in result["events"] if e["event"]=="ema_exit_signal")
        self.assertEqual(signal["frozen_edge"],101)
        self.assertGreater(signal["original_liquidation_net"],0)
        self.assertEqual((trade["holding_minutes_lower"],trade["holding_minutes_upper"]),(13,14))
        self.assertEqual(trade["holding_bars"],1)
        self.assertEqual(trade["last_observed_at"],trade["exit_time"])

    def test_early_exit_saves_loss_and_excludes_signal_candle_from_future_path(self):
        edits={i:(104,104.2,100.2,100.5) for i in range(5,10)}
        edits.update({i:(101,120,100.4,100.6) for i in range(10,15)})
        edits[15]=(101,101.2,100.8,101)
        edits[30]=(104,104.2,98,100)
        day=fixture(edits=edits,feature_edits={T+FIVE:(103,99)})
        result=run_episode(day,"X1")
        self.assertLess(day.baseline_trade["net_dollars"],0)
        self.assertGreater(result["episode"]["net_dollars"],0)
        self.assertEqual(result["episode"]["time_saved_minutes"],15)
        self.assertEqual(result["episode"]["time_saved_minutes_upper"],16)
        self.assertAlmostEqual(result["episode"]["post_exit_favorable_points"],3.2)
        self.assertEqual(result["episode"]["post_exit_trace_status"],"known_authored_path")

    def test_missing_after_early_exit_keeps_policy_profit_but_unknown_tradeoff(self):
        edits={i:(104,104.2,100.2,100.5) for i in range(5,10)}
        edits.update({i:(101,101.2,100.4,100.6) for i in range(10,15)})
        day=fixture(edits=edits,feature_edits={T+FIVE:(103,99)},missing=(30,))
        result=run_episode(day,"X1")
        self.assertEqual(result["episode"]["status"],"completed")
        self.assertEqual(day.baseline_trade["status"],"censored")
        self.assertIsNone(result["episode"]["time_saved_minutes"])
        self.assertIsNone(result["episode"]["post_exit_favorable_points"])
        trade=result["trades"][0]
        self.assertIsNone(trade["observed_holding_minutes"])
        self.assertEqual(trade["last_observed_at"],trade["exit_time"])
        self.assertNotEqual(trade["holding_bars"],day.baseline_trade.get("holding_bars"))

    def test_contract_transition_censors_existing_legs_without_reusing_cloud(self):
        day=fixture()
        changed=tuple(replace(b,contract="GC:next") if b.timestamp>=T+timedelta(minutes=20) else b for b in day.minutes)
        result=run_episode(replace(day,minutes=changed),"A20",mode="diagnostic_1plus1")
        self.assertEqual(result["episode"]["status"],"censored")
        self.assertIsNone(result["episode"]["net_dollars"])
        self.assertTrue(all(t["censor_reason"]=="contract_transition" for t in result["trades"]))

    def test_x1_equality_resets_confirmation(self):
        edits={i:(104,104.2,100.2,100.5) for i in range(5,10)}
        edits.update({i:(101,101.2,100.8,101) for i in range(10,15)})
        result=run_episode(fixture(edits=edits),"X1")
        self.assertEqual(result["episode"]["signals"],0)

    def test_x1_unknown_slot_breaks_chain(self):
        edits={i:(104,104.2,100.2,100.5) for i in range(5,15)}
        result=run_episode(fixture(edits=edits,unknown_features=(T+2*FIVE,)),"X1")
        self.assertEqual(result["episode"]["signals"],0)
        self.assertTrue(any(e["event"]=="failure_confirmation_reset_unknown" for e in result["events"]))

    def test_x2_initial_opposition_is_not_fresh_cross(self):
        changes={T+i*FIVE:(100,101) for i in range(1,8)}
        result=run_episode(fixture(feature_edits=changes),"X2")
        self.assertEqual(result["episode"]["signals"],0)

    def test_x2_neutral_to_opposed_is_fresh(self):
        result=run_episode(fixture(feature_edits={T+FIVE:(101,101),T+2*FIVE:(100,101)}),"X2")
        self.assertEqual(result["episode"]["signals"],1)
        self.assertEqual(result["trades"][0]["exit_reason"],"ema_X2")

    def test_x2_unknown_prefix_cannot_invent_cross(self):
        changes={T+i*FIVE:(100,101) for i in range(2,8)}
        result=run_episode(fixture(feature_edits=changes,unknown_features=(T+FIVE,)),"X2")
        self.assertEqual(result["episode"]["signals"],0)

    def test_trail_future_only_and_source_reset_cannot_loosen(self):
        edits={i:(104,104.2,100.5,104) for i in range(5,10)}
        result=run_episode(fixture(edits=edits),"T50")
        activate=next(e for e in result["events"] if e["event"]=="trail_future_activation")
        self.assertEqual(activate["time"],"2018-01-03T04:10:00Z")
        self.assertAlmostEqual(activate["effective_stop"],100.9)
        reset=next(e for e in result["events"] if e["event"]=="stop_reset")
        self.assertAlmostEqual(reset["source_proposed_stop"],99.1)
        self.assertGreaterEqual(reset["effective_stop"],100.9)
        self.assertNotEqual(result["trades"][0]["exit_time"],"2018-01-03T04:05:00Z")
        trade=result["trades"][0]
        if trade["risk_effective_dollars"] is None:
            self.assertIsNone(trade["risk_effective_points"])
            self.assertIsNone(trade["source_style_r"])
        else:
            self.assertAlmostEqual(trade["risk_effective_dollars"],trade["risk_effective_points"]*100*trade["quantity"])

    def test_already_breached_trail_exits_next_open_not_past_stop(self):
        edits={i:(104,104.2,100.2,100.5) for i in range(5,10)}
        result=run_episode(fixture(edits=edits),"T50")
        trade=result["trades"][0]
        self.assertEqual(trade["exit_reason"],"ema_T50_already_breached")
        self.assertEqual(trade["exit_time"],"2018-01-03T04:10:00Z")
        self.assertEqual(trade["exit_price_raw"],104)

    def test_blocked_first_shadow_with_admitted_dual_opposite_unknown(self):
        day=fixture(edits={1:(99.5,100.5,97.5,100.2)},feature_edits={T-FIVE:(100.5,101)})
        result=run_episode(day,"G1")["episode"]
        self.assertEqual(result["action_status"],"unknown_shadow_cancel_ordering")
        self.assertIsNone(result["net_dollars"])

    def test_both_sides_blocked_dual_is_known_abstention(self):
        day=fixture(edits={1:(99.5,100.5,97.5,100.2)},feature_edits={T-FIVE:(100.5,100.5)})
        self.assertEqual(run_episode(day,"G1")["episode"]["net_dollars"],0)

    def test_unknown_current_confirmation_consumes_known_contact(self):
        result=run_episode(fixture(unknown_features=(T+2*FIVE,)),"A20",mode="diagnostic_1plus1")
        contacts=[e for e in result["events"] if e["event"]=="first_contact_consumed"]
        self.assertEqual(len(contacts),1)
        self.assertFalse(contacts[0]["confirmed"])
        self.assertEqual(result["episode"]["add_fills"],0)

    def test_closed_parent_context_kept_but_no_extra_adds(self):
        result=run_episode(fixture(edits={16:(104,104.2,98,100)}),"A20",mode="diagnostic_1plus1")
        self.assertTrue(any(r["parent_state_at_decision"]=="flat" for r in result["monitoring"]))
        self.assertEqual(result["episode"]["add_attempts"],1)

    def test_censored_trade_does_not_leak_frozen_future_pnl(self):
        result=run_episode(fixture(missing=(20,)),"A20",mode="diagnostic_1plus1")
        censored=[t for t in result["trades"] if t["status"]=="censored"]
        self.assertTrue(censored)
        self.assertTrue(all(t.get("gross_dollars") is None and t.get("net_r") is None for t in censored))
        self.assertTrue(all(t.get("exit_time_precision") is None for t in censored))
        self.assertFalse(result["episode"]["exposure_full_path_known"])
        self.assertIsNotNone(result["episode"]["observed_prefix_peak_notional"])


if __name__=="__main__": unittest.main()
