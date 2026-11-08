"""Synthetic input-clock and saved native/local parity audits only."""
from copy import deepcopy
from datetime import date, datetime, timedelta
import csv
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "phase5/audit_development.py"
SPEC = importlib.util.spec_from_file_location("study29_phase5_audit_tests", SOURCE)
A = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = A
SPEC.loader.exec_module(A)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "synthetic.csv"
        self.day = "2026-10-19"
        self.rows = []
        opened = A.at(date(2026, 10, 11),18)
        end = A.at(date(2026, 10, 19),9,30)
        while opened < end:
            weekday, hour = opened.weekday(), opened.hour
            valid = weekday < 5 and hour != 17 and not (weekday == 4 and hour >= 17)
            valid = valid or weekday == 6 and hour >= 18
            if valid:
                self.rows.append([opened.isoformat(),100,101,99,100,10,"ignored-value"])
            opened += timedelta(minutes=5)

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        with self.path.open("w",newline="") as handle:
            writer=csv.writer(handle)
            writer.writerow(("time","open","high","low","close","Volume","derived_native_series"))
            writer.writerows(self.rows)

    def test_monday_keeps_friday_prior_and_exact_three_rth_members(self):
        windows=A.required_windows(self.day)
        self.assertEqual(len(windows),8)
        self.assertEqual(windows[0][1],A.at(date(2026,10,15),18))
        self.assertEqual(windows[0][2],A.at(date(2026,10,16),17))
        self.assertEqual([w[0] for w in windows[-3:]],[
            "composite_member_2026-10-14","composite_member_2026-10-15","composite_member_2026-10-16"])

    def test_complete_clock_coverage_excludes_terminal_future_bar(self):
        self.save();result=A.audit_csv(self.path,self.day)
        self.assertEqual(result["status"],"complete")
        self.assertEqual(result["excluded_after_cutoff_rows"],1)
        self.assertEqual(result["last_included_open"],self.day+"T09:20:00-04:00")
        self.assertEqual(result["last_included_close"],self.day+"T09:25:00-04:00")
        windows={w["window"]:w for w in result["windows"]}
        self.assertEqual(windows["previous_completed_week"]["expected_bars"],1380)
        self.assertEqual(windows["overnight_prefix"]["expected_bars"],185)
        self.assertEqual(windows["completed_RTH"]["expected_bars"],78)

    def test_missing_member_bar_identifies_both_parent_week_and_member(self):
        self.rows=[r for r in self.rows if r[0]!="2026-10-15T10:00:00-04:00"]
        self.save();result=A.audit_csv(self.path,self.day)
        failures={w["window"] for w in result["windows"] if not w["ready"]}
        self.assertEqual(failures,{"previous_completed_week","composite_member_2026-10-15"})
        self.assertEqual(result["status"],"incomplete_or_invalid")

    def test_negative_volume_is_invalid_even_with_complete_timestamps(self):
        next(r for r in self.rows if r[0]=="2026-10-16T11:00:00-04:00")[5]=-1
        self.save();result=A.audit_csv(self.path,self.day)
        failures={w["window"] for w in result["windows"] if not w["ready"]}
        self.assertEqual(failures,{"prior_full","completed_RTH","previous_completed_week","composite_member_2026-10-16"})

    def test_duplicate_history_cannot_claim_complete_coverage(self):
        self.rows.insert(1,list(self.rows[0]))
        self.save();result=A.audit_csv(self.path,self.day)
        self.assertEqual(result["duplicate_included_timestamps"],1)
        self.assertFalse(any(w["ready"] for w in result["windows"]))

    def test_decreasing_history_rejected_as_complete(self):
        self.rows[0],self.rows[1]=self.rows[1],self.rows[0]
        self.save();result=A.audit_csv(self.path,self.day)
        self.assertFalse(result["strictly_increasing_included_timestamps"])
        self.assertEqual(result["status"],"incomplete_or_invalid")

    def test_protected_date_metadata_rejected_before_read(self):
        with self.assertRaisesRegex(ValueError,"exact development"):
            A.audit_csv(Path("does-not-exist.csv"),"2026-10-21")

    def test_future_ohlcv_is_not_validated_or_consumed(self):
        self.rows[-1][1:6]=["future-invalid"]*5
        self.save()
        self.assertEqual(A.audit_csv(self.path,self.day)["status"],"complete")

    def test_missing_volume_is_recorded_as_invalid_not_zero(self):
        next(r for r in self.rows if r[0]=="2026-10-19T08:00:00-04:00")[5]=""
        self.save();result=A.audit_csv(self.path,self.day)
        self.assertEqual(result["status"],"incomplete_or_invalid")
        self.assertTrue(any(w["invalid_bars"] for w in result["windows"]))


