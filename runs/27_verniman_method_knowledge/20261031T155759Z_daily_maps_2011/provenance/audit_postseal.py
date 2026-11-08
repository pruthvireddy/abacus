#!/usr/bin/env python3
"""Independent read-only integrity/navigation audit after the 2011 seal."""
import argparse
import csv
import gzip
import hashlib
import html
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path('/Users/pruthvi/Documents/projects/abacus')
RUN_ID = '20261031T155759Z_daily_maps_2011'
STUDY = '27_verniman_method_knowledge'
RUN = ROOT / 'runs' / STUDY / RUN_ID
STAGE = ROOT / 'work' / STUDY / RUN_ID
MD = re.compile(r'!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked(root, rec):
    p = (root / rec['path']).resolve()
    assert p.is_relative_to(ROOT), ('path outside workspace', p)
    raw = p.read_bytes()
    assert len(raw) == rec['bytes'] and sha(raw) == rec['sha256'], ('identity', p)
    return raw


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(v for k, v in attrs if k in {'href', 'src'} and v)


def local_links(files):
    counts = Counter()
    for p in files:
        if p.suffix == '.md':
            links = [m[1].strip('<>') for m in MD.finditer(p.read_text())]
            kind = 'markdown_links'
        elif p.suffix == '.html':
            parsed = Links()
            parsed.feed(p.read_text())
            links, kind = parsed.links, 'html_links'
        else:
            continue
        for link in links:
            parts = urlsplit(html.unescape(link))
            if parts.scheme or parts.netloc or not parts.path:
                continue
            target = (p.parent / unquote(parts.path)).resolve()
            assert target.is_relative_to(ROOT) and target.is_file(), ('missing local link', p, link)
            counts[kind] += 1
    return dict(counts)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--expected-manifest-sha256',required=True);ap.add_argument('--expected-artifacts',type=int,required=True);ap.add_argument('--expected-artifact-bytes',type=int,required=True);ap.add_argument('--expected-portable-links',type=int,required=True);ap.add_argument('--expected-reader-files',type=int,required=True);ap.add_argument('--expected-reader-html-links',type=int,required=True);ap.add_argument('--expected-reader-markdown-links',type=int,required=True);args=ap.parse_args()
    manifest_raw = (RUN / 'manifest.json').read_bytes()
    assert sha(manifest_raw)==args.expected_manifest_sha256, 'sealed manifest differs from explicit pin'
    manifest = json.loads(manifest_raw)
    artifacts = manifest['artifacts']
    listed = {r['path'] for r in artifacts}
    assert len(listed) == len(artifacts) == args.expected_artifacts
    actual = {p.relative_to(RUN).as_posix() for p in RUN.rglob('*') if p.is_file()} - {'manifest.json'}
    assert actual == listed, ('sealed artifact set', actual ^ listed)
    for record in artifacts:
        checked(RUN, record)
    assert sum(r['bytes'] for r in artifacts) == args.expected_artifact_bytes
    for rec in manifest['prepared_inputs']:
        checked(STAGE, rec)
    assert (RUN/'capture-manifest.json').read_bytes() == (STAGE/'capture-manifest.json').read_bytes()
    assert (RUN/'payload-inventory.json').read_bytes() == (STAGE/'archive/archive-manifest.json').read_bytes()
    capture = json.loads((RUN/'capture-manifest.json').read_bytes())
    assert capture['posts'] == [] and capture['seed_url'] is None
    empty_review = capture['empty_daily_selection_review']
    assert empty_review['status'] == 'reviewed_no_in_scope_daily_plans'
    assert checked(STAGE, empty_review['retained_review']) == (STAGE/'archive/source-review.json').read_bytes()
    assert 'No in-scope daily plans could be established' in (STAGE/'archive/index.html').read_text()
    assert 'source-review.json' in (STAGE/'archive/index.html').read_text()
    assert not list((STAGE/'archive').rglob('*.png')) and not list((STAGE/'archive').rglob('*.jpg'))
    assert not list((STAGE/'archive').rglob('*.jpeg')) and not list((STAGE/'archive').rglob('*.gif')) and not list((STAGE/'archive').rglob('*.webp'))
    metrics = json.loads((STAGE/'archive/metrics.json').read_text())
    assert metrics['calendar_days'] == 365 and metrics['map_records'] == 0 and metrics['days_with_maps'] == 0
    assert metrics['image_references'] == 0 and metrics['unique_image_files'] == 0 and metrics['retained_image_references'] == 0
    assert metrics['weekday_gaps'] == 260 and metrics['weekend_gaps'] == 105
    rows=list(csv.DictReader((STAGE/'archive/coverage.csv').open()))
    dates=[r['date'] for r in rows]
    assert len(rows)==365 and dates==sorted(dates,reverse=True) and dates[0]=='2011-12-31' and dates[-1]=='2011-01-01'
    assert all(r['post_count']=='0' and r['image_count']=='0' for r in rows)
    assert '2011-02-29' not in dates and not (STAGE/'archive/2011/02/29').exists()
    assert (STAGE/'archive/2011/02/index.html').read_text().count('<tr data-date=')==28
    precheck=json.loads(checked(ROOT,empty_review['independent_selection_precheck']))
    assert precheck['status']=='passed' and precheck['selected_source_ids']==[] and precheck['selected_records']==0
    assert precheck['successfully_captured_sources']==70 and precheck['failed_indexed_locators']==0 and precheck['actual_post_body_instances']==73
    assert precheck['raw_source_formats']=={'archived_html':17,'archived_atom_feed':50,'current_html':3}
    assert precheck['excluded_archived_context_records']==67 and precheck['excluded_current_context_records']==3
    assert len(precheck['exact_later_year_full_body_matches'])==3 and precheck['raw_image_references']==131 and precheck['unique_retained_raw_images']==58
    assert precheck['retained_raw_image_references']==81 and precheck['successful_raw_image_pairs']==59
    assert precheck['raw_missing_images']==50 and precheck['missing_tracking_pixel_references']==50 and precheck['missing_authored_chart_references']==0
    assert precheck['unique_missing_image_urls']==38 and precheck['raw_inline_fallbacks']==0
    raw_record=capture['source_archive_capture_manifest']
    assert raw_record['sha256']=='24cd449faeee26a091b9e06de07a6c40ef47714a2c40dc183d7d58e3e0696c82'
    raw_recovery=json.loads(checked(ROOT,raw_record))
    assert len(raw_recovery['posts'])==70 and not any(p.get('capture_failed') for p in raw_recovery['posts'])
    assert len(raw_recovery['files'])==311
    for record in raw_recovery['files']:checked(ROOT,record)

    source_records = set()

    def walk(obj):
        if isinstance(obj, list):
            for x in obj:
                walk(x)
        elif isinstance(obj, dict):
            if isinstance(obj.get('path'), str) and isinstance(obj.get('bytes'), int) and isinstance(obj.get('sha256'), str):
                key = (obj['path'], obj['bytes'], obj['sha256'])
                if key not in source_records:
                    base = ROOT if obj['path'].startswith(('work/', 'data/', 'runs/')) else STAGE
                    checked(base, obj)
                    source_records.add(key)
            for x in obj.values():
                walk(x)

    walk(capture)
    inventory = json.loads((RUN/'payload-inventory.json').read_bytes())
    reader = STAGE/'archive'
    assert len(inventory['files']) == args.expected_reader_files
    assert {r['path'] for r in inventory['files']} == {p.relative_to(reader).as_posix() for p in reader.rglob('*') if p.is_file()}-{'archive-manifest.json'}
    for record in inventory['files']:
        checked(reader, record)
    portable = local_links([RUN/r['path'] for r in artifacts])
    assert sum(portable.values()) == args.expected_portable_links, portable
    reader_links = local_links([reader/r['path'] for r in inventory['files']])
    assert reader_links == {'html_links':args.expected_reader_html_links,'markdown_links':args.expected_reader_markdown_links}, reader_links

    overview = ROOT/'studies'/STUDY
    nav = overview/'knowledge-base/daily-map/README.md'
    text = nav.read_text()
    assert '5,782 calendar records across sixteen annual snapshots' in text
    assert '2011 snapshot' in text
    rows = [line for line in text.splitlines() if re.match(r'\| 20\d\d,', line)]
    assert len(rows) == 16
    year_counts = []
    for row, expected_year in zip(rows, range(2026, 2010, -1)):
        cells = [s.strip() for s in row.split('|')[1:-1]]
        assert cells[0].startswith(str(expected_year)+','), row
        links = [m[1] for m in MD.finditer(cells[-1])]
        assert len(links) == 2
        reader_index = (nav.parent/links[0]).resolve()
        dated_index = (nav.parent/links[1]).resolve()
        assert reader_index.name == 'index.html' and reader_index.is_file()
        assert dated_index.name == 'README.md' and dated_index.is_file()
        annual_metrics = json.loads((reader_index.parent/'metrics.json').read_text())
        assert annual_metrics['map_records'] == int(cells[1]) and annual_metrics['days_with_maps'] == int(cells[2])
        annual_run = ROOT/'runs'/STUDY/annual_metrics['run_id']
        assert dated_index.is_relative_to(annual_run)
        assert (annual_run/'payload-inventory.json').read_bytes() == (reader_index.parent/'archive-manifest.json').read_bytes()
        year_counts.append({'year':expected_year,'calendar_days':annual_metrics['calendar_days'],'dated_maps':annual_metrics['map_records'],'dated_days':annual_metrics['days_with_maps']})
    assert sum(y['calendar_days'] for y in year_counts) == 5782
    maintained_files = [overview/'README.md', overview/'knowledge-base/README.md', nav]
    maintained_links = local_links(maintained_files)
    study_raw = (overview/'study.json').read_bytes()
    study = json.loads(study_raw)
    assert study['reference_run'] == '20261023T174000Z_review27'
    assert '5,782' in study['data_summary'] and '2011' in study['data_summary']
    assert '20261023T174000Z_review27/knowledge-base/README.md' in (overview/'knowledge-base/README.md').read_text()
    result = {'status':'passed','scope':'Read-only postseal byte, inventory and local navigation checks; no historical completeness or method validity inferred.',
              'empty_daily_selection_verified':True,'source_review_notice_present':True,'selected_reader_images':0,'calendar_gap_days':365,'leap_day_record_present':False,'february_rows':28,'failed_indexed_locators':0,'successful_raw_context_records':70,'archived_context_records':67,'current_only_context_records':3,'raw_image_references':131,'retained_raw_image_references':81,'unique_retained_raw_images':58,'missing_tracking_pixel_references':50,'missing_authored_chart_references':0,'method_reference_unchanged':True,
              'run':RUN.relative_to(ROOT).as_posix(),'manifest_sha256':sha(manifest_raw),'sealed_artifacts':len(artifacts),'sealed_artifact_bytes':sum(r['bytes'] for r in artifacts),
              'capture_inventory_equal_sealed':True,'reader_inventory_equal_sealed':True,'current_capture_referenced_objects_checked':len(source_records),
              'reader_files_checked':len(inventory['files']),'reader_bytes_including_inventory':sum(r['bytes'] for r in inventory['files'])+(reader/'archive-manifest.json').stat().st_size,
              'portable_links':portable,'portable_links_total':sum(portable.values()),'reader_links':reader_links,'maintained_navigation_files':len(maintained_files),'maintained_navigation_links':maintained_links,
              'annual_snapshots':len(rows),'scoped_calendar_records':sum(y['calendar_days'] for y in year_counts),'annual_counts':year_counts,'selected_method_run':study['reference_run'],
              'maintained_file_identities':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in maintained_files+[overview/'study.json']]}
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
