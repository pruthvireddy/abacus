"""Hand-worked comparison fixtures; no source targets, bars or Pine execution."""

from dataclasses import replace
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "phase3" / "matching.py"
SPEC = importlib.util.spec_from_file_location("study29_phase3_matching", SOURCE)
MODEL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)
SourceReference = MODEL.SourceReference
CandidateReference = MODEL.CandidateReference
compare_references = MODEL.compare_references


def source(identity, price=10, **kwargs):
    base = SourceReference(identity, "2026-10-01", "daily_plan", "r1", ("HVE",),
                           (price, price), "rth:2026-09-30", "ESZ2026", "unadjusted")
    return replace(base, **kwargs)


def candidate(identity, price=10, **kwargs):
    base = CandidateReference(identity, "2026-10-01", "HVE", (price, price),
                              "rth:2026-09-30", "ESZ2026", "unadjusted")
    return replace(base, **kwargs)


def compare(sources, candidates):
    return compare_references(sources, candidates, candidate_map_ready=True)


def pairs(result):
    return [(row["source_id"], row["candidate_id"])
            for group in result["strata"] for row in group["assignments"]]


class ExactMatchingTests(unittest.TestCase):
    def test_maximum_cardinality_reassigns_a_nearest_candidate(self):
        # A's nearest candidate is X (.4 away), but B can only use X.
        # Maximum coverage is A->Y (.8), B->X (0), not greedy A->X.
        result = compare([source("A", ".4"), source("B", "0")],
                         [candidate("X", "0"), candidate("Y", "1.2")])
        self.assertEqual(pairs(result), [("A", "Y"), ("B", "X")])
        self.assertEqual(result["matched_role_count"], 2)
        self.assertEqual(Decimal(result["strata"][0]["total_interval_gap_points"]), Decimal(".8"))

    def test_minimum_total_gap_follows_cardinality(self):
        # Both perfect matchings cover two sources; .25+.25 beats .75+.75.
        result = compare([source("A", 0), source("B", 1)],
                         [candidate("X", ".25"), candidate("Y", ".75")])
        self.assertEqual(pairs(result), [("A", "X"), ("B", "Y")])
        self.assertEqual(Decimal(result["strata"][0]["total_interval_gap_points"]), Decimal(".50"))
        alternatives = result["strata"][0]["feasible_alternatives"]
        self.assertEqual(len(alternatives), 4)
        self.assertEqual(sum(row["in_equal_optimum"] for row in alternatives), 2)

    def test_lexicographic_ties_and_equal_optimum_alternatives_are_retained(self):
        sources = [source("B"), source("A")]
        candidates = [candidate("Y"), candidate("X")]
        result = compare(sources, candidates)
        self.assertEqual(pairs(result), [("A", "X"), ("B", "Y")])
        self.assertEqual(compare(list(reversed(sources)), list(reversed(candidates))), result)
        self.assertTrue(all(row["in_equal_optimum"] for row in result["strata"][0]["feasible_alternatives"]))

    def test_intervals_touch_without_claiming_precise_boundary_agreement(self):
        result = compare([source("A", interval=(10, 12))],
                         [candidate("X", interval=(12, 16), boundary=14)])
        row = result["strata"][0]["assignments"][0]
        self.assertEqual(row["interval_gap_points"], "0")
        self.assertEqual(row["source_interval_width"], "2")
        self.assertEqual(row["candidate_interval_width"], "4")
        self.assertEqual(row["source_midpoint_minus_boundary"], "-3")

    def test_global_tolerance_is_inclusive_without_floating_roundoff(self):
        result = compare([source("A", "10.1")], [candidate("X", "11.1")])
        self.assertEqual(result["matched_role_count"], 1)
        result = compare([source("A", "10.1")], [candidate("X", "11.1000000001")])
        self.assertEqual(result["matched_role_count"], 0)
        self.assertEqual(result["strata"][0]["unmatched_source_ids"], ["A"])

    def test_one_candidate_does_not_match_two_source_occurrences_in_same_stratum(self):
        result = compare([source("A"), source("B")], [candidate("X")])
        self.assertEqual(pairs(result), [("A", "X")])
        self.assertEqual(result["primary_role_coverage"], .5)
        self.assertEqual(result["strata"][0]["unmatched_source_ids"], ["B"])


