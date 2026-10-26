"""GitHub hygiene boundaries use temporary synthetic Git repositories only."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "check-github-readiness.py"
SPEC = importlib.util.spec_from_file_location("github_readiness", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PRIVATE_HEADER = "-----BEGIN " + "PRIVATE KEY-----\n"


class GitHubReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic test")
        self.git("config", "user.email", "synthetic@example.invalid")
        self.write("README.md", "Synthetic fixture.\n")
        self.commit()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], env=self.env,
                              capture_output=True, check=True).stdout

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)
        return path

    def commit(self):
        self.git("add", "-A")
        self.git("-c", "commit.gpgsign=false", "commit", "-qm", "fixture")

    def run_audit(self, refs=None):
        return MODULE.audit(self.root, refs)

    def findings(self, report, kind):
        return [f for f in report["findings"] if f["kind"] == kind]

    def test_clean_repository_has_no_mutation_and_json_cli(self):
        before = self.git("status", "--porcelain=v1", "--untracked-files=all")
        process = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(self.root), "--ref", "HEAD", "--json"], capture_output=True, check=True)
        report = json.loads(process.stdout)
        self.assertTrue(report["passed"])
        self.assertEqual(before, self.git("status", "--porcelain=v1", "--untracked-files=all"))
        self.assertEqual(report["working_tree"]["candidate_paths"], 1)
        self.assertEqual(report["history"]["scanned_blobs"], 1)

    def test_ignored_files_are_not_read_but_tracked_ignored_files_are(self):
        self.write("tracked.txt", "safe\n")
        self.commit()
        self.write(".gitignore", "*.txt\n.env\n")
        self.write(".env", "ignored private fixture\n")
        self.write("ignored.txt", PRIVATE_HEADER)
        report = self.run_audit()
        self.assertTrue(report["passed"])
        self.write("tracked.txt", PRIVATE_HEADER)
        report = self.run_audit()
        self.assertEqual([f["path"] for f in self.findings(report, "private_key")], ["tracked.txt"])

    def test_token_redaction_and_line_numbers(self):
        token = "ghp_" + "a" * 36
        self.write("code.py", 'safe\nvalue = "' + token + '"\n')
        report = self.run_audit()
        self.assertFalse(report["passed"])
        self.assertEqual(self.findings(report, "github_token")[0]["line"], 2)
        self.assertNotIn(token, json.dumps(report))

    def test_chunks_handle_crossing_signatures_and_exact_boundary_eof(self):
        token = b"ghp_" + b"a" * 36
        with patch.object(MODULE, "CHUNK_BYTES", 1024):
            data = b"\n" * 1010 + token + b'"\n'
            self.assertEqual(list(MODULE.scan_stream(io.BytesIO(data))), [{"kind": "github_token", "line": 1011}])
            data = b"\n" * (1024 - len(token)) + token
            self.assertEqual(list(MODULE.scan_stream(io.BytesIO(data))), [{"kind": "github_token", "line": 985}])

    def test_public_url_fragments_and_longer_non_tokens_are_not_keys(self):
        content = b"https://blogger.googleusercontent.com/a/sk-" + b"a" * 48 + b"\n"
        content += b'"ghp_' + b"a" * 260 + b'"\n'
        self.assertEqual(list(MODULE.scan_stream(io.BytesIO(content))), [])

    def test_sensitive_names_require_review_but_examples_are_allowed(self):
        self.write(".env.example", "EXAMPLE=replace-me\n")
        self.assertTrue(self.run_audit()["passed"])
        self.write("nested/.env.production", "PRIVATE=local\n")
        report = self.run_audit()
        self.assertEqual(self.findings(report, "sensitive_filename")[0]["path"], "nested/.env.production")

    def test_external_symlink_fails_without_reading_target(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "secret"
            target.write_text(PRIVATE_HEADER)
            (self.root / "link").symlink_to(target)
            report = self.run_audit()
        self.assertTrue(self.findings(report, "external_symlink"))
        self.assertFalse(self.findings(report, "private_key"))

    def test_missing_and_ignored_internal_symlink_targets_are_warnings(self):
        self.write(".gitignore", "restored/\n")
        self.write("restored/file", "retained\n")
        (self.root / "retained-link").symlink_to("restored/file")
        (self.root / "missing-link").symlink_to("missing")
        report = self.run_audit()
        self.assertTrue(report["passed"])
        self.assertEqual(len(self.findings(report, "symlink_target_requires_restore")), 2)

    def test_staged_external_symlink_cannot_hide_behind_safe_working_link(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "secret"
            target.write_text(PRIVATE_HEADER)
            link = self.root / "link"
            link.symlink_to(target)
            self.git("add", "link")
            link.unlink()
            link.symlink_to("README.md")
            report = self.run_audit()
        external = self.findings(report, "external_symlink")
        self.assertEqual([(f["path"], f["scope"]) for f in external], [("link", "index")])
        self.assertFalse(self.findings(report, "private_key"))

    def test_symlinked_ancestor_is_not_traversed(self):
        self.write("source/file.txt", "safe tracked bytes\n")
        self.commit()
        (self.root / "source/file.txt").unlink()
        (self.root / "source").rmdir()
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "file.txt").write_text(PRIVATE_HEADER)
            (self.root / "source").symlink_to(outside, target_is_directory=True)
            report = self.run_audit()
        self.assertTrue(self.findings(report, "symlink_ancestor"))
        self.assertFalse(self.findings(report, "private_key"))

    def test_staged_content_and_deleted_history_secret_remain_detected(self):
        self.write("staged.txt", PRIVATE_HEADER)
        self.git("add", "staged.txt")
        self.write("staged.txt", "safe working file\n")
        report = self.run_audit()
        self.assertEqual(self.findings(report, "private_key")[0]["scope"], "index")
        self.git("reset", "-q", "HEAD", "staged.txt")
        self.write("old.txt", PRIVATE_HEADER)
        self.commit()
        (self.root / "old.txt").unlink()
        self.commit()
        report = self.run_audit()
        self.assertEqual(self.findings(report, "private_key")[0]["scope"], "history")

    def test_unrelated_internal_refs_are_excluded(self):
        good_commit = self.git("rev-parse", "HEAD").decode().strip()
        self.write("old.txt", PRIVATE_HEADER)
        self.commit()
        self.git("update-ref", "refs/codex/fixture", "HEAD")
        self.git("reset", "--hard", good_commit)
        self.assertTrue(self.run_audit()["passed"])
        self.assertFalse(self.run_audit(["refs/codex/fixture"])["passed"])

    def test_history_sensitive_alias_of_identical_blob_is_detected(self):
        self.write(".env", "Synthetic fixture.\n")
        self.commit()
        (self.root / ".env").unlink()
        self.commit()
        report = self.run_audit()
        self.assertTrue(any(f["path"] == ".env" and f["scope"] == "history" for f in self.findings(report, "sensitive_filename")))

    def test_size_thresholds_cover_working_tree_index_and_history(self):
        self.write("warning.txt", b"a" * 51)
        self.write("failure.txt", b"b" * 101)
        self.commit()
        with patch.object(MODULE, "WARN_BYTES", 50), patch.object(MODULE, "FAIL_BYTES", 100):
            report = self.run_audit()
        self.assertEqual({f["scope"] for f in self.findings(report, "file_above_100MiB")}, {"working_tree", "index", "history"})
        self.assertEqual({f["scope"] for f in self.findings(report, "file_above_50MiB")}, {"working_tree", "index", "history"})

    def test_invalid_root_and_ref_disclose_failure(self):
        self.assertFalse(MODULE.audit(self.root / "absent")["passed"])
        report = self.run_audit(["does-not-exist"])
        self.assertFalse(report["passed"])
        self.assertTrue(report["errors"])

    def test_unborn_repository_reports_unexecuted_history(self):
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(["git", "-C", folder, "init", "-q"], env=self.env, check=True)
            report = MODULE.audit(Path(folder))
        self.assertTrue(report["passed"])
        self.assertTrue(self.findings(report, "no_committed_history"))

    def test_git_paths_with_spaces_newlines_and_unicode(self):
        name = 'nested/quote"\n雪 file.txt'
        self.write(name, PRIVATE_HEADER)
        self.commit()
        report = self.run_audit()
        self.assertTrue(any(f["path"] == name and f["scope"] == "history" for f in self.findings(report, "private_key")))


if __name__ == "__main__":
    unittest.main()
