from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .stats import stable_seed
from .time_of_day import assign_clock_window


def compute_hold_events(
    bars: pd.DataFrame, events: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    """Evaluate two more same-direction bars after the confirmation candle."""
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy().reset_index(drop=True)
    result = events.loc[events["next_bar_same_direction"]].copy().reset_index(drop=True)
    if result.empty:
        return result

    strict_bars = int(config["hold_time"]["strict_additional_bars"])
    horizon = int(config["hold_time"]["eventual_search_horizon_bars"])
    if strict_bars != 2:
        raise ValueError("This implementation defines the strict target as exactly two additional bars")
    if horizon < 2:
        raise ValueError("eventual_search_horizon_bars must be at least 2")

    signal_positions = result["bar_index"].to_numpy(dtype=np.int64)
    confirmation_positions = signal_positions + 1
    sides = result["direction"].to_numpy(dtype=np.int8)
    direction = usable["direction"].to_numpy(dtype=np.int8)
    sequence = usable["sequence_id"].to_numpy(dtype=np.int64)
    timestamps = usable["parsed_timestamp"].to_numpy(dtype="datetime64[ns]")
    source_rows = usable["source_row"].to_numpy(dtype=np.int64)
    n_bars = len(usable)

    result["confirmation_bar_index"] = confirmation_positions
    result["confirmation_source_row"] = source_rows[confirmation_positions]
    result["confirmation_parsed_timestamp"] = timestamps[confirmation_positions]

    strict_targets = confirmation_positions + strict_bars
    strict_eligible = strict_targets < n_bars
    strict_safe = np.minimum(strict_targets, n_bars - 1)
    strict_eligible &= sequence[strict_safe] == sequence[confirmation_positions]
    strict_success = np.zeros(len(result), dtype=bool)
    eligible_indices = np.flatnonzero(strict_eligible)
    if len(eligible_indices):
        confirmation = confirmation_positions[eligible_indices]
        side = sides[eligible_indices]
        strict_success[eligible_indices] = (
            (direction[confirmation + 1] == side)
            & (direction[confirmation + 2] == side)
        )

    result["strict_eligible_two_more"] = strict_eligible
    result["strict_two_more_success"] = strict_success
    result["strict_target_bar_index"] = pd.array(
        np.where(strict_success, strict_targets, np.nan), dtype="Float64"
    )
    result["strict_target_source_row"] = pd.array(
        np.where(strict_success, source_rows[strict_safe], np.nan), dtype="Float64"
    )
    strict_seconds = np.full(len(result), np.nan)
    success_indices = np.flatnonzero(strict_success)
    if len(success_indices):
        strict_seconds[success_indices] = (
            timestamps[strict_targets[success_indices]]
            - timestamps[confirmation_positions[success_indices]]
        ) / np.timedelta64(1, "s")
    result["strict_hold_proxy_seconds"] = strict_seconds
    result["strict_hold_proxy_minutes"] = strict_seconds / 60.0
    result["strict_bars_to_target"] = np.where(strict_success, strict_bars, np.nan)

    eventual_last = confirmation_positions + horizon
    eventual_eligible = eventual_last < n_bars
    eventual_safe = np.minimum(eventual_last, n_bars - 1)
    eventual_eligible &= sequence[eventual_safe] == sequence[confirmation_positions]
    target_offsets = np.full(len(result), -1, dtype=np.int16)
    open_indices = np.flatnonzero(eventual_eligible)
    for offset in range(2, horizon + 1):
        if not len(open_indices):
            break
        confirmation = confirmation_positions[open_indices]
        side = sides[open_indices]
        hit = (
            (direction[confirmation + offset - 1] == side)
            & (direction[confirmation + offset] == side)
        )
        target_offsets[open_indices[hit]] = offset
        open_indices = open_indices[~hit]
    eventual_success = target_offsets.ge(0) if isinstance(target_offsets, pd.Series) else target_offsets >= 0
    eventual_targets = confirmation_positions + np.maximum(target_offsets, 0)
    result["eventual_horizon_bars"] = horizon
    result["eventual_eligible_horizon"] = eventual_eligible
    result["eventual_pair_success"] = eventual_success
    result["eventual_bars_to_target"] = pd.array(
        np.where(eventual_success, target_offsets, np.nan), dtype="Float64"
    )
    result["eventual_target_source_row"] = pd.array(
        np.where(eventual_success, source_rows[np.minimum(eventual_targets, n_bars - 1)], np.nan),
        dtype="Float64",
    )
    eventual_seconds = np.full(len(result), np.nan)
    eventual_indices = np.flatnonzero(eventual_success)
    if len(eventual_indices):
        eventual_seconds[eventual_indices] = (
            timestamps[eventual_targets[eventual_indices]]
            - timestamps[confirmation_positions[eventual_indices]]
        ) / np.timedelta64(1, "s")
    result["eventual_hold_proxy_seconds"] = eventual_seconds
    result["eventual_hold_proxy_minutes"] = eventual_seconds / 60.0
    result["hold_time_status"] = (
        "raw timestamp-difference proxy; timezone and bar timestamp meaning unresolved"
    )
    result["strict_definition"] = (
        "the two bars immediately after confirmation both close in signal direction"
    )
    result["eventual_definition"] = (
        f"first pair of consecutive signal-direction bars among the next {horizon} bars"
    )
    return result


def _numeric_summary(series: pd.Series) -> dict[str, float | int]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    if values.empty:
        return {"n": 0, "mean": math.nan, "median": math.nan, "p25": math.nan, "p75": math.nan, "p90": math.nan}
    quantiles = values.quantile([0.25, 0.50, 0.75, 0.90])
    return {
        "n": int(len(values)),
        "mean": float(values.mean()),
        "median": float(quantiles.loc[0.50]),
        "p25": float(quantiles.loc[0.25]),
        "p75": float(quantiles.loc[0.75]),
        "p90": float(quantiles.loc[0.90]),
    }


def _date_block_rate_ci(
    frame: pd.DataFrame,
    eligible_column: str,
    success_column: str,
    reps: int,
    seed: int,
) -> tuple[float, float]:
    grouped = frame.groupby("export_date", observed=True).agg(
        eligible=(eligible_column, "sum"), success=(success_column, "sum")
    )
    grouped = grouped.loc[grouped["eligible"].gt(0)]
    if grouped.empty:
        return math.nan, math.nan
    eligible = grouped["eligible"].to_numpy(dtype=float)
    success = grouped["success"].to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(grouped), size=(reps, len(grouped)))
    denominators = eligible[indices].sum(axis=1)
    draws = success[indices].sum(axis=1) / denominators
    low, high = np.quantile(draws, [0.025, 0.975])
    return float(low), float(high)


