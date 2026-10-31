"""Completed-bar descriptive pivot events and paths; no execution simulation."""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import math
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo


NY = ZoneInfo("America/New_York")
UTC = timezone.utc
SECTIONS = (("opening_range", "09:30", "10:30"),
            ("new_york_am", "10:30", "12:30"),
            ("new_york_pm", "12:30", "16:00"))
TABLES = ("daily", "sections", "snapshots", "price_events", "ema_events", "outcomes")
CONTEXT_FIELDS = ("cloud_order", "price_cloud_location", "pivot_cloud_location",
                  "vwap_side_relative_pivot", "price_side_relative_vwap",
                  "ema6_slope_15m", "ema20_slope_15m", "ema50_slope_15m", "vwap_slope_15m",
                  "cloud_width_change_15m")


class IneligibleDay(ValueError):
    """Declared source-independent quality exclusion, not a software error."""

    def __init__(self, codes: Iterable[str]):
        self.codes = sorted(set(codes))
        super().__init__(";".join(self.codes))


def _dt(value: Any) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("bar timestamps must be timezone-aware")
    return result.astimezone(UTC)


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def strict_side(value: Any, pivot: Any) -> int | None:
    x, p = _number(value), _number(pivot)
    return None if x is None or p is None else 1 if x > p else -1 if x < p else 0


def transition(previous: int | None, raw_side: int | None) -> tuple[int | None, int | None]:
    """Return remembered strict side and actual transition direction.

    Unknown clears history. Equality is explicitly observed and retains the
    last strict side; a first strict observation initializes without crossing.
    """
    if raw_side is None:
        return None, None
    if raw_side == 0:
        return previous, None
    return raw_side, raw_side if previous in (-1, 1) and previous != raw_side else None


def _clock(day: str, value: str) -> datetime:
    return datetime.combine(date.fromisoformat(day), time.fromisoformat(value), NY).astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _records(frame: Any, contract: str, interval: int) -> list[dict]:
    raw = frame.to_dict("records") if hasattr(frame, "to_dict") else list(frame)
    result = []
    seen = set()
    for value in raw:
        row = dict(value)
        if row.get("contract") is None:
            raise IneligibleDay(["native_contract_missing"])
        if row.get("contract") != contract:
            raise ValueError("analyze_day cannot mix delivery contracts")
        row["open_time"], row["close_time"] = _dt(row["open_time"]), _dt(row["close_time"])
        if row["close_time"] - row["open_time"] != timedelta(minutes=interval):
            raise ValueError("bar duration differs from its native interval")
        local = row["open_time"].astimezone(NY)
        if local.second or local.microsecond or (local.hour * 60 + local.minute) % interval:
            raise ValueError("native bars must follow fixed New York clock boundaries")
        if row["open_time"] in seen:
            raise ValueError("duplicate native bar opening timestamp")
        seen.add(row["open_time"])
        result.append(row)
    return sorted(result, key=lambda row: row["open_time"])


def _usable(row: Mapping | None) -> bool:
    return row is not None and bool(row.get("usable", False))


class _Series:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.closes = [row["close_time"] for row in rows]
        self.by_open = {row["open_time"]: row for row in rows}
        self.by_close = {row["close_time"]: row for row in rows}

    def asof(self, at: datetime) -> dict | None:
        index = bisect_right(self.closes, at) - 1
        return self.rows[index] if index >= 0 else None


def _feature(row: Mapping | None, name: str, ready: str) -> float | None:
    return _number(row.get(name)) if _usable(row) and bool(row.get(ready, False)) else None


def _location(value: float | None, lower: float | None, upper: float | None) -> str:
    if value is None or lower is None or upper is None:
        return "unknown"
    return "below" if value < lower else "above" if value > upper else "inside"


