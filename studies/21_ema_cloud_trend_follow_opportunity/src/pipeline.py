"""Explicit saved-evidence phases and immutable sealing for Study 21 only."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pandas as pd

from .execution import assert_frozen_sources, file_record, sha256, verify_record, write_json


def _read(stage: Path, role: str) -> pd.DataFrame:
    records = json.loads((stage / "events.manifest.json").read_text())["records"]
    return pd.concat([pd.read_parquet(verify_record(record)) for record in records
                      if record["role"] == role], ignore_index=True)


def _coverage_columns(table: pd.DataFrame, technical: pd.DataFrame) -> pd.DataFrame:
    """Attach audited signal-time support; missing feature coverage isn't zero."""
    from .engine import _strata
    tech = _strata(technical.copy())
    tech = tech.loc[tech.year.between(2018, 2020)]
    tech["eligible"] = tech.usable.fillna(False) & tech.feature_valid.fillna(False)
    parts = []
    for kind in table.period_kind.unique():
        for side in ("All", "Buy", "Sell"):
            subset = tech if side == "All" else tech.loc[tech.side.eq(side)]
            grouped = subset.groupby(["product", "interval_minutes", kind], observed=True).agg(
                scheduled_slots=("timestamp", "size"), eligible_slots=("eligible", "sum")).reset_index()
            grouped = grouped.rename(columns={kind: "period"})
            grouped["period"] = grouped.period.astype(str)
            grouped["direction"], grouped["period_kind"] = side, kind
            parts.append(grouped)
    support = pd.concat(parts, ignore_index=True)
    result = table.merge(support, on=["product", "interval_minutes", "direction", "period_kind", "period"],
                         how="left", validate="many_to_one")
    for column in ("scheduled_slots", "eligible_slots"):
        result[column] = result[column].fillna(0).astype(int)
    result["unknown_signal_slots"] = result.scheduled_slots - result.eligible_slots
    result["coverage_complete"] = result.scheduled_slots.gt(0) & result.unknown_signal_slots.eq(0)
    result["zero_event_qualification"] = "events_observed"
    result.loc[result.accepted.eq(0) & result.eligible_slots.gt(0), "zero_event_qualification"] = "auditable_eligible_support"
    result.loc[result.accepted.eq(0) & result.eligible_slots.eq(0), "zero_event_qualification"] = "no_eligible_support"
    return result


def _selected_paths(stage: Path, examples: pd.DataFrame) -> Path:
    records = json.loads((stage / "events.manifest.json").read_text())["records"]
    rows = []
    for product in ("ES", "GC", "NQ"):
        for interval in (3, 5):
            record = next(r for r in records if r["product"] == product and r["interval_minutes"] == interval and r["role"] == "technical")
            bars = pd.read_parquet(verify_record(record))
            selections = examples.loc[examples["product"].eq(product) & examples.interval_minutes.eq(interval)
                                      & examples.selection_status.eq("selected")]
            for selection in selections.to_dict("records"):
                index = int(selection["signal_idx"])
                selected = bars.iloc[max(0, index - 10):index + 16].copy()
                local = selected.timestamp.dt.tz_convert("America/New_York")
                selected = selected.loc[local.dt.year.between(2018, 2020)]
                for candle in selected.to_dict("records"):
                    rows.append({"row_id": selection["selection_id"] + "|slot=" + str(int(candle["signal_idx"]) - index),
                                 "selection_id": selection["selection_id"], "event_id": selection["event_id"],
                                 "product": product, "interval_minutes": interval,
                                 "example_class": selection["example_class"],
                                 "relative_slot": int(candle["signal_idx"]) - index,
                                 "timestamp": candle["timestamp"], "available_at": candle["available_at"],
                                 **{key: candle[key] for key in ("open", "high", "low", "close", "ema20", "ema50", "usable")},
                                 "reference_price": selection["reference_price"] if pd.notna(selection["reference_price"]) else bars.iloc[index].close,
                                 "status": candle["quality_reason"], "contract_id": candle["contract"]})
    path = stage / "tables/selected-example-paths.parquet"
    pd.DataFrame(rows).to_parquet(path, index=False, compression="zstd")
    return path


