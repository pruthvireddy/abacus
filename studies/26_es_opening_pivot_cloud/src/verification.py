"""Independent saved-input reconstruction; deliberately does not import engine/reporting.

The verifier reconstructs candidates and one-minute cash flows, including absent
trades and unavailable targets, before checking saved numerical aggregations.
"""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import datetime, time, timedelta
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from zoneinfo import ZoneInfo

import numpy as np

NY = ZoneInfo("America/New_York")
VARIANTS = [(entry, mask, exit_policy) for entry in ("early", "confirmed")
            for mask in "ABCD" for exit_policy in ("fixed_2r", "verne")]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def read_csv(path):
    with Path(path).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key, value in row.items():
            if value == "" or value in ("None", "null", "nan"):
                row[key] = None
            elif value in ("True", "False"):
                row[key] = value == "True"
            elif key not in ("date", "year", "cell"):
                try:
                    row[key] = float(value)
                except (TypeError, ValueError):
                    pass
    return rows


def aware(value):
    result = datetime.fromisoformat(value) if isinstance(value, str) else value
    require(isinstance(result, datetime) and result.tzinfo is not None, "Timestamp must be timezone aware")
    return result.astimezone(NY)


def bar_time(bar):
    return aware(bar.get("time", bar.get("open_time")))


def at(session, hour, minute=0):
    return datetime.combine(datetime.fromisoformat(session["date"]).date(), time(hour, minute), NY)


def compare(actual, expected, context, tolerance=1e-7):
    if expected is None:
        require(actual is None, f"{context}: expected undefined, found {actual!r}")
    elif isinstance(expected, bool):
        require(actual is expected, f"{context}: expected {expected}, found {actual!r}")
    elif isinstance(expected, (float, int)):
        require(isinstance(actual, (float, int)) and not isinstance(actual, bool)
                and math.isfinite(actual) and abs(actual - expected) <= tolerance,
                f"{context}: expected {expected!r}, found {actual!r}")
    elif isinstance(expected, datetime):
        require(actual is not None and aware(actual) == expected, f"{context}: timestamp mismatch")
    else:
        require(actual == expected, f"{context}: expected {expected!r}, found {actual!r}")


def reference_candidates(session, proximity=.10, stop_buffer=1.):
    """A separate episode-state implementation using the frozen seven signal bars."""
    if not session.get("eligible", True):
        return []
    bars = sorted(session["bars5"], key=bar_time)
    bars = [bar for bar in bars if at(session, 9, 25) <= bar_time(bar) <= at(session, 9, 55)]
    require(len(bars) == 7 and len({bar_time(bar) for bar in bars}) == 7, "Reference signal completeness")
    plan = session["plan"]
    low, high = plan["pivot_lower"], plan["pivot_upper"]
    memory, active, number, result = [bars[0]], None, 0, []
    for index, bar in enumerate(bars[1:], 1):
        completed = bar_time(bar) + timedelta(minutes=5)
        cloud = sorted((bar["ema20"], bar["ema50"]))
        consumed = False
        if active is None and bar_time(bar) < at(session, 9, 55):
            tolerance = math.ceil((max(1., proximity * bars[index - 1]["atr14"]) - 1e-10) * 4) / 4
            returned = bar["low"] <= high + tolerance and bar["high"] >= low - tolerance
            if returned:
                previous_short = [prior for prior in memory if prior["close"] <= low - tolerance]
                previous_long = [prior for prior in memory if prior["close"] >= high + tolerance]
                if previous_short and previous_long:
                    memory, consumed = [], True
                elif previous_short or previous_long:
                    direction = "short" if previous_short else "long"
                    prior = (previous_short or previous_long)[-1]
                    number += 1
                    active = dict(direction=direction, start=index, tolerance=tolerance, pivot=False,
                                  cloud=False, near=False, bars=[], approach=prior, number=number, separations=[])
        if active is not None:
            active["bars"].append(bar)
            tolerance = active["tolerance"]
            touch_pivot = bar["low"] <= high + tolerance and bar["high"] >= low - tolerance
            touch_cloud = bar["low"] <= cloud[1] + tolerance and bar["high"] >= cloud[0] - tolerance
            active["pivot"] |= touch_pivot
            active["cloud"] |= touch_cloud
            active["near"] |= (touch_pivot or touch_cloud) and max(low - cloud[1], cloud[0] - high, 0.) <= tolerance
            if touch_pivot or touch_cloud:
                active["separations"].append(max(low - cloud[1], cloud[0] - high, 0.))
            long = active["direction"] == "long"
            reaction = ((bar["close"] > bar["open"] and bar["close"] > cloud[1]) if long else
                        (bar["close"] < bar["open"] and bar["close"] < cloud[0]))
            if reaction and active["pivot"] and active["cloud"] and active["near"] and completed < at(session, 10):
                if long:
                    stop = math.floor((min(low, *(b["low"] for b in active["bars"])) - stop_buffer + 1e-10) * 4) / 4
                    ordering = bar["ema20"] > bar["ema50"]
                    slope = bar["ema20"] > bar["ema20_lag3"] and bar["ema50"] > bar["ema50_lag3"]
                else:
                    stop = math.ceil((max(high, *(b["high"] for b in active["bars"])) + stop_buffer - 1e-10) * 4) / 4
                    ordering = bar["ema20"] < bar["ema50"]
                    slope = bar["ema20"] < bar["ema20_lag3"] and bar["ema50"] < bar["ema50_lag3"]
                result.append(dict(date=session["date"], candidate_id=f"{session['date']}:{completed:%H%M}:{active['direction']}:{number}",
                                   direction=active["direction"], reaction_time=completed, reaction_open_time=bar_time(bar),
                                   episode_start_time=bar_time(bars[active["start"]]), formation_bars=len(active["bars"]),
                                   approach_time=bar_time(active["approach"]) + timedelta(minutes=5),
                                   approach_close=active["approach"]["close"], is_primary=not result,
                                   stop_price=stop, delta=tolerance, pivot_lower=low, pivot_upper=high,
                                   ordering_pass=bool(ordering), slope_pass=bool(slope),
                                   reaction_open=bar["open"], reaction_high=bar["high"], reaction_low=bar["low"],
                                   reaction_close=bar["close"], reaction_ema20=bar["ema20"], reaction_ema50=bar["ema50"],
                                   reaction_ema20_lag3=bar["ema20_lag3"], reaction_ema50_lag3=bar["ema50_lag3"],
                                   atr14=bar["atr14"], preopen_atr14=bars[0]["atr14"],
                                   first_touch_prior_atr14=bars[active["start"] - 1]["atr14"],
                                   pivot_width=high - low, pivot_kind="single" if low == high else "zone",
                                   pivot_description=plan.get("description", "unknown"),
                                   pivot_label_group=plan.get("label_group", "unknown"),
                                   quoted_contract=plan.get("quoted_contract"), available_at=plan.get("available_at"),
                                   cloud_width_points=cloud[1] - cloud[0], cloud_width_atr=(cloud[1] - cloud[0]) / bar["atr14"],
                                   pivot_cloud_separation=min(active["separations"]),
                                   reaction_pivot_cloud_separation=max(low - cloud[1], cloud[0] - high, 0.),
                                   opening_pivot_position="below" if bars[1]["open"] < low else "above" if bars[1]["open"] > high else "inside",
                                   opening_cloud_position="below" if bars[1]["open"] < min(bars[0]["ema20"], bars[0]["ema50"]) else "above" if bars[1]["open"] > max(bars[0]["ema20"], bars[0]["ema50"]) else "inside"))
                active, memory, consumed = None, [], True
            elif index - active["start"] >= 2 or completed >= at(session, 10):
                active, memory, consumed = None, [], True
        if not consumed:
            memory.append(bar)
    return result


