"""Stage 2 saved-evidence statistics, preserving every inherited slow estimator.

Production reads audited saved ledgers. It neither generates signals nor scores
future prices. Large technical/membership rosters are read one cell at a time.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import statistics as inherited
from .engine import _strata
from .execution import file_record, verify_record
from .stage2_contract import ACCEPTED_MEMBERSHIP_VALUES, BRANCHES, GEOMETRY_VALUES, PAIR_ORDER_VALUES, TABLES
from .stage2_comparisons import branch_contrasts, calendar_sufficient_statistics, paired_uncertainty, validate_outcomes


def _wrap(frame, branch, table):
    result = frame.copy()
    if result.empty:
        return result
    result["stage"], result["touch_mode"] = 2, branch
    # Inherited row IDs are selectors, not scientific quantities. Keep their
    # complete original key after an explicit stage/branch wrapper.
    result["row_id"] = table + "|" + branch + "|" + result.row_id.astype(str)
    return result


def _branches(outcomes):
    validate_outcomes(outcomes)
    for branch in BRANCHES:
        yield branch, outcomes.loc[outcomes.touch_mode.eq(branch)].copy()


def _concat(parts):
    nonempty = [part for part in parts if not part.empty]
    return pd.concat(nonempty, ignore_index=True) if nonempty else pd.DataFrame()


def summarize_branches(outcomes, supports=("all",)):
    return _concat([_wrap(inherited.summarize(group, supports), branch, "S2-T02") for branch, group in _branches(outcomes)])


def quantiles_branches(outcomes):
    return _concat([_wrap(inherited.quantiles(group), branch, "S2-T03") for branch, group in _branches(outcomes)])


def stability_branches(outcomes, session_roster=None):
    return _concat([_wrap(inherited.stability(group, session_roster), branch, "S2-stability") for branch, group in _branches(outcomes)])


def signal_flow_branches(technical, events, outcomes):
    validate_outcomes(outcomes)
    return _concat([_wrap(inherited.signal_flow(technical.loc[technical.touch_mode.eq(branch)],
                          events.loc[events.touch_mode.eq(branch)], outcomes.loc[outcomes.touch_mode.eq(branch)]),
                         branch, "S2-T01") for branch in BRANCHES])


def branch_cohort_uncertainty(outcomes, resamples=10000, seed=20261010, block_lengths=(4, 1, 8)):
    """Exact inherited cohort and within-branch candle-interval bootstrap."""
    return _concat([_wrap(inherited.bootstrap(group, resamples, seed, block_lengths), branch, "S2-bootstrap")
                    for branch, group in _branches(outcomes)])


def within_branch_comparisons(outcomes):
    return _concat([_wrap(inherited.comparisons(group), branch, "S2-duration-comparisons")
                    for branch, group in _branches(outcomes)])


def _development(frame):
    if frame.empty:
        return frame.copy()
    local = pd.to_datetime(frame.timestamp, utc=True).dt.tz_convert("America/New_York")
    return frame.loc[local.dt.year.between(2018, 2020)].copy()


def support_roster(technical):
    """Compact signal-time coverage roster, with no branch duplication."""
    tech = _strata(technical.loc[technical.touch_mode.eq("slow")].copy())
    tech = tech.loc[tech.year.between(2018, 2020)]
    tech["eligible"] = tech.usable.fillna(False) & tech.feature_valid.fillna(False)
    rows = []
    for kind in ("year", "time_stratum", "hour", "week", "month", "session"):
        for side in inherited.SIDES:
            subset = tech if side == "All" else tech.loc[tech.side.eq(side)]
            grouped = subset.groupby(["product", "interval_minutes", kind], observed=True).agg(
                scheduled_slots=("timestamp", "size"), eligible_slots=("eligible", "sum")).reset_index()
            grouped = grouped.rename(columns={kind: "period"})
            grouped["period"] = grouped.period.astype(str)
            grouped["direction"], grouped["period_kind"] = side, kind
            rows.append(grouped)
    return _concat(rows), sorted(tech.session.astype(str).unique())


def coverage_columns(table, roster):
    result = table.merge(roster, on=["product", "interval_minutes", "direction", "period_kind", "period"],
                         how="left", validate="many_to_one")
    for column in ("scheduled_slots", "eligible_slots"):
        result[column] = result[column].fillna(0).astype(int)
    result["unknown_signal_slots"] = result.scheduled_slots - result.eligible_slots
    result["coverage_complete"] = result.scheduled_slots.gt(0) & result.unknown_signal_slots.eq(0)
    result["zero_event_qualification"] = "events_observed"
    result.loc[result.accepted.eq(0) & result.eligible_slots.gt(0), "zero_event_qualification"] = "auditable_eligible_support"
    result.loc[result.accepted.eq(0) & result.eligible_slots.eq(0), "zero_event_qualification"] = "no_eligible_support"
    return result


def geometry_membership(membership):
    """Separate geometry from independent stream acceptance on common support."""
    m = _development(membership)
    if m.empty:
        return pd.DataFrame()
    m["year"] = pd.to_datetime(m.timestamp, utc=True).dt.tz_convert("America/New_York").dt.year
    rows = []
    for (product, interval), cell in m.groupby(["product", "interval_minutes"], sort=True):
        for side in inherited.SIDES:
            direction = cell if side == "All" else cell.loc[cell.side.eq(side)]
            for kind, period in [("all", "2018–2020")] + [("year", y) for y in (2018, 2019, 2020)]:
                group = direction if kind == "all" else direction.loc[direction.year.eq(period)]
                scheduled, eligible = len(group), int(group.eligible.fillna(False).sum())
                fast = int(group.fast_accepted.fillna(False).sum())
                slow = int(group.slow_accepted.fillna(False).sum())
                both = int((group.fast_accepted.fillna(False) & group.slow_accepted.fillna(False)).sum())
                union = fast + slow - both
                for dimension, values in (("geometry", GEOMETRY_VALUES), ("accepted_membership", ACCEPTED_MEMBERSHIP_VALUES)):
                    for value in values:
                        part = group.loc[group[dimension].eq(value)]
                        n = len(part)
                        row = dict(stage=2, product=product, interval_minutes=int(interval), direction=side,
                            period_kind=kind, period=str(period), dimension=dimension, category=value,
                            scheduled_slots=scheduled, eligible_slots=eligible, count=n,
                            eligible_count=int(part.eligible.fillna(False).sum()),
                            scheduled_share=n / scheduled if scheduled else np.nan,
                            eligible_rate_per_1000=1000 * int(part.eligible.fillna(False).sum()) / eligible if eligible else np.nan,
                            fast_accepted=fast, slow_accepted=slow, both_accepted=both, union_accepted=union,
                            denominator="common_usable_and_feature_valid_slots")
                        row["row_id"] = "S2-T07|" + "|".join(map(str, [product, interval, side, kind, period, dimension, value]))
                        rows.append(row)
    return pd.DataFrame(rows)


def episode_pair_metrics(pairs, outcomes):
    """Describe chosen first events only; retain interrupted/outside-scope nulls."""
    validate_outcomes(outcomes)
    lookup = {(r["event_id"], int(r["horizon"])): r for r in outcomes.to_dict("records")}
    rows = []
    for pair in pairs.to_dict("records"):
        if not pair.get("contains_development", False):
            continue
        interval = int(pair["interval_minutes"])
        hs = (15, 20, 50) if interval == 3 else (15, 12, 30)
        for h in hs:
            fast = lookup.get((pair.get("first_fast_event_id"), h))
            slow = lookup.get((pair.get("first_slow_event_id"), h))
            scoped = pair.get("pair_scope") == "both_development"
            status = "outside_pair_scope" if not scoped else "missing_saved_outcome" if fast is None or slow is None else "completed" if fast["status"] == slow["status"] == "completed" else "censored_counterpart"
            for unit in ("points", "atr"):
                row = {k: pair.get(k) for k in ("pair_id", "shared_episode_id", "product", "interval_minutes", "direction", "side",
                    "pair_relation", "pair_scope", "first_fast_event_id", "first_slow_event_id", "first_fast_timestamp", "first_slow_timestamp",
                    "slow_minus_fast_signal_minutes", "slow_minus_fast_reference_points", "end_reason", "status")}
                row.update(stage=2, horizon=h, horizon_minutes=h * interval, unit=unit, pair_outcome_status=status,
                           fast_outcome_status=fast["status"] if fast else None, slow_outcome_status=slow["status"] if slow else None,
                           fast_censor_reason=fast.get("censor_reason") if fast else None, slow_censor_reason=slow.get("censor_reason") if slow else None)
                if not scoped:
                    row["slow_minus_fast_signal_minutes"] = np.nan
                    row["slow_minus_fast_reference_points"] = np.nan
                row["direction_adjusted_slow_minus_fast_reference_points"] = pair.get("direction", np.nan) * row["slow_minus_fast_reference_points"]
                for metric in inherited.METRICS:
                    col = metric if unit == "points" else metric + "_atr"
                    evaluable = status == "completed" and pd.notna(fast.get(col)) and pd.notna(slow.get(col))
                    row["fast_" + metric] = float(fast[col]) if evaluable else np.nan
                    row["slow_" + metric] = float(slow[col]) if evaluable else np.nan
                    row["difference_" + metric] = float(fast[col] - slow[col]) if evaluable else np.nan
                if status == "completed" and any(pd.isna(row["difference_" + metric]) for metric in inherited.METRICS):
                    row["pair_outcome_status"] = "normalization_missing"
                row["row_id"] = "S2-pair|" + str(pair["pair_id"]) + "|" + str(h) + "|" + unit
                rows.append(row)
    return pd.DataFrame(rows)


def episode_summary(pairs, metrics):
    """Secondary retrospective episode counts and first-event differences."""
    p = pairs.loc[pairs.contains_development.fillna(False)].copy()
    rows = []
    for (product, interval), cell in p.groupby(["product", "interval_minutes"], sort=True):
        for side in inherited.SIDES:
            group = cell if side == "All" else cell.loc[cell.side.eq(side)]
            key = dict(stage=2, product=product, interval_minutes=int(interval), direction=side,
                       interpretation="retrospective_selected_first_events_not_primary_support")
            for dimension, values in (("pair_relation", PAIR_ORDER_VALUES), ("pair_scope", ("both_development", "warmup_counterpart", "outside_scope", "unpaired_development", "unpaired_warmup", "no_accepted"))):
                for category in values:
                    n = int(group[dimension].eq(category).sum())
                    row = key | dict(summary_kind=dimension, category=category, count=n, episodes=len(group),
                                     share=n / len(group) if len(group) else np.nan)
                    row["row_id"] = "S2-T09|" + "|".join(map(str, [product, interval, side, dimension, category]))
                    rows.append(row)
            scoped_fast = group.loc[group.first_fast_in_development.fillna(False)]
            scoped_pair = group.loc[group.pair_scope.eq("both_development")].copy()
            scoped_pair["direction_adjusted_slow_minus_fast_reference_points"] = scoped_pair.direction * scoped_pair.slow_minus_fast_reference_points
            for metric in ("slow_minus_fast_signal_minutes", "slow_minus_fast_reference_points", "direction_adjusted_slow_minus_fast_reference_points"):
                vals = scoped_pair[metric].dropna().astype(float)
                row = key | dict(summary_kind="pair_timing_reference", category=metric, scoped_pairs=len(scoped_pair),
                    evaluable=len(vals), mean_difference=float(vals.mean()) if len(vals) else np.nan,
                    median_difference=float(vals.median()) if len(vals) else np.nan,
                    p10_difference=float(vals.quantile(.1, interpolation="linear")) if len(vals) else np.nan,
                    p90_difference=float(vals.quantile(.9, interpolation="linear")) if len(vals) else np.nan,
                    difference_orientation="slow_minus_fast", sparse_warning=len(vals) < 100)
                row["row_id"] = "S2-T09|" + "|".join(map(str, [product, interval, side, "pair_timing_reference", metric]))
                rows.append(row)
            for descriptor in ("same_bar_slow_contact", "strictly_later_slow_contact", "strictly_later_slow_signal"):
                for label, mask in (("true", scoped_fast[descriptor].eq(True)), ("false", scoped_fast[descriptor].eq(False)), ("unresolved", scoped_fast[descriptor].isna())):
                    n = int(mask.sum())
                    row = key | dict(summary_kind=descriptor, category=label, count=n, episodes=len(group),
                                     descriptor_eligible=len(scoped_fast), share=n / len(scoped_fast) if len(scoped_fast) else np.nan)
                    row["row_id"] = "S2-T09|" + "|".join(map(str, [product, interval, side, descriptor, label]))
                    rows.append(row)
            selected = metrics.loc[metrics["product"].eq(product) & metrics.interval_minutes.eq(interval)] if not metrics.empty else metrics
            if side != "All" and not selected.empty:
                selected = selected.loc[selected.side.eq(side)]
            for (h, unit), part in selected.groupby(["horizon", "unit"], sort=True) if not selected.empty else []:
                good = part.loc[part.pair_outcome_status.eq("completed")]
                for metric in inherited.METRICS:
                    vals = good["difference_" + metric].dropna()
                    row = key | dict(summary_kind="pair_metric", category=metric, horizon=int(h), horizon_minutes=int(h) * int(interval),
                        unit=unit, selected_pairs=len(part), scoped_pairs=int(part.pair_scope.eq("both_development").sum()),
                        completed_pairs=int(part.pair_outcome_status.eq("completed").sum()), evaluable=len(vals),
                        censored_pairs=int(part.pair_outcome_status.eq("censored_counterpart").sum()),
                        outside_scope_pairs=int(part.pair_outcome_status.eq("outside_pair_scope").sum()),
                        normalization_missing_pairs=int(part.pair_outcome_status.eq("normalization_missing").sum()),
                        mean_difference=float(vals.mean()) if len(vals) else np.nan,
                        median_difference=float(vals.median()) if len(vals) else np.nan,
                        p10_difference=float(vals.quantile(.1, interpolation="linear")) if len(vals) else np.nan,
                        p90_difference=float(vals.quantile(.9, interpolation="linear")) if len(vals) else np.nan,
                        difference_orientation="fast_minus_slow", sparse_warning=len(vals) < 100)
                    row["row_id"] = "S2-T09|" + "|".join(map(str, [product, interval, side, "pair_metric", h, unit, metric]))
                    rows.append(row)
    return pd.DataFrame(rows)


def union_outcomes(union, outcomes):
    """Transfer already saved representative paths; never score a union anew."""
    validate_outcomes(outcomes)
    if union.empty:
        return outcomes.iloc[:0].copy()
    ids = union[["union_id", "representative_event_id", "accepted_membership", "fast_event_id", "slow_event_id"]].copy()
    if ids.union_id.duplicated().any() or ids.representative_event_id.duplicated().any():
        raise ValueError("union identity is not one accepted timestamp/direction")
    # Dual rows must carry exactly equal saved price-path evidence for each H.
    dual = ids.loc[ids.accepted_membership.eq("both")]
    science = [c for c in outcomes.columns if c in ("reference_price", "entry_atr", "contract", "direction", "timestamp", "available_at",
        "entry_at", "horizon", "horizon_minutes", "status", "censor_reason", "terminal_at", "elapsed_minutes", "crosses_closure", "same_session",
        "mfe", "mae", "terminal_delta", "mfe_atr", "mae_atr", "terminal_delta_atr", "favorable", "neutral", "adverse", "mfe_gt_mae", "mfe_mae_tie",
        "mfe_attainment_start", "mfe_attainment_end", "mae_attainment_start", "mae_attainment_end")]
    if not dual.empty:
        fast = dual[["union_id", "fast_event_id"]].merge(outcomes[["event_id"] + science],
            left_on="fast_event_id", right_on="event_id", how="left", validate="one_to_many").set_index(["union_id", "horizon"])
        slow = dual[["union_id", "slow_event_id"]].merge(outcomes[["event_id"] + science],
            left_on="slow_event_id", right_on="event_id", how="left", validate="one_to_many").set_index(["union_id", "horizon"])
        if set(fast.index) != set(slow.index) or fast.index.get_level_values("horizon").isna().any():
            raise ValueError("same-bar dual horizon roster differs")
        cols = [col for col in science if col != "horizon"]
        a, b = fast[cols].sort_index(), slow[cols].sort_index()
        if not (a.eq(b) | (a.isna() & b.isna())).fillna(False).all().all():
            raise ValueError("same-bar dual saved outcomes differ")
    for field in ids.columns:
        if field != "representative_event_id" and field in outcomes:
            outcomes = outcomes.drop(columns=field)
    result = outcomes.merge(ids, left_on="event_id", right_on="representative_event_id", how="inner", validate="many_to_one")
    result["event_id"], result["touch_mode"], result["stage"] = result.union_id, "union", 2
    return result


def verify_union_projection(expected, saved):
    """Compare root's saved union projection with the chosen saved source paths."""
    keys = ["event_id", "horizon"]
    if saved.duplicated(keys).any() or set(map(tuple, saved[keys].to_numpy())) != set(map(tuple, expected[keys].to_numpy())):
        raise ValueError("saved union projection identity/support differs")
    required = [c for c in expected.columns if c not in ("accepted_membership", "row_id")]
    if not set(required).issubset(saved.columns):
        raise ValueError("saved union projection scientific columns missing")
    if "source_event_id" not in saved or not saved.source_event_id.eq(saved.representative_event_id).all():
        raise ValueError("saved union projection representative source differs")
    cols = [c for c in expected.columns if c in saved.columns and c not in ("source_event_id", "row_id")]
    a = expected.set_index(keys)[[c for c in cols if c not in keys]].sort_index()
    b = saved.set_index(keys)[a.columns].sort_index()
    if not (a.eq(b) | (a.isna() & b.isna())).fillna(False).all().all():
        raise ValueError("saved union projection science differs")
    if not saved.touch_mode.eq("union").all():
        raise ValueError("saved union projection branch is not union")
    return saved


