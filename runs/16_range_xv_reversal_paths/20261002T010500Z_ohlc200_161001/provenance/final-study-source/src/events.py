"""Exact OHLC reversal ledger with explicit barriers, availability and forward labels."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .common import Q,SCALE,HORIZONS,lbin,compact,window,split,FEATURES

def ratio(a,b): return float(a/b) if b>0 else np.nan
def switch(ds):
    good=(ds[1:]!=0)&(ds[:-1]!=0);n=int(good.sum())
    return ratio(np.sum((ds[1:]!=ds[:-1])&good),n),n
def efficiency(o,c): return ratio(abs(int(c[-1])-int(o[0])),abs(int(c[0])-int(o[0]))+np.abs(np.diff(c)).sum())

def path(o,h,l,c,t,r,d,n):
    """Caller establishes a completed window; includes entry and exit, excludes R."""
    e=int(o[r+1]);x=int(o[r+n+1]);hi=np.r_[e,h[r+1:r+n+1],x];lo=np.r_[e,l[r+1:r+n+1],x]
    fav=(hi-e) if d==1 else (e-lo);adv=(e-lo) if d==1 else (hi-e)
    mfe=int(fav.max());mae=int(adv.max());fi=int(np.argmax(fav));ai=int(np.argmax(adv))
    def interval(i,v):
        if v==0:return (None,None,None)
        if i==n+1:return (n+1,int(t[r+n+1]-t[r+1]),int(t[r+n+1]-t[r+1]))
        return (i,int(t[r+i]-t[r+1]),int(t[r+i+1]-t[r+1]))
    fb,fs,fe=interval(fi,mfe);ab,aas,ae=interval(ai,mae)
    return {'entry_i':e,'exit_i':x,'D_i':d*(x-e),'MAE_i':mae,'MFE_i':mfe,
      'close_delta_i':d*(int(c[r+n])-e),'structural_delta_i':d*(int(c[r+n])-int(c[r])),
      'mean_body_i':float(d*np.mean(c[r+1:r+n+1]-o[r+1:r+n+1])),
      'elapsed_seconds':int(t[r+n+1]-t[r+1]),'MFE_bar':fb,'MFE_time_low':fs,'MFE_time_high':fe,
      'MAE_bar':ab,'MAE_time_low':aas,'MAE_time_high':ae}

def segments(df):
    days=df.session_date_proxy.to_numpy();barrier=df.barrier.to_numpy();n=len(df);a=0
    while a<n:
        if barrier[a]:a+=1;continue
        b=a+1
        while b<n and not barrier[b] and days[b]==days[a]:b+=1
        yield a,b
        a=b

def extract(df,include_repeated=False):
    if include_repeated:df=df.copy();df['barrier']=df.invalid
    o,h,l,c=[df[n+'_i'].to_numpy() for n in ['open','high','low','close']]
    ds=df.direction.to_numpy();t=df.timestamp_seconds.to_numpy();dur=df.duration.to_numpy();days=df.session_date_proxy.to_numpy()
    stamp=df.bar_start_timestamp.to_numpy();q=int(df.q_i.iloc[0]);chart=df.chart.iloc[0];product=df['product'].iloc[0]
    gap=df.long_gap.to_numpy();out=[]
    for a,b in segments(df):
        s=a;known=False;history=[]
        for r in range(a,b-1): # last row has no observed within-segment completion
            if ds[r]==0:
                if r>s and ds[s]!=0: history.append((r-s,known))
                s=r+1;known=True;continue
            if r==s:continue
            if ds[r]==ds[r-1]:continue
            if ds[r-1]==0:s=r;known=True;continue
            L=r-s;d=int(ds[r]);p=-d
            # No future outcome is used in the feature block.
            body=np.abs(c[s:r]-o[s:r]);span=h[s:r]-l[s:r];prior_span=int(h[s:r].max()-l[s:r].min())
            upper=h[s:r]-np.maximum(o[s:r],c[s:r]);lower=np.minimum(o[s:r],c[s:r])-l[s:r]
            minutes=(t[r]-t[s])/60;distance=p*(int(c[r-1])-int(o[s]));rspan=int(h[r]-l[r]);rbody=abs(int(c[r])-int(o[r]))
            overlap=np.maximum(0,np.minimum(h[s+1:r],h[s:r-1])-np.maximum(l[s+1:r],l[s:r-1]))
            overlapden=np.minimum(span[1:],span[:-1]);valid=overlapden>0
            e={'event_id':f'{chart}:{r+1}', 'chart':chart,'product':product,'setting':int(chart.split('_')[1]),
              'direction':d,'direction_name':'bullish' if d==1 else 'bearish','R_row':r+1,'prior_start_row':s+1,
              'segment_start_row':a+1,'segment_end_row':b,'prior_known':known,'L':L if known else np.nan,
              'L_observed':L,'L_bin':lbin(L) if known else 'unknown','compact_L':compact(L) if known else 'unknown',
              'session_date':days[r],'year':int(days[r][:4]),'split':split(days[r]),'available_at':stamp[r+1],
              'available_seconds':int(t[r+1]),'max_feature_source_row':r+1,'R_start':stamp[r],
              'window':window(stamp[r+1]),'era':'pre' if product=='6S' and days[r]<'2022-05-02' else 'post' if product=='6S' else 'constant',
              'primary':known and days[r] not in ['2017-07-21','2026-10-01'],
              'exclusion':'unknown_prior_start' if not known else 'excluded_export_edge_session' if days[r] in ['2017-07-21','2026-10-01'] else '',
              'q_i':q,'historical_q_i':int(df.historical_q_i.iloc[r]),'prior_same_second':bool(np.any(dur[s:r]==0)),
              'prior_long_gap':bool(gap[s:r+1].any()),'R_same_second':bool(dur[r]==0),'R_zero_duration':bool(dur[r]==0),
              'R_open_i':int(o[r]),'R_high_i':int(h[r]),'R_low_i':int(l[r]),'R_close_i':int(c[r]),
              'prior_distance_q':distance/q,'prior_body_total_q':float(body.sum()/q),'prior_span_q':prior_span/q,
              'prior_distance_price':distance/SCALE,'prior_body_total_price':float(body.sum()/SCALE),'prior_span_price':prior_span/SCALE,
              'prior_duration_seconds':int(t[r]-t[s]),'prior_seconds_per_bar':float((t[r]-t[s])/L),
              'prior_bars_per_minute':ratio(L,minutes),'prior_distance_per_minute_q':ratio(distance/q,minutes),
              'prior_efficiency':efficiency(o[s:r],c[s:r]),'prior_zero_duration':minutes==0,
              'prior_mean_body_q':float(body.mean()/q),'prior_median_body_q':float(np.median(body)/q),
              'prior_mean_span_q':float(span.mean()/q),'prior_median_span_q':float(np.median(span)/q),
              'prior_median_body_fraction':float(np.median(body[span>0]/span[span>0])) if np.any(span>0) else np.nan,
              'prior_direction_wick_fraction':float(np.mean((upper if p==1 else lower)/span)),
              'prior_counter_wick_fraction':float(np.mean((lower if p==1 else upper)/span)),
              'prior_overlap':float(np.mean(overlap[valid]/overlapden[valid])) if valid.any() else np.nan,
              'R_body_q':rbody/q,'R_span_q':rspan/q,'R_body_fraction':ratio(rbody,rspan),
              'R_upper_wick_fraction':ratio(int(h[r])-max(int(o[r]),int(c[r])),rspan),
              'R_lower_wick_fraction':ratio(min(int(o[r]),int(c[r]))-int(l[r]),rspan),
              'R_close_location':ratio(int(c[r])-int(l[r]) if d==1 else int(h[r])-int(c[r]),rspan),
              'R_opposing_q':d*(int(c[r])-int(c[r-1]))/q,'R_gap_q':(int(o[r])-int(c[r-1]))/q,
              'R_body_prior_span':ratio(rbody,prior_span),'R_opposing_prior_span':ratio(d*(int(c[r])-int(c[r-1])),prior_span),
              'R_duration_seconds':int(t[r+1]-t[r]),'log_L':float(np.log1p(L)) if known else np.nan}
            for k in range(1,4):
                e[f'previous_leg_{k}']=history[-k][0] if len(history)>=k and history[-k][1] else np.nan
            for k in [10,20]:
                if r-a>=k:e[f'chop{k}'],e[f'chop{k}_pairs']=switch(ds[r-k:r])
                else:e[f'chop{k}']=np.nan;e[f'chop{k}_pairs']=0
            if r-a>=20:e['recent20_efficiency']=efficiency(o[r-20:r],c[r-20:r])
            else:e['recent20_efficiency']=np.nan
            if r-a>=21:
                tr=np.maximum.reduce([h[r-20:r]-l[r-20:r],np.abs(h[r-20:r]-c[r-21:r-1]),np.abs(l[r-20:r]-c[r-21:r-1])]);e['recent20_tr_q']=float(np.median(tr)/q)
            else:e['recent20_tr_q']=np.nan
            e['R_span_recent20_tr']=ratio(e['R_span_q'],e['recent20_tr_q'])
            for name,f in [('pace','prior_bars_per_minute'),('efficiency','prior_efficiency'),('chop','chop20'),('R_relative','R_body_prior_span')]:e['interaction_'+name]=e['log_L']*e[f]
            if not known:
                for n in list(e):
                    if n.startswith('prior_') and n not in ['prior_start_row','prior_known','prior_same_second','prior_long_gap','prior_zero_duration']:e[n]=np.nan
                for n in ['R_body_prior_span','R_opposing_prior_span','interaction_pace','interaction_efficiency','interaction_chop','interaction_R_relative']:e[n]=np.nan
            for f in FEATURES:e['undefined_'+f]=bool(pd.isna(e[f]))
            e['feature_complete']=all(not e['undefined_'+f] for f in FEATURES)
            # Forward labels: only completed physical followers count, and a completed breaker is necessary.
            j=r+1
            while j<b-1 and ds[j]==d:j+=1
            obs=j-(r+1);breaker=j<b-1
            e.update(F_observed=obs,F_exact=obs if breaker else np.nan,right_censored=not breaker,
             breaker_row=j+1 if breaker else np.nan,breaker_direction=int(ds[j]) if breaker else np.nan,
             future_boundary='quality_barrier' if b<len(df) and df.barrier.iloc[b] else 'export_end' if b==len(df) else 'session_end',
             new_leg_length=1+obs if breaker else np.nan,new_leg_seconds=int(t[j]-t[r]) if breaker else np.nan)
            for k in range(1,11):
                eligible=r+k+1<b
                e[f'order{k}']=eligible
                e[f'strict{k}']=eligible and bool(np.all(dur[r:r+k+1]>0))
                e[f'y{k}']=1. if obs>=k else 0. if breaker else np.nan
                if k<=5:e[f'time_to{k}']=int(t[r+k+1]-t[r+1]) if obs>=k else np.nan
            e['cap10']=float(min(obs,10)) if e['order10'] else np.nan
            for n in HORIZONS:
                eligible=e[f'order{n}'];strict=e[f'strict{n}']
                e[f'strict{n}']=strict;e[f'path_long_gap{n}']=bool(gap[r:r+min(n+1,b-r-1)].any()) or e['prior_long_gap']
                e[f'path_reason{n}']='eligible' if strict else 'nonpositive_duration' if eligible else e['future_boundary']
                if eligible:
                    v=path(o,h,l,c,t,r,d,n)
                    for f,x in v.items():e[f'h{n}_{f}']=x
                    for f in ['D','MAE','MFE','close_delta','structural_delta','mean_body']:
                        x=v[f+'_i'];e[f'h{n}_{f}_q']=x/q;e[f'h{n}_{f}_price']=x/SCALE;e[f'h{n}_{f}_historical_ticks']=x/e['historical_q_i']
                    e[f'h{n}_D_Rspan']=ratio(v['D_i'],rspan);e[f'h{n}_D_recentTR']=ratio(v['D_i']/q,e['recent20_tr_q'])
                    e[f'h{n}_D_MFE']=ratio(v['D_i'],v['MFE_i']);e[f'h{n}_exit_row']=r+n+2;e[f'h{n}_exit_time']=stamp[r+n+1]
                    for multiple in [.5,1.]:
                        tag='half' if multiple==.5 else 'one';level=rspan*multiple
                        for kind,values in [('favourable',d*(h[r+1:r+n+1]-v['entry_i']) if d==1 else d*(l[r+1:r+n+1]-v['entry_i'])),('adverse',-d*(l[r+1:r+n+1]-v['entry_i']) if d==1 else -d*(h[r+1:r+n+1]-v['entry_i']))]:
                            vv=np.r_[values,d*(v['exit_i']-v['entry_i']) if kind=='favourable' else -d*(v['exit_i']-v['entry_i'])];hits=np.flatnonzero(vv>=level)
                            e[f'h{n}_{kind}_{tag}_hit']=bool(len(hits))
                            ix=int(hits[0])+1 if len(hits) else None;e[f'h{n}_{kind}_{tag}_bar']=ix
                            e[f'h{n}_{kind}_{tag}_time_low']=int(t[r+ix]-t[r+1]) if ix else np.nan
                            e[f'h{n}_{kind}_{tag}_time_high']=int(t[r+min(ix+1,n+1)]-t[r+1]) if ix else np.nan
                        e[f'h{n}_{tag}_intrabar_order_unknown']=e[f'h{n}_favourable_{tag}_bar']==e[f'h{n}_adverse_{tag}_bar'] and e[f'h{n}_favourable_{tag}_bar'] is not None
            for minutes_ in [5,15,30]:
                target=t[r+1]+minutes_*60;observed=t[b-1]>=target
                e[f'clock{minutes_}_boundary_censored']=not observed
                endpoint=min(int(np.searchsorted(t[r+2:b],target,side='right'))+r+2,b)-1
                covered=observed and endpoint>=r+2
                e[f'clock{minutes_}_covered']=covered
                if covered:
                    bar=endpoint-1;e[f'clock{minutes_}_bar_row']=bar+1;e[f'clock{minutes_}_actual_time']=stamp[endpoint]
                    e[f'clock{minutes_}_elapsed']=int(t[endpoint]-t[r+1]);e[f'clock{minutes_}_staleness']=int(target-t[endpoint])
                    e[f'clock{minutes_}_D_q']=d*(int(c[bar])-int(o[r+1]))/q;e[f'clock{minutes_}_strict']=bool(np.all(dur[r:bar+1]>0))
            out.append(e)
            history.append((L,known));s=r;known=True
    return pd.DataFrame(out)
