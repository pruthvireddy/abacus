"""Descriptive distributions and shared-ISO-week cluster uncertainty."""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .common import save_table, dump, HORIZONS, THRESHOLDS, PRODUCTS, SESSIONS

CLASSES=('bounce','through','neither','ambiguous')
NUMERIC=('primary_mae','primary_mfe','opposite_mae','opposite_mfe','directional_delta','price_delta','opposite_directional_delta',
         'close_minus_signal_close','entry_gap','entry_open','terminal_close')
PROBABILITY=('above_entry','below_entry','entry_tie','directional_positive','directional_negative',
             'final_candle_up','final_candle_down','final_candle_tie')

class Bootstrap:
    def __init__(self,weeks,replicates=2000,seed=1501):
        self.weeks=sorted(set(weeks));self.index={w:i for i,w in enumerate(self.weeks)}
        self.draws=np.random.default_rng(seed).multinomial(len(self.weeks),np.ones(len(self.weeks))/len(self.weeks),size=replicates)
    def interval(self,frame,cols):
        # Rows remain events, weights are whole weeks shared across every invocation.
        labels=np.array([self.index[w] for w in frame.iso_week],dtype=int)
        unique,inverse=np.unique(labels,return_inverse=True)
        values=frame[cols].astype(float).to_numpy();ok=np.isfinite(values)
        sums=np.zeros((len(unique),len(cols)));counts=np.zeros_like(sums)
        np.add.at(sums,inverse,np.where(ok,values,0));np.add.at(counts,inverse,ok)
        weights=self.draws[:,unique].astype(float)
        num=weights@sums;den=weights@counts
        estimates=np.divide(num,den,out=np.full(num.shape,np.nan),where=den>0)
        bounds=[]
        for j in range(len(cols)):
            finite=estimates[:,j][np.isfinite(estimates[:,j])]
            bounds.append((np.quantile(finite,.025),np.quantile(finite,.975),len(finite)) if len(finite) else (None,None,0))
        return bounds


def slices(frame):
    yield 'all',frame
    yield 'common_50',frame[frame.common_50]
    yield 'age_ge30',frame[frame['departure_anchor_age_minutes' if frame.kind.iloc[0]=='touch' else 'anchor_age_minutes']>=30]
    for y,g in frame.groupby('year',sort=True):yield f'year_{y}',g
    for name,mask in [('through_2023',frame.year<=2023),('year_2024_period',frame.year==2024),('years_2025_2026',frame.year>=2025)]:
        yield name,frame[mask]
    # Marginal primary-threshold context summaries, never a Cartesian filter search.
    primary=frame[frame.threshold==2]
    for col in ['anchor_age_bin','local_hour']+(['latency_bin'] if frame.kind.iloc[0]=='touch' else []):
        for value,g in primary.groupby(col,sort=True):yield f'{col}_{value}',g


def prepare(frame,kind):
    f=frame.copy()
    if kind=='touch':
        # The touch event is unique. Nested cohorts repeat its FK, not its measurement.
        f=pd.concat([f[f.threshold>=k].assign(threshold=k) for k in THRESHOLDS],ignore_index=True)
        for c in CLASSES:f['first_'+c]=np.where(f.first_move=='unavailable',np.nan,(f.first_move==c).astype(float))
        f['barrier_gap']=f.barrier_gap.where(f.eligible).astype(float)
    else:
        for c in ['evolving_touch','frozen_touch','evolving_only','frozen_only']:
            f[c]=pd.to_numeric(f[c],errors='coerce')
        f['evolving_minus_frozen']=f.evolving_touch-f.frozen_touch
        f['any_gap']=(f.gap_count>0).where(f.eligible).astype(float)
        f['any_reference_overtake']=(f.reference_overtake_count>0).where(f.eligible).astype(float)
    return f


