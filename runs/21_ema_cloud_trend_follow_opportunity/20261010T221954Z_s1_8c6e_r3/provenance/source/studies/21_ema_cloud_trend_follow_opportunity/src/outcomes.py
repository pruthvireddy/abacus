"""Scheduled-slot price-path observations; no fills, exits, or trade simulation."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import NY, _ordered

HORIZONS = (5, 10, 15, 20, 30, 50, 100)
NUMERIC_OUTCOMES = ("mfe", "mae", "terminal_delta", "mfe_atr", "mae_atr", "terminal_delta_atr")
EVENT_COLUMNS = ("event_id", "product", "contract", "interval_minutes", "timestamp", "signal_timestamp",
                 "available_at", "entry_at", "reference_price", "direction", "side", "signal_idx", "entry_atr",
                 "session", "year", "week", "month", "calendar_date", "time_stratum", "hour", "stage",
                 "touch_mode", "gate_id", "split", "ema20", "ema50", "width", "episode_id")


def _boundary(value: str | pd.Timestamp) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    return stamp.tz_localize(NY).tz_convert("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")


def score_outcomes(bars: pd.DataFrame, events: pd.DataFrame, horizons=HORIZONS,
                   interval_minutes: int = 5, development_start="2018-01-01",
                   endpoint="2021-01-01", roster_end_is_endpoint=False) -> pd.DataFrame:
    """Exclude entry; preserve every accepted event for every requested horizon.

    Input is the complete expected chart-slot roster, with known closures omitted.
    Unknown/mixed/partial slots remain present and censor paths. Reserved events
    are rejected at the API boundary before any price-path calculation.
    """
    roster = _ordered(bars)
    start, end = _boundary(development_start), _boundary(endpoint)
    events = events.copy()
    events["entry_at"] = pd.to_datetime(events.entry_at, utc=True)
    signal_times = pd.to_datetime(events.timestamp, utc=True)
    if ((signal_times < start) | (signal_times >= end)).any():
        raise ValueError("outcome events must be exclusively 2018–2020 development")
    hs = sorted(set(int(h) for h in horizons))
    if not hs or min(hs) < 1:
        raise ValueError("horizons must be positive")
    rows = []
    by_product = {p: f.reset_index(drop=True) for p, f in roster.groupby("product", sort=False)}
    arrays = {}
    for product, source in by_product.items():
        arrays[product] = {key: source[key].to_numpy() for key in ("contract", "high", "low", "close", "quality_reason", "session")}
        arrays[product]["usable"] = source.usable.fillna(False).to_numpy(bool)
        arrays[product]["closure"] = source.get("known_closure_before", pd.Series(False, index=source.index)).fillna(False).to_numpy(bool)
        arrays[product]["starts"] = source.timestamp.array.asi8
        arrays[product]["ends"] = source.available_at.array.asi8
    for event in events.to_dict("records"):
        source = by_product[event["product"]]
        a = arrays[event["product"]]
        i = int(event["signal_idx"])
        if i >= len(source) or a["starts"][i] != pd.Timestamp(event["timestamp"]).value:
            raise ValueError("event signal_idx does not identify its roster slot")
        # Only inspect paths required by the approved horizon, never reserved bars.
        for h in hs:
            row = {key: event[key] for key in EVENT_COLUMNS if key in event}
            row.update(horizon=h, horizon_minutes=h * interval_minutes, status="censored", censor_reason="",
                       terminal_at=pd.NaT, elapsed_minutes=np.nan, crosses_closure=None, same_session=None)
            row.update({key: np.nan for key in NUMERIC_OUTCOMES})
            row.update({key: None for key in ("favorable", "neutral", "adverse", "mfe_gt_mae", "mfe_mae_tie")})
            row.update({key: pd.NaT for key in ("mfe_attainment_start", "mfe_attainment_end", "mae_attainment_start", "mae_attainment_end")})
            lo, hi = i + 1, i + 1 + h
            if hi > len(source):
                # The production roster's explicit end is the development cutoff.
                row["censor_reason"] = "development_endpoint" if roster_end_is_endpoint else "data_edge"
            elif a["ends"][hi - 1] > end.value:
                row["censor_reason"] = "development_endpoint"
            else:
                same_contract = a["contract"][lo:hi] == event["contract"]
                highs, lows = a["high"][lo:hi].astype(float), a["low"][lo:hi].astype(float)
                valid = a["usable"][lo:hi] & np.isfinite(highs) & np.isfinite(lows) & np.isfinite(a["close"][lo:hi].astype(float))
                bad = np.flatnonzero(~same_contract | ~valid)
                if len(bad):
                    j = int(bad[0])
                    row["censor_reason"] = "invalid_future_slot:" + str(a["quality_reason"][lo + j]) if not valid[j] else "contract_switch"
                else:
                    entry, d = float(event["reference_price"]), int(event["direction"])
                    favorable_values = highs - entry if d == 1 else entry - lows
                    adverse_values = entry - lows if d == 1 else highs - entry
                    mfe, mae = max(0., float(favorable_values.max())), max(0., float(adverse_values.max()))
                    delta = d * (float(a["close"][hi - 1]) - entry)
                    epsilon = 1e-10 * max(1., mfe, mae)
                    row.update(status="completed", terminal_at=pd.Timestamp(a["ends"][hi - 1], tz="UTC"),
                               elapsed_minutes=(a["ends"][hi - 1] - pd.Timestamp(event["entry_at"]).value) / 60e9,
                               crosses_closure=bool(a["closure"][lo:hi].any()),
                               same_session=bool((a["session"][lo:hi].astype(str) == str(event["session"])).all()),
                               mfe=mfe, mae=mae, terminal_delta=delta,
                               favorable=delta > 0, neutral=delta == 0, adverse=delta < 0,
                               mfe_gt_mae=mfe - mae > epsilon, mfe_mae_tie=abs(mfe - mae) <= epsilon)
                    for metric, values in (("mfe", favorable_values), ("mae", adverse_values)):
                        if row[metric] > 0:
                            attained = lo + int(np.argmax(values))
                            row[metric + "_attainment_start"] = pd.Timestamp(a["starts"][attained], tz="UTC")
                            row[metric + "_attainment_end"] = pd.Timestamp(a["ends"][attained], tz="UTC")
                    atr = event.get("entry_atr", np.nan)
                    if pd.notna(atr) and np.isfinite(atr) and atr > 0:
                        for metric in ("mfe", "mae", "terminal_delta"):
                            row[metric + "_atr"] = row[metric] / atr
            rows.append(row)
    if not rows:
        return pd.DataFrame(columns=list(events.columns) + ["horizon", "horizon_minutes", "status", "censor_reason"] + list(NUMERIC_OUTCOMES))
    result = pd.DataFrame(rows)
    for column in ("terminal_at", "mfe_attainment_start", "mfe_attainment_end", "mae_attainment_start", "mae_attainment_end"):
        result[column] = pd.to_datetime(result[column], utc=True)
    if result.duplicated(["event_id", "horizon"]).any():
        raise ValueError("duplicate outcome key")
    return result
