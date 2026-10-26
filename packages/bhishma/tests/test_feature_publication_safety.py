"""Publication refusal/failure fixtures never use configured historical storage."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from abacus_bhishma import daily_context as daily
from abacus_bhishma import derived_ohlcv_5m as derived
from abacus_bhishma import gc_ema_bands as gc
from abacus_bhishma import session_anchored_vwap as vwap
from abacus_bhishma import vp_hvn_release as vp
from abacus_bhishma.publication_safety import check_absent, check_path, write_new_bytes


def write(path, data=b"immutable sentinel\x00\xff"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def inventory(root):
    return {str(p.relative_to(root)): ("link", os.readlink(p)) if p.is_symlink() else
            ("directory", None) if p.is_dir() else ("file", p.read_bytes())
            for p in sorted(root.rglob("*"))}


class FeaturePublicationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "publication"
        self.workspace = self.base / "workspace"
        self.root.mkdir()
        self.workspace.mkdir()
        self.pine_sha = hashlib.sha256(b"synthetic Pine source").hexdigest()
        pin = patch.object(vp, "SOURCE_SHA", self.pine_sha)
        pin.start()
        self.addCleanup(pin.stop)

    def cases(self):
        dp = derived.DeliveryPaths.from_root(self.root)
        wp = vwap.Paths.from_root(self.root)
        daily_meta = [self.root / f"catalog/{kind}/{daily.DATASET_ID}.json" for kind in ("datasets", "schemas")]
        gc_meta = [self.root / f"catalog/{kind}/{gc.DATASET_ID}.json" for kind in ("datasets", "indicators")]
        gc_meta.append(self.root / f"reports/quality/{gc.DATASET_ID}.md")
        return [
            ("daily", lambda: daily.publish_daily_context(self.base / "input", self.root),
             [self.root / f"data/features/bars/1d/feature_set={daily.FEATURE_SET}/version=1.0.0", *daily_meta,
              *(p.with_name(p.name + ".part") for p in daily_meta)], FileExistsError,
             patch.object(daily, "_sha256", side_effect=AssertionError("heavy hashing ran"))),
            ("gc", lambda: gc.publish(self.root),
             [self.root / f"data/features/bars/5m/feature_set={gc.FEATURE_SET}/version=1.0.0",
              self.root / f"work/bhishma/{gc.DATASET_ID}", *gc_meta,
              *(p.with_name(p.name + ".part") for p in gc_meta)], FileExistsError,
             patch.object(gc.json, "loads", side_effect=AssertionError("source reader ran"))),
            ("derived", lambda: derived.build(self.root, self.base / "request.yaml"),
             [dp.output_root, dp.temporary_output_root, dp.request_snapshot, dp.manifest, dp.quality_report,
              *(p.with_name(p.name + ".part") for p in (dp.request_snapshot, dp.manifest, dp.quality_report))],
             derived.DeliveryError,
             patch.object(derived, "_load_yaml_with_ruby", side_effect=AssertionError("Ruby request reader ran"))),
            ("vwap", lambda: vwap.build(self.root),
             [*[wp.output_root(i) for i in (2, 5)], *[wp.output_root(i, True) for i in (2, 5)],
              *[wp.manifest(i) for i in (2, 5)], wp.release_manifest, wp.audit, wp.schema, wp.report,
              *[p.with_name(f".{p.name}.123.tmp") for p in
                (*[wp.manifest(i) for i in (2, 5)], wp.release_manifest, wp.schema, wp.report)]],
             vwap.FeatureBuildError,
             patch.object(vwap, "_verify_inputs", side_effect=AssertionError("input reader ran"))),
            ("vp", lambda: vp.publish(self.root, self.workspace),
             [*[p for _, p in vp._publication_outputs(self.root, self.workspace)],
              self.workspace / f"work/bhishma/{vp.DATASET_ID}",
              *[p.with_name(p.name + ".part") for _, p in vp._publication_outputs(self.root, self.workspace)[1:]]],
             FileExistsError, patch.object(vp, "build", side_effect=AssertionError("native replay ran"))),
        ]

    def test_each_owned_destination_refused_before_heavy_readers(self):
        for name, action, outputs, error, blocker in self.cases():
            with blocker:
                for output in outputs:
                    with self.subTest(publisher=name, output=output):
                        write(output)
                        before = inventory(self.base)
                        with self.assertRaises(error):
                            action()
                        self.assertEqual(inventory(self.base), before)
                        output.unlink()

    def test_broken_owned_leaves_refused_and_preserved(self):
        for name, action, outputs, error, blocker in self.cases():
            with blocker:
                for output in outputs:
                    with self.subTest(publisher=name, output=output):
                        output.parent.mkdir(parents=True, exist_ok=True)
                        output.symlink_to(self.base / "absent")
                        before = inventory(self.base)
                        with self.assertRaises(error):
                            action()
                        self.assertEqual(inventory(self.base), before)
                        output.unlink()

    def test_linked_and_non_directory_output_ancestors_refused(self):
        for name, action, _, error, blocker in self.cases():
            for kind in ("file", "link", "broken_link"):
                with self.subTest(publisher=name, ancestor=kind), blocker:
                    parent = self.root / "data"
                    if kind == "file":
                        write(parent)
                    else:
                        parent.symlink_to(self.workspace if kind == "link" else self.base / "absent")
                    before = inventory(self.base)
                    with self.assertRaises(error):
                        action()
                    self.assertEqual(inventory(self.base), before)
                    parent.unlink()

    def test_required_specifications_are_inputs_not_owned_outputs(self):
        for path in (self.root / f"catalog/indicators/{vp.DATASET_ID}.spec.json",
                     self.root / f"catalog/indicators/{vp.DATASET_ID}.source.pine",
                     self.workspace / f"requests/inbox/{vp.DATASET_ID}.yaml"):
            write(path)
        vp._check_publication_absent(self.root, self.workspace)
        paths = vwap.Paths.from_root(self.root)
        for path in (paths.request, paths.calendar, paths.indicator, paths.source_manifest):
            write(path)
        vwap._check_publication_absent(paths)
        write(self.root / f"catalog/indicators/{daily.DATASET_ID}.json")
        # The existing specification must survive the static destination gate.
        with patch.object(daily, "SOURCE_FILES", {}), patch.object(daily, "_sha256"):
            with patch.object(daily._provenance, "retain_sources", side_effect=RuntimeError("after gate")):
                with self.assertRaisesRegex(RuntimeError, "after gate"):
                    daily.publish_daily_context(self.base / "input", self.root)

    def daily_dynamic(self):
        source = self.base / "input"
        source.mkdir()
        for filename, _, _ in daily.SOURCE_FILES.values():
            write(source / filename, b"synthetic CSV")
        hashes = {asset: daily._sha256(source / record[0]) for asset, record in daily.SOURCE_FILES.items()}
        batch_hash = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]
        raw = self.root / f"data/raw/tradingview/chart_exports/1d/20261010-{batch_hash}"
        stage = self.root / f"data/features/bars/1d/feature_set={daily.FEATURE_SET}/.{daily.FEATURE_SET}-{batch_hash}.part"
        return source, raw, stage

    def test_daily_exact_raw_batch_copies_manifest_and_stage_refused_before_parse(self):
        source, raw, stage = self.daily_dynamic()
        outputs = [raw, raw / "batch_manifest.json", raw / "batch_manifest.json.part", stage,
                   *[raw / p.name for p in source.iterdir()]]
        for output in outputs:
            with self.subTest(output=output):
                write(output)
                before = inventory(self.base)
                with patch.object(daily, "datetime") as clock, patch.object(daily, "_parse_source", side_effect=AssertionError("parse ran")):
                    clock.now.return_value = datetime(2026, 10, 10, tzinfo=timezone.utc)
                    with self.assertRaises(FileExistsError):
                        daily.publish_daily_context(source, self.root)
                self.assertEqual(inventory(self.base), before)
                output.unlink()
                # Test each raw leaf independently rather than an old empty batch.
                for parent in (raw, stage):
                    if parent.exists() and parent.is_dir() and not list(parent.iterdir()):
                        parent.rmdir()

    def test_daily_failed_parse_retains_exact_stage_and_unrelated_sibling(self):
        source, _, stage = self.daily_dynamic()
        sibling = stage.with_name("unrelated-scratch")
        write(sibling / "keep.bin")
        with patch.object(daily, "datetime") as clock, patch.object(daily, "_parse_source", side_effect=ValueError("bad CSV")):
            clock.now.return_value = datetime(2026, 10, 10, tzinfo=timezone.utc)
            with self.assertRaisesRegex(ValueError, "bad CSV"):
                daily.publish_daily_context(source, self.root)
        self.assertTrue((stage / "provenance/sources.json").is_file())
        self.assertEqual((sibling / "keep.bin").read_bytes(), b"immutable sentinel\x00\xff")
        before = inventory(self.base)
        with patch.object(daily, "datetime") as clock:
            clock.now.return_value = datetime(2026, 10, 10, tzinfo=timezone.utc)
            with self.assertRaises(FileExistsError):
                daily.publish_daily_context(source, self.root)
        self.assertEqual(inventory(self.base), before)

    def test_daily_known_raw_ancestors_refused_before_source_hashing(self):
        source, _, _ = self.daily_dynamic()
        raw_parent = self.root / "data/raw"
        for kind in ("file", "link"):
            with self.subTest(kind=kind):
                if kind == "file":
                    write(raw_parent)
                else:
                    raw_parent.symlink_to(self.workspace, target_is_directory=True)
                before = inventory(self.base)
                with patch.object(daily, "_sha256", side_effect=AssertionError("source hashing ran")):
                    with self.assertRaises(FileExistsError):
                        daily.publish_daily_context(source, self.root)
                self.assertEqual(inventory(self.base), before)
                raw_parent.unlink()

    def test_explicit_vp_stage_links_escape_and_wrong_identity_are_refused(self):
        real = self.workspace / "selected-stage"
        write(real / "build.json", b'{"dataset_id":"wrong","version":"1.0.0"}')
        linked = self.workspace / "selected-link"
        linked.symlink_to(real, target_is_directory=True)
        for stage in (linked, self.base / "outside", real):
            with self.subTest(stage=stage), patch.object(vp, "verify_inputs", side_effect=AssertionError("input processing ran")):
                before = inventory(self.base)
                with self.assertRaises(ValueError):
                    vp.publish(self.root, self.workspace, stage)
                self.assertEqual(inventory(self.base), before)

    def vp_summary(self, stage):
        summary = dict(dataset_id=vp.DATASET_ID, version="1.0.0", rows=0, sessions=0,
                       output_files=[], code=[], request={}, feature_protocol={},
                       source_integrity=[], compiler={},
                       indicator_source={"path": f"catalog/indicators/{vp.DATASET_ID}.source.pine", "sha256": vp.SOURCE_SHA},
                       snapshot_semantics="fixture", weekly_boundary="fixture", limitations=[])
        request = self.workspace / f"requests/inbox/{vp.DATASET_ID}.yaml"
        protocol = self.root / f"catalog/indicators/{vp.DATASET_ID}.spec.json"
        write(request, b"request")
        write(protocol, b"{}")
        write(self.root / f"catalog/indicators/{vp.DATASET_ID}.source.pine", b"synthetic Pine source")
        summary["request"] = {"path": str(request.relative_to(self.workspace)), "sha256": vp.sha256(request)}
        summary["feature_protocol"] = {"path": str(protocol.relative_to(self.root)), "sha256": vp.sha256(protocol)}
        write(stage / "build.json", json.dumps(summary).encode())
        write(stage / "integrity.json", b"[]")
        write(stage / "compiler.json", b"{}")
        return summary

    def fake_retained(self, destination, sources, **kwargs):
        return {"files": [{"source": label, "path": label, "bytes": path.stat().st_size,
                            "sha256": vp.sha256(path)} for label, path in sources if path.is_file()]}

    def test_vp_selected_stage_is_used_and_late_quality_conflict_preserves_it(self):
        stage = self.workspace / "caller-selected"
        self.vp_summary(stage)
        quality = self.root / f"reports/quality/{vp.DATASET_ID}.md"
        def retain(*args, **kwargs):
            write(quality, b"late quality bytes")
            return self.fake_retained(*args, **kwargs)
        with patch.object(vp, "_code_sources", return_value=[]), patch.object(vp, "verify_inputs"), \
             patch.object(vp, "validate_stage", return_value={}), patch.object(vp._provenance, "retain_sources", side_effect=retain):
            with self.assertRaises(FileExistsError):
                vp.publish(self.root, self.workspace, stage)
        self.assertTrue(stage.is_dir())
        self.assertEqual(quality.read_bytes(), b"late quality bytes")
        self.assertFalse((self.root / "data/features/vp_hvn/version=1.0.0").exists())

    def test_vp_unchanged_explicit_stage_can_publish_with_separate_roots(self):
        stage = self.workspace / "caller-selected"
        self.vp_summary(stage)
        with patch.object(vp, "_code_sources", return_value=[]), patch.object(vp, "verify_inputs"), \
             patch.object(vp, "validate_stage", return_value={}), patch.object(vp._provenance, "retain_sources", side_effect=self.fake_retained), \
             patch.object(vp, "build", side_effect=AssertionError("automatic build ran")):
            catalog = vp.publish(self.root, self.workspace, stage)
        self.assertTrue(catalog.is_file())
        self.assertFalse(stage.exists())
        self.assertTrue((self.root / "data/features/vp_hvn/version=1.0.0/build.json").is_file())
        self.assertEqual((self.workspace / f"requests/fulfilled/{vp.DATASET_ID}.yaml").read_bytes(), b"request")
        self.assertFalse((self.root / "requests/fulfilled").exists())

    def test_vp_stale_declared_helper_inventory_refused_before_inputs(self):
        stage = self.workspace / "caller-selected"
        self.vp_summary(stage)
        before = inventory(self.base)
        with patch.object(vp, "_code_sources", return_value=[{"path": "changed helper", "sha256": "new"}]), \
             patch.object(vp, "verify_inputs", side_effect=AssertionError("input processing ran")):
            with self.assertRaisesRegex(ValueError, "helpers changed"):
                vp.publish(self.root, self.workspace, stage)
        self.assertEqual(inventory(self.base), before)

    def test_vp_helper_changed_during_validation_retains_stage_without_promotion(self):
        stage = self.workspace / "caller-selected"
        summary = self.vp_summary(stage)
        helper = self.workspace / "helpers/continuous_loader.py"
        write(helper, b"original executed helper")
        code = {"path": str(helper.relative_to(self.workspace)), "sha256": vp.sha256(helper)}
        summary["code"] = [code]
        write(stage / "build.json", json.dumps(summary).encode())
        def validate(selected):
            self.assertEqual(selected, stage)
            helper.write_bytes(b"helper changed during validation")
            return {}
        # Real byte retention is used here; only market-data processing is patched.
        for name in ("uv.lock", "pyproject.toml", "packages/bhishma/pyproject.toml"):
            write(self.workspace / name, b"prepared fixture")
        with patch.object(vp, "_code_sources", return_value=[code]), patch.object(vp, "verify_inputs"), \
             patch.object(vp, "validate_stage", side_effect=validate):
            with self.assertRaisesRegex(ValueError, "changed after staged validation"):
                vp.publish(self.root, self.workspace, stage)
        self.assertEqual((stage / "provenance/helpers/continuous_loader.py").read_bytes(),
                         b"helper changed during validation")
        self.assertFalse((self.root / "data/features/vp_hvn/version=1.0.0").exists())

    def test_vp_known_stage_recovery_metadata_refused_and_preserved(self):
        stage = self.workspace / "caller-selected"
        self.vp_summary(stage)
        for name in ("build.json", "integrity.json", "compiler.json", "validation.json"):
            with self.subTest(name=name):
                recovery = stage / (name + ".part")
                write(recovery, b"retained partial metadata")
                before = inventory(self.base)
                with self.assertRaises(ValueError):
                    vp.publish(self.root, self.workspace, stage)
                self.assertEqual(inventory(self.base), before)
                recovery.unlink()

    def test_vp_saved_matching_validation_bytes_are_preserved_and_different_bytes_refused(self):
        stage = self.workspace / "caller-selected"
        self.vp_summary(stage)
        result = vp.validate_stage(stage)
        validation = stage / "validation.json"
        exact = json.dumps(result, separators=(",", ":")).encode()
        validation.write_bytes(exact)
        self.assertEqual(vp.validate_stage(stage), result)
        self.assertEqual(validation.read_bytes(), exact)
        different = b'{"status":"failed"}'
        validation.write_bytes(different)
        with self.assertRaisesRegex(ValueError, "validation differs"):
            vp.validate_stage(stage)
        self.assertEqual(validation.read_bytes(), different)

    def test_vp_unowned_directory_part_sibling_is_allowed_and_preserved(self):
        sibling = self.root / "data/features/vp_hvn/version=1.0.0.part"
        write(sibling / "keep.bin", b"unrelated sibling")
        before = inventory(self.base)
        vp._check_publication_absent(self.root, self.workspace)
        self.assertEqual(inventory(self.base), before)

    def test_vp_failed_move_retains_selected_stage_and_shared_sibling(self):
        stage = self.workspace / "caller-selected"
        self.vp_summary(stage)
        sibling = self.root / "data/features/vp_hvn/unrelated"
        write(sibling / "keep.bin", b"unrelated sibling")
        real_rename = Path.rename
        def fail_move(path, target):
            if path == stage:
                raise OSError("injected promotion failure")
            return real_rename(path, target)
        with patch.object(vp, "_code_sources", return_value=[]), patch.object(vp, "verify_inputs"), \
             patch.object(vp, "validate_stage", return_value={}), patch.object(vp._provenance, "retain_sources", side_effect=self.fake_retained), \
             patch.object(Path, "rename", new=fail_move):
            with self.assertRaisesRegex(OSError, "promotion failure"):
                vp.publish(self.root, self.workspace, stage)
        self.assertTrue((stage / "build.json").is_file())
        self.assertEqual((sibling / "keep.bin").read_bytes(), b"unrelated sibling")
        self.assertFalse((self.root / "data/features/vp_hvn/version=1.0.0").exists())


class MetadataRefusalTests(unittest.TestCase):
    def test_exclusive_final_creation_preserves_late_conflict_and_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "manifest.json"
            real_link = os.link
            def conflict(source, destination):
                write(destination, b"other writer")
                return real_link(source, destination)
            with patch("abacus_bhishma.publication_safety.os.link", side_effect=conflict):
                with self.assertRaises(FileExistsError):
                    write_new_bytes(target, b"our retained metadata", root)
            self.assertEqual(target.read_bytes(), b"other writer")
            self.assertEqual(target.with_name("manifest.json.part").read_bytes(), b"our retained metadata")

    def test_failed_final_write_preserves_recovery_and_unrelated_sibling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            write(root / "sibling", b"keep")
            with patch("abacus_bhishma.publication_safety.os.link", side_effect=OSError("write failed")):
                with self.assertRaisesRegex(OSError, "write failed"):
                    write_new_bytes(root / "new.json", b"complete metadata", root)
            self.assertEqual((root / "new.json.part").read_bytes(), b"complete metadata")
            self.assertEqual((root / "sibling").read_bytes(), b"keep")

    def test_lexical_escape_and_redirected_paths_raise_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for path in (root / "../outside", root):
                with self.assertRaises(FileExistsError):
                    check_absent(path, root)
            (root / "parent").symlink_to(root, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                check_path(root / "parent/new", root)


if __name__ == "__main__":
    unittest.main()
