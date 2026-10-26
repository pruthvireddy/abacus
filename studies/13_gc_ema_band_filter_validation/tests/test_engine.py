import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import accepted_context, build_context, event_scores, summarize


class ContextTest(unittest.TestCase):
    def test_filters_use_only_current_and_prior_bars(self):
        ts = pd.date_range("2025-01-02 13:00", periods=25, freq="5min", tz="UTC")
        close = np.full(25, 100.)
        close[21] = 98.
        close[22] = 99.
        bars = pd.DataFrame({"ts_event": ts, "session_date": [pd.Timestamp("2025-01-02").date()] * 25,
                             "open": np.full(25, 99.) * 1e9,
                             "high": np.full(25, 101.) * 1e9,
                             "low": np.full(25, 97.) * 1e9,
                             "close": close * 1e9,
                             "raw_symbol": ["GCG5"] * 25,
                             "price_adjustment": [0] * 25,
                             "source_bar_count": [5] * 25,
                             "is_partial_bar": [False] * 25,
                             "is_mixed_contract_bar": [False] * 25,
                             "is_mixed_adjustment_bar": [False] * 25,
                             "contains_roll": [False] * 25})
        bands = pd.DataFrame({"ts_event": ts, "available_at": ts + pd.Timedelta(minutes=5),
                              "ema_base_225": np.full(25, 100.),
                              "residual_sigma_225": np.ones(25),
                              "lower_outer_3sigma": np.full(25, 99.)})
        context = build_context(bars, bands)
        self.assertEqual(context.bar_index.tolist(), [21, 22])
        self.assertTrue(context.first_outer_close.iloc[0])
        self.assertFalse(context.first_outer_close.iloc[1])
        self.assertTrue(context.upper_half_close.iloc[1])
        self.assertTrue(context.shallow_penetration_025.iloc[1])
        self.assertEqual(context.year.tolist(), [2025, 2025])
        bars.loc[23, "close"] = 10 * 1e9
        later_changed = build_context(bars, bands)
        pd.testing.assert_frame_equal(context, later_changed.iloc[:2].reset_index(drop=True))

    def test_filter_is_applied_before_cooldown(self):
        context = pd.DataFrame({"bar_index": [10, 11, 14], "upper_half_close": [False, True, True]})
        accepted = accepted_context(context, "upper_half_close", 3)
        self.assertEqual(accepted.bar_index.tolist(), [11])

    def test_year_subset_follows_full_history_cadence(self):
        # Method-contract fixture: the runner's use of full context is reviewed
        # separately; this test does not execute a study or its outcome pipeline.
        context = pd.DataFrame({"bar_index": [10, 11, 14], "year": [2024, 2025, 2025]})
        accepted = accepted_context(context, "unfiltered", 3)
        self.assertEqual(accepted.bar_index.tolist(), [10, 14])
        self.assertEqual(accepted.loc[accepted.year == 2025].bar_index.tolist(), [14])
        premature_subset = accepted_context(context.loc[context.year == 2025], "unfiltered", 3)
        self.assertEqual(premature_subset.bar_index.tolist(), [11])

    def test_causal_filter_preserves_all_history_cadence_before_year_subset(self):
        context = pd.DataFrame({"bar_index": [8, 10, 11, 14], "year": [2024, 2024, 2025, 2025],
                                "upper_half_close": [False, True, True, True]})
        original = context.copy(deep=True)
        accepted = accepted_context(context, "upper_half_close", 3)
        self.assertEqual(accepted.bar_index.tolist(), [10, 14])
        self.assertEqual(accepted.loc[accepted.year == 2025].bar_index.tolist(), [14])
        premature_subset = accepted_context(context.loc[context.year == 2025], "upper_half_close", 3)
        self.assertEqual(premature_subset.bar_index.tolist(), [11])
        pd.testing.assert_frame_equal(context, original)

    def test_sigma_scaled_score_and_missing_path(self):
        events = pd.DataFrame({"status": ["valid", "valid", "time_gap"],
                               "signal_sigma": [2., 2., 2.],
                               "mae_points": [2., 4., None],
                               "mfe_points": [6., 30., None],
                               "terminal_points": [1., -1., None],
                               "session_date": ["2025-01-01", "2025-01-02", "2025-01-03"],
                               "iso_week": ["2025-W01", "2025-W01", "2025-W01"]})
        scored = event_scores(events.iloc[:2])
        self.assertAlmostEqual(scored.clipped_score.iloc[0], 2.)
        self.assertAlmostEqual(scored.clipped_score.iloc[1], 8.)
        row = summarize(events, 3, 3)
        self.assertEqual(row["valid_n"], 2)
        self.assertEqual(row["excluded"], 1)
        self.assertAlmostEqual(row["mean_clipped_score"], 5.)


if __name__ == "__main__":
    unittest.main()
