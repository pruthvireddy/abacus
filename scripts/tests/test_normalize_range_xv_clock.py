from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "normalize_range_xv_clock", Path(__file__).resolve().parents[1] / "normalize-range-xv-clock.py"
)
assert SPEC is not None and SPEC.loader is not None
clock = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(clock)


class RangeXVClockTests(unittest.TestCase):
    def test_fixed_export_offset_maps_seasonal_opens_to_eastern_six_pm(self):
        cases = [
            (b"2026-01-04 19:00:00", "2026-01-04 18:00:00", "2026-01-05"),
            (b"2026-07-05 18:00:00", "2026-07-05 18:00:00", "2026-07-06"),
            (b"2026-01-05 00:30:00", "2026-01-04 23:30:00", "2026-01-05"),
        ]
        for raw, expected, session in cases:
            with self.subTest(raw=raw):
                converted = clock.canonical_stamp(raw)
                self.assertEqual(converted.isoformat(sep=" "), expected)
                self.assertEqual(clock.session_day(converted).isoformat(), session)

    def test_stream_keeps_source_and_prices_and_recomputes_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            output = Path(directory) / "output.csv"
            values = [
                ("04-01-2026 19:00:00", "2026-01-04 19:00:00", "2026-01-05", "next_bar_start_same_second"),
                ("04-01-2026 19:00:00", "2026-01-04 19:00:00", "2026-01-05", "next_bar_start_proxy"),
                ("05-01-2026 00:30:00", "2026-01-05 00:30:00", "2026-01-05", "unavailable_session_boundary"),
                ("05-01-2026 19:00:00", "2026-01-05 19:00:00", "2026-01-06", "unavailable_session_boundary"),
                ("05-07-2026 18:00:00", "2026-07-05 18:00:00", "2026-07-06", "unavailable_export_end"),
            ]
            with source.open("wb") as stream:
                stream.write(clock.HEADER)
                for row, (raw, stamp, session, status) in enumerate(values, start=1):
                    stream.write(f"{row};{raw};{stamp};;;{status};{session};100;101;99;100\n".encode())
            result = clock.normalize_file(source, output)
            rows = [line.split(";") for line in output.read_text().splitlines()[1:]]
            self.assertEqual(result["rows"], 5)
            self.assertEqual(result["winter_rows_shifted"], 4)
            self.assertEqual(result["changed_session_dates"], 0)
            self.assertEqual(result["changed_completion_statuses"], 0)
            self.assertEqual(rows[0][2:6], ["2026-01-04 18:00:00", "2026-01-04 18:00:00", "0", "next_bar_start_same_second"])
            self.assertEqual(rows[1][2:6], ["2026-01-04 18:00:00", "2026-01-04 23:30:00", "19800", "next_bar_start_proxy"])
            self.assertEqual(rows[2][2:6], ["2026-01-04 23:30:00", "", "", "unavailable_session_boundary"])
            self.assertEqual(rows[4][2], "2026-07-05 18:00:00")
            self.assertEqual([row[1] for row in rows], [item[0] for item in values])
            self.assertTrue(all(row[7:] == ["100", "101", "99", "100"] for row in rows))


if __name__ == "__main__":
    unittest.main()
