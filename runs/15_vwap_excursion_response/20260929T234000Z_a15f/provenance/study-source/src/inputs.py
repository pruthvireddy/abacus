"""Pinned, read-only public-loader access and full feature-only coverage pilot."""
from __future__ import annotations
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from abacus_bhishma.paths import load_workspace_paths
from abacus_bhishma.feature_loader import load_session_anchored_vwap
from abacus_bhishma.continuous_loader import open_continuous_dataset
from .common import OWNER, PRODUCTS, SESSIONS, THRESHOLDS, sha, dump, save_table, utcnow, window

FEATURE_COLUMNS = ['ts_event','bar_close_ts','available_at','session_date','product',
 'instrument_id','raw_symbol','open','high','low','close','volume','price_adjustment',
 'min_tick','source_bar_count','contains_roll','roll_id'] + [f'{s}_{c}' for s in SESSIONS for c in
 ['anchor_ts','vwap','sigma','cumulative_volume','minutes_since_anchor']]
RAW_COLUMNS = ['ts_event','session_date','product','instrument_id','raw_symbol',
               'open','high','low','close','volume','roll_id']

def roots(): return load_workspace_paths()

def verify_inputs(out):
    root = roots().publication_root
    lock = json.loads((OWNER/'inputs.lock.json').read_text())
    records = [lock['release_manifest'], lock['audit']] + lock['related_manifests'] + [
        {'path':d['manifest_path'],'sha256':d['manifest_sha256']} for d in lock['datasets']]
    for m in ('session_anchored_vwap_2m_v1', 'volume_lead_unadjusted_v1'):
        manifest = json.loads((root/f'catalog/datasets/{m}.json').read_text())
        records += [r for r in manifest['output_files'] if '/part-' in r['path']]
    checked=[]
    for r in records:
        actual = sha(root/r['path'])
        checked.append({'path':r['path'],'expected_sha256':r['sha256'],'sha256':actual,
                        'bytes':(root/r['path']).stat().st_size,'pass':actual==r['sha256']})
        if actual != r['sha256']: raise ValueError(f'Input hash mismatch: {r["path"]}')
    dump(Path(out)/'input-checks.json', {'checked_at':utcnow(),'publication_root':str(root),
         'all_pass':True,'records':checked,'scope':'All feature 2m partitions and all raw 1m partitions, plus every input-lock pin.'})
    return checked

def feature_parts():
    root=roots().publication_root
    m=json.loads((root/'catalog/datasets/session_anchored_vwap_2m_v1.json').read_text())
    return sorted((re.search(r'product=(\w+)',r['path'])[1], int(re.search(r'year=(\d+)',r['path'])[1]))
                  for r in m['output_files'] if '/part-' in r['path'])

def load_year(product, year):
    root=roots().publication_root
    f=load_session_anchored_vwap(root, product,'2m',version='1.0.0',
       start_date=f'{year}-01-01',end_date=f'{year+1}-01-01',columns=FEATURE_COLUMNS).to_pandas()
    expr=(ds.field('session_date')>=pa.scalar(pd.Timestamp(f'{year}-01-01').date())) & (ds.field('session_date')<pa.scalar(pd.Timestamp(f'{year+1}-01-01').date()))
    raw=open_continuous_dataset(root,product,variant='unadjusted').to_table(columns=RAW_COLUMNS,filter=expr).to_pandas()
    f=f.sort_values('ts_event').reset_index(drop=True)
    raw=raw[raw.session_date.isin(f.session_date.unique())].sort_values('ts_event').reset_index(drop=True)
    return f, raw

def audit_coverage(out):
    root=roots().publication_root
    a=pq.read_table(root/json.loads((OWNER/'inputs.lock.json').read_text())['audit']['path']).to_pandas()
    rows=[]
    for (p,y),g in a.groupby(['product','session_year']):
        base={'product':p,'year':int(y),'candidate_days':len(g),'eligible_days':int(g.eligible.sum()),'excluded_days':int((~g.eligible).sum())}
        for reason in sorted({r for rs in g.exclusion_reasons for r in rs}):
            base[reason]=sum(reason in rs for rs in g.exclusion_reasons)
        rows.append(base)
    save_table(Path(out)/'tables/release-coverage',pd.DataFrame(rows).fillna(0))

