#!/usr/bin/env python3
"""Independent verification of saved shared-week draws and representative CIs."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from src.common import dump,utcnow
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out
z=np.load(out/'tables/bootstrap-week-draws.npz');weeks=list(z['weeks']);draws=z['draws'];lookup={w:i for i,w in enumerate(weeks)}
expected=np.random.default_rng(1501).multinomial(len(weeks),np.ones(len(weeks))/len(weeks),size=2000)
assert np.array_equal(expected,draws)
s=pd.read_parquet(out/'tables/summary.parquet');records=[]
for kind in ['departure','touch']:
 f=pd.read_parquet(out/f'evidence/{kind}-horizons.parquet')
 for _,r in s[(s.kind==kind)&(s.scope=='all')&(s.side=='both')&(s.threshold==2)&(s.horizon_bars==10)].iterrows():
  g=f[(f['product']==r['product'])&(f.session==r.session)&(f.horizon_bars==10)&f.eligible]
  if kind=='departure':g=g[g.threshold==2]
  labels=np.array([lookup[w] for w in g.iso_week]);count=np.bincount(labels,minlength=len(weeks))
  for col in ['primary_mae','primary_mfe','directional_delta','directional_positive']+(['evolving_touch','frozen_touch'] if kind=='departure' else []):
   values=g[col].astype(float).to_numpy();sums=np.bincount(labels,weights=values,minlength=len(weeks));den=draws@count
   reps=(draws@sums)[den>0]/den[den>0];low,high=np.quantile(reps,[.025,.975])
   assert np.isclose(low,r[col+'_ci_low'],atol=1e-10) and np.isclose(high,r[col+'_ci_high'],atol=1e-10)
   records.append({'metric_id':r.metric_id,'column':col,'ci_low':low,'ci_high':high,'pass':True})
dump(out/'uncertainty-verification.json',{'status':'pass','verified_at':utcnow(),'shared_week_draws_identical':True,'replicates':2000,'seed':1501,'independent_intervals':len(records),'records':records})
print('Independent interval checks:',len(records),'passed')
