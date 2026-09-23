from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from abacus_bhishma.continuous_phase1 import (
    EXPECTED_TRANSITIONS,
    PRODUCTS,
    SOURCE_END_EXCLUSIVE,
    SOURCE_START,
    SessionCalendar,
)
from abacus_bhishma.continuous_phase2 import (
    INT64_MAX,
    Phase2Error,
    Phase2Paths,
    ReferenceCandidate,
    LastBar,
    _candidate_key,
    _prepare_build,
    choose_reference_candidate,
    compute_interval_adjustments,
    resolve_adjustments,
    safe_add_int64,
)
from abacus_bhishma.continuous_loader import continuous_path

from abacus_bhishma.paths import PathConfigurationError, resolve_publication_root

try:
    ROOT = resolve_publication_root()
except PathConfigurationError:
    ROOT = None


def ns(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(timezone.utc).timestamp()) * 1_000_000_000


class AdjustmentMathTests(unittest.TestCase):
    def test_positive_negative_and_reverse_cumulative_adjustments(self):
        adjustments = compute_interval_adjustments({1: 10, 2: -4, 3: 7}, 4)
        self.assertEqual(adjustments, [13, 3, 7, 0])
        self.assertEqual(adjustments[0] - adjustments[1], 10)
        self.assertEqual(adjustments[1] - adjustments[2], -4)
        self.assertEqual(adjustments[2] - adjustments[3], 7)

    def test_latest_contract_is_zero(self):
        self.assertEqual(compute_interval_adjustments({1: 25}, 2), [25, 0])

    def test_gap_set_must_be_complete(self):
        with self.assertRaises(Phase2Error):
            compute_interval_adjustments({1: 5}, 3)

    def test_exact_int64_addition_and_overflow_rejection(self):
        values = np.asarray([1_000_000_000, -2_000_000_000], dtype=np.int64)
        adjustments = np.asarray([250_000_000, -500_000_000], dtype=np.int64)
        np.testing.assert_array_equal(
            safe_add_int64(values, adjustments), [1_250_000_000, -2_500_000_000]
        )
        with self.assertRaises(Phase2Error):
            safe_add_int64(
                np.asarray([INT64_MAX], dtype=np.int64), np.asarray([1], dtype=np.int64)
            )


class ReferenceSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transition = {
            "product": "ES",
            "roll_id": 1,
            "old_raw_symbol": "ESM4",
            "new_raw_symbol": "ESU4",
        }

    def test_monday_roll_uses_available_friday_pair(self):
        candidates = [
            ReferenceCandidate(0, date(2024, 6, 16), 1, 10, 11),
            ReferenceCandidate(0, date(2024, 6, 15), 2, 12, 13),
            ReferenceCandidate(0, date(2024, 6, 14), 3, 14, 15),
        ]
        friday = (date(2024, 6, 14) - date(1970, 1, 1)).days
        bars = {
            _candidate_key(friday, 14): LastBar(ns("2024-06-14T20:59:00+00:00"), 100),
            _candidate_key(friday, 15): LastBar(ns("2024-06-14T20:59:00+00:00"), 105),
        }
        candidate, old, new = choose_reference_candidate(self.transition, candidates, bars)
        self.assertEqual(candidate.candidate_date, date(2024, 6, 14))
        self.assertEqual(candidate.searchback_days, 3)
        self.assertEqual(new.close - old.close, 5)

    def test_early_close_is_eligible(self):
        candidate = ReferenceCandidate(0, date(2024, 7, 3), 1, 20, 21)
        day_number = (candidate.candidate_date - date(1970, 1, 1)).days
        bars = {
            _candidate_key(day_number, 20): LastBar(ns("2024-07-03T17:14:00+00:00"), 200),
            _candidate_key(day_number, 21): LastBar(ns("2024-07-03T17:13:00+00:00"), 205),
        }
        selected, _, _ = choose_reference_candidate(self.transition, [candidate], bars)
        self.assertEqual(selected, candidate)

    def test_missing_pair_fails(self):
        candidate = ReferenceCandidate(0, date(2024, 6, 14), 3, 14, 15)
        day_number = (candidate.candidate_date - date(1970, 1, 1)).days
        bars = {_candidate_key(day_number, 14): LastBar(1, 100)}
        with self.assertRaises(Phase2Error):
            choose_reference_candidate(self.transition, [candidate], bars)

    def test_date_scoped_ids_are_separated_by_session_date(self):
        first = _candidate_key((date(2024, 1, 2) - date(1970, 1, 1)).days, 42)
        second = _candidate_key((date(2024, 1, 3) - date(1970, 1, 1)).days, 42)
        self.assertNotEqual(first, second)

    def test_dst_boundaries_and_maintenance_exclusion(self):
        calendar = SessionCalendar.build(date(2024, 1, 1), date(2025, 1, 1))
        timestamps = np.asarray(
            [
                ns("2024-01-07T23:00:00+00:00"),  # 18:00 EST Sunday
                ns("2024-07-07T22:00:00+00:00"),  # 18:00 EDT Sunday
                ns("2024-07-08T20:59:00+00:00"),  # 16:59 EDT
                ns("2024-07-08T21:00:00+00:00"),  # 17:00 EDT
            ],
            dtype=np.int64,
        )
        _, session_days, maintenance = calendar.locate(timestamps)
        expected = [date(2024, 1, 8), date(2024, 7, 8), date(2024, 7, 8), date(2024, 7, 8)]
        actual = [date(1970, 1, 1) + timedelta(days=int(day)) for day in session_days]
        self.assertEqual(actual, expected)
        self.assertEqual(maintenance.tolist(), [False, False, False, True])


class SafetyTests(unittest.TestCase):
    def test_completed_output_requires_force(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = Phase2Paths.from_root(temporary)
            paths.product_output("ES").mkdir(parents=True)
            with self.assertRaises(Phase2Error):
                _prepare_build(paths, force=False)

    @unittest.skipIf(ROOT is None, "Configure a publication root for integration tests")
    def test_loader_paths_are_backwards_compatible(self):
        unadjusted = continuous_path(ROOT, "ES")
        adjusted = continuous_path(ROOT, "ES", variant="back_adjusted")
        self.assertIn("variant=unadjusted", str(unadjusted))
        self.assertIn("variant=back_adjusted", str(adjusted))
        self.assertIn("adjustment=prior_session_close_additive_v1", str(adjusted))


@unittest.skipIf(ROOT is None, "Configure a publication root for integration tests")
class RealRollIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = Phase2Paths.from_root(ROOT)
        calendar = SessionCalendar.build(SOURCE_START, SOURCE_END_EXCLUSIVE)
        cls.schedule, cls.factors, cls.factor_arrays = resolve_adjustments(
            cls.paths, calendar, chunk_size=1_000_000
        )

    def test_real_rolls_for_all_products(self):
        rows = self.schedule.to_pylist()
        for product in PRODUCTS:
            with self.subTest(product=product):
                selected = [row for row in rows if row["product"] == product]
                self.assertEqual(len(selected), EXPECTED_TRANSITIONS[product])
                for row in selected:
                    self.assertLess(row["reference_session_date"], row["effective_session_date"])
                    self.assertEqual(
                        row["roll_gap"], row["new_reference_close"] - row["old_reference_close"]
                    )
                    self.assertEqual(
                        row["old_interval_adjustment"] - row["new_interval_adjustment"],
                        row["roll_gap"],
                    )

    def test_latest_real_intervals_are_unadjusted(self):
        for product in PRODUCTS:
            self.assertEqual(int(self.factor_arrays[product][-1]), 0)


if __name__ == "__main__":
    unittest.main()
