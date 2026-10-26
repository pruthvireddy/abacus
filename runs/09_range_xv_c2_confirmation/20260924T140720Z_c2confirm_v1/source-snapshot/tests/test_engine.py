import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


ENGINE = Path(__file__).resolve().parents[1] / "src" / "engine.py"
spec = importlib.util.spec_from_file_location("study09_engine", ENGINE)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


def rows(directions, statuses=None):
    n = len(directions)
    starts = pd.date_range("2020-03-08 18:00:00", periods=n, freq="min").strftime("%Y-%m-%d %H:%M:%S").tolist()
    if statuses is None:
        statuses = [engine.STRICT]*(n-1)+["unavailable_session_boundary"]
    closes = [100+x*.25 for x in directions]
    return pd.DataFrame({"source_row":range(1,n+1),"source_timestamp":starts,
        "bar_start_timestamp":starts,"bar_completion_timestamp_proxy":starts[1:]+[None],
        "completion_proxy_status":statuses,"session_date_proxy":["2020-03-09"]*n,
        "open":[100.]*n,"high":[max(100,v)+.25 for v in closes],
        "low":[min(100,v)-.25 for v in closes],"close":closes})


class DecisionTests(unittest.TestCase):
    def test_c1_c2_and_two_future_bars(self):
        opportunities, baseline, audit = engine.extract_session(
            rows([1,1,1,-1,-1,-1,-1,1]),"ES",5)
        c1 = opportunities.loc[opportunities.c1_source_row == 4].iloc[0]
        self.assertEqual(c1.prior_run,3)
        self.assertTrue(c1.common_eligible)
        self.assertTrue(c1.c2_follows)
        self.assertTrue(c1.immediate_two_success)
        self.assertTrue(c1.wait_two_success)
        self.assertEqual(c1.c2_source_row,5)
        self.assertNotIn(5,baseline.b2_source_row.tolist())
        self.assertGreater(audit["candidate_pairs_removed_from_ordinary"],0)

    def test_doji_breaks_confirmation_and_old_trend_branch(self):
        opportunities,_,_ = engine.extract_session(rows([1,1,1,-1,0,1,1,1]),"ES",5)
        c1=opportunities.loc[opportunities.c1_source_row==4].iloc[0]
        self.assertTrue(c1.common_eligible)
        self.assertTrue(c1.c2_doji)
        self.assertFalse(c1.c2_follows)
        self.assertFalse(c1.c2_old_trend)
        self.assertTrue(c1.c3_old_trend)
        self.assertFalse(c1.wait_two_success)

    def test_strict_c4_completion_and_same_second_exclusion(self):
        data=rows([1,1,1,-1,-1,-1,-1,1])
        data.loc[6,"completion_proxy_status"] = engine.SAME
        opportunities,baseline,_=engine.extract_session(data,"ES",5)
        c1=opportunities.loc[opportunities.c1_source_row==4].iloc[0]
        self.assertFalse(c1.common_eligible)
        self.assertNotIn(5,baseline.b2_source_row.tolist())

    def test_no_cross_session_or_export_end(self):
        opportunities,baseline,_=engine.extract_session(rows([1,1,1,-1,-1]),"ES",5)
        c1=opportunities.loc[opportunities.c1_source_row==4].iloc[0]
        self.assertFalse(c1.common_eligible)
        self.assertNotIn(5,baseline.b2_source_row.tolist())

    def test_ordinary_interior_pair_remains(self):
        _,baseline,_=engine.extract_session(rows([1,1,1,1,1,1,1]),"ES",5)
        self.assertIn(2,baseline.b2_source_row.tolist())
        self.assertTrue(baseline.two_success.all())
        self.assertEqual(int(baseline.loc[baseline.b2_source_row==2,"pair_run_age"].iloc[0]),2)
        self.assertGreater(int(baseline.pair_run_age.max()),2)

    def test_session_boundaries_and_normalized_dst_wall_time(self):
        self.assertEqual(engine.session_window("2020-03-08 02:59:59"),"asia")
        self.assertEqual(engine.session_window("2020-03-08 03:00:00"),"london_pre_ny")
        self.assertEqual(engine.session_window("2020-11-01 09:30:00"),"ny_morning")
        self.assertEqual(engine.session_window("2020-11-01 16:00:00"),"transition")
        self.assertEqual(engine.session_window("2020-11-01 18:00:00"),"asia")

    def test_larger_join_strict_prior_and_missing_completion(self):
        times=np.array(["2020-03-08T18:01:00","2020-03-08T18:04:00"],dtype="datetime64[s]")
        signals=np.array(["2020-03-08T18:04:00","NaT"],dtype="datetime64[s]")
        state,joined,tie=engine.attach_larger(signals,(times,np.array([1,-1],dtype=np.int8)))
        self.assertEqual(state.tolist(),[1,0])
        self.assertEqual(joined[0],"2020-03-08T18:01:00")
        self.assertEqual(joined[1],"")
        self.assertEqual(tie.tolist(),[True,False])

    def test_signed_movement_and_adverse_extreme(self):
        movement,adverse=engine.price_path(
            np.array([-1,1]),np.array([100,100]),np.array([98,103]),
            np.array([99,99]),np.array([97,98]),np.array([101,102]),np.array([102,103]))
        self.assertEqual(movement.tolist(),[2,3])
        self.assertEqual(adverse.tolist(),[2,2])


if __name__ == "__main__": unittest.main()
