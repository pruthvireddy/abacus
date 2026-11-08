import contextlib
import copy
import gzip
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path('/Users/pruthvi/Documents/projects/abacus')
SOURCE = ROOT / 'studies/27_verniman_method_knowledge/capture_daily_maps.py'
OVERRIDES = ROOT / 'studies/27_verniman_method_knowledge/daily-map-2022-date-overrides.json'
SPEC = importlib.util.spec_from_file_location('date_override_capture', SOURCE)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
BASE = json.loads(OVERRIDES.read_text())
BOUNDARY = BASE['overrides'][0]['url']
STALE = BASE['overrides'][1]['url']
SEED = 'https://verniman.blogspot.com/2005/12/final-day.html'
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
PRIOR = json.loads((ROOT / 'data/raw/blogspot/verniman/html/20261021T012001Z_history_49cd90e5/collection_manifest.reviewed.json').read_text())


class OfflineCapture(mod.Capture):
    def __init__(self, *args, responses=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.responses = responses or {}
    def fetch(self, url, kind='html'):
        raw = self.responses.get(url)
        record = {'url': url, 'http_status': 200 if raw else 404, 'captured_at': '2026-10-31T00:00:00+00:00',
                  'error': None if raw else 'fixture missing'}
        if raw:
            self.number += 1
            record.update(self.store(gzip.compress(raw, mtime=0), f'captures/fixture-{self.number:04d}.{kind}.gz',
                                     uncompressed_sha256=mod.digest(raw), uncompressed_bytes=len(raw)))
        self.m['attempts'].append(record)
        return record, raw
    def image(self, item):
        return {**item, 'error': 'image bytes outside this date-only fixture'}


def fixture_article(md, older=None):
    navigation = f'<a id="Blog1_blog-pager-older-link" href="{older}">Older</a>' if older else ''
    return f'<h3 class="post-title">Fixture</h3><div class="post-body">Outlook {md}: fixture.</div>{navigation}'.encode()


class DateExceptions(unittest.TestCase):
    def capture(self, *, responses=None):
        temporary = tempfile.TemporaryDirectory(prefix='abacus-2022-exceptions-', dir='/private/tmp')
        self.addCleanup(temporary.cleanup)
        stage = Path(temporary.name) / 'stage'
        return OfflineCapture(ROOT, stage, date(2022, 1, 1), date(2022, 12, 31),
                              seed=SEED, retained_manifests=[], date_override_manifest=OVERRIDES,
                              responses=responses)

    def test_explicit_boundary_after_may_is_not_misdated_december2022(self):
        rule = BASE['overrides'][0]
        raw = (ROOT / rule['evidence']['path']).read_bytes()
        cap = self.capture(responses={BOUNDARY + '?m=0': raw})
        with contextlib.redirect_stdout(io.StringIO()):
            row = cap.post(BOUNDARY, date(2022, 5, 16))
        self.assertEqual(row['session_date'], '2021-12-31')
        self.assertEqual(row['date_method'], 'explicit_reviewed_source_date_exception')
        self.assertEqual(row['date_warnings'], [rule['reason']])
        self.assertEqual(row['source_date_override'], rule)
        self.assertTrue(all('nonmonotonic' not in x for x in row['date_warnings']))

    def test_stale_article_becomes_separate_null_date_context(self):
        rule = BASE['overrides'][1]
        cap = self.capture(responses={STALE + '?m=0': (ROOT / rule['evidence']['path']).read_bytes()})
        with contextlib.redirect_stdout(io.StringIO()):
            row = cap.post(STALE, date(2022, 10, 19))
        self.assertIsNone(row['session_date'])
        self.assertEqual(row['source_date_override'], rule)
        self.assertEqual(len(row['images']), 2)

    def test_changed_body_is_refused_before_exception_or_images(self):
        rule = BASE['overrides'][1]
        raw = (ROOT / rule['evidence']['path']).read_bytes().replace(b'4464', b'4465')
        cap = self.capture(responses={STALE + '?m=0': raw})
        with self.assertRaisesRegex(ValueError, 'body identity mismatch'):
            cap.post(STALE, date(2022, 10, 19))
        self.assertEqual(cap.m['posts'], [])

    def test_wrong_scope_is_refused_before_stage_creation(self):
        with tempfile.TemporaryDirectory(prefix='abacus-2022-scope-', dir='/private/tmp') as tmp:
            stage = Path(tmp) / 'stage'
            with self.assertRaisesRegex(ValueError, 'requested scope differs'):
                mod.Capture(ROOT, stage, date(2023, 1, 1), date(2023, 12, 31), date_override_manifest=OVERRIDES)
            self.assertFalse(stage.exists())

    def test_input_identities_and_supporting_reviews_are_pinned(self):
        cap = self.capture()
        paths = {item['path'] for item in cap.m['retained_inputs']}
        self.assertIn(OVERRIDES.relative_to(ROOT).as_posix(), paths)
        for item in BASE['source_reviews'] + [r['evidence'] for r in BASE['overrides']]:
            self.assertIn(item['path'], paths)
        self.assertEqual(len(cap.m['retained_source_verifications']), 5)

    def test_reconciliation_does_not_duplicate_legacy_stale_stamp(self):
        boundary_raw = (ROOT / BASE['overrides'][0]['evidence']['path']).read_bytes()
        stale_raw = (ROOT / BASE['overrides'][1]['evidence']['path']).read_bytes()
        page = 'https://verniman.blogspot.com/sitemap.xml?page=1'
        cap = self.capture(responses={
            SEED + '?m=0': fixture_article('10/19', STALE),
            STALE + '?m=0': stale_raw,
            'https://verniman.blogspot.com/2005/10/monday-bounce.html?m=0': fixture_article('05/16', BOUNDARY),
            BOUNDARY + '?m=0': boundary_raw,
            'https://verniman.blogspot.com/sitemap.xml': f'<sitemapindex xmlns="{NS}"><sitemap><loc>{page}</loc></sitemap></sitemapindex>'.encode(),
            page: ('<urlset xmlns="' + NS + '">' + ''.join('<url><loc>' + u + '</loc></url>' for u in [SEED, STALE, 'https://verniman.blogspot.com/2005/10/monday-bounce.html', BOUNDARY]) + '</urlset>').encode()
        })
        old = next(x for x in PRIOR['posts'] if x['url'] == STALE)
        def load():
            cap.retained_revisions = [(STALE, old)]
            cap.retained[STALE] = old
        cap.load_retained = load
        with contextlib.redirect_stdout(io.StringIO()):
            cap.run()
        rows = [p for p in cap.m['posts'] if p['url'] == STALE]
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]['session_date'])
        self.assertEqual(cap.m['boundary_post']['session_date'], '2021-12-31')
        self.assertTrue(cap.m['lower_boundary_reached'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
