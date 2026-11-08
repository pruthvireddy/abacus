import contextlib
import gzip
import importlib.util
import io
import json
import tempfile
import unittest
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SOURCE = Path('/Users/pruthvi/Documents/projects/abacus/studies/27_verniman_method_knowledge/capture_daily_maps.py')
spec = importlib.util.spec_from_file_location('daily_capture_maintenance', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
HOST = 'https://verniman.blogspot.com'
SEED = mod.SEED
BOUNDARY = HOST + '/2008/12/boundary.html'
JANUARY = HOST + '/2009/01/start.html'
MISSING = HOST + '/2009/10/missing.html'
SKIPPED = HOST + '/2009/05/skipped.html'
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


def article(md, older=None):
    nav = f'<a id="Blog1_blog-pager-older-link" href="{older}">Older</a>' if older else ''
    return (f'<h3 class="post-title">Fixture</h3><div class="post-body"><p>Outlook {md}: fixture.</p></div>{nav}').encode()


class OfflineCapture(mod.Capture):
    def __init__(self, *args, responses, **kwargs):
        super().__init__(*args, **kwargs)
        self.responses = responses
        self.calls = Counter()

    def fetch(self, url, kind='html'):
        self.number += 1
        self.calls[url] += 1
        raw = self.responses.get(url)
        rec = {'url': url, 'captured_at': '2026-10-31T00:00:00+00:00',
               'error': None if raw is not None else 'fixture unavailable',
               'http_status': 200 if raw is not None else 404}
        if raw is not None:
            rec.update(self.store(gzip.compress(raw, mtime=0), f'captures/fixture-{self.number:04d}.{kind}.gz',
                                  uncompressed_sha256=mod.digest(raw), uncompressed_bytes=len(raw)))
        self.m['attempts'].append(rec)
        return rec, raw


class CaptureMaintenanceTests(unittest.TestCase):
    def run_fixture(self, responses, old=(), recent=(), sitemap=None):
        temporary = tempfile.TemporaryDirectory(prefix='abacus-daily-map-', dir='/private/tmp')
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        def retained(records, group):
            result = []
            for index, (url, stamp, raw) in enumerate(records):
                path = root / group / f'{index}.html'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                result.append({'url': url, 'source_url': url, 'session_date': stamp,
                               'html': {'path': path.relative_to(root).as_posix(), 'sha256': mod.digest(raw),
                                        'bytes': len(raw), 'captured_at': '2026-10-20T00:00:00+00:00'}, 'images': []})
            return result
        for loc, key, values, group in [(mod.OLD, 'posts', old, 'old'), (mod.RECENT, 'source_dispositions', recent, 'recent')]:
            target = root / loc
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({key: retained(values, group)}))
        page = HOST + '/sitemap.xml?page=1'
        urls = sitemap or [SEED, BOUNDARY]
        responses = dict(responses)
        responses[JANUARY + '?m=0'] = article('01/02', BOUNDARY)
        responses[HOST + '/sitemap.xml'] = f'<sitemapindex xmlns="{NS}"><sitemap><loc>{page.replace("&", "&amp;")}</loc></sitemap></sitemapindex>'.encode()
        responses[page] = ('<urlset xmlns="' + NS + '">' + ''.join('<url><loc>' + u + '</loc></url>' for u in urls) + '</urlset>').encode()
        capture = OfflineCapture(root, root / 'stage', date(2026, 1, 1), date(2026, 10, 30), responses=responses)
        with contextlib.redirect_stdout(io.StringIO()):
            capture.run()
        return capture

    def test_retained_boundary_stops_and_is_not_in_scope(self):
        capture = self.run_fixture({SEED + '?m=0': article('01/02', BOUNDARY)},
                                   old=[(BOUNDARY, '2025-12-31', article('12/31', HOST + '/2008/12/older.html'))])
        self.assertTrue(capture.m['lower_boundary_reached'])
        self.assertEqual(capture.m['boundary_post']['session_date'], '2025-12-31')
        self.assertEqual([(p['url'], p['session_date']) for p in capture.m['posts']], [(SEED, '2026-01-02')])
        self.assertNotIn(HOST + '/2008/12/older.html?m=0', capture.calls)

    def test_failed_seen_url_reconciles_against_earlier_valid_revision(self):
        capture = self.run_fixture({SEED + '?m=0': article('10/30', MISSING), BOUNDARY + '?m=0': article('12/31')},
            old=[(MISSING, '2026-10-29', article('10/29', JANUARY))],
            recent=[(MISSING, '2026-10-29', b'<html>no article body</html>')],
            sitemap=[SEED, MISSING, JANUARY, BOUNDARY])
        rows = [p for p in capture.m['posts'] if p['url'] == MISSING]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['session_date'], '2026-10-29')
        self.assertEqual(rows[0]['capture_kind'], 'retained')
        self.assertTrue(capture.m['lower_boundary_reached'])

    def test_changed_live_date_preserves_distinct_prior_pinned_dates(self):
        capture = self.run_fixture({SEED + '?m=0': article('10/30', JANUARY), BOUNDARY + '?m=0': article('12/31')},
            old=[(SEED, '2026-10-20', article('10/20', BOUNDARY)), (SEED, '2026-10-19', article('10/19', BOUNDARY))])
        rows = [p for p in capture.m['posts'] if p['url'] == SEED]
        self.assertEqual({p['session_date'] for p in rows}, {'2026-10-30', '2026-10-20', '2026-10-19'})
        earlier = [p for p in rows if p['capture_kind'] == 'retained']
        self.assertEqual(len(earlier), 2)
        self.assertTrue(all(p['session_date'] == p['retained_manifest_date'] for p in earlier))
        self.assertTrue(all(p['live_status'].startswith('live_revision_has_different_body_date') for p in earlier))

    def test_sitemap_locator_skipped_by_chain_is_attempted_within_boundary(self):
        outside = HOST + '/2008/11/outside.html'
        capture = self.run_fixture({SEED + '?m=0': article('10/30', JANUARY), BOUNDARY + '?m=0': article('12/31'),
                                   SKIPPED + '?m=0': article('05/01')}, sitemap=[SEED, SKIPPED, JANUARY, BOUNDARY, outside])
        rows = [p for p in capture.m['posts'] if p['url'] == SKIPPED]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['session_date'], '2026-05-01')
        self.assertEqual(rows[0]['discovery'], 'supplemental_official_sitemap_seed_to_boundary_range')
        self.assertNotIn(outside + '?m=0', capture.calls)

    def test_no_sitemap_range_inferred_without_known_boundary(self):
        capture = self.run_fixture({SEED + '?m=0': article('10/30', SEED)}, sitemap=[SEED, SKIPPED])
        self.assertFalse(capture.m['lower_boundary_reached'])
        # SKIPPED is attempted by observed next-locator recovery, not a synthetic full-range sweep.
        self.assertNotIn('supplemental_official_sitemap_seed_to_boundary_range',
                         [p.get('discovery') for p in capture.m['posts']])


if __name__ == '__main__':
    unittest.main(verbosity=2)
