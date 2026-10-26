"""Frozen expectations for the existing pinned holiday exclusion rules."""

from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from abacus_bhishma import vp_hvn_release
from abacus_bhishma.calendar import (
    _easter,
    _last_weekday,
    _nth_weekday,
    _observed,
    holiday_sessions,
)
from abacus_bhishma.session_anchored_vwap import holiday_sessions as vwap_holiday_sessions


# Specified and checked against the pre-extraction implementation.  These fixtures
# intentionally include the mourning dates outside the requested year range.
HOLIDAYS_2021 = {
    date(2021, 1, 1): ["New Year's"],
    date(2021, 1, 18): ["Martin Luther King Jr. Day"],
    date(2021, 2, 15): ["Presidents Day"],
    date(2021, 4, 2): ["Good Friday"],
    date(2021, 5, 31): ["Memorial Day"],
    date(2021, 7, 5): ["Independence Day"],
    date(2021, 9, 6): ["Labor Day"],
    date(2021, 11, 25): ["Thanksgiving"],
    date(2021, 11, 26): ["Thanksgiving Friday early close"],
    date(2021, 12, 24): ["Christmas", "Christmas Eve early close"],
    date(2018, 12, 5): ["National day of mourning"],
    date(2025, 1, 9): ["National day of mourning"],
}

EQUITY_HOLIDAYS_2024 = {
    date(2024, 1, 1): ["New Year's"],
    date(2024, 1, 15): ["Martin Luther King Jr. Day"],
    date(2024, 2, 19): ["Presidents Day"],
    date(2024, 3, 29): ["Good Friday"],
    date(2024, 5, 27): ["Memorial Day"],
    date(2024, 6, 19): ["Juneteenth"],
    date(2024, 7, 3): ["Independence Day adjacent equity early close"],
    date(2024, 7, 4): ["Independence Day"],
    date(2024, 9, 2): ["Labor Day"],
    date(2024, 11, 28): ["Thanksgiving"],
    date(2024, 11, 29): ["Thanksgiving Friday early close"],
    date(2024, 12, 24): ["Christmas Eve early close"],
    date(2024, 12, 25): ["Christmas"],
    date(2018, 12, 5): ["National day of mourning"],
    date(2025, 1, 9): ["National day of mourning"],
}


class HolidayCalendarTests(unittest.TestCase):
    def test_complete_frozen_2021_fixture(self) -> None:
        for product in ("ES", "NQ", "GC"):
            with self.subTest(product=product):
                self.assertEqual(holiday_sessions(product, 2021, 2021), HOLIDAYS_2021)

    def test_complete_frozen_2024_fixture_and_product_difference(self) -> None:
        for product in ("ES", "NQ"):
            with self.subTest(product=product):
                self.assertEqual(
                    holiday_sessions(product, 2024, 2024), EQUITY_HOLIDAYS_2024
                )
        metal_holidays = dict(EQUITY_HOLIDAYS_2024)
        del metal_holidays[date(2024, 7, 3)]
        self.assertEqual(holiday_sessions("GC", 2024, 2024), metal_holidays)

    def test_new_year_weekend_and_year_boundary_behavior(self) -> None:
        saturday = holiday_sessions("ES", 2022, 2022)
        self.assertEqual(saturday[date(2022, 1, 1)], ["New Year's"])
        self.assertNotIn(date(2021, 12, 31), saturday)
        self.assertNotIn(date(2022, 1, 3), saturday)
        sunday = holiday_sessions("ES", 2023, 2023)
        self.assertEqual(sunday[date(2023, 1, 2)], ["New Year's"])
        self.assertNotIn(date(2023, 1, 1), sunday)
        combined = holiday_sessions("ES", 2021, 2023)
        self.assertNotIn(date(2021, 12, 31), combined)

    def test_juneteenth_start_year_and_observed_weekday(self) -> None:
        self.assertNotIn(date(2021, 6, 18), holiday_sessions("ES", 2021, 2021))
        self.assertNotIn(date(2021, 6, 19), holiday_sessions("ES", 2021, 2021))
        self.assertEqual(
            holiday_sessions("GC", 2022, 2022)[date(2022, 6, 20)], ["Juneteenth"]
        )
        self.assertEqual(
            holiday_sessions("GC", 2023, 2023)[date(2023, 6, 19)], ["Juneteenth"]
        )

    def test_observed_holiday_collision_reason_order(self) -> None:
        equity = holiday_sessions("NQ", 2026, 2026)
        self.assertEqual(
            equity[date(2026, 7, 3)],
            ["Independence Day", "Independence Day adjacent equity early close"],
        )
        self.assertEqual(
            holiday_sessions("GC", 2026, 2026)[date(2026, 7, 3)], ["Independence Day"]
        )
        self.assertEqual(
            holiday_sessions("GC", 2022, 2022)[date(2022, 12, 26)], ["Christmas"]
        )

    def test_mourning_entries_are_unconditional(self) -> None:
        expected = {
            date(2018, 12, 5): ["National day of mourning"],
            date(2025, 1, 9): ["National day of mourning"],
        }
        self.assertEqual(holiday_sessions("GC", 2026, 2025), expected)
        for product in ("ES", "NQ", "GC"):
            for year in (2010, 2018, 2025, 2026):
                with self.subTest(product=product, year=year):
                    holidays = holiday_sessions(product, year, year)
                    for day, reasons in expected.items():
                        self.assertEqual(holidays[day], reasons)

    def test_vwap_compatibility_import_preserves_frozen_expectations(self) -> None:
        self.assertEqual(vwap_holiday_sessions("ES", 2021, 2021), HOLIDAYS_2021)
        self.assertEqual(vwap_holiday_sessions("NQ", 2024, 2024), EQUITY_HOLIDAYS_2024)


