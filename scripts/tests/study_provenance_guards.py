"""Disposable Study 12/13 orchestration checks; no retained market inputs."""
from __future__ import annotations

import ast
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import study_provenance as provenance

OWNERS = sorted(provenance.STUDIES)


class StageFixture:
    def __init__(self, root, owner=OWNERS[0]):
        self.root, self.owner = root, owner
        self.stage = root / "work" / owner / "synthetic-run"
        source_names = set()
        for phase in provenance.PHASES:
            source_names.update(provenance.sources(root, owner, phase))
        source_names.update(f"studies/{owner}/{name}" for name in ("plan.md", "study.yaml", "inputs.lock.json"))
        source_names.add("uv.lock")
        for name in source_names:
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            original = ROOT / name
            destination.write_bytes(original.read_bytes() if original.is_file() else b"synthetic declared source\n")

    def outputs(self):
        for name in provenance.OUTPUTS[self.owner]:
            path = self.stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"{}\n" if name.endswith(".json") else b"synthetic table\n")

    def reports(self):
        for name in provenance.REPORTS:
            (self.stage / name).write_text("synthetic saved report\n")

    def checks(self):
        return {"status": "pass", ("statistic_cells" if self.owner.startswith("12_") else
                                  "baseline_cells_matching_sealed_study_12"): 595 if self.owner.startswith("12_") else 70}

    def phase(self, phase, callback):
        # An explicit injected ordinary-runtime fixture makes -O guard discovery
        # exercise ordinary record validation without pretending to run science.
        with patch.object(provenance.sys, "flags", SimpleNamespace(**{name: (0 if name == "optimize" else getattr(sys.flags, name)) for name in dir(sys.flags) if not name.startswith("_")})):
            return provenance.run_phase(self.root, self.owner, self.stage, phase, callback)

    def ready(self):
        self.phase("execution", self.outputs)
        self.phase("rendering", self.reports)
        self.phase("verification", self.checks)
        return self


