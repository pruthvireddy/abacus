"""Numerical and real-session checks for the frozen VWAP state protocol."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.features import clock_window, extract_day, load_features, side_of, state_of
from src.outcomes import barrier_class, evaluate_landmark, load_source_year, reconcile_day

ROOT = Path(__file__).resolve().parents[3]
SCALE = 1_000_000_000


class DynamicsTest(unittest.TestCase):
    @staticmethod
    def synthetic_feature_day(reset=False):
        start = pd.Timestamp("2024-01-02T23:00:00Z")  # 18:00 New York
        opened = pd.date_range(start, periods=76, freq="2min")
        closed = opened + pd.Timedelta(minutes=2)
        anchor = [start]*76
        if reset:
            anchor[29:] = [opened[29]]*47
        price = 100*SCALE
        return pd.DataFrame({"ts_event": opened, "bar_close_ts": closed,
            "available_at": closed, "session_date": pd.Timestamp("2024-01-03").date(),
            "product": "ES", "timeframe": "2m", "instrument_id": 42, "raw_symbol": "ESH4",
            "open": price, "high": price, "low": price, "close": price,
            "volume": 1, "price_adjustment": 0, "min_tick": int(.25*SCALE),
            "is_asia_session": False, "is_london_session": False, "is_ny_session": False,
            "globex_anchor_ts": anchor, "globex_anchor_active": True,
            "globex_vwap": 100., "globex_sigma": 1.})

    def test_side_equality_and_residence_classes(self):
        self.assertEqual(side_of(100., 100.), 0)
        self.assertEqual(side_of(100.+5e-9, 100.), 0)
        self.assertEqual(state_of(np.array([1]*12+[-1]*3), 2)[0], "other")
        self.assertEqual(state_of(np.array([1]*12+[0]*2+[1]), 2)[0], "persistent")
        self.assertEqual(state_of(np.array([1,-1]*7+[1]), 2)[0], "rotational")

    def test_dst_local_clock(self):
        winter = pd.Timestamp("2024-01-10T00:00:00Z").tz_convert("America/New_York")
        summer = pd.Timestamp("2024-07-10T23:00:00Z").tz_convert("America/New_York")
        self.assertEqual((winter.hour, summer.hour), (19,19))
        self.assertEqual(clock_window(winter), "evening_asia")
        self.assertEqual(clock_window(summer), "evening_asia")

    def test_anchor_reset_and_incomplete_lookback(self):
        ordinary, _ = extract_day(self.synthetic_feature_day(), "globex", 2, 50.)
        self.assertEqual([x["local_time"][11:16] for x in ordinary], ["19:00","19:30","20:00"])
        reset, _ = extract_day(self.synthetic_feature_day(reset=True), "globex", 2, 50.)
        self.assertEqual([x["local_time"][11:16] for x in reset], ["20:00"])
        gap = self.synthetic_feature_day().drop(index=22).reset_index(drop=True)
        incomplete, counts = extract_day(gap, "globex", 2, 50.)
        self.assertNotIn("19:00", [x["local_time"][11:16] for x in incomplete])
        self.assertGreater(counts["lookback_or_contract_gap"], 0)

    def test_four_way_barrier_and_open_gap(self):
        def frame(open_, high, low):
            return pd.DataFrame({"open": [int(open_*SCALE)], "high": [int(high*SCALE)],
                                 "low": [int(low*SCALE)]})
        self.assertEqual(barrier_class(frame(100,102,98), 1, 1, .25), "ambiguous")
        gap = pd.concat([frame(100,100.5,99.5), frame(102,102,98)], ignore_index=True)
        self.assertEqual(barrier_class(gap, 1, 1, .25), "favorable")
        self.assertEqual(barrier_class(frame(100,100.5,98), 1, 1, .25), "adverse")
        self.assertEqual(barrier_class(frame(100,100.5,99.5), 1, 1, .25), "neither")

    def test_horizon_boundary_cross_tie_and_missing_minute(self):
        t = pd.Timestamp("2024-01-03T00:00:00Z")
        times = pd.date_range(t, periods=30, freq="min")
        closes = np.full(30, 100*SCALE, dtype=np.int64)
        closes[-1] = 99*SCALE
        source = pd.DataFrame({"ts_event": times, "open": 100*SCALE,
            "high": 101*SCALE, "low": 99*SCALE, "close": closes,
            "volume": 1, "raw_symbol": "ESH4", "instrument_id": 42})
        future_t = pd.date_range(t, periods=16, freq="2min")
        feature = pd.DataFrame({"available_at": future_t, "close": [101*SCALE]+[100*SCALE]*14+[99*SCALE],
            "globex_vwap": 100., "globex_anchor_ts": t-pd.Timedelta(hours=1),
            "globex_anchor_active": True, "raw_symbol": "ESH4", "instrument_id": 42,
            "price_adjustment": 0})
        row = pd.Series({"event_id": "synthetic", "timeframe": "2m", "anchor": "globex",
            "feature_index": 0, "landmark_ts": t, "raw_symbol": "ESH4", "instrument_id": 42,
            "price_adjustment": 0, "side": 1, "tick": .25, "sigma": 2.,
            "vwap": 100., "twap": 100., "close": 101.})
        result = evaluate_landmark(row, feature, source)
        self.assertTrue(result["y2_cross"])
        self.assertFalse(result["y1_residence"])
        self.assertEqual(result["first_cross_minute"], 30)
        self.assertTrue(result["paired_tie"])
        missing = evaluate_landmark(row, feature, source.drop(index=10).reset_index(drop=True))
        self.assertEqual(missing["outcome_missing"], "source_30m_gap")
        self.assertIsNone(missing["y1_residence"])

    def test_real_product_sessions_manual_identity_and_path(self):
        # Independent HLC3/volume and median calculations on one pinned session per product.
        for product in ("ES", "NQ", "GC"):
            with self.subTest(product=product):
                features = load_features(ROOT, product, 2023, "2m")
                source = load_source_year(ROOT, product, 2023)
                day = features.session_date.iloc[0]
                f = features[features.session_date == day].reset_index(drop=True)
                s = source[source.session_date == day].reset_index(drop=True)
                self.assertEqual(reconcile_day(f, s, 2), len(f))
                rows, _ = extract_day(f, "globex", 2, 50.)
                self.assertGreater(len(rows), 0)
                landmark = rows[0]
                i = landmark["feature_index"]
                h = (f.high.iloc[:i+1].to_numpy()+f.low.iloc[:i+1].to_numpy()+f.close.iloc[:i+1].to_numpy())/3/SCALE
                vol = f.volume.iloc[:i+1].to_numpy()
                self.assertAlmostEqual(landmark["vwap"], float(np.average(h, weights=vol)), places=7)
                self.assertAlmostEqual(landmark["twap"], float(np.mean(h)), places=7)
                result = evaluate_landmark(pd.Series(landmark), f, s)
                path = s[(s.ts_event >= landmark["landmark_ts"]) &
                         (s.ts_event < landmark["landmark_ts"]+pd.Timedelta(minutes=30))]
                self.assertEqual(len(path), 30)
                self.assertAlmostEqual(result["future_median"], float(np.median(path.close))/SCALE, places=7)


if __name__ == "__main__":
    unittest.main()
