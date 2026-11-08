"""Metadata-only exact-window support; never inspect prices or candidate pools.

A source assertion is supported only by a separately pinned same-revision JSON
identity record with complete explicit clocks/contract/measurement. Partial or
inferred assertions remain provided-but-unassessed; their evidence is preserved.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

POLICY = "phase5-explicit-window-metadata-v1"
SCHEMA = "abacus.study29.explicit-source-window/v1"
DATES = {"2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20"}
NY = ZoneInfo("America/New_York")
PROFILE_MEASUREMENT = "uniform_chart_bar_volume_across_inclusive_touched_bins"
EXTREME_MEASUREMENT = "unadjusted_market_price_extreme"
FIELDS = ("supported_window_id", "period_identity", "source_contract", "reference_start", "reference_end", "information_cutoff", "measurement", "adjustment")
CONTRACTS = {"ESZ26": "ESZ2026", "ESZ2026": "ESZ2026", "CME_MINI:ESZ2026": "ESZ2026"}


def aware(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("aware window clocks required")
    return result.astimezone(NY)


def local(day, hour, minute=0):
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=NY)


def previous_weekday(day):
    day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def compatible_period(claim, day):
    """Compatibility is clock/calendar based, independent of all price fields."""
    start, end, cutoff = (aware(claim[key]) for key in ("reference_start", "reference_end", "information_cutoff"))
    terminal = local(day, 9, 25)
    if not start < end <= cutoff <= terminal:
        return False
    prior = previous_weekday(day)
    sunday = day - timedelta(days=(day.weekday() + 1) % 7)
    period = claim["period_identity"]
    if period == "completed_RTH":
        expected = local(prior, 9, 30), local(prior, 16)
    elif period == "overnight_prefix":
        expected = local(day - timedelta(days=1), 18), terminal
    elif period == "current_week_prefix":
        expected = local(sunday, 18), terminal
    elif period == "previous_completed_week":
        expected = local(sunday - timedelta(days=7), 18), local(sunday - timedelta(days=2), 17)
    elif period == "full":
        expected = local(prior - timedelta(days=1), 18), local(prior, 17)
    elif period == "explicit_composite_RTH3":
        days = []
        current = day
        for _ in range(3):
            current = previous_weekday(current); days.append(current)
        days.reverse()
        expected_members = [{"reference_start": local(member, 9, 30).isoformat(), "reference_end": local(member, 16).isoformat()} for member in days]
        if claim.get("members") != expected_members:
            return False
        expected = local(days[0], 9, 30), local(days[-1], 16)
    else:
        return False
    if (start, end) != expected:
        return False
    identifier = claim["supported_window_id"]
    if period == "explicit_composite_RTH3":
        return identifier == "composite_RTH3:" + day.isoformat()
    if period == "full":
        return identifier == f"full:{start}:{end}"
    return identifier == f"{period}:{start.isoformat()}:{end.isoformat()}"


def assess(row, root, *, allowed_evidence_roots):
    root = root.resolve()
    supplied = row.get("source_window_identity_supplied")
    result = {"policy": POLICY, "status": "unidentified_no_explicit_window_metadata", "supported_window_id": None,
              "normalized_contract": None, "adjustment": None, "supplied_metadata": supplied,
              "evidence": [], "reasons": [], "candidate_or_source_price_inspected": False}
    if supplied is None:
        return result
    result["status"] = "provided_metadata_unassessed"
    try:
        if row.get("session_date") not in DATES or not isinstance(supplied, dict):
            raise ValueError("unauthorized source date or malformed explicit metadata")
        if supplied.get("schema") != SCHEMA or supplied.get("basis") != "explicit_independent_source_metadata" or supplied.get("independent_of_candidate_prices") is not True:
            raise ValueError("inferred or unqualified identity assertion")
        if any(not supplied.get(key) for key in FIELDS):
            raise ValueError("partial contract/window/cutoff/measurement identity")
        contract = CONTRACTS.get(supplied["source_contract"])
        original_contract = row.get("actual_contract")
        if contract is None or original_contract is not None and CONTRACTS.get(original_contract) != contract or supplied["adjustment"] != "individual_contract_unadjusted":
            raise ValueError("source contract/price coordinate compatibility unresolved")
        if supplied["measurement"] not in {PROFILE_MEASUREMENT, EXTREME_MEASUREMENT}:
            raise ValueError("provided measurement does not establish compatible candidate construction")
        families = set(row.get("families") or [])
        if supplied["measurement"] == EXTREME_MEASUREMENT and (not families or families - {"YHOD", "YLOD", "ONH", "ONL"}):
            raise ValueError("price-extreme metadata cannot establish a profile/projection construction")
        if not compatible_period(supplied, date.fromisoformat(row["session_date"])):
            raise ValueError("explicit period/window identity incompatible with frozen clocks or members")
        evidence = supplied.get("identity_evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("independently pinned identity evidence missing")
        expected = {key: supplied[key] for key in FIELDS}
        if "members" in supplied:
            expected["members"] = supplied["members"]
        for pin in evidence:
            path = (root / pin["path"]).resolve()
            if (not path.is_relative_to(root) or not any(path.is_relative_to(base.resolve()) for base in allowed_evidence_roots) or
                    not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != pin.get("sha256")):
                raise ValueError("identity evidence is unpinned, mismatched or outside bounded evidence roots")
            document = json.loads(path.read_text())
            if (document.get("schema") != "abacus.study29.source-window-evidence/v1" or
                    document.get("session_date") != row["session_date"] or
                    document.get("source_class") != row.get("source_class") or
                    document.get("source_revision_id") != row.get("provenance", {}).get("source_revision_id") or
                    document.get("basis") != "explicit_independent_source_metadata" or
                    document.get("independent_of_candidate_prices") is not True or document.get("identity") != expected):
                raise ValueError("pinned evidence does not explicitly establish this same-revision identity")
            result["evidence"].append(pin)
        result.update(status="supported_explicit_metadata", supported_window_id=supplied["supported_window_id"], normalized_contract=contract, adjustment=supplied["adjustment"])
    except (KeyError, TypeError, ValueError, OSError) as error:
        result["reasons"].append(str(error))
    return result


def source_refs(rows, matching, assessments, original_rows=()):
    """Construct the frozen matcher's references without changing its algorithm."""
    result = []
    for row in rows:
        assessment = assessments.get(row["level_id"]) or row.get("phase5_window_identity_assessment") or {"status": "unidentified_no_explicit_window_metadata"}
        if row["level_id"].startswith("interpreted-functional-divider:"):
            triggers = [original for original in original_rows if original.get("phase4_role") == "conditional_scenario_divider" and
                        (original.get("session_date"), original.get("source_class"), original.get("provenance", {}).get("source_revision_id")) ==
                        (row.get("session_date"), row.get("source_class"), row.get("provenance", {}).get("source_revision_id"))]
            claims = [assessments[original["level_id"]] for original in triggers]
            identities = {(claim.get("supported_window_id"), claim.get("normalized_contract"), claim.get("adjustment")) for claim in claims}
            if not claims or any(claim["status"] != "supported_explicit_metadata" for claim in claims) or len(identities) != 1:
                assessment = {"status": "common_divider_window_unresolved_or_conflicting"}
            else:
                assessment = claims[0]
        supported = assessment["status"] == "supported_explicit_metadata"
        normalized = assessment["normalized_contract"] if supported else CONTRACTS.get(row.get("actual_contract"))
        result.append(matching.SourceReference(row["level_id"], row["session_date"], row["source_class"],
                      row.get("provenance", {}).get("source_revision_id") or "unresolved_revision", tuple(row["families"]),
                      (row["price_low"], row["price_high"]), assessment["supported_window_id"] if supported else None,
                      normalized, assessment["adjustment"] if supported else "individual_contract_unadjusted" if normalized else None,
                      row["source_timing_class"], row.get("available_at")))
    return result
