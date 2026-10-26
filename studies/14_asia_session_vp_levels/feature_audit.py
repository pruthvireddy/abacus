"""Read-only timing, selection, mass and deterministic pilot audits."""
import argparse
import json
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from abacus_bhishma.provenance import sha256_file as sha256
from src.evidence import MINUTE


def audit(stage,repeat=None):
    report={'status':'pass','study_outcomes_computed':False,'snapshot_rows':0,'candidate_rows':0,'selected_rows':0}
    for p in sorted((stage/'snapshots').rglob('*.parquet')):
        f=pq.ParquetFile(p).read().to_pandas()
        assert (f.available_at<=f.ts_event).all(),'future information cutoff'
        mask=f.rebuild_at.notna()
        assert (f.loc[mask,'rebuild_at']<=f.loc[mask,'ts_event']).all(),'future rebuild'
        first=f.groupby('session_date',sort=False).head(1)
        assert first.rebuild_at.isna().all(),'new session inherited old candidates'
        assert (np.round(f.open*4)==f.open*4).all(),'price conversion off grid'
        for row in f.itertuples():
            for name,refs,price in [('selected',row.references,row.previous_close),('adj_selected',row.adj_references,row.previous_close)]:
                selected=getattr(row,name)
                for n in selected:
                    assert n['available_at']<=row.ts_event
                    assert n['lo']>price or n['hi']<price
                    assert not any(n['lo']-2<=x<=n['hi']+2 for x in refs if np.isfinite(x))
                for side in (-1,1):assert sum(n['side']==side for n in selected)<=2
                for k,n in enumerate(selected):
                    for m in selected[k+1:]:assert not (n['lo']<=m['hi']+2 and n['hi']>=m['lo']-2)
        report['snapshot_rows']+=len(f);report['selected_rows']+=int(f.selected.map(len).gt(0).sum())
    for p in sorted((stage/'candidates').rglob('*.parquet')):
        c=pq.ParquetFile(p).read().to_pandas()
        assert np.allclose(c.mass,c.input_volume,rtol=1e-10,atol=1e-6),'volume mass'
        assert (c.hi-c.lo<=2+1e-10).all(),'zone width'
        assert (c.profile_rows<=3000).all(),'row cap'
        rebuilt=c[['session_date','coordinate','available_at']].drop_duplicates()
        for _,g in rebuilt.groupby(['session_date','coordinate'],sort=False):
            delta=np.diff(g.available_at.to_numpy())
            assert (delta>=15*MINUTE).all(),'candidate rebuilt too early'
        report['candidate_rows']+=len(c)
    if repeat:
        files=sorted(stage.rglob('*.parquet'))
        assert len(files)==len(list(repeat.rglob('*.parquet')))
        for p in files:assert sha256(p)==sha256(repeat/p.relative_to(stage)),f'non-deterministic: {p}'
        report['deterministic_partition_checks']=len(files)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',type=Path,required=True)
    parser.add_argument('--repeat',type=Path);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();result=audit(a.stage,a.repeat)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(result)
