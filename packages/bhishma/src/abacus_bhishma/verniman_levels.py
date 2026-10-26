"""Offline, immutable publication of captured Verniman daily outlook levels.

These are observations of captured content, not a point-in-time trading signal.
The Blogger published/updated fields are source claims; historical availability
of the current outlook remains unknown even when those fields contain a time.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq

from . import provenance
from .paths import resolve_publication_root
from .publication_safety import check_absent, check_path, write_new_bytes

DATASET_ID = "verniman_daily_levels__1.0.0"
VERSION = "1.0.0"
EXTRACTION_VERSION = "verniman_ab_plan_v1"
TIMING_STATUS = "historical_availability_unverified"
EXPECTED_SESSIONS = frozenset(date(2026, 10, day) for day in (7, 8, 9, 12, 13, 14, 15, 16, 19, 20))
DATA_PATH = Path("data/curated/external_levels/source=verniman/version=1.0.0")
MANIFEST_PATH = Path(f"catalog/datasets/{DATASET_ID}.json")
SCHEMA_PATH = Path(f"catalog/schemas/{DATASET_ID}.json")
QUALITY_PATH = Path(f"reports/quality/{DATASET_ID}.md")
ATOM = "{http://www.w3.org/2005/Atom}"
EASTERN = ZoneInfo("America/New_York")
PRICE_TYPE = pa.decimal128(12, 2)
_LEVEL = re.compile(
    r"(?P<label>[A-Z][A-Z/-]*)\s*(?P<low>\d{3,6}(?:\.\d{1,2})?)"
    r"(?:\s*[-–]\s*(?P<high>\d{1,6}(?:\.\d{1,2})?))?"
)


class _Text(HTMLParser):
    def __init__(self, *, post_only: bool = False):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.post_only = post_only
        self.depth = 0
        self.active_depth: int | None = None
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignored += 1
        if self.post_only and tag == "div":
            self.depth += 1
            if "post-body" in dict(attrs).get("class", "").split():
                if self.active_depth is not None:
                    raise ValueError("multiple nested post-body elements")
                self.active_depth = self.depth
        if tag in {"p", "div", "br", "li"} and self._active():
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"p", "div", "li"} and self._active():
            self.parts.append("\n")
        if self.post_only and tag == "div":
            if self.active_depth == self.depth:
                self.active_depth = None
            self.depth -= 1
        if tag in {"script", "style"}:
            self.ignored = max(0, self.ignored - 1)

    def _active(self):
        return not self.ignored and (not self.post_only or self.active_depth is not None)

    def handle_data(self, data):
        if self._active():
            self.parts.append(data)


def content_text(html: str, *, post_only: bool = False) -> str:
    """Read visible text only; never infer dates/times from image filenames."""
    parser = _Text(post_only=post_only)
    parser.feed(html)
    return "\n".join(line for part in "".join(parser.parts).splitlines()
                     if (line := " ".join(part.split())))


def _timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamps require an explicit timezone")
    return result.astimezone(timezone.utc)


def _scenario_text(text: str) -> dict[str, str]:
    found = {}
    for letter, side in (("A", "bullish"), ("B", "bearish")):
        matches = re.findall(rf"(?m)^\s*{letter}\)\s*(.+)$", text)
        if len(matches) != 1:
            raise ValueError(f"expected one {letter}) scenario, found {len(matches)}")
        found[side] = matches[0].strip()
    return found


def _prices(text: str) -> list[dict]:
    result = []
    for match in _LEVEL.finditer(text):
        low_text, high_text = match["low"], match["high"]
        low = Decimal(low_text).quantize(Decimal("0.01"))
        if high_text and len(high_text.split(".")[0]) < len(low_text.split(".")[0]):
            if "." in low_text or "." in high_text:
                raise ValueError("ambiguous abbreviated decimal range")
            high_text = low_text[:-len(high_text)] + high_text
        high = Decimal(high_text).quantize(Decimal("0.01")) if high_text else low
        if high < low:
            raise ValueError(f"descending price range: {match[0]}")
        result.append({"source_label": match["label"], "price_low": low,
                       "price_high": high, "source_text": match[0]})
    # Fail closed when a number could not be assigned to a labelled level.
    if not result or re.search(r"\d", _LEVEL.sub("", text)):
        raise ValueError(f"unrecognised level notation: {text}")
    return result


def extract_entry(atom_xml: bytes | str, *, captured_at: str, html_path: str,
                  atom_path: str, html_sha256: str, atom_sha256: str,
                  source_url: str | None = None, html_text: str | None = None,
                  atom_captured_at: str | None = None
                  ) -> tuple[dict, list[dict]]:
    """Extract only explicitly labelled A/B trigger and target statements."""
    entry = ET.fromstring(atom_xml)
    if entry.tag != ATOM + "entry":
        raise ValueError("expected a single Atom entry")
    source_id = entry.findtext(ATOM + "id")
    title = entry.findtext(ATOM + "title")
    body = entry.findtext(ATOM + "content")
    if not source_id or title is None or not body:
        raise ValueError("Atom entry lacks id, title, or content")
    alternate = next((node.get("href") for node in entry.findall(ATOM + "link")
                      if node.get("rel") == "alternate"), None)
    if not alternate or (source_url is not None and source_url != alternate):
        raise ValueError("captured URL and Atom alternate URL disagree")
    text = content_text(body)
    scenarios = _scenario_text(text)
    outlook = re.search(r"\bOutlook\s+(\d{1,2})/(\d{1,2})\b", text)
    contract = re.search(r"\b([A-Z]{1,4}[FGHJKMNQUVXZ](\d{2}))\s*\(\s*[A-Za-z]+\s*(20\d{2})\s*\)", text)
    if not outlook or not contract or int(contract[2]) != int(contract[3]) % 100:
        raise ValueError("session date requires Outlook M/D and an explicit matching contract year")
    if html_text is not None:
        html_visible = content_text(html_text, post_only=True)
        html_outlook = re.search(r"\bOutlook\s+(\d{1,2})/(\d{1,2})\b", html_visible)
        html_contract = re.search(r"\b([A-Z]{1,4}[FGHJKMNQUVXZ](\d{2}))\s*\(\s*[A-Za-z]+\s*(20\d{2})\s*\)", html_visible)
        if (_scenario_text(html_visible) != scenarios or html_outlook is None or html_contract is None
                or html_outlook.groups() != outlook.groups() or html_contract.groups() != contract.groups()):
            raise ValueError("HTML and Atom outlook identities or A/B plans differ; preserve both captures for review")
    session_date = date(int(contract[3]), int(outlook[1]), int(outlook[2]))
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    revision = hashlib.sha256((source_id + "\n" + content_hash).encode()).hexdigest()
    row = {
        "outlook_id": revision, "source_post_id": source_id,
        "content_sha256": content_hash, "title": title, "source_url": alternate,
        "product": re.sub(r"[FGHJKMNQUVXZ]\d{2}$", "", contract[1]),
        "contract": contract[1], "session_date": session_date,
        "session_date_method": "body_outlook_month_day_plus_explicit_contract_year",
        "session_date_source_text": f"{outlook[0]}; {contract[0]}",
        "captured_at": max(_timestamp(captured_at), _timestamp(atom_captured_at)) if atom_captured_at else _timestamp(captured_at),
        "raw_html_captured_at": _timestamp(captured_at),
        "raw_atom_captured_at": _timestamp(atom_captured_at) if atom_captured_at else None,
        "available_at": None,
        "timing_status": TIMING_STATUS, "plan_text": "\n".join(scenarios.values()),
        "raw_html_path": html_path, "raw_html_sha256": html_sha256,
        "raw_atom_path": atom_path, "raw_atom_sha256": atom_sha256,
        "extraction_version": EXTRACTION_VERSION,
        "review_status": "snapshot_extracted_html_atom_plan_matched" if html_text is not None else "snapshot_extracted",
    }
    for name in ("published", "updated"):
        claimed = entry.findtext(ATOM + name)
        stamp = _timestamp(claimed) if claimed else None
        row[f"source_claimed_{name}"] = claimed
        row[f"source_claimed_{name}_at"] = stamp
        row[f"source_claimed_{name}_eastern"] = stamp.astimezone(EASTERN).isoformat() if stamp else None
    levels = []
    for side, scenario in scenarios.items():
        match = re.fullmatch(
            r"If market (?:moves(?:\s+remains)?|remains)\s+(above|below)\s+(.+?)\s+with\s+(.+?),\s*"
            r"(buy|sell)\s+(?:towards?\s+)?(.+)", scenario, flags=re.IGNORECASE,
        )
        expected = ("above", "buy") if side == "bullish" else ("below", "sell")
        if not match or (match[1].lower(), match[4].lower()) != expected:
            raise ValueError(f"unrecognised {side} scenario: {scenario}")
        triggers, targets = _prices(match[2]), _prices(match[5])
        if len(triggers) != 1:
            raise ValueError("expected exactly one trigger in each scenario")
        for role, values in (("trigger", triggers), ("target", targets)):
            for ordinal, value in enumerate(values, 1):
                levels.append({"outlook_id": revision, "session_date": session_date,
                               "product": row["product"], "contract": row["contract"],
                               "side": side, "role": role, "ordinal": ordinal,
                               **value, "conditions": match[3],
                               "scenario_text": scenario, "available_at": None,
                               "timing_status": TIMING_STATUS})
    return row, levels


def outlook_schema() -> pa.Schema:
    required_strings = (
        "outlook_id source_post_id content_sha256 title source_url product contract "
        "session_date_method session_date_source_text timing_status plan_text "
        "raw_html_path raw_html_sha256 raw_atom_path raw_atom_sha256 extraction_version review_status"
    ).split()
    fields = [pa.field(name, pa.string(), False) for name in required_strings]
    fields += [pa.field("session_date", pa.date32(), False),
               pa.field("captured_at", pa.timestamp("us", tz="UTC"), False),
               pa.field("raw_html_captured_at", pa.timestamp("us", tz="UTC"), False),
               pa.field("raw_atom_captured_at", pa.timestamp("us", tz="UTC")),
               pa.field("available_at", pa.timestamp("us", tz="UTC"), True)]
    for name in ("published", "updated"):
        fields += [pa.field(f"source_claimed_{name}", pa.string()),
                   pa.field(f"source_claimed_{name}_at", pa.timestamp("us", tz="UTC")),
                   pa.field(f"source_claimed_{name}_eastern", pa.string())]
    return pa.schema(fields, metadata={b"dataset_id": DATASET_ID.encode(), b"table": b"outlooks"})


def levels_schema() -> pa.Schema:
    return pa.schema([
        pa.field("outlook_id", pa.string(), False), pa.field("session_date", pa.date32(), False),
        *[pa.field(name, pa.string(), False) for name in ("product", "contract", "side", "role")],
        pa.field("ordinal", pa.int32(), False),
        pa.field("price_low", PRICE_TYPE, False), pa.field("price_high", PRICE_TYPE, False),
        *[pa.field(name, pa.string(), False) for name in
          ("source_label", "source_text", "conditions", "scenario_text")],
        pa.field("available_at", pa.timestamp("us", tz="UTC")),
        pa.field("timing_status", pa.string(), False),
    ], metadata={b"dataset_id": DATASET_ID.encode(), b"table": b"levels"})


def schema_document() -> dict:
    return {"dataset_id": DATASET_ID, "version": VERSION,
            "tables": {name: [{"name": field.name, "arrow_type": str(field.type),
                                "nullable": field.nullable} for field in schema]
                       for name, schema in (("outlooks", outlook_schema()), ("levels", levels_schema()))},
            "prices": "Exact decimal(12,2), source contract points; never roll adjusted. Equal bounds denote a point.",
            "available_at": "Always null: captured current content has unverified historical availability.",
            "timestamps": "Source-claimed published/updated metadata is retained separately and is not proof of plan availability.",
            "session_date": "Outlook M/D with explicit body contract year; never URL, image filename, or published year.",
            "null_semantics": "Unknown timestamps remain null; absent data is not a negative signal.",
            "level_selection": "A/B scenarios only; trigger and ordered targets kept separately for each side."}


def _contained(root: Path, locator: str) -> Path:
    path = Path(locator)
    if not path.is_absolute():
        path = root / path
    return check_path(path, root, error=ValueError)


def _record(path: Path, root: Path) -> dict:
    return {"path": str(path.relative_to(root)), "sha256": provenance.sha256_file(path),
            "bytes": path.stat().st_size}


def _check_record(record: dict, root: Path, *, verify_bytes: bool = True) -> Path:
    if (not isinstance(record, dict) or not isinstance(record.get("path"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", record.get("sha256", ""))
            or type(record.get("bytes")) is not int or record["bytes"] < 0):
        raise ValueError("invalid file identity")
    path = _contained(root, record["path"])
    if not path.is_file():
        raise ValueError(f"missing declared file: {path}")
    if verify_bytes and (path.stat().st_size != record["bytes"] or provenance.sha256_file(path) != record["sha256"]):
        raise ValueError(f"declared bytes do not match: {path}")
    return path


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, default=lambda item: item.isoformat() if isinstance(item, (date, datetime)) else str(item)) + "\n").encode()


def _csv(path: Path, rows: list[dict], names: list[str]) -> None:
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        writer.writerows({key: value.isoformat() if isinstance(value, (datetime, date)) else value
                         for key, value in row.items()} for row in rows)


def _daily_summary(outlooks: list[dict], levels: list[dict]) -> list[dict]:
    summaries = []
    for outlook in outlooks:
        row = {key: outlook[key] for key in (
            "session_date", "contract", "source_url", "title", "outlook_id", "available_at", "timing_status",
            "source_claimed_published", "source_claimed_updated", "source_claimed_published_at",
            "source_claimed_updated_at", "source_claimed_published_eastern", "source_claimed_updated_eastern", "captured_at")}
        for side in ("bullish", "bearish"):
            selected = [level for level in levels if level["outlook_id"] == outlook["outlook_id"] and level["side"] == side]
            trigger = next(level for level in selected if level["role"] == "trigger")
            row.update({f"{side}_trigger_low": trigger["price_low"], f"{side}_trigger_high": trigger["price_high"],
                        f"{side}_trigger_label": trigger["source_label"], f"{side}_conditions": trigger["conditions"]})
            targets = sorted((level for level in selected if level["role"] == "target"), key=lambda item: item["ordinal"])
            row[f"{side}_targets"] = " | ".join(level["source_text"] for level in targets)
            for ordinal in range(1, 1 + max(item["ordinal"] for item in levels if item["role"] == "target")):
                target = next((item for item in targets if item["ordinal"] == ordinal), {})
                for field in ("price_low", "price_high", "source_label"):
                    row[f"{side}_target_{ordinal}_{field}"] = target.get(field)
        summaries.append(row)
    return summaries


def _validate_tables(outlooks: pa.Table, levels: pa.Table) -> None:
    for name, table, expected in (("outlooks", outlooks, outlook_schema()), ("levels", levels, levels_schema())):
        if not table.schema.equals(expected, check_metadata=True) or not table.num_rows:
            raise ValueError(f"unexpected {name} schema or empty table")
        if any(table[field.name].null_count for field in expected if not field.nullable):
            raise ValueError(f"null in required {name} field")
        if table["available_at"].null_count != table.num_rows or set(table["timing_status"].to_pylist()) != {TIMING_STATUS}:
            raise ValueError("historical availability must remain explicitly unverified")
    parents = {row["outlook_id"]: row for row in outlooks.to_pylist()}
    if len(parents) != outlooks.num_rows:
        raise ValueError("duplicate outlook revision")
    sessions = [row["session_date"] for row in parents.values()]
    if len(sessions) != len(set(sessions)) or set(sessions) != EXPECTED_SESSIONS:
        raise ValueError("release 1.0.0 requires exactly the ten declared October 7–20, 2026 sessions")
    if any(row["contract"] != "ESZ26" or row["product"] != "ES" for row in parents.values()):
        raise ValueError("release 1.0.0 requires source-stated ESZ26 contract and ES product")
    groups: dict[tuple, list[dict]] = {}
    for row in levels.to_pylist():
        parent = parents.get(row["outlook_id"])
        if parent is None or any(row[key] != parent[key] for key in ("session_date", "contract", "product")):
            raise ValueError("level has invalid outlook reference")
        if row["side"] not in {"bullish", "bearish"} or row["role"] not in {"trigger", "target"} or row["price_low"] > row["price_high"]:
            raise ValueError("invalid level role, side, or price bounds")
        groups.setdefault((row["outlook_id"], row["side"], row["role"]), []).append(row)
    for identity in parents:
        for side in ("bullish", "bearish"):
            for role in ("trigger", "target"):
                rows = groups.get((identity, side, role), [])
                if not rows or (role == "trigger" and len(rows) != 1) or sorted(row["ordinal"] for row in rows) != list(range(1, len(rows) + 1)):
                    raise ValueError("missing/duplicate/non-contiguous scenario levels")


def publish_release(batch_manifest: Path | str, root: Path | str, request: Path | str) -> Path:
    """Publish from already captured bytes; no network and no overwrite mode."""
    root = Path(root).resolve()
    batch_path, request_path = _contained(root, str(batch_manifest)), _contained(root, str(request))
    batch_record, request_record = _record(batch_path, root), _record(request_path, root)
    batch = json.loads(batch_path.read_text())
    if batch.get("source") != "verniman" or not batch.get("posts") or not isinstance(batch.get("files"), list):
        raise ValueError("expected verniman capture manifest with posts and files")
    outputs = [root / DATA_PATH, root / MANIFEST_PATH, root / SCHEMA_PATH, root / QUALITY_PATH]
    for path in outputs + [item.with_name(item.name + ".part") for item in outputs[1:]]:
        check_absent(path, root)
    batch_id = batch.get("batch_id", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", batch_id):
        raise ValueError("unsafe or missing capture batch id")
    stage = root / "data/staging/verniman" / batch_id
    check_absent(stage, root)
    stage.mkdir(parents=True)
    (stage / "capture_manifest.json").write_bytes(batch_path.read_bytes())
    declared = provenance.publication_sources(Path(__file__), ("verniman_capture.py", "provenance.py", "publication_safety.py", "paths.py"))
    prepared = stage / "curated"
    prepared.mkdir()
    retained = provenance.retain_sources(prepared / "provenance", declared, artifact_id=DATASET_ID, root=root)
    # Everything after stage creation is retained for inspection after failure.
    inventory = {}
    for record in batch["files"]:
        _check_record(record, root)
        if record["path"] in inventory:
            raise ValueError("duplicate raw file identity")
        inventory[record["path"]] = record
    outlook_rows, level_rows = [], []
    for post in batch["posts"]:
        for record in [post["html"], post["atom"], *post.get("images", [])]:
            if any(record.get(key) != inventory.get(record.get("path"), {}).get(key) for key in ("path", "sha256", "bytes")):
                raise ValueError("post source is not pinned in capture inventory")
        html_path, atom_path = _check_record(post["html"], root), _check_record(post["atom"], root)
        if _timestamp(post["captured_at"]) != _timestamp(post["html"]["captured_at"]):
            raise ValueError("post capture timestamp differs from HTML capture timestamp")
        row, levels = extract_entry(
            atom_path.read_bytes(), captured_at=post["captured_at"], html_path=post["html"]["path"],
            atom_path=post["atom"]["path"], html_sha256=post["html"]["sha256"], atom_sha256=post["atom"]["sha256"],
            source_url=post["url"], html_text=html_path.read_text(encoding="utf-8"),
            atom_captured_at=post["atom"]["captured_at"],
        )
        outlook_rows.append(row)
        level_rows.extend(levels)
    outlook_rows.sort(key=lambda row: (row["session_date"], row["outlook_id"]))
    level_rows.sort(key=lambda row: (row["session_date"], row["outlook_id"], row["side"], row["role"], row["ordinal"]))
    tables = {"outlooks": pa.Table.from_pylist(outlook_rows, schema=outlook_schema()),
              "levels": pa.Table.from_pylist(level_rows, schema=levels_schema())}
    _validate_tables(tables["outlooks"], tables["levels"])
    (stage / "extracted.json").write_bytes(_json_bytes({"outlooks": outlook_rows, "levels": level_rows}))
    for name, table in tables.items():
        pq.write_table(table, prepared / f"{name}.parquet", compression="zstd")
        _csv(prepared / f"{name}.csv", table.to_pylist(), table.column_names)
    summaries = _daily_summary(outlook_rows, level_rows)
    _csv(prepared / "daily_summary.csv", summaries, list(summaries[0]))
    schema_bytes = _json_bytes(schema_document())
    quality = (
        f"# Verniman daily levels {VERSION}\n\n"
        f"Captured outlook revisions: {len(outlook_rows)}. Scenario level rows: {len(level_rows)}.\n\n"
        f"Session coverage: {outlook_rows[0]['session_date']} through {outlook_rows[-1]['session_date']}.\n\n"
        "A/B plan text matched between captured HTML and Atom for every post. Only scenario triggers and ordered targets were extracted; summary headers were excluded. Exact point prices and zones retain source labels, conditions and text. Differing bullish/bearish trigger labels remain distinct.\n\n"
        "This fixed 1.0.0 sample requires exactly October 7, 8, 9, 12, 13, 14, 15, 16, 19 and 20, 2026, and source-stated ESZ26. No missing session or extra session is accepted.\n\n"
        "All available_at values are null. Blogger published/updated fields are source-claimed metadata, not proof of the availability of current plan content. Recycled permalink dates and image filenames do not date an outlook. Session dates use Outlook M/D and the explicitly stated contract year; that year assignment is an inference. This snapshot must not be treated as verified premarket historical signals.\n\n"
        "Validation covers file identities, schemas, source-plan agreement and extraction structure. It does not establish historical publication timing, market accuracy, strategy performance or scientific validity. No missing sessions are interpolated. Source chart images are retained when declared by the capture manifest and are not OCR inputs.\n"
    ).encode()
    # These qualifications are asserted against the sample rather than silently
    # copied into reports for unrelated future releases.
    oct13 = [item for item in level_rows if item["session_date"] == date(2026, 10, 13)]
    trigger_labels = {item["side"]: item["source_label"] for item in oct13 if item["role"] == "trigger"}
    if trigger_labels == {"bullish": "HVE-YVAL", "bearish": "HVE-YVAH"}:
        quality += b"\nOctober 13 retains conflicting trigger labels: bullish HVE-YVAL versus bearish HVE-YVAH, both 7850.00. The captured summary header lists GAP 7856, whereas Plan A lists GAP 7857; the extracted bullish target is the Plan A value 7857.00.\n"
    quality += ("\nSource metadata (original claimed timezone offsets; UTC and Eastern conversions are in the tables):\n\n"
                "| Session | Source-claimed published | Source-claimed updated |\n|---|---|---|\n" +
                "\n".join(f"| {row['session_date']} | {row['source_claimed_published']} | {row['source_claimed_updated']} |"
                          for row in outlook_rows) + "\n\n"
                "These are source claims, not independently verified availability. captured_at is the later of the HTML and Atom response timestamps; both source capture timestamps are retained.\n").encode()
    (stage / "schema.json").write_bytes(schema_bytes)
    (stage / "quality.md").write_bytes(quality)
    files = []
    for path in sorted(prepared.rglob("*")):
        if path.is_file():
            record = _record(path, prepared)
            record["path"] = str(DATA_PATH / record["path"])
            files.append(record)
    files.extend([
        {"path": str(SCHEMA_PATH), "sha256": hashlib.sha256(schema_bytes).hexdigest(), "bytes": len(schema_bytes)},
        {"path": str(QUALITY_PATH), "sha256": hashlib.sha256(quality).hexdigest(), "bytes": len(quality)},
    ])
    manifest = {
        "dataset_id": DATASET_ID, "version": VERSION, "source": "verniman",
        "created_at": datetime.now(timezone.utc).isoformat(), "source_batch": batch_record,
        "request": request_record, "raw_files": list(inventory.values()),
        "schema_path": str(SCHEMA_PATH), "quality_report_path": str(QUALITY_PATH),
        "tables": {name: {"path": str(DATA_PATH / f"{name}.parquet"), "rows": table.num_rows} for name, table in tables.items()},
        "files": files, "provenance": {**provenance.git_version(root), "retained": retained,
                                       "path": str(DATA_PATH / "provenance")},
        "extraction_version": EXTRACTION_VERSION, "available_at_policy": TIMING_STATUS,
        "publication_invocation": {
            "entry_point": "abacus_bhishma.verniman_levels",
            "working_directory": "publication_root",
            "arguments": {"root": ".", "batch_manifest": batch_record["path"], "request": request_record["path"]},
            "reconstruction_argv": ["./scripts/uv", "run", "--locked", "--no-sync", "python", "-m",
                                    "abacus_bhishma.verniman_levels", "--root", ".", "--batch-manifest",
                                    batch_record["path"], "--request", request_record["path"]],
            "environment": {"UV_CACHE_DIR": ".uv-cache"},
            "note": "Reconstruction requires an empty publication destination; existing final and staged evidence is never replaced.",
        },
        "review_status": "snapshot_source_plan_agreement_and_schema_checked",
        "known_limitations": ["Source-claimed timestamps do not establish current-plan historical availability.",
                              "Session year is inferred from body contract year.",
                              "This is a captured-content sample, not a point-in-time trading dataset."],
    }
    (stage / "manifest.json").write_bytes(_json_bytes(manifest))
    provenance.verify_retained_sources(prepared / "provenance", declared, retained)
    _check_record(batch_record, root)
    _check_record(request_record, root)
    for record in inventory.values():
        _check_record(record, root)
    for path in outputs + [item.with_name(item.name + ".part") for item in outputs[1:]]:
        check_absent(path, root)
    check_path(prepared, root)
    (root / DATA_PATH).parent.mkdir(parents=True, exist_ok=True)
    prepared.rename(root / DATA_PATH)
    write_new_bytes(root / SCHEMA_PATH, schema_bytes, root)
    write_new_bytes(root / QUALITY_PATH, quality, root)
    write_new_bytes(root / MANIFEST_PATH, _json_bytes(manifest), root)
    verify_release(root, root / MANIFEST_PATH, provenance.sha256_file(root / MANIFEST_PATH))
    return root / MANIFEST_PATH


def verify_release(root: Path | str, manifest_path: Path | str, expected_manifest_sha256: str,
                   *, verify_bytes: bool = True) -> dict:
    """Read-only verification of an explicit, hash-pinned release; never repairs."""
    root = Path(root).resolve()
    selected = Path(manifest_path)
    if not selected.is_absolute():
        selected = root / selected
    if selected.is_symlink() or selected.resolve() != selected.absolute():
        raise ValueError("manifest must be an explicit non-symlinked file")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256 or "") or provenance.sha256_file(selected) != expected_manifest_sha256:
        raise ValueError("manifest SHA-256 does not match required pin")
    manifest = json.loads(selected.read_text())
    if (manifest.get("dataset_id") != DATASET_ID or manifest.get("version") != VERSION
            or manifest.get("available_at_policy") != TIMING_STATUS
            or set(manifest.get("tables", {})) != {"outlooks", "levels"}):
        raise ValueError("unsupported dataset identity, timing policy, or table inventory")
    files = manifest.get("files", [])
    paths = [item.get("path") for item in files]
    required = {str(DATA_PATH / name) for name in (
        "outlooks.parquet", "levels.parquet", "outlooks.csv", "levels.csv", "daily_summary.csv", "provenance/sources.json")}
    required.update((str(SCHEMA_PATH), str(QUALITY_PATH)))
    if len(paths) != len(set(paths)) or not required.issubset(paths):
        raise ValueError("invalid publication artifact inventory")
    for record in files:
        _check_record(record, root, verify_bytes=verify_bytes)
    for record in [manifest["source_batch"], manifest["request"], *manifest["raw_files"]]:
        _check_record(record, root, verify_bytes=verify_bytes)
    schema = json.loads((root / SCHEMA_PATH).read_text())
    if schema != schema_document():
        raise ValueError("release schema differs from supported contract")
    tables = {}
    for name, record in manifest["tables"].items():
        if record.get("path") != str(DATA_PATH / f"{name}.parquet") or type(record.get("rows")) is not int:
            raise ValueError("invalid table path or row count")
        tables[name] = pq.ParquetFile(_contained(root, record["path"])).read()
        if tables[name].num_rows != record["rows"]:
            raise ValueError("table row count differs from manifest")
    _validate_tables(tables["outlooks"], tables["levels"])
    return manifest


def load_release(root: Path | str, manifest_path: Path | str, expected_manifest_sha256: str,
                 *, table: str = "outlooks", verify_bytes: bool = True) -> pa.Table:
    """Load one manifest-listed table after explicit identity and schema checks."""
    if table not in {"outlooks", "levels"}:
        raise ValueError(f"unsupported table: {table}")
    manifest = verify_release(root, manifest_path, expected_manifest_sha256, verify_bytes=verify_bytes)
    return pq.ParquetFile(_contained(Path(root).resolve(), manifest["tables"][table]["path"])).read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-manifest", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    result = publish_release(args.batch_manifest, resolve_publication_root(args.root), args.request)
    print(json.dumps({"manifest": str(result), "manifest_sha256": provenance.sha256_file(result)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
