"""Causal pivot/cloud event and one-contract execution model.

No loaders or market-data side effects live here.  ``time``/``open_time`` always
means bar OPEN; a five-minute bar becomes information at open + five minutes.
See protocol-1.0.0.md for the pre-outcome decisions implemented by this module.
"""
from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
TICK = 0.25
POINT_VALUE = 50.0
ROUND_TRIP_FEE = 5.0
FIVE = timedelta(minutes=5)
ONE = timedelta(minutes=1)


def _day(session):
    value = session["date"]
    return date.fromisoformat(value) if isinstance(value, str) else value


def _at(session, hour, minute=0):
    return datetime.combine(_day(session), time(hour, minute), NY)


def _time(bar):
    value = bar.get("time", bar.get("open_time"))
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Bar timestamps must be timezone-aware bar-open datetimes")
    return value.astimezone(NY)


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _ohlc_valid(bar):
    return (all(_finite(bar.get(k)) for k in ("open", "high", "low", "close"))
            and bar["low"] <= min(bar["open"], bar["close"])
            and bar["high"] >= max(bar["open"], bar["close"]))


def _up(value):
    return round(math.ceil((value - 1e-10) / TICK) * TICK, 8)


def _down(value):
    return round(math.floor((value + 1e-10) / TICK) * TICK, 8)


def _touch(low, high, lower, upper, delta):
    return low <= upper + delta and high >= lower - delta


def _separation(lower, upper, cloud_low, cloud_high):
    return max(lower - cloud_high, cloud_low - upper, 0.0)


def _position(price, lower, upper):
    return "below" if price < lower else "above" if price > upper else "inside"


def _signal_bars(session):
    """Require a fixed opening window; no outcome-dependent missing-bar repair."""
    bars = sorted(session.get("bars5", []), key=_time)
    wanted = {_at(session, 9, 25) + FIVE * i for i in range(7)}
    selected = [bar for bar in bars if _time(bar) in wanted]
    if len(selected) != len(wanted) or {_time(b) for b in selected} != wanted:
        return None, "incomplete_signal_data"
    features = ("ema20", "ema50", "atr14", "ema20_lag3", "ema50_lag3")
    if any(not _ohlc_valid(b) for b in selected):
        return None, "invalid_signal_ohlc"
    if any(not all(_finite(b.get(k)) for k in features) or b["atr14"] <= 0 for b in selected):
        return None, "feature_not_ready"
    return selected, None


def _execution_bars(session):
    wanted = {_at(session, 9, 30) + ONE * i for i in range(90)}
    selected = sorted((b for b in session.get("minutes", []) if _time(b) in wanted), key=_time)
    if len(selected) != len(wanted) or {_time(b) for b in selected} != wanted:
        return None, "incomplete_execution_data"
    if any(not _ohlc_valid(b) for b in selected):
        return None, "invalid_execution_ohlc"
    return selected, None


def _opening_tags(session, bars):
    first = bars[1]
    pivot = session["plan"]
    return {
        "opening_pivot_position": _position(first["open"], pivot["pivot_lower"], pivot["pivot_upper"]),
        # These are LAST COMPLETED pre-open cloud values, available at 09:30.
        "opening_cloud_position": _position(first["open"], min(bars[0]["ema20"], bars[0]["ema50"]),
                                            max(bars[0]["ema20"], bars[0]["ema50"])),
    }


