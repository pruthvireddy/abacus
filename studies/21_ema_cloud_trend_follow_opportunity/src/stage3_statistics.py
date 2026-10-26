"""Phase-scoped development surfaces, frozen choices and paired evidence tables."""
from __future__ import annotations

import json
import math
from pathlib import Path
import numpy as np
import pandas as pd

from . import statistics as inherited
from .execution import file_record, write_json
from .stage3_masks import NY, boundary, calendar_weeks, scoring_periods
from .stage3_outcomes import score_period
from .stage3_selection import (CELL, assess_candidates, fixed_gate_id, fold_records,
                               select_nominees, validation_decisions)

METRICS = ("mfe", "mae", "terminal_delta")
KEYS = ("period_id", "product", "interval_minutes", "touch_mode", "gate_id", "direction", "horizon", "unit", "support")
TABLE_FILES = {
    "grid": "S3-T11_development_grid.csv", "folds": "S3-T12_development_fold_eligibility.csv",
    "nominees": "S3-T13_development_nominees.csv", "neighbors": "S3-T15_neighborhood_frontiers.csv",
}


def _id(row, extras=()):
    return "|".join(str(row.get(k, "")) for k in KEYS + tuple(extras))


def _key(payload, phase, h, direction="All", unit="atr", support="common_atr_valid"):
    gate = payload["gate"]
    return dict(stage=3, period_id=phase, product=payload["product"],
        interval_minutes=int(payload["interval_minutes"]), touch_mode=payload["touch_mode"],
        gate_id=gate["gate_id"], gate_family=gate["family"], gate_threshold=float(gate["threshold"]),
        direction=direction, horizon=int(h), horizon_minutes=int(h) * int(payload["interval_minutes"]),
        unit=unit, support=support)


def summaries(outcomes, payload, phase, horizons):
    """All common ATR scoring support; full absolute support is an extra view."""
    rows = []
    for h in horizons:
        for side in inherited.SIDES:
            all_rows = outcomes.loc[outcomes.horizon.eq(h)]
            if side != "All":
                all_rows = all_rows.loc[all_rows.side.eq(side)]
            supports = ("common_atr_valid", "full_absolute") if payload["gate"]["family"] == "absolute" else ("common_atr_valid",)
            for support in supports:
                selected = all_rows.loc[all_rows.score_eligible]
                if support == "common_atr_valid":
                    selected = selected.loc[selected.atr_support]
                for unit in ("points", "atr"):
                    row = _key(payload, phase, h, side, unit, support) | inherited._summary(selected, unit)
                    row.update(accepted_total=len(all_rows), start_embargo=int(all_rows.start_embargo.sum()),
                        endpoint_purge=int(all_rows.endpoint_purge.sum()),
                        atr_support_missing=int((all_rows.score_eligible & ~all_rows.atr_support).sum()),
                        scoring_accepted=len(selected))
                    row["row_id"] = _id(row)
                    rows.append(row)
    return pd.DataFrame(rows)


def quantiles(outcomes, payload, phase, horizons):
    rows = []
    for h in horizons:
        for side in inherited.SIDES:
            part = outcomes.loc[outcomes.horizon.eq(h) & outcomes.score_eligible & outcomes.atr_support & outcomes.status.eq("completed")]
            if side != "All":
                part = part.loc[part.side.eq(side)]
            for unit in ("points", "atr"):
                for metric in METRICS:
                    values = part[metric if unit == "points" else metric + "_atr"]
                    qs = values.quantile(inherited.PS, interpolation="linear") if len(values) else None
                    for q in inherited.PS:
                        row = _key(payload, phase, h, side, unit) | dict(metric=metric, quantile=q,
                            percentile=q * 100, value=float(qs.loc[q]) if qs is not None else np.nan,
                            evaluable=len(values), quantile_method="linear_rank_p_times_n_minus_1")
                        row["row_id"] = _id(row, ("metric", "percentile"))
                        rows.append(row)
    return pd.DataFrame(rows)


