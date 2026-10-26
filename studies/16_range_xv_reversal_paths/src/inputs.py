"""Read pinned bars, preserving all rows and exact prices; never reconvert clocks."""
from __future__ import annotations
from decimal import Decimal
import numpy as np
import pandas as pd
from .common import OWNER,Q,SCALE,roots,load,sha,dump,save_table

def fixed(s):
    n=Decimal(str(s))*SCALE
    if not n.is_finite() or n!=n.to_integral_value(): raise ValueError('Price cannot be represented exactly at 1e-9: '+str(s))
    return int(n)

def verify_pins(out):
    lock=load(OWNER/'inputs.lock.json');paths=roots();rows=[]
    for entry in [lock['manifest'],lock['tracked_manifest_mirror'],*lock['files'],*lock['supporting_artifacts']]:
        base=paths.workspace_root if entry['path'].startswith('docs/') else paths.publication_root
        p=base/entry['path'];actual=sha(p)
        assert actual==entry['sha256'],str(p)
        assert 'bytes' not in entry or p.stat().st_size==entry['bytes'],str(p)
        rows.append({'path':entry['path'],'sha256':actual,'bytes':p.stat().st_size,'status':'pass'})
    save_table(out,'input-identities',rows)
    dump(out/'input-verification.json',{'status':'pass','identities':len(rows),'manifest':lock['manifest']['sha256']})
    return lock

def read_chart(entry,include_repeated=False):
    p=roots().publication_root/entry['path']
    df=pd.read_csv(p,sep=';',dtype=str,keep_default_na=False)
    assert len(df)==entry.get('rows',len(df))
    assert np.array_equal(df.source_row.astype(int),np.arange(1,len(df)+1))
    for n in ['open','high','low','close']: df[n+'_i']=np.array([fixed(v) for v in df[n]],dtype=np.int64)
    o,h,l,c=[df[n+'_i'].to_numpy() for n in ['open','high','low','close']]
    invalid=(l>np.minimum(o,c))|(h<np.maximum(o,c))|(l>h)|(l<=0)
    repeated=df.duplicated(['bar_start_timestamp','open','high','low','close']).to_numpy()
    t=pd.to_datetime(df.bar_start_timestamp).astype('int64').to_numpy()//10**9
    assert np.all(np.diff(t)>=0),'enhanced clock regression'
    day=df.session_date_proxy.to_numpy()
    dur=np.r_[np.diff(t),np.nan].astype(float);same=np.r_[day[:-1]==day[1:],False]
    duration=np.where(same,dur,np.nan)
    supplied=pd.to_numeric(df.bar_duration_seconds_proxy,errors='coerce').to_numpy()
    assert np.allclose(duration,supplied,equal_nan=True)
    status=np.where(~same,np.where(np.arange(len(df))==len(df)-1,'unavailable_export_end','unavailable_session_boundary'),np.where(duration==0,'next_bar_start_same_second','next_bar_start_proxy'))
    assert np.array_equal(status,df.completion_proxy_status.to_numpy())
    completion=np.where(same,np.concatenate([df.bar_start_timestamp.to_numpy()[1:],np.array([''])]),'')
    assert np.array_equal(completion,df.bar_completion_timestamp_proxy.to_numpy())
    q=Q[entry['product']];grid=np.any(np.column_stack([o%q,h%q,l%q,c%q])!=0,axis=1)
    historic_q=np.where((entry['product']=='6S')&(day<'2022-05-02'),100000,q)
    histgrid=np.any(np.column_stack([o%historic_q,h%historic_q,l%historic_q,c%historic_q])!=0,axis=1)
    df['direction']=np.sign(c-o).astype(int);df['timestamp_seconds']=t;df['duration']=duration
    df['repeated']=repeated;df['invalid']=invalid;df['off_grid_constant']=grid;df['off_grid_historical']=histgrid
    df['barrier']=invalid|(repeated & (not include_repeated));df['long_gap']=duration>3600
    df['chart']=entry['product']+'_'+str(entry['setting_ticks']);df['product']=entry['product'];df['q_i']=q
    df['historical_q_i']=historic_q
    source=roots().publication_root/entry['path'].replace('/enhanced/','/source/')
    raw=pd.read_csv(source,sep=';',header=None,dtype=str,keep_default_na=False)
    assert len(raw)==len(df)
    assert np.array_equal(raw.to_numpy(),df[['source_timestamp','open','high','low','close']].to_numpy()),'source-price/order mismatch'
    flagpath=roots().publication_root/entry['path'].replace('/enhanced/','/quality/').replace('.csv','_flags.csv')
    flags=pd.read_csv(flagpath,sep=';')
    for flag,computed in [('repeated_timestamp_ohlc_record',repeated),('zero_range_bar',h==l)]:
        actual=flags.loc[flags.flag==flag,'source_row'].to_numpy()
        assert np.array_equal(actual,np.flatnonzero(computed)+1),flag
    return df

def input_audit(entry,df):
    return {'chart':df.chart.iloc[0],'rows':len(df),'session_dates':df.session_date_proxy.nunique(),
     'invalid':int(df.invalid.sum()),'repeated':int(df.repeated.sum()),'doji':int((df.direction==0).sum()),
     'zero_range':int((df.high_i==df.low_i).sum()),'same_second':int((df.duration==0).sum()),
     'long_gaps_gt_3600':int(df.long_gap.sum()),'off_grid_constant':int(df.off_grid_constant.sum()),
     'off_grid_historical':int(df.off_grid_historical.sum()),'complete_positive':int((df.duration>0).sum()),
     'unavailable':int(df.duration.isna().sum()),'source_sha256':sha(roots().publication_root/entry['path'].replace('/enhanced/','/source/')),
     'enhanced_sha256':sha(roots().publication_root/entry['path'])}
