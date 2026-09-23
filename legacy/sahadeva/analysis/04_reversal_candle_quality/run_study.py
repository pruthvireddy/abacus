from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(__file__).with_name("config.json")
RUN_ID = "20260908T_reversal_quality_v1"
REPORT_DIR = ROOT / "reports" / "04_reversal_candle_quality" / RUN_ID
TABLE_DIR = REPORT_DIR / "tables"

USECOLS = [
    "source_row",
    "bar_start_timestamp",
    "bar_completion_timestamp_proxy",
    "completion_proxy_status",
    "session_date_proxy",
    "open",
    "high",
    "low",
    "close",
]

SECONDARY_FEATURES = [
    "large_body",
    "strong_close",
    "small_close_side_wick",
    "rejection_tail",
    "favorable_gap",
    "adverse_gap",
    "retraces_previous_body",
    "breaks_previous_extreme",
    "closes_beyond_previous_extreme",
    "breaks_prior_run_extreme",
    "closes_beyond_prior_run_extreme",
]
PRIMARY_FEATURES = [
    "strong_close_structure_break",
    "strict_strong_close_structure_break",
]
FEATURES = [
    *SECONDARY_FEATURES,
    *PRIMARY_FEATURES,
    "strong_close_prior_run_break",
    "quality_stack",
]


@dataclass
class PairResult:
    signals: pd.DataFrame
    audit: dict[str, Any]


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def assign_split(session_dates: pd.Series, config: dict[str, Any]) -> pd.Series:
    result = pd.Series("outside", index=session_dates.index, dtype="string")
    for name, (start, end) in config["splits"].items():
        mask = session_dates.between(pd.Timestamp(start), pd.Timestamp(end))
        result.loc[mask] = name
    return result


