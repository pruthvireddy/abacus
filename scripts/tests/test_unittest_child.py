"""Actual miniature unittest children; no workspace suite dispatch."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHILD = Path(__file__).resolve().parents[1] / "unittest_child.py"


class UnittestChildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tests = self.root / "tests"
        self.tests.mkdir()

    def run_fixture(self, source=None, *, names=None, pattern="test*.py", optimize=False):
        if source is not None:
            (self.tests / "test_fixture.py").write_text(source, encoding="utf-8")
        result_path = self.root / "result.json"
        selection = {"start_dir": str(self.tests), "pattern": pattern, "optimize": optimize}
        if names is not None:
            selection["names"] = names
        arguments = [sys.executable] + (["-O"] if optimize else []) + [
            "-B", str(CHILD), "--spec", json.dumps(selection), "--result", str(result_path)]
        execution = subprocess.run(arguments, cwd=str(self.root), shell=False,
                                   capture_output=True, text=True, timeout=10)
        self.assertTrue(result_path.exists(), execution.stderr)
        return execution, json.loads(result_path.read_text(encoding="utf-8"))

    def test_empty_discovery_fails_and_reports_zero(self):
        execution, result = self.run_fixture()
        self.assertEqual(execution.returncode, 1)
        self.assertEqual(result["outcome"], "empty")
        self.assertEqual(result["counts"]["tests_run"], 0)
        self.assertEqual(result["counts"]["discovered"], 0)
        self.assertIn("Empty unittest discovery", execution.stderr)

    def test_pass_and_mixed_skip_counts_and_reasons_come_from_result(self):
        execution, result = self.run_fixture('''import unittest
class Fixture(unittest.TestCase):
    def test_pass(self): self.assertEqual(2 + 2, 4)
    @unittest.skip("fixture unavailable")
    def test_skip(self): pass
    @unittest.expectedFailure
    def test_expected(self): self.assertEqual(1, 2)
''')
        self.assertEqual(execution.returncode, 0)
        self.assertEqual(result["outcome"], "passed")
        self.assertEqual(result["counts"], {"discovered": 3, "tests_run": 3, "failures": 0,
            "errors": 0, "skipped": 1, "expected_failures": 1, "unexpected_successes": 0})
        self.assertEqual(result["skips"], [{"test": "test_fixture.Fixture.test_skip", "reason": "fixture unavailable"}])
        self.assertIn("Ran 3 tests", execution.stderr)
        self.assertIn("skipped=1", execution.stderr)

    def test_fail_error_and_unexpected_success_fail(self):
        execution, result = self.run_fixture('''import unittest
class Fixture(unittest.TestCase):
    def test_fail(self): self.assertEqual(1, 2)
    def test_error(self): raise ValueError("fixture error")
    @unittest.expectedFailure
    def test_unexpected(self): pass
''')
        self.assertEqual(execution.returncode, 1)
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["counts"]["tests_run"], 3)
        self.assertEqual(result["counts"]["failures"], 1)
        self.assertEqual(result["counts"]["errors"], 1)
        self.assertEqual(result["counts"]["unexpected_successes"], 1)
        self.assertIn("fixture error", execution.stderr)

    def test_import_error_is_actual_failed_test_not_empty_or_success(self):
        execution, result = self.run_fixture('raise ImportError("fixture import failure")\n')
        self.assertEqual(execution.returncode, 1)
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["counts"]["tests_run"], 1)
        self.assertEqual(result["counts"]["errors"], 1)
        self.assertIn("fixture import failure", execution.stderr)

    def test_all_skipped_is_nonpassing(self):
        execution, result = self.run_fixture('''import unittest
@unittest.skip("all unavailable")
class Fixture(unittest.TestCase):
    def test_one(self): pass
    def test_two(self): pass
''')
        self.assertEqual(execution.returncode, 1)
        self.assertEqual(result["outcome"], "all_skipped")
        self.assertEqual(result["counts"]["tests_run"], 2)
        self.assertEqual(result["counts"]["skipped"], 2)

    def test_class_setup_skip_has_actual_zero_tests_run(self):
        execution, result = self.run_fixture('''import unittest
class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls): raise unittest.SkipTest("class unavailable")
    def test_one(self): pass
    def test_two(self): pass
''')
        self.assertEqual(execution.returncode, 1)
        self.assertEqual(result["outcome"], "all_skipped")
        self.assertEqual(result["counts"]["discovered"], 2)
        self.assertEqual(result["counts"]["tests_run"], 0)
        self.assertEqual(result["counts"]["skipped"], 1)
        self.assertEqual(result["skips"][0]["reason"], "class unavailable")

    def test_partly_skipped_subtests_are_not_entirely_skipped(self):
        execution, result = self.run_fixture('''import unittest
class Fixture(unittest.TestCase):
    def test_subtests(self):
        with self.subTest("unavailable"): self.skipTest("one unavailable")
        with self.subTest("available"): self.assertEqual(1, 1)
''')
        self.assertEqual(execution.returncode, 0)
        self.assertEqual(result["outcome"], "passed")
        self.assertEqual(result["counts"]["tests_run"], 1)
        self.assertEqual(result["counts"]["skipped"], 1)

    def test_discovery_exception_fails_with_no_invented_executions(self):
        missing = self.root / "missing"
        result_path = self.root / "result.json"
        execution = subprocess.run([sys.executable, "-B", str(CHILD), "--spec",
            json.dumps({"start_dir": str(missing), "pattern": "test*.py", "optimize": False}),
            "--result", str(result_path)], capture_output=True, text=True, timeout=10)
        self.assertEqual(execution.returncode, 1)
        result = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(result["outcome"], "discovery_error")
        self.assertEqual(result["counts"]["tests_run"], 0)

    def test_explicit_names_select_only_requested_test_and_support_helpers(self):
        (self.tests / "helper.py").write_text("VALUE = 4\n", encoding="utf-8")
        execution, result = self.run_fixture('''import unittest
from helper import VALUE
class Fixture(unittest.TestCase):
    def test_selected(self): self.assertEqual(VALUE, 4)
    def test_excluded(self): self.fail("must not execute")
''', names=["test_fixture.Fixture.test_selected"])
        self.assertEqual(execution.returncode, 0)
        self.assertEqual(result["counts"]["discovered"], 1)
        self.assertNotIn("must not execute", execution.stderr)

    def test_optimized_execution_is_real(self):
        execution, result = self.run_fixture('''import unittest
class Fixture(unittest.TestCase):
    def test_optimized(self): self.assertFalse(__debug__)
''', optimize=True)
        self.assertEqual(execution.returncode, 0)
        self.assertEqual(result["counts"]["tests_run"], 1)

    def test_keyboard_interrupt_records_partial_actual_result(self):
        execution, result = self.run_fixture('''import unittest
class Fixture(unittest.TestCase):
    def test_interrupt(self): raise KeyboardInterrupt
''')
        self.assertEqual(execution.returncode, 130)
        self.assertEqual(result["outcome"], "interrupted")
        self.assertEqual(result["counts"]["tests_run"], 1)


if __name__ == "__main__":
    unittest.main()
