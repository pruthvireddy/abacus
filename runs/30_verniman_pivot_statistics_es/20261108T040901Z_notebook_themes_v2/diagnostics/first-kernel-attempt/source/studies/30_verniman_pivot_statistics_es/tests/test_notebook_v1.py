"""Structural and staging checks for the study-authored notebook execution tool."""

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "notebook_v1.py"
SPEC = importlib.util.spec_from_file_location("study30_notebook_v1", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture(*, executed=False):
    cells = [{"cell_type": "markdown", "id": "introduction", "metadata": {}, "source": "# Synthetic notebook fixture"}]
    execution = 0
    for kind in ("table", "line", "bar"):
        insight = "synthetic-" + kind
        for role in ("heading", "description", "analysis", "findings", "evidence"):
            code = role in {"analysis", "findings", "evidence"}
            cell = {"cell_type": "code" if code else "markdown", "id": insight + "-" + role,
                    "metadata": {"abacus": {"insight_id": insight, "kind": kind, "role": role}},
                    "source": "value = 1\n" if code else role.capitalize()}
            if code:
                execution += 1
                cell.update(execution_count=execution if executed else None, outputs=[])
                if executed and role != "analysis":
                    mime = "text/markdown" if role == "findings" else "text/html" if kind == "table" else "image/png"
                    cell["outputs"] = [{"output_type": "display_data", "data": {mime: "Synthetic fixture only"}, "metadata": {}}]
            cells.append(cell)
    return {"nbformat": 4, "nbformat_minor": 5, "metadata": {}, "cells": cells}


class NotebookV1Tests(unittest.TestCase):
    def test_three_visible_groups_and_executed_rich_outputs(self):
        result = MODULE.validate_notebook(fixture())
        self.assertEqual([group["kind"] for group in result["insights"]], ["table", "line", "bar"])
        self.assertEqual(result["code_cells"], 9)
        MODULE.validate_notebook(fixture(executed=True), require_outputs=True)
        markdown_findings = fixture(executed=True)
        cell = next(cell for cell in markdown_findings["cells"] if cell["id"] == "synthetic-table-findings")
        cell.update(cell_type="markdown", source="Reviewed synthetic finding")
        cell.pop("outputs")
        cell.pop("execution_count")
        MODULE.validate_notebook(markdown_findings, require_outputs=True)

    def test_missing_or_duplicate_role_and_wrong_evidence_kind_refused(self):
        for mutation in ("missing", "duplicate", "wrong-kind", "order"):
            notebook = fixture()
            if mutation == "missing":
                notebook["cells"] = [cell for cell in notebook["cells"] if cell["id"] != "synthetic-table-findings"]
            elif mutation == "duplicate":
                extra = copy.deepcopy(notebook["cells"][1])
                extra["id"] += "-duplicate"
                notebook["cells"].insert(2, extra)
            elif mutation == "wrong-kind":
                for cell in notebook["cells"]:
                    if cell.get("metadata", {}).get("abacus", {}).get("insight_id") == "synthetic-line":
                        cell["metadata"]["abacus"]["kind"] = "table"
            else:
                notebook["cells"][2], notebook["cells"][3] = notebook["cells"][3], notebook["cells"][2]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                MODULE.validate_notebook(notebook)

    def test_packed_oversized_or_hidden_cell_sources_refused(self):
        for mutation in ("packed", "long", "hidden", "tagged"):
            notebook = fixture()
            cell = next(cell for cell in notebook["cells"] if cell["id"] == "synthetic-table-analysis")
            if mutation == "packed":
                cell["source"] = "payload = '" + "A" * 220 + "'"
            elif mutation == "long":
                cell["source"] = "# comment\n" * 700
            elif mutation == "hidden":
                cell["metadata"]["jupyter"] = {"source_hidden": True}
            else:
                cell["metadata"]["tags"] = ["hide-input"]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                MODULE.validate_notebook(notebook)

    def test_unexecuted_error_or_missing_evidence_outputs_refused(self):
        with self.assertRaisesRegex(ValueError, "not executed"):
            MODULE.validate_notebook(fixture(), require_outputs=True)
        notebook = fixture(executed=True)
        evidence = next(cell for cell in notebook["cells"] if cell["id"] == "synthetic-line-evidence")
        evidence["outputs"] = [{"output_type": "error", "ename": "ValueError", "evalue": "synthetic error", "traceback": []}]
        with self.assertRaisesRegex(ValueError, "error output"):
            MODULE.validate_notebook(notebook, require_outputs=True)
        evidence["outputs"] = [{"output_type": "stream", "name": "stdout", "text": "This is not a chart"}]
        with self.assertRaisesRegex(ValueError, "executed evidence"):
            MODULE.validate_notebook(notebook, require_outputs=True)

    def test_execution_refuses_sealed_or_existing_destinations_before_kernel_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "studies" / MODULE.STUDY / "source.ipynb"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps(fixture()), encoding="utf-8")
            staged = root / "work" / MODULE.STUDY / "synthetic-stage" / "executed.ipynb"
            staged.parent.mkdir(parents=True)
            staged.write_text("retained", encoding="utf-8")
            with patch.object(MODULE, "ROOT", root), patch.object(MODULE, "_load_execution_tools", side_effect=AssertionError("Kernel import must not occur")):
                with self.assertRaises(FileExistsError):
                    MODULE.execute_notebook(source, output_path=staged)
                with self.assertRaisesRegex(ValueError, "staged under"):
                    MODULE.execute_notebook(source, output_path=root / "runs" / MODULE.STUDY / "sealed" / "executed.ipynb")
            self.assertEqual(staged.read_text(), "retained")
            self.assertEqual(json.loads(source.read_text()), fixture())

    @unittest.skipUnless(importlib.util.find_spec("nbclient") and importlib.util.find_spec("ipykernel"), "Notebook execution environment required")
    def test_actual_fresh_ipython_kernel_and_receipt(self):
        notebook = fixture()
        setup = {"cell_type": "code", "id": "setup", "metadata": {"abacus": {"role": "setup"}},
                 "source": "from IPython.display import display, HTML, SVG, Markdown\n", "outputs": [], "execution_count": None}
        notebook["cells"].insert(1, setup)
        for cell in notebook["cells"]:
            meta = cell.get("metadata", {}).get("abacus", {})
            if meta.get("role") == "findings":
                cell["source"] = 'display(Markdown(f"Synthetic value: {value}"))\n'
            elif meta.get("role") == "evidence":
                cell["source"] = ('display(HTML("<table><tr><td>1</td></tr></table>"))\n' if meta["kind"] == "table" else
                                  'display(SVG(\'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20"/></svg>\'))\n')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "studies" / MODULE.STUDY / "source.ipynb"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps(notebook), encoding="utf-8")
            input_path = source.parent / "input.txt"
            input_path.write_text("synthetic pinned input", encoding="utf-8")
            output = root / "work" / MODULE.STUDY / "fresh-kernel" / "executed.ipynb"
            original = source.read_bytes()
            with patch.object(MODULE, "ROOT", root):
                record = MODULE.execute_notebook(source, output_path=output, python_executable=sys.executable,
                                                 input_paths=[input_path], timeout=30)
            self.assertEqual(record["result"], "passed")
            self.assertTrue(record["source_and_inputs_unchanged"])
            self.assertEqual(record["kernel"]["argv"][0], str(Path(sys.executable).absolute()))
            self.assertEqual(record["executed_validation"]["code_cells"], 10)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(json.loads(output.with_suffix(".execution.json").read_text())["result"], "passed")
            MODULE.validate_notebook(json.loads(output.read_text()), require_outputs=True)


if __name__ == "__main__":
    unittest.main()
