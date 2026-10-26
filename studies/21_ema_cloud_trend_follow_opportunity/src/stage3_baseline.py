"""Reproduce fixed Stage 2 scientific ledgers and original estimands separately."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil

import pandas as pd

from .execution import file_record, sha256, verify_record, write_json
from .stage3_execution import BASELINES, STUDY_ID, assert_frozen, assert_numerical_gate, write_once


def save(frame, path, role, product, interval, branch=None):
    if path.exists():
        raise ValueError('retained evidence overwrite refused: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False, compression='zstd')
    result = file_record(path) | {'role': role, 'product': product,
        'interval_minutes': interval, 'row_count': len(frame),
        'schema': {c: str(d) for c, d in frame.dtypes.items()},
        'retention_status': 'retained_local_external_research_evidence_backup_not_certified'}
    if branch is not None:
        result['branch'] = branch
    return result


def reproduce(stage: Path, workspace: Path, mapped_cells, retained: Path) -> dict:
    from .stage2_engine import generate_streams
    from .stage2_membership import build_membership, attach_episode_metadata
    from .outcomes import score_outcomes
    from .stage2_statistics import produce_tables
    from .stage2_reporting import prepare_examples
    from .stage2_parity import compare_frames
    from .stage3_events import generate_gateway_stream, gate_spec
    assert_frozen(stage, workspace)
    assert_numerical_gate(stage)
    baseline = workspace / 'runs' / STUDY_ID / BASELINES['stage2']
    original = json.loads((baseline / 'events.manifest.json').read_text())['records']
    cfg = json.loads((baseline / 'config.json').read_text())
    parity = stage / 'parity' / 'fixed-stage2'
    parity.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(baseline / 'config.json', parity / 'config.json')
    records, gateway_comparisons = [], []
    end = pd.Timestamp(cfg['development_endpoint_ny']).tz_convert('UTC')
    for product, interval, full in mapped_cells:
        # Feature/history values are continuous, but this reproduction roster
        # must stop at the original endpoint before paths are scored.
        bars = full.loc[full.available_at.le(end)].reset_index(drop=True)
        technical, all_events = generate_streams(bars, interval, cfg['minimum_width_points'])
        for branch in ('fast', 'slow'):
            payload = generate_gateway_stream(bars, interval, branch,
                gate_spec('absolute', cfg['minimum_width_points'][product]))
            for role, old, new, keys_for_role in (
                ('technical', technical.loc[technical.touch_mode.eq(branch)], payload['technical'], ['product', 'timestamp']),
                ('events', all_events.loc[all_events.touch_mode.eq(branch)], payload['events'], ['event_id'])):
                item = compare_frames(old, new, keys=keys_for_role, excluded=('stage', 'gate_id', 'split'),
                    label=f'{product}/{interval}/{branch}/actual-stage3-fixed-{role}')
                gateway_comparisons.append(item)
                if item['mismatch_count']:
                    write_once(stage / 'provenance/fixed-stage3-gateway-failure.json', item)
                    raise ValueError('actual Stage 3 fixed gateway differs from inherited acceptance')
        membership = build_membership(bars, technical, all_events, endpoint=cfg['development_endpoint_ny'])
        all_events = attach_episode_metadata(all_events, membership['membership'])
        local = all_events.timestamp.dt.tz_convert('America/New_York')
        scoped = all_events.loc[local.dt.year.between(2018, 2020)].copy()
        records.append(save(bars, retained / f'{product}_{interval}m_bars.parquet', 'bars', product, interval))
        cell_outcomes = []
        for branch in ('fast', 'slow'):
            branch_events = scoped.loc[scoped.touch_mode.eq(branch)].reset_index(drop=True)
            paths = score_outcomes(bars, branch_events, cfg[f'horizons_{interval}m'], interval,
                development_start=cfg['development_start_ny'], endpoint=cfg['development_endpoint_ny'], roster_end_is_endpoint=True)
            added = [c for c in ('shared_episode_id', 'selected_ema', 'union_id') if c in branch_events and c not in paths]
            if added:
                paths = paths.merge(branch_events[['event_id'] + added], on='event_id', how='left', validate='many_to_one')
            cell_outcomes.append(paths)
            for role, frame in (('technical', technical.loc[technical.touch_mode.eq(branch)].reset_index(drop=True)),
                                ('events', branch_events), ('outcomes', paths)):
                records.append(save(frame, retained / f'{product}_{interval}m_{branch}_{role}.parquet', role, product, interval, branch))
        for role, frame in membership.items():
            records.append(save(frame, retained / f'{product}_{interval}m_{role}.parquet', role, product, interval))
        union = membership['union']
        all_paths = pd.concat(cell_outcomes, ignore_index=True)
        result = union[['union_id', 'fast_event_id', 'slow_event_id', 'representative_event_id']].merge(
            all_paths, left_on='representative_event_id', right_on='event_id', how='left', validate='one_to_many')
        if result.horizon.isna().any():
            raise ValueError('fixed union representative path missing')
        result['source_event_id'] = result.event_id
        result['event_id'], result['touch_mode'] = result.union_id, 'union'
        records.append(save(result, retained / f'{product}_{interval}m_union_outcomes.parquet', 'union_outcomes', product, interval))
        print(json.dumps({'fixed_reproduction': f'{product}/{interval}m', 'accepted': len(scoped), 'outcome_rows': len(all_paths)}), flush=True)
    write_once(parity / 'events.manifest.json', {'schema_version': 'study21.stage3-fixed-reproduction/v1', 'records': records})
    ledger_comparisons = []
    keys = {'bars': ['product', 'timestamp'], 'technical': ['product', 'timestamp'], 'events': ['event_id'],
            'outcomes': ['event_id', 'horizon'], 'membership': ['product', 'timestamp'],
            'episodes': ['shared_episode_id'], 'pairs': ['pair_id'], 'union': ['union_id'],
            'union_outcomes': ['event_id', 'horizon']}
    for old in original:
        matches = [r for r in records if r['role'] == old['role'] and r['product'] == old['product'] and
                   r['interval_minutes'] == old['interval_minutes'] and r.get('branch') == old.get('branch')]
        if len(matches) != 1:
            raise ValueError('fixed ledger role missing or ambiguous')
        left, right = pd.read_parquet(verify_record(old)), pd.read_parquet(verify_record(matches[0]))
        comparison = compare_frames(left, right, keys=keys[old['role']], excluded=(),
                                    label=f"{old['product']}/{old['interval_minutes']}/{old.get('branch','common')}/{old['role']}")
        ledger_comparisons.append(comparison)
        if comparison['mismatch_count']:
            write_once(stage / 'provenance/fixed-baseline-ledger-failure.json', comparison)
            raise ValueError('fixed baseline ledger scientific mismatch: ' + comparison['artifact'])
    tables = parity / 'tables'
    tables.mkdir()
    # Original coverage has independently reproduced exact source/mapped rosters;
    # its preserved table is explicitly an inherited coverage view, not a new
    # forward estimator. Every outcome-dependent estimate below is recalculated.
    shutil.copyfile(baseline / 'tables/S2-T00_coverage.csv', tables / 'S2-T00_coverage.csv')
    produce_tables(parity)
    prepare_examples(parity)
    table_comparisons = []
    for old_path in sorted((baseline / 'tables').glob('*.csv')):
        new_path = tables / old_path.name
        if not new_path.is_file():
            raise ValueError('fixed inherited table absent: ' + old_path.name)
        with old_path.open(newline='') as stream:
            reader = csv.reader(stream)
            width = len(next(reader))
            count = sum(1 for _ in reader)
        exact = old_path.read_bytes() == new_path.read_bytes()
        item = {'artifact': old_path.name, 'rows': count, 'columns': width, 'compared_cells': count * width,
                'mismatch_count': 0 if exact else 1, 'old': file_record(old_path), 'new': file_record(new_path, stage)}
        table_comparisons.append(item)
        if not exact:
            write_once(stage / 'provenance/fixed-baseline-table-failure.json', item)
            raise ValueError('fixed original-string table mismatch: ' + old_path.name)
    assert_frozen(stage, workspace)
    result = {'schema_version': 'study21.stage3-fixed-parity/v1', 'status': 'passed',
        'records': [file_record(parity / 'events.manifest.json', stage)] + [r['new'] for r in table_comparisons],
        'external_records': records,
        'ledger_comparisons': ledger_comparisons, 'table_comparisons': table_comparisons,
        'actual_stage3_gateway_comparisons': gateway_comparisons,
        'ledger_artifacts_compared': len(ledger_comparisons), 'table_artifacts_compared': len(table_comparisons),
        'compared_cells': sum(r['compared_cells'] for r in ledger_comparisons + table_comparisons + gateway_comparisons),
        'mismatch_count': 0, 'tolerance': 0, 'retained_records': records,
        'original_endpoint': cfg['development_endpoint_ny'],
        'coverage_disposition': 'Original coverage CSV explicitly inherited after full exact source/mapped prefix parity; every path-dependent table and uncertainty estimator regenerated.',
        'fold_masks_applied': False, 'later_outcomes_scored': False}
    write_once(stage / 'provenance/fixed-baseline-parity.json', result)
    return result
