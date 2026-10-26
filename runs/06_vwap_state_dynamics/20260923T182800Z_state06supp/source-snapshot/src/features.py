"""Causal landmark features. This module never reads a future price outcome."""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd

from abacus_bhishma.feature_loader import load_session_anchored_vwap

PRODUCTS = ("ES", "NQ", "GC")
YEARS = {"ES": range(2021, 2027), "NQ": range(2021, 2027), "GC": range(2016, 2027)}
ANCHORS = ("globex", "asia", "london", "ny")
SCALE = 1e-9
COLUMNS = ["ts_event", "bar_close_ts", "available_at", "session_date", "product", "timeframe",
           "instrument_id", "raw_symbol", "open", "high", "low", "close", "volume",
           "price_adjustment", "min_tick", "is_asia_session", "is_london_session",
           "is_ny_session"]
for _a in ANCHORS:
    COLUMNS += [f"{_a}_{s}" for s in ("anchor_ts", "anchor_active", "vwap", "sigma",
               "cumulative_volume", "minutes_since_anchor")]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_features(root: Path, product: str, year: int, timeframe: str) -> pd.DataFrame:
    return load_session_anchored_vwap(root, product, timeframe, version="1.0.0",
                                      start_date=f"{year}-01-01", end_date=f"{year+1}-01-01",
                                      columns=COLUMNS).to_pandas()


def side_of(close: float, vwap: float, tolerance: float = 1e-8) -> int:
    return int(close > vwap + tolerance) - int(close < vwap - tolerance)


def state_of(sides: np.ndarray, timeframe: int) -> tuple[str, int, int, int, int, int]:
    """Return class, above, below, equality, changes, longest run, in that order."""
    above = int(np.sum(sides == 1))
    below = int(np.sum(sides == -1))
    equal = int(np.sum(sides == 0))
    changes = int(np.sum((sides[1:] * sides[:-1]) == -1))
    current = int(sides[-1])
    longest = 0
    run = 0
    prior = 0
    for side in sides:
        if side != 0 and side == prior:
            run += 1
        elif side != 0:
            run = 1
        else:
            run = 0
        longest = max(longest, run)
        prior = int(side)
    n = len(sides)
    if timeframe == 2:
        state = ("persistent" if current and int(np.sum(sides == current)) >= 12 and changes <= 1
                 else "rotational" if 6 <= above <= 9 and changes >= 3 else "other")
    else:
        state = ("persistent" if current and int(np.sum(sides == current)) >= 5 and changes <= 1
                 else "rotational" if 2 <= above <= 4 and changes >= 2 else "other")
    return state, above, below, equal, changes, longest


def clock_window(local: pd.Timestamp) -> str:
    m = local.hour * 60 + local.minute
    if m >= 18 * 60 or m < 3 * 60:
        return "evening_asia"
    if m < 9 * 60 + 30:
        return "london_to_ny"
    if m < 12 * 60:
        return "ny_morning"
    return "ny_afternoon"


def prior_atr(days: pd.DataFrame) -> dict[date, float]:
    """Fourteen previous eligible product sessions; no signal-day range enters."""
    daily = days.groupby("session_date", sort=True).agg(high=("high", "max"),
              low=("low", "min"), close=("close", "last"))
    result: dict[date, float] = {}
    ranges: list[float] = []
    previous = None
    for day, row in daily.iterrows():
        result[day] = float(np.mean(ranges[-14:])) if len(ranges) >= 14 else math.nan
        high, low, close = row.high * SCALE, row.low * SCALE, row.close * SCALE
        ranges.append(max(high - low, abs(high - previous), abs(low - previous)) if previous is not None else high - low)
        previous = close
    return result


