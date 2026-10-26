"""Select a 2025 causal filter and check it unchanged in 2026 YTD."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from study_provenance import run_phase

import numpy as np
import pandas as pd

from abacus_bhishma.feature_loader import load_gc_5m_release
from src.engine import (COOLDOWNS, FILTERS, HORIZONS, accepted_context,
                        build_context, paired_week_bootstrap, summarize)


BAR_COLUMNS = ["ts_event", "session_date", "open", "high", "low", "close",
               "raw_symbol", "price_adjustment", "source_bar_count", "is_partial_bar",
               "is_mixed_contract_bar", "is_mixed_adjustment_bar", "contains_roll"]
BAND_COLUMNS = ["ts_event", "available_at", "ema_base_225", "residual_sigma_225", "lower_outer_3sigma"]
PRIMARY_COOLDOWN = 10
PRIMARY_HORIZON = 20
YEARS = [2025, 2026]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_input(root: Path, record: dict, *, partitions: bool = False) -> dict:
    path = root / record["manifest_path"]
    if sha256(path) != record["sha256"]:
        raise ValueError(f"manifest hash mismatch: {path}")
    manifest = json.loads(path.read_text())
    if partitions:
        files = [x for x in manifest["output_files"] if "/product=GC/" in x["path"]]
        if len(files) != 17:
            raise ValueError("expected 17 GC partitions")
        for item in files:
            p = root / item["path"]
            if sha256(p) != item["sha256"]:
                raise ValueError(f"partition hash mismatch: {p}")
    return manifest


def raw_count(context: pd.DataFrame, rule: str, year: int) -> int:
    rows = context.loc[context.year == year]
    return len(rows) if rule == "unfiltered" else int(rows[rule].sum())


def subset(events: pd.DataFrame, accepted: pd.DataFrame, year: int, horizon: int) -> pd.DataFrame:
    return events.loc[(events.year == year) & (events.horizon == horizon) &
                      events.bar_index.isin(accepted.bar_index)]


def execute(stage: Path, study: Path, root: Path) -> None:
    lock = json.loads((study / "inputs.lock.json").read_text())
    source_manifest = verify_input(root, lock["source_bars"], partitions=True)
    band_manifest = verify_input(root, lock["band_features"], partitions=True)
    verify_input(root, lock["source_outcomes"])
    pine = root / lock["pine_source"]["path"]
    if sha256(pine) != lock["pine_source"]["sha256"]:
        raise ValueError("Pine source hash mismatch")
    events_path = root / lock["source_outcomes"]["event_ledger_path"]
    if sha256(events_path) != lock["source_outcomes"]["event_ledger_sha256"]:
        raise ValueError("sealed outcome ledger hash mismatch")
    bars = load_gc_5m_release(root, "dridr_ohlcv_5m", version="1.0.0", columns=BAR_COLUMNS).to_pandas()
    bands = load_gc_5m_release(root, "gc_ema_deviation_bands", version="1.0.0", columns=BAND_COLUMNS).to_pandas()
    expected_rows = sum(x["rows"] for x in source_manifest["product_year_quality"] if x["product"] == "GC")
    if len(bars) != expected_rows:
        raise ValueError("bar rows differ from pinned source manifest")
    if len(bars) != band_manifest["rows"]:
        raise ValueError("bar and feature row counts differ")
    context = build_context(bars, bands)
    outcomes = pd.read_parquet(events_path)
    outcomes = outcomes.loc[outcomes.cooldown == 0].copy()
    outcomes["signal_ts_utc"] = pd.to_datetime(outcomes.signal_ts_utc, utc=True)
    context["signal_ts_utc"] = pd.to_datetime(context.signal_ts_utc, utc=True)
    original = outcomes.loc[outcomes.horizon == PRIMARY_HORIZON, "signal_ts_utc"]
    if len(original) != len(context) or not original.reset_index(drop=True).equals(context.signal_ts_utc.reset_index(drop=True)):
        raise ValueError("reconstructed signal candidates differ from sealed study 12")
    merged = outcomes.merge(context, on="signal_ts_utc", validate="many_to_one", suffixes=("_old", ""))
    if not (merged.year_old == merged.year).all():
        raise ValueError("signal close year mismatch")
    merged = merged.loc[merged.year.isin(YEARS)].copy()
    context_recent = context.loc[context.year.isin(YEARS)].copy()
    rules = ["unfiltered", *FILTERS]
    accepted = {(rule, cooldown): accepted_context(context, rule, cooldown)
                for rule in rules for cooldown in COOLDOWNS}
    for rule in rules:
        context_recent[f"accepted_c10_{rule}"] = context_recent.bar_index.isin(
            accepted[(rule, PRIMARY_COOLDOWN)].bar_index).to_numpy()
    primary_rows = []
    primary_sets = {}
    for rule in rules:
        selected = accepted[(rule, PRIMARY_COOLDOWN)]
        for year in YEARS:
            cohort = subset(merged, selected, year, PRIMARY_HORIZON)
            primary_sets[(rule, year)] = cohort
            row = {"rule": rule, "year": year, "cooldown": PRIMARY_COOLDOWN,
                   "horizon": PRIMARY_HORIZON}
            row.update(summarize(cohort, raw_count(context, rule, year), int((selected.year == year).sum())))
            primary_rows.append(row)
    primary = pd.DataFrame(primary_rows)
    primary["score_delta_vs_unfiltered"] = np.nan
    primary["score_delta_ci_low"] = np.nan
    primary["score_delta_ci_high"] = np.nan
    for year in YEARS:
        baseline_score = primary.loc[(primary.rule == "unfiltered") & (primary.year == year), "mean_clipped_score"].iloc[0]
        for index, rule in enumerate(FILTERS):
            row_idx = primary.index[(primary.rule == rule) & (primary.year == year)][0]
            primary.loc[row_idx, "score_delta_vs_unfiltered"] = primary.loc[row_idx, "mean_clipped_score"] - baseline_score
            lo, hi = paired_week_bootstrap(primary_sets[(rule, year)], primary_sets[("unfiltered", year)],
                                            seed=1313 + 100 * (year - 2025) + index, replicates=2000)
            primary.loc[row_idx, "score_delta_ci_low"] = lo
            primary.loc[row_idx, "score_delta_ci_high"] = hi
    train_base = primary.loc[(primary.rule == "unfiltered") & (primary.year == 2025)].iloc[0]
    eligible = []
    for rule in FILTERS:
        row = primary.loc[(primary.rule == rule) & (primary.year == 2025)].iloc[0]
        if (row.valid_n >= 45 and row.sessions >= 20 and row.weeks >= 10 and
            row.mean_mae_sigma < train_base.mean_mae_sigma and
            row.mean_mfe_sigma >= .9 * train_base.mean_mfe_sigma and
            row.score_delta_vs_unfiltered > 0):
            eligible.append(rule)
    chosen = max(eligible, key=lambda rule: primary.loc[(primary.rule == rule) &
                     (primary.year == 2025), "score_delta_vs_unfiltered"].iloc[0]) if eligible else None
    check_base = primary.loc[(primary.rule == "unfiltered") & (primary.year == 2026)].iloc[0]
    check_row = (primary.loc[(primary.rule == chosen) & (primary.year == 2026)].iloc[0]
                 if chosen is not None else None)
    check_pass = bool(check_row is not None and check_row.valid_n >= 30 and
                      check_row.sessions >= 15 and check_row.weeks >= 8 and
                      check_row.score_delta_vs_unfiltered > 0 and
                      check_row.mean_mae_sigma < check_base.mean_mae_sigma and
                      check_row.mean_mfe_sigma >= .9 * check_base.mean_mfe_sigma)
    interval_excludes_zero = bool(check_row is not None and
                                  pd.notna(check_row.score_delta_ci_low) and
                                  check_row.score_delta_ci_low > 0)
    decision = {"selected_rule": chosen, "selection_year": 2025,
                "chronological_check_year": 2026,
                "eligible_training_rules": eligible,
                "descriptive_check_passed": check_pass,
                "check_interval_excludes_zero": interval_excludes_zero,
                "status": ("descriptive_improvement_uncertain" if check_pass and not interval_excludes_zero else
                           "descriptive_improvement" if check_pass else
                           "no_training_rule_qualified" if chosen is None else "failed_2026_check"),
                "not_untouched_holdout": True,
                "selection_used_2026_outcomes": False}
    sensitivity_rows = []
    for rule in ["unfiltered", chosen] if chosen else ["unfiltered"]:
        for cooldown in COOLDOWNS:
            selected = accepted[(rule, cooldown)]
            for horizon in HORIZONS:
                for year in YEARS:
                    cohort = subset(merged, selected, year, horizon)
                    row = {"rule": rule, "year": year, "cooldown": cooldown,
                           "horizon": horizon}
                    row.update(summarize(cohort, raw_count(context, rule, year), int((selected.year == year).sum())))
                    sensitivity_rows.append(row)
    sensitivity = pd.DataFrame(sensitivity_rows)
    if chosen:
        keys = ["year", "cooldown", "horizon"]
        baseline = sensitivity.loc[sensitivity.rule == "unfiltered", keys + ["mean_clipped_score"]].rename(columns={"mean_clipped_score": "baseline_score"})
        sensitivity = sensitivity.merge(baseline, on=keys, how="left", validate="many_to_one")
        sensitivity["score_delta_vs_unfiltered"] = sensitivity.mean_clipped_score - sensitivity.baseline_score
    tables = stage / "tables"
    tables.mkdir()
    context_recent.to_parquet(tables / "candidate_context.parquet", compression="zstd", index=False)
    merged.to_parquet(tables / "candidate_outcomes.parquet", compression="zstd", index=False)
    primary.to_csv(tables / "primary.csv", index=False, float_format="%.10f")
    sensitivity.to_csv(tables / "sensitivity.csv", index=False, float_format="%.10f")
    (stage / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    config = {"study_id": study.name, "protocol_version": "1.0.0", "outcome_years": YEARS,
              "training_year": 2025, "chronological_check_year": 2026,
              "primary_cooldown": PRIMARY_COOLDOWN, "primary_horizon": PRIMARY_HORIZON,
              "rules": rules, "score": "mean(min(mfe/sigma,10)-min(mae/sigma,10))",
              "minimum_training_valid": 45, "minimum_training_sessions": 20,
              "minimum_training_weeks": 10, "minimum_check_valid": 30,
              "minimum_check_sessions": 15, "minimum_check_weeks": 8,
              "minimum_mfe_retention": .9,
              "bootstrap_replicates": 2000, "bootstrap_seed": 1313,
              "plan_sha256": sha256(study / "plan.md"),
              "settings_sha256": sha256(study / "study.yaml")}
    (stage / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    (stage / "inputs.lock.json").write_text(json.dumps(lock, indent=2) + "\n")
    (stage / "metrics.json").write_text(json.dumps({"executed_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_bar_rows": len(bars), "raw_signal_candidates_all_years": len(context),
                "raw_signal_candidates_2025_2026": len(context_recent),
                "outcome_rows_2025_2026": len(merged), "primary_rows": len(primary),
                "sensitivity_rows": len(sensitivity), "selected_rule": chosen,
                "descriptive_check_passed": check_pass}, indent=2) + "\n")
    print(json.dumps({"stage": str(stage), "selected_rule": chosen,
                      "descriptive_check_passed": check_pass,
                      "primary_rows": len(primary), "sensitivity_rows": len(sensitivity)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, type=Path)
    args = parser.parse_args()
    study = Path(__file__).resolve().parent
    root = study.parents[1]
    run_phase(root, study.name, args.stage, "execution",
              lambda: execute(args.stage.absolute(), study, root))


if __name__ == "__main__":
    main()
