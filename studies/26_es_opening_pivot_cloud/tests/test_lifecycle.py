"""Synthetic guards for explicit, immutable, pre-outcome evidence phases."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

STUDY = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('study26_lifecycle', STUDY / 'run.py')
life = importlib.util.module_from_spec(spec)
spec.loader.exec_module(life)


class LifecycleTests(unittest.TestCase):
    def test_path_traversal_and_unsafe_identity_refused(self):
        for value in ('../escape', '/tmp/escape', 'a', 'abc/def', 'a b c d'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                life.stage_path(value)

    def test_freeze_checks_retained_and_current_source_and_cached_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = root / 'stage'
            stage.mkdir()
            (root / 'engine.py').write_text('synthetic source')
            (stage / 'source.py').write_text('synthetic source')
            (stage / 'cache.json').write_text('{}')
            life.write_json(stage / 'freeze.json', {'source_files': [{'source': 'engine.py', 'snapshot': 'source.py',
                              'sha256': life.digest(root / 'engine.py')}],
                              'audit_artifacts': [{'path': 'cache.json', 'sha256': life.digest(stage / 'cache.json')}]})
            with patch.object(life, 'ROOT', root):
                life.check_freeze(stage)
                for target in (root / 'engine.py', stage / 'source.py', stage / 'cache.json'):
                    original = target.read_bytes()
                    target.write_text('mutated')
                    with self.subTest(target=target.name), self.assertRaises(ValueError):
                        life.check_freeze(stage)
                    target.write_bytes(original)

    def test_freeze_refuses_outcome_or_existing_freeze_stage(self):
        for marker in ('execution-started.json', 'freeze.json'):
            with tempfile.TemporaryDirectory() as temporary:
                stage = Path(temporary)
                (stage / marker).write_text('{}')
                with self.subTest(marker=marker), self.assertRaises(FileExistsError):
                    life.freeze(stage)

    def test_csv_retains_missing_zero_and_structured_cells(self):
        import csv
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'ledger.csv'
            life.write_csv(path, [{'value': None, 'lineage': ['a', 'b']}, {'value': 0, 'lineage': []}])
            with path.open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]['value'], '')
            self.assertEqual(rows[1]['value'], '0')
            self.assertEqual(json.loads(rows[0]['lineage']), ['a', 'b'])


if __name__ == '__main__':
    unittest.main()
