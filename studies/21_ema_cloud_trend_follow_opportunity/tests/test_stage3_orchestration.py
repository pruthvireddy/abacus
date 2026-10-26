"""Meaningful phase-boundary refusal fixtures with real file mutations."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.execution import file_record, write_json
from src.stage3_execution import authorize, freeze_phase, write_once


class Stage3PhaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.workspace = Path(self.directory.name)
        self.stage = self.workspace / 'work' / '21_ema_cloud_trend_follow_opportunity' / 'fixture'
        self.study = self.workspace / 'studies' / '21_ema_cloud_trend_follow_opportunity'
        self.stage.mkdir(parents=True)
        self.study.mkdir(parents=True)
        cfg = {'periods': {p: {'start': '2021-01-01', 'end': '2024-01-01'}
                           for p in ('development', 'validation', 'final', 'recent')},
               'primary_comparison_family': {'size': 12}}
        write_json(self.study / 'config-stage3.json', cfg)
        write_json(self.stage / 'config.json', cfg)
        for p in (self.study / 'protocol-stage3.md', self.stage / 'protocol.md'):
            p.write_text('frozen methods')
        self.source = self.study / 'kernel.py'
        self.source.write_text('defined before outcomes')
        retained = self.stage / 'provenance/source/kernel.py'
        retained.parent.mkdir(parents=True)
        retained.write_bytes(self.source.read_bytes())
        inventory = {'sources': [{'workspace_path': self.source.relative_to(self.workspace).as_posix(),
                                  'snapshot_path': retained.relative_to(self.stage).as_posix(),
                                  **{k: v for k, v in file_record(self.source).items() if k != 'path'}}]}
        write_json(self.stage / 'provenance/source-inventory.json', inventory)
        self.input = self.workspace / 'input.txt'
        self.input.write_text('immutable release bytes')
        write_json(self.stage / 'inputs.lock.json', {'consumed_records': [file_record(self.input)]})
        write_json(self.stage / 'baseline.lock.json', {'pins': []})
        for name in ('input-prefix-parity.json', 'fixed-baseline-parity.json'):
            write_json(self.stage / 'provenance' / name, {'status': 'passed', 'records': []})
        result = self.stage / 'provenance/actual-tests.json'
        write_json(result, {'passed': True})
        write_json(self.stage / 'provenance/stage3-numerical.json', {'status': 'passed',
            'source_inventory': file_record(self.stage / 'provenance/source-inventory.json', self.stage),
            'input_lock': file_record(self.stage / 'inputs.lock.json', self.stage),
            'baseline_lock': file_record(self.stage / 'baseline.lock.json', self.stage),
            'suites': [{'name': name, 'status': 'passed', 'result': file_record(result, self.stage),
                       'counts': {'tests_run': 3, 'skipped': 0, 'failures': 0, 'errors': 0}}
                      for name in ('study21', 'bhishma-ema')]})
        write_json(self.stage / 'provenance/execution-freeze.json', {'records': [file_record(self.stage / name, self.stage)
            for name in ('config.json', 'protocol.md', 'inputs.lock.json', 'baseline.lock.json', 'provenance/source-inventory.json')]})
        self.gates = [('ES', 3, 'fast', 'abs_2p4')]

    def freeze(self, phase, text='decision'):
        decision = self.stage / (phase + '-choice.json')
        decision.write_text(text)
        receipt = self.stage / (phase + '-independent.json')
        write_json(receipt, {'status': 'passed', 'phase': phase})
        freeze_phase(self.stage, self.workspace, phase, [decision], receipt, self.gates)
        return decision

    def test_development_is_explicit_and_whitelisted(self):
        auth = authorize(self.stage, self.workspace, 'development', self.gates)
        auth.validate('development', 'ES', 3, 'fast', 'abs_2p4')
        with self.assertRaises(ValueError):
            auth.validate('validation', 'ES', 3, 'fast', 'abs_2p4')
        with self.assertRaises(ValueError):
            auth.validate('development', 'ES', 3, 'fast', 'atr_0p5')

    def test_validation_cannot_precede_frozen_shortlist(self):
        with self.assertRaises(FileNotFoundError):
            authorize(self.stage, self.workspace, 'validation', self.gates)
        self.freeze('development')
        authorize(self.stage, self.workspace, 'validation', self.gates)

    def test_reserved_fullgrid_cannot_replace_shortlist(self):
        self.freeze('development')
        with self.assertRaises(ValueError):
            authorize(self.stage, self.workspace, 'validation', self.gates + [('ES', 3, 'fast', 'atr_1')])

    def test_input_mutation_invalidates_new_phase(self):
        self.freeze('development')
        self.input.write_text('changed release bytes')
        with self.assertRaises(ValueError):
            authorize(self.stage, self.workspace, 'validation', self.gates)

    def test_source_mutation_invalidates_authorization_and_phase(self):
        auth = authorize(self.stage, self.workspace, 'development', self.gates)
        self.source.write_text('changed after scoring')
        with self.assertRaises(ValueError):
            auth.validate('development', 'ES', 3, 'fast', 'abs_2p4')
        with self.assertRaises(ValueError):
            authorize(self.stage, self.workspace, 'development', self.gates)

    def test_shortlist_mutation_invalidates_later_final_gate(self):
        shortlist = self.freeze('development')
        self.freeze('validation')
        authorize(self.stage, self.workspace, 'final', self.gates)
        shortlist.write_text('a different nominee')
        with self.assertRaises(ValueError):
            authorize(self.stage, self.workspace, 'final', self.gates)

    def test_recent_requires_completed_final_assessment(self):
        self.freeze('development')
        self.freeze('validation')
        with self.assertRaises(FileNotFoundError):
            authorize(self.stage, self.workspace, 'recent', self.gates)
        self.freeze('final')
        authorize(self.stage, self.workspace, 'recent', self.gates)

    def test_failed_independent_receipt_cannot_unlock(self):
        path = self.stage / 'rejected.json'
        write_json(path, {'status': 'failed'})
        with self.assertRaises(ValueError):
            freeze_phase(self.stage, self.workspace, 'development', [], path, self.gates)

    def test_phase_artifacts_refuse_overwrite(self):
        self.freeze('development')
        with self.assertRaises(ValueError):
            self.freeze('development', 'replacement')
        path = self.stage / 'once.json'
        write_once(path, {'answer': 1})
        with self.assertRaises(ValueError):
            write_once(path, {'answer': 2})

    def enable_recovery(self):
        cfg = json.loads((self.stage / 'config.json').read_text())
        cfg['development_recovery'] = {'adopted_attempt_id': 'retained-original'}
        write_json(self.stage / 'config.json', cfg)
        write_json(self.study / 'config-stage3.json', cfg)
        frozen = self.stage / 'provenance/execution-freeze.json'
        value = json.loads(frozen.read_text())
        value['records'][0] = file_record(self.stage / 'config.json', self.stage)
        write_json(frozen, value)
        original = self.workspace / 'original-packet'
        original.write_text('source-frozen scientific values')
        return original

    def recovery_receipts(self, original, completion=False):
        names = ['adopted-recovery-packets.json', 'development-recovery-freeze.json']
        if completion:
            names.append('development-recovery-completion.json')
        for name in names:
            write_json(self.stage / 'provenance' / name, {'status': 'passed',
                'records': [], 'external_records': [file_record(original)]})

    def test_recovery_needs_original_packet_and_source_freeze_before_scoring(self):
        original = self.enable_recovery()
        with self.assertRaises(FileNotFoundError):
            authorize(self.stage, self.workspace, 'development', self.gates)
        self.recovery_receipts(original)
        authorize(self.stage, self.workspace, 'development', self.gates)
        original.write_text('altered original packet')
        with self.assertRaises(ValueError):
            authorize(self.stage, self.workspace, 'development', self.gates)

    def test_partial_recovery_cannot_freeze_shortlist_or_unlock_validation(self):
        original = self.enable_recovery()
        self.recovery_receipts(original)
        with self.assertRaises(FileNotFoundError):
            self.freeze('development')
        self.recovery_receipts(original, completion=True)
        self.freeze('development')
        authorize(self.stage, self.workspace, 'validation', self.gates)
        original.write_text('altered retained original')
        with self.assertRaises(ValueError):
            authorize(self.stage, self.workspace, 'validation', self.gates)

    def test_failed_recovery_completion_cannot_unlock_selection(self):
        original = self.enable_recovery()
        self.recovery_receipts(original, completion=True)
        write_json(self.stage / 'provenance/development-recovery-completion.json',
                   {'status': 'failed', 'records': [], 'external_records': []})
        with self.assertRaises(ValueError):
            self.freeze('development')


if __name__ == '__main__':
    unittest.main()
