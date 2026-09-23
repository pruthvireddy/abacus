from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from followthrough_adverse.core import detect_reversals
from followthrough_adverse.leg_duration import (
    assign_leg_session,
    compute_leg_events,
    leg_duration_by_clock,
    leg_duration_by_session,
    reconcile_leg_sample,
    summarize_leg_duration,
)


CONFIG = {
    "primary_reference": "follow-through candle open",
    "timing_status": "unresolved",
    "time_of_day": {"window_minutes": 30},
    "leg_duration": {
        "minimum_candles_including_reversal": 3,
        "minimum_qualifying_legs_per_window": 1,
        "minimum_active_export_dates": 1,
        "top_windows_per_criterion": 1,
        "sessions": [
            {"name": "Asia", "start": "18:00", "end": "03:00"},
            {"name": "New York AM", "start": "09:30", "end": "12:00"},
            {"name": "New York PM", "start": "12:00", "end": "16:00"},
        ],
    },
    "bootstrap": {"replicates": 50, "seed": 7},
}


def make_bars(rows, timestamps=None, sequences=None):
    frame = pd.DataFrame(rows, columns=["open_ticks", "high_ticks", "low_ticks", "close_ticks"])
    n = len(frame)
    frame["direction"] = np.sign(frame["close_ticks"] - frame["open_ticks"]).astype(int)
    if timestamps is None:
        timestamps = pd.date_range("2026-01-01 09:29:00", periods=n, freq="min")
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


class LegDurationTests(unittest.TestCase):
    def test_completed_three_candle_leg_includes_reversal(self):
        bars = make_bars(
            [
                (102, 102, 100, 101),
                (100, 102, 100, 101),
                (101, 103, 101, 102),
                (102, 104, 102, 103),
                (104, 104, 102, 103),
                (103, 103, 101, 102),
            ]
        )
        event = compute_leg_events(bars, detect_reversals(bars, CONFIG), CONFIG).loc[
            lambda frame: frame["bar_index"].eq(1)
        ].iloc[0]
        self.assertTrue(event["leg_completed"])
        self.assertTrue(event["leg_at_least_three"])
        self.assertEqual(event["leg_candle_count_including_reversal"], 3)
        self.assertEqual(event["leg_additional_candle_count"], 2)
        self.assertEqual(event["leg_duration_proxy_minutes"], 2.0)
        self.assertEqual(event["leg_break_type"], "opposite candle")

    def test_doji_ends_leg(self):
        bars = make_bars(
            [
                (102, 102, 100, 101),
                (100, 102, 100, 101),
                (101, 103, 101, 102),
                (102, 104, 102, 103),
                (103, 104, 102, 103),
            ]
        )
        event = compute_leg_events(bars, detect_reversals(bars, CONFIG), CONFIG).iloc[0]
        self.assertTrue(event["leg_completed"])
        self.assertEqual(event["leg_break_type"], "doji")
        self.assertEqual(event["leg_candle_count_including_reversal"], 3)

    def test_export_boundary_censors_leg(self):
        bars = make_bars(
            [
                (102, 102, 100, 101),
                (100, 102, 100, 101),
                (101, 103, 101, 102),
                (102, 104, 102, 103),
                (103, 105, 103, 104),
            ],
            sequences=[1, 1, 1, 1, 2],
        )
        event = compute_leg_events(bars, detect_reversals(bars, CONFIG), CONFIG).iloc[0]
        self.assertFalse(event["leg_completed"])
        self.assertTrue(event["leg_censored"])
        self.assertFalse(event["leg_at_least_three"])

    def test_summary_and_clock_bucket(self):
        bars = make_bars(
            [
                (102, 102, 100, 101),
                (100, 102, 100, 101),
                (101, 103, 101, 102),
                (102, 104, 102, 103),
                (104, 104, 102, 103),
                (103, 103, 101, 102),
            ]
        )
        events = compute_leg_events(bars, detect_reversals(bars, CONFIG), CONFIG)
        summary = summarize_leg_duration(events, CONFIG).iloc[0]
        clock = leg_duration_by_clock(events, CONFIG)
        window = clock.loc[clock["window_start"].eq("09:30")].iloc[0]
        self.assertEqual(summary["legs_at_least_three"], 1)
        self.assertEqual(summary["mean_duration_proxy_minutes"], 2.0)
        self.assertEqual(window["legs_at_least_three"], 1)
        self.assertEqual(window["mean_candles_in_leg"], 3.0)

    def test_independent_reconciliation(self):
        bars = make_bars(
            [
                (102, 102, 100, 101),
                (100, 102, 100, 101),
                (101, 103, 101, 102),
                (102, 104, 102, 103),
                (104, 104, 102, 103),
                (103, 103, 101, 102),
            ]
        )
        events = compute_leg_events(bars, detect_reversals(bars, CONFIG), CONFIG)
        reconciliation, check = reconcile_leg_sample(bars, events, seed=3, sample_size=1)
        self.assertTrue(check["all_match"])
        self.assertTrue(reconciliation.iloc[0]["all_match"])

    def test_session_boundaries_and_overnight_window(self):
        timestamps = pd.Series(
            pd.to_datetime(
                [
                    "2026-01-01 18:00:00",
                    "2026-01-02 02:59:00",
                    "2026-01-02 03:00:00",
                    "2026-01-02 09:30:00",
                    "2026-01-02 11:59:00",
                    "2026-01-02 12:00:00",
                    "2026-01-02 15:59:00",
                    "2026-01-02 16:00:00",
                ]
            )
        )
        assigned = assign_leg_session(timestamps, CONFIG["leg_duration"]["sessions"])
        self.assertEqual(
            assigned["session"].tolist(),
            ["Asia", "Asia", pd.NA, "New York AM", "New York AM", "New York PM", "New York PM", pd.NA],
        )

    def test_session_summary_uses_event_weighted_mean(self):
        timestamps = pd.Series(
            pd.to_datetime(
                [
                    "2026-01-01 18:00:00",
                    "2026-01-02 02:59:00",
                    "2026-01-02 09:30:00",
                    "2026-01-02 11:59:00",
                    "2026-01-02 12:00:00",
                    "2026-01-02 15:59:00",
                ]
            )
        )
        events = pd.DataFrame(
            {
                "asset": "ES",
                "contract": "ESU6",
                "range_setting": 4,
                "parsed_timestamp": timestamps,
                "export_date": timestamps.dt.strftime("%Y-%m-%d"),
                "leg_completed": True,
                "leg_at_least_three": True,
                "leg_duration_proxy_minutes": [10.0, 20.0, 4.0, 6.0, 8.0, 12.0],
                "leg_duration_proxy_seconds": [600.0, 1200.0, 240.0, 360.0, 480.0, 720.0],
                "leg_candle_count_including_reversal": [3, 5, 3, 3, 4, 6],
            }
        )
        summary = leg_duration_by_session(events, CONFIG).set_index("session")
        self.assertEqual(summary.loc["Asia", "mean_duration_proxy_minutes"], 15.0)
        self.assertEqual(summary.loc["New York AM", "mean_duration_proxy_minutes"], 5.0)
        self.assertEqual(summary.loc["New York PM", "mean_duration_proxy_minutes"], 10.0)


if __name__ == "__main__":
    unittest.main()