def summarize_hold_events(all_hold_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    reps = int(config["bootstrap"]["replicates"])
    seed = int(config["bootstrap"]["seed"])
    for (asset, range_setting), chart in all_hold_events.groupby(
        ["asset", "range_setting"], observed=True
    ):
        strict_eligible = chart.loc[chart["strict_eligible_two_more"]]
        strict_success = strict_eligible.loc[strict_eligible["strict_two_more_success"]]
        eventual_eligible = chart.loc[chart["eventual_eligible_horizon"]]
        eventual_success = eventual_eligible.loc[eventual_eligible["eventual_pair_success"]]
        strict_time = _numeric_summary(strict_success["strict_hold_proxy_minutes"])
        eventual_time = _numeric_summary(eventual_success["eventual_hold_proxy_minutes"])
        eventual_bars = _numeric_summary(eventual_success["eventual_bars_to_target"])
        strict_ci = _date_block_rate_ci(
            chart,
            "strict_eligible_two_more",
            "strict_two_more_success",
            reps,
            stable_seed(seed, asset, range_setting, "strict_hold_rate"),
        )
        eventual_ci = _date_block_rate_ci(
            chart,
            "eventual_eligible_horizon",
            "eventual_pair_success",
            reps,
            stable_seed(seed, asset, range_setting, "eventual_pair_rate"),
        )
        rows.append(
            {
                "asset": asset,
                "contract": str(chart["contract"].iloc[0]),
                "range_setting": int(range_setting),
                "conditioned_confirmation_events": int(len(chart)),
                "strict_eligible": int(len(strict_eligible)),
                "strict_success": int(len(strict_success)),
                "strict_success_probability": len(strict_success) / len(strict_eligible) if len(strict_eligible) else np.nan,
                "strict_success_ci_low": strict_ci[0],
                "strict_success_ci_high": strict_ci[1],
                "strict_mean_hold_proxy_minutes": strict_time["mean"],
                "strict_median_hold_proxy_minutes": strict_time["median"],
                "strict_p25_hold_proxy_minutes": strict_time["p25"],
                "strict_p75_hold_proxy_minutes": strict_time["p75"],
                "strict_p90_hold_proxy_minutes": strict_time["p90"],
                "strict_zero_time_count": int(strict_success["strict_hold_proxy_seconds"].eq(0).sum()),
                "strict_zero_time_share": strict_success["strict_hold_proxy_seconds"].eq(0).mean() if len(strict_success) else np.nan,
                "eventual_horizon_bars": int(config["hold_time"]["eventual_search_horizon_bars"]),
                "eventual_eligible": int(len(eventual_eligible)),
                "eventual_success": int(len(eventual_success)),
                "eventual_success_probability": len(eventual_success) / len(eventual_eligible) if len(eventual_eligible) else np.nan,
                "eventual_success_ci_low": eventual_ci[0],
                "eventual_success_ci_high": eventual_ci[1],
                "eventual_mean_bars_to_target": eventual_bars["mean"],
                "eventual_median_bars_to_target": eventual_bars["median"],
                "eventual_p90_bars_to_target": eventual_bars["p90"],
                "eventual_mean_hold_proxy_minutes": eventual_time["mean"],
                "eventual_median_hold_proxy_minutes": eventual_time["median"],
                "eventual_p90_hold_proxy_minutes": eventual_time["p90"],
                "timing_status": "raw timestamp-difference proxy; not verified elapsed time",
            }
        )
    return pd.DataFrame(rows).sort_values(["asset", "range_setting"]).reset_index(drop=True)


def hold_time_by_clock(all_hold_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    window_minutes = int(config["time_of_day"]["window_minutes"])
    labels = []
    for index in range(1440 // window_minutes):
        start = index * window_minutes
        end = (start + window_minutes) % 1440
        labels.append(
            {
                "window_index": index,
                "window_start": f"{start // 60:02d}:{start % 60:02d}",
                "window_end": f"{end // 60:02d}:{end % 60:02d}",
                "half_hour_window": f"{start // 60:02d}:{start % 60:02d}–{end // 60:02d}:{end % 60:02d}",
            }
        )
    clock_grid = pd.DataFrame(labels)
    rows: list[dict[str, Any]] = []
    for (asset, range_setting), chart in all_hold_events.groupby(
        ["asset", "range_setting"], observed=True
    ):
        chart = chart.copy()
        chart["window_index"] = assign_clock_window(
            chart["confirmation_parsed_timestamp"], window_minutes
        )["window_index"]
        first = chart.iloc[0]
        for window in clock_grid.itertuples(index=False):
            selected = chart.loc[chart["window_index"].eq(window.window_index)]
            strict_eligible = selected.loc[selected["strict_eligible_two_more"]]
            strict_success = strict_eligible.loc[strict_eligible["strict_two_more_success"]]
            eventual_eligible = selected.loc[selected["eventual_eligible_horizon"]]
            eventual_success = eventual_eligible.loc[eventual_eligible["eventual_pair_success"]]
            strict_time = _numeric_summary(strict_success["strict_hold_proxy_minutes"])
            eventual_time = _numeric_summary(eventual_success["eventual_hold_proxy_minutes"])
            eventual_bars = _numeric_summary(eventual_success["eventual_bars_to_target"])
            rows.append(
                {
                    "asset": asset,
                    "contract": str(first["contract"]),
                    "range_setting": int(range_setting),
                    "window_index": int(window.window_index),
                    "window_start": window.window_start,
                    "window_end": window.window_end,
                    "half_hour_window": window.half_hour_window,
                    "conditioned_confirmation_events": int(len(selected)),
                    "active_export_dates": int(selected["export_date"].nunique()),
                    "strict_eligible": int(len(strict_eligible)),
                    "strict_success": int(len(strict_success)),
                    "strict_success_probability": len(strict_success) / len(strict_eligible) if len(strict_eligible) else np.nan,
                    "strict_mean_hold_proxy_minutes": strict_time["mean"],
                    "strict_median_hold_proxy_minutes": strict_time["median"],
                    "strict_p25_hold_proxy_minutes": strict_time["p25"],
                    "strict_p75_hold_proxy_minutes": strict_time["p75"],
                    "strict_p90_hold_proxy_minutes": strict_time["p90"],
                    "strict_zero_time_share": strict_success["strict_hold_proxy_seconds"].eq(0).mean() if len(strict_success) else np.nan,
                    "eventual_eligible": int(len(eventual_eligible)),
                    "eventual_success": int(len(eventual_success)),
                    "eventual_success_probability": len(eventual_success) / len(eventual_eligible) if len(eventual_eligible) else np.nan,
                    "eventual_mean_bars_to_target": eventual_bars["mean"],
                    "eventual_median_bars_to_target": eventual_bars["median"],
                    "eventual_p90_bars_to_target": eventual_bars["p90"],
                    "eventual_mean_hold_proxy_minutes": eventual_time["mean"],
                    "eventual_median_hold_proxy_minutes": eventual_time["median"],
                    "eventual_p90_hold_proxy_minutes": eventual_time["p90"],
                    "timing_basis": "confirmation candle raw timestamp",
                    "timing_status": "raw timestamp-difference proxy; timezone and timestamp meaning unresolved",
                }
            )
    return pd.DataFrame(rows)


def rank_hold_windows(
    time_table: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    settings = config["hold_time"]
    min_eligible = int(settings["minimum_eligible_events_per_window"])
    min_success = int(settings["minimum_successes_per_window"])
    min_dates = int(settings["minimum_active_export_dates"])
    top_n = int(settings["top_windows_per_criterion"])
    ranking_rows: list[dict[str, Any]] = []
    balanced_rows: list[dict[str, Any]] = []
    for (asset, range_setting), chart in time_table.groupby(
        ["asset", "range_setting"], observed=True
    ):
        supported = chart.loc[
            chart["strict_eligible"].ge(min_eligible)
            & chart["strict_success"].ge(min_success)
            & chart["active_export_dates"].ge(min_dates)
        ].copy()
        if supported.empty:
            continue
        criteria = (
            ("shortest median strict hold", "strict_median_hold_proxy_minutes", True, "minutes"),
            ("shortest p90 strict hold", "strict_p90_hold_proxy_minutes", True, "minutes"),
            ("highest strict success rate", "strict_success_probability", False, "share"),
            ("shortest median eventual hold", "eventual_median_hold_proxy_minutes", True, "minutes"),
        )
        for criterion, column, ascending, units in criteria:
            ordered = supported.sort_values(
                [column, "window_index"], ascending=[ascending, True], na_position="last"
            ).head(top_n)
            for rank, row in enumerate(ordered.itertuples(index=False), start=1):
                ranking_rows.append(
                    {
                        "asset": asset,
                        "range_setting": int(range_setting),
                        "criterion": criterion,
                        "rank": rank,
                        "half_hour_window": row.half_hour_window,
                        "metric_value": getattr(row, column),
                        "units": units,
                        "strict_eligible": int(row.strict_eligible),
                        "strict_success": int(row.strict_success),
                        "active_export_dates": int(row.active_export_dates),
                    }
                )
        rate_cutoff = supported["strict_success_probability"].median()
        time_cutoff = supported["strict_median_hold_proxy_minutes"].median()
        balanced = supported.loc[
            supported["strict_success_probability"].ge(rate_cutoff)
            & supported["strict_median_hold_proxy_minutes"].le(time_cutoff)
        ].sort_values(
            [
                "strict_median_hold_proxy_minutes",
                "strict_p90_hold_proxy_minutes",
                "strict_success_probability",
                "window_index",
            ],
            ascending=[True, True, False, True],
        ).head(top_n)
        for rank, row in enumerate(balanced.itertuples(index=False), start=1):
            balanced_rows.append(
                {
                    "asset": asset,
                    "range_setting": int(range_setting),
                    "rank": rank,
                    "half_hour_window": row.half_hour_window,
                    "conditioned_confirmation_events": int(row.conditioned_confirmation_events),
                    "active_export_dates": int(row.active_export_dates),
                    "strict_eligible": int(row.strict_eligible),
                    "strict_success": int(row.strict_success),
                    "strict_success_probability": row.strict_success_probability,
                    "strict_median_hold_proxy_minutes": row.strict_median_hold_proxy_minutes,
                    "strict_p75_hold_proxy_minutes": row.strict_p75_hold_proxy_minutes,
                    "strict_p90_hold_proxy_minutes": row.strict_p90_hold_proxy_minutes,
                    "eventual_success_probability": row.eventual_success_probability,
                    "eventual_median_bars_to_target": row.eventual_median_bars_to_target,
                    "eventual_median_hold_proxy_minutes": row.eventual_median_hold_proxy_minutes,
                    "selection_rule": "at-or-above chart median strict success rate and at-or-below chart median hold proxy; ranked by median then p90 hold proxy",
                }
            )
    return pd.DataFrame(ranking_rows), pd.DataFrame(balanced_rows)


def reconcile_hold_sample(
    bars: pd.DataFrame,
    hold_events: pd.DataFrame,
    config: dict[str, Any],
    seed: int,
    sample_size: int = 12,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Independently re-scan a real-event sample from source-order bars."""
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy().reset_index(drop=True)
    candidates = hold_events.loc[hold_events["eventual_eligible_horizon"]]
    take = min(sample_size, len(candidates))
    rng = np.random.default_rng(seed)
    selected = candidates.iloc[rng.choice(len(candidates), size=take, replace=False)] if take else candidates
    horizon = int(config["hold_time"]["eventual_search_horizon_bars"])
    rows = []
    matches = 0
    for event in selected.itertuples(index=False):
        confirmation = int(event.confirmation_bar_index)
        side = int(event.direction)
        strict_success = all(
            int(usable.iloc[confirmation + offset]["direction"]) == side for offset in (1, 2)
        )
        eventual_offset = None
        for offset in range(2, horizon + 1):
            if (
                int(usable.iloc[confirmation + offset - 1]["direction"]) == side
                and int(usable.iloc[confirmation + offset]["direction"]) == side
            ):
                eventual_offset = offset
                break
        strict_seconds = None
        if strict_success:
            strict_seconds = (
                usable.iloc[confirmation + 2]["parsed_timestamp"]
                - usable.iloc[confirmation]["parsed_timestamp"]
            ).total_seconds()
        match = (
            strict_success == bool(event.strict_two_more_success)
            and (eventual_offset is not None) == bool(event.eventual_pair_success)
            and (
                eventual_offset is None
                or eventual_offset == int(event.eventual_bars_to_target)
            )
            and (
                strict_seconds is None
                or strict_seconds == float(event.strict_hold_proxy_seconds)
            )
        )
        matches += int(match)
        rows.append(
            {
                "event_id": event.event_id,
                "asset": event.asset,
                "range_setting": int(event.range_setting),
                "confirmation_source_row": int(event.confirmation_source_row),
                "strict_success_stored": bool(event.strict_two_more_success),
                "strict_success_independent": strict_success,
                "strict_hold_proxy_seconds_stored": event.strict_hold_proxy_seconds,
                "strict_hold_proxy_seconds_independent": strict_seconds,
                "eventual_offset_stored": event.eventual_bars_to_target,
                "eventual_offset_independent": eventual_offset,
                "all_match": match,
            }
        )
    return pd.DataFrame(rows), {"sampled": take, "matches": matches, "all_match": matches == take}
