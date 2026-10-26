"""Prespecified probability, shared-date uncertainty, and overlap tables."""

from __future__ import annotations

import math
import numpy as np
import pandas as pd


def classify(events: pd.DataFrame, config: dict) -> pd.DataFrame:
    frame = events.copy()
    slope = config["slope"]
    nonflat = (frame.price_slope_atr.abs() >= slope["price_min_abs_prior_atr14"]) & (
        frame.vwap_slope_atr.abs() >= slope["vwap_min_abs_prior_atr14"])
    frame["slope_class"] = "flat_or_unavailable"
    frame.loc[nonflat & (frame.price_slope * frame.vwap_slope > 0), "slope_class"] = "aligned"
    frame.loc[nonflat & (frame.price_slope * frame.vwap_slope < 0), "slope_class"] = "opposing"
    frame["material_separation"] = frame.vwap_minus_twap_ticks.abs() >= frame["product"].map(config["material_dislocation_min_abs_ticks"])
    frame["absolute_distance_sigma"] = frame.signed_distance_sigma.abs()
    frame["distance_bin"] = pd.cut(frame.absolute_distance_sigma, [-math.inf, .5, 1., math.inf],
                                    labels=["<0.5", "0.5-1", "1+"], right=False).astype(str)
    edges = config["matching"]["atr_product_development_terciles"]
    frame["atr_bin"] = "missing"
    for product, (low, high) in edges.items():
        mask = (frame["product"] == product) & frame.prior_atr14.notna()
        frame.loc[mask & (frame.prior_atr14 < low), "atr_bin"] = "low"
        frame.loc[mask & (frame.prior_atr14 >= low) & (frame.prior_atr14 < high), "atr_bin"] = "middle"
        frame.loc[mask & (frame.prior_atr14 >= high), "atr_bin"] = "high"
    frame["age_bin"] = np.where(frame.anchor_age_minutes < 240, "60-239", "240+")
    frame["session_key"] = frame["product"] + ":" + frame.session_date
    return frame


def _date_matrix(frame: pd.DataFrame, label: str, positive=True) -> tuple[np.ndarray, np.ndarray]:
    g = frame.assign(_success=(frame[label] == positive).astype(int)).groupby("session_date")._success.agg(["sum", "count"])
    return g["sum"].to_numpy(dtype=float), g["count"].to_numpy(dtype=float)


def rate(frame: pd.DataFrame, label: str, rng: np.random.Generator, positive=True, repetitions=400) -> dict:
    n = len(frame)
    if not n:
        return {"numerator": 0, "denominator": 0, "probability": None,
                "ci_low": None, "ci_high": None, "product_sessions": 0, "shared_dates": 0,
                "session_weighted_probability": None, "session_weighted_ci_low": None,
                "session_weighted_ci_high": None}
    wins = int((frame[label] == positive).sum())
    k, d = _date_matrix(frame, label, positive)
    weights = rng.multinomial(len(k), np.full(len(k), 1/len(k)), size=repetitions)
    draws = (weights @ k) / (weights @ d)
    session_means = frame.assign(_success=(frame[label] == positive).astype(float)).groupby("session_key")._success.mean()
    session_table = session_means.reset_index()
    session_table["session_date"] = session_table.session_key.str.rsplit(":", n=1).str[-1]
    per_date = session_table.groupby("session_date")._success.agg(["sum","count"]).reindex(
        frame.session_date.drop_duplicates().sort_values().to_numpy(), fill_value=0)
    session_draws = (weights @ per_date["sum"].to_numpy()) / (weights @ per_date["count"].to_numpy())
    return {"numerator": wins, "denominator": n, "probability": wins/n,
            "ci_low": float(np.quantile(draws, .025)), "ci_high": float(np.quantile(draws, .975)),
            "product_sessions": int(frame.session_key.nunique()), "shared_dates": int(len(k)),
            "session_weighted_probability": float(session_means.mean()),
            "session_weighted_ci_low": float(np.quantile(session_draws,.025)),
            "session_weighted_ci_high": float(np.quantile(session_draws,.975))}


