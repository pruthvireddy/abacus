from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from html import escape
from pathlib import Path

from abacus_bhishma.provenance import sha256_file
from abacus_bhishma.verniman_history_2022 import (
    DATA_PATH, MANIFEST_PATH, QUALITY_PATH, SCHEMA_PATH, build_tables, extract_post,
    load_release, parse_branch, parse_level_groups, publish_release, schemas, verify_release,
)

BASE = """<p>Outlook 01/02: Stock futures move on Tuesday.</p>
<p>ESH22 (Mar2022): GAP 7000</p>
<p>/ES Plan: Today's possible paths.</p>
<div>A) If market remains above HVE 7000 with bullish VIX/CVD, buy towards GAP 7010 and PBT 7020 magnets.</div>
<div>B) If market moves remains below HVE 7000 with bearish internal/delta, sell towards GAP 6990 and PBT 6980.</div>
<div>Note: Retain this discussion and image 2009 date, not as targets.</div>"""


def make_post(root: Path, *, body: str = BASE, day: str | None = "2022-01-02", identity: str = "one", atom_body: str | None = None, with_atom=True, source_updated: str = "2022-01-02T09:10:00-05:00") -> dict:
    raw = root / "data/raw/synthetic"
    raw.mkdir(parents=True, exist_ok=True)
    url = f"https://verniman.blogspot.com/2009/01/{identity}.html"
    html = raw / f"{identity}.html"
    html.write_text(f'<html><div class="post-body entry-content">{body}</div></html>')
    xml = raw / f"{identity}.atom"
    xml.write_text(f'<entry xmlns="http://www.w3.org/2005/Atom"><id>{identity}</id><title>{identity}</title>'
                   f'<published>2009-01-02T09:10:00-05:00</published><updated>{source_updated}</updated>'
                   f'<content type="html">{escape(atom_body if atom_body is not None else body)}</content>'
                   f'<link rel="alternate" href="{url}"/></entry>')
    def record(path, kind):
        return {"path": str(path.relative_to(root)), "sha256": sha256_file(path), "bytes": path.stat().st_size,
                "kind": kind, "captured_at": "2022-10-20T23:59:00Z" if kind == "html" else "2022-10-21T00:00:00Z"}
    return {"url": url, "captured_at": "2022-10-20T23:59:00Z", "html": record(html, "html"),
            "atom": record(xml, "atom") if with_atom else None, "images": [], "session_date": day,
            "session_date_method": "chronology_anchored_2022_12_31", "ledger_id": identity, "date_warnings": []}


def fixture(root: Path, posts: list[dict] | None = None):
    posts = posts if posts is not None else [make_post(root)]
    coverage = []
    for index in range(365):
        day = date(2022, 1, 1) + timedelta(days=index)
        urls = [post["url"] for post in posts if post["session_date"] == day.isoformat()]
        coverage.append({"session_date": day.isoformat(), "post_urls": urls,
            "status": "post_captured" if urls else ("weekend_no_dated_post" if day.weekday() >= 5 else "weekday_no_dated_post"),
            "reason": "Observed chronology; no inferred historical availability."})
    document = {"source": "verniman", "crawl_id": "synthetic_history", "requested_start_date": "2022-01-01",
                "anchor_session_date": "2022-12-31", "posts": posts, "coverage": coverage, "traversal": [],
                "traversal_reached_lower_boundary": True, "stop_reason": "lower_boundary_reached",
                "files": [record for post in posts for record in [post["html"], *([post["atom"]] if post.get("atom") else [])]]}
    incoming = root / "data/raw/synthetic/crawl_manifest.json"
    incoming.write_text(json.dumps(document))
    request = root / "requests/fulfilled/history.yaml"
    request.parent.mkdir(parents=True, exist_ok=True)
    request.write_text("request:\n  id: synthetic_history\n")
    return incoming, request, document


