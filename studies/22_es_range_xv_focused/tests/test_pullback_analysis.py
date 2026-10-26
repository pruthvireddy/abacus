"""Causal earlier-A cohorts and known/unknown outcome denominators."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
import sys
import unittest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
from analysis import Coverage
from pullback_analysis import CONTINUATION_COLUMNS, EARLIER_LEG_BUCKETS, RETRACEMENT_COLUMNS, SUMMARY_COLUMNS, analyze_pullbacks, earlier_leg_bucket
from pullbacks import extract_pullbacks
from timeframes import load_timeframes
from test_pullbacks import known_pullback, make_pullback_bar, pullback_sequence


class PullbackAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frames = load_timeframes(_ROOT / "study.yaml")

    def select(self, rows: list[dict], *, setting: int = 4, year: int | None = None,
               window: str = "all_hours", direction: str = "bullish", bucket: str = "all",
               n: int | None = None, level: int | None = None) -> dict:
        matches = [row for row in rows if (row["setting_ticks"], row["year"], row["timeframe_id"], row["direction"], row["earlier_leg_bucket"])
                   == (setting, year, window, direction, bucket) and (n is None or row["n"] == n)
                   and (level is None or row["level_percent"] == level)]
        self.assertEqual(1, len(matches))
        return matches[0]

    def small(self, events):
        return analyze_pullbacks(events, [4], self.frames, years=[2024], horizons=[1, 2, 3], levels=[25, 50, 75, 100])

    def test_horizon_specific_known_success_failure_and_unknown(self) -> None:
        events = []
        for text in ("ZUUUDUUD", "ZUUUDUUU", "ZUUUDUD", "ZUUUDU"):
            events.append(next(event for event in extract_pullbacks(pullback_sequence(text), 4) if event.source_row == 6))
        tables = self.small(events)
        summary = self.select(tables.summaries)
        self.assertEqual((4, 2, 2, 3, 1), tuple(summary[key] for key in
                         ("event_count", "exact_followup_count", "censored_followup_count", "known_f1_count", "unknown_f1_count")))
        for n, success, failure, unknown, denominator, probability in ((1, 2, 1, 1, 3, 2/3), (2, 1, 2, 1, 3, 1/3), (3, 0, 2, 2, 2, 0)):
            row = self.select(tables.continuation, bucket="3", n=n)
            self.assertEqual((success, failure, unknown, denominator, probability), tuple(row[key] for key in
                             ("success_count", "failure_count", "unknown_count", "denominator", "probability")))

    def test_retracement_joint_and_conditional_denominators(self) -> None:
        events = [known_pullback(follower=("103", "106", "101", "105")),
                  known_pullback(follower=("102", "104", "101", "103")),
                  known_pullback(follower=("104", "106", "103.5", "105")),
                  next(extract_pullbacks(pullback_sequence("ZUUUDU"), 4))]
        row = self.select(self.small(events).retracement, level=50, bucket="3")
        self.assertEqual((4, 3, 1, 2, 2/3), tuple(row[key] for key in
                         ("event_count", "valid_f1_count", "unknown_f1_count", "touch_count", "touch_probability")))
        self.assertEqual((1, 3, 1/3), tuple(row[key] for key in
                         ("joint_beyond_close_numerator", "joint_beyond_close_denominator", "joint_beyond_close_probability")))
        self.assertEqual((1, 2, .5), tuple(row[key] for key in
                         ("conditional_beyond_close_numerator", "conditional_beyond_close_denominator", "conditional_beyond_close_probability")))
        self.assertEqual(1, row["conditional_same_colour_probability"])

    def test_unknown_start_gets_no_exact_size_bucket(self) -> None:
        event, = extract_pullbacks(pullback_sequence("UUUDUU"), 4)
        tables = self.small([event])
        self.assertEqual("unknown_start", earlier_leg_bucket(event))
        self.assertEqual(0, self.select(tables.summaries, bucket="3")["event_count"])
        row = self.select(tables.summaries, bucket="unknown_start")
        self.assertEqual((1, 0, 1), tuple(row[key] for key in ("event_count", "earlier_start_known_count", "earlier_start_unknown_count")))

    def test_cohort_endpoints_and_all_partition_conservation(self) -> None:
        events = []
        for length, bucket in ((1, "1"), (10, "10"), (11, "11-15"), (15, "11-15"),
                               (16, "16-20"), (20, "16-20"), (21, "21+"), (100, "21+")):
            event = next(event for event in extract_pullbacks(pullback_sequence("Z" + "U"*length + "DUU"), 4)
                         if event.direction == "bullish")
            self.assertEqual(bucket, earlier_leg_bucket(event))
            events.append(event)
        events.append(next(extract_pullbacks(pullback_sequence("UUUDUU"), 4)))
        tables = self.small(events)
        for direction in ("bullish", "bearish", "all"):
            overall = self.select(tables.summaries, direction=direction)
            parts = [self.select(tables.summaries, direction=direction, bucket=bucket) for bucket in EARLIER_LEG_BUCKETS[1:]]
            for key in ("event_count", "exact_followup_count", "censored_followup_count", "known_f1_count", "unknown_f1_count",
                        "earlier_start_known_count", "earlier_start_unknown_count"):
                self.assertEqual(overall[key], sum(row[key] for row in parts))
            for n in (1, 2, 3):
                overall = self.select(tables.continuation, direction=direction, n=n)
                parts = [self.select(tables.continuation, direction=direction, n=n, bucket=bucket) for bucket in EARLIER_LEG_BUCKETS[1:]]
                for key in ("event_count", "success_count", "failure_count", "unknown_count", "numerator", "denominator"):
                    self.assertEqual(overall[key], sum(row[key] for row in parts))

    def test_all_required_cells_order_schema_and_empty_nulls(self) -> None:
        tables = analyze_pullbacks([], [4, 5, 6], self.frames)
        self.assertEqual((9720, 194400, 38880), tuple(len(rows) for rows in (tables.summaries, tables.continuation, tables.retracement)))
        self.assertEqual(SUMMARY_COLUMNS, tuple(tables.summaries[0]))
        self.assertEqual(CONTINUATION_COLUMNS, tuple(tables.continuation[0]))
        self.assertEqual(RETRACEMENT_COLUMNS, tuple(tables.retracement[0]))
        self.assertEqual(list(range(1, 21)), [row["n"] for row in tables.continuation[:20]])
        self.assertEqual([25, 50, 75, 100], [row["level_percent"] for row in tables.retracement[:4]])
        self.assertTrue(all(row["event_count"] == 0 and row["probability"] is None for row in tables.continuation))

    def test_signal_completion_time_and_year_window_are_causal(self) -> None:
        event = replace(known_pullback(), start_timestamp=datetime(2024, 6, 10, 10, 29, 59),
                        available_at=datetime(2024, 6, 10, 10, 30))
        tables = self.small([event])
        self.assertEqual(0, self.select(tables.summaries, window="ny_open")["event_count"])
        self.assertEqual(1, self.select(tables.summaries, window="ny_am")["event_count"])
        event = replace(event, available_at=datetime(2024, 12, 31, 20), session_date=date(2025, 1, 1))
        tables = analyze_pullbacks([event], [4], self.frames, years=[2024, 2025], horizons=[1], levels=[50])
        for window in ("all_hours", "asia", "asia_open"):
            self.assertEqual(1, self.select(tables.summaries, year=2025, window=window, bucket="3")["event_count"])
            self.assertEqual(0, self.select(tables.summaries, year=2024, window=window, bucket="3")["event_count"])

    def test_future_can_cross_named_window_without_reassigning_event(self) -> None:
        event = replace(known_pullback(), available_at=datetime(2024, 6, 10, 10, 29, 59),
                        f1_available_at=datetime(2024, 6, 10, 10, 31))
        tables = self.small([event])
        self.assertEqual(1, self.select(tables.retracement, window="ny_open", level=50)["valid_f1_count"])
        self.assertEqual(0, self.select(tables.retracement, window="ny_am", level=50)["valid_f1_count"])

    def test_unassigned_hours_retained_all_hours(self) -> None:
        event = replace(known_pullback(), available_at=datetime(2024, 6, 10, 9, 15))
        tables = self.small([event])
        self.assertEqual(1, self.select(tables.summaries)["event_count"])
        self.assertEqual(0, self.select(tables.summaries, window="ny")["event_count"])

    def test_chart_direction_pool_and_coverage_sessions(self) -> None:
        coverage = Coverage(self.frames)
        for row in range(1, 4):
            coverage.observe(make_pullback_bar(row))
        coverage.observe(make_pullback_bar(4, stamp=datetime(2024, 6, 11, 9, 30)))
        bull, bear = known_pullback(), known_pullback(bullish=False)
        other = replace(bull, session_date=date(2024, 6, 11))
        tables = analyze_pullbacks([bull, bear, other, replace(bull, setting_ticks=5)], [4, 5, 6], self.frames,
                                  coverage, years=[2024], horizons=[1], levels=[50])
        row = self.select(tables.summaries, direction="all")
        self.assertEqual((3, 2, 4, 2), tuple(row[key] for key in ("event_count", "sessions_with_events", "eligible_bar_count", "covered_sessions")))
        self.assertEqual("setup_R_completion_timestamp_proxy", row["event_membership_anchor"])
        self.assertEqual("bar_start_timestamp", row["bar_coverage_anchor"])
        self.assertEqual(1, self.select(tables.summaries, setting=5)["event_count"])
        self.assertEqual(0, self.select(tables.summaries, setting=6)["event_count"])

    def test_horizon_and_nested_touch_count_conservation(self) -> None:
        events = list(extract_pullbacks(pullback_sequence("ZUUUDUUUDDUUDUUZUUUDU"), 4))
        tables = self.small(events)
        for row in tables.continuation:
            self.assertEqual(row["event_count"], sum(row[key] for key in ("success_count", "failure_count", "unknown_count")))
            self.assertEqual(row["denominator"], row["event_count"] - row["unknown_count"])
        touches = [self.select(tables.retracement, level=level)["touch_count"] for level in (25, 50, 75, 100)]
        self.assertEqual(sorted(touches, reverse=True), touches)
        for row in tables.retracement:
            self.assertLessEqual(row["joint_beyond_close_numerator"], row["touch_count"])

    def test_zero_touch_and_unknown_f1_rates_are_null(self) -> None:
        row = self.select(self.small([known_pullback(follower=("104", "106", "104", "105"))]).retracement, level=100)
        self.assertEqual(0, row["conditional_beyond_close_denominator"])
        self.assertIsNone(row["conditional_beyond_close_probability"])
        unknown, = extract_pullbacks(pullback_sequence("UUUDU"), 4)
        tables = self.small([unknown])
        row = self.select(tables.continuation, n=1)
        self.assertEqual((1, 0, None), (row["unknown_count"], row["denominator"], row["probability"]))

    def test_inconsistent_event_and_undeclared_universe_refused(self) -> None:
        event = known_pullback()
        invalid = (replace(event, exact_follow_count=1), replace(event, follow_count=-1),
                   replace(event, earlier_observed_length=0), replace(event, f1_open=None),
                   replace(event, f1_source_row=20), replace(event, previous_source_row=0),
                   replace(event, pullback_source_row=20), replace(event, earlier_start_source_row=0),
                   replace(event, pullback_close=event.pullback_open), replace(event, direction="bearish"),
                   replace(event, setting_ticks=5), replace(event, session_date=date(2018, 6, 10)))
        for bad in invalid:
            with self.assertRaises(ValueError):
                self.small([bad])

    def test_invalid_configuration_and_iterable_arguments(self) -> None:
        for kwargs in ({"settings": []}, {"settings": [4, 4]}, {"settings": [7]}, {"years": [2024, 2024]},
                       {"horizons": []}, {"horizons": [True]}, {"horizons": [1, 1]}, {"levels": []},
                       {"levels": [0]}, {"levels": [25, 25]}):
            with self.assertRaises(ValueError):
                analyze_pullbacks([], kwargs.get("settings", [4]), self.frames,
                                  **{key: value for key, value in kwargs.items() if key != "settings"})
        tables = analyze_pullbacks([], [4], self.frames, years=(year for year in [2024]),
                                  horizons=(n for n in [1, 2]), levels=(level for level in [50]))
        self.assertEqual((720, 1440, 720), tuple(len(rows) for rows in (tables.summaries, tables.continuation, tables.retracement)))


if __name__ == "__main__":
    unittest.main()
