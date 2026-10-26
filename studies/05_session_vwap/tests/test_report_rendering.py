"""Synthetic rendering and compatibility checks; no historical research inputs."""
from argparse import Namespace
from contextlib import ExitStack
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zlib
import json
from pathlib import Path
import pandas as pd

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY))
from src import reporting, report_rendering

STAGE_NAME = '20261010T000000Z_Synthetic'

class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        assert tz is timezone.utc
        return cls(2026, 10, 10, 12, 34, 56, tzinfo=tz)


def fixture(zero=False):
    rows = [
        dict(strategy='C', product='ALL', events=10, evaluable=8, successes=2,
             rate=.25, sessions=3, ci_low=.125, ci_high=.5,
             favorable=2, adverse=2, neither=2, ambiguous=2),
        dict(strategy='B', product='ALL', events=9, evaluable=8, successes=5,
             rate=.625, sessions=3, ci_low=.25, ci_high=.875,
             departure_windows=2, h30_frozen_returns=2, h30_n=4,
             evolving_returns=3, conditional_return_median_minutes=12.5),
        dict(strategy='A', product='ALL', events=11, evaluable=10, successes=2,
             rate=.2, sessions=4, ci_low=None, ci_high=None,
             favorable=2, adverse=3, neither=4, ambiguous=1),
        dict(strategy='A', product='ES', events=99, evaluable=99, successes=99,
             rate=1., sessions=9, ci_low=1., ci_high=1.,
             favorable=99, adverse=0, neither=0, ambiguous=0),
    ]
    if zero:
        for row in rows:
            if row['product'] == 'ALL':
                for key in ('events', 'evaluable', 'successes', 'sessions', 'favorable',
                            'adverse', 'neither', 'ambiguous', 'departure_windows',
                            'h30_frozen_returns', 'h30_n', 'evolving_returns'):
                    if key in row:
                        row[key] = 0
                for key in ('rate', 'ci_low', 'ci_high', 'conditional_return_median_minutes'):
                    if key in row:
                        row[key] = None
    cards = pd.DataFrame(rows)
    breaks = pd.DataFrame([
        dict(breakdown='product+timeframe+anchor+window+split', strategy=strategy,
             split=split, successes=success, evaluable=total)
        for strategy in ('B', 'A', 'C')
        for split, success, total in (('development', 1, 2), ('validation', 0, 2),
                                      ('final', 2, 2))
    ] + [dict(breakdown='ignored', strategy='B', split='development',
              successes=99, evaluable=99)])
    controls = pd.DataFrame([
        dict(product='ALL', barrier_definition='half_sigma', split='development',
             treated='A extremes', control='lesser departures', matched_treated=4.,
             difference=.125, ci_low_conditional_overlap=-.25,
             ci_high_conditional_overlap=.5, claim_status='exploratory only'),
        dict(product='ALL', barrier_definition='half_sigma', split='final',
             treated='C retests', control='near approaches', matched_treated=None,
             difference=None, ci_low_conditional_overlap=None,
             ci_high_conditional_overlap=None, claim_status='no overlap'),
        dict(product='ES', barrier_definition='half_sigma', split='ignored-product',
             treated='ignore me', control='ignore me', matched_treated=99.,
             difference=1., ci_low_conditional_overlap=1.,
             ci_high_conditional_overlap=1., claim_status='ignore me'),
        dict(product='ALL', barrier_definition='fixed_8_ticks', split='ignored-barrier',
             treated='ignore me', control='ignore me', matched_treated=99.,
             difference=1., ci_low_conditional_overlap=1.,
             ci_high_conditional_overlap=1., claim_status='ignore me'),
    ])
    samples = pd.DataFrame([
        dict(product='NQ', strategy='C', **{'class': 'ambiguous'},
             signal_ts='2026-01-02 13:00:00+00:00', event_id='NQ:C:<example&>:2'),
        dict(product='ES', strategy='B', **{'class': 'nonreturn'},
             signal_ts='2024-01-02 12:00:00+00:00', event_id='ES:B:1'),
        dict(product='ES', strategy='A', **{'class': 'favorable'},
             signal_ts='2024-01-02 11:00:00+00:00', event_id='ES:A:1'),
    ])
    events = pd.DataFrame({'event_id': ['ES:B:1', 'ES:A:1', 'NQ:C:2'],
                           'direction': [-1, 1, 1]})
    windows = pd.DataFrame({'product': ['ES', 'ES', 'GC'],
                            'session_date': ['2024-01-02', '2024-01-02', '2026-01-02']})
    audit = [{'feature_bars_reconciled': 1000, 'references_audited': 2},
             {'feature_bars_reconciled': 7, 'references_audited': 3}, {}]
    unused = pd.DataFrame({'precomputed': [1]})
    return dict(cards=cards, breaks=breaks, horizons=unused, cycles=unused,
                controls=controls, samples=samples, events=events, windows=windows), audit


