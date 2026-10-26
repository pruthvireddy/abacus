from __future__ import annotations

from dataclasses import asdict
import math
from pathlib import Path
import random
import unittest

from pine_kernel import PineArray, SOURCE, load_kernel


class FibonacciMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = load_kernel()

    def event(self, direction=1, horizon=2, atr=2.0, target=1.0, stop=0.5,
              costs=0.0, identity=1, bucket=0, signal=0):
        return self.k.f_event(identity, self.k.f_swing_key(direction, 10, 20),
                              10, 20, bucket, direction, signal, 99.0, 101.0,
                              atr, horizon, target, stop, costs, 0.25)

    def step(self, e, index, o, h, l, c):
        return self.k.f_step(e, index, o, h, l, c)

    def cohorts(self):
        return self.k.Cohort(PineArray()), self.k.Cohort(PineArray())

    def completed(self, outcome, mfe, mae, net_lo, net_hi=None, direction=1,
                  identity=1, barrier_bars=1):
        e = self.event(direction=direction, identity=identity)
        e.entry, e.entryBar, e.completedBar = 100.0, 1, 2
        e.outcome = outcome
        e.windowMfePrice = mfe * e.atr0
        e.windowMaePrice = mae * e.atr0
        e.netRLo = net_lo
        e.netRHi = net_lo if net_hi is None else net_hi
        e.barsToBarrier = barrier_bars
        if outcome == self.k.TARGET:
            e.preTargetMaeLo, e.preTargetMaeHi = 0.0, mae
        if outcome == self.k.STOP:
            e.preStopMfeLo, e.preStopMfeHi = 0.0, mfe
        return e

    def test_up_levels_and_continuation_extensions(self):
        expected = {0.236: 115.28, 0.382: 112.36, 0.5: 110.0,
                    0.618: 107.64, 0.65: 107.0, 0.786: 104.28}
        for ratio, price in expected.items():
            self.assertAlmostEqual(self.k.f_level(1, 100, 120, ratio, False), price)
        self.assertAlmostEqual(self.k.f_level(1, 100, 120, 1.272, True), 125.44)
        self.assertAlmostEqual(self.k.f_level(1, 100, 120, 1.618, True), 132.36)

    def test_down_levels_mirror_up_levels(self):
        for ratio in [0, .236, .382, .5, .618, .65, .786, 1, 1.272, 1.618, 2]:
            extension = ratio > 1
            up = self.k.f_level(1, 100, 120, ratio, extension)
            down = self.k.f_level(-1, 120, 100, ratio, extension)
            self.assertAlmostEqual(up + down, 220)

    def test_equal_price_pivots_keep_distinct_bar_identities(self):
        self.assertNotEqual(self.k.f_swing_key(1, 10, 20), self.k.f_swing_key(1, 11, 21))
        self.assertNotEqual(self.k.f_swing_key(1, 10, 20), self.k.f_swing_key(-1, 10, 20))
        self.assertEqual(self.k.f_swing_key(1, 10, 20), self.k.f_swing_key(1, 10, 20))

    def test_new_ladder_is_ineligible_on_confirmation_bar(self):
        args = (False, 99, 101, 2, .15, 102, 100, 103)
        self.assertFalse(self.k.f_touch(1, 5, 5, *args))
        self.assertTrue(self.k.f_touch(1, 5, 6, *args))

    def test_touch_approach_is_strict_and_overlap_is_inclusive(self):
        self.assertFalse(self.k.f_touch(1, 0, 1, False, 100, 100, 2, .15, 100.3, 100, 101))
        self.assertTrue(self.k.f_touch(1, 0, 1, False, 100, 100, 2, .15, 101, 100.3, 101))
        self.assertFalse(self.k.f_touch(1, 0, 1, False, 100, 100, 2, .15, 101, 100.31, 101))

    def test_short_touch_requires_approach_from_below(self):
        self.assertTrue(self.k.f_touch(-1, 0, 1, False, 100, 100, 2, .15, 99, 99, 99.7))
        self.assertFalse(self.k.f_touch(-1, 0, 1, False, 100, 100, 2, .15, 101, 99, 101))

    def test_used_bucket_does_not_register_a_retest(self):
        self.assertFalse(self.k.f_touch(1, 0, 1, True, 100, 100, 2, .15, 101, 100, 101))

    def test_invalid_atr_or_missing_previous_close_has_no_signal(self):
        self.assertFalse(self.k.f_touch(1, 0, 1, False, 100, 100, 0, .15, 101, 100, 101))
        self.assertFalse(self.k.f_touch(1, 0, 1, False, 100, 100, math.nan, .15, 101, 100, 101))
        self.assertFalse(self.k.f_touch(1, 0, 1, False, 100, 100, 2, .15, math.nan, 100, 101))

    def test_pocket_is_one_zone_and_one_registration(self):
        lower, upper = self.k.f_zone(1, 100, 120, 3)
        self.assertAlmostEqual(lower, 107)
        self.assertAlmostEqual(upper, 107.64)
        used = False
        registrations = 0
        for candle in [(106.5, 109), (106.5, 109)]:
            if self.k.f_touch(1, 0, 1, used, lower, upper, 2, .15, 110, *candle):
                used = True
                registrations += 1
        self.assertEqual(registrations, 1)

    def test_signal_bar_is_excluded_even_with_large_extremes(self):
        e = self.event()
        self.step(e, 0, 100, 1000, 0, 100)
        self.assertIsNone(e.entry)
        self.assertEqual(e.windowMfePrice, 0)
        self.assertEqual(e.windowMaePrice, 0)

    def test_entry_uses_next_open_and_frozen_atr(self):
        e = self.event(costs=1)
        self.step(e, 1, 110, 111, 109.5, 110.5)
        self.assertEqual(e.entry, 110)
        self.assertEqual(e.entryBar, 1)
        self.assertEqual(e.atr0, 2)
        self.assertEqual(e.riskPts, 1)
        self.assertEqual(e.targetPrice, 112)
        self.assertEqual(e.stopPrice, 109)
        self.assertEqual(e.costR, .25)
        self.assertEqual(e.entryDistanceAtr, 4.5)

    def test_long_window_excursions_match_known_prices(self):
        e = self.event(horizon=1, target=10, stop=10)
        self.step(e, 1, 100, 103, 99.2, 101)
        self.assertAlmostEqual(e.windowMfePrice / e.atr0, 1.5)
        self.assertAlmostEqual(e.windowMaePrice / e.atr0, .4)

    def test_short_excursions_mirror_long(self):
        long = self.event(horizon=1, target=10, stop=10)
        short = self.event(direction=-1, horizon=1, target=10, stop=10)
        self.step(long, 1, 100, 104, 99, 101)
        self.step(short, 1, 100, 104, 99, 101)
        self.assertEqual(long.windowMfePrice, short.windowMaePrice)
        self.assertEqual(long.windowMaePrice, short.windowMfePrice)

    def test_target_payoff_survives_later_adverse_movement(self):
        e = self.event()
        self.step(e, 1, 100, 103, 99.5, 101)
        self.assertEqual(e.outcome, self.k.TARGET)
        self.assertIsNone(e.completedBar)
        self.step(e, 2, 101, 101.5, 97, 98)
        self.assertEqual(e.netRLo, 2)
        self.assertEqual(e.windowMaePrice, 3)
        self.assertEqual(e.barsToBarrier, 1)

    def test_stop_payoff_survives_later_favorable_movement(self):
        e = self.event()
        self.step(e, 1, 100, 101, 98, 99)
        self.step(e, 2, 99, 104, 98.5, 103)
        self.assertEqual(e.outcome, self.k.STOP)
        self.assertEqual(e.netRLo, -1)
        self.assertEqual(e.windowMfePrice, 4)

    def test_identical_window_excursions_different_first_barriers(self):
        a, b = self.event(), self.event()
        self.step(a, 1, 100, 103, 99.5, 101)
        self.step(a, 2, 101, 101.5, 98, 99)
        self.step(b, 1, 100, 101, 98, 99)
        self.step(b, 2, 99, 103, 98.5, 102)
        self.assertEqual(a.windowMfePrice, b.windowMfePrice)
        self.assertEqual(a.windowMaePrice, b.windowMaePrice)
        self.assertEqual((a.outcome, b.outcome), (self.k.TARGET, self.k.STOP))

    def test_timeout_uses_final_close_not_zero(self):
        e = self.event(horizon=1)
        self.step(e, 1, 100, 101, 99.5, 100.25)
        self.assertEqual(e.outcome, self.k.TIMEOUT)
        self.assertEqual(e.netRLo, .25)
        self.assertEqual(e.completedBar, 1)

    def test_horizon_16_includes_entry_bar_and_preserves_pending(self):
        e = self.event(horizon=16)
        for index in range(1, 16):
            self.step(e, index, 100, 101, 99.5, 100.25)
            self.assertIsNone(e.completedBar)
        self.step(e, 16, 100, 101, 99.5, 100.25)
        self.assertEqual(e.completedBar, 16)

    def test_last_bar_target_takes_precedence_over_timeout(self):
        e = self.event(horizon=16)
        for index in range(1, 16):
            self.step(e, index, 100, 101, 99.5, 100)
        self.step(e, 16, 100, 103, 99.5, 102)
        self.assertEqual(e.outcome, self.k.TARGET)
        self.assertEqual(e.barsToBarrier, 16)

    def test_both_barriers_in_one_candle_preserve_payoff_bounds(self):
        e = self.event(horizon=1, costs=.5)
        self.step(e, 1, 100, 103, 98, 101)
        self.assertEqual(e.outcome, self.k.AMBIGUOUS)
        self.assertEqual((e.netRLo, e.netRHi), (-1.125, 1.875))
        self.assertIsNone(e.preTargetMaeLo)
        self.assertIsNone(e.preStopMfeLo)

    def test_ambiguous_outcome_cannot_be_resolved_by_later_candles(self):
        e = self.event()
        self.step(e, 1, 100, 103, 98, 101)
        self.step(e, 2, 95, 104, 94, 100)
        self.assertEqual(e.outcome, self.k.AMBIGUOUS)
        self.assertEqual((e.netRLo, e.netRHi), (-1, 2))
        self.assertEqual(e.windowMaePrice, 6)

    def test_long_stop_gap_precedes_later_target_and_fills_at_open(self):
        e = self.event()
        self.step(e, 1, 100, 101, 99.5, 100)
        self.step(e, 2, 98, 103, 97, 102)
        self.assertEqual(e.outcome, self.k.STOP)
        self.assertEqual(e.netRLo, -2)
        self.assertEqual(e.preStopMfeLo, .5)
        self.assertEqual(e.preStopMfeHi, .5)

    def test_short_stop_gap_is_symmetric(self):
        e = self.event(direction=-1)
        self.step(e, 1, 100, 100.5, 99, 100)
        self.step(e, 2, 103, 104, 96, 97)
        self.assertEqual(e.outcome, self.k.STOP)
        self.assertEqual(e.netRLo, -3)
        self.assertEqual(e.preStopMfeLo, .5)
        self.assertEqual(e.preStopMfeHi, .5)

    def test_favorable_gap_uses_target_fill_and_exact_preexit_excursion(self):
        e = self.event()
        self.step(e, 1, 100, 101, 99.5, 100)
        self.step(e, 2, 104, 105, 98, 99)
        self.assertEqual(e.outcome, self.k.TARGET)
        self.assertEqual(e.netRLo, 2)
        self.assertEqual((e.preTargetMaeLo, e.preTargetMaeHi), (.25, .25))
        self.assertEqual(e.windowMaePrice, 2)

    def test_pre_target_bounds_include_known_open_and_uncertain_low(self):
        e = self.event()
        self.step(e, 1, 100, 101, 99.6, 100)
        self.step(e, 2, 99.5, 103, 99.25, 102)
        self.assertEqual(e.outcome, self.k.TARGET)
        self.assertAlmostEqual(e.preTargetMaeLo, .25)
        self.assertAlmostEqual(e.preTargetMaeHi, .375)

    def test_pre_stop_bounds_include_known_open_and_uncertain_high(self):
        e = self.event()
        self.step(e, 1, 100, 100.5, 99.5, 100)
        self.step(e, 2, 101, 101.5, 98.5, 99)
        self.assertEqual(e.outcome, self.k.STOP)
        self.assertEqual((e.preStopMfeLo, e.preStopMfeHi), (.5, .75))

    def test_pre_exit_bounds_cover_both_possible_ohlc_orderings(self):
        target = self.event(horizon=1)
        self.step(target, 1, 100, 103, 99.5, 100.5)
        for realized_mae_at_target in [0, .25]:
            self.assertLessEqual(target.preTargetMaeLo, realized_mae_at_target)
            self.assertGreaterEqual(target.preTargetMaeHi, realized_mae_at_target)
        stop = self.event(horizon=1)
        self.step(stop, 1, 100, 100.5, 98, 99.5)
        for realized_mfe_at_stop in [0, .25]:
            self.assertLessEqual(stop.preStopMfeLo, realized_mfe_at_stop)
            self.assertGreaterEqual(stop.preStopMfeHi, realized_mfe_at_stop)

    def test_completed_event_is_immutable_to_later_steps(self):
        e = self.event(horizon=1)
        self.step(e, 1, 100, 101, 99.5, 100.25)
        before = asdict(e)
        self.step(e, 2, 80, 120, 70, 100)
        self.assertEqual(asdict(e), before)

    def test_another_swing_does_not_change_existing_event(self):
        old = self.event()
        self.step(old, 1, 100, 101, 99.5, 100)
        new = self.event(direction=-1, atr=10, identity=2)
        new.zoneLo, new.zoneHi = 140, 150
        self.step(old, 2, 100, 103, 99.5, 102)
        self.assertEqual((old.swingId, old.atr0, old.zoneLo, old.zoneHi, old.entry), (1, 2, 99, 101, 100))
        self.assertEqual(old.outcome, self.k.TARGET)

    def test_percentiles_interpolate_and_do_not_mutate_input(self):
        values = PineArray([10.0, 0.0])
        self.assertEqual(self.k.f_percentile(values, .5), 5)
        self.assertEqual(self.k.f_percentile(values, .9), 9)
        self.assertEqual(values, [10, 0])
        self.assertEqual(self.k.f_percentile(PineArray([3]), .9), 3)

    def test_empty_is_undefined_and_zero_is_valid(self):
        self.assertIsNone(self.k.f_percentile(PineArray(), .5))
        self.assertEqual(self.k.f_percentile(PineArray([0.0]), .5), 0)
        longs, shorts = self.cohorts()
        empty = self.k.f_summary(longs, shorts, "Combined")
        self.assertEqual(empty.n, 0)
        self.assertIsNone(empty.probabilityLo)
        self.assertIsNone(empty.meanNetRLo)

    def test_wilson_zero_all_and_no_observations(self):
        low, high = self.k.f_wilson(0, 10)
        self.assertAlmostEqual(low, 0)
        self.assertAlmostEqual(high, .2775327998628892)
        low, high = self.k.f_wilson(10, 10)
        self.assertAlmostEqual(low, .7224672001371107)
        self.assertAlmostEqual(high, 1)
        self.assertEqual(self.k.f_wilson(0, 0), [None, None])

    def test_ring_eviction_keeps_latest_completed_sample_for_all_metrics(self):
        longs, shorts = self.cohorts()
        for identity in range(1, 6):
            row = self.completed(self.k.TIMEOUT, identity, identity, identity, identity=identity)
            self.k.f_remember(longs, row, 2)
        summary = self.k.f_summary(longs, shorts, "Long")
        self.assertEqual(sorted(e.swingId for e in longs.rows), [4, 5])
        self.assertEqual(summary.n, 2)
        self.assertEqual(summary.swings, 2)
        self.assertEqual(summary.medianMfe, 4.5)
        self.assertEqual(summary.medianMae, 4.5)
        self.assertEqual(summary.meanNetRLo, 4.5)
        self.assertEqual(summary.probabilityLo, 0)

    def test_combined_pools_records_instead_of_averaging_group_medians(self):
        longs, shorts = self.cohorts()
        self.k.f_remember(longs, self.completed(self.k.TARGET, 1, .1, 2, identity=1), 10)
        self.k.f_remember(longs, self.completed(self.k.STOP, 9, .9, -1, identity=2), 10)
        self.k.f_remember(shorts, self.completed(self.k.TIMEOUT, 2, .2, .5, direction=-1, identity=3), 10)
        combined = self.k.f_summary(longs, shorts, "Combined")
        self.assertEqual(combined.n, 3)
        self.assertEqual(combined.medianMfe, 2)
        self.assertEqual(combined.swings, 3)
        self.assertAlmostEqual(combined.meanNetRLo, .5)
        self.assertAlmostEqual(combined.probabilityLo, 1 / 3)
        self.assertEqual(self.k.f_summary(longs, shorts, "Long").n, 2)
        self.assertEqual(self.k.f_summary(longs, shorts, "Short").n, 1)

    def test_ambiguity_probability_and_payoff_use_all_completed_rows(self):
        longs, shorts = self.cohorts()
        for row in [
            self.completed(self.k.TARGET, 2, .1, 2, identity=1),
            self.completed(self.k.TIMEOUT, .2, .2, 0, identity=2),
            self.completed(self.k.AMBIGUOUS, 2, 1, -1, 2, identity=3),
        ]:
            self.k.f_remember(longs, row, 10)
        summary = self.k.f_summary(longs, shorts, "Long")
        self.assertAlmostEqual(summary.probabilityLo, 1 / 3)
        self.assertAlmostEqual(summary.probabilityHi, 2 / 3)
        self.assertAlmostEqual(summary.meanNetRLo, 1 / 3)
        self.assertAlmostEqual(summary.meanNetRHi, 4 / 3)
        self.assertIsNone(summary.wilsonLo)
        self.assertEqual(summary.wins + summary.stops + summary.timeouts + summary.ambiguous, summary.n)

    def test_target_timing_uses_only_target_first_events(self):
        longs, shorts = self.cohorts()
        for row in [
            self.completed(self.k.TARGET, 2, .1, 2, identity=1, barrier_bars=1),
            self.completed(self.k.TARGET, 2, .1, 2, identity=2, barrier_bars=3),
            self.completed(self.k.STOP, .2, .5, -1, identity=3, barrier_bars=12),
        ]:
            self.k.f_remember(longs, row, 10)
        summary = self.k.f_summary(longs, shorts, "Long")
        self.assertEqual(summary.medianTargetBars, 2)
        self.assertIsNotNone(summary.wilsonLo)

    def test_duplicate_swing_ids_are_counted_once_in_diagnostic(self):
        longs, shorts = self.cohorts()
        for identity in [1, 1, 2]:
            self.k.f_remember(longs, self.completed(self.k.TIMEOUT, 0, 0, 0, identity=identity), 10)
        summary = self.k.f_summary(longs, shorts, "Long")
        self.assertEqual((summary.n, summary.swings), (3, 2))

    def test_deterministic_random_paths_preserve_mirror_symmetry(self):
        rng = random.Random(20261006)
        for _ in range(100):
            long = self.event(horizon=10, costs=1)
            short = self.event(direction=-1, horizon=10, costs=1)
            close = 100
            for index in range(1, 11):
                o = 100 if index == 1 else close + rng.uniform(-1.5, 1.5)
                h = o + rng.uniform(0, 2)
                l = o - rng.uniform(0, 2)
                close = rng.uniform(l, h)
                self.step(long, index, o, h, l, close)
                self.step(short, index, 200 - o, 200 - l, 200 - h, 200 - close)
            self.assertEqual(long.outcome, short.outcome)
            self.assertAlmostEqual(long.windowMfePrice, short.windowMfePrice)
            self.assertAlmostEqual(long.windowMaePrice, short.windowMaePrice)
            self.assertAlmostEqual(long.netRLo, short.netRLo)
            self.assertAlmostEqual(long.netRHi, short.netRHi)

    def test_chart_integration_orders_old_events_touches_then_pivots(self):
        source = SOURCE.read_text()
        step_at = source.index("int changed = f_step(e, bar_index")
        touch_at = source.index("if f_touch(legDir, legConfirmedBar")
        pivot_at = source.index("if not na(ph)", touch_at)
        self.assertLess(step_at, touch_at)
        self.assertLess(touch_at, pivot_at)
        self.assertIn("touched.set(bucket, true)", source)
        self.assertIn("touched.fill(false)", source)
        self.assertIn("if not na(e.completedBar)", source)
        self.assertNotIn("high > legB", source)
        self.assertNotIn("low < legB", source)
        self.assertNotIn("strategy(", source)
        self.assertNotIn("request.security", source)

    def test_embedded_self_checks_use_production_helpers_and_pass(self):
        self.assertTrue(self.k.f_self_checks())


if __name__ == "__main__":
    unittest.main()