def read_bars(path: Path, tick_size: float, include_outcomes: bool) -> pd.DataFrame:
    bars = pd.read_csv(
        path,
        sep=";",
        usecols=USECOLS,
        dtype={
            "source_row": "int64",
            "bar_start_timestamp": "string",
            "bar_completion_timestamp_proxy": "string",
            "completion_proxy_status": "category",
            "session_date_proxy": "string",
            "open": "float64",
            "high": "float64",
            "low": "float64",
            "close": "float64",
        },
    )
    bars["bar_start_time"] = pd.to_datetime(
        bars.pop("bar_start_timestamp"), format="%Y-%m-%d %H:%M:%S", errors="raise"
    )
    bars["completion_time"] = pd.to_datetime(
        bars.pop("bar_completion_timestamp_proxy"),
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
    )
    bars["session_date"] = pd.to_datetime(
        bars.pop("session_date_proxy"), format="%Y-%m-%d", errors="raise"
    )
    bars["direction"] = np.sign(bars["close"] - bars["open"]).astype(np.int8)

    same_session = bars["session_date"].eq(bars["session_date"].shift())
    previous_direction = bars["direction"].shift(fill_value=0).astype(np.int8)
    same_nonzero_direction = (
        same_session
        & bars["direction"].ne(0)
        & bars["direction"].eq(previous_direction)
    )
    bars["run_id"] = (~same_nonzero_direction).cumsum().astype(np.int64)
    run_group = bars.groupby("run_id", sort=False, observed=True)
    bars["run_length"] = (run_group.cumcount() + 1).astype(np.int32)
    bars["run_size"] = run_group["source_row"].transform("size").astype(np.int32)
    bars["prior_run_length"] = bars["run_length"].shift(fill_value=0).astype(np.int32)
    bars.loc[~same_session, "prior_run_length"] = 0
    bars["future_same_direction_bars"] = (
        bars["run_size"] - bars["run_length"]
    ).astype(np.int32)
    bars["is_reversal"] = (
        same_session
        & bars["direction"].ne(0)
        & previous_direction.ne(0)
        & bars["direction"].eq(-previous_direction)
    )

    next_same_session = bars["session_date"].eq(bars["session_date"].shift(-1))
    run_is_last_row = bars["run_id"].ne(bars["run_id"].shift(-1))
    observed_end_by_run = pd.Series(
        next_same_session.loc[run_is_last_row].to_numpy(bool),
        index=bars.loc[run_is_last_row, "run_id"].to_numpy(),
    )
    bars["run_observed_end"] = bars["run_id"].map(observed_end_by_run).astype(bool)

    if not include_outcomes:
        return bars

    bars["prev_open"] = bars["open"].shift()
    bars["prev_high"] = bars["high"].shift()
    bars["prev_low"] = bars["low"].shift()
    bars["prev_close"] = bars["close"].shift()
    bars.loc[
        ~same_session, ["prev_open", "prev_high", "prev_low", "prev_close"]
    ] = np.nan
    run_high = run_group["high"].transform("max")
    run_low = run_group["low"].transform("min")
    bars["prior_run_high"] = run_high.shift()
    bars["prior_run_low"] = run_low.shift()
    bars.loc[~same_session, ["prior_run_high", "prior_run_low"]] = np.nan

    bar_range = bars["high"] - bars["low"]
    bars["body_fraction"] = (bars["close"] - bars["open"]).abs() / bar_range
    bars["favorable_close_fraction"] = np.where(
        bars["direction"].eq(1),
        (bars["close"] - bars["low"]) / bar_range,
        (bars["high"] - bars["close"]) / bar_range,
    )
    bars["close_side_wick_fraction"] = np.where(
        bars["direction"].eq(1),
        (bars["high"] - bars["close"]) / bar_range,
        (bars["close"] - bars["low"]) / bar_range,
    )
    bars["adverse_wick_fraction"] = np.where(
        bars["direction"].eq(1),
        (bars["open"] - bars["low"]) / bar_range,
        (bars["high"] - bars["open"]) / bar_range,
    )
    bars["close_side_wick_ticks"] = bars["close_side_wick_fraction"] * bar_range / tick_size
    bars["adverse_wick_ticks"] = bars["adverse_wick_fraction"] * bar_range / tick_size
    bars["directional_opening_gap_ticks"] = (
        bars["direction"] * (bars["open"] - bars["prev_close"]) / tick_size
    )

    bullish = bars["direction"].eq(1)
    bars["retraces_previous_body"] = np.where(
        bullish, bars["close"].ge(bars["prev_open"]), bars["close"].le(bars["prev_open"])
    )
    bars["breaks_previous_extreme"] = np.where(
        bullish, bars["high"].gt(bars["prev_high"]), bars["low"].lt(bars["prev_low"])
    )
    bars["closes_beyond_previous_extreme"] = np.where(
        bullish, bars["close"].gt(bars["prev_high"]), bars["close"].lt(bars["prev_low"])
    )
    bars["breaks_prior_run_extreme"] = np.where(
        bullish,
        bars["high"].gt(bars["prior_run_high"]),
        bars["low"].lt(bars["prior_run_low"]),
    )
    bars["closes_beyond_prior_run_extreme"] = np.where(
        bullish,
        bars["close"].gt(bars["prior_run_high"]),
        bars["close"].lt(bars["prior_run_low"]),
    )

    for horizon in (1, 3, 5):
        bars[f"eligible_L_ge_{horizon}"] = (
            bars["future_same_direction_bars"].ge(horizon) | bars["run_observed_end"]
        )
        bars[f"success_L_ge_{horizon}"] = bars["future_same_direction_bars"].ge(
            horizon
        )
        future_same_session = bars["session_date"].eq(
            bars["session_date"].shift(-horizon)
        )
        future_complete = bars["completion_time"].shift(-horizon).notna()
        entry_open = bars["open"].shift(-1)
        bars[f"forward_return_{horizon}_bars_ticks"] = (
            bars["direction"]
            * (bars["close"].shift(-horizon) - entry_open)
            / tick_size
        ).where(future_same_session & future_complete)

    entry_open = bars["open"].shift(-1)
    five_same_session = bars["session_date"].eq(bars["session_date"].shift(-5))
    five_complete = bars["completion_time"].shift(-5).notna()
    future_highs = pd.concat(
        [bars["high"].shift(-offset) for offset in range(1, 6)], axis=1
    )
    future_lows = pd.concat(
        [bars["low"].shift(-offset) for offset in range(1, 6)], axis=1
    )
    max_high = future_highs.max(axis=1)
    min_low = future_lows.min(axis=1)
    bars["mfe_5_bars_ticks"] = np.where(
        bullish, (max_high - entry_open) / tick_size, (entry_open - min_low) / tick_size
    )
    bars["mae_5_bars_ticks"] = np.where(
        bullish, (entry_open - min_low) / tick_size, (max_high - entry_open) / tick_size
    )
    bars.loc[
        ~(five_same_session & five_complete), ["mfe_5_bars_ticks", "mae_5_bars_ticks"]
    ] = np.nan
    bars["entry_open"] = entry_open.where(next_same_session)
    return bars


