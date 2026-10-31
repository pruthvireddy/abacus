"""Synthetic checks for independent feature oracles and receipt safety."""
from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


SPEC = importlib.util.spec_from_file_location("study30_feature_verifier", Path(__file__).resolve().parents[1] / "verify_features.py")
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)
NY = ZoneInfo("America/New_York")


def ema_frame(closes, stamps=None, contracts=None, usable=None, known=None):
    n = len(closes)
    return pd.DataFrame({"timestamp": pd.to_datetime(stamps or pd.date_range("2020-01-02", periods=n, freq="3min", tz="UTC"), utc=True),
                         "contract": contracts or ["one"] * n, "close": closes,
                         "usable": usable or [True] * n, "known_closure_before": known or [False] * n})


def minute_frame(values, volumes=None, offsets=None, contracts=None):
    anchor = pd.Timestamp(datetime(2020, 1, 8, 18, tzinfo=NY)).tz_convert("UTC")
    offsets = offsets or list(range(len(values)))
    return pd.DataFrame({"timestamp": [anchor + pd.Timedelta(minutes=n) for n in offsets],
                         "session_date": ["2020-01-09"] * len(values), "contract": contracts or ["ESH2020"] * len(values),
                         "open": values, "high": values, "low": values, "close": values,
                         "volume": volumes or [1.] * len(values), "calendar_valid": True})


class EmaOracleTests(unittest.TestCase):
    def test_hand_recurrence_and_preceding_warmup(self):
        result = verify.oracle_ema6(ema_frame([7., 14., 21.]), preceding=2)
        self.assertEqual(result.ema6.tolist(), [7., 9., 87 / 7])
        self.assertEqual(result.ema6_consecutive_count.tolist(), [1, 2, 3])
        self.assertEqual(result.ema6_ready.tolist(), [False, False, True])

    def test_known_closure_carries_unknown_gap_contract_and_invalid_reset(self):
        stamps = pd.to_datetime(["2020-01-02T00:00Z", "2020-01-02T00:18Z", "2020-01-02T00:36Z", "2020-01-02T00:39Z", "2020-01-02T00:42Z", "2020-01-02T00:45Z"])
        result = verify.oracle_ema6(ema_frame([7., 14., 21., 28., 35., 42.], stamps=stamps.tolist(),
                                             contracts=["one", "one", "one", "two", "two", "two"],
                                             usable=[True, True, True, True, False, True],
                                             known=[False, True, False, False, False, False]), preceding=1)
        self.assertEqual(result.ema6_consecutive_count.tolist(), [1, 2, 1, 1, 0, 1])
        self.assertEqual(result.ema6_ready.tolist(), [False, True, False, False, False, False])
        self.assertTrue(np.isnan(result.ema6.iloc[4]))


class VwapOracleTests(unittest.TestCase):
    def test_volume_weighting_and_zero_volume_undefined(self):
        result, counts = verify.oracle_vwap(minute_frame([10., 20., 30.], [1., 3., 0.]))
        self.assertEqual(result.globex_vwap.tolist(), [10., 17.5, 17.5])
        self.assertEqual(counts["valid_vwap_rows"], 3)
        result, _ = verify.oracle_vwap(minute_frame([10., 20.], [0., 1.]))
        self.assertFalse(result.vwap_valid.iloc[0])
        self.assertTrue(np.isnan(result.globex_vwap.iloc[0]))
        self.assertEqual(result.globex_vwap.iloc[1], 20.)

    def test_later_gap_does_not_change_prefix_and_invalidates_suffix(self):
        before, _ = verify.oracle_vwap(minute_frame([10., 20.]))
        after, _ = verify.oracle_vwap(minute_frame([10., 20., 30.], offsets=[0, 1, 3]))
        self.assertEqual(before.globex_vwap.tolist(), after.globex_vwap.iloc[:2].tolist())
        self.assertEqual(after.anchor_prefix_complete.tolist(), [True, True, False])
        self.assertFalse(after.vwap_valid.iloc[-1])

    def test_missing_anchor_or_delivery_switch_cannot_create_valid_vwap(self):
        result, _ = verify.oracle_vwap(minute_frame([10., 20.], offsets=[1, 2]))
        self.assertFalse(result.vwap_valid.any())
        result, _ = verify.oracle_vwap(minute_frame([10., 20.], contracts=["ESH2020", "ESM2020"]))
        self.assertEqual(result.vwap_valid.tolist(), [True, False])


class VerificationGuardTests(unittest.TestCase):
    def test_exact_comparison_preserves_nulls_and_refuses_numerical_drift(self):
        frame = pd.DataFrame({"x": [1., np.nan]})
        self.assertEqual(verify.compare_columns(frame, frame.copy(), ["x"], "synthetic")["maximum_absolute_error"], 0.)
        with self.assertRaises(ValueError):
            verify.compare_columns(frame, pd.DataFrame({"x": [1.01, np.nan]}), ["x"], "synthetic")
        with self.assertRaises(ValueError):
            verify.compare_columns(pd.DataFrame({"x": [np.inf]}), pd.DataFrame({"x": [-np.inf]}), ["x"], "synthetic")

    def test_cloud_asof_requires_latest_completed_value_and_value_parity(self):
        five = pd.DataFrame({"contract": ["ESH2020", "ESH2020"],
                             "available_at": pd.to_datetime(["2020-01-09T14:30Z", "2020-01-09T14:35Z"]),
                             "ema20": [10., 20.], "ema50": [9., 19.], "cloud_ready": True})
        three = pd.DataFrame({"contract": ["ESH2020"],
                              "available_at": pd.to_datetime(["2020-01-09T14:33Z"]),
                              "cloud_available_at": pd.to_datetime(["2020-01-09T14:30Z"]),
                              "ema20": [10.], "ema50": [9.], "cloud_ready": True})
        self.assertEqual(verify._asof_cloud(three, five)["rows"], 1)
        changed = three.copy()
        changed.ema20 = 20.
        with self.assertRaises(ValueError):
            verify._asof_cloud(changed, five)
        changed = three.copy()
        changed.cloud_available_at = pd.to_datetime(["2020-01-09T14:35Z"])
        with self.assertRaises(ValueError):
            verify._asof_cloud(changed, five)

    def test_receipt_cannot_write_outside_study_work(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "not-study-work"
            with self.assertRaisesRegex(ValueError, "receipt must be"):
                verify.verify(Path(temporary), Path(temporary) / "lock.json", output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
