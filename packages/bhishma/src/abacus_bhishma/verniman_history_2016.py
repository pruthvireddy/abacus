"""Publish the separate full-calendar 2016 Verniman source-level release.

The v1/v2/v3/v4/v5/v6/v7/v8/v9/v10/v11 publishers remain frozen. Stable endpoint, schema-shape, summary and
relationship-validation helpers are reused explicitly; this module owns the
2016 date/contract policy, release identity and no-overwrite publisher.

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
from html.parser import HTMLParser
from urllib.parse import urlsplit
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from . import provenance
from . import verniman_history as history_frozen_v2
from .verniman_history import _issue, _expand, _summary as _summary_frozen, _OUTLOOK
from .paths import resolve_publication_root
from .publication_safety import check_absent, check_path, write_new_bytes
from .verniman_levels import (
    ATOM, EASTERN, TIMING_STATUS, _check_record, _contained, _csv, _json_bytes,
    _record, _timestamp, content_text,
)

DATASET_ID = "verniman_daily_levels__12.0.0"
VERSION = "12.0.0"
EXTRACTION_VERSION = "verniman_history_2016_ab_v11"
DATA_PATH = Path("data/curated/external_levels/source=verniman/version=12.0.0")
MANIFEST_PATH = Path(f"catalog/datasets/{DATASET_ID}.json")
SCHEMA_PATH = Path(f"catalog/schemas/{DATASET_ID}.json")
QUALITY_PATH = Path(f"reports/quality/{DATASET_ID}.md")
TABLES = ("outlooks", "levels", "issues", "coverage")

_SOURCE_CONTRACT_TOKEN = re.compile(r"\bES[FGHJKMNQUVXZ]\d{1,2}\b", re.IGNORECASE)
_CONTRACT = re.compile(r"\b(ES[FGHJKMNQUVXZ](\d{2}|[67]))\b(?:\s*\(\s*[A-Za-z]+\s*(20\d{2})\s*\))?")

_NUMBER = r"\d{3,6}(?:\.\d{1,2})?"
_SUFFIX = r"\d{1,6}(?:\.\d{1,2})?"
_PRICE_SEQUENCE = rf"{_NUMBER}(?:\s*[-–/]\s*{_SUFFIX}|\s+and\s+{_NUMBER}|\s+{_NUMBER})*"
_LIS_LABEL = r"(?:LIS\s+(?:HVE\s+YVAH|HVE\s+YVAL|YVAL\s+HVE|YLOD\s+HVE|YHOD\s+HVE|YPOC\s+HVE|LVN\s+YVAH|YPOC-HVE|YVAL-HVE|HVE-YPOC|HVE-YVAL|HVE-YVAH|YLOD-HVE|ON-HVE|ON-POC|ON-VAH|ON-VAL|YHOD-HVE|YHOD-YVAH|YVAH-HVE|HVE|YVAH|YVAL|YPOC|YHOD|YLOD|ATH|LVN|POC)|HVE\s+LIS)"
_MARKET_LIMIT_LABEL = r"RTH\s+(?:Limit\s+Down|limit)"
_GROUP = re.compile(
    rf"(?:(?<![\w/-])|(?<=\d)(?=HVE\s+\d{{3,6}}\b)|(?<=\d-)(?=[A-Z][A-Z/-]*\s+\d{{3,6}}\b))(?P<prefix_label>{_LIS_LABEL}|{_MARKET_LIMIT_LABEL}|previous value area|Brexit SoC-PBT-GAP|CLVN-SoC Brexit|NFP SOC|POC-GAPs-LVN|HVE Tariffs SoC|Trump_XiSoC|Edge-LIS|Edge-LVN|Edge|edge|HGap|PrevATH|YVAl|HVE_PBT|HVE-1yrPOC|Trump-China Soc|Roll-GAP|(?:[A-Z][A-Z/-]*[- ])?So[cC](?:-[A-Z][A-Z/-]*)?|ONl|[A-Z][A-Z/-]*s?(?:\s+(?:Collar|collar|Sell|Buy))?)\s*"
    rf"(?:(?:support|resistance|magnet|zone|at|pending|exp|key level)\s+|\(\s*(?:ETH|ON)\s*\)\s+)?(?P<prefix_prices>{_PRICE_SEQUENCE})"
    rf"|(?<![\w./-])(?P<postfix_prices>{_PRICE_SEQUENCE})\s+(?P<postfix_label>support|resistance|magnet)\b"
)
_QUOTING = re.compile(r"\b(?P<tense>I['’]m|I\s+am|I\s+still|I['’]ll(?:\s+be)?|I\s+will(?:\s+be)?|I\s+start)\s+(?:still\s+)?quoting\s+(?:(?:old|new)\s+contract\s+)?(?:(?:Mar(?:ch)?|Jun(?:e)?|Sep(?:tember)?|Dec(?:ember)?)\s+(?:contract\s+)?)?/?(?P<contract>ES[FGHJKMNQUVXZ](?:\d{2}|[67]))\b", re.IGNORECASE)
_ACTION_WORDING = r"(?:try\s+to\s+)?(?:buy|sell|(?:be|become)\s+a\s+(?:buyer|seller))|try\s+to\s+lean\s+on"
_ACTION = re.compile(rf"\b({_ACTION_WORDING})\s+(?:(?:towards?|to|targeting)\s+|towards(?=HVE\s+\d{{3,6}}(?:\.\d{{1,2}})?\b))?(.+)$", re.IGNORECASE)


def _economic_action(source_action: str) -> str:
    """Map only explicit source buy/sell or nominal buyer/seller wording."""
    if re.fullmatch(r"try\s+to\s+lean\s+on", source_action, re.IGNORECASE):
        return "lean_on"
    if source_action.lower().endswith(("buy", "buyer")):
        return "buy"
    if source_action.lower().endswith(("sell", "seller")):
        return "sell"
    raise ValueError("unsupported source action")


def _source_branches(text: str) -> dict[str, str]:
    """Retain the source A/B/C letters independently of economic direction."""
    found = {}
    for label in ("A", "B", "C"):
        pattern = rf"(?ims)^\s*{label}[).:]\s*(.+?)(?=^\s*(?:[A-C][).:]|Notes?\s*(?:\d+\s*)?:|Reminder\s*:|Tips\s*:|Basics\s*:|Quotes\s*:|Notice\s*:|Rollover\s+(?:week|note|starts)\b|Expiration Week\b|When VIX climbs above\b|FOMC days are\b|SOC\s*:|Today's Economic Calendar\b|Disclaimer\s*:|Questions\b|Glossary of terms\b|Market Movers|Follow\s)|\Z)"
        matches = re.findall(pattern, text)
        if matches:
            found[label] = "\n".join(" ".join(value.split()) for value in matches)
    return found


def _branch_side(text: str) -> str:
    """Assign explicit directional scenarios, including qualified bearish lean-on wording."""
    action = _ACTION.search(text)
    if not action:
        raise ValueError("missing explicit buy/sell target clause")
    directions = re.findall(r"\b(above|below)\b", text[:action.start()], re.IGNORECASE)
    if len(directions) != 1:
        raise ValueError("source branch lacks exactly one explicit above/below direction")
    side = {("above", "buy"): "bullish", ("below", "sell"): "bearish", ("below", "lean_on"): "bearish"}.get((directions[0].lower(), _economic_action(action[1])))
    if side is None:
        raise ValueError("source direction/action pair is contradictory")
    if _economic_action(action[1]) == "lean_on":
        if (not re.search(r"\bwith\s+bearish\s+internals\s*[,;]?\s*$", text[:action.start()], re.IGNORECASE)
                or not re.match(rf"^{_NUMBER}\s+towards\s+", action[2], re.IGNORECASE)):
            raise ValueError("lean-on classification requires explicit below/bearish internals and one full leaning price before towards")
    conditions = re.search(r"\bwith\s+(.+)$", text[:action.start()], re.IGNORECASE)
    if conditions and re.search(r"\b" + ("bearish" if side == "bullish" else "bullish") + r"\b", conditions[1], re.IGNORECASE):
        raise ValueError("source confirmation wording contradicts the direction/action pair")
    return side


def _branch_mapping(text: str) -> tuple[dict[str, str], dict[str, str], list[dict]]:
    candidates: dict[str, list[tuple[str, str]]] = {"bullish": [], "bearish": []}
    problems = []
    for letter, branch in _source_branches(text).items():
        if len(re.findall(rf"(?m)^\s*{letter}[).:]", text)) != 1:
            problems.append({"code": "branch_duplicated", "description": f"Multiple source Plan {letter} branches have the same letter; no direction assignment or numeric extraction for that letter.", "source_text": branch})
            continue
        try:
            side = _branch_side(branch)
        except ValueError as error:
            problems.append({"code": "branch_direction_ambiguous", "description": f"Source Plan {letter}: {error}; retain source text without a numeric side assignment.", "source_text": branch})
            continue
        candidates[side].append((letter, branch))
    found, letters = {}, {}
    for side, branches in candidates.items():
        if len(branches) == 1:
            letters[side], found[side] = branches[0]
        elif len(branches) > 1:
            problems.append({"code": "multiple_source_branches_for_side", "description": "Multiple source A/B/C branches describe the same economic side; no unique branch can be selected for this side and numeric extraction is refused.", "side": side, "source_text": " | ".join(f"{letter}) {branch}" for letter, branch in branches)})
    return found, letters, problems


def _branches(text: str) -> dict[str, str]:
    """Expose only uniquely and consistently classified economic branches."""
    return _branch_mapping(text)[0]


def parse_level_groups(text: str) -> list[dict]:
    """Preserve supported source-labelled points, zones and ordered sequences."""
    result = []
    for match in _GROUP.finditer(text):
        label = match["prefix_label"] or match["postfix_label"]
        prices = match["prefix_prices"] or match["postfix_prices"]
        plural = label.endswith("s")
        if re.search(r"\band\b", prices) and not plural:
            raise ValueError(f"conjoined prices require an explicit plural source label: {match[0]}")
        if "/" in prices and (not plural or any(not re.fullmatch(_NUMBER, part)
                                               for part in re.split(r"\s*(?:[-–/]|\band\b)\s*", prices))):
            raise ValueError(f"slash-separated prices require an explicit plural label and full prices: {match[0]}")
        if re.search(r"\d\s+\d", prices) and not plural:
            raise ValueError(f"space-separated point lists require an explicit plural source label: {match[0]}")
        parts = re.split(r"\s*(?:[-–/]|\band\b)\s*|\s+", prices)
        if re.search(r"\d\s+\d", prices) and any(not re.fullmatch(_NUMBER, part) for part in parts):
            raise ValueError(f"space-separated plural points require full source prices: {match[0]}")
        full_sequence = len(parts) > 2 and not plural and all(len(part.split(".")[0]) >= 3 for part in parts)
        if len(parts) > 2 and not plural and not full_sequence:
            raise ValueError(f"ambiguous singular multi-price sequence: {match[0]}")
        if full_sequence:
            numbers = [Decimal(part).quantize(Decimal("0.01")) for part in parts]
        else:
            numbers = [_expand(parts[0], parts[0])]
            previous = parts[0]
            for part in parts[1:]:
                # The observed singular zone 4187-86.50 has an integer anchor
                # and a two-digit decimal suffix. Retain the same leading
                # digits as other abbreviated zones. Decimal anchors, shorter
                # suffixes and plural/multi-price decimal abbreviations remain
                # unsupported by this bounded policy.
                if (len(parts) == 2 and not plural
                        and re.fullmatch(r"\d{3,6}", previous)
                        and re.fullmatch(r"\d{2}\.\d{1,2}", part)):
                    number = _expand(previous[:-2] + part, previous)
                else:
                    number = _expand(part, previous)
                numbers.append(number)
                previous = format(number, ".0f") if number == number.to_integral_value() else str(number)
        if plural or full_sequence:
            ranges = [(value, value) for value in numbers]
            notation = "singular_full_point_sequence" if full_sequence else ("plural_point_sequence" if len(numbers) > 1 else "point")
        else:
            ranges = [(min(numbers), max(numbers))]
            notation = "zone" if len(numbers) > 1 else "point"
        result.extend({"source_label": label, "price_low": low, "price_high": high,
                       "source_text": match[0], "notation": notation} for low, high in ranges)
    unassigned = _GROUP.sub("", text)
    unassigned = re.sub(r"(?<!\w)-(?!\w)", "", unassigned)
    unassigned = re.sub(r"\(\s*\d{1,2}\s*[- ]\s*(?:weeks?|days?|hours?|minutes?)\b[^)]*\)", "", unassigned, flags=re.IGNORECASE)
    unassigned = re.sub(r"\(\s*VAR\s*\)", "", unassigned)
    if re.search(r"(?<![\w/-])[A-Z][A-Z/-]+\b", unassigned):
        raise ValueError(f"source label has no assigned explicit numeric level: {text}")
    if not result or re.search(r"\d", unassigned):
        raise ValueError(f"unassigned or unrecognised numeric level: {text}")
    return result


_TARGET_ANNOTATION = re.compile(r"(?:['‘]Look\s+(?:above|below)\s+and\s+fail|Failure\s+to\s+(?:take\s+out|breakdown))\b", re.IGNORECASE)
_EXECUTION_SUFFIX = rf"(?:{_NUMBER}|\d{{1,2}}|\d{{2}}\.\d{{1,2}})"
_EXECUTION_PRICES = rf"{_NUMBER}(?:\s*[-–]\s*{_EXECUTION_SUFFIX}){{0,2}}(?:\s+and\s+(?:edge\s+)?{_NUMBER})?"
_EXECUTION_REFERENCE = re.compile(rf"^(?P<qualifier>leaning\s+on|above|below|around)\s+(?P<prices>{_EXECUTION_PRICES})\s+(?:towards?|to|targeting)\s+(?P<targets>.+)$", re.IGNORECASE)


def _target_parts(text: str, side: str) -> tuple[str, str | None, str | None]:
    """Separate explicit target lists from retained execution/comment prose."""
    reference = _EXECUTION_REFERENCE.fullmatch(text)
    execution = None
    if reference:
        qualifier = reference["qualifier"].lower()
        if qualifier in {"above", "below"} and qualifier != ("above" if side == "bullish" else "below"):
            raise ValueError("ancillary execution direction contradicts the source branch")
        # Ancillary leaning references are retained as literal source text only.
        # Their bounded price expressions are never expanded into output bounds.
        # The conditional trigger and the labelled targets are parsed separately.
        if qualifier == "leaning on":
            if len(re.findall(r"[-–]|\band\b", reference["prices"], re.IGNORECASE)) > 2:
                raise ValueError("ancillary leaning reference supports at most three stated price components")
        else:
            parse_level_groups("HVE " + reference["prices"])
        execution = text[:reference.start("targets")].strip()
        text = reference["targets"]
    annotation = _TARGET_ANNOTATION.search(text)
    trailing = text[annotation.start():].strip() if annotation else None
    targets = text[:annotation.start()].rstrip(" .;,") if annotation else text
    return targets, execution, trailing


def parse_branch(text: str, side: str) -> tuple[list[dict], str | None]:
    # A previously captured branch spells the delimiter "buy towardsHVE 4810".
    # Accept that exact joined delimiter before an explicit HVE price; source
    # branch text and an issue retain the spelling. Other joined words do not
    # receive general whitespace repair or inferred labels.
    action = _ACTION.search(text)
    if not action:
        raise ValueError("missing explicit buy/sell target clause")
    prefix = text[:action.start()].rstrip(" ,;:-")
    direction = re.search(r"\b(above|below)\s+(.+)$", prefix, re.IGNORECASE)
    expected = {("above", "buy")} if side == "bullish" else {("below", "sell"), ("below", "lean_on")}
    if not direction or (direction[1].lower(), _economic_action(action[1])) not in expected:
        raise ValueError("branch direction/action does not unambiguously match its side")
    parts = re.split(r"\s+with\s+", direction[2], maxsplit=1, flags=re.IGNORECASE)
    trigger_text = parts[0].strip(" ,;")
    conditions = parts[1].strip(" ,;") if len(parts) > 1 else None
    if re.fullmatch(_NUMBER, trigger_text):
        point = Decimal(trigger_text).quantize(Decimal("0.01"))
        triggers = [{"source_label": None, "price_low": point, "price_high": point,
                     "source_text": trigger_text, "notation": "point"}]
    else:
        triggers = parse_level_groups(trigger_text)
    target_clause = action[2]
    if _economic_action(action[1]) == "lean_on":
        if _branch_side(text) != side:
            raise ValueError("lean-on source scenario contradicts its assigned side")
        target_clause = "leaning on " + target_clause
    targets_text, _, _ = _target_parts(target_clause, side)
    targets = parse_level_groups(targets_text)
    if len(triggers) != 1:
        raise ValueError("branch does not contain exactly one explicit trigger")
    rows = [{**value, "side": side, "role": role, "ordinal": ordinal,
             "conditions": conditions, "scenario_text": text}
            for role, values in (("trigger", triggers), ("target", targets))
            for ordinal, value in enumerate(values, 1)]
    return rows, conditions


def _operative_quotes(text: str) -> list[tuple[str, str]]:
    """Recognize present quoting or an affirmative future-tense quote today."""
    result = []
    for match in _QUOTING.finditer(text):
        sentence_start = max(text.rfind(separator, 0, match.start()) for separator in ("\n", ".", "!", "?")) + 1
        sentence_end = min((position for separator in ("\n", ".", "!", "?")
                            if (position := text.find(separator, match.end())) >= 0), default=len(text))
        sentence = text[sentence_start:sentence_end].strip()
        present = re.fullmatch(r"I['’]m|I\s+am|I\s+still", match["tense"], re.IGNORECASE)
        future_condition = re.search(r"\b(?:when|once|if|after|until|tomorrow)\b", text[match.end():sentence_end], re.IGNORECASE)
        if present or (not future_condition and re.search(r"\btoday\b", sentence, re.IGNORECASE)):
            result.append((match["contract"].upper(), sentence))
    return result


def _ambiguous_quotes(text: str) -> list[tuple[str, str]]:
    """Retain unqualified future quotes justified by current greater volume.

    This does not turn a future-tense statement into a verified today claim.
    A different heading makes assignment of the plan's prices uncertain.
    """
    result = []
    for match in _QUOTING.finditer(text):
        if not re.fullmatch(r"I['’]ll(?:\s+be)?|I\s+will(?:\s+be)?", match["tense"], re.IGNORECASE):
            continue
        sentence_start = max(text.rfind(separator, 0, match.start()) for separator in ("\n", ".", "!", "?")) + 1
        sentence_end = min((position for separator in ("\n", ".", "!", "?")
                            if (position := text.find(separator, match.end())) >= 0), default=len(text))
        sentence = text[sentence_start:sentence_end].strip()
        suffix = text[match.end():sentence_end]
        if re.search(r"\b(?:when|once|if|after|until|tomorrow)\b", suffix, re.IGNORECASE):
            continue
        if re.search(r"\btoday\b", sentence, re.IGNORECASE):
            continue  # The separately defined affirmative today policy applies.
        if re.search(r"\bas\s+volume\b.*\bis\s+greater\b", suffix, re.IGNORECASE):
            result.append((match["contract"].upper(), sentence))
    return result


def _intraday_contract_switches(text: str) -> list[tuple[str, str, str]]:
    """Classify bounded observed switch wording without inferring availability.

    Past after-bell switching, future after-bell switching and the source's
    present-tense equal-volume transition have different implications. These
    statements do not establish a pre-open publication or an execution time.
    """
    pattern = re.compile(r"\b(?P<tense>I\s+started|I\s+start|I['’]ll\s+start|I\s+will\s+start)\s+quoting\s+(?:new\s+(?:contract\s+)?)?/?(?P<contract>ES[FGHJKMNQUVXZ](?:\d{2}|[67]))\b", re.IGNORECASE)
    result = []
    for match in pattern.finditer(text):
        beginning = max(text.rfind(separator, 0, match.start()) for separator in ("\n", ".", "!", "?")) + 1
        ending = min((position for separator in ("\n", ".", "!", "?")
                      if (position := text.find(separator, match.end())) >= 0), default=len(text))
        sentence = text[beginning:ending].strip()
        suffix = text[match.end():ending]
        after_bell = re.search(r"\bafter\s+['‘\"]?(?:the\s+)?(?:NYSE\s+(?:Opening\s+)?Bell|Opening\s+Bell)\b", suffix, re.IGNORECASE)
        future_bell_wording = (re.search(r"\bsince\s+NYSE\s+opening\s+bell\b", suffix, re.IGNORECASE)
                               or re.search(r"\bafter\s+the\s+bell\s*,?\s*$", text[beginning:match.start()], re.IGNORECASE))
        if re.fullmatch(r"I\s+started", match["tense"], re.IGNORECASE) and after_bell:
            kind = "past_after_open"
        elif re.fullmatch(r"I['’]ll\s+start|I\s+will\s+start", match["tense"], re.IGNORECASE) and after_bell:
            kind = "future_after_open"
        elif re.fullmatch(r"I['’]ll\s+start|I\s+will\s+start", match["tense"], re.IGNORECASE) and future_bell_wording:
            kind = "future_opening_bell_wording"
        elif (re.fullmatch(r"I\s+start", match["tense"], re.IGNORECASE)
              and re.search(r"\bas\s+(?:March|June|September|December)\s+contract\s+increases\s+to\s+equal\s+volume\b", suffix, re.IGNORECASE)):
            kind = "equal_volume_transition"
        elif (re.fullmatch(r"I\s+start", match["tense"], re.IGNORECASE)
              and not re.search(r"\b(?:when|once|if|after|until|tomorrow)\b", suffix, re.IGNORECASE)):
            kind = "unqualified_present_transition"
        else:
            continue
        result.append((match["contract"].upper(), sentence, kind))
    return result



class _ArchivedPostTitle(HTMLParser):
    """Read the actual post heading, avoiding document-title or permalink guesses."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active, self.depth, self.parts, self.titles = False, 0, [], []
        self.link, self.links = None, []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "h3" and "post-title" in attributes.get("class", "").split():
            self.active, self.depth, self.parts, self.link = True, 1, [], None
        elif self.active:
            self.depth += 1
            if tag == "a" and self.link is None:
                self.link = attributes.get("href")

    def handle_endtag(self, tag):
        if self.active:
            self.depth -= 1
            if self.depth == 0:
                self.titles.append(" ".join("".join(self.parts).split()))
                self.links.append(self.link)
                self.active = False

    def handle_data(self, value):
        if self.active:
            self.parts.append(value)


