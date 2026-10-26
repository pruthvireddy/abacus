"""Read-only actual Stage 2 presentation review; never reruns estimators."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import struct
import sys

WORKSPACE = Path('/Users/ppanati/Documents/projects/abacus')
STUDY = WORKSPACE / 'studies/21_ema_cloud_trend_follow_opportunity'
STAGE = WORKSPACE / 'work/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4'
REVIEW = Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def identity(path):
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=sha(path))

def write_new(path, value):
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + '\n')

def rows(name):
    with (STAGE / 'tables' / name).open(newline='') as stream:
        return list(csv.DictReader(stream))

def assert_equal(actual, expected, context):
    if actual != expected:
        raise ValueError(context)

def prepare():
    bindings = json.loads((STAGE / 'source-bindings.json').read_text())
    paths = [STAGE / name for name in ('report.md', 'report.html', 'advice.md', 'publication.json',
        'source-bindings.json', 'metrics.json', 'exclusions.json', 'protocol.md', 'config.json',
        'inputs.lock.json', 'baseline.lock.json', 'evidence.manifest.json', 'events.manifest.json',
        'figure-environment.json', 'provenance/source-inventory.json', 'provenance/slow-baseline-parity.json')]
    paths += list((STAGE / 'tables').glob('*')) + list((STAGE / 'figures').glob('*.png')) + list((STAGE / 'downloads').glob('*.csv'))
    paths += [Path(item['path']) for item in bindings['baseline_sources']]
    paths += [STUDY / 'src' / name for name in ('stage2_reference.py', 'stage2_reconcile.py',
        'stage2_reporting.py', 'stage2_contract.py', 'reconcile.py', 'reporting.py')]
    paths += [Path(__file__).resolve()]
    write_new(REVIEW / 'review-before.json', dict(schema_version=1, run_id=STAGE.name,
        captured_at_utc=datetime.now(timezone.utc).isoformat(),
        scope='Formal saved-source presentation review only. Initial read-only familiarization and native-resolution visual inspection preceded these formal execution pins; numerical estimators are not rerun.',
        identities=[identity(p) for p in sorted(set(paths)) if p.is_file()]))

def run():
    before_path = REVIEW / 'review-before.json'
    before = json.loads(before_path.read_text())
    for pin in before['identities']:
        assert_equal(identity(Path(pin['path'])), pin, 'pre-execution dependency drift')
    sys.path.insert(0, str(STUDY))
    from src.stage2_reconcile import verify_publication
    transfer = verify_publication(STAGE)
    report = (STAGE / 'report.md').read_text()
    advice = (STAGE / 'advice.md').read_text()
    publication = json.loads((STAGE / 'publication.json').read_text())
    contrasts = rows('S2-T08_branch_contrasts.csv')
    primary = [r for r in contrasts if r['direction'] == 'All' and r['horizon'] == '15' and
        r['support'] == 'all' and r['unit'] == 'points' and r['metric'] == 'terminal_delta' and r['weighting'] == 'event' and r['block_weeks'] == '4' and r['interval_type'] in ('pointwise95', 'bonferroni')]
    assert_equal(len(primary), 12, 'complete primary six-cell paired interval inventory')
    assert_equal({(r['product'], r['interval_minutes']) for r in primary}, {(p, i) for p in ('ES', 'GC', 'NQ') for i in ('3', '5')}, 'primary scientific cells')
    assert_equal(all(float(r['ci_low']) <= 0 <= float(r['ci_high']) for r in primary), True, 'actual primary intervals')
    sensitivities = [r for r in contrasts if r['direction'] == 'All' and r['horizon'] == '15' and r['support'] == 'all' and r['unit'] == 'points' and r['metric'] == 'terminal_delta' and r['weighting'] == 'event' and r['block_weeks'] in ('1', '8') and r['interval_type'] in ('pointwise95', 'bonferroni')]
    point_exceptions = [r for r in sensitivities if r['interval_type'] == 'pointwise95' and not float(r['ci_low']) <= 0 <= float(r['ci_high'])]
    assert_equal({(r['product'], r['interval_minutes'], r['block_weeks']) for r in point_exceptions}, {('GC', '3', '1'), ('ES', '3', '8')}, 'retain pointwise block sensitivity exceptions')
    assert_equal(all(float(r['ci_low']) <= 0 <= float(r['ci_high']) for r in sensitivities if r['interval_type'] == 'bonferroni'), True, 'adjusted sensitivity intervals')
    scorecard = [r for r in rows('S2-T02_horizon_scorecard.csv') if r['direction'] == 'All' and r['horizon'] == '15' and r['support'] == 'all' and r['unit'] == 'points']
    assert_equal(len(scorecard), 12, 'pooled branch scorecard inventory')
    assert_equal(all(float(r['mean_mae']) > float(r['mean_mfe']) for r in scorecard), True, 'all pooled branch adverse excursion exceeds favorable')
    positive_terminal = [r['row_id'] for r in scorecard if float(r['mean_terminal_delta']) > 0]
    assert_equal({(r['product'], r['interval_minutes'], r['touch_mode']) for r in scorecard if float(r['mean_terminal_delta']) > 0}, {('ES', '5', 'fast'), ('ES', '5', 'slow')}, 'do not describe every pooled terminal point mean as negative')
    annual = [r for r in rows('S2-T04_stability.csv') if r['product'] == 'GC' and r['direction'] == 'All' and r['horizon'] == '15' and r['support'] == 'all' and r['unit'] == 'points' and r['period_kind'] == 'year']
    early_slow = [r for r in annual if r['touch_mode'] == 'slow' and r['period'] in ('2018', '2019')]
    assert_equal({(r['interval_minutes'], r['period'], r['completed']) for r in early_slow}, {('3', '2018', '10'), ('3', '2019', '39'), ('5', '2018', '5'), ('5', '2019', '29')}, 'early GC sparse supports')
    assert_equal(all(r['sparse_warning'] == 'True' for r in early_slow), True, 'early GC sparse flags')
    coverage = rows('S2-T00_coverage.csv')
    for r in coverage:
        if r['split'] == 'development':
            assert_equal(r['feature_ready_slots'], r['mapped_ready_slots'], 'shared feature/mapped readiness field')
            if abs(float(r['ready_share']) - int(r['mapped_ready_slots']) / int(r['scheduled_slots'])) > 1e-14:
                raise ValueError('readiness denominator')
        elif r['interval_minutes'] == '3':
            assert_equal([r[k] for k in ('feature_ready_slots', 'mapped_ready_slots', 'ready_share', 'ready_sessions')], ['', '', '', ''], 'warmup 3m readiness remains undefined')
    diagnostics = rows('S2-T09_episode_pairing.csv')
    denominator_checks = []
    for p in ('ES', 'GC', 'NQ'):
        for i in ('3', '5'):
            for side in ('All', 'Buy', 'Sell'):
                cell = [r for r in diagnostics if (r['product'], r['interval_minutes'], r['direction']) == (p, i, side)]
                for kind in ('pair_relation', 'pair_scope', 'same_bar_slow_contact', 'strictly_later_slow_contact', 'strictly_later_slow_signal'):
                    group = [r for r in cell if r['summary_kind'] == kind]
                    denominator = int(group[0]['episodes']) if kind.startswith('pair_') else int(group[0]['descriptor_eligible'])
                    assert_equal(sum(int(r['count']) for r in group), denominator, 'episode/descriptor population denominator')
                    for r in group:
                        expected = int(r['count']) / denominator if denominator else None
                        if expected is None:
                            assert_equal(r['share'], '', 'undefined empty descriptor share')
                        elif abs(float(r['share']) - expected) > 1e-14:
                            raise ValueError('descriptor share denominator')
                    denominator_checks.append(dict(product=p, interval_minutes=int(i), direction=side, summary_kind=kind, denominator=denominator, rows=[r['row_id'] for r in group]))
    examples = rows('S2-T06_examples.csv')
    assert_equal(len(examples), 36, 'six deterministic example classes per cell')
    for r in examples:
        if r['kind'] == 'rejected':
            assert_equal([r[k] for k in ('status', 'mfe', 'mae', 'terminal_delta')], ['', '', '', ''], 'rejected example has no future score')
        if r['kind'] == 'censored':
            assert_equal([r[k] for k in ('status', 'mfe', 'mae', 'terminal_delta')], ['censored', '', '', ''], 'censored example has null scores')
    import pandas as pd
    paths = pd.read_parquet(STAGE / 'tables/selected-example-paths.parquet')
    assert_equal(paths.timestamp.dt.tz_convert('America/New_York').dt.year.between(2018, 2020).all().item(), True, 'displayed paths contain development candles only')
    for text in (report, advice):
        for phrase in ('Warmup first events are retained and never replaced', 'absent contacts at resets or the endpoint remain unresolved', 'These labels never filter a fast signal', 'later outcomes remain reserved', 'original raw reconstruction', 'native TradingView equivalence', 'off-device backup remain uncertified'):
            assert_equal(phrase in text, True, 'required causal/scope/evidence qualification')
    assert_equal('nominal 95% familywise confidence' in report and 'exact tails .05/12' in report, True, 'nominal familywise uncertainty wording')
    assert_equal('Early GC counts are sparse' in report and 'changing mapped readiness limit stability interpretation' in report, True, 'coverage/stability qualification')
    figure_review = []
    for path in sorted((STAGE / 'figures').glob('*.png')):
        payload = path.read_bytes()
        assert_equal(payload[:8], b'\x89PNG\r\n\x1a\n', 'PNG file signature')
        width, height = struct.unpack('>II', payload[16:24])
        figure_review.append(dict(**identity(path), width=width, height=height,
            visual_status='readable_at_native_resolution',
            note=('Annual count annotations near lower plot edges and GC3m early-year labels are crowded. Numerical means/readiness and year axes remain readable; exact counts and sparse flags are explicit in the adjacent annual table. Nonblocking presentation limitation.' if path.name == 'calendar_coverage.png' else
                  'Same-bar signals share one labeled window; different-time windows use a marked omitted interval; blue/orange EMA caption is explicit.' if path.name == 'episodes.png' else
                  'Adverse/rejected/censored/unresolved classes have separate panels; no favorable substitution or rejected future score; blue/orange EMA caption is explicit.' if path.name == 'qualifying_examples.png' else
                  'Axes, branch styles and product/candle panels are clear; descriptive values remain product-specific.')))
    for pin in before['identities']:
        assert_equal(identity(Path(pin['path'])), pin, 'review dependency drift')
    result = dict(schema_version=1, run_id=STAGE.name, status='passed_with_nonblocking_visual_note',
        completed_at_utc=datetime.now(timezone.utc).isoformat(), reviewer='Agent C /root/reporting',
        scope='Read-only actual narrative, table-level denominator/interpretation consistency, selected-source transfer and all six native-resolution PNGs. Full scalar/uncertainty numerical reconciliation is the separately running root verify phase; this receipt does not replace it. No browser/publisher claim is made here.',
        before_execution=identity(before_path), reviewer_source=identity(Path(__file__)), dependencies_unchanged=True,
        publication_sections=len(publication['sections']), source_transfer=transfer,
        primary_rows=[dict(row_id=r['row_id'], estimate=r['estimate'], ci_low=r['ci_low'], ci_high=r['ci_high']) for r in primary],
        pointwise_sensitivity_exceptions=[dict(row_id=r['row_id'], ci_low=r['ci_low'], ci_high=r['ci_high']) for r in point_exceptions],
        pooled_branch_rows=[r['row_id'] for r in scorecard], all_twelve_mean_mae_gt_mfe=True,
        positive_terminal_point_mean_rows=positive_terminal,
        early_gc_sparse_rows=[dict(row_id=r['row_id'], completed=r['completed'], sessions=r['contributing_sessions'], sparse_warning=r['sparse_warning']) for r in early_slow],
        coverage_rows=len(coverage), retrospective_denominator_checks=denominator_checks,
        examples=len(examples), selected_path_rows=len(paths), all_displayed_candles_in_development=True,
        figure_reviews=figure_review, necessary_corrections=[],
        interpretation='The report scopes its conclusion to prespecified pooled comparisons, preserves negative baseline side/session findings and sparse/changing supports, retains pointwise sensitivity exceptions, and distinguishes retrospective scoped-first descriptors, unresolved nulls and union frequencies from causal or executable profit claims.')
    write_new(REVIEW / 'report-review.json', result)
    print(json.dumps(dict(status=result['status'], sections=result['publication_sections'], **{k: transfer[k] for k in ('public_cells', 'download_cells', 'claims', 'figures')}, examples=len(examples), path_rows=len(paths), retrospective_denominator_groups=len(denominator_checks), necessary_corrections=[])))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'run'))
    args = parser.parse_args()
    prepare() if args.phase == 'prepare' else run()
