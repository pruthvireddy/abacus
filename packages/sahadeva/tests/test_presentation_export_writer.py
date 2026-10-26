"""Disposable tests of fresh revision writing; no saved revision is selected."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from abacus_sahadeva import presentation_revision


class PresentationRevisionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.output = self.root / "exports" / "explicit-v1"
        self.arguments = {
            "publication_bytes": b'{"title": "unchanged"}\n',
            "source_map_bytes": b'{"rows": [1, 3]}\n',
            "readme_text": "# Saved résumé\n",
            "producer_sources": [
                ("provenance/first.py", b"# actual producer one\n"),
                ("provenance/second.py", b"# actual producer two\n"),
            ],
        }

    def test_exact_supplied_bytes_and_deterministic_inventory(self):
        presentation_revision.write_revision(self.output, **self.arguments)
        self.assertEqual((self.output / "publication.json").read_bytes(), self.arguments["publication_bytes"])
        self.assertEqual((self.output / "source-map.json").read_bytes(), self.arguments["source_map_bytes"])
        self.assertEqual((self.output / "README.md").read_bytes(), self.arguments["readme_text"].encode())
        expected = []
        for name, content in self.arguments["producer_sources"]:
            self.assertEqual((self.output / name).read_bytes(), content)
            expected.append({"path": name, "sha256": hashlib.sha256(content).hexdigest()})
        inventory = (json.dumps(expected, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
        self.assertEqual((self.output / "provenance/source-inventory.json").read_bytes(), inventory)
        second = self.root / "exports" / "explicit-v2"
        presentation_revision.write_revision(second, **self.arguments)
        self.assertEqual((second / "provenance/source-inventory.json").read_bytes(), inventory)

    def test_preflight_types_paths_duplicates_and_encoding_before_any_creation(self):
        cases = [
            ("publication_bytes", {}, TypeError),
            ("source_map_bytes", bytearray(b"{}"), TypeError),
            ("readme_text", b"not text", TypeError),
            ("readme_text", "bad\ud800", UnicodeEncodeError),
            ("producer_sources", [], ValueError),
            ("producer_sources", [("provenance/first.py", "text")], TypeError),
            ("producer_sources", [("provenance/first.py", b"a"), ("provenance/first.py", b"b")], ValueError),
        ]
        for path in ["../escape.py", "/absolute.py", "provenance/../escape.py", "provenance/nested/code.py",
                     "provenance/", "provenance/..", "provenance/source-inventory.json", "provenance/code\\evil.py",
                     "provenance/code%2fevil.py", "provenance/bad\x00.py", "provenance/bad\n.py"]:
            cases.append(("producer_sources", [(path, b"source")], ValueError))
        for key, value, error in cases:
            with self.subTest(key=key, value=value):
                arguments = {**self.arguments, key: value}
                with self.assertRaises(error):
                    presentation_revision.write_revision(self.output, **arguments)
                self.assertEqual(list(self.root.iterdir()), [])
        for path in [Path("relative/revision"), self.root / "exports" / ".." / "escape"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                presentation_revision.write_revision(path, **self.arguments)
            self.assertEqual(list(self.root.iterdir()), [])

    def test_existing_directory_file_or_broken_link_is_preserved(self):
        for kind in ["directory", "file", "broken-link"]:
            with self.subTest(kind=kind):
                output = self.root / kind
                if kind == "directory":
                    output.mkdir()
                    (output / "keep").write_bytes(b"existing evidence")
                elif kind == "file":
                    output.write_bytes(b"existing bytes")
                else:
                    output.symlink_to(self.root / "absent")
                with self.assertRaises(FileExistsError):
                    presentation_revision.write_revision(output, **self.arguments)
                if kind == "directory":
                    self.assertEqual(list(output.iterdir()), [output / "keep"])
                    self.assertEqual((output / "keep").read_bytes(), b"existing evidence")
                elif kind == "file":
                    self.assertEqual(output.read_bytes(), b"existing bytes")
                else:
                    self.assertTrue(output.is_symlink())
                    self.assertFalse(output.exists())

    def test_redirected_and_non_directory_ancestors_are_refused(self):
        external = self.root / "external"
        external.mkdir()
        for kind in ["link", "broken", "file"]:
            with self.subTest(kind=kind):
                ancestor = self.root / kind
                if kind == "link":
                    ancestor.symlink_to(external, target_is_directory=True)
                elif kind == "broken":
                    ancestor.symlink_to(self.root / "absent", target_is_directory=True)
                else:
                    ancestor.write_bytes(b"preserve")
                with self.assertRaises(ValueError):
                    presentation_revision.write_revision(ancestor / "new" / "revision", **self.arguments)
                self.assertEqual(list(external.iterdir()), [])
                if kind == "file":
                    self.assertEqual(ancestor.read_bytes(), b"preserve")
                else:
                    self.assertTrue(ancestor.is_symlink())

    def test_partial_write_failure_retains_completed_outputs_for_diagnosis(self):
        original = presentation_revision._write_new

        def fail_on_source(path, content):
            if path.name == "second.py":
                with path.open("xb") as handle:
                    handle.write(content[:4])
                raise OSError("Synthetic write failure")
            return original(path, content)

        with mock.patch.object(presentation_revision, "_write_new", side_effect=fail_on_source):
            with self.assertRaisesRegex(OSError, "Synthetic write failure"):
                presentation_revision.write_revision(self.output, **self.arguments)
        self.assertEqual((self.output / "publication.json").read_bytes(), self.arguments["publication_bytes"])
        self.assertEqual((self.output / "source-map.json").read_bytes(), self.arguments["source_map_bytes"])
        self.assertEqual((self.output / "provenance/first.py").read_bytes(), self.arguments["producer_sources"][0][1])
        self.assertEqual((self.output / "provenance/second.py").read_bytes(), b"# ac")
        self.assertFalse((self.output / "provenance/source-inventory.json").exists())
        self.assertFalse((self.output / "README.md").exists())
        with self.assertRaises(FileExistsError):
            presentation_revision.write_revision(self.output, **self.arguments)


if __name__ == "__main__":
    unittest.main()
