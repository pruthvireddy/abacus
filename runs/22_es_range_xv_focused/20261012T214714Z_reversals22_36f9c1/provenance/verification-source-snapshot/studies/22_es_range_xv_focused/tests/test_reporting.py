"""Saved-evidence projection and bounded public artifacts from synthetic tables."""

from __future__ import annotations

import csv
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout


_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
import reporting
from analysis import Coverage, analyze
from timeframes import load_timeframes
from test_analysis import trend
from test_trends import make_bar
from trends import inferred_session_date


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class ReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.stage = Path(self.temporary.name) / "synthetic-run"
        self.stage.mkdir()
        (self.stage / "config.json").write_text((_ROOT / "study.yaml").read_text())
        frames = load_timeframes(_ROOT / "study.yaml")
        coverage = Coverage(frames)
        events = []
        for setting in (4, 5, 6):
            coverage.observe(make_bar(1, "Z", setting=setting))
            for index, length in enumerate((1, 2, 3)):
                events.append(trend(length, setting=setting, row=index * 10 + 1))
            events.append(trend(7, "bearish", setting=setting, row=41))
            events.append(trend(100, setting=setting, row=61, right=True))
        tables = analyze(events, [4, 5, 6], frames, coverage)
        # Preserve a deliberately noncanonical numeric representation exactly in
        # CSV downloads; numeric table presentation still shows the same value.
        tables.summaries[0]["mean_candles"] = "2.000000000000000000"
        for filename, rows in (("trend_summary.csv", tables.summaries),
                               ("trend_histogram.csv", tables.histograms),
                               ("trend_survival.csv", tables.survival)):
            write_csv(self.stage / "tables" / filename, rows)
        audits = [{"setting_ticks": setting, "input_rows": 20,
                   "primary_eligible_bars": 19, "doji_eligible_bars": 1}
                  for setting in (4, 5, 6)]
        (self.stage / "input-audit.json").write_text(json.dumps(audits))

    def build(self) -> None:
        with redirect_stdout(io.StringIO()):
            reporting.build_reports(self.stage)

    def populate_all_groups(self) -> None:
        """Fill every annual/window directional cell with plausible nonempty runs."""
        frames = load_timeframes(_ROOT / "study.yaml")
        coverage = Coverage(frames)
        events = []
        for setting in (4, 5, 6):
            for year in range(2019, 2027):
                for hour, minute in ((19, 45), (22, 0), (3, 0), (10, 0), (11, 0), (14, 0)):
                    stamp = datetime(year, 11 if year == 2019 else 6, 10, hour, minute)
                    session = inferred_session_date(stamp)
                    coverage.observe(make_bar(1, "Z", stamp=stamp, session=session, setting=setting))
                    for direction in ("bullish", "bearish"):
                        lengths = (1, 2, 3 + setting % 3, 6 + year % 4, 11, 21)
                        events.extend(trend(length, direction, setting=setting, row=index * 30 + 1,
                                            stamp=stamp, session=session)
                                      for index, length in enumerate(lengths))
                        events.append(trend(20, direction, setting=setting, stamp=stamp, session=session, right=True))
        tables = analyze(events, [4, 5, 6], frames, coverage)
        for filename, rows in (("trend_summary.csv", tables.summaries),
                               ("trend_histogram.csv", tables.histograms),
                               ("trend_survival.csv", tables.survival)):
            write_csv(self.stage / "tables" / filename, rows)

    def reports(self) -> list[dict]:
        return [json.loads((self.stage / "publications" / f"{setting}t" / "publication.json").read_text())
                for setting in (4, 5, 6)]

    def test_three_chart_reports_are_distinct_and_retain_source_identity(self) -> None:
        self.build()
        reports = self.reports()
        self.assertEqual(3, len({report["id"] for report in reports}))
        for setting, report in zip((4, 5, 6), reports):
            self.assertIn(f"{setting}t", report["id"])
            self.assertEqual("synthetic-run", report["source"]["runId"])
            overall = next(section for section in report["sections"] if section["id"] == "overall")
            self.assertEqual(["Bullish", "Bearish", "Both directions"], [row["direction"] for row in overall["rows"]])
            self.assertEqual(3, overall["rows"][0]["exact"])
            self.assertEqual(2, overall["rows"][0]["mean"])
            self.assertEqual(1, overall["rows"][0]["censored"])
        verification = json.loads((self.stage / "publication-verification.json").read_text())
        self.assertEqual("passed", verification["result"])
        self.assertEqual(3, len(verification["publications"]))

    def test_probability_table_values_are_ratios_and_undefined_cells_stay_null(self) -> None:
        self.build()
        for report in self.reports():
            survival = next(section for section in report["sections"] if section["id"] == "survival")
            cell = next(row for row in survival["rows"] if row["direction"] == "Bullish" and row["length"] == "2")
            self.assertAlmostEqual(2 / 3, cell["share"], places=6)
            self.assertEqual((2, 3), (cell["count"], cell["denominator"]))
            column = next(column for column in survival["columns"] if column["key"] == "share")
            self.assertEqual("percent", column["format"])
            yearly = next(section for section in report["sections"] if section["id"] == "yearly")
            empty = next(row for row in yearly["rows"] if row["year"] == "2019 (partial)" and row["direction"] == "Bullish")
            self.assertEqual(0, empty["exact"])
            self.assertIsNone(empty["mean"])
            self.assertIsNone(empty["max"])

    def test_public_report_and_table_limits_hold_for_full_reporting_grid(self) -> None:
        self.populate_all_groups()
        self.build()
        for setting, report in zip((4, 5, 6), self.reports()):
            path = self.stage / "publications" / f"{setting}t" / "publication.json"
            self.assertLessEqual(path.stat().st_size, 96 * 1024)
            identifiers = [section["id"] for section in report["sections"]]
            self.assertEqual(len(identifiers), len(set(identifiers)))
            self.assertTrue({"overall", "yearly", "timeframes", "yearly-bullish", "yearly-bearish"}.issubset(identifiers))
            for section in report["sections"]:
                if section["kind"] == "table":
                    self.assertLessEqual(len(section["columns"]), 12)
                    self.assertLessEqual(len(section["rows"]), 100)
                    keys = [column["key"] for column in section["columns"]]
                    self.assertEqual(len(keys), len(set(keys)))
                    for row in section["rows"]:
                        self.assertEqual(set(keys), set(row))

    def test_every_displayed_numeric_table_cell_has_an_explicit_saved_source_binding(self) -> None:
        self.build()
        for setting, report in zip((4, 5, 6), self.reports()):
            target = self.stage / "publications" / f"{setting}t"
            source_map = json.loads((target / "source-map.json").read_text())
            self.assertIn("six decimals", source_map["numeric_projection"])
            source_tables = {source: reporting.read_csv(self.stage / source)[1]
                             for source in source_map["source_hashes"]}
            bindings = {(binding["section"], binding["report_row"], binding["column"]): binding
                        for binding in source_map["bindings"] if "section" in binding}
            for section in report["sections"]:
                if section["kind"] != "table":
                    continue
                numeric = [column["key"] for column in section["columns"] if column.get("format") in ("number", "percent")]
                for row_number, row in enumerate(section["rows"]):
                    for column in numeric:
                        identity = (section["id"], row_number, column)
                        self.assertIn(identity, bindings)
                        binding = bindings[identity]
                        self.assertEqual(row[column], binding["value"])
                        source = source_tables[binding["source"]][binding["source_row"] - 2]
                        self.assertEqual(source[binding["source_column"]], binding["original"])
                        self.assertEqual(reporting.number(binding["original"]), row[column])

    def test_four_csv_downloads_preserve_selected_strings_columns_rows_and_hashes(self) -> None:
        self.build()
        for setting, report in zip((4, 5, 6), self.reports()):
            self.assertEqual(4, len(report["downloads"]))
            target = self.stage / "publications" / f"{setting}t"
            source_map = json.loads((target / "source-map.json").read_text())
            for source, digest in source_map["source_hashes"].items():
                self.assertEqual(digest, hashlib.sha256((self.stage / source).read_bytes()).hexdigest())
            for download in report["downloads"]:
                path = target / download["path"]
                columns, copied = reporting.read_csv(path)
                self.assertLessEqual(len(columns), 24)
                self.assertLessEqual(len(copied), 1000)
                self.assertEqual(len(copied), download["rowCount"])
                self.assertEqual(columns, download["columns"])
                self.assertEqual(download["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
                binding = next(binding for binding in source_map["bindings"] if binding.get("download") == path.name)
                source_columns, source_rows = reporting.read_csv(self.stage / binding["source"])
                self.assertTrue(set(columns).issubset(source_columns))
                expected = [{column: source_rows[source_row - 2][column] for column in columns}
                            for source_row in binding["source_rows"]]
                self.assertEqual(expected, copied)
                self.assertTrue(binding["original_strings_verified"])
                self.assertTrue(all(row["setting_ticks"] == str(setting) for row in copied))
            columns, rows = reporting.read_csv(target / "downloads" / "trend-summary.csv")
            self.assertEqual("2.000000000000000000" if setting == 4 else "2.0", rows[0]["mean_candles"])
            empty = next(row for row in rows if row["year"] == "2019")
            self.assertEqual("", empty["mean_candles"])

    def test_numeric_transfer_guard_refuses_saved_source_mismatch(self) -> None:
        original_number = reporting.number
        corrupted = False

        def corrupt_one_projection(raw: str):
            nonlocal corrupted
            if raw == "2.000000000000000000" and not corrupted:
                corrupted = True
                return 999
            return original_number(raw)

        with patch.object(reporting, "number", side_effect=corrupt_one_projection):
            with redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, "public table cell disagrees"):
                    reporting.build_reports(self.stage)
        self.assertFalse((self.stage / "publication-verification.json").exists())

    def test_publication_sources_refuse_overwrite(self) -> None:
        self.build()
        with self.assertRaises(FileExistsError):
            self.build()


if __name__ == "__main__":
    unittest.main()
