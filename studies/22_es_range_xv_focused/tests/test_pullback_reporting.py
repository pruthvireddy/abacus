"""Saved-source projections across all horizons, cohorts and reporting slices."""
import csv
import hashlib
import importlib.util
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import sys
import shutil
import tempfile
import unittest

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / "src"))
from analysis import Coverage
from pullback_analysis import analyze_pullbacks
from pullbacks import extract_pullbacks
from pullback_payoff import evaluate_payoffs, analyze_payoffs
from pullback_reporting import build_reports, read_csv, number, _verify_bindings
from timeframes import load_timeframes
from trends import Bar


class PullbackReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.stage = Path(cls.temp.name) / "synthetic_pullback"
        cls.stage.mkdir()
        configuration = json.loads((STUDY / "pullback.yaml").read_text())
        (cls.stage / "config.json").write_text(json.dumps(configuration))
        frames = load_timeframes(cls.stage / "config.json")
        coverage = Coverage(frames)
        outputs = {"summary": [], "continuation": [], "retracement": [], "payoff": []}
        pairs = [(100, 100, 100), (100, 101, 100), (101, 102, 101), (102, 103, 102),
                 (103, 102, 102), (102, 103, 102), (103, 104, 102.5), (104, 105, 103.9),
                 (105, 104, 104), (104, 104, 104)]
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
            events = list(extract_pullbacks(bars, setting))
            result = analyze_pullbacks(events, [setting], frames, coverage)
            outputs["payoff"].extend(analyze_payoffs(evaluate_payoffs(events, bars, setting), [setting], frames))
            for key, rows in (("summary", result.summaries), ("continuation", result.continuation), ("retracement", result.retracement)):
                outputs[key].extend(rows)
        (cls.stage / "tables").mkdir()
        for key, rows in [*outputs.items(), ("coverage", coverage.rows([4, 5, 6]))]:
            filename = "coverage.csv" if key == "coverage" else "pullback_" + key + ".csv"
            with (cls.stage / "tables" / filename).open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows({k: "" if value is None else value for k, value in row.items()} for row in rows)
        (cls.stage / "input-audit.json").write_text('{}\n')
        cls.result = build_reports(cls.stage)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_nine_reports_all_1080_contexts_and_all_twenty_horizons(self):
        self.assertEqual(len(self.result["publications"]), 9)
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
        source_rows = read_csv(self.stage / "tables/pullback_continuation.csv")[1]
        for filename, column in (("probabilities.csv", "probability"), ("successes.csv", "numerator"),
                                 ("known-outcomes.csv", "denominator"), ("unknown-outcomes.csv", "unknown_count")):
            header, projected = read_csv(self.stage / "publications/4t-continuation/downloads" / filename)
            self.assertEqual(len(header), 24)
            self.assertEqual(len(projected), 3240)
            index = {tuple(row[k] for k in ("year", "timeframe_id", "direction", "earlier_leg_bucket")): row for row in projected}
            for row in source_rows:
                if row["setting_ticks"] == "4":
                    key = tuple(row[k] for k in ("year", "timeframe_id", "direction", "earlier_leg_bucket"))
                    self.assertEqual(index[key]["n" + row["n"]], row[column])
        _header, retraces = read_csv(self.stage / "publications/4t-retracement/downloads/retracement-recovery.csv")
        self.assertEqual(len(retraces), 12960)
        self.assertTrue(any(r["earlier_leg_bucket"] == "unknown_start" for r in retraces))

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

    def test_setup_labels_distinguish_earlier_a_from_one_candle_b(self):
        report = json.loads((self.stage / "publications/4t-continuation/publication.json").read_text())
        definition = report["sections"][0]["body"]
        self.assertIn("A1,A2,A3", definition)
        self.assertIn("one completed opposite-colour candle", definition)
        self.assertIn("measures A, not the one-candle B", definition)
        table = next(s for s in report["sections"] if s["id"] == "n1-8-bullish")
        self.assertEqual(table["rowFilters"][2]["label"], "Earlier trend length")
        self.assertEqual(table["columns"][2]["label"], "Earlier original-direction leg")
        self.assertTrue(any(row["leg"] == "Unknown earlier start" for row in table["rows"]))
        self.assertTrue(any(row["leg"] == "1 candle" for row in table["rows"]))

    def test_wrong_context_label_is_refused_even_when_numeric_value_matches(self):
        path = self.stage / "tables/pullback_summary.csv"
        headers, rows = read_csv(path)
        source = rows[0]
        source_number = number(source["event_count"])
        table = {"id": "cohort", "kind": "table", "rowFilters": [{"key": "year"}],
                 "rows": [{"year": "Wrong year", "window": "All hours", "leg": "All earlier legs", "e": source_number}]}
        binding = {"section": "cohort", "report_row": 0, "column": "e", "source": "tables/pullback_summary.csv",
                   "source_row": 2, "source_column": "event_count", "original": source["event_count"], "value": source_number}
        with self.assertRaisesRegex(ValueError, "cohort context differs"):
            _verify_bindings({"sections": [table]}, [binding], self.stage, {"summary": (headers, rows)}, {"summary": path})

    def test_payoff_is_explicit_gross_ohlc_bounds_with_all_saved_counts(self):
        report = json.loads((self.stage / "publications/4t-payoff/publication.json").read_text())
        definition = report["sections"][0]["body"]
        self.assertIn("gross OHLC price-path proxy", definition)
        self.assertIn("No fill, costs, slippage", definition)
        tables = [section for section in report["sections"] if section["id"].startswith("target-")]
        self.assertEqual(len(tables), 6)
        self.assertTrue(all(len(section["rows"]) == 1080 for section in tables))
        self.assertTrue(all(len(section["columns"]) == 12 for section in tables))
        section = next(section for section in tables if section["id"] == "target-1r-bullish")
        row = next(row for row in section["rows"] if row["year"] == "All years" and row["window"] == "All hours" and row["leg"] == "3 candles")
        self.assertEqual((row["e"], row["k"], row["u"], row["a"], row["lo"], row["hi"], row["wl"], row["wh"]),
                         (1, 1, 0, 0, 1, 1, 1, 1))
        sources = {tuple(row[key] for key in ("year", "timeframe_id", "direction", "earlier_leg_bucket", "target_multiple")): row
                   for row in read_csv(self.stage / "tables/pullback_payoff.csv")[1] if row["setting_ticks"] == "4"}
        union = set()
        for filename in ("gross-ohlc-payoff.csv", "payoff-resolution.csv"):
            header, copied = read_csv(self.stage / "publications/4t-payoff/downloads" / filename)
            self.assertEqual(len(header), 24)
            self.assertEqual(len(copied), 6480)
            union.update(header)
            for row in copied:
                key = tuple(row[key] for key in ("year", "timeframe_id", "direction", "earlier_leg_bucket", "target_multiple"))
                self.assertEqual(row, {column: sources[key][column] for column in header})
        self.assertEqual(union, set(read_csv(self.stage / "tables/pullback_payoff.csv")[0]) - {"setting_ticks", "units"})

    def test_portability_export_retains_exact_reports_and_frozen_exporter(self):
        spec = importlib.util.spec_from_file_location("pullback_export_under_test", STUDY / "pullback_export.py")
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        with tempfile.TemporaryDirectory() as temp:
            exporter.ROOT = Path(temp)
            run = exporter.ROOT / "runs" / exporter.STUDY_ID / self.stage.name
            shutil.copytree(self.stage, run)
            for name in ("verification.json", "preseal-checks.json"):
                (run / name).write_text('{"result":"passed"}\n')
            (run / "inputs.lock.json").write_text('{}\n')
            artifacts = [{"path": p.relative_to(run).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                         for p in sorted(run.rglob("*")) if p.is_file()]
            (run / "manifest.json").write_text(json.dumps({"study_id": exporter.STUDY_ID,
                                                         "run_id": run.name, "artifacts": artifacts}))
            revisions = exporter.export(run.name, "synthetic_web")
            self.assertEqual(len(revisions), 9)
            for revision in revisions:
                target = exporter.ROOT / revision["revision"]
                manifest = json.loads((target / "manifest.json").read_text())
                source_name = target.name.removeprefix("synthetic_web_").replace("_", "-")
                self.assertEqual((target / "publication.json").read_bytes(),
                                 (run / "publications" / source_name / "publication.json").read_bytes())
                self.assertEqual((target / "producer-source/pullback_export.py").read_bytes(),
                                 (STUDY / "pullback_export.py").read_bytes())
                self.assertTrue(any(item["path"].endswith("producer-source/pullback_export.py")
                                    for item in manifest["outputs"]))
                self.assertFalse(any(item["path"] == "studies/22_es_range_xv_focused/pullback_export.py"
                                     for item in manifest["source_artifacts"]))
            with self.assertRaises(FileExistsError):
                exporter.export(run.name, "synthetic_web")
            (run / "verification.json").write_text('{"result":"passed","tampered":true}\n')
            with self.assertRaisesRegex(ValueError, "gate bytes differ"):
                exporter.export(run.name, "synthetic_web_other")

    def test_unbound_numeric_transfer_is_refused(self):
        report = {"sections": [{"id": "unbound", "kind": "table", "rows": [{"p": .5}]}]}
        with self.assertRaisesRegex(ValueError, "lacks saved-source binding"):
            _verify_bindings(report, [], self.stage, {}, {})


if __name__ == "__main__":
    unittest.main()
