"""Explicitly authorized phase paths, vectorized by accepted event and horizon."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .stage3_masks import boundary, event_masks

NUMERIC = ("mfe", "mae", "terminal_delta", "mfe_atr", "mae_atr", "terminal_delta_atr")
FLAGS = ("favorable", "neutral", "adverse", "mfe_gt_mae", "mfe_mae_tie")
TIMES = ("terminal_at", "mfe_attainment_start", "mfe_attainment_end", "mae_attainment_start", "mae_attainment_end")


def score_period(bars, events, horizons, period, authorization, *, product, interval_minutes, touch_mode, gate):
    """Authorization and endpoint masks are checked before reading future prices.

    Entry acceptance is an input, independently generated for this gateway.
    Missing ATR affects common scoring support only; full absolute paths remain.
    No default period, gateway roster or authorization can expose reserved data.
    """
    if authorization is None or not callable(getattr(authorization, "validate", None)):
        raise ValueError("explicit phase authorization required")
    authorization.validate(period.phase, product, int(interval_minutes), touch_mode, gate["gate_id"])
    if boundary(period.start) < boundary(authorization.start) or boundary(period.end) > boundary(authorization.end):
        raise ValueError("scoring fold is outside authorized phase boundaries")
    if len(bars) and (bars["product"].nunique() != 1 or str(bars["product"].iloc[0]) != product):
        raise ValueError("one product/interval roster per scorer call")
    masks, audit = event_masks(bars, events, horizons, period)
    masks["gate_id"], masks["gate_family"], masks["gate_threshold"] = gate["gate_id"], gate["family"], float(gate["threshold"])
    masks["touch_mode"], masks["stage"], masks["split"] = touch_mode, 3, period.phase
    masks["interval_minutes"] = int(interval_minutes)
    if masks.empty:
        for c in NUMERIC + FLAGS + TIMES + ("status", "censor_reason", "horizon_minutes", "elapsed_minutes", "crosses_closure", "same_session"):
            masks[c] = pd.Series(dtype="object")
        return masks, audit
    masks["horizon_minutes"] = masks.horizon * int(interval_minutes)
    masks["status"] = np.where(masks.score_eligible, "censored", "excluded")
    masks["censor_reason"] = np.where(masks.score_eligible, "data_edge", "")
    for c in NUMERIC + ("elapsed_minutes",):
        masks[c] = np.nan
    for c in FLAGS + ("crosses_closure", "same_session"):
        masks[c] = pd.Series([None] * len(masks), dtype=object)
    for c in TIMES:
        masks[c] = pd.Series(pd.NaT, index=masks.index, dtype="datetime64[ns, UTC]")
    # Never touch any OHLC values for excluded paths. Vector indices below are
    # assembled only from the authorized in-period, post-embargo terminal mask.
    highs = pd.to_numeric(bars.high, errors="coerce").to_numpy(float)
    lows = pd.to_numeric(bars.low, errors="coerce").to_numpy(float)
    close = pd.to_numeric(bars.close, errors="coerce").to_numpy(float)
    usable = bars.usable.fillna(False).to_numpy(bool)
    contracts = bars.contract.to_numpy()
    reasons = bars.quality_reason.astype(str).to_numpy()
    sessions = bars.session.astype(str).to_numpy()
    closures = bars.get("known_closure_before", pd.Series(False, index=bars.index)).fillna(False).to_numpy(bool)
    starts = pd.to_datetime(bars.timestamp, utc=True).array.asi8
    ends = pd.to_datetime(bars.available_at, utc=True).array.asi8
    for h, part in masks.loc[masks.score_eligible].groupby("horizon", sort=True):
        part = part.loc[part.terminal_signal_idx < len(bars)]
        if part.empty:
            continue
        ix = part.index.to_numpy()
        i = part.signal_idx.to_numpy(np.int64)
        path = i[:, None] + np.arange(1, int(h) + 1)[None, :]
        valid = usable[path] & np.isfinite(highs[path]) & np.isfinite(lows[path]) & np.isfinite(close[path])
        same = contracts[path] == part.contract.to_numpy()[:, None]
        bad = ~valid | ~same
        failed = bad.any(axis=1)
        if failed.any():
            first = np.argmax(bad[failed], axis=1)
            slot = path[failed, first]
            invalid = ~valid[failed, first]
            why = np.where(invalid, np.char.add("invalid_future_slot:", reasons[slot].astype(str)), "contract_switch")
            masks.loc[ix[failed], "censor_reason"] = why
        good_ix = ix[~failed]
        if not len(good_ix):
            continue
        p = path[~failed]
        ep = part.loc[good_ix]
        entry = ep.reference_price.to_numpy(float)
        d = ep.direction.to_numpy(int)
        fv = np.where(d[:, None] == 1, highs[p] - entry[:, None], entry[:, None] - lows[p])
        av = np.where(d[:, None] == 1, entry[:, None] - lows[p], highs[p] - entry[:, None])
        mfe, mae = np.maximum(0., fv.max(axis=1)), np.maximum(0., av.max(axis=1))
        delta = d * (close[p[:, -1]] - entry)
        epsilon = 1e-10 * np.maximum(1., np.maximum(mfe, mae))
        masks.loc[good_ix, "status"], masks.loc[good_ix, "censor_reason"] = "completed", ""
        masks.loc[good_ix, "mfe"], masks.loc[good_ix, "mae"], masks.loc[good_ix, "terminal_delta"] = mfe, mae, delta
        masks.loc[good_ix, "terminal_at"] = pd.to_datetime(ends[p[:, -1]], utc=True)
        masks.loc[good_ix, "elapsed_minutes"] = (ends[p[:, -1]] - pd.to_datetime(ep.entry_at, utc=True).array.asi8) / 60e9
        masks.loc[good_ix, "crosses_closure"] = closures[p].any(axis=1)
        masks.loc[good_ix, "same_session"] = (sessions[p] == ep.session.astype(str).to_numpy()[:, None]).all(axis=1)
        for c, v in zip(FLAGS, (delta > 0, delta == 0, delta < 0, mfe - mae > epsilon, np.abs(mfe - mae) <= epsilon)):
            masks.loc[good_ix, c] = v
        for metric, values, excursion in (("mfe", fv, mfe), ("mae", av, mae)):
            attained = p[np.arange(len(p)), np.argmax(values, axis=1)]
            positive = excursion > 0
            masks.loc[good_ix[positive], metric + "_attainment_start"] = pd.to_datetime(starts[attained[positive]], utc=True)
            masks.loc[good_ix[positive], metric + "_attainment_end"] = pd.to_datetime(ends[attained[positive]], utc=True)
        atr = ep.entry_atr.to_numpy(float)
        atr_good = np.isfinite(atr) & (atr > 0)
        for metric, values in (("mfe", mfe), ("mae", mae), ("terminal_delta", delta)):
            masks.loc[good_ix[atr_good], metric + "_atr"] = values[atr_good] / atr[atr_good]
    if masks.duplicated(["gate_id", "event_id", "horizon"]).any():
        raise ValueError("duplicate phase outcome key")
    return masks, audit
