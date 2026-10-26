"""Independent Stage 2 streams around the unchanged Stage 1 slow engine.

The full causal roster is processed before any development/outcome restriction.
Each selected EMA owns its state; membership and future labels are separate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import THRESHOLDS, _ordered, _strata, generate_events


def _fast_stream(mapped_bars: pd.DataFrame, interval_minutes: int,
                 thresholds: dict[str, float]) -> tuple[pd.DataFrame, pd.DataFrame]:
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
                fast_touch = row.low <= row.ema20 <= row.high
                slow_touch = row.low <= row.ema50 <= row.high
                penetration = row.low <= row.ema20 if direction == 1 else row.high >= row.ema20
                departure = row.low > max(row.ema20, row.ema50) if direction == 1 else row.high < min(row.ema20, row.ema50)
                gate = width + epsilon >= threshold
                candidate = bool(fast_touch and armed)
                accepted = candidate and gate
                fields["width"][i] = width
                for col, val in (("width_pass", gate), ("slow_touch", slow_touch), ("fast_touch", fast_touch),
                                 ("penetration", penetration), ("full_departure", departure),
                                 ("technical_candidate", fast_touch), ("setup_candidate", candidate), ("accepted", accepted)):
                    fields[col][i] = val
                reasons[i] = "accepted" if accepted else "not_armed" if fast_touch and not armed else "width_below_minimum" if candidate and not gate else "gap_penetration" if penetration and not fast_touch else "slow_only" if slow_touch and not fast_touch else "no_touch"
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
            bars.loc[selected, "contract"].astype(str) + "|" + bars.loc[selected, "timestamp"].map(lambda t: t.isoformat()) + "|" + bars.loc[selected, "side"] + "|fast")
    events = bars.loc[selected].copy()
    events["signal_timestamp"] = events.timestamp
    events["reference_price"] = events.close
    events["entry_at"] = events.available_at
    events["entry_atr"] = events.atr14.where(np.isfinite(events.atr14) & events.atr14.gt(0))
    events = _strata(events)
    events["stage"], events["touch_mode"], events["gate_id"], events["split"] = 2, "fast", "fixed", "development"
    return bars, events.reset_index(drop=True)


def generate_streams(mapped_bars: pd.DataFrame, interval_minutes: int,
                     thresholds: dict[str, float] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return both complete technical rosters and full causal accepted streams.

    Slow scientific values and IDs are supplied by the unchanged inherited
    engine. Fast never reads its decisions, armed state, or accepted list.
    ``episode_id`` remains each branch's inherited arm episode; the separate
    geometric ``shared_episode_id`` is attached only by the membership module.
    """
    if interval_minutes not in (3, 5):
        raise ValueError("Stage 2 permits 3m and 5m candles only")
    thresholds = THRESHOLDS if thresholds is None else thresholds
    slow_technical, slow_events = generate_events(mapped_bars, interval_minutes, thresholds)
    fast_technical, fast_events = _fast_stream(mapped_bars, interval_minutes, thresholds)
    for frame in (slow_technical, slow_events):
        frame["touch_mode"], frame["selected_ema"] = "slow", "ema50"
    for frame in (fast_technical, fast_events):
        frame["touch_mode"], frame["selected_ema"] = "fast", "ema20"
    slow_events["stage"] = 2
    technical = pd.concat([fast_technical, slow_technical], ignore_index=True).sort_values(
        ["product", "timestamp", "touch_mode"], kind="stable").reset_index(drop=True)
    events = pd.concat([fast_events, slow_events], ignore_index=True).sort_values(
        ["product", "timestamp", "touch_mode"], kind="stable").reset_index(drop=True)
    if events.event_id.duplicated().any():
        raise ValueError("branch event ID collision")
    return technical, events
