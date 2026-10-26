import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.stage2_comparisons import (branch_contrasts, calendar_sufficient_statistics,
                                    paired_uncertainty, validate_outcomes)
from src.statistics import calendar_weights
from src.stage2_contract import PRIMARY_FAMILY_SIZE
from test_statistics import population


def streams():
    slow = population()
    slow["touch_mode"], slow["stage"] = "slow", 2
    slow["event_id"] = "slow|" + slow.event_id.astype(str)
    fast = slow.copy()
    fast["touch_mode"], fast["event_id"] = "fast", "fast|" + fast.event_id.astype(str)
    return pd.concat([fast, slow], ignore_index=True)


class Stage2ComparisonsTest(unittest.TestCase):
    def test_primary_separate_populations_do_not_require_event_matching(self):
        out = streams()
        fast = out.touch_mode.eq("fast")
        out.loc[fast, "timestamp"] += pd.Timedelta(minutes=5)
        out.loc[fast, "terminal_delta"] += 2.
        result = branch_contrasts(out)
        row = result.query("direction == 'All' and horizon == 15 and unit == 'points' and metric == 'terminal_delta' and weighting == 'event' and support == 'all'").iloc[0]
        self.assertEqual(row.estimate, 2.)
        self.assertEqual((row.fast_accepted, row.slow_accepted), (4, 4))
        self.assertEqual(row.analysis_role, "primary")
        self.assertEqual(row.block_weeks, 0)
        self.assertTrue(result.row_id.is_unique)

    def test_complete_calendar_and_whole_sunday_monday_session_assignment(self):
        out = streams().iloc[:3].copy()
        out["session"] = ["2019-01-07", "2019-01-07", "2019-01-08"]
        out["week"] = ["2018-12-31", "2019-01-07", "2019-01-07"]
        out["terminal_delta"] = [0., 10., 20.]
        suff = calendar_sufficient_statistics(out)
        group = suff.query("product == 'ES' and interval_minutes == 5 and direction == 'All' and touch_mode == 'fast' and horizon == 15 and unit == 'points' and support == 'all' and metric == 'terminal_delta' and weighting == 'session'")
        self.assertEqual(len(group), 157)
        self.assertEqual((group.week.min(), group.week.max()), ("2018-01-01", "2020-12-28"))
        self.assertEqual(group["count"].sum(), 2)
        self.assertEqual(group["sum"].sum(), 25.)
        self.assertEqual(group.set_index("week").loc["2018-12-31", "count"], 0)
        self.assertEqual(group.set_index("week").loc["2019-01-07", "count"], 2)

    def test_identical_branches_are_exact_zero_paired_not_independent(self):
        out = streams()
        result = paired_uncertainty(out, resamples=80, block_lengths=(4,))
        group = result.query("product == 'ES' and interval_minutes == 5 and horizon == 15 and direction == 'All'")
        self.assertTrue(group.estimate.eq(0).all())
        self.assertTrue(group.ci_low.eq(0).all())
        self.assertTrue(group.ci_high.eq(0).all())
        self.assertEqual(len(result.query("interval_type == 'bonferroni'")), PRIMARY_FAMILY_SIZE)
        self.assertTrue(result.row_id.is_unique)

    def test_reference_sampled_indices_reconcile_pointwise_and_bonferroni(self):
        slow = population().iloc[[0]].copy()
        rows = []
        weeks, _ = calendar_weights(resamples=1)
        for branch in ("fast", "slow"):
            for i, week in enumerate(weeks):
                row = slow.iloc[0].to_dict()
                row.update(event_id=f"{branch}|{i}", touch_mode=branch, stage=2,
                           timestamp=pd.Timestamp(week, tz="America/New_York") + pd.Timedelta(hours=12),
                           terminal_at=pd.Timestamp(week, tz="America/New_York") + pd.Timedelta(hours=13),
                           session=week, week=week, terminal_delta=float(i % 13 if branch == "fast" else -(i % 7)))
                rows.append(row)
        out = pd.DataFrame(rows)
        b, seed, block = 200, 811, 4
        result = paired_uncertainty(out, resamples=b, seed=seed, block_lengths=(block,))
        rng = np.random.default_rng(seed)
        starts = rng.integers(0, 157, size=(b, 40))
        indices = np.array([[(int(start) + j) % 157 for start in draw for j in range(4)][:157] for draw in starts])
        diffs = np.mean((np.arange(157) % 13)[indices], axis=1) + np.mean((np.arange(157) % 7)[indices], axis=1)
        selected = result.query("product == 'ES' and interval_minutes == 5 and direction == 'All' and unit == 'points' and support == 'all' and metric == 'terminal_delta' and weighting == 'event'")
        for interval_type, tails in (("pointwise95", [.025, .975]), ("bonferroni", [.05 / 12, 1 - .05 / 12])):
            row = selected.loc[selected.interval_type.eq(interval_type)].iloc[0]
            np.testing.assert_allclose([row.ci_low, row.ci_high], np.quantile(diffs, tails, method="linear"), rtol=0, atol=1e-12)
            self.assertEqual((row.tail_low, row.tail_high), tuple(tails))
            self.assertEqual((row.defined_draws, row.undefined_draws), (b, 0))

    def test_absent_branch_is_null_and_undefined_not_zero(self):
        out = streams().query("touch_mode == 'slow'")
        result = paired_uncertainty(out, resamples=50, block_lengths=(1,))
        row = result.query("product == 'ES' and interval_minutes == 5 and direction == 'All' and unit == 'points' and support == 'all' and metric == 'terminal_delta' and weighting == 'event' and interval_type == 'bonferroni'").iloc[0]
        self.assertEqual((row.fast_accepted, row.slow_accepted), (0, 4))
        self.assertTrue(pd.isna(row.estimate))
        self.assertTrue(pd.isna(row.ci_low))
        self.assertEqual((row.defined_draws, row.undefined_draws), (0, 50))
        self.assertEqual(row.analysis_role, "sensitivity")

    def test_secondary_support_is_conditional_and_has_no_familywise_interval(self):
        out = streams()
        out.loc[out.touch_mode.eq("fast"), "crosses_closure"] = True
        out.loc[out.touch_mode.eq("fast"), "same_session"] = False
        descriptive = branch_contrasts(out)
        row = descriptive.query("direction == 'All' and unit == 'points' and metric == 'terminal_delta' and weighting == 'event' and support == 'uninterrupted'").iloc[0]
        self.assertEqual(row.fast_accepted, 0)
        self.assertEqual(row.support_qualification, "conditional_completed_path_support")
        result = paired_uncertainty(out, resamples=20, block_lengths=(4,))
        self.assertTrue(result.loc[result.interval_type.eq("bonferroni"), "support"].eq("all").all())
        self.assertFalse(result.support.eq("same_session").any())

    def test_reserved_outcomes_and_duplicate_ids_are_rejected(self):
        out = streams()
        out.loc[0, "timestamp"] = pd.Timestamp("2021-01-01", tz="America/New_York")
        with self.assertRaisesRegex(ValueError, "2018"):
            validate_outcomes(out)
        out = streams()
        out.loc[0, "terminal_at"] = pd.Timestamp("2021-01-01 00:01", tz="America/New_York")
        with self.assertRaisesRegex(ValueError, "reserved"):
            validate_outcomes(out)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_outcomes(pd.concat([streams(), streams().iloc[[0]]], ignore_index=True))


if __name__ == "__main__":
    unittest.main()
