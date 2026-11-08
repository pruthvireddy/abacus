#!/usr/bin/env python3
"""Present immutable Phase 5 comparisons; no selector or market computation.

The numerical source comparisons are already saved. This renderer aggregates
their declared coordinate diagnostics and indexes every original occurrence.
It cannot choose a configuration or change any candidate/prediction/source fact.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import shutil
from statistics import median
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
DATES = ("2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20")
CONFIGS = ("P0-D1", "P0-D0", "B0-D0", "B0-D1", "B1-D0", "B1-D1")
NY = ZoneInfo("America/New_York")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": digest(path), "size_bytes": path.stat().st_size}


def read_pinned(record):
    path = (ROOT / record["path"]).resolve()
    if not path.is_relative_to(ROOT) or digest(path) != record["sha256"]:
        raise ValueError("saved presentation input differs: " + str(record.get("path")))
    return json.loads(path.read_text())


def number(value):
    return format(Decimal(str(value)).normalize(), "f") if value is not None else "Not estimable"


def timing(row):
    provenance = row.get("provenance") or {}
    update = provenance.get("source_claimed_updated_at")
    observed = datetime.fromisoformat(update.replace("Z", "+00:00")).astimezone(NY) if update else None
    cutoff = datetime.combine(date.fromisoformat(row["session_date"]), datetime.min.time(), NY).replace(hour=9, minute=25)
    published = provenance.get("source_posted_at")
    return {"historical_available_at": row.get("available_at"), "claimed_update_new_york": observed.isoformat() if observed else None,
            "claimed_update_after_cutoff": observed > cutoff if observed else None,
            "claimed_published_year_differs_from_stated_session": published[:4] != row["session_date"][:4] if published else None,
            "preopen_unchanged_content_established": False,
            "qualification": "Retained captured revision is descriptive evidence; null availability and claimed publication/update clocks do not establish original preopen content."}


def nearest(row, candidates):
    if row.get("price_low") is None or row.get("price_high") is None:
        return []
    low, high = Decimal(str(row["price_low"])), Decimal(str(row["price_high"]))
    result = []
    for candidate in candidates:
        interval = candidate.get("interval")
        if interval is None or candidate.get("price") is None:
            continue
        a, b = (Decimal(str(value)) for value in interval)
        gap = max(Decimal(0), low - b, a - high)
        point = Decimal(str(candidate["price"]))
        result.append({"candidate_id": candidate["candidate_id"], "price": candidate["price"], "interval": interval,
                       "family": candidate["family"], "origin_role": candidate.get("origin_role"), "window": candidate["window"], "profile_id": candidate["profile_id"],
                       "declared_ready": candidate["ready"], "unavailable_reasons": candidate.get("unavailable_reasons", []),
                       "interval_gap_points": str(gap), "point_or_boundary_error": str(point - low) if low == high else None,
                       "construction_identity_claimed": False})
    result.sort(key=lambda item: (Decimal(item["interval_gap_points"]), abs(Decimal(item["point_or_boundary_error"])) if item["point_or_boundary_error"] is not None else Decimal(0), item["candidate_id"]))
    return result[:5]


def occurrence_choices(row, prediction, comparison, comparison_pin, identity):
    canonical = row["source_class"] == "named_daily_plan" and row["phase4_role"] in {"conditional_scenario_divider", "ordered_bullish_destination", "ordered_bearish_destination"}
    role = "pivot" if row["phase4_role"] == "conditional_scenario_divider" else "bullish" if row["phase4_role"] == "ordered_bullish_destination" else "bearish" if row["phase4_role"] == "ordered_bearish_destination" else None
    status = "canonical_role_compared; exact_window_unresolved" if canonical else "noncanonical_recollection_descriptive_only" if row["source_class"] == "user_supplied_recollection" else "structural_or_annotation_without_selected_scenario_truth"
    policies = {}
    for key in CONFIGS:
        if not canonical:
            continue
        saved = comparison["analysis"][key][role]
        strict = saved.get("strict_decomposition") or {}
        raw = saved.get("raw_source_occurrence_decomposition") or strict
        outcome = next((item for item in raw.get("source_outcomes", []) if item["source_id"] == row["level_id"]), None)
        generation = raw.get("generation") or {}
        family_alternatives = [item for item in generation.get("unresolved_alternatives", []) if item.get("source_id") == row["level_id"]]
        diagnostic = saved.get("coordinate_only_diagnostic") or {}
        assignments = [item for item in diagnostic.get("assignments", []) if item.get("source_id") == row["level_id"]]
        primary = saved.get("primary_pivot_interpretation")
        units = [unit for unit in (primary or {}).get("source_strata", []) if any(item["source_occurrence_id"] == row["level_id"] for item in unit["source_occurrences"])]
        policies[key] = {"role": role, "strict_status": strict.get("status"), "raw_occurrence_outcome": outcome,
                         "family_qualified_but_window_unresolved_candidates": family_alternatives,
                         "coordinate_only_assignments": assignments, "single_pivot_interpretation_units": units,
                         "raw_trigger_occurrences_are_not_independent_pivot_units": role == "pivot",
                         "strict_construction_coverage_established": False, "analysis_artifact": comparison_pin}
    return {"source_occurrence_id": row["level_id"], "session_date": row["session_date"], "source_class": row["source_class"], "source_revision_id": row.get("provenance", {}).get("source_revision_id"),
            "original_label": row["original_label"], "source_role": row["phase4_role"], "source_target_order": row.get("source_target_order"),
            "status": status, "construction_window_identity_supported": None, "strict_generation_outcome": None, "strict_selection_outcome": None, "strict_role_and_order_agreement": None,
            "window_identity_assessment": identity, "historical_timing": timing(row), "competing_coordinate_only_candidates": nearest(row, prediction["selector_inputs"]["candidates"]),
            "policy_evaluations": policies, "analysis_artifact": comparison_pin, "source_price_inserted_into_candidate_pool": False}


def build(stage):
    summary_path = stage / "saved-analysis-1/summary.json"
    summary = json.loads(summary_path.read_text())
    ledger_pin = summary["source_ledger"]; ledger = read_pinned(ledger_pin)
    records = {item["session_date"]: (read_pinned(item), item) for item in summary["records"]}
    if set(records) != set(DATES):
        raise ValueError("all four saved comparison records required")
    predictions = {day: read_pinned(record["map"]) for day, (record, _) in records.items()}
    assessment_path = stage / "decision-assessment-1/assessment.json"
    assessment = json.loads(assessment_path.read_text())
    if assessment.get("coordinate_metrics_used_for_selection") is not False or assessment.get("selected_configuration") is not None:
        raise ValueError("this final report expects the retained no-validated-selection assessment")
    identity = {item["source_occurrence_id"]: item for record, _ in records.values() for item in record["source_window_identity_assessments"]}
    choices = [occurrence_choices(row, predictions[row["session_date"]], records[row["session_date"]][0], records[row["session_date"]][1], identity[row["level_id"]]) for row in ledger["occurrences"]]
    assessed = deepcopy(ledger)
    for row, choice in zip(assessed["occurrences"], choices):
        row["comparison"] = choice
    assessed.update(schema="abacus.study29.phase5.assessed-source-role-ledger/v1", original_source_role_input=ledger_pin, saved_analysis_summary=pin(summary_path), assessment=pin(assessment_path), source_fact_fields_changed=False)
    choice_index = {"schema": "abacus.study29.phase5.candidate-choice-ledger/v1", "recorded_at": datetime.now(timezone.utc).isoformat(), "source_role_input": ledger_pin, "saved_analysis_summary": pin(summary_path), "source_occurrence_count": len(choices), "occurrences": choices, "selection_recomputed": False,
                    "limits": "All source observations remain. Canonical roles are compared separately; recollections/structural references do not enter canonical metric denominators. Nearby candidates do not establish construction identity."}
    per_session = []
    aggregate = {key: {side: Counter() for side in ("bullish", "bearish")} for key in CONFIGS}
    for day in DATES:
        prediction, (comparison, comparison_pin) = predictions[day], records[day]
        source_rows = [row for row in ledger["occurrences"] if row["session_date"] == day and row["source_class"] == "named_daily_plan"]
        canonical = [row for row in source_rows if row["phase4_role"] != "structural_reference_without_selected_scenario_role"]
        pivots, configurations = {}, {}
        for policy in ("P0", "B0", "B1"):
            key = policy + "-D1"; selected = prediction["selections"][key]["pivot"]
            diagnostic = comparison["analysis"][key]["pivot"].get("coordinate_only_diagnostic") or {}
            pivots[policy] = {"candidate": selected["candidate"], "reason_code": selected["reason_code"], "fallback": selected["fallback"], "status": selected["status"], "signed_error": diagnostic.get("pivot_signed_point_or_boundary_error"), "absolute_error": diagnostic.get("pivot_absolute_point_or_boundary_error"), "interval_gap": diagnostic.get("pivot_interval_gap_points"), "primary_strict_status": comparison["analysis"][key]["pivot"].get("strict_decomposition", {}).get("status")}
        for key in CONFIGS:
            configurations[key] = {}
            for side in ("bullish", "bearish"):
                branch = prediction["selections"][key][side]
                diagnostic = comparison["analysis"][key][side]["coordinate_only_diagnostic"]
                matched = diagnostic.get("matched_count") or 0
                current = {"source_target_count": diagnostic["source_count"], "selected_count": diagnostic["selected_count"], "coordinate_pairs": matched,
                           "coordinate_extras": diagnostic["selected_count"] - matched, "unmatched_source_count": diagnostic["source_count"] - matched,
                           "complete_coordinate_ladder": diagnostic["complete_coordinate_ladder"], "relative_order_on_matched_subset": diagnostic.get("relative_order_on_matched_subset"),
                           "status": branch["status"], "targets": branch["targets"], "strict_status": comparison["analysis"][key][side]["strict_decomposition"]["status"], "strict_family_window_coverage": None}
                configurations[key][side] = current
                totals = aggregate[key][side]
                totals.update(source_targets=current["source_target_count"], selected=current["selected_count"], coordinate_pairs=matched, extras=current["coordinate_extras"], unmatched_source=current["unmatched_source_count"],
                              complete_ladders=int(current["complete_coordinate_ladder"] is True), abstained_dates=int(branch["status"] == "unavailable"), partial_dates=int(branch["status"] == "partial"), scheduled_branch_dates=1)
        per_session.append({"session_date": day, "map": comparison["map"], "comparison": comparison_pin, "source_revision_ids": sorted({row["provenance"]["source_revision_id"] for row in canonical}),
                            "source_divider_occurrences": [row for row in canonical if row["phase4_role"] == "conditional_scenario_divider"], "source_destinations": {side: sorted([{"source_id": row["level_id"], "label": row["original_label"], "interval": [row["price_low"], row["price_high"]], "order": row["source_target_order"]} for row in canonical if row["phase4_role"] == "ordered_" + side + "_destination"], key=lambda row: row["order"]) for side in ("bullish", "bearish")},
                            "source_timing": timing(canonical[0]), "pivots": pivots, "configurations": configurations})
    pivot_aggregate = {}
    for policy in ("P0", "B0", "B1"):
        errors = [Decimal(item["pivots"][policy]["absolute_error"]) for item in per_session if item["pivots"][policy]["absolute_error"] is not None]
        gaps = [Decimal(item["pivots"][policy]["interval_gap"]) for item in per_session if item["pivots"][policy]["interval_gap"] is not None]
        pivot_aggregate[policy] = {"coordinate_only_common_dates": len(errors), "dates": [item["session_date"] for item in per_session], "mean_absolute_error": str(sum(errors) / len(errors)) if errors else None, "median_absolute_error": str(median(errors)) if errors else None,
                                   "point_or_boundary_within_one": sum(value <= 1 for value in errors), "interval_gap_within_one": sum(value <= 1 for value in gaps), "supported_window_metric": None}
    result = {"schema": "abacus.study29.phase5.development-results/v1", "recorded_at": datetime.now(timezone.utc).isoformat(), "source_ledger": ledger_pin, "saved_analysis_summary": pin(summary_path), "assessment": pin(assessment_path), "pre_answer_gate": summary["reveal_gate"]["gate"],
              "source_occurrence_count": len(choices), "source_role_counts": dict(Counter(row["phase4_role"] for row in ledger["occurrences"])), "canonical_plan_role_count": sum(row["source_class"] == "named_daily_plan" and row["phase4_role"] != "structural_reference_without_selected_scenario_role" for row in ledger["occurrences"]),
              "pivot_coordinate_diagnostics": pivot_aggregate, "target_coordinate_diagnostics": aggregate, "per_session": per_session,
              "strict_primary_outcomes": {"common_eligible_dates": assessment["common_eligible_dates"], "common_eligible_unit_counts": assessment["common_eligible_unit_counts"], "status": "not_estimable", "zero_is_not_zero_percent": True},
              "selected_configuration": assessment["selected_configuration"], "retained_engineering_default": assessment["retained_engineering_default"], "no_validated_configuration_selected": assessment["no_validated_configuration_selected"], "source_method_final_evaluation_ready": assessment["source_method_final_evaluation_ready"],
              "selection_recomputed": False, "candidate_inputs_modified": False, "source_prices_inserted_into_candidates": False, "hidden_test_executed": False, "source_suitability_limits": ["All available_at values remain null; claimed 2009 publication and 2026 body/update dates are preserved, not reconciled into causal availability.", "October 20's captured revision claims an update at 10:26:57.412 New York, after 09:25; preopen unchanged content is not established.", "No explicit compatible exact-window metadata was supplied; VIX/CVD remain unmeasured and first-pass PBT anchors remain missing."]}
    return result, choice_index, assessed


def markdown(result):
    lines = ["# Phase 5 development comparison", "", "**No validated configuration is selected. P0+D1 remains the frozen engineering default.** The four complete predictions and all six configurations were hashed before answer access; native P0+D1 cutoff/advance/restart checks passed on each date. Exact source-window identity is unsupported on every canonical role, and VIX/CVD remain unmeasured, so the predeclared identifiability gate fails. No policy was fitted or rerun on answers.", "",
             "The [assessed source ledger](source-role-ledger-assessed.json) and [candidate-choice index](candidate-choice-ledger.json) retain all **98 occurrences**. The original [source-role input](source-role-ledger.json) remains unchanged. Canonical data contains 27 role occurrences: eight branch triggers forming four common price dividers, ten bullish destinations and nine bearish destinations. Each date has one retained canonical revision; recollections, closing references and execution annotations remain separate classes.", "", "## Source suitability and timing", "",
             "All four scheduled sessions remain in descriptive price diagnostics. Every `available_at` is null. The retained sources claim 2009 publication dates while their ESZ26 bodies and claimed updates refer to2026; these clocks do not establish unchanged pre-open content. **October20's captured revision claims a10:26:57.412NewYork update, after09:25.** It remains qualified retrospective source evidence, without an inferred pre-open revision.", "",
             "| Date | Literal common divider | Ordered bullish destinations | Ordered bearish destinations | Claimed update (New York) |", "|---|---|---|---|---|"]
    for item in result["per_session"]:
        divider = item["source_divider_occurrences"][0]["original_label"]
        destinations = [" → ".join(row["label"] for row in item["source_destinations"][side]) for side in ("bullish", "bearish")]
        lines.append("| " + " | ".join((item["session_date"], divider, *destinations, item["source_timing"]["claimed_update_new_york"] or "Unknown")) + " |")
    lines += ["", "## Saved primary decisions", "", "| Date | P0 pivot / reason | D1 bullish | D1 bearish | Fallback / branch status |", "|---|---|---|---|---|"]
    for item in result["per_session"]:
        pivot = item["pivots"]["P0"]; branches = item["configurations"]["P0-D1"]
        values = [", ".join(number(target["candidate"]["price"]) for target in branches[side]["targets"]) or "Abstain" for side in ("bullish", "bearish")]
        lines.append("| " + " | ".join((item["session_date"], number(pivot["candidate"]["price"]) + " / " + pivot["reason_code"], *values, str(pivot["fallback"]) + "; " + branches["bullish"]["status"] + " / " + branches["bearish"]["status"])) + " |")
    lines += ["", "October16uses the declared prior-VAH fallback and abstains from both branches. B1 chooses the same pivot price without fallback and saves active targets; that policy difference remains visible. Native/model parity is implementation evidence, not independent source-method agreement.", "", "## Pivot geometry on the common four-date denominator", "", "| Policy | Dates | Mean absolute point/boundary error | Median | Within1point | Interval gap within1point |", "|---|---|---|---|---|---|"]
    for policy, values in result["pivot_coordinate_diagnostics"].items():
        lines.append("| " + " | ".join((policy, str(values["coordinate_only_common_dates"]), number(values["mean_absolute_error"]), number(values["median_absolute_error"]), str(values["point_or_boundary_within_one"]) + "/4", str(values["interval_gap_within_one"]) + "/4")) + " |")
    lines += ["", "| Date | P0 signed error | B0 signed error | B1 signed error |", "|---|---|---|---|"]
    for item in result["per_session"]:
        lines.append("| " + " | ".join((item["session_date"], *(number(item["pivots"][policy]["signed_error"]) for policy in ("P0", "B0", "B1")))) + " |")
    lines += ["", "P0 and B1 choose the same four pivot prices; neither improves on the other geometrically. Both have lower descriptive error than B0. This does not establish identity/role agreement or support a configuration switch. Source timing qualifications apply to the full four-date denominator.", "", "## Target coordinates, extras and order", "",
              "These are unqualified coordinate-only one-to-one counts within each canonical class/revision/branch stratum, using the frozen one-point interval-gap contract. They do not establish construction coverage. Every source destination remains, with common denominators **10 bullish /9 bearish targets across four sessions**. `Pairs/extras` means matched source-selected coordinate pairs and unmatched physical selections.", "", "| Configuration | Bull pairs /source | Bull selected /extras | Bear pairs /source | Bear selected /extras | Abstaining dates (bull/bear) | Partial dates (bull/bear) |", "|---|---|---|---|---|---|---|"]
    for key, branches in result["target_coordinate_diagnostics"].items():
        bull, bear = branches["bullish"], branches["bearish"]
        lines.append("| " + " | ".join((key, f"{bull['coordinate_pairs']}/{bull['source_targets']}", f"{bull['selected']}/{bull['extras']}", f"{bear['coordinate_pairs']}/{bear['source_targets']}", f"{bear['selected']}/{bear['extras']}", f"{bull['abstained_dates']}/{bear['abstained_dates']}", f"{bull['partial_dates']}/{bear['partial_dates']}")) + " |")
    lines += ["", "| Date /branch | Source targets | P0-D1 pairs/extras | P0-D0 | B0-D0 | B0-D1 | B1-D0 | B1-D1 |", "|---|---|---|---|---|---|---|---|"]
    for item in result["per_session"]:
        for side in ("bullish", "bearish"):
            branches = [item["configurations"][key][side] for key in CONFIGS]
            values = ["Abstain" if branch["status"] == "unavailable" else f"{branch['coordinate_pairs']}/{branch['coordinate_extras']}" for branch in branches]
            lines.append("| " + " | ".join((item["session_date"] + " / " + side, str(branches[0]["source_target_count"]), *values)) + " |")
    lines += ["", "No configuration reproduces a complete canonical branch ladder, even by coordinate-only matching. For P0, the two October16branches are explicitly abstained with undefined ordering; the other six branch/date sequences are incomplete. B0/B1 keep all eight branch/date units and also reproduce no complete ladder. A matched subsequence or an E1 interval touch is not exact boundary or full-order agreement. The JSON retains selected IDs, target ranks, unmatched references, extras, complete-order outcomes and competing/equal-optimum assignments for every configuration.", "", "## Why the misses do not authorize new rules", "",
              "- October15: P0 selects prior YVAL7748 for a below-value reclaim; the source prints YVAL7746. D1's own-auction exit7796 skips the earlier source GAP7764. Source profile construction and the GAP's origin remain unverified.",
              "- October16: the source divider is YHOD7802. A generated prior-RTH high7801.75 is nearby, while the frozen P0 rule falls back to prior VAH7796 and abstains. This is a diagnostic range-versus-value role counterexample, without established exact source-window identity.",
              "- October19: source HVE7730 versus selected prior VAH7760 is a30-point disagreement. A generated RTH E1 at7732 has interval[7730,7734]; its touch is not exact boundary agreement, and it is not selected. D1's source ONH/YHOD coordinate matches do not repair the divider or whole ladder.",
              "- October20: source HVE7730 versus prior YVAL7736 differs by6points. Its late claimed source update remains unresolved. Source GAP/POC destinations and the final HVE order are not recovered by the bounded VA/range itinerary.", "",
              "GAP/SOC origins, exact source profiles and causal PBT anchors remain unresolved. Modal centers are excluded by the declared target policy; no source price or back-solved anchor is inserted to repair these misses.", "", "## Frozen decision and final-evaluation status", "",
              "The predeclared engineering gate passes. The strict common eligible denominator is **zero dates/units for pivot and both branches**, and essential VIX/CVD inputs are unmeasured. Source-method availability, conditional strict selection accuracy, exact role/order and end-to-end reproduction are **not estimable**, not zero percent. The strict assessor selects no validated configuration and retains P0+D1 solely as the engineering default; coordinate counts cannot override that rule.", "",
              "The original hidden period has recorded prior answer exposure. A fresh evaluator cannot erase that history. A valid source-method final evaluation is not ready; Phase6 must not be executed under this record. A separately authorized prospective period needs predictions and source timing/identity freezes before answers. No replacement answers, trading P&L, publication or deployment were inspected or performed.", "",
              "See the [JSON evidence](development-results.json), [final assessment](final-assessment.md), [verification](verification.md), [candidate-choice index](candidate-choice-ledger.json) and [Phase6 handoff](phase6-handoff.md)."]
    # Presentation-only readability, without changing any source label or JSON fact.
    text = "\n".join(lines) + "\n"
    for before, after in (("October15", "October 15"), ("October16", "October 16"), ("October19", "October 19"), ("October20", "October 20"), ("Phase6", "Phase 6"), ("within1point", "within 1 point"), ("/9 bearish", "/ 9 bearish"), ("refer to2026", "refer to 2026"), ("a10:26", "a 10:26"), (".412NewYork", ".412 New York"), ("after09:25", "after 09:25"), ("a30-point", "a 30-point"), ("by6points", "by 6 points"), ("uses the", " uses the"), ("branches are", " branches are")):
        text = text.replace(before, after)
    text = re.sub(r"\b(YVAL|YVAH|VAH|YHOD|HVE|GAP)(\d)", r"\1 \2", text)
    for before, after in (("Within1point", "Within 1 point"), ("exit7796", "exit 7796"), ("high7801", "high 7801"), ("at7732", "at 7732"), ("interval[", "interval [")):
        text = text.replace(before, after)
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--stage", type=Path, required=True); parser.add_argument("--revision", required=True)
    args = parser.parse_args(); stage = (ROOT / args.stage).resolve(); revision = stage / args.revision
    if revision.exists() or not revision.is_relative_to(stage):
        raise ValueError("use a fresh retained presentation revision")
    result, choice, assessed = build(stage)
    outputs = {"development-results.md": markdown(result), "development-results.json": result, "candidate-choice-ledger.json": choice, "source-role-ledger-assessed.json": assessed}
    revision.mkdir()
    inputs = [stage / "saved-analysis-1/summary.json", PHASE / "source-role-ledger.json", stage / "decision-assessment-1/assessment.json", Path(__file__).resolve()]
    for path in inputs:
        target = revision / "input-snapshots" / path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
    before = []
    for name, value in outputs.items():
        path = PHASE / name
        if path.exists():
            previous = revision / "before" / name; previous.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, previous); before.append(pin(previous))
        text = value if isinstance(value, str) else json.dumps(value, indent=2, allow_nan=False) + "\n"
        path.write_text(text); (revision / name).write_text(text)
    manifest = {"schema": "abacus.study29.phase5.presentation/v1", "rendered_at": datetime.now(timezone.utc).isoformat(), "renderer": pin(Path(__file__).resolve()), "inputs": [pin(path) for path in inputs], "before_current": before,
                "outputs": [pin(PHASE / name) for name in outputs], "method_or_selection_changed": False, "scope": "Saved comparison presentation/occurrence index; no selector or market computation."}
    (revision / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"revision": str(revision.relative_to(ROOT)), "occurrences": len(choice["occurrences"]), "outputs": list(outputs), "selection_recomputed": False}, indent=2))


if __name__ == "__main__":
    main()
