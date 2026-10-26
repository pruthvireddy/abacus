"""Synthetic saved-evidence checks for every active presentation exporter."""
from __future__ import annotations

import contextlib
import copy
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
import warnings


ROOT = Path(__file__).resolve().parents[3]
STUDIES = (
    "01_reversal_follow_through", "02_followthrough_candle_adverse",
    "03_multi_rxv_alignment", "04_reversal_candle_quality",
    "06_vwap_state_dynamics", "07_range_xv_edge_candidates",
    "08_countertrend_bar_continuation", "09_range_xv_c2_confirmation",
    "10_range_xv_session_overlay", "11_vwap_conditional_probabilities",
    "12_gc_ema_band_excursions", "13_gc_ema_band_filter_validation",
    "14_asia_session_vp_levels", "15_vwap_excursion_response",
    "16_range_xv_reversal_paths",
)
CSV = (
    "cohort,side,metric_id,label,flag,count,ratio,scaled,empty,metric_id_departure,metric_id_touch\n"
    "yes,long,metric_one,first_label,True,2,0.25,8,,departure_one,touch_one\n"
    "no,long,metric_two,unselected_row,False,4,0.5,12,,departure_two,touch_two\n"
    "yes,long,metric_three,final_label,false,6,0.75,16,,departure_three,touch_three\n"
)
COLUMNS = [
    {"column": {"key": "metric_id", "label": "Metric"}, "scale": 1},
    {"column": {"key": "label", "label": "Label"}, "scale": 1},
    {"column": {"key": "flag", "label": "Flag"}, "scale": 1},
    {"column": {"key": "count", "label": "Count", "format": "number"}, "scale": 1},
    {"column": {"key": "ratio", "label": "Ratio", "format": "percent"}, "scale": 1},
    {"column": {"key": "scaled", "label": "Scaled", "format": "number"}, "scale": .25},
    {"column": {"key": "empty", "label": "Empty", "format": "number"}, "scale": 1},
    {"column": {"key": "metric_id_departure", "label": "Departure"}, "scale": 1},
    {"column": {"key": "metric_id_touch", "label": "Touch"}, "scale": 1},
]
ROWS = [
    {"metric_id": "metric_one", "label": "first label", "flag": True,
     "count": 2., "ratio": .25, "scaled": 2., "empty": None,
     "metric_id_departure": "departure_one", "metric_id_touch": "touch_one"},
    {"metric_id": "metric_two", "label": "unselected row", "flag": False,
     "count": 4., "ratio": .5, "scaled": 3., "empty": None,
     "metric_id_departure": "departure_two", "metric_id_touch": "touch_two"},
    {"metric_id": "metric_three", "label": "final label", "flag": "false",
     "count": 6., "ratio": .75, "scaled": 4., "empty": None,
     "metric_id_departure": "departure_three", "metric_id_touch": "touch_three"},
]
# Frozen before the guard changes using the original complete prepare() result
# and the exporters' indent/Unicode/newline/allow_nan serialization rules.
ORIGINAL_SERIALIZED_SHA256 = (
    "79f98035ebf23cf821b4736ea08df041e32c650236a781d3ef3a5bf0c9624b3a",
    "af9bfdfa800e8471b4499b8f986b4e1302c597041e5e0faf04a9d536f1b5d429",
)


