"""Explicit Stage 2 phases; fast outcomes require exact inherited slow parity."""
from pathlib import Path
import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys

import pandas as pd

from abacus_bhishma.ema_cloud import load_release
from abacus_bhishma.paths import load_workspace_paths
from src.execution import assert_stage, file_record, record_command, verify_record, write_json
from src.stage2_contract import BASELINE_RUN_ID, STUDY_ID, TABLES
from src.stage2_execution import assert_frozen_sources, assert_numerical_gate, freeze, pin_baseline

STUDY = Path(__file__).resolve().parent
WORKSPACE = STUDY.parents[1]
BASELINE = WORKSPACE / 'runs' / STUDY_ID / BASELINE_RUN_ID


def config(stage):
    return json.loads((stage / 'config.json').read_text())


def manifest_records(stage):
    for name in ('events.manifest.json', 'slow-evidence.manifest.json', 'acceptance.manifest.json'):
        if (stage / name).exists():
            return json.loads((stage / name).read_text())['records']
    raise ValueError('no saved ledger phase')


def read_role(stage, role, branch=None):
    frames = []
    for r in manifest_records(stage):
        if r['role'] == role and (branch is None or r.get('branch') == branch):
            frames.append(pd.read_parquet(verify_record(r)))
    if not frames:
        raise ValueError('missing saved role: ' + role + '/' + str(branch))
    return pd.concat(frames, ignore_index=True)


def save(frame, destination, role, product, interval, branch=None):
    if destination.exists():
        raise ValueError('retained ledger overwrite refused: ' + str(destination))
    frame.to_parquet(destination, index=False, compression='zstd')
    result = file_record(destination) | {'role': role, 'product': product,
        'interval_minutes': interval, 'row_count': len(frame),
        'schema': {column: str(dtype) for column, dtype in frame.dtypes.items()},
        'retention_status': 'retained_local_external_research_evidence_backup_not_certified'}
    if branch is not None:
        result['branch'] = branch
    return result


def _write_manifest(stage, name, records):
    path = stage / name
    if path.exists():
        raise ValueError('phase manifest overwrite refused: ' + name)
    write_json(path, {'schema_version': 'study21.stage2-ledgers/v1', 'study_id': STUDY_ID,
        'stage': 2, 'run_id': stage.name, 'baseline_run_id': BASELINE_RUN_ID,
        'records': records, 'reserved_outcomes_computed': False})


def _cell_records(stage, role, product, interval, branch=None):
    return [r for r in manifest_records(stage) if r['role'] == role and r['product'] == product
        and r['interval_minutes'] == interval and (branch is None or r.get('branch') == branch)]


def record_plot_context(stage):
    path = stage / 'provenance/numerical-plot-context.json'
    if path.exists():
        for record in json.loads(path.read_text())['packages']:
            verify_record(record)
        return
    packages = []
    for name in ('matplotlib','contourpy','cycler','fontTools','kiwisolver','PIL','pyparsing','numpy','pandas'):
        module = importlib.import_module(name)
        packages.append(file_record(Path(module.__file__).resolve()) | {
            'module':name,'version':module.__version__})
    write_json(path,{'purpose':'Existing cached plot modules for rendering fixtures and saved-evidence figures; core numerical packages remain in the locked environment.',
        'executable':sys.executable,'python':sys.version,'synchronized':False,
        'pythonpath':os.environ.get('PYTHONPATH'),
        'scope':'Module versions and representative initializer byte pins; automatic dependency completeness is not claimed.',
        'packages':packages})


