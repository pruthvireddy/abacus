import ast
import json
from pathlib import Path
import unittest

import numpy as np


def notebook_functions():
    notebook = Path(__file__).resolve().parents[1] / "nq-overnight-range-cash-open.ipynb"
    names = {"threshold_times", "first_side", "excursion_bounds"}
    functions = []
    for cell in json.loads(notebook.read_text())["cells"]:
        if cell["cell_type"] == "code":
            tree = ast.parse("".join(cell["source"]))
            functions.extend(node for node in tree.body
                             if isinstance(node, ast.FunctionDef) and node.name in names)
    namespace = {"np": np}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(notebook), "exec"), namespace)
    return namespace


class NotebookPathTests(unittest.TestCase):
    def test_first_threshold_is_inclusive_and_ties_stay_unresolved(self):
        fn = notebook_functions()
        path = np.array([[100, 100.25, 99.75], [100, 101, 99], [100, 102, 98]])
        upper, lower = fn["threshold_times"](path, 101, 99)
        self.assertEqual((upper, lower), (1, 1))
        self.assertEqual(fn["first_side"](upper, lower), "same minute")
        self.assertEqual(fn["first_side"](None, None), "neither")
        self.assertEqual(fn["threshold_times"](path[:1], 101, 99), (None, None))

    def test_open_through_counts_and_excursion_bounds_include_the_gap(self):
        fn = notebook_functions()
        path = np.array([[100, 101, 99.50], [99, 103, 98]])
        self.assertEqual(fn["threshold_times"](path, 102, 98), (1, 1))
        self.assertEqual(fn["excursion_bounds"](path, 100, "high", 1), (1, 2))
        self.assertEqual(fn["excursion_bounds"](path, 100, "high", None), (2, 2))