def candidates(session, proximity=0.10, stop_buffer=1.0):
    """Return ``(all_candidates, event_ledger)`` before optional filters.

    Primary selection is ``all_candidates[0]``.  The rest remain audit evidence;
    a filter rejection never causes a replacement.  Every episode termination
    consumes prior approach history; only a strictly later completed bar rearms.
    """
    if not _finite(proximity) or proximity < 0 or not _finite(stop_buffer) or stop_buffer <= 0:
        raise ValueError("proximity must be nonnegative and stop_buffer positive")
    day = _day(session).isoformat()
    if session.get("eligible") is False:
        return [], [{"date": day, "event": "session_excluded", "reason": session.get("reason", "input_ineligible")}]
    bars, error = _signal_bars(session)
    if error:
        return [], [{"date": day, "event": "session_excluded", "reason": error}]
    plan = session["plan"]
    lower, upper = plan["pivot_lower"], plan["pivot_upper"]
    if not _finite(lower) or not _finite(upper) or lower > upper:
        raise ValueError("Invalid pivot bounds")
    found, ledger = [], []
    history = [(0, bars[0])]
    episode = None
    episode_number = 0
    tags = _opening_tags(session, bars)
    # The 09:55 bar is retained for confirmation/quality, but a reaction on that
    # bar becomes known at the ineligible 10:00 entry boundary.
    for index, bar in enumerate(bars[1:], 1):
        opened = _time(bar)
        completed = opened + FIVE
        cloud_low, cloud_high = sorted((bar["ema20"], bar["ema50"]))
        terminated = False
        if episode is None and opened < _at(session, 9, 55):
            delta = _up(max(1.0, proximity * bars[index - 1]["atr14"]))
            pivot_touch = _touch(bar["low"], bar["high"], lower, upper, delta)
            if pivot_touch:
                approaches = {}
                for prior_index, prior in history:
                    if prior["close"] <= lower - delta:
                        approaches["short"] = (prior_index, prior)
                    if prior["close"] >= upper + delta:
                        approaches["long"] = (prior_index, prior)
                if len(approaches) == 2:
                    ledger.append({"date": day, "event": "episode_rejected", "reason": "opposite_approach_overlap",
                                   "time": completed, "bar_open_time": opened, "delta": delta})
                    history = []
                    terminated = True
                elif approaches:
                    episode_number += 1
                    direction = next(iter(approaches))
                    approach_index, approach = approaches[direction]
                    episode = {"direction": direction, "start_index": index, "start_time": opened,
                               "number": episode_number, "delta": delta,
                               "first_touch_prior_atr14": bars[index - 1]["atr14"], "pivot_touch": False,
                               "cloud_touch": False, "near": False, "separation": math.inf,
                               "high": -math.inf, "low": math.inf,
                               "approach_time": _time(approach) + FIVE, "approach_close": approach["close"]}
                    ledger.append({"date": day, "event": "episode_started", "reason": "pivot_return",
                                   "episode_number": episode_number, "direction": direction,
                                   "time": completed, "bar_open_time": opened, "delta": delta,
                                   "approach_time": episode["approach_time"]})
                else:
                    ledger.append({"date": day, "event": "return_rejected", "reason": "no_prior_approach",
                                   "time": completed, "bar_open_time": opened, "delta": delta})
        if episode is not None:
            delta = episode["delta"]
            pivot_touch = _touch(bar["low"], bar["high"], lower, upper, delta)
            cloud_touch = _touch(bar["low"], bar["high"], cloud_low, cloud_high, delta)
            separation = _separation(lower, upper, cloud_low, cloud_high)
            episode["pivot_touch"] |= pivot_touch
            episode["cloud_touch"] |= cloud_touch
            if pivot_touch or cloud_touch:
                episode["near"] |= separation <= delta
                episode["separation"] = min(episode["separation"], separation)
            episode["high"] = max(episode["high"], bar["high"])
            episode["low"] = min(episode["low"], bar["low"])
            direction = episode["direction"]
            sign = 1 if direction == "long" else -1
            reaction = (bar["close"] > bar["open"] and bar["close"] > cloud_high) if sign == 1 else (
                bar["close"] < bar["open"] and bar["close"] < cloud_low)
            ingredients = episode["pivot_touch"] and episode["cloud_touch"] and episode["near"]
            if reaction and ingredients and completed < _at(session, 10):
                stop = (_down(min(episode["low"], lower) - stop_buffer) if sign == 1 else
                        _up(max(episode["high"], upper) + stop_buffer))
                ordering = bar["ema20"] > bar["ema50"] if sign == 1 else bar["ema20"] < bar["ema50"]
                slope = (bar["ema20"] > bar["ema20_lag3"] and bar["ema50"] > bar["ema50_lag3"]) if sign == 1 else (
                    bar["ema20"] < bar["ema20_lag3"] and bar["ema50"] < bar["ema50_lag3"])
                span = bar["high"] - bar["low"]
                candidate = {"date": day, "candidate_id": f"{day}:{completed:%H%M}:{direction}:{episode['number']}",
                             "direction": direction, "is_primary": not found,
                             "reaction_index": index, "reaction_time": completed, "reaction_open_time": opened,
                             "episode_start_time": episode["start_time"], "episode_number": episode["number"],
                             "formation_bars": index - episode["start_index"] + 1,
                             "approach_time": episode["approach_time"], "approach_close": episode["approach_close"],
                             "delta": delta, "stop_price": stop, "stop_buffer": stop_buffer, "proximity": proximity,
                             "preopen_atr14": bars[0]["atr14"],
                             "first_touch_prior_atr14": episode["first_touch_prior_atr14"],
                             "pivot_lower": lower, "pivot_upper": upper, "pivot_width": upper - lower,
                             "pivot_kind": "single" if lower == upper else "zone",
                             "pivot_description": plan.get("description", "unknown"),
                             "pivot_label_group": plan.get("label_group", "unknown"),
                             "quoted_contract": plan.get("quoted_contract"),
                             "source_row_ids": plan.get("source_rows", []), "outlook_id": plan.get("outlook_id"),
                             "available_at": plan.get("available_at"),
                             "pivot_cloud_separation": episode["separation"],
                             "reaction_pivot_cloud_separation": separation,
                             "cloud_width_points": cloud_high - cloud_low,
                             "cloud_width_atr": (cloud_high - cloud_low) / bar["atr14"], "atr14": bar["atr14"],
                             "ordering_pass": ordering, "slope_pass": slope,
                             "reaction_ema20": bar["ema20"], "reaction_ema50": bar["ema50"],
                             "reaction_ema20_lag3": bar["ema20_lag3"], "reaction_ema50_lag3": bar["ema50_lag3"],
                             "reaction_open": bar["open"], "reaction_high": bar["high"],
                             "reaction_low": bar["low"], "reaction_close": bar["close"],
                             "reaction_range_points": span,
                             "reaction_body_points": abs(bar["close"] - bar["open"]),
                             "reaction_body_atr": abs(bar["close"] - bar["open"]) / bar["atr14"],
                             "reaction_upper_wick_points": bar["high"] - max(bar["open"], bar["close"]),
                             "reaction_lower_wick_points": min(bar["open"], bar["close"]) - bar["low"], **tags}
                found.append(candidate)
                ledger.append({**candidate, "event": "candidate", "reason": "reaction_completed"})
                episode = None
                history = []
                terminated = True
            elif index - episode["start_index"] == 2 or completed >= _at(session, 10):
                missing = [name for name, present in (("cloud_touch", episode["cloud_touch"]),
                                                       ("pivot_cloud_proximity", episode["near"]),
                                                       ("directional_reaction", reaction)) if not present]
                ledger.append({"date": day, "event": "episode_expired", "reason": "formation_window_expired",
                               "direction": direction, "episode_number": episode["number"],
                               "episode_start_time": episode["start_time"], "time": completed,
                               "missing_ingredients": missing})
                episode = None
                history = []
                terminated = True
        if not terminated:
            history.append((index, bar))
    return found, ledger


