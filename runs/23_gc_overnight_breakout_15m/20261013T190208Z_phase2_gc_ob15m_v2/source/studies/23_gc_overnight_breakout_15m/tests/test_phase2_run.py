import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2_run import normalize, select_primary, execute_phase, level_summaries
from src.phase2_engine import policy_specs


class ChronologicalRunnerTests(unittest.TestCase):
    def test_normalization_does_not_rescue_censors_with_zero(self):
        for source,target in (("unknown_signal","unknown"),("unknown_fill","unknown"),("filled_censored","censored"),("known_no_fill","no_fill")):
            r=normalize(dict(status=source,trade=None,signal_available_at=None,unknown=source.startswith("unknown"),opportunity=False))
            self.assertEqual(r["status"],target)
            self.assertEqual(r["opportunity_seen"],None if source.startswith("unknown") else False)

    def fixture(self):
        policies=[p.name for p in policy_specs() if p.kind=="reclaim"]
        baseline={str(i):dict(direction=1,status="completed",net_dollars=100.,entry_time=f"{2021+i%2}-02-01T05:00:00Z",broker_day=f"{2021+i%2}-02-01") for i in range(100)}
        results={p:[dict(episode_id=k,status="completed",trade={"net_dollars":200.}) for k in baseline] for p in policies}
        return baseline,results,policies

    def test_selection_has_support_threshold_and_shallower_tie_break(self):
        b,r,p=self.fixture()
        s=select_primary(r,b)
        self.assertEqual(s["selected_policy"],p[0])
        self.assertFalse(s["later_alternative_outcomes_opened"])
        self.assertEqual(s["candidates"][0]["completed_fills"],100)
        self.assertEqual(s["candidates"][0]["years_with_completed_fills"],["2021","2022"])

    def test_missing_other_policy_excludes_joint_contrast_not_becomes_zero(self):
        b,r,p=self.fixture()
        for item in r[p[-1]]:item.update(status="unknown",trade=None)
        s=select_primary(r,b)
        self.assertIsNone(s["selected_policy"])
        self.assertTrue(all(x["common_complete_pairs"]==0 for x in s["candidates"]))

    def test_later_outcomes_do_not_choose_the_validation_rule(self):
        b,r,p=self.fixture()
        b["future"]=dict(direction=1,status="completed",net_dollars=0,entry_time="2025-05-01T05:00:00Z",broker_day="2025-05-01")
        for policy in p:r[policy].append(dict(episode_id="future",status="completed",trade={"net_dollars":1e9 if policy==p[-1] else -1e9}))
        self.assertEqual(select_primary(r,b)["selected_policy"],p[0])

    def test_executed_phase_refusal_preserves_old_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage=Path(tmp);folder=stage/"phases/later";folder.mkdir(parents=True);marker=folder/"keep";marker.write_bytes(b"sealed-like")
            with self.assertRaises(FileExistsError):execute_phase(stage,"later")
            self.assertEqual(marker.read_bytes(),b"sealed-like")

    def test_level_path_diagnostics_use_only_known_event_population(self):
        baseline={"yes":dict(entry_time="2021-02-01T05:00:00Z"),"no":dict(entry_time="2021-02-02T05:00:00Z"),"unknown":dict(entry_time="2021-02-03T05:00:00Z")}
        raw=[dict(episode_id=k,year="2021",session="Asia",side="upper-first",fraction=.5,event="touch",occurred=flag,range_recovery_before_opposite=True if flag is True else None,excursion_success=None,repeat_contacts=0 if flag is False else None,mfe_after_touch_points=4. if flag is True else None,mae_after_touch_points=2. if flag is True else None,deepest_range_fraction=.6 if flag is True else None,event_risk_points=10.) for k,flag in (("yes",True),("no",False),("unknown",None))]
        row=next(r for r in level_summaries(raw,baseline) if r["year"]=="all" and r["session"]=="all" and r["side"]=="combined")
        self.assertEqual((row["episodes"],row["known_denominator"],row["unknown"]),(3,2,1))
        self.assertEqual(row["range_recovery_known_denominator"],1)
        self.assertEqual(row["first_1r_success_unknown"],1)
        self.assertEqual(row["mean_mfe_after_touch_points"],4.)
        self.assertEqual(row["mean_mae_after_touch_points"],2.)
        self.assertEqual(row["mean_deepest_range_fraction"],.6)
        self.assertEqual(row["mfe_after_touch_points_denominator"],1)
        self.assertTrue(row["not_realized_trade_return"])

if __name__=="__main__":unittest.main()
