"""Offline 2018 calendar, final-day map and 2017 lower-boundary fixture."""
import csv
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
sys.dont_write_bytecode = True
ROOT = Path('/Users/pruthvi/Documents/projects/abacus')
SOURCE = ROOT / 'studies/27_verniman_method_knowledge/build_daily_maps.py'
spec = importlib.util.spec_from_file_location('fixture_builder2018', SOURCE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
with tempfile.TemporaryDirectory(prefix='daily-map-2018-calendar-') as tmp:
    stage = Path(tmp)
    (stage / 'captures').mkdir()
    posts = []
    for i, stamp in enumerate(['2018-12-31', '2018-01-02', '2017-12-29'], 1):
        raw = ('<h3 class="post-title">Fixture</h3><div class="post-body entry-content"><p>Outlook ' + stamp[5:].replace('-', '/') + '</p><p>Complete plan text.</p></div>').encode()
        compressed = gzip.compress(raw, mtime=0)
        relative = f'captures/post-{i}.html.gz'
        (stage / relative).write_bytes(compressed)
        posts.append({'url': f'https://verniman.blogspot.com/2004/12/fixture-{i}.html', 'session_date': stamp, 'title': stamp,
                      'html': {'path': relative, 'bytes': len(compressed), 'sha256': hashlib.sha256(compressed).hexdigest(), 'uncompressed_sha256': hashlib.sha256(raw).hexdigest()},
                      'images': [], 'date_warnings': [], 'capture_kind': 'live', 'date_method': 'explicit_fixture_date'})
    (stage / 'capture-manifest.json').write_text(json.dumps({'run_id': 'fixture2018', 'seed_url': posts[0]['url'], 'start_date': '2018-01-01', 'end_date': '2018-12-31', 'posts': posts}))
    result = builder.build(stage)
    assert result['status'] == 'passed' and result['calendar_days'] == 365
    archive = stage / 'archive'
    rows = list(csv.DictReader((archive / 'coverage.csv').open()))
    assert len(rows) == 365 and rows[0]['date'] == '2018-12-31' and rows[-1]['date'] == '2018-01-01'
    assert [row['date'] for row in rows] == sorted([row['date'] for row in rows], reverse=True)
    assert rows[0]['post_count'] == '1' and rows[0]['status'] == 'captured_live'
    assert rows[-1]['post_count'] == '0' and rows[-1]['status'] == 'no_dated_post_observed_weekday'
    inventory = json.loads((archive / 'archive-manifest.json').read_text())
    indexes = {entry['path']: entry['dates'] for entry in inventory['indexes']}
    assert len(indexes['2018/12/index.html']) == 31 and len(indexes['2018/02/index.html']) == 28
    assert '<title>Daily Map · 2018 · Verniman Daily Map</title>' in (archive / 'index.html').read_text()
    assert not (archive / '2018/02/29/index.html').exists()
    assert '2018-02-29' not in indexes['2018/02/index.html']
    assert not (archive / '2017').exists()
    metrics = json.loads((archive / 'metrics.json').read_text())
    assert metrics['map_records'] == 2 and metrics['unassigned_or_boundary_records'] == 1
print(json.dumps({'status': 'passed', 'calendar_days': 365, 'latest_fixture_map': '2018-12-31', 'earliest_fixture_map': '2018-01-02', 'initial_weekday_gap': '2018-01-01', 'lower_boundary_excluded': '2017-12-29', 'february_days': 28}))
