import copy
from datetime import date, datetime, timezone
import importlib.util
import json
from pathlib import Path
import unittest

OWNER = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("study29_phase6_calendar_tests", OWNER / "phase6/calendar_control.py")
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.calendar = json.loads((OWNER / "phase6/calendar.json").read_text())
        self.freeze = "2026-10-31T04:00:00+00:00"

    def test_adopted_twenty_supported_sessions(self):
        result = C.validate_calendar(self.calendar, self.freeze)
        self.assertEqual((result["first"], result["last"], result["scheduled_sessions"]),
                         ("2026-11-02", "2026-12-08", 20))
        self.assertFalse(result["future_market_observations_verified"])

    def test_dates_do_not_extend_to_replace_failures(self):
        self.calendar["no_replacement_of_scheduled_failures"] = False
        with self.assertRaisesRegex(ValueError, "nonreplacement"):
            C.validate_calendar(self.calendar, self.freeze)

    def test_naive_full_current_sessions_do_not_meet_required_history(self):
        dates = self.calendar["scheduled_dates"]
        dates[-2:] = ["2026-11-30", "2026-12-01"]
        with self.assertRaisesRegex(ValueError, "first twenty"):
            C.validate_calendar(self.calendar, self.freeze)

    def test_duplicate_date_fails(self):
        self.calendar["scheduled_dates"][-1] = self.calendar["scheduled_dates"][-2]
        with self.assertRaisesRegex(ValueError, "unique"):
            C.validate_calendar(self.calendar, self.freeze)

    def test_missing_date_fails(self):
        self.calendar["scheduled_dates"].pop()
        with self.assertRaisesRegex(ValueError, "twenty"):
            C.validate_calendar(self.calendar, self.freeze)

    def test_unscheduled_wrong_date_fails(self):
        self.calendar["scheduled_dates"][0] = "2026-10-30"
        with self.assertRaises(ValueError):
            C.validate_calendar(self.calendar, self.freeze)

    def test_actual_freeze_after_first_cutoff_cannot_use_old_calendar(self):
        with self.assertRaisesRegex(ValueError, "anchor"):
            C.validate_calendar(self.calendar, "2026-11-02T09:25:00-05:00")

    def test_naive_freeze_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            C.validate_calendar(self.calendar, "2026-10-31T04:00:00")

    def test_fixed_offset_substitution_rejected(self):
        self.calendar["sessions"][0]["cutoff_utc"] = "2026-11-02T13:25:00+00:00"
        with self.assertRaisesRegex(ValueError, "DST"):
            C.validate_calendar(self.calendar, self.freeze)

    def test_new_york_dst_boundary(self):
        before = C.at(date(2026, 10, 30), 9, 25).astimezone(timezone.utc)
        after = C.at(date(2026, 11, 2), 9, 25).astimezone(timezone.utc)
        self.assertEqual((before.hour, after.hour), (13, 14))
        repeated = datetime(2026, 11, 1, 1, 30, tzinfo=C.NY)
        self.assertEqual(repeated.replace(fold=1).timestamp() - repeated.replace(fold=0).timestamp(), 3600)

    def test_all_scheduled_cutoffs_are_est(self):
        for row in self.calendar["sessions"]:
            self.assertTrue(row["cutoff_ny"].endswith("-05:00"))
            self.assertTrue(row["cutoff_utc"].endswith("T14:25:00+00:00"))

    def test_full_rth_boundary_change_rejected(self):
        self.calendar["sessions"][0]["rth_close_ny"] = "2026-11-02T13:00:00-05:00"
        with self.assertRaisesRegex(ValueError, "RTH"):
            C.validate_calendar(self.calendar, self.freeze)

    def test_silent_contract_transition_rejected(self):
        for field, value in (("contract", "ESH2027"), ("symbol", "CME_MINI:ES1!"),
                             ("adjustment", "back_adjusted")):
            changed = copy.deepcopy(self.calendar)
            changed["contract"][field] = value
            with self.assertRaisesRegex(ValueError, "contract transition"):
                C.validate_calendar(changed, self.freeze)

    def test_contract_expiry_guard(self):
        self.calendar["contract"]["last_trade_at"] = "2026-12-08T09:30:00-05:00"
        with self.assertRaisesRegex(ValueError, "suitability"):
            C.validate_calendar(self.calendar, self.freeze)

    def test_customary_roll_guard_is_separate(self):
        self.calendar["contract"]["customary_roll_at"] = "2026-12-08T00:00:00-05:00"
        with self.assertRaisesRegex(ValueError, "suitability"):
            C.validate_calendar(self.calendar, self.freeze)

    def test_holiday_exclusions_cannot_be_deleted(self):
        self.calendar["calendar_exclusions"].pop()
        with self.assertRaisesRegex(ValueError, "exclusions"):
            C.validate_calendar(self.calendar, self.freeze)

    def test_exact_eight_history_windows_and_strict_composite(self):
        windows = C.required_windows("2026-11-30")
        self.assertEqual(len(windows), 8)
        self.assertEqual([n for n, *_ in windows if n.startswith("composite")],
                         ["composite_member_2026-11-25", "composite_member_2026-11-26", "composite_member_2026-11-27"])
        self.assertEqual(windows[1][1].isoformat(), "2026-11-27T09:30:00-05:00")

    def test_calendar_exclusions_are_predeclared_not_observed_data(self):
        events = self.calendar["known_events"]
        affected = C.support_exclusions("2026-12-03", events)
        self.assertEqual([r["window"] for r in affected], ["previous_completed_week"])
        self.assertEqual(C.support_exclusions("2026-12-07", events), [])

    def test_veterans_day_retained_as_full_nominal_session(self):
        self.assertIn("2026-11-11", self.calendar["scheduled_dates"])
        self.assertEqual(C.support_exclusions("2026-11-11", self.calendar["known_events"]), [])

    def test_unsupported_weekend_and_duplicate_event(self):
        with self.assertRaisesRegex(ValueError, "weekday"):
            C.required_windows("2026-11-01")
        events = self.calendar["known_events"] + [self.calendar["known_events"][0]]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            C.support_exclusions("2026-11-02", events)


if __name__ == "__main__":
    unittest.main()
