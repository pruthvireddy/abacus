"""Independent scalar Stage 2 references; no event/statistical producer imports.

These calculations consume the complete saved scheduled roster. Unknown missing
slots remain records, and retrospective episode labels never enter acceptance.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd

NY = "America/New_York"
START = pd.Timestamp("2018-01-01", tz=NY).tz_convert("UTC")
END = pd.Timestamp("2021-01-01", tz=NY).tz_convert("UTC")
THRESHOLDS = {"ES": 2.4, "GC": 2.0, "NQ": 10.0}
BRANCHES = ("fast", "slow")
METRICS = ("mfe", "mae", "terminal_delta")
FLAGS = ("favorable", "neutral", "adverse", "mfe_gt_mae", "mfe_mae_tie")


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def finite(value):
    return value is not None and pd.notna(value) and math.isfinite(float(value))


def in_development(value):
    stamp = pd.Timestamp(value)
    return START <= stamp < END


def linear_quantile(values, probability):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    position = float(probability) * (len(values) - 1)
    lower, upper = math.floor(position), math.ceil(position)
    return values[lower] + (position - lower) * (values[upper] - values[lower])


def _strata(row):
    stamp = pd.Timestamp(row["timestamp"]).tz_convert(NY)
    day = stamp.date()
    hour = stamp.hour + stamp.minute / 60
    return dict(year=day.year, month=f"{day.year:04d}-{day.month:02d}",
                week=(day - timedelta(days=day.weekday())).isoformat(),
                calendar_date=day.isoformat(), hour=stamp.hour,
                time_stratum="Asia" if hour >= 18 or hour < 3 else
                "Europe" if hour < 9 else "US" if hour < 16 else "Late",
                session=str(row.get("session", day.isoformat())))


def iter_reference_stream(mapped_bars, interval_minutes=None, thresholds=None):
    """Replay both independent arm states in one scalar chronological pass.

    Returns full causal technical/event rows, including warmup events. Outcomes
    must receive only scoped events. Branch-local episode_id follows the inherited
    slow semantics and is separate from the geometric matching episode.
    """
    thresholds = THRESHOLDS if thresholds is None else thresholds
    frame = mapped_bars
    if interval_minutes is not None:
        frame = frame.copy()
        frame["interval_minutes"] = int(interval_minutes)
    require(not frame.duplicated(["product", "interval_minutes", "timestamp"]).any(), "duplicate reference slots")
    for (product, interval), group in frame.groupby(["product", "interval_minutes"], sort=False):
        require(pd.to_datetime(group.timestamp, utc=True).is_monotonic_increasing, "unordered reference slots")
        armed = {branch: False for branch in BRANCHES}
        episode = {branch: 0 for branch in BRANCHES}
        previous_direction, previous_contract, previous_reset_source = 0, None, None
        threshold = float(thresholds[product])
        epsilon = 1e-10 * max(1.0, abs(threshold))
        for ordinal, item in enumerate(group.itertuples(index=False)):
            base = item._asdict()
            valid = bool(base["usable"]) and bool(base["feature_valid"]) and finite(base["ema20"]) and finite(base["ema50"])
            direction = (1 if base["ema20"] > base["ema50"] else -1 if base["ema20"] < base["ema50"] else 0) if valid else 0
            source = base.get("feature_source_timestamp", base["timestamp"])
            explicit = bool(base.get("feature_reset", False)) and source != previous_reset_source
            reset = ("invalid_data_or_feature" if not valid else "equality" if not direction else
                     "contract_change" if previous_contract is not None and base["contract"] != previous_contract else
                     "feature_reset" if explicit else "direction_change" if direction != previous_direction else "")
            if reset:
                armed = {branch: False for branch in BRANCHES}
            slow_touch = fast_touch = departure = False
            width = None
            gate = False
            if valid and direction:
                width = abs(float(base["ema20"]) - float(base["ema50"]))
                gate = width + epsilon >= threshold
                slow_touch = base["low"] <= base["ema50"] <= base["high"]
                fast_touch = base["low"] <= base["ema20"] <= base["high"]
                departure = base["low"] > max(base["ema20"], base["ema50"]) if direction == 1 else base["high"] < min(base["ema20"], base["ema50"])
            for branch in BRANCHES:
                selected = "ema20" if branch == "fast" else "ema50"
                touch = fast_touch if branch == "fast" else slow_touch
                other_touch = slow_touch if branch == "fast" else fast_touch
                before = armed[branch]
                penetration = bool(valid and direction and (base["low"] <= base[selected] if direction == 1 else base["high"] >= base[selected]))
                candidate = bool(touch and before)
                accepted = bool(candidate and gate)
                reason = ("invalid_data_or_feature" if not valid else "no_direction" if not direction else
                          "accepted" if accepted else "not_armed" if touch and not before else
                          "width_below_minimum" if candidate and not gate else "gap_penetration" if penetration and not touch else
                          ("slow_only" if branch == "fast" else "fast_only") if other_touch and not touch else "no_touch")
                if penetration:
                    armed[branch] = False
                if departure:
                    if not armed[branch]:
                        episode[branch] += 1
                    armed[branch] = True
                side = "Buy" if direction == 1 else "Sell" if direction == -1 else "None"
                event_id = (f"{product}|{int(interval)}m|{base['contract']}|{pd.Timestamp(base['timestamp']).isoformat()}|{side}|{branch}" if accepted else None)
                row = base | dict(touch_mode=branch, selected_ema=selected, direction=direction,
                                  side=side, signal_idx=ordinal, min_width=threshold, width=width,
                                  width_pass=gate, fast_touch=bool(fast_touch), slow_touch=bool(slow_touch),
                                  penetration=penetration, full_departure=bool(departure),
                                  armed_before=before, armed_after=armed[branch], episode_id=episode[branch],
                                  technical_candidate=bool(touch), setup_candidate=candidate, accepted=accepted,
                                  suppression_reason=reason, reset_reason=reset, event_id=event_id)
                event = None
                if accepted:
                    atr = base.get("atr14")
                    event = row | _strata(row) | dict(stage=2, gate_id="fixed", split="development",
                        signal_timestamp=base["timestamp"], reference_price=base["close"], entry_at=base["available_at"],
                        entry_atr=float(atr) if finite(atr) and atr > 0 else None)
                yield row, event
            previous_direction, previous_contract = direction, base["contract"]
            if bool(base.get("feature_reset", False)):
                previous_reset_source = source


def reference_stream(mapped_bars, interval_minutes=None, thresholds=None):
    """Materialized small-fixture API; full audits use iter_reference_stream."""
    rows, events = [], []
    for row, event in iter_reference_stream(mapped_bars, interval_minutes, thresholds):
        rows.append(row)
        if event is not None:
            events.append(event)
    columns = list(dict.fromkeys(list(mapped_bars.columns) + ["event_id", "touch_mode", "selected_ema", "signal_idx", "direction", "side", "accepted", "reference_price", "signal_timestamp", "entry_at", "entry_atr", "year", "week", "month", "calendar_date", "hour", "time_stratum", "session", "stage", "gate_id", "split"]))
    return pd.DataFrame(rows), pd.DataFrame(events, columns=columns if not events else None)


def reference_outcomes(bars, events, horizons=None, *, roster_end_is_endpoint=True):
    """Independent following-slot min/max/first-attainment outcomes, all fields."""
    events = events.copy()
    require(all(in_development(t) for t in events.timestamp), "reserved reference outcome event")
    require(not events.event_id.duplicated().any(), "duplicate reference event")
    source = {(p, int(i)): group.reset_index(drop=True) for (p, i), group in bars.groupby(["product", "interval_minutes"], sort=False)}
    arrays = {key: {column: group[column].to_numpy() for column in group.columns} for key, group in source.items()}
    result = []
    for event in events.to_dict("records"):
        interval = int(event["interval_minutes"])
        a = arrays[(event["product"], interval)]
        hs = horizons if horizons is not None else ((5, 10, 15, 20, 30, 50, 100) if interval == 3 else (5, 10, 12, 15, 20, 30, 50, 100))
        i = int(event["signal_idx"])
        require(pd.Timestamp(a["timestamp"][i]) == pd.Timestamp(event["timestamp"]), "reference event roster identity")
        for h in hs:
            h = int(h)
            row = event | dict(horizon=h, horizon_minutes=h * interval, status="censored", censor_reason="",
                terminal_at=None, elapsed_minutes=None, crosses_closure=None, same_session=None)
            row.update({key: None for key in METRICS + tuple(k + "_atr" for k in METRICS) + FLAGS})
            row.update({f"{metric}_attainment_{edge}": None for metric in ("mfe", "mae") for edge in ("start", "end")})
            required = list(range(i + 1, i + h + 1))
            reason = None
            if required[-1] >= len(a["timestamp"]):
                reason = "development_endpoint" if roster_end_is_endpoint else "data_edge"
            elif any(pd.Timestamp(a["available_at"][j]) > END for j in required):
                reason = "development_endpoint"
            else:
                for j in required:
                    if not bool(a["usable"][j]) or not all(finite(a[k][j]) for k in ("high", "low", "close")):
                        reason = "invalid_future_slot:" + str(a.get("quality_reason", ["unusable"] * len(a["timestamp"]))[j])
                        break
                    if a["contract"][j] != event["contract"]:
                        reason = "contract_switch"
                        break
            if reason:
                row["censor_reason"] = reason
            else:
                reference, d = float(event["reference_price"]), int(event["direction"])
                favorable = [d * (float(a["high" if d == 1 else "low"][j]) - reference) for j in required]
                adverse = [d * (reference - float(a["low" if d == 1 else "high"][j])) for j in required]
                mfe, mae = max(0.0, max(favorable)), max(0.0, max(adverse))
                delta = d * (float(a["close"][required[-1]]) - reference)
                epsilon = 1e-10 * max(1.0, mfe, mae)
                closure = a.get("known_closure_before", np.zeros(len(a["timestamp"]), dtype=bool))
                row.update(status="completed", terminal_at=pd.Timestamp(a["available_at"][required[-1]]),
                    elapsed_minutes=(pd.Timestamp(a["available_at"][required[-1]]) - pd.Timestamp(event["entry_at"])).total_seconds() / 60,
                    crosses_closure=any(bool(closure[j]) for j in required),
                    same_session=all(str(a["session"][j]) == str(event["session"]) for j in required),
                    mfe=mfe, mae=mae, terminal_delta=delta, favorable=delta > 0, neutral=delta == 0,
                    adverse=delta < 0, mfe_gt_mae=mfe - mae > epsilon, mfe_mae_tie=abs(mfe - mae) <= epsilon)
                for metric, values in (("mfe", favorable), ("mae", adverse)):
                    if row[metric] > 0:
                        j = required[values.index(max(values))]
                        row[metric + "_attainment_start"] = pd.Timestamp(a["timestamp"][j])
                        row[metric + "_attainment_end"] = pd.Timestamp(a["available_at"][j])
                atr = event.get("entry_atr")
                if finite(atr) and float(atr) > 0:
                    for metric in METRICS:
                        row[metric + "_atr"] = row[metric] / float(atr)
            result.append(row)
    columns = list(dict.fromkeys(list(events.columns) + ["horizon", "horizon_minutes", "status", "censor_reason", "terminal_at", "elapsed_minutes", "crosses_closure", "same_session"] + list(METRICS) + [m + "_atr" for m in METRICS] + list(FLAGS) + [m + "_attainment_" + edge for m in ("mfe", "mae") for edge in ("start", "end")]))
    return pd.DataFrame(result, columns=columns if not result else None)


def reference_membership(mapped_bars, technical=None, events=None, *, member_callback=None,
                         materialize_membership=True):
    """Independent shared episode replay, union identity and retrospective labels.

    Scalar branch decisions are regenerated when not supplied. Supplying the
    independently replayed decisions avoids a second replay during verification.
    No producer decision/episode columns are needed from mapped_bars.
    """
    if technical is None:
        technical, events = reference_stream(mapped_bars)
    decision_columns = ("direction", "side", "reset_reason", "full_departure", "accepted", "event_id",
                        "suppression_reason", "armed_before", "armed_after", "penetration")
    tech = {key: group[list(decision_columns)].reset_index(drop=True)
            for key, group in technical.groupby(["product", "interval_minutes", "touch_mode"], sort=False)}
    lookup = {r["event_id"]: r for r in events.to_dict("records")}
    membership, episodes, pairs, union = [], [], [], []
    for (product, interval), group in mapped_bars.groupby(["product", "interval_minutes"], sort=False):
        active = None
        previous_departure = False
        episode_slots = []

        def finish(cause, termination):
            nonlocal active, episode_slots
            if active is None:
                return
            active["end_reason"] = cause
            active["termination_timestamp"] = termination
            active["status"] = "resolved" if cause == "new_departure" else "endpoint" if cause == "development_endpoint" else "interrupted"
            first_fast = active.get("first_fast_event_id")
            fast = lookup.get(first_fast)
            contact = signal = None
            first_contact = first_signal = None
            same_bar = None
            scope_reason = "no_fast_event" if fast is None else "outside_scope_warmup_first_fast" if not in_development(fast["timestamp"]) else "development"
            if scope_reason == "development":
                fast_time = pd.Timestamp(fast["timestamp"])
                selected = [r for r in episode_slots if pd.Timestamp(r["timestamp"]) >= fast_time and in_development(r["timestamp"])]
                same_bar = next((bool(r["slow_touch"]) for r in selected if pd.Timestamp(r["timestamp"]) == fast_time), False)
                later = [r for r in selected if pd.Timestamp(r["timestamp"]) > fast_time]
                first_contact = next((r["timestamp"] for r in later if r["slow_touch"]), None)
                first_signal = next((r["timestamp"] for r in later if r["slow_accepted"]), None)
                contact = True if first_contact is not None else False if cause == "new_departure" else None
                signal = True if first_signal is not None else False if cause == "new_departure" else None
                scope_reason = "resolved_new_departure" if cause == "new_departure" else "interrupted:" + cause
            active.update(same_bar_slow_contact=same_bar, strictly_later_slow_contact=contact,
                strictly_later_slow_signal=signal, first_later_slow_contact_timestamp=first_contact,
                first_later_slow_signal_timestamp=first_signal, retrospective_scope_reason=scope_reason)
            episodes.append(active.copy())
            fast_id, slow_id = active.get("first_fast_event_id"), active.get("first_slow_event_id")
            slow = lookup.get(slow_id)
            relation = ("same_bar" if fast and slow and fast["timestamp"] == slow["timestamp"] else
                        "fast_before_slow" if fast and slow and fast["timestamp"] < slow["timestamp"] else
                        "slow_before_fast" if fast and slow else "fast_only" if fast else "slow_only" if slow else "neither")
            both_scoped = bool(fast and slow and in_development(fast["timestamp"]) and in_development(slow["timestamp"]))
            fd, sd = active["first_fast_in_development"], active["first_slow_in_development"]
            scope = "both_development" if both_scoped else "warmup_counterpart" if fast and slow and (fd or sd) else "outside_scope" if fast and slow else "unpaired_development" if fd or sd else "unpaired_warmup" if fast or slow else "no_accepted"
            pairs.append(active.copy() | dict(pair_id=active["shared_episode_id"] + "|first_pair",
                pair_relation=relation, pair_in_development=both_scoped, pair_scope=scope,
                fast_reference_price=fast["reference_price"] if fast else None,
                slow_reference_price=slow["reference_price"] if slow else None,
                slow_minus_fast_signal_minutes=(pd.Timestamp(slow["timestamp"]) - pd.Timestamp(fast["timestamp"])).total_seconds() / 60 if both_scoped else None,
                slow_minus_fast_reference_points=slow["reference_price"] - fast["reference_price"] if both_scoped else None))
            active, episode_slots = None, []

        fast_rows = tech[(product, interval, "fast")].itertuples(index=False)
        slow_rows = tech[(product, interval, "slow")].itertuples(index=False)
        for item, fast_item, slow_item in zip(group.itertuples(index=False), fast_rows, slow_rows):
            row = item._asdict()
            stamp = pd.Timestamp(row["timestamp"])
            fast, slow = fast_item._asdict(), slow_item._asdict()
            if slow["reset_reason"]:
                finish(slow["reset_reason"], stamp)
                previous_departure = False
            valid_geometry = bool(row["usable"] and row["feature_valid"] and
                all(finite(row[k]) for k in ("low", "high", "ema20", "ema50")) and row["low"] <= row["high"])
            departure = bool(valid_geometry and slow["full_departure"])
            if departure and (active is None or not previous_departure):
                finish("new_departure", stamp)
                side = slow["side"]
                identity = f"{product}|{int(interval)}m|{row['contract']}|{stamp.isoformat()}|{side}|shared_episode"
                active = dict(shared_episode_id=identity, product=product, interval_minutes=int(interval),
                    contract=row["contract"], direction=slow["direction"], side=side,
                    start_timestamp=stamp, start_available_at=row["available_at"],
                    last_timestamp=stamp, last_available_at=row["available_at"],
                    start_in_development=in_development(stamp), contains_development=in_development(stamp),
                    first_fast_event_id=None, first_fast_timestamp=None, first_fast_in_development=False,
                    first_slow_event_id=None, first_slow_timestamp=None, first_slow_in_development=False)
            ft = bool(valid_geometry and row["low"] <= row["ema20"] <= row["high"])
            st = bool(valid_geometry and row["low"] <= row["ema50"] <= row["high"])
            geometry = "undefined" if not valid_geometry else "both" if ft and st else "fast_only" if ft else "slow_only" if st else "neither"
            accepted_membership = "both" if fast["accepted"] and slow["accepted"] else "fast_only" if fast["accepted"] else "slow_only" if slow["accepted"] else "neither"
            member = {key: row[key] for key in ("product", "interval_minutes", "contract", "timestamp", "available_at")}
            member.update(direction=slow["direction"], side=slow["side"], eligible=bool(row["usable"] and row["feature_valid"]),
                fast_touch=ft, slow_touch=st, geometry=geometry, accepted_membership=accepted_membership,
                full_departure=departure, reset_reason=slow["reset_reason"],
                shared_episode_id=active["shared_episode_id"] if active else None)
            for branch, decision in (("fast", fast), ("slow", slow)):
                member.update({branch + "_accepted": decision["accepted"], branch + "_event_id": decision["event_id"],
                    branch + "_reason": decision["suppression_reason"], branch + "_armed_before": decision["armed_before"],
                    branch + "_armed_after": decision["armed_after"], branch + "_penetration": decision["penetration"]})
                if active is not None and decision["accepted"] and active["first_" + branch + "_event_id"] is None:
                    active["first_" + branch + "_event_id"] = decision["event_id"]
                    active["first_" + branch + "_timestamp"] = stamp
                    active["first_" + branch + "_in_development"] = in_development(stamp)
            if active is not None:
                active["last_timestamp"], active["last_available_at"] = stamp, row["available_at"]
                active["contains_development"] |= in_development(stamp)
                episode_slots.append(member)
            if member_callback is not None:
                member_callback(member)
            if materialize_membership:
                membership.append(member)
            if in_development(stamp) and accepted_membership != "neither":
                representative = lookup[slow["event_id"] if slow["accepted"] else fast["event_id"]]
                identity = f"{product}|{int(interval)}m|{stamp.isoformat()}|{slow['side']}|union"
                union.append(representative | dict(union_id=identity, event_id=identity,
                    touch_mode="union",
                    representative_event_id=representative["event_id"], fast_event_id=fast["event_id"],
                    slow_event_id=slow["event_id"], accepted_membership=accepted_membership,
                    shared_episode_id=member["shared_episode_id"]))
            previous_departure = departure
        finish("development_endpoint", END)
    return {"membership": pd.DataFrame(membership), "episodes": pd.DataFrame(episodes, columns=None if episodes else ["shared_episode_id"]),
            "pairs": pd.DataFrame(pairs, columns=None if pairs else ["pair_id"]), "union": pd.DataFrame(union, columns=None if union else ["union_id"])}


def week_roster():
    first, last = date(2018, 1, 1), date(2020, 12, 28)
    return [(first + timedelta(days=7 * i)).isoformat() for i in range((last - first).days // 7 + 1)]


def sampled_week_indices(block_weeks, resamples=10000, seed=20261010):
    """Direct calendar-index reference; compare means by sampled week gathering."""
    n = len(week_roster())
    require(int(block_weeks) >= 1 and int(resamples) >= 1, "positive bootstrap dimensions")
    starts = np.random.default_rng(seed).integers(0, n, size=(resamples, math.ceil(n / block_weeks)))
    return np.concatenate([(starts + offset)[:, :, None] for offset in range(block_weeks)], axis=2).reshape(resamples, -1)[:, :n] % n


def weekly_sufficient(outcomes, *, weighting="event", metric="terminal_delta", unit="points"):
    """Independently reduce evaluable paths to complete week sums/denominators."""
    weeks = week_roster()
    sums, counts = np.zeros(len(weeks)), np.zeros(len(weeks))
    week_position = {week: i for i, week in enumerate(weeks)}
    suffix = "_atr" if unit == "atr" and metric in METRICS else ""
    groups = {}
    for row in outcomes.itertuples(index=False):
        if row.status != "completed" or not all(finite(getattr(row, m + ("_atr" if unit == "atr" else ""))) for m in METRICS):
            continue
        value = float(getattr(row, metric + suffix))
        if weighting == "session":
            groups.setdefault(str(row.session), []).append(value)
        else:
            j = week_position[str(row.week)]
            sums[j] += value
            counts[j] += 1
    if weighting == "session":
        for session, values in groups.items():
            day = date.fromisoformat(session[:10])
            week = (day - timedelta(days=day.weekday())).isoformat()
            j = week_position[week]
            sums[j] += math.fsum(values) / len(values)
            counts[j] += 1
    return sums, counts


def reference_interval(fast, slow, *, block_weeks=4, resamples=10000, seed=20261010,
                       family_size=6, weighting="event", metric="terminal_delta", unit="points"):
    indices = sampled_week_indices(block_weeks, resamples, seed)
    branch = []
    for frame in (fast, slow):
        sums, counts = weekly_sufficient(frame, weighting=weighting, metric=metric, unit=unit)
        den = counts[indices].sum(axis=1)
        num = sums[indices].sum(axis=1)
        branch.append(np.divide(num, den, out=np.full(resamples, np.nan), where=den > 0))
    draws = branch[0] - branch[1]
    values = draws[np.isfinite(draws)]
    return dict(defined_draws=len(values), undefined_draws=resamples - len(values),
        ci_low=linear_quantile(values, .025), ci_high=linear_quantile(values, .975),
        familywise_low=linear_quantile(values, .05 / (2 * family_size)),
        familywise_high=linear_quantile(values, 1 - .05 / (2 * family_size)))
