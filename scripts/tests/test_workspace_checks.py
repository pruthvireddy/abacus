"""Orchestration fixtures use miniature repositories and injected children."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("workspace_checks", SCRIPTS / "workspace_checks.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def check(check_id, *, kind="command", runtime="standard-library", env=None, prerequisites=None,
          optimize=False, owner="workspace", cwd="."):
    record = {"id": check_id, "owner": owner, "kind": kind, "description": "Fixture check",
              "cwd": cwd, "env": env or {}, "prerequisites": prerequisites or [],
              "scope": ["Only the explicit fixture"]}
    if kind == "command":
        record["argv"] = ["{python}", "-c", "pass"]
    else:
        record.update(runtime=runtime, unittest={"start_dir": "tests", "pattern": "test*.py", "optimize": optimize})
    return record


def child_result(outcome="passed", *, tests=1, skips=0):
    return {"schema_version": 1, "outcome": outcome, "successful_callbacks": tests - skips,
            "counts": {"discovered": tests, "tests_run": tests,
                       "failures": 0, "errors": 0, "skipped": skips,
                       "expected_failures": 0, "unexpected_successes": 0},
            "skips": [{"test": "fixture.test_{}".format(index), "reason": "fixture skip"} for index in range(skips)]}


class WorkspaceChecksTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = (Path(self.temporary.name) / "repo").resolve()
        self.root.mkdir()
        (self.root / "tests").mkdir()
        (self.root / "scripts").mkdir()
        (self.root / "README.md").write_text("# Fixture\n", encoding="utf-8")
        (self.root / "scripts/check-workspace").write_text("fixture\n", encoding="utf-8")
        self.checks = [check("one"), check("two")]
        self.registry = {"schema_version": 1, "default_profile": "default",
            "profiles": {"default": {"description": "Default fixture", "checks": ["one", "two"]}},
            "owners": {"workspace": {"kind": "workspace", "path": ".", "description": "Fixture owner",
                "guides": ["README.md"], "read_first": ["README.md"], "entry_points": ["scripts/check-workspace"],
                "preservation": ["No evidence writes"]}}, "checks": self.checks}
        self.output = io.StringIO()

    def fake_child(self, *, code=0, result=None, interrupted=False):
        def execute(argv, cwd, environment, result_path):
            if result_path is not None and result is not None:
                result_path.write_text(json.dumps(result), encoding="utf-8")
            return {"exit_code": code, "interrupted": interrupted}
        return Mock(side_effect=execute)

    def run_checks(self, *, selection=None, executor=None, prerequisite_checker=None, **kwargs):
        return runner.run_checks(self.registry, selection or self.checks, self.root,
            executor=executor or self.fake_child(),
            prerequisite_checker=prerequisite_checker or (lambda *_args, **_kwargs: []),
            output=self.output, **kwargs)

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file()}

    def test_default_six_step_order_and_legacy_environment(self):
        identifiers = ["docs", "bhishma", "sahadeva", "legacy-01", "legacy-02", "doctor"]
        records = [check(identifier) for identifier in identifiers]
        for number in (3, 4):
            records[number]["env"] = {"PYTHONPATH": "{{root}}/legacy/{}/src".format(number)}
        self.registry["checks"] = records
        self.registry["profiles"]["default"]["checks"] = identifiers
        executor = self.fake_child()
        parent_environment = {"PATH": "/fixture/bin", "PYTHONPATH": "/parent/not/merged"}
        summary = self.run_checks(selection=runner.registry_api().select_checks(self.registry), executor=executor,
                                  environ=parent_environment)
        self.assertEqual(summary["selection"], identifiers)
        self.assertEqual(executor.call_count, 6)
        environments = [call.args[2] for call in executor.call_args_list]
        self.assertEqual(environments[3]["PYTHONPATH"], str(self.root / "legacy/3/src"))
        self.assertEqual(environments[4]["PYTHONPATH"], str(self.root / "legacy/4/src"))
        self.assertEqual(environments[5]["PYTHONPATH"], "/parent/not/merged")
        self.assertEqual(parent_environment["PYTHONPATH"], "/parent/not/merged")
        self.assertIsNot(environments[0], environments[1])

    def test_repeated_selection_deduplicates_in_stable_registry_order(self):
        selected = runner.registry_api().select_checks(self.registry, profiles=["default", "default"],
                                                        checks=["two", "one", "two"])
        self.assertEqual([record["id"] for record in selected], ["one", "two"])

    def test_unknown_and_empty_selection_rejected(self):
        for profiles, checks in [(["unknown"], []), ([], ["unknown"]), ([], [])]:
            with self.subTest(profiles=profiles, checks=checks), self.assertRaises(ValueError):
                runner.registry_api().select_checks(self.registry, profiles=profiles, checks=checks, use_default=False)

    def test_command_nonzero_is_not_test_success_and_failfast_marks_remaining(self):
        executor = self.fake_child(code=7)
        summary = self.run_checks(executor=executor)
        self.assertEqual(summary["exit_code"], 7)
        self.assertEqual([record["outcome"] for record in summary["checks"]], ["failed", "not_run"])
        self.assertEqual(executor.call_count, 1)
        self.assertIsNone(summary["checks"][0]["unittest"])
        self.assertIsNone(summary["checks"][1]["exit_code"])
        self.assertEqual(summary["checks"][1]["duration_seconds"], 0.0)

    def test_missing_required_prerequisites_do_not_start_child_or_pass(self):
        executor = self.fake_child()
        summary = self.run_checks(executor=executor, prerequisite_checker=lambda *_args, **_kwargs: ["clang++ unavailable"])
        executor.assert_not_called()
        self.assertEqual(summary["exit_code"], 1)
        self.assertEqual(summary["checks"][0]["outcome"], "prerequisite_missing")
        self.assertEqual(summary["checks"][0]["missing_prerequisites"], ["clang++ unavailable"])

    def test_failed_process_launch_is_structured_failure(self):
        summary = self.run_checks(executor=Mock(side_effect=FileNotFoundError("fixture executable")))
        self.assertEqual(summary["checks"][0]["outcome"], "failed")
        self.assertEqual(summary["exit_code"], 1)
        self.assertIn("fixture executable", summary["checks"][0]["reason"])

    def test_unittest_counts_use_private_channel_and_temporary_file_is_removed(self):
        selected = [check("suite", kind="unittest")]
        executor = self.fake_child(result=child_result(tests=3, skips=1))
        summary = self.run_checks(selection=selected, executor=executor)
        record = summary["checks"][0]
        self.assertEqual(record["outcome"], "passed")
        self.assertEqual(record["unittest"]["counts"]["tests_run"], 3)
        self.assertEqual(record["unittest"]["skips"][0]["reason"], "fixture skip")
        self.assertFalse(executor.call_args.args[3].exists())
        self.assertFalse(executor.call_args.args[3].parent.exists())
        self.assertEqual(record["argv"], executor.call_args.args[0])
        self.assertEqual(record["owner"], "workspace")
        self.assertGreaterEqual(record["duration_seconds"], 0)

    def test_zero_exit_with_missing_or_malformed_result_fails(self):
        invalid_boolean = dict(child_result(), schema_version=True)
        invalid_all_skipped = child_result(skips=1)
        for result in (None, [], {"schema_version": 0}, child_result(tests=0), invalid_boolean, invalid_all_skipped):
            with self.subTest(result=result):
                summary = self.run_checks(selection=[check("suite", kind="unittest")],
                                          executor=self.fake_child(result=result))
                self.assertEqual(summary["checks"][0]["outcome"], "failed")
                self.assertEqual(summary["exit_code"], 1)

    def test_partly_skipped_subtest_result_remains_passing(self):
        result = dict(child_result(skips=1), successful_callbacks=1)
        summary = self.run_checks(selection=[check("suite", kind="unittest")],
                                  executor=self.fake_child(result=result))
        self.assertEqual(summary["outcome"], "passed")
        self.assertEqual(summary["checks"][0]["unittest"]["counts"]["skipped"], 1)

    def test_all_skipped_does_not_become_passed_even_if_child_returns_zero(self):
        summary = self.run_checks(selection=[check("suite", kind="unittest")],
            executor=self.fake_child(result=child_result("all_skipped", skips=1)))
        self.assertEqual(summary["checks"][0]["outcome"], "all_skipped")
        self.assertEqual(summary["exit_code"], 1)

    def test_interruption_failfast_and_temporary_cleanup(self):
        executor = self.fake_child(code=130, interrupted=True)
        selected = [check("suite", kind="unittest"), check("later")]
        summary = self.run_checks(selection=selected, executor=executor)
        self.assertEqual(summary["outcome"], "interrupted")
        self.assertEqual(summary["exit_code"], 130)
        self.assertEqual(summary["checks"][1]["outcome"], "not_run")
        self.assertFalse(executor.call_args.args[3].parent.exists())

    def test_locked_and_optimized_dispatch_do_not_sync(self):
        ordinary = check("ordinary", kind="unittest", runtime="locked-python")
        optimized = check("optimized", kind="unittest", runtime="locked-python", optimize=True)
        arguments = runner.build_command(ordinary, self.root)
        self.assertEqual(arguments[:5], [str(self.root / "scripts/uv"), "run", "--locked", "--no-sync", "python"])
        self.assertNotIn("-O", arguments)
        self.assertIn("-O", runner.build_command(optimized, self.root))
        standard = runner.build_command(check("tooling", kind="unittest"), self.root)
        self.assertEqual(standard[0], sys.executable)
        self.assertNotIn("uv", standard)
        selection = json.loads(arguments[arguments.index("--spec") + 1])
        self.assertEqual(selection["start_dir"], str(self.root / "tests"))

    def test_list_dryrun_context_are_readonly_without_prerequisite_probes(self):
        before = self.snapshot()
        for arguments in (["--list"], ["--dry-run"], ["--context", "workspace"]):
            with self.subTest(arguments=arguments), patch.object(runner, "missing_prerequisites", side_effect=AssertionError("probe")), patch.object(runner.subprocess, "Popen", side_effect=AssertionError("execute")), redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(runner.main(arguments, root=self.root, registry=self.registry,
                                             executor=Mock(side_effect=AssertionError("execute"))), 0)
                self.assertIn("workspace", stdout.getvalue())
        self.assertEqual(before, self.snapshot())

    def test_context_unknown_fails_and_context_has_boundaries_not_guide_contents(self):
        with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(runner.main(["--context", "unknown"], root=self.root, registry=self.registry), 2)
        self.assertIn("unknown context", stderr.getvalue())
        with redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(runner.main(["--context", "workspace"], root=self.root, registry=self.registry), 0)
        self.assertIn("README.md", stdout.getvalue())
        self.assertIn("No evidence writes", stdout.getvalue())
        self.assertNotIn("# Fixture", stdout.getvalue())

    def test_report_persists_only_explicit_execution_path(self):
        executor = self.fake_child()
        before = self.snapshot()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main([], root=self.root, registry=self.registry, executor=executor), 0)
        self.assertEqual(before, self.snapshot())
        path = self.root / "explicit-summary.json"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(["--report", str(path)], root=self.root,
                                         registry=self.registry, executor=executor), 0)
        summary = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(summary["schema_version"], 1)
        self.assertEqual(summary["requested"], {"profiles": ["default"], "checks": []})
        self.assertEqual(summary["selection"], ["one", "two"])
        self.assertEqual(summary["checks"][0]["argv"], [sys.executable, "-c", "pass"])
        self.assertNotIn("PATH", path.read_text(encoding="utf-8"))
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            runner.main(["--dry-run", "--report", str(self.root / "must-not-exist")], root=self.root, registry=self.registry)
        self.assertFalse((self.root / "must-not-exist").exists())

    def test_executable_path_node_and_preview_prerequisites(self):
        selected = check("tools", prerequisites=[
            {"kind": "executable", "name": "ruby", "description": "Ruby required"},
            {"kind": "file", "path": "retained.csv", "description": "Retained fixture required"},
            {"kind": "node-major", "major": 24, "description": "Node 24"},
            {"kind": "argument", "name": "preview_origin", "description": "Running preview"},
            {"kind": "note", "description": "No private config reading"}])
        probe = Mock(return_value=subprocess.CompletedProcess(["node"], 0, stdout="v26.1.0\n"))
        missing = runner.missing_prerequisites(selected, self.root, environ={"PATH": "/fixture"},
            which=lambda name, **_kwargs: "/fixture/node" if name == "node" else None, probe=probe)
        self.assertEqual(len(missing), 4)
        probe.assert_called_once()
        self.assertFalse(probe.call_args.kwargs["shell"])
        for origin in ("http://127.0.0.1:4173", "http://localhost:4173", "http://[::1]:4173"):
            self.assertTrue(runner.valid_preview_origin(origin), origin)
        for origin in (None, "https://localhost:4173", "http://user@localhost:4173", "http://example.com:4173",
                       "http://127.0.0.1:4173/", "http://127.0.0.1:4173?secret", "http://127.0.0.1"):
            self.assertFalse(runner.valid_preview_origin(origin), origin)

    def test_locked_prerequisites_accept_local_uv_without_executing_it(self):
        local = self.root / ".tools/uv/bin/uv"
        local.parent.mkdir(parents=True)
        local.write_text("#!/bin/sh\nexit 91\n", encoding="utf-8")
        local.chmod(0o755)
        python = self.root / ".venv/bin/python"
        python.parent.mkdir(parents=True)
        python.write_text("fixture\n", encoding="utf-8")
        selected = check("suite", kind="unittest", runtime="locked-python")
        self.assertEqual(runner.missing_prerequisites(selected, self.root,
            which=lambda *_args, **_kwargs: None, probe=Mock(side_effect=AssertionError("execute"))), [])

    def test_popen_receives_array_no_shell_and_owns_child_group(self):
        process = Mock()
        process.wait.return_value = 0
        with patch.object(runner.subprocess, "Popen", return_value=process) as popen:
            result = runner.execute_child([sys.executable, "-c", "pass"], self.root, {"PATH": "/fixture"})
        self.assertEqual(result, {"exit_code": 0, "interrupted": False})
        self.assertEqual(popen.call_args.args[0], [sys.executable, "-c", "pass"])
        self.assertFalse(popen.call_args.kwargs["shell"])
        self.assertEqual(popen.call_args.kwargs["start_new_session"], os.name == "posix")

    @unittest.skipUnless(os.name == "posix", "POSIX process-group cleanup fixture")
    def test_cleanup_kills_descendants_after_leader_exits(self):
        process = Mock(pid=43210)
        process.poll.return_value = None
        process.wait.return_value = -signal.SIGTERM
        with patch.object(runner.os, "killpg") as kill_group:
            runner.terminate_child(process)
        self.assertEqual(kill_group.call_args_list[0].args, (43210, signal.SIGTERM))
        self.assertEqual(kill_group.call_args_list[1].args, (43210, signal.SIGKILL))
        process.wait.assert_called_once_with(timeout=3)

    @unittest.skipUnless(os.name == "posix", "POSIX process-group cleanup fixture")
    def test_cleanup_signals_group_even_if_leader_already_exited(self):
        process = Mock(pid=43210)
        process.poll.return_value = 0
        process.wait.return_value = 0
        with patch.object(runner.os, "killpg") as kill_group:
            runner.terminate_child(process)
        self.assertEqual([call.args for call in kill_group.call_args_list],
                         [(43210, signal.SIGTERM), (43210, signal.SIGKILL)])
        process.wait.assert_called_once_with(timeout=3)

    @unittest.skipUnless(os.name == "posix", "POSIX process-group cleanup fixture")
    def test_actual_child_is_reaped_on_interrupt(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"], start_new_session=True)
        original_wait = process.wait
        first = True
        def wait(*arguments, **keywords):
            nonlocal first
            if first:
                first = False
                raise KeyboardInterrupt
            return original_wait(*arguments, **keywords)
        try:
            with patch.object(runner.subprocess, "Popen", return_value=process), patch.object(process, "wait", side_effect=wait):
                result = runner.execute_child(["owned-fixture"], self.root, {})
            self.assertEqual(result, {"exit_code": 130, "interrupted": True})
            self.assertIsNotNone(process.poll())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            original_wait()

    def test_two_owned_suites_execute_in_fresh_processes_despite_shared_module_names(self):
        (self.root / "scripts/unittest_child.py").write_bytes((SCRIPTS / "unittest_child.py").read_bytes())
        records = []
        for index, value in enumerate(("first", "second")):
            directory = self.root / ("suite-" + str(index))
            directory.mkdir()
            (directory / "generic.py").write_text("VALUE = {!r}\n".format(value), encoding="utf-8")
            (directory / "test_engine.py").write_text('import unittest\nfrom generic import VALUE\nclass Engine(unittest.TestCase):\n    def test_identity(self): self.assertEqual(VALUE, {!r})\n'.format(value), encoding="utf-8")
            record = check("suite-" + str(index), kind="unittest")
            record["unittest"]["start_dir"] = directory.name
            records.append(record)
        summary = self.run_checks(selection=records, executor=runner.execute_child)
        self.assertEqual(summary["outcome"], "passed")
        self.assertEqual([record["unittest"]["counts"]["tests_run"] for record in summary["checks"]], [1, 1])

    def test_wrapper_help_from_unrelated_cwd_needs_no_uv_node_or_workspace_writes(self):
        before = self.snapshot()
        environment = dict(os.environ, ABACUS_CHECK_PYTHON=sys.executable, PATH="/unavailable")
        execution = subprocess.run(["/bin/sh", str(SCRIPTS / "check-workspace"), "--help"],
            cwd=str(self.root), env=environment, shell=False, text=True, capture_output=True, timeout=10)
        self.assertEqual(execution.returncode, 0, execution.stderr)
        self.assertIn("--context", execution.stdout)
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
