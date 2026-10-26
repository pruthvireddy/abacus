from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from html import escape
from pathlib import Path

from abacus_bhishma.provenance import sha256_file
from abacus_bhishma.verniman_history_2025 import (
    DATA_PATH, MANIFEST_PATH, QUALITY_PATH, SCHEMA_PATH, build_tables, extract_post,
    load_release, parse_branch, parse_level_groups, publish_release, schemas, verify_release,
)

BASE = """<p>Outlook 01/02: Stock futures move on Thursday.</p>
<p>ESH25 (Mar2025): GAP 7000</p>
<p>/ES Plan: Today's possible paths.</p>
<div>A) If market remains above HVE 7000 with bullish VIX/CVD, buy towards GAP 7010 and PBT 7020 magnets.</div>
<div>B) If market moves remains below HVE 7000 with bearish internal/delta, sell towards GAP 6990 and PBT 6980.</div>
<div>Note: Retain this discussion and image 2009 date, not as targets.</div>"""


def make_post(root: Path, *, body: str = BASE, day: str | None = "2025-01-02", identity: str = "one", atom_body: str | None = None, with_atom=True) -> dict:
    raw = root / "data/raw/synthetic"
    raw.mkdir(parents=True, exist_ok=True)
    url = f"https://verniman.blogspot.com/2009/01/{identity}.html"
    html = raw / f"{identity}.html"
    html.write_text(f'<html><div class="post-body entry-content">{body}</div></html>')
    xml = raw / f"{identity}.atom"
    xml.write_text(f'<entry xmlns="http://www.w3.org/2005/Atom"><id>{identity}</id><title>{identity}</title>'
                   '<published>2009-01-02T09:10:00-05:00</published><updated>2025-01-02T09:10:00-05:00</updated>'
                   f'<content type="html">{escape(atom_body if atom_body is not None else body)}</content>'
                   f'<link rel="alternate" href="{url}"/></entry>')
    def record(path, kind):
        return {"path": str(path.relative_to(root)), "sha256": sha256_file(path), "bytes": path.stat().st_size,
                "kind": kind, "captured_at": "2025-10-20T23:59:00Z" if kind == "html" else "2025-10-21T00:00:00Z"}
    return {"url": url, "captured_at": "2025-10-20T23:59:00Z", "html": record(html, "html"),
            "atom": record(xml, "atom") if with_atom else None, "images": [], "session_date": day,
            "session_date_method": "chronology_anchored_2025_12_31", "ledger_id": identity, "date_warnings": []}


def fixture(root: Path, posts: list[dict] | None = None):
    posts = posts if posts is not None else [make_post(root)]
    coverage = []
    for index in range(365):
        day = date(2025, 1, 1) + timedelta(days=index)
        urls = [post["url"] for post in posts if post["session_date"] == day.isoformat()]
        coverage.append({"session_date": day.isoformat(), "post_urls": urls,
            "status": "post_captured" if urls else ("weekend_no_dated_post" if day.weekday() >= 5 else "weekday_no_dated_post"),
            "reason": "Observed chronology; no inferred historical availability."})
    document = {"source": "verniman", "crawl_id": "synthetic_history", "requested_start_date": "2025-01-01",
                "anchor_session_date": "2025-12-31", "posts": posts, "coverage": coverage, "traversal": [],
                "traversal_reached_lower_boundary": True, "stop_reason": "lower_boundary_reached",
                "files": [record for post in posts for record in [post["html"], *([post["atom"]] if post.get("atom") else [])]]}
    incoming = root / "data/raw/synthetic/crawl_manifest.json"
    incoming.write_text(json.dumps(document))
    request = root / "requests/fulfilled/history.yaml"
    request.parent.mkdir(parents=True, exist_ok=True)
    request.write_text("request:\n  id: synthetic_history\n")
    return incoming, request, document


