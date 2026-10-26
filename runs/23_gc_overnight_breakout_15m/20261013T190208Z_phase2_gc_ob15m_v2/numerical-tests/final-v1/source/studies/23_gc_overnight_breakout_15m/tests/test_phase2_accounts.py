"""Actual account budgeting and causal financial recovery, synthetic only."""
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2_accounts import (AccountConfig,account_results,budget_quantity,financial_recovery)
from src.phase2_engine import BaselineEpisode,Phase2Config
from test_phase2_engine import clock,context,fixture,set_minute,after,original

PRIMARY="reclaim-q050"


def synthetic(*,capital=20000,exit_hour=7,exit_minute=30,loss=-125.,later_price=96.,
              missing=None,censored=False,day="2024-01-03"):
    ep=original(baseline_exit_time=clock(exit_hour,exit_minute),baseline_exit_time_latest=clock(exit_hour,exit_minute),
                baseline_net_dollars=loss,baseline_status="censored" if censored else "completed",
                baseline_censor_at=clock(8) if censored else None)
    ep,bars=fixture(episode=ep)
    set_minute(bars,7,29,o=95.)
    set_minute(bars,7,44,o=95.2)
    set_minute(bars,7,45,o=95.2)
    after(bars,7,46,price=later_price)
    if missing is not None:bars=[b for b in bars if b.timestamp!=missing]
    if day!="2024-01-03":
        target=clock(7,5,day=day);delta=target-ep.entry_time
        ep=replace(ep,episode_id=day,broker_day=day,entry_time=ep.entry_time+delta,
                   entry_time_latest=ep.entry_time_latest+delta,
                   baseline_exit_time=ep.baseline_exit_time+delta,baseline_exit_time_latest=ep.baseline_exit_time_latest+delta,
                   baseline_censor_at=ep.baseline_censor_at+delta if ep.baseline_censor_at else None)
        bars=[replace(b,timestamp=b.timestamp+delta,available_at=b.available_at+delta) for b in bars]
    unit={"trade_id":ep.episode_id,"broker_day":ep.broker_day,"contract":ep.contract,"quantity":1,
          "status":ep.baseline_status,"initial_stop":99.,"entry_price":100.1,"entry_price_raw":100.,
          "entry_time":ep.entry_time.isoformat(),"exit_time":ep.baseline_exit_time.isoformat(),
          "net_dollars":None if censored else loss,"gross_dollars":None if censored else loss+5,
          "commission_dollars":None if censored else 5.,"risk_initial_dollars":110.,
          "last_observed_at":ep.baseline_censor_at.isoformat() if ep.baseline_censor_at else ep.baseline_exit_time.isoformat()}
    return context(ep,bars),unit,AccountConfig(initial_capital=capital)


def result(ctx,unit,a=None,*,selection=PRIMARY,roster=None):
    return account_results([ctx],{ctx.episode.episode_id:unit},{"selected_policy":selection},account_config=a,range_roster=roster)


def row(output,mode,policy=PRIMARY):
    return next(r for r in output["ledgers"] if r["mode"]==mode and r["policy"]==policy)


def cohort(output,mode,policy=PRIMARY):
    return next(r for r in output["cohorts"] if r["mode"]==mode and r["policy"]==policy and r["year"]=="all" and r["session"]=="all" and r["side"]=="combined")


