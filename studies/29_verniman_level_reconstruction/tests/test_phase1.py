"""Synthetic specification tests; no market inputs or TradingView execution."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "reference_model.py"
SPEC = importlib.util.spec_from_file_location("study29_reference_model", SOURCE)
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)
Bar, CandidateEngine, Profile, Window = MODEL.Bar, MODEL.CandidateEngine, MODEL.Profile, MODEL.Window
NY, UTC, clock, local, allowed_gap = MODEL.NY, MODEL.UTC, MODEL.clock, MODEL.local, MODEL.allowed_gap


def bars(start, end, *, minutes=5, price=100.0, volume=10.0):
    """Generate independent constant-price bars, stepping in UTC elapsed time."""
    opened, terminal = start.astimezone(UTC), end.astimezone(UTC)
    while opened < terminal:
        closed = opened + timedelta(minutes=minutes)
        yield Bar(opened.astimezone(NY), closed.astimezone(NY), price + 1, price - 1, price, volume)
        opened = closed


def day_bars(day, **kwargs):
    return list(bars(local(day - timedelta(days=1), 18), local(day, 17), **kwargs))


class ProfileArithmeticTests(unittest.TestCase):
    def test_uniform_volume_is_conserved_across_touched_inclusive_bins(self):
        profile = Profile(row_size=2)
        profile.add(6, 2, 90)
        self.assertEqual(profile.bins, {1: 30, 2: 30, 3: 30})
        self.assertEqual(profile.total, sum(profile.bins.values()))
        # This is bin-edge approximation; six itself touches the upper bin.
        self.assertEqual(profile.levels(), (6, 2, 2))

    def test_lowest_poc_tie_is_preserved(self):
        profile = Profile(row_size=1, va_pct=40)
        profile.add(11, 11, 20)
        profile.add(10, 10, 20)
        self.assertEqual(profile.levels(), (10, 10, 10))

    def test_equal_neighbor_value_area_expands_up_first(self):
        profile = Profile(row_size=1, va_pct=70)
        for price, volume in ((10, 30), (9, 20), (11, 20)):
            profile.add(price, price, volume)
        self.assertEqual(profile.levels(), (11, 10, 10))

    def test_rebinning_is_not_timeframe_invariant(self):
        coarse, fine = Profile(row_size=1), Profile(row_size=1)
        coarse.add(12, 10, 100)
        fine.add(10, 10, 90)
        fine.add(12, 12, 10)
        self.assertEqual(coarse.total, fine.total)
        self.assertNotEqual(coarse.levels(), fine.levels())

    def test_reset_clears_prices_and_zero_volume_does_not_revive_them(self):
        profile = Profile()
        profile.add(101, 99, 20)
        self.assertNotEqual(profile.levels(), MODEL.EMPTY_LEVELS)
        profile.reset()
        self.assertEqual(profile.levels(), MODEL.EMPTY_LEVELS)
        profile.add(500, 500, 0)
        self.assertEqual(profile.levels(), MODEL.EMPTY_LEVELS)

    def test_missing_or_invalid_volume_invalidates_profile(self):
        for volume in (None, -1, float("nan")):
            with self.subTest(volume=volume):
                profile = Profile()
                profile.add(101, 99, 10)
                profile.add(101, 99, volume)
                self.assertTrue(profile.bad)
                self.assertEqual(profile.levels(), MODEL.EMPTY_LEVELS)

    def test_bin_limit_clears_profile_and_is_sticky_until_reset(self):
        profile = Profile(row_size=1, max_bins=3)
        profile.add(2, 0, 10)
        profile.add(3, 3, 10)
        self.assertTrue(profile.bad)
        self.assertEqual(profile.levels(), MODEL.EMPTY_LEVELS)
        profile.add(1, 1, 100)
        self.assertEqual(profile.levels(), MODEL.EMPTY_LEVELS)
        profile.reset()
        profile.add(1, 1, 100)
        self.assertEqual(profile.levels(), (1, 1, 1))

    def test_negative_prices_use_floor_not_truncation(self):
        profile = Profile(row_size=2)
        profile.add(-1, -3, 20)
        self.assertEqual(profile.bins, {-2: 10, -1: 10})
        self.assertEqual(profile.levels(), (-2, -4, -4))

    def test_hundred_percent_value_area_stops_at_available_bins(self):
        profile = Profile(row_size=1, va_pct=100)
        for price, volume in ((10, .1), (11, .2), (12, .3), (13, .7)):
            profile.add(price, price, volume)
        self.assertEqual(profile.levels(), (13, 13, 10))


class SessionIdentityTests(unittest.TestCase):
    def test_midnight_does_not_change_futures_identity(self):
        evening = clock(local(date(2026, 9, 28), 18))
        morning = clock(local(date(2026, 9, 29), 9))
        self.assertEqual(evening, morning)
        self.assertEqual(evening.trading_date, date(2026, 9, 29))

    def test_sunday_open_belongs_to_monday_and_new_week(self):
        sunday = clock(local(date(2026, 9, 27), 18))
        friday = clock(local(date(2026, 9, 25), 16))
        self.assertEqual(sunday.trading_date, date(2026, 9, 28))
        self.assertEqual(sunday.week_start, local(date(2026, 9, 27), 18))
        self.assertNotEqual(sunday.week_start, friday.week_start)

    def test_maintenance_and_weekend_bars_are_excluded(self):
        for stamp in (local(date(2026, 9, 28), 17, 30),
                      local(date(2026, 9, 25), 18),
                      local(date(2026, 9, 26), 12),
                      local(date(2026, 9, 27), 17, 55)):
            self.assertIsNone(clock(stamp))

    def test_spring_and_fall_boundaries_use_new_york_civil_time(self):
        for day, offset in ((date(2026, 3, 9), -4), (date(2026, 11, 2), -5)):
            with self.subTest(day=day):
                identity = clock(local(day - timedelta(days=1), 18))
                self.assertEqual(identity.rth_start.hour, 9)
                self.assertEqual(identity.rth_start.minute, 30)
                self.assertEqual(identity.rth_start.utcoffset(), timedelta(hours=offset))
                self.assertEqual(identity.futures_start.utcoffset(), timedelta(hours=offset))
                self.assertEqual(identity.futures_end.astimezone(UTC)
                                 - identity.futures_start.astimezone(UTC), timedelta(hours=23))

    def test_week_id_crosses_year_without_week_number_collision(self):
        identity = clock(local(date(2027, 1, 1), 8))
        self.assertEqual(identity.week_start, local(date(2026, 12, 27), 18))
        self.assertEqual(identity.week_end, local(date(2027, 1, 1), 17))


class CoverageAndStateTests(unittest.TestCase):
    DAY = date(2026, 9, 29)

    def test_no_maintenance_break_bars_needed_for_rollover(self):
        engine = CandidateEngine()
        previous = day_bars(self.DAY)
        engine.feed(previous)
        self.assertTrue(engine.previous_full.coverage)
        engine.accept(next(bars(local(self.DAY, 18), local(self.DAY, 18, 5), price=200)))
        self.assertEqual(engine.previous_full.high, 101)
        self.assertEqual(engine.futures.high, 201)
        self.assertEqual(engine.futures.start, local(self.DAY, 18))

    def test_rth_only_consecutive_days_reset_by_identity(self):
        engine = CandidateEngine()
        for day, price in ((self.DAY, 100), (self.DAY + timedelta(days=1), 200)):
            engine.feed(bars(local(day, 9, 30), local(day, 16), price=price))
            self.assertTrue(engine.completed_rth.coverage)
            self.assertFalse(engine.futures.reference().coverage)
            self.assertEqual(engine.completed_rth.close, price)
        self.assertEqual(engine.rth.start, local(self.DAY + timedelta(days=1), 9, 30))
        self.assertIsNone(engine.snapshot)
        self.assertEqual(engine.snapshot_status, "missing exact cutoff bar")

    def test_missing_off_session_bar_withholds_full_and_overnight(self):
        engine = CandidateEngine()
        retained = day_bars(self.DAY)
        del retained[60]  # Omit one otherwise normal evening bar.
        engine.feed(retained)
        self.assertFalse(engine.previous_full.coverage)
        self.assertIsNone(engine.previous_full.high)
        self.assertEqual(engine.snapshot.values[11:16], (None,) * 5)
        self.assertTrue(engine.completed_rth.coverage)

    def test_incomplete_initial_history_withholds_until_complete_next_period(self):
        engine = CandidateEngine()
        engine.feed(bars(local(self.DAY, 8), local(self.DAY, 17)))
        self.assertFalse(engine.previous_full.coverage)
        self.assertEqual(engine.snapshot.values[11:16], (None,) * 5)
        self.assertEqual(engine.week.reference(local(self.DAY, 17)).levels, MODEL.EMPTY_LEVELS)
        engine.feed(day_bars(self.DAY + timedelta(days=1), price=200))
        self.assertTrue(engine.previous_full.coverage)
        self.assertEqual(engine.previous_full.high, 201)

    def test_latest_completed_rth_and_developing_are_separate(self):
        engine = CandidateEngine()
        engine.feed(day_bars(self.DAY))
        prior = engine.completed_rth
        next_day = self.DAY + timedelta(days=1)
        engine.feed(bars(local(self.DAY, 18), local(next_day, 9, 35), price=200))
        self.assertEqual(engine.completed_rth, prior)
        self.assertEqual(engine.rth.reference(local(next_day, 9, 35)).high, 201)
        engine.feed(bars(local(next_day, 9, 35), local(next_day, 16), price=200))
        self.assertEqual(engine.completed_rth.high, 201)
        self.assertEqual(engine.completed_rth.close, 200)  # Last trade, no settlement assertion.

    def test_incomplete_rth_and_zero_volume_do_not_preserve_old_profile(self):
        engine = CandidateEngine()
        engine.feed(day_bars(self.DAY))
        next_day = self.DAY + timedelta(days=1)
        engine.feed(day_bars(next_day, price=200, volume=0))
        self.assertTrue(engine.completed_rth.coverage)
        self.assertEqual(engine.completed_rth.levels, MODEL.EMPTY_LEVELS)
        self.assertEqual(engine.completed_rth.close, 200)
        third_day = next_day + timedelta(days=1)
        retained = day_bars(third_day, price=300)
        retained = [bar for bar in retained if bar.opened != local(third_day, 12)]
        engine.feed(retained)
        self.assertFalse(engine.completed_rth.coverage)
        self.assertIsNone(engine.completed_rth.close)

    def test_week_accepts_exact_maintenance_gaps_and_requires_sunday_start(self):
        monday = date(2026, 9, 28)
        engine = CandidateEngine()
        for offset in range(5):
            engine.feed(day_bars(monday + timedelta(days=offset)))
        self.assertTrue(engine.week.reference().coverage)
        next_monday = monday + timedelta(days=7)
        engine.accept(next(iter(day_bars(next_monday))))
        self.assertTrue(engine.previous_week.coverage)
        self.assertEqual(engine.previous_week.start, local(monday - timedelta(days=1), 18))
        self.assertFalse(allowed_gap(local(monday, 16, 55), local(monday, 18)))
        self.assertFalse(allowed_gap(local(monday, 17), local(monday, 18, 5)))

    def test_week_with_missing_session_is_not_ready(self):
        monday = date(2026, 9, 28)
        engine = CandidateEngine()
        for offset in (0, 1, 3, 4):
            engine.feed(day_bars(monday + timedelta(days=offset)))
        self.assertFalse(engine.week.reference().coverage)
        self.assertEqual(engine.week.reference().levels, MODEL.EMPTY_LEVELS)

    def test_entirely_missing_weekday_cannot_reuse_older_day_references(self):
        engine = CandidateEngine()
        engine.feed(day_bars(self.DAY))  # Tuesday is complete; Wednesday is absent.
        thursday = self.DAY + timedelta(days=2)
        engine.feed(bars(local(thursday - timedelta(days=1), 18), local(thursday, 9, 25), price=200))
        self.assertIsNone(engine.previous_full)
        self.assertIsNone(engine.completed_rth)
        self.assertEqual(engine.snapshot.values[:2], (None, None))
        self.assertEqual(engine.snapshot.values[8:11], MODEL.EMPTY_LEVELS)
        self.assertEqual(engine.snapshot.values[16:19], (None,) * 3)

    def test_weekend_is_expected_but_whole_missing_week_clears_prior_week(self):
        monday = date(2026, 9, 14)
        engine = CandidateEngine()
        for offset in range(5):
            engine.feed(day_bars(monday + timedelta(days=offset)))
        # An entire intervening week is absent; older week is not "previous week".
        next_seen_monday = monday + timedelta(days=14)
        engine.accept(next(iter(day_bars(next_seen_monday))))
        self.assertIsNone(engine.previous_week)
        self.assertIsNone(engine.previous_full)
        self.assertIsNone(engine.completed_rth)

    def test_friday_to_monday_retains_friday_completed_references(self):
        friday = date(2026, 9, 25)
        monday = friday + timedelta(days=3)
        engine = CandidateEngine()
        engine.feed(day_bars(friday))
        engine.feed(bars(local(monday - timedelta(days=1), 18), local(monday, 9, 25), price=200))
        self.assertTrue(engine.previous_full.coverage)
        self.assertTrue(engine.completed_rth.coverage)
        self.assertEqual(engine.snapshot.values[:2], (101, 99))
        self.assertEqual(engine.snapshot.values[18], 100)

    def test_overnight_missing_terminal_bar_is_not_a_completed_profile(self):
        engine = CandidateEngine(cutoff=(9, 20))
        engine.feed(bars(local(self.DAY - timedelta(days=1), 18), local(self.DAY, 9, 20)))
        frozen = engine.snapshot
        self.assertEqual(frozen.values[14:16], (101, 99))
        engine.feed(bars(local(self.DAY, 9, 30), local(self.DAY, 9, 35), price=200))
        self.assertFalse(engine.overnight.reference().coverage)
        self.assertEqual(engine.overnight.reference().levels, MODEL.EMPTY_LEVELS)
        self.assertIs(engine.snapshot, frozen)  # Earlier valid cutoff remains causal.

    def test_missing_rth_terminal_bar_is_cleared_at_next_session(self):
        engine = CandidateEngine()
        previous = self.DAY - timedelta(days=1)
        engine.feed(day_bars(previous))
        current = day_bars(self.DAY)
        # This completed prefix is legitimately available while RTH develops.
        engine.feed(bar for bar in current if bar.closed <= local(self.DAY, 15, 55))
        developing = engine.rth.reference(local(self.DAY, 15, 55))
        self.assertTrue(developing.coverage)
        self.assertNotEqual(developing.levels, MODEL.EMPTY_LEVELS)
        self.assertEqual(developing.close, 100)
        # The final 15:55–16:00 bar is absent. Later full-session bars establish
        # that RTH has ended, so the earlier prefix is not a complete RTH map.
        engine.feed(bar for bar in current if bar.opened >= local(self.DAY, 16))
        incomplete = engine.rth.reference(local(self.DAY, 16))
        self.assertFalse(incomplete.coverage)
        self.assertEqual(incomplete.levels, MODEL.EMPTY_LEVELS)
        self.assertIsNone(incomplete.close)
        engine.accept(next(bars(local(self.DAY, 18), local(self.DAY, 18, 5))))
        self.assertFalse(engine.completed_rth.coverage)
        self.assertIsNone(engine.completed_rth.close)

    def test_out_of_session_bars_cannot_poison_next_sunday_week_start(self):
        sunday = date(2026, 9, 27)
        engine = CandidateEngine()
        engine.feed(bars(local(sunday, 12), local(sunday, 12, 5), price=900))
        self.assertIsNone(engine.week)
        engine.feed(bars(local(sunday, 18), local(sunday + timedelta(days=1), 9, 25)))
        self.assertTrue(engine.week.coverage)
        self.assertEqual(engine.snapshot.values[2:5], (100, 96, 96))


class SnapshotTests(unittest.TestCase):
    DAY = date(2026, 9, 30)

    def test_exact_cutoff_records_last_completed_bar_and_19_fields(self):
        engine = CandidateEngine()
        engine.feed(bars(local(self.DAY - timedelta(days=1), 18), local(self.DAY, 9, 25)))
        snapshot = engine.snapshot
        self.assertEqual(snapshot.last_open, local(self.DAY, 9, 20))
        self.assertEqual(snapshot.last_close, local(self.DAY, 9, 25))
        self.assertEqual(snapshot.cutoff, snapshot.last_close)
        self.assertEqual(len(snapshot.values), 19)
        self.assertEqual(snapshot.values[14:16], (101, 99))

    def test_unconfirmed_bar_never_supplies_later_high_or_volume(self):
        engine = CandidateEngine()
        engine.feed(bars(local(self.DAY - timedelta(days=1), 18), local(self.DAY, 9, 20)))
        cutoff_bar = next(bars(local(self.DAY, 9, 20), local(self.DAY, 9, 25), price=900))
        engine.accept(replace(cutoff_bar, confirmed=False))
        self.assertIsNone(engine.snapshot)
        self.assertEqual(engine.overnight.high, 101)
        engine.accept(cutoff_bar)
        self.assertEqual(engine.snapshot.values[14], 901)

    def test_advancing_into_rth_does_not_rewrite_frozen_map(self):
        engine = CandidateEngine()
        engine.feed(bars(local(self.DAY - timedelta(days=1), 18), local(self.DAY, 9, 25)))
        snapshot = engine.snapshot
        engine.feed(bars(local(self.DAY, 9, 25), local(self.DAY, 16), price=900))
        self.assertIs(engine.snapshot, snapshot)
        self.assertEqual(engine.snapshot.values[14:16], (101, 99))
        self.assertEqual(engine.completed_rth.close, 900)

    def test_reload_with_same_history_and_settings_is_reproducible(self):
        history = day_bars(self.DAY - timedelta(days=1))
        history += list(bars(local(self.DAY - timedelta(days=1), 18), local(self.DAY, 9, 25), price=200))
        first, reloaded = CandidateEngine(), CandidateEngine()
        first.feed(history)
        reloaded.feed(history)
        self.assertEqual(first.snapshot, reloaded.snapshot)

    def test_missing_cutoff_or_straddling_bar_never_uses_later_ohlcv(self):
        # A valid five-minute chart may use a cutoff not aligned to five minutes.
        engine = CandidateEngine(cutoff=(9, 23))
        engine.feed(bars(local(self.DAY - timedelta(days=1), 18), local(self.DAY, 9, 20)))
        engine.feed(bars(local(self.DAY, 9, 20), local(self.DAY, 9, 30), price=900))
        self.assertIsNone(engine.snapshot)
        self.assertEqual(engine.snapshot_status, "missing exact cutoff bar")

    def test_partial_history_does_not_become_a_ready_overnight_map(self):
        engine = CandidateEngine()
        engine.feed(bars(local(self.DAY, 9), local(self.DAY, 9, 25)))
        self.assertIsNotNone(engine.snapshot)
        self.assertEqual(engine.snapshot.values, (None,) * 19)

    def test_new_trading_day_clears_snapshot_without_maintenance_bars(self):
        engine = CandidateEngine()
        engine.feed(day_bars(self.DAY))
        self.assertIsNotNone(engine.snapshot)
        engine.accept(next(bars(local(self.DAY, 18), local(self.DAY, 18, 5))))
        self.assertIsNone(engine.snapshot)
        self.assertEqual(engine.snapshot_status, "waiting")

    def test_one_minute_configuration_and_preopen_cutoff_constraints(self):
        engine = CandidateEngine(minutes=1, cutoff=(9, 24))
        engine.feed(bars(local(self.DAY - timedelta(days=1), 18), local(self.DAY, 9, 24), minutes=1))
        self.assertEqual(engine.snapshot.last_open, local(self.DAY, 9, 23))
        for config in ({"minutes": 15}, {"cutoff": (9, 30)}, {"cutoff": (25, 0)}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                CandidateEngine(**config)


if __name__ == "__main__":
    unittest.main()
