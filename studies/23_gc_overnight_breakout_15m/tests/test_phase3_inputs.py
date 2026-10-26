"""Synthetic timing/quality and formula checks; no historical policy outcomes."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phase3_inputs import (CloudBar, CloudTimeline, audit_feature_recurrence,
                           cloud_bars, expected_cloud_slots, ordinary, verify_record,
                           parent_order_update_times, parent_order_updates, audit_cloud_contracts)

UTC = timezone.utc
T = datetime(2020, 1, 2, 4, tzinfo=UTC)
FIVE = timedelta(minutes=5)


def bar(t=T, **changes):
    return replace(CloudBar(t, t + FIVE, "GC:1:2020:2:GCG0", 100., 102., 99., 101.,
                            100., 99., 2., True, True, 250), **changes)


class TimelineTests(unittest.TestCase):
    def test_completion_and_opening_snapshot_do_not_use_current_close(self):
        old, new = bar(), bar(T + FIVE, ema20=105.)
        timeline = CloudTimeline([old, new], [T, T + FIVE])
        self.assertFalse(timeline.snapshot(T + FIVE - timedelta(microseconds=1)).known)
        self.assertEqual(timeline.snapshot(T + FIVE).ema20, old.ema20)
        self.assertEqual(timeline.snapshot(T + 2 * FIVE).ema20, new.ema20)

    def test_invalid_latest_never_forward_fills(self):
        invalid = bar(T + FIVE, usable=False, feature_valid=False, consecutive_count=0,
                      quality_reason="missing_source_minutes")
        timeline = CloudTimeline([bar(), invalid], [T, T + FIVE])
        s = timeline.snapshot(T + 2 * FIVE)
        self.assertFalse(s.known)
        self.assertEqual(s.reason, "unusable_latest_expected_slot")
        self.assertIsNone(s.ema20)

    def test_missing_latest_retains_null_quality_slot(self):
        timeline = CloudTimeline([bar()], [T, T + FIVE])
        self.assertEqual(timeline.snapshot(T + 2 * FIVE).reason, "missing_latest_expected_slot")
        rows = timeline.for_window(T, T + 2 * FIVE)
        self.assertEqual(len(rows), 2)
        self.assertFalse(rows[1].usable)
        self.assertIsNone(rows[1].open)
        self.assertEqual(rows[1].quality_reason, "missing_expected_slot")

    def test_missing_prefix_cannot_keep_old_saved_feature_validity(self):
        slots = [T + FIVE * i for i in range(252)]
        rows = [bar(t, consecutive_count=250+i) for i,t in enumerate(slots) if i != 1]
        timeline = CloudTimeline(rows, slots)
        self.assertEqual(timeline.snapshot(slots[2] + FIVE).reason, "unknown_feature_prefix_gap")
        self.assertFalse(timeline.snapshot(slots[250] + FIVE).known)
        self.assertTrue(timeline.snapshot(slots[251] + FIVE).known)

    def test_known_closure_preserves_cloud_and_expected_adjacency(self):
        later = T + timedelta(hours=2)
        timeline = CloudTimeline([bar(), bar(later, known_closure_before=True)], [T, later])
        self.assertTrue(timeline.snapshot(T + timedelta(hours=1)).known)
        self.assertTrue(timeline.snapshot(later + FIVE).known)
        self.assertTrue(timeline.adjacent(T, later))
        self.assertEqual(timeline.snapshot(later + FIVE).aligned_count, 2)
        self.assertEqual(timeline.snapshot(later + FIVE).aligned_duration_minutes, 120.)

    def test_warmup_values_are_retained_but_unavailable_for_decisions(self):
        warm = bar(feature_valid=False, consecutive_count=249)
        timeline = CloudTimeline([warm], [T])
        self.assertIsNotNone(timeline.snapshot(T + FIVE).bar.ema20)
        self.assertIsNone(timeline.snapshot(T + FIVE).ema20)
        self.assertEqual(timeline.snapshot(T + FIVE).reason, "warmup_or_invalid_feature")

    def test_valid_flag_before_250_is_rejected(self):
        with self.assertRaises(ValueError):
            CloudTimeline([bar(consecutive_count=249)], [T])

    def test_contract_match_and_new_contract_neutrality(self):
        timeline = CloudTimeline([bar()], [T])
        self.assertEqual(timeline.snapshot(T + FIVE, "other").reason, "contract_mismatch")
        self.assertTrue(timeline.snapshot(T + FIVE, bar().contract).known)

    def test_equal_ema_is_neutral(self):
        neutral = bar(ema50=100.)
        timeline = CloudTimeline([neutral], [T])
        self.assertEqual(timeline.snapshot(T + FIVE).direction, 0)
        self.assertEqual(timeline.snapshot(T + FIVE).aligned_count, 0)
        self.assertEqual(neutral.upper, neutral.lower)

    def test_aligned_duration_retains_left_censored_prefix(self):
        slots=[T,T+FIVE,T+2*FIVE]
        timeline=CloudTimeline([bar(t) for t in slots],slots)
        first=timeline.snapshot(T+FIVE)
        last=timeline.snapshot(T+3*FIVE)
        self.assertFalse(first.alignment_start_known)
        self.assertTrue(first.duration_left_censored)
        self.assertTrue(last.duration_left_censored)
        self.assertEqual(last.aligned_count,3)
        self.assertEqual(last.aligned_duration_minutes,10.)

    def test_known_neutral_or_opposite_transition_establishes_alignment_start(self):
        for prior in [bar(ema20=99.,ema50=99.),bar(ema20=98.,ema50=99.)]:
            timeline=CloudTimeline([prior,bar(T+FIVE),bar(T+2*FIVE)],[T,T+FIVE,T+2*FIVE])
            snapshot=timeline.snapshot(T+3*FIVE)
            self.assertTrue(snapshot.alignment_start_known)
            self.assertFalse(snapshot.duration_left_censored)
            self.assertEqual(snapshot.aligned_count,2)

    def test_three_bar_slope_uses_four_adjacent_observations(self):
        slots = [T + FIVE * i for i in range(4)]
        rows = [bar(t, ema20=100.+i, ema50=99.+i/2) for i,t in enumerate(slots)]
        timeline = CloudTimeline(rows, slots)
        self.assertIsNone(timeline.snapshot(slots[2] + FIVE).slope20_3)
        last = timeline.snapshot(slots[3] + FIVE)
        self.assertEqual(last.slope20_3, 3.)
        self.assertEqual(last.slope50_3, 1.5)
        self.assertEqual(last.width_change_3, 1.5)

    def test_slope_does_not_skip_invalid_slot_or_contract_reset(self):
        slots = [T + FIVE * i for i in range(4)]
        invalid = bar(slots[1], usable=False, feature_valid=False, consecutive_count=0)
        timeline = CloudTimeline([bar(slots[0]), invalid, bar(slots[2]), bar(slots[3])], slots)
        self.assertIsNone(timeline.snapshot(slots[3] + FIVE).slope20_3)
        self.assertEqual(timeline.snapshot(slots[3] + FIVE).aligned_count, 2)

    def test_full_post_fill_candle_excludes_partial_candle(self):
        slots = [T + FIVE * i for i in range(4)]
        timeline = CloudTimeline([bar(t) for t in slots], slots)
        rows = timeline.for_window(T, T + 4 * FIVE, full_after=T + timedelta(minutes=2, seconds=59))
        self.assertEqual([r.timestamp for r in rows], slots[1:])

    def test_year_boundary_does_not_restart_alignment(self):
        old = datetime(2020, 12, 31, 23, 55, tzinfo=UTC)
        new = old + FIVE
        timeline = CloudTimeline([bar(old), bar(new)], [old, new])
        self.assertEqual(timeline.snapshot(new + FIVE).aligned_count, 2)

    def test_naive_delayed_duplicate_and_invalid_ohlc_refused(self):
        for rows,slots in [([bar(T.replace(tzinfo=None))],[T]),
                           ([bar(available_at=T+timedelta(minutes=6))],[T]),
                           ([bar(),bar()],[T]),([bar(high=98.)],[T])]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                CloudTimeline(rows, slots)

    def test_retained_endpoint_does_not_extend_cloud_forever(self):
        timeline = CloudTimeline([bar()], [T])
        self.assertTrue(timeline.snapshot(T + FIVE).known)
        self.assertEqual(timeline.snapshot(T + FIVE + timedelta(seconds=1)).reason, "outside_retained_coverage")


class NumericalAndPinTests(unittest.TestCase):
    def test_full_maturity_contract_and_mapping_bounds_are_checked(self):
        frame=pd.DataFrame({"contract_count":[1],"contract":["GC:1:2020:2:GCG0"],
                            "raw_symbol":["GCG0"],"roll_id":[1],"session":["2020-01-02"]})
        master=pd.DataFrame({"product":["GC"],"roll_id":[1],"instrument_id":[1],
            "maturity_year":[2020],"maturity_month":[2],"raw_symbol":["GCG0"],
            "mapping_start":["2020-01-01"],"mapping_end":["2020-02-01"]})
        self.assertEqual(audit_cloud_contracts(frame,master)["composite_contracts"],1)
        frame.loc[0,"contract"]="GC:1:2010:2:GCG0"
        with self.assertRaises(ValueError):audit_cloud_contracts(frame,master)
        frame.loc[0,"contract"]="GC:1:2020:2:GCG0"
        frame.loc[0,"session"]="2020-02-01"
        with self.assertRaises(ValueError):audit_cloud_contracts(frame,master)

    def test_saved_frame_adapter_preserves_quality_and_raw_unrounded_values(self):
        raw=bar(ema20=100.0123456789)
        invalid=bar(T+FIVE,contract=None,open=None,high=None,low=None,close=None,
            ema20=None,ema50=None,atr14=None,usable=False,feature_valid=False,consecutive_count=0,
            quality_reason="empty_bucket")
        converted=cloud_bars(pd.DataFrame([asdict(raw),asdict(invalid)]))
        self.assertEqual(converted,(raw,invalid))
        self.assertEqual(converted[0].ema20,100.0123456789)
        self.assertIsNone(converted[1].close)

    def test_source_updates_keep_original_15m_schedule_and_skip_unusable(self):
        times=pd.date_range(T, periods=5, freq="15min")
        frame=pd.DataFrame({"timestamp":times,"contract":["GC","GC","GC","other","GC"],
                            "usable":[True,False,True,True,True]})
        first=T+timedelta(minutes=15)
        updates=parent_order_update_times(frame,first_submission=first,
            shadow_event_time=T+timedelta(minutes=75),cutoff=T+timedelta(hours=13),contract="GC")
        self.assertEqual(updates,(first,T+timedelta(minutes=45),T+timedelta(minutes=75)))

    def test_source_update_preserves_coincident_later_shadow_as_candidate(self):
        frame=pd.DataFrame({"timestamp":[pd.Timestamp(T)],"contract":["GC"],"usable":[True]})
        first=T
        updates=parent_order_update_times(frame,first_submission=first,
            shadow_event_time=T+timedelta(minutes=15),cutoff=T+timedelta(hours=13),contract="GC")
        self.assertEqual(updates,(first,T+timedelta(minutes=15)))
        records=parent_order_updates(frame,first_submission=first,
            shadow_event_time=T+timedelta(minutes=15),cutoff=T+timedelta(hours=13),contract="GC")
        self.assertEqual(records[0]["kind"],"saved_initial_submission")
        self.assertEqual(records[1]["kind"],"inferred_source_recalculation")
        self.assertTrue(records[1]["coincident_shadow"])
        self.assertEqual(records[1]["timing_rule"],"candidate_update_requires_admission_tie_resolution")

    def constant_frame(self, n=251):
        times = pd.date_range(T, periods=n, freq="5min")
        return pd.DataFrame({"timestamp": times, "contract": "GC", "usable": True,
            "known_closure_before": False, "close": 100., "high": 101., "low": 99.,
            "ema20": 100., "ema50": 100., "true_range": 2.,
            "atr14": [np.nan]*13+[2.]*(n-13), "consecutive_count": np.arange(1,n+1),
            "feature_valid": np.arange(n)>=249, "feature_reset": [True]+[False]*(n-1)})

    def test_first_close_seed_wilder_seed_and_250th_observation(self):
        result = audit_feature_recurrence(self.constant_frame())
        self.assertEqual(result["comparisons"], 251*7)
        self.assertEqual(result["maximum_errors"], {k:0. for k in ["ema20","ema50","atr14","true_range"]})

    def test_closed_form_ema_decay_after_a_step(self):
        frame = self.constant_frame()
        frame.loc[1:, ["close","high","low"]] = [121.,122.,120.]
        k=np.arange(251)
        frame["ema20"]=121.-21.*(19./21.)**k
        frame["ema50"]=121.-21.*(49./51.)**k
        frame.loc[0,"true_range"]=2.
        frame.loc[1,"true_range"]=22.
        frame.loc[2:,"true_range"]=2.
        frame.loc[13,"atr14"]=48./14.
        for i in range(14,251):frame.loc[i,"atr14"]=(13*frame.loc[i-1,"atr14"]+2)/14
        self.assertEqual(audit_feature_recurrence(frame)["result"], "passed")

    def test_formula_drift_and_validity_drift_fail(self):
        frame=self.constant_frame(); frame.loc[100,"ema20"]+=.0001
        with self.assertRaises(ValueError):audit_feature_recurrence(frame)

    def test_invalid_quality_slot_resets_and_preserves_declared_reason(self):
        frame=self.constant_frame(501)
        frame["quality_reason"]=""
        frame["feature_reset_reason"]=""
        frame.loc[0,"feature_reset_reason"]="segment_start"
        frame.loc[250,"usable"]=False
        frame.loc[250,"quality_reason"]="missing_source_minutes"
        frame.loc[250,"feature_reset_reason"]="missing_source_minutes"
        frame.loc[251,"feature_reset_reason"]="segment_start"
        frame.loc[250:,"consecutive_count"]=np.arange(251)
        frame.loc[250:,"feature_valid"]=np.arange(251)>=250
        frame.loc[250:251,"feature_reset"]=True
        frame.loc[250,["ema20","ema50","atr14","true_range"]]=np.nan
        frame.loc[251:263,"atr14"]=np.nan
        self.assertEqual(audit_feature_recurrence(frame)["fields"],8)
        frame.loc[250,"feature_reset_reason"]="calendar_uncertified"
        with self.assertRaises(ValueError):audit_feature_recurrence(frame)
        frame=self.constant_frame(); frame.loc[248,"feature_valid"]=True
        with self.assertRaises(ValueError):audit_feature_recurrence(frame)

    def test_new_contract_resets_seed_and_warmup(self):
        frame=self.constant_frame(500)
        frame.loc[250:,"contract"]="GC-next"
        frame.loc[250:,"consecutive_count"]=np.arange(1,251)
        frame.loc[250:,"feature_valid"]=np.arange(250)>=249
        frame.loc[250,"feature_reset"]=True
        frame.loc[250:262,"atr14"]=np.nan
        self.assertEqual(audit_feature_recurrence(frame)["result"], "passed")

    def test_calendar_preserves_maintenance_but_retains_uncertified_holiday(self):
        roster=expected_cloud_slots("2020-01-01","2020-01-03T22:00:00Z")
        ny=roster.timestamp.dt.tz_convert("America/New_York")
        self.assertFalse(ny.dt.hour.eq(17).any())
        self.assertFalse(roster.loc[roster.session.eq("2020-01-01"),"calendar_valid"].any())
        self.assertEqual(roster.groupby("session").size().tolist(), [276,276,276])

    def test_actual_byte_pin_and_path_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/"data").write_bytes(b"unchanged")
            row={"path":"data","bytes":9,"sha256":hashlib.sha256(b"unchanged").hexdigest()}
            self.assertEqual(verify_record(root,row)["bytes"],9)
            (root/"data").write_bytes(b"different")
            with self.assertRaises(ValueError):verify_record(root,row)
            with self.assertRaises(ValueError):ordinary(root,"../data")
            (root/"alias").symlink_to(root/"data")
            with self.assertRaises(ValueError):ordinary(root,"alias")


if __name__ == "__main__":
    unittest.main()