class ProvenanceGuards(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.fixture = StageFixture(self.root)

    def test_valid_exact_phase_records_and_preflight(self):
        f = self.fixture.ready()
        with patch("numerical_test_record.require_numerical_record", return_value={"actual": "synthetic gate fixture"}) as numerical:
            result = provenance.preflight(f.root, f.stage, f.owner)
        numerical.assert_called_once_with(f.stage, f.root, f.owner)
        self.assertEqual(result["checks"]["statistic_cells"], 595)
        self.assertFalse((f.root / "runs").exists())
        execution = provenance.require_phase(f.root, f.stage, f.owner, "execution")
        for original, retained in zip(execution["original_sources"], execution["retained_sources"]):
            self.assertEqual((f.root / original["path"]).read_bytes(), (f.stage / retained["path"]).read_bytes())

    def test_both_scientific_cardinalities_are_required(self):
        for owner in OWNERS:
            with self.subTest(owner=owner), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve(), owner)
                f.phase("execution", f.outputs)
                f.phase("rendering", f.reports)
                invalid = f.checks()
                key = next(key for key in invalid if key != "status")
                invalid[key] -= 1
                with self.assertRaises(provenance.ProvenanceError):
                    f.phase("verification", lambda: invalid)
                self.assertFalse((f.stage / "checks.json").exists())

    def test_incomplete_execution_refuses_before_render_or_destinations(self):
        f = self.fixture
        def fail():
            f.outputs()
            raise RuntimeError("synthetic analytical failure")
        with self.assertRaises(RuntimeError):
            f.phase("execution", fail)
        self.assertEqual(provenance.read_json(f.stage / "provenance/execution/failed.json")["state"], "failed")
        with self.assertRaises(provenance.ProvenanceError):
            f.phase("rendering", f.reports)
        self.assertFalse((f.root / "runs").exists())
        self.assertTrue((f.stage / "tables/yearly.csv").exists())

    def test_source_changed_during_execution_cannot_complete(self):
        f = self.fixture
        def changed():
            f.outputs()
            (f.root / f"studies/{f.owner}/run.py").write_text("changed execution source")
        with self.assertRaises(provenance.ProvenanceError):
            f.phase("execution", changed)
        self.assertFalse((f.stage / "provenance/execution/completed.json").exists())
        self.assertTrue((f.stage / "provenance/execution/failed.json").exists())

    def test_rendering_source_and_input_change_are_failures(self):
        for target in ("source", "table"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve())
                f.phase("execution", f.outputs)
                def changed():
                    f.reports()
                    path = (f.root / f"studies/{f.owner}/render.py" if target == "source"
                            else f.stage / "tables/yearly.csv")
                    path.write_text("changed")
                with self.assertRaises(provenance.ProvenanceError):
                    f.phase("rendering", changed)
                self.assertFalse((f.stage / "provenance/rendering/completed.json").exists())

    def test_artifact_changed_during_verification_fails(self):
        f = self.fixture
        f.phase("execution", f.outputs)
        f.phase("rendering", f.reports)
        def changed():
            (f.stage / "report.md").write_text("changed during verifier")
            return f.checks()
        with self.assertRaises(provenance.ProvenanceError):
            f.phase("verification", changed)
        self.assertFalse((f.stage / "provenance/verification/completed.json").exists())

    def test_each_verified_artifact_is_rechecked_before_destination(self):
        names = provenance.OUTPUTS[self.fixture.owner] + provenance.REPORTS + ("checks.json",)
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve()).ready()
                (f.stage / name).write_text("changed after verification")
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.preflight(f.root, f.stage, f.owner, numerical=False)
                self.assertFalse((f.root / "runs").exists())

    def test_stale_source_settings_input_lock_and_environment_are_refused(self):
        names = ("run.py", "study.yaml", "inputs.lock.json", "plan.md")
        names = tuple(f"studies/{self.fixture.owner}/{name}" for name in names) + ("uv.lock",)
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve()).ready()
                (f.root / name).write_text("changed original bytes")
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.preflight(f.root, f.stage, f.owner, numerical=False)

    def test_missing_retained_source_or_lock_refuses(self):
        for name in ("uv.lock", f"studies/{self.fixture.owner}/run.py"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve()).ready()
                (f.stage / "provenance/execution/source" / name).unlink()
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.preflight(f.root, f.stage, f.owner, numerical=False)

    def test_missing_historical_records_are_not_synthesized(self):
        f = self.fixture
        f.stage.mkdir(parents=True)
        f.outputs(); f.reports()
        (f.stage / "checks.json").write_text(json.dumps(f.checks()))
        with self.assertRaises(provenance.ProvenanceError):
            provenance.preflight(f.root, f.stage, f.owner, numerical=False)
        self.assertFalse((f.stage / "provenance").exists())

    def test_malformed_failed_not_run_and_wrong_receipts_refuse(self):
        mutations = [lambda r: r.update(contract="unknown/v2"),
                     lambda r: r.update(status="not_run", reason="not executed"),
                     lambda r: r.update(status="failed"),
                     lambda r: r.update(study_id=OWNERS[1]),
                     lambda r: r.update(stage_id="other-run"),
                     lambda r: r["runtime"].update(optimization=True),
                     lambda r: r["runtime"].update(optimization=1),
                     lambda r: r["outcome"].update(exit_code=False),
                     lambda r: r["scientific_checks"].update(statistic_cells=True),
                     lambda r: r["artifacts"][0].update(bytes=True),
                     lambda r: r["artifacts"][0].update(path="../escape"),
                     lambda r: r.pop("retained_sources")]
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve()).ready()
                path = f.stage / "provenance/verification/completed.json"
                record = provenance.read_json(path)
                mutation(record)
                path.write_text(json.dumps(record))
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.preflight(f.root, f.stage, f.owner, numerical=False)
                self.assertFalse((f.root / "runs").exists())

    def test_duplicate_json_key_refuses(self):
        f = self.fixture.ready()
        path = f.stage / "provenance/verification/completed.json"
        path.write_text('{"contract":"a","contract":"b"}')
        with self.assertRaises(provenance.ProvenanceError):
            provenance.preflight(f.root, f.stage, f.owner, numerical=False)

    def test_start_receipt_command_runtime_and_scope_are_bound(self):
        mutations = [lambda r: r["command"].update(argv=["invented", "command"]),
                     lambda r: r["runtime"].update(version="invented Python version"),
                     lambda r: r["runtime"].update(executable=12),
                     lambda r: r.update(started_at_utc="today"),
                     lambda r: r.update(completed_at_utc="2000-01-01T00:00:00+00:00"),
                     lambda r: r.update(source_scope="invented scope")]
        for mutate in mutations:
            with self.subTest(mutation=mutate), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve()).ready()
                path = f.stage / "provenance/verification/completed.json"
                record = provenance.read_json(path)
                mutate(record)
                path.write_text(json.dumps(record))
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.preflight(f.root, f.stage, f.owner, numerical=False)

    def test_direct_verification_validation_requires_actual_scientific_pass(self):
        for change in ({"status": "failed"}, {"statistic_cells": True}, {"statistic_cells": 594}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve()).ready()
                path = f.stage / "provenance/verification/completed.json"
                record = provenance.read_json(path)
                record["scientific_checks"].update(change)
                path.write_text(json.dumps(record))
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.require_phase(f.root, f.stage, f.owner, "verification")

    def test_missing_or_tampered_start_record_refuses(self):
        for remove in (True, False):
            with self.subTest(remove=remove), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve()).ready()
                path = f.stage / "provenance/verification/started.json"
                if remove:
                    path.unlink()
                else:
                    path.write_text("{}")
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.preflight(f.root, f.stage, f.owner, numerical=False)

    def test_empty_dependencies_have_exact_list_type(self):
        for value in ({}, ""):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve())
                f.phase("execution", f.outputs)
                folder = f.stage / "provenance/execution"
                started = provenance.read_json(folder / "started.json")
                started["dependencies"] = value
                (folder / "started.json").write_text(json.dumps(started))
                completed = provenance.read_json(folder / "completed.json")
                completed["dependencies"] = value
                completed["started_record"] = provenance.identity(f.stage, "provenance/execution/started.json")
                (folder / "completed.json").write_text(json.dumps(completed))
                with self.assertRaises(provenance.ProvenanceError):
                    provenance.require_phase(f.root, f.stage, f.owner, "execution")

    def test_original_interpreter_switches_are_retained(self):
        f = self.fixture
        expected = [sys.executable, "-B", "-W", "ignore", "run.py", "--stage", str(f.stage)]
        with patch.object(sys, "orig_argv", expected):
            f.phase("execution", f.outputs)
        self.assertEqual(provenance.require_phase(f.root, f.stage, f.owner, "execution")["command"]["argv"], expected)

    def test_symlink_traversal_refuses_before_callback_or_new_stage(self):
        f = self.fixture
        outside = f.root / "outside"
        outside.mkdir()
        f.stage.parent.mkdir(parents=True)
        (f.stage.parent / "redirect").symlink_to(outside, target_is_directory=True)
        stage = f.stage.parent / "redirect" / ".." / f.stage.name
        callback = unittest.mock.Mock()
        with self.assertRaises(provenance.ProvenanceError):
            provenance.run_phase(f.root, f.owner, stage, "execution", callback)
        callback.assert_not_called()
        self.assertFalse(f.stage.exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_receipt_copy_to_another_stage_or_root_refuses(self):
        f = self.fixture.ready()
        for target in (f.stage.parent / "other-run", self.root / "other-root/work" / f.owner / f.stage.name):
            shutil.copytree(f.stage, target)
            other_root = f.root if target.name == "other-run" else self.root / "other-root"
            with self.assertRaises(provenance.ProvenanceError):
                provenance.preflight(other_root, target, f.owner, numerical=False)

    def test_existing_destination_and_broken_link_are_preserved(self):
        f = self.fixture.ready()
        destination = f.root / "runs" / f.owner / f.stage.name
        destination.parent.mkdir(parents=True)
        destination.symlink_to(f.root / "missing")
        with self.assertRaises(provenance.ProvenanceError):
            provenance.preflight(f.root, f.stage, f.owner, numerical=False)
        self.assertTrue(destination.is_symlink())
        destination.unlink(); destination.mkdir()
        with self.assertRaises(FileExistsError):
            provenance.preflight(f.root, f.stage, f.owner, numerical=False)
        self.assertTrue(destination.is_dir())

    def test_redirected_destination_ancestor_refuses(self):
        f = self.fixture.ready()
        outside = f.root / "outside"
        outside.mkdir()
        (f.root / "runs").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(provenance.ProvenanceError):
            provenance.preflight(f.root, f.stage, f.owner, numerical=False)
        self.assertEqual(list(outside.iterdir()), [])

    def test_redirected_source_and_stage_ancestors_refuse(self):
        f = self.fixture.ready()
        path = f.stage / "report.md"
        path.unlink(); path.symlink_to(f.stage / "advice.md")
        with self.assertRaises(provenance.ProvenanceError):
            provenance.preflight(f.root, f.stage, f.owner, numerical=False)
        link = f.root / "stage-alias"
        link.symlink_to(f.stage, target_is_directory=True)
        with self.assertRaises(provenance.ProvenanceError):
            provenance.require_phase(f.root, link, f.owner, "execution")

    def test_optimized_verification_refuses_before_callback(self):
        f = self.fixture
        f.phase("execution", f.outputs)
        f.phase("rendering", f.reports)
        callback = unittest.mock.Mock()
        with patch.object(provenance.sys, "flags", SimpleNamespace(**{name: (1 if name == "optimize" else getattr(sys.flags, name)) for name in dir(sys.flags) if not name.startswith("_")})):
            with self.assertRaises(provenance.ProvenanceError):
                provenance.run_phase(f.root, f.owner, f.stage, "verification", callback)
        callback.assert_not_called()
        self.assertFalse((f.stage / "provenance/verification").exists())

    def test_invalid_owned_numerical_gate_cannot_be_replaced_by_science(self):
        f = self.fixture.ready()
        from numerical_test_record import NumericalRecordError
        with patch("numerical_test_record.require_numerical_record", side_effect=NumericalRecordError("failed numerical record")):
            with self.assertRaises(NumericalRecordError):
                provenance.seal_stage(f.root, f.owner, f.stage, unittest.mock.Mock())
        self.assertFalse((f.root / "runs").exists())
        self.assertFalse((f.stage / "provenance/sealing").exists())

    def test_valid_synthetic_sealing_has_only_supported_actual_claims(self):
        f = self.fixture.ready()
        directory = f.stage / "numerical-tests"
        directory.mkdir(); (directory / "record.json").write_text('{"fixture":"passed numerical gate"}')
        with patch("numerical_test_record.require_numerical_record", return_value={"fixture": "synthetic numerical gate"}):
            destination = provenance.seal_stage(f.root, f.owner, f.stage, lambda stage: {"fixture": "retained synthetic events"})
        manifest = provenance.read_json(destination / "manifest.json")
        self.assertNotIn("verification_commands_passed", manifest)
        self.assertNotIn("workspace_gate_note", manifest)
        self.assertEqual({row["status"] for row in manifest["supplementary_checks"]}, {"not_run"})
        self.assertEqual(manifest["sealing_provenance"], "provenance/sealing/prepared.json")
        self.assertFalse(f.stage.exists())
        self.assertEqual((destination / "report.md").read_text(), "synthetic saved report\n")

    def test_failed_move_preserves_diagnostic_stage_and_failure_record(self):
        f = self.fixture.ready()
        directory = f.stage / "numerical-tests"
        directory.mkdir(); (directory / "record.json").write_text("{}")
        with patch("numerical_test_record.require_numerical_record", return_value={}), patch.object(Path, "rename", side_effect=OSError("synthetic move failed")):
            with self.assertRaises(OSError):
                provenance.seal_stage(f.root, f.owner, f.stage, lambda stage: {})
        self.assertTrue(f.stage.exists())
        record = provenance.read_json(f.stage / "provenance/sealing/failed.json")
        self.assertEqual(record["status"], "failed")
        self.assertTrue((f.stage / "manifest.json").exists())

    def test_last_artifact_recheck_precedes_completed_destination_creation(self):
        f = self.fixture.ready()
        directory = f.stage / "numerical-tests"
        directory.mkdir(); (directory / "record.json").write_text("{}")
        original_write = provenance.write_json
        def changed_at_manifest(path, value):
            original_write(path, value)
            if path.name == "manifest.json":
                (f.stage / "report.md").write_text("late changed report")
        with patch("numerical_test_record.require_numerical_record", return_value={}), patch.object(provenance, "write_json", changed_at_manifest):
            with self.assertRaises(provenance.ProvenanceError):
                provenance.seal_stage(f.root, f.owner, f.stage, lambda stage: {})
        self.assertFalse((f.root / "runs").exists())
        self.assertTrue((f.stage / "provenance/sealing/failed.json").exists())

    def test_phase_record_is_append_only(self):
        f = self.fixture
        f.phase("execution", f.outputs)
        first = (f.stage / "provenance/execution/completed.json").read_bytes()
        with self.assertRaises(FileExistsError):
            f.phase("execution", f.outputs)
        self.assertEqual((f.stage / "provenance/execution/completed.json").read_bytes(), first)


class StudyOrchestration(unittest.TestCase):
    def load(self, owner, filename):
        path = ROOT / "studies" / owner / filename
        spec = importlib.util.spec_from_file_location("synthetic_" + owner + filename.replace(".", "_"), path)
        module = importlib.util.module_from_spec(spec)
        saved = {name: value for name, value in sys.modules.items() if name == "src" or name.startswith("src.") or name == "run"}
        for name in list(saved):
            sys.modules.pop(name)
        sys.path.insert(0, str(path.parent))
        try:
            if filename == "verify.py" and owner.startswith("12_"):
                runner = self.load(owner, "run.py")
                sys.modules["run"] = runner
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(path.parent))
            for name in list(sys.modules):
                if name == "src" or name.startswith("src.") or name == "run":
                    sys.modules.pop(name)
            sys.modules.update(saved)
        return module

    def test_main_execution_stage_and_snapshot_precede_any_input_loading(self):
        for owner in OWNERS:
            module = self.load(owner, "run.py")
            with self.subTest(owner=owner), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve(), owner)
                module.__file__ = str(f.root / "studies" / owner / "run.py")
                calls = []
                def fake_execution(stage, study, root):
                    calls.append(stage)
                    self.assertTrue((stage / "provenance/execution/started.json").is_file())
                    self.assertTrue((stage / "provenance/execution/source/uv.lock").is_file())
                    f.outputs()
                with patch.object(module, "execute", fake_execution), patch.object(sys, "argv", ["run.py", "--stage", str(f.stage)]):
                    module.main()
                self.assertEqual(calls, [f.stage])
                self.assertEqual(provenance.require_phase(f.root, f.stage, owner, "execution")["state"], "completed")

    def test_12_direct_verifier_refuses_optimization_before_data(self):
        module = self.load(OWNERS[0], "verify.py")
        with patch.object(sys, "flags", SimpleNamespace(**{name: (1 if name == "optimize" else getattr(sys.flags, name)) for name in dir(sys.flags) if not name.startswith("_")})), patch.object(module.pd, "read_parquet") as read:
            with self.assertRaises(ValueError):
                module.verify(Path("does-not-exist"))
        read.assert_not_called()

    def test_verifier_main_retains_actual_callback_and_exact_scope(self):
        for owner in OWNERS:
            module = self.load(owner, "verify.py")
            with self.subTest(owner=owner), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve(), owner)
                f.phase("execution", f.outputs); f.phase("rendering", f.reports)
                module.__file__ = str(f.root / "studies" / owner / "verify.py")
                with patch.object(module, "verify", return_value=f.checks()), patch.object(sys, "flags", SimpleNamespace(**{name: (0 if name == "optimize" else getattr(sys.flags, name)) for name in dir(sys.flags) if not name.startswith("_")})), patch.object(sys, "argv", ["verify.py", "--stage", str(f.stage)]), contextlib.redirect_stdout(__import__("io").StringIO()):
                    module.main()
                receipt = provenance.require_phase(f.root, f.stage, owner, "verification")
                self.assertEqual(receipt["scientific_checks"], f.checks())
                self.assertIn("report.md", {row["path"] for row in receipt["artifacts"]})

    def report_tables(self, f):
        import pandas as pd
        f.outputs()
        if f.owner.startswith("12_"):
            rows = [{"year": year, "cooldown": cooldown, "horizon": horizon,
                     "raw_candidates": 4, "accepted_signals": 3, "valid_n": 2,
                     "mean_mae": 1.25, "p90_mae": 2., "mean_mfe": 2.5,
                     "p90_mfe": 3., "mean_terminal": .125,
                     "terminal_positive_rate": .5}
                    for year in range(2010, 2027) for cooldown in (0, 5, 10, 20, 30)
                    for horizon in (5, 10, 15, 20, 30, 50, 100)]
            pd.DataFrame(rows).to_csv(f.stage / "tables/yearly.csv", index=False, float_format="%.10f")
            (f.stage / "metrics.json").write_text('{"statistic_rows":595}')
        else:
            module = self.load(f.owner, "render.py")
            def row(rule, year, cooldown=10, horizon=20):
                return {"rule": rule, "year": year, "cooldown": cooldown, "horizon": horizon,
                        "raw_candidates": 4, "accepted_signals": 3, "valid_n": 2,
                        "mean_mae_points": 1.25, "mean_mfe_points": 2.5,
                        "mean_mae_sigma": .625, "mean_mfe_sigma": 1.25,
                        "mean_clipped_score": .625, "score_delta_vs_unfiltered": .25,
                        "score_delta_ci_low": -.125, "score_delta_ci_high": .5,
                        "terminal_positive_rate": .5}
            pd.DataFrame([row(rule, year) for rule in module.LABELS for year in (2025, 2026)]).to_csv(f.stage / "tables/primary.csv", index=False, float_format="%.10f")
            pd.DataFrame([row(rule, year, cooldown, horizon)
                          for rule in ("unfiltered", "upper_half_close") for year in (2025, 2026)
                          for cooldown in (0, 5, 10, 20, 30) for horizon in (5, 10, 15, 20, 30, 50, 100)]).to_csv(f.stage / "tables/sensitivity.csv", index=False, float_format="%.10f")
            (f.stage / "decision.json").write_text('{"selected_rule":"upper_half_close","eligible_training_rules":["upper_half_close"]}')

    def test_phase_wrapped_render_preserves_all_serialized_report_bytes(self):
        for owner in OWNERS:
            module = self.load(owner, "render.py")
            with self.subTest(owner=owner), tempfile.TemporaryDirectory() as directory:
                f = StageFixture(Path(directory).resolve(), owner)
                f.phase("execution", lambda: self.report_tables(f))
                expected = f.root / "plain-render"
                expected.mkdir()
                for name in provenance.OUTPUTS[owner]:
                    path = expected / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(f.stage / name, path)
                before = {name: (f.stage / name).read_bytes() for name in provenance.OUTPUTS[owner]}
                module._render(expected)
                module.__file__ = str(f.root / "studies" / owner / "render.py")
                module.render(f.stage)
                for name in provenance.REPORTS:
                    self.assertEqual((f.stage / name).read_bytes(), (expected / name).read_bytes())
                self.assertEqual(before, {name: (f.stage / name).read_bytes() for name in before})
                self.assertEqual(provenance.require_phase(f.root, f.stage, owner, "rendering")["state"], "completed")

    def test_12_wrapped_execution_preserves_synthetic_csv_json_parquet_bytes(self):
        import pandas as pd
        from datetime import datetime, timezone
        module = self.load(OWNERS[0], "run.py")
        with tempfile.TemporaryDirectory() as directory:
            f = StageFixture(Path(directory).resolve(), OWNERS[0])
            study = f.root / "studies" / f.owner
            lock = json.loads((study / "inputs.lock.json").read_text())
            pine = f.root / lock["pine_source"]["path"]
            pine.parent.mkdir(parents=True, exist_ok=True)
            pine.write_bytes((ROOT / lock["pine_source"]["path"]).read_bytes())
            raw = f.root / "plain-execution"
            raw.mkdir()
            bars = pd.DataFrame({"synthetic": [1, 2]})
            ledger = pd.DataFrame({"status": ["valid", "time_gap"], "mae_points": [1.25, None]})
            cohort = pd.DataFrame({"cooldown": [0], "accepted_signals": [2]})
            statistics = pd.DataFrame({"year": [2025, 2026], "mean_mae": [1.25, 2.5]})
            class Clock:
                @staticmethod
                def now(zone):
                    return datetime(2099, 1, 1, tzinfo=timezone.utc)
            with patch.object(module, "load_pinned", return_value=bars), patch.object(module, "analyze", return_value=(ledger, cohort)), patch.object(module, "summarize", return_value=statistics), patch.object(module, "datetime", Clock), contextlib.redirect_stdout(__import__("io").StringIO()):
                module.execute(raw, study, f.root)
                module.__file__ = str(study / "run.py")
                with patch.object(sys, "argv", ["run.py", "--stage", str(f.stage)]):
                    module.main()
            for name in provenance.OUTPUTS[f.owner]:
                self.assertEqual((raw / name).read_bytes(), (f.stage / name).read_bytes())

    def test_13_wrapped_execution_preserves_synthetic_csv_json_parquet_bytes(self):
        import pandas as pd
        from datetime import datetime, timezone
        module = self.load(OWNERS[1], "run.py")
        with tempfile.TemporaryDirectory() as directory:
            f = StageFixture(Path(directory).resolve(), OWNERS[1])
            study = f.root / "studies" / f.owner
            lock = json.loads((study / "inputs.lock.json").read_text())
            pine = f.root / lock["pine_source"]["path"]
            pine.parent.mkdir(parents=True, exist_ok=True)
            pine.write_bytes((ROOT / lock["pine_source"]["path"]).read_bytes())
            raw = f.root / "plain-execution"
            raw.mkdir()
            bars = pd.DataFrame({"synthetic": [1, 2]})
            stamps = ["2025-01-02T15:00:00+00:00", "2026-01-02T15:00:00+00:00"]
            context = pd.DataFrame({"bar_index": [0, 1], "signal_ts_utc": stamps,
                                    "year": [2025, 2026], **{rule: [True, True] for rule in module.FILTERS}})
            outcomes = pd.DataFrame([{"year": year, "cooldown": 0, "horizon": horizon,
                                      "signal_ts_utc": stamp, "status": "valid"}
                                     for year, stamp in zip((2025, 2026), stamps)
                                     for horizon in module.HORIZONS])
            events = f.root / lock["source_outcomes"]["event_ledger_path"]
            events.parent.mkdir(parents=True, exist_ok=True)
            outcomes.to_parquet(events, index=False)
            # The synthetic input identity is frozen before provenance capture.
            lock["source_outcomes"]["event_ledger_sha256"] = module.sha256(events)
            (study / "inputs.lock.json").write_text(json.dumps(lock, indent=2) + "\n")
            manifest = {"rows": 2, "product_year_quality": [{"product": "GC", "rows": 2}]}
            summary = {"valid_n": 50, "sessions": 25, "weeks": 12,
                       "mean_mae_sigma": .5, "mean_mfe_sigma": 1., "mean_clipped_score": 2.}
            class Clock:
                @staticmethod
                def now(zone):
                    return datetime(2099, 1, 1, tzinfo=timezone.utc)
            with patch.object(module, "verify_input", return_value=manifest), patch.object(module, "load_gc_5m_release", return_value=SimpleNamespace(to_pandas=lambda: bars.copy())), patch.object(module, "build_context", side_effect=lambda *_: context.copy()), patch.object(module, "accepted_context", side_effect=lambda frame, *_: frame.copy()), patch.object(module, "summarize", side_effect=lambda *_: dict(summary)), patch.object(module, "paired_week_bootstrap", return_value=(-.25, .5)), patch.object(module, "datetime", Clock), contextlib.redirect_stdout(__import__("io").StringIO()):
                module.execute(raw, study, f.root)
                module.__file__ = str(study / "run.py")
                with patch.object(sys, "argv", ["run.py", "--stage", str(f.stage)]):
                    module.main()
            for name in provenance.OUTPUTS[f.owner]:
                self.assertEqual((raw / name).read_bytes(), (f.stage / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