def reference_outcome(session, candidate, entry_policy, mask, exit_policy, slippage=1):
    """Independent minute loop, including known-open ordering and absent policies."""
    result = dict(trade=False, candidate=candidate is not None, reason="no_candidate", net_dollars=0., net_r=None,
                  optimistic_net_dollars=0., optimistic_net_r=None, entry_time=None, entry_price=None,
                  exit_time=None, exit_price=None, exit_reason=None, target_price=None,
                  initial_risk_points=None, target_ordinal=None, target_source_row_id=None,
                  target_description=None,
                  ambiguity=False, ambiguity_count=0, fees_dollars=0., gross_dollars=None,
                  confirmation_time=None, confirmation_delay=None, coincident_entry=None)
    if candidate is None:
        return result
    if (mask in "BD" and not candidate["ordering_pass"]) or (mask in "CD" and not candidate["slope_pass"]):
        result["reason"] = "ema_filter_rejected"
        return result
    side = 1 if candidate["direction"] == "long" else -1
    stop = candidate["stop_price"]
    reaction = aware(candidate["reaction_time"])
    entry_time = reaction
    minutes = sorted(session["minutes"], key=bar_time)
    bars = sorted(session["bars5"], key=bar_time)
    def stopped(bar):
        return bar["low"] <= stop if side == 1 else bar["high"] >= stop
    if entry_policy == "confirmed":
        confirmation = []
        for bar in bars:
            completion = bar_time(bar) + timedelta(minutes=5)
            if reaction <= completion <= reaction + timedelta(minutes=15) and completion < at(session, 10):
                boundary = max(candidate["pivot_upper"], bar["ema20"], bar["ema50"]) if side == 1 else min(candidate["pivot_lower"], bar["ema20"], bar["ema50"])
                if side * (bar["close"] - boundary) > 0:
                    confirmation.append(completion)
        if not confirmation:
            wait_end = min(reaction + timedelta(minutes=15), at(session, 10))
            result["reason"] = "structural_invalidation" if any(reaction <= bar_time(b) < wait_end and stopped(b) for b in minutes) else "confirmation_expired"
            return result
        entry_time = confirmation[0]
        result.update(confirmation_time=entry_time, confirmation_delay=(entry_time - reaction).total_seconds() / 300,
                      coincident_entry=entry_time == reaction)
    if not at(session, 9, 30) <= entry_time < at(session, 10):
        result["reason"] = "entry_cutoff"
        return result
    if any(reaction <= bar_time(bar) < entry_time and stopped(bar) for bar in minutes):
        result["reason"] = "structural_invalidation"
        return result
    entry_bar = next(bar for bar in minutes if bar_time(bar) == entry_time)
    if side * (entry_bar["open"] - stop) <= 0:
        result["reason"] = "entry_open_beyond_stop"
        return result
    entry = entry_bar["open"] + side * .25 * slippage
    risk = side * (entry - stop)
    require(risk > 0, "Reference risk must be positive")
    if exit_policy == "fixed_2r":
        target, ordinal, source_id, description = entry + side * 2 * risk, None, None, "fixed 2R"
    else:
        possible = []
        for target_info in session["plan"]["targets"][candidate["direction"]][:2]:
            price = target_info["lower"] if side == 1 else target_info["upper"]
            if side * (price - entry) > 0:
                possible.append((side * (price - entry), price, target_info))
        if not possible:
            result.update(reason="target_unavailable", net_dollars=None, optimistic_net_dollars=None)
            return result
        _, target, info = min(possible, key=lambda item: item[0])
        ordinal, source_id, description = info.get("ordinal"), info.get("source_row_id"), info.get("description", "unknown")
    result.update(trade=True, reason="filled", entry_time=entry_time, entry_price=entry, initial_risk_points=risk,
                  target_price=target, target_ordinal=ordinal, target_source_row_id=source_id,
                  target_description=description, fees_dollars=5.,
                  entry_pivot_distance_points=max(candidate["pivot_lower"] - entry, entry - candidate["pivot_upper"], 0.))
    favorable, adverse = 0., 0.
    for bar in minutes:
        opened = bar_time(bar)
        if opened < entry_time:
            continue
        favorable = max(favorable, (bar["high"] - entry) if side == 1 else (entry - bar["low"]), 0.)
        adverse = max(adverse, (entry - bar["low"]) if side == 1 else (bar["high"] - entry), 0.)
        gap_stop = side * (bar["open"] - stop) <= 0
        gap_target = side * (bar["open"] - target) >= .25 - 1e-10
        hit_stop = stopped(bar)
        hit_target = bar["high"] >= target + .25 - 1e-10 if side == 1 else bar["low"] <= target - .25 + 1e-10
        optimistic = None
        if gap_stop:
            exit_price, exit_time, reason = bar["open"] - side * .25 * slippage, opened, "stop_gap"
        elif gap_target:
            exit_price, exit_time, reason = target, opened, "target"
        elif hit_stop:
            exit_price, exit_time, reason = stop - side * .25 * slippage, opened + timedelta(minutes=1), "stop"
            if hit_target:
                result.update(ambiguity=True, ambiguity_count=1)
                optimistic = target
        elif hit_target:
            exit_price, exit_time, reason = target, opened + timedelta(minutes=1), "target"
        elif opened == at(session, 10, 59):
            exit_price, exit_time, reason = bar["close"] - side * .25 * slippage, at(session, 11), "time"
        else:
            continue
        gross = side * (exit_price - entry) * 50
        net = gross - 5
        optimistic_net = side * ((exit_price if optimistic is None else optimistic) - entry) * 50 - 5
        result.update(exit_time=exit_time, exit_price=exit_price, exit_reason=reason, gross_dollars=gross,
                      net_dollars=net, net_r=net / (risk * 50), optimistic_net_dollars=optimistic_net,
                      optimistic_net_r=optimistic_net / (risk * 50), mae_points=adverse, mfe_points=favorable,
                      holding_minutes=(exit_time - entry_time).total_seconds() / 60,
                      target_distance_r=side * (target - entry) / risk)
        return result
    raise ValueError("Reference execution did not exit within complete minute window")


