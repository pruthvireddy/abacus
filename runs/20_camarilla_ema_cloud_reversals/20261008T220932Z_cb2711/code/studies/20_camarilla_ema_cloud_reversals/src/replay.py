"""One-minute barrier replay and complete one-position policy schedules."""
import numpy as np
import pandas as pd
from .calendar import stamp, week
from .core import MINUTE, tick_round, tick_valid
from .spec import PRODUCTS, window

def replay(event, minutes, tick, multiplier, fee=10, slip=1, target="3R", delay=0, touch=False, order="stop_first", end_window=690):
    d = int(event["direction"])
    ts = int(event["entry_ts"]) + delay * MINUTE
    if int(event["entry_minute_NY"]) + delay >= end_window:
        return {"entered": False, "reason": "delayed_entry_outside_window"}
    timeline = minutes["ts"]
    start = np.searchsorted(timeline, ts)
    if start == len(timeline) or timeline[start] != ts:
        return {"entered": False, "reason": "entry_open_absent"}
    raw = float(minutes["open"][start])
    stop = tick_round(float(event["confirmation_low"] if d > 0 else event["confirmation_high"]) - d*tick, tick, -d)
    fill = raw + d*slip*tick
    if not tick_valid(raw, tick) or not tick_valid(fill, tick):
        return {"entered": False, "reason": "off_tick_entry"}
    if d*(raw-stop) <= 0 or d*(fill-stop) <= 0:
        return {"entered": False, "reason": "invalid_risk_open_beyond_stop"}
    risk = d*(fill-stop)
    if target in ("3R", "2R"):
        goal = fill + d*float(target[0])*risk
    elif str(event["pair"]) == "4":
        goal = float(event["prior_close"]) - d*(1.1/4)*float(event["prior_range"])
    else:
        goal = float(event["opposite_pivot"])
    goal = tick_round(goal, tick, d)
    if not np.isfinite(goal) or d*(goal-fill) <= 0:
        return {"entered": False, "reason": "pivot_target_not_favorable"}
    deadline = stamp(event["day"], 960)
    end = np.searchsorted(timeline, deadline)
    times = timeline[start:end]
    o,h,l = (minutes[c][start:end] for c in ("open", "high", "low"))
    expected = ts + np.arange(len(times))*MINUTE
    missing = np.flatnonzero(times != expected)
    valid = minutes["valid"][start:end]
    invalid = np.flatnonzero(~valid)
    cut = min([len(times), *([int(missing[0])] if len(missing) else []), *([int(invalid[0])] if len(invalid) else [])])
    # An absent tail is unresolved too, unless a barrier already executed earlier.
    fully_observed = cut == len(times) and len(times) == (deadline-ts)//MINUTE
    o,h,l,times = o[:cut],h[:cut],l[:cut],times[:cut]
    hit_stop = l <= stop if d>0 else h >= stop
    limit_threshold = goal + d*(0 if touch else tick)
    hit_target = h >= limit_threshold - 1e-8 if d>0 else l <= limit_threshold + 1e-8
    hits = np.flatnonzero(hit_stop | hit_target)
    base = {"entered": True, "reason": "", "entry_fill": fill, "raw_entry": raw, "entry_actual_ts": ts, "stop": stop, "target_price": goal, "risk_points": risk, "risk_USD": risk*multiplier, "ambiguous": False}
    if len(hits):
        k = int(hits[0])
        stop_gap = d*(o[k]-stop) <= 0
        limit_gap = d*(o[k]-limit_threshold) >= -1e-8
        ambiguous = bool(hit_stop[k] and hit_target[k] and not stop_gap and not limit_gap)
        stop_chosen = bool(stop_gap or (hit_stop[k] and not limit_gap and (not hit_target[k] or order == "stop_first")))
        if stop_chosen:
            price = (min(stop, o[k]) if d>0 else max(stop,o[k])) - d*slip*tick
            reason = "stop_gap" if stop_gap else "stop"
        else:
            price, reason = goal, "target"
        exit_ts = int(times[k])
        base.update(ambiguous=ambiguous)
    elif fully_observed and end < len(timeline) and timeline[end] == deadline and minutes["valid"][end]:
        price = float(minutes["open"][end])-d*slip*tick
        reason, exit_ts = "timeout", deadline
    else:
        return {**base, "reason": "unresolved_missing_path_or_1600_open", "exit_ts": deadline, "net_R": np.nan, "net_USD": np.nan, "gross_USD": np.nan, "holding_minutes": (deadline-ts)//MINUTE}
    gross = d*(price-fill)*multiplier
    return {**base, "reason": reason, "exit_fill": price, "exit_ts": exit_ts, "gross_USD": gross, "net_USD": gross-fee, "net_R": (gross-fee)/(risk*multiplier), "holding_minutes": (exit_ts-ts)//MINUTE}

def minute_arrays(frame):
    return {c: frame[c].to_numpy() for c in ("ts", "open", "high", "low", "close", "valid")}

def policy(events, roster, minutes, product, pair, mode, extension="core", fee=10, slip=1, target="3R", delay=0, touch=False, order="stop_first", window_name="main", cache=None):
    tick,multiplier = PRODUCTS[product]
    a,b = window(product, window_name)
    trades, sessions = [], []
    groups = {d:g for d,g in events.groupby("day", sort=False)}
    for r in roster.itertuples():
        busy = -1
        day_net, day_dollars, unresolved, ambiguous, entered, skips, cancels = 0.,0.,False,0,0,0,0
        day_trades = []
        for e in groups.get(r.day, events.iloc[:0]).to_dict("records"):
            if int(e["entry_ts"]) + delay*MINUTE < busy:
                skips += 1
                continue
            key = (e["event_id"], slip, target, delay, touch, order, b)
            if cache is not None and key in cache:
                out = dict(cache[key])
                if out.get("entered") and np.isfinite(out.get("gross_USD", np.nan)):
                    out["net_USD"] = out["gross_USD"] - fee
                    out["net_R"] = out["net_USD"] / out["risk_USD"]
            else:
                out = replay(e, minutes, tick, multiplier, fee, slip, target, delay, touch, order, b)
                if cache is not None:
                    cache[key] = dict(out)
            trade = {"event_id": e["event_id"], "day": r.day, "week": week(r.day), "split": r.split, "product": product, "pair": pair, "mode": mode, "extension": extension, "fee_USD": fee, "slippage_ticks": slip, "target": target, "delay": delay, "touch": touch, "order_assumption": order, "window": window_name, **out}
            trades.append(trade)
            day_trades.append(trade)
            if out["entered"]:
                entered += 1
                ambiguous += int(out["ambiguous"])
                busy = int(out["exit_ts"]) + MINUTE
                if np.isfinite(out["net_R"]):
                    day_net += out["net_R"]
                    day_dollars += out["net_USD"]
                else:
                    unresolved = True
            else:
                cancels += 1
        # Later signal-window missingness cannot establish a zero-opportunity day.
        complete_window = r.session_window_complete if window_name == "session" else r.signal_window_complete
        if not complete_window:
            unresolved = True
        sessions.append({"day": r.day, "week": week(r.day), "year": r.year, "split": r.split, "product": product, "pair": pair, "mode": mode, "extension": extension, "fee_USD": fee, "slippage_ticks": slip, "target": target, "delay": delay, "touch": touch, "order_assumption": order, "window": window_name, "entered": entered, "ambiguous": ambiguous, "occupancy_skips": skips, "cancellations": cancels, "unresolved": unresolved, "net_R": np.nan if unresolved else day_net, "net_USD": np.nan if unresolved else day_dollars, "observed_resolved_trade_net_R": day_net})
    return pd.DataFrame(trades), pd.DataFrame(sessions)