def _base(session, candidate, entry_policy, mask, exit_policy, slippage):
    result = dict(candidate or {})
    result.update({"date": _day(session).isoformat(), "candidate_id": (candidate or {}).get("candidate_id"),
                   "candidate": candidate is not None, "trade": False, "entry_policy": entry_policy,
                   "mask": mask, "exit_policy": exit_policy, "slippage_ticks": slippage,
                   "reason": None, "net_dollars": 0.0, "net_r": None,
                   "optimistic_net_dollars": 0.0, "optimistic_net_r": None,
                   "entry_time": None, "entry_price": None, "confirmation_time": None,
                   "confirmation_delay": None, "coincident_entry": None,
                   "initial_risk_points": None, "intended_entry_time": None, "intended_entry_price": None,
                   "exit_time": None, "exit_price": None, "exit_bar_open_time": None,
                   "exit_time_precision": None,
                   "exit_reason": None, "ambiguity": False, "ambiguity_count": 0,
                   "mae_points": None, "mfe_points": None, "holding_minutes": None,
                   "target_price": None, "target_ordinal": None, "target_description": None,
                   "target_source_row_id": None, "target_distance_r": None,
                   "entry_pivot_distance_points": None, "gross_dollars": None, "fees_dollars": 0.0,
                   "excursions_scope": "through_exit_minute_ohlc_envelope"})
    return result


def _unavailable(result, reason):
    result.update(reason=reason, net_dollars=None, optimistic_net_dollars=None)
    return result


