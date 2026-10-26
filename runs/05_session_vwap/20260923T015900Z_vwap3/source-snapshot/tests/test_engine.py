"""Synthetic causal and first-passage checks for the VWAP study."""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import barrier_outcome, contact, evaluate, extract_view, reconcile, valid


def bars(*rows):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"])


def synthetic_window(closes):
    start = pd.Timestamp("2026-01-02T20:00:00Z")
    minutes = pd.date_range(start, periods=2 * len(closes), freq="min")
    source_prices = [value for value in closes for _ in range(2)]
    source = pd.DataFrame({"ts_event": minutes, "open": [int(x * 1e9) for x in source_prices],
        "high": [int(x * 1e9) for x in source_prices], "low": [int(x * 1e9) for x in source_prices],
        "close": [int(x * 1e9) for x in source_prices], "instrument_id": [11] * len(minutes),
        "raw_symbol": ["TEST"] * len(minutes)})
    opens = pd.date_range(start, periods=len(closes), freq="2min")
    feature = pd.DataFrame({"ts_event": opens, "bar_close_ts": opens + pd.Timedelta(minutes=2),
        "available_at": opens + pd.Timedelta(minutes=2), "session_date": [start.date()] * len(closes),
        "product": ["ES"] * len(closes), "timeframe": ["2m"] * len(closes),
        "instrument_id": [11] * len(closes), "raw_symbol": ["TEST"] * len(closes),
        "open": [int(x * 1e9) for x in closes], "high": [int(x * 1e9) for x in closes],
        "low": [int(x * 1e9) for x in closes], "close": [int(x * 1e9) for x in closes],
        "price_adjustment": [0] * len(closes), "min_tick": [int(1e9)] * len(closes),
        "globex_vwap": [100.0] * len(closes), "globex_sigma": [1.0] * len(closes),
        "globex_anchor_active": [True] * len(closes),
        "globex_minutes_since_anchor": [30 + 2 * i for i in range(len(closes))],
        "globex_exit_above_upper_2sigma": [None] + [False] * (len(closes) - 1),
        "globex_exit_below_lower_2sigma": [None] + [False] * (len(closes) - 1)})
    return feature, source