def numerical_tests(stage):
    """Run actual registered fixtures in isolated locked child processes."""
    assert_frozen_sources(stage, WORKSPACE)
    receipt_path = stage / 'provenance/stage2-numerical.json'
    if receipt_path.exists() or any((stage / 'provenance' / name).exists() for name in (
            'study21-numerical.json','study21-numerical.log',
            'bhishma-ema-numerical.json','bhishma-ema-numerical.log')):
        raise ValueError('numerical receipt overwrite refused')
    record_plot_context(stage)
    env = {key:os.environ[key] for key in ('UV_CACHE_DIR','OPENBLAS_NUM_THREADS',
        'VECLIB_MAXIMUM_THREADS','PYTHONPATH','MPLCONFIGDIR') if key in os.environ}
    harness_result = stage / 'provenance/study21-numerical.json'
    commands = [[str(WORKSPACE / 'scripts/check-workspace'),'--check','study-21',
                 '--report',str(harness_result)],
        [str(WORKSPACE / 'scripts/uv'),'run','--locked','--no-sync','python','-B',
         str(WORKSPACE / 'scripts/unittest_child.py'),'--spec',
         json.dumps({'start_dir':str(WORKSPACE / 'packages/bhishma/tests'),
             'names':['test_ema_cloud','test_ema_cloud_release'],'optimize':False}),
         '--result',str(stage / 'provenance/bhishma-ema-numerical.json')]]
    for name, command in zip(('study21','bhishma-ema'),commands):
        record_command(stage,command,WORKSPACE,env)
        with (stage / f'provenance/{name}-numerical.log').open('w') as log:
            code = subprocess.run(command,cwd=WORKSPACE,stdout=log,stderr=subprocess.STDOUT).returncode
        if code:
            raise ValueError('actual numerical fixtures failed: ' + name)
    harness = json.loads(harness_result.read_text())
    if harness['outcome'] != 'passed' or len(harness['checks']) != 1:
        raise ValueError('registered study fixture evidence incomplete')
    result = harness['checks'][0]['unittest']
    feature_path = stage / 'provenance/bhishma-ema-numerical.json'
    feature = json.loads(feature_path.read_text())
    write_json(receipt_path,{'status':'passed',
        'source_inventory':file_record(stage / 'provenance/source-inventory.json',stage),
        'input_lock':file_record(stage / 'inputs.lock.json',stage),
        'baseline_lock':file_record(stage / 'baseline.lock.json',stage),
        'suites':[{'name':'study21','status':result['outcome'],'counts':result['counts'],
                    'result':file_record(harness_result,stage)},
                  {'name':'bhishma-ema','status':feature['outcome'],'counts':feature['counts'],
                    'result':file_record(feature_path,stage)}],
        'scope':'Actual unittest TestResult counts, registered Study 21 and EMA feature fixtures in separate locked processes; no synchronization.'})
    assert_numerical_gate(stage)
    assert_frozen_sources(stage,WORKSPACE)
    print(json.dumps({'numerical':'passed','study21':result['counts'],
                      'bhishma_ema':feature['counts']}),flush=True)


def audit(stage):
    """Fresh pinned-loader mapping must exactly reproduce every baseline bar."""
    from src.engine import map_features
    assert_frozen_sources(stage, WORKSPACE)
    if (stage / 'provenance/input-coverage-identity.json').exists():
        raise ValueError('input identity receipt overwrite refused')
    paths = load_workspace_paths(WORKSPACE)
    delivery = json.loads((stage / 'inputs.lock.json').read_text())['delivery']
    original = json.loads((BASELINE / 'events.manifest.json').read_text())['records']
    cells = []
    for product in config(stage)['products']:
        five = load_release(paths.publication_root, product=product, interval=5,
            manifest_path=delivery['path'], expected_manifest_sha256=delivery['sha256'])
        for interval in config(stage)['interval_minutes']:
            bars = five if interval == 5 else load_release(paths.publication_root, product=product, interval=interval,
                manifest_path=delivery['path'], expected_manifest_sha256=delivery['sha256'])
            mapped = map_features(bars, five, interval)
            baseline_record = next(r for r in original if r['role'] == 'bars' and r['product'] == product and r['interval_minutes'] == interval)
            baseline_bars = pd.read_parquet(verify_record(baseline_record))
            pd.testing.assert_frame_equal(mapped.reset_index(drop=True), baseline_bars.reset_index(drop=True),
                check_exact=True, check_dtype=True)
            cells.append({'product': product, 'interval_minutes': interval, 'rows': len(mapped),
                          'columns': list(mapped.columns), 'tolerance': 0, 'baseline': baseline_record})
    destination = stage / 'data-preparation'
    destination.mkdir(exist_ok=True)
    for source, target in ((BASELINE / 'tables/S1-T00_coverage.csv', destination / 'coverage.csv'),
                           (BASELINE / 'data-preparation/calendar-exclusions.csv', destination / 'calendar-exclusions.csv')):
        shutil.copyfile(source, target)
    write_json(stage / 'provenance/input-coverage-identity.json', {'status': 'passed',
        'source_inventory': file_record(stage / 'provenance/source-inventory.json', stage),
        'input_lock': file_record(stage / 'inputs.lock.json', stage), 'cells': cells,
        'signals_computed': False, 'outcomes_computed': False, 'policy_relaxed': False,
        'scope': 'All six freshly loaded mapped rosters equal sealed Stage 1 bars exactly, including warmup/invalid slots.'})
    assert_frozen_sources(stage, WORKSPACE)
    print(json.dumps({'audit': 'passed', 'mapped_cells': len(cells), 'mapped_rows': sum(r['rows'] for r in cells)}), flush=True)


