"""Synthetic selected-source/rendering checks; no retained market data."""
import csv
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.reporting import (TABLES, project_download, project_table, render_bundle,
                           select_examples, sha256)
from src.reconcile import verify_publication


def fixture_tables(stage):
    (stage / "tables").mkdir()
    rows, coverage, flow, quantiles, annual, months = [], [], [], [], [], []
    for product in ("ES", "GC", "NQ"):
        for interval in (3, 5):
            row = {"row_id": f"test|{product}|{interval}", "product": product, "interval_minutes": interval,
                   "direction": "All", "horizon": 15, "horizon_minutes": interval * 15,
                   "unit": "points", "support": "all", "split": "development",
                   "accepted": 4, "completed": 3, "censored": 1, "contributing_sessions": 2,
                   "contributing_weeks": 2, "mean_mfe": 1.25, "mean_mae": .5,
                   "mean_terminal_delta": -.25, "favorable_share": 1 / 3,
                   "session_mean_terminal_delta": -.125, "ci95_low": -1., "ci95_high": .75,
                   "sparse_warning": True}
            rows.append(row)
            for metric in ("mfe", "mae", "terminal_delta"):
                for p in (0., .1, .5, .9, 1.):
                    quantiles.append(row | {"row_id": row["row_id"] + f"|{metric}|{p}", "metric": metric, "quantile": p, "value": p})
            coverage.append({"row_id": "coverage|" + product + str(interval), "product": product,
                             "interval_minutes": interval, "year": 2018, "split": "development", "scheduled_slots": 100,
                             "usable_slots": 95, "missing_slots": 5})
            flow.append(row | {"row_id": "flow|" + product + str(interval), "flow_kind": "signal", "reason": "accepted", "count": 4})
            for year in (2018, 2019, 2020):
                annual.append(row | {"row_id": row["row_id"] + str(year), "period_kind": "year", "period": year})
            months.append(row | {"row_id": row["row_id"] + "|month", "period_kind": "month", "period": "2018-01"})
    pd.DataFrame(rows).to_csv(stage / "tables" / TABLES["S1-T02"], index=False, float_format="%.17g")
    for key, value in (("S1-T00", coverage), ("S1-T01", flow), ("S1-T03", quantiles), ("S1-T04", annual), ("S1-T05", months)):
        pd.DataFrame(value).to_csv(stage / "tables" / TABLES[key], index=False, float_format="%.17g")
    empty = pd.DataFrame(columns=["product", "interval_minutes", "timestamp"])
    examples = select_examples(empty, empty, empty)
    examples.to_csv(stage / "tables" / TABLES["S1-T06"], index=False)


class ProjectionTests(unittest.TestCase):
    def test_string_blank_ratio_and_identifier_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "table.csv"
            path.write_text("row_id,label,ratio,missing\na_b,False,0.33333333333333331,\n")
            rows, bindings = project_table(path, columns=[{"key": "row_id", "label": "ID"},
                                                          {"key": "label", "label": "Label"},
                                                          {"key": "ratio", "label": "Ratio", "format": "percent"},
                                                          {"key": "missing", "label": "Missing", "format": "number"}],
                                           selector={"row_id": ["a_b"]}, section="test", source_artifact="tables/table.csv")
            self.assertEqual(rows[0]["row_id"], "a_b")
            self.assertEqual(rows[0]["label"], "False")
            self.assertIsNone(rows[0]["missing"])
            self.assertEqual(bindings[2]["source_raw"], "0.33333333333333331")
            self.assertAlmostEqual(rows[0]["ratio"], 1 / 3)

    def test_download_keeps_source_strings_after_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            (stage / "tables").mkdir()
            source = stage / "tables/table.csv"
            source.write_text("row_id,value,flag,blank\na,1.0000000000000000,False,\nb,0,True,\n")
            declaration, binding = project_download(stage, source, columns=["row_id", "value", "flag", "blank"],
                                                     selector={"row_id": ["a"]}, filename="selected.csv", run_id="test", download_id="selected", description="Test projection")
            self.assertEqual((stage / declaration["path"]).read_text(), "row_id,value,flag,blank\na,1.0000000000000000,False,\n")
            self.assertEqual(binding["data_rows_1_based"], [1])

    def test_nonfinite_number_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "table.csv"
            path.write_text("value\nnan\n")
            with self.assertRaisesRegex(ValueError, "Non-finite"):
                project_table(path, columns=[{"key": "value", "label": "Value", "format": "number"}], selector={}, section="x", source_artifact="x.csv")

    def test_table_bound_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "table.csv"
            path.write_text("value\n" + "1\n" * 101)
            with self.assertRaisesRegex(ValueError, "bounds"):
                project_table(path, columns=[{"key": "value", "label": "Value"}], selector={}, section="x", source_artifact="x.csv")


