"""Independent saved-evidence checks; does not import the study calculation engine.

Version 3 reviews protocol 1.1.0's sole 3m timeframe. It independently derives
every eligible session's OHLCV and VWAP from the pinned one-minute source,
reconstructs saved events/tables and ATR context, and checks nine hand-recursive
EMA samples. No study calculation engine or Bhishma aggregation/indicator
implementation is imported. Run against an unsealed stage; historical reviewers
and completed runs remain unchanged.
"""
from __future__ import annotations

import argparse
import bisect
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as pads
import pyarrow.parquet as pq
from abacus_bhishma.paths import load_workspace_paths


BASE = ['product', 'timeframe', 'window', 'cohort']
DAY = ['product', 'timeframe', 'window', 'session_date']
EVENT = ['product', 'timeframe', 'ts_event']
PRIOR_RUN = '20261023T202400Z_ema6_v1'
TIMEFRAME = '3m'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def close(a, b, label, atol=1e-10):
    aa, bb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    require(aa.shape == bb.shape and np.allclose(aa, bb, rtol=1e-11, atol=atol, equal_nan=True), label)


def csv(path):
    return pd.read_csv(path, dtype={'session_date': str, 'year': str, 'month': str,
                                    'month_of_year': str})


def sorted_keys(frame, columns):
    return frame.sort_values(columns).reset_index(drop=True)


def reconstruct_days(bars):
    """Crossing predicates use direct shifted comparisons, not engine code."""
    records, event_parts = [], []
    for (product, timeframe), frame in bars.groupby(['product', 'timeframe'], sort=True):
        size = int(timeframe[:-1])
        f = frame.sort_values('ts_event').reset_index(drop=True)
        time = pd.DatetimeIndex(f.ts_event)
        previous_ema = f.ema6.shift()
        previous_vwap = f.globex_vwap.shift()
        eligible = ((f.session_date == f.session_date.shift()) &
                    (f.ts_event - f.ts_event.shift() == pd.Timedelta(minutes=size)) &
                    f.ema6.notna() & f.globex_vwap.notna() &
                    previous_ema.notna() & previous_vwap.notna())
        up = eligible & (f.ema6 > f.globex_vwap) & (previous_ema <= previous_vwap)
        down = eligible & (f.ema6 < f.globex_vwap) & (previous_ema >= previous_vwap)
        predicted = up.astype(int) - down.astype(int)
        require(np.array_equal(eligible.to_numpy(), f.event_defined.to_numpy()),
                f'event validity differs for {product}/{timeframe}')
        require(np.array_equal(predicted.to_numpy(), f.direction.to_numpy()),
                f'event direction differs for {product}/{timeframe}')
        require(np.array_equal(f.groupby('session_date').cumcount().to_numpy(), f.bar_position.to_numpy()),
                f'bar positions differ for {product}/{timeframe}')
        event_parts.append(f.loc[predicted != 0, EVENT + ['session_date', 'direction']])
        local = time.tz_convert('America/New_York')
        minute = local.hour * 60 + local.minute
        windows = {'globex': np.ones(len(f), bool),
                   'us_cash': (minute >= 570) & (minute < 960),
                   'globex_after_30_bars': f.bar_position.to_numpy() >= 31}
        if product == 'GC':
            windows['gc_day'] = (minute >= 500) & (minute < 810)
        for window, mask in windows.items():
            for session, g in f.loc[mask].groupby('session_date', sort=True):
                records.append({'product': product, 'timeframe': timeframe,
                                'window': window, 'session_date': session,
                                'crosses': int(np.count_nonzero(g.direction)),
                                'crosses_up': int(np.count_nonzero(g.direction > 0)),
                                'crosses_down': int(np.count_nonzero(g.direction < 0)),
                                'bars': len(g), 'defined_comparisons': int(g.event_defined.sum()),
                                'observed_hours': len(g) * size / 60})
    return pd.DataFrame(records), pd.concat(event_parts, ignore_index=True)


def verify_panel(panel, independent):
    require(len(panel) > 0 and len(independent) > 0, 'empty panel or independent session evidence')
    require(not panel.duplicated(DAY + ['cohort']).any(), 'duplicate panel session/window/cohort')
    comparison = panel.merge(independent, on=DAY, suffixes=('', '_check'), how='outer', indicator=True)
    require((comparison._merge == 'both').all(), 'panel and bar evidence have different session/window keys')
    for column in ['crosses', 'crosses_up', 'crosses_down', 'bars', 'defined_comparisons', 'observed_hours']:
        close(comparison[column], comparison[column + '_check'], 'panel ' + column)
    require((panel.crosses == panel.crosses_up + panel.crosses_down).all(), 'directions do not sum')
    require((panel.crosses == 0).any(), 'no retained true-zero session/window observations')
    return len(comparison)


