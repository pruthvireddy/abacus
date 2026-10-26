from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("verify_storage", Path(__file__).resolve().parents[1] / "verify-storage.py")
assert SPEC is not None and SPEC.loader is not None
storage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(storage)


class StorageVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()
        self.root = self.parent / "workspace"
        self.original = self.parent / "original"
        self.root.mkdir()
        self.original.mkdir()
        (self.root / "data/empty").mkdir(parents=True)
        (self.original / "empty").mkdir()
        self.files = []
        for source, destination, content in [
            ("a.bin", "data/a.bin", b"abc"),
            ("README.md", "legacy/bhishma/data-readme.md", b"original readme"),
        ]:
            target = self.root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            (self.original / source).write_bytes(content)
            self.files.append({"group": "bhishma", "source_relative": source, "destination": destination, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
        (self.root / "legacy/bhishma/data").symlink_to("../../data")
        self.manifest = {
            "schema_version": 1,
            "groups": [{"id": "bhishma", "source_root": str(self.original), "destination_root": "data", "files": len(self.files), "bytes": sum(item["bytes"] for item in self.files), "directories": ["empty"]}],
            "files": self.files, "total_files": len(self.files), "total_bytes": sum(item["bytes"] for item in self.files),
            "internal_links": [{"path": "legacy/bhishma/data", "target": "../../data"}],
        }
        self.path = self.root / storage.DEFAULT_MANIFEST
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.manifest))

    def test_default_is_independent_and_allows_extra_destination_files(self):
        self.original.rename(self.parent / "unavailable-original")
        (self.root / "data/new-future-file").write_text("future")
        result = storage.verify(self.root)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["files_verified"], 2)
        self.assertEqual(result["bytes_checked"], self.manifest["total_bytes"])
        self.assertEqual(result["source_files_checked"], 0)
        self.assertEqual(result["internal_links_checked"], 1)

    def test_corruption_and_missing_file_are_reported(self):
        (self.root / "data/a.bin").write_bytes(b"bad")
        (self.root / "legacy/bhishma/data-readme.md").unlink()
        result = storage.verify(self.root)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["files_checked"], 2)
        self.assertEqual(len(result["failures"]), 2)
        self.assertIn("SHA-256", result["failures"][0]["reason"])

    def test_external_file_symlink_is_rejected_even_with_matching_content(self):
        target = self.root / "data/a.bin"
        target.unlink()
        target.symlink_to(self.original / "a.bin")
        result = storage.verify(self.root)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("escapes" in item["reason"] for item in result["failures"]))

    def test_internal_link_must_match_exist_and_stay_inside_workspace(self):
        link = self.root / "legacy/bhishma/data"
        for target, expected, reason in [
            ("../../data/empty", "../../data", "differs"),
            ("../../missing", "../../missing", "missing"),
            ("../../../original", "../../../original", "escapes"),
        ]:
            with self.subTest(target=target):
                link.unlink()
                link.symlink_to(target)
                self.manifest["internal_links"][0]["target"] = expected
                self.save()
                result = storage.verify(self.root)
                self.assertEqual(result["status"], "fail")
                self.assertTrue(any(reason in item["reason"] for item in result["failures"]), result)

    def test_missing_empty_directory_and_invalid_manifest_fail_cleanly(self):
        (self.root / "data/empty").rmdir()
        result = storage.verify(self.root)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("directory" in item["reason"] for item in result["failures"]))
        self.path.write_text('{"schema_version":1,"groups":false}')
        output = io.StringIO()
        with redirect_stdout(output):
            code = storage.main(["--workspace-root", str(self.root)])
        self.assertEqual(code, 1)
        result = json.loads(output.getvalue())
        self.assertIn("invalid manifest", result["failures"][0]["reason"])
        self.manifest["files"][0]["destination"] = "../original/a.bin"
        self.save()
        self.assertIn("invalid manifest", storage.verify(self.root)["failures"][0]["reason"])

    def test_optional_original_verification_checks_inventory_and_hashes(self):
        result = storage.verify(self.root, verify_sources=True)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["source_files_checked"], 2)
        (self.original / "extra.bin").write_bytes(b"extra")
        (self.original / "a.bin").write_bytes(b"bad")
        result = storage.verify(self.root, verify_sources=True)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("inventory" in item["reason"] for item in result["failures"]))
        self.assertTrue(any("SHA-256" in item["reason"] for item in result["failures"]))

    def test_clock_repair_crosswalk_keeps_original_inventory_verifiable(self):
        migrated = []
        for index in range(7):
            name = f"clock-{index}.csv"
            destination = f"data/range_xv/{name}"
            old = f"old-{index}".encode()
            new = f"new-{index}".encode()
            target = self.root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(new)
            (self.original / name).write_bytes(old)
            self.files.append({"group": "bhishma", "source_relative": name, "destination": destination,
                               "bytes": len(old), "sha256": hashlib.sha256(old).hexdigest()})
            migrated.append({"collection": "old", "path": destination,
                             "old_bytes": len(old), "old_sha256": hashlib.sha256(old).hexdigest(),
                             "enhanced_bytes": len(new), "enhanced_sha256": hashlib.sha256(new).hexdigest()})
        manifest_name = "data/range_xv/range_xv_exports_manifest.json"
        old_manifest = b"old manifest"
        new_manifest = b"new manifest"
        (self.root / manifest_name).write_bytes(new_manifest)
        (self.original / "range_xv_exports_manifest.json").write_bytes(old_manifest)
        self.files.append({"group": "bhishma", "source_relative": "range_xv_exports_manifest.json",
                           "destination": manifest_name, "bytes": len(old_manifest),
                           "sha256": hashlib.sha256(old_manifest).hexdigest()})
        readme_name = "data/range_xv/README.md"
        old_readme, new_readme = b"old readme", b"new readme"
        (self.root / readme_name).write_bytes(new_readme)
        (self.original / "range_xv_README.md").write_bytes(old_readme)
        self.files.append({"group": "bhishma", "source_relative": "range_xv_README.md",
                           "destination": readme_name, "bytes": len(old_readme),
                           "sha256": hashlib.sha256(old_readme).hexdigest()})
        self.manifest["groups"][0]["files"] = len(self.files)
        self.manifest["groups"][0]["bytes"] = sum(item["bytes"] for item in self.files)
        self.manifest["total_files"] = len(self.files)
        self.manifest["total_bytes"] = sum(item["bytes"] for item in self.files)
        self.save()
        legacy = self.root / "legacy/sahadeva/data/range_xv_exports_manifest.json"
        legacy.parent.mkdir(parents=True)
        legacy.symlink_to("../../../data/range_xv/range_xv_exports_manifest.json")
        (legacy.parent / "README.md").symlink_to("../../../data/range_xv/README.md")
        repair = self.root / storage.CLOCK_REPAIR
        repair.write_text(json.dumps({"schema_version": 1, "files": migrated,
                                      "old_manifest_sha256": hashlib.sha256(old_manifest).hexdigest(),
                                      "new_manifest_sha256": {"old": hashlib.sha256(new_manifest).hexdigest(),
                                                              "legacy": hashlib.sha256(new_manifest).hexdigest()},
                                      "documentation_changes": [{"path": readme_name,
                                                                  "old_sha256": hashlib.sha256(old_readme).hexdigest(),
                                                                  "old_bytes": len(old_readme),
                                                                  "new_sha256": hashlib.sha256(new_readme).hexdigest(),
                                                                  "new_bytes": len(new_readme),
                                                                  "legacy_link": "legacy/sahadeva/data/README.md"}]}))
        result = storage.verify(self.root, verify_sources=True)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["clock_normalized_files"], 9)
        (self.root / migrated[0]["path"]).write_bytes(b"tampered")
        self.assertEqual(storage.verify(self.root)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
