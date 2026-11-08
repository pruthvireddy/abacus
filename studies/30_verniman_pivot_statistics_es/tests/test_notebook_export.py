"""Notebook transfer guards use synthetic cached outputs, never retained market data."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

OWNER = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("study30_notebook_export_tests", OWNER / "publish_notebook.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
FIXTURE_SPEC = importlib.util.spec_from_file_location("study30_notebook_fixtures", Path(__file__).with_name("test_notebook_v2.py"))
FIXTURES = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(FIXTURES)


class ExportTests(unittest.TestCase):
    def setup_source(self, root):
        source = root / "work" / MODULE.STUDY / "stage" / "source" / "source.ipynb"
        source.parent.mkdir(parents=True)
        book = FIXTURES.fixture(figures=True)
        # This private setup must never become report or asset content.
        book["cells"].insert(0, {"id": "private-setup", "cell_type": "code", "metadata": {"abacus": {"publish": False, "role": "setup"}},
                                 "source": "private_secret = '/Users/private/research-secret'", "execution_count": 1,
                                 "outputs": [{"output_type": "stream", "name": "stdout", "text": "PRIVATE_TERMINAL_LOG"}]})
        source.write_bytes(MODULE.notebook.json_bytes(book))
        lock = root / "studies" / MODULE.STUDY / "notebook-v2.inputs.lock.json"
        lock.parent.mkdir(parents=True)
        environment = root / "uv.lock"
        environment.write_text("synthetic environment\n")
        artifact = source.parent / "input.txt"
        artifact.write_text("synthetic source input")
        lock.write_bytes(MODULE.notebook.json_bytes({"environment_lock_sha256": MODULE.notebook.digest(environment.read_bytes()),
            "artifacts": {"fixture": {"root": "workspace", "path": artifact.relative_to(root).as_posix(), "sha256": MODULE.notebook.digest(artifact.read_bytes())}}}))
        executed = source.parent.parent / "executed.ipynb"
        executed.write_bytes(source.read_bytes())
        receipt = source.parent.parent / "executed.execution.json"
        signature = MODULE.notebook.authoring_signature(book)
        record = {"schema_version": "abacus.study30.notebook-execution/v2", "result": "passed",
                  "source_and_inputs_unchanged": True, "source_authoring_signature": signature,
                  "executed_authoring_signature": signature,
                  "source_and_inputs": [MODULE.notebook.file_pin(p, root=root) for p in (source, lock, environment, artifact)],
                  "output": MODULE.notebook.file_pin(executed, root=root)}
        receipt.write_bytes(MODULE.notebook.json_bytes(record))
        (source.parent.parent / "saved-statistics-verification.json").write_bytes(MODULE.notebook.json_bytes({
            "result": "passed", "source_run_id": "synthetic-upstream", "publication_run_id": "synthetic-run",
            "checks": [{"insight_id": i, "passed": True} for i in book["metadata"]["abacus"]["insight_order"]],
            "insight_coverage": book["metadata"]["abacus"]["insight_order"]}))
        return source, executed, receipt

    def arguments(self, root, source, executed, receipt):
        return {"executed_path": executed, "receipt_path": receipt,
                "output_path": source.parent.parent / "publications", "run_id": "synthetic-run",
                "publication_suffix": "synthetic-v2", "published_at": "2026-11-08T00:00:00Z",
                "retained_root": f"runs/{MODULE.STUDY}/synthetic-run/publications",
                "retained_stage": f"runs/{MODULE.STUDY}/synthetic-run",
                "analysis_verification_path": source.parent.parent / "saved-statistics-verification.json"}

    def test_export_preserves_narrative_typed_cells_png_and_omits_private_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch.object(MODULE, "ROOT", root):
                source, executed, receipt = self.setup_source(root)
                args = self.arguments(root, source, executed, receipt)
                index = MODULE.export_notebook(source, **args)
                self.assertEqual(len(index["publications"]), 6)
                self.assertEqual(MODULE.check_export(args["output_path"])["result"], "passed")
                public_bytes = []
                found_figure = False
                for publication in index["publications"]:
                    folder = args["output_path"] / publication["publication_id"]
                    report_bytes = (folder / "publication.json").read_bytes()
                    public_bytes.append(report_bytes)
                    report = json.loads(report_bytes)
                    self.assertEqual(report["presentation"], "research-paper")
                    self.assertEqual(report["source"]["runId"], "synthetic-run")
                    for section in report["sections"]:
                        self.assertEqual(section["description"], "Observe the synthetic count.\n\nRetain missing and zero values.")
                        self.assertEqual(section["finding"], "Synthetic count 1.")
                        if section["kind"] == "table":
                            values = [r["count"] for r in section["rows"]]
                            self.assertIsNone(values[1])
                            self.assertIs(section["rows"][2]["observed"], False)
                            self.assertIs(type(values[3]), int)
                            self.assertEqual(section["columns"][1]["format"], "number")
                            self.assertEqual(section["columns"][1]["precision"], 0)
                        else:
                            found_figure = True
                            actual = (folder / section["path"]).read_bytes()
                            self.assertEqual(MODULE.base64.b64encode(actual).decode(), FIXTURES.PNG)
                    manifest = json.loads((folder / "publication-manifest.json").read_bytes())
                    self.assertTrue(all(p["path"].startswith(f"runs/{MODULE.STUDY}/synthetic-run/") for p in manifest["outputs"] + manifest["source_artifacts"]))
                combined = b"".join(public_bytes)
                self.assertTrue(found_figure)
                self.assertNotIn(b"private_secret", combined)
                self.assertNotIn(b"/Users/private", combined)
                self.assertNotIn(b"PRIVATE_TERMINAL_LOG", combined)

    def test_stale_source_changed_execution_and_changed_inputs_refused(self):
        for mutation in ("source", "executed", "input", "failed-receipt"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                with patch.object(MODULE, "ROOT", root):
                    source, executed, receipt = self.setup_source(root)
                    args = self.arguments(root, source, executed, receipt)
                    if mutation == "source":
                        book = json.loads(source.read_bytes())
                        book["cells"][2]["source"] += " Changed statement."
                        source.write_bytes(MODULE.notebook.json_bytes(book))
                    elif mutation == "executed":
                        executed.write_bytes(executed.read_bytes() + b" ")
                    elif mutation == "input":
                        (root / "uv.lock").write_text("changed environment")
                    else:
                        record = json.loads(receipt.read_bytes())
                        record["result"] = "failed"
                        receipt.write_bytes(MODULE.notebook.json_bytes(record))
                    with self.assertRaises(ValueError):
                        MODULE.export_notebook(source, **args)
                    self.assertFalse(args["output_path"].exists())

    def test_existing_sealed_symlink_and_mismatched_retained_destinations_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch.object(MODULE, "ROOT", root):
                source, executed, receipt = self.setup_source(root)
                args = self.arguments(root, source, executed, receipt)
                for destination in (root / "runs" / "retained", root / "arbitrary"):
                    with self.assertRaises(ValueError):
                        MODULE.export_notebook(source, **{**args, "output_path": destination})
                with self.assertRaises(ValueError):
                    MODULE.export_notebook(source, **{**args, "retained_root": "runs/other-study/wrong/publications"})
                args["output_path"].mkdir()
                with self.assertRaises(FileExistsError):
                    MODULE.export_notebook(source, **args)

    def test_export_inventory_detects_changed_saved_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch.object(MODULE, "ROOT", root):
                source, executed, receipt = self.setup_source(root)
                args = self.arguments(root, source, executed, receipt)
                index = MODULE.export_notebook(source, **args)
                report = args["output_path"] / index["publications"][0]["path"]
                report.write_bytes(report.read_bytes().replace(b'Synthetic count 1.', b'Changed finding.'))
                with self.assertRaisesRegex(ValueError, "Export bytes changed"):
                    MODULE.check_export(args["output_path"])

    def test_omitted_artifact_and_same_basename_wrong_active_lock_refused(self):
        for mutation in ("omitted-artifact", "wrong-lock-path"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                with patch.object(MODULE, "ROOT", root):
                    source, executed, receipt = self.setup_source(root)
                    args = self.arguments(root, source, executed, receipt)
                    record = json.loads(receipt.read_bytes())
                    if mutation == "omitted-artifact":
                        record["source_and_inputs"].pop()
                    else:
                        active = root / "studies" / MODULE.STUDY / "notebook-v2.inputs.lock.json"
                        replacement = source.parent / active.name
                        replacement.write_bytes(active.read_bytes())
                        record["source_and_inputs"][1] = MODULE.notebook.file_pin(replacement, root=root)
                    receipt.write_bytes(MODULE.notebook.json_bytes(record))
                    with self.assertRaisesRegex(ValueError, "missing locked artifact|exact active"):
                        MODULE.export_notebook(source, **args)
                    self.assertFalse(args["output_path"].exists())

    def test_private_paths_in_selected_table_and_figure_fields_refused(self):
        for field in ("row", "column", "note", "alt", "caption", "windows-row"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                with patch.object(MODULE, "ROOT", root):
                    source, executed, receipt = self.setup_source(root)
                    args = self.arguments(root, source, executed, receipt)
                    book = json.loads(executed.read_bytes())
                    cells = [c for c in book["cells"] if c.get("metadata", {}).get("abacus", {}).get("role") == "evidence"]
                    cell = next(c for c in cells if c["metadata"]["abacus"]["kind"] == ("line" if field in ("alt", "caption") else "table"))
                    descriptor = cell["outputs"][0]["data"][MODULE.MIME]
                    if field in ("row", "windows-row"):
                        descriptor["rows"][0]["label"] = "C:\\Users\\private\\data" if field == "windows-row" else "/Users/private/data"
                    elif field == "column":
                        descriptor["columns"][0]["label"] = "/private/working/data"
                    elif field == "note":
                        descriptor["notes"] = ["Private source /home/research/file"]
                    else:
                        descriptor[field] = "Private source /Users/private/data"
                    executed.write_bytes(MODULE.notebook.json_bytes(book))
                    record = json.loads(receipt.read_bytes())
                    record["output"] = MODULE.notebook.file_pin(executed, root=root)
                    receipt.write_bytes(MODULE.notebook.json_bytes(record))
                    with self.assertRaisesRegex(ValueError, "Private paths"):
                        MODULE.export_notebook(source, **args)
                    self.assertFalse(args["output_path"].exists())

    def test_uninventoried_extra_export_file_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch.object(MODULE, "ROOT", root):
                source, executed, receipt = self.setup_source(root)
                args = self.arguments(root, source, executed, receipt)
                MODULE.export_notebook(source, **args)
                (args["output_path"] / "unexpected.html").write_text("Unselected output")
                with self.assertRaisesRegex(ValueError, "unlisted"):
                    MODULE.check_export(args["output_path"])

    def test_failed_or_incomplete_numerical_reconciliation_refused(self):
        for mutation in ("failed", "coverage", "other-run"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                with patch.object(MODULE, "ROOT", root):
                    source, executed, receipt = self.setup_source(root)
                    args = self.arguments(root, source, executed, receipt)
                    numerical = json.loads(args["analysis_verification_path"].read_bytes())
                    if mutation == "failed":
                        numerical["checks"][0]["passed"] = False
                    elif mutation == "coverage":
                        numerical["checks"].pop()
                    else:
                        numerical["publication_run_id"] = "other-run"
                    args["analysis_verification_path"].write_bytes(MODULE.notebook.json_bytes(numerical))
                    with self.assertRaisesRegex(ValueError, "Numerical reconciliation"):
                        MODULE.export_notebook(source, **args)

    def test_narrative_html_code_blocks_and_private_paths_refused(self):
        for text in ('<img src="secret">', '```python\nsecret\n```', '[label](https://example.com)', '/Users/private/data'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                MODULE.plain_text(text)


if __name__ == "__main__":
    unittest.main()