def setup_stage(parent: Path, zero=False):
    stage = parent / STAGE_NAME
    stage.mkdir(parents=True)
    frames, audit = fixture(zero)
    (stage / 'source-audit.json').write_text(json.dumps(audit))
    return stage, frames

# Captured from the exact original working-tree renderer before extracting it.
# These cover serialized bytes, in addition to the semantic assertions below.
OUTPUT_HASHES = {
    'populated': {
        'report.md': '7599b821f5b3775493df1f86ad0fb2cd39d63c8c843258fd4143f854d95dfff6',
        'report.html': '5de9883db240abcd98a345aaeaf0d0e7ea954b117779f1efbc62f89cb7f3dfe3',
        'figures/barrier-outcomes.svg': '7aac0dd198c8372138602611844b9011d505b8b8f12b816475cac760669ac512',
        'figures/barrier-outcomes.png': '593151c32283ccc0f5a878ecaea8fe2b8b42a090f980d6af3a0f4de49edda5cb',
        'publication.json': '727d216548b732cdec489caed0ed584e79d2ffcbf8ce64c998ccf34cbe1d1e10',
    },
    'zero': {
        'report.md': 'd16217a867dc569e8ba34542634d8b022e8b6395c211fb8c6f2ecff82ae706f9',
        'report.html': '70f6e07cc82ad95de42714fd50c4f2b8ef43a2662a5bc0350fc409fdfbac2a67',
        'figures/barrier-outcomes.svg': '86490dc16eb90ffa8c719085ae3b7ac22181d5094bf7c8c9963b24f819074ace',
        'figures/barrier-outcomes.png': '2cbd6d37163bd78df2d5c270950871e95946f12b4f165ebda57e812683add144',
        'publication.json': 'd0a06765fe7ac717c6a1326f4200537f1d38de23cfb1355353fa2a77fce03446',
    },
}


def render(stage, frames):
    # Exercise the existing compatibility entry points, not a separate renderer.
    reporting.write_figure(stage, frames['cards'])
    reporting.write_report(stage, **frames)
    with patch.object(report_rendering, 'datetime', FrozenDateTime):
        reporting.write_publication(stage, frames['cards'])


def png_pixels(path):
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise AssertionError('not a PNG')
    chunks = []
    offset = 8
    while offset < len(data):
        size = struct.unpack('>I', data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + size]
        crc = struct.unpack('>I', data[offset + 8 + size:offset + 12 + size])[0]
        if crc != zlib.crc32(kind + payload) & 0xffffffff:
            raise AssertionError('PNG checksum mismatch')
        chunks.append((kind, payload))
        offset += 12 + size
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        '>IIBBBBB', chunks[0][1])
    if (depth, color, compression, filtering, interlace) != (8, 2, 0, 0, 0):
        raise AssertionError('unexpected PNG encoding')
    scanlines = zlib.decompress(b''.join(payload for kind, payload in chunks if kind == b'IDAT'))
    stride = 1 + width * 3
    if any(scanlines[y * stride] != 0 for y in range(height)):
        raise AssertionError('unexpected scanline filter')
    return width, height, lambda x, y: tuple(scanlines[y * stride + 1 + x * 3:y * stride + 4 + x * 3])


