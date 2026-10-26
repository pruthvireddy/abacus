"""Independent raw-source recount and saved-evidence reconciliation.

Does not import the causal/path engine or statistical summarizer.
"""
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from .common import PRODUCTS, SESSIONS, HORIZONS, save_table, dump, sha, utcnow
from .inputs import load_year


def choose_examples(departures,touches):
    selected=[]
    for product in PRODUCTS:
        for session in SESSIONS:
            a=departures[(departures['product']==product)&(departures.session==session)]
            b=touches[(touches['product']==product)&(touches.session==session)]
            populations={
              'return':a[a.eligible&(a.horizon_bars==10)&(a.evolving_touch==True)],
              'non_return':a[a.eligible&(a.horizon_bars==10)&(a.evolving_touch==False)],
              'bounce':b[b.eligible&(b.horizon_bars==10)&(b.first_move=='bounce')],
              'through':b[b.eligible&(b.horizon_bars==10)&(b.first_move=='through')],
              'ambiguity':b[b.eligible&(b.horizon_bars==10)&(b.first_move=='ambiguous')],
              'exclusion':a[~a.eligible]}
            for category,g in populations.items():
                if len(g):
                    r=g.sort_values('horizon_id').iloc[0].to_dict();r['example_class']=category;selected.append(r)
                else:selected.append({'product':product,'session':session,'example_class':category,'horizon_id':None})
    return pd.DataFrame(selected)


