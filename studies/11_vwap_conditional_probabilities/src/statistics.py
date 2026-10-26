"""Blocked uncertainty and development-only supported conditional estimators."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd


def add_common_bins(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    result = frame.copy()
    if "prior_atr14" in result:
        result["atr_bin"] = "missing"
        for product, edges in config["atr_terciles"].items():
            mask = (result["product"] == product) & result.prior_atr14.notna()
            low, high = edges
            result.loc[mask & (result.prior_atr14 < low), "atr_bin"] = "low"
            result.loc[mask & (result.prior_atr14 >= low) & (result.prior_atr14 < high), "atr_bin"] = "middle"
            result.loc[mask & (result.prior_atr14 >= high), "atr_bin"] = "high"
    result["shared_week"] = pd.to_datetime(result.session_date).dt.to_period("W-SUN").astype(str)
    result["session_key"] = result["product"].astype(str) + ":" + result.session_date.astype(str)
    return result


def classify_ab(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    result = add_common_bins(frame, config)
    result["distance_bin"] = pd.cut(
        result.absolute_distance_sigma, config["bins"]["distance_sigma"],
        labels=config["labels"]["distance_sigma"], right=False,
    ).astype(str)
    result["elapsed_bin"] = pd.cut(
        result.elapsed_without_return_minutes, config["bins"]["elapsed_minutes"],
        labels=config["labels"]["elapsed_minutes"], right=False,
    ).astype(str)
    result["age_bin"] = pd.cut(
        result.anchor_age_minutes, config["bins"]["anchor_age_minutes"],
        labels=config["labels"]["anchor_age_minutes"], right=False,
    ).astype(str)
    result["remaining_bin"] = pd.cut(
        result.time_remaining_minutes, config["bins"]["time_remaining_minutes"],
        labels=config["labels"]["time_remaining_minutes"], right=False,
    ).astype(str)
    result["excursion_bin"] = pd.cut(
        result.max_excursion_sigma, config["bins"]["max_excursion_sigma"],
        labels=config["labels"]["max_excursion_sigma"], right=False,
    ).astype(str)
    result["path_context"] = (result.residence_state.fillna("unavailable").astype(str) + "|" +
                              result.vwap_slope_side_class.fillna("unavailable").astype(str))
    if "return_geometry_share" in result:
        result["geometry_bin"] = pd.cut(
            result.return_geometry_share, config["bins"]["geometry_share"],
            labels=config["labels"]["geometry_share"], right=False, include_lowest=True,
        ).astype(str)
    return result


def classify_corridor(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    result = add_common_bins(frame, config)
    result["position_bin"] = pd.cut(
        result.position_from_day, config["bins"]["corridor_position"],
        labels=config["labels"]["corridor_position"], right=False, include_lowest=True,
    ).astype(str)
    result["width_bin"] = pd.cut(
        result.corridor_width_day_sigma, config["bins"]["corridor_width_day_sigma"],
        labels=config["labels"]["corridor_width_day_sigma"], right=False,
    ).astype(str)
    result["hold_bin"] = pd.cut(
        result.prior_hold_minutes, config["bins"]["prior_hold_minutes"],
        labels=config["labels"]["prior_hold_minutes"], right=False,
    ).astype(str)
    result["remaining_bin"] = pd.cut(
        result.time_remaining_minutes, config["bins"]["time_remaining_minutes"],
        labels=config["labels"]["time_remaining_minutes"], right=False,
    ).astype(str)
    result["path_context"] = (
        result.slope_agreement.fillna("unavailable").astype(str) + "|" +
        result.corridor_trend.fillna("unavailable").astype(str) + "|" +
        result.hold_bin.fillna("unavailable").astype(str)
    )
    return result


def block_rate(frame: pd.DataFrame, outcome: str, positive,
               rng: np.random.Generator, repetitions: int = 400) -> dict:
    valid = frame[frame[outcome].notna()].copy()
    n = len(valid)
    if n == 0:
        return {"numerator": 0, "denominator": 0, "probability": None,
                "ci_low": None, "ci_high": None, "episodes": 0,
                "product_sessions": 0, "shared_weeks": 0}
    valid["_success"] = (valid[outcome] == positive).astype(int)
    weekly = valid.groupby("shared_week")._success.agg(["sum", "count"])
    weights = rng.multinomial(len(weekly), np.full(len(weekly), 1 / len(weekly)), size=repetitions)
    draws = (weights @ weekly["sum"].to_numpy(dtype=float)) / (
        weights @ weekly["count"].to_numpy(dtype=float)
    )
    wins = int(valid._success.sum())
    return {
        "numerator": wins, "denominator": n, "probability": wins / n,
        "ci_low": float(np.quantile(draws, .025)), "ci_high": float(np.quantile(draws, .975)),
        "episodes": int(valid.episode_id.nunique()) if "episode_id" in valid else int(valid.event_id.nunique()),
        "product_sessions": int(valid.session_key.nunique()), "shared_weeks": int(len(weekly)),
    }


def outcome_counts(frame: pd.DataFrame, column: str, classes: Iterable[str]) -> dict:
    return {name: int((frame[column] == name).sum()) for name in classes}


def _probability_table(train: pd.DataFrame, keys: list[str], outcome: str,
                       classes: list[str], alpha: float) -> pd.DataFrame:
    counts = train.groupby(keys + [outcome], dropna=False, observed=True).size().unstack(fill_value=0)
    for name in classes:
        if name not in counts:
            counts[name] = 0
    counts = counts[classes]
    total = counts.sum(axis=1)
    probabilities = (counts + alpha).div(total + alpha * len(classes), axis=0)
    probabilities.columns = [f"p_{name}" for name in classes]
    table = probabilities.copy()
    table["support"] = total
    return table.reset_index()


def _apply_tables(target: pd.DataFrame, tables: list[tuple[list[str], pd.DataFrame, int]],
                  classes: list[str]) -> tuple[np.ndarray, np.ndarray]:
    probabilities = np.full((len(target), len(classes)), np.nan)
    source_support = np.zeros(len(target), dtype=int)
    base = target.reset_index(drop=True)
    for keys, table, floor in tables:
        columns = keys + ["support"] + [f"p_{name}" for name in classes]
        if keys:
            merged = base[keys].merge(table[columns], on=keys, how="left", sort=False)
        else:
            merged = pd.concat([table[columns]] * len(base), ignore_index=True)
        eligible = np.isnan(probabilities[:, 0]) & merged.support.fillna(0).to_numpy().astype(int).__ge__(floor)
        if eligible.any():
            probabilities[eligible] = merged.loc[eligible, [f"p_{name}" for name in classes]].to_numpy(dtype=float)
            source_support[eligible] = merged.loc[eligible, "support"].to_numpy(dtype=int)
    if np.isnan(probabilities).any():
        raise ValueError("conditional estimator backoff failed")
    return probabilities, source_support


def supported_predictions(train: pd.DataFrame, target: pd.DataFrame, outcome: str,
                          classes: list[str], base_keys: list[str], extra_keys: list[str],
                          min_support: int, alpha: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    base_table = _probability_table(train, base_keys, outcome, classes, alpha)
    fallback_keys = [key for key in base_keys if key not in ("atr_bin", "clock_window")]
    fallback_table = _probability_table(train, fallback_keys, outcome, classes, alpha)
    product_keys = ["product"] if "product" in base_keys else []
    product_table = _probability_table(train, product_keys, outcome, classes, alpha) if product_keys else None
    global_counts = train[outcome].value_counts().reindex(classes, fill_value=0).to_numpy(dtype=float)
    global_probs = (global_counts + alpha) / (global_counts.sum() + alpha * len(classes))
    global_table = pd.DataFrame({f"p_{name}": [global_probs[index]] for index, name in enumerate(classes)})
    global_table["support"] = len(train)
    base_tables = [(base_keys, base_table, min_support),
                   (fallback_keys, fallback_table, min_support)]
    if product_table is not None:
        base_tables.append((product_keys, product_table, min_support))
    base_tables.append(([], global_table, 0))
    base_prob, base_support = _apply_tables(target, base_tables, classes)

    augmented_keys = base_keys + extra_keys
    augmented_table = _probability_table(train, augmented_keys, outcome, classes, alpha)
    merged = target.reset_index(drop=True)[augmented_keys].merge(
        augmented_table[augmented_keys + ["support"] + [f"p_{name}" for name in classes]],
        on=augmented_keys, how="left", sort=False,
    )
    use = merged.support.fillna(0).to_numpy(dtype=int) >= min_support
    augmented_prob = base_prob.copy()
    augmented_support = np.zeros(len(target), dtype=int)
    if use.any():
        augmented_prob[use] = merged.loc[use, [f"p_{name}" for name in classes]].to_numpy(dtype=float)
        augmented_support[use] = merged.loc[use, "support"].to_numpy(dtype=int)
    return base_prob, augmented_prob, augmented_support


def brier_losses(outcomes: pd.Series, probabilities: np.ndarray,
                 classes: list[str]) -> np.ndarray:
    codes = pd.Categorical(outcomes, categories=classes).codes
    if (codes < 0).any():
        raise ValueError("unknown outcome class")
    truth = np.zeros_like(probabilities)
    truth[np.arange(len(codes)), codes] = 1.0
    return np.sum((probabilities - truth) ** 2, axis=1) / 2.0


def score_interval(frame: pd.DataFrame, baseline_loss: np.ndarray,
                   augmented_loss: np.ndarray, rng: np.random.Generator,
                   repetitions: int = 400) -> dict:
    scored = frame[["shared_week"]].copy()
    scored["baseline"] = baseline_loss
    scored["augmented"] = augmented_loss
    weekly = scored.groupby("shared_week").agg(
        baseline=("baseline", "sum"), augmented=("augmented", "sum"), n=("baseline", "size")
    )
    weights = rng.multinomial(len(weekly), np.full(len(weekly), 1 / len(weekly)), size=repetitions)
    baseline_draw = (weights @ weekly.baseline.to_numpy()) / (weights @ weekly.n.to_numpy())
    augmented_draw = (weights @ weekly.augmented.to_numpy()) / (weights @ weekly.n.to_numpy())
    differences = augmented_draw - baseline_draw
    point_base = float(np.mean(baseline_loss))
    point_aug = float(np.mean(augmented_loss))
    return {
        "baseline_brier": point_base, "augmented_brier": point_aug,
        "brier_difference": point_aug - point_base,
        "difference_ci_low": float(np.quantile(differences, .025)),
        "difference_ci_high": float(np.quantile(differences, .975)),
        "relative_error_reduction": ((point_base - point_aug) / point_base if point_base else None),
        "shared_weeks": int(len(weekly)),
    }


def calibration_rows(frame: pd.DataFrame, probabilities: np.ndarray,
                     outcomes: pd.Series, classes: list[str], model: str,
                     question: str, split: str) -> list[dict]:
    rows: list[dict] = []
    edges = np.linspace(0, 1, 11)
    for class_index, name in enumerate(classes):
        predicted = probabilities[:, class_index]
        observed = (outcomes.to_numpy() == name).astype(float)
        bins = np.minimum(9, np.searchsorted(edges, predicted, side="right") - 1)
        bins = np.maximum(0, bins)
        for index in range(10):
            mask = bins == index
            if not mask.any():
                continue
            rows.append({
                "question": question, "split": split, "model": model,
                "outcome_class": name, "probability_bin": f"{index / 10:.1f}-{(index + 1) / 10:.1f}",
                "rows": int(mask.sum()), "mean_predicted": float(predicted[mask].mean()),
                "observed_rate": float(observed[mask].mean()),
                "product_sessions": int(frame.loc[mask, "session_key"].nunique()),
            })
    return rows
