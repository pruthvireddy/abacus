import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import generate_events
from src.outcomes import score_outcomes
from src.reference import scalar_acceptance, scalar_outcomes, reconcile_scalar
from test_engine import fixture
from test_outcomes import observation


class IndependentReferenceTest(unittest.TestCase):
    def test_random_state_sequences_match_independent_scalar_ids(self):
        rng = np.random.default_rng(20261010)
        for _ in range(60):
            bars = fixture(30)
            bars["ema20"] = rng.choice([97., 100., 102., 103.], len(bars))
            bars["low"] = rng.choice([95., 99., 100., 102., 104.], len(bars))
            bars["high"] = bars.low + rng.choice([1., 3., 7.], len(bars))
            bars["feature_valid"] = rng.random(len(bars)) > .05
            bars["contract"] = ["A"] * 15 + ["B"] * 15
            _, events = generate_events(bars, 5)
            self.assertEqual(events.event_id.tolist(), scalar_acceptance(bars, 5))

    def test_independent_scalar_entire_population_long_short_partial_roll_endpoint(self):
        for direction in (1, -1):
            for defect in ("none", "partial", "empty", "roll"):
                bars, event = observation(direction)
                if defect == "partial":
                    bars.loc[4, "usable"] = False
                elif defect == "empty":
                    bars.loc[4, "usable"] = False
                    bars.loc[4, "contract"] = None
                    bars.loc[4, ["high", "low", "close"]] = np.nan
                elif defect == "roll":
                    bars.loc[4:, "contract"] = "B"
                full = score_outcomes(bars, event, [1, 2, 3, 5, 100], 5)
                independent = scalar_outcomes(bars, event, [1, 2, 3, 5, 100])
                for col in ("status", "censor_reason", "mfe", "mae", "terminal_delta", "mfe_atr", "mfe_gt_mae", "mfe_attainment_start"):
                    pd.testing.assert_series_equal(full[col], independent[col], check_dtype=False, check_names=False)

    def test_full_reconciliation_detects_changed_outcome(self):
        bars, event = observation()
        _, all_events = generate_events(bars, 5)
        out = score_outcomes(bars, all_events, [1, 3], 5)
        receipt = reconcile_scalar(bars, bars, all_events, out, 5, [1, 3])
        self.assertTrue(receipt["scalar_agreement"])
        out.loc[0, "mfe"] += 1.
        with self.assertRaisesRegex(AssertionError, "mfe differs"):
            reconcile_scalar(bars, bars, all_events, out, 5, [1, 3])


if __name__ == "__main__":
    unittest.main()
