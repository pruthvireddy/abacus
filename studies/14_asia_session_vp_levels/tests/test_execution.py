import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.execution import session_signals, session_outcomes

M=60_000_000_000


def bar(minute,open_,high,low,close,previous,**changes):
    r=dict(ts_event=minute*M,session_date='2024-01-02',week='2024-01-01',season='EST',
           minute=minute,raw_symbol='NQH4',roll_id=1,open=open_,high=high,low=low,close=close,
           previous_close=previous,on_vah=100.,on_poc=96.,on_val=92.,volatility60=2.,
           overnight_complete=True,overnight_contract_clean=True,source_degraded=False,
           hvn_complete=True,hvn_contract_clean=True,reference_complete=True,
           reference_contract_clean=True,hvn_source_degraded=False,reference_source_degraded=False,
           selected=[],post_selected=[])
    r.update(changes)
    return r


class ExecutionTests(unittest.TestCase):
    def test_confirmed_upper_poc_buy_is_next_open(self):
        records=[bar(120,100,100.5,99.75,100.25,100),
                 bar(121,100.25,100.5,95.75,96.25,100.25),
                 bar(122,96.5,99,95.5,98,96.25),
                 bar(123,98,100,97,99,98)]
        ledger,signals=session_signals(records)
        a=[x for x in signals if x['setup']=='A' and x['variant']=='primary']
        self.assertEqual(len(a),1)
        self.assertEqual(a[0]['direction'],1)
        self.assertEqual(a[0]['status'],'accepted')
        self.assertEqual(a[0]['entry'],96.5)
        outcome=next(x for x in session_outcomes(records,a,horizons=(2,)) if x['horizon']==2)
        self.assertEqual(outcome['path_status'],'complete')
        self.assertEqual(outcome['mfe_points'],3.5)
        self.assertEqual(outcome['mae_points'],1.)
        self.assertTrue(any(x['setup']=='B' and x['status']=='failed_retest_cancelled' for x in ledger))

    def test_confirmed_lower_poc_sell_and_hvn_saved_before_touch(self):
        node=dict(node_id='n',candidate_id='c',lo=95.5,hi=96.5,mid=96.,strength=10.,
                  side=-1,rank=1,available_at=0,match_ambiguous=False)
        records=[bar(120,92,92,91.5,91.75,92),
                 bar(121,91.75,96.25,91.5,95.75,91.75,selected=[node]),
                 bar(122,95.5,96,92,93,95.75)]
        _,signals=session_signals(records)
        a=[x for x in signals if x['setup']=='A' and x['variant']=='primary']
        self.assertEqual(len(a),1)
        self.assertEqual(a[0]['direction'],-1)
        self.assertEqual(a[0]['entry'],95.5)
        c=[x for x in signals if x['setup']=='C' and x['variant']=='primary']
        self.assertEqual(len(c),0)  # lower node was approached from below

    def test_unconfirmed_retest_keeps_arm_for_later_confirmation(self):
        records=[bar(120,100,100.5,99.75,100.25,100),
                 bar(121,100.25,100.5,99.75,99.75,100.25),
                 bar(122,100.5,101,99.75,100.25,100.5),
                 bar(123,100.25,101,100,100.5,100.25)]
        _,signals=session_signals(records)
        b=[x for x in signals if x['setup']=='B' and x['variant']=='primary']
        self.assertEqual(len(b),1)
        self.assertEqual(b[-1]['status'],'accepted')
        self.assertEqual(sum(x['variant']=='touch_only' for x in signals if x['setup']=='B'),2)

    def test_missing_next_minute_rejected_and_not_entered(self):
        records=[bar(120,100,100.5,99.75,100.25,100),
                 bar(121,100.25,100.5,95.75,96.25,100.25),
                 bar(123,96.5,99,95.5,98,96.25)]
        _,signals=session_signals(records)
        a=[x for x in signals if x['setup']=='A' and x['variant']=='primary'][0]
        self.assertEqual(a['status'],'missing_next_minute')
        self.assertEqual(session_outcomes(records,[a],horizons=(2,)),[])

    def test_frozen_breakout_poc_is_separate_from_developing_poc(self):
        records=[bar(120,100,100.5,99.75,100.25,100),
                 bar(121,97,97,95.75,96.5,100.25,on_poc=98),
                 bar(122,96.5,98,96,97,96.5,on_poc=98)]
        _,developing=session_signals(records)
        _,frozen=session_signals(records,level_mode='frozen_breakout')
        self.assertFalse(any(x['setup']=='A' and x['variant']=='primary' for x in developing))
        primary=[x for x in frozen if x['setup']=='A' and x['variant']=='primary']
        self.assertEqual(len(primary),1)
        self.assertEqual(primary[0]['level'],96)

if __name__=='__main__':unittest.main()
