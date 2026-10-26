"""Preservation checks use temporary synthetic roots and no configured data."""

from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from abacus_bhishma import continuous_phase1 as phase1
from abacus_bhishma import continuous_phase2 as phase2


def inventory(root: Path) -> dict[str, tuple[str, bytes | str | None]]:
    """Record directories, bytes and links without following symlink targets."""
    result = {}
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            result[relative] = ("symlink", os.readlink(path))
        elif path.is_dir():
            result[relative] = ("directory", None)
        else:
            result[relative] = ("file", path.read_bytes())
    return result


def write(path: Path, content: bytes = b"sentinel\x00\xff") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


class PublicationSafetyChecks:
    module: object

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "publication"
        self.root.mkdir()
        if self.module is phase1:
            self.paths = phase1.ProjectPaths.from_root(self.root)
        else:
            self.paths = phase2.Phase2Paths.from_root(self.root)
        self.error = self.module.Phase1Error if self.module is phase1 else self.module.Phase2Error

    def owned_outputs(self, *, temporary: bool = False) -> list[Path]:
        if self.module is phase1:
            return [
                self.paths.instrument_output(temporary=temporary),
                self.paths.schedule_output(temporary=temporary) / "roll_schedule.parquet",
                self.paths.schedule_output(temporary=temporary) / "roll_schedule.csv",
                *(self.paths.product_output(product, temporary=temporary) for product in ("ES", "NQ", "GC")),
            ]
        return [
            self.paths.audit_output(temporary=temporary),
            *(self.paths.product_output(product, temporary=temporary) for product in ("ES", "NQ", "GC")),
        ]

    def stage_outputs(self) -> None:
        for output in self.owned_outputs(temporary=True):
            if output.suffix:
                write(output, output.name.encode())
            else:
                write(output / "fixture.bin", str(output.relative_to(self.paths.temp_root)).encode())

    def assert_refusal_preserves(self, action) -> None:
        before = inventory(self.base)
        with self.assertRaises(self.error):
            action()
        self.assertEqual(inventory(self.base), before)

    def test_manifest_refused_with_and_without_force(self) -> None:
        write(self.paths.manifest)
        write(self.paths.temp_root / "stale-evidence.bin")
        for force in (False, True):
            with self.subTest(force=force):
                self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=force))

    def test_quality_report_alone_refused_with_and_without_force(self) -> None:
        write(self.paths.quality_report)
        write(self.paths.temp_root / "stale-evidence.bin")
        for force in (False, True):
            with self.subTest(force=force):
                self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=force))

    def test_every_partial_final_destination_refused_before_staging_cleanup(self) -> None:
        write(self.paths.temp_root / "stale-evidence.bin")
        for output in self.owned_outputs():
            with self.subTest(output=output):
                if output.suffix:
                    write(output)
                else:
                    write(output / "partial.bin")
                for force in (False, True):
                    self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=force))
                if output.suffix:
                    output.unlink()
                else:
                    (output / "partial.bin").unlink()
                    output.rmdir()

    def test_known_backup_and_metadata_recovery_artifacts_are_preserved(self) -> None:
        backup = self.root / "data/curated" / f".{self.module.DATASET_NAME}.backup"
        recovery = [backup, self.paths.manifest.with_name(self.paths.manifest.name + ".part"),
                    self.paths.quality_report.with_name(self.paths.quality_report.name + ".part")]
        write(self.paths.temp_root / "stale-evidence.bin")
        for artifact in recovery:
            with self.subTest(artifact=artifact):
                if artifact == backup:
                    write(artifact / "previous-output.bin")
                else:
                    write(artifact)
                for force in (False, True):
                    self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=force))
                self.assert_refusal_preserves(lambda: self.module._publish(self.paths))
                if artifact == backup:
                    (artifact / "previous-output.bin").unlink()
                    artifact.rmdir()
                else:
                    artifact.unlink()

    def test_broken_symlink_final_and_recovery_entries_are_conflicts(self) -> None:
        entries = [self.paths.manifest, self.paths.quality_report, *self.owned_outputs(),
                   self.root / "data/curated" / f".{self.module.DATASET_NAME}.backup",
                   self.paths.manifest.with_name(self.paths.manifest.name + ".part"),
                   self.paths.quality_report.with_name(self.paths.quality_report.name + ".part")]
        write(self.paths.temp_root / "stale-evidence.bin")
        for entry in entries:
            with self.subTest(entry=entry):
                entry.parent.mkdir(parents=True, exist_ok=True)
                entry.symlink_to(self.base / "absent-target")
                self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=True))
                self.assert_refusal_preserves(lambda: self.module._publish(self.paths))
                entry.unlink()

    def test_stale_staging_requires_force_and_recovery_is_exact(self) -> None:
        write(self.paths.temp_root / "stale-evidence.bin")
        sibling = self.paths.temp_root.with_name(self.paths.temp_root.name + ".unrelated")
        write(sibling / "retained.bin")
        sibling_before = inventory(sibling)
        self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=False))
        self.module._prepare_build(self.paths, force=True)
        self.assertTrue(self.paths.temp_root.is_dir())
        self.assertEqual(list(self.paths.temp_root.iterdir()), [])
        self.assertEqual(inventory(sibling), sibling_before)

    def test_symlinked_staging_target_is_untouched(self) -> None:
        target = self.base / "other-staging"
        write(target / "retained.bin")
        self.paths.temp_root.parent.mkdir(parents=True)
        self.paths.temp_root.symlink_to(target, target_is_directory=True)
        for force in (False, True):
            self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=force))
        self.assert_refusal_preserves(lambda: self.module._publish(self.paths))

    def test_broken_symlink_staging_is_preserved(self) -> None:
        self.paths.temp_root.parent.mkdir(parents=True)
        self.paths.temp_root.symlink_to(self.base / "missing")
        for force in (False, True):
            self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=force))

    def test_escaped_or_wrong_staging_directory_is_rejected(self) -> None:
        for location in (self.base / "outside", self.root / "data/curated/unrelated"):
            with self.subTest(location=location):
                write(location / "retained.bin")
                altered = replace(self.paths, temp_root=location)
                for force in (False, True):
                    self.assert_refusal_preserves(lambda: self.module._prepare_build(altered, force=force))
                self.assert_refusal_preserves(lambda: self.module._publish(altered))

    def test_redirected_staging_ancestor_is_rejected(self) -> None:
        target = self.base / "other-data"
        write(target / "curated" / self.paths.temp_root.name / "retained.bin")
        (self.root / "data").symlink_to(target, target_is_directory=True)
        for force in (False, True):
            self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=force))
        self.assert_refusal_preserves(lambda: self.module._publish(self.paths))

    def test_conflicting_publication_parent_preserves_staging_and_target(self) -> None:
        self.stage_outputs()
        parent = self.owned_outputs()[0].parent
        target = self.base / "other-final-output"
        write(target / "retained.bin")
        parent.parent.mkdir(parents=True, exist_ok=True)
        for kind in ("file", "symlink", "broken_symlink"):
            with self.subTest(kind=kind):
                if kind == "file":
                    write(parent)
                else:
                    parent.symlink_to(target if kind == "symlink" else self.base / "absent-target")
                for force in (False, True):
                    self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=force))
                self.assert_refusal_preserves(lambda: self.module._publish(self.paths))
                parent.unlink()

    def test_staging_cleanup_helper_rejects_final_and_arbitrary_paths(self) -> None:
        for path in (self.owned_outputs()[0], self.root / "data/curated/unrelated", self.base / "outside"):
            with self.subTest(path=path):
                write(path / "retained.bin")
                self.assert_refusal_preserves(lambda: self.module._safe_remove(path, self.root))

    def test_staged_source_symlink_is_refused_without_following_target(self) -> None:
        self.stage_outputs()
        source = self.owned_outputs(temporary=True)[0]
        target = self.base / "other-output"
        source.rename(target)
        source.symlink_to(target, target_is_directory=True)
        self.assert_refusal_preserves(lambda: self.module._publish(self.paths))

    def test_direct_publish_refuses_all_existing_final_destinations(self) -> None:
        self.stage_outputs()
        for output in [self.paths.manifest, self.paths.quality_report, *self.owned_outputs()]:
            with self.subTest(output=output):
                if output in self.owned_outputs() and not output.suffix:
                    write(output / "published.bin")
                else:
                    write(output)
                self.assert_refusal_preserves(lambda: self.module._publish(self.paths))
                if output in self.owned_outputs() and not output.suffix:
                    (output / "published.bin").unlink()
                    output.rmdir()
                else:
                    output.unlink()

    def test_conflict_after_preparation_refuses_without_moving_staged_data(self) -> None:
        self.module._prepare_build(self.paths, force=False)
        self.stage_outputs()
        for output in (self.paths.manifest, self.paths.quality_report, self.owned_outputs()[-1] / "partial.bin"):
            with self.subTest(output=output):
                write(output)
                self.assert_refusal_preserves(lambda: self.module._publish(self.paths))
                output.unlink()
                if output.name == "partial.bin":
                    output.parent.rmdir()

    def test_fresh_synthetic_publication_moves_owned_data(self) -> None:
        self.module._prepare_build(self.paths, force=False)
        self.stage_outputs()
        staged = [inventory(path) if path.is_dir() else path.read_bytes()
                  for path in self.owned_outputs(temporary=True)]
        self.module._publish(self.paths)
        for output, expected in zip(self.owned_outputs(), staged):
            self.assertEqual(inventory(output) if output.is_dir() else output.read_bytes(), expected)
        self.assertFalse(self.paths.temp_root.exists())
        self.assertFalse((self.root / "data/curated" / f".{self.module.DATASET_NAME}.backup").exists())
        self.module._atomic_text(self.paths.manifest, "synthetic manifest")
        self.module._atomic_text(self.paths.quality_report, "synthetic quality report")
        self.assertEqual(self.paths.manifest.read_text(), "synthetic manifest")
        self.assertEqual(self.paths.quality_report.read_text(), "synthetic quality report")
        self.assertFalse(self.paths.manifest.with_name(self.paths.manifest.name + ".part").exists())
        self.assertFalse(self.paths.quality_report.with_name(self.paths.quality_report.name + ".part").exists())

    def test_injected_move_failures_restore_bytes_and_directory_inventory(self) -> None:
        self.stage_outputs()
        write(self.root / "data/curated/continuous/1m/unrelated/retained.bin")
        before = inventory(self.base)
        real_replace = os.replace
        for fail_at in range(1, len(self.owned_outputs()) + 1):
            calls = 0

            def fail_move(source, destination):
                nonlocal calls
                calls += 1
                if calls == fail_at:
                    raise OSError("injected publication failure")
                return real_replace(source, destination)

            with self.subTest(fail_at=fail_at), patch.object(self.module.os, "replace", side_effect=fail_move):
                with self.assertRaisesRegex(OSError, "injected publication failure"):
                    self.module._publish(self.paths)
            self.assertEqual(inventory(self.base), before)

    def test_rollback_retains_new_sibling_evidence_in_created_parent(self) -> None:
        self.stage_outputs()
        real_replace = os.replace
        calls = 0
        sibling = self.owned_outputs()[0].parent / "new-sibling.bin"

        def fail_after_first_move(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                write(sibling, b"retain sibling created during failure")
                raise OSError("injected publication failure")
            return real_replace(source, destination)

        staged_before = inventory(self.paths.temp_root)
        with patch.object(self.module.os, "replace", side_effect=fail_after_first_move):
            with self.assertRaises(OSError):
                self.module._publish(self.paths)
        self.assertEqual(sibling.read_bytes(), b"retain sibling created during failure")
        self.assertEqual(inventory(self.paths.temp_root), staged_before)
        for output in self.owned_outputs():
            self.assertFalse(output.exists())

    def test_rollback_failure_leaves_moved_evidence_and_preserves_staging(self) -> None:
        self.stage_outputs()
        first_source = self.owned_outputs(temporary=True)[0]
        first_destination = self.owned_outputs()[0]
        expected = inventory(first_source)
        real_replace = os.replace
        calls = 0

        def fail_publication_and_restoration(source, destination):
            nonlocal calls
            calls += 1
            if calls in (2, 3):
                raise OSError("injected move/restore failure")
            return real_replace(source, destination)

        with patch.object(self.module.os, "replace", side_effect=fail_publication_and_restoration):
            with self.assertRaises(OSError) as caught:
                self.module._publish(self.paths)
        self.assertEqual(inventory(first_destination), expected)
        self.assertTrue(self.paths.temp_root.exists())
        self.assertTrue(any("rollback retained" in note for note in caught.exception.__notes__))
        self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=True))

    def test_metadata_write_refuses_final_or_temporary_recovery_file(self) -> None:
        for artifact in (self.paths.manifest, self.paths.manifest.with_name(self.paths.manifest.name + ".part")):
            with self.subTest(artifact=artifact):
                write(artifact)
                self.assert_refusal_preserves(lambda: self.module._atomic_text(self.paths.manifest, "new metadata"))
                artifact.unlink()

    def test_metadata_conflict_after_initial_check_retains_staged_bytes(self) -> None:
        real_open = Path.open
        temporary = self.paths.manifest.with_name(self.paths.manifest.name + ".part")

        def introduce_conflict(path, mode="r", *args, **kwargs):
            if path == temporary and mode == "xb":
                with real_open(self.paths.manifest, "wb") as handle:
                    handle.write(b"late immutable manifest")
            return real_open(path, mode, *args, **kwargs)

        with patch.object(Path, "open", new=introduce_conflict):
            with self.assertRaises(self.error):
                self.module._atomic_text(self.paths.manifest, "staged metadata")
        self.assertEqual(self.paths.manifest.read_bytes(), b"late immutable manifest")
        self.assertEqual(temporary.read_bytes(), b"staged metadata")

    def test_success_retains_unexpected_staging_evidence(self) -> None:
        self.stage_outputs()
        evidence = self.paths.temp_root / "diagnostic.bin"
        write(evidence)
        self.module._publish(self.paths)
        self.assertEqual(evidence.read_bytes(), b"sentinel\x00\xff")


