from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .stats import numeric_summary, session_bootstrap_mean, stable_seed
from .time_of_day import assign_clock_window


def compute_leg_events(
    bars: pd.DataFrame, events: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    """Measure each reversal's uninterrupted same-direction leg, including the reversal."""
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy().reset_index(drop=True)
    result = events.copy().reset_index(drop=True)
    if result.empty:
        return result

    direction = usable["direction"].to_numpy(dtype=np.int8)
    sequence = usable["sequence_id"].to_numpy(dtype=np.int64)
    timestamps = usable["parsed_timestamp"].to_numpy(dtype="datetime64[ns]")
    source_rows = usable["source_row"].to_numpy(dtype=np.int64)
    n_bars = len(usable)

    remaining_run = np.zeros(n_bars, dtype=np.int32)
    completed = np.zeros(n_bars, dtype=bool)
    for position in range(n_bars - 1, -1, -1):
        if direction[position] == 0:
            continue
        next_position = position + 1
        if next_position >= n_bars or sequence[next_position] != sequence[position]:
            remaining_run[position] = 1
            completed[position] = False
        elif direction[next_position] == direction[position]:
            remaining_run[position] = 1 + remaining_run[next_position]
            completed[position] = completed[next_position]
        else:
            remaining_run[position] = 1
            completed[position] = True

    positions = result["bar_index"].to_numpy(dtype=np.int64)
    leg_candles = remaining_run[positions]
    leg_completed = completed[positions]
    last_positions = positions + leg_candles - 1
    break_positions = last_positions + 1
    break_safe = np.minimum(break_positions, n_bars - 1)
    minimum_candles = int(config["leg_duration"]["minimum_candles_including_reversal"])
    qualifies = leg_completed & (leg_candles >= minimum_candles)

    duration_seconds = np.full(len(result), np.nan)
    complete_indices = np.flatnonzero(leg_completed)
    if len(complete_indices):
        duration_seconds[complete_indices] = (
            timestamps[last_positions[complete_indices]] - timestamps[positions[complete_indices]]
        ) / np.timedelta64(1, "s")

    result["leg_completed"] = leg_completed
    result["leg_censored"] = ~leg_completed
    result["leg_candle_count_including_reversal"] = leg_candles
    result["leg_additional_candle_count"] = leg_candles - 1
    result["leg_at_least_three"] = qualifies
    result["leg_last_bar_index"] = last_positions
    result["leg_last_source_row"] = source_rows[last_positions]
    result["leg_last_timestamp"] = timestamps[last_positions]
    result["leg_break_source_row"] = pd.array(
        np.where(leg_completed, source_rows[break_safe], np.nan), dtype="Float64"
    )
    result["leg_break_direction"] = pd.array(
        np.where(leg_completed, direction[break_safe], np.nan), dtype="Float64"
    )
    result["leg_break_type"] = np.where(
        ~leg_completed,
        "export-date boundary",
        np.where(direction[break_safe] == 0, "doji", "opposite candle"),
    )
    result["leg_duration_proxy_seconds"] = duration_seconds
    result["leg_duration_proxy_minutes"] = duration_seconds / 60.0
    result["leg_definition"] = (
        "consecutive close-minus-open direction from reversal through final same-direction candle"
    )
    result["timing_status"] = (
        "raw timestamp-difference proxy; timezone and bar timestamp meaning unresolved"
    )
    return result


def summarize_leg_duration(
    all_leg_events: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    reps = int(config["bootstrap"]["replicates"])
    seed = int(config["bootstrap"]["seed"])
    for (asset, range_setting), chart in all_leg_events.groupby(
        ["asset", "range_setting"], observed=True
    ):
        completed = chart.loc[chart["leg_completed"]]
        qualifying = completed.loc[completed["leg_at_least_three"]]
        duration = numeric_summary(qualifying["leg_duration_proxy_minutes"])
        candles = numeric_summary(qualifying["leg_candle_count_including_reversal"])
        ci_low, ci_high, valid_reps = session_bootstrap_mean(
            qualifying,
            "leg_duration_proxy_minutes",
            reps,
            stable_seed(seed, asset, range_setting, "leg_duration_mean"),
        )
        rows.append(
            {
                "asset": asset,
                "contract": str(chart["contract"].iloc[0]),
                "range_setting": int(range_setting),
                "total_reversals": int(len(chart)),
                "completed_legs": int(len(completed)),
                "censored_legs": int((~chart["leg_completed"]).sum()),
                "legs_at_least_three": int(len(qualifying)),
                "share_at_least_three_of_completed": len(qualifying) / len(completed) if len(completed) else np.nan,
                "mean_duration_proxy_minutes": duration["mean"],
                "mean_duration_ci_low_minutes": ci_low,
                "mean_duration_ci_high_minutes": ci_high,
                "median_duration_proxy_minutes": duration["median"],
                "p75_duration_proxy_minutes": duration["p75"],
                "p90_duration_proxy_minutes": duration["p90"],
                "p95_duration_proxy_minutes": duration["p95"],
                "max_duration_proxy_minutes": duration["max"],
                "zero_duration_count": int(qualifying["leg_duration_proxy_seconds"].eq(0).sum()),
                "zero_duration_share": qualifying["leg_duration_proxy_seconds"].eq(0).mean() if len(qualifying) else np.nan,
                "mean_candles_in_leg": candles["mean"],
                "median_candles_in_leg": candles["median"],
                "p90_candles_in_leg": candles["p90"],
                "valid_bootstrap_replicates": valid_reps,
                "cohort": "completed reversal legs with at least three candles including reversal",
                "timing_status": "raw timestamp-difference proxy; not verified elapsed time",
            }
        )
    return pd.DataFrame(rows).sort_values(["asset", "range_setting"]).reset_index(drop=True)


def _clock_labels(window_minutes: int) -> pd.DataFrame:
    rows = []
    for index in range(1440 // window_minutes):
        start = index * window_minutes
        end = (start + window_minutes) % 1440
        rows.append(
            {
                "window_index": index,
                "window_start": f"{start // 60:02d}:{start % 60:02d}",
                "window_end": f"{end // 60:02d}:{end % 60:02d}",
                "half_hour_window": f"{start // 60:02d}:{start % 60:02d}–{end // 60:02d}:{end % 60:02d}",
            }
        )
    return pd.DataFrame(rows)


def leg_duration_by_clock(
    all_leg_events: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    window_minutes = int(config["time_of_day"]["window_minutes"])
    reps = int(config["bootstrap"]["replicates"])
    seed = int(config["bootstrap"]["seed"])
    labels = _clock_labels(window_minutes)
    rows: list[dict[str, Any]] = []
    for (asset, range_setting), chart in all_leg_events.groupby(
        ["asset", "range_setting"], observed=True
    ):
        chart = chart.copy()
        chart["window_index"] = assign_clock_window(
            chart["parsed_timestamp"], window_minutes
        )["window_index"]
        first = chart.iloc[0]
        for window in labels.itertuples(index=False):
            selected = chart.loc[chart["window_index"].eq(window.window_index)]
            completed = selected.loc[selected["leg_completed"]]
            qualifying = completed.loc[completed["leg_at_least_three"]]
            duration = numeric_summary(qualifying["leg_duration_proxy_minutes"])
            candles = numeric_summary(qualifying["leg_candle_count_including_reversal"])
            ci_low, ci_high, valid_reps = session_bootstrap_mean(
                qualifying,
                "leg_duration_proxy_minutes",
                reps,
                stable_seed(seed, asset, range_setting, window.window_index, "leg_duration_clock"),
            )
            rows.append(
                {
                    "asset": asset,
                    "contract": str(first["contract"]),
                    "range_setting": int(range_setting),
                    "window_index": int(window.window_index),
                    "window_start": window.window_start,
                    "window_end": window.window_end,
                    "half_hour_window": window.half_hour_window,
                    "total_reversals": int(len(selected)),
                    "reversal_active_export_dates": int(selected["export_date"].nunique()),
                    "completed_legs": int(len(completed)),
                    "censored_legs": int((~selected["leg_completed"]).sum()),
                    "legs_at_least_three": int(len(qualifying)),
                    "qualifying_active_export_dates": int(qualifying["export_date"].nunique()),
                    "share_at_least_three_of_completed": len(qualifying) / len(completed) if len(completed) else np.nan,
                    "mean_duration_proxy_minutes": duration["mean"],
                    "mean_duration_ci_low_minutes": ci_low,
                    "mean_duration_ci_high_minutes": ci_high,
                    "median_duration_proxy_minutes": duration["median"],
                    "p75_duration_proxy_minutes": duration["p75"],
                    "p90_duration_proxy_minutes": duration["p90"],
                    "p95_duration_proxy_minutes": duration["p95"],
                    "max_duration_proxy_minutes": duration["max"],
                    "zero_duration_share": qualifying["leg_duration_proxy_seconds"].eq(0).mean() if len(qualifying) else np.nan,
                    "mean_candles_in_leg": candles["mean"],
                    "median_candles_in_leg": candles["median"],
                    "p90_candles_in_leg": candles["p90"],
                    "valid_bootstrap_replicates": valid_reps,
                    "timing_basis": "reversal candle raw timestamp",
                    "timing_status": "raw timestamp-difference proxy; timezone and timestamp meaning unresolved",
                }
            )
    return pd.DataFrame(rows)


def _clock_minutes(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":"))
    if hour not in range(24) or minute not in range(60):
        raise ValueError(f"Invalid session clock time: {value}")
    return hour * 60 + minute


def assign_leg_session(
    timestamps: pd.Series, sessions: list[dict[str, str]]
) -> pd.DataFrame:
    """Assign half-open raw-clock sessions, including windows that cross midnight."""
    clock_minutes = timestamps.dt.hour * 60 + timestamps.dt.minute
    labels = pd.Series(pd.NA, index=timestamps.index, dtype="string")
    orders = pd.Series(pd.NA, index=timestamps.index, dtype="Int64")
    windows = pd.Series(pd.NA, index=timestamps.index, dtype="string")
    for order, session in enumerate(sessions):
        start = _clock_minutes(session["start"])
        end = _clock_minutes(session["end"])
        if start == end:
            raise ValueError(f"Session {session['name']} has identical start and end")
        mask = (
            (clock_minutes >= start) & (clock_minutes < end)
            if start < end
            else (clock_minutes >= start) | (clock_minutes < end)
        )
        if (mask & labels.notna()).any():
            raise ValueError(f"Session {session['name']} overlaps another configured session")
        labels.loc[mask] = session["name"]
        orders.loc[mask] = order
        windows.loc[mask] = f"{session['start']}–{session['end']}"
    return pd.DataFrame(
        {"session": labels, "session_order": orders, "session_window": windows}
    )


def leg_duration_by_session(
    all_leg_events: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    """Summarize qualifying reversal legs by the reversal's configured raw-clock session."""
    sessions = config["leg_duration"]["sessions"]
    reps = int(config["bootstrap"]["replicates"])
    seed = int(config["bootstrap"]["seed"])
    rows: list[dict[str, Any]] = []
    for (asset, range_setting), chart in all_leg_events.groupby(
        ["asset", "range_setting"], observed=True
    ):
        chart = chart.copy()
        assignments = assign_leg_session(chart["parsed_timestamp"], sessions)
        chart["session"] = assignments["session"]
        first = chart.iloc[0]
        for order, session in enumerate(sessions):
            selected = chart.loc[chart["session"].eq(session["name"])]
            completed = selected.loc[selected["leg_completed"]]
            qualifying = completed.loc[completed["leg_at_least_three"]]
            duration = numeric_summary(qualifying["leg_duration_proxy_minutes"])
            candles = numeric_summary(qualifying["leg_candle_count_including_reversal"])
            ci_low, ci_high, valid_reps = session_bootstrap_mean(
                qualifying,
                "leg_duration_proxy_minutes",
                reps,
                stable_seed(seed, asset, range_setting, session["name"], "leg_duration_session"),
            )
            rows.append(
                {
                    "asset": asset,
                    "contract": str(first["contract"]),
                    "range_setting": int(range_setting),
                    "session_order": order,
                    "session": session["name"],
                    "session_start": session["start"],
                    "session_end": session["end"],
                    "session_window": f"{session['start']}–{session['end']}",
                    "total_reversals": int(len(selected)),
                    "reversal_active_export_dates": int(selected["export_date"].nunique()),
                    "completed_legs": int(len(completed)),
                    "censored_legs": int((~selected["leg_completed"]).sum()),
                    "legs_at_least_three": int(len(qualifying)),
                    "qualifying_active_export_dates": int(qualifying["export_date"].nunique()),
                    "share_at_least_three_of_completed": len(qualifying) / len(completed) if len(completed) else np.nan,
                    "mean_duration_proxy_minutes": duration["mean"],
                    "mean_duration_ci_low_minutes": ci_low,
                    "mean_duration_ci_high_minutes": ci_high,
                    "median_duration_proxy_minutes": duration["median"],
                    "p75_duration_proxy_minutes": duration["p75"],
                    "p90_duration_proxy_minutes": duration["p90"],
                    "p95_duration_proxy_minutes": duration["p95"],
                    "max_duration_proxy_minutes": duration["max"],
                    "zero_duration_share": qualifying["leg_duration_proxy_seconds"].eq(0).mean() if len(qualifying) else np.nan,
                    "mean_candles_in_leg": candles["mean"],
                    "median_candles_in_leg": candles["median"],
                    "p90_candles_in_leg": candles["p90"],
                    "valid_bootstrap_replicates": valid_reps,
                    "timing_basis": "reversal candle raw timestamp",
                    "timing_status": "raw timestamp-difference proxy; timezone and timestamp meaning unresolved",
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["asset", "range_setting", "session_order"]
    ).reset_index(drop=True)


def rank_leg_windows(
    time_table: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    minimum_legs = int(config["leg_duration"]["minimum_qualifying_legs_per_window"])
    minimum_dates = int(config["leg_duration"]["minimum_active_export_dates"])
    top_n = int(config["leg_duration"]["top_windows_per_criterion"])
    rows: list[dict[str, Any]] = []
    for (asset, range_setting), chart in time_table.groupby(
        ["asset", "range_setting"], observed=True
    ):
        supported = chart.loc[
            chart["legs_at_least_three"].ge(minimum_legs)
            & chart["qualifying_active_export_dates"].ge(minimum_dates)
        ].copy()
        for criterion, column, ascending in (
            ("longest mean duration", "mean_duration_proxy_minutes", False),
            ("shortest mean duration", "mean_duration_proxy_minutes", True),
            ("longest median duration", "median_duration_proxy_minutes", False),
        ):
            ordered = supported.sort_values(
                [column, "window_index"], ascending=[ascending, True], na_position="last"
            ).head(top_n)
            for rank, row in enumerate(ordered.itertuples(index=False), start=1):
                rows.append(
                    {
                        "asset": asset,
                        "range_setting": int(range_setting),
                        "criterion": criterion,
                        "rank": rank,
                        "half_hour_window": row.half_hour_window,
                        "legs_at_least_three": int(row.legs_at_least_three),
                        "qualifying_active_export_dates": int(row.qualifying_active_export_dates),
                        "metric_value_minutes": getattr(row, column),
                        "mean_duration_proxy_minutes": row.mean_duration_proxy_minutes,
                        "mean_duration_ci_low_minutes": row.mean_duration_ci_low_minutes,
                        "mean_duration_ci_high_minutes": row.mean_duration_ci_high_minutes,
                        "median_duration_proxy_minutes": row.median_duration_proxy_minutes,
                        "p90_duration_proxy_minutes": row.p90_duration_proxy_minutes,
                        "mean_candles_in_leg": row.mean_candles_in_leg,
                        "share_at_least_three_of_completed": row.share_at_least_three_of_completed,
                    }
                )
    return pd.DataFrame(rows)


def reconcile_leg_sample(
    bars: pd.DataFrame,
    leg_events: pd.DataFrame,
    seed: int,
    sample_size: int = 12,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy().reset_index(drop=True)
    candidates = leg_events.loc[leg_events["leg_completed"]]
    take = min(sample_size, len(candidates))
    rng = np.random.default_rng(seed)
    selected = candidates.iloc[rng.choice(len(candidates), size=take, replace=False)] if take else candidates
    rows = []
    matches = 0
    for event in selected.itertuples(index=False):
        position = int(event.bar_index)
        side = int(event.direction)
        sequence = int(usable.iloc[position]["sequence_id"])
        cursor = position
        while (
            cursor + 1 < len(usable)
            and int(usable.iloc[cursor + 1]["sequence_id"]) == sequence
            and int(usable.iloc[cursor + 1]["direction"]) == side
        ):
            cursor += 1
        completed = (
            cursor + 1 < len(usable)
            and int(usable.iloc[cursor + 1]["sequence_id"]) == sequence
        )
        candle_count = cursor - position + 1
        seconds = (
            usable.iloc[cursor]["parsed_timestamp"]
            - usable.iloc[position]["parsed_timestamp"]
        ).total_seconds()
        match = (
            completed == bool(event.leg_completed)
            and candle_count == int(event.leg_candle_count_including_reversal)
            and seconds == float(event.leg_duration_proxy_seconds)
        )
        matches += int(match)
        rows.append(
            {
                "event_id": event.event_id,
                "asset": event.asset,
                "range_setting": int(event.range_setting),
                "source_row": int(event.source_row),
                "stored_candle_count": int(event.leg_candle_count_including_reversal),
                "independent_candle_count": candle_count,
                "stored_duration_proxy_seconds": event.leg_duration_proxy_seconds,
                "independent_duration_proxy_seconds": seconds,
                "all_match": match,
            }
        )
    return pd.DataFrame(rows), {"sampled": take, "matches": matches, "all_match": matches == take}
