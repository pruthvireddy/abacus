import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


SOURCE = Path(__file__).resolve().parents[1] / "src" / "stats.py"
spec = importlib.util.spec_from_file_location("overlay_stats", SOURCE)
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


class SessionStatsTests(unittest.TestCase):
    def test_half_open_session_boundaries(self):
        checks = {"2025-01-02 02:59:59": "asia",
                  "2025-01-02 03:00:00": "london",
                  "2025-07-02 09:29:59": "london",
                  "2025-07-02 09:30:00": "new_york",
                  "2025-07-02 15:59:59": "new_york",
                  "2025-07-02 16:00:00": "transition",
                  "2025-07-02 18:00:00": "asia"}
        self.assertEqual({x: stats.segment(x) for x in checks}, checks)

    def test_new_york_subwindows_combine(self):
        self.assertEqual(stats.named_window("ny_morning"), "new_york")
        self.assertEqual(stats.named_window("ny_afternoon"), "new_york")
        self.assertEqual(stats.named_window("london_pre_ny"), "london")

    def test_rate_count_and_session_cluster_interval(self):
        data = pd.DataFrame({"session_date": ["a", "a", "b", "b"],
                             "value": [True, False, True, True]})
        row = stats.estimate(stats.grouped(data, data.value), scale=100, clamp_rate=True)
        self.assertEqual((row["numerator"], row["denominator"], row["session_dates"]),
                         (3, 4, 2))
        self.assertEqual(row["estimate"], 75)
        self.assertLessEqual(row["ci_high"], 100)

    def test_joint_contrast_uses_shared_dates(self):
        a = pd.DataFrame({"session_date": ["a", "b"], "value": [1, 0]})
        b = pd.DataFrame({"session_date": ["a", "b"], "value": [0, 1]})
        result = stats.difference(stats.grouped(a, a.value), stats.grouped(b, b.value),
                                  scale=100, family=42)
        self.assertEqual(result["difference"], 0)
        self.assertLess(result["family_ci_low"], 0)
        self.assertGreater(result["family_ci_high"], 0)

    def test_policy_zero_stays_in_opportunity_denominator(self):
        data = pd.DataFrame({"session_date": ["a", "a", "b", "b"],
                             "return_ticks": [3, 0, -2, 0],
                             "traded": [True, False, True, False]})
        net = data.return_ticks - 2 * data.traded.astype(int)
        row = stats.estimate(stats.grouped(data, net))
        self.assertEqual(row["denominator"], 4)
        self.assertEqual(row["estimate"], -0.75)

    def test_empty_and_nonfinite_rejected(self):
        empty = pd.DataFrame({"session_date": []})
        self.assertEqual(stats.estimate(stats.grouped(empty, []))["denominator"], 0)
        with self.assertRaises(ValueError):
            stats.grouped(pd.DataFrame({"session_date": ["a"]}), np.array([np.nan]))


if __name__ == "__main__":
    unittest.main()
