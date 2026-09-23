from __future__ import annotations

import math
import zlib
from typing import Any

import numpy as np
import pandas as pd


def stable_seed(base: int, *parts: Any) -> int:
    return (int(base) + zlib.crc32("|".join(map(str, parts)).encode())) % (2**32 - 1)


def numeric_summary(series: pd.Series) -> dict[str, float | int]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if values.empty:
        return {k: math.nan for k in ("mean", "median", "p75", "p90", "p95", "max")} | {"n": 0}
    q = values.quantile([0.5, 0.75, 0.9, 0.95, 1.0])
    return {
        "n": int(len(values)),
        "mean": float(values.mean()),
        "median": float(q.loc[0.5]),
        "p75": float(q.loc[0.75]),
        "p90": float(q.loc[0.9]),
        "p95": float(q.loc[0.95]),
        "max": float(q.loc[1.0]),
    }


def session_bootstrap_mean(
    frame: pd.DataFrame, column: str, reps: int, seed: int
) -> tuple[float, float, int]:
    clean = frame.loc[pd.to_numeric(frame[column], errors="coerce").notna()].copy()
    if clean.empty:
        return math.nan, math.nan, 0
    grouped = clean.groupby("export_date", observed=True)[column].agg(["sum", "size"])
    numerators = grouped["sum"].to_numpy(dtype=float)
    denominators = grouped["size"].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(grouped), size=(reps, len(grouped)))
    den = denominators[indices].sum(axis=1)
    draws = numerators[indices].sum(axis=1) / den
    low, high = np.quantile(draws, [0.025, 0.975])
    return float(low), float(high), int(len(draws))


def summarize_events(all_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    periods = ("full", "development", "validation", "test")
    directions = ("all", "long", "short")
    reps = int(config["bootstrap"]["replicates"])
    base_seed = int(config["bootstrap"]["seed"])
    for (asset, range_setting), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        tick_size = float(config["contracts"][asset]["tick_size"])
        dollar_tick = float(config["contracts"][asset]["dollars_per_tick"])
        for period in periods:
            period_frame = chart if period == "full" else chart.loc[chart["split"].eq(period)]
            for prior_min in config["prior_run_minimums"]:
                prior_frame = period_frame.loc[period_frame["prior_opposite_run"].ge(prior_min)]
                for direction in directions:
                    selected = prior_frame if direction == "all" else prior_frame.loc[prior_frame["signal_side"].eq(direction)]
                    if selected.empty:
                        continue
                    eligible = selected.loc[selected["eligible_next_bar"]]
                    conditioned = eligible.loc[eligible["next_bar_same_direction"]]
                    adverse = numeric_summary(conditioned["adverse_from_follow_open_ticks"])
                    ci_low, ci_high, valid_reps = session_bootstrap_mean(
                        conditioned,
                        "adverse_from_follow_open_ticks",
                        reps,
                        stable_seed(base_seed, asset, range_setting, period, prior_min, direction),
                    )
                    row = {
                        "asset": asset,
                        "contract": str(chart["contract"].iloc[0]),
                        "range_setting": int(range_setting),
                        "chart_identity_status": config["chart_identity_status"],
                        "date_window": f"{selected['export_date'].min()} to {selected['export_date'].max()}",
                        "period": period,
                        "direction": direction,
                        "prior_run_minimum": int(prior_min),
                        "cohort": f"reversal after >={prior_min} opposite candle(s), with next bar closing in reversal direction",
                        "reference": "follow-through candle open",
                        "units": "ticks, native price units, gross dollars per standard contract",
                        "timing_status": config["timing_status"],
                        "total_reversals": int(len(selected)),
                        "eligible_next_bar": int(len(eligible)),
                        "same_direction_next_bar": int(len(conditioned)),
                        "same_direction_probability": len(conditioned) / len(eligible) if len(eligible) else np.nan,
                        "boundary_exclusions": int(len(selected) - len(eligible)),
                        "denominator": int(len(conditioned)),
                        "mean_adverse_ticks": adverse["mean"],
                        "mean_adverse_ci_low_ticks": ci_low,
                        "mean_adverse_ci_high_ticks": ci_high,
                        "median_adverse_ticks": adverse["median"],
                        "p75_adverse_ticks": adverse["p75"],
                        "p90_adverse_ticks": adverse["p90"],
                        "p95_adverse_ticks": adverse["p95"],
                        "max_adverse_ticks": adverse["max"],
                        "zero_adverse_count": int(conditioned["adverse_from_follow_open_ticks"].eq(0).sum()),
                        "zero_adverse_share": conditioned["adverse_from_follow_open_ticks"].eq(0).mean() if len(conditioned) else np.nan,
                        "valid_bootstrap_replicates": valid_reps,
                    }
                    for prefix, column in (
                        ("adverse_from_signal_close", "adverse_from_signal_close_ticks"),
                        ("favorable_from_follow_open", "favorable_from_follow_open_ticks"),
                        ("close_progress_from_follow_open", "close_progress_from_follow_open_ticks"),
                        ("directional_open_gap", "directional_open_gap_ticks"),
                    ):
                        summary = numeric_summary(conditioned[column])
                        for statistic in ("mean", "median", "p90", "p95"):
                            row[f"{prefix}_{statistic}_ticks"] = summary[statistic]
                    tick_fields = [key for key in row if key.endswith("_ticks")]
                    for key in tick_fields:
                        value = row[key]
                        base = key[:-6]
                        row[f"{base}_price"] = value * tick_size if pd.notna(value) else np.nan
                        row[f"{base}_gross_dollars"] = value * dollar_tick if pd.notna(value) else np.nan
                    rows.append(row)
    return pd.DataFrame(rows)

