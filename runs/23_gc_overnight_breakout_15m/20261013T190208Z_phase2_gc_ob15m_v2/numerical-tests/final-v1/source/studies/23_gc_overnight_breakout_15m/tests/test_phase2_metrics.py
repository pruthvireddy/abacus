import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase2_metrics import known_pnl, paired_intervals, paired_rows, financial_recovery, budget_quantity, frequency_rows


class Phase2SummaryTests(unittest.TestCase):
    def test_null_trade_is_not_known_no_fill(self):
        self.assertIsNone(known_pnl({"status":"unknown"}))
        self.assertIsNone(known_pnl({"status":"censored"}))
        self.assertEqual(known_pnl({"status":"no_fill"}),0)

    def test_common_mask_keeps_zero_and_removes_unknown_across_family(self):
        base={str(i):dict(status="completed",net_dollars=v,entry_time=f"2020-01-0{i+1}T05:00:00Z",direction=1,broker_day=f"2020-01-0{i+1}") for i,v in enumerate([100,-100,20])}
        a=[dict(episode_id=str(i),status="no_fill",trade=None) for i in range(3)]
        b=[dict(episode_id=str(i),status="unknown" if i==2 else "no_fill",trade=None) for i in range(3)]
        rows=paired_rows({"a":a,"b":b},base,[x["broker_day"] for x in base.values()],["a","b"],"primary",intervals=False)
        selected=[x for x in rows if x["year"]=="all" and x["session"]=="all" and x["side"]=="combined"]
        self.assertTrue(all(r["complete_pairs"]==2 and r["mean_difference"]==0 for r in selected))
        self.assertEqual(selected[0]["individual_pairs"],3)
        self.assertEqual(selected[0]["individual_mean_difference"],-20/3)

    def test_zero_support_ratios_and_intervals_remain_unavailable(self):
        self.assertEqual(paired_intervals([],[]),[])
        rows=frequency_rows([],[])
        self.assertEqual(rows,[])

    def test_aligned_identical_vectors_have_identical_intervals(self):
        values=[("2020-01-01",[10.,10.]),("2020-01-31",[-3.,-3.])]
        ci=paired_intervals(values,["2020-01-01","2020-02-28"],reps=10000)
        self.assertEqual(ci[0],ci[1])
        self.assertLessEqual(ci[0][0],3.5)
        self.assertGreaterEqual(ci[0][1],3.5)

    def test_realized_loss_and_actual_later_fill_are_required(self):
        self.assertIsNone(financial_recovery(-100,150,loss_known=False,actually_executed=True))
        self.assertIsNone(financial_recovery(-100,150,loss_known=True,actually_executed=False))
        for later,category in ((150,"full_recovery"),(50,"partial_recovery"),(0,"no_improvement"),(-10,"further_loss")):
            self.assertEqual(financial_recovery(-100,later,loss_known=True,actually_executed=True)["category"],category)

    def test_source_capital_and_shared_notional_do_not_allow_fractional_gc(self):
        self.assertEqual(budget_quantity(10000,1500,1485,fraction=.5),0)
        self.assertEqual(budget_quantity(1000000,1500,1485,fraction=.5,active_notional=10000000),0)

    def test_known_breach_survives_unknown_recovery(self):
        observations=[dict(year="2020",session="Asia",side="upper-first",horizon="remaining_broker_window",event="one_tick_breach",occurred=v,scheduled_exposure_minutes=300) for v in (True,False,None)]
        r=next(x for x in frequency_rows(observations,["one_tick_breach"]) if x["year"]=="all" and x["session"]=="all" and x["side"]=="combined")
        self.assertEqual((r["known_events"],r["known_none"],r["unknown"]),(1,1,1))
        self.assertEqual(r["rate"],.5)
        self.assertEqual((r["lower_bound"],r["upper_bound"]),(1/3,2/3))

if __name__=="__main__":unittest.main()
