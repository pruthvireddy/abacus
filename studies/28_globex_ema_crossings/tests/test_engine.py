import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

S=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(S))
from src.engine import (aggregate_closes,ema6,crossing_directions,window_masks,atr_context,
                       atr_bin,realized_bin,summarize_group,moving_block_means,make_tables)


class NumericalDefinitions(unittest.TestCase):
    def test_minute_aggregation_last_observed_close_and_no_fill(self):
        m=pd.DataFrame({'ts_event':pd.to_datetime(['2024-06-03T22:00Z','2024-06-03T22:04Z','2024-06-03T22:10Z']), 'close':[10,14,20]})
        b=aggregate_closes(m,'5m')
        self.assertEqual(b.close.tolist(),[14,20])
        self.assertEqual(b.index.minute.tolist(),[0,10])
        self.assertEqual(aggregate_closes(m,'2m').index.minute.tolist(),[0,4,10])

    def test_ema_hand_recursion(self):
        np.testing.assert_allclose(ema6([7,14,7]),[7,9,59/7])

    def test_ema_shift_invariance(self):
        x=[12,19,14,10,1,15]
        np.testing.assert_allclose(ema6(x)+100,ema6(np.array(x)+100))

    def test_ema_rejects_missing(self):
        with self.assertRaises(ValueError): ema6([1,np.nan])

    def test_equality_leaves_zero_but_touch_is_not_cross(self):
        ts=pd.date_range('2024-01-01',periods=7,freq='5min',tz='UTC')
        c,v=crossing_directions([1,0,1,0,-1,-2,1],np.zeros(7),['A']*7,ts,5)
        self.assertEqual(c.tolist(),[0,0,1,0,-1,0,1])
        self.assertEqual(v.tolist(),[False,True,True,True,True,True,True])

    def test_anchor_reset_not_cross(self):
        ts=pd.date_range('2024-01-01',periods=3,freq='5min',tz='UTC')
        c,v=crossing_directions([-1,1,-1],[0]*3,['A','B','B'],ts,5)
        self.assertEqual(c.tolist(),[0,0,-1]);self.assertFalse(v[1])

    def test_nonconsecutive_or_nonfinite_undefined(self):
        ts=pd.to_datetime(['2024-01-01T00:00Z','2024-01-01T00:10Z','2024-01-01T00:15Z'])
        c,v=crossing_directions([-1,1,-1],[0,0,np.nan],['A']*3,ts,5)
        self.assertFalse(v.any());self.assertFalse(c.any())

    def test_window_boundaries_and_gc(self):
        ts=pd.to_datetime(['2024-06-03T08:20','2024-06-03T09:30','2024-06-03T13:30','2024-06-03T16:00']).tz_localize('America/New_York')
        m=window_masks(ts,'GC',[29,30,31,32])
        self.assertEqual(m['us_cash'].tolist(),[False,True,True,False])
        self.assertEqual(m['gc_day'].tolist(),[True,True,False,False])
        self.assertEqual(m['globex_after_30_bars'].tolist(),[False,False,True,True])
        self.assertNotIn('gc_day',window_masks(ts,'ES',[0,1,2,3]))

    def test_atr_thresholds(self):
        self.assertEqual([atr_bin(x) for x in [0,1/3,2/3,1,np.nan]],['low','normal','high','high','unknown'])
        self.assertEqual([realized_bin(x) for x in [0,.75,1.25,np.nan]],['quiet','normal','active','unknown'])

    def daily(self):
        return pd.DataFrame({'trading_day':['2024-01-01','2024-01-02','2024-01-03','2024-01-04'],
          'available_at':pd.date_range('2024-01-01T22:00Z',periods=4,freq='D'),
          'atr14':[10.,20,30,40], 'atr14_pct':[1.,2.,3.,2.]})

    def test_asof_exact_end_and_midrank(self):
        d=self.daily();t=[pd.Timestamp('2024-01-04T22:00Z')]
        r=atr_context(d,t,lookback=3).iloc[0]
        self.assertEqual(r.atr14,40);self.assertEqual(r.atr_percentile,.5)

    def test_future_daily_values_cannot_change_past_context(self):
        d=self.daily();t=[pd.Timestamp('2024-01-03T23:00Z')]
        a=atr_context(d,t,lookback=2);d.loc[3,'atr14_pct']=1000
        pd.testing.assert_frame_equal(a,atr_context(d,t,lookback=2))
        self.assertEqual(a.iloc[0].atr14,30)

    def test_before_history_stale_and_not_enough_rank_are_unknown(self):
        d=self.daily();t=pd.to_datetime(['2023-01-01T22:00Z','2024-01-02T23:00Z','2024-01-12T22:01Z'])
        r=atr_context(d,t,lookback=3)
        self.assertEqual(r.atr_regime.tolist(),['unknown']*3)
        self.assertTrue(np.isnan(r.iloc[0].atr14));self.assertEqual(r.iloc[1].atr14,20)
        self.assertTrue(np.isnan(r.iloc[2].atr14))

    def test_nonpositive_atr_unknown(self):
        d=self.daily();d.loc[3,'atr14']=0
        self.assertTrue(np.isnan(atr_context(d,[d.available_at.iloc[3]],lookback=2).iloc[0].atr14))

    def test_zero_days_in_denominator(self):
        g=pd.DataFrame({'crosses':[0,2,4],'crosses_up':[0,1,2],'crosses_down':[0,1,2],'observed_hours':[1,1,1]})
        r=summarize_group(g)
        self.assertEqual(r['mean_crosses'],2);self.assertEqual(r['zero_cross_fraction'],1/3)
        self.assertEqual(r['sessions'],3);self.assertEqual(r['crosses_per_hour'],2)

    def test_bootstrap_deterministic_and_label_preserving(self):
        a=moving_block_means([1,1,5,5],['low','low','high','high'],['low','high'],replicates=50)
        self.assertEqual(a,{'low':(1.,1.),'high':(5.,5.)})
        self.assertEqual(a,moving_block_means([1,1,5,5],['low','low','high','high'],['low','high'],replicates=50))

    def test_no_sample_month_not_zero_filled(self):
        p=pd.DataFrame({'product':['ES']*2,'timeframe':['5m']*2,'window':['globex']*2,
           'cohort':['all_available']*2,'session_date':['2024-01-01','2024-03-01'],
           'crosses':[0,2],'crosses_up':[0,1],'crosses_down':[0,1],
           'observed_hours':[23,23],'atr_regime':['low','high'],'realized_regime':['quiet','active']})
        t=make_tables(p)
        self.assertEqual(set(t['monthly'].month),{'2024-01','2024-03'})
        g=t['summary'].query("segmentation == 'all'").iloc[0]
        self.assertEqual(g.sessions,2);self.assertEqual(g.mean_crosses,1)


if __name__=='__main__': unittest.main()
