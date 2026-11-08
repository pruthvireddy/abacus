"""Synthetic numerical checks against functions authored in notebook cells."""
import ast
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd


NOTEBOOK = Path(__file__).resolve().parents[1] / "vern-pivot-cross-statistics.ipynb"


def notebook_function(insight_id, name):
    notebook = json.loads(NOTEBOOK.read_text())
    functions = []
    for cell in notebook["cells"]:
        metadata = cell.get("metadata", {}).get("abacus", {})
        if metadata.get("insight_id") == insight_id and metadata.get("role") == "analysis":
            source = cell["source"] if isinstance(cell["source"], str) else "".join(cell["source"])
            functions.extend(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == name)
    if len(functions) != 1:
        raise ValueError("Expected one authored function in the selected analysis cell")
    namespace = {"pd": pd, "np": np}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(NOTEBOOK), "exec"), namespace)
    return namespace[name]


class NotebookV1AnalysisTests(unittest.TestCase):
    def test_confirmation_is_distinct_from_later_return_censoring(self):
        classify = notebook_function("pivot-confirmation", "confirmation_outcome")
        self.assertEqual(classify({"confirmation_at": "2026-01-01T15:00Z", "returned_at": None,
                                   "return_censored": True}), "EMA6 confirmed before return")
        self.assertEqual(classify({"confirmation_at": "2026-01-01T15:00Z", "returned_at": "2026-01-01T15:03Z"}),
                         "EMA6 confirmed before return")

    def test_return_and_unresolved_remain_different(self):
        classify = notebook_function("pivot-confirmation", "confirmation_outcome")
        self.assertEqual(classify({"confirmation_at": None, "returned_at": "2026-01-01T15:03Z"}),
                         "Price returned before confirmation")
        self.assertEqual(classify({"confirmation_at": pd.NaT, "returned_at": None}),
                         "Unresolved at observation end")

    def test_annual_means_include_observed_zero_and_do_not_invent_years(self):
        summarize = notebook_function("pivot-frequency-trend", "annual_crossing_summary")
        daily = pd.DataFrame({"session_date": pd.to_datetime(["2022-01-02", "2020-01-02", "2020-01-03"]),
                              "ema_crosses": [3, 0, 2]})
        result = summarize(daily)
        self.assertEqual(list(result.index), [2020, 2022])
        self.assertEqual(result.loc[2020, "sessions"], 2)
        self.assertEqual(result.loc[2020, "mean_crossings"], 1)
        self.assertEqual(result.loc[2020, "crossings"], 2)

    def test_duplicate_sessions_are_not_treated_as_independent_days(self):
        summarize = notebook_function("pivot-frequency-trend", "annual_crossing_summary")
        daily = pd.DataFrame({"session_date": pd.to_datetime(["2020-01-02", "2020-01-02"]), "ema_crosses": [0, 2]})
        with self.assertRaisesRegex(ValueError, "unique eligible session"):
            summarize(daily)

    def test_section_rate_is_mean_of_daily_rates_not_pooled_exposure(self):
        summarize = notebook_function("pivot-session-rate", "section_crossing_rates")
        rows = pd.DataFrame({"section": ["am", "am"], "session_date": pd.to_datetime(["2020-01-02", "2020-01-03"]),
                             "ema_crosses": [2, 0], "ema_observed_hours": [1.0, 3.0]})
        result = summarize(rows)
        self.assertEqual(result.loc["am", "mean_per_hour"], 1.0)
        self.assertNotEqual(result.loc["am", "mean_per_hour"], 2 / 4)
        self.assertEqual(result.loc["am", "days"], 2)

    def test_invalid_exposure_is_excluded_and_retained_as_unavailable(self):
        summarize = notebook_function("pivot-session-rate", "section_crossing_rates")
        rows = pd.DataFrame({"section": ["am"] * 3,
                             "session_date": pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-04"]),
                             "ema_crosses": [0, 2, None], "ema_observed_hours": [1.0, 0.0, 2.0]})
        result = summarize(rows)
        self.assertEqual(result.loc["am", "mean_per_hour"], 0.0)
        self.assertEqual(result.loc["am", "days"], 1)
        self.assertEqual(result.loc["am", "unavailable_day_sections"], 2)


if __name__ == "__main__":
    unittest.main()