class BudgetTests(unittest.TestCase):
    def test_frozen_defaults_and_whole_contract_requirement(self):
        self.assertEqual(AccountConfig().initial_capital,10000)
        with self.assertRaises(ValueError):AccountConfig(quantity_step=.5)
        with self.assertRaises(ValueError):AccountConfig(initial_capital=float("nan"))

    def test_realistic_gc_one_percent_account_is_infeasible(self):
        size=budget_quantity(10000,2000,1980,fraction=1.)
        self.assertEqual(size["quantity"],0)
        self.assertEqual(size["risk_budget_dollars"],100)
        self.assertEqual(size["leverage_quantity"],0)

    def test_half_budget_does_not_replenish_after_profit(self):
        size=budget_quantity(20000,100,99,fraction=.5,capacity_equity=30000)
        self.assertEqual(size["risk_budget_dollars"],100)
        self.assertEqual(size["quantity"],1)

    def test_concurrent_notional_and_margin_reduce_capacity(self):
        size=budget_quantity(20000,100,99.9,fraction=.5,active_notional=190000,active_margin=9500)
        self.assertEqual(size["risk_quantity"],10)
        self.assertEqual(size["leverage_quantity"],1)
        self.assertEqual(size["quantity"],1)

    def test_margin_can_bind_before_leverage(self):
        a=AccountConfig(initial_capital=20000,margin_percent=100)
        size=budget_quantity(20000,100,99.9,fraction=1.,account=a)
        self.assertEqual(size["quantity"],2)
        self.assertEqual(size["margin_quantity"],2)

    def test_unknown_equity_is_not_zero_capacity(self):
        self.assertIsNone(budget_quantity(None,100,99,fraction=.5)["quantity"])

    def test_zero_or_negative_equity_cannot_open(self):
        self.assertEqual(budget_quantity(-5,100,99,fraction=1.)["quantity"],0)


class RecoveryTests(unittest.TestCase):
    def test_actual_combined_costs_define_recovery(self):
        self.assertEqual(financial_recovery(-125,150,loss_known=True,actually_executed=True)["category"],"full_recovery")
        self.assertEqual(financial_recovery(-125,50,loss_known=True,actually_executed=True)["category"],"partial_recovery")
        self.assertEqual(financial_recovery(-125,0,loss_known=True,actually_executed=True)["category"],"no_improvement")
        self.assertEqual(financial_recovery(-125,-25,loss_known=True,actually_executed=True)["category"],"further_loss")

    def test_unit_loss_without_actual_original_denies_recovery(self):
        self.assertIsNone(financial_recovery(-125,500,loss_known=True,actually_executed=False))
        self.assertIsNone(financial_recovery(-125,500,loss_known=False,actually_executed=True))

    def test_breakeven_tolerance_and_recovered_loss_amount(self):
        r=financial_recovery(-100,100-1e-9,loss_known=True,actually_executed=True)
        self.assertEqual(r["category"],"full_recovery")
        self.assertAlmostEqual(r["loss_recovered_dollars"],100)


