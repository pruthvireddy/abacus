"""Causal episode state machine and forward labels. No portfolio/P&L model."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
from .common import MINUTE, HORIZONS, THRESHOLDS, SCHEMA_VERSION, window, stamp, week, age_bin, latency_bin


def round_half_up(values):
    values=np.asarray(values,dtype=float)
    return np.copysign(np.floor(np.abs(values)+0.5),values)


def zone_touch(low,high,center): return bool(low<=center+1 and high>=center-1)

def whole_gap(previous_close,opening,center):
    return bool((previous_close>center+1 and opening<center-1) or
                (previous_close<center-1 and opening>center+1))

def reference_overtake(close,old,new,side):
    # Require the entire newly rounded zone to have passed the current close.
    return bool(side*(close-old)>1 and side*(close-new)<-1)

def first_move(o,h,l,entry,distance,side):
    if not np.isfinite(distance) or distance<=0: return 'unavailable',False,None
    up=entry+distance;down=entry-distance
    for j in range(len(o)):
        if not np.isfinite(o[j]+h[j]+l[j]): return 'unavailable',False,None
        if o[j]>=up: return ('bounce' if side==1 else 'through'),True,j
        if o[j]<=down: return ('through' if side==1 else 'bounce'),True,j
        u=h[j]>=up;d=l[j]<=down
        if u and d: return 'ambiguous',False,j
        if u: return ('bounce' if side==1 else 'through'),False,j
        if d: return ('through' if side==1 else 'bounce'),False,j
    return 'neither',False,None

@dataclass
class Session:
    product: str
    name: str
    day: str
    start: int
    end: int
    tick: float
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    vwap: np.ndarray  # completed-bar unrounded reference in ticks
    sigma: np.ndarray # completed-bar sigma in ticks
    volume: np.ndarray
    valid_bar: np.ndarray
    minute_ok: np.ndarray
    identity: np.ndarray
    adjustment: np.ndarray
    raw_symbol: np.ndarray
    instrument: np.ndarray
    close: np.ndarray
    centers: np.ndarray  # per-minute lagged, rounded reference
    source_feature: str = ''
    source_raw: str = ''

    @property
    def n(self): return len(self.vwap)
    def ts(self,i): return self.start+int(i)*MINUTE
    def valid_signal(self,i):
        return bool(self.valid_bar[i] and np.isfinite(self.vwap[i]) and np.isfinite(self.sigma[i]) and self.sigma[i]>0 and self.volume[i]>0)
    def same(self,a,b):
        return bool(self.identity[a]==self.identity[b] and self.adjustment[a]==self.adjustment[b])
    def z(self,i): return (self.close[i]-self.vwap[i])/self.sigma[i]


def make_session(features,raw,product,name,day):
    a,b=window(day,name); n=int((b-a)/pd.Timedelta(minutes=2))
    times=pd.date_range(a,b,freq='1min',inclusive='left')
    f=features.set_index('ts_event').reindex(times[::2])
    r=raw.set_index('ts_event').reindex(times)
    tick_int=int(features.min_tick.iloc[0]);tick=tick_int*1e-9
    arr=lambda col: r[col].to_numpy(dtype=float)/tick_int
    identity=(f.raw_symbol.astype(str)+'|'+f.instrument_id.astype(str)+'|'+f.roll_id.astype(str)).to_numpy()
    minute_identity=(r.raw_symbol.astype(str)+'|'+r.instrument_id.astype(str)+'|'+r.roll_id.astype(str)).to_numpy()
    adj=f.price_adjustment.to_numpy(dtype=float)
    minute_ok=(r.open.notna() & r.high.notna() & r.low.notna() & r.close.notna()).to_numpy()
    minute_ok &= minute_identity==np.repeat(identity,2)
    minute_ok &= r.session_date.astype(str).to_numpy()==str(day)
    minute_ok &= r['product'].to_numpy()==product
    valid=minute_ok.reshape(-1,2).all(axis=1)&(f.available_at.to_numpy()==(times[::2]+pd.Timedelta(minutes=2)).to_numpy())
    valid &= (f[f'{name}_anchor_ts'].to_numpy()==a)&(f.source_bar_count.to_numpy()==2)
    valid &= (f.min_tick.to_numpy()==tick_int)
    close=(f.close.to_numpy(dtype=float)-adj)/tick_int
    vv=(f[f'{name}_vwap'].to_numpy(dtype=float)-adj*1e-9)/tick
    sigma=f[f'{name}_sigma'].to_numpy(dtype=float)/tick
    volume=f[f'{name}_cumulative_volume'].to_numpy(dtype=float)
    good_ref=valid&np.isfinite(vv)&(volume>0)
    centers=np.repeat(np.r_[np.nan,np.where(good_ref[:-1],round_half_up(vv[:-1]),np.nan)],2)
    year=str(day)[:4]
    return Session(product,name,str(day),a.value,b.value,tick,arr('open'),arr('high'),arr('low'),arr('close'),
       vv,sigma,volume,valid,minute_ok,identity,adj,f.raw_symbol.to_numpy(),f.instrument_id.to_numpy(),close,centers,
       f'data/features/bars/2m/feature_set=session_anchored_vwap/version=1.0.0/product={product}/year={year}/part-000.parquet',
       f'data/curated/continuous/1m/product={product}/roll=volume_lead_v1/variant=unadjusted/year={year}/part-000.parquet')


def event_base(s,i,side,parent_id,event_id,threshold,kind):
    t=s.ts(2*(i+1));local=pd.Timestamp(t,tz='UTC').tz_convert('America/New_York')
    return {'schema_version':SCHEMA_VERSION,'event_id':event_id,'parent_id':parent_id,'kind':kind,
       'product':s.product,'session':s.name,'session_date':s.day,'year':int(s.day[:4]),'iso_week':week(s.day),
       'side':'upper' if side==1 else 'lower','d':side,'threshold':threshold,'signal_bar_index':i,
       'signal_open':stamp(s.ts(2*i)),'signal_close_time':stamp(t),'available_at':stamp(t),
       'entry_time':stamp(t),'session_end':stamp(s.end),'anchor_time':stamp(s.start),
       'anchor_age_minutes':2*(i+1),'anchor_age_bin':age_bin(2*(i+1)),'local_hour':local.hour,
       'signal_close':float(s.close[i]*s.tick),'vwap_signal':float(s.vwap[i]*s.tick),
       'sigma_signal':float(s.sigma[i]*s.tick) if np.isfinite(s.sigma[i]) else None,
       'min_tick':s.tick,'raw_symbol':str(s.raw_symbol[i]),'instrument_id':int(s.instrument[i]),
       'price_adjustment_fixed':int(s.adjustment[i]),'identity':str(s.identity[i]),
       'feature_partition':s.source_feature,'raw_partition':s.source_raw,
       'entry_minute_index':2*(i+1),'entry_open':float(s.o[2*(i+1)]*s.tick) if 2*(i+1)<len(s.o) and np.isfinite(s.o[2*(i+1)]) else None}


def episodes(s):
    parents=[];thresholds=[];touches=[];candidates=[]
    parent=None;armed=False;reached=set();original=None
    for i in range(s.n):
        valid=s.valid_signal(i)
        pair=i>0 and valid and s.valid_signal(i-1) and s.same(i-1,i)
        fresh=[]
        if pair:
            z=s.z(i);pz=s.z(i-1)
            for d in (1,-1):
                for k in THRESHOLDS:
                    if d*z>k and d*pz<=k: fresh.append((d,k))
        ended=False;reason=None;contact_minute=None;termination_ns=None
        if parent is not None:
            d=parent['d']
            if i==0 or not s.same(i-1,i): reason='contract_or_adjustment_break';termination_ns=s.ts(2*i)
            else:
                for m in (2*i,2*i+1):
                    if not s.minute_ok[m]: reason='missing_or_invalid_minute'
                    elif not np.isfinite(s.centers[m]): reason='invalid_reference'
                    elif whole_gap(s.c[m-1],s.o[m],s.centers[m]): reason='gap_through'
                    elif zone_touch(s.l[m],s.h[m],s.centers[m]): reason='touch';contact_minute=m
                    if reason:
                        termination_ns=s.ts(m if reason=='gap_through' else m+1);break
                if reason is None and s.valid_bar[i] and np.isfinite(s.vwap[i]) and s.volume[i]>0:
                    if reference_overtake(s.close[i],s.centers[2*i+1],round_half_up(s.vwap[i]).item(),d):
                        reason='reference_overtake';termination_ns=s.ts(2*(i+1))
            if reason:
                parent.update(termination_reason=reason,termination_time=stamp(termination_ns),
                              termination_bar_index=i)
                if reason=='touch':
                    ev=event_base(s,i,d,parent['parent_id'],parent['parent_id']+'-T',max(reached),'touch')
                    ev.update(touch_open=stamp(s.ts(contact_minute)),touch_close=stamp(s.ts(contact_minute+1)),
                       touch_minute_index=contact_minute,touched_vwap=float(s.centers[contact_minute]*s.tick),
                       touched_reference_available_at=stamp(s.ts(2*(contact_minute//2))),
                       departure_time=original['entry_time'],departure_anchor_age_minutes=original['anchor_age_minutes'],departure_event_id=original['event_id'],
                       latency_minutes=contact_minute-original['entry_minute_index']+1,
                       latency_bars=(contact_minute-original['entry_minute_index'])//2+1,
                       reached_thresholds=','.join(f'{x:g}' for x in sorted(reached)))
                    ev['latency_bin']=latency_bin(ev['latency_bars'])
                    ev['entry_location']=None if ev['entry_open'] is None else ('above' if ev['entry_open']>ev['touched_vwap'] else 'below' if ev['entry_open']<ev['touched_vwap'] else 'at_center')
                    touches.append(ev)
                parent=None;armed=False;ended=True
        if not ended and parent is None and pair and armed and i<s.n-1:
            departure=next(((d,k) for d,k in fresh if k==2),None)
            if departure:
                d,_=departure;pid=f'{s.product}-{s.name}-{s.day}-P{i:04d}'
                parent={'schema_version':SCHEMA_VERSION,'parent_id':pid,'product':s.product,'session':s.name,
                  'session_date':s.day,'year':int(s.day[:4]),'iso_week':week(s.day),'d':d,
                  'side':'upper' if d==1 else 'lower','departure_bar_index':i,
                  'departure_time':stamp(s.ts(2*(i+1))),'termination_reason':None,'termination_time':None,
                  'raw_symbol':str(s.raw_symbol[i]),'instrument_id':int(s.instrument[i]),
                  'feature_partition':s.source_feature,'raw_partition':s.source_raw}
                parents.append(parent);reached=set();armed=False
        for d,k in fresh:
            accepted=not ended and parent is not None and d==parent['d'] and k not in reached and i<s.n-1
            why='accepted' if accepted else ('termination_precedes_signal' if ended else 'session_end_no_next_open' if i==s.n-1 else
               'left_censored_or_unarmed' if parent is None else 'opposite_side_active_parent' if d!=parent['d'] else 'already_recorded_parent')
            cid=f'{s.product}-{s.name}-{s.day}-C{i:04d}-{d}-{k:g}'
            candidates.append({'schema_version':SCHEMA_VERSION,'candidate_id':cid,'product':s.product,'session':s.name,
                'session_date':s.day,'year':int(s.day[:4]),'bar_index':i,'signal_time':stamp(s.ts(2*(i+1))),
                'side':'upper' if d==1 else 'lower','threshold':k,'status':why,
                'parent_id':parent['parent_id'] if parent else None})
            if accepted:
                eid=parent['parent_id']+f'-K{k:g}'
                ev=event_base(s,i,d,parent['parent_id'],eid,k,'departure')
                thresholds.append(ev);reached.add(k)
                if k==2:original=ev
        if valid and not pair and abs(s.z(i))>2:
            candidates.append({'schema_version':SCHEMA_VERSION,'candidate_id':f'{s.product}-{s.name}-{s.day}-L{i:04d}',
              'product':s.product,'session':s.name,'session_date':s.day,'year':int(s.day[:4]),'bar_index':i,
              'signal_time':stamp(s.ts(2*(i+1))),'side':'upper' if s.z(i)>0 else 'lower','threshold':2.,
              'status':'outside_without_consecutive_valid_bars','parent_id':None})
        if parent is None:
            if valid and abs(s.z(i))<=2:armed=True
            elif not valid:armed=False
        if parent is not None and i==s.n-1:
            parent.update(termination_reason='session_end',termination_time=stamp(s.end),termination_bar_index=i)
    return parents,thresholds,touches,candidates


def horizon_reason(s,event,h):
    start=event['entry_minute_index'];end=start+2*h
    if end>len(s.o):return 'session_boundary'
    if not s.minute_ok[start:end].all():return 'missing_or_invalid_minute'
    bars=slice(start//2,end//2)
    if not s.valid_bar[bars].all():return 'invalid_feature_or_source_bar'
    if not np.all(s.identity[bars]==event['identity']) or not np.all(s.adjustment[bars]==event['price_adjustment_fixed']):
        return 'contract_or_adjustment_break'
    if not np.isfinite(s.centers[start:end]).all():return 'invalid_reference'
    return None


def contact_path(s,event,end):
    start=event['entry_minute_index'];frozen=round_half_up(event['vwap_signal']/s.tick).item()
    first_e=None;first_f=None;gaps=0;overtakes=0
    for m in range(start,min(end,len(s.o))):
        b=m//2
        if not s.minute_ok[m] or not s.same(event['signal_bar_index'],b) or not np.isfinite(s.centers[m]):break
        center=s.centers[m]
        if first_e is None and zone_touch(s.l[m],s.h[m],center):first_e=m
        if first_f is None and zone_touch(s.l[m],s.h[m],frozen):first_f=m
        if m>0:
            gaps+=int(whole_gap(s.c[m-1],s.o[m],center))
            old=s.centers[m-1]
            if np.isfinite(old) and old!=center:
                overtakes+=int(reference_overtake(s.c[m-1],old,center,1) or reference_overtake(s.c[m-1],old,center,-1))
    return first_e,first_f,gaps,overtakes


def horizons(s,event):
    rows=[];start=event['entry_minute_index'];i=event['signal_bar_index'];d=event['d']
    for h in HORIZONS:
        end=start+2*h;reason=horizon_reason(s,event,h)
        r={**event,'horizon_id':event['event_id']+f'-H{h:02d}','horizon_bars':h,'horizon_minutes':2*h,
           'deadline':stamp(s.ts(end)),'eligible':reason is None,'exclusion_reason':reason,
           'common_50':horizon_reason(s,event,50) is None}
        if event['kind']=='departure':
            e,f,gaps,over=contact_path(s,event,end)
            r.update(observed_evolving_touch_open=stamp(s.ts(e)) if e is not None else None,
                observed_frozen_touch_open=stamp(s.ts(f)) if f is not None else None,
                evolving_touch_close=stamp(s.ts(e+1)) if e is not None else None,
                frozen_touch_close=stamp(s.ts(f+1)) if f is not None else None,
                evolving_touch=None if reason else e is not None, frozen_touch=None if reason else f is not None,
                evolving_latency_minutes=e-start+1 if e is not None else None,
                frozen_latency_minutes=f-start+1 if f is not None else None,
                evolving_latency_bars=(e-start)//2+1 if e is not None else None,
                frozen_latency_bars=(f-start)//2+1 if f is not None else None,
                evolving_only=None if reason else e is not None and f is None,
                frozen_only=None if reason else f is not None and e is None,
                gap_count=gaps,reference_overtake_count=over)
        if reason:
            rows.append(r);continue
        o=s.o[start:end];hi=s.h[start:end];lo=s.l[start:end];e=o[0];c=s.c[end-1];lastopen=s.o[end-2]
        long_mfe=max(0.,float(hi.max()-e));long_mae=max(0.,float(e-lo.min()));delta=float(c-e)
        sig=s.sigma[i]*s.tick
        r.update(entry_open=e*s.tick,terminal_close=c*s.tick,terminal_candle_open=lastopen*s.tick,
            long_mfe=long_mfe*s.tick,long_mae=long_mae*s.tick,short_mfe=long_mae*s.tick,short_mae=long_mfe*s.tick,
            price_delta=delta*s.tick,directional_delta=d*delta*s.tick,
            close_minus_signal_close=(c-s.close[i])*s.tick,entry_gap=(e-s.close[i])*s.tick,
            above_entry=c>e,below_entry=c<e,entry_tie=c==e,
            directional_positive=d*delta>0,directional_negative=d*delta<0,
            final_candle_up=c>lastopen,final_candle_down=c<lastopen,final_candle_tie=c==lastopen)
        # continuation/bounce is toward the original excursion side; fade/through is its inverse.
        r.update(primary_direction='long' if d==1 else 'short',opposite_direction='short' if d==1 else 'long',
            primary_mfe=(long_mfe if d==1 else long_mae)*s.tick,
            primary_mae=(long_mae if d==1 else long_mfe)*s.tick)
        r['opposite_mfe']=r['primary_mae'];r['opposite_mae']=r['primary_mfe'];r['opposite_directional_delta']=-r['directional_delta']
        for name in ('long_mfe','long_mae','short_mfe','short_mae','price_delta','directional_delta',
                     'primary_mfe','primary_mae','opposite_mfe','opposite_mae','opposite_directional_delta','close_minus_signal_close','entry_gap'):
            r[name+'_ticks']=r[name]/s.tick
            r[name+'_sigma']=r[name]/sig if np.isfinite(sig) and sig>0 else None
        if event['kind']=='touch':
            distance=max(1,math.ceil(.5*s.sigma[i])) if np.isfinite(s.sigma[i]) and s.sigma[i]>0 else np.nan
            result,gap,minute=first_move(o,hi,lo,e,distance,d)
            r.update(first_move=result,barrier_ticks=distance if np.isfinite(distance) else None,
               barrier_gap=gap,first_move_minute=minute+1 if minute is not None else None,
               bounce_endpoint=d*delta>0,through_endpoint=d*delta<0)
        rows.append(r)
    return rows
