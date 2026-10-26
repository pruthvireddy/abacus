import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("study23_metrics", ROOT / "metrics.py")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def trade(ident, value, time="2024-01-03T05:00:00+00:00", status="completed", r=1.):
    return dict(trade_id=str(ident), broker_day="2024-01-03", side="long",
                entry_time=time, exit_time=time, status=status,
                raw_price_points=value/100+.25, raw_price_dollars=value+25,
                net_points=value/100, net_dollars=value, net_r=r,
                source_style_r=r, mfe_points=1., mae_points=2., holding_minutes=15.,
                exit_reason="timed", ambiguous=False)


DAY = dict(broker_day="2024-01-03", eligible=True, valid_range=True,
           no_trade=False, unknown_outcome=False, quantity_skips=0)


class MetricsTests(unittest.TestCase):
    def test_session_boundaries_dst_and_cross_midnight(self):
        cases = [("2024-01-03T01:00:00Z", "Asia"), ("2024-01-03T07:00:00Z", "London"),
                 ("2024-01-03T14:00:00Z", "Outside"), ("2024-01-03T14:30:00Z", "New York"),
                 ("2024-01-03T21:00:00Z", "Outside"), ("2024-07-03T06:00:00Z", "London"),
                 ("2024-07-03T13:30:00Z", "New York")]
        for time, expected in cases:
            with self.subTest(time=time):
                self.assertEqual(m.session_at(time), expected)
        row = m.enrich(trade(1, 1, "2025-01-01T05:15:00Z"))
        self.assertEqual(row["year"], "2025")
        self.assertEqual(row["session"], "Asia")
        self.assertEqual(row["weekday"], "Wednesday")

    def test_counts_invalid_r_and_censoring(self):
        trades = [m.enrich(trade(1, 100, r=1)), m.enrich(trade(2, -50, r=None)),
                  m.enrich(trade(3, 0, r=0)), m.enrich(trade(4, 0, status="censored", r=None))]
        row = m.cohort(trades, [DAY], intervals=False)
        self.assertEqual((row["wins"], row["losses"], row["breakevens"]), (1, 1, 1))
        self.assertEqual(row["completed"], 3)
        self.assertEqual(row["censored"], 1)
        self.assertEqual(row["win_rate"], 1/3)
        self.assertEqual(row["r_denominator"], 2)
        self.assertEqual(row["invalid_r"], 1)
        self.assertEqual(row["expectancy_r"], .5)
        self.assertEqual(row["profit_factor"], 2.)
        self.assertEqual(row["net_dollars"], 50.)

    def test_zero_support_is_null_and_day_counts_do_not_invent_session(self):
        row = m.cohort([], [DAY], session="New York", intervals=False)
        self.assertIsNone(row["net_dollars"])
        self.assertIsNone(row["profit_factor"])
        self.assertIsNone(row["win_rate"])
        self.assertIsNone(row["eligible_days"])
        row = m.cohort([], [dict(DAY, no_trade=True)], intervals=False)
        self.assertEqual(row["no_trade_days"], 1)

    def test_pf_not_subgroup_average_and_drawdown_zero_anchor(self):
        values = [-50, 100, -20, -40, 0, -10]
        rows = [m.enrich(trade(i, v)) for i, v in enumerate(values)]
        result = m.cohort(rows, [DAY], intervals=False)
        self.assertAlmostEqual(result["profit_factor"], 100/120)
        self.assertEqual(result["max_drawdown_dollars"], 70)
        self.assertEqual(result["max_losing_streak"], 2)
        positive = m.cohort([m.enrich(trade(1, 10))], [DAY], intervals=False)
        self.assertIsNone(positive["profit_factor"])

    def test_wilson_and_bootstrap_defined_denominator(self):
        self.assertEqual(m.wilson(0, 0), (None, None))
        lo, hi = m.wilson(0, 10)
        self.assertAlmostEqual(lo, 0)
        self.assertGreater(hi, 0)
        rows = [m.enrich(trade(1, 5)), m.enrich(trade(2, 5))]
        self.assertEqual(m.block_interval(rows, "net_dollars", [DAY], reps=100), (5, 5))


if __name__ == "__main__":
    unittest.main()
