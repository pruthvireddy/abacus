from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from html import escape
from pathlib import Path

from abacus_bhishma.provenance import sha256_file
from abacus_bhishma.verniman_levels import (
    DATA_PATH, DATASET_ID, MANIFEST_PATH, QUALITY_PATH, SCHEMA_PATH, TIMING_STATUS,
    extract_entry, levels_schema, load_release, outlook_schema, publish_release, verify_release,
)

URL = "https://verniman.blogspot.com/2009/10/example.html"
BODY = """<img src="screen-1999-01-01-090435.png">
<p>Outlook 10/13: Commentary.</p>
<p><b>ESZ26 (Dec2026)</b>: GAP 7856 IVR 85</p>
<p>/ES Plan</p>
<div>A) If market moves above HVE-YVAL 7850 with bullish VIX/CVD, buy towards GAP 7857 YVAH 7864 and PBT 7906 all magnets.</div>
<div>B) If market moves below HVE-YVAH 7850 with bearish VIX/CVD, sell towards ONL 7836 and PBT 7824 GAP 7822 both magnets.</div>
<div>Note: This prose and 1234 must not become a target.</div>"""


def atom(body: str = BODY, *, url: str = URL, source_id: str = "456") -> bytes:
    return (f'<entry xmlns="http://www.w3.org/2005/Atom">'
            f'<id>tag:blogger.com,1999:blog-123.post-{source_id}</id><title>Example outlook</title>'
            '<published>2009-10-13T09:10:00.000-04:00</published>'
            '<updated>2026-10-13T09:05:57.412-04:00</updated>'
            f'<content type="html">{escape(body)}</content>'
            f'<link rel="alternate" href="{url}"/></entry>').encode()


def extract(body: str = BODY, *, html_body: str | None = None):
    return extract_entry(
        atom(body), captured_at="2026-10-20T23:31:30Z", html_path="raw/page.html",
        atom_path="raw/entry.atom", html_sha256="a" * 64, atom_sha256="b" * 64,
        source_url=URL, html_text=f'<div class="post-body entry-content">{html_body or body}</div>',
    )


def batch(root: Path, body: str = BODY) -> tuple[Path, Path]:
    raw = root / "data/raw/blogspot/verniman/html/synthetic"
    raw.mkdir(parents=True)
    files, posts = [], []
    for day in (7, 8, 9, 12, 13, 14, 15, 16, 19, 20):
        content = body.replace("Outlook 10/13", f"Outlook 10/{day}")
        url = f"https://verniman.blogspot.com/2009/10/example-{day}.html"
        html = raw / f"example-{day}.html"
        html.write_text(f'<div class="post-body entry-content">{content}</div>', encoding="utf-8")
        xml = raw / f"example-{day}.atom"
        xml.write_bytes(atom(content, url=url, source_id=str(456 + day)))
        source_files = [{"path": str(path.relative_to(root)), "sha256": sha256_file(path), "bytes": path.stat().st_size,
                         "captured_at": stamp, "kind": kind}
                        for path, kind, stamp in ((html, "html", "2026-10-20T23:31:30Z"),
                                                   (xml, "atom", "2026-10-20T23:31:31Z"))]
        files.extend(source_files)
        posts.append({"url": url, "captured_at": "2026-10-20T23:31:30Z", "html": source_files[0],
                      "atom": source_files[1], "images": []})
    manifest = raw / "batch_manifest.json"
    manifest.write_text(json.dumps({"source": "verniman", "batch_id": "synthetic", "files": files, "posts": posts}))
    request = root / "requests/fulfilled/example.yaml"
    request.parent.mkdir(parents=True)
    request.write_text("request:\n  id: synthetic\n")
    return manifest, request


