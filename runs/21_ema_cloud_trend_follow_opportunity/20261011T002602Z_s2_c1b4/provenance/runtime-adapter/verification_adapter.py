"""Extra retained verifier adapter; canonical/frozen source bytes stay unchanged.

Only two helper references are replaced. Historical execution is explicit and
must follow the parent's source/test review; it is never started by tests.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from time import perf_counter

WORKSPACE = Path('/Users/ppanati/Documents/projects/abacus')
STUDY = WORKSPACE / 'studies/21_ema_cloud_trend_follow_opportunity'
ROOT = Path(__file__).resolve().parent
STAGE = WORKSPACE / 'work/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def pin(path):
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=sha(path))


def write_new(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sources():
    local = [ROOT / name for name in ('verification_adapter.py', 'lazy_equal.py', 'test_runtime_adapter.py')]
    maintained = [STUDY / 'src' / name for name in ('reconcile.py', 'stage2_reconcile.py', 'stage2_reference.py', 'stage2_reporting.py', 'stage2_contract.py')]
    maintained += [STUDY / 'tests' / name for name in ('test_stage2_reference.py', 'test_stage2_reconcile.py', 'test_stage2_reporting.py')]
    maintained += [STUDY / 'run_stage2.py', WORKSPACE / 'uv.lock', WORKSPACE / 'pyproject.toml']
    return local + maintained


def assert_pins(receipt):
    for item in receipt['source_identities']:
        if pin(Path(item['path'])) != item:
            raise ValueError('adapter/source/test pin drift')


def prepare_tests():
    env = dict(PYTHONPATH='/private/tmp/abacus-study21-plot-deps', MPLCONFIGDIR='/private/tmp/abacus-study21-mpl', UV_CACHE_DIR='/private/tmp/abacus-study21-uv-cache')
    commands = [dict(phase=p, command='PYTHONPATH=/private/tmp/abacus-study21-plot-deps MPLCONFIGDIR=/private/tmp/abacus-study21-mpl UV_CACHE_DIR=/private/tmp/abacus-study21-uv-cache ./scripts/uv run --locked --no-sync python work/21_ema_cloud_trend_follow_opportunity/stage2_preparation/C-runtime/verification_adapter.py ' + p + ' > work/21_ema_cloud_trend_follow_opportunity/stage2_preparation/C-runtime/' + p + '.log 2>&1') for p in ('equivalence', 'fixtures')]
    receipt = dict(schema_version=1, run_id=STAGE.name, captured_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Pre-test pins of separate adapter/helper/tests and unchanged maintained numerical/fixture sources. No historical verification launched.',
        source_identities=[pin(p) for p in sources()], commands=commands, environment=env,
        plot_context_locator=str(STAGE / 'provenance/numerical-plot-context.json'), plot_context_sha256=sha(STAGE / 'provenance/numerical-plot-context.json'),
        allowed_replacements=['src.reconcile._equal', 'src.stage2_reconcile.base_equal'],
        behavior='Same missing checks, type/numeric branches, finite predicate, rel_tol/abs_tol=2e-10, strict boolean callers and exact mismatch message strings. Only success-path repr formatting is deferred.')
    write_new(ROOT / 'tests-before.json', receipt)


def load_test_environment():
    sys.path.insert(0, str(STUDY))
    sys.path.insert(0, str(STUDY / 'tests'))
    before = json.loads((ROOT / 'tests-before.json').read_text())
    assert_pins(before)
    return before


def run_tests(phase):
    before = load_test_environment()
    import unittest
    from lazy_equal import install, restore
    started = perf_counter()
    if phase == 'equivalence':
        suite = unittest.defaultTestLoader.loadTestsFromName('test_runtime_adapter')
        original = None
    else:
        original = install()
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in
            ('test_stage2_reference', 'test_stage2_reconcile', 'test_stage2_reporting'))
    try:
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        if original is not None:
            restore(original)
    assert_pins(before)
    receipt = dict(schema_version=1, phase=phase, status='passed' if result.wasSuccessful() and not result.skipped else 'failed',
        tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped),
        seconds=perf_counter()-started, before=pin(ROOT / 'tests-before.json'), source_identities=before['source_identities'],
        historical_execution=False, maintained_sources_unchanged=True,
        patched_during_fixtures=['src.reconcile._equal', 'src.stage2_reconcile.base_equal'] if phase == 'fixtures' else [])
    write_new(ROOT / (phase + '-result.json'), receipt)
    print(json.dumps(receipt))
    if receipt['status'] != 'passed':
        raise SystemExit(1)


def prepare_run(stage):
    before_tests = json.loads((ROOT / 'tests-before.json').read_text())
    assert_pins(before_tests)
    for name in ('equivalence-result.json', 'fixtures-result.json'):
        if json.loads((ROOT / name).read_text())['status'] != 'passed':
            raise ValueError('adapter tests must pass before run preparation')
    from src.stage2_execution import assert_frozen_sources
    assert_frozen_sources(stage, WORKSPACE)
    if (stage / 'provenance/independent-stage2-before.json').exists():
        raise ValueError('original audit attempt must be retained separately before adapter execution')
    artifacts = [stage / name for name in ('config.json', 'protocol.md', 'inputs.lock.json', 'baseline.lock.json',
        'events.manifest.json', 'publication.json', 'source-bindings.json', 'report.md', 'report.html', 'advice.md', 'metrics.json', 'exclusions.json', 'provenance/source-inventory.json')]
    artifacts += list((stage / 'tables').glob('*')) + list((stage / 'figures').glob('*.png')) + list((stage / 'downloads').glob('*.csv'))
    artifacts += [Path(r['path']) for r in json.loads((stage / 'events.manifest.json').read_text())['records']]
    receipt = dict(schema_version=1, run_id=stage.name, captured_at_utc=datetime.now(timezone.utc).isoformat(),
        status='prepared', source_identities=before_tests['source_identities'], tests=[pin(ROOT / name) for name in ('tests-before.json', 'equivalence-result.json', 'fixtures-result.json')],
        input_output_identities=[pin(p) for p in sorted(set(artifacts)) if p.is_file()],
        allowed_replacements=['src.reconcile._equal', 'src.stage2_reconcile.base_equal'],
        command='UV_CACHE_DIR=/private/tmp/abacus-study21-uv-cache ./scripts/uv run --locked --no-sync python work/21_ema_cloud_trend_follow_opportunity/stage2_preparation/C-runtime/verification_adapter.py run --execute-reviewed > work/21_ema_cloud_trend_follow_opportunity/stage2_preparation/C-runtime/historical-run.log 2>&1',
        scope='Unchanged complete frozen run_stage2.verify → verify_bundle, no skipped checks. Only success-path diagnostic repr formatting is deferred in memory; no scientific behavior or artifact changes.')
    write_new(ROOT / 'historical-before.json', receipt)


def execute_run(stage):
    before = json.loads((ROOT / 'historical-before.json').read_text())
    assert_pins(before)
    for item in before['input_output_identities']:
        if pin(Path(item['path'])) != item:
            raise ValueError('adapter run input/output drift')
    from lazy_equal import install, restore
    original = install()
    spec = importlib.util.spec_from_file_location('stage2_frozen_verify_runner', STUDY / 'run_stage2.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    started = perf_counter()
    try:
        runner.verify(stage)
    finally:
        restore(original)
    assert_pins(before)
    for item in before['input_output_identities']:
        if pin(Path(item['path'])) != item:
            raise ValueError('adapter completed run input/output drift')
    augmentation = dict(status='passed', scope=before['scope'], allowed_replacements=before['allowed_replacements'],
        adapter_before_execution=pin(ROOT / 'historical-before.json'), adapter_source_identities=before['source_identities'],
        scientific_behavior_changed=False, numerical_artifacts_changed=False, full_frozen_verify_bundle_called=True,
        checks_skipped=0, seconds=perf_counter()-started)
    path = stage / 'provenance/scientific-reconciliation.json'
    scientific = json.loads(path.read_text())
    scientific['verification_runtime_adapter'] = augmentation
    path.write_text(json.dumps(scientific, indent=2, allow_nan=False) + '\n')
    completion = dict(schema_version=1, run_id=stage.name, status='passed', finished_at_utc=datetime.now(timezone.utc).isoformat(),
        runtime_adapter=augmentation, results=[pin(stage / 'provenance' / name) for name in
            ('scientific-reconciliation.json', 'external-bytes.json', 'independent-uncertainty.json', 'independent-presentation-transfer.json', 'independent-stage2-before.json')])
    write_new(ROOT / 'historical-completion.json', completion)
    print(json.dumps(completion))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare-tests', 'equivalence', 'fixtures', 'prepare-run', 'run'))
    parser.add_argument('--stage', type=Path, default=STAGE)
    parser.add_argument('--execute-reviewed', action='store_true')
    args = parser.parse_args()
    if args.phase == 'prepare-tests':
        prepare_tests()
    elif args.phase in ('equivalence', 'fixtures'):
        run_tests(args.phase)
    else:
        sys.path.insert(0, str(STUDY))
        if args.phase == 'run' and not args.execute_reviewed:
            parser.error('Historical execution requires the explicit reviewed execution flag')
        prepare_run(args.stage.resolve()) if args.phase == 'prepare-run' else execute_run(args.stage.resolve())
