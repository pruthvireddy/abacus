from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from html import escape
from pathlib import Path

from abacus_bhishma.provenance import sha256_file
from abacus_bhishma.verniman_history_2017 import (
    DATA_PATH, MANIFEST_PATH, QUALITY_PATH, SCHEMA_PATH, build_tables, extract_post,
    load_release, parse_branch, parse_level_groups, publish_release, schemas, verify_release,
)

BASE = """<p>Outlook 01/02: Stock futures move on Tuesday.</p>
<p>ESH17 (Mar2017): GAP 7000</p>
<p>/ES Plan: Today's possible paths.</p>
<div>A) If market remains above HVE 7000 with bullish VIX/CVD, buy towards GAP 7010 and PBT 7020 magnets.</div>
<div>B) If market moves remains below HVE 7000 with bearish internal/delta, sell towards GAP 6990 and PBT 6980.</div>
<div>Note: Retain this discussion and image 2009 date, not as targets.</div>"""


def make_post(root: Path, *, body: str = BASE, day: str | None = "2017-01-02", identity: str = "one", atom_body: str | None = None, with_atom=True, source_updated: str = "2017-01-02T09:10:00-05:00") -> dict:
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
                "kind": kind, "captured_at": "2017-10-20T23:59:00Z" if kind == "html" else "2017-10-21T00:00:00Z"}
    return {"url": url, "captured_at": "2017-10-20T23:59:00Z", "html": record(html, "html"),
            "atom": record(xml, "atom") if with_atom else None, "images": [], "session_date": day,
            "session_date_method": "chronology_anchored_2017_12_31", "ledger_id": identity, "date_warnings": []}


def fixture(root: Path, posts: list[dict] | None = None):
    posts = posts if posts is not None else [make_post(root)]
    coverage = []
    for index in range(365):
        day = date(2017, 1, 1) + timedelta(days=index)
        urls = [post["url"] for post in posts if post["session_date"] == day.isoformat()]
        coverage.append({"session_date": day.isoformat(), "post_urls": urls,
            "status": "post_captured" if urls else ("weekend_no_dated_post" if day.weekday() >= 5 else "weekday_no_dated_post"),
            "reason": "Observed chronology; no inferred historical availability."})
    document = {"source": "verniman", "crawl_id": "synthetic_history", "requested_start_date": "2017-01-01",
                "anchor_session_date": "2017-12-31", "posts": posts, "coverage": coverage, "traversal": [],
                "traversal_reached_lower_boundary": True, "stop_reason": "lower_boundary_reached",
                "files": [record for post in posts for record in [post["html"], *([post["atom"]] if post.get("atom") else [])]]}
    incoming = root / "data/raw/synthetic/crawl_manifest.json"
    incoming.write_text(json.dumps(document))
    request = root / "requests/fulfilled/history.yaml"
    request.parent.mkdir(parents=True, exist_ok=True)
    request.write_text("request:\n  id: synthetic_history\n")
    return incoming, request, document


def exhaustion_fixture(root: Path, breakage: str | None = None):
    """Synthetic independent page/body evidence for an observed-exhaustion release."""
    from abacus_bhishma.verniman_history_2017 import _validate_collection_completion
    post = make_post(root)
    context = make_post(root, identity="education", body="<p>Trading education only.</p>", day=None)
    incoming, request, crawl = fixture(root, [post])
    row, _, _ = extract_post(post, root)
    raw = root / "data/raw/synthetic"
    def saved(name, document, kind):
        path = raw / name
        path.write_text(json.dumps(document))
        record = {"kind": kind, "path": str(path.relative_to(root)), "sha256": sha256_file(path), "bytes": path.stat().st_size}
        crawl["files"].append(record)
        return record
    crawl["files"].extend([context["html"], context["atom"]])
    crawl.update({"traversal_reached_lower_boundary": False, "stop_reason": "navigation_exhausted", "excluded_context_posts": [context]})
    original = {**crawl, "posts": [post, context], "traversal": [
        {"kind": "post", "status": "captured", "source_url": post["url"], "older_url": context["url"]},
        {"kind": "post", "status": "captured", "source_url": context["url"], "older_url": None}]}
    if breakage == "original_max_stop": original["stop_reason"] = "max_posts"
    if breakage == "original_open_link": original["traversal"][-1]["older_url"] = post["url"]
    if breakage == "original_capture_failure": original["traversal"][0]["status"] = "capture_failed"
    original_record = saved("original_navigation.json", original, "original_full_chronological_crawl_manifest")
    candidate = {"source_post_id": "one", "source_url": post["url"], "normalized_feed_body_sha256": row["content_sha256"]}
    candidate_review = {"source": "verniman", "candidate_count": 1, "candidates": [candidate], "unresolved_candidate_or_year_ambiguity_records": []}
    if breakage == "candidate_body_mismatch": candidate["normalized_feed_body_sha256"] = "0" * 64
    if breakage == "candidate_url_mismatch": candidate["source_url"] = "https://example.com/other"
    if breakage == "unresolved_candidate": candidate_review["unresolved_candidate_or_year_ambiguity_records"] = [{"reason": "unknown"}]
    candidate_record = saved("independent_candidates.json", candidate_review, "independent_candidate_body_review_manifest")
    first = saved("feed-1.json", {"feed": {"entry": [{"id": {"$t": "one"}}]}}, "feed_discovery")
    empty = saved("feed-2.json", {"feed": {"entry": [] if breakage != "nonempty_probe" else [{"id": {"$t": "other"}}]}}, "feed_discovery_terminal_empty_probe")
    feed = {"source": "verniman", "feed_exhaustion_confirmed": True, "chronological_navigation_exhausted": True,
        "chronological_stop_reason": "navigation_exhausted", "chronological_final_record": original["traversal"][-1],
        "traversal_reached_lower_boundary": False, "older_2016_boundary_encountered": False,
        "observed_source_exhaustion_only": True, "chronological_crawl": original_record,
        "independent_body_review": candidate_record, "pages": [first, empty],
        "page_ranges": [{"path": first["path"], "start_index": 1, "entry_count": 1},
                        {"path": empty["path"], "start_index": 2, "entry_count": 0}],
        "terminal_next_index": 2, "feed_entry_count": 1, "unique_feed_post_ids": 1, "candidate_count": 1,
        "candidates": [{**candidate, "chronology_assigned_session_date": post["session_date"]}],
        "selected_candidate_ids": ["one"], "linked_context_record_count": 1,
        "linked_context_records": [{"source_url": context["url"]}]}
    for key in ("independent_candidates_absent_from_2017_crawl", "independent_new_in_scope_candidates_absent_from_crawl",
                "unresolved_candidate_or_year_ambiguity_records", "candidate_body_date_chronology_disagreements",
                "candidate_ids_absent_from_crawl", "crawl_ids_absent_from_feed", "content_mismatches"):
        feed[key] = []
    if breakage == "feed_not_exhausted": feed["feed_exhaustion_confirmed"] = False
    if breakage == "feed_historical_boundary": feed["older_2016_boundary_encountered"] = True
    if breakage == "feed_missing_candidate": feed["independent_candidates_absent_from_2017_crawl"] = [{"source_post_id": "other"}]
    if breakage == "feed_date_mismatch": feed["candidates"][0]["chronology_assigned_session_date"] = "2017-01-03"
    if breakage == "feed_pagination_hole": feed["page_ranges"][-1]["start_index"] = 3
    if breakage == "feed_missing_empty_probe": feed["page_ranges"].pop(); feed["pages"].pop()
    if breakage == "feed_false_count": feed["feed_entry_count"] = 2
    if breakage == "feed_false_selection": feed["selected_candidate_ids"] = ["other"]
    feed_record = saved("independent_discovery.json", feed, "independent_feed_discovery_manifest")
    review = {"kind": "verniman_2017_observed_source_exhaustion", "requested_start_date": "2017-01-01",
        "anchor_session_date": "2017-12-31", "lower_boundary_observed": False,
        "historical_full_year_completeness_claimed": False, "original_crawl": original_record,
        "feed_discovery": feed_record, "candidate_body_review": candidate_record}
    if breakage == "full_historical_claim": review["historical_full_year_completeness_claimed"] = True
    if breakage == "invented_boundary": review["lower_boundary_observed"] = True
    if breakage == "wrong_review_interval": review["requested_start_date"] = "2017-11-01"
    review_record = saved("completion_review.json", review, "collection_completion_review")
    crawl["collection_completion_review"] = review_record
    if breakage == "missing_review": crawl.pop("collection_completion_review")
    if breakage == "unretained_review": crawl["files"].remove(review_record)
    if breakage == "missing_context": crawl["excluded_context_posts"] = []
    if breakage == "dated_context": crawl["excluded_context_posts"][0]["session_date"] = "2017-01-01"
    incoming.write_text(json.dumps(crawl))
    return incoming, request, crawl