def _snapshot(at: datetime, *, label: str, day: str, contract: str, pivot: float,
              minute: _Series, three: _Series, five: _Series,
              opening_price: bool = False) -> dict:
    one, fast, slow = minute.by_close.get(at), three.asof(at), five.asof(at)
    if fast and at - fast["close_time"] >= timedelta(minutes=3):
        fast = None
    if slow and at - slow["close_time"] >= timedelta(minutes=5):
        slow = None
    price_row = minute.by_open.get(at) if opening_price else one
    price = _number(price_row.get("open" if opening_price else "close")) if _usable(price_row) else None
    ema6 = _feature(fast, "ema6", "ema6_ready")
    ema20, ema50 = (_feature(slow, key, "cloud_ready") for key in ("ema20", "ema50"))
    vwap = _feature(one, "vwap", "vwap_valid")
    lower, upper = (min(ema20, ema50), max(ema20, ema50)) if ema20 is not None and ema50 is not None else (None, None)
    spread = ema20 - ema50 if lower is not None else None
    values = {"ema6": (ema6, fast, three, "ema6_ready"),
              "ema20": (ema20, slow, five, "cloud_ready"),
              "ema50": (ema50, slow, five, "cloud_ready"),
              "vwap": (vwap, one, minute, "vwap_valid")}
    slopes = {}
    for name, (value, row, series, ready) in values.items():
        lag = series.by_close.get(row["close_time"] - timedelta(minutes=15)) if row else None
        before = _feature(lag, name, ready)
        slopes[f"{name}_slope_15m"] = value - before if value is not None and before is not None else None
    old_slow = five.by_close.get(slow["close_time"] - timedelta(minutes=15)) if slow else None
    old20, old50 = (_feature(old_slow, name, "cloud_ready") for name in ("ema20", "ema50"))
    slopes["cloud_width_change_15m"] = abs(spread) - abs(old20 - old50) if spread is not None and old20 is not None and old50 is not None else None
    return {
        "snapshot_id": f"{day}:{contract}:{label}", "session_date": day, "contract": contract,
        "snapshot_label": label, "snapshot_at": _iso(at), "pivot": pivot,
        "price": price, "price_source_at": _iso(at if opening_price and price_row else price_row["close_time"] if price_row else None),
        "ema6": ema6, "ema20": ema20, "ema50": ema50, "vwap": vwap,
        "ema6_source_at": _iso(fast["close_time"] if fast else None),
        "cloud_source_at": _iso(slow["close_time"] if slow else None),
        "vwap_source_at": _iso(one["close_time"] if one else None),
        "cloud_lower": lower, "cloud_upper": upper,
        "cloud_spread": spread, "cloud_width": abs(spread) if spread is not None else None,
        "cloud_order": "unknown" if spread is None else "bullish" if spread > 0 else "bearish" if spread < 0 else "flat",
        "price_cloud_location": _location(price, lower, upper),
        "pivot_cloud_location": _location(pivot, lower, upper),
        "price_side_relative_pivot": strict_side(price, pivot),
        "ema6_side_relative_pivot": strict_side(ema6, pivot),
        "vwap_side_relative_pivot": strict_side(vwap, pivot),
        "price_side_relative_vwap": strict_side(price, vwap),
        "price_minus_pivot": price - pivot if price is not None else None,
        "ema6_minus_pivot": ema6 - pivot if ema6 is not None else None,
        "vwap_minus_pivot": vwap - pivot if vwap is not None else None,
        "cloud_lower_minus_pivot": lower - pivot if lower is not None else None,
        "cloud_upper_minus_pivot": upper - pivot if upper is not None else None,
        "price_minus_vwap": price - vwap if price is not None and vwap is not None else None,
        "price_minus_ema6": price - ema6 if price is not None and ema6 is not None else None,
        **slopes,
    }


def _context(snapshot: Mapping) -> dict:
    return {key: snapshot[key] for key in CONTEXT_FIELDS}