def events(stage):
    from src.engine import map_features
    from src.stage2_engine import generate_streams
    from src.stage2_membership import build_membership, attach_episode_metadata
    assert_frozen_sources(stage, WORKSPACE)
    assert_numerical_gate(stage)
    audit_receipt = json.loads((stage / 'provenance/input-coverage-identity.json').read_text())
    if audit_receipt['status'] != 'passed' or audit_receipt['outcomes_computed']:
        raise ValueError('input-only identity audit must pass')
    cfg = config(stage)
    paths = load_workspace_paths(WORKSPACE)
    delivery = json.loads((stage / 'inputs.lock.json').read_text())['delivery']
    if paths.legacy_research_root is None:
        raise ValueError('retained evidence storage must be configured')
    retained = (paths.legacy_research_root / 'work' / STUDY_ID / stage.name).resolve()
    retained.mkdir(parents=True, exist_ok=False)
    records = []
    start, end = (pd.Timestamp(cfg[k]).tz_convert('UTC') for k in ('development_start_ny', 'development_endpoint_ny'))
    for product in cfg['products']:
        five = load_release(paths.publication_root, product=product, interval=5,
            manifest_path=delivery['path'], expected_manifest_sha256=delivery['sha256'])
        for interval in cfg['interval_minutes']:
            bars = five if interval == 5 else load_release(paths.publication_root, product=product, interval=interval,
                manifest_path=delivery['path'], expected_manifest_sha256=delivery['sha256'])
            mapped = map_features(bars, five, interval)
            technical, causal_events = generate_streams(mapped, interval, cfg['minimum_width_points'])
            membership = build_membership(mapped, technical, causal_events, endpoint=end)
            causal_events = attach_episode_metadata(causal_events, membership['membership'])
            scoped = causal_events.loc[causal_events.timestamp.ge(start) & causal_events.timestamp.lt(end)].copy()
            records.append(save(mapped, retained / f'{product}_{interval}m_bars.parquet', 'bars', product, interval))
            for branch in ('fast', 'slow'):
                for role, frame in (('technical', technical.loc[technical.touch_mode.eq(branch)]),
                                    ('events', scoped.loc[scoped.touch_mode.eq(branch)])):
                    records.append(save(frame.reset_index(drop=True), retained / f'{product}_{interval}m_{branch}_{role}.parquet', role, product, interval, branch))
            for role, frame in membership.items():
                records.append(save(frame, retained / f'{product}_{interval}m_{role}.parquet', role, product, interval))
            print(json.dumps({'cell': f'{product}/{interval}m', 'accepted': scoped.touch_mode.value_counts().to_dict()}), flush=True)
    _write_manifest(stage, 'acceptance.manifest.json', records)
    write_json(stage / 'acceptance-execution.json', {'status': 'accepted_pending_slow_parity',
        'manifest': file_record(stage / 'acceptance.manifest.json', stage), 'outcomes_computed': False})
    assert_frozen_sources(stage, WORKSPACE)


