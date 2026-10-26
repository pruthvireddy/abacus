from __future__ import annotations

import importlib
import subprocess
import unittest
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, call, patch

from abacus_bhishma.provenance import git_version, sha256_file


# Frozen from the original Phase 1 helpers before extraction. These expectations
# are independent of the extracted implementation and its compatibility aliases.
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
BINARY_SHA256 = "40aff2e9d2d8922e47afd4648e6967497158785fbd1da870e7110266bf944880"
CHANGED_SHA256 = "54acfbfedc4d8da40f76f275e1a98f10af8ef1fb9fb39e5a67a00aabcbe6597c"
NO_REPOSITORY = {"git_commit": None, "repository_state": "not_a_git_repository"}
CONSUMERS = (
    "continuous_phase1",
    "continuous_phase2",
    "derived_ohlcv_5m",
    "session_anchored_vwap",
)


class FileHashTests(unittest.TestCase):
    def test_known_empty_binary_and_changed_hashes(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.bin"
            for data, expected in (
                (b"", EMPTY_SHA256),
                (bytes(range(256)), BINARY_SHA256),
                (bytes(range(256)) + b"\x00", CHANGED_SHA256),
            ):
                with self.subTest(data_length=len(data)):
                    path.write_bytes(data)
                    self.assertEqual(sha256_file(path), expected)

    def test_streaming_reads_have_bounded_existing_chunk_size(self):
        path = MagicMock(spec=Path)
        handle = path.open.return_value.__enter__.return_value
        handle.read.side_effect = [bytes(range(128)), bytes(range(128, 256)), b""]
        self.assertEqual(sha256_file(path), BINARY_SHA256)
        path.open.assert_called_once_with("rb")
        self.assertEqual(handle.read.call_args_list, [call(8 * 1024 * 1024)] * 3)
        path.open.return_value.__exit__.assert_called_once()

    def test_file_errors_propagate(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                sha256_file(Path(directory) / "missing")
        path = MagicMock(spec=Path)
        path.open.side_effect = PermissionError("unreadable fixture")
        with self.assertRaisesRegex(PermissionError, "unreadable fixture"):
            sha256_file(path)

    def test_read_errors_propagate_and_close_stream(self):
        path = MagicMock(spec=Path)
        path.open.return_value.__enter__.return_value.read.side_effect = OSError("read failed")
        with self.assertRaisesRegex(OSError, "read failed"):
            sha256_file(path)
        path.open.return_value.__exit__.assert_called_once()


class GitVersionTests(unittest.TestCase):
    def test_clean_and_dirty_result_shapes_and_commands(self):
        root = Path("/synthetic/publication/root")
        for status, dirty in ((" \n", False), (" M builder.py\n", True), ("?? untracked\n", True)):
            with self.subTest(status=status), patch(
                "subprocess.run",
                side_effect=[
                    subprocess.CompletedProcess([], 0, " abc123\n"),
                    subprocess.CompletedProcess([], 0, status),
                ],
            ) as run:
                self.assertEqual(git_version(root), {"git_commit": "abc123", "git_worktree_dirty": dirty})
                self.assertEqual(
                    run.call_args_list,
                    [
                        call(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True),
                        call(["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True),
                    ],
                )

    def test_unavailable_and_non_repository_results(self):
        errors = (
            FileNotFoundError("git unavailable"),
            subprocess.CalledProcessError(128, ["git", "rev-parse", "HEAD"]),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__), patch("subprocess.run", side_effect=error):
                self.assertEqual(git_version(Path("/synthetic/root")), NO_REPOSITORY)

    def test_status_failure_preserves_original_fallback_shape(self):
        for error in (
            FileNotFoundError("git disappeared"),
            subprocess.CalledProcessError(128, ["git", "status", "--porcelain"]),
        ):
            with self.subTest(error=type(error).__name__), patch(
                "subprocess.run",
                side_effect=[subprocess.CompletedProcess([], 0, "abc123\n"), error],
            ):
                self.assertEqual(git_version(Path("/synthetic/root")), NO_REPOSITORY)

    def test_unexpected_git_errors_propagate(self):
        with patch("subprocess.run", side_effect=PermissionError("cannot execute git")):
            with self.assertRaisesRegex(PermissionError, "cannot execute git"):
                git_version(Path("/synthetic/root"))


class CompatibilityTests(unittest.TestCase):
    def test_existing_imports_keep_known_hash_and_git_results(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.bin"
            path.write_bytes(bytes(range(256)))
            for consumer in CONSUMERS:
                module = importlib.import_module("abacus_bhishma." + consumer)
                with self.subTest(consumer=consumer):
                    self.assertEqual(module._sha256(path), BINARY_SHA256)
                    with patch(
                        "subprocess.run",
                        side_effect=[
                            subprocess.CompletedProcess([], 0, " abc123\n"),
                            subprocess.CompletedProcess([], 0, "?? untracked\n"),
                        ],
                    ):
                        self.assertEqual(
                            module._git_version(Path(directory)),
                            {"git_commit": "abc123", "git_worktree_dirty": True},
                        )


class HelperSourceProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.builder_path = self.root / "builder.py"
        self.builder_path.write_bytes(b"")
        (self.root / "pyproject.toml").write_bytes(b"")
        self.provenance_path = self.root / "provenance.py"
        self.provenance_path.write_bytes(b"")
        self.calendar_path = self.root / "calendar.py"
        self.calendar_path.write_bytes(bytes(range(256)))
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        self.patches.enter_context(patch("abacus_bhishma.provenance.__file__", str(self.provenance_path)))
        self.patches.enter_context(patch("abacus_bhishma.calendar.__file__", str(self.calendar_path)))

    def patch_builder(self, module):
        self.patches.enter_context(patch.object(module, "__file__", str(self.builder_path)))
        self.patches.enter_context(
            patch.object(module, "_git_version", return_value={"git_commit": "abc123", "git_worktree_dirty": False})
        )

    def assert_software(self, software, *, calendar=False):
        expected_helpers = {"abacus_bhishma.provenance": EMPTY_SHA256}
        if calendar:
            expected_helpers["abacus_bhishma.calendar"] = BINARY_SHA256
        self.assertEqual(software["helper_source_sha256"], expected_helpers)
        self.assertEqual(software["builder_sha256"], EMPTY_SHA256)
        self.assertEqual(software["git_commit"], "abc123")
        self.assertIs(software["git_worktree_dirty"], False)
        for field in ("builder", "python", "numpy", "pyarrow"):
            self.assertIn(field, software)

    def test_phase1_manifest_records_helper_source_without_replacing_existing_fields(self):
        from abacus_bhishma import continuous_phase1 as module

        self.patch_builder(module)
        for name, value in (("_condition_summary", {}), ("_source_files", []), ("_output_files", [])):
            self.patches.enter_context(patch.object(module, name, return_value=value))
        paths = module.ProjectPaths.from_root(self.root)
        manifest = module.build_manifest(
            paths,
            {product: [] for product in module.PRODUCTS},
            {"products": {}, "passed": True, "failures": []},
        )
        self.assert_software(manifest["code_version"])
        self.assertEqual(manifest["code_version"]["pyproject_sha256"], EMPTY_SHA256)
        self.assertEqual(manifest["code_version"]["builder"], "builder.py")
        # A changed helper source must affect its provenance independently of
        # the builder's unchanged bytes and existing fingerprint field.
        self.provenance_path.write_bytes(bytes(range(256)))
        changed = module.build_manifest(
            paths,
            {product: [] for product in module.PRODUCTS},
            {"products": {}, "passed": True, "failures": []},
        )["code_version"]
        self.assertEqual(changed["helper_source_sha256"], {"abacus_bhishma.provenance": BINARY_SHA256})
        self.assertEqual(changed["builder_sha256"], EMPTY_SHA256)

    def test_phase2_manifest_records_helper_source_without_replacing_existing_fields(self):
        from abacus_bhishma import continuous_phase2 as module

        self.patch_builder(module)
        self.patches.enter_context(patch.object(module, "_gap_statistics", return_value={}))
        self.patches.enter_context(patch.object(module, "_output_files", return_value=[]))
        paths = module.Phase2Paths.from_root(self.root)
        source = {
            "source_files": [],
            "output_files": [],
            "source_batches": {},
            "session_convention": {},
            "condition_reports": {},
        }
        manifest = module.build_manifest(
            paths,
            source,
            "source-manifest-fixture",
            MagicMock(),
            MagicMock(),
            {"products": {}, "passed": True, "failures": []},
        )
        self.assert_software(manifest["code_version"])
        self.assertEqual(manifest["code_version"]["pyproject_sha256"], EMPTY_SHA256)
        self.assertEqual(manifest["code_version"]["builder"], "builder.py")

    def test_vwap_manifest_records_both_helper_sources_and_retains_lineage(self):
        from abacus_bhishma import session_anchored_vwap as module

        self.patch_builder(module)
        descriptor = {"path": "synthetic", "bytes": 0, "sha256": "descriptor-fixture"}
        for name, value in (("_descriptor", descriptor), ("_product_stats", {}), ("_output_files", [])):
            self.patches.enter_context(patch.object(module, name, return_value=value))
        hashes = {"source_code_sha256": "saved-builder-fixture", "source_manifest_sha256": "saved-source-fixture"}
        manifest = module._manifest(
            module.Paths.from_root(self.root),
            2,
            hashes,
            {"source_batches": {"ohlcv_1m": "synthetic-batch"}, "adjustment_methodology": "synthetic"},
            [],
            {},
            descriptor,
            module.output_schema("source", "calendar", "indicator", 2),
        )
        self.assert_software(manifest["software"], calendar=True)
        self.assertEqual(manifest["lineage_hashes"], hashes)

    def test_derived_manifest_records_helper_source_with_all_publication_operations_stubbed(self):
        from abacus_bhishma import derived_ohlcv_5m as module

        self.patch_builder(module)
        stubs = {
            "_load_yaml_with_ruby": ({}, b"synthetic request"),
            "_validate_request": None,
            "_date_bounds": (0, 1, date(1970, 1, 1), date(1970, 1, 2)),
            "_verify_inputs": ({"output_files": []}, "synthetic-source", MagicMock(), [], {}),
            "_tick_lookup": ({}, {"ES": [250_000_000]}),
            "_validate_replay": {"passed": True, "failures": []},
            "_summarize_products": {},
            "_audit_descriptor": {"path": "synthetic", "bytes": 0, "sha256": "descriptor-fixture"},
            "_loader_example": "synthetic example",
            "_report_markdown": "synthetic report",
            "_atomic_bytes": None,
            "_atomic_text": None,
        }
        for name, value in stubs.items():
            self.patches.enter_context(patch.object(module, name, return_value=value))
        # Exercise manifest construction only. No real input, output rename,
        # request snapshot, quality report, or manifest is read/published.
        self.patches.enter_context(patch.object(module.os, "replace"))
        self.patches.enter_context(patch.object(module._provenance, "retain_sources", return_value={"files": []}))
        self.patches.enter_context(patch.object(module._provenance, "publication_sources", return_value=[]))
        manifest = module.build(self.root, self.root / "synthetic-request.yaml")
        self.assert_software(manifest["code_version"])
        self.assertFalse(module.DeliveryPaths.from_root(self.root).manifest.exists())


if __name__ == "__main__":
    unittest.main()
