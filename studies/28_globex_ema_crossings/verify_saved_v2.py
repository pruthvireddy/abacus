"""Independent saved-evidence checks; does not import the study calculation engine.

This reconstructs events and aggregations from the retained bar evidence and
checks ATR context plus bounded EMA samples against the pinned input releases.
It does not recalculate or publish a dataset. Run against an unsealed stage.

Version 2 corrects the source EMA sampler's pandas resampling alias from ``5m``
or ``2m`` (parsed as month-end offsets) to explicit ``5min`` or ``2min``. The
original reviewer was already frozen with the execution sources and remains
unchanged; this separately retained reviewer is not a calculation producer.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as pads
import pyarrow.parquet as pq


BASE = ['product', 'timeframe', 'window', 'cohort']
DAY = ['product', 'timeframe', 'window', 'session_date']
EVENT = ['product', 'timeframe', 'ts_event']


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
    require(not panel.duplicated(DAY + ['cohort']).any(), 'duplicate panel session/window/cohort')
    comparison = panel.merge(independent, on=DAY, suffixes=('', '_check'), how='outer', indicator=True)
    require((comparison._merge == 'both').all(), 'panel and bar evidence have different session/window keys')
    for column in ['crosses', 'crosses_up', 'crosses_down', 'bars', 'defined_comparisons', 'observed_hours']:
        close(comparison[column], comparison[column + '_check'], 'panel ' + column)
    require((panel.crosses == panel.crosses_up + panel.crosses_down).all(), 'directions do not sum')
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
    require(len(cohorts) == 3, 'expected three cohorts')
    return {name: len(dates) for name, dates in day_sets.items()}


def verify_coverage(workspace, stage, bars, panel):
    release = json.loads((workspace / 'catalog/datasets/session_anchored_vwap__1.0.0.release.json').read_text())
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
    for timeframe in ['5m', '2m']:
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
        # Realized range is reconstructed separately for each interval to avoid
        # relying on agreement between 2m and 5m evidence as its only check.
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, type=Path)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    stage, workspace = args.stage.resolve(), args.workspace.resolve()
    require('work' in stage.relative_to(workspace).parts, 'verify an unsealed work stage')
    for pin in json.loads((stage / 'inputs.lock.json').read_text())['releases']:
        require(sha(workspace / pin['path']) == pin['sha256'], 'manifest/spec differs from frozen input pin')
    bar_path = stage / 'bar_evidence.parquet'
    event_path, panel_path = stage / 'crossings.csv', stage / 'daily_panel.csv'
    bars = pq.ParquetFile(bar_path).read().to_pandas()
    bars['ts_event'] = pd.to_datetime(bars.ts_event, utc=True)
    bars['session_date'] = bars.session_date.astype(str)
    require(not bars.duplicated(EVENT).any(), 'duplicate bar identities')
    independent, events = reconstruct_days(bars)
    panel = csv(panel_path)
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
    coverage = verify_coverage(workspace, stage, bars, panel)
    context = verify_atr(workspace, bars, panel)
    ema_samples = verify_ema_samples(workspace, bars)
    retained = [bar_path, event_path, panel_path, *sorted((stage / 'tables').glob('*.csv'))]
    receipt = {'schema_version': 1, 'status': 'passed', 'reviewer_version': 2,
               'reviewer_version_reason': 'The original verifier was frozen before execution. Version 2 independently corrects its source EMA sampler to explicit minute aliases; it was not used to produce crossing outcomes.',
               'scope': 'Independent saved-bar event/panel/table reconstruction, ATR input alignment/ranks/bins and bounded source EMA samples; no trade-profitability validation.',
               'verifier_sha256': sha(__file__), 'bars_checked': len(bars),
               'crossings_checked': len(events), 'panel_rows_checked': comparisons,
               'tables_checked': checked_tables, 'cohort_unique_dates': cohort_sizes,
               'coverage_and_audit_checks': coverage,
               'daily_context_checks': context, 'ema_source_samples': ema_samples,
               'artifacts': [{'path': p.relative_to(stage).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in retained]}
    output = stage / 'saved-evidence-verification.json'
    require(not output.exists(), 'verification receipt already exists; preserve the prior receipt')
    output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': 'passed', 'bars_checked': len(bars), 'crossings_checked': len(events),
                      'panel_rows_checked': comparisons, 'tables_checked': checked_tables,
                      'source_ema_sample_sessions': len(ema_samples), 'receipt': str(output)}, indent=2))


if __name__ == '__main__':
    main()
