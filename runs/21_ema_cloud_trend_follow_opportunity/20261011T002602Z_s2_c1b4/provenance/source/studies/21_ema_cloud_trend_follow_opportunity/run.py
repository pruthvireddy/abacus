"""Execute only the frozen Stage 1 development study into a fresh work stage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

import pandas as pd

from abacus_bhishma.paths import load_workspace_paths
from src.execution import (assert_frozen_sources, assert_numerical_gate, assert_stage, file_record,
                           record_command, sha256, snapshot_sources, verify_record,
                           write_json)

STUDY_ID = "21_ema_cloud_trend_follow_opportunity"
STUDY = Path(__file__).resolve().parent
WORKSPACE = STUDY.parents[1]


def freeze(stage: Path) -> None:
    if not (stage / "inputs.lock.json").is_file():
        raise ValueError("audited input lock required before freeze")
    if (stage / "execution.json").exists():
        raise ValueError("already executed stage")
    shutil.copyfile(STUDY / "config-stage1.json", stage / "config.json")
    shutil.copyfile(STUDY / "protocol-stage1.md", stage / "protocol.md")
    snapshot_sources(stage, WORKSPACE, STUDY)


def _save_ledger(frame: pd.DataFrame, path: Path, role: str, product: str, interval: int) -> dict:
    if path.exists():
        raise ValueError("ledger overwrite refused")
    frame.to_parquet(path, index=False, compression="zstd")
    return {**file_record(path), "role": role, "product": product,
            "interval_minutes": interval, "row_count": len(frame),
            "schema": {column: str(dtype) for column, dtype in frame.dtypes.items()},
            "retention_status": "retained_local_external_research_evidence_backup_not_certified"}


def audit(stage: Path) -> None:
    """Inspect all six decision rosters without signals or forward paths."""
    from abacus_bhishma.ema_cloud import load_release
    from src.engine import map_features
    assert_frozen_sources(stage, WORKSPACE)
    paths = load_workspace_paths(WORKSPACE)
    delivery = json.loads((stage / "inputs.lock.json").read_text())["delivery"]
    verify_record(delivery, paths.publication_root)
    rows = []
    for product in ("ES", "GC", "NQ"):
        five = load_release(paths.publication_root, product=product, interval=5,
            manifest_path=delivery["path"], expected_manifest_sha256=delivery["sha256"])
        for interval in (3, 5):
            bars = five if interval == 5 else load_release(paths.publication_root, product=product, interval=3,
                manifest_path=delivery["path"], expected_manifest_sha256=delivery["sha256"])
            mapped = map_features(bars, five, interval)
            mapped["year"] = mapped.timestamp.dt.tz_convert("America/New_York").dt.year
            for year, group in mapped.loc[mapped.year.between(2018, 2020)].groupby("year"):
                ready = group.usable & group.feature_valid
                rows.append({"product": product, "interval_minutes": interval, "year": int(year),
                             "scheduled_slots": len(group), "usable_slots": int(group.usable.sum()),
                             "mapped_ready_slots": int(ready.sum()), "ready_share": float(ready.mean()),
                             "ready_sessions": group.loc[ready, "session"].nunique()})
    frame = pd.DataFrame(rows)
    frame.to_csv(stage / "data-preparation/decision-coverage.csv", index=False, float_format="%.17g")
    if any(frame.groupby(["product", "interval_minutes"]).mapped_ready_slots.sum().eq(0)):
        raise ValueError("essential feature support absent; no outcomes may be scored")
    write_json(stage / "provenance/decision-coverage.json", {"status": "passed", "signals_computed": False,
        "outcomes_computed": False, "policy_relaxed": False,
        "coverage": file_record(stage / "data-preparation/decision-coverage.csv", stage),
        "input_lock": file_record(stage / "inputs.lock.json", stage),
        "source_inventory": file_record(stage / "provenance/source-inventory.json", stage),
        "qualification": "Conservative warmup/calendar support retained as frozen; no minimum event support is inferred before scoring."})
    print(frame.to_string(index=False), flush=True)


def development_slice(stage: Path) -> None:
    """Fixed June 4–15, 2018 reconciliation, before full development scoring."""
    from abacus_bhishma.ema_cloud import load_release
    from src.engine import generate_events, map_features
    from src.outcomes import score_outcomes
    from src.reconcile import reconcile_outcomes, reconcile_signals
    assert_frozen_sources(stage, WORKSPACE)
    assert_numerical_gate(stage)
    if (stage / "provenance/development-slice.json").exists():
        raise ValueError("slice diagnostic overwrite refused")
    config = json.loads((stage / "config.json").read_text())
    paths = load_workspace_paths(WORKSPACE)
    delivery = json.loads((stage / "inputs.lock.json").read_text())["delivery"]
    destination = stage / "diagnostics/development-slice"
    destination.mkdir(parents=True, exist_ok=False)
    start, end, prefix_end = (pd.Timestamp(config[name]).tz_convert("UTC") for name in
        ("reconciliation_slice_start_ny", "reconciliation_slice_end_ny", "reconciliation_prefix_end_ny"))
    checks, artifacts = [], []
    for product in config["products"]:
        five = load_release(paths.publication_root, product=product, interval=5,
            manifest_path=delivery["path"], expected_manifest_sha256=delivery["sha256"])
        five = five.loc[five.available_at.le(prefix_end)]
        for interval in config["interval_minutes"]:
            bars = five if interval == 5 else load_release(paths.publication_root, product=product, interval=3,
                manifest_path=delivery["path"], expected_manifest_sha256=delivery["sha256"])
            bars = bars.loc[bars.available_at.le(prefix_end)]
            mapped = map_features(bars, five, interval)
            technical, all_events = generate_events(mapped, interval, config["minimum_width_points"])
            development = all_events.loc[all_events.timestamp.ge(pd.Timestamp(config["development_start_ny"]).tz_convert("UTC"))]
            checks.append(reconcile_signals(technical, development))
            events = development.loc[development.timestamp.ge(start) & development.timestamp.lt(end)]
            outcomes = score_outcomes(mapped, events, config[f"horizons_{interval}m"], interval)
            checks.append(reconcile_outcomes(technical, events, outcomes, roster_end_is_endpoint=False))
            for role, frame in (("events", events), ("outcomes", outcomes)):
                path = destination / f"{product}_{interval}m_{role}.parquet"
                frame.to_parquet(path, index=False, compression="zstd")
                artifacts.append(file_record(path, stage))
            print(json.dumps({"slice": "2018-06-04_to_2018-06-16_exclusive", "product": product,
                              "interval_minutes": interval, "accepted": len(events), "rows": len(outcomes)}), flush=True)
    write_json(stage / "provenance/development-slice.json", {"status": "passed", "checks": checks,
        "slice": [str(start), str(end)], "artifacts": artifacts,
        "source_inventory": file_record(stage / "provenance/source-inventory.json", stage),
        "input_lock": file_record(stage / "inputs.lock.json", stage),
        "scope": "Prespecified development slice; full prior causal state independently reconciled; every sample outcome checked before full scoring."})
    assert_frozen_sources(stage, WORKSPACE)


def execute(stage: Path) -> None:
    from abacus_bhishma.ema_cloud import load_release
    from src.engine import generate_events, map_features
    from src.outcomes import score_outcomes
    assert_frozen_sources(stage, WORKSPACE)
    assert_numerical_gate(stage)
    audit_receipt = json.loads((stage / "provenance/decision-coverage.json").read_text())
    if audit_receipt["status"] != "passed" or audit_receipt["outcomes_computed"]:
        raise ValueError("input-only six-cell coverage audit required before scoring")
    verify_record(audit_receipt["coverage"], stage)
    slice_receipt = json.loads((stage / "provenance/development-slice.json").read_text())
    if slice_receipt["status"] != "passed":
        raise ValueError("prespecified development slice reconciliation required")
    for record in slice_receipt["artifacts"]:
        verify_record(record, stage)
    if (stage / "execution.json").exists() or (stage / "events.manifest.json").exists():
        raise ValueError("execution overwrite refused; preserve diagnostic attempt")
    config = json.loads((stage / "config.json").read_text())
    paths = load_workspace_paths(WORKSPACE)
    lock = json.loads((stage / "inputs.lock.json").read_text())
    # The delivery adapter is intentionally narrow: exact file records and roles,
    # not arbitrary path discovery or a replacement for source-publication loaders.
    delivery = lock["delivery"]
    manifest_path = verify_record(delivery, paths.publication_root)
    manifest = json.loads(manifest_path.read_text())
    output_records = manifest["output_files"]
    if paths.legacy_research_root is None:
        raise ValueError("configured retained research root required")
    retained = (paths.legacy_research_root / "work" / STUDY_ID / stage.name).resolve()
    retained.mkdir(parents=True, exist_ok=False)
    records = []
    for product in config["products"]:
        loaded = {}
        for interval in config["interval_minutes"]:
            item = next(r for r in output_records if r["product"] == product and r["interval_minutes"] == interval)
            verify_record(item, paths.publication_root)
            loaded[interval] = load_release(paths.publication_root, product=product,
                interval=interval, manifest_path=delivery["path"],
                expected_manifest_sha256=delivery["sha256"], verify_selected_files=True)
            if not isinstance(loaded[interval], pd.DataFrame):
                loaded[interval] = loaded[interval].to_pandas()
        for interval in config["interval_minutes"]:
            mapped = map_features(loaded[interval], loaded[5], interval)
            technical, events = generate_events(mapped, interval, config["minimum_width_points"])
            start = pd.Timestamp(config["development_start_ny"]).tz_convert("UTC")
            endpoint = pd.Timestamp(config["development_endpoint_ny"]).tz_convert("UTC")
            events = events.loc[events.timestamp.ge(start) & events.timestamp.lt(endpoint)].copy()
            # Save acceptance and the full state ledger BEFORE future exclusions.
            for role, frame in (("bars", mapped), ("technical", technical), ("events", events)):
                records.append(_save_ledger(frame, retained / f"{product}_{interval}m_{role}.parquet", role, product, interval))
            outcomes = score_outcomes(mapped, events, config[f"horizons_{interval}m"], interval,
                                      development_start=start, endpoint=endpoint,
                                      roster_end_is_endpoint=True)
            records.append(_save_ledger(outcomes, retained / f"{product}_{interval}m_outcomes.parquet", "outcomes", product, interval))
            print(json.dumps({"product": product, "interval_minutes": interval,
                              "accepted": len(events), "outcome_rows": len(outcomes),
                              "completed_h15": int((outcomes.horizon.eq(15) & outcomes.status.eq("completed")).sum())}), flush=True)
    assert_frozen_sources(stage, WORKSPACE)
    write_json(stage / "events.manifest.json", {"schema_version": "study21.ledgers/v1", "study_id": STUDY_ID,
               "run_id": stage.name, "records": records,
               "reserved_outcomes_computed": False})
    write_json(stage / "evidence.manifest.json", {"records": records})
    write_json(stage / "execution.json", {"status": "computed_pending_verification",
               "source_inventory": file_record(stage / "provenance/source-inventory.json", stage),
               "input_lock": file_record(stage / "inputs.lock.json", stage),
               "settings": file_record(stage / "config.json", stage),
               "ledgers": file_record(stage / "events.manifest.json", stage),
               "reserved_outcomes_computed": False})


def load_ledgers(stage: Path, role: str) -> pd.DataFrame:
    records = json.loads((stage / "events.manifest.json").read_text())["records"]
    return pd.concat([pd.read_parquet(verify_record(r)) for r in records if r["role"] == role], ignore_index=True)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["freeze", "audit", "slice", "execute", "summarize", "render", "verify", "seal"])
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args(argv)
    stage = args.stage.resolve()
    assert_stage(stage, WORKSPACE)
    record_command(stage, [sys.executable, str(Path(__file__).resolve()), *(sys.argv[1:] if argv is None else argv)], WORKSPACE)
    if args.phase == "freeze":
        freeze(stage)
    elif args.phase == "audit":
        audit(stage)
    elif args.phase == "slice":
        development_slice(stage)
    elif args.phase == "execute":
        execute(stage)
    else:
        from src.pipeline import summarize_stage, render_stage, verify_stage, seal_stage
        {"summarize": summarize_stage, "render": render_stage,
         "verify": verify_stage, "seal": seal_stage}[args.phase](stage, WORKSPACE)


if __name__ == "__main__":
    main()
