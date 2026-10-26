"""Independent Stage 3 scalar, mask, selection and uncertainty references.

No numerical producer is imported. All masks follow the canonical saved slot
roster; they never restart causal state. Successful comparisons elsewhere use
lazy diagnostics so timestamp formatting is confined to actual mismatches.
"""
from __future__ import annotations

import math
from datetime import timedelta

import numpy as np
import pandas as pd

NY = "America/New_York"
METRICS = ("mfe", "mae", "terminal_delta")
FLAGS = ("favorable", "neutral", "adverse", "mfe_gt_mae", "mfe_mae_tie")
HORIZONS = (1, 2, 3, 5, 10, 12, 15, 20, 30, 40, 50, 60, 80, 100)
FIXED = {"ES": 2.4, "GC": 2., "NQ": 10.}


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def finite(value):
    return value is not None and pd.notna(value) and math.isfinite(float(value))


def boundary(value):
    stamp = pd.Timestamp(value)
    return stamp.tz_localize(NY).tz_convert("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")


def gate_id(family, threshold):
    return ("abs_" if family == "absolute" else "atr_") + format(float(threshold), ".12g").replace(".", "p")


def gate_grid(config, product):
    return [dict(gate_id=gate_id(f, x), family=f, threshold=float(x)) for f, values in
            (("absolute", config["absolute_gates"][product]), ("atr", config["atr_gates"])) for x in values]


def strata(row):
    stamp = pd.Timestamp(row["timestamp"]).tz_convert(NY)
    day, hour = stamp.date(), stamp.hour + stamp.minute / 60
    return dict(year=day.year, month=day.strftime("%Y-%m"), week=(day - timedelta(days=day.weekday())).isoformat(),
                calendar_date=day.isoformat(), hour=stamp.hour, session=str(row.get("session", day.isoformat())),
                time_stratum="Asia" if hour >= 18 or hour < 3 else "Europe" if hour < 9 else "US" if hour < 16 else "Late")


def iter_reference_stream(bars, gates, touch_modes=("fast", "slow")):
    """Replay every gate independently, retaining warmup and later causal events.

    Gate width failure consumes the selected penetration. ATR gates use only a
    finite positive ATR at the current signal slot. No period mask enters here.
    """
    require(not bars.duplicated(["product", "interval_minutes", "timestamp"]).any(), "duplicate reference slots")
    for (product, interval), group in bars.groupby(["product", "interval_minutes"], sort=False):
        require(group.timestamp.is_monotonic_increasing, "unordered reference slots")
        state = {(g["gate_id"], b): [False, 0] for g in gates for b in touch_modes}
        previous_direction, previous_contract, previous_reset_source = 0, None, None
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
                for s in state.values():
                    s[0] = False
            width = abs(float(base["ema20"]) - float(base["ema50"])) if valid and direction else None
            atr = base.get("atr14")
            atr_valid = finite(atr) and float(atr) > 0
            ratio = width / float(atr) if width is not None and atr_valid else None
            fast_touch = bool(valid and direction and base["low"] <= base["ema20"] <= base["high"])
            slow_touch = bool(valid and direction and base["low"] <= base["ema50"] <= base["high"])
            departure = bool(valid and direction and (base["low"] > max(base["ema20"], base["ema50"]) if direction == 1 else base["high"] < min(base["ema20"], base["ema50"])))
            for gate in gates:
                threshold, family = float(gate["threshold"]), gate["family"]
                value = width if family == "absolute" else ratio
                passes = bool(value is not None and value + 1e-10 * max(1., abs(threshold)) >= threshold)
                for branch in touch_modes:
                    s = state[(gate["gate_id"], branch)]
                    selected = "ema20" if branch == "fast" else "ema50"
                    touch = fast_touch if branch == "fast" else slow_touch
                    other = slow_touch if branch == "fast" else fast_touch
                    before = s[0]
                    penetration = bool(valid and direction and (base["low"] <= base[selected] if direction == 1 else base["high"] >= base[selected]))
                    candidate, accepted = bool(touch and before), bool(touch and before and passes)
                    reason = ("invalid_data_or_feature" if not valid else "no_direction" if not direction else
                              "accepted" if accepted else "not_armed" if touch and not before else
                              "atr_invalid" if candidate and family == "atr" and not atr_valid else
                              "width_below_minimum" if candidate and not passes else "gap_penetration" if penetration and not touch else
                              ("slow_only" if branch == "fast" else "fast_only") if other and not touch else "no_touch")
                    if penetration:
                        s[0] = False
                    if departure:
                        if not s[0]:
                            s[1] += 1
                        s[0] = True
                    side = "Buy" if direction == 1 else "Sell" if direction == -1 else "None"
                    eid = f"{product}|{int(interval)}m|{base['contract']}|{pd.Timestamp(base['timestamp']).isoformat()}|{side}|{branch}" if accepted else None
                    row = base | dict(touch_mode=branch, selected_ema=selected, gate_id=gate["gate_id"],
                        gate_family=family, gate_threshold=threshold, direction=direction, side=side, signal_idx=ordinal,
                        min_width=threshold if family == "absolute" else threshold * float(atr) if atr_valid else None,
                        width=width, width_ratio=ratio, width_pass=passes,
                        fast_touch=fast_touch, slow_touch=slow_touch, penetration=penetration, full_departure=departure,
                        armed_before=before, armed_after=s[0], episode_id=s[1], technical_candidate=touch,
                        setup_candidate=candidate, accepted=accepted, suppression_reason=reason, reset_reason=reset, event_id=eid)
                    event = None
                    if accepted:
                        event = row | strata(row) | dict(stage=3, signal_timestamp=base["timestamp"],
                            reference_price=base["close"], entry_at=base["available_at"], entry_atr=float(atr) if atr_valid else None)
                    yield row, event
            previous_direction, previous_contract = direction, base["contract"]
            if bool(base.get("feature_reset", False)):
                previous_reset_source = source


