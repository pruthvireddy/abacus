import contextlib
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from abacus_sahadeva import presentation_revision, saved_evidence


ROOT = Path(__file__).resolve().parents[3]
STUDIES = ["08_countertrend_bar_continuation", "09_range_xv_c2_confirmation"]


def load_exporter(study):
    path = ROOT / "studies" / study / "publish_web.py"
    spec = importlib.util.spec_from_file_location("projection_exporter_" + study, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(root):
    return {str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
            for path in root.rglob("*")}


def make_fixture(root, module):
    run = root / "runs" / "synthetic-study" / "saved-run"
    run.mkdir(parents=True)
    (run / "report.md").write_text("# Question\nSaved résumé.\n## Limits\nNo execution tested.\n")
    (run / "config.json").write_text('{"fixed": true}\n')
    with (run / "table.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "cohort", "rate", "flag", "metric_id", "label"])
        writer.writerows([
            ["keep", "A", ".125", "True", "first_id", "first_row"],
            ["skip", "A", ".9", "true", "skipped_id", "skipped_row"],
            ["keep", "A", "", "False", "third_id", "third_row"],
            ["keep", "B", ".4", "TRUE", "other_id", "other_cohort"],
        ])
    columns = [
        {"column": {"key": "rate", "label": "Rate", "format": "percent", "precision": 1}, "scale": 1},
        {"column": {"key": "flag", "label": "Flag"}, "scale": 1},
        {"column": {"key": "metric_id", "label": "ID"}, "scale": 1},
        {"column": {"key": "label", "label": "Label"}, "scale": 10},
    ]
    module.ROOT = root
    module.SPEC = {
        "study_id": "synthetic-study", "source_run_id": "saved-run", "publication_id": "synthetic-publication",
        "title": "Saved résumé", "summary": "Bounded saved evidence.", "selection": "Explicit reference",
        "reason": "Preserve its scope.", "sources": ["config.json"], "sections": [
            {"kind": "text", "id": "question", "title": "Question", "body": "Authored résumé and qualification.",
             "source": "report.md", "anchor": "Question"},
            {"kind": "table", "id": "selected", "title": "Selected", "file": "table.csv", "columns": columns,
             "where": {"metric": ["keep"], "cohort": ["A"]}, "description": "Two separated source rows"},
            {"kind": "table", "id": "all", "title": "All saved rows", "file": "table.csv", "columns": [columns[-1]],
             "where": {}, "description": "Empty predicate selects all"},
        ],
    }
    module.EXPECTED = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in run.iterdir()}
    return run


def expected_objects(module, revision):
    prefix = "runs/synthetic-study/saved-run/"
    selected = [
        {"rate": .125, "flag": True, "metric_id": "first_id", "label": "first row"},
        {"rate": None, "flag": False, "metric_id": "third_id", "label": "third row"},
    ]
    bindings = [
        {"section": "selected", "output_row": 0, "column": "rate", "source": prefix + "table.csv", "data_row_1_based": 1, "source_column": "rate", "source_raw": ".125", "scale": 1, "value": .125},
        {"section": "selected", "output_row": 0, "column": "flag", "source": prefix + "table.csv", "data_row_1_based": 1, "source_column": "flag", "source_raw": "True", "scale": 1, "value": True},
        {"section": "selected", "output_row": 0, "column": "metric_id", "source": prefix + "table.csv", "data_row_1_based": 1, "source_column": "metric_id", "source_raw": "first_id", "scale": 1, "value": "first_id"},
        {"section": "selected", "output_row": 0, "column": "label", "source": prefix + "table.csv", "data_row_1_based": 1, "source_column": "label", "source_raw": "first_row", "scale": 10, "value": "first row"},
        {"section": "selected", "output_row": 1, "column": "rate", "source": prefix + "table.csv", "data_row_1_based": 3, "source_column": "rate", "source_raw": "", "scale": 1, "value": None},
        {"section": "selected", "output_row": 1, "column": "flag", "source": prefix + "table.csv", "data_row_1_based": 3, "source_column": "flag", "source_raw": "False", "scale": 1, "value": False},
        {"section": "selected", "output_row": 1, "column": "metric_id", "source": prefix + "table.csv", "data_row_1_based": 3, "source_column": "metric_id", "source_raw": "third_id", "scale": 1, "value": "third_id"},
        {"section": "selected", "output_row": 1, "column": "label", "source": prefix + "table.csv", "data_row_1_based": 3, "source_column": "label", "source_raw": "third_row", "scale": 10, "value": "third row"},
        {"section": "all", "output_row": 0, "column": "label", "source": prefix + "table.csv", "data_row_1_based": 1, "source_column": "label", "source_raw": "first_row", "scale": 10, "value": "first row"},
        {"section": "all", "output_row": 1, "column": "label", "source": prefix + "table.csv", "data_row_1_based": 2, "source_column": "label", "source_raw": "skipped_row", "scale": 10, "value": "skipped row"},
        {"section": "all", "output_row": 2, "column": "label", "source": prefix + "table.csv", "data_row_1_based": 3, "source_column": "label", "source_raw": "third_row", "scale": 10, "value": "third row"},
        {"section": "all", "output_row": 3, "column": "label", "source": prefix + "table.csv", "data_row_1_based": 4, "source_column": "label", "source_raw": "other_cohort", "scale": 10, "value": "other cohort"},
    ]
    columns = [field["column"] for field in module.SPEC["sections"][1]["columns"]]
    publication = {
        "schemaVersion": "1.0", "id": "synthetic-publication", "title": "Saved résumé",
        "summary": "Bounded saved evidence.", "publishedAt": "2026-10-06T23:09:36Z",
        "source": {"producer": "sahadeva", "runId": "saved-run"}, "sections": [
            {"kind": "text", "id": "question", "title": "Question", "body": "Authored résumé and qualification."},
            {"kind": "table", "id": "selected", "title": "Selected", "columns": columns, "rows": selected},
            {"kind": "table", "id": "all", "title": "All saved rows", "columns": [columns[-1]],
             "rows": [{"label": "first row"}, {"label": "skipped row"}, {"label": "third row"}, {"label": "other cohort"}]},
            {"kind": "text", "id": "sources-provenance", "title": "Source and presentation provenance",
             "body": "Study synthetic-study; source run saved-run. Explicit reference: Preserve its scope.\n\n"
                     f"Presentation revision {revision}, web-study-report-1.0. Saved numerical tables are the authority; only selected rows and columns are presented. No new statistics or research execution. The publication record identifies this JSON and its selected assets."},
        ],
    }
    mapping = {
        "study_id": "synthetic-study", "source_run_id": "saved-run", "revision_id": revision,
        "sources": [{"path": prefix + name, "sha256": module.EXPECTED[prefix + name]}
                    for name in ["config.json", "report.md", "table.csv"]],
        "bindings": bindings,
        "claims": [{"section": "question", "source": prefix + "report.md",
                    "heading_or_scope": {"scope": "Selected saved document; authored abridgment", "headings": ["Question", "Limits"]},
                    "operation": "Authored abridgment preserving the saved meaning; definitions and result numbers are not recomputed."}],
        "table_selections": [
            {"section": "selected", "source": "table.csv", "where": {"metric": ["keep"], "cohort": ["A"]}, "description": "Two separated source rows"},
            {"section": "all", "source": "table.csv", "where": {}, "description": "Empty predicate selects all"},
        ],
        "figures": [],
    }
    return publication, mapping


def serialized(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


class ExportProjectionTest(unittest.TestCase):
    def test_complete_prepare_objects_serialization_and_inputs_for_both_adopters(self):
        for study in STUDIES:
            with self.subTest(study=study), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                module = load_exporter(study)
                make_fixture(root, module)
                before = inventory(root), copy.deepcopy(module.SPEC), dict(module.EXPECTED)
                actual = module.prepare("fixture-v1")
                expected = expected_objects(module, "fixture-v1")
                self.assertEqual(actual, expected)
                self.assertEqual(tuple(map(serialized, actual)), tuple(map(serialized, expected)))
                self.assertIn("résumé".encode(), serialized(actual[0]))
                self.assertNotIn(b"\\u00e9", serialized(actual[0]))
                self.assertEqual((inventory(root), module.SPEC, module.EXPECTED), before)

    def test_future_output_retains_exact_bounded_source_snapshots_and_readonly_check(self):
        for study in STUDIES:
            with self.subTest(study=study), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                module = load_exporter(study)
                run = make_fixture(root, module)
                inputs = inventory(run)
                specifications = copy.deepcopy(module.SPEC), dict(module.EXPECTED)
                output = root / "reports/exports/synthetic-study/saved-run/fixture-v1"
                with contextlib.redirect_stdout(io.StringIO()):
                    module.main(["--revision", "fixture-v1"])
                publication, mapping = expected_objects(module, "fixture-v1")
                self.assertEqual((output / "publication.json").read_bytes(), serialized(publication))
                self.assertEqual((output / "source-map.json").read_bytes(), serialized(mapping))
                exporter_bytes = Path(module.__file__).read_bytes()
                helper_bytes = Path(saved_evidence.__file__).read_bytes()
                writer_bytes = Path(presentation_revision.__file__).read_bytes()
                self.assertEqual((output / "provenance/publish_web.py").read_bytes(), exporter_bytes)
                self.assertEqual((output / "provenance/saved_evidence.py").read_bytes(), helper_bytes)
                self.assertEqual((output / "provenance/presentation_revision.py").read_bytes(), writer_bytes)
                self.assertEqual(json.loads((output / "provenance/source-inventory.json").read_text()), [
                    {"path": "provenance/publish_web.py", "sha256": hashlib.sha256(exporter_bytes).hexdigest()},
                    {"path": "provenance/saved_evidence.py", "sha256": hashlib.sha256(helper_bytes).hexdigest()},
                    {"path": "provenance/presentation_revision.py", "sha256": hashlib.sha256(writer_bytes).hexdigest()},
                ])
                self.assertEqual(set(inventory(output)), {
                    "publication.json", "source-map.json", "README.md", "provenance", "provenance/publish_web.py",
                    "provenance/saved_evidence.py", "provenance/presentation_revision.py", "provenance/source-inventory.json",
                })
                before = inventory(root)
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    module.main(["--revision", "fixture-v1", "--check"])
                self.assertIn("12 saved-cell transfers and source hashes match", stdout.getvalue())
                self.assertEqual(inventory(root), before)
                self.assertEqual(inventory(run), inputs)
                self.assertEqual((module.SPEC, module.EXPECTED), specifications)
                with self.assertRaises(FileExistsError), contextlib.redirect_stdout(io.StringIO()):
                    module.main(["--revision", "fixture-v1"])
                self.assertEqual(inventory(root), before)
                self.assertEqual((module.SPEC, module.EXPECTED), specifications)

    def test_missing_files_columns_and_pins_fail_before_output_and_preserve_inputs(self):
        for study in STUDIES:
            for failure in ["missing-file", "missing-column", "missing-pin"]:
                with self.subTest(study=study, failure=failure), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary).resolve()
                    module = load_exporter(study)
                    make_fixture(root, module)
                    section = module.SPEC["sections"][1]
                    if failure == "missing-file":
                        section["file"] = "absent.csv"
                        error = FileNotFoundError
                    elif failure == "missing-column":
                        section["columns"][0]["column"]["key"] = "absent-column"
                        error = KeyError
                    else:
                        del module.EXPECTED["runs/synthetic-study/saved-run/table.csv"]
                        error = KeyError
                    before = inventory(root)
                    with self.assertRaises(error), contextlib.redirect_stdout(io.StringIO()):
                        module.main(["--revision", "failed-v1"])
                    self.assertEqual(inventory(root), before)
                    self.assertFalse((root / "reports").exists())

    def test_adopter_numeric_and_selection_failures_are_nonzero_in_normal_and_optimized_subprocesses(self):
        script = """
import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('exporter_guard_subject',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
state=json.loads(Path(sys.argv[3]).read_text())
module.ROOT=Path(sys.argv[2]);module.SPEC=state['spec'];module.EXPECTED=state['expected']
module.main(['--revision','failed-v1'])
"""
        for study in STUDIES:
            for optimized in [False, True]:
                for failure in ["NaN", "Infinity", "overflow", "empty", "101"]:
                    with self.subTest(study=study, optimized=optimized, failure=failure), tempfile.TemporaryDirectory() as temporary:
                        base = Path(temporary).resolve()
                        root = base / "workspace"
                        module = load_exporter(study)
                        run = make_fixture(root, module)
                        section = module.SPEC["sections"][1]
                        module.SPEC["sections"] = [section]
                        if failure in ["NaN", "Infinity", "overflow"]:
                            raw = "1e308" if failure == "overflow" else failure
                            (run / "table.csv").write_text(f"metric,cohort,rate,flag,metric_id,label\nkeep,A,{raw},True,first_id,first_row\n")
                            if failure == "overflow":
                                section["columns"][0]["scale"] = 10
                            expected_message = "numeric value must be finite"
                        elif failure == "empty":
                            section["where"] = {"metric": ["absent"]}
                            expected_message = "got 0"
                        else:
                            (run / "table.csv").write_text("metric,cohort,rate,flag,metric_id,label\n" + "keep,A,.125,True,first_id,first_row\n" * 101)
                            expected_message = "got 101"
                        state = base / "state.json"
                        state.write_text(json.dumps({"spec": module.SPEC, "expected": module.EXPECTED}))
                        before = inventory(root)
                        command = [sys.executable, "-B"] + (["-O"] if optimized else [])
                        result = subprocess.run(command + ["-c", script, str(module.__file__), str(root), str(state)],
                                                text=True, capture_output=True,
                                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("ValueError", result.stderr)
                        self.assertIn(expected_message, result.stderr)
                        self.assertIn("Section 'selected'", result.stderr)
                        self.assertIn("table.csv", result.stderr)
                        self.assertEqual(result.stdout, "")
                        self.assertEqual(inventory(root), before)
                        self.assertFalse((root / "reports").exists())

    def test_serialization_and_each_producer_read_failure_precede_output_creation(self):
        for study in STUDIES:
            for failure in ["publication", "source-map", "exporter-source", "projection-source", "writer-source"]:
                with self.subTest(study=study, failure=failure), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary).resolve()
                    module = load_exporter(study)
                    make_fixture(root, module)
                    before = inventory(root), copy.deepcopy(module.SPEC), dict(module.EXPECTED)
                    if failure in ["publication", "source-map"]:
                        publication, mapping = module.prepare("failed-v1")
                        target = publication if failure == "publication" else mapping
                        target["invalid-synthetic-value"] = float("nan")
                        patch = mock.patch.object(module, "prepare", return_value=(publication, mapping))
                        error = ValueError
                    else:
                        failed_path = {
                            "exporter-source": Path(module.__file__),
                            "projection-source": Path(saved_evidence.__file__),
                            "writer-source": Path(presentation_revision.__file__),
                        }[failure]
                        original = Path.read_bytes

                        def read_bytes(path):
                            if path == failed_path:
                                raise OSError("Synthetic producer read failure")
                            return original(path)

                        patch = mock.patch.object(Path, "read_bytes", read_bytes)
                        error = OSError
                    with patch, self.assertRaises(error), contextlib.redirect_stdout(io.StringIO()):
                        module.main(["--revision", "failed-v1"])
                    self.assertEqual((inventory(root), module.SPEC, module.EXPECTED), before)
                    self.assertFalse((root / "reports").exists())

    def test_both_exporters_refuse_broken_revision_links_and_redirected_ancestors(self):
        for study in STUDIES:
            for target in ["revision", "ancestor"]:
                with self.subTest(study=study, target=target), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary).resolve() / "workspace"
                    module = load_exporter(study)
                    run = make_fixture(root, module)
                    if target == "revision":
                        output = root / "reports/exports/synthetic-study/saved-run/failed-v1"
                        output.parent.mkdir(parents=True)
                        output.symlink_to(root / "missing-revision")
                        error = FileExistsError
                    else:
                        external = root.parent / "outside"
                        external.mkdir()
                        (root / "reports").symlink_to(external, target_is_directory=True)
                        error = ValueError
                    inputs = inventory(run), copy.deepcopy(module.SPEC), dict(module.EXPECTED)
                    with self.assertRaises(error), contextlib.redirect_stdout(io.StringIO()):
                        module.main(["--revision", "failed-v1"])
                    self.assertEqual((inventory(run), module.SPEC, module.EXPECTED), inputs)
                    if target == "revision":
                        self.assertTrue(output.is_symlink())
                        self.assertFalse(output.exists())
                    else:
                        self.assertEqual(list(external.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
