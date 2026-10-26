#!/usr/bin/env python3
"""Explicit audit → freeze → outcomes → saved rendering → verify → seal lifecycle."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import unittest

STUDY = Path(__file__).resolve().parent
ROOT = STUDY.parents[1]
IDENTITY = STUDY.name
sys.path.insert(0, str(STUDY))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def plain(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if hasattr(value, 'item'):
        return value.item()
    raise TypeError(type(value).__name__)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=plain, allow_nan=False) + '\n')


def read_json(path):
    return json.loads(Path(path).read_text())


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(key for row in rows for key in row)) or ['status']
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, default=plain, allow_nan=False) if isinstance(value, (list, dict))
                             else plain(value) if isinstance(value, datetime) else value for key, value in row.items()})


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def stage_path(run_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{5,100}', run_id):
        raise ValueError('Run ID must be a safe unique basename')
    return ROOT / 'work' / IDENTITY / run_id


def science_sources():
    own = [p for p in STUDY.rglob('*') if p.is_file() and '__pycache__' not in p.parts
           and (p.suffix in ('.py', '.yaml') or p.name in ('inputs.lock.json', 'protocol-1.0.0.md',
                                                         'reporting-decisions.md', 'input-decisions.md', 'review-notes.md',
                                                         'plan.md', 'user-request.txt'))]
    # Explicit broad loader-source snapshot; not dependency-closure proof.
    bhishma = list((ROOT / 'packages/bhishma/src/abacus_bhishma').glob('*.py'))
    return sorted(set(own + bhishma + [ROOT / 'uv.lock', ROOT / 'pyproject.toml',
                                     ROOT / 'packages/bhishma/pyproject.toml', ROOT / 'config/paths.example.toml',
                                     ROOT / 'apps/narada/package.json', ROOT / 'apps/narada/package-lock.json']
                      + ([ROOT / 'config/paths.local.toml'] if (ROOT / 'config/paths.local.toml').exists() else [])))


def audit(stage):
    from src.inputs import load_inputs
    if stage.exists():
        raise FileExistsError('Audit requires an unused stage; preserve partial diagnostics')
    stage.mkdir(parents=True)
    input_source = digest(STUDY / 'src/inputs.py')
    source_snapshot = stage / 'input-audit-source.py'
    shutil.copy2(STUDY / 'src/inputs.py', source_snapshot)
    write_json(stage / 'audit-started.json', {'at': utcnow(), 'command': sys.argv,
                                          'input_source_sha256': input_source})
    result = load_inputs(ROOT)
    if digest(STUDY / 'src/inputs.py') != input_source:
        raise ValueError('Input audit implementation changed during audit')
    with gzip.open(stage / 'sessions.json.gz', 'wt') as stream:
        json.dump(result['sessions'], stream, default=plain, allow_nan=False)
    for name in ('coverage', 'waterfall'):
        write_csv(stage / f'{name}.csv', result[name])
    chart_bars = [dict(date=s['date'], **bar) for s in result['sessions'] if s['eligible'] for bar in s.get('chart_bars', s['bars5'])]
    write_csv(stage / 'chart_bars.csv', chart_bars)
    write_json(stage / 'input-audit.json', result['audit'])
    write_json(stage / 'audit-complete.json', {'at': utcnow(), 'status': 'passed',
               'sessions_sha256': digest(stage / 'sessions.json.gz'), 'inputs_lock_sha256': digest(STUDY / 'inputs.lock.json'),
               'input_source_sha256': input_source, 'retained_source_sha256': digest(source_snapshot)})
    print(json.dumps(result['audit'], indent=2, default=plain))


def freeze(stage):
    if (stage / 'execution-started.json').exists() or (stage / 'freeze.json').exists():
        raise FileExistsError('Freeze is single-use and precedes execution')
    receipt = read_json(stage / 'audit-complete.json')
    if receipt['sessions_sha256'] != digest(stage / 'sessions.json.gz') or receipt['inputs_lock_sha256'] != digest(STUDY / 'inputs.lock.json'):
        raise ValueError('Audited input cache/lock changed')
    if receipt.get('input_source_sha256') != digest(STUDY / 'src/inputs.py'):
        raise ValueError('Input audit source changed; run a new input audit before freezing')
    if receipt.get('retained_source_sha256') != digest(stage / 'input-audit-source.py'):
        raise ValueError('Retained input audit source changed')
    settings = read_json(STUDY / 'study.yaml')  # JSON syntax is valid YAML 1.2.
    expected = {'proximity_atr_multiplier': .1, 'proximity_min_points': 1, 'stop_buffer_points': 1,
                'formation_bars': 3, 'confirmation_subsequent_bars': 3, 'tick_points': .25,
                'point_dollars': 50, 'fees_round_trip_dollars': 5, 'market_stop_slippage_ticks': 1,
                'target_trade_through_ticks': 1, 'readiness_bars': 250, 'bootstrap_seed': 26021,
                'bootstrap_resamples': 4000, 'entry_policies': ['early', 'confirmed'], 'ema_masks': ['A', 'B', 'C', 'D'],
                'exit_policies': ['fixed_2r', 'verne'], 'entry_cutoff': '10:00', 'flatten_at': '11:00',
                'completeness_window': ['09:30', '10:59'], 'signal_minutes': 5, 'execution_minutes': 1,
                'sensitivities': {'slippage_ticks': [2, 4], 'stop_buffer_points': [.5, 1.5],
                                  'proximity_atr_multiplier': [.05, .15]}}
    if any(settings.get(key) != value for key, value in expected.items()):
        raise ValueError('Machine-readable settings disagree with protocol-1.0.0 engine constants')
    retained = stage / 'provenance'
    retained.mkdir()
    records = []
    for path in science_sources():
        relative = path.relative_to(ROOT)
        output = retained / 'source' / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, output)
        records.append({'source': str(relative), 'snapshot': str(output.relative_to(stage)), 'sha256': digest(path)})
    (retained / 'git-status.txt').write_text(git('status', '--porcelain=v1'))
    (retained / 'tracked-diff.patch').write_text(git('diff', '--binary', 'HEAD'))
    environment = {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
                   'installed_distributions': sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions()),
                   'lock_sha256': digest(ROOT / 'uv.lock'), 'environment_sync': 'none; existing locked environment',
                   'thread_env': {key: os.environ.get(key) for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')},
                   'path_env': {key: os.environ.get(key) for key in ('ABACUS_PUBLICATION_ROOT', 'ABACUS_LEGACY_RESEARCH_ROOT', 'UV_CACHE_DIR')}}
    write_json(retained / 'environment.json', environment)
    for name in ('inputs.lock.json', 'study.yaml', 'protocol-1.0.0.md', 'reporting-decisions.md', 'input-decisions.md'):
        shutil.copy2(STUDY / name, stage / name)
    write_json(stage / 'config.json', {'protocol_version': '1.0.0', 'settings_file': 'study.yaml',
              'study_settings': settings,
              'bootstrap_seed': 26021, 'bootstrap_resamples': 4000, 'inspiration_date': '2026-09-15',
              'inspiration_included': True, 'baseline_variants': 16,
              'sensitivities': [{'name': 'slippage_2', 'slippage': 2}, {'name': 'slippage_4', 'slippage': 4},
                                {'name': 'stop_buffer_0.5', 'stop_buffer': .5}, {'name': 'stop_buffer_1.5', 'stop_buffer': 1.5},
                                {'name': 'proximity_0.05', 'proximity': .05}, {'name': 'proximity_0.15', 'proximity': .15}]})
    write_json(stage / 'freeze.json', {'schema_version': 'opening-pivot-freeze/v1', 'status': 'frozen_before_outcomes',
               'study_id': IDENTITY, 'run_id': stage.name, 'at': utcnow(), 'git_revision': git('rev-parse', 'HEAD').strip(),
               'worktree_dirty': bool(git('status', '--porcelain=v1').strip()), 'source_files': records,
               'audit_artifacts': [{'path': name, 'sha256': digest(stage / name)} for name in
                                   ('sessions.json.gz', 'input-audit.json', 'coverage.csv', 'waterfall.csv', 'chart_bars.csv',
                                    'input-audit-source.py', 'audit-started.json', 'audit-complete.json',
                                    'config.json', 'inputs.lock.json', 'study.yaml', 'protocol-1.0.0.md',
                                    'reporting-decisions.md', 'input-decisions.md')],
               'commands': {'freeze': sys.argv, 'execution': ['./scripts/uv', 'run', '--locked', '--no-sync', 'python',
                            str(STUDY.relative_to(ROOT) / 'run.py'), 'execute', '--run-id', stage.name]},
               'scope': 'Explicit source snapshots and installed versions; not a complete dependency discovery or historical availability proof'})
    print('Frozen before outcomes:', stage)


def check_freeze(stage):
    receipt = read_json(stage / 'freeze.json')
    for record in receipt['source_files']:
        if digest(ROOT / record['source']) != record['sha256'] or digest(stage / record['snapshot']) != record['sha256']:
            raise ValueError('Changed frozen source: ' + record['source'])
    for record in receipt['audit_artifacts']:
        if digest(stage / record['path']) != record['sha256']:
            raise ValueError('Changed audited input: ' + record['path'])
    return receipt


def sessions(stage):
    with gzip.open(stage / 'sessions.json.gz', 'rt') as stream:
        return json.load(stream)


def tag(session, row, sensitivity='baseline'):
    year = int(session['date'][:4])
    return {**row, 'year': year, 'split': 'development' if year <= 2024 else 'validation' if year == 2025 else 'temporal_test',
            'weekday': datetime.fromisoformat(session['date']).strftime('%A'), 'inspired_date': session['date'] == '2026-09-15',
            'sensitivity': sensitivity, 'variant_id': f"{row['entry_policy']}_{row['mask']}_{row['exit_policy']}"}


def execute(stage):
    from src.engine import candidates, simulate
    from src.reporting import summarize
    check_freeze(stage)
    if (stage / 'execution-started.json').exists():
        raise FileExistsError('Execution is single-use; retain partial stages and use a new run ID')
    # Retain the actual synthetic test output and counts before market outcomes.
    suite = unittest.defaultTestLoader.discover(str(STUDY / 'tests'))
    with (stage / 'numerical-tests.log').open('w') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    test_receipt = {'status': 'passed' if result.wasSuccessful() and result.testsRun > 0 and not result.skipped
                    and not result.expectedFailures and not result.unexpectedSuccesses else 'failed',
                    'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                    'skipped': len(result.skipped), 'expected_failures': len(result.expectedFailures),
                    'unexpected_successes': len(result.unexpectedSuccesses), 'at': utcnow(), 'command': sys.argv,
                    'log_sha256': digest(stage / 'numerical-tests.log'), 'source_freeze_sha256': digest(stage / 'freeze.json')}
    write_json(stage / 'numerical-tests.json', test_receipt)
    if test_receipt['status'] != 'passed':
        raise ValueError('Numerical tests did not pass completely; no outcomes executed')
    write_json(stage / 'execution-started.json', {'at': utcnow(), 'command': sys.argv, 'freeze_sha256': digest(stage / 'freeze.json')})
    daily, trade_rows, candidate_rows, event_rows, sensitivity_rows = [], [], [], [], []
    eligible = [s for s in sessions(stage) if s['eligible']]
    settings = read_json(stage / 'config.json')
    for session in eligible:
        found, events = candidates(session)
        selected = found[0] if found else None
        candidate_rows.extend(found)
        event_rows.extend(events)
        for entry in ('early', 'confirmed'):
            for mask in ('A', 'B', 'C', 'D'):
                for exit_policy in ('fixed_2r', 'verne'):
                    row = tag(session, simulate(session, selected, entry, mask, exit_policy))
                    daily.append(row)
                    if row['trade']:
                        trade_rows.append(row)
        for setting in settings['sensitivities']:
            changed, _ = candidates(session, proximity=setting.get('proximity', .10), stop_buffer=setting.get('stop_buffer', 1.0))
            candidate = changed[0] if changed else None
            for entry in ('early', 'confirmed'):
                sensitivity_rows.append(tag(session, simulate(session, candidate, entry, 'A', 'fixed_2r',
                                                               slippage=setting.get('slippage', 1)), setting['name']))
    for name, rows in [('daily', daily), ('trades', trade_rows), ('candidates', candidate_rows), ('episodes', event_rows),
                       ('sensitivities', sensitivity_rows)]:
        write_csv(stage / f'{name}.csv', rows)
    write_csv(stage / 'variants.csv', [{'variant_id': f'{entry}_{mask}_{exit_policy}', 'entry_policy': entry, 'mask': mask,
                                      'exit_policy': exit_policy} for entry in ('early', 'confirmed')
                                     for mask in ('A', 'B', 'C', 'D') for exit_policy in ('fixed_2r', 'verne')])
    summarize(stage)
    check_freeze(stage)
    write_json(stage / 'execution-complete.json', {'status': 'passed', 'at': utcnow(), 'eligible_sessions': len(eligible),
               'daily_rows': len(daily), 'trade_rows': len(trade_rows), 'candidate_rows': len(candidate_rows),
               'artifact_hashes': [{'path': name, 'sha256': digest(stage / name)} for name in
                                   ('daily.csv', 'trades.csv', 'candidates.csv', 'episodes.csv', 'sensitivities.csv', 'metrics.json')]})
    print('Executed', len(eligible), 'eligible sessions;', len(daily), 'baseline daily rows')


def verify(stage):
    from src.verification import verify_stage, verify_publication
    check_freeze(stage)
    verify_stage(stage)
    verify_publication(stage)
    check_freeze(stage)


def seal(stage):
    check_freeze(stage)
    for name in ('numerical-tests.json', 'execution-complete.json', 'scientific-verification.json',
                 'publication-verification.json', 'independent-publication-verification.json'):
        receipt = read_json(stage / name)
        if receipt.get('status') != 'passed':
            raise ValueError('Failed required receipt ' + name)
    # Verification rechecks saved values and exact publication/source identities.
    verify(stage)
    destination = ROOT / 'runs' / IDENTITY / stage.name
    if destination.exists():
        raise FileExistsError('Completed runs are immutable')
    freeze_receipt = read_json(stage / 'freeze.json')
    artifacts = [{'path': str(path.relative_to(stage)), 'sha256': digest(path), 'bytes': path.stat().st_size}
                 for path in sorted(stage.rglob('*')) if path.is_file() and path.name != 'manifest.json']
    write_json(stage / 'manifest.json', {'schema_version': 'opening-pivot-run/v1', 'study_id': IDENTITY, 'run_id': stage.name,
               'sealed_at': utcnow(), 'protocol_version': '1.0.0', 'git_revision': freeze_receipt['git_revision'],
               'worktree_dirty': freeze_receipt['worktree_dirty'], 'freeze_sha256': digest(stage / 'freeze.json'),
               'environment_lock_sha256': digest(ROOT / 'uv.lock'), 'exact_seal_command': sys.argv,
               'checks': ['numerical-tests.json', 'input-audit.json', 'scientific-verification.json',
                          'publication-verification.json', 'independent-publication-verification.json'],
               'artifacts': artifacts, 'retention': 'Local retained run; bulk ignored evidence requires separate backup',
               'qualifications': ['Historical level availability null/unverified', 'Native TradingView parity not established',
                                  'Retrospective temporal test; prior inspiration date 2026-09-15 retained']})
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage.rename(destination)
    print('Sealed:', destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['audit', 'freeze', 'execute', 'render', 'verify', 'seal'])
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    stage = stage_path(args.run_id)
    if args.phase == 'render':
        from src.reporting import report
        check_freeze(stage)
        report(stage, IDENTITY, stage.name)
        check_freeze(stage)
    else:
        globals()[args.phase](stage)


if __name__ == '__main__':
    main()