def summarize_stage(stage: Path, workspace: Path) -> None:
    from .statistics import bootstrap, comparisons, quantiles, signal_flow, stability, summarize
    from .reporting import TABLES, select_examples
    assert_frozen_sources(stage, workspace)
    if (stage / "metrics.json").exists():
        raise ValueError("saved metrics overwrite refused")
    outcomes, events, technical = (_read(stage, role) for role in ("outcomes", "events", "technical"))
    tables = stage / "tables"
    tables.mkdir(exist_ok=True)
    coverage = pd.read_csv(stage / "data-preparation/coverage.csv")
    decision_coverage = pd.read_csv(stage / "data-preparation/decision-coverage.csv")
    coverage = coverage.merge(decision_coverage[["product", "interval_minutes", "year", "mapped_ready_slots", "ready_share", "ready_sessions"]],
                              on=["product", "interval_minutes", "year"], how="left", validate="one_to_one")
    coverage["feature_ready_slots"] = coverage.mapped_ready_slots.combine_first(coverage.feature_ready_slots)
    flow = signal_flow(technical, events, outcomes)
    score = summarize(outcomes, supports=("all", "same_session", "uninterrupted"))
    uncertainty = bootstrap(outcomes)
    ci = uncertainty.loc[uncertainty.kind.eq("cohort") & uncertainty.metric.eq("terminal_delta") &
                         uncertainty.weighting.eq("event") & uncertainty.block_weeks.eq(4),
                         ["product", "interval_minutes", "direction", "horizon", "unit", "support", "ci_low", "ci_high"]]
    score = score.merge(ci.rename(columns={"ci_low": "ci95_low", "ci_high": "ci95_high"}),
                        on=["product", "interval_minutes", "direction", "horizon", "unit", "support"], how="left", validate="one_to_one")
    dev_tech = technical.loc[technical.timestamp.dt.tz_convert("America/New_York").dt.year.between(2018, 2020)]
    strata = _coverage_columns(stability(outcomes, session_roster=sorted(dev_tech.session.astype(str).unique())), technical)
    examples = select_examples(technical, events, outcomes)
    outputs = {"S1-T00": coverage, "S1-T01": flow, "S1-T02": score, "S1-T03": quantiles(outcomes),
               "S1-T04": strata.loc[~strata.period_kind.isin(["week", "month"])],
               "S1-T05": strata.loc[strata.period_kind.isin(["week", "month"])], "S1-T06": examples}
    for key, frame in outputs.items():
        frame.to_csv(tables / TABLES[key], index=False, float_format="%.17g")
    uncertainty.to_csv(tables / "S1-bootstrap.csv", index=False, float_format="%.17g")
    comparisons(outcomes).to_csv(tables / "S1-comparisons.csv", index=False, float_format="%.17g")
    _selected_paths(stage, examples)
    write_json(stage / "metrics.json", {"study_id": "21_ema_cloud_trend_follow_opportunity", "run_id": stage.name,
               "stage": 1, "results": "development_price_paths", "reserved_outcomes_computed": False,
               "accepted_events": len(events), "outcome_rows": len(outcomes),
               "source_tables": [file_record(tables / TABLES[key], stage) for key in TABLES],
               "estimator_definitions": "protocol.md and config.json",
               "numerical_values": "Exact tables are authoritative; stable row_id selectors identify every estimate."})
    exclusions = {"signal_suppression_counts": {str(k): int(v) for k, v in technical.suppression_reason.value_counts().items()},
                  "outcome_censor_counts": {str(k): int(v) for k, v in outcomes.loc[outcomes.status.eq("censored"), "censor_reason"].value_counts().items()},
                  "calendar": "data-preparation/calendar-exclusions.csv", "scope": "Path exclusions occur after acceptance; primary development tables preserve per-horizon denominators."}
    write_json(stage / "exclusions.json", exclusions)
    assert_frozen_sources(stage, workspace)


