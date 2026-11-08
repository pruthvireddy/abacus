"""Deterministic, source-only Phase 1 inventory; no market-price access.

The caller owns pinned loading and byte verification.  These functions inspect
saved source records without selecting a preferred revision or asserting that a
historical plan was known before the open.  Returned records deliberately omit
source prices and prose so they can feed coverage checks without exposing dated
pivot answers.  A shape match is a candidate for review, not scientific eligibility.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "abacus.verniman-source-audit/v1"
_CONTRACT_RE = re.compile(r"ES([HMUZ])(\d{1,2}|\d{4})\Z")
_MONTHS = {"H": 3, "M": 6, "U": 9, "Z": 12}
_DATE_ISSUES = frozenset({
    "cross_release_session_date_conflict", "ledger_body_date_mismatch",
    "session_date_unresolved", "source_weekday_differs",
    "stale_source_year_conflict", "weekend_stated_outlook_date",
})
_SEMANTIC_ISSUES = frozenset({
    "branch_direction_ambiguous", "branch_duplicated", "branch_parse_failed",
    "different_branch_triggers", "operative_contract_assignment_ambiguous",
    "operative_contract_header_conflict", "past_contract_switch_header_conflict",
    "future_intraday_contract_switch", "source_trigger_ambiguous",
    "source_execution_reference", "source_execution_reference_threshold",
    "source_explicit_failure_reference", "source_lean_on_wording",
    "source_level_session_qualifier", "contextual_price_outlier",
})


def _text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _iso_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        raise ValueError("session dates must be dates, not timestamps")
    if isinstance(value, date):
        return value.isoformat()
    text = str(value)
    parsed = date.fromisoformat(text)
    if parsed.isoformat() != text:
        raise ValueError("session dates must use YYYY-MM-DD")
    return text


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _fingerprint(row: Mapping[str, Any]) -> str:
    raw = json.dumps(_json_value(row), sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _unique_rows(rows: Iterable[Mapping[str, Any]], key: str,
                 table: str) -> dict[str, dict[str, Any]]:
    result = {}
    for raw in rows:
        row = dict(raw)
        identity = _text(row.get(key))
        if not identity:
            raise ValueError(f"{table} contains a missing {key}")
        if identity in result:
            raise ValueError(f"{table} contains duplicate {key}")
        result[identity] = row
    return result


def normalize_es_contract(contract: Any, session_date: Any) -> dict[str, Any]:
    """Expand a literal ES maturity only with unique adjacent-year context.

    No front-month, roll schedule or missing maturity is inferred.  One/two-digit
    suffixes must identify exactly one of the preceding/current/following session
    years.  The resulting delivery month must lie between three months before
    and twelve months after the source session month.  This conservative source
    consistency check is not an exchange expiry or active-contract calculation.
    """
    source = _text(contract)
    result = {"source_contract": source, "normalized_contract": None,
              "status": "missing", "reason": "source_contract_missing"}
    if source is None:
        return result
    match = _CONTRACT_RE.fullmatch(source.strip().upper())
    if not match:
        return {**result, "status": "unsupported",
                "reason": "source_contract_not_explicit_quarterly_es"}
    try:
        day_text = _iso_date(session_date)
    except (TypeError, ValueError):
        day_text = None
    if day_text is None:
        return {**result, "status": "date_context_missing",
                "reason": "qualified_session_date_required_for_contract"}
    day = date.fromisoformat(day_text)
    month_code, suffix = match.groups()
    if len(suffix) == 4:
        candidates = [int(suffix)]
        status = "explicit_full_maturity"
    else:
        modulus = 10 ** len(suffix)
        candidates = [year for year in range(day.year - 1, day.year + 2)
                      if year % modulus == int(suffix)]
        status = "expanded_unique_session_year_context"
    if len(candidates) != 1:
        return {**result, "status": "year_context_conflict",
                "reason": "source_contract_year_not_unique_in_adjacent_years"}
    year = candidates[0]
    month_distance = (year - day.year) * 12 + _MONTHS[month_code] - day.month
    if not -3 <= month_distance <= 12:
        return {**result, "status": "maturity_context_conflict",
                "reason": "source_delivery_month_outside_conservative_context"}
    return {**result, "normalized_contract": f"ES{month_code}{year:04d}",
            "status": status, "reason": None}


def _bounds(row: Mapping[str, Any]) -> tuple[Decimal, Decimal] | None:
    try:
        low = Decimal(str(row.get("price_low")))
        high = Decimal(str(row.get("price_high")))
    except (InvalidOperation, ValueError):
        return None
    if not low.is_finite() or not high.is_finite() or low > high:
        return None
    return low, high


def classify_trigger_shape(levels: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Classify literal saved trigger geometry without returning any prices."""
    triggers = [dict(row) for row in levels if row.get("role") == "trigger"]
    bullish = [row for row in triggers if row.get("side") == "bullish"]
    bearish = [row for row in triggers if row.get("side") == "bearish"]
    if not triggers:
        shape = "no_trigger"
    elif any(_bounds(row) is None for row in triggers):
        shape = "invalid_trigger_data"
    elif len(bullish) + len(bearish) != len(triggers):
        shape = "unsupported_trigger_side"
    elif len(bullish) > 1 or len(bearish) > 1:
        shape = "multiple_triggers_per_side"
    elif not bullish or not bearish:
        shape = "one_sided"
    elif _bounds(bullish[0]) != _bounds(bearish[0]):
        shape = "separate_thresholds"
    else:
        low, high = _bounds(bullish[0])  # type: ignore[misc]
        shape = "single_shared_trigger" if low == high else "shared_zone"
    interpretations = sorted({_text(row.get("trigger_interpretation")) or "unspecified"
                              for row in triggers})
    return {"source_shape": shape, "trigger_row_count": len(triggers),
            "bullish_trigger_count": len(bullish),
            "bearish_trigger_count": len(bearish),
            "trigger_interpretations": interpretations}


