from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from reversal_study.events import detect_events, detect_events_bruteforce


CONFIG = {"thresholds": [1, 2, 3, 4, 5, 10]}


def bars_from_directions(directions, sequences=None):
    n = len(directions)
    if sequences is None:
        sequences = [1] * n
    opens = np.full(n, 100, dtype=int)
    closes = opens + np.asarray(directions, dtype=int)
    return pd.DataFrame(
        {
            "source_sha256": ["abc"] * n,
            "source_file": ["synthetic.csv"] * n,
            "source_row": np.arange(1, n + 1),
            "timestamp": [f"2026-01-01 00:00:{i:02d}" for i in range(n)],
            "parsed_timestamp": pd.date_range("2026-01-01", periods=n, freq="s"),
            "export_date": ["2026-01-01"] * n,
            "open": opens,
            "high": np.maximum(opens, closes),
            "low": np.minimum(opens, closes),
            "close": closes,
            "open_ticks": opens,
            "high_ticks": np.maximum(opens, closes),
            "low_ticks": np.minimum(opens, closes),
            "close_ticks": closes,
            "valid_row": [True] * n,
            "bar_included": [True] * n,
            "direction": directions,
            "asset": ["ES"] * n,
            "contract": ["ESU6"] * n,
            "range_setting": [4] * n,
            "chart_type": ["Range XV (filename label)"] * n,
            "chart_identity_status": ["provisional"] * n,
            "timing_status": ["unverified"] * n,
            "split": ["development"] * n,
            "sequence_id": sequences,
        }
    )


class EventTests(unittest.TestCase):
    def test_reversal_and_follow_through_exclude_signal(self):
        bars = bars_from_directions([-1, -1, 1, 1, 1, 1, -1])
        events, _ = detect_events(bars, CONFIG)
        signal = events.loc[events["bar_index"].eq(2)].iloc[0]
        self.assertEqual(signal["prior_opposite_run"], 2)
        self.assertEqual(signal["observed_L"], 3)
        self.assertTrue(signal["success_L_ge_3"])
        self.assertFalse(signal["success_L_ge_4"])
        self.assertEqual(signal["T_including_reversal"], 4)

    def test_doji_breaks_adjacency_and_runs(self):
        bars = bars_from_directions([-1, 0, 1, 1, 0, -1])
        events, _ = detect_events(bars, CONFIG)
        self.assertTrue(events.empty)

    def test_sequence_boundary_prevents_reversal(self):
        bars = bars_from_directions([-1, 1, 1], sequences=[1, 2, 2])
        events, _ = detect_events(bars, CONFIG)
        self.assertTrue(events.empty)

    def test_incomplete_window_is_excluded_not_failed(self):
        bars = bars_from_directions([-1, 1, 1])
        events, _ = detect_events(bars, CONFIG)
        signal = events.iloc[0]
        self.assertTrue(signal["eligible_L_ge_1"])
        self.assertTrue(signal["success_L_ge_1"])
        self.assertFalse(signal["eligible_L_ge_2"])
        self.assertTrue(pd.isna(signal["success_L_ge_2"]))
        self.assertTrue(signal["run_censored"])
        self.assertEqual(signal["observed_L"], 1)

    def test_optimized_matches_bruteforce(self):
        bars = bars_from_directions([-1, -1, 1, 1, -1, -1, 1, 1, 1])
        events, _ = detect_events(bars, CONFIG)
        simple = detect_events_bruteforce(bars, events["bar_index"].astype(int).tolist())
        for event, brute in zip(events.itertuples(index=False), simple):
            self.assertEqual(event.prior_opposite_run, brute["prior_opposite_run"])
            self.assertEqual(event.observed_L, brute["observed_L"])
            self.assertEqual(event.run_censored, brute["run_censored"])


if __name__ == "__main__":
    unittest.main()

