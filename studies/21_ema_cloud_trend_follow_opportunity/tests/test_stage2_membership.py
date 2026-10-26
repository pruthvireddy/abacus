import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.stage2_engine import generate_streams
from src.stage2_membership import attach_episode_metadata, build_membership
from test_stage2_engine import fixture


class MembershipTest(unittest.TestCase):
    def build(self, bars):
        technical, events = generate_streams(bars, int(bars.interval_minutes.iloc[0]))
        return build_membership(bars, technical, events), technical, events

    def test_geometry_and_independent_membership_and_union_identity(self):
        bars = fixture(4)
        bars.loc[1, ["low", "high"]] = [102., 105.]
        bars.loc[2, ["low", "high"]] = [99., 105.]
        bars.loc[3, ["ema20", "low", "high"]] = [100., 99., 101.]
        result, _, events = self.build(bars)
        m = result["membership"]
        self.assertEqual(m.geometry.tolist(), ["neither", "fast_only", "both", "both"])
        self.assertEqual(m.accepted_membership.tolist(), ["neither", "fast_only", "slow_only", "neither"])
        self.assertTrue(m.eligible.all())
        self.assertEqual(m.direction.iloc[3], 0)
        self.assertEqual(len(result["union"]), 2)
        self.assertEqual(result["pairs"].pair_relation.iloc[0], "fast_before_slow")
        self.assertTrue(result["pairs"].strictly_later_slow_contact.iloc[0])
        pd.testing.assert_series_equal(events.event_id, attach_episode_metadata(events, m).event_id)

    def test_dual_same_bar_deduplicates_and_consecutive_departure_retains_episode(self):
        bars = fixture(5)
        bars.loc[2, ["low", "high"]] = [99., 105.]
        result, _, events = self.build(bars)
        m, union, pairs = result["membership"], result["union"], result["pairs"]
        self.assertEqual(m.shared_episode_id.iloc[0], m.shared_episode_id.iloc[1])
        self.assertNotEqual(m.shared_episode_id.iloc[1], m.shared_episode_id.iloc[3])
        self.assertEqual(len(events), 2)
        self.assertEqual(len(union), 1)
        self.assertEqual(union.accepted_membership.iloc[0], "both")
        self.assertTrue(union.representative_event_id.iloc[0].endswith("|slow"))
        self.assertEqual(pairs.pair_relation.iloc[0], "same_bar")
        self.assertTrue(pairs.same_bar_slow_contact.iloc[0])
        self.assertFalse(pairs.strictly_later_slow_contact.iloc[0])
        self.assertEqual(pairs.end_reason.iloc[0], "new_departure")

    def test_geometric_slow_width_rejection_differs_from_accepted_slow_contact(self):
        bars = fixture(4)
        bars.loc[1, ["low", "high"]] = [102., 105.]
        bars.loc[2, ["ema20", "low", "high"]] = [102., 99., 101.]
        result, _, _ = self.build(bars)
        pair = result["pairs"].iloc[0]
        self.assertTrue(pair.strictly_later_slow_contact)
        self.assertFalse(pair.strictly_later_slow_signal)
        self.assertEqual(pair.pair_relation, "fast_only")

    def test_reset_before_bar_and_endpoint_leave_absent_contact_unresolved(self):
        for reset in ("invalid", "roll", "equal", "direction", "source", "endpoint"):
            bars = fixture(3)
            bars.loc[1, ["low", "high"]] = [102., 105.]
            bars.loc[2, ["low", "high"]] = [102., 105.]
            if reset == "invalid": bars.loc[2, "feature_valid"] = False
            if reset == "roll": bars.loc[2, "contract"] = "B"
            if reset == "equal": bars.loc[2, "ema20"] = 100.
            if reset == "direction": bars.loc[2, "ema20"] = 97.
            if reset == "source": bars.loc[2, "feature_reset"] = True
            result, _, _ = self.build(bars)
            pair = result["pairs"].iloc[0]
            self.assertIsNone(pair.strictly_later_slow_contact, reset)
            self.assertIsNone(pair.strictly_later_slow_signal, reset)
            self.assertNotEqual(pair.status, "resolved", reset)
            if reset != "endpoint":
                self.assertEqual(pair.last_timestamp, bars.timestamp.iloc[1])
                self.assertEqual(pair.termination_timestamp, bars.timestamp.iloc[2])

    def test_warmup_first_counterpart_is_preserved_not_replaced_or_scored(self):
        bars = fixture(4, start="2018-01-01 04:50Z")
        bars.loc[1, ["low", "high"]] = [102., 105.]
        bars.loc[2, ["low", "high"]] = [99., 105.]
        result, _, events = self.build(bars)
        pair = result["pairs"].iloc[0]
        self.assertFalse(pair.first_fast_in_development)
        self.assertTrue(pair.first_slow_in_development)
        self.assertEqual(pair.pair_scope, "warmup_counterpart")
        self.assertFalse(pair.pair_in_development)
        self.assertIsNone(pair.same_bar_slow_contact)
        self.assertIsNone(pair.strictly_later_slow_contact)
        self.assertEqual(pair.retrospective_scope_reason, "outside_scope_warmup_first_fast")
        self.assertTrue(pd.isna(pair.slow_minus_fast_signal_minutes))
        self.assertTrue(pd.isna(pair.slow_minus_fast_reference_points))
        self.assertEqual(len(result["union"]), 1)
        self.assertEqual(result["union"].accepted_membership.iloc[0], "slow_only")

    def test_undefined_geometry_retains_all_support_and_known_closure_episode(self):
        bars = fixture(4)
        bars.loc[1, "usable"] = False
        bars.loc[2:, ["timestamp", "available_at"]] += pd.Timedelta(hours=1)
        bars.loc[2, "known_closure_before"] = True
        bars.loc[3, ["low", "high"]] = [99., 105.]
        result, _, _ = self.build(bars)
        m = result["membership"]
        self.assertEqual(m.geometry.iloc[1], "undefined")
        self.assertFalse(m.eligible.iloc[1])
        self.assertEqual(m.shared_episode_id.iloc[2], m.shared_episode_id.iloc[3])

    def test_reversed_first_event_order_is_retained_by_metadata_without_changing_states(self):
        bars = fixture(4)
        bars.loc[1, ["low", "high"]] = [99., 102.]
        bars.loc[2, ["low", "high"]] = [102., 105.]
        technical, events = generate_streams(bars, 5)
        # A matching-layer fixture supplies two arbitrary independently accepted
        # streams. The production engine separately tests that a slow penetration
        # consumes fast; matching must still retain reversed inputs without filtering.
        slow = events.iloc[0].copy()
        fast = slow.copy()
        for key in ("timestamp", "signal_timestamp", "available_at", "entry_at"):
            fast[key] = bars.loc[2, "timestamp" if key in ("timestamp", "signal_timestamp") else "available_at"]
        fast["event_id"] = slow.event_id.replace(slow.timestamp.isoformat(), fast.timestamp.isoformat()).replace("|slow", "|fast")
        fast["touch_mode"], fast["signal_idx"], fast["reference_price"] = "fast", 2, bars.close.iloc[2]
        event_frame = pd.DataFrame([slow, fast])
        mask = technical.touch_mode.eq("fast") & technical.signal_idx.eq(2)
        technical.loc[mask, "accepted"] = True
        technical.loc[mask, "event_id"] = fast.event_id
        result = build_membership(bars, technical, event_frame)
        self.assertEqual(result["pairs"].pair_relation.iloc[0], "slow_before_fast")
        self.assertLess(result["pairs"].slow_minus_fast_signal_minutes.iloc[0], 0)

    def test_same_bar_dual_reference_drift_and_missing_branch_roster_are_refused(self):
        bars = fixture(2)
        bars.loc[1, ["low", "high"]] = [99., 105.]
        technical, events = generate_streams(bars, 5)
        bad = events.copy()
        bad.loc[bad.touch_mode.eq("fast"), "reference_price"] += .25
        with self.assertRaisesRegex(ValueError, "reference/feature"):
            build_membership(bars, technical, bad)
        with self.assertRaisesRegex(ValueError, "every scheduled"):
            build_membership(bars, technical.iloc[1:], events)
        with self.assertRaisesRegex(ValueError, "reserved"):
            build_membership(bars, technical, events, endpoint="2022-01-01")


if __name__ == "__main__": unittest.main()