def outcomes(stage, branch):
    from src.outcomes import score_outcomes
    assert_frozen_sources(stage, WORKSPACE)
    assert_numerical_gate(stage)
    if branch == 'fast':
        parity = json.loads((stage / 'provenance/slow-baseline-parity.json').read_text())
        if parity['status'] != 'passed':
            raise ValueError('complete exact slow parity required before fast outcomes')
        if (parity.get('mismatch_count') != 0 or parity.get('tolerance') != 0
                or parity.get('ledger_artifacts_compared') != 24
                or parity.get('table_artifacts_compared') != 9):
            raise ValueError('complete exact slow parity scope absent')
        expected = [file_record(BASELINE / 'events.manifest.json'),
                    file_record(stage / 'slow-evidence.manifest.json')]
        if parity.get('manifests') != expected:
            raise ValueError('slow parity manifest pins differ')
        for record in parity['consumed_artifacts']:
            verify_record(record)
        if (stage / 'events.manifest.json').exists():
            raise ValueError('final outcomes already saved')
    elif (stage / 'slow-evidence.manifest.json').exists():
        raise ValueError('slow outcomes already saved')
    cfg = config(stage)
    records = list(manifest_records(stage))
    for product in cfg['products']:
        for interval in cfg['interval_minutes']:
            bar_record = _cell_records(stage, 'bars', product, interval)[0]
            event_record = _cell_records(stage, 'events', product, interval, branch)[0]
            bars, signals = pd.read_parquet(verify_record(bar_record)), pd.read_parquet(verify_record(event_record))
            result = score_outcomes(bars, signals, cfg[f'horizons_{interval}m'], interval,
                development_start=cfg['development_start_ny'], endpoint=cfg['development_endpoint_ny'], roster_end_is_endpoint=True)
            added = [c for c in ('shared_episode_id', 'selected_ema', 'union_id') if c in signals and c not in result]
            if added:
                result = result.merge(signals[['event_id'] + added], on='event_id', how='left', validate='many_to_one')
            destination = Path(bar_record['path']).parent / f'{product}_{interval}m_{branch}_outcomes.parquet'
            records.append(save(result, destination, 'outcomes', product, interval, branch))
            print(json.dumps({'cell': f'{product}/{interval}m', 'branch': branch, 'outcome_rows': len(result),
                'completed_h15': int((result.horizon.eq(15) & result.status.eq('completed')).sum())}), flush=True)
    name = 'events.manifest.json' if branch == 'fast' else 'slow-evidence.manifest.json'
    if branch == 'fast':
        records.extend(union_outcomes(stage,records))
    _write_manifest(stage, name, records)
    if branch == 'fast':
        shutil.copyfile(stage / name, stage / 'evidence.manifest.json')
        write_json(stage / 'execution.json', {'status': 'computed_pending_verification',
            'source_inventory': file_record(stage / 'provenance/source-inventory.json', stage),
            'input_lock': file_record(stage / 'inputs.lock.json', stage), 'baseline_lock': file_record(stage / 'baseline.lock.json', stage),
            'settings': file_record(stage / 'config.json', stage), 'ledgers': file_record(stage / name, stage), 'reserved_outcomes_computed': False})
    assert_frozen_sources(stage, WORKSPACE)


def union_outcomes(stage,records):
    """Project saved branch paths onto the union, without calculating new paths."""
    added = []
    cfg = config(stage)
    for product in cfg['products']:
        for interval in cfg['interval_minutes']:
            selected = [r for r in records if r['product']==product and r['interval_minutes']==interval]
            union_record = next(r for r in selected if r['role']=='union')
            union = pd.read_parquet(verify_record(union_record))
            paths = pd.concat([pd.read_parquet(verify_record(r)) for r in selected if r['role']=='outcomes'],ignore_index=True)
            required = ['union_id','fast_event_id','slow_event_id','representative_event_id']
            if any(column not in union for column in required):
                raise ValueError('union representative identity missing')
            result = union[required].merge(paths,left_on='representative_event_id',right_on='event_id',
                how='left',validate='one_to_many')
            if result.horizon.isna().any():
                raise ValueError('union representative path missing')
            result['source_event_id'] = result.event_id
            result['event_id'],result['touch_mode'] = result.union_id,'union'
            if result.duplicated(['event_id','horizon']).any():
                raise ValueError('union double counted a same-bar member')
            destination = Path(union_record['path']).parent / f'{product}_{interval}m_union_outcomes.parquet'
            added.append(save(result,destination,'union_outcomes',product,interval))
    return added


