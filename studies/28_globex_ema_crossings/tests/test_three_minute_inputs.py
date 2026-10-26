"""Synthetic 3m OHLCV/VWAP and clock boundary checks; no market inputs."""
from datetime import date
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
import pyarrow as pa
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.engine import aggregate_closes, window_masks
from src.inputs import derive_three_minute_session
from abacus_bhishma.session_anchored_vwap import output_schema


class ThreeMinuteDerivation(unittest.TestCase):
    def source(self, start='2024-06-02T22:00Z'):
        n=1380
        ts=pd.date_range(start,periods=n,freq='min')
        prices=(100+np.arange(n)%9).astype(np.int64)*10**9
        return pa.table({'ts_event':pa.array(ts,type=pa.timestamp('ns',tz='UTC')),
            'session_date':[date(2024,6,3)]*n,'product':['ES']*n,
            'continuous_symbol':['ES.c.0']*n,'instrument_id':pa.array([1]*n,type=pa.uint32()),
            'raw_symbol':['ESM4']*n,'open':prices,'high':prices+2*10**9,'low':prices-10**9,
            'close':prices+10**9,'volume':pa.array(1+np.arange(n)%3,type=pa.uint64()),
            'mapping_start':[date(2024,6,1)]*n,'mapping_end':[date(2024,6,30)]*n,
            'roll_id':pa.array([1]*n,type=pa.int16()),'is_roll':[False]*n,
            'source_batch':['synthetic']*n,'price_adjustment':[0]*n})

    def derive(self, source):
        return derive_three_minute_session(source,'ES',250000000,output_schema('a'*64,'b'*64,'c'*64,3))

    def test_complete_three_minute_ohlcv_and_weighted_hlc3_vwap(self):
        source=self.source();t=self.derive(source);f=t.to_pandas()
        self.assertEqual(len(f),460);self.assertIsNone(t.schema.metadata)
        self.assertTrue((f.source_bar_count==3).all())
        self.assertEqual(f.open.iloc[0],100*10**9)
        self.assertEqual(f.high.iloc[0],104*10**9)
        self.assertEqual(f.low.iloc[0],99*10**9)
        self.assertEqual(f.close.iloc[0],103*10**9)
        self.assertEqual(f.volume.iloc[0],6)
        self.assertEqual(f.volume.sum(),sum(source['volume'].to_pylist()))
        hlc=(f.high.to_numpy(float)+f.low.to_numpy(float)+f.close.to_numpy(float))*1e-9/3
        expected=np.cumsum(hlc*f.volume.to_numpy(float))/np.cumsum(f.volume.to_numpy(float))
        np.testing.assert_allclose(f.globex_vwap,expected,rtol=1e-12,atol=1e-10)
        self.assertEqual(f.ts_event.iloc[0],pd.Timestamp('2024-06-02T22:00Z'))
        self.assertEqual(f.bar_close_ts.iloc[-1],pd.Timestamp('2024-06-03T21:00Z'))
        self.assertTrue((f.bar_close_ts==f.available_at).all())

    def test_missing_duplicate_or_shifted_roster_rejected(self):
        with self.assertRaisesRegex(ValueError,'complete session'):self.derive(self.source().slice(1))
        source=self.source();bad=pa.concat_tables([source.slice(0,1),source.slice(0,1379)])
        with self.assertRaisesRegex(ValueError,'roster'):self.derive(bad)
        with self.assertRaisesRegex(ValueError,'roster'):self.derive(self.source('2024-06-02T22:01Z'))

    def test_contract_or_adjustment_change_rejected(self):
        for col in ['raw_symbol','price_adjustment']:
            source=self.source();v=source[col].to_pylist();v[-1]='ESH5' if col=='raw_symbol' else 10
            source=source.set_column(source.schema.get_field_index(col),col,pa.array(v,type=source[col].type))
            with self.assertRaisesRegex(ValueError,'lineage'):self.derive(source)

    def test_three_minute_close_alignment_and_no_missing_bar_fill(self):
        minutes=pd.DataFrame({'ts_event':pd.to_datetime(['2024-06-02T22:00Z','2024-06-02T22:02Z','2024-06-02T22:06Z']),
                              'close':[100,102,106]})
        bars=aggregate_closes(minutes,'3m')
        self.assertEqual(bars.close.tolist(),[102,106]);self.assertEqual(bars.index.minute.tolist(),[0,6])

    def test_cash_gc_and_opening_sensitivity_boundaries(self):
        ts=pd.date_range('2024-06-02T18:00',periods=460,freq='3min',tz='America/New_York')
        masks=window_masks(ts,'GC',np.arange(460))
        cash=ts[masks['us_cash']];gc=ts[masks['gc_day']];later=ts[masks['globex_after_30_bars']]
        self.assertEqual(len(cash),130);self.assertEqual(cash[0].strftime('%H:%M'),'09:30')
        self.assertEqual(cash[-1].strftime('%H:%M'),'15:57')
        self.assertEqual(len(gc),103);self.assertEqual(gc[0].strftime('%H:%M'),'08:21')
        self.assertEqual(gc[-1].strftime('%H:%M'),'13:27')
        self.assertEqual(later[0].strftime('%H:%M'),'19:33')

    def test_winter_anchor_uses_new_york_clock(self):
        source=self.source('2024-01-01T23:00Z')
        source=source.set_column(source.schema.get_field_index('session_date'),'session_date',pa.array([date(2024,1,2)]*1380))
        f=self.derive(source).to_pandas()
        self.assertEqual(f.ts_event.iloc[0].tz_convert('America/New_York').hour,18)
        self.assertEqual(f.bar_close_ts.iloc[-1].tz_convert('America/New_York').hour,17)


if __name__=='__main__':unittest.main()
