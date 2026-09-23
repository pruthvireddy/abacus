from __future__ import annotations

import math
import zlib
from typing import Any, Iterable

import numpy as np
import pandas as pd


ANALYSIS_SPLITS = ("development", "validation", "test", "full")
DIRECTIONS = ("long", "short", "all")


def stable_seed(base_seed: int, *parts: Any) -> int:
    suffix = "|".join(map(str, parts)).encode("utf-8")
    return (int(base_seed) + zlib.crc32(suffix)) % (2**32 - 1)


def split_frame(frame: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "full":
        return frame.loc[frame["split"].isin(["development", "validation", "test"])]
    return frame.loc[frame["split"].eq(split)]


def side_frame(frame: pd.DataFrame, direction: str) -> pd.DataFrame:
    if direction == "all":
        return frame
    return frame.loc[frame["signal_side"].eq(direction)]


def _block_indices(rng: np.random.Generator, n_dates: int, reps: int, block_length: int) -> np.ndarray:
    if block_length <= 1:
        return rng.integers(0, n_dates, size=(reps, n_dates))
    blocks = int(math.ceil(n_dates / block_length))
    starts = rng.integers(0, n_dates, size=(reps, blocks))
    offsets = np.arange(block_length, dtype=np.int64)
    indices = (starts[..., None] + offsets) % n_dates
    return indices.reshape(reps, blocks * block_length)[:, :n_dates]


def session_bootstrap_probability(
    frame: pd.DataFrame,
    eligible_column: str,
    success_column: str,
    reps: int,
    seed: int,
    block_length: int = 1,
) -> dict[str, float | int]:
    eligible = frame.loc[frame[eligible_column].fillna(False)].copy()
    n = int(len(eligible))
    successes = int(eligible[success_column].astype("boolean").fillna(False).sum())
    probability = successes / n if n else math.nan
    dates = sorted(frame["export_date"].dropna().unique())
    if not dates:
        return {
            "eligible_n": n,
            "successes": successes,
            "probability": probability,
            "ci_low": math.nan,
            "ci_high": math.nan,
            "export_dates": 0,
            "valid_bootstrap_replicates": 0,
        }
    grouped = eligible.groupby("export_date", observed=True)[success_column].agg(["size", "sum"])
    denominators = np.array([grouped.loc[d, "size"] if d in grouped.index else 0 for d in dates], dtype=float)
    numerators = np.array([grouped.loc[d, "sum"] if d in grouped.index else 0 for d in dates], dtype=float)
    rng = np.random.default_rng(seed)
    idx = _block_indices(rng, len(dates), reps, block_length)
    den = denominators[idx].sum(axis=1)
    num = numerators[idx].sum(axis=1)
    valid = den > 0
    draws = num[valid] / den[valid]
    ci_low, ci_high = (np.quantile(draws, [0.025, 0.975]) if len(draws) else (math.nan, math.nan))
    return {
        "eligible_n": n,
        "successes": successes,
        "probability": probability,
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "export_dates": int(len(dates)),
        "valid_bootstrap_replicates": int(len(draws)),
    }


def paired_session_bootstrap_difference(
    left: pd.DataFrame,
    right: pd.DataFrame,
    eligible_column: str,
    success_column: str,
    reps: int,
    seed: int,
    block_length: int = 1,
) -> dict[str, float | int]:
    dates = sorted(set(left["export_date"].dropna()) & set(right["export_date"].dropna()))
    if not dates:
        return {"difference": math.nan, "ci_low": math.nan, "ci_high": math.nan, "p_value": math.nan, "paired_dates": 0}

    def counts(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        eligible = frame.loc[frame[eligible_column].fillna(False)]
        grouped = eligible.groupby("export_date", observed=True)[success_column].agg(["size", "sum"])
        den = np.array([grouped.loc[d, "size"] if d in grouped.index else 0 for d in dates], dtype=float)
        num = np.array([grouped.loc[d, "sum"] if d in grouped.index else 0 for d in dates], dtype=float)
        return num, den

    left_num, left_den = counts(left)
    right_num, right_den = counts(right)
    left_p = left_num.sum() / left_den.sum() if left_den.sum() else math.nan
    right_p = right_num.sum() / right_den.sum() if right_den.sum() else math.nan
    observed = left_p - right_p
    rng = np.random.default_rng(seed)
    idx = _block_indices(rng, len(dates), reps, block_length)
    ld = left_den[idx].sum(axis=1)
    rd = right_den[idx].sum(axis=1)
    valid = (ld > 0) & (rd > 0)
    draws = left_num[idx].sum(axis=1)[valid] / ld[valid] - right_num[idx].sum(axis=1)[valid] / rd[valid]
    if len(draws):
        low, high = np.quantile(draws, [0.025, 0.975])
        tail = min((np.sum(draws <= 0) + 1) / (len(draws) + 1), (np.sum(draws >= 0) + 1) / (len(draws) + 1))
        p_value = min(1.0, 2.0 * tail)
    else:
        low = high = p_value = math.nan
    return {
        "difference": float(observed),
        "ci_low": float(low),
        "ci_high": float(high),
        "p_value": float(p_value),
        "paired_dates": int(len(dates)),
        "valid_bootstrap_replicates": int(len(draws)),
    }


def holm_adjust(p_values: Iterable[float]) -> list[float]:
    values = np.asarray(list(p_values), dtype=float)
    adjusted = np.full(len(values), np.nan)
    valid_positions = np.flatnonzero(np.isfinite(values))
    if not len(valid_positions):
        return adjusted.tolist()
    order = valid_positions[np.argsort(values[valid_positions])]
    running = 0.0
    m = len(order)
    for rank, position in enumerate(order):
        candidate = min(1.0, (m - rank) * values[position])
        running = max(running, candidate)
        adjusted[position] = running
    return adjusted.tolist()


def numeric_summary(values: pd.Series) -> dict[str, float | int]:
    clean = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if clean.empty:
        return {
            "n": 0,
            "mean": math.nan,
            "median": math.nan,
            "p75": math.nan,
            "p90": math.nan,
            "p95": math.nan,
            "max": math.nan,
        }
    q = clean.quantile([0.5, 0.75, 0.9, 0.95, 1.0])
    return {
        "n": int(len(clean)),
        "mean": float(clean.mean()),
        "median": float(q.loc[0.5]),
        "p75": float(q.loc[0.75]),
        "p90": float(q.loc[0.9]),
        "p95": float(q.loc[0.95]),
        "max": float(q.loc[1.0]),
    }
