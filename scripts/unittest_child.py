#!/usr/bin/env python3
"""Isolated unittest execution with an explicit machine-readable result channel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import traceback
import unittest


class ExecutionResult(unittest.TextTestResult):
    """Track successful execution to distinguish wholly skipped suites/subtests."""
    def __init__(self, *arguments):
        super().__init__(*arguments)
        self.successful_executions = 0

    def addSuccess(self, test):
        self.successful_executions += 1
        super().addSuccess(test)

    def addSubTest(self, test, subtest, error):
        if error is None:
            self.successful_executions += 1
        super().addSubTest(test, subtest, error)


def result_record(result, discovered, outcome):
    return {"schema_version": 1, "outcome": outcome,
            "successful_callbacks": getattr(result, "successful_executions", 0),
            "counts": {"discovered": discovered, "tests_run": result.testsRun,
                       "failures": len(result.failures), "errors": len(result.errors),
                       "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
                       "unexpected_successes": len(result.unexpectedSuccesses)},
            "skips": [{"test": test.id(), "reason": reason} for test, reason in result.skipped]}


def run_suite(selection, *, stream=None):
    stream = sys.stderr if stream is None else stream
    loader = unittest.TestLoader()
    result = unittest.TestResult()
    try:
        start = str(Path(selection["start_dir"]).resolve())
        if selection.get("names"):
            # Like discovery, allow sibling helper imports from the selected tests directory.
            sys.path.insert(0, start)
            suite = loader.loadTestsFromNames(selection["names"])
        else:
            suite = loader.discover(start, pattern=selection.get("pattern", "test*.py"))
        discovered = suite.countTestCases()
    except Exception:
        traceback.print_exc(file=stream)
        record = result_record(result, 0, "discovery_error")
        return 1, record
    if discovered == 0:
        print("Empty unittest discovery: no tests selected", file=stream)
        return 1, result_record(result, 0, "empty")
    # Retain the actual result object when interrupted midway through a test.
    def make_result(*arguments):
        nonlocal result
        result = ExecutionResult(*arguments)
        return result
    runner = unittest.TextTestRunner(stream=stream, verbosity=1, resultclass=make_result)
    try:
        runner.run(suite)
    except KeyboardInterrupt:
        return 130, result_record(result, discovered, "interrupted")
    outcome = "passed" if result.wasSuccessful() else "failed"
    if outcome == "passed" and result.testsRun == 0 and not result.skipped:
        outcome = "empty"
    elif (outcome == "passed" and result.skipped and not result.successful_executions
          and not result.expectedFailures):
        outcome = "all_skipped"
    return (0 if outcome == "passed" else 1), result_record(result, discovered, outcome)


def main(argv=None):
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--spec", required=True, help="Validated registry unittest selection JSON")
    arguments.add_argument("--result", type=Path, required=True, help="Private temporary result channel")
    options = arguments.parse_args(argv)
    try:
        selection = json.loads(options.spec)
        code, record = run_suite(selection)
    except (ValueError, TypeError, KeyError) as error:
        print("Invalid unittest selection: " + str(error), file=sys.stderr)
        return 2
    options.result.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
