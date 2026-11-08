#!/usr/bin/env python3
"""Independent offline capture audit; no network requests or source mutations.

Sitemap locators are discovery candidates, not proof of daily-map scope. A
boundary capture proves traversal only when its article date precedes the start.
"""
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

sys.dont_write_bytecode = True


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(url):
    p = urlsplit(url)
    return urlunsplit(("https", p.hostname or "", p.path, "", ""))


class Article(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.found = 0
        self.skip = 0
        self.parts = []
        self.images = []
        self.linked_images = []
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if not self.depth:
            if tag == "div" and "post-body" in (a.get("class") or "").split():
                self.depth = 1
                self.found += 1
            return
        if tag == "div":
            self.depth += 1
        if tag in {"script", "style", "template"}:
            self.skip += 1
        if not self.skip and tag == "a":
            self.anchors.append(a.get("href"))
        if not self.skip and tag == "img":
            self.images.append(a.get("src") or a.get("data-src"))
            anchor = self.anchors[-1] if self.anchors else None
            self.linked_images.append(anchor if anchor and re.search(r"(?:blogger\.googleusercontent\.com|bp\.blogspot\.com)/", anchor) else None)

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag == "a" and self.anchors:
            self.anchors.pop()
        if tag in {"script", "style", "template"} and self.skip:
            self.skip -= 1
        if tag == "div":
            self.depth -= 1

    def handle_data(self, value):
        if self.depth and not self.skip:
            self.parts.append(value)

    def month_days(self):
        return sorted({(int(m), int(d)) for m, d in re.findall(
            r"\bOutlook\s+(\d{1,2})/(\d{1,2})\b", " ".join(self.parts), re.I)})


def image_asset_identity(url):
    parts = urlsplit(url)
    segments = [segment for segment in unquote(parts.path).split('/') if segment]
    # Remove only explicit Blogger rendition-size segments. Asset tokens and
    # filenames remain intact; different chart identities must not collapse.
    return tuple(segment for segment in segments
                 if not re.fullmatch(r'(?:s\d+|w\d+-h\d+)(?:-[^/]*)?', segment))


def audit(stage, root):
    manifest = json.loads((stage / "capture-manifest.json").read_text())
    errors, qualifications = [], []
    checked = set()

    def payload(base, record, label):
        path = (base / record["path"]).resolve()
        if not path.is_relative_to(base.resolve()):
            raise ValueError(f"path outside audit root: {record['path']}")
        raw = path.read_bytes()
        if sha(raw) != record["sha256"] or len(raw) != record["bytes"]:
            errors.append({"check": "recorded_bytes", "record": label, "path": record["path"]})
        checked.add(str(path))
        if record["path"].endswith(".gz"):
            raw = gzip.decompress(raw)
            if record.get("uncompressed_sha256") and sha(raw) != record["uncompressed_sha256"]:
                errors.append({"check": "gzip_payload_hash", "record": label})
            if record.get("uncompressed_bytes") is not None and len(raw) != record["uncompressed_bytes"]:
                errors.append({"check": "gzip_payload_length", "record": label})
        return raw

    for record in manifest.get("attempts", []):
        if record.get("path"):
            payload(stage, record, "captured-response")

    for item in manifest.get("retained_inputs", []) + manifest.get("retained_source_verifications", []):
        payload(root, item, "retained-input")

    overrides = {}
    exception_verification = {"status": "not_declared", "rules_checked": 0, "reviewed_sources_checked": 0}
    override_record = manifest.get("date_override_manifest")
    if override_record:
        override_document = json.loads(payload(root, override_record, "reviewed-date-exceptions"))
        if override_document.get("start_date") != manifest["start_date"] or override_document.get("end_date") != manifest["end_date"]:
            errors.append({"check": "date_exception_scope"})
        for review in override_document.get("source_reviews", []):
            payload(root, review, "pinned-date-review")
        for rule in override_document.get("overrides", []):
            rule_url = canonical(rule["url"])
            if rule_url in overrides:
                errors.append({"check": "duplicate_date_exception", "url": rule_url})
            raw_evidence = payload(root, rule["evidence"], "date-exception-evidence")
            evidence_article = Article()
            evidence_article.feed(raw_evidence.decode("utf-8"))
            evidence_body_hash = sha(re.sub(r"\s+", "", "".join(evidence_article.parts)).encode())
            if evidence_article.month_days() != [tuple(rule["expected_body_month_day"])] or evidence_body_hash != rule["body_text_sha256"]:
                errors.append({"check": "reviewed_date_exception_evidence", "url": rule_url})
            overrides[rule_url] = rule
        declared = manifest.get("source_date_exceptions")
        if declared != override_document:
            errors.append({"check": "date_exception_manifest_declaration"})
        exception_verification = {"status": "passed", "rules_checked": len(overrides),
                                  "reviewed_sources_checked": len(override_document.get("source_reviews", [])),
                                  "input": override_record}
    posts = manifest["posts"]
    excluded_posts = manifest.get("excluded_context_posts", [])
    all_posts = posts + excluded_posts
    successful_all = {canonical(p["url"]) for p in all_posts}
    successful = {canonical(p["url"]) for p in posts}
    identities = {(canonical(p["url"]), p.get("session_date")) for p in posts}
    start, end = manifest["start_date"], manifest["end_date"]
    for rule_url, rule in overrides.items():
        reviewed_stamp = rule.get("session_date")
        if reviewed_stamp is None or start <= reviewed_stamp <= end:
            matching_rule_posts = [post for post in posts if canonical(post["url"]) == rule_url
                                   and post.get("session_date") == reviewed_stamp
                                   and post.get("source_date_override") == rule]
            if len(matching_rule_posts) != 1:
                errors.append({"check": "declared_in_scope_exception_represented_once", "url": rule_url,
                               "reviewed_session_date": reviewed_stamp, "matching_posts": len(matching_rule_posts)})
    image_missing, image_counts = [], Counter()
    text_only_articles = []
    duplicate_dates = Counter(p["session_date"] for p in posts if p.get("session_date"))
    for p in posts:
        raw = payload(stage, p["html"], p["url"])
        article = Article()
        article.feed(raw.decode("utf-8"))
        md = article.month_days()
        stamp = p.get("session_date")
        rule = overrides.get(canonical(p["url"]))
        if rule:
            body_hash = sha(re.sub(r"\s+", "", "".join(article.parts)).encode())
            if (stamp != rule["session_date"] or p.get("source_date_override") != rule
                    or p.get("date_method") != "explicit_reviewed_source_date_exception"
                    or md != [tuple(rule["expected_body_month_day"])] or body_hash != rule["body_text_sha256"]):
                errors.append({"check": "applied_reviewed_date_exception", "url": p["url"], "assigned": stamp})
            qualifications.append({"check": "reviewed_source_date_exception", "url": p["url"],
                                   "session_date": stamp, "reason": rule["reason"],
                                   "qualification": "Exact source bytes retained; the explicit reviewed date is checked against pinned body and review identities."})
        if article.found != 1:
            errors.append({"check": "one_article", "url": p["url"], "count": article.found})
        if stamp:
            d = date.fromisoformat(stamp)
            if not (start <= stamp <= end) or md != [(d.month, d.day)]:
                errors.append({"check": "body_date_correspondence", "url": p["url"], "assigned": stamp, "body_month_days": md})
        elif len(md) == 1 and not rule:
            qualifications.append({"check": "unassigned_unambiguous_month_day", "url": p["url"], "body_month_days": md})
        elif stamp is None and not md:
            original_tokens = re.findall(r"\bOutlook\s+([^\s:]+)", " ".join(article.parts), re.I)
            qualifications.append({"check": "unassigned_source_date_preserved", "url": p["url"],
                                   "original_outlook_tokens": original_tokens,
                                   "qualification": "The retained source does not supply a parseable Outlook month/day. No date is repaired or guessed."})
        if not article.images:
            text_only_articles.append({'url': p['url'], 'session_date': stamp,
                                       'source_html_sha256': sha(raw),
                                       'retention': 'Complete source text retained; original article has no image elements.'})
        records = p.get("images", [])
        image_counts["article_image_elements"] += len(article.images)
        image_counts["image_records"] += len(records)
        if len(records) != len(article.images):
            errors.append({"check": "all_article_images_recorded", "url": p["url"], "elements": len(article.images), "records": len(records)})
        for index, image in enumerate(records):
            if index < len(article.images):
                inline = urljoin(p["url"], article.images[index] or "")
                linked = article.linked_images[index]
                requested = urljoin(p["url"], linked) if linked else inline
                linked_name = unquote(urlsplit(requested).path).rsplit("/", 1)[-1]
                inline_name = unquote(urlsplit(inline).path).rsplit("/", 1)[-1]
                mismatch = bool(linked and linked_name and inline_name and linked_name != inline_name)
                asset_mismatch = bool(linked and image_asset_identity(requested) != image_asset_identity(inline))
                image_counts['linked_inline_asset_identities_checked'] += bool(linked)
                if asset_mismatch and not mismatch:
                    qualifications.append({'check': 'same_filename_distinct_asset_identity', 'post': p['url'], 'index': index,
                                           'linked_url': requested, 'actual_inline_url': inline})
                    if image.get('url') != inline or image.get('rendition') != 'inline_thumbnail':
                        errors.append({'check': 'distinct_inline_asset_not_preserved', 'post': p['url'], 'index': index,
                                       'linked_url': requested, 'actual_inline_url': inline})
                if mismatch:
                    if not image.get("source_link_qualification") or image.get("url") != inline or image.get("rendition") != "inline_thumbnail" or not image.get("full_size_error"):
                        errors.append({"check": "mismatched_link_preserves_actual_inline", "post": p["url"], "index": index,
                                       "linked": requested, "inline": inline, "record": image})
                    qualifications.append({"check": "source_link_filename_mismatch", "post": p["url"], "index": index,
                                           "linked_url": requested, "actual_inline_url": inline,
                                           "qualification": "Actual inline source bytes preserved; linked image names another image. No replacement full-size URL inferred."})
                if image.get("requested_url") != requested:
                    errors.append({"check": "actual_linked_image_preferred", "post": p["url"], "index": index,
                                   "source_preferred_url": requested, "record_requested_url": image.get("requested_url")})
                if image.get("inline_url") != inline:
                    errors.append({"check": "image_position_and_source", "post": p["url"], "index": index,
                                   "article_src": inline, "record_inline_url": image.get("inline_url")})
            if image.get("path"):
                payload(stage, image, p["url"] + " image")
                image_counts["retained_image_occurrences"] += 1
                if image.get("rendition") == "inline_thumbnail":
                    image_counts["qualified_inline_fallbacks"] += 1
                    qualifications.append({"check": "qualified_inline_image_fallback", "post": p["url"],
                                           "requested_url": image.get("requested_url"), "retained_url": image.get("url"),
                                           "source_error": image.get("full_size_error"),
                                           "qualification": "Actual source inline rendition retained because its linked image names a different image; this is not full-size recovery." if image.get("source_link_qualification") else "Actual source inline rendition retained after the linked full-size URL failed; this is not full-size recovery."})
                elif image.get("rendition") == "linked_full_image":
                    image_counts["linked_full_image_occurrences"] += 1
            else:
                image_missing.append({"post": p["url"], "url": image.get("requested_url") or image.get("url"), "error": image.get("error")})

    excluded_checks = []
    for post in excluded_posts:
        raw = payload(stage, post["html"], "excluded-source-html")
        article = Article()
        article.feed(raw.decode("utf-8"))
        rule = post.get("source_scope_exclusion", {})
        if (post.get("archive_role") != "excluded_reviewed_context"
                or rule.get("url") != canonical(post["url"])
                or rule.get("body_text_sha256") != sha(re.sub(r"\s+", "", "".join(article.parts)).encode())):
            errors.append({"check": "excluded_context_rule_metadata", "url": post["url"]})
        if post.get("session_date") is not None or article.month_days() or article.found != 1:
            errors.append({"check": "excluded_context_is_undated", "url": post["url"]})
        if len(post.get("images", [])) != len(article.images):
            errors.append({"check": "all_excluded_context_images_recorded", "url": post["url"]})
        for index, image in enumerate(post.get("images", [])):
            inline = urljoin(post["url"], article.images[index] or "")
            linked = article.linked_images[index]
            requested = urljoin(post["url"], linked) if linked else inline
            if linked and image_asset_identity(requested) != image_asset_identity(inline):
                errors.append({"check": "excluded_linked_inline_asset_mismatch", "url": post["url"], "index": index})
            if image.get("requested_url") != requested or image.get("inline_url") != inline:
                errors.append({"check": "excluded_image_identity", "url": post["url"], "index": index})
            if not image.get("path"):
                errors.append({"check": "excluded_image_not_retained", "url": post["url"], "index": index})
            else:
                payload(stage, image, "excluded-source-image")
        excluded_checks.append({"url": post["url"], "source_html_sha256": sha(raw), "images": len(article.images)})

    # Reconcile source/date identities, not merely navigation's seen set.
    prior_missing = []
    prior_body_changes = []
    prior_source_records = 0
    prior_date_adjustments = []
    for record in manifest.get("retained_inputs", []):
        retained_raw = payload(root, record, "retained-manifest")
        if Path(record["path"]).suffix.lower() in {".html", ".htm"}:
            continue  # Explicit exception evidence is hashed above, not a JSON source ledger.
        doc = json.loads(retained_raw)
        for p in doc.get("posts", []) + doc.get("source_dispositions", []):
            original_stamp = p.get("session_date")
            url = p.get("url") or p.get("source_url")
            rule = overrides.get(canonical(url)) if url else None
            stamp = rule["session_date"] if rule else original_stamp
            if rule and original_stamp != stamp:
                prior_date_adjustments.append({"url": url, "legacy_session_date": original_stamp,
                                               "reviewed_session_date": stamp, "reason": rule["reason"]})
            if not url or not p.get("html") or (stamp and not start <= stamp <= end):
                continue
            prior_source_records += 1
            old_raw = payload(root, p["html"], "prior-source-html")
            old_article = Article()
            old_article.feed(old_raw.decode("utf-8"))
            matching = [row for row in posts if canonical(row["url"]) == canonical(url) and row.get("session_date") == stamp]
            old_text = re.sub(r"\s+", "", "".join(old_article.parts))
            matched_body = False
            for row in matching:
                new_article = Article()
                new_article.feed(payload(stage, row["html"], "matching-source").decode("utf-8"))
                if re.sub(r"\s+", "", "".join(new_article.parts)) == old_text:
                    matched_body = True
                    break
            if matching and not matched_body:
                prior_body_changes.append({"url": url, "session_date": stamp,
                                           "qualification": "Current same-date source body differs from prior retained body; original prior bytes remain hash-pinned."})
            if (canonical(url), stamp) not in identities:
                prior_missing.append({"url": url, "prior_session_date": stamp,
                                      "successful_current_url": canonical(url) in successful})
    excluded_prior_urls = set()
    reviewed_exhaustion = None
    for input_record in manifest.get("retained_inputs", []):
        if not str(input_record.get("path", "")).endswith(".json"):
            continue
        prior = json.loads(payload(root, input_record, "retained-context-manifest"))
        for old in prior.get("excluded_context_posts", []):
            excluded_prior_urls.add(canonical(old["url"]))
            candidates = [p for p in excluded_posts if canonical(p["url"]) == canonical(old["url"])]
            if len(candidates) != 1:
                errors.append({"check": "excluded_context_identity_once", "url": old["url"], "records": len(candidates)})
                continue
            expected_rule = candidates[0].get("source_scope_exclusion", {})
            if expected_rule.get("source_html") != old["html"] or expected_rule.get("source_manifest") != input_record["path"]:
                errors.append({"check": "excluded_context_rule_input_identity", "url": old["url"]})
            old_article, current_article = Article(), Article()
            old_article.feed(payload(root, old["html"], "prior-excluded-html").decode("utf-8"))
            current_article.feed(payload(stage, candidates[0]["html"], "current-excluded-html").decode("utf-8"))
            normalize = lambda a: re.sub(r"\s+", "", "".join(a.parts))
            if normalize(old_article) != normalize(current_article):
                errors.append({"check": "excluded_context_body_changed", "url": old["url"]})
        review_record = prior.get("collection_completion_review")
        if review_record:
            review = json.loads(payload(root, review_record, "reviewed-completion-scope"))
            chronology = json.loads(payload(root, prior["chronology_review"], "reviewed-chronology-scope"))
            if (review.get("kind") != "verniman_2017_observed_source_exhaustion"
                    or review.get("requested_start_date") != start or review.get("anchor_session_date") != end
                    or review.get("lower_boundary_observed") is not False
                    or review.get("historical_full_year_completeness_claimed") is not False
                    or chronology.get("boundary") is not None
                    or chronology.get("retained_post_count") != len(posts)
                    or chronology.get("excluded_context_post_count") != len(excluded_posts)
                    or chronology.get("undated_daily_plan_count") != sum(p.get("session_date") is None for p in posts)):
                errors.append({"check": "reviewed_exhaustion_scope"})
            reviewed_exhaustion = {"review": review_record, "chronology": prior["chronology_review"]}
    declared_rules = manifest.get("source_scope_exclusions", [])
    if ({r.get("url") for r in declared_rules} != excluded_prior_urls
            or len(declared_rules) != len(excluded_prior_urls)
            or any(p.get("archive_role") == "excluded_reviewed_context" for p in posts)):
        errors.append({"check": "excluded_context_declared_rules_exact"})
    if {canonical(p["url"]) for p in excluded_posts} != excluded_prior_urls:
        errors.append({"check": "excluded_context_exact_reviewed_set"})

    if prior_missing:
        errors.append({"check": "retained_source_date_coverage", "missing": prior_missing})

    boundary = manifest.get("boundary_post")
    boundary_valid = False
    if boundary:
        raw = payload(stage, boundary["html"], "boundary")
        article = Article()
        article.feed(raw.decode("utf-8"))
        stamp = boundary.get("session_date")
        rule = overrides.get(canonical(boundary["url"]))
        if rule:
            body_hash = sha(re.sub(r"\s+", "", "".join(article.parts)).encode())
            if stamp != rule["session_date"] or body_hash != rule["body_text_sha256"] or article.month_days() != [tuple(rule["expected_body_month_day"])]:
                errors.append({"check": "reviewed_boundary_exception", "url": boundary["url"]})
        if stamp:
            d = date.fromisoformat(stamp)
            boundary_valid = stamp < start and article.month_days() == [(d.month, d.day)]
    if manifest.get("lower_boundary_reached") and not boundary_valid:
        errors.append({"check": "claimed_boundary_not_proven"})
    if not manifest.get("lower_boundary_reached"):
        qualifications.append({"check": "lower_boundary_not_reached", "stop_reason": manifest.get("stop_reason")})

    exhaustion_check = {"status": "not_applicable"}
    exhausted_valid = False
    terminal_url = "https://verniman.blogspot.com/2000/02/vtp.html"
    if not boundary and manifest.get("stop_reason") == "navigation_exhausted":
        class OlderLinks(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and attrs.get("id") == "Blog1_blog-pager-older-link":
                    self.links.append(canonical(attrs["href"]))
        records_by_url = {canonical(p["url"]): p for p in all_posts}
        cursor, chain, chain_errors = canonical(manifest["seed_url"]), [], []
        while cursor:
            if cursor in chain or cursor not in records_by_url:
                chain_errors.append({"url": cursor, "problem": "cycle_or_unretained_navigation_target"})
                break
            chain.append(cursor)
            record = records_by_url[cursor]
            links = OlderLinks()
            links.feed(payload(stage, record["html"], "raw-older-navigation").decode("utf-8"))
            if len(links.links) > 1:
                chain_errors.append({"url": cursor, "problem": "multiple_older_links"})
                break
            older = links.links[0] if links.links else None
            recorded_older = canonical(record["older_url"]) if record.get("older_url") else None
            if older != recorded_older:
                chain_errors.append({"url": cursor, "problem": "recorded_older_link_differs"})
            cursor = older
        exhausted_valid = (not chain_errors and bool(chain) and chain[-1] == terminal_url
                           and set(chain) == successful_all and reviewed_exhaustion is not None
                           and manifest.get("lower_boundary_reached") is False)
        declared_terminal = manifest.get("reviewed_navigation_terminal", {})
        if (declared_terminal.get("url") != terminal_url or not reviewed_exhaustion
                or declared_terminal.get("completion_review") != reviewed_exhaustion["review"]):
            errors.append({"check": "reviewed_terminal_metadata"})
            exhausted_valid = False
        if not exhausted_valid:
            errors.append({"check": "reviewed_raw_navigation_exhaustion", "chain": chain_errors})
        exhaustion_check = {"status": "passed" if exhausted_valid else "failed", "terminal_url": terminal_url,
                            "retained_navigation_records": len(chain), "lower_boundary_observed": False,
                            "historical_completeness_claimed": False, "reviewed_scope": reviewed_exhaustion,
                            "qualification": "The current raw Older Post chain exhausts without an observed prior-year boundary. Earlier requested dates remain gaps and undated plans remain unassigned."}

    sitemap_urls = []
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    for record in manifest.get("sitemaps", []):
        if not record.get("path") or record.get("error"):
            continue
        tree = ET.fromstring(payload(stage, record, "sitemap"))
        if tree.tag == namespace + "urlset":
            sitemap_urls.extend(canonical(node.findtext(namespace + "loc")) for node in tree.findall(namespace + "url"))
    seed = canonical(manifest["seed_url"])
    boundary_url = canonical(boundary["url"]) if boundary else terminal_url if exhausted_valid else None
    sitemap_range = {"seed_index": sitemap_urls.index(seed) if seed in sitemap_urls else None,
                     "boundary_index": sitemap_urls.index(boundary_url) if boundary_url in sitemap_urls else None,
                     "unresolved_locator_candidates": [],
                     "qualification": "Sitemap order supplies discovery candidates; old permalink dates do not establish session scope. Boundary is separate from in-scope posts."}
    first, last = sitemap_range["seed_index"], sitemap_range["boundary_index"]
    if first is not None and last is not None and first <= last:
        sitemap_range["unresolved_locator_candidates"] = [u for u in sitemap_urls[first:last + (1 if exhausted_valid else 0)] if u not in successful_all]
    attempted = {canonical(row["url"]) for row in manifest.get("attempts", []) if row.get("url")}
    unresolved = sitemap_range["unresolved_locator_candidates"]
    unattempted = [url for url in unresolved if url not in attempted]
    sitemap_range["unattempted_locators"] = unattempted
    if exhausted_valid:
        sitemap_range["qualification"] = "Official sitemap locators are accounted inclusively through the observed reviewed navigation terminal; no dated prior-year boundary was observed."
        qualifications.append({"check": "reviewed_navigation_exhaustion_without_year_boundary", "terminal_url": terminal_url,
                               "earliest_dated_plan": min(duplicate_dates) if duplicate_dates else None,
                               "undated_daily_plans": sum(p.get("session_date") is None for p in posts),
                               "excluded_context_posts": len(excluded_posts), "historical_full_year_completeness_claimed": False})
        declared_scope = manifest.get("sitemap_scope", {})
        if (declared_scope.get("seed_url") != seed or declared_scope.get("end_url") != terminal_url
                or declared_scope.get("end_kind") != "observed_navigation_terminal"
                or declared_scope.get("candidate_count") != last - first + 1):
            errors.append({"check": "sitemap_exhaustion_scope_metadata"})
    if unattempted:
        errors.append({"check": "sitemap_locators_unaccounted", "urls": unattempted})
    if unresolved:
        qualifications.append({"check": "unavailable_sitemap_locators", "urls": unresolved})
    if first is None or last is None or first > last:
        errors.append({"check": "sitemap_range_unproven"})
    if not boundary_valid and not exhausted_valid:
        errors.append({"check": "lower_boundary_or_reviewed_exhaustion_not_proven"})
    earliest_stated = min(duplicate_dates) if duplicate_dates else None
    if earliest_stated and boundary and (date.fromisoformat(earliest_stated) - date.fromisoformat(start)).days > 31:
        class OlderLink(HTMLParser):
            def __init__(self):
                super().__init__()
                self.urls = []
            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if tag == "a" and values.get("id") == "Blog1_blog-pager-older-link":
                    self.urls.append(canonical(values.get("href", "")))
        edge_rows = []
        for post in posts:
            if post.get("session_date") != earliest_stated:
                continue
            raw = payload(stage, post["html"], "earliest-contemporary-navigation")
            links = OlderLink()
            links.feed(raw.decode("utf-8"))
            expected_older = canonical(boundary["url"]) if boundary else None
            verified = links.urls == [expected_older] and post.get("older_url") == boundary["url"]
            if not verified:
                errors.append({"check": "early_year_gap_navigation_edge", "url": post["url"], "older_links": links.urls})
            edge_rows.append({"from": post["url"], "to": expected_older, "verified_from_raw_html": verified})
        qualifications.append({"check": "early_year_navigation_gap", "scope_start": start,
                               "earliest_contemporary_map": earliest_stated,
                               "unobserved_calendar_days_before_first_map": (date.fromisoformat(earliest_stated) - date.fromisoformat(start)).days,
                               "next_older_boundary_date": boundary.get("session_date") if boundary else None,
                               "navigation_edges": edge_rows,
                               "qualification": "The observed older-post navigation jumps from the oldest contemporary map to a prior-year boundary. Every early calendar date remains an explicit gap; this does not establish that no earlier post ever existed."})
    if image_missing:
        qualifications.append({"check": "unavailable_article_images", "count": len(image_missing)})
    qualifications.extend(prior_body_changes)
    for stamp in sorted(duplicate_dates):
        if date.fromisoformat(stamp).weekday() >= 5:
            qualifications.append({"check": "stated_weekend_map_preserved", "session_date": stamp,
                                   "urls": [p["url"] for p in posts if p.get("session_date") == stamp],
                                   "qualification": "The source explicitly states this weekend date. Source update metadata is not used to silently correct the article's stated map date."})
    cursor, last_date = date.fromisoformat(start), date.fromisoformat(end)
    all_dates = []
    while cursor <= last_date:
        all_dates.append(cursor)
        cursor += timedelta(days=1)
    absent = [day for day in all_dates if day.isoformat() not in duplicate_dates]
    gaps = {"calendar_days": len(all_dates),
            "weekday_gaps": [day.isoformat() for day in absent if day.weekday() < 5],
            "weekend_gaps": [day.isoformat() for day in absent if day.weekday() >= 5],
            "policy": "No dated post observed; no holiday or historical-absence inference."}
    archive_text_check = {"status": "not_available", "articles_checked": 0}
    inventory_path = stage / "archive/archive-manifest.json"
    if inventory_path.exists():
        parser_path = root / "studies/27_verniman_method_knowledge/capture_daily_maps.py"
        spec = importlib.util.spec_from_file_location("independent_capture_parser", parser_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        inventory = json.loads(inventory_path.read_text())
        archive_errors = []
        for record in inventory["posts"]:
            capsule = stage / "archive" / record["capsule"]
            article = json.loads(gzip.decompress((capsule / "article.json.gz").read_bytes()))
            raw = gzip.decompress((capsule / "source.html.gz").read_bytes())
            parsed = module.Post(raw.decode("utf-8"))
            original = re.sub(r"\s+", "", "".join(parsed.parts))
            retained_text = re.sub(r"\s+", "", article["full_text"])
            if original != retained_text:
                archive_errors.append({"url": record["url"], "capsule": record["capsule"],
                                       "source_characters": len(original), "retained_characters": len(retained_text)})
        archive_text_check = {"status": "passed" if not archive_errors else "failed",
                              "articles_checked": len(inventory["posts"]),
                              "normalization": "whitespace removal only",
                              "independent_parser": parser_path.relative_to(root).as_posix(),
                              "independent_parser_sha256": sha(parser_path.read_bytes()),
                              "errors": archive_errors}
        if archive_errors:
            errors.append({"check": "complete_article_text", "articles": archive_errors})
    archive_image_order_check = {'status': 'not_available'}
    if inventory_path.exists():
        class RenderedImages(HTMLParser):
            def __init__(self):
                super().__init__()
                self.sources = []
            def handle_starttag(self, tag, attrs):
                if tag == 'img':
                    self.sources.append(dict(attrs).get('src'))
        pages = {}
        for entry in inventory['posts']:
            record = json.loads(gzip.decompress((stage / 'archive' / entry['capsule'] / 'article.json.gz').read_bytes()))
            stamp = record.get('session_date')
            folder = Path(stamp[:4]) / stamp[5:7] / stamp[8:] if stamp and start <= stamp <= end else Path('undated')
            page = stage / 'archive' / folder / 'index.html'
            pages.setdefault(page, [])
            pages[page].extend((stage / 'archive' / image['path']).resolve()
                               for image in record['images'] if image.get('path') and not image['path'].endswith('.bin'))
        image_order_errors = []
        total_rendered = 0
        for page, expected_sources in pages.items():
            rendered = RenderedImages()
            rendered.feed(page.read_text())
            sources = [(page.parent / unquote(urlsplit(src).path)).resolve() for src in rendered.sources]
            total_rendered += len(sources)
            if sources != expected_sources:
                image_order_errors.append({'page': page.relative_to(stage).as_posix(),
                                           'expected': [p.name for p in expected_sources], 'observed': [p.name for p in sources]})
        if image_order_errors:
            errors.append({'check': 'rendered_image_order', 'pages': image_order_errors})
        archive_image_order_check = {'status': 'passed' if not image_order_errors else 'failed',
                                     'dated_or_undated_pages': len(pages), 'rendered_image_elements': total_rendered,
                                     'errors': image_order_errors}
    archive_calendar_check = {"status": "not_available"}
    if inventory_path.exists():
        with (stage / "archive/coverage.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        expected = [day.isoformat() for day in reversed(all_dates)]
        observed = [row["date"] for row in rows]
        if observed != expected:
            errors.append({"check": "all_calendar_dates_descending", "expected": len(expected), "observed": len(observed)})
        for row in rows:
            stamp = row["date"]
            expected_count = duplicate_dates.get(stamp, 0)
            if int(row["post_count"]) != expected_count:
                errors.append({"check": "coverage_source_post_count", "date": stamp, "expected": expected_count, "observed": row["post_count"]})
            if not expected_count:
                expected_status = "no_dated_post_observed_weekend" if date.fromisoformat(stamp).weekday() >= 5 else "no_dated_post_observed_weekday"
                if row["status"] != expected_status:
                    errors.append({"check": "coverage_gap_status", "date": stamp, "expected": expected_status, "observed": row["status"]})
        indexes = {entry["path"]: entry["dates"] for entry in inventory["indexes"]}
        if indexes.get("index.html") != expected:
            errors.append({"check": "reader_index_calendar_order"})
        for year in sorted({day.year for day in all_dates}):
            year_key = f"{year}/index.html"
            expected_year = [stamp for stamp in expected if stamp.startswith(str(year) + "-")]
            if indexes.get(year_key) != expected_year:
                errors.append({"check": "reader_year_index_calendar_order", "year": year})
            for month in sorted({day.month for day in all_dates if day.year == year}):
                key = f"{year}/{month:02}/index.html"
                expected_month = [stamp for stamp in expected_year if stamp.startswith(f"{year}-{month:02}-")]
                if indexes.get(key) != expected_month:
                    errors.append({"check": "reader_month_index_calendar_order", "month": f"{year}-{month:02}"})
        for stamp in expected:
            if not (stage / "archive" / stamp[:4] / stamp[5:7] / stamp[8:] / "index.html").is_file():
                errors.append({"check": "daily_page_missing", "date": stamp})
        leap_days = [day.isoformat() for day in all_dates if day.month == 2 and day.day == 29]
        for stamp in leap_days:
            if not (stage / "archive" / stamp[:4] / "02/29/index.html").is_file():
                errors.append({"check": "leap_day_page_missing", "date": stamp})
            february = indexes.get(stamp[:4] + "/02/index.html", [])
            if len(february) != 29 or stamp not in february:
                errors.append({"check": "leap_february_index", "date": stamp, "dates": len(february)})
        archive_calendar_check = {"status": "passed" if observed == expected and not any(e["check"] in {"reader_index_calendar_order", "reader_year_index_calendar_order", "reader_month_index_calendar_order", "daily_page_missing", "coverage_source_post_count", "coverage_gap_status", "leap_day_page_missing", "leap_february_index"} for e in errors) else "failed", "calendar_days": len(rows), "leap_days": leap_days, "date_order": "descending", "year_end_weekend_records": [row for row in rows if row["date"] >= end[:4] + "-12-30" and date.fromisoformat(row["date"]).weekday() >= 5]}
    return {"audit": "offline_capture_integrity_and_coverage", "passed": not errors,
            "checked_unique_files": len(checked), "posts": len(posts), "distinct_dated_days": len(duplicate_dates),
            "multiple_post_dates": {k: [p["url"] for p in posts if p.get("session_date") == k] for k, v in sorted(duplicate_dates.items()) if v > 1},
            "archive_text_integrity": archive_text_check,
            "archive_calendar_integrity": archive_calendar_check,
            "archive_rendered_image_order": archive_image_order_check,
            "prior_source_records_checked": prior_source_records,
            "reviewed_date_exception_integrity": exception_verification,
            "legacy_source_date_adjustments": prior_date_adjustments,
            "prior_source_identity_omissions": prior_missing,
            "same_date_prior_body_changes": prior_body_changes,
            "daily_coverage": gaps,
            "observed_map_span": {"earliest_stated_date": min(duplicate_dates) if duplicate_dates else None, "latest_stated_date": max(duplicate_dates) if duplicate_dates else None, "scope_start": start, "scope_end": end, "qualification": "Source traversal may jump over calendar periods. All requested dates remain represented; no historical absence or holiday inference is made."},
            "images": dict(image_counts), "unavailable_images": image_missing,
            "source_articles_without_images": text_only_articles,
            "boundary_valid": boundary_valid, "source_exhaustion": exhaustion_check, "excluded_context_integrity": {"records": len(excluded_checks), "posts": excluded_checks, "status": "passed" if not any(e["check"].startswith("excluded_") or e["check"] == "all_excluded_context_images_recorded" for e in errors) else "failed"}, "sitemap_range": sitemap_range,
            "qualifications": qualifications, "errors": errors,
            "scope": "Source byte integrity, body-date correspondence, retained-source identities and image accounting only. No empirical validation or independent source-authenticity claim."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    args = parser.parse_args()
    result = audit(args.stage.resolve(), args.root.resolve())
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
