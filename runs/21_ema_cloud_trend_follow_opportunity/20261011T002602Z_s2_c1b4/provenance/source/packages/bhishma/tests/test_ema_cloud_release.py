import json
from pathlib import Path
import tempfile
import unittest
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from abacus_bhishma.ema_cloud import DATASET_ID, load_release
from abacus_bhishma.ema_cloud_release import reconciliation, prepare_release
from abacus_bhishma.provenance import sha256_file


class DeliveryTests(unittest.TestCase):
    def test_exact_adjustment_and_independent_float_reconciliation(self):
        ts=pd.date_range('2018-01-02 14:30',periods=5,freq='min',tz='UTC')
        source=pd.DataFrame(dict(ts_event=ts,open=[100000000000]*5,high=[102000000000]*5,
            low=[99000000000]*5,close=[101000000000]*5,volume=[1]*5,instrument_id=[7]*5,
            roll_id=[2]*5,is_roll=[False]*5))
        rebuilt=pd.DataFrame(dict(timestamp=[ts[0]],open=[100.],high=[102.],low=[99.],
                                  close=[101.],volume=[5],usable=[True]))
        retained=pd.DataFrame(dict(ts_event=[ts[0]],open=[110000000000],high=[112000000000],
            low=[109000000000],close=[111000000000],volume=[5],instrument_id=[7],roll_id=[2],
            contains_roll=[False],source_bar_count=[5],price_adjustment=[10000000000],
            is_mixed_contract_bar=[False],is_mixed_adjustment_bar=[False]))
        self.assertTrue(reconciliation(source,rebuilt,retained)['passed'])
        retained.loc[0,'price_adjustment']+=1
        with self.assertRaisesRegex(ValueError,'reconciliation failed'):
            reconciliation(source,rebuilt,retained)

    def test_loader_manifest_and_selected_byte_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);part=root/'part.parquet'
            pq.write_table(pa.table({'timestamp':['2018-01-02'],'usable':[True]}),part)
            manifest=root/'manifest.json'
            manifest.write_text(json.dumps(dict(dataset_id=DATASET_ID,version='1.0.0',output_files=[
                dict(path='part.parquet',sha256=sha256_file(part),bytes=part.stat().st_size,
                     product='ES',interval_minutes=3)])))
            pin=sha256_file(manifest)
            self.assertEqual(len(load_release(root,product='ES',interval=3,manifest_path=manifest,
                                              expected_manifest_sha256=pin)),1)
            with part.open('ab') as f:f.write(b'changed')
            with self.assertRaises(ValueError):
                load_release(root,product='ES',interval=3,manifest_path=manifest,expected_manifest_sha256=pin)
            with self.assertRaises(ValueError):
                load_release(root,product='ES',interval=3,manifest_path=manifest,expected_manifest_sha256='0'*64)

    def test_existing_release_refused_before_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'pyproject.toml').write_text('[tool.uv.workspace]\nmembers=[]\n')
            (root/'config').mkdir();(root/'config/paths.local.toml').write_text('[paths]\npublication_root="."\n')
            final=root/'data/features/ema_cloud/version=1.0.0';final.mkdir(parents=True)
            kept=final/'preserved';kept.write_bytes(b'original')
            with self.assertRaises(FileExistsError):prepare_release(root,root/'audit','new')
            self.assertEqual(kept.read_bytes(),b'original')
            self.assertFalse((root/'data/staging/ema_cloud/new').exists())


if __name__=='__main__':unittest.main()
