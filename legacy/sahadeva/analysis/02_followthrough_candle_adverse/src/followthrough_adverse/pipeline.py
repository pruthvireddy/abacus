from __future__ import annotations

import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .core import config_hash, detect_reversals, load_config, read_chart, reconcile_sample, sha256_file
from .hold_time import compute_hold_events, hold_time_by_clock, rank_hold_windows, reconcile_hold_sample, summarize_hold_events
from .leg_duration import compute_leg_events, leg_duration_by_clock, leg_duration_by_session, rank_leg_windows, reconcile_leg_sample, summarize_leg_duration
from .reporting import generate_figures, headline_table, write_data_quality, write_json, write_leg_duration_report, write_methodology, write_report
from .stats import stable_seed, summarize_events
from .time_of_day import build_confirmation_time_table, build_signal_time_table, rank_time_windows


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_study")


def run_study(config_path: str | Path, run_id: str | None = None) -> tuple[Path, Path]:
    started = datetime.now(timezone.utc)
    config, project_root = load_config(config_path)
    run_id = run_id or make_run_id()
    work_dir = project_root / "work" / config["study_id"] / run_id
    report_dir = project_root / "reports" / config["study_id"] / run_id
    for path in (work_dir / "events", work_dir / "hold_events", work_dir / "leg_events", work_dir / "diagnostics", report_dir / "tables", report_dir / "figures"):
        path.mkdir(parents=True, exist_ok=False if path == work_dir / "events" else True)
    shutil.copy2(Path(config_path).resolve(), work_dir / "diagnostics" / "frozen_config.yaml")

    audits: list[dict[str, Any]] = []
    event_frames: list[pd.DataFrame] = []
    signal_time_frames: list[pd.DataFrame] = []
    confirmation_time_frames: list[pd.DataFrame] = []
    hold_event_frames: list[pd.DataFrame] = []
    hold_reconciliations: list[pd.DataFrame] = []
    hold_check_rows: list[dict[str, Any]] = []
    leg_event_frames: list[pd.DataFrame] = []
    leg_reconciliations: list[pd.DataFrame] = []
    leg_check_rows: list[dict[str, Any]] = []
    reconciliations: list[pd.DataFrame] = []
    check_rows: list[dict[str, Any]] = []
    for dataset in config["datasets"]:
        bars, audit = read_chart(dataset, config, project_root)
        audits.append(audit)
        events = detect_reversals(bars, config)
        event_frames.append(events)
        hold_events = compute_hold_events(bars, events, config)
        hold_event_frames.append(hold_events)
        leg_events = compute_leg_events(bars, events, config)
        leg_event_frames.append(leg_events)
        signal_time_frames.append(build_signal_time_table(bars, events, config))
        confirmation_time_frames.append(build_confirmation_time_table(bars, events, config))
        key = f"{dataset['asset']}_range{dataset['range']}"
        events.to_csv(work_dir / "events" / f"{key}_events.csv", index=False)
        hold_events.to_csv(work_dir / "hold_events" / f"{key}_hold_events.csv", index=False)
        leg_events.to_csv(work_dir / "leg_events" / f"{key}_leg_events.csv", index=False)
        reconciliation, check = reconcile_sample(
            bars,
            events,
            stable_seed(config["bootstrap"]["seed"], dataset["asset"], dataset["range"], "reconcile"),
        )
        reconciliations.append(reconciliation)
        check_rows.append({"asset": dataset["asset"], "range_setting": dataset["range"], **check})
        hold_reconciliation, hold_check = reconcile_hold_sample(
            bars,
            hold_events,
            config,
            stable_seed(config["bootstrap"]["seed"], dataset["asset"], dataset["range"], "hold_reconcile"),
        )
        hold_reconciliations.append(hold_reconciliation)
        hold_check_rows.append({"asset": dataset["asset"], "range_setting": dataset["range"], **hold_check})
        leg_reconciliation, leg_check = reconcile_leg_sample(
            bars,
            leg_events,
            stable_seed(config["bootstrap"]["seed"], dataset["asset"], dataset["range"], "leg_reconcile"),
        )
        leg_reconciliations.append(leg_reconciliation)
        leg_check_rows.append({"asset": dataset["asset"], "range_setting": dataset["range"], **leg_check})

    audit = pd.DataFrame(audits)
    events = pd.concat(event_frames, ignore_index=True)
    reconciliation = pd.concat(reconciliations, ignore_index=True)
    hold_events = pd.concat(hold_event_frames, ignore_index=True)
    hold_reconciliation = pd.concat(hold_reconciliations, ignore_index=True)
    leg_events = pd.concat(leg_event_frames, ignore_index=True)
    leg_reconciliation = pd.concat(leg_reconciliations, ignore_index=True)
    summary = summarize_events(events, config)
    signal_time = pd.concat(signal_time_frames, ignore_index=True)
    confirmation_time = pd.concat(confirmation_time_frames, ignore_index=True)
    time_rankings, balanced_windows = rank_time_windows(signal_time, confirmation_time, config)
    hold_summary = summarize_hold_events(hold_events, config)
    hold_time_30min = hold_time_by_clock(hold_events, config)
    hold_rankings, hold_balanced_windows = rank_hold_windows(hold_time_30min, config)
    leg_duration_summary = summarize_leg_duration(leg_events, config)
    leg_duration_30min = leg_duration_by_clock(leg_events, config)
    leg_duration_sessions = leg_duration_by_session(leg_events, config)
    leg_duration_rankings = rank_leg_windows(leg_duration_30min, config)
    headline = headline_table(summary)
    long_short = summary.loc[summary["period"].eq("full") & summary["prior_run_minimum"].eq(1) & summary["direction"].isin(["long", "short"])]
    prior = summary.loc[summary["period"].eq("full") & summary["direction"].eq("all")]
    chronological = summary.loc[summary["period"].isin(["development", "validation", "test"]) & summary["direction"].eq("all") & summary["prior_run_minimum"].eq(1)]
    tables = {
        "data_audit": audit,
        "all_summary": summary,
        "headline": headline,
        "long_short": long_short,
        "prior_run_sensitivity": prior,
        "chronological_stability": chronological,
        "manual_reconciliation": reconciliation,
        "time_of_day_signal_30min": signal_time,
        "time_of_day_confirmation_30min": confirmation_time,
        "time_of_day_rankings_30min": time_rankings,
        "time_of_day_balanced_windows_30min": balanced_windows,
        "hold_time_summary": hold_summary,
        "hold_time_by_confirmation_30min": hold_time_30min,
        "hold_time_rankings_30min": hold_rankings,
        "hold_time_balanced_windows_30min": hold_balanced_windows,
        "hold_time_manual_reconciliation": hold_reconciliation,
        "leg_duration_summary": leg_duration_summary,
        "leg_duration_by_reversal_30min": leg_duration_30min,
        "leg_duration_by_session": leg_duration_sessions,
        "leg_duration_rankings_30min": leg_duration_rankings,
        "leg_duration_manual_reconciliation": leg_reconciliation,
    }
    for name, frame in tables.items():
        frame.to_csv(report_dir / "tables" / f"{name}.csv", index=False)
    checks = {
        "charts": check_rows,
        "sampled_events": int(sum(row["sampled"] for row in check_rows)),
        "matching_events": int(sum(row["matches"] for row in check_rows)),
        "all_checks_pass": all(row["all_match"] for row in check_rows),
        "nonnegative_primary_adverse": bool(events["adverse_from_follow_open_ticks"].dropna().ge(0).all()),
        "conditioned_rows_have_same_direction": bool(events.loc[events["next_bar_same_direction"], "close_progress_from_follow_open_ticks"].gt(0).all()),
        "time_of_day_signal_rows": int(len(signal_time)),
        "time_of_day_confirmation_rows": int(len(confirmation_time)),
        "time_of_day_expected_rows": int(len(config["datasets"]) * (1440 // config["time_of_day"]["window_minutes"])),
        "time_of_day_signal_reversals_reconcile": bool(signal_time["total_reversals"].sum() == len(events)),
        "time_of_day_signal_events_reconcile": bool(signal_time["same_direction_events"].sum() == events["next_bar_same_direction"].sum()),
        "time_of_day_confirmation_events_reconcile": bool(confirmation_time["conditioned_events"].sum() == events["next_bar_same_direction"].sum()),
        "time_of_day_rankings_meet_support": bool(
            time_rankings["conditioned_events"].ge(config["time_of_day"]["minimum_conditioned_events"]).all()
            & time_rankings["active_export_dates"].ge(config["time_of_day"]["minimum_active_export_dates"]).all()
        ),
        "hold_events_reconcile_to_conditioned_events": bool(len(hold_events) == events["next_bar_same_direction"].sum()),
        "hold_strict_success_requires_eligibility": bool((~hold_events["strict_two_more_success"] | hold_events["strict_eligible_two_more"]).all()),
        "hold_eventual_success_requires_eligibility": bool((~hold_events["eventual_pair_success"] | hold_events["eventual_eligible_horizon"]).all()),
        "hold_strict_success_target_is_two_bars": bool(hold_events.loc[hold_events["strict_two_more_success"], "strict_bars_to_target"].eq(2).all()),
        "hold_proxy_times_nonnegative": bool(
            hold_events["strict_hold_proxy_seconds"].dropna().ge(0).all()
            & hold_events["eventual_hold_proxy_seconds"].dropna().ge(0).all()
        ),
        "hold_time_rows": int(len(hold_time_30min)),
        "hold_time_expected_rows": int(len(config["datasets"]) * (1440 // config["time_of_day"]["window_minutes"])),
        "hold_reconciliation_charts": hold_check_rows,
        "hold_reconciliation_sampled_events": int(sum(row["sampled"] for row in hold_check_rows)),
        "hold_reconciliation_matching_events": int(sum(row["matches"] for row in hold_check_rows)),
        "hold_reconciliation_all_checks_pass": all(row["all_match"] for row in hold_check_rows),
        "leg_events_reconcile_to_reversals": bool(len(leg_events) == len(events)),
        "leg_completed_and_censored_partition": bool(
            (leg_events["leg_completed"] ^ leg_events["leg_censored"]).all()
        ),
        "leg_three_plus_requires_completion": bool(
            (~leg_events["leg_at_least_three"] | leg_events["leg_completed"]).all()
        ),
        "leg_three_plus_minimum_candles": bool(
            leg_events.loc[leg_events["leg_at_least_three"], "leg_candle_count_including_reversal"].ge(3).all()
        ),
        "leg_duration_nonnegative": bool(
            leg_events["leg_duration_proxy_seconds"].dropna().ge(0).all()
        ),
        "leg_time_rows": int(len(leg_duration_30min)),
        "leg_time_expected_rows": int(len(config["datasets"]) * (1440 // config["time_of_day"]["window_minutes"])),
        "leg_session_rows": int(len(leg_duration_sessions)),
        "leg_session_expected_rows": int(len(config["datasets"]) * len(config["leg_duration"]["sessions"])),
        "leg_session_qualifying_within_total": bool(
            leg_duration_sessions["legs_at_least_three"].le(
                leg_duration_sessions["completed_legs"]
            ).all()
        ),
        "leg_rankings_meet_support": bool(
            leg_duration_rankings["legs_at_least_three"].ge(config["leg_duration"]["minimum_qualifying_legs_per_window"]).all()
            & leg_duration_rankings["qualifying_active_export_dates"].ge(config["leg_duration"]["minimum_active_export_dates"]).all()
        ),
        "leg_reconciliation_charts": leg_check_rows,
        "leg_reconciliation_sampled_events": int(sum(row["sampled"] for row in leg_check_rows)),
        "leg_reconciliation_matching_events": int(sum(row["matches"] for row in leg_check_rows)),
        "leg_reconciliation_all_checks_pass": all(row["all_match"] for row in leg_check_rows),
    }
    checks["all_checks_pass"] = bool(
        checks["all_checks_pass"]
        and checks["time_of_day_signal_reversals_reconcile"]
        and checks["time_of_day_signal_events_reconcile"]
        and checks["time_of_day_confirmation_events_reconcile"]
        and checks["time_of_day_rankings_meet_support"]
        and checks["hold_events_reconcile_to_conditioned_events"]
        and checks["hold_strict_success_requires_eligibility"]
        and checks["hold_eventual_success_requires_eligibility"]
        and checks["hold_strict_success_target_is_two_bars"]
        and checks["hold_proxy_times_nonnegative"]
        and checks["hold_time_rows"] == checks["hold_time_expected_rows"]
        and checks["hold_reconciliation_all_checks_pass"]
        and checks["leg_events_reconcile_to_reversals"]
        and checks["leg_completed_and_censored_partition"]
        and checks["leg_three_plus_requires_completion"]
        and checks["leg_three_plus_minimum_candles"]
        and checks["leg_duration_nonnegative"]
        and checks["leg_time_rows"] == checks["leg_time_expected_rows"]
        and checks["leg_session_rows"] == checks["leg_session_expected_rows"]
        and checks["leg_session_qualifying_within_total"]
        and checks["leg_rankings_meet_support"]
        and checks["leg_reconciliation_all_checks_pass"]
    )
    write_json(work_dir / "diagnostics" / "validation_checks.json", checks)
    write_methodology(report_dir, config)
    write_data_quality(report_dir, audit)
    generate_figures(report_dir, summary, signal_time, hold_time_30min, leg_duration_30min)
    write_report(
        report_dir,
        config,
        summary,
        audit,
        run_id,
        signal_time,
        time_rankings,
        balanced_windows,
        hold_summary,
        hold_rankings,
        hold_balanced_windows,
    )
    write_leg_duration_report(
        report_dir,
        config,
        run_id,
        leg_duration_summary,
        leg_duration_30min,
        leg_duration_sessions,
        leg_duration_rankings,
    )

    completed = datetime.now(timezone.utc)
    package_dir = project_root / "analysis" / "02_followthrough_candle_adverse"
    output_files = sorted(
        [p for p in work_dir.rglob("*") if p.is_file()]
        + [p for p in report_dir.rglob("*") if p.is_file() and p.name != "run_manifest.json"]
    )
    source_files = sorted(p for p in package_dir.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    manifest = {
        "study_id": config["study_id"],
        "run_id": run_id,
        "started_utc": started.isoformat(),
        "completed_utc": completed.isoformat(),
        "runtime_seconds": (completed - started).total_seconds(),
        "reproducible_command": f"PYTHONPATH=analysis/02_followthrough_candle_adverse/src python -m followthrough_adverse.cli run --config analysis/02_followthrough_candle_adverse/configs/study.yaml --run-id {run_id}_rerun",
        "python": sys.version,
        "platform": platform.platform(),
        "dependencies": {"numpy": np.__version__, "pandas": pd.__version__},
        "configuration_sha256": config_hash(config),
        "definition": config["question"],
        "primary_reference": config["primary_reference"],
        "second_candle_interpretation": config["second_candle_interpretation"],
        "hold_time_definitions": {
            "strict": "two immediately subsequent bars both close in the confirmation direction",
            "eventual": f"first two-bar same-direction pair within {config['hold_time']['eventual_search_horizon_bars']} bars after confirmation",
            "elapsed_time": "raw timestamp-difference proxy only",
        },
        "leg_duration_definition": {
            "cohort": "completed reversal legs with at least three candles including the reversal",
            "start": "reversal candle raw timestamp",
            "end": "last consecutive same-direction candle raw timestamp before the next opposite candle or doji",
            "elapsed_time": "raw timestamp-difference proxy only",
            "sessions": config["leg_duration"]["sessions"],
        },
        "bootstrap": config["bootstrap"],
        "input_files": audit[["source_path", "source_sha256", "size_bytes", "rows"]].to_dict(orient="records"),
        "input_hashes_rechecked_after_run": {
            row.source_path: sha256_file(project_root / row.source_path) == row.source_sha256
            for row in audit.itertuples(index=False)
        },
        "implementation_files": {str(p.relative_to(project_root)): sha256_file(p) for p in source_files},
        "output_files": {str(p.relative_to(project_root)): sha256_file(p) for p in output_files},
        "table_rows": {name: int(len(frame)) for name, frame in tables.items()},
        "total_reversal_events": int(len(events)),
        "conditioned_same_direction_events": int(events["next_bar_same_direction"].sum()),
        "validation_checks": checks,
        "limitations": [
            "Filename-labeled Range XV is provisional rather than verified Range XC",
            "Export timezone and timestamp meaning unresolved",
            "Conditional cohort uses the follow-through candle close and is not known at its open",
            "GC6 is analyzed explicitly and is not a substitute for missing GC20",
        ],
    }
    write_json(report_dir / "run_manifest.json", manifest)
    return work_dir, report_dir
