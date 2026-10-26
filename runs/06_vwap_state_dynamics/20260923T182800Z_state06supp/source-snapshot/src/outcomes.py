"""Reconciled unadjusted one-minute paths for frozen landmark features."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import math

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from abacus_bhishma.continuous_loader import open_continuous_dataset
from .features import SCALE, load_features, side_of

SOURCE_COLUMNS = ["ts_event", "session_date", "instrument_id", "raw_symbol", "open", "high", "low", "close", "volume"]


def load_source_year(root: Path, product: str, year: int) -> pd.DataFrame:
    dataset = open_continuous_dataset(root, product)
    filt = ((pc.field("session_date") >= pa.scalar(date(year, 1, 1), pa.date32())) &
            (pc.field("session_date") < pa.scalar(date(year+1, 1, 1), pa.date32())))
    return dataset.to_table(columns=SOURCE_COLUMNS, filter=filt).to_pandas()


def reconcile_day(feature: pd.DataFrame, source: pd.DataFrame, interval: int) -> int:
    """Independently reconcile every published output bar with contract-truth bars."""
    if len(source) != len(feature) * interval:
        raise ValueError("feature/source day bar count differs")
    if not np.array_equal(source.ts_event.to_numpy()[::interval], feature.ts_event.to_numpy()):
        raise ValueError("feature/source boundaries differ")
    if not (feature.available_at == feature.bar_close_ts).all():
        raise ValueError("feature available_at differs from exclusive close")
    if feature.price_adjustment.nunique() != 1 or feature.raw_symbol.nunique() != 1 or feature.instrument_id.nunique() != 1:
        raise ValueError("feature contract/adjustment changes inside session")
    for key in ("instrument_id", "raw_symbol"):
        if not np.array_equal(source[key].to_numpy()[::interval], feature[key].to_numpy()):
            raise ValueError(f"feature/source {key} differs")
    adjustment = feature.price_adjustment.to_numpy()
    expected = {"open": source.open.to_numpy()[::interval],
                "high": source.high.to_numpy().reshape(-1, interval).max(axis=1),
                "low": source.low.to_numpy().reshape(-1, interval).min(axis=1),
                "close": source.close.to_numpy()[interval-1::interval]}
    for key, values in expected.items():
        if not np.array_equal(feature[key].to_numpy() - adjustment, values):
            raise ValueError(f"feature/source adjusted {key} differs")
    if not np.array_equal(feature.volume.to_numpy(), source.volume.to_numpy().reshape(-1, interval).sum(axis=1)):
        raise ValueError("feature/source volume differs")
    return len(feature)


def barrier_class(path: pd.DataFrame, direction: int, distance: float, tick: float) -> str:
    if direction == 0 or path.empty:
        return "unavailable"
    opening = float(path.open.iloc[0]) * SCALE
    favorable = opening + direction * distance
    adverse = opening - direction * distance
    for bar in path.itertuples(index=False):
        opened = bar.open * SCALE
        if direction * (opened - favorable) >= -1e-8:
            return "favorable"
        if direction * (opened - adverse) <= 1e-8:
            return "adverse"
        first = direction * ((bar.high if direction > 0 else bar.low) * SCALE - favorable) >= -1e-8
        second = direction * ((bar.low if direction > 0 else bar.high) * SCALE - adverse) <= 1e-8
        if first and second:
            return "ambiguous"
        if first:
            return "favorable"
        if second:
            return "adverse"
    return "neither"


def evaluate_landmark(row: pd.Series, feature: pd.DataFrame, source: pd.DataFrame) -> dict:
    """All future evaluation starts after landmark availability; never changes X."""
    out = row.to_dict()
    interval = int(row.timeframe[:-1])
    length = 30 // interval
    index = int(row.feature_index)
    t = row.landmark_ts
    future = feature.iloc[index+1:index+length+1]
    start = int(source.ts_event.searchsorted(t))
    path = source.iloc[start:start+30]
    reason = None
    if (len(path) != 30 or path.ts_event.iloc[0] != t or
        path.ts_event.iloc[-1] != t + pd.Timedelta(minutes=29) or
        not (path.ts_event.diff().iloc[1:] == pd.Timedelta(minutes=1)).all()):
        reason = "source_30m_gap"
    elif ((path.raw_symbol != row.raw_symbol) | (path.instrument_id != row.instrument_id)).any():
        reason = "future_contract_discontinuity"
    elif (len(future) != length or future.available_at.iloc[0] != t + pd.Timedelta(minutes=interval) or
          future.available_at.iloc[-1] != t + pd.Timedelta(minutes=30) or
          not (future.available_at.diff().iloc[1:] == pd.Timedelta(minutes=interval)).all()):
        reason = "future_feature_gap"
    elif (future[f"{row.anchor}_anchor_ts"] != feature[f"{row.anchor}_anchor_ts"].iloc[index]).any() or not future[f"{row.anchor}_anchor_active"].all():
        reason = "future_anchor_discontinuity"
    elif row.anchor != "globex" and not future[f"is_{row.anchor}_session"].all():
        reason = "future_outside_window"
    elif ((future.raw_symbol != row.raw_symbol) | (future.instrument_id != row.instrument_id) |
          (future.price_adjustment != row.price_adjustment)).any():
        reason = "future_feature_contract_discontinuity"
    out["outcome_missing"] = reason
    out["y1_residence"] = None
    out["y2_cross"] = None
    out["first_cross_minute"] = None
    out["frozen_residence"] = None
    out["barrier_8tick"] = None
    out["barrier_half_sigma"] = None
    out["half_sigma_ticks"] = None
    out["future_median"] = None
    out["vwap_error"] = None
    out["twap_error"] = None
    out["last_price_error"] = None
    out["vwap_win"] = None
    out["paired_tie"] = None
    out["future_volume_weighted_price"] = None
    out["future_end_close"] = None
    if reason:
        return out
    adjustment = row.price_adjustment * SCALE
    source_closes = path.close.to_numpy(dtype=float) * SCALE
    future_closes = source_closes[interval-1::interval]
    feature_closes = future.close.to_numpy(dtype=float) * SCALE - adjustment
    if not np.allclose(future_closes, feature_closes, atol=1e-8, rtol=0):
        raise ValueError(f"future feature/source close mismatch: {row.event_id}")
    future_vwaps = future[f"{row.anchor}_vwap"].to_numpy(dtype=float) - adjustment
    if not np.isfinite(future_vwaps).all():
        out["outcome_missing"] = "future_reference_missing"
        return out
    current = int(row.side)
    if current:
        evolving = np.array([side_of(c, v) for c, v in zip(future_closes, future_vwaps)])
        frozen = np.array([side_of(c, row.vwap-adjustment) for c in future_closes])
        opposite = np.flatnonzero(evolving == -current)
        out["y2_cross"] = bool(len(opposite))
        out["y1_residence"] = not bool(len(opposite))
        out["first_cross_minute"] = int((opposite[0]+1)*interval) if len(opposite) else None
        out["frozen_residence"] = not bool(np.any(frozen == -current))
        tick = float(row.tick)
        half_ticks = max(1, math.ceil(.5 * row.sigma / tick - 1e-10))
        out["half_sigma_ticks"] = half_ticks
        out["barrier_8tick"] = barrier_class(path, current, 8*tick, tick)
        out["barrier_half_sigma"] = barrier_class(path, current, half_ticks*tick, tick)
    target = float(np.median(source_closes))
    vwap = float(row.vwap) - adjustment
    twap = float(row.twap) - adjustment
    last = float(row.close) - adjustment
    v_err, t_err = abs(target-vwap), abs(target-twap)
    out["future_median"] = target
    out["vwap_error"] = v_err
    out["twap_error"] = t_err
    out["last_price_error"] = abs(target-last)
    out["vwap_win"] = v_err < t_err - 1e-8
    out["paired_tie"] = abs(v_err-t_err) <= 1e-8
    vol = path.volume.to_numpy(dtype=float)
    out["future_volume_weighted_price"] = float(np.dot(source_closes, vol)/vol.sum()) if vol.sum() else None
    out["future_end_close"] = float(source_closes[-1])
    return out


def evaluate_year(root: Path, stage: Path, product: str, year: int, timeframe: str) -> dict:
    landmarks = pd.read_parquet(stage / "features" / f"landmarks_{product}_{timeframe}.parquet")
    landmarks = landmarks[landmarks.year == year]
    if landmarks.empty:
        return {"product": product, "year": year, "timeframe": timeframe, "landmarks": 0}
    features = load_features(root, product, year, timeframe)
    source = load_source_year(root, product, year)
    features_by_day = {str(day): group.reset_index(drop=True) for day, group in features.groupby("session_date", sort=False)}
    source_by_day = {str(day): group.reset_index(drop=True) for day, group in source.groupby("session_date", sort=False)}
    records = []
    reconciled = 0
    for day, group in landmarks.groupby("session_date", sort=False):
        f = features_by_day[day]
        s = source_by_day[day]
        reconciled += reconcile_day(f, s, int(timeframe[:-1]))
        for _, row in group.iterrows():
            records.append(evaluate_landmark(row, f, s))
    output = pd.DataFrame(records)
    (stage / "events").mkdir(exist_ok=True)
    output.to_parquet(stage / "events" / f"events_{product}_{timeframe}_{year}.parquet", index=False)
    return {"product": product, "year": year, "timeframe": timeframe,
            "landmarks": len(output), "reconciled_feature_bars": reconciled,
            "outcome_missing": output.outcome_missing.value_counts(dropna=False).to_dict()}