def _forward(event: Mapping, *, observed: datetime, reference: float,
             end: datetime, horizon: str, minute: _Series, day_end: datetime,
             event_type: str, context: Mapping) -> dict:
    elapsed = (end - observed).total_seconds() / 60
    reason = "reference_price_unavailable" if _number(reference) is None else "outside_rth" if end > day_end else "no_followthrough_interval" if elapsed <= 0 else None
    path = []
    if reason is None:
        current = observed
        while current < end:
            row = minute.by_open.get(current)
            if not _usable(row) or any(_number(row.get(key)) is None for key in ("high", "low", "close")):
                reason = "missing_or_unusable_forward_minute"
                break
            path.append(row)
            current += timedelta(minutes=1)
    valid = reason is None and bool(path)
    direction = event["direction"]
    displacement = direction * (float(path[-1]["close"]) - reference) if valid else None
    favorable = max(0., max(direction * (float(row["high"] if direction == 1 else row["low"]) - reference) for row in path)) if valid else None
    adverse = max(0., max(-direction * (float(row["low"] if direction == 1 else row["high"]) - reference) for row in path)) if valid else None
    result = {
        "outcome_id": f"{event['event_id']}:{event_type}:{horizon}",
        "event_id": event["event_id"], "event_type": event_type,
        "feature_snapshot_id": event.get("confirmation_feature_snapshot_id") if event_type == "ema_confirmation" else event.get("feature_snapshot_id"),
        "session_date": event["session_date"], "contract": event["contract"],
        "direction": direction, "section": event["section"],
        "origin_section": event.get("origin_section", event["section"]),
        "information_section": event.get("information_section", event["section"]),
        "first_per_day": event["first_per_day"], "first_per_section": event["first_per_section"],
        "origin_first_per_day": event.get("origin_first_per_day", event["first_per_day"]),
        "origin_first_per_section": event.get("origin_first_per_section", event["first_per_section"]),
        "ema_state_at_cross": event.get("ema_state_at_cross"),
        "reference_at": _iso(observed), "reference_price": reference,
        "endpoint_at": _iso(end), "horizon": horizon, "valid": valid,
        "unknown_reason": reason, "elapsed_minutes": elapsed if elapsed > 0 else None,
        "displacement_points": displacement, "favorable_excursion_points": favorable,
        "adverse_excursion_points": adverse, **_context(context),
    }
    for threshold in (5, 10, 20):
        result[f"favorable_reach_{threshold}"] = favorable >= threshold if favorable is not None else None
        result[f"adverse_reach_{threshold}"] = adverse >= threshold if adverse is not None else None
    return result


def _event_outcomes(event: Mapping, observed: datetime, reference: float, minute: _Series,
                    section_end: datetime, day_end: datetime, event_type: str,
                    context: Mapping) -> list[dict]:
    endpoints = [(f"{n}m", observed + timedelta(minutes=n)) for n in (15, 30, 60)]
    endpoints.extend((("section_end", section_end), ("day_end", day_end)))
    return [_forward(event, observed=observed, reference=reference, end=end, horizon=name,
                     minute=minute, day_end=day_end, event_type=event_type, context=context)
            for name, end in endpoints]


def _retest(event: Mapping, rows: list[dict], pivot: float, day_end: datetime) -> dict:
    observed = _dt(event["observed_at"])
    requested_end = observed + timedelta(minutes=30)
    end = min(requested_end, day_end)
    by_open = {row["open_time"]: row for row in rows}
    whole_window = requested_end <= day_end
    check = observed
    while whole_window and check < requested_end:
        item = by_open.get(check)
        whole_window = _usable(item) and all(_number(item.get(key)) is not None for key in ("low", "high", "close"))
        check += timedelta(minutes=3)
    expected = observed
    touch = None
    gap = False
    for row in rows:
        if row["open_time"] < observed or row["close_time"] > end:
            continue
        if row["open_time"] != expected or not _usable(row) or any(_number(row.get(k)) is None for k in ("low", "high", "close")):
            gap = True
            break
        expected = row["close_time"]
        if float(row["low"]) <= pivot <= float(row["high"]):
            touch = row
            break
    if touch:
        side = strict_side(touch["close"], pivot)
        return {"retest_found": True, "retest_censored": False,
                "retest_at": _iso(touch["close_time"]), "retest_bar_open": _iso(touch["open_time"]),
                "retest_minutes": (touch["close_time"] - observed).total_seconds() / 60,
                "retest_close_class": "equal" if side == 0 else "hold" if side == event["direction"] else "failed",
                "retest_observed_minutes": (touch["close_time"] - observed).total_seconds() / 60,
                "retest_window_complete": whole_window,
                "retest_unknown_reason": None}
    complete = not gap and expected == end and requested_end <= day_end
    return {"retest_found": False if complete else None, "retest_censored": not complete,
            "retest_at": None, "retest_bar_open": None, "retest_minutes": None,
            "retest_close_class": None,
            "retest_window_complete": whole_window,
            "retest_observed_minutes": max(0., (expected - observed).total_seconds() / 60),
            "retest_unknown_reason": None if complete else "missing_or_unusable_retest_bar" if gap or expected < end else "right_censored_at_rth_end"}


