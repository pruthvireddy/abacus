"""Explicit staged metadata/declared-byte check; scientific checks are separate."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

root = Path('/Users/ppanati/Documents/projects/abacus')
stage = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'studies/21_ema_cloud_trend_follow_opportunity'))
sys.path.insert(0, str(root / 'scripts'))
spec = importlib.util.spec_from_file_location('stage2_manifest_runner', root / 'studies/21_ema_cloud_trend_follow_opportunity/run_stage2.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
from evidence_contract import assess_bundle
from src.execution import record_command, write_json

record_command(stage, [sys.executable] + sys.argv, root,
               {key: os.environ.get(key) for key in ('UV_CACHE_DIR', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'PYTHONPATH', 'MPLCONFIGDIR')})
runner.assert_frozen_sources(stage, root)
write_json(stage / 'manifest.json', runner.build_manifest(stage))
assessment = assess_bundle(stage)
if assessment['status'] != 'verified_declared_artifacts':
    raise ValueError(json.dumps(assessment))
saved = stage / 'provenance/preflight-manifest.json'
if saved.exists():
    raise ValueError('preflight snapshot overwrite refused')
shutil.copyfile(stage / 'manifest.json', saved)
receipt = {
    'status': 'passed',
    'scope': 'Explicit staged abacus.evidence/v1 metadata and declared local artifact bytes at the retained preflight manifest; scientific and external-byte checks remain separate. Seal regenerates the final manifest after this receipt is added.',
    'manifest_snapshot': 'provenance/preflight-manifest.json',
    'manifest_sha256': hashlib.sha256(saved.read_bytes()).hexdigest(),
    'assessment': assessment,
}
write_json(stage / 'provenance/preseal-bundle-integrity.json', receipt)
print(json.dumps({'status': assessment['status'], 'local_artifacts_verified': assessment['local_artifacts_verified'], 'external_declarations': len(assessment['external_artifacts'])}))
