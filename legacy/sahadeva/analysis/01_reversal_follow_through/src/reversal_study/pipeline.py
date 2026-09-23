from __future__ import annotations

import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .comparisons import paired_comparisons, select_and_freeze_candidates
from .events import detect_events
from .excursions import add_excursions_and_timing
from .ingest import (
    config_hash,
    coverage_by_date,
    geometry_summary,
    load_config,
    read_dataset,
    sha256_file,
)
from .reporting import (
    baseline_table,
    boundary_sensitivity_table,
    continuation_curve_table,
    cross_asset_summary,
    fixed_excursion_table,
    generate_figures,
    headline_table,
    movement_milestone_table,
    natural_excursion_table,
    run_tables,
    stability_table,
    threshold_table,
    write_data_quality,
    write_methodology,
    write_report,
)
from .statistics import stable_seed
from .timing import extreme_bar_table, milestone_timing_table, opportunity_table, timestamp_quality_table
from .validate import aggregate_invariants, reconciliation_sample, write_json


def make_run_id(prefix: str = "run") -> str:
    return datetime.now(timezone.utc).strftime(f"%Y%m%dT%H%M%SZ_{prefix}")


def _dirs(project_root: Path, study_id: str, run_id: str) -> tuple[Path, Path]:
    work_dir = project_root / "work" / study_id / run_id
    report_dir = project_root / "reports" / study_id / run_id
    for path in (
        work_dir / "normalized",
        work_dir / "events",
        work_dir / "diagnostics",
        report_dir / "tables",
        report_dir / "figures",
    ):
        path.mkdir(parents=True, exist_ok=False if path == work_dir / "normalized" else True)
    return work_dir, report_dir


def _audit_inventory(config: dict[str, Any], project_root: Path) -> tuple[list[pd.DataFrame], list[dict[str, Any]]]:
    bars: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    for dataset in config["datasets"]:
        if not dataset["available"]:
            audit_rows.append(
                {
                    "asset": dataset["asset"],
                    "contract": dataset["contract"],
                    "range_setting": dataset["range"],
                    "source_file": None,
                    "source_path": None,
                    "status": "missing",
                    "reason": "Requested dataset not found; no substitution made",
                    "chart_identity_status": config["chart_identity_status"],
                    "timing_status": config["timing_status"],
                }
            )
            continue
        frame, audit = read_dataset(dataset, config, project_root)
        audit["status"] = "analyzed"
        audit["reason"] = "Requested and available"
        bars.append(frame)
        audit_rows.append(audit)
    for dataset in config.get("inventory_only", []):
        frame, audit = read_dataset(dataset, config, project_root)
        audit["status"] = "inventory_only"
        audit["reason"] = dataset["reason"]
        audit_rows.append(audit)
    return bars, audit_rows


def audit_only(config_path: str | Path, run_id: str | None = None) -> Path:
    config, project_root = load_config(config_path)
    run_id = run_id or make_run_id("audit")
    work_dir = project_root / "work" / config["study_id"] / run_id
    diagnostics = work_dir / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=False)
    bars, audits = _audit_inventory(config, project_root)
    pd.DataFrame(audits).to_csv(diagnostics / "data_audit.csv", index=False)
    for frame in bars:
        key = f"{frame['asset'].iloc[0]}_range{int(frame['range_setting'].iloc[0])}"
        geometry_summary(frame).to_csv(diagnostics / f"{key}_geometry.csv", index=False)
    shutil.copy2(Path(config_path).resolve(), diagnostics / "frozen_config.yaml")
    return work_dir


def _alternative_sequence(bars: pd.DataFrame) -> pd.DataFrame:
    alternative = bars.copy()
    split_change = alternative["split"].ne(alternative["split"].shift())
    invalid = (~alternative["valid_row"]) | (~alternative["valid_row"].shift(fill_value=False))
    alternative["sequence_id"] = (split_change | invalid).cumsum().astype(np.int64)
    return alternative


