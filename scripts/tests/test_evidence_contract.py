"""Synthetic future-bundle fixtures; no research imports or retained evidence reads."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
try:
    import evidence_contract as evidence
finally:
    sys.path.remove(str(SCRIPTS))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")


def inventory(root, names):
    return [{"path": name, "bytes": len((root / name).read_bytes()),
             "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()}
            for name in names]


def bundle(root, *, qualitative=False):
    files = {
        "settings.json": json.dumps({"observed": False, "undefined": None}),
        "inputs.lock.json": "{}", "exclusions.json": "[]", "uv.lock": "synthetic lock",
        "code-status.txt": " M synthetic.py\n", "source/synthetic.py": "# retained synthetic source\n",
        "check.log": "Synthetic recorded check; no computation.\n",
        "results.csv": "id,value\none,\n",
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    write_json(root / "commands.json", [{"argv": ["python3", "synthetic.py", "--fixture"],
                                       "cwd": ".", "environment": {"EXAMPLE": ""}}])
    write_json(root / "checks.json", [{"name": "synthetic fixture", "status": "passed", "record": "check.log"}])
    files.update({"commands.json": "", "checks.json": ""})
    manifest = {
        "contract": evidence.CONTRACT, "bundle_kind": "research", "study_id": "99_synthetic",
        "run_id": "synthetic_run", "inventory_scope": "declared_artifacts",
        "results": {"kind": "qualitative" if qualitative else "quantitative",
                    "state": "not_computed" if qualitative else "computed", "artifacts": ["results.csv"]},
        "provenance": {
            "settings": "settings.json", "input_lock": "inputs.lock.json", "exclusions": "exclusions.json",
            "commands": "commands.json", "checks": "checks.json", "environment_lock": "uv.lock",
            "code": {"revision": "a" * 40, "dirty": True, "status": "code-status.txt",
                     "source_snapshot": {"paths": ["source/synthetic.py"], "scope": "One authored synthetic file only."}},
        },
        "artifacts": inventory(root, files),
    }
    if qualitative:
        manifest["results"]["reason"] = "Authored qualitative review; market statistics were not computed."
        manifest["provenance"]["input_lock"] = {"state": "not_applicable", "reason": "Synthetic example has no market inputs."}
        manifest["provenance"]["exclusions"] = {"state": "not_applicable", "reason": "No numerical sample was assembled."}
    write_json(root / "manifest.json", manifest)
    return manifest


def tree(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file() and not path.is_symlink()}


class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name).resolve()
        self.root = self.parent / "bundle"
        self.root.mkdir()
        self.manifest = bundle(self.root)

    def save(self, manifest=None):
        write_json(self.root / "manifest.json", self.manifest if manifest is None else manifest)

    def invalid(self, mutate, phrase):
        value = copy.deepcopy(self.manifest)
        mutate(value)
        self.save(value)
        result = evidence.assess_bundle(self.root)
        self.assertEqual(result["status"], "invalid", result)
        self.assertIn(phrase, " ".join(result["errors"]))
        return result

    def test_valid_quantitative_bundle_is_read_only_and_scoped(self):
        (self.root / "undeclared.txt").write_text("not assessed")
        before = tree(self.root)
        result = evidence.assess_bundle(self.root)
        self.assertEqual(result["status"], "verified_declared_artifacts", result)
        self.assertTrue(result["metadata_valid"])
        self.assertEqual(result["local_artifacts_verified"], len(self.manifest["artifacts"]))
        self.assertEqual(result["inventory_scope"], "declared_artifacts")
        self.assertEqual(result["recorded_checks"], [{"name": "synthetic fixture", "status": "passed"}])
        self.assertEqual(tree(self.root), before)
        self.assertTrue(any("dependency completeness" in limit for limit in result["limits"]))

    def test_qualitative_bundle_without_market_input_or_trading_metrics(self):
        manifest = bundle(self.root, qualitative=True)
        result = evidence.assess_bundle(self.root / "manifest.json")
        self.assertEqual(result["status"], "verified_declared_artifacts", result)
        self.assertEqual(result["results"]["state"], "not_computed")
        self.assertEqual(result["results"]["artifacts"], ["results.csv"])
        self.assertNotIn("metrics", manifest)
        self.assertEqual(json.loads((self.root / "settings.json").read_text()), {"observed": False, "undefined": None})

    def test_historical_and_future_contracts_are_unsupported_without_artifact_reads(self):
        for value in ({"schema_version": 1, "artifacts": [{"path": "/must/not/read"}]},
                      {"contract": "abacus.evidence/v2", "artifacts": False},
                      {"schema_version": "qualitative-review-bundle-1"}):
            with self.subTest(value=value):
                self.save(value)
                with patch.object(evidence, "_verify_artifact", side_effect=AssertionError("must not inspect historical bytes")):
                    result = evidence.assess_bundle(self.root)
                self.assertEqual(result["status"], "unsupported", result)
                self.assertFalse(result["metadata_valid"])
                self.assertEqual(result["local_artifacts_verified"], 0)
                self.assertIn("not assessed", result["reason"])

    def test_missing_provenance_file_or_reference_is_not_certified(self):
        (self.root / "settings.json").unlink()
        result = evidence.assess_bundle(self.root)
        self.assertEqual(result["status"], "invalid", result)
        self.assertIn("settings.json", " ".join(result["errors"]))
        self.invalid(lambda m: m["provenance"].update(settings="unlisted.json"), "not inventoried")

    def test_dirty_code_requires_retained_source_bytes(self):
        (self.root / "source/synthetic.py").unlink()
        result = evidence.assess_bundle(self.root)
        self.assertEqual(result["status"], "invalid", result)
        self.assertIn("source/synthetic.py", " ".join(result["errors"]))
        self.invalid(lambda m: m["provenance"]["code"]["source_snapshot"].update(paths=[]), "nonempty")
        self.invalid(lambda m: m["provenance"]["code"].update(dirty=None), "null is not false")
        self.invalid(lambda m: m["provenance"]["code"].update(revision="HEAD"), "pinned")

    def test_hash_and_size_mismatches_are_distinct(self):
        (self.root / "results.csv").write_text("id,value\ntwo,\n")
        result = evidence.assess_bundle(self.root)
        self.assertEqual(result["status"], "invalid", result)
        self.assertIn("SHA-256 mismatch", " ".join(result["errors"]))
        (self.root / "results.csv").write_text("larger than declared bytes")
        self.assertIn("byte-size mismatch", " ".join(evidence.assess_bundle(self.root)["errors"]))

    def test_duplicate_keys_nonfinite_numbers_and_invalid_json(self):
        for text in ('{"contract":"abacus.evidence/v1","contract":"abacus.evidence/v1"}',
                     '{"contract":"abacus.evidence/v1","value":NaN}',
                     '{"contract":"abacus.evidence/v1","value":Infinity}',
                     '{"contract":"abacus.evidence/v1","value":1e999}', '{'):
            with self.subTest(text=text):
                (self.root / "manifest.json").write_text(text)
                result = evidence.assess_bundle(self.root)
                self.assertEqual(result["status"], "invalid", result)
                self.assertTrue(result["errors"])

    def test_duplicate_inventory_paths_bad_hashes_and_byte_size_types(self):
        self.invalid(lambda m: m["artifacts"].append(dict(m["artifacts"][0])), "duplicate artifact")
        for value in (True, False, -1, 2.0, "2", None):
            with self.subTest(value=value):
                self.invalid(lambda m: m["artifacts"][0].update(bytes=value), "byte size")
        for value in (None, "x" * 64, "a" * 63, "A" * 64):
            self.invalid(lambda m: m["artifacts"][0].update(sha256=value), "SHA-256")

    def test_unsafe_paths_are_rejected_before_artifact_open(self):
        for path in ("../outside", "/absolute", "a//b", "a/./b", "a/../b", "a\\b", "C:/x", "a/", "", "a?b", "a#b"):
            with self.subTest(path=path), patch.object(evidence, "_verify_artifact", side_effect=AssertionError("no byte reads")):
                self.invalid(lambda m: m["artifacts"][0].update(path=path), "path")

    def test_leaf_ancestor_internal_and_selected_symlinks_are_rejected(self):
        outside = self.parent / "outside.txt"
        outside.write_bytes((self.root / "results.csv").read_bytes())
        (self.root / "results.csv").unlink()
        (self.root / "results.csv").symlink_to(outside)
        result = evidence.assess_bundle(self.root)
        self.assertEqual(result["status"], "invalid", result)
        self.assertIn("symlink", " ".join(result["errors"]).lower())
        (self.root / "results.csv").unlink()
        (self.root / "results.csv").symlink_to("settings.json")
        self.assertIn("symlink", " ".join(evidence.assess_bundle(self.root)["errors"]).lower())
        source = self.root / "source"
        source.rename(self.parent / "outside_source")
        source.symlink_to(self.parent / "outside_source", target_is_directory=True)
        self.assertIn("symlink", " ".join(evidence.assess_bundle(self.root)["errors"]).lower())
        chosen = self.parent / "chosen.json"
        chosen.symlink_to(self.root / "manifest.json")
        self.assertIn("symlink", " ".join(evidence.assess_bundle(chosen)["errors"]).lower())

    def test_artifacts_must_be_ordinary_files(self):
        path = self.root / "results.csv"
        path.unlink()
        path.mkdir()
        self.assertEqual(evidence.assess_bundle(self.root)["status"], "invalid")

    def test_external_declarations_are_not_resolved(self):
        self.manifest["external_artifacts"] = [{"id": "retained-events", "locator": "/archived/unavailable/events.parquet",
                                                "bytes": 5, "sha256": "d" * 64}]
        self.save()
        result = evidence.assess_bundle(self.root)
        self.assertEqual(result["status"], "verified_declared_artifacts", result)
        self.assertFalse(result["external_artifacts"][0]["bytes_verified"])
        self.assertEqual(result["external_artifacts"][0]["locator"], "/archived/unavailable/events.parquet")
        self.invalid(lambda m: m["external_artifacts"][0].update(bytes=True), "byte size")
        self.invalid(lambda m: m["external_artifacts"].append(dict(m["external_artifacts"][0])), "duplicate external")

    def test_required_identity_provenance_result_and_scope_fields(self):
        self.invalid(lambda m: m.pop("provenance"), "missing fields")
        self.invalid(lambda m: m.update(study_id="../other"), "study identity")
        self.invalid(lambda m: m.update(run_id="../run"), "run identity")
        self.invalid(lambda m: m.update(inventory_scope="complete_bundle"), "declared_artifacts")
        self.invalid(lambda m: m["results"].update(state="not_computed"), "reason")
        self.invalid(lambda m: m["results"].update(state=False), "computed")
        self.invalid(lambda m: m["results"].update(artifacts=[]), "nonempty")
        self.invalid(lambda m: m["provenance"].update(exclusions={"state": "not_applicable", "reason": ""}), "reason")
        self.invalid(lambda m: m["artifacts"].append({"path": "manifest.json", "bytes": 0, "sha256": "e" * 64}), "own artifact")

    def rewrite_record(self, name, content):
        write_json(self.root / name, content)
        replacement = inventory(self.root, [name])[0]
        self.manifest["artifacts"] = [replacement if item["path"] == name else item for item in self.manifest["artifacts"]]
        self.save()

    def test_commands_are_recorded_never_executed_and_checks_are_not_revalidated(self):
        marker = self.parent / "must-not-exist"
        self.rewrite_record("commands.json", [{"argv": [sys.executable, "-c", f"open({str(marker)!r},'w').write('executed')"], "cwd": "."}])
        self.rewrite_record("checks.json", [{"name": "recorded failed check", "status": "failed", "record": "check.log"},
                                            {"name": "unavailable check", "status": "not_run", "reason": "Synthetic unavailable compiler"}])
        result = evidence.assess_bundle(self.root)
        self.assertEqual(result["status"], "verified_declared_artifacts", result)
        self.assertEqual(result["recorded_checks"][0]["status"], "failed")
        self.assertFalse(marker.exists())

    def test_recorded_empty_argument_is_preserved(self):
        self.rewrite_record("commands.json", [{"argv": ["python3", "-c", "", "argument with\nnewline"], "cwd": "."}])
        self.assertEqual(evidence.assess_bundle(self.root)["status"], "verified_declared_artifacts")

    def test_command_and_check_records_have_explicit_shape(self):
        self.rewrite_record("commands.json", [{"argv": [], "cwd": "."}])
        result = evidence.assess_bundle(self.root)
        self.assertIn("nonempty", " ".join(result["errors"]))
        self.assertFalse(result["metadata_valid"])
        self.rewrite_record("commands.json", [{"argv": ["python3"], "cwd": "."}])
        for record in ([{"name": "test", "status": "passed"}],
                       [{"name": "test", "status": "not_run"}],
                       [{"name": "test", "status": "passed", "record": "unlisted.log"}],
                       [{"name": "test", "status": True}]):
            self.rewrite_record("checks.json", record)
            self.assertEqual(evidence.assess_bundle(self.root)["status"], "invalid")

    def test_cli_outside_cwd_read_only_and_exit_codes(self):
        before = tree(self.root)
        command = [sys.executable, "-B", str(SCRIPTS / "check-evidence-bundle.py"), str(self.root), "--json"]
        completed = subprocess.run(command, cwd=self.parent, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["status"], "verified_declared_artifacts")
        self.assertEqual(tree(self.root), before)
        self.save({"schema_version": 1})
        self.assertEqual(subprocess.run(command, cwd=self.parent, capture_output=True).returncode, 2)
        self.save({"contract": evidence.CONTRACT})
        self.assertEqual(subprocess.run(command, cwd=self.parent, capture_output=True).returncode, 1)

    def test_critical_failures_under_optimized_python(self):
        for mutate in (lambda m: m["artifacts"][0].update(bytes=True),
                       lambda m: m["artifacts"][0].update(path="../outside"),
                       lambda m: m["provenance"]["code"].update(dirty=None),
                       lambda m: m["artifacts"][0].update(sha256="f" * 64)):
            value = copy.deepcopy(self.manifest)
            mutate(value)
            self.save(value)
            command = [sys.executable, "-O", "-B", str(SCRIPTS / "check-evidence-bundle.py"), str(self.root), "--json"]
            completed = subprocess.run(command, cwd=self.parent, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 1, completed.stderr + completed.stdout)
            self.assertEqual(json.loads(completed.stdout)["status"], "invalid")
            self.assertTrue(json.loads(completed.stdout)["errors"])


if __name__ == "__main__":
    unittest.main()
