import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import generate_events
from src.outcomes import score_outcomes
from test_engine import fixture


def observation(direction=1):
    bars = fixture(7)
    bars.loc[1, ["low", "high", "close"]] = [-1000., 1000., 100.]
    if direction == -1:
        bars.ema20 = 97.
        bars.loc[0, ["low", "high"]] = [94., 96.]
    bars.loc[2:, "high"] = [105., 104., 106., 103., 105.]
    bars.loc[2:, "low"] = [97., 98., 97., 99., 98.]
    bars.loc[2:, "close"] = [102., 100., 103., 100., 99.]
    _, events = generate_events(bars, 5)
    return bars, events.iloc[[0]].copy()


class OutcomesTest(unittest.TestCase):
    def test_entry_wicks_excluded_and_long_short_formulas(self):
        for direction, expected in [(1, (6., 3., 3.)), (-1, (3., 6., -3.))]:
            bars, event = observation(direction)
            row = score_outcomes(bars, event, [3], 5).iloc[0]
            self.assertEqual(tuple(row[m] for m in ("mfe", "mae", "terminal_delta")), expected)
            self.assertEqual(row.mfe_atr, expected[0] / 2.)
            self.assertEqual(row.horizon_minutes, 15)
            self.assertEqual(row.elapsed_minutes, 15)

    def test_first_extremum_attainment_tie_and_zero_has_no_attainment(self):
        bars, event = observation()
        row = score_outcomes(bars, event, [3], 5).iloc[0]
        self.assertEqual(row.mae_attainment_start, bars.timestamp.iloc[2])
        bars.loc[2:, ["high", "low", "close"]] = 100.
        row = score_outcomes(bars, event, [3], 5).iloc[0]
        self.assertEqual(row.mfe, 0.)
        self.assertTrue(pd.isna(row.mfe_attainment_start))
        self.assertTrue(row.neutral)
        self.assertTrue(row.mfe_mae_tie)
        self.assertFalse(row.mfe_gt_mae)

    def test_partial_unknown_slot_censors_longer_but_preserves_short(self):
        bars, event = observation()
        bars.loc[4, "usable"] = False
        bars.loc[4, "quality_reason"] = "missing_minute"
        out = score_outcomes(bars, event, [2, 3, 5], 5)
        self.assertEqual(out.status.tolist(), ["completed", "censored", "censored"])
        self.assertEqual(out.censor_reason.iloc[1], "invalid_future_slot:missing_minute")
        self.assertTrue(out.mfe.iloc[1:].isna().all())
        self.assertTrue(out.favorable.iloc[1:].isna().all())

    def test_roll_censors_without_adjustment_or_state_feedback(self):
        bars, event = observation()
        before = event.copy(deep=True)
        bars.loc[4:, "contract"] = "B"
        out = score_outcomes(bars, event, [2, 3], 5)
        self.assertEqual(out.censor_reason.tolist(), ["", "contract_switch"])
        pd.testing.assert_frame_equal(event, before)

    def test_empty_and_mixed_unknown_contract_are_quality_censors_not_rolls(self):
        for quality in ("empty", "mixed_contract"):
            bars, event = observation()
            bars.loc[3, "usable"] = False
            bars.loc[3, "contract"] = None
            bars.loc[3, "quality_reason"] = quality
            bars.loc[3, ["high", "low", "close"]] = np.nan
            row = score_outcomes(bars, event, [3], 5).iloc[0]
            self.assertEqual(row.censor_reason, "invalid_future_slot:" + quality)

    def test_known_closure_keeps_active_slots_and_records_elapsed(self):
        bars, event = observation()
        bars.loc[3:, "timestamp"] += pd.Timedelta(hours=1)
        bars.loc[3:, "available_at"] += pd.Timedelta(hours=1)
        bars.loc[3, "known_closure_before"] = True
        bars.loc[3:, "session"] = "2019-01-03"
        row = score_outcomes(bars, event, [3], 5).iloc[0]
        self.assertEqual(row.horizon_minutes, 15)
        self.assertEqual(row.elapsed_minutes, 75)
        self.assertTrue(row.crosses_closure)
        self.assertFalse(row.same_session)

    def test_development_boundary_and_data_edge_remain_null(self):
        bars, event = observation()
        out = score_outcomes(bars, event, [100], 5)
        self.assertEqual(out.censor_reason.iloc[0], "data_edge")
        out = score_outcomes(bars, event, [100], 5, roster_end_is_endpoint=True)
        self.assertEqual(out.censor_reason.iloc[0], "development_endpoint")
        endpoint = bars.available_at.iloc[3]
        out = score_outcomes(bars, event, [2, 3], 5, endpoint=endpoint)
        self.assertEqual(out.status.tolist(), ["completed", "censored"])

    def test_reserved_and_optional_earlier_events_are_refused(self):
        bars, event = observation()
        for year in (2017, 2021, 2026):
            bad = event.copy()
            bad.timestamp = bad.timestamp.map(lambda t: t.replace(year=year))
            with self.assertRaisesRegex(ValueError, "development"):
                score_outcomes(bars, bad, [3], 5)

    def test_overlap_and_opposite_event_do_not_end_observation(self):
        bars, event = observation()
        second = event.copy()
        second.event_id = "opposite"
        second.signal_idx = 2
        second.timestamp = bars.timestamp.iloc[2]
        second.entry_at = bars.available_at.iloc[2]
        second.reference_price = bars.close.iloc[2]
        second.direction = -1
        second.side = "Sell"
        out = score_outcomes(bars, pd.concat([event, second], ignore_index=True), [3], 5)
        self.assertEqual(len(out), 2)
        self.assertTrue(out.status.eq("completed").all())
        self.assertEqual(out.mfe.iloc[0], 6.)

    def test_mfe_mae_source_tolerance_and_strict_terminal_sign(self):
        bars, event = observation()
        bars.loc[2, ["high", "low", "close"]] = [102. + 1e-11, 98., 100. + 1e-11]
        row = score_outcomes(bars, event, [1], 5).iloc[0]
        self.assertFalse(row.mfe_gt_mae)
        self.assertTrue(row.mfe_mae_tie)
        self.assertTrue(row.favorable)


if __name__ == "__main__":
    unittest.main()
