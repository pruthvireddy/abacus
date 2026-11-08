#!/usr/bin/env python3
"""Compare saved pre-reveal predictions with explicitly selected training roles.

No market bars, detector, selector, API or source discovery is executed. Typed
inputs/selections are hydrated from retained JSON only, after the existing reveal
gate passes. Results go to a fresh directory; candidate artifacts are read-only.
"""
from __future__ import annotations

import argparse
from dataclasses import fields, is_dataclass, MISSING
from datetime import date, datetime, timezone
import hashlib
import importlib.util
import json
from math import isfinite
from pathlib import Path
import sys
import types
from typing import Union, get_args, get_origin, get_type_hints

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
STUDY = PHASE.parent
SCHEMA = "abacus.study29.phase4.saved-analysis-inputs/v1"
POLICIES = {p+"-"+d for p in ("P0", "B0", "B1") for d in ("D0", "D1")}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def hydrate(expected, value):
    """Reconstitute saved dataclass values; never execute a selection formula."""
    origin, arguments = get_origin(expected), get_args(expected)
    if origin in (Union, types.UnionType):
        for choice in arguments:
            try:
                return hydrate(choice, value)
            except (TypeError, ValueError):
                pass
        raise ValueError("saved value does not satisfy declared union")
    if value is None:
        if expected is type(None):
            return None
        raise ValueError("missing required saved value")
    if is_dataclass(expected):
        if not isinstance(value, dict):
            raise ValueError("saved dataclass must be a record")
        names = {field.name for field in fields(expected)}
        if set(value)-names:
            raise ValueError("unexpected saved dataclass fields: "+",".join(sorted(set(value)-names)))
        hints = get_type_hints(expected)
        arguments = {}
        for field in fields(expected):
            if field.name in value:
                arguments[field.name] = hydrate(hints[field.name], value[field.name])
            elif field.default is MISSING and field.default_factory is MISSING:
                raise ValueError("missing saved dataclass field: "+field.name)
        return expected(**arguments)
    if origin is tuple:
        if not isinstance(value, (list, tuple)):
            raise ValueError("saved tuple must be a sequence")
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            return tuple(hydrate(arguments[0], item) for item in value)
        if len(value) != len(arguments):
            raise ValueError("saved tuple width differs")
        return tuple(hydrate(kind, item) for kind, item in zip(arguments, value))
    if expected is datetime:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError("saved timestamp must be timezone aware")
        return result
    if expected is date:
        return date.fromisoformat(value)
    if expected is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError("saved numeric coordinate must be finite")
        return value
    if expected is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("saved integer required")
        return value
    if expected in (bool, str):
        if not isinstance(value, expected):
            raise ValueError("saved primitive type differs")
        return value
    raise ValueError("unsupported saved type: "+str(expected))


def hydrate_map(document, model):
    """Validate selection-to-pool lineage while retaining every saved decision."""
    if document.get("schema") != "abacus.study29.phase4.local-training-map/v1":
        raise ValueError("expected saved local-training map")
    inputs = hydrate(model.SelectionInputs, document["selector_inputs"])
    if inputs.trading_date.isoformat() != document["session_date"] or inputs.cutoff.astimezone(model.P3.BASE.NY).date() != inputs.trading_date:
        raise ValueError("saved input date differs from map")
    if set(document["selections"]) != POLICIES:
        raise ValueError("all six frozen saved alternatives are required")
    pool = {candidate.candidate_id: candidate for candidate in inputs.candidates}
    if len(pool) != len(inputs.candidates):
        raise ValueError("duplicate original candidate ID")

    def original(candidate):
        if candidate is not None and pool.get(candidate.candidate_id) != candidate:
            raise ValueError("selection is not an unchanged original candidate")

    selections = {}
    for key, raw in document["selections"].items():
        selection = hydrate(model.SelectionMap, raw)
        pivot_policy, target_policy = key.split("-")
        if (selection.cutoff != inputs.cutoff or selection.cutoff_close != inputs.cutoff_close or
                selection.pivot.cutoff != inputs.cutoff or selection.pivot.policy != pivot_policy or
                selection.input_identity != inputs.input_identity or
                selection.generator_identity != inputs.generator_identity or
                selection.candidate_ids != tuple(candidate.candidate_id for candidate in inputs.candidates)):
            raise ValueError("saved selection/input/cutoff identity differs")
        original(selection.pivot.candidate)
        for expected_side, branch in (("bullish",selection.bullish),("bearish",selection.bearish)):
            if branch.side != expected_side or branch.policy != target_policy or len(branch.targets) > 3:
                raise ValueError("saved branch policy/cap differs")
            if selection.pivot.fallback and branch.targets:
                raise ValueError("fallback pivot cannot have frozen target choices")
            sign = 1 if branch.side == "bullish" else -1 if branch.side == "bearish" else 0
            if not sign:
                raise ValueError("unknown saved branch side")
            last = selection.pivot.price
            for rank, target in enumerate(branch.targets, 1):
                original(target.candidate)
                for member in target.group:
                    original(member)
                ids = [candidate.candidate_id for candidate in target.group]
                if (target.rank != rank or not ids or len(set(ids)) != len(ids) or
                        target.candidate.candidate_id != min(ids) or
                        target.originating_candidate_id not in ids or
                        any(member.price != target.candidate.price for member in target.group)):
                    raise ValueError("saved exact-price group/rank lineage differs")
                if last is None or sign*(target.candidate.price-last) <= inputs.buffer:
                    raise ValueError("saved target order/spacing differs")
                last = target.candidate.price
        selections[key] = selection
    return inputs, selections


