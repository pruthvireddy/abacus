import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import generate_events, map_features


def fixture(n=6, interval=5, start="2019-01-02 14:00Z"):
    timestamps = pd.date_range(start, periods=n, freq=f"{interval}min")
    return pd.DataFrame(dict(timestamp=timestamps, available_at=timestamps + pd.Timedelta(minutes=interval),
        product="ES", contract="A", open=105., high=106., low=104., close=105., volume=10,
        usable=True, quality_reason="complete", session="2019-01-02", ema20=103., ema50=100.,
        atr14=2., feature_valid=True, feature_reset=False, consecutive_count=250,
        known_closure_before=False))


class FeatureMappingTest(unittest.TestCase):
    def test_awkward_three_five_alignment_freezes_at_open(self):
        five = fixture(5, start="2019-01-02 14:20Z")
        five["ema50"] = [90., 91., 92., 93., 94.]
        three = fixture(4, interval=3, start="2019-01-02 14:30Z")
        mapped = map_features(three, five, 3)
        self.assertEqual(mapped.ema50.tolist(), [91., 91., 92., 92.])
        self.assertEqual(mapped.feature_source_timestamp.iloc[1], pd.Timestamp("2019-01-02 14:25Z"))
        self.assertEqual(mapped.feature_available_at.iloc[1], pd.Timestamp("2019-01-02 14:30Z"))
        self.assertEqual(mapped.source_age_minutes.iloc[1], 3.)

    def test_five_uses_current_completed_cloud(self):
        bars = fixture(3)
        bars.ema50 = [100., 101., 102.]
        mapped = map_features(bars, bars, 5)
        self.assertEqual(mapped.ema50.tolist(), [100., 101., 102.])
        pd.testing.assert_series_equal(mapped.feature_source_timestamp, bars.timestamp, check_names=False)

    def test_missing_latest_slot_never_carries_old_ready_cloud(self):
        five = fixture(4)
        five.loc[1, ["feature_valid", "usable"]] = False
        three = fixture(1, interval=3, start="2019-01-02 14:12Z")
        mapped = map_features(three, five, 3)
        self.assertFalse(mapped.feature_valid.iloc[0])
        self.assertTrue(pd.isna(mapped.ema50.iloc[0]))
        self.assertEqual(mapped.feature_source_timestamp.iloc[0], five.timestamp.iloc[1])

    def test_contract_mismatch_and_no_completed_source_are_undefined(self):
        five = fixture(2)
        signal = fixture(2, interval=3, start="2019-01-02 14:03Z")
        signal.contract = "B"
        mapped = map_features(signal, five, 3)
        self.assertEqual(mapped.map_reason.tolist(), ["no_completed_source", "contract_mismatch"])
        self.assertFalse(mapped.feature_valid.any())

    def test_known_closure_can_map_last_scheduled_source(self):
        five = fixture(1, start="2019-01-02 21:55Z")
        three = fixture(1, interval=3, start="2019-01-02 23:00Z")
        three.known_closure_before = True
        mapped = map_features(three, five, 3)
        self.assertTrue(mapped.feature_valid.iloc[0])
        self.assertEqual(mapped.source_age_minutes.iloc[0], 60.)

    def test_duplicate_and_reordered_inputs_fail(self):
        bars = fixture(3)
        for bad in (pd.concat([bars, bars.iloc[[0]]], ignore_index=True), bars.iloc[::-1]):
            with self.assertRaises(ValueError):
                map_features(bad, bars, 5)

    def test_mapping_prefix_invariance_when_future_features_change(self):
        five = fixture(10)
        three = fixture(8, interval=3, start="2019-01-02 14:06Z")
        before = map_features(three, five, 3)
        five.loc[7:, ["ema20", "ema50", "atr14"]] = 10000.
        after = map_features(three, five, 3)
        pd.testing.assert_frame_equal(before, after)


