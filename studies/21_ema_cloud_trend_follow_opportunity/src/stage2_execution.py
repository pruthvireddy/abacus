"""Stage 2 freeze, numerical evidence and explicit immutable baseline guards."""
from pathlib import Path
import json
import shutil

from .execution import file_record, sha256, snapshot_sources, verify_record, write_json
from .stage2_contract import BASELINE_RUN_ID, DELIVERY_SHA256, STUDY_ID


def pin_baseline(stage: Path, workspace: Path) -> dict:
    if (stage / 'provenance/source-inventory.json').exists():
        raise ValueError('baseline repinning after source freeze refused')
    baseline = workspace / 'runs' / STUDY_ID / BASELINE_RUN_ID
    handoff_path = baseline / 'stage2-handoff.json'
    handoff = json.loads(handoff_path.read_text())
    records = []
    for declared in handoff['slow_baseline']:
        path = baseline / declared['artifact']
        if sha256(path) != declared['sha256']:
            raise ValueError('Stage 1 handoff identity mismatch: ' + str(path))
        records.append(file_record(path))
    if handoff['reusable_delivery']['sha256'] != DELIVERY_SHA256:
        raise ValueError('baseline delivery declaration differs')
    delivery = workspace / handoff['reusable_delivery']['manifest']
    if sha256(delivery) != DELIVERY_SHA256:
        raise ValueError('immutable delivery differs')
    manifest = json.loads((baseline / 'manifest.json').read_text())
    for record in manifest['artifacts']:
        verify_record(record, baseline)
    external = json.loads((baseline / 'events.manifest.json').read_text())['records']
    for record in external:
        verify_record(record)
    # The actual numerical kernels must match the executed baseline. Current C
    # verifier/renderer repairs are separately disclosed and are not kernels.
    kernel_records = []
    for name in ('engine.py', 'outcomes.py', 'statistics.py'):
        current = workspace / 'studies' / STUDY_ID / 'src' / name
        frozen = baseline / 'provenance/source/studies' / STUDY_ID / 'src' / name
        if sha256(current) != sha256(frozen):
            raise ValueError('inherited numerical source differs: ' + name)
        kernel_records.append(file_record(frozen))
    shutil.copyfile(baseline / 'inputs.lock.json', stage / 'inputs.lock.json')
    for name in ('protocol.md', 'config.json', 'stage2-handoff.json', 'events.manifest.json', 'manifest.json'):
        destination = stage / 'baseline' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(baseline / name, destination)
    receipt = {'status': 'passed_with_inherited_qualifications', 'baseline_run_id': BASELINE_RUN_ID,
        'baseline_manifest': file_record(baseline / 'manifest.json'), 'handoff': file_record(handoff_path),
        'declared_scientific_pins': records, 'delivery': file_record(delivery),
        'local_artifacts_verified': len(manifest['artifacts']), 'external_ledgers_verified': len(external),
        'external_records': external, 'inherited_kernels': kernel_records,
        'qualification': 'Consumed published bytes are verified. Original producer snapshots, corrected canonical source, missing reconstruction/arrival records and calendar/native/backup qualifications retain the sealed Stage 1 interpretation.'}
    write_json(stage / 'baseline.lock.json', receipt)
    return receipt


def freeze(stage: Path, workspace: Path, study: Path) -> dict:
    if not (stage / 'baseline.lock.json').is_file() or (stage / 'execution.json').exists():
        raise ValueError('verified baseline required before a fresh source freeze')
    shutil.copyfile(study / 'config-stage2.json', stage / 'config.json')
    shutil.copyfile(study / 'protocol-stage2.md', stage / 'protocol.md')
    inventory = snapshot_sources(stage, workspace, study)
    for path in (study / 'config-stage2.json', study / 'protocol-stage2.md',
                 workspace / 'scripts/tests/test_check_registry.py',
                 workspace / 'scripts/check-workspace',
                 workspace / 'scripts/workspace_checks.py',
                 workspace / 'scripts/check_registry.py',
                 workspace / 'uv.lock',
                 workspace / 'packages/bhishma/tests/test_ema_cloud.py',
                 workspace / 'packages/bhishma/tests/test_ema_cloud_release.py'):
        relative = path.relative_to(workspace)
        destination = stage / 'provenance/source' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        inventory['sources'].append({'workspace_path': relative.as_posix(),
            'snapshot_path': destination.relative_to(stage).as_posix(),
            'bytes': path.stat().st_size, 'sha256': sha256(path)})
    inventory['scope'] += ' Stage 2 protocol/settings and every study Python source/test are explicitly included.'
    write_json(stage / 'provenance/source-inventory.json', inventory)
    assert_frozen_sources(stage, workspace)
    return inventory


def assert_frozen_sources(stage: Path, workspace: Path) -> dict:
    inventory = json.loads((stage / 'provenance/source-inventory.json').read_text())
    for record in inventory['sources']:
        for path in (workspace / record['workspace_path'], stage / record['snapshot_path']):
            verify_record({'path': str(path), 'bytes': record['bytes'], 'sha256': record['sha256']})
    study = workspace / 'studies' / STUDY_ID
    for name, original in (('config.json', 'config-stage2.json'), ('protocol.md', 'protocol-stage2.md')):
        if sha256(stage / name) != sha256(study / original):
            raise ValueError('frozen Stage 2 settings/protocol differ')
    baseline_lock = json.loads((stage / 'baseline.lock.json').read_text())
    verify_record(baseline_lock['baseline_manifest'])
    for item in baseline_lock['declared_scientific_pins']:
        verify_record(item)
    verify_record(baseline_lock['delivery'])
    return inventory


def assert_numerical_gate(stage: Path) -> dict:
    receipt = json.loads((stage / 'provenance/stage2-numerical.json').read_text())
    if receipt['status'] != 'passed':
        raise ValueError('actual owned numerical fixtures must pass')
    for key in ('source_inventory', 'input_lock', 'baseline_lock'):
        verify_record(receipt[key], stage)
    for suite in receipt['suites']:
        verify_record(suite['result'], stage)
        counts = suite['counts']
        if suite['status'] != 'passed' or counts['tests_run'] <= counts['skipped'] or counts['failures'] or counts['errors']:
            raise ValueError('empty, wholly skipped or failed numerical suite')
    if {item['name'] for item in receipt['suites']} != {'study21', 'bhishma-ema'}:
        raise ValueError('required actual numerical records absent')
    return receipt