class HolidayDateHelperTests(unittest.TestCase):
    def test_easter_dates(self) -> None:
        self.assertEqual(_easter(2021), date(2021, 4, 4))
        self.assertEqual(_easter(2024), date(2024, 3, 31))
        self.assertEqual(_easter(2025), date(2025, 4, 20))

    def test_nth_and_last_weekdays(self) -> None:
        self.assertEqual(_nth_weekday(2024, 11, 3, 4), date(2024, 11, 28))
        self.assertEqual(_last_weekday(2024, 5, 0), date(2024, 5, 27))
        self.assertEqual(_last_weekday(2024, 12, 0), date(2024, 12, 30))
        self.assertEqual(_last_weekday(2024, 2, 3), date(2024, 2, 29))

    def test_observed_weekdays(self) -> None:
        self.assertEqual(_observed(date(2021, 12, 25)), date(2021, 12, 24))
        self.assertEqual(_observed(date(2022, 12, 25)), date(2022, 12, 26))
        self.assertEqual(_observed(date(2024, 7, 4)), date(2024, 7, 4))


class CalendarSourceProvenanceTests(unittest.TestCase):
    def test_vp_hvn_sources_include_calendar_and_detect_changed_bytes(self) -> None:
        with TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            package = workspace / "packages/bhishma/src/abacus_bhishma"
            package.mkdir(parents=True)
            sources = {
                "vp_hvn.py": b"profile engine\n",
                "vp_hvn_release.py": b"release builder\n",
                "vp_hvn_native.cpp": b"native accelerator\n",
                "calendar.py": b"pinned holidays\n",
                "vp_hvn_loader.py": b"consumer loader\n",
                "continuous_loader.py": b"continuous loader\n",
                "manifest_selection.py": b"manifest selection\n",
                "paths.py": b"path configuration\n",
                "provenance.py": b"file provenance\n",
                "publication_safety.py": b"publication guards\n",
                "unrelated.py": b"not an executed helper\n",
            }
            for name, payload in sources.items():
                (package / name).write_bytes(payload)
            (package / "vp_hvn_directory").mkdir()
            prefix = "packages/bhishma/src/abacus_bhishma/"
            expected = [
                {
                    "path": prefix + "vp_hvn_release.py",
                    "sha256": "490ee323717e4c605d979e8b0082bbeb149b61402376341ceabf5491e79cf9be",
                },
                {
                    "path": prefix + "vp_hvn.py",
                    "sha256": "c0f0d1984dcd7acafe5959cf7b7b0f3cdde215a9baa89a1a9ec99013ed62358a",
                },
                {
                    "path": prefix + "vp_hvn_native.cpp",
                    "sha256": "90c0348b1297a14b13d3438694aeba0d0486a86be4c6184ac4f6e14292df9c8a",
                },
                {
                    "path": prefix + "vp_hvn_loader.py",
                    "sha256": "fde53fc1ef9e5e92f3f6f7543ba16ef5fa73fde14230707b8e224c796450c428",
                },
                {
                    "path": prefix + "calendar.py",
                    "sha256": "5ecc00f02554ecfa5518c70a4b71c78f06f8ccbc1ce72200d3c8a9c758fb6b57",
                },
                {
                    "path": prefix + "continuous_loader.py",
                    "sha256": "c833be2acfb1eba4a652610e3efef02419e78207752502f049a40c924a4850f4",
                },
                {
                    "path": prefix + "manifest_selection.py",
                    "sha256": "f38dff0dec4adf29815eb44e3bb47bf8644f56b72badcad4bb8e5e0f492e07d8",
                },
                {
                    "path": prefix + "paths.py",
                    "sha256": "7ffa93d9f95dcc9aa699754f22482e3cf99567a48345d312eea8f876e140e7e4",
                },
                {
                    "path": prefix + "provenance.py",
                    "sha256": "27aff5302e7157989fb7937f1c83ef7c74597842387f35e0e8a5cf2edb460bad",
                },
                {
                    "path": prefix + "publication_safety.py",
                    "sha256": "c832b8267d8c6dab825c42a06297f23cfcdb0cc8788db2b80c4e7e4a0ecdc42a",
                },
            ]
            self.assertEqual(vp_hvn_release._code_sources(workspace), expected)
            (package / "calendar.py").write_bytes(b"pinned holidays changed\n")
            changed = vp_hvn_release._code_sources(workspace)
            self.assertEqual([record for record in changed if record["path"] != prefix + "calendar.py"],
                             [record for record in expected if record["path"] != prefix + "calendar.py"])
            self.assertEqual(
                changed[4],
                {
                    "path": prefix + "calendar.py",
                    "sha256": "1f494fb7808d552159c91cb3894402cfeddeed9f5a23d57a6f8a8626f0ee0c84",
                },
            )


if __name__ == "__main__":
    unittest.main()