def _count(rows: Iterable[Mapping[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field)) for row in rows).items()))


def audit_sources(*, outlooks: Iterable[Mapping[str, Any]],
                  levels: Iterable[Mapping[str, Any]],
                  issues: Iterable[Mapping[str, Any]],
                  coverage: Iterable[Mapping[str, Any]],
                  observations: Iterable[Mapping[str, Any]] = (),
                  observation_levels: Iterable[Mapping[str, Any]] = (),
                  start_date: str = "2020-01-01",
                  end_date: str = "2026-10-30") -> dict[str, Any]:
    """Account for source records and every inclusive calendar date.

    Inputs must be complete mutually consistent selected tables from the same
    pinned release.  Byte verification is the caller's prerequisite.  This
    function never opens files or loads OHLC, outcomes or indicators.
    Non-trigger levels are counted for accounting but never treated as pivots.
    Every outlook is retained, including undated and outside-range records.
    """
    start = _iso_date(start_date)
    end = _iso_date(end_date)
    if start is None or end is None or start > end:
        raise ValueError("a valid inclusive date range is required")
    parents = _unique_rows(outlooks, "outlook_id", "outlooks")
    observation_parents = _unique_rows(observations, "observation_id", "observations")
    level_rows = [dict(row) for row in levels]
    issue_rows = [dict(row) for row in issues]
    observation_children = [dict(row) for row in observation_levels]
    by_outlook: dict[str, list[dict[str, Any]]] = defaultdict(list)
    issue_by_outlook: dict[str, list[dict[str, Any]]] = defaultdict(list)
    issue_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in level_rows:
        parent = _text(row.get("outlook_id"))
        if parent not in parents:
            raise ValueError("levels contains an unknown outlook_id")
        by_outlook[parent].append(row)
    for row in issue_rows:
        parent = _text(row.get("outlook_id"))
        if parent in parents:
            issue_by_outlook[parent].append(row)
        day = _iso_date(row.get("session_date"))
        if day:
            issue_by_date[day].append(row)
    by_date: dict[str, list[str]] = defaultdict(list)
    dates: dict[str, str | None] = {}
    for identity, row in parents.items():
        day = _iso_date(row.get("session_date"))
        dates[identity] = day
        if day:
            by_date[day].append(identity)
    coverage_by_date = {}
    undated_coverage_count = 0
    for raw in coverage:
        row = dict(raw)
        day = _iso_date(row.get("session_date"))
        if day is None:
            undated_coverage_count += 1
        elif day in coverage_by_date:
            raise ValueError("coverage contains duplicate session_date")
        else:
            coverage_by_date[day] = row
    outlook_audit = []
    for identity, row in sorted(parents.items(), key=lambda item: (dates[item[0]] or "", item[0])):
        day = dates[identity]
        in_range = day is not None and start <= day <= end
        contract = normalize_es_contract(row.get("contract"), day)
        shape = classify_trigger_shape(by_outlook[identity])
        source_issues = issue_by_outlook[identity]
        codes = sorted({_text(issue.get("code")) or "unspecified" for issue in source_issues})
        date_codes = sorted((set(codes) | {
            _text(issue.get("code")) or "unspecified"
            for issue in issue_by_date[day] if day
        }) & _DATE_ISSUES)
        date_review_required = bool(date_codes) or not _text(row.get("session_date_method")) or row.get("source_year_status") in {"unresolved", "stale_source_year_conflict"}
        reasons = []
        if day is None:
            reasons.append("session_date_missing")
        if contract["normalized_contract"] is None:
            reasons.append(contract["reason"])
        if _text(row.get("product")) != "ES":
            reasons.append("source_product_not_explicit_es")
        if row.get("extraction_status") != "complete":
            reasons.append("source_extraction_not_complete")
        if row.get("evidence_basis") != "captured_source":
            reasons.append("source_evidence_not_captured_plan")
        if row.get("content_kind") not in (None, "", "daily_outlook"):
            reasons.append("source_content_not_daily_outlook")
        if shape["source_shape"] != "single_shared_trigger":
            reasons.append("source_shape_not_single_shared_trigger")
        interpretations = set(shape["trigger_interpretations"])
        if "unspecified" in interpretations:
            reasons.append("pivot_semantics_unreviewed")
        if interpretations - {"unspecified", "conditional_threshold"}:
            reasons.append("trigger_not_exclusively_conditional_threshold")
        if day and len(by_date[day]) > 1:
            reasons.append("multiple_canonical_outlooks_on_date")
        if not _text(row.get("session_date_method")):
            reasons.append("source_date_assignment_method_missing")
        if row.get("source_year_status") in {"unresolved", "stale_source_year_conflict"}:
            reasons.append("source_year_context_requires_review")
        reasons.extend(f"source_issue:{code}" for code in sorted((set(codes) & (_DATE_ISSUES | _SEMANTIC_ISSUES)) | set(date_codes)))
        if any(issue.get("severity") == "error" for issue in source_issues):
            reasons.append("source_error_issue_present")
        for child in by_outlook[identity]:
            if _iso_date(child.get("session_date")) != day:
                reasons.append("level_date_differs_from_parent")
            if _text(child.get("contract")) != _text(row.get("contract")):
                reasons.append("level_contract_differs_from_parent")
        if day is None:
            disposition = "undated"
        elif not in_range:
            disposition = "outside_requested_range"
        else:
            disposition = "review_required" if reasons else "candidate_pending_data"
        availability = _json_value(row.get("available_at"))
        null_available_at = availability in (None, "")
        outlook_audit.append({
            "candidate_id": identity, "outlook_id": identity,
            "source_revision_id": _text(row.get("source_revision_id")),
            "session_date": day, "in_requested_range": in_range,
            "source_contract": contract["source_contract"],
            "normalized_contract": contract["normalized_contract"],
            "contract_normalization_status": contract["status"],
            "contract_normalization_reason": contract["reason"],
            **shape, "canonical_outlooks_on_date": len(by_date[day]) if day else None,
            "source_only_disposition": disposition,
            "review_reasons": sorted(set(reasons)),
            "source_date_assignment_method": _text(row.get("session_date_method")),
            "source_date_assignment_review_status": "review_required" if date_review_required else "source_assignment_retained_unrevalidated",
            "source_date_assignment_issue_codes": date_codes,
            "source_review_status": _text(row.get("review_status")),
            "source_year_status": _text(row.get("source_year_status")),
            "source_agreement_status": _text(row.get("source_agreement_status")),
            "source_extraction_status": _text(row.get("extraction_status")),
            "source_evidence_basis": _text(row.get("evidence_basis")),
            "source_issue_codes": codes, "source_issue_count": len(source_issues),
            "source_level_row_count": len(by_outlook[identity]),
            "available_at": availability if not null_available_at else None,
            "null_available_at": null_available_at,
            "source_timing_status": _text(row.get("timing_status")),
            "point_in_time_eligible": False,
            "availability_assessment": "historical_availability_unverified" if null_available_at else "timestamp_present_not_independently_verified",
        })
    observation_audit, observation_level_audit = _audit_observations(
        observation_parents, observation_children, start, end)
    calendar_audit = []
    current = date.fromisoformat(start)
    last = date.fromisoformat(end)
    while current <= last:
        day = current.isoformat()
        source = coverage_by_date.get(day)
        ids = sorted(by_date[day])
        calendar_audit.append({
            "session_date": day,
            "calendar_kind": "calendar_date_not_exchange_eligibility",
            "coverage_record_present": source is not None,
            "source_coverage_status": _text(source.get("status")) if source else None,
            "source_coverage_reason_present": bool(_text(source.get("reason"))) if source else False,
            "source_coverage_reason_sha256": hashlib.sha256(str(source["reason"]).encode("utf-8")).hexdigest() if source and _text(source.get("reason")) else None,
            "canonical_outlook_count": len(ids), "canonical_outlook_ids": ids,
            "duplicate_date": len(ids) > 1,
            "source_issue_codes": sorted({_text(row.get("code")) or "unspecified" for row in issue_by_date[day]}),
            "user_observation_count": sum(row["session_date"] == day for row in observation_audit),
            "source_only_disposition": "missing_coverage_record" if source is None else "multiple_canonical_outlooks" if len(ids) > 1 else "one_canonical_outlook" if ids else "no_canonical_outlook_observed",
        })
        current += timedelta(days=1)
    selected = [row for row in outlook_audit if row["in_requested_range"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "requested_interval": {"start_date": start, "end_date": end, "end_inclusive": True},
        "outlook_audit": outlook_audit, "calendar_audit": calendar_audit,
        "observation_audit": observation_audit,
        "observation_level_audit": observation_level_audit,
        "summary": {
            "canonical_outlook_rows_input": len(parents),
            "canonical_outlook_rows_accounted": len(outlook_audit),
            "canonical_outlook_rows_in_range": len(selected),
            "canonical_outlook_rows_undated": sum(row["session_date"] is None for row in outlook_audit),
            "canonical_level_rows_input": len(level_rows),
            "canonical_level_rows_accounted": sum(row["source_level_row_count"] for row in outlook_audit),
            "calendar_dates_accounted": len(calendar_audit),
            "coverage_rows_input": len(coverage_by_date) + undated_coverage_count,
            "undated_coverage_rows": undated_coverage_count,
            "issue_rows_input": len(issue_rows),
            "source_shapes_in_range": _count(selected, "source_shape"),
            "source_dispositions_in_range": _count(selected, "source_only_disposition"),
            "calendar_dispositions": _count(calendar_audit, "source_only_disposition"),
            "duplicate_dates_in_range": sum(row["duplicate_date"] for row in calendar_audit),
            "normalized_contract_outlooks_in_range": sum(row["normalized_contract"] is not None for row in selected),
            "null_available_at_outlooks_in_range": sum(row["null_available_at"] for row in selected),
            "point_in_time_eligible_outlooks": 0,
            "user_observation_rows_accounted": len(observation_audit),
            "user_observation_level_rows_accounted": len(observation_level_audit),
            "user_observation_basis_counts": _count(observation_audit, "source_evidence_basis"),
        },
        "limitations": [
            "Saved source geometry and metadata only; no market outcomes calculated.",
            "Historical availability is not independently verified; 09:25 is not imputed.",
            "Duplicate dates retain every canonical outlook; no latest-revision selection.",
            "Source-only dispositions do not establish scientific or exchange-session eligibility.",
            "User observations remain separate and never replace canonical source plans.",
        ],
    }


def _audit_observations(parents: Mapping[str, Mapping[str, Any]],
                        children: list[dict[str, Any]], start: str,
                        end: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in children:
        identity = _text(row.get("observation_id"))
        if identity not in parents:
            raise ValueError("observation_levels contains an unknown observation_id")
        by_parent[identity].append(row)
    parent_audit, level_audit = [], []
    for identity, row in sorted(parents.items()):
        day = _iso_date(row.get("session_date"))
        parent_audit.append({
            "observation_id": identity, "session_date": day,
            "in_requested_range": day is not None and start <= day <= end,
            "source_evidence_basis": _text(row.get("evidence_basis")),
            "claim_timing_class": _text(row.get("claim_timing_class")),
            "source_timing_status": _text(row.get("timing_status")),
            "source_contract": _text(row.get("contract")),
            "level_row_count": len(by_parent[identity]),
            "source_only_disposition": "separate_observation_not_canonical_plan",
            "null_available_at": row.get("available_at") in (None, ""),
            "point_in_time_eligible": False,
        })
        seen: Counter[str] = Counter()
        for child in sorted(by_parent[identity], key=_fingerprint):
            fingerprint = _fingerprint(child)
            seen[fingerprint] += 1
            child_day = _iso_date(child.get("session_date"))
            bounds = _bounds(child)
            level_audit.append({
                "record_id": f"{identity}:level:{fingerprint}:{seen[fingerprint]}",
                "source_level_id": _text(child.get("id")),
                "source_row_sha256": fingerprint, "observation_id": identity,
                "session_date": child_day,
                "in_requested_range": child_day is not None and start <= child_day <= end,
                "source_role": _text(child.get("role")),
                "source_side": _text(child.get("side")),
                "has_valid_numeric_bounds": bounds is not None,
                "source_only_disposition": "separate_observation_not_canonical_plan",
            })
    return parent_audit, level_audit