def slow_parity(stage):
    from src.pipeline import _coverage_columns
    from src.statistics import summarize, quantiles, stability, signal_flow, bootstrap, comparisons
    from src.reporting import TABLES as ORIGINAL_TABLES, select_examples
    from src.stage2_parity import compare_baseline
    assert_frozen_sources(stage, WORKSPACE)
    technical, signals, paths = (read_role(stage, role, 'slow') for role in ('technical', 'events', 'outcomes'))
    signals['stage'], paths['stage'] = 1, 1
    folder = stage / 'parity/slow'
    folder.mkdir(parents=True, exist_ok=False)
    score = summarize(paths, supports=('all', 'same_session', 'uninterrupted'))
    uncertainty = bootstrap(paths)
    ci = uncertainty.loc[uncertainty.kind.eq('cohort') & uncertainty.metric.eq('terminal_delta') & uncertainty.weighting.eq('event') & uncertainty.block_weeks.eq(4),
        ['product','interval_minutes','direction','horizon','unit','support','ci_low','ci_high']]
    score = score.merge(ci.rename(columns={'ci_low':'ci95_low','ci_high':'ci95_high'}), on=['product','interval_minutes','direction','horizon','unit','support'], how='left', validate='one_to_one')
    dev = technical.loc[technical.timestamp.dt.tz_convert('America/New_York').dt.year.between(2018,2020)]
    periods = _coverage_columns(stability(paths,session_roster=sorted(dev.session.astype(str).unique())), technical)
    tables = {'S1-T00': pd.read_csv(stage / 'data-preparation/coverage.csv'),
        'S1-T01': signal_flow(technical,signals,paths), 'S1-T02': score, 'S1-T03': quantiles(paths),
        'S1-T04': periods.loc[~periods.period_kind.isin(['week','month'])],
        'S1-T05': periods.loc[periods.period_kind.isin(['week','month'])],
        'S1-T06': select_examples(technical,signals,paths)}
    for name, table in tables.items():
        if name=='S1-T00':
            shutil.copyfile(stage / 'data-preparation/coverage.csv',folder / ORIGINAL_TABLES[name])
        else:
            table.to_csv(folder / ORIGINAL_TABLES[name],index=False,float_format='%.17g')
    uncertainty.to_csv(folder / 'S1-bootstrap.csv',index=False,float_format='%.17g')
    comparisons(paths).to_csv(folder / 'S1-comparisons.csv',index=False,float_format='%.17g')
    receipt = compare_baseline(BASELINE / 'events.manifest.json', stage / 'slow-evidence.manifest.json', BASELINE / 'tables', folder)
    write_json(stage / 'provenance/slow-baseline-parity.json',receipt)
    if receipt['status'] != 'passed':
        raise ValueError('slow scientific parity failed')
    assert_frozen_sources(stage, WORKSPACE)
    print(json.dumps({'slow_parity': 'passed'}),flush=True)


