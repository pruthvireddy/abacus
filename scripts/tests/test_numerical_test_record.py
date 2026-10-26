"""Disposable stdlib fixtures for stage-bound numerical evidence and legacy gates."""
from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import numerical_test_record as records


STUDY = "08_countertrend_bar_continuation"


def fixture(root, study=STUDY):
    root = Path(root).resolve()
    (root / "config").mkdir()
    registry = json.loads((SCRIPTS.parent / "config/workspace-checks.json").read_text())
    check_id = records.STUDIES[study][0]
    check = next(item for item in registry["checks"] if item["id"] == check_id)
    owner = {"kind": "study", "path": "studies/" + study, "study_id": study,
             "description": "Disposable numerical owner", "guides": ["studies/" + study + "/README.md"],
             "read_first": ["studies/" + study + "/README.md"], "entry_points": ["studies/" + study + "/tests"],
             "preservation": ["Synthetic fixture only"]}
    registry = {"schema_version": 1, "default_profile": "numerical", "owners": {check_id: owner},
                "profiles": {"numerical": {"description": "Disposable selection", "checks": [check_id]}}, "checks": [check]}
    (root / "config/workspace-checks.json").write_text(json.dumps(registry))
    for name in records.MECHANICS:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SCRIPTS.parent / name, target)
    # This fixture shim only launches installed system Python; it never uses UV,
    # research dependencies, package synchronization or retained market inputs.
    uv = root / "scripts/uv"
    uv.write_text("#!" + sys.executable + "\nimport os, sys\n"
                  "if sys.argv[1:5] != ['run', '--locked', '--no-sync', 'python']: raise SystemExit(2)\n"
                  "os.execv(sys.executable, [sys.executable, *sys.argv[5:]])\n")
    uv.chmod(0o755)
    owner = root / "studies" / study
    tests = owner / "tests"
    tests.mkdir(parents=True)
    (owner / "README.md").write_text("# Disposable numerical owner\n")
    (tests / "test_tiny.py").write_text("import unittest\nclass Tiny(unittest.TestCase):\n"
                                       "    def test_one(self): self.assertEqual(1 + 1, 2)\n"
                                       "    def test_two(self): self.assertTrue(True)\n")
    for name in records.STUDIES[study][1]:
        target = owner / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Declared synthetic numerical helper.\n")
    if study.startswith(("12_", "13_")):
        target = root / "packages/sahadeva/src/abacus_sahadeva/cooldown.py"
        target.parent.mkdir(parents=True)
        target.write_text("# Synthetic shared helper.\n")
    (root / "uv.lock").write_bytes(b"# Synthetic lock bytes, no environment claim.\n")
    stage = root / "work" / study / "20990101T000000Z_fixture"
    stage.mkdir(parents=True)
    return root, stage


def mutate_record(stage, callback):
    path = stage / records.RECORD_DIRECTORY / "record.json"
    record = json.loads(path.read_text())
    callback(record)
    path.write_text(json.dumps(record) + "\n")


def digest_tree(root):
    return {p.relative_to(root).as_posix(): records._sha(p.read_bytes())
            for p in root.rglob("*") if p.is_file() and not p.is_symlink()}


class NumericalRecordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root, self.stage = fixture(self.temp.name)

    def record(self, executor=None):
        return records.record_numerical_tests(self.stage, self.root, STUDY, executor=executor)

    def require(self):
        return records.require_numerical_record(self.stage, self.root, STUDY)

    def test_actual_child_counts_and_growth_without_literal_count(self):
        record = self.record()
        self.assertEqual(record["state"], "completed")
        self.assertEqual(record["child_result"]["counts"]["tests_run"], 2)
        self.assertEqual(self.require(), record)
        before = digest_tree(self.root)
        self.require()
        self.assertEqual(before, digest_tree(self.root))
        test = self.root / "studies" / STUDY / "tests/test_added.py"
        test.write_text("import unittest\nclass More(unittest.TestCase):\n    def test_more(self): pass\n")
        with self.assertRaisesRegex(records.NumericalRecordError, "inventory changed"):
            self.require()
        fresh = self.stage.parent / "20990101T000001Z_growth"
        fresh.mkdir()
        record = records.record_numerical_tests(fresh, self.root, STUDY)
        self.assertEqual(record["child_result"]["counts"]["tests_run"], 3)
        records.require_numerical_record(fresh, self.root, STUDY)

    def test_all_allowlisted_studies_have_exact_owned_selection(self):
        for study in tuple(records.STUDIES)[1:]:
            with self.subTest(study=study), tempfile.TemporaryDirectory() as directory:
                root, stage = fixture(directory, study)
                record = records.record_numerical_tests(stage, root, study)
                self.assertEqual(records.require_numerical_record(stage, root, study), record)

    def test_existing_evidence_and_known_recovery_are_preserved(self):
        self.record()
        before = digest_tree(self.root)
        with self.assertRaises(records.NumericalRecordError):
            self.record()
        self.assertEqual(before, digest_tree(self.root))
        recovery = self.stage.parent / "20990101T000002Z_recovery"
        recovery.mkdir()
        (recovery / "numerical-tests.part").write_text("diagnostic")
        with self.assertRaises(records.NumericalRecordError):
            records.record_numerical_tests(recovery, self.root, STUDY)
        self.assertEqual((recovery / "numerical-tests.part").read_text(), "diagnostic")
        self.assertFalse((recovery / "numerical-tests").exists())

    def test_missing_unknown_malformed_records_refuse(self):
        with self.assertRaises(records.NumericalRecordError):
            self.require()
        self.record()
        path = self.stage / "numerical-tests/record.json"
        original = path.read_bytes()
        for raw in (b"{}", b"{bad", b'{"contract":"x","contract":"y"}', b'{"bad":NaN}'):
            with self.subTest(raw=raw):
                path.write_bytes(raw)
                with self.assertRaises(records.NumericalRecordError):
                    self.require()
        path.write_bytes(original)
        mutate_record(self.stage, lambda r: r.update(contract="abacus.unknown/v1"))
        with self.assertRaises(records.NumericalRecordError):
            self.require()

    def test_wrong_study_stage_suite_selection_command_and_runtime_refuse(self):
        self.record()
        path = self.stage / "numerical-tests/record.json"
        original = path.read_bytes()
        mutations = (
            lambda r: r.update(study_id="09_range_xv_c2_confirmation"),
            lambda r: r.update(stage_id="copied-stage"),
            lambda r: r.update(stage_path="work/other/copied-stage"),
            lambda r: r.update(check_id="sahadeva"),
            lambda r: r["selection"].update(pattern="test_tiny.py"),
            lambda r: r["selection"].update(optimize=0),
            lambda r: r["argv"].append("--invented"),
            lambda r: r.update(cwd="/elsewhere"),
            lambda r: r["runtime"].update(optimize=1),
            lambda r: r["runtime"].update(optimize=False),
            lambda r: r["runtime"].update(argv=["fabricated"]),
            lambda r: r.update(completed_at="1900-01-01T00:00:00+00:00"),
            lambda r: r.update(started_at="2099-01-01T00:00:00"),
        )
        for mutate in mutations:
            path.write_bytes(original)
            mutate_record(self.stage, mutate)
            with self.subTest(mutation=mutate), self.assertRaises(records.NumericalRecordError):
                self.require()

    def test_inconsistent_success_callbacks_fail_even_with_rehashed_result(self):
        self.record()
        directory = self.stage / "numerical-tests"
        child = json.loads((directory / "child-result.json").read_text())
        child["successful_callbacks"] = 1
        (directory / "child-result.json").write_text(json.dumps(child) + "\n")
        mutate_record(self.stage, lambda r: r.update(
            child_result=child,
            child_result_file=records._identity(directory / "child-result.json", "child-result.json")))
        with self.assertRaisesRegex(records.NumericalRecordError, "without failures"):
            self.require()

    def test_negative_boolean_zero_and_inconsistent_counts_refuse(self):
        self.record()
        path = self.stage / "numerical-tests/record.json"
        original = path.read_bytes()
        # Bind loop values at construction, avoiding late-binding fixture mistakes.
        mutations = [lambda r, n=n, v=v: r["child_result"]["counts"].update({n: v})
                     for n, v in (("tests_run", True), ("tests_run", -1), ("tests_run", 0),
                                  ("discovered", 0), ("discovered", 3), ("failures", 1),
                                  ("errors", 1), ("skipped", 1), ("expected_failures", 1),
                                  ("unexpected_successes", 1))]
        mutations.extend((lambda r: r["child_result"].update(successful_callbacks=True),
                          lambda r: r["child_result"].update(successful_callbacks=0),
                          lambda r: r["child_result"].update(outcome="interrupted"),
                          lambda r: r["process"].update(exit_code=True),
                          lambda r: r["process"].update(exit_code=1),
                          lambda r: r["process"].update(interrupted=True),
                          lambda r: r.update(state="not_run")))
        for mutate in mutations:
            path.write_bytes(original)
            mutate_record(self.stage, mutate)
            with self.subTest(mutation=mutate), self.assertRaises(records.NumericalRecordError):
                self.require()

    def test_changed_log_lock_source_and_missing_retained_bytes_refuse(self):
        self.record()
        changes = ("scripts/unittest_child.py", "uv.lock",
                   "work/" + STUDY + "/" + self.stage.name + "/numerical-tests/log.txt",
                   "work/" + STUDY + "/" + self.stage.name + "/numerical-tests/uv.lock",
                   "work/" + STUDY + "/" + self.stage.name + "/numerical-tests/source-snapshot/scripts/uv")
        for name in changes:
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(path=name), self.assertRaises(records.NumericalRecordError):
                self.require()
            path.unlink()
            with self.subTest(missing=name), self.assertRaises(records.NumericalRecordError):
                self.require()
            path.write_bytes(original)

    def test_changed_sources_during_execution_fail_and_preserve_diagnostics(self):
        def executor(argv, cwd, environment, log):
            result = records._execute(argv, cwd, environment, log)
            (self.root / "studies" / STUDY / "src/engine.py").write_text("# changed during execution\n")
            return result
        record = self.record(executor)
        self.assertEqual(record["state"], "failed")
        self.assertTrue((self.stage / "numerical-tests/log.txt").is_file())
        with self.assertRaises(records.NumericalRecordError):
            self.require()

    def test_actual_zero_all_skipped_mixed_skipped_expected_failure_and_import_error(self):
        variants = {
            "empty": "# no tests\n",
            "all_skipped": "import unittest\n@unittest.skip('synthetic unavailable scope')\nclass Tiny(unittest.TestCase):\n    def test_skip(self): pass\n",
            "mixed": "import unittest\nclass Tiny(unittest.TestCase):\n    def test_pass(self): pass\n    @unittest.skip('synthetic unavailable scope')\n    def test_skip(self): pass\n",
            "expected": "import unittest\nclass Tiny(unittest.TestCase):\n    @unittest.expectedFailure\n    def test_known(self): self.fail('synthetic expected failure')\n",
            "import_error": "raise ImportError('synthetic import error')\n",
        }
        for name, source in variants.items():
            with self.subTest(variant=name), tempfile.TemporaryDirectory() as directory:
                root, stage = fixture(directory)
                (root / "studies" / STUDY / "tests/test_tiny.py").write_text(source)
                record = records.record_numerical_tests(stage, root, STUDY)
                self.assertEqual(record["state"], "failed")
                if name == "mixed":
                    self.assertEqual(record["process"]["exit_code"], 0)
                    self.assertEqual(record["child_result"]["outcome"], "passed")
                with self.assertRaises(records.NumericalRecordError):
                    records.require_numerical_record(stage, root, STUDY)

    def test_launch_failure_missing_observations_and_failure_no_overwrite(self):
        def missing(argv, cwd, environment, log):
            log.write_text("Synthetic child supplied no result channel\n")
            return {"exit_code": 0, "interrupted": False, "error": None}
        record = self.record(missing)
        self.assertEqual(record["state"], "failed")
        before = digest_tree(self.root)
        with self.assertRaises(records.NumericalRecordError):
            self.record()
        self.assertEqual(before, digest_tree(self.root))

    def test_broken_link_and_redirected_source_stage_or_destination_refuse(self):
        source = self.root / "studies" / STUDY / "src/engine.py"
        source.unlink()
        source.symlink_to(self.root / "missing-source")
        with self.assertRaises(records.NumericalRecordError):
            self.record()
        self.assertFalse((self.stage / "numerical-tests").exists())
        source.unlink()
        source.write_text("# restored synthetic source\n")
        directory = self.stage / "numerical-tests"
        directory.symlink_to(self.root / "missing-evidence")
        with self.assertRaises(records.NumericalRecordError):
            self.record()
        directory.unlink()
        outside = self.root / "outside"
        outside.mkdir()
        linked = self.stage.parent / "linked"
        linked.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(records.NumericalRecordError):
            records.record_numerical_tests(linked, self.root, STUDY)
        with self.assertRaisesRegex(records.NumericalRecordError, "original path traversal"):
            records.record_numerical_tests(linked / ".." / self.stage.name, self.root, STUDY)
        tests = self.root / "studies" / STUDY / "tests"
        (tests / "linked_helpers").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(records.NumericalRecordError):
            self.record()

    def test_interrupted_executor_uses_owned_process_cleanup(self):
        process = unittest.mock.Mock()
        process.wait.side_effect = KeyboardInterrupt()
        with patch.object(records.subprocess, "Popen", return_value=process) as launch, patch.object(records, "terminate_child") as cleanup:
            outcome = records._execute(["synthetic-command"], self.root, {}, self.stage / "interrupted-log.txt")
        cleanup.assert_called_once_with(process)
        self.assertEqual(launch.call_args.kwargs["start_new_session"], os.name == "posix")
        self.assertEqual(outcome["exit_code"], 130)
        self.assertIs(outcome["interrupted"], True)

    def test_retained_unsafe_path_boolean_size_and_part_refuse(self):
        self.record()
        path = self.stage / "numerical-tests/record.json"
        original = path.read_bytes()
        for mutate in (lambda r: r["log"].update(path="../focused-tests.log"),
                       lambda r: r["log"].update(bytes=True),
                       lambda r: r["retained_sources"][0].update(path="/absolute")):
            path.write_bytes(original)
            mutate_record(self.stage, mutate)
            with self.assertRaises(records.NumericalRecordError):
                self.require()
        path.write_bytes(original)
        recovery = self.stage / "numerical-tests/log.txt.part"
        recovery.write_text("diagnostic partial")
        with self.assertRaises(records.NumericalRecordError):
            self.require()
        self.assertEqual(recovery.read_text(), "diagnostic partial")

    def test_explicit_legacy_count_policy_and_adoption_cannot_fallback(self):
        log = self.stage / "focused-tests.log"
        log.write_text("Ran 8 tests\n\nOK\n")
        with self.assertRaises(records.NumericalRecordError):
            records.require_test_evidence(self.stage, self.root, STUDY)
        legacy = records.require_test_evidence(self.stage, self.root, STUDY, legacy_test_log=True)
        self.assertEqual(legacy["mode"], "legacy/log-only")
        self.assertEqual(legacy["source_binding"], "unbound")
        log.write_text("Ran 9 tests\n\nOK\n")
        with self.assertRaises(records.NumericalRecordError):
            records.require_test_evidence(self.stage, self.root, STUDY, legacy_test_log=True)
        log.write_text("Ran 8 tests\n\nOK\n")
        self.record()
        mutate_record(self.stage, lambda r: r.update(state="failed"))
        for legacy_mode in (False, True):
            with self.subTest(legacy=legacy_mode), self.assertRaises(records.NumericalRecordError):
                records.require_test_evidence(self.stage, self.root, STUDY, legacy_test_log=legacy_mode)


