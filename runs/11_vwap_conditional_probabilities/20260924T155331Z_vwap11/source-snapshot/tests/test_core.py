from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))

from src.features import (reference_zone, residence_state, round_half_up_to_tick,
                          select_corridor_events)
from src.outcomes import (_valid_path, contact_dynamic, contact_fixed,
                          race_between_zones, race_return_extension)


def path(rows, start="2026-01-02T15:00:00Z", symbol="ESH6", instrument=1):
    start_ts = pd.Timestamp(start)
    records = []
    for index, values in enumerate(rows):
        opening, high, low, close = values
        records.append({
            "ts_event": start_ts + pd.Timedelta(minutes=index),
            "open": int(opening * 1e9), "high": int(high * 1e9),
            "low": int(low * 1e9), "close": int(close * 1e9),
            "raw_symbol": symbol, "instrument_id": instrument, "volume": 1,
        })
    return pd.DataFrame(records)


class CoreTests(unittest.TestCase):
    def test_tick_rounding_and_zone(self):
        self.assertEqual(round_half_up_to_tick(100.125, .25), 100.25)
        self.assertEqual(reference_zone(100.12, .25), (99.75, 100.25, 100.0))

    def test_no_return_before_expiry(self):
        result = contact_fixed(path([(102, 103, 101.5, 102)] * 3), 99.75, 100.25, 1)
        self.assertFalse(result["contact"])
        self.assertIsNone(result["contact_minute"])

    def test_return_after_earlier_unresolved_checkpoint(self):
        rows = [(102, 102.5, 101.5, 102), (101, 101.2, 99.9, 100.1)]
        result = contact_fixed(path(rows), 99.75, 100.25, 1)
        self.assertTrue(result["contact"])
        self.assertEqual(result["contact_minute"], 2)

    def test_evolving_contact_without_frozen_contact(self):
        bars = path([(102, 102.5, 101.5, 102)])
        frozen = contact_fixed(bars, 99.75, 100.25, 1)
        evolving = contact_dynamic(bars, np.array([101.75]), np.array([102.25]), 1)
        self.assertFalse(frozen["contact"])
        self.assertTrue(evolving["contact"])

    def test_both_barriers_same_minute_is_ambiguous(self):
        bars = path([(101, 103, 99, 101)])
        result = race_return_extension(bars, 1, 99.75, 100.25, 102.5)
        self.assertEqual(result["outcome"], "ambiguous")

    def test_open_gap_resolves_extension(self):
        bars = path([(103, 103.2, 102.8, 103)])
        result = race_return_extension(bars, 1, 99.75, 100.25, 102.5)
        self.assertEqual(result["outcome"], "extension_first")
        self.assertTrue(result["gap"])

    def test_gap_through_return_is_flagged(self):
        bars = path([(99, 99.5, 98.5, 99)])
        result = race_return_extension(bars, 1, 99.75, 100.25, 102.5)
        self.assertEqual(result["outcome"], "return_first")
        self.assertEqual(result["gap_target"], "return")

    def test_mirrored_corridor_destinations(self):
        down = race_between_zones(path([(105, 105.5, 99.8, 100.2)]),
                                  (99.75, 100.25), (109.75, 110.25),
                                  "day_first", "session_first")
        up = race_between_zones(path([(105, 110.1, 104.8, 109.9)]),
                                (99.75, 100.25), (109.75, 110.25),
                                "session_first", "day_first")
        self.assertEqual(down["outcome"], "day_first")
        self.assertEqual(up["outcome"], "day_first")

    def test_fixed_lockout_suppresses_repeated_crosses(self):
        times = pd.to_datetime(["2026-01-02T15:00Z", "2026-01-02T15:10Z", "2026-01-02T15:30Z"])
        frame = pd.DataFrame({
            "product": ["ES"] * 3, "session_date": ["2026-01-02"] * 3,
            "timeframe": ["2m"] * 3, "session_anchor": ["ny"] * 3,
            "forecast_ts": times, "corridor_width_ticks": [12] * 3,
            "corridor_width_day_sigma": [.5] * 3,
        })
        selected, suppressed = select_corridor_events(frame, 8, .25, 30)
        self.assertEqual(len(selected), 2)
        self.assertEqual(suppressed, 1)
        self.assertEqual(selected.episode_ordinal.tolist(), [1, 2])

    def test_residence_state(self):
        state = residence_state(np.ones(15, dtype=np.int8), 2)
        self.assertEqual(state[0], "persistent")
        alternating = np.array([1, -1] * 7 + [1], dtype=np.int8)
        self.assertEqual(residence_state(alternating, 2)[0], "rotational")

    def test_missing_bar_is_unavailable_not_false(self):
        bars = path([(101, 102, 100, 101), (101, 102, 100, 101)])
        bars.loc[1, "ts_event"] += pd.Timedelta(minutes=1)
        reason = _valid_path(bars, pd.Timestamp("2026-01-02T15:00:00Z"), 2, "ESH6", 1)
        self.assertEqual(reason, "missing_source_bars")

    def test_roll_or_contract_change_is_unavailable(self):
        bars = path([(101, 102, 100, 101), (101, 102, 100, 101)])
        bars.loc[1, "raw_symbol"] = "ESM6"
        reason = _valid_path(bars, pd.Timestamp("2026-01-02T15:00:00Z"), 2, "ESH6", 1)
        self.assertEqual(reason, "future_contract_discontinuity")


if __name__ == "__main__":
    unittest.main()

