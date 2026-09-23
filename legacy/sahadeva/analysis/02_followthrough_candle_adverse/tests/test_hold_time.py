from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from followthrough_adverse.core import detect_reversals
from followthrough_adverse.hold_time import compute_hold_events, reconcile_hold_sample


CONFIG = {
    "primary_reference": "follow-through candle open",
    "timing_status": "unresolved",
    "hold_time": {"strict_additional_bars": 2, "eventual_search_horizon_bars": 3},
}


def make_bars(rows, timestamps=None, sequences=None):
    frame = pd.DataFrame(rows, columns=["open_ticks", "high_ticks", "low_ticks", "close_ticks"])
    n = len(frame)
    frame["direction"] = np.sign(frame["close_ticks"] - frame["open_ticks"]).astype(int)
    if timestamps is None:
        timestamps = pd.date_range("2026-01-01 10:00:00", periods=n, freq="min")
    if sequences is None:
        sequences = [1] * n
    for column in ("open", "high", "low", "close"):
        frame[column] = frame[f"{column}_ticks"]
    return frame.assign(
        source_row=np.arange(1, n + 1),
        timestamp=pd.Series(timestamps).dt.strftime("%Y-%d-%m %H:%M:%S"),
        parsed_timestamp=pd.Series(timestamps),
        export_date="2026-01-01",
        valid_row=True,
        bar_included=True,
        split="development",
        sequence_id=sequences,
        source_file="synthetic.csv",
        source_sha256="abc",
        asset="ES",
        contract="ESU6",
        range_setting=4,
        chart_identity_status="provisional",
    )


class HoldTimeTests(unittest.TestCase):
    def test_strict_two_more_success_and_proxy_time(self):
        bars = make_bars(
            [
                (102, 102, 100, 101),
                (100, 102, 100, 101),
                (101, 103, 101, 102),
                (102, 104, 102, 103),
                (103, 105, 103, 104),
                (104, 104, 102, 103),
            ]
        )
        hold = compute_hold_events(bars, detect_reversals(bars, CONFIG), CONFIG).iloc[0]
        self.assertTrue(hold["strict_eligible_two_more"])
        self.assertTrue(hold["strict_two_more_success"])
        self.assertEqual(hold["strict_bars_to_target"], 2)
        self.assertEqual(hold["strict_hold_proxy_minutes"], 2.0)

    def test_eventual_pair_allows_intervening_bar(self):
        bars = make_bars(
            [
                (102, 102, 100, 101),
                (100, 102, 100, 101),
                (101, 103, 101, 102),
                (103, 103, 101, 102),
                (102, 104, 102, 103),
                (103, 105, 103, 104),
            ]
        )
        hold = compute_hold_events(bars, detect_reversals(bars, CONFIG), CONFIG).iloc[0]
        self.assertFalse(hold["strict_two_more_success"])
        self.assertTrue(hold["eventual_pair_success"])
        self.assertEqual(hold["eventual_bars_to_target"], 3)
        self.assertEqual(hold["eventual_hold_proxy_minutes"], 3.0)

    def test_sequence_boundary_excludes_incomplete_targets(self):
        bars = make_bars(
            [
                (102, 102, 100, 101),
                (100, 102, 100, 101),
                (101, 103, 101, 102),
                (102, 104, 102, 103),
                (103, 105, 103, 104),
                (104, 104, 102, 103),
            ],
            sequences=[1, 1, 1, 1, 2, 2],
        )
        hold = compute_hold_events(bars, detect_reversals(bars, CONFIG), CONFIG).iloc[0]
        self.assertFalse(hold["strict_eligible_two_more"])
        self.assertFalse(hold["eventual_eligible_horizon"])

    def test_tied_timestamps_are_preserved_as_zero(self):
        timestamps = pd.to_datetime(["2026-01-01 10:00:00"] * 5 + ["2026-01-01 10:01:00"])
        bars = make_bars(
            [
                (102, 102, 100, 101),
                (100, 102, 100, 101),
                (101, 103, 101, 102),
                (102, 104, 102, 103),
                (103, 105, 103, 104),
                (104, 104, 102, 103),
            ],
            timestamps=timestamps,
        )
        hold = compute_hold_events(bars, detect_reversals(bars, CONFIG), CONFIG).iloc[0]
        self.assertEqual(hold["strict_hold_proxy_seconds"], 0.0)

    def test_independent_reconciliation(self):
        bars = make_bars(
            [
                (102, 102, 100, 101),
                (100, 102, 100, 101),
                (101, 103, 101, 102),
                (103, 103, 101, 102),
                (102, 104, 102, 103),
                (103, 105, 103, 104),
            ]
        )
        hold = compute_hold_events(bars, detect_reversals(bars, CONFIG), CONFIG)
        reconciliation, check = reconcile_hold_sample(bars, hold, CONFIG, seed=7, sample_size=1)
        self.assertTrue(check["all_match"])
        self.assertTrue(reconciliation.iloc[0]["all_match"])


if __name__ == "__main__":
    unittest.main()