def caller(name):
    path = STUDY / f'{name}.py'
    spec = importlib.util.spec_from_file_location(f'study05_render_test_{name}', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RenderingTests(unittest.TestCase):
    def test_formatting_preserves_nulls_ratios_and_numeric_units(self):
        for value in (None, pd.NA, float('nan')):
            with self.subTest(value=value):
                self.assertEqual(reporting._fmt(value), '—')
                self.assertEqual(reporting._fmt(value, True), '—')
        self.assertEqual(reporting._fmt(.125, True), '12.5%')
        self.assertEqual(reporting._fmt(0., True), '0.0%')
        self.assertEqual(reporting._fmt(1234), '1,234')
        self.assertEqual(reporting._fmt(1234.25), '1,234.2')

    def test_complete_original_output_bytes_and_input_preservation(self):
        for name, zero in (('populated', False), ('zero', True)):
            with self.subTest(fixture=name), TemporaryDirectory() as directory:
                stage, frames = setup_stage(Path(directory), zero)
                originals = {key: frame.copy(deep=True) for key, frame in frames.items()}
                audit_before = (stage / 'source-audit.json').read_bytes()
                render(stage, frames)
                for path, expected in OUTPUT_HASHES[name].items():
                    self.assertEqual(sha256((stage / path).read_bytes()).hexdigest(), expected, path)
                self.assertEqual((stage / 'source-audit.json').read_bytes(), audit_before)
                for key in frames:
                    pd.testing.assert_frame_equal(frames[key], originals[key])
                self.assertEqual({str(path.relative_to(stage)) for path in stage.rglob('*') if path.is_file()},
                                 set(OUTPUT_HASHES[name]) | {'source-audit.json'})

    def test_report_denominators_nulls_qualifications_and_example_order(self):
        with TemporaryDirectory() as directory:
            stage, frames = setup_stage(Path(directory))
            reporting.write_report(stage, **frames)
            markdown = (stage / 'report.md').read_text()
            html = (stage / 'report.html').read_text()
            self.assertIn('| Return after departure | 8 / 9 | 3 | 5/8 (62.5%) | 25.0%–87.5% |', markdown)
            self.assertIn('| First outside-2σ fade | 10 / 11 | 4 | 2/10 (20.0%) | unavailable |', markdown)
            self.assertIn('contains 3 product × date × timeframe × anchor/window views', markdown)
            self.assertIn('includes 2 eligible product-days', markdown)
            self.assertIn('verified 1,007 published feature bars and 5 evaluable event reference opens', markdown)
            self.assertIn('development — A extremes versus lesser departures: 4.0 matched treated events; '
                          'observed difference 12.5%; shared-date bootstrap interval -25.0%–50.0%. exploratory only.', markdown)
            self.assertIn('final — C retests versus near approaches: unmatched matched treated events; '
                          'observed difference —. no overlap.', markdown)
            self.assertNotIn('ignore me', markdown)
            self.assertLess(markdown.index('`ES:A:1`'), markdown.index('`ES:B:1`'))
            self.assertLess(markdown.index('`ES:B:1`'), markdown.index('`NQ:C:<example&>:2`'))
            self.assertIn('These are conditional movement observations, not net profitability.', markdown)
            self.assertIn('this cannot be used as an entry-time filter.', markdown)
            self.assertIn('Ambiguity remains in the denominator', markdown)
            self.assertIn('NQ:C:&lt;example&amp;&gt;:2', html)
            self.assertIn("<a href='tables/scorecards.csv'>Scorecards</a>", html)
            self.assertIn("<img src='figures/barrier-outcomes.svg'", html)
            self.assertNotIn('http://', html)
            self.assertNotIn('https://', html)

    def test_figure_has_all_four_classes_with_each_own_denominator(self):
        with TemporaryDirectory() as directory:
            stage, frames = setup_stage(Path(directory))
            reporting.write_figure(stage, frames['cards'])
            svg = ET.parse(stage / 'figures/barrier-outcomes.svg').getroot()
            rectangles = svg.findall('{http://www.w3.org/2000/svg}rect')
            bars = [item.attrib for item in rectangles if item.attrib['height'] == '28']
            self.assertEqual([float(item['width']) for item in bars],
                             [124., 186., 248., 62., 155., 155., 155., 155.])
            self.assertEqual([item['fill'] for item in bars],
                             ['#2b8a6e', '#cf604a', '#a4afc0', '#8a6cb3'] * 2)
            width, height, pixel = png_pixels(stage / 'figures/barrier-outcomes.png')
            self.assertEqual((width, height), (900, 250))
            for x, color in ((180, (43, 138, 110)), (304, (207, 96, 74)),
                             (490, (164, 175, 192)), (738, (138, 108, 179))):
                self.assertEqual(pixel(x, 70), color)
            for x, color in ((180, (43, 138, 110)), (335, (207, 96, 74)),
                             (490, (164, 175, 192)), (645, (138, 108, 179))):
                self.assertEqual(pixel(x, 140), color)
            self.assertEqual(pixel(800, 70), (255, 255, 255))

    def test_zero_denominators_leave_empty_bars_and_null_scorecard(self):
        with TemporaryDirectory() as directory:
            stage, frames = setup_stage(Path(directory), True)
            render(stage, frames)
            svg = ET.parse(stage / 'figures/barrier-outcomes.svg').getroot()
            bars = [item for item in svg.findall('{http://www.w3.org/2000/svg}rect')
                    if item.attrib['height'] == '28']
            self.assertEqual([float(item.attrib['width']) for item in bars], [0.] * 8)
            _, _, pixel = png_pixels(stage / 'figures/barrier-outcomes.png')
            self.assertEqual(pixel(180, 70), (255, 255, 255))
            self.assertEqual(pixel(180, 140), (255, 255, 255))
            self.assertIn('| Return after departure | 0 / 0 | 0 | 0/0 (—) | unavailable |',
                          (stage / 'report.md').read_text())
            rows = json.loads((stage / 'publication.json').read_text())['sections'][0]['rows']
            for row in rows:
                self.assertEqual((row['events'], row['evaluable'], row['successes']), (0, 0, 0))
                self.assertIsNone(row['rate'])
                self.assertIsNone(row['ciLow'])
                self.assertIsNone(row['ciHigh'])

    def test_publication_schema_row_order_original_ratios_and_utc_clock(self):
        with TemporaryDirectory() as directory:
            stage, frames = setup_stage(Path(directory))
            with patch.object(report_rendering, 'datetime', FrozenDateTime):
                reporting.write_publication(stage, frames['cards'])
            data = (stage / 'publication.json').read_bytes()
            pub = json.loads(data)
            self.assertEqual(pub['publishedAt'], '2026-10-10T12:34:56Z')
            self.assertEqual(pub['id'], 'vwap-three-20261010t000000z-synthetic')
            self.assertEqual(pub['source'], {'producer': 'sahadeva', 'runId': STAGE_NAME})
            self.assertEqual([row['candidate'] for row in pub['sections'][0]['rows']],
                             ['Return after departure', 'First outside-2σ fade', 'First VWAP retest bounce'])
            self.assertEqual(pub['sections'][0]['rows'][0],
                             {'candidate': 'Return after departure', 'events': 9, 'evaluable': 8,
                              'successes': 5, 'rate': .625, 'sessions': 3, 'ciLow': .25, 'ciHigh': .875})
            self.assertIsNone(pub['sections'][0]['rows'][1]['ciLow'])
            self.assertEqual([column['key'] for column in pub['sections'][0]['columns']],
                             ['candidate', 'events', 'evaluable', 'sessions', 'successes', 'rate', 'ciLow', 'ciHigh'])
            self.assertEqual(pub['sections'][1]['path'], 'figures/barrier-outcomes.png')
            self.assertIn('Each bar uses its own evaluable-event denominator.', pub['sections'][1]['caption'])
            self.assertEqual(data, (json.dumps(pub, indent=2) + '\n').encode())

    def test_saved_evidence_facade_reads_partitions_for_existing_audit_and_warmup_callers(self):
        audit, warmup = caller('audit'), caller('warmup_sensitivity')
        with TemporaryDirectory() as directory:
            stage = Path(directory)
            (stage / 'events').mkdir()
            pd.DataFrame({'event_id': ['ES:B:2', 'ES:A:1'], 'direction': [-1, 1]}).to_parquet(
                stage / 'events/events_ES_2024.parquet', index=False)
            pd.DataFrame({'product': ['ES'], 'session_date': ['2024-01-02']}).to_parquet(
                stage / 'events/windows_ES_2024.parquet', index=False)
            for read in (audit.read_evidence, warmup.read_evidence):
                events, windows = read(stage)
                self.assertEqual(events.ordinal.tolist(), [2, 1])
                self.assertEqual(events.direction_label.tolist(), ['short', 'long'])
                self.assertEqual(windows['product'].tolist(), ['ES'])
            pd.DataFrame({'event_id': ['ES:B:2'], 'direction': [1]}).to_parquet(
                stage / 'events/events_ES_2025.parquet', index=False)
            pd.DataFrame({'product': ['ES'], 'session_date': ['2025-01-02']}).to_parquet(
                stage / 'events/windows_ES_2025.parquet', index=False)
            with self.assertRaisesRegex(ValueError, 'duplicate event ID'):
                audit.read_evidence(stage)

    def test_summary_caller_facade_orchestrates_precomputed_tables_and_actual_renderers(self):
        summarize = caller('summarize')
        with TemporaryDirectory() as directory, ExitStack() as patches:
            root = Path(directory).resolve()
            stage, frames = setup_stage(root / 'work/05_session_vwap')
            (stage / 'events').mkdir()
            partition = stage / 'events/events_fixture.parquet'
            partition.write_bytes(b'synthetic retained bytes; not a market partition')
            unused = pd.DataFrame({'precomputed': [7]})
            called = []
            tables = {'scorecards': frames['cards'], 'breakdown': frames['breaks'],
                      'stability_table': unused, 'horizon_table': frames['horizons'],
                      'landmark_table': unused, 'return_survival': unused, 'subset_table': unused,
                      'path_table': unused, 'cycle_table': frames['cycles'],
                      'departure_class_table': unused, 'window_population_table': unused,
                      'baseline': frames['controls'], 'examples': frames['samples'],
                      'sensitivity': unused, 'eligibility_table': unused,
                      'threshold_times': unused, 'exclusion_table': unused}
            def table(name, result):
                def saved(*args):
                    called.append(name)
                    return result
                return saved
            for name, frame in tables.items():
                patches.enter_context(patch.object(reporting, name, side_effect=table(name, frame)))
            patches.enter_context(patch.object(reporting, 'read_evidence',
                                               return_value=(frames['events'], frames['windows'])))
            paths = patches.enter_context(patch.object(reporting, 'load_workspace_paths',
                                                        return_value=Namespace(publication_root=root)))
            for name in ('write_figure', 'write_report', 'write_publication'):
                original = getattr(reporting, name)
                def renderer(*args, name=name, original=original):
                    called.append(name)
                    self.assertTrue((stage / 'tables/scorecards.csv').is_file())
                    self.assertEqual((stage / 'metrics.json').exists(), name != 'write_figure')
                    return original(*args)
                patches.enter_context(patch.object(reporting, name, side_effect=renderer))
            patches.enter_context(patch.object(report_rendering, 'datetime', FrozenDateTime))
            patches.enter_context(patch.object(summarize.argparse.ArgumentParser, 'parse_args',
                                               return_value=Namespace(workspace_root=root, run_id=STAGE_NAME)))
            summarize.main()
            self.assertEqual(called, list(tables) + ['write_figure', 'write_report', 'write_publication'])
            paths.assert_called_once_with(root)
            expected_tables = ('scorecards', 'breakdowns', 'stability', 'horizons', 'landmarks',
                               'return_survival', 'subsets', 'paths', 'cycles', 'departure_classes',
                               'window_populations', 'baselines', 'examples', 'sensitivity',
                               'eligibility', 'threshold_times', 'exclusions')
            self.assertEqual({path.stem for path in (stage / 'tables').glob('*.csv')}, set(expected_tables))
            saved_cards = pd.read_csv(stage / 'tables/scorecards.csv')
            self.assertEqual(saved_cards.strategy.tolist(), frames['cards'].strategy.tolist())
            self.assertEqual(saved_cards.evaluable.tolist(), [8, 8, 10, 99])
            for path, expected in OUTPUT_HASHES['populated'].items():
                self.assertEqual(sha256((stage / path).read_bytes()).hexdigest(), expected, path)
            metrics = json.loads((stage / 'metrics.json').read_text())
            self.assertEqual([row['id'] for row in metrics], ['c.all.primary', 'b.all.primary', 'a.all.primary', 'a.es.primary'])
            self.assertEqual(metrics[1]['denominator'], 8)
            self.assertEqual(metrics[1]['horizon'], 'window_end')
            self.assertEqual(metrics[2]['ci_95'], [None, None])
            manifest = json.loads((stage / 'events.manifest.json').read_text())
            self.assertEqual((manifest['row_count'], manifest['window_row_count']), (3, 3))
            self.assertEqual(manifest['partitions'], [{'path': 'events/events_fixture.parquet',
                                                      'sha256': sha256(partition.read_bytes()).hexdigest()}])
            self.assertEqual(partition.read_bytes(), b'synthetic retained bytes; not a market partition')


if __name__ == '__main__':
    unittest.main()
