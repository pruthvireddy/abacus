"""Study-local identities, exact units, and portable evidence utilities."""
from __future__ import annotations
import hashlib, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from abacus_bhishma.paths import load_workspace_paths

STUDY = '16_range_xv_reversal_paths'
OWNER = Path(__file__).resolve().parents[1]
SCALE = 10**9
Q = {'6E':50000, '6B':100000, '6J':500, '6S':50000}
HORIZONS = [1,2,3,5,10]
LBINS = [str(i) for i in range(1,11)] + ['11-15','16+']
WINDOWS = ['asia','london_pre_ny','ny_morning','ny_afternoon','transition']
SEED = 161001

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()
def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean(v) for v in x]
    if isinstance(x,np.ndarray): return clean(x.tolist())
    if isinstance(x,np.generic): return clean(x.item())
    if isinstance(x,float) and not np.isfinite(x): return None
    return x
def dump(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(clean(x),indent=2,sort_keys=True,allow_nan=False)+'\n')
def load(p): return json.loads(Path(p).read_text())
def roots(): return load_workspace_paths(OWNER.parents[1])
def save_table(out,name,rows):
    df=rows if isinstance(rows,pd.DataFrame) else pd.DataFrame(rows)
    p=Path(out)/'tables'/f'{name}.csv';p.parent.mkdir(exist_ok=True,parents=True)
    df.to_csv(p,index=False,float_format='%.12g');return df
def lbin(n): return str(n) if n<=10 else ('11-15' if n<=15 else '16+')
def compact(n): return str(n) if n<=4 else ('5-7' if n<=7 else '8-10' if n<=10 else '11-15' if n<=15 else '16+')
def window(t):
    m=(int(t[11:13])*60+int(t[14:16]))
    return 'asia' if m>=1080 or m<180 else ('london_pre_ny' if m<570 else 'ny_morning' if m<720 else 'ny_afternoon' if m<960 else 'transition')
def split(date): return 'development' if date<'2020-01-01' else ('validation' if date<'2023-01-01' else 'later')
def command(out,stage,args):
    p=Path(out)/'commands.json';x=load(p) if p.exists() else []
    x.append({'stage':stage,'utc':now(),'argv':args,'cwd':str(roots().workspace_root),
              'environment':{k:os.environ.get(k) for k in ['UV_CACHE_DIR','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','OMP_NUM_THREADS']}})
    dump(p,x)

NUMERIC_B1=['R_body_q','R_span_q','R_body_fraction','R_upper_wick_fraction','R_lower_wick_fraction',
 'R_close_location','R_opposing_q','R_gap_q','R_duration_seconds']
NUMERIC_M1=NUMERIC_B1+['log_L']
RICH=['prior_distance_q','prior_body_total_q','prior_span_q','prior_duration_seconds','prior_seconds_per_bar',
 'prior_bars_per_minute','prior_distance_per_minute_q','prior_efficiency','prior_mean_body_q','prior_median_body_q',
 'prior_mean_span_q','prior_median_span_q','prior_median_body_fraction','prior_direction_wick_fraction',
 'prior_counter_wick_fraction','prior_overlap','previous_leg_1','previous_leg_2','previous_leg_3',
 'recent20_tr_q','recent20_efficiency','chop10','chop20','R_body_prior_span','R_opposing_prior_span',
 'R_span_recent20_tr','interaction_pace','interaction_efficiency','interaction_chop','interaction_R_relative']
FEATURES=NUMERIC_M1+RICH

def dictionary():
    descriptions={
      'L':'Known maximal adjacent non-doji leg length; R excluded; segment-start legs undefined.',
      'log_L':'log1p(L).', 'prior_distance_q':'prior direction * (last close - first open) / q.',
      'prior_body_total_q':'sum(abs(close-open)) / q.', 'prior_span_q':'(max(high)-min(low))/q.',
      'prior_duration_seconds':'R start minus first prior-leg start.',
      'prior_seconds_per_bar':'prior duration / L.', 'prior_bars_per_minute':'60*L/prior duration.',
      'prior_distance_per_minute_q':'60*prior_distance_q/prior duration.',
      'prior_efficiency':'abs(last close-first open)/(abs(first close-first open)+sum(abs(adjacent closes))).',
      'prior_mean_body_q':'mean absolute bodies/q.', 'prior_median_body_q':'median absolute bodies/q.',
      'prior_mean_span_q':'mean high-low/q.', 'prior_median_span_q':'median high-low/q.',
      'prior_median_body_fraction':'median(abs(body)/span); zero spans undefined.',
      'prior_direction_wick_fraction':'mean upper wick/span for bullish prior leg, lower for bearish.',
      'prior_counter_wick_fraction':'mean lower wick/span for bullish prior leg, upper for bearish.',
      'prior_overlap':'mean intersection/min(span) across adjacent prior bars; L=1 undefined.',
      'recent20_tr_q':'median max(span,abs(high-prevC),abs(low-prevC)) on prior 20 bars/q; 21 bars required.',
      'recent20_efficiency':'abs(last prior close-first of 20 open)/(abs(first body)+sum(abs(adjacent closes))).',
      'chop10':'switches/non-doji adjacent pairs in prior 10 physical bars.',
      'chop20':'switches/non-doji adjacent pairs in prior 20 physical bars.',
      'R_body_q':'abs(R close-open)/q.', 'R_span_q':'(R high-low)/q.',
      'R_body_fraction':'abs(R body)/R span.', 'R_upper_wick_fraction':'(high-max(open,close))/span.',
      'R_lower_wick_fraction':'(min(open,close)-low)/span.',
      'R_close_location':'(close-low)/span bullish; (high-close)/span bearish.',
      'R_opposing_q':'R direction*(R close-previous close)/q.', 'R_gap_q':'(R open-previous close)/q signed raw gap.',
      'R_duration_seconds':'B1 start-R start; zero duration retained with undefined pace flag.',
      'R_body_prior_span':'R absolute body/prior span.', 'R_opposing_prior_span':'R direction*(R close-previous close)/prior span.',
      'R_span_recent20_tr':'R span/prior20 median true range.',
    }
    for i in range(1,4): descriptions[f'previous_leg_{i}']='Length of '+str(i)+'th completed known non-doji leg before immediate prior leg; missing across barriers/unknown starts.'
    for n,b in [('pace','prior_bars_per_minute'),('efficiency','prior_efficiency'),('chop','chop20'),('R_relative','R_body_prior_span')]:
        descriptions['interaction_'+n]='log1p(L)*'+b+'; either undefined => undefined.'
    return {'version':'2.0.0','availability':'R and earlier only, available_at=B1 start; max_feature_source_row=R row',
      'fixed_point_scale':SCALE,'prices':'all classifications, differences and grids exact int64 at 1e-9; ratios converted only after exact arithmetic',
      'missing':'NaN/nullable values, plus explicit undefined_<name> flags; no zero imputation in evidence',
      'features':descriptions,'categorical':['decision_window','6S_era','compact_L_bin'],
      'model_B1':NUMERIC_B1,'model_M1':NUMERIC_M1,'model_M2':FEATURES,
      'quartile_features':['prior_bars_per_minute','prior_efficiency','chop20','R_body_prior_span','prior_overlap','R_body_fraction']}
