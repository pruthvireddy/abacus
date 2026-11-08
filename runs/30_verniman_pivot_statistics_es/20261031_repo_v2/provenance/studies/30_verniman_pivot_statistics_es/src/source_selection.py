"""Source-only interpretation of legacy paired thresholds; no market prices."""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import re

from source_audit import audit_sources

_CONDITION = re.compile(r"^\s*if\s+(?:the\s+)?market\s+(?:moves?|remains?|trades?|stays?)\s+(above|below)\b", re.I)
_NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:,\d{3})*(?:\.\d+)?(?![A-Za-z0-9])")
_CONFLICT = re.compile(r"\b(?:not|unless|fails?|failure|around|lean|rejects?)\b", re.I)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def review_threshold(row: dict) -> dict:
    """Accept only the first literal price of an explicit above/below condition.

    Additional source internals/delta conditions are retained as source method
    qualifications; this study analyzes the supplied divider, not those rules.
    A blank legacy enum alone is never treated as proof of a threshold.
    """
    text = str(row.get("scenario_text") or "")
    result = {"side": row.get("side"), "scenario_sha256": _hash(text),
              "source_text_sha256": _hash(str(row.get("source_text") or "")),
              "source_interpretation": row.get("trigger_interpretation") or None,
              "decision": "unresolved", "rule": "literal_paired_conditional_threshold/v1"}
    declared = row.get("trigger_interpretation")
    if declared not in (None, "", "conditional_threshold"):
        return {**result, "reason": "explicit_incompatible_source_interpretation"}
    match = _CONDITION.match(text)
    expected = "above" if row.get("side") == "bullish" else "below" if row.get("side") == "bearish" else None
    if match is None or match[1].lower() != expected:
        return {**result, "reason": "missing_explicit_directional_condition"}
    after = text[match.end():]
    number = _NUMBER.search(after)
    if number is None or _CONFLICT.search(after[:number.end()]):
        return {**result, "reason": "ambiguous_or_missing_first_threshold"}
    try:
        price = Decimal(number[0].replace(",", ""))
        lower, upper = Decimal(str(row["price_low"])), Decimal(str(row["price_high"]))
    except (InvalidOperation, KeyError, ValueError):
        return {**result, "reason": "invalid_numeric_threshold"}
    if not price.is_finite() or price <= 0 or price != lower or lower != upper:
        return {**result, "reason": "first_threshold_does_not_match_saved_single_price"}
    # 'Above 100-110' is a zone even if a faulty extraction saved only100.
    suffix = after[number.end():].lstrip()
    if re.match(r"^(?:-|–|—|/|to\b)\s*\d", suffix, re.I):
        return {**result, "reason": "source_threshold_is_range"}
    return {**result, "decision": "conditional_threshold_supported", "reason": None,
            "qualification": "Source internals/delta qualifiers are not modeled as study filters."}


def select_sources(tables: dict, *, start_date="2020-01-01", end_date="2026-10-30") -> dict:
    """Freeze an auditable retrospective cohort before any outcome execution."""
    inventory = audit_sources(**tables, start_date=start_date, end_date=end_date)
    parents = {row["outlook_id"]: row for row in tables["outlooks"]}
    children = defaultdict(list)
    for row in tables["levels"]:
        if row.get("role") == "trigger":
            children[row["outlook_id"]].append(row)
    decisions, candidates = [], []
    for row in inventory["outlook_audit"]:
        if not row["in_requested_range"]:
            continue
        reviews = [review_threshold(child) for child in children[row["outlook_id"]]]
        resolved = (row["source_shape"] == "single_shared_trigger" and len(reviews) == 2
                    and all(child["decision"] == "conditional_threshold_supported" for child in reviews))
        reasons = list(row["review_reasons"])
        if resolved:
            reasons = [reason for reason in reasons if reason != "pivot_semantics_unreviewed"]
        elif "pivot_semantics_unreviewed" not in reasons:
            reasons.append("conditional_threshold_source_review_unresolved")
        eligible = not reasons and resolved
        decision = {"candidate_id": row["candidate_id"], "session_date": row["session_date"],
                    "contract": row["normalized_contract"], "source_shape": row["source_shape"],
                    "source_semantics_resolved": resolved, "retrospective_source_eligible": eligible,
                    "exclusion_reasons": sorted(set(reasons)), "threshold_reviews": reviews,
                    "source_revision_id": row["source_revision_id"],
                    "available_at": row["available_at"], "point_in_time_eligible": False}
        decisions.append(decision)
        if eligible:
            pivot = float(children[row["outlook_id"]][0]["price_low"])
            candidates.append({"session_date": row["session_date"], "contract": row["normalized_contract"],
                               "pivot": pivot, "outlook_id": row["outlook_id"],
                               "source_revision_id": row["source_revision_id"],
                               "source_url": parents[row["outlook_id"]].get("source_url"),
                               "available_at": None, "historical_availability": "unverified",
                               "source_method_qualification": "Additional internals/delta conditions are unmodeled."})
    return {"schema_version": "abacus.study30.source-selection/v1", "decisions": decisions,
            "candidates": sorted(candidates, key=lambda row: row["session_date"]),
            "summary": {"outlooks_in_range": len(decisions), "source_eligible": len(candidates),
                        "source_semantics_resolved": sum(row["source_semantics_resolved"] for row in decisions),
                        "exclusion_reason_counts": dict(sorted(Counter(reason for row in decisions for reason in row["exclusion_reasons"]).items()))},
            "qualifications": inventory["limitations"] + [
                "Source-only lexical review resolves paired explicit above/below thresholds; no market outcome was used.",
                "Retained historical date assignments are qualified projections, not independently proven delivery dates.",
                "This does not test Verniman's full method, including internals/delta conditions."]}