def independent_summary(rows):
    """Deterministic point estimates from saved daily rows, with explicit nulls."""
    values = [row["net_dollars"] for row in rows]
    defined = [v for v in values if v is not None]
    traded = [row for row in rows if row["trade"]]
    dollars = [row["net_dollars"] for row in traded]
    rs = [row["net_r"] for row in traded]
    wins, losses = [v for v in dollars if v > 0], [v for v in dollars if v < 0]
    complete = len(defined) == len(rows) and bool(rows)
    equity = peak = max_dd = 0.
    for row in sorted(rows, key=lambda r: r["date"]):
        if row["net_dollars"] is not None:
            equity += row["net_dollars"]
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
    ordered = sorted(rows, key=lambda row: row["date"])
    return dict(eligible_sessions=len(rows), defined_sessions=len(defined), unavailable_sessions=len(rows) - len(defined),
                start_date=ordered[0]["date"] if ordered else None, end_date=ordered[-1]["date"] if ordered else None,
                candidates=sum(row["candidate"] for row in rows), trades=len(traded),
                participation=len(traded) / len(rows) if rows else None,
                net_dollars=sum(defined) if complete else None,
                net_per_session=mean(defined) if complete else None,
                net_per_available_session=mean(defined) if defined else None,
                expectancy_dollars=mean(dollars) if dollars else None,
                expectancy_r=mean(rs) if rs else None, win_rate=len(wins) / len(dollars) if dollars else None,
                average_win_dollars=mean(wins) if wins else None, average_loss_dollars=mean(losses) if losses else None,
                payoff_ratio=mean(wins) / abs(mean(losses)) if wins and losses else None,
                profit_factor=sum(wins) / abs(sum(losses)) if losses else None,
                median_r=median(rs) if rs else None,
                p10_r=float(np.quantile(rs, .1)) if rs else None, p90_r=float(np.quantile(rs, .9)) if rs else None,
                max_drawdown_dollars=max_dd if complete else None,
                mean_stop_points=mean([r["initial_risk_points"] for r in traded]) if traded else None,
                mean_target_r=mean([r["target_distance_r"] for r in traded]) if traded else None,
                mean_achieved_reward_risk=mean([r["gross_dollars"] / (r["initial_risk_points"] * 50) for r in traded]) if traded else None,
                mean_mae_points=mean([r["mae_points"] for r in traded]) if traded else None,
                mean_mfe_points=mean([r["mfe_points"] for r in traded]) if traded else None,
                mean_holding_minutes=mean([r["holding_minutes"] for r in traded]) if traded else None,
                ambiguity_count=sum(row["ambiguity"] for row in traded), weak_evidence=len(traded) < 30,
                optimistic_net_dollars=sum(row["optimistic_net_dollars"] for row in rows) if complete else None)


