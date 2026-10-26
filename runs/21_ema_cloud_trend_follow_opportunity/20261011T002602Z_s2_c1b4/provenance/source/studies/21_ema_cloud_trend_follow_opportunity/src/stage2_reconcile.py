"""Independent Stage 2 ledger, uncertainty and selected-source reconciliation.

Numerical producer modules are deliberately absent. The maintained Stage 1
independent checker supplies only byte/mapping/coverage/CSV scalar utilities.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .reconcile import (sha256, _equal as base_equal, _raw_csv as raw_csv,
                        reconcile_mapping, reconcile_coverage)
from .stage2_contract import TABLES, BASELINE_RUN_ID, PRIMARY_FAMILY_ID
from .stage2_reference import (require, finite, in_development, iter_reference_stream,
    reference_membership, reference_outcomes, linear_quantile, week_roster,
    sampled_week_indices, weekly_sufficient, METRICS, FLAGS)

STATE_FIELDS = ("direction", "side", "signal_idx", "min_width", "width", "width_pass", "episode_id",
    "fast_touch", "slow_touch", "penetration", "full_departure", "armed_before", "armed_after",
    "technical_candidate", "setup_candidate", "accepted", "suppression_reason", "reset_reason", "event_id", "selected_ema")
OUTCOME_FIELDS = ("reference_price", "entry_atr", "direction", "timestamp", "entry_at", "horizon", "horizon_minutes",
    "status", "censor_reason", "terminal_at", "elapsed_minutes", "crosses_closure", "same_session") + METRICS + tuple(m + "_atr" for m in METRICS) + FLAGS + tuple(m + "_attainment_" + edge for m in ("mfe", "mae") for edge in ("start", "end"))
OUTCOME_FIELDS += ("product", "interval_minutes", "contract", "side", "signal_idx", "signal_timestamp", "available_at", "ema20", "ema50", "width", "episode_id")


def equal(actual, expected, context):
    if isinstance(expected, (bool, np.bool_)):
        require(isinstance(actual, (bool, np.bool_)), context + ": boolean type must be retained")
    base_equal(actual, expected, context)


def cell(raw, expected, context):
    """Strict CSV scalar reference: malformed flags/nonfinite strings fail."""
    if raw == "":
        equal(None, expected, context)
    elif expected is None or pd.isna(expected):
        raise ValueError(context + ": undefined cell must be blank")
    elif isinstance(expected, (bool, np.bool_)):
        require(raw in ("True", "False", "true", "false"), context + ": malformed boolean")
        equal(raw in ("True", "true"), expected, context)
    else:
        require(finite(float(raw)), context + ": nonfinite numeric string")
        equal(float(raw), expected, context)


def compare_frames(actual, expected, keys, *, fields=None, exact=False, context="ledger"):
    """Scientific-key comparison with explicit nulls; no row-order inference."""
    require(not actual.duplicated(keys).any() and not expected.duplicated(keys).any(), context + ": duplicate key")
    actual = actual.sort_values(keys, kind="stable").reset_index(drop=True)
    expected = expected.sort_values(keys, kind="stable").reset_index(drop=True)
    require(len(actual) == len(expected), context + ": population size")
    fields = list(expected.columns) if fields is None else list(fields)
    require(all(field in actual and field in expected for field in fields), context + ": required fields")
    count = 0
    for field in list(dict.fromkeys(list(keys) + fields)):
        for a, e in zip(actual[field], expected[field]):
            if exact and pd.notna(a) and pd.notna(e):
                require(a == e, context + "/" + field + ": exact mismatch")
            else:
                equal(a, e, context + "/" + field)
            count += 1
    return count


def reconcile_stream(bars, technical, events):
    """Stream scalar decisions without a whole technical-record dictionary."""
    require(set(technical.touch_mode.unique()) == {"fast", "slow"}, "both technical streams required")
    actual = {branch: iter(group.itertuples(index=False)) for branch, group in technical.groupby("touch_mode", sort=False)}
    causal, examined, fields = [], 0, 0
    for expected, event in iter_reference_stream(bars):
        got = next(actual[expected["touch_mode"]], None)
        require(got is not None, "missing technical reference row")
        got = got._asdict()
        for key in ("product", "interval_minutes", "timestamp") + STATE_FIELDS:
            equal(got[key], expected[key], "stream/" + key)
            fields += 1
        if event is not None:
            causal.append(event)
        examined += 1
    require(all(next(it, None) is None for it in actual.values()), "extra technical rows")
    causal = pd.DataFrame(causal, columns=list(events.columns) if not causal else None)
    scoped = causal.loc[causal.timestamp.map(in_development)] if len(causal) else causal
    required = [key for key in ("event_id", "product", "interval_minutes", "contract", "timestamp", "signal_idx",
        "reference_price", "entry_at", "entry_atr", "direction", "side", "year", "week", "month", "calendar_date", "hour", "time_stratum", "session", "touch_mode") if key in scoped]
    required += [key for key in ("available_at", "ema20", "ema50", "atr14", "width", "feature_source_timestamp", "feature_available_at", "feature_contract") if key in scoped]
    fields += compare_frames(events, scoped, ["event_id"], fields=required, context="accepted events")
    return {"check": "independent_scalar_two_stream_state", "status": "passed", "technical_rows": examined,
            "development_events": len(scoped), "fields": fields}, causal


def reconcile_paths(bars, events, outcomes):
    expected = reference_outcomes(bars, events)
    fields = compare_frames(outcomes, expected, ["event_id", "horizon"], fields=OUTCOME_FIELDS, context="independent outcomes")
    return {"check": "independent_scalar_all_forward_paths", "status": "passed", "rows": len(expected), "fields": fields}


def reconcile_memberships(bars, technical, causal, actual):
    member_columns = ["product", "interval_minutes", "timestamp", "contract", "available_at", "direction", "side",
        "eligible", "fast_touch", "slow_touch", "geometry", "accepted_membership", "full_departure", "reset_reason",
        "shared_episode_id"] + [branch + "_" + field for branch in ("fast", "slow") for field in
        ("accepted", "event_id", "reason", "armed_before", "armed_after", "penetration")]
    require(len(actual["membership"]) == len(bars), "membership roster length")
    member_rows = iter(actual["membership"][member_columns].itertuples(index=False))
    count = 0
    def check_member(expected):
        nonlocal count
        got = next(member_rows, None)
        require(got is not None, "missing membership row")
        for key, a in zip(member_columns, got):
            equal(a, expected[key], "membership/" + key)
            count += 1
    expected = reference_membership(bars, technical, causal, member_callback=check_member, materialize_membership=False)
    require(next(member_rows, None) is None, "extra membership row")
    for name, key in (("episodes", "shared_episode_id"), ("pairs", "pair_id")):
        count += compare_frames(actual[name], expected[name], [key], context="geometric " + name)
    union_fields = ["union_id", "event_id", "representative_event_id", "fast_event_id", "slow_event_id",
        "accepted_membership", "shared_episode_id", "touch_mode", "timestamp", "direction", "reference_price", "entry_atr", "entry_at", "signal_idx"]
    count += compare_frames(actual["union"], expected["union"], ["union_id"], fields=union_fields, context="union identity")
    return {"check": "independent_geometry_membership_episodes_union", "status": "passed", "fields": count,
        "episodes": len(expected["episodes"]), "pairs": len(expected["pairs"]), "union": len(expected["union"])}


def reconcile_dual_union(events, outcomes, union, union_outcomes):
    require(not union.duplicated(["product", "interval_minutes", "direction", "timestamp"]).any(), "union bar duplicate")
    lookup = outcomes.set_index(["event_id", "horizon"], verify_integrity=True)
    event_lookup = events.set_index("event_id", verify_integrity=True)
    fields = 0
    expected = []
    for row in union.itertuples(index=False):
        branch_ids = [v for v in (row.fast_event_id, row.slow_event_id) if pd.notna(v)]
        require(len(branch_ids) in (1, 2), "union source identities")
        first = event_lookup.loc[branch_ids[0]]
        if len(branch_ids) == 2:
            second = event_lookup.loc[branch_ids[1]]
            for key in ("reference_price", "direction", "entry_atr", "entry_at", "timestamp", "contract", "signal_idx"):
                a, b = first[key], second[key]
                require((pd.isna(a) and pd.isna(b)) or a == b, "same-bar exact event equality/" + key)
                fields += 1
        hs = (5, 10, 15, 20, 30, 50, 100) if row.interval_minutes == 3 else (5, 10, 12, 15, 20, 30, 50, 100)
        for h in hs:
            source = lookup.loc[(branch_ids[0], h)]
            if len(branch_ids) == 2:
                other = lookup.loc[(branch_ids[1], h)]
                for key in (key for key in OUTCOME_FIELDS if key not in ("episode_id", "horizon")):
                    a, b = source[key], other[key]
                    require((pd.isna(a) and pd.isna(b)) or a == b, "same-bar exact path equality/" + key)
                    fields += 1
            expected.append(lookup.loc[(row.representative_event_id, h)].to_dict() | dict(event_id=row.union_id, horizon=h,
                union_id=row.union_id, source_event_id=row.representative_event_id, representative_event_id=row.representative_event_id,
                fast_event_id=row.fast_event_id, slow_event_id=row.slow_event_id, touch_mode="union"))
    fields += compare_frames(union_outcomes, pd.DataFrame(expected), ["event_id", "horizon"],
        fields=OUTCOME_FIELDS + ("union_id", "source_event_id", "representative_event_id", "fast_event_id", "slow_event_id", "touch_mode"),
        exact=True, context="union outcome projection")
    return {"check": "same_bar_exact_equality_and_union_projection", "status": "passed", "fields": fields, "union_outcomes": len(expected)}


def _cohort(outcomes, row):
    cohort = outcomes[(outcomes["product"] == row["product"]) & (outcomes.interval_minutes == int(row["interval_minutes"])) &
        (outcomes.horizon == int(row["horizon"])) & (outcomes.touch_mode == row["touch_mode"])]
    if row.get("direction", "All") != "All":
        cohort = cohort[cohort.side == row["direction"]]
    if row.get("support", "all") == "same_session":
        cohort = cohort[cohort.same_session == True]
    elif row.get("support", "all") == "uninterrupted":
        cohort = cohort[cohort.crosses_closure == False]
    if "period_kind" in row:
        cohort = cohort[cohort[row["period_kind"]].astype(str) == str(row["period"])]
    complete = cohort[cohort.status == "completed"]
    suffix = "_atr" if row["unit"] == "atr" else ""
    good = complete[complete[[m + suffix for m in METRICS]].notna().all(axis=1)]
    return cohort, complete, good, suffix


def _summary_expected(cohort, complete, good, suffix):
    n, accepted = len(good), len(cohort)
    sessions = good.session.nunique()
    result = dict(accepted=accepted, completed=len(complete), censored=accepted - len(complete), evaluable=n,
        normalization_missing=len(complete) - n, contributing_sessions=sessions, contributing_weeks=good.week.nunique(),
        sparse_warning=n < 100 or sessions < 30)
    for metric in METRICS:
        values = good[metric + suffix].astype(float).tolist()
        result["mean_" + metric] = math.fsum(values) / n if n else None
        result["median_" + metric] = linear_quantile(values, .5)
        session_means = good.groupby("session")[metric + suffix].mean().tolist()
        result["session_mean_" + metric] = math.fsum(session_means) / len(session_means) if session_means else None
        for q in (.1, .25, .5, .75, .9, .95):
            result[f"{metric}_p{int(q * 100):02d}"] = linear_quantile(values, q)
    for flag in FLAGS:
        total = sum(bool(v) for v in good[flag])
        result[flag + "_count"] = total
        result[flag + "_share"] = total / n if n else None
        session_means = good[flag].astype(float).groupby(good.session).mean().tolist()
        result["session_" + flag + "_share"] = math.fsum(session_means) / len(session_means) if session_means else None
    favorable = int(complete.favorable.eq(True).sum()) if len(complete) else 0
    result.update(missing_worst_favorable_share=favorable / accepted if accepted else None,
        missing_best_favorable_share=(favorable + accepted - len(complete)) / accepted if accepted else None,
        mean_elapsed_minutes=float(good.elapsed_minutes.mean()) if n else None,
        closure_crossing_completed=int(complete.crosses_closure.eq(True).sum()),
        same_session_completed=int(complete.same_session.eq(True).sum()))
    return result


def reconcile_summary_tables(outcomes, tables, session_roster=None):
    count, cache = 0, {}
    def cohort_for(row):
        key = tuple(row.get(c, "") for c in ("product", "interval_minutes", "horizon", "direction", "support", "unit", "touch_mode"))
        if key not in cache:
            cache[key] = _cohort(outcomes, {k: v for k, v in row.items() if k not in ("period_kind", "period")})
        frames = cache[key]
        if "period_kind" in row:
            return tuple(frame[frame[row["period_kind"]].astype(str) == row["period"]] for frame in frames[:3]) + (frames[3],)
        return frames
    for name in ("S2-T02", "S2-T04", "S2-T05"):
        rows = raw_csv(tables[name])
        require(len({r["row_id"] for r in rows}) == len(rows), "duplicate summary row IDs")
        group_keys = ("product", "interval_minutes", "direction", "horizon", "unit", "support", "touch_mode")
        expected_groups = set()
        cells = set((r.product, int(r.interval_minutes), int(r.horizon), r.touch_mode) for r in outcomes.itertuples(index=False))
        for product, interval, h, branch in cells:
            if name != "S2-T02" and h != 15:
                continue
            for side, unit, support in itertools.product(("All", "Buy", "Sell"), ("points", "atr"), ("all", "uninterrupted", "same_session") if name == "S2-T02" else ("all",)):
                expected_groups.add(tuple(map(str, (product, interval, side, h, unit, support, branch))))
        require({tuple(row[key] for key in group_keys) for row in rows} == expected_groups, "complete inherited branch summary groups")
        if name == "S2-T02":
            require(len(rows) == len(expected_groups), "unique branch summary scientific keys")
        if name != "S2-T02":
            periods = ({"year": ["2018", "2019", "2020"], "time_stratum": ["Asia", "Europe", "US", "Late"], "hour": list(map(str, range(24))),
                       "session": sorted(map(str, session_roster if session_roster is not None else outcomes.session.unique()))} if name == "S2-T04" else
                       {"week": week_roster(), "month": [str(p) for p in pd.period_range("2018-01", "2020-12", freq="M")]})
            expected = {group + (kind, period) for group in expected_groups for kind, values in periods.items() for period in values}
            require(len(rows) == len(expected) and {tuple(row[key] for key in group_keys) + (row["period_kind"], row["period"]) for row in rows} == expected, "complete unique frozen stability period inventory")
        if name == "S2-T05":
            for _, group in itertools.groupby(sorted(rows, key=lambda r: (r["product"], r["interval_minutes"], r["direction"], r["unit"], r["touch_mode"], r["period_kind"])), key=lambda r: (r["product"], r["interval_minutes"], r["direction"], r["unit"], r["touch_mode"], r["period_kind"])):
                group = list(group)
                if group[0]["period_kind"] == "week":
                    require(sorted(r["period"] for r in group) == week_roster(), "full157 summary calendar roster")
        for row in rows:
            expected = _summary_expected(*cohort_for(row))
            require(all(key in row for key in expected), "summary scientific field absent")
            for key, value in expected.items():
                cell(row[key], value, name + "/" + row["row_id"] + "/" + key)
                count += 1
    quantile_rows = raw_csv(tables["S2-T03"])
    probabilities = tuple(sorted(set([i / 10 for i in range(11)] + [.25, .75, .95])))
    groups = {(str(r.product), str(int(r.interval_minutes)), side, str(int(r.horizon)), unit, "all", r.touch_mode) for r in outcomes.itertuples(index=False) for side, unit in itertools.product(("All", "Buy", "Sell"), ("points", "atr"))}
    expected_quantiles = {group + (metric, round(q, 10)) for group in groups for metric, q in itertools.product(METRICS, probabilities)}
    require(len(quantile_rows) == len(expected_quantiles) and {tuple(row[key] for key in group_keys) + (row["metric"], round(float(row["quantile"]), 10)) for row in quantile_rows} == expected_quantiles, "complete unique exact quantile grid")
    for row in quantile_rows:
        _, _, good, suffix = cohort_for(row)
        cell(row["value"], linear_quantile(good[row["metric"] + suffix].tolist(), float(row["quantile"])), "quantile/" + row["row_id"])
        cell(row["evaluable"], len(good), "quantile support")
        count += 2
    return {"check": "independent_complete_branch_summary_quantile_calendar", "status": "passed", "cells": count}


def reconcile_flow(technical, outcomes, path):
    count = 0
    scoped = technical.loc[pd.to_datetime(technical.timestamp, utc=True).map(in_development)]
    product, interval = str(technical["product"].iloc[0]), int(technical.interval_minutes.iloc[0])
    rows = [r for r in raw_csv(path) if r["product"] == product and int(r["interval_minutes"]) == interval]
    expected_keys = set()
    for branch, side in itertools.product(("fast", "slow"), ("All", "Buy", "Sell")):
        signals = scoped[scoped.touch_mode == branch]
        paths = outcomes[outcomes.touch_mode == branch]
        if side != "All":
            signals, paths = signals[signals.side == side], paths[paths.side == side]
        reasons = {"scheduled_slots", "usable_slots", "feature_valid_slots", "eligible_slots", "technical_candidates", "setup_candidates", "accepted", "eligible_sessions"}
        reasons |= {"suppressed:" + str(r) for r in signals.suppression_reason.dropna().unique()}
        expected_keys |= {(branch, side, "0", "signal", r) for r in reasons}
        for h, group in paths.groupby("horizon"):
            reasons = {"accepted", "completed", "censored"} | {"censor:" + r for r in group.loc[group.status == "censored", "censor_reason"].unique()}
            expected_keys |= {(branch, side, str(int(h)), "outcome", r) for r in reasons}
    keys = ("touch_mode", "direction", "horizon", "flow_kind", "reason")
    require(len(rows) == len(expected_keys) and {tuple(r[k] for k in keys) for r in rows} == expected_keys, "complete unique signal-flow scientific keys")
    for row in rows:
        source = outcomes if row["flow_kind"] == "outcome" else scoped
        group = source[source.touch_mode == row["touch_mode"]]
        if row["direction"] != "All":
            group = group[group.side == row["direction"]]
        reason = row["reason"]
        if row["flow_kind"] == "outcome":
            group = group[group.horizon == int(row["horizon"])]
            expected = len(group) if reason == "accepted" else int((group.status == reason).sum()) if reason in ("completed", "censored") else int(((group.status == "censored") & (group.censor_reason == reason.removeprefix("censor:"))).sum())
        else:
            columns = {"usable_slots": "usable", "feature_valid_slots": "feature_valid", "technical_candidates": "technical_candidate", "setup_candidates": "setup_candidate", "accepted": "accepted"}
            expected = len(group) if reason == "scheduled_slots" else int((group.usable & group.feature_valid).sum()) if reason == "eligible_slots" else group[group.usable & group.feature_valid].session.nunique() if reason == "eligible_sessions" else int(group[columns[reason]].sum()) if reason in columns else int((group.suppression_reason == reason.removeprefix("suppressed:")).sum())
        cell(row["count"], expected, "flow/" + row["row_id"])
        count += 1
    return {"check": "independent_flow", "status": "passed", "cells": count}


def reconcile_contrasts(outcomes, path, sufficient_path=None):
    """Every branch point estimate and saved interval independently reconstructed."""
    rows = raw_csv(path)
    require(len({r["row_id"] for r in rows}) == len(rows), "duplicate contrast keys")
    scientific_keys = ("product", "interval_minutes", "direction", "horizon", "unit", "support", "metric", "weighting", "block_weeks", "interval_type")
    expected_keys = set()
    for product, interval, h in set((r.product, int(r.interval_minutes), int(r.horizon)) for r in outcomes.itertuples(index=False)):
        for side, unit, support, metric, weighting in itertools.product(("All", "Buy", "Sell"), ("points", "atr"), ("all", "uninterrupted", "same_session"), METRICS + ("favorable", "mfe_gt_mae"), ("event", "session")):
            expected_keys.add(tuple(map(str, (product, interval, side, h, unit, support, metric, weighting, 0, "descriptive"))))
    for product, interval in itertools.product(("ES", "GC", "NQ"), (3, 5)):
        for h, side, unit, support, metric, weighting, block in itertools.product((15, 20, 50) if interval == 3 else (15, 12, 30), ("All", "Buy", "Sell"), ("points", "atr"), ("all", "uninterrupted"), METRICS + ("favorable", "mfe_gt_mae"), ("event", "session"), (1, 4, 8)):
            prefix = tuple(map(str, (product, interval, side, h, unit, support, metric, weighting, block)))
            expected_keys.add(prefix + ("pointwise95",))
            if (h, side, unit, support, metric, weighting) == (15, "All", "points", "all", "terminal_delta", "event"):
                expected_keys.add(prefix + ("bonferroni",))
    require(len(rows) == len(expected_keys) and {tuple(row[key] for key in scientific_keys) for row in rows} == expected_keys, "complete unique frozen contrast/uncertainty key inventory")
    groups, weekly, draws = {}, {}, {}
    indices = {}
    count = 0
    def branch_data(row, branch):
        key = tuple(row[k] for k in ("product", "interval_minutes", "direction", "horizon", "unit", "support", "metric", "weighting")) + (branch,)
        if key not in groups:
            group, complete, good, suffix = _cohort(outcomes, row | {"touch_mode": branch})
            metric = row["metric"] + (suffix if row["metric"] in METRICS else "")
            vals = good[metric].astype(float)
            if row["weighting"] == "session":
                vals = vals.groupby(good.session).mean()
            estimate = math.fsum(vals) / len(vals) if len(vals) else None
            groups[key] = (estimate, dict(accepted=len(group), completed=len(complete), censored=len(group) - len(complete),
                evaluable=len(good), sessions=good.session.nunique(), weeks=good.week.nunique()))
            weekly[key] = weekly_sufficient(group, weighting=row["weighting"], metric=row["metric"], unit=row["unit"])
        return key, groups[key]
    for row in rows:
        keys, estimates = {}, {}
        sparse = False
        for branch in ("fast", "slow"):
            key, (estimate, support) = branch_data(row, branch)
            keys[branch], estimates[branch] = key, estimate
            cell(row[branch + "_estimate"], estimate, "branch estimate")
            for field, value in support.items():
                cell(row[branch + "_" + field], value, "branch support")
                count += 1
            sparse |= support["evaluable"] < 100 or support["sessions"] < 30
        estimate = estimates["fast"] - estimates["slow"] if all(v is not None for v in estimates.values()) else None
        cell(row["estimate"], estimate, "fast-minus-slow")
        cell(row["sparse_warning"], sparse, "contrast sparsity")
        block = int(row["block_weeks"])
        if block:
            resamples, seed = int(row.get("resamples", 10000)), int(row.get("seed", 20261010))
            require(resamples == 10000 and seed == 20261010 and block in (1, 4, 8), "frozen bootstrap settings")
            if block not in indices:
                indices[block] = sampled_week_indices(block, resamples, seed)
            branch_draws = []
            for branch in ("fast", "slow"):
                draw_key = (keys[branch], block)
                if draw_key not in draws:
                    sums, ns = weekly[keys[branch]]
                    den = ns[indices[block]].sum(axis=1)
                    num = sums[indices[block]].sum(axis=1)
                    draws[draw_key] = np.divide(num, den, out=np.full(resamples, np.nan), where=den > 0)
                branch_draws.append(draws[draw_key])
            valid = branch_draws[0] - branch_draws[1]
            valid = valid[np.isfinite(valid)]
            primary = row["direction"] == "All" and int(row["horizon"]) == 15 and row["unit"] == "points" and row["support"] == "all" and row["metric"] == "terminal_delta" and row["weighting"] == "event"
            if row["interval_type"] == "bonferroni":
                require(primary and row["family_id"] == PRIMARY_FAMILY_ID, "Bonferroni outside frozen family")
                tails, coverage = (.05 / 12, 1 - .05 / 12), 1 - .05 / 6
                cell(row["family_size"], 6, "six primary family")
            else:
                require(row["interval_type"] == "pointwise95", "unknown interval definition")
                tails, coverage = (.025, .975), .95
            for field, value in ("ci_low", linear_quantile(valid, tails[0])), ("ci_high", linear_quantile(valid, tails[1])), ("coverage", coverage), ("tail_low", tails[0]), ("tail_high", tails[1]), ("defined_draws", len(valid)), ("undefined_draws", resamples - len(valid)):
                cell(row[field], value, "independent paired interval/" + field)
                count += 1
        else:
            require(row["interval_type"] == "descriptive" and row["ci_low"] == row["ci_high"] == "", "undefined descriptive CI")
        count += 4
    for block in (1, 4, 8):
        family = [r for r in rows if int(r["block_weeks"]) == block and r["interval_type"] == "bonferroni"]
        require(len(family) == 6 and {(r["product"], r["interval_minutes"]) for r in family} == {(p, str(i)) for p in ("ES", "GC", "NQ") for i in (3, 5)}, "complete primary multiplicity family")
    if sufficient_path is not None:
        sufficient = raw_csv(sufficient_path)
        require(len({r["row_id"] for r in sufficient}) == len(sufficient), "weekly sufficient unique rows")
        positions = {w: i for i, w in enumerate(week_roster())}
        by_key = {}
        for row in sufficient:
            key, (estimate, _) = branch_data(row, row["touch_mode"])
            require(row["week"] in positions, "week outside frozen157")
            j = positions[row["week"]]
            sums, ns = weekly[key]
            cell(row["sum"], sums[j], "weekly sum")
            cell(row["count"], ns[j], "weekly count")
            cell(row["cohort_estimate"], estimate, "weekly cohort estimate")
            by_key.setdefault(key, []).append(row["week"])
            count += 3
        require(all(sorted(v) == week_roster() for v in by_key.values()), "complete weekly sufficient roster")
        expected_groups = {tuple(row[k] for k in ("product", "interval_minutes", "direction", "horizon", "unit", "support", "metric", "weighting")) + (branch,) for row in rows if int(row["block_weeks"]) > 0 for branch in ("fast", "slow")}
        require(set(by_key) == expected_groups and len(sufficient) == len(expected_groups) * 157, "complete unique sufficient-statistic group inventory")
    return {"check": "independent_all_branch_contrasts_paired_uncertainty", "status": "passed", "rows": len(rows), "cells": count,
        "method": "Direct gathered sampled calendar indices, independent event/session reductions, exact linear tails.", "numeric_tolerance": 2e-10}


def reconcile_inherited_uncertainty(outcomes, bootstrap_path, comparison_path):
    """All fast/slow cohort and within-branch duration intervals, not a sample."""
    cache, indices, count = {}, {}, 0
    def get(row, interval, horizon):
        block = int(row["block_weeks"])
        key = (row["touch_mode"], row["product"], interval, row["direction"], horizon,
               row["unit"], row["metric"], row["weighting"], block)
        if key not in cache:
            q = row | dict(interval_minutes=interval, horizon=horizon, support="all")
            _, _, good, suffix = _cohort(outcomes, q)
            column = row["metric"] + (suffix if row["metric"] in METRICS else "")
            values = good[column].astype(float)
            if row["weighting"] == "session":
                values = values.groupby(good.session).mean()
            estimate = math.fsum(values) / len(values) if len(values) else None
            sums, ns = weekly_sufficient(good, weighting=row["weighting"], metric=row["metric"], unit=row["unit"])
            if block not in indices:
                indices[block] = sampled_week_indices(block)
            den = ns[indices[block]].sum(axis=1)
            num = sums[indices[block]].sum(axis=1)
            cache[key] = estimate, np.divide(num, den, out=np.full(10000, np.nan), where=den > 0)
        return cache[key]
    rows = raw_csv(bootstrap_path)
    scientific = ("touch_mode", "product", "direction", "unit", "metric", "weighting", "block_weeks", "kind", "interval_minutes", "horizon", "comparison", "horizon_a", "horizon_b")
    expected_keys = set()
    for branch, product, interval in itertools.product(("fast", "slow"), ("ES", "GC", "NQ"), (3, 5)):
        for h, side, unit, metric, weight, block in itertools.product((15, 20, 50) if interval == 3 else (15, 12, 30), ("All", "Buy", "Sell"), ("points", "atr"), METRICS + ("favorable", "mfe_gt_mae"), ("event", "session"), (1, 4, 8)):
            expected_keys.add(tuple(map(str, (branch, product, side, unit, metric, weight, block, "cohort", interval, h, "", "", ""))))
    for branch, product, side, unit, metric, weight, block, comparison in itertools.product(("fast", "slow"), ("ES", "GC", "NQ"), ("All", "Buy", "Sell"), ("points", "atr"), METRICS, ("event", "session"), (1, 4, 8), ("same_horizon", "equal_active_60", "equal_active_150")):
        ha, hb = {"same_horizon": (15, 15), "equal_active_60": (20, 12), "equal_active_150": (50, 30)}[comparison]
        expected_keys.add(tuple(map(str, (branch, product, side, unit, metric, weight, block, "contrast", "", "", comparison, ha, hb))))
    require(len(rows) == len(expected_keys) and {tuple(row[k] for k in scientific) for row in rows} == expected_keys, "complete unique inherited uncertainty inventory")
    for row in rows:
        require(int(row["resamples"]) == 10000 and int(row["seed"]) == 20261010 and int(row["block_weeks"]) in (1, 4, 8), "inherited frozen bootstrap")
        if row["kind"] == "cohort":
            estimate, draws = get(row, int(row["interval_minutes"]), int(row["horizon"]))
        else:
            a, ad = get(row, 3, int(row["horizon_a"]))
            b, bd = get(row, 5, int(row["horizon_b"]))
            estimate = a - b if a is not None and b is not None else None
            draws = ad - bd
        good = draws[np.isfinite(draws)]
        for field, value in (("estimate", estimate), ("ci_low", linear_quantile(good, .025)),
            ("ci_high", linear_quantile(good, .975)), ("defined_draws", len(good)), ("undefined_draws", 10000 - len(good))):
            cell(row[field], value, "inherited interval/" + row["row_id"] + "/" + field)
            count += 1
    comparison_rows = raw_csv(comparison_path)
    keys = ("touch_mode", "product", "direction", "unit", "support", "comparison", "horizon_a", "horizon_b")
    views = [("same_horizon", h, h) for h in (5, 10, 15, 20, 30, 50, 100)] + [("equal_active_60", 20, 12), ("equal_active_150", 50, 30)]
    expected = {tuple(map(str, (b, p, s, u, support, comp, ha, hb))) for b, p, s, u, support, (comp, ha, hb) in itertools.product(("fast", "slow"), ("ES", "GC", "NQ"), ("All", "Buy", "Sell"), ("points", "atr"), ("all", "uninterrupted", "same_session"), views)}
    require(len(comparison_rows) == len(expected) and {tuple(row[k] for k in keys) for row in comparison_rows} == expected, "complete unique duration comparison inventory")
    for row in comparison_rows:
        qa = row | dict(interval_minutes=3, horizon=row["horizon_a"])
        qb = row | dict(interval_minutes=5, horizon=row["horizon_b"])
        ca, aa, ga, sa = _cohort(outcomes, qa)
        cb, ab, gb, sb = _cohort(outcomes, qb)
        for field, value in (("completed_a", len(aa)), ("completed_b", len(ab)), ("sessions_a", ga.session.nunique()), ("sessions_b", gb.session.nunique())):
            cell(row[field], value, "duration support")
            count += 1
        for metric in METRICS:
            for weighting, field in (("event", "difference_mean_"), ("session", "difference_session_mean_")):
                values = []
                for good, suffix in ((ga, sa), (gb, sb)):
                    vals = good[metric + suffix].astype(float)
                    if weighting == "session":
                        vals = vals.groupby(good.session).mean()
                    values.append(math.fsum(vals) / len(vals) if len(vals) else None)
                expected = values[0] - values[1] if all(v is not None for v in values) else None
                cell(row[field + metric], expected, "duration contrast")
                count += 1
    return {"check": "independent_all_inherited_cohort_duration_uncertainty", "status": "passed", "interval_rows": len(rows), "cells": count}


def reconcile_new_diagnostics(membership, pairs, union, outcomes, tables, pair_metrics_path):
    """Independently reconcile geometry, pair nulls/differences and union tables."""
    product, interval = str(membership["product"].iloc[0]), int(membership.interval_minutes.iloc[0])
    local = pd.to_datetime(membership.timestamp, utc=True).dt.tz_convert("America/New_York")
    member = membership.loc[local.dt.year.between(2018, 2020)].copy()
    member["year"] = local.loc[member.index].dt.year
    count = 0
    def local_rows(name):
        return [r for r in raw_csv(tables[name]) if r["product"] == product and int(r["interval_minutes"]) == interval]
    geometry_rows = local_rows("S2-T07")
    expected = {(side, kind, period, dim, category) for side, (kind, period), (dim, categories) in itertools.product(
        ("All", "Buy", "Sell"), (("all", "2018–2020"), ("year", "2018"), ("year", "2019"), ("year", "2020")),
        (("geometry", ("fast_only", "slow_only", "both", "neither", "undefined")), ("accepted_membership", ("fast_only", "slow_only", "both", "neither")))) for category in categories}
    require(len(geometry_rows) == len(expected) and {tuple(r[k] for k in ("direction", "period_kind", "period", "dimension", "category")) for r in geometry_rows} == expected, "complete unique geometry inventory")
    for row in geometry_rows:
        group = member if row["direction"] == "All" else member[member.side == row["direction"]]
        if row["period_kind"] == "year":
            group = group[group.year == int(row["period"])]
        selected = group[group[row["dimension"]] == row["category"]]
        scheduled, eligible = len(group), int(group.eligible.sum())
        fast, slow = int(group.fast_accepted.sum()), int(group.slow_accepted.sum())
        both = int((group.fast_accepted & group.slow_accepted).sum())
        expected = dict(scheduled_slots=scheduled, eligible_slots=eligible, count=len(selected),
            eligible_count=int(selected.eligible.sum()), scheduled_share=len(selected) / scheduled if scheduled else None,
            eligible_rate_per_1000=1000 * int(selected.eligible.sum()) / eligible if eligible else None,
            fast_accepted=fast, slow_accepted=slow, both_accepted=both, union_accepted=fast + slow - both)
        for key, value in expected.items():
            cell(row[key], value, "geometry membership/" + key)
            count += 1
    scoped_pairs = pairs[pairs.contains_development.fillna(False)]
    lookup = {(r["event_id"], int(r["horizon"])): r for r in outcomes.to_dict("records")}
    pair_lookup = {r["pair_id"]: r for r in scoped_pairs.to_dict("records")}
    metric_records = []
    observed_keys = set()
    with Path(pair_metrics_path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["product"] != product or int(row["interval_minutes"]) != interval:
                continue
            key = row["pair_id"], int(row["horizon"]), row["unit"]
            require(key not in observed_keys and row["pair_id"] in pair_lookup, "pair metric scientific key")
            observed_keys.add(key)
            pair = pair_lookup[row["pair_id"]]
            for field in ("slow_minus_fast_signal_minutes", "slow_minus_fast_reference_points", "direction_adjusted_slow_minus_fast_reference_points"):
                value = (float(pair["slow_minus_fast_reference_points"]) * int(pair["direction"]) if field.startswith("direction_adjusted") else pair[field]) if pair["pair_scope"] == "both_development" else None
                cell(row[field], value, "pair retained reference difference/" + field)
            fast = lookup.get((pair["first_fast_event_id"], key[1]))
            slow = lookup.get((pair["first_slow_event_id"], key[1]))
            status = "outside_pair_scope" if pair["pair_scope"] != "both_development" else "missing_saved_outcome" if fast is None or slow is None else "completed" if fast["status"] == slow["status"] == "completed" else "censored_counterpart"
            expected = {}
            suffix = "_atr" if row["unit"] == "atr" else ""
            for metric in METRICS:
                evaluable = status == "completed" and finite(fast.get(metric + suffix)) and finite(slow.get(metric + suffix))
                fv = float(fast[metric + suffix]) if evaluable else None
                sv = float(slow[metric + suffix]) if evaluable else None
                expected["fast_" + metric], expected["slow_" + metric] = fv, sv
                expected["difference_" + metric] = fv - sv if evaluable else None
            if status == "completed" and any(expected["difference_" + m] is None for m in METRICS):
                status = "normalization_missing"
            require(row["pair_outcome_status"] == status, "pair null/censor status")
            for branch, source in (("fast", fast), ("slow", slow)):
                require(row[branch + "_outcome_status"] == (source["status"] if source else ""), "pair constituent status")
                require(row[branch + "_censor_reason"] == (source["censor_reason"] if source else ""), "pair constituent censor")
            for key2, value in expected.items():
                cell(row[key2], value, "pair path metric/" + key2)
                count += 1
            metric_records.append(dict(side=pair["side"], horizon=key[1], unit=key[2], status=status, scope=pair["pair_scope"]) | expected)
    hs = (15, 20, 50) if interval == 3 else (15, 12, 30)
    require(observed_keys == {(p, h, u) for p in pair_lookup for h in hs for u in ("points", "atr")}, "all first pairs retain every fixed metric view")
    pairing_rows = local_rows("S2-T09")
    expected = set()
    dimensions = {"pair_relation": ("same_bar", "fast_before_slow", "slow_before_fast", "fast_only", "slow_only", "neither"),
        "pair_scope": ("both_development", "warmup_counterpart", "outside_scope", "unpaired_development", "unpaired_warmup", "no_accepted"),
        "pair_timing_reference": ("slow_minus_fast_signal_minutes", "slow_minus_fast_reference_points", "direction_adjusted_slow_minus_fast_reference_points"),
        **{k: ("true", "false", "unresolved") for k in ("same_bar_slow_contact", "strictly_later_slow_contact", "strictly_later_slow_signal")}}
    for side in ("All", "Buy", "Sell"):
        expected |= {(side, kind, category, "", "") for kind, cats in dimensions.items() for category in cats}
        if any(r["side"] == side or side == "All" for r in metric_records):
            expected |= {(side, "pair_metric", m, str(h), u) for m, h, u in itertools.product(METRICS, hs, ("points", "atr"))}
    require(len(pairing_rows) == len(expected) and {tuple(r[k] for k in ("direction", "summary_kind", "category", "horizon", "unit")) for r in pairing_rows} == expected, "complete unique episode-summary inventory")
    for row in pairing_rows:
        group = scoped_pairs if row["direction"] == "All" else scoped_pairs[scoped_pairs.side == row["direction"]]
        kind, category = row["summary_kind"], row["category"]
        if kind == "pair_metric":
            part = [r for r in metric_records if r["horizon"] == int(float(row["horizon"])) and r["unit"] == row["unit"] and (row["direction"] == "All" or r["side"] == row["direction"])]
            values = [r["difference_" + category] for r in part if r["status"] == "completed" and r["difference_" + category] is not None]
            expected = dict(selected_pairs=len(part), scoped_pairs=sum(r["scope"] == "both_development" for r in part),
                completed_pairs=sum(r["status"] == "completed" for r in part), evaluable=len(values),
                censored_pairs=sum(r["status"] == "censored_counterpart" for r in part),
                outside_scope_pairs=sum(r["status"] == "outside_pair_scope" for r in part),
                normalization_missing_pairs=sum(r["status"] == "normalization_missing" for r in part),
                mean_difference=math.fsum(values) / len(values) if values else None,
                median_difference=linear_quantile(values, .5), p10_difference=linear_quantile(values, .1),
                p90_difference=linear_quantile(values, .9), sparse_warning=len(values) < 100)
        elif kind == "pair_timing_reference":
            selected = group[group.pair_scope == "both_development"]
            values = [(float(r.slow_minus_fast_reference_points) * int(r.direction) if category == "direction_adjusted_slow_minus_fast_reference_points" else float(getattr(r, category))) for r in selected.itertuples(index=False)]
            expected = dict(scoped_pairs=len(selected), evaluable=len(values), mean_difference=math.fsum(values) / len(values) if values else None,
                median_difference=linear_quantile(values, .5), p10_difference=linear_quantile(values, .1), p90_difference=linear_quantile(values, .9), sparse_warning=len(values) < 100)
        else:
            selected = group if kind in ("pair_scope", "pair_relation") else group[group.first_fast_in_development.fillna(False)]
            if kind in ("pair_scope", "pair_relation"):
                n = int((selected[kind] == category).sum())
            else:
                n = int(selected[kind].isna().sum()) if category == "unresolved" else int(selected[kind].eq(category == "true").sum())
            expected = dict(count=n, episodes=len(group), share=n / len(selected) if len(selected) else None)
            if kind not in ("pair_scope", "pair_relation"):
                expected["descriptor_eligible"] = len(selected)
        for key, value in expected.items():
            cell(row[key], value, "episode summary/" + key)
            count += 1
    union_paths = []
    for row in union.itertuples(index=False):
        for h in ((5, 10, 15, 20, 30, 50, 100) if interval == 3 else (5, 10, 12, 15, 20, 30, 50, 100)):
            union_paths.append(lookup[(row.representative_event_id, h)] | dict(event_id=row.union_id, touch_mode="union"))
    paths = pd.DataFrame(union_paths)
    union_rows = local_rows("S2-T10")
    expected = {(side, "frequency", "", "", "") for side in ("All", "Buy", "Sell")}
    expected |= {(side, "outcome", str(int(h)), u, support) for side, h, u, support in itertools.product(("All", "Buy", "Sell"), paths.horizon.unique(), ("points", "atr"), ("all", "same_session", "uninterrupted"))}
    if ((paths.horizon == 15) & (paths.status == "completed")).any():
        expected |= {(side, "overlap", "15", "", "") for side in ("All", "Buy", "Sell")}
    require(len(union_rows) == len(expected) and {tuple(r[k] for k in ("direction", "summary_kind", "horizon", "unit", "support")) for r in union_rows} == expected, "complete unique union-summary inventory")
    for row in union_rows:
        group = member if row["direction"] == "All" else member[member.side == row["direction"]]
        kind = row["summary_kind"]
        if kind == "frequency":
            fast, slow, both = int(group.fast_accepted.sum()), int(group.slow_accepted.sum()), int((group.fast_accepted & group.slow_accepted).sum())
            eligible, n = int(group.eligible.sum()), fast + slow - both
            expected = dict(fast_accepted=fast, slow_accepted=slow, both_accepted=both, union_accepted=n,
                incremental_vs_slow=n - slow, incremental_fast_only=int((group.accepted_membership == "fast_only").sum()),
                fast_only=int((group.accepted_membership == "fast_only").sum()), slow_only=int((group.accepted_membership == "slow_only").sum()),
                scheduled_slots=len(group), eligible_slots=eligible, union_rate_per_1000=1000 * n / eligible if eligible else None,
                fast_rate_per_1000=1000 * fast / eligible if eligible else None, slow_rate_per_1000=1000 * slow / eligible if eligible else None,
                incremental_rate_per_1000=1000 * (n - slow) / eligible if eligible else None)
        elif kind == "outcome":
            q = row.copy()
            q["horizon"] = int(float(q["horizon"]))
            expected = _summary_expected(*_cohort(paths, q))
        else:
            group = paths[(paths.horizon == 15) & (paths.status == "completed")]
            if row["direction"] != "All":
                group = group[group.side == row["direction"]]
            active, overlaps, maximum = [], 0, 0
            for path in group.sort_values("entry_at").itertuples(index=False):
                start = pd.Timestamp(path.entry_at)
                active = [end for end in active if end > start]
                overlaps += bool(active)
                active.append(pd.Timestamp(path.terminal_at))
                maximum = max(maximum, len(active))
            expected = dict(completed_windows=len(group), windows_overlapping_prior=overlaps, max_concurrent_windows=maximum)
        for key, value in expected.items():
            cell(row[key], value, "union diagnostic/" + key)
            count += 1
    return {"check": "independent_geometry_episode_union_tables", "status": "passed", "cells": count, "pair_metric_rows": len(observed_keys)}


def reconcile_calendar_support(technical, tables):
    """Every annual/session/hour/calendar quality overlay from common support."""
    frame = technical[technical.touch_mode == "slow"].copy()
    local = pd.to_datetime(frame.timestamp, utc=True).dt.tz_convert("America/New_York")
    frame = frame[local.dt.year.between(2018, 2020)].copy()
    local = local.loc[frame.index]
    naive = local.dt.tz_localize(None)
    frame["year"] = local.dt.year.astype(str)
    frame["week"] = (naive.dt.normalize() - pd.to_timedelta(local.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    frame["month"] = local.dt.strftime("%Y-%m")
    frame["hour"] = local.dt.hour.astype(str)
    minute = local.dt.hour * 60 + local.dt.minute
    frame["time_stratum"] = np.where((minute >= 1080) | (minute < 180), "Asia", np.where(minute < 540, "Europe", np.where(minute < 960, "US", "Late")))
    frame["session"] = frame.session.astype(str)
    frame["eligible"] = frame.usable.fillna(False) & frame.feature_valid.fillna(False)
    product, interval = str(frame["product"].iloc[0]), int(frame.interval_minutes.iloc[0])
    lookup, count = {}, 0
    for side in ("All", "Buy", "Sell"):
        part = frame if side == "All" else frame[frame.side == side]
        for kind in ("year", "time_stratum", "hour", "week", "month", "session"):
            for period, group in part.groupby(kind, sort=False):
                lookup[(side, kind, str(period))] = (len(group), int(group.eligible.sum()))
    for name in ("S2-T04", "S2-T05"):
        for row in raw_csv(tables[name]):
            if row["product"] != product or int(row["interval_minutes"]) != interval:
                continue
            scheduled, eligible = lookup.get((row["direction"], row["period_kind"], row["period"]), (0, 0))
            accepted = int(row["accepted"])
            expected = dict(scheduled_slots=scheduled, eligible_slots=eligible, unknown_signal_slots=scheduled - eligible,
                coverage_complete=scheduled > 0 and scheduled == eligible)
            for key, value in expected.items():
                cell(row[key], value, "calendar common support/" + key)
                count += 1
            qualifier = "events_observed" if accepted else "auditable_eligible_support" if eligible else "no_eligible_support"
            require(row["zero_event_qualification"] == qualifier, "zero-event quality qualification")
            count += 1
    return {"check": "independent_full_common_calendar_coverage", "status": "passed", "cells": count}, set(frame.session)


def reconcile_examples(technical, events, outcomes, pairs, example_path, illustrated):
    """Independent extrema/chronological selection and exact capped source paths."""
    product, interval = str(technical["product"].iloc[0]), int(technical.interval_minutes.iloc[0])
    tech = technical[technical.timestamp.map(in_development)]
    primary = outcomes[outcomes.horizon == 15]
    event_lookup = {r["event_id"]: r for r in events.to_dict("records")}
    rows = [r for r in raw_csv(example_path) if r["product"] == product and int(r["interval_minutes"]) == interval]
    kinds = ("high_adverse", "rejected", "censored", "unresolved", "same_bar", "different_time")
    require(len(rows) == 6 and {r["kind"] for r in rows} == set(kinds), "all six deterministic classes required")
    path_keys, count = set(), 0
    for row in rows:
        kind = row["kind"]
        selected, paired, pair = None, None, None
        if kind in ("high_adverse", "censored"):
            candidates = [r for r in primary.to_dict("records") if r["status"] == ("completed" if kind == "high_adverse" else "censored")]
            if candidates:
                selected = min(candidates, key=lambda r: (-r["mae"], pd.Timestamp(r["timestamp"]), r["event_id"]) if kind == "high_adverse" else (pd.Timestamp(r["timestamp"]), r["event_id"]))
        elif kind == "rejected":
            candidates = [r._asdict() for r in tech[tech.technical_candidate & ~tech.accepted].itertuples(index=False)]
            if candidates:
                selected = min(candidates, key=lambda r: (pd.Timestamp(r["timestamp"]), r["touch_mode"], int(r["signal_idx"])))
        else:
            candidates = []
            for p in pairs.to_dict("records"):
                eligible = bool(p["first_fast_in_development"]) and pd.isna(p["strictly_later_slow_contact"]) and p["same_bar_slow_contact"] is not None and p["same_bar_slow_contact"] == False if kind == "unresolved" else bool(p["pair_in_development"]) and (p["pair_relation"] == "same_bar" if kind == "same_bar" else p["pair_relation"] in ("fast_before_slow", "slow_before_fast"))
                if not eligible:
                    continue
                ids = [p["first_fast_event_id"]] + ([] if kind == "unresolved" else [p["first_slow_event_id"]])
                require(all(x in event_lookup for x in ids), "example selected first event is outside scoped ledger")
                ordered = sorted((event_lookup[x] for x in ids), key=lambda r: (pd.Timestamp(r["timestamp"]), r["event_id"]))
                candidates.append((pd.Timestamp(ordered[0]["timestamp"]), ordered[0]["event_id"], ordered[-1]["event_id"], p["shared_episode_id"], p, ordered))
            if candidates:
                best = min(candidates, key=lambda r: r[:4])
                pair, selected_events = best[4:]
                selected, paired = selected_events[0], selected_events[-1] if len(selected_events) == 2 else None
        require(row["selection_status"] == ("selected" if selected else "unavailable"), "example explicit unavailable class")
        require(row["row_id"] == row["example_id"] == f"S2-T06|{product}|{interval}|{kind}", "example scientific identity")
        own_paths = illustrated[illustrated.example_id == row["example_id"]]
        if selected is None:
            require(len(own_paths) == 0 and all(row[k] == "" for k in ("event_id", "paired_event_id", "timestamp", "signal_idx", "touch_mode", "reference_price")), "unavailable class cannot have replacement")
            continue
        for key in ("event_id", "timestamp", "signal_idx", "touch_mode", "reference_price"):
            value = selected.get(key, selected.get("close") if key == "reference_price" else None)
            if key == "timestamp":
                equal(pd.Timestamp(row[key]), pd.Timestamp(value), "example timestamp")
            elif key in ("signal_idx", "reference_price"):
                cell(row[key], value, "example numeric source")
            else:
                require(row[key] == (str(value) if pd.notna(value) else ""), "example selected ID/branch")
            count += 1
        for key in ("mfe", "mae", "terminal_delta"):
            cell(row[key], selected.get(key), "example scored source/" + key)
        for key in ("suppression_reason", "status", "censor_reason"):
            value = selected.get(key)
            require(row[key] == (str(value) if value is not None and pd.notna(value) else ""), "example selected source/" + key)
        require(row["paired_event_id"] == (paired["event_id"] if paired else ""), "example first counterpart identity")
        if pair is not None:
            require(row["shared_episode_id"] == pair["shared_episode_id"] and row["pair_relation"] == pair["pair_relation"] and row["end_reason"] == pair["end_reason"], "example retrospective header")
        selected_events = [selected] + ([paired] if paired else [])
        expected_paths = set()
        for segment, event in enumerate(selected_events):
            branch, index = event["touch_mode"], int(event["signal_idx"])
            window = tech[(tech.touch_mode == branch) & tech.signal_idx.between(index - 10, index + 15)]
            expected_paths.update((segment, int(i)) for i in window.signal_idx)
            actual = own_paths[own_paths.segment_id == segment].sort_values("original_signal_idx")
            require(len(actual) == len(window) <= 26, "capped path population")
            require(actual.original_signal_idx.tolist() == window.signal_idx.astype(int).tolist(), "complete capped source slots")
            for key in ("timestamp", "available_at", "open", "high", "low", "close", "ema20", "ema50", "usable", "feature_valid", "contract", "direction"):
                for a, e in zip(actual[key], window[key]):
                    equal(a, e, "selected path source/" + key)
                    count += 1
            for a in actual.itertuples(index=False):
                require(in_development(a.timestamp), "reserved illustrated candle")
                equal(a.reference_price, event.get("reference_price", event.get("close")), "path reference close")
                equal(a.event_id, event.get("event_id"), "path selected ID")
                require(a.relative_slot == a.original_signal_idx - index and a.is_signal == (a.original_signal_idx == index), "relative slot/signal marker")
                expected_id = f"{row['example_id']}|{segment}|{a.original_signal_idx}"
                require(a.row_id == expected_id, "selected path stable identity")
                path_keys.add(a.row_id)
        require({(int(r.segment_id), int(r.original_signal_idx)) for r in own_paths.itertuples(index=False)} == expected_paths, "path has undeclared segment")
    return {"check": "independent_frozen_examples_and_capped_candles", "status": "passed", "classes": len(rows), "fields": count, "path_rows": len(path_keys)}


def verify_publication(stage):
    stage = Path(stage)
    publication = json.loads((stage / "publication.json").read_text())
    bindings = json.loads((stage / "source-bindings.json").read_text())
    require(sha256(stage / "publication.json") == bindings["publication_sha256"], "publication pin changed")
    sections = {s["id"]: s for s in publication["sections"]}
    cache = {}
    def source(item):
        path = stage / item["source_artifact"]
        path.resolve().relative_to(stage.resolve())
        require(sha256(path) == item["source_sha256"], "selected source pin changed")
        if path not in cache:
            cache[path] = raw_csv(path) if path.suffix == ".csv" else pd.read_parquet(path).to_dict("records")
        return cache[path]
    public, transferred, count = set(), set(), 0
    for section in publication["sections"]:
        if section["kind"] == "table":
            public.update((section["id"], i, key) for i, row in enumerate(section["rows"]) for key in row)
    for item in bindings["cells"]:
        row = source(item)[int(item["data_row_1_based"]) - 1]
        require(row[item["column"]] == item["source_raw"] and row.get("row_id", "") == item["row_id"], "selected original cell identity")
        require(all(row[key] in [str(v) for v in values] for key, values in item["selector"].items()), "cell selector membership")
        expected = None if row[item["column"]] == "" else float(row[item["column"]]) if item["conversion"] == "finite_float_or_null" else row[item["column"]]
        key = item["section"], int(item["output_row"]), item["column"]
        require(key not in transferred, "duplicate cell binding")
        transferred.add(key)
        equal(sections[key[0]]["rows"][key[1]][key[2]], expected, "table to public cell")
        count += 1
    require(public == transferred, "all public cells must bind exactly once")
    declarations = {d["id"]: d for d in publication.get("downloads", [])}
    downloaded_cells = 0
    for item in bindings["downloads"]:
        declaration = declarations[item["download"]]
        require(sha256(stage / item["path"]) == item["sha256"] == declaration["sha256"], "download bytes")
        rows = source(item)
        selected = [i for i, r in enumerate(rows, 1) if all(r[k] in [str(v) for v in vs] for k, vs in item["selector"].items())]
        downloaded = raw_csv(stage / item["path"])
        require(selected == item["data_rows_1_based"] and len(downloaded) == item["row_count"] == declaration["rowCount"], "download source selection")
        for target, i in zip(downloaded, selected):
            for column in item["columns"]:
                require(target[column] == rows[i - 1][column], "download retains exact saved string")
                downloaded_cells += 1
    require(set(declarations) == {i["download"] for i in bindings["downloads"]}, "all downloads bound")
    for claim in bindings["claims"]:
        originals = []
        for item in claim["sources"]:
            row = source(item)[item["data_row_1_based"] - 1]
            require(row["row_id"] == item["row_id"] and all(row[k] == v for k, v in item["source_raw"].items()), "claim original strings")
            originals.append(row)
        point, family = originals
        f = lambda v: "undefined" if v == "" else v
        low, high = family["ci_low"], family["ci_high"]
        qualifier = "familywise interval unavailable" if not low or not high else "familywise interval includes zero" if float(low) <= 0 <= float(high) else "familywise interval is entirely positive" if float(low) > 0 else "familywise interval is entirely negative"
        expected = (f"{point['product']} {point['interval_minutes']}m H15: fast-minus-slow mean signed terminal movement {f(point['estimate'])} points; "
            f"four-week pointwise 95% interval [{f(point['ci_low'])}, {f(point['ci_high'])}], six-contrast familywise interval [{f(low)}, {f(high)}]; {qualifier}. "
            f"Fast: {point['fast_accepted']} accepted, {point['fast_completed']} completed, {point['fast_censored']} censored; "
            f"slow: {point['slow_accepted']} accepted, {point['slow_completed']} completed, {point['slow_censored']} censored. Evidence rows {point['row_id']} and {family['row_id']}.")
        require(claim["claim"] == expected and expected in sections["findings"]["body"], "independent primary claim reconstruction")
        require(expected in (stage / "report.md").read_text() and expected in (stage / "advice.md").read_text(), "offline/advice claims")
    expected_cells = {(p, str(i)) for p, i in itertools.product(("ES", "GC", "NQ"), (3, 5))}
    claim_cells = {(c["sources"][0]["source_raw"]["product"], c["sources"][0]["source_raw"]["interval_minutes"]) for c in bindings["claims"]}
    require(len(bindings["claims"]) == 6 and claim_cells == expected_cells, "complete six primary claims")
    families = [source(c["sources"][1])[c["sources"][1]["data_row_1_based"] - 1] for c in bindings["claims"]]
    for family in families:
        require(family["family_id"] == PRIMARY_FAMILY_ID and family["interval_type"] == "bonferroni" and family["block_weeks"] == "4", "aggregate family rows")
    intervals = [(float(r["ci_low"]), float(r["ci_high"])) for r in families if r["ci_low"] and r["ci_high"]]
    headline = ("All six primary familywise intervals include zero; the prespecified comparison does not establish a pooled fast-versus-slow signed-terminal advantage." if len(intervals) == 6 and all(lo <= 0 <= hi for lo, hi in intervals) else
        "The six prespecified effects and their familywise intervals are shown individually below. Any interval excluding zero describes development population differences under the fixed rule, without causal or profitability interpretation.")
    require(publication["summary"] == headline and sections["findings"]["body"].startswith(headline), "independent aggregate primary headline")
    require(headline in (stage / "report.md").read_text() and headline in (stage / "advice.md").read_text(), "offline aggregate headline")
    for item in bindings["figures"]:
        require(sha256(stage / item["path"]) == item["sha256"] and sections[item["figure"]]["path"] == item["path"], "figure bytes/identity")
        for bound in item["sources"]:
            rows = source(bound)
            selected = [i for i, row in enumerate(rows, 1) if all(str(row[k]) in [str(v) for v in vs] for k, vs in bound["selector"].items())]
            if "data_rows_1_based" in bound:
                require(len(bound["data_rows_1_based"]) == len(set(bound["data_rows_1_based"])) and set(bound["data_rows_1_based"]) <= set(selected), "figure explicit original row selection")
            if "row_ids" in bound:
                require(len(bound["row_ids"]) == len(set(bound["row_ids"])) and set(bound["row_ids"]) <= {str(rows[i - 1]["row_id"]) for i in selected}, "figure stable row selection")
            require(all(all(k in r for k in bound["columns"]) for r in rows), "figure source columns")
    require({s["id"] for s in publication["sections"] if s["kind"] == "figure"} == {i["figure"] for i in bindings["figures"]}, "all figure sources bound")
    baseline = Path(__file__).resolve().parents[3] / "runs/21_ema_cloud_trend_follow_opportunity" / BASELINE_RUN_ID
    for item in bindings["baseline_sources"]:
        require(item["run_id"] == BASELINE_RUN_ID, "cross-run baseline attribution")
        path = Path(item["path"])
        path.resolve().relative_to(baseline.resolve())
        require(sha256(path) == item["sha256"], "cross-run baseline source byte pin")
    return {"check": "all_table_download_claim_figure_source_transfers", "status": "passed", "public_cells": count,
        "download_cells": downloaded_cells, "claims": len(bindings["claims"]), "figures": len(bindings["figures"]),
        "publication_sha256": sha256(stage / "publication.json"), "bindings_sha256": sha256(stage / "source-bindings.json"),
        "qualification": "Independent source selection/bytes; actual visual/browser QA and publisher contract validity remain separate."}


def verify_bundle(stage):
    """Full independent audit, bounded to one product/candle roster at a time."""
    from .stage2_execution import assert_frozen_sources
    from abacus_bhishma.paths import load_workspace_paths
    stage = Path(stage).resolve()
    workspace = Path(__file__).resolve().parents[3]
    source_inventory = assert_frozen_sources(stage, workspace)
    publication_root = load_workspace_paths(workspace).publication_root
    records = json.loads((stage / "events.manifest.json").read_text())["records"]
    tables = {key: stage / "tables" / filename for key, filename in TABLES.items()}
    paths = [stage / "config.json", stage / "protocol.md", stage / "inputs.lock.json", stage / "baseline.lock.json",
        stage / "events.manifest.json", stage / "provenance/source-inventory.json", stage / "provenance/slow-baseline-parity.json"]
    paths += list(tables.values()) + list((stage / "tables").glob("*.parquet")) + [stage / "tables" / name for name in
        ("S2-bootstrap.csv", "S2-duration-comparisons.csv", "S2-calendar-sufficient-statistics.csv", "S2-episode-pair-metrics.csv")]
    paths += [stage / name for name in ("publication.json", "source-bindings.json", "report.md", "report.html", "advice.md", "metrics.json", "exclusions.json")]
    paths += list((stage / "figures").glob("*.png")) + list((stage / "downloads").glob("*.csv"))
    lock = json.loads((stage / "inputs.lock.json").read_text())
    delivery_path = Path(lock["delivery"]["path"])
    if not delivery_path.is_absolute():
        delivery_path = publication_root / delivery_path
    require(sha256(delivery_path) == lock["delivery"]["sha256"], "immutable input delivery identity")
    delivery = json.loads(delivery_path.read_text())
    paths.append(delivery_path)
    def record_path(record):
        path = Path(record["path"])
        return path if path.is_absolute() else publication_root / path
    paths += [record_path(r) for r in records]
    native_records = [r for r in delivery["output_files"] if int(r.get("interval_minutes", 0)) == 5]
    paths += [record_path(r) for r in native_records]
    paths = sorted(set(paths))
    pins = [dict(path=str(p), bytes=p.stat().st_size, sha256=sha256(p)) for p in paths]
    own_sources = [Path(__file__), Path(__file__).with_name("stage2_reference.py"), Path(__file__).with_name("stage2_reporting.py"), Path(__file__).with_name("reconcile.py"), Path(__file__).with_name("reporting.py")]
    checker_pins = [dict(path=str(p), bytes=p.stat().st_size, sha256=sha256(p)) for p in own_sources]
    before = dict(schema_version=1, run_id=stage.name, scope="All six development cells; no reserved outcomes", input_output_identities=pins,
        checker_sources=checker_pins, source_inventory_sha256=sha256(stage / "provenance/source-inventory.json"))
    target = stage / "provenance/independent-stage2-before.json"
    require(not target.exists(), "independent audit attempt overwrite refused")
    target.write_text(json.dumps(before, indent=2, allow_nan=False) + "\n")
    parity = json.loads((stage / "provenance/slow-baseline-parity.json").read_text())
    require(parity["status"] == "passed", "slow parity must pass before full interpretation")
    baseline = workspace / "runs/21_ema_cloud_trend_follow_opportunity" / BASELINE_RUN_ID
    baseline_records = json.loads((baseline / "events.manifest.json").read_text())["records"]
    baseline_tables = list((baseline / "tables").glob("S1-*.csv"))
    for path in baseline_tables:
        require(sha256(path) == sha256(stage / "parity/slow" / path.name), "independent inherited slow table exact bytes/" + path.name)
    def read(record):
        path = record_path(record)
        require(path.stat().st_size == record["bytes"] and sha256(path) == record["sha256"], "declared ledger bytes")
        frame = pd.read_parquet(path)
        declared_rows = record.get("row_count", record.get("rows"))
        require(declared_rows is not None and len(frame) == declared_rows, "declared ledger rows")
        if record.get("branch"):
            require(frame.touch_mode.eq(record["branch"]).all(), "explicit branch identity")
        return frame
    def cell_role(cell_records, role):
        frames = [read(r) for r in cell_records if r["role"] == role]
        require(frames, "essential cell ledger absent/" + role)
        return pd.concat(frames, ignore_index=True)
    checks, outcomes_all, sessions = [], [], set()
    illustrated = pd.read_parquet(stage / "tables/selected-example-paths.parquet")
    require(not illustrated.row_id.duplicated().any(), "duplicate selected path identity")
    examples = raw_csv(tables["S2-T06"])
    require(len(examples) == 36 and len({r["example_id"] for r in examples}) == 36, "complete six-cell example roster")
    require(set(illustrated.example_id) <= {r["example_id"] for r in examples if r["selection_status"] == "selected"}, "undeclared illustrated example")
    checks.append(dict(check="independent_exact_slow_table_parity", status="passed", tables=len(baseline_tables), tolerance=0))
    for product in ("ES", "GC", "NQ"):
        native_five = read(next(r for r in native_records if r["product"] == product))
        for interval in (3, 5):
            cell_records = [r for r in records if r["product"] == product and int(r["interval_minutes"]) == interval]
            bars = cell_role(cell_records, "bars")
            technical = cell_role(cell_records, "technical").sort_values(["timestamp", "touch_mode"], kind="stable").reset_index(drop=True)
            events = cell_role(cell_records, "events")
            outcomes = cell_role(cell_records, "outcomes")
            slow = technical[technical.touch_mode == "slow"].reset_index(drop=True)
            for column in bars:
                require(bars[column].reset_index(drop=True).equals(slow[column].reset_index(drop=True)), "mapped/common technical source equality/" + column)
            checks.append(reconcile_mapping(slow, native_five))
            checks.append(reconcile_coverage(slow, native_five, tables["S2-T00"]))
            state, causal = reconcile_stream(bars, technical, events)
            checks.append(state)
            checks.append(reconcile_paths(bars, events, outcomes))
            for role, actual, keys in (("bars", bars, ["product", "interval_minutes", "timestamp"]), ("technical", slow, ["product", "interval_minutes", "timestamp"]),
                ("events", events[events.touch_mode == "slow"], ["event_id"]), ("outcomes", outcomes[outcomes.touch_mode == "slow"], ["event_id", "horizon"])):
                declared = next(r for r in baseline_records if r["product"] == product and int(r["interval_minutes"]) == interval and r["role"] == role)
                original = read(declared)
                columns = [c for c in original if c != "stage"]
                original = original.sort_values(keys, kind="stable").reset_index(drop=True)
                actual = actual.sort_values(keys, kind="stable").reset_index(drop=True)
                require(len(original) == len(actual), "slow scientific population exact parity")
                for column in columns:
                    require(original[column].equals(actual[column]), "independent exact inherited slow field/" + role + "/" + column)
                checks.append(dict(check="independent_exact_slow_" + role, status="passed", product=product, interval_minutes=interval, rows=len(original), fields=len(columns), tolerance=0))
                del original, actual
            members = {role: cell_role(cell_records, role) for role in ("membership", "episodes", "pairs", "union")}
            checks.append(reconcile_memberships(bars, technical, causal, members))
            checks.append(reconcile_dual_union(events, outcomes, members["union"], cell_role(cell_records, "union_outcomes")))
            checks.append(reconcile_flow(technical, outcomes, tables["S2-T01"]))
            support, cell_sessions = reconcile_calendar_support(technical, tables)
            checks.append(support)
            sessions.update(cell_sessions)
            checks.append(reconcile_new_diagnostics(members["membership"], members["pairs"], members["union"], outcomes, tables, stage / "tables/S2-episode-pair-metrics.csv"))
            checks.append(reconcile_examples(technical, events, outcomes, members["pairs"], tables["S2-T06"], illustrated))
            outcomes_all.append(outcomes)
            print(json.dumps(dict(independent_cell=f"{product}/{interval}", status="passed", checks=len(checks))), flush=True)
            del bars, technical, events, outcomes, slow, causal, members
        del native_five
    combined = pd.concat(outcomes_all, ignore_index=True)
    metrics = json.loads((stage / "metrics.json").read_text())
    equal(metrics["accepted_events"], combined.event_id.nunique(), "metrics total accepted")
    equal(metrics["outcome_rows"], len(combined), "metrics total paths")
    require(metrics["reserved_outcomes_computed"] is False, "reserved outcome guard")
    exclusions = json.loads((stage / "exclusions.json").read_text())
    for branch in ("fast", "slow"):
        group = combined[combined.touch_mode == branch]
        for field, expected in (("accepted", group.event_id.nunique()), ("completed_h15", int(((group.horizon == 15) & (group.status == "completed")).sum())), ("censored_h15", int(((group.horizon == 15) & (group.status == "censored")).sum()))):
            equal(metrics["branches"][branch][field], expected, "metrics branch/" + field)
        expected = {str(k): int(v) for k, v in group.loc[group.status == "censored", "censor_reason"].value_counts().items()}
        require(exclusions["path_counts"][branch] == expected, "all exclusions counts")
    checks.append(dict(check="independent_metrics_and_exclusions", status="passed"))
    checks.append(reconcile_summary_tables(combined, tables, session_roster=sessions))
    print(json.dumps(dict(independent_summaries="passed")), flush=True)
    uncertainty = reconcile_contrasts(combined, tables["S2-T08"], stage / "tables/S2-calendar-sufficient-statistics.csv")
    inherited_uncertainty = reconcile_inherited_uncertainty(combined, stage / "tables/S2-bootstrap.csv", stage / "tables/S2-duration-comparisons.csv")
    checks.extend([uncertainty, inherited_uncertainty])
    transfer = verify_publication(stage)
    checks.append(transfer)
    for pin in pins:
        p = Path(pin["path"])
        require(p.stat().st_size == pin["bytes"] and sha256(p) == pin["sha256"], "audit dependency drift")
    assert_frozen_sources(stage, workspace)
    receipt = dict(schema_version=1, study_id="21_ema_cloud_trend_follow_opportunity", run_id=stage.name, status="passed", checks=checks,
        input_output_identities=pins, checker_sources=checker_pins, before_execution=dict(path=str(target), sha256=sha256(target)),
        scope="Full independent scalar stream/path/membership/episode/union replay, exact slow scientific parity, all summaries/coverage/uncertainty and selected-source transfer; no producer numerical imports.",
        qualifications="Native chart equivalence, original raw reconstruction/receipt times, annual-calendar certification and off-device backup remain unverified. No reserved outcome or profitability calculation.")
    for name, result in (("independent-uncertainty.json", [uncertainty, inherited_uncertainty]), ("independent-presentation-transfer.json", [transfer])):
        (stage / "provenance" / name).write_text(json.dumps(dict(status="passed", run_id=stage.name, checks=result, input_output_identities=pins, checker_sources=checker_pins), indent=2, allow_nan=False) + "\n")
    return receipt
