"""Offline reviewed-context exclusion guard and terminal navigation fixtures."""
from contextlib import redirect_stdout
from datetime import date
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import MethodType
from xml.sax.saxutils import escape
sys.dont_write_bytecode = True
ROOT = Path('/Users/pruthvi/Documents/projects/abacus')
SOURCE = ROOT / 'studies/27_verniman_method_knowledge/capture_daily_maps.py'
spec = importlib.util.spec_from_file_location('scope_fixture_capture2017', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
MANIFEST = 'data/raw/blogspot/verniman/html/20261021T033311Z_history_bccc6daf/collection_manifest.final.json'
original = json.loads((ROOT / MANIFEST).read_text())
seed = original['posts'][0]['url']

def rejects(call, expected):
    try:
        call()
    except ValueError as exc:
        assert expected in str(exc), str(exc)
        return
    raise AssertionError('guard accepted invalid input')

with tempfile.TemporaryDirectory(prefix='daily-map-2017-scope-') as tmp:
    top = Path(tmp).resolve()
    capture = module.Capture(ROOT, top/'valid', date(2017,1,1), date(2017,12,31), seed=seed, retained_manifests=[MANIFEST])
    capture.load_retained()
    assert len(capture.scope_exclusions) == 5
    rule = next(iter(capture.scope_exclusions.values()))
    original_raw = (ROOT / rule['source_html']['path']).read_text()
    capture.validate_scope_exclusion(rule['url'], module.Post(original_raw), rule)
    changed = module.Post('<div class="post-body">Changed educational body</div>')
    rejects(lambda: capture.validate_scope_exclusion(rule['url'], changed, rule), 'body identity mismatch')
    dated = module.Post('<div class="post-body">Outlook 11/01: A dated body</div>')
    dated_rule = {**rule, 'body_text_sha256': module.digest(''.join(dated.parts).replace(' ', '').encode())}
    rejects(lambda: capture.validate_scope_exclusion(rule['url'], dated, dated_rule), 'body identity mismatch')
    mismatch = module.Capture(ROOT, top/'wrong-scope', date(2016,1,1), date(2017,12,31), seed=seed, retained_manifests=[MANIFEST])
    rejects(mismatch.load_retained, 'differ from requested scope')
    minimal_root = top/'review-drift-root'
    minimal_root.mkdir()
    copied = json.loads(json.dumps(original))
    (minimal_root/'review.json').write_text('changed review bytes')
    copied['collection_completion_review'] = {'path':'review.json', 'bytes':3, 'sha256':hashlib.sha256(b'old').hexdigest()}
    (minimal_root/'manifest.json').write_text(json.dumps(copied))
    drift = module.Capture(minimal_root, top/'review-drift-stage', date(2017,1,1), date(2017,12,31), seed=seed, retained_manifests=['manifest.json'])
    rejects(drift.load_retained, 'retained input identity mismatch')
    # Full retained HTML chain served by a local in-memory fetch substitute.
    rows = original['posts'] + original['excluded_context_posts']
    bodies = {r['url']:(ROOT/r['html']['path']).read_bytes() for r in rows}
    order = [r['source_url'] for r in original['traversal'] if r.get('kind')=='post']
    assert len(order) == len(rows) == 45
    sitemap_page = 'https://verniman.blogspot.com/sitemap-fixture.xml'
    unrelated = 'https://verniman.blogspot.com/2000/02/unrelated-fixture.html'
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    index = (f'<sitemapindex xmlns="{ns}"><sitemap><loc>{sitemap_page}</loc></sitemap></sitemapindex>').encode()
    page = (f'<urlset xmlns="{ns}">' + ''.join('<url><loc>'+escape(u)+'</loc></url>' for u in order+[unrelated]) + '</urlset>').encode()
    counter = [0]
    def mock_fetch(self, url, kind='html'):
        counter[0] += 1
        if url == 'https://verniman.blogspot.com/sitemap.xml': raw = index
        elif url == sitemap_page: raw = page
        else:
            target = module.canonical(url)
            assert target in bodies, 'collector crossed reviewed terminal into unrelated source'
            raw = bodies[target]
        record = self.store(gzip.compress(raw,mtime=0), f'captures/mock-{counter[0]:04d}.{kind}.gz', url=url, http_status=200, error=None, uncompressed_sha256=module.digest(raw), uncompressed_bytes=len(raw), captured_at='fixture')
        self.m['attempts'].append(record)
        return record, raw
    capture.fetch = MethodType(mock_fetch, capture)
    with redirect_stdout(io.StringIO()):
        capture.run()
    selected = capture.m['posts']
    excluded = capture.m['excluded_context_posts']
    assert len(selected) == 40 and len(excluded) == 5
    assert sum(p['session_date'] is None for p in selected) == 12
    assert {p['url'] for p in selected} == {p['url'] for p in original['posts']}
    assert {p['url'] for p in excluded} == {p['url'] for p in original['excluded_context_posts']}
    assert all(p['archive_role']=='excluded_reviewed_context' for p in excluded)
    assert all(p.get('archive_role')!='excluded_reviewed_context' for p in selected)
    assert capture.m['stop_reason']=='navigation_exhausted' and capture.m['lower_boundary_reached'] is False
    assert capture.m['sitemap_scope']['end_kind']=='observed_navigation_terminal'
    assert capture.m['sitemap_scope']['candidate_count']==45
    assert capture.m['traversal'][-1]['from'].endswith('/vtp.html') and capture.m['traversal'][-1]['to'] is None
print(json.dumps({'status':'passed','scope_mismatch_rejected':True,'review_byte_drift_rejected':True,'excluded_body_drift_rejected':True,'dated_body_exclusion_rejected':True,'selected_daily_plans':40,'undated_plans_preserved':12,'excluded_context_records':5,'mock_navigation_records':45,'terminal_does_not_cross_to_unrelated_sitemap_locator':True,'lower_boundary_claimed':False}))
