"""Hand-calculated cases for the separately written verification oracle."""
import importlib.util
from pathlib import Path
import unittest

import pandas as pd

SPEC=importlib.util.spec_from_file_location("study23_independent_verifier",
    Path(__file__).resolve().parents[1]/"verify_execution.py")
v=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)


def fixture():
    times=pd.date_range("2024-01-03T04:00Z","2024-01-03T17:00Z",freq="min")
    frame=pd.DataFrame(dict(timestamp=times,open=95.,high=97.,low=94.,close=95.,contract="GC:1:2024:2:GCG4"))
    coverage=dict(eligible=True,broker_date="2024-01-03",decision_available_at="2024-01-03T04:00Z",
        trading_end_utc="2024-01-03T17:00Z",range_high=100.,range_low=90.,range_contract="GC:1:2024:2:GCG4")
    config=dict(slippage_ticks=1,commission_per_side=2.5,ordering="source_ohlc",timed_exit_priority="market_first")
    return frame,coverage,set(times.astype("int64")),config


class IndependentOracleTests(unittest.TestCase):
    def test_long_touch_survives_and_costs_are_hand_reconciled(self):
        frame,coverage,expected,config=fixture()
        frame.loc[1:, ["open","high","low","close"]]=100.5
        frame.loc[0,["open","high","low","close"]]=[99.5,100.,99.2,99.9]
        trade,status=v.oracle_day(frame,coverage,expected,config)
        self.assertEqual(status,"completed")
        self.assertEqual(trade["side"],"long")
        self.assertEqual(trade["entry_price_raw"],100.)
        self.assertAlmostEqual(trade["entry_price"],100.1)
        self.assertEqual(trade["reset_stop_active_at"],"2024-01-03T04:15:00Z")
        self.assertEqual(trade["reset_stop"],99.1)
        self.assertAlmostEqual(trade["raw_price_dollars"],50.)
        self.assertAlmostEqual(trade["net_dollars"],25.)
        self.assertAlmostEqual(trade["net_r"],25/110)

    def test_same_minute_stop_cannot_be_rescued_by_reset(self):
        frame,coverage,expected,config=fixture()
        frame.loc[0,["open","high","low","close"]]=[110.,115.,98.,112.]
        trade,status=v.oracle_day(frame,coverage,expected,config)
        self.assertEqual(status,"completed")
        self.assertEqual(trade["exit_price_raw"],99.)
        self.assertIsNone(trade["reset_stop"])
        self.assertEqual(trade["holding_minutes"],0.)
        self.assertAlmostEqual(trade["net_dollars"],-1125.)

    def test_missing_last_entry_minute_censors_before_reset(self):
        frame,coverage,expected,config=fixture()
        frame.loc[:,["open","high","low","close"]]=100.5
        frame=frame.drop(index=14)
        trade,status=v.oracle_day(frame,coverage,expected,config)
        self.assertEqual(status,"censored")
        self.assertIsNone(trade["reset_stop"])
        self.assertEqual(trade["last_observed_at"],"2024-01-03T04:14:00Z")

    def test_known_close_then_missing_next_minute_retains_valid_reset(self):
        frame,coverage,expected,config=fixture()
        frame.loc[:,["open","high","low","close"]]=100.5
        frame=frame.drop(index=15)
        trade,status=v.oracle_day(frame,coverage,expected,config)
        self.assertEqual(status,"censored")
        self.assertEqual(trade["reset_stop_active_at"],"2024-01-03T04:15:00Z")
        self.assertEqual(trade["reset_stop"],99.6)

    def test_missing_last_unfilled_window_minute_is_unknown(self):
        frame,coverage,expected,config=fixture()
        frame=frame.drop(index=779)
        trade,status=v.oracle_day(frame,coverage,expected,config)
        self.assertIsNone(trade)
        self.assertEqual(status,"unknown")

    def test_short_boundary_symmetry(self):
        frame,coverage,expected,config=fixture()
        frame.loc[1:, ["open","high","low","close"]]=89.5
        frame.loc[0,["open","high","low","close"]]=[90.5,90.8,90.,90.1]
        trade,status=v.oracle_day(frame,coverage,expected,config)
        self.assertEqual(trade["side"],"short")
        self.assertAlmostEqual(trade["net_dollars"],25.)
        self.assertEqual(trade["initial_stop"],90.9)
        self.assertEqual(trade["reset_stop"],90.8)

    def test_ratios_and_drawdown_use_saved_numerators(self):
        trades=[]
        for i,pnl in enumerate([-50,100,-20,-40,0,-10]):
            trades.append(dict(status="completed",trade_id=str(i),exit_time=str(i),net_dollars=pnl,
                net_points=pnl/100,raw_price_points=(pnl+25)/100,raw_price_dollars=pnl+25,
                net_r=pnl/100,source_style_r=pnl/100,mfe_points=1,mae_points=2,
                holding_minutes=15,exit_reason="time",broker_day="2024-01-03"))
        result=v.independent_stats(trades)
        self.assertAlmostEqual(result["profit_factor"],100/120)
        self.assertEqual(result["max_drawdown_dollars"],70)
        self.assertEqual(result["max_losing_streak"],2)


if __name__=="__main__":unittest.main()