def union_summary(membership, union, outcomes, saved_union_outcomes=None):
    """Union counts/rates and overlapping descriptive paths, without positions."""
    m = _development(membership)
    u = _development(union)
    rows = []
    for (product, interval), cell in m.groupby(["product", "interval_minutes"], sort=True):
        for side in inherited.SIDES:
            group = cell if side == "All" else cell.loc[cell.side.eq(side)]
            union_group = u.loc[u["product"].eq(product) & u.interval_minutes.eq(interval)]
            if side != "All":
                union_group = union_group.loc[union_group.side.eq(side)]
            fast, slow = int(group.fast_accepted.sum()), int(group.slow_accepted.sum())
            both = int(group.accepted_membership.eq("both").sum())
            n, eligible = len(union_group), int(group.eligible.fillna(False).sum())
            if n != fast + slow - both:
                raise ValueError("union must satisfy fast + slow - both identity")
            row = dict(stage=2, product=product, interval_minutes=int(interval), direction=side, touch_mode="union",
                summary_kind="frequency", fast_accepted=fast, slow_accepted=slow, both_accepted=both, union_accepted=n,
                incremental_vs_slow=n - slow, incremental_fast_only=int(group.accepted_membership.eq("fast_only").sum()),
                fast_only=int(group.accepted_membership.eq("fast_only").sum()), slow_only=int(group.accepted_membership.eq("slow_only").sum()),
                scheduled_slots=len(group), eligible_slots=eligible,
                union_rate_per_1000=1000 * n / eligible if eligible else np.nan,
                fast_rate_per_1000=1000 * fast / eligible if eligible else np.nan,
                slow_rate_per_1000=1000 * slow / eligible if eligible else np.nan,
                incremental_rate_per_1000=1000 * (n - slow) / eligible if eligible else np.nan,
                denominator="common_usable_and_feature_valid_slots", interpretation="descriptive_union_not_position_policy")
            row["row_id"] = "S2-T10|" + "|".join(map(str, [product, interval, side, "frequency"]))
            rows.append(row)
    paths = union_outcomes(u, outcomes)
    if saved_union_outcomes is not None:
        paths = verify_union_projection(paths, saved_union_outcomes)
    score = inherited.summarize(paths, supports=("all", "uninterrupted", "same_session"))
    if not score.empty:
        score["stage"], score["touch_mode"], score["summary_kind"] = 2, "union", "outcome"
        score["interpretation"] = "deduplicated_saved_price_paths_not_position_policy"
        score["row_id"] = "S2-T10|union|" + score.row_id.astype(str)
        rows.extend(score.to_dict("records"))
    # Interval overlap is diagnosed on completed saved union H15 paths only.
    # Censored paths have no invented terminal timestamp.
    complete = paths.loc[paths.horizon.eq(15) & paths.status.eq("completed")]
    for (product, interval), cell in complete.groupby(["product", "interval_minutes"], sort=True):
        for side in inherited.SIDES:
            group = cell if side == "All" else cell.loc[cell.side.eq(side)]
            starts = pd.to_datetime(group.entry_at, utc=True).array.asi8
            ends = pd.to_datetime(group.terminal_at, utc=True).array.asi8
            # Half-open windows: end==next start does not overlap.
            boundaries = sorted([(int(t), 1) for t in starts] + [(int(t), -1) for t in ends])
            active = maximum = 0
            for _, change in boundaries:
                active += change
                maximum = max(maximum, active)
            ordered = group.sort_values("entry_at")
            prior_end, overlaps = -1, 0
            for item in ordered.itertuples():
                start, end = pd.Timestamp(item.entry_at).value, pd.Timestamp(item.terminal_at).value
                overlaps += int(start < prior_end)
                prior_end = max(prior_end, end)
            row = dict(stage=2, product=product, interval_minutes=int(interval), direction=side, touch_mode="union",
                summary_kind="overlap", horizon=15, horizon_minutes=15 * int(interval), completed_windows=len(group),
                windows_overlapping_prior=overlaps, max_concurrent_windows=maximum,
                overlap_support="completed_union_H15_only", interpretation="descriptive_observation_overlap_not_positions")
            row["row_id"] = "S2-T10|" + "|".join(map(str, [product, interval, side, "overlap", 15]))
            rows.append(row)
    return pd.DataFrame(rows)


