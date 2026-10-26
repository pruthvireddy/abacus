from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parents[1] / "prepare_inputs.py"
SPEC = importlib.util.spec_from_file_location("study23_prepare_inputs", MODULE)
inputs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inputs)


def minutes_for(schedule):
    frame = schedule[["timestamp"]].copy()
    frame["open_fixed"] = 1000_000_000_000
    frame["high_fixed"] = 1001_000_000_000
    frame["low_fixed"] = 999_000_000_000
    frame["close_fixed"] = 1000_500_000_000
    for name in ("open", "high", "low", "close"):
        frame[name] = frame[name + "_fixed"] * 1e-9
    frame["volume"] = np.arange(1, len(frame)+1, dtype=np.uint64)
    frame["contract"] = "GC:1:2024:2:GCG4"
    frame["raw_symbol"] = "GCG4"
    frame["roll_id"] = 30
    frame["source_valid"] = True
    frame["is_roll"] = False
    return frame


class InputAuditTests(unittest.TestCase):
    def test_integer_quarter_hour_alignment_and_available_at(self):
        schedule = inputs.expected_minutes("GC", "2024-01-09", "2024-01-10").iloc[:15].copy()
        frame = minutes_for(schedule)
        frame.loc[4, "high_fixed"] += 100_000_000
        frame.loc[8, "low_fixed"] -= 100_000_000
        bars, check = inputs.aggregate_15m(frame, schedule)
        bar = bars.iloc[0]
        self.assertTrue(bar.usable)
        self.assertEqual(bar.timestamp.minute % 15, 0)
        self.assertEqual(bar.available_at - bar.timestamp, pd.Timedelta(minutes=15))
        self.assertEqual(bar.open_fixed, frame.open_fixed.iloc[0])
        self.assertEqual(bar.close_fixed, frame.close_fixed.iloc[-1])
        self.assertEqual(bar.high_fixed, frame.high_fixed.max())
        self.assertEqual(bar.low_fixed, frame.low_fixed.min())
        self.assertEqual(bar.volume, frame.volume.sum())
        self.assertEqual(check["mismatch_counts"], {x: 0 for x in check["compared_fields"]})

    def test_missing_minute_remains_unusable_with_observed_prices(self):
        schedule = inputs.expected_minutes("GC", "2024-01-09", "2024-01-10").iloc[:15].copy()
        frame = minutes_for(schedule).drop(index=5)
        bars, _ = inputs.aggregate_15m(frame, schedule)
        self.assertFalse(bars.usable.iloc[0])
        self.assertEqual(bars.missing_expected_count.iloc[0], 1)
        self.assertIn("missing_expected_source_minutes", bars.quality_reason.iloc[0])
        self.assertEqual(bars.observed_count.iloc[0], 14)

    def test_missing_later_trading_minute_never_changes_range_eligibility(self):
        schedule = inputs.expected_minutes("GC", "2024-01-08", "2024-01-11")
        start, end = pd.Timestamp("2024-01-07T21:00Z"), pd.Timestamp("2024-01-10T21:00Z")
        frame = minutes_for(schedule)
        before = inputs.coverage_roster(frame, schedule, start, end).set_index("broker_date")
        frame = frame.loc[frame.timestamp.ne(pd.Timestamp("2024-01-09T12:00Z"))]
        after = inputs.coverage_roster(frame, schedule, start, end).set_index("broker_date")
        self.assertTrue(before.loc["2024-01-09", "eligible"])
        self.assertTrue(after.loc["2024-01-09", "eligible"])
        self.assertEqual(after.loc["2024-01-09", "later_missing_trading_minutes"], 1)
        self.assertFalse(after.loc["2024-01-09", "later_missing_is_eligibility_filter"])

    def test_missing_range_minute_is_known_at_decision(self):
        schedule = inputs.expected_minutes("GC", "2024-01-08", "2024-01-11")
        frame = minutes_for(schedule)
        frame = frame.loc[frame.timestamp.ne(pd.Timestamp("2024-01-09T03:59Z"))]
        roster = inputs.coverage_roster(frame, schedule, pd.Timestamp("2024-01-07T21:00Z"),
                                      pd.Timestamp("2024-01-10T21:00Z")).set_index("broker_date")
        self.assertFalse(roster.loc["2024-01-09", "eligible"])
        self.assertEqual(roster.loc["2024-01-09", "missing_range_minutes"], 1)
        self.assertIn("missing_range_source_minutes", roster.loc["2024-01-09", "reason"])
        self.assertEqual(roster.loc["2024-01-09", "decision_available_at"], "2024-01-09T04:00:00+00:00")

    def test_normal_closures_are_not_missing_and_monday_follows_dst(self):
        for day, count, expected_offset in [("2024-01-08", 300, -300), ("2024-07-08", 360, -240)]:
            opening = pd.Timestamp(day, tz=inputs.BROKER).tz_convert("UTC")
            schedule = inputs.expected_minutes("GC", day, str((pd.Timestamp(day)+pd.Timedelta(days=2)).date()))
            roster = inputs.coverage_roster(minutes_for(schedule), schedule, opening,
                opening+pd.Timedelta(days=2)).set_index("broker_date")
            self.assertEqual(roster.loc[day, "expected_range_minutes"], count)
            self.assertEqual(roster.loc[day, "missing_range_minutes"], 0)
            self.assertEqual(roster.loc[day, "ny_utc_offset_minutes"], expected_offset)

    def test_roll_across_winter_range_is_excluded_at_0700(self):
        schedule = inputs.expected_minutes("GC", "2024-01-08", "2024-01-11")
        frame = minutes_for(schedule)
        frame.loc[frame.timestamp.ge(pd.Timestamp("2024-01-08T23:00Z")), "contract"] = "GC:2:2024:4:GCJ4"
        roster = inputs.coverage_roster(frame, schedule, pd.Timestamp("2024-01-07T21:00Z"),
                                      pd.Timestamp("2024-01-10T21:00Z")).set_index("broker_date")
        self.assertFalse(roster.loc["2024-01-09", "eligible"])
        self.assertIn("range_contract_transition", roster.loc["2024-01-09", "reason"])
        self.assertEqual(roster.loc["2024-01-09", "range_contract_count"], 2)

    def test_conservative_holiday_calendar_is_explicit(self):
        schedule = inputs.expected_minutes("GC", "2024-12-23", "2024-12-27")
        roster = inputs.coverage_roster(minutes_for(schedule), schedule,
            pd.Timestamp("2024-12-22T21:00Z"), pd.Timestamp("2024-12-26T21:00Z")).set_index("broker_date")
        self.assertFalse(roster.loc["2024-12-25", "eligible"])
        self.assertIn("calendar_uncertified", roster.loc["2024-12-25", "reason"])
        self.assertIn("Christmas", roster.loc["2024-12-25", "calendar_event"])
        self.assertEqual(roster.loc["2024-12-25", "missing_range_minutes"], 0)

    def test_first_loaded_broker_day_always_excluded(self):
        schedule = inputs.expected_minutes("GC", "2024-01-09", "2024-01-11")
        roster = inputs.coverage_roster(minutes_for(schedule), schedule,
            pd.Timestamp("2024-01-08T21:00Z"), pd.Timestamp("2024-01-10T21:00Z"))
        first = roster.loc[roster.first_loaded_broker_day].iloc[0]
        self.assertFalse(first.eligible)
        self.assertIn("first_loaded_broker_day", first.reason)


if __name__ == "__main__":
    unittest.main()
