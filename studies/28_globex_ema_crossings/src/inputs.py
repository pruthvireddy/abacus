"""Pinned read-only loaders; compute no reusable feature publications."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as pads
import pyarrow.parquet as pq
from abacus_bhishma.continuous_loader import open_continuous_dataset
from abacus_bhishma.feature_loader import load_session_anchored_vwap
from abacus_bhishma.daily_context import load_daily_context
from abacus_bhishma.paths import load_workspace_paths
from abacus_bhishma.session_anchored_vwap import (SOURCE_COLUMNS, aggregate_session, output_schema, session_bounds)
from .engine import aggregate_closes, ema6, atr_context, realized_bin, crossing_directions, window_masks


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024*1024), b''):
            h.update(part)
    return h.hexdigest()


def prepare_inputs(workspace, study, stage):
    paths = load_workspace_paths(workspace)
    root = paths.publication_root
    lock = json.loads((study/'inputs.lock.json').read_text())
    manifests = {}
    inventory = []
    for pin in lock['releases']:
        p = root/pin['path']
        if sha(p) != pin['sha256']:
            raise ValueError(f'input identity mismatch: {p}')
        manifests[pin['path']] = json.loads(p.read_text())
        inventory.append({**pin, 'role': 'manifest_or_definition'})
    for name, manifest in manifests.items():
        files = manifest.get('output_files', []) if '/datasets/' in name else []
        if name == 'catalog/datasets/tradingview_daily_context__1.0.0.json':
            files = [{'path': a['output_path'], 'sha256': a['output_sha256']}
                     for k,a in manifest['assets'].items() if k in ['ES','NQ','GC']]
        if name.endswith('session_anchored_vwap__1.0.0.release.json'):
            files = [manifest['audit']]
        for item in files:
            p = root/item['path']
            # Source manifests may include non-bar auxiliary outputs, retain and verify all declared bytes.
            if sha(p) != item['sha256']:
                raise ValueError(f'partition mismatch: {p}')
            inventory.append({'path': item['path'], 'sha256': item['sha256'], 'bytes': p.stat().st_size, 'role': 'data_or_auxiliary'})
    unique = {r['path']: r for r in inventory}
    (stage/'input-verification.json').write_text(json.dumps(list(unique.values()),indent=2)+'\n')
    return root, manifests


def derive_three_minute_session(source, product, tick, schema):
    """Use Bhishma numerical aggregation in memory; never write a feature release."""
    if source.num_rows != 1380:
        raise ValueError('three-minute derivation requires a complete session')
    day = source['session_date'][0].as_py()
    opened, closed = session_bounds(day)
    timestamps = source['ts_event'].cast(pa.int64()).to_numpy()
    expected = np.arange(opened, closed, 60_000_000_000, dtype=np.int64)
    if not np.array_equal(timestamps, expected):
        raise ValueError('source minute roster differs from the full Globex session')
    for column in ['session_date', 'instrument_id', 'raw_symbol', 'price_adjustment']:
        if len(set(source[column].to_pylist())) != 1:
            raise ValueError('session lineage changed: ' + column)
    if set(source['product'].to_pylist()) != {product}:
        raise ValueError('source product differs')
    # output_schema has legacy release metadata; never retain it as a dataset identity.
    derived = aggregate_session(source, product, 3, tick, schema)
    columns = ['ts_event','bar_close_ts','available_at','session_date','product','timeframe',
               'open','high','low','close','volume','globex_vwap','raw_symbol','instrument_id',
               'price_adjustment','min_tick','source_bar_count']
    return derived.select(columns).replace_schema_metadata(None)


def load_product(root, manifests, product):
    source_path = 'catalog/datasets/volume_lead_back_adjusted_v1.json'
    source_hash = sha(root/source_path)
    dataset = open_continuous_dataset(root, product, 'back_adjusted', manifest_path=source_path,
                                     expected_manifest_sha256=source_hash)
    minutes = dataset.to_table(columns=['ts_event','close']).to_pandas().sort_values('ts_event')
    if minutes.ts_event.duplicated().any():
        raise ValueError('duplicate source timestamp')
    daily = load_daily_context(root, product, version='1.0.0',
                columns=['trading_day','available_at','atr14','atr14_pct']).to_pandas()
    # The released 5m file is used only for immutable eligibility/contract/tick identity.
    reference_path = 'catalog/datasets/session_anchored_vwap_5m_v1.json'
    reference = load_session_anchored_vwap(root, product, '5m', version='1.0.0',
        manifest_path=reference_path, expected_manifest_sha256=sha(root/reference_path),
        columns=['session_date','min_tick','raw_symbol','instrument_id','price_adjustment']).to_pandas()
    dates = sorted(reference.session_date.unique())
    audit = read_audit(root)
    audited = set(audit.loc[(audit['product'] == product) & audit.eligible, 'session_date'])
    if set(dates) != audited:
        raise ValueError('published reference/audit eligibility mismatch')
    ticks = {}
    for day,g in reference.groupby('session_date',sort=True):
        if any(g[c].nunique() != 1 for c in ['min_tick','raw_symbol','instrument_id','price_adjustment']):
            raise ValueError('reference session lineage differs')
        ticks[day] = int(g.min_tick.iloc[0])
    selected = dataset.to_table(columns=list(SOURCE_COLUMNS),
              filter=pads.field('session_date').isin(dates)).sort_by([('ts_event','ascending')])
    session_dates = selected['session_date'].to_numpy()
    starts = np.flatnonzero(np.r_[True,session_dates[1:] != session_dates[:-1]])
    ends = np.r_[starts[1:],len(session_dates)]
    schema = output_schema(source_hash, sha(root/'catalog/calendars/cme_fixed_clock_session_v1.json'),
                           sha(root/'catalog/indicators/session_anchored_vwap__1.0.0.json'),3)
    parts = []
    for start,end in zip(starts,ends):
        source = selected.slice(int(start),int(end-start))
        day = source['session_date'][0].as_py()
        parts.append(derive_three_minute_session(source,product,ticks[day],schema))
    f = pa.concat_tables(parts).to_pandas().sort_values('ts_event').reset_index(drop=True)
    tf,size = '3m',3
    bars = aggregate_closes(minutes,tf)
    bars['ema6'] = ema6(bars.close.to_numpy(float)*1e-9)
    bars['source_position'] = np.arange(len(bars))
    joined = f.merge(bars[['close','ema6','source_position']],left_on='ts_event',right_index=True,
                      how='left',suffixes=('', '_source'),validate='one_to_one')
    if joined.ema6.isna().any() or not (joined.close == joined.close_source).all():
        raise ValueError('source/derived three-minute close parity failed')
    if joined.source_position.min() < 250:
        raise ValueError('insufficient preceding source warmup')
    if not (joined.available_at == joined.bar_close_ts).all():
        raise ValueError('bar timing mismatch')
    joined['session_date'] = joined.session_date.astype(str)
    joined['bar_position'] = joined.groupby('session_date').cumcount()
    if not (joined.groupby('session_date').size() == 460).all():
        raise ValueError('incomplete derived session')
    direction,valid = crossing_directions(joined.ema6,joined.globex_vwap,joined.session_date,joined.ts_event,size)
    joined['direction'],joined['event_defined'] = direction,valid
    return [joined],daily


def build_panel(frame, daily):
    product = frame['product'].iloc[0]
    size = int(frame.timeframe.iloc[0][:-1])
    days = frame.groupby('session_date', sort=True).agg(
        session_open=('ts_event','first'), session_high=('high','max'),session_low=('low','min'))
    context = atr_context(daily, days.session_open)
    context.index = days.index
    days = days.join(context)
    days['session_range'] = (days.session_high-days.session_low)*1e-9
    days['range_atr'] = days.session_range/days.atr14
    days['realized_regime'] = [realized_bin(x) for x in days.range_atr]
    records = []
    masks = window_masks(frame.ts_event,product,frame.bar_position)
    for window, mask in masks.items():
        sub = frame[mask]
        for date, g in sub.groupby('session_date', sort=True):
            r = days.loc[date]
            records.append({'product':product,'timeframe':frame.timeframe.iloc[0],
                'window':window,'session_date':date,
                'crosses':int((g.direction != 0).sum()), 'crosses_up':int((g.direction > 0).sum()),
                'crosses_down':int((g.direction < 0).sum()),'bars':len(g),
                'defined_comparisons':int(g.event_defined.sum()),'observed_hours':len(g)*size/60,
                **{k:r[k] for k in ['session_range','atr_source_day','atr_available_at','atr14',
                                    'atr14_pct','atr_percentile','atr_regime','range_atr','realized_regime']}})
    return pd.DataFrame(records)


def read_audit(root):
    p=root/'data/features/audits/feature_set=session_anchored_vwap/version=1.0.0/product_day_eligibility.parquet'
    return pq.read_table(p).to_pandas()
