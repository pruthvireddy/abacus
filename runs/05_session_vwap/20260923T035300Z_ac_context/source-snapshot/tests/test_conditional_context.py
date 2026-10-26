"""Causal boundary tests for the A/C follow-up context."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.conditional_context import (SCALE, c_pre_touch, clock_bin,
                                     opening_balance, prior_atr14, window_start)


class ContextTests(unittest.TestCase):
    def test_ny_clock_bins_and_dst_use_local_wall_time(self):
        self.assertEqual(clock_bin(0), "00-29")
        self.assertEqual(clock_bin(29), "00-29")
        self.assertEqual(clock_bin(30), "30-59")
        self.assertEqual(clock_bin(60), "60-119")
        self.assertEqual(window_start("2024-03-11", "ny").isoformat(),
                         "2024-03-11T13:30:00+00:00")
        self.assertEqual(window_start("2024-11-04", "ny").isoformat(),
                         "2024-11-04T14:30:00+00:00")

    def test_atr_uses_fourteen_prior_completed_days(self):
        days = pd.DataFrame({"high": [110 * 10**9] * 16,
                             "low": [100 * 10**9] * 16,
                             "close": [105 * 10**9] * 15 + [999 * 10**9]})
        atr = prior_atr14(days)
        self.assertTrue(atr.iloc[:14].isna().all())
        self.assertAlmostEqual(atr.iloc[14], 10.0)
        self.assertAlmostEqual(atr.iloc[15], 10.0)

    def test_opening_balance_requires_exact_complete_first_thirty_minutes(self):
        start = window_start("2024-06-03", "ny")
        times = pd.date_range(start, periods=30, freq="min")
        source = pd.DataFrame({"ts_event": times, "high": [102 * 10**9] * 30,
                               "low": [98 * 10**9] * 30})
        self.assertEqual(opening_balance(source, start), (102.0, 98.0))
        self.assertIsNone(opening_balance(source.iloc[1:].reset_index(drop=True), start))

    def test_c_peak_excludes_touch_bar_extreme(self):
        times = pd.date_range("2024-06-03T14:00:00Z", periods=3, freq="2min")
        frame = pd.DataFrame({"ts_event": times,
            "available_at": times + pd.Timedelta(minutes=2),
            "raw_symbol": ["ESM4"] * 3,
            "close": [102 * 10**9, 1015 * 10**8, 100 * 10**9],
            "high": [103 * 10**9, 102 * 10**9, 130 * 10**9],
            "low": [101 * 10**9, 100 * 10**9, 90 * 10**9],
            "globex_vwap": [100.0] * 3,
            "globex_sigma": [1.0] * 3,
            "globex_anchor_active": [True] * 3})
        event = pd.Series({"feature_index": 2, "departure_feature_index": 0,
                           "anchor": "globex", "side": 1, "raw_symbol": "ESM4",
                           "event_id": "C:test"})
        result = c_pre_touch(frame, event)
        self.assertAlmostEqual(result["c_peak_close_sigma"], 2.0)
        self.assertAlmostEqual(result["c_peak_frozen_extreme_sigma"], 3.0)
        self.assertEqual(result["c_departure_to_touch_minutes"], 2)


if __name__ == "__main__":
    unittest.main()
