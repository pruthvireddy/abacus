from __future__ import annotations

import unittest

import pandas as pd

from followthrough_adverse.stats import numeric_summary, session_bootstrap_mean


class StatsTests(unittest.TestCase):
    def test_numeric_summary(self):
        result = numeric_summary(pd.Series([0, 1, 2, 3, 4]))
        self.assertEqual(result["n"], 5)
        self.assertEqual(result["mean"], 2)
        self.assertEqual(result["median"], 2)
        self.assertEqual(result["p90"], 3.6)

    def test_bootstrap_mean_reconciles_constant_values(self):
        frame = pd.DataFrame(
            {"export_date": ["d1", "d1", "d2"], "value": [3.0, 3.0, 3.0]}
        )
        low, high, reps = session_bootstrap_mean(frame, "value", 2000, 17)
        self.assertEqual(low, 3.0)
        self.assertEqual(high, 3.0)
        self.assertEqual(reps, 2000)


if __name__ == "__main__":
    unittest.main()