def raw_difference(frame: pd.DataFrame, class_col: str, treated: str, baseline: str,
                   outcome: str, rng: np.random.Generator, repetitions=400) -> dict:
    subset = frame[frame[class_col].isin([treated, baseline])]
    if subset.empty:
        return {"difference": None, "ci_low": None, "ci_high": None}
    dates, dc = np.unique(subset.session_date.to_numpy(), return_inverse=True)
    is_t = (subset[class_col].to_numpy() == treated).astype(int)
    success = (subset[outcome].to_numpy() == True).astype(int)
    counts = np.zeros((len(dates), 2, 2), dtype=float)
    np.add.at(counts, (dc, is_t, np.zeros(len(subset), dtype=int)), 1)
    np.add.at(counts, (dc, is_t, np.ones(len(subset), dtype=int)), success)
    all_counts = counts.sum(axis=0)
    if min(all_counts[0,0], all_counts[1,0]) == 0:
        return {"difference": None, "ci_low": None, "ci_high": None}
    point = all_counts[1,1]/all_counts[1,0] - all_counts[0,1]/all_counts[0,0]
    weights = rng.multinomial(len(dates), np.full(len(dates), 1/len(dates)), size=repetitions)
    boot = np.tensordot(weights, counts, axes=(1,0))
    draws = boot[:,1,1]/boot[:,1,0] - boot[:,0,1]/boot[:,0,0]
    draws = draws[np.isfinite(draws)]
    return {"difference": float(point), "ci_low": float(np.quantile(draws,.025)),
            "ci_high": float(np.quantile(draws,.975))}


def matched_difference(frame: pd.DataFrame, class_col: str, treated: str, baseline: str,
                       outcome: str, q2: bool, rng: np.random.Generator, repetitions=400) -> dict:
    all_treated = int((frame[class_col] == treated).sum())
    all_baseline = int((frame[class_col] == baseline).sum())
    subset = frame[frame[class_col].isin([treated, baseline]) & frame[outcome].notna() &
                   (frame.side != 0) & (frame.atr_bin != "missing")].copy()
    keys = ["product", "side", "distance_bin", "clock_window", "atr_bin", "age_bin"]
    if q2:
        keys.append("state")
    if subset.empty:
        return {"matched_difference": None, "matched_ci_low": None, "matched_ci_high": None,
                "matched_treated": 0, "matched_baseline": 0, "unmatched_treated": 0,
                "unmatched_baseline": 0, "context_excluded_treated": all_treated,
                "context_excluded_baseline": all_baseline, "common_strata": 0}
    subset["stratum"] = subset[keys].astype(str).agg("|".join, axis=1)
    strata, sc = np.unique(subset.stratum.to_numpy(), return_inverse=True)
    dates, dc = np.unique(subset.session_date.to_numpy(), return_inverse=True)
    is_t = (subset[class_col].to_numpy() == treated).astype(int)
    success = (subset[outcome].to_numpy() == True).astype(int)
    n = np.bincount(sc*2+is_t, minlength=len(strata)*2).reshape(-1,2)
    k = np.bincount(sc*2+is_t, weights=success, minlength=len(strata)*2).reshape(-1,2)
    overlap = (n[:,0] > 0) & (n[:,1] > 0)
    def estimate(counts: np.ndarray, wins: np.ndarray) -> float:
        common = (counts[:,0] > 0) & (counts[:,1] > 0)
        if not common.any():
            return math.nan
        treated_n = counts[common,1]
        return float(wins[common,1].sum()/treated_n.sum() -
                     np.sum(treated_n * wins[common,0]/counts[common,0])/treated_n.sum())
    point = estimate(n,k)
    group = subset.assign(_class=is_t, _success=success).groupby(["session_date","stratum","_class"], observed=True)._success.agg(["sum","count"]).reset_index()
    date_code = pd.Index(dates).get_indexer(group.session_date)
    stratum_code = pd.Index(strata).get_indexer(group.stratum)
    cell = stratum_code*2 + group._class.to_numpy(dtype=int)
    gc = group["count"].to_numpy(dtype=float)
    gk = group["sum"].to_numpy(dtype=float)
    weights = rng.multinomial(len(dates), np.full(len(dates), 1/len(dates)), size=repetitions)
    draws = []
    for w in weights:
        bn = np.bincount(cell, weights=w[date_code]*gc, minlength=len(strata)*2).reshape(-1,2)
        bk = np.bincount(cell, weights=w[date_code]*gk, minlength=len(strata)*2).reshape(-1,2)
        draws.append(estimate(bn,bk))
    draws = np.asarray(draws)
    draws = draws[np.isfinite(draws)]
    return {"matched_difference": point, "matched_ci_low": float(np.quantile(draws,.025)) if len(draws) else None,
            "matched_ci_high": float(np.quantile(draws,.975)) if len(draws) else None,
            "matched_treated": int(n[overlap,1].sum()), "matched_baseline": int(n[overlap,0].sum()),
            "unmatched_treated": int(n[~overlap,1].sum()), "unmatched_baseline": int(n[~overlap,0].sum()),
            "context_excluded_treated": all_treated-int(n[:,1].sum()),
            "context_excluded_baseline": all_baseline-int(n[:,0].sum()),
            "common_strata": int(overlap.sum()), "total_strata": len(strata)}