class HistoryExtractionTests(unittest.TestCase):
    def test_plural_sequence_is_distinct_from_singular_zone(self):
        plural = parse_level_groups("PBTs 7878-7890-7902-7915 and GAPs 7803-7830 magnets")
        self.assertEqual([row["price_low"] for row in plural], list(map(Decimal, ("7878", "7890", "7902", "7915", "7803", "7830"))))
        self.assertTrue(all(row["price_low"] == row["price_high"] for row in plural))
        zone = parse_level_groups("GAP-PBT 7875-77 magnets")
        self.assertEqual((zone[0]["price_low"], zone[0]["price_high"]), (Decimal("7875"), Decimal("7877")))
        descending = parse_level_groups("PBT-GAP 7775-72 magnets")[0]
        self.assertEqual((descending["price_low"], descending["price_high"]), (Decimal("7772"), Decimal("7775")))
        self.assertEqual(descending["source_text"], "PBT-GAP 7775-72")
        full = parse_level_groups("HVE 6732-6712-6690")
        self.assertEqual([row["price_low"] for row in full], list(map(Decimal, ("6732", "6712", "6690"))))
        self.assertEqual({row["notation"] for row in full}, {"singular_full_point_sequence"})

    def test_observed_descriptors_and_wording_variants(self):
        for lead in ("If market remains above", "If market moves above", "If market moves and stays above", "If market is above"):
            rows, condition = parse_branch(f"{lead} HVE 7000 with bullish VIX/CVD, buy GAP 7010 and PBTs 7020-7030.", "bullish")
            self.assertEqual(len(rows), 4)
            self.assertEqual(condition, "bullish VIX/CVD")
        rows, _ = parse_branch("If market remains below HVE 7000 with bearish internal/delta, sell towards CTAs Sell 6990 and HVE support 6980.", "bearish")
        self.assertEqual([row["source_label"] for row in rows], ["HVE", "CTAs Sell", "HVE"])
        self.assertEqual(parse_level_groups("ONH-ATH pending 7148 magnet")[0]["price_low"], Decimal("7148"))
        self.assertEqual(parse_level_groups("JPM Collar 6500 magnet")[0]["source_label"], "JPM Collar")
        self.assertEqual(parse_level_groups("HVE 6714 (2-weeks deal SoC)")[0]["price_low"], Decimal("6714"))
        self.assertEqual(parse_level_groups("CTAs key level 6553")[0]["price_low"], Decimal("6553"))

    def test_observed_mixed_case_and_postfix_labels_preserve_source_text(self):
        values = parse_level_groups("PBT 6780 Trump-China Soc 6787 and ON-ATH 6812 all magnets")
        self.assertEqual([row["source_label"] for row in values], ["PBT", "Trump-China Soc", "ON-ATH"])
        self.assertEqual(values[1]["source_text"], "Trump-China Soc 6787")
        typo = parse_level_groups("ONl 6295 HVE 6245 and PBT-GAP 6221 magnet")
        self.assertEqual(typo[0]["source_label"], "ONl")
        self.assertEqual(typo[0]["source_text"], "ONl 6295")
        for label in ("HVE-SoC", "CPI-SoC-GAP", "YVAL-SoC", "HVE-1yrPOC"):
            self.assertEqual(parse_level_groups(label + " 6034")[0]["source_label"], label)
        with self.assertRaisesRegex(ValueError, "unassigned"):
            parse_level_groups("unknownMixedC 6034")
        rows, conditions = parse_branch("If market moves below YPOC 6659 with bearish internals/delta, sell towards GAP 6633 magnet and 6570 support.", "bearish")
        self.assertEqual([row["source_label"] for row in rows], ["YPOC", "GAP", "support"])
        self.assertEqual(rows[-1]["source_text"], "6570 support")
        self.assertEqual(rows[-1]["price_low"], Decimal("6570"))
        self.assertEqual(conditions, "bearish internals/delta")
        for text in ("GAP 6633 and 6570", "GAP 6633 and 6570 price", "PBT 6800-90-75"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_level_groups(text)

    def test_nonstandard_label_retains_case_and_has_an_explicit_warning(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            row, levels, issues = extract_post(make_post(root, body=BASE.replace("GAP 6990", "ONl 6990")), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIn("ONl", {value["source_label"] for value in levels})
            warnings = [value for value in issues if value["code"] == "nonstandard_source_label"]
            self.assertEqual(len(warnings), 1)
            self.assertEqual(warnings[0]["severity"], "warning")
            self.assertEqual(warnings[0]["source_text"], "ONl 6990")

    def test_numbered_notes_and_reminders_terminate_branch_without_inventing_targets(self):
        for heading in ("Note 1:", "Note1:", "Reminder:"):
            with self.subTest(heading=heading), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("<div>Note:", f"<div>{heading} Quoting /ESH25 from 2025.") + '<div>Note 2: OPEX $3.4 trillion, $7000 inventory.</div>'
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                self.assertEqual(len(levels), 6)
                self.assertNotIn(heading, row["bearish_scenario_text"])
                self.assertIn("$3.4 trillion", row["body_text"])
                self.assertNotIn("branch_parse_failed", {value["code"] for value in issues})

    def test_current_quoting_header_conflict_blocks_numeric_but_future_roll_does_not(self):
        cases = [
            ("Today, I'll be quoting /ESM25 as its volume is greater than /ESH25.", True),
            ("I'm quoting /ESM25 as its volume is greater than /ESH25.", True),
            ("Today, I’ll be quoting /ESM25 as its volume is greater than /ESH25.", True),
            ("Tomorrow, I'll be quoting /ESM25 when volume exceeds /ESH25.", False),
            ("Today, I'm still trading /ESH25 and I'll be quoting /ESM25 when volume from June contract is greater than March contract.", False),
            ("Today, I'll be quoting /ESM25 after the NYSE opening bell.", False),
            ("Today, I'll be quoting /ESH25 as its volume is greater than /ESM25.", False),
            ("Switch to /ESM25 when volume exceeds /ESH25.", False),
        ]
        for note, blocked in cases:
            with self.subTest(note=note), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE + f'<div>Rollover note: {note}</div>'
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["contract"], "ESH25")
                self.assertIn("buy towards", row["bullish_scenario_text"])
                self.assertIn("sell towards", row["bearish_scenario_text"])
                self.assertEqual(row["extraction_status"], "failed" if blocked else "complete")
                self.assertEqual(bool(levels), not blocked)
                self.assertEqual("operative_contract_header_conflict" in {value["code"] for value in issues}, blocked)

    def test_ambiguous_branch_does_not_drop_post_or_valid_other_branch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root, body=BASE.replace("GAP 6990 and PBT 6980", "GAP 6990-80-70"))
            outlook, levels, issues = extract_post(post, root)
            self.assertEqual(outlook["extraction_status"], "partial")
            self.assertEqual({row["side"] for row in levels}, {"bullish"})
            self.assertEqual(outlook["bearish_conditions"], "bearish internal/delta")
            self.assertTrue(any(issue["code"] == "branch_parse_failed" and issue["side"] == "bearish" for issue in issues))
            self.assertIn("GAP 6990-80-70", outlook["bearish_scenario_text"])

    def test_commentary_without_plan_is_retained_without_claiming_extraction_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root, day=None, body="<p>CTAs sell trigger support at 6512; the Big Long of 2025 is coming.</p>")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["extraction_status"], "no_explicit_plan")
            self.assertEqual(row["content_kind"], "commentary_without_explicit_daily_plan")
            self.assertEqual(levels, [])
            self.assertEqual({value["code"] for value in issues}, {"no_explicit_daily_plan"})

    def test_unlabelled_numeric_value_fails_branch_closed(self):
        with self.assertRaisesRegex(ValueError, "unassigned"):
            parse_branch("If market moves above HVE 7000 with bullish VIX/CVD, buy towards 7010 and PBT 7020.", "bullish")

    def test_html_atom_mismatch_blocks_only_affected_branch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root, atom_body=BASE.replace("GAP 6990", "GAP 6991"))
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["extraction_status"], "partial")
            self.assertEqual({value["side"] for value in levels}, {"bullish"})
            self.assertIn("html_atom_branch_mismatch", {value["code"] for value in issues})

    def test_missing_atom_still_keeps_html_evidence_with_qualification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            row, levels, issues = extract_post(make_post(root, with_atom=False), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(len(levels), 6)
            self.assertIsNone(row["source_claimed_published_at"])
            self.assertIn("atom_unavailable", {value["code"] for value in issues})

    def test_image_capture_failures_are_visible_without_discarding_plan_levels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root)
            post["capture_errors"] = [
                "image https://example.com/first.png: HTTPError: HTTP Error 400: Bad Request",
                "image https://example.com/second.png: HTTPError: HTTP Error 400: Bad Request",
            ]
            row, levels, issues = extract_post(post, root)
            failures = [item for item in issues if item["code"] == "image_capture_failed"]
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(len(levels), 6)
            self.assertEqual(len(failures), 2)
            self.assertEqual({item["source_text"] for item in failures}, set(post["capture_errors"]))
            self.assertEqual(len({item["issue_id"] for item in failures}), 2)
            self.assertTrue(all(item["severity"] == "warning" for item in failures))

    def test_rollover_commentary_does_not_change_operative_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root, body=BASE + '<div>Rollover note: switch to /ESM25 when volume exceeds /ESH25.</div>')
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["contract"], "ESH25")
            self.assertEqual({value["contract"] for value in levels}, {"ESH25"})
            self.assertIn("other_contracts_mentioned", {value["code"] for value in issues})

    def test_source_year_conflict_is_not_silently_promoted_to_2025(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root, body=BASE.replace("ESH25 (Mar2025)", "ESH24 (Mar2024)"))
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2025, 1, 2))
            self.assertEqual(row["contract"], "ESH24")
            self.assertEqual(row["source_year_status"], "stale_source_year_conflict")
            self.assertEqual(levels, [])
            self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})

    def test_missing_source_direction_remains_partial(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("remains above HVE", "moves remains HVE")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "partial")
            self.assertEqual({value["side"] for value in levels}, {"bearish"})
            self.assertIn("moves remains HVE", row["bullish_scenario_text"])
            self.assertTrue(any(value["code"] == "branch_parse_failed" and value["side"] == "bullish" for value in issues))

    def test_late_year_next_delivery_year_is_retained_without_redating(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 12/31").replace("ESH25 (Mar2025)", "ESH26 (Mar2026)")
            row, levels, issues = extract_post(make_post(root, day="2025-12-31", body=body), root)
            self.assertEqual(row["session_date"], date(2025, 12, 31))
            self.assertEqual(row["contract"], "ESH26")
            self.assertEqual(row["body_contract_year"], 2026)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual({value["session_date"] for value in levels}, {date(2025, 12, 31)})
            self.assertIn("contract_year_differs_from_session", {value["code"] for value in issues})
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))

    def test_early_year_next_delivery_year_and_far_year_conflicts_fail_closed(self):
        for day, header, contract in (("2025-01-02", "01/02", "ESH26 (Mar2026)"),
                                      ("2025-12-31", "12/31", "ESH27 (Mar2027)")):
            with self.subTest(day=day, contract=contract), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("Outlook 01/02", "Outlook " + header).replace("ESH25 (Mar2025)", contract)
                row, levels, issues = extract_post(make_post(root, day=day, body=body), root)
                self.assertEqual(row["extraction_status"], "failed")
                self.assertEqual(levels, [])
                self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})

    def test_full_calendar_required_and_older_boundary_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            boundary = make_post(root, identity="boundary", day="2024-12-31", body=BASE.replace("Outlook 01/02", "Outlook 12/31"))
            _, _, crawl = fixture(root, [make_post(root), boundary])
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"].num_rows, 1)
            self.assertEqual(tables["coverage"].num_rows, 365)
            self.assertEqual(tables["coverage"]["session_date"].to_pylist()[0], date(2025, 1, 1))
            self.assertEqual(tables["coverage"]["session_date"].to_pylist()[-1], date(2025, 12, 31))
            for start, end in (("2025-01-02", "2025-12-31"), ("2025-01-01", "2025-12-30"),
                               ("2026-01-01", "2026-12-31")):
                crawl.update(requested_start_date=start, anchor_session_date=end)
                with self.assertRaisesRegex(ValueError, "complete January"):
                    build_tables(crawl, root)

    def test_duplicate_dates_and_multiple_contracts_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            posts = [make_post(root, identity="first"), make_post(root, identity="second", body=BASE.replace("ESH25 (Mar2025)", "ESM25 (Jun2025)"))]
            _, _, crawl = fixture(root, posts)
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"].num_rows, 2)
            self.assertEqual(set(tables["levels"]["contract"].to_pylist()), {"ESH25", "ESM25"})
            self.assertEqual(tables["coverage"].to_pylist()[1]["post_count"], 2)
            self.assertEqual(sum(issue["code"] == "duplicate_outlook_date" for issue in tables["issues"].to_pylist()), 2)

    def test_failed_post_is_retained_and_every_calendar_date_is_logged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root, body=BASE.replace("A)", "No A:").replace("B)", "No B:"))
            _, _, crawl = fixture(root, [post])
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"].num_rows, 1)
            self.assertEqual(tables["outlooks"]["extraction_status"].to_pylist(), ["failed"])
            self.assertEqual(tables["levels"].num_rows, 0)
            self.assertEqual(tables["coverage"].num_rows, 365)
            crawl["coverage"].pop()
            with self.assertRaisesRegex(ValueError, "every date"):
                build_tables(crawl, root)

    def test_suspicious_and_opposite_direction_prices_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("GAP 7010", "VPOC 5691").replace("PBT 7020", "PBT 6500")
            _, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertIn(Decimal("5691"), [row["price_low"] for row in levels])
            codes = {row["code"] for row in issues}
            self.assertIn("contextual_price_outlier", codes)
            self.assertIn("target_opposite_trigger_direction", codes)


