"""Retain a byte-pinned, read-only Node 24 publisher check of saved output."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess
import sys


def record(path, root=None):
    path = path.resolve()
    return {'path': str(path.relative_to(root)) if root else str(path),
            'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


stage = Path(sys.argv[1]).resolve()
workspace = stage.parents[2]
app = workspace / 'apps/narada'
target = stage / 'provenance/publication-dry-run.json'
before = stage / 'provenance/publication-before.json'
log = stage / 'provenance/publication-dry-run.log'
if any(p.exists() for p in (target, before, log)):
    raise ValueError('Publisher check receipt overwrite refused')
node = Path(shutil.which('node')).resolve()
version = subprocess.check_output([str(node), '--version'], text=True).strip()
if not version.startswith('v24.'):
    raise ValueError('Actual publisher check requires Node24')
publication = json.loads((stage / 'publication.json').read_text())
figures = [s['path'] for s in publication['sections'] if s['kind'] == 'figure']
downloads = [s['path'] for s in publication['downloads']]
inputs = [record(stage / p, stage) for p in ['publication.json', 'source-bindings.json', *figures, *downloads]]
sources = [record(p) for p in [Path(__file__), app / 'scripts/publish.mjs',
    app / 'scripts/lib/publication.mjs', app / 'scripts/lib/evidence.mjs',
    app / 'package.json', app / 'package-lock.json', *sorted((app / 'contracts').glob('*.schema.json'))]]
command = [str(node), 'scripts/publish.mjs', '--report', str(stage / 'publication.json'), '--dry-run']
before.write_text(json.dumps({'time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': {'argv': command, 'cwd': str(app)}, 'node_version': version,
    'node_binary': record(node), 'inputs': inputs, 'checker_and_contract_sources': sources,
    'scope': 'Saved publication, selected assets, direct publisher sources/contracts and app lock; automatic dependency completeness is not claimed.'}, indent=2) + '\n')
with log.open('w') as output:
    result = subprocess.run(command, cwd=app, stdout=output, stderr=subprocess.STDOUT)
for r in inputs:
    if record(stage / r['path'], stage) != r:
        raise ValueError('Publisher input changed during read-only check')
for r in sources:
    if record(Path(r['path'])) != r:
        raise ValueError('Publisher/checker source changed during check')
target.write_text(json.dumps({'status': 'passed' if result.returncode == 0 else 'failed',
    'exit_code': result.returncode, 'node_version': version,
    'command': {'argv': command, 'cwd': str(app)}, 'before': record(before, stage),
    'log': record(log, stage), 'inputs': inputs,
    'saved_source_budgets': {'publication_bytes': (stage / 'publication.json').stat().st_size,
        'sections': len(publication['sections']), 'raster_figures': len(figures),
        'total_figure_bytes': sum((stage / p).stat().st_size for p in figures),
        'downloads': len(downloads)},
    'public_staging_performed': False, 'deployment_performed': False,
    'scope': 'Narada schema/content/asset validation of explicit saved source; read-only dry-run, no scientific revalidation.'}, indent=2) + '\n')
print(target.read_text())
sys.exit(result.returncode)
