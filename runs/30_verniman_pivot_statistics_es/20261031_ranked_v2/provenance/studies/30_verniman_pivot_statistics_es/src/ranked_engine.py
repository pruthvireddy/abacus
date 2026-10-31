"""Study 30 ranked extension: moving-reference events and linked paths.

This module consumes explicit, pinned native feature rows. It performs no data
discovery and leaves the original pivot event interface untouched. Physical
crossings have one identity, with RTH/Globex membership attached separately.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

import engine as core


TABLES = ("daily", "sections", "events", "snapshots", "outcomes", "recrosses", "sequences", "transitions")
MATCHED = "pivot_matched_rth"
VWAP_RTH = "vwap_only_rth"
VWAP_GLOBEX = "vwap_only_full_globex"


def _side(a, b):
    return core.strict_side(a, b)


def distance_band(value):
    if value is None:
        return "unknown"
    return "<5" if value < 5 else "5–<15" if value < 15 else "15–<30" if value < 30 else "≥30"


def configuration(value, pivot, vwap):
    a, b = _side(value, pivot), _side(value, vwap)
    if a is None or b is None:
        return "unknown"
    if a == 0 or b == 0:
        return "equal"
    return "above_both" if a == b == 1 else "below_both" if a == b == -1 else "between"


def cloud_support(snapshot, direction):
    order = snapshot.get("cloud_order")
    slopes = [snapshot.get("ema20_slope_15m"), snapshot.get("ema50_slope_15m")]
    if order == "unknown" or any(x is None for x in slopes):
        return "unknown"
    ordering = 1 if order == "bullish" else -1 if order == "bearish" else 0
    if ordering == direction and all(direction * x > 0 for x in slopes):
        return "support"
    if ordering == -direction and all(direction * x < 0 for x in slopes):
        return "opposition"
    return "mixed"


def _snapshot(at, label, day, contract, pivot, minute, three, five, opening=False):
    row = core._snapshot(at, label=label, day=day, contract=contract,
                         pivot=pivot if pivot is not None else 0., minute=minute,
                         three=three, five=five, opening_price=opening)
    if pivot is None:
        row["pivot"] = None
        for key in list(row):
            if "pivot" in key and key != "pivot":
                row[key] = "unknown" if key == "pivot_cloud_location" else None
    row["ema6_side_relative_vwap"] = _side(row["ema6"], row["vwap"])
    row["ema6_minus_vwap"] = row["ema6"] - row["vwap"] if row["ema6"] is not None and row["vwap"] is not None else None
    row["price_available_at"] = row["price_source_at"]
    row["ema6_available_at"] = row["ema6_source_at"]
    row["cloud_available_at"] = row["cloud_source_at"]
    row["vwap_available_at"] = row["vwap_source_at"]
    return row


def _valid_value(row, series):
    return core._feature(row, "ema6", "ema6_ready") if series == "ema6" else core._number(row.get("close")) if core._usable(row) else None


def _count_bucket(count):
    return "0" if count == 0 else "1" if count == 1 else "2" if count == 2 else "3–4" if count <= 4 else "5+"


def _known_pause(day, previous, current):
    return (day < "2021-06-28" and previous == core._clock(day, "16:15")
            and current == core._clock(day, "16:30"))


def _complete_pair_path(start, end, observations, *, day, allow_pause=False):
    """A pair-valid observation at every native close through the endpoint."""
    current = start + timedelta(minutes=3)
    while current <= end:
        if allow_pause and day < "2021-06-28" and core._clock(day, "16:15") < current <= core._clock(day, "16:30"):
            current += timedelta(minutes=3)
            continue
        if not observations.get(current, False):
            return False
        current += timedelta(minutes=3)
    return True


def build_ranked_day(day, contract, minute_rows, three_rows, five_rows, pivot=None,
                     pivot_matched=False, vwap_rth=False, vwap_globex=False):
    """Build one explicitly selected contract/session; no eligibility inference.

    Root orchestration supplies each cohort's independent coverage decision.
    ``daily``/``sections`` use explicit ``session_mode`` and one row per
    reference/series. ``events`` stores each physical cross once and attaches
    ``scopes``, ``cohorts_by_mode`` and separate native-sequence ordinals.
    Forward paths and recross probabilities are RTH-only.
    """
    pivot = core._number(pivot)
    if pivot_matched and pivot is None:
        raise ValueError("pivot-matched cohort requires finite pivot")
    minute = core._Series(core._records(minute_rows, contract, 1))
    three = core._Series(core._records(three_rows, contract, 3))
    five = core._Series(core._records(five_rows, contract, 5))
    result = {name: [] for name in TABLES}
    rth_start, rth_end = core._clock(day, "09:30"), core._clock(day, "16:00")
    anchor = core._clock((date.fromisoformat(day) - timedelta(days=1)).isoformat(), "18:00")
    globex_end = core._clock(day, "17:00")
    intervals = [(name, core._clock(day, a), core._clock(day, b)) for name, a, b in core.SECTIONS]
    snapshots = {}

    def snap(at, label="crossing", opening=False):
        identity = f"{day}:{contract}:ranked:{label}:{at.isoformat()}"
        if identity not in snapshots:
            row = _snapshot(at, label, day, contract, pivot, minute, three, five, opening)
            row["snapshot_id"] = identity
            snapshots[identity] = row
        return snapshots[identity]

    opening = snap(rth_start, "0930", opening=True)
    separation = abs(pivot - opening["vwap"]) if pivot is not None and opening["vwap"] is not None else None
    separation_bps = 10000 * separation / pivot if separation is not None and pivot > 0 else None
    opening_context = {
        "opening_configuration": configuration(opening["price"], pivot, opening["vwap"]),
        "opening_ema6_configuration": configuration(opening["ema6"], pivot, opening["vwap"]),
        "opening_separation_points": separation, "opening_separation_bps": separation_bps,
        "opening_separation_band": distance_band(separation_bps),
        "opening_context_available_at": core._iso(rth_start),
    }
    memberships = {"rth": ([MATCHED] if pivot_matched else []) + ([VWAP_RTH] if vwap_rth else []),
                   "globex": [VWAP_GLOBEX] if vwap_globex else []}
    refs = ["vwap"] + (["pivot"] if pivot_matched else [])
    physical = {}
    observations_by_pair = {}
    scope_events = {}

    for mode, start, end in (("rth", rth_start, rth_end), ("globex", anchor, globex_end)):
        if not memberships[mode]:
            continue
        for reference in refs:
            if reference == "pivot" and mode != "rth":
                continue
            cohorts = memberships[mode] if reference == "vwap" else [MATCHED]
            for series in ("price", "ema6"):
                # RTH starts from the exact opening observation. Globex starts
                # uninitialized: there is no pre-anchor VWAP comparison.
                seed = opening["price" if series == "price" else "ema6"] if mode == "rth" else None
                reference_seed = pivot if reference == "pivot" else opening["vwap"]
                state = _side(seed, reference_seed)
                state = state if state else None
                expected = start
                selected = []
                valid_observations = {}
                for row in three.rows:
                    if not start <= row["open_time"] < end:
                        continue
                    at = row["close_time"]
                    if row["open_time"] != expected and not _known_pause(day, expected, row["open_time"]):
                        state = None
                    expected = at
                    value = _valid_value(row, series)
                    vwap = core._feature(minute.by_close.get(at), "vwap", "vwap_valid")
                    ref_value = pivot if reference == "pivot" else vwap
                    raw = _side(value, ref_value)
                    valid_observations[at] = raw is not None
                    before = state
                    state, direction = core.transition(state, raw)
                    if direction is None:
                        continue
                    context = snap(at)
                    name = next((name for name, a, b in intervals if a <= row["open_time"] < b), "overnight" if row["open_time"] < rth_start else "post_rth")
                    identity = f"{day}:{contract}:ranked:{reference}:{series}:{at.isoformat()}"
                    event = physical.get(identity)
                    if event is None:
                        event = {
                            "event_id": identity, "session_date": day, "contract": contract,
                            "reference": reference, "series": series, "direction": direction,
                            "bar_open": core._iso(row["open_time"]), "observed_at": core._iso(at),
                            "available_at": core._iso(at), "section": name,
                            "reference_price": core._number(row.get("close")),
                            "reference_line_value": ref_value, "crossing_value": value,
                            "difference": value - ref_value,
                            "previous_strict_side": before, "raw_side": raw,
                            "feature_snapshot_id": context["snapshot_id"],
                            "scopes": [], "cohorts": [], "cohorts_by_mode": {},
                            "session_mode": "rth" if mode == "rth" else "globex",
                            "cloud_support": cloud_support(context, direction),
                            **core._context(context), **opening_context,
                        }
                        physical[identity] = event
                    event["scopes"].append(mode)
                    event["cohorts_by_mode"][mode] = list(cohorts)
                    event["cohorts"] = sorted(set(event["cohorts"]) | set(cohorts))
                    event[f"{mode}_ordinal"] = len(selected) + 1
                    event[f"{mode}_ordinal_group"] = "1" if not selected else "2" if len(selected) == 1 else "3+"
                    section_ordinal = 1 + sum(item["section"] == name for item in selected)
                    event[f"{mode}_section_ordinal"] = section_ordinal
                    if mode == "rth":
                        event.update(ordinal=len(selected) + 1, ordinal_group=event["rth_ordinal_group"],
                                     first_per_day=not selected, first_per_section=section_ordinal == 1,
                                     section_ordinal=section_ordinal)
                    selected.append(event)
                observations_by_pair[(mode, reference, series)] = valid_observations
                scope_events[(mode, reference, series)] = selected
                windows = [("all", start, end)] + (intervals if mode == "rth" else [])
                for name, a, b in windows:
                    events = [item for item in selected if a <= core._dt(item["bar_open"]) < b]
                    observed = sum(a < at <= b and valid for at, valid in valid_observations.items())
                    hours = observed * 3 / 60
                    expected_bars = int((b-a).total_seconds() / 180) - (5 if mode == "globex" and day < "2021-06-28" else 0)
                    record = {
                        "session_date": day, "contract": contract, "reference": reference,
                        "series": series, "session_mode": mode, "section": name,
                        "cohorts": list(cohorts), "crosses": len(events),
                        "crosses_up": sum(item["direction"] == 1 for item in events),
                        "crosses_down": sum(item["direction"] == -1 for item in events),
                        "count_bucket": _count_bucket(len(events)), "observed_hours": hours,
                        "crosses_per_hour": len(events) / hours if hours else None,
                        "valid_observations": observed, "expected_observations": expected_bars,
                        "missing_observations": expected_bars - observed,
                        "first_cross_at": events[0]["observed_at"] if events else None,
                        "first_cross_bar_open": events[0]["bar_open"] if events else None,
                        "first_cross_direction": events[0]["direction"] if events else None,
                        "first_cross_minutes": (core._dt(events[0]["observed_at"])-a).total_seconds()/60 if events else None,
                        "last_cross_at": events[-1]["observed_at"] if events else None,
                        "opening_feature_snapshot_id": opening["snapshot_id"], **opening_context,
                    }
                    result["daily" if name == "all" else "sections"].append(record)

    result["events"] = list(physical.values())
    for (mode, reference, series), events in scope_events.items():
        if mode != "rth":
            continue
        valid_observations = observations_by_pair[(mode, reference, series)]
        for i, event in enumerate(events):
            at = core._dt(event["observed_at"])
            context = snapshots[event["feature_snapshot_id"]]
            section_end = next(b for name, _, b in intervals if name == event["section"])
            event_type = f"{series}_{reference}_cross"
            for outcome in core._event_outcomes(event, at, event["reference_price"], minute, section_end, rth_end, event_type, context):
                outcome.update(reference=reference, series=series, session_mode="rth",
                               cohorts=event["cohorts_by_mode"]["rth"], ordinal=event["ordinal"],
                               ordinal_group=event["ordinal_group"], cloud_support=event["cloud_support"], **opening_context)
                result["outcomes"].append(outcome)
            if series != "ema6":
                continue
            later = next((item for item in events[i+1:] if item["direction"] == -event["direction"]), None)
            event["next_ema_recross_at"] = later["observed_at"] if later else None
            event["next_ema_recross_minutes"] = (core._dt(later["observed_at"])-at).total_seconds()/60 if later else None
            for horizon in (15, 30, 60):
                end = at + timedelta(minutes=horizon)
                reverse = later is not None and core._dt(later["observed_at"]) <= min(end, rth_end)
                complete = _complete_pair_path(at, min(end, rth_end), valid_observations, day=day)
                valid = complete and end <= rth_end
                result["recrosses"].append({
                    "event_id": event["event_id"], "session_date": day, "contract": contract,
                    "reference": reference, "series": series, "session_mode": mode,
                    "cohorts": event["cohorts_by_mode"]["rth"], "section": event["section"],
                    "direction": event["direction"], "horizon": f"{horizon}m",
                    "no_recross": not reverse if valid else None, "valid": valid,
                    "censored": not valid, "unknown_reason": None if valid else "missing_reference_observation" if not complete else "right_censored_at_rth_end",
                    "next_recross_at": later["observed_at"] if later else None,
                    "next_recross_minutes": event["next_ema_recross_minutes"],
                    "first_per_day": event["first_per_day"], "first_per_section": event["first_per_section"],
                    "ordinal_group": event["ordinal_group"], **opening_context,
                })

    # S14 is a paired, matched-RTH question. Every start is retained, including
    # simultaneous/already-beyond cases; ordering at equal timestamps is unknown.
    if pivot_matched:
        ema = sorted([e for e in result["events"] if e["series"] == "ema6" and "rth" in e["scopes"]], key=lambda e: (e["observed_at"], e["reference"]))
        for event in ema:
            at = core._dt(event["observed_at"])
            deadline = at + timedelta(minutes=30)
            other = "pivot" if event["reference"] == "vwap" else "vwap"
            snaprow = snapshots[event["feature_snapshot_id"]]
            other_side = snaprow[f"ema6_side_relative_{other}"]
            simultaneous = next((e for e in ema if e["reference"] == other and e["observed_at"] == event["observed_at"]), None)
            second = next((e for e in ema if e["reference"] == other and e["direction"] == event["direction"] and at < core._dt(e["observed_at"]) <= min(deadline, rth_end)), None)
            reverse = next((e for e in ema if e["reference"] == event["reference"] and e["direction"] == -event["direction"] and at < core._dt(e["observed_at"]) <= min(deadline, rth_end)), None)
            endpoint = min([core._dt(e["observed_at"]) for e in (second, reverse) if e] or [min(deadline, rth_end)])
            complete = all(_complete_pair_path(at, endpoint, observations_by_pair[("rth", ref, "ema6")], day=day) for ref in ("pivot", "vwap"))
            if simultaneous:
                label = "simultaneous"
            elif other_side is None:
                label = "unknown_other_line"
            elif other_side == event["direction"]:
                label = "already_beyond_other"
            elif other_side == 0:
                label = "other_equal_at_start"
            elif not complete:
                label = "censored_missing_observation"
            elif second and reverse and second["observed_at"] == reverse["observed_at"]:
                label = "simultaneous_endpoint"
            elif second and (not reverse or second["observed_at"] < reverse["observed_at"]):
                label = "second_before_recross"
            elif reverse:
                label = "recross_first"
            elif deadline > rth_end:
                label = "censored_no_endpoint"
            else:
                label = "neither_within_30m"
            result["sequences"].append({
                "event_id": event["event_id"], "session_date": day, "contract": contract,
                "reference": event["reference"], "first_reference": event["reference"], "second_reference": other,
                "series": "ema6", "session_mode": "rth", "cohorts": [MATCHED],
                "section": event["section"], "direction": event["direction"], "horizon": "30m",
                "result": label, "second_before_recross": label == "second_before_recross" if label in ("second_before_recross", "recross_first", "neither_within_30m") else None,
                "second_cross_at": second["observed_at"] if second else None,
                "first_recross_at": reverse["observed_at"] if reverse else None,
                "first_per_day": event["first_per_day"],
                "first_per_section": event["first_per_section"],
                "censored": label.startswith("censored") or label == "unknown_other_line", **opening_context,
            })

    for reference in refs:
        cohorts = memberships["rth"] if reference == "vwap" else [MATCHED]
        if not cohorts:
            continue
        states = []
        for name, a, b in intervals:
            end_snap = snap(b, f"{name}_end")
            line = pivot if reference == "pivot" else end_snap["vwap"]
            states.append((name, {"price_side": _side(end_snap["price"], line),
                                  "ema6_side": _side(end_snap["ema6"], line),
                                  "cloud_order": end_snap["cloud_order"]}))
        # Include OR->PM explicitly, as well as adjacent transitions.
        for source, target in ((0, 1), (1, 2), (0, 2)):
            for metric in ("price_side", "ema6_side", "cloud_order"):
                a, b = states[source][1][metric], states[target][1][metric]
                valid = a is not None and b is not None and a != "unknown" and b != "unknown"
                result["transitions"].append({
                    "session_date": day, "contract": contract, "reference": reference,
                    "series": "ema6" if metric == "ema6_side" else "price" if metric == "price_side" else "cloud",
                    "session_mode": "rth", "cohorts": list(cohorts), "metric": metric,
                    "from_section": states[source][0], "to_section": states[target][0],
                    "from_state": a, "to_state": b, "valid": valid,
                    "persistent": a == b if valid else None,
                    "reversed": (a == -b if isinstance(a, int) and isinstance(b, int) and a != 0 and b != 0 else
                                 (a, b) in (("bullish", "bearish"), ("bearish", "bullish"))) if valid else None,
                })
    result["snapshots"] = list(snapshots.values())
    return result
