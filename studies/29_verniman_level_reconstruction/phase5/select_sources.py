#!/usr/bin/env python3
"""Four-date Phase 5 reveal guard and bounded release-13 source selection.

The standard-library check path reads only frozen protocol, market predictions,
native verification records and exposure metadata. It never imports a source
loader. A passing gate validates bytes/declared observations, not unseen-source
purity, independent OCR or source-method reproduction.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from math import isfinite
from pathlib import Path
import re
from zoneinfo import ZoneInfo

DATES = ("2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20")
POLICIES = {p + "-" + d for p in ("P0", "B0", "B1") for d in ("D0", "D1")}
STUDY = "studies/29_verniman_level_reconstruction"
PHASE = STUDY + "/phase5"
STAGE_PARENT = "work/29_verniman_level_reconstruction"
MANIFEST = "catalog/datasets/verniman_daily_levels__13.0.0.json"
MANIFEST_SHA256 = "39a12cd01b131729908a6b7743a710eaefe73f86e7df9ecb66787787b88277bf"
LOADER = "packages/bhishma/src/abacus_bhishma/verniman_consolidated.py"
INTAKE = "data/inbox/x/verniman_eod/20261028_backfill_2026"
WINDOWS = {"completed_RTH", "overnight_prefix", "current_week_prefix", "previous_completed_week", "explicit_composite_RTH3"}
TABLES = ("outlooks", "levels", "issues", "coverage", "source_coverage", "release_membership", "observations", "observation_levels")
NY = ZoneInfo("America/New_York")
EXPECTED = {
    "candidate_pine": "034c3731f2ada4620aac9a80ca20261d0a06376bee044fa30e95529ad9e1954c",
    "selector_pine": "1145834bfb240029f07342e52f98d805771ca4f2a39a646c19e80d3846794924",
    "phase4_model": "bec68316b9028cff8d43e6e9fbcef86c4e46a5be792b9df325d42753a85547c5",
    "phase3_model": "e54ba9950618e99dc1fe57ac5fab19cf43e990099b98df8b25f506bd8c92f48b",
    "reference_model": "712016db99bc62b35c787b9269825529221636545d903d814993284fbd769bbd",
    "matcher": "b595fbca570df868888dd58c8fe341ee341b69770d902319ba25ac8fd1fd90a6",
    "phase3_settings": "c0297d86f2a6dce33b6888a174c31d6390477dd0e12d78a46832173e0f17653a",
    "phase4_settings": "5a1cc36f7c0a2b16ee82ab9eccd285c9a897d933d2b0ad1e02a2c026e5bb5f1a",
    "autopivot_pine": "228ce4f4cc938cfb967eed4b20df8db0711755fb2fd8d4ae2cc9be8632dd3145",
    "autopivot_model": "1fc67f44ea3dc6bc374a3bfcf526bfea419af8316f7eaf82cc179d01c3e466f4",
}
FROZEN_DOCUMENTS = {"protocol": "protocol.md", "settings": "settings.json", "input_declaration": "input-declaration.json", "decision_rule": "decision-rule.md"}
COMPARISON_FILES = {
    STUDY + "/phase4/analyze_saved_training.py": "00ea8e9a8b516b3a000481d9dc8f66222acf9b797beabc0a5dce246803b0d77f",
    STUDY + "/phase4/run_training.py": "9c93687619d01d064b398cdc124d2336d232cd6a855fddd76e04cfd40efa124d",
    STUDY + "/phase4/source_roles.py": "e1f4b7c0b1795ac37a86deac05a1ae5f4e7000e17d87022ef1ea88548d9a8c31",
}
BASELINE_NAMES = ("FULL_HIGH", "FULL_LOW", "WEEK_VAH", "WEEK_POC", "WEEK_VAL", "PREVWEEK_VAH", "PREVWEEK_POC", "PREVWEEK_VAL", "YVAH", "YPOC", "YVAL", "ONVAH", "ONPOC", "ONVAL", "ONH", "ONL", "RTH_HIGH", "RTH_LOW", "RTH_CLOSE")
MARKET = {"symbol": "CME_MINI:ESZ2026", "contract": "ESZ2026", "feed": "CME GLOBEX", "adjustment": "individual_contract_unadjusted", "minutes": 5, "session": "ETH", "timezone": "America/New_York", "tick_size": .25, "row_ticks": 16, "value_area_percent": 70, "grid_origin": 0, "cutoff_hour": 9, "cutoff_minute": 25, "manual_anchors": []}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def within(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("artifact path escapes the explicit workspace")
    return path


def stamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return result


def pinned(root, record, *, expected_path=None, expected_sha=None):
    if expected_path is not None and record.get("path") != expected_path:
        raise ValueError("unexpected artifact identity path")
    if expected_sha is not None and record.get("sha256") != expected_sha:
        raise ValueError("unexpected frozen implementation hash")
    path = within(root, record["path"])
    if not path.is_file() or digest(path) != record.get("sha256"):
        raise ValueError("missing or mismatched pinned artifact: " + record["path"])
    return path


def finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)


def boundary(record, day, *, baseline=False):
    cutoff = datetime.combine(date.fromisoformat(day), datetime.min.time(), NY).replace(hour=9, minute=25)
    opening = record.get("last_open" if baseline else "last_included_open")
    closing = record.get("last_close" if baseline else "last_included_close")
    if stamp(opening) != cutoff - timedelta(minutes=5) or stamp(closing) != cutoff:
        raise ValueError("exact completed 09:20-09:25 boundary required")
    if record.get("cutoff") is not None and stamp(record["cutoff"]) != cutoff:
        raise ValueError("cutoff differs from 09:25 New York")
    return cutoff


def check_expanded(record, day):
    baseline = record.get("baseline") or {}
    if baseline.get("trading_date") != day:
        raise ValueError("baseline trading date differs")
    boundary(baseline, day, baseline=True)
    values = baseline.get("values")
    if not isinstance(values, list) or len(values) != 19 or not all(finite(v) for v in values):
        raise ValueError("all 19 finite original fields required; failure/baseline-only placeholders do not pass")
    distributions, ledgers = record.get("distributions"), record.get("candidate_ledgers")
    if not isinstance(distributions, list) or not isinstance(ledgers, list) or len(distributions) != 5 or len(ledgers) != 5:
        raise ValueError("all five expanded profile calculation ledgers required")
    if {d.get("window") for d in distributions} != WINDOWS:
        raise ValueError("five profile/window identities differ")
    for metadata, ledger in zip(distributions, ledgers):
        recorded = ledger.get("distribution") or {}
        if (not metadata.get("profile_id") or not metadata.get("input_identity") or not metadata.get("code_identity") or
                metadata.get("code_identity") != EXPECTED["phase3_model"] or
                metadata.get("settings_identity") != EXPECTED["phase3_settings"] or
                recorded.get("metadata", {}).get("profile_id") != metadata["profile_id"]):
            raise ValueError("profile provenance or frozen candidate settings differ")
        for key, expected in (("contract", "ESZ2026"), ("feed", "CME GLOBEX"), ("adjustment", "individual_contract_unadjusted"), ("tick_size", .25), ("row_size", 4), ("grid_origin", 0), ("measurement", "uniform_chart_bar_volume_across_inclusive_touched_bins")):
            if metadata.get(key) != expected:
                raise ValueError("profile contract/feed/adjustment/grid/measurement differs")
        if ledger.get("status") != "ready" or recorded.get("readiness") != "ready" or recorded.get("reasons"):
            raise ValueError("all five required profiles must be ready before development reveal")
        rows, mass = recorded.get("rows"), recorded.get("total_mass")
        if (not isinstance(rows, list) or not rows or not finite(mass) or mass <= 0 or
                any(not finite(r.get("raw_mass")) or r["raw_mass"] < 0 for r in rows)):
            raise ValueError("ready profile must retain positive observed mass and finite rows")
        if not all(name in ledger for name in ("peaks", "regions", "lvn_ledger", "edge_ledger", "presentation", "counts")):
            raise ValueError("full candidate/rejection/cap ledger required")
    if not isinstance(record.get("composite_ledger"), dict) or not isinstance(record.get("projection_ledgers"), list):
        raise ValueError("composite lineage and explicit PBT eligibility required")
    return {"ready_windows": sorted(WINDOWS), "unavailable_windows": []}


def check_selections(document, day):
    inputs = document.get("selector_inputs") or {}
    if inputs.get("trading_date") != day:
        raise ValueError("selector input date differs")
    cutoff = boundary(inputs, day)
    if not finite(inputs.get("cutoff_close")) or inputs.get("rth_ready") is not True or inputs.get("overnight_ready") is not True:
        raise ValueError("finite cutoff P and ready RTH/ON inputs required")
    if inputs.get("tick_size") != 0.25 or inputs.get("row_size") != 4 or inputs.get("contract") != "ESZ2026" or inputs.get("adjustment") != "individual_contract_unadjusted":
        raise ValueError("selector market configuration differs")
    candidates = inputs.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("actual frozen candidate pool required")
    pool = {c.get("candidate_id"): c for c in candidates}
    if None in pool or len(pool) != len(candidates):
        raise ValueError("unique original candidate identities required")
    for candidate in candidates:
        interval = candidate.get("interval")
        if not finite(candidate.get("price")) or not isinstance(interval, list) or len(interval) != 2 or not all(finite(v) for v in interval) or interval[0] > interval[1]:
            raise ValueError("candidate original coordinate/interval invalid")
    original_values = document["expanded_snapshot"]["baseline"]["values"]
    for name, value in zip(BASELINE_NAMES, original_values):
        original = [c for c in candidates if c.get("origin_role") == name]
        if len(original) != 1 or original[0]["price"] != value:
            raise ValueError("selector original-19 coordinates differ from the expanded baseline")

    def original(candidate):
        if candidate is not None and pool.get(candidate.get("candidate_id")) != candidate:
            raise ValueError("saved choice differs from its original candidate")

    selections = document.get("selections")
    if not isinstance(selections, dict) or set(selections) != POLICIES:
        raise ValueError("all six predeclared configurations must be saved")
    for key, selection in selections.items():
        p, d = key.split("-")
        pivot = selection.get("pivot") or {}
        if (selection.get("policy") != "phase4-4.0.0" or stamp(selection["cutoff"]) != cutoff or
                selection.get("cutoff_close") != inputs["cutoff_close"] or pivot.get("policy") != p or
                stamp(pivot["cutoff"]) != cutoff or selection.get("input_identity") != inputs.get("input_identity") or
                selection.get("generator_identity") != inputs.get("generator_identity") or
                selection.get("candidate_ids") != [c["candidate_id"] for c in candidates]):
            raise ValueError("selection policy/input/cutoff lineage differs")
        original(pivot.get("candidate"))
        if not pivot.get("reason_code") or not pivot.get("status") or not isinstance(pivot.get("fallback"), bool):
            raise ValueError("explicit pivot reason/readiness/fallback required")
        for side, sign in (("bullish", 1), ("bearish", -1)):
            branch = selection.get(side) or {}
            targets = branch.get("targets")
            if branch.get("side") != side or branch.get("policy") != d or not isinstance(targets, list) or len(targets) > 3 or not branch.get("status"):
                raise ValueError("bounded branch policies/status required")
            if pivot["fallback"] and targets:
                raise ValueError("fallback pivot must abstain from both target branches")
            last = (pivot.get("candidate") or {}).get("price")
            for rank, target in enumerate(targets, 1):
                candidate = target.get("candidate") or {}
                original(candidate)
                members = target.get("group") or []
                for member in members:
                    original(member)
                ids = [member.get("candidate_id") for member in members]
                if (target.get("rank") != rank or not ids or len(set(ids)) != len(ids) or
                        candidate["candidate_id"] != min(ids) or target.get("originating_candidate_id") not in ids or
                        any(member["price"] != candidate["price"] for member in members) or not target.get("reason_code")):
                    raise ValueError("target rank/exact-price confluence/reason lineage differs")
                if last is None or sign * (candidate["price"] - last) <= 2:
                    raise ValueError("outward target order/strict buffer differs")
                last = candidate["price"]
    auto = (document.get("autopivot_comparator") or {}).get("frozen") or {}
    boundary(auto, day)
    selected = auto.get("selection") or {}
    if not finite(selected.get("price")) or len(selected.get("inputs", [])) != 5 or not all(finite(v) for v in selected["inputs"]):
        raise ValueError("actual immutable Autopivot prediction/five inputs required")


def check_native(root, stage, record, day, model_primary, created):
    path = pinned(root, record)
    if not path.is_relative_to(stage):
        raise ValueError("native receipt must be retained in the explicit stage")
    native = json.loads(path.read_text())
    if native.get("schema") != "abacus.study29.phase5.native-date/v1" or native.get("session_date") != day:
        raise ValueError("native receipt date/schema differs")
    pinned(root, native["source"], expected_sha=EXPECTED["selector_pine"])
    if native.get("implementation") != "4.0.1" or native.get("control") != "4.0.0":
        raise ValueError("native implementation/control differs")
    expected_settings = {"symbol": "CME_MINI:ESZ2026", "minutes": 5, "chart_type": "standard candles", "session": "ETH", "timezone": "America/New_York", "row_ticks": 16, "value_area_percent": 70, "cutoff": "09:25", "pivot_policy": "P0", "target_policy": "D1", "manual_anchors": []}
    if native.get("settings") != expected_settings:
        raise ValueError("native settings differ from frozen market/selection configuration")
    states = native.get("states") or {}
    if set(states) != {"cutoff", "advanced", "restart"}:
        raise ValueError("cutoff/advance/restart native observations required on every development date")
    chosen = None
    observed_at = None
    for name in ("cutoff", "advanced", "restart"):
        state = states[name]
        boundary(state, day)
        observed = stamp(state["observed_at"])
        if observed > created or observed_at is not None and observed < observed_at:
            raise ValueError("native observation is after reveal-gate chronology")
        observed_at = observed
        if name == "advanced" and stamp(state["latest_observed_bar_close"]) < datetime.combine(date.fromisoformat(day), datetime.min.time(), NY).replace(hour=9, minute=35):
            raise ValueError("native advance must actually reach completed RTH bars")
        selection = state.get("selection") or {}
        pivot = selection.get("pivot") or {}
        if not pivot.get("candidate_id") or not pivot.get("reason_code") or not isinstance(pivot.get("fallback"), bool):
            raise ValueError("actual native pivot identity/reason/fallback required")
        if not finite(pivot.get("price")):
            raise ValueError("actual native primary pivot price required")
        for side in ("bullish", "bearish"):
            branch = selection.get(side) or {}
            if not branch.get("status") or not isinstance(branch.get("targets"), list) or len(branch["targets"]) > 3:
                raise ValueError("actual native bounded branch status/targets required")
            for rank, target in enumerate(branch["targets"], 1):
                if target.get("rank") != rank or not finite(target.get("price")) or not target.get("candidate_id") or not target.get("reason_code"):
                    raise ValueError("native target identity/rank/price/reason required")
        if chosen is not None and selection != chosen:
            raise ValueError("native frozen prices/identities/reasons/fallback changed after cutoff/restart")
        chosen = selection
        evidence = state.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("each native state requires hashed actual browser evidence")
        for item in evidence:
            evidence_path = pinned(root, item)
            if not evidence_path.is_relative_to(stage) or evidence_path.stat().st_size == 0:
                raise ValueError("native evidence must be nonempty retained stage bytes")
    if chosen["pivot"]["price"] != (model_primary["pivot"].get("candidate") or {}).get("price") or chosen["pivot"]["fallback"] != model_primary["pivot"]["fallback"]:
        raise ValueError("native/model primary numeric or fallback parity differs")
    if chosen["pivot"]["reason_code"] != model_primary["pivot"]["reason_code"]:
        raise ValueError("native/model primary reason parity differs")
    for side in ("bullish", "bearish"):
        if [t["price"] for t in chosen[side]["targets"]] != [t["candidate"]["price"] for t in model_primary[side]["targets"]]:
            raise ValueError("native/model target price/order parity differs")
        if [t["reason_code"] for t in chosen[side]["targets"]] != [t["reason_code"] for t in model_primary[side]["targets"]] or chosen[side]["status"] != model_primary[side]["status"]:
            raise ValueError("native/model target reasons/status parity differs")
    return {"receipt": record, "states": list(states), "semantic_state_equal": True, "numeric_model_parity": True}


def validate_gate(root, stage, gate_path, *, now=None):
    root, stage, gate_path = root.resolve(), stage.resolve(), gate_path.resolve()
    if stage.parent != within(root, STAGE_PARENT) or not re.fullmatch(r"phase5_\d{8}T\d{6}Z(?:_[a-z0-9]+)?", stage.name) or not gate_path.is_relative_to(stage):
        raise ValueError("use a unique explicit Phase 5 stage and a gate retained inside it")
    gate = json.loads(gate_path.read_text())
    if gate.get("schema") != "abacus.study29.phase5.reveal-gate/v1":
        raise ValueError("unsupported development reveal-gate schema")
    created = stamp(gate["recorded_at"])
    now = now or datetime.now(timezone.utc)
    if created > now:
        raise ValueError("gate timestamp is in the future")
    freeze_path = pinned(root, gate["protocol_freeze"])
    if not freeze_path.is_relative_to(stage):
        raise ValueError("protocol freeze must be retained in the declared stage")
    freeze = json.loads(freeze_path.read_text())
    frozen_at = stamp(freeze["frozen_at"])
    if frozen_at > created:
        raise ValueError("protocol freeze chronology differs")
    documents = {p["path"]: p for p in freeze["frozen_files"]}
    if len(documents) != 4 or set(documents) != {PHASE + "/" + filename for filename in FROZEN_DOCUMENTS.values()}:
        raise ValueError("freeze must retain exactly four Phase 5 protocol documents")
    for key, filename in FROZEN_DOCUMENTS.items():
        expected_path = PHASE + "/" + filename
        if expected_path not in documents:
            raise ValueError("all four pre-answer protocol documents must be frozen")
        pinned(root, gate[key], expected_path=expected_path, expected_sha=documents[expected_path]["sha256"])
    settings = json.loads(pinned(root, gate["settings"]).read_text())
    if settings.get("development_dates") != list(DATES) or set(settings.get("configurations", [])) != POLICIES or len(settings["configurations"]) != 6:
        raise ValueError("exact four dates and six predeclared configurations required")
    producer_path = pinned(root, gate["producer_manifest"])
    if not producer_path.is_relative_to(stage):
        raise ValueError("producer manifest must be retained in declared stage")
    producer = json.loads(producer_path.read_text())
    retained = stamp(producer["retained_at"])
    if producer.get("schema") != "abacus.study29.phase5.producer/v1" or producer.get("stage") != str(stage.relative_to(root)) or not frozen_at <= retained <= created:
        raise ValueError("producer identity/retention chronology differs")
    if producer.get("protocol_freeze") != gate["protocol_freeze"]:
        raise ValueError("producer must bind the same frozen protocol")
    roles = {r["role"]: r for r in producer["files"]}
    if len(roles) != len(producer["files"]) or not set(EXPECTED) <= set(roles):
        raise ValueError("producer requires unique frozen implementation roles")
    snapshots = {}
    for role, expected in EXPECTED.items():
        item = roles[role]
        snapshot = (producer_path.parent / item["snapshot_path"]).resolve()
        if not snapshot.is_relative_to(stage):
            raise ValueError("producer snapshot escapes explicit stage")
        pinned(root, {"path": str(snapshot.relative_to(root)), "sha256": item["sha256"]}, expected_sha=expected)
        snapshots[role] = snapshot
    for role in ("phase5_protocol", "phase5_settings", "phase5_inputs", "phase5_decision_rule", "runner", "environment_lock"):
        if role not in roles:
            raise ValueError("complete execution producer roles required")
        item = roles[role]
        snapshot = (producer_path.parent / item["snapshot_path"]).resolve()
        if not snapshot.is_relative_to(stage) or digest(snapshot) != item["sha256"]:
            raise ValueError("execution producer retained bytes differ")
    for role, key in (("phase5_protocol", "protocol"), ("phase5_settings", "settings"), ("phase5_inputs", "input_declaration"), ("phase5_decision_rule", "decision_rule")):
        if roles[role]["path"] != gate[key]["path"] or roles[role]["sha256"] != gate[key]["sha256"]:
            raise ValueError("executed producer protocol/decision bytes differ from frozen gate documents")
    model_dir = snapshots["phase4_model"].parent
    if snapshots["phase3_model"] != model_dir / "phase3_model.py" or snapshots["reference_model"] != model_dir / "reference_model.py" or snapshots["matcher"] != model_dir.parent / "phase3/matching.py":
        raise ValueError("retained model/matcher imports must occupy their actual sibling dependency paths")
    input_path = pinned(root, producer["input_manifest"])
    inputs_manifest = json.loads(input_path.read_text())
    if (inputs_manifest.get("schema") != "abacus.study29.phase5.market-inputs/v1" or
            inputs_manifest.get("stage") != str(stage.relative_to(root)) or not input_path.is_relative_to(stage) or
            inputs_manifest.get("market_configuration") != MARKET or
            not frozen_at <= stamp(inputs_manifest["recorded_at"]) <= retained):
        raise ValueError("market input declaration/configuration/chronology differs")
    market_records = [r for r in inputs_manifest["files"] if r.get("session_date")]
    input_records = {r["session_date"]: r for r in market_records}
    if set(input_records) != set(DATES) or len(market_records) != 4 or len({r["path"] for r in market_records}) != 4:
        raise ValueError("all four unique market input identities required")
    pinned(root, gate["loader_code"], expected_path=LOADER)
    pinned(root, gate["source_selector"], expected_path=PHASE + "/select_sources.py")
    pinned(root, gate["source_role_builder"], expected_path=PHASE + "/build_source_role_ledger.py")
    pinned(root, gate["scoring_orchestrator"], expected_path=PHASE + "/analyze_saved_development.py")
    comparisons = {r["path"]: r for r in gate.get("comparison_files", [])}
    if set(comparisons) != set(COMPARISON_FILES):
        raise ValueError("exact frozen source-role/scoring contracts required")
    for path, expected in COMPARISON_FILES.items():
        pinned(root, comparisons[path], expected_path=path, expected_sha=expected)
    pinned(root, gate["window_adapter"], expected_path=PHASE + "/window_identity.py")
    if gate.get("window_adapter_policy") != "phase5-explicit-window-metadata-v1":
        raise ValueError("pre-answer explicit-window adapter policy required")
    exposure = json.loads(pinned(root, gate["exposure_audit"]).read_text())
    if exposure.get("development_answer_exposure_status") not in ("none_known_before_capture", "already_exposed_recorded"):
        raise ValueError("explicit development exposure metadata required")
    captures = gate.get("captures")
    if not isinstance(captures, list) or len(captures) != 4 or {c.get("session_date") for c in captures} != set(DATES):
        raise ValueError("all four exact development predictions and native checks required")
    records = []
    for capture in sorted(captures, key=lambda r: r["session_date"]):
        day = capture["session_date"]
        market_path = pinned(root, capture["input"])
        if capture["input"].get("path") != input_records[day]["path"] or capture["input"].get("sha256") != input_records[day]["sha256"] or not market_path.is_relative_to(stage):
            raise ValueError("capture market input differs from producer input manifest")
        map_path = pinned(root, capture["prediction"])
        if not map_path.is_relative_to(stage):
            raise ValueError("predictions must remain within explicit stage")
        document = json.loads(map_path.read_text())
        if document.get("schema") != "abacus.study29.phase5.local-development-map/v1" or document.get("session_date") != day or document.get("producer_revision") != producer.get("id"):
            raise ValueError("prediction date/schema/producer identity differs")
        if document.get("complete_expanded_map") is not True or document.get("incomplete_reasons"):
            raise ValueError("producer reports an incomplete expanded prediction map")
        execution = document.get("execution") or {}
        captured = stamp(document["model_pre_reveal_captured_at"])
        if not retained <= stamp(execution["started_at"]) <= captured <= created or stamp(execution["captured_at"]) != captured or execution.get("producer_manifest") != gate["producer_manifest"]:
            raise ValueError("prediction capture/execution chronology differs")
        if captured < datetime.combine(date.fromisoformat(day), datetime.min.time(), NY).replace(hour=9, minute=25):
            raise ValueError("prediction capture cannot precede its actual market cutoff")
        declared_input = document.get("input") or {}
        if declared_input.get("path") != capture["input"]["path"] or declared_input.get("sha256") != capture["input"]["sha256"]:
            raise ValueError("prediction market input provenance differs")
        expanded = document.get("expanded_snapshot") or {}
        if document.get("selector_inputs", {}).get("input_identity") != capture["input"]["sha256"] or any(d.get("input_identity") != capture["input"]["sha256"] for d in expanded.get("distributions", []) if d.get("window") != "explicit_composite_RTH3"):
            raise ValueError("candidate/profile identity must bind the actual market-input hash")
        composite = expanded.get("composite_ledger") or {}
        members = composite.get("members") or []
        if len(members) != 3 or len({m.get("profile_id") for m in members}) != 3 or any(m.get("input_identity") != capture["input"]["sha256"] for m in members):
            raise ValueError("composite must retain three identified market-input member lineages")
        derived = hashlib.sha256(json.dumps([(m["profile_id"], m["input_identity"]) for m in members], sort_keys=True, default=str, allow_nan=False).encode()).hexdigest()
        if any(d.get("input_identity") != derived for d in expanded.get("distributions", []) if d.get("window") == "explicit_composite_RTH3"):
            raise ValueError("composite derived input identity differs from its exact member lineage")
        readiness = check_expanded(document.get("expanded_snapshot") or {}, day)
        check_selections(document, day)
        native = check_native(root, stage, capture["native_verification"], day, document["selections"]["P0-D1"], created)
        records.append({"session_date": day, "prediction": capture["prediction"], "input": capture["input"], "captured_at": captured.isoformat(), **readiness, "native": native})
    return {"status": "passed", "gate": {"path": str(gate_path.relative_to(root)), "sha256": digest(gate_path)}, "recorded_at": created.isoformat(), "checked_at": now.isoformat(), "captures": records, "configurations": sorted(POLICIES), "scope": "Retained bytes and explicit semantic/chronology checks; not independent OCR, native execution or proof of pristine source exposure."}


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
        claims = []
        for field in ("chart_session_date", "inferred_session_date", "session_date", "stated_session_date"):
            raw = source.get(field)
            try:
                claimed = date.fromisoformat(raw).isoformat() if isinstance(raw, str) else None
            except ValueError:
                claimed = None
            if claimed is not None:
                claims.append((field, claimed))
        if any(claimed != day for _, claimed in claims):
            excluded.append({key: source.get(key) for key in
                ("source_id", "post_id", "post_url", "posted_at", "captured_at", "role",
                 "chart_session_date", "inferred_session_date", "session_date", "stated_session_date", "image_index", "local_capture_path", "capture_sha256")})
    if not excluded:
        return observation, []
    ids = {source["source_id"] for source in excluded}
    projected = dict(observation)
    projected["sources"] = [s for s in observation.get("sources", []) if s.get("source_id") not in ids]
    for field in ("markers", "closing_notes"):
        projected[field] = [r for r in observation.get(field, []) if r.get("source_id") not in ids]
    projected["issues"] = [r for r in observation.get("issues", []) if r.get("source_id") not in ids and r.get("source_id") is not None]
    projected["session_notes"] = None
    projected["coverage_basis"] = "Bounded Phase5 projection; known-other-date nested source content and unscoped notes withheld. Original retained by locator/hash."
    projected["phase5_selection_projection"] = {"excluded_source_metadata": excluded,
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
    inventory = {"schema": "abacus.study29.phase5.source-selection/v1",
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
    parser.add_argument("--check-gate", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    stage = (root / args.stage).resolve()
    gate = (root / args.capture_gate).resolve()
    result = validate_gate(root, stage, gate) if args.check_gate else select(root, stage, gate)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
