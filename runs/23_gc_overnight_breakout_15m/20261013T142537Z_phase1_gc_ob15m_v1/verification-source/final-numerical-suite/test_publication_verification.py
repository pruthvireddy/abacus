"""Synthetic transfer guard tests; no historical publication generation."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_publication import (SavedCells, digest, same, typed, verify_cells,
                                verify_claims, verify_downloads, verify_svg)


class PublicationTransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.stage = Path(self.temp.name)
        (self.stage / "tables").mkdir()
        self.source = self.stage / "tables" / "counts.csv"
        with self.source.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["cohort", "count", "rate", "unknown", "flag"])
            writer.writerow(["all", "4", ".25", "", "False"])
            writer.writerow(["zero", "0", "", "", "True"])
        self.saved = SavedCells(self.stage, [{"path": "tables/counts.csv", "sha256": digest(self.source)}])
        self.report = {"source": {"runId": "synthetic"}, "sections": [
            {"id": "counts", "kind": "table", "rows": [{"cohort": "all", "count": 4, "rate": .25, "unknown": None, "flag": False}]},
            {"id": "headline", "kind": "metrics", "items": [{"value": 4}]},
            {"id": "interpretation", "kind": "text", "body": "Count is positive; rate is less than half."}]}
        self.mapping = {"bindings": [dict(section="counts", row_index=0, key=key,
            source_artifact="tables/counts.csv", source_row=0, source_column=key, value_type=kind)
            for key, kind in [("cohort", "string"), ("count", "integer"), ("rate", "number"), ("unknown", "null"), ("flag", "boolean")]],
            "metric_bindings": [dict(section="headline", metric_index=0, source_artifact="tables/counts.csv", source_row=0, source_column="count", value_type="integer")]}

    def test_all_numeric_string_boolean_null_cells_exact(self):
        self.assertEqual(verify_cells(self.report, self.mapping, self.saved), 6)

    def test_unbound_cell_refused(self):
        self.mapping["bindings"].pop()
        with self.assertRaisesRegex(ValueError, "unbound"):
            verify_cells(self.report, self.mapping, self.saved)

    def test_duplicate_display_binding_refused(self):
        self.mapping["bindings"].append(dict(self.mapping["bindings"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify_cells(self.report, self.mapping, self.saved)

    def test_changed_display_value_and_boolean_as_number_refused(self):
        self.report["sections"][0]["rows"][0]["count"] = 5
        with self.assertRaisesRegex(ValueError, "transfer"):
            verify_cells(self.report, self.mapping, self.saved)
        with self.assertRaisesRegex(ValueError, "type"):
            same(True, 1, "bool is not a numeric statistic")

    def test_source_pin_tampering_refused(self):
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            SavedCells(self.stage, [{"path": "tables/counts.csv", "sha256": "0" * 64}])

    def test_zero_based_original_row_and_blank_meaning(self):
        cell = dict(source_artifact="tables/counts.csv", source_row=1, source_column="rate", value_type="number")
        self.assertIsNone(self.saved.cell(cell))
        self.assertEqual(typed("0", "number"), 0)
        self.assertEqual(typed("False", "boolean"), False)
        with self.assertRaisesRegex(ValueError, "null"):
            typed("0", "null")

    def test_claim_rule_checks_actual_saved_cells(self):
        self.mapping["claims"] = [{"id": "positive", "target": {"section": "interpretation", "field": "body"},
            "text": "Count is positive", "conditions": [dict(source_artifact="tables/counts.csv", source_row=0,
            source_column="count", value_type="integer", operator="gt", value=0)]}]
        self.assertEqual(verify_claims(self.report, self.mapping, self.saved), 1)
        self.mapping["claims"][0]["conditions"][0]["operator"] = "lt"
        with self.assertRaisesRegex(ValueError, "condition false"):
            verify_claims(self.report, self.mapping, self.saved)

    def test_json_pointer_account_metrics_keep_null_and_zero_distinct(self):
        file = self.stage / "account.json"
        file.write_text(json.dumps({"fills": 0, "win_rate": None, "fractional": False}))
        saved = SavedCells(self.stage, [{"path": "account.json", "sha256": digest(file)}])
        self.assertEqual(saved.cell(dict(source_artifact="account.json", source_pointer="/fills", value_type="number")), 0)
        self.assertIsNone(saved.cell(dict(source_artifact="account.json", source_pointer="/win_rate", value_type="number")))
        with self.assertRaisesRegex(ValueError, "numeric type"):
            saved.cell(dict(source_artifact="account.json", source_pointer="/fractional", value_type="number"))

    def test_formatted_prose_source_token_changed_refused(self):
        self.mapping["claims"] = [{"id": "count", "target": {"section": "interpretation", "field": "body"},
            "text": "Count is positive", "sources": [dict(source_artifact="tables/counts.csv", source_row=0,
            source_column="count", display=dict(style="number", precision=0, grouping=True))]}]
        with self.assertRaisesRegex(ValueError, "printed source"):
            verify_claims(self.report, self.mapping, self.saved)

    def test_svg_bar_geometry_checked_even_with_matching_artifact_hash(self):
        source = self.stage / "tables" / "figure.csv"
        source.write_text("executable_fills\n4\n")
        saved = SavedCells(self.stage, [{"path": "tables/figure.csv", "sha256": digest(source)}])
        (self.stage / "figures").mkdir()
        svg = self.stage / "figures" / "count.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect x="320" y="161.90" width="630" height="336.21"/><text x="635" y="150">4</text></svg>')
        section = dict(id="hour-chart", path="figures/count.png")
        provenance = dict(kind="saved-values",source_artifact="tables/figure.csv",source_rows=[0],svg_sha256=digest(svg))
        self.assertEqual(verify_svg(self.stage, section, provenance, saved), 1)
        svg.write_text(svg.read_text().replace('y="161.90"', 'y="200"'))
        provenance["svg_sha256"] = digest(svg)
        with self.assertRaisesRegex(ValueError, "geometry"):
            verify_svg(self.stage, section, provenance, saved)

    def test_selected_csv_preserves_original_strings_all_rows(self):
        (self.stage / "downloads").mkdir()
        target = self.stage / "downloads" / "counts.csv"
        target.write_bytes(self.source.read_bytes())
        columns = ["cohort", "count", "rate", "unknown", "flag"]
        self.report["downloads"] = [dict(id="counts", path="downloads/counts.csv", columns=columns,
            rowCount=2, sha256=digest(target), source=dict(runId="synthetic", artifact="tables/counts.csv", sha256=digest(self.source)))]
        self.mapping["downloads"] = [dict(id="counts", source_artifact="tables/counts.csv", source_rows=[0, 1], columns=columns)]
        self.assertEqual(verify_downloads(self.stage, self.report, self.mapping, self.saved), 10)
        target.write_text(target.read_text().replace(".25", "0.25"))
        self.report["downloads"][0]["sha256"] = digest(target)
        with self.assertRaisesRegex(ValueError, "original CSV"):
            verify_downloads(self.stage, self.report, self.mapping, self.saved)


if __name__ == "__main__":
    unittest.main()
