from __future__ import annotations

import unittest

import pandas as pd

from followthrough_adverse.time_of_day import (
    assign_clock_window,
    build_confirmation_time_table,
    build_signal_time_table,
    rank_time_windows,
)


CONFIG = {
    "time_of_day": {
        "window_minutes": 30,
        "minimum_conditioned_events": 1,
        "minimum_active_export_dates": 1,
        "top_windows_per_criterion": 1,
    },
    "contracts": {"ES": {"tick_size": 0.25, "dollars_per_tick": 12.5}},
    "timestamp_format": "%Y-%d-%m %H:%M:%S",
}


def synthetic_bars() -> pd.DataFrame:
    timestamps = pd.to_datetime(
        ["2026-06-14 09:28:00", "2026-06-14 09:29:00", "2026-06-14 09:30:00"]
    )
    return pd.DataFrame(
        {
            "asset": "ES",
            "contract": "ESU6",
            "range_setting": 4,
            "source_row": [1, 2, 3],
            "parsed_timestamp": timestamps,
            "export_date": "2026-06-14",
            "bar_included": True,
            "valid_row": True,
        }
    )


def synthetic_event() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": ["ES4-r2"],
            "asset": ["ES"],
            "contract": ["ESU6"],
            "range_setting": [4],
            "parsed_timestamp": [pd.Timestamp("2026-06-14 09:29:00")],
            "follow_timestamp": ["2026-14-06 09:30:00"],
            "export_date": ["2026-06-14"],
            "eligible_next_bar": [True],
            "next_bar_same_direction": [True],
            "adverse_from_follow_open_ticks": [2.0],
            "favorable_from_follow_open_ticks": [5.0],
        }
    )


class TimeOfDayTests(unittest.TestCase):
    def test_half_hour_boundaries(self):
        timestamps = pd.Series(
            pd.to_datetime(
                [
                    "2026-01-01 09:00:00",
                    "2026-01-01 09:29:59",
                    "2026-01-01 09:30:00",
                    "2026-01-01 09:59:59",
                ]
            )
        )
        assigned = assign_clock_window(timestamps)
        self.assertEqual(assigned["window_start"].tolist(), ["09:00", "09:00", "09:30", "09:30"])

    def test_signal_and_confirmation_use_different_candle_timestamps(self):
        signal = build_signal_time_table(synthetic_bars(), synthetic_event(), CONFIG)
        confirmation = build_confirmation_time_table(synthetic_bars(), synthetic_event(), CONFIG)
        signal_row = signal.loc[signal["window_start"].eq("09:00")].iloc[0]
        confirmation_row = confirmation.loc[confirmation["window_start"].eq("09:30")].iloc[0]
        self.assertEqual(signal_row["conditioned_events"], 1)
        self.assertEqual(confirmation_row["conditioned_events"], 1)
        self.assertEqual(signal_row["mean_favorable_minus_adverse_ticks"], 3.0)

    def test_active_zero_event_windows_are_retained(self):
        signal = build_signal_time_table(synthetic_bars(), synthetic_event(), CONFIG)
        row = signal.loc[signal["window_start"].eq("09:30")].iloc[0]
        self.assertEqual(row["active_export_dates"], 1)
        self.assertEqual(row["same_direction_events"], 0)

    def test_rankings_respect_timing_basis(self):
        signal = build_signal_time_table(synthetic_bars(), synthetic_event(), CONFIG)
        confirmation = build_confirmation_time_table(synthetic_bars(), synthetic_event(), CONFIG)
        rankings, balanced = rank_time_windows(signal, confirmation, CONFIG)
        highest_rate = rankings.loc[rankings["criterion"].eq("highest follow-through rate")].iloc[0]
        most_confirmations = rankings.loc[rankings["criterion"].eq("most confirmations")].iloc[0]
        self.assertEqual(highest_rate["half_hour_window"], "09:00–09:30")
        self.assertEqual(most_confirmations["half_hour_window"], "09:30–10:00")
        self.assertEqual(balanced.iloc[0]["half_hour_window"], "09:00–09:30")


if __name__ == "__main__":
    unittest.main()
