"""Original/adapter scalar and strict-caller behavior equivalence fixtures."""
import math
from decimal import Decimal
import unittest

import numpy as np
import pandas as pd
from src import reconcile, stage2_reconcile
from lazy_equal import lazy_equal, install, restore

ORIGINAL = reconcile._equal


def outcome(function, actual, expected, context='edge fixture'):
    try:
        result = function(actual, expected, context)
        return ('passed', result)
    except Exception as error:
        return ('failed', type(error).__module__, type(error).__qualname__, str(error))


class ScalarEquivalentTests(unittest.TestCase):
    def compare(self, actual, expected):
        original = outcome(ORIGINAL, actual, expected)
        adapted = outcome(lazy_equal, actual, expected)
        self.assertEqual(adapted, original, (actual, expected))
        return original

    def test_missing_null_nan_nat_and_present_mismatch_messages(self):
        missing = (None, float('nan'), np.float64('nan'), pd.NA, pd.NaT)
        for actual in missing:
            for expected in missing:
                with self.subTest(actual=repr(actual), expected=repr(expected)):
                    self.assertEqual(self.compare(actual, expected)[0], 'passed')
            for present in (0., False, '', 'not missing', pd.Timestamp('2018-01-01T00:00Z')):
                self.assertEqual(self.compare(actual, present)[0], 'failed')
                self.assertEqual(self.compare(present, actual)[0], 'failed')

    def test_numeric_tolerance_edges_nonfinite_and_conversion_errors(self):
        cases = ((7.25, 7.25), (np.float64(3.), 3.), (3, np.int64(3)),
                 (0., 0.), (0., 1.9e-10), (0., 2.1e-10),
                 (1e6, 1e6 + 1.9e-4), (1e6, 1e6 + 2.1e-4),
                 (-3., -3.), (-3., 3.), ('3', 3.), ('garbage', 3.),
                 (float('inf'), float('inf')), (float('-inf'), float('-inf')),
                 (3., float('inf')), (float('inf'), 3.), (Decimal('3.0'), 3.),
                 (False, 0), (True, 1), (0, False), (1, True))
        for actual, expected in cases:
            with self.subTest(actual=repr(actual), expected=repr(expected)):
                self.compare(actual, expected)
        self.assertEqual(outcome(lazy_equal, 0., 2.1e-10),
                         ('failed', 'builtins', 'ValueError', 'edge fixture: value mismatch 0.0/2.1e-10'))

    def test_strings_lists_dicts_booleans_and_timestamp_identity_messages(self):
        stamp = pd.Timestamp('2018-01-02T14:00:00Z')
        cases = ((False, False), (True, False), (np.bool_(False), False),
                 ('False', False), ('True', True), ('same', 'same'), ('other', 'same'),
                 ([1, 2], [1, 2]), ([1], [2]), ({'a': 1}, {'a': 1}), ({'a': 2}, {'a': 1}),
                 (stamp, stamp), (stamp.tz_convert('America/New_York'), stamp),
                 (stamp + pd.Timedelta(minutes=1), stamp),
                 (pd.Timestamp('2018-01-02'), pd.Timestamp('2018-01-02')))
        for actual, expected in cases:
            with self.subTest(actual=repr(actual), expected=repr(expected)):
                self.compare(actual, expected)

    def test_strict_boolean_caller_and_csv_tokens_are_unchanged(self):
        def capture(function, args):
            try:
                function(*args)
                return ('passed',)
            except Exception as error:
                return ('failed', type(error).__qualname__, str(error))
        original_results = [capture(stage2_reconcile.equal, (a, e, 'strict bool')) for a, e in
                            ((False, False), (0, False), ('False', False), (np.bool_(False), False), (True, False))]
        original_csv = [capture(stage2_reconcile.cell, (a, e, 'strict csv')) for a, e in
                        (('False', False), ('false', False), ('garbage', False), ('0', False), ('', None), ('0', None), ('0', 0))]
        previous = install()
        try:
            adapted_results = [capture(stage2_reconcile.equal, (a, e, 'strict bool')) for a, e in
                               ((False, False), (0, False), ('False', False), (np.bool_(False), False), (True, False))]
            adapted_csv = [capture(stage2_reconcile.cell, (a, e, 'strict csv')) for a, e in
                           (('False', False), ('false', False), ('garbage', False), ('0', False), ('', None), ('0', None), ('0', 0))]
            self.assertEqual(adapted_results, original_results)
            self.assertEqual(adapted_csv, original_csv)
            self.assertEqual(adapted_results[1][0], 'failed')
            self.assertEqual(adapted_csv[2][0], 'failed')
            self.assertIs(reconcile._equal, lazy_equal)
            self.assertIs(stage2_reconcile.base_equal, lazy_equal)
        finally:
            restore(previous)
        self.assertIs(reconcile._equal, ORIGINAL)
        self.assertIs(stage2_reconcile.base_equal, ORIGINAL)


if __name__ == '__main__':
    unittest.main()
