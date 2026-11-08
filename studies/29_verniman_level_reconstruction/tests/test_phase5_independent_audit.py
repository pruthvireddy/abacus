"""Synthetic checks for the independent small-assignment audit.

These fixtures contain no market or source-answer material and do not call any
candidate detector, selector, study matcher, or source loader.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[1]/"phase5/independent_comparison_audit.py"
SPEC=importlib.util.spec_from_file_location("study29_phase5_independent_audit_tests",SOURCE)
A=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=A
SPEC.loader.exec_module(A)


def source(identifier,price,order=1,high=None):
    return {"source_id":identifier,"interval":[price,price if high is None else high],"order":order}


def target(identifier,price,rank=1,high=None):
    return {"candidate_id":identifier,"interval":[price,price if high is None else high],"rank":rank}


class ExhaustiveAssignmentTests(unittest.TestCase):
    def test_cardinality_beats_greedy_nearest_first(self):
        # s1's nearest A is s2's only feasible target; optimal matching uses B.
        actual=A.exhaustive_assignment([source("s1",100),source("s2",99,2)],
            [target("A",100),target("B",101,2)])
        self.assertEqual(actual["matched_count"],2)
        self.assertEqual(actual["chosen_pairs"],[["s1","B"],["s2","A"]])
        self.assertEqual(actual["total_interval_gap"],"2")

    def test_total_gap_precedes_lexical_identity(self):
        actual=A.exhaustive_assignment([source("s",100)],
            [target("a",101),target("z",100,2)])
        self.assertEqual(actual["chosen_pairs"],[["s","z"]])
        self.assertEqual(actual["total_interval_gap"],"0")

    def test_equal_optima_retained_before_lexical_choice(self):
        actual=A.exhaustive_assignment([source("s",100)],
            [target("z",100),target("a",100,2)])
        self.assertEqual(actual["chosen_pairs"],[["s","a"]])
        self.assertEqual(actual["optimal_assignment_count"],2)
        self.assertEqual(actual["all_optimal_pairs"],[["s","a"],["s","z"]])

    def test_interval_overlap_is_zero_gap_without_boundary_equality(self):
        actual=A.exhaustive_assignment([source("s",100)],
            [target("zone",99,high=101)])
        self.assertEqual(actual["matched_count"],1)
        self.assertEqual(actual["total_interval_gap"],"0")
        self.assertIn("no construction/window",actual["classification"])

    def test_distinct_source_occurrences_cannot_share_one_target(self):
        actual=A.exhaustive_assignment([source("s1",100),source("s2",100,2)],
            [target("t",100)])
        self.assertEqual(actual["matched_count"],1)
        self.assertEqual(actual["source_misses"],1)
        self.assertFalse(actual["complete_coordinate_ladder"])

    def test_reversed_target_order_is_not_a_complete_ladder(self):
        actual=A.exhaustive_assignment([source("s1",100),source("s2",110,2)],
            [target("t1",100,2),target("t2",110,1)])
        self.assertEqual(actual["matched_count"],2)
        self.assertFalse(actual["relative_order_on_matched_subset"])
        self.assertFalse(actual["complete_coordinate_ladder"])

    def test_extra_physical_selection_prevents_complete_ladder(self):
        actual=A.exhaustive_assignment([source("s",100)],
            [target("match",100),target("extra",110,2)])
        self.assertEqual(actual["extras"],1)
        self.assertFalse(actual["complete_coordinate_ladder"])

    def test_empty_selection_keeps_order_undefined(self):
        actual=A.exhaustive_assignment([source("s",100)],[])
        self.assertEqual(actual["matched_count"],0)
        self.assertIsNone(actual["relative_order_on_matched_subset"])
        self.assertIsNone(actual["complete_coordinate_ladder"])

    def test_missing_orders_keep_completeness_undefined(self):
        actual=A.exhaustive_assignment([source("s",100,None)],[target("t",100)])
        self.assertEqual(actual["matched_count"],1)
        self.assertIsNone(actual["complete_coordinate_ladder"])

    def test_one_point_boundary_is_inclusive_using_exact_decimals(self):
        actual=A.exhaustive_assignment([source("s",100)],
            [target("inclusive",101),target("outside","101.00001",2)])
        self.assertEqual(actual["chosen_pairs"],[["s","inclusive"]])

    def test_duplicate_original_ids_rejected(self):
        with self.assertRaisesRegex(ValueError,"unique original"):
            A.exhaustive_assignment([source("s",100),source("s",110,2)],[])

    def test_two_optimal_permutations_keep_all_four_pairs(self):
        actual=A.exhaustive_assignment([source("s1",100),source("s2",100,2)],
            [target("t1",100),target("t2",100,2)])
        self.assertEqual(actual["optimal_assignment_count"],2)
        self.assertEqual(len(actual["all_optimal_pairs"]),4)
        self.assertEqual(actual["chosen_pairs"],[["s1","t1"],["s2","t2"]])


if __name__=="__main__":unittest.main()
