"""Independent synthetic examples for definitions, units, availability and models."""
import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from src.events import extract,path,ratio,switch,efficiency
from src.inputs import fixed
from src.models import preprocess,fit,sigmoid,losses,mask_condition
from src.bootstrap import Bootstrap
from src.analysis import nonoverlap
from src.common import SCALE,window,Q

def bars(directions,step=60,times=None,barrier=None):
    n=len(directions);t=np.arange(n)*step+pd.Timestamp('2020-01-02 10:00').value//10**9 if times is None else np.array(times)
    o=np.arange(n)*100000+1000000000;c=o+np.array(directions)*100000
    df=pd.DataFrame({'open_i':o,'high_i':np.maximum(o,c)+50000,'low_i':np.minimum(o,c)-50000,'close_i':c,
      'direction':directions,'timestamp_seconds':t,'duration':np.r_[np.diff(t),np.nan],
      'bar_start_timestamp':pd.to_datetime(t,unit='s').strftime('%Y-%m-%d %H:%M:%S'),
      'session_date_proxy':['2020-01-02']*n,'barrier':[False]*n,'invalid':[False]*n,'long_gap':[False]*n,
      'chart':['6E_4']*n,'product':['6E']*n,'q_i':[50000]*n,'historical_q_i':[50000]*n})
    if barrier is not None:df.loc[barrier,'barrier']=True
    return df

