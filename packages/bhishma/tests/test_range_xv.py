from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from abacus_bhishma.range_xv import enhance_range_xv, verify_enhanced


class RangeXVImportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "raw.csv"
        self.enhanced = self.root / "enhanced.csv"
        self.flags = self.root / "flags.csv"
        self.sessions = self.root / "sessions.csv"

    def convert(self, text):
        self.source.write_bytes(text.encode("ascii"))
        return enhance_range_xv(self.source, self.enhanced, self.flags, self.sessions)

    def test_day_month_clock_midnight_and_completion_boundaries(self):
        result = self.convert(
            "2026-04-01 19:00:00;1.0100;1.0200;1.0000;1.0100\r\n"
            "2026-04-01 19:00:00;1.0100;1.0200;1.0000;1.0100\r\n"
            "2026-05-01 00:30:00;1.0200;1.0200;1.0200;1.0200\r\n"
            "2026-05-01 19:00:00;1.0100;1.0200;1.0000;1.0100\r\n"
            "2026-05-07 18:00:00;1.0100;1.0200;1.0000;1.0100\r\n"
        )
        rows = [line.split(";") for line in self.enhanced.read_text().splitlines()[1:]]
        self.assertEqual(rows[0][2:7], ["2026-01-04 18:00:00", "2026-01-04 18:00:00", "0", "next_bar_start_same_second", "2026-01-05"])
        self.assertEqual(rows[1][2:7], ["2026-01-04 18:00:00", "2026-01-04 23:30:00", "19800", "next_bar_start_proxy", "2026-01-05"])
        self.assertEqual(rows[2][2:7], ["2026-01-04 23:30:00", "", "", "unavailable_session_boundary", "2026-01-05"])
        self.assertEqual(rows[-1][2:7], ["2026-07-05 18:00:00", "", "", "unavailable_export_end", "2026-07-06"])
        self.assertEqual(rows[0][7:], ["1.0100", "1.0200", "1.0000", "1.0100"])
        self.assertEqual([int(row[0]) for row in rows], [1, 2, 3, 4, 5])
        self.assertEqual(result["winter_rows_shifted"], 4)
        self.assertEqual(result["quality_flag_counts"], {"repeated_timestamp_ohlc_record": 1, "zero_range_bar": 1})
        self.assertEqual(result["rows"], 5)
        self.assertEqual(verify_enhanced(self.source, self.enhanced), 5)
        session_rows = self.sessions.read_text().splitlines()
        self.assertIn("export_end_session_partial", session_rows[-1])
        self.assertEqual(session_rows[1].split(";")[1], "3")

    def test_year_day_month_is_unambiguous_when_day_exceeds_twelve(self):
        self.convert("2017-20-07 18:00:00;0.0089610;0.0089660;0.0089600;0.0089650\n")
        row = self.enhanced.read_text().splitlines()[1].split(";")
        self.assertEqual(row[1:3], ["2017-20-07 18:00:00", "2017-07-20 18:00:00"])
        self.assertEqual(row[7:], ["0.0089610", "0.0089660", "0.0089600", "0.0089650"])

    def test_existing_output_is_never_overwritten(self):
        self.enhanced.write_text("retained")
        with self.assertRaises(FileExistsError):
            self.convert("2017-20-07 18:00:00;1;2;1;2\n")
        self.assertEqual(self.enhanced.read_text(), "retained")
        self.assertFalse(self.flags.exists())

    def test_invalid_input_leaves_no_partial_outputs(self):
        examples = [
            "2017-20-07 18:00:00;1;2;1;2;100\n",
            "2017-32-07 18:00:00;1;2;1;2\n",
            "2017-20-07 18:00:00;NaN;2;1;2\n",
            "2017-20-07 18:00:00;0;2;0;2\n",
            "2017-20-07 18:00:00;2;1;1;2\n",
            "2017-20-07 18:00:01;1;2;1;2\n2017-20-07 18:00:00;1;2;1;2\n",
            "",
        ]
        for text in examples:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    self.convert(text)
                self.assertTrue(all(not path.exists() for path in (self.enhanced, self.flags, self.sessions)))

    def test_verifier_rejects_changed_source_fields_and_extra_rows(self):
        self.convert("2017-20-07 18:00:00;1.000;2.000;1.000;2.000\n")
        correct = self.enhanced.read_bytes()
        for changed in (correct.replace(b";2.000\n", b";1.000\n"), correct + correct.splitlines()[-1] + b"\n"):
            with self.subTest(changed=changed):
                self.enhanced.write_bytes(changed)
                with self.assertRaises(ValueError):
                    verify_enhanced(self.source, self.enhanced)


if __name__ == "__main__":
    unittest.main()
