"""Synthetic compatibility checks for the existing eager feature loaders."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

from abacus_bhishma.feature_loader import (
    load_gc_5m_release,
    load_session_anchored_vwap,
    session_anchored_vwap_path,
)


def tree(root: Path) -> dict[str, bytes | None]:
    return {str(path.relative_to(root)): None if path.is_dir() else path.read_bytes()
            for path in sorted(root.rglob("*"))}


class OneShotColumns:
    def __init__(self, names):
        self.names = tuple(names)
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        if self.iterations != 1:
            raise AssertionError("column iterable consumed more than once")
        return iter(self.names)


class GCReleaseLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        # Creation order deliberately differs from required loading order.
        for release in ("gc_ema_deviation_bands", "dridr_ohlcv_5m"):
            for year in (2026, 2025):
                target = self.partition(release, year)
                target.parent.mkdir(parents=True)
                values = {
                    "row_id": pa.array([year * 100 + 1, year * 100 + 2], type=pa.int64()),
                    "band": pa.array([1.25, None] if year == 2026 else [None, 2.5], type=pa.float64()),
                    "promoted": pa.array([7, 8], type=pa.int32()) if year == 2026 else pa.nulls(2),
                }
                if year == 2026:
                    values["later_only"] = pa.array(["x", "y"])
                pq.write_table(pa.table(values), target)

    def partition(self, release, year):
        return (self.root / "data/features/bars/5m" / f"feature_set={release}"
                / "version=1.0.0/product=GC" / f"year={year}" / "part-000.parquet")

    def load(self, release="gc_ema_deviation_bands", *, version="1.0.0", columns=None):
        before = tree(self.root)
        try:
            return load_gc_5m_release(self.root, release, version=version, columns=columns)
        finally:
            self.assertEqual(tree(self.root), before)

    def assert_projection(self, result) -> None:
        self.assertIsInstance(result, pa.Table)
        self.assertEqual(result.num_rows, 4)
        self.assertEqual(result.column_names, ["band", "row_id"])
        self.assertEqual(result.schema.types, [pa.float64(), pa.int64()])
        self.assertEqual(result.to_pydict(), {
            "band": [None, 2.5, 1.25, None],
            "row_id": [202501, 202502, 202601, 202602],
        })

    def test_list_tuple_and_generator_project_all_rows_in_year_order(self) -> None:
        for release in ("gc_ema_deviation_bands", "dridr_ohlcv_5m"):
            for kind in ("list", "tuple", "generator"):
                with self.subTest(release=release, kind=kind):
                    names = ["band", "row_id"]
                    columns = names if kind == "list" else tuple(names) if kind == "tuple" else (x for x in names)
                    self.assert_projection(self.load(release, columns=columns))

    def test_original_iterable_is_consumed_exactly_once(self) -> None:
        columns = OneShotColumns(["band", "row_id"])
        self.assert_projection(self.load(columns=columns))
        self.assertEqual(columns.iterations, 1)

    def test_none_preserves_all_columns_schema_promotion_and_partition_behavior(self) -> None:
        result = self.load(columns=None)
        # Frozen against the original read_table(Path) strategy before this fix:
        # these single-file reads return physical fields without inferred Hive fields.
        self.assertEqual(result.column_names, ["row_id", "band", "promoted", "later_only"])
        self.assertEqual(result.schema.types, [pa.int64(), pa.float64(), pa.int32(), pa.string()])
        self.assertEqual(result.to_pydict(), {
            "row_id": [202501, 202502, 202601, 202602],
            "band": [None, 2.5, 1.25, None],
            "promoted": [None, None, 7, 8],
            "later_only": [None, None, "x", "y"],
        })

    def test_explicit_empty_projection_preserves_zero_rows_and_columns(self) -> None:
        # concat_tables of the original zero-column reads returns zero rows.
        for columns in ([], (), (x for x in ())):
            with self.subTest(columns=type(columns).__name__):
                result = self.load(columns=columns)
                self.assertIsInstance(result, pa.Table)
                self.assertEqual(result.num_rows, 0)
                self.assertEqual(result.num_columns, 0)
                self.assertEqual(result.schema, pa.schema([]))

    def test_release_version_and_missing_files_fail_before_consuming_columns(self) -> None:
        for release, version, error in (
            ("other", "1.0.0", ValueError),
            ("gc_ema_deviation_bands", "latest", ValueError),
            ("gc_ema_deviation_bands", "2.0.0", ValueError),
        ):
            with self.subTest(release=release, version=version):
                columns = OneShotColumns(["row_id"])
                with self.assertRaises(error):
                    self.load(release, version=version, columns=columns)
                self.assertEqual(columns.iterations, 0)
        for year in (2025, 2026):
            self.partition("gc_ema_deviation_bands", year).unlink()
        columns = OneShotColumns(["row_id"])
        with self.assertRaises(FileNotFoundError):
            self.load(columns=columns)
        self.assertEqual(columns.iterations, 0)

    def test_missing_requested_column_keeps_arrow_error(self) -> None:
        with self.assertRaises(pa.ArrowInvalid):
            self.load(columns=["not_a_column"])
        # A physically absent selected field in the first year is also an error;
        # promotion applies only after successful partition reads.
        with self.assertRaises(pa.ArrowInvalid):
            self.load(columns=["later_only"])

    def test_incompatible_partition_types_keep_arrow_error(self) -> None:
        pq.write_table(pa.table({"row_id": ["incompatible"], "band": [1.0]}),
                       self.partition("gc_ema_deviation_bands", 2026))
        with self.assertRaises(pa.ArrowTypeError):
            self.load(columns=["row_id"])

    def test_invalid_parquet_keeps_underlying_arrow_failure(self) -> None:
        self.partition("gc_ema_deviation_bands", 2026).write_bytes(b"invalid parquet")
        with self.assertRaises(pa.ArrowInvalid):
            self.load(columns=["row_id"])

    def test_gc_loader_requires_explicit_version(self) -> None:
        with self.assertRaises(TypeError):
            load_gc_5m_release(self.root, "gc_ema_deviation_bands")


class VWAPLoaderCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for timeframe in (2, 5):
            target = (self.root / f"data/features/bars/{timeframe}m"
                      / "feature_set=session_anchored_vwap/version=1.0.0/product=GC"
                      / "year=2025/part-000.parquet")
            target.parent.mkdir(parents=True)
            pq.write_table(pa.table({
                "session_date": pa.array([date(2025, 1, day) for day in (1, 2, 3, 4)], type=pa.date32()),
                "value": pa.array([10, 20, 30, 40], type=pa.int64()),
                "nullable": pa.array([None, 2.5, None, 4.5], type=pa.float64()),
            }), target)

    def load(self, product="GC", timeframe="5m", *, version="1.0.0", **options):
        before = tree(self.root)
        try:
            return load_session_anchored_vwap(self.root, product, timeframe, version=version, **options)
        finally:
            self.assertEqual(tree(self.root), before)

    def test_product_normalization_and_existing_timeframe_aliases(self) -> None:
        for product in ("gc", "Gc", "GC"):
            for timeframe in ("2m", 2, "5m", 5):
                with self.subTest(product=product, timeframe=timeframe):
                    result = self.load(product, timeframe, columns=["value"])
                    self.assertIsInstance(result, pa.Table)
                    self.assertEqual(result.to_pydict(), {"value": [10, 20, 30, 40]})

    def test_session_date_bounds_filter_when_date_is_projected_away(self) -> None:
        for start, end in ((date(2025, 1, 2), date(2025, 1, 4)), ("2025-01-02", "2025-01-04")):
            with self.subTest(start=start):
                result = self.load(start_date=start, end_date=end, columns=(x for x in ["nullable", "value"]))
                self.assertEqual(result.column_names, ["nullable", "value"])
                self.assertEqual(result.schema.types, [pa.float64(), pa.int64()])
                self.assertEqual(result.to_pydict(), {"nullable": [2.5, None], "value": [20, 30]})

    def test_version_is_required_and_unsupported_arguments_keep_failures(self) -> None:
        with self.assertRaises(TypeError):
            load_session_anchored_vwap(self.root, "GC", "5m")
        for options in ({"version": "latest"}, {"timeframe": "1m"}, {"product": "CL"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.load(**options)
        with self.assertRaises(FileNotFoundError):
            self.load(product="NQ")
        with self.assertRaises(FileNotFoundError):
            session_anchored_vwap_path(self.root / "missing", "5m", version="1.0.0")


if __name__ == "__main__":
    unittest.main()