class Events(unittest.TestCase):
    def event(self,seq,row):return extract(bars(seq)).set_index('R_row').loc[row]
    def test_L2_F0(self):
        e=self.event([-1,1,1,-1,1,1,1,1,1],4)
        self.assertEqual(e.L,2);self.assertEqual(e.F_exact,0);self.assertEqual(e.y3,0)
    def test_L3_F4(self):
        e=self.event([-1,1,1,1,-1,-1,-1,-1,-1,1,1],5)
        self.assertEqual(e.L,3);self.assertEqual(e.F_exact,4);self.assertEqual(e.new_leg_length,5)
    def test_F1(self):self.assertEqual(self.event([-1,1,1,-1,-1,1,1],4).F_exact,1)
    def test_L1(self):self.assertEqual(self.event([-1,1,-1,1,1],3).L,1)
    def test_direction_symmetry(self):
        seq=[-1,1,1,1,-1,-1,-1,-1,-1,1,1]
        a=extract(bars(seq));b=extract(bars([-d for d in seq]))
        np.testing.assert_equal(a.F_observed.to_numpy(),b.F_observed.to_numpy());np.testing.assert_equal(a.L.to_numpy(),b.L.to_numpy())
    def test_unknown_start(self):
        e=extract(bars([1,1,-1,-1,1,1]));self.assertFalse(e.iloc[0].prior_known);self.assertTrue(e.iloc[1].prior_known)
    def test_doji_break(self):
        df=extract(bars([-1,1,1,0,-1,-1,1,1]));self.assertNotIn(5,df.R_row.tolist());self.assertEqual(df.set_index('R_row').loc[7].L,2)
    def test_doji_breaks_future(self):self.assertEqual(self.event([-1,1,1,-1,0,1,1],4).F_exact,0)
    def test_unfinished_breaker(self):
        e=self.event([-1,1,1,-1,-1,-1,-1,-1,1],4)
        self.assertEqual(e.F_observed,4);self.assertTrue(pd.isna(e.F_exact));self.assertTrue(e.right_censored)
    def test_censor_unknown_not_zero(self):
        e=self.event([-1,1,1,-1,1],4);self.assertTrue(pd.isna(e.y1));self.assertFalse(e.order1)
    def test_early_failure_known_but_not_complete(self):
        e=self.event([-1,1,1,-1,1,1],4);self.assertEqual(e.y3,0);self.assertFalse(e.order3)
    def test_barrier(self):
        e=extract(bars([-1,1,1,-1,-1,-1,1,1],barrier=4)).set_index('R_row')
        self.assertNotIn(4,e.index);self.assertFalse(e.loc[7].prior_known)
    def test_session_boundary(self):
        x=bars([-1,1,1,-1,1,1]);x.loc[4:,'session_date_proxy']='2020-01-03'
        self.assertNotIn(4,extract(x).R_row.tolist())
    def test_same_second(self):
        x=bars([-1,1,1,-1,-1,-1,1,1]);x.loc[3,'duration']=0
        e=extract(x).set_index('R_row').loc[4];self.assertTrue(e.order3);self.assertFalse(e.strict3);self.assertEqual(e.y3,0)
    def test_feature_availability(self):
        a=bars([-1,1,1,-1,-1,1,1,1]);b=a.copy();b.loc[4:,'high_i']+=100000000
        e=extract(a).set_index('R_row').loc[4];f=extract(b).set_index('R_row').loc[4]
        for n in ['prior_distance_q','prior_efficiency','R_span_q','R_body_fraction','chop10']:
            self.assertTrue((pd.isna(e[n]) and pd.isna(f[n])) or e[n]==f[n])
        self.assertEqual(e.max_feature_source_row,e.name)
    def test_zero_duration_pace(self):
        x=bars([-1,1,1,-1,1,1]);x.loc[1:3,'timestamp_seconds']=x.timestamp_seconds.iloc[1]
        e=extract(x).set_index('R_row').loc[4];self.assertTrue(np.isnan(e.prior_bars_per_minute));self.assertTrue(e.prior_zero_duration)
    def test_exact_decimal(self):
        self.assertGreater(fixed('1.000000001'),fixed('1.000000000'));self.assertEqual(fixed('1.23'),1230000000)
        with self.assertRaises(ValueError):fixed('1.0000000001')
    def test_units(self):self.assertEqual(Q['6J'],500);self.assertEqual(Q['6S'],50000)
    def test_windows(self):
        self.assertEqual(window('2020-01-01 18:00:00'),'asia');self.assertEqual(window('2020-01-01 03:00:00'),'london_pre_ny')
        self.assertEqual(window('2020-01-01 09:30:00'),'ny_morning');self.assertEqual(window('2020-01-01 16:00:00'),'transition')
    def test_clock_staleness(self):
        e=self.event([-1,1,1,-1,-1,-1,-1,-1,1,1,1,1,1],4)
        self.assertEqual(e.clock5_staleness,0);self.assertEqual(e.clock5_elapsed,300);self.assertEqual(e.clock5_bar_row,9)
    def test_clock_no_future_completed(self):
        x=bars([-1,1,1,-1,-1,-1],step=1000);e=extract(x).set_index('R_row').loc[4]
        self.assertFalse(e.clock5_covered);self.assertFalse(e.clock5_boundary_censored)
    def test_gap_flags(self):
        x=bars([-1,1,1,-1,-1,-1,1,1]);x.loc[2,'long_gap']=True
        e=extract(x).set_index('R_row').loc[4];self.assertTrue(e.path_long_gap3)
    def test_cap_identity(self):
        x=bars([-1,1,1,-1]+[-1]*11+[1]*12);e=extract(x);g=e[e.order10]
        self.assertAlmostEqual(g.cap10.mean(),sum(g[f'y{k}'].mean() for k in range(1,11)))
    def test_F10_censored(self):
        e=self.event([-1,1,1,-1]+[-1]*11,4);self.assertEqual(e.y10,1);self.assertTrue(e.right_censored)
    def test_overlap_L1_undefined(self):self.assertTrue(np.isnan(self.event([-1,1,-1,1,1],3).prior_overlap))
    def test_switch_pairs(self):
        rate,n=switch(np.array([1,0,-1,1,1]));self.assertEqual(n,2);self.assertEqual(rate,.5)
    def test_efficiency_gaps(self):self.assertEqual(efficiency(np.array([10,20]),np.array([11,21])),1)
    def test_zero_division(self):self.assertTrue(np.isnan(ratio(1,0)))