class Phase1PublicationSafetyTests(PublicationSafetyChecks, unittest.TestCase):
    module = phase1

    def test_schedule_publishes_only_leaves_preserving_phase2_audits_and_siblings(self) -> None:
        shared = self.paths.schedule_output()
        audit = shared / "adjustment=prior_session_close_additive_v1"
        write(audit / "adjustment_schedule.parquet")
        write(audit / "adjustment_factors.csv", b"phase2 factors")
        write(shared / "unrelated.txt", b"shared sibling")
        shared_inode = shared.stat().st_ino
        before = inventory(shared)
        self.module._prepare_build(self.paths, force=False)
        self.stage_outputs()
        self.module._publish(self.paths)
        expected = {**before, "roll_schedule.parquet": ("file", b"roll_schedule.parquet"),
                    "roll_schedule.csv": ("file", b"roll_schedule.csv")}
        self.assertEqual(inventory(shared), expected)
        self.assertEqual(shared.stat().st_ino, shared_inode)

    def test_schedule_leaf_conflicts_preserve_shared_ancestor_and_audit_descendants(self) -> None:
        shared = self.paths.schedule_output()
        write(shared / "adjustment=prior_session_close_additive_v1/audit.bin")
        for name in ("roll_schedule.parquet", "roll_schedule.csv"):
            with self.subTest(name=name):
                write(shared / name)
                shared_inode = shared.stat().st_ino
                self.stage_outputs()
                for force in (False, True):
                    self.assert_refusal_preserves(lambda: self.module._prepare_build(self.paths, force=force))
                self.assert_refusal_preserves(lambda: self.module._publish(self.paths))
                self.assertEqual(shared.stat().st_ino, shared_inode)
                (shared / name).unlink()


class Phase2PublicationSafetyTests(PublicationSafetyChecks, unittest.TestCase):
    module = phase2

    def test_phase1_schedule_and_contract_truth_siblings_are_preserved(self) -> None:
        write(self.paths.roll_schedule, b"phase1 schedule")
        write(self.paths.roll_schedule.with_suffix(".csv"), b"phase1 schedule csv")
        write(self.paths.phase1_product("ES") / "year=2024/part-000.parquet", b"contract truth")
        before = inventory(self.root)
        self.module._prepare_build(self.paths, force=False)
        self.stage_outputs()
        self.module._publish(self.paths)
        after = inventory(self.root)
        for path, expected in before.items():
            self.assertEqual(after[path], expected)


if __name__ == "__main__":
    unittest.main()