def independent_path(row,f,raw):
    start=pd.Timestamp(row.entry_time);deadline=pd.Timestamp(row.deadline);boundary=pd.Timestamp(row.session_end)
    path=raw[(raw.ts_event>=start)&(raw.ts_event<min(deadline,boundary))].sort_values('ts_event').copy()
    refs=f[f.session_date.astype(str)==str(row.session_date)].sort_values('available_at').copy()
    name=row.session;tick=float(row.min_tick);tick_fixed=int(round(tick*1e9))
    refs['reference']=(refs[f'{name}_vwap']-refs.price_adjustment*1e-9)
    ref_times=refs.available_at.astype('int64').to_numpy()
    centers=[];sigmas=[];ref_ats=[];unrounded=[]
    for ts in path.ts_event:
        ix=np.searchsorted(ref_times,ts.value,side='right')-1
        if ix<0:centers.append(np.nan);sigmas.append(np.nan);ref_ats.append(None);unrounded.append(np.nan);continue
        v=float(refs.reference.iloc[ix])/tick;unrounded.append(float(refs.reference.iloc[ix]))
        centers.append(int(Decimal(str(v)).quantize(Decimal('1'),rounding=ROUND_HALF_UP)))
        sigmas.append(float(refs[f'{name}_sigma'].iloc[ix]));ref_ats.append(str(refs.available_at.iloc[ix]))
    for col in ['open','high','low','close']:path[col+'_ticks']=path[col]/tick_fixed
    path['evolving_vwap_points']=unrounded
    for k in [2,2.5,3]:
        path[f'known_upper_{k:g}sigma']=np.array(unrounded)+k*np.array(sigmas)
        path[f'known_lower_{k:g}sigma']=np.array(unrounded)-k*np.array(sigmas)
    path['evolving_center_ticks']=centers;path['reference_available_at']=ref_ats;path['sigma_known_points']=sigmas
    path['frozen_center_ticks']=int(Decimal(str(float(row.vwap_signal)/tick)).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    return path


def recount(row,f,raw):
    p=independent_path(row,f,raw);checks=[]
    if row.eligible:
        assert len(p)==2*row.horizon_bars
        assert (p.ts_event.diff().dropna()==pd.Timedelta(minutes=1)).all()
        assert p.raw_symbol.nunique()==1 and str(p.raw_symbol.iloc[0])==row.raw_symbol
        e=p.open_ticks.iloc[0];hi=p.high_ticks.max();lo=p.low_ticks.min();c=p.close_ticks.iloc[-1];tick=row.min_tick
        expected={'entry_open':e*tick,'terminal_close':c*tick,'terminal_candle_open':p.open_ticks.iloc[-2]*tick,
          'long_mfe':max(0,hi-e)*tick,'long_mae':max(0,e-lo)*tick,'price_delta':(c-e)*tick,
          'above_entry':c>e,'entry_tie':c==e,'final_candle_up':c>p.open_ticks.iloc[-2]}
        for key,value in expected.items():assert np.isclose(row[key],value,rtol=1e-11,atol=1e-9),(row.horizon_id,key,row[key],value)
        checks+=list(expected)
        if row.kind=='departure':
            for ref in ['evolving','frozen']:
                center=p[ref+'_center_ticks'];contact=(p.low_ticks<=center+1)&(p.high_ticks>=center-1)
                assert bool(row[ref+'_touch'])==bool(contact.any())
                if contact.any():
                    ix=np.flatnonzero(contact)[0]
                    assert row[ref+'_latency_minutes']==ix+1
                    assert pd.Timestamp(row['observed_'+ref+'_touch_open'])==p.ts_event.iloc[ix]
                checks.append(ref+'_touch_and_latency')
        else:
            sigma=row.sigma_signal
            if not np.isfinite(sigma) or sigma<=0:result='unavailable'
            else:
                ticks=max(1,math.ceil(.5*sigma/tick));result='neither'
                for x in p.itertuples():
                    if x.open_ticks>=e+ticks:result='bounce' if row.d==1 else 'through';break
                    if x.open_ticks<=e-ticks:result='through' if row.d==1 else 'bounce';break
                    up=x.high_ticks>=e+ticks;down=x.low_ticks<=e-ticks
                    if up and down:result='ambiguous';break
                    if up:result='bounce' if row.d==1 else 'through';break
                    if down:result='through' if row.d==1 else 'bounce';break
            assert row.first_move==result,(row.horizon_id,'first_move',row.first_move,result)
            checks.append('independent_barrier_race')
    else:
        assert row.exclusion_reason=='session_boundary' or len(p)!=2*row.horizon_bars or not p.open.notna().all()
        checks.append('excluded_horizon')
    return p,checks


def audit(out):
    out=Path(out);evidence=out/'evidence'
    frames={name:pd.read_parquet(evidence/(name+'.parquet')) for name in ['parents','thresholds','touches','candidates','departure-horizons','touch-horizons']}
    pa=frames['parents'];ev=frames['thresholds'];to=frames['touches'];ca=frames['candidates'];dep=frames['departure-horizons'];touch=frames['touch-horizons']
    tests=[]
    for name,key in [('parents','parent_id'),('thresholds','event_id'),('touches','event_id'),('candidates','candidate_id'),('departure-horizons','horizon_id'),('touch-horizons','horizon_id')]:
        assert not frames[name][key].duplicated().any();tests.append(name+'_unique_keys')
    assert set(ev.parent_id)==set(pa.parent_id);assert set(to.parent_id)<=set(pa.parent_id)
    assert len(ev[ev.threshold==2])==len(pa);assert not ev.duplicated(['parent_id','threshold']).any()
    assert not to.parent_id.duplicated().any();assert set(to.parent_id)==set(pa.loc[pa.termination_reason=='touch','parent_id'])
    assert (pa.termination_reason.notna()).all();assert len(ca[ca.status=='accepted'])==len(ev)
    assert set(dep.event_id)==set(ev.event_id) and set(touch.event_id)==set(to.event_id)
    assert (dep.groupby('event_id').size()==5).all() and (touch.groupby('event_id').size()==5).all()
    tests+=['parent_threshold_touch_foreign_keys','one_2sigma_per_parent','one_touch_per_parent','all_five_horizon_rows','candidate_reconciliation']
    for name,f in [('departure',dep),('touch',touch)]:
        good=f[f.eligible]
        assert np.allclose(good.long_mfe,good.short_mae) and np.allclose(good.long_mae,good.short_mfe)
        assert (good[['above_entry','below_entry','entry_tie']].astype(int).sum(axis=1)==1).all()
        assert (good[['final_candle_up','final_candle_down','final_candle_tie']].astype(int).sum(axis=1)==1).all()
        assert (pd.to_datetime(good.deadline)<=pd.to_datetime(good.session_end)).all()
        common=good[good.common_50].sort_values(['event_id','horizon_bars'])
        for col in ['long_mfe','long_mae']+(['evolving_touch','frozen_touch'] if name=='departure' else []):
            diff=common.assign(value=common[col].astype(float)).groupby('event_id').value.diff().dropna()
            assert (diff>=-1e-9).all(),(name,col)
        if name=='departure':assert f.loc[~f.eligible,'evolving_touch'].isna().all() and f.loc[~f.eligible,'frozen_touch'].isna().all()
        else:assert good.first_move.isin(['bounce','through','neither','ambiguous','unavailable']).all()
        tests += [name+'_directional_symmetry',name+'_terminal_count_reconciliation',name+'_common_cohort_monotonicity',name+'_boundary_and_null_semantics']
    # Recount every published main cell's denominator and central metric directly.
    summary=pd.read_parquet(out/'tables/summary.parquet');checked=0
    grouped={kind:dict(tuple(frame.groupby(['product','session','horizon_bars']))) for kind,frame in [('departure',dep),('touch',touch)]}
    for row in summary[summary.scope.isin(['all','common_50','age_ge30'])].itertuples():
        g=grouped[row.kind][(row.product,row.session,row.horizon_bars)]
        g=g[g.threshold==row.threshold] if row.kind=='departure' else g[g.threshold>=row.threshold]
        if row.side!='both':g=g[g.side==row.side]
        if row.scope=='common_50':g=g[g.common_50]
        if row.scope=='age_ge30':g=g[g['anchor_age_minutes' if row.kind=='departure' else 'departure_anchor_age_minutes']>=30]
        assert row.candidate_events==len(g)
        good=g[g.eligible];assert row.n==len(good) and row.unavailable==len(g)-len(good)
        assert row.parents==good.parent_id.nunique() and row.days==good.session_date.nunique() and row.weeks==good.iso_week.nunique()
        if len(good):
            for col in ['primary_mae','primary_mfe','directional_delta','above_entry','final_candle_up']:
                assert np.isclose(getattr(row,col+'_mean'),good[col].astype(float).mean(),atol=1e-10)
            if row.kind=='departure':assert row.evolving_touch_count==int(good.evolving_touch.sum())
            else:assert sum(getattr(row,'first_'+c+'_count') for c in ['bounce','through','neither','ambiguous'])+row.barrier_unavailable==len(good)
        checked+=1
    tests.append('all_main_summary_cells_recounted')
    examples=choose_examples(dep,touch);save_table(out/'tables/example-selection',examples)
    # Additional deterministic first/last event per product/session/year, all horizons.
    extra=[]
    for frame in [dep,touch]:
        for _,g in frame.groupby(['product','session','year']):
            ids=sorted(g.event_id.unique());extra.extend(ids[:1]+ids[-1:])
    selections=pd.concat([examples.dropna(subset=['horizon_id']),dep[dep.event_id.isin(extra)],touch[touch.event_id.isin(extra)]],ignore_index=True).drop_duplicates('horizon_id')
    recounts=[];example_paths=[]
    for (product,year),group in selections.groupby(['product','year']):
        f,raw=load_year(product,int(year))
        for _,row in group.iterrows():
            # Independent signal crossing and post-touch confirmation timing.
            if row.kind=='departure':
                fi=f.set_index('ts_event');signal=pd.Timestamp(row.signal_open);prior=signal-pd.Timedelta(minutes=2)
                current=fi.loc[signal];previous=fi.loc[prior];d=int(row.d);k=row.threshold
                assert current.available_at==pd.Timestamp(row.entry_time)
                assert d*(current['close']*1e-9-current[row.session+'_vwap'])>k*current[row.session+'_sigma']
                assert d*(previous['close']*1e-9-previous[row.session+'_vwap'])<=k*previous[row.session+'_sigma']
            else:
                assert pd.Timestamp(row.touch_open)>=pd.Timestamp(row.departure_time)
                assert pd.Timestamp(row.touch_close)<=pd.Timestamp(row.entry_time)
                assert pd.Timestamp(row.entry_time)-pd.Timestamp(row.touch_open)<=pd.Timedelta(minutes=2)
                earlier=ev[ev.parent_id==row.parent_id]
                assert (pd.to_datetime(earlier.entry_time)<=pd.Timestamp(row.touch_open)).all()
                assert earlier.threshold.max()==row.threshold
                visual=row.copy();visual.entry_time=row.departure_time;visual.deadline=row.entry_time
                pp=independent_path(visual,f,raw);previous_close=float(f.loc[f.available_at==pd.Timestamp(row.departure_time),'close'].iloc[0])*1e-9-float(f.loc[f.available_at==pd.Timestamp(row.departure_time),'price_adjustment'].iloc[0])*1e-9
                previous_close/=row.min_tick;last_center=None;actual=None
                for minute in pp.itertuples():
                    center=minute.evolving_center_ticks
                    if last_center is not None and center!=last_center:
                        assert not (row.d*(previous_close-last_center)>1 and row.d*(previous_close-center)<-1)
                    assert not ((previous_close>center+1 and minute.open_ticks<center-1) or (previous_close<center-1 and minute.open_ticks>center+1))
                    if minute.low_ticks<=center+1 and minute.high_ticks>=center-1:
                        actual=minute.ts_event;break
                    previous_close=minute.close_ticks;last_center=center
                assert actual==pd.Timestamp(row.touch_open),(row.horizon_id,'first parent contact')
            p,checks=recount(row,f,raw);recounts.append({'horizon_id':row.horizon_id,'checks':';'.join(checks),'pass':True})
            if pd.notna(row.get('example_class')):
                visual=row.copy();visual.entry_time=row.signal_open if row.kind=='departure' else str(pd.Timestamp(row.departure_time)-pd.Timedelta(minutes=2))
                p=independent_path(visual,f,raw)
                p['horizon_id']=row.horizon_id;p['example_class']=row.example_class;p['session']=row.session
                for col in ['entry_time','signal_close_time','deadline','vwap_signal','sigma_signal','min_tick']:
                    p[col]=row[col]
                example_paths.append(p)
        print(f'audit raw source {product} {int(year)}: {len(group)} horizons',flush=True)
    save_table(out/'tables/independent-recounts',recounts)
    save_table(out/'tables/example-paths',pd.concat(example_paths,ignore_index=True))
    tests.append('independent_raw_source_recounts')
    # Retained old study/release/source record preservation.
    baseline=json.loads((out.parents[0]/'preservation-baseline.json').read_text())
    root=Path.cwd()
    for path,digest in baseline.items():assert sha(root/path)==digest,('preservation',path)
    tests.append('older_studies_runs_catalog_and_packages_unchanged')
    dump(out/'verification.json',{'status':'pass','verified_at':utcnow(),'checks':tests,
       'main_summary_cells_reconciled':checked,'independent_source_horizons':len(recounts),
       'preserved_preexisting_files':len(baseline),'ledger_counts':{n:len(f) for n,f in frames.items()},
       'independent_recount_method':'Fresh public loader reads; independent availability search and Decimal tick rounding; direct raw OHLC extrema and barrier loop.',
       'synthetic_tests':json.loads((out/'freeze.json').read_text())['tests'],
       'remaining_checks':['rendered report visual inspection','documentation','navigation','sealed artifact verification']})
