from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from html import escape
from pathlib import Path

from abacus_bhishma.provenance import sha256_file
from abacus_bhishma.verniman_history_2021 import (
    DATA_PATH, MANIFEST_PATH, QUALITY_PATH, SCHEMA_PATH, build_tables, extract_post,
    load_release, parse_branch, parse_level_groups, publish_release, schemas, verify_release,
)

BASE = """<p>Outlook 01/02: Stock futures move on Tuesday.</p>
<p>ESH21 (Mar2021): GAP 7000</p>
<p>/ES Plan: Today's possible paths.</p>
<div>A) If market remains above HVE 7000 with bullish VIX/CVD, buy towards GAP 7010 and PBT 7020 magnets.</div>
<div>B) If market moves remains below HVE 7000 with bearish internal/delta, sell towards GAP 6990 and PBT 6980.</div>
<div>Note: Retain this discussion and image 2009 date, not as targets.</div>"""


def make_post(root: Path, *, body: str = BASE, day: str | None = "2021-01-02", identity: str = "one", atom_body: str | None = None, with_atom=True, source_updated: str = "2021-01-02T09:10:00-05:00") -> dict:
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
                "kind": kind, "captured_at": "2021-10-20T23:59:00Z" if kind == "html" else "2021-10-21T00:00:00Z"}
    return {"url": url, "captured_at": "2021-10-20T23:59:00Z", "html": record(html, "html"),
            "atom": record(xml, "atom") if with_atom else None, "images": [], "session_date": day,
            "session_date_method": "chronology_anchored_2021_12_31", "ledger_id": identity, "date_warnings": []}


