#!/usr/bin/env python3
"""Explicit retained-input Phase 4 reconstruction; no source discovery or reveal.

Only declared training-date CSVs are consumed, with immutable producer/input
pins verified before imports or calculation. Source comparisons use only the
already exposed October1/2/5 role ledger. Results are local specification-model
executions, never native Pine verification or an out-of-sample test.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import importlib.util
import json
from math import isfinite
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
EXPOSED = {"2026-10-01", "2026-10-02", "2026-10-05"}
BASELINE_FIELDS = ("previous_full_high", "previous_full_low", "current_week_vah", "current_week_poc", "current_week_val",
                   "previous_week_vah", "previous_week_poc", "previous_week_val", "completed_rth_vah", "completed_rth_poc",
                   "completed_rth_val", "overnight_vah", "overnight_poc", "overnight_val", "overnight_high", "overnight_low",
                   "completed_rth_high", "completed_rth_low", "rth_last_traded_close")


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def plain(value):
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def write_json(path, value):
    path.write_text(json.dumps(plain(value), indent=2, allow_nan=False) + "\n")


def check_pins(input_path, producer_path):
    source = json.loads(input_path.read_text())
    producer = json.loads(producer_path.read_text())
    parent_pin = producer["input_manifest"]
    if (ROOT / parent_pin["path"]).resolve() != input_path or digest(input_path) != parent_pin["sha256"]:
        raise ValueError("producer revision must pin the explicit input manifest")
    replacements = {pin["path"]: pin for pin in producer["files"]}
    for pin in source["files"]:
        actual = digest(ROOT / pin["path"])
        if actual != pin["sha256"] and (pin.get("session_date") or pin["path"] not in replacements):
            raise ValueError("changed input/producer without retained revision: " + pin["path"])
    for pin in producer["files"]:
        if digest(ROOT / pin["path"]) != pin["sha256"]:
            raise ValueError("changed producer/input: " + pin["path"])
        if digest(producer_path.parent / pin["snapshot_path"]) != pin["sha256"]:
            raise ValueError("retained producer/input bytes differ: " + pin["path"])
    required = {str((PHASE / "run_training.py").relative_to(ROOT)),
                "studies/29_verniman_level_reconstruction/src/phase4_model.py",
                "studies/29_verniman_level_reconstruction/src/phase3_model.py",
                "studies/29_verniman_level_reconstruction/src/reference_model.py",
                "studies/29_verniman_level_reconstruction/src/pivot_model.py",
                "studies/29_verniman_level_reconstruction/phase3/matching.py",
                str((PHASE / "source-role-ledger.json").relative_to(ROOT)),
                str((PHASE / "source_roles.py").relative_to(ROOT)),
                str((PHASE / "settings.json").relative_to(ROOT)),
                str((PHASE / "interpretation-record.md").relative_to(ROOT))}
    if not required <= replacements.keys():
        raise ValueError("producer revision missing required files: " + ",".join(sorted(required - replacements.keys())))
    return source, producer


def read_bars(path, day, model):
    cutoff = model.P3.BASE.local(date.fromisoformat(day), 9, 25)
    bars = []
    excluded = 0
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        columns = {key.lower(): key for key in reader.fieldnames or ()}
        if not {"time", "open", "high", "low", "close", "volume"} <= columns.keys():
            raise ValueError("native CSV requires time/open/high/low/close/Volume")
        for row in reader:
            stamp = row[columns["time"]]
            opened = datetime.fromtimestamp(int(stamp), timezone.utc) if stamp.lstrip("-").isdigit() else datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if opened.tzinfo is None:
                raise ValueError("timezone-aware bar time required")
            closed = opened + timedelta(minutes=5)
            if closed > cutoff:
                excluded += 1
                continue
            high, low, close = (float(row[columns[key]]) for key in ("high", "low", "close"))
            raw_volume = row[columns["volume"]]
            volume = float(raw_volume) if raw_volume.strip() else None
            if not all(isfinite(value) for value in (high, low, close)) or low > high:
                raise ValueError("invalid OHLC price row")
            if volume is not None and not isfinite(volume):
                raise ValueError("nonfinite volume row")
            bars.append(model.P3.BASE.Bar(opened.astimezone(model.P3.BASE.NY), closed.astimezone(model.P3.BASE.NY), high, low, close, volume, True))
    if any(b.opened >= a.opened for b, a in zip(bars, bars[1:])):
        raise ValueError("strictly increasing unique bar opens required")
    return bars, {"included_rows": len(bars), "excluded_after_cutoff_rows": excluded,
                  "ignored_columns": sorted(key for key in columns if key not in {"time", "open", "high", "low", "close", "volume"}),
                  "policy": "Only OHLCV and explicit timestamps are used; all native diagnostic series are ignored.",
                  "last_included_open": bars[-1].opened if bars else None,
                  "last_included_close": bars[-1].closed if bars else None}


def source_refs(rows, matching):
    return [matching.SourceReference(
        row["level_id"], row["session_date"], row["source_class"],
        row["provenance"].get("source_revision_id") or "retained_source_revision_unresolved",
        tuple(row["families"]), (row["price_low"], row["price_high"]),
        None, "ESZ2026" if row.get("actual_contract") == "ESZ26" else None,
        "individual_contract_unadjusted" if row.get("actual_contract") == "ESZ26" else None,
        row["source_timing_class"], row["available_at"])
        for row in rows]


def coordinate_diagnostic(rows, generated, matching, tolerance):
    """Family/window-unqualified geometry only; never construction coverage."""
    source_by_id = {row["level_id"]: row for row in rows}
    generated_by_id = {item["candidate_id"]: item for item in generated}
    if len(source_by_id) != len(rows) or len(generated_by_id) != len(generated):
        raise ValueError("coordinate diagnostics require unique source and selected candidate IDs")
    edges = {}
    for sid, source in source_by_id.items():
        for cid, candidate in generated_by_id.items():
            gap = matching.interval_gap((source["price_low"], source["price_high"]), candidate["interval"])
            if gap <= Decimal(str(tolerance)):
                edges[(sid, cid)] = gap
    chosen, error = matching._optimal_pairs(source_by_id, generated_by_id, edges)
    equal_optimal = []
    for pair, gap in sorted(edges.items()):
        reduced = {edge: cost for edge, cost in edges.items() if edge[0] != pair[0] and edge[1] != pair[1]}
        pairs, remainder = matching._optimal_pairs(set(source_by_id) - {pair[0]}, set(generated_by_id) - {pair[1]}, reduced)
        if len(pairs) + 1 == len(chosen) and remainder + gap == error:
            equal_optimal.append(pair)
    assignments = []
    for sid, cid in chosen:
        source, candidate = source_by_id[sid], generated_by_id[cid]
        exact = source["price_low"] == source["price_high"]
        assignments.append({"source_id": sid, "candidate_id": cid,
                            "source_order": source.get("source_target_order"),
                            "target_rank": candidate.get("rank"),
                            "source_interval": [source["price_low"], source["price_high"]],
                            "candidate_interval": candidate["interval"], "candidate_price": candidate["price"],
                            "interval_gap_points": str(edges[(sid, cid)]),
                            "signed_point_or_boundary_error": str(Decimal(str(candidate["price"])) - Decimal(source["price_low"])) if exact else None,
                            "family_or_window_identity_claimed": False})
    def observed_order(values):
        return bool(values) and all(type(v) is int and v > 0 for v in values) and len(set(values)) == len(values)
    source_order_known = observed_order([row.get("source_target_order") for row in rows])
    selected_order_known = observed_order([item.get("rank") for item in generated])
    order_known = source_order_known and selected_order_known
    ordered = sorted((item["source_order"], item["target_rank"]) for item in assignments) if order_known else []
    relative = all(ordered[i][1] < ordered[i + 1][1] for i in range(len(ordered) - 1)) if len(ordered) > 1 else None
    complete = (len(chosen) == len(rows) == len(generated) and (len(chosen) < 2 or relative)) if order_known else None
    return {"classification": "coordinate_only_descriptive_not_family_window_or_source_method_reproduction",
            "source_count": len(rows), "selected_count": len(generated),
            "matched_count": len(chosen), "total_interval_gap": str(error),
            "assignments": assignments,
            "feasible_alternatives": [{"source_id": sid, "candidate_id": cid, "interval_gap_points": str(cost)} for (sid, cid), cost in sorted(edges.items())],
            "equal_optimal_pairs": [list(pair) for pair in equal_optimal],
            "unmatched_source_ids": sorted(set(source_by_id) - {sid for sid, _ in chosen}),
            "unmatched_selected_candidate_ids": sorted(set(generated_by_id) - {cid for _, cid in chosen}),
            "relative_order_on_matched_subset": relative,
            "ordering_status": "observed_positive_unique_orders" if order_known else "unresolved_missing_empty_or_nonunique_orders",
            "complete_coordinate_ladder": complete,
            "strict_family_window_coverage": None,
            "limits": "Nearby prices may have unsupported families or unknown source windows. This is not end-to-end reproduction."}


def target_coordinate_diagnostic(rows, generated, matching, tolerance):
    """Independent source revisions/classes cannot share a pooled assignment."""
    role_units = load_module("study29_phase4_source_role_interpretation", PHASE / "source_roles.py")
    grouped = {}
    for row in rows:
        grouped.setdefault(role_units.source_stratum(row), []).append(row)
    strata = [{"source_stratum": {"session_date": key[0], "source_class": key[1], "source_revision_id": key[2]},
               "diagnostic": coordinate_diagnostic(values, generated, matching, tolerance)}
              for key, values in sorted(grouped.items())]
    if len(strata) == 1:
        return {**strata[0]["diagnostic"], "source_stratum": strata[0]["source_stratum"], "source_strata_count": 1}
    return {"classification": "coordinate_only_descriptive_not_family_window_or_source_method_reproduction",
            "status": "source_stratified_no_pooled_score", "source_strata_count": len(strata),
            "source_count": len(rows), "selected_count": len(generated), "matched_count": None,
            "total_interval_gap": None, "assignments": [], "feasible_alternatives": [],
            "equal_optimal_pairs": [], "relative_order_on_matched_subset": None,
            "complete_coordinate_ladder": None, "strict_family_window_coverage": None,
            "per_source_stratum": strata,
            "limits": "Each source class/revision is assigned independently against the saved branch; no pooled cross-revision score or nearest-revision choice."}


def analyze_sources(day, rows, inputs, selection, model):
    matching = model._matching_module()
    roles = {}
    for role in ("pivot", "bullish", "bearish"):
        wanted = "conditional_scenario_divider" if role == "pivot" else "ordered_" + role + "_destination"
        selected_rows = [row for row in rows if row["phase4_role"] == wanted]
        if not selected_rows:
            roles[role] = {"status": "not_executed_no_source_role_labels", "strict_family_window_coverage": None}
            continue
        refs = source_refs(selected_rows, matching)
        order = {row["level_id"]: row["source_target_order"] for row in selected_rows if row["source_target_order"] is not None}
        raw_occurrence_decomposition = model.evaluate_role(inputs, selection, refs, role=role, source_order=order)
        strict = raw_occurrence_decomposition
        primary_interpretation = None
        if role == "pivot":
            role_units = load_module("study29_phase4_source_role_interpretation", PHASE / "source_roles.py")
            units = role_units.interpret_divider_strata(selected_rows)
            candidate = selection.pivot.candidate
            generated = [{"candidate_id": candidate.candidate_id, "interval": candidate.interval, "price": candidate.price}] if candidate else []
            branch_errors = []
            for row in selected_rows:
                bounds = role_units.interval(row)
                exact = bounds is not None and bounds[0] == bounds[1]
                branch_errors.append({"source_occurrence_id": row["level_id"], "scenario_side": row.get("scenario_side"),
                    "original_label": row.get("original_label"), "directional_conditions": row.get("directional_conditions"),
                    "source_interval": [row.get("price_low"), row.get("price_high")],
                    "signed_point_or_boundary_error": str(Decimal(str(candidate.price)) - bounds[0]) if candidate and exact else None,
                    "interval_gap_points": str(matching.interval_gap(bounds, candidate.interval)) if candidate and bounds is not None else None,
                    "classification": "branch_specific_descriptive_error_not_single_pivot_ground_truth"})
            unique_common = len(units) == 1 and units[0]["status"] == "unique_common_functional_divider"
            primary_interpretation = {"policy": role_units.POLICY, "source_strata": units,
                "status": "unique_common_functional_divider" if unique_common else "unresolved_single_pivot_ground_truth",
                "primary_source_unit_count": 1 if unique_common else None,
                "branch_specific_descriptive_errors": branch_errors,
                "raw_trigger_occurrences_are_not_independent_pivot_observations": True}
            if unique_common:
                unit = units[0]
                row = dict(selected_rows[0])
                row.update(level_id=unit["unit_id"], price_low=unit["primary_price_interval"][0],
                           price_high=unit["primary_price_interval"][1], source_target_order=None)
                diagnostic = coordinate_diagnostic([row], generated, matching, 1)
                diagnostic["source_occurrence_groups"] = [{"interval": unit["primary_price_interval"],
                    "original_occurrence_ids": [item["source_occurrence_id"] for item in unit["source_occurrences"]]}]
                if candidate:
                    exact = row["price_low"] == row["price_high"]
                    signed = Decimal(str(candidate.price)) - Decimal(row["price_low"]) if exact else None
                    diagnostic["pivot_signed_point_or_boundary_error"] = str(signed) if signed is not None else None
                    diagnostic["pivot_absolute_point_or_boundary_error"] = str(abs(signed)) if signed is not None else None
                    diagnostic["pivot_interval_gap_points"] = str(matching.interval_gap((row["price_low"], row["price_high"]), candidate.interval))
                if unit["primary_family_identity_consistent"]:
                    row["families"] = unit["common_families"]
                    strict = model.evaluate_role(inputs, selection, source_refs([row], matching), role="pivot")
                    strict["source_evaluation_unit"] = "one_interpreted_common_divider"
                else:
                    strict = {"role": "pivot", "status": "not_estimable", "primary_source_unit_count": 1,
                        "reason": "BRANCH_LABEL_FAMILY_CONFLICT_RETAINED_NOT_COMPOUND_CONFLUENCE",
                        "strict_family_window_coverage": None}
            else:
                diagnostic = {"classification": "primary_single_pivot_diagnostic_unavailable",
                    "status": "unresolved_single_pivot_ground_truth", "source_count": None,
                    "selected_count": len(generated), "matched_count": None, "total_interval_gap": None,
                    "assignments": [], "feasible_alternatives": [], "equal_optimal_pairs": [],
                    "pivot_signed_point_or_boundary_error": None, "pivot_absolute_point_or_boundary_error": None,
                    "pivot_interval_gap_points": None, "strict_family_window_coverage": None,
                    "branch_specific_descriptive_errors": branch_errors,
                    "limits": "Different/multiple branch trigger intervals or source strata cannot be reduced to the nearest trigger or an averaged single pivot."}
                strict = {"role": "pivot", "status": "not_estimable", "primary_source_unit_count": None,
                          "reason": "SINGLE_PIVOT_GROUND_TRUTH_UNRESOLVED", "strict_family_window_coverage": None}
        else:
            branch = selection.bullish if role == "bullish" else selection.bearish
            generated = [{"candidate_id": target.candidate.candidate_id, "interval": target.candidate.interval,
                          "price": target.candidate.price, "rank": target.rank,
                          "group_ids": [c.candidate_id for c in target.group]} for target in branch.targets]
            diagnostic = target_coordinate_diagnostic(selected_rows, generated, matching, 1)
        roles[role] = {"strict_decomposition": strict, "coordinate_only_diagnostic": diagnostic,
                       "primary_pivot_interpretation": primary_interpretation,
                       "raw_source_occurrence_decomposition": raw_occurrence_decomposition if role == "pivot" else None,
                       "raw_occurrence_result_is_not_primary_pivot_accuracy": role == "pivot",
                       "source_family_support": [{"source_id": row["level_id"], "families": row["families"],
                          "unsupported_or_unresolved_roles": row["comparison"]["unsupported_or_unresolved_roles"],
                          "exact_source_window": None, "historical_available_at": row["available_at"]} for row in selected_rows]}
    return roles


def compact_selection(selection):
    return {"pivot": {"price": selection.pivot.price,
                       "candidate_id": selection.pivot.candidate.candidate_id if selection.pivot.candidate else None,
                       "reason_code": selection.pivot.reason_code,
                       "fallback": selection.pivot.fallback, "status": selection.pivot.status},
            "bullish": {"prices": [t.candidate.price for t in selection.bullish.targets],
                        "candidate_ids": [t.candidate.candidate_id for t in selection.bullish.targets],
                        "reason_codes": [t.reason_code for t in selection.bullish.targets], "status": selection.bullish.status},
            "bearish": {"prices": [t.candidate.price for t in selection.bearish.targets],
                        "candidate_ids": [t.candidate.candidate_id for t in selection.bearish.targets],
                        "reason_codes": [t.reason_code for t in selection.bearish.targets], "status": selection.bearish.status}}


def reconstruct(pin, model, pivot_model, baseline_rows, native_rows, role_rows, producer):
    day = pin["session_date"]
    bars, bar_audit = read_bars(ROOT / pin["path"], day, model)
    engine = model.Phase4Engine(contract="ESZ2026", feed="CME GLOBEX",
                adjustment="individual_contract_unadjusted", tick_size=.25, row_size=4, va_pct=70,
                input_identity=pin["sha256"], code_identity=producer["phase3_model_sha256"],
                settings_identity=producer["phase3_settings_sha256"], minutes=5)
    engine.feed(bars)
    expanded = engine.expanded_snapshot
    if expanded is None or expanded.baseline.trading_date.isoformat() != day:
        raise ValueError("No exact target-date expanded snapshot: " + engine.snapshot_status)
    last_bar = next((bar for bar in reversed(bars) if bar.closed == expanded.baseline.cutoff), None)
    inputs = model.inputs_from_phase3(expanded, last_bar.close if last_bar else None)
    selections = {p + "-" + t: model.select_map(inputs, pivot_policy=p, target_policy=t)
                  for p in ("P0", "B0", "B1") for t in ("D0", "D1")}
    profile_readiness = [{"window": d.window, "profile_id": d.profile_id,
                          "status": ledger["status"], "reasons": ledger["distribution"]["reasons"],
                          "included_sessions": d.included_sessions, "expected_sessions": d.expected_sessions,
                          "row_count": len(d.masses), "last_included_open": d.last_bar_open,
                          "last_included_close": d.last_bar_close,
                          "counts": ledger["counts"] if ledger["status"] == "ready" else None,
                          "presentation": ledger["presentation"] if ledger["status"] == "ready" else None}
                         for d, ledger in zip(expanded.distributions, expanded.candidate_ledgers)]
    expected = baseline_rows.get(day)
    comparisons = []
    for name, value in zip(BASELINE_FIELDS, expanded.baseline.values):
        recorded = expected.get(name) if expected else None
        comparisons.append({"field": name, "local": value, "retained_Phase1": recorded,
                            "status": "unavailable_local_history" if value is None else "no_retained_reference" if recorded is None else
                                      "equal" if Decimal(str(value)) == Decimal(recorded) else "different"})
    comparator = pivot_model.PivotEngine()
    comparator.feed(bars)
    native = native_rows.get(day)
    frozen = comparator.frozen
    selected = frozen.selection if frozen else None
    alternate = pivot_model.alternate_reference(selected.price, selected.reason, *selected.inputs[:3], selected.inputs[4]) if selected else (None, "na")
    comparator_receipt = {"execution": "current_translated_comparator_on_retained_native_export_not_fresh_Pine",
        "frozen": plain(frozen) if frozen else None,
        "current_alternate_model_only": {"price": alternate[0], "origin": alternate[1], "is_target": False},
        "retained_native_v1_price": native["pivot"] if native else None,
        "local_comparator_equals_retained_native_v1": (selected is not None and selected.price is not None and Decimal(str(selected.price)) == Decimal(native["pivot"])) if native else None,
        "P0_equals_retained_native_v1": (selections["P0-D1"].pivot.price is not None and Decimal(str(selections["P0-D1"].pivot.price)) == Decimal(native["pivot"])) if native else None,
        "input_eligibility_difference": "P0 requires expected priorweekday; savedAutopivot uses latestobservedRTH. Input eligibility must be assessed separately for each declared export; parity is reported only when a retained native reference exists."}
    sources = [row for row in role_rows if row["session_date"] == day]
    evaluations = {key: analyze_sources(day, sources, inputs, selection, model) for key, selection in selections.items()}
    result = {"schema": "abacus.study29.phase4.local-training-map/v1", "session_date": day,
              "execution": "independent_local_specification_model_not_Pine",
              "candidate_control": "phase3-3.0.0; mathematical N1/E1/P1/P2 control unchanged",
              "selector_policy": "phase4-4.0.0", "input": pin, "producer_revision": producer["id"],
              "bar_audit": bar_audit, "cutoff_close": inputs.cutoff_close,
              "expanded_snapshot": plain(expanded), "selector_inputs": plain(inputs),
              "profile_readiness": profile_readiness,
              "baseline_comparison": comparisons,
              "autopivot_comparator": comparator_receipt,
              "selections": {key: plain(value) for key, value in selections.items()},
              "evaluation": evaluations,
              "source_access": "retained_already_exposed_Phase2_only" if sources else "closed_no_answer_sources_read",
              "new_answers_opened": False, "out_of_sample": False,
              "limits": "Partial history withholds missing families. Same-feed reconstruction is not native full-generator verification or independent provider validation."}
    summary = {"session_date": day, "status": "local_partial_expanded_map",
               "execution": result["execution"], "cutoff": expanded.baseline.cutoff,
               "last_included_bar": [expanded.baseline.last_open, expanded.baseline.last_close],
               "cutoff_close": inputs.cutoff_close, "profile_readiness": profile_readiness,
               "baseline_reference_available": expected is not None,
               "baseline_available": sum(x["local"] is not None for x in comparisons),
               "baseline_compared_equal": sum(x["status"] == "equal" for x in comparisons),
               "baseline_differences": [x for x in comparisons if x["status"] == "different"],
               "comparator": comparator_receipt,
               "candidate_counts": {"records": len(inputs.candidates),
                    "ready": sum(not c.reasons(inputs.cutoff) for c in inputs.candidates),
                    "eligible_destinations": sum(not model._destination_reasons(c, inputs) for c in inputs.candidates)},
               "selection_summaries": {key: compact_selection(value) for key, value in selections.items()},
               "pivot_price_diagnostics": {key: value["pivot"].get("coordinate_only_diagnostic") for key, value in evaluations.items()},
               "target_coordinate_diagnostics": {key: {side: value[side].get("coordinate_only_diagnostic") for side in ("bullish", "bearish")} for key, value in evaluations.items()},
               "strict_family_window_coverage": None,
               "end_to_end_source_reproduction": None,
               "new_answer_sources_opened": False,
               "source_suitability": "unresolved_exact_windows_and_historical_availability" if sources else "answers_closed",
               "all_five_profiles_ready": all(x["status"] == "ready" for x in profile_readiness)}
    if summary["all_five_profiles_ready"]:
        summary["status"] = "local_expanded_map"
    return result, summary


def render_summary(result):
    lines = ["# Phase 4 training results", "", "These are local reconstructions of declared retained native OHLCV exports, not native Pine executions. Full missing profiles remain unavailable. The seven new answer sources remain closed; no source price enters the candidate pool.", "", "| Training date | Available/equal baseline fields | Ready profile families | P0 pivot | Native v1 comparator parity |", "|---|---|---|---|---|"]
    for row in result["records"]:
        if row["status"] == "unavailable":
            lines.append(f"| {row['session_date']} | Unavailable | Unavailable | Unavailable | Not assessed |")
        else:
            ready = ", ".join(x["window"] for x in row["profile_readiness"] if x["status"] == "ready")
            pivot = row["selection_summaries"]["P0-D1"]["pivot"]["price"]
            baseline_text = (f"{row['baseline_compared_equal']}/{row['baseline_available']} available; original19 retained separately"
                             if row.get("baseline_reference_available", row["session_date"] in EXPOSED) else
                             f"{row['baseline_available']} available; no retained Phase1 reference")
            parity = row["comparator"]["P0_equals_retained_native_v1"]
            lines.append(f"| {row['session_date']} | {baseline_text} | {ready} | {pivot} | {parity if parity is not None else 'Not assessed'} |")
    lines += ["", "The [JSON summary](training-results.json) links exact staged map hashes, six P0/B0/B1 × D0/D1 choices, retained comparator attribution and coordinate-only target assignments. Each full staged map includes all five distributions, original19 fields, cutoff close, uncapped N1/E1 ledgers/rejections/caps, composite lineage/missing members, and unavailable PBT anchors.", "", "| Date / pivot policy | Pivot | Signed error to source conditional divider | Interval gap |", "|---|---|---|---|"]
    for row in result["records"]:
        if row["status"] == "unavailable":
            continue
        for policy in ("P0", "B0", "B1"):
            selection = row["selection_summaries"][policy + "-D1"]
            diagnostic = row["pivot_price_diagnostics"][policy + "-D1"] or {}
            lines.append(f"| {row['session_date']} / {policy} | {selection['pivot']['price']} | {diagnostic.get('pivot_signed_point_or_boundary_error', 'Not assessed')} | {diagnostic.get('pivot_interval_gap_points', 'Not assessed')} |")
    lines += ["", "Divider comparisons above are descriptive geometry. Source construction/windows and historical availability remain unresolved; exact family/window coverage, role agreement and end-to-end reproduction are not estimable. Opposite conditional source triggers are preserved as separate occurrences but grouped as one functional divider for price diagnostics. No literal LIS label is invented.", "", "D0 is a distance-only baseline. D1 is an unfitted auction-exit/range/external-boundary itinerary; neither is learned source order. All source destinations are retained, including the four October1 bullish marks despite the executable cap of three. Coordinate-only one-to-one matches do not establish source-family equivalence: GAP is unsupported, PBT anchors are missing, and compound labels remain unresolved. Strict candidate-availability/identity/selection/order decomposition is saved in each full map; unknown identity is not a measured generation or selector failure.", "", "Additional-date status is explicit in the table: unavailable records are not candidate maps or pre-reveal predictions. A retained local map is a model reconstruction, with each missing family disclosed. All-seven expanded-map and current-Autopivot capture remains required before any new target reveal; this runner never opens new answers or automatically passes that gate. Training remains training. Development October15–20 and hidden October21–27 sources/Replay dates stay protected.", "", "See the [rulebook](rulebook.md), [readiness reconciliation](readiness-reconciliation.md), [verification](verification.md) and [Phase5 handoff](phase5-handoff.md) for the remaining acceptance gates.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--producer-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="fresh attempt directory under the explicit Phase4 stage")
    parser.add_argument("--prior-summary", type=Path, help="optional exact pinned earlier summary to carry forward")
    parser.add_argument("--write-current-summary", action="store_true")
    args = parser.parse_args()
    input_path, producer_path, output = ((ROOT / value).resolve() if not value.is_absolute() else value.resolve() for value in (args.input_manifest, args.producer_manifest, args.output))
    settings = json.loads((PHASE / "settings.json").read_text())
    allowed = set(settings["training_dates"])
    source, producer = check_pins(input_path, producer_path)
    if output.exists():
        raise SystemExit("Refusing to overwrite retained attempt directory")
    stage = producer_path.parent
    if stage.name != "phase4_20261031T010249Z" or output.parent != stage:
        raise ValueError("output must be one fresh directory within the explicit Phase4 stage")
    pins = [pin for pin in source["files"] if pin.get("session_date") and str(pin["path"]).endswith(".csv")]
    if not pins or len({pin["session_date"] for pin in pins}) != len(pins) or any(pin["session_date"] not in allowed for pin in pins):
        raise ValueError("explicit unique authorized training-date CSV pins required")
    ledger = json.loads((PHASE / "source-role-ledger.json").read_text())
    if any(row["session_date"] not in EXPOSED for row in ledger["occurrences"]):
        raise ValueError("runner does not open new training answer labels; use already exposed three-date ledger only")
    baseline_path = next(ROOT / p["path"] for p in ledger["source_pins"] if p["path"].endswith("frozen-candidates.csv"))
    native_path = next(ROOT / p["path"] for p in ledger["source_pins"] if p["path"].endswith("frozen-selections.csv"))
    with baseline_path.open(newline="") as handle:
        baseline_rows = {row["date"]: row for row in csv.DictReader(handle)}
    with native_path.open(newline="") as handle:
        native_rows = {row["date"]: row for row in csv.DictReader(handle)}
    model = load_module("study29_phase4_declared_training_model", ROOT / "studies/29_verniman_level_reconstruction/src/phase4_model.py")
    load_module("reference_model", ROOT / "studies/29_verniman_level_reconstruction/src/reference_model.py")
    pivot_model = load_module("study29_phase4_declared_comparator_model", ROOT / "studies/29_verniman_level_reconstruction/src/pivot_model.py")
    records = {}
    if args.prior_summary:
        prior_path = (ROOT / args.prior_summary).resolve()
        prior = json.loads(prior_path.read_text())
        required_pin = next((p for p in producer["files"] if (ROOT / p["path"]).resolve() == prior_path), None)
        if required_pin is None:
            raise ValueError("prior summary must have an explicit producer/input hash pin")
        records = {row["session_date"]: row for row in prior["records"]}
        if not set(records) <= allowed:
            raise ValueError("prior summary includes unauthorized dates")
    payloads = []
    for pin in pins:
        try:
            full, compact = reconstruct(pin, model, pivot_model, baseline_rows, native_rows, ledger["occurrences"], producer)
            payloads.append((pin["session_date"] + ".json", full, compact))
        except (ValueError, ArithmeticError) as exc:
            records[pin["session_date"]] = {"session_date": pin["session_date"], "status": "unavailable", "failure_reasons": [str(exc)], "candidate_counts": None, "new_answer_sources_opened": False, "strict_family_window_coverage": None}
    # Calculation succeeds before the fresh output directory is created.
    output.mkdir()
    for name, full, compact in payloads:
        path = output / name
        write_json(path, full)
        compact["map_artifact"] = {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}
        records[compact["session_date"]] = compact
    for day in settings["training_dates"]:
        records.setdefault(day, {"session_date": day, "status": "unavailable",
            "failure_reasons": ["No newly declared compatible training export/capture; additional answer sources remain closed."],
            "candidate_counts": None, "phase3_candidate_map": None, "current_Autopivot_prediction": None,
            "new_answer_sources_opened": False, "strict_family_window_coverage": None})
    summary = {"schema": "abacus.study29.phase4.training-results/v1", "protocol_version": "4.0.0",
               "recorded_at": datetime.now(timezone.utc), "attempt": str(output.relative_to(ROOT)),
               "input_manifest": {"path": str(input_path.relative_to(ROOT)), "sha256": digest(input_path)},
               "producer_manifest": {"path": str(producer_path.relative_to(ROOT)), "sha256": digest(producer_path)},
               "selection_learning": "not_fitted; frozen engineering controls on already exposed training data",
               "new_answer_sources_opened": False, "seven_date_reveal_gate_passed": False,
               "native_verification": "separate_required; these records are local model execution only",
               "records": [records[day] for day in settings["training_dates"]]}
    write_json(output / "training-results.json", summary)
    (output / "training-results.md").write_text(render_summary(plain(summary)))
    write_json(output / "artifact-hashes.json", {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()})
    if args.write_current_summary:
        write_json(PHASE / "training-results.json", summary)
        (PHASE / "training-results.md").write_text(render_summary(plain(summary)))
    print(json.dumps({"attempt": str(output.relative_to(ROOT)), "local_maps": len(payloads),
                      "unavailable_records": sum(row["status"] == "unavailable" for row in records.values()),
                      "new_answer_sources_opened": False}, indent=2))


if __name__ == "__main__":
    main()