def _example_rows(bars: pd.DataFrame, events: pd.DataFrame, seed: int) -> pd.DataFrame:
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy().reset_index(drop=True)
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    eligible = events.loc[events["eligible_L_ge_3"].fillna(False)]
    groups = (
        ("success_L_ge_3", eligible.loc[eligible["success_L_ge_3"].fillna(False)]),
        ("failure_before_3", eligible.loc[~eligible["success_L_ge_3"].fillna(False)]),
    )
    for label, candidates in groups:
        if candidates.empty:
            continue
        event = candidates.iloc[int(rng.integers(0, len(candidates)))]
        pos = int(event["bar_index"])
        sequence = int(event["sequence_id"])
        start = max(0, pos - 3)
        end = min(len(usable), pos + 7)
        window = usable.iloc[start:end]
        window = window.loc[window["sequence_id"].eq(sequence)]
        tokens = []
        price_tokens = []
        for w in window.itertuples():
            arrow = "UP" if int(w.direction) == 1 else "DOWN" if int(w.direction) == -1 else "DOJI"
            marker = "[SIGNAL]" if int(w.Index) == pos else ""
            tokens.append(f"r{int(w.source_row)}:{arrow}{marker}")
            price_tokens.append(f"r{int(w.source_row)} O{w.open:g} H{w.high:g} L{w.low:g} C{w.close:g}")
        rows.append(
            {
                "event_id": event["event_id"],
                "asset": event["asset"],
                "contract": event["contract"],
                "range_setting": int(event["range_setting"]),
                "chart_identity_status": event["chart_identity_status"],
                "date_window": event["export_date"],
                "split": event["split"],
                "direction": event["signal_side"],
                "cohort": "seeded real-event example",
                "denominator": 1,
                "horizon": "three future bars plus context",
                "units": "ticks and native price",
                "timing_status": event["timing_status"],
                "example_type": label,
                "source_file": event["source_file"],
                "source_row": int(event["source_row"]),
                "signal_side": event["signal_side"],
                "signal_reference_ticks": int(event["signal_reference_ticks"]),
                "observed_L": int(event["observed_L"]),
                "success_L_ge_3": bool(event["success_L_ge_3"]),
                "mae_h3_ticks": event["mae_h3"],
                "mfe_h3_ticks": event["mfe_h3"],
                "direction_sequence": " | ".join(tokens),
                "ohlc_sequence": " | ".join(price_tokens),
            }
        )
    return pd.DataFrame(rows)


