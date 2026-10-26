"""Known examples for the independent Study 22 verifier."""

from datetime import date, datetime, timedelta
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


AUDIT_PATH = Path(__file__).resolve().parents[1] / "audit.py"
spec = importlib.util.spec_from_file_location("study22_independent_audit", AUDIT_PATH)
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


def bars(signs, *, session="2025-01-02", start="2025-01-02 09:29:59"):
    initial = datetime.fromisoformat(start)
    result = []
    for index, sign in enumerate(signs):
        timestamp = initial + timedelta(seconds=index)
        result.append(audit.ObservedBar(
            index + 1, timestamp, date.fromisoformat(session), sign,
            timestamp + timedelta(seconds=1), "next_bar_start_proxy",
        ))
    return result


class RunAuditKnownExamples(unittest.TestCase):
    def test_initial_and_terminal_censors_are_not_exact_lengths(self):
        observed = bars(["bullish", "bullish", "bearish", "bearish", "bullish", None, "bearish", "bearish"])
        result = list(audit.reconstruct_runs(observed, 4, date(2026, 9, 24)))
        self.assertEqual([item["observed_length"] for item in result], [2, 2, 1, 2])
        self.assertEqual([item["length"] for item in result], [None, 2, 1, None])
        self.assertEqual([item["end_reason"] for item in result], ["reversal", "reversal", "doji", "export_end"])
        self.assertEqual(sum(item["observed_length"] for item in result), 7)

    def test_single_segment_has_both_censors(self):
        result = list(audit.reconstruct_runs(bars(["bullish"] * 3), 5, date(2026, 9, 24)))
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["length"])
        self.assertTrue(result[0]["left_censored"])
        self.assertTrue(result[0]["right_censored"])

    def test_initial_doji_establishes_known_start(self):
        result = list(audit.reconstruct_runs(bars([None, "bullish", "bullish", None]), 6, date(2026, 9, 24)))
        self.assertEqual(result[0]["length"], 2)
        self.assertFalse(result[0]["left_censored"])
        self.assertFalse(result[0]["right_censored"])

    def test_completion_barrier_cannot_stitch_equal_signs(self):
        observed = bars([None, "bullish", "bullish", "bullish", "bullish", "bearish"])
        barrier = observed[2]
        observed[2] = audit.ObservedBar(barrier.row, barrier.start, barrier.session, barrier.direction, None, "unknown_completion")
        result = list(audit.reconstruct_runs(observed, 4, date(2026, 9, 24)))
        self.assertEqual([item["observed_length"] for item in result], [1, 2, 1])
        self.assertEqual([item["length"] for item in result], [None, None, None])
        self.assertTrue(result[0]["right_censored"])
        self.assertTrue(result[1]["left_censored"])
        self.assertEqual(sum(item["observed_length"] for item in result), 4)

    def test_session_boundary_breaks_and_resets_known_start(self):
        observed = bars([None, "bullish"])
        observed.extend([
            audit.ObservedBar(3, datetime(2025, 1, 2, 18), date(2025, 1, 3), "bullish", datetime(2025, 1, 2, 18, 1), "next_bar_start_proxy"),
            audit.ObservedBar(4, datetime(2025, 1, 2, 18, 1), date(2025, 1, 3), "bearish", datetime(2025, 1, 2, 18, 2), "next_bar_start_proxy"),
        ])
        result = list(audit.reconstruct_runs(observed, 4, date(2026, 9, 24)))
        self.assertEqual([item["observed_length"] for item in result], [1, 1, 1])
        self.assertEqual(result[0]["end_reason"], "session_boundary")
        self.assertTrue(result[1]["left_censored"])

    def test_partial_final_session_is_excluded(self):
        observed = bars([None, "bullish", "bearish"], session="2026-09-24", start="2026-09-24 09:30:00")
        self.assertEqual(list(audit.reconstruct_runs(observed, 4, date(2026, 9, 24))), [])

    def test_same_second_original_rows_are_preserved(self):
        observed = [
            audit.ObservedBar(index + 1, datetime(2025, 1, 2, 9, 30), date(2025, 1, 2), direction, datetime(2025, 1, 2, 9, 30), "next_bar_start_same_second")
            for index, direction in enumerate([None, "bullish", "bullish", "bearish"])
        ]
        result = list(audit.reconstruct_runs(observed, 5, date(2026, 9, 24)))
        self.assertEqual(result[0]["length"], 2)
        self.assertEqual((result[0]["start_source_row"], result[0]["end_source_row"]), (2, 3))

    def test_completion_lookahead_requires_exact_next_source_row(self):
        observed = bars(["bullish", "bearish"])
        terminal = observed[-1]
        observed[-1] = audit.ObservedBar(terminal.row, terminal.start, terminal.session, terminal.direction, None, "unavailable_export_end")
        self.assertEqual(list(audit.validate_completion(observed)), observed)
        observed[0] = audit.ObservedBar(1, observed[0].start, observed[0].session, "bullish", observed[0].start, "next_bar_start_same_second")
        with self.assertRaisesRegex(ValueError, "completion metadata"):
            list(audit.validate_completion(observed))


