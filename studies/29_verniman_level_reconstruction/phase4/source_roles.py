"""Pure source-role interpretation units; no source loading or selector fitting.

A single functional divider requires identical exact intervals in both branch
triggers. Different branches/revisions never select their nearest trigger as a
single ground truth. Original occurrences, labels and conditions remain intact.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json

POLICY = "phase4-source-role-units-v1"


def interval(row):
    try:
        low, high = (Decimal(str(row.get(key))) for key in ("price_low", "price_high"))
    except (InvalidOperation, ValueError):
        return None
    return (low, high) if low.is_finite() and high.is_finite() and low <= high else None


def source_stratum(row):
    provenance = row.get("provenance") or {}
    return (row.get("session_date") or "", row.get("source_class") or "",
            provenance.get("source_revision_id") or row.get("source_id") or "unresolved_revision")


def interpret_divider_strata(rows):
    """Return explicit revision/class units without merging independent claims.

    A valid unique common interval is mathematical equality of both bounds,
    not a tolerance test or overlap. Numeric100 and100.00 denote the same exact
    coordinate; their original reading precision remains in occurrence records.
    """
    rows = [row for row in rows if row.get("phase4_role") == "conditional_scenario_divider"]
    ids = [row.get("level_id") for row in rows]
    if any(not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("unique original trigger occurrence IDs required")
    grouped = {}
    for row in rows:
        grouped.setdefault(source_stratum(row), []).append(row)
    result = []
    for stratum, observations in sorted(grouped.items()):
        observations = sorted(observations, key=lambda row: row["level_id"])
        bounds = [interval(row) for row in observations]
        valid = {value for value in bounds if value is not None}
        sides = {row.get("scenario_side") for row in observations}
        reasons = []
        if any(value is None for value in bounds):
            reasons.append("INVALID_OR_UNREADABLE_TRIGGER_INTERVAL")
        if len(valid) != 1:
            reasons.append("DIFFERENT_OR_MULTIPLE_TRIGGER_INTERVALS")
        if not {"bullish", "bearish"} <= sides or sides - {"bullish", "bearish"}:
            reasons.append("MISSING_OR_UNRESOLVED_BRANCH_TRIGGER")
        common = next(iter(valid)) if not reasons else None
        families = {tuple(sorted(row.get("families") or ())) for row in observations}
        family_consistent = len(families) == 1 and bool(next(iter(families)))
        identifier = hashlib.sha256(json.dumps([stratum, [row["level_id"] for row in observations]], sort_keys=True).encode()).hexdigest()[:16]
        occurrences = [{"source_occurrence_id": row["level_id"],
                        "source_id": row.get("source_id"), "original_label": row.get("original_label"),
                        "scenario_side": row.get("scenario_side"),
                        "directional_conditions": row.get("directional_conditions"),
                        "original_price_interval": [row.get("price_low"), row.get("price_high")],
                        "families": row.get("families"),
                        "historical_available_at": row.get("available_at")}
                       for row in observations]
        result.append({"policy": POLICY, "unit_id": "interpreted-functional-divider:" + stratum[0] + ":" + identifier,
                       "source_stratum": {"session_date": stratum[0], "source_class": stratum[1], "source_revision_id": stratum[2]},
                       "status": "unique_common_functional_divider" if common is not None else "unresolved_single_pivot_ground_truth",
                       "primary_price_interval": [format(value, "f") for value in common] if common is not None else None,
                       "primary_source_unit_count": 1 if common is not None else None,
                       "primary_family_identity_consistent": family_consistent,
                       "common_families": list(next(iter(families))) if family_consistent else None,
                       "reasons": reasons,
                       "source_occurrences": occurrences,
                       "literal_source_LIS_label_inferred": False,
                       "price_averaged_or_nearest_trigger_chosen": False})
    return result
