"""Independent row recounts, arithmetic identities, leakage and saved-file checks."""
from __future__ import annotations
import subprocess,sys
from pathlib import Path
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from .common import OWNER,HORIZONS,SEED,SCALE,FEATURES,load,dump,sha,save_table,roots
from .execution import check_freeze

def verify_sealed(out):
    out=Path(out).resolve();manifest=load(out/'manifest.json');assert manifest['status']=='complete'
    for name,digest in manifest['artifacts'].items():assert sha(out/name)==digest,name
    locator=load(out/'events.manifest.json');retained=roots().workspace_root/locator['workspace_relative_locator']
    assert sha(retained/'manifest.json')==locator['retained_manifest_sha256']
    for f in locator['files']:assert sha(retained/f['file'])==f['sha256'],f['file']
    print('Read-only sealed verification passed:',len(manifest['artifacts']),'artifacts and',len(locator['files']),'retained files')

def same(a,b):
    if pd.isna(a) and pd.isna(b):return True
    return bool(np.isclose(float(a),float(b),rtol=1e-10,atol=1e-10))

def price_cohort_audit(out,events):
    from .bootstrap import Bootstrap
    from .analysis import groups
    df=events[events.primary];boot=Bootstrap(load(out/'config.json')['observed_session_dates']);rows=[]
    for ident,g in groups(df):
        sub=g[g.strict3];row={**ident,'strict3_n':len(sub),'dates':sub.session_date.nunique(),'order3_n':int(g.order3.sum()),
          'strict3_coverage_of_order3':len(sub)/g.order3.sum() if g.order3.sum() else np.nan}
        for k in [1,2,3]:
            lo,hi,u=boot.mean(sub,f'y{k}');row[f'F_ge{k}']=sub[f'y{k}'].mean();row[f'F_ge{k}_low']=lo;row[f'F_ge{k}_high']=hi
        rows.append(row)
    save_table(out,'price-cohort-continuation-audit',rows)

def progression_feature_audit(out,events):
    from .bootstrap import Bootstrap
    from .analysis import groups
    df=events[events.primary];boot=Bootstrap(load(out/'config.json')['observed_session_dates']);progress=[]
    for ident,g in groups(df,panels=False):
        for k in range(1,5):
            eligible=g[g[f'order{k+1}']&g[f'y{k}'].eq(1)];lo,hi,u=boot.mean(eligible,f'y{k+1}')
            progress.append({**ident,'from_k':k,'to_k':k+1,'n':len(eligible),'dates':eligible.session_date.nunique(),
              'probability':eligible[f'y{k+1}'].mean(),'low':lo,'high':hi,'undefined_replicates':u})
    save_table(out,'progression-uncertainty-audit',progress)
    quarters=load(out/'development-quartiles.json');rows=[]
    for (chart,d),g in df.groupby(['chart','direction']):
        for feature,cuts in quarters[f'{chart}:{d}'].items():
            if not cuts:continue
            for length in ['2','3']:
                for block in ['development','validation','later']:
                    sample=g[g.L_bin.eq(length)&g.split.eq(block)];first=sample[sample[feature]<=cuts[0]];last=sample[sample[feature]>cuts[-1]]
                    for col,eligibility in [('y3','order3'),('h3_D_q','strict3')]:
                        a=last[last[eligibility]];b=first[first[eligibility]];lo,hi,u=boot.difference(a,col,b,col)
                        rows.append({'chart':chart,'direction':d,'L_bin':length,'split':block,'feature':feature,'metric':col,
                          'highest_bin_n':len(a),'lowest_bin_n':len(b),'highest_bin_dates':a.session_date.nunique(),'lowest_bin_dates':b.session_date.nunique(),
                          'highest_bin_mean':a[col].mean(),'lowest_bin_mean':b[col].mean(),'high_minus_low':a[col].mean()-b[col].mean(),
                          'low':lo,'high':hi,'undefined_replicates':u,'sparse':min(len(a),len(b))<100 or min(a.session_date.nunique(),b.session_date.nunique())<30})
    save_table(out,'feature-quartile-paired-audit',rows)
    yearly=[]
    for (chart,d,year),g in df.groupby(['chart','direction','year']):
        for col,eligibility in [('y3','order3'),('h3_D_q','strict3')]:
            a=g[g.L_bin.eq('3')&g[eligibility]];b=g[g.L_bin.eq('2')&g[eligibility]];lo,hi,u=boot.difference(a,col,b,col)
            yearly.append({'chart':chart,'direction':d,'year':year,'metric':col,'n2':len(b),'n3':len(a),'dates2':b.session_date.nunique(),'dates3':a.session_date.nunique(),
              'L2_mean':b[col].mean(),'L3_mean':a[col].mean(),'L3_minus_L2':a[col].mean()-b[col].mean(),'low':lo,'high':hi,'undefined_replicates':u})
    save_table(out,'L2-L3-yearly-audit',yearly)