def independent_bootstrap(values, dates, week=False):
    paired = [(v, d) for v, d in zip(values, dates) if v is not None]
    if not paired:
        return dict(estimate=None, ci_low=None, ci_high=None, tail_probability=None)
    groups = defaultdict(list)
    for i, (value, day) in enumerate(paired):
        iso = datetime.fromisoformat(day).isocalendar()
        groups[(iso.year, iso.week) if week else i].append(value)
    totals = np.array([sum(group) for group in groups.values()])
    sizes = np.array([len(group) for group in groups.values()])
    result = dict(estimate=mean(v for v, _ in paired), ci_low=None, ci_high=None, tail_probability=None)
    if len(groups) < 2:
        return result
    indices = np.random.default_rng(26021).integers(len(groups), size=(4000, len(groups)))
    draws = np.sum(totals[indices], axis=1) / np.sum(sizes[indices], axis=1)
    result.update(ci_low=float(np.quantile(draws, .025)), ci_high=float(np.quantile(draws, .975)),
                  tail_probability=min(1., 2 * min((sum(draws <= 0) + 1) / 4001, (sum(draws >= 0) + 1) / 4001)))
    return result


def independent_pair(early, confirmed, both_only=False, require_complete=False):
    a, b = {r["date"]: r for r in early}, {r["date"]: r for r in confirmed}
    require(set(a) == set(b), "Paired date populations differ")
    common = [(day, a[day], b[day]) for day in sorted(a) if a[day]["net_dollars"] is not None and b[day]["net_dollars"] is not None]
    selected = [(d, x, y) for d, x, y in common if not both_only or (x["trade"] and y["trade"])]
    differences = [x["net_dollars"] - y["net_dollars"] for _, x, y in selected]
    days = [d for d, _, _ in selected]
    day = independent_bootstrap(differences, days)
    week = independent_bootstrap(differences, days, True)
    both = [(a[d], b[d]) for d in a if a[d]["trade"] and b[d]["trade"]]
    candidate_count = sum(row["candidate"] for row in a.values())
    coincident = sum(x["entry_time"] == y["entry_time"] for x, y in both)
    full_denominator = not require_complete or len(common) == len(a)
    return dict(eligible_sessions=len(a), common_defined_sessions=len(common), paired_sessions=len(selected),
                unavailable_pairs=len(a) - len(common), both_filled=len(both),
                neither_filled=sum(not a[d]["trade"] and not b[d]["trade"] for d in a),
                coincident_entries=coincident, coincident_rate=coincident / len(both) if both else None,
                confirmation_rate=sum(row["trade"] for row in b.values()) / candidate_count if candidate_count else None,
                confirmed_fill_rate_per_candidate=sum(row["trade"] for row in b.values()) / candidate_count if candidate_count else None,
                left_only=sum(a[d]["trade"] and not b[d]["trade"] for d in a),
                right_only=sum(b[d]["trade"] and not a[d]["trade"] for d in a),
                left_mean=mean(x["net_dollars"] for _, x, _ in selected) if selected and full_denominator else None,
                right_mean=mean(y["net_dollars"] for _, _, y in selected) if selected and full_denominator else None,
                difference_dollars=day["estimate"] if full_denominator else None, available_pair_difference=day["estimate"],
                ci_low=day["ci_low"] if full_denominator else None, ci_high=day["ci_high"] if full_denominator else None,
                week_ci_low=week["ci_low"] if full_denominator else None, week_ci_high=week["ci_high"] if full_denominator else None,
                bootstrap_tail_probability=day["tail_probability"], weak_evidence=len(both) < 30,
                population="both_filled" if both_only else "all_eligible_days" if require_complete else "common_defined_days")