def _read_records(records, role):
    return _concat([pd.read_parquet(verify_record(r)) for r in records if r["role"] == role])


def produce_tables(stage):
    """Write statistical tables once from hash-verified Stage 2 saved evidence."""
    stage = Path(stage)
    records = json.loads((stage / "events.manifest.json").read_text())["records"]
    outcomes, events = _read_records(records, "outcomes"), _read_records(records, "events")
    validate_outcomes(outcomes)
    tables = stage / "tables"
    tables.mkdir(exist_ok=True)
    names = [TABLES[f"S2-T{i:02d}"] for i in (1, 2, 3, 4, 5, 7, 8, 9, 10)] + [
        "S2-bootstrap.csv", "S2-duration-comparisons.csv", "S2-calendar-sufficient-statistics.csv", "S2-episode-pair-metrics.csv"]
    if any((tables / name).exists() for name in names):
        raise ValueError("saved Stage 2 statistical table overwrite refused")
    flows, supports, sessions, pairs, geometries, union_tables = [], [], set(), [], [], []
    for product in ("ES", "GC", "NQ"):
        for interval in (3, 5):
            cell_records = [r for r in records if r["product"] == product and r["interval_minutes"] == interval]
            tech = _read_records(cell_records, "technical")
            if tech.empty:
                continue
            cell_out = outcomes.loc[outcomes["product"].eq(product) & outcomes.interval_minutes.eq(interval)]
            cell_events = events.loc[events["product"].eq(product) & events.interval_minutes.eq(interval)]
            flows.append(signal_flow_branches(tech, cell_events, cell_out))
            roster, cell_sessions = support_roster(tech)
            supports.append(roster)
            sessions.update(cell_sessions)
            member = _read_records(cell_records, "membership")
            union = _read_records(cell_records, "union")
            saved_union = _read_records(cell_records, "union_outcomes")
            pair = _read_records(cell_records, "pairs")
            geometries.append(geometry_membership(member))
            if saved_union.empty and not union.empty:
                raise ValueError("saved union projection is required before statistical tables")
            union_tables.append(union_summary(member, union, cell_out, saved_union))
            pairs.append(pair)
            del tech, member, union
    uncertainty = branch_cohort_uncertainty(outcomes)
    score = summarize_branches(outcomes, supports=("all", "same_session", "uninterrupted"))
    ci = uncertainty.loc[uncertainty.kind.eq("cohort") & uncertainty.metric.eq("terminal_delta") &
        uncertainty.weighting.eq("event") & uncertainty.block_weeks.eq(4),
        ["product", "interval_minutes", "direction", "horizon", "unit", "support", "touch_mode", "ci_low", "ci_high"]]
    score = score.merge(ci.rename(columns={"ci_low": "ci95_low", "ci_high": "ci95_high"}),
        on=["product", "interval_minutes", "direction", "horizon", "unit", "support", "touch_mode"], how="left", validate="one_to_one")
    strata = coverage_columns(stability_branches(outcomes, sorted(sessions)), _concat(supports))
    pair_frames = _concat(pairs)
    pair_metrics = episode_pair_metrics(pair_frames, outcomes)
    sufficient = calendar_sufficient_statistics(outcomes)
    contrast = _concat([branch_contrasts(outcomes), paired_uncertainty(outcomes, sufficient=sufficient)])
    frames = {TABLES["S2-T01"]: _concat(flows), TABLES["S2-T02"]: score, TABLES["S2-T03"]: quantiles_branches(outcomes),
        TABLES["S2-T04"]: strata.loc[~strata.period_kind.isin(["week", "month"])],
        TABLES["S2-T05"]: strata.loc[strata.period_kind.isin(["week", "month"])], TABLES["S2-T07"]: _concat(geometries),
        TABLES["S2-T08"]: contrast, TABLES["S2-T09"]: episode_summary(pair_frames, pair_metrics), TABLES["S2-T10"]: _concat(union_tables),
        "S2-bootstrap.csv": uncertainty, "S2-duration-comparisons.csv": within_branch_comparisons(outcomes),
        "S2-calendar-sufficient-statistics.csv": sufficient, "S2-episode-pair-metrics.csv": pair_metrics}
    receipt = {"status": "saved", "stage": 2, "outcome_rows": len(outcomes), "accepted_events": len(events),
               "scope": "saved_2018_2020_evidence_only", "tables": []}
    for name, frame in frames.items():
        if "row_id" in frame and frame.row_id.duplicated().any():
            raise ValueError("duplicate saved statistic selector: " + name)
        path = tables / name
        frame.to_csv(path, index=False, float_format="%.17g")
        receipt["tables"].append(file_record(path, stage) | {"rows": len(frame), "columns": list(frame.columns)})
    return receipt