def prediction_stability_audit(out,predictions,boot):
    rows=[]
    for (chart,d,target),g in predictions.groupby(['chart','direction','target']):
        for panel in ['year','window','era']:
            for level,sub in g.groupby(panel):
                by={model:gg.set_index('event_id') for model,gg in sub.groupby('model')};reference=by['B0']
                y=reference.observed.to_numpy();loss={}
                for model,gg in by.items():
                    p=gg.loc[reference.index].prediction.to_numpy()
                    if target in ['F1','F3']:
                        p=np.clip(p,1e-6,1-1e-6);v=-y*np.log(p)-(1-y)*np.log1p(-p);metric='log_loss'
                    else:v=np.abs(y-p);metric='mae'
                    loss[model]=v
                    rows.append({'chart':chart,'direction':d,'target':target,'panel':panel,'level':str(level),'model':model,'baseline':'none','metric':metric,
                      'value':v.mean(),'n':len(v),'dates':gg.session_date.nunique(),'sparse':len(v)<100 or gg.session_date.nunique()<30})
                for model,base in [('M1','B1'),('M2','M1'),('M2','B1')]:
                    v=loss[base]-loss[model];temp=pd.DataFrame({'session_date':reference.session_date.to_numpy(),'value':v});lo,hi,u=boot.mean(temp,'value')
                    rows.append({'chart':chart,'direction':d,'target':target,'panel':panel,'level':str(level),'model':model,'baseline':base,'metric':metric,
                      'value':v.mean(),'low':lo,'high':hi,'n':len(v),'dates':temp.session_date.nunique(),'sparse':len(v)<100 or temp.session_date.nunique()<30})
    save_table(out,'prediction-stability-audit',rows)

