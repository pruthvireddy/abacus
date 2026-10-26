import sys
from pathlib import Path
import unittest
import tempfile
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core import (pivots, indicator_segment, rejection, cloud, Episodes, excursions,
                      tick_round, threshold_order, forward_outcome, MINUTE, FIVE)
from src.calendar import expected, stamp, assign_days, previous_weekday, week
from src.spec import split_for
from src.inputs import aggregate
from src.replay import replay, policy, minute_arrays
from src.statistics import path_summary, policy_summary, Bootstrap, interval
from src.reporting import project_csv, check_projection

def event(**kw):
    return {"event_id": "e", "direction": 1, "entry_ts": stamp("2024-01-03", 570),
            "entry_minute_NY": 570, "confirmation_low": 98, "confirmation_high": 103,
            "day": "2024-01-03", "pair": "3", "prior_close": 100,
            "prior_range": 20, "opposite_pivot": 105, **kw}

def minute_fixture():
    t = stamp("2024-01-03", 570) + np.arange(391)*MINUTE
    return pd.DataFrame({"ts": t, "open": 100., "high": 101., "low": 99., "close": 100., "valid": True, "volume": 10})

class Arithmetic(unittest.TestCase):
    def test_fixed_point_gc_equal_touch_regression(self):
        c=float(np.float64(1000100000000)*1e-9)
        h=float(np.float64(1004100000000)*1e-9)
        l=c
        support,resistance=pivots(h,l,c,1.1/4)
        touched=float(np.float64(999000000000)*1e-9)
        self.assertEqual(support,999)
        self.assertEqual(rejection(1000,999,1001,touched,1000,support,resistance),1)
        episode=Episodes();self.assertTrue(episode.step(1,1001,touched,support,resistance))
        self.assertFalse(episode.step(1,1001,touched,support,resistance))
    def test_exact_pivot_fraction(self):
        self.assertEqual(pivots(120,60,100,1.1/6), (89,111))
        self.assertEqual(pivots(120,60,100,1.1/4), (83.5,116.5))
        self.assertTrue(np.isnan(pivots(np.nan,60,100,.275)[0]))

    def test_ema_and_wilder_seed(self):
        c=np.arange(100.,130.)
        fast,slow,atr=indicator_segment(c+1,c-1,c)
        self.assertAlmostEqual(fast[1],100+2/21)
        self.assertAlmostEqual(slow[1],100+2/51)
        self.assertTrue(np.isnan(atr[12]))
        self.assertAlmostEqual(atr[13],2.)
        self.assertAlmostEqual(atr[14],2.)

    def test_true_range_gap(self):
        c=np.r_[100., np.repeat(110.,20)]
        _,_,a=indicator_segment(c+1,c-1,c)
        self.assertAlmostEqual(a[13],(2*13+11)/14)

    def test_prefix_and_additive_invariance(self):
        c=np.sin(np.arange(600))*3+100
        all_=indicator_segment(c+2,c-2,c)
        short=indicator_segment(c[:300]+2,c[:300]-2,c[:300])
        shifted=indicator_segment(c+1002,c+998,c+1000)
        for a,b in zip(all_,short): np.testing.assert_allclose(a[:300],b,equal_nan=True)
        np.testing.assert_allclose(all_[0]+1000,shifted[0],atol=1e-11)
        np.testing.assert_allclose(all_[2],shifted[2],atol=1e-11)

    def test_short_close_definitions_and_units(self):
        o=excursions(-1,100,np.array([103,102]),np.array([95,98]),np.array([99,99]),2)
        self.assertEqual(o["delta"],.5)
        self.assertEqual(o["mfe"],2.5)
        self.assertEqual(o["mae"],1.5)
        self.assertFalse(o["literal_above"])

class Signal(unittest.TestCase):
    def test_equality_and_approach(self):
        self.assertEqual(rejection(101,100,102,100,101,100,110),1)
        self.assertEqual(rejection(100,100,102,100,101,100,110),0)
        self.assertEqual(rejection(101,99,102,98,101,100,110),0)
        self.assertEqual(rejection(101,100,102,99,100,100,110),0)
        self.assertEqual(rejection(101,101,102,99,101,100,110),0)

    def test_dual_touch_mirrored_and_tolerance(self):
        self.assertEqual(rejection(109,110,111,108,109,100,110),-1)
        self.assertEqual(rejection(101,100,110,99,102,100,110),0)
        self.assertEqual(rejection(102,101,103,100.25,102,100,110),0)
        self.assertEqual(rejection(102,101,103,100.25,102,100,110,.25),1)

    def test_undefined_not_false(self):
        self.assertIsNone(rejection(np.nan,100,102,99,101,100,110))
        self.assertIsNone(cloud(1,101,np.nan,99)["alignment"])
        self.assertFalse(cloud(1,101,100,100)["alignment"])
        self.assertTrue(cloud(-1,98,99,100)["alignment_outside"])

    def test_episode_shared_before_cloud(self):
        s=Episodes()
        self.assertTrue(s.step(1,103,99,100,110))
        self.assertFalse(cloud(1,101,99,100)["alignment"])
        self.assertFalse(s.step(1,103,99,100,110))
        s.step(0,103,100.5,100,110,complete=False)
        self.assertFalse(s.step(1,103,99,100,110))
        s.step(0,103,100.5,100,110,complete=True)
        self.assertTrue(s.step(1,103,99,100,110))

