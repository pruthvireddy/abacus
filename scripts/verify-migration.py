#!/usr/bin/env python3
"""Verify preserved copies and optionally original files and published VWAP parts."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def verify(root: Path, original: bool, publication: Path | None) -> dict:
    inventory = json.loads((root / 'docs/migration/source-files.json').read_text())
    failures = []
    preserved = sources = parts = 0
    seen = set()
    for item in inventory['files']:
        dest = item['destination']
        # Active package code is deliberately adapted to the new layout.
        if not dest.startswith('packages/'):
            path = root / dest
            if not path.is_file() or digest(path) != item['sha256']:
                failures.append({'path': dest, 'reason': 'preserved copy missing or changed'})
            preserved += 1
        if original and item['source'] not in seen:
            seen.add(item['source'])
            path = Path(item['source'])
            if not path.is_file() or digest(path) != item['sha256']:
                failures.append({'path': str(path), 'reason': 'original missing or changed'})
            sources += 1
    if publication:
        for timeframe in ['2m', '5m']:
            m = json.loads((root / f'catalog/datasets/session_anchored_vwap_{timeframe}_v1.json').read_text())
            for item in m['output_files']:
                p = publication / item['path']
                if not p.is_file() or p.stat().st_size != item['bytes'] or digest(p) != item['sha256']:
                    failures.append({'path': str(p), 'reason': 'published partition identity mismatch'})
                parts += 1
        release = json.loads((root / 'catalog/datasets/session_anchored_vwap__1.0.0.release.json').read_text())
        item = release['audit']
        p = publication / item['path']
        if not p.is_file() or digest(p) != item['sha256']:
            failures.append({'path': str(p), 'reason': 'published audit identity mismatch'})
    return {'checked_at': datetime.now(timezone.utc).isoformat(), 'status': 'pass' if not failures else 'fail',
            'preserved_copies_checked': preserved, 'original_files_checked': sources,
            'published_partitions_checked': parts, 'publication_root': str(publication) if publication else None,
            'failures': failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-sources', action='store_true')
    parser.add_argument('--publication-root', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = verify(root, args.verify_sources, args.publication_root)
    body = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body)
    print(body, end='')
    return 0 if report['status'] == 'pass' else 1

if __name__ == '__main__':
    raise SystemExit(main())