def audit_sources(out,events):
    audits=[];examples=[];example_rows=[];sample_rng=np.random.default_rng(SEED)
    for chart,ev in events.groupby('chart'):
        bars=pd.read_parquet(out/'evidence'/(chart+'-bars.parquet'));ds=bars.direction.to_numpy();n=len(bars)
        # Independent boundaries from raw flag/session arrays rather than ledger segments.
        days=bars.session_date_proxy.to_numpy();bad=bars.barrier.to_numpy();raw_path=next(x['path'] for x in load(out/'inputs.lock.json')['files'] if x['kind']=='source' and x['product']+'_'+str(x['setting_ticks'])==chart)
        raw=pd.read_csv(roots().publication_root/raw_path,sep=';',header=None,dtype=str)
        picks=[]
        for direction in [-1,1]:
            g=ev[ev.direction==direction]
            for name,mask in [('L2_F0',(g.L==2)&(g.F_exact==0)),('L3_F4',(g.L==3)&(g.F_exact==4)),
              ('L2',g.L==2),('L3',g.L==3),('F0',g.F_exact==0),('F4',g.F_exact==4),('doji_breaker',g.breaker_direction==0),
              ('unknown_start',~g.prior_known),('right_censored',g.right_censored),('same_second',g.R_same_second|g.prior_same_second),
              ('long_gap',g.path_long_gap3),('near_barrier',(g.future_boundary=='quality_barrier')&(~g.order3|g.right_censored))]:
                sub=g[mask]
                if len(sub):picks.append((name,sub.iloc[0]))
                else:audits.append({'chart':chart,'direction':direction,'case':name,'status':'not_present','event_id':None})
            for ix in sample_rng.choice(g.index,size=min(24,len(g)),replace=False):picks.append(('random',g.loc[ix]))
        seen=set()
        for case,e in picks:
            r=int(e.R_row)-1;a=r
            while a>0 and not bad[a-1] and days[a-1]==days[r]:a-=1
            b=r+1
            while b<n and not bad[b] and days[b]==days[r]:b+=1
            assert a+1==e.segment_start_row and b==e.segment_end_row
            s=r-1;p=int(ds[r-1]);d=int(ds[r]);assert p==-d and p!=0
            while s>a and ds[s-1]==p:s-=1
            known=s>a
            assert known==e.prior_known;assert (r-s)==e.L_observed
            if known:assert (r-s)==e.L
            j=r+1
            while j+1<b and ds[j]==d:j+=1
            obs=j-r-1;ended=j+1<b
            assert obs==e.F_observed and ended==pd.notna(e.F_exact)
            if ended:assert obs==e.F_exact
            for row in range(max(s-1,a),min(r+12,b)):
                source=[Decimal(v) for v in raw.iloc[row,1:5]]
                values=[int(bars.iloc[row][k+'_i']) for k in ['open','high','low','close']]
                assert values==[int(v*SCALE) for v in source]
                assert int(ds[row])==(1 if source[3]>source[0] else -1 if source[3]<source[0] else 0)
            O,H,Lo,C=[bars[k+'_i'].to_numpy() for k in ['open','high','low','close']];T=bars.timestamp_seconds.to_numpy();q=int(e.q_i)
            if known:
                span=int(max(H[s:r])-min(Lo[s:r]));distance=p*(int(C[r-1])-int(O[s]));bodies=sum(abs(int(C[k])-int(O[k])) for k in range(s,r))
                den=abs(int(C[s])-int(O[s]))+sum(abs(int(C[k])-int(C[k-1])) for k in range(s+1,r))
                assert same(distance/q,e.prior_distance_q) and same(span/q,e.prior_span_q) and same(bodies/q,e.prior_body_total_q)
                expected=abs(int(C[r-1])-int(O[s]))/den if den else np.nan;assert same(expected,e.prior_efficiency)
                mins=(int(T[r])-int(T[s]))/60;assert same((r-s)/mins if mins else np.nan,e.prior_bars_per_minute)
                rspan=int(H[r]-Lo[r]);assert same(d*(int(C[r])-int(C[r-1]))/span if span else np.nan,e.R_opposing_prior_span)
                body=np.array([abs(int(C[k])-int(O[k])) for k in range(s,r)],dtype=float)
                spans=np.array([int(H[k])-int(Lo[k]) for k in range(s,r)],dtype=float)
                upper=np.array([int(H[k])-max(int(O[k]),int(C[k])) for k in range(s,r)],dtype=float)
                lower=np.array([min(int(O[k]),int(C[k]))-int(Lo[k]) for k in range(s,r)],dtype=float)
                expected={'prior_duration_seconds':int(T[r]-T[s]),'prior_seconds_per_bar':(T[r]-T[s])/(r-s),
                  'prior_mean_body_q':body.mean()/q,'prior_median_body_q':np.median(body)/q,'prior_mean_span_q':spans.mean()/q,
                  'prior_median_span_q':np.median(spans)/q,'prior_median_body_fraction':np.median(body/spans),
                  'prior_direction_wick_fraction':np.mean((upper if p==1 else lower)/spans),
                  'prior_counter_wick_fraction':np.mean((lower if p==1 else upper)/spans),
                  'prior_distance_per_minute_q':distance/q/mins if mins else np.nan,'R_body_prior_span':abs(int(C[r])-int(O[r]))/span if span else np.nan}
                overlaps=[max(0,min(int(H[k]),int(H[k-1]))-max(int(Lo[k]),int(Lo[k-1])))/min(int(H[k]-Lo[k]),int(H[k-1]-Lo[k-1])) for k in range(s+1,r)]
                expected['prior_overlap']=np.mean(overlaps) if overlaps else np.nan
                for name,value in expected.items():assert same(value,e[name]),(e.event_id,name,value,e[name])
            rspan=int(H[r]-Lo[r]);rbody=abs(int(C[r])-int(O[r]))
            for name,value in {'R_body_q':rbody/q,'R_span_q':rspan/q,'R_body_fraction':rbody/rspan,
              'R_upper_wick_fraction':(int(H[r])-max(int(O[r]),int(C[r])))/rspan,
              'R_lower_wick_fraction':(min(int(O[r]),int(C[r]))-int(Lo[r]))/rspan,
              'R_close_location':(int(C[r])-int(Lo[r]))/rspan if d==1 else (int(H[r])-int(C[r]))/rspan,
              'R_opposing_q':d*(int(C[r])-int(C[r-1]))/q,'R_gap_q':(int(O[r])-int(C[r-1]))/q,
              'R_duration_seconds':int(T[r+1]-T[r])}.items():assert same(value,e[name])
            for window_ in [10,20]:
                if r-a>=window_:
                    pairs=[(int(ds[k-1]),int(ds[k])) for k in range(r-window_+1,r) if ds[k-1]!=0 and ds[k]!=0]
                    value=sum(x!=y for x,y in pairs)/len(pairs) if pairs else np.nan
                    assert same(value,e[f'chop{window_}']);assert len(pairs)==e[f'chop{window_}_pairs']
            if r-a>=21:
                tr=[max(int(H[k]-Lo[k]),abs(int(H[k])-int(C[k-1])),abs(int(Lo[k])-int(C[k-1]))) for k in range(r-20,r)]
                assert same(np.median(tr)/q,e.recent20_tr_q)
            # Independently enumerate completed legs before the immediate prior leg.
            legs=[];cursor=a
            while cursor<s:
                if ds[cursor]==0:cursor+=1;continue
                end=cursor+1
                while end<s and ds[end]==ds[cursor]:end+=1
                if end<s or end==s:legs.append((end-cursor,cursor>a))
                cursor=end
            for k in range(1,4):
                expected=legs[-k][0] if len(legs)>=k and legs[-k][1] else np.nan
                assert same(expected,e[f'previous_leg_{k}']),(e.event_id,k,expected,e[f'previous_leg_{k}'])
            for h in HORIZONS:
                eligible=(r+h+1)<b;assert eligible==e[f'order{h}']
                strict=eligible and all(T[k+1]>T[k] for k in range(r,r+h+1));assert strict==e[f'strict{h}']
                if not eligible:continue
                entry=int(O[r+1]);exit_=int(O[r+h+1]);D=d*(exit_-entry)
                prices=[entry,exit_]+[int(v) for v in H[r+1:r+h+1]]+[int(v) for v in Lo[r+1:r+h+1]]
                signed=[d*(v-entry) for v in prices];MFE=max(0,*signed);MAE=max(0,*[-v for v in signed])
                assert D==e[f'h{h}_D_i'] and MFE==e[f'h{h}_MFE_i'] and MAE==e[f'h{h}_MAE_i']
                assert r+h+2==e[f'h{h}_exit_row'];assert int(T[r+h+1]-T[r+1])==e[f'h{h}_elapsed_seconds']
                assert same(D/q,e[f'h{h}_D_q']);assert same(D/SCALE,e[f'h{h}_D_price'])
            for minute in [5,15,30]:
                target=int(T[r+1])+minute*60;observed=int(T[b-1])>=target
                possible=[k for k in range(r+1,b-1) if T[k+1]<=target]
                covered=observed and bool(possible)
                assert covered==e[f'clock{minute}_covered'];assert (not observed)==e[f'clock{minute}_boundary_censored']
                if covered:
                    k=possible[-1];assert k+1==e[f'clock{minute}_bar_row'];assert target-T[k+1]==e[f'clock{minute}_staleness']
                    assert same(d*(int(C[k])-int(O[r+1]))/q,e[f'clock{minute}_D_q'])
            audits.append({'chart':chart,'direction':d,'case':case,'event_id':e.event_id,'R_row':r+1,'L':e.L,'F':e.F_exact,'F_lower':obs,'status':'pass'})
            if case in ['L2_F0','L3_F4','L2','L3','F0','F4'] and (d,case) not in seen:
                seen.add((d,case));examples.append({'chart':chart,'direction':d,'case':case,'event_id':e.event_id,'L':e.L,'F':e.F_exact})
                for k in range(s,min(r+7,b)):
                    example_rows.append({'chart':chart,'direction':d,'case':case,'event_id':e.event_id,'source_row':k+1,'relative_bar':k-r,
                      'open_price':O[k]/SCALE,'high_price':H[k]/SCALE,'low_price':Lo[k]/SCALE,'close_price':C[k]/SCALE,
                      'timestamp':bars.bar_start_timestamp.iloc[k],'completed':k+1<b})
    save_table(out,'source-row-audits',audits);save_table(out,'source-examples',examples);save_table(out,'source-example-bars',example_rows)
    return audits

