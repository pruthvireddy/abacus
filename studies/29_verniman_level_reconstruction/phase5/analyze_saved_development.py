#!/usr/bin/env python3
"""Evaluate four saved development maps with the frozen Phase 4 comparison API.

No market parser, candidate detector or selection formula is invoked. The new
map schema is adapted only in memory for the unchanged dataclass hydrator. All
source role/revision strata, interval rules and unmatched alternatives remain.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
STUDY = PHASE.parent
DATES = ("2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20")
POLICIES = {p + "-" + d for p in ("P0", "B0", "B1") for d in ("D0", "D1")}
SCHEMA = "abacus.study29.phase5.saved-analysis-inputs/v1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def pinned(root, pin):
    path = (root / pin["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file() or digest(path) != pin["sha256"]:
        raise ValueError("mismatched explicit saved-analysis pin: " + str(pin.get("path")))
    return path


def hydrate_saved(document, model, hydrator):
    if document.get("schema") != "abacus.study29.phase5.local-development-map/v1" or document.get("session_date") not in DATES:
        raise ValueError("exact authorized saved development map required")
    if set(document.get("selections", {})) != POLICIES:
        raise ValueError("all six frozen configurations required")
    compatible = dict(document)
    compatible["schema"] = "abacus.study29.phase4.local-training-map/v1"
    return hydrator.hydrate_map(compatible, model)


def analyze_document(document, rows, model, hydrator, comparison, *, window_adapter=None, assessments=None):
    inputs, selections = hydrate_saved(document, model, hydrator)
    day = document["session_date"]
    selected = [row for row in rows if row["session_date"] == day]
    if window_adapter is None:
        return {key: comparison.analyze_sources(day, selected, inputs, choice, model) for key, choice in selections.items()}
    original = comparison.source_refs
    comparison.source_refs = lambda records, matching: window_adapter.source_refs(records, matching, assessments, selected)
    try:
        return {key: comparison.analyze_sources(day, selected, inputs, choice, model) for key, choice in selections.items()}
    finally:
        comparison.source_refs = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_path, output = ((ROOT / value).resolve() for value in (args.manifest, args.output))
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unsupported development saved-analysis manifest")
    stage = (ROOT / manifest["stage"]).resolve()
    if not manifest_path.is_relative_to(stage) or output.exists() or output.parent != stage:
        raise ValueError("use retained inputs and a fresh output directory in the declared Phase 5 stage")
    files = {pin["path"]: pin for pin in manifest["files"]}
    required = {str(path.relative_to(ROOT)) for path in (Path(__file__).resolve(), PHASE / "select_sources.py", PHASE / "settings.json", PHASE / "window_identity.py", STUDY / "phase4/analyze_saved_training.py", STUDY / "phase4/run_training.py", STUDY / "phase4/source_roles.py")}
    if not required <= set(files) or len(files) != len(manifest["files"]):
        raise ValueError("saved-analysis orchestration/comparison producer pins incomplete")
    for path in sorted(required):
        pinned(ROOT, files[path])
    gate_module = module("study29_phase5_saved_analysis_gate", PHASE / "select_sources.py")
    gate_path = pinned(ROOT, manifest["reveal_gate"])
    # This precedes all answer-role or market-map JSON reads in this program.
    gate_receipt = gate_module.validate_gate(ROOT, stage, gate_path)
    predictions = manifest["maps"]
    if len(predictions) != 4 or {pin.get("session_date") for pin in predictions} != set(DATES):
        raise ValueError("all four unique saved development prediction pins required")
    by_day = {pin["session_date"]: pin for pin in predictions}
    for capture in gate_receipt["captures"]:
        declared, frozen = by_day[capture["session_date"]], capture["prediction"]
        if (declared["path"], declared["sha256"]) != (frozen["path"], frozen["sha256"]):
            raise ValueError("analysis may only use the exact four pre-reveal maps")
    ledger_path = pinned(ROOT, manifest["source_ledger"])
    if not (ledger_path.is_relative_to(PHASE) or ledger_path.is_relative_to(stage)):
        raise ValueError("explicit Phase 5 source-role artifact required")
    ledger = json.loads(ledger_path.read_text())
    if ledger.get("schema") != "abacus.study29.phase5.source-role-ledger/v1" or ledger.get("reveal_gate") != gate_receipt["gate"]:
        raise ValueError("source ledger must bind the same gate-approved selection")
    rows = ledger["occurrences"]
    if any(row.get("session_date") not in DATES for row in rows) or len({row.get("level_id") for row in rows}) != len(rows):
        raise ValueError("source role dates/occurrence identities differ")
    sessions = {row["session_date"]: row for row in ledger["session_records"]}
    if len(sessions) != 4 or set(sessions) != set(DATES):
        raise ValueError("all four scheduled source statuses required")
    represented = {row["session_date"] for row in rows if row.get("source_class") == "named_daily_plan"}
    for day in set(DATES) - represented:
        if sessions[day].get("source_review_status") != "source_suitability_failure" or not sessions[day].get("failure_reasons"):
            raise ValueError("missing canonical plan requires a retained suitability failure")
    producer = json.loads(pinned(ROOT, json.loads(gate_path.read_text())["producer_manifest"]).read_text())
    producer_path = ROOT / json.loads(gate_path.read_text())["producer_manifest"]["path"]
    snapshots = {row["role"]: (producer_path.parent / row["snapshot_path"]).resolve() for row in producer["files"]}
    model = module("study29_phase5_saved_model", snapshots["phase4_model"])
    hydrator = module("study29_phase5_fixed_hydrator", STUDY / "phase4/analyze_saved_training.py")
    comparison = module("study29_phase5_fixed_comparison", STUDY / "phase4/run_training.py")
    adapter = module("study29_phase5_explicit_window_adapter", PHASE / "window_identity.py")
    assessments = {row["level_id"]: adapter.assess(row, ROOT, allowed_evidence_roots=[stage / "selected-sources-release13", stage / "identity-evidence"]) for row in rows}
    assessed_rows = [{**row, "phase5_window_identity_assessment": assessments[row["level_id"]]} for row in rows]
    payloads = []
    for day in DATES:
        prediction = by_day[day]
        path = pinned(ROOT, prediction)
        if not path.is_relative_to(stage):
            raise ValueError("saved prediction outside explicit stage")
        document = json.loads(path.read_text())
        if document.get("session_date") != day:
            raise ValueError("saved prediction day differs from its pin")
        payloads.append({"schema": "abacus.study29.phase5.saved-comparison/v1", "session_date": day, "map": prediction, "source_ledger": manifest["source_ledger"], "source_review_status": sessions[day]["source_review_status"], "source_failure_reasons": sessions[day].get("failure_reasons", []),
                         "analysis": analyze_document(document, assessed_rows, model, hydrator, comparison, window_adapter=adapter, assessments=assessments), "selection_recomputed": False, "candidate_inputs_modified": False,
                         "source_window_identity_assessments": [{"source_occurrence_id": row["level_id"], **assessments[row["level_id"]]} for row in rows if row["session_date"] == day],
                         "format_adapter": "Only the in-memory document schema tag is adapted for the frozen Phase4 hydrator; source bytes and every saved candidate/decision remain unchanged.", "execution": "saved_prediction_comparison_not_Pine_execution_or_profitability"})
    output.mkdir()
    records = []
    for payload in payloads:
        path = output / (payload["session_date"] + ".json")
        with path.open("x") as handle:
            json.dump(payload, handle, indent=2, allow_nan=False); handle.write("\n")
        records.append({"session_date": payload["session_date"], "path": str(path.relative_to(ROOT)), "sha256": digest(path)})
    summary = {"schema": "abacus.study29.phase5.saved-comparisons/v1", "recorded_at": datetime.now(timezone.utc).isoformat(), "input_manifest": {"path": str(manifest_path.relative_to(ROOT)), "sha256": digest(manifest_path)}, "reveal_gate": gate_receipt, "source_ledger": manifest["source_ledger"], "configurations": sorted(POLICIES), "records": records, "selection_recomputed": False, "candidate_inputs_modified": False,
               "comparison_contract": "Frozen Phase4 family/window/contract-qualified matching with one-point interval-gap, separate point error, one-to-one source revision/class/branch strata; unknown windows remain not estimable.", "automatic_winner_selected": False}
    with (output / "summary.json").open("x") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False); handle.write("\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "compared_dates": 4, "selection_recomputed": False, "candidate_inputs_modified": False}, indent=2))


if __name__ == "__main__":
    main()
