"""Numerical and boundary checks with synthetic saved-ledger observations."""

from __future__ import annotations

import csv
import importlib.util
import math
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "per_future_stats.py"
SPEC = importlib.util.spec_from_file_location("forex25_per_future_stats", MODULE_PATH)
stats = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stats)


def observation(
    index=0, *, when=None, symbol="6E", mode="combined", horizon=5,
    direction=1, mfe=12, mae=6, close=3, complete=True, codes="1",
    news_type="U.S. CPI", elapsed=None,
):
    instant = datetime.fromisoformat(when.replace("Z", "+00:00")) if when else datetime(2026, 1, 5, 14, 30, tzinfo=timezone.utc) + timedelta(days=index)
    tick = .00005
    parts = [int(value) for value in codes.split(";")]
    row = {
        "symbol": symbol, "mode": mode, "event_epoch": int(instant.timestamp()),
        "event_utc": instant.astimezone(timezone.utc).isoformat(),
        "event_ny": instant.astimezone(ZoneInfo("America/New_York")).isoformat(),
        "month_chicago": instant.astimezone(stats.CHICAGO).strftime("%Y-%m"),
        "entry_price": 1.0, "direction": direction,
        "side": "Long" if direction == 1 else "Short",
        "type_code": 13 if len(parts) > 1 else parts[0],
        "news_type": news_type, "component_category_codes": codes,
        "component_count": len(parts), "has_us": any(code <= 5 for code in parts),
        "has_local": any(code > 5 for code in parts), "event_titles": news_type,
        "horizon_bars": horizon, "complete": complete,
        "elapsed_calendar_minutes": (elapsed if elapsed is not None else horizon * 15) if complete else None,
    }
    for measure, value in (("mfe", mfe), ("mae", mae), ("close", close)):
        row[f"{measure}_price"] = value * tick if complete else None
        row[f"{measure}_ticks"] = value if complete else None
        row[f"{measure}_percent"] = value * tick * 100 if complete else None
    return row


