"""Causal one-minute outcome evaluation for the frozen study 11 protocol."""

from __future__ import annotations

from datetime import date
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from abacus_bhishma.continuous_loader import open_continuous_dataset
from .features import SCALE, load_features, reference_zone, round_half_up_to_tick

SOURCE_COLUMNS = [
    "ts_event", "session_date", "instrument_id", "raw_symbol",
    "open", "high", "low", "close", "volume",
]


def load_source_year(root: Path, product: str, year: int) -> pd.DataFrame:
    dataset = open_continuous_dataset(root, product, "unadjusted")
    filt = ((pc.field("session_date") >= pa.scalar(date(year, 1, 1), pa.date32())) &
            (pc.field("session_date") < pa.scalar(date(year + 1, 1, 1), pa.date32())))
    return dataset.to_table(columns=SOURCE_COLUMNS, filter=filt).to_pandas()


def reconcile_day(feature: pd.DataFrame, source: pd.DataFrame, interval: int) -> int:
    if len(source) != len(feature) * interval:
        raise ValueError("feature/source day bar count differs")
    if not np.array_equal(source.ts_event.to_numpy()[::interval], feature.ts_event.to_numpy()):
        raise ValueError("feature/source boundaries differ")
    if not (feature.available_at == feature.bar_close_ts).all():
        raise ValueError("available_at differs from exclusive close")
    if feature.price_adjustment.nunique() != 1 or feature.raw_symbol.nunique() != 1 or feature.instrument_id.nunique() != 1:
        raise ValueError("contract or adjustment changes within product-session")
    for key in ("instrument_id", "raw_symbol"):
        if not np.array_equal(source[key].to_numpy()[::interval], feature[key].to_numpy()):
            raise ValueError(f"feature/source {key} differs")
    adjustment = feature.price_adjustment.to_numpy()
    expected = {
        "open": source.open.to_numpy()[::interval],
        "high": source.high.to_numpy().reshape(-1, interval).max(axis=1),
        "low": source.low.to_numpy().reshape(-1, interval).min(axis=1),
        "close": source.close.to_numpy()[interval - 1::interval],
    }
    for key, values in expected.items():
        if not np.array_equal(feature[key].to_numpy() - adjustment, values):
            raise ValueError(f"feature/source adjusted {key} differs")
    if not np.array_equal(feature.volume.to_numpy(), source.volume.to_numpy().reshape(-1, interval).sum(axis=1)):
        raise ValueError("feature/source volume differs")
    return len(feature)


