import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.events import breakout,touch,Arm,retest,Lockout,selected_hvn_touches,confirmed_hvn,entry_status


class SignalPrimitiveTests(unittest.TestCase):
    def test_price_crossing_not_boundary_migration(self):
        self.assertTrue(breakout(100,100.25,100,1))
        self.assertTrue(breakout(100,99.75,100,-1))
        # Old VAH=104 moved to 100 while price stayed at 102.
        self.assertFalse(breakout(102,102,100,1))
        self.assertFalse(breakout(98,98,100,-1))

    def test_touch_approach_mirror_and_gap_across_without_touch(self):
        self.assertTrue(touch(102,101,99,100,1))
        self.assertTrue(touch(98,101,99,100,-1))
        self.assertFalse(touch(102,99,98,100,1))
        self.assertFalse(touch(98,102,101,100,-1))
        self.assertFalse(touch(99,101,99,100,1))

    def test_no_same_bar_expiry_opposite_and_midnight(self):
        arm=Arm(1,80,'s',100,96)
        self.assertEqual(arm.availability(80,'s'),'same_bar_not_allowed')
        self.assertEqual(arm.availability(140,'s'),'armed')
        self.assertEqual(arm.availability(141,'s'),'expired')
        self.assertEqual(arm.availability(90,'s',True),'opposite_cancelled')
        self.assertEqual(arm.availability(360,'s'),'session_cancelled')
        self.assertEqual(arm.availability(90,'new'),'session_cancelled')

    def test_retest_confirmation_mirror_cancellation(self):
        self.assertEqual(retest(102,102,100,101,100,1),'confirmed')
        self.assertEqual(retest(98,100,98,99,100,-1),'confirmed')
        self.assertEqual(retest(102,102,99,99.5,100,1),'failed_retest_cancelled')
        self.assertEqual(retest(102,102,99,99.75,100,1),'unconfirmed')

    def test_lockout_is_per_setup_side_and_suppression_does_not_restart(self):
        lock=Lockout(15)
        self.assertTrue(lock.accept('B',1,120,'s'))
        self.assertFalse(lock.accept('B',1,134,'s'))
        self.assertTrue(lock.accept('B',1,135,'s'))
        self.assertTrue(lock.accept('B',-1,135,'s'))
        self.assertTrue(lock.accept('C',1,135,'s'))
        self.assertTrue(lock.accept('B',1,120,'next'))

    def test_node_saved_before_touch_multi_node_ambiguity(self):
        nodes=[dict(node_id='x',candidate_id='c1',lo=104,hi=106,mid=105,side=1,rank=1),
               dict(node_id='y',candidate_id='c2',lo=110,hi=112,mid=111,side=1,rank=2)]
        touches=selected_hvn_touches(100,111,100,nodes)
        self.assertEqual(len(touches),2)
        self.assertEqual(touches[0]['node_id'],'x')
        self.assertEqual(touches[0]['direction'],-1)
        self.assertTrue(confirmed_hvn(nodes[0],103))
        self.assertFalse(confirmed_hvn(nodes[0],105))
        # Selection after price enters x may be empty; saved record remains x.
        self.assertEqual(selected_hvn_touches(100,105,100,nodes)[0]['candidate_id'],'c1')
        lower=dict(node_id='s',candidate_id='c3',lo=94,hi=96,mid=95,side=-1,rank=1)
        self.assertEqual(selected_hvn_touches(100,100,95,[lower])[0]['direction'],1)
        self.assertTrue(confirmed_hvn(lower,97))

    def test_next_contiguous_open_and_midnight(self):
        m=60_000_000_000
        self.assertEqual(entry_status(0,m,120),'next_open_eligible')
        self.assertEqual(entry_status(0,2*m,121),'missing_next_minute')
        self.assertEqual(entry_status(0,None,120),'missing_next_minute')
        self.assertEqual(entry_status(0,m,360),'outside_entry_window')
        self.assertEqual(entry_status(0,m,119),'outside_entry_window')


if __name__=='__main__':unittest.main()
