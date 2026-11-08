"""Numerical edge cases against the actual authored V2 notebook functions."""
import ast
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

NOTEBOOK = Path(__file__).resolve().parents[1] / "vern-pivot-cross-statistics.ipynb"


def authored_function(insight_id, name):
    notebook = json.loads(NOTEBOOK.read_text())
    functions = []
    for cell in notebook["cells"]:
        metadata = cell.get("metadata", {}).get("abacus", {})
        if metadata.get("insight_id") == insight_id and metadata.get("role") == "analysis":
            source = cell["source"] if isinstance(cell["source"], str) else "".join(cell["source"])
            functions.extend(node for node in ast.parse(source).body
                             if isinstance(node, ast.FunctionDef) and node.name == name)
    if len(functions) != 1:
        raise ValueError("Expected one numerical function in the authored analysis cell")
    namespace = {"pd": pd, "np": np}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(NOTEBOOK), "exec"), namespace)
    return namespace[name]


class NotebookV2AnalysisTests(unittest.TestCase):
    def test_frozen_cross_count_categories_keep_missing_distinct_from_zero(self):
        bucket = authored_function("count-distribution", "crossing_bucket")
        self.assertEqual([bucket(value) for value in (0, 1, 2, 3, 4, 5, 10)],
                         ["0", "1", "2", "3–4", "3–4", "5+", "5+"])
        self.assertIsNone(bucket(None))
        self.assertIsNone(bucket(np.nan))
        self.assertIsNone(bucket(-1))

    def test_no_recross_requires_complete_window_even_if_reverse_already_observed(self):
        summarize = authored_function("ema-recross", "no_recross_summary")
        rows = pd.DataFrame({"valid": [True, True, False, False],
                             "no_recross": [True, False, False, None],
                             "session_date": ["a", "a", "b", "c"]})
        result = summarize(rows)
        self.assertEqual(result, {"denominator": 2, "numerator": 1, "days": 1, "censored": 2})

    def test_null_in_otherwise_complete_recross_row_is_not_false(self):
        summarize = authored_function("ema-recross", "no_recross_summary")
        rows = pd.DataFrame({"valid": [True, True], "no_recross": [False, None],
                             "session_date": ["a", "b"]})
        self.assertEqual(summarize(rows), {"denominator": 1, "numerator": 0, "days": 1, "censored": 1})

    def test_sequence_denominator_excludes_starting_configurations_and_censoring(self):
        summarize = authored_function("pivot-to-vwap", "sequence_summary")
        rows = pd.DataFrame({
            "result": ["second_before_recross", "recross_first", "neither_within_30m",
                       "simultaneous", "already_beyond_other", "censored_no_endpoint"],
            "censored": [False] * 5 + [True],
            "session_date": ["a", "a", "b", "c", "d", "e"]})
        self.assertEqual(summarize(rows), {"denominator": 3, "numerator": 1, "days": 2, "censored": 1})

    def test_recent_and_preceding_windows_are_disjoint_observed_sessions(self):
        split = authored_function("recent-history", "disjoint_windows")
        rows = pd.DataFrame({"session_date": pd.to_datetime(["2026-06-10", "2026-01-01", "2026-06-02", "2026-02-01"]),
                             "crosses": [0, 1, 2, 3]})
        recent, earlier = split(rows, 2)
        self.assertEqual(recent["crosses"].tolist(), [2, 0])
        self.assertEqual(earlier["crosses"].tolist(), [1, 3])
        self.assertFalse(set(recent["session_date"]) & set(earlier["session_date"]))
        self.assertEqual(len(recent) + len(earlier), len(rows))

    def test_recent_windows_refuse_duplicate_or_empty_comparison_support(self):
        split = authored_function("recent-history", "disjoint_windows")
        rows = pd.DataFrame({"session_date": pd.to_datetime(["2026-01-01", "2026-01-02"]), "crosses": [0, 1]})
        for size in (0, -1, 2, 3):
            with self.subTest(size=size), self.assertRaises(ValueError):
                split(rows, size)
        duplicates = pd.concat([rows.iloc[[0]], rows.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "unique eligible sessions"):
            split(duplicates, 1)


if __name__ == "__main__":
    unittest.main()
