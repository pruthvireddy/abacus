"""OHLC scenario reference prices, ambiguity bounds and grouped evidence."""

from __future__ import annotations

import csv
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
from pullbacks import LEDGER_COLUMNS, extract_pullbacks, ledger_row
from pullback_analysis import EARLIER_LEG_BUCKETS
from pullback_payoff import PAYOFF_COLUMNS, PAYOFF_LEDGER_COLUMNS, analyze_payoffs, evaluate_payoffs, load_pullback_ledger, payoff_ledger_row
from timeframes import load_timeframes
from test_pullbacks import make_pullback_bar, pullback_sequence


def payoff_fixture(path, *, bearish=False):
    bars = pullback_sequence("ZUUUDU")
    bars += [make_pullback_bar(row, prices=prices) for row, prices in enumerate(path, 7)]
    if bearish:
        bars = [replace(bar, open=Decimal(200)-bar.open, high=Decimal(200)-bar.low,
                        low=Decimal(200)-bar.high, close=Decimal(200)-bar.close) for bar in bars]
    event = next(event for event in extract_pullbacks(bars, 4) if event.source_row == 6)
    return event, bars


class PullbackPayoffTests(unittest.TestCase):
    def run_path(self, path, *, bearish=False):
        event, bars = payoff_fixture(path, bearish=bearish)
        return list(evaluate_payoffs([event], bars, 4))

    def test_reference_and_structural_stop_are_mirrored(self) -> None:
        for bearish in (False, True):
            results = self.run_path([("100", "103", "99.5", "102")], bearish=bearish)
            self.assertEqual([1, 2], [result.target_multiple for result in results])
            self.assertEqual(["target_touch", "target_touch"], [result.exit_reason for result in results])
            self.assertEqual([Decimal(1), Decimal(2)], [result.payoff_lower_r for result in results])
            self.assertEqual(Decimal("101.25" if bearish else "98.75"), results[0].stop_price)
            self.assertEqual(Decimal("1.25"), results[0].risk_points)
            self.assertEqual(7, results[0].entry_source_row)

    def test_inclusive_stop_touch_is_minus_one(self) -> None:
        results = self.run_path([("100", "101", "98.75", "99")])
        self.assertTrue(all(result.exit_reason == "stop_touch" and result.payoff_lower_r == -1 for result in results))

    def test_both_touch_retains_unresolved_intrabar_order(self) -> None:
        for bearish in (False, True):
            results = self.run_path([("100", "103", "98", "100")], bearish=bearish)
            self.assertEqual(["ambiguous", "ambiguous"], [result.status for result in results])
            self.assertEqual([(Decimal(-1), Decimal(1)), (Decimal(-1), Decimal(2))],
                             [(result.payoff_lower_r, result.payoff_upper_r) for result in results])
            self.assertTrue(all(result.exit_price is None for result in results))

    def test_target1_resolved_and_target2_ambiguous_independently(self) -> None:
        results = self.run_path([("100", "101.25", "99.5", "101"), ("101", "103", "98", "100")])
        self.assertEqual(["target_touch", "both_touch"], [result.exit_reason for result in results])
        self.assertEqual([1, 2], [result.bars_observed for result in results])

    def test_stop_open_gap_precedes_target_extrema_and_uses_observed_open_move(self) -> None:
        results = self.run_path([("100", "101", "99.5", "100"), ("98", "103", "97", "101")])
        self.assertTrue(all(result.exit_reason == "stop_open_gap" for result in results))
        self.assertTrue(all(result.payoff_lower_r == Decimal("-1.6") for result in results))
        self.assertTrue(all(result.exit_available_at == result.entry_start_timestamp.replace(second=8) for result in results))

    def test_target_open_gap_precedes_stop_extrema_and_is_not_capped(self) -> None:
        results = self.run_path([("100", "101", "99.5", "100"), ("103", "104", "98", "99")])
        self.assertTrue(all(result.exit_reason == "target_open_gap" and result.payoff_lower_r == Decimal("2.4") for result in results))

    def test_physical_ten_bars_include_opposite_and_doji(self) -> None:
        path = [("100.5", "101", "99.5", "100"), ("100", "101", "99.5", "100")]*5
        path[0] = ("100", "101", "99.5", "100.5")
        path[-1] = ("100", "101", "99.5", "100.625")
        results = self.run_path(path)
        self.assertEqual(["marked", "marked"], [result.status for result in results])
        self.assertTrue(all(result.bars_observed == 10 and result.payoff_lower_r == Decimal("0.5") for result in results))
        self.assertTrue(all(result.exit_source_row == 16 for result in results))

    def test_short_unresolved_tail_is_unknown_not_terminal_mark(self) -> None:
        results = self.run_path([("100", "101", "99.5", "100.5")]*9)
        self.assertTrue(all(result.status == "unknown" and result.bars_observed == 9 for result in results))
        self.assertTrue(all(result.entry_price == 100 and result.payoff_lower_r is None for result in results))

    def test_nonpositive_risk_invalid_without_future_payoff(self) -> None:
        results = self.run_path([("98.5", "104", "98", "103")])
        self.assertTrue(all(result.status == "invalid" and result.risk_points == Decimal("-0.25") for result in results))
        self.assertTrue(all(result.target_price is None and result.bars_observed == 0 for result in results))

    def test_unavailable_F1_entry_unknown(self) -> None:
        event, bars = payoff_fixture([])
        results = list(evaluate_payoffs([event], bars, 4))
        self.assertTrue(all(result.exit_reason == "f1_unavailable" and result.entry_price is None for result in results))

    def test_barrier_session_and_source_gap_are_unknown_after_entry(self) -> None:
        event, bars = payoff_fixture([("100", "101", "99.5", "100"), ("100", "101", "99.5", "100")])
        variants = (replace(bars[-1], primary_eligible=False, barrier_reason="excluded_session"),
                    replace(bars[-1], session_date=date(2024, 6, 11)), replace(bars[-1], source_row=20))
        for last, reason in zip(variants, ("excluded_session", "session_boundary", "source_row_gap")):
            results = list(evaluate_payoffs([event], [*bars[:-1], last], 4))
            self.assertTrue(all(result.status == "unknown" and result.exit_reason == reason and result.bars_observed == 1 for result in results))

    def test_prior_resolution_stays_known_when_later_barrier_occurs(self) -> None:
        event, bars = payoff_fixture([("100", "101.25", "99.5", "101"), ("100", "101", "99.5", "100")])
        bars[-1] = replace(bars[-1], primary_eligible=False, barrier_reason="excluded_session")
        results = list(evaluate_payoffs([event], bars, 4))
        self.assertEqual(["resolved", "unknown"], [result.status for result in results])

    def test_results_order_by_setup_then_target_for_overlap(self) -> None:
        bars = pullback_sequence("ZUUUDUDUDUUU")
        events = list(extract_pullbacks(bars, 4))
        results = list(evaluate_payoffs(events, bars, 4))
        self.assertEqual([(event.source_row, target) for event in events for target in (1, 2)],
                         [(result.source_row, result.target_multiple) for result in results])

    def test_csv_loader_validates_exact_schema_strings_and_nulls(self) -> None:
        event, bars = payoff_fixture([("100", "103", "99.5", "102")])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"core.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS)
                writer.writeheader()
                writer.writerow(ledger_row(event))
            self.assertEqual([event], list(load_pullback_ledger(path)))
            results = list(evaluate_payoffs(path, bars, 4))
            row = payoff_ledger_row(results[0])
            self.assertEqual(PAYOFF_LEDGER_COLUMNS, tuple(row))
            self.assertEqual("1.25", row["risk_points"])
            self.assertEqual("true", row["earlier_start_known"])
            path.write_text(path.read_text().replace("true", "True"))
            with self.assertRaises(ValueError):
                list(load_pullback_ledger(path))

    def test_configuration_source_join_and_F1_drift_refused(self) -> None:
        event, bars = payoff_fixture([("100", "101", "99.5", "100")])
        for kwargs in ({"targets": []}, {"targets": [1, 1]}, {"targets": [True]}, {"horizon": 0}, {"buffer": Decimal(0)}):
            with self.assertRaises(ValueError):
                list(evaluate_payoffs([event], bars, 4, **kwargs))
        for bad_events, bad_bars, setting in (([event], bars, 5), ([replace(event, open=Decimal(9))], bars, 4),
                                             ([event], bars[:-2], 4), ([event, event], bars, 4),
                                             ([event], [*bars[:-1], replace(bars[-1], close=Decimal("100.1"))], 4)):
            with self.assertRaises(ValueError):
                list(evaluate_payoffs(bad_events, bad_bars, setting))

    def test_grouped_bounds_denominators_unknown_and_invalid(self) -> None:
        results = []
        for path in ([ ("100", "103", "99.5", "102") ], [("100", "101", "98", "99")],
                     [("100", "103", "98", "100")], [("100", "101", "99.5", "100")],
                     [("98.5", "104", "98", "103")]):
            results.extend(self.run_path(path))
        rows = analyze_payoffs(results, [4], load_timeframes(_ROOT/"study.yaml"), years=[2024])
        row = next(row for row in rows if row["year"] is None and row["timeframe_id"] == "all_hours"
                   and row["direction"] == "bullish" and row["earlier_leg_bucket"] == "3" and row["target_multiple"] == 1)
        self.assertEqual((5, 4, 1, 3, 1, 2, 1, 0), tuple(row[key] for key in
                         ("event_count", "valid_entry_count", "invalid_entry_count", "known_outcome_count", "unknown_outcome_count",
                          "resolved_count", "ambiguous_count", "marked_count")))
        self.assertEqual((1, 2, 3, 1/3, 2/3), tuple(row[key] for key in
                         ("win_lower_numerator", "win_upper_numerator", "denominator", "win_rate_lower", "win_rate_upper")))
        self.assertEqual((Decimal(-1), Decimal(1), -1/3, 1/3), tuple(row[key] for key in
                         ("payoff_lower_sum_r", "payoff_upper_sum_r", "mean_lower_r", "mean_upper_r")))

    def test_all_empty_cells_and_schema(self) -> None:
        rows = analyze_payoffs([], [4, 5, 6], load_timeframes(_ROOT/"study.yaml"))
        self.assertEqual(19440, len(rows))
        self.assertEqual(PAYOFF_COLUMNS, tuple(rows[0]))
        self.assertTrue(all(row["event_count"] == 0 and row["mean_lower_r"] is None for row in rows))

    def test_payoff_earlier_cohort_and_direction_counts_conserve(self) -> None:
        results = [*self.run_path([("100", "103", "99.5", "102")]),
                   *self.run_path([("100", "103", "98", "100")], bearish=True)]
        rows = analyze_payoffs(results, [4], load_timeframes(_ROOT/"study.yaml"), years=[2024])
        selected = [row for row in rows if row["year"] is None and row["timeframe_id"] == "all_hours" and row["target_multiple"] == 1]
        overall = next(row for row in selected if row["direction"] == "all" and row["earlier_leg_bucket"] == "all")
        for key in ("event_count", "known_outcome_count", "win_lower_numerator", "win_upper_numerator", "payoff_lower_sum_r", "payoff_upper_sum_r"):
            cohorts = [row for row in selected if row["direction"] == "all" and row["earlier_leg_bucket"] in EARLIER_LEG_BUCKETS[1:]]
            self.assertEqual(overall[key], sum(row[key] for row in cohorts))
            directions = [row for row in selected if row["direction"] != "all" and row["earlier_leg_bucket"] == "all"]
            self.assertEqual(overall[key], sum(row[key] for row in directions))


if __name__ == "__main__":
    unittest.main()