def render_stage(stage: Path, workspace: Path) -> None:
    from .reporting import render_bundle
    assert_frozen_sources(stage, workspace)
    receipt = render_bundle(stage, stage.name, example_paths=stage / "tables/selected-example-paths.parquet")
    write_json(stage / "provenance/render-receipt.json", receipt)
    if (stage / "source-bindings.json").exists():
        shutil.copyfile(stage / "source-bindings.json", stage / "publication-source-map.json")
    assert_frozen_sources(stage, workspace)


def verify_stage(stage: Path, workspace: Path) -> None:
    from .reconcile import verify_bundle
    assert_frozen_sources(stage, workspace)
    receipt = verify_bundle(stage)
    write_json(stage / "provenance/scientific-reconciliation.json", receipt)
    if receipt.get("status") not in ("passed", "verified"):
        raise ValueError("scientific reconciliation did not pass")
    records = json.loads((stage / "events.manifest.json").read_text())["records"]
    for record in records:
        verify_record(record)
    write_json(stage / "provenance/external-bytes.json", {"status": "passed", "verified": len(records),
               "events_manifest": file_record(stage / "events.manifest.json", stage),
               "records": [{key: r[key] for key in ("path", "sha256", "bytes", "row_count", "role", "product", "interval_minutes")} for r in records],
               "scope": "Explicit retained external ledger bytes, not backup verification."})


def build_manifest(stage: Path) -> dict:
    inventory = json.loads((stage / "provenance/source-inventory.json").read_text())
    paths = sorted(p for p in stage.rglob("*") if p.is_file() and p != stage / "manifest.json"
                   and "__pycache__" not in p.parts)
    external = json.loads((stage / "events.manifest.json").read_text())["records"]
    return {"contract": "abacus.evidence/v1", "bundle_kind": "research",
            "study_id": "21_ema_cloud_trend_follow_opportunity", "run_id": stage.name,
            "inventory_scope": "declared_artifacts", "results": {"kind": "quantitative", "state": "computed",
                "artifacts": ["metrics.json", "report.md", "report.html", "publication.json"]},
            "provenance": {"settings": "config.json", "input_lock": "inputs.lock.json", "exclusions": "exclusions.json",
                "commands": "provenance/commands.json", "checks": "provenance/checks.json", "environment_lock": "provenance/uv.lock",
                "code": {"revision": inventory["revision"], "dirty": inventory["dirty"], "status": "provenance/git-status.txt",
                         "source_snapshot": {"paths": [r["snapshot_path"] for r in inventory["sources"]], "scope": inventory["scope"]}}},
            "artifacts": [file_record(path, stage) for path in paths],
            "external_artifacts": [{"id": f"{r['product']}-{r['interval_minutes']}m-{r['role']}", "locator": r["path"],
                                    "bytes": r["bytes"], "sha256": r["sha256"]} for r in external]}


def seal_stage(stage: Path, workspace: Path) -> None:
    assert_frozen_sources(stage, workspace)
    checks = json.loads((stage / "provenance/checks.json").read_text())
    required = {"study21-numerical", "bhishma-ema-numerical", "input-provenance", "five-minute-reconciliation",
                "scientific-reconciliation", "external-ledger-bytes", "publication-dry-run"}
    passed = {r["name"] for r in checks if r["status"] == "passed"}
    if not required.issubset(passed):
        raise ValueError("required sealing gates absent: " + str(sorted(required - passed)))
    for item in checks:
        if item["status"] in ("passed", "failed") and not (stage / item["record"]).is_file():
            raise ValueError("check evidence missing")
    write_json(stage / "manifest.json", build_manifest(stage))
    sys.path.insert(0, str(workspace / "scripts"))
    from evidence_contract import assess_bundle
    assessment = assess_bundle(stage)
    if assessment["status"] != "verified_declared_artifacts":
        raise ValueError("bundle integrity failed: " + json.dumps(assessment))
    for r in json.loads((stage / "events.manifest.json").read_text())["records"]:
        verify_record(r)
    destination = workspace / "runs/21_ema_cloud_trend_follow_opportunity" / stage.name
    if destination.exists():
        raise ValueError("completed destination exists")
    destination.parent.mkdir(exist_ok=True, parents=True)
    shutil.move(str(stage), destination)
    print(json.dumps({"status": "sealed", "run": str(destination), "integrity": assessment["status"]}), flush=True)