def stability(outcomes, payload, phase, cfg):
    """H15 All ATR calendar/clock panels, with exact causal roster coverage."""
    from .engine import _strata
    limits = cfg["periods"][phase]
    tech = _strata(payload["technical"].copy())
    stamps = pd.to_datetime(tech.timestamp, utc=True)
    tech = tech.loc[(stamps >= boundary(limits["start"])) & (stamps < boundary(limits["end"]))].copy()
    tech["eligible"] = tech.usable.fillna(False) & tech.feature_valid.fillna(False)
    atr = pd.to_numeric(tech.get("atr14", pd.Series(np.nan, index=tech.index)), errors="coerce").to_numpy(float)
    tech["atr_eligible"] = tech.eligible & np.isfinite(atr) & (atr > 0)
    cuts = np.quantile(atr[tech.atr_eligible], [.25, .5, .75], method="linear") if tech.atr_eligible.any() else np.full(3, np.nan)
    tech["volatility_bin"] = "undefined"
    if np.isfinite(cuts).all():
        tech.loc[tech.atr_eligible, "volatility_bin"] = ["Q" + str(v) for v in np.searchsorted(cuts, atr[tech.atr_eligible], side="left") + 1]
    primary = outcomes.loc[outcomes.horizon.eq(15)].copy()
    entry_atr = pd.to_numeric(primary.entry_atr, errors="coerce").to_numpy(float)
    valid_atr = np.isfinite(entry_atr) & (entry_atr > 0)
    primary["volatility_bin"] = "undefined"
    if np.isfinite(cuts).all():
        primary.loc[valid_atr, "volatility_bin"] = ["Q" + str(v) for v in np.searchsorted(cuts, entry_atr[valid_atr], side="left") + 1]
    local_start = boundary(limits["start"]).tz_convert(NY)
    local_end = (boundary(limits["end"]) - pd.Timedelta(nanoseconds=1)).tz_convert(NY)
    kinds = {"year": list(range(local_start.year, local_end.year + 1)),
             "week": calendar_weeks(limits["start"], limits["end"]),
             "month": tuple(pd.period_range(local_start.strftime("%Y-%m"), local_end.strftime("%Y-%m"), freq="M").astype(str)),
             "time_stratum": ("Asia", "Europe", "US", "Late"), "hour": tuple(range(24)),
             "session": tuple(sorted(tech.session.astype(str).unique())),
             "volatility_bin": ("Q1", "Q2", "Q3", "Q4", "undefined")}
    rows = []
    # Per-session evidence uses efficient direct aggregations; richer quantile
    # cells are already retained in the horizon and calendar panels.
    for kind, values in kinds.items():
        event_groups = {str(v): g for v, g in primary.groupby(kind, sort=False)}
        coverage = tech.groupby(kind).agg(scheduled_slots=("eligible", "size"),
            eligible_slots=("eligible", "sum"), eligible_atr_slots=("atr_eligible", "sum"))
        coverage.index = coverage.index.astype(str)
        for value in values:
            part = event_groups.get(str(value), primary.iloc[:0])
            scored = part.loc[part.score_eligible & part.atr_support]
            row = _key(payload, phase, 15) | dict(period_kind=kind, period=str(value))
            if kind == "session":
                good = scored.loc[scored.status.eq("completed")]
                row.update(accepted=len(scored), completed=len(good), censored=int(scored.status.eq("censored").sum()),
                    evaluable=len(good), contributing_sessions=good.session.nunique(), contributing_weeks=good.week.nunique(),
                    sparse_warning=len(good) < 100 or good.session.nunique() < 30)
                for metric in METRICS:
                    row["mean_" + metric] = float(good[metric + "_atr"].mean()) if len(good) else np.nan
                    row["session_mean_" + metric] = row["mean_" + metric]
            else:
                row.update(inherited._summary(scored, "atr"))
            cov = coverage.loc[str(value)] if str(value) in coverage.index else None
            scheduled, eligible, eligible_atr = (int(cov.scheduled_slots), int(cov.eligible_slots), int(cov.eligible_atr_slots)) if cov is not None else (0, 0, 0)
            row.update(scheduled_slots=scheduled, eligible_slots=eligible, eligible_atr_slots=eligible_atr,
                atr_q25=float(cuts[0]), atr_q50=float(cuts[1]), atr_q75=float(cuts[2]),
                volatility_cut_population="phase_common_eligible_mapped_atr",
                unknown_signal_slots=scheduled - eligible,
                coverage_complete=scheduled > 0 and scheduled == eligible,
                zero_event_qualification="events_observed" if len(scored) else "auditable_eligible_support" if eligible else "no_eligible_support")
            row["row_id"] = _id(row, ("period_kind", "period"))
            rows.append(row)
    return pd.DataFrame(rows)


