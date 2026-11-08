import csv
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

REPO = Path('/Users/pruthvi/Documents/projects/abacus')
SOURCE = REPO / 'studies/27_verniman_method_knowledge/build_daily_maps.py'
spec = importlib.util.spec_from_file_location('daily_map_builder', SOURCE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class YearAgnosticBuilderTests(unittest.TestCase):
    def fixture(self, base, boundary=None, *, start='2025-01-01', end='2025-12-31'):
        stage = Path(base)
        captures = stage / 'captures'
        captures.mkdir()
        posts = []
        for ordinal, stamp in enumerate([end, '2025-01-02'] + ([boundary] if boundary else []), 1):
            raw = ('<html><head><title>Test</title></head><body><h3 class="post-title">Fixture</h3>'
                   '<div class="post-body entry-content"><p>Outlook ' + stamp[5:].replace('-', '/') + '</p>'
                   '<p>Plan text <a href="https://verniman.blogspot.com/source.html">support</a>.</p></div>'
                   '<aside>Not part of article</aside></body></html>').encode()
            encoded = gzip.compress(raw, mtime=0)
            relative = f'captures/post-{ordinal}.html.gz'
            (stage / relative).write_bytes(encoded)
            posts.append({'url':f'https://verniman.blogspot.com/2008/12/fixture-{ordinal}.html',
                          'session_date':stamp, 'title':f'Fixture {stamp}',
                          'html':{'path':relative, 'bytes':len(encoded),
                                  'sha256':hashlib.sha256(encoded).hexdigest(),
                                  'uncompressed_sha256':hashlib.sha256(raw).hexdigest()},
                          'images':[], 'date_warnings':[], 'date_method':'fixture_explicit_date',
                          'capture_kind':'live','captured_at':'2026-10-31T03:24:00Z'})
        (stage / 'capture-manifest.json').write_text(json.dumps({'run_id':'fixture2025','start_date':start,'end_date':end,'posts':posts}))
        result = builder.build(stage)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['calendar_days'], 365)
        return stage / 'archive'

    def assert_year_order(self, archive):
        root = (archive / 'index.html').read_text()
        self.assertIn('<title>Daily Map · 2025 · Verniman Daily Map</title>', root)
        self.assertNotIn('Daily Map · 2026', root)
        inventory = json.loads((archive / 'archive-manifest.json').read_text())
        indexes = {x['path']:x['dates'] for x in inventory['indexes']}
        self.assertEqual(len(indexes), 14)
        self.assertEqual(indexes['index.html'][0], '2025-12-31')
        self.assertEqual(indexes['index.html'][-1], '2025-01-01')
        self.assertEqual(indexes['index.html'], sorted(indexes['index.html'], reverse=True))
        self.assertEqual(indexes['2025/index.html'], indexes['index.html'])
        for month in range(1, 13):
            key=f'2025/{month:02}/index.html'
            self.assertTrue(all(d.startswith(f'2025-{month:02}') for d in indexes[key]))
            self.assertEqual(indexes[key], sorted(indexes[key], reverse=True))
        with (archive/'coverage.csv').open() as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),365)
        self.assertEqual(rows[0]['date'],'2025-12-31')
        self.assertEqual(rows[-1]['date'],'2025-01-01')
        self.assertEqual(rows[-1]['post_count'],'0')
        self.assertTrue((archive/'2025/01/01/index.html').is_file())

    def test_full_2025_order_titles_and_gaps(self):
        with tempfile.TemporaryDirectory(prefix='daily-map-builder2025-') as tmp:
            archive=self.fixture(tmp)
            self.assert_year_order(archive)
            self.assertEqual(json.loads((archive/'metrics.json').read_text())['map_records'],2)
            self.assertEqual(builder.check(Path(tmp))['status'],'passed')

    def test_lower_boundary_is_retained_but_excluded_from_2025(self):
        with tempfile.TemporaryDirectory(prefix='daily-map-lower-boundary-') as tmp:
            archive=self.fixture(tmp,'2024-12-31')
            self.assert_year_order(archive)
            metrics=json.loads((archive/'metrics.json').read_text())
            self.assertEqual(metrics['map_records'],2)
            self.assertEqual(metrics['unassigned_or_boundary_records'],1)
            self.assertIn('Fixture 2024-12-31',(archive/'undated/index.html').read_text())
            self.assertFalse((archive/'2024').exists())

    def test_upper_boundary_is_retained_but_excluded_from_2025(self):
        with tempfile.TemporaryDirectory(prefix='daily-map-upper-boundary-') as tmp:
            archive=self.fixture(tmp,'2026-01-01')
            self.assert_year_order(archive)
            metrics=json.loads((archive/'metrics.json').read_text())
            self.assertEqual(metrics['map_records'],2)
            self.assertEqual(metrics['unassigned_or_boundary_records'],1)
            self.assertIn('Fixture 2026-01-01',(archive/'undated/index.html').read_text())
            self.assertFalse((archive/'2026').exists())

if __name__ == '__main__':
    unittest.main(verbosity=2)
