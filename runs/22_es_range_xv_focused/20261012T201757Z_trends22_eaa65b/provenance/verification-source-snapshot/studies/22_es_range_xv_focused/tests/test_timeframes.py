"""Synthetic checks for Study 22 reporting groups; no retained-data reads."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


_STUDY_ROOT = Path(__file__).resolve().parents[1]
_MODULE_NAME = "study_22_reporting_timeframes"
_SPEC = importlib.util.spec_from_file_location(
    _MODULE_NAME, _STUDY_ROOT / "src" / "timeframes.py"
)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_MODULE_NAME] = _MODULE
_SPEC.loader.exec_module(_MODULE)

Timeframe = _MODULE.Timeframe
ReportingSlice = _MODULE.ReportingSlice
load_timeframes = _MODULE.load_timeframes
timeframe_ids = _MODULE.timeframe_ids
reporting_slices = _MODULE.reporting_slices


_WINDOWS = [
    {"id": "asia", "label": "Asia", "group": "sessions", "start": "20:00", "end": "02:00"},
    {"id": "london", "label": "London", "group": "sessions", "start": "02:00", "end": "09:00"},
    {"id": "ny", "label": "NY", "group": "sessions", "start": "09:30", "end": "16:00"},
    {"id": "asia_open", "label": "Asia Open", "group": "subwindows", "start": "19:30", "end": "21:30"},
    {"id": "ny_open", "label": "NY Open", "group": "subwindows", "start": "09:30", "end": "10:30"},
    {"id": "ny_am", "label": "NY AM", "group": "subwindows", "start": "10:30", "end": "12:30"},
    {"id": "ny_pm", "label": "NY PM", "group": "subwindows", "start": "12:30", "end": "16:00"},
]


def _settings() -> dict:
    return {
        "reporting": {
            "timezone": "America/New_York",
            "interval_bounds": "start_inclusive_end_exclusive",
            "timeframes": deepcopy(_WINDOWS),
        }
    }


class TimeframeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings_path = Path(self.temp.name) / "study.yaml"
        self.write_settings(_settings())
        self.frames = load_timeframes(self.settings_path)

    def write_settings(self, settings: object) -> None:
        self.settings_path.write_text(json.dumps(settings), encoding="utf-8")

    def test_loading_preserves_settings_order_and_clock_values(self) -> None:
        self.assertEqual(tuple(row["id"] for row in _WINDOWS), tuple(f.id for f in self.frames))
        self.assertEqual(time(20), self.frames[0].start)
        self.assertEqual(time(2), self.frames[0].end)
        self.assertEqual("sessions", self.frames[0].group)
        self.assertEqual("subwindows", self.frames[-1].group)

    def test_authoritative_settings_match_the_requested_seven_windows(self) -> None:
        self.assertEqual(self.frames, load_timeframes(_STUDY_ROOT / "study.yaml"))

    def test_every_window_includes_start_and_excludes_end(self) -> None:
        for frame in self.frames:
            start = datetime.combine(date(2024, 6, 10), frame.start)
            end = datetime.combine(date(2024, 6, 10), frame.end)
            if frame.start > frame.end:
                end += timedelta(days=1)
            with self.subTest(window=frame.id):
                self.assertIn(frame.id, timeframe_ids(start, self.frames))
                self.assertNotIn(frame.id, timeframe_ids(start - timedelta(microseconds=1), self.frames))
                self.assertIn(frame.id, timeframe_ids(end - timedelta(microseconds=1), self.frames))
                self.assertNotIn(frame.id, timeframe_ids(end, self.frames))

    def test_overnight_asia_crosses_midnight_without_date_filtering(self) -> None:
        cases = {
            "2024-06-10T23:59:59.999999": ("asia",),
            "2024-06-11T00:00:00": ("asia",),
            "2024-06-11T01:59:59.999999": ("asia",),
            "2024-06-11T02:00:00": ("london",),
        }
        for stamp, expected in cases.items():
            with self.subTest(timestamp=stamp):
                self.assertEqual(expected, timeframe_ids(datetime.fromisoformat(stamp), self.frames))

    def test_overlapping_windows_match_independently(self) -> None:
        cases = {
            "19:30:00": ("asia_open",),
            "20:00:00": ("asia", "asia_open"),
            "21:30:00": ("asia",),
            "09:30:00": ("ny", "ny_open"),
            "10:30:00": ("ny", "ny_am"),
            "12:30:00": ("ny", "ny_pm"),
        }
        for clock, expected in cases.items():
            with self.subTest(clock=clock):
                stamp = datetime.fromisoformat(f"2024-06-10T{clock}")
                self.assertEqual(expected, timeframe_ids(stamp, self.frames))

    def test_unassigned_hours_remain_in_yearly_and_pooled_all_hours(self) -> None:
        for clock in ("09:00:00", "09:29:59.999999", "16:00:00", "19:29:59.999999"):
            stamp = datetime.fromisoformat(f"2024-06-10T{clock}")
            with self.subTest(clock=clock):
                self.assertEqual((), timeframe_ids(stamp, self.frames))
                self.assertEqual(
                    (ReportingSlice(None, "all_hours"), ReportingSlice(2024, "all_hours")),
                    reporting_slices(stamp, date(2024, 6, 10), self.frames),
                )

    def test_year_uses_session_date_for_december_31_evening(self) -> None:
        self.assertEqual(
            (
                ReportingSlice(None, "all_hours"),
                ReportingSlice(2025, "all_hours"),
                ReportingSlice(None, "asia"),
                ReportingSlice(None, "asia_open"),
                ReportingSlice(2025, "asia"),
                ReportingSlice(2025, "asia_open"),
            ),
            reporting_slices(datetime(2024, 12, 31, 20), date(2025, 1, 1), self.frames),
        )

    def test_subsecond_times_do_not_round_across_boundaries(self) -> None:
        self.assertEqual(
            ("ny", "ny_open"),
            timeframe_ids(datetime(2024, 6, 10, 10, 29, 59, 999999), self.frames),
        )
        self.assertEqual(
            ("ny", "ny_am"),
            timeframe_ids(datetime(2024, 6, 10, 10, 30, 0, 1), self.frames),
        )

    def test_repeated_same_second_rows_each_keep_their_sections(self) -> None:
        stamps = [datetime(2024, 6, 10, 10), datetime(2024, 6, 10, 10)]
        sections = [reporting_slices(stamp, date(2024, 6, 10), self.frames) for stamp in stamps]
        self.assertEqual(2, len(sections))
        self.assertEqual(sections[0], sections[1])
        self.assertEqual(6, len(sections[0]))

    def test_settings_define_windows_without_source_schedule(self) -> None:
        settings = _settings()
        settings["reporting"]["timeframes"] = [
            {"id": "custom", "label": "Custom", "group": "sessions", "start": "07:15", "end": "08:45"}
        ]
        self.write_settings(settings)
        frames = load_timeframes(self.settings_path)
        self.assertEqual(("custom",), timeframe_ids(datetime(2024, 6, 10, 8), frames))
        self.assertEqual((), timeframe_ids(datetime(2024, 6, 10, 20), frames))

    def test_invalid_root_or_reporting_structure_is_rejected(self) -> None:
        for settings in (None, [], {}, {"reporting": []}, {"reporting": "bad"}):
            with self.subTest(settings=settings):
                self.write_settings(settings)
                with self.assertRaises(ValueError):
                    load_timeframes(self.settings_path)

    def test_invalid_timezone_interval_and_window_collection_are_rejected(self) -> None:
        invalid = (
            ("timezone", "UTC"),
            ("timezone", None),
            ("interval_bounds", "closed"),
            ("interval_bounds", None),
            ("timeframes", []),
            ("timeframes", {}),
            ("timeframes", None),
            ("timeframes", [False]),
        )
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                settings = _settings()
                settings["reporting"][key] = value
                self.write_settings(settings)
                with self.assertRaises(ValueError):
                    load_timeframes(self.settings_path)

    def test_invalid_window_fields_are_rejected(self) -> None:
        invalid = (
            ("id", ""),
            ("id", " asia "),
            ("id", "all_hours"),
            ("label", None),
            ("label", ""),
            ("group", "other"),
            ("start", "9:30"),
            ("start", "09:3"),
            ("start", "09:30:00"),
            ("start", "24:00"),
            ("start", 2000),
            ("end", "02:60"),
            ("end", "20:00"),
        )
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                settings = _settings()
                settings["reporting"]["timeframes"][0][key] = value
                self.write_settings(settings)
                with self.assertRaises(ValueError):
                    load_timeframes(self.settings_path)

    def test_duplicate_ids_are_rejected_even_with_different_groups(self) -> None:
        settings = _settings()
        settings["reporting"]["timeframes"][-1]["id"] = "asia"
        self.write_settings(settings)
        with self.assertRaisesRegex(ValueError, "duplicate timeframe id"):
            load_timeframes(self.settings_path)

    def test_non_json_yaml_is_rejected_with_subset_explanation(self) -> None:
        self.settings_path.write_text("reporting:\n  timezone: America/New_York\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "JSON syntax subset"):
            load_timeframes(self.settings_path)

    def test_aware_datetimes_are_rejected_for_both_apis(self) -> None:
        stamp = datetime(2024, 6, 10, 10, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "naive New York"):
            timeframe_ids(stamp, self.frames)
        with self.assertRaisesRegex(ValueError, "naive New York"):
            reporting_slices(stamp, date(2024, 6, 10), self.frames)

    def test_date_types_are_validated_without_reinterpreting_session_date(self) -> None:
        for invalid in ("2024-06-10", datetime(2024, 6, 10), None):
            with self.subTest(session_date=invalid):
                with self.assertRaises(TypeError):
                    reporting_slices(datetime(2024, 6, 10, 10), invalid, self.frames)
        with self.assertRaises(TypeError):
            timeframe_ids(date(2024, 6, 10), self.frames)
        self.assertEqual(
            ReportingSlice(2025, "all_hours"),
            reporting_slices(datetime(2024, 6, 10, 10), date(2025, 1, 1), self.frames)[1],
        )


if __name__ == "__main__":
    unittest.main()
