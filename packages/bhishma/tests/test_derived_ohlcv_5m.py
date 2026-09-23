from __future__ import annotations

from datetime import date, datetime, timezone
import unittest

import numpy as np
import pyarrow as pa

from abacus_bhishma.continuous_phase2 import adjusted_schema
from abacus_bhishma.derived_ohlcv_5m import (
    _aggregate_table,
    _local_clock,
    output_schema,
)


def _source_table() -> pa.Table:
    schema = adjusted_schema("source-manifest-hash")
    base = int(datetime(2024, 1, 2, 14, 30, tzinfo=timezone.utc).timestamp() * 1e9)
    offsets = [0, 1, 2, 3, 4, 5, 7]
    rows = []
    for index, offset in enumerate(offsets):
        second_contract = offset >= 7
        adjustment = 20_000_000_000 if second_contract else 10_000_000_000
        raw = 100_000_000_000 + index * 250_000_000
        rows.append(
            {
                "ts_event": datetime.fromtimestamp((base + offset * 60_000_000_000) / 1e9, timezone.utc),
                "session_date": date(2024, 1, 2),
                "product": "ES",
                "continuous_symbol": "ES.v.0",
                "instrument_id": 2 if second_contract else 1,
                "raw_symbol": "ESH4" if second_contract else "ESZ3",
                "open": raw + adjustment,
                "high": raw + adjustment + 250_000_000,
                "low": raw + adjustment - 250_000_000,
                "close": raw + adjustment,
                "volume": index + 1,
                "mapping_start": date(2023, 12, 1),
                "mapping_end": date(2024, 3, 1),
                "roll_id": 2 if second_contract else 1,
                "is_roll": second_contract,
                "source_batch": "test",
                "price_adjustment": adjustment,
            }
        )
    return pa.Table.from_pylist(rows, schema=schema)


class DerivedOhlcvTests(unittest.TestCase):
    def test_aggregate_keeps_partial_and_nulls_mixed_lineage(self) -> None:
        schema = output_schema("source", "request")
        source = _source_table()
        table, stats = _aggregate_table(
            source,
            "ES",
            2024,
            {("ES", 1): 250_000_000, ("ES", 2): 250_000_000},
            schema,
            0,
            np.iinfo(np.int64).max,
        )
        self.assertEqual(table.num_rows, 2)
        self.assertEqual(table["source_bar_count"].to_pylist(), [5, 2])
        self.assertEqual(table["is_partial_bar"].to_pylist(), [False, True])
        self.assertEqual(table["volume"].to_pylist(), [15, 13])
        self.assertEqual(table["first_raw_symbol"].to_pylist(), ["ESZ3", "ESZ3"])
        self.assertEqual(table["last_raw_symbol"].to_pylist(), ["ESZ3", "ESH4"])
        self.assertEqual(table["is_mixed_contract_bar"].to_pylist(), [False, True])
        self.assertEqual(table["is_mixed_adjustment_bar"].to_pylist(), [False, True])
        self.assertEqual(table["raw_symbol"].to_pylist(), ["ESZ3", None])
        self.assertEqual(table["instrument_id"].to_pylist(), [1, None])
        self.assertEqual(table["roll_id"].to_pylist(), [1, None])
        self.assertEqual(table["price_adjustment"].to_pylist(), [10_000_000_000, None])
        self.assertEqual(table["contains_roll"].to_pylist(), [False, True])
        self.assertEqual(stats["source_bar_count_sum"], source.num_rows)

    def test_local_clock_is_dst_aware(self) -> None:
        before = int(datetime(2024, 3, 10, 6, 55, tzinfo=timezone.utc).timestamp() * 1e9)
        after = int(datetime(2024, 3, 10, 7, 0, tzinfo=timezone.utc).timestamp() * 1e9)
        _, minutes = _local_clock(np.asarray([before, after], dtype=np.int64))
        self.assertEqual(minutes.tolist(), [1 * 60 + 55, 3 * 60])
