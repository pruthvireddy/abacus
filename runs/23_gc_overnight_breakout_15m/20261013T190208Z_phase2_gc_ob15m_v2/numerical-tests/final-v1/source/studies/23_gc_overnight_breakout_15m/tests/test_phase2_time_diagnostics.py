import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2_time_diagnostics import measure


class RecoveryTimeTests(unittest.TestCase):
    def records(self):
        return (dict(occurred=True,first_time="2020-01-01T10:00:00Z",first_time_latest="2020-01-01T10:01:00Z"),dict(breach_occurred=True,occurred=True,first_time="2020-01-01T10:15:00Z",first_time_latest="2020-01-01T10:15:00Z",first_available_at="2020-01-01T10:15:00Z",horizon_end="2020-01-01T17:00:00Z"))
    def test_delay_uses_breach_and_conservative_intraminute_bounds(self):
        b,r=self.records();x=measure(b,r)
        self.assertEqual((x["delay_minutes_source_estimate"],x["delay_minutes_lower"],x["delay_minutes_upper"]),(15.,14.,15.))
        self.assertEqual(x["post_breach_exposure_minutes_lower"],419.)
    def test_known_recovery_with_unknown_first_breach_time_has_null_delay(self):
        b,r=self.records();b.update(first_time=None,first_time_latest=None)
        x=measure(b,r);self.assertTrue(x["recovered"]);self.assertIsNone(x["delay_minutes_source_estimate"])
    def test_no_breach_is_ineligible_rather_than_censored(self):
        b,r=self.records();b.update(occurred=False,first_time=None,first_time_latest=None);r.update(breach_occurred=False,occurred=None,first_time=None,first_time_latest=None)
        x=measure(b,r);self.assertFalse(x["known_breach"]);self.assertIsNone(x["recovery_censored"])
    def test_known_breach_then_unobserved_recovery_is_censored_not_false(self):
        b,r=self.records();r.update(occurred=None,first_time=None,first_time_latest=None)
        x=measure(b,r);self.assertTrue(x["known_breach"]);self.assertTrue(x["recovery_censored"]);self.assertIsNone(x["recovered"])
    def test_backdated_recovery_is_rejected(self):
        b,r=self.records();r["first_time"]="2020-01-01T09:00:00Z"
        with self.assertRaises(ValueError):measure(b,r)


if __name__=="__main__":unittest.main()
