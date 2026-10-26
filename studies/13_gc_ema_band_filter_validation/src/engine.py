"""Causal candidate context and fixed-year filter comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

from abacus_sahadeva.cooldown import accepted_bar_indices


FILTERS = [
    "first_outer_close", "bullish_signal_body", "upper_half_close",
    "shallow_penetration_025", "less_falling_ema_050",
    "nonexpanding_sigma_110", "ny_morning_08_13",
    "first_outer_and_upper_half", "shallow_and_upper_half",
]
COOLDOWNS = [0, 5, 10, 20, 30]
HORIZONS = [5, 10, 15, 20, 30, 50, 100]
PRICE_SCALE = 1e-9
FIVE_NS = 300_000_000_000


def build_context(bars: pd.DataFrame, bands: pd.DataFrame) -> pd.DataFrame:
    """Return one row per original outer-band candidate, with past-only flags."""
    if len(bars) != len(bands) or not bars.ts_event.equals(bands.ts_event):
        raise ValueError("bar and band timestamps differ")
    ts = bars.ts_event
    ts_ns = ts.to_numpy(dtype="datetime64[ns]").astype(np.int64)
    if np.any(np.diff(ts_ns) <= 0):
        raise ValueError("bar timestamps not strictly increasing")
    if not np.array_equal(bands.available_at.to_numpy(dtype="datetime64[ns]").astype(np.int64), ts_ns + FIVE_NS):
        raise ValueError("band availability is not at completed five-minute close")
    price = {x: bars[x].to_numpy(dtype=np.float64) * PRICE_SCALE for x in ("open", "high", "low", "close")}
    sigma = bands.residual_sigma_225.to_numpy(dtype=np.float64)
    lower = bands.lower_outer_3sigma.to_numpy(dtype=np.float64)
    ema = bands.ema_base_225.to_numpy(dtype=np.float64)
    complete = ((bars.source_bar_count.to_numpy() == 5) &
                ~bars.is_partial_bar.to_numpy() &
                ~bars.is_mixed_contract_bar.to_numpy() &
                ~bars.is_mixed_adjustment_bar.to_numpy() &
                ~bars.contains_roll.to_numpy() &
                bars.raw_symbol.notna().to_numpy() &
                bars.price_adjustment.notna().to_numpy())
    signal = complete & np.isfinite(lower) & np.isfinite(sigma) & (sigma > 0) & (price["close"] <= lower)
    ny_close = (ts + pd.Timedelta(minutes=5)).dt.tz_convert("America/New_York")
    iso = ny_close.dt.isocalendar()
    prior_contiguous = np.r_[False, np.diff(ts_ns) == FIVE_NS]
    prior_above = np.r_[False, price["close"][:-1] > lower[:-1]]
    first = prior_contiguous & prior_above
    spread = price["high"] - price["low"]
    location = np.divide(price["close"] - price["low"], spread,
                         out=np.full(len(bars), np.nan), where=spread > 0)
    penetration = np.divide(lower - price["close"], sigma,
                            out=np.full(len(bars), np.nan), where=sigma > 0)
    slope = np.full(len(bars), np.nan)
    slope[20:] = (ema[20:] - ema[:-20]) / sigma[20:]
    sigma_ratio = np.full(len(bars), np.nan)
    sigma_ratio[20:] = sigma[20:] / sigma[:-20]
    idx = np.flatnonzero(signal)
    context = pd.DataFrame({
        "bar_index": idx, "signal_ts_utc": ts.iloc[idx].to_numpy(),
        "year": ny_close.dt.year.iloc[idx].to_numpy(),
        "session_date": bars.session_date.iloc[idx].astype(str).to_numpy(),
        "iso_week": (iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)).iloc[idx].to_numpy(),
        "signal_sigma": sigma[idx], "penetration_sigma": penetration[idx],
        "close_location": location[idx], "ema_slope_sigma_20": slope[idx],
        "sigma_ratio_20": sigma_ratio[idx],
        "first_outer_close": first[idx],
        "bullish_signal_body": price["close"][idx] > price["open"][idx],
        "upper_half_close": location[idx] >= 0.5,
        "shallow_penetration_025": penetration[idx] <= 0.25,
        "less_falling_ema_050": slope[idx] >= -0.5,
        "nonexpanding_sigma_110": sigma_ratio[idx] <= 1.1,
        "ny_morning_08_13": ((ny_close.dt.hour >= 8) & (ny_close.dt.hour < 13)).iloc[idx].to_numpy(),
    })
    context["first_outer_and_upper_half"] = context.first_outer_close & context.upper_half_close
    context["shallow_and_upper_half"] = context.shallow_penetration_025 & context.upper_half_close
    return context


def accepted_context(context: pd.DataFrame, rule: str, cooldown: int) -> pd.DataFrame:
    """Apply a causal filter before suppressing subsequent chart bars."""
    if rule == "unfiltered":
        candidate = context
    elif rule in FILTERS:
        candidate = context.loc[context[rule]]
    else:
        raise ValueError(f"unknown rule: {rule}")
    selected = accepted_bar_indices(candidate.bar_index.to_numpy(), cooldown)
    return candidate.loc[candidate.bar_index.isin(selected)]


def event_scores(events: pd.DataFrame) -> pd.DataFrame:
    result = events.copy()
    sigma = result.signal_sigma.to_numpy(dtype=float)
    if np.any(~np.isfinite(sigma) | (sigma <= 0)):
        raise ValueError("signal sigma must be positive and finite")
    result["mae_sigma"] = result.mae_points / sigma
    result["mfe_sigma"] = result.mfe_points / sigma
    result["clipped_score"] = np.minimum(result.mfe_sigma, 10) - np.minimum(result.mae_sigma, 10)
    return result


def summarize(events: pd.DataFrame, raw_count: int, accepted_count: int) -> dict:
    valid = event_scores(events.loc[events.status == "valid"])
    row = {"raw_candidates": int(raw_count), "accepted_signals": int(accepted_count),
           "valid_n": len(valid), "sessions": valid.session_date.nunique(),
           "weeks": valid.iso_week.nunique(),
           "excluded": int(accepted_count - len(valid))}
    for col in ("mae_points", "mfe_points", "terminal_points", "mae_sigma", "mfe_sigma", "clipped_score"):
        row[f"mean_{col}"] = float(valid[col].mean()) if len(valid) else None
        row[f"median_{col}"] = float(valid[col].median()) if len(valid) else None
    row["p90_mae_points"] = float(valid.mae_points.quantile(.9)) if len(valid) else None
    row["p90_mfe_points"] = float(valid.mfe_points.quantile(.9)) if len(valid) else None
    row["terminal_positive_rate"] = float((valid.terminal_points > 0).mean()) if len(valid) else None
    row["mfe_to_mae_mean_ratio"] = (float(valid.mfe_points.mean() / valid.mae_points.mean())
                                      if len(valid) and valid.mae_points.mean() > 0 else None)
    return row


def paired_week_bootstrap(candidate: pd.DataFrame, baseline: pd.DataFrame,
                          *, seed: int, replicates: int = 2000) -> tuple[float | None, float | None]:
    """Resample ISO weeks jointly for candidate-minus-baseline score means."""
    a = event_scores(candidate.loc[candidate.status == "valid"])
    b = event_scores(baseline.loc[baseline.status == "valid"])
    if a.empty or b.empty:
        return None, None
    weeks = sorted(set(a.iso_week) | set(b.iso_week))
    if len(weeks) < 8:
        return None, None
    ga = a.groupby("iso_week").clipped_score.agg(["sum", "count"]).reindex(weeks, fill_value=0)
    gb = b.groupby("iso_week").clipped_score.agg(["sum", "count"]).reindex(weeks, fill_value=0)
    rng = np.random.default_rng(seed)
    draw = rng.integers(0, len(weeks), size=(replicates, len(weeks)))
    asum = ga["sum"].to_numpy()[draw].sum(axis=1)
    an = ga["count"].to_numpy()[draw].sum(axis=1)
    bsum = gb["sum"].to_numpy()[draw].sum(axis=1)
    bn = gb["count"].to_numpy()[draw].sum(axis=1)
    diffs = asum / np.where(an > 0, an, np.nan) - bsum / np.where(bn > 0, bn, np.nan)
    diffs = diffs[np.isfinite(diffs)]
    if len(diffs) < replicates * .95:
        return None, None
    return float(np.quantile(diffs, .025)), float(np.quantile(diffs, .975))
