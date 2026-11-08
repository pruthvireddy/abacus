"""Reconstruct baseline download projections from recalculated summary tables."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / 'studies/30_verniman_pivot_statistics_es'
sys.path.insert(0, str(STUDY))
import publish_web

stage = ROOT / 'work/30_verniman_pivot_statistics_es/20261031_ranked_v1'
diagnostic = Path(__file__).resolve().parent / 'baseline-projection-reconstruction'
diagnostic.mkdir(exist_ok=False)
(diagnostic / 'tables').mkdir()
metadata = json.loads((stage / 'metrics.json').read_text())
for item in metadata['source_tables'].values():
    path = Path(item['artifact'])
    shutil.copyfile(stage / path, diagnostic / path)
shutil.copyfile(stage / 'metrics.json', diagnostic / 'metrics.json')
shutil.copytree(stage / 'figures', diagnostic / 'figures')
counts = publish_web.prepare(diagnostic, '20261031_ranked_v1')
for path in (diagnostic / 'tables').glob('publication-*.csv'):
    destination = stage / 'tables' / path.name
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copyfile(path, destination)
print(json.dumps({'status': 'passed', 'scope': 'Reconstructed baseline selected-download projections only; diagnostic sources are not selected for Narada.', **counts}))
