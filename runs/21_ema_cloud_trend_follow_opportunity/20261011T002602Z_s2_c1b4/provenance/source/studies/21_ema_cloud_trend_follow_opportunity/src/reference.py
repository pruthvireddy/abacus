"""Independent scalar definitions used for scientific reconciliation.

This module imports no study engine/outcome/statistical implementation and uses
explicit scalar loops rather than their NumPy slices or state arrays.
"""
from __future__ import annotations

import math
import pandas as pd


def scalar_acceptance(mapped_bars, interval_minutes, thresholds=None, development_only=False):
    thresholds = {"ES": 2.4, "GC": 2., "NQ": 10.} if thresholds is None else thresholds
    result = []
    for product, group in mapped_bars.groupby("product", sort=False):
        ready = False
        last_direction, last_contract, last_reset_source = 0, None, None
        for bar in group.to_dict("records"):
            valid = bar["usable"] and bar["feature_valid"] and math.isfinite(bar["ema20"]) and math.isfinite(bar["ema50"])
            d = 1 if valid and bar["ema20"] > bar["ema50"] else -1 if valid and bar["ema20"] < bar["ema50"] else 0
            reset_source = bar.get("feature_source_timestamp", bar["timestamp"])
            reset = bool(bar["feature_reset"]) and reset_source != last_reset_source
            if not valid or not d or d != last_direction or (last_contract is not None and last_contract != bar["contract"]) or reset:
                ready = False
            if valid and d:
                selected = bar["ema50"]
                touch = bar["low"] <= selected and bar["high"] >= selected
                threshold = thresholds[product]
                width_valid = abs(bar["ema20"] - bar["ema50"]) + 1e-10 * max(1., abs(threshold)) >= threshold
                if ready and touch and width_valid:
                    side = "Buy" if d == 1 else "Sell"
                    if not development_only or 2018 <= pd.Timestamp(bar["timestamp"]).tz_convert("America/New_York").year <= 2020:
                        result.append(f"{product}|{interval_minutes}m|{bar['contract']}|{pd.Timestamp(bar['timestamp']).isoformat()}|{side}|slow")
                if (d == 1 and bar["low"] <= selected) or (d == -1 and bar["high"] >= selected):
                    ready = False
                if (d == 1 and bar["low"] > max(bar["ema20"], bar["ema50"])) or (d == -1 and bar["high"] < min(bar["ema20"], bar["ema50"])):
                    ready = True
            last_direction, last_contract = d, bar["contract"]
            if bar["feature_reset"]:
                last_reset_source = reset_source
    return result


def scalar_outcomes(bars, events, horizons, endpoint="2021-01-01", roster_end_is_endpoint=False):
    end = pd.Timestamp(endpoint)
    end = end.tz_localize("America/New_York").tz_convert("UTC") if end.tzinfo is None else end.tz_convert("UTC")
    rosters = {p: f.to_dict("records") for p, f in bars.groupby("product", sort=False)}
    output = []
    for event in events.to_dict("records"):
        roster = rosters[event["product"]]
        for h in sorted(set(horizons)):
            row = dict(event_id=event["event_id"], horizon=h, status="censored", censor_reason="", mfe=None, mae=None, terminal_delta=None,
                       mfe_atr=None, mae_atr=None, terminal_delta_atr=None, favorable=None, neutral=None, adverse=None,
                       mfe_gt_mae=None, mfe_mae_tie=None, mfe_attainment_start=pd.NaT, mae_attainment_start=pd.NaT)
            i = int(event["signal_idx"])
            required = roster[i + 1:i + h + 1]
            if len(required) != h:
                row["censor_reason"] = "development_endpoint" if roster_end_is_endpoint else "data_edge"
            elif any(pd.Timestamp(bar["available_at"]) > end for bar in required):
                row["censor_reason"] = "development_endpoint"
            else:
                for bar in required:
                    if not bar["usable"] or not all(pd.notna(bar[x]) and math.isfinite(float(bar[x])) for x in ("high", "low", "close")):
                        row["censor_reason"] = "invalid_future_slot:" + str(bar["quality_reason"])
                        break
                    if bar["contract"] != event["contract"]:
                        row["censor_reason"] = "contract_switch"
                        break
                if not row["censor_reason"]:
                    best, worst = 0., 0.
                    entry, d = float(event["reference_price"]), int(event["direction"])
                    for bar in required:
                        favorable = float(bar["high"]) - entry if d == 1 else entry - float(bar["low"])
                        adverse = entry - float(bar["low"]) if d == 1 else float(bar["high"]) - entry
                        if favorable > best:
                            best, row["mfe_attainment_start"] = favorable, bar["timestamp"]
                        if adverse > worst:
                            worst, row["mae_attainment_start"] = adverse, bar["timestamp"]
                    delta = d * (float(required[-1]["close"]) - entry)
                    epsilon = 1e-10 * max(1., best, worst)
                    row.update(status="completed", mfe=best, mae=worst, terminal_delta=delta,
                               favorable=delta > 0, neutral=delta == 0, adverse=delta < 0,
                               mfe_gt_mae=best - worst > epsilon, mfe_mae_tie=abs(best - worst) <= epsilon)
                    atr = event.get("entry_atr")
                    if atr is not None and pd.notna(atr) and atr > 0:
                        row.update(mfe_atr=best / atr, mae_atr=worst / atr, terminal_delta_atr=delta / atr)
            output.append(row)
    return pd.DataFrame(output)


def reconcile_scalar(bars, mapped_bars, events, outcomes, interval_minutes, horizons, roster_end_is_endpoint=False):
    """Return explicit checked population counts, raise on any mismatch."""
    accepted = scalar_acceptance(mapped_bars, interval_minutes, development_only=True)
    if accepted != events.event_id.tolist():
        raise AssertionError("independent scalar signal IDs differ")
    ref = scalar_outcomes(bars, events, horizons, roster_end_is_endpoint=roster_end_is_endpoint)
    cols = list(ref.columns)
    left, right = ref.set_index(["event_id", "horizon"]), outcomes.set_index(["event_id", "horizon"])
    if not left.index.equals(right.index):
        raise AssertionError("independent scalar outcome keys differ")
    numeric = ("mfe", "mae", "terminal_delta", "mfe_atr", "mae_atr", "terminal_delta_atr")
    for col in cols:
        if col in ("event_id", "horizon"):
            continue
        for a, b in zip(left[col], right[col]):
            if pd.isna(a) and pd.isna(b):
                continue
            if col in numeric:
                if not math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12):
                    raise AssertionError(f"independent scalar {col} differs")
            elif a != b:
                raise AssertionError(f"independent scalar {col} differs")
    return dict(accepted_events_checked=len(events), outcome_rows_checked=len(ref), scalar_agreement=True)
