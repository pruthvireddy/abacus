#!/usr/bin/env python3
"""Append-only prospective capture around the unchanged Phase 5 mechanism.

No source loader is imported. Preparation does not capture future observations.
The CLI clock is read inside this process; it is local evidence, not an
independent timestamp certificate. Later replay is never classified timely.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
from math import isfinite
from pathlib import Path
import sys
from types import SimpleNamespace
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
NY = ZoneInfo("America/New_York")
CONFIGURATIONS = ("P0-D1", "P0-D0", "B0-D0", "B0-D1", "B1-D0", "B1-D1")
MARKET = {"symbol": "CME_MINI:ESZ2026", "contract": "ESZ2026", "feed": "CME GLOBEX",
          "adjustment": "individual_contract_unadjusted", "minutes": 5, "session": "ETH",
          "timezone": "America/New_York", "tick_size": .25, "row_ticks": 16,
          "value_area_percent": 70, "grid_origin": 0, "cutoff_hour": 9,
          "cutoff_minute": 25, "manual_anchors": []}
BASELINE_FIELDS = ("previous_full_high", "previous_full_low", "current_week_vah", "current_week_poc", "current_week_val",
                   "previous_week_vah", "previous_week_poc", "previous_week_val", "completed_rth_vah", "completed_rth_poc",
                   "completed_rth_val", "overnight_vah", "overnight_poc", "overnight_val", "overnight_high", "overnight_low",
                   "completed_rth_high", "completed_rth_low", "rth_last_traded_close")
FIXED = {
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
    "phase5_runner": "6878d29604e6ba0a6ba8776e43624dd4745acc54d2e4bf6426c2a15b78a84b67",
}
TERMINAL_STATUSES = frozenset(("timely", "late", "reconstructed", "missing", "input_unavailable", "exposed", "unsupported"))


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def aware(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timezone-aware time required")
    return result


def at(day, clock):
    return datetime.combine(date.fromisoformat(day), time.fromisoformat(clock), NY)


def resolved(root, value):
    root = Path(root).resolve()
    path = Path(value)
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("artifact path escapes workspace")
    return path


def pin(root, row):
    path = resolved(root, row["path"])
    if not path.is_file() or digest(path) != row.get("sha256"):
        raise ValueError("missing or changed pinned bytes: " + str(row.get("path")))
    return path


def pinned(root, path):
    path = resolved(root, path)
    return {"path": str(path.relative_to(Path(root).resolve())), "sha256": digest(path)}


def read_json(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_freeze(root, freeze_path, *, now=None):
    """Validate exact producer snapshots before parsing any market content."""
    root = Path(root).resolve()
    freeze_path = resolved(root, freeze_path)
    freeze = read_json(freeze_path)
    if freeze.get("schema") != "abacus.study29.phase6.freeze/v1":
        raise ValueError("explicit Phase6 freeze required")
    dates = freeze.get("scheduled_dates", [])
    if len(dates) != 20 or dates != sorted(set(dates)):
        raise ValueError("exact twenty ordered unique scheduled dates required")
    frozen_at = aware(freeze["frozen_at"])
    if frozen_at > (now or datetime.now(timezone.utc)):
        raise ValueError("protocol freeze cannot be in the future")
    if any(date.fromisoformat(day).weekday() > 4 or at(day, "09:25") <= frozen_at for day in dates):
        raise ValueError("scheduled weekday cutoffs must occur after protocol freeze")
    if tuple(freeze.get("configurations", [])) != CONFIGURATIONS:
        raise ValueError("six unchanged predeclared configurations required")
    if freeze.get("market_configuration") != MARKET:
        raise ValueError("frozen unadjusted ESZ2026 market configuration differs")
    if freeze.get("cutoff_local") != "09:25" or freeze.get("capture_deadline_local") != "09:30":
        raise ValueError("frozen09:25cutoff/09:30capture deadline required")
    if aware(freeze["period_end_at"]) != at(dates[-1], "16:00"):
        raise ValueError("period end must be final scheduled16:00NY")
    documents = freeze.get("files", [])
    by_document_role = {row.get("role"): row for row in documents}
    if not documents or len(by_document_role) != len(documents) or "calendar" not in by_document_role:
        raise ValueError("unique frozen protocol/settings/calendar file pins required")
    for row in documents:
        pin(root, row)
    rows = freeze.get("producer_files", [])
    roles = {row.get("role"): row for row in rows}
    if len(roles) != len(rows) or not (set(FIXED) | {"capture_runner", "calendar_control"}) <= roles.keys():
        raise ValueError("complete unique exact producer roles required")
    snapshots = {}
    for role, row in roles.items():
        if role in FIXED and row.get("sha256") != FIXED[role]:
            raise ValueError("fixed Phase5 artifact identity differs: " + role)
        source = pin(root, row)
        snapshot = resolved(root, row["snapshot_path"])
        if not snapshot.is_file() or digest(snapshot) != row["sha256"]:
            raise ValueError("retained producer snapshot differs: " + role)
        snapshots[role] = snapshot
        if role == "capture_runner" and row["sha256"] != digest(__file__):
            raise ValueError("executed capture wrapper differs from frozen producer")
    directory = snapshots["phase4_model"].parent
    if snapshots["phase3_model"] != directory / "phase3_model.py" or snapshots["reference_model"] != directory / "reference_model.py":
        raise ValueError("model dependency snapshot tree differs")
    if snapshots["matcher"] != directory.parent / "phase3/matching.py":
        raise ValueError("matcher must occupy actual frozen import path")
    calendar_control = load_module("study29_phase6_pinned_calendar_control", snapshots["calendar_control"])
    calendar = read_json(pin(root, by_document_role["calendar"]))
    calendar_control.validate_calendar(calendar, freeze["frozen_at"])
    if calendar["scheduled_dates"] != dates:
        raise ValueError("frozen dates differ from independently fixed calendar")
    return freeze, snapshots


def validate_session(freeze, day):
    if day not in freeze["scheduled_dates"]:
        raise ValueError("session not in fixed prospective calendar")


def validate_access_log(root, row, operator_id, process_started):
    path = pin(root, row)
    access = read_json(path)
    if access.get("schema") != "abacus.study29.phase6.access-log/v1" or access.get("complete_to_best_knowledge") is not True:
        raise ValueError("explicit complete-to-best-knowledge actor access log required")
    closed = aware(access["closed_through"])
    if closed > process_started or process_started - closed > timedelta(minutes=5):
        raise ValueError("source access log must close within five minutes before process start, never in the future")
    actors = access.get("actors", [])
    if len({a.get("actor_id") for a in actors}) != len(actors):
        raise ValueError("actor IDs must be unique")
    for actor in actors:
        actor_id = actor.get("actor_id")
        if not isinstance(actor_id, str) or not actor_id.strip() or any(word in actor_id.lower() for word in ("pending", "placeholder", "unassigned", "unknown", "todo")):
            raise ValueError("actual nonplaceholder actor identity required")
        if actor.get("role") not in ("prediction", "collector", "scorer"):
            raise ValueError("explicit actor responsibility required")
    if not any(a.get("actor_id") == operator_id and a.get("role") == "prediction" for a in actors):
        raise ValueError("identified prediction operator required")
    if not isinstance(access.get("events"), list):
        raise ValueError("explicit source access events array required")
    for event in access["events"]:
        if aware(event["occurred_at"]) > closed:
            raise ValueError("access event is later than declared log closure")
        if event.get("actor_id") not in {a["actor_id"] for a in actors}:
            raise ValueError("source event actor is undeclared")
        if event.get("kind") not in ("answer_access", "answer_disclosure"):
            raise ValueError("unknown source access event kind")
    return access


def classify(freeze, day, mode, started, completed, access, operator_id, complete):
    if completed < started or started < aware(freeze["frozen_at"]):
        raise ValueError("capture process chronology differs")
    if mode not in ("prospective", "historical_replay"):
        raise ValueError("explicit prospective or historical_replay mode required")
    if started < at(day, freeze["cutoff_local"]):
        raise ValueError("capture execution cannot begin before confirmed cutoff")
    exposed = any((e.get("actor_id") == operator_id or e.get("kind") == "answer_disclosure" and e.get("recipient_actor_id") == operator_id)
                  and e.get("session_date") in freeze["scheduled_dates"] and aware(e["occurred_at"]) <= completed for e in access["events"])
    if exposed:
        return "exposed"
    if not complete:
        return "unsupported"
    if mode == "historical_replay":
        return "reconstructed"
    if completed.astimezone(NY).date().isoformat() != day:
        return "late"
    return "timely" if completed <= at(day, freeze["capture_deadline_local"]) else "late"


def _csv_rows(path, day, *, trim):
    """Only this adapter filters raw exports; executed prefixes reject future rows."""
    cutoff = at(day, "09:25")
    rows, excluded = [], 0
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        names = {key.lower(): key for key in reader.fieldnames or ()}
        if not {"time", "open", "high", "low", "close", "volume"} <= names.keys():
            raise ValueError("native timestamp and OHLCV columns required")
        for row in reader:
            stamp = row[names["time"]]
            opened = datetime.fromtimestamp(int(stamp), timezone.utc) if stamp.lstrip("-").isdigit() else aware(stamp)
            opened = opened.astimezone(NY)
            if opened.date() > date.fromisoformat(day):
                raise ValueError("capture contains a later market date")
            if opened.second or opened.microsecond or opened.minute % 5:
                raise ValueError("five-minute aligned opens required")
            if opened + timedelta(minutes=5) > cutoff:
                if not trim:
                    raise ValueError("post-cutoff input contamination in execution prefix")
                excluded += 1
                continue
            values = [float(row[names[k]]) for k in ("open", "high", "low", "close", "volume")]
            opening, high, low, close, volume = values
            if not all(isfinite(v) for v in values) or low > min(opening, close) or high < max(opening, close) or volume < 0:
                raise ValueError("invalid finite OHLCV interval")
            rows.append((opened, *values))
    if not rows or rows[-1][0] != cutoff - timedelta(minutes=5):
        raise ValueError("exact completed09:20–09:25 terminal bar missing")
    if any(a[0] >= b[0] for a, b in zip(rows, rows[1:])):
        raise ValueError("strictly increasing unique timestamps required")
    return rows, excluded


def read_bars(path, day, model):
    rows, _ = _csv_rows(path, day, trim=False)
    return [model.P3.BASE.Bar(r[0], r[0] + timedelta(minutes=5), r[2], r[3], r[4], r[5], True) for r in rows]


def audit_coverage(bars, day, calendar_control):
    """Unchanged eight fixed-clock coverage requirements; no holiday repair."""
    seen = {int(bar.opened.timestamp()) for bar in bars}
    records = []
    for name, start, end, maintenance in calendar_control.required_windows(day):
        expected = set()
        cursor = start
        while cursor < end:
            if not maintenance or cursor.hour != 17:
                expected.add(int(cursor.timestamp()))
            cursor += timedelta(minutes=5)
        missing = sorted(expected - seen)
        records.append({"window": name, "reference_start": start.isoformat(), "reference_end": end.isoformat(),
            "expected_bars": len(expected), "observed_bars": len(expected & seen), "missing_bars": len(missing),
            "missing_open_examples": [datetime.fromtimestamp(t, NY).isoformat() for t in missing[:16]], "ready": not missing})
    return {"status": "complete" if len(records) == 8 and all(r["ready"] for r in records) else "incomplete",
            "required_windows": records, "policy": "Strict expected weekday and five-minute fixed clocks; no holiday or missing-bar substitution"}


def prepare_input(root, freeze_path, day, raw_csv, output, *, now=None):
    current = now or datetime.now(timezone.utc)
    freeze, _ = validate_freeze(root, freeze_path, now=current)
    validate_session(freeze, day)
    if current < at(day, "09:25"):
        raise ValueError("cannot prepare a future completed cutoff")
    raw_csv, output = resolved(root, raw_csv), resolved(root, output)
    if output.exists():
        raise ValueError("fresh immutable input directory required")
    rows, excluded = _csv_rows(raw_csv, day, trim=True)
    output = _new_output(root, output)
    target = output / "cutoff-input.csv"
    with target.open("x", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("time", "open", "high", "low", "close", "volume"))
        writer.writerows((r[0].isoformat(), *r[1:]) for r in rows)
    manifest = {"schema": "abacus.study29.phase6.market-inputs/v1", "session_date": day,
        "recorded_at": current.isoformat(), "protocol_freeze": pinned(root, freeze_path),
        "market_configuration": MARKET, "raw_export": pinned(root, raw_csv), "file": pinned(root, target),
        "first_included_open": rows[0][0].isoformat(), "last_included_open": rows[-1][0].isoformat(),
        "last_included_close": at(day, "09:25").isoformat(), "included_rows": len(rows),
        "excluded_raw_after_cutoff_rows": excluded,
        "transformation": "Retain identified OHLCV rows with close<=09:25NY; ignore derived columns; no price adjustment",
        "timestamp_qualification": "Local process clock only; no independent certification"}
    write_new(output / "input-manifest.json", manifest)
    return manifest


def validate_input(root, freeze_path, day, row):
    source_path = pin(root, row)
    source = read_json(source_path)
    if source.get("schema") != "abacus.study29.phase6.market-inputs/v1" or source.get("session_date") != day:
        raise ValueError("exact scheduled input session required")
    if source.get("market_configuration") != MARKET or pin(root, source["protocol_freeze"]) != resolved(root, freeze_path):
        raise ValueError("input configuration/freeze differs")
    raw = pin(root, source["raw_export"])
    path = pin(root, source["file"])
    rows, _ = _csv_rows(path, day, trim=False)
    original, excluded = _csv_rows(raw, day, trim=True)
    if rows != original or source.get("included_rows") != len(rows) or source.get("excluded_raw_after_cutoff_rows") != excluded:
        raise ValueError("execution prefix differs from declared raw OHLCV transformation")
    if aware(source["first_included_open"]) != rows[0][0]:
        raise ValueError("preceding-history start metadata differs")
    if aware(source["last_included_open"]) != at(day, "09:20") or aware(source["last_included_close"]) != at(day, "09:25"):
        raise ValueError("input terminal metadata differs")
    return source, path


def validate_saved_map(prediction, day):
    """Check saved expanded structure without recalculating any selection."""
    if prediction.get("schema") != "abacus.study29.phase6.local-map/v1" or prediction.get("session_date") != day:
        raise ValueError("prediction date/schema differs")
    if prediction.get("market_configuration") != MARKET or tuple(prediction.get("configurations", [])) != CONFIGURATIONS:
        raise ValueError("prediction settings/configurations differ")
    if type(prediction.get("complete_expanded_map")) is not bool or not isinstance(prediction.get("incomplete_reasons"), list):
        raise ValueError("explicit map completeness and reasons required")
    if aware(prediction["bar_audit"]["last_included_open"]) != at(day, "09:20") or aware(prediction["bar_audit"]["last_included_close"]) != at(day, "09:25"):
        raise ValueError("prediction has post-cutoff or missing terminal boundary")
    if prediction["bar_audit"].get("excluded_after_cutoff_rows") != 0:
        raise ValueError("executed map must consume strict cutoff prefix only")
    if set(prediction.get("selections", {})) != set(CONFIGURATIONS):
        raise ValueError("complete six-policy selection inventory required")
    if prediction["complete_expanded_map"]:
        coverage = prediction.get("input_coverage", {})
        if coverage.get("status") != "complete" or len(coverage.get("required_windows", [])) != 8 or any(row.get("ready") is not True or row.get("missing_bars") != 0 for row in coverage["required_windows"]):
            raise ValueError("all eight fixed-clock input windows must be complete")
        baseline = prediction.get("original_baseline_fields", {})
        if set(baseline) != set(BASELINE_FIELDS) or any(not isinstance(v, (float, int)) or not isfinite(v) for v in baseline.values()):
            raise ValueError("exact19 finite original baseline field names required")
        expanded = prediction.get("expanded_snapshot", {})
        distributions, ledgers = expanded.get("distributions", []), expanded.get("candidate_ledgers", [])
        windows = {"completed_RTH", "overnight_prefix", "current_week_prefix", "previous_completed_week", "explicit_composite_RTH3"}
        if len(distributions) != 5 or {d.get("window") for d in distributions} != windows or any(not d.get("profile_id") or not d.get("masses") for d in distributions):
            raise ValueError("five actual distributions and window identities required")
        required = {"policy", "distribution", "peaks", "regions", "lvn_ledger", "edge_ledger", "presentation", "counts", "status"}
        if len(ledgers) != 5 or any(not required <= ledger.keys() or ledger.get("status") != "ready" for ledger in ledgers):
            raise ValueError("full candidate/rejection/omission ledgers required")
        if "composite_ledger" not in expanded or "projection_ledgers" not in expanded:
            raise ValueError("explicit composite and PBT eligibility ledgers required")
        profiles = prediction.get("profile_readiness", [])
        if len(profiles) != 5 or {p.get("window") for p in profiles} != windows or any(p.get("status") != "ready" for p in profiles):
            raise ValueError("required profiles not ready in complete prediction")
        if prediction["incomplete_reasons"]:
            raise ValueError("complete map cannot have incomplete reasons")
        for selection in prediction["selections"].values():
            if not {"pivot", "bullish", "bearish", "candidate_ids", "input_identity", "generator_identity"} <= selection.keys():
                raise ValueError("full original selection identities required")
            pivot = selection["pivot"]
            if not {"candidate", "reason_code", "status", "fallback", "fallback_status", "alternatives"} <= pivot.keys():
                raise ValueError("pivot reasons/fallback/alternative ledger required")
            for side in ("bullish", "bearish"):
                branch = selection[side]
                if not {"targets", "status", "reasons", "alternatives"} <= branch.keys() or len(branch["targets"]) > 3:
                    raise ValueError("both capped branches and rejection ledgers required")
                for rank, target in enumerate(branch["targets"], 1):
                    if target.get("rank") != rank or not target.get("reason_code") or not (target.get("candidate") or {}).get("candidate_id"):
                        raise ValueError("original ranked target IDs/reasons required")
    return prediction


def construct_map(root, freeze_path, freeze, snapshots, day, source, csv_path, started):
    """Same frozen engines and policy calls; only orchestration/date schema is new."""
    helper = load_module("study29_phase6_pinned_phase5_helpers", snapshots["phase5_runner"])
    calendar_control = load_module("study29_phase6_pinned_coverage_calendar", snapshots["calendar_control"])
    model = load_module("study29_phase6_exact_phase4_model", snapshots["phase4_model"])
    load_module("reference_model", snapshots["reference_model"])
    comparator_model = load_module("study29_phase6_exact_autopivot", snapshots["autopivot_model"])
    bars = read_bars(csv_path, day, model)
    coverage = audit_coverage(bars, day, calendar_control)
    engine = model.Phase4Engine(contract="ESZ2026", feed="CME GLOBEX", adjustment="individual_contract_unadjusted",
        tick_size=.25, row_size=4, va_pct=70, input_identity=source["file"]["sha256"],
        code_identity=FIXED["phase3_model"], settings_identity=FIXED["phase3_settings"], minutes=5)
    engine.feed(bars)
    expanded = engine.expanded_snapshot
    if expanded is None or expanded.baseline.trading_date.isoformat() != day:
        raise ValueError("no exact-date expanded snapshot: " + engine.snapshot_status)
    inputs = model.inputs_from_phase3(expanded, bars[-1].close)
    selections = {key: model.select_map(inputs, pivot_policy=key.split("-")[0], target_policy=key.split("-")[1]) for key in CONFIGURATIONS}
    comparator = comparator_model.PivotEngine()
    comparator.feed(bars)
    frozen = comparator.frozen
    current = frozen.selection if frozen else None
    alternate = comparator_model.alternate_reference(current.price, current.reason, *current.inputs[:3], current.inputs[4]) if current else (None, "na")
    readiness = [{"window": d.window, "profile_id": d.profile_id, "status": ledger["status"],
        "reasons": ledger["distribution"]["reasons"], "included_sessions": d.included_sessions,
        "expected_sessions": d.expected_sessions, "row_count": len(d.masses), "last_included_open": d.last_bar_open,
        "last_included_close": d.last_bar_close, "counts": ledger.get("counts"), "presentation": ledger.get("presentation")}
        for d, ledger in zip(expanded.distributions, expanded.candidate_ledgers)]
    missing = helper.complete_map_reasons(expanded, inputs, selections)
    if coverage["status"] != "complete":
        missing.append("required_eight_fixed_clock_windows_incomplete")
    if current is None or current.price is None:
        missing.append("immutable_Autopivot_prediction_unavailable")
    result = {"schema": "abacus.study29.phase6.local-map/v1", "session_date": day,
        "execution": {"kind": "frozen_local_specification_model_not_Pine", "started_at": started,
            "protocol_freeze": pinned(root, freeze_path)},
        "candidate_control": "phase3-3.0.0", "candidate_implementation": "3.0.2",
        "selector_policy": "phase4-4.0.0", "selector_implementation": "4.0.1",
        "configurations": list(CONFIGURATIONS), "market_configuration": MARKET, "input": source["file"],
        "bar_audit": {"included_rows": len(bars), "excluded_after_cutoff_rows": 0,
            "last_included_open": bars[-1].opened, "last_included_close": bars[-1].closed,
            "first_included_open": bars[0].opened}, "cutoff_close": inputs.cutoff_close,
        "input_coverage": coverage, "original_baseline_fields": dict(zip(helper.BASELINE_FIELDS, expanded.baseline.values)),
        "expanded_snapshot": expanded, "selector_inputs": inputs, "profile_readiness": readiness,
        "selections": selections, "complete_expanded_map": not missing, "incomplete_reasons": missing,
        "autopivot_comparator": {"execution": "immutable_Phase4_capture_translated_model_not_fresh_Pine",
            "pine_sha256": FIXED["autopivot_pine"], "model_sha256": FIXED["autopivot_model"], "frozen": frozen,
            "alternate_model_only": {"price": alternate[0], "origin": alternate[1], "is_target": False},
            "input_policy_difference": "P0 strict expected prior-weekday RTH; comparator latest actually observed RTH"},
        "source_method_fidelity_established": False, "selection_fitted": False,
        "limits": "Local translated-model output; actual native observations require separate evidence. Missing PBT anchors stay unavailable; VIX/CVD unmeasured."}
    return helper.plain(result)


def _check_output(root, output):
    output = resolved(root, output)
    if output.exists():
        raise ValueError("fresh immutable capture directory required")
    if not output.is_relative_to(Path(root).resolve() / "work/29_verniman_level_reconstruction"):
        raise ValueError("capture evidence must stay under owning study work root")
    return output


def _new_output(root, output):
    output = _check_output(root, output)
    output.mkdir(parents=True)
    return output


def validate_capture_attestation(root, request, day):
    if request.get("schema") != "abacus.study29.phase6.capture-request/v1":
        raise ValueError("explicit Phase6 capture request required")
    terminal = request.get("observed_terminal_bar", {})
    if terminal.get("confirmed") is not True or aware(terminal.get("opened")) != at(day, "09:20") or aware(terminal.get("closed")) != at(day, "09:25"):
        raise ValueError("actual confirmed terminal-bar attestation required")
    evidence = request.get("native_evidence", [])
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("nonempty actual browser/settings/terminal evidence required")
    for row in evidence:
        if pin(root, row).stat().st_size == 0:
            raise ValueError("native evidence is empty")
    return evidence


def capture(root, freeze_path, request_path, output, *, clock=None):
    clock = clock or (lambda: datetime.now(timezone.utc))
    started = clock()
    freeze, snapshots = validate_freeze(root, freeze_path, now=started)
    _check_output(root, output)  # Refuse a duplicate attempt before model import/execution.
    request_path = resolved(root, request_path)
    request = read_json(request_path)
    if request.get("schema") != "abacus.study29.phase6.capture-request/v1":
        raise ValueError("explicit Phase6 capture request required")
    day = request["session_date"]
    validate_session(freeze, day)
    if started < at(day, "09:25"):
        raise ValueError("cannot capture a future completed cutoff")
    source, csv_path = validate_input(root, freeze_path, day, request["input_manifest"])
    if aware(source["recorded_at"]) > started:
        raise ValueError("input manifest records a future preparation time")
    evidence = validate_capture_attestation(root, request, day)
    # Inspect the actor log before generation; it conveys only access metadata.
    validate_access_log(root, request["source_access_log"], request["operator_id"], started)
    model_map = construct_map(root, freeze_path, freeze, snapshots, day, source, csv_path, started)
    output = _new_output(root, output)
    map_path = output / "prediction.json"
    write_new(map_path, model_map)
    map_pin = pinned(root, map_path)
    completed = clock()
    access = validate_access_log(root, request["source_access_log"], request["operator_id"], started)
    status = classify(freeze, day, request["capture_mode"], started, completed, access, request["operator_id"], model_map["complete_expanded_map"])
    receipt = {"schema": "abacus.study29.phase6.capture/v1", "session_date": day, "status": status,
        "prediction": map_pin, "input_manifest": request["input_manifest"],
        "inputs": [source["file"], source["raw_export"]], "producer_manifest": pinned(root, freeze_path),
        "protocol_freeze": pinned(root, freeze_path), "captured_at": completed.isoformat(),
        "capture_mode": request["capture_mode"], "operator_id": request["operator_id"],
        "source_access_log": request["source_access_log"], "request": pinned(root, request_path),
        "access_audit_qualification": "Fresh pre-process operator log; wrapper imports no answer loader. Actual access during/after execution remains subject to the final whole-period actor audit; no independent non-access proof.",
        "timestamp_evidence": {"kind": "local_process_clock_only", "independent_certification": False,
            "process_started_at": started.isoformat(), "process_completed_at": completed.isoformat(),
            "operator_evidence": evidence, "qualification": "Operator/OS/browser evidence; hash proves bytes, not independent pre-existence or complete non-access"},
        "complete_expanded_map": model_map["complete_expanded_map"],
        "incomplete_reasons": model_map["incomplete_reasons"], "native_execution_established_by_capture_tool": False,
        "source_method_fidelity_established": False}
    write_new(output / "capture-receipt.json", receipt)
    verify_capture(root, freeze_path, output / "capture-receipt.json", now=completed)
    return receipt


def finalize_status(root, freeze_path, request_path, output, *, now=None):
    current = now or datetime.now(timezone.utc)
    freeze, _ = validate_freeze(root, freeze_path, now=current)
    request_path = resolved(root, request_path)
    request = read_json(request_path)
    if request.get("schema") != "abacus.study29.phase6.status-request/v1":
        raise ValueError("explicit Phase6 status request required")
    day, status = request["session_date"], request["status"]
    validate_session(freeze, day)
    if status not in ("missing", "input_unavailable") or not request.get("incomplete_reasons"):
        raise ValueError("explicit missing/input_unavailable status and reasons required")
    if current < at(day, freeze["capture_deadline_local"]):
        raise ValueError("cannot finalize a scheduled failure before its deadline")
    validate_access_log(root, request["source_access_log"], request["operator_id"], current)
    output = _new_output(root, output)
    receipt = {"schema": "abacus.study29.phase6.capture/v1", "session_date": day, "status": status,
        "prediction": None, "input_manifest": None, "inputs": [],
        "producer_manifest": pinned(root, freeze_path), "protocol_freeze": pinned(root, freeze_path),
        "captured_at": current.isoformat(), "capture_mode": "not_captured", "operator_id": request["operator_id"],
        "source_access_log": request["source_access_log"], "request": pinned(root, request_path),
        "timestamp_evidence": {"kind": "local_process_clock_only", "independent_certification": False,
            "process_started_at": current.isoformat(), "process_completed_at": current.isoformat(), "operator_evidence": []},
        "complete_expanded_map": False, "incomplete_reasons": request["incomplete_reasons"],
        "native_execution_established_by_capture_tool": False, "source_method_fidelity_established": False}
    write_new(output / "capture-receipt.json", receipt)
    verify_capture(root, freeze_path, output / "capture-receipt.json", now=current)
    return receipt


def verify_capture(root, freeze_path, receipt_path, *, now=None):
    """Read/hash saved bytes and semantics only. Never rerun engine or selection."""
    current = now or datetime.now(timezone.utc)
    freeze, snapshots = validate_freeze(root, freeze_path, now=current)
    receipt = read_json(resolved(root, receipt_path))
    if receipt.get("schema") != "abacus.study29.phase6.capture/v1" or receipt.get("status") not in TERMINAL_STATUSES:
        raise ValueError("explicit final capture receipt required")
    day = receipt["session_date"]
    validate_session(freeze, day)
    if pin(root, receipt["protocol_freeze"]) != resolved(root, freeze_path) or receipt.get("producer_manifest") != receipt["protocol_freeze"]:
        raise ValueError("capture protocol/producer identity differs")
    stamp = receipt["timestamp_evidence"]
    if stamp.get("kind") != "local_process_clock_only" or stamp.get("independent_certification") is not False:
        raise ValueError("local clock evidence cannot claim independent certification")
    started, completed = aware(stamp["process_started_at"]), aware(stamp["process_completed_at"])
    if completed != aware(receipt["captured_at"]) or completed > current or completed < started:
        raise ValueError("capture timestamp chronology differs")
    access = validate_access_log(root, receipt["source_access_log"], receipt["operator_id"], started)
    request = read_json(pin(root, receipt["request"]))
    if any(request.get(k) != receipt.get(k) for k in ("session_date", "operator_id", "source_access_log")):
        raise ValueError("request/receipt actor/date/access identity differs")
    if receipt["status"] in ("missing", "input_unavailable"):
        if request.get("schema") != "abacus.study29.phase6.status-request/v1" or request.get("status") != receipt["status"] or request.get("incomplete_reasons") != receipt.get("incomplete_reasons"):
            raise ValueError("status request schema/status/reasons differ from saved receipt")
        if receipt.get("prediction") is not None or receipt.get("input_manifest") is not None or receipt.get("complete_expanded_map") is not False:
            raise ValueError("failure placeholder cannot masquerade as a prediction")
        if completed < at(day, freeze["capture_deadline_local"]) or not receipt.get("incomplete_reasons"):
            raise ValueError("missing status needs elapsed deadline and explicit reasons")
        return receipt
    source, csv_path = validate_input(root, freeze_path, day, receipt["input_manifest"])
    validate_capture_attestation(root, request, day)
    if aware(source["recorded_at"]) > started:
        raise ValueError("input preparation chronology differs")
    if any(request.get(k) != receipt.get(k) for k in ("capture_mode", "input_manifest")) or request.get("native_evidence") != stamp.get("operator_evidence"):
        raise ValueError("request/receipt mode/input/evidence identity differs")
    if receipt.get("inputs") != [source["file"], source["raw_export"]]:
        raise ValueError("capture input identities differ")
    for row in stamp.get("operator_evidence", []):
        pin(root, row)
    if not stamp.get("operator_evidence"):
        raise ValueError("actual capture evidence required")
    prediction = read_json(pin(root, receipt["prediction"]))
    validate_saved_map(prediction, day)
    if "input_coverage" in prediction:
        # A read-only timestamp audit is distinct from rerunning the detector or
        # selector. It prevents stored ready flags from replacing actual history.
        rows, _ = _csv_rows(csv_path, day, trim=False)
        calendar_control = load_module("study29_phase6_saved_timestamp_coverage", snapshots["calendar_control"])
        expected_coverage = audit_coverage([SimpleNamespace(opened=row[0]) for row in rows], day, calendar_control)
        if prediction["input_coverage"] != expected_coverage:
            raise ValueError("saved eight-window coverage differs from actual input timestamps")
    if aware(prediction["execution"]["started_at"]) != started or prediction["execution"].get("protocol_freeze") != receipt["protocol_freeze"]:
        raise ValueError("map execution chronology/freeze differs")
    if prediction.get("input") != source["file"]:
        raise ValueError("map input differs")
    if receipt.get("complete_expanded_map") != prediction.get("complete_expanded_map") or receipt.get("incomplete_reasons") != prediction.get("incomplete_reasons"):
        raise ValueError("map completeness receipt differs")
    expected = classify(freeze, day, receipt["capture_mode"], started, completed, access, receipt["operator_id"], receipt["complete_expanded_map"])
    if receipt["status"] != expected:
        raise ValueError("capture status incorrectly classifies timing/exposure/readiness")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--freeze", type=Path, required=True)
    subs = parser.add_subparsers(dest="command", required=True)
    prepare = subs.add_parser("prepare-input")
    prepare.add_argument("--session", required=True)
    prepare.add_argument("--raw-csv", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    for name in ("capture", "finalize-status"):
        sub = subs.add_parser(name)
        sub.add_argument("--request", type=Path, required=True)
        sub.add_argument("--output", type=Path, required=True)
    check = subs.add_parser("verify-capture")
    check.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "prepare-input":
        result = prepare_input(root, args.freeze, args.session, args.raw_csv, args.output)
    elif args.command == "capture":
        result = capture(root, args.freeze, args.request, args.output)
    elif args.command == "finalize-status":
        result = finalize_status(root, args.freeze, args.request, args.output)
    else:
        result = verify_capture(root, args.freeze, args.receipt)
    print(json.dumps({"session_date": result["session_date"], "status": result.get("status", "input_prefix_prepared"),
                      "future_capture_fabricated": False, "source_answers_read": False}))


if __name__ == "__main__":
    main()
