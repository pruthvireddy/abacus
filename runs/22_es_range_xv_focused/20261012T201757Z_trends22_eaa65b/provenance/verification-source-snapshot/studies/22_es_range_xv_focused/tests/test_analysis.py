"""Known weighted distributions, denominator semantics and overlapping groups."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
import sys
import unittest


_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
from analysis import Coverage, analyze
from timeframes import load_timeframes
from trends import Trend
from test_trends import make_bar


def trend(length: int, direction: str = "bullish", *, row: int = 1,
          stamp: datetime = datetime(2024, 6, 10, 9, 30),
          session: date = date(2024, 6, 10), setting: int = 4,
          left: bool = False, right: bool = False) -> Trend:
    return Trend(setting, direction, row, row + length - 1, stamp, stamp, session,
                 length, None if left or right else length, left, right,
                 "export_end" if right else "reversal", None if right else stamp)


class AnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frames = load_timeframes(_ROOT / "study.yaml")

    def selected(self, rows: list[dict], *, setting: int = 4, year: int | None = None,
                 window: str = "all_hours", direction: str = "bullish") -> dict:
        matches = [row for row in rows if (row["setting_ticks"], row["year"], row["timeframe_id"], row["direction"])
                   == (setting, year, window, direction)]
        self.assertEqual(1, len(matches))
        return matches[0]

    def test_known_distribution_quantiles_mode_ties_histogram_and_tail(self) -> None:
        events = [trend(value, row=index * 50 + 1) for index, value in enumerate([1, 1, 2, 2, 5, 20])]
        tables = analyze(events, [4], self.frames)
        cell = self.selected(tables.summaries)
        self.assertEqual(6, cell["exact_trends"])
        self.assertAlmostEqual(31 / 6, cell["mean_candles"])
        self.assertEqual(2, cell["median_candles"])
        self.assertEqual(1, cell["mode_candles"])
        self.assertEqual("1|2", cell["tied_modes"])
        self.assertEqual(1.25, cell["q25_candles"])
        self.assertEqual(4.25, cell["q75_candles"])
        self.assertEqual(12.5, cell["p90_candles"])
        self.assertEqual(16.25, cell["p95_candles"])
        histogram = [row for row in tables.histograms if row["setting_ticks"] == 4 and row["year"] is None
                     and row["timeframe_id"] == "all_hours" and row["direction"] == "bullish"]
        self.assertEqual(6, sum(row["numerator"] for row in histogram))
        self.assertEqual(1, next(row for row in histogram if row["bin"] == "20+")["numerator"])
        tails = [row for row in tables.survival if row["year"] is None and row["timeframe_id"] == "all_hours"
                 and row["direction"] == "bullish"]
        self.assertEqual([4, 2, 2, 1, 1], [row["numerator"] for row in tails])
        self.assertAlmostEqual(4 / 6, tails[0]["probability"])

    def test_censored_counts_never_enter_estimates_or_probability_denominators(self) -> None:
        events = [trend(2), trend(100, left=True), trend(200, right=True), trend(300, left=True, right=True)]
        tables = analyze(events, [4], self.frames)
        cell = self.selected(tables.summaries)
        self.assertEqual((4, 1, 3, 2, 2), tuple(cell[key] for key in
                         ("observed_trends", "exact_trends", "censored_trends", "left_censored_trends", "right_censored_trends")))
        self.assertEqual(2, cell["mean_candles"])
        tail = next(row for row in tables.survival if row["year"] is None and row["timeframe_id"] == "all_hours"
                    and row["direction"] == "bullish" and row["minimum_candles"] == 20)
        self.assertEqual((0, 1, 0), (tail["numerator"], tail["denominator"], tail["probability"]))

    def test_all_required_empty_cells_have_null_estimates_and_zero_counts(self) -> None:
        tables = analyze([], [4, 5, 6], self.frames)
        self.assertEqual(648, len(tables.summaries))
        self.assertEqual(6480, len(tables.histograms))
        self.assertEqual(3240, len(tables.survival))
        for row in tables.summaries:
            self.assertEqual(0, row["observed_trends"])
            self.assertEqual(0, row["exact_trends"])
            self.assertIsNone(row["mean_candles"])
            self.assertIsNone(row["mode_candles"])
            self.assertEqual("", row["tied_modes"])
        for row in (*tables.histograms, *tables.survival):
            self.assertEqual(0, row["denominator"])
            self.assertIsNone(row["probability"])

    def test_first_candle_anchor_keeps_full_length_across_window_boundary(self) -> None:
        event = replace(trend(12, stamp=datetime(2024, 6, 10, 10, 29, 59)),
                        end_timestamp=datetime(2024, 6, 10, 10, 40))
        tables = analyze([event], [4], self.frames)
        self.assertEqual(12, self.selected(tables.summaries, window="ny_open")["mean_candles"])
        self.assertEqual(12, self.selected(tables.summaries, window="ny")["mean_candles"])
        self.assertEqual(0, self.selected(tables.summaries, window="ny_am")["exact_trends"])

    def test_session_year_and_overlap_at_new_year_evening(self) -> None:
        event = trend(3, stamp=datetime(2024, 12, 31, 20), session=date(2025, 1, 1))
        tables = analyze([event], [4], self.frames)
        for window in ("all_hours", "asia", "asia_open"):
            self.assertEqual(1, self.selected(tables.summaries, year=2025, window=window)["exact_trends"])
            self.assertEqual(0, self.selected(tables.summaries, year=2024, window=window)["exact_trends"])

    def test_chart_separation_and_all_direction_summary(self) -> None:
        tables = analyze([trend(2), trend(6, "bearish"), trend(100, setting=5)], [4, 5, 6], self.frames)
        self.assertEqual(4, self.selected(tables.summaries, direction="all")["mean_candles"])
        self.assertEqual(2, self.selected(tables.summaries, direction="all")["exact_trends"])
        self.assertEqual(100, self.selected(tables.summaries, setting=5)["mean_candles"])
        self.assertEqual(0, self.selected(tables.summaries, setting=6)["exact_trends"])

    def test_pooled_statistics_use_actual_events_not_mean_of_yearly_medians(self) -> None:
        events = [trend(1, session=date(2023, 6, 10))] + [trend(9) for _ in range(3)]
        tables = analyze(events, [4], self.frames)
        self.assertEqual(9, self.selected(tables.summaries)["median_candles"])
        self.assertEqual(7, self.selected(tables.summaries)["mean_candles"])

    def test_distinct_event_sessions_and_coverage_from_eligible_bars_including_doji(self) -> None:
        coverage = Coverage(self.frames)
        for row, direction in enumerate("ZUU", 1):
            coverage.observe(make_bar(row, direction))
        coverage.observe(make_bar(4, "D", eligible=False, reason="excluded_session"))
        coverage.observe(make_bar(5, "U", stamp=datetime(2024, 6, 11, 10)))
        tables = analyze([trend(2), trend(3), trend(4, session=date(2024, 6, 11))], [4], self.frames, coverage)
        cell = self.selected(tables.summaries, window="ny_open")
        self.assertEqual(2, cell["sessions_with_exact_trends"])
        self.assertEqual(2, cell["covered_sessions"])
        self.assertEqual(4, cell["eligible_bar_count"])
        self.assertEqual("2024-06-10", cell["first_session_date"])
        self.assertEqual("2024-06-11", cell["last_session_date"])
        self.assertEqual(48, len(coverage.rows([4, 5, 6], years=(year for year in [2024]))))

    def test_unassigned_hours_stay_in_overall_only(self) -> None:
        tables = analyze([trend(4, stamp=datetime(2024, 6, 10, 9, 15))], [4], self.frames)
        self.assertEqual(1, self.selected(tables.summaries)["exact_trends"])
        self.assertEqual(0, self.selected(tables.summaries, window="ny")["exact_trends"])

    def test_inconsistent_censor_flags_and_undeclared_universe_refused(self) -> None:
        invalid = (replace(trend(2), length=None), replace(trend(2), left_censored=True),
                   replace(trend(2), length=3), trend(2, setting=5), trend(2, session=date(2018, 1, 1)))
        for event in invalid:
            with self.subTest(event=event):
                with self.assertRaises(ValueError):
                    analyze([event], [4], self.frames)


if __name__ == "__main__":
    unittest.main()
