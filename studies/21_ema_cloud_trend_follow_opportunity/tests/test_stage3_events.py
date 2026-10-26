import sys
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.stage2_engine import generate_streams
from src.stage3_events import gate_spec,generate_gateway_stream,iter_gateway_streams


def bars(n=6,interval=5):
    times=pd.date_range('2019-01-02T14:00Z',periods=n,freq=f'{interval}min')
    return pd.DataFrame(dict(timestamp=times,available_at=times+pd.Timedelta(minutes=interval),
        product='ES',contract='A',open=105.,high=106.,low=104.,close=105.,volume=10.,
        usable=True,quality_reason='',session='2019-01-02',ema20=103.,ema50=100.,atr14=2.,
        feature_valid=True,feature_reset=False,consecutive_count=250,known_closure_before=False,
        feature_source_timestamp=times,feature_available_at=times+pd.Timedelta(minutes=interval),
        feature_contract='A',interval_minutes=interval))


class GatewayAcceptanceTests(unittest.TestCase):
    def test_fixed_absolute_exact_every_inherited_field_against_stage2(self):
        source=bars(8)
        source.loc[[1,2,4,7],['low','high']]=[99.,105.]
        source.loc[4,'ema20']=102.
        source.loc[5,'feature_valid']=False
        old_technical,old_events=generate_streams(source,5)
        for mode in ('fast','slow'):
            result=generate_gateway_stream(source,5,mode,gate_spec('absolute',2.4))
            old=old_technical.loc[old_technical.touch_mode.eq(mode)].reset_index(drop=True)
            pd.testing.assert_frame_equal(old,result['technical'][old.columns],check_exact=True)
            old=old_events.loc[old_events.touch_mode.eq(mode)].reset_index(drop=True)
            current=result['events'][old.columns].copy()
            for column in ('stage','gate_id','split'):current[column]=old[column]
            pd.testing.assert_frame_equal(old,current,check_exact=True)

    def test_zero_gateway_accepts_fixed_reject_without_filtering_accepted_baseline(self):
        source=bars(3)
        source.loc[1,['ema20','low','high']]=[102.,101.,105.]
        source.loc[2,['low','high']]=[99.,105.]
        low=generate_gateway_stream(source,5,'fast',gate_spec('absolute',0))
        fixed=generate_gateway_stream(source,5,'fast',gate_spec('absolute',2.4))
        self.assertEqual(low['events'].signal_idx.tolist(),[1])
        self.assertTrue(fixed['events'].empty)
        self.assertFalse(fixed['technical'].armed_after.iloc[1])

    def test_dimensionless_epsilon_boundary(self):
        # Price deficit / ATR4 gives ratio deficits0.9e-10 and1.1e-10.
        for deficit,accepted in ((3.6e-10,True),(4.4e-10,False)):
            source=bars(2)
            source.ema20=102.-deficit
            source.atr14=4.
            source.loc[1,['low','high']]=[99.,105.]
            result=generate_gateway_stream(source,5,'slow',gate_spec('atr',.5))
            self.assertEqual(bool(result['technical'].accepted.iloc[1]),accepted)
            self.assertEqual(result['technical'].min_width.iloc[1],2.)
        source=bars(2);source.atr14=.25;source.loc[1,['low','high']]=[99.,105.]
        self.assertTrue(generate_gateway_stream(source,5,'slow',gate_spec('atr',1.5))['technical'].accepted.iloc[1])

    def test_atr_invalid_rejected_penetration_consumes_and_absolute_support_retained(self):
        for invalid in (np.nan,0.,-1.,np.inf):
            source=bars(3)
            source.loc[1:2,['low','high']]=[99.,105.]
            source.loc[1,'atr14']=invalid
            ratio=generate_gateway_stream(source,5,'slow',gate_spec('atr',.5))
            absolute=generate_gateway_stream(source,5,'slow',gate_spec('absolute',2.4))
            self.assertTrue(ratio['events'].empty)
            self.assertEqual(ratio['technical'].suppression_reason.iloc[1],'atr_invalid')
            self.assertFalse(ratio['technical'].armed_after.iloc[1])
            self.assertEqual(absolute['events'].signal_idx.tolist(),[1])
            self.assertTrue(pd.isna(absolute['events'].entry_atr.iloc[0]))

    def test_independent_fast_slow_states_and_prefix_causality(self):
        source=bars(5,3)
        source.feature_reset=True;source.feature_source_timestamp=source.timestamp.iloc[0]
        source.loc[1,['low','high']]=[102.,105.]
        source.loc[2,['low','high']]=[99.,105.]
        for mode,index in (('fast',1),('slow',2)):
            result=generate_gateway_stream(source,3,mode,gate_spec('atr',1.))
            prefix=generate_gateway_stream(source.iloc[:4],3,mode,gate_spec('atr',1.))
            self.assertEqual(result['events'].signal_idx.tolist(),[index])
            pd.testing.assert_frame_equal(result['technical'].iloc[:4].reset_index(drop=True),prefix['technical'],check_exact=True)
            pd.testing.assert_frame_equal(result['events'],prefix['events'],check_exact=True)

    def test_year_boundary_known_closure_does_not_reset_acceptance(self):
        source=bars(2)
        source.loc[0,'timestamp']=pd.Timestamp('2018-12-31T21:55Z')
        source.loc[1,'timestamp']=pd.Timestamp('2019-01-02T14:00Z')
        source['available_at']=source.timestamp+pd.Timedelta(minutes=5)
        source.loc[1,'known_closure_before']=True
        source.loc[1,['low','high']]=[99.,105.]
        result=generate_gateway_stream(source,5,'slow',gate_spec('atr',1.))
        self.assertEqual(result['events'].signal_idx.tolist(),[1])
        self.assertEqual(result['technical'].reset_reason.iloc[1],'')

    def test_equality_roll_direction_and_invalid_feature_reset_both_gateway_families(self):
        for change in ('equality','roll','direction','invalid'):
            source=bars(2);source.loc[1,['low','high']]=[96.,106.]
            if change=='equality':source.loc[1,'ema20']=100.
            if change=='roll':source.loc[1,'contract']='B'
            if change=='direction':source.loc[1,'ema20']=97.
            if change=='invalid':source.loc[1,'feature_valid']=False
            for result in iter_gateway_streams(source,5,[gate_spec('absolute',0),gate_spec('atr',.1)]):
                self.assertTrue(result['events'].empty,change)

    def test_iterator_only_explicit_gates_and_canonical_ids(self):
        self.assertEqual(gate_spec('absolute',2.)['gate_id'],'abs_2')
        self.assertEqual(gate_spec('atr',.1)['gate_id'],'atr_0p1')
        result=list(iter_gateway_streams(bars(),5,[gate_spec('atr',.1)],touch_modes=('slow',)))
        self.assertEqual([(p['gate']['gate_id'],p['touch_mode']) for p in result],[('atr_0p1','slow')])
        for family,value in (('atr',0),('absolute',np.nan),('absolute',-1)):
            with self.assertRaises(ValueError):gate_spec(family,value)
        with self.assertRaises(ValueError):generate_gateway_stream(bars(),5,'slow',dict(gate_id='wrong',family='atr',threshold=.1))


if __name__=='__main__':unittest.main()
