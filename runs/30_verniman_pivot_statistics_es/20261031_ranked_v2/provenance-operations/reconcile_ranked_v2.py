"""Compare fresh v2 with the retained failed v1 diagnostic; no estimation."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'work/30_verniman_pivot_statistics_es'
old, new = BASE / '20261031_ranked_v1', BASE / '20261031_ranked_v2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
changes, tolerance_cells, checked = 0, 0, 0
with (old / 'tables/ranked_summary.csv').open(newline='') as a, (new / 'tables/ranked_summary.csv').open(newline='') as b:
    before, after = csv.DictReader(a), csv.DictReader(b)
    assert before.fieldnames == after.fieldnames
    count = 0
    for left, right in zip(before, after, strict=True):
        count += 1
        for key in left:
            checked += 1
            if left[key] == right[key]:
                continue
            if key == 'censored' and left['statistic_id'] == right['statistic_id'] == 'S13':
                changes += 1
                continue
            try:
                valid = math.isclose(float(left[key]), float(right[key]), rel_tol=1e-11, abs_tol=1e-8)
            except ValueError:
                valid = False
            if not valid:
                raise ValueError(f'Unexpected diagnostic reconciliation difference: row {count}, {key}')
            tolerance_cells += 1
if changes != 2224:
    raise ValueError(f'Unexpected S13 metadata correction count: {changes}')
for name in ('ledgers.json.gz', 'ranked-ledgers.json.gz'):
    if sha(old / name) != sha(new / name):
        raise ValueError('Event/path/coverage ledger changed: ' + name)
record = {'status': 'passed', 'rows': count, 'cells': checked, 'changed_S13_censored_cells': changes,
          'other_numeric_cells_within_tolerance': tolerance_cells,
          'old_summary_sha256': sha(old / 'tables/ranked_summary.csv'),
          'new_summary_sha256': sha(new / 'tables/ranked_summary.csv'),
          'event_path_coverage_ledgers_byte_identical': True,
          'qualification': 'Saved byte/cell reconciliation to an unsealed diagnostic; fresh v2 independently recalculates intervals and requires its own native verification.'}
with (new / 'diagnostic-reconciliation.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(record))