class VernimanExtractionTests(unittest.TestCase):
    def test_plan_targets_labels_and_dates_are_independent_of_header_and_published(self):
        row, levels = extract()
        self.assertEqual(row["session_date"], date(2026, 10, 13))
        self.assertEqual(row["source_claimed_published_at"], datetime(2009, 10, 13, 13, 10, tzinfo=timezone.utc))
        self.assertEqual(row["source_claimed_updated_eastern"], "2026-10-13T09:05:57.412000-04:00")
        self.assertIsNone(row["available_at"])
        self.assertEqual(row["timing_status"], TIMING_STATUS)
        bullish = [item for item in levels if item["side"] == "bullish"]
        bearish = [item for item in levels if item["side"] == "bearish"]
        self.assertEqual(bullish[0]["source_label"], "HVE-YVAL")
        self.assertEqual(bearish[0]["source_label"], "HVE-YVAH")
        self.assertEqual([item["price_low"] for item in bullish], list(map(Decimal, ("7850.00", "7857.00", "7864.00", "7906.00"))))
        self.assertEqual([item["ordinal"] for item in bearish[1:]], [1, 2, 3])
        self.assertTrue(all(item["available_at"] is None for item in levels))
        self.assertNotIn(Decimal("7856.00"), [item["price_low"] for item in levels])
        self.assertNotIn(Decimal("1234.00"), [item["price_low"] for item in levels])

    def test_zone_and_observed_wording_variants(self):
        body = BODY.replace("moves above", "remains above").replace(
            "GAP 7857 YVAH 7864 and PBT 7906 all magnets.", "GAP-PBT7875-77 magnets and ATH-RTH 7897.").replace(
            "moves below", "moves remains below")
        _, levels = extract(body)
        zone = next(row for row in levels if row["source_label"] == "GAP-PBT")
        self.assertEqual((zone["price_low"], zone["price_high"]), (Decimal("7875.00"), Decimal("7877.00")))
        self.assertEqual(zone["source_text"], "GAP-PBT7875-77")
        extract(BODY.replace("buy towards", "buy"))

    def test_missing_year_cannot_be_inferred_from_image_filename_or_metadata(self):
        with self.assertRaisesRegex(ValueError, "explicit matching contract year"):
            extract(BODY.replace("(Dec2026)", ""))

    def test_different_plan_or_session_between_html_and_atom_is_rejected(self):
        for html_body in (BODY.replace("GAP 7857", "GAP 7858"), BODY.replace("Outlook 10/13", "Outlook 10/14"),
                          BODY.replace("ESZ26 (Dec2026)", "ESZ25 (Dec2025)")):
            with self.subTest(html_body=html_body), self.assertRaisesRegex(ValueError, "HTML and Atom"):
                extract(html_body=html_body)

    def test_content_revision_changes_with_source_content(self):
        first, _ = extract()
        second, _ = extract(BODY.replace("Commentary.", "Changed commentary."))
        self.assertNotEqual(first["outlook_id"], second["outlook_id"])
        self.assertEqual(first["source_post_id"], second["source_post_id"])

    def test_combined_capture_time_is_latest_without_inventing_availability(self):
        row, _ = extract_entry(
            atom(), captured_at="2026-10-20T23:31:30Z", atom_captured_at="2026-10-20T23:31:32Z",
            html_path="raw/page.html", atom_path="raw/page.atom", html_sha256="a" * 64, atom_sha256="b" * 64,
        )
        self.assertEqual(row["captured_at"].second, 32)
        self.assertEqual(row["raw_html_captured_at"].second, 30)
        self.assertEqual(row["raw_atom_captured_at"].second, 32)
        self.assertIsNone(row["available_at"])

    def test_unrecognised_or_unlabelled_numbers_fail_closed(self):
        for body in (BODY.replace("PBT 7906", "7906"), BODY.replace("GAP 7857", "GAP 7857-50")):
            with self.subTest(body=body), self.assertRaises(ValueError):
                extract(body)