class NativeParityTests(unittest.TestCase):
    def setUp(self):
        self.day="2026-10-15"
        self.local={"session_date":self.day,"selections":{"P0-D1":{
            "pivot":{"candidate":{"candidate_id":"model/pivot","price":100},"reason_code":"P0_BELOW_VALUE_RECLAIM","fallback":False,"status":"ready"},
            "bullish":{"status":"partial","targets":[{"rank":1,"candidate":{"candidate_id":"model/high","price":110},"reason_code":"OWN_AUCTION_EXIT"}]},
            "bearish":{"status":"partial","targets":[{"rank":1,"candidate":{"candidate_id":"model/low","price":90},"reason_code":"RANGE_EXTREME"}]}}}}
        selected={"pivot":{"candidate_id":"native/other-namespace/pivot","price":100,"reason_code":"P0_BELOW_VALUE_RECLAIM","fallback":False},
                  "bullish":{"status":"partial","targets":[{"rank":1,"candidate_id":"native/high","price":110,"reason_code":"OWN_AUCTION_EXIT"}]},
                  "bearish":{"status":"partial","targets":[{"rank":1,"candidate_id":"native/low","price":90,"reason_code":"RANGE_EXTREME"}]}}
        self.native={"schema":"abacus.study29.phase5.native-date/v1","session_date":self.day,"source":{"sha256":A.R.FIXED_HASHES["selector_pine"]},
                     "implementation":"4.0.1","control":"4.0.0","settings":deepcopy(A.NATIVE_SETTINGS),"states":{}}
        for i,state in enumerate(("cutoff","advanced","restart")):
            self.native["states"][state]={"last_included_open":self.day+"T09:20:00-04:00","last_included_close":self.day+"T09:25:00-04:00",
                "observed_at":f"2026-10-31T03:0{i}:00+00:00","selection":deepcopy(selected)}
        self.native["states"]["advanced"]["latest_observed_bar_close"]=self.day+"T09:40:00-04:00"

    def test_equal_coordinates_and_reasons_keep_distinct_native_ids(self):
        result=A.parity_values(self.native,self.local)
        self.assertTrue(result["P0_D1_numeric_reason_fallback_and_branch_status_parity"])
        mappings=result["native_model_identity_namespaces"]
        self.assertEqual(len(mappings),3)
        self.assertTrue(all(not r["identity_string_equality_claimed"] for r in mappings))
        self.assertNotEqual(mappings[0]["native_candidate_id"],mappings[0]["model_candidate_id"])

    def test_changed_native_id_after_restart_fails_even_equal_price(self):
        self.native["states"]["restart"]["selection"]["pivot"]["candidate_id"]="different-native-id"
        with self.assertRaisesRegex(ValueError,"changed after"):
            A.parity_values(self.native,self.local)

    def test_wrong_bar_boundary_fails(self):
        self.native["states"]["cutoff"]["last_included_open"]=self.day+"T09:25:00-04:00"
        with self.assertRaisesRegex(ValueError,"included-bar"):
            A.parity_values(self.native,self.local)

    def test_advance_must_reach_rth(self):
        self.native["states"]["advanced"]["latest_observed_bar_close"]=self.day+"T09:30:00-04:00"
        with self.assertRaisesRegex(ValueError,"completed RTH"):
            A.parity_values(self.native,self.local)

    def test_equal_prices_do_not_excuse_wrong_reason_or_fallback(self):
        for name,value in (("reason_code","OTHER_REASON"),("fallback",True)):
            with self.subTest(name=name):
                changed=deepcopy(self.native)
                for state in changed["states"].values():state["selection"]["pivot"][name]=value
                with self.assertRaisesRegex(ValueError,"price/reason/fallback"):
                    A.parity_values(changed,self.local)

    def test_equal_targets_do_not_excuse_wrong_branch_status(self):
        for state in self.native["states"].values():state["selection"]["bullish"]["status"]="ready"
        with self.assertRaisesRegex(ValueError,"branch status"):
            A.parity_values(self.native,self.local)

    def test_target_rank_and_reason_are_compared(self):
        for field,value in (("rank",2),("reason_code","DISTANCE_BASELINE")):
            with self.subTest(field=field):
                changed=deepcopy(self.native)
                for state in changed["states"].values():state["selection"]["bullish"]["targets"][0][field]=value
                with self.assertRaisesRegex(ValueError,"price/order/reason"):
                    A.parity_values(changed,self.local)

    def test_missing_native_identity_is_not_inferred_from_local(self):
        for state in self.native["states"].values():state["selection"]["bullish"]["targets"][0].pop("candidate_id")
        with self.assertRaisesRegex(ValueError,"actual native target identity"):
            A.parity_values(self.native,self.local)

    def test_settings_or_source_revision_cannot_be_substituted(self):
        changed=deepcopy(self.native);changed["settings"]["row_ticks"]=8
        with self.assertRaisesRegex(ValueError,"settings"):
            A.parity_values(changed,self.local)
        changed=deepcopy(self.native);changed["source"]["sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"source"):
            A.parity_values(changed,self.local)

    def test_metadata_for_another_development_session_does_not_match(self):
        self.native["session_date"]="2026-10-16"
        with self.assertRaisesRegex(ValueError,"explicit development date"):
            A.parity_values(self.native,self.local)


if __name__=="__main__":
    unittest.main()