def summarize_cell(g,meta,boot):
    good=g[g.eligible].copy();n=len(good)
    record={**meta,'candidate_events':len(g),'n':n,'unavailable':len(g)-n,
       'parents':good.parent_id.nunique(),'days':good.session_date.nunique(),'weeks':good.iso_week.nunique()}
    record['support_flag']=';'.join(k for k,v in [('events_below_100',n<100),('days_below_30',record['days']<30),('weeks_below_20',record['weeks']<20)] if v)
    for why in ['session_boundary','missing_or_invalid_minute','invalid_feature_or_source_bar','contract_or_adjustment_break','invalid_reference']:
        record['excluded_'+why]=int((g.exclusion_reason==why).sum())
    if not n:return record
    kind=meta['kind']
    probs=list(PROBABILITY)+(['evolving_touch','frozen_touch','evolving_only','frozen_only','any_gap','any_reference_overtake'] if kind=='departure' else ['first_'+c for c in CLASSES]+['barrier_gap'])
    means=list(NUMERIC)+(['evolving_minus_frozen'] if kind=='departure' else [])
    columns=means+probs
    for col in columns:
        vals=good[col].dropna().astype(float)
        record[col+'_mean']=float(vals.mean()) if len(vals) else None
        record[col+'_denominator']=len(vals)
        if col in probs:
            record[col+'_count']=int(vals.sum()) if len(vals) else 0
            record[col+'_boundary_uncertainty_unresolved']=bool(len(vals) and (vals.sum()==0 or vals.sum()==len(vals)))
    bounds=boot.interval(good,columns)
    for col,(lo,hi,reps) in zip(columns,bounds):
        record[col+'_ci_low']=lo;record[col+'_ci_high']=hi;record[col+'_bootstrap_nonempty_replicates']=reps
    for col in NUMERIC[:-2]:
        units=['','_ticks','_sigma']
        for unit in units:
            name=col+unit;vals=good[name].dropna().astype(float)
            record[name+'_mean']=float(vals.mean()) if len(vals) else None
            for q in ([.05,.25,.5,.75,.95] if 'delta' in col or 'gap' in col or 'close_minus' in col else [.25,.5,.75,.9,.95]):
                record[f'{name}_p{int(q*100):02d}']=float(vals.quantile(q)) if len(vals) else None
    # Point-to-tick is constant within each product. Signal-sigma is event-specific.
    sigma_cols=[x+'_sigma' for x in ['primary_mae','primary_mfe','directional_delta']]
    for col,b in zip(sigma_cols,boot.interval(good,sigma_cols)):
        record[col+'_ci_low'],record[col+'_ci_high'],record[col+'_bootstrap_nonempty_replicates']=b
    for col in ['primary_mae','primary_mfe','opposite_mae','opposite_mfe','directional_delta','price_delta']:
        for bound in ['low','high']:record[col+'_ticks_ci_'+bound]=record[col+'_ci_'+bound]/good.min_tick.iloc[0]
    if kind=='departure':
        for ref in ['evolving','frozen']:
            touched=good[good[ref+'_touch']==1]
            record[ref+'_no_touch']=n-len(touched)
            for unit in ['minutes','bars']:
                for q in [.5,.75,.9,.95]:record[f'{ref}_latency_{unit}_p{int(100*q):02d}']=float(touched[f'{ref}_latency_{unit}'].quantile(q)) if len(touched) else None
        record['observed_touch_on_unavailable']=int(g.loc[~g.eligible,'observed_evolving_touch_open'].notna().sum())
        record['gap_count']=int(good.gap_count.sum());record['reference_overtake_count']=int(good.reference_overtake_count.sum())
    else:record['barrier_unavailable']=int((good.first_move=='unavailable').sum())
    return record


def summarize(out,weeks):
    out=Path(out);boot=Bootstrap(weeks)
    np.savez_compressed(out/'tables/bootstrap-week-draws.npz',weeks=np.array(boot.weeks),draws=boot.draws)
    records=[]
    for kind in ['departure','touch']:
        raw=pd.read_parquet(out/f'evidence/{kind}-horizons.parquet');frame=prepare(raw,kind)
        for scope,selection in slices(frame):
            # Include explicit empty product/side/threshold/horizon cells for main scopes.
            side_values=['upper','lower','both'] if scope in ['all','common_50','age_ge30'] else ['both']
            for side in side_values:
                chosen=selection if side=='both' else selection[selection.side==side]
                groups={(p,s,k,h):g for (p,s,k,h),g in chosen.groupby(['product','session','threshold','horizon_bars'],observed=True)}
                keys=[(p,s,k,h) for p in PRODUCTS for s in SESSIONS for k in THRESHOLDS for h in HORIZONS] if scope in ['all','common_50','age_ge30'] else sorted(groups)
                for key in keys:
                    p,s,k,h=key;g=groups.get(key,chosen.iloc[:0])
                    ident=f'{kind}|{scope}|{p}|{s}|{side}|{k:g}|{h}'
                    meta={'metric_id':ident,'kind':kind,'scope':scope,'product':p,'session':s,'side':side,'threshold':k,'horizon_bars':h}
                    records.append(summarize_cell(g,meta,boot))
            print(f'summary {kind} {scope}: {len(records)} cells',flush=True)
    summary=save_table(out/'tables/summary',records)
    # Coverage preserves candidate/exclusion counts and the requested independent support units.
    coverage=summary[['metric_id','kind','scope','product','session','side','threshold','horizon_bars','candidate_events','n','unavailable','parents','days','weeks','support_flag']+[c for c in summary if c.startswith('excluded_')]]
    save_table(out/'tables/coverage',coverage)
    dump(out/'metrics.json',{'schema_version':'1.0.0','evidence_table':'tables/summary.parquet',
       'metric_id_column':'metric_id','rows':len(summary),'primary_threshold_sigma':2,
       'uncertainty':{'method':'shared ISO-week cluster percentile bootstrap','replicates':2000,'seed':1501,'confidence':.95,
        'week_universe':'all feature-eligible session-date ISO weeks across products','weeks':len(boot.weeks),
        'paired_contrast':'evolving_minus_frozen is the paired probability difference with identical week draws'},
       'unit_convention':'unsuffixed prices: points; _ticks: product minimum ticks; _sigma: event signal or touch-close sigma',
       'cohorts':'touch thresholds are nested reached-before-touch cohorts; departure thresholds have different clocks',
       'no_eligible_cases':'unavailable (null); zero successes with n>0 are 0/n',
       'boundary_uncertainty':'zero/all-success bootstrap intervals flagged unresolved',
       'history_status':'previously inspected exploratory history; not holdout',
       'profitability_tested':False})
    return summary