class HistoryPublicationTests(unittest.TestCase):
    def test_hash_pinned_release_preserves_partial_and_failed_posts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            posts = [make_post(root), make_post(root, identity="partial", body=BASE.replace("PBT 6980", "6980"))]
            incoming, request, _ = fixture(root, posts)
            manifest = publish_release(incoming, root, request)
            digest = sha256_file(manifest)
            metadata = verify_release(root, manifest, digest)
            self.assertEqual(metadata["version"], "3.0.0")
            for name, schema in schemas().items():
                table = load_release(root, manifest, digest, table=name)
                self.assertTrue(table.schema.equals(schema, check_metadata=True))
            self.assertEqual(load_release(root, manifest, digest)["extraction_status"].to_pylist(), ["complete", "partial"])
            self.assertTrue((root / DATA_PATH / "daily_summary.csv").is_file())
            quality = (root / QUALITY_PATH).read_text()
            self.assertIn("Weekdays without a captured dated post", quality)
            self.assertIn("Duplicate stated dates (1 groups)", quality)
            self.assertIn("Partial or failed numeric extraction (1 posts)", quality)
            self.assertIn("[partial](https://verniman.blogspot.com/2009/01/partial.html)", quality)
            self.assertIn("branch_parse_failed", quality)
            self.assertIn("No holiday or exchange-session eligibility is inferred", quality)
            with self.assertRaisesRegex(ValueError, "SHA256"):
                load_release(root, manifest, "0" * 64)

    def test_provenance_pins_prior_helpers_and_does_not_mutate_v2_identity(self):
        from abacus_bhishma import verniman_history as original
        original_schemas = original.schemas()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request, _ = fixture(root)
            manifest = publish_release(incoming, root, request)
            metadata = json.loads(manifest.read_text())
            self.assertEqual(metadata["publication_invocation"]["entry_point"], "abacus_bhishma.verniman_history_2025")
            retained = metadata["provenance"]["retained"]["files"]
            labels = {item["source"] for item in retained}
            self.assertTrue({"abacus_bhishma/verniman_history_2025.py", "abacus_bhishma/verniman_history.py",
                             "abacus_bhishma/verniman_levels.py", "abacus_bhishma/verniman_backfill.py",
                             "uv.lock"}.issubset(labels))
            self.assertEqual(original.DATASET_ID, "verniman_daily_levels__2.0.0")
            self.assertEqual(original.VERSION, "2.0.0")
            self.assertTrue(all(schema.equals(original.schemas()[name], check_metadata=True)
                                for name, schema in original_schemas.items()))
            with self.assertRaisesRegex(ValueError, "unsupported table"):
                load_release(root, manifest, sha256_file(manifest), table="unknown")

    def test_every_final_and_recovery_destination_is_refused(self):
        for locator in (DATA_PATH, MANIFEST_PATH, SCHEMA_PATH, QUALITY_PATH, MANIFEST_PATH.with_name(MANIFEST_PATH.name + ".part")):
            with self.subTest(locator=locator), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                incoming, request, _ = fixture(root)
                destination = root / locator
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(b"preserve")
                with self.assertRaises(FileExistsError):
                    publish_release(incoming, root, request)
                self.assertEqual(destination.read_bytes(), b"preserve")

    def test_failed_ledger_validation_retains_stage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request, crawl = fixture(root)
            crawl["coverage"].pop()
            incoming.write_text(json.dumps(crawl))
            with self.assertRaises(ValueError):
                publish_release(incoming, root, request)
            self.assertTrue((root / "data/staging/verniman/synthetic_history-v3/crawl_manifest.json").is_file())
            self.assertFalse((root / MANIFEST_PATH).exists())

    def test_incomplete_crawl_and_coverage_url_conflict_are_refused(self):
        for kind in ("incomplete", "url_conflict"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                incoming, request, crawl = fixture(root)
                if kind == "incomplete":
                    crawl["traversal_reached_lower_boundary"] = False
                else:
                    crawl["coverage"][1]["post_urls"] = []
                incoming.write_text(json.dumps(crawl))
                with self.assertRaisesRegex(ValueError, "completed traversal|post URLs disagree"):
                    publish_release(incoming, root, request)

    def test_tampering_and_path_traversal_are_detected_without_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request, _ = fixture(root)
            manifest = publish_release(incoming, root, request)
            digest = sha256_file(manifest)
            data = root / DATA_PATH / "daily_summary.csv"
            data.write_bytes(data.read_bytes() + b"tamper")
            before = data.read_bytes()
            with self.assertRaisesRegex(ValueError, "bytes do not match"):
                verify_release(root, manifest, digest)
            self.assertEqual(data.read_bytes(), before)
            document = json.loads(manifest.read_text())
            document["tables"]["outlooks"]["path"] = "../outside.parquet"
            manifest.write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, "table path"):
                verify_release(root, manifest, sha256_file(manifest), verify_bytes=False)


if __name__ == "__main__":
    unittest.main()
