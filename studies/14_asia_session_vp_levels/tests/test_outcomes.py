import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.outcomes import excursion,race,structural,fixed_path


class OutcomeTests(unittest.TestCase):
    def test_entry_candle_and_mirrored_excursions_units(self):
        o=np.array([100.,102.]);h=np.array([103.,104.]);l=np.array([98.,101.]);c=np.array([102.,103.])
        long=excursion(o,h,l,c,1,2,4)
        self.assertEqual((long['mfe_points'],long['mae_points'],long['terminal_points']),(4,2,3))
        self.assertEqual(long['mfe_ticks'],16);self.assertEqual(long['mae_dollars'],40)
        short=excursion(200-o,200-l,200-h,200-c,-1,2,4)
        self.assertEqual(long,dict(short,entry=100))

    def test_null_normalization_not_zero(self):
        result=excursion([1],[2],[0],[1],1,0,0)
        self.assertIsNone(result['mae_tr60']);self.assertIsNone(result['mfe_va_width'])

    def test_same_bar_bounds_and_non_hits(self):
        r=race([100],[105],[95],1,4,4)
        self.assertEqual(r['status'],'same_bar_ambiguous')
        self.assertEqual((r['favorable_first_lower'],r['favorable_first_upper']),(0,1))
        self.assertEqual((r['pre_target_mae_lower'],r['pre_target_mae_upper']),(0,5))
        self.assertEqual(race([100],[101],[99],1,4,4)['status'],'neither')
        self.assertIsNone(race([100],[101],[99],1,4,4)['pre_target_mae_upper'])

    def test_gap_open_resolves_order(self):
        r=race([100,105],[101,106],[99,94],1,4,4)
        self.assertEqual(r['status'],'favorable_first_open_gap')
        self.assertEqual(r['pre_target_mae_upper'],1)
        r=race([100,95],[101,106],[99,94],1,4,4)
        self.assertEqual(r['status'],'adverse_first_open_gap')

    def test_mirrored_race(self):
        o=np.array([100,105]);h=np.array([101,106]);l=np.array([99,94])
        self.assertEqual(race(o,h,l,1,4,4),race(200-o,200-l,200-h,-1,4,4))

    def test_elapsed_horizon_midnight_and_gap(self):
        ts=np.arange(360,dtype=np.int64)*60_000_000_000
        p,status=fixed_path(ts,125,125,30)
        self.assertEqual((p.start,p.stop,status),(125,155,'complete'))
        self.assertEqual(fixed_path(ts,350,350,30)[1],'midnight_censored')
        self.assertEqual(fixed_path(ts,330,330,30)[1],'complete')
        missing=np.delete(ts,140)
        self.assertEqual(fixed_path(missing,125,125,30)[1],'missing_future_minutes')

    def test_reference_behind_entry_retained_undefined_distinct(self):
        self.assertFalse(structural([100],[101],[99],1,98)['ahead'])
        self.assertTrue(structural([100],[101],[99],1,98)['directional_reach'])
        self.assertIsNone(structural([100],[101],[99],1,None)['range_hit'])


if __name__=='__main__':unittest.main()
