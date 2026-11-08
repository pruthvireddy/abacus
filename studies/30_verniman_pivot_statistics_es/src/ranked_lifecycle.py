"""Fresh ranked-extension execution; baseline records and releases stay immutable."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta, datetime, timezone
import csv
import gzip
import json
import math
from pathlib import Path
import shutil
import sys

import lifecycle
from lifecycle import ROOT, STUDY, STUDY_ID, digest, dump, load, assert_frozen

BASELINE = ROOT / 'runs' / STUDY_ID / '20261031_repo_v2'


def load_inputs(stage):
    from abacus_bhishma.es_contract_session_indicators import load_release
    freeze = load(Path(stage) / 'freeze.json')
    pin = freeze['inputs']['session_indicators']
    frames = {name: load_release(Path(freeze['publication_root']), pin['path'], pin['sha256'], table=name)
              for name in ('bars1', 'bars3', 'bars5', 'quality')}
    grouped = {name: {str(day): frame for day, frame in frames[name].groupby('session_date', sort=False)}
               for name in ('bars1', 'bars3', 'bars5')}
    quality = {str(row['session_date']): row for row in frames['quality'].to_dict('records')}
    return frames, grouped, quality


def cohort_eligibility(day, q, minutes, three, five):
    """Source-independent readiness audit, deliberately without event outcomes."""
    from engine import _records, _Series, _snapshot, _quality_codes, _clock, _feature, IneligibleDay
    if q is None:
        return {'vwap_only_rth': False, 'vwap_only_full_globex': False,
                'rth_reasons': ['no_retained_market_session'], 'globex_reasons': ['no_retained_market_session']}
    contract = q['contract']
    if not contract:
        return {'vwap_only_rth': False, 'vwap_only_full_globex': False,
                'rth_reasons': ['unresolved_retained_contract'], 'globex_reasons': ['unresolved_retained_contract']}
    try:
        one, fast, slow = (_Series(_records(rows, contract, n)) for rows, n in ((minutes, 1), (three, 3), (five, 5)))
    except IneligibleDay as exc:
        return {'vwap_only_rth': False, 'vwap_only_full_globex': False,
                'rth_reasons': exc.codes, 'globex_reasons': exc.codes}
    # The arbitrary fixed reference is unused in quality tests: no pivot-based
    # outcome or source criterion enters the VWAP-only readiness decision.
    snapshots = [_snapshot(_clock(day, clock), label=label, day=day, contract=contract,
                           pivot=1., minute=one, three=fast, five=slow, opening_price=clock == '09:30')
                 for label, clock in (('0925', '09:25'), ('0930', '09:30'))]
    rth = _quality_codes(day, one, fast, slow, snapshots)
    if not (q['calendar_valid'] and q['rth_complete'] and q['anchor_to_rth_end_complete']):
        rth.append('incomplete_anchor_rth_or_uncertified_calendar')
    full = []
    if not q['full_globex_complete']:
        full.append('incomplete_full_globex_or_uncertified_calendar')
    if not fast.rows or any(_feature(row, 'ema6', 'ema6_ready') is None for row in fast.rows):
        full.append('unready_full_globex_ema6')
    if not one.rows or any(_feature(row, 'vwap', 'vwap_valid') is None for row in one.rows):
        full.append('unready_full_globex_vwap')
    return {'vwap_only_rth': not rth, 'vwap_only_full_globex': not full,
            'rth_reasons': sorted(set(rth)), 'globex_reasons': sorted(set(full))}


def _write_gzip(path, value):
    with Path(path).open('xb') as target:
        with gzip.GzipFile(fileobj=target, mode='wb', mtime=0) as stream:
            stream.write(json.dumps(value, sort_keys=True, allow_nan=False).encode())


def read_ranked(stage):
    stage = Path(stage)
    record = load(stage / 'ranked-execution.json')
    path = stage / 'ranked-ledgers.json.gz'
    if not path.exists():
        pins = load(stage / 'events.manifest.json')['artifacts']
        path = ROOT / next(p['path'] for p in pins if Path(p['path']).name == path.name)
    if digest(path) != record['ledger_sha256']:
        raise ValueError('ranked ledger bytes changed')
    with gzip.open(path, 'rt') as stream:
        return json.load(stream)


def audit(stage):
    stage = Path(stage)
    assert_frozen(stage)
    _, grouped, quality = load_inputs(stage)
    rows = []
    day = date(2020, 1, 1)
    while day <= date(2026, 10, 30):
        label = day.isoformat()
        q = quality.get(label)
        eligible = cohort_eligibility(label, q, *(grouped[k].get(label, []) for k in ('bars1', 'bars3', 'bars5')))
        rows.append({'session_date': label, 'retained_session': q is not None,
                     'contract': q['contract'] if q else None, **eligible})
        day += timedelta(days=1)
    dump(stage / 'ranked-coverage-audit.json', {'created_at': datetime.now(timezone.utc).isoformat(),
         'scope': 'source-independent coverage/readiness only; no new event/outcome calculations',
         'rows': rows, 'eligible_counts': {key: sum(row[key] for row in rows) for key in ('vwap_only_rth', 'vwap_only_full_globex')},
         'feature_manifest_sha256': load(stage / 'freeze.json')['inputs']['session_indicators']['sha256']})
    return load(stage / 'ranked-coverage-audit.json')['eligible_counts']


def execute(stage):
    from ranked_engine import build_ranked_day
    stage = Path(stage)
    assert_frozen(stage)
    if (stage / 'ranked-execution.json').exists():
        raise FileExistsError('ranked execution already exists')
    if not (stage / 'ranked-coverage-audit.json').exists():
        raise ValueError('coverage audit must precede outcomes')
    lifecycle.execute(stage)
    baseline = lifecycle.read_ledgers(stage)
    matched = {row['session_date']: row for row in baseline['daily']}
    _, grouped, quality = load_inputs(stage)
    coverage = load(stage / 'ranked-coverage-audit.json')['rows']
    result = {name: [] for name in ('daily', 'sections', 'events', 'snapshots', 'outcomes', 'recrosses', 'sequences', 'transitions')}
    for row in coverage:
        day = row['session_date']
        pivot = matched.get(day)
        row['pivot_matched_rth'] = pivot is not None
        if not (pivot or row['vwap_only_rth'] or row['vwap_only_full_globex']):
            continue
        output = build_ranked_day(day, quality[day]['contract'],
             *(grouped[key][day] for key in ('bars1', 'bars3', 'bars5')),
             pivot=pivot['pivot'] if pivot else None, pivot_matched=pivot is not None,
             vwap_rth=row['vwap_only_rth'], vwap_globex=row['vwap_only_full_globex'])
        for key, values in output.items():
            result.setdefault(key, []).extend(values)
    result['coverage'] = coverage
    _write_gzip(stage / 'ranked-ledgers.json.gz', result)
    dump(stage / 'ranked-execution.json', {'status': 'completed', 'command': sys.argv,
         'created_at': datetime.now(timezone.utc).isoformat(), 'freeze_sha256': digest(stage / 'freeze.json'),
         'coverage_audit_sha256': digest(stage / 'ranked-coverage-audit.json'),
         'ledger_sha256': digest(stage / 'ranked-ledgers.json.gz'), 'rows': {k: len(v) for k, v in result.items()}})
    return load(stage / 'ranked-execution.json')


def render(stage):
    from ranked_statistics import write_statistics
    stage = Path(stage)
    assert_frozen(stage)
    lifecycle.render(stage)
    ranked = read_ranked(stage)
    write_statistics(stage, ranked, lifecycle.read_ledgers(stage), bootstrap_replicates=2000)
    _report(stage, ranked)
    return load(stage / 'ranked-metrics.json')


def _report(stage, ranked):
    """Render only saved coverage/summary values, before publication and seal."""
    from reporting import write_csv, read_csv
    import html
    coverage = ranked['coverage']
    available = [r['session_date'] for r in coverage if r['retained_session']]
    rows = []
    for cohort in ('pivot_matched_rth', 'vwap_only_rth', 'vwap_only_full_globex'):
        days = [r['session_date'] for r in coverage if r[cohort]]
        rows.append({'cohort': cohort, 'requested_start': '2020-01-01', 'requested_end': '2026-10-30',
                     'available_start': min(available), 'available_end': max(available),
                     'eligible_sessions': len(days), 'eligible_start': min(days) if days else None,
                     'eligible_end': max(days) if days else None,
                     'excluded_requested_dates': len(coverage) - len(days),
                     'qualification': 'Requested dates include weekends and holidays; retrospective cohort rules, not prospective eligibility.'})
    write_csv(stage / 'tables/ranked_coverage_summary.csv', rows)
    summary = read_csv(stage / 'tables/ranked_summary.csv')
    counts = Counter(r['statistic_id'] for r in summary)
    if set(counts) != {f'S{i:02d}' for i in range(1, 21)}:
        raise ValueError('ranked summary must cover all 20 statistic IDs')
    dump(stage / 'implementation-coverage.json', {'status': 'completed', 'statistic_ids': dict(counts),
         'matrix_sha256': digest(STUDY / 'implementation-matrix.md'),
         'summary_sha256': digest(stage / 'tables/ranked_summary.csv'),
         'qualification': 'Implementation and saved summary coverage; independent verification is recorded separately.'})
    text = ['# Verniman Pivot Statistics — ES: ranked extension', '',
            'Requested calendar: 2020-01-01–2026-10-30. Retained repository market sessions: '
            f'{min(available)}–{max(available)}. No data acquired or release rebuilt.', '',
            '| Cohort | Eligible sessions | Actual eligible dates |', '|---|---:|---|']
    for row in rows:
        text.append(f"| {row['cohort']} | {row['eligible_sessions']} | {row['eligible_start']}–{row['eligible_end']} |")
    text += ['', 'The 20 ranked questions are defined in the retained implementation matrix and protocol 2.0.0. '
             'Full saved summaries are in tables/ranked_summary.csv. Public report tables and figures select those cells only. '
             'Each summary retains units, numerator, valid denominator, supporting days, missing/censored counts, dates and sparse status.', '',
             'The pivot-matched cohort is reconciled against the unchanged completed 20261031_repo_v2 baseline. '
             'Existing ema_events remain EMA6–pivot events. Actual EMA6–VWAP crossings use contemporaneous completed minute-HLC3/volume VWAP. '
             'RTH and Globex state initialization and populations remain explicit.', '',
             'Forward outcomes are RTH-only with 30 minutes primary and 15/60-minute context. '
             'Recent20/60/120 comparisons exclude each recent window from its preceding comparison. '
             'Intervals use 2,000 five-session day-block replicates with seed20261031; broad conditional views are exploratory. '
             'Historical pivot availability remains unverified and baseline results were viewed before this extension. '
             'No fills, costs or profitability are tested.', '',
             'Independent event/episode/exposure/summary verification, exact publication-cell transfer and local application checks '
             'are separate receipts. Read their actual scope and status; coverage alone does not establish validity.', '']
    (stage / 'ranked-report.md').write_text('\n'.join(text))
    (stage / 'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Verniman ES ranked statistics</title>'
        '<style>body{max-width:1000px;margin:40px auto;padding:20px;font:16px/1.6 system-ui;white-space:pre-wrap}</style><body>'
        + html.escape('\n'.join(text)) + '</body></html>')
    (stage / 'advice.md').write_text('# Dated interpretation — 2026-10-31\n\n'
        'These saved descriptions measure recurrence and price paths in retrospectively eligible retained ES sessions. '
        'Historical pivot availability is unverified. Prior results were viewed; new conditional findings are exploratory. '
        'No entry, fill, cost or net profitability experiment was performed. A tradable hypothesis requires a separate protocol.\n')


def _same(actual, expected, label, counts):
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            raise ValueError(f'baseline field set changed: {label}')
        for key in expected:
            _same(actual[key], expected[key], f'{label}/{key}', counts)
    elif isinstance(expected, list):
        if len(actual) != len(expected):
            raise ValueError(f'baseline row count changed: {label}')
        for i, (a, b) in enumerate(zip(actual, expected)):
            _same(a, b, f'{label}/{i}', counts)
    else:
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            valid = isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-8)
        else:
            valid = type(actual) is type(expected) and actual == expected
        if not valid:
            raise ValueError(f'baseline parity mismatch: {label}: {actual!r} != {expected!r}')
        counts['cells'] += 1


def parity(stage):
    from reporting import read_csv
    stage = Path(stage)
    counts = Counter()
    _same(lifecycle.read_ledgers(stage), lifecycle.read_ledgers(BASELINE), 'ledgers', counts)
    # The old run includes selected-download projections as well as numerical
    # tables. Reconstruct those projections from this run's recalculated
    # summaries without adding six more selected priority sources.
    missing = [p for p in (BASELINE / 'tables').glob('publication-*.csv') if not (stage / 'tables' / p.name).exists()]
    if missing:
        sys.path.insert(0, str(STUDY))
        import publish_web
        diagnostic = stage / 'baseline-projection-check'
        diagnostic.mkdir(exist_ok=False)
        (diagnostic / 'tables').mkdir()
        for item in load(stage / 'metrics.json')['source_tables'].values():
            shutil.copyfile(stage / item['artifact'], diagnostic / item['artifact'])
        shutil.copyfile(stage / 'metrics.json', diagnostic / 'metrics.json')
        shutil.copytree(stage / 'figures', diagnostic / 'figures')
        publish_web.prepare(diagnostic, load(stage / 'freeze.json')['run_id'])
        for path in (diagnostic / 'tables').glob('publication-*.csv'):
            destination = stage / 'tables' / path.name
            if destination.exists():
                raise FileExistsError(destination)
            shutil.copyfile(path, destination)
    tables = []
    for path in sorted((BASELINE / 'tables').glob('*.csv')):
        _same(read_csv(stage / 'tables' / path.name), read_csv(path), path.name, counts)
        tables.append({'path': str(path.relative_to(ROOT)), 'sha256': digest(path)})
    receipt = {'status': 'passed', 'baseline_run_id': BASELINE.name, 'baseline_manifest_sha256': digest(BASELINE / 'manifest.json'),
         'checked': dict(counts), 'tables': tables, 'absolute_tolerance': 1e-8, 'relative_tolerance': 1e-11,
         'qualification': 'Exact identities/nulls/booleans and all baseline ledger fields; numeric summary cells allow declared floating-point tolerance.'}
    dump(stage / 'baseline-parity.json', receipt)
    return receipt


def check_ranked_receipt(stage):
    """Bind an already successful independent check to the exact sealed bytes."""
    stage = Path(stage)
    ranked_receipt = load(stage / 'ranked-verification.json')
    if ranked_receipt.get('status') != 'passed':
        raise ValueError('ranked independent verification not passed')
    for path, expected in ((stage / 'ranked-ledgers.json.gz', ranked_receipt['ledger_sha256']),
                           (stage / 'ranked-execution.json', ranked_receipt['ranked_execution_sha256']),
                           (stage / 'freeze.json', ranked_receipt['freeze_sha256'])):
        if digest(path) != expected:
            raise ValueError('ranked scientifically verified evidence changed')
    if digest(stage / 'ranked-coverage-audit.json') != load(stage / 'ranked-execution.json')['coverage_audit_sha256']:
        raise ValueError('pre-outcome coverage audit changed')
    for record in ranked_receipt['summary_tables']:
        if digest(stage / record['path']) != record['sha256']:
            raise ValueError('ranked scientifically verified summary changed')
    return ranked_receipt


def seal(stage):
    stage = Path(stage).resolve()
    freeze = assert_frozen(stage)
    for name in ('scientific-verification.json', 'ranked-verification.json', 'baseline-parity.json', 'local-verification.json'):
        if load(stage / name).get('status') != 'passed':
            raise ValueError(f'required check not passed: {name}')
    from publish_ranked import verify as verify_publication
    check_ranked_receipt(stage)
    verify_publication(stage, run_id=freeze['run_id'])
    if digest(stage / 'ledgers.json.gz') != load(stage / 'scientific-verification.json')['ledger_sha256']:
        raise ValueError('baseline verified ledger changed')
    for record in load(stage / 'scientific-verification.json')['summary_tables']:
        if digest(stage / record['path']) != record['sha256']:
            raise ValueError('baseline verified summary changed')
    publications = list((stage / 'publications').glob('*/publication.json'))
    if len(publications) != 2:
        raise ValueError('two priority publication sources required')
    destination = ROOT / 'runs' / STUDY_ID / freeze['run_id']
    retained = ROOT / 'data/research/sahadeva' / STUDY_ID / freeze['run_id']
    if destination.exists() or retained.exists():
        raise FileExistsError('completed run or retained evidence exists')
    retained.mkdir(parents=True)
    artifacts = []
    for name in ('ledgers.json.gz', 'ranked-ledgers.json.gz'):
        path = retained / name
        shutil.copyfile(stage / name, path)
        if digest(path) != digest(stage / name):
            raise ValueError('retained evidence copy mismatch')
        artifacts.append({'path': str(path.relative_to(ROOT)), 'sha256': digest(path), 'bytes': path.stat().st_size})
    dump(stage / 'events.manifest.json', {'artifacts': artifacts, 'qualification': 'Retained private full evidence; no external backup asserted.'})
    for name in ('ledgers.json.gz', 'ranked-ledgers.json.gz'):
        (stage / name).unlink()
    inventory = [{'path': str(path.relative_to(stage)), 'sha256': digest(path), 'bytes': path.stat().st_size}
                 for path in sorted(stage.rglob('*')) if path.is_file()]
    dump(stage / 'manifest.json', {'study_id': STUDY_ID, 'run_id': freeze['run_id'], 'status': 'completed',
         'protocol_version': '2.0.0', 'created_at': datetime.now(timezone.utc).isoformat(), 'artifacts': inventory,
         'frozen_inputs': freeze['inputs'], 'data_policy': 'repository_only',
         'qualifications': ['Historical pivot availability unverified.', 'Prior baseline outcomes viewed; exploratory extension.',
                            'Retrospective source/calendar/coverage/readiness eligibility.', 'No fills, costs or profitability tested.']})
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(stage), destination)
    return str(destination)
