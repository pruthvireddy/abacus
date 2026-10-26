"""Recover saved development packets without rescoring adopted outcomes.

This orchestration companion delegates scientific calculations to the frozen
Stage 3 helpers. Saved acceptance is joined to its original mapped roster;
mask audits inspect metadata only. Each descriptive frame bundle is retained
before the one original global close. Reserved phases are inaccessible here.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import pickle
import sys
import time
import traceback

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .execution import file_record, verify_record
from .stage3_execution import assert_frozen, assert_input_bytes, assert_numerical_gate, write_once
from .stage3_events import gate_spec
from .stage3_masks import boundary, event_masks, scoring_periods
from .stage3_parallel_execution import (configured_gates, cell_plan, stream_chunk,
    close_development, acceptance_records, validate_outcome_records)
from .stage3_selection import fold_records
from .stage3_statistics import summaries, quantiles, stability, _flow, _key, _id

SCHEMA = "study21.stage3-recovery-freeze/v1"
KERNELS = ("engine.py", "outcomes.py", "statistics.py", "stage2_engine.py",
           "stage3_events.py", "stage3_masks.py", "stage3_outcomes.py",
           "stage3_statistics.py", "stage3_selection.py", "stage3_parallel_execution.py")
FRAME_KEYS = ("scorecard", "quantiles", "stability", "folds", "audit", "flow")
ROUNDTRIP_FLAGS = frozenset(("favorable", "neutral", "adverse", "mfe_gt_mae", "mfe_mae_tie", "crosses_closure", "same_session"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def key_of(record):
    return (record["product"], int(record["interval_minutes"]),
            record.get("touch_mode", record.get("branch")), record["gate_id"])


def generic_pins(value, stage):
    """Verify safe generic local and explicit absolute external identities."""
    local, external = value.get("records", []), value.get("external_records", [])
    require(isinstance(local, list) and isinstance(external, list), "generic identity lists required")
    seen = set()
    for record in local:
        path = verify_record(record, stage)
        require(str(path.resolve()) not in seen, "duplicate generic artifact identity")
        seen.add(str(path.resolve()))
    for record in external:
        require(Path(record["path"]).is_absolute(), "external artifact must be absolute")
        path = verify_record(record)
        require(str(path.resolve()) not in seen, "duplicate generic artifact identity")
        seen.add(str(path.resolve()))
    return seen


def pinned_receipt(path, stage):
    value = json.loads(Path(path).read_text())
    require(value.get("status") == "passed", "passing recovery dependency required")
    generic_pins(value, stage)
    return value


def gate_specs(cfg, product):
    specs = [gate_spec("absolute", v) for v in cfg["absolute_gates"][product]]
    specs += [gate_spec("atr", v) for v in cfg["atr_gates"]]
    return {spec["gate_id"]: spec for spec in specs}


def packet_plan(cfg, freeze, authorized_gates):
    """Complete disjoint adopted/missing inventory, in original gate order."""
    cell_plan(cfg, authorized_gates)
    expected = configured_gates(cfg)
    recovery = cfg["development_recovery"]
    missing = tuple(tuple(k) for k in freeze["missing_gates"])
    require(missing == tuple(tuple(k) for k in recovery["expected_missing_gateways"]),
            "missing gateway list differs from frozen recovery config")
    require(len(missing) == len(set(missing)) and set(missing) <= set(expected), "invalid missing gateway inventory")
    packets = freeze["packets"]
    keys = [tuple(packet["key"]) for packet in packets]
    require(len(keys) == len(set(keys)), "duplicate adopted packet")
    require(len(keys) == recovery["expected_adopted_gateways"] and set(keys) == set(expected) - set(missing),
            "complete disjoint adopted/missing gateway inventory required")
    by_key = dict(zip(keys, packets))
    for key, packet in by_key.items():
        require(packet["gate"] == gate_specs(cfg, key[0])[key[3]], "adopted gate specification differs")
    return expected, by_key, missing


def read_frame(record, stage=None):
    path = verify_record(record, stage)
    frame = pd.read_parquet(path)
    require(len(frame) == record.get("rows", record.get("row_count")), "saved row count differs")
    decoded = {c: str(t) for c, t in frame.dtypes.items()}
    declared = record.get("schema", {})
    require(set(decoded) == set(declared), "saved pandas schema differs")
    # Original Parquet metadata sometimes retains an object producer dtype
    # while decoding a null-free Boolean column as bool. Verify that exact
    # declared producer metadata rather than treating this as byte drift.
    metadata = json.loads(pq.read_schema(path).metadata[b"pandas"])
    fields = {c["name"]: c for c in metadata["columns"]}
    for c in frame:
        if decoded[c] == declared[c]:
            continue
        require(record["role"] == "outcomes" and c in ROUNDTRIP_FLAGS and declared[c] == "object" and decoded[c] == "bool"
                and frame[c].notna().all() and fields[c]["numpy_type"] == "object" and fields[c]["pandas_type"] == "bool",
                "saved pandas schema differs")
    require(list(frame.columns) == list(record["schema"]), "saved column order differs")
    if "columns" in record:
        require(list(frame.columns) == record["columns"], "saved scientific columns differ")
    return frame


def producer_frame(frame, record):
    """Restore only original declared null-free object Boolean producer dtypes."""
    restored = frame.copy()
    for c, declared in record["schema"].items():
        if str(restored[c].dtype) != declared:
            require(c in ROUNDTRIP_FLAGS and declared == "object" and str(restored[c].dtype) == "bool" and restored[c].notna().all(),
                    "unsupported producer dtype rehydration")
            restored[c] = restored[c].astype(object)
    require({c: str(t) for c, t in restored.dtypes.items()} == record["schema"], "producer schema rehydration differs")
    return restored


def check_packet_records(packet, stage):
    """No alternative paths, cross-gate records, partials, or replaced bytes."""
    key = tuple(packet["key"])
    product, interval, touch, gate_id = key
    for role in ("technical", "events", "outcomes"):
        record = packet[role]
        require(record["role"] == role and key_of(record) == key, "packet role/gateway metadata differs")
        if role == "outcomes":
            require(record["period_id"] == "development", "adopted outcomes outside development")
            expected = f"ledgers/stage3/development/{product}_{interval}_{touch}_{gate_id}_outcomes.parquet"
            require(record["path"] == expected, "adopted outcome path differs from original namespace")
            verify_record(record, stage)
            original = packet["original_outcomes"]
            require(Path(original["path"]).is_absolute(), "original outcome pin must be absolute")
            verify_record(original)
            require((record["bytes"], record["sha256"]) == (original["bytes"], original["sha256"]),
                    "adopted outcome bytes differ from original packet")
        else:
            require(record["period"] == "development" and record["gate"] == packet["gate"], "adopted acceptance scope differs")
            require(Path(record["path"]).is_absolute(), "original acceptance pin must be absolute")
            require(Path(record["path"]).name == f"{product}_{interval}m_{touch}_{gate_id}_{role}.parquet",
                    "adopted acceptance filename differs")
            verify_record(record)


def reconstruct_payload(full, technical, events, key, gate, cfg):
    """Restore the original full technical schema by a strict ordinal join."""
    product, interval, touch, gate_id = key
    causal = full.loc[full.available_at.le(boundary(cfg["periods"]["development"]["end"]))].reset_index(drop=True)
    require(len(causal) == len(technical), "compact technical does not cover complete causal prefix")
    require(not technical.timestamp.duplicated().any() and technical.timestamp.is_monotonic_increasing,
            "compact technical roster must be unique and ordered")
    for column in ("timestamp", "product", "interval_minutes"):
        pd.testing.assert_series_equal(causal[column], technical[column], check_names=True, check_exact=True)
    require(np.array_equal(technical.signal_idx.to_numpy(), np.arange(len(causal))), "causal global ordinal drift")
    for column, value in (("product", product), ("interval_minutes", interval), ("touch_mode", touch),
                          ("gate_id", gate_id), ("gate_family", gate["family"]), ("gate_threshold", gate["threshold"])):
        require(technical[column].eq(value).all() and events[column].eq(value).all(), "saved scientific gateway values differ")
    restored = causal.copy()
    for column in technical:
        restored[column] = technical[column]
    require(list(restored) == list(causal) + [c for c in technical if c not in causal], "linked technical column order differs")
    accepted = restored.loc[restored.accepted].reset_index(drop=True)
    require(len(accepted) == len(events) and not events.event_id.duplicated().any(), "accepted event support differs")
    shared = [c for c in restored if c in events]
    pd.testing.assert_frame_equal(accepted[shared], events[shared].reset_index(drop=True), check_exact=True)
    require(events.reference_price.equals(events.close) and events.entry_at.equals(events.available_at), "saved entry timing/reference differs")
    return dict(bars=full, technical=restored, events=events, product=product,
                interval_minutes=interval, touch_mode=touch, gate=gate)


def rebuild_audit(outcomes, payload, cfg):
    """Reproduce original audit rows from masks and saved outcomes, no scorer."""
    masks_all, rows = [], []
    for period in scoring_periods(cfg, "development"):
        masks, audit = event_masks(payload["bars"], payload["events"], cfg["horizons"], period)
        gate = payload["gate"]
        masks["gate_id"], masks["gate_family"], masks["gate_threshold"] = gate["gate_id"], gate["family"], float(gate["threshold"])
        masks["touch_mode"], masks["stage"], masks["split"] = payload["touch_mode"], 3, "development"
        masks["interval_minutes"] = int(payload["interval_minutes"])
        masks_all.append(masks)
        for h in cfg["horizons"]:
            part = outcomes.loc[outcomes.fold_id.eq(period.fold_id) & outcomes.horizon.eq(h)]
            row = _key(payload, "development", h) | audit | dict(accepted=len(part), start_embargo=int(part.start_embargo.sum()),
                endpoint_purge=int(part.endpoint_purge.sum()), atr_support_missing=int((part.score_eligible & ~part.atr_support).sum()),
                excluded_start_embargo=int(part.mask_reason.eq("start_embargo").sum()),
                excluded_endpoint_purge=int(part.mask_reason.eq("period_endpoint_purge").sum()),
                scoring_accepted=int(part.score_eligible.sum()), completed=int(part.status.eq("completed").sum()),
                censored=int(part.status.eq("censored").sum()), excluded=int(part.status.eq("excluded").sum()))
            row["row_id"] = _id(row, ("fold_id",))
            rows.append(row)
    nonempty = [frame for frame in masks_all if len(frame)]
    expected = pd.concat(nonempty, ignore_index=True) if nonempty else masks_all[0].copy()
    require(set(expected).issubset(outcomes), "saved outcomes missing event/mask columns")
    pd.testing.assert_frame_equal(expected, outcomes[list(expected)].reset_index(drop=True), check_exact=True)
    require(not outcomes.duplicated(["gate_id", "event_id", "horizon"]).any(), "duplicate saved outcome key")
    require(outcomes.status.isin(("completed", "censored", "excluded")).all(), "unknown saved outcome status")
    require(outcomes.loc[~outcomes.score_eligible, "status"].eq("excluded").all(), "masked path status differs")
    return pd.DataFrame(rows)


def adopted_chunk(stage, cfg, packet, full):
    check_packet_records(packet, stage)
    technical, events = read_frame(packet["technical"]), read_frame(packet["events"])
    payload = reconstruct_payload(full, technical, events, tuple(packet["key"]), packet["gate"], cfg)
    decoded = read_frame(packet["outcomes"], stage)
    original_record = packet["outcomes"] | dict(path=packet["original_outcomes"]["path"])
    original_decoded = read_frame(original_record)
    pd.testing.assert_frame_equal(decoded, original_decoded, check_exact=True)
    outcomes = producer_frame(decoded, packet["outcomes"])
    audit = rebuild_audit(outcomes, payload, cfg)
    return dict(key=tuple(packet["key"]), record=packet["outcomes"],
        scorecard=summaries(outcomes, payload, "development", cfg["horizons"]),
        quantiles=quantiles(outcomes, payload, "development", cfg["horizons"]),
        stability=stability(outcomes, payload, "development", cfg), audit=audit,
        folds=fold_records(outcomes, packet["gate"], payload["product"], payload["interval_minutes"], payload["touch_mode"],
                           [fold["id"] for fold in cfg["development_folds"]]), flow=_flow(payload, "development", cfg))


def checkpoint(stage, chunk, dependency):
    """Exclusive durable typed frame bundle, with its exact input dependency."""
    key = tuple(chunk["key"])
    name = "_".join(map(str, key))
    directory = Path(stage) / "provenance/recovery-checkpoints"
    directory.mkdir(parents=True, exist_ok=True)
    path, receipt_path = directory / (name + ".pickle"), directory / (name + ".json")
    require(not path.exists() and not receipt_path.exists(), "recovery checkpoint overwrite refused")
    require(set(chunk) == {"key", "record", *FRAME_KEYS}, "exact original development chunk fields required")
    with path.open("xb") as stream:
        pickle.dump(chunk, stream, protocol=5)
        stream.flush()
        os.fsync(stream.fileno())
    record = file_record(path, Path(stage))
    write_once(receipt_path, dict(status="passed", key=list(key), dependency=dependency,
        records=[record], external_records=[], frame_schemas={k: {c: str(t) for c, t in chunk[k].dtypes.items()} for k in FRAME_KEYS},
        frame_rows={k: len(chunk[k]) for k in FRAME_KEYS}))
    return file_record(receipt_path, Path(stage))


def load_checkpoint(stage, receipt_record, dependency):
    receipt_path = verify_record(receipt_record, Path(stage))
    receipt = pinned_receipt(receipt_path, Path(stage))
    require(receipt["dependency"] == dependency, "checkpoint input/source dependency differs")
    path = verify_record(receipt["records"][0], Path(stage))
    # Only the locally written hash-pinned checkpoint is deserialized.
    with path.open("rb") as stream:
        chunk = pickle.load(stream)
    require(list(chunk["key"]) == receipt["key"] and set(chunk) == {"key", "record", *FRAME_KEYS}, "checkpoint gateway/fields differ")
    for k in FRAME_KEYS:
        require(isinstance(chunk[k], pd.DataFrame) and len(chunk[k]) == receipt["frame_rows"][k] and
                {c: str(t) for c, t in chunk[k].dtypes.items()} == receipt["frame_schemas"][k], "checkpoint frame schema differs")
    return chunk


def scientific_identity(stage, source_stage, cfg):
    original = json.loads((source_stage / "config.json").read_text())
    remove = {"protocol_version", "development_recovery"}
    require({k: v for k, v in original.items() if k not in remove} == {k: v for k, v in cfg.items() if k not in remove},
            "recovery changed scientific configuration")
    old = json.loads((source_stage / "provenance/source-inventory.json").read_text())["sources"]
    new = json.loads((stage / "provenance/source-inventory.json").read_text())["sources"]
    prefix = "studies/21_ema_cloud_trend_follow_opportunity/src/"
    for name in KERNELS:
        a = next(r for r in old if r["workspace_path"] == prefix + name)
        b = next(r for r in new if r["workspace_path"] == prefix + name)
        require((a["sha256"], a["bytes"]) == (b["sha256"], b["bytes"]), "frozen scientific kernel differs: " + name)
        verify_record(dict(path=str(source_stage / a["snapshot_path"]), sha256=a["sha256"], bytes=a["bytes"]))


def require_prefrozen_inputs(freeze, stage, source_stage, adopted, mapped):
    """All reused packet and method identities precede missing-gate scoring."""
    bound = generic_pins(freeze, stage)
    critical = [source_stage / "config.json", source_stage / "provenance/source-inventory.json",
                source_stage / "provenance/parallel-development-before.json", Path(__file__),
                stage / "provenance/adopted-recovery-packets.json"]
    old_sources = json.loads((source_stage / "provenance/source-inventory.json").read_text())["sources"]
    prefix = "studies/21_ema_cloud_trend_follow_opportunity/src/"
    for name in KERNELS:
        source = next(r for r in old_sources if r["workspace_path"] == prefix + name)
        critical.append(source_stage / source["snapshot_path"])
    for packet in adopted.values():
        critical.extend(Path(packet[role]["path"]) for role in ("technical", "events", "original_outcomes"))
        critical.append(stage / packet["outcomes"]["path"])
    critical.extend(Path(r["path"]) for r in mapped + freeze["cell_manifests"])
    require({str(path.resolve()) for path in critical} <= bound, "complete source/packet/input identities must be frozen before recovery scoring")


def deduplicated_pins(stage, paths):
    local, external, seen = [], [], set()
    for value in paths:
        path = Path(value).resolve()
        if str(path) in seen:
            continue
        seen.add(str(path))
        if path.is_relative_to(Path(stage).resolve()):
            local.append(file_record(path, Path(stage).resolve()))
        else:
            external.append(file_record(path))
    return local, external


def recover_development(output_stage, cfg, authorization, recovery_freeze):
    """Production-only adopted187 + missing5, complete192, one global close."""
    from run_stage3 import gateway_iterator
    stage = Path(output_stage).resolve()
    require(authorization is not None and authorization.period == "development" and Path(authorization.stage).resolve() == stage,
            "explicit matching development phase authorization required")
    require(json.loads((stage / "config.json").read_text()) == cfg, "saved frozen recovery settings differ")
    freeze_path = Path(recovery_freeze).resolve()
    require(freeze_path == stage / "provenance/development-recovery-freeze.json", "canonical new-run recovery freeze required")
    assert_frozen(stage, authorization.workspace)
    assert_input_bytes(stage)
    assert_numerical_gate(stage)
    freeze = pinned_receipt(freeze_path, stage)
    require(freeze["schema_version"] == SCHEMA and Path(freeze["output_stage"]).resolve() == stage and
            Path(freeze["workspace"]).resolve() == Path(authorization.workspace).resolve(), "recovery freeze scope differs")
    source_stage = Path(freeze["source_stage"]).resolve()
    require(source_stage != stage and source_stage.name == cfg["development_recovery"]["adopted_attempt_id"], "explicit unique adopted attempt required")
    adoption_path = stage / "provenance/adopted-recovery-packets.json"
    pinned_receipt(adoption_path, stage)
    require(str(adoption_path) in generic_pins(freeze, stage), "adoption receipt must be frozen before execution")
    scientific_identity(stage, source_stage, cfg)
    expected, adopted, missing = packet_plan(cfg, freeze, authorization.gates)
    require(len(expected) == 192 and len(adopted) == 187 and len(missing) == 5, "exact production recovery192/187/5 required")
    for key in expected:
        authorization.validate("development", *key)
    require(not (stage / "stage3-development.manifest.json").exists() and not (stage / "acceptance-development.manifest.json").exists(),
            "recovery global phase overwrite refused")
    require(not (stage / "tables").exists() or not list((stage / "tables").glob("S3-*development*")), "fresh global development table namespace required")
    require({p.name for p in (stage / "ledgers/stage3/development").glob("*.parquet")} ==
            {Path(packet["outcomes"]["path"]).name for packet in adopted.values()}, "unexpected/partial/missing adopted outcome namespace")
    mapped = json.loads((stage / "mapped.manifest.json").read_text())["records"]
    require(mapped == freeze["mapped"], "original common mapped pins differ")
    require(len(mapped) == 6 and {(r["product"], int(r["interval_minutes"])) for r in mapped} == {(k[0], k[1]) for k in expected},
            "complete six-cell common mapped inventory required")
    mapped_by_cell = {(r["product"], int(r["interval_minutes"])): r for r in mapped}
    for packet in adopted.values():
        check_packet_records(packet, stage)
    require_prefrozen_inputs(freeze, stage, source_stage, adopted, mapped)
    require(len(freeze["cell_manifests"]) == 5, "five complete original cell manifests required")
    original_acceptance = {}
    for record in freeze["cell_manifests"]:
        require(Path(record["path"]).is_absolute(), "original cell manifest must be absolute")
        manifest = json.loads(verify_record(record).read_text())
        require(manifest["period"] == "development" and manifest["schema_version"] == "study21.stage3-acceptance/v1", "original cell manifest scope differs")
        bars = [r for r in manifest["records"] if r["role"] == "bars"]
        require(len(bars) == 1, "one original common mapped cell record required")
        cell = bars[0]["product"], int(bars[0]["interval_minutes"])
        require(bars[0] == mapped_by_cell[cell], "original cell common mapped pin differs")
        ordered = [k for k in expected if k[:2] == cell]
        require(len(ordered) == 32 and all(k in adopted for k in ordered), "original manifest must cover a complete adopted cell")
        require(manifest["records"] == [mapped_by_cell[cell]] + [adopted[k][r] for k in ordered for r in ("technical", "events")],
                "original complete cell role/gate order differs")
        for item in manifest["records"]:
            if item["role"] != "bars":
                ident = key_of(item), item["role"]
                require(ident not in original_acceptance, "duplicate original complete-cell record")
                original_acceptance[ident] = item
    require(len(original_acceptance) == 320, "five complete original32-gateway cell inventories required")
    for (key, role), record in original_acceptance.items():
        require(key in adopted and adopted[key][role] == record, "packet differs from original complete-cell manifest")
    before_paths = [freeze_path, adoption_path, Path(__file__), stage / "config.json", stage / "mapped.manifest.json",
                    stage / "provenance/source-inventory.json", stage / "provenance/execution-freeze.json", stage / "provenance/stage3-numerical.json"]
    before_paths += [verify_record(r, stage) for r in freeze.get("records", [])]
    before_paths += [verify_record(r) for r in freeze.get("external_records", [])]
    for packet in adopted.values():
        before_paths += [verify_record(packet[r], stage if r == "outcomes" else None) for r in ("technical", "events", "outcomes")]
        before_paths.append(verify_record(packet["original_outcomes"]))
    before_paths += [verify_record(r) for r in mapped + freeze["cell_manifests"]]
    local, external = deduplicated_pins(stage, before_paths)
    before_path = stage / "provenance/development-recovery-before.json"
    write_once(before_path, dict(status="passed", phase="development", created_at_utc=datetime.now(timezone.utc).isoformat(),
        gateway_count=192, adopted_count=187, missing_count=5, records=local, external_records=external,
        execution=dict(argv=[sys.executable, *sys.argv], cwd=os.getcwd(), environment={k: os.environ[k] for k in
            ("OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "UV_CACHE_DIR", "PYTHONPATH") if k in os.environ}),
        disposition="Reuse exact source-frozen adopted packets without rescoring; score only missing five; reconstruct original typed descriptive frames and close once in original192 order."))
    dependency = file_record(before_path, stage)
    start = time.perf_counter()
    checkpoint_records, acceptance_by_gate, consumed = [], {}, list(before_paths) + [before_path]
    try:
        # Missing gates execute first in fresh namespaces. Each yielded packet
        # uses the unchanged full causal iterator and original phase scorer.
        missing_manifest = stage / "provenance/recovery-missing-acceptance.manifest.json"
        seen = []
        for payload in gateway_iterator(stage, "development", list(missing), cell=("NQ", 3), manifest_path=missing_manifest):
            key = payload["product"], int(payload["interval_minutes"]), payload["touch_mode"], payload["gate"]["gate_id"]
            require(key in missing and key not in seen, "unexpected missing recovery gateway")
            seen.append(key)
            chunk = stream_chunk(stage, cfg, payload, authorization)
            checkpoint_records.append(checkpoint(stage, chunk, dependency))
        require(tuple(seen) == missing and missing_manifest.is_file(), "missing gateway execution incomplete or reordered")
        new_acceptance = json.loads(missing_manifest.read_text())
        require(new_acceptance["schema_version"] == "study21.stage3-acceptance/v1" and new_acceptance["period"] == "development"
                and new_acceptance["records"][0] == mapped_by_cell[("NQ", 3)], "new missing acceptance common input/scope differs")
        for record in new_acceptance["records"]:
            if record["role"] != "bars":
                identity = key_of(record), record["role"]
                require(identity not in acceptance_by_gate and identity[0] in missing, "duplicate/outside missing acceptance record")
                acceptance_by_gate[identity] = record
        require(set(acceptance_by_gate) == {(k, r) for k in missing for r in ("technical", "events")}, "complete missing acceptance role pairs required")
        require(new_acceptance["records"] == [mapped_by_cell[("NQ", 3)]] + [acceptance_by_gate[(k, r)] for k in missing for r in ("technical", "events")],
                "missing acceptance original gateway/role order differs")
        # Reconstruct one original per-gate bundle at a time. Whole scientific
        # frames remain separate through final concatenation and dtype inference.
        for cell in ((p, int(i)) for p in cfg["products"] for i in cfg["interval_minutes"]):
            full = read_frame(mapped_by_cell[cell])
            for key in expected:
                if key[:2] != cell or key not in adopted:
                    continue
                packet = adopted[key]
                chunk = adopted_chunk(stage, cfg, packet, full)
                checkpoint_records.append(checkpoint(stage, chunk, dependency))
                for role in ("technical", "events"):
                    acceptance_by_gate[(key, role)] = packet[role]
                print(json.dumps(dict(recovery_phase="development", gateway=list(key), disposition="adopted_bytes_descriptive_checkpoint")), flush=True)
        checkpoint_by_key = {}
        for record in checkpoint_records:
            receipt = json.loads(verify_record(record, stage).read_text())
            key = tuple(receipt["key"])
            require(key not in checkpoint_by_key, "duplicate recovery checkpoint")
            checkpoint_by_key[key] = record
            consumed += [stage / record["path"], stage / receipt["records"][0]["path"]]
        require(set(checkpoint_by_key) == set(expected), "incomplete192 checkpoints; global close refused")
        chunks = [load_checkpoint(stage, checkpoint_by_key[key], dependency) for key in expected]
        validate_outcome_records(stage, chunks)
        directory = stage / "provenance/cell-acceptance/development"
        directory.mkdir(parents=True, exist_ok=False)
        results = []
        for ordinal, item in enumerate(cell_plan(cfg, authorization.gates)):
            cell = item["cell"]
            records = [mapped_by_cell[cell]] + [acceptance_by_gate[(key, role)] for key in item["gates"] for role in ("technical", "events")]
            path = directory / f"{cell[0]}_{cell[1]}.manifest.json"
            write_once(path, dict(schema_version="study21.stage3-acceptance/v1", period="development", records=records,
                source_attribution="Explicit recovery: original adopted acceptance pins and new-run missing gateway pins, joined to unchanged mapped roster."))
            results.append(dict(cell=cell, acceptance_manifest=file_record(path, stage)))
            consumed.append(path)
        acceptance = acceptance_records(stage, mapped, results, expected)
        generic_pins(json.loads(before_path.read_text()), stage)
        assert_frozen(stage, authorization.workspace)
        assert_input_bytes(stage)
        assert_numerical_gate(stage)
        for key in expected:
            authorization.validate("development", *key)
        write_once(stage / "acceptance-development.manifest.json", dict(schema_version="study21.stage3-acceptance/v1", period="development", records=acceptance,
            technical_scope="Causal 2017-to-phase-end prefix; state fields joined to full input-only bars by timestamp; no outcome eligibility changes acceptance.",
            recovery_disposition="187 byte-identical adopted packets; five freshly executed missing packets; no adopted outcome rescoring."))
        result = close_development(stage, cfg, chunks, expected)
        assert_frozen(stage, authorization.workspace)
        assert_input_bytes(stage)
        generic_pins(json.loads(before_path.read_text()), stage)
        consumed += [missing_manifest, stage / "acceptance-development.manifest.json", stage / result["manifest"]["path"]]
        consumed += [stage / r["path"] for r in result["records"] + result["tables"]]
        consumed += [verify_record(r, None if Path(r["path"]).is_absolute() else stage) for r in acceptance]
        local, external = deduplicated_pins(stage, consumed)
        write_once(stage / "provenance/development-recovery-completion.json", dict(status="passed", phase="development",
            schema_version="study21.stage3-recovery-completion/v1", gateway_count=192, adopted_count=187, missing_count=5,
            runtime_seconds=time.perf_counter()-start, records=local, external_records=external,
            checkpoint_count=len(checkpoint_by_key), global_close_count=1, numerical_order="Original configured192 gateway order; unchanged original single-parent development close.",
            adopted_outcomes_scored=False, missing_gateways_scored=[list(k) for k in missing]))
        return result
    except BaseException as error:
        write_once(stage / "provenance/development-recovery-failure.json", dict(status="failed_partial_artifacts_preserved", phase="development",
            error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(), runtime_seconds=time.perf_counter()-start,
            qualification="Partial recovery/checkpoints preserved; no shortlist or later authorization without complete independent development verification."))
        raise