def _beyond(bar, candidate):
    if candidate["direction"] == "long":
        return bar["close"] > max(candidate["pivot_upper"], bar["ema20"], bar["ema50"])
    return bar["close"] < min(candidate["pivot_lower"], bar["ema20"], bar["ema50"])


def _stop_touched(bar, stop, sign):
    return bar["low"] <= stop if sign == 1 else bar["high"] >= stop


def _select_target(session, candidate, entry, risk, exit_policy):
    sign = 1 if candidate["direction"] == "long" else -1
    if exit_policy == "fixed_2r":
        return {"price": entry + sign * 2.0 * risk, "ordinal": None, "description": "fixed 2R",
                "source_row_id": None}
    targets = session["plan"].get("targets", {}).get(candidate["direction"], [])
    eligible = []
    for position, target in enumerate(targets[:2], 1):
        lower = target.get("lower", target.get("price"))
        upper = target.get("upper", lower)
        if not _finite(lower) or not _finite(upper) or lower > upper:
            continue
        near = lower if sign == 1 else upper
        if sign * (near - entry) > 0:
            eligible.append({"price": near, "ordinal": target.get("ordinal", position),
                             "description": target.get("description", "unknown"),
                             "source_row_id": target.get("source_row_id")})
    return min(eligible, key=lambda t: sign * (t["price"] - entry)) if eligible else None


