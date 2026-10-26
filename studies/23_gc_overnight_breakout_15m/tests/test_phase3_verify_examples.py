"""Presentation trace selection and deliberately mutated causal/source cells."""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase3_inputs import CloudBar,CloudTimeline
from phase3_verify import OracleDay,OracleMinute,VerificationError,compare
from phase3_verify_examples import selection_reference,case_reference,raw_window_reference,case_qualifies

UTC=timezone.utc
T=datetime(2020,1,2,4,tzinfo=UTC)


def fixture():
    parent=dict(trade_id="p",direction=1,contract="GC:synthetic",status="completed",entry_time=(T+timedelta(minutes=1)).isoformat(),
        entry_time_latest=(T+timedelta(minutes=2)).isoformat(),entry_price=101.1,initial_stop=100.,reset_stop=100.1,
        reset_stop_active_at=(T+timedelta(minutes=15)).isoformat(),exit_time=(T+timedelta(minutes=30)).isoformat(),exit_price=103.9,net_dollars=275.)
    bars=[]
    for i in range(-3,6):
        at=T+timedelta(minutes=5*i)
        bars.append(CloudBar(at,at+timedelta(minutes=5),"GC:synthetic",103.,104.,102.,103.,102.,100.,1.,True,i!=2,250))
    timeline=CloudTimeline(bars,[r.timestamp for r in bars])
    minutes=[OracleMinute(T+timedelta(minutes=i),103.,104.,102.,103.,"GC:synthetic",T+timedelta(minutes=i+1)) for i in range(-15,31) if i!=12]
    day=OracleDay("p","2020-01-02",parent,minutes,timeline,[T],101.,98.,T+timedelta(minutes=30),lambda t:True)
    ep=dict(episode_id="p",policy="A20",mode="diagnostic_1plus1",status="completed",net_dollars=270.)
    add=dict(leg="add",status="completed",entry_time=(T+timedelta(minutes=10)).isoformat(),entry_price=103.1,signal_available_at=(T+timedelta(minutes=10)).isoformat(),net_dollars=-5.)
    signal=dict(event="first_contact_consumed",time=(T+timedelta(minutes=10)).isoformat(),frozen_level=102.,liquidation_net=175.,confirmed=True,parent_open=True)
    record=dict(id="a20-add-loss-long",episode_id="p",policy="A20",mode="diagnostic_1plus1",kind="add_loss",direction=1)
    return day,parent,ep,[add],[signal],record


class TraceMutationTests(unittest.TestCase):
    def test_selection_uses_first_chronological_case_not_largest_gain(self):
        parents={"late":dict(direction=1,entry_time="2020-01-04T04:00:00Z",net_dollars=5.),"early":dict(direction=1,entry_time="2020-01-02T04:00:00Z",net_dollars=5.)}
        episodes=[dict(episode_id=eid,policy=p,mode="diagnostic_1plus1" if p.startswith("A") else "standardized",net_dollars=5.) for eid in parents for p in ("A20","A50","X1","X2")]
        trades=[dict(episode_id=eid,policy="A20",mode="diagnostic_1plus1",leg="add",status="completed",net_dollars=value) for eid,value in (("late",10000.),("early",1.))]
        selected,absent,*_=selection_reference(parents,episodes,trades,[])
        self.assertEqual(selected[0]["episode_id"],"early")
        self.assertEqual(selected[0]["id"],"a20-add-win-long")
        self.assertEqual(len(selected)+len(absent),20)

    def test_censored_added_leg_is_neither_win_nor_loss_case(self):
        day,parent,ep,trades,events,record=fixture()
        trades[0].update(status="censored",net_dollars=None)
        self.assertFalse(case_qualifies("add_win",parent,ep,trades,events))
        self.assertFalse(case_qualifies("add_loss",parent,ep,trades,events))

    def test_exact_causal_signal_action_and_parent_fields(self):
        day,parent,ep,trades,events,record=fixture()
        expected=case_reference(record,day,parent,ep,trades,events)
        self.assertEqual(expected["signal_at"],trades[0]["signal_available_at"])
        self.assertIs(expected["parent_open_at_signal"],True)
        changed=dict(expected,action_price=expected["action_price"]+.1)
        with self.assertRaises(VerificationError):compare(changed,expected)

    def test_action_before_confirmation_is_rejected(self):
        day,parent,ep,trades,events,record=fixture()
        trades[0]["entry_time"]=(T+timedelta(minutes=9)).isoformat()
        with self.assertRaises(VerificationError):case_reference(record,day,parent,ep,trades,events)

    def test_partial_pre_fill_contact_candle_is_rejected(self):
        day,parent,ep,trades,events,record=fixture()
        parent=dict(parent,entry_time_latest=(T+timedelta(minutes=6)).isoformat())
        with self.assertRaises(VerificationError):case_reference(record,replace(day,parent=parent),parent,ep,trades,events)

    def test_warmup_prior_cloud_cannot_supply_frozen_contact_level(self):
        day,parent,ep,trades,events,record=fixture()
        bars=[CloudBar(T+timedelta(minutes=5*i),T+timedelta(minutes=5*(i+1)),"GC:synthetic",103.,104.,102.,103.,102.,100.,1.,True,False,249) for i in range(-3,6)]
        cloud=CloudTimeline(bars,[b.timestamp for b in bars])
        with self.assertRaises(VerificationError):case_reference(record,replace(day,cloud=cloud),parent,ep,trades,events)

    def test_x1_frozen_edge_clock_uses_first_close_and_second_confirms(self):
        day,parent,ep,trades,events,record=fixture()
        record=dict(record,id="x1-loss-saved-long",policy="X1",mode="standardized",kind="loss_saved")
        ep=dict(ep,policy="X1",mode="standardized")
        events=[dict(event="failure_first_close",time=(T+timedelta(minutes=10)).isoformat(),frozen_edge=100.),
            dict(event="ema_exit_signal",time=(T+timedelta(minutes=15)).isoformat(),frozen_edge=100.,original_open_at_signal=True,original_liquidation_net=-25.)]
        trade=dict(leg="original",status="completed",exit_time=(T+timedelta(minutes=15)).isoformat(),exit_price=99.9)
        expected=case_reference(record,day,parent,ep,[trade],events)
        self.assertEqual(expected["frozen_level_contact_open"],(T+timedelta(minutes=5)).isoformat())
        self.assertEqual(expected["contact_open"],(T+timedelta(minutes=10)).isoformat())

    def test_expected_missing_minutes_and_unavailable_features_survive_trace(self):
        day,parent,ep,trades,events,record=fixture()
        case=case_reference(record,day,parent,ep,trades,events)
        minutes,cloud=raw_window_reference(case,day)
        missing=next(r for r in minutes if r["timestamp"]==(T+timedelta(minutes=12)).isoformat())
        self.assertIs(missing["usable"],False)
        self.assertTrue(all(missing[k] is None for k in ("open","high","low","close")))
        feature=next(r for r in cloud if r["timestamp"]==(T+timedelta(minutes=10)).isoformat())
        self.assertTrue(feature["usable"])
        self.assertFalse(feature["feature_valid"])
        self.assertEqual(feature["ema20"],102.)


if __name__=="__main__":unittest.main()
