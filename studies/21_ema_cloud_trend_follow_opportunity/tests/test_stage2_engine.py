import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import generate_events
from src.outcomes import score_outcomes
from src.stage2_engine import generate_streams


def fixture(n=6, interval=5, start="2019-01-02 14:00Z"):
    times = pd.date_range(start, periods=n, freq=f"{interval}min")
    return pd.DataFrame(dict(timestamp=times, available_at=times + pd.Timedelta(minutes=interval),
        product="ES", contract="A", open=105., high=106., low=104., close=105., volume=10.,
        usable=True, quality_reason="complete", session="2019-01-02", ema20=103., ema50=100.,
        atr14=2., feature_valid=True, feature_reset=False, consecutive_count=250,
        known_closure_before=False, feature_source_timestamp=times, feature_available_at=times + pd.Timedelta(minutes=interval),
        feature_contract="A", interval_minutes=interval))


class IndependentStreamsTest(unittest.TestCase):
    def test_fast_touch_then_dual_accepts_slow_only_without_slow_consumption(self):
        bars = fixture(4)
        bars.loc[1, ["low", "high"]] = [102., 105.]
        bars.loc[2:, ["low", "high"]] = [99., 105.]
        technical, events = generate_streams(bars, 5)
        self.assertEqual(events[["touch_mode", "signal_idx"]].values.tolist(), [["fast", 1], ["slow", 2]])
        self.assertEqual(technical.loc[technical.touch_mode.eq("slow"), "armed_before"].tolist(), [False, True, True, False])
        self.assertEqual(technical.loc[technical.touch_mode.eq("fast"), "armed_before"].tolist(), [False, True, False, False])

    def test_width_rejected_fast_consumes_only_fast_and_slow_can_accept(self):
        bars = fixture(3)
        bars.loc[1, ["ema20", "low", "high"]] = [102., 101., 105.]
        bars.loc[2, ["low", "high"]] = [99., 105.]
        technical, events = generate_streams(bars, 5)
        rejected = technical.loc[technical.touch_mode.eq("fast")].iloc[1]
        self.assertEqual(rejected.suppression_reason, "width_below_minimum")
        self.assertFalse(rejected.armed_after)
        self.assertEqual(events.touch_mode.tolist(), ["slow"])

    def test_slow_only_touch_consumes_fast_gap_and_dual_ids_never_collide(self):
        bars = fixture(5)
        bars.loc[1, ["low", "high"]] = [99., 102.]
        bars.loc[2, ["low", "high"]] = [102., 105.]
        bars.loc[4, ["low", "high"]] = [99., 105.]
        technical, events = generate_streams(bars, 5)
        self.assertEqual(events[["touch_mode", "signal_idx"]].values.tolist(), [["slow", 1], ["fast", 4], ["slow", 4]])
        self.assertEqual(technical.loc[technical.touch_mode.eq("fast"), "suppression_reason"].iloc[1], "gap_penetration")
        self.assertEqual(events.event_id.nunique(), 3)
        self.assertTrue(events.event_id.iloc[1].endswith("|fast"))
        self.assertTrue(events.event_id.iloc[2].endswith("|slow"))

    def test_exact_slow_every_field_state_and_event_id_against_inherited_engine(self):
        bars = fixture(8)
        bars.loc[[1, 2, 4, 7], ["low", "high"]] = [99., 105.]
        bars.loc[4, "ema20"] = 102.
        bars.loc[5, "feature_valid"] = False
        original_technical, original_events = generate_events(bars, 5)
        technical, events = generate_streams(bars, 5)
        slow_technical = technical.loc[technical.touch_mode.eq("slow"), original_technical.columns].reset_index(drop=True)
        slow_events = events.loc[events.touch_mode.eq("slow"), original_events.columns].reset_index(drop=True)
        slow_events["stage"] = 1
        pd.testing.assert_frame_equal(original_technical, slow_technical, check_exact=True)
        pd.testing.assert_frame_equal(original_events, slow_events, check_exact=True)

    def test_both_streams_clear_at_quality_equality_roll_and_direction_changes(self):
        for change in ("invalid", "equal", "roll", "reset", "direction"):
            bars = fixture(2)
            bars.loc[1, ["low", "high"]] = [96., 105.]
            if change == "invalid": bars.loc[1, "feature_valid"] = False
            if change == "equal": bars.loc[1, "ema20"] = 100.
            if change == "roll": bars.loc[1, "contract"] = "B"
            if change == "reset": bars.loc[1, "feature_reset"] = True
            if change == "direction": bars.loc[1, "ema20"] = 97.
            technical, events = generate_streams(bars, 5)
            self.assertTrue(events.empty, change)
            self.assertFalse(technical.loc[technical.signal_idx.eq(1), "armed_before"].any(), change)

    def test_three_minute_repeated_source_reset_applies_once_and_prefix_is_causal(self):
        bars = fixture(5, interval=3)
        bars.feature_reset = True
        bars.feature_source_timestamp = bars.timestamp.iloc[0]
        bars.loc[[1, 3], ["low", "high"]] = [99., 105.]
        technical, events = generate_streams(bars, 3)
        prefix, prefix_events = generate_streams(bars.iloc[:4], 3)
        pd.testing.assert_frame_equal(technical.loc[technical.signal_idx.lt(4)].reset_index(drop=True), prefix, check_exact=True)
        pd.testing.assert_frame_equal(events.loc[events.signal_idx.lt(4)].reset_index(drop=True), prefix_events, check_exact=True)
        self.assertEqual(len(prefix_events), 4)

    def test_sell_and_width_epsilon_and_null_outcomes_are_inherited(self):
        bars = fixture(4)
        bars.ema20 = 97.6
        bars.loc[0, ["low", "high"]] = [95., 96.]
        bars.loc[1, ["low", "high"]] = [97., 101.]
        bars.loc[2, ["low", "high", "close"]] = [95., 98., 96.]
        bars.loc[3, ["low", "high", "close"]] = [np.nan, np.nan, np.nan]
        bars.loc[3, "usable"] = False
        bars.loc[3, "contract"] = None
        bars.loc[3, "quality_reason"] = "empty"
        _, events = generate_streams(bars, 5)
        self.assertEqual(events.touch_mode.tolist(), ["fast", "slow"])
        self.assertEqual(events.side.tolist(), ["Sell", "Sell"])
        paths = score_outcomes(bars, events, horizons=[1, 2], interval_minutes=5)
        complete = paths.loc[paths.horizon.eq(1)]
        self.assertEqual(complete.mfe.tolist(), [10., 10.])
        self.assertEqual(complete.mae.tolist(), [0., 0.])
        self.assertEqual(paths.loc[paths.horizon.eq(2), "censor_reason"].tolist(), ["invalid_future_slot:empty"] * 2)
        self.assertTrue(paths.loc[paths.horizon.eq(2), "favorable"].isna().all())


if __name__ == "__main__": unittest.main()