def simulate(session, candidate, entry_policy="early", mask="A", exit_policy="fixed_2r", slippage=1):
    """Simulate a selected common candidate, retaining genuine no-trade zeros.

    Missing inputs and unavailable secondary targets have undefined dollars,
    rather than artificial wins, losses, or no-trade zeros. ``slippage`` is ticks
    per market/stop side; the $5 round-trip fee is assessed exactly once.
    """
    if entry_policy not in ("early", "confirmed") or mask not in ("A", "B", "C", "D"):
        raise ValueError("Unknown entry policy or EMA mask")
    if exit_policy not in ("fixed_2r", "verne") or not _finite(slippage) or slippage < 0:
        raise ValueError("Unknown exit policy or invalid slippage ticks")
    result = _base(session, candidate, entry_policy, mask, exit_policy, slippage)
    if session.get("eligible") is False:
        return _unavailable(result, session.get("reason", "input_ineligible"))
    bars, error = _signal_bars(session)
    if error:
        return _unavailable(result, error)
    minutes, error = _execution_bars(session)
    if error:
        return _unavailable(result, error)
    if candidate is None:
        result["reason"] = "no_candidate"
        return result
    if not candidate.get("is_primary", True):
        result["reason"] = "later_candidate_suppressed"
        return result
    if ((mask in ("B", "D") and not candidate["ordering_pass"])
            or (mask in ("C", "D") and not candidate["slope_pass"])):
        result["reason"] = "ema_filter_rejected"
        return result
    sign = 1 if candidate["direction"] == "long" else -1
    stop = candidate["stop_price"]
    reaction_time = candidate["reaction_time"]
    if isinstance(reaction_time, str):
        reaction_time = datetime.fromisoformat(reaction_time).astimezone(NY)
    if reaction_time.tzinfo is None:
        raise ValueError("Candidate reaction timestamp must be timezone aware")
    reaction_bar = next((b for b in bars if _time(b) + FIVE == reaction_time), None)
    if reaction_bar is None:
        return _unavailable(result, "candidate_reaction_bar_missing")
    entry_time = reaction_time
    if entry_policy == "confirmed":
        confirmation = next((b for b in bars if reaction_time <= _time(b) + FIVE <= reaction_time + 3 * FIVE
                             and _time(b) + FIVE < _at(session, 10) and _beyond(b, candidate)), None)
        if confirmation is None:
            # Record structural invalidation even when confirmation never forms.
            wait_end = min(reaction_time + 3 * FIVE, _at(session, 10))
            stopped = next((b for b in minutes if reaction_time <= _time(b) < wait_end
                            and _stop_touched(b, stop, sign)), None)
            result["reason"] = "structural_invalidation" if stopped else "confirmation_expired"
            result["invalidation_time"] = _time(stopped) if stopped else None
            return result
        entry_time = _time(confirmation) + FIVE
        result["confirmation_time"] = entry_time
        result["confirmation_delay"] = int((entry_time - reaction_time) / FIVE)
        result["coincident_entry"] = entry_time == reaction_time
    if not _at(session, 9, 30) <= entry_time < _at(session, 10):
        result["reason"] = "entry_cutoff"
        return result
    for bar in minutes:
        if reaction_time <= _time(bar) < entry_time and _stop_touched(bar, stop, sign):
            result.update(reason="structural_invalidation", invalidation_time=_time(bar))
            return result
    entry_bar = next((b for b in minutes if _time(b) == entry_time), None)
    if entry_bar is None:
        return _unavailable(result, "entry_minute_missing")
    if sign * (entry_bar["open"] - stop) <= 0:
        result["reason"] = "entry_open_beyond_stop"
        return result
    slip = slippage * TICK
    entry = entry_bar["open"] + sign * slip
    risk = sign * (entry - stop)
    if risk <= 0:
        result["reason"] = "nonpositive_initial_risk"
        return result
    result.update(intended_entry_time=entry_time, intended_entry_price=entry)
    target_info = _select_target(session, candidate, entry, risk, exit_policy)
    if target_info is None:
        return _unavailable(result, "target_unavailable")
    target = target_info["price"]
    result.update(trade=True, reason="filled", entry_time=entry_time, entry_price=entry,
                  initial_risk_points=risk, target_price=target, target_ordinal=target_info["ordinal"],
                  target_description=target_info["description"], target_source_row_id=target_info["source_row_id"],
                  target_distance_r=sign * (target - entry) / risk,
                  entry_pivot_distance_points=max(candidate["pivot_lower"] - entry, entry - candidate["pivot_upper"], 0.0),
                  fees_dollars=ROUND_TRIP_FEE)
    low_water, high_water = entry, entry
    exit_price, exit_time, exit_reason, optimistic_price = None, None, None, None
    exit_bar_open_time = None
    exit_time_precision = None
    for bar in minutes:
        opened = _time(bar)
        if opened < entry_time:
            continue
        low_water, high_water = min(low_water, bar["low"]), max(high_water, bar["high"])
        stop_open = sign * (bar["open"] - stop) <= 0
        target_open = sign * (bar["open"] - target) >= TICK - 1e-10
        stop_hit = _stop_touched(bar, stop, sign)
        target_hit = (bar["high"] >= target + TICK - 1e-10 if sign == 1 else
                      bar["low"] <= target - TICK + 1e-10)
        if stop_open:
            exit_price, exit_time, exit_reason = bar["open"] - sign * slip, opened, "stop_gap"
        elif target_open:
            exit_price, exit_time, exit_reason = target, opened, "target"
        elif stop_hit:
            exit_price, exit_time, exit_reason = stop - sign * slip, opened + ONE, "stop"
            if target_hit:
                result.update(ambiguity=True, ambiguity_count=1)
                optimistic_price = target
        elif target_hit:
            exit_price, exit_time, exit_reason = target, opened + ONE, "target"
        elif opened == _at(session, 10, 59):
            exit_price, exit_time, exit_reason = bar["close"] - sign * slip, _at(session, 11), "time"
        if exit_price is not None:
            exit_bar_open_time = opened
            exit_time_precision = ("11:00_flatten" if exit_reason == "time" else
                                   "bar_open" if exit_time == opened else "bar_completion")
            break
    if exit_price is None:
        return _unavailable(result, "execution_exit_missing")
    gross = sign * (exit_price - entry) * POINT_VALUE
    net = gross - ROUND_TRIP_FEE
    optimistic_net = sign * ((optimistic_price if optimistic_price is not None else exit_price) - entry) * POINT_VALUE - ROUND_TRIP_FEE
    result.update(exit_time=exit_time, exit_price=exit_price, exit_reason=exit_reason,
                  exit_bar_open_time=exit_bar_open_time, exit_time_precision=exit_time_precision,
                  gross_dollars=gross, net_dollars=net, net_r=net / (risk * POINT_VALUE),
                  optimistic_net_dollars=optimistic_net, optimistic_net_r=optimistic_net / (risk * POINT_VALUE),
                  mae_points=max(entry - low_water, 0.0) if sign == 1 else max(high_water - entry, 0.0),
                  mfe_points=max(high_water - entry, 0.0) if sign == 1 else max(entry - low_water, 0.0),
                  holding_minutes=(exit_time - entry_time).total_seconds() / 60.0)
    return result