def verify_cohorts(panel):
    cohorts = set(panel.cohort.unique())
    # Cohort names are saved in the source; identify their membership from dates.
    day_sets = {name: set(group.session_date) for name, group in panel.groupby('cohort')}
    common = ('2021-06-28', '2026-09-18')
    membership = {}
    for name in cohorts:
        g = panel[panel.cohort == name]
        membership[name] = {product: sorted(set(sub.session_date)) for product, sub in g.groupby('product')}
        if 'common' in name or 'matched' in name:
            require(g.session_date.between(*common).all(), f'{name} has date outside common calendar')
        if 'matched' in name:
            require(len({tuple(x) for x in membership[name].values()}) == 1,
                    'matched cohort has different product dates')
    require(cohorts == {'all_available', 'common_calendar', 'matched_dates'}, 'expected three declared cohorts')
    return {name: len(dates) for name, dates in day_sets.items()}


def verify_coverage(workspace, stage, bars, panel):
    release = json.loads((workspace / 'catalog/datasets/session_anchored_vwap__1.0.0.release.json').read_text())
    require(sha(workspace / release['audit']['path']) == release['audit']['sha256'], 'release audit bytes differ')
    original = pq.ParquetFile(workspace / release['audit']['path']).read().to_pandas()
    original['session_date'] = original.session_date.astype(str)
    saved = csv(stage / 'input_audit.csv')
    require(len(saved) == len(original), 'audit CSV row count differs from release')
    require(not saved.duplicated(['product', 'session_date']).any(), 'duplicate saved audit product/day')
    merged = saved.merge(original[['product', 'session_date', 'eligible']], on=['product', 'session_date'],
                         how='outer', suffixes=('', '_check'), indicator=True)
    require((merged._merge == 'both').all() and (merged.eligible == merged.eligible_check).all(),
            'saved audit eligibility differs from release')
    coverage = csv(stage / 'tables' / 'coverage.csv')
    require(not coverage.duplicated(['product', 'timeframe', 'month']).any(), 'duplicate coverage month')
    samples, common_sets = {}, {}
    for (product, timeframe), g in bars.groupby(['product', 'timeframe']):
        dates = set(g.session_date)
        eligible = set(original.loc[(original['product'] == product) & original.eligible, 'session_date'])
        require(dates == eligible, product + '/' + timeframe + ' not exactly published eligible sessions')
        months = pd.period_range(min(dates)[:7], max(dates)[:7], freq='M').astype(str)
        cells = coverage[(coverage['product'] == product) & (coverage.timeframe == timeframe)]
        require(set(cells.month) == set(months), 'coverage omits an intervening calendar month')
        for row in cells.itertuples(index=False):
            observed = g[g.session_date.str.startswith(row.month)]
            candidates = original[(original['product'] == product) & original.session_date.str.startswith(row.month)]
            require(row.eligible_sessions == observed.session_date.nunique() and row.observed_bars == len(observed)
                    and row.audit_candidate_sessions == len(candidates) and row.has_evidence == bool(len(observed)),
                    'coverage denominators differ for ' + product + '/' + timeframe + '/' + row.month)
            require(str(row.first_session) == str(observed.session_date.min()) and
                    str(row.last_session) == str(observed.session_date.max()),
                    'coverage first/last sessions differ for ' + product + '/' + timeframe + '/' + row.month)
        all_dates = set(panel.loc[(panel['product'] == product) & (panel.timeframe == timeframe) &
                                 (panel.cohort == 'all_available'), 'session_date'])
        common_dates = set(panel.loc[(panel['product'] == product) & (panel.timeframe == timeframe) &
                                    (panel.cohort == 'common_calendar'), 'session_date'])
        require(all_dates == dates, 'all-available cohort omits eligible days')
        require(common_dates == {d for d in dates if '2021-06-28' <= d <= '2026-09-18'},
                'common-calendar cohort membership differs')
        common_sets[(product, timeframe)] = common_dates
        samples[product + '/' + timeframe] = {'eligible_sessions': len(dates),
            'common_calendar_sessions': len(common_dates), 'calendar_months': len(cells),
            'no_sample_months': int((cells.eligible_sessions == 0).sum())}
    for timeframe in [TIMEFRAME]:
        shared = set.intersection(*(common_sets[(p, timeframe)] for p in ['ES', 'NQ', 'GC']))
        for product in ['ES', 'NQ', 'GC']:
            matched = set(panel.loc[(panel['product'] == product) & (panel.timeframe == timeframe) &
                                   (panel.cohort == 'matched_dates'), 'session_date'])
            require(matched == shared, 'matched-date cohort is not the exact common intersection')
    return {'release_audit_rows': len(original), 'coverage_cells': len(coverage), 'samples': samples}