class QualificationTests(unittest.TestCase):
    def test_family_price_proximity_cannot_substitute_for_construction(self):
        result = compare([source("A")], [candidate("POC", family="YPOC")])
        self.assertEqual(result["matched_role_count"], 0)
        self.assertEqual(result["unmatched_generated_candidate_ids"], ["POC"])

    def test_window_and_contract_adjustment_must_match(self):
        for change in ({"window_id": "overnight:2026-10-01"}, {"contract": "ES1!"},
                       {"adjustment": "back_adjusted"}, {"session_date": "2026-10-02"}):
            with self.subTest(change=change):
                result = compare([source("A")], [candidate("X", **change)])
                self.assertEqual(result["matched_role_count"], 0)
                self.assertEqual(result["eligible_role_count"], 1)

    def test_unknown_window_has_no_primary_denominator(self):
        result = compare([source("A", window_id=None)], [candidate("X")])
        self.assertEqual(result["status"], "not_estimable")
        self.assertIsNone(result["primary_role_coverage"])
        self.assertEqual(result["readable_source_occurrences"], 1)
        self.assertEqual(result["eligible_occurrence_count"], 0)
        self.assertIn("unknown_reference_window", result["source_role_exclusions"][0]["reasons"])
        self.assertEqual(result["unresolved_alternatives"][0]["candidate_id"], "X")
        self.assertFalse(result["unresolved_alternatives"][0]["primary_match"])

    def test_unsupported_family_and_unknown_coordinates_are_excluded_explicitly(self):
        result = compare([source("A", families=("GAP",)), source("B", contract=None)], [candidate("X")])
        self.assertEqual(result["eligible_role_count"], 0)
        reasons = [row["reasons"] for row in result["source_role_exclusions"]]
        self.assertIn(["unsupported_family"], reasons)
        self.assertIn(["unknown_contract_or_price_coordinates"], reasons)

    def test_later_source_timing_is_preserved_and_never_certified_as_preopen(self):
        result = compare([source("A", timing_class="supported later/intraday")], [candidate("X")])
        row = result["strata"][0]["assignments"][0]
        self.assertEqual(row["source_timing_class"], "supported later/intraday")
        self.assertIsNone(row["source_historical_available_at"])

    def test_revisions_and_source_classes_remain_separate_observation_strata(self):
        result = compare([source("A"), source("B", revision_id="r2"),
                          source("C", source_class="closing_chart")], [candidate("X")])
        self.assertEqual(len(result["strata"]), 3)
        self.assertEqual(result["matched_role_count"], 3)
        self.assertEqual(result["unmatched_generated_candidate_ids"], [])

    def test_compound_roles_count_one_occurrence_with_full_and_partial_coverage(self):
        row = source("A", families=("HVE", "YVAL"))
        result = compare([row], [candidate("edge"), candidate("value", family="YVAL")])
        self.assertEqual(result["matched_role_count"], 2)
        self.assertEqual(result["matched_occurrence_count"], 1)
        self.assertEqual(result["fully_covered_occurrence_count"], 1)
        result = compare([row], [candidate("edge")])
        self.assertEqual(result["matched_role_count"], 1)
        self.assertEqual(result["matched_occurrence_count"], 1)
        self.assertEqual(result["fully_covered_occurrence_count"], 0)
        self.assertEqual(result["occurrences"][0]["coverage"], "partial_roles")

    def test_unsupported_compound_component_cannot_count_as_full_coverage(self):
        result = compare([source("A", families=("HVE", "GAP"))], [candidate("X")])
        self.assertEqual(result["eligible_role_count"], 1)
        self.assertEqual(result["matched_occurrence_count"], 1)
        self.assertEqual(result["fully_covered_occurrence_count"], 0)

    def test_presentation_omission_does_not_remove_qualified_candidate(self):
        result = compare([source("A")], [candidate("X", displayed=False)])
        self.assertEqual(result["qualified_generated_count"], 1)
        self.assertEqual(result["displayed_generated_count"], 0)
        self.assertEqual(result["presentation_omitted_ids"], ["X"])
        self.assertEqual(result["matched_role_count"], 1)

    def test_unavailable_map_has_no_comparison_even_with_baseline_like_inputs(self):
        result = compare_references([source("A")], [candidate("X")], candidate_map_ready=False)
        self.assertEqual(result["status"], "not_executed")
        self.assertEqual(result["strata"], [])
        self.assertIsNone(result["primary_role_coverage"])
        self.assertIsNone(result["qualified_generated_count"])
        self.assertIsNone(result["displayed_generated_count"])

    def test_bad_intervals_and_unready_candidates_cannot_match(self):
        result = compare([source("A", interval=(12, 10)), source("B", interval=("NaN", 10))],
                         [candidate("X", ready=False), candidate("Y", interval=(float("inf"), 10))])
        self.assertEqual(result["readable_source_occurrences"], 0)
        self.assertEqual(result["qualified_generated_count"], 0)
        self.assertEqual(len(result["candidate_exclusions"]), 2)
        self.assertEqual(result["status"], "not_estimable")

    def test_unidentified_candidate_and_invalid_boundary_are_not_qualified(self):
        result = compare([source("A")], [candidate("X", window_id=""),
                                        candidate("Y", boundary="NaN")])
        self.assertEqual(result["qualified_generated_count"], 0)
        self.assertEqual(result["matched_role_count"], 0)
        self.assertEqual(result["candidate_exclusions"][0]["reasons"], ["missing_candidate_identity"])
        self.assertEqual(result["candidate_exclusions"][1]["reasons"], ["invalid_boundary"])

    def test_duplicate_ids_or_roles_are_rejected(self):
        for sources, candidates in (([source("A"), source("A")], []),
                                    ([], [candidate("X"), candidate("X")]),
                                    ([source("A", families=("HVE", "HVE"))], [])):
            with self.subTest(sources=sources, candidates=candidates):
                with self.assertRaises(ValueError):
                    compare(sources, candidates)


if __name__ == "__main__":
    unittest.main()
