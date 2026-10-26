import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.engine import Session, episodes, horizons, round_half_up, first_move, zone_touch, whole_gap, reference_overtake
from src.common import MINUTE, window, HORIZONS


def synthetic(z, *, side=1, sigma=2., center=100., name='ny'):
    n=len(z);a,_=window('2024-03-11',name);v=np.full(n,center);s=np.full(n,sigma)
    closes=center+np.array(z)*sigma*side
    c=np.repeat(closes,2);o=c.copy();h=c+.1;l=c-.1
    centers=np.repeat(np.r_[np.nan,v[:-1]],2)
    return Session('ES',name,'2024-03-11',a.value,a.value+n*2*MINUTE,1.,o,h,l,c,v,s,np.ones(n)*10,
        np.ones(n,dtype=bool),np.ones(2*n,dtype=bool),np.array(['ESH4|1|1']*n),np.zeros(n),
        np.array(['ESH4']*n),np.ones(n),closes,centers,'feature','raw')

class EngineTests(unittest.TestCase):
    def test_strict_thresholds_and_jump(self):
        for side in [1,-1]:
            s=synthetic([0,2,2.5,3,3.1,3.2],side=side)
            p,e,t,c=episodes(s)
            self.assertEqual([x['threshold'] for x in e],[2.,2.5,3.])
            self.assertEqual([x['signal_bar_index'] for x in e],[2,3,4]);self.assertEqual(len(p),1)
            s=synthetic([0,3.5,3.6],side=side)
            self.assertEqual([e['threshold'] for e in episodes(s)[1]],[2,2.5,3])
    def test_left_censored_rearm_dedup(self):
        s=synthetic([3.5,4,1.5,3.5,2.2,3.5,0,3.5,3.6])
        p,e,t,c=episodes(s)
        self.assertEqual(len(p),2);self.assertEqual(len(e),6);self.assertEqual(len(t),1)
        self.assertEqual(p[0]['departure_bar_index'],3);self.assertEqual(p[1]['departure_bar_index'],7)
        self.assertTrue(any(x['status']=='already_recorded_parent' for x in c))
    def test_no_signal_bar_or_touch_bar_leakage(self):
        s=synthetic([0,3.5,0]+[1]*102)
        s.h[2:4]=10000;s.l[2:4]=-10000
        p,e,t,_=episodes(s)
        out=horizons(s,e[0]);self.assertLess(out[0]['long_mfe'],10)
        self.assertEqual(len(t),1);self.assertEqual(t[0]['entry_minute_index'],6)
        s.h[4:6]=9999;s.l[4:6]=-9999
        out=horizons(s,t[0]);self.assertLess(out[0]['long_mfe'],10)
    def test_exact_horizon_indexing_and_own_open(self):
        s=synthetic([0,3.5]+[4]*102);e=episodes(s)[1][0];start=e['entry_minute_index']
        s.o[start:]=100;s.c[start:]=101
        for h in HORIZONS:s.c[start+2*h-1]=100+h;s.o[start+2*h-2]=200
        rows=horizons(s,e)
        self.assertEqual([x['price_delta'] for x in rows],list(HORIZONS))
        self.assertTrue(all(x['above_entry'] and not x['final_candle_up'] for x in rows))
    def test_lagged_evolving_and_frozen_disagreement(self):
        s=synthetic([0,3.5]+[4]*55);e=episodes(s)[1][0]
        s.vwap[2:]=110;s.centers[6:]=110;s.l[4:]=109.5;s.h[4:]=110.5;s.o[4:]=110;s.c[4:]=110
        row=horizons(s,e)[0]
        self.assertTrue(row['evolving_touch']);self.assertFalse(row['frozen_touch']);self.assertEqual(row['evolving_latency_minutes'],3)
        self.assertTrue(row['evolving_only'])
    def test_gap_before_later_contact_is_no_parent_touch(self):
        s=synthetic([0,3.5,-2,0]+[1]*52)
        p,e,t,c=episodes(s)
        self.assertEqual(p[0]['termination_reason'],'gap_through');self.assertEqual(t,[])
        row=horizons(s,e[0])[0];self.assertTrue(row['evolving_touch']);self.assertGreater(row['gap_count'],0)
    def test_reference_overtake(self):
        self.assertTrue(reference_overtake(105,100,110,1));self.assertFalse(zone_touch(104,106,110))
        s=synthetic([0,3.5,4,4,4]);s.vwap[2]=112;s.centers[6:8]=112
        p,e,t,c=episodes(s);self.assertEqual(p[0]['termination_reason'],'reference_overtake');self.assertFalse(t)
    def test_touch_precedes_higher_close_cross(self):
        s=synthetic([0,2.2,3.5,4]);s.l[4]=100
        p,e,t,c=episodes(s);self.assertEqual([x['threshold'] for x in e],[2]);self.assertEqual(t[0]['threshold'],2)
    def test_missing_minutes_and_null_not_false(self):
        s=synthetic([0,3.5]+[4]*60);e=episodes(s)[1][0];s.minute_ok[5]=False
        r=horizons(s,e)[0];self.assertFalse(r['eligible']);self.assertIsNone(r['evolving_touch'])
        self.assertEqual(episodes(s)[0][0]['termination_reason'],'missing_or_invalid_minute')
    def test_contract_adjustment_break(self):
        for field in ['identity','adjustment']:
            s=synthetic([0,3.5]+[4]*60);e=episodes(s)[1][0]
            if field=='identity':s.identity[3:]='NQM4|2|2'
            else:s.adjustment[3:]=100
            self.assertEqual(horizons(s,e)[0]['exclusion_reason'],'contract_or_adjustment_break')
            self.assertEqual(episodes(s)[0][0]['termination_reason'],'contract_or_adjustment_break')
    def test_boundary_exact_and_excluded(self):
        s=synthetic([0,3.5]+[4]*10);e=episodes(s)[1][0];r=horizons(s,e)
        self.assertTrue(r[1]['eligible']);self.assertEqual(r[2]['exclusion_reason'],'session_boundary')
        self.assertIsNone(r[2]['evolving_touch'])
    def test_zero_sigma_retains_touch_points(self):
        s=synthetic([0,3.5,0]+[1]*60);s.sigma[2]=0
        p,e,t,c=episodes(s);self.assertEqual(len(t),1)
        r=horizons(s,t[0])[0];self.assertTrue(r['eligible']);self.assertEqual(r['first_move'],'unavailable')
        self.assertIsNone(r['long_mae_sigma'])
        s=synthetic([0,3.5,4]);s.sigma[0]=0;self.assertFalse(episodes(s)[1])
    def test_barriers_ambiguity_open_priority_symmetry(self):
        for side in [1,-1]:
            self.assertEqual(first_move([100],[103],[97],100,2,side)[0],'ambiguous')
            self.assertEqual(first_move([103],[104],[95],100,2,side)[:2],('bounce' if side==1 else 'through',True))
            self.assertEqual(first_move([100],[101],[99],100,2,side)[0],'neither')
    def test_monotonic_and_side_identity(self):
        s=synthetic([0,3.5]+[4]*102);e=episodes(s)[1][0]
        r=horizons(s,e)
        for x in r:
            self.assertEqual(x['long_mfe'],x['short_mae']);self.assertEqual(x['long_mae'],x['short_mfe'])
            self.assertEqual(sum(x[k] for k in ['above_entry','below_entry','entry_tie']),1)
            self.assertEqual(sum(x[k] for k in ['final_candle_up','final_candle_down','final_candle_tie']),1)
        for col in ['long_mfe','long_mae','evolving_touch','frozen_touch']:
            self.assertTrue(all(a[col]<=b[col] for a,b in zip(r,r[1:])))
    def test_translation_invariance(self):
        a=synthetic([0,3.5,0]+[1]*60);b=synthetic([0,3.5,0]+[1]*60,center=10000)
        ea=episodes(a)[1][0];eb=episodes(b)[1][0]
        ra=horizons(a,ea)[0];rb=horizons(b,eb)[0]
        for col in ['long_mfe','long_mae','price_delta','evolving_touch','frozen_touch']:
            self.assertAlmostEqual(ra[col],rb[col],places=8)
    def test_clock_dst_midnight_windows_and_gaps(self):
        a,b=window('2024-03-08','ny');c,d=window('2024-03-11','ny')
        self.assertEqual(a.hour,14);self.assertEqual(c.hour,13)
        a,b=window('2024-11-04','asia');self.assertEqual((b-a)/pd.Timedelta(hours=1),7)
        self.assertNotEqual(a.tz_convert('America/New_York').date(),b.tz_convert('America/New_York').date())
        self.assertEqual(window('2024-03-11','london')[1].tz_convert('America/New_York').strftime('%H:%M'),'09:00')
        self.assertEqual(window('2024-03-11','ny')[0].tz_convert('America/New_York').strftime('%H:%M'),'09:30')
    def test_tick_rounding_and_inclusive_touch(self):
        np.testing.assert_equal(round_half_up([1.5,-1.5,2.49]),[2,-2,2])
        self.assertTrue(zone_touch(101,102,100));self.assertFalse(zone_touch(101.01,102,100))
        self.assertTrue(whole_gap(102,98,100));self.assertFalse(whole_gap(101,98,100))

if __name__=='__main__':unittest.main()
