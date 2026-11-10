import sys
import unittest
from decimal import Decimal
from pathlib import Path

import numpy as np

from abacus_bhishma.nq_opening_range import opening_geometry

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from support import block_interval, ridge_probabilities, wilson


class OpeningRangeTests(unittest.TestCase):
    def test_signed_distances_and_exact_midpoint(self):
        result = opening_geometry(Decimal("101.25"), Decimal("100"), Decimal("101.50"))
        self.assertEqual(result["overnight_midpoint"], Decimal("100.625"))
        self.assertEqual(result["distance_to_high"], Decimal("-0.25"))
        self.assertEqual(result["distance_to_low"], Decimal("1.50"))
        self.assertEqual(result["normalized_open"], 1.2)

    def test_missing_or_degenerate_inputs(self):
        self.assertIsNone(opening_geometry(None, None, Decimal(99))["distance_to_high"])
        self.assertIsNone(opening_geometry(Decimal(99), Decimal(99), Decimal(99))["normalized_open"])

    def test_interval_and_fitted_probabilities(self):
        low, high = wilson(5, 10)
        self.assertAlmostEqual(low, 1 - high)
        x = np.array([[-2.], [-1.], [1.], [2.]])
        probabilities = ridge_probabilities(x, np.array([0, 0, 1, 1]), x)
        self.assertTrue((np.diff(probabilities) > 0).all())
        self.assertEqual(block_interval(np.zeros(15), 32), (0, 0))
