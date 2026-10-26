"""Known grouped continuation denominators, retracement rates and empty cells."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
import unittest


_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
from analysis import Coverage
from reversal_analysis import CONTINUATION_COLUMNS, PRIOR_LEG_BUCKETS, RETRACEMENT_COLUMNS, SUMMARY_COLUMNS, analyze_reversals, prior_leg_bucket
from reversals import extract_reversals
from timeframes import load_timeframes
from test_reversals import known_reversal, make_reversal_bar, reversal_sequence


class ReversalAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frames = load_timeframes(_ROOT / "study.yaml")

    def select(self, rows: list[dict], *, setting: int = 4, year: int | None = None,
               window: str = "all_hours", direction: str = "bullish", bucket: str = "all", n: int | None = None,
               level: int | None = None) -> dict:
        matches = [row for row in rows if (row["setting_ticks"], row["year"], row["timeframe_id"], row["direction"])
                   == (setting, year, window, direction) and row["prior_leg_bucket"] == bucket and (n is None or row["n"] == n)
                   and (level is None or row["level_percent"] == level)]
        self.assertEqual(1, len(matches))
        return matches[0]

    def test_short_horizon_success_from_censored_event_remains_in_own_denominator(self) -> None:
        first = list(extract_reversals(reversal_sequence("DUUD"), 4))[0]  # exact1
        second = list(extract_reversals(reversal_sequence("DUUU"), 4))[0]  # censored2
        third = list(extract_reversals(reversal_sequence("DUD"), 4))[0]  # exact0
        fourth = list(extract_reversals(reversal_sequence("DU"), 4))[0]  # censored0
        tables = analyze_reversals([first, second, third, fourth], [4], self.frames)
        summary = self.select(tables.summaries)
        self.assertEqual((4, 2, 2, 3, 1), tuple(summary[key] for key in
                         ("event_count", "exact_followup_count", "censored_followup_count", "known_f1_count", "unknown_f1_count")))
        expected = ((1, 2, 1, 1, 3, 2 / 3), (2, 1, 2, 1, 3, 1 / 3), (3, 0, 2, 2, 2, 0))
        for n, success, failure, unknown, denominator, probability in expected:
            row = self.select(tables.continuation, n=n)
            self.assertEqual((4, success, failure, unknown, success, denominator), tuple(row[key] for key in
                             ("event_count", "success_count", "failure_count", "unknown_count", "numerator", "denominator")))
            self.assertEqual(probability, row["probability"])

    def test_joint_and_conditional_retracement_denominators_differ_and_unknown_is_excluded(self) -> None:
        touched_favorable = known_reversal(follower=("103", "106", "101", "105"))
        touched_not_favorable = known_reversal(follower=("102", "104", "101", "103"))
        untouch_favorable = known_reversal(follower=("104", "106", "103.5", "105"))
        unknown = list(extract_reversals(reversal_sequence("DU"), 4))[0]
        tables = analyze_reversals([touched_favorable, touched_not_favorable, untouch_favorable, unknown], [4], self.frames)
        row = self.select(tables.retracement, level=50)
        self.assertEqual((4, 3, 1, 2), tuple(row[key] for key in ("event_count", "valid_f1_count", "unknown_f1_count", "touch_count")))
        self.assertEqual((2, 3, 2 / 3), tuple(row[key] for key in ("touch_numerator", "touch_denominator", "touch_probability")))
        self.assertEqual((1, 3, 1 / 3), tuple(row[key] for key in ("joint_beyond_close_numerator", "joint_beyond_close_denominator", "joint_beyond_close_probability")))
        self.assertEqual((1, 2, .5), tuple(row[key] for key in ("conditional_beyond_close_numerator", "conditional_beyond_close_denominator", "conditional_beyond_close_probability")))
        self.assertEqual((2, 3, 2 / 3), tuple(row[key] for key in ("joint_same_colour_numerator", "joint_same_colour_denominator", "joint_same_colour_probability")))
        self.assertEqual((2, 2, 1), tuple(row[key] for key in ("conditional_same_colour_numerator", "conditional_same_colour_denominator", "conditional_same_colour_probability")))

    def test_zero_touch_denominator_has_null_conditional_probability(self) -> None:
        tables = analyze_reversals([known_reversal(follower=("104", "106", "104", "105"))], [4], self.frames)
        row = self.select(tables.retracement, level=100)
        self.assertEqual(0, row["conditional_beyond_close_denominator"])
        self.assertIsNone(row["conditional_beyond_close_probability"])
        self.assertEqual(0, row["joint_beyond_close_probability"])

    def test_unknown_only_cells_have_null_rates_and_positive_unknown_counts(self) -> None:
        event, = extract_reversals(reversal_sequence("DU"), 4)
        tables = analyze_reversals([event], [4], self.frames)
        continuation = self.select(tables.continuation, n=1)
        retrace = self.select(tables.retracement, level=25)
        self.assertEqual((1, 0, 1, None), tuple(continuation[key] for key in ("event_count", "denominator", "unknown_count", "probability")))
        self.assertEqual((1, 0, 1, None), tuple(retrace[key] for key in ("event_count", "valid_f1_count", "unknown_f1_count", "touch_probability")))

    def test_all_required_empty_rows_are_present_in_declared_order_and_schema(self) -> None:
        tables = analyze_reversals([], [4, 5, 6], self.frames)
        self.assertEqual((9720, 194400, 38880), (len(tables.summaries), len(tables.continuation), len(tables.retracement)))
        self.assertEqual(tuple(SUMMARY_COLUMNS), tuple(tables.summaries[0]))
        self.assertEqual(tuple(CONTINUATION_COLUMNS), tuple(tables.continuation[0]))
        self.assertEqual(tuple(RETRACEMENT_COLUMNS), tuple(tables.retracement[0]))
        self.assertEqual([1, 2, 3, 4, 5], [row["n"] for row in tables.continuation[:5]])
        self.assertEqual([25, 50, 75, 100], [row["level_percent"] for row in tables.retracement[:4]])
        for row in tables.continuation:
            self.assertEqual(0, row["event_count"])
            self.assertIsNone(row["probability"])
        for row in tables.retracement:
            self.assertEqual(0, row["valid_f1_count"])
            self.assertIsNone(row["joint_beyond_close_probability"])

    def test_event_completion_anchor_can_differ_from_R_opening_window(self) -> None:
        event = replace(known_reversal(), start_timestamp=datetime(2024, 6, 10, 10, 29, 59),
                        available_at=datetime(2024, 6, 10, 10, 30),
                        f1_start_timestamp=datetime(2024, 6, 10, 10, 30),
                        f1_available_at=datetime(2024, 6, 10, 10, 31))
        tables = analyze_reversals([event], [4], self.frames)
        self.assertEqual(0, self.select(tables.summaries, window="ny_open")["event_count"])
        self.assertEqual(1, self.select(tables.summaries, window="ny_am")["event_count"])
        self.assertEqual(1, self.select(tables.summaries, window="ny")["event_count"])

    def test_future_outcome_can_cross_window_while_event_stays_in_R_completion_window(self) -> None:
        event = replace(known_reversal(), available_at=datetime(2024, 6, 10, 10, 29, 59),
                        f1_start_timestamp=datetime(2024, 6, 10, 10, 29, 59),
                        f1_available_at=datetime(2024, 6, 10, 10, 31))
        tables = analyze_reversals([event], [4], self.frames)
        self.assertEqual(1, self.select(tables.retracement, window="ny_open", level=50)["valid_f1_count"])
        self.assertEqual(0, self.select(tables.retracement, window="ny_am", level=50)["valid_f1_count"])

    def test_session_year_at_December_evening_and_overlapping_windows(self) -> None:
        event = replace(known_reversal(), available_at=datetime(2024, 12, 31, 20), session_date=date(2025, 1, 1))
        tables = analyze_reversals([event], [4], self.frames)
        for window in ("all_hours", "asia", "asia_open"):
            self.assertEqual(1, self.select(tables.summaries, year=2025, window=window)["event_count"])
            self.assertEqual(0, self.select(tables.summaries, year=2024, window=window)["event_count"])

    def test_charts_and_directions_are_separate_and_all_is_actual_pooled_events(self) -> None:
        bull = known_reversal()
        bear = known_reversal(bullish=False)
        unknown = replace(list(extract_reversals(reversal_sequence("DU"), 4))[0], setting_ticks=5)
        tables = analyze_reversals([bull, bear, unknown], [4, 5, 6], self.frames)
        self.assertEqual(2, self.select(tables.summaries, direction="all")["event_count"])
        self.assertEqual(1, self.select(tables.summaries, setting=5, direction="all")["event_count"])
        self.assertEqual(0, self.select(tables.summaries, setting=6, direction="all")["event_count"])
        self.assertEqual(2, self.select(tables.continuation, n=1, direction="all")["numerator"])

    def test_overall_rate_uses_actual_observations_instead_of_year_rate_average(self) -> None:
        yes = known_reversal()
        no = list(extract_reversals(reversal_sequence("DUD"), 4))[0]
        events = [replace(yes, session_date=date(2023, 6, 10)), no, no, no]
        tables = analyze_reversals(events, [4], self.frames)
        self.assertEqual(.25, self.select(tables.continuation, n=1)["probability"])
        self.assertEqual(1, self.select(tables.continuation, n=1, year=2023)["probability"])
        self.assertEqual(0, self.select(tables.continuation, n=1, year=2024)["probability"])

    def test_distinct_sessions_and_opening_time_bar_coverage_are_explicit(self) -> None:
        coverage = Coverage(self.frames)
        for row in (1, 2, 3):
            coverage.observe(make_reversal_bar(row))
        coverage.observe(make_reversal_bar(4, stamp=datetime(2024, 6, 11, 9, 30)))
        coverage.observe(make_reversal_bar(5, eligible=False))
        event = known_reversal()
        other = replace(event, session_date=date(2024, 6, 11))
        tables = analyze_reversals([event, event, other], [4], self.frames, coverage)
        summary = self.select(tables.summaries)
        self.assertEqual((3, 2, 2, 4, 2), tuple(summary[key] for key in
                         ("event_count", "sessions_with_events", "sessions_with_known_f1", "eligible_bar_count", "covered_sessions")))
        self.assertEqual("bar_start_timestamp", summary["bar_coverage_anchor"])
        self.assertEqual("reversal_completion_timestamp_proxy", summary["event_membership_anchor"])
        self.assertEqual(2, self.select(tables.continuation, n=1)["sessions_with_known_outcome"])

    def test_all_horizon_counts_conserve_events_and_nested_touch_counts_monotone(self) -> None:
        events = list(extract_reversals(reversal_sequence("DUUUDDUUDZDU"), 4))
        tables = analyze_reversals(events, [4], self.frames)
        for row in tables.continuation:
            self.assertEqual(row["event_count"], row["success_count"] + row["failure_count"] + row["unknown_count"])
            self.assertEqual(row["numerator"], row["success_count"])
            self.assertEqual(row["denominator"], row["event_count"] - row["unknown_count"])
        selected = [self.select(tables.retracement, level=level) for level in (25, 50, 75, 100)]
        counts = [row["touch_count"] for row in selected]
        self.assertEqual(sorted(counts, reverse=True), counts)
        for row in selected:
            self.assertLessEqual(row["joint_beyond_close_numerator"], row["touch_count"])

    def test_three_bear_leg_then_bull_R_and_two_followers_uses_exact_prior_three_cohort(self) -> None:
        events = list(extract_reversals(reversal_sequence("UDDDUUUD"), 4))
        event = next(row for row in events if row.source_row == 5)
        self.assertEqual((3, 2, "bullish"), (event.prior_exact_length, event.exact_follow_count, event.direction))
        tables = analyze_reversals([event], [4], self.frames)
        self.assertEqual(1, self.select(tables.summaries, bucket="3")["event_count"])
        self.assertEqual(0, self.select(tables.summaries, bucket="unknown_start")["event_count"])
        self.assertEqual(1, self.select(tables.continuation, bucket="3", n=2)["numerator"])
        self.assertEqual(0, self.select(tables.continuation, bucket="3", n=3)["numerator"])
        self.assertEqual(1, self.select(tables.retracement, bucket="3", level=50)["valid_f1_count"])

    def test_unknown_start_never_uses_observed_preceding_length_as_exact_bucket(self) -> None:
        event, = extract_reversals(reversal_sequence("DDDU"), 4)
        self.assertEqual(3, event.prior_observed_length)
        tables = analyze_reversals([event], [4], self.frames)
        self.assertEqual(0, self.select(tables.summaries, bucket="3")["event_count"])
        self.assertEqual(1, self.select(tables.summaries, bucket="unknown_start")["event_count"])
        self.assertEqual(1, self.select(tables.summaries)["event_count"])

    def test_prior_bucket_endpoints_and_overall_partition_conservation(self) -> None:
        template = known_reversal()
        expected = ((1, "1"), (10, "10"), (11, "11-15"), (15, "11-15"),
                    (16, "16-20"), (20, "16-20"), (21, "21+"), (100, "21+"))
        events = []
        for size, bucket in expected:
            event = replace(template, prior_start_known=True, prior_observed_length=size)
            self.assertEqual(bucket, prior_leg_bucket(event))
            events.append(event)
        events.append(template)
        tables = analyze_reversals(events, [4], self.frames, years=[2024], horizons=[1, 2], levels=[50])
        for direction in ("bullish", "bearish", "all"):
            overall = self.select(tables.summaries, direction=direction)
            parts = [self.select(tables.summaries, direction=direction, bucket=bucket)
                     for bucket in PRIOR_LEG_BUCKETS[1:]]
            for column in ("event_count", "exact_followup_count", "censored_followup_count", "known_f1_count",
                           "unknown_f1_count", "prior_start_known_count", "prior_start_unknown_count"):
                self.assertEqual(overall[column], sum(row[column] for row in parts))
            for n in (1, 2):
                all_row = self.select(tables.continuation, direction=direction, n=n)
                part_rows = [self.select(tables.continuation, direction=direction, n=n, bucket=bucket)
                             for bucket in PRIOR_LEG_BUCKETS[1:]]
                for column in ("event_count", "success_count", "failure_count", "unknown_count", "numerator", "denominator"):
                    self.assertEqual(all_row[column], sum(row[column] for row in part_rows))

    def test_prior_cohorts_keep_year_window_chart_and_direction_filters(self) -> None:
        event = replace(known_reversal(), prior_start_known=True, prior_observed_length=3,
                        available_at=datetime(2024, 12, 31, 20), session_date=date(2025, 1, 1))
        tables = analyze_reversals([event], [4, 5], self.frames, years=[2024, 2025], horizons=[1, 2], levels=[50])
        for window in ("all_hours", "asia", "asia_open"):
            self.assertEqual(1, self.select(tables.summaries, year=2025, window=window, bucket="3")["event_count"])
            self.assertEqual(0, self.select(tables.summaries, year=2024, window=window, bucket="3")["event_count"])
            self.assertEqual(0, self.select(tables.summaries, setting=5, year=2025, window=window, bucket="3")["event_count"])

    def test_unassigned_event_hours_remain_in_all_hours(self) -> None:
        event = replace(known_reversal(), available_at=datetime(2024, 6, 10, 9, 15))
        tables = analyze_reversals([event], [4], self.frames)
        self.assertEqual(1, self.select(tables.summaries)["event_count"])
        self.assertEqual(0, self.select(tables.summaries, window="ny")["event_count"])

    def test_inconsistent_event_or_undeclared_universe_refused(self) -> None:
        event = known_reversal()
        invalid = (replace(event, exact_follow_count=1), replace(event, follow_count=-1),
                   replace(event, prior_observed_length=0), replace(event, f1_open=None),
                   replace(event, f1_source_row=5), replace(event, previous_source_row=0),
                   replace(event, direction="bearish"), replace(event, setting_ticks=5),
                   replace(event, session_date=date(2018, 6, 10)))
        for bad in invalid:
            with self.subTest(event=bad), self.assertRaises(ValueError):
                analyze_reversals([bad], [4], self.frames)

    def test_invalid_aggregation_config_refused_and_iterable_arguments_preserved(self) -> None:
        invalid = ({"settings": []}, {"settings": [4, 4]}, {"settings": [7]},
                   {"years": [2024, 2024]}, {"horizons": []}, {"horizons": [True]},
                   {"horizons": [1, 1]}, {"levels": []}, {"levels": [0]}, {"levels": [25, 25]})
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                analyze_reversals([], kwargs.get("settings", [4]), self.frames,
                                  **{key: value for key, value in kwargs.items() if key != "settings"})
        tables = analyze_reversals([], [4], self.frames, years=(year for year in [2024]),
                                   horizons=(n for n in [1, 2]), levels=(level for level in [50]))
        self.assertEqual((720, 1440, 720), (len(tables.summaries), len(tables.continuation), len(tables.retracement)))


if __name__ == "__main__":
    unittest.main()