class DataTiming(unittest.TestCase):
    def test_aggregation_availability_and_no_fill(self):
        f=minute_fixture().iloc[:5].copy()
        f["minute_ts"]=f.ts
        f["contract"]="ES@1"
        f["instrument_id"]=1
        f["raw_symbol"]="ESM4"
        b=aggregate(f)
        self.assertTrue(b.iloc[0].complete)
        self.assertEqual(int(b.iloc[0]["count"]),5)
        self.assertFalse(aggregate(f.drop(2)).iloc[0].complete)
        f.loc[2,"contract"]="ES@2"
        self.assertFalse(aggregate(f).iloc[0].complete)

    def test_short_horizons_survive_partial_long_path(self):
        start=stamp("2024-01-03",570)
        b=pd.DataFrame({"ts":start+np.arange(15)*FIVE,"high":102.,"low":99.,"close":101.,"complete":True,"contract":"X","day":"2024-01-03"})
        b.loc[7,"complete"]=False
        self.assertTrue(forward_outcome(b,0,5,100,1,2,99,stamp("2024-01-03",960))["completed"])
        self.assertFalse(forward_outcome(b,0,10,100,1,2,99,stamp("2024-01-03",960))["completed"])
        self.assertFalse(forward_outcome(b,0,50,100,1,2,99,stamp("2024-01-03",960))["completed"])

    def test_calendar_dst_historical_regimes(self):
        self.assertEqual(len(expected("ES","2020-03-09")),1365)
        self.assertEqual(len(expected("ES","2024-03-11")),1380)
        self.assertEqual(len(expected("GC","2015-09-18")),1395)
        self.assertEqual(len(expected("GC","2015-09-21")),1380)
        self.assertEqual(pd.Timestamp(stamp("2024-03-08",570),tz="UTC").hour,14)
        self.assertEqual(pd.Timestamp(stamp("2024-03-11",570),tz="UTC").hour,13)

    def test_gc_assignment_and_no_prior_substitution(self):
        self.assertEqual(assign_days(np.array([stamp("2014-01-06",1030)]))[0],"2014-01-06")
        self.assertEqual(assign_days(np.array([stamp("2014-01-06",1080)]))[0],"2014-01-07")
        self.assertEqual(previous_weekday("2024-01-16"),"2024-01-15")

    def test_split_and_week_leakage_boundaries(self):
        self.assertEqual(split_for("2020-12-31"),"development")
        self.assertEqual(split_for("2021-01-01"),"validation")
        self.assertEqual(split_for("2023-12-31"),"validation")
        self.assertEqual(split_for("2024-01-01"),"final_evaluation")
        self.assertIsNone(split_for("2026-09-19"))
        self.assertEqual(week("2021-01-01"),"2020-12-28")

