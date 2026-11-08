#!/usr/bin/env python3
"""Project only byte-pinned, gate-approved four-date Phase 5 source evidence.

This program has no source discovery, market reader or selector. It preserves
every canonical revision, recollection and closing/execution class separately.
The legacy field name phase4_role is retained solely for the frozen scorer API.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
DATES = ("2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20")
FAMILIES = {"YVAH", "YPOC", "YVAL", "YVALH", "YHOD", "YLOD", "ONH", "ONL", "HVE", "HVN", "LVN", "PBT", "GAP", "VPOC", "ATH", "RTH", "ON", "IVL", "VAR", "CPI", "SOC"}
SUPPORTED = {"YVAH", "YPOC", "YVAL", "ONVAH", "ONPOC", "ONVAL", "ONH", "ONL", "YHOD", "YLOD", "PRIOR_CLOSE", "CWVAH", "CWPOC", "CWVAL", "PWVAH", "PWPOC", "PWVAL", "HVN", "LVN", "HVE", "PBT"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def families(label):
    tokens = re.findall(r"[A-Z]+", (label or "").upper().replace("PBTS", "PBT").replace("GAPS", "GAP"))
    return list(dict.fromkeys(token for token in tokens if token in FAMILIES)) or ["UNRESOLVED_LABEL"]


def occurrence(day, source_id, identifier, label, low, high, source_class, raw, parent, *, role="structural_reference_without_selected_scenario_role", side=None, order=None):
    return {"level_id": identifier, "session_date": day, "source_id": source_id,
            "original_label": label, "exact_readable_source_text": label, "price_low": low, "price_high": high,
            "price_basis": "printed_or_reported_original" if low is not None else "unpriced_label",
            "reading_uncertainty": "Original recorded reading retained; rounding and exact source calculation remain unresolved." if low is not None else "No exact printed numeric coordinate; chart-axis values are not substituted.",
            "families": families(label), "reference_period": "unresolved_exact_source_window", "developing_or_completed": "unresolved",
            "instrument": parent.get("product") or parent.get("instrument_raw"), "actual_contract": parent.get("contract"),
            "contract_identity_basis": "Printed canonical plan contract." if source_class == "named_daily_plan" else "Original metadata only; missing identity remains null.",
            "source_timing_class": "unresolved", "available_at": raw.get("available_at"),
            "preopen_status": "historical_availability_unverified; capture, claimed update and recollection do not certify historical availability",
            "provenance": {"source_revision_id": parent.get("source_revision_id") or parent.get("observation_id"),
                           "source_posted_at": parent.get("posted_at") or parent.get("source_claimed_published_at"),
                           "source_claimed_updated_at": parent.get("source_claimed_updated_at"),
                           "capture_timestamp": parent.get("captured_at") or parent.get("reviewed_at"), "source_url": parent.get("source_url") or parent.get("post_url")},
            "source_class": source_class, "source_kind": source_class, "apparent_role": raw.get("role") or "structural reference",
            "scenario_side": side, "source_target_order": order, "phase4_role": role,
            "role_basis": "Original canonical branch role/ordinal." if source_class == "named_daily_plan" else "Reported/structural role remains a separate evidence class, never canonical truth.",
            "literal_source_LIS_label": bool(re.search(r"\bLIS\b", label or "", re.I)),
            "directional_conditions": parent.get((side or "") + "_conditions"), "vix_cvd_input_status": "unmeasured_not_substituted",
            "origin": {"kind": source_class, "original_role": raw.get("role"), "source_record": raw},
            "source_identity": {key: value for key, value in parent.items() if key not in {"body_text", "plan_text", "bullish_scenario_text", "bearish_scenario_text", "source_text"}},
            "source_window_identity_supplied": raw.get("source_window_identity") or parent.get("source_window_identity"),
            "candidate_explanations": ["Literal family may suggest a boundary/extreme/projection, but exact construction/window identity remains unverified."],
            "competing_explanations": ["Different construction/feed/window/grid, source rounding, revision conflict or unsupported family."],
            "comparison": {"status": "comparison_retained_separately_from_source_input", "strict_candidate_availability": None, "construction_window_identity_supported": None, "selector_chose_source_reference": None, "scenario_role_and_order_agreement": None, "strict_family_window_coverage": None, "unsupported_or_unresolved_roles": [family for family in families(label) if family not in SUPPORTED], "post_cutoff_reaction_used": False}}


def project_day(day, canonical, levels, recalled_outlooks, recalled_levels, intakes, issues, coverage, role_units):
    if day not in DATES or any(str(row.get("session_date")) != day for rows in (canonical, levels, recalled_outlooks, recalled_levels, issues, coverage) for row in rows):
        raise ValueError("source row outside exact development session")
    by_id = {row["outlook_id"]: row for row in canonical}
    if len(by_id) != len(canonical):
        raise ValueError("distinct canonical revision IDs required")
    rows = []
    for raw in levels:
        parent = by_id[raw["outlook_id"]]
        sid = "B-" + day.replace("-", "") + "-" + raw["outlook_id"][:12]
        identifier = sid + "-PLAN-" + raw["side"] + "-" + raw["role"] + "-" + str(raw["ordinal"])
        role = "conditional_scenario_divider" if raw["role"] == "trigger" else "ordered_" + raw["side"] + "_destination" if raw["role"] == "target" else "explicit_invalidation_reference" if raw["role"] == "invalidation" else "structural_reference_without_selected_scenario_role"
        rows.append(occurrence(day, sid, identifier, raw["source_text"], raw["price_low"], raw["price_high"], "named_daily_plan", raw, parent, role=role, side=raw["side"], order=raw["ordinal"] if raw["role"] == "target" else None))
    for parent in canonical:
        header = re.search(r"ESZ26[^\n]*", parent.get("body_text") or "")
        for label, price in re.findall(r"\b(YVAH|YPOC|YVAL|GAP)\s+([0-9]+(?:\.[0-9]+)?)", header.group() if header else ""):
            sid = "B-" + day.replace("-", "") + "-" + parent["outlook_id"][:12]
            rows.append(occurrence(day, sid, sid + "-HEADER-" + label, label + " " + price, price, price, "named_daily_plan", {"role": "header_reference", "source_label": label}, parent))
    recalled_by_id = {row["observation_id"]: row for row in recalled_outlooks}
    for raw in recalled_levels:
        parent = recalled_by_id[raw["observation_id"]]
        sid = "RECOLLECTION-" + parent["observation_id"][:12]
        role = "reported_divider_recollection" if raw["role"] == "trigger" else "recalled_ordered_" + raw["side"] + "_destination" if raw["role"] == "target" else "structural_reference_without_selected_scenario_role"
        identifier = sid + "-" + raw["side"] + "-" + raw["role"] + "-" + str(raw["ordinal"])
        rows.append(occurrence(day, sid, identifier, raw["source_text"], raw["price_low"], raw["price_high"], "user_supplied_recollection", raw, parent, role=role, side=raw["side"], order=raw["ordinal"] if raw["role"] == "target" else None))
    annotations, executions, intake_issues = [], [], []
    for observation in intakes:
        if observation.get("session_date") != day:
            raise ValueError("intake outside exact authorized development date")
        source_by_id = {row["source_id"]: row for row in observation.get("sources", [])}
        for raw in observation.get("closing_notes", []):
            if raw.get("source_id") not in source_by_id:
                annotations.append({"observation_id": observation["observation_id"], **raw,
                                    "source_linkage_status": "unresolved_no_retained_same_date_source_identity",
                                    "selected_scenario_truth": False})
                continue
            parent = {**source_by_id[raw["source_id"]], "observation_id": observation["observation_id"], "source_revision_id": observation["observation_id"]}
            if raw.get("category") == "reference_level":
                sid = "X-" + raw["source_id"]
                identifier = sid + "-" + observation["observation_id"] + "-" + raw["note_id"]
                rows.append(occurrence(day, sid, identifier, raw["label_raw"], raw.get("numeric_value"), raw.get("numeric_value"), "closing_chart_reference", raw, parent))
            else:
                annotations.append({"observation_id": observation["observation_id"], **raw})
        executions.extend({"observation_id": observation["observation_id"], **raw} for raw in observation.get("markers", []))
        intake_issues.extend(observation.get("issues", []))
    selected = [row for row in rows if row["source_class"] == "named_daily_plan" and row["phase4_role"] in {"conditional_scenario_divider", "ordered_bullish_destination", "ordered_bearish_destination"}]
    invalidation = [row["level_id"] for row in rows if row["phase4_role"] == "explicit_invalidation_reference"]
    status = "reviewed" if selected else "source_suitability_failure"
    session = {"session_date": day, "source_review_status": status,
               "failure_reasons": [] if selected else ["NO_DATED_CANONICAL_SCENARIO_PLAN_IN_RETAINED_RELEASE13; closing labels/executions do not supply missing preopen roles."],
               "source_occurrence_ids": [row["level_id"] for row in rows], "source_role_counts": dict(Counter(row["phase4_role"] for row in rows)), "selected_source_refs": [row["level_id"] for row in selected],
               "canonical_source_revision_ids": list(by_id), "functional_divider_interpretations": role_units.interpret_divider_strata(selected),
               "explicit_invalidation_references": {"status": "explicit_canonical_role" if invalidation else "not_identified_as_separate_canonical_role", "occurrence_ids": invalidation},
               "execution_annotations": {"status": "retained_separately_never_pivot_target_truth", "records": executions}, "other_source_annotations": annotations, "source_issues": issues, "intake_issues": intake_issues, "coverage_records": coverage,
               "source_sequence_qualification": "Every independent source revision/class and every ordinal remains; executable cap never truncates observed targets.",
               "available_at": None, "source_historical_availability": "unresolved", "exact_window_coverage": None, "selector_evaluation_status": "separate_saved_prediction_comparison", "out_of_sample_hidden_test": False}
    return rows, session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--capture-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    stage, gate_path, output = ((ROOT / value).resolve() for value in (args.stage, args.capture_gate, args.output))
    gate = module("study29_phase5_role_gate", PHASE / "select_sources.py")
    receipt = gate.validate_gate(ROOT, stage, gate_path)
    selection_path = stage / "source-selection-manifest-release13.json"
    selection = json.loads(selection_path.read_text())
    if selection.get("authorized_dates") != list(DATES) or selection.get("gate", {}).get("gate") != receipt["gate"] or selection.get("dataset", {}).get("sha256") != gate.MANIFEST_SHA256:
        raise ValueError("exact gate-approved source selection required")
    if set(selection.get("tables", {})) != set(gate.TABLES):
        raise ValueError("all bounded source table inventories required")
    if datetime.fromisoformat(selection["selection_started_at"]) < datetime.fromisoformat(receipt["recorded_at"]):
        raise ValueError("source selection predates the prediction reveal gate")
    used = []
    def read_selected(relative, expected):
        path = (stage / relative).resolve()
        if not path.is_relative_to(stage) or digest(path) != expected:
            raise ValueError("selected source bytes differ")
        used.append({"path": str(path.relative_to(ROOT)), "sha256": expected})
        return json.loads(path.read_text())
    # Check every selected artifact before the first target-bearing JSON read.
    for table, dates in selection["tables"].items():
        if table not in gate.TABLES or set(dates) != set(DATES):
            raise ValueError("unbounded selected table/date inventory")
        for row in dates.values():
            path = (stage / row["path"]).resolve()
            if not path.is_relative_to(stage) or digest(path) != row["sha256"]:
                raise ValueError("selected source table integrity differs")
    for row in selection["intake"]:
        if row["session_date"] not in DATES:
            raise ValueError("intake metadata outside allowlist")
        if row.get("selected_path"):
            path = (stage / row["selected_path"]).resolve()
            if not path.is_relative_to(stage) or digest(path) != row["selected_sha256"]:
                raise ValueError("selected intake integrity differs")
    role_units = module("study29_phase5_frozen_role_units", ROOT / "studies/29_verniman_level_reconstruction/phase4/source_roles.py")
    rows, sessions = [], []
    for day in DATES:
        def table(name):
            row = selection["tables"][name][day]
            return read_selected(row["path"], row["sha256"])
        intakes = [read_selected(row["selected_path"], row["selected_sha256"]) for row in selection["intake"] if row["session_date"] == day and row.get("selected_path")]
        current, session = project_day(day, table("outlooks"), table("levels"), table("observations"), table("observation_levels"), intakes, table("issues"), table("coverage"), role_units)
        rows.extend(current); sessions.append(session)
    if len({row["level_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate source occurrence identity")
    if output.exists() or not (output.is_relative_to(PHASE) or output.is_relative_to(stage)):
        raise ValueError("use a new Phase 5 source-ledger path; never overwrite earlier evidence")
    result = {"schema": "abacus.study29.phase5.source-role-ledger/v1", "recorded_at": datetime.now(timezone.utc).isoformat(), "study_id": 29, "scope": "Four scheduled development sessions; canonical revisions, recollections, structural and execution evidence remain separate.", "source_occurrence_count": len(rows), "session_records": sessions, "occurrences": rows,
              "role_interface": "phase4_role field preserves the fixed Phase4 scorer API; no prior ledger is edited.", "source_selection": {"path": str(selection_path.relative_to(ROOT)), "sha256": digest(selection_path)}, "reveal_gate": receipt["gate"], "projection_code": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest(Path(__file__))}, "source_pins": used,
              "source_window_policy": "Unknown exact windows remain outside the primary denominator; availability nulls stay null.", "selection_recomputed": False, "candidate_inputs_modified": False,
              "exposure_qualification": "Development access is gate-approved; the original hidden period has recorded earlier exposure and is not pristine. This projection reads no hidden/replacement sources."}
    with output.open("x") as handle:
        json.dump(result, handle, indent=2); handle.write("\n")
    print(json.dumps({"ledger": str(output.relative_to(ROOT)), "sha256": digest(output), "occurrences": len(rows), "session_status": {row["session_date"]: row["source_review_status"] for row in sessions}}, indent=2))


if __name__ == "__main__":
    main()
