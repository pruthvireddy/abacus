from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from abacus_bhishma import vp_hvn_loader
from abacus_bhishma.vp_hvn_release import CODE_SOURCE_NAMES, _code_sources, load_release as compatible_load_release


TABLES = ("snapshots", "candidates", "decisions", "sessions", "rhythm")
SCHEMA = pa.schema([pa.field("value", pa.int64()), pa.field("label", pa.string())], metadata={b"fixture": b"vp"})


def inventory(root):
    return {
        str(path.relative_to(root)): ("directory", None) if path.is_dir() else ("file", path.read_bytes())
        for path in sorted(root.rglob("*"))
    }


class VPReleaseLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest_path = self.root / "catalog/datasets/nq_causal_vp_hvn__1.0.0.json"
        self.files = []
        # Reverse year order freezes the original manifest-selected ordering;
        # these path components must not become inferred partition columns.
        for table in TABLES:
            for year, values in ((2025, [2, None]), (2024, [1])):
                path = self.root / f"data/features/vp_hvn/version=1.0.0/{table}/product=NQ/year={year}/part-000.parquet"
                path.parent.mkdir(parents=True)
                pq.write_table(pa.Table.from_pydict({"value": values, "label": [table] * len(values)}, schema=SCHEMA), path)
                self.files.append({"table": table, "path": str(path.relative_to(self.root))})
        self.manifest_path.parent.mkdir(parents=True)
        self.write_manifest(self.files)

    def write_manifest(self, files):
        self.manifest_path.write_text(json.dumps({"output_files": files}), encoding="utf-8")

    def test_default_and_all_explicit_tables_preserve_lazy_schema_rows_and_order(self):
        before = inventory(self.root)
        for table in TABLES:
            with self.subTest(table=table):
                result = vp_hvn_loader.load_release(self.root, "1.0.0", table)
                self.assertIsInstance(result, ds.Dataset)
                self.assertTrue(result.schema.equals(SCHEMA, check_metadata=True))
                self.assertEqual(result.to_table().to_pydict(), {"value": [2, None, 1], "label": [table] * 3})
                self.assertEqual(result.files, [str(self.root / item["path"]) for item in self.files if item["table"] == table])
                self.assertNotIn("year", result.schema.names)
                self.assertNotIn("product", result.schema.names)
        self.assertEqual(vp_hvn_loader.load_release(self.root, "1.0.0").to_table().to_pydict(),
                         {"value": [2, None, 1], "label": ["snapshots"] * 3})
        self.assertEqual(inventory(self.root), before)

    def test_manifest_selected_files_only_and_arrow_scanning_projection(self):
        unlisted = self.root / "data/features/vp_hvn/version=1.0.0/snapshots/product=NQ/year=2025/unlisted.parquet"
        unlisted.write_bytes(b"not valid parquet and intentionally absent from manifest")
        before = inventory(self.root)
        result = vp_hvn_loader.load_release(str(self.root), "1.0.0")
        projected = result.scanner(columns=["label", "value"], filter=ds.field("value") >= 2).to_table()
        self.assertEqual(projected.column_names, ["label", "value"])
        self.assertEqual(projected.to_pydict(), {"label": ["snapshots"], "value": [2]})
        self.assertEqual(inventory(self.root), before)

    def test_factory_keeps_original_lazy_dataset_arguments(self):
        sentinel = object()
        with patch.object(vp_hvn_loader.ds, "dataset", return_value=sentinel) as factory:
            self.assertIs(vp_hvn_loader.load_release(self.root, "1.0.0"), sentinel)
        factory.assert_called_once_with(
            [str(self.root / item["path"]) for item in self.files if item["table"] == "snapshots"],
            format="parquet",
        )

    def test_compatibility_path_reexports_one_implementation_and_same_valid_result(self):
        self.assertIs(compatible_load_release, vp_hvn_loader.load_release)
        canonical = vp_hvn_loader.load_release(self.root, "1.0.0", "sessions")
        compatibility = compatible_load_release(self.root, "1.0.0", "sessions")
        self.assertIsInstance(compatibility, ds.Dataset)
        self.assertEqual(canonical.files, compatibility.files)
        self.assertTrue(canonical.to_table().equals(compatibility.to_table(), check_metadata=True))

    def test_valid_zero_row_parquet_with_schema_is_supported(self):
        path = self.root / self.files[0]["path"]
        pq.write_table(pa.Table.from_pylist([], schema=SCHEMA), path)
        self.write_manifest([self.files[0]])
        before = inventory(self.root)
        result = vp_hvn_loader.load_release(self.root, "1.0.0")
        self.assertTrue(result.schema.equals(SCHEMA, check_metadata=True))
        self.assertEqual(result.to_table().num_rows, 0)
        self.assertEqual(inventory(self.root), before)

    def test_invalid_version_or_table_is_explicit_before_manifest_access(self):
        absent_root = self.root / "absent"
        for version in ("latest", "2.0.0", None):
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, "unsupported VP/HVN version"):
                vp_hvn_loader.load_release(absent_root, version)
        for table in ("unknown", "", None):
            with self.subTest(table=table), self.assertRaisesRegex(ValueError, "unsupported VP/HVN table"):
                vp_hvn_loader.load_release(absent_root, "1.0.0", table)

    def test_supported_table_without_manifest_files_is_explicit(self):
        self.write_manifest([item for item in self.files if item["table"] != "snapshots"])
        before = inventory(self.root)
        with self.assertRaisesRegex(ValueError, "no manifest-listed files.*snapshots"):
            vp_hvn_loader.load_release(self.root, "1.0.0")
        self.assertEqual(inventory(self.root), before)

    def test_missing_manifest_and_missing_listed_file_remain_failures(self):
        with self.assertRaises(FileNotFoundError):
            vp_hvn_loader.load_release(self.root / "missing", "1.0.0")
        (self.root / self.files[0]["path"]).unlink()
        before = inventory(self.root)
        with self.assertRaises(FileNotFoundError):
            vp_hvn_loader.load_release(self.root, "1.0.0")
        self.assertEqual(inventory(self.root), before)

    def test_malformed_json_retains_decoder_failure(self):
        self.manifest_path.write_text("{ broken JSON", encoding="utf-8")
        before = inventory(self.root)
        with self.assertRaises(json.JSONDecodeError):
            vp_hvn_loader.load_release(self.root, "1.0.0")
        self.assertEqual(inventory(self.root), before)

    def test_invalid_parquet_retains_arrow_failure_with_file_context(self):
        path = self.root / self.files[0]["path"]
        path.write_bytes(b"not parquet")
        before = inventory(self.root)
        with self.assertRaises(pa.ArrowInvalid) as caught:
            vp_hvn_loader.load_release(self.root, "1.0.0")
        self.assertIn(path.name, str(caught.exception))
        self.assertEqual(inventory(self.root), before)

    def test_future_builder_source_provenance_includes_new_loader(self):
        package = self.root / "packages/bhishma/src/abacus_bhishma"
        package.mkdir(parents=True)
        for name in CODE_SOURCE_NAMES:
            (package / name).write_bytes(b"")
        before = inventory(self.root)
        records = _code_sources(self.root)
        self.assertIn(
            {"path": "packages/bhishma/src/abacus_bhishma/vp_hvn_loader.py",
             "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
            records,
        )
        self.assertEqual(inventory(self.root), before)


if __name__ == "__main__":
    unittest.main()
