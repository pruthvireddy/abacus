"""Pure strict-common-unit distillation of already saved Phase 5 comparisons.

No file/source loading, metadata inference, matching or selector execution occurs.
The caller verifies summary/ledger/comparison bytes through explicit manifests.
Coordinate diagnostics are never read. Unsupported or unresolved source identity
cannot supply a common primary unit or be repaired by proximity.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re


def _group(row):
    return (row["session_date"], row["source_class"],
            row.get("provenance", {}).get("source_revision_id") or row.get("source_id") or "unresolved_revision")


def _occurrences(strict, section):
    rows = (strict.get(section) or {}).get("occurrences") or []
    result = {row["source_id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate source occurrence IDs in saved strict comparison")
    return result


def _fully_eligible(row):
    families = row.get("families") or []
    return bool(families) and set(row.get("eligible_roles") or []) == set(families)


def _full_match(row):
    return _fully_eligible(row) and set(row.get("matched_roles") or []) == set(row["families"])


def _identity(assessment):
    return (isinstance(assessment, dict) and assessment.get("status") == "supported_explicit_metadata"
            and bool(assessment.get("supported_window_id")) and bool(assessment.get("normalized_contract"))
            and assessment.get("adjustment") == "individual_contract_unadjusted")


def _ordering(strict, key):
    rows = [row for row in strict.get("ordering", [])
            if (row.get("session_date"), row.get("source_class"), row.get("revision_id")) == key]
    return rows[0] if len(rows) == 1 else None


def _price_agrees(strict, source_id, bounds):
    """Require actual point/E1 boundary proximity in addition to strict roles.

    For E1 the uncertainty interval alone cannot pass this pivot price metric.
    Source intervals remain intervals; no midpoint or source price is invented.
    Other eligible selected pivot candidates are exact points under this control.
    """
    try:
        low, high = (Decimal(str(x)) for x in bounds)
        if not low.is_finite() or not high.is_finite() or low > high:
            return False
        assignments = [a for s in (strict.get("selection") or {}).get("strata", [])
                       for a in s.get("assignments", []) if a.get("source_id") == source_id]
        if not assignments:
            return False
        for row in assignments:
            if row.get("boundary") is not None:
                boundary = Decimal(str(row["boundary"]))
                if not boundary.is_finite() or max(Decimal(0), low - boundary, boundary - high) > 1:
                    return False
            else:
                width = Decimal(str(row.get("candidate_interval_width")))
                gap = Decimal(str(row.get("interval_gap_points")))
                if width != 0 or not gap.is_finite() or gap < 0 or gap > 1:
                    return False
        return True
    except (InvalidOperation, TypeError, ValueError):
        return False


def _count(value, label, maximum=None):
    if type(value) is not int or value < 0 or maximum is not None and value > maximum:
        raise ValueError(label + " must be a nonnegative integer within its declared bound")
    return value


def _unit(role, key, source_ids, raw_ids):
    encoded = json.dumps([role, key, sorted(source_ids)], separators=(",", ":"))
    identifier = "strict-common:" + role + ":" + hashlib.sha256(encoded.encode()).hexdigest()[:24]
    return {"unit_id": identifier, "session_date": key[0], "source_class": key[1], "source_revision_id": key[2],
            "family_supported": True, "contract_supported": True, "exact_window_supported": True,
            "eligible_source_occurrence_count": len(source_ids), "eligible_source_occurrence_ids": sorted(source_ids),
            "original_source_occurrence_ids": sorted(raw_ids)}


def distill(summary, records, ledger, *, decision_spec):
    """Build the assessor's explicit input from fixed strict outcomes only.

    Branch units retain the entire source destination list and require supported
    identity/order for every original occurrence. Generation failures remain in
    eligible units and end-to-end denominators. Common units are intersected
    across all six configurations; source revisions/classes are never pooled.
    """
    if summary.get("schema") != "abacus.study29.phase5.saved-comparisons/v1":
        raise ValueError("explicit saved Phase5 comparison summary required")
    configs, dates, roles = decision_spec.CONFIGURATIONS, decision_spec.DATES, decision_spec.ROLES
    if set(summary.get("configurations") or []) != set(configs) or len(summary.get("configurations") or []) != len(configs):
        raise ValueError("saved summary configurations differ from the frozen family")
    gate = summary.get("reveal_gate") or {}
    payload = {"schema": decision_spec.SCHEMA, "decision_rule_sha256": decision_spec.RULE_SHA256,
               "scheduled_dates": list(dates), "configurations": list(configs),
               "engineering_gate": {"status": gate.get("status", "incomplete")},
               "common_primary_units": {r: [] for r in roles}, "essential_unmeasured_conditions": [],
               "configuration_results": {c: {"metric_basis": "strict_common_primary_units",
                   "common_primary_unit_ids": {r: [] for r in roles},
                   "metrics": {m: {"status": "not_estimable", "numerator": None, "denominator": 0}
                               for m in decision_spec.METRICS}, "abstentions": {r: 0 for r in roles}} for c in configs},
               "unit_exclusions": [], "comparison_selection_recomputed": False,
               "coordinate_diagnostics_read": False,
               "metric_definition": "Pivot agreement requires full supported strict roles and actual point/E1-boundary gap<=1 to the original source interval. Recall/order remain interval-qualified under the frozen matcher. Extras count unmatched physical target ranks; occurrences and compound roles count once."}
    if gate.get("status") != "passed":
        payload["source_data_examined_by_distiller"] = False
        return payload
    payload["engineering_gate"]["receipt"] = dict(gate.get("gate") or {})
    if summary.get("selection_recomputed") is not False or summary.get("candidate_inputs_modified") is not False:
        raise ValueError("saved-only unchanged predictions are required")
    if len(records) != len(dates) or {r.get("session_date") for r in records} != set(dates):
        raise ValueError("all four unique scheduled saved comparisons are required")
    if len(summary.get("records") or []) != len(dates) or {r.get("session_date") for r in summary["records"]} != set(dates):
        raise ValueError("summary must inventory every scheduled comparison")
    if ledger.get("schema") != "abacus.study29.phase5.source-role-ledger/v1":
        raise ValueError("explicit Phase5 source-role ledger required")
    observations = ledger.get("occurrences") or []
    by_id = {row["level_id"]: row for row in observations}
    if len(by_id) != len(observations) or any(row.get("session_date") not in dates for row in observations):
        raise ValueError("source occurrence identities/dates must remain unique and allowlisted")
    by_day = {row["session_date"]: row for row in records}
    assessments, grouping = {}, {r: defaultdict(list) for r in roles}
    wanted = {"conditional_scenario_divider": "pivot", "ordered_bullish_destination": "bullish", "ordered_bearish_destination": "bearish"}
    for row in observations:
        role = wanted.get(row.get("phase4_role"))
        if role:
            grouping[role][_group(row)].append(row)
            conditions = row.get("directional_conditions")
            if conditions is None and role == "pivot":
                payload["essential_unmeasured_conditions"].append("UNRESOLVED_DIRECTIONAL_CONDITION_STATUS")
            elif isinstance(conditions, str):
                payload["essential_unmeasured_conditions"].extend(name for name in ("VIX", "CVD")
                    if re.search(r"\b" + name + r"\b", conditions, re.IGNORECASE))
            explicit = row.get("essential_unmeasured_conditions") or []
            if not isinstance(explicit, list) or any(not isinstance(x, str) or not x for x in explicit):
                raise ValueError("explicit essential-condition qualifications must be strings")
            payload["essential_unmeasured_conditions"].extend(explicit)
    payload["essential_unmeasured_conditions"] = sorted(set(payload["essential_unmeasured_conditions"]))
    for day, record in by_day.items():
        if (record.get("schema") != "abacus.study29.phase5.saved-comparison/v1"
                or record.get("selection_recomputed") is not False or record.get("candidate_inputs_modified") is not False
                or set(record.get("analysis") or {}) != set(configs)
                or record.get("source_ledger") != summary.get("source_ledger")):
            raise ValueError("saved comparison identity/configuration/provenance differs")
        rows = record.get("source_window_identity_assessments") or []
        index = {row["source_occurrence_id"]: row for row in rows}
        if len(index) != len(rows) or any(sid not in by_id or by_id[sid]["session_date"] != day for sid in index):
            raise ValueError("source-window assessment IDs differ from the bounded ledger")
        assessments[day] = index
    internal = {r: {} for r in roles}
    for role in roles:
        for key, rows in sorted(grouping[role].items()):
            day = key[0]; raw_ids = {r["level_id"] for r in rows}; reasons = []
            claims = [assessments[day].get(sid) for sid in raw_ids]
            if not all(_identity(claim) for claim in claims):
                reasons.append("NO_SUPPORTED_EXPLICIT_SOURCE_IDENTITY")
            ordered = [row.get("source_target_order") for row in rows]
            if role != "pivot" and (any(type(x) is not int or x < 1 for x in ordered) or len(set(ordered)) != len(ordered)):
                reasons.append("SOURCE_TARGET_ORDER_UNRESOLVED")
            source_ids, bounds = raw_ids, None
            if role == "pivot":
                units = by_day[day]["analysis"][configs[0]].get(role, {}).get("primary_pivot_interpretation") or {}
                candidates = [u for u in units.get("source_strata", [])
                              if (u.get("source_stratum", {}).get("session_date"),
                                  u.get("source_stratum", {}).get("source_class"),
                                  u.get("source_stratum", {}).get("source_revision_id")) == key]
                if (units.get("status") != "unique_common_functional_divider" or len(candidates) != 1
                        or candidates[0].get("status") != "unique_common_functional_divider"
                        or candidates[0].get("primary_family_identity_consistent") is not True):
                    reasons.append("SINGLE_SUPPORTED_PIVOT_UNIT_UNRESOLVED")
                else:
                    unit = candidates[0]; source_ids = {unit["unit_id"]}; bounds = unit.get("primary_price_interval")
                    if len({(c.get("supported_window_id"), c.get("normalized_contract"), c.get("adjustment")) for c in claims if c}) != 1:
                        reasons.append("PIVOT_BRANCH_IDENTITIES_CONFLICT")
            for config in configs:
                strict = by_day[day]["analysis"][config].get(role, {}).get("strict_decomposition") or {}
                generation = _occurrences(strict, "generation")
                if strict.get("status") != "compared" or any(not _fully_eligible(generation.get(sid) or {}) for sid in source_ids):
                    reasons.append("NOT_FULLY_ELIGIBLE_ON_ALL_SAVED_CONFIGURATIONS")
                if type(strict.get("selector_abstained")) is not bool:
                    reasons.append("SELECTION_STATE_UNRESOLVED")
                if role != "pivot":
                    order = _ordering(strict, key)
                    if (not order or type(order.get("complete_ladder_agreement")) is not bool
                            or order.get("source_order_ambiguous") is True or order.get("source_targets_not_truncated") is not True):
                        reasons.append("STRICT_ORDERED_BRANCH_STATE_UNRESOLVED")
                    elif order.get("observed_target_count") != len(source_ids):
                        raise ValueError("source target denominator was changed or truncated")
            if reasons:
                payload["unit_exclusions"].append({"role": role, "session_date": day,
                    "source_class": key[1], "source_revision_id": key[2],
                    "source_occurrence_ids": sorted(raw_ids), "reasons": sorted(set(reasons))})
                continue
            unit = _unit(role, key, source_ids, raw_ids)
            payload["common_primary_units"][role].append(unit)
            internal[role][unit["unit_id"]] = {"key": key, "source_ids": source_ids, "bounds": bounds}
    denominators = {
        "pivot_identity_role_price_agreement": len(internal["pivot"]),
        "complete_bullish_ladder_agreement": len(internal["bullish"]),
        "complete_bearish_ladder_agreement": len(internal["bearish"]),
        "end_to_end_eligible_source_recall": sum(len(u["source_ids"]) for r in roles for u in internal[r].values()),
        "bullish_extras_per_branch": len(internal["bullish"]),
        "bearish_extras_per_branch": len(internal["bearish"]),
    }
    for config in configs:
        numerators = {m: 0 for m in decision_spec.METRICS}
        result = payload["configuration_results"][config]
        for role in roles:
            result["common_primary_unit_ids"][role] = [u["unit_id"] for u in payload["common_primary_units"][role]]
            for info in internal[role].values():
                key, source_ids = info["key"], info["source_ids"]
                strict = by_day[key[0]]["analysis"][config][role]["strict_decomposition"]
                selected = _occurrences(strict, "selection")
                full_ids = {sid for sid in source_ids if _full_match(selected.get(sid) or {})}
                numerators["end_to_end_eligible_source_recall"] += len(full_ids)
                result["abstentions"][role] += strict["selector_abstained"]
                physical = _count(strict.get("physical_selected_count"), "physical selections", 1 if role == "pivot" else 3)
                if role == "pivot":
                    sid, = source_ids
                    numerators["pivot_identity_role_price_agreement"] += sid in full_ids and _price_agrees(strict, sid, info["bounds"])
                else:
                    order = _ordering(strict, key)
                    numerators["complete_" + role + "_ladder_agreement"] += order["complete_ladder_agreement"]
                    ranks = set()
                    for pair in order.get("matched_order_pairs") or []:
                        if (not isinstance(pair, list) or len(pair) != 2 or type(pair[1]) is not int
                                or pair[1] < 1 or pair[1] > physical):
                            raise ValueError("saved strict matched target rank exceeds physical selections")
                        ranks.add(pair[1])
                    if order["complete_ladder_agreement"] and (physical != len(source_ids) or len(ranks) != physical):
                        raise ValueError("complete ladder assertion conflicts with physical/source counts")
                    numerators[role + "_extras_per_branch"] += physical - len(ranks)
        result["metrics"] = {name: {"status": "estimable" if denominators[name] else "not_estimable",
            "numerator": numerators[name] if denominators[name] else None, "denominator": denominators[name]}
            for name in decision_spec.METRICS}
    payload["source_data_examined_by_distiller"] = True
    payload["source_ledger"] = dict(summary.get("source_ledger") or {})
    payload["saved_comparison_records"] = [dict(row) for row in summary["records"]]
    return payload
