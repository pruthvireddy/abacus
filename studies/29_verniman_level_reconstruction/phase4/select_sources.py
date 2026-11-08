#!/usr/bin/env python3
"""Guarded, exact-date Phase 4 source intake using immutable release13.

The standard-library --check-gate mode never imports the data loader or reads
answer sources. Selection is allowed only after seven actual expanded maps,
current-comparator predictions and browser captures are byte-pinned and checked.
No operator flag substitutes for those artifacts. No network access occurs.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from math import isfinite
from pathlib import Path
from zoneinfo import ZoneInfo

DATES = ("2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12", "2026-10-13", "2026-10-14")
ADDITIONAL = DATES[3:]
STUDY = "studies/29_verniman_level_reconstruction"
PHASE = STUDY + "/phase4"
STAGE = "work/29_verniman_level_reconstruction/phase4_20261031T010249Z"
MANIFEST = "catalog/datasets/verniman_daily_levels__13.0.0.json"
MANIFEST_SHA256 = "39a12cd01b131729908a6b7743a710eaefe73f86e7df9ecb66787787b88277bf"
CANDIDATE_SETTINGS = STUDY + "/phase3/settings.json"
CANDIDATE_SETTINGS_SHA256 = "c0297d86f2a6dce33b6888a174c31d6390477dd0e12d78a46832173e0f17653a"
AUTOPIVOT_PINE = STUDY + "/indicator/verniman_pivot_levels.pine"
PRIOR_AUTOPIVOT_PINE_SHA256 = "22604477ef983021911320b255d0d08e937ab10c81f852ca25358fb972fd1a49"
AUTOPIVOT_PINE_SHA256 = "228ce4f4cc938cfb967eed4b20df8db0711755fb2fd8d4ae2cc9be8632dd3145"
AUTOPIVOT_MODEL = STUDY + "/src/pivot_model.py"
PRIOR_AUTOPIVOT_MODEL_SHA256 = "e29249e2ae9e4663cc7d8a829ca3b1cea7de12a288aa21cdf1c4301969575d29"
AUTOPIVOT_MODEL_SHA256 = "1fc67f44ea3dc6bc374a3bfcf526bfea419af8316f7eaf82cc179d01c3e466f4"
LOADER = "packages/bhishma/src/abacus_bhishma/verniman_consolidated.py"
INTAKE = "data/inbox/x/verniman_eod/20261028_backfill_2026"
WINDOWS = {"completed_RTH", "overnight_prefix", "current_week_prefix", "previous_completed_week", "explicit_composite_RTH3"}
TABLES = ("outlooks", "levels", "issues", "coverage", "source_coverage", "release_membership", "observations", "observation_levels")
NY = ZoneInfo("America/New_York")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def within(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("artifact path escapes the explicit workspace")
    return path


def stamp(text):
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware capture/boundary time required")
    return value


def pinned(root, record, *, expected_path=None, expected_sha=None):
    if expected_path is not None and record.get("path") != expected_path:
        raise ValueError("unexpected identity path: " + str(record.get("path")))
    if expected_sha is not None and record.get("sha256") != expected_sha:
        raise ValueError("unexpected pinned identity: " + str(record.get("path")))
    path = within(root, record["path"])
    if not path.is_file() or digest(path) != record.get("sha256"):
        raise ValueError("missing or mismatched pinned artifact: " + record["path"])
    return path


def semantic(document, selector):
    value = document
    for key in selector.split("."):
        if not isinstance(value, dict) or key not in value:
            raise ValueError("required capture semantics absent: " + selector)
        value = value[key]
    return value


def cutoff_fields(record, day, *, baseline=False):
    cutoff = stamp(record["cutoff"])
    opening = stamp(record["last_open" if baseline else "last_included_open"])
    closing = stamp(record["last_close" if baseline else "last_included_close"])
    expected = datetime.combine(date.fromisoformat(day), datetime.min.time(), NY).replace(hour=9, minute=25)
    if cutoff != expected or closing != cutoff or opening != cutoff - timedelta(minutes=5):
        raise ValueError("capture does not end with the exact09:20-09:25 boundary: " + day)
    if record.get("trading_date") != day:
        raise ValueError("capture trading date differs from its declaration")


def check_expanded(record, day):
    baseline = record.get("baseline") or {}
    cutoff_fields(baseline, day, baseline=True)
    values = baseline.get("values")
    if not isinstance(values, list) or len(values) != 19:
        raise ValueError("actual original19 fields are required, not failure placeholders")
    distributions, ledgers = record.get("distributions"), record.get("candidate_ledgers")
    if not isinstance(distributions, list) or not isinstance(ledgers, list) or len(distributions) != 5 or len(ledgers) != 5:
        raise ValueError("all five identified distributions and calculation ledgers required")
    if {d.get("window") for d in distributions} != WINDOWS:
        raise ValueError("expanded map window inventory differs")
    ready = []
    unavailable = []
    for d, ledger in zip(distributions, ledgers):
        window = d["window"]
        if not d.get("profile_id") or not d.get("input_identity") or not d.get("code_identity"):
            raise ValueError("distribution provenance missing")
        if d.get("settings_identity") != CANDIDATE_SETTINGS_SHA256:
            raise ValueError("candidate settings differ from the frozen control")
        recorded = ledger.get("distribution", {})
        if recorded.get("metadata", {}).get("profile_id") != d["profile_id"]:
            raise ValueError("distribution and candidate ledger identity differ")
        status = ledger.get("status")
        if status == "ready":
            if recorded.get("readiness") != "ready" or recorded.get("reasons"):
                raise ValueError("inconsistent ready distribution")
            rows = recorded.get("rows")
            total = recorded.get("total_mass")
            if not isinstance(rows, list) or not rows or total is None or not isfinite(total) or total <= 0:
                raise ValueError("ready input must retain observed positive row mass")
            if any(r.get("raw_mass") is None or not isfinite(r["raw_mass"]) or r["raw_mass"] < 0 for r in rows):
                raise ValueError("invalid ready row mass")
            if not all(key in ledger for key in ("peaks", "regions", "lvn_ledger", "edge_ledger", "presentation", "counts")):
                raise ValueError("actual uncapped candidate calculation ledger missing")
            ready.append(window)
        elif status == "unavailable" and recorded.get("reasons"):
            unavailable.append(window)
        else:
            raise ValueError("missing explicit per-family readiness")
    if not {"completed_RTH", "overnight_prefix"} <= set(ready):
        raise ValueError("required RTH/ON inputs unavailable; placeholder does not pass reveal gate")
    if any(values[i] is None or not isfinite(values[i]) for i in range(8, 16)):
        raise ValueError("required RTH/ON original baseline references missing")
    if not isinstance(record.get("composite_ledger"), dict) or not isinstance(record.get("projection_ledgers"), list):
        raise ValueError("composite lineage and PBT eligibility ledger required")
    return {"ready_windows": ready, "unavailable_windows": unavailable}


def check_comparator_freeze(root, stage, gate, created):
    """Bind predictions to the source bytes retained before their execution.

    Mutable workspace diagnostics may change after capture. They cannot replace
    the source identity in an existing prediction or its immutable producer.
    """
    freeze = gate.get("comparator_freeze") or {}
    if freeze.get("source_basis") != "immutable_at_capture":
        raise ValueError("explicit immutable comparator-at-capture freeze required")
    producer_path = pinned(root, freeze["producer_manifest"])
    if not producer_path.is_relative_to(stage):
        raise ValueError("comparator producer must be retained in the Phase4 stage")
    producer = json.loads(producer_path.read_text())
    retained = stamp(producer["retained_before_market_execution_at"])
    if (producer.get("schema") != "abacus.study29.phase4.local-producer/v1" or
            retained != stamp(freeze["retained_before_market_execution_at"]) or retained > created or
            producer.get("current_autopivot_pine_sha256") != AUTOPIVOT_PINE_SHA256 or
            producer.get("current_autopivot_model_sha256") != AUTOPIVOT_MODEL_SHA256):
        raise ValueError("comparator producer identity or capture chronology differs")
    files = {r["path"]: r for r in producer["files"]}
    for name, original, expected in (("autopivot_pine", AUTOPIVOT_PINE, AUTOPIVOT_PINE_SHA256),
                                     ("autopivot_model", AUTOPIVOT_MODEL, AUTOPIVOT_MODEL_SHA256)):
        record = files.get(original) or {}
        snapshot = (producer_path.parent / record.get("snapshot_path", "")).resolve()
        if not snapshot.is_relative_to(stage) or record.get("sha256") != expected:
            raise ValueError("comparator snapshot is not bound to its retained producer")
        pinned(root, gate[name], expected_path=str(snapshot.relative_to(root)), expected_sha=expected)
    return producer, retained


def validate_gate(root, stage, gate_path, *, now=None):
    root, stage, gate_path = root.resolve(), stage.resolve(), gate_path.resolve()
    if stage != within(root, STAGE) or not gate_path.is_relative_to(stage):
        raise ValueError("use the explicit Phase4 stage and a gate retained inside it")
    gate = json.loads(gate_path.read_text())
    if gate.get("schema") != "abacus.study29.phase4.reveal-gate/v1":
        raise ValueError("unsupported reveal-gate schema")
    now = now or datetime.now(timezone.utc)
    created = stamp(gate["recorded_at"])
    if created > now:
        raise ValueError("gate timestamp is in the future")
    freeze = json.loads((stage / "protocol-freeze.json").read_text())
    frozen = {r["path"]: r["sha256"] for r in freeze["frozen_files"]}
    for pin in freeze["frozen_files"]:
        pinned(root, pin)
    pinned(root, gate["protocol"], expected_path=PHASE + "/protocol.md", expected_sha=frozen[PHASE + "/protocol.md"])
    pinned(root, gate["settings"], expected_path=PHASE + "/settings.json", expected_sha=frozen[PHASE + "/settings.json"])
    pinned(root, gate["candidate_settings"], expected_path=CANDIDATE_SETTINGS, expected_sha=CANDIDATE_SETTINGS_SHA256)
    comparator_producer, comparator_retained = check_comparator_freeze(root, stage, gate, created)
    reconciliation_path = pinned(root, gate["comparator_reconciliation"])
    reconciliation = json.loads(reconciliation_path.read_text())
    if (reconciliation.get("schema") != "abacus.study29.phase4.comparator-reconciliation/v1" or
            reconciliation.get("old_source_sha256") != PRIOR_AUTOPIVOT_PINE_SHA256 or
            reconciliation.get("old_model_sha256") != PRIOR_AUTOPIVOT_MODEL_SHA256 or
            reconciliation.get("current_source_sha256") != AUTOPIVOT_PINE_SHA256 or
            reconciliation.get("current_model_sha256") != AUTOPIVOT_MODEL_SHA256 or
            not all(reconciliation.get("checks", {}).get(name) is True for name in
                ("primary_selector_block_equal", "alternate_function_equal", "profile_and_N1_E1_code_equal", "model_existing_functions_byte_prefix_unchanged"))):
        raise ValueError("current comparator must retain its explicit prior-policy reconciliation")
    pinned(root, gate["loader_code"], expected_path=LOADER)
    exposure_path = pinned(root, gate["exposure_audit"])
    exposure = json.loads(exposure_path.read_text())
    # This is a recorded audit, not an automatic proof of pristine exposure.
    exposed = exposure.get("already_exposed_training_dates")
    if not isinstance(exposed, list) or any(day not in DATES for day in exposed):
        raise ValueError("explicit bounded previous-exposure audit required")
    captures = gate.get("captures")
    if not isinstance(captures, list) or len(captures) != 7 or {c.get("session_date") for c in captures} != set(ADDITIONAL):
        raise ValueError("all seven exact additional-date captures are required")
    result = []
    for capture in sorted(captures, key=lambda c: c["session_date"]):
        day = capture["session_date"]
        captured = stamp(capture["model_pre_reveal_captured_at"])
        if captured > created or captured < comparator_retained:
            raise ValueError("capture chronology is after the gate")
        map_pin = capture["candidate_map"]
        if map_pin.get("semantic_selector") != "expanded_snapshot":
            raise ValueError("expanded-map semantic selector must be explicit")
        map_path = pinned(root, map_pin)
        map_document = json.loads(map_path.read_text())
        if map_document.get("session_date") != day:
            raise ValueError("map date differs from gate capture")
        if map_document.get("producer_revision") != comparator_producer.get("id"):
            raise ValueError("map producer differs from comparator-at-capture freeze")
        readiness = check_expanded(semantic(map_document, map_pin["semantic_selector"]), day)
        auto_pin = capture["autopivot_prediction"]
        if auto_pin.get("semantic_selector") not in ("autopivot_comparator.frozen", "frozen"):
            raise ValueError("current comparator semantic selector must be explicit")
        auto_path = pinned(root, auto_pin)
        auto_document = map_document if auto_path == map_path else json.loads(auto_path.read_text())
        auto = semantic(auto_document, auto_pin["semantic_selector"])
        cutoff_fields(auto, day)
        selected = auto.get("selection") or {}
        price, inputs = selected.get("price"), selected.get("inputs")
        if price is None or not isfinite(price) or not isinstance(inputs, list) or len(inputs) != 5 or any(v is None or not isfinite(v) for v in inputs):
            raise ValueError("actual current-comparator prediction and five frozen inputs required")
        browser = capture.get("browser_evidence")
        if not isinstance(browser, list) or not browser:
            raise ValueError("per-date browser capture hash required")
        for pin in browser:
            path = pinned(root, pin)
            if path.stat().st_size == 0:
                raise ValueError("empty browser-evidence placeholder")
        result.append({"session_date": day, "model_pre_reveal_captured_at": captured.isoformat(),
                       "candidate_map": map_pin, "autopivot_prediction": auto_pin,
                       "browser_evidence": browser, **readiness})
    return {"status": "passed", "gate": {"path": str(gate_path.relative_to(root)), "sha256": digest(gate_path)},
            "recorded_at": created.isoformat(), "checked_at": now.isoformat(), "captures": result,
            "comparator_freeze": gate["comparator_freeze"],
            "previously_exposed_training_dates": exposed,
            "scope": "Checks retained bytes, explicit semantic records and chronology claims; not independent native execution, OCR or proof of unseen exposure."}


def bounded_rows(rows, day):
    if day not in DATES or any(str(row.get("session_date")) != day for row in rows):
        raise ValueError("source row outside the exact authorized session")
    return rows



def bounded_observation(observation, day):
    """Project same-day/undated nested sources; never rewrite the intake original.

    A filename/top-level date does not override a source's different explicit
    chart date. Retain only metadata for such excluded sources, never their
    target text, markers, notes or pixels. Unknown chart dates stay qualified.
    """
    bounded_rows([observation], day)
    excluded = []
    for source in observation.get("sources", []):
        raw = source.get("chart_session_date")
        try:
            claimed = date.fromisoformat(raw).isoformat() if isinstance(raw, str) else None
        except ValueError:
            claimed = None
        if claimed is not None and claimed != day:
            excluded.append({key: source.get(key) for key in
                ("source_id", "post_id", "post_url", "posted_at", "captured_at", "role",
                 "chart_session_date", "image_index", "local_capture_path", "capture_sha256")})
    if not excluded:
        return observation, []
    ids = {source["source_id"] for source in excluded}
    projected = dict(observation)
    projected["sources"] = [s for s in observation.get("sources", []) if s.get("source_id") not in ids]
    for field in ("markers", "closing_notes"):
        projected[field] = [r for r in observation.get(field, []) if r.get("source_id") not in ids]
    projected["issues"] = [r for r in observation.get("issues", []) if r.get("source_id") not in ids and r.get("source_id") is not None]
    projected["session_notes"] = None
    projected["coverage_basis"] = "Bounded Phase4 projection; known-other-date nested source content and unscoped notes withheld. Original retained by locator/hash."
    projected["phase4_selection_projection"] = {"excluded_source_metadata": excluded,
        "reason": "explicit_nested_chart_date_differs_from_requested_session",
        "original_intake_unchanged": True, "unknown_chart_dates": "retained_with_original_uncertainty"}
    return projected, excluded


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, default=str)
        handle.write("\n")


def select(root, stage, gate_path):
    checked = validate_gate(root, stage, gate_path)
    # All prerequisite checks precede loader import and any answer source read.
    if digest(root / MANIFEST) != MANIFEST_SHA256:
        raise ValueError("release13 immutable manifest identity differs")
    selected = stage / "selected-sources-release13"
    if selected.exists():
        raise FileExistsError("refusing to overwrite retained selected sources")
    from abacus_bhishma.verniman_consolidated import load_release
    manifest = json.loads((root / MANIFEST).read_text())
    files = {record["path"]: record for record in manifest["files"]}
    inventory = {"schema": "abacus.study29.phase4.source-selection/v1",
        "selection_started_at": datetime.now(timezone.utc).isoformat(), "authorized_dates": list(DATES),
        "dataset": {"path": MANIFEST, "sha256": MANIFEST_SHA256, "version": "13.0.0"},
        "gate": checked, "loader_sha256": digest(root / LOADER),
        "selector_sha256": digest(Path(__file__)),
        "loader_scope": "Public loader internally verifies/reads release tables before filtering. Only exact one-day returned rows are checked/serialized; unrestricted rows never enter model context.",
        "timing_policy": "Retain every original available_at/source/capture timestamp; no reconstruction repairs historical timing.",
        "source_revisions_policy": "Retain all returned revisions and all exact-date intake revision filenames; no closest-price revision selection.",
        "release_table_inputs": {}, "tables": {}, "intake": []}
    for table in TABLES:
        inventory["tables"][table] = {}
        inventory["release_table_inputs"][table] = [files[path] for path in manifest["tables"][table]["paths"]]
        for day in DATES:
            end = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
            result = load_release(root, MANIFEST, MANIFEST_SHA256, table=table, start_date=day, end_date=end)
            rows = bounded_rows(result.to_pylist(), day)
            category = "user-recollections" if table in ("observations", "observation_levels") else "release"
            target = selected / category / day / (table + ".json")
            write_new(target, rows)
            inventory["tables"][table][day] = {"rows": len(rows), "path": str(target.relative_to(stage)), "sha256": digest(target), "start_inclusive": day, "end_exclusive": end}
    for day in DATES:
        originals = sorted((root / INTAKE / "observations").glob(day + "__r*.json"))
        if not originals:
            inventory["intake"].append({"session_date": day, "status": "missing"})
        revisions = []
        for original in originals:
            observation = json.loads(original.read_text())
            bounded_rows([observation], day)
            if observation.get("observation_id") != original.stem:
                raise ValueError("intake filename/identity mismatch")
            revision = observation.get("revision")
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1 or revision in revisions:
                raise ValueError("invalid/duplicate retained intake revision")
            revisions.append(revision)
            target = selected / "intake" / original.name
            projected, excluded = bounded_observation(observation, day)
            write_new(target, projected)
            inventory["intake"].append({"session_date": day, "path": str(original.relative_to(root)), "sha256": digest(original), "revision": revision,
                "observation_id": observation["observation_id"], "supersedes": observation.get("supersedes"),
                "selected_path": str(target.relative_to(stage)), "selected_sha256": digest(target), "status": observation.get("review_status"),
                "excluded_other_chart_date_source_metadata": excluded, "original_intake_unchanged": True})
    inventory["selection_completed_at"] = datetime.now(timezone.utc).isoformat()
    target = stage / "source-selection-manifest-release13.json"
    write_new(target, inventory)
    return {"status": "selected", "manifest": str(target), "dates": list(DATES),
            "table_counts": {table: {day: item["rows"] for day, item in rows.items()} for table, rows in inventory["tables"].items()},
            "intake_records": len(inventory["intake"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--capture-gate", type=Path, required=True)
    parser.add_argument("--check-gate", action="store_true", help="standard-library read-only prerequisite audit; no target-source access")
    args = parser.parse_args()
    root = args.root.resolve()
    stage = (root / args.stage).resolve() if not args.stage.is_absolute() else args.stage.resolve()
    gate = (root / args.capture_gate).resolve() if not args.capture_gate.is_absolute() else args.capture_gate.resolve()
    result = validate_gate(root, stage, gate) if args.check_gate else select(root, stage, gate)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
