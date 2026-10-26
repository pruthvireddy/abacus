"""Synthetic earlier-leg setup selection and separately observed outcomes."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
from pullbacks import LEDGER_COLUMNS, extract_pullbacks, ledger_row
from trends import Bar, inferred_session_date


def make_pullback_bar(row: int, direction: str = "U", *, setting: int = 4,
                      stamp: datetime | None = None, prices: tuple[str, ...] | None = None) -> Bar:
    stamp = stamp or datetime(2024, 6, 10, 9, 30) + timedelta(seconds=row)
    prices = prices or ("100", "101", "99", "101" if direction == "U" else "99" if direction == "D" else "100")
    return Bar(setting, row, stamp, stamp + timedelta(seconds=1), inferred_session_date(stamp),
               *(Decimal(price) for price in prices), "next_bar_start_proxy")


def pullback_sequence(text: str) -> list[Bar]:
    return [make_pullback_bar(row, direction) for row, direction in enumerate(text, 1)]


def known_pullback(*, bullish: bool = True, follower: tuple[str, ...] | None = None):
    text = "ZUUUDUU" if bullish else "ZDDDUDD"
    bars = pullback_sequence(text)
    bars[5] = make_pullback_bar(6, prices=("100", "105", "99", "104") if bullish else ("104", "105", "99", "100"))
    follower = follower or (("103", "106", "101", "105") if bullish else ("101", "103", "98", "99"))
    bars[6] = make_pullback_bar(7, prices=follower)
    return next(event for event in extract_pullbacks(bars, 4) if event.source_row == 6)


class PullbackTests(unittest.TestCase):
    def test_three_A_one_B_then_R_two_followers(self) -> None:
        event = next(event for event in extract_pullbacks(pullback_sequence("ZUUUDUUUD"), 4) if event.source_row == 6)
        self.assertEqual((2, 4, 3, True, 3), (event.earlier_start_source_row, event.earlier_end_source_row,
                         event.earlier_observed_length, event.earlier_start_known, event.earlier_exact_length))
        self.assertEqual((5, 6, 7, 2, 2), (event.pullback_source_row, event.source_row,
                         event.f1_source_row, event.follow_count, event.exact_follow_count))
        self.assertEqual([True, True, False], [event.continuation_outcome(n) for n in (1, 2, 3)])
        self.assertEqual("bullish", event.direction)

    def test_mirrored_three_bear_A_one_bull_B_then_bear_R(self) -> None:
        event = known_pullback(bullish=False)
        self.assertEqual(("bearish", 3, 1), (event.direction, event.earlier_exact_length, event.follow_count))
        self.assertGreater(event.pullback_close, event.pullback_open)

    def test_segment_start_A_kept_unknown_not_exact_observed_length(self) -> None:
        event, = extract_pullbacks(pullback_sequence("UUUDUU"), 4)
        self.assertEqual((3, False, None, 5), (event.earlier_observed_length,
                         event.earlier_start_known, event.earlier_exact_length, event.source_row))

    def test_B_at_segment_start_is_not_one_pullback_setup(self) -> None:
        self.assertEqual([], list(extract_pullbacks(pullback_sequence("DUUU"), 4)))

    def test_two_candle_B_excluded(self) -> None:
        self.assertEqual([], list(extract_pullbacks(pullback_sequence("ZUUUDDUUU"), 4)))

    def test_A_of_one_is_valid_and_alternations_have_observed_flips(self) -> None:
        events = list(extract_pullbacks(pullback_sequence("UDUDU"), 4))
        self.assertEqual([3, 4, 5], [event.source_row for event in events])
        self.assertEqual([None, 1, 1], [event.earlier_exact_length for event in events])
        self.assertEqual([0, 0, None], [event.exact_follow_count for event in events])

    def test_doji_prevents_selection_across_it(self) -> None:
        for text in ("UUUZDU", "UUUDZU", "UUZDU"):
            self.assertEqual([], list(extract_pullbacks(pullback_sequence(text), 4)))

    def test_doij_breaker_is_known_failure_and_F1_known(self) -> None:
        event, = extract_pullbacks(pullback_sequence("UUUDUZ"), 4)
        self.assertEqual((0, "doji", True, False), (event.exact_follow_count, event.end_reason,
                         event.f1_known, event.continuation_outcome(1)))

    def test_known_followers_before_barrier_retained(self) -> None:
        bars = pullback_sequence("UUUDUUUD")
        bars[-1] = replace(bars[-1], primary_eligible=False, barrier_reason="excluded_session")
        event, = extract_pullbacks(bars, 4)
        self.assertEqual([True, True, None], [event.continuation_outcome(n) for n in (1, 2, 3)])
        self.assertEqual("excluded_session", event.end_reason)
        self.assertIsNone(event.exact_follow_count)

    def test_uncompleted_F1_not_false_and_uncompleted_R_not_selected(self) -> None:
        bars = pullback_sequence("UUUDUD")
        bars[-1] = replace(bars[-1], completion_status="unavailable_export_end", completion_timestamp=None)
        event, = extract_pullbacks(bars, 4)
        self.assertFalse(event.f1_known)
        self.assertIsNone(event.continuation_outcome(1))
        for level in (25, 50, 75, 100):
            self.assertIsNone(event.retracement_outcome(level)["touched"])
        bars[4] = replace(bars[4], primary_eligible=False)
        self.assertEqual([], list(extract_pullbacks(bars, 4)))

    def test_session_boundary_prevents_A_B_R_selection_and_followup(self) -> None:
        for boundary in (3, 4, 5):
            bars = pullback_sequence("UUUDUU")
            bars[boundary:] = [replace(bar, session_date=date(2024, 6, 11)) for bar in bars[boundary:]]
            events = list(extract_pullbacks(bars, 4))
            if boundary == 5:
                self.assertEqual(1, len(events))
                self.assertEqual("session_boundary", events[0].end_reason)
                self.assertFalse(events[0].f1_known)
            else:
                self.assertEqual([], events)

    def test_source_gap_resets_A_B_state(self) -> None:
        bars = pullback_sequence("UUUDUU")
        bars[3:] = [replace(bar, source_row=bar.source_row + 1) for bar in bars[3:]]
        self.assertEqual([], list(extract_pullbacks(bars, 4)))

    def test_same_second_rows_and_identical_followers_kept(self) -> None:
        stamp = datetime(2024, 6, 10, 9, 30)
        bars = [replace(bar, start_timestamp=stamp, completion_timestamp=stamp,
                        completion_status="next_bar_start_same_second") for bar in pullback_sequence("UUUDUUUD")]
        event = next(event for event in extract_pullbacks(bars, 4) if event.source_row == 5)
        self.assertEqual((2, 6, stamp), (event.follow_count, event.f1_source_row, event.available_at))

    def test_body_touch_and_beyond_close_are_exact_mirrored(self) -> None:
        for bullish, prices in ((True, [103, 102, 101, 100]), (False, [101, 102, 103, 104])):
            event = known_pullback(bullish=bullish)
            self.assertEqual([Decimal(price) for price in prices], [event.retracement_price(level) for level in (25, 50, 75, 100)])
            self.assertEqual([True, True, True, False], [event.retracement_outcome(level)["touched"] for level in (25, 50, 75, 100)])
            self.assertTrue(event.retracement_outcome(50)["favorable_beyond_close"])

    def test_gap_colour_and_price_endpoint_are_distinct(self) -> None:
        event = known_pullback(follower=("106", "107", "101", "105"))
        self.assertFalse(event.continuation_outcome(1))
        self.assertTrue(event.retracement_outcome(50)["favorable_beyond_close"])
        self.assertFalse(event.retracement_outcome(50)["favorable_same_colour"])

    def test_equal_close_is_not_favorable(self) -> None:
        event = known_pullback(follower=("104", "105", "102", "104"))
        self.assertTrue(event.retracement_outcome(50)["touched"])
        self.assertFalse(event.retracement_outcome(50)["favorable_beyond_close"])

    def test_source_metadata_B_OHLC_and_csv_nulls(self) -> None:
        event = known_pullback()
        row = ledger_row(event)
        self.assertEqual(LEDGER_COLUMNS, tuple(row))
        self.assertEqual("true", row["earlier_start_known"])
        self.assertEqual("3", row["earlier_exact_length"])
        self.assertEqual("99", row["pullback_close"])
        self.assertEqual("", row["exact_follow_count"])
        self.assertEqual("2024-06-10 09:30:07", row["available_at"])

    def test_invalid_inputs_and_parameters_refused(self) -> None:
        invalid = ([make_pullback_bar(1, setting=5)], [make_pullback_bar(0)],
                   [make_pullback_bar(1), make_pullback_bar(1)],
                   [replace(make_pullback_bar(1), completion_timestamp=None)],
                   [replace(make_pullback_bar(1), start_timestamp=datetime(2024, 6, 10, tzinfo=timezone.utc))])
        for bars in invalid:
            with self.assertRaises(ValueError):
                list(extract_pullbacks(bars, 4))
        with self.assertRaises(ValueError):
            list(extract_pullbacks([], 7))
        event = known_pullback()
        for n in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                event.continuation_outcome(n)
        for level in (0, 101, True, 25.0):
            with self.assertRaises(ValueError):
                event.retracement_price(level)


if __name__ == "__main__":
    unittest.main()