def grid_comparisons(scorecard, cfg):
    primary = scorecard.loc[scorecard.direction.eq("All") & scorecard.unit.eq("atr") & scorecard.support.eq("common_atr_valid")].copy()
    rows = []
    for cell, group in primary.groupby(list(CELL), sort=True):
        fixed = fixed_gate_id(cell[0], cfg)
        base = group.loc[group.gate_id.eq(fixed)].set_index("horizon")
        for row in group.to_dict("records"):
            if row["horizon"] not in base.index:
                raise ValueError("fixed baseline required at every development horizon")
            b = base.loc[row["horizon"]]
            row["fixed_gate_id"] = fixed
            row["baseline_evaluable"] = int(b.evaluable)
            row["retention"] = row["evaluable"] / b.evaluable if b.evaluable else np.nan
            for metric in METRICS:
                row["baseline_mean_" + metric] = b["mean_" + metric]
                row["difference_mean_" + metric] = row["mean_" + metric] - b["mean_" + metric]
            rows.append(row)
    return pd.DataFrame(rows)


def neighborhoods(grid):
    rows = []
    universes = {key: group for key, group in grid.groupby(list(CELL) + ["horizon"], sort=True)}
    for family_key, group in grid.groupby(list(CELL) + ["horizon", "gate_family"], sort=True):
        ordered = group.sort_values(["gate_threshold", "gate_id"]).reset_index(drop=True)
        for i, item in ordered.iterrows():
            row = item.to_dict()
            row["previous_gate_id"] = ordered.iloc[i - 1].gate_id if i else None
            row["next_gate_id"] = ordered.iloc[i + 1].gate_id if i + 1 < len(ordered) else None
            neighbors = ordered.iloc[max(0, i - 1):min(len(ordered), i + 2)]
            row["neighbor_count"] = len(neighbors) - 1
            row["neighbor_min_improvement"] = float(neighbors.difference_mean_terminal_delta.min()) if neighbors.difference_mean_terminal_delta.notna().all() else np.nan
            row["stable_positive_neighborhood"] = bool(len(neighbors) >= 2 and neighbors.difference_mean_terminal_delta.notna().all() and (neighbors.difference_mean_terminal_delta > 0).all())
            defined = np.isfinite([row["retention"], row["mean_terminal_delta"], row["mean_mae"]]).all()
            universe = universes[family_key[:4]]
            other = universe.loc[np.isfinite(universe.retention) & np.isfinite(universe.mean_terminal_delta) & np.isfinite(universe.mean_mae)]
            dominates = ((other.retention >= row["retention"]) & (other.mean_terminal_delta >= row["mean_terminal_delta"]) & (other.mean_mae <= row["mean_mae"]) &
                         ((other.retention > row["retention"]) | (other.mean_terminal_delta > row["mean_terminal_delta"]) | (other.mean_mae < row["mean_mae"])))
            row["pareto_frontier"] = not bool(dominates.any()) if defined else None
            row["frontier_scope"] = "all_gate_families_same_cell_horizon"
            rows.append(row)
    return pd.DataFrame(rows)


def calendar_weights(start, end, *, resamples=10000, seed=20261010, block_weeks=4):
    weeks = calendar_weeks(start, end)
    if not weeks or resamples < 1 or block_weeks < 1:
        raise ValueError("nonempty calendar and positive bootstrap parameters required")
    n = len(weeks)
    starts = np.random.default_rng(seed).integers(0, n, size=(resamples, math.ceil(n / block_weeks)))
    sampled = ((starts[:, :, None] + np.arange(block_weeks)) % n).reshape(resamples, -1)[:, :n]
    weights = np.zeros((resamples, n), dtype=float)
    np.add.at(weights, (np.repeat(np.arange(resamples), n), sampled.ravel()), 1.)
    return weeks, weights


