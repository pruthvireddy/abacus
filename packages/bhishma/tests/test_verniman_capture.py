"""Synthetic network-boundary tests; no public website requests."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from abacus_bhishma.verniman_capture import _PostLinks, capture_pages


class CaptureTests(unittest.TestCase):
    def test_only_full_size_post_images_are_collected(self):
        parser = _PostLinks()
        parser.feed("""<a href='https://blogger.googleusercontent.com/header.png'>logo</a>
        <a name='123'></a><div class='post-body entry-content'><div>
        <a href='https://blogger.googleusercontent.com/large.png'><img src='small.png'/></a>
        <br/><a href='https://example.org/tracker.png'>external</a></div></div>
        <a href='https://blogger.googleusercontent.com/footer.png'>footer</a>""")
        self.assertEqual(parser.post_id, "123")
        self.assertEqual(parser.images, ["https://blogger.googleusercontent.com/large.png"])

    def test_rejects_duplicate_pages_and_non_post_urls_before_network(self):
        with tempfile.TemporaryDirectory() as directory, patch(
                "abacus_bhishma.verniman_capture._fetch") as fetch:
            root = Path(directory)
            for urls in (["https://example.org/a.html"],
                         ["https://verniman.blogspot.com/"],
                         ["https://verniman.blogspot.com/2026/10/a.html?m=0",
                          "https://verniman.blogspot.com/2026/10/a.html?m=1"]):
                with self.assertRaises(ValueError):
                    capture_pages(root, urls)
            fetch.assert_not_called()

    def test_refuses_existing_batch_without_network(self):
        with tempfile.TemporaryDirectory() as directory, patch(
                "abacus_bhishma.verniman_capture._fetch") as fetch:
            root = Path(directory)
            batch = root / "data/raw/blogspot/verniman/html/existing"
            batch.mkdir(parents=True)
            sentinel = batch / "retained.txt"
            sentinel.write_text("retained")
            with self.assertRaises(FileExistsError):
                capture_pages(root, ["https://verniman.blogspot.com/2026/10/a.html"], batch_id="existing")
            self.assertEqual(sentinel.read_text(), "retained")
            fetch.assert_not_called()

    def test_failed_capture_retains_partial_bytes_and_failure_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def fetch(url, path, publication_root, kind):
                if kind == "atom":
                    raise OSError("synthetic feed failure")
                path.write_text("<a name='123'></a><div class='post-body'>Plan</div>")
                return {"path": path.relative_to(publication_root).as_posix(), "captured_at": "2026-10-20T15:00:00Z"}

            with patch("abacus_bhishma.verniman_capture._fetch", side_effect=fetch):
                with self.assertRaisesRegex(OSError, "synthetic feed failure"):
                    capture_pages(root, ["https://verniman.blogspot.com/2026/10/a.html"], batch_id="failed")
            batch = root / "data/raw/blogspot/verniman/html/failed"
            self.assertTrue((batch / "post-01.html").is_file())
            failure = json.loads((batch / "capture_failure.json").read_text())
            self.assertIn("synthetic feed failure", failure["error"])
            self.assertEqual(len(failure["files"]), 1)
            self.assertFalse((batch / "batch_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
