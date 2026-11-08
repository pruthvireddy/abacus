"""Independent synthetic ranking checks; not a Pine interpreter."""
from copy import deepcopy
from itertools import permutations
from pathlib import Path
import sys
import unittest

_study_src = Path(__file__).resolve().parents[1] / "src"
if _study_src.is_dir():
    sys.path.insert(0, str(_study_src))
    from pivot_model import rank_candidates
else:
    from ranking_model_addition import rank_candidates


def edge(price, *, family=5, key=25, prominence=4, qualified=True, overlap=False):
    return {"coordinate": price, "family": family, "parent_key": key,
            "prominence": prominence, "qualified": qualified, "overlap": overlap}


class RankedCandidateTests(unittest.TestCase):
    def rank(self, **overrides):
        settings = dict(primary=96, alternate=100, yval=96, ypoc=100,
                        yvah=104, onpoc=102, price=94, edges=(), limit=5)
        return rank_candidates(**(settings | overrides))

    def prices(self, **overrides):
        return [row["price"] for row in self.rank(**overrides)["candidates"]]

    def test_existing_alternate_precedes_nearer_candidates(self):
        rows = self.rank(alternate=104, edges=(edge(94.5),))["candidates"]
        self.assertEqual([r["price"] for r in rows], [104, 94.5, 100, 102])
        self.assertEqual([r["priority"] for r in rows], [0, 1, 1, 1])

    def test_same_tier_candidates_use_distance_from_frozen_p(self):
        self.assertEqual(self.prices(alternate=None, price=101), [100, 102, 104])

    def test_family_code_resolves_equal_distance_before_price(self):
        rows = self.rank(alternate=None, price=102, onpoc=110)["candidates"]
        self.assertEqual([r["family"] for r in rows[:2]], [2, 3])
        self.assertEqual([r["price"] for r in rows[:2]], [100, 104])

    def test_prior_reference_family_wins_equal_distance_to_edge(self):
        rows = self.rank(alternate=None, price=101,
                         edges=(edge(102, prominence=100),))["candidates"]
        self.assertEqual(rows[0]["family"], 2)
        self.assertEqual(rows[1]["family"], 4)

    def test_same_family_distance_tie_uses_descending_prominence(self):
        rows = self.rank(alternate=100, price=94,
                         edges=(edge(93, key=1, prominence=2),
                                edge(95, key=2, prominence=8)))["candidates"]
        self.assertEqual([r["price"] for r in rows[:3]], [100, 95, 93])

    def test_identical_distance_family_prominence_uses_lower_price(self):
        rows = self.rank(edges=(edge(93, key=2), edge(95, key=1)))["candidates"]
        self.assertEqual([r["price"] for r in rows[:3]], [100, 93, 95])

    def test_same_price_identity_tie_uses_lowest_parent_key(self):
        rows = self.rank(edges=(edge(95, key=3), edge(95, key=1)))["candidates"]
        selected = next(r for r in rows if r["price"] == 95)
        self.assertEqual(selected["parent_key"], 1)
        self.assertEqual(selected["source_identities"],
                         ("ON lower E1 N1@1", "ON lower E1 N1@3"))

    def test_dedupe_retains_all_source_family_bits_and_original_price(self):
        rows = self.rank(edges=(edge(100, family=5, key=21),
                                edge(100, family=6, key=19)))["candidates"]
        selected = rows[0]
        self.assertEqual((selected["price"], selected["family"], selected["parent_key"]),
                         (100, 2, None))
        self.assertEqual(selected["identity_mask"], 2 | 16 | 32)
        self.assertEqual(len(selected["source_identities"]), 3)
        self.assertEqual(sum(row["price"] == 100 for row in rows), 1)

    def test_primary_price_excluded_across_all_identities(self):
        rows = self.rank(edges=(edge(96), edge(96, family=6)))["all_candidates"]
        self.assertNotIn(96, [row["price"] for row in rows])

    def test_duplicate_value_references_are_one_candidate(self):
        rows = self.rank(ypoc=104, alternate=104, onpoc=104)["candidates"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["identity_mask"], 2 | 4 | 8)

    def test_qualified_and_nonoverlapping_edges_only(self):
        rows = self.rank(edges=(edge(93, qualified=False), edge(94, overlap=True),
                                edge(95)))["candidates"]
        self.assertIn(95, [row["price"] for row in rows])
        self.assertNotIn(93, [row["price"] for row in rows])
        self.assertNotIn(94, [row["price"] for row in rows])

    def test_malformed_or_nonfinite_edges_withheld(self):
        edges = (edge(float("nan")), edge(95, prominence=float("inf")),
                 edge(95, key=None), edge(95, family=2), edge(95, family=5.0),
                 edge(95, prominence=-1), None, edge(93))
        self.assertEqual(self.prices(edges=edges), [100, 93, 102, 104])

    def test_top_k_reports_known_pool_truncation(self):
        result = self.rank(limit=2, edges=(edge(93), edge(95)))
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["total_distinct"], 5)
        self.assertTrue(result["truncated"])
        self.assertEqual([r["rank"] for r in result["all_candidates"]], [1, 2, 3, 4, 5])

    def test_exact_limit_and_small_pools_not_reported_truncated(self):
        self.assertFalse(self.rank(limit=3)["truncated"])
        self.assertFalse(self.rank(limit=8)["truncated"])

    def test_all_candidates_equal_primary_returns_ready_empty(self):
        result = self.rank(primary=100, alternate=None, yval=100, ypoc=100,
                           yvah=100, onpoc=100, edges=(edge(100),))
        self.assertTrue(result["ready"])
        self.assertEqual(result["total_distinct"], 0)
        self.assertEqual(result["candidates"], [])

    def test_input_order_cannot_change_prices_or_identities(self):
        edges = (edge(93, key=1), edge(95, family=6, key=2),
                 edge(100, key=3), edge(95, family=5, key=4))
        baseline = self.rank(edges=edges)
        for ordering in permutations(edges):
            self.assertEqual(self.rank(edges=ordering), baseline)

    def test_missing_required_input_returns_empty_unavailable(self):
        for field in ("primary", "yval", "ypoc", "yvah", "onpoc", "price"):
            with self.subTest(field=field):
                result = self.rank(**{field: None})
                self.assertFalse(result["ready"])
                self.assertEqual(result["candidates"], [])

    def test_nonfinite_required_input_returns_empty_unavailable(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            for field in ("primary", "yval", "ypoc", "yvah", "onpoc", "price"):
                with self.subTest(field=field, value=value):
                    self.assertFalse(self.rank(**{field: value})["ready"])

    def test_absent_or_nonfinite_alternate_does_not_invalidate_ready_pool(self):
        for value in (None, float("nan"), float("inf")):
            with self.subTest(value=value):
                result = self.rank(alternate=value)
                self.assertTrue(result["ready"])
                self.assertTrue(all(r["priority"] == 1 for r in result["candidates"]))

    def test_original_numeric_prices_never_rounded_or_averaged(self):
        values = self.prices(primary=96.25, yval=96.25, alternate=100.75,
                             ypoc=100.75, yvah=104.5, onpoc=102.125,
                             edges=(edge(94.875),))
        self.assertEqual(values, [100.75, 94.875, 102.125, 104.5])

    def test_input_objects_remain_unchanged(self):
        edges = [edge(93), edge(95, family=6), edge(100)]
        original = deepcopy(edges)
        result = self.rank(edges=edges)
        self.assertEqual(edges, original)
        result["candidates"][0]["source_identities"] += ("changed copy",)
        self.assertEqual(edges, original)

    def test_supported_display_limits_are_bounded(self):
        for value in (0, 9, 1.5, True, None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.rank(limit=value)
        self.assertEqual(self.rank(limit=1)["limit"], 1)
        self.assertEqual(self.rank(limit=8)["limit"], 8)


if __name__ == "__main__":
    unittest.main()
