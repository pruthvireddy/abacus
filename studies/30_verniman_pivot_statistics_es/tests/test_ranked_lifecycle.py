"""Cohort and parity guards using synthetic bars only."""
import importlib.util
from pathlib import Path
import sys
import unittest
import tempfile
from collections import Counter

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'src'))
import ranked_lifecycle as lifecycle

spec = importlib.util.spec_from_file_location('ranked_cohort_fixture', STUDY / 'tests/test_engine.py')
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)


class CohortTests(unittest.TestCase):
    def test_late_tail_is_only_full_globex_exclusion(self):
        data = fixture_module.fixture()
        quality = {'contract': 'ESH2020', 'calendar_valid': True, 'rth_complete': True,
                   'anchor_to_rth_end_complete': True, 'full_globex_complete': False}
        minute = [row for row in data['minutes'] if row['open_time'] < fixture_module.at('16:00')]
        got = lifecycle.cohort_eligibility(data['session_date'], quality, minute, data['bars3'], data['bars5'])
        self.assertTrue(got['vwap_only_rth'])
        self.assertFalse(got['vwap_only_full_globex'])
        self.assertEqual(got['rth_reasons'], [])

    def test_missing_anchor_and_unready_features_are_explicit(self):
        data = fixture_module.fixture()
        quality = {'contract': 'ESH2020', 'calendar_valid': True, 'rth_complete': True,
                   'anchor_to_rth_end_complete': False, 'full_globex_complete': False}
        data['bars3'][0]['ema6_ready'] = False
        got = lifecycle.cohort_eligibility(data['session_date'], quality, data['minutes'][1:], data['bars3'], data['bars5'])
        self.assertFalse(got['vwap_only_rth'])
        self.assertIn('unready_full_globex_ema6', got['globex_reasons'])

    def test_parity_distinguishes_zero_false_null_and_float_tolerance(self):
        counts = Counter()
        lifecycle._same({'value': 1. + 1e-10, 'unknown': None, 'flag': False},
                        {'value': 1., 'unknown': None, 'flag': False}, 'test', counts)
        self.assertEqual(counts['cells'], 3)
        with self.assertRaises(ValueError):
            lifecycle._same(False, 0, 'typed', Counter())
        with self.assertRaises(ValueError):
            lifecycle._same(0, None, 'unknown', Counter())

    def test_seal_receipt_refuses_changed_ledger_summary_or_coverage(self):
        for changed in ('ranked-ledgers.json.gz', 'summary.csv', 'ranked-coverage-audit.json'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as folder:
                stage = Path(folder)
                for name in ('ranked-ledgers.json.gz', 'summary.csv', 'freeze.json', 'ranked-coverage-audit.json'):
                    (stage / name).write_text('retained original bytes')
                lifecycle.dump(stage / 'ranked-execution.json', {
                    'coverage_audit_sha256': lifecycle.digest(stage / 'ranked-coverage-audit.json')})
                lifecycle.dump(stage / 'ranked-verification.json', {'status': 'passed',
                    'ledger_sha256': lifecycle.digest(stage / 'ranked-ledgers.json.gz'),
                    'freeze_sha256': lifecycle.digest(stage / 'freeze.json'),
                    'ranked_execution_sha256': lifecycle.digest(stage / 'ranked-execution.json'),
                    'summary_tables': [{'path': 'summary.csv', 'sha256': lifecycle.digest(stage / 'summary.csv')}]})
                lifecycle.check_ranked_receipt(stage)
                (stage / changed).write_text('changed after verification')
                with self.assertRaisesRegex(ValueError, 'changed'):
                    lifecycle.check_ranked_receipt(stage)


if __name__ == '__main__':
    unittest.main()