def reference_stream(bars, gates, touch_modes=("fast", "slow")):
    rows, events = [], []
    for row, event in iter_reference_stream(bars, gates, touch_modes):
        rows.append(row)
        if event is not None:
            events.append(event)
    columns = list(dict.fromkeys(list(bars.columns) + ["event_id", "gate_id", "gate_family", "gate_threshold", "touch_mode", "signal_idx", "entry_atr", "reference_price", "entry_at", "signal_timestamp"]))
    return pd.DataFrame(rows), pd.DataFrame(events, columns=columns if not events else None)


def segments(config, period):
    if period == "development":
        return [dict(id=f"{year}H{half}", start=f"{year}-{'01' if half == 1 else '07'}-01",
                     end=f"{year}-07-01" if half == 1 else f"{year + 1}-01-01") for year in (2018, 2019, 2020) for half in (1, 2)]
    if period == "validation":
        return config["validation_folds"]
    p = config["periods"][period]
    return [dict(id=period, start=p["start"], end=p["end"])]


def reference_masks(bars, config, period, horizons=HORIZONS, signal_indices=None):
    """Slot and event scoring masks. Unknown/invalid scheduled slots count.

    Closures are absent from the canonical roster. The endpoint test uses the
    final required slot's modeled completion; equality with endpoint is allowed.
    """
    frame = bars.reset_index(drop=True)
    opens = pd.to_datetime(frame.timestamp, utc=True).array.asi8
    closes = pd.to_datetime(frame.available_at, utc=True).array.asi8
    result = []
    for spec in segments(config, period):
        start, end = boundary(spec["start"]), boundary(spec["end"])
        positions = np.flatnonzero((opens >= start.value) & (opens < end.value))
        requested = positions if signal_indices is None else np.intersect1d(positions, np.asarray(signal_indices, dtype=np.int64))
        for i in requested:
            rank = int(np.searchsorted(positions, i))
            embargo = rank < int(config["canonical_start_embargo_slots"])
            for h in horizons:
                terminal = int(i) + int(h)
                purge = closes[terminal] > end.value if terminal < len(frame) else bool(len(closes) and closes[-1] >= end.value)
                reason = "start_embargo" if embargo else "period_endpoint_purge" if purge else ""
                result.append(dict(signal_idx=int(i), timestamp=frame.timestamp.iloc[i], period_id=period, fold_id=spec["id"],
                    horizon=int(h), horizon_minutes=int(h) * int(frame.interval_minutes.iloc[i]),
                    start_embargo=embargo, endpoint_purge=purge, score_eligible=not embargo and not purge,
                    mask_reason=reason, terminal_signal_idx=terminal, canonical_fold_rank=rank, fold_start=start, fold_end=end))
    return pd.DataFrame(result, columns=["signal_idx","timestamp","period_id","fold_id","horizon","horizon_minutes","start_embargo","endpoint_purge","score_eligible","mask_reason","terminal_signal_idx","canonical_fold_rank","fold_start","fold_end"])