def analyze_document(document, rows, model, source_analysis):
    inputs, selections = hydrate_map(document, model)
    day = document["session_date"]
    selected_rows = [row for row in rows if row["session_date"] == day]
    return {key: source_analysis.analyze_sources(day, selected_rows, inputs, choice, model)
            for key, choice in selections.items()}


def pinned(root, pin):
    path = (root/pin["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file() or digest(path) != pin["sha256"]:
        raise ValueError("mismatched explicit analysis pin: "+str(pin.get("path")))
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = (ROOT/args.manifest).resolve()
    output = (ROOT/args.output).resolve()
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unsupported saved-analysis manifest")
    stage = (ROOT/manifest["stage"]).resolve()
    gate_path = pinned(ROOT, manifest["reveal_gate"])
    required = {str(path.relative_to(ROOT)) for path in (
        Path(__file__), PHASE/"select_sources.py", PHASE/"run_training.py", PHASE/"source_roles.py",
        PHASE/"settings.json", PHASE/"interpretation-record.md", STUDY/"src/phase4_model.py",
        STUDY/"src/phase3_model.py", STUDY/"src/reference_model.py", STUDY/"phase3/matching.py")}
    files = {pin["path"]: pin for pin in manifest["files"]}
    if not required <= set(files):
        raise ValueError("analysis producer dependency pins are incomplete")
    for name in sorted(required):
        pinned(ROOT, files[name])
    gate_checker = load_module("study29_phase4_saved_analysis_gate", PHASE/"select_sources.py")
    # Gate validation precedes the first updated role-ledger or candidate-map read.
    gate_receipt = gate_checker.validate_gate(ROOT, stage, gate_path)
    if output.exists() or output.parent != stage:
        raise ValueError("use a fresh output directory within the explicit Phase4 stage")
    settings = json.loads((PHASE/"settings.json").read_text())
    allowed = settings["training_dates"]
    pins = manifest["maps"]
    if len(pins) != len(allowed) or {pin["session_date"] for pin in pins} != set(allowed):
        raise ValueError("all ten unique explicit training-map pins required")
    by_day = {pin["session_date"]: pin for pin in pins}
    for capture in gate_receipt["captures"]:
        declared = by_day[capture["session_date"]]
        retained = capture["candidate_map"]
        if (declared["path"], declared["sha256"]) != (retained["path"], retained["sha256"]):
            raise ValueError("analysis must use the seven exact pre-reveal map artifacts")
    ledger_path = pinned(ROOT, manifest["source_ledger"])
    if not ledger_path.is_relative_to(PHASE) and not ledger_path.is_relative_to(stage):
        raise ValueError("role ledger must be explicit study/stage artifact")
    ledger = json.loads(ledger_path.read_text())
    rows = ledger["occurrences"]
    if any(row.get("session_date") not in allowed for row in rows):
        raise ValueError("source role outside authorized training dates")
    sessions = {record["session_date"]: record for record in ledger.get("session_records", [])}
    represented = {row.get("session_date") for row in rows}
    for day in set(allowed)-represented:
        status = sessions.get(day,{})
        if status.get("source_review_status") not in {"unavailable", "missing", "source_suitability_failure"} or not status.get("failure_reasons"):
            raise ValueError("missing source roles require an explicit reviewed suitability failure: "+day)
    model = load_module("study29_phase4_saved_analysis_model", STUDY/"src/phase4_model.py")
    source_analysis = load_module("study29_phase4_saved_analysis_roles", PHASE/"run_training.py")
    payloads = []
    for day in allowed:
        pin = by_day[day]
        map_path = pinned(ROOT, pin)
        if not map_path.is_relative_to(stage):
            raise ValueError("candidate maps must be retained within the explicit stage")
        document = json.loads(map_path.read_text())
        if document.get("session_date") != day:
            raise ValueError("map date differs from analysis pin")
        payloads.append({"schema":"abacus.study29.phase4.saved-comparison/v1", "session_date":day,
            "map":pin, "source_ledger":manifest["source_ledger"],
            "analysis":analyze_document(document,rows,model,source_analysis),
            "source_review_status":sessions.get(day,{}).get("source_review_status","explicit_role_rows_provided"),
            "source_failure_reasons":sessions.get(day,{}).get("failure_reasons",[]),
            "selection_recomputed":False, "candidate_inputs_modified":False,
            "execution":"saved_prediction_source_comparison_not_Pine_or_profitability"})
    # All reads, hash checks and calculations precede creation of a fresh output.
    output.mkdir()
    for payload in payloads:
        (output/(payload["session_date"]+".json")).write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
    summary={"schema":"abacus.study29.phase4.saved-comparisons/v1", "recorded_at":datetime.now(timezone.utc).isoformat(),
        "input_manifest":{"path":str(manifest_path.relative_to(ROOT)),"sha256":digest(manifest_path)},
        "gate":gate_receipt,"source_ledger":manifest["source_ledger"],"selection_recomputed":False,
        "records":[{"session_date":item["session_date"],"path":str((output/(item["session_date"]+".json")).relative_to(ROOT)),
                    "sha256":digest(output/(item["session_date"]+".json"))} for item in payloads]}
    (output/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"output":str(output.relative_to(ROOT)),"compared_dates":len(payloads),
                      "selection_recomputed":False,"candidate_inputs_modified":False},indent=2))


if __name__=="__main__":
    main()
