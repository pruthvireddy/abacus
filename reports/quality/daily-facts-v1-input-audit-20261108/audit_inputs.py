#!/usr/bin/env python3
"""Read-only selected-input coverage audit; does not calculate Daily Facts."""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds

from abacus_bhishma.calendar import holiday_sessions
from abacus_bhishma.continuous_loader import open_continuous_dataset
from abacus_bhishma.daily_context import align_daily_context_asof, load_daily_context
from abacus_bhishma.paths import resolve_publication_root, workspace_root

NY = ZoneInfo('America/New_York')
UTC = timezone.utc
MINUTE_NS = 60_000_000_000
START, END = date(2010, 6, 7), date(2026, 9, 18)
COMMON = date(2021, 6, 28)
BAR_MANIFEST = 'catalog/datasets/volume_lead_unadjusted_v1.json'
BAR_HASH = '00757f5fc8278e75744d7adfaddc688be588d619d82b1dc1811aa60f21b7e5d4'
CONTEXT_MANIFEST = 'catalog/datasets/tradingview_daily_context__1.0.0.json'
CONTEXT_HASH = 'b7395d6ec2a3263e6f17b2ed95d22ea235d543a01e5b7f850eff81604ba6ce8f'
WINDOWS = ('globex', 'overnight', 'rth', 'or15', 'first60', 'last60', 'globex_to_rth_end')
PRODUCTS = ('ES', 'NQ', 'GC')
COLS = ['ts_event', 'session_date', 'open', 'high', 'low', 'close', 'volume', 'instrument_id', 'is_roll']


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def write_csv(path, rows):
    if not rows:
        raise ValueError(f'empty required output: {path}')
    with Path(path).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def local(day, hour, minute=0):
    return datetime.combine(day, time(hour, minute), NY)


def bounds(asset, day):
    opening = local(day, 8, 20) if asset == 'GC' else local(day, 9, 30)
    closing = local(day, 13, 30) if asset == 'GC' else local(day, 16)
    globex = local(day - timedelta(days=1), 18)
    return {
        'globex': (globex, local(day, 17)),
        'overnight': (globex, opening),
        'rth': (opening, closing),
        'or15': (opening, opening + timedelta(minutes=15)),
        'first60': (opening, opening + timedelta(hours=1)),
        'last60': (closing - timedelta(hours=1), closing),
        'globex_to_rth_end': (globex, closing),
    }


def ns(value):
    return int(pd.Timestamp(value).value)


def inspect_window(timestamps, valid, instruments, volumes, start, end):
    begin, finish = ns(start), ns(end)
    mask = (timestamps >= begin) & (timestamps < finish)
    ts, ok, ids, vol = timestamps[mask], valid[mask], instruments[mask], volumes[mask]
    expected = np.arange(begin, finish, MINUTE_NS, dtype=np.int64)
    unique, counts = np.unique(ts, return_counts=True)
    missing = np.setdiff1d(expected, unique, assume_unique=True)
    off_grid = np.setdiff1d(unique, expected, assume_unique=True)
    duplicate = int(np.sum(counts - 1))
    grid = len(missing) == 0 and len(off_grid) == 0 and duplicate == 0
    contracts = len(np.unique(ids))
    complete = bool(grid and np.all(ok) and contracts == 1)
    open_mask = ts == begin
    close_mask = ts == finish - MINUTE_NS
    return {
        'expected_minutes': len(expected), 'observed_rows': len(ts),
        'unique_timestamps': len(unique), 'missing_minutes': len(missing),
        'off_grid_timestamps': len(off_grid), 'duplicate_rows': duplicate,
        'invalid_rows': int(np.count_nonzero(~ok)), 'distinct_contracts': contracts,
        'grid_complete': bool(grid), 'valid_complete': complete,
        'open_ready': bool(np.count_nonzero(open_mask) == 1 and np.all(ok[open_mask])),
        'close_boundary_ready': bool(np.count_nonzero(close_mask) == 1 and np.all(ok[close_mask])),
        'positive_volume_present': bool(np.any(vol > 0)),
    }