def _finish_episode(event: dict, endpoint: datetime, *, returned: bool,
                    reason: str, minute: _Series, pivot: float) -> None:
    start = _dt(event["observed_at"])
    event.update(returned_at=_iso(endpoint) if returned else None,
                 return_censored=not returned, episode_end_at=_iso(endpoint),
                 episode_end_reason=reason,
                 episode_duration_minutes=(endpoint - start).total_seconds() / 60,
                 return_time_minutes=(endpoint - start).total_seconds() / 60 if returned else None)
    path = []
    current = start
    while current < endpoint:
        row = minute.by_open.get(current)
        if not _usable(row) or any(_number(row.get(key)) is None for key in ("high", "low")):
            path = None
            break
        path.append(row)
        current += timedelta(minutes=1)
    initial = event["direction"] * (event["reference_price"] - pivot)
    event["episode_penetration_points"] = max(0., initial, max((event["direction"] * (float(row["high"] if event["direction"] == 1 else row["low"]) - pivot) for row in path), default=0.)) if path is not None else None
    event["price_movement_to_confirmation_points"] = event["direction"] * (event["confirmation_price"] - event["reference_price"]) if event["confirmation_price"] is not None else None
    if event["confirmation_at"] is not None:
        confirmation = _dt(event["confirmation_at"])
        before = [row for row in (path or []) if row["open_time"] < confirmation]
        event["penetration_before_confirmation_points"] = max(0., initial, max((event["direction"] * (float(row["high"] if event["direction"] == 1 else row["low"]) - pivot) for row in before), default=0.)) if path is not None else None
    else:
        event["penetration_before_confirmation_points"] = None
    if reason == "data_gap":
        label = "unknown_after_data_gap"
    elif event["confirmation_at"] is None:
        label = "returned_without_new_ema_cross" if returned else "unfinished_unconfirmed"
    else:
        label = "confirmed_then_returned" if returned else "confirmed_unfinished"
    event["episode_label"] = label


