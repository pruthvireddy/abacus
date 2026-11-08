"""Synthetic structure/staging and real-kernel tests for the themed notebook."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "notebook_v2.py"
SPEC = importlib.util.spec_from_file_location("study30_v2_tests", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII="


def fixture(*, executed=True, figures=False):
    cells = []
    themes = []
    count = 0
    for theme_id, measures in MODULE.THEMES.items():
        ids = []
        for measure in sorted(measures):
            identity = "question-" + measure.lower()
            ids.append(identity)
            kind = "line" if figures and measure == "S02" else "table"
            for role in MODULE.ROLES:
                meta = {"theme_id": theme_id, "insight_id": identity, "kind": kind,
                        "role": role, "publish": role != "analysis"}
                if role == "heading":
                    meta["primary_measure_id"] = measure
                code = role in ("analysis", "findings", "evidence")
                source = {"heading": "### Synthetic " + measure,
                          "description": "Observe the **synthetic** count.\n\nRetain missing and zero values.",
                          "analysis": "value = 1\n", "findings": "# generate a synthetic finding\n",
                          "evidence": "# generate synthetic evidence\n"}[role]
                cell = {"id": identity + "-" + role, "cell_type": "code" if code else "markdown",
                        "metadata": {"abacus": meta}, "source": source}
                if code:
                    count += 1
                    cell.update(execution_count=count if executed else None, outputs=[])
                    data = None
                    if role == "findings":
                        data = {"text/markdown": "**Findings summary.** Synthetic count **1**."}
                    elif role == "evidence":
                        descriptor = {"kind": "table", "columns": [{"key": "label", "label": "Label", "format": "text"},
                                                                 {"key": "count", "label": "Count", "format": "integer"},
                                                                 {"key": "observed", "label": "Observed", "format": "text"}],
                                      "rows": [{"label": "Observed", "count": 1, "observed": True}, {"label": "Missing", "count": None, "observed": None},
                                               {"label": "False", "count": None, "observed": False}, {"label": "Zero", "count": 0, "observed": True}],
                                      "notes": ["Synthetic observations only."], "source": {"measure_id": measure}}
                        data = {MODULE.MIME: descriptor, "text/html": "<table><tr><td>1</td></tr></table>"}
                        if kind != "table":
                            data = {MODULE.MIME: {"kind": "figure", "alt": "Synthetic one-pixel fixture", "caption": "Synthetic fixture only.", "source": {"measure_id": measure}}, "image/png": PNG}
                    if executed and data:
                        cell["outputs"] = [{"output_type": "display_data", "data": data, "metadata": {}}]
                cells.append(cell)
        themes.append({"id": theme_id, "title": theme_id.replace("-", " ").title(),
                       "question": "Synthetic " + theme_id + " questions.", "insight_ids": ids})
    return {"nbformat": 4, "nbformat_minor": 5, "metadata": {"abacus": {
        "schema_version": MODULE.SCHEMA, "study_id": MODULE.STUDY, "version": "V2",
        "themes": themes, "insight_order": [i for t in themes for i in t["insight_ids"]],
        "source_run_id": "synthetic-upstream", "input_lock": "notebook-v2.inputs.lock.json",
        "publication_notes": ["Synthetic evidence only."]}}, "cells": cells}


class NotebookV2Tests(unittest.TestCase):
    def test_six_themes_cover_every_primary_measure_with_real_rich_outputs(self):
        result = MODULE.validate_notebook(fixture(figures=True), require_outputs=True)
        self.assertEqual(result["insights"], 20)
        self.assertEqual(result["primary_measures"], 20)
        self.assertEqual(len(result["themes"]), 6)

    def test_duplicate_membership_wrong_primary_home_and_missing_measure_refused(self):
        for mutation in ("duplicate", "wrong-home", "missing", "reordered"):
            book = fixture()
            if mutation == "duplicate":
                book["metadata"]["abacus"]["themes"][1]["insight_ids"].append(book["metadata"]["abacus"]["themes"][0]["insight_ids"][0])
            elif mutation == "wrong-home":
                book["cells"][0]["metadata"]["abacus"]["primary_measure_id"] = "S01"
            elif mutation == "missing":
                book["cells"][0]["metadata"]["abacus"].pop("primary_measure_id")
            else:
                book["cells"][0], book["cells"][1] = book["cells"][1], book["cells"][0]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                MODULE.validate_notebook(book)

    def test_missing_structured_table_corrupt_png_and_nonfinite_values_refused(self):
        for mutation in ("mime", "nan", "extra-cell", "png", "multiple-outputs", "numeric-false", "fractional-integer"):
            book = fixture(figures=True)
            tables = [c for c in book["cells"] if c["metadata"]["abacus"]["role"] == "evidence" and c["metadata"]["abacus"]["kind"] == "table"]
            data = tables[0]["outputs"][0]["data"]
            if mutation == "mime":
                data.pop(MODULE.MIME)
            elif mutation == "nan":
                data[MODULE.MIME]["rows"][0]["count"] = float("nan")
            elif mutation == "extra-cell":
                data[MODULE.MIME]["rows"][0]["undeclared"] = 9
            elif mutation == "multiple-outputs":
                tables[0]["outputs"].append(copy.deepcopy(tables[0]["outputs"][0]))
            elif mutation == "numeric-false":
                data[MODULE.MIME]["rows"][0]["count"] = False
            elif mutation == "fractional-integer":
                data[MODULE.MIME]["rows"][0]["count"] = 1.2
            else:
                chart = next(c for c in book["cells"] if c["metadata"]["abacus"]["role"] == "evidence" and c["metadata"]["abacus"]["kind"] == "line")
                chart["outputs"][0]["data"]["image/png"] = "not a PNG"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                MODULE.validate_notebook(book, require_outputs=True)

    def test_visible_code_explicit_selection_and_error_free_execution_required(self):
        for mutation in ("hidden", "publish-analysis", "packed", "unexecuted", "error"):
            book = fixture()
            code = book["cells"][2]
            if mutation == "hidden":
                code["metadata"]["jupyter"] = {"source_hidden": True}
            elif mutation == "publish-analysis":
                code["metadata"]["abacus"]["publish"] = True
            elif mutation == "packed":
                code["source"] = "payload='" + "A" * 210 + "'"
            elif mutation == "unexecuted":
                code["execution_count"] = None
            else:
                code["outputs"] = [{"output_type": "error", "ename": "ValueError", "evalue": "synthetic", "traceback": []}]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                MODULE.validate_notebook(book, require_outputs=True)

    def test_signature_ignores_execution_cache_but_detects_authored_edits(self):
        book = fixture()
        first = MODULE.authoring_signature(book)
        book["cells"][2]["outputs"] = []
        book["cells"][2]["metadata"]["execution"] = {"iopub.status.busy": "synthetic"}
        self.assertEqual(first, MODULE.authoring_signature(book))
        book["cells"][1]["source"] += " Changed claim."
        self.assertNotEqual(first, MODULE.authoring_signature(book))

    def test_execution_refuses_existing_and_sealed_outputs_before_kernel_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "source.ipynb"
            source.write_text(json.dumps(fixture(executed=False)))
            output = root / "work" / MODULE.STUDY / "stage" / "executed.ipynb"
            output.parent.mkdir(parents=True)
            output.write_text("retained")
            with patch.object(MODULE, "ROOT", root), patch.object(MODULE, "_load_execution_tools", side_effect=AssertionError("Kernel import must not occur")):
                with self.assertRaises(FileExistsError):
                    MODULE.execute_notebook(source, output_path=output)
                with self.assertRaises(ValueError):
                    MODULE.execute_notebook(source, output_path=root / "runs" / "executed.ipynb")
            self.assertEqual(output.read_text(), "retained")

    @unittest.skipUnless(importlib.util.find_spec("nbclient") and importlib.util.find_spec("ipykernel"), "Locked notebooks environment required")
    def test_actual_fresh_kernel_signature_and_receipt(self):
        book = fixture(executed=False)
        for cell in book["cells"]:
            role = cell["metadata"]["abacus"]["role"]
            if role == "findings":
                cell["source"] = "from IPython.display import display,Markdown\ndisplay(Markdown('**Findings summary.** Synthetic count **1**.'))\n"
            elif role == "evidence":
                cell["source"] = "display({" + repr(MODULE.MIME) + ":{'kind':'table','columns':[{'key':'count','label':'Count','format':'integer'}],'rows':[{'count':value}],'notes':['Synthetic only.']},'text/html':'<table><tr><td>1</td></tr></table>'},raw=True)\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "source.ipynb"
            source.write_text(json.dumps(book))
            pinned = root / "pinned.txt"
            pinned.write_text("synthetic input")
            output = root / "work" / MODULE.STUDY / "fresh" / "executed.ipynb"
            with patch.object(MODULE, "ROOT", root):
                record = MODULE.execute_notebook(source, output_path=output, input_paths=[pinned], python_executable=sys.executable, working_directory=root, timeout=30)
            self.assertEqual(record["result"], "passed")
            self.assertEqual(record["source_authoring_signature"], record["executed_authoring_signature"])
            self.assertTrue(record["source_and_inputs_unchanged"])
            MODULE.validate_notebook(json.loads(output.read_bytes()), require_outputs=True)


if __name__ == "__main__":
    unittest.main()
