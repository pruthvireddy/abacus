"""Synthetic numerical, timing and immutable-input indicator checks."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from abacus_bhishma.es_contract_session_indicators import (
    add_ema6, add_exact_slope, build_release, derive_minute_vwap,
    join_completed_features, load_release, native_bars, session_quality,
)
from abacus_bhishma.provenance import sha256_file


def three_bars(closes, *, timestamp="2020-01-06T00:00:00Z"):
    ts = pd.date_range(timestamp, periods=len(closes), freq="3min")
    return pd.DataFrame({"timestamp": ts, "available_at": ts + pd.Timedelta(minutes=3),
                         "close": closes, "contract": "ESH2020", "usable": True,
                         "known_closure_before": False, "quality_reason": ""})


def minute_bars(*, day="2020-01-06", periods=25, start=None):
    opening = (pd.Timestamp(day, tz="America/New_York") - pd.Timedelta(days=1) + pd.Timedelta(hours=18))
    ts = pd.date_range(start or opening, periods=periods, freq="min").tz_convert("UTC")
    return pd.DataFrame({"timestamp": ts, "session_date": day, "contract": "ESH2020",
                         "open": 100., "high": 102., "low": 99., "close": 101., "volume": 1.})


class EmaTests(unittest.TestCase):
    def test_hand_recursion_and_exact_preceding_readiness(self):
        frame = add_ema6(three_bars([7., 14., 7.]), preceding_bars=2)
        np.testing.assert_allclose(frame.ema6, [7, 9, 59 / 7])
        self.assertEqual(frame.ema6_ready.tolist(), [False, False, True])
        full = add_ema6(three_bars(np.arange(260, dtype=float) + 100))
        self.assertFalse(full.ema6_ready.iloc[249])
        self.assertTrue(full.ema6_ready.iloc[250])

    def test_invalid_slot_contract_switch_and_unknown_gap_reset(self):
        frame = three_bars([100., 110., 120., 130., 140.])
        frame.loc[1, "usable"] = False
        frame.loc[3:, "contract"] = "ESM2020"
        result = add_ema6(frame, preceding_bars=0)
        self.assertTrue(np.isnan(result.ema6.iloc[1]))
        self.assertEqual(result.ema6.iloc[2], 120.)
        self.assertEqual(result.ema6.iloc[3], 130.)
        self.assertEqual(result.ema6_reset_reason.iloc[3], "contract_switch")
        gap = three_bars([100., 110., 120.]).drop(index=1).reset_index(drop=True)
        self.assertEqual(add_ema6(gap).ema6.iloc[-1], 120.)
        gap.loc[1, "known_closure_before"] = True
        self.assertAlmostEqual(add_ema6(gap).ema6.iloc[-1], 2 / 7 * 120 + 5 / 7 * 100)

    def test_prefix_and_year_boundaries_do_not_reset(self):
        original = three_bars(np.arange(100, dtype=float) + 100, timestamp="2019-12-31T22:00:00Z")
        complete = add_ema6(original, preceding_bars=2)
        prefix = add_ema6(original.iloc[:30], preceding_bars=2)
        np.testing.assert_array_equal(prefix.ema6, complete.ema6.iloc[:30])
        self.assertEqual(int(complete.ema6_reset.sum()), 1)

    def test_native_aliases_preserve_ema_values(self):
        frame = pd.DataFrame({"timestamp": pd.date_range("2020-01-06", periods=3, freq="5min", tz="UTC"),
                              "session": "2020-01-06", "contract": "ES:7:2020:3:ESH0",
                              "ema20": [100., 100.1, 100.2], "ema50": [100.4, 100.3, 100.2]})
        frame["available_at"] = frame.timestamp + pd.Timedelta(minutes=5)
        result = native_bars(frame, 5)
        np.testing.assert_array_equal(result.ema20, frame.ema20)
        np.testing.assert_array_equal(result.ema50, frame.ema50)
        self.assertTrue(result.contract.eq("ESH2020").all())
        self.assertTrue(result.close_time.eq(frame.available_at).all())


class VwapTests(unittest.TestCase):
    def test_unequal_volume_hand_fixture_and_zero_volume(self):
        frame = minute_bars(periods=3)
        frame.loc[:, ["open", "high", "low", "close"]] = [[10., 12., 9., 9.], [20., 24., 18., 21.], [15., 18., 12., 15.]]
        frame["volume"] = [0., 2., 1.]
        result = derive_minute_vwap(frame)
        self.assertTrue(np.isnan(result.vwap.iloc[0]))
        self.assertEqual(result.vwap.iloc[1], 21.)
        self.assertEqual(result.vwap.iloc[2], 19.)
        self.assertEqual(result.vwap_valid.tolist(), [False, True, True])

    def test_gap_invalidates_remaining_anchor_without_rewriting_prefix(self):
        frame = minute_bars(periods=10)
        complete = derive_minute_vwap(frame)
        missing = derive_minute_vwap(frame.drop(index=4))
        np.testing.assert_array_equal(missing.vwap.iloc[:4], complete.vwap.iloc[:4])
        self.assertFalse(missing.vwap_valid.iloc[4:].any())
        self.assertTrue(missing.usable.all())
        late = derive_minute_vwap(frame.iloc[1:])
        self.assertFalse(late.vwap_valid.any())

    def test_negative_volume_and_delivery_switch_invalidates(self):
        frame = minute_bars(periods=10)
        frame.loc[3, "volume"] = -1.
        result = derive_minute_vwap(frame)
        self.assertFalse(result.usable.iloc[3])
        self.assertFalse(result.vwap_valid.iloc[3:].any())
        frame = minute_bars(periods=10)
        frame.loc[5:, "contract"] = "ESM2020"
        result = derive_minute_vwap(frame)
        self.assertFalse(result.vwap_valid.iloc[5:].any())

    def test_historical_pause_is_known_and_holiday_remains_uncertified(self):
        frame = minute_bars(day="2020-01-06", periods=1380)
        local = frame.timestamp.dt.tz_convert("America/New_York")
        frame = frame[~(local.dt.hour.eq(16) & local.dt.minute.ge(15) & local.dt.minute.lt(30))]
        result = derive_minute_vwap(frame)
        self.assertTrue(result.vwap_valid.all())
        holiday = derive_minute_vwap(minute_bars(day="2020-01-01"))
        self.assertFalse(holiday.usable.any())
        self.assertFalse(holiday.vwap_valid.any())

    def test_dst_anchor_and_exact_slope(self):
        frame = minute_bars(day="2026-03-09", periods=20)
        frame["close"] = np.arange(20) / 10 + 101.
        frame["high"] = frame.close + 1
        result = derive_minute_vwap(frame)
        self.assertEqual(result.timestamp.iloc[0].hour, 22)
        self.assertTrue(np.isnan(result.vwap_slope_15m.iloc[14]))
        self.assertAlmostEqual(result.vwap_slope_15m.iloc[15], result.vwap.iloc[15] - result.vwap.iloc[0])


class JoinAndQualityTests(unittest.TestCase):
    def test_only_completed_cloud_is_joined(self):
        bars3 = add_ema6(three_bars([100., 100., 100.], timestamp="2020-01-06T14:27:00Z"), preceding_bars=0)
        bars3["session_date"] = "2020-01-06"
        bars3["ema6_slope_15m"] = np.nan
        cloud_times = pd.to_datetime(["2020-01-06T14:25:00Z", "2020-01-06T14:30:00Z", "2020-01-06T14:35:00Z"])
        bars5 = pd.DataFrame({"available_at": cloud_times, "contract": "ESH2020", "ema20": [1., 2., 999.],
                              "ema50": [11., 12., 999.], "cloud_ready": True,
                              "ema20_slope_15m": 0., "ema50_slope_15m": 0.})
        bars1 = derive_minute_vwap(minute_bars(periods=960))
        result = join_completed_features(bars3, bars5, bars1)
        self.assertEqual(result.ema20.tolist(), [2., 2., 999.])
        self.assertTrue(result.cloud_available_at.le(result.available_at).all())
        self.assertTrue(result.vwap_available_at.le(result.available_at).all())
        changed = bars5.copy()
        changed.loc[2, "ema20"] = -999.
        prefix = join_completed_features(bars3.iloc[:2], changed, bars1)
        np.testing.assert_array_equal(prefix.ema20, result.ema20.iloc[:2])

    def test_native_slope_does_not_bridge_reset_or_contract(self):
        frame = add_ema6(three_bars(np.arange(15) + 100.), preceding_bars=0)
        result = add_exact_slope(frame, "ema6", "ema6_ready", "ema6_segment")
        self.assertTrue(result.ema6_slope_15m.iloc[:5].isna().all())
        self.assertTrue(np.isfinite(result.ema6_slope_15m.iloc[5]))
        frame.loc[5, "usable"] = False
        result = add_exact_slope(add_ema6(frame, preceding_bars=0), "ema6", "ema6_ready", "ema6_segment")
        self.assertTrue(result.ema6_slope_15m.iloc[6:11].isna().all())

    def test_quality_distinguishes_complete_rth_from_missing_anchor(self):
        full = minute_bars(day="2022-01-04", periods=1380)
        minutes = derive_minute_vwap(full)
        bars = pd.DataFrame({"session_date": "2022-01-04", "calendar_valid": True,
                             "contract": "ESH2020"}, index=range(2))
        result = session_quality(minutes, bars).iloc[0]
        self.assertTrue(result.rth_complete)
        self.assertTrue(result.anchor_to_rth_end_complete)
        self.assertTrue(result.full_globex_complete)
        missing = derive_minute_vwap(full.drop(index=20))
        result = session_quality(missing, bars).iloc[0]
        self.assertTrue(result.rth_complete)
        self.assertFalse(result.anchor_to_rth_end_complete)
        self.assertEqual(result.missing_minutes_to_rth_end, 1)

    def test_existing_release_refused_before_any_prepare_or_rebuild(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "data/features/es_contract_session_indicators/version=1.0.0"
            destination.mkdir(parents=True)
            sentinel = destination / "old"
            sentinel.write_text("preserve")
            with patch("abacus_bhishma.es_contract_session_indicators.prepare_frames") as prepare:
                with self.assertRaises(FileExistsError):
                    build_release(root, release_id="synthetic")
                prepare.assert_not_called()
            self.assertEqual(sentinel.read_text(), "preserve")


class PublicationTests(unittest.TestCase):
    def _fixture(self, root):
        request = root / "request.yaml"
        request.write_text("synthetic retained-input request\n")
        dummy = root / "producer.py"
        dummy.write_text("synthetic retained producer\n")
        quality = pd.DataFrame({"session_date": ["2020-01-06"], "anchor_to_rth_end_complete": [True]})
        frames = {name: pd.DataFrame({"contract": ["ESH2020"], "close": [100.]})
                  for name in ("bars1", "bars3", "bars5")}
        frames.update(quality=quality, input_manifests=[], input_files=[], qualifications=["synthetic fixture"])
        return dummy, frames

    def test_new_release_loader_and_tamper_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            dummy, frames = self._fixture(root)
            with patch("abacus_bhishma.es_contract_session_indicators.publication_sources", return_value=[("producer.py", dummy)]), \
                 patch("abacus_bhishma.es_contract_session_indicators.prepare_frames", return_value=frames):
                manifest = build_release(root, release_id="synthetic", request_path="request.yaml")
            digest = sha256_file(manifest)
            self.assertEqual(load_release(root, manifest, digest, table="bars5").close.iloc[0], 100.)
            output = root / "data/features/es_contract_session_indicators/version=1.0.0/table=bars5/part-000.parquet"
            with output.open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaisesRegex(ValueError, "size/SHA-256 mismatch"):
                load_release(root, manifest, digest, table="bars5")
            with self.assertRaises(FileExistsError):
                build_release(root, release_id="another", request_path="request.yaml")

    def test_changed_executed_source_refuses_promotion_and_retains_stage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            dummy, frames = self._fixture(root)

            def prepare(*args, **kwargs):
                dummy.write_text("changed during numerical preparation\n")
                return frames

            with patch("abacus_bhishma.es_contract_session_indicators.publication_sources", return_value=[("producer.py", dummy)]), \
                 patch("abacus_bhishma.es_contract_session_indicators.prepare_frames", side_effect=prepare):
                with self.assertRaisesRegex(ValueError, "source or retained copy changed"):
                    build_release(root, release_id="synthetic", request_path="request.yaml")
            self.assertFalse((root / "data/features/es_contract_session_indicators/version=1.0.0").exists())
            self.assertTrue((root / "data/staging/es_contract_session_indicators/synthetic/provenance/producer.py").is_file())


if __name__ == "__main__":
    unittest.main()