def _counts(rows: list[dict], price: list[dict], ema: list[dict], pivot: float,
            start: datetime, end: datetime, five: _Series) -> dict:
    expected = int((end - start).total_seconds() / 180)
    observed = [row for row in rows if start <= row["open_time"] < end]
    sides = [strict_side(row.get("close"), pivot) if _usable(row) else None for row in observed]
    counts = Counter(sides)
    valid = sum(counts[side] for side in (-1, 0, 1))
    price_hours = valid * 3 / 60
    ema_hours = sum(_feature(row, "ema6", "ema6_ready") is not None for row in observed) * 3 / 60
    longest, runs = Counter(), Counter()
    previous_close = start
    for row, side in zip(observed, sides):
        if row["open_time"] != previous_close or side not in (-1, 1):
            runs.clear()
        if side in (-1, 1):
            runs[-side] = 0
            runs[side] += 1
            longest[side] = max(longest[side], runs[side])
        previous_close = row["close_time"]
    state, cloud_crosses = None, 0
    cloud_counts, widths = Counter(), []
    seed = five.asof(start)
    seed20, seed50 = (_feature(seed, name, "cloud_ready") for name in ("ema20", "ema50"))
    state = strict_side(seed20, seed50)
    state = state if state else None
    previous_cloud_close = start
    for row in five.rows:
        if not start <= row["open_time"] < end:
            continue
        if row["open_time"] != previous_cloud_close:
            state = None
        previous_cloud_close = row["close_time"]
        ema20, ema50 = (_feature(row, name, "cloud_ready") for name in ("ema20", "ema50"))
        raw = strict_side(ema20, ema50)
        cloud_counts[raw] += 1
        state, crossing = transition(state, raw)
        cloud_crosses += crossing is not None
        if ema20 is not None and ema50 is not None:
            widths.append(abs(ema20 - ema50))
    return {
        "price_crosses": len(price), "price_crosses_up": sum(row["direction"] == 1 for row in price),
        "price_crosses_down": sum(row["direction"] == -1 for row in price),
        "price_recrosses": sum(bool(row.get("is_recross")) for row in price),
        "ema_crosses": len(ema), "ema_crosses_up": sum(row["direction"] == 1 for row in ema),
        "ema_crosses_down": sum(row["direction"] == -1 for row in ema),
        "price_observed_hours": price_hours, "ema_observed_hours": ema_hours,
        "price_crosses_per_hour": len(price) / price_hours if price_hours else None,
        "ema_crosses_per_hour": len(ema) / ema_hours if ema_hours else None,
        "first_price_cross_at": price[0]["observed_at"] if price else None,
        "last_price_cross_at": price[-1]["observed_at"] if price else None,
        "first_ema_cross_at": ema[0]["observed_at"] if ema else None,
        "last_ema_cross_at": ema[-1]["observed_at"] if ema else None,
        "touch_bars": sum(_usable(row) and _number(row.get("low")) is not None and _number(row.get("high")) is not None and float(row["low"]) <= pivot <= float(row["high"]) for row in observed),
        "expected_3m_bars": expected, "observed_3m_bars": len(observed),
        "sampled_close_above": counts[1], "sampled_close_below": counts[-1],
        "sampled_close_equal": counts[0], "sampled_close_unknown": expected - valid,
        "sampled_close_valid": valid, "sampled_close_total": expected,
        "longest_above_run_3m": longest[1], "longest_below_run_3m": longest[-1],
        "occupancy_above_share": counts[1] / valid if valid else None,
        "occupancy_below_share": counts[-1] / valid if valid else None,
        "occupancy_equal_share": counts[0] / valid if valid else None,
        "cloud_order_changes": cloud_crosses,
        "cloud_bullish_bars": cloud_counts[1], "cloud_bearish_bars": cloud_counts[-1],
        "cloud_flat_bars": cloud_counts[0], "cloud_unknown_bars": cloud_counts[None],
        "cloud_width_min": min(widths) if widths else None,
        "cloud_width_max": max(widths) if widths else None,
        "cloud_width_mean": sum(widths) / len(widths) if widths else None,
    }