class PathTests(unittest.TestCase):
    def test_contact_includes_boundary_equality(self):
        self.assertEqual(contact(bars((101_000000000, 101_000000000,
                                       101_000000000, 101_000000000)), 100, 1)[0], 0)

    def test_gap_through_is_not_contact(self):
        path = bars((102_000000000, 102_000000000, 102_000000000, 102_000000000),
                    (98_000000000, 98_000000000, 98_000000000, 98_000000000))
        self.assertEqual(contact(path, 100, 1), (None, 1))

    def test_favorable_adverse_and_ambiguous(self):
        self.assertEqual(barrier_outcome(bars((100_000000000, 102_000000000,
                                               100_000000000, 102_000000000)), 100, 1, 1)["barrier"], "favorable")
        self.assertEqual(barrier_outcome(bars((100_000000000, 100_000000000,
                                               98_000000000, 98_000000000)), 100, 1, 1)["barrier"], "adverse")
        self.assertEqual(barrier_outcome(bars((100_000000000, 102_000000000,
                                               98_000000000, 100_000000000)), 100, 1, 1)["barrier"], "ambiguous")

    def test_open_gap_precedes_intraminute_extreme(self):
        result = barrier_outcome(bars((102_000000000, 103_000000000,
                                       98_000000000, 99_000000000)), 100, 1, 1)
        self.assertEqual(result["barrier"], "favorable")
        self.assertTrue(result["open_gap"])

    def test_anchor_requires_positive_sigma_and_elapsed_maturity(self):
        row = pd.Series({"globex_anchor_active": True, "globex_vwap": 100.0,
                         "globex_sigma": 1.0, "globex_minutes_since_anchor": 30})
        self.assertTrue(valid(row, "globex"))
        row["globex_sigma"] = 0.0
        self.assertFalse(valid(row, "globex"))
        row["globex_sigma"] = 1.0
        row["globex_minutes_since_anchor"] = 29
        self.assertFalse(valid(row, "globex"))
        row["globex_anchor_active"] = False
        self.assertFalse(valid(row, "globex"))

    def test_frozen_and_evolving_contact_use_prior_available_feature(self):
        start = pd.Timestamp("2026-01-02T20:00:00Z")
        minutes = pd.date_range(start, periods=15, freq="min")
        levels = [104] * 10 + [102] * 5
        source = pd.DataFrame({"ts_event": minutes, "open": [int(x * 1e9) for x in levels],
                               "high": [int(x * 1e9) for x in levels],
                               "low": [int(x * 1e9) for x in levels],
                               "close": [int(x * 1e9) for x in levels],
                               "instrument_id": [11] * 15, "raw_symbol": ["TEST"] * 15})
        features = pd.DataFrame({
            "ts_event": [start, start + pd.Timedelta(minutes=5), start + pd.Timedelta(minutes=10)],
            "bar_close_ts": [start + pd.Timedelta(minutes=x) for x in (5, 10, 15)],
            "available_at": [start + pd.Timedelta(minutes=x) for x in (5, 10, 15)],
            "timeframe": ["5m"] * 3, "instrument_id": [11] * 3,
            "raw_symbol": ["TEST"] * 3, "price_adjustment": [int(1e9)] * 3,
            "open": [int(x * 1e9) for x in (105, 105, 103)],
            "high": [int(x * 1e9) for x in (105, 105, 103)],
            "low": [int(x * 1e9) for x in (105, 105, 103)],
            "close": [int(x * 1e9) for x in (105, 105, 103)],
            "globex_vwap": [101.0, 103.0, 103.0]})
        event = {"strategy": "B", "feature_index": 0, "tick": 1.0, "side": 1,
                 "direction": -1, "vwap": 100.0, "sigma": 2.0}
        outcome = evaluate(event, features, source, "globex", start + pd.Timedelta(minutes=15))
        self.assertIsNone(outcome["frozen_contact_minute"])
        self.assertEqual(outcome["evolving_contact_minute"], 5)
        self.assertTrue(outcome["h10_evaluable"])
        self.assertFalse(outcome["h30_evaluable"])

    def test_reconciliation_rejects_contract_and_adjustment_mismatch(self):
        start = pd.Timestamp("2026-01-02T20:00:00Z")
        signal = pd.Series({"ts_event": start, "bar_close_ts": start + pd.Timedelta(minutes=2),
                            "instrument_id": 11, "raw_symbol": "TEST",
                            "price_adjustment": int(1e9),
                            "open": int(101e9), "high": int(101e9),
                            "low": int(101e9), "close": int(101e9)})
        source = pd.DataFrame({"ts_event": [start, start + pd.Timedelta(minutes=1)],
                               "instrument_id": [11, 11], "raw_symbol": ["TEST", "TEST"],
                               "open": [int(100e9)] * 2, "high": [int(100e9)] * 2,
                               "low": [int(100e9)] * 2, "close": [int(100e9)] * 2})
        reconcile(signal, source, 2)
        source.loc[1, "instrument_id"] = 12
        with self.assertRaisesRegex(ValueError, "contract mismatch"):
            reconcile(signal, source, 2)
        source.loc[1, "instrument_id"] = 11
        signal["price_adjustment"] = int(2e9)
        with self.assertRaisesRegex(ValueError, "OHLC mismatch"):
            reconcile(signal, source, 2)

    def test_first_touch_after_ten_minutes_qualifies(self):
        feature, source = synthetic_window([105] * 6 + [100] * 6)
        events, summary = extract_view(feature, source, "globex", "globex")
        touches = [event for event in events if event["strategy"] == "C"]
        self.assertEqual(len(touches), 1)
        self.assertEqual(touches[0]["feature_index"], 6)
        self.assertEqual(summary["unqualified_first_touches"], 0)
        self.assertFalse(touches[0]["confirmation"])

    def test_early_touch_consumes_departure_then_new_departure_rearms(self):
        feature, source = synthetic_window([105] * 3 + [100] + [105] * 7 + [100] * 5)
        events, summary = extract_view(feature, source, "globex", "globex")
        touches = [event for event in events if event["strategy"] == "C"]
        self.assertEqual(summary["unqualified_first_touches"], 1)
        self.assertEqual([event["feature_index"] for event in touches], [11])

    def test_departure_four_tick_equality_and_null_event_are_distinct(self):
        feature, source = synthetic_window([104] * 6 + [100] * 6)
        events, summary = extract_view(feature, source, "globex", "globex")
        self.assertTrue(summary["departure"])
        self.assertEqual(sum(event["strategy"] == "B" for event in events), 1)
        self.assertEqual(sum(event["strategy"] == "A" for event in events), 0)


if __name__ == "__main__":
    unittest.main()
