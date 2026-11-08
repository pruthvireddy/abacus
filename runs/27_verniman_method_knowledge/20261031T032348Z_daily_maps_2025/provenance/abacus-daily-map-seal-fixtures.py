import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE=Path('/Users/pruthvi/Documents/projects/abacus/studies/27_verniman_method_knowledge/seal_daily_maps.py')
spec=importlib.util.spec_from_file_location('daily_map_sealer',SOURCE)
sealer=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealer)

class SealerTests(unittest.TestCase):
    def fixture(self, temp):
        root=Path(temp);stage=root/'work'/sealer.STUDY_ID/'20261031T032348Z_daily_maps_2025';archive=stage/'archive';archive.mkdir(parents=True)
        source=root/'studies'/sealer.STUDY_ID;source.mkdir(parents=True)
        (source/'daily-map-plan.md').write_text('# Private annual archive protocol\n')
        (source/'study.json').write_text(json.dumps({'study_id':sealer.STUDY_ID}))
        provenance=stage/'provenance';provenance.mkdir();(provenance/'environment.json').write_text('{"python":"fixture"}\n')
        (provenance/'capture.py').write_text('# frozen input producer\n')
        files={
            'README.md':'# Daily Map 2025\n\n[Reader](index.html) · [Year](2025/README.md) · [Gaps](gap-log.md)\n',
            '2025/README.md':'# 2025\n\n[December](12/README.md)\n',
            '2025/12/README.md':'# December\n\n[December 31](31/README.md)\n',
            '2025/12/31/README.md':'# Daily Map 2025-12-31\n\n[Reader](index.html) · [Compressed source](p0001/source.html.gz)\n',
            'gap-log.md':'# Gaps\n\nNo fixture gap.\n',
            'index.html':'<html><body><a href="2025/index.html">2025</a><a href="gap-log.md">Gaps</a></body></html>',
            '2025/index.html':'<html><body><a href="12/index.html">December</a></body></html>',
            '2025/12/index.html':'<html><body><a href="31/index.html">31</a></body></html>',
            '2025/12/31/index.html':'<html><body><a href="../../../index.html">Archive</a></body></html>',
            'metrics.json':json.dumps({'calendar_days':365,'map_records':1}),
            'coverage.csv':'date,post_count\n2025-12-31,1\n',
        }
        for path,data in files.items():
            dest=archive/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(data)
        dest=archive/'2025/12/31/p0001/source.html.gz';dest.parent.mkdir(parents=True);dest.write_bytes(gzip.compress(b'<div class="post-body">Private source fixture</div>',mtime=0))
        cap={'run_id':stage.name,'start_date':'2025-01-01','end_date':'2025-12-31','command':['studies/27_verniman_method_knowledge/capture_daily_maps.py','--stage',str(stage)],'posts':[],'retained_inputs':[]}
        raw=json.dumps(cap).encode();(stage/'capture-manifest.json').write_bytes(raw)
        inventory={'source_capture_manifest_sha256':hashlib.sha256(raw).hexdigest(),'files':[sealer.identity(p,relative_to=archive) for p in sorted(archive.rglob('*')) if p.is_file()]}
        (archive/'archive-manifest.json').write_text(json.dumps(inventory))
        report='# Annual archive fixture\n\n[Reader](../../../work/'+sealer.STUDY_ID+'/'+stage.name+'/archive/index.html) · [Dates](knowledge-base/daily-map/README.md)\n'
        (stage/'archive-report.md').write_text(report)
        (stage/'verification.json').write_text('{"status":"passed","scope":"source preservation fixture"}')
        return root,stage

    def test_prepare_rewrites_links_and_seals_once(self):
        with tempfile.TemporaryDirectory(prefix='daily-map-seal-links-') as temp:
            root,stage=self.fixture(temp)
            r=sealer.prepare(stage,root=root);self.assertEqual(r['status'],'prepared')
            bundle=stage/'completed-bundle'
            self.assertIn('[Year](2025/README.md)',(bundle/'knowledge-base/daily-map/README.md').read_text())
            day=(bundle/'knowledge-base/daily-map/2025/12/31/README.md').read_text()
            self.assertIn('/work/',day);self.assertIn('/archive/2025/12/31/p0001/source.html.gz',day)
            self.assertEqual((bundle/'report.md').read_bytes(),(stage/'archive-report.md').read_bytes())
            self.assertIn('../../../work/',(bundle/'report.html').read_text())
            self.assertTrue((bundle/'provenance/producer/seal_daily_maps.py').is_file())
            with self.assertRaises(FileExistsError):sealer.prepare(stage,root=root)
            result=sealer.seal(stage,root=root);self.assertEqual(result['status'],'sealed')
            with self.assertRaises(FileExistsError):sealer.seal(stage,root=root)

    def test_prepared_artifact_tamper_refuses_seal(self):
        with tempfile.TemporaryDirectory(prefix='daily-map-seal-tamper-') as temp:
            root,stage=self.fixture(temp);sealer.prepare(stage,root=root)
            (stage/'completed-bundle/report.md').write_text('changed report')
            with self.assertRaises(ValueError):sealer.seal(stage,root=root)
            self.assertFalse((root/'runs'/sealer.STUDY_ID/stage.name).exists())

    def test_payload_tamper_refuses_seal(self):
        with tempfile.TemporaryDirectory(prefix='daily-map-seal-payload-') as temp:
            root,stage=self.fixture(temp);sealer.prepare(stage,root=root)
            (stage/'archive/coverage.csv').write_text('changed data')
            with self.assertRaises(ValueError):sealer.seal(stage,root=root)
            self.assertFalse((root/'runs'/sealer.STUDY_ID/stage.name).exists())

    def test_failed_verification_refuses_prepare(self):
        with tempfile.TemporaryDirectory(prefix='daily-map-seal-checks-') as temp:
            root,stage=self.fixture(temp)
            (stage/'verification.json').write_text('{"status":"failed"}')
            with self.assertRaises(ValueError):sealer.prepare(stage,root=root)
            self.assertFalse((stage/'completed-bundle').exists())

    def test_broken_report_link_refuses_before_output(self):
        with tempfile.TemporaryDirectory(prefix='daily-map-seal-badlink-') as temp:
            root,stage=self.fixture(temp)
            (stage/'archive-report.md').write_text('# Report\n\n[Missing](missing.md)\n')
            with self.assertRaises(ValueError):sealer.prepare(stage,root=root)
            self.assertFalse((stage/'completed-bundle').exists())

    def test_modified_verification_after_prepare_refuses_seal(self):
        with tempfile.TemporaryDirectory(prefix='daily-map-seal-checks-change-') as temp:
            root,stage=self.fixture(temp);sealer.prepare(stage,root=root)
            (stage/'verification.json').write_text('{"status":"passed","changed":true}')
            with self.assertRaises(ValueError):sealer.seal(stage,root=root)
            self.assertFalse((root/'runs'/sealer.STUDY_ID/stage.name).exists())

if __name__=='__main__':unittest.main(verbosity=2)
