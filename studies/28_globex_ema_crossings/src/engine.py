"""Study-local deterministic crossing, volatility and summary definitions."""
from __future__ import annotations

import numpy as np
import pandas as pd

ALPHA = 2 / 7
BASE = ['product', 'timeframe', 'window', 'cohort']


def ema6(values):
    x = np.asarray(values, dtype=float)
    if not np.isfinite(x).all():
        raise ValueError('EMA input must be finite')
    return pd.Series(x).ewm(alpha=ALPHA, adjust=False).mean().to_numpy()


def aggregate_closes(minutes, timeframe):
    size = int(timeframe.removesuffix('m'))
    if size not in (2, 3, 5):
        raise ValueError('unsupported timeframe')
    return minutes.groupby(minutes.ts_event.dt.floor(f'{size}min'), sort=True).close.last().to_frame()


def crossing_directions(ema, vwap, session, timestamps, minutes):
    d = np.asarray(ema) - np.asarray(vwap)
    prev = np.roll(d, 1)
    same = np.asarray(session) == np.roll(np.asarray(session), 1)
    ts = pd.DatetimeIndex(timestamps)
    consecutive = np.asarray(ts - ts.to_series().shift(1).array == pd.Timedelta(minutes=minutes))
    valid = same & consecutive & np.isfinite(d) & np.isfinite(prev)
    valid[0] = False
    direction = np.where(valid & (d > 0) & (prev <= 0), 1,
                         np.where(valid & (d < 0) & (prev >= 0), -1, 0))
    return direction, valid


def window_masks(timestamps, product, bar_position):
    local = pd.DatetimeIndex(timestamps).tz_convert('America/New_York')
    clock = local.hour * 60 + local.minute
    masks = {'globex': np.ones(len(local), dtype=bool),
             'us_cash': (clock >= 570) & (clock < 960),
             'globex_after_30_bars': np.asarray(bar_position) > 30}
    if product == 'GC':
        masks['gc_day'] = (clock >= 500) & (clock < 810)
    return masks


def atr_bin(percentile):
    if not np.isfinite(percentile):
        return 'unknown'
    return 'low' if percentile < 1/3 else ('normal' if percentile < 2/3 else 'high')


def realized_bin(ratio):
    if not np.isfinite(ratio):
        return 'unknown'
    return 'quiet' if ratio < .75 else ('normal' if ratio < 1.25 else 'active')


def atr_context(daily, session_opens, lookback=252):
    """As-of ATR plus trailing percentile excluding the chosen daily row."""
    d = daily.sort_values('available_at').copy().reset_index(drop=True)
    if d.available_at.duplicated().any():
        raise ValueError('duplicate daily availability')
    pct = d.atr14_pct.to_numpy(float)
    ranks = np.full(len(d), np.nan)
    for i in range(lookback, len(d)):
        h = pct[i-lookback:i]
        if np.isfinite(h).all() and np.isfinite(pct[i]):
            ranks[i] = (np.sum(h < pct[i]) + .5*np.sum(h == pct[i])) / lookback
    opens = pd.DatetimeIndex(session_opens)
    available = pd.DatetimeIndex(d.available_at)
    indices = available.searchsorted(opens, side='right') - 1
    out = []
    for when, i in zip(opens, indices):
        row = {'atr_source_day': None, 'atr_available_at': None,
               'atr14': np.nan, 'atr14_pct': np.nan,
               'atr_percentile': np.nan, 'atr_regime': 'unknown'}
        if i >= 0 and when - available[i] <= pd.Timedelta(days=7):
            r = d.iloc[i]
            if np.isfinite(r.atr14) and r.atr14 > 0 and np.isfinite(r.atr14_pct) and r.atr14_pct > 0:
                row = {'atr_source_day': str(r.trading_day),
                       'atr_available_at': available[i].isoformat(),
                       'atr14': float(r.atr14), 'atr14_pct': float(r.atr14_pct),
                       'atr_percentile': ranks[i], 'atr_regime': atr_bin(ranks[i])}
        out.append(row)
    return pd.DataFrame(out)


def summarize_group(g):
    x = g.crosses.to_numpy(float)
    n = len(x)
    return {'sessions': n, 'total_crosses': int(x.sum()),
            'crosses_up': int(g.crosses_up.sum()), 'crosses_down': int(g.crosses_down.sum()),
            'mean_crosses': float(x.mean()), 'median_crosses': float(np.median(x)),
            'p25_crosses': float(np.quantile(x, .25)), 'p75_crosses': float(np.quantile(x, .75)),
            'p90_crosses': float(np.quantile(x, .9)), 'zero_cross_fraction': float((x == 0).mean()),
            'observed_hours': float(g.observed_hours.sum()),
            'crosses_per_hour': float(x.sum()/g.observed_hours.sum()),
            'small_cell': n < 30}


def moving_block_means(values, labels, categories, replicates=2000, seed=20261023):
    """Bootstrap complete observed-day panels before regime subsetting."""
    x, labels = np.asarray(values), np.asarray(labels)
    n = len(x)
    rng = np.random.default_rng(seed)
    indices = ((rng.integers(0, n, size=(replicates, (n+4)//5))[:, :, None]
                + np.arange(5)) % n).reshape(replicates, -1)[:, :n]
    sampled_x, sampled_labels = x[indices], labels[indices]
    result = {}
    for category in categories:
        mask = np.ones_like(indices, dtype=bool) if category == 'all' else sampled_labels == category
        denominator = mask.sum(axis=1)
        means = np.divide((sampled_x * mask).sum(axis=1), denominator,
                          out=np.full(replicates, np.nan), where=denominator > 0)
        finite = means[np.isfinite(means)]
        result[category] = (float(np.quantile(finite, .025)), float(np.quantile(finite, .975))) if len(finite) else (np.nan, np.nan)
    return result


def make_tables(panel):
    """Return evidence tables. No missing day is made into a zero observation."""
    panel = panel.copy()
    panel['year'] = panel.session_date.str[:4]
    panel['month'] = panel.session_date.str[:7]
    panel['month_of_year'] = panel.session_date.str[5:7]
    records = {name: [] for name in ['summary', 'yearly', 'monthly', 'month_of_year', 'distribution']}
    for keys, base in panel.groupby(BASE, sort=True):
        base = base.sort_values('session_date')
        identifiers = dict(zip(BASE, keys))
        specifications = [('all', None), ('atr_regime', 'atr_regime'), ('realized_regime', 'realized_regime')]
        for segmentation, column in specifications:
            categories = ['all'] if column is None else sorted(base[column].unique())
            labels = np.full(len(base), 'all') if column is None else base[column].to_numpy()
            cis = moving_block_means(base.crosses.to_numpy(), labels, categories)
            for category in categories:
                g = base if column is None else base[base[column] == category]
                identity = {**identifiers, 'segmentation': segmentation, 'regime': category}
                row = {**identity, **summarize_group(g)}
                row['mean_ci95_low'], row['mean_ci95_high'] = cis[category]
                records['summary'].append(row)
                for name in ['yearly', 'monthly', 'month_of_year']:
                    field = {'yearly': 'year', 'monthly': 'month', 'month_of_year': 'month_of_year'}[name]
                    for period, sub in g.groupby(field, sort=True):
                        records[name].append({**identity, field: period, **summarize_group(sub)})
                for count, sub in g.groupby('crosses', sort=True):
                    records['distribution'].append({**identity, 'crosses': int(count), 'sessions': len(sub), 'fraction': len(sub)/len(g)})
    return {k: pd.DataFrame(v) for k, v in records.items()}
