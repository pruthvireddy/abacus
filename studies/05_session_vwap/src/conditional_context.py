"""Causal context for the second, exploratory A/C VWAP run."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import math

import numpy as np
import pandas as pd

from abacus_bhishma.feature_loader import load_session_anchored_vwap

from .engine import (FEATURE_COLUMNS, PRODUCTS, YEARS, SCALE, barrier_outcome,
                     load_source_year, price, view_indices)

REENTRY_COLUMNS = [f"{anchor}_reenter_from_{side}_2sigma"
                   for anchor in ("globex", "asia", "london", "ny")
                   for side in ("above", "below")]
EVENT_COLUMNS = ["event_id", "strategy", "product", "session_date", "year", "split",
                 "timeframe", "anchor", "window", "feature_index", "signal_ts",
                 "signal_bar_open", "instrument_id", "raw_symbol", "adjustment",
                 "tick", "vwap", "sigma", "side", "direction", "distance_sigma",
                 "distance_ticks", "anchor_age_minutes", "departure_feature_index",
                 "reference_price", "exclusion", "h30_evaluable", "h30_barrier_0p5",
                 "h30_barrier_8ticks", "h30_barrier_0p5_ticks",
                 "h30_pre_barrier_mfe_ticks", "h30_pre_barrier_mae_ticks",
                 "already_passed_3sigma", "hit_3sigma_pre_return_lower",
                 "hit_3sigma_pre_return_upper", "touch_close_class", "confirmation",
                 "source_reference_audited"]


def window_start(session_date: str, window: str) -> pd.Timestamp:
    day = pd.Timestamp(session_date)
    if window == "globex":
        local = day - pd.Timedelta(days=1) + pd.Timedelta(hours=18)
    elif window == "asia":
        local = day - pd.Timedelta(days=1) + pd.Timedelta(hours=20)
    elif window == "london":
        local = day + pd.Timedelta(hours=3)
    elif window == "ny":
        local = day + pd.Timedelta(hours=9, minutes=30)
    else:
        raise ValueError(window)
    return local.tz_localize("America/New_York").tz_convert("UTC")


def clock_bin(minutes: int) -> str:
    if minutes < 0:
        raise ValueError("signal precedes observation window")
    if minutes < 30:
        return "00-29"
    if minutes < 60:
        return "30-59"
    if minutes < 120:
        return "60-119"
    return "120+"


def prior_atr14(daily: pd.DataFrame) -> pd.Series:
    """Daily high/low/close are adjusted prices; never include the signal day."""
    high, low, close = daily.high * SCALE, daily.low * SCALE, daily.close * SCALE
    previous_close = close.shift(1)
    tr = pd.concat([high - low, (high - previous_close).abs(),
                    (low - previous_close).abs()], axis=1).max(axis=1)
    return tr.rolling(14, min_periods=14).mean().shift(1)


def build_daily_context(root: Path) -> tuple[pd.DataFrame, dict]:
    """ATR14 uses only adjusted feature days completed before the signal day."""
    output = []
    cutoffs = {}
    for product in PRODUCTS:
        days = []
        for year in YEARS[product]:
            table = load_session_anchored_vwap(root, product, "2m", version="1.0.0",
                start_date=f"{year}-01-01", end_date=f"{year + 1}-01-01",
                columns=["session_date", "high", "low", "close"])
            frame = table.to_pandas()
            if frame.empty:
                continue
            grouped = frame.groupby("session_date", sort=True).agg(
                high=("high", "max"), low=("low", "min"), close=("close", "last"))
            days.append(grouped)
        daily = pd.concat(days).sort_index()
        if daily.index.duplicated().any():
            raise ValueError(f"duplicate daily feature date: {product}")
        daily["atr14_prior"] = prior_atr14(daily)
        daily["product"] = product
        daily["session_date"] = daily.index.astype(str)
        eligible_dev = daily[(daily.index.map(lambda day: day.year <= 2023)) &
                             daily.atr14_prior.notna()].atr14_prior
        if eligible_dev.empty:
            raise ValueError(f"no development ATR: {product}")
        q1, q2 = eligible_dev.quantile([1 / 3, 2 / 3]).tolist()
        cutoffs[product] = {"low_max": float(q1), "middle_max": float(q2)}
        daily["atr_regime"] = np.select(
            [daily.atr14_prior.isna(), daily.atr14_prior <= q1,
             daily.atr14_prior <= q2],
            ["unavailable", "low", "middle"], default="high")
        output.append(daily[["product", "session_date", "atr14_prior", "atr_regime"]])
    return pd.concat(output, ignore_index=True), cutoffs


def opening_balance(source: pd.DataFrame, start: pd.Timestamp) -> tuple[float, float] | None:
    offset = int(source.ts_event.searchsorted(start))
    part = source.iloc[offset:offset + 30]
    if len(part) != 30 or part.ts_event.iloc[0] != start or (
        part.ts_event.iloc[-1] != start + pd.Timedelta(minutes=29)):
        return None
    return price(part.high.max()), price(part.low.min())


def c_pre_touch(frame: pd.DataFrame, event: pd.Series) -> dict:
    i, dep = int(event.feature_index), int(event.departure_feature_index)
    if dep < 0 or dep >= i:
        raise ValueError(f"invalid C departure link {event.event_id}")
    anchor, side = event.anchor, int(event.side)
    part = frame.iloc[dep:i]
    if part.empty or part.raw_symbol.nunique() != 1 or part.raw_symbol.iloc[0] != event.raw_symbol:
        raise ValueError(f"pre-touch contract mismatch {event.event_id}")
    if not (part[f"{anchor}_anchor_active"] == True).all():
        raise ValueError(f"inactive pre-touch anchor {event.event_id}")
    sigma = part[f"{anchor}_sigma"].to_numpy(dtype=float)
    if not np.isfinite(sigma).all() or (sigma <= 0).any():
        raise ValueError(f"invalid pre-touch sigma {event.event_id}")
    z = side * ((part.close.to_numpy(dtype=float) * SCALE -
                 part[f"{anchor}_vwap"].to_numpy(dtype=float)) / sigma)
    peak_offset = int(np.argmax(z))
    peak_row = part.iloc[peak_offset]
    dep_row = part.iloc[0]
    dep_vwap = float(dep_row[f"{anchor}_vwap"])
    dep_sigma = float(dep_row[f"{anchor}_sigma"])
    outward = part.high.max() if side > 0 else part.low.min()
    peak_frozen_extreme = max(0.0, side * (price(outward) - dep_vwap) / dep_sigma)
    touch_open = frame.iloc[i].ts_event
    peak_to_touch = int((touch_open - peak_row.available_at).total_seconds() // 60)
    dep_to_touch = int((touch_open - dep_row.available_at).total_seconds() // 60)
    last_z = float(z[-1])
    return {
        "c_departure_strength_sigma": float(z[0]),
        "c_peak_close_sigma": float(z[peak_offset]),
        "c_peak_frozen_extreme_sigma": float(peak_frozen_extreme),
        "c_departure_to_touch_minutes": dep_to_touch,
        "c_peak_to_touch_minutes": peak_to_touch,
        "c_away_closes_1sigma": int((z >= 1).sum()),
        "c_last_pre_touch_distance_sigma": last_z,
        "c_approach_speed_sigma_per_minute": (
            max(0.0, float(z[peak_offset] - last_z)) / peak_to_touch
            if peak_to_touch > 0 else None),
    }


def a_pre_exit(frame: pd.DataFrame, event: pd.Series, start: pd.Timestamp) -> dict:
    i, anchor, side = int(event.feature_index), event.anchor, int(event.side)
    row = frame.iloc[i]
    high, low, close = [price(row[name]) for name in ("high", "low", "close")]
    outward_close_location = ((close - low) / (high - low) if side > 0 else
                              (high - close) / (high - low)) if high > low else None
    result = {"a_exit_strength_sigma": float(event.distance_sigma),
              "a_excess_2sigma_ticks": max(0.0, (event.distance_sigma - 2) * event.sigma / event.tick),
              "a_outward_close_location": outward_close_location}
    lookback = 30 // int(event.timeframe[:-1])
    earlier = i - lookback
    if earlier >= 0:
        prior = frame.iloc[earlier]
        if (prior[f"{anchor}_anchor_active"] == True and
            prior.available_at == row.available_at - pd.Timedelta(minutes=30) and
            prior.raw_symbol == row.raw_symbol and
            pd.notna(prior[f"{anchor}_vwap"])):
            result["a_prior30_trend_sigma"] = side * (price(row.close) - price(prior.close)) / event.sigma
            result["a_prior30_vwap_slope_sigma"] = side * (
                float(row[f"{anchor}_vwap"]) - float(prior[f"{anchor}_vwap"])) / event.sigma
            prior_sigma = float(prior[f"{anchor}_sigma"])
            result["a_prior30_sigma_ratio"] = event.sigma / prior_sigma if prior_sigma > 0 else None
    for j in range(i - 1, -1, -1):
        prior = frame.iloc[j]
        if prior.available_at < start or prior.raw_symbol != row.raw_symbol:
            break
        sigma = prior[f"{anchor}_sigma"]
        if pd.notna(sigma) and sigma > 0 and abs(price(prior.close) - prior[f"{anchor}_vwap"]) <= .25 * sigma:
            result["a_minutes_since_near_vwap"] = int((row.available_at - prior.available_at).total_seconds() // 60)
            break
    return result


def reentry_for_a(frame: pd.DataFrame, source: pd.DataFrame, event: pd.Series,
                  window_end: pd.Timestamp) -> dict:
    i, side, anchor = int(event.feature_index), int(event.side), event.anchor
    flag = f"{anchor}_reenter_from_{'above' if side > 0 else 'below'}_2sigma"
    result = {"original_event_id": event.event_id, "product": event["product"],
              "session_date": event.session_date, "year": int(event.year),
              "split": event.split, "timeframe": event.timeframe,
              "anchor": anchor, "window": event.window,
              "original_signal_ts": event.signal_ts, "original_h30_evaluable": event.h30_evaluable,
              "original_h30_barrier_0p5": event.h30_barrier_0p5,
              "confirmed": False, "status": "no_reentry"}
    for j in range(i + 1, len(frame)):
        row = frame.iloc[j]
        if row.available_at > window_end or (
            event.window != "globex" and not bool(row[f"is_{event.window}_session"])):
            break
        if row.raw_symbol != event.raw_symbol:
            result["status"] = "contract_change"
            break
        observed = row[flag]
        if pd.notna(observed) and bool(observed):
            result["confirmed"] = True
            result["status"] = "confirmed"
            result["reentry_signal_ts"] = row.available_at.isoformat()
            result["reentry_feature_index"] = j
            result["minutes_to_reentry"] = int((row.available_at - pd.Timestamp(event.signal_ts)).total_seconds() // 60)
            result["reentry_sigma"] = float(row[f"{anchor}_sigma"])
            result["reentry_vwap"] = float(row[f"{anchor}_vwap"]) - price(row.price_adjustment)
            offset = int(source.ts_event.searchsorted(row.available_at))
            followup = int((window_end - row.available_at).total_seconds() // 60)
            if offset >= len(source) or source.ts_event.iloc[offset] != row.available_at:
                result["status"] = "missing_reference"
                break
            reference = source.iloc[offset]
            if reference.raw_symbol != row.raw_symbol:
                result["status"] = "contract_change"
                break
            ref = price(reference.open)
            result["reference_price"] = ref
            result["remaining_to_vwap_ticks"] = int(event.direction) * (result["reentry_vwap"] - ref) / event.tick
            result["already_past_vwap"] = result["remaining_to_vwap_ticks"] <= 1
            if followup < 30:
                result["status"] = "late_for_30m"
                break
            path = source.iloc[offset:offset + 30]
            if len(path) != 30 or path.ts_event.iloc[-1] != row.available_at + pd.Timedelta(minutes=29) or (
                path.raw_symbol != row.raw_symbol).any():
                result["status"] = "source_discontinuity"
                break
            tick = float(event.tick)
            size = max(1, math.ceil(.5 * result["reentry_sigma"] / tick - 1e-10)) * tick
            result["h30_barrier_0p5"] = barrier_outcome(path, ref, int(event.direction), size)["barrier"]
            result["h30_barrier_8ticks"] = barrier_outcome(path, ref, int(event.direction), 8 * tick)["barrier"]
            result["status"] = "evaluable"
            break
        z = side * (price(row.close) - float(row[f"{anchor}_vwap"]))
        if z <= 2 * row[f"{anchor}_sigma"] + 1e-8:
            result["status"] = "inside_without_true_flag"
            break
    return result


def context_year(root: Path, parent: Path, product: str, year: int,
                 daily_file: Path, output: Path) -> dict:
    path = parent / "events" / f"events_{product}_{year}.parquet"
    original = pd.read_parquet(path)
    selected = original[original.strategy.isin(["A", "C", "A_control", "C_near"])].copy()
    daily = pd.read_parquet(daily_file)
    daily = daily[daily["product"] == product].set_index("session_date")
    source_year = load_source_year(root, product, year)
    source_by_day = {str(day): group.reset_index(drop=True)
                     for day, group in source_year.groupby("session_date", sort=False)}
    features = {}
    for timeframe in ("2m", "5m"):
        table = load_session_anchored_vwap(root, product, timeframe, version="1.0.0",
            start_date=f"{year}-01-01", end_date=f"{year + 1}-01-01",
            columns=FEATURE_COLUMNS + REENTRY_COLUMNS)
        features[timeframe] = {str(day): group.reset_index(drop=True)
                               for day, group in table.to_pandas().groupby("session_date", sort=False)}
    rows, reentries = [], []
    for (timeframe, day), group in selected.groupby(["timeframe", "session_date"], sort=False):
        frame = features[timeframe].get(day)
        source = source_by_day.get(day)
        if frame is None or source is None or day not in daily.index:
            raise ValueError(f"missing context source {product} {day} {timeframe}")
        balance = {window: opening_balance(source, window_start(day, window))
                   for window in ("globex", "asia", "london", "ny")}
        window_ends = {window: frame.iloc[view_indices(frame, window)[-1]].bar_close_ts
                       for window in ("globex", "asia", "london", "ny")}
        for _, event in group.iterrows():
            i = int(event.feature_index)
            row = frame.iloc[i]
            signal = pd.Timestamp(event.signal_ts)
            if (row.available_at != signal or row.raw_symbol != event.raw_symbol or
                not math.isclose(price(row.price_adjustment), event.adjustment, abs_tol=1e-8)):
                raise ValueError(f"parent event feature mismatch {event.event_id}")
            start = window_start(day, event.window)
            elapsed = int((signal - start).total_seconds() // 60)
            item = {name: event[name] for name in EVENT_COLUMNS}
            item["ordinal"] = int(event.event_id.rsplit(":", 1)[-1])
            item["window_age_minutes"] = elapsed
            item["window_clock_bin"] = clock_bin(elapsed)
            item["first_hour"] = elapsed < 60
            item["atr14_prior"] = daily.loc[day, "atr14_prior"]
            item["atr_regime"] = daily.loc[day, "atr_regime"]
            ob = balance[event.window]
            if ob is not None and signal >= start + pd.Timedelta(minutes=30):
                ob_high, ob_low = ob
                unadjusted_close = price(row.close - row.price_adjustment)
                item["opening_balance_high"] = ob_high
                item["opening_balance_low"] = ob_low
                item["opening_balance_width_points"] = ob_high - ob_low
                item["opening_balance_width_atr"] = ((ob_high - ob_low) / item["atr14_prior"]
                    if pd.notna(item["atr14_prior"]) and item["atr14_prior"] > 0 else None)
                item["opening_balance_location"] = (
                    "above" if unadjusted_close > ob_high + 1e-8 else
                    "below" if unadjusted_close < ob_low - 1e-8 else "inside")
            else:
                item["opening_balance_location"] = "unavailable"
            if event.window != "globex" and bool(row[f"{event.window}_anchor_active"]):
                local_vwap = row[f"{event.window}_vwap"]
                globex_vwap = row.globex_vwap
                local_sigma = row[f"{event.window}_sigma"]
                if pd.notna(local_vwap) and pd.notna(globex_vwap) and pd.notna(local_sigma) and local_sigma > 0:
                    close = price(row.close)
                    item["local_globex_separation_sigma"] = abs(local_vwap - globex_vwap) / local_sigma
                    item["vwap_geometry"] = (
                        "above_both" if close > max(local_vwap, globex_vwap) else
                        "below_both" if close < min(local_vwap, globex_vwap) else "between")
            if "vwap_geometry" not in item:
                item["vwap_geometry"] = "unavailable"
            if event.strategy in ("A", "A_control"):
                item.update(a_pre_exit(frame, event, start))
                if event.strategy == "A":
                    reentries.append(reentry_for_a(frame, source, event, window_ends[event.window]))
            if event.strategy == "C":
                item.update(c_pre_touch(frame, event))
            rows.append(item)
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(output / f"context_{product}_{year}.parquet", index=False)
    pd.DataFrame(reentries).to_parquet(output / f"reentry_{product}_{year}.parquet", index=False)
    return {"product": product, "year": year, "context_rows": len(rows),
            "reentry_rows": len(reentries)}
