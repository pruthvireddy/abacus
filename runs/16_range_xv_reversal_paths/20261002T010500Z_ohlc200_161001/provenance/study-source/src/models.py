"""Bounded deterministic logistic/ridge comparisons; later labels read after selection lock."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .common import NUMERIC_B1,NUMERIC_M1,FEATURES,WINDOWS,LBINS,SEED,load,dump,sha,now,save_table

PENALTIES=[.1,1.,10.]
TRANSFORM=[n for n in FEATURES if n.endswith('_seconds') or n.endswith('_q') and n not in ['R_gap_q','R_opposing_q'] or n in ['prior_seconds_per_bar','prior_bars_per_minute']]

def sigmoid(z):
    return 1/(1+np.exp(-np.clip(z,-700,700)))

def preprocess(train,test,names,with_L=False):
    x=train[names].to_numpy(float);z=test[names].to_numpy(float)
    for j,n in enumerate(names):
        if n in TRANSFORM:x[:,j]=np.log1p(np.maximum(0,x[:,j]));z[:,j]=np.log1p(np.maximum(0,z[:,j]))
    miss=~np.isfinite(x);zm=~np.isfinite(z)
    med=np.array([np.median(x[np.isfinite(x[:,j]),j]) if np.isfinite(x[:,j]).any() else 0. for j in range(x.shape[1])])
    x=np.where(miss,med,x);z=np.where(zm,med,z)
    mean=x.mean(0);sd=x.std(0);sd=np.where(sd>1e-12,sd,1.)
    x=np.c_[(x-mean)/sd,miss.astype(float)];z=np.c_[(z-mean)/sd,zm.astype(float)]
    cols=names+['missing_'+n for n in names]
    for n in ['window','era']+(['compact_L'] if with_L else []):
        cats=sorted(train[n].unique().tolist())
        # Training-observed vocabulary only. Unknown categories encode the reference level.
        for cat in cats[1:]:
            x=np.c_[x,(train[n]==cat).astype(float)];z=np.c_[z,(test[n]==cat).astype(float)];cols.append(n+'='+cat)
    keep=x.std(0)>1e-12;cols=[n for n,k in zip(cols,keep) if k]
    return np.c_[np.ones(len(x)),x[:,keep]],np.c_[np.ones(len(z)),z[:,keep]],{'numeric':names,'median':med,'mean':mean,'scale':sd,'columns':['intercept']+cols,'keep':keep.tolist(),'unseen':'all-zero non-reference dummies; training reference','transform':TRANSFORM}

def fit(X,y,penalty,binary):
    n,p=X.shape;diag=np.ones(p)*penalty;diag[0]=0
    if not binary:
        b=np.linalg.solve(X.T@X+np.diag(diag),X.T@y)
        return b,{'iterations':1,'converged':True,'normalization':'sum squared errors + lambda*sum(beta^2); intercept unpenalized'}
    b=np.zeros(p);mean=np.clip(y.mean(),1e-6,1-1e-6);b[0]=np.log(mean/(1-mean))
    def obj(v):return float(np.sum(np.logaddexp(0,X@v)-y*(X@v))+.5*np.sum(diag*v*v))
    converged=False
    for it in range(80):
        pr=sigmoid(X@b);g=X.T@(pr-y)+diag*b;w=np.maximum(pr*(1-pr),1e-12)
        step=np.linalg.solve(X.T@(w[:,None]*X)+np.diag(diag)+np.eye(p)*1e-10,g)
        rate=1.;old=obj(b)
        while rate>2**-24 and obj(b-rate*step)>old-1e-4*rate*float(g@step):rate*=.5
        b-=rate*step
        if np.max(np.abs(rate*step))<1e-8 or np.max(np.abs(g))/n<1e-9:converged=True;break
    if not converged:raise RuntimeError(f'Logistic nonconvergence: iterations={it+1}, grad={np.max(np.abs(g))/n}')
    return b,{'iterations':it+1,'converged':converged,'normalization':'sum binary log loss + lambda/2*sum(beta^2); intercept unpenalized'}

def losses(y,p,binary):
    if binary:
        p=np.clip(p,1e-6,1-1e-6)
        return {'brier':(y-p)**2,'log_loss':-y*np.log(p)-(1-y)*np.log1p(-p)}
    return {'mae':np.abs(y-p),'mse':(y-p)**2}

def auc(y,p):
    positives=y.sum();negatives=len(y)-positives
    if positives==0 or negatives==0:return np.nan
    rank=pd.Series(p).rank(method='average').to_numpy()
    return float((rank[y==1].sum()-positives*(positives+1)/2)/(positives*negatives))

TARGETS={'F3':('order3','y3',True),'F1':('order3','y1',True),'D3':('strict3','h3_D_q',False),'cap10':('order10','cap10',False)}
def nominal_pool(quartiles):
    pool=[]
    for key in sorted(quartiles):
        chart,direction=key.split(':');direction=int(direction)
        for lb in LBINS:pool.append({'type':'length_only','chart':chart,'direction':direction,'predicates':[['L_bin','eq',lb]]})
        for lb in ['2','3','5','6','7']:
            for f in ['prior_bars_per_minute','prior_efficiency','chop20']:
                cuts=quartiles[key][f]
                if not cuts:continue
                for op,cut in [('le',cuts[0]),('gt',cuts[-1])]:
                    pred=[['L_bin','eq',lb],[f,op,cut]]
                    pool.append({'type':'length_plus_context','chart':chart,'direction':direction,'predicates':pred})
                    rc=quartiles[key]['R_body_prior_span']
                    if rc:pool.append({'type':'adding_R_geometry','chart':chart,'direction':direction,'predicates':pred+[['R_body_prior_span','gt',rc[-1]]]})
    return pool

def mask_condition(df,c):
    m=(df.chart==c['chart'])&(df.direction==c['direction'])
    for n,op,x in c['predicates']:
        m &= df[n].eq(x) if op=='eq' else df[n].le(x) if op=='le' else df[n].gt(x)
    return m

def select(out,events,boot):
    assert not (out/'selection.lock.json').exists(),'Selection is immutable within this run'
    cfg=load(out/'config.json');embargo=cfg['embargo_dates']
    # Explicitly discard later data here; no later aggregates or feature transforms are evaluated.
    early=events[events.primary & events.split.ne('later') & ~events.session_date.isin(embargo)].copy()
    quarters={}
    for (chart,d),g in early[early.split=='development'].groupby(['chart','direction']):
        quarters[f'{chart}:{d}']={n:sorted(set(g[n].dropna().quantile([.25,.5,.75]).tolist())) for n in load(out/'feature-dictionary.json')['quartile_features']}
    dump(out/'development-quartiles.json',quarters)
    settings={};history=[];solver=[]
    for (chart,d),g in early.groupby(['chart','direction']):
        for target,(elig,label,binary) in TARGETS.items():
            subset=g[g[elig]];train=subset[subset.split=='development'];val=subset[subset.split=='validation']
            assert len(train)>0 and len(val)>0
            y=train[label].to_numpy(float);yv=val[label].to_numpy(float);assert np.isfinite(y).all() and np.isfinite(yv).all()
            base=np.full(len(yv),y.mean());s=losses(yv,base,binary)
            history.append({'chart':chart,'direction':d,'target':target,'model':'B0','penalty':0.,'validation_score':np.mean(s['log_loss' if binary else 'mae']),'train_n':len(train),'validation_n':len(val)})
            for model,names in [('B1',NUMERIC_B1),('M1',NUMERIC_M1),('M2',FEATURES)]:
                X,V,pre=preprocess(train,val,names,model!='B1');choices=[]
                for penalty in PENALTIES:
                    coef,diag=fit(X,y,penalty,binary);p=sigmoid(V@coef) if binary else V@coef
                    if target=='cap10':p=np.clip(p,0,10)
                    score=float(np.mean(losses(yv,p,binary)['log_loss' if binary else 'mae']))
                    choices.append((score,penalty));history.append({'chart':chart,'direction':d,'target':target,'model':model,'penalty':penalty,'validation_score':score,'train_n':len(train),'validation_n':len(val)})
                    solver.append({'chart':chart,'direction':d,'target':target,'model':model,'penalty':penalty,**diag})
                settings[f'{chart}:{d}:{target}:{model}']=min(choices)[1]
    candidates=[];c_history=[]
    for i,c in enumerate(nominal_pool(quarters)):
        key=(early.chart==c['chart'])&(early.direction==c['direction'])&early.order3
        comparisons={};supported=True
        for block in ['development','validation']:
            base=early[key & early.split.eq(block)];sub=base[mask_condition(base,c)]
            n=len(sub);nd=sub.session_date.nunique();diff=sub.y3.mean()-base.y3.mean()
            comparisons[block]={'n':n,'dates':nd,'coverage':n/len(base) if len(base) else np.nan,'p3':sub.y3.mean(),'baseline_p3':base.y3.mean(),'lift':diff}
            for label in ['h3_D_q','h3_MAE_q','h3_MFE_q','h3_elapsed_seconds']:
                ps=sub[sub.strict3];comparisons[block][label]=ps[label].mean()
            if n<300 or nd<100 or not diff>0:supported=False
        val=early[key & early.split.eq('validation')];sub=val[mask_condition(val,c)]
        if supported:
            lo,hi,undefined=boot.difference(sub,'y3',val,'y3');comparisons['validation'].update(lift_low=lo,lift_high=hi,undefined_bootstrap=undefined)
            supported=lo>0
        record={'candidate_id':f'C{i:04d}',**c,'development':comparisons['development'],'validation':comparisons['validation'],'supported_for_nomination':supported}
        c_history.append(record)
        if supported:candidates.append(record)
    nominated=[]
    for kind in ['length_only','length_plus_context','adding_R_geometry']:
        choices=[c for c in candidates if c['type']==kind]
        if choices:
            best=sorted(choices,key=lambda c:(-c['validation']['lift_low'],-c['validation']['n'],c['candidate_id']))[0]
            nominated.append(best)
    save_table(out,'model-validation',history);save_table(out,'solver-validation',solver)
    dump(out/'candidate-selection-history.json',c_history)
    lock={'protocol':'2.0.0','frozen_at_utc':now(),'later_outcome_summaries_read':False,'penalties':settings,
      'quartiles_sha256':sha(out/'development-quartiles.json'),'candidates':nominated,'candidates_evaluated':len(c_history),
      'candidate_support':'positive development and validation F3 lift; >=300 events/100 dates in each; validation synchronized CI low>0',
      'selection_history_sha256':sha(out/'candidate-selection-history.json'),'prior_inspection':'Planning input/quality checks and prior studies inspected; no pristine holdout claim.',
      'regularization':'summed loss + lambda penalty, intercept excluded','solver':'deterministic Newton line search max80; step 1e-8 or mean-gradient 1e-9; ridge exact solve',
      'final_fit':'development+validation, embargoed synchronized sessions removed; all models same target rows',
      'condition_max':3,'preprocessing':'training medians/scales/missing flags; nonnegative sizes/durations log1p; fixed feature lists; train-observed categories',
      'targets':TARGETS,'embargo_dates':embargo}
    dump(out/'selection.lock.json',lock)
    return lock

def evaluate(out,events,boot):
    lock=load(out/'selection.lock.json');assert lock['later_outcome_summaries_read'] is False
    cfg=load(out/'config.json');df=events[events.primary & ~events.session_date.isin(cfg['embargo_dates'])]
    predictions=[];scores=[];calibration=[];paired=[];final_settings={};leakage=[]
    for (chart,d),g in df.groupby(['chart','direction']):
        for target,(elig,label,binary) in TARGETS.items():
            targetdf=g[g[elig]];train=targetdf[targetdf.split!='later'];test=targetdf[targetdf.split=='later']
            horizon=10 if target=='cap10' else 3
            assert train[f'h{horizon}_exit_time'].max()<test.available_at.min(),'outcome-window leakage'
            leakage.append({'chart':chart,'direction':d,'target':target,'train_n':len(train),'later_n':len(test),
              'train_latest_available':train.available_at.max(),'train_latest_outcome':train[f'h{horizon}_exit_time'].max(),
              'later_first_available':test.available_at.min(),'identical_model_event_set':True,'status':'pass'})
            y=train[label].to_numpy(float);yt=test[label].to_numpy(float);model_predictions={};baseline_losses={}
            for model,names in [('B0',[]),('B1',NUMERIC_B1),('M1',NUMERIC_M1),('M2',FEATURES)]:
                if model=='B0':raw=np.full(len(test),y.mean());details={'constant':y.mean()}
                else:
                    X,V,pre=preprocess(train,test,names,model!='B1');penalty=lock['penalties'][f'{chart}:{d}:{target}:{model}']
                    coef,diag=fit(X,y,penalty,binary);raw=sigmoid(V@coef) if binary else V@coef
                    details={'preprocessing':pre,'coefficients':coef,'penalty':penalty,'solver':diag}
                final_settings[f'{chart}:{d}:{target}:{model}']=details
                p=np.clip(raw,0,10) if target=='cap10' else raw;model_predictions[model]=p
                row=test[['event_id','session_date','year','window','era','feature_complete']].copy()
                row['chart']=chart;row['direction']=d;row['target']=target;row['model']=model;row['observed']=yt;row['prediction']=p;row['unclipped_prediction']=raw
                predictions.append(row);loss=losses(yt,p,binary);baseline_losses[model]=loss
                for metric,values in loss.items():
                    temp=pd.DataFrame({'session_date':test.session_date.to_numpy(),'value':values})
                    lo,hi,u=boot.mean(temp,'value')
                    scores.append({'chart':chart,'direction':d,'target':target,'model':model,'cohort':'all','metric':metric,'value':values.mean(),'low':lo,'high':hi,'undefined_replicates':u,'n':len(test),'dates':test.session_date.nunique(),'rmse':np.sqrt(values.mean()) if metric=='mse' else np.nan,'auc':auc(yt,p) if binary else np.nan,'unclipped_mae':np.abs(yt-raw).mean() if target=='cap10' else np.nan})
                    fm=test.feature_complete.to_numpy();ft=temp[fm];flo,fhi,fu=boot.mean(ft,'value')
                    scores.append({'chart':chart,'direction':d,'target':target,'model':model,'cohort':'feature_complete','metric':metric,'value':values[fm].mean() if fm.any() else np.nan,'low':flo,'high':fhi,'undefined_replicates':fu,'n':int(fm.sum()),'dates':ft.session_date.nunique(),'rmse':np.sqrt(values[fm].mean()) if metric=='mse' and fm.any() else np.nan,'auc':auc(yt[fm],p[fm]) if binary and fm.any() else np.nan})
                bins=np.minimum((p*10).astype(int),9) if binary else pd.Series(p).rank(method='first',pct=True).mul(10).clip(upper=9).astype(int).to_numpy()
                for bin_ in range(10):
                    m=bins==bin_;calibration.append({'chart':chart,'direction':d,'target':target,'model':model,'bin':bin_, 'n':int(m.sum()),'mean_prediction':p[m].mean() if m.any() else np.nan,'mean_observed':yt[m].mean() if m.any() else np.nan})
            for model,base in [('B1','B0'),('M1','B1'),('M2','M1'),('M2','B1'),('M1','B0'),('M2','B0')]:
                for metric in baseline_losses[model]:
                    delta=baseline_losses[base][metric]-baseline_losses[model][metric]
                    temp=pd.DataFrame({'session_date':test.session_date.to_numpy(),'delta':delta});lo,hi,u=boot.mean(temp,'delta');blo,bhi,bu=boot.mean(temp,'delta',block=True)
                    paired.append({'chart':chart,'direction':d,'target':target,'model':model,'baseline':base,'metric':metric,
                     'improvement':delta.mean(),'low':lo,'high':hi,'block5_low':blo,'block5_high':bhi,'undefined_replicates':u,'n':len(test),'dates':test.session_date.nunique()})
    pred=pd.concat(predictions,ignore_index=True);pred.to_parquet(out/'evidence'/'predictions.parquet',index=False)
    save_table(out,'model-scores',scores);save_table(out,'model-calibration',calibration);save_table(out,'model-paired-improvements',paired)
    save_table(out,'split-leakage',leakage);dump(out/'final-model-settings.json',final_settings)
    # Adjustment of L=2 versus L=3 on later common rows: prediction-fixed R/context expectations.
    adjustment=[]
    f3=pred[pred.target=='F3'].merge(events[['event_id','L_bin']],on='event_id',validate='many_to_one')
    for (ch,d,model),g in f3.groupby(['chart','direction','model']):
        g=g.copy();g['residual']=g.observed-g.prediction;a=g[g.L_bin=='2'];b=g[g.L_bin=='3']
        lo,hi,u=boot.difference(b,'residual',a,'residual')
        adjustment.append({'chart':ch,'direction':d,'model':model,'L3_minus_L2_observed':b.observed.mean()-a.observed.mean(),
          'L3_minus_L2_predicted':b.prediction.mean()-a.prediction.mean(),'L3_minus_L2_residual':b.residual.mean()-a.residual.mean(),
          'low':lo,'high':hi,'n2':len(a),'n3':len(b),'undefined_replicates':u})
    save_table(out,'L2-L3-adjustment',adjustment)
    return pred
