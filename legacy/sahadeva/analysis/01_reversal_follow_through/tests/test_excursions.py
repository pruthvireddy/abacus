from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from reversal_study.events import detect_events
from reversal_study.excursions import _window_metrics, add_excursions_and_timing


CONFIG = {"thresholds": [1, 2, 3, 4, 5, 10], "fixed_horizons": [1, 3, 5, 10, 20]}


def excursion_bars():
    values = [
        (101, 102, 99, 100),
        (99, 150, 50, 100),
        (100, 103, 99, 101),
        (101, 104, 98, 102),
        (102, 102, 97, 101),
    ]
    frame = pd.DataFrame(values, columns=["open_ticks", "high_ticks", "low_ticks", "close_ticks"])
    for column in ("open", "high", "low", "close"):
        frame[column] = frame[f"{column}_ticks"]
    frame["direction"] = np.sign(frame["close_ticks"] - frame["open_ticks"]).astype(int)
    n = len(frame)
    frame = frame.assign(
        source_sha256="abc",
        source_file="synthetic.csv",
        source_row=np.arange(1, n + 1),
        timestamp=[f"2026-01-01 00:00:0{i}" for i in range(n)],
        parsed_timestamp=pd.date_range("2026-01-01", periods=n, freq="s"),
        export_date="2026-01-01",
        valid_row=True,
        bar_included=True,
        asset="ES",
        contract="ESU6",
        range_setting=4,
        chart_type="Range XV (filename label)",
        chart_identity_status="provisional",
        timing_status="unverified",
        split="development",
        sequence_id=1,
    )
    return frame


class ExcursionTests(unittest.TestCase):
    def test_signal_bar_extremes_are_excluded(self):
        bars = excursion_bars()
        events, _ = detect_events(bars, CONFIG)
        enriched = add_excursions_and_timing(bars, events, CONFIG)
        signal = enriched.loc[enriched["bar_index"].eq(1)].iloc[0]
        self.assertEqual(signal["mfe_h3"], 4)
        self.assertEqual(signal["mae_h3"], 3)
        self.assertEqual(signal["terminal_move_h3"], 1)
        self.assertEqual(signal["mfe_bar_index_h3"], 2)
        self.assertEqual(signal["mae_bar_index_h3"], 3)

    def test_break_bar_is_included_in_through_break(self):
        bars = excursion_bars()
        events, _ = detect_events(bars, CONFIG)
        enriched = add_excursions_and_timing(bars, events, CONFIG)
        signal = enriched.loc[enriched["bar_index"].eq(1)].iloc[0]
        self.assertEqual(signal["observed_L"], 2)
        self.assertEqual(signal["through_break_mae_ticks"], 3)
        self.assertEqual(signal["run_only_mae_ticks"], 2)
        self.assertEqual(signal["break_bar_index"], 3)

    def test_long_short_symmetry(self):
        long_metrics = _window_metrics(np.array([103, 104]), np.array([99, 98]), np.array([101, 102]), 100, 1)
        short_metrics = _window_metrics(np.array([201, 202]), np.array([197, 196]), np.array([199, 198]), 200, -1)
        self.assertEqual(long_metrics, short_metrics)

    def test_zero_excursion_uses_reference_index_zero(self):
        metrics = _window_metrics(np.array([100, 100]), np.array([98, 97]), np.array([99, 98]), 100, 1)
        self.assertEqual(metrics[1], 0)
        self.assertEqual(metrics[4], 0)

    def test_tied_positive_extreme_uses_earliest_bar(self):
        metrics = _window_metrics(np.array([103, 103]), np.array([99, 99]), np.array([101, 102]), 100, 1)
        self.assertEqual(metrics[1], 3)
        self.assertEqual(metrics[4], 1)


if __name__ == "__main__":
    unittest.main()