def run_study(config_path: str | Path, run_id: str | None = None) -> tuple[Path, Path]:
    started = datetime.now(timezone.utc)
    config, project_root = load_config(config_path)
    run_id = run_id or make_run_id("study")
    work_dir, report_dir = _dirs(project_root, config["study_id"], run_id)
    config_path = Path(config_path).resolve()
    shutil.copy2(config_path, work_dir / "diagnostics" / "frozen_config.yaml")

    # Audit all inputs and persist the audit before calculating any outcomes.
    source_bars, audit_rows = _audit_inventory(config, project_root)
    audit = pd.DataFrame(audit_rows)
    audit.to_csv(work_dir / "diagnostics" / "data_audit.csv", index=False)

    all_events: list[pd.DataFrame] = []
    all_baseline: list[pd.DataFrame] = []
    all_alternative: list[pd.DataFrame] = []
    all_geometry: list[pd.DataFrame] = []
    all_coverage: list[pd.DataFrame] = []
    all_timing_quality: list[pd.DataFrame] = []
    all_reconciliation: list[pd.DataFrame] = []
    reconciliation_checks: list[dict[str, Any]] = []
    examples: list[pd.DataFrame] = []

    for bars in source_bars:
        asset = str(bars["asset"].iloc[0])
        range_setting = int(bars["range_setting"].iloc[0])
        key = f"{asset}_range{range_setting}"
        bars.to_csv(work_dir / "normalized" / f"{key}_bars.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
        all_geometry.append(geometry_summary(bars))
        coverage = coverage_by_date(bars)
        all_coverage.append(coverage)
        all_timing_quality.append(timestamp_quality_table(bars, config))

        events, baseline = detect_events(bars, config)
        events = add_excursions_and_timing(bars, events, config)
        events.to_csv(work_dir / "events" / f"{key}_events.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
        all_events.append(events)
        baseline_columns = [
            "asset", "contract", "range_setting", "export_date", "split", "signal_side",
            "eligible_L_ge_3", "success_L_ge_3", "chart_identity_status", "timing_status",
        ]
        all_baseline.append(baseline[baseline_columns].copy())

        alt_events, _ = detect_events(_alternative_sequence(bars), config)
        all_alternative.append(alt_events)

        recon, checks = reconciliation_sample(
            {(asset, range_setting): bars},
            {(asset, range_setting): events},
            stable_seed(config["bootstrap"]["seed"], "reconciliation", asset, range_setting),
        )
        all_reconciliation.append(recon)
        reconciliation_checks.append(checks)
        examples.append(_example_rows(bars, events, stable_seed(config["bootstrap"]["seed"], "examples", asset, range_setting)))

    events = pd.concat(all_events, ignore_index=True)
    baseline = pd.concat(all_baseline, ignore_index=True)
    alternative = pd.concat(all_alternative, ignore_index=True)
    geometry = pd.concat(all_geometry, ignore_index=True)
    coverage = pd.concat(all_coverage, ignore_index=True)
    timing_quality = pd.concat(all_timing_quality, ignore_index=True)
    reconciliation = pd.concat(all_reconciliation, ignore_index=True)
    examples_frame = pd.concat(examples, ignore_index=True)

    tables: dict[str, pd.DataFrame] = {}
    tables["data_audit"] = audit
    tables["geometry"] = geometry
    tables["coverage"] = coverage
    tables["headline"] = headline_table(events, config)
    tables["continuation_thresholds"] = threshold_table(events, config)
    tables["continuation_curve"] = continuation_curve_table(events, config)
    tables["run_length_summary"], tables["run_length_bins"] = run_tables(events, config)
    tables["excursions_fixed"] = fixed_excursion_table(events, config)
    tables["excursions_through_break"] = natural_excursion_table(events, config, "through_break")
    tables["excursions_run_only"] = natural_excursion_table(events, config, "run_only")
    tables["movement_at_milestones"] = movement_milestone_table(events, config)
    tables["timing_milestones"] = milestone_timing_table(events, config)
    tables["extreme_bar_indices"] = extreme_bar_table(events, config)
    tables["timing_quality"] = timing_quality
    tables["opportunities"] = opportunity_table(events, coverage, config)
    tables["paired_comparisons"] = paired_comparisons(events, config)
    tables["same_chart_baseline"] = baseline_table(events, baseline, config)
    tables["stability"] = stability_table(events, config)
    tables["boundary_sensitivity"] = boundary_sensitivity_table(events, alternative, config)
    tables["manual_reconciliation"] = reconciliation
    tables["annotated_examples"] = examples_frame

    recommendations, selection_ledger = select_and_freeze_candidates(
        tables["headline"], tables["paired_comparisons"], config
    )
    tables["candidate_selection"] = recommendations
    tables["cross_asset_summary"] = cross_asset_summary(
        tables["headline"],
        recommendations,
        tables["excursions_fixed"],
        tables["run_length_summary"],
        tables["opportunities"],
        tables["timing_milestones"],
        config,
    )

    invariant_checks = aggregate_invariants(events, config)
    reconciliation_combined = {
        "charts": reconciliation_checks,
        "sampled_events": sum(c["sampled_events"] for c in reconciliation_checks),
        "event_scan_matches": sum(c["event_scan_matches"] for c in reconciliation_checks),
        "threshold_logic_matches": sum(c["threshold_logic_matches"] for c in reconciliation_checks),
        "all_checks_pass": all(c["all_checks_pass"] for c in reconciliation_checks),
    }
    write_json(work_dir / "diagnostics" / "aggregate_invariants.json", invariant_checks)
    write_json(work_dir / "diagnostics" / "real_event_crosscheck.json", reconciliation_combined)
    write_json(report_dir / "selection_ledger.json", selection_ledger)

    for name, frame in tables.items():
        output_name = "timing_milestones_proxy" if name == "timing_milestones" else name
        frame.to_csv(report_dir / "tables" / f"{output_name}.csv", index=False)

    write_methodology(report_dir, config)
    write_data_quality(report_dir, audit, config)
    generate_figures(report_dir, tables, examples_frame)
    write_report(report_dir, config, tables, recommendations, run_id)

    completed = datetime.now(timezone.utc)
    manifest = _manifest(
        project_root,
        work_dir,
        report_dir,
        config,
        config_path,
        audit,
        tables,
        recommendations,
        invariant_checks,
        reconciliation_combined,
        started,
        completed,
        run_id,
    )
    write_json(report_dir / "run_manifest.json", manifest)
    return work_dir, report_dir


def _manifest(
    project_root: Path,
    work_dir: Path,
    report_dir: Path,
    config: dict[str, Any],
    config_path: Path,
    audit: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
    recommendations: pd.DataFrame,
    invariants: dict[str, Any],
    reconciliation: dict[str, Any],
    started: datetime,
    completed: datetime,
    run_id: str,
) -> dict[str, Any]:
    package_root = project_root / "analysis" / "01_reversal_follow_through"
    source_files = sorted(p for p in package_root.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    output_files = sorted(
        [p for p in work_dir.rglob("*") if p.is_file()]
        + [p for p in report_dir.rglob("*") if p.is_file() and p.name != "run_manifest.json"]
    )
    present_audit = audit.loc[audit["status"].isin(["analyzed", "inventory_only"])]
    return {
        "study_id": config["study_id"],
        "run_id": run_id,
        "started_utc": started.isoformat(),
        "completed_utc": completed.isoformat(),
        "runtime_seconds": (completed - started).total_seconds(),
        "reproducible_command": f"PYTHONPATH=analysis/01_reversal_follow_through/src python -m reversal_study.cli run --config analysis/01_reversal_follow_through/configs/study.yaml --run-id {run_id}_rerun",
        "python": sys.version,
        "platform": platform.platform(),
        "dependencies": {"numpy": np.__version__, "pandas": pd.__version__},
        "git_revision": None,
        "git_status": "project directory is not a Git repository",
        "configuration_path": str(config_path.relative_to(project_root)),
        "configuration_sha256": config_hash(config),
        "bootstrap": config["bootstrap"],
        "definitions": {
            "direction": "sign(close-open) in integer exchange ticks",
            "reversal": "adjacent non-doji bar opposite the preceding non-doji bar within a valid segment",
            "primary_metric": "P(L>=3), conditional on a complete three-future-bar window",
            "segment_rule": config["segment_rule"],
            "final_row_exclusion": config["bar_completion"],
        },
        "unresolved_metadata": [
            "Range XV versus prior user label Range XC",
            "ATAS version and exact chart settings",
            "range parameter units",
            "timezone",
            "timestamp open-versus-close meaning",
            "bar completion flags",
            "data feed and contract adjustment history",
        ],
        "missing_inputs": ["GC range 20 export"],
        "inventory_only": ["data/GCZ6_rangexv6_0614_0904.csv"],
        "input_files": present_audit[["source_path", "source_sha256", "size_bytes", "rows", "status"]].to_dict(orient="records"),
        "input_hashes_rechecked_after_run": {
            row.source_path: sha256_file(project_root / row.source_path) == row.source_sha256
            for row in present_audit.itertuples(index=False)
        },
        "implementation_files": {
            str(path.relative_to(project_root)): sha256_file(path) for path in source_files
        },
        "output_files": {
            str(path.relative_to(project_root)): sha256_file(path) for path in output_files
        },
        "table_rows": {name: int(len(frame)) for name, frame in tables.items()},
        "event_rows": int(invariants["events"]),
        "analysis_event_rows_excluding_embargo": int(
            sum(
                tables["headline"].loc[
                    tables["headline"]["split"].eq("full")
                    & tables["headline"]["direction"].eq("all"),
                    "total_reversals",
                ].fillna(0)
            )
        ),
        "candidate_selection": recommendations.to_dict(orient="records"),
        "aggregate_invariants": invariants,
        "real_event_crosscheck": reconciliation,
    }


def regenerate_html(project_root: Path, run_id: str) -> Path:
    report_dir = project_root / "reports" / "01_reversal_follow_through" / run_id
    report_path = report_dir / "report.md"
    headline_path = report_dir / "tables" / "headline.csv"
    if not report_path.exists() or not headline_path.exists():
        raise FileNotFoundError(f"Run {run_id!r} does not contain report.md and tables/headline.csv")
    from .reporting import _write_html_report

    _write_html_report(report_dir, report_path.read_text(encoding="utf-8"), {"headline": pd.read_csv(headline_path)}, run_id)
    return report_dir / "report.html"