def independent_statistics(group):
    counts = group.crosses.to_numpy(float)
    exposure = group.observed_hours.sum()
    return {'sessions': len(group), 'total_crosses': int(counts.sum()),
            'crosses_up': int(group.crosses_up.sum()), 'crosses_down': int(group.crosses_down.sum()),
            'mean_crosses': np.mean(counts), 'median_crosses': np.median(counts),
            'p25_crosses': np.percentile(counts, 25), 'p75_crosses': np.percentile(counts, 75),
            'p90_crosses': np.percentile(counts, 90), 'zero_cross_fraction': np.mean(counts == 0),
            'observed_hours': exposure, 'crosses_per_hour': counts.sum() / exposure,
            'small_cell': len(group) < 30}


def independent_intervals(group):
    """Literal circular-block draws, retaining labels before selecting a bin."""
    group = group.sort_values('session_date')
    n = len(group)
    values = group.crosses.to_numpy(float)
    choices = [('all', 'all', np.ones(n, dtype=bool))]
    for kind in ['atr_regime', 'realized_regime']:
        choices.extend((kind, regime, group[kind].to_numpy() == regime)
                       for regime in sorted(group[kind].unique()))
    samples = {(kind, regime): [] for kind, regime, _ in choices}
    rng = np.random.default_rng(20261023)
    for _ in range(2000):
        starts = rng.integers(0, n, size=(n + 4) // 5)
        draw = np.concatenate([np.arange(start, start + 5) % n for start in starts])[:n]
        for kind, regime, labels in choices:
            selected = values[draw][labels[draw]]
            if len(selected):
                samples[(kind, regime)].append(float(selected.mean()))
    return {key: np.percentile(values, [2.5, 97.5]) if values else [np.nan, np.nan]
            for key, values in samples.items()}


def verify_tables(stage, panel):
    checked = {}
    for name, period in [('summary', None), ('yearly', 'year'), ('monthly', 'month'),
                         ('month_of_year', 'month_of_year')]:
        table = csv(stage / 'tables' / (name + '.csv'))
        keys = BASE + ['segmentation', 'regime'] + ([] if period is None else [period])
        require(not table.duplicated(keys).any(), name + ' duplicate summary keys')
        expected = []
        for base_keys, g in panel.groupby(BASE, sort=True):
            identity = dict(zip(BASE, base_keys))
            intervals = independent_intervals(g) if period is None else None
            segments = [('all', 'all', g)]
            for kind in ['atr_regime', 'realized_regime']:
                segments.extend((kind, regime, sub) for regime, sub in g.groupby(kind, sort=True))
            for segmentation, regime, sub in segments:
                groups = [(None, sub)] if period is None else sub.groupby(period, sort=True)
                for date, cell in groups:
                    expected.append({**identity, 'segmentation': segmentation, 'regime': regime,
                                     **({} if period is None else {period: date}),
                                     **independent_statistics(cell),
                                     **({'mean_ci95_low': intervals[(segmentation, regime)][0],
                                         'mean_ci95_high': intervals[(segmentation, regime)][1]}
                                        if intervals is not None else {})})
        check = pd.DataFrame(expected)
        joined = table.merge(check, on=keys, suffixes=('', '_check'), how='outer', indicator=True)
        require((joined._merge == 'both').all(), name + ' missing or extra summary cells')
        for column in independent_statistics(panel.iloc[:1]):
            close(joined[column], joined[column + '_check'], name + '/' + column)
        if period is None:
            for column in ['mean_ci95_low', 'mean_ci95_high']:
                close(joined[column], joined[column + '_check'], 'independent block bootstrap/' + column)
        checked[name] = len(table)
    distribution = csv(stage / 'tables' / 'distribution.csv')
    expected_dist = []
    for base_keys, g in panel.groupby(BASE, sort=True):
        identity = dict(zip(BASE, base_keys))
        segments = [('all', 'all', g)]
        for kind in ['atr_regime', 'realized_regime']:
            segments.extend((kind, regime, sub) for regime, sub in g.groupby(kind, sort=True))
        for segmentation, regime, sub in segments:
            for count, frequency in sub.crosses.value_counts().items():
                expected_dist.append({**identity, 'segmentation': segmentation, 'regime': regime,
                                      'crosses': count, 'sessions': frequency, 'fraction': frequency / len(sub)})
    keys = BASE + ['segmentation', 'regime', 'crosses']
    require(not distribution.duplicated(keys).any(), 'duplicate distribution keys')
    joined = distribution.merge(pd.DataFrame(expected_dist), on=keys, suffixes=('', '_check'),
                                how='outer', indicator=True)
    require((joined._merge == 'both').all(), 'distribution keys differ')
    for column in ['sessions', 'fraction']:
        close(joined[column], joined[column + '_check'], 'distribution/' + column)
    checked['distribution'] = len(distribution)
    return checked


def verify_atr(workspace, bars, panel):
    manifest = json.loads((workspace / 'catalog/datasets/tradingview_daily_context__1.0.0.json').read_text())
    outcomes = {}
    for product, group in bars.groupby('product', sort=True):
        record = manifest['assets'][product]
        path = workspace / record['output_path']
        require(sha(path) == record['output_sha256'], 'daily context partition identity')
        daily = pq.ParquetFile(path).read(columns=['trading_day', 'available_at', 'atr14', 'atr14_pct']).to_pandas()
        daily = daily.sort_values('available_at').reset_index(drop=True)
        times = list(pd.to_datetime(daily.available_at, utc=True))
        require(len(times) == len(set(times)), 'duplicate daily available_at')
        sessions = group.groupby('session_date', sort=True).ts_event.min()
        expected = []
        valid_history_counts = []
        for date, opened in sessions.items():
            selected = bisect.bisect_right(times, opened) - 1
            row = {'session_date': date, 'atr14': np.nan, 'atr14_pct': np.nan,
                   'atr_percentile': np.nan, 'atr_regime': 'unknown',
                   'atr_source_day': '', 'atr_available_at': None}
            if selected >= 0 and (opened - times[selected]).total_seconds() <= 7 * 86400:
                source = daily.iloc[selected]
                if np.isfinite(source.atr14) and source.atr14 > 0 and np.isfinite(source.atr14_pct) and source.atr14_pct > 0:
                    history = daily.iloc[max(0, selected - 252):selected].atr14_pct.to_numpy(float)
                    valid_history_counts.append(int(np.isfinite(history).sum()))
                    rank = np.nan
                    if len(history) == 252 and np.isfinite(history).all():
                        rank = sum(float(x < source.atr14_pct) + .5 * float(x == source.atr14_pct)
                                   for x in history) / 252
                    regime = 'unknown' if not np.isfinite(rank) else ('low' if rank < 1 / 3 else 'normal' if rank < 2 / 3 else 'high')
                    row.update(atr14=source.atr14, atr14_pct=source.atr14_pct,
                               atr_percentile=rank, atr_regime=regime,
                               atr_source_day=str(source.trading_day), atr_available_at=times[selected])
            expected.append(row)
        check = pd.DataFrame(expected)
        actual = panel[panel['product'] == product]
        joined = actual.merge(check, on='session_date', suffixes=('', '_check'), how='left', validate='many_to_one')
        for column in ['atr14', 'atr14_pct', 'atr_percentile']:
            close(joined[column], joined[column + '_check'], product + '/' + column)
        require((joined.atr_regime == joined.atr_regime_check).all(), product + '/ATR bins')
        saved_times = pd.to_datetime(joined.atr_available_at, utc=True)
        check_times = pd.to_datetime(joined.atr_available_at_check, utc=True)
        require(((saved_times == check_times) | (saved_times.isna() & check_times.isna())).all(), product + '/ATR availability')
        require((joined.atr_source_day.fillna('') == joined.atr_source_day_check.fillna('')).all(), product + '/ATR source day')
        # Realized range is reconstructed from every saved session's bars;
        # full source reconciliation independently checks those high/low values.
        ranges = group.groupby(['timeframe', 'session_date']).agg(high=('high', 'max'), low=('low', 'min'))
        ranges['range_check'] = (ranges.high - ranges.low) * 1e-9
        realized = actual.merge(ranges[['range_check']].reset_index(), on=['timeframe', 'session_date'], validate='many_to_one')
        close(realized.session_range, realized.range_check, product + '/session range')
        ratios = realized.range_check / realized.atr14
        close(realized.range_atr, ratios, product + '/range ATR ratio')
        bins = np.where(~np.isfinite(ratios), 'unknown', np.where(ratios < .75, 'quiet', np.where(ratios < 1.25, 'normal', 'active')))
        require(np.array_equal(bins, realized.realized_regime.to_numpy()), product + '/realized bins')
        outcomes[product] = {'sessions': len(sessions), 'minimum_valid_rank_history': min(valid_history_counts, default=0),
                             'daily_rows': len(daily), 'initial_or_missing_atr_rows': int(daily.atr14_pct.isna().sum())}
    return outcomes


def selected_source_records(publication_root, product):
    manifest = json.loads((publication_root / 'catalog/datasets/volume_lead_back_adjusted_v1.json').read_text())
    records = [record for record in manifest['output_files']
               if f'/product={product}/' in record['path'] and '/variant=back_adjusted/' in record['path']
               and '/year=' in record['path'] and record['path'].endswith('.parquet')]
    require(len(records) > 0, product + ': empty one-minute source inventory')
    return records


def verify_source_bars(publication_root, bars):
    """Pandas group aggregation and two independent weighted-mean formulations.

    Cumulative weighted HLC3 sums check all VWAP values with absolute tolerance
    1e-8. An independently written recursive weighted mean also checks every
    direction with the producer's strict floating-point semantics; this avoids
    silently imposing a tolerance on crossings near zero.
    """
    outcomes = {}
    columns = ['ts_event', 'session_date', 'open', 'high', 'low', 'close', 'volume',
               'raw_symbol', 'instrument_id', 'price_adjustment']
    require(set(columns + ['bar_close_ts', 'available_at', 'source_bar_count', 'globex_vwap']).issubset(bars.columns),
            'bar evidence omits source reconciliation fields')
    for product, group in bars.groupby('product', sort=True):
        source_records = selected_source_records(publication_root, product)
        for record in source_records:
            require(sha(publication_root / record['path']) == record['sha256'],
                    product + ': pinned one-minute partition bytes differ')
        dataset = pads.dataset([str(publication_root / record['path']) for record in source_records], format='parquet')
        dates = sorted(group.session_date.unique())
        selected_days = pa.array([date.fromisoformat(day) for day in dates], type=pa.date32())
        source = dataset.to_table(columns=columns, filter=pads.field('session_date').isin(selected_days)).to_pandas()
        source['session_date'] = source.session_date.astype(str)
        source['ts_event'] = pd.to_datetime(source.ts_event, utc=True)
        require(not source.ts_event.duplicated().any(), product + ': duplicate source timestamps')
        require(set(source.session_date) == set(dates), product + ': source/evidence sessions differ')
        evidence_days = {day: frame.sort_values('ts_event').reset_index(drop=True)
                         for day, frame in group.groupby('session_date', sort=True)}
        checked_bars = 0
        near_zero_bars = 0
        cumsum_direction_differences = 0
        max_cumsum_error = 0.0
        max_recursive_error = 0.0
        for day, minutes in source.groupby('session_date', sort=True):
            minutes = minutes.sort_values('ts_event').reset_index(drop=True)
            evidence = evidence_days[day]
            opening_day = date.fromisoformat(day) - timedelta(days=1)
            opened = pd.Timestamp(f'{opening_day} 18:00', tz='America/New_York').tz_convert('UTC')
            expected_minutes = pd.date_range(opened, periods=1380, freq='min')
            require(len(minutes) == 1380 and pd.DatetimeIndex(minutes.ts_event).equals(expected_minutes),
                    product + '/' + day + ': incomplete or shifted 1,380-minute source roster')
            for lineage in ['raw_symbol', 'instrument_id', 'price_adjustment']:
                require(minutes[lineage].nunique(dropna=False) == 1, product + '/' + day + ': source lineage changes')
                require((evidence[lineage] == minutes[lineage].iloc[0]).all(), product + '/' + day + ': saved lineage differs')
            calculated = minutes.groupby(minutes.ts_event.dt.floor('3min'), sort=True).agg(
                open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
                close=('close', 'last'), volume=('volume', 'sum'), source_bar_count=('close', 'size'))
            require(len(calculated) == 460 and (calculated.source_bar_count == 3).all(),
                    product + '/' + day + ': incomplete 460-bar three-minute aggregation')
            require(len(evidence) == 460 and pd.DatetimeIndex(evidence.ts_event).equals(calculated.index),
                    product + '/' + day + ': saved three-minute bar-open timestamps differ')
            for field in ['open', 'high', 'low', 'close', 'volume', 'source_bar_count']:
                require(np.array_equal(evidence[field].to_numpy(), calculated[field].to_numpy()),
                        product + '/' + day + ': source-derived ' + field + ' differs')
            close_times = calculated.index + pd.Timedelta(minutes=3)
            for field in ['bar_close_ts', 'available_at']:
                require(pd.DatetimeIndex(pd.to_datetime(evidence[field], utc=True)).equals(close_times),
                        product + '/' + day + ': saved ' + field + ' differs')
            require(not evidence.event_defined.iloc[0] and evidence.direction.iloc[0] == 0,
                    product + '/' + day + ': anchor reset counted as defined crossing')
            price = ((calculated.high.to_numpy(float) * 1e-9 + calculated.low.to_numpy(float) * 1e-9
                      + calculated.close.to_numpy(float) * 1e-9) / 3.0)
            weights = calculated.volume.to_numpy(np.uint64)
            require(np.isfinite(price).all() and (weights >= 0).all(), 'invalid source HLC3/volume')
            cumulative_weight = np.cumsum(weights, dtype=np.uint64)
            weighted_sum = np.cumsum(price * weights.astype(float))
            cumulative_vwap = np.divide(weighted_sum, cumulative_weight, out=np.full(len(price), np.nan),
                                        where=cumulative_weight != 0)
            recursive_vwap = np.full(len(price), np.nan)
            total, running = 0, 0.0
            for position, (value, weight) in enumerate(zip(price, weights)):
                weight = int(weight)
                if weight:
                    if total:
                        running = running + weight / (total + weight) * (float(value) - running)
                    else:
                        running = float(value)
                    total += weight
                if total:
                    recursive_vwap[position] = running
            saved_vwap = evidence.globex_vwap.to_numpy(float)
            require(np.allclose(saved_vwap, cumulative_vwap, rtol=0, atol=1e-8, equal_nan=True),
                    product + '/' + day + ': cumulative weighted source VWAP differs')
            require(np.array_equal(saved_vwap, recursive_vwap, equal_nan=True),
                    product + '/' + day + ': source recursive weighted VWAP differs')
            delta = evidence.ema6.to_numpy(float) - recursive_vwap
            defined = np.zeros(len(delta), bool)
            defined[1:] = np.isfinite(delta[1:]) & np.isfinite(delta[:-1])
            direction = np.zeros(len(delta), int)
            direction[1:] = np.where(defined[1:] & (delta[1:] > 0) & (delta[:-1] <= 0), 1,
                                    np.where(defined[1:] & (delta[1:] < 0) & (delta[:-1] >= 0), -1, 0))
            require(np.array_equal(defined, evidence.event_defined), product + '/' + day + ': source event validity differs')
            require(np.array_equal(direction, evidence.direction), product + '/' + day + ': source crossing direction differs')
            cumulative_delta = evidence.ema6.to_numpy(float) - cumulative_vwap
            cumulative_direction = np.zeros(len(delta), int)
            cumulative_direction[1:] = np.where(defined[1:] & (cumulative_delta[1:] > 0) & (cumulative_delta[:-1] <= 0), 1,
                                               np.where(defined[1:] & (cumulative_delta[1:] < 0) & (cumulative_delta[:-1] >= 0), -1, 0))
            cumsum_direction_differences += int(np.count_nonzero(cumulative_direction != direction))
            near_zero_bars += int(np.count_nonzero(np.abs(delta) <= 1e-8))
            checked_bars += len(evidence)
            max_cumsum_error = max(max_cumsum_error, float(np.nanmax(np.abs(saved_vwap - cumulative_vwap))))
            max_recursive_error = max(max_recursive_error, float(np.nanmax(np.abs(saved_vwap - recursive_vwap))))
        outcomes[product] = {'sessions_checked': len(dates), 'source_minutes_checked': len(source),
                             'bars_checked': checked_bars, 'source_partition_count': len(source_records),
                             'max_cumulative_vwap_absolute_difference': max_cumsum_error,
                             'max_recursive_vwap_absolute_difference': max_recursive_error,
                             'near_zero_delta_bars': near_zero_bars,
                             'cumulative_vs_recursive_direction_differences': cumsum_direction_differences,
                             'strict_source_recursive_directions_match': True,
                             'source_partitions': [{'path': record['path'], 'sha256': record['sha256']} for record in source_records]}
        print(product + ': all eligible 3m source bars, VWAP and directions reconciled', flush=True)
    return outcomes


def verify_previous_run(workspace, panel):
    """Timeframe changes must leave coverage, ranges and ATR classifications intact."""
    path = workspace / 'runs/28_globex_ema_crossings' / PRIOR_RUN / 'daily_panel.csv'
    prior = csv(path)
    keys = ['product', 'session_date', 'cohort']
    numbers = ['session_range', 'atr14', 'atr14_pct', 'atr_percentile', 'range_atr']
    labels = ['atr_regime', 'realized_regime', 'atr_source_day', 'atr_available_at']
    previous = prior[(prior.timeframe == '5m') & (prior.window == 'globex')][keys + numbers + labels]
    current = panel[panel.window == 'globex'][keys + numbers + labels]
    require(not previous.duplicated(keys).any() and not current.duplicated(keys).any(), 'duplicate invariant comparison keys')
    joined = current.merge(previous, on=keys, suffixes=('', '_prior'), how='outer', indicator=True)
    require((joined._merge == 'both').all(), '3m versus prior 5m product/day/cohort coverage differs')
    for field in numbers:
        close(joined[field], joined[field + '_prior'], 'prior-run invariant/' + field)
    for field in labels:
        require((joined[field].fillna('') == joined[field + '_prior'].fillna('')).all(),
                'prior-run invariant/' + field)
    return {'prior_run': PRIOR_RUN, 'prior_daily_panel_sha256': sha(path),
            'rows_checked': len(joined), 'numeric_fields': numbers, 'label_fields': labels,
            'coverage_ranges_atr_context_and_labels_unchanged': True}


def verify_ema_samples(workspace, bars):
    manifest = json.loads((workspace / 'catalog/datasets/volume_lead_back_adjusted_v1.json').read_text())
    results = []
    for (product, timeframe), group in bars.groupby(['product', 'timeframe'], sort=True):
        candidates = sorted(group.session_date.unique())
        selected = [candidates[0], candidates[len(candidates) // 2], candidates[-1]]
        paths = [str(workspace / record['path']) for record in manifest['output_files']
                 if f'/product={product}/' in record['path'] and '/variant=back_adjusted/' in record['path']
                 and '/year=' in record['path'] and record['path'].endswith('.parquet')]
        dataset = pads.dataset(paths, format='parquet')
        for session in selected:
            evidence = group[group.session_date == session].sort_values('ts_event')
            start, end = evidence.ts_event.iloc[0], evidence.ts_event.iloc[-1] + pd.Timedelta(minutes=int(timeframe[:-1]))
            predicate = ((pads.field('ts_event') >= pa.scalar(start - pd.Timedelta(days=7))) &
                         (pads.field('ts_event') < pa.scalar(end)))
            minutes = dataset.to_table(columns=['ts_event', 'close'], filter=predicate).to_pandas().sort_values('ts_event')
            closes = minutes.groupby(minutes.ts_event.dt.floor(f'{int(timeframe[:-1])}min')).close.last()
            require((closes.index < start).sum() >= 250, 'source sample lacks 250 preceding observed bars')
            values = closes.to_numpy(float) * 1e-9
            expected = np.empty(len(values), float)
            expected[0] = values[0]
            for i in range(1, len(values)):
                expected[i] = (2 * values[i] + 5 * expected[i - 1]) / 7
            sample = pd.DataFrame({'close_check': closes.to_numpy(), 'ema_check': expected}, index=closes.index)
            joined = evidence.merge(sample, left_on='ts_event', right_index=True, how='left', validate='one_to_one')
            close(joined.ema6, joined.ema_check, f'{product}/{timeframe}/{session} EMA source sample', atol=1e-8)
            if 'close' in joined:
                require((joined.close == joined.close_check).all(), 'sample close parity')
            results.append({'product': product, 'timeframe': timeframe, 'session_date': session,
                            'bars_checked': len(joined), 'preceding_observed_bars': int((closes.index < start).sum()),
                            'max_ema_absolute_difference': float(np.max(np.abs(joined.ema6 - joined.ema_check)))})
    return results


def main():
    started = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, type=Path)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    stage, workspace = args.stage.resolve(), args.workspace.resolve()
    publication_root = load_workspace_paths(workspace).publication_root
    require('work' in stage.relative_to(workspace).parts, 'verify an unsealed work stage')
    output = stage / 'saved-evidence-verification.json'
    review_log = stage / 'saved-evidence-review.log'
    require(not output.exists() and not review_log.exists(), 'verification receipt/log already exists; preserve prior review')
    config = json.loads((stage / 'config.json').read_text())
    require(config['protocol_version'] == '1.1.0' and config['primary_timeframe'] == TIMEFRAME
            and config['timeframes'] == [TIMEFRAME] and config['ema_period'] == 6,
            'v3 reviewer requires sole 3m EMA6 protocol 1.1.0')
    retained_reviewer = stage / 'provenance/source/studies/28_globex_ema_crossings/verify_saved_v3.py'
    require(retained_reviewer.is_file() and sha(retained_reviewer) == sha(__file__),
            'reviewer differs from the source frozen before calculation')
    for pin in json.loads((stage / 'inputs.lock.json').read_text())['releases']:
        require(sha(publication_root / pin['path']) == pin['sha256'], 'manifest/spec differs from frozen input pin')
    bar_path = stage / 'bar_evidence.parquet'
    event_path, panel_path = stage / 'crossings.csv', stage / 'daily_panel.csv'
    bars = pq.ParquetFile(bar_path).read().to_pandas()
    bars['ts_event'] = pd.to_datetime(bars.ts_event, utc=True)
    bars['session_date'] = bars.session_date.astype(str)
    require(len(bars) > 0 and not bars.duplicated(EVENT).any(), 'empty bars or duplicate bar identities')
    require(set(bars.timeframe) == {TIMEFRAME} and set(bars['product']) == {'ES', 'NQ', 'GC'},
            'unexpected product/timeframe evidence')
    source_bars = verify_source_bars(publication_root, bars)
    independent, events = reconstruct_days(bars)
    panel = csv(panel_path)
    require(set(panel.timeframe) == {TIMEFRAME}, 'unexpected panel timeframe')
    require((panel.crosses >= 0).all() and np.equal(panel.crosses, np.floor(panel.crosses)).all(),
            'negative or fractional crossing count')
    panel['year'], panel['month'], panel['month_of_year'] = panel.session_date.str[:4], panel.session_date.str[:7], panel.session_date.str[5:7]
    comparisons = verify_panel(panel, independent)
    ledger = csv(event_path)
    ledger['ts_event'] = pd.to_datetime(ledger.ts_event, utc=True)
    # A crossing is retained once per chart bar; window and cohort membership
    # belongs in the panel. Explicit duplicate ledger rows are never accepted.
    require(not ledger.duplicated(EVENT).any(), 'duplicate crossing identities')
    actual = sorted_keys(ledger, EVENT)
    expected = sorted_keys(events, EVENT)
    require(len(actual) == len(expected), 'ledger crossing count differs')
    require(actual[EVENT].equals(expected[EVENT]), 'ledger crossing keys differ')
    close(actual.direction, expected.direction, 'ledger directions differ')
    checked_tables = verify_tables(stage, panel)
    cohort_sizes = verify_cohorts(panel)
    coverage = verify_coverage(publication_root, stage, bars, panel)
    context = verify_atr(publication_root, bars, panel)
    ema_samples = verify_ema_samples(publication_root, bars)
    require(len(ema_samples) == 9, 'expected nine independent source EMA session samples')
    previous = verify_previous_run(workspace, panel)
    completed = datetime.now(timezone.utc)
    stdout_lines = [product + ': all eligible 3m source bars, VWAP and directions reconciled'
                    for product in sorted(source_bars)]
    final_output = json.dumps({'status': 'passed', 'bars_checked': len(bars), 'crossings_checked': len(events),
                               'panel_rows_checked': comparisons, 'tables_checked': checked_tables,
                               'source_ema_sample_sessions': len(ema_samples), 'receipt': str(output)}, indent=2)
    review_log.write_text('\n'.join([*stdout_lines, final_output]) + '\n')
    retained = [bar_path, event_path, panel_path, stage / 'input_audit.csv', review_log,
                retained_reviewer, *sorted((stage / 'tables').glob('*.csv'))]
    receipt = {'schema_version': 1, 'status': 'passed', 'reviewer_version': 3,
               'reviewer_version_reason': 'New sole-3m protocol 1.1.0 requires full source OHLCV/VWAP reconciliation and invariance to the previous run for coverage/ranges/ATR context. Reviewer frozen before execution; no producer imports.',
               'scope': 'All source-derived 3m OHLCV/timestamps/VWAP and strict directions, independent saved-bar event/panel/table reconstruction including exact bootstrap, ATR alignment/ranks/bins, nine bounded hand-recursive EMA source samples, and prior-run coverage/range/ATR invariants. No trade-profitability validation.',
               'execution': {'argv': [sys.executable, *sys.argv], 'cwd': str(Path.cwd()),
                             'started_utc': started.isoformat(), 'completed_utc': completed.isoformat(),
                             'duration_seconds': (completed - started).total_seconds(),
                             'stdout_log': review_log.relative_to(stage).as_posix(),
                             'return_code_record': 'The invoking process records the actual exit code separately.'},
               'verifier_sha256': sha(__file__), 'bars_checked': len(bars),
               'retained_reviewer_source': retained_reviewer.relative_to(stage).as_posix(),
               'crossings_checked': len(events), 'panel_rows_checked': comparisons,
               'tables_checked': checked_tables, 'cohort_unique_dates': cohort_sizes,
               'coverage_and_audit_checks': coverage,
               'daily_context_checks': context, 'ema_source_samples': ema_samples,
               'three_minute_source_checks': source_bars,
               'previous_run_invariants': previous,
               'true_zero_panel_rows': int((panel.crosses == 0).sum()),
               'artifacts': [{'path': p.relative_to(stage).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in retained]}
    output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(final_output)


if __name__ == '__main__':
    main()
