import unittest
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.stage2_reference import (reference_stream, reference_outcomes, reference_membership,
    week_roster, sampled_week_indices, reference_interval, weekly_sufficient)


def bars(ranges, *, interval=5, start="2018-01-02T14:00Z", ema20=105., ema50=100.):
    stamps = pd.date_range(start, periods=len(ranges), freq=f"{interval}min")
    return pd.DataFrame([dict(timestamp=t, available_at=t + pd.Timedelta(minutes=interval),
        product="ES", interval_minutes=interval, contract="ESH8", open=(lo + hi) / 2,
        high=hi, low=lo, close=(lo + hi) / 2, ema20=ema20, ema50=ema50, atr14=2.,
        usable=True, feature_valid=True, feature_reset=False, feature_source_timestamp=t,
        session="2018-01-02", quality_reason="usable", known_closure_before=False)
        for t, (lo, hi) in zip(stamps, ranges)])


class Stage2ReferenceTests(unittest.TestCase):
    def test_independent_consumption_and_dual_geometry_one_accepted(self):
        frame = bars([(106, 108), (104, 106), (99, 106), (99, 106), (106, 108), (99, 106)])
        technical, events = reference_stream(frame)
        fast = technical[technical.touch_mode == "fast"]
        slow = technical[technical.touch_mode == "slow"]
        self.assertEqual(fast.accepted.tolist(), [False, True, False, False, False, True])
        self.assertEqual(slow.accepted.tolist(), [False, False, True, False, False, True])
        member = reference_membership(frame, technical, events)["membership"]
        self.assertEqual(member.geometry.tolist(), ["neither", "fast_only", "both", "both", "neither", "both"])
        self.assertEqual(member.accepted_membership.tolist(), ["neither", "fast_only", "slow_only", "neither", "neither", "both"])
        self.assertEqual(len(set(events.event_id)), len(events))

    def test_width_reject_and_gap_consume_both_selected_states(self):
        frame = bars([(106, 108), (104, 106), (99, 101), (99, 106), (106, 108), (96, 98), (99, 106)])
        frame.loc[1, "ema20"] = 101.
        technical, _ = reference_stream(frame)
        fast = technical[technical.touch_mode == "fast"].reset_index(drop=True)
        slow = technical[technical.touch_mode == "slow"].reset_index(drop=True)
        # Narrow-cloud departure remains an arm; width rejection at a touch consumes it.
        narrow = bars([(102, 104), (100, 102), (100, 102)], ema20=101.)
        nt, ne = reference_stream(narrow)
        self.assertEqual(len(ne), 0)
        self.assertEqual(nt[nt.touch_mode == "fast"].suppression_reason.tolist(), ["no_touch", "width_below_minimum", "not_armed"])
        self.assertFalse(fast.loc[5, "armed_after"])
        self.assertFalse(slow.loc[5, "armed_after"])
        self.assertEqual(slow.loc[5, "suppression_reason"], "gap_penetration")

    def test_invalid_roll_equality_and_direction_reset(self):
        frame = bars([(106, 108)] * 7 + [(99, 106)])
        frame.loc[1, "usable"] = False
        frame.loc[3, "contract"] = "ESM8"
        frame.loc[4:, "contract"] = "ESM8"
        frame.loc[4, "ema20"] = 100.
        frame.loc[6:, "ema20"] = 95.
        tech, events = reference_stream(frame)
        slow = tech[tech.touch_mode == "slow"].reset_index(drop=True)
        self.assertEqual(slow.reset_reason.tolist(), ["direction_change", "invalid_data_or_feature", "direction_change", "contract_change", "equality", "direction_change", "direction_change", ""])
        member = reference_membership(frame, tech, events)["membership"]
        self.assertEqual(member.loc[1, "geometry"], "undefined")
        self.assertTrue(member.loc[4, "eligible"])

    def test_episode_boundaries_contacts_and_interruption(self):
        frame = bars([(106, 108), (106, 108), (104, 106), (99, 101), (106, 108), (104, 106), (104, 106)])
        tech, events = reference_stream(frame)
        bundle = reference_membership(frame, tech, events)
        self.assertEqual(len(bundle["episodes"]), 2)
        first, second = bundle["episodes"].to_dict("records")
        self.assertEqual(first["end_reason"], "new_departure")
        self.assertTrue(first["strictly_later_slow_contact"])
        self.assertTrue(first["strictly_later_slow_signal"])
        self.assertIsNone(second["strictly_later_slow_contact"])
        self.assertEqual(second["status"], "endpoint")
        self.assertEqual(bundle["pairs"].pair_relation.tolist(), ["fast_before_slow", "fast_only"])
        self.assertEqual(bundle["membership"].shared_episode_id.iloc[0], bundle["membership"].shared_episode_id.iloc[1])
        self.assertNotEqual(bundle["membership"].shared_episode_id.iloc[1], bundle["membership"].shared_episode_id.iloc[4])

    def test_warmup_first_not_replaced_and_retrospective_labels_not_acceptance(self):
        frame = bars([(106, 108), (104, 106), (99, 101)], start="2017-12-31T23:50Z")
        tech, events = reference_stream(frame)
        result = reference_membership(frame, tech, events)
        episode = result["episodes"].iloc[0]
        self.assertFalse(episode.first_fast_in_development)
        self.assertIsNone(episode.strictly_later_slow_contact)
        before = tech.accepted.tolist()
        frame2 = pd.concat([frame, bars([(99, 101)], start="2018-01-01T00:05Z")], ignore_index=True)
        after, _ = reference_stream(frame2)
        self.assertEqual(before, after.accepted.tolist()[:len(before)])

    def test_outcomes_entry_exclusion_sell_attainment_and_null_priority(self):
        frame = bars([(90, 130), (99, 110), (97, 110), (100, 104)])
        event = dict(event_id="e", product="ES", interval_minutes=5, contract="ESH8", timestamp=frame.timestamp[0],
            signal_idx=0, entry_at=frame.available_at[0], reference_price=100., direction=-1, entry_atr=2., session="2018-01-02")
        out = reference_outcomes(frame, pd.DataFrame([event]), [3])
        row = out.iloc[0]
        self.assertEqual((row.mfe, row.mae, row.terminal_delta), (3., 10., -2.))
        self.assertEqual(row.mae_attainment_start, frame.timestamp[1])
        self.assertEqual(row.mfe_attainment_start, frame.timestamp[2])
        self.assertEqual(row.mfe_atr, 1.5)
        frame.loc[1, ["usable", "contract", "quality_reason"]] = [False, None, "empty"]
        row = reference_outcomes(frame, pd.DataFrame([event]), [3]).iloc[0]
        self.assertEqual(row.censor_reason, "invalid_future_slot:empty")
        self.assertIsNone(row.mfe)
        self.assertIsNone(row.crosses_closure)

    def test_exact_week_roster_paired_multiplicity_and_empty_support(self):
        weeks = week_roster()
        self.assertEqual((len(weeks), weeks[0], weeks[-1]), (157, "2018-01-01", "2020-12-28"))
        indices = sampled_week_indices(4, 5, 123)
        for row in indices:
            for i in range(0, 156, 4):
                self.assertEqual((row[i + 1] - row[i]) % 157, 1)
        frame = pd.DataFrame([dict(status="completed", mfe=1., mae=2., terminal_delta=v,
            mfe_atr=.5, mae_atr=1., terminal_delta_atr=v / 2,
            week="2018-01-01", session="2018-01-01") for v in (1., 3.)])
        self.assertEqual(weekly_sufficient(frame)[1].sum(), 2)
        result = reference_interval(frame, frame, resamples=100, seed=3)
        self.assertEqual((result["ci_low"], result["ci_high"], result["familywise_low"], result["familywise_high"]), (0., 0., 0., 0.))
        self.assertGreater(result["undefined_draws"], 0)
        empty = frame.iloc[:0]
        self.assertIsNone(reference_interval(frame, empty, resamples=10)["ci_low"])


if __name__ == "__main__":
    unittest.main()
