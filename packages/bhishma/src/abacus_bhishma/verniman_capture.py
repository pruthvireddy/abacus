"""Capture explicit public Vern outlook pages without replacing prior batches.

Network collection is separate from offline extraction/publication. HTML, Atom
and linked post images retain their response-body bytes. HTTP and source metadata
are observations, never proof of historical pre-open availability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .paths import resolve_publication_root
from .provenance import git_version
from .publication_safety import check_absent, write_new_bytes

MAX_BYTES = 20 * 1024 * 1024


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _PostLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.div_depth = 0
        self.body_depth: int | None = None
        self.post_id: str | None = None
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs)
        if tag == "div":
            self.div_depth += 1
            if "post-body" in (attrs.get("class") or "").split():
                if self.body_depth is not None:
                    raise ValueError("nested post-body")
                self.body_depth = self.div_depth
        if tag == "a" and (attrs.get("name") or "").isdigit():
            if self.post_id is not None:
                raise ValueError("expected one post per capture")
            self.post_id = attrs["name"]
        # Preserve the full-size image links inside the post, not template icons.
        if self.body_depth is not None and tag == "a":
            href = attrs.get("href") or ""
            parsed = urlsplit(href)
            if (parsed.scheme == "https" and parsed.hostname == "blogger.googleusercontent.com"
                    and parsed.path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
                    and href not in self.images):
                self.images.append(href)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Empty image/br tags do not change div nesting.
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "div":
            if self.body_depth == self.div_depth:
                self.body_depth = None
            self.div_depth -= 1


def _fetch(url: str, path: Path, root: Path, kind: str) -> dict:
    started = _now()
    request = Request(url, headers={"User-Agent": "Abacus historical-source capture/1.0"})
    with urlopen(request, timeout=40) as response:
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError(f"capture exceeds {MAX_BYTES} bytes: {url}")
        if response.status != 200:
            raise ValueError(f"unexpected capture HTTP status {response.status}: {url}")
        headers = {key: response.headers[key] for key in
                   ("Content-Type", "Content-Encoding", "Date", "Last-Modified", "ETag")
                   if key in response.headers}
        final_url = response.url
        status = response.status
    if not payload:
        raise ValueError(f"empty capture: {url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    write_new_bytes(path, payload, root)
    return {"kind": kind, "path": path.relative_to(root).as_posix(), "url": url,
            "final_url": final_url, "request_started_at": started, "captured_at": _now(),
            "http_status": status, "headers": headers, "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest()}


def capture_pages(root: Path, urls: list[str], *, batch_id: str | None = None) -> Path:
    """Fetch only explicitly supplied post URLs into one new immutable batch."""
    root = root.resolve()
    if not urls:
        raise ValueError("at least one post URL is required")
    canonical = []
    for url in urls:
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.netloc != "verniman.blogspot.com"
                or not parts.path.endswith(".html") or parts.fragment):
            raise ValueError(f"expected an explicit HTTPS Vern post URL: {url}")
        canonical.append(urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")))
    if len(canonical) != len(set(canonical)):
        raise ValueError("duplicate post URLs")
    batch_id = batch_id or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                            + "_" + uuid.uuid4().hex[:8])
    if not batch_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                           for char in batch_id):
        raise ValueError("unsafe batch ID")
    batch = root / "data/raw/blogspot/verniman/html" / batch_id
    check_absent(batch, root)
    batch.mkdir(parents=True)
    manifest = {"batch_id": batch_id, "source": "verniman",
                "capture_started_at": _now(), "capture_method": "urllib.request; explicit URLs; response body bytes",
                "command": sys.argv, "code_state": git_version(root), "posts": [], "files": [],
                "timing_caveat": "Source publication/update claims and HTTP dates do not establish historical plan availability."}
    try:
        for index, url in enumerate(canonical, 1):
            page = _fetch(url + "?m=0", batch / f"post-{index:02d}.html", root, "html")
            manifest["files"].append(page)
            links = _PostLinks()
            links.feed((root / page["path"]).read_text(encoding="utf-8"))
            if links.post_id is None:
                raise ValueError(f"no unambiguous Blogger post ID in {url}")
            atom = _fetch("https://verniman.blogspot.com/feeds/posts/default/" + links.post_id,
                          batch / f"post-{index:02d}.atom", root, "atom")
            manifest["files"].append(atom)
            images = []
            for image_index, image_url in enumerate(links.images, 1):
                suffix = Path(urlsplit(image_url).path).suffix.lower()
                record = _fetch(image_url, batch / "images" / f"post-{index:02d}-{image_index:02d}{suffix}",
                                root, "image")
                images.append(record)
                manifest["files"].append(record)
            manifest["posts"].append({"url": url, "captured_at": page["captured_at"],
                                      "html": page, "atom": atom, "images": images})
        manifest["capture_completed_at"] = _now()
        target = batch / "batch_manifest.json"
        write_new_bytes(target, (json.dumps(manifest, indent=2) + "\n").encode(), root)
        return target
    except Exception as exc:
        manifest["capture_failed_at"] = _now()
        manifest["error"] = f"{type(exc).__name__}: {exc}"
        write_new_bytes(batch / "capture_failure.json", (json.dumps(manifest, indent=2) + "\n").encode(), root)
        raise


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Configured publication root (workspace containing data and catalog)")
    parser.add_argument("--url", action="append", required=True, help="Explicit post URL; repeat for each post")
    parser.add_argument("--batch-id", help="New capture identity; existing batches are refused")
    args = parser.parse_args(argv)
    print(capture_pages(resolve_publication_root(args.root), args.url, batch_id=args.batch_id))


if __name__ == "__main__":
    main()