class SealerCompatibilityTests(unittest.TestCase):
    def sealer(self, root, study):
        spec = importlib.util.spec_from_file_location("sealer_" + study, SCRIPTS.parent / "studies" / study / "seal.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.__file__ = str(root / "studies" / study / "seal.py")
        return module

    def stage_evidence(self, root, stage, study, module):
        owner = root / "studies" / study
        for name in module.SOURCE_FILES:
            target = owner / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text("# Disposable source bytes\n")
        charts = {"synthetic_" + str(i): {"events": 1, "opportunities": 1, "ordinary_pairs": 1}
                  for i in range(7)}
        audit = {"charts": charts, "executed_at_utc": "2099-01-01T00:00:00+00:00", "verified_inputs": []}
        (stage / "audit.json").write_text(json.dumps(audit))
        (stage / "checks.json").write_text(json.dumps({"status": "pass", "verified_input_files": 34}))
        for name in ("config.json", "metrics.json", "report.md", "report.html", "advice.md"):
            (stage / name).write_text("{}")
        lock = {"manifest": {"sha256": "0" * 64}}
        if study.startswith("10_"):
            lock = {"source_runs": {}, "files": [{"role": "synthetic_events", "path": "saved/" + str(i)} for i in range(24)]}
        lock_bytes = json.dumps(lock).encode()
        (owner / "inputs.lock.json").write_bytes(lock_bytes)
        (stage / "inputs.lock.json").write_bytes(lock_bytes)
        (stage / "tables").mkdir()
        if study.startswith(("08_", "09_")):
            kinds = ("events",) if study.startswith("08_") else ("opportunities", "ordinary")
            for kind in kinds:
                for chart in charts:
                    (stage / "tables" / (kind + "_" + chart + ".parquet")).write_bytes(b"Synthetic ledger bytes; no market rows.\n")

    def test_all_three_sealers_accept_structured_records_with_growing_counts(self):
        for study in tuple(records.STUDIES)[:3]:
            with self.subTest(study=study), tempfile.TemporaryDirectory() as directory:
                root, stage = fixture(directory, study)
                module = self.sealer(root, study)
                self.stage_evidence(root, stage, study, module)
                record = records.record_numerical_tests(stage, root, study)
                self.assertEqual(record["child_result"]["counts"]["tests_run"], 2)
                with patch.object(module.subprocess, "check_output", return_value="a" * 40), patch.object(module.importlib.metadata, "version", return_value="fixture"), patch.object(module.platform, "platform", return_value="fixture"), contextlib.redirect_stdout(io.StringIO()):
                    module.main(["--stage", str(stage)])
                destination = root / "runs" / study / stage.name
                self.assertTrue(destination.is_dir())
                manifest = json.loads((destination / "manifest.json").read_text())
                self.assertEqual(manifest["numerical_test_evidence"]["mode"], "structured")
                self.assertEqual(manifest["numerical_test_evidence"]["counts"]["tests_run"], 2)
                self.assertEqual(manifest["test_log"], "numerical-tests/log.txt")
                self.assertFalse(stage.exists())

    def test_all_three_sealers_accept_only_explicit_legacy_and_label_it(self):
        for study in tuple(records.STUDIES)[:3]:
            with self.subTest(study=study), tempfile.TemporaryDirectory() as directory:
                root, stage = fixture(directory, study)
                module = self.sealer(root, study)
                self.stage_evidence(root, stage, study, module)
                count = "6" if study.startswith("10_") else "8"
                (stage / "focused-tests.log").write_text("Ran " + count + " tests\nOK\n")
                with patch.object(module.subprocess, "check_output", return_value="a" * 40), patch.object(module.importlib.metadata, "version", return_value="fixture"), patch.object(module.platform, "platform", return_value="fixture"), contextlib.redirect_stdout(io.StringIO()):
                    module.main(["--stage", str(stage), "--legacy-test-log"])
                manifest = json.loads((root / "runs" / study / stage.name / "manifest.json").read_text())
                self.assertEqual(manifest["numerical_test_evidence"]["mode"], "legacy/log-only")
                self.assertEqual(manifest["numerical_test_evidence"]["source_binding"], "unbound")

    def test_existing_and_redirected_destinations_refuse_before_stage_mutation(self):
        for kind in ("directory", "broken_link", "redirected_parent"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root, stage = fixture(directory)
                module = self.sealer(root, STUDY)
                self.stage_evidence(root, stage, STUDY, module)
                records.record_numerical_tests(stage, root, STUDY)
                destination = root / "runs" / STUDY / stage.name
                if kind == "redirected_parent":
                    (root / "outside").mkdir()
                    (root / "runs").symlink_to(root / "outside", target_is_directory=True)
                else:
                    destination.parent.mkdir(parents=True)
                    if kind == "directory":
                        destination.mkdir()
                    else:
                        destination.symlink_to(root / "missing-run")
                before = digest_tree(stage)
                with self.assertRaises(records.NumericalRecordError):
                    module.main(["--stage", str(stage)])
                self.assertEqual(before, digest_tree(stage))
                self.assertFalse((stage / "source-snapshot").exists())

    def test_late_source_lock_log_record_or_destination_changes_refuse_promotion(self):
        for study in tuple(records.STUDIES)[:3]:
            for changed in ("source", "lock", "log", "record", "destination"):
                with self.subTest(study=study, changed=changed), tempfile.TemporaryDirectory() as directory:
                    root, stage = fixture(directory, study)
                    module = self.sealer(root, study)
                    self.stage_evidence(root, stage, study, module)
                    records.record_numerical_tests(stage, root, study)
                    destination = root / "runs" / study / stage.name
                    original_write = Path.write_text

                    def late_change(path, content, *arguments, **keywords):
                        result = original_write(path, content, *arguments, **keywords)
                        if path == stage / "manifest.json":
                            if changed == "source":
                                original_write(root / "studies" / study / records.STUDIES[study][1][0], "# changed at seal\n")
                            elif changed == "lock":
                                original_write(root / "uv.lock", "# changed lock at seal\n")
                            elif changed == "log":
                                original_write(stage / "numerical-tests/log.txt", "changed log at seal\n")
                            elif changed == "record":
                                original_write(stage / "numerical-tests/record.json", '{"contract":"invalid"}\n')
                            else:
                                destination.mkdir(parents=True)
                        return result

                    with patch.object(Path, "write_text", late_change), patch.object(module.subprocess, "check_output", return_value="a" * 40), patch.object(module.importlib.metadata, "version", return_value="fixture"), patch.object(module.platform, "platform", return_value="fixture"), patch.object(module.os, "replace") as move:
                        with self.assertRaises((records.NumericalRecordError, ValueError)):
                            module.main(["--stage", str(stage)])
                    move.assert_not_called()
                    self.assertTrue(stage.is_dir())
                    self.assertTrue((stage / "manifest.json").is_file())
                    self.assertTrue((stage / "source-snapshot").is_dir())
                    if changed == "destination":
                        self.assertTrue(destination.is_dir())
                        self.assertEqual(list(destination.iterdir()), [])
                    else:
                        self.assertFalse((root / "runs").exists())

    def test_change_after_destination_parent_creation_is_rechecked(self):
        with tempfile.TemporaryDirectory() as directory:
            root, stage = fixture(directory)
            module = self.sealer(root, STUDY)
            self.stage_evidence(root, stage, STUDY, module)
            records.record_numerical_tests(stage, root, STUDY)
            destination = root / "runs" / STUDY / stage.name
            original_mkdir = Path.mkdir
            original_write = Path.write_text

            def change_after_parent(path, *arguments, **keywords):
                result = original_mkdir(path, *arguments, **keywords)
                if path == destination.parent:
                    original_write(stage / "numerical-tests/log.txt", "changed after creating parent\n")
                return result

            with patch.object(Path, "mkdir", change_after_parent), patch.object(module.subprocess, "check_output", return_value="a" * 40), patch.object(module.importlib.metadata, "version", return_value="fixture"), patch.object(module.platform, "platform", return_value="fixture"), patch.object(module.os, "replace") as move:
                with self.assertRaises(records.NumericalRecordError):
                    module.main(["--stage", str(stage)])
            move.assert_not_called()
            self.assertTrue(stage.is_dir())
            self.assertFalse(destination.exists())

    def test_all_three_sealers_refuse_missing_new_record_before_writes(self):
        for study in tuple(records.STUDIES)[:3]:
            with self.subTest(study=study), tempfile.TemporaryDirectory() as directory:
                root, stage = fixture(directory, study)
                owner = root / "studies" / study
                spec = importlib.util.spec_from_file_location("sealer_" + study, SCRIPTS.parent / "studies" / study / "seal.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                module.__file__ = str(owner / "seal.py")
                required = ("audit.json", "checks.json", "config.json", "inputs.lock.json", "metrics.json", "report.md", "report.html", "advice.md")
                for name in required:
                    (stage / name).write_text("{}")
                (stage / "audit.json").write_text(json.dumps({"charts": {str(i): {} for i in range(7)}}))
                (stage / "checks.json").write_text(json.dumps({"status": "pass", "verified_input_files": 34}))
                (stage / "focused-tests.log").write_text("Ran " + ("6" if study.startswith("10_") else "8") + " tests\nOK\n")
                before = digest_tree(root)
                with patch.object(module.os, "replace") as move, self.assertRaises(records.NumericalRecordError):
                    module.main(["--stage", str(stage)])
                move.assert_not_called()
                self.assertFalse((root / "runs").exists())
                self.assertEqual(before, digest_tree(root))
                (stage / "numerical-tests").mkdir()
                (stage / "numerical-tests/record.json").write_text('{"contract":"invalid"}')
                before = digest_tree(root)
                with self.assertRaises(records.NumericalRecordError):
                    module.main(["--stage", str(stage), "--legacy-test-log"])
                self.assertEqual(before, digest_tree(root))

    def test_study10_legacy_count_is_six_and_new_counts_are_not_fixed(self):
        study = "10_range_xv_session_overlay"
        with tempfile.TemporaryDirectory() as directory:
            root, stage = fixture(directory, study)
            log = stage / "focused-tests.log"
            log.write_text("Ran 8 tests\nOK\n")
            with self.assertRaises(records.NumericalRecordError):
                records.require_test_evidence(stage, root, study, legacy_test_log=True)
            log.write_text("Ran 6 tests\nOK\n")
            self.assertEqual(records.require_test_evidence(stage, root, study, legacy_test_log=True)["legacy_literal_count"], 6)
            records.record_numerical_tests(stage, root, study)
            evidence = records.require_test_evidence(stage, root, study)
            self.assertEqual(evidence["counts"]["tests_run"], 2)


if __name__ == "__main__":
    unittest.main()
