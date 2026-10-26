"""Stage 3 byte-bound phase gates; no implicit reserved-period execution."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from .execution import file_record, sha256, snapshot_sources, verify_record, write_json

STUDY_ID = '21_ema_cloud_trend_follow_opportunity'
BASELINES = {'stage1': '20261010T221954Z_s1_8c6e_r3',
             'stage2': '20261011T002602Z_s2_c1b4'}
BASELINE_HASHES = {'stage1': '139f50355969e0557efea2f5a3f273320e059af4a74aad429011c396a4b098a6',
                   'stage2': '97667926022ab8c32533f9c3e31a2b2091156eb90233e66176c7b63baa7ff181'}
OLD_DELIVERY_SHA = '59010a558b4e727dbfaa37a64b4a209590288f23744127ab98747cd27ff56d44'
RECEIPTS = {'development': 'development-frozen.json',
            'validation': 'validation-frozen.json',
            'final': 'final-assessment-frozen.json'}


def write_once(path: Path, value) -> None:
    if path.exists():
        raise ValueError('immutable phase artifact overwrite refused: ' + str(path))
    write_json(path, value)


def pin_baselines(stage: Path, workspace: Path) -> dict:
    """Verify every declared local baseline and explicitly retained ledger byte."""
    destination = stage / 'baseline.lock.json'
    if destination.exists() or (stage / 'provenance/source-inventory.json').exists():
        raise ValueError('baseline repinning refused')
    records = []
    for label, run_id in BASELINES.items():
        baseline = workspace / 'runs' / STUDY_ID / run_id
        if sha256(baseline / 'manifest.json') != BASELINE_HASHES[label]:
            raise ValueError('completed baseline manifest differs: ' + label)
        manifest = json.loads((baseline / 'manifest.json').read_text())
        for declared in manifest['artifacts']:
            verify_record(declared, baseline)
        external = json.loads((baseline / 'events.manifest.json').read_text())['records']
        for declared in external:
            verify_record(declared)
        scientific = []
        for name in ('protocol.md', 'config.json', 'inputs.lock.json', 'manifest.json',
                     'events.manifest.json', 'report.md', 'advice.md', 'provenance/checks.json'):
            source = baseline / name
            target = stage / 'baseline' / label / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            scientific.append(file_record(source))
        records.append({'stage': label, 'run_id': run_id, 'manifest': file_record(baseline / 'manifest.json'),
                        'scientific_pins': scientific, 'local_artifacts_verified': len(manifest['artifacts']),
                        'external_records': external, 'external_ledgers_verified': len(external)})
    second = workspace / 'runs' / STUDY_ID / BASELINES['stage2']
    handoff = json.loads((second / 'stage3-handoff.json').read_text())
    verify_record(handoff['stage1_manifest'])
    for declared in handoff['stage2_baseline_artifacts']:
        verify_record(declared, second)
    delivery = workspace / handoff['reusable_delivery']['path']
    if sha256(delivery) != OLD_DELIVERY_SHA or handoff['reusable_delivery']['sha256'] != OLD_DELIVERY_SHA:
        raise ValueError('original immutable delivery identity differs')
    if handoff['reserved_outcomes_computed'] is not False or handoff['stage3_executed'] is not False:
        raise ValueError('handoff does not retain reserved Stage 3 outcomes')
    for name in ('stage3-handoff.json', 'baseline.lock.json'):
        shutil.copyfile(second / name, stage / 'baseline' / 'stage2' / name)
    kernels = []
    for name in ('engine.py', 'outcomes.py', 'statistics.py', 'stage2_engine.py', 'stage2_statistics.py'):
        current = workspace / 'studies' / STUDY_ID / 'src' / name
        executed = second / 'provenance/source/studies' / STUDY_ID / 'src' / name
        if sha256(current) != sha256(executed):
            raise ValueError('fixed reproduction kernel drift: ' + name)
        kernels.append(file_record(executed))
    receipt = {'schema_version': 'study21.stage3-baselines/v1', 'status': 'passed',
               'baselines': records, 'stage2_handoff': file_record(second / 'stage3-handoff.json'),
               'stage2_baseline_lock': file_record(second / 'baseline.lock.json'),
               'old_delivery': file_record(delivery), 'inherited_kernels': kernels,
               'qualification': 'Exact retained bytes verified. Executed snapshots, canonical/checker/presentation repairs and reconstruction/arrival/calendar/native/backup qualifications remain distinct.'}
    write_once(destination, receipt)
    return receipt


def freeze(stage: Path, workspace: Path, study: Path) -> dict:
    if not (stage / 'baseline.lock.json').is_file() or not (stage / 'inputs.lock.json').is_file():
        raise ValueError('new input and both verified baseline identities required before freeze')
    if (stage / 'provenance/source-inventory.json').exists():
        raise ValueError('source already frozen')
    shutil.copyfile(study / 'config-stage3.json', stage / 'config.json')
    shutil.copyfile(study / 'protocol-stage3.md', stage / 'protocol.md')
    inventory = snapshot_sources(stage, workspace, study)
    paths = [study / 'config-stage3.json', study / 'protocol-stage3.md', study / 'README.md',
             study / 'notes.md', study / 'study.json',
             study / 'config-stage2.json', study / 'protocol-stage2.md',
             workspace / 'scripts/check-workspace', workspace / 'scripts/workspace_checks.py',
             workspace / 'scripts/check_registry.py', workspace / 'scripts/tests/test_check_registry.py',
             workspace / 'uv.lock']
    paths += list((workspace / 'packages/bhishma/tests').glob('test_ema_cloud*.py'))
    paths += [workspace / relative for relative in ('.gitignore', 'AGENTS.md', 'README.md', 'ARCHITECTURE.md',
        'studies/AGENTS.md', 'packages/sahadeva/AGENTS.md', 'packages/bhishma/AGENTS.md',
        'packages/bhishma/README.md', 'data/README.md', 'requests/README.md', 'runs/README.md', 'templates/README.md',
        'docs/evidence-contract.md', 'apps/narada/AGENTS.md', 'docs/narada.md')]
    known = {r['workspace_path'] for r in inventory['sources']}
    for path in sorted(set(paths)):
        relative = path.relative_to(workspace).as_posix()
        if relative in known:
            continue
        destination = stage / 'provenance/source' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        inventory['sources'].append({'workspace_path': relative,
            'snapshot_path': destination.relative_to(stage).as_posix(),
            'bytes': path.stat().st_size, 'sha256': sha256(path)})
    inventory['sources'].sort(key=lambda r: r['workspace_path'])
    inventory['scope'] += ' Stage 3 source/tests/config/protocol, relevant maintained guides, input producer tests and workspace registry/tooling explicitly included.'
    write_json(stage / 'provenance/source-inventory.json', inventory)
    identity = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'status': 'frozen_before_development', 'records': [file_record(stage / name, stage)
                    for name in ('config.json', 'protocol.md', 'inputs.lock.json', 'baseline.lock.json',
                                 'provenance/source-inventory.json', 'provenance/uv.lock')]}
    identity['records'] += [file_record(path, stage) for path in sorted((stage / 'provenance/reviews').glob('*.py'))]
    if (stage / 'provenance/adopted-preparation.json').is_file():
        identity['records'].append(file_record(stage / 'provenance/adopted-preparation.json', stage))
    if json.loads((stage / 'config.json').read_text()).get('development_workers', 1) > 1:
        original = stage / 'provenance/reviews/serial-parallel-original-before.json'
        if not original.is_file():
            raise ValueError('original partial-stream identities required before parallel restart freeze')
        identity['records'].append(file_record(original, stage))
    if json.loads((stage / 'config.json').read_text()).get('development_recovery'):
        for name in ('adopted-recovery-packets.json', 'development-recovery-freeze.json'):
            _verify_receipt(stage, name)
            identity['records'].append(file_record(stage / 'provenance' / name, stage))
    write_once(stage / 'provenance/execution-freeze.json', identity)
    assert_frozen(stage, workspace)
    return inventory


def assert_frozen(stage: Path, workspace: Path) -> dict:
    frozen = json.loads((stage / 'provenance/execution-freeze.json').read_text())
    for record in frozen['records']:
        verify_record(record, stage)
    inventory = json.loads((stage / 'provenance/source-inventory.json').read_text())
    for r in inventory['sources']:
        for path in (workspace / r['workspace_path'], stage / r['snapshot_path']):
            verify_record({'path': str(path), 'bytes': r['bytes'], 'sha256': r['sha256']})
    for target, original in (('config.json', 'config-stage3.json'), ('protocol.md', 'protocol-stage3.md')):
        if sha256(stage / target) != sha256(workspace / 'studies' / STUDY_ID / original):
            raise ValueError('frozen Stage 3 settings/protocol drift')
    return inventory


def assert_input_bytes(stage: Path) -> int:
    lock = json.loads((stage / 'inputs.lock.json').read_text())
    records = lock.get('consumed_records')
    if not records:
        raise ValueError('complete consumed input byte inventory absent')
    for record in records:
        verify_record(record)
    return len(records)


def assert_numerical_gate(stage: Path) -> dict:
    receipt = json.loads((stage / 'provenance/stage3-numerical.json').read_text())
    if receipt['status'] != 'passed':
        raise ValueError('actual owned numerical results must pass')
    for key in ('source_inventory', 'input_lock', 'baseline_lock'):
        verify_record(receipt[key], stage)
    for suite in receipt['suites']:
        verify_record(suite['result'], stage)
        count = suite['counts']
        if suite['status'] != 'passed' or count['tests_run'] <= count['skipped'] or count['failures'] or count['errors']:
            raise ValueError('empty, wholly skipped or failed actual numerical suite')
    if {s['name'] for s in receipt['suites']} != {'study21', 'bhishma-ema'}:
        raise ValueError('required owned suites absent')
    return receipt


def _verify_receipt(stage: Path, name: str) -> dict:
    path = stage / 'provenance' / name
    receipt = json.loads(path.read_text())
    if receipt['status'] != 'passed':
        raise ValueError('required passing receipt absent: ' + name)
    for record in receipt.get('records', []):
        verify_record(record, stage)
    for record in receipt.get('external_records', []):
        verify_record(record)
    return receipt


@dataclass(frozen=True)
class PhaseAuthorization:
    period: str
    gates: tuple[tuple[str, int, str, str], ...]
    start: str
    end: str
    stage: Path
    workspace: Path
    predecessor: dict | None

    @property
    def allowed_gate_ids(self) -> dict[tuple[str, int, str], tuple[str, ...]]:
        result = {}
        for product, interval, touch, gate_id in self.gates:
            result.setdefault((product, interval, touch), []).append(gate_id)
        return {key: tuple(values) for key, values in result.items()}

    def validate(self, period: str, product: str, interval: int, touch_mode: str, gate_id: str) -> None:
        if period != self.period or (product, interval, touch_mode, gate_id) not in self.gates:
            raise ValueError('outcome period/gateway is outside explicit phase authorization')
        assert_frozen(self.stage, self.workspace)
        if self.predecessor is not None:
            verify_record(self.predecessor, self.stage)


def authorize(stage: Path, workspace: Path, period: str, gates: list[tuple[str, int, str, str]]) -> PhaseAuthorization:
    """Authorize only an explicit period and the frozen allowed gateway roster."""
    assert_frozen(stage, workspace)
    assert_numerical_gate(stage)
    assert_input_bytes(stage)
    cfg = json.loads((stage / 'config.json').read_text())
    if cfg.get('development_recovery'):
        for name in ('adopted-recovery-packets.json', 'development-recovery-freeze.json'):
            _verify_receipt(stage, name)
        if period != 'development':
            _verify_receipt(stage, 'development-recovery-completion.json')
    if period not in ('development', 'validation', 'final', 'recent'):
        raise ValueError('unknown outcome phase')
    _verify_receipt(stage, 'input-prefix-parity.json')
    _verify_receipt(stage, 'fixed-baseline-parity.json')
    predecessor = None
    if period != 'development':
        previous = {'validation': 'development', 'final': 'validation', 'recent': 'final'}[period]
        name = RECEIPTS[previous]
        receipt = _verify_receipt(stage, name)
        # Verify all previous gates too, so mutating an earlier shortlist cannot
        # preserve an apparently intact later final-choice receipt.
        if period in ('final', 'recent'):
            _verify_receipt(stage, RECEIPTS['development'])
        if period == 'recent':
            _verify_receipt(stage, RECEIPTS['validation'])
        allowed = {tuple(item) for item in receipt['allowed_next_gates']}
        if set(gates) != allowed:
            raise ValueError('reserved gateway roster differs from frozen choices')
        predecessor = file_record(stage / 'provenance' / name, stage)
    limits = cfg['periods'][period]
    return PhaseAuthorization(period, tuple(gates), limits['start'], limits['end'],
                              stage, workspace, predecessor)


def freeze_phase(stage: Path, workspace: Path, phase: str, artifacts: list[Path],
                 independent_receipt: Path, next_gates: list[tuple[str, int, str, str]],
                 external_records: list[dict] | None = None) -> dict:
    """Freeze decisions and their independent verification before next outcomes."""
    assert_frozen(stage, workspace)
    if phase not in RECEIPTS:
        raise ValueError('phase has no dependent outcome gate')
    if json.loads((stage / 'config.json').read_text()).get('development_recovery'):
        for name in ('adopted-recovery-packets.json', 'development-recovery-freeze.json',
                     'development-recovery-completion.json'):
            _verify_receipt(stage, name)
            artifacts = artifacts + [stage / 'provenance' / name]
    result = json.loads(independent_receipt.read_text())
    if result.get('status') != 'passed' or result.get('phase') != phase:
        raise ValueError('independent phase assessment must pass before freezing')
    for record in result.get('records', []):
        verify_record(record, stage)
    for record in result.get('external_records', []):
        verify_record(record)
    if phase in ('validation', 'final'):
        _verify_receipt(stage, RECEIPTS['development'])
    if phase == 'final':
        _verify_receipt(stage, RECEIPTS['validation'])
    paths = sorted(set(artifacts + [independent_receipt, stage / 'provenance/execution-freeze.json']))
    if not paths or any(not path.is_relative_to(stage) for path in paths):
        raise ValueError('phase artifacts must belong to the explicit staged bundle')
    receipt = {'schema_version': 'study21.stage3-phase-gate/v1', 'status': 'passed',
        'phase': phase, 'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'records': [file_record(path, stage) for path in paths],
        'external_records': external_records or [],
        'allowed_next_gates': [list(item) for item in sorted(set(next_gates))],
        'family': json.loads((stage / 'config.json').read_text())['primary_comparison_family'],
        'interpretation': 'No replacement search, later fullgrid, failed-nominee rescue or retuning. Identity fallback is not improvement; undefined estimates remain null.'}
    write_once(stage / 'provenance' / RECEIPTS[phase], receipt)
    return receipt
