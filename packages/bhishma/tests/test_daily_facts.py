"""Focused coverage for Daily Facts timing, nulls and release boundaries."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

from abacus_bhishma.daily_facts import (MINUTE, MINUTE_COLUMNS, context_facts, measure_window,
                                        minute_arrays, output_schema, session_facts, window_bounds)
from abacus_bhishma.daily_facts_loader import DATA_PATH, DATASET_ID, VERSION, load_daily_facts
from abacus_bhishma.daily_facts_postgres import _layout, _matches
from abacus_bhishma.daily_facts_release import _preflight_publication
from abacus_bhishma.provenance import sha256_file

CONTRACT = (42, "TEST1", 7)
DAY = date(2025, 3, 10)


def minutes(start, count, *, skip=(), duplicate=False, offset=None, invalid=None, mismatch=None,
            volume=2, price=100_000_000_000):
    rows = []
    for index in range(count):
        if index in skip:
            continue
        stamp = start + index * MINUTE
        if index == offset:
            stamp += timedelta(seconds=1)
        rows.append((stamp, DAY, price, price + 3_000_000_000,
                     price + (2_000_000_000 if index == invalid else 0), price + 1_000_000_000,
                     volume, 43 if index == mismatch else CONTRACT[0], CONTRACT[1], CONTRACT[2]))
    if duplicate:
        rows.insert(1, rows[0])
    types = (pa.timestamp("ns", tz="UTC"), pa.date32(), *([pa.int64()] * 4), pa.uint64(),
             pa.uint32(), pa.string(), pa.int16())
    return minute_arrays(pa.table({
        name: pa.array([row[i] for row in rows], type=types[i])
        for i, name in enumerate(MINUTE_COLUMNS)
    }))


class DailyFactsTest(unittest.TestCase):
    def test_postgres_layout_keeps_cross_window_facts_in_their_own_families(self):
        tables, projection = _layout(output_schema())
        self.assertIn("rth_gap_points", tables["daily_sessions"])
        self.assertIn("first60_volume_share", tables["daily_sessions"])
        self.assertIn("globex_to_rth_end_missing_minutes", tables["daily_vwap_facts"])
        self.assertNotIn("volume_share", tables["daily_window_facts"])
        self.assertEqual(projection["last60_volume"], 'last60."volume" AS "last60_volume"')

    def test_postgres_comparison_detects_float_and_decimal_representation_changes(self):
        self.assertTrue(_matches(-0.0, Decimal("-0"), pa.float64()))
        self.assertFalse(_matches(-0.0, Decimal("0"), pa.float64()))
        self.assertFalse(_matches(1.0, Decimal("1.0000000000000002"), pa.float64()))
        self.assertFalse(_matches(Decimal("1.000000000"), Decimal("1"), pa.decimal128(20, 9)))

    def test_asset_windows_and_dst(self):
        before = window_bounds("ES", date(2025, 3, 7))
        after = window_bounds("ES", DAY)
        self.assertEqual(before["rth"][0].hour, 14)
        self.assertEqual(after["rth"][0].hour, 13)
        self.assertEqual(after["globex"][0].weekday(), 6)
        self.assertEqual(after["globex"][1] - after["globex"][0], 1380 * MINUTE)
        gc = window_bounds("GC", DAY)
        self.assertEqual(gc["rth"][0].minute, 20)
        self.assertEqual(gc["rth"][1] - gc["rth"][0], 310 * MINUTE)

    def test_exact_price_and_terminal_endpoint(self):
        start, end = window_bounds("ES", DAY)["or15"]
        row, vwap, status = measure_window(minutes(start, 16), start, end, CONTRACT, "eligible", vwap=True)
        self.assertEqual(row["volume"], 30)
        self.assertEqual(row["open"], Decimal("100"))
        self.assertEqual(row["close"], Decimal("101"))
        self.assertEqual(row["range_points"], Decimal("3"))
        self.assertEqual(row["open_available_at"], start + MINUTE)
        self.assertEqual(row["aggregate_available_at"], end)
        self.assertEqual(status, "ready")
        self.assertAlmostEqual(vwap, 304 / 3)

    def test_missing_overnight_preserves_rth_and_open(self):
        bounds = window_bounds("ES", DAY)
        start, end = bounds["globex"]
        arrays = minutes(start, 1380, skip=(10, 930 + 20))
        row = session_facts("ES", DAY, arrays, CONTRACT, CONTRACT, False, "calendar",
                            "eligible", [], {"rth_close": Decimal("99")})
        self.assertIsNone(row["globex_volume"])
        self.assertIsNone(row["globex_vwap_at_rth_open"])
        self.assertIsNone(row["rth_volume"])
        self.assertEqual(row["rth_open"], Decimal("100"))
        self.assertEqual(row["or15_volume"], 30)
        self.assertEqual(row["last60_volume"], 120)
        self.assertEqual(row["rth_gap_points"], Decimal("1"))

    def test_quality_counts_reject_irregular_rows(self):
        start, end = window_bounds("ES", DAY)["or15"]
        for kwargs, reason, count in (
            ({"duplicate": True}, "duplicate_minutes", "duplicate_rows"),
            ({"offset": 2}, "off_grid_minutes", "off_grid_rows"),
            ({"invalid": 3}, "invalid_ohlcv", "invalid_rows"),
            ({"mismatch": 4}, "contract_mismatch", "contract_mismatch_rows"),
        ):
            with self.subTest(reason=reason):
                row, *_ = measure_window(minutes(start, 15, **kwargs), start, end, CONTRACT, "eligible")
                self.assertEqual(row["status"], reason)
                self.assertEqual(row[count], 1)
                self.assertIsNone(row["volume"])

    def test_excluded_and_zero_denominators(self):
        start, end = window_bounds("GC", DAY)["or15"]
        arrays = minutes(start, 15, volume=0, price=0)
        row, vwap, reason = measure_window(arrays, start, end, CONTRACT, "eligible", vwap=True)
        self.assertEqual(row["volume"], 0)
        self.assertEqual(row["return_status"], "zero_denominator")
        self.assertIsNone(row["return_fraction"])
        self.assertIsNone(vwap)
        self.assertEqual(reason, "zero_denominator")
        excluded, *_ = measure_window(arrays, start, end, CONTRACT, "calendar_excluded")
        self.assertEqual(excluded["observed_rows"], 15)
        self.assertIsNone(excluded["open"])
        self.assertIsNone(excluded["volume"])

    def test_roll_and_prior_weekday_exclusion(self):
        start, _ = window_bounds("GC", DAY)["globex"]
        for prior, roll, reference, reason in (
            ((40, "OLD", 6), True, {"rth_close": Decimal("99")}, "roll_reference"),
            (CONTRACT, False, {"rth_close": None}, "prior_rth_unavailable"),
            (CONTRACT, False, None, "prior_outside_pilot"),
        ):
            with self.subTest(reason=reason):
                row = session_facts("GC", DAY, minutes(start, 1380), CONTRACT, prior,
                                    roll, "calendar", "eligible", [], reference)
                self.assertEqual(row["prior_session_date"], date(2025, 3, 7))
                self.assertEqual(row["prior_rth_close_status"], reason)
                self.assertIsNone(row["rth_gap_points"])
                self.assertEqual(row["rth_open"], Decimal("100"))

    def test_context_staleness_and_future_refusal(self):
        cutoff = datetime(2025, 3, 10, 13, 30, tzinfo=timezone.utc)
        source = {"trading_day": DAY, "available_at": cutoff - timedelta(days=7), "close": 18.0}
        valid = context_facts(source, "VIX", "TVC:VIX", cutoff, "eligible")
        self.assertEqual(valid["vol_index_close_preopen"], 18.0)
        source["available_at"] -= timedelta(seconds=1)
        stale = context_facts(source, "VIX", "TVC:VIX", cutoff, "eligible")
        self.assertEqual(stale["vol_index_status"], "stale_context")
        self.assertIsNone(stale["vol_index_close_preopen"])
        source["available_at"] = cutoff + timedelta(seconds=1)
        with self.assertRaisesRegex(ValueError, "future"):
            context_facts(source, "VIX", "TVC:VIX", cutoff, "eligible")

    def test_loader_projection_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            leaf = DATA_PATH / "product=ES/part-000.parquet"
            path = root / leaf
            path.parent.mkdir(parents=True)
            pq.write_table(pa.table({"session_date": [date(2025, 3, 7), DAY], "volume": [2, 4]}), path)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"dataset_id": DATASET_ID, "version": VERSION, "output_files": [
                {"path": str(leaf), "bytes": path.stat().st_size, "sha256": sha256_file(path)},
            ]}))
            pin = sha256_file(manifest)
            kwargs = {"manifest_path": "manifest.json", "manifest_sha256": pin,
                      "assets": ("ES",), "start": DAY, "columns": ["volume"]}
            self.assertEqual(load_daily_facts(root, **kwargs).to_pylist(), [{"volume": 4}])
            with path.open("ab") as handle:
                handle.write(b"changed")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                load_daily_facts(root, **kwargs)

    def test_publication_refuses_existing_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _preflight_publication(root, root)
            (root / DATA_PATH).mkdir(parents=True)
            with self.assertRaisesRegex(FileExistsError, "refusing existing"):
                _preflight_publication(root, root)
