"""Read-only independent scalar/Wilder and pandas EMA release reconciliation."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from abacus_bhishma.provenance import sha256_file

root=Path.cwd();audit=Path(__file__).parent
manifest=root/'catalog/datasets/same_contract_ema_cloud__1.0.0.json'
m=json.loads(manifest.read_text());results=[]
for record in m['output_files']:
    path=root/record['path']
    if sha256_file(path)!=record['sha256']:raise ValueError('partition byte mismatch')
    bars=pq.ParquetFile(path).read().to_pandas()
    if bars.timestamp.duplicated().any() or not bars.timestamp.is_monotonic_increasing:raise ValueError('slot identity')
    if not (bars.available_at-bars.timestamp).eq(pd.Timedelta(minutes=record['interval_minutes'])).all():raise ValueError('completion time')
    if bars.loc[bars.source_count.eq(0),['open','high','low','close','volume']].notna().any().any():raise ValueError('fabricated empty candle')
    if not bars.loc[bars.usable,'source_count'].eq(record['interval_minutes']).all():raise ValueError('incomplete usable candle')
    summary=dict(product=record['product'],interval=record['interval_minutes'],rows_checked=len(bars),partition_sha256=record['sha256'])
    if record['interval_minutes']==5:
        valid=bars.usable.to_numpy(bool)
        contract=bars.contract.to_numpy()
        starts=[];current=[];segments=[]
        for i in range(len(bars)):
            if not valid[i]:
                if current:segments.append(current);current=[]
                continue
            if current and contract[i]!=contract[current[-1]]:
                segments.append(current);current=[]
            current.append(i)
        if current:segments.append(current)
        max20=max50=maxatr=0.;total=0
        for indexes in segments:
            close=bars.close.to_numpy()[indexes];high=bars.high.to_numpy()[indexes];low=bars.low.to_numpy()[indexes]
            ema20=pd.Series(close).ewm(span=20,adjust=False).mean().to_numpy()
            ema50=pd.Series(close).ewm(span=50,adjust=False).mean().to_numpy()
            tr=[];atr_values=[];prev=None;atr=None
            for j,(c,h,l) in enumerate(zip(close,high,low)):
                value=h-l if prev is None else max(h-l,abs(h-prev),abs(l-prev));tr.append(value)
                if j==13:atr=sum(tr)/14
                elif j>13:atr=(13*atr+value)/14
                atr_values.append(np.nan if atr is None else atr);prev=c
            max20=max(max20,float(np.max(np.abs(ema20-bars.ema20.to_numpy()[indexes]),initial=0.)))
            max50=max(max50,float(np.max(np.abs(ema50-bars.ema50.to_numpy()[indexes]),initial=0.)))
            dif=np.abs(np.asarray(atr_values)-bars.atr14.to_numpy()[indexes]);finite=dif[np.isfinite(dif)]
            maxatr=max(maxatr,float(np.max(finite,initial=0.)))
            if not np.array_equal(bars.consecutive_count.to_numpy()[indexes],np.arange(1,len(indexes)+1)):raise ValueError('segment count mismatch')
            if not np.array_equal(bars.feature_valid.to_numpy()[indexes],np.arange(1,len(indexes)+1)>=250):raise ValueError('readiness mismatch')
            total+=len(indexes)
        if max(max20,max50,maxatr)>1e-9:raise ValueError('independent recurrence error above tolerance')
        if bars.loc[~bars.usable,['ema20','ema50','atr14']].notna().any().any():raise ValueError('invalid feature slot filled')
        summary.update(usable_feature_rows_checked=total,segments_checked=len(segments),max_error_ema20=max20,max_error_ema50=max50,max_error_atr14=maxatr,absolute_tolerance_points=1e-9)
    results.append(summary)
receipt=dict(status='passed',scope='input-only all six immutable partitions and complete same-contract feature recurrences; no event/outcome calculations',
    manifest_sha256=sha256_file(manifest),checker_sha256=sha256_file(Path(__file__)),results=results)
(audit/'independent-feature-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
