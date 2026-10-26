import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import statistics as inherited
from src.stage2_statistics import (summarize_branches, quantiles_branches, stability_branches,
    branch_cohort_uncertainty, within_branch_comparisons, geometry_membership,
    episode_pair_metrics, episode_summary, union_outcomes, union_summary, support_roster, coverage_columns,
    verify_union_projection)
from test_stage2_comparisons import streams


def membership():
    times = pd.date_range("2019-01-02 12:00", periods=4, freq="5min", tz="UTC")
    return pd.DataFrame(dict(product="ES", interval_minutes=5, timestamp=times,
        side=["Buy", "Buy", "Buy", None], eligible=[True, True, True, True],
        fast_accepted=[True, True, False, False], slow_accepted=[True, False, True, False],
        accepted_membership=["both", "fast_only", "slow_only", "neither"],
        geometry=["both", "fast_only", "slow_only", "neither"]))


def unions(out):
    events = out.loc[out.touch_mode.eq("slow")].iloc[:3].copy()
    events["union_id"] = ["u0", "u1", "u2"]
    events["representative_event_id"] = ["slow|0", "fast|slow|1", "slow|2"]
    events["fast_event_id"] = ["fast|slow|0", "fast|slow|1", None]
    events["slow_event_id"] = ["slow|0", None, "slow|2"]
    events["accepted_membership"] = ["both", "fast_only", "slow_only"]
    return events


def pair_population():
    rows = []
    base = dict(product="ES", interval_minutes=5, direction=1, side="Buy", contains_development=True,
                first_fast_in_development=True, first_slow_in_development=True, end_reason="new_departure",
                status="resolved", slow_minus_fast_signal_minutes=5., slow_minus_fast_reference_points=1.,
                first_fast_timestamp=pd.Timestamp("2019-01-02", tz="UTC"), first_slow_timestamp=pd.Timestamp("2019-01-02 00:05", tz="UTC"),
                same_bar_slow_contact=False, strictly_later_slow_contact=True, strictly_later_slow_signal=True)
    rows.append(base | dict(pair_id="p0", shared_episode_id="e0", pair_relation="fast_before_slow", pair_scope="both_development",
                           first_fast_event_id="fast|slow|0", first_slow_event_id="slow|1"))
    rows.append(base | dict(pair_id="p1", shared_episode_id="e1", pair_relation="fast_before_slow", pair_scope="warmup_counterpart",
                           first_fast_event_id="warmup|fast", first_slow_event_id="slow|2", first_fast_in_development=False,
                           same_bar_slow_contact=None, strictly_later_slow_contact=None, strictly_later_slow_signal=None))
    rows.append(base | dict(pair_id="p2", shared_episode_id="e2", pair_relation="fast_only", pair_scope="unpaired_development",
                           first_fast_event_id="fast|slow|3", first_slow_event_id=None, first_slow_in_development=False,
                           status="interrupted", end_reason="invalid_data_or_feature", same_bar_slow_contact=False,
                           strictly_later_slow_contact=None, strictly_later_slow_signal=None))
    return pd.DataFrame(rows)