def reference_tags(row):
    """Declared one-way cut labels and fixed bins, independent of producer tags."""
    day = datetime.fromisoformat(row["date"])
    description = str(row.get("pivot_description") or "").upper()
    pivot_type = "+".join(token for token in ("HVE", "YPOC", "YVAL") if token in description)
    result = dict(year=str(day.year) + (" (partial)" if day.year in (2022, 2026) else ""),
                  split="development" if day.year <= 2024 else "validation" if day.year == 2025 else "temporal_test",
                  direction=row.get("direction") or "no_candidate", weekday=day.strftime("%A"),
                  entry_time=aware(row["entry_time"]).strftime("%H:%M") if row.get("entry_time") else "no_fill",
                  entry_policy=row["entry_policy"], mask=row["mask"],
                  confirmation_delay=str(int(row["confirmation_delay"])) if row.get("confirmation_delay") is not None else "unavailable",
                  pivot_type=pivot_type or ("other" if description else "unknown"),
                  pivot_kind=row.get("pivot_kind") or "unknown",
                  opening_pivot_position=row.get("opening_pivot_position") or "unknown",
                  opening_cloud_position=row.get("opening_cloud_position") or "unknown",
                  target_identity=f"{int(row['target_ordinal'])}: {row.get('target_description') or 'unknown'}" if row.get("target_ordinal") is not None else "fixed_2r" if row["exit_policy"] == "fixed_2r" else "unavailable",
                  exit_reason=row.get("exit_reason") or "no_fill",
                  execution_ambiguity="ambiguous" if row["ambiguity"] else "unambiguous" if row["trade"] else "no_fill")
    bins = {"pivot_width": (0, 1, 2, 5, 10), "pivot_cloud_separation": (0, 1, 2, 5, 10),
            "cloud_width_atr": (0, .25, .5, 1, 2), "preopen_atr14": (0, 2, 4, 8, 16),
            "initial_risk_points": (0, 2, 4, 8, 16), "entry_pivot_distance_points": (0, 1, 2, 5, 10),
            "target_distance_r": (0, .5, 1, 2, 3, 5)}
    for key, edges in bins.items():
        value = row.get(key)
        label = "unknown"
        if value is not None:
            value = abs(value)
            if key == "pivot_width" and value == 0:
                label = "single_price"
            else:
                for start, end in zip(edges, (*edges[1:], math.inf)):
                    if start <= value < end:
                        label = f"[{start:g}, {end:g})"
                        break
        result["prior_known_volatility" if key == "preopen_atr14" else key] = label
    return result


