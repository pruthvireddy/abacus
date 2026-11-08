#!/usr/bin/env python3
"""Adapt explicitly pinned historical captures into a fresh private Daily Map stage.

No network requests are made. Archived HTML remains byte exact. Atom entries
receive derived entry-only HTML while the complete original XML is retained.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
ATOM = {"a": "http://www.w3.org/2005/Atom"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
FORMATS = {"archived_html", "archived_page_post", "archived_atom_feed"}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text_identity(value: str) -> str:
    return re.sub(r"\s+", "", value)


def canonical(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or parts.hostname != "verniman.blogspot.com":
        raise ValueError(f"not an original Verniman permalink: {value}")
    return urlunsplit(("https", parts.hostname, parts.path, "", ""))


class Article(HTMLParser):
    """Read the one actual article body and its ordered image elements."""

    def __init__(self, raw: str, base: str):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.stack = []
        self.depth = None
        self.body_count = 0
        self.parts = []
        self.images = []
        self.title_parts = []
        self.post_ids = []
        self.in_title = False
        self.feed(raw)

    @property
    def title(self):
        return " ".join("".join(self.title_parts).split())

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and re.fullmatch(r"\d+", values.get("name") or ""):
            self.post_ids.append(values["name"])
        if tag in {"h1", "h2", "h3"} and "post-title" in values.get("class", "").split():
            self.in_title = True
        if "post-body" in values.get("class", "").split():
            self.depth = len(self.stack)
            self.body_count += 1
        if self.depth is not None and tag == "img":
            source = values.get("src") or values.get("data-src")
            if not source:
                raise ValueError("source image element has no retained source URL")
            inline = urljoin(self.base, source)
            anchor = next((a.get("href") for t, a in reversed(self.stack) if t == "a"), None)
            linked = urljoin(self.base, anchor) if anchor else None
            if linked and not re.search(r"(?:blogger\.googleusercontent\.com|bp\.blogspot\.com)/", linked):
                linked = None
            self.images.append({"url": linked or inline, "inline_url": inline, "alt": values.get("alt", "")})
        if tag not in VOID:
            self.stack.append((tag, values))

    def handle_endtag(self, tag):
        if tag in {"h1", "h2", "h3"}:
            self.in_title = False
        indexes = [i for i, (t, _) in enumerate(self.stack) if t == tag]
        if indexes:
            index = indexes[-1]
            if self.depth is not None and index <= self.depth:
                self.depth = None
            del self.stack[index:]

    def handle_data(self, value):
        if self.depth is not None:
            self.parts.append(value)
        if self.in_title:
            self.title_parts.append(value)


class Adapter:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.verified = {}

    def record(self, path: Path) -> dict:
        raw = path.read_bytes()
        return {"path": path.relative_to(self.root).as_posix(), "bytes": len(raw), "sha256": digest(raw)}

    def verify(self, record: dict) -> bytes:
        path = (self.root / record["path"]).resolve()
        path.relative_to(self.root)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"retained record is not a regular local file: {path}")
        raw = path.read_bytes()
        if len(raw) != record["bytes"] or digest(raw) != record["sha256"]:
            raise ValueError(f"retained input identity mismatch: {path}")
        identity = {"path": record["path"], "bytes": len(raw), "sha256": digest(raw)}
        previous = self.verified.get(record["path"])
        if previous and previous != identity:
            raise ValueError(f"conflicting retained identities: {path}")
        self.verified[record["path"]] = identity
        return raw

    def atom_entry(self, post: dict) -> tuple[bytes, bytes]:
        raw = self.verify(post["atom"])
        if post["atom"].get("body_truncated") is True:
            raise ValueError("archived Atom response was truncated")
        tree = ET.fromstring(raw)
        entries = tree.findall("a:entry", ATOM)
        selector = post.get("source_entry_selector")
        if not isinstance(selector, str) or not selector:
            raise ValueError("archived Atom entry lacks an exact selector")
        matches = [(i, entry) for i, entry in enumerate(entries, 1)
                   if entry.findtext("a:id", namespaces=ATOM) == selector]
        if len(matches) != 1:
            raise ValueError(f"archived Atom selector is absent or duplicated: {selector}")
        ordinal, entry = matches[0]
        if ordinal != post.get("source_feed_entry_ordinal"):
            raise ValueError(f"archived Atom entry ordinal differs: {selector}")
        if post.get("source_entry_id") != selector:
            raise ValueError(f"archived Atom source entry identity differs: {selector}")
        title = entry.findtext("a:title", namespaces=ATOM)
        content = entry.find("a:content", ATOM)
        if content is None or content.get("type") != "html" or list(content):
            raise ValueError(f"unsupported archived Atom content representation: {selector}")
        body = content.text or ""
        if title != post.get("title") or body != post.get("body_html"):
            raise ValueError(f"archived Atom selected title/content changed: {selector}")
        links = [link.get("href") for link in entry.findall("a:link", ATOM) if link.get("rel") == "alternate"]
        if len(links) != 1 or canonical(links[0]) != canonical(post["url"]):
            raise ValueError(f"archived Atom alternate permalink differs: {selector}")
        self.verify(post["entry_record"])
        derived = ('<!doctype html><html><head><meta charset="utf-8"></head><body>'
                   '<h3 class="post-title">' + html.escape(title) + '</h3><div class="post-body">' + body + '</div></body></html>')
        return derived.encode(), raw

    def prepare(self, manifest: Path, start: date, end: date, expected_sha256: str | None) -> tuple[dict, list]:
        manifest = manifest.resolve()
        identity = self.record(manifest)
        raw = self.verify(identity)
        if expected_sha256 and digest(raw) != expected_sha256:
            raise ValueError("retained collection manifest does not match the explicit hash pin")
        document = json.loads(raw)
        if (document.get("requested_start_date") != start.isoformat()
                or document.get("anchor_session_date") != end.isoformat() or start.year != end.year):
            raise ValueError("retained collection scope differs from requested annual scope")
        for key in ["chronology_review", "collection_completion_review", "archive_capture_manifest"]:
            self.verify(document[key])
        if document.get("collection_review"):
            self.verify(document["collection_review"])
        for record in document.get("files", []):
            self.verify(record)
        posts = document.get("posts")
        if not isinstance(posts, list) or not posts:
            raise ValueError("retained collection has no selected posts")
        prepared = []
        for post in posts:
            stamp = date.fromisoformat(post["session_date"])
            if not start <= stamp <= end:
                raise ValueError(f"source date is outside requested scope: {stamp}")
            title_dates = set(re.findall(r"\bOutlook\s+(\d{1,2})/(\d{1,2})\b", post["title"], re.I))
            if len(title_dates) != 1 or tuple(map(int, next(iter(title_dates)))) != (stamp.month, stamp.day):
                raise ValueError(f"reviewed source title does not support its date: {post['url']}")
            if post.get("year_evidence", {}).get("year") != stamp.year:
                raise ValueError(f"reviewed source year evidence differs: {post['url']}")
            canonical(post["url"])
            fmt = post.get("source_format")
            if fmt not in FORMATS:
                raise ValueError(f"unsupported retained source format: {fmt}")
            original = None
            if fmt == "archived_atom_feed":
                if post.get("html") is not None:
                    raise ValueError("archived Atom source unexpectedly declares original HTML")
                source, original = self.atom_entry(post)
            else:
                source = self.verify(post["html"])
                if post["html"].get("body_truncated") is True:
                    raise ValueError("archived HTML response was truncated")
                self.verify(post["post_record"])
            article = Article(source.decode("utf-8"), post["url"])
            if article.body_count != 1 or article.title != post["title"]:
                raise ValueError(f"retained source article selector/title differs: {post['url']}")
            if fmt != "archived_atom_feed":
                if str(post.get("source_post_id")) not in article.post_ids:
                    raise ValueError(f"archived HTML post identity differs: {post['url']}")
                if fmt == "archived_page_post" and post.get("source_entry_selector") != str(post.get("source_post_id")):
                    raise ValueError(f"archived page selector differs from source post identity: {post['url']}")
            retained_images = post.get("images", [])
            if len(article.images) != len(retained_images):
                raise ValueError(f"actual image elements differ from retained records: {post['url']}")
            image_payloads = []
            for element, record in zip(article.images, retained_images):
                if element["url"] != record.get("url") or element["url"] != record.get("original_image_url"):
                    raise ValueError(f"ordered source image identity differs: {post['url']}")
                if (record.get("kind") != "current_source_image_fallback"
                        or record.get("source_revision_status") != "current_image_response_historical_bytes_unverified"
                        or record.get("historical_digest_match_verified") is not False):
                    raise ValueError(f"unsupported or unqualified historical image provenance: {post['url']}")
                payload = self.verify(record)
                if record.get("body_truncated") is True:
                    raise ValueError(f"retained image response was truncated: {post['url']}")
                content_type = record.get("headers", {}).get("Content-Type", "").split(";")[0]
                if content_type not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
                    raise ValueError(f"unsupported retained image content type: {content_type}")
                image_payloads.append((element, record, payload, content_type))
            prepared.append((post, source, original, image_payloads))
        prepared.sort(key=lambda item: (item[0]["session_date"], item[0]["url"]), reverse=True)
        return {"document": document, "identity": identity}, prepared


def store(stage: Path, raw: bytes, relative: str, **metadata) -> dict:
    path = stage / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError(f"refusing changed content object: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(raw)
    return {"path": relative, "bytes": len(raw), "sha256": digest(raw), **metadata}


def compressed(stage: Path, raw: bytes, relative: str, **metadata) -> dict:
    return store(stage, gzip.compress(raw, compresslevel=9, mtime=0), relative,
                 uncompressed_bytes=len(raw), uncompressed_sha256=digest(raw), **metadata)


def adapt(root: Path, stage: Path, manifest: Path, start: date, end: date,
          expected_manifest_sha256: str | None = None, command: list[str] | None = None) -> dict:
    root, stage = root.resolve(), stage.resolve()
    if stage.exists() or stage.is_symlink():
        raise FileExistsError(f"refusing an existing stage: {stage}")
    adapter = Adapter(root)
    collection, prepared = adapter.prepare(manifest, start, end, expected_manifest_sha256)
    document = collection["document"]
    # All source identities and selected-entry semantics pass before any output.
    stage.mkdir(parents=True)
    (stage / "captures").mkdir()
    (stage / "assets").mkdir()
    result = {"schema_version": "daily-map-capture-1", "run_id": stage.name,
              "start_date": start.isoformat(), "end_date": end.isoformat(),
              "seed_url": prepared[0][0]["url"], "capture_started_at": now(),
              "command": command if command is not None else sys.argv,
              "capture_method": "hash_verified_retained_archival_collection",
              "posts": [], "attempts": [], "sitemaps": [],
              "traversal": document.get("traversal", []),
              "retained_inputs": [collection["identity"]],
              "retained_source_verifications": list(adapter.verified.values()),
              "source_collection_stop_reason": document.get("stop_reason"),
              "source_archive_capture_manifest": document["archive_capture_manifest"],
              "source_completion_review": document["collection_completion_review"],
              "stop_reason": "retained_archive_observed_coverage_only", "lower_boundary_reached": False,
              "observed_archive_coverage_only": True, "historical_full_year_completeness_claimed": False,
              "date_policy": "Selected source-title Outlook M/D plus independently reviewed archived year; no permalink-date inference.",
              "timing_policy": "Archive observation, original source claims and retained capture clocks are distinct; historical availability is unverified.",
              "gaps_policy": "No surviving selected source is not proof that no historical post existed.",
              "archive_notice": "Recovered from retained archived pages and exact historical feed entries. Coverage has gaps and does not establish a complete historical year. Images are retained current-source fallbacks whose historical bytes have not been verified."}
    ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}
    for ordinal, (old, source, original, image_payloads) in enumerate(prepared, 1):
        fmt = old["source_format"]
        is_derived = fmt == "archived_atom_feed"
        source_record = old["atom"] if is_derived else old["html"]
        year_evidence = {key: value for key, value in old["year_evidence"].items()
                         if key != "source_context_excerpt"}
        if "source_context_excerpt" in old["year_evidence"]:
            excerpt = old["year_evidence"]["source_context_excerpt"].encode()
            year_evidence["source_context_excerpt_identity"] = {
                "sha256": digest(excerpt), "utf8_bytes": len(excerpt),
                "retained_in_source_manifest": collection["identity"],
                "source_post_id": old.get("source_post_id")}
        html_record = compressed(stage, source, f"captures/source-{ordinal:04d}.html.gz",
                                 captured_at=source_record.get("captured_at") or old.get("captured_at"),
                                 source_path=source_record["path"], derived_source=is_derived,
                                 source_format=fmt)
        images = []
        for element, record, payload, content_type in image_payloads:
            image = store(stage, payload, "assets/" + digest(payload) + ext[content_type], **element,
                          requested_url=element["url"], content_type=content_type,
                          captured_at=record.get("captured_at"), capture_kind="retained",
                          source_path=record["path"], original_image_record=record,
                          rendition="linked_full_image", source_revision_status=record["source_revision_status"],
                          historical_digest_match_verified=False,
                          image_revision_qualification=old.get("image_revision_qualification"))
            images.append(image)
        row = {"url": old["url"], "title": old["title"], "session_date": old["session_date"],
               "html": html_record, "captured_at": old.get("captured_at"),
               "capture_kind": "retained", "source_capture_at": source_record.get("captured_at") or old.get("captured_at"),
               "date_method": old["session_date_method"],
               "date_warnings": [*old.get("date_warnings", []), "Retained archival source date uses selected title and independently reviewed year; capture time does not establish historical availability."],
               "older_url": next((link.get("href") for link in old.get("navigation_links") or []
                                  if link.get("id") == "Blog1_blog-pager-older-link"), None),
               "images": images, "source_format": fmt, "derived_source": is_derived,
               "archive_url": old.get("archive_url"), "archive_observed_at": old.get("archive_observed_at"),
               "source_entry_selector": old.get("source_entry_selector"),
               "source_feed_entry_ordinal": old.get("source_feed_entry_ordinal"),
               "source_entry_id": old.get("source_entry_id"), "source_post_id": old.get("source_post_id"),
               "source_title": old["title"], "session_date_source_text": old.get("session_date_source_text"),
               "year_evidence": year_evidence,
               "image_revision_qualification": old.get("image_revision_qualification"),
               "source_provenance": {"collection_manifest": collection["identity"], "ledger_id": old.get("ledger_id"),
                                     "original_source_record": source_record, "post_record": old.get("post_record"),
                                     "entry_record": old.get("entry_record"), "index_record": old.get("index_record"),
                                     "source_format": fmt, "navigation_links": old.get("navigation_links")}}
        if original is not None:
            row["original_source"] = compressed(stage, original, f"captures/original-{digest(original)}.xml.gz",
                                                 captured_at=source_record.get("captured_at"),
                                                 source_path=source_record["path"], content_type="application/atom+xml",
                                                 source_entry_selector=old["source_entry_selector"],
                                                 source_feed_entry_ordinal=old["source_feed_entry_ordinal"])
        result["posts"].append(row)
    result["capture_completed_at"] = now()
    (stage / "capture-manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return {"status": "passed", "stage": str(stage), "posts": len(result["posts"]),
            "source_formats": dict(Counter(post["source_format"] for post in result["posts"])),
            "image_references": sum(len(post["images"]) for post in result["posts"]),
            "unique_image_files": len({image["sha256"] for post in result["posts"] for image in post["images"]}),
            "verified_retained_files": len(adapter.verified), "network_requests": 0,
            "historical_full_year_completeness_claimed": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--retained-manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--expected-manifest-sha256")
    args = parser.parse_args()
    root = args.root.resolve()
    stage = args.stage if args.stage.is_absolute() else root / args.stage
    manifest = args.retained_manifest if args.retained_manifest.is_absolute() else root / args.retained_manifest
    result = adapt(root, stage, manifest, args.start, args.end, args.expected_manifest_sha256)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