def summarize_stage(stage):
    from src.stage2_statistics import produce_tables
    assert_frozen_sources(stage, WORKSPACE)
    if (stage / 'metrics.json').exists():
        raise ValueError('summary overwrite refused')
    (stage / 'tables').mkdir(exist_ok=True)
    shutil.copyfile(stage / 'data-preparation/coverage.csv',stage / 'tables' / TABLES['S2-T00'])
    receipt = produce_tables(stage)
    write_json(stage / 'provenance/summary-receipt.json',receipt)
    signals, paths = read_role(stage,'events'), read_role(stage,'outcomes')
    write_json(stage / 'metrics.json',{'stage':2,'study_id':STUDY_ID,'run_id':stage.name,
        'baseline_run_id':BASELINE_RUN_ID,'accepted_events':len(signals),'outcome_rows':len(paths),
        'branches': {branch: {'accepted':int(signals.touch_mode.eq(branch).sum()),
            'completed_h15':int((paths.touch_mode.eq(branch)&paths.horizon.eq(15)&paths.status.eq('completed')).sum()),
            'censored_h15':int((paths.touch_mode.eq(branch)&paths.horizon.eq(15)&paths.status.eq('censored')).sum())}
            for branch in ('fast','slow')},'reserved_outcomes_computed':False,
        'numerical_values':'Exact saved tables and stable row_id selectors are authoritative.'})
    write_json(stage / 'exclusions.json',{'calendar':'data-preparation/calendar-exclusions.csv',
        'path_counts': {branch:{str(k):int(v) for k,v in paths.loc[paths.touch_mode.eq(branch)&paths.status.eq('censored'),'censor_reason'].value_counts().items()}
            for branch in ('fast','slow')},'scope':'All path exclusions occur after independent acceptance; no retrospective filters affect branch decisions.'})
    assert_frozen_sources(stage, WORKSPACE)


def verify(stage):
    from src.stage2_reconcile import verify_bundle
    assert_frozen_sources(stage, WORKSPACE)
    receipt = verify_bundle(stage)
    write_json(stage / 'provenance/scientific-reconciliation.json',receipt)
    if receipt['status'] != 'passed':
        raise ValueError('independent reconciliation must pass')
    records = manifest_records(stage)
    for r in records:
        verify_record(r)
    write_json(stage / 'provenance/external-bytes.json',{'status':'passed','verified':len(records),'records':records,'scope':'Explicit local external ledger bytes; backup certification unverified.'})
    assert_frozen_sources(stage, WORKSPACE)


def build_manifest(stage):
    from src.pipeline import build_manifest
    value = build_manifest(stage)
    value['external_artifacts'] = [{'id': f"{r['product']}-{r['interval_minutes']}m-{r.get('branch','common')}-{r['role']}",
        'locator':r['path'],'bytes':r['bytes'],'sha256':r['sha256']} for r in manifest_records(stage)]
    return value


def handoff(stage):
    """Pin fixed development baselines; leave Stage 3 outcome periods reserved."""
    assert_frozen_sources(stage,WORKSPACE)
    reconciliation = json.loads((stage / 'provenance/scientific-reconciliation.json').read_text())
    if reconciliation['status'] != 'passed':
        raise ValueError('scientific reconciliation required for Stage 3 handoff')
    path = stage / 'stage3-handoff.json'
    if path.exists():
        raise ValueError('handoff overwrite refused')
    write_json(path, {'schema_version':'study21.stage3-handoff/v1',
        'study_id':STUDY_ID,'completed_stage':2,'run_id':stage.name,
        'stage1_baseline_run_id':BASELINE_RUN_ID,
        'stage1_manifest':file_record(BASELINE / 'manifest.json'),
        'stage2_baseline_artifacts':[file_record(stage / name,stage) for name in (
            'protocol.md','config.json','inputs.lock.json','baseline.lock.json',
            'events.manifest.json','metrics.json','report.md',
            'tables/'+TABLES['S2-T02'],'tables/'+TABLES['S2-T08'],
            'provenance/slow-baseline-parity.json','provenance/scientific-reconciliation.json')],
        'fixed_baselines':{'branches':['fast EMA20','slow EMA50'],
            'cloud':'5m EMA20/EMA50','minimum_width_points':config(stage)['minimum_width_points'],
            'primary_horizon':15,'cooldown':0,'signal_period':'2018–2020 New York'},
        'reusable_delivery':json.loads((stage / 'inputs.lock.json').read_text())['delivery'],
        'reserved_outcome_periods':{'validation':'2021–2023',
            'final_evaluation':'2024–2025','recent_replication':'2026 through 2026-09-18'},
        'reserved_outcomes_computed':False,'stage3_executed':False,
        'next_scope':'Separately authorize the planned Stage 3 development grid/fold/objective, freeze a shortlist before validation, and freeze final claims before final/recent evaluation.',
        'qualification':'Prior Abacus history exposure means these periods are reserved for this study, not pristine holdouts. Stage 1 input/arrival/calendar/native/backup qualifications persist.'})