def pilot(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    verify_inputs(out);audit_coverage(out)
    rows=[];total=0
    for product,year in feature_parts():
        f,r=load_year(product,year)
        assert not f.ts_event.duplicated().any() and not r.ts_event.duplicated().any()
        assert ((f.available_at==f.bar_close_ts)&(f.bar_close_ts-f.ts_event==pd.Timedelta(minutes=2))).all()
        ix=r.set_index('ts_event')
        first=ix.reindex(f.ts_event);second=ix.reindex(f.ts_event+pd.Timedelta(minutes=1))
        assert first.open.notna().all() and second.open.notna().all()
        adj=f.price_adjustment.to_numpy()
        for name,expected in [('open',first.open.to_numpy()),('close',second.close.to_numpy()),
            ('high',np.maximum(first.high.to_numpy(),second.high.to_numpy())),
            ('low',np.minimum(first.low.to_numpy(),second.low.to_numpy()))]:
            assert np.array_equal(f[name].to_numpy()-adj,expected), (product,year,name)
        for col in ['product','instrument_id','raw_symbol','session_date','roll_id']:
            assert np.array_equal(f[col].to_numpy(),first[col].to_numpy())
            assert np.array_equal(f[col].to_numpy(),second[col].to_numpy())
        assert (f.volume.to_numpy()==first.volume.to_numpy()+second.volume.to_numpy()).all()
        assert (f.source_bar_count==2).all() and (f.min_tick>0).all()
        for day,g in f.groupby('session_date',sort=True):
            assert g.price_adjustment.nunique()==g.raw_symbol.nunique()==g.instrument_id.nunique()==g.min_tick.nunique()==1
            for s in SESSIONS:
                start,end=window(day,s);v=g[(g.ts_event>=start)&(g.bar_close_ts<=end)]
                sigma=v[f'{s}_sigma'].to_numpy();vv=v[f'{s}_vwap'].to_numpy()
                valid=np.isfinite(vv)&np.isfinite(sigma)&(sigma>0)&(v[f'{s}_cumulative_volume'].to_numpy()>0)
                z=np.divide(v.close.to_numpy()*1e-9-vv,sigma,out=np.full(len(v),np.nan),where=sigma>0)
                pair=valid[1:]&valid[:-1]
                row={'product':product,'year':year,'session':s,'session_date':str(day),
                     'bars':len(v),'valid_positive_sigma_bars':int(valid.sum()),
                     'zero_or_invalid_sigma_bars':int((~valid).sum()),'first_bar':str(v.ts_event.min()),
                     'last_close':str(v.bar_close_ts.max()),'min_tick_points':float(v.min_tick.iloc[0]*1e-9)}
                assert (v[f'{s}_anchor_ts']==start).all()
                assert len(v)==int((end-start)/pd.Timedelta(minutes=2))
                for k in THRESHOLDS:
                    row[f'fresh_{k:g}_cross_candidates']=int(np.sum(pair&(((z[1:]>k)&(z[:-1]<=k))|((z[1:]<-k)&(z[:-1]>=-k)))))
                rows.append(row)
        total+=len(f);print(f'pilot {product} {year}: {len(f)} feature bars, joins/units/availability pass',flush=True)
    save_table(out/'tables/feature-pilot',rows)
    dump(out/'pilot.json',{'status':'pass','finished_at':utcnow(),'feature_bars':total,
       'product_session_windows':len(rows),'future_outcomes_computed':False,
       'checks':['all consumed partition hashes','availability equals exclusive 2m close',
       'all 2m raw OHLCV aggregates exactly match after integer adjustment subtraction',
       'product/date/symbol/instrument/roll joins','one contract/adjustment/tick per day',
       'all four windows complete and correctly anchored','positive-sigma and fresh-cross candidate coverage'],
       'environment_note':'Existing workspace .venv via uv --locked --no-sync; automatic sync attempted a network build, so existing installed dependencies are used and captured.'})
