"""Offline 2022 year-end weekend, early-source gap and lower-boundary fixture."""
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
spec = importlib.util.spec_from_file_location('fixture_builder2022', SOURCE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
with tempfile.TemporaryDirectory(prefix='daily-map-2022-weekend-') as tmp:
    stage = Path(tmp)
    (stage / 'captures').mkdir()
    posts = []
    for i, stamp in enumerate(['2022-12-30', '2022-05-16', '2021-12-31'], 1):
        raw = ('<h3 class="post-title">Fixture</h3><div class="post-body entry-content"><p>Outlook ' + stamp[5:].replace('-', '/') + '</p><p>Complete plan text.</p></div>').encode()
        compressed = gzip.compress(raw, mtime=0)
        relative = f'captures/post-{i}.html.gz'
        (stage / relative).write_bytes(compressed)
        posts.append({'url': f'https://verniman.blogspot.com/2006/12/fixture-{i}.html', 'session_date': stamp, 'title': stamp,
                      'html': {'path': relative, 'bytes': len(compressed), 'sha256': hashlib.sha256(compressed).hexdigest(), 'uncompressed_sha256': hashlib.sha256(raw).hexdigest()},
                      'images': [], 'date_warnings': [], 'capture_kind': 'live', 'date_method': 'explicit_fixture_date'})
    (stage / 'capture-manifest.json').write_text(json.dumps({'run_id': 'fixture2022', 'seed_url': posts[0]['url'], 'start_date': '2022-01-01', 'end_date': '2022-12-31', 'posts': posts}))
    result = builder.build(stage)
    assert result['status'] == 'passed' and result['calendar_days'] == 365
    archive = stage / 'archive'
    rows = list(csv.DictReader((archive / 'coverage.csv').open()))
    assert len(rows) == 365 and rows[0]['date'] == '2022-12-31' and rows[-1]['date'] == '2022-01-01'
    assert [row['date'] for row in rows] == sorted([row['date'] for row in rows], reverse=True)
    assert rows[0]['post_count'] == '0' and rows[0]['status'] == 'no_dated_post_observed_weekend'
    assert rows[1]['date'] == '2022-12-30' and rows[1]['post_count'] == '1'
    assert all(row['post_count'] == '0' for row in rows if row['date'] < '2022-05-16')
    inventory = json.loads((archive / 'archive-manifest.json').read_text())
    indexes = {entry['path']: entry['dates'] for entry in inventory['indexes']}
    assert len(indexes['2022/12/index.html']) == 31 and len(indexes['2022/02/index.html']) == 28
    assert '<title>Daily Map · 2022 · Verniman Daily Map</title>' in (archive / 'index.html').read_text()
    assert not (archive / '2021').exists()
    metrics = json.loads((archive / 'metrics.json').read_text())
    assert metrics['map_records'] == 2 and metrics['unassigned_or_boundary_records'] == 1
print(json.dumps({'status': 'passed', 'calendar_days': 365, 'year_end_weekend_gaps': ['2022-12-31'], 'latest_fixture_map': '2022-12-30', 'early_source_gap_before': '2022-05-16', 'lower_boundary_excluded': '2021-12-31', 'february_days': 28}))
