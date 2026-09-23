from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from abacus_bhishma.paths import WorkspacePaths
from abacus_sahadeva.inputs import InputPinError, read_samples, sha256, verify_inputs


class InputPinsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.workspace = self.root / "new-workspace"
        self.publication = self.root / "original-publication"
        self.workspace.mkdir()
        self.publication.mkdir()
        self.paths = WorkspacePaths(self.workspace, self.publication)
        self.partition_name = (
            "data/features/bars/2m/feature_set=session_anchored_vwap/"
            "version=1.0.0/product=ES/year=2024/part-000.parquet"
        )
        partition = self.publication / self.partition_name
        partition.parent.mkdir(parents=True)
        pq.write_table(pa.table({
            "session_date": pa.array([date(2024, 1, 8)], pa.date32()),
            "ts_event": [datetime(2024, 1, 7, 23, 0, tzinfo=timezone.utc)],
            "available_at": [datetime(2024, 1, 7, 23, 2, tzinfo=timezone.utc)],
            "close": [4700.25],
        }), partition)
        manifest = {
            "dataset_id": "session_anchored_vwap_2m_v1",
            "dataset_version": "1.0.0",
            "timeframe": "2m",
            "products": {"ES": {"rows": 1}},
            "output_files": [{"path": self.partition_name, "sha256": sha256(partition)}],
        }
        self.dataset_record = self.catalog(
            "catalog/datasets/session_anchored_vwap_2m_v1.json", manifest
        )
        release = {
            "feature_set": "session_anchored_vwap",
            "version": "1.0.0",
            "release_id": "session_anchored_vwap__1.0.0",
            "datasets": {"2m": self.dataset_record},
        }
        release_record = self.catalog(
            "catalog/datasets/session_anchored_vwap__1.0.0.release.json", release
        )
        self.lock = {
            "schema_version": 1,
            "feature_set": "session_anchored_vwap",
            "version": "1.0.0",
            "release_manifest": release_record,
            "datasets": [{
                "dataset_id": manifest["dataset_id"],
                "timeframe": "2m",
                "manifest_path": self.dataset_record["path"],
                "manifest_sha256": self.dataset_record["sha256"],
            }],
        }
        self.save_lock()

    def catalog(self, relative: str, value: dict) -> dict:
        content = json.dumps(value, sort_keys=True).encode()
        for root in (self.workspace, self.publication):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return {"path": relative, "sha256": sha256(self.publication / relative)}

    def save_lock(self):
        (self.workspace / "inputs.lock.json").write_text(json.dumps(self.lock))

    def test_relocated_workspace_reads_original_pinned_release(self):
        verified = verify_inputs(self.paths, "inputs.lock.json")
        samples = read_samples(self.paths, verified)
        self.assertEqual(samples[0]["session_date"], "2024-01-08")
        self.assertEqual(samples[0]["rows"], 1)
        self.assertEqual(len(verified["checked_files"]), 4)

    def test_changed_publication_manifest_is_rejected(self):
        (self.publication / self.dataset_record["path"]).write_text("{}")
        with self.assertRaisesRegex(InputPinError, "SHA-256 mismatch"):
            verify_inputs(self.paths, "inputs.lock.json")

    def test_changed_workspace_catalog_copy_is_rejected(self):
        (self.workspace / self.dataset_record["path"]).write_text("{}")
        with self.assertRaisesRegex(InputPinError, "SHA-256 mismatch"):
            verify_inputs(self.paths, "inputs.lock.json")

    def test_missing_explicit_version_is_rejected(self):
        self.lock.pop("version")
        self.save_lock()
        with self.assertRaisesRegex(InputPinError, "explicitly supported"):
            verify_inputs(self.paths, "inputs.lock.json")

    def test_dataset_identity_must_agree_with_pinned_manifest(self):
        self.lock["datasets"][0]["dataset_id"] = "wrong_dataset"
        self.save_lock()
        with self.assertRaisesRegex(InputPinError, "identity differs"):
            verify_inputs(self.paths, "inputs.lock.json")

    def test_partition_tampering_is_rejected_before_sample_read(self):
        verified = verify_inputs(self.paths, "inputs.lock.json")
        (self.publication / self.partition_name).write_bytes(b"changed")
        with self.assertRaisesRegex(InputPinError, "SHA-256 mismatch"):
            read_samples(self.paths, verified)

    def test_pinned_paths_cannot_escape_publication_root(self):
        self.lock["release_manifest"]["path"] = "../outside.json"
        self.save_lock()
        with self.assertRaisesRegex(InputPinError, "escapes its root"):
            verify_inputs(self.paths, "inputs.lock.json")


if __name__ == "__main__":
    unittest.main()
