"""Synthetic source-role units; no dated source labels or market inputs read."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "phase4/source_roles.py"
SPEC = importlib.util.spec_from_file_location("study29_phase4_source_role_units", PATH)
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)


class SourceRoleUnitTests(unittest.TestCase):
    def row(self, name, side, low="100", high=None, **changes):
        row = {"level_id": name, "source_id": "synthetic-plan", "session_date": "2026-10-01",
               "source_class": "named_daily_plan", "phase4_role": "conditional_scenario_divider",
               "scenario_side": side, "price_low": low, "price_high": low if high is None else high,
               "original_label": "synthetic label", "families": ["HVE"],
               "directional_conditions": side + " synthetic condition", "available_at": None,
               "provenance": {"source_revision_id": "synthetic-revision"}}
        row.update(changes)
        return row

    def test_identical_two_branch_intervals_make_one_unit_without_losing_rows(self):
        rows = [self.row("bull", "bullish"), self.row("bear", "bearish")]
        before = deepcopy(rows)
        result, = R.interpret_divider_strata(rows)
        self.assertEqual(result["status"], "unique_common_functional_divider")
        self.assertEqual(result["primary_source_unit_count"], 1)
        self.assertEqual(len(result["source_occurrences"]), 2)
        self.assertEqual(rows, before)

    def test_different_branch_prices_do_not_choose_the_nearer_trigger(self):
        result, = R.interpret_divider_strata([self.row("bull", "bullish", "100"), self.row("bear", "bearish", "101")])
        self.assertEqual(result["status"], "unresolved_single_pivot_ground_truth")
        self.assertIsNone(result["primary_price_interval"])
        self.assertFalse(result["price_averaged_or_nearest_trigger_chosen"])

    def test_overlapping_but_different_intervals_stay_unresolved(self):
        result, = R.interpret_divider_strata([self.row("bull", "bullish", "99", "101"), self.row("bear", "bearish", "100", "102")])
        self.assertIsNone(result["primary_price_interval"])

    def test_multiple_triggers_cannot_drop_one_to_find_a_common_price(self):
        rows = [self.row("bull-a", "bullish", "100"), self.row("bull-b", "bullish", "110"), self.row("bear", "bearish", "100")]
        result, = R.interpret_divider_strata(rows)
        self.assertIsNone(result["primary_price_interval"])
        self.assertEqual(len(result["source_occurrences"]), 3)

    def test_missing_branch_is_not_a_common_divider(self):
        result, = R.interpret_divider_strata([self.row("bull", "bullish")])
        self.assertIn("MISSING_OR_UNRESOLVED_BRANCH_TRIGGER", result["reasons"])

    def test_equal_numeric_bounds_preserve_literal_precision(self):
        result, = R.interpret_divider_strata([self.row("bull", "bullish", "100.0"), self.row("bear", "bearish", "100.00")])
        self.assertEqual(result["status"], "unique_common_functional_divider")
        self.assertEqual({x["original_price_interval"][0] for x in result["source_occurrences"]}, {"100.0", "100.00"})

    def test_branch_family_conflict_does_not_become_compound_confluence(self):
        result, = R.interpret_divider_strata([self.row("bull", "bullish", families=["YVALH"]), self.row("bear", "bearish", families=["YVAL"])])
        self.assertEqual(result["status"], "unique_common_functional_divider")
        self.assertFalse(result["primary_family_identity_consistent"])
        self.assertIsNone(result["common_families"])

    def test_different_revisions_are_separate_units_not_nearest_revision_selection(self):
        rows = [self.row("b1", "bullish"), self.row("s1", "bearish"),
                self.row("b2", "bullish", "110", provenance={"source_revision_id": "revision2"}),
                self.row("s2", "bearish", "110", provenance={"source_revision_id": "revision2"})]
        result = R.interpret_divider_strata(rows)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(x["primary_source_unit_count"] == 1 for x in result))

    def test_unreadable_interval_is_not_dropped_to_create_a_match(self):
        result, = R.interpret_divider_strata([self.row("bull", "bullish", "NaN"), self.row("bear", "bearish")])
        self.assertIsNone(result["primary_price_interval"])
        self.assertIn("INVALID_OR_UNREADABLE_TRIGGER_INTERVAL", result["reasons"])

    def test_duplicate_occurrence_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            R.interpret_divider_strata([self.row("same", "bullish"), self.row("same", "bearish")])

    def test_nondivider_target_rows_are_not_promoted_to_dividers(self):
        result = R.interpret_divider_strata([self.row("target", "bullish", phase4_role="ordered_bullish_destination")])
        self.assertEqual(result, [])

    def test_unit_id_is_order_invariant_and_unaffected_by_another_revision(self):
        first = [self.row("bull", "bullish"), self.row("bear", "bearish")]
        one, = R.interpret_divider_strata(first)
        reverse, = R.interpret_divider_strata(list(reversed(first)))
        extended = R.interpret_divider_strata(first + [self.row("other-bull", "bullish", "110", provenance={"source_revision_id": "other-revision"}), self.row("other-bear", "bearish", "110", provenance={"source_revision_id": "other-revision"})])
        same = next(unit for unit in extended if unit["source_stratum"]["source_revision_id"] == "synthetic-revision")
        self.assertEqual(one["unit_id"], reverse["unit_id"])
        self.assertEqual(one["unit_id"], same["unit_id"])


class CoordinateReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study = PATH.parents[1]
        spec = importlib.util.spec_from_file_location("study29_phase4_training_reporting", study / "phase4/run_training.py")
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)
        cls.matching = cls.runner.load_module("study29_phase4_synthetic_reporting_matcher", study / "phase3/matching.py")

    def row(self, name, order=1, revision="r1", price="100"):
        return {"level_id": name, "session_date": "2026-10-01", "source_class": "synthetic",
                "provenance": {"source_revision_id": revision}, "price_low": price, "price_high": price,
                "source_target_order": order}

    def candidate(self, name="c1", rank=1, price=100):
        return {"candidate_id": name, "rank": rank, "price": price, "interval": [price, price]}

    def report(self, rows, candidates):
        return self.runner.coordinate_diagnostic(rows, candidates, self.matching, 1)

    def test_empty_ladder_is_unresolved(self):
        self.assertIsNone(self.report([], [])["complete_coordinate_ladder"])

    def test_missing_order_does_not_become_complete(self):
        self.assertIsNone(self.report([self.row("s", None)], [self.candidate()])["complete_coordinate_ladder"])

    def test_duplicate_orders_do_not_become_complete(self):
        result = self.report([self.row("s1"), self.row("s2", price="110")], [self.candidate(), self.candidate("c2", 2, 110)])
        self.assertEqual(result["matched_count"], 2)
        self.assertIsNone(result["complete_coordinate_ladder"])

    def test_observed_complete_order_is_true(self):
        result = self.report([self.row("s1"), self.row("s2", 2, price="110")], [self.candidate(), self.candidate("c2", 2, 110)])
        self.assertTrue(result["complete_coordinate_ladder"])

    def test_reversed_order_is_false(self):
        result = self.report([self.row("s1"), self.row("s2", 2, price="110")], [self.candidate(rank=2), self.candidate("c2", 1, 110)])
        self.assertFalse(result["complete_coordinate_ladder"])

    def test_extra_source_target_remains_in_denominator(self):
        result = self.report([self.row("s1"), self.row("s2", 2, price="110")], [self.candidate()])
        self.assertEqual(result["source_count"], 2)
        self.assertFalse(result["complete_coordinate_ladder"])

    def test_two_revisions_have_independent_assignments_and_no_pooled_score(self):
        rows = [self.row("s1"), self.row("s2", revision="r2")]
        result = self.runner.target_coordinate_diagnostic(rows, [self.candidate()], self.matching, 1)
        self.assertEqual(result["source_strata_count"], 2)
        self.assertIsNone(result["matched_count"])
        self.assertEqual([x["diagnostic"]["matched_count"] for x in result["per_source_stratum"]], [1, 1])

    def test_duplicate_occurrence_id_rejected(self):
        with self.assertRaises(ValueError):
            self.report([self.row("s"), self.row("s", 2)], [self.candidate()])
