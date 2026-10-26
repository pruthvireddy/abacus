"""Read-only independent reduceat aggregation; original delivery stays immutable."""
from datetime import datetime,timezone
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq
from abacus_bhishma.continuous_loader import open_continuous_dataset
from abacus_bhishma.provenance import sha256_file

root=Path.cwd();audit=Path(__file__).parent
manifest=root/'catalog/datasets/same_contract_ema_cloud__1.0.0.json';m=json.loads(manifest.read_text())
base=root/'catalog/datasets/volume_lead_unadjusted_v1.json'
master=pq.ParquetFile(root/'data/curated/instruments/roll=volume_lead_v1/instrument_master.parquet').read().to_pandas()
results=[]
for product in ('ES','GC','NQ'):
    dataset=open_continuous_dataset(root,product,manifest_path=base,expected_manifest_sha256=sha256_file(base),verify_selected_files=True)
    src=dataset.to_table(filter=(pc.field('year')>=2017)&(pc.field('year')<=2020)).to_pandas().sort_values('ts_event').reset_index(drop=True)
    null_identity=src[['product','instrument_id','raw_symbol','roll_id','mapping_start','mapping_end']].isna().any(axis=1)
    null_identity|=src.raw_symbol.astype('string').str.strip().eq('').fillna(True)
    if null_identity.any():raise ValueError('primary source null identity')
    binding={int(r.roll_id):f'{product}:{int(r.instrument_id)}:{int(r.maturity_year)}:{int(r.maturity_month)}:{r.raw_symbol}'
             for r in master[master['product']==product].itertuples(index=False)}
    for interval in (3,5):
        record=next(r for r in m['output_files'] if r['product']==product and r['interval_minutes']==interval)
        path=root/record['path']
        if sha256_file(path)!=record['sha256']:raise ValueError('immutable partition changed')
        bars=pq.ParquetFile(path).read().to_pandas()
        good=bars.usable
        missing_contract=int(bars.loc[good,'contract'].isna().sum())
        if missing_contract or not bars.loc[good,'contract_count'].eq(1).all():raise ValueError('delivered usable contract missing/mixed')
        ns=src.ts_event.array.asi8
        bucket=ns//(interval*60_000_000_000)*(interval*60_000_000_000)
        include=np.isin(bucket,bars.timestamp.array.asi8)
        selected=src.loc[include];bucket=bucket[include]
        starts=np.r_[0,np.flatnonzero(np.diff(bucket)!=0)+1]
        ends=np.r_[starts[1:],len(bucket)]
        index=pd.to_datetime(bucket[starts],utc=True)
        actual=bars.set_index('timestamp').loc[index]
        mismatches={}
        values={'open':selected.open.to_numpy()[starts],
                'high':np.maximum.reduceat(selected.high.to_numpy(),starts),
                'low':np.minimum.reduceat(selected.low.to_numpy(),starts),
                'close':selected.close.to_numpy()[ends-1],
                'volume':np.add.reduceat(selected.volume.to_numpy(),starts),
                'source_count':ends-starts}
        for name,expected in values.items():
            observed=actual[name].to_numpy()
            if name in ('open','high','low','close'):expected=expected.astype(np.float64)*1e-9
            mismatches[name]=int((observed!=expected).sum())
        raw_ids=selected.instrument_id.to_numpy();same=np.minimum.reduceat(raw_ids,starts)==np.maximum.reduceat(raw_ids,starts)
        if not same.all():raise ValueError('actual primary mixed contract requires separate explanation')
        expected_contract=np.array([binding[int(roll)] for roll in selected.roll_id.to_numpy()[starts]],object)
        nonnull=actual.contract.notna().to_numpy()
        mismatches['contract']=int((actual.contract.to_numpy()[nonnull]!=expected_contract[nonnull]).sum())
        if any(mismatches.values()):raise ValueError(f'independent {product}/{interval} mismatch {mismatches}')
        results.append(dict(product=product,interval_minutes=interval,all_scheduled_rows=len(bars),
            nonempty_buckets_checked=len(actual),usable_contract_rows_checked=int(good.sum()),
            primary_source_rows=len(src),source_identity_null_rows=int(null_identity.sum()),
            usable_contract_null_rows=missing_contract,mismatch_counts=mismatches,partition_sha256=record['sha256']))
receipt=dict(status='passed',scope='independent NumPy reduceat 1m→3m/5m integer/float OHLCV, count, lineage and null-identity reconciliation; all nonempty expected slots; no signal/outcome calculations',
    created_at=datetime.now(timezone.utc).isoformat(),manifest_sha256=sha256_file(manifest),source_manifest_sha256=sha256_file(base),checker_sha256=sha256_file(Path(__file__)),results=results)
(audit/'independent-bar-aggregation-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
old=root/'data/features/ema_cloud/version=1.0.0/provenance/ema_cloud.py'
new=root/'packages/bhishma/src/abacus_bhishma/ema_cloud.py'
correction=dict(status='passed',reason='Reusable null/empty constituent contract identity guard added after release; actual published input identity never null and all delivered usable contracts defined. Original release and original producer snapshot preserved.',
    old_producer={'path':old.relative_to(root).as_posix(),'sha256':sha256_file(old)},
    corrected_canonical={'path':new.relative_to(root).as_posix(),'sha256':sha256_file(new)},
    immutable_delivery={'path':manifest.relative_to(root).as_posix(),'sha256':sha256_file(manifest)},
    impact='No rebuilt or replaced release. Canonical guard changes generic synthetic missing-identity behavior; the recorded actual source and usable delivery rows are unaffected.',
    actual_delivery_proof={'path':(audit/'independent-bar-aggregation-verification.json').relative_to(root).as_posix(),'sha256':sha256_file(audit/'independent-bar-aggregation-verification.json')},
    corrected_fixture_result=json.loads((audit/'numerical-tests-corrected.json').read_text()))
(audit/'source-correction.json').write_text(json.dumps(correction,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
