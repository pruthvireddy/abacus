import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from abacus_bhishma.ema_cloud import expected_minutes,aggregate_minutes,add_features
from abacus_bhishma.ema_cloud_loader_v2 import load_release
from abacus_bhishma.ema_cloud_release_v2 import scientific_prefix_parity,integer_aggregation_check,prepare_release,combine_roster
from abacus_bhishma.provenance import sha256_file


class ExtendedInputTests(unittest.TestCase):
    def test_equity_pause_session_date_transition_independent_three_five_buckets(self):
        for product in ('ES','NQ'):
            for session,expected in (('2021-06-25',1365),('2021-06-28',1380)):
                end=(pd.Timestamp(session)+pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                schedule=expected_minutes(product,session,end)
                local=schedule.timestamp.dt.tz_convert('America/New_York')
                pause=local.dt.hour.eq(16)&local.dt.minute.between(15,29)
                self.assertEqual(len(schedule),expected)
                self.assertEqual(int(pause.sum()),0 if session=='2021-06-25' else 15)
                source=pd.DataFrame(dict(timestamp=schedule.timestamp,contract='A',open=10.,high=11.,low=9.,close=10.,volume=1.))
                for interval in (3,5):
                    rebuilt=aggregate_minutes(source,interval,schedule,product)
                    local=rebuilt.timestamp.dt.tz_convert('America/New_York')
                    at1630=rebuilt.loc[local.dt.hour.eq(16)&local.dt.minute.eq(30)].iloc[0]
                    self.assertEqual(bool(at1630.known_closure_before),session=='2021-06-25')
                    self.assertTrue(rebuilt.usable.all())
                    self.assertEqual(len(rebuilt),expected//interval)
        self.assertEqual(len(expected_minutes('GC','2021-06-25','2021-06-26')),1380)

    def test_prefix_exact_null_false_dtype_and_reordered_column_mutations(self):
        old=pd.DataFrame(dict(timestamp=pd.to_datetime(['2020-12-31T23:55Z'],utc=True),
            available_at=pd.to_datetime(['2021-01-01T00:00Z'],utc=True),usable=[False],close=[np.nan]))
        extended=pd.concat([old,old.assign(timestamp=pd.Timestamp('2021-01-02T00:00Z'),available_at=pd.Timestamp('2021-01-02T00:05Z'))],ignore_index=True)
        self.assertEqual(scientific_prefix_parity(old,extended)['cells'],4)
        for mutated in (extended.assign(usable=[None,False]),extended.assign(close=[0.,np.nan]),extended[list(reversed(extended.columns))]):
            with self.assertRaises(ValueError):scientific_prefix_parity(old,mutated)

    def test_independent_integer_aggregation_both_intervals_refuses_price_and_volume_mutations(self):
        ts=pd.date_range('2019-01-02T14:00Z',periods=15,freq='min')
        fixed=pd.DataFrame(dict(ts_event=ts,open=np.arange(15)*10**9+100*10**9,
            high=np.arange(15)*10**9+102*10**9,low=np.arange(15)*10**9+99*10**9,
            close=np.arange(15)*10**9+101*10**9,volume=np.arange(15)+1,instrument_id=7,is_roll=False))
        source=fixed.rename(columns={'ts_event':'timestamp'}).assign(contract='A')
        for column in ('open','high','low','close'):source[column]=source[column]*1e-9
        schedule=pd.DataFrame(dict(timestamp=ts,session='2019-01-02',calendar_event='',calendar_valid=True))
        for interval in (3,5):
            result=aggregate_minutes(source,interval,schedule,'ES')
            self.assertEqual(integer_aggregation_check(fixed,result,interval)['status'],'passed')
            for column in ('open','volume'):
                corrupted=result.copy();corrupted.loc[0,column]+=1
                with self.assertRaises(ValueError):integer_aggregation_check(fixed,corrupted,interval)

    def test_feature_year_processing_boundary_carries_same_seed_state(self):
        times=pd.date_range('2020-12-31T22:00Z',periods=260,freq='5min')
        source=pd.DataFrame(dict(timestamp=times,contract='A',open=10.,high=11.,low=9.,close=10.,
            usable=True,quality_reason='',known_closure_before=False))
        full=add_features(source)
        combined=combine_roster([source.iloc[:100],source.iloc[100:]],5)
        pd.testing.assert_frame_equal(full,combined,check_exact=True)
        self.assertTrue(full.feature_valid.iloc[249])
        self.assertEqual(full.consecutive_count.iloc[-1],260)
        self.assertEqual(combined.atr14.iloc[-1],2.)
        self.assertEqual(combined.ema50.iloc[-1],10.)

    def test_version_loader_legacy_compatibility_selected_size_pin_and_role_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);part=root/'part.parquet'
            pq.write_table(pa.Table.from_pandas(pd.DataFrame(dict(timestamp=pd.to_datetime(['2018-01-02T14:00Z']),
                product=['ES'],interval_minutes=[3],usable=[True])),preserve_index=False),part)
            for version in ('1.0.0','1.1.0'):
                manifest=root/f'manifest-{version}.json'
                value=dict(dataset_id=f'same_contract_ema_cloud__{version}',version=version,output_files=[dict(
                    path='part.parquet',bytes=part.stat().st_size,sha256=sha256_file(part),product='ES',interval_minutes=3,role='bars3',rows=1)])
                manifest.write_text(json.dumps(value))
                self.assertEqual(len(load_release(root,product='ES',interval=3,manifest_path=manifest,expected_manifest_sha256=sha256_file(manifest))),1)
            value['output_files'][0]['role']='bars5features';manifest.write_text(json.dumps(value))
            with self.assertRaises(ValueError):load_release(root,product='ES',interval=3,manifest_path=manifest,expected_manifest_sha256=sha256_file(manifest))
            value['output_files'][0]['role']='bars3';value['output_files'][0]['bytes']+=1;manifest.write_text(json.dumps(value))
            with self.assertRaises(ValueError):load_release(root,product='ES',interval=3,manifest_path=manifest,expected_manifest_sha256=sha256_file(manifest))

    def test_existing_extended_release_refused_without_reading_or_rebuilding_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'pyproject.toml').write_text('[tool.uv.workspace]\nmembers=[]\n')
            (root/'config').mkdir();(root/'config/paths.local.toml').write_text('[paths]\npublication_root="."\n')
            kept=root/'data/features/ema_cloud/version=1.1.0';kept.mkdir(parents=True)
            (kept/'immutable').write_bytes(b'original')
            with self.assertRaises(FileExistsError):prepare_release(root,root/'audit','new')
            self.assertEqual((kept/'immutable').read_bytes(),b'original')
            self.assertFalse((root/'data/staging/ema_cloud/new').exists())


if __name__=='__main__':unittest.main()
