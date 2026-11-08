"""Portable saved-evidence notebook checks; no research/data execution."""

import ast
import base64
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "insight_notebook.py"
SPEC = importlib.util.spec_from_file_location("study30_insight_notebook", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def report():
    return {
        "id": "synthetic-saved-insights", "title": "Saved crossing questions", "summary": "Synthetic fixture only.",
        "source": {"producer": "sahadeva", "runId": "synthetic-run"},
        "sections": [
            {"id": "scope", "kind": "text", "title": "Scope", "body": "Explicit synthetic cohort, not market evidence."},
            {"id": "s01", "kind": "table", "title": "Does the saved default retain scalar meanings?",
             "description": "Select saved rows, preserving their types.", "finding": "The synthetic baseline contains an observed zero.",
             "columns": [{"key": "cohort", "label": "Cohort"}, {"key": "value", "label": "Mean", "precision": 3},
                         {"key": "share", "label": "Share", "format": "percent", "precision": 1},
                         {"key": "days", "label": "Days", "precision": 0}, {"key": "flag", "label": "State"},
                         {"key": "missing", "label": "Missing"}],
             "rowFilters": [{"key": "cohort", "label": "Cohort", "defaultValue": "whole sample"}],
             "notes": ["Null stays unavailable; false and zero remain observed values."],
             "rows": [{"cohort": "whole sample", "value": 0, "share": 0.125, "days": 1234, "flag": False, "missing": None},
                      {"cohort": "other <cohort>", "value": -0.25, "share": None, "days": 2, "flag": True, "missing": "<script>"}]},
            {"id": "s02", "kind": "figure", "title": "What does the selected saved chart show?",
             "description": "Display the saved raster bytes.", "finding": "This fixture tests presentation only.",
             "path": "figures/crossings.png", "alt": "An explicitly synthetic chart.", "caption": "Exact saved bytes; no new estimates."},
            {"id": "limits", "kind": "text", "title": "Limits", "body": "No market outcomes or profitability assessed."}
        ]}


def build(selected=None):
    return MODULE.build_notebook({"pivot": selected or report()}, {"pivot": {"figures/crossings.png": b"synthetic-raster-bytes"}},
                                 source_run_id="synthetic-run")


def runtime(notebook):
    namespace = {"__name__": "__main__"}
    setup = next(cell for cell in notebook["cells"] if cell["id"] == "saved-presentation-setup")
    exec(compile(ast.parse("".join(setup["source"])), "<setup>", "exec"), namespace)
    return namespace


class InsightNotebookTests(unittest.TestCase):
    def test_portable_fresh_process_replay_and_stable_metadata(self):
        notebook = build()
        self.assertEqual(notebook, build())
        self.assertEqual(MODULE.replay_notebook(notebook), 3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "saved.ipynb"
            path.write_text(json.dumps(notebook), encoding="utf-8")
            script = ("import importlib.util,json,sys; "
                      "s=importlib.util.spec_from_file_location('saved',sys.argv[1]); "
                      "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                      "print(m.replay_notebook(json.load(open(sys.argv[2]))))")
            result = subprocess.run([sys.executable, "-I", "-c", script, str(MODULE_PATH), str(path)],
                                    cwd=directory, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "3")
        blocks = [cell for cell in notebook["cells"] if cell.get("metadata", {}).get("abacus", {}).get("role") == "narrative"]
        self.assertEqual(len(blocks), 2)
        for block in blocks:
            self.assertIn("Findings summary.", "".join(block["source"]))
        self.assertTrue(all(cell["metadata"]["jupyter"]["source_hidden"] for cell in notebook["cells"] if cell["cell_type"] == "code"))

    def test_default_rows_formats_null_false_zero_and_escaped_content(self):
        notebook = build()
        view = runtime(notebook)["show_insight"]("pivot", "s01")
        markup = view._repr_mimebundle_()["text/html"]
        self.assertIn("0.000", markup)
        self.assertIn("12.5%", markup)
        self.assertIn("1,234", markup)
        self.assertIn(">false<", markup)
        self.assertIn("Not available", markup)
        self.assertNotIn("other &lt;cohort&gt;", markup)
        alternate = runtime(notebook)["show_insight"]("pivot", "s01", {"cohort": "other <cohort>"}).data["text/html"]
        self.assertIn("other &lt;cohort&gt;", alternate)
        self.assertIn("&lt;script&gt;", alternate)
        self.assertNotIn("<script>", alternate)

    def test_typed_filters_distinguish_false_zero_null_and_string(self):
        selected = report()
        table = selected["sections"][1]
        table["rows"] = [{"cohort": value, "value": index} for index, value in enumerate([False, 0, None, "0"])]
        table["rowFilters"][0]["defaultValue"] = False
        show = runtime(build(selected))["show_insight"]
        for index, value in enumerate([False, 0, None, "0"]):
            plain = show("pivot", "s01", {"cohort": value}).data["text/plain"]
            self.assertIn("Showing 1 of 1 matching saved rows", plain)
            self.assertIn(f"{index:.3f}", plain)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            show("pivot", "s01", {"unsupported": 0})
        with self.assertRaisesRegex(ValueError, "Unavailable"):
            show("pivot", "s01", {"cohort": "missing"})

    def test_row_cap_and_exact_figure_bytes(self):
        selected = report()
        selected["sections"][1]["rows"] = [{"cohort": "whole sample", "value": index} for index in range(101)]
        namespace = runtime(build(selected))
        plain = namespace["show_insight"]("pivot", "s01").data["text/plain"]
        self.assertIn("Showing 100 of 101 matching saved rows", plain)
        self.assertNotIn("100.000", plain)
        figure = namespace["show_insight"]("pivot", "s02").data
        self.assertEqual(base64.b64decode(figure["image/png"]), b"synthetic-raster-bytes")
        self.assertIn("Exact saved bytes", figure["text/html"])

    def test_changed_cached_outputs_or_embedded_payload_refused(self):
        notebook = build()
        changed = copy.deepcopy(notebook)
        evidence = next(cell for cell in changed["cells"] if cell["id"] == "pivot-s01-evidence")
        evidence["outputs"][0]["data"]["text/plain"] = "changed value"
        with self.assertRaisesRegex(ValueError, "differs"):
            MODULE.replay_notebook(changed)
        changed = copy.deepcopy(notebook)
        setup = next(cell for cell in changed["cells"] if cell["id"] == "saved-presentation-setup")
        digest = changed["metadata"]["abacus"]["embedded_payload_sha256"]
        setup["source"] = [line.replace(digest, "0" * 64) for line in setup["source"]]
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            MODULE.replay_notebook(changed)
        changed = copy.deepcopy(notebook)
        changed["cells"][-1]["id"] = changed["cells"][0]["id"]
        with self.assertRaisesRegex(ValueError, "unique"):
            MODULE.replay_notebook(changed)

    def test_missing_identity_narrative_or_image_refused(self):
        selected = report()
        selected["source"]["runId"] = "another-run"
        with self.assertRaisesRegex(ValueError, "identity"):
            build(selected)
        selected = report()
        selected["sections"][1]["finding"] = " "
        with self.assertRaisesRegex(ValueError, "findings"):
            build(selected)
        with self.assertRaisesRegex(ValueError, "figure bytes"):
            MODULE.build_notebook({"pivot": report()}, {}, source_run_id="synthetic-run")


if __name__ == "__main__":
    unittest.main()