def reference_outcomes(bars, events, config, period, horizons=HORIZONS):
    """One approved-phase observation per accepted signal and horizon.

    Endpoint/embargo exclusions are applied before any future price inspection.
    Signal state always comes from the uninterrupted causal roster.
    """
    start, end = (boundary(config["periods"][period][k]) for k in ("start", "end"))
    require(all(start <= pd.Timestamp(t) < end for t in events.timestamp), "reference outcomes outside approved period")
    require(not events.duplicated(["gate_id", "event_id"]).any(), "duplicate gate reference event")
    masks = reference_masks(bars, config, period, horizons, events.signal_idx.unique()).set_index(["signal_idx", "horizon"])
    a = {k: bars[k].to_numpy() for k in bars}
    result = []
    for item in events.itertuples(index=False):
        event = item._asdict()
        i = int(event["signal_idx"])
        require(pd.Timestamp(a["timestamp"][i]) == pd.Timestamp(event["timestamp"]), "reference event roster identity")
        for h in horizons:
            mask = masks.loc[(i, int(h))].to_dict()
            row = event | {k: mask[k] for k in ("period_id", "fold_id", "start_embargo", "endpoint_purge", "score_eligible", "mask_reason", "terminal_signal_idx")}
            row.update(stage=3, split=period)
            row.update(horizon=int(h), horizon_minutes=int(h) * int(event["interval_minutes"]), atr_support=finite(event.get("entry_atr")) and float(event["entry_atr"]) > 0,
                       status="excluded" if not mask["score_eligible"] else "censored", censor_reason="", terminal_at=None,
                       elapsed_minutes=None, crosses_closure=None, same_session=None)
            row.update({k: None for k in METRICS + tuple(m + "_atr" for m in METRICS) + FLAGS + tuple(m + "_attainment_" + edge for m in ("mfe", "mae") for edge in ("start", "end"))})
            if not mask["score_eligible"]:
                result.append(row)
                continue
            if i + int(h) >= len(bars):
                row["censor_reason"] = "data_edge"
                result.append(row)
                continue
            required = range(i + 1, i + int(h) + 1)
            for j in required:
                if not bool(a["usable"][j]) or not all(finite(a[k][j]) for k in ("high", "low", "close")):
                    row["censor_reason"] = "invalid_future_slot:" + str(a.get("quality_reason", ["unusable"] * len(bars))[j])
                    break
                if a["contract"][j] != event["contract"]:
                    row["censor_reason"] = "contract_switch"
                    break
            else:
                d, ref = int(event["direction"]), float(event["reference_price"])
                favorable = [d * (float(a["high" if d == 1 else "low"][j]) - ref) for j in required]
                adverse = [d * (ref - float(a["low" if d == 1 else "high"][j])) for j in required]
                mfe, mae = max(0., max(favorable)), max(0., max(adverse))
                delta = d * (float(a["close"][i + int(h)]) - ref)
                terminal = pd.Timestamp(a["available_at"][i + int(h)])
                eps = 1e-10 * max(1., mfe, mae)
                row.update(status="completed", terminal_at=terminal, elapsed_minutes=(terminal - pd.Timestamp(event["entry_at"])).total_seconds() / 60,
                    crosses_closure=any(bool(a.get("known_closure_before", np.zeros(len(bars), dtype=bool))[j]) for j in required),
                    same_session=all(str(a["session"][j]) == str(event["session"]) for j in required), mfe=mfe, mae=mae,
                    terminal_delta=delta, favorable=delta > 0, neutral=delta == 0, adverse=delta < 0,
                    mfe_gt_mae=mfe - mae > eps, mfe_mae_tie=abs(mfe - mae) <= eps)
                for metric, values in (("mfe", favorable), ("mae", adverse)):
                    if row[metric] > 0:
                        j = i + 1 + values.index(max(values))
                        row[metric + "_attainment_start"], row[metric + "_attainment_end"] = pd.Timestamp(a["timestamp"][j]), pd.Timestamp(a["available_at"][j])
                if row["atr_support"]:
                    for metric in METRICS:
                        row[metric + "_atr"] = row[metric] / float(event["entry_atr"])
            result.append(row)
    cols = list(dict.fromkeys(list(events.columns) + ["period_id", "fold_id", "horizon", "horizon_minutes", "status", "censor_reason", "start_embargo", "endpoint_purge", "score_eligible", "mask_reason", "atr_support","terminal_signal_idx","terminal_at","elapsed_minutes","crosses_closure","same_session"] + list(METRICS) + [m + "_atr" for m in METRICS] + list(FLAGS) + [m+"_attainment_"+edge for m in ("mfe","mae") for edge in ("start","end")]))
    return pd.DataFrame(result, columns=cols if not result else None)


