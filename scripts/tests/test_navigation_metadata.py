"""Synthetic navigation declarations; no research imports or retained data."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from navigation_metadata import NavigationMetadataError, load_navigation, validate_navigation, validate_reference_shape


def study_record(sid="01_synthetic", **changes):
    record = {"study_id": sid, "title": "Synthetic saved study", "summary": "Synthetic description", "status": "historical_import", "topic": "synthetic", "products": ["FAKE"], "data_summary": "Disposable fixture inputs", "evidence_status": "Not scientifically assessed", "strategy_ids": []}
    record.update(changes)
    return record


def strategy_record(**changes):
    record = {"strategy_id": "synthetic_card", "title": "Synthetic idea", "path": "strategies/synthetic_card.md", "status": "proposed", "study_ids": ["01_synthetic"], "summary": "Synthetic interpretation"}
    record.update(changes)
    return record


def reference_record(**changes):
    record = {"id": "primary-scorecard", "label": "Synthetic exact row", "kind": "csv_row", "study_id": "01_synthetic", "run_id": "run2", "artifact": "tables/scores.csv", "sha256": "0" * 64, "where": {"metric_id": "primary"}, "columns": ["events", "value"]}
    record.update(changes)
    return record


def write_file(root, locator, content="synthetic fixture\n"):
    path = root / locator
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_navigation(root, studies, strategies):
    for record in studies:
        sid = record["study_id"]
        write_file(root, f"studies/{sid}/study.json", json.dumps(record))
        write_file(root, f"studies/{sid}/README.md")
    write_file(root, "strategies/index.json", json.dumps({"schema_version": 1, "strategies": strategies}))
    for card in strategies:
        write_file(root, card["path"])
    (root / "runs").mkdir(exist_ok=True)


class NavigationMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.study = study_record()
        self.card = strategy_record()
        self.write()

    def write(self):
        write_navigation(self.root, [self.study], [self.card])

    def assert_invalid(self, text):
        with self.assertRaisesRegex(NavigationMetadataError, "(?i)" + text):
            load_navigation(self.root)

    def test_existing_optional_schema_and_free_status_compatibility(self):
        self.study.update(status="locally verified exploratory overlay", optional_context={"computed": None, "checked": False})
        self.card["status"] = "untested implementation option"
        self.write()
        studies, cards = load_navigation(self.root)
        self.assertEqual(studies[0]["optional_context"], {"computed": None, "checked": False})
        self.assertEqual(cards[0]["status"], self.card["status"])

    def test_schema_version_bool_or_unknown_is_rejected(self):
        for version in (True, "1", 2):
            with self.subTest(version=version):
                self.study["schema_version"] = version
                self.write()
                self.assert_invalid("schema_version")

    def test_top_level_and_required_field_types(self):
        for field, value in (("title", False), ("products", "FAKE"), ("strategy_ids", {}), ("status", "")):
            with self.subTest(field=field):
                self.study = study_record(**{field: value})
                self.write()
                self.assert_invalid(field)
        self.study = study_record()
        self.write()
        write_file(self.root, "strategies/index.json", "[]")
        self.assert_invalid("strategy index: expected an object")

    def test_duplicate_json_keys_and_nonfinite_numbers(self):
        for content in ('{"strategies": [], "strategies": []}', '{"strategies": [], "ignored": NaN}', '{"strategies": [], "ignored": 1e999}'):
            with self.subTest(content=content):
                write_file(self.root, "strategies/index.json", content)
                self.assert_invalid("duplicate|finite")

    def test_study_id_must_match_owning_directory(self):
        path = self.root / "studies/01_synthetic/study.json"
        path.write_text(json.dumps(study_record("02_elsewhere")), encoding="utf-8")
        self.assert_invalid("owning directory")

    def test_metadata_in_nonconforming_directory_is_rejected_not_silently_ignored(self):
        write_file(self.root, "studies/not-a-study/study.json", json.dumps(study_record()))
        self.assert_invalid("owning directory")

    def test_non_utf8_text_and_exact_selectors_are_rejected(self):
        bad = "bad " + chr(0xd800)
        self.study["title"] = bad
        self.write()
        self.assert_invalid("title: expected UTF-8")
        for changes in ({"label": bad}, {"where": {"metric_id": bad}}, {"artifact": bad + ".csv"}, {"columns": [bad]}):
            with self.subTest(changes=changes), self.assertRaisesRegex(NavigationMetadataError, "UTF-8"):
                validate_reference_shape(reference_record(**changes), ["01_synthetic"])

    def test_duplicate_study_and_strategy_ids(self):
        with self.assertRaisesRegex(NavigationMetadataError, "duplicate study_id"):
            validate_navigation(self.root, [self.study, copy.deepcopy(self.study)], [self.card])
        with self.assertRaisesRegex(NavigationMetadataError, "duplicate strategy_id"):
            validate_navigation(self.root, [self.study], [self.card, copy.deepcopy(self.card)])

    def test_associations_exist_without_requiring_symmetry(self):
        load_navigation(self.root)  # The card names the study, which names no card.
        self.study["strategy_ids"] = ["missing_card"]
        self.write()
        self.assert_invalid("unknown strategy_ids")
        self.study["strategy_ids"] = []
        self.card["study_ids"] = ["02_missing"]
        self.write()
        self.assert_invalid("unknown study_ids")

    def test_reference_is_explicit_and_latest_or_run_id_is_not_inferred(self):
        self.study.update(run_id="run10", latest_exploratory_run="run20")
        self.write()
        studies, _ = load_navigation(self.root)
        self.assertNotIn("reference_run", studies[0])
        self.study["reference_run"] = "run2"
        self.write()
        self.assert_invalid("reference_run")
        (self.root / "runs/01_synthetic/run2").mkdir(parents=True)
        studies, _ = load_navigation(self.root)
        self.assertEqual(studies[0]["reference_run"], "run2")

    def test_card_path_must_exist(self):
        (self.root / self.card["path"]).unlink()
        self.assert_invalid("strategy synthetic_card.path")

    def test_unsafe_paths_are_rejected_before_open(self):
        for locator in ("/tmp/card.md", "../card.md", "strategies//card.md", "strategies/./card.md", "strategies\\card.md", "file:card.md"):
            with self.subTest(locator=locator):
                self.card["path"] = locator
                write_file(self.root, "strategies/index.json", json.dumps({"strategies": [self.card]}))
                self.assert_invalid("path")

    def test_symlink_leaf_and_ancestor_are_rejected(self):
        outside = Path(self.temporary.name).parent / (self.root.name + "-outside")
        outside.mkdir()
        self.addCleanup(outside.rmdir)
        self.addCleanup(lambda: (outside / "card.md").unlink())
        (outside / "card.md").write_text("external", encoding="utf-8")
        card_path = self.root / self.card["path"]
        card_path.unlink()
        card_path.symlink_to(outside / "card.md")
        self.assert_invalid("symlink")
        card_path.unlink()
        alias = self.root / "alias"
        alias.symlink_to(outside, target_is_directory=True)
        self.card["path"] = "alias/card.md"
        write_file(self.root, "strategies/index.json", json.dumps({"strategies": [self.card]}))
        self.assert_invalid("symlink")

    def test_metadata_checks_reference_structure_without_hash_or_csv_reads(self):
        reference = reference_record()
        self.card["evidence_refs"] = [reference]
        write_file(self.root, "runs/01_synthetic/run2/tables/scores.csv", "not even CSV; wrong declared hash\n")
        self.write()
        with patch.object(Path, "read_bytes", side_effect=AssertionError("metadata must not read artifact bytes")):
            studies, cards = load_navigation(self.root)
        self.assertEqual(cards[0]["evidence_refs"], [reference])

    def test_reference_missing_local_targets_and_duplicate_ids(self):
        self.card["evidence_refs"] = [reference_record()]
        self.write()
        self.assert_invalid("run")
        write_file(self.root, "runs/01_synthetic/run2/tables/scores.csv")
        self.card["evidence_refs"].append(reference_record())
        self.write()
        self.assert_invalid("duplicate evidence reference ID")

    def test_reference_shape_preserves_blanks_and_rejects_malformed_fields(self):
        reference = reference_record(where={"blank": ""})
        validate_reference_shape(reference, ["01_synthetic"])
        for changes, message in (({"where": {"n": 1}}, "must be a string"), ({"columns": ["n", "n"]}, "duplicate"), ({"sha256": "x"}, "sha256"), ({"kind": "html_link"}, "kind"), ({"artifact": "../outside.csv"}, "artifact"), ({"study_id": "02_other"}, "outside"), ({"extra": False}, "unknown fields")):
            with self.subTest(changes=changes), self.assertRaisesRegex(NavigationMetadataError, message):
                validate_reference_shape(reference_record(**changes), ["01_synthetic"])

    def test_indicator_content_has_actual_links_and_no_required_market_products(self):
        self.study = study_record(content_kind="indicator_implementation", status="indicator_implementation", products=[], reference_run=None, implementation={"plan": "plan.md", "settings": "study.yaml", "inputs_lock": "inputs.lock.json", "source": "pine/prototype.pine"})
        for locator in self.study["implementation"].values():
            write_file(self.root, "studies/01_synthetic/" + locator)
        self.write()
        studies, _ = load_navigation(self.root)
        self.assertEqual(studies[0]["products"], [])
        (self.root / "studies/01_synthetic/pine/prototype.pine").unlink()
        self.assert_invalid("implementation.source")

    def test_unknown_content_kind_and_indicator_field_errors(self):
        self.study["content_kind"] = "automatically_verified_strategy"
        self.write()
        self.assert_invalid("unsupported content_kind")
        self.study["content_kind"] = "indicator_implementation"
        self.write()
        self.assert_invalid("implementation")

    def test_critical_failures_are_explicit_in_ordinary_and_optimized_cli(self):
        write_file(self.root, "strategies/index.json", '{"strategies": [], "strategies": []}')
        command = [str(SCRIPTS / "check-navigation-metadata.py"), "--root", str(self.root)]
        for optimize in ([], ["-O"]):
            result = subprocess.run([sys.executable] + optimize + command, cwd=self.root.parent, text=True, capture_output=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("duplicate", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
