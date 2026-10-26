"""Known directional sequences and strict synthetic CSV checks for Study 22."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import csv
import sys
import tempfile
import unittest


_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
from trends import Bar, extract_trends, inferred_session_date, load_bars


def make_bar(row: int, direction: str, *, stamp: datetime | None = None,
             session: date | None = None, status: str = "next_bar_start_proxy",
             eligible: bool = True, reason: str | None = None, setting: int = 4) -> Bar:
    stamp = stamp or datetime(2024, 6, 10, 9, 30) + timedelta(seconds=row)
    close = Decimal(101 if direction == "U" else 99 if direction == "D" else 100)
    completion = stamp if status == "next_bar_start_same_second" else stamp + timedelta(seconds=1)
    return Bar(setting, row, stamp, completion, session or inferred_session_date(stamp),
               Decimal(100), Decimal(101), Decimal(99), close, status, eligible, reason)


def make_sequence(text: str) -> list[Bar]:
    return [make_bar(row, direction) for row, direction in enumerate(text, 1)]


class TrendTests(unittest.TestCase):
    def test_known_reversal_doji_and_right_censored_lengths(self) -> None:
        results = list(extract_trends(make_sequence("UUDDDUZU"), 4))
        self.assertEqual(["bullish", "bearish", "bullish", "bullish"], [row.direction for row in results])
        self.assertEqual([2, 3, 1, 1], [row.observed_length for row in results])
        self.assertEqual([None, 3, 1, None], [row.length for row in results])
        self.assertEqual([True, False, False, False], [row.left_censored for row in results])
        self.assertEqual([False, False, False, True], [row.right_censored for row in results])
        self.assertEqual(["reversal", "reversal", "doji", "export_end"], [row.end_reason for row in results])
        self.assertEqual((3, 5), (results[1].start_source_row, results[1].end_source_row))
        self.assertEqual(datetime(2024, 6, 10, 9, 30, 7), results[1].termination_available_at)

    def test_initial_doji_establishes_known_left_boundary(self) -> None:
        results = list(extract_trends(make_sequence("ZUUDZ"), 4))
        self.assertEqual([2, 1], [row.length for row in results])
        self.assertEqual([False, False], [row.left_censored for row in results])

    def test_entire_single_direction_segment_is_censored_at_both_ends(self) -> None:
        row, = extract_trends(make_sequence("UUUU"), 4)
        self.assertEqual(4, row.observed_length)
        self.assertIsNone(row.length)
        self.assertTrue(row.left_censored and row.right_censored)

    def test_unsupported_row_breaks_without_stitching_or_establishing_direction(self) -> None:
        bars = make_sequence("ZUUUDDZ")
        bars[3] = replace(bars[3], completion_status="unknown", primary_eligible=False,
                          barrier_reason="completion_status:unknown")
        up, down = extract_trends(bars, 4)
        self.assertEqual((2, None, False, True), (up.observed_length, up.length, up.left_censored, up.right_censored))
        self.assertEqual((2, None, True, False), (down.observed_length, down.length, down.left_censored, down.right_censored))
        self.assertEqual("completion_status:unknown", up.end_reason)

    def test_session_change_is_barrier_even_without_an_explicit_terminal_row(self) -> None:
        bars = [make_bar(1, "Z"), make_bar(2, "U"),
                make_bar(3, "U", stamp=datetime(2024, 6, 11, 9, 30)),
                make_bar(4, "D", stamp=datetime(2024, 6, 11, 9, 31))]
        first, second, third = extract_trends(bars, 4)
        self.assertEqual("session_boundary", first.end_reason)
        self.assertTrue(first.right_censored)
        self.assertTrue(second.left_censored)
        self.assertEqual([1, 1, 1], [row.observed_length for row in (first, second, third)])

    def test_same_second_distinct_and_identical_bars_keep_source_order(self) -> None:
        stamp = datetime(2024, 6, 10, 9, 30)
        bars = [make_bar(row, direction, stamp=stamp, status="next_bar_start_same_second")
                for row, direction in enumerate("ZUUUDZ", 1)]
        up, down = extract_trends(bars, 4)
        self.assertEqual((3, 1), (up.length, down.length))
        self.assertEqual((2, 4), (up.start_source_row, up.end_source_row))
        self.assertEqual(stamp, up.termination_available_at)

    def test_doji_only_and_empty_stream_produce_no_directional_runs(self) -> None:
        self.assertEqual([], list(extract_trends(make_sequence("ZZZZ"), 4)))
        self.assertEqual([], list(extract_trends([], 4)))

    def test_price_direction_uses_decimal_without_binary_float_rounding(self) -> None:
        bar = replace(make_bar(1, "Z"), open=Decimal("100.00000000000000000001"),
                      close=Decimal("100.00000000000000000002"))
        self.assertEqual("bullish", bar.direction)

    def test_different_settings_refused_in_single_stream(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot pool"):
            list(extract_trends([make_bar(1, "U", setting=5)], 4))

    def test_inferred_year_rollover_and_timezone_refusal(self) -> None:
        self.assertEqual(date(2025, 1, 1), inferred_session_date(datetime(2024, 12, 31, 18)))
        self.assertEqual(date(2024, 12, 31), inferred_session_date(datetime(2024, 12, 31, 17, 59, 59)))
        with self.assertRaisesRegex(ValueError, "naive New York"):
            inferred_session_date(datetime(2024, 12, 31, 18, tzinfo=timezone.utc))


class LoaderTests(unittest.TestCase):
    COLUMNS = ("source_row", "source_timestamp", "bar_start_timestamp",
               "bar_completion_timestamp_proxy", "bar_duration_seconds_proxy",
               "completion_proxy_status", "session_date_proxy", "open", "high", "low", "close")

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "bars.csv"

    def rows(self, directions: str = "ZUUUDZ", *, same_second: bool = False,
             start: datetime = datetime(2024, 6, 10, 9, 30)) -> list[dict]:
        stamps = [start + timedelta(seconds=0 if same_second else index)
                  for index in range(len(directions))]
        return [{
            "source_row": str(index + 1), "source_timestamp": stamp.strftime("%Y-%d-%m %H:%M:%S"),
            "bar_start_timestamp": stamp.isoformat(sep=" "),
            "bar_completion_timestamp_proxy": stamps[index + 1].isoformat(sep=" ") if index + 1 < len(stamps) else "",
            "bar_duration_seconds_proxy": str(int((stamps[index + 1] - stamp).total_seconds())) if index + 1 < len(stamps) else "",
            "completion_proxy_status": ("next_bar_start_same_second" if same_second else "next_bar_start_proxy") if index + 1 < len(stamps) else "unavailable_export_end",
            "session_date_proxy": inferred_session_date(stamp).isoformat(),
            "open": "100.00", "high": "101.00", "low": "99.00",
            "close": "101.00" if direction == "U" else "99.00" if direction == "D" else "100.00",
        } for index, (stamp, direction) in enumerate(zip(stamps, directions))]

    def write(self, rows: list[dict]) -> None:
        with self.path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.COLUMNS, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

    def test_streaming_validation_and_terminal_barrier_audit(self) -> None:
        self.write(self.rows())
        audit = {}
        bars = list(load_bars(self.path, 4, audit=audit))
        self.assertEqual(6, audit["input_rows"])
        self.assertEqual(5, audit["primary_eligible_bars"])
        self.assertEqual(1, audit["doji_eligible_bars"])
        self.assertEqual({"completion_status:unavailable_export_end": 1}, audit["barrier_counts"])
        self.assertEqual(Decimal("100.00"), bars[0].open)
        self.assertFalse(bars[-1].primary_eligible)
        up, down = extract_trends(bars, 4)
        self.assertEqual(3, up.length)
        self.assertIsNone(down.length)
        self.assertEqual("completion_status:unavailable_export_end", down.end_reason)

    def test_identical_adjacent_rows_flagged_and_preserved(self) -> None:
        self.write(self.rows(same_second=True))
        audit = {}
        bars = list(load_bars(self.path, 4, audit=audit))
        self.assertEqual(2, audit["duplicate_adjacent_rows"])
        self.assertEqual(5, audit["primary_eligible_bars"])
        self.assertEqual([3, 4], [row["source_row"] for row in audit["duplicate_examples"]])
        up, _ = extract_trends(bars, 4)
        self.assertEqual(3, up.length)

    def test_entire_partial_session_is_excluded_with_retained_rows(self) -> None:
        self.write(self.rows(start=datetime(2026, 9, 23, 20)))
        audit = {}
        bars = list(load_bars(self.path, 4, [date(2026, 9, 24)], audit=audit))
        self.assertEqual(6, len(bars))
        self.assertEqual(0, audit["primary_eligible_bars"])
        self.assertEqual({"2026-09-24": 6}, audit["excluded_session_counts"])
        self.assertEqual([], list(extract_trends(bars, 4)))

    def test_malformed_values_hard_fail_instead_of_becoming_exclusions(self) -> None:
        mutations = (("open", "NaN"), ("close", "bad"), ("high", "99"),
                     ("bar_start_timestamp", "invalid"), ("bar_start_timestamp", "2024-06-10T09:30:01Z"),
                     ("source_timestamp", "2024-99-99 09:30:00"),
                     ("session_date_proxy", "2024-06-11"), ("source_row", "20"),
                     ("bar_completion_timestamp_proxy", ""),
                     ("bar_duration_seconds_proxy", "2"),
                     ("completion_proxy_status", "next_bar_start_same_second"))
        for key, value in mutations:
            with self.subTest(field=key):
                rows = self.rows()
                rows[0][key] = value
                self.write(rows)
                with self.assertRaises(ValueError):
                    list(load_bars(self.path, 4))

    def test_lookahead_completion_must_match_following_bar(self) -> None:
        rows = self.rows()
        rows[0]["bar_completion_timestamp_proxy"] = "2024-06-10 09:30:02"
        rows[0]["bar_duration_seconds_proxy"] = "2"
        self.write(rows)
        with self.assertRaisesRegex(ValueError, "previous completion proxy"):
            list(load_bars(self.path, 4))

    def test_regressing_unsupported_timestamps_still_hard_fail(self) -> None:
        rows = self.rows()
        rows[0]["completion_proxy_status"] = "unknown"
        rows[1]["bar_start_timestamp"] = "2024-06-10 09:29:59"
        rows[1]["bar_duration_seconds_proxy"] = "3"
        self.write(rows)
        with self.assertRaisesRegex(ValueError, "regress"):
            list(load_bars(self.path, 4))

    def test_schema_and_dangling_completed_final_row_are_refused(self) -> None:
        self.path.write_text("open;close\n100;101\n")
        with self.assertRaisesRegex(ValueError, "header"):
            list(load_bars(self.path, 4))
        self.write(self.rows()[:-1])
        with self.assertRaisesRegex(ValueError, "final source row"):
            list(load_bars(self.path, 4))


if __name__ == "__main__":
    unittest.main()