def analyze_day(*, session_date: str, contract: str, pivot: float,
                minutes: Any, bars3: Any, bars5: Any,
                source: Mapping | None = None, prior_rth_close: float | None = None,
                require_quality: bool = True) -> dict[str, list[dict]]:
    """Analyze one source-qualified day using only its same-contract frames.

    The runner owns calendar/source/full-anchor/warmup selection and preserves
    exclusions. Partial synthetic inputs remain explicitly quality-ineligible;
    their gaps reset crossing state and censor paths rather than fabricating
    observations. All output timestamps are UTC ISO instants.
    """
    p = _number(pivot)
    if p is None:
        raise ValueError("pivot must be finite")
    minute = _Series(_records(minutes, contract, 1))
    three = _Series(_records(bars3, contract, 3))
    five = _Series(_records(bars5, contract, 5))
    start, end = _clock(session_date, "09:30"), _clock(session_date, "16:00")
    intervals = [(name, _clock(session_date, a), _clock(session_date, b)) for name, a, b in SECTIONS]
    snapshots = [_snapshot(_clock(session_date, "09:25"), label="0925", day=session_date, contract=contract, pivot=p, minute=minute, three=three, five=five),
                 _snapshot(start, label="0930", day=session_date, contract=contract, pivot=p, minute=minute, three=three, five=five, opening_price=True)]
    for name, _, finish in intervals:
        snapshots.append(_snapshot(finish, label=f"{name}_end", day=session_date, contract=contract, pivot=p, minute=minute, three=three, five=five))
    opening = snapshots[1]
    quality_codes = _quality_codes(session_date, minute, three, five, snapshots)
    if require_quality and quality_codes:
        raise IneligibleDay(quality_codes)
    price_side = strict_side(opening["price"], p)
    price_side = price_side if price_side else None
    ema_side = strict_side(opening["ema6"], p)
    ema_side = ema_side if ema_side else None
    price_events, ema_events, outcomes = [], [], []
    crossing_snapshots = []
    price_by_section, ema_by_section = Counter(), Counter()
    active = None
    expected_open = start
    rth = [row for row in three.rows if start <= row["open_time"] < end]
    for row in rth:
        at = row["close_time"]
        name, _, section_end = next(item for item in intervals if item[1] <= row["open_time"] < item[2])
        gap = row["open_time"] != expected_open or not _usable(row) or _number(row.get("close")) is None
        if gap:
            price_side = ema_side = None
            if active is not None:
                _finish_episode(active, min(expected_open, row["open_time"]), returned=False,
                                reason="data_gap", minute=minute, pivot=p)
                active = None
        expected_open = at
        raw_price = strict_side(row.get("close"), p) if _usable(row) else None
        raw_ema = strict_side(_feature(row, "ema6", "ema6_ready"), p)
        prior_price, prior_ema = price_side, ema_side
        price_side, price_cross = transition(price_side, raw_price)
        ema_side, ema_cross = transition(ema_side, raw_ema)
        context = _snapshot(at, label="event", day=session_date, contract=contract, pivot=p, minute=minute, three=three, five=five)
        feature_snapshot_id = f"{session_date}:{contract}:crossing:{at.isoformat()}"
        if price_cross is not None or ema_cross is not None:
            crossing_snapshots.append({**context, "snapshot_id": feature_snapshot_id,
                                       "snapshot_label": "crossing"})
        common = {"session_date": session_date, "contract": contract, "section": name,
                  "bar_open": _iso(row["open_time"]), "observed_at": _iso(at),
                  "feature_snapshot_id": feature_snapshot_id,
                  "reference_price": _number(row.get("close")), **_context(context)}
        if price_cross is not None:
            if active is not None:
                _finish_episode(active, at, returned=True, reason="reverse_price_cross", minute=minute, pivot=p)
            state = "same_close_actual_crossing" if ema_cross == price_cross else "equal_with_remembered_side" if raw_ema == 0 and ema_side is not None else "unavailable_uninitialized" if raw_ema is None or (raw_ema == 0 and ema_side is None) or (raw_ema == price_cross and prior_ema is None) else "already_aligned" if raw_ema == price_cross else "opposite"
            active = {**common, "event_id": f"{session_date}:{contract}:price:{at.isoformat()}",
                      "direction": price_cross, "first_per_day": not price_events,
                      "is_recross": bool(price_events),
                      "first_per_section": price_by_section[name] == 0,
                      "price_raw_side": raw_price, "price_previous_strict_side": prior_price,
                      "ema_raw_side": raw_ema, "ema_remembered_side": ema_side,
                      "ema_previous_strict_side": prior_ema, "ema_state_at_cross": state,
                      "ema_already_aligned_at_start": state == "already_aligned",
                      "confirmation_kind": None, "confirmation_at": None,
                      "confirmation_section": None, "confirmation_event_id": None,
                      "confirmation_feature_snapshot_id": None,
                      "confirmation_lag_minutes": None, "confirmation_price": None,
                      "confirmation_distance_from_pivot": None}
            price_events.append(active)
            price_by_section[name] += 1
        if ema_cross is not None:
            event = {**common, "event_id": f"{session_date}:{contract}:ema:{at.isoformat()}",
                     "direction": ema_cross, "first_per_day": not ema_events,
                     "first_per_section": ema_by_section[name] == 0,
                     "ema_raw_side": raw_ema, "ema_previous_strict_side": prior_ema}
            event.update(_retest(event, rth, p, end))
            event.update(retest_close_classification=event["retest_close_class"],
                         time_to_retest_minutes=event["retest_minutes"])
            ema_events.append(event)
            ema_by_section[name] += 1
            if active is not None and active["direction"] == ema_cross and active["confirmation_at"] is None:
                lag = (at - _dt(active["observed_at"])).total_seconds() / 60
                active.update(confirmation_kind="same_close" if lag == 0 else "delayed",
                              confirmation_at=_iso(at), confirmation_lag_minutes=lag,
                              confirmation_section=name, confirmation_event_id=event["event_id"],
                              confirmation_feature_snapshot_id=event["feature_snapshot_id"],
                              confirmation_price=float(row["close"]),
                              confirmation_distance_from_pivot=ema_cross * (float(row["close"]) - p))
    if active is not None:
        _finish_episode(active, min(expected_open, end), returned=False,
                        reason="data_gap" if expected_open < end else "rth_end", minute=minute, pivot=p)
    section_ends = {name: finish for name, _, finish in intervals}
    confirmations_seen, confirmations_by_section = 0, Counter()
    for event_type, events in (("price_cross", price_events), ("ema_cross", ema_events)):
        for event in events:
            at = _dt(event["observed_at"])
            outcomes.extend(_event_outcomes(event, at, event["reference_price"], minute,
                                            section_ends[event["section"]], end, event_type, event))
            if event_type == "price_cross" and event["confirmation_at"] is not None:
                confirmed = _dt(event["confirmation_at"])
                context = _snapshot(confirmed, label="confirmation", day=session_date, contract=contract, pivot=p, minute=minute, three=three, five=five)
                confirmation_section = event["confirmation_section"]
                confirmation_event = {**event, "section": confirmation_section,
                                      "origin_section": event["section"], "information_section": confirmation_section,
                                      "origin_first_per_day": event["first_per_day"],
                                      "origin_first_per_section": event["first_per_section"],
                                      "first_per_day": confirmations_seen == 0,
                                      "first_per_section": confirmations_by_section[confirmation_section] == 0}
                outcomes.extend(_event_outcomes(confirmation_event, confirmed, event["confirmation_price"], minute,
                                                section_ends[confirmation_section], end, "ema_confirmation", context))
                confirmations_seen += 1
                confirmations_by_section[confirmation_section] += 1
    sections = []
    for name, beginning, finish in intervals:
        first = _snapshot(beginning, label=f"{name}_start", day=session_date, contract=contract, pivot=p, minute=minute, three=three, five=five, opening_price=beginning == start)
        last = next(row for row in snapshots if row["snapshot_label"] == f"{name}_end")
        records = {"session_date": session_date, "contract": contract, "section": name,
                   **_counts(rth, [row for row in price_events if row["section"] == name],
                             [row for row in ema_events if row["section"] == name], p, beginning, finish, five)}
        section_context = (*CONTEXT_FIELDS, "cloud_width", "cloud_spread", "price_side_relative_pivot", "ema6_side_relative_pivot")
        records.update({f"start_{key}": first[key] for key in section_context})
        records.update({f"end_{key}": last[key] for key in section_context})
        records["cloud_order_transition"] = f"{first['cloud_order']}_to_{last['cloud_order']}"
        records["price_side_transition"] = f"{first['price_side_relative_pivot']}_to_{last['price_side_relative_pivot']}"
        records["ema6_side_transition"] = f"{first['ema6_side_relative_pivot']}_to_{last['ema6_side_relative_pivot']}"
        sections.append(records)
    last = snapshots[-1]
    expected_minutes = [start + timedelta(minutes=n) for n in range(390)]
    complete_minutes = all(_usable(minute.by_open.get(at)) for at in expected_minutes)
    complete_three = len(rth) == 130 and all(_usable(row) for row in rth) and all(row["open_time"] == start + timedelta(minutes=3 * n) for n, row in enumerate(rth))
    daily = {"session_date": session_date, "contract": contract, "pivot": p,
             "source_outlook_id": (source or {}).get("outlook_id"),
             "source_id": (source or {}).get("outlook_id", (source or {}).get("source_id")),
             "historical_availability": "unverified_retrospective_descriptive",
             "retrospective_full_day_quality_selection": True,
             "rth_minute_roster_complete": complete_minutes,
             "rth_three_minute_roster_complete": complete_three,
             "quality_eligible": not quality_codes, "quality_exclusion_codes": quality_codes,
             **_counts(rth, price_events, ema_events, p, start, end, five),
             "opening_price": opening["price"], "closing_price": last["price"],
             "prior_same_contract_rth_close": _number(prior_rth_close),
             "opening_gap_points": opening["price"] - float(prior_rth_close) if opening["price"] is not None and _number(prior_rth_close) is not None else None,
             "close_minus_open": last["price"] - opening["price"] if last["price"] is not None and opening["price"] is not None else None,
             "closing_side_relative_pivot": last["price_side_relative_pivot"],
             "closing_ema6_side_relative_pivot": last["ema6_side_relative_pivot"],
             "closing_price_cloud_location": last["price_cloud_location"],
             "closing_price_side_relative_vwap": last["price_side_relative_vwap"],
             "returned_without_new_ema_cross": sum(row["episode_label"] == "returned_without_new_ema_cross" for row in price_events),
             "unfinished_price_episodes": sum(row["return_censored"] for row in price_events)}
    daily.update({f"opening_{key}": opening[key] for key in (*CONTEXT_FIELDS, "cloud_width", "cloud_spread")})
    daily.update({f"closing_{key}": last[key] for key in ("cloud_order", "cloud_width", "cloud_spread")})
    return {"daily": [daily], "sections": sections, "snapshots": snapshots + crossing_snapshots,
            "price_events": price_events, "ema_events": ema_events, "outcomes": outcomes}


