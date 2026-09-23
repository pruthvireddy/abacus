from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _window_metrics(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    entry: int,
    side: int,
) -> tuple[int, int, int, int, int]:
    if len(highs) == 0:
        return 0, 0, 0, 0, 0
    if side == 1:
        favorable = highs - entry
        adverse = entry - lows
        terminal = int(closes[-1] - entry)
    else:
        favorable = entry - lows
        adverse = highs - entry
        terminal = int(entry - closes[-1])
    mfe = max(0, int(favorable.max()))
    mae = max(0, int(adverse.max()))
    mfe_idx = int(np.flatnonzero(favorable == mfe)[0] + 1) if mfe > 0 else 0
    mae_idx = int(np.flatnonzero(adverse == mae)[0] + 1) if mae > 0 else 0
    return mae, mfe, terminal, mae_idx, mfe_idx


def add_excursions_and_timing(
    bars: pd.DataFrame, events: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy().reset_index(drop=True)
    highs = usable["high_ticks"].to_numpy(dtype=np.int64)
    lows = usable["low_ticks"].to_numpy(dtype=np.int64)
    closes = usable["close_ticks"].to_numpy(dtype=np.int64)
    times = usable["parsed_timestamp"].to_numpy(dtype="datetime64[ns]")

    result = events.copy()
    for horizon in config["fixed_horizons"]:
        for name in ("mae", "mfe", "terminal_move", "mae_bar_index", "mfe_bar_index", "elapsed_proxy_seconds"):
            result[f"{name}_h{horizon}"] = pd.NA

    for threshold in config["thresholds"]:
        result[f"time_to_L_ge_{threshold}_proxy_seconds"] = pd.NA
        result[f"movement_at_L_ge_{threshold}_ticks"] = pd.NA

    for name in (
        "through_break_mae_ticks",
        "through_break_mfe_ticks",
        "through_break_terminal_ticks",
        "through_break_mae_bar_index",
        "through_break_mfe_bar_index",
        "break_bar_index",
        "time_to_break_proxy_seconds",
        "run_only_mae_ticks",
        "run_only_mfe_ticks",
        "run_only_terminal_ticks",
        "run_only_mae_bar_index",
        "run_only_mfe_bar_index",
        "time_to_last_run_bar_proxy_seconds",
    ):
        result[name] = pd.NA

    for row_idx, event in result.iterrows():
        pos = int(event["bar_index"])
        side = int(event["direction"])
        entry = int(event["signal_reference_ticks"])
        for horizon in config["fixed_horizons"]:
            if not bool(event[f"eligible_L_ge_{horizon}"]) if horizon in config["thresholds"] else False:
                continue
            end = pos + horizon
            if end >= len(usable) or usable.loc[end, "sequence_id"] != usable.loc[pos, "sequence_id"]:
                continue
            metrics = _window_metrics(
                highs[pos + 1 : end + 1], lows[pos + 1 : end + 1], closes[pos + 1 : end + 1], entry, side
            )
            for name, value in zip(
                ("mae", "mfe", "terminal_move", "mae_bar_index", "mfe_bar_index"), metrics
            ):
                result.at[row_idx, f"{name}_h{horizon}"] = value
            result.at[row_idx, f"elapsed_proxy_seconds_h{horizon}"] = int(
                (times[end] - times[pos]) / np.timedelta64(1, "s")
            )

        for threshold in config["thresholds"]:
            if bool(event[f"eligible_L_ge_{threshold}"]) and bool(event[f"success_L_ge_{threshold}"]):
                target = pos + threshold
                result.at[row_idx, f"time_to_L_ge_{threshold}_proxy_seconds"] = int(
                    (times[target] - times[pos]) / np.timedelta64(1, "s")
                )
                signed_move = int(closes[target] - entry) if side == 1 else int(entry - closes[target])
                result.at[row_idx, f"movement_at_L_ge_{threshold}_ticks"] = signed_move

        if not bool(event["run_censored"]):
            run = int(event["observed_L"])
            break_pos = pos + run + 1
            metrics = _window_metrics(
                highs[pos + 1 : break_pos + 1],
                lows[pos + 1 : break_pos + 1],
                closes[pos + 1 : break_pos + 1],
                entry,
                side,
            )
            for name, value in zip(
                (
                    "through_break_mae_ticks",
                    "through_break_mfe_ticks",
                    "through_break_terminal_ticks",
                    "through_break_mae_bar_index",
                    "through_break_mfe_bar_index",
                ),
                metrics,
            ):
                result.at[row_idx, name] = value
            result.at[row_idx, "break_bar_index"] = run + 1
            result.at[row_idx, "time_to_break_proxy_seconds"] = int(
                (times[break_pos] - times[pos]) / np.timedelta64(1, "s")
            )

            run_metrics = _window_metrics(
                highs[pos + 1 : pos + run + 1],
                lows[pos + 1 : pos + run + 1],
                closes[pos + 1 : pos + run + 1],
                entry,
                side,
            )
            for name, value in zip(
                (
                    "run_only_mae_ticks",
                    "run_only_mfe_ticks",
                    "run_only_terminal_ticks",
                    "run_only_mae_bar_index",
                    "run_only_mfe_bar_index",
                ),
                run_metrics,
            ):
                result.at[row_idx, name] = value
            if run > 0:
                result.at[row_idx, "time_to_last_run_bar_proxy_seconds"] = int(
                    (times[pos + run] - times[pos]) / np.timedelta64(1, "s")
                )
            else:
                result.at[row_idx, "time_to_last_run_bar_proxy_seconds"] = 0

    numeric_columns = [
        column
        for column in result.columns
        if column.startswith(("mae_", "mfe_", "terminal_", "elapsed_", "time_to_", "movement_", "through_", "run_only_", "break_bar"))
    ]
    for column in numeric_columns:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce").astype("Float64")
    return result

