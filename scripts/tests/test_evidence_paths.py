"""Shared JSON/path boundaries use disposable local files only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from evidence_paths import EvidenceError, load_json, relative_path, safe_path


class EvidencePathsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.file = self.root / "input.json"

    def test_null_false_and_exact_strings_survive_json(self):
        self.file.write_text('{"null":null,"false":false,"blank":"","zero":"0"}')
        self.assertEqual(load_json(self.file), {"null": None, "false": False, "blank": "", "zero": "0"})

    def test_duplicate_keys_and_all_nonfinite_number_forms_fail(self):
        for content in ('{"x":1,"x":2}', '{"nested":{"x":1,"x":2}}',
                        '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e999}'):
            with self.subTest(content=content):
                self.file.write_text(content)
                with self.assertRaises(EvidenceError):
                    load_json(self.file)

    def test_json_failures_are_useful_errors(self):
        with self.assertRaisesRegex(EvidenceError, "Cannot read JSON"):
            load_json(self.file)
        self.file.write_bytes(b"\xff")
        with self.assertRaises(EvidenceError):
            load_json(self.file)
        self.file.write_text("[")
        with self.assertRaises(EvidenceError):
            load_json(self.file)

    def test_paths_reject_ambiguous_segments_before_access(self):
        for value in (None, True, "", "/absolute", "../escape", "a/../b", "a//b",
                      "a/./b", "a/", "a\\b", "C:/drive", "a\x00b", " spaced",
                      "a?b", "a#b", "a%b", "a /b", "a/ b", "bad\ud800", "bad\udc80"):
            with self.subTest(value=value), self.assertRaises(EvidenceError):
                relative_path(value)
        self.assertEqual(relative_path("tables/sample count.csv"), "tables/sample count.csv")

    def test_local_file_directory_and_missing_boundaries(self):
        self.file.write_text("{}")
        directory = self.root / "tables"
        directory.mkdir()
        self.assertEqual(safe_path(self.root, "input.json", ordinary_file=True), self.file)
        self.assertEqual(safe_path(self.root, "tables"), directory)
        for value in ("tables", "missing.json", "input.json/child"):
            with self.subTest(value=value), self.assertRaises(EvidenceError):
                safe_path(self.root, value, ordinary_file=True)

    def test_symlinked_files_and_ancestors_rejected_even_when_contained(self):
        self.file.write_text("{}")
        (self.root / "file-link").symlink_to(self.file)
        (self.root / "ancestor").symlink_to(self.root, target_is_directory=True)
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "outside").symlink_to(outside, target_is_directory=True)
            for value in ("file-link", "ancestor/input.json", "outside/private.json"):
                with self.subTest(value=value), self.assertRaisesRegex(EvidenceError, "Symlink"):
                    safe_path(self.root, value, ordinary_file=True)

    def test_critical_errors_remain_active_under_optimized_python(self):
        self.file.write_text('{"x":1e999}')
        program = '''from pathlib import Path
import sys
sys.path.insert(0, sys.argv[1])
from evidence_paths import EvidenceError, load_json, relative_path
for operation in (lambda: load_json(Path(sys.argv[2])), lambda: relative_path('../escape')):
    try: operation()
    except EvidenceError: continue
    raise SystemExit('critical validation was disabled')
'''
        for optimize in (False, True):
            command = [sys.executable] + (["-O"] if optimize else [])
            result = subprocess.run(command + ["-B", "-c", program, str(SCRIPTS), str(self.file)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
