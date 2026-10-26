#!/usr/bin/env python3
"""Compact a staged publication's JSON whitespace without changing its content.

Presentation packaging only; no research imports, estimates or interpretation.
The original rendered source and this producer are retained before writing.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package(stage):
    stage = Path(stage).resolve()
    if 'runs' in stage.parts or not (stage / 'execution-complete.json').is_file():
        raise ValueError('Only an explicitly staged completed execution can be packaged')
    receipt = stage / 'publication-packaging.json'
    if receipt.exists():
        raise FileExistsError('Packaging is single-use; retain existing presentation evidence')
    path = stage / 'publication.json'
    original = path.read_bytes()
    report = json.loads(original)
    compact = (json.dumps(report, separators=(',', ':'), sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode()
    if json.loads(compact) != report:
        raise ValueError('Serialization changed JSON content')
    retained = stage / 'provenance' / 'presentation-packaging'
    retained.mkdir(parents=True)
    (retained / 'original-publication.json').write_bytes(original)
    shutil.copy2(__file__, retained / 'package_publication.py')
    path.write_bytes(compact)
    manifest_path = stage / 'publication-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for output in manifest['outputs']:
        if output['path'].endswith('/publication.json'):
            output['sha256'] = sha(path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    record = {'status': 'passed', 'at': datetime.now(timezone.utc).isoformat(), 'command': sys.argv,
              'scope': 'JSON whitespace serialization only; parsed content is exactly equal, no research recalculation or interpretation change',
              'original_bytes': len(original), 'packaged_bytes': len(compact), 'publication_sha256': sha(path),
              'retained_original_sha256': sha(retained / 'original-publication.json'),
              'producer_sha256': sha(retained / 'package_publication.py')}
    receipt.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    package(parser.parse_args().stage)