class HistoryExtractionTests(unittest.TestCase):
    def test_2017_leaning_reference_components_stay_literal_without_extra_levels(self):
        references = ("2691.50-90.50", "2594.50-96.50-98.50", "2645-2647-2651",
                      "2579-80-83", "2578-79 and 2581.50", "2572 and edge 2570")
        for reference in references:
            with self.subTest(reference=reference), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("sell towards", "try to be a seller leaning on " + reference + " towards")
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                bearish = [value for value in levels if value["side"] == "bearish"]
                self.assertEqual([value["price_low"] for value in bearish],
                                 [Decimal("7000.00"), Decimal("6990.00"), Decimal("6980.00")])
                self.assertIn("leaning on " + reference + " towards", row["bearish_scenario_text"])
                self.assertEqual([issue["source_text"] for issue in issues if issue["code"] == "source_execution_reference"],
                                 ["leaning on " + reference + " towards"])
                self.assertEqual(bearish[0]["conditions"], "bearish internal/delta")

    def test_2017_malformed_or_contradictory_ancillary_references_fail_closed(self):
        for reference in ("leaning on 99-98", "leaning on 2579-80-81-82",
                          "leaning on 2579-80-81 and 2582", "leaning on 2579-8.50",
                          "leaning on 2572 and unknown 2570", "leaning on 2572 or 2570",
                          "above 2570", "leaning on -2570", "leaning on 2570-", "leaning on 2570/2571"):
            with self.subTest(reference=reference), self.assertRaises(ValueError):
                parse_branch("If market remains below HVE 7000 with bearish internals, sell " + reference + " towards GAP 6990.", "bearish")

    def test_single_digit_next_year_delivery_is_only_qualified_late_in_anchored_2017(self):
        for day, header, expected in (("2017-01-02", "01/02", "failed"),
                                      ("2017-12-29", "12/29", "complete")):
            with self.subTest(day=day), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("ESH17 (Mar2017)", "ESH8").replace("Outlook 01/02", "Outlook " + header)
                row, levels, issues = extract_post(make_post(root, body=body, day=day), root)
                self.assertEqual(row["session_date"].isoformat(), day)
                self.assertEqual(row["contract"], "ESH8")
                self.assertEqual(row["body_contract_year"], 2018)
                self.assertEqual(row["extraction_status"], expected)
                self.assertEqual(bool(levels), expected == "complete")
                self.assertIn("single_digit_source_contract", {issue["code"] for issue in issues})

    def test_undated_daily_body_retains_original_scenarios_without_numeric_dates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02:", "Outlook:").replace("ESH17 (Mar2017):", "/ES Value:")
            post = make_post(root, body=body, day=None, source_updated="2019-04-23T08:30:00-04:00")
            row, levels, issues = extract_post(post, root)
            self.assertIsNone(row["session_date"])
            self.assertIsNone(row["contract"])
            self.assertTrue(row["source_plan_a_text"] and row["source_plan_b_text"])
            self.assertEqual(row["extraction_status"], "failed")
            self.assertFalse(levels)
            self.assertTrue({"session_date_unresolved", "ledger_body_date_mismatch"}.issubset({issue["code"] for issue in issues}))
            incoming, request, crawl = fixture(root, [post])
            manifest = publish_release(incoming, root, request)
            verify_release(root, manifest, sha256_file(manifest))
            self.assertEqual(sum(load_release(root, manifest, sha256_file(manifest), table="coverage")["post_count"].to_pylist()), 0)

    def test_exact_2017_still_quoting_claim_resolves_generic_contract_without_future_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("ESH17 (Mar2017):", "/ES Value:") + "<div>Tips: We're into the rollover week, I still quoting /ESZ7. I'll start to quote /ESH8 when volume from March contract will be greater than December contract.</div>"
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["contract"], "ESZ7")
            self.assertEqual(row["body_contract_year"], 2017)
            self.assertEqual({value["contract"] for value in levels}, {"ESZ7"})
            self.assertIn("source_contract_from_explicit_quoting", {issue["code"] for issue in issues})

    def test_2017_unqualified_start_to_quote_does_not_resolve_generic_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("ESH17 (Mar2017):", "/ES Value:") + "<div>Tips: I start to quote /ESH8 due to volume from March contract becomes greater than December /ESZ7 contract.</div>"
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertIsNone(row["contract"])
            self.assertFalse(levels)
            self.assertEqual(row["extraction_status"], "failed")
            self.assertIn("operative_contract_assignment_ambiguous", {issue["code"] for issue in issues})

    def test_single_digit_delivery_year_preserves_exact_contract_and_explicit_warning(self):
        for month in ("M", "U", "Z"):
            with self.subTest(month=month), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("ESH17 (Mar2017)", "ES" + month + "7")
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                self.assertEqual(row["contract"], "ES" + month + "7")
                self.assertEqual(row["body_contract_year"], 2017)
                self.assertEqual({value["contract"] for value in levels}, {"ES" + month + "7"})
                self.assertIn("single_digit_source_contract", {value["code"] for value in issues})
                incoming, request, _ = fixture(root, [make_post(root, body=body)])
                manifest = publish_release(incoming, root, request)
                verify_release(root, manifest, sha256_file(manifest))

    def test_single_digit_explicit_parenthesized_year_must_agree(self):
        for header, expected in (("ESM7 (Jun2017)", "complete"), ("ESM7 (Jun2016)", "failed")):
            with self.subTest(header=header), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                row, levels, issues = extract_post(make_post(root, body=BASE.replace("ESH17 (Mar2017)", header)), root)
                self.assertEqual(row["extraction_status"], expected)
                if expected == "failed":
                    self.assertFalse(levels)
                    self.assertIn("contract_year_inconsistent", {value["code"] for value in issues})

    def test_generic_es_value_heading_preserves_unadjusted_prices_without_inventing_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("ESH17 (Mar2017):", "/ES Value:")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIsNone(row["contract"])
            self.assertIsNone(row["body_contract_year"])
            self.assertEqual(row["product"], "ES")
            self.assertTrue(levels)
            self.assertTrue(all(value["contract"] is None for value in levels))
            self.assertTrue(row["source_plan_a_text"] and row["source_plan_b_text"])
            self.assertIn("source_contract_unspecified", {value["code"] for value in issues})
            incoming, request, _ = fixture(root, [make_post(root, body=body)])
            manifest = publish_release(incoming, root, request)
            verify_release(root, manifest, sha256_file(manifest))
            self.assertNotIn("__v11_", (root / DATA_PATH / "levels.csv").read_text())

    def test_neutral_no_mans_land_branch_stays_text_without_direction_or_levels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            neutral = "If market opens within ON value 2738-2732, stay aside until buyers or sellers break that 'No Man's Land' Zone."
            body = BASE.replace("If market remains above HVE 7000 with bullish VIX/CVD, buy towards GAP 7010 and PBT 7020 magnets.", neutral)
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["source_plan_a_text"], neutral)
            self.assertEqual(row["extraction_status"], "partial")
            self.assertIsNone(row["bullish_source_plan_branch"])
            self.assertEqual({value["side"] for value in levels}, {"bearish"})
            self.assertIn("branch_direction_ambiguous", {value["code"] for value in issues})

    def test_source_c_can_supply_bearish_branch_while_neutral_a_remains_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            neutral = "If market opens within ON value 2738-2732, stay aside until buyers or sellers break that 'No Man's Land' Zone."
            body = BASE.replace("A)", "B)").replace("B) If market moves", "C) If market moves")
            body = body.replace("<div>B)", "<div>A) " + neutral + "</div><div>B)")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["source_plan_a_text"], neutral)
            self.assertEqual(row["bullish_source_plan_branch"], "B")
            self.assertEqual(row["bearish_source_plan_branch"], "C")
            self.assertEqual({value["source_plan_branch"] for value in levels}, {"B", "C"})
            self.assertTrue(row["source_plan_c_text"])
            self.assertIn("branch_direction_ambiguous", {value["code"] for value in issues})
            incoming, request, _ = fixture(root, [make_post(root, body=body)])
            manifest = publish_release(incoming, root, request)
            verify_release(root, manifest, sha256_file(manifest))
            self.assertIn("source_plan_c_text", (root / DATA_PATH / "daily_summary.csv").read_text())

    def test_neutral_c_keeps_source_text_without_extra_numeric_side(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("<div>Note:", "<div>C) If market remains within 7000-7010 wait for breakout.</div><div>Note:")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIn("7000-7010", row["source_plan_c_text"])
            self.assertEqual(len(levels), 6)
            self.assertIn("branch_direction_ambiguous", {value["code"] for value in issues})

    def test_generic_heading_explicit_current_quote_can_assign_literal_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("ESH17 (Mar2017):", "/ES Value:") + "<div>Tips: I'm still quoting old contract /ESH7 until new /ESM7 increases to equal volume of March contract.</div>"
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["contract"], "ESH7")
            self.assertTrue(all(value["contract"] == "ESH7" for value in levels))
            self.assertIn("source_contract_from_explicit_quoting", {value["code"] for value in issues})

    def test_generic_heading_ambiguous_new_contract_does_not_pick_first_token(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("ESH17 (Mar2017):", "/ES Value:") + "<div>Tips: I start quoting new contract /ESM7.</div>"
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "failed")
            self.assertIsNone(row["contract"])
            self.assertFalse(levels)
            self.assertIn("operative_contract_assignment_ambiguous", {value["code"] for value in issues})

    def test_still_quoting_another_year_conflicts_with_explicit_heading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE + "<div>Rollover starts. I'm still quoting /ESH20 until /ESM20 increases to equal volume of March.</div>"
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "failed")
            self.assertFalse(levels)
            self.assertIn("operative_contract_header_conflict", {value["code"] for value in issues})

    def test_lean_only_requires_below_and_explicit_bearish_internals(self):
        source = "If market remains below YLOD 2873.25 with bearish internals, try to lean on 2873 towards HVE 2864 and PBT-GAP 2857.75 'Look below and fail' is a bullish signal."
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("If market moves remains below HVE 7000 with bearish internal/delta, sell towards GAP 6990 and PBT 6980.", source)
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            bearish = [value for value in levels if value["side"] == "bearish"]
            self.assertEqual(bearish[0]["price_low"], Decimal("2873.25"))
            self.assertEqual([value["price_low"] for value in bearish if value["role"] == "target"], [Decimal("2864.00"), Decimal("2857.75")])
            self.assertIn("2873 towards", row["bearish_scenario_text"])
            self.assertTrue({"source_lean_on_wording", "source_execution_reference", "source_branch_annotation"}.issubset({value["code"] for value in issues}))
        for old, new in (("below", "above"), ("bearish internals", "bullish internals"), (" with bearish internals", ""), ("2873 towards", "2873-72 towards"), ("HVE 2864", "2864")):
            with self.subTest(replacement=new), self.assertRaises(ValueError):
                parse_branch(source.replace(old, new, 1), "bearish")

    def test_ancillary_execution_reference_is_not_threshold_or_target(self):
        for action in ("buy above 7001 towards", "become a buyer leaning on 6999-7002 towards", "try to buy around 6999 towards"):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("buy towards", action).replace("PBT 7020 magnets.", "PBT 7020 magnets. 'Look above and fail' is a bearish signal.")
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                selected = [value for value in levels if value["side"] == "bullish"]
                self.assertEqual([value["price_low"] for value in selected], [Decimal("7000"), Decimal("7010"), Decimal("7020")])
                self.assertEqual(row["bullish_conditions"], "bullish VIX/CVD")
                self.assertTrue({"source_execution_reference", "source_branch_annotation"}.issubset({value["code"] for value in issues}))

    def test_trailing_failure_annotation_keeps_prices_without_counting_as_targets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("PBT 7020 magnets.", "PBT 7020. Failure to take out ONH 7030 early (1st 30m) is a signal of weakness.")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(len(levels), 6)
            self.assertIn("ONH 7030", row["bullish_scenario_text"])
            self.assertIn("ONH 7030", next(value["source_text"] for value in issues if value["code"] == "source_branch_annotation"))

    def test_null_contract_exception_requires_exact_generic_source_and_warning(self):
        import pyarrow as pa
        from abacus_bhishma.verniman_history_2017 import _validate_tables
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("ESH17 (Mar2017):", "/ES Value:")
            _, _, crawl = fixture(root, [make_post(root, body=body)])
            tables = build_tables(crawl, root)
            _validate_tables(tables, date(2017, 1, 1), date(2017, 12, 31))
            for change in ("missing_warning", "missing_heading", "mentioned_contract", "wrong_product"):
                with self.subTest(change=change):
                    rows = {name: table.to_pylist() for name, table in tables.items()}
                    if change == "missing_warning": rows["issues"] = [row for row in rows["issues"] if row["code"] != "source_contract_unspecified"]
                    elif change == "missing_heading": rows["outlooks"][0]["body_text"] = rows["outlooks"][0]["body_text"].replace("/ES Value:", "Generic Value:")
                    elif change == "mentioned_contract": rows["outlooks"][0]["body_text"] += "\nESH7"
                    else: rows["outlooks"][0]["product"] = "NQ"
                    changed = {name: pa.Table.from_pylist(value, schema=schemas()[name]) for name, value in rows.items()}
                    with self.assertRaisesRegex(ValueError, "null delivery contract"):
                        _validate_tables(changed, date(2017, 1, 1), date(2017, 12, 31))

    def test_explicit_plural_full_prices_can_be_space_separated(self):
        for source, expected in (("HVEs 2845 2838", ["2845.00", "2838.00"]), ("HVEs 2680 2690 and 2700", ["2680.00", "2690.00", "2700.00"])):
            with self.subTest(source=source):
                selected = parse_level_groups(source)
                self.assertEqual([str(value["price_low"]) for value in selected], expected)
                self.assertTrue(all(value["source_text"] == source for value in selected))
        for source in ("HVE 2845 2838", "PBT 2733 2741", "HVEs 2680 90", "HVEs 2680-90 2700"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse_level_groups(source)

    def test_mixed_case_edge_labels_and_on_qualifier_preserve_source_spelling(self):
        for label in ("Edge-LIS", "Edge-LVN", "Edge", "edge", "HGap"):
            with self.subTest(label=label):
                self.assertEqual(parse_level_groups(label + " 2700")[0]["source_label"], label)
        self.assertEqual(parse_level_groups("LVN-VAH (ON) 2923")[0]["source_text"], "LVN-VAH (ON) 2923")

    def test_generic_heading_with_unsupported_contract_token_cannot_hide_as_unspecified(self):
        for mention in ("ESZ7", "esh8", "ESM18"):
            with self.subTest(mention=mention), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("ESH17 (Mar2017):", "/ES Value:") + "<div>Tips: Future contract " + mention + ".</div>"
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "failed")
                self.assertIsNone(row["contract"])
                self.assertFalse(levels)
                self.assertIn("operative_contract_assignment_ambiguous", {value["code"] for value in issues})

    def test_explicit_2017_nominal_actions_keep_source_letters_and_conditions(self):
        for buyer, seller in (("be a buyer", "be a seller"), ("become a buyer", "become a seller")):
            for reverse in (False, True):
                with self.subTest(buyer=buyer, seller=seller, reverse=reverse), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary).resolve()
                    body = BASE.replace("buy towards", buyer + " towards").replace("sell towards", seller + " towards")
                    if reverse:
                        body = body.replace("A)", "PLACEHOLDER)").replace("B)", "A)").replace("PLACEHOLDER)", "B)")
                    row, levels, issues = extract_post(make_post(root, body=body), root)
                    self.assertEqual(row["extraction_status"], "complete")
                    self.assertEqual(row["bullish_conditions"], "bullish VIX/CVD")
                    self.assertEqual(row["bearish_conditions"], "bearish internal/delta")
                    self.assertEqual(row["bullish_source_plan_branch"], "B" if reverse else "A")
                    self.assertEqual(row["bearish_source_plan_branch"], "A" if reverse else "B")
                    self.assertIn(buyer, row["bullish_scenario_text"])
                    self.assertIn(seller, row["bearish_scenario_text"])
                    self.assertEqual({value["source_text"] for value in issues if value["code"] == "source_nominal_action_wording"}, {buyer, seller})
                    self.assertEqual(len(levels), 6)
                    _, _, crawl = fixture(root, [make_post(root, body=body)])
                    from abacus_bhishma.verniman_history_2017 import _validate_tables
                    _validate_tables(build_tables(crawl, root), date(2017, 1, 1), date(2017, 12, 31))

    def test_nominal_action_contradictions_and_unsupported_wording_stay_unassigned(self):
        for phrase in ("be a seller", "become a seller", "be buyers", "become bullish"):
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                row, levels, issues = extract_post(make_post(root, body=BASE.replace("buy towards", phrase + " towards")), root)
                self.assertEqual(row["extraction_status"], "partial")
                self.assertIsNone(row["bullish_source_plan_branch"])
                self.assertEqual({value["side"] for value in levels}, {"bearish"})
                self.assertIn(phrase, row["source_plan_a_text"])
                self.assertIn("branch_direction_ambiguous", {value["code"] for value in issues})

    def test_nominal_action_does_not_supply_a_missing_trigger_label(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("above HVE 7000", "above 7000").replace("buy towards", "become a buyer towards")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["bullish_source_plan_branch"], "A")
            self.assertEqual(row["bullish_conditions"], "bullish VIX/CVD")
            trigger = next(value for value in levels if value["side"] == "bullish" and value["role"] == "trigger")
            self.assertIsNone(trigger["source_label"])
            self.assertEqual(trigger["source_text"], "7000")
            self.assertIn("unlabelled_trigger_price", {value["code"] for value in issues})

    def test_2017_headings_and_separate_comment_paragraphs_stop_numeric_extraction(self):
        for heading in ("Tips:", "Basics:", "Quotes:", "Notice:", "Today's Economic Calendar", "Disclaimer:", "Questions via", "Glossary of terms", "Expiration Week.", "When VIX climbs above 20,"):
            with self.subTest(heading=heading), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("<div>Note:", "<div>" + heading + " HVE 9876 Calendar 09:45:")
                row, levels, _ = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                self.assertNotIn("9876", row["bearish_scenario_text"])
                self.assertIn("9876", row["body_text"])
                self.assertEqual(len(levels), 6)

    def test_unheaded_comment_inside_same_source_paragraph_is_not_silently_cut(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("PBT 6980.</div>", "PBT 6980. When VIX climbs above 20, manage risk.</div>")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "partial")
            self.assertEqual({value["side"] for value in levels}, {"bullish"})
            self.assertIn("When VIX", row["bearish_scenario_text"])
            self.assertIn("branch_parse_failed", {value["code"] for value in issues})

    def test_2017_lis_modifier_orders_and_hyphenated_compounds_share_one_price(self):
        for label in ("LIS YHOD HVE", "LIS YPOC HVE", "LIS LVN YVAH", "LIS HVE-YVAH", "LIS YLOD-HVE", "HVE LIS"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("HVE 7000", label + " 7000")
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                self.assertEqual([value["source_label"] for value in levels if value["role"] == "trigger"], [label, label])
                self.assertEqual(sum(value["code"] == "compound_lis_source_label" for value in issues), 2)
                self.assertEqual(len(levels), 6)
        with self.assertRaises(ValueError):
            parse_level_groups("LIS UNKNOWN HVE 7000")

    def test_2017_tariffs_compound_and_eth_annotation_preserve_source_claims(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("GAP 7010 and PBT 7020", "HVE Tariffs SoC 7010 and ATH (ETH) 7020")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            targets = [value for value in levels if value["side"] == "bullish" and value["role"] == "target"]
            self.assertEqual([value["source_label"] for value in targets], ["HVE Tariffs SoC", "ATH"])
            self.assertEqual([value["source_text"] for value in targets], ["HVE Tariffs SoC 7010", "ATH (ETH) 7020"])
            self.assertTrue({"nonstandard_source_label", "source_level_session_qualifier"}.issubset({value["code"] for value in issues}))
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))

    def test_2017_preposed_and_since_bell_future_quotes_keep_header_qualified(self):
        for quote in ("Pace of the Roll now is 48% so, after the bell, I'll start quoting /ESM17.",
                      "I'll start quoting /ESM17 June contract since NYSE opening bell."):
            with self.subTest(quote=quote), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                row, levels, issues = extract_post(make_post(root, body=BASE + "<div>Note: " + quote + "</div>"), root)
                self.assertEqual(row["extraction_status"], "complete")
                self.assertEqual({value["contract"] for value in levels}, {"ESH17"})
                self.assertIn("future_intraday_contract_switch", {value["code"] for value in issues})
                self.assertFalse({"operative_contract_header_conflict", "operative_contract_assignment_ambiguous"}.intersection(value["code"] for value in issues))
                self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))

    def test_source_letters_and_economic_direction_are_separate_for_normal_and_reversed_plans(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE
                if reverse:
                    body = body.replace("A)", "PLACEHOLDER)").replace("B)", "A)").replace("PLACEHOLDER)", "B)")
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                self.assertEqual(row["bullish_source_plan_branch"], "B" if reverse else "A")
                self.assertEqual(row["bearish_source_plan_branch"], "A" if reverse else "B")
                self.assertIn("above HVE 7000", row["bullish_scenario_text"])
                self.assertIn("below HVE 7000", row["bearish_scenario_text"])
                self.assertIn("below" if reverse else "above", row["source_plan_a_text"])
                self.assertEqual("source_plan_letters_reversed" in {value["code"] for value in issues}, reverse)
                for level in levels:
                    self.assertEqual(level["source_plan_branch"], row[f"{level['side']}_source_plan_branch"])
                incoming, request, _ = fixture(root, [make_post(root, body=body)])
                manifest = publish_release(incoming, root, request)
                verify_release(root, manifest, sha256_file(manifest))
                import csv
                with (root / DATA_PATH / "daily_summary.csv").open() as stream:
                    summary = next(csv.DictReader(stream))
                self.assertEqual(summary["bullish_source_plan_branch"], "B" if reverse else "A")
                self.assertEqual(summary["source_plan_a_text"], row["source_plan_a_text"])

    def test_contradictory_direction_action_or_confirmation_does_not_invent_a_side(self):
        for source in ("If market moves below HVE 7000 with bullish internals, buy towards GAP 7010.",
                       "If market moves above HVE 7000 with bearish internals, buy towards GAP 7010.",
                       "If market moves above HVE 7000 with bullish internals, sell towards GAP 6990."):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("If market remains above HVE 7000 with bullish VIX/CVD, buy towards GAP 7010 and PBT 7020 magnets.", source)
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "partial")
                self.assertEqual(row["source_plan_a_text"], source)
                self.assertIsNone(row["bullish_source_plan_branch"])
                self.assertIsNone(row["bullish_scenario_text"])
                self.assertEqual({value["side"] for value in levels}, {"bearish"})
                self.assertIn("branch_direction_ambiguous", {value["code"] for value in issues})

    def test_two_consistent_branches_for_same_side_fail_that_side_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("below HVE 7000 with bearish internal/delta, sell", "above HVE 7000 with bullish internal/delta, buy")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertTrue(row["source_plan_a_text"] and row["source_plan_b_text"])
            self.assertIsNone(row["bullish_source_plan_branch"])
            self.assertIsNone(row["bearish_source_plan_branch"])
            self.assertIn("multiple_source_branches_for_side", {value["code"] for value in issues})

    def test_duplicate_source_a_letters_preserve_both_texts_without_relabelling(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            row, levels, issues = extract_post(make_post(root, body=BASE.replace("B)", "A)")), root)
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("above HVE 7000", row["source_plan_a_text"])
            self.assertIn("below HVE 7000", row["source_plan_a_text"])
            self.assertIsNone(row["source_plan_b_text"])
            self.assertIn("branch_duplicated", {value["code"] for value in issues})

    def test_html_atom_letter_disagreement_refuses_matching_economic_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            reversed_body = BASE.replace("A)", "PLACEHOLDER)").replace("B)", "A)").replace("PLACEHOLDER)", "B)")
            row, levels, issues = extract_post(make_post(root, atom_body=reversed_body), root)
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertEqual(row["bullish_source_plan_branch"], "B")
            self.assertEqual(sum(value["code"] == "html_atom_branch_mismatch" for value in issues), 2)

    def test_additive_schema_fields_and_direction_mapping_are_validated(self):
        import pyarrow as pa
        from abacus_bhishma.verniman_history_2017 import _validate_tables, schema_document
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            _, _, crawl = fixture(root)
            tables = build_tables(crawl, root)
            document = schema_document()
            self.assertIn("source_plan_branch", {field["name"] for field in document["tables"]["levels"]})
            self.assertIn("source_plan_a_text", {field["name"] for field in document["tables"]["outlooks"]})
            _validate_tables(tables, date(2017, 1, 1), date(2017, 12, 31))
            for table_name, field, replacement in (("levels", "source_plan_branch", "B"),
                                                    ("outlooks", "bullish_source_plan_branch", "B"),
                                                    ("outlooks", "source_plan_a_text", "Incorrect source text")):
                with self.subTest(table_name=table_name, field=field):
                    rows = tables[table_name].to_pylist()
                    index = next((index for index, row in enumerate(rows) if row.get("side") == "bullish"), 0)
                    rows[index][field] = replacement
                    corrupted = dict(tables)
                    corrupted[table_name] = pa.Table.from_pylist(rows, schema=schemas()[table_name])
                    with self.assertRaisesRegex(ValueError, "source letter|source-letter|contradicts"):
                        _validate_tables(corrupted, date(2017, 1, 1), date(2017, 12, 31))

    def test_observed_2017_lis_compounds_share_exactly_one_explicit_level(self):
        for suffix in ("LVN", "POC", "YLOD", "HVE YVAH", "HVE YVAL", "YVAL HVE", "YLOD HVE", "YPOC-HVE", "YVAL-HVE", "HVE-YPOC", "HVE-YVAL", "ON-HVE", "ON-POC", "ON-VAH", "ON-VAL", "YHOD-HVE", "YHOD-YVAH", "YVAH-HVE"):
            with self.subTest(suffix=suffix):
                source = f"LIS {suffix} 3207-3205"
                values = parse_level_groups(source)
                self.assertEqual(len(values), 1)
                self.assertEqual(values[0]["source_label"], "LIS " + suffix)
                self.assertEqual(values[0]["source_text"], source)
                self.assertEqual((values[0]["price_low"], values[0]["price_high"]), (Decimal("3205"), Decimal("3207")))
        with self.assertRaises(ValueError):
            parse_level_groups("LIS UNKNOWN 3207")

    def test_explicit_rth_market_limit_labels_remain_qualified_source_claims(self):
        for label in ("RTH Limit Down", "RTH limit"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("GAP 6990 and PBT 6980", f"{label} 2501.50 and LVN-PBT 2300")
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                targets = [value for value in levels if value["side"] == "bearish" and value["role"] == "target"]
                self.assertEqual(targets[0]["source_label"], label)
                self.assertEqual(targets[0]["price_low"], Decimal("2501.50"))
                self.assertTrue(any(value["code"] == "source_market_limit_claim" and value["source_text"] == label + " 2501.50" for value in issues))

    def test_original_source_metadata_capture_times_and_session_date_stay_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            row, levels, _ = extract_post(make_post(root), root)
            self.assertEqual(row["session_date"], date(2017, 1, 2))
            self.assertEqual(row["source_claimed_published"], "2009-01-02T09:10:00-05:00")
            self.assertEqual(row["source_claimed_published_at"].isoformat(), "2009-01-02T14:10:00+00:00")
            self.assertEqual(row["source_claimed_updated"], "2017-01-02T09:10:00-05:00")
            self.assertEqual(row["source_claimed_updated_at"].isoformat(), "2017-01-02T14:10:00+00:00")
            self.assertEqual(row["source_claimed_updated_eastern"], "2017-01-02T09:10:00-05:00")
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

    def test_2017_roll_and_fomc_soc_labels_retain_exact_source_spelling(self):
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

    def test_2017_underscore_label_and_joined_hve_separator_are_explicit(self):
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

    def test_exact_2017_mixed_case_source_labels_are_retained_with_warning(self):
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

    def test_single_unlabelled_numeric_trigger_is_retained_without_invented_label(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("below HVE 7000", "below 4016")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual({value["side"] for value in levels}, {"bullish", "bearish"})
            self.assertIn("below 4016", row["bearish_scenario_text"])
            trigger = next(value for value in levels if value["side"] == "bearish" and value["role"] == "trigger")
            self.assertIsNone(trigger["source_label"])
            self.assertEqual((trigger["price_low"], trigger["price_high"]), (Decimal("4016"), Decimal("4016")))
            self.assertTrue(any(value["code"] == "unlabelled_trigger_price" and value["side"] == "bearish" for value in issues))

    def test_unlabelled_trigger_ranges_lists_and_extra_numbers_are_refused(self):
        for source in ("7000-7001", "7000/7001", "7000 and 7001", "7000 7001", "7000 (7001)", "7000.123"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse_branch(f"If market moves above {source} with bullish internals, buy towards GAP 7010.", "bullish")
        for source in ("7000", "7000.25", "7000.5"):
            with self.subTest(source=source):
                rows, _ = parse_branch(f"If market moves above {source} with bullish internals, buy towards GAP 7010.", "bullish")
                self.assertIsNone(rows[0]["source_label"])
                self.assertEqual(rows[0]["source_text"], source)
                self.assertEqual(rows[0]["price_low"], Decimal(source))
                self.assertEqual(rows[0]["price_high"], Decimal(source))
                self.assertEqual(rows[0]["notation"], "point")

    def test_null_source_labels_are_bounded_to_exact_source_trigger_points(self):
        import pyarrow as pa
        from abacus_bhishma.verniman_history_2017 import _validate_tables
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("above HVE 7000", "above 7000")
            _, _, crawl = fixture(root, [make_post(root, body=body)])
            tables = build_tables(crawl, root)
            _validate_tables(tables, date(2017, 1, 1), date(2017, 12, 31))
            self.assertTrue(schemas()["levels"].field("source_label").nullable)
            for kind in ("target", "range", "changed_price", "changed_source", "changed_notation", "absent_text"):
                with self.subTest(kind=kind):
                    rows = tables["levels"].to_pylist()
                    trigger = next(value for value in rows if value["source_label"] is None)
                    if kind == "target":
                        next(value for value in rows if value["role"] == "target")["source_label"] = None
                    elif kind == "range":
                        trigger["source_text"] = "7000-7001"
                    elif kind == "changed_price":
                        trigger["price_high"] = Decimal("7001")
                    elif kind == "changed_source":
                        trigger.update(source_text="7001", price_low=Decimal("7001"), price_high=Decimal("7001"))
                    elif kind == "changed_notation":
                        trigger["notation"] = "zone"
                    else:
                        trigger["source_text"] = None
                    changed = {**tables, "levels": pa.Table.from_pylist(rows, schema=schemas()["levels"])}
                    with self.assertRaisesRegex(ValueError, "unlabelled trigger"):
                        _validate_tables(changed, date(2017, 1, 1), date(2017, 12, 31))

    def test_unlabelled_trigger_warning_and_null_summary_survive_pinned_publication(self):
        import csv
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("above HVE 7000", "above 7000.25")
            incoming, request, _ = fixture(root, [make_post(root, body=body)])
            manifest = publish_release(incoming, root, request)
            loaded = load_release(root, manifest, sha256_file(manifest), table="levels")
            trigger = next(value for value in loaded.to_pylist() if value["side"] == "bullish" and value["role"] == "trigger")
            self.assertIsNone(trigger["source_label"])
            self.assertEqual(trigger["source_text"], "7000.25")
            self.assertNotIn("__v11_unlabelled", (root / DATA_PATH / "levels.csv").read_text())
            with (root / DATA_PATH / "daily_summary.csv").open() as stream:
                summary = next(csv.DictReader(stream))
            self.assertEqual(summary["bullish_trigger_source_label"], "")
            self.assertEqual(Decimal(summary["bullish_trigger_price_low"]), Decimal("7000.25"))
            self.assertIn("unlabelled_trigger_price", (root / QUALITY_PATH).read_text())

    def test_unlabelled_trigger_requires_the_explicit_source_warning(self):
        import pyarrow as pa
        from abacus_bhishma.verniman_history_2017 import _validate_tables
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("above HVE 7000", "above 7000")
            _, _, crawl = fixture(root, [make_post(root, body=body)])
            tables = build_tables(crawl, root)
            remaining = [row for row in tables["issues"].to_pylist() if row["code"] != "unlabelled_trigger_price"]
            changed = {**tables, "issues": pa.Table.from_pylist(remaining, schema=schemas()["issues"])}
            with self.assertRaisesRegex(ValueError, "unlabelled trigger requires its explicit source warning"):
                _validate_tables(changed, date(2017, 1, 1), date(2017, 12, 31))

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
        for heading in ("Note 1:", "Note1:", "Reminder:", "Tips:", "Rollover week.", "FOMC days are two separate sessions."):
            with self.subTest(heading=heading), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("<div>Note:", f"<div>{heading} Quoting /ESH17 from 2017.") + '<div>Note 2: OPEX $3.4 trillion, $7000 inventory.</div>'
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["extraction_status"], "complete")
                self.assertEqual(len(levels), 6)
                self.assertNotIn(heading, row["bearish_scenario_text"])
                self.assertIn("$3.4 trillion", row["body_text"])
                self.assertNotIn("branch_parse_failed", {value["code"] for value in issues})

    def test_missing_contract_retains_both_branch_texts_without_inventing_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("<p>ESH17 (Mar2017): GAP 7000</p>", "")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertIsNone(row["contract"])
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("buy towards GAP 7010", row["bullish_scenario_text"])
            self.assertIn("sell towards GAP 6990", row["bearish_scenario_text"])
            self.assertIn("contract_missing", {value["code"] for value in issues})

    def test_current_quoting_header_conflict_blocks_numeric_but_future_roll_does_not(self):
        cases = [
            ("Today, I'll be quoting /ESM17 as its volume is greater than /ESH17.", True),
            ("I'm quoting /ESM17 as its volume is greater than /ESH17.", True),
            ("Today, I’ll be quoting /ESM17 as its volume is greater than /ESH17.", True),
            ("Tomorrow, I'll be quoting /ESM17 when volume exceeds /ESH17.", False),
            ("Today, I'm still trading /ESH17 and I'll be quoting /ESM17 when volume from June contract is greater than March contract.", False),
            ("Today, I'll be quoting /ESM17 after the NYSE opening bell.", False),
            ("Today, I'll be quoting /ESH17 as its volume is greater than /ESM17.", False),
            ("Switch to /ESM17 when volume exceeds /ESH17.", False),
            ("Today, I start quoting Jun /ESM17 as volume is greater than Mar /ESH17 contract. (Pace of the Roll 60%)", True),
            ("Today, I start quoting Jun /ESM17 when its volume is greater than Mar /ESH17 contract.", False),
            ("I start quoting Jun /ESM17 tomorrow.", False),
            ("Today, I start quoting Mar /ESH17 as volume is greater than Jun /ESM17 contract.", False),
        ]
        for note, blocked in cases:
            with self.subTest(note=note), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE + f'<div>Rollover note: {note}</div>'
                row, levels, issues = extract_post(make_post(root, body=body), root)
                self.assertEqual(row["contract"], "ESH17")
                self.assertIn("buy towards", row["bullish_scenario_text"])
                self.assertIn("sell towards", row["bearish_scenario_text"])
                self.assertEqual(row["extraction_status"], "failed" if blocked else "complete")
                self.assertEqual(bool(levels), not blocked)
                self.assertEqual("operative_contract_header_conflict" in {value["code"] for value in issues}, blocked)

    def test_unqualified_future_quote_with_present_volume_reason_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            quote = "I'll be quoting /ESU17 as volume September contract is greater than June contract."
            body = BASE.replace("Outlook 01/02", "Outlook 06/12").replace("ESH17 (Mar2017)", "ESM17 (June2017)")
            body += "<div>REMINDER: We're into rollover week and usually rollover days show big divergences between Stocks vs. Futures, so setups that usually work well, may fail completely. " + quote + "</div>"
            row, levels, issues = extract_post(make_post(root, day="2017-06-12", body=body), root)
            self.assertEqual(row["contract"], "ESM17")
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("buy towards", row["bullish_scenario_text"])
            self.assertIn("sell towards", row["bearish_scenario_text"])
            warning = next(value for value in issues if value["code"] == "operative_contract_assignment_ambiguous")
            self.assertEqual(warning["severity"], "error")
            self.assertEqual(warning["source_text"], quote.rstrip("."))
            self.assertNotIn("operative_contract_header_conflict", {value["code"] for value in issues})
        for quote in ("I'll be quoting /ESU17 when volume September contract is greater than June contract.",
                      "I'll be quoting /ESU17 after the opening bell as volume September contract is greater than June contract.",
                      "I'll be quoting /ESU17 tomorrow as volume September contract is greater than June contract.",
                      "I'll be quoting /ESM17 as volume June contract is greater than September contract."):
            with self.subTest(quote=quote), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("ESH17 (Mar2017)", "ESM17 (June2017)") + "<div>REMINDER: " + quote + "</div>"
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
            post = make_post(root, day=None, body="<p>CTAs sell trigger support at 6512; the Big Long of 2017 is coming.</p>")
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
            post = make_post(root, body=BASE + '<div>Rollover note: switch to /ESM17 when volume exceeds /ESH17.</div>')
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["contract"], "ESH17")
            self.assertEqual({value["contract"] for value in levels}, {"ESH17"})
            self.assertIn("other_contracts_mentioned", {value["code"] for value in issues})

    def test_past_after_bell_switch_conflicting_with_heading_refuses_numbers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            quote = "I started quoting ESH18 March contract after 'NYSE Opening Bell'."
            body = BASE.replace("Outlook 01/02", "Outlook 12/10").replace("ESH17 (Mar2017)", "ESZ17 (Dec2017)")
            row, levels, issues = extract_post(make_post(root, day="2017-12-10", body=body + "<div>Note: " + quote + "</div>"), root)
            self.assertEqual(row["contract"], "ESZ17")
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
            quote = "I'll start quoting ESZ17 December contract after NYSE Bell."
            body = BASE.replace("Outlook 01/02", "Outlook 09/10").replace("ESH17 (Mar2017)", "ESU17 (Sep2017)")
            row, levels, issues = extract_post(make_post(root, day="2017-09-10", body=body + "<div>Note: " + quote + "</div>"), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["contract"], "ESU17")
            self.assertEqual({value["contract"] for value in levels}, {"ESU17"})
            warnings = [value for value in issues if value["code"] == "future_intraday_contract_switch"]
            self.assertEqual(len(warnings), 1)
            self.assertEqual(warnings[0]["severity"], "warning")
            self.assertIn(quote[:-1], warnings[0]["source_text"])
            self.assertFalse(any(value["code"] in {"operative_contract_header_conflict", "operative_contract_assignment_ambiguous"} for value in issues))
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))

    def test_equal_volume_present_transition_has_ambiguous_contract_assignment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            quote = "I start quoting /ESM17 as June contract increases to equal volume of March /ESH17."
            body = BASE.replace("Outlook 01/02", "Outlook 03/12") + "<div>Note: " + quote + "</div>"
            row, levels, issues = extract_post(make_post(root, day="2017-03-12", body=body), root)
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(row["contract"], "ESH17")
            self.assertEqual(levels, [])
            failures = [value for value in issues if value["code"] == "operative_contract_assignment_ambiguous"]
            self.assertEqual(len(failures), 1)
            self.assertIn(quote[:-1], failures[0]["source_text"])
            self.assertIn("transition phase", failures[0]["description"])
            self.assertIn("buy towards", row["bullish_scenario_text"])
            self.assertIn("sell towards", row["bearish_scenario_text"])
            self.assertIsNone(row["available_at"])

    def test_unqualified_present_rollover_statement_conflicting_with_heading_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 09/11").replace("ESH17 (Mar2017)", "ESU17 (Sep2017)")
            body += "<div>Note: I start quoting ESZ17 December contract.</div>"
            row, levels, issues = extract_post(make_post(root, day="2017-09-11", body=body), root)
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(row["contract"], "ESU17")
            self.assertEqual(levels, [])
            self.assertIn("operative_contract_assignment_ambiguous", {value["code"] for value in issues})
            self.assertIn("buy towards", row["source_plan_a_text"])
            self.assertIsNone(row["available_at"])

    def test_explicit_future_new_contract_after_open_does_not_reassign_heading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 12/11").replace("ESH17 (Mar2017)", "ESZ17 (Dec2017)")
            body += "<div>Note: I'll start quoting new /ESH18 after the Opening Bell.</div>"
            row, levels, issues = extract_post(make_post(root, day="2017-12-11", body=body), root)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["contract"], "ESZ17")
            self.assertEqual({value["contract"] for value in levels}, {"ESZ17"})
            self.assertIn("future_intraday_contract_switch", {value["code"] for value in issues})
            self.assertNotIn("operative_contract_assignment_ambiguous", {value["code"] for value in issues})
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))

    def test_source_year_conflict_is_not_silently_promoted_to_2017(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root, body=BASE.replace("ESH17 (Mar2017)", "ESH16 (Mar2016)"))
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2017, 1, 2))
            self.assertEqual(row["contract"], "ESH16")
            self.assertEqual(row["source_year_status"], "stale_source_year_conflict")
            self.assertEqual(levels, [])
            self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})

    def test_2017_update_does_not_promote_a_stale_2016_body(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 03/12").replace("ESH17 (Mar2017)", "ESH16 (Mar2016)")
            body += "<div>REMINDER: I'll be quoting /ESM17 tomorrow when volume is greater.</div>"
            post = make_post(root, day="2017-03-12", body=body,
                             source_updated="2017-03-12T08:47:01-05:00")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2017, 3, 12))
            self.assertEqual(row["source_claimed_updated"], "2017-03-12T08:47:01-05:00")
            self.assertEqual(row["contract"], "ESH16")
            self.assertEqual(row["body_contract_year"], 2016)
            self.assertEqual(row["source_year_status"], "stale_source_year_conflict")
            self.assertEqual(row["extraction_status"], "failed")
            self.assertEqual(levels, [])
            self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})
            self.assertIn("buy towards GAP 7010", row["bullish_scenario_text"])
            self.assertIsNone(row["available_at"])

    def test_2018_metadata_update_does_not_reassign_a_2017_body(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 05/18").replace("ESH17 (Mar2017)", "ESM17 (Jun2017)")
            post = make_post(root, day="2017-05-18", body=body,
                             source_updated="2018-05-18T09:20:00-04:00")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2017, 5, 18))
            self.assertEqual(row["contract"], "ESM17")
            self.assertEqual(row["source_claimed_updated"], "2018-05-18T09:20:00-04:00")
            self.assertEqual(row["source_year_status"], "source_contract_year_matches_session")
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIn("source_updated_date_differs", {value["code"] for value in issues})
            self.assertTrue(all(value["session_date"] == date(2017, 5, 18) for value in levels))
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))

    def test_december_30_seed_can_quote_next_delivery_year_without_redating(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 12/30").replace("ESH17 (Mar2017)", "ESH18 (Mar2018)")
            post = make_post(root, day="2017-12-30", body=body,
                             source_updated="2017-12-30T09:18:54-05:00")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2017, 12, 30))
            self.assertEqual(row["contract"], "ESH18")
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIn("contract_year_differs_from_session", {value["code"] for value in issues})
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))
            _, _, crawl = fixture(root, [post])
            coverage = build_tables(crawl, root)["coverage"].to_pylist()
            self.assertEqual(coverage[-1]["session_date"], date(2017, 12, 31))
            self.assertEqual(coverage[-1]["status"], "weekend_no_dated_post")
            self.assertEqual(coverage[-2]["post_count"], 1)

    def test_observed_december_rollover_heading_conflicts_are_retained(self):
        for day, trigger in (("2017-12-12", "3979"), ("2017-12-13", "4137")):
            with self.subTest(day=day), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("Outlook 01/02", "Outlook " + day[5:].replace("-", "/"))
                body = body.replace("ESH17 (Mar2017)", "ESZ17 (Dec2017)").replace("HVE 7000", "HVE " + trigger)
                body += "<div>Note: I'm quoting /ESH18 (Mar 2018).</div>"
                row, levels, issues = extract_post(make_post(root, day=day, body=body), root)
                self.assertEqual(row["contract"], "ESZ17")
                self.assertEqual(row["session_date"].isoformat(), day)
                self.assertEqual(row["extraction_status"], "failed")
                self.assertEqual(levels, [])
                self.assertIn("HVE " + trigger, row["bullish_scenario_text"])
                self.assertIn("HVE " + trigger, row["bearish_scenario_text"])
                conflicts = [value for value in issues if value["code"] == "operative_contract_header_conflict"]
                self.assertEqual(len(conflicts), 1)
                self.assertEqual(conflicts[0]["source_text"], "Note: I'm quoting /ESH18 (Mar 2018)")

    def test_observed_september_12_affirmative_today_quote_conflicts_with_heading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 09/12").replace("ESH17 (Mar2017)", "ESU17 (Sep2017)")
            quote = "Today, I start quoting Dec /ESZ17 as volume is greater than Sep /ESU17 contract."
            body += "<div>REMINDER: " + quote + "</div>"
            row, levels, issues = extract_post(make_post(root, day="2017-09-12", body=body), root)
            self.assertEqual(row["session_date"], date(2017, 9, 12))
            self.assertEqual(row["contract"], "ESU17")
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
            body = BASE.replace("Outlook 01/02", "Outlook 12/26").replace("ESH17 (Mar2017)", "ESH18 (Mar2018)")
            post = make_post(root, day="2017-12-26", body=body.replace("Tuesday", "Wednesday"),
                             source_updated="2017-12-27T09:15:00-05:00")
            row, levels, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2017, 12, 26))
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual(row["source_claimed_updated"], "2017-12-27T09:15:00-05:00")
            self.assertIn("source_updated_date_differs", {value["code"] for value in issues})
            self.assertIn("source_weekday_differs", {value["code"] for value in issues})
            self.assertTrue(all(value["session_date"] == date(2017, 12, 26) for value in levels))

    def test_missing_source_direction_remains_partial(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("remains above HVE", "moves remains HVE")
            row, levels, issues = extract_post(make_post(root, body=body), root)
            self.assertEqual(row["extraction_status"], "partial")
            self.assertEqual({value["side"] for value in levels}, {"bearish"})
            self.assertIn("moves remains HVE", row["source_plan_a_text"])
            self.assertIsNone(row["bullish_scenario_text"])
            self.assertIsNone(row["bullish_source_plan_branch"])
            self.assertTrue(any(value["code"] == "branch_direction_ambiguous" and value["side"] is None for value in issues))

    def test_late_year_next_delivery_year_is_retained_without_redating(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 12/31").replace("ESH17 (Mar2017)", "ESH18 (Mar2018)")
            row, levels, issues = extract_post(make_post(root, day="2017-12-31", body=body), root)
            self.assertEqual(row["session_date"], date(2017, 12, 31))
            self.assertEqual(row["contract"], "ESH18")
            self.assertEqual(row["body_contract_year"], 2018)
            self.assertEqual(row["extraction_status"], "complete")
            self.assertEqual({value["session_date"] for value in levels}, {date(2017, 12, 31)})
            self.assertIn("contract_year_differs_from_session", {value["code"] for value in issues})
            self.assertTrue(all(value["available_at"] is None for value in [row, *levels]))

    def test_early_year_next_delivery_year_and_far_year_conflicts_fail_closed(self):
        for day, header, contract in (("2017-01-02", "01/02", "ESH18 (Mar2018)"),
                                      ("2017-12-31", "12/31", "ESH21 (Mar2021)")):
            with self.subTest(day=day, contract=contract), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                body = BASE.replace("Outlook 01/02", "Outlook " + header).replace("ESH17 (Mar2017)", contract)
                row, levels, issues = extract_post(make_post(root, day=day, body=body), root)
                self.assertEqual(row["extraction_status"], "failed")
                self.assertEqual(levels, [])
                self.assertIn("stale_source_year_conflict", {value["code"] for value in issues})

    def test_full_calendar_required_and_older_boundary_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            boundary = make_post(root, identity="boundary", day="2016-12-31", body=BASE.replace("Outlook 01/02", "Outlook 12/31"))
            _, _, crawl = fixture(root, [make_post(root), boundary])
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"].num_rows, 1)
            self.assertEqual(tables["coverage"].num_rows, 365)
            self.assertEqual(tables["coverage"]["session_date"].to_pylist()[0], date(2017, 1, 1))
            self.assertEqual(tables["coverage"]["session_date"].to_pylist()[-1], date(2017, 12, 31))
            for start, end in (("2017-01-02", "2017-12-31"), ("2017-01-01", "2017-12-30"),
                               ("2018-01-01", "2018-12-31")):
                crawl.update(requested_start_date=start, anchor_session_date=end)
                with self.assertRaisesRegex(ValueError, "complete January"):
                    build_tables(crawl, root)

    def test_malformed_three_digit_day_is_undated_and_never_repaired(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 08/276").replace("ESH17 (Mar2017)", "ESU17 (Sep2017)")
            post = make_post(root, day=None, identity="malformed_source_day", body=body,
                             source_updated="2017-08-27T09:20:00-04:00")
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

    def test_nonleap_february_calendar_advances_directly_to_march(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 02/28")
            post = make_post(root, day="2017-02-28", body=body)
            _, _, crawl = fixture(root, [post])
            tables = build_tables(crawl, root)
            rows = tables["coverage"].to_pylist()
            self.assertEqual(len(rows), 365)
            self.assertEqual(rows[58]["session_date"], date(2017, 2, 28))
            self.assertEqual(rows[58]["post_count"], 1)
            self.assertEqual(rows[59]["session_date"], date(2017, 3, 1))
            self.assertEqual(tables["outlooks"]["session_date"].to_pylist(), [date(2017, 2, 28)])
            self.assertEqual(tables["outlooks"]["extraction_status"].to_pylist(), ["complete"])
            self.assertTrue(all(value is None for value in tables["levels"]["available_at"].to_pylist()))

    def test_invalid_nonleap_calendar_date_is_refused_without_reassignment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 02/29")
            post = make_post(root, day="2017-02-29", body=body)
            _, _, crawl = fixture(root, [post])
            with self.assertRaisesRegex(ValueError, "day is out of range"):
                build_tables(crawl, root)

    def test_weekend_stated_date_and_different_update_day_are_not_reassigned(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 10/21").replace("ESH17 (Mar2017)", "ESZ17 (Dec2017)")
            post = make_post(root, day="2017-10-21", body=body, source_updated="2017-10-14T09:17:57.596-04:00")
            row, _, issues = extract_post(post, root)
            self.assertEqual(row["session_date"], date(2017, 10, 21))
            self.assertEqual(row["extraction_status"], "complete")
            self.assertIn("weekend_stated_outlook_date", {value["code"] for value in issues})
            self.assertIn("source_updated_date_differs", {value["code"] for value in issues})
            incoming, request, _ = fixture(root, [post])
            manifest = publish_release(incoming, root, request)
            self.assertIn("Weekend stated dates (1 posts)", (root / QUALITY_PATH).read_text())
            self.assertIn("2017-10-14T09:17:57.596-04:00", (root / QUALITY_PATH).read_text())
            coverage = load_release(root, manifest, sha256_file(manifest), table="coverage").to_pylist()
            by_day = {value["session_date"]: value for value in coverage}
            self.assertEqual(by_day[date(2017, 10, 21)]["post_count"], 1)
            self.assertEqual(by_day[date(2017, 10, 14)]["post_count"], 0)

    def test_duplicate_dates_and_multiple_contracts_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            posts = [make_post(root, identity="first"), make_post(root, identity="second", body=BASE.replace("ESH17 (Mar2017)", "ESM17 (Jun2017)"))]
            _, _, crawl = fixture(root, posts)
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"].num_rows, 2)
            self.assertEqual(set(tables["levels"]["contract"].to_pylist()), {"ESH17", "ESM17"})
            self.assertEqual(tables["coverage"].to_pylist()[1]["post_count"], 2)
            self.assertEqual(sum(issue["code"] == "duplicate_outlook_date" for issue in tables["issues"].to_pylist()), 2)

    def test_duplicate_body_date_is_not_reassigned_to_updated_metadata_day(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            body = BASE.replace("Outlook 01/02", "Outlook 11/08")
            posts = [make_post(root, identity="election_day", day="2017-11-08", body=body,
                               source_updated="2017-11-08T09:10:00-05:00"),
                     make_post(root, identity="election_result", day="2017-11-08", body=body,
                               source_updated="2017-11-09T08:43:48-05:00")]
            _, _, crawl = fixture(root, posts)
            tables = build_tables(crawl, root)
            self.assertEqual(tables["outlooks"]["session_date"].to_pylist(), [date(2017, 11, 8)] * 2)
            by_day = {row["session_date"]: row for row in tables["coverage"].to_pylist()}
            self.assertEqual(by_day[date(2017, 11, 8)]["post_count"], 2)
            self.assertEqual(by_day[date(2017, 11, 9)]["post_count"], 0)
            self.assertEqual(by_day[date(2017, 11, 9)]["status"], "weekday_no_dated_post")
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
            self.assertEqual(metadata["version"], "11.0.0")
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
            boundary = make_post(root, day="2016-12-31", identity="older_boundary",
                                 body=BASE.replace("Outlook 01/02", "Outlook 12/31"))
            incoming, request, crawl = fixture(root, [make_post(root), boundary])
            review = {"requested_start_date": "2017-01-01", "anchor_session_date": "2017-12-31",
                      "retained_post_count": 1,
                      "notes": ["Synthetic review: the retained links support this calendar selection; no earlier collection discontinuity is assumed."],
                      "boundary": {"url": boundary["url"], "reviewed_session_date": "2016-12-31"}}
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
            self.assertIn("[the 2016-12-31 session](https://verniman.blogspot.com/2009/01/older_boundary.html)", quality)
            self.assertIn("without recomputing years from source updates or delivery contracts", quality)
            self.assertNotIn("intentional local no-overwrite control stop", quality)
            self.assertNotIn("May 2018", quality)

    def test_review_interval_and_count_disagreement_are_refused(self):
        from abacus_bhishma.verniman_history_2017 import _quality
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            _, _, crawl = fixture(root)
            tables = build_tables(crawl, root)
            review = {"requested_start_date": "2017-01-01", "anchor_session_date": "2017-12-31",
                      "retained_post_count": 1, "notes": ["Explicit synthetic source review."]}
            for change, message in (({"anchor_session_date": "2018-12-31"}, "interval"),
                                    ({"retained_post_count": 2}, "post count"),
                                    ({"notes": []}, "review notes"),
                                    ({"boundary": {"reviewed_session_date": "2017-01-01"}}, "must precede")):
                with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                    _quality(tables, date(2017, 1, 1), date(2017, 12, 31), chronology_review={**review, **change})

    def test_gap_report_links_the_closest_captured_dates_for_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            posts = [make_post(root, day="2017-01-09", identity="earlier",
                               body=BASE.replace("Outlook 01/02", "Outlook 01/09")),
                     make_post(root, day="2017-01-11", identity="later",
                               body=BASE.replace("Outlook 01/02", "Outlook 01/11"))]
            incoming, request, _ = fixture(root, posts)
            publish_release(incoming, root, request)
            quality = (root / QUALITY_PATH).read_text()
            line = next(line for line in quality.splitlines() if line.startswith("| 2017-01-10 |"))
            self.assertIn("2017-01-09: [earlier](https://verniman.blogspot.com/2009/01/earlier.html)", line)
            self.assertIn("2017-01-11: [later](https://verniman.blogspot.com/2009/01/later.html)", line)
            self.assertIn("not source posts for an absent date", quality)

    def test_quality_links_undated_scenarios_and_discloses_missing_numeric_dates(self):
        from abacus_bhishma.verniman_history_2017 import _quality
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            post = make_post(root, identity="undated", day=None,
                             body=BASE.replace("Outlook 01/02:", "Outlook:").replace("ESH17 (Mar2017):", "/ES Value:"))
            _, _, crawl = fixture(root, [post])
            quality = _quality(build_tables(crawl, root), date(2017, 1, 1), date(2017, 12, 31)).decode()
            self.assertIn("Source extent and undated daily plans (1 posts)", quality)
            self.assertIn("https://verniman.blogspot.com/2009/01/undated.html", quality)
            self.assertIn("Session date unresolved; numeric extraction refused.", quality)
            self.assertIn("Source timestamp claims, permalinks and image dates do not supply missing body dates", quality)
            self.assertIn("December 29 seed explicitly stating the final trading day of 2017", quality)

    def test_navigation_exhaustion_publication_requires_and_retains_independent_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request, _ = exhaustion_fixture(root)
            manifest = publish_release(incoming, root, request)
            verify_release(root, manifest, sha256_file(manifest))
            metadata = json.loads(manifest.read_text())
            self.assertFalse(metadata["traversal_reached_lower_boundary"])
            self.assertEqual(metadata["stop_reason"], "navigation_exhausted")
            self.assertTrue(metadata["observed_source_exhaustion_only"])
            self.assertFalse(metadata["historical_full_year_completeness_claimed"])
            self.assertIsNotNone(metadata["collection_completion_review"])
            self.assertEqual(load_release(root, manifest, sha256_file(manifest), table="outlooks").num_rows, 1)

    def test_navigation_exhaustion_never_bypasses_missing_or_conflicting_evidence(self):
        from abacus_bhishma.verniman_history_2017 import _validate_collection_completion
        for breakage in ("missing_review", "unretained_review", "full_historical_claim", "invented_boundary",
                         "wrong_review_interval", "original_max_stop", "original_open_link", "original_capture_failure",
                         "feed_not_exhausted", "feed_historical_boundary", "feed_missing_candidate", "feed_date_mismatch",
                         "feed_pagination_hole", "feed_missing_empty_probe", "feed_false_count", "feed_false_selection",
                         "nonempty_probe", "candidate_body_mismatch", "candidate_url_mismatch", "unresolved_candidate",
                         "missing_context", "dated_context"):
            with self.subTest(breakage=breakage), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                _, _, crawl = exhaustion_fixture(root, breakage)
                with self.assertRaises(ValueError):
                    _validate_collection_completion(crawl, root)

    def test_provenance_pins_prior_helpers_and_does_not_mutate_v2_identity(self):
        from abacus_bhishma import verniman_history as original
        from abacus_bhishma import verniman_history_2025 as prior_year
        from abacus_bhishma import verniman_history_2024 as prior_release
        from abacus_bhishma import verniman_history_2023 as previous_release
        from abacus_bhishma import verniman_history_2022 as preceding_release
        from abacus_bhishma import verniman_history_2021 as latest_prior_release
        from abacus_bhishma import verniman_history_2018 as frozen_v10
        original_schemas = original.schemas()
        prior_schemas = prior_year.schemas()
        prior_release_schemas = prior_release.schemas()
        previous_release_schemas = previous_release.schemas()
        preceding_release_schemas = preceding_release.schemas()
        latest_prior_release_schemas = latest_prior_release.schemas()
        frozen_v10_schemas = frozen_v10.schemas()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            incoming, request, _ = fixture(root)
            manifest = publish_release(incoming, root, request)
            metadata = json.loads(manifest.read_text())
            self.assertEqual(metadata["publication_invocation"]["entry_point"], "abacus_bhishma.verniman_history_2017")
            retained = metadata["provenance"]["retained"]["files"]
            labels = {item["source"] for item in retained}
            self.assertTrue({"abacus_bhishma/verniman_history_2017.py", "abacus_bhishma/verniman_history_2018.py", "abacus_bhishma/verniman_history.py",
                             "abacus_bhishma/verniman_levels.py", "abacus_bhishma/verniman_backfill.py",
                             "abacus_bhishma/verniman_history_2021.py", "abacus_bhishma/verniman_history_2022.py",
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
            self.assertEqual(preceding_release.DATASET_ID, "verniman_daily_levels__6.0.0")
            self.assertEqual(preceding_release.VERSION, "6.0.0")
            self.assertTrue(all(schema.equals(preceding_release.schemas()[name], check_metadata=True)
                                for name, schema in preceding_release_schemas.items()))
            self.assertIn("verniman_daily_levels__6.0.0", metadata["preserved_prior_releases"])
            self.assertEqual(latest_prior_release.DATASET_ID, "verniman_daily_levels__7.0.0")
            self.assertEqual(latest_prior_release.VERSION, "7.0.0")
            self.assertTrue(all(schema.equals(latest_prior_release.schemas()[name], check_metadata=True)
                                for name, schema in latest_prior_release_schemas.items()))
            self.assertIn("verniman_daily_levels__7.0.0", metadata["preserved_prior_releases"])
            self.assertEqual(frozen_v10.DATASET_ID, "verniman_daily_levels__10.0.0")
            self.assertEqual(frozen_v10.VERSION, "10.0.0")
            self.assertTrue(all(schema.equals(frozen_v10.schemas()[name], check_metadata=True)
                                for name, schema in frozen_v10_schemas.items()))
            self.assertIn("verniman_daily_levels__10.0.0", metadata["preserved_prior_releases"])
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
            self.assertTrue((root / "data/staging/verniman/synthetic_history-v11/crawl_manifest.json").is_file())
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