def _quality_codes(day: str, minute: _Series, three: _Series, five: _Series,
                   snapshots: list[dict]) -> list[str]:
    start, end = _clock(day, "09:30"), _clock(day, "16:00")
    anchor = _clock((date.fromisoformat(day) - timedelta(days=1)).isoformat(), "18:00")
    reasons = []
    for name, beginning, finish in (("anchor_to_rth_end", anchor, end), ("rth", start, end)):
        current = beginning
        while current < finish:
            row = minute.by_open.get(current)
            if not _usable(row) or any(_number(row.get(key)) is None for key in ("open", "high", "low", "close")):
                reasons.append(f"incomplete_or_unusable_{name}_minutes")
                break
            current += timedelta(minutes=1)
    for label, series, interval, names, readiness in (("ema6", three, 3, ("ema6",), "ema6_ready"),
                                                    ("cloud", five, 5, ("ema20", "ema50"), "cloud_ready")):
        current = start
        while current < end:
            row = series.by_open.get(current)
            if any(_feature(row, name, readiness) is None for name in names) or any(_number(row.get(key)) is None for key in ("open", "high", "low", "close")):
                reasons.append(f"unready_or_missing_rth_{label}")
                break
            current += timedelta(minutes=interval)
    for row in snapshots[:2]:
        for feature in ("ema6", "ema20", "ema50", "vwap"):
            if row[feature] is None:
                reasons.append(f"unavailable_{row['snapshot_label']}_{feature}")
    current = start
    while current < end:
        row = minute.by_open.get(current)
        if _feature(row, "vwap", "vwap_valid") is None:
            reasons.append("unavailable_rth_vwap")
            break
        current += timedelta(minutes=1)
    return sorted(set(reasons))


def analyze(days: Iterable[Mapping[str, Any]]) -> dict[str, list[dict]]:
    """Combine explicitly supplied qualified-day arguments; no data discovery."""
    result = {name: [] for name in TABLES}
    seen = set()
    for settings in sorted(days, key=lambda row: (row["session_date"], row["contract"])):
        identity = (settings["session_date"], settings["contract"])
        if identity in seen:
            raise ValueError("duplicate day/contract analysis input")
        seen.add(identity)
        output = analyze_day(**settings)
        for name in TABLES:
            result[name].extend(output[name])
    return result
