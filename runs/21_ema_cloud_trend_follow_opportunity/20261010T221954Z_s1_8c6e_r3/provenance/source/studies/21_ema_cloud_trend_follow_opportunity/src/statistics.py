"""Frozen descriptive estimators and paired calendar-block uncertainty.

Raw price points are never pooled across products. Circular week blocks share
identical draw weights across every product, candle interval, and direction.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

SIDES = ("All", "Buy", "Sell")
METRICS = ("mfe", "mae", "terminal_delta")
PS = tuple(sorted(set([i / 10 for i in range(11)] + [.25, .75, .95])))
GROUP = ("product", "interval_minutes", "direction", "horizon", "unit", "support")


def _key(product, interval, side, horizon, unit="points", support="all"):
    return dict(stage=1, product=product, interval_minutes=int(interval), direction=side,
                touch_mode="slow", gate_id="fixed", split="development", support=support,
                horizon=int(horizon), horizon_minutes=int(interval) * int(horizon), unit=unit)


def _row_id(row, extra=()):
    return "|".join(str(row.get(k, "")) for k in ("stage", "product", "interval_minutes", "direction",
                    "touch_mode", "gate_id", "horizon", "unit", "split", "support") + tuple(extra))


def _cohorts(outcomes, supports=("all",)):
    for (product, interval, h), group in outcomes.groupby(["product", "interval_minutes", "horizon"], sort=True):
        for side in SIDES:
            side_group = group if side == "All" else group.loc[group.side.eq(side)]
            for support in supports:
                cohort = side_group
                if support == "same_session":
                    cohort = cohort.loc[cohort.same_session.eq(True)]
                elif support == "uninterrupted":
                    cohort = cohort.loc[cohort.crosses_closure.eq(False)]
                for unit in ("points", "atr"):
                    yield _key(product, interval, side, h, unit, support), cohort


def _evaluable(group, unit):
    complete = group.loc[group.status.eq("completed")].copy()
    cols = list(METRICS) if unit == "points" else [m + "_atr" for m in METRICS]
    good = complete.loc[complete[cols].notna().all(axis=1)].copy()
    for metric, col in zip(METRICS, cols):
        good[metric] = good[col].astype(float)
    return complete, good


def _summary(group, unit):
    complete, good = _evaluable(group, unit)
    n, accepted = len(good), len(group)
    result = dict(accepted=accepted, completed=len(complete), censored=accepted - len(complete),
                  evaluable=n, normalization_missing=len(complete) - n,
                  contributing_sessions=good.session.nunique(), contributing_weeks=good.week.nunique())
    result["sparse_warning"] = n < 100 or result["contributing_sessions"] < 30
    for metric in METRICS:
        result["mean_" + metric] = float(good[metric].mean()) if n else np.nan
        result["median_" + metric] = float(good[metric].median()) if n else np.nan
        session_means = good.groupby("session")[metric].mean()
        result["session_mean_" + metric] = float(session_means.mean()) if len(session_means) else np.nan
        for q in (.1, .25, .5, .75, .9, .95):
            result[f"{metric}_p{int(q * 100):02d}"] = float(good[metric].quantile(q, interpolation="linear")) if n else np.nan
    for flag in ("favorable", "neutral", "adverse", "mfe_gt_mae", "mfe_mae_tie"):
        vals = good[flag].astype(float)
        result[flag + "_count"] = int(vals.sum()) if n else 0
        result[flag + "_share"] = float(vals.mean()) if n else np.nan
        result["session_" + flag + "_share"] = float(vals.groupby(good.session).mean().mean()) if n else np.nan
    favorable = int(complete.favorable.eq(True).sum()) if len(complete) else 0
    result["missing_worst_favorable_share"] = favorable / accepted if accepted else np.nan
    result["missing_best_favorable_share"] = (favorable + accepted - len(complete)) / accepted if accepted else np.nan
    result["mean_elapsed_minutes"] = float(good.elapsed_minutes.mean()) if n else np.nan
    result["closure_crossing_completed"] = int(complete.crosses_closure.eq(True).sum())
    result["same_session_completed"] = int(complete.same_session.eq(True).sum())
    return result


def summarize(outcomes, supports=("all",)):
    rows = []
    for key, group in _cohorts(outcomes, supports):
        row = key | _summary(group, key["unit"])
        row["row_id"] = _row_id(row)
        rows.append(row)
    return pd.DataFrame(rows)


def quantiles(outcomes):
    rows = []
    for key, group in _cohorts(outcomes):
        _, good = _evaluable(group, key["unit"])
        for metric in METRICS:
            for p in PS:
                row = key | dict(metric=metric, quantile=p, percentile=100 * p,
                                 value=float(good[metric].quantile(p, interpolation="linear")) if len(good) else np.nan,
                                 evaluable=len(good), quantile_method="linear_rank_p_times_n_minus_1")
                row["row_id"] = _row_id(row, ("metric", "percentile"))
                rows.append(row)
    return pd.DataFrame(rows)


def stability(outcomes, session_roster=None):
    """H15 annual, fixed session/hour, and complete calendar week/month panels.

    Zero accepted calendar periods have null outcomes. A separate technical
    coverage roster establishes whether zero opportunities are auditable.
    """
    rows = []
    weeks = pd.date_range("2018-01-01", "2020-12-28", freq="W-MON").strftime("%Y-%m-%d")
    periods = {"year": [2018, 2019, 2020], "time_stratum": ["Asia", "Europe", "US", "Late"],
               "hour": list(range(24)), "week": list(weeks),
               "month": list(pd.period_range("2018-01", "2020-12", freq="M").astype(str))}
    periods["session"] = sorted(set(map(str, session_roster if session_roster is not None else outcomes.session.unique())))
    primary = outcomes.loc[outcomes.horizon.eq(15)]
    for key, group in _cohorts(primary):
        for kind, values in periods.items():
            for value in values:
                part = group.loc[group[kind].eq(value)]
                row = key | dict(period_kind=kind, period=str(value)) | _summary(part, key["unit"])
                row["row_id"] = _row_id(row, ("period_kind", "period"))
                rows.append(row)
    return pd.DataFrame(rows)


def signal_flow(technical, events, outcomes):
    rows = []
    local = pd.to_datetime(technical.timestamp, utc=True).dt.tz_convert("America/New_York")
    tech = technical.loc[local.dt.year.between(2018, 2020)]
    for (product, interval), group in tech.groupby(["product", "interval_minutes"], sort=True):
        for side in SIDES:
            part = group if side == "All" else group.loc[group.side.eq(side)]
            key = _key(product, interval, side, 0)
            counts = {"scheduled_slots": len(part), "usable_slots": int(part.usable.sum()),
                      "feature_valid_slots": int(part.feature_valid.sum()),
                      "eligible_slots": int((part.usable & part.feature_valid).sum()),
                      "technical_candidates": int(part.technical_candidate.sum()),
                      "setup_candidates": int(part.setup_candidate.sum()), "accepted": int(part.accepted.sum()),
                      "eligible_sessions": part.loc[part.usable & part.feature_valid, "session"].nunique()}
            for reason, count in part.suppression_reason.value_counts().items():
                counts["suppressed:" + reason] = int(count)
            for reason, count in counts.items():
                row = key | dict(flow_kind="signal", reason=reason, count=count)
                row["row_id"] = _row_id(row, ("flow_kind", "reason"))
                rows.append(row)
            os = outcomes.loc[outcomes["product"].eq(product) & outcomes.interval_minutes.eq(interval)]
            if side != "All":
                os = os.loc[os.side.eq(side)]
            for h, sub in os.groupby("horizon", sort=True):
                reasons = {"accepted": len(sub), "completed": int(sub.status.eq("completed").sum()),
                           "censored": int(sub.status.eq("censored").sum())}
                reasons.update({"censor:" + r: int(n) for r, n in sub.loc[sub.status.eq("censored"), "censor_reason"].value_counts().items()})
                for reason, count in reasons.items():
                    row = _key(product, interval, side, h) | dict(flow_kind="outcome", reason=reason, count=count)
                    row["row_id"] = _row_id(row, ("flow_kind", "reason"))
                    rows.append(row)
    return pd.DataFrame(rows)


def _contrast_specs(outcomes):
    hs = set(outcomes.horizon)
    common = [h for h in (5, 10, 15, 20, 30, 50, 100) if h in hs]
    specs = [("same_horizon", h, h) for h in common]
    specs += [("equal_active_60", 20, 12), ("equal_active_150", 50, 30)]
    return specs


def comparisons(outcomes):
    score = summarize(outcomes, supports=("all", "uninterrupted", "same_session"))
    lookup = {(r.product, r.interval_minutes, r.direction, r.horizon, r.unit, r.support): r for r in score.itertuples()}
    rows = []
    for product in sorted(outcomes["product"].unique()):
        for side in SIDES:
            for unit in ("points", "atr"):
                for support in ("all", "uninterrupted", "same_session"):
                    for name, h3, h5 in _contrast_specs(outcomes):
                        a = lookup.get((product, 3, side, h3, unit, support))
                        b = lookup.get((product, 5, side, h5, unit, support))
                        if a is None or b is None:
                            continue
                        row = dict(stage=1, product=product, direction=side, unit=unit, support=support,
                                   comparison=name, interval_a=3, horizon_a=h3, interval_b=5, horizon_b=h5,
                                   minutes_a=3 * h3, minutes_b=5 * h5, completed_a=a.completed, completed_b=b.completed,
                                   sessions_a=a.contributing_sessions, sessions_b=b.contributing_sessions)
                        for metric in METRICS:
                            row["difference_mean_" + metric] = getattr(a, "mean_" + metric) - getattr(b, "mean_" + metric)
                            row["difference_session_mean_" + metric] = getattr(a, "session_mean_" + metric) - getattr(b, "session_mean_" + metric)
                        row["row_id"] = "|".join(map(str, [1, product, side, unit, support, name, h3, h5]))
                        rows.append(row)
    return pd.DataFrame(rows)


def calendar_weights(resamples=10000, seed=20261010, block_weeks=4):
    """Return full-week roster and circular moving-block multiplicities."""
    weeks = list(pd.date_range("2018-01-01", "2020-12-28", freq="W-MON").strftime("%Y-%m-%d"))
    if block_weeks < 1 or resamples < 1:
        raise ValueError("positive resamples and block size required")
    rng, n = np.random.default_rng(seed), len(weeks)
    starts = rng.integers(0, n, size=(resamples, math.ceil(n / block_weeks)))
    indices = ((starts[:, :, None] + np.arange(block_weeks)) % n).reshape(resamples, -1)[:, :n]
    weights = np.zeros((resamples, n), dtype=np.float64)
    np.add.at(weights, (np.repeat(np.arange(resamples), n), indices.ravel()), 1.)
    return weeks, weights


def _interval(draws):
    finite = draws[np.isfinite(draws)]
    lo, hi = np.quantile(finite, [.025, .975], method="linear") if len(finite) else (np.nan, np.nan)
    return dict(ci_low=float(lo), ci_high=float(hi), defined_draws=len(finite), undefined_draws=len(draws) - len(finite))


def bootstrap(outcomes, resamples=10000, seed=20261010, block_lengths=(4, 1, 8)):
    """Primary H15 and 60/150-minute means/shares, plus paired 3m-minus-5m CIs.

    A sampled week carries all its events and contributing-session means.
    Empty weeks participate with zero weight denominators; undefined draws are
    counted. No independence assumption is made for overlapping observations.
    """
    primary = outcomes.loc[(outcomes.horizon.eq(15)) |
        (outcomes.interval_minutes.eq(3) & outcomes.horizon.isin([20, 50])) |
        (outcomes.interval_minutes.eq(5) & outcomes.horizon.isin([12, 30]))]
    rows = []
    for block in block_lengths:
        weeks, weights = calendar_weights(resamples, seed, block)
        draw_lookup = {}
        for key, group in _cohorts(primary):
            _, good = _evaluable(group, key["unit"])
            for metric in METRICS + ("favorable", "mfe_gt_mae"):
                for weighting in ("event", "session"):
                    vals = good.loc[:, ["week", "session", metric]].copy()
                    vals[metric] = vals[metric].astype(float)
                    if weighting == "session":
                        vals = vals.groupby("session", as_index=False)[metric].mean()
                        dates = pd.to_datetime(vals.session)
                        vals["week"] = (dates - pd.to_timedelta(dates.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
                    weekly = vals.groupby("week")[metric].agg(["sum", "count"]).reindex(weeks, fill_value=0)
                    sums = weights @ weekly["sum"].to_numpy(float)
                    counts = weights @ weekly["count"].to_numpy(float)
                    draws = np.divide(sums, counts, out=np.full(resamples, np.nan), where=counts > 0)
                    estimate = float(vals[metric].mean()) if len(vals) else np.nan
                    row = key | dict(block_weeks=block, resamples=resamples, seed=seed, metric=metric,
                                    weighting=weighting, estimate=estimate, kind="cohort") | _interval(draws)
                    row["row_id"] = _row_id(row, ("block_weeks", "metric", "weighting"))
                    rows.append(row)
                    draw_lookup[(key["product"], key["interval_minutes"], key["direction"], key["horizon"], key["unit"], metric, weighting)] = (draws, estimate)
        for product in sorted(primary["product"].unique()):
            for side in SIDES:
                for unit in ("points", "atr"):
                    for name, h3, h5 in [("same_horizon", 15, 15), ("equal_active_60", 20, 12), ("equal_active_150", 50, 30)]:
                        for metric in METRICS:
                            for weighting in ("event", "session"):
                                a = draw_lookup.get((product, 3, side, h3, unit, metric, weighting))
                                b = draw_lookup.get((product, 5, side, h5, unit, metric, weighting))
                                if a is None or b is None:
                                    continue
                                row = dict(stage=1, product=product, direction=side, unit=unit, support="all", kind="contrast",
                                           comparison=name, horizon_a=h3, horizon_b=h5, metric=metric, weighting=weighting,
                                           block_weeks=block, resamples=resamples, seed=seed, estimate=a[1] - b[1]) | _interval(a[0] - b[0])
                                row["row_id"] = "|".join(map(str, [1, product, side, unit, name, h3, h5, metric, weighting, block]))
                                rows.append(row)
    return pd.DataFrame(rows)
