import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.engine import make_session
from src.statistics import Bootstrap, prepare
from src.common import window

class InputStatisticsTests(unittest.TestCase):
    def test_shared_week_draws_and_constant(self):
        b=Bootstrap(['2024-W01','2024-W02'],2000,1501)
        c=Bootstrap(['2024-W02','2024-W01'],2000,1501)
        np.testing.assert_equal(b.draws,c.draws)
        f=pd.DataFrame({'iso_week':['2024-W01','2024-W01','2024-W02'],'x':[1,1,1],'y':[1,1,1]})
        self.assertEqual(b.interval(f,['x','y']),[(1,1,2000)]*2)
    def test_public_join_lag_and_price_units(self):
        a,_=window('2024-03-11','ny');times=pd.date_range(a,periods=4,freq='min')
        f=pd.DataFrame({'ts_event':times[::2],'available_at':times[::2]+pd.Timedelta(minutes=2),
          'ny_anchor_ts':[a,a],'source_bar_count':[2,2],'min_tick':[250000000]*2,
          'contains_roll':[True,False],'raw_symbol':['ESH4']*2,'instrument_id':[1,1],
          'roll_id':['r','r'],'price_adjustment':[10_000_000_000]*2,
          'close':[110_000_000_000]*2,'ny_vwap':[109.,110.],'ny_sigma':[1.,2.],
          'ny_cumulative_volume':[1,2]})
        r=pd.DataFrame({'ts_event':times,'open':[100_000_000_000]*4,'high':[100_000_000_000]*4,
          'low':[100_000_000_000]*4,'close':[100_000_000_000]*4,'product':['ES']*4,
          'session_date':[pd.Timestamp('2024-03-11').date()]*4,'raw_symbol':['ESH4']*4,
          'instrument_id':[1]*4,'roll_id':['r']*4})
        s=make_session(f,r,'ES','ny','2024-03-11')
        self.assertEqual(s.vwap[0],396);self.assertEqual(s.sigma[0],4)
        self.assertTrue(np.isnan(s.centers[:2]).all());self.assertEqual(list(s.centers[2:4]),[396,396])
        self.assertTrue(s.valid_bar[0]);self.assertEqual(s.c[0],400)
        self.assertFalse(s.minute_ok[4]);self.assertFalse(s.valid_bar[2])
    def test_nested_touch_cohorts(self):
        f=pd.DataFrame({'threshold':[2,2.5,3],'first_move':['bounce','through','ambiguous'],
          'barrier_gap':[False]*3,'eligible':[True]*3,'event_id':['a','b','c']})
        result=prepare(f,'touch')
        self.assertEqual(result.groupby('threshold').size().to_dict(),{2.:3,2.5:2,3.:1})
        self.assertEqual(set(result.loc[result.threshold==3,'event_id']),{'c'})

if __name__=='__main__':unittest.main()
