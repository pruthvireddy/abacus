"""Causal 5m cloud mapping and the frozen Stage 1 slow-touch state machine.

Input rosters contain EVERY expected scheduled slot, including invalid slots.
Known closures are omitted by Bhishma; they are never inferred from absent data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

THRESHOLDS = {"ES": 2.4, "GC": 2.0, "NQ": 10.0}
NY = "America/New_York"


def _ordered(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy().reset_index(drop=True)
    for column in ("timestamp", "available_at"):
        result[column] = pd.to_datetime(result[column], utc=True)
    if result.duplicated(["product", "timestamp"]).any():
        raise ValueError("duplicate product/open slots")
    for _, group in result.groupby("product", sort=False):
        if not group.timestamp.is_monotonic_increasing:
            raise ValueError("roster must be chronologically ordered per product")
    return result


def map_features(signal_bars: pd.DataFrame, five_bars: pd.DataFrame,
                 interval_minutes: int) -> pd.DataFrame:
    """Map latest scheduled source, preserving invalid records before the join."""
    if interval_minutes not in (3, 5):
        raise ValueError("Stage 1 permits 3m and 5m candles only")
    signal = _ordered(signal_bars)
    source = _ordered(five_bars)
    out = signal.copy()
    for col in ("ema20", "ema50", "atr14", "consecutive_count"):
        out[col] = np.nan
    for col in ("feature_source_timestamp", "feature_available_at"):
        out[col] = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns, UTC]")
    out["feature_contract"] = None
    out["feature_valid"] = False
    out["feature_reset"] = False
    out["map_reason"] = "no_completed_source"
    out["source_age_minutes"] = np.nan
    out["interval_minutes"] = interval_minutes
    for product, group in signal.groupby("product", sort=False):
        five = source.loc[source["product"].eq(product)].reset_index(drop=True)
        if five.empty:
            continue
        decision = group.timestamp if interval_minutes == 3 else group.available_at
        pos = np.searchsorted(five.available_at.array.asi8, decision.array.asi8, side="right") - 1
        mask = pos >= 0
        target = group.index[mask]
        picked = five.iloc[pos[mask]].copy()
        picked.index = target
        for col in ("ema20", "ema50", "atr14", "consecutive_count", "feature_valid", "feature_reset"):
            out.loc[target, col] = picked[col].to_numpy()
        out.loc[target, "feature_source_timestamp"] = picked.timestamp
        out.loc[target, "feature_available_at"] = picked.available_at
        out.loc[target, "feature_contract"] = picked.contract.to_numpy()
        out.loc[target, "source_age_minutes"] = (decision.loc[target] - picked.available_at).dt.total_seconds() / 60
        same = picked.contract.eq(group.loc[target, "contract"])
        valid = picked.feature_valid.fillna(False).astype(bool) & picked.usable.fillna(False).astype(bool)
        current = picked.timestamp.eq(group.loc[target, "timestamp"]) if interval_minutes == 5 else pd.Series(True, index=target)
        reasons = np.where(~current, "missing_current_source", np.where(~same, "contract_mismatch",
                            np.where(~valid, "invalid_latest_source", "valid")))
        out.loc[target, "map_reason"] = reasons
        out.loc[target, "feature_valid"] = (same & valid & current).to_numpy()
        # Undefined values remain null; the invalid source identity stays visible.
        bad = target[~(same & valid & current).to_numpy()]
        out.loc[bad, ["ema20", "ema50", "atr14"]] = np.nan
    return out


def _strata(events: pd.DataFrame) -> pd.DataFrame:
    local = events.timestamp.dt.tz_convert(NY)
    naive = local.dt.tz_localize(None)
    events["year"] = local.dt.year
    events["month"] = local.dt.strftime("%Y-%m")
    events["week"] = (naive.dt.normalize() - pd.to_timedelta(local.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    events["calendar_date"] = local.dt.strftime("%Y-%m-%d")
    minutes = local.dt.hour * 60 + local.dt.minute
    events["time_stratum"] = np.select(
        [(minutes >= 1080) | (minutes < 180), minutes < 540, minutes < 960],
        ["Asia", "Europe", "US"], default="Late")
    events["hour"] = local.dt.hour
    if "session" not in events:
        events["session"] = events.calendar_date
    events["session"] = events.session.astype(str)
    return events


def generate_events(mapped_bars: pd.DataFrame, interval_minutes: int,
                    thresholds: dict[str, float] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return all scheduled state records and accepted signals before future checks.

    ``technical_candidate`` is a directed geometric touch; ``setup_candidate``
    additionally requires the pre-bar armed state. A rejected penetration consumes
    that setup, regardless of the width gateway or future outcome availability.
    """
    thresholds = THRESHOLDS if thresholds is None else thresholds
    bars = _ordered(mapped_bars)
    bars["interval_minutes"] = interval_minutes
    n = len(bars)
    fields = {"direction": np.zeros(n, dtype=np.int8), "width": np.full(n, np.nan),
              "min_width": np.full(n, np.nan), "episode_id": np.zeros(n, dtype=np.int64),
              "signal_idx": np.zeros(n, dtype=np.int64)}
    for col in ("width_pass", "slow_touch", "fast_touch", "penetration", "full_departure",
                "armed_before", "armed_after", "technical_candidate", "setup_candidate", "accepted"):
        fields[col] = np.zeros(n, dtype=bool)
    reasons, resets = np.full(n, "no_touch", dtype=object), np.full(n, "", dtype=object)
    for product, group in bars.groupby("product", sort=False):
        armed, previous_direction, previous_contract, episode = False, 0, None, 0
        previous_source_reset = None
        threshold = float(thresholds[product])
        epsilon = 1e-10 * max(1., abs(threshold))
        for ordinal, row in enumerate(group.itertuples()):
            i = row.Index
            fields["signal_idx"][i] = ordinal
            fields["min_width"][i] = threshold
            valid = bool(row.usable) and bool(row.feature_valid) and np.isfinite(row.ema20) and np.isfinite(row.ema50)
            direction = (1 if row.ema20 > row.ema50 else -1 if row.ema20 < row.ema50 else 0) if valid else 0
            fields["direction"][i] = direction
            reset_source = getattr(row, "feature_source_timestamp", row.timestamp)
            explicit_reset = bool(row.feature_reset) and reset_source != previous_source_reset
            reset = "invalid_data_or_feature" if not valid else "equality" if direction == 0 else "contract_change" if previous_contract is not None and row.contract != previous_contract else "feature_reset" if explicit_reset else "direction_change" if direction != previous_direction else ""
            if reset:
                armed = False
                resets[i] = reset
            fields["armed_before"][i] = armed
            if valid and direction:
                width = abs(row.ema20 - row.ema50)
                touch = row.low <= row.ema50 <= row.high
                fast_touch = row.low <= row.ema20 <= row.high
                penetration = row.low <= row.ema50 if direction == 1 else row.high >= row.ema50
                departure = row.low > max(row.ema20, row.ema50) if direction == 1 else row.high < min(row.ema20, row.ema50)
                gate = width + epsilon >= threshold
                candidate = bool(touch and armed)
                accepted = candidate and gate
                fields["width"][i] = width
                for col, val in (("width_pass", gate), ("slow_touch", touch), ("fast_touch", fast_touch),
                                 ("penetration", penetration), ("full_departure", departure),
                                 ("technical_candidate", touch), ("setup_candidate", candidate), ("accepted", accepted)):
                    fields[col][i] = val
                reasons[i] = "accepted" if accepted else "not_armed" if touch and not armed else "width_below_minimum" if candidate and not gate else "gap_penetration" if penetration and not touch else "fast_only" if fast_touch and not touch else "no_touch"
                if penetration:
                    armed = False
                if departure:
                    if not armed:
                        episode += 1
                    armed = True
            else:
                reasons[i] = "invalid_data_or_feature" if not valid else "no_direction"
            fields["armed_after"][i] = armed
            fields["episode_id"][i] = episode
            previous_direction, previous_contract = direction, row.contract
            if bool(row.feature_reset):
                previous_source_reset = reset_source
    for key, values in fields.items():
        bars[key] = values
    bars["suppression_reason"], bars["reset_reason"] = reasons, resets
    bars["side"] = np.select([bars.direction.eq(1), bars.direction.eq(-1)], ["Buy", "Sell"], default="None")
    bars["event_id"] = None
    selected = bars.accepted
    if selected.any():
        bars.loc[selected, "event_id"] = (bars.loc[selected, "product"].astype(str) + "|" + str(interval_minutes) + "m|" +
            bars.loc[selected, "contract"].astype(str) + "|" + bars.loc[selected, "timestamp"].map(lambda t: t.isoformat()) + "|" + bars.loc[selected, "side"] + "|slow")
    events = bars.loc[selected].copy()
    events["signal_timestamp"] = events.timestamp
    events["reference_price"] = events.close
    events["entry_at"] = events.available_at
    events["entry_atr"] = events.atr14.where(np.isfinite(events.atr14) & events.atr14.gt(0))
    events = _strata(events)
    events["stage"], events["touch_mode"], events["gate_id"], events["split"] = 1, "slow", "fixed", "development"
    return bars, events.reset_index(drop=True)
