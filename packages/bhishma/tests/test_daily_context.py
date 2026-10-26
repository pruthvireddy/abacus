from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

from abacus_bhishma.daily_context import (
    SOURCE_COLUMNS,
    _parse_source,
    align_daily_context_asof,
    load_daily_context,
    lookup_daily_context_asof,
)


def _row(day: int, close: str, confirmed: str = "1") -> dict[str, str]:
    row = {name: "" for name in SOURCE_COLUMNS}
    row.update({
        "time": str(day - 6 * 3600),
        "bar_open_unix_s": str(day - 6 * 3600),
        "bar_close_unix_s": str(day + 16 * 3600),
        "trading_day_utc_unix_s": str(day),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "atr14": "2.5",
        "bar_confirmed": confirmed,
        "warmup1000_complete": "1",
        "is_1d": "1",
    })
    return row


class DailyContextTests(unittest.TestCase):
    def test_completed_bar_only_and_point_in_time_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.csv"
            day1 = int(datetime(2026, 9, 22, tzinfo=timezone.utc).timestamp())
            day2 = day1 + 86_400
            day3 = day2 + 86_400
            with source.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=SOURCE_COLUMNS)
                writer.writeheader()
                writer.writerows([
                    _row(day1, "10"),
                    _row(day2, "20"),
                    _row(day3, "30", "0"),
                ])
            table, profile = _parse_source(source, "VIX", "TVC:VIX")
            self.assertEqual(profile["raw_rows"], 3)
            self.assertEqual(profile["published_rows"], 2)
            self.assertEqual(profile["excluded_unconfirmed_rows"], 1)
            self.assertEqual(table["close"].to_pylist(), [10, 20])
            self.assertEqual(table["volume_raw"].to_pylist(), [None, None])
            destination = root / "data/features/bars/1d/feature_set=tradingview_daily_context/version=1.0.0/asset=VIX/part-000.parquet"
            destination.parent.mkdir(parents=True)
            pq.write_table(table, destination)
            before_close = datetime.fromtimestamp(day2 + 15 * 3600, timezone.utc)
            after_close = datetime.fromtimestamp(day2 + 17 * 3600, timezone.utc)
            self.assertEqual(lookup_daily_context_asof(root, "VIX", before_close, version="1.0.0")["close"], 10)
            self.assertEqual(lookup_daily_context_asof(root, "VIX", after_close, version="1.0.0")["close"], 20)
            self.assertEqual(
                [row["close"] for row in align_daily_context_asof(root, "VIX", [before_close, after_close], version="1.0.0", columns=["close"])],
                [10, 20],
            )
            self.assertEqual(load_daily_context(root, "VIX", version="1.0.0", start_date="2026-09-23", end_date="2026-09-24").num_rows, 1)
            self.assertIsNone(lookup_daily_context_asof(root, "VIX", datetime.fromtimestamp(day1 - 1, timezone.utc), version="1.0.0"))
            self.assertIsNone(lookup_daily_context_asof(root, "VIX", datetime.fromtimestamp(day3 + 8 * 86_400, timezone.utc), version="1.0.0"))

    def test_naive_lookup_time_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            lookup_daily_context_asof(Path("."), "VIX", datetime(2026, 9, 23), version="1.0.0")


if __name__ == "__main__":
    unittest.main()
