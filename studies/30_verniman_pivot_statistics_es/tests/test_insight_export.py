"""Presentation-transfer guards using synthetic rows; no market-data execution."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

OWNER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OWNER))
spec = importlib.util.spec_from_file_location("study30_insight_export", OWNER / "publish_insights.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def section():
    return {"id": "s09", "title": "Movement", "rows": [
        {"period": "overall: all", "selection": "Pivot-matched · RTH · EMA6/pivot · All sections · Both directions · All crosses · 30m",
         "metric": "displacement [points]", "value": -0.04, "share": None,
         "denominator": 1790, "days": 636, "unknown": 96, "censored": 0},
        {"period": "overall: all", "selection": "Other cohort", "metric": "positive [fraction]",
         "value": None, "share": 0.0, "denominator": 3, "days": 2, "unknown": 1, "censored": 1}]}


class InsightExportTests(unittest.TestCase):
    def test_binding_requires_unique_typed_saved_row(self):
        saved = {"id": "typed", "rows": [{"flag": False, "value": 9}, {"flag": 0, "value": 0}]}
        text, evidence = p.resolve_binding(saved, {"where": {"flag": 0}, "column": "value", "format": "integer"})
        self.assertEqual(text, "0")
        self.assertEqual(evidence["source_row"], 1)
        saved["rows"].append({"flag": 0, "value": 3})
        with self.assertRaisesRegex(ValueError, "Expected one saved row"):
            p.resolve_binding(saved, {"where": {"flag": 0}, "column": "value", "format": "integer"})

    def test_missing_and_fractional_integer_are_not_reported_as_zero(self):
        saved = {"id": "missing", "rows": [{"id": "a", "value": None}]}
        binding = {"where": {"id": "a"}, "column": "value", "format": "integer"}
        self.assertEqual(p.resolve_binding(saved, binding)[0], "not available")
        saved["rows"][0]["value"] = 0.75
        with self.assertRaisesRegex(ValueError, "discard"):
            p.resolve_binding(saved, binding)

    def test_projection_selects_cited_rows_once_and_preserves_support(self):
        saved = section()
        before = deepcopy(saved)
        table, indices = p.compact_table(saved, {"mean": {"source_row": 0, "column": "value"}, "n": {"source_row": 0, "column": "denominator"}, "rate": {"source_row": 1, "column": "share"}})
        self.assertEqual(indices, [0, 1])
        self.assertEqual(saved, before)
        self.assertEqual(table["rows"][0]["value"], -0.04)
        self.assertIsNone(table["rows"][0]["share"])
        self.assertEqual(table["rows"][1]["share"], 0.0)
        self.assertEqual(table["rows"][0]["unknown"], 96)
        self.assertEqual(table["rows"][1]["censored"], 1)
        self.assertEqual(table["rows"][0]["days"], 636)
        self.assertIn("30m", table["rows"][0]["measure"])

    def test_compact_labels_keep_distinct_populations_and_periods(self):
        row = section()["rows"][0]
        rth = {**row, "selection": "VWAP-only RTH · RTH · EMA6/vwap · All sections · Both directions · All crosses"}
        globex = {**rth, "selection": "VWAP-only Globex · Globex · EMA6/vwap · All sections · Both directions · All crosses"}
        self.assertNotEqual(p.compact_measure(rth), p.compact_measure(globex))
        self.assertIn("Full Globex", p.compact_measure(globex))
        self.assertNotEqual(p.compact_measure(rth), p.compact_measure({**rth, "period": "recent: last_20"}))

    def test_pinned_bytes_reject_tampering_and_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "saved.json").write_bytes(b"saved")
            entry = {"path": "saved.json", "sha256": hashlib.sha256(b"saved").hexdigest()}
            self.assertEqual(p.read_pinned(root, entry), b"saved")
            (root / "saved.json").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Changed pinned source"):
                p.read_pinned(root, entry)
            with self.assertRaisesRegex(ValueError, "Invalid source locator"):
                p.read_pinned(root, {**entry, "path": "../saved.json"})

    def test_fresh_revision_refuses_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "revision"
            p.write_files(destination, {"saved.json": b"original"})
            with self.assertRaises(FileExistsError):
                p.write_files(destination, {"saved.json": b"replacement"})
            self.assertEqual((destination / "saved.json").read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
