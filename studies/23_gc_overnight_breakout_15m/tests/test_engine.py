"""Meaningful synthetic execution tests; no historical market outcomes."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import (BROKER, Bar, EngineConfig, entry_cohort, ordering_bounds,
                        quantity_at_boundary, regular_gc_expected, round_tick,
                        run_backtest)

UTC = timezone.utc


def broker(day="2024-01-03", hour=0, minute=0):
    return datetime.fromisoformat(day).replace(hour=hour, minute=minute, tzinfo=BROKER).astimezone(UTC)


def fixture(*, end_hour=20, end_minute=14, contract="GCG4"):
    bars = [Bar(broker("2024-01-02"), 95, 100, 90, 95, contract)]
    start = broker()
    for offset in range(end_hour * 60 + end_minute + 1):
        t = start + timedelta(minutes=offset)
        o, h, l, c = (95, 100, 90, 95) if offset < 420 else (95, 97, 94, 95)
        bars.append(Bar(t, o, h, l, c, contract, t + timedelta(minutes=1)))
    return bars


def change(bars, hour, minute=0, *, o, h=None, l=None, c=None, **kw):
    target = broker(hour=hour, minute=minute)
    index = next(i for i, b in enumerate(bars) if b.timestamp == target)
    bars[index] = replace(bars[index], open=o, high=o if h is None else h,
                          low=o if l is None else l, close=o if c is None else c, **kw)


def after(bars, hour, minute=0, *, price=100.5):
    start = broker(hour=hour, minute=minute)
    for i, b in enumerate(bars):
        if b.timestamp >= start:
            bars[i] = replace(b, open=price, high=price, low=price, close=price)


def run(bars, **kwargs):
    return run_backtest(bars, EngineConfig(slippage_ticks=0, commission_per_side=0, **kwargs))


class EngineTests(unittest.TestCase):
    def test_tick_rounding_half_up_and_exact_decimal(self):
        self.assertEqual(round_tick(99.95), 100.0)
        self.assertEqual(round_tick(99.94), 99.9)

    def test_long_boundary_touch_and_time_exit(self):
        bars = fixture()
        after(bars, 7, 1)
        change(bars, 7, o=99.5, h=100, l=99.2, c=99.9)
        result = run(bars)
        trade = result.trades[0]
        self.assertEqual((trade["side"], trade["entry_price_raw"], trade["exit_reason"]), ("long", 100, "time"))
        self.assertEqual(trade["order_active_at"], "2024-01-03T04:00:00Z")
        self.assertEqual(trade["exit_time"], "2024-01-03T17:00:00Z")
        self.assertEqual(trade["net_dollars"], 50)

    def test_short_symmetry_exact_boundary_touch(self):
        bars = fixture()
        after(bars, 7, 1, price=89.5)
        change(bars, 7, o=90.5, h=90.8, l=90, c=90.1)
        trade = run(bars).trades[0]
        self.assertEqual((trade["side"], trade["entry_price_raw"], trade["initial_stop"]), ("short", 90, 90.9))
        self.assertEqual(trade["net_dollars"], 50)

    def test_first_loaded_day_excluded(self):
        bars = fixture()
        change(bars, 7, o=110)
        result = run(bars)
        first = result.days[0]
        self.assertFalse(first["eligible"])
        self.assertEqual(first["exclusion_reason"], "first_loaded_broker_day")

    def test_range_uses_0645_candle_not_0700(self):
        bars = fixture()
        change(bars, 6, 59, o=95, h=101, l=90, c=95)
        after(bars, 7, 1, price=101.5)
        change(bars, 7, o=100.5, h=101, l=100.4, c=100.9)
        result = run(bars)
        self.assertEqual(result.days[1]["range_high"], 101)
        self.assertEqual(result.trades[0]["entry_price_raw"], 101)

    def test_no_close_confirmation_requirement(self):
        bars = fixture(end_hour=7)
        after(bars, 7, 1, price=100.1)
        change(bars, 7, o=99.9, h=100, l=99.5, c=99.8)
        result = run(bars)
        self.assertEqual(result.days[1]["accepted_breakouts"], 1)
        self.assertLess(bars[421].close, 100)

    def test_oca_and_one_trade_same_candle_stop(self):
        bars = fixture()
        change(bars, 7, o=100, h=100, l=98, c=98.5)
        change(bars, 8, o=89, h=91, l=88, c=89)
        result = run(bars)
        self.assertEqual(len(result.trades), 1)
        self.assertEqual(result.trades[0]["exit_price_raw"], 99)
        self.assertEqual(result.trades[0]["holding_bars"], 0)
        self.assertEqual(result.days[1]["accepted_breakouts"], 1)
        self.assertEqual(sum(o["action"] == "first_fill_cancels_opposite" for o in result.orders), 1)

    def test_same_candle_stop_does_not_reset(self):
        bars = fixture()
        change(bars, 7, o=110, h=115, l=98, c=112)
        trade = run(bars).trades[0]
        self.assertEqual(trade["entry_price_raw"], 110)
        self.assertEqual(trade["exit_price_raw"], 99)
        self.assertIsNone(trade["reset_stop"])
        self.assertEqual(trade["risk_initial_dollars"], 1100)

    def test_open_gap_fill_preserved_not_boundary_fill(self):
        bars = fixture()
        after(bars, 7, price=110)
        trade = run(bars).trades[0]
        self.assertTrue(trade["gap_entry"])
        self.assertEqual(trade["entry_price_raw"], 110)
        self.assertEqual(trade["initial_stop"], 99)
        self.assertEqual(trade["reset_stop"], 108.9)

    def test_delayed_reset_at_15m_close_not_next_minute(self):
        bars = fixture()
        after(bars, 7, price=110)
        change(bars, 7, 5, o=110, h=110, l=105, c=110)
        trade = run(bars).trades[0]
        self.assertEqual(trade["exit_reason"], "time")
        self.assertEqual(trade["reset_stop_active_at"], "2024-01-03T04:15:00Z")
        self.assertEqual(trade["mae_points"], 5)

    def test_reset_stop_triggered_at_creation_exits_rebounded_open(self):
        bars = fixture()
        after(bars, 7, price=110)
        change(bars, 7, 14, o=110, h=110, l=105, c=105)
        change(bars, 7, 15, o=112)
        trade = run(bars).trades[0]
        self.assertEqual((trade["exit_time"], trade["exit_price_raw"], trade["exit_reason"]), ("2024-01-03T04:15:00Z", 112, "stop"))

    def test_reset_remains_fixed_after_entry_close(self):
        bars = fixture()
        after(bars, 7, price=110)
        after(bars, 8, price=120)
        trade = run(bars).trades[0]
        self.assertEqual(trade["reset_stop"], 108.9)
        self.assertEqual(trade["risk_initial_points"], 11)
        self.assertAlmostEqual(trade["risk_effective_points"], 1.1)

    def test_adverse_stop_gap_uses_actual_open(self):
        bars = fixture()
        after(bars, 7, price=100)
        change(bars, 8, o=95)
        trade = run(bars).trades[0]
        self.assertEqual((trade["exit_price_raw"], trade["net_dollars"]), (95, -500))

    def test_mfe_excludes_prefill_and_postexit_extremes(self):
        bars = fixture()
        change(bars, 7, o=99.5, h=101, l=98, c=98)
        result = run(bars, ordering="low_first")
        trade = result.trades[0]
        # Low98 occurs before the long fill100; stop99 occurs after high101.
        self.assertEqual((trade["entry_price_raw"], trade["mfe_points"], trade["mae_points"]), (100, 1, 1))

    def test_earlier_one_minute_evidence_resolves_15m_dual(self):
        bars = fixture()
        change(bars, 7, o=100, h=101, l=99.5, c=100)
        change(bars, 7, 1, o=100, h=100, l=88, c=90)
        trade = run(bars).trades[0]
        self.assertEqual(trade["side"], "long")
        self.assertFalse(trade["ambiguous"])

    def test_unresolved_dual_boundary_and_ordering_bounds(self):
        bars = fixture()
        change(bars, 7, o=95, h=102, l=88, c=95)
        hi = run(bars, ordering="high_first")
        lo = run(bars, ordering="low_first")
        self.assertEqual(hi.trades[0]["side"], "long")
        self.assertEqual(lo.trades[0]["side"], "short")
        self.assertTrue(hi.trades[0]["ambiguous"])
        bounds = ordering_bounds(hi, lo)[0]
        self.assertTrue(bounds["side_ordering_sensitive"])
        self.assertAlmostEqual(bounds["adverse_net_dollars"], -100)
        self.assertAlmostEqual(bounds["favorable_net_dollars"], -90)

    def test_source_equal_distance_tie_is_low_first_authored(self):
        bars = fixture()
        change(bars, 7, o=95, h=102, l=88, c=95)
        trade = run(bars).trades[0]
        self.assertEqual(trade["side"], "short")

    def test_20_boundary_no_new_entry(self):
        bars = fixture()
        change(bars, 20, o=110)
        self.assertEqual(len(run(bars).trades), 0)

    def test_1959_entry_then_20_exit(self):
        bars = fixture()
        after(bars, 19, 59, price=100)
        trade = run(bars).trades[0]
        self.assertEqual((trade["entry_time"], trade["exit_time"]), ("2024-01-03T16:59:00Z", "2024-01-03T17:00:00Z"))

    def test_time_and_stop_compete_at_open(self):
        bars = fixture()
        after(bars, 7, price=100)
        change(bars, 20, o=98)
        trade = run(bars).trades[0]
        self.assertEqual(trade["exit_reason"], "time")
        self.assertTrue(trade["competing_exit_orders"])
        stop = run(bars, timed_exit_priority="stop_first").trades[0]
        self.assertEqual(stop["exit_reason"], "stop")
        self.assertEqual(stop["net_dollars"], trade["net_dollars"])

    def test_cost_and_slippage_accounting(self):
        bars = fixture()
        after(bars, 7, price=100)
        change(bars, 20, o=105)
        trade = run_backtest(bars).trades[0]
        self.assertAlmostEqual(trade["entry_price"], 100.1)
        self.assertAlmostEqual(trade["exit_price"], 104.9)
        self.assertAlmostEqual(trade["gross_dollars"], 480)
        self.assertEqual(trade["commission_dollars"], 5)
        self.assertAlmostEqual(trade["net_dollars"], 475)
        self.assertAlmostEqual(trade["raw_price_dollars"], 500)
        self.assertAlmostEqual(trade["risk_initial_dollars"], 110)
        self.assertAlmostEqual(trade["net_r"], 475 / 110)

    def test_source_whole_contract_quantity_below_minimum(self):
        bars = fixture()
        for i, b in enumerate(bars):
            bars[i] = replace(b, open=b.open * 20, high=b.high * 20,
                              low=b.low * 20, close=b.close * 20)
        result = run(bars, sizing="source_account", commission_cash_per_order=0.4)
        self.assertEqual(len(result.trades), 0)
        self.assertEqual(result.days[1]["quantity_skips"], 2)
        self.assertTrue(result.days[1]["no_trade"])

    def test_quantity_floor_and_leverage_cap(self):
        self.assertEqual(quantity_at_boundary(10000, 100, 99), 1)
        self.assertEqual(quantity_at_boundary(10000, 2000, 1980), 0)
        self.assertEqual(quantity_at_boundary(10000, 100, 99, step=0.25, minimum=0.25), 1)
        self.assertEqual(quantity_at_boundary(10000, 1000, 999, max_leverage=5), 0)

    def test_source_cash_per_order_not_per_contract(self):
        bars = fixture()
        after(bars, 7, price=100)
        trade = run(bars, sizing="source_account", initial_capital=100000,
                    commission_cash_per_order=0.4).trades[0]
        self.assertEqual(trade["quantity"], 10)
        self.assertEqual(trade["commission_dollars"], 0.8)

    def test_missing_after_acceptance_censored_not_excluded(self):
        bars = fixture()
        after(bars, 7, price=100)
        bars = [b for b in bars if b.timestamp != broker(hour=8)]
        result = run(bars)
        self.assertEqual(result.trades[0]["status"], "censored")
        self.assertIsNone(result.trades[0]["net_dollars"])
        self.assertTrue(result.days[1]["eligible"])
        self.assertEqual(result.days[1]["accepted_breakouts"], 1)
        self.assertFalse(result.days[1]["no_trade"])

    def test_missing_last_entry_minute_censors_before_stop_reset(self):
        bars = fixture()
        after(bars, 7, price=110)
        bars = [b for b in bars if b.timestamp != broker(hour=7, minute=14)]
        result = run(bars)
        self.assertEqual(result.trades[0]["status"], "censored")
        self.assertIsNone(result.trades[0]["reset_stop"])
        self.assertEqual(sum(e["event"] == "stop_reset" for e in result.events), 0)

    def test_known_entry_close_reset_preserved_before_later_missing_minute(self):
        bars = fixture()
        after(bars, 7, price=110)
        bars = [b for b in bars if b.timestamp != broker(hour=7, minute=15)]
        result = run(bars)
        self.assertEqual(result.trades[0]["status"], "censored")
        self.assertEqual(result.trades[0]["reset_stop"], 108.9)
        self.assertEqual(result.trades[0]["reset_stop_active_at"], "2024-01-03T04:15:00Z")

    def test_missing_last_range_minute_does_not_submit_from_earlier_close(self):
        bars = fixture()
        after(bars, 7, price=110)
        bars = [b for b in bars if b.timestamp != broker(hour=6, minute=59)]
        result = run_backtest(bars, range_eligibility={"2024-01-03": {"eligible": False, "reason": "missing_expected_range_minutes"}})
        self.assertEqual(len(result.trades), 0)
        self.assertEqual(sum(o["action"] == "submit" for o in result.orders), 0)

    def test_missing_before_first_fill_is_unknown_not_no_trade(self):
        bars = fixture()
        bars = [b for b in bars if b.timestamp != broker(hour=8)]
        result = run(bars)
        self.assertTrue(result.days[1]["unknown_outcome"])
        self.assertFalse(result.days[1]["no_trade"])
        self.assertEqual(len(result.trades), 0)

    def test_missing_last_trading_minute_preserves_unknown_opportunity(self):
        bars = fixture()
        bars = [b for b in bars if b.timestamp != broker(hour=19, minute=59)]
        result = run(bars)
        self.assertTrue(result.days[1]["unknown_outcome"])
        self.assertFalse(result.days[1]["no_trade"])

    def test_native_pending_order_stale_missing_evening_fill(self):
        bars = fixture(end_hour=21, end_minute=14)
        bars = [b for b in bars if not broker(hour=19, minute=45) <= b.timestamp < broker(hour=21)]
        change(bars, 21, o=110)
        native = run(bars, model="native_strategy_approx")
        self.assertEqual(native.trades[0]["entry_price_raw"], 110)
        self.assertTrue(native.trades[0]["stale_entry"])
        indicator = run(bars, model="indicator_approx")
        self.assertEqual(len(indicator.trades), 0)
        validated = run(bars)
        self.assertEqual(len(validated.trades), 0)
        self.assertTrue(validated.days[1]["unknown_outcome"])

    def test_native_missing_time_decision_retains_position(self):
        bars = fixture(end_hour=21, end_minute=14)
        after(bars, 7, price=100)
        bars = [b for b in bars if not broker(hour=19, minute=45) <= b.timestamp < broker(hour=21)]
        native = run(bars, model="native_strategy_approx").trades[0]
        self.assertEqual(native["status"], "censored")
        indicator = run(bars, model="indicator_approx").trades[0]
        self.assertEqual((indicator["status"], indicator["exit_reason"]), ("completed", "indicator_missing_bar_fallback"))

    def test_scheduled_closed_gap_is_not_censor(self):
        bars = fixture()
        after(bars, 7, price=100)
        missing = broker(hour=8)
        bars = [b for b in bars if b.timestamp != missing]
        result = run_backtest(bars, EngineConfig(slippage_ticks=0, commission_per_side=0),
                              expected_minute=lambda t: t != missing and regular_gc_expected(t))
        self.assertEqual(result.trades[0]["status"], "completed")

    def test_roll_barrier_censors_before_new_price(self):
        bars = fixture()
        after(bars, 7, price=100)
        for i, b in enumerate(bars):
            if b.timestamp >= broker(hour=8):
                bars[i] = replace(b, contract="GCJ4", open=500, high=500, low=500, close=500)
        trade = run(bars).trades[0]
        self.assertEqual(trade["status"], "censored")
        self.assertEqual(trade["censor_reason"], "contract_transition")
        self.assertIsNone(trade["net_dollars"])
        self.assertEqual(trade["mfe_points"], 0)

    def test_roll_during_range_excludes(self):
        bars = fixture()
        for i, b in enumerate(bars):
            if b.timestamp >= broker(hour=3):
                bars[i] = replace(b, contract="GCJ4")
        result = run(bars)
        self.assertFalse(result.days[1]["eligible"])
        self.assertEqual(result.days[1]["exclusion_reason"], "range_contract_transition")

    def test_midday_roll_cannot_rearm_new_contract_from_old_range(self):
        bars = fixture()
        for i, b in enumerate(bars):
            if b.timestamp >= broker(hour=8):
                bars[i] = replace(b, contract="GCJ4", open=500, high=500, low=500, close=500)
        result = run(bars)
        self.assertEqual(len(result.trades), 0)
        self.assertTrue(result.days[1]["eligible"])
        self.assertTrue(result.days[1]["unknown_outcome"])
        self.assertFalse(result.days[1]["no_trade"])
        self.assertEqual(sum(o["action"] == "submit" and o["time"] >= "2024-01-03T05:00:00Z" for o in result.orders), 0)

    def test_partial_range_excluded_by_decision_available_mask(self):
        bars = fixture()
        result = run_backtest(bars, range_eligibility={"2024-01-03": {
            "eligible": False, "reason": "missing_expected_range_minutes", "expected_range_minutes": 420}})
        self.assertFalse(result.days[1]["eligible"])
        self.assertEqual(result.days[1]["expected_range_minutes"], 420)
        self.assertEqual(result.days[1]["exclusion_reason"], "missing_expected_range_minutes")

    def test_later_missing_metadata_does_not_change_range_eligibility(self):
        bars = fixture()
        result = run_backtest(bars, range_eligibility={"2024-01-03": {
            "eligible": True, "later_missing_trading_minutes": 100}})
        self.assertTrue(result.days[1]["eligible"])

    def test_partial_endpoint_retains_open_trade_no_future_reset(self):
        bars = fixture(end_hour=7, end_minute=2)
        after(bars, 7, price=110)
        trade = run(bars).trades[0]
        self.assertEqual(trade["status"], "censored")
        self.assertIsNone(trade["reset_stop"])
        self.assertIsNone(trade["exit_time"])

    def test_endpoint_pending_is_unknown_not_no_trade(self):
        result = run(fixture(end_hour=7, end_minute=14))
        self.assertTrue(result.days[1]["unknown_outcome"])
        self.assertFalse(result.days[1]["no_trade"])

    def test_no_trade_distinct_from_unknown(self):
        result = run(fixture())
        self.assertTrue(result.days[1]["no_trade"])
        self.assertFalse(result.days[1]["unknown_outcome"])

    def test_input_duplicate_and_early_availability_refused(self):
        bars = fixture()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            run(bars[:2] + [bars[1]])
        with self.assertRaisesRegex(ValueError, "available"):
            run([replace(bars[0], available_at=bars[0].timestamp)])

    def test_holiday_expected_callback_no_market_minutes(self):
        result = run_backtest(fixture(), expected_minute=lambda t: False)
        self.assertEqual(result.days[1]["observed_range_minutes"], 420)

    def test_unresolved_bounds_with_censored_branch_remain_null(self):
        bars = fixture(end_hour=7, end_minute=2)
        after(bars, 7, price=100)
        bounds = ordering_bounds(run(bars, ordering="high_first"), run(bars, ordering="low_first"))[0]
        self.assertTrue(bounds["unknown_branch"])
        self.assertIsNone(bounds["adverse_net_dollars"])


class ReportingClockTests(unittest.TestCase):
    def ny(self, day, hour, minute):
        return datetime.fromisoformat(day).replace(hour=hour, minute=minute, tzinfo=ZoneInfo("America/New_York")).astimezone(UTC)

    def test_reporting_session_boundaries(self):
        cases = [(1, 59, "asia"), (2, 0, "london"), (8, 59, "london"),
                 (9, 0, "outside_named_sessions"), (9, 29, "outside_named_sessions"),
                 (9, 30, "new_york"), (15, 59, "new_york"),
                 (16, 0, "outside_named_sessions"), (19, 59, "outside_named_sessions"), (20, 0, "asia")]
        for hour, minute, expected in cases:
            with self.subTest(hour=hour, minute=minute):
                self.assertEqual(entry_cohort(self.ny("2024-06-03", hour, minute))["entry_session"], expected)

    def test_fixed_broker_clock_does_not_follow_us_dst(self):
        winter = entry_cohort(broker("2024-01-03", 7))
        summer = entry_cohort(broker("2024-07-03", 7))
        self.assertEqual((winter["entry_hour"], summer["entry_hour"]), (23, 0))
        self.assertEqual((winter["minutes_from_trading_start"], summer["minutes_from_trading_start"]), (0, 0))

    def test_dst_fall_back_utc_identity_preserved(self):
        a = entry_cohort(datetime(2024, 11, 3, 5, 30, tzinfo=UTC))
        b = entry_cohort(datetime(2024, 11, 3, 6, 30, tzinfo=UTC))
        self.assertEqual(a["entry_session"], b["entry_session"])
        self.assertNotEqual(a["entry_time_ny"], b["entry_time_ny"])

    def test_cross_midnight_asia_retains_actual_year_and_date(self):
        cohort = entry_cohort(self.ny("2025-01-01", 0, 30))
        self.assertEqual((cohort["entry_year"], cohort["entry_date_ny"], cohort["entry_session"]), (2025, "2025-01-01", "asia"))

    def test_regular_market_break_and_weekend(self):
        self.assertFalse(regular_gc_expected(self.ny("2024-06-03", 17, 30)))
        self.assertTrue(regular_gc_expected(self.ny("2024-06-03", 18, 0)))
        self.assertFalse(regular_gc_expected(self.ny("2024-06-01", 12, 0)))
        self.assertFalse(regular_gc_expected(self.ny("2024-06-02", 17, 59)))
        self.assertTrue(regular_gc_expected(self.ny("2024-06-02", 18, 0)))


if __name__ == "__main__":
    unittest.main()
