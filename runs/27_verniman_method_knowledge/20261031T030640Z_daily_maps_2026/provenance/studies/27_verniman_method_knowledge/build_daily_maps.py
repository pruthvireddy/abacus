#!/usr/bin/env python3
"""Build and audit a private, offline Daily Map source archive.

This study-specific standard-library utility consumes an explicit capture
manifest. It performs no network requests, market calculations or publication.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import io
import json
import re
from collections import Counter
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


SCHEMA = "verniman.daily-map-archive/v1"
BLOCK_TAGS = {"div", "p", "br", "li", "h1", "h2", "h3", "h4", "tr", "blockquote", "hr"}
SKIP_TAGS = {"script", "style", "template"}
CSS = """body{margin:0;background:#f6f5f1;color:#242929;font:16px/1.6 system-ui,sans-serif}
main{max-width:1020px;margin:auto;padding:32px 22px 64px}a{color:#245a65;text-underline-offset:3px}
nav{display:flex;flex-wrap:wrap;gap:18px;margin-bottom:28px;font-size:14px}h1{font-size:34px;line-height:1.2;margin:12px 0}
h2{font-size:23px;margin-top:32px}p{max-width:78ch}.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#64716e}
.muted,.meta{color:#64716e;font-size:14px}.summary{display:flex;flex-wrap:wrap;gap:12px;margin:26px 0}
.stat{background:#fff;border:1px solid #dedfd7;border-radius:10px;padding:13px 20px;min-width:130px}.stat strong{font-size:24px;display:block}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #dddeda;vertical-align:top}
th{font-weight:600;background:#eceee8}.gap{color:#7c7261}.badge{font-size:12px;border:1px solid #bfcac4;border-radius:4px;padding:2px 6px;white-space:nowrap}
article{margin:28px 0 40px;padding:24px;background:white;border:1px solid #dedfd7;border-radius:12px}article h2{margin-top:0}
.notice{padding:13px 17px;background:#eeede3;border-left:3px solid #8d997a;border-radius:2px;margin:20px 0;font-size:14px}
figure{margin:22px 0}img{max-width:100%;height:auto;border:1px solid #dce0d9;border-radius:4px}figcaption{font-size:13px;color:#64716e}
.source-text p{white-space:pre-wrap;margin:1em 0}.months{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}.months a{background:#fff;padding:7px 12px;border:1px solid #dedfd7;border-radius:6px}
footer{border-top:1px solid #dddeda;margin-top:36px;padding-top:16px;font-size:13px;color:#64716e}code{font-size:13px;overflow-wrap:anywhere}
@media(max-width:650px){main{padding:22px 12px}h1{font-size:28px}th,td{padding:8px 5px}article{padding:16px}.capture-col{display:none}}
"""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bounded(root: Path, relative: str) -> Path:
    p = (root / relative).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError(f"path leaves archive root: {relative}")
    return p


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def write(path: Path, value: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(value.encode() if isinstance(value, str) else value)


def checked_bytes(root: Path, record: dict) -> bytes:
    value = bounded(root, record["path"]).read_bytes()
    if digest(value) != record["sha256"] or len(value) != record["bytes"]:
        raise ValueError(f"capture identity mismatch: {record['path']}")
    return value


def source_bytes(stage: Path, record: dict) -> bytes:
    value = checked_bytes(stage, record)
    raw = gzip.decompress(value) if record["path"].endswith(".gz") else value
    if record.get("uncompressed_sha256") and digest(raw) != record["uncompressed_sha256"]:
        raise ValueError(f"uncompressed source mismatch: {record['path']}")
    return raw


def safe_url(value: str, base: str) -> str | None:
    value = urljoin(base, value)
    return value if urlsplit(value).scheme in {"http", "https"} else None


class ArticleParser(HTMLParser):
    """Extract only article text, links and image positions without executing HTML."""

    def __init__(self, base: str):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.div_depth = 0
        self.found = 0
        self.skip = 0
        self.anchors: list[str | None] = []
        self.runs: list[dict] = []
        self.blocks: list[dict] = []

    def flush(self) -> None:
        if any(x["text"].strip() for x in self.runs):
            self.runs[0]["text"] = self.runs[0]["text"].lstrip()
            self.runs[-1]["text"] = self.runs[-1]["text"].rstrip()
            self.blocks.append({"type": "paragraph", "runs": self.runs})
        self.runs = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if not self.div_depth:
            if tag == "div" and "post-body" in (a.get("class") or "").split():
                self.found += 1
                self.div_depth = 1
            return
        if tag == "div":
            self.div_depth += 1
        if tag in SKIP_TAGS:
            self.skip += 1
        if self.skip:
            return
        if tag in BLOCK_TAGS:
            self.flush()
        if tag == "a":
            self.anchors.append(safe_url(a.get("href") or "", self.base))
        elif tag == "img":
            self.flush()
            src = safe_url(a.get("src") or a.get("data-src") or "", self.base)
            self.blocks.append({"type": "image", "url": self.anchors[-1] if self.anchors else src,
                                "inline_url": src, "alt": a.get("alt") or ""})
        elif tag in {"iframe", "video", "audio"} and a.get("src"):
            self.flush()
            self.blocks.append({"type": "media_link", "url": safe_url(a["src"], self.base)})

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in {"img", "br", "hr", "input", "meta", "link", "source"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.div_depth:
            return
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1
        if self.skip:
            if tag == "div":
                self.div_depth -= 1
            return
        if tag in BLOCK_TAGS:
            self.flush()
        if tag == "a" and self.anchors:
            self.anchors.pop()
        if tag == "div":
            self.div_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.div_depth and not self.skip:
            value = re.sub(r"\s+", " ", data.replace("\xa0", " "))
            if value:
                href = self.anchors[-1] if self.anchors else None
                if self.runs and self.runs[-1]["href"] == href:
                    self.runs[-1]["text"] += value
                else:
                    self.runs.append({"text": value, "href": href})


def parse_article(raw: bytes, url: str) -> dict:
    p = ArticleParser(url)
    p.feed(raw.decode("utf-8"))
    p.flush()
    if p.found != 1:
        raise ValueError(f"expected one post-body, observed {p.found}: {url}")
    text = "\n\n".join("".join(r["text"] for r in b["runs"]) for b in p.blocks if b["type"] == "paragraph")
    if not text.strip():
        raise ValueError(f"article has no retained body text: {url}")
    return {"blocks": p.blocks, "full_text": text}


def escaped(value: object) -> str:
    return html.escape(str(value), quote=True)


def relative_href(root: Path, current: Path, target: Path) -> str:
    import os
    return Path(os.path.relpath(target, current.parent)).as_posix()


def document(title: str, content: str, root_href: str = "index.html", extra_nav: str = "") -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>{escaped(title)} · Verniman Daily Map</title><style>{CSS}</style></head><body><main>
<nav><a href="{escaped(root_href)}">Daily Map archive</a>{extra_nav}</nav>{content}
<footer>Private source record · Captured source statements remain attributed to Verniman. Session dates are not verified publication or historical availability times.</footer>
</main></body></html>"""


def all_dates(start: str, end: str) -> list[str]:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError("archive start date exceeds end date")
    return [(last - timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]


def status_label(row: dict) -> str:
    labels = {"captured_live": "Captured", "retained_capture_only": "Retained earlier capture",
              "mixed_live_and_retained": "Live + retained revisions", "no_dated_post_observed_weekday": "No dated post observed",
              "no_dated_post_observed_weekend": "Weekend · no dated post observed"}
    return labels[row["status"]]


def table_rows(rows: list[dict], current: Path, archive: Path) -> str:
    result = []
    for row in rows:
        stamp = row["date"]
        href = relative_href(archive, current, archive / stamp[:4] / stamp[5:7] / stamp[8:] / "index.html")
        title = " / ".join(row["titles"]) or "—"
        result.append(f'<tr data-date="{stamp}"><td><a href="{href}">{stamp}</a><br><span class="muted">{row["weekday"]}</span></td>'
                      f'<td>{escaped(title)}</td><td class="{ "gap" if not row["post_count"] else ""}">{escaped(status_label(row))}</td>'
                      f'<td class="capture-col">{row["post_count"]} maps · {row["image_count"]} images</td></tr>')
    return '<table><thead><tr><th>Date</th><th>Daily Map</th><th>Record</th><th class="capture-col">Contents</th></tr></thead><tbody>' + "".join(result) + "</tbody></table>"


def build(stage: Path) -> dict:
    stage = stage.resolve()
    capture_path = stage / "capture-manifest.json"
    captures = json.loads(capture_path.read_text())
    archive = stage / "archive"
    if archive.exists():
        raise FileExistsError(f"refusing to replace existing archive: {archive}")
    dates = all_dates(captures["start_date"], captures["end_date"])
    posts = captures.get("posts", [])
    if not posts:
        raise ValueError("capture manifest has no posts")
    # Validate every input before creating output; a partial output is retained if later construction fails.
    parsed = []
    for post in posts:
        raw = source_bytes(stage, post["html"])
        article = parse_article(raw, post["url"])
        for image in post.get("images", []):
            if image.get("path"):
                checked_bytes(stage, image)
        parsed.append((post, raw, article))
    archive.mkdir()
    image_registry = {}
    archived_posts = []
    total_source_bytes = total_gzip_bytes = text_bytes = article_gzip_bytes = 0
    for ordinal, (post, raw, article) in enumerate(parsed, 1):
        stamp = post.get("session_date")
        in_scope = stamp in dates
        folder = Path(stamp[:4]) / stamp[5:7] / stamp[8:] if in_scope else Path("undated")
        identity = f"p{ordinal:04d}-{digest(post['url'].encode())[:10]}"
        capsule = folder / identity
        source_gz = gzip.compress(raw, compresslevel=9, mtime=0)
        write(archive / capsule / "source.html.gz", source_gz)
        images = []
        for image in post.get("images", []):
            record = {k: v for k, v in image.items() if k != "path"}
            if image.get("path"):
                value = checked_bytes(stage, image)
                sha = digest(value)
                ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp", "image/svg+xml": ".svg"}.get(image.get("content_type", "").split(";")[0], Path(image["path"]).suffix.lower())
                if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"}:
                    # SVG and unknown formats remain downloadable source bytes, never an inline active document.
                    ext = ".bin"
                retained = Path("assets") / (sha + ext)
                if sha not in image_registry:
                    write(archive / retained, value)
                    image_registry[sha] = {"path": retained.as_posix(), "bytes": len(value), "sha256": sha}
                record["path"] = image_registry[sha]["path"]
            images.append(record)
        stored = {"schema": SCHEMA, "url": post["url"], "title": post.get("title") or "Daily Map", "session_date": stamp,
                  "capture_kind": post.get("capture_kind", "live"), "captured_at": post.get("captured_at"),
                  "source_capture_at": post.get("source_capture_at"), "date_method": post.get("date_method"),
                  "date_warnings": post.get("date_warnings", []), "older_url": post.get("older_url"),
                  "images": images, "source_html_sha256": digest(raw), **article}
        article_gz = gzip.compress(json_bytes(stored), compresslevel=9, mtime=0)
        write(archive / capsule / "article.json.gz", article_gz)
        archived_posts.append({**stored, "capsule": capsule.as_posix(), "in_scope": in_scope})
        total_source_bytes += len(raw)
        total_gzip_bytes += len(source_gz)
        text_bytes += len(article["full_text"].encode())
        article_gzip_bytes += len(article_gz)
    by_date = {stamp: [p for p in archived_posts if p["session_date"] == stamp and p["in_scope"]] for stamp in dates}
    coverage = []
    for stamp in dates:
        items = by_date[stamp]
        live = sum(p["capture_kind"] == "live" for p in items)
        retained = len(items) - live
        weekend = date.fromisoformat(stamp).weekday() >= 5
        status = ("mixed_live_and_retained" if live and retained else "captured_live" if live else "retained_capture_only" if retained else
                  "no_dated_post_observed_weekend" if weekend else "no_dated_post_observed_weekday")
        coverage.append({"date": stamp, "weekday": date.fromisoformat(stamp).strftime("%A"), "status": status,
                         "post_count": len(items), "live_post_count": live, "retained_post_count": retained,
                         "image_count": sum(bool(im.get("path")) for p in items for im in p["images"]),
                         "missing_image_count": sum(not im.get("path") for p in items for im in p["images"]),
                         "titles": [p["title"] for p in items],
                         "notes": "Multiple distinct maps/revisions state this date; preserved separately." if len(items) > 1 else
                         "No dated post was observed in the traversal and retained-source review; this does not prove no post existed." if not items else ""})

    def render_post(post: dict, current: Path) -> str:
        capsule = archive / post["capsule"]
        image_matches = {im[key]: im for im in post["images"] for key in ["url", "requested_url", "inline_url", "final_url"] if im.get(key)}
        seen_images = set()

        def picture(im: dict | None, url: str | None, alt: str = "") -> str:
            if not im or not im.get("path"):
                detail = escaped(im.get("error", "No retained image bytes for this source image.")) if im else "No retained image bytes for this source image."
                return f'<div class="notice">Image unavailable. {detail}' + (f' <a href="{escaped(url)}">Source image</a>' if url else "") + "</div>"
            seen_images.add(im["path"])
            link = relative_href(archive, current, archive / im["path"])
            qualifier = "Inline rendition retained; full-size source unavailable. " if im.get("rendition") == "inline_thumbnail" else "Original retained source image. "
            label = alt or "Daily Map source chart"
            inline = Path(im["path"]).suffix != ".bin"
            tag = f'<a href="{link}"><img src="{link}" alt="{escaped(label)}" loading="lazy"></a>' if inline else f'<a href="{link}">Download retained image bytes</a>'
            return f'<figure>{tag}<figcaption>{qualifier}<a href="{escaped(url)}">Source</a> · <a href="{link}">Open full image</a></figcaption></figure>'

        content = []
        for block in post["blocks"]:
            if block["type"] == "paragraph":
                runs = []
                for run in block["runs"]:
                    text = escaped(run["text"])
                    runs.append(f'<a href="{escaped(run["href"])}">{text}</a>' if run.get("href") else text)
                content.append("<p>" + "".join(runs) + "</p>")
            elif block["type"] == "image":
                im = image_matches.get(block["url"]) or image_matches.get(block["inline_url"])
                content.append(picture(im, block["url"], block.get("alt", "")))
            elif block["type"] == "media_link" and block.get("url"):
                content.append(f'<p class="notice">Embedded media retained as a source reference: <a href="{escaped(block["url"])}">Open source media</a>. The media itself was not downloaded.</p>')
        for im in post["images"]:
            if im.get("path") not in seen_images:
                content.append(picture(im, im.get("url")))
        warnings = post["date_warnings"]
        warning_html = '<div class="notice">Date qualifications: ' + escaped("; ".join(warnings)) + "</div>" if warnings else ""
        source_link = relative_href(archive, current, capsule / "source.html.gz")
        json_link = relative_href(archive, current, capsule / "article.json.gz")
        kind = "Live capture" if post["capture_kind"] == "live" else "Retained earlier capture"
        return f'<article><h2>{escaped(post["title"])}</h2><p class="meta">{kind} · captured {escaped(post.get("source_capture_at") or post.get("captured_at") or "time unrecorded")}</p>' + warning_html + f'<p class="meta"><a href="{escaped(post["url"])}">Original post</a> · <a href="{source_link}">Compressed HTML</a> · <a href="{json_link}">Compressed article and metadata</a></p><div class="source-text">' + "".join(content) + "</div></article>"

    # A dated page and metadata note exist for every calendar day, including gaps.
    for index, row in enumerate(coverage):
        stamp = row["date"]
        current = archive / stamp[:4] / stamp[5:7] / stamp[8:] / "index.html"
        root_href = relative_href(archive, current, archive / "index.html")
        nav = []
        for other, label in [(index - 1, "Newer day"), (index + 1, "Older day")]:
            if 0 <= other < len(coverage):
                d = coverage[other]["date"]
                target = archive / d[:4] / d[5:7] / d[8:] / "index.html"
                nav.append(f'<a href="{relative_href(archive,current,target)}">{label}</a>')
        intro = f'<div class="eyebrow">Verniman Daily Map</div><h1>{stamp}</h1><p class="muted">{row["weekday"]} · {escaped(status_label(row))}</p>'
        items = by_date[stamp]
        if items:
            intro += '<p class="muted">Retained article body and source images. The displayed map date is inferred from source text and chronology.</p>'
            intro += "".join(render_post(p, current) for p in items)
        else:
            intro += '<div class="notice">No dated post was observed for this day. ' + ("This is a weekend date. " if date.fromisoformat(stamp).weekday() >= 5 else "") + "The record does not infer a missing plan from surrounding days or establish that no post ever existed.</div>"
        write(current, document(stamp, intro, root_href, "".join(nav)))
        md = [f"# Daily Map {stamp}", "", f"{row['weekday']} · {status_label(row)}", "", "[Read retained text and images](index.html)", ""]
        for post in items:
            rel = Path(post["capsule"]).name
            md += [f"## {post['title']}", "", f"[Original post]({post['url']}) · [Compressed source HTML]({rel}/source.html.gz) · [Compressed article record]({rel}/article.json.gz)", "",
                   f"Capture: {post['capture_kind']}; {post.get('source_capture_at') or post.get('captured_at') or 'time unrecorded'}.", ""]
            if post["date_warnings"]:
                md += ["Date qualifications: " + "; ".join(post["date_warnings"]), ""]
        if not items:
            md += [row["notes"], ""]
        write(current.with_name("README.md"), "\n".join(md))

    indexes = []
    for scope in [""] + sorted({s[:4] for s in dates}, reverse=True) + sorted({s[:7].replace("-", "/") for s in dates}, reverse=True):
        current = archive / scope / "index.html"
        selected = [r for r in coverage if not scope or r["date"].replace("-", "/").startswith(scope)]
        title = "Daily Map" + (" · " + scope.replace("/", "-") if scope else " · 2026")
        root_href = relative_href(archive, current, archive / "index.html")
        months = []
        for month in sorted({r["date"][:7] for r in selected}, reverse=True):
            target = archive / month[:4] / month[5:] / "index.html"
            months.append(f'<a href="{relative_href(archive,current,target)}">{month}</a>')
        stats = [(sum(bool(r["post_count"]) for r in selected), "days with maps"),
                 (sum(r["post_count"] for r in selected), "map records"),
                 (sum(r["image_count"] for r in selected), "retained images"),
                 (sum(not r["post_count"] and date.fromisoformat(r["date"]).weekday() < 5 for r in selected), "weekday gaps")]
        content = f'<div class="eyebrow">Verniman knowledge base</div><h1>{escaped(title)}</h1><p>Daily outlooks, plans and charts, ordered newest first. {selected[-1]["date"]} through {selected[0]["date"]}.</p>'
        content += '<div class="summary">' + "".join(f'<div class="stat"><strong>{n}</strong>{label}</div>' for n, label in stats) + "</div>"
        content += '<div class="notice">Dates come from map text and source chronology, not old permalink years. Earlier retained revisions are labeled. Gaps and ambiguous dates remain explicit.</div>'
        content += '<div class="months">' + "".join(months) + "</div>" + table_rows(selected, current, archive)
        if not scope:
            content += '<p><a href="gap-log.md">Gap and qualification log</a> · <a href="coverage.csv">Daily coverage CSV</a> · <a href="metrics.json">Archive counts</a></p>'
            if any(not p["in_scope"] for p in archived_posts):
                content += '<p><a href="undated/index.html">Ambiguous or boundary source records</a></p>'
        write(current, document(title, content, root_href))
        indexes.append({"path": current.relative_to(archive).as_posix(), "dates": [r["date"] for r in selected]})
        md = ["# " + title, "", "[Open offline archive](index.html)", "", "Dates descend. Missing days indicate no dated post observed, not proof of historical absence.", "", "| Date | Record | Maps | Images |", "|---|---|---:|---:|"]
        for row in selected:
            d = row["date"]
            target = archive / d[:4] / d[5:7] / d[8:] / "README.md"
            md.append(f"| [{d}]({relative_href(archive,current,target)}) | {status_label(row)} | {row['post_count']} | {row['image_count']} |")
        write(current.with_name("README.md"), "\n".join(md) + "\n")

    uncertain = [p for p in archived_posts if not p["in_scope"]]
    if uncertain:
        current = archive / "undated/index.html"
        content = '<h1>Ambiguous or boundary source records</h1><p>These source records are retained separately and are not assigned to an in-range calendar day.</p>'
        content += "".join(render_post(p, current) for p in uncertain)
        write(current, document("Ambiguous or boundary source records", content, "../index.html"))
    output = io.StringIO(newline="")
    fields = ["date", "weekday", "status", "post_count", "live_post_count", "retained_post_count", "image_count", "missing_image_count", "notes"]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows({k: r[k] for k in fields} for r in coverage)
    write(archive / "coverage.csv", output.getvalue())
    gaps = ["# Daily Map gaps and qualifications", "", "A gap means no dated post was observed. Weekends are listed separately; no exchange-holiday or publication-absence claim is inferred.", "", "## Weekday gaps", ""]
    gaps += ["- " + r["date"] + " — no dated post observed." for r in coverage if not r["post_count"] and date.fromisoformat(r["date"]).weekday() < 5] or ["None."]
    gaps += ["", "## Weekend dates without a dated post", "", ", ".join(r["date"] for r in coverage if not r["post_count"] and date.fromisoformat(r["date"]).weekday() >= 5), "", "## Source and image qualifications", ""]
    for p in archived_posts:
        for warning in p["date_warnings"]:
            gaps += [f"- {p.get('session_date') or 'Unassigned date'}: {warning} ([source]({p['url']}))."]
        for im in p["images"]:
            if not im.get("path") or im.get("rendition") == "inline_thumbnail":
                gaps += [f"- {p.get('session_date') or 'Unassigned date'} image: {im.get('error') or im.get('full_size_error') or 'inline rendition retained'} ([source]({im.get('url') or p['url']}))."]
    for failure in captures.get("failures", []):
        gaps += ["- Capture/discovery issue: " + json.dumps(failure, ensure_ascii=False, sort_keys=True)]
    for attempt in captures.get("attempts", []):
        if attempt.get("error"):
            gaps += [f"- Capture/discovery issue: [{attempt.get('url', 'source')}]({attempt.get('url', '')}) — {attempt.get('error')}; HTTP status {attempt.get('http_status')}. The failed response is retained in the capture manifest."]
    write(archive / "gap-log.md", "\n".join(gaps) + "\n")
    counts = Counter(r["status"] for r in coverage)
    metrics = {"schema": SCHEMA, "run_id": captures["run_id"], "start_date": dates[-1], "end_date": dates[0], "calendar_days": len(dates),
               "days_with_maps": sum(bool(r["post_count"]) for r in coverage), "map_records": sum(r["post_count"] for r in coverage),
               "unassigned_or_boundary_records": len(uncertain), "live_map_records": sum(p["capture_kind"] == "live" and p["in_scope"] for p in archived_posts),
               "retained_map_records": sum(p["capture_kind"] != "live" and p["in_scope"] for p in archived_posts), "status_counts": dict(counts),
               "weekday_gaps": sum(not r["post_count"] and date.fromisoformat(r["date"]).weekday() < 5 for r in coverage),
               "weekend_gaps": sum(not r["post_count"] and date.fromisoformat(r["date"]).weekday() >= 5 for r in coverage),
               "duplicate_date_count": sum(r["post_count"] > 1 for r in coverage), "image_references": sum(len(p["images"]) for p in archived_posts),
               "retained_image_references": sum(bool(im.get("path")) for p in archived_posts for im in p["images"]),
               "in_scope_retained_image_references": sum(bool(im.get("path")) for p in archived_posts if p["in_scope"] for im in p["images"]),
               "missing_image_references": sum(not im.get("path") for p in archived_posts for im in p["images"]),
               "inline_rendition_references": sum(im.get("rendition") == "inline_thumbnail" for p in archived_posts for im in p["images"]),
               "unique_image_files": len(image_registry), "unique_image_bytes": sum(v["bytes"] for v in image_registry.values()),
               "source_html_bytes": total_source_bytes, "compressed_source_html_bytes": total_gzip_bytes,
               "article_text_utf8_bytes": text_bytes, "compressed_article_json_bytes": article_gzip_bytes,
               "compression_policy": "Gzip level 9 for source HTML and article JSON; content-addressed source image bytes retained without recompression or resizing."}
    write(archive / "metrics.json", json_bytes(metrics))
    files = [{"path": p.relative_to(archive).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p.read_bytes())} for p in sorted(archive.rglob("*")) if p.is_file()]
    inventory = {"schema": SCHEMA, "source_capture_manifest_sha256": digest(capture_path.read_bytes()), "files": files, "indexes": indexes,
                 "posts": [{k: p[k] for k in ["url", "session_date", "capsule", "in_scope", "source_html_sha256"]} for p in archived_posts],
                 "archive_bytes_excluding_manifest": sum(f["bytes"] for f in files)}
    write(archive / "archive-manifest.json", json_bytes(inventory))
    return check(stage)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.dates: list[str] = []
        self.remote_images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("data-date"):
            self.dates.append(a["data-date"])
        for name in ["href", "src"]:
            if a.get(name):
                self.links.append(a[name])
        if tag == "img" and urlsplit(a.get("src") or "").scheme:
            self.remote_images.append(a["src"])


def check(stage: Path) -> dict:
    stage = stage.resolve()
    capture = stage / "capture-manifest.json"
    archive = stage / "archive"
    inputs = json.loads(capture.read_text())
    inventory = json.loads((archive / "archive-manifest.json").read_text())
    metrics = json.loads((archive / "metrics.json").read_text())
    if digest(capture.read_bytes()) != inventory["source_capture_manifest_sha256"]:
        raise ValueError("capture manifest changed after archive construction")
    listed = {x["path"] for x in inventory["files"]}
    actual = {x.relative_to(archive).as_posix() for x in archive.rglob("*") if x.is_file()} - {"archive-manifest.json"}
    if listed != actual or len(listed) != len(inventory["files"]):
        raise ValueError("archive inventory differs from actual files")
    for item in inventory["files"]:
        checked_bytes(archive, item)
    with (archive / "coverage.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    dates = all_dates(inputs["start_date"], inputs["end_date"])
    if [r["date"] for r in rows] != dates:
        raise ValueError("calendar coverage is incomplete or not descending")
    if metrics["calendar_days"] != len(dates) or metrics["days_with_maps"] != sum(int(r["post_count"]) > 0 for r in rows):
        raise ValueError("archive metrics disagree with daily coverage")
    if metrics["map_records"] != sum(int(r["post_count"]) for r in rows):
        raise ValueError("map record count mismatch")
    if len(inventory["posts"]) != len(inputs["posts"]):
        raise ValueError("source record omitted during construction")
    for original, record in zip(inputs["posts"], inventory["posts"]):
        capsule = bounded(archive, record["capsule"])
        raw = gzip.decompress((capsule / "source.html.gz").read_bytes())
        article = json.loads(gzip.decompress((capsule / "article.json.gz").read_bytes()))
        source = source_bytes(stage, original["html"])
        if raw != source or digest(raw) != record["source_html_sha256"]:
            raise ValueError("retained HTML differs from pinned capture")
        parsed = parse_article(raw, original["url"])
        if parsed["full_text"] != article["full_text"] or parsed["blocks"] != article["blocks"]:
            raise ValueError("retained article text or image ordering changed")
        for image in article["images"]:
            if image.get("path"):
                checked_bytes(archive, image)
    index_dates = {item["path"]: item["dates"] for item in inventory["indexes"]}
    links = 0
    for path in sorted(archive.rglob("*.html")):
        p = LinkParser()
        p.feed(path.read_text())
        if p.remote_images:
            raise ValueError(f"remote images are not allowed in offline viewer: {path}")
        relative = path.relative_to(archive).as_posix()
        if relative in index_dates and p.dates != index_dates[relative]:
            raise ValueError(f"HTML date ordering mismatch: {relative}")
        for link in p.links:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc or link.startswith("#"):
                continue
            target = (path.parent / unquote(parts.path)).resolve()
            if not target.is_relative_to(archive) or not target.is_file():
                raise ValueError(f"broken or escaping local link: {relative} -> {link}")
            links += 1
    markdown_links = 0
    for path in sorted(archive.rglob("*.md")):
        for link in re.findall(r"\]\(([^\s)]+)\)", path.read_text()):
            parts = urlsplit(link)
            if parts.scheme or parts.netloc or link.startswith("#"):
                continue
            target = (path.parent / unquote(parts.path)).resolve()
            if not target.is_relative_to(archive) or not target.is_file():
                raise ValueError(f"broken or escaping Markdown link: {path.relative_to(archive)} -> {link}")
            markdown_links += 1
    return {"status": "passed", "calendar_days": len(dates), "map_records": metrics["map_records"],
            "retained_image_references": metrics["retained_image_references"], "unique_image_files": metrics["unique_image_files"],
            "inventoried_files": len(inventory["files"]), "local_html_links_checked": links,
            "local_markdown_links_checked": markdown_links,
            "archive_bytes": inventory["archive_bytes_excluding_manifest"] + (archive / "archive-manifest.json").stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--check", action="store_true", help="Audit an existing archive without writing")
    args = parser.parse_args()
    result = check(args.stage) if args.check else build(args.stage)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