class Execution(unittest.TestCase):
    def test_stop_gap_and_fee_units(self):
        m=minute_fixture();m.loc[1,["open","high","low"]]=[95.,96.,94.]
        o=replay(event(),minute_arrays(m),.25,50)
        self.assertEqual(o["reason"],"stop_gap")
        self.assertEqual(o["entry_fill"],100.25)
        self.assertEqual(o["exit_fill"],94.75)
        self.assertEqual(o["net_USD"],-285)

    def test_entry_candle_and_latency(self):
        m=minute_fixture();m.loc[0,"low"]=90
        a=replay(event(),minute_arrays(m),.25,50)
        b=replay(event(),minute_arrays(m),.25,50,delay=1)
        self.assertEqual(a["reason"],"stop")
        self.assertEqual(b["reason"],"timeout")
        self.assertEqual(b["entry_actual_ts"],event()["entry_ts"]+MINUTE)

    def test_limit_trade_through_touch(self):
        m=minute_fixture();m.loc[0,"high"]=107.75
        a=replay(event(),minute_arrays(m),.25,50)
        b=replay(event(),minute_arrays(m),.25,50,touch=True)
        self.assertEqual(a["reason"],"timeout")
        self.assertEqual(b["reason"],"target")
        self.assertEqual(b["exit_fill"],107.75)

    def test_same_minute_bounds(self):
        m=minute_fixture();m.loc[0,["high","low"]]=[109,97]
        a=replay(event(),minute_arrays(m),.25,50,order="stop_first")
        b=replay(event(),minute_arrays(m),.25,50,order="target_first")
        self.assertTrue(a["ambiguous"] and b["ambiguous"])
        self.assertLess(a["net_R"],b["net_R"])

    def test_missing_entry_timeout_and_invalid_risk(self):
        m=minute_fixture()
        self.assertFalse(replay(event(),minute_arrays(m.iloc[1:]),.25,50)["entered"])
        self.assertTrue(np.isnan(replay(event(),minute_arrays(m.iloc[:-1]),.25,50)["net_R"]))
        m.loc[0,"open"]=97
        self.assertFalse(replay(event(),minute_arrays(m),.25,50)["entered"])

    def test_tick_round_both_directions(self):
        self.assertAlmostEqual(tick_round(100.21,.1,1),100.3)
        self.assertAlmostEqual(tick_round(100.21,.1,-1),100.2)
        self.assertEqual(tick_round(100.25,.25,1),100.25)

    def test_threshold_censor_and_ambiguity(self):
        self.assertEqual(threshold_order(np.array([.5]),np.array([1]),.5),"same_minute_ambiguous")
        self.assertEqual(threshold_order(np.array([0]),np.array([0]),1,False),"censored")
        self.assertEqual(threshold_order(np.array([1,0]),np.array([0,1]),1),"favorable_first")

    def test_one_position_and_missing_zero_day(self):
        m=minute_fixture()
        e1=event();e2=event(event_id="later",entry_ts=event()["entry_ts"]+FIVE,entry_minute_NY=575)
        ev=pd.DataFrame([e1,e2])
        roster=pd.DataFrame({"day":["2024-01-03"],"split":["final_evaluation"],"year":[2024],"signal_window_complete":[True],"session_window_complete":[True]})
        t,s=policy(ev,roster,minute_arrays(m),"ES","3","none")
        self.assertEqual(s.iloc[0].entered,1)
        self.assertEqual(s.iloc[0].occupancy_skips,1)
        empty,s=policy(ev.iloc[:0],roster,minute_arrays(m),"ES","3","none")
        self.assertEqual(s.iloc[0].net_R,0)
        roster.loc[0,"signal_window_complete"]=False
        empty,s=policy(ev.iloc[:0],roster,minute_arrays(m),"ES","3","none")
        self.assertTrue(np.isnan(s.iloc[0].net_R))

class Denominators(unittest.TestCase):
    def test_report_exact_cells_and_stale_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/"tables").mkdir()
            source=root/"tables/values.csv"
            source.write_text("group,value,missing\na,0.000123456789,\nb,0,\n")
            p=project_csv(source,root/"downloads/selected.csv",["value","missing"],lambda r:r["group"]=="a")
            self.assertEqual(check_projection(root,p),2)
            self.assertIn("0.000123456789,",(root/"downloads/selected.csv").read_text())
            source.write_text("group,value,missing\na,1,\nb,0,\n")
            with self.assertRaises(AssertionError):check_projection(root,p)
    def test_completed_denominator_ties_and_missing(self):
        ev=pd.DataFrame({"event_id":["a","b","c"],"day":["2024-01-03"]*3,"week":["2024-01-01"]*3})
        outcomes=pd.DataFrame({"event_id":["a","b","c"],"completed":[True,True,False],"entered":[True,True,True],"favorable":[True,False,None],"literal_above":[True,False,None],"defended":[True,True,None],"mfe_gt_mae":[True,False,None],"delta":[1,0,np.nan],"delta_points":[2,0,np.nan],"mae":[0,1,np.nan],"mfe":[2,1,np.nan]})
        s=path_summary(ev,outcomes)
        self.assertEqual(s["accepted"],3)
        self.assertEqual(s["completed_N"],2)
        self.assertEqual(s["favorable_share"],.5)
        self.assertEqual(s["mean_delta"],.5)
        self.assertEqual(s["censored_entered"],1)
        self.assertAlmostEqual(s["favorable_lower_bound_entered"],1/3)
        self.assertAlmostEqual(s["favorable_upper_bound_entered"],2/3)

    def test_calendar_blocks_paired_and_zero_support(self):
        b=Bootstrap("2024-01-01","2024-03-01",replicates=100)
        a=pd.DataFrame({"week":["2024-01-01","2024-02-05"],"delta":[1,2]})
        draws,support=b.distribution(a)
        twice,_=b.distribution(a.assign(delta=a.delta*2))
        np.testing.assert_allclose(twice,2*draws,equal_nan=True)
        self.assertEqual(support,2)
        none,support=b.distribution(a.iloc[:1])
        self.assertTrue(np.isnan(none).all())
        self.assertTrue(np.isnan(interval(none)[0]))

if __name__ == "__main__": unittest.main()