class VernimanPublicationTests(unittest.TestCase):
    def test_publish_and_hash_pinned_read_with_decimal_schemas(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request = batch(root)
            manifest = publish_release(incoming, root, request)
            digest = sha256_file(manifest)
            metadata = verify_release(root, manifest, digest)
            self.assertEqual(metadata["dataset_id"], DATASET_ID)
            outlooks = load_release(root, manifest, digest)
            levels = load_release(root, manifest, digest, table="levels")
            self.assertTrue(outlooks.schema.equals(outlook_schema(), check_metadata=True))
            self.assertTrue(levels.schema.equals(levels_schema(), check_metadata=True))
            self.assertEqual((outlooks.num_rows, levels.num_rows), (10, 80))
            self.assertTrue((root / DATA_PATH / "daily_summary.csv").is_file())
            self.assertTrue((root / "data/staging/verniman/synthetic/extracted.json").is_file())
            retained = metadata["provenance"]["retained"]["files"]
            self.assertIn("abacus_bhishma/verniman_capture.py", [item["source"] for item in retained])
            self.assertIn("uv.lock", [item["source"] for item in retained])
            self.assertEqual(outlooks["captured_at"][0].as_py().second, 31)
            self.assertEqual(metadata["publication_invocation"]["arguments"]["root"], ".")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_release(root, manifest, "0" * 64)
            with self.assertRaisesRegex(ValueError, "unsupported table"):
                load_release(root, manifest, digest, table="arbitrary")

    def test_existing_outputs_and_recovery_leaves_are_never_replaced(self):
        for locator in (DATA_PATH, MANIFEST_PATH, SCHEMA_PATH, QUALITY_PATH,
                        MANIFEST_PATH.with_name(MANIFEST_PATH.name + ".part")):
            with self.subTest(locator=locator), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                incoming, request = batch(root)
                existing = root / locator
                existing.parent.mkdir(parents=True, exist_ok=True)
                existing.write_bytes(b"preserved")
                with self.assertRaises(FileExistsError):
                    publish_release(incoming, root, request)
                self.assertEqual(existing.read_bytes(), b"preserved")

    def test_symlinked_output_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request = batch(root)
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            (root / "data/curated").symlink_to(elsewhere, target_is_directory=True)
            with self.assertRaises(FileExistsError):
                publish_release(incoming, root, request)
            self.assertEqual(list(elsewhere.iterdir()), [])

    def test_failed_extraction_retains_stage_and_cannot_be_silently_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request = batch(root, BODY.replace("Outlook 10/13", "No date"))
            with self.assertRaises(ValueError):
                publish_release(incoming, root, request)
            self.assertTrue((root / "data/staging/verniman/synthetic/capture_manifest.json").is_file())
            self.assertFalse((root / MANIFEST_PATH).exists())
            with self.assertRaises(FileExistsError):
                publish_release(incoming, root, request)

    def test_raw_and_published_bytes_tampering_is_detected_without_repair(self):
        for target in ("data", "raw", "schema"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                incoming, request = batch(root)
                manifest = publish_release(incoming, root, request)
                digest = sha256_file(manifest)
                path = {"data": root / DATA_PATH / "daily_summary.csv", "schema": root / SCHEMA_PATH,
                        "raw": incoming.parent / "example-7.html"}[target]
                path.write_bytes(path.read_bytes() + b"tampered")
                before = sha256_file(path)
                with self.assertRaisesRegex(ValueError, "bytes do not match"):
                    verify_release(root, manifest, digest)
                self.assertEqual(sha256_file(path), before)

    def test_manifest_table_path_traversal_is_rejected_even_with_new_pin(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request = batch(root)
            manifest = publish_release(incoming, root, request)
            document = json.loads(manifest.read_text())
            document["tables"]["outlooks"]["path"] = "../outside.parquet"
            manifest.write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, "table path"):
                verify_release(root, manifest, sha256_file(manifest))

    def test_fixed_sample_rejects_missing_extra_and_duplicate_sessions(self):
        for kind in ("missing", "extra", "duplicate"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                incoming, request = batch(root)
                document = json.loads(incoming.read_text())
                if kind == "missing":
                    document["posts"].pop()
                elif kind == "extra":
                    document["posts"].append(document["posts"][0])
                else:
                    document["posts"][1] = document["posts"][0]
                incoming.write_text(json.dumps(document))
                with self.assertRaisesRegex(ValueError, "ten declared|duplicate outlook"):
                    publish_release(incoming, root, request)

    def test_wrong_contract_is_rejected_for_fixed_sample(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request = batch(root, BODY.replace("ESZ26", "NQZ26"))
            with self.assertRaisesRegex(ValueError, "ESZ26"):
                publish_release(incoming, root, request)


if __name__ == "__main__":
    unittest.main()