def _archived_title(html: str) -> str | None:
    parser = _ArchivedPostTitle()
    parser.feed(html)
    return parser.titles[0] if len(parser.titles) == 1 else None



class _ArchivedPostScope(HTMLParser):
    """Scope a source post within retained multi-post/home HTML without replacing raw bytes."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth, self.parts, self.posts = 0, [], []

    def handle_starttag(self, tag, attrs):
        if tag == "div" and {"post", "hentry"}.issubset(set(dict(attrs).get("class", "").split())) and not self.depth:
            self.depth, self.parts = 1, [self.get_starttag_text()]
        elif self.depth:
            self.parts.append(self.get_starttag_text())
            if tag == "div":
                self.depth += 1

    def handle_startendtag(self, tag, attrs):
        if self.depth:
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.depth:
            self.parts.append(f"</{tag}>")
            if tag == "div":
                self.depth -= 1
                if not self.depth:
                    self.posts.append("".join(self.parts))

    def handle_data(self, value):
        if self.depth:
            self.parts.append(value)

    def handle_entityref(self, name):
        if self.depth:
            self.parts.append(f"&{name};")

    def handle_charref(self, name):
        if self.depth:
            self.parts.append(f"&#{name};")


def _selected_archived_html(html: str, selector: str | None) -> str:
    if not selector:
        return html
    parser = _ArchivedPostScope()
    parser.feed(html)
    matches = [fragment for fragment in parser.posts if re.search(rf"<a\s+name=['\"]{re.escape(str(selector).rsplit('post-', 1)[-1])}['\"]", fragment)]
    if len(matches) != 1:
        raise ValueError("archive HTML selector must resolve exactly one retained Blogger post")
    return matches[0]


def _is_archive_feed(post: dict) -> bool:
    return bool(post.get("source_entry_selector") and post.get("atom") and not post.get("html"))

def _stated_date(html: str, visible: str, archived: bool):
    body_date = _OUTLOOK.search(visible)
    title_date = _OUTLOOK.search(_archived_title(html) or "") if archived else None
    if body_date and title_date and body_date.groups() != title_date.groups():
        return None
    return body_date or title_date



def _validate_archived_input(post: dict, root: Path) -> None:
    address = post.get("archive_url")
    matched = re.fullmatch(r"https://web\.archive\.org/web/(\d{14})(?:id_)?/(https?://.+)", address or "")
    if not matched:
        raise ValueError("archive source requires an exact timestamped replay URL")
    observed = datetime.strptime(matched[1], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    if _timestamp(post.get("archive_observed_at")) != observed:
        raise ValueError("archive observation timestamp disagrees with the replay locator")
    def original_identity(value):
        parsed = urlsplit(value)
        if parsed.hostname != "verniman.blogspot.com" or parsed.scheme not in {"http", "https"}:
            raise ValueError("archive original must identify the Verniman blog")
        if parsed.port not in {None, 80, 443} or parsed.fragment:
            raise ValueError("archive original URL has unsupported authority or fragment")
        return parsed.hostname, parsed.path, parsed.query
    is_feed = _is_archive_feed(post)
    expected_original = post.get("archive_source_url") if is_feed or post.get("source_entry_selector") else post["url"]
    if not expected_original or original_identity(matched[2]) != original_identity(expected_original):
        raise ValueError("archive replay original URL disagrees with its original source locator")
    if is_feed:
        if post.get("html") is not None or not post.get("atom"):
            raise ValueError("archive feed entry must retain the full original XML response without a synthetic HTML source")
        record = post["atom"]
        document = ET.fromstring(_check_record(record, root).read_bytes())
        entries = [node for node in document.findall(ATOM + "entry") if node.findtext(ATOM + "id") == post["source_entry_selector"]]
        if document.tag != ATOM + "feed" or len(entries) != 1:
            raise ValueError("archive feed selector must resolve exactly one retained source entry")
        entry = entries[0]
        alternate = next((node.get("href") for node in entry.findall(ATOM + "link") if node.get("rel") == "alternate"), None)
        if not alternate or original_identity(alternate) != original_identity(post["url"]) or (entry.findtext(ATOM + "title") or "") != post.get("title"):
            raise ValueError("archive feed source URL/title differs from its retained entry")
        selected_id = (entry.findtext(ATOM + "id") or "").rsplit("post-", 1)[-1]
        source_id = str(post.get("source_post_id") or post.get("post_id") or "").rsplit("post-", 1)[-1]
        if selected_id != source_id:
            raise ValueError("archive feed source identity differs from its retained entry")
    else:
        if post.get("atom") is not None:
            raise ValueError("archived HTML cannot be combined with a current Atom body")
        record = post["html"]
        html = _selected_archived_html(_check_record(record, root).read_text(encoding="utf-8"), post.get("source_entry_selector"))
        title = _archived_title(html)
        if title is None or post.get("title", title) != title:
            raise ValueError("archive source requires one exact retained post title")
        title_parser = _ArchivedPostTitle()
        title_parser.feed(html)
        if not title_parser.links[0] or original_identity(title_parser.links[0]) != original_identity(post["url"]):
            raise ValueError("archive selected post URL differs from its actual source heading link")
        source_ids = re.findall(r"<div\s+class=['\"]post hentry['\"]>\s*<a\s+name=['\"](\d+)['\"]", html)
        source_id = str(post.get("source_post_id") or post.get("post_id") or "").rsplit("post-", 1)[-1]
        if len(source_ids) != 1 or source_id != source_ids[0]:
            raise ValueError("archive source identity differs from its retained HTML post ID")
    if record.get("url", record.get("requested_url", address)) != address:
        raise ValueError("archive request locator disagrees with its snapshot")
    if post.get("session_date") and observed.astimezone(EASTERN).date() < date.fromisoformat(post["session_date"]):
        raise ValueError("archive observation predates the assigned source session; review the year/date instead of forcing the requested year")
    if record.get("captured_at") and _timestamp(record["captured_at"]) < observed:
        raise ValueError("local archive retrieval cannot predate the archive observation")


def _unlettered_plan(text: str) -> str | None:
    matches = list(re.finditer(r"(?m)^(?:Trading\s+)?Plan:\s*(.+?)(?=\n(?:Value References|Economic Data|Notice|Note|Disclaimer|Questions)\b|\Z)", text, re.DOTALL))
    return matches[0][1].strip() if len(matches) == 1 else None


def _unlettered_scenarios(plan: str) -> dict[str, str]:
    """Preserve exact fragments; named participants/actions supply economic sides."""
    alternatives = re.search(r"(?P<one>sellers towards? .+?) or (?P<two>buyers towards? .+)$", plan)
    if alternatives:
        return {"bearish": alternatives["one"], "bullish": alternatives["two"]}
    unpriced_alternatives = re.search(r"(?P<one>[Bb]uyers? above towards? .+?) or (?P<two>sellers? below towards? .+)$", plan)
    if unpriced_alternatives:
        return {"bullish": unpriced_alternatives["one"], "bearish": unpriced_alternatives["two"]}
    split = re.search(r"\s+(?=[Ii]f (?:(?:buyers|sellers|this first idea|the first idea|that idea|bullish idea|bearish idea|that)\s+fails?\b|(?:[A-Z][A-Z/-]*\s+)?\d{3,6}(?:\.\d{1,2})?\s+fails?\b|market returns within value, I))", plan)
    if not split:
        candidates = list(re.finditer(r"\s+(?=[Ii]f\b)", plan))
        split = next((candidate for candidate in candidates if "first idea is" in plan[:candidate.start()] and re.search(r"(?:towards?|through)\s+[A-Z].*\d", plan[:candidate.start()])), None)
    first, second = (plan[:split.start()].strip(), plan[split.end():].strip()) if split else (plan, "")
    primary = re.search(r"first idea is (?:to be a (?:responsive )?(?P<nominal>buyer|seller)|wait and see if (?P<participant>buyers|sellers) can|(?:responsive )?(?P<action>buying|selling) (?:above|below|around|at)|wait for (?P<setups>bullish|bearish) setups (?:above|below))", first)
    reverse = re.search(r"I (?:become|am) a (buyer|seller) (?:towards?|to)", second)
    if not primary:
        return {}
    action = primary["nominal"] or ({"buyers": "buyer", "sellers": "seller"}[primary["participant"]] if primary["participant"] else {"buying": "buyer", "selling": "seller"}[primary["action"]] if primary["action"] else {"bullish": "buyer", "bearish": "seller"}[primary["setups"]])
    if reverse is None:
        return {"bullish" if action == "buyer" else "bearish": first}
    if action == reverse[1]:
        return {}
    return {"bullish" if action == "buyer" else "bearish": first,
            "bullish" if reverse[1] == "buyer" else "bearish": second}


def _parse_unlettered_scenario(text: str, side: str) -> tuple[list[dict], str]:
    participant, opposite, action = ("buyers", "sellers", "buyer") if side == "bullish" else ("sellers", "buyers", "seller")
    target_only = re.fullmatch(rf"(?:{participant}|{action})(?: {'above' if side == 'bullish' else 'below'})? (?:towards?|to) (.+?)[.]?", text, re.IGNORECASE)
    failure = re.fullmatch(rf"If (?P<subject>.+?) fails?(?: at (?P<at>.+?))?[,\.] I (?:become|am) a {action} (?:towards?|to) (?P<targets>.+?)[.]?", text, re.IGNORECASE)
    value_return = re.fullmatch(rf"If market returns within value, I (?:become|am) a {action} towards? (.+?)[.]?", text)
    interpretation, conditions, triggers = None, None, []
    if value_return:
        target_text, status, conditions = value_return[1], "targets_only", "If market returns within value"
    elif target_only:
        target_text, status = target_only[1], "targets_only"
        conditions = "wait and see what side shows more strength"
    elif failure:
        target_text = failure["targets"]
        conditions = text[:text.index("I ")].strip(" ,.")
        explicit = failure["at"] or (failure["subject"] if re.search(r"\d", failure["subject"]) else None)
        if explicit:
            if re.fullmatch(_NUMBER, explicit):
                value = Decimal(explicit).quantize(Decimal("0.01"))
                triggers = [{"source_label": None, "price_low": value, "price_high": value, "source_text": explicit, "notation": "point"}]
            else:
                triggers = parse_level_groups(explicit)
            interpretation, status = "explicit_failure_reference", "complete"
        elif failure["subject"].lower() in {opposite, "this first idea", "the first idea", "that", "that idea", "bullish idea", "bearish idea"}:
            status = "targets_only"
        else:
            raise ValueError("unsupported unlettered failure condition")
    else:
        direction = "above" if side == "bullish" else "below"
        positive = re.fullmatch(rf"It seems an open [a-z ]+ so first idea is wait and see if {participant} can (?:(?:hold|stay)(?: {direction})? (.+?) (?:and push (?:towards?|through)|towards?)|push {direction} (.+?) towards?) (.+?)[.]?", text)
        conditional_action = re.search(rf"first idea is (?:to be a (?:responsive )?{action}|wait for {'bullish' if side == 'bullish' else 'bearish'} setups) {direction} (?P<reference>.+?)(?:,? (?:looking for|using) RTH (?:profile )?setups)? towards? (?P<targets>.+?)[.]?$", text)
        explicit_action = re.search(rf"first idea is {'buying' if side == 'bullish' else 'selling'} {direction} (.+?) towards? (.+?)[.]?$", text)
        reference = re.search(rf"first idea is (?:to be a (?:responsive )?{action}|(?:responsive )?{'buying' if side == 'bullish' else 'selling'}) (?P<qualifier>at|around) (?P<reference>.+?) towards? (?P<targets>.+?)[.]?$", text)
        setup_only = re.search(rf"first idea is to be a {action} (?:(?P<setup_wording>(?:looking for|using) (?:RTH )?(?:profile )?setups) )?(?:towards?|to) (?P<targets>.+?)[.]?$", text)
        if positive or explicit_action or conditional_action:
            explicit = (positive[1] or positive[2]) if positive else explicit_action[1] if explicit_action else conditional_action["reference"]
            if re.fullmatch(_NUMBER, explicit):
                value = Decimal(explicit).quantize(Decimal("0.01"))
                triggers = [{"source_label": None, "price_low": value, "price_high": value, "source_text": explicit, "notation": "point"}]
            else:
                triggers = parse_level_groups(explicit)
            target_text, status, interpretation = positive[3] if positive else explicit_action[2] if explicit_action else conditional_action["targets"], "complete", "conditional_threshold"
            conditions = text[:text.index(explicit)].strip()
        elif reference:
            explicit = reference["reference"]
            if re.fullmatch(_NUMBER, explicit):
                value = Decimal(explicit).quantize(Decimal("0.01"))
                triggers = [{"source_label": None, "price_low": value, "price_high": value, "source_text": explicit, "notation": "point"}]
            else:
                triggers = parse_level_groups(explicit)
            target_text, status, interpretation = reference["targets"], "complete", "execution_reference"
            conditions = reference["qualifier"]
        elif setup_only:
            target_text, status, conditions = setup_only["targets"], "targets_only", setup_only["setup_wording"] or "explicit directional targets without a numeric trigger"
        else:
            raise ValueError("unsupported unlettered buyer/seller scenario wording")
    if status == "complete" and len(triggers) > 1:
        triggers, interpretation, status = [], None, "targets_only_ambiguous"
    if len(triggers) != (1 if status == "complete" else 0):
        raise ValueError("unlettered source scenario requires one explicit reference or no invented trigger")
    target_text = re.split(r"\s+Remember(?: this)? ATH\b", target_text, maxsplit=1)[0]
    targets = parse_level_groups(target_text.rstrip("."))
    return [{**value, "side": side, "role": role, "ordinal": ordinal,
             "conditions": conditions, "scenario_text": text,
             "trigger_interpretation": interpretation if role == "trigger" else None}
            for role, values in (("trigger", triggers), ("target", targets))
            for ordinal, value in enumerate(values, 1)], status


def schemas() -> dict[str, pa.Schema]:
    """Retain canonical v2 fields with a separately identified 2016 schema."""
    result = {name: schema.with_metadata({b"dataset_id": DATASET_ID.encode(), b"table": name.encode()})
              for name, schema in history_frozen_v2.schemas().items()}
    for name in ("source_plan_a_text", "source_plan_b_text", "source_plan_c_text", "bullish_source_plan_branch", "bearish_source_plan_branch"):
        result["outlooks"] = result["outlooks"].append(pa.field(name, pa.string(), nullable=True))
    result["levels"] = result["levels"].append(pa.field("source_plan_branch", pa.string(), nullable=True))
    result["levels"] = result["levels"].append(pa.field("trigger_interpretation", pa.string(), nullable=True))
    label_index = result["levels"].get_field_index("source_label")
    result["levels"] = result["levels"].set(label_index, pa.field("source_label", pa.string(), nullable=True))
    contract_index = result["levels"].get_field_index("contract")
    result["levels"] = result["levels"].set(contract_index, pa.field("contract", pa.string(), nullable=True))
    for name in ("source_plan_structure", "source_unlettered_plan_text", "bullish_extraction_status", "bearish_extraction_status", "archive_url", "archive_source_url", "source_format", "source_entry_selector"):
        result["outlooks"] = result["outlooks"].append(pa.field(name, pa.string(), nullable=True))
    result["outlooks"] = result["outlooks"].append(pa.field("archive_observed_at", pa.timestamp("us", tz="UTC"), nullable=True))
    for name in ("raw_html_path", "raw_html_sha256", "raw_html_captured_at"):
        index = result["outlooks"].get_field_index(name)
        result["outlooks"] = result["outlooks"].set(index, result["outlooks"].field(index).with_nullable(True))
    return result


def schema_document() -> dict:
    document = history_frozen_v2.schema_document()
    document.update({"dataset_id": DATASET_ID, "version": VERSION,
        "tables": {name: [{"name": item.name, "arrow_type": str(item.type), "nullable": item.nullable} for item in schema]
                   for name, schema in schemas().items()},
        "source_plan_branch": "Plan letters A/B/C are source labels, not fixed economic sides: A can be bearish and B bullish. A uniquely labelled source branch maps to bullish from exactly one above direction paired with explicit buy, be a buyer or become a buyer (optionally preceded by try to), or bearish from exactly one below direction paired with corresponding sell/seller wording. The separately qualified lean-on scenario also maps to bearish only from one below direction, explicit bearish internals, exact try to lean on plus one full numeric reference and a towards labelled-target clause; it does not assert an explicit sell order; contradictory explicit bullish/bearish confirmation wording also causes refusal. Duplicated letters, missing or inconsistent direction/action and multiple branches describing one side remain text/issues without invented numeric assignments. levels.source_plan_branch retains A/B/C; outlooks and daily_summary retain source_plan_a_text/source_plan_b_text/source_plan_c_text and bullish_source_plan_branch/bearish_source_plan_branch. The bounded below/bearish-internals/try-to-lean-on policy is separately documented and qualified without asserting an explicit sell order. Side-specific scenario and target columns follow the economic direction, not alphabetical position.",
        "session_date": "The 366-date calendar ends December 31, 2016. For archived sources, actual post-heading Outlook M/D or body Outlook M/D is cross-checked against the reviewed ledger; heading and body must agree when both exist. Qualified years require a separately retained archive/source-context review and never come solely from permalink or delivery contract. Undated sources retain null without numeric extraction.",
        "label_formats": "The exact observed mixed-case labels PrevATH and YVAl are retained with explicit source-spelling warnings; no generic case normalization is performed. Original source labels are retained. Exact Edge, edge, Edge-LIS, Edge-LVN, HGap and Trump_XiSoC spellings retain source case with explicit warnings. Supported syntax includes mixed-case Soc/SoC compounds (including FOMC Soc and YPOC-FOMC Soc), Roll-GAP, HVE-1yrPOC, HVE_PBT, nonstandard ONl and explicit postfix support/resistance/magnet labels. A full price immediately followed by HVE and an explicit price can delimit two labelled levels, retaining its source spelling with a warning. Explicit plural labels can introduce full point prices joined by and. Only the separately documented exact bare trigger point may omit its source label; unlabelled target prices and singular-labelled conjunctions remain unsupported.",
        "lis_label_modifier": "The observed LIS modifier followed by one of HVE, YVAH, YVAL, YPOC, YHOD, YLOD, ATH, LVN, POC, HVE YVAH, HVE YVAL, YVAL HVE, YLOD HVE, YPOC-HVE, YVAL-HVE, HVE-YPOC, HVE-YVAL, ON-HVE, ON-POC, ON-VAH, ON-VAL, YHOD-HVE, YHOD-YVAH, YVAH-HVE, HVE-YVAH, YLOD-HVE, YHOD HVE, YPOC HVE or LVN YVAH and one explicit price or supported zone is retained as one compound source label; no extra unpriced level is inferred. The observed reversed modifier HVE LIS also shares one explicit price and remains one source label. Bare LIS followed by a price is itself an explicit source label. Parenthesized (VAR) remains a nonnumeric annotation to the priced source level. A standalone SOC: definition paragraph terminates plan branch extraction; full body text stays retained.",
        "source_market_limit_labels": "The exact source labels RTH Limit Down and RTH limit followed by explicit prices are retained as labelled source-level targets with source_market_limit_claim warnings. These are source observations; no exchange limit calculation, validity, availability or execution eligibility is independently established.",
        "space_point_lists": "An explicit plural label such as HVEs may introduce full numeric point prices separated by spaces, optionally followed by and plus another full point. Each price retains source order and original group text with space_separated_plural_points warning. Singular-labelled space lists and abbreviated space prices remain refused.",
        "slash_point_lists": "Explicit plural labels may introduce slash-separated full numeric prices, e.g. PBTs 4448/4454. Each price is a separate ordered point, with the original group text and slash_separated_plural_points warning. Singular slash lists and abbreviated slash prices remain unsupported. Any otherwise unassigned uppercase source level label causes branch refusal rather than silently omitting a level with no numeric price.",
        "branch_boundaries": "A/B/C branches end at the next labelled branch, Note/Reminder/Tips/Basics/Quotes/Notice headings, Rollover week/note/starts, Expiration Week, When VIX climbs above or FOMC days are paragraph opening, Today's Economic Calendar, Disclaimer, Questions, Glossary of terms, Market Movers or Follow heading. The full source body remains retained.",
        "operative_contract_policy": "An explicit present-tense or affirmative-today statement quoting another contract conflicts with the header; preserve the post and both branches as text but refuse numeric extraction.",
        "ambiguous_contract_policy": "A future-tense quote of another contract justified by an affirmative present-volume-is-greater statement, without a conditional future term or explicit today, leaves the plan's operative contract ambiguous. Preserve the heading, quote and both branches but refuse numeric extraction with operative_contract_assignment_ambiguous; do not label the future-tense statement as a verified today claim.",
        "intraday_contract_switch_policy": "A past-tense I started quoting another contract after NYSE Opening Bell contradicts the retained source heading: both branches stay as text, with numeric extraction refused as past_contract_switch_header_conflict. An explicit future opening-bell switch (including preposed after the bell, future-tense since NYSE opening bell, and new /ESH20 after the Opening Bell) does not establish that contract as active in the captured plan: retain heading-based numeric extraction and future_intraday_contract_switch warning. Present I start quoting another contract, either as its month increases to equal volume or without a conditional future qualifier, leaves the transition phase ambiguous: refuse numeric extraction as operative_contract_assignment_ambiguous. None of these statements verifies pre-open availability or an execution timestamp.",
        "target_clause_spelling": "The observed joined delimiter towardsHVE followed by an explicit HVE price is recognized without changing source branch text; nonstandard_target_delimiter records the source spelling. Other joined target delimiters receive no inferred whitespace repair.",
        "decimal_zone_suffix": "A singular two-endpoint zone with a full integer anchor and a two-digit decimal suffix retains the anchor's leading digits: 4187-86.50 becomes bounds 4186.50 and 4187.00, with an abbreviated_decimal_zone warning. Decimal anchors, one-digit decimal suffixes and plural/multi-price decimal abbreviations remain unsupported.",
        "generic_contract_policy": "Exact generic /ES Value headings with no explicit contract anywhere retain ES prices with contract null and source_contract_unspecified warning. No delivery month/year is inferred from dates, images or adjacent posts. An explicit present source quoting claim may supply the exact contract with source_contract_from_explicit_quoting warning. Other mentioned contracts without a uniquely operative present claim cause numeric refusal; the first source token is never silently selected. Only a disposable compatibility projection receives a marker for the frozen validator; saved tables remain null.",
        "source_plan_c_text": "This release additionally retains original source Plan C text. C participates in the same explicit economic-direction mapping as A/B. Neutral or ambiguous letters remain text with issues; the source letter never determines side. levels.source_plan_branch may be A, B or C.",
        "source_lean_on_wording": "The exact try to lean on plus one full price and towards labelled targets can describe a bearish scenario only when its conditional prefix has one below direction and explicit bearish internals. This is a source scenario classification, not an inferred explicit sell order. The conditional threshold and auxiliary leaning reference remain separate. Missing, contradictory or non-bearish conditions, leaning zones/lists and malformed target clauses are refused. A source_lean_on_wording issue retains the exact action/target clause; trailing failed-auction commentary does not replace the conditional scenario direction.",
        "source_execution_reference": "After an explicit action, the source may state leaning on/above/below/around before a towards-delimited labelled target list. Ancillary leaning-on references additionally support one full first price followed by up to two explicit integer/full-price or two-digit decimal suffix components and an optional and full-price or and edge full-price component, with at most three stated price components overall. Such expressions remain literal source text without expanding or storing their prices. The conditional trigger and labelled targets remain independently strict; ancillary references never replace the trigger or become extra targets. Contradictory above/below references and malformed or longer expressions are refused.",
        "source_branch_annotation": "Exact Look above/below and fail or Failure to take out/breakdown explanatory tails terminate the numeric target list. Their full text remains in the scenario and source_branch_annotation issue, including referenced labels/prices/timing; no additional target or changed economic direction is inferred.",
        "single_digit_contract_policy": "The exact ES futures contract suffix 6 or 7 is supported only within the separately anchored 2016 collection. Its delivery year is 2016 or permitted late-year 2017 while the source contract (for example ESM6 or ESH7) remains literal, with single_digit_source_contract warning. A parenthesized full delivery year must agree modulo ten; the ordinary full two-digit contract policy is unchanged. No session year is inferred from the contract, and generic /ES Value headings without an explicit delivery contract follow the separately qualified nullable-contract policy.",
        "2016_source_annotations": "The exact mixed-case source label HVE Tariffs SoC followed by an explicit price remains one source label, with a nonstandard_source_label warning. The exact parenthesized ETH/ON annotation between a label and explicit price stays in source_text with a source_level_session_qualifier warning; no independent session eligibility is inferred. A trigger consisting of exactly one full numeric price is retained as a point with source_label null and an unlabelled_trigger_price warning. Bare numeric ranges/lists, unpriced source labels and singular-labelled target conjunctions remain unsupported. No label or price is borrowed from the opposite branch.",
        "unlabelled_trigger_price": "Only a trigger consisting of exactly one full 3–6-digit numeric point with an optional one- or two-digit decimal part may have source_label null. source_text is the exact source point, notation is point, and price_low equals price_high equals that literal price. The corresponding explicit unlabelled_trigger_price issue is required. Numeric target rows still require a source label; bare trigger zones/lists or other unassigned numeric text are refused. Validation cross-checks the null-label trigger against the parent scenario and exact bounds, and only a separate compatibility projection receives a temporary marker for the frozen relationship validator. Saved tables and summaries retain the null label without an inferred source label.",
        "observed_source_exhaustion": "A collection with traversal_reached_lower_boundary false may publish only when navigation exhausted normally and a pinned completion review plus independently captured complete feed reconcile the exact selected daily source IDs, URLs, normalized bodies and qualified dates, with zero unresolved candidate/content discrepancies. The exact next-index empty feed probe is verified from retained page bytes. Separately retained navigation context is fully accounted for. No 2015 boundary or full-year historical completeness is asserted; January–October dates without current source bodies remain observed gaps.",
        "contract_year_policy": "January–October dated 2016 requires delivery year 2016; November–December may use 2016 or 2017, preserving the stated contract. Conflicts remain raw with numeric extraction refused."})
    document.update({
        "source_origin": "Archive HTML and full historical Atom responses preserve exact Wayback replay URL, archive observation timestamp and current retrieval timestamps independently. Source URL remains the original blog URL; HTML post ID and actual title must agree with the selected archived capture. Current Atom bodies cannot be combined with an archived HTML revision. Empty historical timestamp elements remain null source claims. Every available_at remains null.",
        "archive_observed_at": "Archive capture observation time parsed and verified against the exact timestamped replay locator; distinct from historical publication, source update and local retrieval, and never used as available_at.",
        "unlettered_plan_policy": "Original prose Plan text is retained as source_unlettered_plan_text, with source_plan_structure unlettered and null source letter fields. Only bounded buyers/sellers can hold or push an explicit threshold and explicit labelled targets receives directional source-market-condition classification and source_market_condition_wording warning, without inventing an explicit order verb. Exact failure-to-buyer/seller target clauses with no numeric trigger retain target rows only, side extraction status targets_only and source_trigger_unstated. Multiple explicit primary references instead receive source_trigger_ambiguous and no selected pivot, while clear labelled directional targets remain retained. Exact at/around first-idea references preserve their distinct execution_reference interpretation; explicitly priced failure clauses preserve explicit_failure_reference. No opposing trigger or shared pivot is inferred. All exact fragment/price/role/ordinal inventories are independently re-parsed and validated against the unchanged source plan.",
        "trigger_interpretation": "Only trigger rows carry conditional_threshold, execution_reference or explicit_failure_reference. Target rows remain null. A conditional threshold follows explicit above/below or bounded participant hold/push conditions. An at/around first-idea reference is execution_reference; an explicit numeric source failure clause is explicit_failure_reference. No unstated pivot or opposite-side trigger is inferred. The viewing summary retains the corresponding side trigger interpretation.",
        "side_extraction_status": "Each side is complete, targets_only, failed or missing. parsed_branch_count counts complete sides with a trigger plus targets. A targets_only side preserves explicit directional targets without an unstated threshold; overall extraction remains partial whenever such rows exist. Saved calendar/level counts include every retained numeric row. Only a disposable frozen-validator projection omits targets_only rows and recomputes projected counts; saved outputs never receive artificial rows, letters or counts.",
        "source_plan_branch": "A/B/C retains the actual source letter for labelled plans. It is null only for separately qualified unlettered archive scenarios, never replaced with inferred letters. Original A/B/C text and side fields remain null where no letters appear.",
        "observed_archive_coverage": "All 366 calendar dates are logged. An archive-index candidate not retrieved is a capture limitation; a calendar date with no selected post is observed absence rather than proof no post ever existed. Indexed archive discovery is not full-year historical completeness, and current feed/navigation exhaustion is recorded separately. All selected source/date assignments require exact pinned review membership.",
    })
    return document


def _extract_labelled_post(post: dict, root: Path | str) -> tuple[dict, list[dict], list[dict]]:
    """Retain one dated capture and independently extract each safe branch."""
    root = Path(root).resolve()
    html_record = post.get("html")
    html = _check_record(html_record, root).read_text(encoding="utf-8") if html_record else ""
    if html_record and post.get("archive_url"):
        html = _selected_archived_html(html, post.get("source_entry_selector"))
    html_visible = content_text(html, post_only=True) if html_record else ""
    atom_record = post.get("atom")
    entry, atom_visible = None, None
    atom_problem = None
    if atom_record:
        xml = _check_record(atom_record, root).read_bytes()
        try:
            entry = ET.fromstring(xml)
            if _is_archive_feed(post):
                candidates = [node for node in entry.findall(ATOM + "entry") if node.findtext(ATOM + "id") == post["source_entry_selector"]]
                if entry.tag != ATOM + "feed" or len(candidates) != 1:
                    raise ValueError("archive feed selector must resolve exactly one original entry")
                entry = candidates[0]
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
    if post.get("archive_url"):
        source_id = source_id.rsplit("post-", 1)[-1]
    content_hash = hashlib.sha256(visible.encode()).hexdigest()
    revision = hashlib.sha256((source_id + "\n" + content_hash).encode()).hexdigest()
    stated = _stated_date(html, visible, bool(post.get("archive_url")))
    if _is_archive_feed(post):
        title_date = _OUTLOOK.search(entry.findtext(ATOM + "title") or "") if entry is not None else None
        body_date = _OUTLOOK.search(visible)
        stated = None if body_date and title_date and body_date.groups() != title_date.groups() else body_date or title_date
    contract_matches = list(_CONTRACT.finditer(visible))
    contract_headers = [match for match in contract_matches if not visible[:match.start()].rsplit("\n", 1)[-1].strip()]
    generic_contract_heading = re.search(r"(?m)^\s*/?ES\s+Value\s*:", visible) is not None
    contract = contract_headers[0] if contract_headers else (contract_matches[0] if contract_matches and not generic_contract_heading else None)
    generic_contract_claim_ambiguous = False
    if generic_contract_heading and not contract:
        current_quotes = {value for value, _ in _operative_quotes(visible)}
        if len(current_quotes) == 1:
            contract = next((match for match in contract_matches if match[1] in current_quotes), None)
        elif _SOURCE_CONTRACT_TOKEN.search(visible):
            generic_contract_claim_ambiguous = True
    inferred_date = date.fromisoformat(post["session_date"]) if post.get("session_date") else None
    html_stamp = _timestamp(html_record.get("captured_at", post["captured_at"])) if html_record else None
    atom_stamp = _timestamp(atom_record["captured_at"]) if atom_record else None
    source_branches = _source_branches(visible)
    found, source_letters, branch_problems = _branch_mapping(visible)
    row = {
        "outlook_id": revision, "source_post_id": str(source_id), "content_sha256": content_hash,
        "source_url": post["url"], "title": (entry.findtext(ATOM + "title") if entry is not None else post.get("title")) or "",
        "product": "ES" if contract or generic_contract_heading else None, "contract": contract[1] if contract else None,
        "body_contract_year": int(contract[3]) if contract and contract[3] else (2010 + int(contract[2]) if contract and len(contract[2]) == 1 else (2000 + int(contract[2]) if contract else None)),
        "session_date": inferred_date,
        "session_date_method": post.get("session_date_method", "crawl_ledger_anchored_year_plus_body_month_day"),
        "session_date_source_text": stated[0] if stated else None,
        "raw_html_path": html_record["path"] if html_record else None, "raw_html_sha256": html_record["sha256"] if html_record else None,
        "raw_atom_path": atom_record["path"] if atom_record else None,
        "raw_atom_sha256": atom_record["sha256"] if atom_record else None,
        "raw_html_captured_at": html_stamp, "raw_atom_captured_at": atom_stamp,
        "captured_at": max(stamp for stamp in (html_stamp, atom_stamp) if stamp is not None),
        "available_at": None, "timing_status": TIMING_STATUS,
        "body_text": visible, "bullish_scenario_text": found.get("bullish"), "bearish_scenario_text": found.get("bearish"),
        "source_plan_a_text": source_branches.get("A"), "source_plan_b_text": source_branches.get("B"), "source_plan_c_text": source_branches.get("C"),
        "bullish_source_plan_branch": source_letters.get("bullish"), "bearish_source_plan_branch": source_letters.get("bearish"),
        "bullish_conditions": None, "bearish_conditions": None,
        "extraction_version": EXTRACTION_VERSION, "source_agreement_status": "html_only" if atom_visible is None else "compared",
        "content_kind": "daily_outlook",
        "source_plan_structure": "labelled" if source_branches else "unlettered" if _unlettered_plan(visible) else "unsupported",
        "source_unlettered_plan_text": _unlettered_plan(visible),
        "bullish_extraction_status": "missing", "bearish_extraction_status": "missing",
        "source_format": "archived_atom_feed" if _is_archive_feed(post) else "archived_page_post" if post.get("source_entry_selector") else "archived_html" if post.get("archive_url") else "current_html_atom",
        "source_entry_selector": post.get("source_entry_selector"),
        "archive_url": post.get("archive_url"),
        "archive_source_url": post.get("archive_source_url"),
        "archive_observed_at": _timestamp(post["archive_observed_at"]) if post.get("archive_observed_at") else None,
        "source_year_status": "unresolved", "crawl_date_warnings_json": json.dumps(post.get("date_warnings", [])),
        "ledger_id": post.get("ledger_id", post["url"]),
        "extraction_status": "failed", "parsed_branch_count": 0, "level_count": 0, "issue_count": 0,
    }
    problems = [_issue(row, severity="error", scope="branch", **problem) for problem in branch_problems]
    if source_letters == {"bullish": "B", "bearish": "A"}:
        problems.append(_issue(row, "source_plan_letters_reversed", "The source labels bearish instructions A and bullish instructions B. Economic side follows the explicit direction/action while all original letters remain recorded.", source_text=" | ".join(f"{letter}) {source_branches[letter]}" for letter in ("A", "B"))))
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
    if inferred_date and inferred_date.weekday() >= 5:
        problems.append(_issue(row, "weekend_stated_outlook_date", "The source-stated anchored Outlook date falls on a calendar weekend. It is retained without reassignment; no exchange-session eligibility is inferred.", source_text=stated[0] if stated else None))
    if not contract:
        if generic_contract_heading:
            problems.append(_issue(row, "source_contract_unspecified", "The source explicitly identifies /ES Value but provides no safely assigned delivery contract. Source ES threshold and target prices remain unadjusted external claims with contract null; no front month or delivery year is inferred from dates, images or neighboring posts.", source_text="/ES Value:"))
            if generic_contract_claim_ambiguous:
                problems.append(_issue(row, "operative_contract_assignment_ambiguous", "A generic /ES Value heading and other contract mentions do not uniquely establish an operative contract. No first-token or front-month assignment is made; numeric extraction is refused.", source_text=" | ".join(match[0] for match in contract_matches), severity="error"))
                blocked = True
        else:
            problems.append(_issue(row, "contract_missing", "No unambiguous source ES contract was found; no numeric extraction.", severity="error"))
            blocked = True
    elif len({match[1] for match in contract_headers}) > 1:
        problems.append(_issue(row, "conflicting_contracts", "Multiple different ES contracts appear in source text; no numeric extraction.", source_text=" | ".join(match[0] for match in contract_matches), severity="error"))
        blocked = True
    elif contract[3] and int(contract[2]) != int(contract[3]) % (10 if len(contract[2]) == 1 else 100):
        problems.append(_issue(row, "contract_year_inconsistent", "Contract code and parenthesized delivery year disagree; no numeric extraction.", source_text=contract[0], severity="error"))
        blocked = True
    elif inferred_date and inferred_date.year == 2016 and ((inferred_date.month <= 10 and row["body_contract_year"] != 2016) or (inferred_date.month > 10 and row["body_contract_year"] not in {2016, 2017})):
        problems.append(_issue(row, "stale_source_year_conflict", "The anchored 2016 date conflicts with the permitted source delivery-contract year; numeric extraction refused and the post retained.", source_text=contract[0], severity="error"))
        row["source_year_status"] = "stale_source_year_conflict"
        blocked = True
    elif inferred_date and row["body_contract_year"] != inferred_date.year:
        problems.append(_issue(row, "contract_year_differs_from_session", "Delivery-contract year differs from inferred session year; session date was not changed.", source_text=contract[0]))
        row["source_year_status"] = "different_delivery_year_qualified"
    elif contract and inferred_date:
        row["source_year_status"] = "source_contract_year_matches_session"
    if contract and generic_contract_heading:
        problems.append(_issue(row, "source_contract_from_explicit_quoting", "The generic ES heading omits delivery month, while an explicit present-tense source quoting claim names the operative contract. The exact source contract is retained; no front month is inferred from neighboring posts or images.", source_text=" | ".join(sentence for quoted, sentence in _operative_quotes(visible) if quoted == contract[1])))
    if contract and len(contract[2]) == 1:
        problems.append(_issue(row, "single_digit_source_contract", "The source spells the ES delivery contract with a single 6 or 7 year digit. Under the independently anchored 2016 session chronology this denotes delivery year 2016 or permitted late-year 2017; the exact one-digit source contract is retained, and no session date is inferred from it.", source_text=contract[0]))
    if contract:
        for quoted_contract, source_sentence in _operative_quotes(visible):
            if quoted_contract != contract[1]:
                problems.append(_issue(row, "operative_contract_header_conflict",
                    "The source explicitly states it is currently quoting another contract, contradicting its contract heading; both branch texts and the heading are retained but numeric extraction is refused.",
                    source_text=source_sentence, severity="error"))
                blocked = True
        for quoted_contract, source_sentence in _ambiguous_quotes(visible):
            if quoted_contract != contract[1]:
                problems.append(_issue(row, "operative_contract_assignment_ambiguous",
                    "The source heading and an unqualified future-tense quoting statement name different contracts. The quote cites currently greater volume without a conditional future term; the operative contract for these prices remains ambiguous. Both branch texts, heading and quote are retained, but numeric extraction is refused.",
                    source_text=source_sentence, severity="error"))
                blocked = True
    if contract:
        for switched_contract, source_sentence, kind in _intraday_contract_switches(visible):
            if kind == "past_after_open":
                if switched_contract != contract[1]:
                    problems.append(_issue(row, "past_contract_switch_header_conflict",
                        "The source says it started quoting another contract after the NYSE opening bell while retaining a different contract heading. The captured body's contract assignment is inconsistent; both branch texts remain but numeric extraction is refused. The statement does not establish pre-open availability or an execution timestamp.",
                        source_text=source_sentence, severity="error"))
                    blocked = True
            elif kind in {"future_after_open", "future_opening_bell_wording"}:
                problems.append(_issue(row, "future_intraday_contract_switch",
                    "The source prospectively says it will start quoting this contract using an opening-bell qualifier. The plan retains its explicit heading contract; the exact future wording does not establish an active replacement contract, pre-open availability or an execution timestamp.",
                    source_text=source_sentence))
            elif kind == "unqualified_present_transition" and switched_contract != contract[1]:
                problems.append(_issue(row, "operative_contract_assignment_ambiguous",
                    "The source says I start quoting another contract without a conditional future qualifier while retaining a different heading. The transition phase and operative contract for the captured prices remain ambiguous; both branches and heading stay retained, but numeric extraction is refused. No pre-open availability or execution timestamp is established.",
                    source_text=source_sentence, severity="error"))
                blocked = True
            elif switched_contract != contract[1]:
                problems.append(_issue(row, "operative_contract_assignment_ambiguous",
                    "The source says I start quoting another contract as its delivery month increases to equal volume, while retaining a different heading. The transition phase and operative contract for the captured prices remain ambiguous; both branches and heading are retained but numeric extraction is refused. No active-switch or timing claim is inferred.",
                    source_text=source_sentence, severity="error"))
                blocked = True
    if contract and any(match[1] != contract[1] for match in contract_matches):
        problems.append(_issue(row, "other_contracts_mentioned", "Rollover commentary mentions other contracts; levels use the explicit contract heading.", source_text=" | ".join(dict.fromkeys(match[0] for match in contract_matches))))
    if entry is not None:
        alternate = next((node.get("href") for node in entry.findall(ATOM + "link") if node.get("rel") == "alternate"), None)
        alternate_equal = alternate == post["url"]
        if post.get("archive_url") and alternate:
            left, right = urlsplit(alternate), urlsplit(post["url"])
            alternate_equal = (left.hostname, left.path, left.query) == (right.hostname, right.path, right.query)
        if not alternate_equal:
            problems.append(_issue(row, "atom_url_mismatch", "HTML capture URL and Atom alternate URL disagree; no numeric extraction.", source_text=alternate, severity="error"))
            blocked = True
        html_date, html_contract = _OUTLOOK.search(html_visible), _CONTRACT.search(html_visible)
        html_generic = re.search(r"(?m)^\s*/?ES\s+Value\s*:", html_visible) is not None
        if generic_contract_heading and html_generic and contract is None:
            html_contract = None
        identity_mismatch = ((html_date.groups() if html_date else None) != (stated.groups() if stated else None)
                             or (contract[1] if contract else None) != (html_contract[1] if html_contract else None))
        if not html_record:
            identity_mismatch = False
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
    html_branches, html_source_letters, _ = _branch_mapping(html_visible)
    for side in ("bullish", "bearish"):
        branch = found.get(side)
        if branch:
            condition_match = re.search(rf"\bwith\s+(.+?)(?=[,;]?\s*\b(?:{_ACTION_WORDING})\b)", branch, re.IGNORECASE)
            row[f"{side}_conditions"] = condition_match[1].strip(" ,;") if condition_match else None
        if not branch:
            problems.append(_issue(row, "branch_missing", "No unique labelled plan branch was found.", side=side, scope="branch", severity="error"))
            continue
        letter = source_letters[side]
        if html_record and atom_visible is not None and (branch != html_branches.get(side) or letter != html_source_letters.get(side)):
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
        nominal_action = _ACTION.search(branch)
        lean_action = _economic_action(nominal_action[1]) == "lean_on"
        _, execution_reference, target_annotation = _target_parts(("leaning on " if lean_action else "") + nominal_action[2], side)
        if lean_action:
            problems.append(_issue(row, "source_lean_on_wording", "The source uses try to lean on rather than an explicit sell order. This bounded scenario is classified bearish only from its single below condition, explicit bearish internals, one full leaning price and towards target clause. The conditional threshold and separate leaning reference remain unchanged; no sell order or causal availability is asserted.", side=side, source_text=nominal_action[0]))
        if execution_reference:
            problems.append(_issue(row, "source_execution_reference", "The source gives this ancillary execution reference between its explicit action and target clause. It remains verbatim in the scenario and this issue; it is not substituted for the conditional trigger or counted as a target.", side=side, source_text=execution_reference))
        if target_annotation:
            problems.append(_issue(row, "source_branch_annotation", "The target list is followed by an explicit Look above/below and fail or Failure to take out/breakdown explanation. The full explanation remains in the scenario and this issue; its referenced labels, prices or timing are not additional target rows or a replacement branch direction.", side=side, source_text=target_annotation))
        if nominal_action and not lean_action and _economic_action(nominal_action[1]) in {"buy", "sell"} and re.search(r"\b(?:buyer|seller)\b", nominal_action[1], re.IGNORECASE):
            problems.append(_issue(row, "source_nominal_action_wording", "The source explicitly says be/become a buyer/seller. Economic side follows that action paired with one consistent above/below direction; original branch and condition wording remain retained.", side=side, source_text=nominal_action[1]))
        if re.search(r"\b(?:buy|sell)\s+towardsHVE\s+\d{3,6}(?:\.\d{1,2})?\b", branch, re.IGNORECASE):
            problems.append(_issue(row, "nonstandard_target_delimiter", "The source joins the target delimiter and HVE label as towardsHVE; the explicit HVE price is parsed while the original branch spelling is retained.", side=side, source_text=branch))
        if re.search(r"(?<![\d.])\d{3,6}(?:\.\d{1,2})?HVE\s+\d{3,6}(?:\.\d{1,2})?\b", branch):
            problems.append(_issue(row, "missing_level_separator", "The source omits whitespace between a full price and the next explicit HVE label. Each labelled price is retained separately with the original branch spelling.", side=side, source_text=branch))
        for item in selected:
            if item["source_label"] is None:
                problems.append(_issue(row, "unlabelled_trigger_price", "The source states one explicit numeric trigger point without a level label. The exact point is retained with source_label null; no HVE, YVAL or other label is inferred from this or the opposite branch.", side=side, source_text=item["source_text"]))
            if item["source_label"] is not None and re.fullmatch(_MARKET_LIMIT_LABEL, item["source_label"]):
                problems.append(_issue(row, "source_market_limit_claim", "The source labels this explicit price as an RTH market limit. It is retained as a source claim; no exchange-limit calculation, validity, historical availability or execution eligibility is established.", side=side, source_text=item["source_text"]))
            if item["source_label"] is not None and re.search(r"\d\s+\d", item["source_text"].split(item["source_label"], 1)[-1]):
                problems.append(_issue(row, "space_separated_plural_points", "An explicit plural source label introduces full numeric point prices separated by spaces. Each explicit price remains a separate ordered point with original group text; singular labels or abbreviated space lists remain refused.", side=side, source_text=item["source_text"]))
            if item["source_label"] is not None and "/" in item["source_text"].split(item["source_label"], 1)[-1]:
                problems.append(_issue(row, "slash_separated_plural_points", "The explicit plural source label introduces full prices separated by slashes. They remain distinct ordered point levels with the original group notation retained.", side=side, source_text=item["source_text"]))
            if item["source_label"] is not None and re.fullmatch(_LIS_LABEL, item["source_label"]):
                problems.append(_issue(row, "compound_lis_source_label", "The source's LIS modifier and following source label share one explicit numeric price. They are retained together as a compound source label without inferring another level.", side=side, source_text=item["source_text"]))
            if item["source_label"] in {"PrevATH", "YVAl", "HVE Tariffs SoC", "Trump_XiSoC", "Edge-LIS", "Edge-LVN", "Edge", "edge", "HGap"}:
                problems.append(_issue(row, "nonstandard_source_label", "The source uses this exact mixed-case label. Its source spelling and price are retained without case normalization or correction.", side=side, source_text=item["source_text"]))
            if re.search(r"\(\s*(?:ETH|ON)\s*\)", item["source_text"]):
                problems.append(_issue(row, "source_level_session_qualifier", "The source places an ETH or ON annotation before this explicit level. The original annotation stays in source_text; no independent session eligibility, availability or execution claim is inferred.", side=side, source_text=item["source_text"]))
            if item["notation"] == "zone" and re.search(r"\b\d{3,6}\s*[-–]\s*\d{2}\.\d{1,2}\b", item["source_text"]):
                problems.append(_issue(row, "abbreviated_decimal_zone", "The singular zone has a full integer anchor and an explicit two-digit decimal suffix. Bounds retain the anchor's leading digits; original source notation is retained without nearest-price or rollover inference.", side=side, source_text=item["source_text"]))
            if item["source_label"] == "ONl":
                problems.append(_issue(row, "nonstandard_source_label", "The source spells this label ONl with a lowercase final l; its exact case and price are retained without normalizing the label.", side=side, source_text=item["source_text"]))
            if item["notation"] == "singular_full_point_sequence":
                problems.append(_issue(row, "singular_multi_point_sequence", "Three or more full prices following a singular source label are retained as an explicit ordered point sequence, with the original notation.", side=side, source_text=item["source_text"]))
        levels.extend({**item, "outlook_id": revision, "session_date": inferred_date, "source_plan_branch": letter, "trigger_interpretation": "conditional_threshold" if item["role"] == "trigger" else None,
                       "product": row["product"], "contract": row["contract"],
                       "available_at": None, "timing_status": TIMING_STATUS} for item in selected)
    for side in ("bullish", "bearish"):
        row[f"{side}_extraction_status"] = "complete" if any(item["side"] == side for item in levels) else "failed" if found.get(side) else "missing"
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



def extract_post(post: dict, root: Path | str) -> tuple[dict, list[dict], list[dict]]:
    """Extract labelled plans or separately qualified archived unlettered scenarios."""
    if post.get("archive_url"):
        _validate_archived_input(post, Path(root).resolve())
    row, levels, problems = _extract_labelled_post(post, root)
    if post.get("image_revision_qualification"):
        qualification = post["image_revision_qualification"]
        problems.append(_issue(row, "source_image_revision_unverified", "Linked source images were retrieved from their current original hosts as an explicitly qualified fallback. Their byte identity at the historical archived observation is unverified; no chart-only numeric inference is made.", source_text=qualification if isinstance(qualification, str) else json.dumps(qualification, sort_keys=True)))
    if row["archive_url"]:
        problems = [item for item in problems if item["code"] != "atom_unavailable"]
        row["source_agreement_status"] = "archived_atom_feed_entry_only" if _is_archive_feed(post) else "archived_html_only"
        problems.append(_issue(row, "archive_source_only", "The historical page is retained from an archive snapshot; no current body is substituted or compared. Archive observation time is separate from source publication and does not establish premarket availability.", source_text=row["archive_url"]))
        if row["session_date_source_text"] and _OUTLOOK.search(row["body_text"]) is None:
            problems.append(_issue(row, "source_title_date", "The Outlook M/D is explicitly printed in the archived post heading. The independently reviewed archive context supplies the qualified year; no date is inferred from a permalink or image filename.", source_text=row["session_date_source_text"]))
    if row["archive_url"] and not row["source_unlettered_plan_text"] and not any(row[f"source_plan_{letter}_text"] for letter in ("a", "b", "c")) and _CONTRACT.search(row["body_text"]) is None:
        row.update(content_kind="commentary_without_explicit_daily_plan", extraction_status="no_explicit_plan", parsed_branch_count=0, level_count=0)
        problems = [item for item in problems if item["code"] not in {"contract_missing", "branch_missing"}]
        problems.append(_issue(row, "no_explicit_daily_plan", "This archived source has no explicit textual ES daily plan; its source title, images and other evidence remain retained without chart-only numeric inference."))
        row["issue_count"] = len({item["issue_id"] for item in problems})
        return row, [], problems
    if row["source_plan_structure"] != "unlettered" or not row["archive_url"]:
        row["issue_count"] = len({item["issue_id"] for item in problems})
        return row, levels, problems
    plan = row["source_unlettered_plan_text"]
    scenarios = _unlettered_scenarios(plan)
    problems = [item for item in problems if item["code"] not in {"branch_missing", "branch_direction_ambiguous"}]
    problems.append(_issue(row, "unlettered_source_plan", "The archived source states a prose Plan without A/B/C letters. Exact buyer/seller scenarios and original prose are retained without inventing source letters or buy/sell order wording.", source_text=plan))
    levels = []
    row["parsed_branch_count"] = 0
    blocked = any(item["severity"] == "error" for item in problems)
    for side in ("bullish", "bearish"):
        fragment = scenarios.get(side)
        row[f"{side}_scenario_text"] = fragment
        row[f"{side}_source_plan_branch"] = None
        if not fragment:
            row[f"{side}_extraction_status"] = "missing"
            problems.append(_issue(row, "unlettered_scenario_unresolved", "No bounded source buyer/seller scenario can be assigned to this economic side; full prose remains retained.", side=side, scope="branch", source_text=plan, severity="error"))
            continue
        row[f"{side}_extraction_status"] = "failed"
        if blocked:
            continue
        try:
            selected, status = _parse_unlettered_scenario(fragment, side)
        except ValueError as error:
            problems.append(_issue(row, "branch_parse_failed", str(error), side=side, scope="branch", source_text=fragment, severity="error"))
            continue
        row[f"{side}_extraction_status"] = "targets_only" if status.startswith("targets_only") else status
        row[f"{side}_conditions"] = selected[0]["conditions"]
        row["parsed_branch_count"] += status == "complete"
        if status == "targets_only_ambiguous":
            problems.append(_issue(row, "source_trigger_ambiguous", "The source gives multiple explicit primary references or prerequisites, so a unique numeric threshold cannot be assigned. Its unambiguous labelled directional targets remain targets_only; no pivot is selected or borrowed.", side=side, scope="branch", source_text=fragment))
        elif status == "targets_only":
            problems.append(_issue(row, "source_trigger_unstated", "The source explicitly names directional priced targets after the other side fails, but states no numeric threshold for that failure. Targets are retained without a trigger, borrowed pivot or invented source letter.", side=side, scope="branch", source_text=fragment))
        elif selected[0].get("trigger_interpretation") == "execution_reference":
            problems.append(_issue(row, "source_execution_reference_threshold", "The first idea gives an explicit at/around execution price reference, retained as a trigger-role source reference with interpretation execution_reference. It is not reinterpreted as an above/below conditional threshold or guaranteed fill.", side=side, scope="branch", source_text=fragment))
        elif selected[0].get("trigger_interpretation") == "explicit_failure_reference":
            problems.append(_issue(row, "source_explicit_failure_reference", "The failure clause itself explicitly supplies this numeric source reference. It is retained with interpretation explicit_failure_reference; no opposing threshold is borrowed.", side=side, scope="branch", source_text=fragment))
        else:
            problems.append(_issue(row, "source_market_condition_wording", "The source names buyers/sellers holding or pushing an explicit threshold toward explicit targets. Economic side follows that bounded source scenario; no explicit buy/sell order verb or source letter is invented.", side=side, scope="branch", source_text=fragment))
        if re.search(r"\s+Remember(?: this)? ATH\b", fragment):
            problems.append(_issue(row, "source_branch_annotation", "The source appends an explicit Remember ATH advisory after its target clause. The full advisory remains in the scenario; its prose and referenced prices are not additional target rows.", side=side, source_text=fragment[re.search(r"Remember(?: this)? ATH\b", fragment).start():]))
        for item in selected:
            if item["source_label"] in {"previous value area", "Brexit SoC-PBT-GAP", "CLVN-SoC Brexit", "NFP SOC", "POC-GAPs-LVN"}:
                problems.append(_issue(row, "nonstandard_source_label", "The source prints this exact narrative or mixed-case level label. Its spelling and explicit bounds are retained without invented label normalization.", side=side, source_text=item["source_text"]))
            if re.search(r"\d-[A-Z][A-Z/-]*\s+\d{3,6}", fragment):
                problems.append(_issue(row, "source_delimiter_warning", "The source joins a full price to another explicit labelled price with a hyphen. Both literal labelled groups are retained separately; the hyphen is a source delimiter and no missing label or price is inferred.", side=side, source_text=fragment))
            if item["role"] == "trigger" and item["source_label"] is None:
                problems.append(_issue(row, "unlabelled_trigger_price", "The source explicitly states this single full reference price without a level label. It remains an exact point with source_label null and its qualified trigger_interpretation; no source label is inferred.", side=side, source_text=item["source_text"]))
        levels.extend({**item, "outlook_id": row["outlook_id"], "session_date": row["session_date"], "source_plan_branch": None,
                       "product": row["product"], "contract": row["contract"], "available_at": None,
                       "timing_status": TIMING_STATUS} for item in selected)
    row["level_count"] = len(levels)
    row["extraction_status"] = "complete" if row["parsed_branch_count"] == 2 else "partial" if levels else "failed"
    problems = list({item["issue_id"]: item for item in problems}.values())
    row["issue_count"] = len(problems)
    return row, levels, problems

def _range(manifest: dict) -> tuple[date, date]:
    start = date.fromisoformat(manifest.get("requested_start_date", ""))
    end = date.fromisoformat(manifest.get("anchor_session_date", ""))
    if start != date(2016, 1, 1) or end != date(2016, 12, 31):
        raise ValueError("2016 release requires the explicit complete January 1–December 31, 2016 interval")
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



def _validate_actual_inventory(tables: dict[str, pa.Table], start: date, end: date) -> None:
    """Validate saved counts and target-only rows before any compatibility claims."""
    parents = {row["outlook_id"]: row for row in tables["outlooks"].to_pylist()}
    levels = tables["levels"].to_pylist()
    keys = [(row["outlook_id"], row["side"], row["role"], row["ordinal"]) for row in levels]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate numeric level identity")
    for value in levels:
        parent = parents.get(value["outlook_id"])
        if (parent is None or value["side"] not in {"bullish", "bearish"} or value["role"] not in {"trigger", "target"}
                or any(value[key] != parent[key] for key in ("session_date", "product", "contract"))
                or value["price_low"] > value["price_high"]):
            raise ValueError("orphaned or invalid saved numeric level")
        if (value["role"] == "target" and value["trigger_interpretation"] is not None
                or value["role"] == "trigger" and value["trigger_interpretation"] not in {"conditional_threshold", "execution_reference", "explicit_failure_reference"}):
            raise ValueError("numeric row has invalid trigger interpretation")
        if parent["source_plan_structure"] != "unlettered" and value["role"] == "trigger" and value["trigger_interpretation"] != "conditional_threshold":
            raise ValueError("labelled above/below trigger requires conditional threshold interpretation")
    for parent in parents.values():
        selected = [row for row in levels if row["outlook_id"] == parent["outlook_id"]]
        complete = sum(parent[f"{side}_extraction_status"] == "complete" for side in ("bullish", "bearish"))
        expected_status = "complete" if complete == 2 else "partial" if selected else "no_explicit_plan" if parent["extraction_status"] == "no_explicit_plan" else "failed"
        if parent["level_count"] != len(selected) or parent["parsed_branch_count"] != complete or parent["extraction_status"] != expected_status:
            raise ValueError("saved numeric and complete/targets-only side inventory disagrees")
        for side in ("bullish", "bearish"):
            rows = [row for row in selected if row["side"] == side]
            status = parent[f"{side}_extraction_status"]
            if status not in {"complete", "targets_only", "failed", "missing"}:
                raise ValueError("unsupported side extraction status")
            if rows and status not in {"complete", "targets_only"} or not rows and status in {"complete", "targets_only"}:
                raise ValueError("side extraction status disagrees with saved rows")
            if status == "targets_only" and (parent["source_plan_structure"] != "unlettered" or any(row["role"] != "target" for row in rows)):
                raise ValueError("targets-only side cannot acquire a trigger or source letter")
            for role in ("trigger", "target"):
                group = [row for row in rows if row["role"] == role]
                if sorted(row["ordinal"] for row in group) != list(range(1, len(group) + 1)):
                    raise ValueError("invalid saved side ordinal inventory")
    for day in tables["coverage"].to_pylist():
        posts = [row for row in parents.values() if row["session_date"] == day["session_date"]]
        statuses = Counter(row["extraction_status"] for row in posts)
        if (day["level_count"] != sum(row["level_count"] for row in posts)
                or any(day[field] != statuses[status] for field, status in (("complete_post_count", "complete"), ("partial_post_count", "partial"), ("failed_post_count", "failed"), ("non_outlook_post_count", "no_explicit_plan")))):
            raise ValueError("saved calendar numeric/status counts disagree")


def _validate_unlettered_parent(parent: dict, levels: list[dict], issues: list[dict]) -> None:
    plan = _unlettered_plan(parent["body_text"])
    if (not parent["archive_url"] or parent["archive_observed_at"] is None or plan is None
            or parent["source_unlettered_plan_text"] != plan
            or any(parent[f"source_plan_{letter}_text"] is not None for letter in ("a", "b", "c"))):
        raise ValueError("unlettered source requires unchanged archived prose without invented source letters")
    if not any(issue["outlook_id"] == parent["outlook_id"] and issue["code"] == "unlettered_source_plan" and issue["source_text"] == plan for issue in issues):
        raise ValueError("unlettered source plan requires its explicit qualification")
    scenarios = _unlettered_scenarios(plan)
    for side in ("bullish", "bearish"):
        fragment, status = scenarios.get(side), parent[f"{side}_extraction_status"]
        if parent[f"{side}_source_plan_branch"] is not None or parent[f"{side}_scenario_text"] != fragment:
            raise ValueError("unlettered scenario contradicts exact source fragment or invents a letter")
        selected = [row for row in levels if row["outlook_id"] == parent["outlook_id"] and row["side"] == side]
        if status not in {"complete", "targets_only"}:
            continue
        expected, expected_status = _parse_unlettered_scenario(fragment, side)
        fields = ("side", "role", "ordinal", "source_label", "source_text", "price_low", "price_high", "notation", "conditions", "scenario_text", "trigger_interpretation")
        if status != ("targets_only" if expected_status.startswith("targets_only") else expected_status) or sorted(tuple(row[field] for field in fields) for row in selected) != sorted(tuple(row[field] for field in fields) for row in expected):
            raise ValueError("unlettered numeric rows differ from literal source extraction")
        interpretation = expected[0]["trigger_interpretation"]
        code = "source_trigger_ambiguous" if expected_status == "targets_only_ambiguous" else "source_trigger_unstated" if status == "targets_only" else "source_execution_reference_threshold" if interpretation == "execution_reference" else "source_explicit_failure_reference" if interpretation == "explicit_failure_reference" else "source_market_condition_wording"
        if not any(issue["outlook_id"] == parent["outlook_id"] and issue["side"] == side and issue["code"] == code and issue["source_text"] == fragment for issue in issues):
            raise ValueError("unlettered side requires its precise source condition/trigger qualification")

def _validate_tables(tables: dict[str, pa.Table], start: date, end: date, *, root: Path | None = None) -> None:
    for name, schema in schemas().items():
        if name not in tables or not tables[name].schema.equals(schema, check_metadata=True):
            raise ValueError(f"unsupported {name} schema")
        if any(tables[name][field.name].null_count for field in schema if not field.nullable):
            raise ValueError(f"null in required {name} field")
        if "available_at" in tables[name].column_names and (tables[name]["available_at"].null_count != tables[name].num_rows or set(tables[name]["timing_status"].to_pylist()) - {TIMING_STATUS}):
            raise ValueError("historical availability must remain unknown")
    # Validate v12's inherited nullable-label exception before making a separate
    # projection for the frozen v2 required-label/schema validator. The saved
    # tables and frozen helpers are never mutated or given inferred labels.
    parents = {row["outlook_id"]: row for row in tables["outlooks"].to_pylist()}
    issue_rows = tables["issues"].to_pylist()
    for row in tables["levels"].to_pylist():
        if row["source_label"] is not None:
            continue
        source = row["source_text"]
        if (row["role"] != "trigger" or not isinstance(source, str) or not re.fullmatch(_NUMBER, source)
                or row["notation"] != "point" or row["ordinal"] != 1
                or row["price_low"] != row["price_high"]
                or row["price_low"] != Decimal(source)):
            raise ValueError("null source label requires one exact unlabelled trigger point")
        parent = parents.get(row["outlook_id"])
        if parent is None or row["side"] not in {"bullish", "bearish"}:
            raise ValueError("unlabelled trigger lacks a consistent source parent/side")
        try:
            selected, _ = (_parse_unlettered_scenario(parent[f"{row['side']}_scenario_text"], row["side"])
                           if parent["source_plan_structure"] == "unlettered" else parse_branch(parent[f"{row['side']}_scenario_text"], row["side"]))
        except (ValueError, TypeError) as error:
            raise ValueError("unlabelled trigger source scenario cannot be validated") from error
        trigger = next((value for value in selected if value["role"] == "trigger"), {})
        if any(trigger.get(key) != row[key] for key in ("source_label", "source_text", "price_low", "price_high", "notation")):
            raise ValueError("unlabelled trigger contradicts exact source scenario")
        if not any(issue["outlook_id"] == row["outlook_id"] and issue["side"] == row["side"]
                   and issue["code"] == "unlabelled_trigger_price" and issue["source_text"] == source
                   for issue in issue_rows):
            raise ValueError("unlabelled trigger requires its explicit source warning")
    for row in tables["levels"].to_pylist():
        if row["contract"] is not None:
            continue
        parent = parents.get(row["outlook_id"])
        if (parent is None or parent["contract"] is not None or parent["product"] != "ES"
                or parent["body_contract_year"] is not None or row["product"] != "ES"
                or not re.search(r"(?m)^\s*/?ES\s+Value\s*:", parent["body_text"])
                or _SOURCE_CONTRACT_TOKEN.search(parent["body_text"]) is not None
                or not any(issue["outlook_id"] == row["outlook_id"] and issue["code"] == "source_contract_unspecified" for issue in issue_rows)):
            raise ValueError("null delivery contract requires an explicit generic ES source parent and warning without other contract claims")
    # The frozen relationship validator is year-agnostic with an explicit
    # interval. Only this disposable compatibility projection receives a marker.
    relabelled = {name: table.select(history_frozen_v2.schemas()[name].names).replace_schema_metadata(history_frozen_v2.schemas()[name].metadata)
                  for name, table in tables.items()}
    actual_levels = tables["levels"].to_pylist()
    projected_levels = [row for row in relabelled["levels"].to_pylist()
                        if parents[row["outlook_id"]][f"{row['side']}_extraction_status"] != "targets_only"]
    projected_outlooks = relabelled["outlooks"].to_pylist()
    for row in projected_outlooks:
        if row["raw_html_path"] is None:
            row["raw_html_path"] = row["raw_atom_path"]
            row["raw_html_sha256"] = row["raw_atom_sha256"]
            row["raw_html_captured_at"] = row["raw_atom_captured_at"]
        if any(parents[row["outlook_id"]][f"{side}_extraction_status"] == "targets_only" for side in ("bullish", "bearish")):
            selected = [value for value in projected_levels if value["outlook_id"] == row["outlook_id"]]
            row["level_count"] = len(selected)
            row["parsed_branch_count"] = sum(value["role"] == "trigger" for value in selected)
            row["extraction_status"] = {0: "failed", 1: "partial", 2: "complete"}[row["parsed_branch_count"]]
        if row["contract"] is None and row["parsed_branch_count"]:
            row["contract"] = "__v12_unspecified_source_contract_validation_only__"
    relabelled["outlooks"] = pa.Table.from_pylist(projected_outlooks, schema=history_frozen_v2.schemas()["outlooks"])
    for row in projected_levels:
        if row["source_label"] is None:
            row["source_label"] = "__v12_unlabelled_trigger_validation_only__"
        if row["contract"] is None:
            row["contract"] = "__v12_unspecified_source_contract_validation_only__"
    relabelled["levels"] = pa.Table.from_pylist(projected_levels, schema=history_frozen_v2.schemas()["levels"])
    projected_calendar = relabelled["coverage"].to_pylist()
    for day in projected_calendar:
        posts = [row for row in projected_outlooks if row["session_date"] == day["session_date"]]
        statuses = Counter(row["extraction_status"] for row in posts)
        day.update(level_count=sum(row["level_count"] for row in posts),
                   complete_post_count=statuses["complete"], partial_post_count=statuses["partial"],
                   failed_post_count=statuses["failed"], non_outlook_post_count=statuses["no_explicit_plan"])
    relabelled["coverage"] = pa.Table.from_pylist(projected_calendar, schema=history_frozen_v2.schemas()["coverage"])
    history_frozen_v2._validate_tables(relabelled, start, end)
    _validate_actual_inventory(tables, start, end)
    for row in tables["outlooks"].to_pylist():
        if row["archive_url"]:
            if row["source_format"] not in {"archived_html", "archived_page_post", "archived_atom_feed"} or row["archive_observed_at"] is None:
                raise ValueError("archived source lacks its explicit format/observation qualification")
            feed_only = row["source_format"] == "archived_atom_feed"
            if (feed_only and (any(row[name] is not None for name in ("raw_html_path", "raw_html_sha256", "raw_html_captured_at")) or not row["source_entry_selector"] or not row["raw_atom_path"])
                    or not feed_only and (not row["raw_html_path"] or row["raw_atom_path"] is not None)):
                raise ValueError("archived source format conflicts with retained raw source types")
            if root is not None:
                record = {"path": row["raw_atom_path"] if feed_only else row["raw_html_path"], "sha256": row["raw_atom_sha256"] if feed_only else row["raw_html_sha256"], "captured_at": row["raw_atom_captured_at"].isoformat() if feed_only else row["raw_html_captured_at"].isoformat(), "url": row["archive_url"]}
                record["bytes"] = _contained(Path(root).resolve(), record["path"]).stat().st_size
                post = {"url": row["source_url"], "title": row["title"], "source_post_id": row["source_post_id"], "html": None if feed_only else record, "atom": record if feed_only else None, "archive_url": row["archive_url"], "archive_source_url": row["archive_source_url"], "archive_observed_at": row["archive_observed_at"].isoformat(), "source_entry_selector": row["source_entry_selector"], "captured_at": row["captured_at"].isoformat(), "session_date": row["session_date"].isoformat() if row["session_date"] else None, "session_date_method": row["session_date_method"]}
                source_row, _, _ = extract_post(post, root)
                for field in ("content_sha256", "outlook_id", "body_text", "source_claimed_published", "source_claimed_updated", "session_date_source_text"):
                    if row[field] != source_row[field]:
                        raise ValueError("saved archived source body/date/timestamp claims contradict retained raw bytes")
        elif row["raw_html_path"] is None:
            raise ValueError("nullable HTML sources are limited to qualified archived feed entries")
        if row["session_date"] is not None and not start <= row["session_date"] <= end:
            raise ValueError("out-of-range outlook session date")
        if row["extraction_version"] != EXTRACTION_VERSION:
            raise ValueError("unsupported extraction version")
        if row["parsed_branch_count"] and row["contract"] is not None:
            year = row["body_contract_year"]
            allowed = {2016} if row["session_date"].month <= 10 else {2016, 2017}
            if year not in allowed:
                raise ValueError("numeric levels conflict with 2016 delivery-contract policy")
        if row["source_plan_structure"] == "unlettered":
            _validate_unlettered_parent(row, actual_levels, issue_rows)
            continue
        found, letters, _ = _branch_mapping(row["body_text"])
        source_branches = _source_branches(row["body_text"])
        for letter in ("A", "B", "C"):
            if row[f"source_plan_{letter.lower()}_text"] != source_branches.get(letter):
                raise ValueError("retained source-letter branch text differs from the source body")
        for side in ("bullish", "bearish"):
            if row[f"{side}_source_plan_branch"] != letters.get(side) or row[f"{side}_scenario_text"] != found.get(side):
                raise ValueError("source letter or scenario contradicts explicit branch direction/action")
    for row in tables["levels"].to_pylist():
        parent = parents[row["outlook_id"]]
        if parent["source_plan_structure"] == "unlettered":
            if row["source_plan_branch"] is not None:
                raise ValueError("unlettered source cannot have an invented source branch")
            continue
        if (row["source_plan_branch"] not in {"A", "B", "C"}
                or row["source_plan_branch"] != parent[f"{row['side']}_source_plan_branch"]
                or row["scenario_text"] != parent[f"{row['side']}_scenario_text"]
                or _branch_side(row["scenario_text"]) != row["side"]):
            raise ValueError("numeric level source letter/side/scenario is inconsistent")


def _summary(tables: dict[str, pa.Table]) -> list[dict]:
    """Add original source letters/text to the frozen direction-based summary."""
    parents = {row["outlook_id"]: row for row in tables["outlooks"].to_pylist()}
    result = _summary_frozen(tables)
    for row in result:
        parent = parents[row["outlook_id"]]
        for side in ("bullish", "bearish"):
            row[f"{side}_trigger_interpretation"] = next((value["trigger_interpretation"] for value in tables["levels"].to_pylist() if value["outlook_id"] == parent["outlook_id"] and value["side"] == side and value["role"] == "trigger"), None)
        for name in ("source_plan_a_text", "source_plan_b_text", "source_plan_c_text", "bullish_source_plan_branch", "bearish_source_plan_branch", "source_plan_structure", "source_unlettered_plan_text", "bullish_extraction_status", "bearish_extraction_status", "archive_url", "archive_source_url", "archive_observed_at", "source_format", "source_entry_selector"):
            row[name] = parent[name]
    return result


def _quality(tables: dict[str, pa.Table], start: date, end: date, *, chronology_review: dict | None = None) -> bytes:
    posts = tables["outlooks"].to_pylist()
    statuses = Counter(post["extraction_status"] for post in posts)
    issue_rows = tables["issues"].to_pylist()
    codes = Counter(row["code"] for row in issue_rows)
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
            "Session dates follow separately reviewed archived source context, explicit post-heading or body Outlook M/D, and the complete 366-date 2016 calendar. Heading and body must agree where both exist; publication/update metadata, delivery contracts, permalinks and image filenames alone do not assign session years. Delivery-contract year is retained separately. Exact one-digit ES contract suffix 6 or 7 denotes delivery year 2016 or permitted late-year 2017 within this independently anchored collection, with the source spelling retained and a single_digit_source_contract warning; no session date is inferred from it. Generic /ES Value headings with no explicit delivery contract retain ES source prices with contract null and source_contract_unspecified warning; explicit present quoting claims may establish a source contract, while ambiguous mentions cause numeric refusal. Explicit today-quoting statements conflicting with the source contract heading cause numeric extraction to be refused, with both branches retained as text. An unqualified future-tense quote naming another contract and justified by present greater volume also causes refusal because operative contract assignment is ambiguous; it is not promoted to a verified today claim. The observed past-tense after-NYSE-bell switch to another contract also causes numeric refusal because the captured body conflicts with its heading. A prospective after-NYSE-bell switch retains the heading contract and a future_intraday_contract_switch warning; it is not treated as an active replacement. The observed present I start quoting another contract as its month increases to equal volume leaves the transition phase ambiguous and causes refusal. These source statements establish neither pre-open availability nor execution timestamps. Conditional future rollover wording remains separate. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets, including full point prices joined by and after an explicit plural label; singular two-endpoint ranges are zones. Numbered notes, Reminder/Tips/Basics/Quotes/Notice headings, explicit Rollover week/note/starts, Expiration Week, When VIX climbs above and FOMC reminder paragraph openings terminate plan branches. Explicit postfix support/resistance/magnet labels, Roll-GAP, FOMC Soc/YPOC-FOMC Soc, other supported mixed-case Soc/SoC compounds and HVE-1yrPOC preserve their source wording. The exact mixed-case labels PrevATH and YVAl retain their spelling with explicit warnings. Explicit plural labels can introduce slash-separated full numeric point lists, retaining their notation with a warning; singular or abbreviated slash lists remain unsupported. LIS plus an observed following HVE/YVAH/YVAL/YPOC/YHOD/ATH label sharing one price stays a single compound source label, with a compound_lis_source_label warning. Parenthesized VAR stays a nonnumeric annotation. Standalone SOC: definition paragraphs terminate branches. An otherwise unassigned uppercase source label with no numeric price causes branch refusal. Unlabelled point/zone conjunctions and missing numeric triggers remain unsupported and preserve the affected branch as text with an issue. The nonstandard ONl label retains its exact case and an explicit warning. The exact HVE_PBT label is retained; observed missing whitespace in towardsHVE and a full price immediately followed by HVE is parsed with explicit spelling warnings. A singular zone with an integer anchor and a two-digit decimal suffix retains the anchor's leading digits with an abbreviated_decimal_zone warning; other abbreviated decimal forms remain unsupported.\n\n"
            "All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.\n\n"
            "Plan A/B/C are source letters, not fixed economic sides. In this release economic side follows the explicit above+buy or below+sell direction/action pair, including exact be/become a buyer/seller and optional try to wording. The separately qualified below+bearish internals+try to lean on one full price+towards labelled-target scenario also maps to bearish without asserting an explicit sell order. Contradictory explicit confirmation wording is refused. The original A/B/C texts are retained in source_plan_a_text/source_plan_b_text/source_plan_c_text, and source_plan_branch on levels plus bullish_source_plan_branch/bearish_source_plan_branch on outlooks/summary preserve the original letter. Duplicate source letters, contradictory or missing directional instructions, and two branches for the same side remain raw with issues; no side is invented from alphabetical position. This release retains the additive source-letter fields and direction-assignment policy introduced in 8.0.0; all earlier releases remain byte-identical.\n\n"
            f"Source letters reversed relative to A-bullish/B-bearish shorthand: {codes['source_plan_letters_reversed']} retained posts. This describes source ordering and does not change economic direction or source text.\n\n"
            "The source phrases be a buyer, become a buyer, be a seller and become a seller are explicit directional actions, paired with exactly one consistent above/below direction. Source nominal wording remains in both plan text and a source_nominal_action_wording issue. Today's Economic Calendar and subsequent Disclaimer, Questions and Glossary headings terminate plan extraction before calendar numbers. Additional supported source syntax retains compound LIS labels sharing one explicit price or zone, including POC/LVN and the observed hyphenated or spaced HVE/value combinations. Exact RTH Limit Down and RTH limit targets remain qualified source_market_limit_claim observations, without independent exchange-limit or execution validation. An unqualified present I start quoting another contract while the heading names a different contract causes numeric refusal because transition phase is ambiguous. Prospective opening-bell switches, including preposed after the bell and future-tense since NYSE opening bell wording, retain the heading and a future switch warning. The exact mixed-case HVE Tariffs SoC label and parenthesized ETH/ON annotation retain source text and explicit warnings; no source correction or session eligibility is inferred. A single full numeric trigger point without a source label is retained with a null label and unlabelled_trigger_price warning. Bare ranges/lists and unpriced source labels remain unparsed; the opposite branch never supplies a missing label or price.\n\n"
            "2016 source attribution retains source_plan_c_text and preserves C as a possible numeric source letter, while neutral A/B/C branches remain verbatim with issues. Literal ESM6/ESU6/ESZ6 and late-year ESH7 codes retain their one-digit spelling; their delivery year is qualified by the separately anchored 2016 chronology and permitted delivery-year policy. Generic /ES Value bodies with no explicit contract anywhere retain source ES prices with contract null, product ES and source_contract_unspecified. A directly stated present quoting claim, including the exact observed I still quoting wording, can identify an exact delivery contract with source_contract_from_explicit_quoting; ambiguous generic contract mentions remain null and contribute no numeric rows. No delivery contract is inferred from source images, neighboring sessions or price levels. Nullable labels remain limited to exact unlabelled trigger points; nullable delivery contracts are validated only against generic source parents and required warnings.\n\n"
            "The source sometimes uses try to buy/sell or be/become a buyer/seller with an ancillary leaning on, above, below or around price/zone before towards. Those execution references stay in source_execution_reference issues and unchanged scenarios rather than replacing the initial conditional threshold or becoming extra targets. Exact quoted Look above/below and fail and Failure to take out/breakdown explanatory tails remain in source_branch_annotation, including their labels/prices/timing, rather than producing extra target rows. A narrowly supported try to lean on clause has no explicit sell order: its source scenario is classified bearish only with one conditional below direction, explicit bearish internals, one full leaning price and a towards labelled-target list, retaining source_lean_on_wording. Leaning zones/lists, contradictory or absent confirmations and ambiguous target prices remain refused. Explicit plural full point lists may use spaces, with space_separated_plural_points; singular or abbreviated space lists remain unsupported. Exact observed Edge/edge/Edge-LIS/Edge-LVN/HGap spellings and ON annotations retain source text and warnings.\n\n"
            "2016 ancillary leaning-on references support at most three stated source price components with one full first price, bounded integer/full-price or two-digit decimal suffix components, and an optional and full-price or and edge full-price component. They remain unchanged source text and source_execution_reference issues only; no ancillary price is expanded or stored as a threshold or target. The conditional trigger and towards-delimited labelled target list remain independently validated. Missing source target prices and ambiguous singular target lists remain refused. Undated daily bodies retain session_date null and no numeric rows; neither publication metadata, permalinks nor image dates supply a guessed session date.\n\n"
            "Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0 through 11.0.0 evidence is preserved unchanged.\n\n"
            "| Issue code | Count |\n|---|---:|\n" + "\n".join(f"| {code} | {count} |" for code, count in sorted(codes.items())) + "\n")
    published_claims = sum(post["source_claimed_published"] is not None for post in posts)
    updated_claims = sum(post["source_claimed_updated"] is not None for post in posts)
    image_only = sum(not post["body_text"] and post["extraction_status"] == "no_explicit_plan" for post in posts)
    context_only = sum(bool(post["body_text"]) and post["extraction_status"] == "no_explicit_plan" for post in posts)
    text += (f"Retained original source timestamp claims: published {published_claims}, updated {updated_claims}. "
             f"Image-only sources without a textual plan: {image_only}; context-only sources without a textual plan: {context_only}. "
             "Absent source claims remain null; archive observation and image filename clocks do not replace them.\n\n")
    text += ("## Archived source and unlettered-plan qualifications\n\n"
             "Archive HTML or full historical Atom feed responses retain their original archive_url, archive_observed_at and current retrieval clocks separately. The original post permalink remains source_url. A selected full-feed entry uses source_entry_selector and raw_atom_path pointing to the complete original XML; its raw_html fields remain null. A selected post on a retained home/archive page uses its exact Blogger post ID, heading permalink and scoped original body within the full raw HTML. Current Atom bodies are never grafted onto an archived HTML revision. Only actual historical entry publication/update claims populate source timestamp fields; empty source elements stay null. Archive observation does not establish publication or premarket availability.\n\n"
             "source_plan_structure distinguishes labelled and unlettered source plans. Unlettered plans retain the complete source_unlettered_plan_text and exact bullish/bearish fragments with null A/B/C letter fields; no source letter or order verb is invented. Bounded buyers/sellers holding or pushing an explicit threshold receives source_market_condition_wording. A first idea at/around a source reference receives source_execution_reference_threshold. trigger_interpretation distinguishes conditional_threshold, execution_reference and explicit_failure_reference; at/around prices are not reinterpreted as above/below pivots.\n\n"
             "Side extraction statuses expose complete, targets_only, failed and missing. Explicit directional targets without a numeric threshold remain targets_only with source_trigger_unstated and no trigger row or borrowed pivot. Multiple explicit primary references receive source_trigger_ambiguous while retaining only clear directional targets; no unique pivot is guessed. parsed_branch_count counts only complete sides; saved level/calendar counts include all targets-only rows. Overall extraction remains partial whenever target-only rows exist. Every saved numeric source fragment, bound, label, role, ordinal and interpretation is validated against the literal selected plan. The frozen validator sees only a disposable count-adjusted projection; published rows remain unchanged.\n\n"
             "Calendar gaps describe observed retrieval coverage, including indexed source capture failures where recorded, not proof of original historical absence or exchange-session eligibility. All 366 dates remain visible. Current-host image fallback bytes carry source_image_revision_unverified; their historical identity is unverified, and chart-only numbers are not extracted. All eleven earlier releases remain unchanged.\n\n")
    if chronology_review is not None:
        # A separately pinned review may qualify the raw chronology. Its text
        # describes this collection only; no earlier release's discontinuity or
        # local stop mechanism is assumed to have happened again.
        if not isinstance(chronology_review, dict):
            raise ValueError("chronology review must be an object")
        review_start = chronology_review.get("requested_start_date")
        review_end = chronology_review.get("anchor_session_date")
        if review_start != start.isoformat() or review_end != end.isoformat():
            raise ValueError("chronology review interval disagrees with release")
        if chronology_review.get("retained_post_count") != len(posts):
            raise ValueError("chronology review post count disagrees with retained rows")
        notes = chronology_review.get("notes")
        if not isinstance(notes, list) or not notes or not all(isinstance(note, str) and note.strip() for note in notes):
            raise ValueError("chronology review requires explicit nonempty review notes")
        text += "\n## Collection chronology review\n\n" + "\n\n".join(notes) + "\n"
        boundary = chronology_review.get("boundary")
        if boundary is not None:
            boundary_day = date.fromisoformat(boundary["reviewed_session_date"])
            if boundary_day >= start:
                raise ValueError("reviewed chronology boundary must precede the release interval")
            text += (f"\nThe reviewed older boundary [the {boundary_day} session]({boundary['url']}) "
                     f"is retained raw and excluded from the {start.year} tables.\n")
        text += ("\nThe original source captures and traversal ledger remain retained. "
                 "This publisher consumes the reviewed dates without recomputing years from source updates or delivery contracts. In this 2016 collection, source-claimed updates may be from later years; metadata years do not reassign retained body dates.\n")
    weekdays = [row["session_date"] for row in gaps if row["session_date"].weekday() < 5]
    text += (f"\n## Weekdays without a captured dated post ({len(weekdays)})\n\n"
             + (", ".join(day.isoformat() for day in weekdays) if weekdays else "None.")
             + "\n\nThese are observed calendar gaps. No holiday or exchange-session eligibility is inferred, and a gap is not proof that a post never existed.\n")

    def cell(value: object) -> str:
        return str(value).replace("\n", " ").replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")

    def source_link(post: dict) -> str:
        label = cell(post["title"] or post["source_url"])
        if post["archive_url"]:
            return f"[{label}]({post['archive_url']}) ([original]({post['source_url']}))"
        return f"[{label}]({post['source_url']})"

    if weekdays:
        text += "\n| Missing weekday | Nearest earlier captured date | Nearest later captured date |\n|---|---|---|\n"
        observed_dates = sorted({post["session_date"] for post in posts if post["session_date"] is not None})

        def neighboring_links(day: date | None) -> str:
            if day is None:
                return "No captured dated post in this interval"
            links = "; ".join(source_link(post)
                              for post in posts if post["session_date"] == day)
            return f"{day}: {links}"

        for missing in weekdays:
            before = max((day for day in observed_dates if day < missing), default=None)
            after = min((day for day in observed_dates if day > missing), default=None)
            text += f"| {missing} | {neighboring_links(before)} | {neighboring_links(after)} |\n"
        text += "\nNeighbor links identify the closest captured stated dates for review; they are not source posts for an absent date or proof of a historical absence. A retained post with refused numeric extraction still counts as a captured date.\n"

    undated = [post for post in posts if post["session_date"] is None]
    dated = sorted(post["session_date"] for post in posts if post["session_date"] is not None)
    text += f"\n## Source extent and undated daily plans ({len(undated)} posts)\n\n"
    if dated:
        text += f"Currently captured dated bodies span {dated[0]} through {dated[-1]}; this is source extent rather than a claim of full-year historical completeness. "
    text += "Undated daily bodies remain in outlooks and the viewing summary with null session_date and zero numeric levels. Source timestamp claims, permalinks and image dates do not supply missing body dates. Full-calendar gaps describe dated source observations only.\n"
    if undated:
        text += "\n| Source | Source-claimed published timestamp | Source-claimed updated timestamp | Qualification |\n|---|---|---|---|\n"
        for post in undated:
            link = source_link(post)
            text += f"| {link} | {cell(post['source_claimed_published'])} | {cell(post['source_claimed_updated'])} | Session date unresolved; numeric extraction refused. |\n"
        text += "\nThese are retained daily scenarios with missing body month/day, not additional dated sessions or duplicate-date cases. Their source timestamp claims remain unverified historical availability metadata.\n"

    weekend_posts = [post for post in posts if post["session_date"] and post["session_date"].weekday() >= 5]
    text += f"\n## Weekend stated dates ({len(weekend_posts)} posts)\n\n"
    if weekend_posts:
        text += "| Stated date | Source | Source-claimed updated timestamp |\n|---|---|---|\n"
        for post in weekend_posts:
            link = source_link(post)
            text += f"| {post['session_date']} | {link} | {cell(post['source_claimed_updated'] or 'Missing')} |\n"
        text += "\nThe source-stated dates remain unchanged even when update metadata names another day. Calendar weekends are descriptive; no exchange-session eligibility is inferred.\n"
    else:
        text += "None.\n"

    duplicate_days = sorted(day for day, count in Counter(post["session_date"] for post in posts if post["session_date"]).items() if count > 1)
    text += f"\n## Duplicate stated dates ({len(duplicate_days)} groups)\n\n"
    if duplicate_days:
        text += "| Stated date | Source posts |\n|---|---|\n"
        for day in duplicate_days:
            links = "; ".join(source_link(post)
                              for post in posts if post["session_date"] == day)
            text += f"| {day} | {links} |\n"
        text += "\nEach post revision retains its original stated date. No duplicate was silently reassigned or removed.\n"
    else:
        text += "None.\n"
    affected = [post for post in posts if post["extraction_status"] in {"partial", "failed"}]
    text += f"\n## Partial or failed numeric extraction ({len(affected)} posts)\n\n"
    if affected:
        text += "| Stated date | Status | Source | Qualifications retained |\n|---|---|---|---|\n"
        for post in affected:
            reasons = "; ".join(f"{item['code']}: {item['description']}"
                                for item in issue_rows if item["outlook_id"] == post["outlook_id"] and (item["severity"] == "error" or item["code"] in {"source_trigger_unstated", "source_trigger_ambiguous"}))
            link = source_link(post)
            text += f"| {post['session_date'] or 'Unresolved'} | {post['extraction_status']} | {link} | {cell(reasons)} |\n"
        text += "\nOriginal branch text and capture locators remain in outlooks, including every branch that yielded no numeric rows.\n"
    else:
        text += "None.\n"
    archived_posts = [post for post in posts if post["archive_url"]]
    if archived_posts:
        text += f"\n## Archived source index ({len(archived_posts)} posts)\n\n| Stated date | Source revision and original permalink | Source format |\n|---|---|---|\n"
        for post in archived_posts:
            text += f"| {post['session_date'] or 'Unresolved'} | {source_link(post)} | {post['source_format']} |\n"
    return text.encode()



def _validate_archive_completion(crawl: dict, root: Path) -> dict:
    """Require exact retained archive/source/date review membership without a completeness claim."""
    root = Path(root).resolve()
    if crawl.get("traversal_reached_lower_boundary") is not False or crawl.get("stop_reason") != "archive_index_capture_completed":
        raise ValueError("archive publication requires explicit observed archive retrieval completion without a dated lower boundary")
    inventory = {record.get("path"): record for record in crawl.get("files", [])}
    def checked(record, label):
        if (not isinstance(record, dict) or not isinstance(record.get("path"), str)
                or any(record.get(key) != inventory.get(record["path"], {}).get(key) for key in ("sha256", "bytes"))):
            raise ValueError(f"{label} must be pinned in the retained capture inventory")
        return json.loads(_check_record(record, root).read_text())
    review = checked(crawl.get("collection_completion_review"), "archive collection completion review")
    if (review.get("kind") != "verniman_2016_archive_observed_coverage"
            or review.get("requested_start_date") != "2016-01-01" or review.get("anchor_session_date") != "2016-12-31"
            or review.get("lower_boundary_observed") is not False or review.get("historical_full_year_completeness_claimed") is not False):
        raise ValueError("archive review must qualify observed coverage without a historical full-year claim")
    checked(review.get("archive_capture_manifest"), "archive capture manifest")
    checked(review.get("current_source_review"), "current source baseline review")
    selected, expected = {}, {}
    for post in crawl["posts"]:
        if not post.get("archive_url"):
            raise ValueError("archive release selected an unqualified current source")
        row, _, _ = extract_post(post, root)
        if row["outlook_id"] in selected:
            raise ValueError("archive selected revisions must be explicitly deduplicated before publication")
        selected[row["outlook_id"]] = row
    reviewed_posts = review.get("selected_posts")
    if not isinstance(reviewed_posts, list):
        raise ValueError("archive review requires exact selected source revision membership")
    for candidate in reviewed_posts:
        source_id = str(candidate.get("source_post_id", "")).rsplit("post-", 1)[-1]
        body_hash = candidate.get("content_sha256")
        if not source_id or not isinstance(body_hash, str):
            raise ValueError("archive reviewed candidate lacks exact source identity/body hash")
        identity = hashlib.sha256((source_id + "\n" + body_hash).encode()).hexdigest()
        if identity in expected:
            raise ValueError("archive review duplicates a selected source revision")
        expected[identity] = candidate
    if set(selected) != set(expected):
        raise ValueError("archive review membership differs from the selected exact source revisions")
    for identity, row in selected.items():
        candidate = expected[identity]
        for key in ("source_url", "raw_html_sha256", "raw_atom_sha256", "session_date_method"):
            if candidate.get(key) != row[key]:
                raise ValueError("archive source URL/capture identity/date method differs from independent review")
        if candidate.get("session_date") != (row["session_date"].isoformat() if row["session_date"] else None):
            raise ValueError("archive selected date differs from independent source review")
        evidence = candidate.get("year_evidence")
        if (not isinstance(evidence, dict) or evidence.get("year") != 2016
                or not isinstance(evidence.get("method"), str) or not evidence["method"].strip()
                or evidence.get("source_title") != row["title"]
                or _timestamp(evidence.get("archive_observed_at")) != row["archive_observed_at"]):
            raise ValueError("archive candidate lacks a consistent independently reviewed source-year qualification")
        excerpt = evidence.get("source_context_excerpt")
        if (not isinstance(excerpt, str) or (excerpt and excerpt not in row["body_text"])
                or not excerpt and not (not row["body_text"] and (evidence.get("image_only_source") is True or evidence.get("image_only_qualification") is True))):
            raise ValueError("archive year-context excerpt is absent or not literal selected source text")
        tokens = set(_SOURCE_CONTRACT_TOKEN.findall(row["body_text"]))
        if set(evidence.get("source_contract_tokens", [])) != tokens:
            raise ValueError("archive reviewed contract context differs from source tokens")
        records = evidence.get("source_records")
        selected_source = row["raw_html_path"] or row["raw_atom_path"]
        if not isinstance(records, list) or not any(record.get("path") == selected_source for record in records):
            raise ValueError("archive year review must pin its selected original source bytes")
        for record in records:
            if any(record.get(key) != inventory.get(record.get("path"), {}).get(key) for key in ("sha256", "bytes")):
                raise ValueError("archive source-year evidence is absent from retained inventory")
            _check_record(record, root)
    return review

def _validate_collection_completion(crawl: dict, root: Path) -> dict | None:
    """Permit honest current-source exhaustion only with independently pinned evidence."""
    if crawl.get("stop_reason") == "archive_index_capture_completed":
        return _validate_archive_completion(crawl, root)
    if crawl.get("traversal_reached_lower_boundary") is True:
        return None
    if crawl.get("traversal_reached_lower_boundary") is not False or crawl.get("stop_reason") != "navigation_exhausted":
        raise ValueError("history publication requires a completed traversal to the lower boundary or explicitly reviewed current-source exhaustion")
    review_record = crawl.get("collection_completion_review")
    if not isinstance(review_record, dict):
        raise ValueError("navigation exhaustion requires a pinned collection completion review")
    inventory = {record.get("path"): record for record in crawl.get("files", [])}

    def checked(record: dict, label: str) -> dict:
        if (not isinstance(record, dict) or not isinstance(record.get("path"), str)
                or any(record.get(key) != inventory.get(record["path"], {}).get(key) for key in ("sha256", "bytes"))):
            raise ValueError(f"{label} must be pinned in the retained capture inventory")
        return json.loads(_check_record(record, root).read_text())

    review = checked(review_record, "collection completion review")
    if (review.get("kind") != "verniman_2016_observed_source_exhaustion"
            or review.get("requested_start_date") != "2016-01-01" or review.get("anchor_session_date") != "2016-12-31"
            or review.get("lower_boundary_observed") is not False
            or review.get("historical_full_year_completeness_claimed") is not False):
        raise ValueError("completion review must explicitly qualify observed exhaustion without a lower-boundary or historical completeness claim")
    original = checked(review.get("original_crawl"), "original navigation crawl")
    feed = checked(review.get("feed_discovery"), "independent feed discovery")
    candidates = checked(review.get("candidate_body_review"), "independent candidate body review")
    traversal = original.get("traversal", [])
    if (original.get("source") != "verniman" or original.get("traversal_reached_lower_boundary") is not False
            or original.get("stop_reason") != "navigation_exhausted" or not traversal
            or traversal[-1].get("kind") != "post" or traversal[-1].get("status") != "captured"
            or traversal[-1].get("older_url") is not None
            or any(item.get("status") != "captured" for item in traversal)):
        raise ValueError("original navigation did not exhaust normally after captured posts")
    def same_pin(left: dict, right: dict) -> bool:
        return isinstance(left, dict) and isinstance(right, dict) and all(left.get(key) == right.get(key) for key in ("path", "sha256", "bytes"))

    if (feed.get("source") != "verniman" or feed.get("feed_exhaustion_confirmed") is not True
            or feed.get("chronological_navigation_exhausted") is not True
            or feed.get("chronological_stop_reason") != "navigation_exhausted"
            or feed.get("traversal_reached_lower_boundary") is not False
            or feed.get("older_2015_boundary_encountered") is not False
            or feed.get("observed_source_exhaustion_only") is not True
            or feed.get("chronological_final_record") != traversal[-1]
            or not same_pin(feed.get("chronological_crawl"), review["original_crawl"])
            or not same_pin(feed.get("independent_body_review"), review["candidate_body_review"])):
        raise ValueError("independent feed discovery does not attest the same observed navigation exhaustion")
    for key in ("independent_candidates_absent_from_2016_crawl", "independent_new_in_scope_candidates_absent_from_crawl",
                "unresolved_candidate_or_year_ambiguity_records", "candidate_body_date_chronology_disagreements",
                "candidate_ids_absent_from_crawl", "crawl_ids_absent_from_feed", "content_mismatches"):
        if feed.get(key) != []:
            raise ValueError("independent feed discovery has unresolved candidate or content discrepancies")
    if candidates.get("unresolved_candidate_or_year_ambiguity_records") != []:
        raise ValueError("independent candidate review has unresolved membership")
    # Read the retained feed pages themselves: booleans do not establish exhaustion.
    pages = {record["path"]: record for record in feed.get("pages", [])}
    ranges = feed.get("page_ranges", [])
    next_index, all_feed_ids, terminal_empty = 1, set(), False
    for index, page in enumerate(ranges):
        if page.get("start_index") != next_index or page.get("path") not in pages:
            raise ValueError("feed page ranges are not contiguous from index one")
        payload = checked(pages[page["path"]], "independent feed page")
        entries = payload.get("feed", {}).get("entry", [])
        if not isinstance(entries, list) or page.get("entry_count") != len(entries):
            raise ValueError("retained feed page count disagrees with discovery")
        if not entries:
            if index != len(ranges) - 1:
                raise ValueError("empty feed probe must terminate discovery")
            terminal_empty = True
            continue
        for entry in entries:
            identity = entry.get("id", {}).get("$t")
            if not isinstance(identity, str) or identity in all_feed_ids:
                raise ValueError("feed entries require unique source identities")
            all_feed_ids.add(identity)
        next_index += len(entries)
    if (not terminal_empty or len(pages) != len(ranges) or feed.get("terminal_next_index") != next_index
            or feed.get("feed_entry_count") != len(all_feed_ids) or feed.get("unique_feed_post_ids") != len(all_feed_ids)):
        raise ValueError("feed exhaustion requires an exact next-index empty probe and complete unique entry accounting")

    def identity(value: str) -> str:
        return str(value).rsplit("post-", 1)[-1]

    selected = {}
    for post in crawl["posts"]:
        row, _, _ = extract_post(post, root)
        key = identity(row["source_post_id"])
        if key in selected:
            raise ValueError("selected exhaustion candidates require unique source post identities")
        selected[key] = (row["source_url"], row["content_sha256"], row["session_date"].isoformat() if row["session_date"] else None)
    independently_reviewed = {str(candidate["source_post_id"]): candidate for candidate in candidates.get("candidates", [])}
    reconciled = {str(candidate["source_post_id"]): candidate for candidate in feed.get("candidates", [])}
    if (not selected or len(independently_reviewed) != candidates.get("candidate_count")
            or len(reconciled) != feed.get("candidate_count")
            or set(selected) != set(independently_reviewed) or set(selected) != set(reconciled)
            or set(feed.get("selected_candidate_ids", [])) != set(selected)
            or not set(selected).issubset({identity(value) for value in all_feed_ids})):
        raise ValueError("selected daily posts must exactly equal the independently reviewed and reconciled feed candidates")
    for key, (url, body_hash, day) in selected.items():
        independent, reconciled_post = independently_reviewed[key], reconciled[key]
        if (url != independent.get("source_url") or body_hash != independent.get("normalized_feed_body_sha256")
                or url != reconciled_post.get("source_url") or body_hash != reconciled_post.get("normalized_feed_body_sha256")
                or day != reconciled_post.get("chronology_assigned_session_date")):
            raise ValueError("selected candidate URL, source body or qualified date disagrees with independent evidence")
    original_urls = {post["url"] for post in original.get("posts", [])}
    selected_urls = {post["url"] for post in crawl["posts"]}
    context = crawl.get("excluded_context_posts")
    if (not isinstance(context, list) or {post.get("url") for post in context} != original_urls - selected_urls
            or len(context) != feed.get("linked_context_record_count")
            or any(post.get("session_date") is not None for post in context)
            or {post.get("source_url") for post in feed.get("linked_context_records", [])} != original_urls - selected_urls):
        raise ValueError("excluded navigation context must remain separately and completely accounted for")
    for post in context:
        _check_record(post["html"], root)
        if post.get("atom"):
            _check_record(post["atom"], root)
    return review


def publish_release(crawl_manifest: Path | str, root: Path | str, request: Path | str) -> Path:
    """Publish retained captures and their ledger without fetching or overwriting."""
    root = Path(root).resolve()
    incoming, request_path = _contained(root, str(crawl_manifest)), _contained(root, str(request))
    incoming_record, request_record = _record(incoming, root), _record(request_path, root)
    crawl = json.loads(incoming.read_text())
    if crawl.get("source") != "verniman" or not isinstance(crawl.get("posts"), list) or not isinstance(crawl.get("files"), list):
        raise ValueError("expected chronological Verniman capture manifest")
    completion_review = _validate_collection_completion(crawl, root)
    start, end = _range(crawl)
    finals = [root / DATA_PATH, root / MANIFEST_PATH, root / SCHEMA_PATH, root / QUALITY_PATH]
    inventory_outputs = finals + [path.with_name(path.name + ".part") for path in finals[1:]]
    for path in inventory_outputs:
        check_absent(path, root)
    crawl_id = crawl.get("crawl_id", crawl.get("batch_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]+", crawl_id):
        raise ValueError("unsafe or missing crawl identity")
    stage = root / "data/staging/verniman" / f"{crawl_id}-v12"
    check_absent(stage, root)
    stage.mkdir(parents=True)
    (stage / "crawl_manifest.json").write_bytes(incoming.read_bytes())
    prepared = stage / "curated"
    prepared.mkdir()
    # Frozen prior-year producers are retained for independent feed-grammar
    # and chronology audit helpers. They are not runtime dependencies.
    declared = provenance.publication_sources(Path(__file__), (
        "verniman_history.py", "verniman_history_2017.py", "verniman_history_2018.py", "verniman_history_2019.py", "verniman_history_2020.py", "verniman_history_2021.py", "verniman_history_2022.py", "verniman_history_2023.py", "verniman_backfill.py", "verniman_capture.py", "verniman_levels.py", "provenance.py", "publication_safety.py", "paths.py"))
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
        for record in [*([post["html"]] if post.get("html") else []), *([post["atom"]] if post.get("atom") else []), *post.get("images", [])]:
            if any(record.get(key) != source_inventory.get(record["path"], {}).get(key) for key in ("sha256", "bytes")):
                raise ValueError("post source is absent from declared capture inventory")
    tables = build_tables(crawl, root)
    _validate_tables(tables, start, end, root=root)
    for name, table in tables.items():
        pq.write_table(table, prepared / f"{name}.parquet", compression="zstd")
        _csv(prepared / f"{name}.csv", table.to_pylist(), table.column_names)
    summary = _summary(tables)
    _csv(prepared / "daily_summary.csv", summary, list(summary[0]) if summary else schemas()["outlooks"].names)
    (stage / "extracted.json").write_bytes(_json_bytes({name: table.to_pylist() for name, table in tables.items()}))
    review_record = crawl.get("chronology_review")
    chronology_review = json.loads(_check_record(review_record, root).read_text()) if review_record else None
    schema_bytes, quality = _json_bytes(schema_document()), _quality(tables, start, end, chronology_review=chronology_review)
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
        "collection_completion_review": crawl.get("collection_completion_review"),
        "observed_source_exhaustion_only": completion_review is not None,
        "observed_archive_coverage_only": crawl.get("stop_reason") == "archive_index_capture_completed",
        "historical_full_year_completeness_claimed": False,
        "provenance": {**provenance.git_version(root), "path": str(DATA_PATH / "provenance"), "retained": retained},
        "publication_invocation": {"entry_point": "abacus_bhishma.verniman_history_2016", "working_directory": "publication_root",
            "arguments": {"root": ".", "crawl_manifest": incoming_record["path"], "request": request_record["path"]},
            "reconstruction_argv": ["./scripts/uv", "run", "--locked", "--no-sync", "python", "-m", "abacus_bhishma.verniman_history_2016", "--root", ".", "--crawl-manifest", incoming_record["path"], "--request", request_record["path"]]},
        "preserved_prior_releases": ["verniman_daily_levels__1.0.0", "verniman_daily_levels__2.0.0", "verniman_daily_levels__3.0.0", "verniman_daily_levels__4.0.0", "verniman_daily_levels__5.0.0", "verniman_daily_levels__6.0.0", "verniman_daily_levels__7.0.0", "verniman_daily_levels__8.0.0", "verniman_daily_levels__9.0.0", "verniman_daily_levels__10.0.0", "verniman_daily_levels__11.0.0"],
        "known_limitations": ["Historical availability unverified; all available_at null.", "Coverage is observed archive/current-source retrieval coverage, not proof of original completeness or a dated lower boundary.", "Unlettered scenarios can retain explicit targets without a source-stated threshold; side statuses and trigger interpretation preserve this qualification.", "Ambiguous or unlabelled targets remain as source text/issues without guessed numeric levels."],
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
    _validate_tables(tables, *_range(manifest), root=root if verify_bytes else None)
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
