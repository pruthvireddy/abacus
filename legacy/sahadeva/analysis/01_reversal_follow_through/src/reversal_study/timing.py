from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .statistics import DIRECTIONS, ANALYSIS_SPLITS, numeric_summary, side_frame, split_frame


def _identity(frame: pd.DataFrame, config: dict[str, Any], split: str, direction: str, cohort: str, horizon: str, units: str) -> dict[str, Any]:
    return {
        "asset": str(frame["asset"].iloc[0]),
        "contract": str(frame["contract"].iloc[0]),
        "range_setting": int(frame["range_setting"].iloc[0]),
        "chart_identity_status": config["chart_identity_status"],
        "date_window": f"{frame['export_date'].min()} to {frame['export_date'].max()}" if not frame.empty else "unavailable",
        "split": split,
        "direction": direction,
        "cohort": cohort,
        "horizon": horizon,
        "units": units,
        "timing_status": config["timing_status"],
    }


def milestone_timing_table(all_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (_, _), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        for split in ANALYSIS_SPLITS:
            split_data = split_frame(chart, split)
            for direction in DIRECTIONS:
                side = side_frame(split_data, direction)
                if side.empty:
                    continue
                for threshold in config["thresholds"]:
                    eligible = side.loc[side[f"eligible_L_ge_{threshold}"].fillna(False)]
                    success = eligible.loc[eligible[f"success_L_ge_{threshold}"].fillna(False)]
                    summary = numeric_summary(success[f"time_to_L_ge_{threshold}_proxy_seconds"])
                    row = _identity(
                        side,
                        config,
                        split,
                        direction,
                        "successful reversals among complete threshold windows",
                        f"L>={threshold}",
                        "raw timestamp-difference proxy seconds",
                    )
                    row.update(summary)
                    row["denominator"] = int(len(eligible))
                    row["successes"] = int(len(success))
                    row["success_probability"] = len(success) / len(eligible) if len(eligible) else np.nan
                    rows.append(row)
                completed = side.loc[~side["run_censored"]]
                for label, column in (
                    ("last same-direction bar", "time_to_last_run_bar_proxy_seconds"),
                    ("first breaking bar", "time_to_break_proxy_seconds"),
                ):
                    row = _identity(
                        side,
                        config,
                        split,
                        direction,
                        "completed runs only",
                        label,
                        "raw timestamp-difference proxy seconds",
                    )
                    row.update(numeric_summary(completed[column]))
                    row["denominator"] = int(len(completed))
                    row["successes"] = np.nan
                    row["success_probability"] = np.nan
                    rows.append(row)
    return pd.DataFrame(rows)


def extreme_bar_table(all_events: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (_, _), chart in all_events.groupby(["asset", "range_setting"], observed=True):
        for split in ANALYSIS_SPLITS:
            split_data = split_frame(chart, split)
            for direction in DIRECTIONS:
                side = side_frame(split_data, direction)
                if side.empty:
                    continue
                for horizon in config["fixed_horizons"]:
                    for kind in ("mae", "mfe"):
                        column = f"{kind}_bar_index_h{horizon}"
                        summary = numeric_summary(side[column])
                        row = _identity(
                            side,
                            config,
                            split,
                            direction,
                            "fixed-horizon eligible primary reversals",
                            f"{horizon} bars: {kind.upper()} containing-bar index",
                            "future bars; zero means no positive excursion",
                        )
                        row.update(summary)
                        row["denominator"] = summary["n"]
                        row["zero_excursion_count"] = int((pd.to_numeric(side[column], errors="coerce") == 0).sum())
                        rows.append(row)
    return pd.DataFrame(rows)


def timestamp_quality_table(all_bars: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (_, _), chart in all_bars.groupby(["asset", "range_setting"], observed=True):
        included = chart.loc[chart["bar_included"] & chart["valid_row"]].copy()
        same = included["sequence_id"].eq(included["sequence_id"].shift())
        delta = included["parsed_timestamp"].diff().dt.total_seconds().where(same).dropna()
        summary = numeric_summary(delta)
        row = _identity(
            included,
            config,
            "full",
            "all",
            "adjacent included bars within provisional export-date segments",
            "one next-bar timestamp delta",
            "raw timestamp-difference seconds",
        )
        row.update(summary)
        row["denominator"] = int(len(delta))
        row["zero_delta_count"] = int((delta == 0).sum())
        row["negative_delta_count"] = int((delta < 0).sum())
        row["positive_delta_count"] = int((delta > 0).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def opportunity_table(all_events: pd.DataFrame, coverage: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, chart_dates in coverage.groupby(["asset", "range_setting"], observed=True):
        asset, range_setting = keys
        chart_events = all_events.loc[
            all_events["asset"].eq(asset) & all_events["range_setting"].eq(range_setting)
        ]
        contract = str(chart_dates["contract"].iloc[0])
        for split in ANALYSIS_SPLITS:
            dates = chart_dates.loc[
                chart_dates["split"].isin(["development", "validation", "test"])
                if split == "full"
                else chart_dates["split"].eq(split)
            ].copy()
            if dates.empty:
                continue
            split_events = split_frame(chart_events, split)
            for direction in DIRECTIONS:
                side = side_frame(split_events, direction)
                event_counts = side.groupby("export_date", observed=True).size()
                eligible = side.loc[side["eligible_L_ge_3"].fillna(False)]
                success_counts = eligible.loc[eligible["success_L_ge_3"].fillna(False)].groupby("export_date", observed=True).size()
                dates["signals"] = dates["export_date"].map(event_counts).fillna(0)
                dates["successful_L_ge_3"] = dates["export_date"].map(success_counts).fillna(0)
                span = pd.to_numeric(dates["raw_clock_span_hours"], errors="coerce").clip(lower=0)
                row = {
                    "asset": asset,
                    "contract": contract,
                    "range_setting": int(range_setting),
                    "chart_identity_status": config["chart_identity_status"],
                    "date_window": f"{dates['export_date'].min()} to {dates['export_date'].max()}",
                    "split": split,
                    "direction": direction,
                    "cohort": "primary reversals; valid zero-event export dates retained",
                    "denominator": int(len(dates)),
                    "horizon": "per provisional export date",
                    "units": "events/date and events/raw-clock-span-hour",
                    "timing_status": config["timing_status"],
                    "export_dates": int(len(dates)),
                    "signals": int(dates["signals"].sum()),
                    "mean_signals_per_date": float(dates["signals"].mean()),
                    "median_signals_per_date": float(dates["signals"].median()),
                    "p90_signals_per_date": float(dates["signals"].quantile(0.9)),
                    "successful_L_ge_3": int(dates["successful_L_ge_3"].sum()),
                    "mean_successful_L_ge_3_per_date": float(dates["successful_L_ge_3"].mean()),
                    "total_raw_clock_span_hours": float(span.sum()),
                    "signals_per_raw_clock_span_hour_proxy": float(dates["signals"].sum() / span.sum()) if span.sum() else np.nan,
                }
                rows.append(row)
    return pd.DataFrame(rows)