def verify_stage(stage):
    stage = Path(stage)
    with gzip.open(stage / "sessions.json.gz", "rt") as stream:
        sessions = json.load(stream)
    eligible = {session["date"]: session for session in sessions if session["eligible"]}
    require(len(eligible) == sum(bool(s["eligible"]) for s in sessions), "Duplicate cached session dates")
    daily, trades, candidates = (read_csv(stage / (name + ".csv")) for name in ("daily", "trades", "candidates"))
    metrics = json.loads((stage / "metrics.json").read_text())
    require(metrics["seed"] == 26021 and metrics["resamples"] == 4000, "Bootstrap seed/settings differ from freeze")
    groups, actual_by_date = defaultdict(list), defaultdict(list)
    seen = set()
    for row in daily:
        identity = (row["date"], row["entry_policy"], row["mask"], row["exit_policy"])
        require(identity not in seen, "Duplicate daily variant")
        seen.add(identity)
        require(row["date"] in eligible, "Daily row outside input-eligible population")
        groups[identity[1:]].append(row)
        actual_by_date[row["date"]].append(row)
    require(set(actual_by_date) == set(eligible), "Missing eligible daily session")
    require(len(daily) == len(eligible) * 16, "Daily count must be sixteen per eligible session")
    for day in eligible:
        require({(r["entry_policy"], r["mask"], r["exit_policy"]) for r in actual_by_date[day]} == set(VARIANTS),
                "Incomplete sixteen-variant population")
    saved_candidates = defaultdict(list)
    for row in candidates:
        saved_candidates[row["date"]].append(row)
    expected_candidate_count = 0
    outcome_comparisons = 0
    for day, session in eligible.items():
        expected = reference_candidates(session)
        expected_candidate_count += len(expected)
        actual = saved_candidates.get(day, [])
        require(len(actual) == len(expected), f"{day}: candidate inventory differs")
        for actual_candidate, expected_candidate in zip(actual, expected):
            for field, value in expected_candidate.items():
                compare(actual_candidate.get(field), value, f"{day}: candidate {field}")
        selected = expected[0] if expected else None
        for row in actual_by_date[day]:
            compare(row["candidate_id"], selected["candidate_id"] if selected else None, f"{day}: first candidate selection")
            result = reference_outcome(session, selected, row["entry_policy"], row["mask"], row["exit_policy"])
            for field, value in result.items():
                compare(row.get(field), value, f"{day}/{row['entry_policy']}/{row['mask']}/{row['exit_policy']}: {field}")
            outcome_comparisons += 1
    require(expected_candidate_count == len(candidates), "Unexpected saved candidate outside eligible dates")
    # Every trade is exactly the corresponding daily record, with no extra fill.
    actual_trade_map = {(r["date"], r["entry_policy"], r["mask"], r["exit_policy"]): r for r in trades}
    expected_trade_map = {(r["date"], r["entry_policy"], r["mask"], r["exit_policy"]): r for r in daily if r["trade"]}
    require(len(actual_trade_map) == len(trades) and set(actual_trade_map) == set(expected_trade_map), "Trade ledger population differs")
    for identity, row in expected_trade_map.items():
        saved = actual_trade_map[identity]
        require(all(saved.get(key) == row.get(key) for key in set(saved) | set(row)),
                f"Trade differs from daily row: {identity}")
    summary = read_csv(stage / "tables/variant_summary.csv")
    require(len(summary) == 16, "Variant summary row count")
    summary_cells = 0
    for table_row in summary:
        key = tuple(table_row[field] for field in ("entry_policy", "mask", "exit_policy"))
        require(key in groups, "Unknown summary variant")
        expected = independent_summary(groups[key])
        for field, value in expected.items():
            compare(table_row.get(field), value, f"{key}: summary {field}")
            summary_cells += 1
        for in_json in (r for r in metrics["variants"] if tuple(r[f] for f in ("entry_policy", "mask", "exit_policy")) == key):
            for field, value in expected.items():
                compare(in_json.get(field), value, f"metrics.json/{key}/{field}")
    for filename, partition in (("annual.csv", "year"), ("splits.csv", "split")):
        for row in read_csv(stage / "tables" / filename):
            key = tuple(row[field] for field in ("entry_policy", "mask", "exit_policy"))
            chosen = [r for r in groups[key] if (r["date"][:4] == str(row[partition]) if partition == "year" else r["split"] == row[partition])]
            for field, value in independent_summary(chosen).items():
                compare(row.get(field), value, f"{filename}/{key}/{row[partition]}/{field}")
                summary_cells += 1
    paired_cells = 0
    early, confirmed = groups[("early", "A", "fixed_2r")], groups[("confirmed", "A", "fixed_2r")]
    for row in read_csv(stage / "tables/primary_comparison.csv"):
        cohort = row["cohort"]
        choose = lambda rs: [r for r in rs if cohort == "pooled_exploratory" or r["split"] == cohort]
        expected_primary = independent_pair(choose(early), choose(confirmed), require_complete=True)
        json_rows = [r for r in metrics["primary"] if r["cohort"] == cohort]
        require(len(json_rows) == 1, "metrics.json primary cohort inventory")
        for field, value in expected_primary.items():
            compare(row.get(field), value, f"primary/{cohort}/{field}")
            compare(json_rows[0].get(field), value, f"metrics.json primary/{cohort}/{field}")
            paired_cells += 1
    for row in read_csv(stage / "tables/paired_entries.csv"):
        mask, exit_policy = row["mask"], row["exit_policy"]
        expected = independent_pair(groups[("early", mask, exit_policy)], groups[("confirmed", mask, exit_policy)], row["population"] == "both_filled")
        for field, value in expected.items():
            compare(row.get(field), value, f"paired/{mask}/{exit_policy}/{field}")
            paired_cells += 1
    for row in read_csv(stage / "tables/target_comparison.csv"):
        entry, mask = row["entry_policy"], row["mask"]
        expected = independent_pair(groups[(entry, mask, "verne")], groups[(entry, mask, "fixed_2r")], row["population"] == "both_filled")
        expected["verne_unavailable"] = sum(r["net_dollars"] is None for r in groups[(entry, mask, "verne")])
        for field, value in expected.items():
            compare(row.get(field), value, f"target/{entry}/{mask}/{field}")
            paired_cells += 1
    secondary = read_csv(stage / "tables/secondary_comparisons.csv")
    require(len(secondary) == 15, "Secondary family must have fifteen contrasts")
    probabilities = []
    for row in secondary:
        key = tuple(row[field] for field in ("entry_policy", "mask", "exit_policy"))
        require(key != ("early", "A", "fixed_2r"), "Primary cannot compare with itself in secondary family")
        expected = independent_pair(groups[key], early)
        for field, value in expected.items():
            compare(row.get(field), value, f"Secondary {key}/{field}")
            paired_cells += 1
        probabilities.append(expected["bootstrap_tail_probability"])
    adjusted = [None] * 15
    running = 0.
    for rank, (probability, index) in enumerate(sorted((value, i) for i, value in enumerate(probabilities) if value is not None)):
        running = max(running, min(1., probability * (15 - rank)))
        adjusted[index] = running
    for row, expected in zip(secondary, adjusted):
        compare(row["holm_tail_probability"], expected, "Fifteen-member Holm adjustment")
        paired_cells += 1
    cut_cells = 0
    expected_cuts = defaultdict(list)
    for row in daily:
        key = tuple(row[field] for field in ("entry_policy", "mask", "exit_policy"))
        tags = reference_tags(row)
        for name, cell in tags.items():
            expected_cuts[(*key, name, cell)].append(row)
        expected_cuts[(*key, "year_by_direction", tags["year"] + " | " + tags["direction"])].append(row)
        expected_cuts[(*key, "entry_by_mask", row["entry_policy"] + " | " + row["mask"])].append(row)
    actual_cuts = read_csv(stage / "tables/prespecified_cuts.csv")
    require(len(actual_cuts) == len(expected_cuts), "Prespecified cut inventory differs")
    seen_cuts = set()
    for row in actual_cuts:
        key = tuple(row[field] for field in ("entry_policy", "mask", "exit_policy", "cut", "cell"))
        require(key in expected_cuts and key not in seen_cuts, "Unknown or duplicate cut cell")
        seen_cuts.add(key)
        for field, expected in independent_summary(expected_cuts[key]).items():
            compare(row.get(field), expected, f"Cut {key}/{field}")
            cut_cells += 1
    primary_cuts = read_csv(stage / "tables/primary_cuts.csv")
    primary_full = [r for r in actual_cuts if (r["entry_policy"], r["mask"], r["exit_policy"]) == ("early", "A", "fixed_2r")]
    require(len(primary_cuts) == len(primary_full), "Primary cut projection row count")
    for projected, source in zip(primary_cuts, primary_full):
        for key, value in projected.items():
            compare(value, source[key], "Primary cut exact projection")
            cut_cells += 1
    # Rebuild every equity and drawdown point, preserving undefined tails.
    equity_by_variant = defaultdict(list)
    for row in read_csv(stage / "tables/equity.csv"):
        equity_by_variant[tuple(row[f] for f in ("entry_policy", "mask", "exit_policy"))].append(row)
    equity_points = 0
    for key, rows in groups.items():
        saved = equity_by_variant[key]
        require(len(saved) == len(rows), "Equity population count")
        cumulative = peak = 0.
        missing = False
        for raw, point in zip(sorted(rows, key=lambda r: r["date"]), saved):
            compare(point["date"], raw["date"], "Equity chronology")
            missing |= raw["net_dollars"] is None
            if raw["net_dollars"] is not None:
                cumulative += raw["net_dollars"]
            peak = max(peak, cumulative)
            compare(point["net_dollars"], raw["net_dollars"], "Equity daily return")
            compare(point["equity_dollars"], None if missing else cumulative, "Equity cumulative dollars")
            compare(point["drawdown_dollars"], None if missing else cumulative - peak, "Equity drawdown")
            equity_points += 1
    sensitivity_count = 0
    sensitivity_file = stage / "sensitivities.csv"
    if sensitivity_file.exists():
        settings = {"slippage_2": dict(slippage=2), "slippage_4": dict(slippage=4),
                    "stop_buffer_0.5": dict(stop_buffer=.5), "stop_buffer_1.5": dict(stop_buffer=1.5),
                    "proximity_0.05": dict(proximity=.05), "proximity_0.15": dict(proximity=.15)}
        reference_cache = {}
        sens_rows = read_csv(sensitivity_file)
        require(len(sens_rows) == len(eligible) * 12, "Sensitivity population")
        sens_identities = set()
        for row in sens_rows:
            identity = (row["date"], row["sensitivity"], row["entry_policy"])
            require(identity not in sens_identities, "Duplicate sensitivity identity")
            sens_identities.add(identity)
            session = eligible[row["date"]]
            setting = settings[row["sensitivity"]]
            cache_key = (row["date"], row["sensitivity"])
            if cache_key not in reference_cache:
                formed = reference_candidates(session, proximity=setting.get("proximity", .1), stop_buffer=setting.get("stop_buffer", 1.))
                reference_cache[cache_key] = formed[0] if formed else None
            selected = reference_cache[cache_key]
            compare(row["candidate_id"], selected["candidate_id"] if selected else None, "Sensitivity first candidate")
            expected = reference_outcome(session, selected, row["entry_policy"], "A", "fixed_2r", setting.get("slippage", 1))
            for field, value in expected.items():
                compare(row.get(field), value, f"Sensitivity {identity}/{field}")
            sensitivity_count += 1
        robustness = read_csv(stage / "tables/robustness.csv")
        require(len(robustness) == 6, "Six one-factor sensitivity summaries required")
        for row in robustness:
            scenario = [r for r in sens_rows if r["sensitivity"] == row["sensitivity"]]
            left = [r for r in scenario if r["entry_policy"] == "early"]
            right = [r for r in scenario if r["entry_policy"] == "confirmed"]
            expected = independent_pair(left, right, require_complete=True)
            expected.update(early_trades=sum(r["trade"] for r in left), confirmed_trades=sum(r["trade"] for r in right))
            for field, value in expected.items():
                compare(row.get(field), value, f"Robustness {row['sensitivity']}/{field}")
                paired_cells += 1
    checked_files = ["sessions.json.gz", "coverage.csv", "waterfall.csv", "daily.csv", "trades.csv", "candidates.csv", "metrics.json"]
    checked_files += [str(p.relative_to(stage)) for p in sorted((stage / "tables").glob("*.csv"))]
    if sensitivity_file.exists():
        checked_files.append("sensitivities.csv")
    for filename, expected_digest in metrics["tables"].items():
        require(digest(stage / "tables" / filename) == expected_digest, "Saved metrics table hash mismatch: " + filename)
    result = dict(schema_version="es-opening-pivot-cloud-scientific-verification/v1", status="passed",
                  study_id="26_es_opening_pivot_cloud", run_id=stage.name,
                  checks=dict(input_eligible_sessions=len(eligible), reconstructed_candidates=expected_candidate_count,
                              independently_reconstructed_daily_outcomes=outcome_comparisons,
                              independently_reconstructed_sensitivity_outcomes=sensitivity_count,
                              trades_reconciled=len(trades), summary_point_estimate_cells=summary_cells,
                              paired_counts_means_bootstrap_cells=paired_cells, cut_point_estimate_cells=cut_cells,
                              equity_points=equity_points),
                  qualification="Independent candidate state, reaction stop/masks, entry and minute execution; point summaries/cut classifications, paired bootstrap/Holm, sensitivity and equity reconstruction. Cut-specific interval cells are byte-pinned, not all independently recomputed; source-byte/input audits, native TradingView parity and Narada checks are separate.",
                  artifacts=[dict(path=name, sha256=digest(stage / name)) for name in checked_files])
    (stage / "scientific-verification.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def verify_publication(stage):
    """Check actual saved CSV cells and downloads, never trusting map.value alone."""
    stage = Path(stage).resolve()
    publication = json.loads((stage / "publication.json").read_text())
    source_map = json.loads((stage / "source-map.json").read_text())
    require(source_map["publication_id"] == publication["id"], "Publication/map identity differs")
    require(source_map["source_run_id"] == publication["source"]["runId"], "Publication/map source run differs")
    sections = {section["id"]: section for section in publication["sections"]}
    require(len(sections) == len(publication["sections"]), "Duplicate publication section")
    def local(relative):
        path = stage / relative
        require(isinstance(relative, str) and not Path(relative).is_absolute()
                and path.resolve().is_relative_to(stage) and path.is_file(), "Unsafe/missing publication source")
        return path
    source_tables = {}
    source_pins = {}
    checked = ["publication.json", "source-map.json"]
    for source in source_map["sources"]:
        name = source["artifact"]
        require(name not in source_pins, "Duplicate source-map artifact")
        require(digest(local(name)) == source["sha256"], "Publication source hash differs: " + name)
        source_pins[name] = source["sha256"]
        checked.append(name)
    bindings = set()
    for binding in source_map["bindings"]:
        name = binding["source_artifact"]
        require(name in source_pins, "Binding source lacks a hash pin")
        if name not in source_tables:
            source_tables[name] = read_csv(local(name))
        source_row = source_tables[name][binding["source_row"]]
        actual_source = source_row[binding["source_column"]]
        section = sections[binding["section"]]
        actual_public = section["rows"][binding["row"]][binding["column"]]
        compare(binding["value"], actual_source, "Source-map binding actual saved cell")
        compare(actual_public, actual_source, "Publication actual saved cell")
        key = (binding["section"], binding["row"], binding["column"])
        require(key not in bindings, "Duplicate public source-cell binding")
        bindings.add(key)
    for section in sections.values():
        if section["kind"] == "table":
            for row_number, row in enumerate(section["rows"]):
                for column in row:
                    require((section["id"], row_number, column) in bindings, "Unmapped publication table cell")
    downloads = {download["path"]: download for download in publication.get("downloads", [])}
    require(len(downloads) == len(publication.get("downloads", [])), "Duplicate download path")
    require(set(downloads) == {projection["path"] for projection in source_map.get("download_projections", [])}, "Download map inventory differs")
    download_cells = 0
    for projection in source_map.get("download_projections", []):
        name, source = projection["path"], projection["source"]
        download = downloads[name]
        require(source == download["source"], "Download source identity differs")
        require(source["artifact"] in source_pins and source["sha256"] == source_pins[source["artifact"]], "Download source hash is not pinned")
        require(source["runId"] == publication["source"]["runId"], "Download source run differs")
        require(digest(local(name)) == download["sha256"], "Download byte hash differs")
        require(projection["columns"] == download["columns"], "Download columns differ from map")
        rows, sources = read_csv(local(name)), read_csv(local(source["artifact"]))
        require(len(rows) == len(sources) == download["rowCount"], "Download row count differs")
        with local(name).open(newline="") as stream:
            require(next(csv.reader(stream)) == download["columns"], "Download actual header differs")
        for row, source_row in zip(rows, sources):
            for column in projection["columns"]:
                compare(row[column], source_row[column], "Download actual source-cell projection")
                download_cells += 1
        checked.append(name)
    for reference in publication.get("references", []):
        if reference.get("kind") == "saved-artifact":
            require(digest(local(reference["artifact"])) == reference["sha256"], "Publication reference bytes differ")
            require(reference["runId"] == publication["source"]["runId"], "Publication reference run differs")
    result = dict(schema_version="es-opening-pivot-cloud-independent-publication/v1", status="passed",
                  publication_id=publication["id"], source_run_id=publication["source"]["runId"],
                  checks=dict(actual_saved_table_cells=len(bindings), actual_saved_download_cells=download_cells,
                              source_artifacts=len(source_pins), downloads=len(downloads)),
                  qualification="Independent saved-source cell and byte projection audit; Narada schema, layout and browser checks remain separate.",
                  artifacts=[dict(path=name, sha256=digest(local(name))) for name in sorted(set(checked))])
    (stage / "independent-publication-verification.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result
