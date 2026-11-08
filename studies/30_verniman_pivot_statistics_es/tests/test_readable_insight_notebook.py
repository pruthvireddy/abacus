"""Checks for normal notebook cells and portable companion presentation files."""

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "readable_insight_notebook.py"
SPEC = importlib.util.spec_from_file_location("study30_readable_insight_notebook", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture():
    reports = {"pivot": {
        "id": "synthetic-saved-insights", "title": "Saved crossing questions", "summary": "Synthetic fixture only.",
        "source": {"producer": "sahadeva", "runId": "synthetic-run"},
        "sections": [
            {"id": "scope", "kind": "text", "title": "Scope", "body": "Explicit synthetic cohort, not market evidence."},
            {"id": "s01", "kind": "table", "title": "What do these saved rows contain?",
             "description": "Select saved rows, preserving scalar types.", "finding": "The synthetic baseline contains an observed zero.",
             "columns": [{"key": "cohort", "label": "Cohort"}, {"key": "value", "label": "Mean", "precision": 3},
                         {"key": "share", "label": "Share", "format": "percent", "precision": 1},
                         {"key": "days", "label": "Days", "precision": 0}, {"key": "flag", "label": "State"},
                         {"key": "missing", "label": "Missing"}],
             "rowFilters": [{"key": "cohort", "label": "Cohort", "defaultValue": "whole sample"}],
             "notes": ["Null stays unavailable; false and zero remain observed values."],
             "rows": [{"cohort": "whole sample", "value": 0, "share": 0.125, "days": 1234, "flag": False, "missing": None},
                      {"cohort": "other <cohort>", "value": -0.25, "share": None, "days": 2, "flag": True, "missing": "<script>"}]},
            {"id": "s02", "kind": "figure", "title": "What does the selected saved chart show?",
             "description": "Display saved raster bytes.", "finding": "This fixture tests presentation only.",
             "path": "figures/crossings.png", "alt": "An explicitly synthetic chart.", "caption": "Exact saved bytes; no new estimates."},
            {"id": "limits", "kind": "text", "title": "Limits", "body": "No market outcomes or profitability assessed."}
        ]}}
    return reports, {"pivot": {"figures/crossings.png": b"synthetic-raster-bytes"}}


def write_folder(folder, reports, assets):
    folder.mkdir(parents=True)
    payload = MODULE.saved_payload(reports, assets)
    (folder / "insight_view.py").write_text(MODULE.view_helper_source(), encoding="utf-8")
    (folder / "saved-reports.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for key, images in payload["assets"].items():
        for path, relative in images.items():
            destination = folder / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(assets[key][path])


class ReadableInsightNotebookTests(unittest.TestCase):
    def test_small_visible_code_cells_without_embedded_payload(self):
        reports, assets = fixture()
        notebook = MODULE.build_readable_notebook(reports, assets, source_run_id="synthetic-run")
        self.assertEqual(notebook, MODULE.build_readable_notebook(reports, assets, source_run_id="synthetic-run"))
        code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        self.assertEqual(len(code), 3)
        self.assertLess(max(len("".join(cell["source"])) for cell in code), 1500)
        for cell in code:
            source = "".join(cell["source"])
            self.assertNotIn("base64", source)
            self.assertNotIn("zlib", source)
            self.assertNotIn("synthetic-raster-bytes", source)
            self.assertFalse(cell["metadata"].get("collapsed", False))
            self.assertFalse(cell["metadata"].get("jupyter", {}).get("source_hidden", False))
        self.assertEqual("".join(code[1]["source"]), "show_insight('pivot', 's01')\n")
        narratives = [cell for cell in notebook["cells"] if cell.get("metadata", {}).get("abacus", {}).get("role") == "narrative"]
        self.assertEqual(len(narratives), 2)
        self.assertTrue(all("**Findings summary.**" in "".join(cell["source"]) for cell in narratives))

    def test_portable_folder_replays_in_fresh_isolated_python_process(self):
        reports, assets = fixture()
        notebook = MODULE.build_readable_notebook(reports, assets, source_run_id="synthetic-run")
        before = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original"
            write_folder(original, reports, assets)
            moved = Path(directory) / "portable-copy"
            shutil.copytree(original, moved)
            self.assertEqual(MODULE.replay_readable_notebook(notebook, moved), 3)
            (moved / "saved.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
            script = ("import importlib.util,json,sys; "
                      "s=importlib.util.spec_from_file_location('saved',sys.argv[1]); "
                      "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                      "print(m.replay_readable_notebook(json.load(open(sys.argv[2])),sys.argv[3]))")
            result = subprocess.run([sys.executable, "-I", "-c", script, str(MODULE_PATH), str(moved / "saved.ipynb"), str(moved)],
                                    cwd=directory, text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "3")
        self.assertEqual(Path.cwd(), before)

    def test_exact_images_saved_scalar_meanings_and_no_encoded_assets_in_payload(self):
        reports, assets = fixture()
        notebook = MODULE.build_readable_notebook(reports, assets, source_run_id="synthetic-run")
        payload = MODULE.saved_payload(reports, assets)
        self.assertEqual(payload["assets"]["pivot"]["figures/crossings.png"], "assets/pivot/figures/crossings.png")
        self.assertNotIn("c3ludGhldGlj", json.dumps(payload))
        table = next(cell for cell in notebook["cells"] if cell["id"] == "pivot-s01-evidence")
        markup = table["outputs"][0]["data"]["text/html"]
        for value in ["0.000", "12.5%", "1,234", ">false<", "Not available"]:
            self.assertIn(value, markup)
        self.assertNotIn("other &lt;cohort&gt;", markup)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "notebook"
            write_folder(folder, reports, assets)
            spec = importlib.util.spec_from_file_location("saved_view_fixture", folder / "insight_view.py")
            helper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(helper)
            alternate = helper.show_insight("pivot", "s01", {"cohort": "other <cohort>"}).data["text/html"]
            self.assertIn("&lt;script&gt;", alternate)
            self.assertNotIn("<script>", alternate)
            self.assertEqual(helper.show_insight("pivot", "s02").data,
                             next(cell for cell in notebook["cells"] if cell["id"] == "pivot-s02-evidence")["outputs"][0]["data"])

    def test_explicit_workspace_fallback_and_failures_restore_cwd(self):
        reports, assets = fixture()
        notebook = MODULE.build_readable_notebook(reports, assets, source_run_id="synthetic-run")
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            folder = workspace / "work/30_verniman_pivot_statistics_es/notebook"
            write_folder(folder, reports, assets)
            self.assertEqual(MODULE.replay_readable_notebook(notebook, workspace), 3)
            changed = copy.deepcopy(notebook)
            next(cell for cell in changed["cells"] if cell["id"] == "pivot-s01-evidence")["outputs"][0]["data"]["text/plain"] = "changed"
            with self.assertRaisesRegex(ValueError, "differs"):
                MODULE.replay_readable_notebook(changed, folder)
        self.assertEqual(Path.cwd(), previous)

    def test_invalid_source_identity_and_asset_path_refused(self):
        reports, assets = fixture()
        with self.assertRaisesRegex(ValueError, "identity"):
            MODULE.build_readable_notebook(reports, assets, source_run_id="another-run")
        with self.assertRaisesRegex(ValueError, "figure bytes"):
            MODULE.saved_payload(reports, {})
        reports["pivot"]["sections"][2]["path"] = "figures/../../outside.png"
        with self.assertRaisesRegex(ValueError, "inside figures"):
            MODULE.saved_payload(reports, assets)


if __name__ == "__main__":
    unittest.main()
