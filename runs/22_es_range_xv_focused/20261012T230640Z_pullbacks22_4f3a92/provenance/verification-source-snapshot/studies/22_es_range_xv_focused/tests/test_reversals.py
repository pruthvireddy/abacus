"""Known reversal examples, observable horizons and exact retracement prices."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
from reversals import LEDGER_COLUMNS, extract_reversals, ledger_row
from trends import Bar, inferred_session_date


def make_reversal_bar(row: int, direction: str = "U", *, setting: int = 4,
                      stamp: datetime | None = None, session: date | None = None,
                      prices: tuple[str, str, str, str] | None = None,
                      eligible: bool = True, status: str = "next_bar_start_proxy",
                      reason: str | None = None) -> Bar:
    stamp = stamp or datetime(2024, 6, 10, 9, 30) + timedelta(seconds=row)
    if prices is None:
        prices = ("100", "101", "99", "101" if direction == "U" else "99" if direction == "D" else "100")
    return Bar(setting, row, stamp, stamp + timedelta(seconds=1), session or inferred_session_date(stamp),
               *(Decimal(price) for price in prices), status, eligible, reason)


def reversal_sequence(directions: str) -> list[Bar]:
    return [make_reversal_bar(row, direction) for row, direction in enumerate(directions, 1)]


def known_reversal(*, bullish: bool = True, follower: tuple[str, str, str, str] | None = None):
    predecessor = make_reversal_bar(1, "D" if bullish else "U")
    reversal = make_reversal_bar(2, prices=("100", "105", "99", "104") if bullish else ("104", "105", "99", "100"))
    follower = follower or (("103", "106", "101", "105") if bullish else ("101", "103", "98", "99"))
    next_bar = make_reversal_bar(3, prices=follower)
    return list(extract_reversals([predecessor, reversal, next_bar], 4))[0]


class ReversalTests(unittest.TestCase):
    def test_reversal_excludes_R_and_requires_direct_opposite_predecessor(self) -> None:
        events = list(extract_reversals(reversal_sequence("UUDDDUZZDUUUD"), 4))
        self.assertEqual([3, 6, 10, 13], [event.source_row for event in events])
        self.assertEqual(["bearish", "bullish", "bullish", "bearish"], [event.direction for event in events])
        self.assertEqual([2, 3, 1, 3], [event.prior_observed_length for event in events])
        self.assertEqual([False, True, True, True], [event.prior_start_known for event in events])
        self.assertEqual([None, 3, 1, 3], [event.prior_exact_length for event in events])
        self.assertEqual([2, 0, 2, 0], [event.follow_count for event in events])
        self.assertEqual([2, 0, 2, None], [event.exact_follow_count for event in events])
        self.assertEqual(["reversal", "doji", "reversal", "export_end"], [event.end_reason for event in events])
        self.assertEqual([4, 7, 11, None], [event.f1_source_row for event in events])

    def test_first_colour_change_valid_even_when_prior_leg_start_unknown(self) -> None:
        event, = extract_reversals(reversal_sequence("UUUD"), 4)
        self.assertEqual((4, 3, 3, False, None), (event.source_row, event.previous_source_row,
                         event.prior_observed_length, event.prior_start_known, event.prior_exact_length))

    def test_doji_establishes_prior_start_but_doji_to_direction_is_not_reversal(self) -> None:
        event, = extract_reversals(reversal_sequence("ZUUUD"), 4)
        self.assertTrue(event.prior_start_known)
        self.assertEqual(3, event.prior_exact_length)
        self.assertEqual([], list(extract_reversals(reversal_sequence("ZZUUUZDD"), 4)))

    def test_completed_breaker_remains_failure_for_all_later_horizons(self) -> None:
        bars = reversal_sequence("DUUD")
        bars.append(make_reversal_bar(5, eligible=False, reason="excluded_session"))
        first, second = extract_reversals(bars, 4)
        self.assertEqual([True, False, False], [first.continuation_outcome(n) for n in (1, 2, 20)])
        self.assertFalse(first.right_censored)
        self.assertIsNone(second.continuation_outcome(1))

    def test_known_success_before_barrier_is_retained_and_longer_horizon_unknown(self) -> None:
        bars = reversal_sequence("DUUU")
        bars.append(make_reversal_bar(5, eligible=False, status="unavailable_export_end"))
        event, = extract_reversals(bars, 4)
        self.assertEqual(2, event.follow_count)
        self.assertEqual([True, True, None, None], [event.continuation_outcome(n) for n in (1, 2, 3, 20)])
        self.assertIsNone(event.exact_follow_count)
        self.assertTrue(event.f1_known)

    def test_unconfirmed_opposite_candle_is_barrier_not_failure_or_new_event(self) -> None:
        bars = reversal_sequence("DUD")
        bars[-1] = replace(bars[-1], primary_eligible=False, completion_status="unavailable_session_boundary")
        event, = extract_reversals(bars, 4)
        self.assertIsNone(event.continuation_outcome(1))
        self.assertFalse(event.f1_known)
        self.assertEqual("completion_status:unavailable_session_boundary", event.end_reason)

    def test_session_boundary_never_stitches_followers_or_opposite_event(self) -> None:
        bars = reversal_sequence("DUDD")
        bars[2:] = [replace(bar, session_date=date(2024, 6, 11)) for bar in bars[2:]]
        event, = extract_reversals(bars, 4)
        self.assertEqual("session_boundary", event.end_reason)
        self.assertIsNone(event.continuation_outcome(1))

    def test_omitted_source_row_is_barrier_and_new_segment_needs_new_predecessor(self) -> None:
        bars = reversal_sequence("DUDU")
        bars[2:] = [replace(bar, source_row=bar.source_row + 1) for bar in bars[2:]]
        first, second = extract_reversals(bars, 4)
        self.assertEqual("source_row_gap", first.end_reason)
        self.assertEqual(5, second.source_row)
        self.assertFalse(second.prior_start_known)

    def test_same_second_and_identical_rows_keep_order(self) -> None:
        stamp = datetime(2024, 6, 10, 9, 30)
        bars = [replace(bar, start_timestamp=stamp, completion_timestamp=stamp,
                        completion_status="next_bar_start_same_second") for bar in reversal_sequence("DUUUD")]
        first, second = extract_reversals(bars, 4)
        self.assertEqual((2, 3, 2), (first.source_row, first.f1_source_row, first.exact_follow_count))
        self.assertEqual(stamp, first.available_at)
        self.assertEqual(stamp, first.termination_available_at)
        self.assertEqual(5, second.source_row)

    def test_bull_and_bear_retrace_levels_are_exact_inclusive_touches(self) -> None:
        bull, bear = known_reversal(), known_reversal(bullish=False)
        self.assertEqual([Decimal(103), Decimal(102), Decimal(101), Decimal(100)],
                         [bull.retracement_price(n) for n in (25, 50, 75, 100)])
        self.assertEqual([Decimal(101), Decimal(102), Decimal(103), Decimal(104)],
                         [bear.retracement_price(n) for n in (25, 50, 75, 100)])
        for event in (bull, bear):
            self.assertEqual([True, True, True, False],
                             [event.retracement_outcome(n)["touched"] for n in (25, 50, 75, 100)])
            self.assertTrue(event.retracement_outcome(50)["favorable_beyond_close"])
            self.assertTrue(event.retracement_outcome(50)["favorable_same_colour"])

    def test_same_colour_close_inside_R_body_is_not_beyond_close_success(self) -> None:
        event = known_reversal(follower=("102", "104", "101", "103"))
        self.assertTrue(event.continuation_outcome(1))
        result = event.retracement_outcome(50)
        self.assertTrue(result["touched"] and result["favorable_same_colour"])
        self.assertFalse(result["favorable_beyond_close"])

    def test_opposite_colour_and_doji_F1_can_have_favorable_beyond_close_endpoint(self) -> None:
        for follower in (("106", "107", "101", "105"), ("105", "106", "101", "105")):
            with self.subTest(follower=follower):
                event = known_reversal(follower=follower)
                result = event.retracement_outcome(50)
                self.assertTrue(result["touched"] and result["favorable_beyond_close"])
                self.assertFalse(result["favorable_same_colour"])
                self.assertFalse(event.continuation_outcome(1))

    def test_equal_R_close_is_not_favorable_and_equal_F1_open_is_not_same_colour(self) -> None:
        event = known_reversal(follower=("104", "105", "102", "104"))
        result = event.retracement_outcome(50)
        self.assertTrue(result["touched"])
        self.assertFalse(result["favorable_beyond_close"] or result["favorable_same_colour"])

    def test_unavailable_F1_retracement_null_is_not_false(self) -> None:
        event, = extract_reversals(reversal_sequence("DU"), 4)
        for level in (25, 50, 75, 100):
            result = event.retracement_outcome(level)
            self.assertIsNone(result["touched"])
            self.assertIsNone(result["favorable_beyond_close"])
            self.assertIsNone(result["favorable_same_colour"])

    def test_exact_small_decimal_prices_and_csv_null_bool_timestamp_strings(self) -> None:
        event = known_reversal()
        event = replace(event, open=Decimal("100.00000000000000000000"),
                        close=Decimal("100.00000000000000000004"))
        self.assertEqual(Decimal("100.00000000000000000003"), event.retracement_price(25))
        row = ledger_row(event)
        self.assertEqual(tuple(LEDGER_COLUMNS), tuple(row))
        self.assertEqual("true", row["right_censored"])
        self.assertEqual("", row["exact_follow_count"])
        self.assertEqual("2024-06-10 09:30:03", row["available_at"])
        self.assertEqual("100.00000000000000000004", row["close"])
        self.assertEqual("1", row["follow_count"])

    def test_invalid_horizons_and_levels_refused(self) -> None:
        event = known_reversal()
        for n in (0, -1, 1.5, True):
            with self.subTest(n=n), self.assertRaises(ValueError):
                event.continuation_outcome(n)
        for level in (0, -25, 101, 25.0, True):
            with self.subTest(level=level), self.assertRaises(ValueError):
                event.retracement_outcome(level)

    def test_empty_and_single_colour_streams_have_no_events(self) -> None:
        for text in ("", "U", "UUUU", "ZZZZ"):
            self.assertEqual([], list(extract_reversals(reversal_sequence(text), 4)))

    def test_bad_settings_rows_or_completed_timestamps_refused(self) -> None:
        invalid = (
            ([make_reversal_bar(1, setting=5)], "cannot pool"),
            ([make_reversal_bar(0)], "positive integers"),
            ([make_reversal_bar(1), make_reversal_bar(1)], "strictly increasing"),
            ([replace(make_reversal_bar(1), completion_timestamp=None)], "completion timestamp"),
            ([replace(make_reversal_bar(1), start_timestamp=datetime(2024, 6, 10, tzinfo=timezone.utc))], "naive New York"),
        )
        for bars, message in invalid:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                list(extract_reversals(bars, 4))
        with self.assertRaises(ValueError):
            list(extract_reversals([], 7))


if __name__ == "__main__":
    unittest.main()