def linear_quantile(values, probability):
    values = sorted(float(v) for v in values if finite(v))
    if not values:
        return None
    pos = float(probability) * (len(values) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] + (pos - lo) * (values[hi] - values[lo])


def week_roster(start, end):
    first = boundary(start).tz_convert(NY).date()
    last = (boundary(end) - pd.Timedelta(nanoseconds=1)).tz_convert(NY).date()
    first -= timedelta(days=first.weekday())
    last -= timedelta(days=last.weekday())
    return [(first + timedelta(weeks=i)).isoformat() for i in range((last - first).days // 7 + 1)]


def sampled_week_indices(n, block, draws=10000, seed=20261010):
    require(n > 0 and block > 0 and draws > 0, "positive bootstrap dimensions")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(draws, math.ceil(n / block)))
    return ((starts[:, :, None] + np.arange(block)[None, None, :]) % n).reshape(draws, -1)[:, :n]


def weekly_sufficient(outcomes, metric, roster, weighting="event"):
    frame = outcomes.loc[outcomes.status.eq("completed") & outcomes[metric].map(finite)].copy()
    if weighting == "session":
        values = frame.groupby("session", sort=False)[metric].mean()
        frame = pd.DataFrame({metric: values.values, "week": [(pd.Timestamp(s).date() - timedelta(days=pd.Timestamp(s).weekday())).isoformat() for s in values.index]})
    else:
        require(weighting == "event", "unknown weighting")
    groups = frame.groupby("week")[metric].agg(["sum", "count"]) if len(frame) else pd.DataFrame(columns=["sum", "count"])
    require(set(groups.index).issubset(set(roster)), "observation week outside period roster")
    groups = groups.reindex(roster, fill_value=0)
    return groups["sum"].to_numpy(float), groups["count"].to_numpy(float)


def reference_uncertainty(selected, fixed, metric, roster, block=4, weighting="event", draws=10000, seed=20261010, family_size=12):
    indices = sampled_week_indices(len(roster), block, draws, seed)
    ss, sn = weekly_sufficient(selected, metric, roster, weighting)
    fs, fn = weekly_sufficient(fixed, metric, roster, weighting)
    sd, fd = sn[indices].sum(axis=1), fn[indices].sum(axis=1)
    values = np.divide(ss[indices].sum(axis=1), sd, out=np.full(draws, np.nan), where=sd > 0) - np.divide(fs[indices].sum(axis=1), fd, out=np.full(draws, np.nan), where=fd > 0)
    defined = values[np.isfinite(values)]
    return dict(estimate=float(ss.sum() / sn.sum() - fs.sum() / fn.sum()) if sn.sum() > 0 and fn.sum() > 0 else None,
                ci_low=linear_quantile(defined, .025), ci_high=linear_quantile(defined, .975),
                adjusted_low=linear_quantile(defined, .05 / (2 * family_size)), adjusted_high=linear_quantile(defined, 1 - .05 / (2 * family_size)),
                defined_draws=len(defined), undefined_draws=draws - len(defined))


def cohort(outcomes):
    """H15 common ATR support, with each candidate's own accepted observations."""
    h = outcomes.loc[outcomes.horizon.eq(15) & outcomes.atr_support.astype(bool)]
    done = h.loc[h.status.eq("completed")]
    return dict(completed=len(done), sessions=done.session.nunique(), weeks=done.week.nunique(),
        mean_terminal_delta_atr=float(done.terminal_delta_atr.mean()) if len(done) else None,
        mean_mfe_atr=float(done.mfe_atr.mean()) if len(done) else None,
        mean_mae_atr=float(done.mae_atr.mean()) if len(done) else None)


def candidate_assessment(candidate, fixed, config, phase="development"):
    """Independently derive every guard from saved event paths, not fold tables."""
    folds = config["development_folds"] if phase == "development" else config["validation_folds"]
    ids = [f["id"] for f in folds]
    candidate = candidate.loc[candidate.fold_id.isin(ids)]
    fixed = fixed.loc[fixed.fold_id.isin(ids)]
    c, b = cohort(candidate), cohort(fixed)
    cfg = config["selection" if phase == "development" else "validation"]
    fold_rows = []
    for fid in ids:
        cf, bf = cohort(candidate.loc[candidate.fold_id.eq(fid)]), cohort(fixed.loc[fixed.fold_id.eq(fid)])
        diff = cf["mean_terminal_delta_atr"] - bf["mean_terminal_delta_atr"] if finite(cf["mean_terminal_delta_atr"]) and finite(bf["mean_terminal_delta_atr"]) else None
        fold_rows.append(dict(fold_id=fid, **cf, baseline_completed=bf["completed"], baseline_mean_terminal_delta_atr=bf["mean_terminal_delta_atr"], improvement=diff))
    objective = float(np.mean([f["mean_terminal_delta_atr"] for f in fold_rows])) if all(finite(f["mean_terminal_delta_atr"]) for f in fold_rows) else None
    baseline_score = float(np.mean([f["baseline_mean_terminal_delta_atr"] for f in fold_rows])) if all(finite(f["baseline_mean_terminal_delta_atr"]) for f in fold_rows) else None
    improvement = objective - baseline_score if phase == "development" and finite(objective) and finite(baseline_score) else c["mean_terminal_delta_atr"] - b["mean_terminal_delta_atr"] if phase != "development" and finite(c["mean_terminal_delta_atr"]) and finite(b["mean_terminal_delta_atr"]) else None
    retention = c["completed"] / b["completed"] if b["completed"] else None
    defined = all(finite(x) for x in (objective, improvement, retention, c["mean_mae_atr"], b["mean_mae_atr"], c["mean_mfe_atr"], b["mean_mfe_atr"])) and all(finite(f["improvement"]) for f in fold_rows)
    guards = dict(pooled_completed=c["completed"] >= cfg["minimum_completed"], pooled_sessions=c["sessions"] >= cfg["minimum_sessions"], pooled_weeks=c["weeks"] >= cfg["minimum_weeks"],
        fold_completed=all(f["completed"] >= cfg["minimum_fold_completed"] for f in fold_rows), fold_sessions=all(f["sessions"] >= cfg["minimum_fold_sessions"] for f in fold_rows),
        retention=finite(retention) and retention >= cfg["minimum_baseline_retention"],
        mae=finite(c["mean_mae_atr"]) and finite(b["mean_mae_atr"]) and c["mean_mae_atr"] <= b["mean_mae_atr"] * cfg["maximum_mean_mae_baseline_multiple"],
        mfe=finite(c["mean_mfe_atr"]) and finite(b["mean_mfe_atr"]) and c["mean_mfe_atr"] >= b["mean_mfe_atr"] * cfg["minimum_mean_mfe_baseline_multiple"],
        positive_folds=sum(finite(f["improvement"]) and f["improvement"] > 0 for f in fold_rows) >= cfg["minimum_positive_folds"],
        overall_improvement=finite(improvement) and improvement > 0, defined=defined)
    return dict(**c, baseline_completed=b["completed"], baseline_equal_fold_score=baseline_score, retention=retention, score=objective, improvement=improvement,
                positive_folds=sum(finite(f["improvement"]) and f["improvement"] > 0 for f in fold_rows), guards=guards,
                eligible=all(guards.values()), failed_guards="|".join(k for k, passed in guards.items() if not passed), folds=fold_rows)


def independent_selection(candidates, fixed, gates, config):
    assessments = [dict(**g, **candidate_assessment(candidates[g["gate_id"]], fixed, config)) for g in gates]
    eligible = [a for a in assessments if a["eligible"]]
    maximum=max((a["score"] for a in eligible),default=None)
    tied=[a for a in eligible if maximum-a["score"]<=float(config["selection_tie_epsilon_scale"])*max(1.,abs(maximum),abs(a["score"]))]
    ranked=sorted(tied,key=lambda a:(-a["completed"],0 if a["family"]=="absolute" else 1,a["threshold"],a["gate_id"]))
    return dict(assessments=assessments, nominee=ranked[0]["gate_id"] if ranked else None,
                selection_status="eligible_nominee" if ranked else "fixed_baseline_no_eligible_improvement")
