"""Verify a staged previous-RTH extension before sealing it."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from abacus_bhishma.provenance import sha256_file as sha256


def verify(stage: Path):
    stage = stage.resolve()
    manifest = json.loads((stage / 'manifest.json').read_text())
    assert manifest['study_id'] == '14_asia_session_vp_levels'
    assert manifest['run_id'] == stage.name
    for item in manifest['artifacts']:
        path = stage / item['path']
        assert path.is_file() and path.stat().st_size == item['bytes']
        assert sha256(path) == item['sha256'], item['path']
    events = json.loads((stage / 'events.manifest.json').read_text())
    assert len(events['files']) == 17 * 3
    for item in events['files']:
        assert sha256(stage / item['path']) == item['sha256']
    metrics = pd.read_csv(stage / 'tables/metrics.csv')
    outcomes = pd.read_csv(stage / 'tables/outcomes.csv')
    assert set(metrics.setup) == {'D', 'E'}
    assert set(outcomes.horizon) == {0, 5, 10, 20}
    assert set(outcomes.direction) == {-1, 1}
    assert set(outcomes.path_status).issubset(
        {'complete', 'midnight_censored', 'missing_future_minutes',
         'path_contract_change', 'path_source_degraded'})
    for r in metrics.itertuples():
        group = outcomes[(outcomes.split == r.split) & (outcomes.setup == r.setup)
                         & (outcomes.direction == r.direction) & (outcomes.horizon == r.horizon)]
        complete = group[group.path_status == 'complete']
        assert len(group) == r.signals and len(complete) == r.n
        assert len(group) - len(complete) == r.censored
        if r.n:
            for source, target in [('mfe_points', 'avg_mfe_points'),
                                   ('mae_points', 'avg_mae_points'),
                                   ('terminal_points', 'avg_close_delta_points')]:
                assert np.isclose(complete[source].mean(), getattr(r, target))
            assert np.isclose((complete.terminal_points > 0).mean(), r.favorable_close_share)
    text = (stage / 'report.html').read_text()
    assert '5</td>' in text and '10</td>' in text and '20</td>' in text
    assert 'Avg close Δ (pts)' in text and 'Prev RTH POC fade' in text
    result = {'status': 'passed', 'run_id': stage.name,
              'outcome_rows': len(outcomes), 'metrics_rows': len(metrics),
              'complete_paths': int((outcomes.path_status == 'complete').sum()),
              'checks': ['artifact hashes', 'event hashes', 'horizon coverage',
                         'metric arithmetic', 'report labels']}
    verification_path = stage / 'verification.json'
    encoded = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if verification_path.exists():
        assert verification_path.read_text() == encoded, 'saved verification differs'
    else:
        verification_path.write_text(encoded)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    print(json.dumps(verify(parser.parse_args().stage), indent=2))


if __name__ == '__main__':
    main()
