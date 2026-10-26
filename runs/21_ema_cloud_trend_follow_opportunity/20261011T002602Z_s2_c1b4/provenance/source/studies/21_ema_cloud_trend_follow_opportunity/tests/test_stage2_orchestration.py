"""Required slow parity and bound numerical evidence gate fast execution."""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STUDY))
spec = importlib.util.spec_from_file_location('owned_stage2_run',STUDY / 'run_stage2.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
from src.execution import file_record
from src.stage2_execution import assert_numerical_gate
from src.stage2_contract import PRIMARY_ALPHA, PRIMARY_FAMILY_SIZE, TABLES


class Stage2OrchestrationTests(unittest.TestCase):
    def test_fast_scoring_refuses_failed_parity_before_loading_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            stage=Path(folder);(stage/'provenance').mkdir()
            (stage/'provenance/slow-baseline-parity.json').write_text(json.dumps({'status':'failed'}))
            with patch.object(runner,'assert_frozen_sources'),patch.object(runner,'assert_numerical_gate'):
                with self.assertRaisesRegex(ValueError,'complete exact slow parity'):
                    runner.outcomes(stage,'fast')

    def test_missing_parity_is_not_authorization_to_score(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(runner,'assert_frozen_sources'),patch.object(runner,'assert_numerical_gate'):
                with self.assertRaises(FileNotFoundError):
                    runner.outcomes(Path(folder),'fast')

    def test_passed_headline_parity_cannot_authorize_fast_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            stage=Path(folder);(stage/'provenance').mkdir()
            receipt={'status':'passed','mismatch_count':0,'tolerance':0,
                     'ledger_artifacts_compared':6,'table_artifacts_compared':1}
            (stage/'provenance/slow-baseline-parity.json').write_text(json.dumps(receipt))
            with patch.object(runner,'assert_frozen_sources'),patch.object(runner,'assert_numerical_gate'):
                with self.assertRaisesRegex(ValueError,'parity scope absent'):
                    runner.outcomes(stage,'fast')

    def test_passed_receipt_with_stale_manifest_pin_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            stage=Path(folder);(stage/'provenance').mkdir()
            receipt={'status':'passed','mismatch_count':0,'tolerance':0,
                     'ledger_artifacts_compared':24,'table_artifacts_compared':9,
                     'manifests':[{'sha256':'stale'}]}
            (stage/'provenance/slow-baseline-parity.json').write_text(json.dumps(receipt))
            with patch.object(runner,'assert_frozen_sources'),patch.object(runner,'assert_numerical_gate'),patch.object(runner,'file_record',return_value={'sha256':'actual'}):
                with self.assertRaisesRegex(ValueError,'manifest pins differ'):
                    runner.outcomes(stage,'fast')

    def test_numerical_receipt_detects_changed_bound_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            stage=Path(folder);(stage/'provenance').mkdir()
            for name in ('input.json','baseline.json','source.json','tests.json'):
                (stage/name).write_text('{}\n')
            counts={'tests_run':3,'skipped':0,'failures':0,'errors':0}
            receipt={'status':'passed','source_inventory':file_record(stage/'source.json',stage),
                'input_lock':file_record(stage/'input.json',stage),'baseline_lock':file_record(stage/'baseline.json',stage),
                'suites':[{'name':name,'status':'passed','counts':counts,'result':file_record(stage/'tests.json',stage)} for name in ('study21','bhishma-ema')]}
            (stage/'provenance/stage2-numerical.json').write_text(json.dumps(receipt))
            self.assertEqual(assert_numerical_gate(stage)['status'],'passed')
            (stage/'input.json').write_text('{"changed":true}\n')
            with self.assertRaisesRegex(ValueError,'identity mismatch'):
                assert_numerical_gate(stage)

    def test_phase_manifest_cannot_replace_a_prior_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            stage=Path(folder)
            runner._write_manifest(stage,'acceptance.manifest.json',[])
            with self.assertRaisesRegex(ValueError,'overwrite refused'):
                runner._write_manifest(stage,'acceptance.manifest.json',[])

    def test_six_primary_family_and_complete_table_contract(self):
        self.assertEqual(PRIMARY_FAMILY_SIZE,6)
        self.assertAlmostEqual(1-PRIMARY_ALPHA/PRIMARY_FAMILY_SIZE,0.9916666666666667)
        self.assertEqual(set(TABLES),{f'S2-T{i:02d}' for i in range(11)})


if __name__=='__main__':
    unittest.main()
