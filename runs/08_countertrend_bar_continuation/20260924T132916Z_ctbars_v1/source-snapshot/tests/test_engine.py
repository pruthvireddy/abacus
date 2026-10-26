import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ENGINE = Path(__file__).resolve().parents[1] / "src" / "engine.py"
spec = importlib.util.spec_from_file_location("study08_engine", ENGINE)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
SUMMARIZE = Path(__file__).resolve().parents[1] / "summarize.py"
summary_spec = importlib.util.spec_from_file_location("study08_summarize", SUMMARIZE)
summary = importlib.util.module_from_spec(summary_spec)
summary_spec.loader.exec_module(summary)


def rows(directions, starts=None, date="2020-03-09", status=None):
    n = len(directions)
    if starts is None:
        starts = pd.date_range("2020-03-08 18:00:00", periods=n, freq="min").strftime("%Y-%m-%d %H:%M:%S").tolist()
    if status is None: status = [engine.STATUS_STRICT]*(n-1)+["unavailable_session_boundary"]
    close = [100 + x*.25 for x in directions]
    return pd.DataFrame({"source_row":range(1,n+1),"source_timestamp":starts,
        "bar_start_timestamp":starts,"bar_completion_timestamp_proxy":starts[1:]+[None],
        "bar_duration_seconds_proxy":[60.]*(n-1)+[np.nan],
        "completion_proxy_status":status,"session_date_proxy":[date]*n,
        "open":[100.]*n,"high":[max(100.,v)+.25 for v in close],
        "low":[min(100.,v)-.25 for v in close],"close":close})


class ExtractionTests(unittest.TestCase):
    def test_two_more_excludes_c1_and_doji_breaks(self):
        df = rows([1,1,1,-1,-1,-1,1,0,-1,-1,-1])
        out,_ = engine.extract_session(df,"ES",5)
        first = out.loc[out.source_row==4].iloc[0]
        self.assertEqual((first.prior_run,first.prior_bin),(3,"3-4"))
        self.assertTrue(first.primary_eligible)
        self.assertTrue(first.c2_c3_follow)
        self.assertEqual(first.subsequent_run_length,2)
        # The doji prevents the later down bar from being the first reversal.
        self.assertNotIn(9,out.source_row.tolist())

    def test_boundaries_and_doji_outcomes(self):
        df = rows([1,1,-1,0,-1,-1])
        out,_ = engine.extract_session(df,"ES",5)
        first = out.iloc[0]
        self.assertTrue(first.primary_eligible)
        self.assertFalse(first.c2_follows)
        self.assertTrue(first.c2_doji)
        self.assertFalse(first.immediate_resumption)
        self.assertFalse(first.three_eligible)
        self.assertFalse(out.iloc[-1].primary_eligible) if len(out)>1 else None

    def test_same_second_and_strict_larger_join(self):
        df = rows([1,1,-1,-1,-1,1])
        df.loc[2,"completion_proxy_status"] = engine.STATUS_SAME
        times = np.array(["2020-03-08T18:01:00","2020-03-08T18:03:00"],dtype="datetime64[s]")
        out,_ = engine.extract_session(df,"ES",5,(times,np.array([1,-1],dtype=np.int8)))
        first = out.iloc[0]
        self.assertFalse(first.primary_eligible)
        self.assertTrue(first.c1_same_second)
        self.assertTrue(first.larger_equal_second_tie)
        self.assertEqual(first.larger_direction,1)
        self.assertEqual(first.larger_completion,"2020-03-08T18:01:00")

    def test_sessions_and_dst_wall_clock(self):
        self.assertEqual(engine.session_window("2020-03-08 02:59:59"),"asia")
        self.assertEqual(engine.session_window("2020-03-08 03:00:00"),"london_pre_ny")
        self.assertEqual(engine.session_window("2020-11-01 09:30:00"),"ny_morning")
        self.assertEqual(engine.session_window("2020-11-01 16:00:00"),"transition")
        self.assertEqual(engine.session_window("2020-11-01 18:00:00"),"asia")
        # No second timezone conversion: wall time is classified as stored.

    def test_primary_denominator_requires_strict_c2_and_c3_completion(self):
        df = rows([1,1,-1,-1,-1,1,1])
        out,_ = engine.extract_session(df,"ES",5)
        self.assertTrue(out.iloc[0].primary_eligible)
        df.loc[4,"completion_proxy_status"] = engine.STATUS_SAME
        out,_ = engine.extract_session(df,"ES",5)
        self.assertFalse(out.iloc[0].primary_eligible)
        self.assertTrue(out.iloc[0].c2_c3_follow)
        self.assertFalse(out.iloc[0].three_eligible)

    def test_three_more_requires_c4_and_its_completion(self):
        df = rows([1,1,-1,-1,-1,-1,1])
        out,_ = engine.extract_session(df,"ES",5)
        self.assertTrue(out.iloc[0].three_eligible)
        self.assertTrue(out.iloc[0].c2_c3_c4_follow)
        df.loc[5,"completion_proxy_status"] = "unavailable_session_boundary"
        out,_ = engine.extract_session(df,"ES",5)
        self.assertTrue(out.iloc[0].primary_eligible)
        self.assertFalse(out.iloc[0].three_eligible)

    def test_equal_second_larger_ties_are_removed_from_primary_pair_cohort(self):
        df = pd.DataFrame({"larger_context":["against","aligned","unavailable"],
                           "larger_equal_second_tie":[False,True,False],
                           "source_row":[1,2,3]})
        self.assertEqual(summary.strict_larger_cohort(df).source_row.tolist(),[1])

    def test_session_final_c1_has_no_larger_state_without_completion(self):
        df = rows([1,1,-1])
        times = np.array(["2020-03-08T18:01:00"],dtype="datetime64[s]")
        out,_ = engine.extract_session(df,"ES",5,(times,np.array([1],dtype=np.int8)))
        self.assertFalse(out.iloc[0].primary_eligible)
        self.assertEqual(out.iloc[0].larger_context,"unavailable")
        self.assertEqual(out.iloc[0].larger_completion,"")


if __name__ == "__main__": unittest.main()
