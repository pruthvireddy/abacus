"""Saved-source projections across all horizons, cohorts and reporting slices."""
import csv
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / "src"))
from analysis import Coverage
from reversal_analysis import analyze_reversals
from reversals import extract_reversals
from reversal_reporting import build_reports, read_csv, number, _verify_bindings
from timeframes import load_timeframes
from trends import Bar


class ReversalReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.stage = Path(cls.temp.name) / "synthetic_reversal"
        cls.stage.mkdir()
        (cls.stage / "config.json").write_bytes((STUDY / "reversal.yaml").read_bytes())
        frames = load_timeframes(STUDY / "reversal.yaml")
        coverage = Coverage(frames)
        outputs = {"summary": [], "continuation": [], "retracement": []}
        pairs = [(100, 100, 100), (100, 99, 99), (99, 98, 98), (98, 97, 97),
                 (97, 98, 97), (98, 99, 97.5), (99, 100, 98.9), (100, 99, 99), (99, 99, 99)]
        for setting in (4, 5, 6):
            bars = []
            for i, (opening, close, low) in enumerate(pairs, 1):
                stamp = datetime(2020, 1, 2, 10) + timedelta(seconds=i)
                terminal = i == len(pairs)
                bar = Bar(setting, i, stamp, None if terminal else stamp + timedelta(seconds=1), date(2020, 1, 2),
                          Decimal(str(opening)), Decimal(str(max(opening, close) + .25)), Decimal(str(low)), Decimal(str(close)),
                          "unavailable_export_end" if terminal else "next_bar_start_proxy", not terminal,
                          "completion_status:unavailable_export_end" if terminal else None)
                bars.append(bar)
                coverage.observe(bar)
            result = analyze_reversals(extract_reversals(bars, setting), [setting], frames, coverage)
            for key, rows in (("summary", result.summaries), ("continuation", result.continuation), ("retracement", result.retracement)):
                outputs[key].extend(rows)
        (cls.stage / "tables").mkdir()
        for key, rows in [*outputs.items(), ("coverage", coverage.rows([4, 5, 6]))]:
            filename = "coverage.csv" if key == "coverage" else "reversal_" + key + ".csv"
            with (cls.stage / "tables" / filename).open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows({k: "" if value is None else value for k, value in row.items()} for row in rows)
        (cls.stage / "input-audit.json").write_text('{}\n')
        cls.result = build_reports(cls.stage)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_six_reports_all_1080_contexts_and_all_twenty_horizons(self):
        self.assertEqual(len(self.result["publications"]), 6)
        report = json.loads((self.stage / "publications/4t-continuation/publication.json").read_text())
        tables = [s for s in report["sections"] if s["id"].startswith("n")]
        self.assertEqual(len(tables), 6)
        self.assertTrue(all(len(t["rows"]) == 1080 for t in tables))
        self.assertTrue(all(len(t["columns"]) <= 12 for t in tables))
        cols = {c["key"] for t in tables for c in t["columns"]}
        self.assertTrue({"n" + str(i) for i in range(1, 21)} <= cols)
        row = next(r for r in tables[0]["rows"] if r["year"] == "All years" and r["window"] == "All hours" and r["leg"] == "3 candles")
        self.assertEqual(row["n2"], 1)
        self.assertEqual(row["n3"], 0)
        self.assertEqual(report["source"]["runId"], self.stage.name)

    def test_csv_pivots_preserve_all_saved_original_strings(self):
        source_rows = read_csv(self.stage / "tables/reversal_continuation.csv")[1]
        for filename, column in (("probabilities.csv", "probability"), ("successes.csv", "numerator"),
                                 ("known-outcomes.csv", "denominator"), ("unknown-outcomes.csv", "unknown_count")):
            header, projected = read_csv(self.stage / "publications/4t-continuation/downloads" / filename)
            self.assertEqual(len(header), 24)
            self.assertEqual(len(projected), 3240)
            index = {tuple(row[k] for k in ("year", "timeframe_id", "direction", "prior_leg_bucket")): row for row in projected}
            for row in source_rows:
                if row["setting_ticks"] == "4":
                    key = tuple(row[k] for k in ("year", "timeframe_id", "direction", "prior_leg_bucket"))
                    self.assertEqual(index[key]["n" + row["n"]], row[column])
        _header, retraces = read_csv(self.stage / "publications/4t-retracement/downloads/retracement-recovery.csv")
        self.assertEqual(len(retraces), 12960)
        self.assertTrue(any(r["prior_leg_bucket"] == "unknown_start" for r in retraces))

    def test_undefined_is_null_and_existing_report_source_is_refused(self):
        self.assertIsNone(number(""))
        self.assertEqual(number("0"), 0)
        self.assertEqual(number("0.123456789"), .123457)
        with self.assertRaises(FileExistsError):
            build_reports(self.stage)
        report = json.loads((self.stage / "publications/4t-retracement/publication.json").read_text())
        table = next(s for s in report["sections"] if s["id"] == "depth-25-bullish")
        row = next(r for r in table["rows"] if r["year"] == "All years" and r["window"] == "All hours" and r["leg"] == "3 candles")
        self.assertEqual((row["f"], row["t"], row["j"], row["q"], row["r"]), (1, 1, 1, 1, 1))
        empty = next(r for r in table["rows"] if r["year"] == "All years" and r["window"] == "All hours" and r["leg"] == "10 candles")
        self.assertIsNone(empty["r"])

    def test_unbound_numeric_transfer_is_refused(self):
        report = {"sections": [{"id": "unbound", "kind": "table", "rows": [{"p": .5}]}]}
        with self.assertRaisesRegex(ValueError, "lacks saved-source binding"):
            _verify_bindings(report, [], self.stage, {}, {})


if __name__ == "__main__":
    unittest.main()
