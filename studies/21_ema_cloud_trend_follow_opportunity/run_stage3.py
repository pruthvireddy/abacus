"""Explicit Stage 3 phases; frozen choices unlock each reserved assessment."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

import pandas as pd

from abacus_bhishma.paths import load_workspace_paths
from src.execution import assert_stage, file_record, record_command, verify_record, write_json
from src.stage3_execution import (BASELINES, STUDY_ID, assert_frozen, assert_input_bytes,
    assert_numerical_gate, authorize, freeze, freeze_phase, pin_baselines, write_once)
from src.stage3_baseline import save

STUDY = Path(__file__).resolve().parent
WORKSPACE = STUDY.parents[1]


def config(stage):
    return json.loads((stage / 'config.json').read_text())


def retained_root(stage):
    paths = load_workspace_paths(WORKSPACE)
    if paths.legacy_research_root is None:
        raise ValueError('retained research storage must be configured')
    return (paths.legacy_research_root / 'work' / STUDY_ID / stage.name).resolve()


def numerical_tests(stage):
    from run_stage2 import record_plot_context
    assert_frozen(stage, WORKSPACE)
    assert_input_bytes(stage)
    receipt = stage / 'provenance/stage3-numerical.json'
    if receipt.exists():
        raise ValueError('numerical receipt overwrite refused')
    record_plot_context(stage)
    env = {k: os.environ[k] for k in ('UV_CACHE_DIR', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
                                     'PYTHONPATH', 'MPLCONFIGDIR') if k in os.environ}
    study_result = stage / 'provenance/study21-numerical.json'
    feature_result = stage / 'provenance/bhishma-ema-numerical.json'
    if study_result.exists() or feature_result.exists():
        raise ValueError('actual numerical output overwrite refused')
    commands = [[str(WORKSPACE / 'scripts/check-workspace'), '--check', 'study-21', '--report', str(study_result)],
        [str(WORKSPACE / 'scripts/uv'), 'run', '--locked', '--no-sync', 'python', '-B',
         str(WORKSPACE / 'scripts/unittest_child.py'), '--spec', json.dumps({
             'start_dir': str(WORKSPACE / 'packages/bhishma/tests'),
             'names': ['test_ema_cloud', 'test_ema_cloud_release', 'test_ema_cloud_v2'], 'optimize': False}),
         '--result', str(feature_result)]]
    for label, command in zip(('study21', 'bhishma-ema'), commands):
        record_command(stage, command, WORKSPACE, env)
        with (stage / f'provenance/{label}-numerical.log').open('w') as log:
            status = subprocess.run(command, cwd=WORKSPACE, stdout=log, stderr=subprocess.STDOUT).returncode
        if status:
            raise ValueError('actual numerical fixtures failed: ' + label)
    study = json.loads(study_result.read_text())
    if study['outcome'] != 'passed' or len(study['checks']) != 1:
        raise ValueError('registered actual study fixture evidence incomplete')
    study = study['checks'][0]['unittest']
    feature = json.loads(feature_result.read_text())
    write_once(receipt, {'status': 'passed',
        'source_inventory': file_record(stage / 'provenance/source-inventory.json', stage),
        'input_lock': file_record(stage / 'inputs.lock.json', stage),
        'baseline_lock': file_record(stage / 'baseline.lock.json', stage),
        'suites': [{'name': name, 'status': result['outcome'], 'counts': result['counts'], 'result': file_record(path, stage)}
                  for name, result, path in (('study21', study, study_result), ('bhishma-ema', feature, feature_result))],
        'scope': 'Actual TestResult in separate owned locked processes without sync; no scientific or publication validation inferred.'})
    assert_numerical_gate(stage)
    assert_frozen(stage, WORKSPACE)
    print(json.dumps({'numerical': 'passed', 'study': study['counts'], 'features': feature['counts']}), flush=True)


def mapped_cells(stage, cell=None):
    records = json.loads((stage / 'mapped.manifest.json').read_text())['records']
    for record in records:
        if cell is not None and (record['product'], record['interval_minutes']) != tuple(cell):
            continue
        yield record['product'], record['interval_minutes'], pd.read_parquet(verify_record(record))


def audit_inputs(stage):
    from abacus_bhishma.ema_cloud_loader_v2 import load_release
    from src.engine import map_features
    assert_frozen(stage, WORKSPACE)
    assert_numerical_gate(stage)
    assert_input_bytes(stage)
    if (stage / 'mapped.manifest.json').exists():
        raise ValueError('mapped input overwrite refused')
    paths = load_workspace_paths(WORKSPACE)
    lock = json.loads((stage / 'inputs.lock.json').read_text())
    delivery = lock['delivery']
    baseline = WORKSPACE / 'runs' / STUDY_ID / BASELINES['stage2']
    original = json.loads((baseline / 'events.manifest.json').read_text())['records']
    end = pd.Timestamp('2021-01-01T00:00:00-05:00').tz_convert('UTC')
    records, comparisons, coverage = [], [], []
    for product in config(stage)['products']:
        five = load_release(paths.publication_root, product=product, interval=5,
            manifest_path=delivery['path'], expected_manifest_sha256=delivery['sha256'])
        for interval in config(stage)['interval_minutes']:
            source = five if interval == 5 else load_release(paths.publication_root, product=product, interval=interval,
                manifest_path=delivery['path'], expected_manifest_sha256=delivery['sha256'])
            full = map_features(source, five, interval)
            old_record = next(r for r in original if r['role'] == 'bars' and r['product'] == product and r['interval_minutes'] == interval)
            old = pd.read_parquet(verify_record(old_record))
            prefix = full.loc[full.available_at.le(end)].reset_index(drop=True)
            pd.testing.assert_frame_equal(old, prefix, check_exact=True, check_dtype=True)
            comparisons.append({'product': product, 'interval_minutes': interval, 'old_rows': len(old),
                'full_rows': len(full), 'columns': list(old), 'compared_cells': len(old) * len(old.columns),
                'tolerance': 0, 'mismatch_count': 0, 'old': old_record})
            records.append(save(full, retained_root(stage) / 'mapped' / f'{product}_{interval}m.parquet', 'bars', product, interval))
            local_year = full.timestamp.dt.tz_convert('America/New_York').dt.year
            for year, group in full.groupby(local_year, sort=True):
                ready = group.usable.fillna(False) & group.feature_valid.fillna(False)
                atr = pd.to_numeric(group.atr14, errors='coerce')
                coverage.append({'row_id': f'S3-T00|{product}|{interval}|{year}', 'stage': 3,
                    'product': product, 'interval_minutes': interval, 'year': int(year),
                    'scope': 'causal_warmup_input_only' if year == 2017 else 'input_only',
                    'scheduled_slots': len(group), 'usable_slots': int(group.usable.fillna(False).sum()),
                    'calendar_uncertified_slots': int((~group.calendar_valid.fillna(False)).sum()),
                    'feature_ready_slots': int(ready.sum()), 'mapped_ready_slots': int(ready.sum()),
                    'atr_valid_slots': int((ready & atr.gt(0) & atr.lt(float('inf'))).sum()),
                    'ready_share': float(ready.mean()), 'usable_share': float(group.usable.fillna(False).mean()),
                    'unknown_signal_slots': int((~ready).sum()), 'contributing_sessions': group.session.nunique(),
                    'ready_sessions': group.loc[ready, 'session'].nunique(),
                    'first_timestamp': group.timestamp.iloc[0].isoformat(),
                    'last_available_at': group.available_at.iloc[-1].isoformat(),
                    'coverage_complete': bool(ready.all()),
                    'quality_counts': json.dumps({str(k): int(v) for k, v in group.quality_reason.value_counts().items()}, sort_keys=True)})
            print(json.dumps({'mapped': f'{product}/{interval}m', 'old_prefix_rows': len(old), 'full_rows': len(full)}), flush=True)
    write_once(stage / 'mapped.manifest.json', {'schema_version': 'study21.stage3-mapped-inputs/v1', 'records': records,
        'scope': 'Input-only full canonical roster and causal mapping; no entry or outcomes calculated.'})
    (stage / 'tables').mkdir(exist_ok=True)
    pd.DataFrame(coverage).to_csv(stage / 'tables/S3-T00_coverage.csv', index=False, float_format='%.17g')
    write_once(stage / 'provenance/input-prefix-parity.json', {'status': 'passed',
        'records': [file_record(stage / 'mapped.manifest.json', stage), file_record(stage / 'inputs.lock.json', stage),
                    file_record(stage / 'tables/S3-T00_coverage.csv', stage)],
        'external_records': records,
        'release_prefix_receipt': lock['input_prefix_parity'], 'mapped_comparisons': comparisons,
        'compared_cells': sum(c['compared_cells'] for c in comparisons), 'tolerance': 0, 'mismatch_count': 0,
        'outcomes_computed': False, 'state_reset_at_split': False})
    assert_frozen(stage, WORKSPACE)


def gate_specs(cfg, product):
    from src.stage3_events import gate_spec
    return [gate_spec('absolute', x) for x in cfg['absolute_gates'][product]] + [gate_spec('atr', x) for x in cfg['atr_gates']]


def development_gates(cfg):
    return [(p, i, t, g['gate_id']) for p in cfg['products'] for i in cfg['interval_minutes']
            for t in cfg['touch_modes'] for g in gate_specs(cfg, p)]


def choice_gates(frame, cfg):
    from src.stage3_selection import fixed_gate_id
    # The saved choice column is defined by B; caller passes one twelve-cell
    # table whose chosen gate is the sole candidate alongside its own baseline.
    field = 'selected_gate_id' if 'selected_gate_id' in frame else 'final_gate_id' if 'final_gate_id' in frame else 'nominee_gate_id'
    if field not in frame:
        raise ValueError('saved frozen choice gate column absent')
    result = set()
    for row in frame.to_dict('records'):
        cell = row['product'], int(row['interval_minutes']), row['touch_mode']
        result.add((*cell, row[field]))
        result.add((*cell, fixed_gate_id(cell[0], cfg)))
    if len(frame) != 12 or frame.duplicated(['product', 'interval_minutes', 'touch_mode']).any():
        raise ValueError('exact twelve-cell frozen choices required')
    return sorted(result)


def gateway_iterator(stage, period, allowed, *, cell=None, manifest_path=None):
    from src.stage3_events import generate_gateway_stream
    from src.stage3_masks import boundary
    cfg = config(stage)
    records = []
    old_mapped = json.loads((stage / 'mapped.manifest.json').read_text())['records']
    if cell is not None:
        old_mapped = [r for r in old_mapped if (r['product'], r['interval_minutes']) == tuple(cell)]
    records.extend(old_mapped)
    manifest = Path(manifest_path) if manifest_path is not None else stage / f'acceptance-{period}.manifest.json'
    if manifest.exists():
        raise ValueError('gateway acceptance phase overwrite refused')
    for product, interval, full in mapped_cells(stage, cell=cell):
        causal = full.loc[full.available_at.le(boundary(cfg['periods'][period]['end']))].reset_index(drop=True)
        specs = {g['gate_id']: g for g in gate_specs(cfg, product)}
        cell_gates = [x for x in allowed if x[:2] == (product, interval)]
        for _, _, touch, gate_id in cell_gates:
            payload = generate_gateway_stream(causal, interval, touch, specs[gate_id])
            technical, events = payload['technical'], payload['events']
            prefix = retained_root(stage) / period / f'{product}_{interval}m_{touch}_{gate_id}'
            # Keep native mapped bars once, with every scientific state field
            # retained in the compact linked decision roster.
            keep = [c for c in technical if c not in full or c in ('product', 'timestamp', 'interval_minutes')]
            for role, frame in (('technical', technical[keep]), ('events', events)):
                record = save(frame, prefix.with_name(prefix.name + '_' + role + '.parquet'), role, product, interval, touch)
                record.update(touch_mode=touch, gate_id=gate_id, period=period, gate=specs[gate_id])
                records.append(record)
            payload['bars'] = full
            yield payload
            print(json.dumps({'acceptance_phase': period, 'cell': f'{product}/{interval}m/{touch}/{gate_id}', 'causal_accepted': len(events)}), flush=True)
    write_once(manifest, {'schema_version': 'study21.stage3-acceptance/v1', 'period': period, 'records': records,
        'technical_scope': 'Causal 2017-to-phase-end prefix; state fields joined to full input-only bars by timestamp; no outcome eligibility changes acceptance.'})


def verify_phase(stage, phase):
    from src.stage3_reconcile import verify_bundle
    assert_frozen(stage, WORKSPACE)
    path = stage / f'provenance/independent-{phase}.json'
    if path.exists():
        raise ValueError('independent phase receipt overwrite refused')
    if phase == 'development' and config(stage).get('independent_development_workers', 1) > 1:
        from src.stage3_parallel_reconcile import verify_bundle as verify_parallel
        receipt = verify_parallel(stage, phase, workers=config(stage)['independent_development_workers'])
    else:
        receipt = verify_bundle(stage, phase)
    write_once(path, receipt)
    if receipt.get('status') != 'passed' or receipt.get('phase') != phase:
        raise ValueError('independent phase verification failed')
    assert_frozen(stage, WORKSPACE)


def frozen_choice_phase(stage, phase):
    if phase == 'development' and config(stage).get('development_workers', 1) > 1:
        from src.stage3_execution import _verify_receipt
        _verify_receipt(stage, 'reviews/serial-parallel-development-parity.json')
    cfg = config(stage)
    if phase == 'development':
        frame = pd.read_csv(stage / 'tables/S3-T13_development_nominees.csv')
    else:
        frame = pd.read_csv(stage / 'tables/S3-T13_validation_decisions.csv')
    gates = choice_gates(frame, cfg)
    paths = [stage / f'acceptance-{phase}.manifest.json', stage / f'stage3-{phase}.manifest.json']
    if phase == 'development' and cfg.get('development_recovery'):
        from src.stage3_execution import _verify_receipt
        for name in ('adopted-recovery-packets.json', 'development-recovery-freeze.json',
                     'development-recovery-completion.json'):
            _verify_receipt(stage, name)
            paths.append(stage / 'provenance' / name)
    if phase == 'development':
        paths += list((stage / 'tables').glob('S3-*development*'))
        paths += [stage / 'tables/S3-T15_neighborhood_frontiers.csv']
        paths += [p for p in (stage / 'shortlist.json', stage / 'development-shortlist.json') if p.exists()]
    elif phase == 'validation':
        paths += list((stage / 'tables').glob('S3-*validation*'))
        paths += [p for p in (stage / 'final-choices.json',) if p.exists()]
    else:
        paths += list((stage / 'tables').glob('S3-*final*'))
        paths.append(freeze_final_assessment(stage))
    paths += list((stage / 'ledgers/stage3' / phase).rglob('*.parquet'))
    external = json.loads((stage / f'acceptance-{phase}.manifest.json').read_text())['records']
    freeze_phase(stage, WORKSPACE, phase, paths, stage / f'provenance/independent-{phase}.json', gates, external)



def freeze_final_assessment(stage):
    """Fix the primary final interpretation before inspecting recent outcomes."""
    from datetime import datetime, timezone
    from src.stage3_execution import _verify_receipt
    _verify_receipt(stage, 'independent-final.json')
    path = stage / 'tables/S3-T14_final_effects.csv'
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    primary = frame.loc[frame.horizon.eq('15') & frame.direction.eq('All') & frame.unit.eq('atr') &
                        frame.metric.eq('terminal_delta') & frame.weighting.eq('event') &
                        frame.block_weeks.eq('4') & frame.interval_kind.eq('bonferroni12')]
    if len(primary) != 12 or primary.duplicated(['product', 'interval_minutes', 'touch_mode']).any():
        raise ValueError('exact twelve-cell final assessment family required')
    cells = {(p, str(i), b) for p in ('ES', 'GC', 'NQ') for i in (3, 5) for b in ('fast', 'slow')}
    if set(primary[['product', 'interval_minutes', 'touch_mode']].itertuples(index=False, name=None)) != cells:
        raise ValueError('final assessment family identities differ')
    counts = dict(includes_zero=0, above_zero=0, below_zero=0, undefined=0)
    for row in primary.to_dict('records'):
        if row['ci_low'] == '' or row['ci_high'] == '':
            counts['undefined'] += 1
        elif float(row['ci_low']) > 0:
            counts['above_zero'] += 1
        elif float(row['ci_high']) < 0:
            counts['below_zero'] += 1
        else:
            counts['includes_zero'] += 1
    conclusion = (f"The twelve prespecified final H15 comparisons have {counts['includes_zero']} adjusted intervals including zero, "
        f"{counts['above_zero']} entirely above zero, {counts['below_zero']} entirely below zero and {counts['undefined']} undefined. "
        "These compare each frozen gateway’s own accepted observations with its fixed-width baseline; they do not establish executable profitability.")
    destination = stage / 'provenance/final-assessment.json'
    write_once(destination, {'status': 'frozen_final_assessment_before_recent',
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'period': 'final',
        'records': [file_record(path, stage), file_record(stage / 'provenance/independent-final.json', stage)],
        'family': config(stage)['primary_comparison_family'], 'classification': counts,
        'primary_rows': primary.to_dict('records'), 'conclusion': conclusion,
        'interpretation': 'Primary family remains all12 cells. Identity fallback is not improvement; undefined stays null. Recent evidence cannot retune or replace this final assessment.'})
    return destination


def build_manifest(stage):
    from src.pipeline import build_manifest as inherited
    result = inherited(stage)
    result['external_artifacts'] = [{'id': str(i), 'locator': r['path'], 'bytes': r['bytes'], 'sha256': r['sha256']}
                                   for i, r in enumerate(json.loads((stage / 'events.manifest.json').read_text())['records'])
                                   if Path(r['path']).is_absolute()]
    return result


def finalize_evidence(stage):
    """Inventory completed phase ledgers without altering phase-gate evidence."""
    records = []
    seen = set()
    phases = {}
    for phase in ('development', 'validation', 'final', 'recent'):
        acceptance = stage / f'acceptance-{phase}.manifest.json'
        outcomes = stage / f'stage3-{phase}.manifest.json'
        for path in (acceptance, outcomes):
            value = json.loads(path.read_text())
            for record in value['records']:
                if record['path'] in seen:
                    continue
                seen.add(record['path'])
                records.append(record)
        phases[phase] = {'acceptance': file_record(acceptance, stage), 'outcomes': file_record(outcomes, stage)}
    fixed = json.loads((stage / 'provenance/fixed-baseline-parity.json').read_text())
    for record in fixed['retained_records']:
        if record['path'] not in seen:
            records.append(record | {'period_id': 'fixed_reproduction'})
            seen.add(record['path'])
    restart = stage / 'provenance/reviews/serial-parallel-development-parity.json'
    if restart.exists():
        for record in json.loads(restart.read_text()).get('retained_original_records', []):
            if record['path'] not in seen:
                records.append(record | {'role': 'diagnostic_serial_development_' + record.get('role', 'artifact'),
                    'source_run_id': '20261011T023748Z_s3_5a9d', 'scope': 'retained_partial_attempt_not_used_for_selection'})
                seen.add(record['path'])
    for record in records:
        verify_record(record, None if Path(record['path']).is_absolute() else stage)
    write_once(stage / 'events.manifest.json', {'schema_version': 'study21.stage3-complete-evidence/v1',
        'study_id': STUDY_ID, 'run_id': stage.name, 'records': records, 'phase_manifests': phases,
        'qualification': 'Declared local and explicitly retained external evidence; off-device backup unverified.'})
    cfg = config(stage)
    write_once(stage / 'metrics.json', {'study_id': STUDY_ID, 'run_id': stage.name, 'stage': 3,
        'results': 'exploratory_development_and_frozen_sequential_price_paths',
        'development_grid_cells': 2688, 'primary_family': cfg['primary_comparison_family'],
        'input_release': json.loads((stage / 'inputs.lock.json').read_text())['delivery'],
        'baseline_runs': BASELINES, 'periods': cfg['periods'],
        'choices': 'tables/S3-T13_validation_decisions.csv',
        'phase_evidence': phases, 'numerical_values': 'Saved tables and stable row selectors are authoritative; no trading profitability tested.'})
    write_once(stage / 'exclusions.json', {'input_calendar_and_quality': 'tables/S3-T00_coverage.csv',
        'phase_masks': [f'tables/S3-T16_{p}_masks.csv' for p in phases],
        'failed_development_guards': 'tables/S3-T12_development_fold_eligibility.csv',
        'failed_validation_guards': 'tables/S3-T12_validation_fold_eligibility.csv',
        'scope': 'Canonical100-slot embargo, endpointpurge, ATR scoring and pathcensoring follow independent acceptance; no entry state reset or future eligibility filter.'})
    write_once(stage / 'provenance/external-bytes.json', {'status': 'passed',
        'records': [r for r in records if Path(r['path']).is_absolute()],
        'verified': sum(Path(r['path']).is_absolute() for r in records),
        'scope': 'Explicit retained local external evidence bytes; no off-device backup certification.'})


def seal(stage):
    assert_frozen(stage, WORKSPACE)
    assert_input_bytes(stage)
    assert_numerical_gate(stage)
    from src.stage3_execution import _verify_receipt
    for name in ('development-frozen.json', 'validation-frozen.json', 'final-assessment-frozen.json',
                 'independent-complete.json', 'publication-dry-run.json'):
        _verify_receipt(stage, name)
    _verify_receipt(stage, 'checks-pins.json')
    checks = json.loads((stage / 'provenance/checks.json').read_text())
    required = {'study21-numerical', 'bhishma-ema-numerical', 'baseline-input-identities',
        'input-prefix-parity', 'fixed-baseline-parity', 'independent-development', 'independent-validation',
        'independent-final', 'independent-recent', 'scientific-reconciliation', 'independent-uncertainty',
        'external-ledger-bytes', 'report-transfer', 'publication-dry-run',
        'independent-mapping-review', 'independent-fixed-review'}
    if config(stage).get('development_workers', 1) > 1:
        required.update({'adopted-preparation', 'serial-parallel-development-parity'})
        _verify_receipt(stage, 'adopted-preparation.json')
        _verify_receipt(stage, 'reviews/serial-parallel-development-parity.json')
    if config(stage).get('development_recovery'):
        required.update({'recovery-adoption', 'recovery-freeze', 'recovery-completion'})
        for name in ('adopted-recovery-packets.json', 'development-recovery-freeze.json',
                     'development-recovery-completion.json'):
            _verify_receipt(stage, name)
    if not required <= {c['name'] for c in checks if c['status'] == 'passed'}:
        raise ValueError('required complete Stage 3 sealing checks absent')
    for record in json.loads((stage / 'events.manifest.json').read_text())['records']:
        verify_record(record, None if Path(record['path']).is_absolute() else stage)
    for b in json.loads((stage / 'baseline.lock.json').read_text())['baselines']:
        verify_record(b['manifest'])
        for r in b['external_records']:
            verify_record(r)
    write_once(stage / 'manifest.json', build_manifest(stage))
    sys.path.insert(0, str(WORKSPACE / 'scripts'))
    from evidence_contract import assess_bundle
    assessment = assess_bundle(stage)
    if assessment['status'] != 'verified_declared_artifacts':
        raise ValueError('declared bundle integrity failed: ' + json.dumps(assessment))
    destination = WORKSPACE / 'runs' / STUDY_ID / stage.name
    if destination.exists():
        raise ValueError('completed run overwrite refused')
    shutil.move(str(stage), str(destination))
    print(json.dumps({'sealed': str(destination), 'integrity': assessment['status']}), flush=True)



def publication_check(stage):
    """Actual private publisher dry run with immutable before/after asset pins."""
    assert_frozen(stage, WORKSPACE)
    target = stage / 'provenance/publication-dry-run.json'
    if target.exists():
        raise ValueError('publication dry-run receipt overwrite refused')
    publication = json.loads((stage / 'publication.json').read_text())
    paths = [stage / 'publication.json', stage / 'source-bindings.json']
    paths += [stage / x['path'] for x in publication['sections'] if x['kind'] == 'figure']
    paths += [stage / x['path'] for x in publication.get('downloads', [])]
    before = [file_record(path, stage) for path in paths]
    node_root = Path('/Users/ppanati/.nvm/versions/node/v24.18.0/bin')
    environment = os.environ.copy()
    environment['PATH'] = str(node_root) + os.pathsep + environment['PATH']
    command = [str(node_root / 'npm'), 'run', 'report:publish', '--', '--report',
               str(stage / 'publication.json'), '--dry-run']
    cwd = WORKSPACE / 'apps/narada'
    record_command(stage, command, cwd, {'PATH_prefix': str(node_root)})
    log = stage / 'provenance/publication-dry-run.log'
    with log.open('w') as output:
        result = subprocess.run(command, cwd=cwd, env=environment, stdout=output, stderr=subprocess.STDOUT)
    for pin in before:
        verify_record(pin, stage)
    receipt = {'status': 'passed' if result.returncode == 0 else 'failed', 'returncode': result.returncode,
        'command': command, 'cwd': str(cwd), 'log': file_record(log, stage), 'records': before,
        'node': subprocess.check_output([str(node_root / 'node'), '--version'], text=True).strip(),
        'sections': len(publication['sections']), 'figures': sum(s['kind'] == 'figure' for s in publication['sections']),
        'downloads': len(publication.get('downloads', [])),
        'scope': 'Read-only selected private Narada 1.1 source/content/assets dry run; no public staging, catalog mutation or deployment.'}
    write_once(target, receipt)
    if result.returncode:
        raise ValueError('private publisher dry run failed; actual diagnostics retained')
    assert_frozen(stage, WORKSPACE)


def assemble_checks(stage):
    """Record actual completed gates, retaining prerequisite and sandbox failures."""
    assert_frozen(stage, WORKSPACE)
    destination = stage / 'provenance/checks.json'
    if destination.exists():
        raise ValueError('check inventory overwrite refused')
    checks = []
    pins = []
    def add(name, path, status, reason):
        if not (stage / path).is_file():
            raise ValueError('actual check record absent: ' + path)
        checks.append({'name': name, 'status': status, 'record': path, 'reason': reason})
        pins.append(file_record(stage / path, stage))
    for name, file in (('workspace-default', 'default-checks.json'),
                       ('remaining-default', 'remaining-default-checks.json'),
                       ('tooling', 'tooling-checks.json'),
                       ('study-integration-preliminary', 'study-integration-checks.json'),
                       ('narada-initial', 'narada-checks.json'),
                       ('narada-permitted', 'narada-permitted-checks.json')):
        path = 'provenance/preparation/' + file
        result = json.loads((stage / path).read_text())
        add(name, path, result['outcome'], 'Actual registered preparation gate; scope/counts/diagnostics and omitted checks retained in its report. Historical reconstruction prerequisites are not repaired or inferred from retained-byte validity.')
    baseline = json.loads((stage / 'baseline.lock.json').read_text())
    add('baseline-input-identities', 'baseline.lock.json', baseline['status'], 'Both declared completed baseline inventories, handoff pins and external bytes verified; immutable old delivery and executed kernels pinned.')
    numeric = assert_numerical_gate(stage)
    for suite in numeric['suites']:
        name = 'study21-numerical' if suite['name'] == 'study21' else 'bhishma-ema-numerical'
        add(name, suite['result']['path'], suite['status'], 'Actual separate owned locked-process TestResult bound to frozen source/input/baseline: ' + json.dumps(suite['counts'], sort_keys=True))
    for name in ('input-prefix-parity', 'fixed-baseline-parity'):
        path = 'provenance/' + name + '.json'
        result = json.loads((stage / path).read_text())
        add(name, path, result['status'], 'Exact scientific identities and values at declared original endpoint; wrappers/exclusions and original table estimands retained explicitly.')
    if config(stage).get('development_workers', 1) > 1:
        for name, path in (('adopted-preparation', 'provenance/adopted-preparation.json'),
                           ('serial-parallel-development-parity', 'provenance/reviews/serial-parallel-development-parity.json')):
            result = json.loads((stage / path).read_text())
            if result.get('status') != 'passed':
                raise ValueError('parallel restart lineage/parity incomplete')
            add(name, path, result['status'], 'Explicit retained serial-attempt disposition; unchanged scientific settings/kernels and exact partial-stream equality. All192 independent streams verified before selection; interrupted execution attribution remains explicit.')
    if config(stage).get('development_recovery'):
        from src.stage3_execution import _verify_receipt
        for name, file in (('recovery-adoption', 'adopted-recovery-packets.json'),
                           ('recovery-freeze', 'development-recovery-freeze.json'),
                           ('recovery-completion', 'development-recovery-completion.json')):
            result = _verify_receipt(stage, file)
            add(name, 'provenance/' + file, result['status'],
                'Exact original-source187-packet adoption, separately frozen recovery execution and complete original-order192-stream closure; no scientific parameter or reserved-period gate changed.')
    for name, file in (('independent-mapping-review', 'mapped-feature-review.json'),
                       ('independent-fixed-review', 'fixed-baseline-review.json')):
        path = 'provenance/reviews/' + file
        result = json.loads((stage / path).read_text())
        if result.get('status') != 'passed':
            raise ValueError('independent input/baseline saved-value review incomplete')
        add(name, path, result['status'], 'Independent exact saved-value audit with before/after source/input identities; scope and cells/fields retained in the actual receipt.')
    for phase in ('development', 'validation', 'final', 'recent'):
        path = 'provenance/independent-' + phase + '.json'
        result = json.loads((stage / path).read_text())
        if result.get('phase') != phase or not result.get('checks') or any(x['status'] != 'passed' for x in result['checks']):
            raise ValueError('actual independent phase calculations incomplete')
        add('independent-' + phase, path, result['status'], 'Independent saved full state, acceptance, scalar paths/masks, summaries/support, guards/decisions and phase uncertainty as explicitly inventoried.')
    complete = json.loads((stage / 'provenance/independent-complete.json').read_text())
    if complete.get('phase') != 'complete' or any(x['status'] != 'passed' for x in complete['checks']):
        raise ValueError('complete independent result incomplete')
    add('scientific-reconciliation', 'provenance/independent-complete.json', complete['status'], 'All independent phase calculations retained through exact source/input/output byte rechecks; full scientific inventory verified.')
    uncertainty = [x for x in complete['checks'] if x['check'] == 'independent_paired_period_week_uncertainty']
    if {x['phase'] for x in uncertainty} != {'validation', 'final', 'recent'}:
        raise ValueError('independent uncertainty periods incomplete')
    add('independent-uncertainty', 'provenance/independent-complete.json', 'passed', 'Independent paired calendar-week bootstrap and exact twelve-cell final multiplicity; estimable identities and undefined draws retained.')
    transfer = [x for x in complete['checks'] if x['check'] == 'exact_saved_publication_transfer']
    if len(transfer) != 1:
        raise ValueError('saved report transfer verification absent')
    add('report-transfer', 'provenance/independent-complete.json', 'passed', 'Exact saved cells, claims, figures, four downloads and private cross-run baseline attribution verified independently.')
    for name, file in (('external-ledger-bytes', 'external-bytes.json'), ('publication-dry-run', 'publication-dry-run.json')):
        path = 'provenance/' + file
        result = json.loads((stage / path).read_text())
        add(name, path, result['status'], result['scope'])
    write_once(destination, checks)
    write_once(stage / 'provenance/checks-pins.json', {'status': 'passed', 'records': pins + [file_record(destination, stage)]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['pin', 'freeze', 'test', 'audit', 'baseline-parity', 'development',
        'verify-development', 'freeze-shortlist', 'validation', 'verify-validation', 'freeze-final',
        'final', 'verify-final', 'freeze-final-assessment', 'recent', 'verify-recent', 'verify', 'render', 'publication-check', 'checks', 'seal'])
    parser.add_argument('--stage', type=Path, required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    assert_stage(stage, WORKSPACE)
    stage.mkdir(parents=True, exist_ok=True)
    env = {k: os.environ[k] for k in ('UV_CACHE_DIR', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
                                     'PYTHONPATH', 'MPLCONFIGDIR') if k in os.environ}
    record_command(stage, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], WORKSPACE, env)
    phase = args.phase
    if phase == 'pin':
        pin_baselines(stage, WORKSPACE)
    elif phase == 'freeze':
        freeze(stage, WORKSPACE, STUDY)
    elif phase == 'test':
        numerical_tests(stage)
    elif phase == 'audit':
        audit_inputs(stage)
    elif phase == 'baseline-parity':
        from src.stage3_baseline import reproduce
        reproduce(stage, WORKSPACE, mapped_cells(stage), retained_root(stage) / 'fixed-parity')
    elif phase == 'development':
        from src.stage3_statistics import produce_development
        cfg = config(stage)
        gates = development_gates(cfg)
        authorization = authorize(stage, WORKSPACE, 'development', gates)
        if cfg.get('development_recovery'):
            from src.stage3_execution import _verify_receipt
            from src.stage3_recovery import recover_development
            _verify_receipt(stage, 'adopted-preparation.json')
            _verify_receipt(stage, 'adopted-recovery-packets.json')
            _verify_receipt(stage, 'development-recovery-freeze.json')
            recover_development(stage, cfg, authorization,
                               stage / 'provenance/development-recovery-freeze.json')
        elif cfg.get('development_workers', 1) > 1:
            from src.stage3_execution import _verify_receipt
            from src.stage3_parallel_execution import produce_development_parallel
            _verify_receipt(stage, 'adopted-preparation.json')
            produce_development_parallel(stage, cfg, authorization, workers=cfg['development_workers'])
        else:
            produce_development(stage, cfg, gateway_iterator(stage, 'development', gates), authorization)
        assert_input_bytes(stage)
        assert_frozen(stage, WORKSPACE)
    elif phase in ('validation', 'final', 'recent'):
        from src.stage3_statistics import evaluate_period
        cfg = config(stage)
        choice = 'S3-T13_development_nominees.csv' if phase == 'validation' else 'S3-T13_validation_decisions.csv'
        choices = pd.read_csv(stage / 'tables' / choice)
        gates = choice_gates(choices, cfg)
        authorization = authorize(stage, WORKSPACE, phase, gates)
        if cfg.get('evaluation_workers', 1) > 1:
            from src.stage3_parallel_execution import evaluate_period_parallel
            evaluate_period_parallel(stage, cfg, choices, phase, authorization, workers=cfg['evaluation_workers'])
        else:
            evaluate_period(stage, cfg, choices, phase, authorization, gateway_iterator(stage, phase, gates))
        assert_input_bytes(stage)
        assert_frozen(stage, WORKSPACE)
        if phase == 'recent':
            finalize_evidence(stage)
    elif phase.startswith('verify-'):
        verify_phase(stage, phase.removeprefix('verify-'))
    elif phase in ('freeze-shortlist', 'freeze-final', 'freeze-final-assessment'):
        frozen_choice_phase(stage, {'freeze-shortlist': 'development', 'freeze-final': 'validation', 'freeze-final-assessment': 'final'}[phase])
    elif phase == 'verify':
        verify_phase(stage, 'complete')
    elif phase == 'render':
        from src.stage3_reporting import render_bundle
        from run_stage2 import record_plot_context
        assert_frozen(stage, WORKSPACE)
        record_plot_context(stage)
        write_once(stage / 'provenance/render-receipt.json', render_bundle(stage, stage.name))
        assert_frozen(stage, WORKSPACE)
    elif phase == 'publication-check':
        publication_check(stage)
    elif phase == 'checks':
        assemble_checks(stage)
    elif phase == 'seal':
        seal(stage)


if __name__ == '__main__':
    main()
