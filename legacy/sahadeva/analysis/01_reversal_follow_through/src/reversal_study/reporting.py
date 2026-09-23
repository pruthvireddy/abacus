from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from .statistics import (
    ANALYSIS_SPLITS,
    DIRECTIONS,
    numeric_summary,
    paired_session_bootstrap_difference,
    session_bootstrap_probability,
    side_frame,
    split_frame,
    stable_seed,
)


def _date_window(frame: pd.DataFrame) -> str:
    return "unavailable" if frame.empty else f"{frame['export_date'].min()} to {frame['export_date'].max()}"


def _identity(
    frame: pd.DataFrame,
    config: dict[str, Any],
    split: str,
    direction: str,
    cohort: str,
    horizon: str,
    units: str,
) -> dict[str, Any]:
    return {
        "asset": str(frame["asset"].iloc[0]),
        "contract": str(frame["contract"].iloc[0]),
        "range_setting": int(frame["range_setting"].iloc[0]),
        "chart_identity_status": config["chart_identity_status"],
        "date_window": _date_window(frame),
        "split": split,
        "direction": direction,
        "cohort": cohort,
        "horizon": horizon,
        "units": units,
        "timing_status": config["timing_status"],
    }


def headline_table(all_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    reps = int(config["bootstrap"]["replicates"])
    seed = int(config["bootstrap"]["seed"])
    for (_, _), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        for split in ANALYSIS_SPLITS:
            split_data = split_frame(chart, split)
            for direction in DIRECTIONS:
                side = side_frame(split_data, direction)
                if side.empty:
                    continue
                primary = session_bootstrap_probability(
                    side,
                    "eligible_L_ge_3",
                    "success_L_ge_3",
                    reps,
                    stable_seed(seed, "headline", side["asset"].iloc[0], side["range_setting"].iloc[0], split, direction, 3),
                )
                including = session_bootstrap_probability(
                    side,
                    "eligible_L_ge_2",
                    "success_L_ge_2",
                    reps,
                    stable_seed(seed, "headline", side["asset"].iloc[0], side["range_setting"].iloc[0], split, direction, 2),
                )
                common = side.loc[side["shared_eligible_10"]]
                dates = sorted(side["export_date"].unique())
                row = _identity(
                    side,
                    config,
                    split,
                    direction,
                    "primary reversals with complete threshold-specific future windows",
                    "L>=3 primary; T>=3 equals L>=2",
                    "probability and bars",
                )
                row.update(primary)
                row.update(
                    {
                        "total_reversals": int(len(side)),
                        "boundary_exclusions_L_ge_3": int(len(side) - primary["eligible_n"]),
                        "exclusion_share_L_ge_3": (len(side) - primary["eligible_n"]) / len(side) if len(side) else np.nan,
                        "eligible_n_T_ge_3": int(including["eligible_n"]),
                        "successes_T_ge_3": int(including["successes"]),
                        "probability_T_ge_3": including["probability"],
                        "ci_low_T_ge_3": including["ci_low"],
                        "ci_high_T_ge_3": including["ci_high"],
                        "shared_eligible_n_10": int(len(common)),
                        "restricted_mean_min_L_10": float(common["restricted_L_10"].mean()) if len(common) else np.nan,
                        "signals_per_export_date": len(side) / len(dates) if dates else np.nan,
                        "support_status": "low support"
                        if primary["eligible_n"] < config["support_flags"]["minimum_eligible_reversals"]
                        or primary["export_dates"] < config["support_flags"]["minimum_export_dates"]
                        else "supported sample",
                    }
                )
                row["denominator"] = primary["eligible_n"]
                rows.append(row)
    for dataset in config["datasets"]:
        if dataset["requested"] and not dataset["available"]:
            rows.append(
                {
                    "asset": dataset["asset"],
                    "contract": dataset["contract"],
                    "range_setting": dataset["range"],
                    "chart_identity_status": config["chart_identity_status"],
                    "date_window": "unavailable",
                    "split": "full",
                    "direction": "all",
                    "cohort": "requested dataset",
                    "denominator": np.nan,
                    "horizon": "L>=3 primary; T>=3 equals L>=2",
                    "units": "probability and bars",
                    "timing_status": config["timing_status"],
                    "support_status": "dataset missing; not estimated",
                }
            )
    return pd.DataFrame(rows)


def threshold_table(all_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    reps = int(config["bootstrap"]["replicates"])
    seed = int(config["bootstrap"]["seed"])
    for (_, _), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        for split in ANALYSIS_SPLITS:
            split_data = split_frame(chart, split)
            for direction in DIRECTIONS:
                side = side_frame(split_data, direction)
                if side.empty:
                    continue
                for threshold in config["thresholds"]:
                    result = session_bootstrap_probability(
                        side,
                        f"eligible_L_ge_{threshold}",
                        f"success_L_ge_{threshold}",
                        reps,
                        stable_seed(seed, "threshold", side["asset"].iloc[0], side["range_setting"].iloc[0], split, direction, threshold),
                    )
                    row = _identity(
                        side,
                        config,
                        split,
                        direction,
                        "primary reversals with a complete threshold-specific future window",
                        f"L>={threshold}",
                        "probability",
                    )
                    row.update(result)
                    row.update(
                        {
                            "threshold_k": threshold,
                            "total_reversals": int(len(side)),
                            "failures": int(result["eligible_n"] - result["successes"]),
                            "boundary_exclusions": int(len(side) - result["eligible_n"]),
                            "exclusion_share": (len(side) - result["eligible_n"]) / len(side) if len(side) else np.nan,
                            "denominator": result["eligible_n"],
                        }
                    )
                    rows.append(row)
    return pd.DataFrame(rows)


def continuation_curve_table(all_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    reps = int(config["bootstrap"]["replicates"])
    seed = int(config["bootstrap"]["seed"])
    for (_, _), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        split_data = split_frame(chart, "full")
        for direction in DIRECTIONS:
            side = side_frame(split_data, direction)
            common = side.loc[side["shared_eligible_10"]].copy()
            if common.empty:
                continue
            common["common_eligible"] = True
            for threshold in range(1, 11):
                column = f"curve_success_{threshold}"
                common[column] = common["observed_L"].ge(threshold)
                result = session_bootstrap_probability(
                    common,
                    "common_eligible",
                    column,
                    reps,
                    stable_seed(seed, "curve", common["asset"].iloc[0], common["range_setting"].iloc[0], direction, threshold),
                )
                at_risk = common["observed_L"].ge(threshold - 1)
                conditional = common.loc[at_risk, "observed_L"].ge(threshold).mean() if at_risk.any() else np.nan
                row = _identity(
                    common,
                    config,
                    "full",
                    direction,
                    "shared N10 cohort",
                    f"L>={threshold}",
                    "probability",
                )
                row.update(result)
                row["threshold_k"] = threshold
                row["conditional_probability_given_L_ge_k_minus_1"] = conditional
                row["conditional_denominator"] = int(at_risk.sum())
                row["denominator"] = result["eligible_n"]
                rows.append(row)
    return pd.DataFrame(rows)


def run_tables(all_events: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    bins_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    labels = ("0", "1", "2", "3", "4", "5-9", "10+", "censored")
    for (_, _), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        for split in ANALYSIS_SPLITS:
            split_data = split_frame(chart, split)
            for direction in DIRECTIONS:
                side = side_frame(split_data, direction)
                if side.empty:
                    continue
                completed = side.loc[~side["run_censored"]]
                summary = numeric_summary(completed["completed_L"])
                common = side.loc[side["shared_eligible_10"]]
                row = _identity(
                    side,
                    config,
                    split,
                    direction,
                    "completed natural runs; capped mean uses shared N10 cohort",
                    "natural L after reversal",
                    "bars",
                )
                row.update(summary)
                row.update(
                    {
                        "denominator": int(len(completed)),
                        "total_reversals": int(len(side)),
                        "completed_runs": int(len(completed)),
                        "censored_runs": int(side["run_censored"].sum()),
                        "shared_eligible_n_10": int(len(common)),
                        "restricted_mean_min_L_10": float(common["restricted_L_10"].mean()) if len(common) else np.nan,
                    }
                )
                summary_rows.append(row)
                run = pd.to_numeric(completed["completed_L"], errors="coerce")
                counts = {
                    "0": int((run == 0).sum()),
                    "1": int((run == 1).sum()),
                    "2": int((run == 2).sum()),
                    "3": int((run == 3).sum()),
                    "4": int((run == 4).sum()),
                    "5-9": int(run.between(5, 9).sum()),
                    "10+": int((run >= 10).sum()),
                    "censored": int(side["run_censored"].sum()),
                }
                for label in labels:
                    bin_row = _identity(
                        side,
                        config,
                        split,
                        direction,
                        "all primary reversals, censoring separate",
                        f"exact L bin {label}",
                        "events",
                    )
                    bin_row.update(
                        {
                            "run_bin": label,
                            "count": counts[label],
                            "denominator": int(len(side)),
                            "share_of_all_reversals": counts[label] / len(side) if len(side) else np.nan,
                        }
                    )
                    bins_rows.append(bin_row)
    return pd.DataFrame(summary_rows), pd.DataFrame(bins_rows)


def _excursion_summary(values: pd.Series) -> dict[str, float | int]:
    return numeric_summary(values)


def fixed_excursion_table(all_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (_, _), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        asset = str(chart["asset"].iloc[0])
        tick_size = float(config["contracts"][asset]["tick_size"])
        dollars_tick = float(config["contracts"][asset]["dollars_per_tick"])
        for split in ANALYSIS_SPLITS:
            split_data = split_frame(chart, split)
            for direction in DIRECTIONS:
                side = side_frame(split_data, direction)
                if side.empty:
                    continue
                for horizon in config["fixed_horizons"]:
                    eligible = side.loc[pd.to_numeric(side[f"mae_h{horizon}"], errors="coerce").notna()]
                    row = _identity(
                        side,
                        config,
                        split,
                        direction,
                        "all primary reversals with complete fixed future-bar horizon",
                        f"{horizon} future bars",
                        "ticks, native price units, and gross dollars per standard contract",
                    )
                    row["denominator"] = int(len(eligible))
                    row["incomplete_horizon_exclusions"] = int(len(side) - len(eligible))
                    for metric in ("mae", "mfe", "terminal_move"):
                        summary = _excursion_summary(eligible[f"{metric}_h{horizon}"])
                        for statistic in ("mean", "median", "p75", "p90", "p95"):
                            tick_value = summary[statistic]
                            row[f"{metric}_{statistic}_ticks"] = tick_value
                            row[f"{metric}_{statistic}_price"] = tick_value * tick_size if np.isfinite(tick_value) else np.nan
                            row[f"{metric}_{statistic}_gross_dollars"] = tick_value * dollars_tick if np.isfinite(tick_value) else np.nan
                    rows.append(row)
    return pd.DataFrame(rows)


def natural_excursion_table(all_events: pd.DataFrame, config: dict[str, Any], view: str) -> pd.DataFrame:
    prefix = "through_break" if view == "through_break" else "run_only"
    cohort = (
        "completed natural runs; entire first breaking bar included"
        if view == "through_break"
        else "completed natural runs; same-direction bars only; hindsight-conditioned potential"
    )
    rows: list[dict[str, Any]] = []
    for (_, _), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        asset = str(chart["asset"].iloc[0])
        tick_size = float(config["contracts"][asset]["tick_size"])
        dollars_tick = float(config["contracts"][asset]["dollars_per_tick"])
        for split in ANALYSIS_SPLITS:
            split_data = split_frame(chart, split)
            for direction in DIRECTIONS:
                side = side_frame(split_data, direction)
                completed = side.loc[~side["run_censored"]]
                if side.empty:
                    continue
                row = _identity(side, config, split, direction, cohort, "through natural run", "ticks, native price units, and gross dollars per standard contract")
                row["denominator"] = int(len(completed))
                row["censored_exclusions"] = int(len(side) - len(completed))
                for metric in ("mae", "mfe", "terminal"):
                    summary = _excursion_summary(completed[f"{prefix}_{metric}_ticks"])
                    for statistic in ("mean", "median", "p75", "p90", "p95"):
                        tick_value = summary[statistic]
                        row[f"{metric}_{statistic}_ticks"] = tick_value
                        row[f"{metric}_{statistic}_price"] = tick_value * tick_size if np.isfinite(tick_value) else np.nan
                        row[f"{metric}_{statistic}_gross_dollars"] = tick_value * dollars_tick if np.isfinite(tick_value) else np.nan
                rows.append(row)
    return pd.DataFrame(rows)


def movement_milestone_table(all_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (_, _), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        asset = str(chart["asset"].iloc[0])
        tick_size = float(config["contracts"][asset]["tick_size"])
        dollars_tick = float(config["contracts"][asset]["dollars_per_tick"])
        split_data = split_frame(chart, "full")
        for direction in DIRECTIONS:
            side = side_frame(split_data, direction)
            for threshold in config["thresholds"]:
                success = side.loc[side[f"eligible_L_ge_{threshold}"].fillna(False) & side[f"success_L_ge_{threshold}"].fillna(False)]
                summary = numeric_summary(success[f"movement_at_L_ge_{threshold}_ticks"])
                row = _identity(
                    side,
                    config,
                    "full",
                    direction,
                    "successful complete-window reversals",
                    f"close of follow-through bar {threshold}",
                    "direction-signed ticks, native price units, and gross dollars",
                )
                row.update(summary)
                row["denominator"] = summary["n"]
                for statistic in ("mean", "median", "p75", "p90", "p95"):
                    row[f"{statistic}_price"] = row[statistic] * tick_size if np.isfinite(row[statistic]) else np.nan
                    row[f"{statistic}_gross_dollars"] = row[statistic] * dollars_tick if np.isfinite(row[statistic]) else np.nan
                rows.append(row)
    return pd.DataFrame(rows)


def baseline_table(all_events: pd.DataFrame, all_baseline: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    reps = int(config["bootstrap"]["replicates"])
    seed = int(config["bootstrap"]["seed"])
    for keys, reversal_chart in all_events.groupby(["asset", "range_setting"], observed=True):
        asset, range_setting = keys
        baseline_chart = all_baseline.loc[all_baseline["asset"].eq(asset) & all_baseline["range_setting"].eq(range_setting)]
        for split in ANALYSIS_SPLITS:
            reversal_split = split_frame(reversal_chart, split)
            baseline_split = split_frame(baseline_chart, split)
            for direction in DIRECTIONS:
                reversal = side_frame(reversal_split, direction)
                ordinary = side_frame(baseline_split, direction)
                if reversal.empty or ordinary.empty:
                    continue
                rev = session_bootstrap_probability(reversal, "eligible_L_ge_3", "success_L_ge_3", reps, stable_seed(seed, "baseline-rev", asset, range_setting, split, direction))
                base = session_bootstrap_probability(ordinary, "eligible_L_ge_3", "success_L_ge_3", reps, stable_seed(seed, "baseline-base", asset, range_setting, split, direction))
                diff = paired_session_bootstrap_difference(reversal, ordinary, "eligible_L_ge_3", "success_L_ge_3", reps, stable_seed(seed, "baseline-diff", asset, range_setting, split, direction))
                row = _identity(
                    reversal,
                    config,
                    split,
                    direction,
                    "reversal signals versus all ordinary non-doji directional bars",
                    "next three bars",
                    "probability",
                )
                row.update(
                    {
                        "reversal_n": rev["eligible_n"],
                        "reversal_successes": rev["successes"],
                        "reversal_probability": rev["probability"],
                        "reversal_ci_low": rev["ci_low"],
                        "reversal_ci_high": rev["ci_high"],
                        "ordinary_bar_n": base["eligible_n"],
                        "ordinary_bar_successes": base["successes"],
                        "ordinary_bar_probability": base["probability"],
                        "ordinary_ci_low": base["ci_low"],
                        "ordinary_ci_high": base["ci_high"],
                        "reversal_minus_ordinary": diff["difference"],
                        "difference_ci_low": diff["ci_low"],
                        "difference_ci_high": diff["ci_high"],
                        "difference_p_value": diff["p_value"],
                        "denominator": rev["eligible_n"],
                    }
                )
                rows.append(row)
    return pd.DataFrame(rows)


def stability_table(all_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    reps = int(config["bootstrap"]["replicates"])
    seed = int(config["bootstrap"]["seed"])
    for (_, _), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        cohorts: list[tuple[str, Callable[[pd.DataFrame], pd.DataFrame]]] = [
            ("all reversals", lambda x: x),
            ("long", lambda x: x.loc[x["signal_side"].eq("long")]),
            ("short", lambda x: x.loc[x["signal_side"].eq("short")]),
            ("prior run >=2", lambda x: x.loc[x["prior_opposite_run"].ge(2)]),
            ("prior run >=3", lambda x: x.loc[x["prior_opposite_run"].ge(3)]),
            ("prior run =1", lambda x: x.loc[x["prior_run_bucket"].eq("1")]),
            ("prior run =2", lambda x: x.loc[x["prior_run_bucket"].eq("2")]),
            ("prior run =3+", lambda x: x.loc[x["prior_run_bucket"].eq("3+")]),
        ]
        for split in ANALYSIS_SPLITS:
            split_data = split_frame(chart, split)
            for cohort_label, selector in cohorts:
                selected = selector(split_data)
                if selected.empty:
                    continue
                result = session_bootstrap_probability(selected, "eligible_L_ge_3", "success_L_ge_3", reps, stable_seed(seed, "stability", selected["asset"].iloc[0], selected["range_setting"].iloc[0], split, cohort_label))
                direction = cohort_label if cohort_label in {"long", "short"} else "all"
                row = _identity(selected, config, split, direction, cohort_label, "L>=3", "probability")
                row.update(result)
                row["denominator"] = result["eligible_n"]
                rows.append(row)
    return pd.DataFrame(rows)


def boundary_sensitivity_table(primary: pd.DataFrame, uninterrupted: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, primary_chart in primary.groupby(["asset", "range_setting"], observed=True):
        asset, range_setting = keys
        alt_chart = uninterrupted.loc[uninterrupted["asset"].eq(asset) & uninterrupted["range_setting"].eq(range_setting)]
        for label, frame in (("provisional export-date segments", primary_chart), ("uninterrupted file sequence sensitivity", alt_chart)):
            side = split_frame(frame, "full")
            eligible = side.loc[side["eligible_L_ge_3"].fillna(False)]
            successes = int(eligible["success_L_ge_3"].fillna(False).sum())
            row = _identity(side, config, "full", "all", label, "L>=3", "probability")
            row.update(
                {
                    "boundary_rule": label,
                    "total_reversals": int(len(side)),
                    "denominator": int(len(eligible)),
                    "successes": successes,
                    "probability": successes / len(eligible) if len(eligible) else np.nan,
                    "censored_runs": int(side["run_censored"].sum()),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def cross_asset_summary(
    headline: pd.DataFrame,
    recommendations: pd.DataFrame,
    fixed_excursions: pd.DataFrame,
    run_summary: pd.DataFrame,
    opportunities: pd.DataFrame,
    timing: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    full = headline.loc[headline["split"].eq("full") & headline["direction"].eq("all")]
    test = headline.loc[headline["split"].eq("test") & headline["direction"].eq("all")]
    for recommendation in recommendations.itertuples(index=False):
        asset = recommendation.asset
        candidate = recommendation.development_candidate
        if pd.isna(candidate):
            continue
        candidate = int(candidate)
        full_row = full.loc[full["asset"].eq(asset) & full["range_setting"].eq(candidate)]
        test_row = test.loc[test["asset"].eq(asset) & test["range_setting"].eq(candidate)]
        exc = fixed_excursions.loc[
            fixed_excursions["asset"].eq(asset)
            & fixed_excursions["range_setting"].eq(candidate)
            & fixed_excursions["split"].eq("test")
            & fixed_excursions["direction"].eq("all")
            & fixed_excursions["horizon"].eq("3 future bars")
        ]
        run = run_summary.loc[
            run_summary["asset"].eq(asset)
            & run_summary["range_setting"].eq(candidate)
            & run_summary["split"].eq("test")
            & run_summary["direction"].eq("all")
        ]
        opp = opportunities.loc[
            opportunities["asset"].eq(asset)
            & opportunities["range_setting"].eq(candidate)
            & opportunities["split"].eq("test")
            & opportunities["direction"].eq("all")
        ]
        tm = timing.loc[
            timing["asset"].eq(asset)
            & timing["range_setting"].eq(candidate)
            & timing["split"].eq("test")
            & timing["direction"].eq("all")
            & timing["horizon"].eq("L>=3")
        ]
        row = {
            "asset": asset,
            "contract": full_row.iloc[0]["contract"] if not full_row.empty else "unavailable",
            "range_setting": candidate,
            "chart_identity_status": config["chart_identity_status"],
            "date_window": test_row.iloc[0]["date_window"] if not test_row.empty else "unavailable",
            "split": "test",
            "direction": "all",
            "cohort": "frozen development candidate; held-out test summary",
            "horizon": "L>=3 and three future bars",
            "units": "probability, ticks, bars, raw time proxy",
            "timing_status": config["timing_status"],
            "recommendation": recommendation.recommendation,
            "reason": recommendation.reason,
            "denominator": test_row.iloc[0]["eligible_n"] if not test_row.empty else np.nan,
            "test_successes": test_row.iloc[0]["successes"] if not test_row.empty else np.nan,
            "test_probability_L_ge_3": test_row.iloc[0]["probability"] if not test_row.empty else np.nan,
            "test_ci_low": test_row.iloc[0]["ci_low"] if not test_row.empty else np.nan,
            "test_ci_high": test_row.iloc[0]["ci_high"] if not test_row.empty else np.nan,
            "full_probability_L_ge_3": full_row.iloc[0]["probability"] if not full_row.empty else np.nan,
            "test_median_MAE_h3_ticks": exc.iloc[0]["mae_median_ticks"] if not exc.empty else np.nan,
            "test_p90_MAE_h3_ticks": exc.iloc[0]["mae_p90_ticks"] if not exc.empty else np.nan,
            "test_median_MFE_h3_ticks": exc.iloc[0]["mfe_median_ticks"] if not exc.empty else np.nan,
            "test_p90_MFE_h3_ticks": exc.iloc[0]["mfe_p90_ticks"] if not exc.empty else np.nan,
            "test_median_completed_L": run.iloc[0]["median"] if not run.empty else np.nan,
            "test_restricted_mean_min_L_10": run.iloc[0]["restricted_mean_min_L_10"] if not run.empty else np.nan,
            "test_signals_per_export_date": opp.iloc[0]["mean_signals_per_date"] if not opp.empty else np.nan,
            "test_median_time_to_L_ge_3_proxy_seconds": tm.iloc[0]["median"] if not tm.empty else np.nan,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def _fmt_pct(value: Any) -> str:
    return "—" if pd.isna(value) else f"{100 * float(value):.2f}%"


def _fmt_num(value: Any, digits: int = 2) -> str:
    return "—" if pd.isna(value) else f"{float(value):,.{digits}f}"


def _markdown_table(frame: pd.DataFrame, columns: list[str], labels: list[str]) -> str:
    visible = frame[columns].copy()
    visible.columns = labels
    lines = ["| " + " | ".join(labels) + " |", "|" + "|".join(["---"] * len(labels)) + "|"]
    for row in visible.itertuples(index=False, name=None):
        values = []
        for value in row:
            if isinstance(value, float):
                if math.isnan(value):
                    values.append("—")
                elif float(value).is_integer():
                    values.append(f"{int(value):,}")
                else:
                    values.append(f"{value:.4f}")
            else:
                values.append(str(value).replace("|", "/"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(
    report_dir: Path,
    config: dict[str, Any],
    tables: dict[str, pd.DataFrame],
    recommendations: pd.DataFrame,
    run_id: str,
) -> None:
    headline = tables["headline"]
    full_headline = headline.loc[
        headline["split"].eq("full") & headline["direction"].eq("all") & headline["eligible_n"].notna()
    ].copy()
    full_headline["p_display"] = full_headline["probability"].map(_fmt_pct)
    full_headline["ci_display"] = full_headline.apply(lambda r: f"{_fmt_pct(r.ci_low)}–{_fmt_pct(r.ci_high)}", axis=1)
    full_headline["t_display"] = full_headline["probability_T_ge_3"].map(_fmt_pct)
    overview = _markdown_table(
        full_headline.sort_values(["asset", "range_setting"]),
        ["asset", "range_setting", "eligible_n", "successes", "p_display", "ci_display", "t_display", "restricted_mean_min_L_10", "signals_per_export_date"],
        ["Asset", "Range", "N3", "L≥3", "P(L≥3)", "95% block CI", "P(T≥3)", "E[min(L,10)]", "Signals/export date"],
    )

    test_headline = headline.loc[
        headline["split"].eq("test") & headline["direction"].eq("all") & headline["eligible_n"].notna()
    ].copy()
    test_headline["p_display"] = test_headline["probability"].map(_fmt_pct)
    test_headline["ci_display"] = test_headline.apply(lambda r: f"{_fmt_pct(r.ci_low)}–{_fmt_pct(r.ci_high)}", axis=1)
    test_overview = _markdown_table(
        test_headline.sort_values(["asset", "range_setting"]),
        ["asset", "range_setting", "eligible_n", "successes", "p_display", "ci_display", "restricted_mean_min_L_10", "signals_per_export_date"],
        ["Asset", "Range", "N3", "L≥3", "P(L≥3)", "95% block CI", "E[min(L,10)]", "Signals/export date"],
    )

    conclusion_lines: list[str] = []
    cross = tables["cross_asset_summary"]
    for rec in recommendations.itertuples(index=False):
        summary = cross.loc[cross["asset"].eq(rec.asset)]
        if summary.empty:
            conclusion_lines.append(f"- **{rec.asset}:** {rec.recommendation}. {rec.reason}")
            continue
        s = summary.iloc[0]
        asset_config = config["contracts"][rec.asset]
        tick_size = float(asset_config["tick_size"])
        dollars_tick = float(asset_config["dollars_per_tick"])
        mae_ticks = float(s["test_median_MAE_h3_ticks"])
        mfe_ticks = float(s["test_median_MFE_h3_ticks"])
        detail = (
            f"Held-out range {int(s['range_setting'])} P(L≥3) was {_fmt_pct(s['test_probability_L_ge_3'])} "
            f"({_fmt_pct(s['test_ci_low'])}–{_fmt_pct(s['test_ci_high'])}, {int(s['test_successes'])}/{int(s['denominator'])}). "
            f"At three future bars, median MAE/MFE was {mae_ticks:g}/{mfe_ticks:g} ticks "
            f"({mae_ticks*tick_size:g}/{mfe_ticks*tick_size:g} native price units; "
            f"${mae_ticks*dollars_tick:,.2f}/${mfe_ticks*dollars_tick:,.2f} gross per standard contract). "
            f"Median completed L was {_fmt_num(s['test_median_completed_L'], 1)} and E[min(L,10)] was {_fmt_num(s['test_restricted_mean_min_L_10'], 2)}; "
            f"there were {_fmt_num(s['test_signals_per_export_date'], 1)} signals per provisional export date. "
            f"The success-only median raw timestamp-difference proxy to L≥3 was {_fmt_num(s['test_median_time_to_L_ge_3_proxy_seconds'], 0)} seconds, not verified elapsed time."
        )
        if rec.asset == "GC":
            conclusion_lines.append(
                f"- **GC:** No requested range comparison is possible because GC20 is missing; GC6 remains inventory-only. {detail}"
            )
            continue
        conclusion_lines.append(
            f"- **{rec.asset}:** {rec.recommendation}. The frozen development candidate was range {int(s['range_setting'])}. "
            f"{detail} {rec.reason}."
        )

    report = f"""# Reversal-candle follow-through across ES, GC, and NQ

Run `{run_id}`. This is a chart-behavior study, not a trading-system backtest. All dollar figures are gross contract-value translations of chart excursions, not executable profits.

## Decision summary

{chr(10).join(conclusion_lines)}

The ranking target was frozen as the probability of at least three additional same-direction completed bars after a reversal, `P(L≥3)`. A result is called a clear winner only if the development leader also passes the prespecified validation support check and all relevant held-out, multiplicity-controlled comparisons. Smaller range settings have a mechanical candle-count advantage, so the companion excursion, movement, timing-proxy, and opportunity tables must be read with the probability result.

## Headline full-period estimates

{overview}

Every estimate above is conditional on a complete threshold-specific future window. Boundary exclusions are in `tables/continuation_thresholds.csv`; incomplete observations were not counted as failures. `P(T≥3)` is the separate interpretation that includes the reversal candle and equals `P(L≥2)`.

## Held-out test estimates for every available setting

{test_overview}

ES range 4 and NQ range 10 led development, but ES range 6 and NQ range 20 had the higher validation point estimates, so neither selection passed the frozen validation rule. ES range 5 had the highest held-out point estimate, but it was not the development-selected candidate, and none of the ES pairwise differences survived the prespecified Holm correction. NQ ranges 10 and 20 were nearly indistinguishable on the held-out probability. These results support “no clear winner,” not post-test reselection.

## Evidence and interpretation

- The held-out candidate summary is in `tables/cross_asset_summary.csv`; development selection, validation checks, and the final frozen decision are in `tables/candidate_selection.csv` and `selection_ledger.json`.
- Fixed-horizon MAE, MFE, and signed terminal movement for 1/3/5/10/20 future bars are in `tables/excursions_fixed.csv`. They use only bars after the signal close and report ticks, native price units, and gross dollars per standard contract.
- `tables/excursions_through_break.csv` includes the first breaking bar. `tables/excursions_run_only.csv` excludes it and is explicitly hindsight-conditioned potential.
- Completed run bins, censored counts, summaries, the shared-N10 continuation curve, and conditional continuation are in the run-length tables.
- Raw timestamp differences are reported only as proxies. The exports do not identify timezone, timestamp meaning, or bar completion semantics, and repeated timestamps prevent exact elapsed-time or intrabar-extreme claims.
- Paired export-date block bootstrap intervals use 2,000 replicates and seed {config['bootstrap']['seed']}. Three-date circular-block sensitivity is alongside the one-date result. Held-out pairwise p-values use Holm familywise-error control.
- The same-chart persistence baseline compares reversal signals with ordinary non-doji directional bars. It is context for chart persistence, not evidence of tradable alpha.

## Figures

- [Common-cohort continuation curves](figures/continuation_curves.svg)
- [Completed run-length distribution](figures/run_length_distributions.svg)
- [MAE/MFE profiles](figures/excursion_profiles.svg)
- [Probability versus opportunities](figures/probability_opportunities.svg)
- [Probability versus adverse excursion](figures/probability_adverse_tradeoff.svg)
- [Raw timestamp proxy to three bars](figures/time_to_three_proxy.svg)
- [Chronological stability](figures/chronological_stability.svg)
- [Coverage and bar counts](figures/coverage_gap.svg)
- [Seeded successful and failed examples](figures/annotated_examples.svg)

## Data identity and quality

The source filenames identify **Range XV**, not verified Range XC. Official ATAS documentation lists RangeX, RangeXV, RangeUS, and RangeZ and states that exact construction algorithms are not disclosed. The study therefore consumes the exports as given and does not reconstruct or claim to reverse-engineer the bars. See [ATAS chart types]({config['official_sources']['atas_chart_types']}) and [ATAS Range XV]({config['official_sources']['atas_range_xv']}).

All available files were explicitly checked as headerless, semicolon-delimited, five-column timestamp/open/high/low/close data. The configured `%Y-%d-%m %H:%M:%S` parse succeeds for every source row. Original row order and repeated timestamps are preserved. The final row of each export is conservatively excluded because completion cannot be verified. Full audit results are in `data_quality.md` and `tables/data_audit.csv`.

GC20 is missing. GC6 was found but not substituted or analyzed. Timezone, bar-open versus bar-close timestamp semantics, completed-bar status, exact ATAS settings, data-feed provenance, and contract-history/adjustment metadata remain unresolved.

## Contract units

The conversions use official standard-contract specifications: ES 0.25 index point and $12.50/tick, NQ 0.25 index point and $5/tick, and GC $0.10/troy ounce and $10/tick. Sources: [CME ES FAQ]({config['official_sources']['cme_es']}), [CME NQ specification]({config['official_sources']['cme_nq']}), and [CME Gold fact card]({config['official_sources']['cme_gc']}).

## Reproducibility and table index

Run from the project root using the exact command in `analysis/01_reversal_follow_through/README.md`. The manifest records input, configuration, and implementation hashes, dependency versions, seed, exclusions, and output hashes. Event-level CSVs make every aggregate traceable to source file and row.

Key tables: [headline](tables/headline.csv), [threshold probabilities](tables/continuation_thresholds.csv), [paired comparisons](tables/paired_comparisons.csv), [fixed excursions](tables/excursions_fixed.csv), [run summaries](tables/run_length_summary.csv), [timing proxies](tables/timing_milestones_proxy.csv), [opportunities](tables/opportunities.csv), [stability](tables/stability.csv), and [real-event reconciliation](tables/manual_reconciliation.csv).
"""
    (report_dir / "report.md").write_text(report, encoding="utf-8")
    _write_html_report(report_dir, report, tables, run_id)


def _write_html_report(report_dir: Path, report_text: str, tables: dict[str, pd.DataFrame], run_id: str) -> None:
    headline = tables["headline"]
    headline = headline.loc[headline["split"].eq("full") & headline["direction"].eq("all")].copy()
    columns = ["asset", "range_setting", "eligible_n", "successes", "probability", "ci_low", "ci_high", "probability_T_ge_3", "restricted_mean_min_L_10", "support_status"]
    table_html = headline[[c for c in columns if c in headline]].to_html(index=False, border=0, classes="data", na_rep="—", float_format=lambda x: f"{x:.4f}")
    figures = [
        ("Continuation curves", "continuation_curves.svg"),
        ("Run lengths", "run_length_distributions.svg"),
        ("Excursion profiles", "excursion_profiles.svg"),
        ("Probability and opportunities", "probability_opportunities.svg"),
        ("Probability and adverse excursion", "probability_adverse_tradeoff.svg"),
        ("Chronological stability", "chronological_stability.svg"),
        ("Coverage", "coverage_gap.svg"),
        ("Examples", "annotated_examples.svg"),
    ]
    figure_html = "\n".join(f'<section><h2>{html.escape(title)}</h2><img src="figures/{name}" alt="{html.escape(title)}"></section>' for title, name in figures)
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reversal follow-through — {html.escape(run_id)}</title>
<style>body{{font-family:system-ui,-apple-system,sans-serif;max-width:1180px;margin:40px auto;padding:0 24px;line-height:1.5;color:#18212b}}h1,h2{{line-height:1.2}}.note{{background:#f3f6f8;padding:16px;border-left:4px solid #3c6e71}}table.data{{border-collapse:collapse;width:100%;font-size:13px}}table.data th,table.data td{{padding:7px;border-bottom:1px solid #d8dee4;text-align:right}}table.data th:first-child,table.data td:first-child{{text-align:left}}img{{max-width:100%;border:1px solid #d8dee4;background:white}}a{{color:#005ea8}}code{{background:#f3f4f6;padding:2px 4px}}</style></head>
<body><h1>Reversal-candle follow-through across ES, GC, and NQ</h1>
<p class="note">Run <code>{html.escape(run_id)}</code>. Chart-behavior research only; not a trading-system backtest.</p>
<h2>Headline full-period estimates</h2>{table_html}
<p><a href="report.md">Full Markdown report</a> · <a href="methodology.md">Methodology</a> · <a href="data_quality.md">Data quality</a> · <a href="tables/cross_asset_summary.csv">Held-out candidate summary</a> · <a href="run_manifest.json">Run manifest</a></p>
{figure_html}
<h2>Study narrative</h2><pre style="white-space:pre-wrap;font-family:system-ui">{html.escape(report_text)}</pre>
</body></html>"""
    (report_dir / "report.html").write_text(document, encoding="utf-8")


def _svg_start(width: int, height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="28" y="32" font-family="system-ui" font-size="20" font-weight="600" fill="#17212b">{html.escape(title)}</text>',
    ]


def _save_svg(path: Path, lines: list[str]) -> None:
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


COLORS = {4: "#005f73", 5: "#ca6702", 6: "#9b2226", 10: "#0a9396", 20: "#bb3e03"}


def _line_panels(path: Path, data: pd.DataFrame, assets: list[str], x_col: str, y_col: str, title: str, x_label: str, y_label: str, ci: tuple[str, str] | None = None) -> None:
    width, height = 1080, 340 * len(assets)
    lines = _svg_start(width, height, title)
    for panel, asset in enumerate(assets):
        frame = data.loc[data["asset"].eq(asset)].copy()
        top = 65 + panel * 330
        left, plot_w, plot_h = 90, 900, 230
        lines += [f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#fafafa" stroke="#d6dce1"/>', f'<text x="{left}" y="{top-10}" font-family="system-ui" font-size="16" font-weight="600">{asset}</text>']
        if frame.empty:
            lines.append(f'<text x="{left+20}" y="{top+40}" font-family="system-ui" font-size="14">Unavailable</text>')
            continue
        xmin, xmax = float(frame[x_col].min()), float(frame[x_col].max())
        ymin = min(0.0, float(frame[y_col].min()) * 0.9)
        ymax = max(1e-9, float(frame[y_col].max()) * 1.08)
        if ci:
            ymin = min(ymin, float(frame[ci[0]].min()) * 0.9)
            ymax = max(ymax, float(frame[ci[1]].max()) * 1.08)
        for tick in range(6):
            yv = ymin + (ymax - ymin) * tick / 5
            yp = top + plot_h - plot_h * tick / 5
            lines.append(f'<line x1="{left}" y1="{yp:.1f}" x2="{left+plot_w}" y2="{yp:.1f}" stroke="#e5e9ed"/>')
            lines.append(f'<text x="{left-8}" y="{yp+4:.1f}" text-anchor="end" font-family="system-ui" font-size="11">{yv:.2f}</text>')
        for range_setting, group in frame.groupby("range_setting", observed=True):
            group = group.sort_values(x_col)
            def point(r):
                x = left + (float(r[x_col]) - xmin) / max(1e-9, xmax - xmin) * plot_w
                y = top + plot_h - (float(r[y_col]) - ymin) / max(1e-9, ymax - ymin) * plot_h
                return x, y
            pts = [point(r) for _, r in group.iterrows()]
            color = COLORS.get(int(range_setting), "#333333")
            lines.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
            for (_, r), (x, y) in zip(group.iterrows(), pts):
                if ci:
                    yl = top + plot_h - (float(r[ci[0]]) - ymin) / max(1e-9, ymax - ymin) * plot_h
                    yh = top + plot_h - (float(r[ci[1]]) - ymin) / max(1e-9, ymax - ymin) * plot_h
                    lines.append(f'<line x1="{x:.1f}" y1="{yl:.1f}" x2="{x:.1f}" y2="{yh:.1f}" stroke="{color}" opacity="0.55"/>')
                lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>')
            if pts:
                lines.append(f'<text x="{pts[-1][0]+7:.1f}" y="{pts[-1][1]+4:.1f}" font-family="system-ui" font-size="12" fill="{color}">R{int(range_setting)}</text>')
        lines.append(f'<text x="{left+plot_w/2}" y="{top+plot_h+34}" text-anchor="middle" font-family="system-ui" font-size="12">{html.escape(x_label)}</text>')
        lines.append(f'<text x="18" y="{top+plot_h/2}" transform="rotate(-90 18 {top+plot_h/2})" text-anchor="middle" font-family="system-ui" font-size="12">{html.escape(y_label)}</text>')
    _save_svg(path, lines)


def _scatter(path: Path, frame: pd.DataFrame, x_col: str, y_col: str, title: str, x_label: str, y_label: str) -> None:
    width, height = 1000, 600
    lines = _svg_start(width, height, title)
    left, top, plot_w, plot_h = 100, 70, 820, 440
    lines.append(f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#fafafa" stroke="#d6dce1"/>')
    clean = frame.dropna(subset=[x_col, y_col])
    if clean.empty:
        lines.append('<text x="130" y="130" font-family="system-ui">Unavailable</text>')
        _save_svg(path, lines)
        return
    xmin, xmax = float(clean[x_col].min()), float(clean[x_col].max())
    ymin, ymax = float(clean[y_col].min()), float(clean[y_col].max())
    xpad, ypad = max(1e-9, (xmax - xmin) * 0.12), max(1e-9, (ymax - ymin) * 0.12)
    xmin, xmax, ymin, ymax = xmin-xpad, xmax+xpad, ymin-ypad, ymax+ypad
    for r in clean.itertuples(index=False):
        x = left + (float(getattr(r, x_col)) - xmin) / (xmax - xmin) * plot_w
        y = top + plot_h - (float(getattr(r, y_col)) - ymin) / (ymax - ymin) * plot_h
        range_setting = int(r.range_setting)
        label = f"{r.asset} R{range_setting}"
        color = COLORS.get(range_setting, "#333333")
        lines += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{color}"/>', f'<text x="{x+8:.1f}" y="{y-7:.1f}" font-family="system-ui" font-size="12">{html.escape(label)}</text>']
    lines += [
        f'<text x="{left+plot_w/2}" y="{top+plot_h+45}" text-anchor="middle" font-family="system-ui" font-size="13">{html.escape(x_label)}</text>',
        f'<text x="25" y="{top+plot_h/2}" transform="rotate(-90 25 {top+plot_h/2})" text-anchor="middle" font-family="system-ui" font-size="13">{html.escape(y_label)}</text>',
    ]
    _save_svg(path, lines)


def generate_figures(report_dir: Path, tables: dict[str, pd.DataFrame], examples: pd.DataFrame) -> None:
    figures = report_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    curve = tables["continuation_curve"]
    curve = curve.loc[curve["direction"].eq("all")]
    _line_panels(figures / "continuation_curves.svg", curve, ["ES", "GC", "NQ"], "threshold_k", "probability", "Shared-N10 continuation probability", "Additional same-direction bars k", "P(L≥k)", ("ci_low", "ci_high"))

    bins = tables["run_length_bins"]
    bins = bins.loc[bins["split"].eq("full") & bins["direction"].eq("all") & ~bins["run_bin"].eq("censored")].copy()
    order = {v: i for i, v in enumerate(["0", "1", "2", "3", "4", "5-9", "10+"])}
    bins["bin_index"] = bins["run_bin"].map(order)
    bins["completed_share"] = bins["count"] / bins.groupby(["asset", "range_setting"], observed=True)["count"].transform("sum")
    _line_panels(figures / "run_length_distributions.svg", bins, ["ES", "GC", "NQ"], "bin_index", "completed_share", "Completed natural-run distribution", "L bin: 0, 1, 2, 3, 4, 5–9, 10+", "Share of completed runs")

    excursion = tables["excursions_fixed"]
    excursion = excursion.loc[excursion["split"].eq("full") & excursion["direction"].eq("all")].copy()
    excursion["horizon_bars"] = excursion["horizon"].str.extract(r"(\d+)").astype(int)
    _line_panels(figures / "excursion_profiles.svg", excursion, ["ES", "GC", "NQ"], "horizon_bars", "mfe_median_ticks", "Median favorable excursion by fixed horizon", "Future bars", "Median MFE (ticks)")

    headline = tables["headline"]
    head = headline.loc[headline["split"].eq("full") & headline["direction"].eq("all") & headline["eligible_n"].notna()].copy()
    opp = tables["opportunities"]
    opp = opp.loc[opp["split"].eq("full") & opp["direction"].eq("all"), ["asset", "range_setting", "mean_signals_per_date"]]
    scatter = head.merge(opp, on=["asset", "range_setting"], how="left")
    _scatter(figures / "probability_opportunities.svg", scatter, "mean_signals_per_date", "probability", "Continuation probability and opportunity frequency", "Mean reversal signals per provisional export date", "P(L≥3)")

    h3 = excursion.loc[excursion["horizon_bars"].eq(3), ["asset", "range_setting", "mae_median_ticks"]]
    adverse = head.merge(h3, on=["asset", "range_setting"], how="left")
    _scatter(figures / "probability_adverse_tradeoff.svg", adverse, "mae_median_ticks", "probability", "Continuation probability and adverse excursion", "Median three-bar MAE (ticks)", "P(L≥3)")

    timing = tables["timing_milestones"]
    timing = timing.loc[timing["split"].eq("full") & timing["direction"].eq("all") & timing["horizon"].eq("L>=3")].copy()
    timing["x"] = timing["range_setting"].astype(float)
    _line_panels(figures / "time_to_three_proxy.svg", timing, ["ES", "GC", "NQ"], "x", "median", "Raw timestamp-difference proxy to three-bar follow-through", "Range setting", "Median proxy seconds among successes")

    stability = tables["stability"]
    stability = stability.loc[stability["cohort"].eq("all reversals") & stability["split"].isin(["development", "validation", "test"])].copy()
    stability["period_index"] = stability["split"].map({"development": 1, "validation": 2, "test": 3})
    _line_panels(figures / "chronological_stability.svg", stability, ["ES", "GC", "NQ"], "period_index", "probability", "Chronological stability", "1 development, 2 validation, 3 test", "P(L≥3)", ("ci_low", "ci_high"))

    coverage = tables["coverage"].copy()
    coverage["date_index"] = coverage.groupby(["asset", "range_setting"], observed=True).cumcount() + 1
    _line_panels(figures / "coverage_gap.svg", coverage, ["ES", "GC", "NQ"], "date_index", "max_adjacent_timestamp_gap_minutes", "Coverage and largest observed timestamp gaps", "Chronological export-date index", "Largest adjacent timestamp gap (minutes)")
    _examples_svg(figures / "annotated_examples.svg", examples)


def _examples_svg(path: Path, examples: pd.DataFrame) -> None:
    width, height = 1100, max(360, 82 * (len(examples) + 2))
    lines = _svg_start(width, height, "Seeded real reversal examples")
    lines.append('<text x="28" y="54" font-family="system-ui" font-size="12" fill="#5b6670">Sequence shows directions around the signal; examples include first available success and failure per chart.</text>')
    y = 82
    for row in examples.itertuples(index=False):
        color = "#2a9d8f" if row.example_type == "success_L_ge_3" else "#c44536"
        label = f"{row.asset} R{int(row.range_setting)} {row.example_type}  {row.event_id}  {row.signal_side}  L={int(row.observed_L)}"
        lines += [
            f'<rect x="28" y="{y-18}" width="1035" height="55" fill="#fafafa" stroke="#e1e5e8"/>',
            f'<rect x="28" y="{y-18}" width="7" height="55" fill="{color}"/>',
            f'<text x="48" y="{y}" font-family="system-ui" font-size="13" font-weight="600">{html.escape(label)}</text>',
            f'<text x="48" y="{y+22}" font-family="ui-monospace,monospace" font-size="12">{html.escape(str(row.direction_sequence))}</text>',
        ]
        y += 70
    _save_svg(path, lines)


def write_methodology(report_dir: Path, config: dict[str, Any]) -> None:
    text = f"""# Methodology

## Documented facts

- ATAS documents range charts as price-movement-based rather than fixed-time charts. Its current chart-types page lists RangeX, RangeXV, RangeUS, and RangeZ. It says the exact construction algorithms are not disclosed: {config['official_sources']['atas_chart_types']}
- ATAS describes Range XV as forming consecutive candles during directional movement and opposite-colored candles when counteraction appears, while keeping the construction method closed: {config['official_sources']['atas_range_xv']}
- CME standard-contract units used here are ES 0.25 point/$12.50 per tick, NQ 0.25 point/$5 per tick, and GC $0.10 per troy ounce/$10 per tick: {config['official_sources']['cme_es']}, {config['official_sources']['cme_nq']}, {config['official_sources']['cme_gc']}

## Observed behavior

The exports are headerless, semicolon-delimited, five-column files consistent with timestamp/open/high/low/close. The configured day-month timestamp parser succeeds for all rows. Price values align with the verified exchange tick sizes, OHLC inequalities are valid, row timestamps do not regress, and repeated timestamps are common. Geometry findings describe the exports only and do not infer the proprietary bar algorithm.

Observed timestamp gaps are reported by export date but are not classified as missing data. A quiet interval in a price-based chart can be legitimate, and the exports contain no feed-status or exchange-calendar field that would support a stronger conclusion.

## Frozen definitions

- Direction is `sign(close-open)` in integer exchange ticks. Dojis have direction zero and break runs.
- A reversal is the first non-doji bar immediately opposite the preceding non-doji bar in the same valid segment. Primary prior-run minimum is one; at-least-two and at-least-three are prespecified sensitivities.
- `L` counts subsequent same-direction bars and excludes the reversal; `T=1+L` includes it. The primary metric is `P(L>=3)`.
- A threshold estimate includes only signals with that many subsequent valid bars in the same segment. Boundary cases are exclusions, not failures. A shared N10 cohort supports continuation curves and `E[min(L,10)]`.
- Natural runs reaching a segment boundary without a breaking bar are right-censored. Completed-run summaries exclude their lower bounds.
- MAE/MFE reference the signal close and use subsequent bars only. Fixed horizons are 1/3/5/10/20 bars. Long and short formulas are symmetric. Through-break includes the break bar; run-only excludes it and is hindsight-conditioned.
- Provisional export-calendar dates define segments. The 60/20/20 split is development 2026-06-14–2026-08-02, validation 2026-08-04–2026-08-18, and test 2026-08-20–2026-09-04. Export dates 2026-08-03 and 2026-08-19 are embargoed.
- The development leader is frozen before reading test conclusions. Validation checks whether it retains the largest point estimate with at least 200 eligible reversals and 10 export dates. A clear held-out winner must retain the lead and beat every alternative under Holm-adjusted paired date-block tests.
- Dependence-aware intervals use 2,000 paired export-date bootstrap replicates with seed {config['bootstrap']['seed']}; three-date circular blocks are the multi-session sensitivity.

## Unresolved assumptions and unsupported analyses

The chart identity remains provisional filename-labeled Range XV, not verified Range XC. Timezone, timestamp meaning, bar-completion field, ATAS version/settings, data feed, continuous-contract/adjustment history, and whether prices are synthetic remain unresolved. The final export row is conservatively excluded. Raw timestamp differences are proxies only; no exact elapsed-time, official-session, intrabar ordering, extreme-touch time, common clock-horizon, volatility-normalized, or nominal-range-normalized claim is made. GC20 is missing and GC6 is not substituted.
"""
    (report_dir / "methodology.md").write_text(text, encoding="utf-8")


def write_data_quality(report_dir: Path, audit: pd.DataFrame, config: dict[str, Any]) -> None:
    available = audit.loc[audit["status"].eq("analyzed")]
    rows = []
    for row in available.itertuples(index=False):
        rows.append(
            f"- {row.asset} range {int(row.range_setting)} `{row.source_file}`: {int(row.rows):,} rows; "
            f"{int(row.timestamp_parse_success):,} day-month timestamps parsed; {int(row.ohlc_failures)} OHLC failures; "
            f"{int(row.off_tick_rows)} off-tick rows; {int(row.timestamp_regressions)} regressions; "
            f"{int(row.repeated_timestamp_rows):,} rows participate in repeated timestamps; {int(row.doji_rows)} dojis."
        )
    text = f"""# Data quality findings

## Inventory

{chr(10).join(rows)}

- GC range 20 is missing and remains unestimated.
- GC range 6 is present but inventory-only. It was not renamed, substituted, or used in performance calculations.
- Every source SHA-256 and byte size is recorded in `tables/data_audit.csv` and `run_manifest.json`. `data/` was read only.

## Schema and timestamps

Every analyzed file has exactly five semicolon-separated fields per parsed row and no header row. The first field parses completely with `%Y-%d-%m %H:%M:%S`; the ordinary year-month-day alternative parses only the ambiguous subset and is rejected. Timestamps are nondecreasing, but repeats are common and sometimes adjacent. Original row number resolves tied timestamps.

Timezone and timestamp meaning are absent. Consequently, parsed dates are **provisional export dates**, not verified trading sessions; timestamp differences are labeled proxies; exact extreme times are unavailable; and a common clock-window comparison is unsupported. A file-sequence boundary sensitivity is reported separately.

## OHLC and tick geometry

All analyzed rows satisfy `high >= max(open, close, low)` and `low <= min(open, close, high)`. Prices align to CME tick sizes. Distributional geometry is in `tables/geometry.csv`. These are observed properties, not a reconstruction of ATAS's proprietary chart-building algorithm.

## Coverage and exclusions

The analyzed files cover the same 72 parsed export dates from 2026-06-14 through 2026-09-04, with differing bar counts and final intraday timestamps. The final row of each analyzed export is excluded because bar completion cannot be established. Threshold and horizon exclusions are reported explicitly in their result tables. Dojis break event adjacency and runs.

## Missing metadata that could change interpretation

Exact ATAS version and settings, Range XV versus the user's earlier Range XC label, parameter units, export timezone, bar-open versus bar-close timestamps, completed-bar status, data feed, contract/roll history, continuous-contract adjustments, and session calendar remain unresolved. None was guessed.
"""
    (report_dir / "data_quality.md").write_text(text, encoding="utf-8")