class ExampleTests(unittest.TestCase):
    def test_ties_medians_rejections_partial_and_reserved_exclusion(self):
        timestamps = pd.date_range("2018-01-02T10:00Z", periods=4, freq="3min")
        outcomes = pd.DataFrame([{"product": "ES", "interval_minutes": 3, "timestamp": timestamp, "event_id": str(i),
                                 "signal_idx": i, "horizon": 15, "status": "completed" if i < 3 else "censored",
                                 "terminal_delta": [-1., 1., 3., None][i], "mfe": [4., 4., 8., None][i],
                                 "mae": [5., 5., 2., None][i]} for i, timestamp in enumerate(timestamps)])
        technical = pd.DataFrame([{"product": "ES", "interval_minutes": 3, "timestamp": timestamps[0],
                                   "signal_idx": 0, "technical_candidate": True, "accepted": False}])
        chosen = select_examples(technical, pd.DataFrame(), outcomes)
        cell = chosen[(chosen["product"] == "ES") & (chosen.interval_minutes == 3)].set_index("example_class")
        self.assertEqual(cell.loc["typical", "event_id"], "1")
        self.assertEqual(cell.loc["high_adverse", "event_id"], "0")
        self.assertEqual(cell.loc["high_favorable", "event_id"], "2")
        self.assertEqual(cell.loc["partial", "event_id"], "3")
        self.assertEqual(cell.loc["rejected", "signal_idx"], 0)
        self.assertEqual(len(chosen), 30)
        reserved = outcomes.copy()
        reserved["timestamp"] = pd.to_datetime(reserved.timestamp) + pd.DateOffset(years=5)
        unavailable = select_examples(pd.DataFrame(), pd.DataFrame(), reserved)
        self.assertTrue(unavailable.selection_status.eq("unavailable").all())


class BundleTests(unittest.TestCase):
    def test_saved_only_bundle_and_exact_transfer(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            fixture_tables(stage)
            receipt = render_bundle(stage, "20261010T215130Z_s1_test", figures=False)
            self.assertEqual(receipt["claim_count"], 6)
            self.assertEqual(receipt["download_count"], 4)
            self.assertEqual(verify_publication(stage)["status"], "passed")
            self.assertIn("includes zero", (stage / "report.md").read_text())
            self.assertNotIn("<script", (stage / "report.html").read_text())

    def test_numeric_mutation_rejected_even_when_report_repin_attempted(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            fixture_tables(stage)
            render_bundle(stage, "20261010T215130Z_s1_test", figures=False)
            report = json.loads((stage / "publication.json").read_text())
            next(section for section in report["sections"] if section["id"] == "primary")["rows"][0]["mean_mfe"] = 900
            (stage / "publication.json").write_text(json.dumps(report))
            bindings = json.loads((stage / "source-bindings.json").read_text())
            bindings["publication_sha256"] = sha256(stage / "publication.json")
            (stage / "source-bindings.json").write_text(json.dumps(bindings))
            with self.assertRaisesRegex(ValueError, "public cell transfer"):
                verify_publication(stage)

    def test_reserved_table_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            fixture_tables(stage)
            path = stage / "tables" / TABLES["S1-T02"]
            path.write_text(path.read_text().replace("development", "validation"))
            with self.assertRaisesRegex(ValueError, "Reserved"):
                render_bundle(stage, "20261010T215130Z_s1_test", figures=False)

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "matplotlib available only in separately recorded existing plot context")
    def test_six_raster_figures_with_unavailable_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            fixture_tables(stage)
            receipt = render_bundle(stage, "20261010T215130Z_s1_test", figures=True)
            self.assertEqual(receipt["figure_count"], 6)
            self.assertEqual(verify_publication(stage)["figures"], 6)
            for path in (stage / "figures").glob("*.png"):
                self.assertLess(path.stat().st_size, 2 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