class PerFutureStatisticsTests(unittest.TestCase):
    def test_employment_code_zero_standalone_and_mixed_are_valid(self):
        rows = [
            observation(0, mode="us_only", codes="0", news_type="U.S. Employment"),
            observation(1, codes="0;8", news_type="Mixed types (same timestamp)"),
        ]
        groups = stats.build_tables(rows)["by_type"]
        self.assertEqual({row["type_code"] for row in groups}, {0, 13})
        self.assertEqual(sum(row["signals"] for row in groups), 2)

    def test_complete_denominators_quantiles_and_elapsed_time(self):
        rows = [
            observation(0, mfe=10, mae=5, close=-10, elapsed=75),
            observation(1, mfe=20, mae=10, close=0, elapsed=150, direction=-1),
            observation(2, mfe=30, mae=15, close=20, elapsed=300),
            observation(3, complete=False, direction=-1),
        ]
        result, = stats.aggregate(rows, [])
        self.assertEqual((result["signals"], result["completed"], result["pending"]), (4, 3, 1))
        self.assertEqual((result["long_signals"], result["short_signals"]), (2, 2))
        for sign in ("favorable", "adverse", "flat"):
            self.assertEqual(result[f"{sign}_close_count"], 1)
            self.assertAlmostEqual(result[f"{sign}_close_percent"], 100 / 3)
        self.assertEqual(result["average_mfe_ticks"], 20)
        self.assertEqual(result["median_mfe_ticks"], 20)
        self.assertAlmostEqual(result["average_close_ticks"], 10 / 3)
        self.assertEqual(result["median_close_ticks"], 0)
        self.assertEqual(result["p10_close_ticks"], -8)
        self.assertEqual(result["p25_close_ticks"], -5)
        self.assertEqual(result["p75_close_ticks"], 10)
        self.assertEqual(result["p90_close_ticks"], 16)
        self.assertEqual((result["min_close_ticks"], result["max_close_ticks"]), (-10, 20))
        self.assertEqual(result["mfe_mae_ratio"], 2)
        self.assertEqual(result["average_elapsed_minutes"], 175)
        self.assertEqual(result["median_elapsed_minutes"], 150)
        self.assertEqual(result["max_elapsed_minutes"], 300)
        self.assertEqual(result["sample_support"], "n<10")

    def test_empty_input_and_pending_only_have_no_outcome_estimates(self):
        self.assertEqual(stats.aggregate([], []), [])
        result, = stats.aggregate([observation(complete=False)], [])
        self.assertEqual((result["signals"], result["completed"], result["pending"]), (1, 0, 1))
        for key, value in result.items():
            if key.startswith(("average_", "median_", "p10_", "p25_", "p75_", "p90_", "min_", "max_")) or key.endswith("_percent") or key == "mfe_mae_ratio":
                with self.subTest(key=key):
                    self.assertIsNone(value)
        self.assertEqual(result["favorable_close_count"], 0)
        self.assertEqual(result["mfe_above_mae_count"], 0)

    def test_single_sample_quantiles_and_strict_positive_close(self):
        result, = stats.aggregate([observation(mfe=7, mae=3, close=1e-12)], [])
        for label in ("p10", "p25", "p75", "p90"):
            self.assertEqual(result[f"{label}_mfe_ticks"], 7)
            self.assertEqual(result[f"{label}_mae_ticks"], 3)
            self.assertEqual(result[f"{label}_close_ticks"], 1e-12)
        self.assertEqual(result["favorable_close_percent"], 100)
        self.assertEqual(result["flat_close_count"], 0)

    def test_source_mfe_above_mae_tolerance_excludes_near_ties(self):
        near = observation(0, mfe=2 + 8e-7, mae=2)
        distinct = observation(1, mfe=2 + 4e-6, mae=2)
        self.assertGreater(near["mfe_price"], near["mae_price"])
        result, = stats.aggregate([near, distinct], [])
        self.assertEqual(result["mfe_above_mae_count"], 1)
        self.assertEqual(result["mfe_above_mae_percent"], 50)

    def test_zero_mae_ratio_is_null_and_support_threshold_uses_completed(self):
        rows = [observation(index, mae=0) for index in range(10)]
        result, = stats.aggregate(rows, [])
        self.assertIsNone(result["mfe_mae_ratio"])
        self.assertEqual(result["sample_support"], "n>=10")
        rows[-1] = observation(9, complete=False)
        result, = stats.aggregate(rows, [])
        self.assertEqual(result["sample_support"], "n<10")

    def test_modes_contracts_and_horizons_are_mandatory_separate_groups(self):
        rows = [
            observation(mode="combined", close=10),
            observation(mode="us_only", close=-20),
            observation(mode="local_only", codes="6", news_type="Local CPI", close=30),
            observation(symbol="6B", close=40),
            observation(horizon=10, close=50),
        ]
        result = stats.aggregate(rows, [])
        self.assertEqual(len(result), 5)
        self.assertTrue(all(row["signals"] == 1 for row in result))
        self.assertEqual([row["average_close_ticks"] for row in result], [10, 50, -20, 30, 40])
        self.assertTrue(all(set(stats.BASE_GROUP_COLUMNS) <= row.keys() for row in result))

    def test_mixed_types_remain_an_exclusive_partition(self):
        rows = [
            observation(0, codes="1", news_type="U.S. CPI", close=1),
            observation(1, codes="6", news_type="Local CPI", close=2),
            observation(2, codes="1;6", news_type="Mixed types (same timestamp)", close=6),
        ]
        tables = stats.build_tables(rows)
        self.assertEqual(sum(row["signals"] for row in tables["by_type"]), 3)
        mixed, = [row for row in tables["by_type"] if row["type_code"] == 13]
        self.assertEqual((mixed["signals"], mixed["average_close_ticks"]), (1, 6))
        self.assertEqual(tables["overall"][0]["average_close_ticks"], 3)

    def test_all_twelve_table_families_partition_each_base_group(self):
        rows = [
            observation(0, when="2025-12-31T23:00:00Z", close=1),
            observation(1, when="2026-01-06T15:00:00Z", close=2, direction=-1),
            observation(2, when="2026-02-06T16:00:00Z", close=3, codes="6", news_type="Local CPI"),
            observation(3, when="2026-04-06T16:00:00Z", complete=False),
        ]
        tables = stats.build_tables(rows)
        self.assertEqual(tuple(tables), tuple(stats.TABLE_DIMENSIONS))
        self.assertEqual(len(tables), 12)
        for name, groups in tables.items():
            with self.subTest(table=name):
                self.assertEqual(sum(row["signals"] for row in groups), 4)
                self.assertEqual(sum(row["completed"] for row in groups), 3)
                self.assertAlmostEqual(math.fsum((row["average_close_ticks"] or 0) * row["completed"] for row in groups), 6)
        self.assertTrue(all("week_start_chicago" in row for row in tables["weekly"]))

    def test_periods_use_chicago_and_iso_week_year_at_year_boundary(self):
        row = stats.enrich(observation(when="2021-01-01T00:15:00Z"))
        self.assertEqual(row["month_chicago"], "2020-12")
        self.assertEqual(row["week_chicago"], "2020-W53")
        self.assertEqual(row["week_start_chicago"], "2020-12-28")
        self.assertEqual(row["year"], 2020)
        self.assertEqual(row["quarter"], "2020-Q4")
        self.assertEqual(row["weekday_chicago"], "4 Thu")
        self.assertEqual(row["hour_chicago"], "18:00")
        row = stats.enrich(observation(when="2021-01-01T15:00:00Z"))
        self.assertEqual((row["year"], row["week_chicago"]), (2021, "2020-W53"))

    def test_daylight_saving_fold_and_gap_use_event_instant(self):
        before = stats.enrich(observation(when="2026-11-01T06:30:00Z"))
        after = stats.enrich(observation(when="2026-11-01T07:30:00Z"))
        self.assertEqual((before["hour_chicago"], after["hour_chicago"]), ("01:00", "01:00"))
        rows = [observation(when="2026-03-08T07:30:00Z"), observation(when="2026-03-08T08:30:00Z")]
        table = stats.build_tables(rows)["hour"]
        self.assertEqual([row["hour_chicago"] for row in table], ["01:00", "03:00"])

    def test_deterministic_results_and_stable_sum(self):
        rows = [observation(0, close=1e16), observation(1, close=1), observation(2, close=-1e16)]
        forward = stats.build_tables(rows)
        self.assertEqual(forward, stats.build_tables(reversed(rows)))
        self.assertEqual(forward["overall"][0]["average_close_ticks"], 1 / 3)

    def test_csv_loader_types_enriches_and_retains_extra_source_fields(self):
        row = observation()
        row["fast_ema20"] = "1.234"
        serialized = {key: "" if value is None else int(value) if isinstance(value, bool) else value for key, value in row.items()}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(serialized))
                writer.writeheader()
                writer.writerow(serialized)
            loaded, = stats.load_ledger(path)
        self.assertIsInstance(loaded["horizon_bars"], int)
        self.assertIsInstance(loaded["complete"], bool)
        self.assertIsInstance(loaded["close_ticks"], float)
        self.assertEqual(loaded["week_chicago"], "2026-W02")
        self.assertEqual(loaded["fast_ema20"], "1.234")

    def test_duplicate_observation_keys_fail_but_distinct_horizons_survive(self):
        with self.assertRaisesRegex(ValueError, "duplicate observation key"):
            stats.aggregate([observation(), observation()], [])
        self.assertEqual(len(stats.aggregate([observation(), observation(horizon=10)], [])), 2)

    def test_nonfinite_numeric_values_fail(self):
        for field in (*stats.OUTCOME_COLUMNS, "entry_price", "elapsed_calendar_minutes"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(field=field, value=value):
                    row = observation()
                    row[field] = value
                    with self.assertRaisesRegex(ValueError, "finite number"):
                        stats.aggregate([row], [])

    def test_null_completed_and_nonnull_pending_outcomes_fail(self):
        for field in (*stats.OUTCOME_COLUMNS, "elapsed_calendar_minutes"):
            with self.subTest(field=field):
                row = observation()
                row[field] = None
                with self.assertRaisesRegex(ValueError, "complete observation has null"):
                    stats.aggregate([row], [])
                pending = observation(complete=False)
                pending[field] = 0
                with self.assertRaisesRegex(ValueError, "pending observation must have null"):
                    stats.aggregate([pending], [])

    def test_invalid_period_clock_side_and_elapsed_values_fail(self):
        failures = (
            ("month_chicago", "2025-12", "month_chicago differs"),
            ("event_utc", "2026-01-05T14:30:00", "lacks an offset"),
            ("event_ny", "2026-01-06T09:30:00-05:00", "differs from event_epoch"),
            ("side", "Short", "side does not match"),
            ("elapsed_calendar_minutes", 60, "shorter than"),
            ("mae_ticks", -1, "nonnegative"),
            ("close_ticks", -1, "close sign differs"),
            ("complete", "False", "must be an integer"),
        )
        for field, value, message in failures:
            with self.subTest(field=field):
                row = observation()
                row[field] = value
                with self.assertRaisesRegex(ValueError, message):
                    stats.aggregate([row], [])

    def test_category_mode_and_cross_horizon_metadata_validation(self):
        failures = (
            ({"type_code": 13}, "exclusive Mixed"),
            ({"component_category_codes": "1;1"}, "unique codes"),
            ({"has_local": True}, "differs from selected"),
            ({"component_count": 0}, "smaller than distinct"),
            ({"mode": "local_only"}, "contains a U.S."),
        )
        for fields, message in failures:
            with self.subTest(fields=fields):
                with self.assertRaisesRegex(ValueError, message):
                    stats.aggregate([{**observation(), **fields}], [])
        with self.assertRaisesRegex(ValueError, "event metadata differs across horizons"):
            stats.aggregate([observation(), observation(horizon=10, direction=-1)], [])
        with self.assertRaisesRegex(ValueError, "news_type label changes"):
            stats.aggregate([observation(), observation(1, news_type="Renamed CPI")], [])

    def test_unsafe_group_dimensions_and_duplicate_columns_fail(self):
        with self.assertRaisesRegex(ValueError, "unsupported group columns"):
            stats.aggregate([observation()], ["close_ticks"])
        with self.assertRaisesRegex(ValueError, "contains duplicates"):
            stats.aggregate([observation()], ["news_type", "news_type"])
        result, = stats.aggregate([observation()], ["symbol", "mode", "horizon_bars"])
        self.assertEqual(result["signals"], 1)

    def test_csv_headers_and_ragged_rows_fail(self):
        texts = ("symbol,symbol\n6E,6E\n", "symbol,mode\n6E,combined\n")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.csv"
            for text in texts:
                with self.subTest(text=text):
                    path.write_text(text)
                    with self.assertRaisesRegex(ValueError, "duplicate columns|missing columns"):
                        stats.load_ledger(path)
            row = observation()
            path.write_text(",".join(row) + "\n" + "only-one-field\n")
            with self.assertRaisesRegex(ValueError, "different number of fields"):
                stats.load_ledger(path)


if __name__ == "__main__":
    unittest.main()
