"""Follow explicit Older Post links and retain a chronological capture ledger.

The crawl anchors the outlook year to the requested current-year session. Body
month/day text is preserved, including duplicates and apparent source typos.
Only a clear January-to-December transition decrements the inferred year.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .paths import resolve_publication_root
from .provenance import git_version, sha256_file
from .publication_safety import check_absent, check_path, write_new_bytes
from .verniman_capture import _PostLinks, _fetch, _now
from .verniman_levels import content_text


class OlderLink(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("id") == "Blog1_blog-pager-older-link":
            self.urls.append(canonical_url(attrs.get("href", "")))


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "verniman.blogspot.com"
            or not parts.path.endswith(".html")):
        raise ValueError(f"unexpected older-post URL: {url}")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def page_identity(html: str) -> tuple[str | None, str | None, list[str], tuple[int, int] | None]:
    links = _PostLinks()
    links.feed(html)
    older = OlderLink()
    older.feed(html)
    if len(older.urls) > 1:
        raise ValueError("multiple Older Post links")
    visible = content_text(html, post_only=True)
    matches = re.findall(r"\bOutlook\s+(\d{1,2})/(\d{1,2})\b", visible, flags=re.IGNORECASE)
    month_day = tuple(map(int, matches[0])) if len(set(matches)) == 1 else None
    return links.post_id, older.urls[0] if older.urls else None, links.images, month_day


def infer_date(month_day: tuple[int, int] | None, previous: date) -> tuple[date | None, list[str]]:
    if month_day is None:
        return None, ["no_unambiguous_outlook_month_day"]
    month, day = month_day
    year = previous.year - 1 if previous.month <= 2 and month >= 11 else previous.year
    result = date(year, month, day)
    warnings = []
    if result > previous:
        warnings.append("nonmonotonic_body_outlook_date_preserved")
    if result == previous:
        warnings.append("duplicate_body_outlook_date_preserved")
    return result, warnings


def _record(path: Path, root: Path, **extra) -> dict:
    return {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size,
            "sha256": sha256_file(path), **extra}


def _retry_fetch(url: str, path: Path, root: Path, kind: str) -> dict:
    for attempt in range(3):
        try:
            return _fetch(url, path, root, kind)
        except Exception:
            # A partial disk artifact is evidence, not permission to replace it.
            if attempt == 2 or path.exists() or path.with_name(path.name + ".part").exists():
                raise
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError("unreachable fetch retry")


def _coverage(start: date, anchor: date, posts: list[dict], complete: bool) -> list[dict]:
    by_day: dict[str, list[str]] = {}
    for post in posts:
        stamp = post.get("session_date")
        if stamp and start.isoformat() <= stamp <= anchor.isoformat():
            by_day.setdefault(stamp, []).append(post["url"])
    rows = []
    cursor = start
    while cursor <= anchor:
        urls = by_day.get(cursor.isoformat(), [])
        if urls:
            status = "post_captured"
            reason = "One or more captured posts state this outlook month/day; date is not publication timing."
        elif complete:
            status = "weekend_no_dated_post" if cursor.weekday() >= 5 else "weekday_no_dated_post"
            reason = "No captured post explicitly states this date; holidays and ambiguous source dates are not inferred."
        else:
            status = "not_fully_traversed"
            reason = "Traversal stopped before establishing the requested lower boundary; absence is not established."
        rows.append({"session_date": cursor.isoformat(), "status": status,
                     "post_urls": urls, "reason": reason})
        cursor += timedelta(days=1)
    return rows


def crawl(root: Path, seed_manifest: Path, *, start: date, anchor: date, max_posts: int = 500) -> Path:
    root = root.resolve()
    if start > anchor:
        raise ValueError("start must not exceed anchor")
    seed_manifest = check_path(seed_manifest if seed_manifest.is_absolute() else root / seed_manifest, root)
    seed = json.loads(seed_manifest.read_text())
    if seed.get("source") != "verniman" or not seed.get("posts"):
        raise ValueError("expected an existing verniman capture batch")
    crawl_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_history_" + uuid.uuid4().hex[:8]
    batch = root / "data/raw/blogspot/verniman/html" / crawl_id
    check_absent(batch, root)
    batch.mkdir(parents=True)
    files: dict[str, dict] = {}
    for item in seed["files"]:
        path = check_path(root / item["path"], root)
        if not path.is_file() or sha256_file(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise ValueError(f"seed capture identity mismatch: {path}")
        files[item["path"]] = item
    seed_record = _record(seed_manifest, root, kind="seed_manifest")
    files[seed_record["path"]] = seed_record
    manifest = {"source": "verniman", "crawl_id": crawl_id, "batch_id": crawl_id,
                "requested_start_date": start.isoformat(), "anchor_session_date": anchor.isoformat(),
                "capture_started_at": _now(), "command": sys.argv, "code_state": git_version(root),
                "seed_manifests": [seed_record], "posts": [], "traversal": [], "files": [],
                "date_policy": "Body Outlook month/day; year anchored to the requested session and decremented only at a clear January-to-December traversal boundary. Duplicates are preserved.",
                "timing_policy": "Source-claimed metadata and capture time do not verify historical plan availability."}
    seen_urls: set[str] = set()
    previous = anchor
    next_url: str | None = None
    progress = batch / "progress.jsonl"

    def append(post: dict, *, reused: bool) -> None:
        nonlocal previous, next_url
        html = (root / post["html"]["path"]).read_text(encoding="utf-8")
        post_id, older, _, month_day = page_identity(html)
        assigned, warnings = infer_date(month_day, previous)
        if assigned is not None:
            previous = assigned
        url = canonical_url(post["url"])
        if url in seen_urls:
            raise ValueError(f"navigation cycle at {url}")
        seen_urls.add(url)
        row = {**post, "url": url, "source_post_id": post_id,
               "session_date": assigned.isoformat() if assigned else None,
               "session_date_method": "body_month_day_with_descending_chronology_anchored_year",
               "session_date_source_text": f"Outlook {month_day[0]:02d}/{month_day[1]:02d}" if month_day else None,
               "date_warnings": warnings, "ledger_id": f"post-{len(manifest['posts']) + 1:04d}",
               "older_url": older, "reused_capture": reused}
        manifest["posts"].append(row)
        ledger = {"ledger_id": row["ledger_id"], "kind": "post", "source_url": url,
                  "session_date": row["session_date"], "status": "captured" if post.get("atom") else "captured_html_atom_unavailable",
                  "reason": "; ".join(warnings), "older_url": older, "reused_capture": reused}
        manifest["traversal"].append(ledger)
        with progress.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(ledger) + "\n")
        print(json.dumps(ledger), flush=True)
        next_url = older

    # Existing, hash-pinned ten-session captures are inputs, never rewritten.
    for post in seed["posts"]:
        append(post, reused=True)
    stop_reason = "unknown"
    try:
        while next_url and len(manifest["posts"]) < max_posts:
            if next_url in seen_urls:
                stop_reason = "navigation_cycle"
                break
            number = len(manifest["posts"]) + 1
            url = next_url
            html_record = _retry_fetch(url + "?m=0", batch / f"post-{number:04d}.html", root, "html")
            files[html_record["path"]] = html_record
            html = (root / html_record["path"]).read_text(encoding="utf-8")
            post_id, older, image_urls, month_day = page_identity(html)
            atom_record = None
            errors = []
            if post_id:
                try:
                    atom_record = _retry_fetch("https://verniman.blogspot.com/feeds/posts/default/" + post_id,
                                               batch / f"post-{number:04d}.atom", root, "atom")
                    files[atom_record["path"]] = atom_record
                except Exception as exc:
                    errors.append(f"atom: {type(exc).__name__}: {exc}")
            else:
                errors.append("no_unambiguous_blogger_post_id")
            images = []
            for image_index, image_url in enumerate(image_urls, 1):
                try:
                    suffix = Path(urlsplit(image_url).path).suffix.lower()
                    image_record = _retry_fetch(image_url, batch / "images" / f"post-{number:04d}-{image_index:02d}{suffix}", root, "image")
                    images.append(image_record)
                    files[image_record["path"]] = image_record
                except Exception as exc:
                    errors.append(f"image {image_url}: {type(exc).__name__}: {exc}")
            post = {"url": url, "captured_at": html_record["captured_at"], "html": html_record,
                    "atom": atom_record, "images": images, "capture_errors": errors}
            append(post, reused=False)
            assigned = manifest["posts"][-1]["session_date"]
            if assigned and date.fromisoformat(assigned) < start:
                stop_reason = "reached_post_before_requested_start"
                break
            time.sleep(0.1)
        else:
            stop_reason = "navigation_exhausted" if not next_url else "max_posts_reached"
    except Exception as exc:
        stop_reason = "capture_error"
        failure = {"ledger_id": f"failure-{len(manifest['traversal']) + 1:04d}", "kind": "fetch_failure",
                   "source_url": next_url, "session_date": None, "status": "failed",
                   "reason": f"{type(exc).__name__}: {exc}"}
        manifest["traversal"].append(failure)
        print(json.dumps(failure), flush=True)
    complete = stop_reason == "reached_post_before_requested_start"
    manifest.update({"capture_completed_at": _now(), "stop_reason": stop_reason,
                     "traversal_reached_lower_boundary": complete, "files": list(files.values()),
                     "coverage": _coverage(start, anchor, manifest["posts"], complete)})
    ledger_path = batch / "traversal.json"
    write_new_bytes(ledger_path, (json.dumps(manifest["traversal"], indent=2) + "\n").encode(), root)
    manifest["ledger"] = _record(ledger_path, root, kind="traversal_ledger")
    manifest["files"].append(manifest["ledger"])
    target = batch / "crawl_manifest.json"
    write_new_bytes(target, (json.dumps(manifest, indent=2) + "\n").encode(), root)
    print(json.dumps({"crawl_manifest": target.relative_to(root).as_posix(), "posts": len(manifest["posts"]),
                      "stop_reason": stop_reason, "complete": complete}), flush=True)
    return target


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--seed-manifest", type=Path, required=True)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--anchor", type=date.fromisoformat, default=date(2026, 10, 20))
    parser.add_argument("--max-posts", type=int, default=500)
    args = parser.parse_args(argv)
    print(crawl(resolve_publication_root(args.root), args.seed_manifest, start=args.start,
                anchor=args.anchor, max_posts=args.max_posts))


if __name__ == "__main__":
    main()
