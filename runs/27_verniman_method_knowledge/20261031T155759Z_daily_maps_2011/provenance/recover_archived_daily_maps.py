#!/usr/bin/env python3
"""Bounded, paced recovery of explicitly indexed historical Daily Map sources.

This collector writes a fresh private source stage, never a dataset release.
Title dates and archived context are evidence for review; URL dates never repair
an unresolved source date. Closing/update/educational material stays context.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import importlib.util
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("retained_source_parser", Path(__file__).with_name("capture_retained_daily_maps.py"))
PARSER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARSER)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def requested_scope(year):
    if year not in {2011, 2012, 2013, 2014, 2015}:
        raise ValueError("source-recovery protocol supports only explicit 2011, 2012, 2013, 2014 or 2015 scope")
    return date(year, 1, 1), date(year, 12, 31)


def canonical(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.hostname not in {"verniman.blogspot.com", "verniman.blogspot.com.ar"} or parsed.scheme not in {"http", "https"}:
        raise ValueError(f"not a Verniman source locator: {url}")
    return urllib.parse.urlunsplit(("https", "verniman.blogspot.com", parsed.path or "/", "", ""))


class Article(PARSER.Article):
    def __init__(self, raw, base):
        self.navigation = []
        self.metadata = []
        self.heading_url = None
        super().__init__(raw, base)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("id") in {"Blog1_blog-pager-older-link", "Blog1_blog-pager-newer-link"}:
            self.navigation.append(values)
        if tag in {"abbr", "time"} or (tag == "meta" and any(k in values for k in ["itemprop", "property", "name"])):
            self.metadata.append(values)
        if self.in_title and tag == "a" and values.get("href"):
            self.heading_url = urllib.parse.urljoin(base_url(self.base), values["href"])
        super().handle_starttag(tag, attrs)


def base_url(url):
    return canonical(url)


def title_month_day(title):
    """Accept only an actual morning-source title; never a permalink filename."""
    first = re.fullmatch(r"(?:Outlook|Opening(?:\s+Print)?)\s+(\d{1,2})/(\d{1,2})", title, re.I)
    second = re.fullmatch(r"Opening(?:\s+Print)?\s+(\d{2})(\d{2})", title, re.I)
    matched = first or second
    if not matched:
        return None
    month, day = map(int, matched.groups())
    date(2000, month, day)
    return month, day


def classify(article, observed, year):
    title = article.title
    primary = bool(re.match(r"^(?:Outlook|Opening(?:\s+Print)?)(?:\b|\s)", title, re.I))
    result = {"role": "daily_plan_candidate" if primary else "excluded_context_candidate",
              "session_date": None, "session_date_method": "unresolved_source_date",
              "date_warnings": [], "requires_year_review": False}
    if not primary:
        result["scope_qualification"] = "Non-morning or educational source retained as context pending review."
        return result
    try:
        md = title_month_day(title)
    except ValueError:
        result["date_warnings"].append("Source title month/day is invalid; retained without date repair.")
        return result
    if md is None:
        result["date_warnings"].append("Morning source title/body has no supported exact date; no URL/image/neighbor-date inference.")
        result["reviewed_daily_plan"] = True
        result["date_review"] = {"status": "undated_title_missing_month_day", "source_title": title}
        result["year_evidence"] = {"year": year, "method": "undated_morning_source_in_archived_year_context", "archive_observed_at": observed,
                                   "qualification": "No month/day is assigned; source year is context only."}
        return result
    proposed = date(year, *md)
    observed_date = datetime.fromisoformat(observed).date()
    contract_tokens = sorted(set(re.findall(r"\b(?:ES|NQ|YM|RTY|CL|GC)[HMUZ]\d{1,2}\b", " ".join(article.parts))))
    if observed_date.year == year and proposed <= observed_date:
        result.update(session_date=proposed.isoformat(), session_date_method="actual_source_title_with_contemporaneous_archive_context")
    elif observed_date.year == year + 1 and observed_date.month <= 2 and proposed.month >= 11:
        result.update(session_date=proposed.isoformat(), session_date_method="actual_source_title_with_review_required_year_end_archive_context", requires_year_review=True)
        result["date_warnings"].append("Late-year source retained in an early-next-year archive; explicit year-context review required.")
    else:
        result["requires_year_review"] = True
        result["date_warnings"].append("Title month/day survives but archive context alone does not establish the requested year.")
    result["year_evidence"] = {"year": year, "method": result["session_date_method"],
                               "source_title": title, "archive_observed_at": observed,
                               "source_contract_tokens": contract_tokens,
                               "qualification": "Archive observation, actual title and source context require independent review; original URL is only a locator."}
    result["reviewed_daily_plan"] = result["session_date"] is not None
    result["date_review"] = {"status": "dated_title" if result["session_date"] else "year_context_review_required", "source_title": title}
    return result


class Recovery:
    def __init__(self, root, stage, year, interval, retry_delay):
        if interval < 3.4:
            raise ValueError("Wayback interval must be at least 3.4 seconds")
        self.root, self.stage, self.year = root.resolve(), stage.resolve(), year
        if self.stage.exists():
            raise FileExistsError(f"refusing existing source recovery stage: {self.stage}")
        self.stage.mkdir(parents=True)
        (self.stage / "responses").mkdir()
        (self.stage / "images").mkdir()
        (self.stage / "capture-pages-producer.py").write_bytes(Path(__file__).read_bytes())
        self.interval, self.retry_delay, self.last_wayback = interval, retry_delay, None
        self.attempts = []
        self.reuse = {}

    def identity(self, path, kind="source_evidence"):
        raw = path.read_bytes()
        return {"kind": kind, "path": path.relative_to(self.root).as_posix(), "bytes": len(raw), "sha256": sha(raw)}

    def retain(self, raw, name, kind, **metadata):
        target = self.stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(raw)
        return {**self.identity(target, kind), **metadata}

    def copy_input(self, path, expected, name):
        raw = path.read_bytes()
        if expected and sha(raw) != expected:
            raise ValueError(f"input hash mismatch: {path}")
        return self.retain(raw, name, "archive_index", original_input_path=str(path))

    def add_reuse(self, manifest):
        data = json.loads(manifest.read_text())
        rows = data if isinstance(data, list) else data.get("queries", [])
        for row in rows:
            url = row.get("url") or row.get("requested_url")
            status = row.get("status", row.get("http_status"))
            if status != 200 or not url:
                continue
            body = row.get("body")
            path = Path(body["path"] if isinstance(body, dict) else row.get("path", ""))
            if not path.is_absolute():
                path = self.root / path
            if not path.is_file():
                continue
            raw = path.read_bytes()
            expected = body if isinstance(body, dict) else row
            if sha(raw) != expected.get("sha256") or len(raw) != expected.get("bytes"):
                raise ValueError(f"reused response identity mismatch: {path}")
            self.reuse[self.archive_key(url)] = (row, path, raw)

    @staticmethod
    def archive_key(url):
        return url.replace("verniman.blogspot.com.ar:80", "verniman.blogspot.com.ar").replace("verniman.blogspot.com:80", "verniman.blogspot.com")

    def paced(self):
        if self.last_wayback is not None:
            remaining = self.interval - (time.monotonic() - self.last_wayback)
            if remaining > 0:
                time.sleep(remaining)
        self.last_wayback = time.monotonic()

    def fetch_source(self, item, ordinal):
        original = item["archive_source_url"].replace("verniman.blogspot.com:80", "verniman.blogspot.com")
        requested = f"https://web.archive.org/web/{item['archive_timestamp']}id_/{original}"
        reused = self.reuse.get(self.archive_key(requested))
        if reused:
            old, path, raw = reused
            record = self.retain(raw, f"responses/source-{ordinal:04d}-retained.html", "archive_html",
                                 url=requested, final_url=old.get("final_url") or requested, http_status=200,
                                 captured_at=old.get("completed_at"), request_started_at=old.get("began") or old.get("requested_at"),
                                 capture_kind="retained", original_retained_path=str(path),
                                 timing_qualification="Original response completion clock unavailable; request clock is retained separately." if not old.get("completed_at") else None,
                                 body_truncated=False, headers=old.get("headers") if isinstance(old.get("headers"), dict) and "path" not in old["headers"] else {},
                                 reused_response_identity={"path": str(path), "bytes": len(raw), "sha256": sha(raw)})
            return record, raw, [record]
        attempts = []
        for attempt in range(1, 3):
            self.paced()
            record = {"kind": "archive_html", "url": requested, "request_started_at": now(), "attempt": attempt}
            raw = None
            try:
                request = urllib.request.Request(requested, headers={"User-Agent": "Abacus private historical-source capture/1.0"})
                try:
                    response = urllib.request.urlopen(request, timeout=30)
                except urllib.error.HTTPError as failure:
                    response = failure
                with response:
                    raw = response.read(20 * 1024 * 1024 + 1)
                    record.update(http_status=response.status, final_url=response.geturl(), headers=dict(response.headers),
                                  body_truncated=len(raw) > 20 * 1024 * 1024)
                raw = raw[:20 * 1024 * 1024]
                record.update(self.retain(raw, f"responses/source-{ordinal:04d}-attempt-{attempt}.html", "archive_html"))
            except (OSError, urllib.error.URLError) as error:
                record.update(error=f"{type(error).__name__}: {error}", http_status=None)
            record["captured_at"] = now()
            attempts.append(record)
            self.attempts.append(record)
            if record.get("http_status") == 200 and not record.get("body_truncated"):
                return record, raw, attempts
            if attempt == 1:
                time.sleep(self.retry_delay)
        return None, None, attempts

    def parse_post(self, item, record, raw, attempts):
        replay = record.get("final_url") or record["url"]
        stamp = re.search(r"/web/(\d{14})", replay)
        timestamp = stamp.group(1) if stamp else item["archive_timestamp"]
        observed = datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat()
        article = Article(raw.decode("utf-8", "replace"), item["url"])
        post = {**item, "archive_url": replay, "archive_observed_at": observed, "html": record,
                "captured_at": record.get("captured_at"), "attempts": attempts,
                "title": article.title, "body_text": "".join(article.parts), "source_post_ids": article.post_ids,
                "source_post_id": article.post_ids[0] if len(set(article.post_ids)) == 1 else None,
                "post_body_count": article.body_count, "navigation_links": article.navigation,
                "source_metadata_claims": article.metadata, "source_format": "archived_html", "atom": None,
                "source_heading_permalink": article.heading_url, "images": [], "actual_image_elements": article.images,
                "capture_errors": [], "image_capture_errors": [],
                "image_revision_qualification": "Current linked-image responses; historical byte identity unverified."}
        if article.body_count == 1:
            post.update(classify(article, observed, self.year))
        else:
            post.update(role="unselected_multi_or_empty_source", session_date=None,
                        scope_qualification="Raw page retained; exact selected post extraction is required before daily classification.")
        post["session_date_source_text"] = article.title
        return post

    def fetch_image(self, url, ordinal, label="full"):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not (parsed.hostname == "blogger.googleusercontent.com" or re.fullmatch(r"\d+\.bp\.blogspot\.com", parsed.hostname or "")):
            return {"url": url, "error": "Actual source image host is outside the bounded image-source policy."}
        attempts = []
        candidates = [url]
        if parsed.scheme == "http":
            candidates.append(urllib.parse.urlunsplit(("https", parsed.netloc, parsed.path, parsed.query, "")))
        for attempt, requested in enumerate(candidates, 1):
            record = {"kind": "current_source_image_fallback", "url": url, "requested_url": requested,
                      "request_started_at": now(), "attempt": attempt}
            try:
                request = urllib.request.Request(requested, headers={"User-Agent": "Abacus private source-image capture/1.0"})
                try:
                    response = urllib.request.urlopen(request, timeout=25)
                except urllib.error.HTTPError as failure:
                    response = failure
                with response:
                    raw = response.read(20 * 1024 * 1024 + 1)
                    record.update(http_status=response.status, final_url=response.geturl(), headers=dict(response.headers),
                                  body_truncated=len(raw) > 20 * 1024 * 1024)
                record.update(self.retain(raw[:20 * 1024 * 1024], f"images/image-{ordinal:04d}-{label}-attempt-{attempt}.response.body", "current_source_image_fallback"))
            except (OSError, urllib.error.URLError) as error:
                record.update(http_status=None, error=f"{type(error).__name__}: {error}")
            record["captured_at"] = now()
            attempts.append(record)
            if record.get("http_status") == 200 and record.get("headers", {}).get("Content-Type", "").startswith("image/") and not record.get("body_truncated"):
                record.update(original_image_url=url, source_revision_status="current_image_response_historical_bytes_unverified",
                              historical_digest_match_verified=False, attempts=attempts[:-1])
                if requested != url:
                    record["transport_qualification"] = "Exact source host/path preserved; HTTPS transport retried after original HTTP response failure."
                return record
        return {"url": url, "error": "No retained usable response from actual linked source image.", "attempts": attempts}

    def fetch_element(self, element, ordinal):
        requested, inline = element["url"], element["inline_url"]
        def asset_name(value):
            return urllib.parse.unquote(urllib.parse.urlsplit(value).path).rsplit("/", 1)[-1]
        qualification = None
        if requested != inline and asset_name(requested) != asset_name(inline):
            qualification = "Linked image filename differs from actual inline source; retain exact inline rendition without guessing a corrected full-size URL."
        full = ({"url": requested, "error": qualification, "attempts": []} if qualification
                else self.fetch_image(requested, ordinal, "full"))
        if not full.get("error"):
            full.update(original_image_url=requested, rendition="linked_full_image")
            return full
        if inline != requested:
            candidate = self.fetch_image(inline, ordinal, "inline")
            if not candidate.get("error"):
                candidate.update(original_image_url=requested, rendition="inline_thumbnail",
                                 full_size_error=full["error"], source_link_qualification=qualification,
                                 full_size_attempts=full.get("attempts", []))
                return candidate
            attempts = [*full.get("attempts", []), *candidate.get("attempts", [])]
        else:
            attempts = full.get("attempts", [])
        return {"kind": "missing_source_image", "original_image_url": requested, "url": requested,
                "inline_url": inline, "error": "Actual linked and inline source image responses are unavailable.",
                "attempts": attempts, "historical_digest_match_verified": False,
                "source_revision_status": "current_image_response_historical_bytes_unverified"}


def complete_images(args):
    """Finish a captured source stage, retaining the initial page evidence unchanged."""
    root = args.root.resolve()
    stage = (args.stage if args.stage.is_absolute() else root / args.stage).resolve()
    stage.relative_to(root)
    original_manifest = stage / "source-recovery-manifest.json"
    document = json.loads(original_manifest.read_text())
    first, last = requested_scope(args.year)
    if any(key in document for key in ["requested_start_date", "anchor_session_date"]):
        if document.get("requested_start_date") != first.isoformat() or document.get("anchor_session_date") != last.isoformat():
            raise ValueError("source stage scope differs from requested image-capture year")
    if document.get("image_capture_status") != "pending":
        raise ValueError("source stage is not awaiting image capture")
    if (stage / "recovery-manifest.json").exists():
        raise FileExistsError("refusing existing completed image/recovery manifest")
    verifier = PARSER.Adapter(root)
    for record in document["files"]:
        verifier.verify(record)
    recovery = Recovery.__new__(Recovery)
    recovery.root, recovery.stage, recovery.year = root, stage, args.year
    (stage / "capture-images-producer.py").write_bytes(Path(__file__).read_bytes())
    posts = document["posts"]
    supplementary = []
    for manifest_path in args.feed_manifest:
        raw_manifest = manifest_path.read_bytes()
        source_input = recovery.retain(raw_manifest, f"feed-input-{len(supplementary)+1:02d}.json", "archive_feed_capture_input", original_input_path=str(manifest_path))
        supplementary.append(source_input)
        feed_document = json.loads(raw_manifest)
        for query in feed_document.get("queries", []):
            if query.get("status") != 200 or query.get("body_truncated"):
                raise ValueError("supplementary feed source lacks a complete successful response")
            body_record = query["body"]
            body_path = Path(body_record["path"])
            if not body_path.is_absolute():
                body_path = root / body_path
            raw_xml = body_path.read_bytes()
            if sha(raw_xml) != body_record["sha256"] or len(raw_xml) != body_record["bytes"]:
                raise ValueError("supplementary full feed XML identity differs")
            request_url = query["requested_url"]
            timestamp = re.search(r"/web/(\d{14})", request_url).group(1)
            observed = datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat()
            header = query.get("headers")
            headers = {}
            header_record = None
            if header:
                header_path = Path(header["path"])
                if not header_path.is_absolute():
                    header_path = root / header_path
                raw_headers = header_path.read_bytes()
                if sha(raw_headers) != header["sha256"] or len(raw_headers) != header["bytes"]:
                    raise ValueError("supplementary feed header identity differs")
                header_record = recovery.retain(raw_headers, f"responses/feed-{sha(raw_xml)[:16]}.headers.json", "http_headers")
                decoded = json.loads(raw_headers)
                headers = dict(decoded) if isinstance(decoded, list) else decoded
            atom = recovery.retain(raw_xml, f"responses/feed-{sha(raw_xml)}.xml", "archive_feed",
                                   url=request_url, final_url=query.get("final_url") or request_url, http_status=200,
                                   request_started_at=query.get("requested_at"), captured_at=query.get("completed_at"),
                                   body_truncated=False, headers=headers, header_record=header_record)
            tree = ET.fromstring(raw_xml)
            namespace = {"a": "http://www.w3.org/2005/Atom"}
            for ordinal, entry in enumerate(tree.findall("a:entry", namespace), 1):
                selector = entry.findtext("a:id", namespaces=namespace)
                title = entry.findtext("a:title", namespaces=namespace)
                content = entry.find("a:content", namespace)
                if not selector or title is None or content is None or content.get("type") != "html" or list(content):
                    raise ValueError("unsupported exact archived feed entry")
                body = content.text or ""
                links = [link.get("href") for link in entry.findall("a:link", namespace) if link.get("rel") == "alternate"]
                if len(links) != 1:
                    raise ValueError("archived feed entry has ambiguous alternate source URL")
                url = canonical(links[0])
                derived = ('<html><body><h3 class="post-title">' + html.escape(title) + '</h3><div class="post-body">' + body + '</div></body></html>')
                article = Article(derived, url)
                classification = classify(article, observed, args.year)
                published = entry.findtext("a:published", namespaces=namespace)
                # A visibly unambiguous DD/MM typo is only assigned when the
                # exact archived entry's published calendar corroborates it.
                typo = re.fullmatch(r"Outlook\s+(\d{1,2})/(\d{1,2})", title, re.I)
                if typo and int(typo[1]) > 12 and 1 <= int(typo[2]) <= 12:
                    qualified = date(args.year, int(typo[2]), int(typo[1]))
                    if not published or published[:10] != qualified.isoformat():
                        raise ValueError("unambiguous title DD/MM lacks exact archived publication corroboration")
                    classification.update(session_date=qualified.isoformat(), session_date_method="explicit_reviewed_title_day_month_with_archived_entry_publication",
                                          reviewed_daily_plan=True, requires_year_review=False,
                                          date_review={"status": "dated_title", "date_order": "day_month", "source_title": title,
                                                       "corroborating_published_at": published,
                                                       "reason": "Literal first title component exceeds12; exact archived entry publication calendar corroborates explicit DD/MM interpretation."},
                                          date_warnings=["Literal title uses unambiguous DD/MM; interpretation is explicitly qualified and corroborated by exact archived entry publication calendar."],
                                          year_evidence={"year": args.year, "method": "exact_archived_feed_entry_title_and_publication_context",
                                                         "source_title": title, "archive_observed_at": observed, "source_published_at": published})
                source_id = selector.rsplit(".post-", 1)[-1]
                post = {"url": url, "title": title, "source_format": "archived_atom_feed", "html": None, "atom": atom,
                        "archive_url": request_url, "archive_source_url": request_url.split("id_/", 1)[-1],
                        "archive_observed_at": observed, "captured_at": query.get("completed_at"),
                        "source_feed": atom, "source_capture_record": source_input,
                        "source_feed_entry_ordinal": ordinal, "source_entry_selector": selector, "source_entry_id": selector,
                        "source_post_id": source_id, "source_published_at": published,
                        "source_updated_at": entry.findtext("a:updated", namespaces=namespace),
                        "body_html": body, "body_text": "".join(article.parts), "actual_image_elements": article.images,
                        "navigation_links": [], "capture_errors": [], "images": [], "image_capture_errors": [],
                        "session_date_source_text": title,
                        "image_revision_qualification": "Current linked-image responses; historical byte identity unverified.",
                        **classification}
                entry_path = stage / f"feed-{sha(raw_xml)[:12]}-entry-{ordinal:03d}.json"
                with entry_path.open("x") as output:
                    output.write(json.dumps(post, ensure_ascii=False, indent=2) + "\n")
                post["entry_record"] = recovery.identity(entry_path, "archive_feed_entry_record")
                posts.append(post)
    for path in args.supplement_posts:
        raw = path.read_bytes()
        extra = json.loads(raw)
        if not isinstance(extra, list):
            raise ValueError("supplementary source posts must be an explicit JSON list")
        supplementary.append(recovery.retain(raw, f"supplement-posts-{len(supplementary)+1:02d}.json", "source_supplement", original_input_path=str(path)))
        posts.extend(extra)
    for post in posts:
        # Home/index observations may expose one exact post. Its real heading
        # permalink, not the homepage URL or title date, identifies that post.
        if post.get("html") and urllib.parse.urlsplit(post["url"]).path == "/" and post.get("post_body_count") == 1:
            heading = post.get("source_heading_permalink")
            if not heading or not post.get("source_post_id"):
                raise ValueError("single homepage post lacks an exact heading permalink/post ID")
            post["original_page_url"] = post["url"]
            post["url"] = canonical(heading)
            post["source_format"] = "archived_page_post"
            post["source_entry_selector"] = str(post["source_post_id"])
    keys = list(dict.fromkeys((e["url"], e["inline_url"]) for post in posts for e in post.get("actual_image_elements", [])))
    elements = [{"url": full, "inline_url": inline} for full, inline in keys]
    lock = threading.Lock()
    completed = [0]
    print(json.dumps({"phase": "image_capture", "unique_source_elements": len(keys), "source_records": len(posts)}), flush=True)
    def capture(pair):
        ordinal, element = pair
        result = recovery.fetch_element(element, ordinal)
        with lock:
            completed[0] += 1
            with (stage / "image-progress.jsonl").open("a") as output:
                output.write(json.dumps({"completed": completed[0], "total": len(keys), "source_url": element["url"],
                                         "retained_url": result.get("url"), "rendition": result.get("rendition"),
                                         "error": result.get("error"), "status": result.get("http_status")}) + "\n")
            if completed[0] % 10 == 0:
                print(json.dumps({"images_completed": completed[0], "total": len(keys)}), flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(capture, enumerate(elements, 1)))
    by_element = dict(zip(keys, results))
    for ordinal, post in enumerate(posts, 1):
        post["images"] = [by_element[(e["url"], e["inline_url"])] for e in post.get("actual_image_elements", [])]
        post["image_capture_errors"] = [image for image in post["images"] if image.get("error")]
        target = stage / f"source-{ordinal:04d}.post.json"
        with target.open("x") as output:
            output.write(json.dumps(post, ensure_ascii=False, indent=2) + "\n")
        post["post_record"] = recovery.identity(target, "archive_post_record")
    document.update(posts=posts, image_capture_status="completed", image_capture_completed_at=now(),
                    image_capture_command=sys.argv, supplementary_source_records=supplementary,
                    source_recovery_manifest=recovery.identity(original_manifest),
                    stop_reason="bounded_archive_source_and_image_capture_completed",
                    files=[recovery.identity(p) for p in sorted(stage.rglob("*")) if p.is_file()])
    target = stage / "recovery-manifest.json"
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"complete": True, "manifest": recovery.identity(target), "sources": len(posts),
                      "unique_source_elements": len(keys), "image_failures": sum(bool(r.get("error")) for r in results),
                      "inline_fallbacks": sum(r.get("rendition") == "inline_thumbnail" for r in results)}), flush=True)


def projected_response_metadata(value, verifier):
    """Keep original capture locators as annotations, with retained byte proof."""
    if isinstance(value, list):
        return [projected_response_metadata(item, verifier) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: projected_response_metadata(item, verifier) for key, item in value.items()}
    origin = result.get("reused_response_identity")
    if origin is not None:
        if not isinstance(origin, dict) or not isinstance(origin.get("path"), str):
            raise ValueError("reused response origin lacks an original path")
        retained = {key: result[key] for key in ["path", "bytes", "sha256"]}
        verifier.verify(retained)
        if any(origin.get(key) != retained[key] for key in ["bytes", "sha256"]):
            raise ValueError("reused response origin differs from the retained payload")
        result["reused_response_identity"] = {
            **{key: item for key, item in origin.items() if key != "path"},
            "original_path": origin["path"], "retained_payload": retained}
    return result


def reviewed_morning_classification(post, decision, review_record, verifier, year):
    """Promote only an exact independently reviewed 2011/2012/2013/2014 morning source."""
    title = post.get("title", "")
    if (year not in {2011, 2012, 2013, 2014} or not isinstance(decision, dict)
            or decision.get("status") != "reviewed_morning_plan"
            or decision.get("source_post_id") != post.get("source_post_id")
            or decision.get("source_title") != title
            or decision.get("source_post_record") != post.get("post_record")
            or not isinstance(decision.get("reason"), str) or not decision["reason"].strip()
            or not isinstance(decision.get("year_context_reason"), str) or not decision["year_context_reason"].strip()
            or not re.fullmatch(r"(?:Market\s+Update|Update)(?:\s+(?:\d{1,2}/\d{1,2}|\d{4}))?", title, re.I)):
        raise ValueError("morning classification lacks an exact supported source review")
    verifier.verify(post["post_record"])
    if post.get("source_format") == "archived_atom_feed":
        source, _ = verifier.atom_entry(post)
    elif post.get("source_format") in {"archived_html", "archived_page_post"}:
        source = verifier.verify(post["html"])
    else:
        raise ValueError("reviewed morning classification has an unsupported source format")
    article = Article(source.decode("utf-8"), post["url"])
    normalized = PARSER.text_identity("".join(article.parts))
    if (article.body_count != 1 or article.title != title
            or decision.get("normalized_body_sha256") != sha(normalized.encode())
            or PARSER.text_identity(post.get("body_text", "")) != normalized
            or post.get("source_format") != "archived_atom_feed" and str(post.get("source_post_id")) not in article.post_ids):
        raise ValueError("reviewed morning classification source body or identity differs")
    matched = re.fullmatch(r"(?:Market\s+Update|Update)\s+(\d{1,2})/(\d{1,2})", title, re.I)
    compact = re.fullmatch(r"(?:Market\s+Update|Update)\s+(\d{2})(\d{2})", title, re.I)
    title_date = matched or compact
    if title_date is None and not re.fullmatch(r"Market\s+Update", title, re.I):
        raise ValueError("only an exact reviewed Market Update may retain an unresolved title date")
    session_date = date(year, *map(int, title_date.groups())).isoformat() if title_date else None
    if decision.get("session_date") != session_date:
        raise ValueError("reviewed morning classification cannot replace the literal title date")
    if session_date is None and PARSER.reviewed_title_dates(" ".join(article.parts), True, market_update=True):
        raise ValueError("undated reviewed morning body contains a supported explicit date")
    warnings = list(post.get("date_warnings", []))
    if session_date is None:
        warnings.append("Reviewed morning source has no supported exact title/body date; retained undated without URL/image/neighbor-date inference.")
    published = post.get("source_published_at")
    if session_date and published and published[:10] != session_date:
        warnings.append("Original source publication claim " + published + " differs from the reviewed title day; literal source title and independently reviewed archived year determine this session date.")
    post.update(role="daily_plan_candidate", reviewed_daily_plan=True, session_date=session_date,
                session_date_method="explicit_reviewed_morning_source_title" if session_date else "explicit_reviewed_undated_morning_source",
                date_review={"status": "dated_title" if session_date else "undated_title_missing_month_day", "source_title": title},
                date_warnings=warnings, requires_year_review=False,
                scope_qualification="Morning plan explicitly reviewed against exact source identity and body; original candidate classification remains in its retained record.",
                year_evidence={"year": year, "method": "explicit_independent_morning_source_context_review",
                               "source_title": title, "archive_observed_at": post.get("archive_observed_at"),
                               "independent_review_reason": decision["year_context_reason"], "membership_review": review_record},
                daily_plan_classification_review={**decision, "review_record": review_record})
    return post


def reviewed_collection(args):
    """Project an explicit independent membership review, without new date guesses."""
    root = args.root.resolve()
    first, last = requested_scope(getattr(args, "year", 2015))
    review_path = (args.review_selection if args.review_selection.is_absolute() else root / args.review_selection).resolve()
    review_path.relative_to(root)
    output = (args.reviewed_output if args.reviewed_output.is_absolute() else root / args.reviewed_output).resolve()
    output.relative_to(root)
    if output.exists():
        raise FileExistsError(f"refusing an existing reviewed collection: {output}")
    review = json.loads(review_path.read_text())
    if (review.get("schema_version") != "daily-map-archive-source-review-1"
            or review.get("review_status") != "reviewed"
            or review.get("requested_start_date") != first.isoformat()
            or review.get("anchor_session_date") != last.isoformat()
            or review.get("historical_full_year_completeness_claimed") is not False):
        raise ValueError("review scope/status or historical completeness declaration differs")
    verifier = PARSER.Adapter(root)
    recovery_record = review["source_recovery_manifest"]
    recovery = json.loads(verifier.verify(recovery_record))
    if recovery.get("requested_start_date") != first.isoformat() or recovery.get("anchor_session_date") != last.isoformat():
        raise ValueError("raw source recovery scope differs from requested review year")
    precheck = json.loads(verifier.verify(review["selection_precheck"]))
    review_documents = {}
    for key in ["chronology_review", "collection_completion_review"]:
        content = json.loads(verifier.verify(review[key]))
        if content.get("requested_start_date") != first.isoformat() or content.get("anchor_session_date") != last.isoformat():
            raise ValueError(f"{key} scope differs from requested {first.year} review")
        review_documents[key] = content
    completion = review_documents["collection_completion_review"]
    if completion.get("lower_boundary_observed") is not False or completion.get("historical_full_year_completeness_claimed") is not False:
        raise ValueError("completion review must retain observed-coverage and lower-boundary limits")
    if precheck.get("status") != "passed" or recovery.get("image_capture_status") != "completed":
        raise ValueError("independent selection audit or recovery phase has not passed")
    for record in recovery["files"]:
        verifier.verify(record)
    supporting_files = review.get("supporting_files", [])
    if not isinstance(supporting_files, list):
        raise ValueError("supporting_files must be an explicit descriptor list")
    for record in supporting_files:
        verifier.verify(record)
    ids = precheck.get("selected_source_ids")
    if not isinstance(ids, list) or len(ids) != len(set(ids)):
        raise ValueError("reviewed selected source identities are absent or repeated")
    empty_review = review.get("empty_daily_selection_review")
    if not ids:
        zero_counts = ["selected_records", "dated", "undated", "image_references", "unique_image_hashes"]
        if (first.year not in {2011, 2012, 2013} or not isinstance(empty_review, dict)
                or empty_review.get("status") != "reviewed_no_in_scope_daily_plans"
                or empty_review.get("requested_start_date") != first.isoformat()
                or empty_review.get("anchor_session_date") != last.isoformat()
                or not isinstance(empty_review.get("reason"), str) or not empty_review["reason"].strip()
                or empty_review.get("independent_selection_precheck") != review["selection_precheck"]
                or any(type(precheck.get(key)) is not int or precheck[key] != 0 for key in zero_counts)):
            raise ValueError("empty source selection lacks an exact independent zero-source review")
    elif empty_review is not None:
        raise ValueError("nonempty source selection contradicts an empty-selection review")
    classification_reviews = review.get("daily_plan_classification_reviews", {})
    if not isinstance(classification_reviews, dict) or not set(classification_reviews) <= set(map(str, ids)):
        raise ValueError("morning classification reviews must identify selected exact sources")
    review_record = {"path": review_path.relative_to(root).as_posix(), "bytes": review_path.stat().st_size,
                     "sha256": sha(review_path.read_bytes())}
    overlaps = {row["selected_post_id"]: row for row in precheck.get("overlaps", [])}
    selected = []
    selected_records = set()
    for identifier in ids:
        candidates = [p for p in recovery["posts"] if str(p.get("source_post_id")) == str(identifier)]
        if len(candidates) > 1:
            rule = overlaps.get(str(identifier))
            if rule is None:
                raise ValueError(f"overlap has no explicit reviewed choice: {identifier}")
            candidates = [p for p in candidates if p.get("source_format") == rule["selected_format"]
                          and (p.get("html") or p.get("atom") or {}).get("sha256") == rule["selected_html_or_atom_sha256"]]
        if len(candidates) != 1:
            raise ValueError(f"reviewed choice does not identify one exact source: {identifier}")
        post = projected_response_metadata(candidates[0], verifier)
        if str(identifier) in classification_reviews:
            post = reviewed_morning_classification(post, classification_reviews[str(identifier)], review_record, verifier, first.year)
        if post.get("role") != "daily_plan_candidate" or post.get("reviewed_daily_plan") is not True:
            raise ValueError(f"review would promote unreviewed context as daily plan: {identifier}")
        if post.get("year_evidence", {}).get("year") != first.year or (post.get("session_date") and not first <= date.fromisoformat(post["session_date"]) <= last):
            raise ValueError(f"selected source year differs from requested review: {identifier}")
        verifier.verify(post["post_record"])
        if post.get("requires_year_review"):
            reason = review.get("year_context_reviews", {}).get(str(identifier))
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"source needs explicit year-context review: {identifier}")
            post["year_evidence"] = {**post["year_evidence"], "independent_review_reason": reason,
                                     "membership_review": {"path": review_path.relative_to(root).as_posix(),
                                                           "bytes": review_path.stat().st_size,
                                                           "sha256": sha(review_path.read_bytes())}}
            post["requires_year_review"] = False
        selected.append(post)
        selected_records.add(post["post_record"]["path"])
    if len(selected) != precheck["selected_records"]:
        raise ValueError("selected source count differs from independent review")
    actual_counts = {"dated": sum(bool(p.get("session_date")) for p in selected),
                     "undated": sum(p.get("session_date") is None for p in selected),
                     "image_references": sum(len(p["images"]) for p in selected),
                     "unique_image_hashes": len({im.get("sha256") for p in selected for im in p["images"] if im.get("sha256")})}
    if any(actual_counts[key] != precheck[key] for key in actual_counts):
        raise ValueError("selected date/image counts differ from independent review")
    selected.sort(key=lambda p: (p.get("session_date") or "", p["url"]), reverse=True)
    contexts, supporting = [], []
    for post in recovery["posts"]:
        if post["post_record"]["path"] in selected_records:
            continue
        if str(post.get("source_post_id")) in set(map(str, ids)):
            supporting.append(projected_response_metadata(post, verifier))
        else:
            contexts.append(projected_response_metadata(post, verifier))
    records = [*recovery["files"], recovery_record, review["selection_precheck"],
               review["chronology_review"], review["collection_completion_review"],
               *supporting_files,
               {"path": review_path.relative_to(root).as_posix(), "bytes": review_path.stat().st_size,
                "sha256": sha(review_path.read_bytes())}]
    files = {}
    for record in records:
        old = files.get(record["path"])
        if old and any(old[k] != record[k] for k in ["sha256", "bytes"]):
            raise ValueError(f"reviewed inventory contains conflicting bytes: {record['path']}")
        files[record["path"]] = record
    coverage = []
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        found = [p for p in selected if p.get("session_date") == day.isoformat()]
        coverage.append({"session_date": day.isoformat(), "status": "post_captured" if found else
                         "weekend_no_dated_post" if day.weekday() >= 5 else "weekday_no_dated_post",
                         "post_urls": [p["url"] for p in found],
                         "reason": "Observed surviving source coverage only; no historical-absence claim or unresolved-date repair."})
    result = {"source": "verniman", "crawl_id": output.parent.name, "batch_id": output.parent.name,
              "requested_start_date": first.isoformat(), "anchor_session_date": last.isoformat(),
              "stop_reason": "reviewed_bounded_archive_observed_coverage", "traversal_reached_lower_boundary": False,
              "historical_full_year_completeness_claimed": False, "posts": selected, "coverage": coverage,
              "traversal": [{"kind": "reviewed_archived_source_revision", "source_url": p["url"],
                             "session_date": p.get("session_date"), "archive_url": p["archive_url"],
                             "post_record": p["post_record"]} for p in selected],
              "excluded_context_posts": contexts, "unselected_supporting_revisions": supporting,
              "selection_review": review["selection_precheck"], "overlap_decisions": precheck.get("overlaps", []),
              "chronology_review": review["chronology_review"],
              "collection_completion_review": review["collection_completion_review"],
              "archive_capture_manifest": recovery_record,
              "collection_review": {"path": review_path.relative_to(root).as_posix(),
                                    "bytes": review_path.stat().st_size, "sha256": sha(review_path.read_bytes())},
              "supporting_files": supporting_files,
              "date_policy": "Actual selected source-title M/D or MMDD with reviewed archived year; missing source dates remain null; explicit unambiguous DD/MM review retained.",
              "files": list(files.values())}
    if empty_review is not None:
        result["empty_daily_selection_review"] = {**empty_review, "review_record": review_record}
    with output.open("x") as destination:
        destination.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"reviewed_collection": {"path": output.relative_to(root).as_posix(), "bytes": output.stat().st_size,
                                              "sha256": sha(output.read_bytes())},
                      "selected": len(selected), "dated": sum(bool(p.get("session_date")) for p in selected),
                      "undated": sum(p.get("session_date") is None for p in selected),
                      "context": len(contexts), "supporting_revisions": len(supporting)}))


def index_items(path, expected, root, year):
    raw = path.read_bytes()
    if expected and sha(raw) != expected:
        raise ValueError(f"index hash differs: {path}")
    rows = json.loads(raw)
    header = rows[0]
    entries = [dict(zip(header, row)) for row in rows[1:]]
    result = []
    for entry in entries:
        if entry.get("statuscode") != "200" or entry.get("mimetype") != "text/html":
            continue
        original = entry["original"]
        url = canonical(original)
        if f"/{year}/" not in urllib.parse.urlsplit(url).path and urllib.parse.urlsplit(url).path != "/":
            continue
        result.append({"archive_timestamp": entry["timestamp"], "archive_source_url": original, "url": url,
                       "archive_index_row": entry})
    return raw, result


def run(args):
    root = args.root.resolve()
    recovery = Recovery(root, args.stage if args.stage.is_absolute() else root / args.stage,
                        args.year, args.interval, args.retry_delay)
    selected = {}
    indexes = []
    for ordinal, (path, expected) in enumerate([(args.index, args.index_sha256), (args.home_index, args.home_index_sha256)], 1):
        if path is None:
            continue
        raw, items = index_items(path, expected, root, args.year)
        identity = recovery.retain(raw, f"index-{ordinal:02d}.json", "archive_index", original_input_path=str(path))
        indexes.append(identity)
        for item in items:
            is_home = urllib.parse.urlsplit(item["url"]).path == "/"
            key = (item["url"], item["archive_timestamp"] if is_home else "")
            item["index_record"] = identity
            if key not in selected or item["archive_timestamp"] < selected[key]["archive_timestamp"]:
                selected[key] = item
    for path in args.reuse_manifest:
        recovery.add_reuse(path)
    # Actual dated source locators first; this ordering does not assign dates.
    items = sorted(selected.values(), key=lambda item: (0 if re.search(r"/(?:outlook|opening)", item["url"]) else 1, item["url"], item["archive_timestamp"]))
    selection = {"year": args.year, "selection_policy": "Earliest explicit indexed revision per canonical non-home locator; every indexed home observation retained. Index/URL dates are locators, not source-date proof.", "indexes": indexes, "items": items}
    recovery.retain((json.dumps(selection, indent=2) + "\n").encode(), "selection.json", "archive_selection")
    posts = []
    print(json.dumps({"phase": "source_capture", "selected_locators": len(items), "stage": str(recovery.stage)}), flush=True)
    for ordinal, item in enumerate(items, 1):
        record, raw, attempts = recovery.fetch_source(item, ordinal)
        if record is None:
            post = {**item, "attempts": attempts, "capture_failed": True, "role": "capture_failure"}
        else:
            post = recovery.parse_post(item, record, raw, attempts)
        posts.append(post)
        source_post = recovery.stage / f"source-{ordinal:04d}.source-post.json"
        source_post.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n")
        with (recovery.stage / "progress.jsonl").open("a") as output:
            output.write(json.dumps({"ordinal": ordinal, "total": len(items), "url": item["url"], "title": post.get("title"), "role": post.get("role"), "date": post.get("session_date"), "status": record.get("http_status") if record else None}) + "\n")
        print(json.dumps({"source": ordinal, "total": len(items), "title": post.get("title"), "date": post.get("session_date"), "role": post.get("role")}), flush=True)
    document = {"source": "verniman", "crawl_id": recovery.stage.name,
                "requested_start_date": f"{args.year}-01-01", "anchor_session_date": f"{args.year}-12-31",
                "command": sys.argv, "source_capture_completed_at": now(), "posts": posts,
                "selection": recovery.identity(recovery.stage / "selection.json", "archive_selection"),
                "index_records": indexes, "attempts": recovery.attempts, "image_capture_status": "pending",
                "stop_reason": "bounded_source_page_capture_completed_images_pending", "traversal_reached_lower_boundary": False,
                "historical_full_year_completeness_claimed": False,
                "files": [recovery.identity(p) for p in sorted(recovery.stage.rglob("*")) if p.is_file()]}
    target = recovery.stage / "source-recovery-manifest.json"
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"source_pages_complete": True, "images_pending": True,
                      "manifest": recovery.identity(target), "roles": dict(Counter(p.get("role") for p in posts))}), flush=True)
    if not args.pages_only:
        complete_images(args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--year", type=int, default=2015)
    parser.add_argument("--index", type=Path)
    parser.add_argument("--index-sha256")
    parser.add_argument("--home-index", type=Path)
    parser.add_argument("--home-index-sha256")
    parser.add_argument("--reuse-manifest", type=Path, action="append", default=[])
    parser.add_argument("--interval", type=float, default=3.5)
    parser.add_argument("--retry-delay", type=float, default=20)
    parser.add_argument("--pages-only", action="store_true")
    parser.add_argument("--images-only", action="store_true")
    parser.add_argument("--supplement-posts", type=Path, action="append", default=[])
    parser.add_argument("--feed-manifest", type=Path, action="append", default=[])
    parser.add_argument("--review-selection", type=Path)
    parser.add_argument("--reviewed-output", type=Path)
    args = parser.parse_args()
    if args.year not in {2011, 2012, 2013, 2014, 2015}:
        parser.error("this source-recovery protocol supports explicit 2011, 2012, 2013, 2014 or 2015 scope")
    if args.review_selection:
        if args.reviewed_output is None:
            parser.error("--review-selection requires --reviewed-output")
        reviewed_collection(args)
    elif args.images_only:
        complete_images(args)
    else:
        if not args.index or not args.index_sha256:
            parser.error("page capture requires an explicitly pinned --index and --index-sha256")
        run(args)


if __name__ == "__main__":
    main()
