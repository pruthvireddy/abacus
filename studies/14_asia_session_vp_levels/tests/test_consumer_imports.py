"""Fresh-process consumer imports; no study preparation or execution is called."""

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


STUDY_ROOT = Path(__file__).resolve().parents[1]
CONSUMERS = ('src.preparation', 'src.study_run', 'src.previous_day_run',
             'seal', 'verify_previous_day_run', 'feature_audit', 'preparation-script-import')
CHILD = r'''
import importlib
import importlib.abc
import os
from pathlib import Path
import subprocess
import sys

study = Path(sys.argv[1])
consumer = sys.argv[2]
sys.path.insert(0, str(study))
forbidden = ('abacus_bhishma.vp_hvn_release', 'abacus_bhishma.vp_hvn',
             'abacus_bhishma.vp_hvn_native', 'abacus_bhishma.continuous_phase1',
             'abacus_bhishma.continuous_phase2', 'abacus_bhishma.gc_ema_bands',
             'abacus_bhishma.session_anchored_vwap', 'abacus_bhishma.derived_ohlcv_5m',
             'abacus_bhishma.daily_context', 'databento', 'databento_dbn')

def blocked(name):
    return any(name == item or name.startswith(item + '.') for item in forbidden)

class Boundary(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if blocked(fullname):
            raise AssertionError('study consumer imported publication/native implementation: ' + fullname)

def no_external(*args, **kwargs):
    raise AssertionError('study consumer invoked an external subprocess tool')

sys.meta_path.insert(0, Boundary())
for name in ('Popen', 'run', 'call', 'check_call', 'check_output'):
    setattr(subprocess, name, no_external)
for name in ('system', 'popen', 'posix_spawn', 'posix_spawnp', 'spawnv', 'spawnve'):
    if hasattr(os, name):
        setattr(os, name, no_external)

forbidden_calls = {'prepare', 'execute', 'execute_previous_day', 'seal', 'verify', 'audit',
                   'read_snapshots', 'session_groups', 'session_signals', 'session_outcomes',
                   '_render', '_render_saved', 'write_jsonl'}
def profile(frame, event, arg):
    if event == 'call' and frame.f_code.co_name in forbidden_calls:
        if Path(frame.f_code.co_filename).is_relative_to(study):
            raise AssertionError('research function ran while importing: ' + frame.f_code.co_name)
sys.setprofile(profile)
from abacus_bhishma import paths
paths.load_workspace_paths = no_external
if consumer == 'preparation-script-import':
    import runpy
    from types import SimpleNamespace
    sys.path.insert(0, str(study / 'src'))
    module = SimpleNamespace(**runpy.run_path(str(study / 'src/preparation.py'), run_name='import_guard'))
else:
    module = importlib.import_module(consumer)
sys.setprofile(None)
if any(blocked(name) for name in sys.modules):
    raise AssertionError('publication/native module loaded')
from abacus_bhishma.provenance import sha256_file
if getattr(module, 'sha256', None) is not sha256_file:
    raise AssertionError('consumer did not retain the canonical hashing alias')
if consumer in ('src.preparation', 'preparation-script-import'):
    from abacus_bhishma.vp_hvn_loader import load_release
    if module.load_release is not load_release:
        raise AssertionError('preparation did not retain canonical consumer loader')
if consumer == 'src.study_run' and hasattr(module, 'load_release'):
    raise AssertionError('unused loader import remains')
print('consumer import passed')
'''


class ConsumerImportTests(unittest.TestCase):
    def test_all_six_consumers_import_in_fresh_processes_without_builders_or_execution(self):
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith('ABACUS_') and key != 'PYTHONPATH'}
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        with TemporaryDirectory() as unrelated:
            for consumer in CONSUMERS:
                with self.subTest(consumer=consumer):
                    result = subprocess.run([sys.executable, '-B', '-c', CHILD, str(STUDY_ROOT), consumer],
                                            cwd=unrelated, env=environment, capture_output=True,
                                            text=True, check=False, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout.strip(), 'consumer import passed')
            self.assertEqual(list(Path(unrelated).iterdir()), [])

    def test_study_json_writer_preserves_exact_existing_convention(self):
        sys.path.insert(0, str(STUDY_ROOT))
        self.addCleanup(sys.path.remove, str(STUDY_ROOT))
        dump = importlib.import_module('src.evidence').dump
        value = {'unicode': 'caf\u00e9', 'nested': {'nullable': None, 'flag': False}, 'order': [2, 1]}
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'created/parents/saved.json'
            dump(str(path), value)
            expected = json.dumps(value, indent=2, allow_nan=False) + '\n'
            self.assertEqual(path.read_text(), expected)
            self.assertIn('caf\\u00e9', path.read_text())
            for number in (float('nan'), float('inf'), float('-inf')):
                with self.subTest(number=number), self.assertRaises(ValueError):
                    dump(path, {'invalid': number})
                self.assertEqual(path.read_text(), expected)

    def test_local_constants_and_future_source_scope_keep_existing_values(self):
        sys.path.insert(0, str(STUDY_ROOT))
        self.addCleanup(sys.path.remove, str(STUDY_ROOT))
        evidence = importlib.import_module('src.evidence')
        self.assertEqual(evidence.DATASET_ID, 'nq_causal_vp_hvn__1.0.0')
        self.assertEqual(evidence.MINUTE, 60_000_000_000)
        self.assertEqual(evidence.PACKAGE_SOURCE_PATHS, (
            'packages/bhishma/src/abacus_bhishma/paths.py',
            'packages/bhishma/src/abacus_bhishma/provenance.py',
            'packages/bhishma/src/abacus_bhishma/publication_safety.py'))


if __name__ == '__main__':
    unittest.main()