def weekly_sufficient(good, weeks, metric, unit, weighting):
    col = metric if unit == "points" else metric + "_atr"
    vals = good.loc[:, ["session", "week", col]].copy()
    vals[col] = vals[col].astype(float)
    if weighting == "session":
        vals = vals.groupby("session", as_index=False)[col].mean()
        dates = pd.to_datetime(vals.session)
        vals["week"] = (dates - pd.to_timedelta(dates.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    elif weighting != "event":
        raise ValueError("unknown weighting")
    if not set(vals.week) <= set(weeks):
        raise ValueError("event/session support falls outside scored-period week roster")
    weekly = vals.groupby("week")[col].agg(["sum", "count"]).reindex(weeks, fill_value=0.)
    return weekly, float(vals[col].mean()) if len(vals) else np.nan


def period_effects(outcomes, choices, cfg, phase):
    """Own accepted populations, shared sampled blocks, no event intersection."""
    limits = cfg["periods"][phase]
    boot = cfg["bootstrap"]
    block_weights = {block: calendar_weights(limits["start"], limits["end"], resamples=boot["resamples"],
        seed=boot["seed"], block_weeks=block) for block in (boot["block_weeks"], *boot["sensitivity_block_weeks"])}
    rows, sufficient = [], []
    for choice in choices.to_dict("records"):
        cell = dict((k, choice[k]) for k in CELL)
        source = outcomes
        for k, v in cell.items():
            source = source.loc[source[k].eq(v)]
        selected, fixed = choice["selected_gate_id"], choice["fixed_gate_id"]
        hs = cfg["horizons"]
        for h in hs:
            for side in inherited.SIDES:
                part = source.loc[source.horizon.eq(h) & source.score_eligible & source.atr_support]
                if side != "All":
                    part = part.loc[part.side.eq(side)]
                for unit in ("points", "atr"):
                    _, a = inherited._evaluable(part.loc[part.gate_id.eq(selected)], unit)
                    _, b = inherited._evaluable(part.loc[part.gate_id.eq(fixed)], unit)
                    for metric in METRICS:
                        for weighting in ("event", "session"):
                            av = a[metric] if weighting == "event" else a.groupby("session")[metric].mean()
                            bv = b[metric] if weighting == "event" else b.groupby("session")[metric].mean()
                            am, bm = (float(av.mean()) if len(av) else np.nan), (float(bv.mean()) if len(bv) else np.nan)
                            row = dict(stage=3, period_id=phase, **cell, gate_id=selected,
                                selected_gate_id=selected, fixed_gate_id=fixed, direction=side,
                                horizon=int(h), horizon_minutes=int(h) * int(cell["interval_minutes"]),
                                unit=unit, support="common_atr_valid", metric=metric, weighting=weighting,
                                selected_evaluable=len(a), fixed_evaluable=len(b),
                                selected_sessions=a.session.nunique(), fixed_sessions=b.session.nunique(),
                                selected_weeks=a.week.nunique(), fixed_weeks=b.week.nunique(),
                                selected_estimate=am, fixed_estimate=bm, estimate=am - bm,
                                identity_fallback=selected == fixed,
                                sparse_warning=len(a) < 100 or len(b) < 100 or a.session.nunique() < 30 or b.session.nunique() < 30,
                                block_weeks=0, interval_kind="descriptive", ci_low=np.nan, ci_high=np.nan,
                                ci_level=np.nan, defined_draws=0, undefined_draws=0)
                            row["row_id"] = _id(row, ("metric", "weighting", "block_weeks", "interval_kind"))
                            rows.append(row)
                            if h != 15 or side != "All" or unit != "atr" or metric != "terminal_delta":
                                continue
                            for block in (boot["block_weeks"], *boot["sensitivity_block_weeks"]):
                                weeks, weights = block_weights[block]
                                wa, _ = weekly_sufficient(a, weeks, metric, unit, weighting)
                                wb, _ = weekly_sufficient(b, weeks, metric, unit, weighting)
                                for label, weekly in (("selected", wa), ("fixed", wb)):
                                    if block == boot["block_weeks"]:
                                        for week, sums in weekly.iterrows():
                                            sufficient.append(dict(stage=3, period_id=phase, **cell, selected_gate_id=selected,
                                                fixed_gate_id=fixed, role=label, horizon=h, direction=side, unit=unit,
                                                metric=metric, weighting=weighting, week=week, sum=float(sums["sum"]), count=int(sums["count"])))
                                da = weights @ wa["count"].to_numpy(float)
                                db = weights @ wb["count"].to_numpy(float)
                                va = np.divide(weights @ wa["sum"].to_numpy(float), da, out=np.full(len(weights), np.nan), where=da > 0)
                                vb = np.divide(weights @ wb["sum"].to_numpy(float), db, out=np.full(len(weights), np.nan), where=db > 0)
                                draws = va - vb
                                finite = draws[np.isfinite(draws)]
                                intervals = [("pointwise95", .025, .975)]
                                if phase == "final" and weighting == "event":
                                    intervals.append(("bonferroni12", .05 / 24, 1 - .05 / 24))
                                for label, lo, hi in intervals:
                                    low, high = np.quantile(finite, [lo, hi], method="linear") if len(finite) else (np.nan, np.nan)
                                    ci = row | dict(block_weeks=block, interval_kind=label, ci_level=hi - lo,
                                        quantile_low=lo, quantile_high=hi, ci_low=float(low), ci_high=float(high),
                                        resamples=boot["resamples"], seed=boot["seed"], week_count=len(weeks),
                                        first_week=weeks[0], last_week=weeks[-1], defined_draws=len(finite),
                                        undefined_draws=len(draws) - len(finite), primary=phase == "final" and weighting == "event" and block == boot["block_weeks"])
                                    ci["row_id"] = _id(ci, ("metric", "weighting", "block_weeks", "interval_kind"))
                                    rows.append(ci)
    weekly_table = pd.DataFrame(sufficient)
    if len(weekly_table):
        weekly_table["row_id"] = [_id(row, ("selected_gate_id", "fixed_gate_id", "role", "metric", "weighting", "week"))
                                  for row in weekly_table.to_dict("records")]
    return pd.DataFrame(rows), weekly_table


def _write_csv(stage, name, table):
    path = Path(stage) / "tables" / name
    if path.exists():
        raise ValueError("Stage 3 table overwrite refused: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if "row_id" in table and table.row_id.duplicated().any():
        raise ValueError("duplicate saved table row_id: " + name)
    table.to_csv(path, index=False, float_format="%.17g", na_rep="")
    return file_record(path, Path(stage)) | dict(rows=len(table), columns=list(table.columns), role="table")


def _phase_stream(stage, cfg, payload, phase, authorization):
    frames, audits = [], []
    for period in scoring_periods(cfg, phase):
        out, audit = score_period(payload["bars"], payload["events"], cfg["horizons"], period, authorization,
            product=payload["product"], interval_minutes=payload["interval_minutes"], touch_mode=payload["touch_mode"], gate=payload["gate"])
        frames.append(out)
        for h in cfg["horizons"]:
            part = out.loc[out.horizon.eq(h)]
            row = _key(payload, phase, h) | audit | dict(accepted=len(part), start_embargo=int(part.start_embargo.sum()),
                endpoint_purge=int(part.endpoint_purge.sum()), atr_support_missing=int((part.score_eligible & ~part.atr_support).sum()),
                excluded_start_embargo=int(part.mask_reason.eq("start_embargo").sum()),
                excluded_endpoint_purge=int(part.mask_reason.eq("period_endpoint_purge").sum()),
                scoring_accepted=int(part.score_eligible.sum()), completed=int(part.status.eq("completed").sum()),
                censored=int(part.status.eq("censored").sum()), excluded=int(part.status.eq("excluded").sum()))
            row["row_id"] = _id(row, ("fold_id",))
            audits.append(row)
    nonempty = [frame for frame in frames if len(frame)]
    outcomes = pd.concat(nonempty, ignore_index=True) if nonempty else frames[0].copy()
    gate = payload["gate"]
    path = Path(stage) / "ledgers/stage3" / phase / f"{payload['product']}_{payload['interval_minutes']}_{payload['touch_mode']}_{gate['gate_id']}_outcomes.parquet"
    if path.exists():
        raise ValueError("Stage 3 outcome overwrite refused")
    path.parent.mkdir(parents=True, exist_ok=True)
    outcomes.to_parquet(path, index=False, compression="zstd")
    record = file_record(path, Path(stage)) | dict(role="outcomes", period_id=phase, product=payload["product"],
        interval_minutes=int(payload["interval_minutes"]), touch_mode=payload["touch_mode"], gate_id=gate["gate_id"],
        rows=len(outcomes), columns=list(outcomes.columns), schema={c: str(t) for c, t in outcomes.dtypes.items()})
    return outcomes, pd.DataFrame(audits), record


def _flow(payload, phase, cfg):
    tech = payload["technical"]
    times = pd.to_datetime(tech.timestamp, utc=True)
    limits = cfg["periods"][phase]
    tech = tech.loc[(times >= boundary(limits["start"])) & (times < boundary(limits["end"]))]
    rows = []
    for side in inherited.SIDES:
        part = tech if side == "All" else tech.loc[tech.side.eq(side)]
        counts = dict(scheduled_slots=len(part), usable_slots=int(part.usable.fillna(False).sum()),
            feature_valid_slots=int(part.feature_valid.fillna(False).sum()),
            eligible_slots=int((part.usable.fillna(False) & part.feature_valid.fillna(False)).sum()),
            accepted=int(part.accepted.sum()), technical_candidates=int(part.technical_candidate.sum()),
            setup_candidates=int(part.setup_candidate.sum()))
        counts.update({"suppressed:" + str(r): int(n) for r, n in part.suppression_reason.value_counts().items()})
        for reason, count in counts.items():
            row = _key(payload, phase, 0, side) | dict(flow_kind="signal", reason=reason, count=count)
            row["row_id"] = _id(row, ("flow_kind", "reason"))
            rows.append(row)
    return pd.DataFrame(rows)


def _manifest(stage, phase, records, tables, choices):
    path = Path(stage) / f"stage3-{phase}.manifest.json"
    if path.exists():
        raise ValueError("phase evidence manifest overwrite refused")
    manifest = dict(schema_version="study21.stage3-phase-evidence/v1", status="produced_not_independently_verified",
        period_id=phase, records=records, tables=tables,
        choices=[{k: None if pd.isna(v) else v for k, v in row.items()} for row in choices.to_dict("records")])
    write_json(path, manifest)
    return dict(manifest=file_record(path, Path(stage)), records=records, tables=tables, choices=choices)


def produce_development(stage, cfg, iterator, authorization):
    if authorization is None or authorization.period != "development":
        raise ValueError("explicit development authorization required")
    scorecards, qs, stabilities, folds, audits, flows, records = [], [], [], [], [], [], []
    observed = set()
    fold_ids = [x["id"] for x in cfg["development_folds"]]
    for payload in iterator:
        key = (payload["product"], int(payload["interval_minutes"]), payload["touch_mode"], payload["gate"]["gate_id"])
        if key in observed:
            raise ValueError("duplicate gateway stream")
        observed.add(key)
        out, audit, record = _phase_stream(stage, cfg, payload, "development", authorization)
        records.append(record)
        scorecards.append(summaries(out, payload, "development", cfg["horizons"]))
        qs.append(quantiles(out, payload, "development", cfg["horizons"]))
        stabilities.append(stability(out, payload, "development", cfg))
        folds.append(fold_records(out, payload["gate"], payload["product"], payload["interval_minutes"], payload["touch_mode"], fold_ids))
        audits.append(audit)
        flows.append(_flow(payload, "development", cfg))
    if observed != set(authorization.gates):
        raise ValueError("development gateway inventory differs from authorized complete grid")
    scorecard, fold_table = pd.concat(scorecards, ignore_index=True), pd.concat(folds, ignore_index=True)
    grid = grid_comparisons(scorecard, cfg)
    assessments = assess_candidates(fold_table, cfg, phase="development")
    nominees = select_nominees(assessments, cfg)
    # The fold table and pooled assessment are separate row types, making all
    # original support estimates and every failed guard directly inspectable.
    fold_table["record_kind"], assessments["record_kind"] = "fold_support", "candidate_assessment"
    fold_table["phase"], fold_table["period_id"] = "development", "development"
    assessments["period_id"], assessments["fold_id"] = "development", "assessment"
    t12 = pd.concat([fold_table, assessments], ignore_index=True)
    t12["row_id"] = [_id(r, ("fold_id", "record_kind")) for r in t12.to_dict("records")]
    nominees["period_id"] = "development"
    nominees["row_id"] = [_id(r, ("phase",)) for r in nominees.to_dict("records")]
    tables = [
        _write_csv(stage, "S3-T01_development_flow.csv", pd.concat(flows, ignore_index=True)),
        _write_csv(stage, "S3-T02_development_horizon_scorecard.csv", scorecard),
        _write_csv(stage, "S3-T03_development_quantiles.csv", pd.concat(qs, ignore_index=True)),
        _write_csv(stage, "S3-T04_development_stability.csv", pd.concat(stabilities, ignore_index=True)),
        _write_csv(stage, TABLE_FILES["grid"], grid), _write_csv(stage, TABLE_FILES["folds"], t12),
        _write_csv(stage, TABLE_FILES["nominees"], nominees),
        _write_csv(stage, TABLE_FILES["neighbors"], neighborhoods(grid)),
        _write_csv(stage, "S3-T16_development_masks.csv", pd.concat(audits, ignore_index=True)),
    ]
    return _manifest(stage, "development", records, tables, nominees)


def evaluate_period(stage, cfg, choices, period, authorization, iterator):
    if period not in ("validation", "final", "recent") or authorization is None or authorization.period != period:
        raise ValueError("explicit reserved-period authorization required")
    if isinstance(choices, (str, Path)):
        choices = pd.read_csv(choices)
    if choices.duplicated(list(CELL)).any():
        raise ValueError("duplicate frozen choice cell")
    expected = set()
    for choice in choices.to_dict("records"):
        cell = tuple(choice[k] for k in CELL)
        chosen = choice["nominee_gate_id"] if period == "validation" else choice["selected_gate_id"]
        if period != "validation" and choice.get("final_gate_id", chosen) != chosen:
            raise ValueError("final frozen choice columns disagree")
        expected.update(((*cell, chosen), (*cell, choice["fixed_gate_id"])))
    if expected != set(authorization.gates):
        raise ValueError("frozen choice inventory differs from phase authorization")
    frames, folds, scorecards, qs, stabilities, audits, flows, records = [], [], [], [], [], [], [], []
    observed = set()
    for payload in iterator:
        key = (payload["product"], int(payload["interval_minutes"]), payload["touch_mode"], payload["gate"]["gate_id"])
        if key in observed:
            raise ValueError("duplicate reserved gateway stream")
        observed.add(key)
        out, audit, record = _phase_stream(stage, cfg, payload, period, authorization)
        frames.append(out)
        records.append(record)
        scorecards.append(summaries(out, payload, period, cfg["horizons"]))
        qs.append(quantiles(out, payload, period, cfg["horizons"]))
        stabilities.append(stability(out, payload, period, cfg))
        audits.append(audit)
        flows.append(_flow(payload, period, cfg))
        if period == "validation":
            folds.append(fold_records(out, payload["gate"], payload["product"], payload["interval_minutes"], payload["touch_mode"], [x["id"] for x in cfg["validation_folds"]]))
    if observed != set(authorization.gates):
        raise ValueError("reserved stream inventory differs from frozen authorized choices")
    outcomes = pd.concat(frames, ignore_index=True)
    tables = []
    evaluation_choices = choices.copy()
    if period == "validation":
        fold_table = pd.concat(folds, ignore_index=True)
        assessments = assess_candidates(fold_table, cfg, phase="validation")
        decisions = validation_decisions(assessments, choices, cfg)
        # Validation effects describe the frozen nominee versus fixed, even if
        # it fails. The decision chooses the final stream only after assessment.
        evaluation_choices["selected_gate_id"] = evaluation_choices.nominee_gate_id
        decisions["period_id"] = "validation"
        decisions["row_id"] = [_id(r, ("phase",)) for r in decisions.to_dict("records")]
        fold_table["record_kind"], assessments["record_kind"] = "fold_support", "candidate_assessment"
        fold_table["period_id"], assessments["period_id"] = period, period
        assessments["fold_id"] = "assessment"
        t12 = pd.concat([fold_table, assessments], ignore_index=True)
        t12["row_id"] = [_id(r, ("fold_id", "record_kind")) for r in t12.to_dict("records")]
        tables.extend([_write_csv(stage, "S3-T12_validation_fold_eligibility.csv", t12),
                       _write_csv(stage, "S3-T13_validation_decisions.csv", decisions)])
    else:
        decisions = choices.copy()
    effects, sufficient = period_effects(outcomes, evaluation_choices, cfg, period)
    tables.extend([
        _write_csv(stage, f"S3-T01_{period}_flow.csv", pd.concat(flows, ignore_index=True)),
        _write_csv(stage, f"S3-T02_{period}_horizon_scorecard.csv", pd.concat(scorecards, ignore_index=True)),
        _write_csv(stage, f"S3-T03_{period}_quantiles.csv", pd.concat(qs, ignore_index=True)),
        _write_csv(stage, f"S3-T04_{period}_stability.csv", pd.concat(stabilities, ignore_index=True)),
        _write_csv(stage, f"S3-T14_{period}_effects.csv", effects),
        _write_csv(stage, f"S3-weekly-{period}.csv", sufficient),
        _write_csv(stage, f"S3-T16_{period}_masks.csv", pd.concat(audits, ignore_index=True)),
    ])
    return _manifest(stage, period, records, tables, decisions)
