#!/usr/bin/env python3
"""Four-date Phase 5 predictions from explicit retained market inputs only.

No answer loader, source discovery or scoring is imported. Candidate/selection
models execute from a byte-checked producer snapshot, including the immutable
Phase 4 Autopivot identity. An incomplete map is retained but cannot pass reveal.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
from math import isfinite
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
STUDY = "studies/29_verniman_level_reconstruction"
PHASE = STUDY + "/phase5"
DATES = ("2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20")
CONFIGURATIONS = tuple(p + "-" + t for p in ("P0", "B0", "B1") for t in ("D0", "D1"))
WINDOWS = frozenset(("completed_RTH", "overnight_prefix", "current_week_prefix",
                     "previous_completed_week", "explicit_composite_RTH3"))
MARKET = {"symbol": "CME_MINI:ESZ2026", "contract": "ESZ2026", "feed": "CME GLOBEX",
          "adjustment": "individual_contract_unadjusted", "minutes": 5,
          "session": "ETH", "timezone": "America/New_York", "tick_size": .25,
          "row_ticks": 16, "value_area_percent": 70, "grid_origin": 0,
          "cutoff_hour": 9, "cutoff_minute": 25, "manual_anchors": []}
FIXED_HASHES = {
    "phase4_model": "bec68316b9028cff8d43e6e9fbcef86c4e46a5be792b9df325d42753a85547c5",
    "phase3_model": "e54ba9950618e99dc1fe57ac5fab19cf43e990099b98df8b25f506bd8c92f48b",
    "reference_model": "712016db99bc62b35c787b9269825529221636545d903d814993284fbd769bbd",
    "matcher": "b595fbca570df868888dd58c8fe341ee341b69770d902319ba25ac8fd1fd90a6",
    "candidate_pine": "034c3731f2ada4620aac9a80ca20261d0a06376bee044fa30e95529ad9e1954c",
    "selector_pine": "1145834bfb240029f07342e52f98d805771ca4f2a39a646c19e80d3846794924",
    "phase3_settings": "c0297d86f2a6dce33b6888a174c31d6390477dd0e12d78a46832173e0f17653a",
    "phase4_settings": "5a1cc36f7c0a2b16ee82ab9eccd285c9a897d933d2b0ad1e02a2c026e5bb5f1a",
    "autopivot_pine": "228ce4f4cc938cfb967eed4b20df8db0711755fb2fd8d4ae2cc9be8632dd3145",
    "autopivot_model": "1fc67f44ea3dc6bc374a3bfcf526bfea419af8316f7eaf82cc179d01c3e466f4",
}
BASELINE_FIELDS = ("previous_full_high", "previous_full_low", "current_week_vah", "current_week_poc", "current_week_val",
                   "previous_week_vah", "previous_week_poc", "previous_week_val", "completed_rth_vah", "completed_rth_poc",
                   "completed_rth_val", "overnight_vah", "overnight_poc", "overnight_val", "overnight_high", "overnight_low",
                   "completed_rth_high", "completed_rth_low", "rth_last_traded_close")
CAPTURE_ROOT = "work/29_verniman_level_reconstruction/phase4_20261031T010249Z/autopivot-current-reconciliation/"
ROLE_PATHS = {
    "runner": PHASE + "/run_development.py",
    "phase4_model": STUDY + "/src/phase4_model.py",
    "phase3_model": STUDY + "/src/phase3_model.py",
    "reference_model": STUDY + "/src/reference_model.py",
    "matcher": STUDY + "/phase3/matching.py",
    "candidate_pine": STUDY + "/indicator/verniman_levels_phase3_3_0_2.pine",
    "selector_pine": STUDY + "/indicator/verniman_levels_phase4.pine",
    "phase3_settings": STUDY + "/phase3/settings.json",
    "phase4_settings": STUDY + "/phase4/settings.json",
    "autopivot_pine": CAPTURE_ROOT + STUDY + "/indicator/verniman_pivot_levels.pine",
    "autopivot_model": CAPTURE_ROOT + STUDY + "/src/pivot_model.py",
    "phase5_protocol": PHASE + "/protocol.md", "phase5_settings": PHASE + "/settings.json",
    "phase5_inputs": PHASE + "/input-declaration.json", "phase5_decision_rule": PHASE + "/decision-rule.md",
    "environment_lock": "uv.lock",
}


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def plain(value):
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(plain(value), handle, indent=2, allow_nan=False)
        handle.write("\n")


def aware(text):
    result = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timezone-aware retained time required")
    return result


def within(root, relative):
    if Path(relative).is_absolute():
        raise ValueError("relative workspace path required")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("artifact path escapes workspace")
    return path


def pin(root, record):
    path = within(root, record["path"])
    if not path.is_file() or digest(path) != record.get("sha256"):
        raise ValueError("missing or changed pinned bytes: " + record["path"])
    return path


def stage_path(root, relative):
    stage = within(root, relative)
    if stage.parent != root / "work/29_verniman_level_reconstruction" or not stage.name.startswith("phase5_"):
        raise ValueError("explicit new Phase5 stage required")
    return stage


def validate_input_manifest(root, input_path):
    source = json.loads(input_path.read_text())
    if source.get("schema") != "abacus.study29.phase5.market-inputs/v1":
        raise ValueError("unsupported development market-input schema")
    stage = stage_path(root, source["stage"])
    if not input_path.is_relative_to(stage):
        raise ValueError("input declaration must be retained inside Phase5 stage")
    for key, value in MARKET.items():
        if source.get("market_configuration", {}).get(key) != value:
            raise ValueError("noncontrol market configuration: " + key)
    files = source.get("files", [])
    if (len(files) != 4 or len({f.get("session_date") for f in files}) != 4 or
            {f.get("session_date") for f in files} != set(DATES)):
        raise ValueError("exact four unique development-date CSV pins required")
    if len({f.get("path") for f in files}) != 4:
        raise ValueError("each development date needs its own declared capture")
    for item in files:
        path = pin(root, item)
        if path.suffix.lower() != ".csv" or not path.is_relative_to(stage):
            raise ValueError("market input must be a declared CSV inside Phase5 stage")
    aware(source["recorded_at"])
    return source, stage


def validate_manifests(root, input_path, producer_path, *, now=None):
    """Validate all byte identities before any model import or market parsing."""
    root, input_path, producer_path = root.resolve(), input_path.resolve(), producer_path.resolve()
    source, stage = validate_input_manifest(root, input_path)
    producer = json.loads(producer_path.read_text())
    if producer.get("schema") != "abacus.study29.phase5.producer/v1" or not producer.get("id"):
        raise ValueError("identified Phase5 producer revision required")
    if producer_path.parent != stage or producer.get("stage") != source["stage"]:
        raise ValueError("producer must belong to the same declared stage")
    if pin(root, producer["input_manifest"]) != input_path:
        raise ValueError("producer must pin this exact input manifest")
    freeze_path = pin(root, producer["protocol_freeze"])
    if not freeze_path.is_relative_to(stage):
        raise ValueError("protocol freeze must be in the declared stage")
    freeze = json.loads(freeze_path.read_text())
    frozen = {item["path"]: item["sha256"] for item in freeze["frozen_files"]}
    required_docs = {ROLE_PATHS[role] for role in ("phase5_protocol", "phase5_settings", "phase5_inputs", "phase5_decision_rule")}
    if set(frozen) != required_docs:
        raise ValueError("freeze must contain the four exact Phase5 documents")
    for item in freeze["frozen_files"]:
        pin(root, item)
    current = now or datetime.now(timezone.utc)
    retained = aware(producer["retained_at"])
    if not aware(freeze["frozen_at"]) <= aware(source["recorded_at"]) <= retained <= current:
        raise ValueError("protocol/input/producer chronology invalid")
    records = producer.get("files", [])
    by_role = {item.get("role"): item for item in records}
    if len(by_role) != len(records) or set(by_role) != set(ROLE_PATHS):
        raise ValueError("producer must uniquely inventory every required source role")
    snapshots = {}
    for role, item in by_role.items():
        original = pin(root, item)
        if item["path"] != ROLE_PATHS[role]:
            raise ValueError("unexpected source path for role: " + role)
        expected = FIXED_HASHES.get(role)
        if expected is not None and item["sha256"] != expected:
            raise ValueError("fixed Phase4 identity differs: " + role)
        if role == "runner" and item["sha256"] != digest(__file__):
            raise ValueError("executed runner differs from its retained producer")
        if role.startswith("phase5_") and item["sha256"] != frozen[item["path"]]:
            raise ValueError("Phase5 producer differs from protocol freeze")
        snapshot = within(stage, item["snapshot_path"])
        if not snapshot.is_file() or digest(snapshot) != item["sha256"]:
            raise ValueError("retained producer snapshot differs: " + role)
        snapshots[role] = snapshot
    # The frozen model imports these files relative to its own path. A digest
    # inventory at unrelated locations would not identify those actual imports.
    model_dir = snapshots["phase4_model"].parent
    if snapshots["phase3_model"] != model_dir / "phase3_model.py" or snapshots["reference_model"] != model_dir / "reference_model.py":
        raise ValueError("retained model dependency tree must preserve sibling imports")
    if snapshots["matcher"] != model_dir.parent / "phase3/matching.py":
        raise ValueError("retained matcher must occupy the model's actual dependency path")
    settings = json.loads(snapshots["phase5_settings"].read_text())
    if settings.get("development_dates") != list(DATES):
        raise ValueError("frozen settings must retain the exact scheduled dates")
    configurations = settings.get("configurations", [])
    if len(configurations) != 6 or set(configurations) != set(CONFIGURATIONS):
        raise ValueError("only the six predeclared existing policy combinations are allowed")
    return source, producer, stage, snapshots, settings


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_bars(path, day, model):
    if day not in DATES:
        raise ValueError("not an authorized development date")
    cutoff = model.P3.BASE.local(date.fromisoformat(day), 9, 25)
    bars, excluded = [], 0
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        columns = {key.lower(): key for key in reader.fieldnames or ()}
        if not {"time", "open", "high", "low", "close", "volume"} <= columns.keys():
            raise ValueError("identified native OHLCV columns required")
        for row in reader:
            text = row[columns["time"]]
            opened = datetime.fromtimestamp(int(text), timezone.utc) if text.lstrip("-").isdigit() else aware(text)
            opened = opened.astimezone(model.P3.BASE.NY)
            if opened.second or opened.microsecond or opened.minute % 5:
                raise ValueError("five-minute aligned bar opens required")
            if opened.date() > date.fromisoformat(day):
                raise ValueError("capture includes market dates after the authorized session")
            closed = opened + timedelta(minutes=5)
            if closed > cutoff:
                excluded += 1
                continue  # No future OHLCV/indicator value can enter this map.
            opening, high, low, close = (float(row[columns[k]]) for k in ("open", "high", "low", "close"))
            if not all(isfinite(v) for v in (opening, high, low, close)) or low > min(opening, close) or high < max(opening, close):
                raise ValueError("invalid finite OHLC interval")
            volume_text = row[columns["volume"]].strip()
            volume = float(volume_text) if volume_text else None
            if volume is not None and not isfinite(volume):
                raise ValueError("nonfinite volume")
            bars.append(model.P3.BASE.Bar(opened, closed, high, low, close, volume, True))
    if any(a.opened >= b.opened for a, b in zip(bars, bars[1:])):
        raise ValueError("strictly increasing unique included timestamps required")
    return bars, {"included_rows": len(bars), "excluded_after_cutoff_rows": excluded,
                  "ignored_columns": sorted(key for key in columns if key not in {"time", "open", "high", "low", "close", "volume"}),
                  "last_included_open": bars[-1].opened if bars else None,
                  "last_included_close": bars[-1].closed if bars else None,
                  "policy": "Only explicit OHLCV consumed; derived native series ignored; close<=09:25."}


def compact_selection(selection):
    def branch(value):
        return {"prices": [t.candidate.price for t in value.targets],
                "candidate_ids": [t.candidate.candidate_id for t in value.targets],
                "reason_codes": [t.reason_code for t in value.targets], "status": value.status}
    return {"pivot": {"price": selection.pivot.price,
                       "candidate_id": selection.pivot.candidate.candidate_id if selection.pivot.candidate else None,
                       "reason_code": selection.pivot.reason_code, "fallback": selection.pivot.fallback,
                       "status": selection.pivot.status},
            "bullish": branch(selection.bullish), "bearish": branch(selection.bearish)}


def complete_map_reasons(expanded, inputs, selections):
    reasons = []
    if len(expanded.baseline.values) != 19 or any(v is None or not isfinite(v) for v in expanded.baseline.values):
        reasons.append("original19_not_all_finite")
    if len(expanded.distributions) != 5 or {d.window for d in expanded.distributions} != WINDOWS:
        reasons.append("five_profile_inventory_missing")
    if len(expanded.candidate_ledgers) != 5 or any(l.get("status") != "ready" for l in expanded.candidate_ledgers):
        reasons.append("required_profile_not_ready")
    if inputs.reasons():
        reasons.extend(inputs.reasons())
    if set(selections) != set(CONFIGURATIONS):
        reasons.append("six_configuration_batch_missing")
    return list(dict.fromkeys(reasons))


def reconstruct(root, item, model, comparator_model, producer, producer_pin, configurations, started_at):
    day = item["session_date"]
    bars, bar_audit = read_bars(root / item["path"], day, model)
    engine = model.Phase4Engine(contract="ESZ2026", feed="CME GLOBEX", adjustment="individual_contract_unadjusted",
        tick_size=.25, row_size=4, va_pct=70, input_identity=item["sha256"],
        code_identity=FIXED_HASHES["phase3_model"], settings_identity=FIXED_HASHES["phase3_settings"], minutes=5)
    engine.feed(bars)
    expanded = engine.expanded_snapshot
    if expanded is None or expanded.baseline.trading_date.isoformat() != day:
        raise ValueError("No exact development-date expanded snapshot: " + engine.snapshot_status)
    terminal = next((bar for bar in reversed(bars) if bar.closed == expanded.baseline.cutoff), None)
    inputs = model.inputs_from_phase3(expanded, terminal.close if terminal else None)
    selections = {key: model.select_map(inputs, pivot_policy=key.split("-")[0], target_policy=key.split("-")[1]) for key in configurations}
    comparator = comparator_model.PivotEngine()
    comparator.feed(bars)
    frozen = comparator.frozen
    current = frozen.selection if frozen else None
    alternate = comparator_model.alternate_reference(current.price, current.reason, *current.inputs[:3], current.inputs[4]) if current else (None, "na")
    readiness = [{"window": d.window, "profile_id": d.profile_id, "status": ledger["status"],
                  "reasons": ledger["distribution"]["reasons"], "included_sessions": d.included_sessions,
                  "expected_sessions": d.expected_sessions, "row_count": len(d.masses),
                  "last_included_open": d.last_bar_open, "last_included_close": d.last_bar_close,
                  "counts": ledger.get("counts"), "presentation": ledger.get("presentation")}
                 for d, ledger in zip(expanded.distributions, expanded.candidate_ledgers)]
    missing = complete_map_reasons(expanded, inputs, selections)
    if frozen is None or current is None or current.price is None:
        missing.append("immutable_Autopivot_prediction_unavailable")
    captured = datetime.now(timezone.utc)
    return {"schema": "abacus.study29.phase5.local-development-map/v1", "session_date": day,
        "execution": {"kind": "independent_local_specification_model_not_Pine", "started_at": started_at,
                      "captured_at": captured, "producer_manifest": producer_pin},
        "model_pre_reveal_captured_at": captured, "producer_revision": producer["id"], "input": item,
        "candidate_control": "phase3-3.0.0", "candidate_implementation": "3.0.2",
        "selector_policy": "phase4-4.0.0", "selector_implementation": "4.0.1",
        "configurations": configurations, "market_configuration": MARKET, "bar_audit": bar_audit,
        "cutoff_close": inputs.cutoff_close, "original_baseline_fields": dict(zip(BASELINE_FIELDS, expanded.baseline.values)),
        "expanded_snapshot": expanded, "selector_inputs": inputs, "profile_readiness": readiness,
        "selections": selections,
        "autopivot_comparator": {"execution": "immutable_Phase4_capture_translated_model_not_fresh_Pine",
            "pine_sha256": FIXED_HASHES["autopivot_pine"], "model_sha256": FIXED_HASHES["autopivot_model"],
            "frozen": frozen, "alternate_model_only": {"price": alternate[0], "origin": alternate[1], "is_target": False},
            "P0_same_price": current is not None and selections["P0-D1"].pivot.price == current.price,
            "input_policy_difference": "P0 strict expected prior-weekday RTH; comparator latest actually observed RTH. Inspect source dates/readiness before selector attribution."},
        "complete_expanded_map": not missing, "incomplete_reasons": missing,
        "source_access": "closed_no_development_answers_read", "development_answers_opened": False,
        "selection_fitted": False, "hidden_test_execution": False,
        "limits": "Local same-feed reconstruction; native execution and source-method agreement require separate evidence. Missing PBT anchors remain unavailable."}


def run(root, input_path, producer_path, output):
    source, producer, stage, snapshots, settings = validate_manifests(root, input_path, producer_path)
    if output.parent != stage or output.exists():
        raise ValueError("one fresh output directory directly inside declared stage required")
    started = datetime.now(timezone.utc)
    producer_pin = {"path": str(producer_path.relative_to(root)), "sha256": digest(producer_path)}
    # These dependencies are loaded from the inventoried retained tree only.
    model = load_module("study29_phase5_retained_phase4_model", snapshots["phase4_model"])
    load_module("reference_model", snapshots["reference_model"])
    comparator = load_module("study29_phase5_immutable_autopivot_model", snapshots["autopivot_model"])
    payloads, failures = [], []
    for item in sorted(source["files"], key=lambda p: p["session_date"]):
        try:
            payloads.append(reconstruct(root, item, model, comparator, producer, producer_pin, settings["configurations"], started))
        except (ValueError, ArithmeticError) as exc:
            failures.append({"session_date": item["session_date"], "status": "input_or_snapshot_failure",
                             "reasons": [str(exc)], "map_artifact": None, "complete_expanded_map": False})
    output.mkdir()
    records = []
    for full in payloads:
        path = output / (full["session_date"] + ".json")
        write_new(path, full)
        records.append({"session_date": full["session_date"], "status": "complete_expanded_map" if full["complete_expanded_map"] else "incomplete_expanded_map",
            "map_artifact": {"path": str(path.relative_to(root)), "sha256": digest(path)},
            "complete_expanded_map": full["complete_expanded_map"], "incomplete_reasons": full["incomplete_reasons"],
            "profile_readiness": full["profile_readiness"], "model_pre_reveal_captured_at": full["model_pre_reveal_captured_at"],
            "selection_summaries": {key: compact_selection(value) for key, value in full["selections"].items()}})
    records.extend(failures)
    records.sort(key=lambda p: p["session_date"])
    summary = {"schema": "abacus.study29.phase5.prediction-batch/v1", "recorded_at": datetime.now(timezone.utc),
        "stage": source["stage"], "input_manifest": producer["input_manifest"], "producer_manifest": producer_pin,
        "configurations": settings["configurations"], "records": records,
        "complete_four_session_batch": len(records) == 4 and all(r["complete_expanded_map"] for r in records),
        "reveal_gate_passed": False, "development_answers_opened": False,
        "native_execution_established": False, "source_method_reproduction_established": False}
    write_new(output / "prediction-batch.json", summary)
    write_new(output / "artifact-hashes.json", {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()})
    return {"output": str(output.relative_to(root)), "maps": len(payloads), "failures": len(failures),
            "complete_four_session_batch": summary["complete_four_session_batch"], "development_answers_opened": False}


def freeze_producer(root, input_path, freeze_path, producer_path, producer_id):
    """Retain source bytes before market execution; does not parse CSV content."""
    source, stage = validate_input_manifest(root, input_path)
    if producer_path.parent != stage or producer_path.exists():
        raise ValueError("fresh producer manifest in declared stage required")
    freeze = json.loads(freeze_path.read_text())
    for item in freeze["frozen_files"]:
        pin(root, item)
    snapshot_root = stage / (producer_path.stem + "-files")
    if snapshot_root.exists():
        raise ValueError("refusing to overwrite retained producer source bytes")
    records = []
    # Check all fixed identities before copying even one source.
    for role, relative in ROLE_PATHS.items():
        path = within(root, relative)
        actual = digest(path)
        if role in FIXED_HASHES and actual != FIXED_HASHES[role]:
            raise ValueError("fixed Phase4 identity differs: " + role)
        records.append({"role": role, "path": relative, "sha256": actual,
                        "snapshot_path": str((snapshot_root / relative).relative_to(stage))})
    snapshot_root.mkdir()
    for item in records:
        destination = stage / item["snapshot_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / item["path"], destination)
    record = {"schema": "abacus.study29.phase5.producer/v1", "id": producer_id,
        "retained_at": datetime.now(timezone.utc).isoformat(), "stage": source["stage"],
        "input_manifest": {"path": str(input_path.relative_to(root)), "sha256": digest(input_path)},
        "protocol_freeze": {"path": str(freeze_path.relative_to(root)), "sha256": digest(freeze_path)}, "files": records}
    write_new(producer_path, record)
    validate_manifests(root, input_path, producer_path)
    return {"producer": str(producer_path.relative_to(root)), "sha256": digest(producer_path),
            "retained_sources": len(records), "market_rows_parsed": 0, "development_answers_opened": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--producer-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--freeze-producer", action="store_true")
    parser.add_argument("--protocol-freeze", type=Path)
    parser.add_argument("--producer-id", default="phase5-producer-1")
    args = parser.parse_args()
    root = args.root.resolve()
    def resolved(value):
        return value.resolve() if value.is_absolute() else (root / value).resolve()
    input_path, producer_path = resolved(args.input_manifest), resolved(args.producer_manifest)
    if args.freeze_producer:
        if args.protocol_freeze is None:
            parser.error("--freeze-producer requires --protocol-freeze")
        result = freeze_producer(root, input_path, resolved(args.protocol_freeze), producer_path, args.producer_id)
    else:
        if args.output is None:
            parser.error("prediction execution requires --output")
        result = run(root, input_path, producer_path, resolved(args.output))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