class Paths(unittest.TestCase):
    def test_B4_and_gaps(self):
        x=bars([1]*8);o=np.array([100,100,110,120,130,180,190,200]);h=o+2;l=o-3;c=o+1;t=np.arange(8)*60
        e=path(o,h,l,c,t,1,1,3)
        self.assertEqual(e['entry_i'],110);self.assertEqual(e['exit_i'],180);self.assertEqual(e['D_i'],70)
        self.assertEqual(e['MFE_i'],70);self.assertEqual(e['MFE_bar'],4);self.assertEqual(e['MAE_i'],3)
        self.assertEqual(e['elapsed_seconds'],180)
    def test_long_short_mirror(self):
        o=np.array([100,100,110,120,130,180,190,200]);h=o+2;l=o-3;c=o+1;t=np.arange(8)*60
        a=path(o,h,l,c,t,1,1,3);b=path(300-o,300-l,300-h,300-c,t,1,-1,3)
        for n in ['D_i','MAE_i','MFE_i','elapsed_seconds']:self.assertEqual(a[n],b[n])
    def test_excludes_R(self):
        o=np.ones(8,dtype=int)*100;h=o+2;l=o-3;c=o+1;h[1]=10000;l[1]=1
        e=path(o,h,l,c,np.arange(8),1,1,3);self.assertEqual(e['MFE_i'],2);self.assertEqual(e['MAE_i'],3)
    def test_zero_extreme_null(self):
        o=np.ones(8,dtype=int)*100;e=path(o,o,o,o,np.arange(8),1,1,3);self.assertIsNone(e['MFE_bar'])
    def test_nonoverlap_strict_after_exit(self):
        x=pd.DataFrame({'R_row':[1,4,5,6,10],'h3_exit_row':[5,8,9,10,14]})
        self.assertEqual(nonoverlap(x,3).R_row.tolist(),[1,5,10])

class Models(unittest.TestCase):
    def test_full_synthetic_pipeline(self):
        from src.analysis import summarize
        from src.models import select,evaluate
        from src.common import dump,dictionary
        e=extract(bars(([-1,1,1,1,-1,-1,-1,-1,-1,1,1]*9)+[1]*12));copies=[]
        for k,date in enumerate(['2019-01-02','2021-01-04','2024-01-03']):
            g=e.copy();g['session_date']=date;g['split']=['development','validation','later'][k];g['year']=int(date[:4]);g['event_id']=g.event_id+str(k);g['available_at']=date+' 12:00:00'
            for h in [1,2,3,5,10]:g['h'+str(h)+'_exit_time']=date+' 13:00:00'
            copies.append(g)
        e=pd.concat(copies,ignore_index=True);boot=Bootstrap(e.session_date)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'evidence').mkdir();dump(p/'feature-dictionary.json',dictionary());dump(p/'config.json',{'embargo_dates':[]})
            select(p,e,boot);evaluate(p,e,boot);summarize(p,e,e,boot)
            self.assertEqual(len(list((p/'tables').glob('*.csv'))),25)
    def test_train_only_preprocessing(self):
        train=pd.DataFrame({'x':[1.,2.,np.nan,3.],'window':['asia']*4,'era':['constant']*4});test=train.copy();test['x']=1e10
        X,V,pre=preprocess(train,test,['x']);self.assertEqual(pre['median'][0],2.);self.assertLess(pre['scale'][0],2)
    def test_ridge_constant(self):
        X=np.c_[np.ones(30),np.arange(30)];b,d=fit(X,np.ones(30)*4,1.,False);np.testing.assert_allclose(X@b,4,atol=1e-10)
    def test_logistic_scores(self):
        rng=np.random.default_rng(1);X=np.c_[np.ones(300),rng.normal(size=300)];y=(X[:,1]+rng.normal(size=300)>.2).astype(float)
        b,d=fit(X,y,1.,True);self.assertTrue(d['converged']);self.assertGreater(b[1],0);self.assertTrue(np.isfinite(losses(y,sigmoid(X@b),True)['log_loss']).all())
    def test_bootstrap_synchronized(self):
        boot=Bootstrap(['a','b','c'],reps=2000);a=pd.DataFrame({'session_date':['a','a','b','c'],'x':[1.,0.,1.,0.]})
        lo,hi,u=boot.difference(a,'x',a,'x');self.assertEqual(lo,0);self.assertEqual(hi,0);self.assertEqual(boot.weights.shape,(2000,3))
    def test_no_missing_imputation_labels(self):
        y=np.array([1.,0.]);p=np.array([1.,0.]);self.assertTrue(np.isfinite(losses(y,p,True)['log_loss']).all())

if __name__=='__main__':unittest.main()
