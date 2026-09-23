from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _window_labels(window_minutes: int) -> pd.DataFrame:
    if window_minutes <= 0 or 1440 % window_minutes:
        raise ValueError("window_minutes must be a positive divisor of 1440")
    starts = np.arange(0, 1440, window_minutes, dtype=int)

    def hhmm(minutes: int) -> str:
        minutes %= 1440
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    return pd.DataFrame(
        {
            "window_index": np.arange(len(starts), dtype=int),
            "window_start": [hhmm(int(value)) for value in starts],
            "window_end": [hhmm(int(value + window_minutes)) for value in starts],
            "half_hour_window": [
                f"{hhmm(int(value))}–{hhmm(int(value + window_minutes))}" for value in starts
            ],
        }
    )


def assign_clock_window(
    timestamps: pd.Series, window_minutes: int = 30, timestamp_format: str | None = None
) -> pd.DataFrame:
    parsed = pd.to_datetime(timestamps, errors="coerce", format=timestamp_format)
    minute_of_day = parsed.dt.hour * 60 + parsed.dt.minute
    window_index = (minute_of_day // window_minutes).astype("Int64")
    labels = _window_labels(window_minutes).set_index("window_index")
    assigned = pd.DataFrame({"window_index": window_index}, index=timestamps.index)
    assigned = assigned.join(labels, on="window_index")
    return assigned


def _chart_grid(frame: pd.DataFrame, window_minutes: int) -> pd.DataFrame:
    labels = _window_labels(window_minutes)
    first = frame.iloc[0]
    labels.insert(0, "range_setting", int(first["range_setting"]))
    labels.insert(0, "contract", str(first["contract"]))
    labels.insert(0, "asset", str(first["asset"]))
    return labels


def _coverage(bars: pd.DataFrame, window_minutes: int) -> pd.DataFrame:
    usable = bars.loc[bars["bar_included"] & bars["valid_row"]].copy()
    assigned = assign_clock_window(usable["parsed_timestamp"], window_minutes)
    usable["window_index"] = assigned["window_index"]
    return (
        usable.groupby("window_index", observed=True)
        .agg(
            bar_count=("source_row", "size"),
            active_export_dates=("export_date", "nunique"),
        )
        .reset_index()
    )


def _geometry(conditioned: pd.DataFrame) -> pd.DataFrame:
    if conditioned.empty:
        return pd.DataFrame(columns=["window_index"])
    conditioned = conditioned.copy()
    adverse = "adverse_from_follow_open_ticks"
    favorable = "favorable_from_follow_open_ticks"
    conditioned["favorable_minus_adverse_ticks"] = (
        pd.to_numeric(conditioned[favorable], errors="coerce")
        - pd.to_numeric(conditioned[adverse], errors="coerce")
    )
    conditioned["favorable_exceeds_adverse"] = conditioned[favorable].gt(conditioned[adverse])
    return (
        conditioned.groupby("window_index", observed=True)
        .agg(
            conditioned_events=("event_id", "size"),
            event_active_dates=("export_date", "nunique"),
            mean_adverse_ticks=(adverse, "mean"),
            median_adverse_ticks=(adverse, "median"),
            p90_adverse_ticks=(adverse, lambda values: values.quantile(0.90)),
            mean_favorable_ticks=(favorable, "mean"),
            median_favorable_ticks=(favorable, "median"),
            p90_favorable_ticks=(favorable, lambda values: values.quantile(0.90)),
            mean_favorable_minus_adverse_ticks=("favorable_minus_adverse_ticks", "mean"),
            favorable_exceeds_adverse_share=("favorable_exceeds_adverse", "mean"),
        )
        .reset_index()
    )


def _add_conversions(table: pd.DataFrame, config: dict[str, Any], asset: str) -> pd.DataFrame:
    tick_size = float(config["contracts"][asset]["tick_size"])
    dollars_per_tick = float(config["contracts"][asset]["dollars_per_tick"])
    for column in (
        "mean_adverse_ticks",
        "median_adverse_ticks",
        "p90_adverse_ticks",
        "mean_favorable_ticks",
        "median_favorable_ticks",
        "p90_favorable_ticks",
        "mean_favorable_minus_adverse_ticks",
    ):
        if column in table:
            stem = column.removesuffix("_ticks")
            table[f"{stem}_price"] = table[column] * tick_size
            table[f"{stem}_gross_dollars"] = table[column] * dollars_per_tick
    return table


def build_signal_time_table(
    bars: pd.DataFrame, events: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    """Summarize by the reversal candle's raw export-clock window."""
    window_minutes = int(config["time_of_day"]["window_minutes"])
    grid = _chart_grid(bars, window_minutes)
    coverage = _coverage(bars, window_minutes)
    timed = events.copy()
    timed["window_index"] = assign_clock_window(
        timed["parsed_timestamp"], window_minutes
    )["window_index"]
    event_counts = (
        timed.groupby("window_index", observed=True)
        .agg(
            total_reversals=("event_id", "size"),
            eligible_reversals=("eligible_next_bar", "sum"),
            same_direction_events=("next_bar_same_direction", "sum"),
        )
        .reset_index()
    )
    geometry = _geometry(timed.loc[timed["next_bar_same_direction"]])
    table = grid.merge(coverage, on="window_index", how="left")
    table = table.merge(event_counts, on="window_index", how="left")
    table = table.merge(geometry, on="window_index", how="left")
    count_columns = (
        "bar_count",
        "active_export_dates",
        "total_reversals",
        "eligible_reversals",
        "same_direction_events",
        "conditioned_events",
        "event_active_dates",
    )
    for column in count_columns:
        table[column] = table[column].fillna(0).astype(int)
    table["same_direction_probability"] = table["same_direction_events"].div(
        table["eligible_reversals"].replace(0, np.nan)
    )
    table["conditioned_events_per_active_date"] = table["same_direction_events"].div(
        table["active_export_dates"].replace(0, np.nan)
    )
    table["conditioned_events_per_1000_bars"] = 1000 * table["same_direction_events"].div(
        table["bar_count"].replace(0, np.nan)
    )
    table["reversals_per_1000_bars"] = 1000 * table["total_reversals"].div(
        table["bar_count"].replace(0, np.nan)
    )
    table["mean_favorable_to_adverse_ratio"] = table["mean_favorable_ticks"].div(
        table["mean_adverse_ticks"].replace(0, np.nan)
    )
    table["timing_basis"] = "reversal candle timestamp"
    table["clock_status"] = "raw export clock; timezone and bar timestamp meaning unresolved"
    return _add_conversions(table, config, str(events["asset"].iloc[0]))


def build_confirmation_time_table(
    bars: pd.DataFrame, events: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    """Summarize successful events by the follow-through candle timestamp."""
    window_minutes = int(config["time_of_day"]["window_minutes"])
    grid = _chart_grid(bars, window_minutes)
    coverage = _coverage(bars, window_minutes)
    conditioned = events.loc[events["next_bar_same_direction"]].copy()
    conditioned["window_index"] = assign_clock_window(
        conditioned["follow_timestamp"], window_minutes, config["timestamp_format"]
    )["window_index"]
    geometry = _geometry(conditioned)
    table = grid.merge(coverage, on="window_index", how="left")
    table = table.merge(geometry, on="window_index", how="left")
    for column in ("bar_count", "active_export_dates", "conditioned_events", "event_active_dates"):
        table[column] = table[column].fillna(0).astype(int)
    table["conditioned_events_per_active_date"] = table["conditioned_events"].div(
        table["active_export_dates"].replace(0, np.nan)
    )
    table["conditioned_events_per_1000_bars"] = 1000 * table["conditioned_events"].div(
        table["bar_count"].replace(0, np.nan)
    )
    table["mean_favorable_to_adverse_ratio"] = table["mean_favorable_ticks"].div(
        table["mean_adverse_ticks"].replace(0, np.nan)
    )
    table["timing_basis"] = "follow-through candle timestamp"
    table["clock_status"] = "raw export clock; timezone and bar timestamp meaning unresolved"
    return _add_conversions(table, config, str(events["asset"].iloc[0]))


def rank_time_windows(
    signal_table: pd.DataFrame, confirmation_table: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return criterion-specific rankings and transparent balanced candidates."""
    min_events = int(config["time_of_day"]["minimum_conditioned_events"])
    min_dates = int(config["time_of_day"]["minimum_active_export_dates"])
    top_n = int(config["time_of_day"]["top_windows_per_criterion"])
    ranking_rows: list[dict[str, Any]] = []
    balanced_rows: list[dict[str, Any]] = []

    def append_ranked(
        chart: pd.DataFrame,
        criterion: str,
        column: str,
        ascending: bool,
        timing_basis: str,
        units: str,
    ) -> None:
        ordered = chart.sort_values(
            [column, "window_index"], ascending=[ascending, True], na_position="last"
        ).head(top_n)
        for rank, row in enumerate(ordered.itertuples(index=False), start=1):
            ranking_rows.append(
                {
                    "asset": row.asset,
                    "range_setting": int(row.range_setting),
                    "timing_basis": timing_basis,
                    "criterion": criterion,
                    "rank": rank,
                    "half_hour_window": row.half_hour_window,
                    "metric_value": getattr(row, column),
                    "units": units,
                    "conditioned_events": int(row.conditioned_events),
                    "eligible_reversals": int(getattr(row, "eligible_reversals", 0)),
                    "active_export_dates": int(row.active_export_dates),
                }
            )

    for (_, _), chart in signal_table.groupby(["asset", "range_setting"], observed=True):
        supported = chart.loc[
            chart["conditioned_events"].ge(min_events)
            & chart["active_export_dates"].ge(min_dates)
            & chart["eligible_reversals"].ge(min_events)
        ].copy()
        if supported.empty:
            continue
        append_ranked(supported, "highest follow-through rate", "same_direction_probability", False, "reversal", "share")
        append_ranked(supported, "most frequent", "conditioned_events_per_active_date", False, "reversal", "events per active export date")
        append_ranked(supported, "lowest mean adverse", "mean_adverse_ticks", True, "reversal", "ticks")
        append_ranked(supported, "highest mean favorable", "mean_favorable_ticks", False, "reversal", "ticks")
        append_ranked(supported, "largest favorable-minus-adverse", "mean_favorable_minus_adverse_ticks", False, "reversal", "ticks")

        rate_cutoff = supported["same_direction_probability"].median()
        frequency_cutoff = supported["conditioned_events_per_active_date"].median()
        balanced = supported.loc[
            supported["same_direction_probability"].ge(rate_cutoff)
            & supported["conditioned_events_per_active_date"].ge(frequency_cutoff)
            & supported["mean_favorable_minus_adverse_ticks"].gt(0)
        ].sort_values(
            ["mean_favorable_minus_adverse_ticks", "conditioned_events_per_active_date", "window_index"],
            ascending=[False, False, True],
        ).head(top_n)
        for rank, row in enumerate(balanced.itertuples(index=False), start=1):
            balanced_rows.append(
                {
                    "asset": row.asset,
                    "range_setting": int(row.range_setting),
                    "rank": rank,
                    "half_hour_window": row.half_hour_window,
                    "conditioned_events": int(row.conditioned_events),
                    "active_export_dates": int(row.active_export_dates),
                    "same_direction_probability": row.same_direction_probability,
                    "conditioned_events_per_active_date": row.conditioned_events_per_active_date,
                    "mean_adverse_ticks": row.mean_adverse_ticks,
                    "mean_favorable_ticks": row.mean_favorable_ticks,
                    "mean_favorable_minus_adverse_ticks": row.mean_favorable_minus_adverse_ticks,
                    "mean_favorable_to_adverse_ratio": row.mean_favorable_to_adverse_ratio,
                    "selection_rule": "at-or-above chart median rate and frequency; positive mean favorable-minus-adverse; ranked by that difference",
                }
            )

    for (_, _), chart in confirmation_table.groupby(["asset", "range_setting"], observed=True):
        supported = chart.loc[
            chart["conditioned_events"].ge(min_events)
            & chart["active_export_dates"].ge(min_dates)
        ].copy()
        if not supported.empty:
            append_ranked(
                supported,
                "most confirmations",
                "conditioned_events_per_active_date",
                False,
                "follow-through confirmation",
                "events per active export date",
            )

    return pd.DataFrame(ranking_rows), pd.DataFrame(balanced_rows)