def fixture(root: Path, posts: list[dict] | None = None):
    posts = posts if posts is not None else [make_post(root)]
    coverage = []
    for index in range(365):
        day = date(2021, 1, 1) + timedelta(days=index)
        urls = [post["url"] for post in posts if post["session_date"] == day.isoformat()]
        coverage.append({"session_date": day.isoformat(), "post_urls": urls,
            "status": "post_captured" if urls else ("weekend_no_dated_post" if day.weekday() >= 5 else "weekday_no_dated_post"),
            "reason": "Observed chronology; no inferred historical availability."})
    document = {"source": "verniman", "crawl_id": "synthetic_history", "requested_start_date": "2021-01-01",
                "anchor_session_date": "2021-12-31", "posts": posts, "coverage": coverage, "traversal": [],
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
            self.assertEqual(row["session_date"], date(2021, 1, 2))
            self.assertEqual(row["source_claimed_published"], "2009-01-02T09:10:00-05:00")
            self.assertEqual(row["source_claimed_published_at"].isoformat(), "2009-01-02T14:10:00+00:00")
            self.assertEqual(row["source_claimed_updated"], "2021-01-02T09:10:00-05:00")
            self.assertEqual(row["source_claimed_updated_at"].isoformat(), "2021-01-02T14:10:00+00:00")
            self.assertEqual(row["source_claimed_updated_eastern"], "2021-01-02T09:10:00-05:00")
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

    def test_2021_roll_and_fomc_soc_labels_retain_exact_source_spelling(self):
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

    def test_2021_underscore_label_and_joined_hve_separator_are_explicit(self):
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

    def test_exact_2021_mixed_case_source_labels_are_retained_with_warning(self):
        for label in ("PrevATH", "YVAl"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("GAP 6990", label + " 6990")
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                level = next(value for value in levels if value["source_label"] == label)
                self.assertEqual(level["source_text"], label + " 6990")
                self.assertEqual(level["price_low"], Decimal("6990"))
                self.assertTrue(any(value["code"] == "nonstandard_source_label" and value["source_text"] == level["source_text"] for value in issues))
        for label in ("PREVath", "YVaL", "prevATH"):
            with self.subTest(label=label), self.assertRaises(ValueError):
                parse_level_groups(label + " 6990")

    def test_lis_modifier_and_label_share_one_explicit_trigger_price(self):
        for label in ("LIS HVE", "LIS YVAH", "LIS YVAL", "LIS YPOC", "LIS YHOD", "LIS ATH"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("above HVE 7000", "above " + label + " 7000")
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                trigger = next(value for value in levels if value["side"] == "bullish" and value["role"] == "trigger")
                self.assertEqual(trigger["source_label"], label)
                self.assertEqual(trigger["source_text"], label + " 7000")
                self.assertEqual(trigger["price_low"], Decimal("7000"))
                self.assertEqual(sum(value["side"] == "bullish" and value["role"] == "trigger" for value in levels), 1)
                self.assertTrue(any(value["code"] == "compound_lis_source_label" for value in issues))
        for source in ("LIS Unknown 7000", "LIS ONH 7000", "LIS and HVE 7000"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse_level_groups(source)

    def test_parenthesized_var_annotation_and_soc_definition_do_not_become_levels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("GAP 6990", "GAP 6990 (VAR)")
            body = body.replace("<div>Note:", "<div>SOC: Scene of Crime, where an impulse move was initiated.</div><div>Note:")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIn("SOC: Scene of Crime", row["body_text"])
            self.assertNotIn("SOC:", row["bearish_scenario_text"])
            self.assertIn("(VAR)", row["bearish_scenario_text"])
            self.assertEqual(len(levels), 6)

    def test_plural_full_price_slash_points_remain_ordered_with_source_notation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = "ONH-ATH 4444.25 and PBTs 4448/4454"
            body = BASE.replace("GAP 7010 and PBT 7020 magnets", source)
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            points = [value for value in levels if value["side"] == "bullish" and value["role"] == "target"]
            self.assertEqual([value["price_low"] for value in points], list(map(Decimal, ("4444.25", "4448", "4454"))))
            self.assertEqual([value["ordinal"] for value in points], [1, 2, 3])
            self.assertEqual([value["source_text"] for value in points], ["ONH-ATH 4444.25", "PBTs 4448/4454", "PBTs 4448/4454"])
            self.assertTrue(all(value["price_low"] == value["price_high"] for value in points))
            warnings = [value for value in issues if value["code"] == "slash_separated_plural_points"]
            self.assertEqual(len(warnings), 1)
            self.assertEqual(warnings[0]["source_text"], "PBTs 4448/4454")
        for source in ("PBT 4448/4454", "PBTs 4448/54", "PBTs 4448/4454/63", "PBTs 4448/44.50"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse_level_groups(source)

    def test_unpriced_source_label_cannot_be_silently_dropped_before_valid_points(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = "ONH-ATH and PBTs 4443/4448"
            body = BASE.replace("GAP 7010 and PBT 7020 magnets", source)
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "partial")
            self.assertEqual({value["side"] for value in levels}, {"bearish"})
            self.assertIn(source, row["bullish_scenario_text"])
            failure = next(value for value in issues if value["code"] == "branch_parse_failed")
            self.assertIn("source label has no assigned explicit numeric level", failure["description"])
        for source in ("ONH and PBTs 4443-4448", "ATH pending PBTs 4443/4448"):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "source label"):
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
                body = BASE.replace("<div>Note:", f"<div>{heading} Quoting /ESH21 from 2021.") + '<div>Note 2: OPEX $3.4 trillion, $7000 inventory.</div>'
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                self.assertEqual(len(levels), 6)
                self.assertNotIn(heading, row["bearish_scenario_text"])
                self.assertIn("$3.4 trillion", row["body_text"])
                self.assertNotIn("branch_parse_failed", {value["code"] for value in issues})

    def test_missing_contract_retains_both_branch_texts_without_inventing_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("<p>ESH21 (Mar2021): GAP 7000</p>", "")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertIsNone(row["contract"])
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("buy towards GAP 7010", row["bullish_scenario_text"])
            self.assertIn("sell towards GAP 6990", row["bearish_scenario_text"])
            self.assertIn("contract_missing", {value["code"] for value in issues})

    def test_current_quoting_header_conflict_blocks_numeric_but_future_roll_does_not(self):
        cases = [
            ("Today, I'll be quoting /ESM21 as its volume is greater than /ESH21.", True),
            ("I'm quoting /ESM21 as its volume is greater than /ESH21.", True),
            ("Today, I’ll be quoting /ESM21 as its volume is greater than /ESH21.", True),
            ("Tomorrow, I'll be quoting /ESM21 when volume exceeds /ESH21.", False),
            ("Today, I'm still trading /ESH21 and I'll be quoting /ESM21 when volume from June contract is greater than March contract.", False),
            ("Today, I'll be quoting /ESM21 after the NYSE opening bell.", False),
            ("Today, I'll be quoting /ESH21 as its volume is greater than /ESM21.", False),
            ("Switch to /ESM21 when volume exceeds /ESH21.", False),
            ("Today, I start quoting Jun /ESM21 as volume is greater than Mar /ESH21 contract. (Pace of the Roll 60%)", True),
            ("Today, I start quoting Jun /ESM21 when its volume is greater than Mar /ESH21 contract.", False),
            ("I start quoting Jun /ESM21 tomorrow.", False),
            ("Today, I start quoting Mar /ESH21 as volume is greater than Jun /ESM21 contract.", False),
        ]
        for note, blocked in cases:
            with self.subTest(note=note), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE + f'<div>Rollover note: {note}</div>'
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["contract"], "ESH21")
                self.assertIn("buy towards", row["bullish_scenario_text"])
                self.assertIn("sell towards", row["bearish_scenario_text"])
                self.assertEqual(row["extraction_status"], "failed" if blocked else "complete")
                self.assertEqual(bool(levels), not blocked)
                self.assertEqual("operative_contract_header_conflict" in {value["code"] for value in issues}, blocked)

    def test_unqualified_future_quote_with_present_volume_reason_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            quote = "I'll be quoting /ESU21 as volume September contract is greater than June contract."
            body = BASE.replace("Outlook 01/02", "Outlook 06/12").replace("ESH21 (Mar2021)", "ESM21 (June2021)")
            body += "<div>REMINDER: We're into rollover week and usually rollover days show big divergences between Stocks vs. Futures, so setups that usually work well, may fail completely. " + quote + "</div>"
            row, levels, issues = extract_post(make_post(root, day="2021-06-12", body=body), root)
            self.assertEqual(row["contract"], "ESM21")
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("buy towards", row["bullish_scenario_text"])
            self.assertIn("sell towards", row["bearish_scenario_text"])
            warning = next(value for value in issues if value["code"] == "operative_contract_assignment_ambiguous")
            self.assertEqual(warning["severity"], "error")
            self.assertEqual(warning["source_text"], quote.rstrip("."))
            self.assertNotIn("operative_contract_header_conflict", {value["code"] for value in issues})
        for quote in ("I'll be quoting /ESU21 when volume September contract is greater than June contract.",
                      "I'll be quoting /ESU21 after the opening bell as volume September contract is greater than June contract.",
                      "I'll be quoting /ESU21 tomorrow as volume September contract is greater than June contract.",
                      "I'll be quoting /ESM21 as volume June contract is greater than September contract."):
            with self.subTest(quote=quote), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("ESH21 (Mar2021)", "ESM21 (June2021)") + "<div>REMINDER: " + quote + "</div>"
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
            post = make_post(root, day=None, body="<p>CTAs sell trigger support at 6512; the Big Long of 2021 is coming.</p>")
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
            post = make_post(root, body=BASE + '<div>Rollover note: switch to /ESM21 when volume exceeds /ESH21.</div>')
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["contract"], "ESH21")
            self.assertEqual({value["contract"] for value in levels}, {"ESH21"})
            self.assertIn("other_contracts_mentioned", {value["code"] for value in issues})

    def test_past_after_bell_switch_conflicting_with_heading_refuses_numbers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            quote = "I started quoting ESH22 March contract after 'NYSE Opening Bell'."
            body = BASE.replace("Outlook 01/02", "Outlook 12/10").replace("ESH21 (Mar2021)", "ESZ21 (Dec2021)")
            row, levels, issues = extract_post(make_post(root, day="2021-12-10", body=body + "<div>Note: " + quote + "</div>"), root)
            self.assertEqual(row["contract"], "ESZ21")
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("buy towards", row["bullish_scenario_text"])
            self.assertIn("sell towards", row["bearish_scenario_text"])
            failure = next(value for value in issues if value["code"] == "past_contract_switch_header_conflict")
            self.assertEqual(failure["source_text"], "Note: " + quote[:-1])
            self.assertIsNone(row["available_at"])

    def test_future_after_bell_switch_is_not_promoted_to_active_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            quote = "I'll start quoting ESZ21 December contract after NYSE Bell."
            body = BASE.replace("Outlook 01/02", "Outlook 09/10").replace("ESH21 (Mar2021)", "ESU21 (Sep2021)")
            row, levels, issues = extract_post(make_post(root, day="2021-09-10", body=body + "<div>Note: " + quote + "</div>"), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["contract"], "ESU21")
            self.assertEqual({value["contract"] for value in levels}, {"ESU21"})
            warnings = [value for value in issues if value["code"] == "future_intraday_contract_switch"]
            self.assertEqual(len(warnings), 1)
            self.assertEqual(warnings[0]["severity"], "warning")
            self.assertIn(quote[:-1], warnings[0]["source_text"])
            self.assertFalse(any(value["code"] in {"operative_contract_header_conflict", "operative_contract_assignment_ambiguous"} for value in issues))
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))

    def test_equal_volume_present_transition_has_ambiguous_contract_assignment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            quote = "I start quoting /ESM21 as June contract increases to equal volume of March /ESH21."
            body = BASE.replace("Outlook 01/02", "Outlook 03/12") + "<div>Note: " + quote + "</div>"
            row, levels, issues = extract_post(make_post(root, day="2021-03-12", body=body), root)
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(row["contract"], "ESH21")
            self.assertEqual(levels, [])
            failures = [value for value in issues if value["code"] == "operative_contract_assignment_ambiguous"]
            self.assertEqual(len(failures), 1)
            self.assertIn(quote[:-1], failures[0]["source_text"])
            self.assertIn("transition phase", failures[0]["description"])
            self.assertIn("buy towards", row["bullish_scenario_text"])
            self.assertIn("sell towards", row["bearish_scenario_text"])
            self.assertIsNone(row["available_at"])

    def test_source_year_conflict_is_not_silently_promoted_to_2021(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root, body=BASE.replace("ESH21 (Mar2021)", "ESH20 (Mar2020)"))
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2021, 1, 2))
            self.assertEqual(row["contract"], "ESH20")
            self.assertEqual(row["source_year_status"], "stale_source_year_conflict")
            self.assertEqual(levels, [])
            self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})

    def test_2021_update_does_not_promote_a_stale_2019_body(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 03/12").replace("ESH21 (Mar2021)", "ESH19 (Mar2019)")
            body += "<div>REMINDER: I'll be quoting /ESM21 tomorrow when volume is greater.</div>"
            post = make_post(root, day="2021-03-12", body=body,
                             source_updated="2021-03-12T08:47:01-05:00")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2021, 3, 12))
            self.assertEqual(row["source_claimed_updated"], "2021-03-12T08:47:01-05:00")
            self.assertEqual(row["contract"], "ESH19")
            self.assertEqual(row["body_contract_year"], 2019)
            self.assertEqual(row["source_year_status"], "stale_source_year_conflict")
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})
            self.assertIn("buy towards GAP 7010", row["bullish_scenario_text"])
            self.assertIsNone(row["available_at"])

    def test_december_30_seed_can_quote_next_delivery_year_without_redating(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 12/30").replace("ESH21 (Mar2021)", "ESH22 (Mar2022)")
            post = make_post(root, day="2021-12-30", body=body,
                             source_updated="2021-12-30T09:18:54-05:00")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2021, 12, 30))
            self.assertEqual(row["contract"], "ESH22")
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIn("contract_year_differs_from_session", {value["code"] for value in issues})
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))
            _, _, crawl = fixture(root, [post])
            coverage = build_tables(crawl, root)["coverage"].to_pylist()
            self.assertEqual(coverage[-1]["session_date"], date(2021, 12, 31))
            self.assertEqual(coverage[-1]["status"], "weekday_no_dated_post")
            self.assertEqual(coverage[-2]["post_count"], 1)

    def test_observed_december_rollover_heading_conflicts_are_retained(self):
        for day, trigger in (("2021-12-12", "3979"), ("2021-12-13", "4137")):
            with self.subTest(day=day), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("Outlook 01/02", "Outlook " + day[5:].replace("-", "/"))
                body = body.replace("ESH21 (Mar2021)", "ESZ21 (Dec2021)").replace("HVE 7000", "HVE " + trigger)
                body += "<div>Note: I'm quoting /ESH22 (Mar 2022).</div>"
                row, levels, issues = extract_post(make_post(root, day=day, body=body), root)
                self.assertEqual(row["contract"], "ESZ21")
                self.assertEqual(row["session_date"].isoformat(), day)
                self.assertEqual(row["extraction_status"], "failed")
                self.assertEqual(levels, [])
                self.assertIn("HVE " + trigger, row["bullish_scenario_text"])
                self.assertIn("HVE " + trigger, row["bearish_scenario_text"])
                conflicts = [value for value in issues if value["code"] == "operative_contract_header_conflict"]
                self.assertEqual(len(conflicts), 1)
                self.assertEqual(conflicts[0]["source_text"], "Note: I'm quoting /ESH22 (Mar 2022)")

    def test_observed_september_12_affirmative_today_quote_conflicts_with_heading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 09/12").replace("ESH21 (Mar2021)", "ESU21 (Sep2021)")
            quote = "Today, I start quoting Dec /ESZ21 as volume is greater than Sep /ESU21 contract."
            body += "<div>REMINDER: " + quote + "</div>"
            row, levels, issues = extract_post(make_post(root, day="2021-09-12", body=body), root)
            self.assertEqual(row["session_date"], date(2021, 9, 12))
            self.assertEqual(row["contract"], "ESU21")
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
            body = BASE.replace("Outlook 01/02", "Outlook 12/26").replace("ESH21 (Mar2021)", "ESH22 (Mar2022)")
            post = make_post(root, day="2021-12-26", body=body,
                             source_updated="2021-12-27T09:15:00-05:00")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2021, 12, 26))
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["source_claimed_updated"], "2021-12-27T09:15:00-05:00")
            self.assertIn("source_updated_date_differs", {value["code"] for value in issues})
            self.assertIn("source_weekday_differs", {value["code"] for value in issues})
            self.assertTrue(all(value["session_date"] == date(2021, 12, 26) for value in levels))

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
            body = BASE.replace("Outlook 01/02", "Outlook 12/31").replace("ESH21 (Mar2021)", "ESH22 (Mar2022)")
            row, levels, issues = extract_post(make_post(root, day="2021-12-31", body=body), root)
            self.assertEqual(row["session_date"], date(2021, 12, 31))
            self.assertEqual(row["contract"], "ESH22")
            self.assertEqual(row["body_contract_year"], 2022)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual({value["session_date"] for value in levels}, {date(2021, 12, 31)})
            self.assertIn("contract_year_differs_from_session", {value["code"] for value in issues})
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))

    def test_early_year_next_delivery_year_and_far_year_conflicts_fail_closed(self):
        for day, header, contract in (("2021-01-02", "01/02", "ESH22 (Mar2022)"),
                                      ("2021-12-31", "12/31", "ESH23 (Mar2023)")):
            with self.subTest(day=day, contract=contract), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("Outlook 01/02", "Outlook " + header).replace("ESH21 (Mar2021)", contract)
                row, levels, issues = extract_post(make_post(root, day=day, body=body), root)
                self.assertEqual(row["extraction_status"], "failed")
                self.assertEqual(levels, [])
                self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})

    def test_full_calendar_required_and_older_boundary_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            boundary = make_post(root, identity="boundary", day="2020-12-31", body=BASE.replace("Outlook 01/02", "Outlook 12/31"))
            _, _, crawl = fixture(root, [make_post(root), boundary])
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"].num_rows, 1)
            self.assertEqual(tables["coverage"].num_rows, 365)
            self.assertEqual(tables["coverage"]["session_date"].to_pylist()[0], date(2021, 1, 1))
            self.assertEqual(tables["coverage"]["session_date"].to_pylist()[-1], date(2021, 12, 31))
            for start, end in (("2021-01-02", "2021-12-31"), ("2021-01-01", "2021-12-30"),
                               ("2022-01-01", "2022-12-31")):
                crawl.update(requested_start_date=start, anchor_session_date=end)
                with self.assertRaisesRegex(ValueError, "complete January"):
                    build_tables(crawl, root)

    def test_malformed_three_digit_day_is_undated_and_never_repaired(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 08/276").replace("ESH21 (Mar2021)", "ESU21 (Sep2021)")
            post = make_post(root, day=None, identity="malformed_source_day", body=body,
                             source_updated="2021-08-27T09:20:00-04:00")
            row, levels, issues = extract_post(post, root)
            self.assertIsNone(row["session_date"])
            self.assertEqual(row["source_year_status"], "unresolved")
            self.assertIsNone(row["session_date_source_text"])
            self.assertIn("Outlook 08/276", row["body_text"])
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertTrue({"session_date_unresolved", "ledger_body_date_mismatch"}.issubset({value["code"] for value in issues}))
            _, _, crawl = fixture(root, [post])
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"].num_rows, 1)
            self.assertEqual(tables["coverage"].num_rows, 365)
            self.assertEqual(sum(tables["coverage"]["post_count"].to_pylist()), 0)
            self.assertEqual(tables["levels"].num_rows, 0)

    def test_nonleap_february_calendar_has_no_invented_leap_date(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 02/28")
            post = make_post(root, day="2021-02-28", body=body)
            _, _, crawl = fixture(root, [post])
            tables = build_tables(crawl, root)
            rows = tables["coverage"].to_pylist()
            self.assertEqual(len(rows), 365)
            self.assertEqual(rows[58]["session_date"], date(2021, 2, 28))
            self.assertEqual(rows[58]["post_count"], 1)
            self.assertEqual(rows[59]["session_date"], date(2021, 3, 1))
            self.assertEqual(tables["outlooks"]["session_date"].to_pylist(), [date(2021, 2, 28)])
            self.assertEqual(tables["outlooks"]["extraction_status"].to_pylist(), ["complete"])
            self.assertTrue(all(value is None for value in tables["levels"]["available_at"].to_pylist()))

    def test_weekend_stated_date_and_different_update_day_are_not_reassigned(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 10/16").replace("ESH21 (Mar2021)", "ESZ21 (Dec2021)")
            post = make_post(root, day="2021-10-16", body=body, source_updated="2021-10-14T09:17:57.596-04:00")
            row, _, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2021, 10, 16))
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIn("weekend_stated_outlook_date", {value["code"] for value in issues})
            self.assertIn("source_updated_date_differs", {value["code"] for value in issues})
            incoming, request, _ = fixture(root, [post])
            manifest = publish_release(incoming, root, request)
            self.assertIn("Weekend stated dates (1 posts)", (root / QUALITY_PATH).read_text())
            self.assertIn("2021-10-14T09:17:57.596-04:00", (root / QUALITY_PATH).read_text())
            coverage = load_release(root, manifest, sha256_file(manifest), table="coverage").to_pylist()
            by_day = {value["session_date"]: value for value in coverage}
            self.assertEqual(by_day[date(2021, 10, 16)]["post_count"], 1)
            self.assertEqual(by_day[date(2021, 10, 14)]["post_count"], 0)

    def test_duplicate_dates_and_multiple_contracts_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            posts = [make_post(root, identity="first"), make_post(root, identity="second", body=BASE.replace("ESH21 (Mar2021)", "ESM21 (Jun2021)"))]
            _, _, crawl = fixture(root, posts)
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"].num_rows, 2)
            self.assertEqual(set(tables["levels"]["contract"].to_pylist()), {"ESH21", "ESM21"})
            self.assertEqual(tables["coverage"].to_pylist()[1]["post_count"], 2)
            self.assertEqual(sum(issue["code"] == "duplicate_outlook_date" for issue in tables["issues"].to_pylist()), 2)

    def test_duplicate_body_date_is_not_reassigned_to_updated_metadata_day(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 11/08")
            posts = [make_post(root, identity="election_day", day="2021-11-08", body=body,
                               source_updated="2021-11-08T09:10:00-05:00"),
                     make_post(root, identity="election_result", day="2021-11-08", body=body,
                               source_updated="2021-11-09T08:43:48-05:00")]
            _, _, crawl = fixture(root, posts)
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"]["session_date"].to_pylist(), [date(2021, 11, 8)] * 2)
            by_day = {row["session_date"]: row for row in tables["coverage"].to_pylist()}
            self.assertEqual(by_day[date(2021, 11, 8)]["post_count"], 2)
            self.assertEqual(by_day[date(2021, 11, 9)]["post_count"], 0)
            self.assertEqual(by_day[date(2021, 11, 9)]["status"], "weekday_no_dated_post")
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
            self.assertEqual(metadata["version"], "7.0.0")
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

    def test_optional_chronology_review_is_collection_specific_and_pinned(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            boundary = make_post(root, day="2020-12-31", identity="older_boundary",
                                 body=BASE.replace("Outlook 01/02", "Outlook 12/31"))
            incoming, request, crawl = fixture(root, [make_post(root), boundary])
            review = {"requested_start_date": "2021-01-01", "anchor_session_date": "2021-12-31",
                      "retained_post_count": 1,
                      "notes": ["Synthetic review: the retained links support this calendar selection; no earlier collection discontinuity is assumed."],
                      "boundary": {"url": boundary["url"], "reviewed_session_date": "2020-12-31"}}
            review_path = root / "data/raw/synthetic/chronology_review.json"
            review_path.write_text(json.dumps(review))
            review_record = {"path": str(review_path.relative_to(root)), "sha256": sha256_file(review_path), "bytes": review_path.stat().st_size}
            crawl["files"].append(review_record)
            crawl["chronology_review"] = review_record
            incoming.write_text(json.dumps(crawl))
            manifest = publish_release(incoming, root, request)
            loaded = load_release(root, manifest, sha256_file(manifest))
            self.assertEqual(loaded.num_rows, 1)
            self.assertEqual(load_release(root, manifest, sha256_file(manifest), table="coverage").num_rows, 365)
            quality = (root / QUALITY_PATH).read_text()
            self.assertIn(review["notes"][0], quality)
            self.assertIn("[the 2020-12-31 session](https://verniman.blogspot.com/2009/01/older_boundary.html)", quality)
            self.assertIn("without recomputing years from source updates or delivery contracts", quality)
            self.assertNotIn("intentional local no-overwrite control stop", quality)
            self.assertNotIn("May 2022", quality)

    def test_review_interval_and_count_disagreement_are_refused(self):
        from abacus_bhishma.verniman_history_2021 import _quality
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            _, _, crawl = fixture(root)
            tables = build_tables(crawl, root)
            review = {"requested_start_date": "2021-01-01", "anchor_session_date": "2021-12-31",
                      "retained_post_count": 1, "notes": ["Explicit synthetic source review."]}
            for change, message in (({"anchor_session_date": "2022-12-31"}, "interval"),
                                    ({"retained_post_count": 2}, "post count"),
                                    ({"notes": []}, "review notes"),
                                    ({"boundary": {"reviewed_session_date": "2021-01-01"}}, "must precede")):
                with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                    _quality(tables, date(2021, 1, 1), date(2021, 12, 31), chronology_review={**review, **change})

    def test_gap_report_links_the_closest_captured_dates_for_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            posts = [make_post(root, day="2021-01-03", identity="earlier",
                               body=BASE.replace("Outlook 01/02", "Outlook 01/03")),
                     make_post(root, day="2021-01-05", identity="later",
                               body=BASE.replace("Outlook 01/02", "Outlook 01/05"))]
            incoming, request, _ = fixture(root, posts)
            publish_release(incoming, root, request)
            quality = (root / QUALITY_PATH).read_text()
            line = next(line for line in quality.splitlines() if line.startswith("| 2021-01-04 |"))
            self.assertIn("2021-01-03: [earlier](https://verniman.blogspot.com/2009/01/earlier.html)", line)
            self.assertIn("2021-01-05: [later](https://verniman.blogspot.com/2009/01/later.html)", line)
            self.assertIn("not source posts for an absent date", quality)

    def test_provenance_pins_prior_helpers_and_does_not_mutate_v2_identity(self):
        from abacus_bhishma import verniman_history as original
        from abacus_bhishma import verniman_history_2025 as prior_year
        from abacus_bhishma import verniman_history_2024 as prior_release
        from abacus_bhishma import verniman_history_2023 as previous_release
        from abacus_bhishma import verniman_history_2022 as preceding_release
        original_schemas = original.schemas()
        prior_schemas = prior_year.schemas()
        prior_release_schemas = prior_release.schemas()
        previous_release_schemas = previous_release.schemas()
        preceding_release_schemas = preceding_release.schemas()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request, _ = fixture(root)
            manifest = publish_release(incoming, root, request)
            metadata = json.loads(manifest.read_text())
            self.assertEqual(metadata["publication_invocation"]["entry_point"], "abacus_bhishma.verniman_history_2021")
            retained = metadata["provenance"]["retained"]["files"]
            labels = {item["source"] for item in retained}
            self.assertTrue({"abacus_bhishma/verniman_history_2021.py", "abacus_bhishma/verniman_history.py",
                             "abacus_bhishma/verniman_levels.py", "abacus_bhishma/verniman_backfill.py",
                             "abacus_bhishma/verniman_history_2022.py", "abacus_bhishma/verniman_history_2023.py", "uv.lock"}.issubset(labels))
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
            self.assertEqual(preceding_release.DATASET_ID, "verniman_daily_levels__6.0.0")
            self.assertEqual(preceding_release.VERSION, "6.0.0")
            self.assertTrue(all(schema.equals(preceding_release.schemas()[name], check_metadata=True)
                                for name, schema in preceding_release_schemas.items()))
            self.assertIn("verniman_daily_levels__6.0.0", metadata["preserved_prior_releases"])
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
            self.assertTrue((root / "data/staging/verniman/synthetic_history-v7/crawl_manifest.json").is_file())
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
