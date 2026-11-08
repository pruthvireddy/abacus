"""Offline 2017 calendar with undated plan and honestly absent year boundary."""
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
spec = importlib.util.spec_from_file_location('fixture_builder2017', SOURCE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
with tempfile.TemporaryDirectory(prefix='daily-map-2017-calendar-') as tmp:
    stage = Path(tmp)
    (stage / 'captures').mkdir()
    posts = []
    for i, stamp in enumerate(['2017-12-29', '2017-11-20', None], 1):
        outlook = stamp[5:].replace('-', '/') if stamp else ''
        raw = ('<h3 class="post-title">Fixture</h3><div class="post-body entry-content"><p>Outlook ' + outlook + ': Complete plan text.</p></div>').encode()
        compressed = gzip.compress(raw, mtime=0)
        relative = f'captures/post-{i}.html.gz'
        (stage / relative).write_bytes(compressed)
        posts.append({'url': f'https://verniman.blogspot.com/2000/12/fixture-{i}.html', 'session_date': stamp, 'title': stamp or 'Undated plan',
                      'html': {'path': relative, 'bytes': len(compressed), 'sha256': hashlib.sha256(compressed).hexdigest(), 'uncompressed_sha256': hashlib.sha256(raw).hexdigest()},
                      'images': [], 'date_warnings': [] if stamp else ['no_unambiguous_outlook_date'], 'capture_kind': 'live', 'date_method': 'explicit_fixture_date' if stamp else 'undated_commentary'})
    (stage / 'capture-manifest.json').write_text(json.dumps({'run_id': 'fixture2017', 'seed_url': posts[0]['url'], 'start_date': '2017-01-01', 'end_date': '2017-12-31', 'lower_boundary_reached': False, 'stop_reason': 'navigation_exhausted', 'posts': posts}))
    result = builder.build(stage)
    assert result['status'] == 'passed' and result['calendar_days'] == 365
    archive = stage / 'archive'
    rows = list(csv.DictReader((archive / 'coverage.csv').open()))
    assert len(rows) == 365 and rows[0]['date'] == '2017-12-31' and rows[-1]['date'] == '2017-01-01'
    assert [row['date'] for row in rows] == sorted([row['date'] for row in rows], reverse=True)
    assert rows[0]['post_count'] == '0' and rows[0]['status'] == 'no_dated_post_observed_weekend'
    assert rows[1]['date'] == '2017-12-30' and rows[1]['post_count'] == '0'
    assert rows[2]['date'] == '2017-12-29' and rows[2]['post_count'] == '1'
    assert rows[-1]['post_count'] == '0' and rows[-1]['status'] == 'no_dated_post_observed_weekend'
    assert rows[-2]['date'] == '2017-01-02' and rows[-2]['status'] == 'no_dated_post_observed_weekday'
    inventory = json.loads((archive / 'archive-manifest.json').read_text())
    indexes = {entry['path']: entry['dates'] for entry in inventory['indexes']}
    assert len(indexes['2017/12/index.html']) == 31 and len(indexes['2017/02/index.html']) == 28
    assert '<title>Daily Map · 2017 · Verniman Daily Map</title>' in (archive / 'index.html').read_text()
    assert not (archive / '2017/02/29/index.html').exists() and not (archive / '2016').exists()
    assert (archive / 'undated/index.html').is_file()
    metrics = json.loads((archive / 'metrics.json').read_text())
    assert metrics['map_records'] == 2 and metrics['unassigned_or_boundary_records'] == 1
    undated_record = [entry for entry in inventory['posts'] if entry.get('session_date') is None]
    assert len(undated_record) == 1
print(json.dumps({'status': 'passed', 'calendar_days': 365, 'latest_fixture_map': '2017-12-29', 'earliest_fixture_map': '2017-11-20', 'undated_plans_retained': 1, 'year_end_weekend_gaps': ['2017-12-30', '2017-12-31'], 'initial_weekend_gap': '2017-01-01', 'initial_weekday_gap': '2017-01-02', 'lower_boundary_observed': False, 'february_days': 28}))
