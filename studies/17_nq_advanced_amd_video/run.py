#!/usr/bin/env python3
"""Package or verify this qualitative review; never execute a market backtest."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
STUDY = "17_nq_advanced_amd_video"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def inline(text):
    text = escape(text)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<a href="\2"><img src="\2" alt="\1" loading="lazy"></a>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', text)


def render(markdown):
    """Render the small, controlled Markdown subset used in this report."""
    blocks, paragraph, table, items = [], [], [], []
    def flush():
        if paragraph:
            blocks.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
        if table:
            cells = [r.strip('|').split('|') for r in table]
            head = '<tr>' + ''.join('<th>' + inline(c.strip()) + '</th>' for c in cells[0]) + '</tr>'
            body = ''.join('<tr>' + ''.join('<td>' + inline(c.strip()) + '</td>' for c in row) + '</tr>' for row in cells[2:])
            blocks.append('<div class="table-scroll"><table><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>')
            table.clear()
        if items:
            blocks.append('<ol>' + ''.join('<li>' + inline(x) + '</li>' for x in items) + '</ol>')
            items.clear()
    for line in markdown.splitlines():
        if not line.strip():
            flush()
        elif line.startswith('#'):
            flush()
            level = len(line) - len(line.lstrip('#'))
            blocks.append(f'<h{level}>' + inline(line[level:].strip()) + f'</h{level}>')
        elif line.startswith('|'):
            table.append(line)
        elif re.match(r'^\d+\. ', line):
            items.append(re.sub(r'^\d+\. ', '', line))
        elif items and line.startswith('   '):
            items[-1] += ' ' + line.strip()
        else:
            paragraph.append(line)
    flush()
    css = '''body{margin:0;background:#f6f5f0;color:#202d33;font:17px/1.65 system-ui,sans-serif}
main{max-width:1040px;margin:auto;padding:48px 28px 80px}h1{font-size:42px;line-height:1.12;max-width:900px}
h2{font-size:26px;margin-top:54px;padding-top:18px;border-top:1px solid #cbd4d2}a{color:#176d69;text-underline-offset:3px}
p{max-width:900px}img{display:block;width:100%;height:auto;border:1px solid #d7ddda;margin:30px 0 12px}
table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.5}th,td{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #ccd7d4}th{background:#e1eeeb}
.table-scroll{overflow-x:auto}code{font-size:.9em;background:#e7ece8;padding:2px 4px}.label{font:12px/1.4 system-ui;letter-spacing:.14em;text-transform:uppercase;color:#426663}
@media(max-width:650px){main{padding:24px 18px}h1{font-size:32px}body{font-size:16px}table{min-width:610px}}
@media print{body{background:white}main{padding:0}h2{break-after:avoid}img,tr{break-inside:avoid}}'''
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NQ advanced AMD source study</title><style>' + css + '</style></head><body><main><div class="label">Abacus / Sahadeva / Qualitative source review</div>' + '\n'.join(blocks) + '</main></body></html>\n'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in ('href', 'src'))


def verify(bundle, publication_root=None, require_manifest=True):
    manifest_path = bundle / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if require_manifest and manifest is None:
        raise ValueError('Missing manifest')
    if manifest:
        actual = {p.relative_to(bundle).as_posix() for p in bundle.rglob('*') if p.is_file() and p != manifest_path}
        assert actual == set(manifest['artifacts']), 'Artifact inventory mismatch'
        for name, info in manifest['artifacts'].items():
            assert sha(bundle / name) == info['sha256'], name
    lock = json.loads((bundle / 'inputs.lock.json').read_text())
    publication_root = Path(publication_root or os.environ.get('ABACUS_PUBLICATION_ROOT', ROOT)).resolve()
    source = publication_root / lock['sources'][0]['transcript']['path']
    assert sha(source) == lock['sources'][0]['transcript']['sha256'], 'Transcript hash mismatch'
    rows = list(csv.DictReader((bundle / 'tables/charts.csv').open()))
    assert len(rows) == 14 and len({r['file'] for r in rows}) == 14
    for row in rows:
        image_path = bundle / row['file']
        data = image_path.read_bytes()
        assert data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9'), str(image_path)
        assert sha(image_path) == row['sha256'], str(image_path)
        assert 0 <= int(row['seconds']) < 1631.401
    segments = list(csv.DictReader((bundle / 'tables/coverage.csv').open()))
    assert float(segments[0]['start_seconds']) == 0
    assert float(segments[-1]['end_seconds']) == 1631.401
    for a, b in zip(segments, segments[1:]):
        assert float(a['end_seconds']) == float(b['start_seconds']), 'Coverage gap/overlap'
    for filename in ('report.html',):
        parser = Links()
        parser.feed((bundle / filename).read_text())
        for href in parser.links:
            u = urlsplit(href)
            if not u.scheme and not u.netloc:
                target = (bundle / unquote(u.path)).resolve()
                assert target.is_relative_to(bundle.resolve()), href
                # Manifest is written after preseal verification.
                if target.name != 'manifest.json' or require_manifest:
                    assert target.is_file(), href
    markdown = (bundle / 'report.md').read_text()
    assert len(re.findall(r'!\[', markdown)) == 14
    result = {'artifact_hashes': 'passed' if manifest else 'pending_manifest',
              'transcript_hash': 'passed', 'image_signatures_and_hashes': 'passed',
              'report_local_links': 'passed', 'continuous_caption_review_coverage': 'passed',
              'chart_count': len(rows), 'coverage_segment_count': len(segments),
              'market_backtest': 'not_run'}
    print(json.dumps(result, indent=2))
    return result


def assemble(args):
    source, destination = args.source.resolve(), args.bundle.resolve()
    if destination.exists():
        raise ValueError('Refusing to overwrite an existing bundle')
    destination.mkdir(parents=True)
    for name in ('figures', 'tables'):
        shutil.copytree(source / name, destination / name)
    for name in ('report.md', 'advice.md', 'source.json', 'config.json', 'capture-log.json'):
        shutil.copy2(source / name, destination / name)
    study_path = ROOT / 'studies' / STUDY
    shutil.copy2(study_path / 'inputs.lock.json', destination / 'inputs.lock.json')
    (destination / 'report.html').write_text(render((destination / 'report.md').read_text()))
    provenance = destination / 'provenance'
    shutil.copytree(study_path, provenance / 'study-source', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(source / 'acquisition.md', provenance / 'acquisition.md')
    shutil.copy2(ROOT / 'uv.lock', provenance / 'uv.lock')
    dump(provenance / 'environment.json', {'python':sys.version, 'platform':sys.platform,
        'runtime_dependencies':'Python standard library only', 'workspace_uv_lock_sha256':sha(ROOT / 'uv.lock'),
        'note':'Workspace lock preserved for provenance; no workspace dependency changes.'})
    for command, name in [(['git','rev-parse','HEAD'], 'git-revision.txt'),
                          (['git','status','--short'], 'git-status-at-packaging.txt')]:
        (provenance / name).write_text(subprocess.check_output(command, cwd=ROOT, text=True))
    segments = list(csv.DictReader((destination / 'tables/coverage.csv').open()))
    claims = list(csv.DictReader((destination / 'tables/claims.csv').open()))
    lock = json.loads((destination / 'inputs.lock.json').read_text())
    caption = Path(args.publication_root).resolve() / lock['sources'][0]['transcript']['path']
    dump(destination / 'metrics.json', {'review_type':'qualitative_source_review',
        'metrics':[
            {'id':'source_video_count','value':1,'unit':'video'},
            {'id':'source_duration','value':1631.401,'unit':'seconds'},
            {'id':'inspected_chart_count','value':14,'unit':'screenshot'},
            {'id':'coverage_segments','value':len(segments),'unit':'review interval'},
            {'id':'claim_ledger_rows','value':len(claims),'unit':'claim'},
            {'id':'caption_segments','value':len(re.findall(r'^\[\d+:\d+\]',caption.read_text(),re.M)),'unit':'automatic caption segment'}],
        'trading_outcomes':{'status':'not_computed','sample_size':None,'net_expectancy':None,'win_rate':None},
        'uncertainty':'Review counts are inventory totals, not statistical estimates of trading performance.'})
    checks = verify(destination, args.publication_root, require_manifest=False)
    dump(destination / 'checks.json', checks)
    print('Staged at ' + str(destination))


def seal(args):
    stage, destination = args.bundle.resolve(), args.destination.resolve()
    if destination.exists() or (stage / 'manifest.json').exists():
        raise ValueError('Refusing to replace a sealed bundle')
    checks = verify(stage, args.publication_root, require_manifest=False)
    checks['visual_review'] = 'All 14 chart captures inspected; HTML layout preview blocked by browser file-URL policy. Static HTML checks recorded in provenance/visual-qa.json.'
    checks['artifact_hashes'] = 'generated_and_verified_at_seal'
    dump(stage / 'checks.json', checks)
    artifacts = {p.relative_to(stage).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
                 for p in sorted(stage.rglob('*')) if p.is_file()}
    manifest = {'schema_version':'qualitative-review-bundle-1', 'study_id':STUDY,
        'run_id':destination.name, 'sealed_at_utc':datetime.now(timezone.utc).isoformat(),
        'review_type':'qualitative_source_review', 'protocol_version':'1.0.0',
        'code_revision':(stage/'provenance/git-revision.txt').read_text().strip(),
        'dirty_source_snapshot':'provenance/study-source/',
        'environment_lock':'provenance/uv.lock',
        'exact_seal_command':shlex.join([sys.executable, *sys.argv]),
        'declared_seal_command':args.record_command,
        'acquisition_and_assembly_commands':'provenance/acquisition.md',
        'config':'config.json','inputs':'inputs.lock.json','checks':'checks.json',
        'limitations':['One selected week; no empirical validation','English automatic captions may contain errors',
                      'Original private-message timestamps unverified','Exact trade fills and profitability unverified'],
        'artifacts':artifacts}
    dump(stage / 'manifest.json', manifest)
    verify(stage, args.publication_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(stage, destination)
    verify(destination, args.publication_root)
    print('Sealed new bundle at ' + str(destination))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('assemble', 'verify', 'seal'):
        p = sub.add_parser(action)
        p.add_argument('--bundle', type=Path, required=True)
        p.add_argument('--publication-root', default=os.environ.get('ABACUS_PUBLICATION_ROOT', str(ROOT)),
                       help='Resolved publication root from Abacus paths configuration or environment')
        if action == 'assemble':
            p.add_argument('--source', type=Path, required=True)
        if action == 'seal':
            p.add_argument('--destination', type=Path, required=True)
            p.add_argument('--record-command', required=True)
    args = parser.parse_args()
    if args.action == 'assemble':
        assemble(args)
    elif args.action == 'seal':
        seal(args)
    else:
        verify(args.bundle.resolve(), args.publication_root)


if __name__ == '__main__':
    main()
