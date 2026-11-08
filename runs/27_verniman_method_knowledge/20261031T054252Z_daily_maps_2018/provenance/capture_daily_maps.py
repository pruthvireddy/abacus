#!/usr/bin/env python3
"""Preserve a bounded Daily Map source traversal without changing data releases."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import http.client
import json
import mimetypes
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

HOST = "verniman.blogspot.com"
SEED = "https://verniman.blogspot.com/2009/10/ai-worries_0248886265.html"
OLD = "data/raw/blogspot/verniman/feed_discovery/20261020T235133Z_feed_b4114e98/collection_manifest.reviewed.json"
RECENT = "data/staging/verniman/20261030_seven_post_update/reviewed-update.json"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme not in {"http", "https"} or p.hostname != HOST:
        raise ValueError(f"non-source navigation: {url}")
    return urllib.parse.urlunsplit(("https", HOST, p.path, "", ""))


class Post(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.body_depth = None
        self.body_count = 0
        self.parts = []
        self.images = []
        self.older = None
        self.title = ""
        self.in_title = False
        self.md = None
        self.feed(raw)
        text = " ".join(self.parts)
        pairs = set(re.findall(r"\bOutlook\s+(\d{1,2})/(\d{1,2})\b", text, re.I))
        if len(pairs) == 1:
            self.md = tuple(map(int, next(iter(pairs))))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("id") == "Blog1_blog-pager-older-link":
            self.older = canonical(a["href"])
        if tag in {"h1", "h2", "h3"} and "post-title" in a.get("class", "").split():
            self.in_title = True
        if "post-body" in a.get("class", "").split():
            self.body_depth = len(self.stack)
            self.body_count += 1
        if self.body_depth is not None and tag == "img" and a.get("src"):
            anchor = next((v.get("href") for t, v in reversed(self.stack) if t == "a"), None)
            src = urllib.parse.urljoin("https://" + HOST, a["src"])
            linked = urllib.parse.urljoin("https://" + HOST, anchor) if anchor else None
            if linked and not re.search(r"(?:blogger\.googleusercontent\.com|bp\.blogspot\.com)/", linked):
                linked = None
            image = {"url": linked or src, "inline_url": src, "alt": a.get("alt", "")}
            if linked:
                linked_name = urllib.parse.unquote(urllib.parse.urlsplit(linked).path).rsplit("/", 1)[-1]
                inline_name = urllib.parse.unquote(urllib.parse.urlsplit(src).path).rsplit("/", 1)[-1]
                if linked_name and inline_name and linked_name != inline_name:
                    image["source_link_qualification"] = "Linked image filename differs from the actual inline source; preserve the inline rendition without guessing a replacement full-size URL."
            self.images.append(image)
        if tag not in VOID:
            self.stack.append((tag, a))

    def handle_endtag(self, tag):
        if tag in {"h1", "h2", "h3"}:
            self.in_title = False
        indexes = [i for i, (t, _) in enumerate(self.stack) if t == tag]
        if indexes:
            i = indexes[-1]
            if self.body_depth is not None and i <= self.body_depth:
                self.body_depth = None
            del self.stack[i:]

    def handle_data(self, data):
        if self.body_depth is not None:
            self.parts.append(data)
        if self.in_title:
            self.title += data


class Capture:
    def __init__(self, root, stage, start, end, *, seed=SEED, retained_manifests=None,
                 date_override_manifest=None):
        self.root, self.stage = root, stage
        self.start, self.end = start, end
        self.seed = canonical(seed)
        self.retained_manifests = [OLD, RECENT] if retained_manifests is None else retained_manifests
        self.number = 0
        self.retained = {}
        self.retained_revisions = []
        self.date_overrides = {}
        self.image_sources = {}
        self.saved_images = {}
        self.m = {"schema_version": "daily-map-capture-1", "run_id": stage.name,
                  "start_date": start.isoformat(), "end_date": end.isoformat(),
                  "seed_url": self.seed,
                  "capture_started_at": now(), "command": sys.argv,
                  "posts": [], "attempts": [], "traversal": [], "sitemaps": [],
                  "retained_inputs": [], "retained_source_verifications": [],
                  "date_policy": f"Article Outlook M/D, year anchored to {end.year}; URL and update dates are not session dates.",
                  "timing_policy": "Capture time does not establish historical availability.",
                  "gaps_policy": "No dated post observed is not proof that a post never existed."}
        if date_override_manifest is not None:
            self.load_date_overrides(date_override_manifest)
        stage.mkdir(parents=True, exist_ok=False)
        (stage / "captures").mkdir()
        (stage / "assets").mkdir()

    def store(self, raw, relative, **extra):
        path = self.stage / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != raw:
                raise ValueError(f"refusing changed object: {path}")
        else:
            path.write_bytes(raw)
        return {"path": relative, "sha256": digest(raw), "bytes": len(raw), **extra}

    def verify_retained(self, item):
        path = (self.root / item["path"]).resolve()
        path.relative_to(self.root)
        raw = path.read_bytes()
        if digest(raw) != item["sha256"] or ("bytes" in item and len(raw) != item["bytes"]):
            raise ValueError(f"retained input identity mismatch: {path}")
        self.m["retained_source_verifications"].append({"path": item["path"], "sha256": digest(raw), "bytes": len(raw)})
        return raw

    def load_date_overrides(self, manifest):
        """Accept only explicit, scope-pinned exceptions supported by verified bytes."""
        path = Path(manifest)
        path = (path if path.is_absolute() else self.root / path).resolve()
        relative = path.relative_to(self.root).as_posix()
        raw = path.read_bytes()
        record = {"path": relative, "sha256": digest(raw), "bytes": len(raw)}
        document = json.loads(raw)
        if (document.get("schema_version") != "daily-map-source-date-exceptions-1"
                or document.get("start_date") != self.start.isoformat()
                or document.get("end_date") != self.end.isoformat()):
            raise ValueError("source-date exception manifest schema or requested scope differs")

        def retain_input(item):
            value = self.verify_retained(item)
            identity = {"path": item["path"], "sha256": digest(value), "bytes": len(value)}
            if identity not in self.m["retained_inputs"]:
                self.m["retained_inputs"].append(identity)
            return value

        retain_input(record)
        for review in document.get("source_reviews", []):
            retain_input(review)
        rules = document.get("overrides")
        if not isinstance(rules, list) or not rules:
            raise ValueError("source-date exception manifest has no explicit rules")
        for rule in rules:
            url = canonical(rule["url"])
            if url in self.date_overrides:
                raise ValueError(f"duplicate source-date exception: {url}")
            stamp = rule.get("session_date")
            if stamp is not None:
                if not isinstance(stamp, str):
                    raise ValueError(f"invalid reviewed source date: {url}")
                date.fromisoformat(stamp)
            expected = rule.get("expected_body_month_day")
            if (not isinstance(expected, list) or len(expected) != 2
                    or any(type(value) is not int for value in expected)):
                raise ValueError(f"invalid expected Outlook month/day: {url}")
            date(2000, *expected)
            if (not isinstance(rule.get("reason"), str) or not rule["reason"].strip()
                    or not re.fullmatch(r"[0-9a-f]{64}", rule.get("body_text_sha256", ""))):
                raise ValueError(f"source-date exception lacks a reason or body identity: {url}")
            evidence = retain_input(rule["evidence"])
            parsed = Post(evidence.decode("utf-8", "replace"))
            self.validate_date_override(url, parsed, rule)
            self.date_overrides[url] = rule
        self.m["date_override_manifest"] = record
        self.m["source_date_exceptions"] = document
        self.m["date_policy"] += " Explicit reviewed exceptions apply only after exact body identity verification."

    @staticmethod
    def validate_date_override(url, parsed, rule):
        body_hash = digest(re.sub(r"\s+", "", "".join(parsed.parts)).encode())
        if (parsed.body_count != 1 or parsed.md != tuple(rule["expected_body_month_day"])
                or body_hash != rule["body_text_sha256"]):
            raise ValueError(f"source-date exception body identity mismatch: {url}")

    def load_retained(self):
        for loc in self.retained_manifests:
            raw = (self.root / loc).read_bytes()
            self.m["retained_inputs"].append({"path": loc, "sha256": digest(raw), "bytes": len(raw)})
            doc = json.loads(raw)
            for p in doc.get("posts", []) + doc.get("source_dispositions", []):
                url = p.get("url") or p.get("source_url")
                if url and p.get("html"):
                    url = canonical(url)
                    self.retained[url] = p
                    identity = (url, p.get("session_date"), p["html"].get("sha256"))
                    if not any((u, old.get("session_date"), old["html"].get("sha256")) == identity
                               for u, old in self.retained_revisions):
                        self.retained_revisions.append((url, p))
                for image in p.get("images", []):
                    self.image_sources[image["url"]] = image
            for item in doc.get("files", []) + doc.get("supplemental_images", []):
                url = item.get("url")
                if url and item.get("kind", "").startswith("image"):
                    self.image_sources[url] = item

    def fetch(self, url, kind="html"):
        p = urllib.parse.urlsplit(url)
        allowed = p.hostname == HOST or p.hostname == "blogger.googleusercontent.com" or bool(re.fullmatch(r"\d+\.bp\.blogspot\.com", p.hostname or ""))
        if p.scheme != "https" or not allowed:
            return {"url": url, "error": "source host outside archive scope"}, None
        self.number += 1
        began = now()
        raw = None
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "AbacusLocalSourceArchive/1.0", "Accept-Encoding": "identity"})
                with urllib.request.urlopen(req, timeout=20) as res:
                    raw = res.read()
                    status, headers, final = res.status, dict(res.headers), res.url
                error = None
                break
            except urllib.error.HTTPError as exc:
                raw = exc.read()
                status, headers, final = exc.code, dict(exc.headers), exc.url
                error = f"HTTP {exc.code}"
                break
            except (OSError, urllib.error.URLError, http.client.HTTPException, ValueError) as exc:
                status, headers, final, error = None, {}, url, f"{type(exc).__name__}: {exc}"
                if attempt == 0:
                    time.sleep(0.3)
        record = {"url": url, "final_url": final, "http_status": status,
                  "request_started_at": began, "captured_at": now(),
                  "content_type": headers.get("Content-Type", ""),
                  "last_modified": headers.get("Last-Modified"), "error": error}
        if raw is not None:
            if kind == "image" and not error:
                suffix = mimetypes.guess_extension(record["content_type"].split(";")[0]) or Path(p.path).suffix or ".bin"
                if suffix == ".jpe":
                    suffix = ".jpg"
                relative = "assets/" + digest(raw) + suffix
                record.update(self.store(raw, relative))
            else:
                relative = f"captures/request-{self.number:04d}.{kind}.gz"
                record.update(self.store(gzip.compress(raw, mtime=0), relative,
                                         uncompressed_sha256=digest(raw), uncompressed_bytes=len(raw)))
        self.m["attempts"].append(record)
        with (self.stage / "progress.jsonl").open("a") as out:
            out.write(json.dumps({"request": self.number, "kind": kind, "url": url,
                                  "status": status, "error": error}) + "\n")
        return record, raw if not error else None

    def image(self, image):
        requested = image["url"]
        qualification = image.get("source_link_qualification")
        full_error = qualification
        candidates = [image["inline_url"]] if qualification else [requested, image["inline_url"]]
        for url in dict.fromkeys(candidates):
            if url in self.saved_images:
                result = {**self.saved_images[url]}
            elif url in self.image_sources:
                item = self.image_sources[url]
                raw = self.verify_retained(item)
                suffix = Path(item["path"]).suffix
                result = self.store(raw, "assets/" + digest(raw) + suffix,
                                    url=url, captured_at=item.get("captured_at"),
                                    content_type=item.get("headers", {}).get("Content-Type", "image/" + suffix.lstrip(".")),
                                    capture_kind="retained", source_path=item["path"])
                self.saved_images[url] = result
            else:
                result, raw = self.fetch(url, "image")
                if raw is not None:
                    self.saved_images[url] = result
            if result.get("path") and not result.get("error"):
                return {**image, **result, "requested_url": requested,
                        "rendition": "linked_full_image" if url == requested else "inline_thumbnail",
                        "full_size_error": None if url == requested else full_error}
            full_error = result.get("error")
        return {**image, "error": full_error or "image unavailable"}

    def post(self, url, previous, *, kind="live", retained=None, retention_reason=None):
        if kind == "live":
            record, raw = self.fetch(url + "?m=0")
            if raw is None:
                return None
        else:
            raw = self.verify_retained(retained["html"])
            record = self.store(gzip.compress(raw, mtime=0), "captures/retained-" + digest(raw)[:20] + ".html.gz",
                                uncompressed_sha256=digest(raw), uncompressed_bytes=len(raw),
                                source_path=retained["html"]["path"], captured_at=retained["html"].get("captured_at"))
        parsed = Post(raw.decode("utf-8", "replace"))
        if parsed.body_count != 1:
            self.m["attempts"].append({"url": url, "error": f"expected one article body, observed {parsed.body_count}"})
            return None
        assigned = None
        warnings = []
        if parsed.md:
            month, day = parsed.md
            year = previous.year - 1 if previous.month <= 2 and month >= 11 else previous.year
            try:
                assigned = date(year, month, day)
                if assigned > previous:
                    warnings.append("nonmonotonic_body_date_preserved")
            except ValueError:
                warnings.append("invalid_body_date")
        else:
            warnings.append("no_unambiguous_outlook_date")
        date_method = "body_outlook_month_day_with_anchored_year" if assigned else "undated_commentary"
        if kind == "retained" and "session_date" in retained:
            stamp = retained["session_date"]
            assigned = date.fromisoformat(stamp) if stamp else None
            date_method = "hash_verified_retained_manifest_session_date" if assigned else "retained_undated_commentary"
            if assigned and parsed.md != (assigned.month, assigned.day):
                warnings.append("retained_manifest_body_date_differs")
        override = self.date_overrides.get(canonical(url))
        if override is not None:
            self.validate_date_override(url, parsed, override)
            assigned = date.fromisoformat(override["session_date"]) if override["session_date"] else None
            date_method = "explicit_reviewed_source_date_exception"
            warnings = [override["reason"]]
        row = {"url": url, "session_date": assigned.isoformat() if assigned else None,
               "title": parsed.title.strip(), "html": record, "captured_at": record.get("captured_at"),
               "date_warnings": warnings, "date_method": date_method,
               "older_url": parsed.older, "capture_kind": kind,
               "source_capture_at": record.get("captured_at"), "images": [self.image(i) for i in parsed.images]}
        if override is not None:
            row["source_date_override"] = override
        if retained:
            row["retained_manifest_date"] = retained.get("session_date")
            if kind == "retained":
                row["live_status"] = retention_reason or "unavailable_at_archive_capture; recovered exact historical revision"
        self.m["posts"].append(row)
        print(json.dumps({"post": len(self.m["posts"]), "date": row["session_date"],
                          "kind": kind, "images": len(row["images"]), "url": url}), flush=True)
        return row

    def run(self):
        self.load_retained()
        rec, raw = self.fetch("https://" + HOST + "/sitemap.xml", "xml")
        self.m["sitemaps"].append(rec)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        sitemap_urls = []
        if raw:
            index = ET.fromstring(raw)
            for item in index.findall("s:sitemap", ns):
                url = item.findtext("s:loc", namespaces=ns)
                rec, page = self.fetch(url, "xml")
                self.m["sitemaps"].append(rec)
                if page:
                    sitemap_urls += [canonical(x.findtext("s:loc", namespaces=ns)) for x in ET.fromstring(page)]
        self.m["sitemap_url_count"] = len(sitemap_urls)
        url, previous, seen = self.seed, self.end, set()
        for _ in range(400):
            if url in seen:
                self.m["stop_reason"] = "navigation_cycle"
                break
            seen.add(url)
            row = self.post(url, previous)
            method = "explicit_older_post_link"
            if not row:
                old = self.retained.get(url)
                if old:
                    row = self.post(url, previous, kind="retained", retained=old)
                    method = "older_link_from_verified_retained_capture"
            if row:
                assigned = date.fromisoformat(row["session_date"]) if row["session_date"] else None
                if assigned and assigned < self.start:
                    self.m["boundary_post"] = {"url": url, "session_date": row["session_date"], "html": row["html"]}
                    self.m["stop_reason"] = "crossed_before_requested_start"
                    break
                if assigned:
                    previous = assigned
                next_url = row["older_url"]
            else:
                next_url, method = None, None
            if not next_url or next_url in seen:
                if url in sitemap_urls and sitemap_urls.index(url) + 1 < len(sitemap_urls):
                    next_url = sitemap_urls[sitemap_urls.index(url) + 1]
                    method = "next_official_sitemap_locator_after_navigation_gap"
            self.m["traversal"].append({"from": url, "to": next_url, "method": method})
            if not next_url:
                self.m["stop_reason"] = "navigation_exhausted"
                break
            url = next_url
        else:
            self.m["stop_reason"] = "safety_limit_400_posts"

        # Check the observed sitemap range even when Older Post links skip a locator.
        # Sitemap publication dates alone never establish the requested body-date scope.
        boundary_url = self.m.get("boundary_post", {}).get("url")
        if self.seed in sitemap_urls and boundary_url in sitemap_urls:
            first, last = sitemap_urls.index(self.seed), sitemap_urls.index(boundary_url)
            if first <= last:
                context = self.end
                for candidate in dict.fromkeys(sitemap_urls[first:last]):
                    rows = [p for p in self.m["posts"] if p["url"] == candidate]
                    if not rows:
                        row = self.post(candidate, context)
                        if row:
                            row["discovery"] = "supplemental_official_sitemap_seed_to_boundary_range"
                            rows = [row]
                    if rows and rows[0]["session_date"]:
                        context = date.fromisoformat(rows[0]["session_date"])

        # Reconcile successfully represented source/date identities, not attempted URLs.
        # The same permalink may now contain a map for another date.
        for url, old in self.retained_revisions:
            stamp = (self.date_overrides[url]["session_date"]
                     if url in self.date_overrides else old.get("session_date"))
            if stamp and not (self.start.isoformat() <= stamp <= self.end.isoformat()):
                continue
            rows = [p for p in self.m["posts"] if p["url"] == url]
            if any(p["session_date"] == stamp for p in rows):
                continue
            context = date.fromisoformat(stamp) if stamp else self.end
            if not rows:
                row = self.post(url, context)
                if row:
                    row["discovery"] = "supplemental_hash_pinned_prior_capture_manifest"
                    rows = [row]
            if any(p["session_date"] == stamp for p in rows):
                continue
            reason = ("live_revision_has_different_body_date; recovered exact historical revision"
                      if any(p["capture_kind"] == "live" for p in rows) else None)
            row = self.post(url, context, kind="retained", retained=old, retention_reason=reason)
            if row:
                row["discovery"] = "supplemental_hash_pinned_prior_capture_manifest"
        # User-known missing locators are attempts, never synthesized content.
        missing = []
        if RECENT in self.retained_manifests and self.start.year <= 2026 <= self.end.year:
            recent = json.loads((self.root / RECENT).read_text())
            missing = [p["source_url"] for p in recent["source_dispositions"] if not p.get("html")]
            missing.append("https://verniman.blogspot.com/2009/10/spcx-surprise.html")
        for url in missing:
            if not any(p["url"] == url for p in self.m["posts"]):
                row = self.post(url, self.end)
                if row:
                    row["discovery"] = "explicit_previously_reported_locator"
        self.m["posts"] = [p for p in self.m["posts"] if not p["session_date"] or self.start.isoformat() <= p["session_date"] <= self.end.isoformat()]
        self.m["capture_completed_at"] = now()
        self.m["lower_boundary_reached"] = self.m.get("stop_reason") == "crossed_before_requested_start"
        (self.stage / "capture-manifest.json").write_text(json.dumps(self.m, indent=2) + "\n")
        print(json.dumps({"complete": True, "posts": len(self.m["posts"]), "stop_reason": self.m.get("stop_reason"), "attempts": len(self.m["attempts"])}), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument("--start", type=date.fromisoformat, default=date(2026, 1, 1))
    p.add_argument("--end", type=date.fromisoformat, default=date(2026, 10, 30))
    p.add_argument("--seed", default=SEED, help="Explicit observed latest post URL for the requested range")
    p.add_argument("--retained-manifest", action="append", help="Explicit workspace-relative source manifest; repeated values override the default 2026 inputs")
    p.add_argument("--date-override-manifest", help="Explicit scope-pinned source-date exception input with verified body identities")
    a = p.parse_args()
    if a.start > a.end:
        p.error("start must not follow end")
    Capture(a.root.resolve(), a.stage.resolve(), a.start, a.end,
            seed=a.seed, retained_manifests=a.retained_manifest,
            date_override_manifest=a.date_override_manifest).run()


if __name__ == "__main__":
    main()
