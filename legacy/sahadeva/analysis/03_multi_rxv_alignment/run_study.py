from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(__file__).with_name("config.json")
RUN_ID = "20260908T_multi_rxv_v1"
REPORT_DIR = ROOT / "reports" / "03_multi_rxv_alignment" / RUN_ID
TABLE_DIR = REPORT_DIR / "tables"

USECOLS = [
    "source_row",
    "bar_start_timestamp",
    "bar_completion_timestamp_proxy",
    "bar_duration_seconds_proxy",
    "completion_proxy_status",
    "session_date_proxy",
    "open",
    "high",
    "low",
    "close",
]


@dataclass
class PairResult:
    pair: dict[str, Any]
    signals: pd.DataFrame
    audit: dict[str, Any]


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def assign_split(session_dates: pd.Series, config: dict[str, Any]) -> pd.Series:
    result = pd.Series("outside", index=session_dates.index, dtype="string")
    for name, (start, end) in config["splits"].items():
        lo = pd.Timestamp(start)
        hi = pd.Timestamp(end)
        result.loc[session_dates.between(lo, hi)] = name
    return result


def read_bars(path: Path, tick_size: float, include_small_outcomes: bool) -> pd.DataFrame:
    bars = pd.read_csv(
        path,
        sep=";",
        usecols=USECOLS,
        dtype={
            "source_row": "int64",
            "bar_start_timestamp": "string",
            "bar_completion_timestamp_proxy": "string",
            "bar_duration_seconds_proxy": "float64",
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
    bars["future_same_direction_bars"] = (
        bars["run_size"] - bars["run_length"]
    ).astype(np.int32)

    next_same_session = bars["session_date"].eq(bars["session_date"].shift(-1))
    run_is_last_row = bars["run_id"].ne(bars["run_id"].shift(-1))
    observed_end_by_run = pd.Series(
        next_same_session.loc[run_is_last_row].to_numpy(bool),
        index=bars.loc[run_is_last_row, "run_id"].to_numpy(),
    )
    bars["run_observed_end"] = bars["run_id"].map(observed_end_by_run).astype(bool)
    bars["is_reversal"] = (
        same_session
        & bars["direction"].ne(0)
        & previous_direction.ne(0)
        & bars["direction"].eq(-previous_direction)
    )
    bars["prior_run_length"] = bars["run_length"].shift(fill_value=0).astype(np.int32)

    run_group = bars.groupby("run_id", sort=False, observed=True)
    run_started_by_reversal = run_group["is_reversal"].transform("first").astype(bool)
    run_start_completion = run_group["completion_time"].transform("first")
    bars["run_reversal_completion_time"] = run_start_completion.where(
        run_started_by_reversal
    )
    bars["run_started_by_reversal"] = run_started_by_reversal

    prior_10_close = bars.groupby("session_date", sort=False, observed=True)["close"].shift(10)
    bars["rolling_trend_10_ticks"] = (bars["close"] - prior_10_close) / tick_size
    bars["rolling_trend_10_direction"] = np.sign(
        bars["rolling_trend_10_ticks"]
    ).fillna(0).astype(np.int8)

    if not include_small_outcomes:
        return bars

    for horizon in (1, 3, 5):
        future_run = bars["future_same_direction_bars"]
        bars[f"eligible_L_ge_{horizon}"] = (future_run.ge(horizon) | bars["run_observed_end"])
        bars[f"success_L_ge_{horizon}"] = future_run.ge(horizon)

        future_close = bars["close"].shift(-horizon)
        future_same_session = bars["session_date"].eq(bars["session_date"].shift(-horizon))
        entry_open = bars["open"].shift(-1)
        bars[f"forward_return_{horizon}_bars_ticks"] = (
            bars["direction"] * (future_close - entry_open) / tick_size
        ).where(future_same_session)

    entry_open = bars["open"].shift(-1)
    five_bar_same_session = bars["session_date"].eq(bars["session_date"].shift(-5))
    future_highs = pd.concat([bars["high"].shift(-offset) for offset in range(1, 6)], axis=1)
    future_lows = pd.concat([bars["low"].shift(-offset) for offset in range(1, 6)], axis=1)
    max_high = future_highs.max(axis=1)
    min_low = future_lows.min(axis=1)
    long_favorable = (max_high - entry_open) / tick_size
    short_favorable = (entry_open - min_low) / tick_size
    long_adverse = (entry_open - min_low) / tick_size
    short_adverse = (max_high - entry_open) / tick_size
    bars["mfe_5_bars_ticks"] = np.where(
        bars["direction"].eq(1), long_favorable, short_favorable
    )
    bars["mae_5_bars_ticks"] = np.where(
        bars["direction"].eq(1), long_adverse, short_adverse
    )
    bars.loc[~five_bar_same_session, ["mfe_5_bars_ticks", "mae_5_bars_ticks"]] = np.nan
    bars["entry_open"] = entry_open.where(next_same_session)
    return bars


def prepare_signals(
    small: pd.DataFrame,
    large: pd.DataFrame,
    pair: dict[str, Any],
    config: dict[str, Any],
) -> PairResult:
    small_signal_mask = small["is_reversal"] & small["completion_time"].notna()
    columns = [
        "source_row",
        "session_date",
        "direction",
        "completion_time",
        "completion_proxy_status",
        "prior_run_length",
        "future_same_direction_bars",
        "entry_open",
        "mfe_5_bars_ticks",
        "mae_5_bars_ticks",
    ]
    for horizon in (1, 3, 5):
        columns.extend(
            [
                f"eligible_L_ge_{horizon}",
                f"success_L_ge_{horizon}",
                f"forward_return_{horizon}_bars_ticks",
            ]
        )
    signals = small.loc[small_signal_mask, columns].copy()
    signals = signals.rename(
        columns={
            "source_row": "small_source_row",
            "direction": "signal_direction",
            "completion_time": "signal_time",
            "completion_proxy_status": "small_completion_status",
        }
    )
    signals["pair_id"] = pair["pair_id"]
    signals["asset"] = pair["asset"]
    signals["small_setting"] = pair["small_setting"]
    signals["large_setting"] = pair["large_setting"]
    signals["split"] = assign_split(signals["session_date"], config)
    signals["strict_timing"] = signals["small_completion_status"].eq(
        config["timestamp_policy"]["strict_small_signal_status"]
    )

    large_state = large.loc[large["completion_time"].notna()].copy()
    large_state_columns = [
        "session_date",
        "source_row",
        "completion_time",
        "direction",
        "run_id",
        "run_length",
        "run_reversal_completion_time",
        "rolling_trend_10_ticks",
        "rolling_trend_10_direction",
        "close",
    ]
    large_state = large_state[large_state_columns].rename(
        columns={
            "source_row": "large_source_row",
            "completion_time": "large_completion_time",
            "direction": "large_direction",
            "run_id": "large_run_id",
            "run_length": "large_run_length",
            "run_reversal_completion_time": "large_reversal_time",
            "rolling_trend_10_ticks": "large_rolling_trend_10_ticks",
            "rolling_trend_10_direction": "large_rolling_trend_10_direction",
            "close": "large_close",
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
    if not signals.loc[signals["large_completion_time"].notna(), "large_completion_time"].lt(
        signals.loc[signals["large_completion_time"].notna(), "signal_time"]
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
    signals["trend10_aligned"] = signals["aligned"] & signals[
        "large_rolling_trend_10_direction"
    ].eq(signals["signal_direction"])
    signals["large_reversal_age_seconds"] = (
        signals["signal_time"] - signals["large_reversal_time"]
    ).dt.total_seconds()
    signals["recent_co_reversal_15m"] = (
        signals["aligned"]
        & signals["large_reversal_age_seconds"].between(0, 15 * 60, inclusive="both")
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
    for minutes in config["large_confirmation_windows_minutes"]:
        signals[f"large_confirms_within_{minutes}m"] = signals[
            "large_confirmation_delay_seconds"
        ].between(0, minutes * 60, inclusive="both")
    tick_size = float(pair["tick_size"])
    signals["early_entry_advantage_ticks"] = (
        signals["signal_direction"]
        * (signals["large_confirmation_entry"] - signals["entry_open"])
        / tick_size
    )

    counter = signals["countertrend"] & signals["large_run_id"].notna()
    signals["countertrend_attempt_number"] = np.nan
    if counter.any():
        attempt_number = (
            signals.loc[counter]
            .groupby(
                ["session_date", "large_run_id", "signal_direction"],
                sort=False,
                observed=True,
            )
            .cumcount()
            + 1
        )
        signals.loc[counter, "countertrend_attempt_number"] = attempt_number.astype(float)
    signals["repeated_countertrend_attempt"] = signals[
        "countertrend_attempt_number"
    ].ge(2)
    signals["extended_large_run"] = signals["large_run_length"].ge(5)
    signals["extended_repeated_countertrend"] = (
        signals["countertrend"]
        & signals["extended_large_run"]
        & signals["repeated_countertrend_attempt"]
    )

    audit = {
        "pair_id": pair["pair_id"],
        "asset": pair["asset"],
        "small_setting": pair["small_setting"],
        "large_setting": pair["large_setting"],
        "small_rows": int(len(small)),
        "large_rows": int(len(large)),
        "small_reversal_signals_with_completion_proxy": int(len(signals)),
        "strict_timing_signals": int(signals["strict_timing"].sum()),
        "same_second_signal_sensitivity_rows": int((~signals["strict_timing"]).sum()),
        "strict_signals_with_larger_state": int(
            (signals["strict_timing"] & signals["large_state_available"]).sum()
        ),
        "larger_state_exact_match_violations": int(
            (
                signals["large_completion_time"].notna()
                & signals["large_completion_time"].ge(signals["signal_time"])
            ).sum()
        ),
    }
    return PairResult(pair=pair, signals=signals, audit=audit)


def bootstrap_rate_ci(
    frame: pd.DataFrame,
    outcome: str,
    rng: np.random.Generator,
    replicates: int,
) -> tuple[float, float]:
    if frame.empty:
        return math.nan, math.nan
    clustered = frame.groupby("session_date", sort=False, observed=True)[outcome].agg(
        ["sum", "count"]
    )
    successes = clustered["sum"].to_numpy(float)
    counts = clustered["count"].to_numpy(float)
    draws = rng.integers(0, len(clustered), size=(replicates, len(clustered)))
    rates = successes[draws].sum(axis=1) / counts[draws].sum(axis=1)
    return float(np.quantile(rates, 0.025)), float(np.quantile(rates, 0.975))


def bootstrap_difference_ci(
    frame: pd.DataFrame,
    cohort: pd.Series,
    outcome: str,
    rng: np.random.Generator,
    replicates: int,
) -> tuple[float, float, float, float, float]:
    work = frame.loc[cohort.isin(["aligned", "countertrend"])].copy()
    work["cohort"] = cohort.loc[work.index]
    rows: list[dict[str, Any]] = []
    for (session, name), group in work.groupby(
        ["session_date", "cohort"], sort=False, observed=True
    ):
        rows.append(
            {
                "session_date": session,
                "cohort": name,
                "successes": int(group[outcome].sum()),
                "count": int(len(group)),
            }
        )
    agg = pd.DataFrame(rows)
    if agg.empty:
        return (math.nan,) * 5
    sessions = pd.Index(work["session_date"].drop_duplicates())
    arrays: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for name in ("aligned", "countertrend"):
        subset = agg.loc[agg["cohort"].eq(name)].set_index("session_date")
        arrays[name] = (
            subset["successes"].reindex(sessions, fill_value=0).to_numpy(float),
            subset["count"].reindex(sessions, fill_value=0).to_numpy(float),
        )
    a_success, a_count = arrays["aligned"]
    c_success, c_count = arrays["countertrend"]
    aligned_rate = a_success.sum() / a_count.sum() if a_count.sum() else math.nan
    counter_rate = c_success.sum() / c_count.sum() if c_count.sum() else math.nan
    draws = rng.integers(0, len(sessions), size=(replicates, len(sessions)))
    draw_a_count = a_count[draws].sum(axis=1)
    draw_c_count = c_count[draws].sum(axis=1)
    valid = (draw_a_count > 0) & (draw_c_count > 0)
    differences = (
        a_success[draws].sum(axis=1)[valid] / draw_a_count[valid]
        - c_success[draws].sum(axis=1)[valid] / draw_c_count[valid]
    )
    return (
        float(aligned_rate),
        float(counter_rate),
        float(aligned_rate - counter_rate),
        float(np.quantile(differences, 0.025)),
        float(np.quantile(differences, 0.975)),
    )


def bootstrap_named_cohort_difference_ci(
    frame: pd.DataFrame,
    cohort: pd.Series,
    outcome: str,
    first_name: str,
    second_name: str,
    rng: np.random.Generator,
    replicates: int,
) -> tuple[float, float, float, float, float]:
    """Return first-minus-second rates and a session-cluster bootstrap interval."""
    work = frame.loc[cohort.isin([first_name, second_name])].copy()
    work["cohort"] = cohort.loc[work.index]
    rows: list[dict[str, Any]] = []
    for (session, name), group in work.groupby(
        ["session_date", "cohort"], sort=False, observed=True
    ):
        rows.append(
            {
                "session_date": session,
                "cohort": name,
                "successes": int(group[outcome].sum()),
                "count": int(len(group)),
            }
        )
    agg = pd.DataFrame(rows)
    if agg.empty:
        return (math.nan,) * 5
    sessions = pd.Index(work["session_date"].drop_duplicates())
    arrays: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for name in (first_name, second_name):
        subset = agg.loc[agg["cohort"].eq(name)].set_index("session_date")
        arrays[name] = (
            subset["successes"].reindex(sessions, fill_value=0).to_numpy(float),
            subset["count"].reindex(sessions, fill_value=0).to_numpy(float),
        )
    first_success, first_count = arrays[first_name]
    second_success, second_count = arrays[second_name]
    first_rate = (
        first_success.sum() / first_count.sum() if first_count.sum() else math.nan
    )
    second_rate = (
        second_success.sum() / second_count.sum() if second_count.sum() else math.nan
    )
    draws = rng.integers(0, len(sessions), size=(replicates, len(sessions)))
    draw_first_count = first_count[draws].sum(axis=1)
    draw_second_count = second_count[draws].sum(axis=1)
    valid = (draw_first_count > 0) & (draw_second_count > 0)
    differences = (
        first_success[draws].sum(axis=1)[valid] / draw_first_count[valid]
        - second_success[draws].sum(axis=1)[valid] / draw_second_count[valid]
    )
    return (
        float(first_rate),
        float(second_rate),
        float(first_rate - second_rate),
        float(np.quantile(differences, 0.025)),
        float(np.quantile(differences, 0.975)),
    )


def direction_mask(frame: pd.DataFrame, label: str) -> pd.Series:
    if label == "bullish":
        return frame["signal_direction"].eq(1)
    if label == "bearish":
        return frame["signal_direction"].eq(-1)
    return pd.Series(True, index=frame.index)


def summarize_pullbacks(
    signals: pd.DataFrame,
    pair_id: str,
    rng: np.random.Generator,
    replicates: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rate_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    samples = {
        "strict": signals["strict_timing"],
        "all_proxy_sensitivity": pd.Series(True, index=signals.index),
    }
    cohorts = {
        "aligned": signals["aligned"],
        "countertrend": signals["countertrend"],
        "aligned_trend10": signals["trend10_aligned"],
        "aligned_recent_co_reversal_15m": signals["recent_co_reversal_15m"],
    }
    for split in ("development", "validation", "test"):
        split_mask = signals["split"].eq(split)
        for sample_name, sample_mask in samples.items():
            base = split_mask & sample_mask & signals["prior_run_length"].isin([1, 2])
            exclusive = pd.Series("other", index=signals.index, dtype="string")
            exclusive.loc[signals["aligned"]] = "aligned"
            exclusive.loc[signals["countertrend"]] = "countertrend"
            for direction in ("both", "bullish", "bearish"):
                dm = direction_mask(signals, direction)
                for cohort_name, cohort_mask in cohorts.items():
                    for horizon in (1, 3, 5):
                        eligible = base & dm & cohort_mask & signals[f"eligible_L_ge_{horizon}"]
                        subset = signals.loc[eligible]
                        outcome = f"success_L_ge_{horizon}"
                        ci_low, ci_high = bootstrap_rate_ci(subset, outcome, rng, replicates)
                        rate_rows.append(
                            {
                                "pair_id": pair_id,
                                "split": split,
                                "timing_sample": sample_name,
                                "direction": direction,
                                "cohort": cohort_name,
                                "outcome": f"P(L>={horizon})",
                                "eligible_signals": int(len(subset)),
                                "successes": int(subset[outcome].sum()),
                                "rate": float(subset[outcome].mean()) if len(subset) else math.nan,
                                "cluster_bootstrap_ci_low": ci_low,
                                "cluster_bootstrap_ci_high": ci_high,
                                "median_forward_return_ticks": float(
                                    subset[f"forward_return_{horizon}_bars_ticks"].median()
                                )
                                if len(subset)
                                else math.nan,
                                "median_mfe_5_ticks": float(subset["mfe_5_bars_ticks"].median())
                                if len(subset)
                                else math.nan,
                                "median_mae_5_ticks": float(subset["mae_5_bars_ticks"].median())
                                if len(subset)
                                else math.nan,
                            }
                        )
                for horizon in (1, 3, 5):
                    comparison_base = base & dm & signals[f"eligible_L_ge_{horizon}"]
                    subset = signals.loc[comparison_base]
                    ar, cr, diff, low, high = bootstrap_difference_ci(
                        subset,
                        exclusive.loc[subset.index],
                        f"success_L_ge_{horizon}",
                        rng,
                        replicates,
                    )
                    comparison_rows.append(
                        {
                            "pair_id": pair_id,
                            "split": split,
                            "timing_sample": sample_name,
                            "direction": direction,
                            "outcome": f"P(L>={horizon})",
                            "aligned_rate": ar,
                            "countertrend_rate": cr,
                            "aligned_minus_countertrend": diff,
                            "cluster_bootstrap_ci_low": low,
                            "cluster_bootstrap_ci_high": high,
                            "aligned_n": int(
                                (comparison_base & signals["aligned"]).sum()
                            ),
                            "countertrend_n": int(
                                (comparison_base & signals["countertrend"]).sum()
                            ),
                        }
                    )
    return rate_rows, comparison_rows


def large_run_bucket(values: pd.Series) -> pd.Series:
    return pd.cut(
        values,
        bins=[0, 2, 4, 7, np.inf],
        labels=["1-2", "3-4", "5-7", "8+"],
    ).astype("string")


def summarize_countertrend_confirmations(
    signals: pd.DataFrame,
    pair_id: str,
    rng: np.random.Generator,
    replicates: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    run_buckets = large_run_bucket(signals["large_run_length"])
    cohort_masks = {
        "all_countertrend": signals["countertrend"],
        "large_run_1-2": signals["countertrend"] & run_buckets.eq("1-2"),
        "large_run_3-4": signals["countertrend"] & run_buckets.eq("3-4"),
        "large_run_5-7": signals["countertrend"] & run_buckets.eq("5-7"),
        "large_run_8+": signals["countertrend"] & run_buckets.eq("8+"),
        "first_attempt": signals["countertrend"]
        & signals["countertrend_attempt_number"].eq(1),
        "repeated_attempt": signals["countertrend"]
        & signals["repeated_countertrend_attempt"],
        "extended_repeated": signals["extended_repeated_countertrend"],
    }
    samples = {
        "strict": signals["strict_timing"],
        "all_proxy_sensitivity": pd.Series(True, index=signals.index),
    }
    for split in ("development", "validation", "test"):
        split_mask = signals["split"].eq(split)
        for sample_name, sample_mask in samples.items():
            for direction in ("both", "bullish", "bearish"):
                dm = direction_mask(signals, direction)
                for cohort_name, cohort_mask in cohort_masks.items():
                    subset = signals.loc[split_mask & sample_mask & dm & cohort_mask]
                    for minutes in (5, 15, 30, 60):
                        outcome = f"large_confirms_within_{minutes}m"
                        ci_low, ci_high = bootstrap_rate_ci(
                            subset, outcome, rng, replicates
                        )
                        confirmed_subset = subset.loc[subset[outcome]]
                        advantage = confirmed_subset["early_entry_advantage_ticks"].dropna()
                        rows.append(
                            {
                                "pair_id": pair_id,
                                "split": split,
                                "timing_sample": sample_name,
                                "direction": direction,
                                "cohort": cohort_name,
                                "window_minutes": minutes,
                                "signals": int(len(subset)),
                                "confirmed": int(subset[outcome].sum()),
                                "confirmation_rate": float(subset[outcome].mean())
                                if len(subset)
                                else math.nan,
                                "cluster_bootstrap_ci_low": ci_low,
                                "cluster_bootstrap_ci_high": ci_high,
                                "median_confirmation_delay_minutes": float(
                                    confirmed_subset["large_confirmation_delay_seconds"].median()
                                    / 60.0
                                )
                                if len(confirmed_subset)
                                else math.nan,
                                "median_early_entry_advantage_ticks": float(advantage.median())
                                if len(advantage)
                                else math.nan,
                                "early_entry_better_rate": float(advantage.gt(0).mean())
                                if len(advantage)
                                else math.nan,
                            }
                        )
    return rows


def summarize_exhaustion_comparisons(
    signals: pd.DataFrame,
    pair_id: str,
    rng: np.random.Generator,
    replicates: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    run_buckets = large_run_bucket(signals["large_run_length"])

    run_labels = pd.Series("other", index=signals.index, dtype="string")
    run_labels.loc[signals["countertrend"] & run_buckets.eq("1-2")] = "run_1-2"
    run_labels.loc[signals["countertrend"] & run_buckets.eq("8+")] = "run_8+"

    attempt_labels = pd.Series("other", index=signals.index, dtype="string")
    attempt_labels.loc[
        signals["countertrend"] & signals["countertrend_attempt_number"].eq(1)
    ] = "first_attempt"
    attempt_labels.loc[
        signals["countertrend"] & signals["repeated_countertrend_attempt"]
    ] = "repeated_attempt"

    contrasts = {
        "run_8+_minus_run_1-2": (run_labels, "run_8+", "run_1-2"),
        "repeated_minus_first_attempt": (
            attempt_labels,
            "repeated_attempt",
            "first_attempt",
        ),
    }
    samples = {
        "strict": signals["strict_timing"],
        "all_proxy_sensitivity": pd.Series(True, index=signals.index),
    }
    for split in ("development", "validation", "test"):
        split_mask = signals["split"].eq(split)
        for sample_name, sample_mask in samples.items():
            for direction in ("both", "bullish", "bearish"):
                base = signals.loc[
                    split_mask & sample_mask & direction_mask(signals, direction)
                ]
                for contrast_name, (labels, first_name, second_name) in contrasts.items():
                    cohort = labels.loc[base.index]
                    for minutes in (5, 15, 30, 60):
                        outcome = f"large_confirms_within_{minutes}m"
                        first_rate, second_rate, diff, low, high = (
                            bootstrap_named_cohort_difference_ci(
                                base,
                                cohort,
                                outcome,
                                first_name,
                                second_name,
                                rng,
                                replicates,
                            )
                        )
                        rows.append(
                            {
                                "pair_id": pair_id,
                                "split": split,
                                "timing_sample": sample_name,
                                "direction": direction,
                                "contrast": contrast_name,
                                "window_minutes": minutes,
                                "first_cohort": first_name,
                                "first_rate": first_rate,
                                "first_n": int(cohort.eq(first_name).sum()),
                                "second_cohort": second_name,
                                "second_rate": second_rate,
                                "second_n": int(cohort.eq(second_name).sum()),
                                "first_minus_second": diff,
                                "cluster_bootstrap_ci_low": low,
                                "cluster_bootstrap_ci_high": high,
                            }
                        )
    return rows


def write_methodology(config: dict[str, Any], audits: list[dict[str, Any]]) -> None:
    lines = [
        "# Methodology: multi-Range-XV alignment study",
        "",
        "## Design",
        "",
        "This is a bar-event study of multiple ATAS Range XV transformations of the same underlying instrument. Agreement is evaluated as a filter, not as independent confirmation.",
        "",
        "A small-chart reversal is known only at its completion proxy (the next small bar's start). The aligned larger state is the latest larger bar whose completion proxy is strictly earlier than the signal time. Exact timestamp matches are rejected, which prevents a larger bar completing in the same recorded second from leaking into the signal.",
        "",
        "Primary results additionally require the small signal's completion proxy to occur in a later recorded second. Same-second small bars are retained only as sensitivity analysis.",
        "",
        "## Frozen definitions",
        "",
    ]
    for key, value in config["definitions"].items():
        lines.append(f"- **{key.replace('_', ' ')}:** {value}.")
    lines.extend(
        [
            "",
            "Continuation `L` excludes the reversal bar itself and counts immediately following same-direction small bars. Session-censored horizons are excluded. Entries are represented by the next small bar's open.",
            "",
            "Large-chart confirmation is an outcome, not a signal-time feature: it is the first strictly later completed larger reversal in the small signal direction. Early-entry advantage is positive when the small-chart next-bar open is better than the larger-confirmation next-bar open in the direction of the proposed trade.",
            "",
            "## Inference",
            "",
            f"Rates and differences use {config['bootstrap']['replicates']:,} session-cluster bootstrap replicates. The chronological development, validation, and test partitions were fixed before outcome inspection. No independent-confirmation claim is made because each pair comes from the same trades.",
            "",
            "## Timing limitations",
            "",
            "The ATAS export omits `IndicatorCandle.LastTime`. Next-bar opening time is only a completion proxy at one-second resolution. Session-boundary bars and export-final bars have no proxy. The export timezone and configured ATAS session are not encoded; the supplied 18:00 session-date proxy is used consistently across paired files.",
            "",
            "## Pair audit",
            "",
            "```json",
            json.dumps(audits, indent=2),
            "```",
            "",
        ]
    )
    (REPORT_DIR / "methodology.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    config = load_config()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(config["bootstrap"]["seed"])
    replicates = int(config["bootstrap"]["replicates"])

    audits: list[dict[str, Any]] = []
    pullback_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    confirmation_rows: list[dict[str, Any]] = []
    exhaustion_comparison_rows: list[dict[str, Any]] = []

    for pair in config["pairs"]:
        print(f"Loading {pair['pair_id']} small bars", flush=True)
        small = read_bars(
            ROOT / pair["small_path"], float(pair["tick_size"]), include_small_outcomes=True
        )
        print(f"Loading {pair['pair_id']} larger bars", flush=True)
        large = read_bars(
            ROOT / pair["large_path"], float(pair["tick_size"]), include_small_outcomes=False
        )
        result = prepare_signals(small, large, pair, config)
        audits.append(result.audit)
        rates, comparisons = summarize_pullbacks(
            result.signals, pair["pair_id"], rng, replicates
        )
        pullback_rows.extend(rates)
        comparison_rows.extend(comparisons)
        confirmation_rows.extend(
            summarize_countertrend_confirmations(
                result.signals, pair["pair_id"], rng, replicates
            )
        )
        exhaustion_comparison_rows.extend(
            summarize_exhaustion_comparisons(
                result.signals, pair["pair_id"], rng, replicates
            )
        )
        del small, large, result

    pullbacks = pd.DataFrame(pullback_rows)
    comparisons = pd.DataFrame(comparison_rows)
    confirmations = pd.DataFrame(confirmation_rows)
    exhaustion_comparisons = pd.DataFrame(exhaustion_comparison_rows)
    pullbacks.to_csv(TABLE_DIR / "pullback_continuation.csv", index=False)
    comparisons.to_csv(TABLE_DIR / "aligned_vs_countertrend.csv", index=False)
    confirmations.to_csv(TABLE_DIR / "countertrend_large_confirmation.csv", index=False)
    exhaustion_comparisons.to_csv(
        TABLE_DIR / "exhaustion_comparisons.csv", index=False
    )
    pd.DataFrame(audits).to_csv(TABLE_DIR / "pair_audit.csv", index=False)

    manifest = {
        "study_id": config["study_id"],
        "run_id": RUN_ID,
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "input_manifest": "data/range_xv_exports_manifest.json",
        "tables": [
            "tables/pullback_continuation.csv",
            "tables/aligned_vs_countertrend.csv",
            "tables/countertrend_large_confirmation.csv",
            "tables/exhaustion_comparisons.csv",
            "tables/pair_audit.csv",
        ],
        "audits": audits,
    }
    (REPORT_DIR / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    write_methodology(config, audits)
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
