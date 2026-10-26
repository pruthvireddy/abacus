"""Disposable, explicit-root fixtures for opt-in pinned consumer loading."""

from datetime import date
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from abacus_bhishma.continuous_loader import continuous_path, open_continuous_dataset
from abacus_bhishma.feature_loader import load_gc_5m_release, load_session_anchored_vwap


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OneShotColumns:
    def __init__(self, values):
        self.values = values
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        if self.iterations != 1:
            raise AssertionError("column iterable consumed more than once")
        return iter(self.values)


class ManifestSelectedLoaderTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.manifest_path = self.root / 'catalog/selected.json'
        self.manifest_path.parent.mkdir()

    def parquet(self, relative, table):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, path)
        return {'path': relative, 'bytes': path.stat().st_size, 'sha256': digest(path)}

    def pin(self, manifest):
        self.manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        return {'manifest_path': self.manifest_path,
                'expected_manifest_sha256': digest(self.manifest_path)}

    def gc(self, release='gc_ema_deviation_bands'):
        records = []
        for year in (2025, 2024):
            values = {'value': pa.array([year, None], type=pa.int64())}
            if year == 2025:
                values['later'] = pa.array([1.5, None], type=pa.float64())
            records.append(self.parquet(
                f'data/features/bars/5m/feature_set={release}/version=1.0.0/product=GC/year={year}/part-000.parquet',
                pa.table(values)))
        manifest = {'feature_set': release, 'output_files': records}
        if release == 'dridr_ohlcv_5m':
            manifest.update(dataset_id='tv_indicators__dridr_ohlcv_5m__v1', feature_set_version='1.0.0')
        else:
            manifest.update(dataset_id='gc_ema_deviation_bands__1.0.0', version='1.0.0')
        return manifest

    def vwap(self, timeframe=5, product='GC'):
        record = self.parquet(
            f'data/features/bars/{timeframe}m/feature_set=session_anchored_vwap/version=1.0.0/product={product}/year=2024/part-000.parquet',
            pa.table({'session_date': pa.array([date(2024, 1, day) for day in (1, 2, 3, 4)], type=pa.date32()),
                      'value': pa.array([10, None, 30, 40], type=pa.int64())}))
        return {'dataset_id': f'session_anchored_vwap_{timeframe}m_v1', 'dataset_version': '1.0.0',
                'feature_set': 'session_anchored_vwap', 'release_id': 'session_anchored_vwap__1.0.0',
                'timeframe': f'{timeframe}m', 'output_files': [record]}

    def continuous(self, variant='unadjusted', product='NQ'):
        scope = continuous_path(self.root, product, variant).relative_to(self.root).as_posix()
        record = self.parquet(scope + '/year=2024/part-000.parquet',
                              pa.table({'close': pa.array([11, None, 13], type=pa.int64())}))
        manifest = {'algorithm_version': '1.0.0', 'adjusted': variant == 'back_adjusted',
                    'output_files': [record]}
        if variant == 'unadjusted':
            manifest.update(dataset='volume_lead_unadjusted_v1', methodology='volume_lead_v1')
        else:
            manifest.update(dataset='volume_lead_back_adjusted_v1', roll_methodology='volume_lead_v1',
                            adjustment_methodology='prior_session_close_additive_v1')
        return manifest

    def load_gc(self, **options):
        return load_gc_5m_release(self.root, 'gc_ema_deviation_bands', version='1.0.0', **options)

    def test_gc_both_families_keep_schema_promotion_and_ascending_path_order(self):
        for release in ('dridr_ohlcv_5m', 'gc_ema_deviation_bands'):
            with self.subTest(release=release):
                manifest = self.gc(release)
                expected = load_gc_5m_release(self.root, release, version='1.0.0')
                with patch('abacus_bhishma.feature_loader.pq.read_table', wraps=pq.read_table) as reads:
                    actual = load_gc_5m_release(self.root, release, version='1.0.0', **self.pin(manifest))
                self.assertTrue(actual.equals(expected, check_metadata=True))
                self.assertEqual(actual['value'].to_pylist(), [2024, None, 2025, None])
                self.assertEqual(actual['later'].to_pylist(), [None, None, 1.5, None])
                paths = [call.args[0] for call in reads.call_args_list]
                self.assertTrue(all(isinstance(path, Path) for path in paths))
                self.assertEqual(paths, sorted(paths))

    def test_gc_projection_generator_and_empty_projection_keep_legacy_behavior(self):
        pin = self.pin(self.gc())
        columns = OneShotColumns(['value'])
        actual = self.load_gc(columns=columns, **pin)
        self.assertEqual(columns.iterations, 1)
        self.assertEqual(actual.to_pydict(), {'value': [2024, None, 2025, None]})
        empty = OneShotColumns([])
        result = self.load_gc(columns=empty, **pin)
        self.assertEqual(empty.iterations, 1)
        self.assertTrue(result.equals(self.load_gc(columns=[]), check_metadata=True))

    def test_vwap_aliases_hive_schema_and_projected_away_date_boundaries(self):
        for minutes in (2, 5):
            pin = self.pin(self.vwap(minutes))
            for timeframe in (minutes, f'{minutes}m'):
                for product in ('GC', 'gc', 'Gc'):
                    with self.subTest(timeframe=timeframe, product=product):
                        legacy = load_session_anchored_vwap(self.root, product, timeframe, version='1.0.0')
                        pinned = load_session_anchored_vwap(self.root, product, timeframe, version='1.0.0', **pin)
                        self.assertTrue(pinned.equals(legacy, check_metadata=True))
                        self.assertEqual(pinned.schema.names, ['session_date', 'value', 'year'])
                        columns = OneShotColumns(['value'])
                        filtered = load_session_anchored_vwap(
                            self.root, product, timeframe, version='1.0.0', columns=columns,
                            start_date='2024-01-02', end_date=date(2024, 1, 4), **pin)
                        self.assertEqual(filtered.to_pydict(), {'value': [None, 30]})
                        self.assertEqual(columns.iterations, 1)

    def test_vwap_empty_projection_keeps_rows_and_schema_behavior(self):
        pin = self.pin(self.vwap())
        options = dict(version='1.0.0', columns=[], start_date='2024-01-02', end_date='2024-01-04')
        actual = load_session_anchored_vwap(self.root, 'GC', 5, **options, **pin)
        legacy = load_session_anchored_vwap(self.root, 'GC', 5, **options)
        self.assertTrue(actual.equals(legacy, check_metadata=True))

    def test_continuous_variants_remain_lazy_hive_datasets(self):
        for variant in ('unadjusted', 'back_adjusted'):
            with self.subTest(variant=variant):
                pin = self.pin(self.continuous(variant))
                sentinel = object()
                with patch('abacus_bhishma.continuous_loader.ds.dataset', return_value=sentinel) as factory:
                    self.assertIs(open_continuous_dataset(self.root, 'nq', variant, **pin), sentinel)
                self.assertEqual(factory.call_args.kwargs['partition_base_dir'],
                                 str(continuous_path(self.root, 'NQ', variant)))
                actual = open_continuous_dataset(self.root, 'nq', variant, **pin)
                self.assertIsInstance(actual, ds.Dataset)
                legacy = open_continuous_dataset(self.root, 'NQ', variant)
                self.assertTrue(actual.schema.equals(legacy.schema, check_metadata=True))
                self.assertEqual(actual.schema.names, ['close', 'year'])
                self.assertEqual(actual.scanner(columns=['close'], filter=ds.field('close') > 11).to_table().to_pydict(),
                                 {'close': [13]})

    def test_pin_options_must_be_paired_and_verification_requires_pin(self):
        pin = self.pin(self.gc())
        for options in ({'manifest_path': pin['manifest_path']},
                        {'expected_manifest_sha256': pin['expected_manifest_sha256']},
                        {'verify_selected_files': True}, {'verify_selected_files': 1},
                        {**pin, 'expected_manifest_sha256': 'latest'}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.load_gc(**options)

    def test_wrong_pin_refuses_before_arrow_or_column_consumption(self):
        pin = self.pin(self.gc())
        pin['expected_manifest_sha256'] = '0' * 64
        columns = OneShotColumns(['value'])
        with patch('abacus_bhishma.feature_loader.pq.read_table', side_effect=AssertionError('Arrow called')):
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                self.load_gc(columns=columns, **pin)
        self.assertEqual(columns.iterations, 0)

    def test_gc_wrong_identity_fields_refuse(self):
        for release in ('dridr_ohlcv_5m', 'gc_ema_deviation_bands'):
            manifest = self.gc(release)
            for field in ('dataset_id', 'feature_set', 'feature_set_version' if release == 'dridr_ohlcv_5m' else 'version'):
                with self.subTest(release=release, field=field):
                    invalid = {**manifest, field: 'wrong'}
                    with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                        load_gc_5m_release(self.root, release, version='1.0.0', **self.pin(invalid))

    def test_vwap_wrong_family_version_release_and_timeframe_refuse(self):
        manifest = self.vwap()
        for field in ('dataset_id', 'dataset_version', 'feature_set', 'release_id', 'timeframe'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'identity mismatch'):
                load_session_anchored_vwap(self.root, 'GC', 5, version='1.0.0',
                                          **self.pin({**manifest, field: 'wrong'}))

    def test_continuous_wrong_identity_and_boolean_types_refuse(self):
        for variant in ('unadjusted', 'back_adjusted'):
            manifest = self.continuous(variant)
            fields = ('dataset', 'adjusted', 'algorithm_version', 'methodology') if variant == 'unadjusted' else (
                'dataset', 'adjusted', 'algorithm_version', 'roll_methodology', 'adjustment_methodology')
            for field in fields:
                with self.subTest(variant=variant, field=field), self.assertRaisesRegex(ValueError, 'identity mismatch'):
                    open_continuous_dataset(self.root, 'NQ', variant, **self.pin({**manifest, field: 'wrong'}))
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                open_continuous_dataset(self.root, 'NQ', variant,
                                        **self.pin({**manifest, 'adjusted': int(manifest['adjusted'])}))

    def test_other_product_files_do_not_satisfy_requested_scope(self):
        manifest = self.vwap(product='ES')
        (self.root / manifest['output_files'][0]['path']).parent.parent.parent.joinpath('product=GC').mkdir()
        with self.assertRaisesRegex(ValueError, 'no manifest-listed files'):
            load_session_anchored_vwap(self.root, 'GC', 5, version='1.0.0', **self.pin(manifest))
        manifest = self.continuous(product='ES')
        with self.assertRaisesRegex(ValueError, 'no manifest-listed files'):
            open_continuous_dataset(self.root, 'NQ', **self.pin(manifest))

    def test_continuous_auxiliary_parquet_is_excluded_even_with_verification(self):
        manifest = self.continuous()
        auxiliary = self.root / 'data/curated/instruments/roll=volume_lead_v1/instrument_master.parquet'
        auxiliary.parent.mkdir(parents=True)
        auxiliary.write_bytes(b'invalid auxiliary Parquet is not a bar')
        manifest['output_files'].append({'path': auxiliary.relative_to(self.root).as_posix(),
                                         'bytes': 999, 'sha256': '0' * 64})
        actual = open_continuous_dataset(self.root, 'NQ', **self.pin(manifest), verify_selected_files=True)
        self.assertEqual(actual.files, [str(self.root / manifest['output_files'][0]['path'])])
        self.assertEqual(actual.to_table(columns=['close']).to_pydict(), {'close': [11, None, 13]})

    def test_unlisted_invalid_parquet_is_ignored_in_all_manifest_modes(self):
        cases = [(self.gc(), lambda pin: self.load_gc(**pin)),
                 (self.vwap(), lambda pin: load_session_anchored_vwap(self.root, 'GC', 5, version='1.0.0', **pin)),
                 (self.continuous(), lambda pin: open_continuous_dataset(self.root, 'NQ', **pin).to_table())]
        for manifest, load in cases:
            with self.subTest(dataset=manifest.get('dataset_id', manifest.get('dataset'))):
                sibling = self.root / manifest['output_files'][0]['path']
                sibling.with_name('unlisted.parquet').write_bytes(b'not Parquet')
                self.assertGreater(load(self.pin(manifest)).num_rows, 0)

    def test_duplicate_json_keys_and_file_records_refuse(self):
        manifest = self.gc()
        pin = self.pin(manifest)
        text = self.manifest_path.read_text().replace('"feature_set":', '"feature_set": "ignored", "feature_set":', 1)
        self.manifest_path.write_text(text)
        pin['expected_manifest_sha256'] = digest(self.manifest_path)
        with self.assertRaisesRegex(ValueError, 'duplicate manifest JSON key'):
            self.load_gc(**pin)
        manifest['output_files'].append(dict(manifest['output_files'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate manifest file record'):
            self.load_gc(**self.pin(manifest))

    def test_malformed_file_records_refuse_without_loading(self):
        manifest = self.gc()
        record = manifest['output_files'][0]
        invalids = [None, [], {}, {**record, 'bytes': True}, {**record, 'bytes': -1},
                    {**record, 'sha256': 'bad'}]
        for invalid in invalids:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.load_gc(**self.pin({**manifest, 'output_files': [invalid]}))
        for records in (None, {}, [], [record, 'not an object']):
            with self.subTest(records=records), self.assertRaises(ValueError):
                self.load_gc(**self.pin({**manifest, 'output_files': records}))

    def test_unsafe_listed_paths_refuse_including_unselected_records(self):
        manifest = self.gc()
        for path in ('../outside.parquet', '/outside.parquet', 'data//bad', 'data/./bad',
                     'data/../bad', 'data\\bad', 'https://example/x', 'data/bad\x00', 'data/\ud800'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                record = {**manifest['output_files'][0], 'path': path}
                self.load_gc(**self.pin({**manifest, 'output_files': [*manifest['output_files'], record]}))

    def test_selected_file_and_ancestor_symlinks_refuse(self):
        manifest = self.gc()
        path = self.root / manifest['output_files'][0]['path']
        retained = path.with_name('retained.parquet')
        path.rename(retained)
        path.symlink_to(retained)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.load_gc(**self.pin(manifest))
        path.unlink()
        path.symlink_to(path.with_name('missing.parquet'))
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.load_gc(**self.pin(manifest))
        path.unlink()
        retained.rename(path)
        year = path.parent
        moved = year.with_name('retained-year')
        year.rename(moved)
        year.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.load_gc(**self.pin(manifest))

    def test_missing_selected_file_fails_without_directory_fallback(self):
        manifest = self.gc()
        (self.root / manifest['output_files'][0]['path']).unlink()
        with self.assertRaises(FileNotFoundError):
            self.load_gc(**self.pin(manifest))

    def test_optional_selected_size_and_hash_verification_are_independent(self):
        manifest = self.gc()
        for key, value in (('bytes', 0), ('sha256', '0' * 64)):
            with self.subTest(key=key):
                records = [dict(item) for item in manifest['output_files']]
                records[0][key] = value
                pin = self.pin({**manifest, 'output_files': records})
                self.assertEqual(self.load_gc(columns=['value'], **pin).num_rows, 4)
                with self.assertRaisesRegex(ValueError, 'size/SHA-256 mismatch'):
                    self.load_gc(**pin, verify_selected_files=True)
        self.assertEqual(self.load_gc(**self.pin(manifest), verify_selected_files=True).num_rows, 4)

    def test_manifest_relative_path_and_explicit_external_copy_work(self):
        manifest = self.gc()
        pin = self.pin(manifest)
        pin['manifest_path'] = 'catalog/selected.json'
        self.assertEqual(self.load_gc(**pin).num_rows, 4)
        with TemporaryDirectory() as separate:
            copied = Path(separate).resolve() / 'selected.json'
            copied.write_bytes(self.manifest_path.read_bytes())
            self.assertEqual(self.load_gc(manifest_path=copied,
                                          expected_manifest_sha256=digest(copied)).num_rows, 4)

    def test_manifest_symlink_and_parent_symlink_refuse(self):
        manifest = self.gc()
        pin = self.pin(manifest)
        retained = self.manifest_path.with_name('retained.json')
        self.manifest_path.rename(retained)
        self.manifest_path.symlink_to(retained)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.load_gc(**pin)
        self.manifest_path.unlink()
        retained.rename(self.manifest_path)
        parent = self.manifest_path.parent
        parent.rename(self.root / 'retained-catalog')
        parent.symlink_to(self.root / 'retained-catalog', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.load_gc(**pin)

    def test_arrow_errors_from_selected_files_remain_visible(self):
        manifest = self.gc()
        (self.root / manifest['output_files'][0]['path']).write_bytes(b'bad parquet')
        with self.assertRaises(pa.ArrowInvalid):
            self.load_gc(**self.pin(manifest))

    def test_gc_missing_columns_and_incompatible_schema_errors_remain_visible(self):
        manifest = self.gc()
        pin = self.pin(manifest)
        with self.assertRaises(pa.ArrowInvalid):
            self.load_gc(columns=['later'], **pin)
        path = self.root / manifest['output_files'][0]['path']
        pq.write_table(pa.table({'value': ['incompatible']}), path)
        with self.assertRaises(pa.ArrowTypeError):
            self.load_gc(columns=['value'], **self.pin(manifest))

    def test_identity_failure_never_calls_directory_discovery(self):
        manifest = self.continuous()
        manifest['dataset'] = 'wrong family'
        with patch('abacus_bhishma.continuous_loader.ds.dataset', side_effect=AssertionError('directory fallback')):
            with self.assertRaises(ValueError):
                open_continuous_dataset(self.root, 'NQ', **self.pin(manifest))


if __name__ == '__main__':
    unittest.main()
