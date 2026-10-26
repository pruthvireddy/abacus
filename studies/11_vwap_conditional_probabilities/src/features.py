"""Past-only feature and episode construction for study 11.

This module deliberately has no one-minute future-path loader.  The feature-only
pilot may import it without gaining access to outcome data.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from abacus_bhishma.feature_loader import load_session_anchored_vwap

PRODUCTS = ("ES", "NQ", "GC")
YEARS = {"ES": range(2021, 2027), "NQ": range(2021, 2027), "GC": range(2016, 2027)}
ANCHORS = ("globex", "asia", "london", "ny")
LOCAL_ANCHORS = ("asia", "london", "ny")
SCALE = 1e-9
TZ = "America/New_York"

BASE_COLUMNS = [
    "ts_event", "bar_close_ts", "available_at", "session_date", "product",
    "timeframe", "instrument_id", "raw_symbol", "open", "high", "low",
    "close", "volume", "price_adjustment", "min_tick", "is_asia_session",
    "is_london_session", "is_ny_session",
]
COLUMNS = list(BASE_COLUMNS)
for _anchor in ANCHORS:
    COLUMNS.extend(
        f"{_anchor}_{suffix}"
        for suffix in (
            "anchor_ts", "anchor_active", "vwap", "sigma",
            "minutes_since_anchor", "cross_above_vwap", "cross_below_vwap",
        )
    )


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_pins(root: Path, lock: dict) -> list[dict]:
    records = [lock["release_manifest"], *lock["datasets"],
               *lock["related_manifests"], lock["audit"]]
    checks: list[dict] = []
    for record in records:
        relative = record.get("path", record.get("manifest_path"))
        expected = record.get("sha256", record.get("manifest_sha256"))
        actual = digest(root / relative)
        if actual != expected:
            raise ValueError(f"pinned input changed: {relative}")
        checks.append({"path": relative, "sha256": actual})
    release = json.loads((root / lock["release_manifest"]["path"]).read_text())
    if release.get("release_id") != "session_anchored_vwap__1.0.0":
        raise ValueError("release ID mismatch")
    for dataset in ("session_anchored_vwap_2m_v1",
                    "session_anchored_vwap_5m_v1",
                    "volume_lead_unadjusted_v1"):
        manifest_path = root / "catalog/datasets" / f"{dataset}.json"
        manifest = json.loads(manifest_path.read_text())
        for partition in manifest["output_files"]:
            relative = partition["path"]
            actual = digest(root / relative)
            if actual != partition["sha256"]:
                raise ValueError(f"partition changed: {relative}")
            checks.append({"path": relative, "sha256": actual})
    return checks


def load_features(root: Path, product: str, year: int, timeframe: str) -> pd.DataFrame:
    return load_session_anchored_vwap(
        root, product, timeframe, version="1.0.0",
        start_date=f"{year}-01-01", end_date=f"{year + 1}-01-01", columns=COLUMNS,
    ).to_pandas()


def side_of(price: float, reference: float, tolerance: float = 1e-8) -> int:
    return int(price > reference + tolerance) - int(price < reference - tolerance)


def round_half_up_to_tick(price: float, tick: float) -> float:
    if tick <= 0:
        raise ValueError("tick must be positive")
    return math.floor(price / tick + 0.5 + 1e-10) * tick


def reference_zone(reference: float, tick: float) -> tuple[float, float, float]:
    center = round_half_up_to_tick(reference, tick)
    return center - tick, center + tick, center


def split_label(day: date) -> str:
    return "development" if day.year <= 2023 else "validation" if day.year == 2024 else "final"


def clock_window(local: pd.Timestamp) -> str:
    minute = local.hour * 60 + local.minute
    if minute >= 18 * 60 or minute < 3 * 60:
        return "evening_asia"
    if minute < 9 * 60 + 30:
        return "london_to_ny"
    if minute < 12 * 60:
        return "ny_morning"
    return "ny_afternoon"


def explicit_clock(local: pd.Timestamp) -> str:
    minute = local.hour * 60 + local.minute
    if minute >= 18 * 60 and minute < 20 * 60:
        return "pre_asia_gap"
    if minute >= 20 * 60 or minute < 3 * 60:
        return "asia"
    if minute < 9 * 60:
        return "london"
    if minute < 9 * 60 + 30:
        return "pre_ny_gap"
    if minute < 16 * 60:
        return "ny"
    return "post_ny_gap"


def prior_atr(days: pd.DataFrame) -> dict[date, float]:
    """ATR14 from prior eligible product-sessions only."""
    daily = days.groupby("session_date", sort=True).agg(
        high=("high", "max"), low=("low", "min"), close=("close", "last")
    )
    result: dict[date, float] = {}
    true_ranges: list[float] = []
    previous_close: float | None = None
    for day, row in daily.iterrows():
        result[day] = float(np.mean(true_ranges[-14:])) if len(true_ranges) >= 14 else math.nan
        high, low, close = row.high * SCALE, row.low * SCALE, row.close * SCALE
        tr = high - low if previous_close is None else max(
            high - low, abs(high - previous_close), abs(low - previous_close)
        )
        true_ranges.append(tr)
        previous_close = close
    return result


def residence_state(sides: np.ndarray, timeframe: int) -> tuple[str, int, int, int, int, int]:
    above = int(np.sum(sides == 1))
    below = int(np.sum(sides == -1))
    equal = int(np.sum(sides == 0))
    changes = int(np.sum((sides[1:] * sides[:-1]) == -1))
    longest = run = 0
    previous = 0
    for value in sides:
        if value and value == previous:
            run += 1
        elif value:
            run = 1
        else:
            run = 0
        longest = max(longest, run)
        previous = int(value)
    current = int(sides[-1])
    if timeframe == 2:
        state = ("persistent" if current and int(np.sum(sides == current)) >= 12 and changes <= 1
                 else "rotational" if 6 <= above <= 9 and changes >= 3 else "other")
    else:
        state = ("persistent" if current and int(np.sum(sides == current)) >= 5 and changes <= 1
                 else "rotational" if 2 <= above <= 4 and changes >= 2 else "other")
    return state, above, below, equal, changes, longest


def _membership(day: pd.DataFrame, anchor: str) -> np.ndarray:
    return (np.ones(len(day), dtype=bool) if anchor == "globex"
            else day[f"is_{anchor}_session"].to_numpy(dtype=bool))


def _window_end(day: pd.DataFrame, membership: np.ndarray) -> pd.Timestamp:
    indexes = np.flatnonzero(membership)
    if not len(indexes):
        return pd.NaT
    return day.bar_close_ts.iloc[indexes[-1]]


def _past_context(day: pd.DataFrame, index: int, anchor: str, timeframe: int,
                  membership: np.ndarray, tick: float, anchor_age: float) -> dict:
    length = 30 // timeframe
    slope_start = index - length
    residence_start = index - length + 1
    unavailable = {
        "context_available": False, "residence_state": "unavailable",
        "above_count": None, "below_count": None, "equality_count": None,
        "side_changes": None, "longest_run": None, "vwap_slope_30m": None,
        "vwap_slope_side_class": "unavailable",
    }
    # The state lookback is additional to the 30-minute anchor warm-up.
    if anchor_age < 60 - 1e-9 or slope_start < 0:
        return unavailable
    interval = day.iloc[slope_start:index + 1]
    expected = pd.Timedelta(minutes=timeframe)
    if (len(interval) != length + 1 or
            not (interval.available_at.diff().iloc[1:] == expected).all() or
            not membership[slope_start:index + 1].all() or
            not interval[f"{anchor}_anchor_active"].fillna(False).all() or
            interval[f"{anchor}_anchor_ts"].nunique() != 1 or
            interval.raw_symbol.nunique() != 1 or
            interval.instrument_id.nunique() != 1 or
            interval.price_adjustment.nunique() != 1):
        return unavailable
    closes = day.close.iloc[residence_start:index + 1].to_numpy(dtype=float) * SCALE
    vwaps = day[f"{anchor}_vwap"].iloc[residence_start:index + 1].to_numpy(dtype=float)
    if not np.isfinite(vwaps).all():
        return unavailable
    sides = np.asarray([side_of(c, v) for c, v in zip(closes, vwaps)], dtype=np.int8)
    state, above, below, equal, changes, longest = residence_state(sides, timeframe)
    slope = float(day[f"{anchor}_vwap"].iloc[index] - day[f"{anchor}_vwap"].iloc[slope_start])
    current = int(sides[-1])
    signed = current * slope
    slope_class = "flat" if abs(slope) < tick - 1e-10 else "outward" if signed > 0 else "inward"
    return {
        "context_available": True, "residence_state": state,
        "above_count": above, "below_count": below, "equality_count": equal,
        "side_changes": changes, "longest_run": longest,
        "vwap_slope_30m": slope, "vwap_slope_side_class": slope_class,
    }


def extract_departure_landmarks(day: pd.DataFrame, anchor: str, timeframe: int,
                                atr: float) -> tuple[list[dict], Counter]:
    """Build fresh departure episodes and ten-minute at-risk checkpoints."""
    day = day.sort_values("available_at").reset_index(drop=True)
    membership = _membership(day, anchor)
    window_end = _window_end(day, membership)
    counts: Counter = Counter()
    rows: list[dict] = []
    if pd.isna(window_end):
        return rows, counts
    local = day.available_at.dt.tz_convert(TZ)
    close = day.close.to_numpy(dtype=float) * SCALE
    high = day.high.to_numpy(dtype=float) * SCALE
    low = day.low.to_numpy(dtype=float) * SCALE
    opening = day.open.to_numpy(dtype=float) * SCALE
    vwap = day[f"{anchor}_vwap"].to_numpy(dtype=float)
    sigma = day[f"{anchor}_sigma"].to_numpy(dtype=float)
    active = day[f"{anchor}_anchor_active"].fillna(False).to_numpy(dtype=bool)
    tick_values = day.min_tick.to_numpy(dtype=float) * SCALE
    armed = False
    saw_initial_away = False
    episode: dict | None = None
    episode_ordinal = 0

    for i in range(len(day)):
        if not membership[i] or not active[i] or not np.isfinite(vwap[i]) or not np.isfinite(sigma[i]) or sigma[i] <= 0:
            if episode is not None:
                counts["terminated_window_or_invalid"] += 1
            episode = None
            armed = False
            saw_initial_away = False
            continue
        anchor_ts = day[f"{anchor}_anchor_ts"].iloc[i]
        age = ((day.available_at.iloc[i] - anchor_ts).total_seconds() / 60
               if not pd.isna(anchor_ts) else -1)
        if age < 30:
            counts["immature_anchor_bars"] += 1
            continue
        tick = float(tick_values[i])
        threshold = max(float(sigma[i]), 4 * tick)
        current_side = side_of(close[i], vwap[i])
        beyond = current_side != 0 and abs(close[i] - vwap[i]) >= threshold - 1e-10
        terminated_this_bar = False

        if episode is not None:
            continuity = (i > 0 and membership[i - 1] and active[i - 1] and
                          day.raw_symbol.iloc[i] == episode["raw_symbol"] and
                          int(day.instrument_id.iloc[i]) == episode["instrument_id"] and
                          int(day.price_adjustment.iloc[i]) == episode["price_adjustment"] and
                          day[f"{anchor}_anchor_ts"].iloc[i] == episode["anchor_ts"])
            if not continuity or not np.isfinite(vwap[i - 1]):
                counts["terminated_contract_or_anchor"] += 1
                episode = None
                armed = False
                terminated_this_bar = True
            else:
                lower, upper, _ = reference_zone(float(vwap[i - 1]), tick)
                touched = low[i] <= upper + 1e-10 and high[i] >= lower - 1e-10
                gap = ((episode["side"] > 0 and opening[i] < lower - 1e-10 and high[i] < lower - 1e-10) or
                       (episode["side"] < 0 and opening[i] > upper + 1e-10 and low[i] > upper + 1e-10))
                if touched:
                    counts["terminated_causal_contact"] += 1
                    episode = None
                    armed = not beyond
                    terminated_this_bar = True
                elif gap:
                    counts["terminated_gap_through"] += 1
                    episode = None
                    armed = not beyond
                    terminated_this_bar = True
                elif current_side != episode["side"]:
                    counts["terminated_reference_overtake"] += 1
                    episode = None
                    armed = not beyond
                    terminated_this_bar = True
                else:
                    excursion_ticks = episode["side"] * (close[i] - vwap[i]) / tick
                    excursion_sigma = episode["side"] * (close[i] - vwap[i]) / sigma[i]
                    episode["max_excursion_ticks"] = max(episode["max_excursion_ticks"], excursion_ticks)
                    episode["max_excursion_sigma"] = max(episode["max_excursion_sigma"], excursion_sigma)
                    current_local = local.iloc[i]
                    is_checkpoint = (current_local.minute % 10 == 0 and current_local.second == 0 and
                                     day.available_at.iloc[i] > episode["departure_ts"])
                    if is_checkpoint:
                        counts["checkpoint_candidates"] += 1
                        remaining = (window_end - day.available_at.iloc[i]).total_seconds() / 60
                        if remaining < 30 - 1e-9:
                            counts["checkpoint_insufficient_horizon"] += 1
                        else:
                            context = _past_context(day, i, anchor, timeframe, membership, tick, age)
                            session_day = day.session_date.iloc[i]
                            elapsed = (day.available_at.iloc[i] - episode["departure_ts"]).total_seconds() / 60
                            event_id = (f"AB:{day['product'].iloc[i]}:{session_day}:{timeframe}m:{anchor}:"
                                        f"{episode['ordinal']}:{day.available_at.iloc[i].isoformat()}")
                            rows.append({
                                "event_id": event_id, "episode_id": episode["episode_id"],
                                "episode_ordinal": episode["ordinal"], "product": str(day["product"].iloc[i]),
                                "session_date": str(session_day), "year": int(session_day.year),
                                "split": split_label(session_day), "timeframe": f"{timeframe}m",
                                "anchor": anchor, "forecast_ts": day.available_at.iloc[i],
                                "forecast_available_at": day.available_at.iloc[i],
                                "window_end_ts": window_end, "feature_index": i,
                                "departure_ts": episode["departure_ts"], "departure_side": episode["side"],
                                "departure_vwap": episode["departure_vwap"],
                                "departure_sigma": episode["departure_sigma"],
                                "departure_distance_sigma": episode["departure_distance_sigma"],
                                "elapsed_without_return_minutes": elapsed,
                                "time_remaining_minutes": remaining, "anchor_age_minutes": age,
                                "local_time": current_local.strftime("%Y-%m-%d %H:%M%z"),
                                "clock_window": clock_window(current_local),
                                "explicit_clock": explicit_clock(current_local),
                                "side": episode["side"], "close": close[i], "vwap": vwap[i],
                                "sigma": sigma[i], "absolute_distance_ticks": abs(close[i] - vwap[i]) / tick,
                                "absolute_distance_sigma": abs(close[i] - vwap[i]) / sigma[i],
                                "max_excursion_ticks": episode["max_excursion_ticks"],
                                "max_excursion_sigma": episode["max_excursion_sigma"],
                                "prior_atr14": atr, "tick": tick,
                                "raw_symbol": str(day.raw_symbol.iloc[i]),
                                "instrument_id": int(day.instrument_id.iloc[i]),
                                "price_adjustment": int(day.price_adjustment.iloc[i]),
                                "anchor_ts": anchor_ts,
                                **context,
                            })
                            counts["eligible_checkpoints"] += 1

        if episode is None and not terminated_this_bar:
            if beyond and armed:
                episode_ordinal += 1
                session_day = day.session_date.iloc[i]
                episode_id = (f"DEP:{day['product'].iloc[i]}:{session_day}:{timeframe}m:"
                              f"{anchor}:{episode_ordinal}")
                episode = {
                    "episode_id": episode_id, "ordinal": episode_ordinal,
                    "departure_ts": day.available_at.iloc[i], "side": current_side,
                    "departure_vwap": float(vwap[i]), "departure_sigma": float(sigma[i]),
                    "departure_distance_sigma": abs(close[i] - vwap[i]) / sigma[i],
                    "max_excursion_ticks": abs(close[i] - vwap[i]) / tick,
                    "max_excursion_sigma": abs(close[i] - vwap[i]) / sigma[i],
                    "raw_symbol": str(day.raw_symbol.iloc[i]),
                    "instrument_id": int(day.instrument_id.iloc[i]),
                    "price_adjustment": int(day.price_adjustment.iloc[i]),
                    "anchor_ts": anchor_ts,
                }
                armed = False
                counts["fresh_departures"] += 1
            elif beyond:
                if not saw_initial_away:
                    counts["already_away_at_first_mature_observation"] += 1
                    saw_initial_away = True
            else:
                armed = True
    if episode is not None:
        counts["terminated_window_end"] += 1
    return rows, counts


def _corridor_past_features(day: pd.DataFrame, index: int, anchor: str,
                            timeframe: int, orientation: int, tick: float,
                            session_anchor_age: float) -> dict:
    length = 30 // timeframe
    start = index - length
    result = {
        "slope_context_available": False, "day_vwap_slope_30m": None,
        "session_vwap_slope_30m": None, "slope_agreement": "unavailable",
        "corridor_change_ticks_10m": None, "corridor_trend": "unavailable",
    }
    if session_anchor_age >= 60 - 1e-9 and start >= 0:
        interval = day.iloc[start:index + 1]
        expected = pd.Timedelta(minutes=timeframe)
        if (len(interval) == length + 1 and
                (interval.available_at.diff().iloc[1:] == expected).all() and
                interval.raw_symbol.nunique() == 1 and interval.instrument_id.nunique() == 1 and
                interval.price_adjustment.nunique() == 1 and
                interval.globex_anchor_active.fillna(False).all() and
                interval[f"{anchor}_anchor_active"].fillna(False).all() and
                interval.globex_anchor_ts.nunique() == 1 and
                interval[f"{anchor}_anchor_ts"].nunique() == 1):
            day_slope = float(day.globex_vwap.iloc[index] - day.globex_vwap.iloc[start])
            session_slope = float(day[f"{anchor}_vwap"].iloc[index] - day[f"{anchor}_vwap"].iloc[start])
            if abs(day_slope) < tick - 1e-10 or abs(session_slope) < tick - 1e-10:
                agreement = "flat"
            else:
                agreement = "agree" if day_slope * session_slope > 0 else "oppose"
            result.update(slope_context_available=True, day_vwap_slope_30m=day_slope,
                          session_vwap_slope_30m=session_slope, slope_agreement=agreement)
    lookback = 10 // timeframe
    previous = index - lookback
    if previous >= 0:
        values = [day.globex_vwap.iloc[previous], day[f"{anchor}_vwap"].iloc[previous]]
        if np.isfinite(values).all():
            prior_width = abs(values[0] - values[1])
            current_width = abs(day.globex_vwap.iloc[index] - day[f"{anchor}_vwap"].iloc[index])
            change_ticks = (current_width - prior_width) / tick
            trend = "widening" if change_ticks > 1 + 1e-10 else "narrowing" if change_ticks < -1 - 1e-10 else "stable"
            result.update(corridor_change_ticks_10m=change_ticks, corridor_trend=trend)
    return result


def extract_corridor_candidates(day: pd.DataFrame, anchor: str, timeframe: int,
                                atr: float) -> tuple[list[dict], Counter]:
    """Build all base crossing candidates; outcome-independent lockout is applied later."""
    day = day.sort_values("available_at").reset_index(drop=True)
    membership = _membership(day, anchor)
    window_end = _window_end(day, membership)
    rows: list[dict] = []
    counts: Counter = Counter()
    if pd.isna(window_end):
        return rows, counts
    local = day.available_at.dt.tz_convert(TZ)
    close = day.close.to_numpy(dtype=float) * SCALE
    tick_values = day.min_tick.to_numpy(dtype=float) * SCALE
    for i in np.flatnonzero(membership):
        counts["membership_bars"] += 1
        if i == 0:
            continue
        t = day.available_at.iloc[i]
        tick = float(tick_values[i])
        active = bool(day.globex_anchor_active.iloc[i]) and bool(day[f"{anchor}_anchor_active"].iloc[i])
        refs = (day.globex_vwap.iloc[i], day[f"{anchor}_vwap"].iloc[i],
                day.globex_sigma.iloc[i], day[f"{anchor}_sigma"].iloc[i])
        if not active or not np.isfinite(refs).all() or refs[2] <= 0 or refs[3] <= 0:
            counts["invalid_references"] += 1
            continue
        day_age = (t - day.globex_anchor_ts.iloc[i]).total_seconds() / 60
        session_age = (t - day[f"{anchor}_anchor_ts"].iloc[i]).total_seconds() / 60
        down_value = day[f"{anchor}_cross_below_vwap"].iloc[i]
        up_value = day[f"{anchor}_cross_above_vwap"].iloc[i]
        crossed_down = False if pd.isna(down_value) else bool(down_value)
        crossed_up = False if pd.isna(up_value) else bool(up_value)
        if not (crossed_down or crossed_up):
            continue
        counts["published_crosses"] += 1
        if day_age < 30 or session_age < 30:
            counts["immature_crosses"] += 1
            continue
        remaining = (window_end - t).total_seconds() / 60
        if remaining < 30 - 1e-9:
            counts["insufficient_horizon"] += 1
            continue
        if (day.raw_symbol.iloc[i] != day.raw_symbol.iloc[i - 1] or
                day.instrument_id.iloc[i] != day.instrument_id.iloc[i - 1] or
                day.price_adjustment.iloc[i] != day.price_adjustment.iloc[i - 1]):
            counts["contract_discontinuity"] += 1
            continue
        day_vwap = float(refs[0])
        session_vwap = float(refs[1])
        day_low, day_high, day_center = reference_zone(day_vwap, tick)
        session_low, session_high, session_center = reference_zone(session_vwap, tick)
        price = float(close[i])
        orientation = 0
        if session_center > day_center and crossed_down and price < session_low - 1e-10 and price > day_high + 1e-10:
            orientation = -1  # lost session from above; day target is below.
        elif day_center > session_center and crossed_up and price > session_high + 1e-10 and price < day_low - 1e-10:
            orientation = 1  # lost session from below; day target is above.
        if orientation == 0:
            counts["not_between_or_target_overlap"] += 1
            continue
        corridor_width = abs(day_center - session_center)
        width_ticks = corridor_width / tick
        width_day_sigma = corridor_width / float(refs[2])
        distance_to_day = abs(price - day_center)
        distance_to_session = abs(price - session_center)
        position_from_day = distance_to_day / corridor_width if corridor_width else math.nan
        lost_side = 1 if orientation < 0 else -1
        hold_bars = 0
        j = i - 1
        while j >= 0 and membership[j] and bool(day[f"{anchor}_anchor_active"].iloc[j]):
            prior_vwap = day[f"{anchor}_vwap"].iloc[j]
            if not np.isfinite(prior_vwap) or side_of(day.close.iloc[j] * SCALE, prior_vwap) != lost_side:
                break
            hold_bars += 1
            j -= 1
        session_day = day.session_date.iloc[i]
        current_local = local.iloc[i]
        context = _corridor_past_features(
            day, i, anchor, timeframe, orientation, tick, session_age
        )
        rows.append({
            "candidate_id": (f"C0:{day['product'].iloc[i]}:{session_day}:{timeframe}m:"
                             f"{anchor}:{t.isoformat()}"),
            "product": str(day["product"].iloc[i]), "session_date": str(session_day),
            "year": int(session_day.year), "split": split_label(session_day),
            "timeframe": f"{timeframe}m", "session_anchor": anchor,
            "forecast_ts": t, "forecast_available_at": t, "window_end_ts": window_end,
            "feature_index": i, "local_time": current_local.strftime("%Y-%m-%d %H:%M%z"),
            "clock_window": clock_window(current_local), "orientation": orientation,
            "day_below_session": day_center < session_center, "close": price,
            "day_vwap": day_vwap, "session_vwap": session_vwap,
            "day_target": day_center, "session_target": session_center,
            "day_zone_low": day_low, "day_zone_high": day_high,
            "session_zone_low": session_low, "session_zone_high": session_high,
            "day_sigma": float(refs[2]), "session_sigma": float(refs[3]),
            "corridor_width_points": corridor_width, "corridor_width_ticks": width_ticks,
            "corridor_width_day_sigma": width_day_sigma,
            "corridor_width_prior_atr": corridor_width / atr if math.isfinite(atr) and atr > 0 else math.nan,
            "distance_to_day_points": distance_to_day, "distance_to_day_ticks": distance_to_day / tick,
            "distance_to_session_points": distance_to_session,
            "distance_to_session_ticks": distance_to_session / tick,
            "position_from_day": position_from_day, "prior_hold_minutes": hold_bars * timeframe,
            "time_remaining_minutes": remaining, "day_anchor_age_minutes": day_age,
            "session_anchor_age_minutes": session_age, "prior_atr14": atr, "tick": tick,
            "raw_symbol": str(day.raw_symbol.iloc[i]),
            "instrument_id": int(day.instrument_id.iloc[i]),
            "price_adjustment": int(day.price_adjustment.iloc[i]),
            **context,
        })
        counts["base_candidates"] += 1
    return rows, counts


def select_corridor_events(candidates: pd.DataFrame, min_ticks: float,
                           min_day_sigma: float, lockout_minutes: int = 30) -> tuple[pd.DataFrame, int]:
    """Apply a past-only separation rule and fixed event lockout."""
    if candidates.empty:
        return candidates.copy(), 0
    eligible = candidates[(candidates.corridor_width_ticks >= min_ticks - 1e-10) &
                          (candidates.corridor_width_day_sigma >= min_day_sigma - 1e-10)].copy()
    eligible = eligible.sort_values(["product", "session_date", "timeframe", "session_anchor", "forecast_ts"])
    selected_indexes: list[int] = []
    suppressed = 0
    group_keys = ["product", "session_date", "timeframe", "session_anchor"]
    for _, group in eligible.groupby(group_keys, sort=False):
        lock_until: pd.Timestamp | None = None
        ordinal = 0
        for index, row in group.iterrows():
            timestamp = row.forecast_ts
            if lock_until is not None and timestamp < lock_until:
                suppressed += 1
                continue
            ordinal += 1
            selected_indexes.append(index)
            eligible.loc[index, "episode_ordinal"] = ordinal
            lock_until = timestamp + pd.Timedelta(minutes=lockout_minutes)
    selected = eligible.loc[selected_indexes].copy()
    if not selected.empty:
        selected["episode_ordinal"] = selected.episode_ordinal.astype(int)
        selected["event_id"] = selected.apply(
            lambda r: (f"C:{r['product']}:{r.session_date}:{r.timeframe}:"
                       f"{r.session_anchor}:{r.episode_ordinal}:{r.forecast_ts.isoformat()}"), axis=1,
        )
    return selected.reset_index(drop=True), suppressed