def self_checks():
    passed = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        passed.append(name)
    winter, summer = date(2025, 1, 7), date(2025, 7, 8)
    for asset, expected in [('ES', [1380, 930, 390, 15, 60, 60]),
                            ('NQ', [1380, 930, 390, 15, 60, 60]),
                            ('GC', [1380, 860, 310, 15, 60, 60])]:
        for day in [winter, summer]:
            actual = [int((e.astimezone(UTC) - s.astimezone(UTC)).total_seconds() / 60)
                      for key, (s, e) in bounds(asset, day).items() if key != 'globex_to_rth_end']
            check(f'{asset}_{day}_window_lengths', actual == expected)
    check('winter_utc_open', bounds('ES', winter)['rth'][0].astimezone(UTC).hour == 14)
    check('summer_utc_open', bounds('ES', summer)['rth'][0].astimezone(UTC).hour == 13)
    check('monday_globex_starts_sunday', bounds('ES', date(2025, 3, 10))['globex'][0].weekday() == 6)
    s, e = bounds('ES', winter)['or15']
    t = np.arange(ns(s), ns(e), MINUTE_NS, dtype=np.int64)
    ok, ids, vol = np.ones(15, dtype=bool), np.ones(15, dtype=int), np.ones(15, dtype=int)
    run = lambda a=t, b=ok, c=ids, d=vol: inspect_window(a, b, c, d, s, e)
    check('complete_grid', run()['valid_complete'])
    check('missing_minute', run(t[:-1], ok[:-1], ids[:-1], vol[:-1])['missing_minutes'] == 1)
    check('late_gap_preserves_open', run(t[:-1], ok[:-1], ids[:-1], vol[:-1])['open_ready'])
    check('missing_open_no_substitution', not run(t[1:], ok[1:], ids[1:], vol[1:])['open_ready'])
    check('duplicate_is_not_complete', not run(np.append(t, t[0]), np.append(ok, True), np.append(ids, 1), np.append(vol, 1))['valid_complete'])
    shifted = t.copy(); shifted[4] += 1
    check('subminute_is_off_grid', run(shifted)['off_grid_timestamps'] == 1)
    invalid = ok.copy(); invalid[2] = False
    check('invalid_ohlc_rejected', not run(b=invalid)['valid_complete'])
    mixed = ids.copy(); mixed[-1] = 2
    check('mixed_contract_rejected', not run(c=mixed)['valid_complete'])
    check('zero_volume_separate_from_grid', run(d=np.zeros(15, dtype=int))['valid_complete'] and not run(d=np.zeros(15, dtype=int))['positive_volume_present'])
    with_end = np.append(t, ns(e))
    check('exclusive_end', run(with_end, np.append(ok, True), np.append(ids, 1), np.append(vol, 1))['observed_rows'] == 15)
    check('calendar_special_closure', date(2025, 1, 9) in holiday_sessions('ES', 2025, 2025))
    check('new_year_saturday_not_shifted', date(2021, 12, 31) not in holiday_sessions('ES', 2021, 2022))
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    workspace, root = workspace_root(), resolve_publication_root()
    output = Path(args.output).resolve()
    if not output.is_relative_to(workspace / 'work/daily-facts-v1'):
        raise ValueError('audit output must be a fresh directory under work/daily-facts-v1')
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(UTC).isoformat()
    checks = self_checks()
    print(f'Audit self-checks: {len(checks)} passed', flush=True)
    verified = []
    def verify(relative, expected=None, size=None, kind='supporting_source'):
        path = root / relative
        digest = sha(path)
        if expected is not None and digest != expected:
            raise ValueError(f'input hash mismatch: {relative}')
        if size is not None and path.stat().st_size != size:
            raise ValueError(f'input size mismatch: {relative}')
        verified.append({'path': relative, 'kind': kind, 'bytes': path.stat().st_size,
                         'sha256': digest, 'matches_recorded_release': expected is not None})
        return path
    manifest_path = verify(BAR_MANIFEST, BAR_HASH, kind='minute_manifest')
    manifest = json.loads(manifest_path.read_text())
    context_path = verify(CONTEXT_MANIFEST, CONTEXT_HASH, kind='context_manifest')
    context_manifest = json.loads(context_path.read_text())
    calendar_path = verify('catalog/calendars/cme_fixed_clock_session_v1.json', kind='calendar_contract')
    calendar = json.loads(calendar_path.read_text())
    for key in ['schema_path', 'indicator_spec']:
        relative = context_manifest[key]
        verify(relative, context_manifest.get(key.replace('_path', '_sha256')) if key == 'schema_path' else None,
               kind='context_definition')
    dates = [START + timedelta(days=i) for i in range((END - START).days + 1)]
    weekdays = {d for d in dates if d.weekday() < 5}
    all_rows, inventories, selections = [], [], {}
    for asset in PRODUCTS:
        records = [r for r in manifest['output_files'] if f'/product={asset}/' in r['path']
                   and '/variant=unadjusted/' in r['path'] and r['path'].endswith('.parquet')]
        for record in records:
            verify(record['path'], record['sha256'], record['bytes'], 'minute_partition')
        dataset = open_continuous_dataset(root, asset, 'unadjusted', manifest_path=BAR_MANIFEST,
                                         expected_manifest_sha256=BAR_HASH, verify_selected_files=False)
        holidays = holiday_sessions(asset, START.year, END.year)
        regimes = calendar['product_regimes'][asset]
        seen, sessions, total_rows = set(), {}, 0
        inventory = {'asset': asset, 'partitions': len(records), 'rows': 0, 'null_cells': 0,
                     'invalid_ohlc_rows': 0, 'nonincreasing_timestamp_pairs': 0,
                     'outside_nominal_globex_rows': 0, 'outside_date_envelope_rows': 0,
                     'weekend_session_rows': 0, 'roll_marked_rows': 0,
                     'source_first_timestamp': None, 'source_last_timestamp': None}
        prior_last = None
        for year in range(START.year, END.year + 1):
            table = dataset.to_table(columns=COLS, filter=ds.field('year') == year)
            if not table.num_rows:
                continue
            nulls = sum(table[c].null_count for c in COLS)
            inventory['null_cells'] += nulls
            if nulls:
                raise ValueError(f'null cells require explicit audit handling: {asset}/{year}')
            arrays = {c: table[c].combine_chunks().to_numpy(zero_copy_only=False) for c in COLS}
            timestamps = table['ts_event'].combine_chunks().cast(pa.int64()).to_numpy()
            day_values = table['session_date'].combine_chunks().cast(pa.int32()).to_numpy()
            inventory['nonincreasing_timestamp_pairs'] += int(np.count_nonzero(np.diff(timestamps) <= 0))
            if prior_last is not None and timestamps[0] <= prior_last:
                inventory['nonincreasing_timestamp_pairs'] += 1
            prior_last = int(timestamps[-1])
            if inventory['source_first_timestamp'] is None:
                inventory['source_first_timestamp'] = pd.Timestamp(int(timestamps[0]), tz='UTC').isoformat()
            inventory['source_last_timestamp'] = pd.Timestamp(int(timestamps[-1]), tz='UTC').isoformat()
            o, h, l, c = [arrays[k] for k in ['open', 'high', 'low', 'close']]
            invalid_price = np.zeros(len(timestamps), dtype=bool)
            for values in [o, h, l, c]:
                invalid_price |= (values == np.iinfo(np.int64).max) | (values == np.iinfo(np.int64).min)
            valid = (l <= o) & (o <= h) & (l <= c) & (c <= h) & (l <= h) & ~invalid_price
            inventory['invalid_ohlc_rows'] += int(np.count_nonzero(~valid))
            inventory['roll_marked_rows'] += int(np.count_nonzero(arrays['is_roll']))
            edges = np.r_[0, np.flatnonzero(np.diff(day_values)) + 1, len(day_values)]
            for left, right in zip(edges[:-1], edges[1:]):
                day = date(1970, 1, 1) + timedelta(days=int(day_values[left]))
                if day.year != year or day in seen:
                    raise ValueError(f'partition/session grouping is not disjoint: {asset}/{day}')
                if not START <= day <= END:
                    raise ValueError(f'unexpected source date: {asset}/{day}')
                seen.add(day)
                t, v = timestamps[left:right], valid[left:right]
                ids, vol = arrays['instrument_id'][left:right], arrays['volume'][left:right]
                session_bounds = bounds(asset, day)
                gs, ge = session_bounds['globex']
                inventory['outside_nominal_globex_rows'] += int(np.count_nonzero((t < ns(gs)) | (t >= ns(ge))))
                inventory['outside_date_envelope_rows'] += int(np.count_nonzero((t < ns(gs)) | (t >= ns(local(day, 18)))))
                if day.weekday() >= 5:
                    inventory['weekend_session_rows'] += len(t)
                sessions[day] = {w: inspect_window(t, v, ids, vol, s, e)
                                 for w, (s, e) in session_bounds.items()}
                total_rows += len(t)
            del table, arrays
            print(f'{asset} {year}: {len(timestamps):,} rows inspected', flush=True)
        inventory['rows'] = total_rows
        inventory['observed_session_dates'] = len(seen)
        if total_rows != manifest['products'][asset]['rows']:
            raise AssertionError(f'source row count differs from manifest: {asset}')
        inventories.append(inventory)
        for day in sorted(weekdays | seen):
            matches = [r for r in regimes if date.fromisoformat(r['start']) <= day < date.fromisoformat(r['end_exclusive'])]
            regime = matches[0] if len(matches) == 1 else {'id': 'uncovered', 'supported': False}
            holiday = holidays.get(day, [])
            for window, (s, e) in bounds(asset, day).items():
                result = sessions.get(day, {}).get(window)
                if result is None:
                    result = inspect_window(np.array([], dtype=np.int64), np.array([], dtype=bool),
                                            np.array([], dtype=int), np.array([], dtype=int), s, e)
                all_rows.append({'asset': asset, 'session_date': day.isoformat(), 'year': day.year,
                                 'window': window, 'window_start_utc': s.astimezone(UTC).isoformat(),
                                 'window_end_utc': e.astimezone(UTC).isoformat(),
                                 'weekday': day.weekday() < 5, 'calendar_supported': bool(regime['supported']),
                                 'calendar_regime': regime['id'], 'holiday_reasons': '; '.join(holiday),
                                 'eligible_normal': day.weekday() < 5 and bool(regime['supported']) and not holiday,
                                 'common_period': day >= COMMON, **result})
        selections[asset] = dataset
    frame = pd.DataFrame(all_rows)
    frame.to_csv(output / 'session_window_coverage.csv', index=False, lineterminator='\n')
    summaries, annual = [], []
    for scope, mask in [
        ('retained_all_weekdays', frame.weekday),
        ('supported_normal', frame.eligible_normal),
        ('common_supported_normal', frame.eligible_normal & frame.common_period),
    ]:
        subset = frame[mask]
        def aggregate(group, base):
            complete = int(group.valid_complete.sum())
            missing = group.missing_minutes.to_numpy()
            return {**base, 'candidate_sessions': len(group), 'complete_sessions': complete,
                    'incomplete_sessions': len(group) - complete,
                    'complete_fraction': complete / len(group),
                    'grid_complete_sessions': int(group.grid_complete.sum()),
                    'open_ready_sessions': int(group.open_ready.sum()),
                    'close_boundary_ready_sessions': int(group.close_boundary_ready.sum()),
                    'absent_windows': int((group.observed_rows == 0).sum()),
                    'missing_minutes_total': int(missing.sum()),
                    'missing_minutes_median': float(np.median(missing)),
                    'missing_minutes_p95': float(np.quantile(missing, .95)),
                    'missing_minutes_max': int(missing.max()),
                    'first_candidate': str(group.session_date.min()), 'last_candidate': str(group.session_date.max())}
        for (asset, window), group in subset.groupby(['asset', 'window'], sort=False):
            summaries.append(aggregate(group, {'scope': scope, 'asset': asset, 'window': window}))
        for (asset, year, window), group in subset.groupby(['asset', 'year', 'window'], sort=False):
            annual.append(aggregate(group, {'scope': scope, 'asset': asset, 'year': int(year), 'window': window}))
    write_csv(output / 'coverage_by_window.csv', summaries)
    write_csv(output / 'coverage_by_year.csv', annual)
    exclusions = []
    for asset in PRODUCTS:
        days = frame[(frame.asset == asset) & (frame.window == 'globex') & frame.weekday]
        for period, sub in [('full_history', days), ('common_period', days[days.common_period])]:
            exclusions.append({'asset': asset, 'period': period, 'weekday_dates': len(sub),
                               'unsupported_regime_dates': int((~sub.calendar_supported).sum()),
                               'holiday_or_shortened_dates': int((sub.holiday_reasons != '').sum()),
                               'supported_holiday_dates': int((sub.calendar_supported & (sub.holiday_reasons != '')).sum()),
                               'eligible_normal_dates': int(sub.eligible_normal.sum())})
    write_csv(output / 'calendar_exclusions.csv', exclusions)
    complete = frame.pivot(index=['asset', 'session_date'], columns='window', values='valid_complete')
    eligible = frame[frame.window == 'globex'].set_index(['asset', 'session_date'])
    losses = []
    for asset in PRODUCTS:
        idx = eligible[(eligible.asset if 'asset' in eligible else eligible.index.get_level_values('asset')) == asset]
        idx = idx[idx.eligible_normal & idx.common_period].index
        for window in WINDOWS:
            part = complete.loc[idx]
            count = int(part[window].sum())
            losses.append({'asset': asset, 'window': window, 'candidate_sessions': len(part),
                           'independent_complete': count,
                           'also_complete_globex': int((part[window] & part.globex).sum()),
                           'lost_to_globex_gate': int((part[window] & ~part.globex).sum())})
    write_csv(output / 'full_day_gate_losses.csv', losses)
    intersections = []
    for window in WINDOWS:
        part = frame[(frame.window == window) & frame.common_period & frame.weekday]
        ready = part.pivot(index='session_date', columns='asset', values='valid_complete')
        possible = part.pivot(index='session_date', columns='asset', values='eligible_normal')
        jointly = possible.all(axis=1)
        intersections.append({'window': window, 'joint_candidate_sessions': int(jointly.sum()),
                              'all_three_complete': int(ready[jointly].all(axis=1).sum())})
    write_csv(output / 'common_asset_intersections.csv', intersections)
    inventory_context, context_rows, context_summaries = [], [], []
    for symbol in ['ES', 'NQ', 'GC', 'VIX', 'VXN', 'GVZ']:
        rec = context_manifest['assets'][symbol]
        verify(rec['output_path'], rec['output_sha256'], rec['output_bytes'], 'daily_context_partition')
        verify(rec['source_path'], rec['source_sha256'], rec['source_bytes'], 'daily_context_raw_csv')
        table = load_daily_context(root, symbol, version='1.0.0', columns=['trading_day', 'available_at', 'close'])
        days, available = table['trading_day'].to_pylist(), table['available_at'].to_pylist()
        check = len(table) == rec['published_rows'] and len(set(days)) == len(days)
        check = check and all(a < b for a, b in zip(available, available[1:]))
        if not check:
            raise AssertionError(f'invalid daily context ordering/count: {symbol}')
        inventory_context.append({'symbol': symbol, 'rows': len(table), 'first_day': str(days[0]),
                                  'last_day': str(days[-1]), 'null_close_rows': table['close'].null_count})
    for asset, symbol in [('ES', 'VIX'), ('NQ', 'VXN'), ('GC', 'GVZ')]:
        day_records = frame[(frame.asset == asset) & (frame.window == 'rth') & frame.weekday]
        days = [date.fromisoformat(d) for d in day_records.session_date]
        times = [bounds(asset, d)['rth'][0] for d in days]
        unrestricted = align_daily_context_asof(root, symbol, times, version='1.0.0', max_age_days=None,
                                              columns=['trading_day', 'available_at', 'close'])
        restricted = align_daily_context_asof(root, symbol, times, version='1.0.0', max_age_days=7,
                                            columns=['trading_day', 'available_at', 'close'])
        source_table = load_daily_context(root, symbol, version='1.0.0', columns=['available_at'])
        source_ns = source_table['available_at'].combine_chunks().cast(pa.timestamp('ns', tz='UTC')).cast(pa.int64()).to_numpy()
        for record, day, when, raw, selected in zip(day_records.to_dict('records'), days, times, unrestricted, restricted):
            index = int(np.searchsorted(source_ns, ns(when), side='right')) - 1
            if (raw is None) != (index < 0):
                raise AssertionError('independent context search mismatch')
            if raw is not None and ns(raw['available_at']) != int(source_ns[index]):
                raise AssertionError('independent context timestamp mismatch')
            age = None if raw is None else (when.astimezone(UTC) - raw['available_at']).total_seconds() / 3600
            status = 'missing' if raw is None else 'stale' if age > 168 else 'invalid_close' if raw['close'] is None or not np.isfinite(raw['close']) else 'valid'
            if (selected is None) != (raw is None or age > 168):
                raise AssertionError('context age-policy mismatch')
            context_rows.append({'asset': asset, 'session_date': str(day), 'symbol': symbol,
                                 'rth_start_utc': when.astimezone(UTC).isoformat(),
                                 'source_day': None if raw is None else str(raw['trading_day']),
                                 'source_available_at': None if raw is None else raw['available_at'].isoformat(),
                                 'age_hours': age, 'status': status,
                                 'eligible_normal': record['eligible_normal'], 'common_period': record['common_period']})
        sub = pd.DataFrame([r for r in context_rows if r['asset'] == asset])
        for scope, group in [('retained_all_weekdays', sub), ('supported_normal', sub[sub.eligible_normal]),
                             ('common_supported_normal', sub[sub.eligible_normal & sub.common_period])]:
            context_summaries.append({'scope': scope, 'asset': asset, 'symbol': symbol, 'candidate_sessions': len(group),
                                      'valid': int((group.status == 'valid').sum()), 'missing': int((group.status == 'missing').sum()),
                                      'stale': int((group.status == 'stale').sum()), 'invalid_close': int((group.status == 'invalid_close').sum()),
                                      'max_valid_age_hours': float(group[group.status == 'valid'].age_hours.max())})
    write_csv(output / 'context_lookup_coverage.csv', context_rows)
    write_csv(output / 'context_summary.csv', context_summaries)
    independent = []
    for asset in PRODUCTS:
        candidates = frame[(frame.asset == asset) & (frame.window == 'globex') & frame.eligible_normal & frame.common_period]
        selected_days = []
        for good in [True, False]:
            sample = candidates[(candidates.valid_complete == good) & (candidates.observed_rows > 0)]
            if len(sample):
                selected_days.append(date.fromisoformat(sample.iloc[0].session_date))
        for day in selected_days:
            rows = selections[asset].to_table(columns=COLS, filter=ds.field('session_date') == pa.scalar(day)).to_pylist()
            for window, (start, end) in bounds(asset, day).items():
                selected = [r for r in rows if start <= r['ts_event'] < end]
                observed = [r['ts_event'].to_pydatetime() for r in selected]
                expected, cursor = set(), start.astimezone(UTC)
                while cursor < end.astimezone(UTC):
                    expected.add(cursor)
                    cursor += timedelta(minutes=1)
                missing = len(expected - set(observed))
                valid = all(r['low'] <= r['open'] <= r['high'] and r['low'] <= r['close'] <= r['high'] for r in selected)
                ready = set(observed) == expected and len(observed) == len(expected) and valid and len({r['instrument_id'] for r in selected}) == 1
                original = frame[(frame.asset == asset) & (frame.session_date == str(day)) & (frame.window == window)].iloc[0]
                if missing != original.missing_minutes or ready != original.valid_complete:
                    raise AssertionError(f'independent source comparison mismatch: {asset}/{day}/{window}')
                independent.append({'asset': asset, 'session_date': str(day), 'window': window,
                                    'missing_minutes': missing, 'valid_complete': ready, 'matched': True})
    write_csv(output / 'independent_source_checks.csv', independent)
    for record in verified:
        if sha(root / record['path']) != record['sha256']:
            raise AssertionError(f'input changed during audit: {record["path"]}')
    write_csv(output / 'input_verification.csv', verified)
    source_paths = [Path(__file__).resolve(), workspace / 'uv.lock',
                    workspace / 'packages/bhishma/src/abacus_bhishma/calendar.py',
                    workspace / 'packages/bhishma/src/abacus_bhishma/paths.py',
                    workspace / 'packages/bhishma/src/abacus_bhishma/continuous_loader.py',
                    workspace / 'packages/bhishma/src/abacus_bhishma/daily_context.py',
                    workspace / 'packages/bhishma/src/abacus_bhishma/manifest_selection.py',
                    workspace / 'packages/bhishma/src/abacus_bhishma/provenance.py']
    summary = {
        'kind': 'read_only_daily_facts_input_audit', 'started_at_utc': started,
        'completed_at_utc': datetime.now(UTC).isoformat(), 'workspace_root': str(workspace),
        'publication_root': str(root), 'source_range': [str(START), str(END)], 'common_start': str(COMMON),
        'scope': 'Selected retained input bytes, minute-grid/row coverage and preopen context; no fact release, research rerun or cloud changes.',
        'minute_manifest_sha256': BAR_HASH, 'context_manifest_sha256': CONTEXT_HASH,
        'calendar_sha256': sha(calendar_path), 'source_inputs_verified': len(verified),
        'inputs_unchanged_after_audit': True, 'inventory': inventories, 'daily_context_inventory': inventory_context,
        'coverage_by_window': summaries, 'calendar_exclusions': exclusions,
        'full_day_gate_losses': losses, 'common_asset_intersections': intersections,
        'context_summary': context_summaries, 'self_checks': checks,
        'independent_source_checks': len(independent),
        'environment': {'python': sys.version, 'platform': platform.platform(), 'numpy': np.__version__,
                        'pandas': pd.__version__, 'pyarrow': pa.__version__},
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=workspace, text=True).strip(),
        'git_status': subprocess.check_output(['git', 'status', '--short'], cwd=workspace, text=True),
        'command': sys.argv, 'declared_sources': [{'path': str(p.relative_to(workspace)), 'sha256': sha(p)} for p in source_paths],
        'limitations': ['No vendor-raw reconciliation or certification of absent no-trade minutes.',
                        'Existing calendar restrictions retained; nominal legacy windows are inventory only.',
                        'Modeled completed-bar timing is not historical point-in-time vintage certification.',
                        'No study results or Daily Facts numerical values calculated; no source release changed.'],
    }
    dump(output / 'summary.json', summary)
    artifacts = [{'path': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(output.iterdir()) if p.is_file()]
    dump(output / 'artifact_manifest.json', {'kind': 'input_audit_artifacts', 'artifacts': artifacts})
    print(json.dumps({'output': str(output), 'verified_inputs': len(verified), 'self_checks': len(checks),
                      'independent_checks': len(independent), 'window_rows': len(frame)}), flush=True)


if __name__ == '__main__':
    main()