class Stage2StatisticsTest(unittest.TestCase):
    def test_all_inherited_scientific_cells_exact_for_slow_wrapper(self):
        out = streams()
        three = out.copy()
        three["interval_minutes"], three["horizon_minutes"] = 3, 45
        three["event_id"] += "|3m"
        three["mfe"] += 1.
        three["mfe_atr"] += .5
        out = pd.concat([out, three], ignore_index=True)
        slow = out.loc[out.touch_mode.eq("slow")]
        for wrapped, original in ((summarize_branches(out, ("all", "uninterrupted", "same_session")), inherited.summarize(slow, ("all", "uninterrupted", "same_session"))),
                                  (quantiles_branches(out), inherited.quantiles(slow)),
                                  (stability_branches(out, ["2019-01-02", "2019-01-03"]), inherited.stability(slow, ["2019-01-02", "2019-01-03"])),
                                  (branch_cohort_uncertainty(out, resamples=25, block_lengths=(4,)), inherited.bootstrap(slow, resamples=25, block_lengths=(4,))),
                                  (within_branch_comparisons(out), inherited.comparisons(slow))):
            if original.empty:
                self.assertTrue(wrapped.empty)
                continue
            cols = [c for c in original if c not in ("stage", "touch_mode", "row_id")]
            pd.testing.assert_frame_equal(wrapped.loc[wrapped.touch_mode.eq("slow"), cols].reset_index(drop=True), original[cols].reset_index(drop=True), check_exact=True)
            self.assertTrue(wrapped.row_id.is_unique)

    def test_geometry_and_acceptance_are_separate_and_equality_eligible_is_retained(self):
        m = membership()
        m.loc[1, "geometry"] = "both"  # selected fast only while both EMA levels touched
        table = geometry_membership(m)
        geometry = table.query("direction == 'All' and period_kind == 'all' and dimension == 'geometry'").set_index("category")
        accepted = table.query("direction == 'All' and period_kind == 'all' and dimension == 'accepted_membership'").set_index("category")
        self.assertEqual(geometry.loc["both", "count"], 2)
        self.assertEqual(accepted.loc["both", "count"], 1)
        self.assertEqual(geometry.eligible_slots.iloc[0], 4)
        self.assertEqual(geometry.scheduled_slots.iloc[0], 4)
        buy = table.query("direction == 'Buy' and period_kind == 'all'")
        self.assertTrue(buy.eligible_slots.eq(3).all())
        self.assertEqual(geometry["count"].sum(), 4)

    def test_union_deduplicates_dual_and_transfers_saved_paths(self):
        out = streams()
        u = unions(out)
        paths = union_outcomes(u, out)
        self.assertEqual(len(paths), 3)
        self.assertEqual(paths.event_id.nunique(), 3)
        self.assertTrue(paths.touch_mode.eq("union").all())
        table = union_summary(membership(), u, out)
        row = table.query("direction == 'All' and summary_kind == 'frequency'").iloc[0]
        self.assertEqual((row.fast_accepted, row.slow_accepted, row.both_accepted, row.union_accepted), (2, 2, 1, 3))
        self.assertEqual(row.incremental_vs_slow, row.incremental_fast_only)
        self.assertEqual(row.union_rate_per_1000, 750.)
        self.assertTrue(table.row_id.is_unique)
        # A single-point dual discrepancy is an error, never averaged away.
        out.loc[out.event_id.eq("fast|slow|0"), "mfe"] = 999.
        with self.assertRaisesRegex(ValueError, "same-bar dual"):
            union_outcomes(u, out)

    def test_saved_union_projection_is_verified_before_use(self):
        out = streams()
        expected = union_outcomes(unions(out), out)
        saved = expected.copy()
        saved["source_event_id"] = saved.representative_event_id
        result = verify_union_projection(expected, saved)
        self.assertEqual(len(result), 3)
        saved.loc[0, "terminal_delta"] += .25
        with self.assertRaisesRegex(ValueError, "science differs"):
            verify_union_projection(expected, saved)
        saved = expected.copy()
        saved["source_event_id"] = "wrong-source"
        with self.assertRaisesRegex(ValueError, "source differs"):
            verify_union_projection(expected, saved)
        with self.assertRaisesRegex(ValueError, "identity/support"):
            verify_union_projection(expected, expected.iloc[:2])

    def test_pair_timing_and_reference_use_both_development_first_events(self):
        pairs = pair_population()
        pairs.loc[pairs.pair_id.eq("p1"), "slow_minus_fast_signal_minutes"] = 10000.
        metrics = episode_pair_metrics(pairs, streams())
        self.assertTrue(metrics.loc[metrics.pair_id.eq("p1"), "slow_minus_fast_signal_minutes"].isna().all())
        table = episode_summary(pairs, metrics)
        row = table.query("direction == 'All' and summary_kind == 'pair_timing_reference' and category == 'slow_minus_fast_signal_minutes'").iloc[0]
        self.assertEqual(row.evaluable, 1)
        self.assertEqual(row.mean_difference, 5.)

    def test_first_warmup_event_is_not_replaced_and_interruptions_remain_unknown(self):
        out = streams()
        pairs = pair_population()
        metrics = episode_pair_metrics(pairs, out)
        warmup = metrics.loc[metrics.pair_id.eq("p1")]
        self.assertTrue(warmup.first_fast_event_id.eq("warmup|fast").all())
        self.assertTrue(warmup.pair_outcome_status.eq("outside_pair_scope").all())
        self.assertTrue(warmup.difference_terminal_delta.isna().all())
        table = episode_summary(pairs, metrics)
        contact = table.query("direction == 'All' and summary_kind == 'strictly_later_slow_contact'").set_index("category")
        self.assertEqual(contact.loc["unresolved", "count"], 1)
        self.assertEqual(contact.loc["true", "count"], 1)
        self.assertEqual(contact.loc["false", "count"], 0)
        self.assertTrue(contact.descriptor_eligible.eq(2).all())

    def test_pair_censored_counterpart_and_atr_missing_have_null_differences(self):
        out = streams()
        out.loc[out.event_id.eq("slow|1"), "status"] = "censored"
        metrics = episode_pair_metrics(pair_population(), out)
        selected = metrics.query("pair_id == 'p0' and horizon == 15")
        self.assertTrue(selected.pair_outcome_status.eq("censored_counterpart").all())
        self.assertTrue(selected.difference_terminal_delta.isna().all())
        out = streams()
        out.loc[out.event_id.eq("slow|1"), "terminal_delta_atr"] = np.nan
        metrics = episode_pair_metrics(pair_population(), out)
        row = metrics.query("pair_id == 'p0' and horizon == 15 and unit == 'atr'").iloc[0]
        self.assertEqual(row.pair_outcome_status, "normalization_missing")
        self.assertTrue(pd.isna(row.difference_terminal_delta))

    def test_causal_support_is_not_doubled_by_two_streams(self):
        m = membership()
        slow = m.copy()
        slow["usable"], slow["feature_valid"], slow["touch_mode"], slow["session"] = True, True, "slow", "2019-01-02"
        slow.loc[0, "feature_valid"] = False
        fast = slow.copy()
        fast["touch_mode"] = "fast"
        roster, sessions = support_roster(pd.concat([fast, slow], ignore_index=True))
        table = pd.DataFrame([dict(product="ES", interval_minutes=5, direction="All", period_kind="session", period="2019-01-02", accepted=0)])
        row = coverage_columns(table, roster).iloc[0]
        self.assertEqual((row.scheduled_slots, row.eligible_slots, row.unknown_signal_slots), (4, 3, 1))
        self.assertFalse(row.coverage_complete)
        self.assertEqual(row.zero_event_qualification, "auditable_eligible_support")
        self.assertEqual(sessions, ["2019-01-02"])


if __name__ == "__main__":
    unittest.main()