def _prices(path: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return tuple(path[key].to_numpy(dtype=float) * SCALE for key in ("open", "high", "low", "close"))


def contact_fixed(path: pd.DataFrame, lower: float, upper: float, starting_side: int) -> dict:
    """Exact zone contact; a complete gap through is flagged but is not a touch."""
    gap_minute = None
    opens, highs, lows, _ = _prices(path)
    for index, (opening, high, low) in enumerate(zip(opens, highs, lows), start=1):
        if low <= upper + 1e-10 and high >= lower - 1e-10:
            return {"contact": True, "contact_minute": index,
                    "gap_through": gap_minute is not None, "gap_minute": gap_minute}
        gap = ((starting_side > 0 and high < lower - 1e-10) or
               (starting_side < 0 and low > upper + 1e-10))
        if gap and gap_minute is None:
            gap_minute = index
    return {"contact": False, "contact_minute": None,
            "gap_through": gap_minute is not None, "gap_minute": gap_minute}


def contact_dynamic(path: pd.DataFrame, lowers: np.ndarray, uppers: np.ndarray,
                    starting_side: int) -> dict:
    gap_minute = None
    opens, highs, lows, _ = _prices(path)
    if len(path) != len(lowers) or len(path) != len(uppers):
        return {"contact": None, "contact_minute": None, "gap_through": None,
                "gap_minute": None, "missing": "dynamic_reference_length"}
    for index, (opening, high, low, lower, upper) in enumerate(
            zip(opens, highs, lows, lowers, uppers), start=1):
        if not np.isfinite(lower) or not np.isfinite(upper):
            return {"contact": None, "contact_minute": None, "gap_through": None,
                    "gap_minute": None, "missing": "dynamic_reference_unavailable"}
        if low <= upper + 1e-10 and high >= lower - 1e-10:
            return {"contact": True, "contact_minute": index,
                    "gap_through": gap_minute is not None, "gap_minute": gap_minute,
                    "missing": None}
        gap = ((starting_side > 0 and high < lower - 1e-10) or
               (starting_side < 0 and low > upper + 1e-10))
        if gap and gap_minute is None:
            gap_minute = index
    return {"contact": False, "contact_minute": None,
            "gap_through": gap_minute is not None, "gap_minute": gap_minute,
            "missing": None}


def race_return_extension(path: pd.DataFrame, side: int, return_lower: float,
                          return_upper: float, extension: float) -> dict:
    opens, highs, lows, _ = _prices(path)
    for minute, (opening, high, low) in enumerate(zip(opens, highs, lows), start=1):
        if side > 0:
            return_open = opening <= return_upper + 1e-10
            extension_open = opening >= extension - 1e-10
            return_touch = low <= return_upper + 1e-10
            extension_touch = high >= extension - 1e-10
            return_gap = opening < return_lower - 1e-10
        else:
            return_open = opening >= return_lower - 1e-10
            extension_open = opening <= extension + 1e-10
            return_touch = high >= return_lower - 1e-10
            extension_touch = low <= extension + 1e-10
            return_gap = opening > return_upper + 1e-10
        if return_open and extension_open:
            return {"outcome": "ambiguous", "minute": minute, "gap": True, "gap_target": "both"}
        if return_open:
            return {"outcome": "return_first", "minute": minute, "gap": return_gap,
                    "gap_target": "return" if return_gap else None}
        if extension_open:
            return {"outcome": "extension_first", "minute": minute, "gap": True,
                    "gap_target": "extension"}
        if return_touch and extension_touch:
            return {"outcome": "ambiguous", "minute": minute, "gap": False, "gap_target": None}
        if return_touch:
            return {"outcome": "return_first", "minute": minute, "gap": False, "gap_target": None}
        if extension_touch:
            return {"outcome": "extension_first", "minute": minute, "gap": False, "gap_target": None}
    return {"outcome": "neither", "minute": None, "gap": False, "gap_target": None}


def race_between_zones(path: pd.DataFrame, lower_zone: tuple[float, float],
                       upper_zone: tuple[float, float], lower_label: str,
                       upper_label: str) -> dict:
    opens, highs, lows, _ = _prices(path)
    lower_low, lower_high = lower_zone
    upper_low, upper_high = upper_zone
    for minute, (opening, high, low) in enumerate(zip(opens, highs, lows), start=1):
        lower_open = opening <= lower_high + 1e-10
        upper_open = opening >= upper_low - 1e-10
        if lower_open and upper_open:
            return {"outcome": "ambiguous", "minute": minute, "gap": True, "gap_target": "both"}
        if lower_open:
            return {"outcome": lower_label, "minute": minute,
                    "gap": opening < lower_low - 1e-10,
                    "gap_target": lower_label if opening < lower_low - 1e-10 else None}
        if upper_open:
            return {"outcome": upper_label, "minute": minute,
                    "gap": opening > upper_high + 1e-10,
                    "gap_target": upper_label if opening > upper_high + 1e-10 else None}
        lower_touch = low <= lower_high + 1e-10
        upper_touch = high >= upper_low - 1e-10
        if lower_touch and upper_touch:
            return {"outcome": "ambiguous", "minute": minute, "gap": False, "gap_target": None}
        if lower_touch:
            return {"outcome": lower_label, "minute": minute, "gap": False, "gap_target": None}
        if upper_touch:
            return {"outcome": upper_label, "minute": minute, "gap": False, "gap_target": None}
    return {"outcome": "neither", "minute": None, "gap": False, "gap_target": None}


def _source_path(source: pd.DataFrame, start: pd.Timestamp, minutes: int) -> pd.DataFrame:
    index = int(source.ts_event.searchsorted(start))
    return source.iloc[index:index + minutes]


def _valid_path(path: pd.DataFrame, start: pd.Timestamp, minutes: int,
                raw_symbol: str, instrument_id: int) -> str | None:
    if len(path) != minutes:
        return "incomplete_future_evidence"
    if path.ts_event.iloc[0] != start or path.ts_event.iloc[-1] != start + pd.Timedelta(minutes=minutes - 1):
        return "missing_source_bars"
    if not (path.ts_event.diff().iloc[1:] == pd.Timedelta(minutes=1)).all():
        return "missing_source_bars"
    if ((path.raw_symbol != raw_symbol) | (path.instrument_id != instrument_id)).any():
        return "future_contract_discontinuity"
    return None


def _dynamic_zones(feature: pd.DataFrame, path: pd.DataFrame, anchor: str,
                   tick: float) -> tuple[np.ndarray, np.ndarray]:
    times = feature.available_at.to_numpy(dtype="datetime64[ns]")
    requests = path.ts_event.to_numpy(dtype="datetime64[ns]")
    indexes = np.searchsorted(times, requests, side="right") - 1
    lowers = np.full(len(path), np.nan)
    uppers = np.full(len(path), np.nan)
    valid = indexes >= 0
    if valid.any():
        chosen = feature.iloc[indexes[valid]]
        refs = chosen[f"{anchor}_vwap"].to_numpy(dtype=float) - chosen.price_adjustment.to_numpy(dtype=float) * SCALE
        active = chosen[f"{anchor}_anchor_active"].fillna(False).to_numpy(dtype=bool)
        for destination, reference, okay in zip(np.flatnonzero(valid), refs, active):
            if okay and np.isfinite(reference):
                lower, upper, _ = reference_zone(float(reference), tick)
                lowers[destination], uppers[destination] = lower, upper
    return lowers, uppers


def _dynamic_corridor_race(feature: pd.DataFrame, path: pd.DataFrame, session_anchor: str,
                           tick: float, day_below_session: bool) -> dict:
    day_low, day_high = _dynamic_zones(feature, path, "globex", tick)
    session_low, session_high = _dynamic_zones(feature, path, session_anchor, tick)
    opens, highs, lows, _ = _prices(path)
    for minute in range(len(path)):
        values = (day_low[minute], day_high[minute], session_low[minute], session_high[minute])
        if not np.isfinite(values).all():
            return {"outcome": "unavailable", "minute": None, "gap": False,
                    "gap_target": None}
        if day_below_session:
            lower = (day_low[minute], day_high[minute], "day_first")
            upper = (session_low[minute], session_high[minute], "session_first")
        else:
            lower = (session_low[minute], session_high[minute], "session_first")
            upper = (day_low[minute], day_high[minute], "day_first")
        opening, high, low = opens[minute], highs[minute], lows[minute]
        lower_open = opening <= lower[1] + 1e-10
        upper_open = opening >= upper[0] - 1e-10
        if lower_open and upper_open:
            return {"outcome": "ambiguous", "minute": minute + 1, "gap": True, "gap_target": "both"}
        if lower_open:
            return {"outcome": lower[2], "minute": minute + 1,
                    "gap": opening < lower[0] - 1e-10, "gap_target": lower[2]}
        if upper_open:
            return {"outcome": upper[2], "minute": minute + 1,
                    "gap": opening > upper[1] + 1e-10, "gap_target": upper[2]}
        lower_touch = low <= lower[1] + 1e-10
        upper_touch = high >= upper[0] - 1e-10
        if lower_touch and upper_touch:
            return {"outcome": "ambiguous", "minute": minute + 1, "gap": False, "gap_target": None}
        if lower_touch:
            return {"outcome": lower[2], "minute": minute + 1, "gap": False, "gap_target": None}
        if upper_touch:
            return {"outcome": upper[2], "minute": minute + 1, "gap": False, "gap_target": None}
    return {"outcome": "neither", "minute": None, "gap": False, "gap_target": None}


def evaluate_ab(row: pd.Series, feature: pd.DataFrame, source: pd.DataFrame,
                extension_factors=(.25, .5, 1.0)) -> dict:
    out = row.to_dict()
    start = row.forecast_ts
    path30 = _source_path(source, start, 30)
    reason = _valid_path(path30, start, 30, row.raw_symbol, int(row.instrument_id))
    out.update(outcome_missing=reason, frozen_return_30=None, evolving_return_30=None,
               frozen_return_window=None, evolving_return_window=None,
               evolving_without_frozen_30=None, frozen_return_minute=None,
               evolving_return_minute=None, frozen_gap_through_30=None,
               evolving_gap_through_30=None, return_distance_points=None,
               return_distance_ticks=None, extension_distance_points=None,
               extension_distance_ticks=None, barrier_primary=None,
               barrier_primary_minute=None, barrier_primary_gap=None,
               barrier_primary_gap_target=None, barrier_quarter_sigma=None,
               barrier_one_sigma=None, toward_vwap_mfe_points=None,
               away_mae_points=None, endpoint_toward_vwap_points=None)
    if reason:
        return out
    adjustment = float(row.price_adjustment) * SCALE
    tick = float(row.tick)
    side = int(row.side)
    reference = float(row.vwap) - adjustment
    lower, upper, center = reference_zone(reference, tick)
    current_close = float(row.close) - adjustment
    return_distance = current_close - upper if side > 0 else lower - current_close
    if return_distance <= 1e-10:
        out["outcome_missing"] = "checkpoint_inside_rounded_return_zone"
        return out
    frozen30 = contact_fixed(path30, lower, upper, side)
    dynamic_lower, dynamic_upper = _dynamic_zones(feature, path30, row.anchor, tick)
    evolving30 = contact_dynamic(path30, dynamic_lower, dynamic_upper, side)
    window_minutes = int(round((row.window_end_ts - start).total_seconds() / 60))
    path_window = _source_path(source, start, window_minutes)
    window_reason = _valid_path(path_window, start, window_minutes, row.raw_symbol, int(row.instrument_id))
    if window_reason is None:
        frozen_window = contact_fixed(path_window, lower, upper, side)
        dyn_low_window, dyn_high_window = _dynamic_zones(feature, path_window, row.anchor, tick)
        evolving_window = contact_dynamic(path_window, dyn_low_window, dyn_high_window, side)
        out["frozen_return_window"] = frozen_window["contact"]
        out["evolving_return_window"] = evolving_window["contact"]
    out["window_outcome_missing"] = window_reason
    out["frozen_return_30"] = frozen30["contact"]
    out["evolving_return_30"] = evolving30["contact"]
    out["frozen_return_minute"] = frozen30["contact_minute"]
    out["evolving_return_minute"] = evolving30["contact_minute"]
    out["frozen_gap_through_30"] = frozen30["gap_through"]
    out["evolving_gap_through_30"] = evolving30["gap_through"]
    out["evolving_without_frozen_30"] = bool(evolving30["contact"] and not frozen30["contact"])
    out["return_target"] = center
    out["return_zone_low"] = lower
    out["return_zone_high"] = upper
    out["return_distance_points"] = return_distance
    out["return_distance_ticks"] = return_distance / tick

    factors = {}
    for factor in extension_factors:
        ticks = max(1, math.ceil(factor * float(row.sigma) / tick - 1e-10))
        extension = current_close + side * ticks * tick
        factors[factor] = (ticks, extension, race_return_extension(path30, side, lower, upper, extension))
    primary_ticks, primary_extension, primary = factors[.5]
    out["extension_target"] = primary_extension
    out["extension_distance_points"] = primary_ticks * tick
    out["extension_distance_ticks"] = primary_ticks
    out["return_geometry_share"] = return_distance / (return_distance + primary_ticks * tick)
    out["barrier_primary"] = primary["outcome"]
    out["barrier_primary_minute"] = primary["minute"]
    out["barrier_primary_gap"] = primary["gap"]
    out["barrier_primary_gap_target"] = primary["gap_target"]
    out["barrier_quarter_sigma"] = factors[.25][2]["outcome"]
    out["barrier_one_sigma"] = factors[1.0][2]["outcome"]
    _, highs, lows, closes = _prices(path30)
    if side > 0:
        out["toward_vwap_mfe_points"] = current_close - float(lows.min())
        out["away_mae_points"] = float(highs.max()) - current_close
        out["endpoint_toward_vwap_points"] = current_close - float(closes[-1])
    else:
        out["toward_vwap_mfe_points"] = float(highs.max()) - current_close
        out["away_mae_points"] = current_close - float(lows.min())
        out["endpoint_toward_vwap_points"] = float(closes[-1]) - current_close
    return out


def evaluate_corridor(row: pd.Series, feature: pd.DataFrame, source: pd.DataFrame) -> tuple[dict, list[dict]]:
    out = row.to_dict()
    start = row.forecast_ts
    path = _source_path(source, start, 30)
    reason = _valid_path(path, start, 30, row.raw_symbol, int(row.instrument_id))
    out.update(outcome_missing=reason, frozen_outcome=None, first_event_minute=None,
               gap_first=None, gap_target=None, evolving_outcome=None,
               evolving_first_event_minute=None)
    if reason:
        return out, []
    adjustment = float(row.price_adjustment) * SCALE
    day_zone = (float(row.day_zone_low) - adjustment, float(row.day_zone_high) - adjustment)
    session_zone = (float(row.session_zone_low) - adjustment, float(row.session_zone_high) - adjustment)
    if bool(row.day_below_session):
        result = race_between_zones(path, day_zone, session_zone, "day_first", "session_first")
    else:
        result = race_between_zones(path, session_zone, day_zone, "session_first", "day_first")
    dynamic = _dynamic_corridor_race(feature, path, row.session_anchor, float(row.tick), bool(row.day_below_session))
    out["day_target_unadjusted"] = float(row.day_target) - adjustment
    out["session_target_unadjusted"] = float(row.session_target) - adjustment
    out["frozen_outcome"] = result["outcome"]
    out["first_event_minute"] = result["minute"]
    out["gap_first"] = result["gap"]
    out["gap_target"] = result["gap_target"]
    out["evolving_outcome"] = dynamic["outcome"]
    out["evolving_first_event_minute"] = dynamic["minute"]
    _, highs, lows, closes = _prices(path)
    event_close = float(row.close) - adjustment
    day_target = out["day_target_unadjusted"]
    session_target = out["session_target_unadjusted"]
    day_direction = 1 if day_target > event_close else -1
    out["max_move_toward_day_points"] = (float(highs.max()) - event_close if day_direction > 0
                                          else event_close - float(lows.min()))
    out["max_move_toward_session_points"] = (event_close - float(lows.min()) if day_direction > 0
                                              else float(highs.max()) - event_close)
    out["endpoint_position_from_day"] = abs(float(closes[-1]) - day_target) / abs(session_target - day_target)

    updates: list[dict] = []
    for elapsed in (10, 20):
        prefix = path.iloc[:elapsed]
        if bool(row.day_below_session):
            prefix_result = race_between_zones(prefix, day_zone, session_zone, "day_first", "session_first")
        else:
            prefix_result = race_between_zones(prefix, session_zone, day_zone, "session_first", "day_first")
        if prefix_result["outcome"] != "neither":
            continue
        current = float(prefix.close.iloc[-1]) * SCALE
        future = path.iloc[elapsed:]
        if bool(row.day_below_session):
            future_result = race_between_zones(future, day_zone, session_zone, "day_first", "session_first")
        else:
            future_result = race_between_zones(future, session_zone, day_zone, "session_first", "day_first")
        width = abs(session_target - day_target)
        updates.append({
            "update_id": f"{row.event_id}:U{elapsed}", "event_id": row.event_id,
            "product": row["product"], "session_date": row.session_date,
            "timeframe": row.timeframe, "session_anchor": row.session_anchor,
            "event_forecast_ts": start, "forecast_ts": start + pd.Timedelta(minutes=elapsed),
            "elapsed_minutes": elapsed, "remaining_minutes": 30 - elapsed,
            "current_close": current,
            "position_from_day": abs(current - day_target) / width if width else math.nan,
            "distance_to_day_ticks": abs(current - day_target) / float(row.tick),
            "distance_to_session_ticks": abs(current - session_target) / float(row.tick),
            "future_outcome": future_result["outcome"],
            "future_first_event_minute": future_result["minute"],
            "original_outcome": result["outcome"], "split": row.split,
            "year": row.year, "episode_ordinal": row.episode_ordinal,
        })
    return out, updates


def evaluate_partition(root: Path, stage: Path, product: str, year: int,
                       timeframe: str) -> dict:
    ab_all = pd.read_parquet(stage / "features" / f"landmarks_ab_{product}_{timeframe}.parquet")
    c_all = pd.read_parquet(stage / "features" / f"events_c_{product}_{timeframe}.parquet")
    ab = ab_all[ab_all.year == year]
    corridors = c_all[c_all.year == year]
    if ab.empty and corridors.empty:
        return {"product": product, "year": year, "timeframe": timeframe,
                "ab_rows": 0, "corridor_rows": 0, "updates": 0,
                "reconciled_feature_bars": 0}
    feature = load_features(root, product, year, timeframe)
    source = load_source_year(root, product, year)
    features_by_day = {str(day): group.reset_index(drop=True)
                       for day, group in feature.groupby("session_date", sort=False)}
    source_by_day = {str(day): group.reset_index(drop=True)
                     for day, group in source.groupby("session_date", sort=False)}
    needed_days = set(ab.session_date).union(corridors.session_date)
    reconciled = 0
    for day in needed_days:
        reconciled += reconcile_day(features_by_day[day], source_by_day[day], int(timeframe[:-1]))
    ab_records = [
        evaluate_ab(row, features_by_day[row.session_date], source_by_day[row.session_date])
        for _, row in ab.iterrows()
    ]
    c_records: list[dict] = []
    updates: list[dict] = []
    for _, row in corridors.iterrows():
        event, event_updates = evaluate_corridor(
            row, features_by_day[row.session_date], source_by_day[row.session_date]
        )
        c_records.append(event)
        updates.extend(event_updates)
    events = stage / "events"
    events.mkdir(exist_ok=True)
    if ab_records:
        pd.DataFrame(ab_records).to_parquet(events / f"ab_{product}_{timeframe}_{year}.parquet", index=False)
    if c_records:
        pd.DataFrame(c_records).to_parquet(events / f"c_{product}_{timeframe}_{year}.parquet", index=False)
    if updates:
        pd.DataFrame(updates).to_parquet(events / f"c_updates_{product}_{timeframe}_{year}.parquet", index=False)
    return {
        "product": product, "year": year, "timeframe": timeframe,
        "ab_rows": len(ab_records), "corridor_rows": len(c_records),
        "updates": len(updates), "reconciled_feature_bars": reconciled,
        "ab_missing": dict(pd.Series([x.get("outcome_missing") for x in ab_records]).value_counts(dropna=False)),
        "corridor_missing": dict(pd.Series([x.get("outcome_missing") for x in c_records]).value_counts(dropna=False)),
    }

