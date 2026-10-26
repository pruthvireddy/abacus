"""Stage 2 branch contrasts and paired calendar uncertainty.

Branches retain separate event populations. Matching is never a condition of a
primary contrast. A shared sampled week carries both populations, including
zero-event weeks; a missing branch denominator leaves that draw undefined.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import statistics as inherited
from .stage2_contract import PRIMARY_ALPHA, PRIMARY_FAMILY_ID, PRIMARY_FAMILY_SIZE

METRICS = inherited.METRICS + ("favorable", "mfe_gt_mae")
SUPPORTS = ("all", "uninterrupted", "same_session")
CI_SUPPORTS = ("all", "uninterrupted")
SIDES = inherited.SIDES
PRODUCTS = ("ES", "GC", "NQ")


def validate_outcomes(outcomes):
    """Reject scope leaks before descriptive or uncertainty calculations."""
    if not outcomes.empty:
        times = pd.to_datetime(outcomes.timestamp, utc=True).dt.tz_convert("America/New_York")
        if not times.dt.year.between(2018, 2020).all():
            raise ValueError("Stage 2 statistics permit only 2018–2020 outcomes")
        if not outcomes.touch_mode.isin(["fast", "slow"]).all():
            raise ValueError("outcomes must identify the independent fast/slow branch")
        if outcomes.duplicated(["event_id", "horizon"]).any():
            raise ValueError("duplicate branch outcome identity")
        terminal = pd.to_datetime(outcomes.terminal_at, utc=True)
        if (terminal > pd.Timestamp("2021-01-01", tz="America/New_York").tz_convert("UTC")).any():
            raise ValueError("reserved terminal observations are forbidden")
    return outcomes


def row_id(row, prefix="S2-T08"):
    keys = ("product", "interval_minutes", "direction", "touch_mode", "support", "horizon",
            "unit", "metric", "weighting", "comparison", "block_weeks", "interval_type")
    return prefix + "|" + "|".join(str(row.get(k, "")) for k in keys)


def _group(outcomes, branch, product, interval, side, h, support):
    group = outcomes.loc[outcomes.touch_mode.eq(branch) & outcomes["product"].eq(product) &
                         outcomes.interval_minutes.eq(interval) & outcomes.horizon.eq(h)]
    if side != "All":
        group = group.loc[group.side.eq(side)]
    if support == "uninterrupted":
        group = group.loc[group.crosses_closure.eq(False)]
    elif support == "same_session":
        group = group.loc[group.same_session.eq(True)]
    return group


def _key(product, interval, side, h, unit, support, metric, weighting):
    return dict(stage=2, product=product, interval_minutes=int(interval), direction=side,
                touch_mode="fast_minus_slow", gate_id="fixed", split="development", support=support,
                horizon=int(h), horizon_minutes=int(h) * int(interval), unit=unit, metric=metric,
                metric_unit=unit if metric in inherited.METRICS else "share", weighting=weighting,
                comparison="fast_minus_slow")


def _values(group, unit, metric, weighting):
    _, good = inherited._evaluable(group, unit)
    vals = good.loc[:, ["week", "session", metric]].copy()
    vals[metric] = vals[metric].astype(float)
    if weighting == "session":
        # Average complete contributing sessions before assigning their week.
        vals = vals.groupby("session", as_index=False)[metric].mean()
        dates = pd.to_datetime(vals.session)
        vals["week"] = (dates - pd.to_timedelta(dates.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    return vals, good


def _counts(group, unit, prefix):
    complete, good = inherited._evaluable(group, unit)
    return {prefix + "_accepted": len(group), prefix + "_completed": len(complete),
            prefix + "_censored": len(group) - len(complete), prefix + "_evaluable": len(good),
            prefix + "_sessions": good.session.nunique(), prefix + "_weeks": good.week.nunique()}


def _specs(outcomes, ci=False):
    """Fixed H15 and equal-active views for CIs; all saved Hs descriptive."""
    if ci:
        return [(p, interval, h) for p in PRODUCTS for interval in (3, 5)
                for h in ((15, 20, 50) if interval == 3 else (15, 12, 30))]
    return sorted(set((r.product, int(r.interval_minutes), int(r.horizon))
                      for r in outcomes[["product", "interval_minutes", "horizon"]].itertuples(index=False)))


def _primary(key):
    return (key["direction"] == "All" and key["horizon"] == 15 and key["unit"] == "points"
            and key["support"] == "all" and key["weighting"] == "event"
            and key["metric"] == "terminal_delta")


def branch_contrasts(outcomes, supports=SUPPORTS):
    """Long point contrasts from separate branch means, without timestamp matching."""
    validate_outcomes(outcomes)
    rows = []
    for product, interval, h in _specs(outcomes):
        for side in SIDES:
            for support in supports:
                groups = {b: _group(outcomes, b, product, interval, side, h, support) for b in ("fast", "slow")}
                for unit in ("points", "atr"):
                    counts = _counts(groups["fast"], unit, "fast") | _counts(groups["slow"], unit, "slow")
                    for metric in METRICS:
                        for weighting in ("event", "session"):
                            key = _key(product, interval, side, h, unit, support, metric, weighting)
                            estimates = {b: float(_values(g, unit, metric, weighting)[0][metric].mean())
                                         for b, g in groups.items()}
                            row = key | counts | dict(fast_estimate=estimates["fast"], slow_estimate=estimates["slow"],
                                estimate=estimates["fast"] - estimates["slow"], block_weeks=0,
                                interval_type="descriptive", coverage=np.nan, family_id=PRIMARY_FAMILY_ID if _primary(key) else "",
                                analysis_role="primary" if _primary(key) else "secondary", ci_low=np.nan, ci_high=np.nan,
                                defined_draws=0, undefined_draws=0,
                                support_qualification="accepted_before_path_exclusion" if support == "all" else "conditional_completed_path_support",
                                sparse_warning=any(counts[b + "_evaluable"] < 100 or counts[b + "_sessions"] < 30 for b in groups))
                            row["row_id"] = row_id(row)
                            rows.append(row)
    return pd.DataFrame(rows)


def calendar_sufficient_statistics(outcomes, supports=CI_SUPPORTS):
    """Complete 157-week branch sums/counts used by paired branch contrasts."""
    validate_outcomes(outcomes)
    weeks, _ = inherited.calendar_weights(resamples=1)
    parts = []
    for product, interval, h in _specs(outcomes, ci=True):
        for side in SIDES:
            for support in supports:
                for branch in ("fast", "slow"):
                    group = _group(outcomes, branch, product, interval, side, h, support)
                    for unit in ("points", "atr"):
                        _, good = inherited._evaluable(group, unit)
                        for weighting in ("event", "session"):
                            vals = good.loc[:, ["week", "session"] + list(METRICS)].copy()
                            vals[list(METRICS)] = vals[list(METRICS)].astype(float)
                            if weighting == "session":
                                vals = vals.groupby("session", as_index=False)[list(METRICS)].mean()
                                dates = pd.to_datetime(vals.session)
                                vals["week"] = (dates - pd.to_timedelta(dates.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
                            if not vals.week.isin(weeks).all():
                                raise ValueError("metric observations fall outside the frozen calendar-week roster")
                            weekly = vals.groupby("week")[list(METRICS)].agg(["sum", "count"]).reindex(weeks, fill_value=0)
                            key = _key(product, interval, side, h, unit, support, "", weighting)
                            key["touch_mode"] = branch
                            part = pd.DataFrame({"week": np.tile(weeks, len(METRICS)),
                                "metric": np.repeat(METRICS, len(weeks)),
                                "sum": np.concatenate([weekly[(metric, "sum")].to_numpy(float) for metric in METRICS]),
                                "count": np.concatenate([weekly[(metric, "count")].to_numpy(int) for metric in METRICS])})
                            for field, value in key.items():
                                if field not in ("metric", "metric_unit"):
                                    part[field] = value
                            part["metric_unit"] = np.where(part.metric.isin(inherited.METRICS), unit, "share")
                            means = vals[list(METRICS)].mean()
                            part["cohort_estimate"] = part.metric.map(means)
                            part["week_assignment"] = "signal_open_NY_week" if weighting == "event" else "whole_trading_session_date_week"
                            prefixes = {metric: row_id(key | {"metric": metric}, "S2-weekly") for metric in METRICS}
                            part["row_id"] = part.metric.map(prefixes) + "|" + part.week
                            parts.append(part)
    return pd.concat(parts, ignore_index=True)


def paired_uncertainty(outcomes, resamples=10000, seed=20261010, block_lengths=(4, 1, 8),
                       supports=CI_SUPPORTS, sufficient=None):
    """Paired branch CIs with pointwise and the frozen six-contrast correction."""
    validate_outcomes(outcomes)
    sufficient = calendar_sufficient_statistics(outcomes, supports) if sufficient is None else sufficient
    group_keys = ["product", "interval_minutes", "direction", "horizon", "unit", "support", "metric", "weighting"]
    lookup = {}
    weeks = list(pd.date_range("2018-01-01", "2020-12-28", freq="W-MON").strftime("%Y-%m-%d"))
    for keys, group in sufficient.groupby(group_keys + ["touch_mode"], sort=True):
        calendar = group.set_index("week").reindex(weeks)
        if calendar[["sum", "count"]].isna().any().any() or len(calendar) != 157:
            raise ValueError("sufficient statistics must retain the full frozen week roster")
        sums, ns = calendar["sum"].to_numpy(float), calendar["count"].to_numpy(float)
        estimate = float(calendar.cohort_estimate.iloc[0])
        lookup[keys] = sums, ns, estimate
    rows = []
    for block in block_lengths:
        weeks, weights = inherited.calendar_weights(resamples, seed, block)
        for product, interval, h in _specs(outcomes, ci=True):
            for side in SIDES:
                for support in supports:
                    groups = {b: _group(outcomes, b, product, interval, side, h, support) for b in ("fast", "slow")}
                    for unit in ("points", "atr"):
                        counts = _counts(groups["fast"], unit, "fast") | _counts(groups["slow"], unit, "slow")
                        for metric in METRICS:
                            for weighting in ("event", "session"):
                                key = _key(product, interval, side, h, unit, support, metric, weighting)
                                draws, estimates = {}, {}
                                for branch in ("fast", "slow"):
                                    sums, ns, estimate = lookup[(product, interval, side, h, unit, support, metric, weighting, branch)]
                                    denominator = weights @ ns
                                    draws[branch] = np.divide(weights @ sums, denominator, out=np.full(resamples, np.nan), where=denominator > 0)
                                    estimates[branch] = estimate
                                difference = draws["fast"] - draws["slow"]
                                finite = difference[np.isfinite(difference)]
                                levels = [("pointwise95", .95, [.025, .975])]
                                if _primary(key):
                                    # Exact rational alpha/(2*6), with no rounded confidence-level input.
                                    tail = PRIMARY_ALPHA / (2 * PRIMARY_FAMILY_SIZE)
                                    levels.append(("bonferroni", 1 - PRIMARY_ALPHA / PRIMARY_FAMILY_SIZE, [tail, 1 - tail]))
                                for interval_type, coverage, tails in levels:
                                    low, high = np.quantile(finite, tails, method="linear") if len(finite) else (np.nan, np.nan)
                                    row = key | counts | dict(block_weeks=block, resamples=resamples, seed=seed,
                                        interval_type=interval_type, coverage=coverage,
                                        family_id=PRIMARY_FAMILY_ID if _primary(key) else "", family_size=PRIMARY_FAMILY_SIZE if _primary(key) else np.nan,
                                        analysis_role=("primary" if _primary(key) else "secondary") if block == 4 else "sensitivity",
                                        fast_estimate=estimates["fast"], slow_estimate=estimates["slow"], estimate=estimates["fast"] - estimates["slow"],
                                        ci_low=float(low), ci_high=float(high), tail_low=tails[0], tail_high=tails[1],
                                        defined_draws=len(finite), undefined_draws=resamples - len(finite),
                                        support_qualification="accepted_before_path_exclusion" if support == "all" else "conditional_completed_path_support",
                                        sparse_warning=any(counts[b + "_evaluable"] < 100 or counts[b + "_sessions"] < 30 for b in groups))
                                    row["row_id"] = row_id(row)
                                    rows.append(row)
    return pd.DataFrame(rows)