class HistoryExtractionTests(unittest.TestCase):
    def test_original_source_metadata_capture_times_and_session_date_stay_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            row, levels, _ = extract_post(make_post(root), root)
            self.assertEqual(row["session_date"], date(2022, 1, 2))
            self.assertEqual(row["source_claimed_published"], "2009-01-02T09:10:00-05:00")
            self.assertEqual(row["source_claimed_published_at"].isoformat(), "2009-01-02T14:10:00+00:00")
            self.assertEqual(row["source_claimed_updated"], "2022-01-02T09:10:00-05:00")
            self.assertEqual(row["source_claimed_updated_at"].isoformat(), "2022-01-02T14:10:00+00:00")
            self.assertEqual(row["source_claimed_updated_eastern"], "2022-01-02T09:10:00-05:00")
            self.assertEqual(row["captured_at"], row["raw_atom_captured_at"])
            self.assertGreater(row["captured_at"], row["raw_html_captured_at"])
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))
            self.assertEqual({value["timing_status"] for value in [row, *levels]}, {"historical_availability_unverified"})

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

    def test_explicit_plural_label_with_and_retains_separate_ordered_prices(self):
        rows, _ = parse_branch("If market moves above YHOD 5868 with bullish internals, buy towards PBTs 5882 and 5906 magnets.", "bullish")
        self.assertEqual([row["price_low"] for row in rows], list(map(Decimal, ("5868", "5882", "5906"))))
        self.assertEqual([row["ordinal"] for row in rows], [1, 1, 2])
        self.assertEqual([row["source_label"] for row in rows], ["YHOD", "PBTs", "PBTs"])
        self.assertEqual(rows[-1]["source_text"], "PBTs 5882 and 5906")
        for value in rows:
            self.assertEqual(value["price_low"], value["price_high"])
        with self.assertRaisesRegex(ValueError, "explicit plural"):
            parse_level_groups("PBT 5882 and 5906 magnets")

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

    def test_2022_roll_and_fomc_soc_labels_retain_exact_source_spelling(self):
        for label in ("Roll-GAP", "FOMC Soc", "YPOC-FOMC Soc"):
            with self.subTest(label=label):
                source = label + " 5240"
                groups = parse_level_groups(source)
                self.assertEqual(len(groups), 1)
                self.assertEqual(groups[0]["source_label"], label)
                self.assertEqual(groups[0]["source_text"], source)
                self.assertEqual(groups[0]["price_low"], Decimal("5240"))

    def test_observed_joined_towards_hve_delimiter_retains_original_spelling(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = "If market remains above YHOD 4798 with bullish internals, buy towardsHVE 4810 PBT 4817 SoC 4823 and ATH 4830."
            body = BASE.replace("If market remains above HVE 7000 with bullish VIX/CVD, buy towards GAP 7010 and PBT 7020 magnets.", source)
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["bullish_scenario_text"], source)
            selected = [value for value in levels if value["side"] == "bullish"]
            self.assertEqual([value["source_label"] for value in selected], ["YHOD", "HVE", "PBT", "SoC", "ATH"])
            self.assertEqual([value["price_low"] for value in selected], list(map(Decimal, ("4798", "4810", "4817", "4823", "4830"))))
            self.assertEqual(selected[1]["source_text"], "HVE 4810")
            warnings = [value for value in issues if value["code"] == "nonstandard_target_delimiter"]
            self.assertEqual(len(warnings), 1)
            self.assertEqual(warnings[0]["source_text"], source)
            for unsupported in ("towardsPBT 4810", "towardsUnknown 4810", "towardsHVE4810", "towardsHVE 4810 and 4820"):
                with self.subTest(unsupported=unsupported), self.assertRaises(ValueError):
                    parse_branch("If market remains above YHOD 4798 with bullish internals, buy " + unsupported, "bullish")

    def test_2022_underscore_label_and_joined_hve_separator_are_explicit(self):
        values = parse_level_groups("HVE 4540 and HVE_PBT 4550")
        self.assertEqual([value["source_label"] for value in values], ["HVE", "HVE_PBT"])
        self.assertEqual(values[1]["source_text"], "HVE_PBT 4550")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = "ONL 4592 PBT 4580HVE 4572 and GAP 4567"
            body = BASE.replace("GAP 6990 and PBT 6980", source)
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            selected = [value for value in levels if value["side"] == "bearish" and value["role"] == "target"]
            self.assertEqual([value["source_label"] for value in selected], ["ONL", "PBT", "HVE", "GAP"])
            self.assertEqual([value["price_low"] for value in selected], list(map(Decimal, ("4592", "4580", "4572", "4567"))))
            self.assertEqual([value["source_text"] for value in selected], ["ONL 4592", "PBT 4580", "HVE 4572", "GAP 4567"])
            warning = next(value for value in issues if value["code"] == "missing_level_separator")
            self.assertIn(source, warning["source_text"])
        for source in ("PBT 4580PBT 4572", "unknown4580HVE 4572", "HVE_unknown 4550"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse_level_groups(source)

    def test_integer_anchor_and_explicit_two_digit_decimal_zone_suffix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("GAP 6990 and PBT 6980", "YVAL 4193 YLOD 4191 and HVE-ONL 4187-86.50")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            zone = next(value for value in levels if value["source_label"] == "HVE-ONL")
            self.assertEqual((zone["price_low"], zone["price_high"]), (Decimal("4186.50"), Decimal("4187.00")))
            self.assertEqual(zone["source_text"], "HVE-ONL 4187-86.50")
            self.assertEqual(zone["notation"], "zone")
            self.assertEqual(sum(value["code"] == "abbreviated_decimal_zone" for value in issues), 1)
        for source in ("HVE 4187.25-86.50", "HVE 4187-6.50", "HVEs 4187-86.50", "HVE 4187-86.50-85.25"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse_level_groups(source)

    def test_unlabelled_numeric_trigger_remains_partial_without_invented_label(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("below HVE 7000", "below 4016")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "partial")
            self.assertEqual({value["side"] for value in levels}, {"bullish"})
            self.assertIn("below 4016", row["bearish_scenario_text"])
            self.assertTrue(any(value["code"] == "branch_parse_failed" and value["side"] == "bearish" for value in issues))

    def test_unlabelled_point_and_zone_conjunction_retains_partial_source_branch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("GAP 6990 and PBT 6980", "ONL-VPOC 5037 GAP 5004 and 4963-4933")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "partial")
            self.assertEqual({value["side"] for value in levels}, {"bullish"})
            self.assertIn("GAP 5004 and 4963-4933", row["bearish_scenario_text"])
            self.assertIn("GAP 5004 and 4963-4933", row["body_text"])
            self.assertTrue(any(value["code"] == "branch_parse_failed" and value["side"] == "bearish" for value in issues))

    def test_numeric_trigger_missing_never_borrows_targets_or_header_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("above HVE 7000", "above ON-VAH").replace("below HVE 7000", "below ON-VAH")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("GAP 7010", row["bullish_scenario_text"])
            self.assertIn("GAP 6990", row["bearish_scenario_text"])
            self.assertEqual({value["side"] for value in issues if value["code"] == "branch_parse_failed"}, {"bullish", "bearish"})

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
        for heading in ("Note 1:", "Note1:", "Reminder:", "Rollover week.", "FOMC days are two separate sessions."):
            with self.subTest(heading=heading), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("<div>Note:", f"<div>{heading} Quoting /ESH22 from 2022.") + '<div>Note 2: OPEX $3.4 trillion, $7000 inventory.</div>'
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                self.assertEqual(len(levels), 6)
                self.assertNotIn(heading, row["bearish_scenario_text"])
                self.assertIn("$3.4 trillion", row["body_text"])
                self.assertNotIn("branch_parse_failed", {value["code"] for value in issues})

    def test_missing_contract_retains_both_branch_texts_without_inventing_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("<p>ESH22 (Mar2022): GAP 7000</p>", "")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertIsNone(row["contract"])
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("buy towards GAP 7010", row["bullish_scenario_text"])
            self.assertIn("sell towards GAP 6990", row["bearish_scenario_text"])
            self.assertIn("contract_missing", {value["code"] for value in issues})

    def test_current_quoting_header_conflict_blocks_numeric_but_future_roll_does_not(self):
        cases = [
            ("Today, I'll be quoting /ESM22 as its volume is greater than /ESH22.", True),
            ("I'm quoting /ESM22 as its volume is greater than /ESH22.", True),
            ("Today, I’ll be quoting /ESM22 as its volume is greater than /ESH22.", True),
            ("Tomorrow, I'll be quoting /ESM22 when volume exceeds /ESH22.", False),
            ("Today, I'm still trading /ESH22 and I'll be quoting /ESM22 when volume from June contract is greater than March contract.", False),
            ("Today, I'll be quoting /ESM22 after the NYSE opening bell.", False),
            ("Today, I'll be quoting /ESH22 as its volume is greater than /ESM22.", False),
            ("Switch to /ESM22 when volume exceeds /ESH22.", False),
            ("Today, I start quoting Jun /ESM22 as volume is greater than Mar /ESH22 contract. (Pace of the Roll 60%)", True),
            ("Today, I start quoting Jun /ESM22 when its volume is greater than Mar /ESH22 contract.", False),
            ("I start quoting Jun /ESM22 tomorrow.", False),
            ("Today, I start quoting Mar /ESH22 as volume is greater than Jun /ESM22 contract.", False),
        ]
        for note, blocked in cases:
            with self.subTest(note=note), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE + f'<div>Rollover note: {note}</div>'
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["contract"], "ESH22")
                self.assertIn("buy towards", row["bullish_scenario_text"])
                self.assertIn("sell towards", row["bearish_scenario_text"])
                self.assertEqual(row["extraction_status"], "failed" if blocked else "complete")
                self.assertEqual(bool(levels), not blocked)
                self.assertEqual("operative_contract_header_conflict" in {value["code"] for value in issues}, blocked)

    def test_unqualified_future_quote_with_present_volume_reason_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            quote = "I'll be quoting /ESU22 as volume September contract is greater than June contract."
            body = BASE.replace("Outlook 01/02", "Outlook 06/12").replace("ESH22 (Mar2022)", "ESM22 (June2022)")
            body += "<div>REMINDER: We're into rollover week and usually rollover days show big divergences between Stocks vs. Futures, so setups that usually work well, may fail completely. " + quote + "</div>"
            row, levels, issues = extract_post(make_post(root, day="2022-06-12", body=body), root)
            self.assertEqual(row["contract"], "ESM22")
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("buy towards", row["bullish_scenario_text"])
            self.assertIn("sell towards", row["bearish_scenario_text"])
            warning = next(value for value in issues if value["code"] == "operative_contract_assignment_ambiguous")
            self.assertEqual(warning["severity"], "error")
            self.assertEqual(warning["source_text"], quote.rstrip("."))
            self.assertNotIn("operative_contract_header_conflict", {value["code"] for value in issues})
        for quote in ("I'll be quoting /ESU22 when volume September contract is greater than June contract.",
                      "I'll be quoting /ESU22 after the opening bell as volume September contract is greater than June contract.",
                      "I'll be quoting /ESU22 tomorrow as volume September contract is greater than June contract.",
                      "I'll be quoting /ESM22 as volume June contract is greater than September contract."):
            with self.subTest(quote=quote), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("ESH22 (Mar2022)", "ESM22 (June2022)") + "<div>REMINDER: " + quote + "</div>"
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                self.assertTrue(levels)
                self.assertNotIn("operative_contract_assignment_ambiguous", {value["code"] for value in issues})

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
            post = make_post(root, day=None, body="<p>CTAs sell trigger support at 6512; the Big Long of 2022 is coming.</p>")
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
            post = make_post(root, body=BASE + '<div>Rollover note: switch to /ESM22 when volume exceeds /ESH22.</div>')
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["contract"], "ESH22")
            self.assertEqual({value["contract"] for value in levels}, {"ESH22"})
            self.assertIn("other_contracts_mentioned", {value["code"] for value in issues})

    def test_source_year_conflict_is_not_silently_promoted_to_2022(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root, body=BASE.replace("ESH22 (Mar2022)", "ESH21 (Mar2021)"))
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2022, 1, 2))
            self.assertEqual(row["contract"], "ESH21")
            self.assertEqual(row["source_year_status"], "stale_source_year_conflict")
            self.assertEqual(levels, [])
            self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})

    def test_2022_update_does_not_promote_a_stale_2020_body(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 03/12").replace("ESH22 (Mar2022)", "ESH20 (Mar2020)")
            body += "<div>REMINDER: I'll be quoting /ESM22 tomorrow when volume is greater.</div>"
            post = make_post(root, day="2022-03-12", body=body,
                             source_updated="2022-03-12T08:47:01-05:00")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2022, 3, 12))
            self.assertEqual(row["source_claimed_updated"], "2022-03-12T08:47:01-05:00")
            self.assertEqual(row["contract"], "ESH20")
            self.assertEqual(row["body_contract_year"], 2020)
            self.assertEqual(row["source_year_status"], "stale_source_year_conflict")
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})
            self.assertIn("buy towards GAP 7010", row["bullish_scenario_text"])
            self.assertIsNone(row["available_at"])

    def test_december_30_seed_can_quote_next_delivery_year_without_redating(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 12/30").replace("ESH22 (Mar2022)", "ESH23 (Mar2023)")
            post = make_post(root, day="2022-12-30", body=body,
                             source_updated="2022-12-30T09:18:54-05:00")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2022, 12, 30))
            self.assertEqual(row["contract"], "ESH23")
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIn("contract_year_differs_from_session", {value["code"] for value in issues})
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))
            _, _, crawl = fixture(root, [post])
            coverage = build_tables(crawl, root)["coverage"].to_pylist()
            self.assertEqual(coverage[-1]["session_date"], date(2022, 12, 31))
            self.assertEqual(coverage[-1]["status"], "weekend_no_dated_post")
            self.assertEqual(coverage[-2]["post_count"], 1)

    def test_observed_december_rollover_heading_conflicts_are_retained(self):
        for day, trigger in (("2022-12-12", "3979"), ("2022-12-13", "4137")):
            with self.subTest(day=day), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("Outlook 01/02", "Outlook " + day[5:].replace("-", "/"))
                body = body.replace("ESH22 (Mar2022)", "ESZ22 (Dec2022)").replace("HVE 7000", "HVE " + trigger)
                body += "<div>Note: I'm quoting /ESH23 (Mar 2023).</div>"
                row, levels, issues = extract_post(make_post(root, day=day, body=body), root)
                self.assertEqual(row["contract"], "ESZ22")
                self.assertEqual(row["session_date"].isoformat(), day)
                self.assertEqual(row["extraction_status"], "failed")
                self.assertEqual(levels, [])
                self.assertIn("HVE " + trigger, row["bullish_scenario_text"])
                self.assertIn("HVE " + trigger, row["bearish_scenario_text"])
                conflicts = [value for value in issues if value["code"] == "operative_contract_header_conflict"]
                self.assertEqual(len(conflicts), 1)
                self.assertEqual(conflicts[0]["source_text"], "Note: I'm quoting /ESH23 (Mar 2023)")

    def test_observed_september_12_affirmative_today_quote_conflicts_with_heading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 09/12").replace("ESH22 (Mar2022)", "ESU22 (Sep2022)")
            quote = "Today, I start quoting Dec /ESZ22 as volume is greater than Sep /ESU22 contract."
            body += "<div>REMINDER: " + quote + "</div>"
            row, levels, issues = extract_post(make_post(root, day="2022-09-12", body=body), root)
            self.assertEqual(row["session_date"], date(2022, 9, 12))
            self.assertEqual(row["contract"], "ESU22")
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            conflicts = [value for value in issues if value["code"] == "operative_contract_header_conflict"]
            self.assertEqual(len(conflicts), 1)
            self.assertIn(quote.rstrip("."), conflicts[0]["source_text"])
            self.assertIn("buy towards GAP 7010", row["bullish_scenario_text"])
            self.assertIn("sell towards GAP 6990", row["bearish_scenario_text"])

    def test_observed_december_26_stated_date_keeps_weekday_and_update_conflicts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 12/26").replace("ESH22 (Mar2022)", "ESH23 (Mar2023)")
            post = make_post(root, day="2022-12-26", body=body,
                             source_updated="2022-12-27T09:15:00-05:00")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2022, 12, 26))
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["source_claimed_updated"], "2022-12-27T09:15:00-05:00")
            self.assertIn("source_updated_date_differs", {value["code"] for value in issues})
            self.assertIn("source_weekday_differs", {value["code"] for value in issues})
            self.assertTrue(all(value["session_date"] == date(2022, 12, 26) for value in levels))

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
            body = BASE.replace("Outlook 01/02", "Outlook 12/31").replace("ESH22 (Mar2022)", "ESH23 (Mar2023)")
            row, levels, issues = extract_post(make_post(root, day="2022-12-31", body=body), root)
            self.assertEqual(row["session_date"], date(2022, 12, 31))
            self.assertEqual(row["contract"], "ESH23")
            self.assertEqual(row["body_contract_year"], 2023)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual({value["session_date"] for value in levels}, {date(2022, 12, 31)})
            self.assertIn("contract_year_differs_from_session", {value["code"] for value in issues})
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))

    def test_early_year_next_delivery_year_and_far_year_conflicts_fail_closed(self):
        for day, header, contract in (("2022-01-02", "01/02", "ESH23 (Mar2023)"),
                                      ("2022-12-31", "12/31", "ESH24 (Mar2024)")):
            with self.subTest(day=day, contract=contract), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("Outlook 01/02", "Outlook " + header).replace("ESH22 (Mar2022)", contract)
                row, levels, issues = extract_post(make_post(root, day=day, body=body), root)
                self.assertEqual(row["extraction_status"], "failed")
                self.assertEqual(levels, [])
                self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})

    def test_full_calendar_required_and_older_boundary_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            boundary = make_post(root, identity="boundary", day="2021-12-31", body=BASE.replace("Outlook 01/02", "Outlook 12/31"))
            _, _, crawl = fixture(root, [make_post(root), boundary])
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"].num_rows, 1)
            self.assertEqual(tables["coverage"].num_rows, 365)
            self.assertEqual(tables["coverage"]["session_date"].to_pylist()[0], date(2022, 1, 1))
            self.assertEqual(tables["coverage"]["session_date"].to_pylist()[-1], date(2022, 12, 31))
            for start, end in (("2022-01-02", "2022-12-31"), ("2022-01-01", "2022-12-30"),
                               ("2023-01-01", "2023-12-31")):
                crawl.update(requested_start_date=start, anchor_session_date=end)
                with self.assertRaisesRegex(ValueError, "complete January"):
                    build_tables(crawl, root)

    def test_nonleap_february_calendar_has_no_invented_leap_date(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 02/28")
            post = make_post(root, day="2022-02-28", body=body)
            _, _, crawl = fixture(root, [post])
            tables = build_tables(crawl, root)
            rows = tables["coverage"].to_pylist()
            self.assertEqual(len(rows), 365)
            self.assertEqual(rows[58]["session_date"], date(2022, 2, 28))
            self.assertEqual(rows[58]["post_count"], 1)
            self.assertEqual(rows[59]["session_date"], date(2022, 3, 1))
            self.assertEqual(tables["outlooks"]["session_date"].to_pylist(), [date(2022, 2, 28)])
            self.assertEqual(tables["outlooks"]["extraction_status"].to_pylist(), ["complete"])
            self.assertTrue(all(value is None for value in tables["levels"]["available_at"].to_pylist()))

    def test_weekend_stated_date_and_different_update_day_are_not_reassigned(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 10/15").replace("ESH22 (Mar2022)", "ESZ22 (Dec2022)")
            post = make_post(root, day="2022-10-15", body=body, source_updated="2022-10-14T09:17:57.596-04:00")
            row, _, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2022, 10, 15))
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIn("weekend_stated_outlook_date", {value["code"] for value in issues})
            self.assertIn("source_updated_date_differs", {value["code"] for value in issues})
            incoming, request, _ = fixture(root, [post])
            manifest = publish_release(incoming, root, request)
            self.assertIn("Weekend stated dates (1 posts)", (root / QUALITY_PATH).read_text())
            self.assertIn("2022-10-14T09:17:57.596-04:00", (root / QUALITY_PATH).read_text())
            coverage = load_release(root, manifest, sha256_file(manifest), table="coverage").to_pylist()
            by_day = {value["session_date"]: value for value in coverage}
            self.assertEqual(by_day[date(2022, 10, 15)]["post_count"], 1)
            self.assertEqual(by_day[date(2022, 10, 14)]["post_count"], 0)

    def test_duplicate_dates_and_multiple_contracts_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            posts = [make_post(root, identity="first"), make_post(root, identity="second", body=BASE.replace("ESH22 (Mar2022)", "ESM22 (Jun2022)"))]
            _, _, crawl = fixture(root, posts)
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"].num_rows, 2)
            self.assertEqual(set(tables["levels"]["contract"].to_pylist()), {"ESH22", "ESM22"})
            self.assertEqual(tables["coverage"].to_pylist()[1]["post_count"], 2)
            self.assertEqual(sum(issue["code"] == "duplicate_outlook_date" for issue in tables["issues"].to_pylist()), 2)

    def test_duplicate_body_date_is_not_reassigned_to_updated_metadata_day(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 11/08")
            posts = [make_post(root, identity="election_day", day="2022-11-08", body=body,
                               source_updated="2022-11-08T09:10:00-05:00"),
                     make_post(root, identity="election_result", day="2022-11-08", body=body,
                               source_updated="2022-11-09T08:43:48-05:00")]
            _, _, crawl = fixture(root, posts)
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"]["session_date"].to_pylist(), [date(2022, 11, 8)] * 2)
            by_day = {row["session_date"]: row for row in tables["coverage"].to_pylist()}
            self.assertEqual(by_day[date(2022, 11, 8)]["post_count"], 2)
            self.assertEqual(by_day[date(2022, 11, 9)]["post_count"], 0)
            self.assertEqual(by_day[date(2022, 11, 9)]["status"], "weekday_no_dated_post")
            disagreements = [row for row in tables["issues"].to_pylist() if row["code"] == "source_updated_date_differs"]
            self.assertEqual(len(disagreements), 1)
            self.assertTrue(disagreements[0]["source_url"].endswith("/election_result.html"))
            self.assertEqual(sum(row["code"] == "duplicate_outlook_date" for row in tables["issues"].to_pylist()), 2)

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
            self.assertEqual(metadata["version"], "6.0.0")
            for name, schema in schemas().items():
                table = load_release(root, manifest, digest, table=name)
                self.assertTrue(table.schema.equals(schema, check_metadata=True))
            self.assertEqual(load_release(root, manifest, digest)["extraction_status"].to_pylist(), ["complete", "partial"])
            self.assertTrue((root / DATA_PATH / "daily_summary.csv").is_file())
            quality = (root / QUALITY_PATH).read_text()
            self.assertIn("Weekdays without a captured dated post", quality)
            self.assertIn("Nearest earlier captured date", quality)
            self.assertIn("not source posts for an absent date", quality)
            self.assertIn("Duplicate stated dates (1 groups)", quality)
            self.assertIn("Partial or failed numeric extraction (1 posts)", quality)
            self.assertIn("[partial](https://verniman.blogspot.com/2009/01/partial.html)", quality)
            self.assertIn("branch_parse_failed", quality)
            self.assertIn("No holiday or exchange-session eligibility is inferred", quality)
            with self.assertRaisesRegex(ValueError, "SHA256"):
                load_release(root, manifest, "0" * 64)

    def test_reviewed_large_may_to_explicit_2021_boundary_keeps_full_2022_calendar(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            current = make_post(root, day="2022-05-16", identity="may2022",
                                body=BASE.replace("Outlook 01/02", "Outlook 05/16").replace("ESH22 (Mar2022)", "ESM22 (Jun2022)"))
            boundary_body = BASE.replace("Outlook 01/02: Stock futures move on Tuesday.",
                                         "Outlook 12/31: Futures dip ahead of the final trading session of 2021.")
            boundary = make_post(root, day="2021-12-31", identity="explicit2021", body=boundary_body,
                                 source_updated="2021-12-31T09:18:44-05:00")
            boundary["original_generic_session_date"] = "2022-12-31"
            boundary["session_date_method"] = "reviewed_explicit_body_2021_and_observed_navigation"
            incoming, request, crawl = fixture(root, [current, boundary])
            review = {"encountered_2022_anchored_rows": 1, "contemporary_2022_plan_count": 1,
                      "stale_body_insertions": 0, "boundary": {"url": boundary["url"],
                      "reviewed_session_date": "2021-12-31", "original_generic_session_date": "2022-12-31",
                      "explicit_year_evidence": "final trading session of 2021"},
                      "original_capture_stop": {"stop_reason": "capture_error", "intentional_local_control_stop": True}}
            review_path = root / "data/raw/synthetic/chronology_review.json"
            review_path.write_text(json.dumps(review))
            review_record = {"path": str(review_path.relative_to(root)), "sha256": sha256_file(review_path), "bytes": review_path.stat().st_size}
            crawl["files"].append(review_record)
            crawl["chronology_review"] = review_record
            crawl["stop_reason"] = "reviewed_explicit_2021_boundary_after_observed_navigation_gap"
            incoming.write_text(json.dumps(crawl))
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"]["session_date"].to_pylist(), [date(2022, 5, 16)])
            self.assertEqual(tables["outlooks"]["contract"].to_pylist(), ["ESM22"])
            coverage = tables["coverage"].to_pylist()
            self.assertEqual(len(coverage), 365)
            self.assertEqual(coverage[0]["session_date"], date(2022, 1, 1))
            self.assertEqual(coverage[-1]["session_date"], date(2022, 12, 31))
            self.assertTrue(all(row["post_count"] == 0 for row in coverage if row["session_date"] < date(2022, 5, 16)))
            manifest = publish_release(incoming, root, request)
            loaded = load_release(root, manifest, sha256_file(manifest))
            self.assertEqual(loaded.num_rows, 1)
            self.assertNotIn("explicit2021", loaded["source_post_id"].to_pylist())
            quality = (root / QUALITY_PATH).read_text()
            self.assertIn("January 1 through 2022-05-15", quality)
            self.assertIn("[the 2021-12-31 session](https://verniman.blogspot.com/2009/01/explicit2021.html)", quality)
            self.assertIn("without recomputing years from source updates or delivery contracts", quality)
            self.assertIn("intentional local no-overwrite control stop", quality)

    def test_gap_report_links_the_closest_captured_dates_for_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            posts = [make_post(root, day="2022-01-03", identity="earlier",
                               body=BASE.replace("Outlook 01/02", "Outlook 01/03")),
                     make_post(root, day="2022-01-05", identity="later",
                               body=BASE.replace("Outlook 01/02", "Outlook 01/05"))]
            incoming, request, _ = fixture(root, posts)
            publish_release(incoming, root, request)
            quality = (root / QUALITY_PATH).read_text()
            line = next(line for line in quality.splitlines() if line.startswith("| 2022-01-04 |"))
            self.assertIn("2022-01-03: [earlier](https://verniman.blogspot.com/2009/01/earlier.html)", line)
            self.assertIn("2022-01-05: [later](https://verniman.blogspot.com/2009/01/later.html)", line)
            self.assertIn("not source posts for an absent date", quality)

    def test_provenance_pins_prior_helpers_and_does_not_mutate_v2_identity(self):
        from abacus_bhishma import verniman_history as original
        from abacus_bhishma import verniman_history_2025 as prior_year
        from abacus_bhishma import verniman_history_2024 as prior_release
        from abacus_bhishma import verniman_history_2023 as previous_release
        original_schemas = original.schemas()
        prior_schemas = prior_year.schemas()
        prior_release_schemas = prior_release.schemas()
        previous_release_schemas = previous_release.schemas()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request, _ = fixture(root)
            manifest = publish_release(incoming, root, request)
            metadata = json.loads(manifest.read_text())
            self.assertEqual(metadata["publication_invocation"]["entry_point"], "abacus_bhishma.verniman_history_2022")
            retained = metadata["provenance"]["retained"]["files"]
            labels = {item["source"] for item in retained}
            self.assertTrue({"abacus_bhishma/verniman_history_2022.py", "abacus_bhishma/verniman_history.py",
                             "abacus_bhishma/verniman_levels.py", "abacus_bhishma/verniman_backfill.py",
                             "abacus_bhishma/verniman_history_2023.py", "uv.lock"}.issubset(labels))
            self.assertEqual(original.DATASET_ID, "verniman_daily_levels__2.0.0")
            self.assertEqual(original.VERSION, "2.0.0")
            self.assertTrue(all(schema.equals(original.schemas()[name], check_metadata=True)
                                for name, schema in original_schemas.items()))
            self.assertEqual(prior_year.DATASET_ID, "verniman_daily_levels__3.0.0")
            self.assertEqual(prior_year.VERSION, "3.0.0")
            self.assertTrue(all(schema.equals(prior_year.schemas()[name], check_metadata=True)
                                for name, schema in prior_schemas.items()))
            self.assertIn("verniman_daily_levels__3.0.0", metadata["preserved_prior_releases"])
            self.assertEqual(prior_release.DATASET_ID, "verniman_daily_levels__4.0.0")
            self.assertEqual(prior_release.VERSION, "4.0.0")
            self.assertTrue(all(schema.equals(prior_release.schemas()[name], check_metadata=True)
                                for name, schema in prior_release_schemas.items()))
            self.assertIn("verniman_daily_levels__4.0.0", metadata["preserved_prior_releases"])
            self.assertEqual(previous_release.DATASET_ID, "verniman_daily_levels__5.0.0")
            self.assertEqual(previous_release.VERSION, "5.0.0")
            self.assertTrue(all(schema.equals(previous_release.schemas()[name], check_metadata=True)
                                for name, schema in previous_release_schemas.items()))
            self.assertIn("verniman_daily_levels__5.0.0", metadata["preserved_prior_releases"])
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
            self.assertTrue((root / "data/staging/verniman/synthetic_history-v6/crawl_manifest.json").is_file())
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