def seal(stage):
    assert_frozen_sources(stage,WORKSPACE)
    if not (stage / 'stage3-handoff.json').is_file():
        raise ValueError('fixed-baseline Stage 3 handoff required before sealing')
    checks = json.loads((stage / 'provenance/checks.json').read_text())
    required = {'study21-numerical','bhishma-ema-numerical','baseline-input-identities',
        'input-coverage-identity','slow-baseline-parity','scientific-reconciliation',
        'external-ledger-bytes','publication-dry-run','independent-uncertainty','report-transfer'}
    passed = {r['name'] for r in checks if r['status']=='passed'}
    if not required.issubset(passed):
        raise ValueError('Stage 2 sealing gates absent: ' + str(sorted(required-passed)))
    for r in checks:
        if r['status'] in ('passed','failed') and not (stage / r['record']).is_file():
            raise ValueError('recorded check evidence absent')
    write_json(stage / 'manifest.json',build_manifest(stage))
    sys.path.insert(0,str(WORKSPACE / 'scripts'))
    from evidence_contract import assess_bundle
    assessment = assess_bundle(stage)
    if assessment['status'] != 'verified_declared_artifacts':
        raise ValueError('declared artifact integrity failed: ' + json.dumps(assessment))
    for r in manifest_records(stage):
        verify_record(r)
    # Preserve actual Stage 1 bytes as well as all compared scientific pins.
    for r in json.loads((stage / 'baseline.lock.json').read_text())['external_records']:
        verify_record(r)
    destination = WORKSPACE / 'runs' / STUDY_ID / stage.name
    if destination.exists():
        raise ValueError('completed run overwrite refused')
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.move(str(stage),str(destination))
    print(json.dumps({'status':'sealed','run':str(destination),'integrity':assessment['status']}),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['pin','freeze','test','audit','events','slow-outcomes','slow-parity','fast-outcomes','summarize','examples','render','verify','handoff','seal'])
    parser.add_argument('--stage',type=Path,required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    assert_stage(stage,WORKSPACE)
    stage.mkdir(parents=True,exist_ok=True)
    environment = {key:os.environ[key] for key in ('UV_CACHE_DIR','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','PYTHONPATH','MPLCONFIGDIR') if key in os.environ}
    record_command(stage,[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]],WORKSPACE,environment)
    if args.phase == 'pin':
        pin_baseline(stage,WORKSPACE)
    elif args.phase == 'freeze':
        freeze(stage,WORKSPACE,STUDY)
    elif args.phase == 'test': numerical_tests(stage)
    elif args.phase == 'audit': audit(stage)
    elif args.phase == 'events': events(stage)
    elif args.phase == 'slow-outcomes': outcomes(stage,'slow')
    elif args.phase == 'slow-parity': slow_parity(stage)
    elif args.phase == 'fast-outcomes': outcomes(stage,'fast')
    elif args.phase == 'summarize': summarize_stage(stage)
    elif args.phase == 'examples':
        from src.stage2_reporting import prepare_examples
        assert_frozen_sources(stage,WORKSPACE)
        write_json(stage / 'provenance/examples-receipt.json',prepare_examples(stage))
        assert_frozen_sources(stage,WORKSPACE)
    elif args.phase == 'render':
        from src.stage2_reporting import render_bundle
        assert_frozen_sources(stage,WORKSPACE)
        record_plot_context(stage)
        write_json(stage / 'provenance/render-receipt.json',render_bundle(stage,stage.name))
        assert_frozen_sources(stage,WORKSPACE)
    elif args.phase == 'verify': verify(stage)
    elif args.phase == 'handoff': handoff(stage)
    elif args.phase == 'seal': seal(stage)


if __name__ == '__main__':
    main()