def load_exporter(study):
    path = ROOT / "studies" / study / "publish_web.py"
    spec = importlib.util.spec_from_file_location("export_guard_" + study, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(module, root):
    module.ROOT = root
    module.SPEC = {
        "study_id": "synthetic", "source_run_id": "saved",
        "publication_id": "synthetic-publication", "title": "Saved title",
        "summary": "Saved summary", "selection": "Explicit selection",
        "reason": "Preserve saved meaning", "sources": ["evidence.md"],
        "sections": [
            {"kind": "text", "id": "claim", "title": "Authored claim",
             "body": "Unchanged authored text.", "source": "evidence.md", "anchor": "A claim"},
            {"kind": "table", "id": "selected", "title": "Selected rows",
             "file": "tables/selection.csv", "columns": copy.deepcopy(COLUMNS),
             "where": {"cohort": ["yes"], "side": ["long"]}, "description": "Two predicates"},
            {"kind": "table", "id": "all", "title": "All rows",
             "file": "tables/selection.csv", "columns": copy.deepcopy(COLUMNS),
             "where": {}, "description": "Empty predicates"},
        ],
    }
    run = root / "runs/synthetic/saved"
    (run / "tables").mkdir(parents=True)
    (run / "evidence.md").write_text("# Saved evidence\n\n## A claim\nSaved text.\n")
    (run / "tables/selection.csv").write_text(CSV)
    pin_sources(module)
    return run


def pin_sources(module):
    run = module.ROOT / "runs/synthetic/saved"
    module.EXPECTED = {
        str(path.relative_to(module.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [run / "evidence.md", run / "tables/selection.csv"]
    }


def inventory(root):
    """Include directory entries and exact bytes, so read-only claims are tested."""
    return {
        str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
    }


def serialize(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


class ExportGuardTests(unittest.TestCase):
    def setUp(self):
        # The 13 exporters retaining their original projection code open CSVs
        # without a context manager. That pre-existing warning is outside this change.
        warning_context = warnings.catch_warnings()
        warning_context.__enter__()
        warnings.simplefilter("ignore", ResourceWarning)
        self.addCleanup(warning_context.__exit__, None, None, None)

    def test_complete_original_serialization_and_selected_cells(self):
        for study in STUDIES:
            with self.subTest(study=study), tempfile.TemporaryDirectory() as temporary:
                module = load_exporter(study)
                root = Path(temporary).resolve()
                fixture(module, root)
                before = inventory(root)
                publication, mapping = module.prepare("synthetic_revision")
                self.assertEqual(
                    tuple(hashlib.sha256(serialize(value)).hexdigest() for value in [publication, mapping]),
                    ORIGINAL_SERIALIZED_SHA256,
                )
                self.assertEqual(publication["sections"][1]["rows"], [ROWS[0], ROWS[2]])
                self.assertEqual(publication["sections"][2]["rows"], ROWS)
                self.assertEqual(publication["sections"][1]["columns"], [f["column"] for f in COLUMNS])
                self.assertEqual([binding["data_row_1_based"] for binding in mapping["bindings"]],
                                 [1] * 9 + [3] * 9 + [1] * 9 + [2] * 9 + [3] * 9)
                self.assertEqual([binding["output_row"] for binding in mapping["bindings"]],
                                 [0] * 9 + [1] * 9 + [0] * 9 + [1] * 9 + [2] * 9)
                self.assertEqual(mapping["bindings"][5], {
                    "section": "selected", "output_row": 0, "column": "scaled",
                    "source": "runs/synthetic/saved/tables/selection.csv",
                    "data_row_1_based": 1, "source_column": "scaled", "source_raw": "8",
                    "scale": .25, "value": 2.,
                })
                self.assertEqual(inventory(root), before)

    def test_exactly_100_rows_is_valid(self):
        for study in STUDIES:
            with self.subTest(study=study), tempfile.TemporaryDirectory() as temporary:
                module = load_exporter(study)
                run = fixture(module, Path(temporary).resolve())
                (run / "tables/selection.csv").write_text(CSV.splitlines(True)[0] + CSV.splitlines(True)[1] * 100)
                pin_sources(module)
                before = inventory(module.ROOT)
                publication, mapping = module.prepare("hundred")
                self.assertEqual([len(s["rows"]) for s in publication["sections"] if s["kind"] == "table"], [100, 100])
                self.assertEqual(len(mapping["bindings"]), 1800)
                self.assertEqual(inventory(module.ROOT), before)

    def test_guard_failures_in_plain_and_optimized_processes(self):
        cases = (
            "empty", "too_many", "nan", "infinity", "overflow", "bad_hash",
            "missing_pin", "missing_file", "missing_column", "unsafe_revision",
            "publication_mismatch", "map_mismatch", "existing_revision",
        )
        for optimized in [False, True]:
            for study in STUDIES:
                for case in cases:
                    with self.subTest(optimized=optimized, study=study, case=case), tempfile.TemporaryDirectory() as temporary:
                        root = Path(temporary).resolve() / "fixture"
                        command = [sys.executable] + (["-O"] if optimized else [])
                        command += [str(Path(__file__).resolve()), "--guard-child", study, case, str(root)]
                        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
                        result = subprocess.run(command, cwd=temporary, env=environment, text=True, capture_output=True)
                        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertNotIn("saved-cell transfers", result.stdout)
                        self.assertEqual(result.stdout, "", result.stdout + result.stderr)
                        self.assertNotIn("AssertionError", result.stderr)
                        expected = {
                            "existing_revision": "FileExistsError", "missing_pin": "KeyError",
                            "missing_column": "KeyError", "missing_file": "FileNotFoundError",
                        }.get(case, "ValueError")
                        self.assertIn(expected, result.stderr)
                        if case in ["empty", "too_many", "nan", "infinity", "overflow"]:
                            self.assertIn("selected", result.stderr)
                            self.assertIn("selection.csv", result.stderr)
                        elif case == "bad_hash":
                            self.assertIn("runs/synthetic/saved/tables/selection.csv", result.stderr)
                        elif case in ["publication_mismatch", "map_mismatch"]:
                            self.assertIn("publication.json" if case == "publication_mismatch" else "source-map.json", result.stderr)
                        self.assertEqual(inventory(root), json_inventory(root.parent / "before.json"))

    def test_valid_cli_write_then_read_only_check_and_existing_refusal(self):
        for study in STUDIES:
            with self.subTest(study=study), tempfile.TemporaryDirectory() as temporary:
                module = load_exporter(study)
                root = Path(temporary).resolve()
                fixture(module, root)
                inputs = inventory(root / "runs")
                expected = module.prepare("valid_revision")
                with contextlib.redirect_stdout(io.StringIO()):
                    module.main(["--revision", "valid_revision"])
                out = root / "reports/exports/synthetic/saved/valid_revision"
                for name, value in zip(["publication.json", "source-map.json"], expected):
                    self.assertEqual((out / name).read_bytes(), serialize(value))
                self.assertEqual((out / "provenance/publish_web.py").read_bytes(), Path(module.__file__).read_bytes())
                before = inventory(root)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    module.main(["--revision", "valid_revision", "--check"])
                self.assertIn("saved-cell transfers and source hashes match", output.getvalue())
                self.assertEqual(inventory(root), before)
                with self.assertRaises(FileExistsError), contextlib.redirect_stdout(io.StringIO()):
                    module.main(["--revision", "valid_revision"])
                self.assertEqual(inventory(root), before)
                self.assertEqual(inventory(root / "runs"), inputs)


def json_inventory(path):
    encoded = json.loads(path.read_text())
    return {key: bytes.fromhex(value) if value is not None else None for key, value in encoded.items()}


def guard_child(study, case, root):
    module = load_exporter(study)
    run = fixture(module, root)
    csv_path = run / "tables/selection.csv"
    revision = "failure_revision"
    check = False
    if case == "empty":
        module.SPEC["sections"][1]["where"] = {"cohort": ["absent"]}
    elif case == "too_many":
        csv_path.write_text(CSV.splitlines(True)[0] + CSV.splitlines(True)[1] * 101)
        pin_sources(module)
    elif case in ["nan", "infinity", "overflow"]:
        replacement = {"nan": "NaN", "infinity": "Infinity", "overflow": "1e308"}[case]
        csv_path.write_text(CSV.replace(",8,,", f",{replacement},,"))
        if case == "overflow":
            module.SPEC["sections"][1]["columns"][5]["scale"] = 10
        pin_sources(module)
    elif case == "bad_hash":
        module.EXPECTED["runs/synthetic/saved/tables/selection.csv"] = "0" * 64
    elif case == "missing_pin":
        del module.EXPECTED["runs/synthetic/saved/tables/selection.csv"]
    elif case == "missing_file":
        csv_path.unlink()
    elif case == "missing_column":
        module.SPEC["sections"][1]["columns"][0]["column"]["key"] = "absent"
    elif case == "unsafe_revision":
        revision = "../../escape"
        def forbidden_prepare(*args):
            raise RuntimeError("unsafe revision reached preparation")
        module.prepare = forbidden_prepare
    elif case in ["publication_mismatch", "map_mismatch", "existing_revision"]:
        out = root / "reports/exports/synthetic/saved" / revision
        out.mkdir(parents=True)
        publication, mapping = module.prepare(revision)
        if case == "publication_mismatch":
            publication["title"] = "Incorrect title"
        elif case == "map_mismatch":
            mapping["bindings"][0]["source_raw"] = "Incorrect saved cell"
        for name, value in [("publication.json", publication), ("source-map.json", mapping)]:
            (out / name).write_bytes(serialize(value))
        check = case != "existing_revision"
    before = root.parent / "before.json"
    recorded = inventory(root)
    before.write_text(json.dumps({key: value.hex() if value is not None else None for key, value in recorded.items()}))
    arguments = ["--revision", revision] + (["--check"] if check else [])
    module.main(arguments)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--guard-child":
        guard_child(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
    else:
        unittest.main()
