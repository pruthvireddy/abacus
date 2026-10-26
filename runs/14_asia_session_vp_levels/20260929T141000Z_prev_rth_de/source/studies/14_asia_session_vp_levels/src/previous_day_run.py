"""Execute the previous-session VP extension into a new local evidence bundle."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import html
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd

from abacus_bhishma.paths import load_workspace_paths
from abacus_bhishma.vp_hvn_release import dump, sha256
from .execution import session_outcomes
from .previous_day import session_signals
from .statistics import moving_week_mean_interval
from .study_run import json_ready, read_snapshots, session_groups, split, write_jsonl


STUDY = '14_asia_session_vp_levels'
HORIZONS = (5, 10, 20)
PROTOCOL = 'protocol-1.1.0.md'
SETTINGS = 'study-1.1.yaml'


def _summary(rows):
    frame = pd.DataFrame(rows)
    out = []
    keys = ['split', 'setup', 'direction', 'horizon']
    for key, group in frame.groupby(keys, sort=True):
        complete = group[group.path_status == 'complete']
        row = dict(zip(keys, key))
        row.update(signals=len(group), n=len(complete),
                   censored=len(group)-len(complete),
                   sessions=complete.session_date.nunique(), weeks=complete.week.nunique())
        for field, label in [('mfe_points', 'avg_mfe_points'),
                             ('mae_points', 'avg_mae_points'),
                             ('terminal_points', 'avg_close_delta_points'),
                             ('mfe_tr60', 'avg_mfe_tr60'),
                             ('mae_tr60', 'avg_mae_tr60'),
                             ('terminal_tr60', 'avg_close_delta_tr60')]:
            values = pd.to_numeric(complete[field], errors='coerce').dropna()
            row[label] = float(values.mean()) if len(values) else None
            row[label + '_n'] = len(values)
        row['favorable_close_share'] = float((complete.terminal_points > 0).mean()) if len(complete) else None
        if len(complete):
            interval = moving_week_mean_interval(
                complete.week.to_numpy(dtype='datetime64[D]'),
                complete.terminal_points.to_numpy(dtype=float), block=2)
            row['delta_ci_lower'] = interval.get('lower')
            row['delta_ci_upper'] = interval.get('upper')
        else:
            row['delta_ci_lower'] = row['delta_ci_upper'] = None
        out.append(row)
    return pd.DataFrame(out)


def _view(metrics, selected):
    columns = ['Setup', 'Side', 'Bars', 'N', 'Avg MFE (pts)', 'Avg MAE (pts)',
               'Avg close Δ (pts)', 'Avg MFE (TR60)', 'Avg MAE (TR60)',
               'Avg close Δ (TR60)', 'Favorable close']
    rows = []
    for r in selected.sort_values(['setup', 'direction', 'horizon']).itertuples():
        fmt = lambda x: '—' if pd.isna(x) else f'{x:.2f}'
        rows.append([{'D': 'Prev RTH POC fade', 'E': 'Prev RTH VA retest'}[r.setup],
                     'Long' if r.direction == 1 else 'Short', int(r.horizon), int(r.n),
                     fmt(r.avg_mfe_points), fmt(r.avg_mae_points), fmt(r.avg_close_delta_points),
                     fmt(r.avg_mfe_tr60), fmt(r.avg_mae_tr60), fmt(r.avg_close_delta_tr60),
                     '—' if pd.isna(r.favorable_close_share) else f'{r.favorable_close_share:.1%}'])
    return columns, rows


def _markdown_table(headers, rows):
    return '| ' + ' | '.join(headers) + ' |\n| ' + ' | '.join(['---'] * len(headers)) + ' |\n' + ''.join(
        '| ' + ' | '.join(map(str, row)) + ' |\n' for row in rows)


def _html_table(headers, rows):
    head = ''.join('<th>' + html.escape(str(x)) + '</th>' for x in headers)
    body = ''.join('<tr>' + ''.join('<td>' + html.escape(str(x)) + '</td>' for x in row) + '</tr>' for row in rows)
    return '<div class="scroll"><table><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table></div>'


def _render(stage, metrics, funnel, yearly, profile_name):
    validations = metrics[(metrics.split == 'validation') & (metrics.horizon.isin(HORIZONS))]
    final = metrics[(metrics.split == 'final_2026_ytd') & (metrics.horizon.isin(HORIZONS))]
    headers, validation_rows = _view(metrics, validations)
    _, final_rows = _view(metrics, final)
    description = (
        f'Previous-day means the fixed {profile_name} 09:30–16:00 New York profile, '
        'known before the evening signal. D fades its first in-window POC contact '
        'from each approach side; E enters after a VAH/VAL breakout and later confirmed retest. '
        'Both enter at the next contiguous one-minute open in 20:00–00:00 New York. '
        'A horizon includes its entry candle and requires every one-minute bar through its close by midnight. '
        'Average close Δ is side-signed: close minus entry for longs, entry minus close for shorts. '
        'MFE and MAE are intrahorizon extrema, not realized profit or loss. '
        'TR60 is the mean true range of the 60 complete minutes before the signal candle, '
        'not a conventional 14-bar ATR. Undefined TR60 values are omitted only from normalized columns, '
        'with denominators saved in tables/metrics.csv. The pictured approach ≥1 ATR condition was '
        'not requested as a signal filter and is not applied.')
    first_year = int(yearly.year.min()) if len(yearly) else None
    coverage = (f'The first complete strict-quality horizon occurs in {first_year}; '
                if first_year is not None else 'No strict-quality horizons were complete; ')
    limits = (
        'These added hypotheses were specified after the earlier Asia VP report was inspected. '
        'The 2024–2025 and 2026 samples are therefore descriptive reuse, not untouched validation. '
        + coverage +
        'Reference completeness is conservative: the saved release flags the combined prior-reference '
        'set rather than just prior RTH. Retrospective completeness and future-path censoring are '
        'reported separately. One-minute OHLCV cannot establish intrabar order, actual fills, costs, '
        'or net profitability. The full 2010–2026 evidence and excluded candidates are in the saved tables.')
    title = 'Asia session VP — previous-RTH POC fade and VA continuation'
    report = (f'# {title}\n\n{description}\n\n## 2024–2025 descriptive period\n\n'
              + _markdown_table(headers, validation_rows)
              + '\n## 2026 year to date\n\n' + _markdown_table(headers, final_rows)
              + '\n## Evidence and limits\n\n' + limits + '\n\n'
              + 'The full-history, year-by-year and exclusion tables are in `tables/`. '
              + 'The earlier three setups remain in the [sealed 1.0.0 report]'
                '(../../../runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/report.html).\n')
    (stage / 'report.md').write_text(report)
    page = ''.join([
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1"><title>', html.escape(title), '</title>',
        '<style>body{font:16px/1.5 system-ui;background:#111416;color:#f0f3f4;max-width:1400px;'
        'margin:36px auto;padding:0 22px}h1{font-size:32px}p{max-width:1050px;color:#c9d4d7}'
        '.scroll{overflow:auto;margin:18px 0 36px}table{border-collapse:collapse;min-width:1050px}'
        'th,td{padding:9px 12px;border-bottom:1px solid #333;text-align:right;white-space:nowrap}'
        'th:first-child,td:first-child{text-align:left}th{color:#90b9c9}a{color:#7fd8d0}'
        '</style><h1>', html.escape(title), '</h1><p>', html.escape(description), '</p>',
        '<h2>2024–2025 descriptive period</h2>', _html_table(headers, validation_rows),
        '<h2>2026 year to date</h2>', _html_table(headers, final_rows),
        '<h2>Evidence and limits</h2><p>', html.escape(limits), '</p>',
        '<p><a href="tables/metrics.csv">All metrics</a> · '
        '<a href="tables/yearly.csv">Yearly results</a> · '
        '<a href="tables/funnel.csv">Signal and exclusion counts</a> · '
        '<a href="../../../runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/report.html">Earlier three setups</a>'
        '</p></html>'])
    (stage / 'report.html').write_text(page)
    lines = []
    for r in validations.itertuples():
        if r.horizon != 20 or not r.n:
            continue
        side = 'long' if r.direction == 1 else 'short'
        interval = ('unavailable' if pd.isna(r.delta_ci_lower) or pd.isna(r.delta_ci_upper)
                    else f'{r.delta_ci_lower:+.2f} to {r.delta_ci_upper:+.2f}')
        lines.append(f'- Setup {r.setup} {side}, 20 bars: {r.n} complete events; '
                     f'average favorable/adverse excursions {r.avg_mfe_points:.2f}/{r.avg_mae_points:.2f} points; '
                     f'average signed close delta {r.avg_close_delta_points:+.2f} points '
                     f'({interval} two-week block interval).')
    (stage / 'advice.md').write_text(
        '# Dated interpretation — ' + datetime.now(timezone.utc).date().isoformat() + '\n\n'
        + '\n'.join(lines) + '\n\nThese are exploratory path descriptions after prior sample inspection. '
        'No net edge or executable strategy is established; assess spread, slippage, fills and a genuinely new sample before promotion.\n')


def execute(stage: Path):
    paths = load_workspace_paths()
    root, workspace = paths.publication_root, paths.workspace_root
    study = workspace / 'studies' / STUDY
    settings = (study / SETTINGS).read_text()
    if ('protocol_status: frozen_before_outcomes' not in settings
            or 'previous_rth' not in settings
            or 'fade_from_above_long: true' not in settings):
        raise ValueError('completed, frozen previous-RTH direction settings required')
    if not (study / PROTOCOL).is_file():
        raise ValueError('extension protocol missing')
    lock = json.loads((study / 'inputs.lock.json').read_text())
    identity = lock['derived_feature_release']
    manifest_file = root / identity['manifest_path']
    if sha256(manifest_file) != identity['sha256']:
        raise ValueError('feature manifest hash mismatch')
    manifest = json.loads(manifest_file.read_text())
    for item in manifest['output_files']:
        if sha256(root / item['path']) != item['sha256']:
            raise ValueError(f"feature file changed: {item['path']}")
    stage = stage.resolve()
    stage.mkdir(parents=True, exist_ok=False)
    for name in ('tables', 'events', 'source'):
        (stage / name).mkdir()
    all_rows, all_ledger = [], []
    event_counts = []
    for year in range(2010, 2027):
        annual_ledger, annual_signals, annual_outcomes = [], [], []
        for _, group in session_groups(read_snapshots(root, manifest, year)):
            ledger, signals = session_signals(group)
            annual_ledger.extend(ledger)
            annual_signals.extend(signals)
            annual_outcomes.extend(session_outcomes(group, signals, horizons=HORIZONS))
        files = [('ledger', annual_ledger), ('signals', annual_signals), ('outcomes', annual_outcomes)]
        for label, values in files:
            location = stage / f'events/{label}_{year}.jsonl.gz'
            write_jsonl(location, values)
            event_counts.append(dict(path=str(location.relative_to(stage)), rows=len(values), sha256=sha256(location)))
        all_ledger.extend(annual_ledger)
        for value in annual_outcomes:
            all_rows.append({key: json_ready(value.get(key)) for key in
                             ('setup', 'variant', 'direction', 'session_date', 'year', 'week', 'season',
                              'minute', 'signal_ts', 'entry_ts', 'entry', 'level', 'origin_minute',
                              'volatility60', 'va_width', 'horizon', 'path_status',
                              'mae_points', 'mfe_points', 'terminal_points',
                              'mae_tr60', 'mfe_tr60', 'terminal_tr60')}
                            | {'split': split(year)})
        print(f'{year}: {len(annual_signals)} candidate signals, '
              f'{sum(x["path_status"] == "complete" for x in annual_outcomes)} complete paths', flush=True)
    frame = pd.DataFrame(all_rows)
    frame.to_csv(stage / 'tables/outcomes.csv', index=False)
    metrics = _summary(all_rows)
    metrics.to_csv(stage / 'tables/metrics.csv', index=False)
    year_summary = frame[(frame.horizon != 0) & (frame.path_status == 'complete')].groupby(
        ['year', 'setup', 'direction', 'horizon'], sort=True).agg(
        n=('entry', 'size'), sessions=('session_date', 'nunique'),
        avg_mfe_points=('mfe_points', 'mean'), avg_mae_points=('mae_points', 'mean'),
        avg_close_delta_points=('terminal_points', 'mean')).reset_index()
    year_summary.to_csv(stage / 'tables/yearly.csv', index=False)
    funnel = pd.DataFrame(all_ledger).groupby(
        ['year', 'setup', 'direction', 'status'], sort=True).size().rename('n').reset_index()
    funnel.to_csv(stage / 'tables/funnel.csv', index=False)
    dump(stage / 'metrics.json', {'study_id': STUDY, 'protocol_version': '1.1.0',
                                 'feature_manifest_sha256': identity['sha256'],
                                 'fixed_horizons_bars': list(HORIZONS),
                                 'metrics': json_ready(metrics.to_dict('records'))})
    dump(stage / 'events.manifest.json', {'files': event_counts})
    dump(stage / 'config.json', {'format': f'frozen {SETTINGS} verbatim', 'study_yaml': settings})
    shutil.copyfile(study / 'inputs.lock.json', stage / 'inputs.lock.json')
    _render(stage, metrics, funnel, year_summary, 'previous RTH')
    sources = [study / SETTINGS, study / PROTOCOL, study / 'inputs.lock.json',
               study / 'run.py', study / 'verify_previous_day_run.py', workspace / 'uv.lock',
               *sorted((study / 'src').glob('*.py')), *sorted((study / 'tests').glob('*.py'))]
    snapshots = []
    for source in sources:
        target = stage / 'source' / source.relative_to(workspace)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        snapshots.append({'path': str(source.relative_to(workspace)), 'sha256': sha256(source)})
    artifacts = [{'path': str(p.relative_to(stage)), 'sha256': sha256(p), 'bytes': p.stat().st_size}
                 for p in sorted(stage.rglob('*')) if p.is_file()]
    command = ('UV_CACHE_DIR=work/.uv-cache ./scripts/uv run --locked --no-sync python '
               f'studies/{STUDY}/run.py --execute-prev-day --stage {stage.relative_to(workspace)}')
    dump(stage / 'manifest.json', {'study_id': STUDY, 'run_id': stage.name,
                                  'created_utc': datetime.now(timezone.utc).isoformat(),
                                  'status': 'staged_verified_pending_seal', 'command': command,
                                  'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=workspace, text=True).strip(),
                                  'git_status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=workspace, text=True),
                                  'python': sys.version,
                                  'environment': {x: importlib.metadata.version(x) for x in ('numpy', 'pandas', 'pyarrow')},
                                  'uv_lock_sha256': sha256(workspace / 'uv.lock'),
                                  'feature_manifest': identity,
                                  'protocol_sha256': sha256(study / PROTOCOL),
                                  'source_snapshot': snapshots, 'artifacts': artifacts,
                                  'template_version': 'abacus-report-1'})
    return stage
