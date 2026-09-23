from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from abacus_bhishma.continuous_phase1 import (
    EXPECTED_INTERVALS,
    EXPECTED_TRANSITIONS,
    SOURCE_END_EXCLUSIVE,
    SOURCE_START,
    ProjectPaths,
    RollInterval,
    SessionCalendar,
    _selection_models,
    iter_dbn_arrays,
    load_roll_intervals,
    resolve_instrument_master,
    select_indices,
)

ROOT = Path(__file__).resolve().parents[1]


def ns(value: str) -> int:
    return int(datetime.fromisoformat(value).astimezone(timezone.utc).timestamp()) * 1_000_000_000


class SessionCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.calendar = SessionCalendar.build(date(2023, 1, 1), date(2025, 1, 1))

    def locate(self, value: str) -> tuple[date, bool]:
        _, days, maintenance = self.calendar.locate(np.asarray([ns(value)], dtype=np.int64))
        return date(1970, 1, 1) + timedelta(days=int(days[0])), bool(maintenance[0])

    def test_standard_time_session_boundary(self):
        self.assertEqual(self.locate("2024-01-07T22:59:59+00:00"), (date(2024, 1, 7), True))
        self.assertEqual(self.locate("2024-01-07T23:00:00+00:00"), (date(2024, 1, 8), False))

    def test_daylight_saving_session_boundary(self):
        self.assertEqual(self.locate("2024-07-07T21:59:59+00:00"), (date(2024, 7, 7), True))
        self.assertEqual(self.locate("2024-07-07T22:00:00+00:00"), (date(2024, 7, 8), False))

    def test_sunday_open_and_maintenance_break(self):
        self.assertEqual(self.locate("2024-07-07T22:00:00+00:00"), (date(2024, 7, 8), False))
        self.assertEqual(self.locate("2024-07-08T21:30:00+00:00"), (date(2024, 7, 8), True))
        self.assertEqual(self.locate("2024-07-08T22:00:00+00:00"), (date(2024, 7, 9), False))


class MappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.paths = ProjectPaths.from_root(ROOT)
        cls.calendar = SessionCalendar.build(SOURCE_START, SOURCE_END_EXCLUSIVE)
        cls.mappings = load_roll_intervals(cls.paths, cls.calendar)
        cls.resolved = resolve_instrument_master(cls.paths, cls.mappings)

    def test_expected_mapping_and_transition_counts(self):
        for product, expected in EXPECTED_INTERVALS.items():
            self.assertEqual(len(self.resolved[product]), expected)
            self.assertEqual(len(self.resolved[product]) - 1, EXPECTED_TRANSITIONS[product])

    def test_every_definition_is_an_outright_future(self):
        for intervals in self.resolved.values():
            for interval in intervals:
                self.assertEqual(interval.asset, interval.product)
                self.assertEqual(interval.instrument_class, "F")
                self.assertEqual(interval.security_type, "FUT")
                self.assertTrue(interval.raw_symbol)
                self.assertIsNotNone(interval.definition_date)

    def test_first_final_and_mapping_boundary(self):
        self.assertEqual(self.resolved["ES"][0].raw_symbol, "ESM0")
        self.assertEqual(self.resolved["ES"][-1].raw_symbol, "ESZ6")
        first_roll = self.resolved["ES"][1]
        self.assertEqual(first_roll.mapping_start, date(2010, 6, 14))
        self.assertEqual(first_roll.effective_start_ns, ns("2010-06-13T22:00:00+00:00"))

    def test_date_scoped_instrument_id_reuse(self):
        rows = np.zeros(
            4,
            dtype=[("ts_event", "<u8"), ("instrument_id", "<u4")],
        )
        rows["ts_event"] = [100, 199, 200, 299]
        rows["instrument_id"] = [7, 7, 7, 7]
        intervals = {
            "ES": [
                RollInterval("ES", "ES.v.0", 0, date(2020, 1, 1), date(2020, 2, 1), 7, 100, 200, "ESA"),
                RollInterval("ES", "ES.v.0", 1, date(2020, 2, 1), date(2020, 3, 1), 7, 200, 300, "ESB"),
            ]
        }
        model = _selection_models(intervals)["ES"]
        positions, mapping_indices = select_indices(rows, model)
        np.testing.assert_array_equal(positions, [0, 1, 2, 3])
        np.testing.assert_array_equal(mapping_indices, [0, 0, 1, 1])
        self.assertEqual(model.raw_symbols[mapping_indices].tolist(), ["ESA", "ESA", "ESB", "ESB"])

    def test_real_es_roll_window_selects_only_expected_contract(self):
        model = _selection_models(self.resolved)["ES"]
        boundary = self.resolved["ES"][1].effective_start_ns
        cutoff = ns("2010-06-15T00:00:00+00:00")
        before_ids: set[int] = set()
        after_ids: set[int] = set()
        before_rows = 0
        after_rows = 0
        for records in iter_dbn_arrays(self.paths.ohlcv_dbn, count=250_000):
            positions, mapping_indices = select_indices(records, model)
            if len(positions):
                selected = records[positions]
                relevant = selected["ts_event"] < cutoff
                selected = selected[relevant]
                selected_mapping = mapping_indices[relevant]
                before = selected["ts_event"] < boundary
                after = ~before
                before_ids.update(map(int, selected["instrument_id"][before]))
                after_ids.update(map(int, selected["instrument_id"][after]))
                before_rows += int(np.count_nonzero(before))
                after_rows += int(np.count_nonzero(after))
                if len(selected_mapping):
                    self.assertTrue(np.all(selected_mapping[before] == 0))
                    self.assertTrue(np.all(selected_mapping[after] == 1))
            if int(records["ts_event"][-1]) >= cutoff:
                break
        self.assertGreater(before_rows, 0)
        self.assertGreater(after_rows, 0)
        self.assertEqual(before_ids, {self.resolved["ES"][0].instrument_id})
        self.assertEqual(after_ids, {self.resolved["ES"][1].instrument_id})


if __name__ == "__main__":
    unittest.main()
