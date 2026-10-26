"""Saved descriptive evidence, matched baselines, and declared sensitivities."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .common import LBINS,HORIZONS,SCALE,Q,load,save_table,dump
from .models import mask_condition

def moments(x,prefix):
    v=pd.Series(x).dropna().to_numpy(float)
    out={prefix+'_n':len(v),prefix+'_mean':v.mean() if len(v) else np.nan,prefix+'_median':np.median(v) if len(v) else np.nan}
    for p in [10,25,50,75,90,95,99]:out[f'{prefix}_p{p}']=np.quantile(v,p/100) if len(v) else np.nan
    return out
def support(g):return {'n':len(g),'dates':g.session_date.nunique(),'sparse':len(g)<100 or g.session_date.nunique()<30}
def groups(df,panels=True):
    for (chart,d),g in df.groupby(['chart','direction']):
        yield {'chart':chart,'direction':d,'panel':'all','level':'all'},g
        for lb in LBINS:yield {'chart':chart,'direction':d,'panel':'L','level':lb},g[g.L_bin==lb]
        if panels:
            for column in ['split','year','window','era']:
                for v,sub in g.groupby(column):yield {'chart':chart,'direction':d,'panel':column,'level':str(v)},sub

def continuation(g,boot):
    row=support(g);row.update(candidate_n=len(g),unresolved_F=int(g.right_censored.sum()),known_exact_n=int(g.F_exact.notna().sum()),
      censored_lower_mean=g.loc[g.right_censored,'F_observed'].mean(),F_exact_mean=g.F_exact.mean(),F_exact_median=g.F_exact.median())
    for k in [1,2,3,4,5,10]:
        eligible=g[g[f'order{k}']];col=f'y{k}';known_success=int(g[col].eq(1).sum());known_fail=int(g[col].eq(0).sum());unresolved=int(g[col].isna().sum())
        lo,hi,u=boot.mean(eligible,col)
        row.update({f'p{k}':eligible[col].mean(),f'p{k}_n':len(eligible),f'p{k}_dates':eligible.session_date.nunique(),
         f'p{k}_low':lo,f'p{k}_high':hi,f'p{k}_undefined_bootstrap':u,f'p{k}_known_success':known_success,
         f'p{k}_known_failure':known_fail,f'p{k}_unresolved':unresolved,f'p{k}_bounds_low':known_success/len(g) if len(g) else np.nan,
         f'p{k}_bounds_high':(known_success+unresolved)/len(g) if len(g) else np.nan})
    c3=g[g.order3];c10=g[g.order10]
    row['common3_n']=len(c3);row['common10_n']=len(c10)
    row.update(moments(g.F_exact,'F_exact'));row.update(moments(g.new_leg_length,'new_leg_length'))
    row['F_exact_mode']=g.F_exact.mode().iloc[0] if g.F_exact.notna().any() else np.nan
    for k in [1,2,3]:row[f'common3_p{k}']=c3[f'y{k}'].mean()
    for k in range(1,11):row[f'common10_p{k}']=c10[f'y{k}'].mean()
    row.update(moments(c10.cap10,'cap10'));row['cap10_mode']=c10.cap10.mode().iloc[0] if len(c10) else np.nan
    row['cap10_sum_probabilities']=sum(row[f'common10_p{k}'] for k in range(1,11));row['cap10_share10']=c10.y10.mean()
    row['cap10_candidates_lower_mean']=np.minimum(g.F_observed,10).mean()
    row['cap10_candidates_upper_mean']=np.where(g.right_censored,10,np.minimum(g.F_observed,10)).mean() if len(g) else np.nan
    for k in range(1,5):
        e=g[g[f'order{k+1}'] & g[f'y{k}'].eq(1)];row[f'progression{k}_{k+1}']=e[f'y{k+1}'].mean();row[f'progression{k}_{k+1}_n']=len(e)
    e=g[g.order1];row['immediate_opposite']=((e.F_exact==0)&e.breaker_direction.ne(0)).sum()/len(e) if len(e) else np.nan
    row['immediate_doji']=((e.F_exact==0)&e.breaker_direction.eq(0)).sum()/len(e) if len(e) else np.nan
    row.update(moments(g.new_leg_seconds,'new_leg_seconds'))
    return row

def path_summary(g,n,boot):
    row=support(g);row['horizon']=n
    for col,prefix in [(f'h{n}_D_q','D_q'),(f'h{n}_MAE_q','MAE_q'),(f'h{n}_MFE_q','MFE_q'),(f'h{n}_elapsed_seconds','elapsed_seconds'),
      (f'h{n}_close_delta_q','last_close_delta_q'),(f'h{n}_structural_delta_q','structural_delta_q'),(f'h{n}_mean_body_q','mean_signed_body_q'),
      (f'h{n}_D_Rspan','D_Rspan'),(f'h{n}_D_recentTR','D_recentTR'),(f'h{n}_D_MFE','D_MFE')]:row.update(moments(g[col],prefix))
    for label in ['D','MAE','MFE']:
        for unit in ['q','price','historical_ticks']:row[f'{label}_{unit}_mean']=g[f'h{n}_{label}_{unit}'].mean()
        lo,hi,u=boot.mean(g,f'h{n}_{label}_q');row.update({f'{label}_q_low':lo,f'{label}_q_high':hi,f'{label}_undefined_bootstrap':u})
    v=g[f'h{n}_D_i'];row['favourable']=v.gt(0).mean();row['flat']=v.eq(0).mean();row['adverse']=v.lt(0).mean()
    for label,value in [('favourable',v.gt(0)),('flat',v.eq(0)),('adverse',v.lt(0))]:
        ss=g[['session_date']].copy();ss['value']=value.astype(float);lo,hi,u=boot.mean(ss,'value')
        row[label+'_low']=lo;row[label+'_high']=hi
    row['break_even_cost_allowance_q']=max(0,row['D_q_mean']) if np.isfinite(row['D_q_mean']) else np.nan
    for cost in [1,2,4]:row[f'assumed_cost{cost}_mean_D_q']=row['D_q_mean']-cost;row[f'assumed_cost{cost}_positive_share']=g[f'h{n}_D_q'].gt(cost).mean()
    for minutes in [1,5,15,30]:row[f'within_{minutes}_minutes']=g[f'h{n}_elapsed_seconds'].le(minutes*60).mean()
    for tag in ['half','one']:
        for kind in ['favourable','adverse']:row[f'{kind}_{tag}_Rspan_attained']=g[f'h{n}_{kind}_{tag}_hit'].mean()
        row[f'{tag}_both_Rspan_attained']=(g[f'h{n}_favourable_{tag}_hit'].eq(True)&g[f'h{n}_adverse_{tag}_hit'].eq(True)).mean()
        row[f'{tag}_same_bar_order_unknown']=g[f'h{n}_{tag}_intrabar_order_unknown'].mean()
    row['F3_and_adverse_n']=int((g.y3.eq(1)&v.lt(0)).sum())
    row['early_break_and_favourable_n']=int((g.y3.eq(0)&v.gt(0)).sum())
    return row

def nonoverlap(g,n):
    rows=[];last=-1
    for _,r in g.sort_values('R_row').iterrows():
        entry=int(r.R_row)+1
        if entry>last:rows.append(r.name);last=int(r[f'h{n}_exit_row'])
    return g.loc[rows]

def standardized(sub,base,column,boot):
    keys=['window','era'];a=sub.groupby(keys)[column].agg(['mean','count']);b=base.groupby(keys)[column].agg(['mean','count'])
    supported=a.index.intersection(b.index);a=a.loc[supported];b=b.loc[supported]
    pooled=pd.concat([sub,base]).drop_duplicates('event_id').groupby(keys)[column].count().reindex(supported)
    weights=pooled/pooled.sum();diff=float((weights*(a['mean']-b['mean'])).sum()) if len(weights) else np.nan
    draws=[];b_draws=[]
    for key,w in weights.items():
        am=(sub.window==key[0])&(sub.era==key[1]);bm=(base.window==key[0])&(base.era==key[1])
        draws.append(w*boot.distribution(sub[am],column));b_draws.append(w*boot.distribution(base[bm],column))
    low,high,u=boot.ci(np.sum(draws,axis=0)-np.sum(b_draws,axis=0)) if draws else (np.nan,np.nan,2000)
    return {'standardized_difference':diff,'standardized_low':low,'standardized_high':high,'supported_strata':len(supported),
      'baseline_strata':len(base.groupby(keys)),'supported_subgroup_events':int(a['count'].sum()),'supported_baseline_events':int(b['count'].sum()),
      'undefined_bootstrap':u,'weights':'union of unique subgroup/reference events over common window/era strata; fixed point-estimate weights'}

def summarize(out,events,allrows,boot):
    df=events[events.primary].copy();rows=[];matrix=[];paths=[];joint=[];time=[];clock=[];extremes=[];elig=[]
    for ident,g in groups(df):
        rows.append({**ident,**continuation(g,boot)})
        counts={str(i):int(g.F_exact.eq(i).sum()) for i in range(6)}
        counts['6-7']=int(g.F_exact.between(6,7).sum());counts['8-9']=int(g.F_exact.between(8,9).sum())
        counts['10+']=int(g.F_observed.ge(10).sum());counts['unresolved']=int((g.right_censored & g.F_observed.lt(10)).sum())
        for f,n in counts.items():matrix.append({**ident,'F_bin':f,'count':n,'percentage':n/len(g) if len(g) else np.nan,'row_total':len(g)})
        for n in HORIZONS:
            ps=g[g[f'strict{n}']]
            if n==3 or ident['panel']=='all':paths.append({**ident,'cohort':'strict',**path_summary(ps,n,boot)})
            if ident['panel']=='all':
                elig.append({**ident,'horizon':n,'candidate':len(g),'order_eligible':int(g[f'order{n}'].sum()),'strict_eligible':len(ps),
                  'same_second_excluded':int((g[f'order{n}']&~g[f'strict{n}']).sum()),'boundary_excluded':int((~g[f'order{n}']).sum()),
                  'distinct_candidate_dates':g.session_date.nunique(),'zero_event_dates':len(boot.dates)-g.session_date.nunique()})
        if ident['panel']!='all':continue
        ps=g[g.strict3]
        for success in [0,1]:
            for landing in ['favourable','flat','adverse']:
                vv=ps.h3_D_i;mm=vv.gt(0) if landing=='favourable' else vv.eq(0) if landing=='flat' else vv.lt(0)
                joint.append({**ident,'F_ge3':success,'landing':landing,'n':int((ps.y3.eq(success)&mm).sum()),'denominator':len(ps)})
        for k in range(1,6):
            attained=g[g[f'y{k}'].eq(1) & g[f'strict{k}']]
            eligible=g[g[f'order{k}']];low,high,u=boot.mean(eligible,f'y{k}')
            time.append({**ident,'k':k,'candidate_n':len(g),'eligible_n':len(eligible),'attainment_probability':eligible[f'y{k}'].mean(),'low':low,'high':high,
              'bound_low':g[f'y{k}'].eq(1).sum()/len(g),'bound_high':(g[f'y{k}'].eq(1).sum()+g[f'y{k}'].isna().sum())/len(g),
              'known_attained':int(g[f'y{k}'].eq(1).sum()),'known_unattained':int(g[f'y{k}'].eq(0).sum()),'unresolved':int(g[f'y{k}'].isna().sum()),
              'strict_timed_attained_n':len(attained),'timing_rule':'strict k completion; conditional on attaining consecutive followers',**moments(attained[f'time_to{k}'],'seconds')})
        for minutes in [5,15,30]:
            marks=g[g[f'clock{minutes}_covered']];strict=marks[marks[f'clock{minutes}_strict'].eq(True)]
            for cohort,ss in [('order',marks),('strict',strict),('strict_staleness_le60',strict[strict[f'clock{minutes}_staleness']<=60])]:
                clock.append({**ident,'minutes':minutes,'cohort':cohort,'candidates':len(g),'boundary_censored':int(g[f'clock{minutes}_boundary_censored'].sum()),'no_future_completed':int((~g[f'clock{minutes}_covered']&~g[f'clock{minutes}_boundary_censored']).sum()),
                  **support(ss),'coverage':len(ss)/len(g),**moments(ss[f'clock{minutes}_D_q'],'D_q'),**moments(ss[f'clock{minutes}_staleness'],'staleness_seconds')})
        for n in [3,10]:
            ss=g[g[f'strict{n}']]
            for kind in ['MAE','MFE']:
                for bar in range(1,n+2):
                    sub=ss[ss[f'h{n}_{kind}_bar'].eq(bar)]
                    extremes.append({**ident,'horizon':n,'kind':kind,'bar':bar,**support(sub),
                      **moments(sub[f'h{n}_{kind}_time_low'],'hit_low_seconds'),**moments(sub[f'h{n}_{kind}_time_high'],'hit_high_seconds')})
    save_table(out,'continuation',rows);save_table(out,'L-F-matrix',matrix);save_table(out,'price-paths',paths)
    save_table(out,'eligibility',elig);save_table(out,'failure-landing-joint',joint);save_table(out,'time-to-followers',time)
    save_table(out,'clock-marks',clock);save_table(out,'extreme-location-intervals',extremes)
    # Explicit exact-length counts retain all L values, separate from display bins.
    exact=df.groupby(['chart','direction','L','F_exact'],dropna=False).size().reset_index(name='count');save_table(out,'exact-L-F-counts',exact)
    lifts=[];pair=[]
    for (chart,d),g in df.groupby(['chart','direction']):
        for split_ in ['all','development','validation','later']:
            base=g if split_=='all' else g[g.split==split_]
            for lb in LBINS:
                sub=base[base.L_bin==lb]
                for metric,eligibility in [('y3','order3'),('h3_D_q','strict3'),('h3_MAE_q','strict3'),('h3_MFE_q','strict3'),('h3_elapsed_seconds','strict3')]:
                    b=base[base[eligibility]];a=sub[sub[eligibility]];lo,hi,u=boot.difference(a,metric,b,metric)
                    lifts.append({'chart':chart,'direction':d,'split':split_,'L_bin':lb,'metric':metric,'sub_mean':a[metric].mean(),'baseline_mean':b[metric].mean(),
                      'difference':a[metric].mean()-b[metric].mean(),'relative_lift':a[metric].mean()/b[metric].mean()-1 if b[metric].mean()>0 else np.nan,
                      'low':lo,'high':hi,**support(a),'baseline_n':len(b),**standardized(a,b,metric,boot)})
            for metric,eligibility in [('y3','order3'),('h3_D_q','strict3')]:
                a=base[base.L_bin.eq('3') & base[eligibility]];b=base[base.L_bin.eq('2') & base[eligibility]]
                lo,hi,u=boot.difference(a,metric,b,metric);blo,bhi,bu=boot.difference(a,metric,b,metric,block=True)
                pair.append({'chart':chart,'direction':d,'split':split_,'metric':metric,'L3_minus_L2':a[metric].mean()-b[metric].mean(),'low':lo,'high':hi,'block5_low':blo,'block5_high':bhi,'n2':len(b),'n3':len(a),'undefined_bootstrap':u,**standardized(a,b,metric,boot)})
    save_table(out,'matched-L-lifts',lifts);save_table(out,'L2-L3-direct',pair)
    sens=[]
    for name,pop in [('primary',df),('include_all_original_repeated',allrows[allrows.primary]),
      ('no_prior_same_second',df[~df.prior_same_second]),('omit_long_gaps',df[~df.path_long_gap3]),('common10',df[df.strict10]),('feature_complete',df[df.feature_complete])]:
        for (chart,d),g in pop.groupby(['chart','direction']):
            for cohort in ['strict','order_same_second_descriptive']:
                ps=g[g.strict3] if cohort=='strict' else g[g.order3]
                sens.append({'sensitivity':name,'chart':chart,'direction':d,'cohort':cohort,'common3_p3':g.loc[g.order3,'y3'].mean(),**path_summary(ps,3,boot)})
    for (chart,d),g in df.groupby(['chart','direction']):
        for n in HORIZONS:
            ps=nonoverlap(g[g[f'strict{n}']],n);sens.append({'sensitivity':'nonoverlap','chart':chart,'direction':d,'cohort':'strict',**path_summary(ps,n,boot)})
            ps=g[g.strict10];sens.append({'sensitivity':'common10_horizons','chart':chart,'direction':d,'cohort':'strict',**path_summary(ps,n,boot)})
    save_table(out,'sensitivities',sens)
    missing=[];feature_rows=[];quartiles=load(out/'development-quartiles.json');features=load(out/'feature-dictionary.json')['features']
    for (chart,d),g in df.groupby(['chart','direction']):
        for f in features:
            missing.append({'chart':chart,'direction':d,'feature':f,'candidates':len(g),'defined':int(g[f].notna().sum()),'missing':int(g[f].isna().sum()),'feature_complete_n':int(g.feature_complete.sum())})
        for f,cuts in quartiles[f'{chart}:{d}'].items():
            vals=g[f].to_numpy();bins=np.searchsorted(cuts,vals,side='left');bins=np.where(np.isfinite(vals),bins,-1)
            for split_ in ['development','validation','later']:
                for bin_ in sorted(set(bins.tolist())):
                    for lb in ['all','2','3']:
                        sub=g[(bins==bin_)&g.split.eq(split_)];sub=sub if lb=='all' else sub[sub.L_bin==lb]
                        ps=sub[sub.strict3]
                        feature_rows.append({'chart':chart,'direction':d,'feature':f,'bin':'missing' if bin_==-1 else str(bin_+1),'split':split_,'L_bin':lb,**support(sub),
                          'p3':sub.loc[sub.order3,'y3'].mean(),'p3_n':int(sub.order3.sum()),'D3_q':ps.h3_D_q.mean(),'price_n':len(ps),'MAE3_q':ps.h3_MAE_q.mean(),'MFE3_q':ps.h3_MFE_q.mean(),'elapsed3_seconds':ps.h3_elapsed_seconds.mean()})
    save_table(out,'feature-coverage',missing);save_table(out,'development-binned-features',feature_rows)
    candidates=[];lock=load(out/'selection.lock.json')
    for c in lock['candidates']:
        for block in ['development','validation','later']:
            base=df[df.chart.eq(c['chart']) & df.direction.eq(c['direction']) & df.split.eq(block) & ~df.session_date.isin(lock['embargo_dates'])]
            sub=base[mask_condition(base,c)];bs=base[base.order3];ss=sub[sub.order3];ps=sub[sub.strict3]
            lo,hi,u=boot.difference(ss,'y3',bs,'y3');blo,bhi,bu=boot.difference(ss,'y3',bs,'y3',block=True)
            candidates.append({'candidate_id':c['candidate_id'],'type':c['type'],'chart':c['chart'],'direction':c['direction'],'split':block,
              'predicates':str(c['predicates']),'coverage':len(ss)/len(bs) if len(bs) else np.nan,'p3':ss.y3.mean(),'baseline_p3':bs.y3.mean(),'lift':ss.y3.mean()-bs.y3.mean(),
              'lift_low':lo,'lift_high':hi,'block5_low':blo,'block5_high':bhi,'highlight_support':len(ss)>=300 and ss.session_date.nunique()>=100,
              'p1':ss.y1.mean(),'cap10_mean':sub.cap10.mean(),'order_n':len(ss),'order_dates':ss.session_date.nunique(),**path_summary(ps,3,boot)})
            for panel in ['year','window','era']:
                for level,sb in sub.groupby(panel):
                    candidates.append({'candidate_id':c['candidate_id'],'type':c['type'],'chart':c['chart'],'direction':c['direction'],'split':block,
                      'panel':panel,'level':str(level),'p3':sb.loc[sb.order3,'y3'].mean(),'order_n':int(sb.order3.sum()),'order_dates':sb.session_date.nunique(),**path_summary(sb[sb.strict3],3,boot)})
    save_table(out,'candidate-evaluation',candidates if candidates else pd.DataFrame(columns=['candidate_id','split','p3','lift']))
    # Compact histogram evidence for computed distribution figures; no chart input or visual labels.
    distributions=[]
    for (chart,d),g in df[df.strict3].groupby(['chart','direction']):
        for column,edges in [('h3_D_q',[-np.inf,-20,-10,-5,0,5,10,20,np.inf]),('h3_MAE_q',[0,1,2,4,8,16,32,np.inf]),('h3_MFE_q',[0,1,2,4,8,16,32,np.inf]),('h3_elapsed_seconds',[0,60,300,900,1800,3600,7200,np.inf])]:
            for ix in range(len(edges)-1):
                count=int((g[column].ge(edges[ix]) & g[column].lt(edges[ix+1])).sum())
                distributions.append({'chart':chart,'direction':d,'metric':column,'bin':ix,'low':edges[ix],'high':edges[ix+1],'count':count,'denominator':len(g),'share':count/len(g)})
    save_table(out,'distributions',distributions)
    audit=events.groupby(['chart','direction','exclusion'],dropna=False).size().reset_index(name='events');save_table(out,'candidate-exclusions',audit)
    session_rows=[]
    for ch in sorted(events.chart.unique()):
        for d in [-1,1]:
            count=df[(df.chart==ch)&(df.direction==d)].groupby('session_date').size()
            for date in boot.dates:session_rows.append({'chart':ch,'direction':d,'session_date':date,'events':int(count.get(date,0))})
    save_table(out,'session-event-counts',session_rows)
    dump(out/'metrics.json',{'schema_version':'2.0.0','numeric_authority':'tables/*.csv','primary_continuation':'continuation: panel=all, complete physical windows; common3/10 columns share denominators',
      'primary_price':'price-paths: cohort=strict,horizon=3','units':'q constant product quanta; raw price separate; historical_ticks only within 6S era panels',
      'uncertainty':'2000 synchronized observed-session draws seed161001, ratio of sums, pointwise 95%; model differences also block5',
      'censoring':'known outcomes and unresolved bounds saved; exact F needs completed breaker','models':'model-paired-improvements on identical later events',
      'candidates_nominated':len(lock['candidates']),'event_count':len(events),'primary_event_count':len(df),'later_summaries_after_selection_lock':True})
