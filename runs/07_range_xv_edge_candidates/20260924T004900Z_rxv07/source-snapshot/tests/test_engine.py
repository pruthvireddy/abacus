"""Focused timing and denominator checks for the frozen Range XV protocol."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import barrier_bounds, evaluate_events, masks, prior_30m_counts, select_nonoverlap


class EngineTests(unittest.TestCase):
    def test_prior_window_excludes_current_and_resets_session(self):
        df = pd.DataFrame({"start": pd.to_datetime(["2026-01-01 09:00:00", "2026-01-01 09:00:00",
                                                     "2026-01-01 09:29:59", "2026-01-01 09:30:00",
                                                     "2026-01-02 09:00:00"]),
                           "session_date_proxy": ["a", "a", "a", "a", "b"]})
        self.assertEqual(prior_30m_counts(df).tolist(), [0, 1, 2, 3, 0])

    def test_pullback_requires_extreme_and_strict_completion(self):
        df = pd.DataFrame({"direction": [1, 1, 1, -1, 1], "run_length": [1, 2, 3, 1, 1],
                           "session_date_proxy": ["a"] * 5,
                           "open_tick": [100, 101, 102, 103, 102],
                           "high_tick": [101, 102, 103, 104, 105],
                           "low_tick": [100, 101, 102, 102, 102],
                           "close_tick": [101, 102, 103, 102, 105],
                           "strict_completion": [True] * 5,
                           "clock_bucket": [19] * 5, "prior_30m": [2] * 5,
                           "full_30m_window": [True] * 5})
        protocol = {"idea_1": {"prior_run_min": 3}, "idea_2": {"long_run_min": 8}}
        found = masks(df, protocol, {19: 2})
        self.assertEqual(np.flatnonzero(found["pullback/extreme_break"]).tolist(), [4])
        self.assertEqual(np.flatnonzero(found["pullback/unfiltered"]).tolist(), [4])
        df.loc[4, "strict_completion"] = False
        self.assertFalse(masks(df, protocol, {19: 2})["pullback/extreme_break"].any())

    def test_nonoverlap_and_session_boundary(self):
        dates = np.array(["a"] * 7 + ["b"] * 5)
        chosen, invalid = select_nonoverlap(np.array([1, 2, 4, 6, 8]), 1, dates)
        self.assertEqual(chosen.tolist(), [1, 4, 8])
        self.assertEqual(invalid, 1)

    def test_wait_policy_keeps_unconfirmed_opportunity(self):
        df = pd.DataFrame({"direction": [1, -1, 1, 1, -1, 1, 1, 1],
                           "open_tick": [100, 100, 100, 101, 102, 105, 106, 107],
                           "high_tick": [101, 101, 101, 102, 103, 106, 107, 108],
                           "low_tick": [99, 99, 99, 100, 101, 104, 105, 106],
                           "close_tick": [101, 99, 101, 102, 101, 106, 107, 108],
                           "session_date_proxy": ["a"] * 8,
                           "start": pd.date_range("2026-01-01 09:00:00", periods=8, freq="min"),
                           "signal_clock": [f"09:{i:02d}:00" for i in range(8)],
                           "strict_completion": [True] * 8})
        rows = evaluate_events(df, np.array([2, 4]), product="ES", idea="exhaustion",
                               cohort="wait_policy", horizon=1, setting=6, wait=True)
        self.assertEqual(rows["traded"].tolist(), [True, False])
        self.assertEqual(rows["return_ticks"].tolist(), [3, 0])
        self.assertEqual(rows["confirmation_cost_ticks"].iloc[0], 1)

    def test_both_barriers_yield_bounds(self):
        df = pd.DataFrame({"open_tick": [100, 100, 100], "high_tick": [100, 107, 100],
                           "low_tick": [100, 93, 100]})
        events = pd.DataFrame({"idea": ["pullback"], "cohort": ["extreme_break"],
                               "signal_index": [0], "direction": [1], "return_ticks": [0], "product": ["ES"]})
        bound = barrier_bounds(events, df, 6, [1]).iloc[0]
        self.assertEqual(bound["ambiguous_both_hit"], 1)
        self.assertEqual(bound["mean_lower_ticks"], -6)
        self.assertEqual(bound["mean_upper_ticks"], 6)


if __name__ == "__main__":
    unittest.main()
