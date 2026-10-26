"""Fresh-process checks for canonical consumer imports and explicit-root reads."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.parquet as pq


FORBIDDEN_MODULES = (
    "abacus_bhishma.continuous_phase1",
    "abacus_bhishma.continuous_phase2",
    "abacus_bhishma.derived_ohlcv_5m",
    "abacus_bhishma.session_anchored_vwap",
    "abacus_bhishma.gc_ema_bands",
    "abacus_bhishma.vp_hvn_release",
    "abacus_bhishma.vp_hvn",
    "abacus_bhishma.vp_hvn_native",
    "abacus_bhishma.databento_cli",
    "abacus_bhishma.daily_context",
    "abacus_bhishma.range_xv",
    "databento",
    "databento_dbn",
    "abacus_sahadeva",
    "studies",
    "legacy",
)

CHILD_CHECK = """
import importlib
import importlib.abc
import json
import os
from pathlib import Path
import subprocess
import sys

forbidden = tuple(json.loads(sys.argv[1]))
module_name = sys.argv[2]
root = Path(sys.argv[3])

def blocked(name):
    return any(name == entry or name.startswith(entry + '.') for entry in forbidden)

class LoaderBoundary(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if blocked(fullname):
            raise AssertionError('canonical loader attempted forbidden import: ' + fullname)

def no_external_tool(*args, **kwargs):
    raise AssertionError('canonical loader invoked an external subprocess tool')

sys.meta_path.insert(0, LoaderBoundary())
for name in ('Popen', 'run', 'call', 'check_call', 'check_output'):
    setattr(subprocess, name, no_external_tool)
for name in ('system', 'popen', 'posix_spawn', 'posix_spawnp', 'spawnv', 'spawnve'):
    if hasattr(os, name):
        setattr(os, name, no_external_tool)

module = importlib.import_module(module_name)
assert not any(blocked(name) for name in sys.modules), 'forbidden module loaded during import'
import pyarrow as pa
import pyarrow.dataset as ds

if module_name == 'abacus_bhishma.vp_hvn_loader':
    result = module.load_release(root, '1.0.0')
    assert isinstance(result, ds.Dataset)
    assert result.to_table().to_pydict() == {'value': [7, None]}
    assert result.schema.names == ['value']
elif module_name == 'abacus_bhishma.continuous_loader':
    result = module.open_continuous_dataset(root, 'nq', 'unadjusted')
    assert isinstance(result, ds.Dataset)
    assert result.to_table(columns=['close']).to_pydict() == {'close': [11, None]}
elif module_name == 'abacus_bhishma.feature_loader':
    for release in ('dridr_ohlcv_5m', 'gc_ema_deviation_bands'):
        result = module.load_gc_5m_release(root, release, version='1.0.0', columns=['open'])
        assert isinstance(result, pa.Table)
        assert result.to_pydict() == {'open': [1, 2]}
    result = module.load_session_anchored_vwap(
        root, 'nq', '5m', version='1.0.0', columns=['value'],
        start_date='2024-01-02', end_date='2024-01-03',
    )
    assert isinstance(result, pa.Table)
    assert result.to_pydict() == {'value': [13]}
else:
    raise AssertionError('unexpected test loader: ' + module_name)
assert not any(blocked(name) for name in sys.modules), 'forbidden module loaded during read'
print('canonical import and explicit-root read passed')
"""


def inventory(root):
    return {
        str(path.relative_to(root)): ("directory", None) if path.is_dir() else ("file", path.read_bytes())
        for path in sorted(root.rglob("*"))
    }


class LoaderImportBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "explicit-publication"
        self.cwd = self.base / "unrelated-cwd"
        self.cwd.mkdir()
        self.write_fixtures()

    def write_parquet(self, relative, table):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, path)
        return relative

    def write_fixtures(self):
        selected = self.write_parquet(
            "data/features/vp_hvn/version=1.0.0/snapshots/year=2024/part-000.parquet",
            pa.table({"value": pa.array([7, None], type=pa.int64())}),
        )
        manifest = self.root / "catalog/datasets/nq_causal_vp_hvn__1.0.0.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"output_files": [{"table": "snapshots", "path": selected}]}), encoding="utf-8")
        self.write_parquet(
            "data/curated/continuous/1m/product=NQ/roll=volume_lead_v1/variant=unadjusted/year=2024/part-000.parquet",
            pa.table({"close": pa.array([11, None], type=pa.int64())}),
        )
        for release in ("dridr_ohlcv_5m", "gc_ema_deviation_bands"):
            for year, value in ((2025, 2), (2024, 1)):
                self.write_parquet(
                    f"data/features/bars/5m/feature_set={release}/version=1.0.0/product=GC/year={year}/part-000.parquet",
                    pa.table({"open": pa.array([value], type=pa.int64())}),
                )
        self.write_parquet(
            "data/features/bars/5m/feature_set=session_anchored_vwap/version=1.0.0/product=NQ/year=2024/part-000.parquet",
            pa.table({"session_date": pa.array([date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)], type=pa.date32()),
                      "value": pa.array([12, 13, 14], type=pa.int64())}),
        )

    def assert_boundary(self, module_name):
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("ABACUS_") and key != "PYTHONPATH"}
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        before = inventory(self.base)
        completed = subprocess.run(
            [sys.executable, "-c", CHILD_CHECK, json.dumps(FORBIDDEN_MODULES), module_name, str(self.root)],
            cwd=self.cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stdout.strip(), "canonical import and explicit-root read passed")
        self.assertEqual(inventory(self.base), before)

    def test_vp_loader_import_and_read_are_thin(self):
        self.assert_boundary("abacus_bhishma.vp_hvn_loader")

    def test_continuous_loader_import_and_read_are_thin(self):
        self.assert_boundary("abacus_bhishma.continuous_loader")

    def test_feature_loader_import_and_reads_are_thin(self):
        self.assert_boundary("abacus_bhishma.feature_loader")


if __name__ == "__main__":
    unittest.main()
