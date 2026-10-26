import unittest

import numpy as np

from abacus_sahadeva.cooldown import accepted_bar_indices


class CooldownTest(unittest.TestCase):
    def assert_indices(self, candidates, cooldown, expected):
        result = accepted_bar_indices(candidates, cooldown)
        np.testing.assert_array_equal(result, expected)
        self.assertEqual(result.dtype, np.dtype(np.int64))
        return result

    def test_empty_input_has_int64_output(self):
        for cooldown in (0, 3):
            with self.subTest(cooldown=cooldown):
                self.assert_indices(np.empty(0, dtype=np.int64), cooldown, [])

    def test_isolated_candidates_use_original_sparse_bar_positions(self):
        self.assert_indices(np.array([0, 50, 100]), 3, [0, 50, 100])
        self.assert_indices(np.array([5, 7, 10, 50]), 3, [5, 10, 50])

    def test_consecutive_candidates_and_cooldown_zero(self):
        candidates = np.arange(8)
        self.assert_indices(candidates, 0, [0, 1, 2, 3, 4, 5, 6, 7])
        self.assert_indices(candidates, 2, [0, 3, 6])

    def test_exact_cooldown_boundary_and_first_eligible_bar(self):
        self.assert_indices(np.array([10, 13, 14, 17, 18]), 3, [10, 14, 18])

    def test_suppressed_candidate_does_not_rearm(self):
        self.assert_indices(np.array([10, 11, 12, 14, 15, 20]), 3, [10, 14, 20])

    def test_filter_must_run_before_cooldown(self):
        np.testing.assert_array_equal(accepted_bar_indices(np.array([10, 11, 14]), 3), [10, 14])
        np.testing.assert_array_equal(accepted_bar_indices(np.array([11, 14]), 3), [11])

    def test_calls_are_independent_inputs_unchanged_and_results_have_int64_type(self):
        candidates = np.array([0, 1, 4, 9], dtype=np.int32)
        before = candidates.copy()
        first = self.assert_indices(candidates, 3, [0, 4, 9])
        self.assert_indices(np.array([1, 2, 5]), 3, [1, 5])
        first[0] = 999
        self.assert_indices(candidates, 3, [0, 4, 9])
        np.testing.assert_array_equal(candidates, before)
        self.assertEqual(candidates.dtype, np.dtype(np.int32))

    def test_negative_cooldown_retains_rejection_without_mutating_input(self):
        for candidates in (np.array([], dtype=np.int64), np.array([0, 5])):
            with self.subTest(candidates=candidates.tolist()):
                before = candidates.copy()
                with self.assertRaisesRegex(ValueError, "cooldown must be nonnegative"):
                    accepted_bar_indices(candidates, -1)
                np.testing.assert_array_equal(candidates, before)

    def test_duplicate_and_descending_positions_retain_rejection(self):
        for candidates in (np.array([1, 1, 2]), np.array([10, 5]), np.array([1, 5, 3])):
            with self.subTest(candidates=candidates.tolist()):
                before = candidates.copy()
                with self.assertRaisesRegex(ValueError, "indices strictly increasing"):
                    accepted_bar_indices(candidates, 0)
                np.testing.assert_array_equal(candidates, before)


if __name__ == "__main__":
    unittest.main()
