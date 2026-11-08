#!/usr/bin/env python3
"""Check a completed prospective schedule without reading source answer content.

The audit uses explicit saved receipts and operator access attestations. Hashes
establish identity, not an independently certified creation time or enforced
blinding. No source discovery, market calculation or selection is performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
TERMINAL = {"timely", "late", "reconstructed", "missing", "input_unavailable", "exposed", "unsupported"}
HAS_MAP = {"timely", "late", "reconstructed", "exposed", "unsupported"}
ACCESS_KINDS = {"answer_access", "answer_disclosure"}


def aware(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timezone-aware audit clock required")
    return result.astimezone(timezone.utc)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin(root, path):
    root = Path(root).resolve()
    path = Path(path).resolve()
    return {"path": str(path.relative_to(root)), "sha256": digest(path)}


def pinned(root, value):
    path = (root / value["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file() or digest(path) != value.get("sha256"):
        raise ValueError("changed or out-of-root explicit pin: " + str(value.get("path")))
    return path


def load(path):
    return json.loads(Path(path).read_text())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def validate_access_log(log, dates, end_at):
    if log.get("schema") != "abacus.study29.phase6.access-log/v1":
        raise ValueError("explicit Phase6 access log required")
    if log.get("complete_to_best_knowledge") is not True or aware(log["closed_through"]) < end_at:
        raise ValueError("access audit must explicitly cover the complete scheduled period")
    actors = {row["actor_id"]: row for row in log.get("actors", [])}
    if not actors or len(actors) != len(log.get("actors", [])):
        raise ValueError("unique actual actor identities required")
    if any(not actor or actor.lower() in {"unassigned", "pending", "placeholder"} for actor in actors):
        raise ValueError("actual actor identities cannot be placeholders")
    predictions = {key for key, row in actors.items() if row["role"] == "prediction"}
    if not predictions or any(row["role"] not in {"prediction", "collector", "scorer"} for row in actors.values()):
        raise ValueError("prediction and collector/scorer roles must be explicit")
    events = {}
    for event in log.get("events", []):
        identifier = event["event_id"]
        if not identifier or identifier in events or event.get("actor_id") not in actors:
            raise ValueError("duplicate access event or unknown actor")
        if event.get("session_date") not in dates or event.get("kind") not in ACCESS_KINDS:
            raise ValueError("access event outside declared dates or kinds")
        if aware(event["occurred_at"]) > aware(log["closed_through"]):
            raise ValueError("access event is later than audit closure")
        if event["kind"] == "answer_disclosure" and event.get("recipient_actor_id") not in actors:
            raise ValueError("answer disclosure requires its actual recipient")
        events[identifier] = event
    return actors, predictions, events


def _affected(event, predictions):
    if event["kind"] == "answer_access" and event["actor_id"] in predictions:
        return event["actor_id"]
    if event["kind"] == "answer_disclosure" and event.get("recipient_actor_id") in predictions:
        return event["recipient_actor_id"]
    return None


def check_gate(root, freeze_path, ledger_path, access_path, *, now=None, capture_validator=None):
    root = Path(root).resolve()
    freeze_path, ledger_path, access_path = [Path(p).resolve() for p in (freeze_path, ledger_path, access_path)]
    if any(not p.is_relative_to(root) for p in (freeze_path, ledger_path, access_path)):
        raise ValueError("gate inputs must be explicit retained workspace files")
    now = datetime.now(timezone.utc) if now is None else aware(now) if isinstance(now, str) else now.astimezone(timezone.utc)
    freeze, ledger, log = load(freeze_path), load(ledger_path), load(access_path)
    if freeze.get("schema") != "abacus.study29.phase6.freeze/v1":
        raise ValueError("frozen Phase6 protocol identity required")
    dates = freeze["scheduled_dates"]
    if len(dates) != 20 or len(set(dates)) != 20 or dates != sorted(dates):
        raise ValueError("exact twenty-date schedule required")
    end_at, frozen_at = aware(freeze["period_end_at"]), aware(freeze["frozen_at"])
    if now < end_at or frozen_at >= end_at:
        raise ValueError("complete scheduled period has not ended")
    for row in freeze.get("files", []):
        pinned(root, row)
    for row in freeze.get("producer_files", []):
        snapshot = {"path": row["snapshot_path"], "sha256": row["sha256"]}
        pinned(root, snapshot)
    expected_freeze = pin(root, freeze_path)
    if ledger.get("schema") != "abacus.study29.phase6.session-ledger/v1" or ledger.get("protocol_freeze") != expected_freeze:
        raise ValueError("session ledger must bind this exact protocol freeze")
    rows = ledger.get("sessions", [])
    if len(rows) != 20 or {r.get("session_date") for r in rows} != set(dates):
        raise ValueError("every scheduled session must remain exactly once")
    if any(r.get("status") not in TERMINAL for r in rows):
        raise ValueError("incomplete batch: all scheduled sessions need explicit final statuses")
    actors, prediction_actors, events = validate_access_log(log, dates, end_at)
    if aware(log["closed_through"]) > now:
        raise ValueError("audit closure cannot claim a future time")
    if now - aware(log["closed_through"]) > timedelta(minutes=5):
        raise ValueError("final access audit must be refreshed within five minutes before gate creation")
    exposure = [event for event in events.values() if _affected(event, prediction_actors) is not None and aware(event["occurred_at"]) <= now]
    if capture_validator is None:
        capture = module("study29_phase6_gate_capture", PHASE / "capture.py")
        capture_validator = capture.verify_capture
    captures, missing, eligible = [], [], []
    for row in sorted(rows, key=lambda r: r["session_date"]):
        day = row["session_date"]
        finalized = aware(row["finalized_at"])
        if finalized > now or finalized < frozen_at:
            raise ValueError("invalid session finalization chronology")
        if not row.get("receipt"):
            raise ValueError("even an explicit failure needs its retained immutable capture/status receipt")
        receipt_path = pinned(root, row["receipt"])
        receipt = load(receipt_path)
        verified = capture_validator(root, freeze_path, receipt_path, now=now)
        if receipt.get("session_date") != day:
            raise ValueError("ledger day differs from the actual saved receipt")
        if receipt.get("protocol_freeze") != expected_freeze:
            raise ValueError("capture was not bound to the exact frozen protocol")
        operator = receipt.get("operator_id")
        if operator not in prediction_actors:
            raise ValueError("prediction receipt requires its actual logged prediction operator")
        old_log = load(pinned(root, receipt["source_access_log"]))
        old_events = old_log.get("events", [])
        if any(events.get(event.get("event_id")) != event for event in old_events):
            raise ValueError("access history was removed or rewritten after a capture")
        old_actors = {r["actor_id"]: r for r in old_log.get("actors", [])}
        if any(actors.get(key) != value for key, value in old_actors.items()):
            raise ValueError("actor identity/role changed after a capture")
        completed = aware(receipt["captured_at"])
        if finalized < completed:
            raise ValueError("session cannot be finalized before its saved receipt completed")
        earlier = [event for event in exposure if _affected(event, prediction_actors) == operator and aware(event["occurred_at"]) <= completed]
        effective = "exposed" if earlier and receipt.get("prediction") is not None else receipt.get("status")
        if row["status"] != effective:
            raise ValueError("ledger must retain the effective exposure/timing classification without rewriting its original receipt")
        complete = receipt.get("complete_expanded_map") is True
        if row["status"] in HAS_MAP:
            if not receipt.get("prediction"):
                raise ValueError("map status cannot be a failure placeholder")
            pinned(root, receipt["prediction"])
        if row["status"] == "timely" and not complete:
            raise ValueError("timely prediction needs a complete expanded map")
        if row["status"] in {"missing", "input_unavailable"}:
            if complete or receipt.get("prediction") is not None or not receipt.get("incomplete_reasons"):
                raise ValueError("missing/input failure must not masquerade as a complete map")
            missing.append(day)
        if row["status"] == "timely" and complete and not earlier:
            eligible.append(day)
        captures.append({"session_date": day, "status": row["status"], "receipt": row["receipt"],
                         "original_receipt_status": receipt.get("status"),
                         "prediction": receipt.get("prediction"), "complete_expanded_map": complete,
                         "operator_id": operator, "captured_at": receipt["captured_at"],
                         "capture_verification": verified, "earlier_prediction_operator_answer_events": [e["event_id"] for e in earlier]})
    return {"schema": "abacus.study29.phase6.reveal-gate/v1", "recorded_at": now.isoformat(),
            "status": "passed", "reveal_allowed": True, "protocol_freeze": expected_freeze,
            "session_ledger": pin(root, ledger_path), "access_log": pin(root, access_path),
            "period_end_at": freeze["period_end_at"], "scheduled_dates": dates, "captures": captures,
            "timely_blinded_capture_dates": eligible, "scheduled_count": 20,
            "complete_timely_count": len(eligible), "missing_or_input_unavailable_dates": missing,
            "pre_batch_prediction_operator_answer_events": [e["event_id"] for e in exposure],
            "pre_reveal_prediction_operator_answer_events": [e["event_id"] for e in exposure],
            "batch_blinding_breach": bool(exposure),
            "evaluation_status": "complete_capture_batch" if len(eligible) == 20 and not exposure else "incomplete_or_exposed_evaluation_retained",
            "formal_prospective_estimation_allowed": not exposure,
            "source_content_read_by_gate": False, "selection_recomputed": False,
            "timestamp_qualification": "Local process clocks and operator attestations only; hashes do not independently certify creation time or enforce blinding."}


def validate_saved_gate(root, gate_path):
    gate_path = Path(gate_path).resolve()
    saved = load(gate_path)
    now = datetime.now(timezone.utc)
    if aware(saved["recorded_at"]) > now:
        raise ValueError("gate creation time is in the future")
    expected = check_gate(root, pinned(root, saved["protocol_freeze"]), pinned(root, saved["session_ledger"]),
                          pinned(root, saved["access_log"]), now=aware(saved["recorded_at"]))
    if saved != expected:
        raise ValueError("saved gate differs from recomputed identity/chronology checks")
    return {**expected, "gate": pin(Path(root).resolve(), gate_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--access-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if output.exists() or not output.is_relative_to(ROOT / "work/29_verniman_level_reconstruction"):
        raise ValueError("new retained Phase6 work-stage output required")
    result = check_gate(ROOT, ROOT / args.freeze, ROOT / args.ledger, ROOT / args.access_log)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False); handle.write("\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "status": result["status"],
                      "timely_count": result["complete_timely_count"], "evaluation_status": result["evaluation_status"]}))


if __name__ == "__main__":
    main()
