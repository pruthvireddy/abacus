import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.outcomes import score_outcomes
from src.statistics import summarize, quantiles, calendar_weights, bootstrap, stability, comparisons
from test_outcomes import observation


def population():
    bars, event = observation()
    one = score_outcomes(bars, event, [3], 5).iloc[0].to_dict()
    rows = []
    for i, (mfe, mae, delta) in enumerate(zip([0., 2., 4., 10.], [2.] * 4, [0., 1., -1., 4.])):
        row = one | dict(event_id=str(i), mfe=mfe, mae=mae, terminal_delta=delta,
            mfe_atr=mfe / 2, mae_atr=mae / 2, terminal_delta_atr=delta / 2,
            favorable=delta > 0, neutral=delta == 0, adverse=delta < 0,
            mfe_gt_mae=mfe > mae, mfe_mae_tie=mfe == mae,
            session="2019-01-02" if i < 3 else "2019-01-03", week="2018-12-31", horizon=15, horizon_minutes=75)
        rows.append(row)
    return pd.DataFrame(rows)


class StatisticsTest(unittest.TestCase):
    def test_mean_quantiles_deciles_shares_and_session_balance(self):
        out = population()
        row = summarize(out).query("direction == 'All' and unit == 'points'").iloc[0]
        self.assertEqual(row.accepted, 4)
        self.assertEqual(row.completed, 4)
        self.assertEqual(row.mean_mfe, 4.)
        self.assertEqual(row.session_mean_mfe, 6.)
        self.assertEqual(row.favorable_share, .5)
        self.assertEqual(row.neutral_share, .25)
        self.assertEqual(row.adverse_share, .25)
        q = quantiles(out).query("direction == 'All' and unit == 'points' and metric == 'mfe'")
        self.assertAlmostEqual(q.loc[q["quantile"].eq(.1), "value"].iloc[0], .6)
        self.assertAlmostEqual(q.loc[q["quantile"].eq(.95), "value"].iloc[0], 9.1)
        self.assertTrue(set(i / 10 for i in range(11)).issubset(set(q["quantile"])))
        self.assertTrue(q.row_id.is_unique)

    def test_censored_null_normalization_and_missing_bounds(self):
        out = population()
        censored = out.iloc[[0]].copy()
        censored.status = "censored"
        for column in ("mfe", "mae", "terminal_delta", "mfe_atr", "mae_atr", "terminal_delta_atr"):
            censored[column] = np.nan
        censored.favorable = None
        out = pd.concat([out, censored], ignore_index=True)
        out.loc[0, ["mfe_atr", "mae_atr", "terminal_delta_atr"]] = np.nan
        scores = summarize(out)
        row = scores.query("direction == 'All' and unit == 'points'").iloc[0]
        self.assertEqual((row.accepted, row.completed, row.censored), (5, 4, 1))
        self.assertEqual(row.missing_worst_favorable_share, .4)
        self.assertEqual(row.missing_best_favorable_share, .6)
        atr = scores.query("direction == 'All' and unit == 'atr'").iloc[0]
        self.assertEqual(atr.normalization_missing, 1)
        self.assertEqual(atr.evaluable, 3)
        empty_side = scores.query("direction == 'Sell' and unit == 'points'").iloc[0]
        self.assertEqual(empty_side.completed, 0)
        self.assertTrue(pd.isna(empty_side.mean_mfe))
        self.assertTrue(empty_side.sparse_warning)

    def test_calendar_weights_include_empty_weeks_and_deterministic_circular_blocks(self):
        weeks, a = calendar_weights(50, 123, 4)
        _, b = calendar_weights(50, 123, 4)
        self.assertEqual(weeks[0], "2018-01-01")
        self.assertEqual(weeks[-1], "2020-12-28")
        self.assertEqual(len(weeks), 157)
        expected, current = [], date(2018, 1, 1)
        while current < date(2021, 1, 1):
            expected.append(current.isoformat())
            current += timedelta(days=7)
        self.assertEqual(weeks, expected)
        self.assertNotIn("2017-12-25", weeks)
        self.assertNotIn("2021-01-04", weeks)
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(a.sum(axis=1), len(weeks))
        self.assertGreater(len(weeks), 150)

    def test_weekly_stability_uses_only_the_full_development_week_roster(self):
        table = stability(population())
        weekly = table.query("direction == 'All' and unit == 'points' and period_kind == 'week'")
        self.assertEqual(len(weekly), 157)
        self.assertEqual(weekly.period.iloc[0], "2018-01-01")
        self.assertEqual(weekly.period.iloc[-1], "2020-12-28")
        self.assertEqual(weekly.accepted.sum(), 4)
        self.assertEqual(weekly.completed.sum(), 4)
        self.assertTrue(weekly.period.ge("2018-01-01").all())
        self.assertTrue(weekly.period.le("2020-12-28").all())
        self.assertTrue(weekly.loc[weekly.accepted.eq(0), "mean_terminal_delta"].isna().all())

    def test_session_bootstrap_does_not_split_sunday_monday_session(self):
        out = population().iloc[:3].copy()
        out["mfe"] = [0., 10., 20.]
        out["session"] = ["2019-01-07", "2019-01-07", "2019-01-08"]
        out["week"] = ["2018-12-31", "2019-01-07", "2019-01-07"]
        expected = summarize(out).query("direction == 'All' and unit == 'points'").session_mean_mfe.iloc[0]
        result = bootstrap(out, resamples=100, block_lengths=(4,))
        row = result.query("direction == 'All' and unit == 'points' and metric == 'mfe' and weighting == 'session'").iloc[0]
        self.assertEqual(row.estimate, 12.5)
        self.assertEqual(row.estimate, expected)
        self.assertEqual(row.defined_draws + row.undefined_draws, 100)

    def test_paired_identical_branch_contrast_has_exact_zero_uncertainty(self):
        five = population()
        three = five.copy()
        three.interval_minutes = 3
        three.horizon_minutes = 45
        out = pd.concat([five, three], ignore_index=True)
        result = bootstrap(out, resamples=100, block_lengths=(1, 4, 8))
        contrasts = result.query("kind == 'contrast' and direction == 'All' and unit == 'points'")
        self.assertTrue(contrasts.estimate.eq(0).all())
        self.assertTrue(contrasts.ci_low.eq(0).all())
        self.assertTrue(contrasts.ci_high.eq(0).all())
        descriptive = comparisons(out)
        self.assertTrue(descriptive.loc[descriptive.direction.eq("All"), "difference_mean_mfe"].eq(0).all())

    def test_empty_calendar_periods_have_zero_count_and_null_outcomes(self):
        table = stability(population(), session_roster=["2019-01-02", "2019-01-03", "2019-01-04"])
        row = table.query("direction == 'All' and unit == 'points' and period_kind == 'session' and period == '2019-01-04'").iloc[0]
        self.assertEqual(row.accepted, 0)
        self.assertTrue(pd.isna(row.mean_mfe))


if __name__ == "__main__":
    unittest.main()
