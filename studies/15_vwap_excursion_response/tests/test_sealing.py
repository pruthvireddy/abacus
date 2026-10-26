"""Temporary-root sealing gates; no real freeze, stage, or retained evidence."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd

OWNER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OWNER))
from src import sealing


REQUIRED = (
    "verification.json", "uncertainty-verification.json", "report-verification.json",
    "visual-inspection.json", "preseal-checks.json",
)


def inventory(root):
    return {
        str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
    }


def fixture(root):
    root = root.resolve()
    out = root / "stages/synthetic_run"
    (out / "evidence").mkdir(parents=True)
    (out / "provenance").mkdir()
    for name in REQUIRED:
        (out / name).write_text(json.dumps({"status": "pass"}))
    (out / "execution-status.json").write_text('{"status": "outcomes_complete"}')
    (out / "provenance/environment.json").write_text('{"git_revision": "synthetic_revision"}')
    (out / "provenance/uv.lock").write_text("synthetic lock bytes\n")
    (out / "report.html").write_text("<p>Saved synthetic report.</p>\n")
    pd.DataFrame({"parent_id": ["synthetic_parent"], "value": [1]}).to_parquet(
        out / "evidence/parents.parquet", index=False)
    (out.parent / "preservation-baseline.json").write_text('{"synthetic": true}')
    source = root / "synthetic-owner"
    (source / "src").mkdir(parents=True)
    (source / "src/renderer.py").write_text("# Synthetic source bytes only.\n")
    (source / "pre-freeze-tests.txt").write_text("Synthetic passing test record.\n")
    paths = SimpleNamespace(workspace_root=root / "workspace", legacy_research_root=root / "legacy")
    return out, source, paths


def locations(out, paths):
    return (
        paths.workspace_root / "runs" / sealing.STUDY / out.name,
        paths.legacy_research_root / "work" / sealing.STUDY / out.name,
        out.parent / (out.name + "-seal-verification.json"),
    )


class SealingTests(unittest.TestCase):
    def test_success_preserves_evidence_and_records_verified_exact_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            out, source, paths = fixture(Path(temporary))
            original = inventory(out / "evidence")
            with patch.object(sealing, "roots", return_value=paths), \
                 patch.object(sealing, "OWNER", source), \
                 patch.object(sealing, "check_freeze") as freeze, \
                 patch.object(sealing, "utcnow", return_value="2026-10-10T00:00:00+00:00"), \
                 contextlib.redirect_stdout(io.StringIO()):
                sealing.seal(out)
            freeze.assert_called_once_with()
            dest, retained, verification = locations(out, paths)
            self.assertEqual(inventory(out / "evidence"), original)
            self.assertEqual((retained / "parents.parquet").read_bytes(), original["parents.parquet"])
            retained_manifest = json.loads((retained / "manifest.json").read_text())
            self.assertEqual(retained_manifest["files"][0]["rows"], 1)
            self.assertEqual(retained_manifest["files"][0]["sha256"],
                             hashlib.sha256(original["parents.parquet"]).hexdigest())
            manifest = json.loads((dest / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "complete")
            self.assertEqual(manifest["git_revision"], "synthetic_revision")
            self.assertFalse((dest / "evidence").exists())
            self.assertEqual((dest / "provenance/final-study-source/src/renderer.py").read_bytes(),
                             (source / "src/renderer.py").read_bytes())
            for name, digest in manifest["artifacts"].items():
                self.assertEqual(hashlib.sha256((dest / name).read_bytes()).hexdigest(), digest)
            self.assertEqual(json.loads(verification.read_text())["status"], "pass")

    def test_failed_gates_and_hashes_in_plain_and_optimized_processes(self):
        cases = [(name, condition) for name in REQUIRED for condition in ["missing", "malformed", "failed"]]
        cases += [
            ("execution-status.json", "missing"), ("execution-status.json", "malformed"),
            ("execution-status.json", "failed"), ("verification.json", "missing_status"),
            ("verification.json", "not_mapping"), ("freeze", "failed"),
            ("completed", "existing"), ("retained", "existing"),
            ("copy", "exception"), ("copy", "hash_mismatch"), ("sealed", "hash_mismatch"),
        ]
        for optimized in [False, True]:
            for name, condition in cases:
                with self.subTest(optimized=optimized, name=name, condition=condition), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "fixture"
                    command = [sys.executable] + (["-O"] if optimized else [])
                    command += [str(Path(__file__).resolve()), "--seal-child", name, condition, str(root)]
                    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
                    result = subprocess.run(command, cwd=temporary, env=environment, text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "", result.stdout + result.stderr)
                    self.assertNotIn("AssertionError", result.stderr)
                    expected_error = "FileExistsError" if condition == "existing" else "OSError" if condition == "exception" else "ValueError"
                    self.assertIn(expected_error, result.stderr)
                    if name in REQUIRED or name == "execution-status.json":
                        self.assertIn(name, result.stderr)
                    out = root / "stages/synthetic_run"
                    paths = SimpleNamespace(workspace_root=root / "workspace", legacy_research_root=root / "legacy")
                    dest, retained, verification = locations(out, paths)
                    self.assertFalse(verification.exists())
                    before = json.loads((root.parent / "before.json").read_text())
                    before = {key: bytes.fromhex(value) if value is not None else None for key, value in before.items()}
                    if name not in ["copy", "sealed"]:
                        self.assertEqual(inventory(root), before)
                    else:
                        # Retention was already started when the injected copy/hash failure
                        # occurred. Existing behavior may leave partial directories.
                        self.assertTrue(retained.is_dir())
                        self.assertEqual(inventory(out / "evidence"), {
                            key.removeprefix("stages/synthetic_run/evidence/"): value
                            for key, value in before.items() if key.startswith("stages/synthetic_run/evidence/")
                        })
                        if name == "copy":
                            self.assertFalse(dest.exists())
                            self.assertFalse((retained / "manifest.json").exists())
                        else:
                            self.assertTrue((dest / "manifest.json").exists())
                            self.assertIn("report.html", result.stderr)


def seal_child(name, condition, root):
    out, source, paths = fixture(root)
    dest, retained, _ = locations(out, paths)
    if name in REQUIRED or name == "execution-status.json":
        path = out / name
        if condition == "missing":
            path.unlink()
        elif condition == "malformed":
            path.write_text("{not valid JSON")
        elif condition == "failed":
            path.write_text('{"status": "incomplete"}')
        elif condition == "missing_status":
            path.write_text("{}")
        elif condition == "not_mapping":
            path.write_text("[]")
    elif condition == "existing":
        existing = dest if name == "completed" else retained
        existing.mkdir(parents=True)
        (existing / "preserve.bin").write_bytes(b"existing immutable identity\x00\xff")
    before = inventory(root)
    (root.parent / "before.json").write_text(json.dumps({key: value.hex() if value is not None else None for key, value in before.items()}))
    with contextlib.ExitStack() as patches:
        patches.enter_context(patch.object(sealing, "roots", return_value=paths))
        patches.enter_context(patch.object(sealing, "OWNER", source))
        patches.enter_context(patch.object(sealing, "check_freeze", side_effect=ValueError("Synthetic freeze rejection") if name == "freeze" else None))
        if name == "copy":
            original_copy = sealing.shutil.copy2
            def failed_copy(src, target, *args, **kwargs):
                if Path(target).parent == retained:
                    if condition == "exception":
                        raise OSError("Synthetic retained copy failure")
                    result = original_copy(src, target, *args, **kwargs)
                    Path(target).write_bytes(b"corrupted retained bytes")
                    return result
                return original_copy(src, target, *args, **kwargs)
            patches.enter_context(patch.object(sealing.shutil, "copy2", side_effect=failed_copy))
        elif name == "sealed":
            original_sha = sealing.sha
            report_reads = 0
            def changed_hash(path):
                nonlocal report_reads
                if Path(path) == dest / "report.html":
                    report_reads += 1
                    if report_reads > 1:
                        return "0" * 64
                return original_sha(path)
            patches.enter_context(patch.object(sealing, "sha", side_effect=changed_hash))
        sealing.seal(out)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--seal-child":
        seal_child(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
    else:
        unittest.main()