class ReportingAuditKnownExamples(unittest.TestCase):
    def test_overnight_overlap_and_half_open_end(self):
        windows = [
            {"id": "asia", "start": "20:00", "end": "02:00"},
            {"id": "asia_open", "start": "19:30", "end": "21:30"},
        ]
        self.assertEqual(audit.window_ids("2025-01-02 20:00:00", windows), ["all_hours", "asia", "asia_open"])
        self.assertEqual(audit.window_ids("2025-01-03 02:00:00", windows), ["all_hours"])
        self.assertEqual(audit.window_ids("2025-01-02 21:30:00", windows), ["all_hours", "asia"])

    def test_group_anchor_stays_at_first_open_across_ny_open(self):
        result = list(audit.reconstruct_runs(bars([None, "bullish", "bullish", "bearish"], start="2025-01-02 09:29:58"), 4, date(2026, 9, 24)))
        windows = [{"id": "ny_open", "start": "09:30", "end": "10:30"}]
        self.assertEqual(result[0]["length"], 2)
        self.assertEqual(audit.window_ids(result[0]["start_timestamp"], windows), ["all_hours"])

    def test_quantiles_have_linear_interpolation_and_null_empty(self):
        self.assertEqual(audit.quantile([1, 2, 8, 9], 0.5), 5.0)
        self.assertEqual(audit.quantile([1, 2, 8, 9], 0.25), 1.75)
        self.assertAlmostEqual(audit.quantile([1, 2, 8, 9], 0.9), 8.7)
        self.assertEqual(audit.quantile([7], 0.95), 7)
        self.assertIsNone(audit.quantile([], 0.5))

    def test_independent_summary_retains_censors_and_overlapping_cells(self):
        windows = [
            {"id": "asia", "start": "20:00", "end": "02:00"},
            {"id": "asia_open", "start": "19:30", "end": "21:30"},
        ]
        cells, coverage = {}, {}
        for length in (1, 2, 8, 9):
            audit.collect_run(cells, {
                "setting_ticks": 4, "direction": "bullish", "session_date": "2025-01-01",
                "start_timestamp": "2024-12-31 20:00:00", "left_censored": False,
                "right_censored": False, "length": length,
            }, windows)
        audit.collect_run(cells, {
            "setting_ticks": 4, "direction": "bullish", "session_date": "2025-01-01",
            "start_timestamp": "2024-12-31 20:00:00", "left_censored": True,
            "right_censored": True, "length": None,
        }, windows)
        audit.collect_coverage(coverage, audit.ObservedBar(
            1, datetime(2024, 12, 31, 20), date(2025, 1, 1), None,
            datetime(2024, 12, 31, 20, 1), "next_bar_start_proxy",
        ), 4, windows)
        tables = audit.expected_tables(cells, coverage, [4], [2024, 2025], windows)
        self.assertEqual(len(tables["summary"]), 27)
        overall = next(row for row in tables["summary"] if row["year"] is None and row["timeframe_id"] == "all_hours" and row["direction"] == "bullish")
        self.assertEqual((overall["observed_trends"], overall["exact_trends"], overall["censored_trends"]), (5, 4, 1))
        self.assertEqual((overall["left_censored_trends"], overall["right_censored_trends"]), (1, 1))
        self.assertEqual((overall["mean_candles"], overall["median_candles"], overall["q25_candles"]), (5.0, 5.0, 1.75))
        self.assertEqual(overall["tied_modes"], "1|2|8|9")
        self.assertEqual(overall["eligible_bar_count"], 1)
        year_rows = [row for row in tables["summary"] if row["year"] is not None and row["timeframe_id"] == "all_hours" and row["direction"] == "bullish"]
        self.assertEqual(sum(row["exact_trends"] for row in year_rows), overall["exact_trends"])
        self.assertEqual([row["exact_trends"] for row in year_rows], [0, 4])
        overlaps = [row for row in tables["summary"] if row["year"] is None and row["timeframe_id"] != "all_hours" and row["direction"] == "bullish"]
        self.assertEqual([row["exact_trends"] for row in overlaps], [4, 4])
        histogram = [row for row in tables["histogram"] if row["year"] is None and row["timeframe_id"] == "all_hours" and row["direction"] == "bullish"]
        self.assertEqual(sum(row["numerator"] for row in histogram), 4)
        self.assertEqual(sum(row["probability"] for row in histogram), 1.0)
        tails = [row for row in tables["survival"] if row["year"] is None and row["timeframe_id"] == "all_hours" and row["direction"] == "bullish"]
        self.assertEqual([row["numerator"] for row in tails], [3, 2, 2, 0, 0])

    def test_empty_cells_have_null_estimates_not_zero_lengths(self):
        tables = audit.expected_tables({}, {}, [4], [2025], [])
        self.assertEqual(len(tables["summary"]), 6)
        for row in tables["summary"]:
            self.assertEqual(row["exact_trends"], 0)
            self.assertIsNone(row["mean_candles"])
            self.assertIsNone(row["max_candles"])
            self.assertEqual(row["tied_modes"], "")
        self.assertTrue(all(row["probability"] is None for row in tables["histogram"]))

    def test_saved_csv_comparison_rejects_changed_counts_or_missing_rows(self):
        expected = [{"count": 4, "estimate": 5.0, "empty": None}]
        with tempfile.TemporaryDirectory() as directory:
            saved = Path(directory) / "saved.csv"
            saved.write_text("count,estimate,empty\n4,5,\n", encoding="utf-8")
            self.assertEqual(audit.compare_csv(expected, saved), 1)
            saved.write_text("count,estimate,empty\n3,5,\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "count"):
                audit.compare_csv(expected, saved)
            saved.write_text("count,estimate,empty\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "row count"):
                audit.compare_csv(expected, saved)


if __name__ == "__main__":
    unittest.main()
