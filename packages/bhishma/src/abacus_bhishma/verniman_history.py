"""Publish a chronological Verniman capture with transparent partial extraction.

Every captured in-scope post is retained, including posts without parseable plans.
Numeric extraction fails closed for each branch; issues and the complete calendar
coverage remain inspectable. All historical availability values remain unknown.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from . import provenance
from .paths import resolve_publication_root
from .publication_safety import check_absent, check_path, write_new_bytes
from .verniman_levels import (
    ATOM, EASTERN, TIMING_STATUS, _check_record, _contained, _csv, _json_bytes,
    _record, _timestamp, content_text,
)

DATASET_ID = "verniman_daily_levels__2.0.0"
VERSION = "2.0.0"
EXTRACTION_VERSION = "verniman_history_ab_v2"
DATA_PATH = Path("data/curated/external_levels/source=verniman/version=2.0.0")
MANIFEST_PATH = Path(f"catalog/datasets/{DATASET_ID}.json")
SCHEMA_PATH = Path(f"catalog/schemas/{DATASET_ID}.json")
QUALITY_PATH = Path(f"reports/quality/{DATASET_ID}.md")
_NUMBER = r"\d{3,6}(?:\.\d{1,2})?"
_SUFFIX = r"\d{1,6}(?:\.\d{1,2})?"
_GROUP = re.compile(rf"(?P<label>[A-Z][A-Z/-]*s?(?:\s+(?:Collar|collar|Sell|Buy))?)\s*(?:(?:support|resistance|magnet|zone|at|pending|exp|key level)\s+)?(?P<prices>{_NUMBER}(?:\s*[-–]\s*{_SUFFIX})*)")
_OUTLOOK = re.compile(r"\bOutlook\s+(\d{1,2})/(\d{1,2})\b", re.IGNORECASE)
_CONTRACT = re.compile(r"\b(ES[FGHJKMNQUVXZ](\d{2}))\b(?:\s*\(\s*[A-Za-z]+\s*(20\d{2})\s*\))?")
TABLES = ("outlooks", "levels", "issues", "coverage")


def _field(name: str, kind=pa.string(), nullable=False):
    return pa.field(name, kind, nullable)


def schemas() -> dict[str, pa.Schema]:
    timestamps = ["captured_at", "raw_html_captured_at", "raw_atom_captured_at", "available_at",
                  "source_claimed_published_at", "source_claimed_updated_at"]
    outlooks = [
        *[_field(name) for name in ("outlook_id", "source_post_id", "content_sha256", "source_url", "title",
                                   "session_date_method", "timing_status", "extraction_version", "extraction_status",
                                   "content_kind", "source_agreement_status", "source_year_status", "crawl_date_warnings_json", "ledger_id",
                                   "body_text", "raw_html_path", "raw_html_sha256")],
        *[_field(name, nullable=True) for name in ("product", "contract", "session_date_source_text", "bullish_scenario_text",
            "bearish_scenario_text", "bullish_conditions", "bearish_conditions", "raw_atom_path", "raw_atom_sha256",
            "source_claimed_published", "source_claimed_updated", "source_claimed_published_eastern", "source_claimed_updated_eastern")],
        _field("session_date", pa.date32(), True), _field("body_contract_year", pa.int16(), True),
        *[_field(name, pa.timestamp("us", tz="UTC"), name != "captured_at" and name != "raw_html_captured_at") for name in timestamps],
        _field("parsed_branch_count", pa.int16()), _field("level_count", pa.int32()), _field("issue_count", pa.int32()),
    ]
    levels = [
        *[_field(name) for name in ("outlook_id", "product", "contract", "side", "role", "source_label", "source_text",
                                   "notation", "scenario_text", "timing_status")],
        _field("conditions", nullable=True), _field("session_date", pa.date32()), _field("ordinal", pa.int32()),
        _field("price_low", pa.decimal128(12, 2)), _field("price_high", pa.decimal128(12, 2)),
        _field("available_at", pa.timestamp("us", tz="UTC"), True),
    ]
    issues = [
        *[_field(name) for name in ("issue_id", "severity", "scope", "code", "description")],
        *[_field(name, nullable=True) for name in ("outlook_id", "source_url", "side", "source_text")],
        _field("session_date", pa.date32(), True),
    ]
    coverage = [
        _field("session_date", pa.date32()), _field("status"), _field("reason", nullable=True),
        _field("post_count", pa.int32()), _field("complete_post_count", pa.int32()),
        _field("partial_post_count", pa.int32()), _field("failed_post_count", pa.int32()),
        _field("non_outlook_post_count", pa.int32()),
        _field("level_count", pa.int32()), _field("issue_count", pa.int32()),
        *[_field(name) for name in ("post_urls_json", "outlook_ids_json", "ledger_json")],
    ]
    return {name: pa.schema(fields, metadata={b"dataset_id": DATASET_ID.encode(), b"table": name.encode()})
            for name, fields in zip(TABLES, (outlooks, levels, issues, coverage))}


def schema_document() -> dict:
    return {
        "dataset_id": DATASET_ID, "version": VERSION,
        "tables": {name: [{"name": item.name, "arrow_type": str(item.type), "nullable": item.nullable} for item in schema]
                   for name, schema in schemas().items()},
        "available_at": "Always null; source claims and capture chronology do not prove historical availability.",
        "session_date": "Dated crawl ledger, anchored to the 2026 October 20 outlook; body M/D is cross-checked. Delivery-contract year never determines session year.",
        "revision_identity": "SHA256(source_post_id + newline + SHA256(extracted visible source body UTF-8)).",
        "extraction": "Only A/B plan branches; each ambiguous branch yields no numeric rows, with raw text and issues retained. Other valid branches remain.",
        "ranges": "Singular labels with two endpoints denote zones; low/high are numeric bounds even when source endpoints descend. Lowercase-plural labels, e.g. PBTs and GAPs, denote ordered point sequences. A singular label followed by three or more full prices (each at least three digits) is an explicit point sequence with a warning; abbreviated singular multi-price sequences are refused. Abbreviated two-endpoint suffixes retain the leading digits of the preceding full price.",
        "price_outlier_warning": "A source point more than max(500 points, 10% of the post median) from the median is flagged, never corrected.",
        "missingness": "No interpolation. Zero extracted levels does not mean zero source targets. Missing date coverage means no post was observed, not proof that none was ever published.",
        "source_certainty": "HTML/Atom agreement, metadata claims, parse success and historical availability are separate qualifications.",
    }


def _issue(outlook: dict, code: str, description: str, *, side: str | None = None,
           source_text: str | None = None, severity: str = "warning", scope: str = "post") -> dict:
    identity = "\n".join((outlook["outlook_id"], code, side or "", scope, description, source_text or ""))
    return {"issue_id": hashlib.sha256(identity.encode()).hexdigest(), "outlook_id": outlook["outlook_id"],
            "session_date": outlook["session_date"], "source_url": outlook["source_url"], "side": side,
            "severity": severity, "scope": scope, "code": code, "description": description, "source_text": source_text}


def _branches(text: str) -> dict[str, str]:
    # Join wrapped lines within a branch, stopping at the next branch or note.
    found = {}
    for label, side in (("A", "bullish"), ("B", "bearish")):
        pattern = rf"(?ims)^\s*{label}[).:]\s*(.+?)(?=^\s*(?:[A-C][).:]|Note\s*:|Market Movers|Follow\s)|\Z)"
        matches = re.findall(pattern, text)
        if len(matches) == 1:
            found[side] = " ".join(matches[0].split())
        elif len(matches) > 1:
            found[side] = "\n".join(" ".join(value.split()) for value in matches)
    return found


def _expand(number: str, previous: str) -> Decimal:
    if len(number.split(".")[0]) < len(previous.split(".")[0]):
        if "." in number or "." in previous:
            raise ValueError("ambiguous abbreviated decimal endpoint")
        number = previous[:-len(number)] + number
    value = Decimal(number).quantize(Decimal("0.01"))
    if not (Decimal("100") <= value < Decimal("1000000")):
        raise ValueError("price endpoint is outside supported numeric syntax")
    return value


def parse_level_groups(text: str) -> list[dict]:
    """Read source-labelled points/zones; unassigned digits fail the branch."""
    result = []
    for match in _GROUP.finditer(text):
        parts = re.split(r"\s*[-–]\s*", match["prices"])
        plural = match["label"].endswith("s")
        full_sequence = len(parts) > 2 and not plural and all(len(part.split(".")[0]) >= 3 for part in parts)
        if len(parts) > 2 and not plural and not full_sequence:
            raise ValueError(f"ambiguous singular multi-price sequence: {match[0]}")
        if full_sequence:
            numbers = [Decimal(part).quantize(Decimal("0.01")) for part in parts]
        else:
            numbers = [_expand(parts[0], parts[0])]
            previous = parts[0]
            for part in parts[1:]:
                number = _expand(part, previous)
                numbers.append(number)
                previous = format(number, ".0f") if number == number.to_integral_value() else str(number)
        if plural or full_sequence:
            ranges = [(value, value) for value in numbers]
            notation = "singular_full_point_sequence" if full_sequence else ("plural_point_sequence" if len(numbers) > 1 else "point")
        else:
            ranges = [(min(numbers), max(numbers))]
            notation = "zone" if len(numbers) > 1 else "point"
        result.extend({"source_label": match["label"], "price_low": low, "price_high": high,
                       "source_text": match[0], "notation": notation} for low, high in ranges)
    unassigned = _GROUP.sub("", text)
    unassigned = re.sub(r"\(\s*\d{1,2}\s*[- ]\s*(?:weeks?|days?|hours?|minutes?)\b[^)]*\)", "", unassigned, flags=re.IGNORECASE)
    if not result or re.search(r"\d", unassigned):
        raise ValueError(f"unassigned or unrecognised numeric level: {text}")
    return result


def parse_branch(text: str, side: str) -> tuple[list[dict], str | None]:
    action = re.search(r"\b(buy|sell)\s+(?:(?:towards?|to|targeting)\s+)?(.+)$", text, re.IGNORECASE)
    if not action:
        raise ValueError("missing explicit buy/sell target clause")
    prefix = text[:action.start()].rstrip(" ,;:-")
    direction = re.search(r"\b(above|below)\s+(.+)$", prefix, re.IGNORECASE)
    expected = ("above", "buy") if side == "bullish" else ("below", "sell")
    if not direction or (direction[1].lower(), action[1].lower()) != expected:
        raise ValueError("branch direction/action does not unambiguously match its side")
    parts = re.split(r"\s+with\s+", direction[2], maxsplit=1, flags=re.IGNORECASE)
    trigger_text = parts[0].strip(" ,;")
    conditions = parts[1].strip(" ,;") if len(parts) > 1 else None
    triggers, targets = parse_level_groups(trigger_text), parse_level_groups(action[2])
    if len(triggers) != 1:
        raise ValueError("branch does not contain exactly one explicit trigger")
    rows = [{**value, "side": side, "role": role, "ordinal": ordinal,
             "conditions": conditions, "scenario_text": text}
            for role, values in (("trigger", triggers), ("target", targets))
            for ordinal, value in enumerate(values, 1)]
    return rows, conditions


def extract_post(post: dict, root: Path | str) -> tuple[dict, list[dict], list[dict]]:
    """Retain one dated capture and independently extract each safe branch."""
    root = Path(root).resolve()
    html_record = post["html"]
    html = _check_record(html_record, root).read_text(encoding="utf-8")
    html_visible = content_text(html, post_only=True)
    atom_record = post.get("atom")
    entry, atom_visible = None, None
    atom_problem = None
    if atom_record:
        xml = _check_record(atom_record, root).read_bytes()
        try:
            entry = ET.fromstring(xml)
            if entry.tag != ATOM + "entry":
                raise ValueError("not a single Atom entry")
            body = entry.findtext(ATOM + "content")
            if not body:
                raise ValueError("Atom entry has no content")
            atom_visible = content_text(body)
        except (ET.ParseError, ValueError) as error:
            atom_problem = str(error)
            entry = None
    visible = atom_visible if atom_visible is not None else html_visible
    source_id = entry.findtext(ATOM + "id") if entry is not None else None
    source_id = source_id or post.get("source_post_id") or post.get("post_id") or post["url"]
    content_hash = hashlib.sha256(visible.encode()).hexdigest()
    revision = hashlib.sha256((source_id + "\n" + content_hash).encode()).hexdigest()
    stated = _OUTLOOK.search(visible)
    contract_matches = list(_CONTRACT.finditer(visible))
    contract_headers = [match for match in contract_matches if not visible[:match.start()].rsplit("\n", 1)[-1].strip()]
    contract = contract_headers[0] if contract_headers else (contract_matches[0] if contract_matches else None)
    inferred_date = date.fromisoformat(post["session_date"]) if post.get("session_date") else None
    html_stamp = _timestamp(html_record.get("captured_at", post["captured_at"]))
    atom_stamp = _timestamp(atom_record["captured_at"]) if atom_record else None
    found = _branches(visible)
    row = {
        "outlook_id": revision, "source_post_id": str(source_id), "content_sha256": content_hash,
        "source_url": post["url"], "title": (entry.findtext(ATOM + "title") if entry is not None else post.get("title")) or "",
        "product": "ES" if contract else None, "contract": contract[1] if contract else None,
        "body_contract_year": int(contract[3]) if contract and contract[3] else (2000 + int(contract[2]) if contract else None),
        "session_date": inferred_date,
        "session_date_method": post.get("session_date_method", "crawl_ledger_anchored_year_plus_body_month_day"),
        "session_date_source_text": stated[0] if stated else None,
        "raw_html_path": html_record["path"], "raw_html_sha256": html_record["sha256"],
        "raw_atom_path": atom_record["path"] if atom_record else None,
        "raw_atom_sha256": atom_record["sha256"] if atom_record else None,
        "raw_html_captured_at": html_stamp, "raw_atom_captured_at": atom_stamp,
        "captured_at": max(html_stamp, atom_stamp) if atom_stamp else html_stamp,
        "available_at": None, "timing_status": TIMING_STATUS,
        "body_text": visible, "bullish_scenario_text": found.get("bullish"), "bearish_scenario_text": found.get("bearish"),
        "bullish_conditions": None, "bearish_conditions": None,
        "extraction_version": EXTRACTION_VERSION, "source_agreement_status": "html_only" if atom_visible is None else "compared",
        "content_kind": "daily_outlook",
        "source_year_status": "unresolved", "crawl_date_warnings_json": json.dumps(post.get("date_warnings", [])),
        "ledger_id": post.get("ledger_id", post["url"]),
        "extraction_status": "failed", "parsed_branch_count": 0, "level_count": 0, "issue_count": 0,
    }
    problems = []
    for name in ("published", "updated"):
        claimed = entry.findtext(ATOM + name) if entry is not None else None
        try:
            stamp = _timestamp(claimed) if claimed else None
        except ValueError:
            stamp = None
            problems.append(_issue(row, "invalid_source_timestamp", f"Invalid source-claimed {name} timestamp retained as text.", source_text=claimed))
        row[f"source_claimed_{name}"] = claimed
        row[f"source_claimed_{name}_at"] = stamp
        row[f"source_claimed_{name}_eastern"] = stamp.astimezone(EASTERN).isoformat() if stamp else None
    if atom_visible is None:
        problems.append(_issue(row, "atom_unavailable", "Using captured HTML only; Atom agreement could not be checked." + (f" {atom_problem}" if atom_problem else "")))
    for error in post.get("capture_errors", []):
        message = error if isinstance(error, str) else json.dumps(error, sort_keys=True)
        image_failure = message.lower().startswith("image ")
        problems.append(_issue(
            row, "image_capture_failed" if image_failure else "source_capture_error",
            "An image capture failed; retained HTML/Atom plan text remains available." if image_failure else
            "A source capture operation failed; retained source bytes and extraction remain separately qualified.",
            source_text=message,
        ))
    if stated is None and not found and contract is None:
        row["content_kind"] = "commentary_without_explicit_daily_plan"
        row["extraction_status"] = "no_explicit_plan"
        row["source_agreement_status"] = "html_atom_visible_content_matched" if atom_visible == html_visible else row["source_agreement_status"]
        problems.append(_issue(row, "no_explicit_daily_plan", "This commentary post has no dated ES daily outlook or A/B plan. Its prose and images are retained; standalone narrative numbers are not converted into daily plan levels."))
        row["issue_count"] = len(problems)
        return row, [], problems
    blocked = False
    if inferred_date is None:
        problems.append(_issue(row, "session_date_unresolved", "Crawl chronology did not resolve a session date; no numeric extraction.", severity="error"))
        blocked = True
    if stated is None or (inferred_date and (int(stated[1]), int(stated[2])) != (inferred_date.month, inferred_date.day)):
        problems.append(_issue(row, "ledger_body_date_mismatch", "Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.", source_text=stated[0] if stated else None, severity="error"))
        blocked = True
    if not contract:
        problems.append(_issue(row, "contract_missing", "No unambiguous source ES contract was found; no numeric extraction.", severity="error"))
        blocked = True
    elif len({match[1] for match in contract_headers}) > 1:
        problems.append(_issue(row, "conflicting_contracts", "Multiple different ES contracts appear in source text; no numeric extraction.", source_text=" | ".join(match[0] for match in contract_matches), severity="error"))
        blocked = True
    elif contract[3] and int(contract[2]) != int(contract[3]) % 100:
        problems.append(_issue(row, "contract_year_inconsistent", "Contract code and parenthesized delivery year disagree; no numeric extraction.", source_text=contract[0], severity="error"))
        blocked = True
    elif inferred_date and inferred_date.year == 2026 and inferred_date.month <= 10 and row["body_contract_year"] != 2026:
        problems.append(_issue(row, "stale_source_year_conflict", "The anchored January–October 2026 date conflicts with the source delivery-contract year; numeric extraction refused and the post retained.", source_text=contract[0], severity="error"))
        row["source_year_status"] = "stale_source_year_conflict"
        blocked = True
    elif inferred_date and row["body_contract_year"] != inferred_date.year:
        problems.append(_issue(row, "contract_year_differs_from_session", "Delivery-contract year differs from inferred session year; session date was not changed.", source_text=contract[0]))
        row["source_year_status"] = "different_delivery_year_qualified"
    elif contract:
        row["source_year_status"] = "source_contract_year_matches_session"
    if contract and any(match[1] != contract[1] for match in contract_matches):
        problems.append(_issue(row, "other_contracts_mentioned", "Rollover commentary mentions other contracts; levels use the explicit contract heading.", source_text=" | ".join(dict.fromkeys(match[0] for match in contract_matches))))
    if entry is not None:
        alternate = next((node.get("href") for node in entry.findall(ATOM + "link") if node.get("rel") == "alternate"), None)
        if alternate != post["url"]:
            problems.append(_issue(row, "atom_url_mismatch", "HTML capture URL and Atom alternate URL disagree; no numeric extraction.", source_text=alternate, severity="error"))
            blocked = True
        html_date, html_contract = _OUTLOOK.search(html_visible), _CONTRACT.search(html_visible)
        identity_mismatch = ((html_date.groups() if html_date else None) != (stated.groups() if stated else None)
                             or (contract[1] if contract else None) != (html_contract[1] if html_contract else None))
        if identity_mismatch:
            problems.append(_issue(row, "html_atom_identity_mismatch", "HTML and Atom date or contract disagree; no numeric extraction.", severity="error"))
            blocked = True
        row["source_agreement_status"] = "identity_mismatch" if identity_mismatch else "html_atom_identity_matched"
    stamp = row["source_claimed_updated_at"]
    if stamp and inferred_date and stamp.astimezone(EASTERN).date() != inferred_date:
        problems.append(_issue(row, "source_updated_date_differs", "Source-claimed update day differs from stated Outlook day; candidate metadata date retained without correcting the outlook.", source_text=row["source_claimed_updated"]))
    introduction = visible.split("\n", 1)[0]
    weekday = re.search(r"\bon\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", introduction)
    if inferred_date and weekday and weekday[1] != inferred_date.strftime("%A"):
        problems.append(_issue(row, "source_weekday_differs", "The source introduction names another weekday; body M/D and anchored date are retained without correction.", source_text=weekday[0]))
    levels = []
    html_branches = _branches(html_visible)
    for side in ("bullish", "bearish"):
        branch = found.get(side)
        if branch:
            condition_match = re.search(r"\bwith\s+(.+?)(?=[,;]?\s*\b(?:buy|sell)\b)", branch, re.IGNORECASE)
            row[f"{side}_conditions"] = condition_match[1].strip(" ,;") if condition_match else None
        if not branch:
            problems.append(_issue(row, "branch_missing", "No unique labelled plan branch was found.", side=side, scope="branch", severity="error"))
            continue
        letter = "A" if side == "bullish" else "B"
        if len(re.findall(rf"(?m)^\s*{letter}[).:]", visible)) != 1:
            problems.append(_issue(row, "branch_duplicated", "Multiple source branches have the same label; numeric extraction refused.", side=side, scope="branch", source_text=branch, severity="error"))
            continue
        if atom_visible is not None and branch != html_branches.get(side):
            problems.append(_issue(row, "html_atom_branch_mismatch", "Captured HTML and Atom branch texts disagree; branch numeric extraction refused.", side=side, scope="branch", source_text=branch, severity="error"))
            continue
        if blocked:
            continue
        try:
            selected, conditions = parse_branch(branch, side)
        except ValueError as error:
            problems.append(_issue(row, "branch_parse_failed", str(error), side=side, scope="branch", source_text=branch, severity="error"))
            continue
        row[f"{side}_conditions"] = conditions
        row["parsed_branch_count"] += 1
        for item in selected:
            if item["notation"] == "singular_full_point_sequence":
                problems.append(_issue(row, "singular_multi_point_sequence", "Three or more full prices following a singular source label are retained as an explicit ordered point sequence, with the original notation.", side=side, source_text=item["source_text"]))
        levels.extend({**item, "outlook_id": revision, "session_date": inferred_date,
                       "product": row["product"], "contract": row["contract"],
                       "available_at": None, "timing_status": TIMING_STATUS} for item in selected)
    row["level_count"] = len(levels)
    row["extraction_status"] = {0: "failed", 1: "partial", 2: "complete"}[row["parsed_branch_count"]]
    if levels:
        middle = Decimal(str(statistics.median([item["price_low"] for item in levels])))
        for item in levels:
            if abs(item["price_low"] - middle) > max(Decimal("500"), middle * Decimal("0.10")):
                problems.append(_issue(row, "contextual_price_outlier", f"Source price {item['price_low']:.2f} differs substantially from other prices in this post; retained without correction.", side=item["side"], source_text=item["source_text"]))
        triggers = [item for item in levels if item["role"] == "trigger"]
        for trigger in triggers:
            for target in [item for item in levels if item["side"] == trigger["side"] and item["role"] == "target"]:
                opposite = (target["price_high"] < trigger["price_low"] if trigger["side"] == "bullish"
                            else target["price_low"] > trigger["price_high"])
                if opposite:
                    problems.append(_issue(row, "target_opposite_trigger_direction", f"Source target {target['ordinal']} ({target['price_low']:.2f}–{target['price_high']:.2f}) lies on the opposite side of its branch trigger; retained exactly without correction.", side=target["side"], source_text=target["source_text"]))
        if len(triggers) == 2 and (triggers[0]["source_label"], triggers[0]["price_low"], triggers[0]["price_high"]) != (triggers[1]["source_label"], triggers[1]["price_low"], triggers[1]["price_high"]):
            problems.append(_issue(row, "different_branch_triggers", "Bullish and bearish triggers differ in source label or price; both are retained.", source_text=" | ".join(item["source_text"] for item in triggers)))
    problems = list({item["issue_id"]: item for item in problems}.values())
    row["issue_count"] = len(problems)
    return row, levels, problems


def _range(manifest: dict) -> tuple[date, date]:
    start = date.fromisoformat(manifest.get("requested_start_date", "2026-01-01"))
    end = date.fromisoformat(manifest.get("anchor_session_date", "2026-10-20"))
    if start > end or start.year != 2026 or end.year != 2026:
        raise ValueError("history release requires an explicit 2026 calendar interval")
    return start, end


def build_tables(crawl: dict, root: Path | str) -> dict[str, pa.Table]:
    """Extract all captured in-scope posts and reconcile the calendar ledger."""
    root = Path(root).resolve()
    start, end = _range(crawl)
    outlooks, levels, issues = [], [], []
    seen = {}
    for post in crawl["posts"]:
        stamp = date.fromisoformat(post["session_date"]) if post.get("session_date") else None
        if stamp is not None and not start <= stamp <= end:
            continue
        row, selected, problems = extract_post(post, root)
        if row["outlook_id"] in seen:
            # The same revision can be reached twice by navigation; preserve that
            # traversal in the ledger, but never duplicate the canonical table.
            previous = seen[row["outlook_id"]]
            if row["session_date"] != previous["session_date"]:
                issues.append(_issue(previous, "duplicate_revision_ledger_conflict", "The same captured content revision has conflicting dates in the traversal ledger; the first assignment is retained and both visits remain in the raw ledger.", severity="error"))
            continue
        seen[row["outlook_id"]] = row
        outlooks.append(row)
        levels.extend(selected)
        issues.extend(problems)
    for day, count in Counter(row["session_date"] for row in outlooks if row["session_date"]).items():
        if count > 1:
            for row in outlooks:
                if row["session_date"] == day:
                    issues.append(_issue(row, "duplicate_outlook_date", f"{count} distinct captured post revisions state this session date; retained separately."))
    counts = Counter(item["outlook_id"] for item in issues)
    for row in outlooks:
        row["issue_count"] = counts[row["outlook_id"]]
    coverage_input = crawl.get("coverage")
    if not isinstance(coverage_input, list):
        raise ValueError("crawl manifest requires a complete calendar coverage ledger")
    by_day = {}
    for record in coverage_input:
        day = date.fromisoformat(record["session_date"])
        if day in by_day or not start <= day <= end:
            raise ValueError("duplicate or out-of-range calendar coverage date")
        by_day[day] = record
    days = [start + timedelta(days=index) for index in range((end - start).days + 1)]
    if set(by_day) != set(days):
        raise ValueError("calendar ledger must explicitly cover every date, including gaps and weekends")
    coverage = []
    for day in days:
        record = by_day[day]
        posts = [row for row in outlooks if row["session_date"] == day]
        if (not isinstance(record.get("post_urls"), list)
                or set(record["post_urls"]) != {row["source_url"] for row in posts}):
            raise ValueError(f"calendar ledger post URLs disagree with captured outlooks on {day}")
        statuses = Counter(row["extraction_status"] for row in posts)
        coverage.append({"session_date": day, "status": record.get("status", "post_observed" if posts else "no_post_observed"),
                         "reason": record.get("reason"), "post_count": len(posts),
                         "complete_post_count": statuses["complete"], "partial_post_count": statuses["partial"],
                         "failed_post_count": statuses["failed"], "non_outlook_post_count": statuses["no_explicit_plan"], "level_count": sum(row["level_count"] for row in posts),
                         "issue_count": sum(row["issue_count"] for row in posts),
                         "post_urls_json": json.dumps([row["source_url"] for row in posts]),
                         "outlook_ids_json": json.dumps([row["outlook_id"] for row in posts]),
                         "ledger_json": json.dumps(record, sort_keys=True)})
    outlooks.sort(key=lambda row: (row["session_date"] or date.max, row["source_url"], row["outlook_id"]))
    levels.sort(key=lambda row: (row["session_date"], row["outlook_id"], row["side"], row["role"], row["ordinal"]))
    issues.sort(key=lambda row: (row["session_date"] or date.max, row["outlook_id"], row["code"], row["issue_id"]))
    return {name: pa.Table.from_pylist(rows, schema=schemas()[name])
            for name, rows in zip(TABLES, (outlooks, levels, issues, coverage))}


def _validate_tables(tables: dict[str, pa.Table], start: date, end: date) -> None:
    for name, schema in schemas().items():
        table = tables[name]
        if not table.schema.equals(schema, check_metadata=True):
            raise ValueError(f"unsupported {name} schema")
        if any(table[field.name].null_count for field in schema if not field.nullable):
            raise ValueError(f"null in required {name} field")
        if "available_at" in table.column_names and (table["available_at"].null_count != table.num_rows or set(table["timing_status"].to_pylist()) - {TIMING_STATUS}):
            raise ValueError("historical availability must remain unknown")
    outlooks = {row["outlook_id"]: row for row in tables["outlooks"].to_pylist()}
    if len(outlooks) != tables["outlooks"].num_rows:
        raise ValueError("duplicate outlook revision")
    groups = {}
    for row in tables["levels"].to_pylist():
        parent = outlooks.get(row["outlook_id"])
        if parent is None or any(row[key] != parent[key] for key in ("session_date", "product", "contract")):
            raise ValueError("orphaned or inconsistent level")
        if row["side"] not in {"bullish", "bearish"} or row["role"] not in {"trigger", "target"} or row["price_low"] > row["price_high"]:
            raise ValueError("invalid level side/role/bounds")
        groups.setdefault((row["outlook_id"], row["side"], row["role"]), []).append(row)
    for (identity, side, role), rows in groups.items():
        if sorted(row["ordinal"] for row in rows) != list(range(1, len(rows) + 1)) or (role == "trigger" and len(rows) != 1):
            raise ValueError("invalid branch ordinal inventory")
        if not groups.get((identity, side, "trigger")) or not groups.get((identity, side, "target")):
            raise ValueError("numeric branch lacks trigger or targets")
    issue_rows = tables["issues"].to_pylist()
    if len({row["issue_id"] for row in issue_rows}) != len(issue_rows):
        raise ValueError("duplicate extraction issue identity")
    for row in issue_rows:
        parent = outlooks.get(row["outlook_id"])
        if parent is None or row["session_date"] != parent["session_date"] or row["severity"] not in {"warning", "error"}:
            raise ValueError("orphaned or invalid extraction issue")
    issue_counts = Counter(row["outlook_id"] for row in issue_rows)
    for identity, row in outlooks.items():
        level_count = sum(len(rows) for key, rows in groups.items() if key[0] == identity)
        branches = sum(bool(groups.get((identity, side, "trigger"))) for side in ("bullish", "bearish"))
        if (row["level_count"] != level_count or row["parsed_branch_count"] != branches or row["issue_count"] != issue_counts[identity]
                or (row["extraction_status"] not in ({"failed", "no_explicit_plan"} if branches == 0 else {1: {"partial"}, 2: {"complete"}}[branches]))):
            raise ValueError("outlook extraction inventory is inconsistent")
    calendar = tables["coverage"].to_pylist()
    expected = {start + timedelta(days=index) for index in range((end - start).days + 1)}
    if {row["session_date"] for row in calendar} != expected or len(calendar) != len(expected):
        raise ValueError("calendar coverage is incomplete or duplicated")
    for row in calendar:
        posts = [post for post in outlooks.values() if post["session_date"] == row["session_date"]]
        statuses = Counter(post["extraction_status"] for post in posts)
        ledger = json.loads(row["ledger_json"])
        urls = {post["source_url"] for post in posts}
        if (row["post_count"] != len(posts) or row["level_count"] != sum(post["level_count"] for post in posts)
                or row["issue_count"] != sum(post["issue_count"] for post in posts)
                or row["complete_post_count"] != statuses["complete"] or row["partial_post_count"] != statuses["partial"]
                or row["failed_post_count"] != statuses["failed"] or row["non_outlook_post_count"] != statuses["no_explicit_plan"]
                or set(json.loads(row["post_urls_json"])) != urls or set(ledger["post_urls"]) != urls
                or set(json.loads(row["outlook_ids_json"])) != {post["outlook_id"] for post in posts}
                or ledger["session_date"] != row["session_date"].isoformat() or ledger["status"] != row["status"]):
            raise ValueError("calendar post/level counts do not match extracted data")


def _summary(tables: dict[str, pa.Table]) -> list[dict]:
    result = []
    levels = tables["levels"].to_pylist()
    max_targets = max((row["ordinal"] for row in levels if row["role"] == "target"), default=0)
    for post in tables["outlooks"].to_pylist():
        row = {key: post[key] for key in ("session_date", "contract", "source_url", "title", "outlook_id", "extraction_status",
            "issue_count", "available_at", "timing_status", "captured_at", "source_claimed_published", "source_claimed_updated")}
        for side in ("bullish", "bearish"):
            selected = [level for level in levels if level["outlook_id"] == post["outlook_id"] and level["side"] == side]
            trigger = next((level for level in selected if level["role"] == "trigger"), {})
            targets = [level for level in selected if level["role"] == "target"]
            row[f"{side}_scenario_text"] = post[f"{side}_scenario_text"]
            row[f"{side}_conditions"] = post[f"{side}_conditions"]
            for key in ("price_low", "price_high", "source_label"):
                row[f"{side}_trigger_{key}"] = trigger.get(key)
            row[f"{side}_targets"] = " | ".join(dict.fromkeys(level["source_text"] for level in targets))
            for ordinal in range(1, max_targets + 1):
                target = next((level for level in targets if level["ordinal"] == ordinal), {})
                for key in ("price_low", "price_high", "source_label"):
                    row[f"{side}_target_{ordinal}_{key}"] = target.get(key)
        result.append(row)
    return result


def _quality(tables: dict[str, pa.Table], start: date, end: date) -> bytes:
    posts = tables["outlooks"].to_pylist()
    statuses = Counter(post["extraction_status"] for post in posts)
    codes = Counter(row["code"] for row in tables["issues"].to_pylist())
    gaps = [row for row in tables["coverage"].to_pylist() if not row["post_count"]]
    dated_days = len({row["session_date"] for row in posts if row["session_date"] is not None})
    html_count = sum(bool(post["raw_html_path"]) for post in posts)
    atom_count = sum(bool(post["raw_atom_path"]) for post in posts)
    image_status = "partial" if codes["image_capture_failed"] else "no recorded image capture failures"
    text = (f"# Verniman chronological history {VERSION}\n\n"
            f"Declared interval: {start} through {end}, inclusive. Retained post revisions: {len(posts)}. "
            f"Complete: {statuses['complete']}; partial: {statuses['partial']}; failed numeric extraction: {statuses['failed']}. "
            f"Commentary posts without an explicit daily plan: {statuses['no_explicit_plan']}. "
            f"Distinct stated outlook dates: {dated_days}. Extracted numeric level rows: {tables['levels'].num_rows}. Calendar dates without observed posts: {len(gaps)}.\n\n"
            f"Retained-post source coverage: HTML {html_count}/{len(posts)}, Atom {atom_count}/{len(posts)}. Image capture coverage: {image_status}; recorded image failures: {codes['image_capture_failed']}. Each failure and its source URL/error are retained in issues.csv; complete plan-text extraction does not imply complete image retrieval.\n\n"
            "Every in-scope captured revision remains in outlooks and daily_summary.csv, including posts with no safe numeric extraction. Ambiguous branches yield no numeric rows; an independently valid other branch remains. issues.csv records each qualification and raw source branch. coverage.csv logs every calendar date; no_post_observed is a retrieval observation, not proof that a post never existed.\n\n"
            "Session dates follow the crawl's chronology, anchored to October 20, 2026, and each body's Outlook M/D. Delivery-contract year is retained separately. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets; singular two-endpoint ranges are zones.\n\n"
            "All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.\n\n"
            "Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0 evidence is preserved unchanged.\n\n"
            "| Issue code | Count |\n|---|---:|\n" + "\n".join(f"| {code} | {count} |" for code, count in sorted(codes.items())) + "\n")
    return text.encode()


def publish_release(crawl_manifest: Path | str, root: Path | str, request: Path | str) -> Path:
    """Publish retained captures and their ledger without fetching or overwriting."""
    root = Path(root).resolve()
    incoming, request_path = _contained(root, str(crawl_manifest)), _contained(root, str(request))
    incoming_record, request_record = _record(incoming, root), _record(request_path, root)
    crawl = json.loads(incoming.read_text())
    if crawl.get("source") != "verniman" or not isinstance(crawl.get("posts"), list) or not isinstance(crawl.get("files"), list):
        raise ValueError("expected chronological Verniman capture manifest")
    if crawl.get("traversal_reached_lower_boundary") is not True:
        raise ValueError("history publication requires a completed traversal to the declared lower boundary; preserve partial captures for inspection")
    start, end = _range(crawl)
    finals = [root / DATA_PATH, root / MANIFEST_PATH, root / SCHEMA_PATH, root / QUALITY_PATH]
    inventory_outputs = finals + [path.with_name(path.name + ".part") for path in finals[1:]]
    for path in inventory_outputs:
        check_absent(path, root)
    crawl_id = crawl.get("crawl_id", crawl.get("batch_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]+", crawl_id):
        raise ValueError("unsafe or missing crawl identity")
    stage = root / "data/staging/verniman" / f"{crawl_id}-v2"
    check_absent(stage, root)
    stage.mkdir(parents=True)
    (stage / "crawl_manifest.json").write_bytes(incoming.read_bytes())
    prepared = stage / "curated"
    prepared.mkdir()
    declared = provenance.publication_sources(Path(__file__), (
        "verniman_backfill.py", "verniman_capture.py", "verniman_levels.py", "provenance.py", "publication_safety.py", "paths.py"))
    retained = provenance.retain_sources(prepared / "provenance", declared, artifact_id=DATASET_ID, root=root)
    source_inventory = {}
    for record in crawl["files"]:
        _check_record(record, root)
        if record["path"] in source_inventory:
            if any(record.get(key) != source_inventory[record["path"]].get(key) for key in ("sha256", "bytes")):
                raise ValueError("conflicting capture file identities")
            continue
        source_inventory[record["path"]] = record
    for post in crawl["posts"]:
        for record in [post["html"], *([post["atom"]] if post.get("atom") else []), *post.get("images", [])]:
            if any(record.get(key) != source_inventory.get(record["path"], {}).get(key) for key in ("sha256", "bytes")):
                raise ValueError("post source is absent from declared capture inventory")
    tables = build_tables(crawl, root)
    _validate_tables(tables, start, end)
    for name, table in tables.items():
        pq.write_table(table, prepared / f"{name}.parquet", compression="zstd")
        _csv(prepared / f"{name}.csv", table.to_pylist(), table.column_names)
    summary = _summary(tables)
    _csv(prepared / "daily_summary.csv", summary, list(summary[0]) if summary else schemas()["outlooks"].names)
    (stage / "extracted.json").write_bytes(_json_bytes({name: table.to_pylist() for name, table in tables.items()}))
    schema_bytes, quality = _json_bytes(schema_document()), _quality(tables, start, end)
    (stage / "schema.json").write_bytes(schema_bytes)
    (stage / "quality.md").write_bytes(quality)
    files = []
    for path in sorted(prepared.rglob("*")):
        if path.is_file():
            record = _record(path, prepared)
            record["path"] = str(DATA_PATH / record["path"])
            files.append(record)
    files.extend({"path": str(path), "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
                 for path, payload in ((SCHEMA_PATH, schema_bytes), (QUALITY_PATH, quality)))
    manifest = {
        "dataset_id": DATASET_ID, "version": VERSION, "source": "verniman",
        "created_at": datetime.now(timezone.utc).isoformat(), "crawl_manifest": incoming_record, "request": request_record,
        "raw_files": list(source_inventory.values()), "files": files,
        "schema_path": str(SCHEMA_PATH), "quality_report_path": str(QUALITY_PATH),
        "tables": {name: {"path": str(DATA_PATH / f"{name}.parquet"), "rows": table.num_rows} for name, table in tables.items()},
        "requested_start_date": start.isoformat(), "anchor_session_date": end.isoformat(),
        "extraction_version": EXTRACTION_VERSION, "available_at_policy": TIMING_STATUS,
        "traversal_reached_lower_boundary": crawl.get("traversal_reached_lower_boundary", False),
        "stop_reason": crawl.get("stop_reason"),
        "provenance": {**provenance.git_version(root), "path": str(DATA_PATH / "provenance"), "retained": retained},
        "publication_invocation": {"entry_point": "abacus_bhishma.verniman_history", "working_directory": "publication_root",
            "arguments": {"root": ".", "crawl_manifest": incoming_record["path"], "request": request_record["path"]},
            "reconstruction_argv": ["./scripts/uv", "run", "--locked", "--no-sync", "python", "-m", "abacus_bhishma.verniman_history", "--root", ".", "--crawl-manifest", incoming_record["path"], "--request", request_record["path"]]},
        "known_limitations": ["Historical availability unverified; all available_at null.", "Coverage is observed retrieval coverage, not proof of original completeness.", "Ambiguous branches remain as raw text/issues and contribute no numeric levels."],
    }
    (stage / "manifest.json").write_bytes(_json_bytes(manifest))
    provenance.verify_retained_sources(prepared / "provenance", declared, retained)
    for record in [incoming_record, request_record, *source_inventory.values()]:
        _check_record(record, root)
    for path in inventory_outputs:
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
    """Read-only validation of a caller-selected manifest and declared artifacts."""
    root = Path(root).resolve()
    selected = Path(manifest_path)
    selected = selected if selected.is_absolute() else root / selected
    if selected.is_symlink() or selected.resolve() != selected.absolute():
        raise ValueError("manifest must be an explicit non-symlinked file")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256 or "") or provenance.sha256_file(selected) != expected_manifest_sha256:
        raise ValueError("manifest SHA256 does not match required pin")
    manifest = json.loads(selected.read_text())
    if manifest.get("dataset_id") != DATASET_ID or manifest.get("version") != VERSION or manifest.get("available_at_policy") != TIMING_STATUS or set(manifest.get("tables", {})) != set(TABLES):
        raise ValueError("unsupported history release identity or table inventory")
    required = {str(DATA_PATH / name) for name in (
        *[f"{table}.{suffix}" for table in TABLES for suffix in ("parquet", "csv")], "daily_summary.csv", "provenance/sources.json")}
    required.update((str(SCHEMA_PATH), str(QUALITY_PATH)))
    paths = [record.get("path") for record in manifest.get("files", [])]
    if len(paths) != len(set(paths)) or not required.issubset(paths):
        raise ValueError("incomplete or duplicated release artifact inventory")
    for record in [*manifest["files"], manifest["crawl_manifest"], manifest["request"], *manifest["raw_files"]]:
        _check_record(record, root, verify_bytes=verify_bytes)
    if json.loads((root / SCHEMA_PATH).read_text()) != schema_document():
        raise ValueError("unsupported history schema document")
    tables = {}
    for name, record in manifest["tables"].items():
        if record.get("path") != str(DATA_PATH / f"{name}.parquet"):
            raise ValueError("unsupported manifest table path")
        tables[name] = pq.ParquetFile(_contained(root, record["path"])).read()
        if tables[name].num_rows != record.get("rows"):
            raise ValueError("manifest row count differs from saved table")
    _validate_tables(tables, *_range(manifest))
    return manifest


def load_release(root: Path | str, manifest_path: Path | str, expected_manifest_sha256: str,
                 *, table: str = "outlooks", verify_bytes: bool = True) -> pa.Table:
    if table not in TABLES:
        raise ValueError(f"unsupported table: {table}")
    manifest = verify_release(root, manifest_path, expected_manifest_sha256, verify_bytes=verify_bytes)
    return pq.ParquetFile(_contained(Path(root).resolve(), manifest["tables"][table]["path"])).read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crawl-manifest", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    manifest = publish_release(args.crawl_manifest, resolve_publication_root(args.root), args.request)
    print(json.dumps({"manifest": str(manifest), "manifest_sha256": provenance.sha256_file(manifest)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
