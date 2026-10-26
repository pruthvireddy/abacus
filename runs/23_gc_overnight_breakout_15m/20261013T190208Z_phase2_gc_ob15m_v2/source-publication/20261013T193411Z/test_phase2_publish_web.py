"""Synthetic saved-cell and boundary checks for the Phase 2 publication producer."""
import ast
import csv
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).resolve().parents[1] / "phase2_publish_web.py"
SPEC = importlib.util.spec_from_file_location("study23_phase2_publication_test", SCRIPT)
web = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = web
SPEC.loader.exec_module(web)


class Phase2PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.stage = Path(self.temporary.name)
        (self.stage / "tables").mkdir()
        self.columns = ["policy", "year", "session", "side", "mean_difference", "rate", "unknown", "partial_year"]
        self.rows = [
            dict(zip(self.columns, ["other", "All years", "All sessions", "combined", "99", ".5", "0", "False"])),
            dict(zip(self.columns, ["wanted", "All years", "All sessions", "combined", "0", ".125", "1", "False"])),
            dict(zip(self.columns, ["wanted", "2026", "Asia", "upper-first", "", "", "2", "True"])),
        ]
        self.source = self.stage / "tables" / "paired.csv"
        self.source.write_bytes(web.csv_bytes(self.columns, self.rows))
        self.inputs = web.SavedInputs(self.stage)
        self.draft = web.PublicationDraft(self.inputs, "synthetic_run", web.ReportSpec("synthetic", "summary", "Synthetic saved cells"))
        self.artifact = self.draft.copy_table("tables/paired.csv", "tables/selected-pairs.csv", {"policy": "wanted"})

    def table(self):
        return self.draft.table(
            "paired", "Exact saved comparison", self.artifact,
            [{"key": key, "label": key} for key in self.columns],
            [{"key": "year", "label": "Original breakout year", "defaultValue": "All years"}],
        )

    def test_projection_preserves_zero_unknown_null_boolean_and_original_rows(self):
        before = self.source.read_bytes()
        table = self.table()
        self.assertEqual(table["rows"][0]["mean_difference"], 0)
        self.assertEqual(table["rows"][0]["rate"], .125)
        self.assertIs(table["rows"][0]["partial_year"], False)
        self.assertIsNone(table["rows"][1]["mean_difference"])
        self.assertIsNone(table["rows"][1]["rate"])
        self.assertEqual(table["rows"][1]["unknown"], 2)
        self.assertEqual(table["rows"][1]["year"], "2026")
        source = self.draft.source_map()["source_artifacts"][0]
        self.assertEqual(source["selected_source_rows"], [1, 2])
        self.assertEqual(source["original_source_sha256"], web.sha_bytes(before))
        bindings = self.draft.source_map()["bindings"]
        self.assertEqual(len(bindings), 16)
        self.assertEqual({binding["original_source_row"] for binding in bindings}, {1, 2})
        null_binding = next(binding for binding in bindings if binding["row_index"] == 1 and binding["key"] == "rate")
        self.assertEqual(null_binding["value_type"], "null")
        self.assertEqual(null_binding["source_row"], 1)
        self.assertEqual(null_binding["original_source_row"], 2)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertFalse((self.stage / "publications").exists())

    def test_selected_csv_retains_exact_strings_order_and_blank_cells(self):
        columns = ["policy", "rate", "mean_difference"]
        declaration = self.draft.download("paired-selection", "Selected paired rows", self.artifact, columns, population="Synthetic rows", units="Saved ratios and USD", scope="Synthetic selected policy")
        downloaded = list(csv.DictReader(io.StringIO(self.draft.files[declaration["path"]].decode())))
        self.assertEqual(downloaded, [{key: row[key] for key in columns} for row in self.rows[1:]])
        self.assertEqual(declaration["rowCount"], 2)
        self.assertEqual(declaration["source"]["sha256"], self.draft.sources[self.artifact]["sha256"])
        self.assertEqual(self.draft.downloads[0]["original_source_rows"], [1, 2])
        self.assertEqual(declaration["sha256"], web.sha_bytes(self.draft.files[declaration["path"]]))

    def test_json_pointer_metrics_preserve_unavailable_and_false_as_distinct_values(self):
        (self.stage / "selection.json").write_bytes(web.json_bytes({"choice": None, "qualified": False, "count": 0}))
        self.draft.copy_json("selection.json")
        self.assertIsNone(self.draft.json_metric("selection", 0, "selection.json", "/choice", "Choice")["value"])
        self.assertIs(self.draft.json_metric("selection", 1, "selection.json", "/qualified", "Qualified")["value"], False)
        self.assertEqual(self.draft.json_metric("selection", 2, "selection.json", "/count", "Count")["value"], 0)
        self.assertEqual([item["value_type"] for item in self.draft.bindings], ["null", "boolean", "number"])
        self.assertEqual(self.draft.bindings[1]["original_source_pointer"], "/qualified")

    def test_selectors_defaults_and_display_columns_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "original saved column"):
            self.inputs.select("tables/paired.csv", {"not_saved": "wanted"})
        with self.assertRaisesRegex(ValueError, "exact saved value"):
            self.draft.table("bad", "Bad default", self.artifact, [{"key": "year", "label": "Year"}], [{"key": "year", "label": "Year", "defaultValue": "2099"}])
        with self.assertRaisesRegex(ValueError, "copied saved cells"):
            self.draft.table("bad", "Invented metric", self.artifact, [{"key": "recomputed", "label": "Wrong"}])
        self.assertEqual(self.draft.bindings, [])

    def test_raw_evidence_boundaries_reject_traversal_symlinks_and_nonfinite_cells(self):
        for path in ("../outside.csv", "/absolute.csv", "tables/../paired.csv", "tables//paired.csv"):
            with self.assertRaises(ValueError):
                self.inputs.read(path)
        (self.stage / "link").symlink_to(self.stage / "tables", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            self.inputs.read("link/paired.csv")
        for column, value in (("mean_difference", "NaN"), ("unknown", "Infinity"), ("unknown", "1.5"), ("unknown", "9007199254740993"), ("partial_year", "1")):
            with self.assertRaises(ValueError):
                web.saved_cell(column, value)

    def test_report_plan_is_bounded_unique_and_imports_no_other_producer(self):
        reports = web.report_specs()
        self.assertEqual(len(reports), 23)
        self.assertEqual(len({report.publication_id for report in reports}), 23)
        self.assertTrue(all(len(report.publication_id) <= 80 for report in reports))
        self.assertEqual(len({report.group for report in reports}) + 1, 8, "The existing Phase 1 singleton is the eighth group.")
        imports = []
        for node in ast.walk(ast.parse(SCRIPT.read_text())):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module)
        self.assertFalse(any("engine" in name or "publish_web" in name or "sahadeva" in name or "bhishma" in name for name in imports))

    def test_bar_plot_encodes_saved_zero_and_does_not_draw_null_as_zero(self):
        svg, mapping = web.saved_bars_svg(self.draft, self.artifact, [0,1], ["year"], "mean_difference",
                                          "Synthetic", "Exact cells", unit="USD")
        root = ET.fromstring(svg)
        bars = [node for node in root.iter() if node.tag.endswith("rect") and "data-source-row" in node.attrib]
        self.assertEqual(len(bars),1)
        self.assertEqual(float(bars[0].attrib["height"]),0)
        self.assertEqual(mapping["plotted_values"][0]["values"]["mean_difference"],0)
        self.assertIsNone(mapping["plotted_values"][1]["values"]["mean_difference"])
        self.assertEqual(mapping["plotted_values"][1]["original_source_row"],2)
        self.assertEqual(mapping["plot_encoding"]["kind"],"bars-v1")
        self.assertIn(b"Not available",svg)

    def test_json_table_and_guide_maps_preserve_scalar_types_and_render_boundaries(self):
        (self.stage / "selection.json").write_bytes(web.json_bytes([{"policy":"synthetic","count":0,"qualified":False,"result":None}]))
        self.draft.copy_json("selection.json")
        columns=[{"key":key,"label":key} for key in ["policy","count","qualified","result"]]
        section=self.draft.json_table("selection","Receipt","selection.json",
                                     [{key:f"/0/{key}" for key in ["policy","count","qualified","result"]}],columns)
        self.assertEqual(section["rows"],[{"policy":"synthetic","count":0,"qualified":False,"result":None}])
        self.assertEqual([binding["value_type"] for binding in self.draft.bindings],["string","number","boolean","null"])
        for kind,q in [("reclaim",0),("reclaim",.25),("reclaim",.5),("reclaim",.75),("passive",None),("protected",None),("financial",None)]:
            root=ET.fromstring(web.illustrative_svg(kind,q))
            self.assertTrue(root.attrib["viewBox"].startswith("0 0 1240 "))
        self.draft.figure("guide","Synthetic guide","guide",web.illustrative_svg("financial"),{
            "kind":"illustrative","source_artifact":"selection.json","source_sha256":self.draft.sources["selection.json"]["sha256"],
        },alt="Synthetic",caption="Illustrative only.")
        with self.assertRaisesRegex(ValueError,"complete rendered image hashes"):
            self.draft.source_map()

    def test_generation_rejects_completed_or_unowned_locations(self):
        with self.assertRaisesRegex(ValueError,"owning work-stage"):
            web.owning_stage(self.stage)


if __name__ == "__main__":
    unittest.main()
