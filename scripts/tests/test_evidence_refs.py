"""Exact saved-row integrity checks use disposable repositories and CSV bytes."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
try:
    SPEC = importlib.util.spec_from_file_location("evidence_refs_tested", SCRIPTS / "evidence_refs.py")
    refs = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(refs)
finally:
    sys.path.pop(0)

STUDY = "01_fixture"
RUN = "20261010T000000Z_fixture"
CSV = "metric_id,count,value,blank,flag\nrow.primary,2,0.125,,False\nother,3,0.500,present,True\n"


def fixture(root):
    (root / "studies" / STUDY).mkdir(parents=True)
    artifact = root / "runs" / STUDY / RUN / "tables/results.csv"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(CSV, encoding="utf-8")
    reference = {
        "id": "primary-row", "label": "Saved primary row", "kind": "csv_row",
        "study_id": STUDY, "run_id": RUN, "artifact": "tables/results.csv",
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "where": {"metric_id": "row.primary"}, "columns": ["count", "value", "blank", "flag"],
    }
    card = {"strategy_id": "fixture_strategy", "study_ids": [STUDY], "evidence_refs": [reference]}
    return artifact, card


def snapshot(root):
    return {path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
            for path in root.rglob("*")}


class EvidenceReferenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.artifact, self.card = fixture(self.root)

    def report(self, card=None):
        return refs.validate_references(self.root, [self.card if card is None else card])

    def update_csv(self, text):
        self.artifact.write_text(text, encoding="utf-8")
        self.card["evidence_refs"][0]["sha256"] = hashlib.sha256(self.artifact.read_bytes()).hexdigest()

    def invalid(self, message, card=None):
        report = self.report(card)
        self.assertEqual(report["status"], "invalid", report)
        self.assertIn(message, "\n".join(report["errors"]))
        return report

    def test_valid_row_is_original_strings_and_ordered_columns(self):
        before = snapshot(self.root)
        report = self.report()
        self.assertEqual(report["status"], "valid")
        self.assertEqual(report["references_verified"], 1)
        row = report["verified_refs"][0]
        self.assertEqual(list(row["values"]), ["count", "value", "blank", "flag"])
        self.assertEqual(row["values"], {"count": "2", "value": "0.125", "blank": "", "flag": "False"})
        self.assertEqual(snapshot(self.root), before)
        self.assertIn("other card claims", report["limits"][0])

    def test_changed_artifact_hash_is_rejected_before_csv_parsing(self):
        self.artifact.write_text("broken csv", encoding="utf-8")
        with mock.patch.object(refs, "_selected_row", side_effect=AssertionError("must not parse mismatched bytes")):
            self.invalid("SHA-256 mismatch")

    def test_missing_and_multiple_matching_rows_fail(self):
        self.card["evidence_refs"][0]["where"] = {"metric_id": "missing"}
        self.invalid("found 0")
        self.update_csv(CSV + "row.primary,7,0.7,,False\n")
        self.card["evidence_refs"][0]["where"] = {"metric_id": "row.primary"}
        self.invalid("found 2")

    def test_unknown_selector_or_selected_column_fails(self):
        for field, value in (("where", {"unknown": "row.primary"}), ("columns", ["unknown"])):
            card = copy.deepcopy(self.card)
            card["evidence_refs"][0][field] = value
            self.invalid("unknown CSV selectors or columns", card)

    def test_duplicate_or_blank_headers_fail(self):
        for text in ("metric_id,value,value\nrow.primary,1,2\n", "metric_id,,value\nrow.primary,1,2\n", ""):
            self.update_csv(text)
            self.invalid("headers must be nonempty and unique")

    def test_selected_columns_are_unique_and_nonempty(self):
        for columns in (["value", "value"], [], [""], [False]):
            card = copy.deepcopy(self.card)
            card["evidence_refs"][0]["columns"] = columns
            with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("metadata must fail before bytes")):
                self.invalid("columns", card)

    def test_blank_and_false_values_are_exact_saved_strings(self):
        self.card["evidence_refs"][0]["where"] = {"blank": "", "flag": "False"}
        self.assertEqual(self.report()["status"], "valid")
        self.card["evidence_refs"][0]["where"] = {"blank": "0"}
        self.invalid("found 0")
        self.card["evidence_refs"][0]["where"] = {"flag": False}
        self.invalid("where")

    def test_study_outside_card_associations_fails_before_bytes(self):
        self.card["study_ids"] = ["02_other_study"]
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("must not read artifact")):
            self.invalid("study_ids")

    def test_cards_without_references_are_valid_without_artifact_reads(self):
        for card in ({"strategy_id": "no_refs", "study_ids": []},
                     {"strategy_id": "empty_refs", "study_ids": [], "evidence_refs": []}):
            with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("must not read artifact")):
                report = self.report(card)
            self.assertEqual(report["status"], "valid")
            self.assertEqual(report["references_verified"], 0)

    def test_all_selected_metadata_is_checked_before_any_artifact_bytes(self):
        bad = copy.deepcopy(self.card["evidence_refs"][0])
        bad.update(id="missing-artifact", artifact="tables/missing.csv")
        self.card["evidence_refs"].append(bad)
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("metadata phase must finish first")):
            report = self.invalid("Missing or inaccessible")
        self.assertEqual(report["references_verified"], 0)

    def test_duplicate_reference_ids_and_unknown_kinds_fail(self):
        self.card["evidence_refs"].append(copy.deepcopy(self.card["evidence_refs"][0]))
        self.invalid("duplicate reference ID")
        self.card["evidence_refs"] = self.card["evidence_refs"][:1]
        self.card["evidence_refs"][0]["kind"] = "inferred_row"
        self.invalid("kind")

    def test_missing_study_run_or_artifact_and_nonordinary_file_fail(self):
        for field, value in (("study_id", "02_missing"), ("run_id", "missing-run"), ("artifact", "tables/missing.csv")):
            card = copy.deepcopy(self.card)
            card["evidence_refs"][0][field] = value
            if field == "study_id":
                card["study_ids"] = [value]
            self.invalid("Missing or inaccessible", card)
        self.artifact.unlink()
        self.artifact.mkdir()
        self.invalid("ordinary file")

    def test_unsafe_relative_paths_and_bad_identity_fail_before_bytes(self):
        for artifact in ("../escape.csv", "/tmp/escape.csv", "tables//results.csv", "tables/./results.csv", "tables\\results.csv", "C:/results.csv",
                         "tables/results.csv?query", "tables/results.csv#fragment", "tables/%2e%2e/results.csv", "tables/ results.csv"):
            card = copy.deepcopy(self.card)
            card["evidence_refs"][0]["artifact"] = artifact
            with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("unsafe path must not be read")):
                self.assertEqual(self.report(card)["status"], "invalid")
        for field in ("study_id", "run_id"):
            card = copy.deepcopy(self.card)
            card["evidence_refs"][0][field] = "../outside"
            self.assertEqual(self.report(card)["status"], "invalid")

    def test_symlinked_artifact_and_ancestor_fail_without_outside_reads(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "results.csv"
            external.write_text(CSV, encoding="utf-8")
            self.artifact.unlink()
            self.artifact.symlink_to(external)
            with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("outside bytes must not be read")):
                self.invalid("Symlink")
            self.artifact.unlink()
            self.artifact.parent.rmdir()
            self.artifact.parent.symlink_to(Path(outside), target_is_directory=True)
            with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("outside bytes must not be read")):
                self.invalid("Symlink")

    def test_symlinked_study_or_run_is_rejected(self):
        for relative in ("studies/" + STUDY, "runs/{}/{}".format(STUDY, RUN)):
            with tempfile.TemporaryDirectory() as root_directory, tempfile.TemporaryDirectory() as outside:
                root = Path(root_directory)
                _, card = fixture(root)
                path = root / relative
                moved = Path(outside) / "retained"
                path.rename(moved)
                path.symlink_to(moved, target_is_directory=True)
                with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("outside bytes must not be read")):
                    report = refs.validate_references(root, [card])
                self.assertEqual(report["status"], "invalid")
                self.assertIn("Symlink", "\n".join(report["errors"]))

    def test_malformed_csv_records_and_utf8_fail(self):
        for text in (CSV + "too,few\n", 'metric_id,value\nrow.primary,"unterminated\n'):
            self.update_csv(text)
            self.assertEqual(self.report()["status"], "invalid")
        self.artifact.write_bytes(b"\xff\xfe")
        self.card["evidence_refs"][0]["sha256"] = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.invalid("cannot read saved CSV")

    def test_index_shape_duplicate_and_unknown_selection_fail_explicitly(self):
        index = {"schema_version": 1, "strategies": [self.card]}
        self.assertEqual(refs.select_cards(index, ["fixture_strategy", "fixture_strategy"]), [self.card])
        for value in (False, "1", 2, None):
            with self.assertRaisesRegex(refs.EvidenceReferenceError, "schema_version"):
                refs.select_cards({"schema_version": value, "strategies": [self.card]})
        with self.assertRaisesRegex(refs.EvidenceReferenceError, "Duplicate strategy ID"):
            refs.select_cards({"schema_version": 1, "strategies": [self.card, self.card]})
        with self.assertRaisesRegex(refs.EvidenceReferenceError, "Unknown strategy"):
            refs.select_cards(index, ["unknown"])
        for card in (None, {}, {"strategy_id": "bad", "study_ids": [False]},
                     {"strategy_id": "bad", "study_ids": [], "evidence_refs": {}}):
            self.assertEqual(refs.validate_references(self.root, [card])["status"], "invalid")

    def test_cli_is_read_only_from_unrelated_cwd_in_both_python_modes(self):
        index_path = self.root / "strategies/index.json"
        index_path.parent.mkdir()
        index_path.write_text(json.dumps({"schema_version": 1, "strategies": [self.card]}), encoding="utf-8")
        before = snapshot(self.root)
        with tempfile.TemporaryDirectory() as unrelated:
            for options in ([], ["-O"]):
                result = subprocess.run([sys.executable, "-B", *options, str(SCRIPTS / "check-evidence-references.py"),
                                         "--root", str(self.root), "--json"], cwd=unrelated, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["verified_refs"][0]["values"]["blank"], "")
                self.assertEqual(snapshot(self.root), before)
                for key, bad in (("artifact", "../escape.csv"), ("columns", ["value", "value"]), ("sha256", "0" * 64)):
                    card = copy.deepcopy(self.card)
                    card["evidence_refs"][0][key] = bad
                    index_path.write_text(json.dumps({"schema_version": 1, "strategies": [card]}), encoding="utf-8")
                    result = subprocess.run([sys.executable, "-B", *options, str(SCRIPTS / "check-evidence-references.py"),
                                             "--root", str(self.root), "--json"], cwd=unrelated, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["status"], "invalid")
                index_path.write_text(json.dumps({"schema_version": 1, "strategies": [self.card]}), encoding="utf-8")
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "results.csv"
            target.write_text(CSV, encoding="utf-8")
            self.artifact.unlink()
            self.artifact.symlink_to(target)
            for options in ([], ["-O"]):
                result = subprocess.run([sys.executable, "-B", *options, str(SCRIPTS / "check-evidence-references.py"),
                                         "--root", str(self.root), "--json"], text=True, capture_output=True)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("Symlink", "\n".join(json.loads(result.stdout)["errors"]))

    def test_cli_rejects_duplicate_json_keys_and_nonfinite_numbers(self):
        index_path = self.root / "strategies/index.json"
        index_path.parent.mkdir()
        for text in ('{"schema_version":1,"schema_version":1,"strategies":[]}',
                     '{"schema_version":1,"strategies":[],"value":NaN}',
                     '{"schema_version":1,"strategies":[],"value":1e999}'):
            index_path.write_text(text, encoding="utf-8")
            for options in ([], ["-O"]):
                result = subprocess.run([sys.executable, "-B", *options, str(SCRIPTS / "check-evidence-references.py"),
                                         "--root", str(self.root), "--json"], text=True, capture_output=True)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
