from __future__ import annotations

from datetime import date, datetime, timezone
import unittest

import numpy as np
import pyarrow as pa

from abacus_bhishma.continuous_phase2 import adjusted_schema
from abacus_bhishma.session_anchored_vwap import (
    MINUTE_NS,
    PRICE_SCALE,
    _audit_one,
    aggregate_partition,
    aggregate_session,
    anchored_features,
    calendar_regime,
    classify_events,
    holiday_sessions,
    output_schema,
    session_bounds,
)


def _source_session(
    day: date,
    product: str = "ES",
    *,
    missing_index: int | None = None,
    second_contract_at: int | None = None,
    adjustment: int = 10_000_000_000,
) -> pa.Table:
    start, _ = session_bounds(day)
    rows = []
    for index in range(1380):
        if index == missing_index:
            continue
        second = second_contract_at is not None and index >= second_contract_at
        raw = 100_000_000_000 + index * 1_000_000
        rows.append(
            {
                "ts_event": datetime.fromtimestamp((start + index * MINUTE_NS) / 1e9, timezone.utc),
                "session_date": day,
                "product": product,
                "continuous_symbol": f"{product}.v.0",
                "instrument_id": 2 if second else 1,
                "raw_symbol": f"{product}H4" if second else f"{product}Z3",
                "open": raw + adjustment,
                "high": raw + adjustment + 2_000_000,
                "low": raw + adjustment - 2_000_000,
                "close": raw + adjustment + 1_000_000,
                "volume": index % 11,
                "mapping_start": date(2023, 12, 1),
                "mapping_end": date(2024, 3, 1),
                "roll_id": 2 if second else 1,
                "is_roll": index == 0,
                "source_batch": "test",
                "price_adjustment": adjustment + (1_000_000_000 if second else 0),
            }
        )
    return pa.Table.from_pylist(rows, schema=adjusted_schema("source"))


