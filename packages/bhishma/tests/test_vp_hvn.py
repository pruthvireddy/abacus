import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
import numpy as np
from abacus_bhishma import vp_hvn as vp
from abacus_bhishma.vp_hvn_release import session_start, week_key, expected_session_minutes


class ProfileTests(unittest.TestCase):
    def setUp(self):
        # Every scalar fixture starts scalar; cleanup also runs after failures.
        native = patch.object(vp, '_native', None)
        native.start()
        self.addCleanup(native.stop)

    def test_mass_and_lower_poc_upper_va_tie(self):
        p=vp.Profile(row=1,va=.7)
        p.add(2,0,30)
        self.assertEqual(p.total,30)
        np.testing.assert_array_equal(p.bins,[10,10,10])
        self.assertEqual(p.calculate(),(2,0,0))
        p.bins=np.array([3.,10.,3.]);p.total=16
        self.assertEqual(p.calculate(),(2,1,1))

    def test_grid_edges_and_null_volume(self):
        p=vp.Profile()
        p.add(104,100,10)
        np.testing.assert_array_equal(p.bins,[5,5])
        self.assertEqual(p.calculate(),(104,100,100))
        p.add(104,100,None);self.assertEqual(p.total,10)
        levels=p.levels;p.reset();self.assertEqual(p.calculate(),levels)

    def test_batch_preserves_sequential_arithmetic(self):
        rng=np.random.default_rng(14);low=rng.integers(400,450,100)/4
        high=low+rng.integers(0,40,100)/4;vol=rng.integers(0,1000,100)
        a,b=vp.Profile(),vp.Profile()
        for h,l,v in zip(high,low,vol):a.add(h,l,v)
        b.add_batch(high,low,vol)
        np.testing.assert_array_equal(a.bins,b.bins)
        self.assertAlmostEqual(a.bins.sum(),float(vol.sum()))

    def test_filtering_precedes_strength_suppression(self):
        strong=vp.Node(100,101,100.5,100,0,50)
        weak=vp.Node(103,104,103.5,90,1,50)
        # Strong node collides with reference; weaker neighbor returns.
        chosen,reasons=vp.select([strong,weak],90,[99],gap=2)
        self.assertEqual(chosen,[(1,1,1)])
        self.assertEqual(reasons[0],'reference_collision')
        self.assertEqual(vp.select([strong,weak],90,[],gap=2)[0],[(0,1,1)])

    def test_quotas_nearest_gap_equality_and_disappearance(self):
        ns=[vp.Node(x,x+1,x+.5,10,0,5) for x in (90,95,105,110,115)]
        selected,_=vp.select(ns,100,[])
        self.assertEqual(len(selected),4)
        self.assertEqual([x for x in selected if x[1]==1],[(2,1,1),(3,1,2)])
        _,why=vp.select(ns,105.5,[]);self.assertEqual(why[2],'contains_price')
        self.assertTrue(vp.collides(vp.Node(1,2,1.5,1,0,0),vp.Node(4,5,4.5,1,0,0),2))

    def test_split_cannot_manufacture_fresh_node(self):
        old=[vp.Node(10,12,11,1,0,1,node_id='old')]
        new=[vp.Node(10,11,10.5,1,0,1),vp.Node(11,12,11.5,1,0,1)]
        vp.match_nodes(new,old,'r')
        self.assertEqual({n.node_id for n in new},{'old'})
        self.assertTrue(all(n.match_ambiguous for n in new))

    def test_literal_percentage_operation_order(self):
        # The second peak has 3/5=.6 volume. Pine 3*20/100 is .6;
        # replacing it with 3*.2 gives .6000000000000001 and drops this peak.
        nodes,_=vp.composite(np.array([18.,2.,14.]),np.array([0.,2.,10.]),
                             np.array([0.,3.,3.]),smooth=1)
        self.assertEqual([n.peak_row for n in nodes],[2,10])

    def test_native_matches_literal_reference(self):
        rng=np.random.default_rng(1414)
        with tempfile.TemporaryDirectory() as folder:
            for wide in (False,True):
                low=rng.integers(0,160000 if wide else 100,80)/4
                high=low+rng.integers(0,25,80)/4
                volume=rng.integers(0,1000,80).astype(float)
                vp._native=None
                reference,meta=vp.composite(high,low,volume)
                vp.enable_native(Path(folder))
                fast,other=vp.composite(high,low,volume)
                self.assertEqual(len(reference),len(fast))
                np.testing.assert_array_equal([[n.lo,n.hi,n.mid,n.strength,n.peak_row,n.prominence] for n in reference],
                                              [[n.lo,n.hi,n.mid,n.strength,n.peak_row,n.prominence] for n in fast])
                self.assertAlmostEqual(other['mass'],volume.sum(),places=7)
                self.assertLessEqual(other['rows'],3000)
                self.assertTrue(all(n.hi-n.lo<=2 for n in fast))
                if wide:self.assertGreater(other['step'],2)
                self.assertEqual(meta['step'],other['step'])

    def test_dst_sunday_week_year_and_pause(self):
        winter=session_start(date(2024,1,8));summer=session_start(date(2024,7,8))
        self.assertEqual(winter.hour,18);self.assertEqual(winter.utcoffset().total_seconds(),-18000)
        self.assertEqual(summer.utcoffset().total_seconds(),-14400)
        self.assertEqual(week_key(date(2024,1,1)),date(2024,1,1))
        self.assertEqual(session_start(date(2024,1,1)).date(),date(2023,12,31))
        self.assertEqual(len(expected_session_minutes(date(2020,1,2))),1365)
        self.assertEqual(len(expected_session_minutes(date(2024,1,2))),1380)


if __name__=='__main__':unittest.main()