class ReportParser(HTMLParser):
    def __init__(self):super().__init__();self.refs=[];self.values=[];self.ids=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        for n in ['href','src']:
            if n in a:self.refs.append(a[n])
        if 'data-table' in a:self.values.append(a)

def verify_report(out):
    parser=ReportParser();parser.feed((out/'report.html').read_text());assert len(parser.ids)==len(set(parser.ids))
    tables={}
    for a in parser.values:
        name=a['data-table']
        if name not in tables:tables[name]=pd.read_csv(out/'tables'/(name+'.csv'))
        expected=tables[name].iloc[int(a['data-row'])][a['data-column']]
        value=a['data-value'];assert (value=='null' and pd.isna(expected)) or same(float(value),expected),(a,expected)
    for ref in parser.refs:
        u=urlsplit(ref);assert not u.scheme and not u.netloc,'Report must be offline/local'
        if u.path:assert (out/unquote(u.path)).exists(),ref
        elif u.fragment:assert u.fragment in parser.ids,ref
    import re
    markdown=(out/'report.md').read_text()
    for target in re.findall(r'\]\(([^)]+)\)',markdown):
        u=urlsplit(target);assert not u.scheme and not u.netloc;assert (out/unquote(u.path)).exists(),target
    figures=[]
    for p in (out/'figures').glob('*.svg'):
        root=ET.parse(p).getroot();assert root.tag.endswith('svg');assert root.attrib.get('viewBox')
        for node in root.iter():
            if node.tag.endswith('metadata') and node.text:
                import json
                meta=json.loads(node.text)
                for source in meta.get('sources',[]):
                    name=source['table']
                    if name not in tables:tables[name]=pd.read_csv(out/'tables'/(name+'.csv'))
                    expected=tables[name].iloc[source['row']][source['column']]
                    assert (source['value'] is None and pd.isna(expected)) or same(source['value'],expected),(p,source)
        figures.append({'file':str(p.relative_to(out)),'sha256':sha(p),'status':'pass'})
    dump(out/'report-verification.json',{'status':'pass','displayed_values_reconciled':len(parser.values),'local_refs_verified':len(parser.refs),'svg_assets':len(figures),
      'figures':figures,'html_sha256':sha(out/'report.html'),'markdown_sha256':sha(out/'report.md'),'gui_used':False})

