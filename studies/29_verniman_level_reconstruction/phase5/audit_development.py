#!/usr/bin/env python3
"""Explicit Phase 5 market-coverage and saved native/local parity audits.

Audits do not calculate candidate/selection maps or read answer sources. Raw
coverage consumes only the four producer-bound OHLCV captures. Parity compares
retained local maps with separately recorded native observations; it is not OCR,
an independent Pine interpreter or source-method validation.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, time, timedelta, timezone
import importlib.util
import json
from math import isfinite
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

_SPEC = importlib.util.spec_from_file_location("study29_phase5_audit_runner", Path(__file__).with_name("run_development.py"))
R = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = R
_SPEC.loader.exec_module(R)
NY = ZoneInfo("America/New_York")
NATIVE_SETTINGS = {"symbol": "CME_MINI:ESZ2026", "minutes": 5, "chart_type": "standard candles",
                   "session": "ETH", "timezone": "America/New_York", "row_ticks": 16,
                   "value_area_percent": 70, "cutoff": "09:25", "pivot_policy": "P0",
                   "target_policy": "D1", "manual_anchors": []}


def at(day, hour, minute=0):
    return datetime.combine(day, time(hour, minute), NY)


def prior_weekday(day):
    return day - timedelta(days=3 if day.weekday() == 0 else 1)


def required_windows(day_text):
    if day_text not in R.DATES:
        raise ValueError("only the four declared development sessions may be audited")
    day = date.fromisoformat(day_text)
    prior = prior_weekday(day)
    current_sunday = day - timedelta(days=day.weekday() + 1)
    previous_sunday = current_sunday - timedelta(days=7)
    windows = [("prior_full", at(prior - timedelta(days=1), 18), at(prior, 17), False),
               ("completed_RTH", at(prior, 9, 30), at(prior, 16), False),
               ("overnight_prefix", at(day - timedelta(days=1), 18), at(day, 9, 25), False),
               ("current_week_prefix", at(current_sunday, 18), at(day, 9, 25), True),
               ("previous_completed_week", at(previous_sunday, 18), at(previous_sunday + timedelta(days=5), 17), True)]
    cursor, members = day, []
    for _ in range(3):
        cursor = prior_weekday(cursor)
        members.insert(0, cursor)
    windows.extend(("composite_member_" + member.isoformat(), at(member, 9, 30), at(member, 16), False) for member in members)
    return windows


def expected_opens(start, end, maintenance_excluded):
    result = set()
    cursor = start
    while cursor < end:
        if not maintenance_excluded or cursor.hour != 17:
            result.add(int(cursor.timestamp()))
        cursor += timedelta(minutes=5)
    return result


def audit_csv(path, day):
    """Fixed-clock completeness only; no volume-profile/selection calculations."""
    if day not in R.DATES:
        raise ValueError("only exact development dates are permitted")
    cutoff = at(date.fromisoformat(day), 9, 25)
    eligible, invalid, excluded = [], [], 0
    exported, first, last = 0, None, None
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        names = {name.lower(): name for name in reader.fieldnames or ()}
        if not {"time", "open", "high", "low", "close", "volume"} <= names.keys():
            raise ValueError("native timestamp and OHLCV columns required")
        for row in reader:
            text = row[names["time"]]
            opened = datetime.fromtimestamp(int(text), timezone.utc) if text.lstrip("-").isdigit() else R.aware(text)
            opened = opened.astimezone(NY)
            if opened.date() > date.fromisoformat(day):
                raise ValueError("capture contains market dates after the authorized session")
            if opened.second or opened.microsecond or opened.minute % 5:
                raise ValueError("bar opens must align to the fixed five-minute grid")
            exported += 1
            first = opened if first is None else first
            last = opened
            if opened + timedelta(minutes=5) > cutoff:
                excluded += 1
                continue
            stamp = int(opened.timestamp())
            eligible.append(stamp)
            try:
                opening, high, low, close, volume = (float(row[names[key]]) for key in ("open", "high", "low", "close", "volume"))
                valid = (all(isfinite(v) for v in (opening, high, low, close, volume)) and
                         volume >= 0 and low <= min(opening, close) and high >= max(opening, close))
            except (ValueError, TypeError):
                valid = False
            if not valid:
                invalid.append(stamp)
    duplicates = len(eligible) - len(set(eligible))
    increasing = all(a < b for a, b in zip(eligible, eligible[1:]))
    seen, bad = set(eligible), set(invalid)
    records = []
    for name, start, end, maintenance in required_windows(day):
        wanted = expected_opens(start, end, maintenance)
        missing = sorted(wanted - seen)
        affected = sorted(wanted & bad)
        records.append({"window": name, "start": start.isoformat(), "end": end.isoformat(),
            "expected_bars": len(wanted), "observed_bars": len(wanted & seen),
            "missing_bars": len(missing), "invalid_bars": len(affected),
            "missing_open_examples": [datetime.fromtimestamp(t, NY).isoformat() for t in missing[:16]],
            "invalid_open_examples": [datetime.fromtimestamp(t, NY).isoformat() for t in affected[:16]],
            "ready": not missing and not affected and not duplicates and increasing})
    return {"session_date": day, "status": "complete" if all(x["ready"] for x in records) else "incomplete_or_invalid",
        "exported_rows": exported, "eligible_pre_cutoff_rows": len(eligible), "excluded_after_cutoff_rows": excluded,
        "duplicate_included_timestamps": duplicates, "strictly_increasing_included_timestamps": increasing,
        "first_exported_open": first.isoformat() if first else None,
        "last_exported_open": last.isoformat() if last else None,
        "last_included_open": datetime.fromtimestamp(eligible[-1], NY).isoformat() if eligible else None,
        "last_included_close": datetime.fromtimestamp(eligible[-1] + 300, NY).isoformat() if eligible else None,
        "windows": records}


def coverage(root, input_path, producer_path):
    source, producer, _, _, _ = R.validate_manifests(root, input_path, producer_path)
    records = []
    for item in sorted(source["files"], key=lambda x: x["session_date"]):
        result = audit_csv(root / item["path"], item["session_date"])
        result["input"] = item
        records.append(result)
    return {"schema": "abacus.study29.phase5.input-coverage/v1", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "producer_manifest": {"path": str(producer_path.relative_to(root)), "sha256": R.digest(producer_path)},
        "input_manifest": producer["input_manifest"], "records": records,
        "complete_coverage": len(records) == 4 and all(x["status"] == "complete" for x in records),
        "required_window_records": 32, "ready_window_records": sum(w["ready"] for r in records for w in r["windows"]),
        "scope": "Timestamp/OHLCV integrity and eight fixed-clock windows per date only; no detectors, selections, answer sources or source-method validation."}


def parity_values(native, local):
    """Compare observed P0+D1 semantics; native/model ID namespaces stay separate."""
    day = local.get("session_date")
    if day not in R.DATES or native.get("session_date") != day or native.get("schema") != "abacus.study29.phase5.native-date/v1":
        raise ValueError("native/local explicit development date or receipt schema differs")
    if native.get("implementation") != "4.0.1" or native.get("control") != "4.0.0" or native.get("settings") != NATIVE_SETTINGS:
        raise ValueError("native selector version/settings differ")
    if (native.get("source") or {}).get("sha256") != R.FIXED_HASHES["selector_pine"]:
        raise ValueError("native source is not the frozen selector implementation")
    states = native.get("states") or {}
    if set(states) != {"cutoff", "advanced", "restart"}:
        raise ValueError("all three actual native states required")
    chosen, observed_times = None, []
    cutoff = at(date.fromisoformat(day), 9, 25)
    for name in ("cutoff", "advanced", "restart"):
        state = states[name]
        if R.aware(state["last_included_open"]) != cutoff - timedelta(minutes=5) or R.aware(state["last_included_close"]) != cutoff:
            raise ValueError("native included-bar boundary differs from09:20-09:25")
        observed_times.append(R.aware(state["observed_at"]))
        if name == "advanced" and R.aware(state["latest_observed_bar_close"]) < at(date.fromisoformat(day), 9, 35):
            raise ValueError("native advance did not reach completed RTH")
        selection = state.get("selection") or {}
        if chosen is not None and chosen != selection:
            raise ValueError("native prices/IDs/reasons/fallback/states changed after cutoff/restart")
        chosen = selection
    if observed_times != sorted(observed_times):
        raise ValueError("native state observation chronology differs")
    selection = local.get("selections", {}).get("P0-D1") or {}
    pivot = selection.get("pivot") or {}
    actual_pivot = chosen.get("pivot") or {}
    expected_price = (pivot.get("candidate") or {}).get("price")
    if (actual_pivot.get("price"), actual_pivot.get("reason_code"), actual_pivot.get("fallback")) != (expected_price, pivot.get("reason_code"), pivot.get("fallback")):
        raise ValueError("native/local primary price/reason/fallback differs")
    if not actual_pivot.get("candidate_id"):
        raise ValueError("actual native pivot identity required separately")
    mappings = [{"role": "pivot", "native_candidate_id": actual_pivot["candidate_id"],
                 "model_candidate_id": (pivot.get("candidate") or {}).get("candidate_id"),
                 "coordinate": expected_price, "identity_string_equality_claimed": False}]
    for side in ("bullish", "bearish"):
        expected = selection.get(side) or {}
        actual = chosen.get(side) or {}
        targets = actual.get("targets")
        if actual.get("status") != expected.get("status") or not isinstance(targets, list) or len(targets) > 3:
            raise ValueError("native/local branch status or cap differs")
        recorded = [(t.get("rank"), t.get("price"), t.get("reason_code")) for t in targets]
        wanted = [(t["rank"], t["candidate"]["price"], t["reason_code"]) for t in expected.get("targets", [])]
        if recorded != wanted:
            raise ValueError("native/local target price/order/reason differs")
        for actual_target, model_target in zip(targets, expected.get("targets", [])):
            if not actual_target.get("candidate_id"):
                raise ValueError("actual native target identity required separately")
            mappings.append({"role": side, "rank": model_target["rank"],
                "native_candidate_id": actual_target["candidate_id"],
                "model_candidate_id": model_target["candidate"]["candidate_id"],
                "coordinate": model_target["candidate"]["price"], "identity_string_equality_claimed": False})
    return {"session_date": day, "same_frozen_native_state_after_advance_and_restart": True,
            "P0_D1_numeric_reason_fallback_and_branch_status_parity": True,
            "native_model_identity_namespaces": mappings,
            "limitations": "ID mappings are observed separate identifiers at corresponding selected coordinates/reasons. No string equality, independent OCR or source-method agreement is inferred."}


def native_parity(root, manifest_path):
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema") != "abacus.study29.phase5.native-parity-inputs/v1":
        raise ValueError("explicit native-parity audit input manifest required")
    stage = R.stage_path(root, manifest["stage"])
    if not manifest_path.is_relative_to(stage):
        raise ValueError("parity manifest must be retained in declared stage")
    input_path = R.pin(root, manifest["input_manifest"])
    producer_path = R.pin(root, manifest["producer_manifest"])
    R.validate_manifests(root, input_path, producer_path)
    batch_path = R.pin(root, manifest["prediction_batch"])
    batch = json.loads(batch_path.read_text())
    records = batch.get("records", [])
    locals_by_date = {r.get("session_date"): r for r in records}
    native_records = manifest.get("native_receipts", [])
    native_by_date = {r.get("session_date"): r for r in native_records}
    if set(locals_by_date) != set(R.DATES) or len(records) != 4 or set(native_by_date) != set(R.DATES) or len(native_records) != 4:
        raise ValueError("all four exact local/native observations required")
    checked_at = datetime.now(timezone.utc)
    outcomes = []
    for day in R.DATES:
        entry = locals_by_date[day]
        if entry.get("complete_expanded_map") is not True:
            raise ValueError("complete expanded local map required for parity")
        local_path = R.pin(root, entry["map_artifact"])
        native_path = R.pin(root, native_by_date[day])
        if not local_path.is_relative_to(stage) or not native_path.is_relative_to(stage):
            raise ValueError("native/local artifacts must be inside declared stage")
        local, native = json.loads(local_path.read_text()), json.loads(native_path.read_text())
        if local.get("producer_revision") != json.loads(producer_path.read_text())["id"] or local["execution"]["producer_manifest"] != manifest["producer_manifest"]:
            raise ValueError("local map producer provenance differs")
        R.pin(root, native["source"])
        for state in native["states"].values():
            if R.aware(state["observed_at"]) > checked_at:
                raise ValueError("native observation time is in the future")
            evidence = state.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                raise ValueError("hashed native browser evidence required for every state")
            for item in evidence:
                path = R.pin(root, item)
                if not path.is_relative_to(stage) or path.stat().st_size == 0:
                    raise ValueError("nonempty native evidence inside stage required")
        result = parity_values(native, local)
        result.update({"prediction": entry["map_artifact"], "native_receipt": native_by_date[day]})
        outcomes.append(result)
    return {"schema": "abacus.study29.phase5.native-parity-audit/v1", "checked_at": checked_at.isoformat(),
        "input_manifest": {"path": str(manifest_path.relative_to(root)), "sha256": R.digest(manifest_path)},
        "status": "passed", "records": outcomes, "source_method_agreement_established": False,
        "native_execution_established_by_this_audit": False,
        "scope": "Saved actual observation receipt parity and byte integrity; actual native evidence retains its own execution scope."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=R.ROOT)
    parser.add_argument("--mode", choices=("coverage", "native-parity"), required=True)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--producer-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    def resolved(path):
        return path.resolve() if path.is_absolute() else (root / path).resolve()
    inputs, output = resolved(args.input_manifest), resolved(args.output)
    if output.exists() or not output.parent.is_relative_to(root / "work/29_verniman_level_reconstruction") or not output.parent.name.startswith("phase5_"):
        raise ValueError("fresh receipt in explicit Phase5 stage required")
    if args.mode == "coverage":
        if args.producer_manifest is None:
            parser.error("coverage requires --producer-manifest")
        result = coverage(root, inputs, resolved(args.producer_manifest))
    else:
        result = native_parity(root, inputs)
    result["audit_code"] = {"path": str(Path(__file__).resolve().relative_to(root)), "sha256": R.digest(__file__)}
    R.write_new(output, result)
    print(json.dumps({"output": str(output.relative_to(root)), "mode": args.mode,
                      "status": result.get("status", "complete" if result.get("complete_coverage") else "incomplete")}, indent=2))


if __name__ == "__main__":
    main()
