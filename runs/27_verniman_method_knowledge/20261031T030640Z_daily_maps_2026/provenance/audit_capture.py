#!/usr/bin/env python3
"""Independent offline capture audit; no network requests or source mutations.

Sitemap locators are discovery candidates, not proof of daily-map scope. A
boundary capture proves traversal only when its article date precedes the start.
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit


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
        if not self.skip and tag == "img":
            self.images.append(a.get("src") or a.get("data-src"))

    def handle_endtag(self, tag):
        if not self.depth:
            return
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

    for item in manifest.get("retained_inputs", []) + manifest.get("retained_source_verifications", []):
        payload(root, item, "retained-input")

    posts = manifest["posts"]
    successful = {canonical(p["url"]) for p in posts}
    identities = {(canonical(p["url"]), p.get("session_date")) for p in posts}
    start, end = manifest["start_date"], manifest["end_date"]
    image_missing, image_counts = [], Counter()
    duplicate_dates = Counter(p["session_date"] for p in posts if p.get("session_date"))
    for p in posts:
        raw = payload(stage, p["html"], p["url"])
        article = Article()
        article.feed(raw.decode("utf-8"))
        md = article.month_days()
        stamp = p.get("session_date")
        if article.found != 1:
            errors.append({"check": "one_article", "url": p["url"], "count": article.found})
        if stamp:
            d = date.fromisoformat(stamp)
            if not (start <= stamp <= end) or md != [(d.month, d.day)]:
                errors.append({"check": "body_date_correspondence", "url": p["url"], "assigned": stamp, "body_month_days": md})
        elif len(md) == 1:
            qualifications.append({"check": "unassigned_unambiguous_month_day", "url": p["url"], "body_month_days": md})
        records = p.get("images", [])
        image_counts["article_image_elements"] += len(article.images)
        image_counts["image_records"] += len(records)
        if len(records) != len(article.images):
            errors.append({"check": "all_article_images_recorded", "url": p["url"], "elements": len(article.images), "records": len(records)})
        for image in records:
            if image.get("path"):
                payload(stage, image, p["url"] + " image")
                image_counts["retained_image_occurrences"] += 1
                if image.get("rendition") == "inline_thumbnail":
                    image_counts["qualified_inline_fallbacks"] += 1
            else:
                image_missing.append({"post": p["url"], "url": image.get("requested_url") or image.get("url"), "error": image.get("error")})

    # Reconcile source/date identities, not merely navigation's seen set.
    prior_missing = []
    for record in manifest.get("retained_inputs", []):
        doc = json.loads(payload(root, record, "retained-manifest"))
        for p in doc.get("posts", []) + doc.get("source_dispositions", []):
            stamp = p.get("session_date")
            url = p.get("url") or p.get("source_url")
            if not url or not p.get("html") or (stamp and not start <= stamp <= end):
                continue
            if (canonical(url), stamp) not in identities:
                prior_missing.append({"url": url, "prior_session_date": stamp,
                                      "successful_current_url": canonical(url) in successful})
    if prior_missing:
        errors.append({"check": "retained_source_date_coverage", "missing": prior_missing})

    boundary = manifest.get("boundary_post")
    boundary_valid = False
    if boundary:
        raw = payload(stage, boundary["html"], "boundary")
        article = Article()
        article.feed(raw.decode("utf-8"))
        stamp = boundary.get("session_date")
        if stamp:
            d = date.fromisoformat(stamp)
            boundary_valid = stamp < start and article.month_days() == [(d.month, d.day)]
    if manifest.get("lower_boundary_reached") and not boundary_valid:
        errors.append({"check": "claimed_boundary_not_proven"})
    if not manifest.get("lower_boundary_reached"):
        qualifications.append({"check": "lower_boundary_not_reached", "stop_reason": manifest.get("stop_reason")})

    sitemap_urls = []
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    for record in manifest.get("sitemaps", []):
        if not record.get("path") or record.get("error"):
            continue
        tree = ET.fromstring(payload(stage, record, "sitemap"))
        if tree.tag == namespace + "urlset":
            sitemap_urls.extend(canonical(node.findtext(namespace + "loc")) for node in tree.findall(namespace + "url"))
    seed = canonical("https://verniman.blogspot.com/2009/10/ai-worries_0248886265.html")
    boundary_url = canonical(boundary["url"]) if boundary else None
    sitemap_range = {"seed_index": sitemap_urls.index(seed) if seed in sitemap_urls else None,
                     "boundary_index": sitemap_urls.index(boundary_url) if boundary_url in sitemap_urls else None,
                     "unresolved_locator_candidates": [],
                     "qualification": "Sitemap order supplies discovery candidates; old permalink dates do not establish session scope. Boundary is separate from in-scope posts."}
    first, last = sitemap_range["seed_index"], sitemap_range["boundary_index"]
    if first is not None and last is not None and first <= last:
        sitemap_range["unresolved_locator_candidates"] = [u for u in sitemap_urls[first:last] if u not in successful]
    return {"audit": "offline_capture_integrity_and_coverage", "passed": not errors,
            "checked_unique_files": len(checked), "posts": len(posts), "distinct_dated_days": len(duplicate_dates),
            "multiple_post_dates": {k: v for k, v in sorted(duplicate_dates.items()) if v > 1},
            "images": dict(image_counts), "unavailable_images": image_missing,
            "boundary_valid": boundary_valid, "sitemap_range": sitemap_range,
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