class IndicatorTests(unittest.TestCase):
    def test_unequal_volume_population_variance_fixture(self) -> None:
        values = anchored_features(
            np.array([10.0, 20.0]),
            np.array([10.0, 20.0]),
            np.array([10.0, 20.0]),
            np.array([1, 3], dtype=np.uint64),
            0.25,
            np.array([0, 2 * MINUTE_NS]),
            2,
            0,
        )
        self.assertAlmostEqual(values["vwap"][1], 17.5)
        self.assertAlmostEqual(values["sigma"][1], np.sqrt(18.75))
        self.assertEqual(values["vwap"][0], 10.0)
        self.assertEqual(values["sigma"][0], 0.0)
        self.assertTrue(np.isnan(values["distance_sigma"][0]))

        hlc3 = anchored_features(
            np.array([12.0]),
            np.array([8.0]),
            np.array([11.0]),
            np.array([4], dtype=np.uint64),
            0.25,
            np.array([0], dtype=np.int64),
            5,
            0,
        )
        self.assertAlmostEqual(hlc3["vwap"][0], (12 + 8 + 11) / 3)

    def test_pre_anchor_zero_volume_and_all_anchor_offsets(self) -> None:
        n = 690
        price = np.full(n, 100.0)
        volume = np.ones(n, dtype=np.uint64)
        opens = np.arange(n, dtype=np.int64) * 2 * MINUTE_NS
        offsets = {"globex": 0, "asia": 120, "london": 540, "ny": 930}
        for name, offset in offsets.items():
            values = anchored_features(price, price, price, volume, 0.25, opens, 2, offset)
            start = offset // 2
            if start:
                self.assertFalse(values["anchor_active"][start - 1], name)
                self.assertTrue(np.isnan(values["vwap"][start - 1]), name)
            self.assertTrue(values["anchor_active"][start], name)
            self.assertEqual(values["minutes_since_anchor"][start], 2, name)

        zero = anchored_features(
            np.array([10.0, 11.0, 12.0]),
            np.array([10.0, 11.0, 12.0]),
            np.array([10.0, 11.0, 12.0]),
            np.array([0, 0, 2], dtype=np.uint64),
            0.25,
            np.arange(3, dtype=np.int64) * 2 * MINUTE_NS,
            2,
            0,
        )
        self.assertTrue(np.isnan(zero["vwap"][0]))
        self.assertEqual(zero["cumulative_volume"][1], 0)
        self.assertEqual(zero["contributing_bar_count"][2], 1)
        self.assertEqual(zero["vwap"][2], 12.0)

    def test_event_equality_and_sigma_rules(self) -> None:
        equal_reentry = classify_events(13, 12, 10, 10, 12, 12, 8, 8, 1, 1)
        self.assertTrue(equal_reentry["reenter_from_above_2sigma"])
        self.assertFalse(equal_reentry["exit_above_upper_2sigma"])
        equality_is_not_cross = classify_events(10, 10, 10, 10, 12, 12, 8, 8, 1, 1)
        self.assertFalse(equality_is_not_cross["cross_above_vwap"])
        self.assertFalse(equality_is_not_cross["cross_below_vwap"])
        undefined_band = classify_events(13, 12, 10, 10, 12, 12, 8, 8, 0, 1)
        self.assertIsNone(undefined_band["reenter_from_above_2sigma"])

    def test_constant_shift_invariance_and_truncation_causality(self) -> None:
        price = np.array([100.0, 101.0, 99.0, 102.0, 100.5])
        volume = np.array([1, 7, 3, 2, 5], dtype=np.uint64)
        opens = np.arange(len(price), dtype=np.int64) * 5 * MINUTE_NS
        base = anchored_features(price, price, price, volume, 0.25, opens, 5, 0)
        shifted = anchored_features(price + 25, price + 25, price + 25, volume, 0.25, opens, 5, 0)
        np.testing.assert_allclose(shifted["vwap"], base["vwap"] + 25)
        np.testing.assert_allclose(shifted["sigma"], base["sigma"])
        np.testing.assert_allclose(shifted["distance_points"], base["distance_points"])
        prefix = anchored_features(price[:3], price[:3], price[:3], volume[:3], 0.25, opens[:3], 5, 0)
        np.testing.assert_allclose(prefix["vwap"], base["vwap"][:3])
        np.testing.assert_allclose(prefix["sigma"], base["sigma"][:3])


class AggregationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = _source_session(date(2024, 1, 2))

    def test_2m_and_5m_direct_aggregation_volume_and_availability(self) -> None:
        outputs = {}
        for interval in (2, 5):
            schema = output_schema("source", "calendar", "indicator", interval)
            first = aggregate_session(self.source, "ES", interval, 250_000_000, schema)
            second = aggregate_session(self.source, "ES", interval, 250_000_000, schema)
            outputs[interval] = first
            self.assertEqual(first, second)
            self.assertEqual(first.num_rows, 1380 // interval)
            self.assertTrue(all(value == interval for value in first["source_bar_count"].to_pylist()))
            self.assertEqual(sum(first["volume"].to_pylist()), sum(self.source["volume"].to_pylist()))
            opens = first["ts_event"].cast(pa.int64()).to_numpy(zero_copy_only=False)
            closes = first["bar_close_ts"].cast(pa.int64()).to_numpy(zero_copy_only=False)
            available = first["available_at"].cast(pa.int64()).to_numpy(zero_copy_only=False)
            np.testing.assert_array_equal(closes, opens + interval * MINUTE_NS)
            np.testing.assert_array_equal(available, closes)
        # 5m is independently aggregated from source; its first volume equals five 1m rows.
        self.assertEqual(outputs[5]["volume"][0].as_py(), sum(self.source["volume"].to_pylist()[:5]))

    def test_normal_roll_at_open_is_retained(self) -> None:
        schema = output_schema("source", "calendar", "indicator", 5)
        result = aggregate_session(self.source, "ES", 5, 250_000_000, schema)
        self.assertTrue(result["is_roll"][0].as_py())
        self.assertTrue(result["contains_roll"][0].as_py())
        self.assertFalse(result["contains_roll"][1].as_py())
        asia_start = 120 // 5
        self.assertIsNone(result["asia_cross_above_vwap"][asia_start].as_py())

    def test_partition_boundary_invariance(self) -> None:
        second_source = _source_session(date(2024, 1, 3))
        combined = pa.concat_tables([self.source, second_source])
        schema = output_schema("source", "calendar", "indicator", 5)
        together, stats = aggregate_partition(
            combined,
            "ES",
            5,
            {date(2024, 1, 2), date(2024, 1, 3)},
            {("ES", 1): 250_000_000},
            schema,
        )
        separate = pa.concat_tables(
            [
                aggregate_session(self.source, "ES", 5, 250_000_000, schema),
                aggregate_session(second_source, "ES", 5, 250_000_000, schema),
            ]
        )
        self.assertEqual(together, separate)
        self.assertEqual(stats["sessions"], 2)


class CalendarEligibilityTests(unittest.TestCase):
    def test_dst_and_overnight_session_assignment(self) -> None:
        spring_start, spring_end = session_bounds(date(2024, 3, 11))
        fall_start, fall_end = session_bounds(date(2024, 11, 4))
        self.assertEqual((spring_end - spring_start) // MINUTE_NS, 1380)
        self.assertEqual((fall_end - fall_start) // MINUTE_NS, 1380)
        self.assertEqual(datetime.fromtimestamp(spring_start / 1e9, timezone.utc).hour, 22)
        self.assertEqual(datetime.fromtimestamp(fall_start / 1e9, timezone.utc).hour, 23)

    def test_holidays_early_closes_and_regimes(self) -> None:
        holidays = holiday_sessions("ES", 2024, 2025)
        self.assertIn(date(2024, 11, 28), holidays)
        self.assertIn(date(2024, 11, 29), holidays)
        self.assertIn(date(2025, 1, 9), holidays)
        self.assertEqual(calendar_regime("GC", date(2015, 9, 18)), ("comex_close_1715_v1", False))
        self.assertEqual(calendar_regime("GC", date(2015, 9, 21)), ("comex_23h_v1", True))
        self.assertFalse(calendar_regime("ES", date(2021, 6, 25))[1])
        self.assertTrue(calendar_regime("NQ", date(2021, 6, 28))[1])

    def test_missing_minute_product_independence_and_intraday_change(self) -> None:
        day = date(2024, 1, 2)
        full = _source_session(day, "ES")
        missing = _source_session(day, "GC", missing_index=10)
        coverage = (session_bounds(day)[0], session_bounds(day)[1])
        conditions = {day.replace(day=1): "available", day: "available"}
        es = _audit_one("ES", day, full, coverage, conditions, {})
        gc = _audit_one("GC", day, missing, coverage, conditions, {})
        self.assertTrue(es["eligible"])
        self.assertFalse(gc["eligible"])
        self.assertIn("missing_expected_published_minute", gc["exclusion_reasons"])

        changed = _source_session(day, "ES", second_contract_at=700)
        changed_audit = _audit_one("ES", day, changed, coverage, conditions, {})
        self.assertIn("intraday_contract_change", changed_audit["exclusion_reasons"])
        self.assertIn("intraday_adjustment_change", changed_audit["exclusion_reasons"])

    def test_degraded_source_and_holiday_exclusion(self) -> None:
        day = date(2024, 11, 28)
        source = _source_session(day, "ES")
        coverage = session_bounds(day)
        audit = _audit_one(
            "ES",
            day,
            source,
            coverage,
            {day: "degraded", date(2024, 11, 27): "available"},
            {day: ["Thanksgiving"]},
        )
        self.assertIn("source_condition_degraded", audit["exclusion_reasons"])
        self.assertIn("exchange_holiday_or_shortened_session", audit["exclusion_reasons"])


if __name__ == "__main__":
    unittest.main()
