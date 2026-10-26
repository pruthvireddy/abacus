"""Summaries and offline report from saved event/window evidence only."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from pathlib import Path
import json
import math
import re
import struct
import zlib

import numpy as np
import pandas as pd
from abacus_bhishma.paths import load_workspace_paths

LABELS = {"B": "Return after departure", "A": "First outside-2σ fade",
          "C": "First VWAP retest bounce"}
PRIMARY = {"B": "window_frozen_contact", "A": "h30_barrier_0p5", "C": "h30_barrier_0p5"}


def read_evidence(stage: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_files = sorted((stage / "events").glob("events_*.parquet"))
    window_files = sorted((stage / "events").glob("windows_*.parquet"))
    if not event_files or len(event_files) != len(window_files):
        raise ValueError("missing extracted evidence partitions")
    events = pd.concat((pd.read_parquet(path) for path in event_files), ignore_index=True)
    windows = pd.concat((pd.read_parquet(path) for path in window_files), ignore_index=True)
    if events.event_id.duplicated().any():
        raise ValueError("duplicate event ID")
    events["ordinal"] = events.event_id.str.rsplit(":", n=1).str[-1].astype(int)
    events["direction_label"] = np.where(events.direction > 0, "long", "short")
    return events, windows


def _eligible(group: pd.DataFrame, strategy: str) -> pd.DataFrame:
    valid = group[group.exclusion.isna()].copy()
    if strategy != "B":
        valid = valid[valid.h30_evaluable == True]
    return valid


def _success(group: pd.DataFrame, strategy: str) -> np.ndarray:
    if strategy == "B":
        return (group.window_frozen_contact == True).to_numpy(dtype=float)
    return (group.h30_barrier_0p5 == "favorable").to_numpy(dtype=float)


def cluster_interval(group: pd.DataFrame, strategy: str, seed: int = 310729,
                     reps: int = 1000, cluster: str = "session_date") -> tuple[float | None, float | None, bool]:
    if group.empty:
        return None, None, True
    work = group.assign(_success=_success(group, strategy))
    summary = work.groupby(cluster)._success.agg(["sum", "count"])
    values = summary.to_numpy(dtype=float)
    if len(values) < 2:
        return None, None, True
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, len(values), size=(reps, len(values)))
    sampled = values[picks].sum(axis=1)
    rates = sampled[:, 0] / sampled[:, 1]
    return float(np.quantile(rates, .025)), float(np.quantile(rates, .975)), bool(work._success.nunique() == 1)


def summarize_cell(group: pd.DataFrame, strategy: str, windows: pd.DataFrame | None = None,
                   ci: bool = True) -> dict:
    valid = _eligible(group, strategy)
    n = len(valid)
    result = {"strategy": strategy, "events": len(group), "evaluable": n,
              "excluded": len(group) - n,
              "sessions": int(group[["product", "session_date"]].drop_duplicates().shape[0]),
              "calendar_dates": int(group.session_date.nunique())}
    result["sparse"] = n < 30 or result["sessions"] < 20
    if windows is not None:
        result["eligible_windows"] = len(windows)
        result["mature_windows"] = int((windows.mature_valid == True).sum())
        result["departure_windows"] = int((windows.departure == True).sum())
        result["no_departure_windows"] = int((windows.departure != True).sum())
        result["windows_with_event"] = int(group[["product", "session_date", "timeframe", "anchor", "window"]].drop_duplicates().shape[0])
        result["fraction_windows_with_event"] = (result["windows_with_event"] / len(windows)
                                                if len(windows) else None)
        result["opportunities_per_100_windows"] = 100 * len(group) / len(windows) if len(windows) else None
    if n == 0:
        result.update(successes=0, rate=None, ci_low=None, ci_high=None,
                      session_weighted_rate=None, degenerate=True)
        return result
    success = _success(valid, strategy)
    result["successes"] = int(success.sum())
    result["rate"] = float(success.mean())
    result["session_weighted_rate"] = float(valid.assign(_success=success).groupby(
        ["product", "session_date"])._success.mean().mean())
    low, high, deg = cluster_interval(valid, strategy) if ci else (None, None, len(set(success)) == 1)
    result.update(ci_low=low, ci_high=high, degenerate=deg)
    if ci:
        week = valid.copy()
        week["calendar_week"] = pd.to_datetime(week.session_date).dt.to_period("W").astype(str)
        week_low, week_high, _ = cluster_interval(week, strategy, seed=310730,
                                                  cluster="calendar_week")
    else:
        week_low = week_high = None
    result.update(week_ci_low=week_low, week_ci_high=week_high)
    if strategy == "B":
        result["evolving_returns"] = int((valid.window_evolving_contact == True).sum())
        result["nonreturns"] = n - result["successes"]
        result["conditional_return_median_minutes"] = (float(valid.loc[valid.window_frozen_contact == True,
            "frozen_contact_minute"].median()) if result["successes"] else None)
        result["already_target_at_reference"] = int((group.already_at_frozen_target == True).sum())
        result["zero_followup"] = int((group.exclusion == "zero_followup").sum())
        result["departure_return_per_all_windows"] = result["successes"] / len(windows) if windows is not None and len(windows) else None
        result["nonreturn_remaining_distance_median_ticks"] = (float(valid.loc[valid.window_frozen_contact != True,
            "remaining_frozen_distance_end_ticks"].median()) if result["nonreturns"] else None)
    else:
        counts = valid.h30_barrier_0p5.value_counts()
        for outcome in ("favorable", "adverse", "neither", "ambiguous"):
            result[outcome] = int(counts.get(outcome, 0))
        result["optimistic_rate"] = (result["favorable"] + result["ambiguous"]) / n
        result["median_barrier_ticks"] = float(valid.h30_barrier_0p5_ticks.median())
        result["median_first_barrier_minutes"] = float(valid.h30_barrier_0p5_minute.median())
        result["h30_open_gap_barriers"] = (int((valid.h30_barrier_open_gap == True).sum())
                                           if "h30_barrier_open_gap" in valid.columns else None)
        if strategy == "A":
            result["hit_3sigma_before_return"] = int((valid.hit_3sigma_before_return == True).sum())
            result["already_passed_3sigma"] = int((valid.already_passed_3sigma == True).sum())
            result["hit_3sigma_lower"] = (int((valid.hit_3sigma_pre_return_lower == True).sum())
                                          if "hit_3sigma_pre_return_lower" in valid.columns else None)
            result["hit_3sigma_upper"] = (int((valid.hit_3sigma_pre_return_upper == True).sum())
                                          if "hit_3sigma_pre_return_upper" in valid.columns else None)
            result["half_retracement_30"] = (int((valid.h30_half_retracement == True).sum())
                                               if "h30_half_retracement" in valid.columns else None)
        if strategy == "C":
            result["confirmed_touches"] = int((valid.confirmation == True).sum())
            for close_class in ("approach_side", "zone", "opposite_side"):
                result[f"touch_close_{close_class}"] = int((valid.touch_close_class == close_class).sum())
    for h in (10, 30, 60):
        capability = valid[valid[f"h{h}_evaluable"] == True]
        result[f"h{h}_n"] = len(capability)
        result[f"h{h}_signed_median_ticks"] = (float(capability[f"h{h}_signed_ticks"].median())
                                                 if len(capability) else None)
        result[f"h{h}_mfe_median_ticks"] = (float(capability[f"h{h}_mfe_ticks"].median())
                                              if len(capability) else None)
        result[f"h{h}_mae_median_ticks"] = (float(capability[f"h{h}_mae_ticks"].median())
                                              if len(capability) else None)
        result[f"h{h}_signed_p10_ticks"] = float(capability[f"h{h}_signed_ticks"].quantile(.1)) if len(capability) else None
        result[f"h{h}_signed_p90_ticks"] = float(capability[f"h{h}_signed_ticks"].quantile(.9)) if len(capability) else None
        result[f"h{h}_mfe_p90_ticks"] = float(capability[f"h{h}_mfe_ticks"].quantile(.9)) if len(capability) else None
        result[f"h{h}_mae_p90_ticks"] = float(capability[f"h{h}_mae_ticks"].quantile(.9)) if len(capability) else None
        if strategy == "B":
            result[f"h{h}_frozen_returns"] = int((capability[f"h{h}_frozen_contact"] == True).sum())
            result[f"h{h}_evolving_returns"] = int((capability[f"h{h}_evolving_contact"] == True).sum())
        else:
            label = f"h{h}_barrier_0p5"
            result[f"h{h}_favorable"] = int((capability[label] == "favorable").sum())
    result["distance_median_sigma"] = float(valid.distance_sigma.median())
    result["distance_median_ticks"] = float(valid.distance_ticks.median())
    result["extension_median_ticks"] = float(valid.max_extension_before_frozen_return_ticks.median()) if strategy in ("A", "B") else None
    if strategy in ("A", "B"):
        result["pre_return_extension_lower_median_ticks"] = (float(valid.pre_return_extension_lower_ticks.median())
            if "pre_return_extension_lower_ticks" in valid.columns else None)
        result["pre_return_extension_upper_median_ticks"] = (float(valid.pre_return_extension_upper_ticks.median())
            if "pre_return_extension_upper_ticks" in valid.columns else None)
        result["price_retracement_end_median_points"] = float(valid.price_retracement_to_end_points.median())
        result["vwap_motion_end_median_points"] = float(valid.vwap_motion_to_end_points.median())
    return result


def _windows_for(windows: pd.DataFrame, group: pd.DataFrame) -> pd.DataFrame:
    if group.empty:
        return windows.iloc[0:0]
    for key in ("product", "timeframe", "anchor", "window"):
        if group[key].nunique() == 1:
            windows = windows[windows[key] == group[key].iloc[0]]
    if group.session_date.nunique() == 1:
        windows = windows[windows.session_date == group.session_date.iloc[0]]
    if group.split.nunique() == 1:
        windows = windows[windows.session_date.map(lambda d: "development" if int(d[:4]) <= 2023 else "validation" if d[:4] == "2024" else "final") == group.split.iloc[0]]
    return windows


def scorecards(events: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy in ("B", "A", "C"):
        part = events[events.strategy == strategy]
        for product in ("ALL", "ES", "NQ", "GC"):
            sub = part if product == "ALL" else part[part["product"] == product]
            row = summarize_cell(sub, strategy, windows if product == "ALL" else windows[windows["product"] == product])
            row["product"] = product
            row["anchor"] = "ALL_CORRELATED_VIEWS"
            row["window"] = "ALL_CORRELATED_VIEWS"
            row["metric_id"] = f"{strategy.lower()}.{product.lower()}.primary"
            rows.append(row)
    return pd.DataFrame(rows)


def breakdown(events: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy in ("B", "A", "C"):
        part = events[events.strategy == strategy]
        for keys in (("product", "timeframe", "anchor", "window", "split"),
                     ("product", "year", "direction_label"),
                     ("product", "timeframe", "anchor", "window", "direction_label")):
            for values, group in part.groupby(list(keys), dropna=False):
                row = summarize_cell(group, strategy, _windows_for(windows, group), ci=len(group) >= 10)
                row["breakdown"] = "+".join(keys)
                row.update(dict(zip(keys, values)))
                row["metric_id"] = ".".join([strategy.lower(), *[str(value).lower() for value in values], "primary"])
                rows.append(row)
    return pd.DataFrame(rows)


def stability_table(breaks: pd.DataFrame) -> pd.DataFrame:
    part = breaks[breaks.breakdown == "product+timeframe+anchor+window+split"]
    rows = []
    for keys, group in part.groupby(["strategy", "product", "timeframe", "anchor", "window"]):
        row = dict(zip(("strategy", "product", "timeframe", "anchor", "window"), keys))
        for split in ("development", "validation", "final"):
            match = group[group.split == split]
            row[f"{split}_events"] = int(match.evaluable.iloc[0]) if len(match) else 0
            row[f"{split}_sessions"] = int(match.sessions.iloc[0]) if len(match) else 0
            row[f"{split}_rate"] = float(match.rate.iloc[0]) if len(match) and pd.notna(match.rate.iloc[0]) else None
            row[f"{split}_ci_low"] = float(match.ci_low.iloc[0]) if len(match) and pd.notna(match.ci_low.iloc[0]) else None
            row[f"{split}_ci_high"] = float(match.ci_high.iloc[0]) if len(match) and pd.notna(match.ci_high.iloc[0]) else None
        row["sparse_any_split"] = any(row[f"{split}_events"] < 30 or row[f"{split}_sessions"] < 20
                                      for split in ("development", "validation", "final"))
        rows.append(row)
    return pd.DataFrame(rows)


def horizon_table(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy in ("B", "A", "C"):
        part = _eligible(events[events.strategy == strategy], strategy)
        common = part[part.h60_evaluable == True]
        for cohort_name, cohort in (("horizon_capable", part), ("common_60min", common)):
            for h in (10, 30, 60):
                sub = cohort[cohort[f"h{h}_evaluable"] == True]
                if sub.empty:
                    continue
                row = {"strategy": strategy, "cohort": cohort_name, "horizon_minutes": h,
                       "events": len(sub), "median_signed_ticks": float(sub[f"h{h}_signed_ticks"].median()),
                       "median_mfe_ticks": float(sub[f"h{h}_mfe_ticks"].median()),
                       "median_mae_ticks": float(sub[f"h{h}_mae_ticks"].median()),
                       "signed_p10_ticks": float(sub[f"h{h}_signed_ticks"].quantile(.1)),
                       "signed_p90_ticks": float(sub[f"h{h}_signed_ticks"].quantile(.9)),
                       "mfe_p90_ticks": float(sub[f"h{h}_mfe_ticks"].quantile(.9)),
                       "mae_p90_ticks": float(sub[f"h{h}_mae_ticks"].quantile(.9))}
                if strategy == "B":
                    row.update(frozen_returns=int((sub[f"h{h}_frozen_contact"] == True).sum()),
                               evolving_returns=int((sub[f"h{h}_evolving_contact"] == True).sum()))
                else:
                    for label in ("favorable", "adverse", "neither", "ambiguous"):
                        row[label] = int((sub[f"h{h}_barrier_0p5"] == label).sum())
                rows.append(row)
    return pd.DataFrame(rows)


def landmark_table(events: pd.DataFrame) -> pd.DataFrame:
    part = _eligible(events[events.strategy == "B"], "B")
    rows = []
    for product in ("ALL", "ES", "NQ", "GC"):
        group = part if product == "ALL" else part[part["product"] == product]
        for minute in (10, 30, 60):
            eligible = group[group[f"h{minute}_evaluable"] == True]
            for mode in ("frozen", "evolving"):
                remaining = eligible[(eligible[f"{mode}_contact_minute"].isna()) |
                                     (eligible[f"{mode}_contact_minute"] >= minute)]
                returned_later = int((remaining[f"window_{mode}_contact"] == True).sum())
                rows.append({"product": product, "mode": mode, "landmark_minutes": minute,
                             "landmark_eligible": len(eligible), "still_unreturned": len(remaining),
                             "later_returns_by_window_end": returned_later,
                             "remaining_return_probability": returned_later / len(remaining) if len(remaining) else None})
    return pd.DataFrame(rows)


def return_survival(events: pd.DataFrame) -> pd.DataFrame:
    """Kaplan-Meier style descriptive curves with administrative window censoring."""
    part = _eligible(events[events.strategy == "B"], "B")
    rows = []
    for product in ("ALL", "ES", "NQ", "GC"):
        group = part if product == "ALL" else part[part["product"] == product]
        if group.empty:
            continue
        for mode in ("frozen", "evolving"):
            observed = (group[f"window_{mode}_contact"] == True).to_numpy()
            durations = np.where(observed, group[f"{mode}_contact_minute"].fillna(0).to_numpy() + 1,
                                 group.window_minutes_remaining.to_numpy()).astype(int)
            event_counts = pd.Series(durations[observed]).value_counts()
            censored_counts = pd.Series(durations[~observed]).value_counts()
            risk = len(group)
            survival = 1.0
            for minute in sorted(set(event_counts.index) | set(censored_counts.index)):
                happened = int(event_counts.get(minute, 0))
                censored = int(censored_counts.get(minute, 0))
                if risk <= 0:
                    break
                survival *= 1 - happened / risk
                rows.append({"product": product, "mode": mode, "minute": int(minute),
                             "at_risk": risk, "returns": happened, "censored": censored,
                             "survival_not_returned": survival,
                             "cumulative_return_estimate": 1 - survival})
                risk -= happened + censored
    return pd.DataFrame(rows)


def subset_table(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy in ("A", "C"):
        part = events[events.strategy == strategy]
        subsets = [("all", part), ("first_of_window", part[part.ordinal == 1]),
                   ("later", part[part.ordinal > 1])]
        if strategy == "C":
            subsets.append(("confirmation", part[part.confirmation == True]))
            subsets.append(("unconfirmed", part[part.confirmation != True]))
        for label, group in subsets:
            row = summarize_cell(group, strategy)
            row["subset"] = label
            rows.append(row)
    return pd.DataFrame(rows)


def path_table(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy in ("A", "C"):
        part = _eligible(events[events.strategy == strategy], strategy)
        for product in ("ALL", "ES", "NQ", "GC"):
            group = part if product == "ALL" else part[part["product"] == product]
            if group.empty:
                continue
            counts = group.window_barrier_0p5.value_counts()
            rows.append({"strategy": strategy, "product": product, "events": len(group),
                         "full_horizon_mfe_median_ticks": float(group.h30_mfe_ticks.median()),
                         "full_horizon_mae_median_ticks": float(group.h30_mae_ticks.median()),
                         "pre_barrier_mfe_median_ticks": float(group.h30_pre_barrier_mfe_ticks.median()),
                         "pre_barrier_mae_median_ticks": float(group.h30_pre_barrier_mae_ticks.median()),
                         "window_mfe_median_ticks": float(group.window_mfe_ticks.median()),
                         "window_mae_median_ticks": float(group.window_mae_ticks.median()),
                         **{f"window_{name}": int(counts.get(name, 0))
                            for name in ("favorable", "adverse", "neither", "ambiguous")}})
    return pd.DataFrame(rows)


def eligibility_table(root: Path) -> pd.DataFrame:
    path = root / "data/features/audits/feature_set=session_anchored_vwap/version=1.0.0/product_day_eligibility.parquet"
    audit = pd.read_parquet(path, columns=["product", "session_year", "eligible", "exclusion_reasons"])
    rows = []
    for (product, year), group in audit.groupby(["product", "session_year"]):
        row = {"product": product, "year": int(year), "candidate_days": len(group),
               "eligible_days": int((group.eligible == True).sum()),
               "excluded_unique_days": int((group.eligible != True).sum())}
        for reason in ("unsupported_historical_schedule_regime", "missing_expected_published_minute",
                       "source_rows_outside_expected_schedule", "exchange_holiday_or_shortened_session",
                       "no_source_rows", "source_condition_degraded"):
            row[reason] = int(group.exclusion_reasons.map(lambda reasons: reason in reasons).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def threshold_times(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy in ("A", "C"):
        part = _eligible(events[events.strategy == strategy], strategy)
        for product in ("ALL", "ES", "NQ", "GC"):
            group = part if product == "ALL" else part[part["product"] == product]
            for ticks in (4, 8, 16, 32):
                values = group[f"favorable_{ticks}ticks_first_minute"].dropna()
                rows.append({"strategy": strategy, "product": product,
                             "threshold_ticks": ticks, "events": len(group),
                             "reached_by_window_end": len(values),
                             "reach_probability": len(values) / len(group) if len(group) else None,
                             "conditional_median_minutes": float(values.median()) if len(values) else None,
                             "conditional_p90_minutes": float(values.quantile(.9)) if len(values) else None})
    return pd.DataFrame(rows)


def exclusion_table(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy in ("B", "A", "C"):
        group = events[events.strategy == strategy]
        for product in ("ALL", "ES", "NQ", "GC"):
            part = group if product == "ALL" else group[group["product"] == product]
            rows.append({"strategy": strategy, "product": product, "events": len(part),
                         "zero_followup": int((part.exclusion == "zero_followup").sum()),
                         "source_or_contract_discontinuity": int((part.exclusion == "source_or_contract_discontinuity").sum()),
                         "late_for_10m": int((part.h10_evaluable != True).sum()),
                         "late_for_30m": int((part.h30_evaluable != True).sum()),
                         "late_for_60m": int((part.h60_evaluable != True).sum()),
                         "already_frozen_target_at_reference": int((part.already_at_frozen_target == True).sum())})
    return pd.DataFrame(rows)


def cycle_table(windows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (product, timeframe, anchor, window), group in windows.groupby(
        ["product", "timeframe", "anchor", "window"]):
        row = {"product": product, "timeframe": timeframe, "anchor": anchor,
               "window": window, "eligible_windows": len(group),
               "mature_windows": int((group.mature_valid == True).sum()),
               "departure_windows": int((group.departure == True).sum()),
               "no_departure_windows": int((group.departure != True).sum()),
               "already_away": int((group.first_departure_class == "already_away").sum()),
               "fresh_departure": int((group.first_departure_class == "fresh").sum()),
               "unqualified_first_touches": int(group.unqualified_first_touches.sum()),
               "gap_throughs": int(group.gap_throughs.sum())}
        for mode in ("frozen", "evolving"):
            for label, count in (("zero", (group[f"{mode}_cycles"] == 0).sum()),
                                 ("one", (group[f"{mode}_cycles"] == 1).sum()),
                                 ("two_plus", (group[f"{mode}_cycles"] >= 2).sum())):
                row[f"{mode}_cycles_{label}"] = int(count)
        rows.append(row)
    return pd.DataFrame(rows)


def departure_class_table(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    part = events[events.strategy == "B"]
    for keys, group in part.groupby(["product", "timeframe", "anchor", "window",
                                     "departure_class", "split"]):
        row = summarize_cell(group, "B", ci=len(group) >= 10)
        row.update(dict(zip(("product", "timeframe", "anchor", "window",
                             "departure_class", "split"), keys)))
        rows.append(row)
    return pd.DataFrame(rows)


def window_population_table(windows: pd.DataFrame) -> pd.DataFrame:
    work = windows.copy()
    work["year"] = work.session_date.str[:4].astype(int)
    work["split"] = np.select([work.year <= 2023, work.year == 2024],
                               ["development", "validation"], default="final")
    rows = []
    for keys, group in work.groupby(["product", "year", "split", "timeframe", "anchor", "window"]):
        rows.append({**dict(zip(("product", "year", "split", "timeframe", "anchor", "window"), keys)),
                     "eligible_windows": len(group), "mature_valid_windows": int((group.mature_valid == True).sum()),
                     "departure_windows": int((group.departure == True).sum()),
                     "no_departure_windows": int((group.departure != True).sum()),
                     "already_away_windows": int((group.first_departure_class == "already_away").sum()),
                     "fresh_departure_windows": int((group.first_departure_class == "fresh").sum())})
    return pd.DataFrame(rows)


def sensitivity(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy in ("A", "C"):
        group = _eligible(events[events.strategy == strategy], strategy)
        for factor in (.25, .5, 1.0):
            key = f"h30_barrier_{str(factor).replace('.', 'p')}"
            counts = group[key].value_counts()
            rows.append({"strategy": strategy, "barrier_sigma": factor, "events": len(group),
                         **{x: int(counts.get(x, 0)) for x in ("favorable", "adverse", "neither", "ambiguous")}})
        for ticks in (4, 8, 16, 32):
            key = f"h30_barrier_{ticks}ticks"
            counts = group[key].value_counts()
            rows.append({"strategy": strategy, "barrier_ticks": ticks, "events": len(group),
                         **{x: int(counts.get(x, 0)) for x in ("favorable", "adverse", "neither", "ambiguous")}})
    return pd.DataFrame(rows)


def _baseline_one(events: pd.DataFrame, outcome_col: str) -> pd.DataFrame:
    """Exact observable-context matching; descriptive contrasts only."""
    work = events[events.strategy.isin(["A", "A_control", "C", "C_near"])].copy()
    work = work[(work.exclusion.isna()) & (work.h30_evaluable == True)]
    if work.empty:
        return pd.DataFrame()
    signal = pd.to_datetime(work.signal_ts, utc=True).dt.tz_convert("America/New_York")
    local_days = pd.to_datetime(work.session_date)
    starts = []
    for day, window in zip(local_days, work.window):
        if window == "globex":
            local = day - pd.Timedelta(days=1) + pd.Timedelta(hours=18)
        elif window == "asia":
            local = day - pd.Timedelta(days=1) + pd.Timedelta(hours=20)
        elif window == "london":
            local = day + pd.Timedelta(hours=3)
        else:
            local = day + pd.Timedelta(hours=9, minutes=30)
        starts.append(local.tz_localize("America/New_York"))
    work["hour_bin"] = [max(0, int((t - start).total_seconds() // 7200))
                        for t, start in zip(signal, starts)]
    work["age_bin"] = np.select([work.anchor_age_minutes < 60,
                                 work.anchor_age_minutes < 120], [0, 1], default=2)
    keys = ["product", "timeframe", "anchor", "window"]
    cutoffs = {}
    for key, group in work[work.split == "development"].groupby(keys):
        cutoffs[key] = tuple(float(x) for x in group.sigma.quantile([1 / 3, 2 / 3]))
    def bin_sigma(row):
        q = cutoffs.get(tuple(row[k] for k in keys))
        return -1 if q is None else 0 if row.sigma <= q[0] else 1 if row.sigma <= q[1] else 2
    work["sigma_bin"] = work.apply(bin_sigma, axis=1)
    work["success"] = work[outcome_col] == "favorable"
    strata = keys + ["split", "direction", "hour_bin", "age_bin", "sigma_bin"]
    rows = []
    def contribution_interval(items):
        if not items:
            return None, None
        values = pd.DataFrame(items).groupby("session_date")[["numerator", "denominator"]].sum().to_numpy()
        if len(values) < 2:
            return None, None
        rng = np.random.default_rng(310731)
        picks = rng.integers(0, len(values), size=(1000, len(values)))
        totals = values[picks].sum(axis=1)
        totals = totals[totals[:, 1] > 0]
        if len(totals) == 0:
            return None, None
        rates = totals[:, 0] / totals[:, 1]
        return float(np.quantile(rates, .025)), float(np.quantile(rates, .975))
    for period in ("ALL", "development", "validation", "final"):
        period_work = work if period == "ALL" else work[work.split == period]
        for treated, control in (("A", "A_control"), ("C", "C_near"),
                                 ("C_first", "C_later")):
            if treated == "C_first":
                left = period_work[(period_work.strategy == "C") & (period_work.ordinal == 1)]
                right = period_work[(period_work.strategy == "C") & (period_work.ordinal > 1)]
            else:
                left = period_work[period_work.strategy == treated]
                right = period_work[period_work.strategy == control]
            pool = right.groupby(strata).success.agg(["mean", "size"])
            control_groups = right.groupby(strata)
            matched = 0
            weighted_treated = weighted_control = 0.0
            contributions = []
            for key, group in left.groupby(strata):
                if key not in pool.index:
                    continue
                controls_here = control_groups.get_group(key)
                matched += len(group)
                weighted_treated += int(group.success.sum())
                weighted_control += len(group) * float(pool.loc[key, "mean"])
                contributions.extend({"session_date": date, "numerator": float(success),
                                      "denominator": 1.0}
                                     for date, success in zip(group.session_date, group.success))
                weight = len(group) / len(controls_here)
                contributions.extend({"session_date": date, "numerator": -weight * float(success),
                                      "denominator": 0.0}
                                     for date, success in zip(controls_here.session_date, controls_here.success))
            ci_low, ci_high = contribution_interval(contributions)
            rows.append({"split": period, "treated": treated, "control": control,
                         "treated_events": len(left), "control_events": len(right),
                         "matched_treated": matched, "unmatched_treated": len(left) - matched,
                         "treated_rate_matched": weighted_treated / matched if matched else None,
                         "control_rate_weighted": weighted_control / matched if matched else None,
                         "difference": (weighted_treated - weighted_control) / matched if matched else None,
                         "ci_low_conditional_overlap": ci_low, "ci_high_conditional_overlap": ci_high,
                         "treated_distance_sigma_median": float(left.distance_sigma.median()) if len(left) else None,
                         "control_distance_sigma_median": float(right.distance_sigma.median()) if len(right) else None,
                         "claim_status": "exploratory; no simultaneous familywise interval"})
    return pd.DataFrame(rows)


def baseline(events: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for barrier_definition, column in (("half_sigma", "h30_barrier_0p5"),
                                       ("fixed_8_ticks", "h30_barrier_8ticks")):
        for product in ("ALL", "ES", "NQ", "GC"):
            part = events if product == "ALL" else events[events["product"] == product]
            table = _baseline_one(part, column)
            table.insert(0, "product", product)
            table.insert(0, "barrier_definition", barrier_definition)
            frames.append(table)
    return pd.concat(frames, ignore_index=True)


def examples(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for product in ("ES", "NQ", "GC"):
        for strategy in ("B", "A", "C"):
            sub = events[(events["product"] == product) & (events.strategy == strategy)].copy()
            if sub.empty:
                continue
            if strategy == "B":
                sub["example_class"] = np.where(sub.exclusion.notna(), "excluded",
                    np.where(sub.window_frozen_contact == True, "return", "nonreturn"))
            else:
                sub["example_class"] = np.where(sub.exclusion.notna(), "excluded",
                    sub.h30_barrier_0p5.fillna("late"))
            for label, group in sub.groupby("example_class"):
                item = group.sort_values("signal_ts").iloc[0]
                rows.append({"product": product, "strategy": strategy, "class": label,
                             "event_id": item.event_id, "signal_ts": item.signal_ts,
                             "reference_price": item.reference_price,
                             "vwap": item.vwap, "sigma": item.sigma,
                             "tick": item.tick, "anchor": item.anchor, "window": item.window})
    return pd.DataFrame(rows)


def _fmt(value, percent=False):
    if value is None or pd.isna(value):
        return "—"
    if percent:
        return f"{100 * value:.1f}%"
    return f"{value:,.1f}" if isinstance(value, float) else f"{value:,}"


def write_figure(stage: Path, cards: pd.DataFrame) -> None:
    """Small offline SVG of the exhaustive primary A/C barrier outcomes."""
    (stage / "figures").mkdir(exist_ok=True)
    colors = {"favorable": "#2b8a6e", "adverse": "#cf604a",
              "neither": "#a4afc0", "ambiguous": "#8a6cb3"}
    labels = {"A": "Outside 2σ fade", "C": "First retest bounce"}
    parts = ["<svg xmlns='http://www.w3.org/2000/svg' width='900' height='250' viewBox='0 0 900 250'>",
             "<rect width='900' height='250' fill='#fff'/>",
             "<text x='30' y='30' font-size='20' font-family='system-ui' fill='#16223a'>30-minute barrier outcomes</text>"]
    for order, strategy in enumerate(("A", "C")):
        row = cards[(cards.strategy == strategy) & (cards["product"] == "ALL")].iloc[0]
        y = 75 + 70 * order
        parts.append(f"<text x='30' y='{y+16}' font-size='15' font-family='system-ui' fill='#16223a'>{labels[strategy]}</text>")
        left = 210
        for name in ("favorable", "adverse", "neither", "ambiguous"):
            width = 620 * int(row[name]) / row.evaluable if row.evaluable else 0
            parts.append(f"<rect x='{left:.2f}' y='{y}' width='{width:.2f}' height='28' fill='{colors[name]}'/>")
            left += width
        parts.append(f"<text x='840' y='{y+19}' font-size='13' font-family='system-ui' fill='#16223a'>n={row.evaluable:,}</text>")
    x = 30
    for name in ("favorable", "adverse", "neither", "ambiguous"):
        parts.append(f"<rect x='{x}' y='210' width='12' height='12' fill='{colors[name]}'/>")
        parts.append(f"<text x='{x+18}' y='221' font-size='13' font-family='system-ui' fill='#16223a'>{name.title()}</text>")
        x += 155
    parts.append("</svg>")
    (stage / "figures/barrier-outcomes.svg").write_text("".join(parts))
    # A compact PNG copy is selected explicitly for Narada's raster-only contract.
    width, height = 900, 250
    pixels = bytearray([255, 255, 255] * width * height)
    rgb = {"favorable": (43, 138, 110), "adverse": (207, 96, 74),
           "neither": (164, 175, 192), "ambiguous": (138, 108, 179)}
    def rect(x0, y0, x1, y1, color):
        for yy in range(y0, y1):
            start = (yy * width + x0) * 3
            pixels[start:start + (x1 - x0) * 3] = bytes(color) * (x1 - x0)
    for order, strategy in enumerate(("A", "C")):
        row = cards[(cards.strategy == strategy) & (cards["product"] == "ALL")].iloc[0]
        y = 70 + 70 * order
        x = 180
        cumulative = 0
        for name in ("favorable", "adverse", "neither", "ambiguous"):
            cumulative += int(row[name])
            end = min(800, 180 + round(620 * cumulative / row.evaluable)) if row.evaluable else x
            if end > x:
                rect(x, y, end, y + 32, rgb[name])
            x = end
    for i, name in enumerate(("favorable", "adverse", "neither", "ambiguous")):
        rect(180 + i * 155, 215, 205 + i * 155, 230, rgb[name])
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    scanlines = b"".join(b"\0" + pixels[y * width * 3:(y + 1) * width * 3]
                         for y in range(height))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(scanlines, 9)) + chunk(b"IEND", b""))
    (stage / "figures/barrier-outcomes.png").write_bytes(png)


def write_report(stage: Path, cards: pd.DataFrame, breaks: pd.DataFrame,
                 horizons: pd.DataFrame, cycles: pd.DataFrame, controls: pd.DataFrame,
                 samples: pd.DataFrame, events: pd.DataFrame, windows: pd.DataFrame) -> None:
    audit = json.loads((stage / "source-audit.json").read_text())
    checked_bars = sum(int(item.get("feature_bars_reconciled", 0)) for item in audit)
    checked_refs = sum(int(item.get("references_audited", 0)) for item in audit)
    lines = ["# Three session VWAP statistical studies", "",
             "Price-path evidence from the pinned Session-Anchored VWAP 1.0.0 release. "
             "Commission, slippage, latency, order type, and position sizing are unspecified. "
             "These are conditional movement observations, not net profitability.", "",
             "## Three-candidate scorecard", "",
             "| Candidate | Evaluable / events | Distinct product-sessions | Primary outcome | 95% session bootstrap interval |",
             "|---|---:|---:|---:|---:|"]
    for strategy in ("B", "A", "C"):
        row = cards[(cards.strategy == strategy) & (cards["product"] == "ALL")].iloc[0]
        label = LABELS[strategy]
        interval = f"{_fmt(row.ci_low, True)}–{_fmt(row.ci_high, True)}" if pd.notna(row.ci_low) else "unavailable"
        lines.append(f"| {label} | {row.evaluable:,} / {row.events:,} | {row.sessions:,} | "
                     f"{row.successes:,}/{row.evaluable:,} ({_fmt(row.rate, True)}) | {interval} |")
    lines += ["", "The scorecard pools seven overlapping anchor/window views and two correlated timeframes. "
              "Counts are events within those views; the session column deduplicates product × date. "
              "The bootstrap resamples shared session dates, retaining the correlated views and products together.", "",
              "![Exhaustive 30-minute barrier outcomes for A and C](figures/barrier-outcomes.svg)", "",
              "## Coverage and sample construction", "",
              f"The saved windows table contains {len(windows):,} product × date × timeframe × anchor/window views. "
              f"The pinned publication includes {windows[['product','session_date']].drop_duplicates().shape[0]:,} "
              "eligible product-days. Its retrospective eligibility audit excludes incomplete product-days; "
              "this cannot be used as an entry-time filter. `tables/eligibility.csv` has year-by-year candidate, "
              "included, excluded, and overlapping reason counts. See `tables/cycles.csv` for mature windows, "
              "already-away/fresh departures, no-departure windows, unqualified first touches, gaps, and cycles.", "",
              f"Source reconciliation verified {checked_bars:,} published feature bars and {checked_refs:,} "
              "evaluable event reference opens against the pinned unadjusted one-minute data. "
              "The source audit also checked exclusive-close availability and adjustment constancy by session.", "",
              "## Exact setup definitions", "",
              "See `protocol-1.0.0.md`. Features are known at exclusive bar close; paths begin at the following "
              "unadjusted one-minute open as an idealized observation, not a guaranteed fill. "
              "B is the first close at least 1σ and four ticks away in each view. "
              "A uses the first published close exit outside 2σ per rearmed excursion. C requires a meaningful "
              "departure, ten elapsed minutes of completed same-side closes, and the first causal VWAP-zone touch. "
              "No C touch-bar extreme counts as post-signal movement.", "",
              "## Frequency and denominators", "",
              "`tables/scorecards.csv`, `tables/breakdowns.csv`, and `tables/cycles.csv` give event, evaluable, "
              "eligible-window, mature-window, departure-window, and distinct-session denominators. "
              "`tables/departure_classes.csv` separates already-away and fresh B departures. "
              "`tables/window_populations.csv` retains no-departure windows by product, year, split, timeframe, "
              "anchor, and observation window. "
              "`tables/exclusions.csv` counts zero-follow-up, discontinuity, late, and already-at-target cases; "
              "the event evidence retains their individual flags.", "",
              f"Meaningful first departures occurred in {int(cards[(cards.strategy == 'B') & (cards['product'] == 'ALL')].iloc[0].departure_windows):,} "
              f"of {len(windows):,} eligible views; these views share dates and price paths. "
              "The remaining views had no qualifying departure.", "",
              "## Return time and movement", "",
              "`tables/horizons.csv` shows 10/30/60-minute return or barrier curves, signed movement, and "
              "full-horizon MFE/MAE; it also provides a common 60-minute-capable cohort. "
              "B nonreturners remain in window-end denominators and are censored in time-to-return summaries. "
              "Departures already at the frozen target on the reference open remain visible and receive no fresh-return credit. "
              "`tables/return_survival.csv` retains returners and censored nonreturners in descriptive survival curves; "
              "interpreting those curves as population return times would require independent administrative censoring "
              "conditional on departure time and other context, which this study does not establish. "
              "Conditional median return time among successes is not an expected waiting time for all departures. "
              "Saved event times are zero-based one-minute bar offsets; intraminute contact times are unknown. "
              "Frozen and evolving VWAP contacts are independent observations; saved events include actual price "
              "retracement and VWAP movement. Pre-return adverse extension has lower/upper bounds because "
              "the order of extremes inside the one-minute contact bar is unknown.", "",
              f"For B, {int(cards[(cards.strategy == 'B') & (cards['product'] == 'ALL')].iloc[0].h30_frozen_returns):,} "
              f"of {int(cards[(cards.strategy == 'B') & (cards['product'] == 'ALL')].iloc[0].h30_n):,} "
              "30-minute-capable departures returned to frozen VWAP within 30 minutes; "
              f"{int(cards[(cards.strategy == 'B') & (cards['product'] == 'ALL')].iloc[0].evolving_returns):,} "
              "had evolving-VWAP contact by window end. The median observed wait among frozen returners "
              f"was {_fmt(cards[(cards.strategy == 'B') & (cards['product'] == 'ALL')].iloc[0].conditional_return_median_minutes)} minutes. "
              "Globex full-session outcomes allow much longer follow-up than local-window outcomes, so the "
              "window-end return rate is strongly horizon dependent.", "",
              "## Favorable, adverse, timeout, and ambiguous outcomes", "",
              "A and C use equal 0.5σ barriers rounded up to whole ticks. The four outcomes are exhaustive among "
              "evaluable events. Ambiguity remains in the denominator, with optimistic success bounds reported. "
              "An open beyond a barrier is flagged as an open-gap first passage. "
              "Full-horizon excursions can occur after the first barrier and should not be read as capturable under "
              "a stopped policy. `tables/paths.csv` contrasts full-horizon and pre-barrier excursions plus "
              "window-end outcomes. `tables/sensitivity.csv` contains the one-at-a-time barrier and fixed-tick grids; "
              "`tables/threshold_times.csv` records descriptive full-window movement-threshold times without a stop; "
              "`tables/warmup_sensitivity.csv` compares the 20-, 30-, and 40-minute full reruns.", "",
              "A and C both have more adverse-first than favorable-first outcomes at the primary barrier. "
              "For C, the approach-side close confirmation subset is in `tables/subsets.csv`; "
              "it does not replace the all-touch primary population. The warm-up and barrier grids are "
              "sensitivity descriptions, not optimized settings.", "",
              "## Baseline comparisons", ""]
    for row in controls[(controls["product"] == "ALL") &
                        (controls.barrier_definition == "half_sigma")].itertuples(index=False):
        ci = (f"; shared-date bootstrap interval {_fmt(row.ci_low_conditional_overlap, True)}–"
              f"{_fmt(row.ci_high_conditional_overlap, True)}" if pd.notna(row.ci_low_conditional_overlap) else "")
        lines.append(f"- {row.split} — {row.treated} versus {row.control}: {row.matched_treated if pd.notna(row.matched_treated) else 'unmatched'} "
                     f"matched treated events; observed difference {_fmt(row.difference, True)}{ci}. "
                     f"{row.claim_status}.")
    lines += ["", "Matching bins for hour, anchor age, and sigma are learned from development data. "
              "The A extreme and 1–2σ controls have disjoint distance support by design; remaining distance "
              "differences, unmatched counts, and a common fixed 8-tick barrier comparison are in "
              "`tables/baselines.csv`. These observational contrasts "
              "have session bootstrap intervals conditional on the observed matching overlap and weights. "
              "They do not establish a familywise-adjusted advantage.", "",
              "The pooled A half-sigma contrast is small and its 2024 and final-period intervals include zero. "
              "With a common fixed 8-tick barrier, A trails its control in the final period. "
              "C has no stable advantage over near approaches; first C retests do not outperform later ones "
              "in the final period. Neither candidate has a demonstrated incremental edge.", "",
              "## Calendar and chronological stability", "",
              "`tables/breakdowns.csv` separates product, timeframe, anchor/window, direction, development, "
              "validation, final evaluation, and calendar year. `tables/stability.csv` aligns the three splits "
              "in one row per product/timeframe/anchor/window. Sparse and degenerate intervals are flagged. "
              "The final period is chronological, but prior unseen status is not certified. "
              "Two agreeing timeframes are correlated observations.", "",
              "Pooled view-level primary rates by period:", "",
              "| Candidate | Development | 2024 validation | 2025–2026 final |",
              "|---|---:|---:|---:|"]
    period_rows = breaks[breaks.breakdown == "product+timeframe+anchor+window+split"]
    for strategy in ("B", "A", "C"):
        rates = []
        for period in ("development", "validation", "final"):
            part = period_rows[(period_rows.strategy == strategy) & (period_rows.split == period)]
            rates.append(_fmt(part.successes.sum() / part.evaluable.sum(), True))
        lines.append(f"| {LABELS[strategy]} | {' | '.join(rates)} |")
    lines += ["",
              "## Representative examples", "",
              "`tables/examples.csv` selects the earliest timestamp in each product × candidate × outcome class. "
              "Each row links to the stable event ID in retained Parquet evidence. These are deterministic "
              "illustrations, not hand-picked successes.", "",
              "| Product | Candidate | Class | Signal (UTC) | Event ID |",
              "|---|---|---|---|---|"]
    for _, example in samples.sort_values(["product", "strategy", "class"]).iterrows():
        lines.append(f"| {example['product']} | {example['strategy']} | {example['class']} | "
                     f"{example['signal_ts']} | `{example['event_id']}` |")
    lines += ["",
              "## Limitations and research advice", "",
              "No net trading conclusion follows from a return rate or movement barrier rate. "
              "Execution research still needs order type, spread/slippage, commission, latency, position size, "
              "overlap handling, and fill behavior at gaps and touched levels. Broad segment grids and controls "
              "are exploratory. The eligibility audit selects complete days retrospectively. "
              "See `advice.md` for candidate-specific dated interpretation.", "",
              "## Reproduce", "",
              "From the workspace root with the locked environment installed, choose a new unique ID and run "
              "`.venv/bin/python studies/05_session_vwap/run.py --run-id <id> --workers 3`, "
              "`.venv/bin/python studies/05_session_vwap/enrich.py --run-id <id> --workers 3`, "
              "`.venv/bin/python studies/05_session_vwap/audit.py --run-id <id>`, and "
              "`.venv/bin/python studies/05_session_vwap/summarize.py --run-id <id>`. "
              "Reproduce warm-up sensitivities with fresh IDs and `--warmup 20` or `--warmup 40`, then run "
              "`warmup_sensitivity.py` with those IDs. Review checks before sealing; never reuse a completed ID. "
              "The manifest records exact code and input hashes.", "",
              "## Saved evidence", "",
              "[Scorecards](tables/scorecards.csv) · [All tables](tables/) · "
              "[Metrics](metrics.json) · [Event evidence manifest](events.manifest.json) · "
              "[Input verification](input-verification.json) · [Source audit](source-audit.json) · "
              "[Denominator audit](denominator-audit.json) · [Run manifest](manifest.json)", ""]
    markdown = "\n".join(lines)
    (stage / "report.md").write_text(markdown)
    html_parts = []
    def inline_html(value: str) -> str:
        escaped = escape(value)
        return re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                      lambda match: f"<a href='{escape(match.group(2), quote=True)}'>{match.group(1)}</a>",
                      escaped)
    in_table = False
    for line in lines:
        if line.startswith("|"):
            cells = [escape(cell.strip()) for cell in line.strip("|").split("|")]
            if all(set(cell) <= {"-", ":"} for cell in cells):
                continue
            if not in_table:
                html_parts.append("<table><thead><tr>" + "".join(f"<th>{cell}</th>" for cell in cells) + "</tr></thead><tbody>")
                in_table = True
            else:
                html_parts.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
            continue
        if in_table:
            html_parts.append("</tbody></table>")
            in_table = False
        if not line:
            continue
        if line.startswith("#"):
            level = min(3, len(line) - len(line.lstrip("#")))
            html_parts.append(f"<h{level}>{escape(line.lstrip('# '))}</h{level}>")
        elif line.startswith("!["):
            html_parts.append("<figure><img src='figures/barrier-outcomes.svg' alt='Exhaustive 30-minute barrier outcomes for A and C' width='900'></figure>")
        elif line.startswith("- "):
            html_parts.append(f"<p class='bullet'>• {inline_html(line[2:])}</p>")
        else:
            html_parts.append(f"<p>{inline_html(line)}</p>")
    if in_table:
        html_parts.append("</tbody></table>")
    body = "\n".join(html_parts)
    (stage / "report.html").write_text("<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<title>Three VWAP statistical studies</title><style>body{font:16px/1.55 system-ui;max-width:1000px;"
        "margin:3rem auto;padding:0 1.5rem;color:#16223a}p{white-space:pre-wrap}h1,h2{margin-top:2rem}"
        "table{border-collapse:collapse;width:100%}th,td{padding:.6rem;border-bottom:1px solid #ccd3de;text-align:left}"
        "th{background:#edf1f6}.bullet{margin:.3rem 0 0 1rem}img{max-width:100%}"
        "</style><main>" + body + "</main></html>\n")


def write_publication(stage: Path, cards: pd.DataFrame) -> None:
    rows = []
    for strategy in ("B", "A", "C"):
        row = cards[(cards.strategy == strategy) & (cards["product"] == "ALL")].iloc[0]
        rows.append({"candidate": LABELS[strategy], "events": int(row.events),
                     "evaluable": int(row.evaluable), "successes": int(row.successes),
                     "rate": float(row.rate) if pd.notna(row.rate) else None,
                     "sessions": int(row.sessions),
                     "ciLow": float(row.ci_low) if pd.notna(row.ci_low) else None,
                     "ciHigh": float(row.ci_high) if pd.notna(row.ci_high) else None})
    pub = {"schemaVersion": "1.0", "id": f"vwap-three-{stage.name.lower().replace('_','-')}",
           "title": "Three session VWAP statistical studies",
           "summary": "Price-path outcomes for return after departure, first outside-2σ fades, and first VWAP retest bounces.",
           "publishedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "source": {"producer": "sahadeva", "runId": stage.name},
           "sections": [{"id": "scorecard", "title": "Three-candidate scorecard", "kind": "table",
                         "columns": [{"key": "candidate", "label": "Candidate"},
                                     {"key": "events", "label": "Events"},
                                     {"key": "evaluable", "label": "Evaluable"},
                                     {"key": "sessions", "label": "Product-sessions"},
                                     {"key": "successes", "label": "Primary successes"},
                                     {"key": "rate", "label": "Primary rate", "format": "percent"},
                                     {"key": "ciLow", "label": "95% low", "format": "percent"},
                                     {"key": "ciHigh", "label": "95% high", "format": "percent"}],
                         "rows": rows},
                        {"id": "barrier-outcomes", "title": "A/C barrier outcomes", "kind": "figure",
                         "path": "figures/barrier-outcomes.png",
                         "alt": "Two stacked bars: first outside-2-sigma fade above, first VWAP retest bounce below. Green is favorable first, coral adverse first, gray neither, purple ambiguous.",
                         "caption": "Top: A fade. Bottom: C bounce. Green favorable first; coral adverse first; gray neither; purple ordering ambiguous. Each bar uses its own evaluable-event denominator."},
                        {"id": "scope", "title": "Scope and limits", "kind": "text",
                         "body": "Seven correlated anchor/window views on ES, NQ, and GC at 2m and 5m. These are statistical price paths, not net trading profits. See the saved report and tables for denominators, uncertainty, baselines, and exclusions."}],
           "notes": ["95% intervals resample shared session dates; anchor and timeframe views are correlated.",
                     "Local publication source only; hosted publication requires separate authorization."]}
    (stage / "publication.json").write_text(json.dumps(pub, indent=2) + "\n")


def write_all(stage: Path) -> None:
    events, windows = read_evidence(stage)
    (stage / "tables").mkdir(exist_ok=True)
    cards = scorecards(events, windows)
    breaks = breakdown(events, windows)
    stability = stability_table(breaks)
    horizons = horizon_table(events)
    landmarks = landmark_table(events)
    survival = return_survival(events)
    subsets = subset_table(events)
    paths = path_table(events)
    cycles = cycle_table(windows)
    departure_classes = departure_class_table(events)
    window_populations = window_population_table(windows)
    controls = baseline(events)
    samples = examples(events)
    sensitivities = sensitivity(events)
    eligibility = eligibility_table(load_workspace_paths(stage.parents[2]).publication_root)
    thresholds = threshold_times(events)
    exclusions = exclusion_table(events)
    tables = {"scorecards": cards, "breakdowns": breaks, "stability": stability,
              "horizons": horizons,
              "landmarks": landmarks, "return_survival": survival,
              "subsets": subsets, "paths": paths,
              "cycles": cycles, "departure_classes": departure_classes,
              "window_populations": window_populations,
              "baselines": controls, "examples": samples,
              "sensitivity": sensitivities, "eligibility": eligibility,
              "threshold_times": thresholds}
    tables["exclusions"] = exclusions
    for name, table in tables.items():
        table.to_csv(stage / "tables" / f"{name}.csv", index=False)
    write_figure(stage, cards)
    metrics = []
    for row in cards.itertuples(index=False):
        metrics.append({"id": f"{row.strategy.lower()}.{row.product.lower()}.primary",
                        "strategy": row.strategy, "product": row.product, "cohort": "evaluable",
                        "horizon": "window_end" if row.strategy == "B" else "30_minutes",
                        "unit": "probability", "numerator": int(row.successes),
                        "denominator": int(row.evaluable),
                        "estimate": float(row.rate) if pd.notna(row.rate) else None,
                        "ci_95": [float(row.ci_low) if pd.notna(row.ci_low) else None,
                                  float(row.ci_high) if pd.notna(row.ci_high) else None],
                        "uncertainty_unit": "shared_session_date"})
    (stage / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n")
    write_report(stage, cards, breaks, horizons, cycles, controls, samples, events, windows)
    write_publication(stage, cards)
    (stage / "events.manifest.json").write_text(json.dumps({
        "location": "events/", "format": "Parquet", "retention": "included_in_sealed_run",
        "row_count": len(events), "window_row_count": len(windows),
        "event_schema": {name: str(dtype) for name, dtype in events.dtypes.items()},
        "window_schema": {name: str(dtype) for name, dtype in windows.dtypes.items()},
        "partitions": [{"path": str(path.relative_to(stage)), "sha256": sha256(path.read_bytes()).hexdigest()}
                       for path in sorted((stage / "events").glob("*.parquet"))]}, indent=2) + "\n")