def add_feature_flags(
    signals: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    thresholds = config["fixed_feature_thresholds"]
    signals["large_body"] = signals["body_fraction"].ge(
        thresholds["large_body_fraction"]
    )
    signals["strong_close"] = signals["favorable_close_fraction"].ge(
        thresholds["strong_close_fraction"]
    )
    signals["small_close_side_wick"] = signals["close_side_wick_fraction"].le(
        thresholds["small_close_side_wick_fraction"]
    )
    signals["rejection_tail"] = signals["adverse_wick_fraction"].ge(
        thresholds["rejection_tail_fraction"]
    )
    signals["favorable_gap"] = signals["directional_opening_gap_ticks"].gt(0)
    signals["adverse_gap"] = signals["directional_opening_gap_ticks"].lt(0)
    signals["strong_close_structure_break"] = (
        signals["strong_close"] & signals["breaks_previous_extreme"]
    )
    signals["strict_strong_close_structure_break"] = (
        signals["strong_close"] & signals["closes_beyond_previous_extreme"]
    )
    signals["strong_close_prior_run_break"] = (
        signals["strong_close"] & signals["breaks_prior_run_extreme"]
    )
    signals["quality_stack"] = (
        signals["large_body"]
        & signals["strong_close"]
        & signals["breaks_previous_extreme"]
    )
    for feature in FEATURES:
        signals[feature] = signals[feature].fillna(False).astype(bool)
    return signals


def prepare_signals(
    small: pd.DataFrame,
    large: pd.DataFrame,
    pair: dict[str, Any],
    config: dict[str, Any],
) -> PairResult:
    geometry_columns = [
        "body_fraction",
        "favorable_close_fraction",
        "close_side_wick_fraction",
        "adverse_wick_fraction",
        "close_side_wick_ticks",
        "adverse_wick_ticks",
        "directional_opening_gap_ticks",
        "retraces_previous_body",
        "breaks_previous_extreme",
        "closes_beyond_previous_extreme",
        "breaks_prior_run_extreme",
        "closes_beyond_prior_run_extreme",
    ]
    outcome_columns: list[str] = []
    for horizon in (1, 3, 5):
        outcome_columns.extend(
            [
                f"eligible_L_ge_{horizon}",
                f"success_L_ge_{horizon}",
                f"forward_return_{horizon}_bars_ticks",
            ]
        )
    columns = [
        "source_row",
        "session_date",
        "direction",
        "completion_time",
        "completion_proxy_status",
        "prior_run_length",
        "entry_open",
        "mfe_5_bars_ticks",
        "mae_5_bars_ticks",
        *geometry_columns,
        *outcome_columns,
    ]
    signals = small.loc[
        small["is_reversal"] & small["completion_time"].notna(), columns
    ].copy()
    signals = signals.rename(
        columns={
            "source_row": "small_source_row",
            "direction": "signal_direction",
            "completion_time": "signal_time",
            "completion_proxy_status": "small_completion_status",
        }
    )
    signals["pair_id"] = pair["pair_id"]
    signals["split"] = assign_split(signals["session_date"], config)
    signals["strict_timing"] = signals["small_completion_status"].eq(
        config["timestamp_policy"]["strict_small_signal_status"]
    )

    large_state = large.loc[
        large["completion_time"].notna(),
        [
            "session_date",
            "source_row",
            "completion_time",
            "direction",
            "run_id",
            "run_length",
        ],
    ].rename(
        columns={
            "source_row": "large_source_row",
            "completion_time": "large_completion_time",
            "direction": "large_direction",
            "run_id": "large_run_id",
            "run_length": "large_run_length",
        }
    )
    signals = pd.merge_asof(
        signals.sort_values("signal_time"),
        large_state.sort_values("large_completion_time"),
        left_on="signal_time",
        right_on="large_completion_time",
        by="session_date",
        direction="backward",
        allow_exact_matches=False,
    )
    available = signals["large_completion_time"].notna()
    if not signals.loc[available, "large_completion_time"].lt(
        signals.loc[available, "signal_time"]
    ).all():
        raise AssertionError("No-look-ahead invariant failed for larger state")

    signals["large_state_available"] = signals["large_direction"].notna()
    signals["aligned"] = (
        signals["large_state_available"]
        & signals["large_direction"].ne(0)
        & signals["signal_direction"].eq(signals["large_direction"])
    )
    signals["countertrend"] = (
        signals["large_state_available"]
        & signals["large_direction"].ne(0)
        & signals["signal_direction"].eq(-signals["large_direction"])
    )
    signals["exhausted_countertrend"] = (
        signals["countertrend"]
        & signals["large_run_length"].ge(
            config["fixed_feature_thresholds"]["extended_large_run_bars"]
        )
    )

    next_same_session = large["session_date"].eq(large["session_date"].shift(-1))
    large_reversals = large.loc[
        large["is_reversal"] & large["completion_time"].notna(),
        ["session_date", "completion_time", "direction", "source_row"],
    ].copy()
    large_reversals["large_confirmation_entry"] = large["open"].shift(-1).loc[
        large_reversals.index
    ].where(next_same_session.loc[large_reversals.index])
    large_reversals = large_reversals.rename(
        columns={
            "completion_time": "future_large_reversal_time",
            "direction": "signal_direction",
            "source_row": "future_large_reversal_source_row",
        }
    )
    signals = pd.merge_asof(
        signals.sort_values("signal_time"),
        large_reversals.sort_values("future_large_reversal_time"),
        left_on="signal_time",
        right_on="future_large_reversal_time",
        by=["session_date", "signal_direction"],
        direction="forward",
        allow_exact_matches=False,
    )
    confirmed = signals["future_large_reversal_time"].notna()
    if not signals.loc[confirmed, "future_large_reversal_time"].gt(
        signals.loc[confirmed, "signal_time"]
    ).all():
        raise AssertionError("Forward confirmation invariant failed")
    signals["large_confirmation_delay_seconds"] = (
        signals["future_large_reversal_time"] - signals["signal_time"]
    ).dt.total_seconds()
    for minutes in config["outcomes"]["large_confirmation_minutes"]:
        signals[f"large_confirms_within_{minutes}m"] = signals[
            "large_confirmation_delay_seconds"
        ].between(0, minutes * 60, inclusive="both")
    signals["early_entry_advantage_ticks"] = (
        signals["signal_direction"]
        * (signals["large_confirmation_entry"] - signals["entry_open"])
        / float(pair["tick_size"])
    )
    signals = add_feature_flags(signals, config)

    audit = {
        "pair_id": pair["pair_id"],
        "asset": pair["asset"],
        "small_setting": pair["small_setting"],
        "large_setting": pair["large_setting"],
        "small_rows": int(len(small)),
        "large_rows": int(len(large)),
        "reversal_signals_with_completion_proxy": int(len(signals)),
        "strict_timing_signals": int(signals["strict_timing"].sum()),
        "same_second_sensitivity_signals": int((~signals["strict_timing"]).sum()),
        "strict_signals_with_larger_state": int(
            (signals["strict_timing"] & signals["large_state_available"]).sum()
        ),
        "larger_state_exact_match_violations": int(
            (
                signals["large_completion_time"].notna()
                & signals["large_completion_time"].ge(signals["signal_time"])
            ).sum()
        ),
        "future_confirmation_order_violations": int(
            (
                signals["future_large_reversal_time"].notna()
                & signals["future_large_reversal_time"].le(signals["signal_time"])
            ).sum()
        ),
    }
    return PairResult(signals=signals, audit=audit)


def direction_mask(frame: pd.DataFrame, label: str) -> pd.Series:
    if label == "bullish":
        return frame["signal_direction"].eq(1)
    if label == "bearish":
        return frame["signal_direction"].eq(-1)
    return pd.Series(True, index=frame.index)


def context_masks(signals: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "all_reversals": pd.Series(True, index=signals.index),
        "aligned": signals["aligned"],
        "countertrend": signals["countertrend"],
        "exhausted_countertrend": signals["exhausted_countertrend"],
    }


def bootstrap_boolean_contrast(
    frame: pd.DataFrame,
    feature: str,
    outcome: str,
    rng: np.random.Generator,
    replicates: int,
) -> tuple[float, float, float, float, float, int, int]:
    work = frame[["session_date", feature, outcome]].dropna(subset=[outcome]).copy()
    grouped = (
        work.groupby(["session_date", feature], sort=False, observed=True)[outcome]
        .agg(["sum", "count"])
        .reset_index()
    )
    sessions = pd.Index(work["session_date"].drop_duplicates())
    arrays: dict[bool, tuple[np.ndarray, np.ndarray]] = {}
    for label in (True, False):
        subset = grouped.loc[grouped[feature].eq(label)].set_index("session_date")
        arrays[label] = (
            subset["sum"].reindex(sessions, fill_value=0).to_numpy(float),
            subset["count"].reindex(sessions, fill_value=0).to_numpy(float),
        )
    feature_success, feature_count = arrays[True]
    other_success, other_count = arrays[False]
    feature_n = int(feature_count.sum())
    other_n = int(other_count.sum())
    if not len(sessions) or not feature_n or not other_n:
        return (math.nan, math.nan, math.nan, math.nan, math.nan, feature_n, other_n)
    feature_rate = feature_success.sum() / feature_n
    other_rate = other_success.sum() / other_n
    draws = rng.integers(0, len(sessions), size=(replicates, len(sessions)))
    draw_feature_count = feature_count[draws].sum(axis=1)
    draw_other_count = other_count[draws].sum(axis=1)
    valid = (draw_feature_count > 0) & (draw_other_count > 0)
    differences = (
        feature_success[draws].sum(axis=1)[valid] / draw_feature_count[valid]
        - other_success[draws].sum(axis=1)[valid] / draw_other_count[valid]
    )
    return (
        float(feature_rate),
        float(other_rate),
        float(feature_rate - other_rate),
        float(np.quantile(differences, 0.025)),
        float(np.quantile(differences, 0.975)),
        feature_n,
        other_n,
    )


def summarize_prevalence(signals: pd.DataFrame, pair_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split in ("development", "validation", "test"):
        for context, cm in context_masks(signals).items():
            base = signals.loc[signals["split"].eq(split) & signals["strict_timing"] & cm]
            for feature in FEATURES:
                rows.append(
                    {
                        "pair_id": pair_id,
                        "split": split,
                        "timing_sample": "strict",
                        "context": context,
                        "feature": feature,
                        "context_signals": int(len(base)),
                        "feature_signals": int(base[feature].sum()),
                        "feature_prevalence": float(base[feature].mean())
                        if len(base)
                        else math.nan,
                    }
                )
    return rows


def directions_for_feature(feature: str) -> tuple[str, ...]:
    if feature in [*PRIMARY_FEATURES, "quality_stack"]:
        return ("both", "bullish", "bearish")
    return ("both",)


def summarize_continuation(
    signals: pd.DataFrame,
    pair_id: str,
    rng: np.random.Generator,
    replicates: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    samples = {
        "strict": (signals["strict_timing"], FEATURES),
        "all_proxy_sensitivity": (
            pd.Series(True, index=signals.index),
            [*PRIMARY_FEATURES, "quality_stack"],
        ),
    }
    contexts = context_masks(signals)
    for split in ("development", "validation", "test"):
        split_mask = signals["split"].eq(split)
        for sample_name, (sample_mask, features) in samples.items():
            for context, context_mask in contexts.items():
                for feature in features:
                    for direction in directions_for_feature(feature):
                        dm = direction_mask(signals, direction)
                        for horizon in (1, 3, 5):
                            base_mask = (
                                split_mask
                                & sample_mask
                                & context_mask
                                & dm
                                & signals[f"eligible_L_ge_{horizon}"]
                            )
                            base = signals.loc[base_mask]
                            outcome = f"success_L_ge_{horizon}"
                            (
                                feature_rate,
                                other_rate,
                                difference,
                                ci_low,
                                ci_high,
                                feature_n,
                                other_n,
                            ) = bootstrap_boolean_contrast(
                                base, feature, outcome, rng, replicates
                            )
                            feature_rows = base.loc[base[feature]]
                            other_rows = base.loc[~base[feature]]
                            rows.append(
                                {
                                    "pair_id": pair_id,
                                    "split": split,
                                    "timing_sample": sample_name,
                                    "context": context,
                                    "direction": direction,
                                    "feature": feature,
                                    "outcome": f"P(L>={horizon})",
                                    "feature_rate": feature_rate,
                                    "nonfeature_rate": other_rate,
                                    "feature_minus_nonfeature": difference,
                                    "cluster_bootstrap_ci_low": ci_low,
                                    "cluster_bootstrap_ci_high": ci_high,
                                    "feature_n": feature_n,
                                    "nonfeature_n": other_n,
                                    "feature_median_forward_return_ticks": float(
                                        feature_rows[
                                            f"forward_return_{horizon}_bars_ticks"
                                        ].median()
                                    )
                                    if len(feature_rows)
                                    else math.nan,
                                    "feature_mean_forward_return_ticks": float(
                                        feature_rows[
                                            f"forward_return_{horizon}_bars_ticks"
                                        ].mean()
                                    )
                                    if len(feature_rows)
                                    else math.nan,
                                    "nonfeature_median_forward_return_ticks": float(
                                        other_rows[
                                            f"forward_return_{horizon}_bars_ticks"
                                        ].median()
                                    )
                                    if len(other_rows)
                                    else math.nan,
                                    "nonfeature_mean_forward_return_ticks": float(
                                        other_rows[
                                            f"forward_return_{horizon}_bars_ticks"
                                        ].mean()
                                    )
                                    if len(other_rows)
                                    else math.nan,
                                    "feature_median_mfe_5_ticks": float(
                                        feature_rows["mfe_5_bars_ticks"].median()
                                    )
                                    if len(feature_rows)
                                    else math.nan,
                                    "feature_median_mae_5_ticks": float(
                                        feature_rows["mae_5_bars_ticks"].median()
                                    )
                                    if len(feature_rows)
                                    else math.nan,
                                }
                            )
    return rows


def summarize_large_confirmation(
    signals: pd.DataFrame,
    pair_id: str,
    rng: np.random.Generator,
    replicates: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    contexts = context_masks(signals)
    for split in ("development", "validation", "test"):
        split_mask = signals["split"].eq(split) & signals["strict_timing"]
        for context in ("countertrend", "exhausted_countertrend"):
            for feature in FEATURES:
                base = signals.loc[split_mask & contexts[context]]
                for minutes in (15, 30):
                    outcome = f"large_confirms_within_{minutes}m"
                    (
                        feature_rate,
                        other_rate,
                        difference,
                        ci_low,
                        ci_high,
                        feature_n,
                        other_n,
                    ) = bootstrap_boolean_contrast(
                        base, feature, outcome, rng, replicates
                    )
                    feature_confirmed = base.loc[base[feature] & base[outcome]]
                    rows.append(
                        {
                            "pair_id": pair_id,
                            "split": split,
                            "timing_sample": "strict",
                            "context": context,
                            "feature": feature,
                            "window_minutes": minutes,
                            "feature_confirmation_rate": feature_rate,
                            "nonfeature_confirmation_rate": other_rate,
                            "feature_minus_nonfeature": difference,
                            "cluster_bootstrap_ci_low": ci_low,
                            "cluster_bootstrap_ci_high": ci_high,
                            "feature_n": feature_n,
                            "nonfeature_n": other_n,
                            "feature_median_confirmation_delay_minutes": float(
                                feature_confirmed[
                                    "large_confirmation_delay_seconds"
                                ].median()
                                / 60.0
                            )
                            if len(feature_confirmed)
                            else math.nan,
                            "feature_median_early_entry_advantage_ticks": float(
                                feature_confirmed[
                                    "early_entry_advantage_ticks"
                                ].median()
                            )
                            if len(feature_confirmed)
                            else math.nan,
                        }
                    )
    return rows


def summarize_geometry(signals: pd.DataFrame, pair_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    numeric_features = [
        "body_fraction",
        "favorable_close_fraction",
        "close_side_wick_fraction",
        "adverse_wick_fraction",
        "close_side_wick_ticks",
        "adverse_wick_ticks",
        "directional_opening_gap_ticks",
    ]
    for split in ("development", "validation", "test"):
        subset = signals.loc[signals["split"].eq(split) & signals["strict_timing"]]
        for feature in numeric_features:
            values = subset[feature].dropna()
            rows.append(
                {
                    "pair_id": pair_id,
                    "split": split,
                    "timing_sample": "strict",
                    "metric": feature,
                    "observations": int(len(values)),
                    "p10": float(values.quantile(0.10)) if len(values) else math.nan,
                    "p25": float(values.quantile(0.25)) if len(values) else math.nan,
                    "median": float(values.median()) if len(values) else math.nan,
                    "p75": float(values.quantile(0.75)) if len(values) else math.nan,
                    "p90": float(values.quantile(0.90)) if len(values) else math.nan,
                }
            )
    return rows


def prior_run_bucket(values: pd.Series) -> pd.Series:
    return pd.cut(
        values,
        bins=[0, 1, 2, 4, np.inf],
        labels=["1", "2", "3-4", "5+"],
    ).astype("string")


def summarize_prior_run_stratified(
    signals: pd.DataFrame,
    pair_id: str,
    rng: np.random.Generator,
    replicates: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    buckets = prior_run_bucket(signals["prior_run_length"])
    features = [
        "breaks_previous_extreme",
        "closes_beyond_previous_extreme",
        "breaks_prior_run_extreme",
        "closes_beyond_prior_run_extreme",
        "strong_close_structure_break",
        "strong_close_prior_run_break",
        "quality_stack",
    ]
    contexts = context_masks(signals)
    for split in ("development", "validation", "test"):
        for context in ("all_reversals", "aligned", "countertrend"):
            for bucket in ("1", "2", "3-4", "5+"):
                bucket_mask = buckets.eq(bucket)
                for feature in features:
                    for horizon in (1, 3):
                        base = signals.loc[
                            signals["split"].eq(split)
                            & signals["strict_timing"]
                            & contexts[context]
                            & bucket_mask
                            & signals[f"eligible_L_ge_{horizon}"]
                        ]
                        outcome = f"success_L_ge_{horizon}"
                        (
                            feature_rate,
                            other_rate,
                            difference,
                            ci_low,
                            ci_high,
                            feature_n,
                            other_n,
                        ) = bootstrap_boolean_contrast(
                            base, feature, outcome, rng, replicates
                        )
                        rows.append(
                            {
                                "pair_id": pair_id,
                                "split": split,
                                "timing_sample": "strict",
                                "context": context,
                                "prior_run_length_bucket": bucket,
                                "feature": feature,
                                "outcome": f"P(L>={horizon})",
                                "feature_rate": feature_rate,
                                "nonfeature_rate": other_rate,
                                "feature_minus_nonfeature": difference,
                                "cluster_bootstrap_ci_low": ci_low,
                                "cluster_bootstrap_ci_high": ci_high,
                                "feature_n": feature_n,
                                "nonfeature_n": other_n,
                            }
                        )
    return rows


def summarize_one_bar_snapback(
    signals: pd.DataFrame,
    pair_id: str,
    rng: np.random.Generator,
    replicates: int,
) -> list[dict[str, Any]]:
    """Contrast reversals after a one-bar opposite run with longer prior runs."""
    work = signals.copy()
    work["prior_run_is_one"] = work["prior_run_length"].eq(1)
    rows: list[dict[str, Any]] = []
    contexts = context_masks(work)
    for split in ("development", "validation", "test"):
        split_mask = work["split"].eq(split) & work["strict_timing"]
        for context, context_mask in contexts.items():
            for horizon in (1, 3, 5):
                base = work.loc[
                    split_mask
                    & context_mask
                    & work["prior_run_length"].ge(1)
                    & work[f"eligible_L_ge_{horizon}"]
                ]
                outcome = f"success_L_ge_{horizon}"
                (
                    one_bar_rate,
                    longer_rate,
                    difference,
                    ci_low,
                    ci_high,
                    one_bar_n,
                    longer_n,
                ) = bootstrap_boolean_contrast(
                    base, "prior_run_is_one", outcome, rng, replicates
                )
                rows.append(
                    {
                        "pair_id": pair_id,
                        "split": split,
                        "timing_sample": "strict",
                        "context": context,
                        "outcome": f"P(L>={horizon})",
                        "one_bar_prior_run_rate": one_bar_rate,
                        "longer_prior_run_rate": longer_rate,
                        "one_bar_minus_longer": difference,
                        "cluster_bootstrap_ci_low": ci_low,
                        "cluster_bootstrap_ci_high": ci_high,
                        "one_bar_n": one_bar_n,
                        "longer_n": longer_n,
                        "supported_min_200_each": bool(
                            one_bar_n >= 200 and longer_n >= 200
                        ),
                    }
                )
    return rows


def write_methodology(config: dict[str, Any], audits: list[dict[str, Any]]) -> None:
    lines = [
        "# Methodology: reversal-candle quality",
        "",
        "## Signal and timing",
        "",
        "A reversal is a completed non-doji small-chart bar whose direction is opposite the immediately preceding non-doji bar in the same inferred session. The signal becomes observable at its completion proxy, which is the next small bar's opening timestamp.",
        "",
        "The larger-chart state is the latest larger bar with a completion proxy strictly earlier than the small signal. Exact timestamp matches are rejected. Primary results exclude small bars whose opening and completion proxies share the same recorded second.",
        "",
        "## Frozen geometry",
        "",
        "- Body fraction is `abs(close-open)/(high-low)`.",
        "- Favorable close fraction is `(close-low)/(high-low)` for bullish bars and `(high-close)/(high-low)` for bearish bars.",
        "- Close-side wick is the distance from the close to the high for bullish bars and to the low for bearish bars.",
        "- Adverse wick is the opening-side wick: open-to-low for bullish bars and high-to-open for bearish bars.",
        "- Directional opening gap is positive when the reversal opens favorably relative to the preceding close.",
        "- Previous-extreme break means the reversal trades above the preceding high when bullish or below the preceding low when bearish. The strict version requires the close to pass that extreme.",
        "- Prior-run break applies the same rule to the full immediately preceding opposite-direction run.",
        "- Full preceding-body retracement means a bullish reversal closes at or above the preceding open, or a bearish reversal closes at or below it.",
        "",
        "The primary strong-close threshold is 0.80. The primary structure-break feature combines that threshold with a previous-extreme break. The strict version requires a close beyond the previous extreme. The quality stack also requires body fraction of at least 0.70.",
        "A dedicated one-bar-snapback contrast separates reversals after a one-bar opposite run from reversals after runs of two or more bars. This guards against interpreting a prior-run break as independent candle quality when it is largely determined by prior-run length.",
        "",
        "## Outcomes and inference",
        "",
        "Continuation `L` excludes the reversal bar and counts immediately following same-direction small bars. Entry geometry uses the next small-bar open. Larger confirmation is the first strictly later completed larger reversal in the signal direction.",
        "",
        f"Differences compare feature-present with feature-absent signals inside the same chart, context, split, and timing sample. Confidence intervals use {config['bootstrap']['replicates']:,} session-cluster bootstrap replicates. Secondary features are diagnostic and are not multiplicity-adjusted entry rules.",
        "",
        "The chronological partitions match the previous multi-RXV study. Because the exhaustion context was motivated by earlier inspection of the same overall dataset, exhaustion interactions should be treated as follow-up historical evidence rather than a fully pristine independent test.",
        "",
        "## Limits",
        "",
        "The exact ATAS last-trade/completion time, timezone, and configured trading session are absent. Completion remains a one-second next-bar-start proxy. OHLC cannot reconstruct intrabar path, volume, delta, or order flow.",
        "",
        "## Pair audit",
        "",
        "```json",
        json.dumps(audits, indent=2),
        "```",
        "",
    ]
    (REPORT_DIR / "methodology.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    config = load_config()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(config["bootstrap"]["seed"])
    replicates = int(config["bootstrap"]["replicates"])

    audits: list[dict[str, Any]] = []
    prevalence_rows: list[dict[str, Any]] = []
    continuation_rows: list[dict[str, Any]] = []
    confirmation_rows: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    prior_run_rows: list[dict[str, Any]] = []
    snapback_rows: list[dict[str, Any]] = []

    for pair in config["pairs"]:
        print(f"Loading {pair['pair_id']} small bars", flush=True)
        small = read_bars(ROOT / pair["small_path"], float(pair["tick_size"]), True)
        print(f"Loading {pair['pair_id']} larger bars", flush=True)
        large = read_bars(ROOT / pair["large_path"], float(pair["tick_size"]), False)
        result = prepare_signals(small, large, pair, config)
        audits.append(result.audit)
        prevalence_rows.extend(summarize_prevalence(result.signals, pair["pair_id"]))
        continuation_rows.extend(
            summarize_continuation(result.signals, pair["pair_id"], rng, replicates)
        )
        confirmation_rows.extend(
            summarize_large_confirmation(result.signals, pair["pair_id"], rng, replicates)
        )
        geometry_rows.extend(summarize_geometry(result.signals, pair["pair_id"]))
        prior_run_rows.extend(
            summarize_prior_run_stratified(
                result.signals, pair["pair_id"], rng, replicates
            )
        )
        snapback_rows.extend(
            summarize_one_bar_snapback(
                result.signals, pair["pair_id"], rng, replicates
            )
        )
        del small, large, result

    tables = {
        "feature_prevalence.csv": pd.DataFrame(prevalence_rows),
        "continuation_feature_contrasts.csv": pd.DataFrame(continuation_rows),
        "large_confirmation_feature_contrasts.csv": pd.DataFrame(confirmation_rows),
        "geometry_distributions.csv": pd.DataFrame(geometry_rows),
        "prior_run_stratified_contrasts.csv": pd.DataFrame(prior_run_rows),
        "one_bar_snapback_contrasts.csv": pd.DataFrame(snapback_rows),
        "pair_audit.csv": pd.DataFrame(audits),
    }
    for filename, frame in tables.items():
        frame.to_csv(TABLE_DIR / filename, index=False)

    manifest = {
        "study_id": config["study_id"],
        "run_id": RUN_ID,
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "input_manifest": "data/range_xv_exports_manifest.json",
        "tables": [f"tables/{name}" for name in tables],
        "audits": audits,
    }
    (REPORT_DIR / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    write_methodology(config, audits)
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
