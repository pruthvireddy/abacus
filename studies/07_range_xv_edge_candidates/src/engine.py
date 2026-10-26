"""Frozen, chart-price-only Range XV candidate extraction and summaries."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import json

import numpy as np
import pandas as pd


IDEAS = ("pullback", "exhaustion", "quiet_breakout")
PRIMARY = {"pullback": ("extreme_break", "unfiltered", 1),
           "exhaustion": ("wait_policy", "early_policy", 3),
           "quiet_breakout": ("quiet", "not_quiet", 3)}


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_inputs(root: Path, lock: dict) -> list[dict]:
    records = [lock["manifest"], *lock["files"]]
    checked = []
    for record in records:
        path = (root / record["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise FileNotFoundError(record["path"])
        actual = digest(path)
        if actual != record["sha256"]:
            raise ValueError(f"input hash differs: {record['path']}")
        checked.append({"path": record["path"], "sha256": actual, "bytes": path.stat().st_size})
    return checked


def load_chart(path: Path, tick_size: float, excluded_session: str) -> pd.DataFrame:
    columns = ["source_row", "bar_start_timestamp", "completion_proxy_status", "session_date_proxy",
               "open", "high", "low", "close"]
    df = pd.read_csv(path, sep=";", usecols=columns)
    if df.empty or not df["source_row"].is_monotonic_increasing or df["source_row"].iloc[0] != 1:
        raise ValueError(f"source order invalid: {path}")
    if not (df["source_row"].to_numpy() == np.arange(1, len(df) + 1)).all():
        raise ValueError(f"source rows not contiguous: {path}")
    df = df.loc[df["session_date_proxy"] != excluded_session].copy().reset_index(drop=True)
    df["start"] = pd.to_datetime(df["bar_start_timestamp"], format="%Y-%m-%d %H:%M:%S")
    df["signal_clock"] = df["bar_start_timestamp"].str[-8:]
    if not df["start"].is_monotonic_increasing:
        raise ValueError(f"bar starts regress: {path}")
    for name in ("open", "high", "low", "close"):
        scaled = df[name].to_numpy(dtype=np.float64) / tick_size
        rounded = np.rint(scaled)
        if not np.isfinite(scaled).all() or np.max(np.abs(scaled - rounded)) > 1e-6:
            raise ValueError(f"off-tick or nonfinite {name}: {path}")
        df[name + "_tick"] = rounded.astype(np.int64)
    if ((df["high_tick"] < df[["open_tick", "close_tick", "low_tick"]].max(axis=1)) |
        (df["low_tick"] > df[["open_tick", "close_tick", "high_tick"]].min(axis=1))).any():
        raise ValueError(f"invalid OHLC: {path}")
    df["direction"] = np.sign(df["close_tick"] - df["open_tick"]).astype(np.int8)
    direction = df["direction"]
    session = df["session_date_proxy"]
    changes = direction.ne(direction.shift()) | session.ne(session.shift()) | direction.eq(0)
    groups = changes.cumsum()
    df["run_length"] = (df.groupby(groups).cumcount() + 1).where(direction.ne(0), 0).astype(np.int32)
    df["strict_completion"] = df["completion_proxy_status"].eq("next_bar_start_proxy")
    return df


def prior_30m_counts(df: pd.DataFrame) -> np.ndarray:
    counts = np.zeros(len(df), dtype=np.int32)
    starts = df["start"].to_numpy(dtype="datetime64[ns]").astype("int64")
    dates = df["session_date_proxy"].to_numpy()
    cut = np.flatnonzero(np.r_[True, dates[1:] != dates[:-1], True])
    for lo, hi in zip(cut[:-1], cut[1:]):
        times = starts[lo:hi]
        left = np.searchsorted(times, times - 30 * 60 * 1_000_000_000, side="left")
        counts[lo:hi] = np.arange(hi - lo, dtype=np.int32) - left
    return counts


def quiet_thresholds(df: pd.DataFrame, protocol: dict) -> dict[int, float]:
    start, end = protocol["splits"]["development"]
    calibration = df.loc[df["session_date_proxy"].between(start, end) & df["full_30m_window"]]
    q = calibration.groupby("clock_bucket")["prior_30m"].quantile(protocol["idea_3"]["quiet_quantile"])
    if len(q) < 40:
        raise ValueError("development period lacks broad export-clock coverage")
    return {int(k): float(v) for k, v in q.items()}


def masks(df: pd.DataFrame, protocol: dict, thresholds: dict[int, float]) -> dict[str, np.ndarray]:
    d = df["direction"]
    s = df["session_date_proxy"]
    prev = s.eq(s.shift(1)) & s.eq(s.shift(2))
    base = (d.ne(0) & d.eq(d.shift(2)) & d.shift(1).eq(-d) &
            df["run_length"].shift(2).ge(protocol["idea_1"]["prior_run_min"]) & prev)
    extreme = pd.Series(np.where(d.gt(0), df["close_tick"].gt(df["high_tick"].shift(1)),
                                 df["close_tick"].lt(df["low_tick"].shift(1))), index=df.index)
    reversal = d.ne(0) & d.eq(-d.shift(1)) & s.eq(s.shift(1))
    long_run = reversal & df["run_length"].shift(1).ge(protocol["idea_2"]["long_run_min"])
    short_run = reversal & df["run_length"].shift(1).between(1, 2)
    same_two = d.ne(0) & d.eq(d.shift(1)) & s.eq(s.shift(1))
    before = s.eq(s.shift(11))
    high_ref = df.groupby("session_date_proxy")["high_tick"].transform(lambda x: x.shift(2).rolling(10, min_periods=10).max())
    low_ref = df.groupby("session_date_proxy")["low_tick"].transform(lambda x: x.shift(2).rolling(10, min_periods=10).min())
    breakout = same_two & before & pd.Series(np.where(d.gt(0), df["close_tick"].gt(high_ref),
                                                       df["close_tick"].lt(low_ref)), index=df.index)
    first_bucket = df["clock_bucket"].shift(1)
    quiet_limit = first_bucket.map(thresholds)
    full_window = df["full_30m_window"].shift(1, fill_value=False)
    quiet = breakout & full_window & df["prior_30m"].shift(1).le(quiet_limit)
    breakout &= full_window
    strict = df["strict_completion"]
    return {"pullback/extreme_break": (base & extreme & strict).to_numpy(),
            "pullback/unfiltered": (base & strict).to_numpy(),
            "pullback/no_break": (base & ~extreme & strict).to_numpy(),
            "pullback/ordinary": (d.ne(0) & d.eq(d.shift(1)) & df["run_length"].shift(1).ge(3) & s.eq(s.shift(1)) & strict).to_numpy(),
            "exhaustion/early_policy": (long_run & strict).to_numpy(),
            "exhaustion/short_run_control": (short_run & strict).to_numpy(),
            "quiet_breakout/quiet": (quiet & strict).to_numpy(),
            "quiet_breakout/not_quiet": (breakout & ~quiet & strict).to_numpy()}


def select_nonoverlap(indices: np.ndarray, horizon: int, dates: np.ndarray, extra_exit: int = 0) -> tuple[np.ndarray, int]:
    selected = []
    previous_exit = -1
    invalid = 0
    length = len(dates)
    for i in indices:
        exit_index = int(i) + 1 + horizon + extra_exit
        if exit_index >= length or dates[exit_index] != dates[i]:
            invalid += 1
            continue
        if i + 1 <= previous_exit:
            continue
        selected.append(int(i))
        previous_exit = exit_index
    return np.asarray(selected, dtype=np.int64), invalid


def evaluate_events(df: pd.DataFrame, indices: np.ndarray, *, product: str, idea: str, cohort: str,
                    horizon: int, setting: int, wait: bool = False) -> pd.DataFrame:
    if not len(indices):
        return pd.DataFrame(columns=["product", "idea", "cohort", "session_date", "signal_index", "direction",
                                     "signal_clock", "opening_hour", "traded", "return_ticks", "delay_return_ticks",
                                     "adverse_ticks", "favorable_ticks", "body_fraction", "adverse_wick_fraction",
                                     "horizon_bars", "confirmation_cost_ticks"])
    d = df["direction"].to_numpy()
    o = df["open_tick"].to_numpy()
    h = df["high_tick"].to_numpy()
    l = df["low_tick"].to_numpy()
    c = df["close_tick"].to_numpy()
    dates = df["session_date_proxy"].to_numpy()
    clock = df["signal_clock"].to_numpy()
    strict = df["strict_completion"].to_numpy()
    rows = []
    for i in indices:
        i = int(i)
        confirmed = bool(d[i + 1] == d[i] and strict[i + 1] and dates[i + 2] == dates[i]) if wait else True
        entry = i + (2 if wait else 1)
        exit_index = entry + horizon
        traded = confirmed
        signed = int(d[i] * (o[exit_index] - o[entry])) if traded else 0
        if traded:
            lows = l[entry:exit_index]
            highs = h[entry:exit_index]
            adverse = max(0, int(o[entry] - lows.min())) if d[i] > 0 else max(0, int(highs.max() - o[entry]))
            favorable = max(0, int(highs.max() - o[entry])) if d[i] > 0 else max(0, int(o[entry] - lows.min()))
        else:
            adverse = favorable = None
        delay_entry = entry + 1
        delay_exit = exit_index + 1
        delayed = int(d[i] * (o[delay_exit] - o[delay_entry])) if traded and delay_exit < len(df) and dates[delay_exit] == dates[i] else None
        rng = int(h[i] - l[i])
        body = abs(int(c[i] - o[i])) / rng if rng else None
        wick = (int(o[i] - l[i]) if d[i] > 0 else int(h[i] - o[i])) / rng if rng else None
        rows.append({"product": product, "idea": idea, "cohort": cohort, "session_date": dates[i],
                     "signal_index": i, "direction": int(d[i]), "signal_clock": clock[i],
                     "opening_hour": "09:30:00" <= clock[i] < "10:30:00", "traded": traded,
                     "return_ticks": signed, "delay_return_ticks": delayed, "adverse_ticks": adverse,
                     "favorable_ticks": favorable, "body_fraction": body, "adverse_wick_fraction": wick,
                     "horizon_bars": horizon,
                     "confirmation_cost_ticks": int(d[i] * (o[i + 2] - o[i + 1])) if wait and confirmed else None})
    return pd.DataFrame(rows)


def extract_product(root: Path, record: dict, protocol: dict, out_dir: Path) -> dict:
    product = record["product"]
    chart = protocol["primary_charts"][product]
    df = load_chart(root / record["path"], chart["tick_size"], protocol["excluded_partial_session"])
    df["prior_30m"] = prior_30m_counts(df)
    df["clock_bucket"] = df["start"].dt.hour * 2 + df["start"].dt.minute // 30
    first_start = df.groupby("session_date_proxy")["start"].transform("first")
    df["full_30m_window"] = (df["start"] - first_start) >= pd.Timedelta(minutes=30)
    thresholds = quiet_thresholds(df, protocol)
    conditions = masks(df, protocol, thresholds)
    dates = df["session_date_proxy"].to_numpy()
    outputs = []
    secondary = []
    audits = []
    for key, mask in conditions.items():
        idea, cohort = key.split("/")
        horizon = int(protocol[f"idea_{IDEAS.index(idea) + 1}"]["primary_horizon_bars"])
        if idea == "exhaustion":
            horizon = 3
        raw = np.flatnonzero(mask)
        extra_exit = 1 if idea == "exhaustion" and cohort == "early_policy" else 0
        chosen, invalid = select_nonoverlap(raw, horizon, dates, extra_exit=extra_exit)
        if idea == "exhaustion" and cohort == "early_policy":
            outputs.append(evaluate_events(df, chosen, product=product, idea=idea, cohort=cohort,
                                           horizon=horizon, setting=chart["setting"]))
            outputs.append(evaluate_events(df, chosen, product=product, idea=idea, cohort="wait_policy",
                                           horizon=horizon, setting=chart["setting"], wait=True))
        else:
            outputs.append(evaluate_events(df, chosen, product=product, idea=idea, cohort=cohort,
                                           horizon=horizon, setting=chart["setting"]))
        horizons = ([protocol["idea_1"]["secondary_horizon_bars"]] if idea == "pullback" else
                    protocol["idea_2"]["secondary_horizons_bars"] if idea == "exhaustion" else [])
        for alt_horizon in horizons:
            alt_extra = 1 if idea == "exhaustion" and cohort == "early_policy" else 0
            alt_indices, _ = select_nonoverlap(raw, alt_horizon, dates, extra_exit=alt_extra)
            secondary.append(evaluate_events(df, alt_indices, product=product, idea=idea, cohort=cohort,
                                             horizon=alt_horizon, setting=chart["setting"]))
            if idea == "exhaustion" and cohort == "early_policy":
                secondary.append(evaluate_events(df, alt_indices, product=product, idea=idea, cohort="wait_policy",
                                                 horizon=alt_horizon, setting=chart["setting"], wait=True))
        audits.append({"product": product, "idea": idea, "cohort": cohort, "raw_signals": int(len(raw)),
                       "incomplete_horizon": invalid, "nonoverlap_events": int(len(chosen))})
    events = pd.concat(outputs, ignore_index=True)
    events["split"] = split_labels(events["session_date"], protocol)
    events.to_parquet(out_dir / f"events_{product}.parquet", index=False)
    secondaries = pd.concat(secondary, ignore_index=True)
    secondaries["split"] = split_labels(secondaries["session_date"], protocol)
    secondaries.to_parquet(out_dir / f"secondary_{product}.parquet", index=False)
    return {"product": product, "rows_loaded": len(df), "session_dates": int(df["session_date_proxy"].nunique()),
            "quiet_thresholds_by_export_halfhour": thresholds, "event_rows": len(events),
            "secondary_event_rows": len(secondaries), "audit": audits}


def split_labels(dates: pd.Series, protocol: dict) -> pd.Series:
    out = pd.Series("excluded_gap", index=dates.index, dtype="object")
    for name, (start, end) in protocol["splits"].items():
        out.loc[dates.between(start, end)] = name
    return out


def bootstrap_contrast(candidate: pd.DataFrame, control: pd.DataFrame, *, reps: int, seed: int,
                       alpha: float) -> dict:
    dates = sorted(set(candidate["session_date"]) | set(control["session_date"]))
    if not dates:
        return {"difference_ticks": None, "lower": None, "upper": None, "n_sessions": 0}
    ca = candidate.assign(net=candidate["return_ticks"] - 2 * candidate["traded"].astype(int)).groupby("session_date")["net"].agg(["sum", "count"]).reindex(dates, fill_value=0)
    co = control.assign(net=control["return_ticks"] - 2 * control["traded"].astype(int)).groupby("session_date")["net"].agg(["sum", "count"]).reindex(dates, fill_value=0)
    xsum, xn = ca["sum"].to_numpy(float), ca["count"].to_numpy(float)
    ysum, yn = co["sum"].to_numpy(float), co["count"].to_numpy(float)
    if not xn.sum() or not yn.sum():
        return {"difference_ticks": None, "lower": None, "upper": None, "n_sessions": len(dates)}
    point = float(xsum.sum() / xn.sum() - ysum.sum() / yn.sum())
    gross = float(candidate["return_ticks"].mean() - control["return_ticks"].mean())
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(dates), size=(reps, len(dates)))
    cx = xn[samples].sum(axis=1)
    cy = yn[samples].sum(axis=1)
    valid = (cx > 0) & (cy > 0)
    draws = xsum[samples][valid].sum(axis=1) / cx[valid] - ysum[samples][valid].sum(axis=1) / cy[valid]
    if not len(draws):
        return {"difference_ticks": point, "gross_difference_ticks": gross, "lower": None, "upper": None, "n_sessions": len(dates)}
    return {"difference_ticks": point, "gross_difference_ticks": gross, "lower": float(np.quantile(draws, alpha / 2)),
            "upper": float(np.quantile(draws, 1 - alpha / 2)), "n_sessions": len(dates),
            "valid_bootstrap_replicates": int(len(draws))}


def summarize_events(events: pd.DataFrame, protocol: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    summaries = []
    contrasts = []
    metrics = {"schema_version": 1, "primary_contrasts": [], "candidate_screens": []}
    split_order = ("development", "validation", "final", "all")
    for product in protocol["primary_charts"]:
        product_events = events.loc[events["product"] == product]
        for idea in IDEAS:
            subset = product_events.loc[product_events["idea"] == idea]
            candidate_name, control_name, horizon = PRIMARY[idea]
            for split in split_order:
                frame = subset if split == "all" else subset.loc[subset["split"] == split]
                for cohort, group in frame.groupby("cohort"):
                    vals = group["return_ticks"].to_numpy(float)
                    traded = group["traded"].to_numpy(bool)
                    losses = vals[vals < 0]
                    daily = group.assign(net=group["return_ticks"] - 2 * group["traded"].astype(int)).groupby("session_date")["net"].sum().sort_values(ascending=False)
                    top = int(np.ceil(len(daily) * .01)) if len(daily) else 0
                    remove = set(daily.index[:top])
                    trim = group.loc[~group["session_date"].isin(remove)]
                    trim_net = float((trim["return_ticks"] - 2 * trim["traded"].astype(int)).mean()) if len(trim) else None
                    summaries.append({"product": product, "idea": idea, "cohort": cohort, "split": split,
                                      "horizon_bars": horizon, "opportunities": len(group), "trades": int(traded.sum()),
                                      "sessions": group["session_date"].nunique(),
                                      "mean_ticks": float(vals.mean()) if len(vals) else None,
                                      "median_ticks": float(np.median(vals)) if len(vals) else None,
                                      "p01_ticks": float(np.quantile(vals, .01)) if len(vals) else None,
                                      "p05_ticks": float(np.quantile(vals, .05)) if len(vals) else None,
                                      "loss_rate": float((vals < 0).mean()) if len(vals) else None,
                                      "mean_loss_ticks": float(losses.mean()) if len(losses) else None,
                                      "mean_adverse_ticks": float(group["adverse_ticks"].mean()) if traded.any() else None,
                                      "mean_delayed_ticks": float(group["delay_return_ticks"].mean()) if group["delay_return_ticks"].notna().any() else None,
                                      "mean_net_1_ticks": float((vals - 1 * traded).mean()) if len(vals) else None,
                                      "mean_net_2_ticks": float((vals - 2 * traded).mean()) if len(vals) else None,
                                      "mean_net_4_ticks": float((vals - 4 * traded).mean()) if len(vals) else None,
                                      "break_even_cost_ticks_per_trade": float(vals.sum() / traded.sum()) if traded.any() else None,
                                      "mean_net_2_without_top_1pct_sessions": trim_net,
                                      "opening_hour_opportunities": int(group["opening_hour"].sum())})
                c = frame.loc[frame["cohort"] == candidate_name]
                b = frame.loc[frame["cohort"] == control_name]
                result = bootstrap_contrast(c, b, reps=protocol["bootstrap_replicates"],
                                            seed=protocol["bootstrap_seed"] + 100 * list(protocol["primary_charts"]).index(product) + 10 * IDEAS.index(idea) + split_order.index(split),
                                            alpha=protocol["bonferroni_alpha"] if split == "all" else .05)
                record = {"product": product, "idea": idea, "split": split,
                          "candidate": candidate_name, "control": control_name,
                          "ci_level": 1 - (protocol["bonferroni_alpha"] if split == "all" else .05), **result}
                contrasts.append(record)
                if split == "all":
                    metrics["primary_contrasts"].append(record)
    summary_df = pd.DataFrame(summaries)
    contrast_df = pd.DataFrame(contrasts)
    for product in protocol["primary_charts"]:
        for idea in IDEAS:
            cname = PRIMARY[idea][0]
            rows = summary_df.loc[(summary_df["product"] == product) & (summary_df["idea"] == idea) & (summary_df["cohort"] == cname)]
            validation = rows.loc[rows["split"] == "validation"]
            final = rows.loc[rows["split"] == "final"]
            compare = contrast_df.loc[(contrast_df["product"] == product) & (contrast_df["idea"] == idea)]
            good = len(validation) == 1 and len(final) == 1
            if good:
                for name, frame in (("validation", validation), ("final", final)):
                    net = frame.iloc[0]["mean_net_2_ticks"]
                    contrast = compare.loc[compare["split"] == name].iloc[0]["difference_ticks"]
                    good &= pd.notna(net) and net > 0 and pd.notna(contrast) and contrast > 0
                net_trim = rows.loc[rows["split"] == "all"].iloc[0]["mean_net_2_without_top_1pct_sessions"]
                good &= pd.notna(net_trim) and net_trim > 0
            all_contrast = compare.loc[compare["split"] == "all"].iloc[0]
            familywise_positive = pd.notna(all_contrast["lower"]) and all_contrast["lower"] > 0
            metrics["candidate_screens"].append({"product": product, "idea": idea,
                                                  "later_blocks_and_concentration_pass": bool(good),
                                                  "familywise_interval_positive": bool(familywise_positive),
                                                  "provisional_candidate": bool(good and familywise_positive)})
    return summary_df, contrast_df, metrics


def barrier_bounds(events: pd.DataFrame, df: pd.DataFrame, setting: int, stops: list[int]) -> pd.DataFrame:
    subset = events.loc[(events["idea"] == "pullback") & (events["cohort"] == "extreme_break")]
    o = df["open_tick"].to_numpy()
    h = df["high_tick"].to_numpy()
    l = df["low_tick"].to_numpy()
    result = []
    for stop_units in stops:
        lower = []
        upper = []
        ambiguous = 0
        stop = stop_units * setting
        target = setting
        for row in subset.itertuples(index=False):
            j = row.signal_index + 1
            direction = row.direction
            favorable = h[j] - o[j] if direction > 0 else o[j] - l[j]
            adverse = o[j] - l[j] if direction > 0 else h[j] - o[j]
            target_hit = favorable >= target
            stop_hit = adverse >= stop
            if target_hit and stop_hit:
                ambiguous += 1
                lower.append(-stop)
                upper.append(target)
            elif target_hit:
                lower.append(target)
                upper.append(target)
            elif stop_hit:
                lower.append(-stop)
                upper.append(-stop)
            else:
                lower.append(row.return_ticks)
                upper.append(row.return_ticks)
        result.append({"product": subset["product"].iloc[0] if len(subset) else None,
                       "stop_units": stop_units, "target_units": 1, "events": len(subset),
                       "ambiguous_both_hit": ambiguous,
                       "mean_lower_ticks": float(np.mean(lower)) if lower else None,
                       "mean_upper_ticks": float(np.mean(upper)) if upper else None})
    return pd.DataFrame(result)
