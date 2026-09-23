#!/usr/bin/env python3
"""Build a deterministic, offline research library from metadata and saved runs."""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote


def natural_key(value: str) -> list:
    return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', value)]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def build(root: Path) -> dict[str, str]:
    def url(path: str) -> str:
        target = (root / path).resolve()
        if not target.is_relative_to(root) or not target.exists():
            raise ValueError(f'Index target missing or outside repository: {path}')
        return '../' + quote(path, safe='/')

    def link(path: str, label: str) -> str:
        return f'<a href="{escape(url(path), quote=True)}">{escape(label)}</a>'

    def mdlink(path: str, label: str) -> str:
        return f'[{label}]({url(path)})'

    studies = []
    for file in sorted((root / 'studies').glob('*/study.json')):
        study = load_json(file)
        if study['study_id'] != file.parent.name:
            raise ValueError(f'Study ID differs from directory: {file}')
        runs = sorted((root / 'runs' / study['study_id']).glob('*'), key=lambda p: natural_key(p.name))
        study['runs'] = [p for p in runs if p.is_dir()]
        reference = study.get('reference_run')
        if reference is not None and reference not in [p.name for p in study['runs']]:
            raise ValueError(f'Reference run does not exist: {study["study_id"]}/{reference}')
        studies.append(study)
    strategies = load_json(root / 'strategies/index.json')['strategies']
    quality = sorted((root / 'reports/quality').glob('*.md'))
    exports = sorted(p for p in (root / 'legacy/sahadeva/presentation-exports').iterdir() if p.is_file())
    run_count = sum(len(s['runs']) for s in studies)
    cards, featured, markdown = [], [], [
        '# Abacus research library', '',
        'Saved evidence, study plans, and current strategy interpretation in one place.', '',
        f'{len(studies)} studies · {run_count} saved runs · {len(strategies)} strategy cards.', '',
        '**Historical results were imported without recalculation or a new review. Latest means natural run-ID ordering; no recommendation or reference selection is inferred.**', '',
    ]

    def artifacts(run: Path) -> list[tuple[str, str]]:
        labels = [('report.html', 'Report'), ('summary.md', 'Summary'), ('report.md', 'Markdown'),
                  ('leg_duration_report.html', 'Leg duration'), ('methodology.md', 'Methods'),
                  ('data_quality.md', 'Data quality'), ('manifest.json', 'Manifest'),
                  ('run_manifest.json', 'Original manifest'), ('import_manifest.json', 'Import record'),
                  ('metrics.json', 'Metrics'), ('advice.md', 'Advice')]
        return [(p, label) for p, label in labels if (run / p).is_file()]

    for study in studies:
        sid, title = study['study_id'], study['title']
        base = f'studies/{sid}'
        markdown.extend([f'## {title}', '', f'`{sid}` · {study["status"]} · {", ".join(study["products"])}', '', study['summary'], '', study['evidence_status'], '', mdlink(f'{base}/README.md', 'Study overview') + ' · ' + mdlink(f'{base}/study.json', 'Metadata'), ''])
        if study['status'] == 'planned':
            plan_links = ' · '.join(mdlink(f'{base}/{p}', l) for p, l in [('plan.md', 'Plan'), ('study.yaml', 'Settings'), ('inputs.lock.json', 'Pinned inputs'), ('notes.md', 'Decisions')])
            markdown.extend([plan_links, '', 'No computed strategy outcomes or completed runs.', ''])
            study_strategies = [s for s in strategies if sid in s['study_ids']]
            candidate_links = ''.join(f'<li>{link(s["path"], s["title"])}</li>' for s in study_strategies)
            featured.append(f'''<article class="featured"><div><span class="badge planned">Planned study</span><h2>{escape(title)}</h2><p>{escape(study['summary'])}</p><p class="scope">{escape(study['data_summary'])}</p><p class="muted">{escape(study['evidence_status'])}</p><div class="links">{link(base + '/plan.md', 'Read the research plan')}{link(base + '/study.yaml', 'Proposed settings')}{link(base + '/inputs.lock.json', 'Pinned inputs')}{link(base + '/notes.md', 'Decisions')}</div></div><div class="featured-aside"><div class="eyebrow">Candidate strategies</div><ol>{candidate_links}</ol></div></article>''')
            continue
        run_rows = []
        for i, run in reversed(list(enumerate(study['runs']))):
            rel = run.relative_to(root).as_posix()
            latest = i == len(study['runs']) - 1
            is_reference = study.get('reference_run') == run.name
            label = (' · latest by ID' if latest else '') + (' · selected reference' if is_reference else '')
            markdown.append(f'- **{run.name}{label}** — ' + ' · '.join(mdlink(f'{rel}/{p}', name) for p, name in artifacts(run)))
            files = [(p.relative_to(root).as_posix(), f'{p.parent.name}/{p.name}') for folder in ('tables', 'figures') for p in sorted((run / folder).glob('*')) if p.is_file()]
            file_html = ''.join(f'<li>{link(path, name)}</li>' for path, name in files)
            file_details = f'<details><summary>{len(files)} tables and figures</summary><ul class="file-list">{file_html}</ul></details>' if files else ''
            run_rows.append(f'<div class="run"><div class="run-head"><span>{escape(run.name)}</span>{"<span class=latest>Latest by ID</span>" if latest else ""}{"<span class=latest>Selected reference</span>" if is_reference else ""}</div><div class="links">' + ''.join(link(f'{rel}/{p}', name) for p, name in artifacts(run)) + f'</div>{file_details}</div>')
        markdown.append('')
        archived = study.get('archived_code_path')
        if archived:
            markdown.extend([mdlink(f'{archived}/README.md', 'Archived analysis and original commands'), ''])
        latest_link = ''
        if study['runs']:
            latest_run = study['runs'][-1]
            main_artifacts = artifacts(latest_run)
            if main_artifacts:
                latest_path = latest_run.relative_to(root).as_posix() + '/' + main_artifacts[0][0]
                latest_link = link(latest_path, 'Latest report' if main_artifacts[0][0].endswith('.html') else 'Latest summary')
        chips = ''.join(f'<span class="pill">{escape(p)}</span>' for p in study['products'])
        status_label = 'Historical import' if study['status'] == 'historical_import' else study['status'].replace('_', ' ').title()
        cards.append(f'''<article class="card"><div class="meta-line"><span class="id">{escape(sid)}</span><span class="badge">{escape(status_label)}</span></div><h3>{escape(title)}</h3><p class="description">{escape(study['summary'])}</p><div class="pill-row">{chips}<span class="pill">{escape(study['topic'])}</span><span class="pill">{len(study['runs'])} saved runs</span></div><p class="scope">{escape(study['evidence_status'])}</p><div class="links">{latest_link}{link(base + '/README.md', 'Study overview')}{link(archived + '/README.md', 'Archived analysis') if archived else ''}</div><details><summary>Browse saved runs and evidence</summary>{''.join(run_rows)}</details></article>''')

    strategy_cards = []
    markdown.extend(['## Strategy cards', '', 'Cards record the current evidence status of each enduring idea. Follow their run links before interpreting any finding.', ''])
    for i, strategy in enumerate(strategies, 1):
        markdown.append(f'- {mdlink(strategy["path"], strategy["title"])} — {strategy["status"]}')
        strategy_cards.append(f'<article class="card strategy"><div class="num">{i:02d}</div><h3>{link(strategy["path"], strategy["title"])}</h3><p>{escape(strategy["summary"])}</p><span class="badge planned">{escape(strategy["status"])}</span></article>')
    markdown.extend(['', '## Data publications and quality', '',
                     mdlink('catalog/datasets/session_anchored_vwap__1.0.0.release.json', 'Session-Anchored VWAP 1.0.0 release') + ' · ' + mdlink('studies/05_session_vwap/inputs.lock.json', 'Pinned input identities'), ''])
    quality_html = []
    for path in quality:
        rel = path.relative_to(root).as_posix()
        markdown.append('- ' + mdlink(rel, path.stem))
        quality_html.append('<li>' + link(rel, path.stem.replace('__', ' · ').replace('_', ' ')) + '</li>')
    markdown.extend(['', '## Historical presentation exports', '', 'Posters and workbook preserved from the old presentation folder. Exact source-run attribution remains unresolved; no current recommendation is implied.', ''])
    export_html = []
    for path in exports:
        rel = path.relative_to(root).as_posix()
        markdown.append('- ' + mdlink(rel, path.name))
        export_html.append('<li>' + link(rel, path.name) + '</li>')
    markdown.extend(['', '## Working with the library', '',
                     mdlink('templates/README.md', 'Artifact conventions') + ' · ' + mdlink('studies/README.md', 'Study registration') + ' · ' + mdlink('strategies/README.md', 'Strategy evidence cards'), '',
                     'Rebuild: `python scripts/build-research-index.py`. Check freshness: `python scripts/build-research-index.py --check`.', '',
                     'Generated from saved metadata and files. No statistics are recalculated.', ''])
    css = (root / 'templates/library.css').read_text(encoding='utf-8')
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Abacus research library: saved studies, evidence, VWAP strategy proposals, and data quality records."><title>Abacus — Research library</title><style>{css}</style></head>
<body><header><div class="brand"><a href="index.html">ABACUS / RESEARCH</a><nav aria-label="Library sections"><a href="#studies">Studies</a><a href="#strategies">Strategies</a><a href="#resources">Data &amp; exports</a></nav></div><div class="eyebrow">A durable record of market research</div><h1>From a question<br>to saved evidence.</h1><p class="lede">Explore the studies, inspect the original statistics, and follow each strategy idea as evidence accumulates.</p><div class="counters"><div><strong>{len(studies):02d}</strong><span>registered studies</span></div><div><strong>{run_count:02d}</strong><span>saved runs</span></div><div><strong>{len(strategies):02d}</strong><span>strategy cards</span></div></div></header>
<main><section aria-label="Planned research">{''.join(featured)}</section><section id="studies"><div class="section-head"><h2>Research archive</h2><p>Original results, tables, figures, and provenance. Open a study to browse every saved run.</p></div><div class="note">Historical results were imported without recalculation or a new review. “Latest” reflects natural run-ID ordering. Recency alone does not select a reference run or establish a strategy recommendation.</div><div class="grid">{''.join(cards)}</div></section><hr class="rule"><section id="strategies"><div class="section-head"><h2>Ideas under investigation</h2><p>Each card preserves a hypothesis, proposed statistics, and the current evidence status. The initial VWAP candidates are proposed, with no computed outcomes yet.</p></div><div class="strategy-grid">{''.join(strategy_cards)}</div></section><hr class="rule"><section id="resources"><div class="section-head"><h2>Data &amp; supporting artifacts</h2><p>Publication records and historical presentation exports stay connected to the research library.</p></div><div class="resources"><article class="card"><div class="eyebrow">Bhishma / publications</div><h3>Data quality and contracts</h3><p class="muted">Published data remains at the configured storage root. The repository preserves catalog records and quality reports.</p><div class="links">{link('catalog/datasets/session_anchored_vwap__1.0.0.release.json', 'VWAP 1.0.0 release')}{link('studies/05_session_vwap/inputs.lock.json', 'Pinned input hashes')}</div><ul class="resource-list">{''.join(quality_html)}</ul></article><article class="card"><div class="eyebrow">Sahadeva / presentation archive</div><h3>Posters and workbook</h3><p class="muted">Original exports preserved for reference. Exact source-run attribution remains unresolved.</p><div class="export-banner"><p>{link('legacy/sahadeva/presentation-exports/RangeXV_All_7_Posters.pdf', 'Open the poster collection')}<br>{link('legacy/sahadeva/presentation-exports/RangeXV_Stats_First_Draft.xlsx', 'Open the statistics workbook')}</p></div><details><summary>Browse all {len(exports)} presentation files</summary><ul class="resource-list">{''.join(export_html)}</ul></details></article></div></section></main>
<footer><span>ABACUS · Offline research library · Generated from saved metadata</span><span>{link('templates/README.md', 'Artifact conventions')} · <a href="index.md">Markdown index</a></span></footer></body></html>
'''
    return {'reports/index.html': html, 'reports/index.md': '\n'.join(markdown)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1], help='Repository root')
    parser.add_argument('--check', action='store_true', help='Fail if generated index files are out of date; do not write')
    args = parser.parse_args()
    root = args.root.resolve()
    outputs = build(root)
    stale = []
    for name, content in outputs.items():
        path = root / name
        if args.check:
            if not path.is_file() or path.read_text(encoding='utf-8') != content:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
    if stale:
        print('Out of date: ' + ', '.join(stale))
        return 1
    print('Research library is current.' if args.check else 'Built reports/index.html and reports/index.md.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