def extract_day(day: pd.DataFrame, anchor: str, timeframe: int, atr: float) -> tuple[list[dict], Counter]:
    """Only current and prior rows are used to derive each landmark feature."""
    rows: list[dict] = []
    counts: Counter = Counter()
    day = day.reset_index(drop=True)
    n = len(day)
    t = day.available_at
    local = t.dt.tz_convert("America/New_York")
    candidate = np.flatnonzero((local.dt.minute.isin([0, 30]) & (local.dt.second == 0)).to_numpy())
    length = 30 // timeframe
    membership = np.ones(n, dtype=bool) if anchor == "globex" else day[f"is_{anchor}_session"].to_numpy(dtype=bool)
    window_end = day.bar_close_ts.iloc[np.flatnonzero(membership)[-1]] if membership.any() else day.bar_close_ts.iloc[0]
    active = day[f"{anchor}_anchor_active"].to_numpy(dtype=bool)
    vwaps = day[f"{anchor}_vwap"].to_numpy(dtype=float)
    sigma = day[f"{anchor}_sigma"].to_numpy(dtype=float)
    closes = day.close.to_numpy(dtype=float) * SCALE
    volumes = day.volume.to_numpy(dtype=float)
    hlc3 = (day.high.to_numpy(dtype=float) + day.low.to_numpy(dtype=float) + day.close.to_numpy(dtype=float)) * SCALE / 3
    anchors = day[f"{anchor}_anchor_ts"]
    for i in candidate:
        counts["clock_candidates"] += 1
        if not membership[i] or not active[i]:
            counts["outside_anchor_window"] += 1
            continue
        age = (t.iloc[i] - anchors.iloc[i]).total_seconds() / 60 if not pd.isna(anchors.iloc[i]) else -1
        if age < 60 or i < length:
            counts["immature"] += 1
            continue
        if t.iloc[i] + pd.Timedelta(minutes=30) > window_end:
            counts["insufficient_window_horizon"] += 1
            continue
        start = i - length
        interval = day.iloc[start:i+1]
        if (len(interval) != length + 1 or
            not np.all(np.diff(interval.available_at.to_numpy()).astype("timedelta64[m]").astype(int) == timeframe) or
            not membership[start:i+1].all() or not active[start:i+1].all() or
            interval[f"{anchor}_anchor_ts"].nunique() != 1 or
            interval.raw_symbol.nunique() != 1 or interval.instrument_id.nunique() != 1 or
            interval.price_adjustment.nunique() != 1):
            counts["lookback_or_contract_gap"] += 1
            continue
        if not np.isfinite(vwaps[start:i+1]).all() or not np.isfinite(sigma[i]) or sigma[i] <= 0:
            counts["missing_reference"] += 1
            continue
        if not math.isfinite(atr):
            counts["missing_prior_atr"] += 1
        # All anchor bars through this completed bar, with no future row included.
        anchor_start = int(t.searchsorted(anchors.iloc[i], side="right"))
        # Anchor timestamp is a bar open, while t is exclusive close.
        anchor_start = max(0, anchor_start)
        while anchor_start > 0 and active[anchor_start-1] and anchors.iloc[anchor_start-1] == anchors.iloc[i]:
            anchor_start -= 1
        if anchors.iloc[anchor_start] != anchors.iloc[i]:
            counts["anchor_sequence_missing"] += 1
            continue
        v = volumes[anchor_start:i+1]
        p = hlc3[anchor_start:i+1]
        cvol = float(v.sum())
        twap = float(p.mean())
        recomputed = float(np.dot(v, p) / cvol) if cvol else math.nan
        if not math.isclose(recomputed, vwaps[i], abs_tol=2e-6):
            raise ValueError(f"VWAP identity failed: {day.session_date.iloc[i]} {anchor} {t.iloc[i]} {recomputed} {vwaps[i]}")
        signs = np.array([side_of(closes[j], vwaps[j]) for j in range(i-length+1, i+1)], dtype=np.int8)
        state, above, below, equal, changes, longest = state_of(signs, timeframe)
        price_slope = closes[i] - closes[start]
        vwap_slope = vwaps[i] - vwaps[start]
        local_time = local.iloc[i]
        side = int(signs[-1])
        tick = float(day.min_tick.iloc[i]) * SCALE
        row = {"event_id": f"{day['product'].iloc[i]}:{day.session_date.iloc[i]}:{timeframe}m:{anchor}:{t.iloc[i].isoformat()}",
            "product": str(day['product'].iloc[i]), "session_date": str(day.session_date.iloc[i]),
            "year": int(day.session_date.iloc[i].year), "split": "development" if day.session_date.iloc[i].year <= 2023 else "validation" if day.session_date.iloc[i].year == 2024 else "final",
            "timeframe": f"{timeframe}m", "anchor": anchor, "landmark_ts": t.iloc[i],
            "local_time": local_time.strftime("%Y-%m-%d %H:%M%z"), "clock_window": clock_window(local_time),
            "local_halfhour": local_time.hour * 2 + local_time.minute // 30,
            "feature_index": i, "anchor_age_minutes": age,
            "raw_symbol": str(day.raw_symbol.iloc[i]), "instrument_id": int(day.instrument_id.iloc[i]),
            "price_adjustment": int(day.price_adjustment.iloc[i]), "tick": tick,
            "side": side, "state": state, "above_count": above, "below_count": below,
            "equality_count": equal, "side_changes": changes, "longest_run": longest,
            "above_fraction": above / length, "below_fraction": below / length,
            "close": closes[i], "vwap": vwaps[i], "twap": twap, "sigma": sigma[i],
            "signed_distance_ticks": (closes[i]-vwaps[i])/tick,
            "signed_distance_sigma": (closes[i]-vwaps[i])/sigma[i],
            "price_slope": price_slope, "vwap_slope": vwap_slope,
            "price_slope_atr": price_slope/atr if math.isfinite(atr) and atr > 0 else math.nan,
            "vwap_slope_atr": vwap_slope/atr if math.isfinite(atr) and atr > 0 else math.nan,
            "price_slope_sigma": price_slope/sigma[i], "vwap_slope_sigma": vwap_slope/sigma[i],
            "vwap_acceleration": (vwaps[i]-vwaps[i-length//2])-(vwaps[i-length//2]-vwaps[start]),
            "prior_atr14": atr, "vwap_minus_twap_ticks": (vwaps[i]-twap)/tick,
            "cumulative_volume": cvol, "recent_volume_share": float(v[-length:].sum()/cvol) if cvol else math.nan,
            "vwap_identity_error": recomputed-vwaps[i]}
        rows.append(row)
        counts["feature_valid"] += 1
        counts[f"state_{state}"] += 1
        counts[f"side_{side}"] += 1
    return rows, counts


def verify_pins(root: Path, lock: dict) -> list[dict]:
    records = [lock["release_manifest"], *lock["datasets"], *lock["related_manifests"], lock["audit"]]
    checks = []
    for record in records:
        path = record.get("path", record.get("manifest_path"))
        expected = record.get("sha256", record.get("manifest_sha256"))
        actual = digest(root / path)
        if actual != expected:
            raise ValueError(f"pinned input changed: {path}")
        checks.append({"path": path, "sha256": actual})
    release = json.loads((root / lock["release_manifest"]["path"]).read_text())
    if release["release_id"] != "session_anchored_vwap__1.0.0":
        raise ValueError("release ID mismatch")
    for dataset in ("session_anchored_vwap_2m_v1", "session_anchored_vwap_5m_v1", "volume_lead_unadjusted_v1"):
        manifest = json.loads((root / "catalog/datasets" / f"{dataset}.json").read_text())
        for part in manifest["output_files"]:
            path = part["path"]
            actual = digest(root / path)
            if actual != part["sha256"]:
                raise ValueError(f"partition changed: {path}")
            checks.append({"path": path, "sha256": actual})
    return checks
