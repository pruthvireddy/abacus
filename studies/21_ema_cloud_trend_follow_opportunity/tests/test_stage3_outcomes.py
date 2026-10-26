import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.stage3_masks import ScoringPeriod
from src.stage3_outcomes import score_period, NUMERIC, FLAGS, TIMES
from src.outcomes import score_outcomes
from test_stage3_masks import roster, events


class Authorization:
    def __init__(self, period="development", gate="abs_2p4", start="2018-01-01", end="2021-01-01"):
        self.period, self.start, self.end = period, start, end
        self.gates = (("ES", 3, "fast", gate),)
        self.calls = 0

    def validate(self, period, product, interval, touch_mode, gate_id):
        self.calls += 1
        if period != self.period or (product, interval, touch_mode, gate_id) not in self.gates:
            raise ValueError("outside authorization")


def score(bars, ev, horizons=(1, 3), p=None, auth=None):
    return score_period(bars, ev, horizons, p or ScoringPeriod("development", "fixture", "2019-01-01", "2019-01-02", 0),
        auth or Authorization(), product="ES", interval_minutes=3, touch_mode="fast",
        gate=dict(gate_id="abs_2p4", family="absolute", threshold=2.4))[0]


class OutcomesTest(unittest.TestCase):
    def test_vectorized_all_scientific_fields_equal_frozen_scalar_kernel(self):
        bars = roster(12)
        bars["high"] = [101., 104., 104., 102., 105., 103., 107., 104., 110., 106., 111., 108.]
        bars["low"] = [99., 98., 98., 97., 99., 98., 96., 99., 98., 95., 99., 96.]
        bars["close"] = [100., 103., 100., 99., 104., 100., 106., 102., 108., 105., 109., 107.]
        bars.loc[7, "known_closure_before"] = True
        ev = events(bars, [0, 2, 5]); ev.loc[1, ["direction", "side"]] = [-1, "Sell"]
        out = score(bars, ev, (1, 3, 5)).sort_values(["event_id", "horizon"])
        reference = score_outcomes(bars, ev, (1, 3, 5), 3, "2019-01-01", "2019-01-02").sort_values(["event_id", "horizon"])
        for c in NUMERIC + FLAGS + TIMES + ("status", "censor_reason", "elapsed_minutes", "crosses_closure", "same_session"):
            self.assertEqual(out[c].astype(str).tolist(), reference[c].astype(str).tolist(), c)

    def test_independent_scalar_path_excludes_entry_and_first_tied_attainment(self):
        bars = roster(6)
        bars.loc[0, ["high", "low"]] = [1000., 0.]
        bars.loc[1:2, ["high", "low"]] = [105., 98.]
        out = score(bars, events(bars, [0]), (2,)).iloc[0]
        self.assertEqual((out.mfe, out.mae, out.terminal_delta), (5., 2., 1.))
        self.assertEqual(out.mfe_attainment_start, bars.timestamp.iloc[1])
        self.assertEqual(out.mae_attainment_start, bars.timestamp.iloc[1])

    def test_invalid_future_before_contract_switch_and_empty_contract_is_quality(self):
        bars = roster(6)
        bars.loc[1, ["usable", "contract", "quality_reason", "high"]] = [False, None, "empty", np.nan]
        bars.loc[2, "contract"] = "ESM9"
        out = score(bars, events(bars, [0]), (1, 3))
        self.assertTrue(out.censor_reason.eq("invalid_future_slot:empty").all())
        self.assertTrue(out[list(NUMERIC)].isna().all().all())
        bars.loc[1, ["usable", "contract", "quality_reason", "high"]] = [True, "ESM9", "complete", 102.]
        self.assertEqual(score(bars, events(bars, [0]), (1,)).censor_reason.iloc[0], "contract_switch")

    def test_masks_precede_quality_paths_and_keep_accepted_metadata(self):
        bars = roster()
        bars.loc[100:, "high"] = np.nan
        out = score(bars, events(bars, [99, 101]), (1,), ScoringPeriod("development", "fixture", "2019-01-01", "2019-01-02"))
        self.assertEqual(out.status.tolist(), ["excluded", "censored"])
        self.assertEqual(out.mask_reason.tolist(), ["start_embargo", ""])
        self.assertEqual(out.event_id.tolist(), ["e99", "e101"])
        self.assertTrue(out[list(NUMERIC)].isna().all().all())

    def test_endpoint_purge_null_even_if_reserved_future_prices_are_finite(self):
        bars = roster(6)
        p = ScoringPeriod("development", "fixture", "2019-01-01", bars.available_at.iloc[2], 0)
        out = score(bars, events(bars, [0]), (2, 3), p)
        self.assertEqual(out.status.tolist(), ["completed", "excluded"])
        self.assertEqual(out.mask_reason.iloc[1], "period_endpoint_purge")
        self.assertTrue(out.loc[1, list(NUMERIC)].isna().all())

    def test_atr_zero_full_absolute_path_is_completed_without_normalization(self):
        bars = roster(6); ev = events(bars, [0]); ev["entry_atr"] = 0.
        out = score(bars, ev, (1,)).iloc[0]
        self.assertEqual(out.status, "completed")
        self.assertFalse(out.atr_support)
        self.assertEqual(out.mfe, 2.)
        self.assertTrue(np.isnan(out.mfe_atr))

    def test_no_default_authorization_or_reserved_scope(self):
        bars = roster(6); ev = events(bars, [0])
        with self.assertRaises(ValueError):
            score_period(bars, ev, [1], ScoringPeriod("development", "fixture", "2019-01-01", "2019-01-02", 0), None,
                product="ES", interval_minutes=3, touch_mode="fast", gate=dict(gate_id="abs_2p4", family="absolute", threshold=2.4))
        with self.assertRaises(ValueError):
            score(bars, ev, (1,), ScoringPeriod("validation", "2021H1", "2021-01-01", "2021-07-01", 0))
        with self.assertRaises(ValueError):
            score(bars, ev, (1,), auth=Authorization(end="2019-01-01"))

    def test_overlap_opposite_events_and_zero_excursion_timestamps(self):
        bars = roster(6); bars[["high", "low", "close"]] = 100.
        ev = events(bars, [0, 1]); ev.loc[1, ["direction", "side"]] = [-1, "Sell"]
        out = score(bars, ev, (2,))
        self.assertTrue(out.status.eq("completed").all())
        self.assertTrue(out.neutral.eq(True).all())
        self.assertTrue(out.mfe_mae_tie.eq(True).all())
        self.assertTrue(out.mfe_attainment_start.isna().all())

    def test_nullable_published_price_columns_and_mfe_mae_epsilon(self):
        bars = roster(6)
        for c in ("high", "low", "close"):
            bars[c] = bars[c].astype("Float64")
        bars.loc[1, ["high", "low"]] = [102., 98.]
        out = score(bars, events(bars, [0]), (1,)).iloc[0]
        self.assertTrue(out.mfe_mae_tie)
        self.assertFalse(out.mfe_gt_mae)
        bars.loc[1, "high"] = 102. + 3e-10
        self.assertTrue(score(bars, events(bars, [0]), (1,)).mfe_gt_mae.iloc[0])
        bars.loc[1, "high"] = pd.NA
        bars.loc[1, "quality_reason"] = "empty"
        self.assertEqual(score(bars, events(bars, [0]), (1,)).censor_reason.iloc[0], "invalid_future_slot:empty")


if __name__ == "__main__":
    unittest.main()
