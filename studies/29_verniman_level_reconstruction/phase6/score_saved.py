#!/usr/bin/env python3
"""Fixed saved-map scoring after the complete prospective reveal gate.

The only format adaptations are the saved map schema tag and the explicit
twenty-date allowlist of the frozen window-metadata assessor. No detector,
selector, target priority, tolerance or construction is executed or changed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
POLICIES = {p + "-" + d for p in ("P0", "B0", "B1") for d in ("D0", "D1")}
ROLES = {"pivot": "conditional_scenario_divider", "bullish": "ordered_bullish_destination", "bearish": "ordered_bearish_destination"}
SNAPSHOT_ROLES = {"phase4_model", "saved_hydrator", "source_comparison", "source_roles", "window_adapter"}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


GATE = module("study29_phase6_scoring_gate", PHASE / "reveal_gate.py")


def load(path):
    return json.loads(Path(path).read_text())


def readable_interval(row):
    try:
        low, high = Decimal(str(row.get("price_low"))), Decimal(str(row.get("price_high")))
        return low.is_finite() and high.is_finite() and low <= high
    except (InvalidOperation, TypeError, ValueError):
        return False


def hydrate_saved(document, model, hydrator, scheduled_dates):
    if document.get("schema") not in {"abacus.study29.phase6.local-map/v1", "abacus.study29.phase6.local-prospective-map/v1", "abacus.study29.phase5.local-development-map/v1"} or document.get("session_date") not in scheduled_dates:
        raise ValueError("saved map must identify an exact scheduled date")
    if set(document.get("selections", {})) != POLICIES:
        raise ValueError("all six unchanged saved configurations required")
    compatible = dict(document)
    compatible["schema"] = "abacus.study29.phase4.local-training-map/v1"
    return hydrator.hydrate_map(compatible, model)


def analyze_saved(document, rows, model, hydrator, comparison, window_adapter, assessments, scheduled_dates):
    inputs, selections = hydrate_saved(document, model, hydrator, scheduled_dates)
    day = document["session_date"]
    selected_rows = [row for row in rows if row["session_date"] == day]
    original = comparison.source_refs
    comparison.source_refs = lambda records, matching: window_adapter.source_refs(records, matching, assessments, selected_rows)
    try:
        return {key: comparison.analyze_sources(day, selected_rows, inputs, choice, model) for key, choice in selections.items()}
    finally:
        comparison.source_refs = original


def _in_evidence_root(root, value, evidence_root):
    result = GATE.pinned(root, value)
    if not result.is_relative_to(evidence_root):
        raise ValueError("source evidence must stay inside the exact bounded collection root")
    return result


def preopen_support(row, root, evidence_root, access_log, cutoff):
    """Validate explicit same-revision capture evidence; never infer from a post timestamp."""
    supplied = row.get("preopen_availability_evidence")
    if supplied is None:
        return {"status": "unresolved_historical_availability", "supported": False}
    try:
        path = _in_evidence_root(root, supplied, evidence_root)
        proof = load(path)
        if proof.get("schema") != "abacus.study29.phase6.source-availability-evidence/v1":
            raise ValueError("explicit source-availability evidence schema required")
        if (proof.get("session_date"), proof.get("source_class"), proof.get("source_revision_id")) != (row["session_date"], row["source_class"], row["provenance"].get("source_revision_id")):
            raise ValueError("availability evidence must bind the same date/class/revision")
        if proof.get("same_revision_authenticated") is not True or proof.get("complete_plan_capture") is not True:
            raise ValueError("later timestamps or incomplete crops cannot authenticate a full preopen revision")
        if proof.get("timestamp_basis") not in {"contemporaneous_browser_capture_local_clock", "independently_timestamped_capture"}:
            raise ValueError("a displayed post/revision time alone is not preopen capture evidence")
        captured, available = GATE.aware(proof["captured_at"]), GATE.aware(proof["available_at"])
        if not available <= captured <= cutoff:
            raise ValueError("same-revision evidence was captured after cutoff or has incompatible clocks")
        if row.get("available_at") is None or GATE.aware(row["available_at"]) != available:
            raise ValueError("null availability cannot be silently repaired by a scoring assertion")
        _in_evidence_root(root, proof["source_artifact"], evidence_root)
        if proof["timestamp_basis"] == "independently_timestamped_capture":
            _in_evidence_root(root, proof["timestamp_certificate"], evidence_root)
        actors = {actor["actor_id"]: actor for actor in access_log["actors"]}
        actor = proof["collector_actor_id"]
        if actor not in actors or actors[actor]["role"] != "collector" or actor != row.get("collector_actor_id"):
            raise ValueError("independent source collector identity required")
        events = {event["event_id"]: event for event in access_log["events"]}
        event = events[proof["source_access_event_id"]]
        if event["actor_id"] != actor or event["kind"] != "answer_access" or event["session_date"] != row["session_date"] or event.get("source_class") != row["source_class"] or event.get("source_revision_id") != row["provenance"].get("source_revision_id") or GATE.aware(event["occurred_at"]) > captured:
            raise ValueError("preopen source access chronology is unsupported")
        if proof["source_access_event_id"] not in row.get("source_access_event_ids", []):
            raise ValueError("availability event is not linked to this original occurrence")
        return {"status": "supported_same_revision_preopen_capture", "supported": True, "evidence": supplied,
                "timestamp_basis": proof["timestamp_basis"], "captured_at": proof["captured_at"],
                "independent_timestamp_certification_claimed": proof["timestamp_basis"] == "independently_timestamped_capture"}
    except (ValueError, KeyError, TypeError, OSError) as error:
        return {"status": "provided_availability_evidence_unassessed", "supported": False,
                "evidence": supplied, "reason": str(error)}


def validate_source_ledger(ledger, gate, access_log, dates):
    if ledger.get("schema") != "abacus.study29.phase6.source-role-ledger/v1" or ledger.get("protocol_freeze") != gate["protocol_freeze"] or ledger.get("reveal_gate") != gate["gate"]:
        raise ValueError("source ledger must bind the exact completed reveal gate and protocol")
    rows = ledger.get("occurrences", [])
    identifiers = [row.get("level_id") for row in rows]
    if any(not i for i in identifiers) or len(set(identifiers)) != len(identifiers) or any(row.get("session_date") not in dates for row in rows):
        raise ValueError("unique original role occurrence IDs on scheduled dates required")
    sessions = ledger.get("session_records", [])
    if len(sessions) != len(dates) or {s.get("session_date") for s in sessions} != set(dates):
        raise ValueError("source status for every scheduled date required")
    actors = {actor["actor_id"]: actor for actor in access_log["actors"]}
    events = {event["event_id"]: event for event in access_log["events"]}
    for row in rows:
        actor = row.get("collector_actor_id")
        if actor not in actors or actors[actor]["role"] not in {"collector", "scorer"}:
            raise ValueError("every source occurrence needs its actual collecting/scoring actor")
        event_ids = row.get("source_access_event_ids")
        if not event_ids:
            raise ValueError("every source occurrence needs access chronology")
        for identifier in event_ids:
            event = events.get(identifier)
            if not event or event["actor_id"] != actor or event["kind"] != "answer_access" or event["session_date"] != row["session_date"]:
                raise ValueError("source actor/date/access event linkage differs")
    by_day = {session["session_date"]: session for session in sessions}
    for day, session in by_day.items():
        if session.get("source_review_status") not in {"available", "missing", "conflicting", "incomplete"}:
            raise ValueError("explicit source suitability status required")
        if session["source_review_status"] != "available" and not session.get("failure_reasons"):
            raise ValueError("unavailable/conflicting source needs its retained reason")
        canonical = session.get("canonical_source_revision_ids", [])
        if len(canonical) != len(set(canonical)):
            raise ValueError("canonical source revision IDs cannot repeat")
        actual = {row.get("provenance", {}).get("source_revision_id") for row in rows if row["session_date"] == day and row["source_class"] == "named_daily_plan"}
        if not set(canonical) <= actual:
            raise ValueError("canonical revision not present in original source occurrences")
    return rows, by_day


def validate_canonical_revisions(rows, sessions, preopen):
    """Choose by independent capture chronology, never agreement with a map."""
    for day, session in sessions.items():
        independently_preopen = {}
        for row in rows:
            assessment = preopen[row["level_id"]]
            if row["session_date"] == day and row["source_class"] == "named_daily_plan" and assessment["supported"]:
                revision = row["provenance"].get("source_revision_id")
                capture_time = GATE.aware(assessment["captured_at"])
                independently_preopen[revision] = min(independently_preopen.get(revision, capture_time), capture_time)
        if independently_preopen:
            first = min(independently_preopen.values())
            earliest = {revision for revision, clock in independently_preopen.items() if clock == first}
            if set(session.get("canonical_source_revision_ids", [])) != earliest:
                raise ValueError("canonical source choice must retain the earliest independently captured preopen plan; tied revisions remain conflicting")
        elif session.get("canonical_source_revision_ids"):
            raise ValueError("no authenticated preopen plan: retain every retrospective revision separately without selecting a canonical truth")


def summarize(records, configurations, *, minimum_dates=15, formal_batch_allowed=True):
    """Estimation/falsification only; missing captures and abstention stay visible."""
    result = {}
    for configuration in configurations:
        roles = {}
        for role in ROLES:
            units = [record for record in records if record.get("formal_role_eligibility", {}).get(role) is True]
            diagnostics = [record["canonical_analysis"][configuration][role]["coordinate_only_diagnostic"] for record in units]
            source = sum(d.get("source_count") or 0 for d in diagnostics)
            matched = sum(d.get("matched_count") or 0 for d in diagnostics)
            selected = sum(d.get("selected_count") or 0 for d in diagnostics)
            errors = [float(d["pivot_absolute_point_or_boundary_error"]) for d in diagnostics if d.get("pivot_absolute_point_or_boundary_error") is not None]
            def exact_ladder(diagnostic):
                pairs = diagnostic.get("assignments", [])
                return diagnostic.get("complete_coordinate_ladder") is True and bool(pairs) and all(pair.get("signed_point_or_boundary_error") is not None and abs(Decimal(pair["signed_point_or_boundary_error"])) <= 1 for pair in pairs)
            def quantile(values, fraction):
                if not values:
                    return None
                values = sorted(values); position = (len(values) - 1) * fraction
                lower = int(position); upper = min(lower + 1, len(values) - 1)
                return values[lower] + (values[upper] - values[lower]) * (position - lower)
            roles[role] = {"eligible_dates": [r["session_date"] for r in units], "eligible_date_count": len(units),
                "minimum_usable_dates": minimum_dates, "minimum_met": len(units) >= minimum_dates and formal_batch_allowed,
                "source_units": source, "coordinate_pairs": matched, "selected_physical_units": selected,
                "coordinate_extras": selected - matched, "source_misses": source - matched,
                "complete_ordered_ladders": sum(d.get("complete_coordinate_ladder") is True for d in diagnostics) if role != "pivot" else None,
                "incomplete_ordered_ladders": sum(d.get("complete_coordinate_ladder") is False for d in diagnostics) if role != "pivot" else None,
                "ordering_undefined_or_abstained": sum(d.get("complete_coordinate_ladder") is None for d in diagnostics) if role != "pivot" else None,
                "actual_point_or_boundary_complete_ladders": sum(exact_ladder(d) for d in diagnostics) if role != "pivot" else None,
                "actual_point_or_boundary_pair_count_within_one": sum(pair.get("signed_point_or_boundary_error") is not None and abs(Decimal(pair["signed_point_or_boundary_error"])) <= 1 for d in diagnostics for pair in d.get("assignments", [])),
                "pivot_actual_point_error": {"finite_point_denominator": len(errors), "mean_absolute": statistics.mean(errors) if errors else None,
                    "median_absolute": statistics.median(errors) if errors else None, "minimum_absolute": min(errors) if errors else None,
                    "maximum_absolute": max(errors) if errors else None, "q25_absolute_linear": quantile(errors, .25),
                    "q75_absolute_linear": quantile(errors, .75)} if role == "pivot" else None,
                "classification": "observable_map_geometry_only_not_construction_or_source_method_fidelity"}
        common = [r for r in records if all(r.get("formal_role_eligibility", {}).get(role) is True for role in ROLES)]
        full = 0
        actual_boundary_full = 0
        for record in common:
            values = record["canonical_analysis"][configuration]
            pivot = values["pivot"]["coordinate_only_diagnostic"]
            targets = [values[side]["coordinate_only_diagnostic"] for side in ("bullish", "bearish")]
            reproduced = pivot.get("matched_count") == 1 and pivot.get("selected_count") == 1 and all(d.get("complete_coordinate_ladder") is True for d in targets)
            full += bool(reproduced)
            # A feasible uncertainty overlap does not count as actual E1 boundary success.
            assignments = [pair for d in [pivot, *targets] for pair in d.get("assignments", [])]
            actual = bool(assignments) and all(pair.get("signed_point_or_boundary_error") is not None and abs(Decimal(pair["signed_point_or_boundary_error"])) <= 1 for pair in assignments)
            actual_boundary_full += bool(reproduced and actual)
        n = len(common)
        def wilson(successes):
            if not n:
                return None
            z = 1.959963984540054
            center = (successes / n + z*z/(2*n))/(1 + z*z/n)
            radius = z * math.sqrt(successes/n*(1-successes/n)/n + z*z/(4*n*n))/(1+z*z/n)
            return [max(0, center-radius), min(1, center+radius)]
        all_minimum = formal_batch_allowed and all(row["minimum_met"] for row in roles.values()) and n >= minimum_dates
        result[configuration] = {"roles": roles, "common_complete_source_dates": [r["session_date"] for r in common],
            "end_to_end_observable_map": {"date_denominator": n, "interval_qualified_reproductions": full,
                "minimum_usable_dates": minimum_dates, "minimum_met": n >= minimum_dates and formal_batch_allowed,
                "actual_point_or_boundary_reproductions": actual_boundary_full, "interval_reproduction_wilson95": wilson(full),
                "actual_boundary_reproduction_wilson95": wilson(actual_boundary_full),
                "uncertainty_qualification": "Nominal descriptive Bernoulli-independent working interval; serial dependence and overlapping history mean this is not a calibrated generalization confidence interval."},
            "formal_estimation_status": "minimum_met_estimation_only" if all_minimum else "descriptive_only_insufficient_or_exposed_sample",
            "validated_method": False, "configuration_switch_authorized": False}
    return result


def paired_differences(records, configurations, primary="P0-D1"):
    """Keep paired dates/errors explicit; no ranking, winner or policy change."""
    result = {}
    for configuration in configurations:
        if configuration == primary:
            continue
        result[configuration] = {}
        for role in ROLES:
            values = []
            for record in records:
                if not record.get("formal_role_eligibility", {}).get(role):
                    continue
                current = record["canonical_analysis"][configuration][role]["coordinate_only_diagnostic"]
                control = record["canonical_analysis"][primary][role]["coordinate_only_diagnostic"]
                def delta(key):
                    a, b = current.get(key), control.get(key)
                    return None if a is None or b is None else float(a) - float(b)
                def extras(diagnostic):
                    a, b = diagnostic.get("selected_count"), diagnostic.get("matched_count")
                    return None if a is None or b is None else a - b
                a, b = extras(current), extras(control)
                values.append({"session_date": record["session_date"],
                    "comparator_minus_primary_coordinate_pairs": delta("matched_count"),
                    "comparator_minus_primary_coordinate_extras": None if a is None or b is None else a-b,
                    "comparator_minus_primary_absolute_point_or_boundary_error": delta("pivot_absolute_point_or_boundary_error"),
                    "comparator_complete_interval_ladder": current.get("complete_coordinate_ladder"),
                    "primary_complete_interval_ladder": control.get("complete_coordinate_ladder")})
            error = [row["comparator_minus_primary_absolute_point_or_boundary_error"] for row in values if row["comparator_minus_primary_absolute_point_or_boundary_error"] is not None]
            result[configuration][role] = {"primary": primary, "paired_date_count": len(values), "per_session": values,
                "finite_point_error_pair_denominator": len(error),
                "mean_comparator_minus_primary_absolute_point_or_boundary_error": statistics.mean(error) if error else None,
                "classification": "paired_observable_geometry_on_identical_eligible_dates_no_winner_or_method_claim"}
    return result


def autopivot_diagnostics(document, canonical_analysis, canonical_rows, comparison, model):
    saved = document.get("autopivot_comparator")
    if not saved:
        return {"status": "saved_immutable_comparator_unavailable", "is_target": False}
    pivot = canonical_analysis["P0-D1"]["pivot"]
    interpretation = pivot.get("primary_pivot_interpretation") or {}
    units = interpretation.get("source_strata", [])
    if interpretation.get("status") != "unique_common_functional_divider" or len(units) != 1:
        return {"status": "unresolved_single_divider", "saved_comparator": saved, "is_target": False}
    unit = units[0]
    source = dict(next(row for row in canonical_rows if row["phase4_role"] == ROLES["pivot"]))
    source.update(level_id=unit["unit_id"], price_low=unit["primary_price_interval"][0], price_high=unit["primary_price_interval"][1], source_target_order=None)
    selection = (saved.get("frozen") or {}).get("selection") or {}
    values = {"primary": selection.get("price"), "alternate": (saved.get("alternate_model_only") or {}).get("price")}
    diagnostics = {}
    for kind, price in values.items():
        generated = [] if price is None else [{"candidate_id": "immutable-autopivot-" + kind, "interval": [price, price], "price": price}]
        diagnostics[kind] = comparison.coordinate_diagnostic([source], generated, model._matching_module(), 1)
        if price is not None:
            exact = source["price_low"] == source["price_high"]
            signed = Decimal(str(price)) - Decimal(str(source["price_low"])) if exact else None
            diagnostics[kind].update(
                pivot_signed_point_or_boundary_error=str(signed) if signed is not None else None,
                pivot_absolute_point_or_boundary_error=str(abs(signed)) if signed is not None else None,
                pivot_interval_gap_points=str(model._matching_module().interval_gap((source["price_low"], source["price_high"]), (price, price))))
    return {"status": "saved_pivot_geometry_only", "diagnostics": diagnostics, "is_target": False,
        "source_identity": {"pine_sha256": saved.get("pine_sha256"), "model_sha256": saved.get("model_sha256")},
        "input_policy_difference": saved.get("input_policy_difference"),
        "qualification": "Immutable Phase4 comparator translated output, not fresh native execution or construction-qualified fidelity; alternate is never a target."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_path, output = (ROOT / args.manifest).resolve(), (ROOT / args.output).resolve()
    manifest = load(manifest_path)
    if manifest.get("schema") != "abacus.study29.phase6.saved-scoring-inputs/v1":
        raise ValueError("explicit prospective saved-scoring manifest required")
    stage = (ROOT / manifest["stage"]).resolve()
    if not stage.is_relative_to(ROOT / "work/29_verniman_level_reconstruction") or output.parent != stage or output.exists() or not manifest_path.is_relative_to(stage):
        raise ValueError("fresh scoring output in the exact Phase6 stage required")
    gate = GATE.validate_saved_gate(ROOT, GATE.pinned(ROOT, manifest["reveal_gate"]))
    freeze_path = GATE.pinned(ROOT, gate["protocol_freeze"])
    freeze = load(freeze_path)
    if manifest.get("protocol_freeze") != gate["protocol_freeze"]:
        raise ValueError("scoring protocol differs from the reveal gate")
    # All answer-role and evidence reads occur only after the recomputed gate.
    evidence_root = (ROOT / manifest["source_evidence_root"]).resolve()
    if not evidence_root.is_relative_to(stage):
        raise ValueError("bounded source collection root must be inside the exact stage")
    source_path = _in_evidence_root(ROOT, manifest["source_ledger"], evidence_root)
    ledger = load(source_path)
    access_path = GATE.pinned(ROOT, manifest["source_access_log"])
    access = load(access_path)
    GATE.validate_access_log(access, freeze["scheduled_dates"], GATE.aware(gate["recorded_at"]))
    if GATE.aware(access["closed_through"]) > datetime.now(timezone.utc):
        raise ValueError("source access audit cannot attest a future closure")
    old_access = load(GATE.pinned(ROOT, gate["access_log"]))
    latest_events = {event["event_id"]: event for event in access["events"]}
    if any(latest_events.get(event["event_id"]) != event for event in old_access["events"]):
        raise ValueError("source access history changed after reveal")
    current_actors = {actor["actor_id"]: actor for actor in access["actors"]}
    if any(current_actors.get(actor["actor_id"]) != actor for actor in old_access["actors"]):
        raise ValueError("actor identity or role changed after reveal")
    predictors = {actor["actor_id"] for actor in access["actors"] if actor["role"] == "prediction"}
    old_events = {event["event_id"] for event in old_access["events"]}
    if any(event["event_id"] not in old_events and GATE._affected(event, predictors) is not None and GATE.aware(event["occurred_at"]) <= GATE.aware(gate["recorded_at"]) for event in access["events"]):
        raise ValueError("newly disclosed pre-gate predictor answer access contradicts the frozen reveal audit")
    rows, sessions = validate_source_ledger(ledger, gate, access, freeze["scheduled_dates"])
    readable_rows = [row for row in rows if row.get("phase4_role") not in set(ROLES.values()) or readable_interval(row)]
    for source in ledger.get("source_artifacts", []):
        _in_evidence_root(ROOT, source, evidence_root)
    producers = {row["role"]: row for row in freeze["producer_files"]}
    if not SNAPSHOT_ROLES <= set(producers):
        raise ValueError("fixed scoring snapshot dependencies incomplete")
    paths = {role: GATE.pinned(ROOT, {"path": row["snapshot_path"], "sha256": row["sha256"]}) for role, row in producers.items()}
    model = module("study29_phase6_frozen_model", paths["phase4_model"])
    hydrator = module("study29_phase6_frozen_hydrator", paths["saved_hydrator"])
    comparison = module("study29_phase6_frozen_comparison", paths["source_comparison"])
    windows = module("study29_phase6_frozen_windows", paths["window_adapter"])
    windows.DATES = set(freeze["scheduled_dates"])
    assessments = {row["level_id"]: windows.assess(row, ROOT, allowed_evidence_roots=[evidence_root]) for row in rows}
    preopen = {}
    for row in rows:
        cutoff = datetime.fromisoformat(row["session_date"] + "T09:25:00").replace(tzinfo=windows.NY)
        preopen[row["level_id"]] = preopen_support(row, ROOT, evidence_root, access, cutoff)
    validate_canonical_revisions(rows, sessions, preopen)
    captures = {row["session_date"]: row for row in gate["captures"]}
    records = []
    for day in freeze["scheduled_dates"]:
        capture, session = captures[day], sessions[day]
        record = {"session_date": day, "capture_status": capture["status"], "source_status": session,
                  "formal_role_eligibility": {role: False for role in ROLES}, "analysis_all_source_strata": None,
                  "canonical_analysis": None, "selection_recomputed": False,
                  "all_original_role_occurrence_counts": {role: sum(row["session_date"] == day and row.get("phase4_role") == source_role for row in rows) for role, source_role in ROLES.items()},
                  "unreadable_source_occurrence_ids": [row["level_id"] for row in rows if row["session_date"] == day and row not in readable_rows]}
        if capture.get("prediction") and capture.get("complete_expanded_map") is True:
            document = load(GATE.pinned(ROOT, capture["prediction"]))
            record["analysis_all_source_strata"] = analyze_saved(document, readable_rows, model, hydrator, comparison, windows, assessments, freeze["scheduled_dates"])
            revisions = session.get("canonical_source_revision_ids", [])
            canonical = [row for row in rows if row["session_date"] == day and row["source_class"] == "named_daily_plan" and len(revisions) == 1 and row["provenance"].get("source_revision_id") == revisions[0]]
            if canonical:
                analysis = analyze_saved(document, [row for row in canonical if row in readable_rows], model, hydrator, comparison, windows, assessments, freeze["scheduled_dates"])
                record["canonical_analysis"] = analysis
                record["autopivot_pivot_comparator"] = autopivot_diagnostics(document, analysis, canonical, comparison, model)
                for role, source_role in ROLES.items():
                    role_rows = [row for row in canonical if row["phase4_role"] == source_role]
                    diagnostic = analysis["P0-D1"][role].get("coordinate_only_diagnostic", {})
                    readable = bool(role_rows) and all(readable_interval(row) for row in role_rows)
                    if role == "pivot":
                        unambiguous = analysis["P0-D1"][role].get("primary_pivot_interpretation", {}).get("status") == "unique_common_functional_divider"
                    else:
                        orders = [r.get("source_target_order") for r in role_rows]
                        unambiguous = bool(orders) and all(type(order) is int and order > 0 for order in orders) and len(orders) == len(set(orders))
                    record["formal_role_eligibility"][role] = bool(capture["status"] == "timely" and session["source_review_status"] == "available" and gate["formal_prospective_estimation_allowed"] and readable and unambiguous and all(preopen[row["level_id"]]["supported"] for row in role_rows))
        elif capture.get("prediction"):
            record["comparison_not_executed_reason"] = "Incomplete expanded map retained as an unsupported capture; no failure placeholder is scored as a prediction."
        records.append(record)
    summary = {"schema": "abacus.study29.phase6.saved-score-summary/v1", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "protocol_freeze": gate["protocol_freeze"], "reveal_gate": gate["gate"], "input_manifest": GATE.pin(ROOT, manifest_path),
        "source_ledger": manifest["source_ledger"], "source_access_log": manifest["source_access_log"],
        "scheduled_count": 20, "all_scheduled_statuses": [{"session_date": r["session_date"], "capture_status": r["capture_status"], "source_status": r["source_status"]["source_review_status"]} for r in records],
        "aggregate": summarize(records, freeze["configurations"], minimum_dates=15, formal_batch_allowed=gate["formal_prospective_estimation_allowed"]),
        "paired_configuration_differences": paired_differences(records, freeze["configurations"]),
        "source_window_assessments": assessments, "preopen_availability_assessments": preopen,
        "source_method_fidelity": {"status": "not_estimable", "reason": "Frozen mechanism leaves essential VIX/CVD conditions unmeasured; exact construction/window results remain separately qualified", "validated_method": False},
        "selection_recomputed": False, "candidate_inputs_modified": False, "configuration_switch_authorized": False,
        "format_adaptations": ["in-memory saved-map schema tag", "explicit frozen prospective date allowlist for unchanged window metadata assessor"],
        "automatic_winner_selected": False, "records": []}
    output.mkdir()
    for record in records:
        path = output / (record["session_date"] + ".json")
        with path.open("x") as handle:
            json.dump(record, handle, indent=2, allow_nan=False); handle.write("\n")
        summary["records"].append({"session_date": record["session_date"], **GATE.pin(ROOT, path)})
    with (output / "summary.json").open("x") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False); handle.write("\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "scheduled_dates": 20, "selection_recomputed": False,
                      "source_method_fidelity": "not_estimable", "automatic_winner_selected": False}))


if __name__ == "__main__":
    main()