class ActualAccountTests(unittest.TestCase):
    def test_genuinely_executed_half_legs_and_costs(self):
        ctx,unit,a=synthetic()
        output=result(ctx,unit,a)
        r=row(output,"post_realized_loss_recovery")
        self.assertEqual((r["original_quantity"],r["second_quantity"]),(1,1))
        self.assertTrue(r["completed_pair"])
        self.assertTrue(r["original_loss_known_at_signal"])
        self.assertEqual(r["original_trade"]["commission_dollars"],5)
        self.assertEqual(r["second_trade"]["commission_dollars"],5)
        self.assertAlmostEqual(r["second_net_dollars"],55)
        self.assertAlmostEqual(r["net_dollars"],-70)
        self.assertEqual(r["recovery_category"],"partial_recovery")
        self.assertAlmostEqual(r["recovery_dollars"],55)
        self.assertGreater(r["recovery_minutes"],0)

    def test_original_full_budget_scales_only_actual_quantity(self):
        ctx,unit,a=synthetic()
        r=row(result(ctx,unit,a),"original_only","baseline")
        self.assertEqual(r["original_quantity"],2)
        self.assertEqual(r["net_dollars"],-250)
        self.assertEqual(r["original_trade"]["commission_dollars"],10)

    def test_default_capital_cannot_invent_actual_original_loss(self):
        ctx,unit,_=synthetic()
        # At this synthetic price full allocation permits one, half permits
        # zero; source-account loss-recovery must use half actual execution.
        output=result(ctx,unit)
        r=row(output,"post_realized_loss_recovery")
        self.assertEqual(r["original_quantity"],0)
        self.assertFalse(r["eligible_loss"])
        self.assertFalse(r["second_filled"])
        self.assertIsNone(r["recovery_category"])
        self.assertEqual(r["net_dollars"],0)
        self.assertIsNone(cohort(output,"post_realized_loss_recovery")["recovery_rate"])

    def test_realistic_gc_prices_preserve_zero_actual_fills_all_modes(self):
        ctx,unit,_=synthetic()
        ep=replace(ctx.episode,range_high=2000,range_low=1800,entry_price_raw=2000)
        minutes=[replace(b,open=b.open*20,high=b.high*20,low=b.low*20,close=b.close*20) for b in ctx.minutes]
        unit={**unit,"initial_stop":1980,"entry_price":2000.1,"entry_price_raw":2000,"net_dollars":-2405,"gross_dollars":-2400}
        output=result(context(ep,minutes),unit)
        self.assertTrue(all(not r["original_filled"] and not r["second_filled"] for r in output["ledgers"]))
        self.assertTrue(all(r["net_dollars"]==0 for r in output["ledgers"]))
        self.assertTrue(all(not r["eligible_loss"] and r["recovery_category"] is None for r in output["ledgers"]))
        self.assertTrue(row(output,"replacement_only")["second_quantity_skipped"])

    def test_replacement_only_is_an_actual_full_budget_trade(self):
        ctx,unit,a=synthetic()
        r=row(result(ctx,unit,a),"replacement_only")
        self.assertFalse(r["original_filled"])
        self.assertEqual(r["second_quantity"],2)
        self.assertAlmostEqual(r["net_dollars"],110)
        self.assertFalse(r["completed_pair"])

    def test_positive_later_leg_can_fully_recover_executed_loss(self):
        ctx,unit,a=synthetic(later_price=97)
        r=row(result(ctx,unit,a),"post_realized_loss_recovery")
        self.assertEqual(r["recovery_category"],"full_recovery")
        self.assertAlmostEqual(r["net_dollars"],30)

    def test_two_legs_use_actually_produced_synthetic_baseline_execution(self):
        from test_engine import fixture as phase1_fixture,change as phase1_change,after as phase1_after
        from src.engine import EngineConfig,run_backtest
        bars=phase1_fixture()
        phase1_change(bars,7,o=100)
        phase1_after(bars,7,1,price=100.5)
        phase1_change(bars,7,20,o=100.5,h=100.5,l=99.1,c=100.5)
        phase1_change(bars,7,29,o=95)
        phase1_change(bars,7,44,o=95.2)
        phase1_after(bars,7,45,price=95.2)
        phase1_after(bars,7,46,price=96)
        unit=run_backtest(bars,EngineConfig(),expected_minute=lambda t:True).trades[0]
        self.assertAlmostEqual(unit["net_dollars"],-115)
        ep=BaselineEpisode.from_rows(unit,{"range_high":100,"range_low":90})
        minutes=[b for b in bars if ep.breakout_bar_open<=b.timestamp<=ep.cutoff]
        output=account_results([context(ep,minutes)],{ep.episode_id:unit},{"selected_policy":PRIMARY},account_config=AccountConfig(initial_capital=20000))
        r=row(output,"post_realized_loss_recovery")
        self.assertTrue(r["original_filled"] and r["second_filled"] and r["completed_pair"])
        self.assertAlmostEqual(r["net_dollars"],-60)
        self.assertAlmostEqual(r["original_trade"]["net_dollars"],unit["net_dollars"])
        self.assertEqual(r["recovery_category"],"partial_recovery")

    def test_later_leg_losses_include_both_fees_and_are_further_loss(self):
        ctx,unit,a=synthetic(later_price=95.2)
        r=row(result(ctx,unit,a),"post_realized_loss_recovery")
        self.assertAlmostEqual(r["second_net_dollars"],-25)
        self.assertEqual(r["recovery_category"],"further_loss")
        self.assertAlmostEqual(r["net_dollars"],-150)

    def test_original_open_denies_flat_reentry_but_allows_same_direction_addon(self):
        ctx,unit,a=synthetic(exit_hour=10)
        output=result(ctx,unit,a)
        self.assertTrue(row(output,"same_direction_concurrent_add_on")["second_filled"])
        flat=row(output,"post_exit_reentry")
        self.assertFalse(flat["second_filled"])
        self.assertEqual(flat["reason"],"first_signal_not_same_direction_post_exit")
        self.assertFalse(row(output,"post_realized_loss_recovery")["second_filled"])

    def test_opposite_signal_while_original_open_is_never_hedged_or_retried(self):
        ctx,unit,a=synthetic(exit_hour=10)
        bars=list(ctx.minutes)
        set_minute(bars,7,29,o=89.8)
        after(bars,7,30,price=89.8)
        output=result(context(ctx.episode,bars),unit,a)
        reversal="protected-reversal"
        standalone=row(output,"replacement_only",reversal)
        self.assertTrue(standalone["second_filled"])
        self.assertEqual(standalone["second_trade"]["direction"],-1)
        for mode in ("same_direction_concurrent_add_on","flat_only_opposite_reversal"):
            r=row(output,mode,reversal)
            self.assertFalse(r["second_filled"])
            self.assertIsNone(r["second_trade"])
            self.assertEqual(r["original_position_at_signal"],"open")

    def test_flat_opposite_leg_without_executed_original_is_not_financial_recovery(self):
        ep=original(range_high=2000,range_low=100,entry_price_raw=2000,entry_time_precision="observed_open")
        ep,bars=fixture(episode=ep)
        set_minute(bars,7,5,o=2000)
        set_minute(bars,7,29,o=99)
        after(bars,7,30,price=99)
        after(bars,7,31,price=98)
        unit={"quantity":1,"status":"completed","initial_stop":1980,"net_dollars":-1000,"commission_dollars":5}
        output=result(context(ep,bars),unit,AccountConfig(initial_capital=20000))
        r=row(output,"flat_only_opposite_reversal","protected-reversal")
        self.assertEqual(r["original_quantity"],0)
        self.assertTrue(r["second_filled"])
        self.assertFalse(r["eligible_loss"])
        self.assertIsNone(r["recovery_category"])

    def test_opening_exit_same_signal_instant_is_not_prior_flat_loss(self):
        ctx,unit,a=synthetic(exit_hour=7,exit_minute=45)
        r=row(result(ctx,unit,a),"post_realized_loss_recovery")
        self.assertFalse(r["second_filled"])
        self.assertEqual(r["original_position_at_signal"],"open")

    def test_original_win_is_not_eligible_loss_recovery(self):
        ctx,unit,a=synthetic(loss=100)
        r=row(result(ctx,unit,a),"post_realized_loss_recovery")
        self.assertFalse(r["eligible_loss"])
        self.assertFalse(r["second_filled"])

    def test_real_leg_censor_propagates_unknown_equity_next_day(self):
        first,unit,a=synthetic(missing=clock(8))
        second,unit2,_=synthetic(day="2024-01-04")
        output=account_results([second,first],{first.episode.episode_id:unit,second.episode.episode_id:unit2},{"selected_policy":PRIMARY},account_config=a)
        rows=[r for r in output["ledgers"] if r["mode"]=="replacement_only" and r["policy"]==PRIMARY]
        self.assertTrue(rows[0]["censored"])
        self.assertIsNone(rows[0]["equity_after_episode"])
        self.assertEqual(rows[1]["reason"],"account_equity_unknown_from_prior_episode")
        self.assertIsNone(rows[1]["second_filled"])
        self.assertIsNone(rows[1]["second_quantity"])
        self.assertEqual(cohort(output,"replacement_only")["unknown_second_fills"],1)
        self.assertIsNone(cohort(output,"replacement_only")["net_dollars"])

    def test_realized_equity_compounds_only_after_actual_completed_legs(self):
        first,unit,a=synthetic()
        second,unit2,_=synthetic(day="2024-01-04")
        output=account_results([second,first],{first.episode.episode_id:unit,second.episode.episode_id:unit2},None,account_config=a)
        rows=[r for r in output["ledgers"] if r["mode"]=="original_only"]
        self.assertEqual(rows[0]["original_quantity"],2)
        self.assertEqual(rows[0]["equity_after_episode"],19750)
        self.assertEqual(rows[1]["day_start_equity"],19750)
        self.assertEqual(rows[1]["original_quantity"],1)
        self.assertEqual(rows[1]["equity_after_episode"],19625)

    def test_zero_quantity_ignores_standardized_baseline_censor(self):
        ctx,unit,_=synthetic(censored=True)
        output=result(ctx,unit)
        r=row(output,"post_realized_loss_recovery")
        self.assertFalse(r["original_filled"])
        self.assertFalse(r["censored"])
        self.assertFalse(r["unknown"])
        self.assertEqual(r["net_dollars"],0)

    def test_unknown_signal_is_not_automatic_quantity_skip_or_zero(self):
        ctx,unit,a=synthetic(missing=clock(7,20))
        r=row(result(ctx,unit,a),"replacement_only")
        self.assertTrue(r["unknown"])
        self.assertIsNone(r["net_dollars"])
        self.assertFalse(r["second_quantity_skipped"])
        self.assertIsNone(r["second_filled"])
        self.assertIsNone(r["second_quantity"])
        self.assertEqual(r["quantity_skips"],0)

    def test_structurally_ineligible_no_original_mode_stays_known_no_trade(self):
        ctx,unit,_=synthetic(missing=clock(7,20))
        r=row(result(ctx,unit),"post_realized_loss_recovery")
        self.assertFalse(r["unknown"])
        self.assertEqual(r["net_dollars"],0)

    def test_capacity_audit_preserves_all_eligible_days_and_two_sides(self):
        ctx,unit,a=synthetic()
        roster={"2024-01-03":{"range_high":2000,"range_low":1980,"eligible":True},
                "2024-01-04":{"range_high":2100,"range_low":2000,"eligible":True},
                "2024-01-05":{"range_high":2200,"range_low":2100,"eligible":False}}
        output=result(ctx,unit,a,roster=roster)
        self.assertEqual(len(output["capacity_audit"]),4)
        self.assertEqual({r["side"] for r in output["capacity_audit"]},{"long","short"})
        self.assertTrue(all(r["population"]=="full_causally_eligible_day_roster" for r in output["capacity_audit"]))

    def test_no_selection_retains_three_protected_rules_without_primary(self):
        ctx,unit,a=synthetic()
        output=result(ctx,unit,a,selection=None)
        self.assertEqual(len(output["selected_policies"]),3)
        self.assertTrue(all(p.startswith("protected-") for p in output["selected_policies"]))
        self.assertEqual(len(output["ledgers"]),16)

    def test_original_cohorts_do_not_invent_candidate_fill_sessions(self):
        ctx,unit,a=synthetic()
        output=result(ctx,unit,a)
        summary=cohort(output,"post_realized_loss_recovery")
        self.assertEqual(summary["episodes"],1)
        self.assertEqual(summary["original_fills"],1)
        self.assertEqual(summary["second_fills"],1)
        self.assertEqual(summary["eligible_loss"],1)
        self.assertEqual(summary["completed_pairs"],1)
        self.assertEqual(summary["partial_recovery"],1)
        self.assertEqual(summary["recovery_rate"],0)

    def test_named_session_counts_partition_all_account_episodes(self):
        ctx,unit,a=synthetic()
        output=result(ctx,unit,a)
        rows=[r for r in output["cohorts"] if r["policy"]==PRIMARY and r["mode"]=="replacement_only" and r["year"]=="all" and r["side"]=="combined"]
        self.assertEqual(sum(r["episodes"] for r in rows if r["session"]!="all"),cohort(output,"replacement_only")["episodes"])
        self.assertEqual(row(output,"replacement_only")["session"],"Asia")
        self.assertEqual(next(r for r in rows if r["session"]=="Asia")["episodes"],1)

    def test_duplicate_day_and_unknown_selection_are_rejected(self):
        ctx,unit,a=synthetic()
        with self.assertRaises(ValueError):result(ctx,unit,a,selection="optimized")
        with self.assertRaises(ValueError):account_results([ctx,ctx],{ctx.episode.episode_id:unit},None)


if __name__=="__main__":unittest.main()