def describe_condition(frame: pd.DataFrame, question: str, condition: str,
                       rng: np.random.Generator) -> dict:
    if question == "Q1":
        chosen = frame[frame.state == condition]
        outcome = "y1_residence"
    elif question == "Q2":
        chosen = frame[frame.slope_class == condition]
        outcome = "y2_cross"
    else:
        chosen = frame if condition == "all" else frame[frame.material_separation == (condition == "material")]
        outcome = "vwap_win"
    valid = chosen[chosen[outcome].notna()]
    result = {"question": question, "condition": condition, "landmarks": len(chosen),
              "outcome_missing": len(chosen)-len(valid), **rate(valid, outcome, rng)}
    if question == "Q3":
        result["twap_wins"] = int((valid.vwap_error > valid.twap_error + 1e-8).sum())
        result["ties"] = int(valid.paired_tie.sum())
        result["baseline_probability"] = result["twap_wins"]/len(valid) if len(valid) else None
    return result


def paired_errors(frame: pd.DataFrame, rng: np.random.Generator) -> dict:
    valid = frame[frame.vwap_error.notna()]
    info = describe_condition(valid, "Q3", "all", rng)
    difference = valid.vwap_error - valid.twap_error
    if len(valid):
        by_date = valid.assign(_delta=difference).groupby("session_date")._delta.agg(["sum","count"])
        weights = rng.multinomial(len(by_date), np.full(len(by_date),1/len(by_date)), size=400)
        mean_draws = (weights @ by_date["sum"].to_numpy())/(weights @ by_date["count"].to_numpy())
    else:
        mean_draws = np.array([])
    info.update(vwap_mae=float(valid.vwap_error.mean()) if len(valid) else None,
                twap_mae=float(valid.twap_error.mean()) if len(valid) else None,
                last_price_mae=float(valid.last_price_error.mean()) if len(valid) else None,
                mean_error_difference=float(difference.mean()) if len(valid) else None,
                mean_error_ci_low=float(np.quantile(mean_draws,.025)) if len(mean_draws) else None,
                mean_error_ci_high=float(np.quantile(mean_draws,.975)) if len(mean_draws) else None,
                median_error_difference=float(difference.median()) if len(valid) else None)
    return info
