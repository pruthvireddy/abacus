"""Declared source retention and publisher inventories use disposable bytes."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from abacus_bhishma import continuous_phase1 as phase1
from abacus_bhishma import continuous_phase2 as phase2
from abacus_bhishma import daily_context as daily
from abacus_bhishma import gc_ema_bands as gc
from abacus_bhishma import provenance
from abacus_bhishma import vp_hvn_release as vp


class RetainedSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "original.py"
        self.source.write_bytes(b"actual dirty helper bytes\x00\xff")

    def test_declared_source_and_lock_copies_match_hashes_and_scope(self):
        lock = self.root / "uv.lock"
        lock.write_bytes(b"prepared environment lock")
        target = self.root / "release/provenance"
        record = provenance.retain_sources(target, [("package/helper.py", self.source), ("uv.lock", lock)],
                                           artifact_id="synthetic-release", root=self.root)
        self.assertEqual(record["artifact_id"], "synthetic-release")
        self.assertIn("not dependency discovery or execution proof", record["scope"])
        self.assertEqual(json.loads((target / "sources.json").read_text()), record)
        for item in record["files"]:
            copied = target / item["path"]
            self.assertEqual(copied.stat().st_size, item["bytes"])
            self.assertEqual(provenance.sha256_file(copied), item["sha256"])
        self.assertEqual((target / "package/helper.py").read_bytes(), self.source.read_bytes())
        self.assertEqual((target / "uv.lock").read_bytes(), lock.read_bytes())

    def test_changed_helper_changes_declared_retention_independently(self):
        first = provenance.retain_sources(self.root / "one", [("helper.py", self.source)], artifact_id="one", root=self.root)
        self.source.write_bytes(b"modified helper")
        second = provenance.retain_sources(self.root / "two", [("helper.py", self.source)], artifact_id="two", root=self.root)
        self.assertNotEqual(first["files"][0]["sha256"], second["files"][0]["sha256"])
        self.assertEqual((self.root / "one/helper.py").read_bytes(), b"actual dirty helper bytes\x00\xff")

    def test_promotion_recheck_rejects_changed_original_and_changed_retained_copy(self):
        sources = [("helper.py", self.source)]
        target = self.root / "retained"
        retained = provenance.retain_sources(target, sources, artifact_id="test", root=self.root)
        provenance.verify_retained_sources(target, sources, retained)
        original = self.source.read_bytes()
        self.source.write_bytes(b"changed original")
        with self.assertRaisesRegex(ValueError, "source or retained copy changed"):
            provenance.verify_retained_sources(target, sources, retained)
        self.source.write_bytes(original)
        (target / "helper.py").write_bytes(b"changed retained copy")
        with self.assertRaisesRegex(ValueError, "source or retained copy changed"):
            provenance.verify_retained_sources(target, sources, retained)

    def test_existing_retention_and_missing_or_unsafe_source_refused(self):
        for label in ("", "../escape", "a/../escape", "/absolute", "a//b", "a\\b", "a:stream"):
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    provenance.retain_sources(self.root / "new", [(label, self.source)], artifact_id="test", root=self.root)
                self.assertFalse((self.root / "new").exists())
        for sources in ([("missing", self.root / "missing")], [("one", self.source), ("one", self.source)]):
            with self.assertRaises(ValueError):
                provenance.retain_sources(self.root / "new", sources, artifact_id="test", root=self.root)
        target = self.root / "existing"
        target.mkdir()
        (target / "keep").write_bytes(b"old evidence")
        with self.assertRaises(ValueError):
            provenance.retain_sources(target, [("helper.py", self.source)], artifact_id="test", root=self.root)
        self.assertEqual((target / "keep").read_bytes(), b"old evidence")

    def test_linked_source_ancestor_and_destination_ancestor_refused(self):
        linked = self.root / "linked"
        linked.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            provenance.retain_sources(self.root / "new", [("helper.py", linked / self.source.name)], artifact_id="test", root=self.root)
        with self.assertRaises(ValueError):
            provenance.retain_sources(linked / "new", [("helper.py", self.source)], artifact_id="test", root=self.root)

    def test_source_changes_during_copy_preserve_failed_snapshot(self):
        real_copy = provenance.shutil.copyfileobj
        def change_source(incoming, outgoing):
            real_copy(incoming, outgoing)
            self.source.write_bytes(b"changed during snapshot")
        with patch.object(provenance.shutil, "copyfileobj", side_effect=change_source):
            with self.assertRaisesRegex(ValueError, "changed during retention"):
                provenance.retain_sources(self.root / "failed", [("helper.py", self.source)], artifact_id="test", root=self.root)
        self.assertEqual((self.root / "failed/helper.py").read_bytes(), b"actual dirty helper bytes\x00\xff")
        self.assertFalse((self.root / "failed/sources.json").exists())

    def test_old_hash_helper_names_and_vp_string_arguments_remain_supported(self):
        expected = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.assertEqual(daily._sha256(self.source), expected)
        self.assertEqual(gc.sha256(self.source), expected)
        self.assertEqual(vp.sha256(str(self.source)), expected)

    def test_vp_explicit_source_list_contains_executed_loader_and_native_helpers(self):
        package = self.root / "packages/bhishma/src/abacus_bhishma"
        package.mkdir(parents=True)
        for name in vp.CODE_SOURCE_NAMES:
            (package / name).write_bytes(name.encode())
        (package / "vp_hvn_unrelated.tmp").write_bytes(b"not executed")
        records = vp._code_sources(self.root)
        self.assertEqual([Path(r["path"]).name for r in records], list(vp.CODE_SOURCE_NAMES))
        for name in ("continuous_loader.py", "manifest_selection.py", "provenance.py", "paths.py",
                     "publication_safety.py", "calendar.py", "vp_hvn_native.cpp"):
            self.assertIn(name, vp.CODE_SOURCE_NAMES)
        before = records
        (package / "continuous_loader.py").write_bytes(b"changed loader")
        after = vp._code_sources(self.root)
        self.assertNotEqual(before, after)
        self.assertEqual([r for r in before if "continuous_loader.py" not in r["path"]],
                         [r for r in after if "continuous_loader.py" not in r["path"]])

    def test_continuous_provenance_is_owned_without_claiming_shared_schedule_parent(self):
        for module, cls, error in ((phase1, phase1.ProjectPaths, phase1.Phase1Error),
                                   (phase2, phase2.Phase2Paths, phase2.Phase2Error)):
            with self.subTest(module=module.__name__):
                paths = cls.from_root(self.root)
                final = module._provenance_output(paths)
                final.mkdir(parents=True)
                (final / "retained.py").write_bytes(b"prior attempt")
                with self.assertRaises(error):
                    module._prepare_build(paths, force=True)
                self.assertEqual((final / "retained.py").read_bytes(), b"prior attempt")
                (final / "retained.py").unlink()
                final.rmdir()


if __name__ == "__main__":
    unittest.main()