class SlowStateTest(unittest.TestCase):
    def test_fast_only_does_not_consume_and_only_one_slow_touch(self):
        bars = fixture(4)
        bars.loc[1, ["low", "high"]] = [102., 105.]
        bars.loc[[2, 3], ["low", "high"]] = [99., 102.]
        technical, events = generate_events(bars, 5)
        self.assertEqual(events.signal_idx.tolist(), [2])
        self.assertEqual(technical.armed_before.tolist(), [False, True, True, False])
        self.assertEqual(technical.suppression_reason.tolist(), ["no_touch", "fast_only", "accepted", "not_armed"])

    def test_rejected_width_touch_consumes_and_departure_rearms(self):
        bars = fixture(5)
        bars.loc[[1, 2, 4], ["low", "high"]] = [99., 102.]
        bars.loc[1, "ema20"] = 102.
        technical, events = generate_events(bars, 5)
        self.assertEqual(technical.suppression_reason.iloc[1], "width_below_minimum")
        self.assertFalse(technical.armed_after.iloc[1])
        self.assertEqual(events.signal_idx.tolist(), [4])
        self.assertEqual(events.episode_id.tolist(), [2])

    def test_gap_penetration_consumes_without_geometric_touch(self):
        bars = fixture(3)
        bars.loc[1, ["low", "high"]] = [95., 99.]
        bars.loc[2, ["low", "high"]] = [99., 102.]
        technical, events = generate_events(bars, 5)
        self.assertEqual(technical.suppression_reason.iloc[1], "gap_penetration")
        self.assertTrue(technical.penetration.iloc[1])
        self.assertFalse(technical.technical_candidate.iloc[1])
        self.assertEqual(len(events), 0)

    def test_inclusive_touch_threshold_epsilon_without_rounding(self):
        for width, expected in [(2.4, 1), (2.4 - 1e-10, 1), (2.4 - 1e-8, 0)]:
            bars = fixture(2)
            bars.ema20 = 100 + width
            bars.loc[1, ["low", "high"]] = [100., 102.]
            _, events = generate_events(bars, 5)
            self.assertEqual(len(events), expected)

    def test_direction_change_clears_before_touch_sell_departure_arms(self):
        bars = fixture(4)
        bars.loc[1:, "ema20"] = 97.
        bars.loc[1, ["low", "high"]] = [99., 101.]
        bars.loc[2, ["low", "high"]] = [95., 96.]
        bars.loc[3, ["low", "high"]] = [99., 101.]
        _, events = generate_events(bars, 5)
        self.assertEqual(events.signal_idx.tolist(), [3])
        self.assertEqual(events.side.tolist(), ["Sell"])

    def test_invalid_equality_roll_each_clear_setup(self):
        for case in ("invalid", "equal", "roll", "reset"):
            bars = fixture(3)
            bars.loc[2, ["low", "high"]] = [99., 102.]
            if case == "invalid":
                bars.loc[1, "feature_valid"] = False
            elif case == "equal":
                bars.loc[1, "ema20"] = 100.
            elif case == "roll":
                bars.loc[2, "contract"] = "B"
            else:
                bars.loc[2, "feature_reset"] = True
            if case in ("invalid", "equal"):
                bars.loc[1, ["low", "high"]] = [99., 102.]
            _, events = generate_events(bars, 5)
            self.assertEqual(len(events), 0, case)

    def test_repeated_source_reset_is_applied_once_on_three_minute_mapping(self):
        bars = fixture(2, interval=3)
        bars.feature_reset = True
        bars["feature_source_timestamp"] = bars.timestamp.iloc[0]
        bars.loc[1, ["low", "high"]] = [99., 102.]
        _, events = generate_events(bars, 3)
        self.assertEqual(len(events), 1)

    def test_prefix_invariance_and_year_boundary_state(self):
        bars = fixture(6, start="2020-01-01 04:55Z")
        bars.loc[[1, 3, 5], ["low", "high"]] = [99., 102.]
        full, events = generate_events(bars, 5)
        prefix, prefix_events = generate_events(bars.iloc[:4], 5)
        for col in ("armed_before", "armed_after", "accepted", "episode_id"):
            self.assertEqual(full[col].iloc[:4].tolist(), prefix[col].tolist())
        self.assertEqual(events.event_id.iloc[:2].tolist(), prefix_events.event_id.tolist())

    def test_ny_open_strata_are_causal_and_dst_offsets_preserved(self):
        for start, hour in [("2019-03-08 14:00Z", 9), ("2019-03-11 13:00Z", 9)]:
            bars = fixture(2, start=start)
            bars.loc[1, ["low", "high"]] = [99., 102.]
            _, events = generate_events(bars, 5)
            self.assertEqual(events.hour.iloc[0], hour)
            self.assertEqual(events.time_stratum.iloc[0], "US")
            self.assertLessEqual(events.timestamp.iloc[0], events.entry_at.iloc[0])


if __name__ == "__main__":
    unittest.main()