def verify(out):
    out=Path(out).resolve();check_freeze(out);events=pd.read_parquet(out/'evidence'/'events.parquet');primary=events[events.primary]
    assert events.event_id.is_unique;assert np.all(events.max_feature_source_row==events.R_row)
    assert not primary.session_date.isin(['2017-07-21','2026-10-01']).any();assert primary.L.notna().all()
    for k in range(1,11):
        e=primary[primary[f'order{k}']];assert e[f'y{k}'].notna().all()
        assert np.all(e[f'y{k}']==(e.F_observed>=k));assert np.all(primary[f'strict{k}']<=primary[f'order{k}'])
    for f in FEATURES:assert np.array_equal(events['undefined_'+f],events[f].isna())
    for h in HORIZONS:
        e=primary[primary[f'order{h}']]
        assert (e[f'h{h}_MAE_i']>=0).all() and (e[f'h{h}_MFE_i']>=0).all()
        assert np.all(e[f'h{h}_MFE_i']>=np.maximum(e[f'h{h}_D_i'],0))
        assert np.all(e[f'h{h}_MAE_i']>=np.maximum(-e[f'h{h}_D_i'],0))
        assert np.all(e[f'h{h}_exit_row']==e.R_row+h+1)
        assert np.allclose(e[f'h{h}_D_price']*SCALE,e[f'h{h}_D_i'])
    for a,b in zip(HORIZONS[:-1],HORIZONS[1:]):
        e=primary[primary[f'order{b}']]
        assert np.all(e[f'h{b}_MAE_i']>=e[f'h{a}_MAE_i']);assert np.all(e[f'h{b}_MFE_i']>=e[f'h{a}_MFE_i'])
    c=pd.read_csv(out/'tables'/'continuation.csv');valid=c.common10_n>0
    assert np.allclose(c.loc[valid,'cap10_mean'],c.loc[valid,'cap10_sum_probabilities'],rtol=1e-10,atol=1e-10)
    for i in range(1,10):assert np.all(c.loc[valid,f'common10_p{i}']>=c.loc[valid,f'common10_p{i+1}']-1e-12)
    for i in [1,2]:assert np.all(c.loc[c.common3_n>0,f'common3_p{i}']>=c.loc[c.common3_n>0,f'common3_p{i+1}']-1e-12)
    m=pd.read_csv(out/'tables'/'L-F-matrix.csv');totals=m.groupby(['chart','direction','panel','level'],dropna=False).agg(n=('count','sum'),expected=('row_total','first'))
    assert np.array_equal(totals.n,totals.expected)
    for k in [1,2,3,4,5,10]:assert np.array_equal(c[f'p{k}_known_success']+c[f'p{k}_known_failure']+c[f'p{k}_unresolved'],c.candidate_n)
    audits=audit_sources(out,events)
    price_cohort_audit(out,events)
    progression_feature_audit(out,events)
    predictions=pd.read_parquet(out/'evidence'/'predictions.parquet');assert predictions.observed.notna().all() and predictions.prediction.notna().all()
    for key,g in predictions.groupby(['chart','direction','target']):
        assert g.groupby('event_id').size().eq(4).all();assert g.groupby('event_id')['observed'].nunique().eq(1).all()
    for target in ['F1','F3']:assert predictions[predictions.target==target].prediction.between(0,1).all()
    assert predictions[predictions.target=='cap10'].prediction.between(0,10).all()
    lock=load(out/'selection.lock.json');assert len(lock['candidates'])<=3;assert lock['later_outcome_summaries_read'] is False
    assert (out/'freeze.json').stat().st_mtime <= (out/'evidence'/'events.parquet').stat().st_mtime
    assert (out/'selection.lock.json').stat().st_mtime <= (out/'evidence'/'predictions.parquet').stat().st_mtime <= (out/'tables'/'continuation.csv').stat().st_mtime
    leak=pd.read_csv(out/'tables'/'split-leakage.csv');assert (leak.train_latest_outcome<leak.later_first_available).all()
    embargo=load(out/'config.json')['embargo_dates'];assert not predictions.session_date.isin(embargo).any()
    assert sha(out/'development-quartiles.json')==lock['quartiles_sha256']
    assert sha(out/'candidate-selection-history.json')==lock['selection_history_sha256']
    settings=load(out/'final-model-settings.json');transform=load(out/'config.json')['model_nonnegative_log1p_features']
    eligible=primary[~primary.session_date.isin(embargo)]
    from .models import TARGETS
    for (chart,d,target,model),g in predictions.groupby(['chart','direction','target','model']):
        specification=settings[f'{chart}:{d}:{target}:{model}'];elig,label,binary=TARGETS[target]
        original=eligible[eligible.chart.eq(chart)&eligible.direction.eq(d)&eligible[elig]]
        train=original[original.split!='later'];test=original.set_index('event_id').loc[g.event_id]
        if model=='B0':expected=np.full(len(test),train[label].mean());assert same(specification['constant'],train[label].mean())
        else:
            pre=specification['preprocessing'];data={};med=pre['median'];center=pre['mean'];scale=pre['scale']
            for j,name in enumerate(pre['numeric']):
                tr=train[name].to_numpy(float);te=test[name].to_numpy(float)
                if name in transform:tr=np.log1p(np.maximum(0,tr));te=np.log1p(np.maximum(0,te))
                missing=~np.isfinite(te);finite=tr[np.isfinite(tr)];assert same(med[j],np.median(finite) if len(finite) else 0)
                data[name]=(np.where(missing,med[j],te)-center[j])/scale[j];data['missing_'+name]=missing.astype(float)
            cols=[np.ones(len(test))]
            for column in pre['columns'][1:]:
                if '=' in column:
                    name,category=column.split('=',1);cols.append(test[name].eq(category).to_numpy(float))
                else:cols.append(data[column])
            z=np.column_stack(cols)@np.array(specification['coefficients'])
            expected=1/(1+np.exp(-np.clip(z,-700,700))) if binary else z
            if target=='cap10':expected=np.clip(expected,0,10)
        assert np.allclose(expected,g.prediction.to_numpy(),rtol=1e-10,atol=1e-10),'Saved preprocessing/prediction mismatch'
    # Independent loss recomputation from event predictions on every later model.
    scores=pd.read_csv(out/'tables'/'model-scores.csv');paired=pd.read_csv(out/'tables'/'model-paired-improvements.csv')
    for (chart,d,target,model),g in predictions.groupby(['chart','direction','target','model']):
        y=g.observed.to_numpy();p=g.prediction.to_numpy()
        expected={'brier':np.mean((y-p)**2),'log_loss':np.mean(-y*np.log(np.clip(p,1e-6,1-1e-6))-(1-y)*np.log(1-np.clip(p,1e-6,1-1e-6)))} if target in ['F1','F3'] else {'mae':np.abs(y-p).mean(),'mse':np.mean((y-p)**2)}
        sub=scores[(scores.chart==chart)&(scores.direction==d)&(scores.target==target)&(scores.model==model)]
        for metric,val in expected.items():assert same(sub[sub.metric==metric].value.iloc[0],val)
    from .bootstrap import Bootstrap
    weights=np.load(out/'evidence'/'bootstrap-weights.npz');boot=Bootstrap(load(out/'config.json')['observed_session_dates'])
    assert np.array_equal(weights['session'],boot.weights) and np.array_equal(weights['block5'],boot.blocks)
    prediction_stability_audit(out,predictions,boot)
    block_rows=[]
    for (chart,d),g in primary.groupby(['chart','direction']):
        for column,eligible_ in [('y1','order3'),('y3','order3'),('cap10','order10'),('h3_D_q','strict3'),('h3_MAE_q','strict3'),('h3_MFE_q','strict3'),('h3_elapsed_seconds','strict3')]:
            sample=g[g[eligible_]];lo,hi,u=boot.mean(sample,column);blo,bhi,bu=boot.mean(sample,column,block=True)
            block_rows.append({'chart':chart,'direction':d,'metric':column,'n':len(sample),'dates':sample.session_date.nunique(),'mean':sample[column].mean(),
              'session_low':lo,'session_high':hi,'block5_low':blo,'block5_high':bhi,'undefined_session':u,'undefined_block5':bu})
    save_table(out,'block5-primary-audit',block_rows)
    candidate_denominators=[];candidate_differences=[]
    from .models import mask_condition
    for candidate in lock['candidates']:
        matched=eligible[mask_condition(eligible,candidate)]
        for split_,g in matched.groupby('split'):
            candidate_denominators.append({'candidate_id':candidate['candidate_id'],'split':split_,'candidate_n':len(g),'order3_n':int(g.order3.sum()),
              'cap10_n':int(g.order10.sum()),'strict3_n':int(g.strict3.sum()),'dates':g.session_date.nunique()})
            base=eligible[eligible.chart.eq(candidate['chart'])&eligible.direction.eq(candidate['direction'])&eligible.split.eq(split_)]
            for column,eligibility in [('y1','order3'),('y3','order3'),('cap10','order10'),('h3_D_q','strict3'),('h3_MAE_q','strict3'),('h3_MFE_q','strict3'),('h3_elapsed_seconds','strict3')]:
                a=g[g[eligibility]];b=base[base[eligibility]];lo,hi,u=boot.difference(a,column,b,column)
                candidate_differences.append({'candidate_id':candidate['candidate_id'],'split':split_,'metric':column,'candidate_n':len(a),'baseline_n':len(b),
                  'candidate_dates':a.session_date.nunique(),'candidate_mean':a[column].mean(),'baseline_mean':b[column].mean(),
                  'difference':a[column].mean()-b[column].mean(),'low':lo,'high':hi,'undefined_replicates':u})
    save_table(out,'candidate-denominators',candidate_denominators if candidate_denominators else pd.DataFrame(columns=['candidate_id','split','candidate_n','order3_n','cap10_n','strict3_n','dates']))
    save_table(out,'candidate-matched-differences',candidate_differences if candidate_differences else pd.DataFrame(columns=['candidate_id','split','metric','candidate_n','baseline_n','candidate_dates','candidate_mean','baseline_mean','difference','low','high']))
    ci_audits=[]
    for ix,r in paired.groupby(['chart','direction','target']).head(1).iterrows():
        g=predictions[(predictions.chart==r.chart)&(predictions.direction==r.direction)&(predictions.target==r.target)]
        a=g[g.model==r.model].set_index('event_id');b=g[g.model==r.baseline].set_index('event_id').loc[a.index]
        y=a.observed.to_numpy();pa=a.prediction.to_numpy();pb=b.prediction.to_numpy()
        def loss(p):
            if r.metric=='brier':return (y-p)**2
            if r.metric=='log_loss':p=np.clip(p,1e-6,1-1e-6);return -y*np.log(p)-(1-y)*np.log1p(-p)
            if r.metric=='mae':return np.abs(y-p)
            return (y-p)**2
        values=loss(pb)-loss(pa)
        ss=np.zeros(len(boot.dates));nn=np.zeros(len(boot.dates))
        for date,v in zip(a.session_date,values):i=boot.index[date];ss[i]+=v;nn[i]+=1
        denominator=weights['session']@nn;numerator=weights['session']@ss
        lo,hi=np.quantile(numerator/denominator,[.025,.975]);assert same(lo,r.low) and same(hi,r.high)
        ci_audits.append({'chart':r.chart,'direction':r.direction,'target':r.target,'model':r.model,'metric':r.metric,'status':'pass'})
    save_table(out,'independent-bootstrap-audit',ci_audits)
    for entry in [load(out/'inputs.lock.json')['manifest'],load(out/'inputs.lock.json')['tracked_manifest_mirror'],*load(out/'inputs.lock.json')['files'],*load(out/'inputs.lock.json')['supporting_artifacts']]:
        base=roots().workspace_root if entry['path'].startswith('docs/') else roots().publication_root
        assert sha(base/entry['path'])==entry['sha256'],'Input preservation'
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(OWNER/'tests'),'-v'],capture_output=True,text=True)
    (out/'provenance'/'final-tests.txt').write_text(tests.stdout+tests.stderr);assert tests.returncode==0,tests.stderr
    verify_report(out)
    dump(out/'verification.json',{'status':'pass','event_rows':len(events),'primary_rows':len(primary),'prediction_rows':len(predictions),
      'source_recounts_pass':sum(r['status']=='pass' for r in audits),'source_cases_absent':sum(r['status']=='not_present' for r in audits),
      'independent_bootstrap_intervals':len(ci_audits),'checks':['synthetic long/short tests','real-source Decimal recounts','F/censor/denominator identities',
       'known-at-decision features','B4 exits and gaps','nested nonnegative excursions','units and clock staleness','synchronized splits/purge/embargo',
       'identical model rows and scores','paired bootstrap independent recomputation','report values/links/SVG','input hashes preserved'],
      'gui_or_browser_used':False,'numerical_freeze_unchanged':True})
    print('Independent numerical, source-row, model, uncertainty and offline report verification passed.',flush=True)
