"""Pure application of the pre-answer Phase 5 decision rule.

Consumes an explicit count-based summary, never source text, market bars or
coordinate errors. The caller must verify the pinned reveal-gate receipt and
derive common supported source units from saved comparisons. This function does
not open files, run a selector, certify provenance bytes or authorize Phase 6.
"""
from __future__ import annotations

from fractions import Fraction

SCHEMA = "abacus.study29.phase5.decision-input/v1"
RULE_SHA256 = "198e73d1f55df4c6af129696533efc821b844e9b19deee6b346c39b687e56440"
DATES = ("2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20")
CONFIGURATIONS = ("P0-D1", "P0-D0", "B0-D0", "B0-D1", "B1-D0", "B1-D1")
PRIMARY = "P0-D1"
ROLES = ("pivot", "bullish", "bearish")
METRICS = {
    "pivot_identity_role_price_agreement": 1,
    "complete_bullish_ladder_agreement": 1,
    "complete_bearish_ladder_agreement": 1,
    "end_to_end_eligible_source_recall": 1,
    "bullish_extras_per_branch": -1,
    "bearish_extras_per_branch": -1,
}
SUPPORT = ("family_supported", "contract_supported", "exact_window_supported")


def _integer(value, label, *, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(label + " must be an integer >= " + str(minimum))
    return value


def _exact_inventory(actual, expected, label):
    if (not isinstance(actual, list) or any(not isinstance(x, str) for x in actual)
            or len(actual) != len(expected) or set(actual) != set(expected)):
        raise ValueError(label + " must equal the frozen unique inventory")


def _receipt(value):
    if not isinstance(value, dict) or not isinstance(value.get("path"), str) or not value["path"]:
        raise ValueError("a pinned validated engineering receipt is required")
    h = value.get("sha256")
    if not isinstance(h, str) or len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
        raise ValueError("engineering receipt requires a full SHA-256")
    return {"path": value["path"], "sha256": h}


def _common_units(payload):
    supplied = payload.get("common_primary_units")
    if not isinstance(supplied, dict) or set(supplied) != set(ROLES):
        raise ValueError("explicit common primary units for all three roles are required")
    units, dates, seen, occurrence_ids, excluded = {}, {}, set(), set(), []
    for role in ROLES:
        rows = supplied[role]
        if not isinstance(rows, list):
            raise ValueError("common primary units must be lists")
        accepted = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("each common primary unit must be a record")
            name, day = row.get("unit_id"), row.get("session_date")
            if not isinstance(name, str) or not name or name in seen:
                raise ValueError("unique original common primary unit IDs are required")
            seen.add(name)
            if day not in DATES:
                raise ValueError("common primary unit is outside the four scheduled dates")
            if any(not isinstance(row.get(k), str) or not row[k] for k in ("source_class", "source_revision_id")):
                raise ValueError("common units require explicit source class and revision")
            count = _integer(row.get("eligible_source_occurrence_count"), "eligible source occurrence count", minimum=1)
            ids = row.get("eligible_source_occurrence_ids")
            if (not isinstance(ids, list) or len(ids) != count or any(not isinstance(x, str) or not x for x in ids)
                    or len(set(ids)) != count or occurrence_ids.intersection(ids)):
                raise ValueError("unique eligible source occurrence IDs must agree with the unit count")
            occurrence_ids.update(ids)
            if role == "pivot" and count != 1:
                raise ValueError("a functional divider counts once, not once per raw branch trigger")
            unsupported = [k for k in SUPPORT if row.get(k) is not True]
            if unsupported:
                excluded.append({"unit_id": name, "role": role, "reasons": unsupported})
            else:
                accepted.append({"unit_id": name, "session_date": day, "eligible_source_occurrence_count": count})
        units[role] = sorted(accepted, key=lambda r: r["unit_id"])
        dates[role] = sorted({r["session_date"] for r in accepted})
    return units, dates, excluded


def _ratio(record, name, denominator):
    n = _integer(record.get("numerator"), name + " numerator")
    d = _integer(record.get("denominator"), name + " denominator", minimum=1)
    if d != denominator:
        raise ValueError(name + " does not use the common eligible denominator")
    if METRICS[name] == 1 and n > d:
        raise ValueError(name + " agreement/recall numerator exceeds denominator")
    return Fraction(n, d)


def assess(payload):
    """Return a deterministic decision without mutating the supplied summary.

    Metrics are six explicit numerator/denominator records on the same supported
    units for every configuration. Extras may exceed one per branch. Abstention
    is an integer count per role on those units. Geometry is never examined.
    Unknown identity, insufficient dates, essential unmeasured conditions or
    non-estimable strict metrics retain only the engineering default.
    """
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA or payload.get("decision_rule_sha256") != RULE_SHA256:
        raise ValueError("the exact pre-answer decision rule/schema is required")
    _exact_inventory(payload.get("scheduled_dates"), DATES, "scheduled dates")
    _exact_inventory(payload.get("configurations"), CONFIGURATIONS, "configurations")
    engineering = payload.get("engineering_gate") or {}
    if not isinstance(engineering, dict):
        raise ValueError("engineering gate must be an explicit status record")
    result = {
        "schema": "abacus.study29.phase5.decision-assessment/v1",
        "decision_rule_sha256": RULE_SHA256,
        "proposed_primary": PRIMARY,
        "configurations": list(CONFIGURATIONS),
        "engineering_gate_passed": engineering.get("status") == "passed",
        "identifiability_passed": False,
        "selected_configuration": None,
        "retained_engineering_default": None,
        "no_validated_configuration_selected": True,
        "dominating_alternatives": [],
        "status": "engineering_incomplete",
        "reasons": [],
        "coordinate_metrics_used_for_selection": False,
        "source_method_final_evaluation_ready": False,
        "phase6_execution_authorized": False,
        "final_evaluation_qualification": "Original holdout exposure is not erased by a fresh evaluator. A separately authorized genuinely unseen period and source-identity eligibility are still required.",
    }
    if not result["engineering_gate_passed"]:
        result["reasons"] = ["ENGINEERING_GATE_NOT_PASSED"]
        return result
    result["engineering_receipt"] = _receipt(engineering.get("receipt"))
    result["retained_engineering_default"] = PRIMARY
    result["status"] = "engineering_default_retained_inconclusive"
    units, dates, excluded = _common_units(payload)
    result["common_eligible_dates"] = dates
    result["common_eligible_unit_counts"] = {r: len(units[r]) for r in ROLES}
    result["unsupported_unit_exclusions"] = excluded
    unmeasured = payload.get("essential_unmeasured_conditions")
    if not isinstance(unmeasured, list) or any(not isinstance(x, str) or not x for x in unmeasured):
        raise ValueError("essential unmeasured conditions must be an explicit string list")
    result["essential_unmeasured_conditions"] = sorted(set(unmeasured))
    if excluded:
        result["reasons"].append("UNKNOWN_OR_UNSUPPORTED_PRIMARY_IDENTITY")
    if any(len(dates[r]) < 3 for r in ROLES):
        result["reasons"].append("INSUFFICIENT_COMMON_ELIGIBLE_DATES")
    if unmeasured:
        result["reasons"].append("ESSENTIAL_SOURCE_CONDITIONS_UNMEASURED")
    supplied = payload.get("configuration_results")
    if not isinstance(supplied, dict) or set(supplied) != set(CONFIGURATIONS):
        raise ValueError("explicit results for all six frozen configurations are required")
    if result["reasons"]:
        return result
    expected_ids = {r: sorted(x["unit_id"] for x in units[r]) for r in ROLES}
    denominators = {
        "pivot_identity_role_price_agreement": len(units["pivot"]),
        "complete_bullish_ladder_agreement": len(units["bullish"]),
        "complete_bearish_ladder_agreement": len(units["bearish"]),
        "end_to_end_eligible_source_recall": sum(x["eligible_source_occurrence_count"] for r in ROLES for x in units[r]),
        "bullish_extras_per_branch": len(units["bullish"]),
        "bearish_extras_per_branch": len(units["bearish"]),
    }
    vectors, abstentions = {}, {}
    for config in CONFIGURATIONS:
        row = supplied[config]
        if not isinstance(row, dict) or row.get("metric_basis") != "strict_common_primary_units":
            result["reasons"].append("NONSTRICT_METRIC_BASIS")
            continue
        ids = row.get("common_primary_unit_ids")
        if not isinstance(ids, dict) or set(ids) != set(ROLES):
            raise ValueError("metric vectors require explicit common unit IDs for all roles")
        for role in ROLES:
            _exact_inventory(ids[role], expected_ids[role], "metric common unit IDs")
        metrics = row.get("metrics") or {}
        if any(not isinstance(metrics.get(k), dict) or metrics[k].get("status") != "estimable" for k in METRICS):
            result["reasons"].append("STRICT_METRICS_NOT_ESTIMABLE")
            continue
        vectors[config] = {k: _ratio(metrics[k], k, denominators[k]) for k in METRICS}
        a = row.get("abstentions")
        if not isinstance(a, dict) or set(a) != set(ROLES):
            raise ValueError("abstention counts for every common role are required")
        abstentions[config] = {r: _integer(a[r], r + " abstention count") for r in ROLES}
        if any(abstentions[config][r] > len(units[r]) for r in ROLES):
            raise ValueError("abstention count exceeds common eligible opportunities")
    if result["reasons"]:
        result["reasons"] = sorted(set(result["reasons"]))
        return result
    result["identifiability_passed"] = True
    result["strict_metric_denominators"] = denominators
    comparisons = {}
    baseline = vectors[PRIMARY]
    for config in CONFIGURATIONS[1:]:
        no_worse = {k: METRICS[k] * (vectors[config][k] - baseline[k]) >= 0 for k in METRICS}
        better = [k for k in METRICS if METRICS[k] * (vectors[config][k] - baseline[k]) > 0]
        abstention_ok = {r: abstentions[config][r] <= abstentions[PRIMARY][r] for r in ROLES}
        qualifies = all(no_worse.values()) and bool(better) and all(abstention_ok.values())
        comparisons[config] = {"no_worse": no_worse, "strictly_better_metrics": better,
                               "abstention_not_increased": abstention_ok, "qualifies": qualifies}
        if qualifies:
            result["dominating_alternatives"].append(config)
    result["dominance_comparisons"] = comparisons
    if len(result["dominating_alternatives"]) == 1:
        result["selected_configuration"] = result["dominating_alternatives"][0]
        result["retained_engineering_default"] = None
        result["no_validated_configuration_selected"] = False
        result["status"] = "unique_development_alternative_selected"
        result["reasons"] = ["UNIQUE_STRICT_DOMINANCE_ON_COMMON_PRIMARY_UNITS"]
    else:
        result["reasons"] = ["NO_STRICT_DOMINATING_ALTERNATIVE" if not result["dominating_alternatives"] else "MULTIPLE_DOMINATING_ALTERNATIVES"]
    return result
