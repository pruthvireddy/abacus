"""Interval uncertainty and denominator tests for independent timing checks."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("time_independent",Path(__file__).resolve().parents[1]/"phase2_verify_time_recovery.py")
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)


def fixture(state=True,recovered=True):
    breach=dict(occurred=state,first_time="2024-01-02T10:00:00Z",first_time_latest="2024-01-02T10:01:00Z")
    recovery=dict(episode_id="a",broker_day="2024-01-02",year="2024",session="London",side="upper-first",horizon="remaining_broker_window",event="touch",recovery_level="midpoint",breach_occurred=state,occurred=recovered,first_time="2024-01-02T10:10:00Z",first_time_latest="2024-01-02T10:11:00Z",first_available_at="2024-01-02T10:11:00Z",horizon_end="2024-01-02T17:00:00Z")
    return breach,recovery


class IndependentTimeTests(unittest.TestCase):
    def test_interval_subtraction_and_exposure_start_at_breach(self):
        row=checker.independent_episode(*fixture())
        self.assertEqual((row["delay_minutes_source_estimate"],row["delay_minutes_lower"],row["delay_minutes_upper"]),(10,9,11))
        self.assertEqual((row["post_breach_exposure_minutes_lower"],row["post_breach_exposure_minutes_upper"]),(419,420))

    def test_same_minute_path_uncertainty_bound_never_negative(self):
        b,r=fixture();r.update(first_time=b["first_time"],first_time_latest=b["first_time_latest"])
        row=checker.independent_episode(b,r)
        self.assertEqual((row["delay_minutes_lower"],row["delay_minutes_source_estimate"],row["delay_minutes_upper"]),(0,0,1))

    def test_observed_recovery_unknown_first_times_does_not_become_zero(self):
        b,r=fixture();b.update(first_time=None,first_time_latest=None)
        row=checker.independent_episode(b,r)
        self.assertTrue(row["recovered"]);self.assertIsNone(row["delay_minutes_source_estimate"])
        summary=checker.independent_groups([row])[("all","all","combined","remaining_broker_window","midpoint","touch")]
        self.assertEqual(summary["known_recoveries"],1)
        self.assertEqual(summary["unknown_recovery_time"],1)
        self.assertEqual(summary["delay_minutes_source_estimate_denominator"],0)
        self.assertIsNone(summary["mean_delay_minutes_source_estimate"])

    def test_no_breach_and_unknown_breach_are_not_recovery_risk(self):
        rows=[checker.independent_episode(*fixture(state=False,recovered=None)),checker.independent_episode(*fixture(state=None,recovered=None))]
        summary=checker.independent_groups(rows)[("all","all","combined","remaining_broker_window","midpoint","touch")]
        self.assertEqual(summary["original_episodes"],2)
        self.assertEqual(summary["known_breach_episodes"],0)
        self.assertEqual(summary["unknown_breach_episodes"],1)
        self.assertEqual(summary["unknown_recovery"],0)

    def test_known_no_recovery_and_censor_partition(self):
        rows=[]
        for state in (True,False,None):
            b,r=fixture(recovered=state)
            if state is not True:r.update(first_time=None,first_time_latest=None,first_available_at=None)
            rows.append(checker.independent_episode(b,r))
        summary=checker.independent_groups(rows)[("all","all","combined","remaining_broker_window","midpoint","touch")]
        self.assertEqual((summary["known_recoveries"],summary["known_no_recovery"],summary["unknown_recovery"]),(1,1,1))
        self.assertEqual(summary["delay_minutes_lower_denominator"],1)

    def test_invalid_event_population_or_chronology_rejected(self):
        b,r=fixture();r["breach_occurred"]=False
        with self.assertRaisesRegex(ValueError,"population"):checker.independent_episode(b,r)
        b,r=fixture();r["first_time"]="2024-01-02T09:59:00Z"
        with self.assertRaisesRegex(ValueError,"chronology"):checker.independent_episode(b,r)


if __name__=="__main__":unittest.main()
