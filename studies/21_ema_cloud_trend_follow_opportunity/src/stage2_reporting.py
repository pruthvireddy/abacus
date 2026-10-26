"""Private Stage 2 presentation from saved evidence only.

Selection definitions precede historical scoring. Raster rendering imports are
lazy, so the locked numerical suite does not need the separately inventoried
existing plotting dependencies. Narada receives explicit bounded projections.
"""
from __future__ import annotations

import csv
import html
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .stage2_contract import TABLES, STUDY_ID, BASELINE_RUN_ID, PRIMARY_FAMILY_ID
from .reporting import (sha256, save_json, read_csv, project_table, project_download,
                        _column, _html_table, _figure_environment)

KINDS = ("high_adverse", "rejected", "censored", "unresolved", "same_bar", "different_time")
NY = "America/New_York"
QUALIFICATIONS = ("Signals opened in New York 2018–2020 only; 2017 is causal warmup and later outcomes remain reserved. "
    "All cells use a five-minute EMA20/50 cloud, inclusive widths ES 2.4, GC 2, NQ 10 points, and independent selected-boundary states. "
    "Five-minute candles use the current completed cloud; three-minute candles use the latest scheduled completed five-minute cloud at open. "
    "This difference changes feature staleness as well as candle aggregation. Missing latest slots invalidate features immediately. "
    "The reference is unadjusted confirmed signal close, and the signal candle is excluded. Overlapping H15 observations are retained. "
    "H15 spans 45 active minutes for 3m and 75 for 5m; 60/150 active-minute and uninterrupted views are secondary. "
    "MFE/MAE and signed terminal movement describe price paths, not executable profits, fills, stops or targets. "
    "Modeled completion is available_at; original vendor receipt and mapping arrival evidence are absent. "
    "Uncertified holiday/early-close sessions are unusable and reset features. Missing minutes cannot reliably distinguish no trades from source loss. "
    "Published input bytes and inherited definitions are checked; original raw reconstruction, native TradingView equivalence and off-device backup remain uncertified. "
    "Earlier Abacus work inspected some later history, so reserved periods are not pristine market holdouts.")
METHODS = ("The six primary comparisons are pooled-direction H15 event-weighted fast-minus-slow mean signed terminal movement in each product’s raw points. "
    "The branches use the same eligible bar/feature/calendar roster and retain their different accepted timestamps. These are observational population comparisons. "
    "Circular calendar-week blocks share sampled weeks across branches and cells, with 157 Monday weeks from 2018-01-01 through 2020-12-28, "
    "10,000 replicates and seed 20261010. Four-week blocks are primary; one/eight-week blocks are sensitivities. "
    "Pointwise intervals have nominal 95% confidence; Bonferroni intervals target nominal 95% familywise confidence for these six primary contrasts and use exact tails .05/12 and 1−.05/12, "
    "equivalent to 99.1666667% marginal coverage. Other sides, units, sessions, metrics and horizons are descriptive. "
    "Undefined draws remain explicit; a zero-event week has no invented outcome mean. Session balancing first averages whole contributing sessions and assigns each "
    "to its trading-date Monday week. Quantiles interpolate at p(n−1). Terminal signs use strict zero; MFE>MAE ties use 1e−10×max(1,MFE,MAE). "
    "Cohorts below 100 evaluable events or 30 contributing sessions are sparse. Changing readiness and early GC support limit pooled stability claims.")
EPISODE_TEXT = ("Geometry, accepted membership, union and episode pairing describe different populations. Geometry can touch both boundaries while only one stream accepts. "
    "A same-bar accepted dual has one union observation and exactly equal reference/ATR/forward paths. Different timestamps remain separate observations. "
    "The descriptive union has no combined position policy. Shared geometric episodes start on strict full-cloud departure, retain consecutive departures, "
    "and restart at a departure after any non-departure; resets terminate them. Only the first accepted event of each stream is paired. Warmup first events are retained "
    "and never replaced with later development counterparts. Later slow geometry and later accepted slow signal are separate retrospective descriptors. "
    "No later contact is false only after an observed new departure; absent contacts at resets or the endpoint remain unresolved. These labels never filter a fast signal.")


def _present(value):
    return value is not None and pd.notna(value)


def _scope(frame):
    if frame.empty:
        return frame
    year = pd.to_datetime(frame.timestamp, utc=True).dt.tz_convert(NY).dt.year
    return frame.loc[year.between(2018, 2020)]


def select_examples(technical, events, outcomes, pairs=None):
    """Six deterministic H15 classes per cell; absent classes stay unavailable."""
    technical, events = _scope(technical), _scope(events)
    primary = outcomes.loc[outcomes.horizon.eq(15)].copy()
    pairs = pd.DataFrame() if pairs is None else pairs
    lookup = {r["event_id"]: r for r in events.to_dict("records")}
    results = []
    cells = sorted(set((r.product, int(r.interval_minutes)) for r in technical[["product", "interval_minutes"]].itertuples(index=False)))
    for product, interval in cells:
        tech = technical[(technical["product"] == product) & (technical.interval_minutes == interval)]
        path = primary[(primary["product"] == product) & (primary.interval_minutes == interval)]
        pp = pairs[(pairs["product"] == product) & (pairs.interval_minutes == interval)] if not pairs.empty else pairs
        for kind in KINDS:
            chosen, second, pair = None, None, None
            if kind == "high_adverse":
                eligible = path[path.status == "completed"]
                if len(eligible):
                    chosen = eligible.sort_values(["mae", "timestamp", "event_id"], ascending=[False, True, True], kind="stable").iloc[0].to_dict()
            elif kind == "censored":
                eligible = path[path.status == "censored"]
                if len(eligible):
                    chosen = eligible.sort_values(["timestamp", "event_id"], kind="stable").iloc[0].to_dict()
            elif kind == "rejected":
                eligible = tech[tech.technical_candidate.fillna(False) & ~tech.accepted.fillna(False)]
                if len(eligible):
                    chosen = eligible.sort_values(["timestamp", "touch_mode", "signal_idx"], kind="stable").iloc[0].to_dict()
            elif not pp.empty:
                if kind == "unresolved":
                    eligible = pp[pp.first_fast_in_development.fillna(False) & pp.strictly_later_slow_contact.isna() & pp.same_bar_slow_contact.eq(False)]
                elif kind == "same_bar":
                    eligible = pp[pp.pair_in_development.fillna(False) & pp.pair_relation.eq("same_bar")]
                else:
                    eligible = pp[pp.pair_in_development.fillna(False) & pp.pair_relation.isin(["fast_before_slow", "slow_before_fast"])]
                candidates = []
                for p in eligible.to_dict("records"):
                    ids = [p.get("first_fast_event_id")]
                    if kind != "unresolved":
                        ids.append(p.get("first_slow_event_id"))
                    selected = sorted((lookup[x] for x in ids if x in lookup), key=lambda r: (pd.Timestamp(r["timestamp"]), r["event_id"]))
                    if len(selected) == (1 if kind == "unresolved" else 2):
                        candidates.append((selected[0]["timestamp"], selected[0]["event_id"], selected[-1]["event_id"], p["shared_episode_id"], p, selected))
                if candidates:
                    best = min(candidates, key=lambda x: x[:4])
                    pair, selected = best[4:]
                    chosen, second = selected[0], selected[-1] if len(selected) == 2 else None
            identity = f"S2-T06|{product}|{interval}|{kind}"
            row = dict(row_id=identity, example_id=identity, stage=2, product=product, interval_minutes=interval,
                kind=kind, horizon=15, selection_status="selected" if chosen else "unavailable", event_id=None,
                paired_event_id=None, timestamp=None, signal_idx=None, touch_mode=None, selected_ema=None,
                reference_price=None, shared_episode_id=None, pair_relation=None, end_reason=None,
                suppression_reason=None, status=None, censor_reason=None, mfe=None, mae=None, terminal_delta=None)
            if chosen:
                for key in ("event_id", "timestamp", "signal_idx", "touch_mode", "selected_ema", "shared_episode_id", "suppression_reason", "status", "censor_reason", "mfe", "mae", "terminal_delta"):
                    row[key] = chosen.get(key)
                row["reference_price"] = chosen.get("reference_price", chosen.get("close"))
                row["selected_ema"] = row["selected_ema"] or ("ema20" if row["touch_mode"] == "fast" else "ema50")
                if second:
                    row["paired_event_id"] = second["event_id"]
                if pair:
                    row.update(shared_episode_id=pair["shared_episode_id"], pair_relation=pair["pair_relation"], end_reason=pair["end_reason"])
            results.append(row)
    return pd.DataFrame(results)


def _read_role(records, role, product, interval):
    frames = []
    for record in records:
        if record["role"] == role and record["product"] == product and int(record["interval_minutes"]) == interval:
            path = Path(record["path"])
            if sha256(path) != record["sha256"] or path.stat().st_size != record["bytes"]:
                raise ValueError("saved example input bytes changed")
            frames.append(pd.read_parquet(path))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def prepare_examples(stage):
    """Save T06 and exact capped candle segments before presentation rendering."""
    stage = Path(stage)
    records = json.loads((stage / "events.manifest.json").read_text())["records"]
    target = stage / "tables" / TABLES["S2-T06"]
    path_target = stage / "tables/selected-example-paths.parquet"
    if target.exists() or path_target.exists():
        raise ValueError("saved example overwrite refused")
    all_examples, saved_paths = [], []
    for product in ("ES", "GC", "NQ"):
        for interval in (3, 5):
            technical = _read_role(records, "technical", product, interval)
            events = _read_role(records, "events", product, interval)
            outcomes = _read_role(records, "outcomes", product, interval)
            pairs = _read_role(records, "pairs", product, interval)
            examples = select_examples(technical, events, outcomes, pairs)
            all_examples.append(examples)
            lookup = events.set_index("event_id", verify_integrity=True)
            for example in examples.to_dict("records"):
                if example["selection_status"] != "selected":
                    continue
                selected = [example]
                if _present(example["paired_event_id"]):
                    selected.append(lookup.loc[example["paired_event_id"]].to_dict() | {"event_id": example["paired_event_id"]})
                for segment, event in enumerate(selected):
                    branch = event["touch_mode"]
                    stream = technical[technical.touch_mode == branch]
                    index = int(event["signal_idx"])
                    window = _scope(stream[stream.signal_idx.between(index - 10, index + 15)])
                    for item in window.itertuples(index=False):
                        source = item._asdict()
                        row = {key: source.get(key) for key in ("product", "interval_minutes", "timestamp", "available_at",
                            "open", "high", "low", "close", "ema20", "ema50", "usable", "feature_valid", "contract", "direction")}
                        row.update(example_id=example["example_id"], segment_id=segment, relative_slot=int(source["signal_idx"]) - index,
                            original_signal_idx=int(source["signal_idx"]), event_id=event.get("event_id"), touch_mode=branch,
                            selected_ema="ema20" if branch == "fast" else "ema50", reference_price=event.get("reference_price", event.get("close")),
                            is_signal=int(source["signal_idx"]) == index, shared_episode_id=example.get("shared_episode_id"))
                        row["row_id"] = f"{example['example_id']}|{segment}|{row['original_signal_idx']}"
                        saved_paths.append(row)
            del technical, events, outcomes, pairs
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(all_examples, ignore_index=True).to_csv(target, index=False, float_format="%.17g")
    paths = pd.DataFrame(saved_paths)
    paths.to_parquet(path_target, index=False)
    return {"status": "prepared", "examples": {"path": str(target), "sha256": sha256(target), "rows": 36},
        "paths": {"path": str(path_target), "sha256": sha256(path_target), "rows": len(paths)},
        "scope": "Six prespecified classes per cell, at most26 bars per event segment, development candles only."}


def render_figures(stage, paths):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    stage = Path(stage)
    figures = stage / "figures"
    figures.mkdir(exist_ok=True)
    score = pd.read_csv(paths["S2-T02"])
    score = score[(score.direction == "All") & (score.unit == "points") & (score.support == "all")]
    quantiles = pd.read_csv(paths["S2-T03"])
    quantiles = quantiles[(quantiles.direction == "All") & (quantiles.unit == "points") & (quantiles.horizon == 15)]
    frequency = pd.read_csv(paths["S2-T10"])
    frequency = frequency[(frequency.direction == "All") & (frequency.summary_kind == "frequency")]
    annual = pd.read_csv(paths["S2-T04"])
    annual = annual[(annual.direction == "All") & (annual.unit == "points") & (annual.period_kind == "year")]
    coverage = pd.read_csv(paths["S2-T00"])
    coverage = coverage[coverage.year.between(2018, 2020)]
    examples = pd.read_csv(paths["S2-T06"])
    saved_path = stage / "tables/selected-example-paths.parquet"
    candles = pd.read_parquet(saved_path)
    cells = [(p, i) for p in ("ES", "GC", "NQ") for i in (3, 5)]
    colors = {"fast": "#1764a1", "slow": "#cf7b1d"}
    sections, bindings = [], []
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

    def bind(path, frame, columns, selector):
        item = dict(source_artifact=Path(path).relative_to(stage).as_posix(), source_sha256=sha256(path),
            selector=selector, columns=columns)
        if "row_id" in frame:
            item["row_ids"] = frame.row_id.astype(str).tolist()
        if Path(path).suffix == ".csv":
            item["data_rows_1_based"] = [int(i) + 1 for i in frame.index]
        return item

    def finish(fig, filename, title, caption, alt, sources):
        target = figures / filename
        fig.tight_layout(rect=(0, 0.03, 1, .97))
        fig.savefig(target, dpi=110, pil_kwargs={"optimize": True})
        plt.close(fig)
        if target.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("figure exceeds PNG budget")
        identity = "figure-" + target.stem.replace("_", "-")
        sections.append(dict(id=identity, kind="figure", title=title, path="figures/" + filename, alt=alt, caption=caption))
        bindings.append(dict(figure=identity, path="figures/" + filename, sha256=sha256(target), sources=sources))

    fig, axes = plt.subplots(3, 2, figsize=(12, 11))
    metric_colors = {"mfe": "#1b8d72", "mae": "#bb4b4b", "terminal_delta": "#576378"}
    for ax, (p, i) in zip(axes.flat, cells):
        group = score[(score["product"] == p) & (score.interval_minutes == i)]
        for branch in ("fast", "slow"):
            part = group[group.touch_mode == branch].sort_values("horizon_minutes")
            for metric in ("mfe", "mae", "terminal_delta"):
                ax.plot(part.horizon_minutes, part["mean_" + metric], color=metric_colors[metric], linestyle="-" if branch == "fast" else "--", label=branch + " " + metric)
        ax.axhline(0, color="#9da8b7", lw=.6)
        ax.set(title=f"{p} {i}m", xlabel="Active minutes (scheduled H×candle minutes)", ylabel=f"Mean movement ({p} points)")
        ax.grid(alpha=.15)
    axes.flat[0].legend(fontsize=8, ncol=2)
    finish(fig, "horizons.png", "Horizon responses of independent streams", "All completed evaluable paths, pooled sides, event means. H15 is 45/75 active minutes; secondary horizons describe duration rather than a selected exit.",
        "Six product/candle panels of fast and slow MFE, MAE and signed terminal mean versus active minutes.",
        [bind(paths["S2-T02"], score, ["horizon_minutes", "mean_mfe", "mean_mae", "mean_terminal_delta"], {"direction": ["All"], "unit": ["points"], "support": ["all"]})])

    fig, axes = plt.subplots(3, 2, figsize=(12, 11))
    for p in ("ES", "GC", "NQ"):
        pg = quantiles[(quantiles["product"] == p) & quantiles.metric.isin(["mfe", "mae"]) & quantiles["quantile"].le(.95)]
        limit = float(pg.value.max()) * 1.08 if pg.value.notna().any() else 1
        for i in (3, 5):
            ax = axes[ ("ES", "GC", "NQ").index(p), (3, 5).index(i)]
            group = pg[pg.interval_minutes == i]
            for branch in ("fast", "slow"):
                for metric in ("mfe", "mae"):
                    part = group[(group.touch_mode == branch) & (group.metric == metric)].sort_values("quantile")
                    ax.plot(part["quantile"] * 100, part.value, color=colors[branch], linestyle="-" if metric == "mfe" else "--", label=branch + " " + metric)
            ax.set(title=f"{p} {i}m H15", ylim=(0, limit), xlabel="Percentile cutoff", ylabel=f"Excursion ({p} points)")
            ax.grid(alpha=.15)
    axes.flat[0].legend(fontsize=8, ncol=2)
    selected = quantiles[quantiles.metric.isin(["mfe", "mae"]) & quantiles["quantile"].le(.95)]
    finish(fig, "distributions.png", "H15 adverse and favorable excursion distributions", "A common vertical scale is used across both candle intervals within each product. Raw points are never combined across ES, GC and NQ. Curves show percentile cutoffs, not tail averages.",
        "Six product/candle panels comparing fast and slow MFE and MAE quantiles through P95 on a common product scale.",
        [bind(paths["S2-T03"], selected, ["quantile", "value", "metric"], {"direction": ["All"], "unit": ["points"], "horizon": ["15"], "metric": ["mfe", "mae"]})])

    fig, axes = plt.subplots(3, 2, figsize=(12, 10))
    for ax, (p, i) in zip(axes.flat, cells):
        freq = frequency[(frequency["product"] == p) & (frequency.interval_minutes == i)].iloc[0]
        primary = score[(score["product"] == p) & (score.interval_minutes == i) & (score.horizon == 15)]
        for branch in ("fast", "slow"):
            row = primary[primary.touch_mode == branch].iloc[0]
            x, y = freq[branch + "_rate_per_1000"], row.mean_terminal_delta
            ax.scatter([x], [y], color=colors[branch], s=75, label=branch)
            ax.annotate(branch + f"; n={int(row.completed)}", (x, y), xytext=(5, 8), textcoords="offset points", fontsize=8)
        ax.axhline(0, color="#9da8b7", lw=.7)
        ax.set(title=f"{p} {i}m H15", xlabel="Accepted events per 1,000 common eligible slots", ylabel=f"Mean signed close ({p} points)")
        ax.margins(.35)
        ax.grid(alpha=.15)
    primary = score[score.horizon == 15]
    finish(fig, "frequency_quality.png", "Frequency and subsequent signed movement", "Frequency uses usable feature-valid signal slots; mean movement uses completed H15 events. These denominators differ. No linear frequency-quality relation or causal advantage is implied; uncertainty appears in the contrast table.",
        "Six product/candle panels showing fast and slow event frequency against completed H15 mean signed terminal movement.",
        [bind(paths["S2-T10"], frequency, ["fast_rate_per_1000", "slow_rate_per_1000"], {"direction": ["All"], "summary_kind": ["frequency"]}),
         bind(paths["S2-T02"], primary, ["completed", "mean_terminal_delta"], {"direction": ["All"], "unit": ["points"], "support": ["all"], "horizon": ["15"]})])

    fig, axes = plt.subplots(3, 2, figsize=(12, 11))
    for ax, (p, i) in zip(axes.flat, cells):
        group = annual[(annual["product"] == p) & (annual.interval_minutes == i)]
        for branch in ("fast", "slow"):
            part = group[group.touch_mode == branch].sort_values("period")
            ax.plot(part.period.astype(int), part.mean_terminal_delta, "o-", color=colors[branch], label=branch)
            for row in part.itertuples():
                ax.annotate(f"n={int(row.completed)}", (int(row.period), row.mean_terminal_delta), fontsize=7, xytext=(0, 5 if branch == "fast" else -13), textcoords="offset points")
        cov = coverage[(coverage["product"] == p) & (coverage.interval_minutes == i)].sort_values("year")
        right = ax.twinx()
        right.plot(cov.year, cov.ready_share, ":o", color="#909caa", markersize=3, label="eligible share")
        right.set(ylim=(0, 1), ylabel="Eligible/scheduled slots")
        ax.axhline(0, color="#9da8b7", lw=.6)
        ax.set(title=f"{p} {i}m H15", xticks=[2018, 2019, 2020], xlim=(2017.7, 2020.3), ylabel=f"Annual signed mean ({p} points)")
        ax.grid(alpha=.15)
    axes.flat[0].legend(fontsize=8)
    finish(fig, "calendar_coverage.png", "Annual movement and changing eligible coverage", "Annual event means and completed supports are descriptive. Dotted lines are common usable mapped-feature readiness shares. Zero events describe eligible observed support; unknown signal coverage cannot establish zero opportunities. Early GC counts are sparse.",
        "Six product/candle panels comparing annual fast and slow signed means, counts and common eligible readiness shares.",
        [bind(paths["S2-T04"], annual, ["period", "completed", "mean_terminal_delta"], {"direction": ["All"], "unit": ["points"], "period_kind": ["year"]}),
         bind(paths["S2-T00"], coverage, ["year", "ready_share"], {"split": ["development"]})])

    def draw_example(ax, example):
        if example.selection_status != "selected":
            ax.text(.5, .5, "Prespecified class unavailable", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            return
        frame = candles[candles.example_id == example.example_id]
        if example.kind == "same_bar":
            frame = frame[frame.segment_id == 0]
        for segment, part in frame.groupby("segment_id", sort=True):
            part = part.sort_values("relative_slot")
            x = part.relative_slot.to_numpy(float) + 40 * int(segment)
            for xx, row in zip(x, part.itertuples()):
                if all(math.isfinite(float(getattr(row, k))) for k in ("open", "high", "low", "close")):
                    color = "#4c8b78" if row.close >= row.open else "#b66462"
                    ax.vlines(xx, row.low, row.high, color=color, lw=.65)
                    ax.add_patch(Rectangle((xx - .32, min(row.open, row.close)), .64, max(abs(row.close - row.open), .002), facecolor=color, alpha=.8, linewidth=0))
            for metric, color in (("ema20", colors["fast"]), ("ema50", colors["slow"])):
                ax.plot(x, part[metric], color=color, lw=1)
            signal = part[part.is_signal]
            if len(signal):
                ax.scatter([40 * int(segment)], [signal.reference_price.iloc[0]], marker="x", color="#17233b", s=40, zorder=5)
                label = "fast + slow (same timestamp)" if example.kind == "same_bar" else str(signal.touch_mode.iloc[0])
                ax.text(40 * int(segment), signal.reference_price.iloc[0], " " + label, fontsize=7)
        if frame.segment_id.nunique() == 2:
            ax.axvspan(16, 29, color="#e9edf3", alpha=.9)
            ax.text(22.5, .02, "Separate capped windows", transform=ax.get_xaxis_transform(), rotation=90, fontsize=6, ha="center", va="bottom")
        ax.set_xticks([-10, 0, 15] + ([30, 40, 55] if frame.segment_id.nunique() == 2 else []))
        ax.tick_params(labelsize=7)
        ax.set_title(f"{example['product']} {int(example.interval_minutes)}m · {example.kind}\n{str(example.timestamp)[:16]} · {example.touch_mode}", fontsize=8)
        ax.grid(alpha=.12)

    for filename, kinds, title, caption in (("episodes.png", ("same_bar", "different_time"), "Prespecified same-bar and different-time episodes",
        "First accepted stream events only, both in development. Same-bar signals share one displayed window. Different-time order is retained, with separate −10/+15 scheduled-slot windows and omitted intervals labeled. Blue=EMA20; orange=EMA50. X marks confirmed-close references. Pairing is retrospective."),
        ("qualifying_examples.png", ("high_adverse", "rejected", "censored", "unresolved"), "Prespecified adverse, rejected, censored and unresolved cases",
        "Largest completed H15 MAE across streams and earliest remaining classes, using frozen timestamp/ID ties. No favorable replacement is allowed. Rejected cases have no forward score; interrupted absent slow contact remains unresolved. Blue=EMA20; orange=EMA50. X marks confirmed close; windows contain development candles only.")):
        fig, axes = plt.subplots(6, len(kinds), figsize=(6 * len(kinds), 18), squeeze=False)
        chosen = examples[examples.kind.isin(kinds)]
        for row_index, (p, i) in enumerate(cells):
            for column, kind in enumerate(kinds):
                example = chosen[(chosen["product"] == p) & (chosen.interval_minutes == i) & (chosen.kind == kind)].iloc[0]
                draw_example(axes[row_index, column], example)
        ids = chosen.example_id.astype(str).tolist()
        selected_candles = candles[candles.example_id.isin(ids)]
        finish(fig, filename, title, caption, f"{6 * len(kinds)} product/example panels with candle ranges, EMA20 and EMA50, and confirmed-close signal markers; unavailable classes labeled.",
            [bind(paths["S2-T06"], chosen, ["kind", "selection_status", "timestamp", "event_id", "paired_event_id", "end_reason"], {"kind": list(kinds)}),
             bind(saved_path, selected_candles, ["open", "high", "low", "close", "ema20", "ema50", "relative_slot", "segment_id", "reference_price", "is_signal"], {"example_id": ids})])
    if sum((stage / item["path"]).stat().st_size for item in sections) > 8 * 1024 * 1024:
        raise ValueError("total figure budget")
    save_json(stage / "figure-environment.json", _figure_environment())
    return sections, bindings


def primary_claim(point, family):
    def f(value):
        return "undefined" if value == "" else value
    low, high = family["ci_low"], family["ci_high"]
    qualifier = "familywise interval unavailable" if not low or not high else "familywise interval includes zero" if float(low) <= 0 <= float(high) else "familywise interval is entirely positive" if float(low) > 0 else "familywise interval is entirely negative"
    return (f"{point['product']} {point['interval_minutes']}m H15: fast-minus-slow mean signed terminal movement {f(point['estimate'])} points; "
        f"four-week pointwise 95% interval [{f(point['ci_low'])}, {f(point['ci_high'])}], "
        f"six-contrast familywise interval [{f(low)}, {f(high)}]; {qualifier}. "
        f"Fast: {point['fast_accepted']} accepted, {point['fast_completed']} completed, {point['fast_censored']} censored; "
        f"slow: {point['slow_accepted']} accepted, {point['slow_completed']} completed, {point['slow_censored']} censored. "
        f"Evidence rows {point['row_id']} and {family['row_id']}.")


def render_bundle(stage, run_id=None):
    """Render private report, offline HTML and bounded Narada 1.1 saved source."""
    stage = Path(stage)
    run_id = run_id or stage.name
    paths = {key: stage / "tables" / name for key, name in TABLES.items()}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise ValueError("essential saved report evidence absent: " + ", ".join(missing))
    _, contrast = read_csv(paths["S2-T08"])
    primary = [r for r in contrast if r["family_id"] == PRIMARY_FAMILY_ID and r["block_weeks"] == "4" and r["interval_type"] == "pointwise95"]
    families = {(r["product"], r["interval_minutes"]): r for r in contrast if r["family_id"] == PRIMARY_FAMILY_ID and r["block_weeks"] == "4" and r["interval_type"] == "bonferroni"}
    if len(primary) != 6 or len(families) != 6:
        raise ValueError("complete six primary contrast family required")
    claims, claim_bindings = [], []
    rows_by_id = {r["row_id"]: (i, r) for i, r in enumerate(contrast, 1)}
    for point in primary:
        family = families[(point["product"], point["interval_minutes"])]
        text = primary_claim(point, family)
        claims.append(text)
        claim_bindings.append(dict(claim=text, sources=[dict(source_artifact="tables/" + TABLES["S2-T08"], source_sha256=sha256(paths["S2-T08"]),
            data_row_1_based=rows_by_id[r["row_id"]][0], row_id=r["row_id"], source_raw={key: r[key] for key in
            ("product", "interval_minutes", "estimate", "ci_low", "ci_high", "fast_accepted", "fast_completed", "fast_censored", "slow_accepted", "slow_completed", "slow_censored")}) for r in (point, family)]))
    classification = [(float(families[(r["product"], r["interval_minutes"])]["ci_low"]), float(families[(r["product"], r["interval_minutes"])]["ci_high"])) for r in primary if families[(r["product"], r["interval_minutes"])]["ci_low"] and families[(r["product"], r["interval_minutes"])]["ci_high"]]
    headline = ("All six primary familywise intervals include zero; the prespecified comparison does not establish a pooled fast-versus-slow signed-terminal advantage." if len(classification) == 6 and all(lo <= 0 <= hi for lo, hi in classification) else
        "The six prespecified effects and their familywise intervals are shown individually below. Any interval excluding zero describes development population differences under the fixed rule, without causal or profitability interpretation.")
    sections = [dict(id="findings", kind="text", title="Primary development findings", body=headline + "\n\n" + "\n\n".join(claims)),
        dict(id="methods", kind="text", title="Fixed definitions and paired uncertainty", body=METHODS),
        dict(id="limitations", kind="text", title="Coverage, timing and evidence qualifications", body=QUALIFICATIONS)]
    bindings, downloads, download_bindings = [], [], []
    def table(key, identity, title, columns, selector, description, notes=()):
        rows, bound = project_table(paths[key], columns=columns, selector=selector, section=identity, source_artifact=paths[key].relative_to(stage).as_posix())
        if len(rows) > 100 or len(columns) > 12:
            raise ValueError("selected table budget")
        sections.append(dict(id=identity, kind="table", title=title, columns=columns, rows=rows, description=description, notes=list(notes)))
        bindings.extend(bound)
    def col(key, numeric=False, percent=False):
        return _column(key, numeric=numeric, percent=percent)
    table("S2-T02", "branch-primary", "Standalone H15 branch scorecards", [col("product"), col("interval_minutes", True), col("touch_mode"), col("accepted", True), col("completed", True), col("censored", True), col("contributing_sessions", True), col("mean_mfe", True), col("mean_mae", True), col("mean_terminal_delta", True), col("session_mean_terminal_delta", True), col("sparse_warning")],
        {"direction": ["All"], "unit": ["points"], "support": ["all"], "horizon": ["15"]}, "Pooled sides. Event and session means have different denominators. Raw points remain separate by product.")
    table("S2-T08", "primary-contrasts", "Six primary paired effects and block sensitivities", [col("product"), col("interval_minutes", True), col("block_weeks", True), col("interval_type"), col("estimate", True), col("ci_low", True), col("ci_high", True), col("undefined_draws", True), col("fast_evaluable", True), col("slow_evaluable", True)],
        {"family_id": [PRIMARY_FAMILY_ID], "block_weeks": ["1", "4", "8"], "interval_type": ["pointwise95", "bonferroni"]}, "Fast-minus-slow event-weighted H15 terminal means in raw points. Four-week blocks are primary; one/eight are sensitivities.", ["Bonferroni marginal coverage is 99.1666667%; pointwise coverage is 95%. Undefined resamples remain counted."])
    table("S2-T10", "frequency", "Opportunity frequency and deduplicated union", [col("product"), col("interval_minutes", True), col("fast_accepted", True), col("slow_accepted", True), col("both_accepted", True), col("union_accepted", True), col("incremental_vs_slow", True), col("eligible_slots", True), col("fast_rate_per_1000", True), col("slow_rate_per_1000", True)],
        {"direction": ["All"], "summary_kind": ["frequency"]}, "Union=fast+slow−same-bar dual. Incremental opportunities are fast-only accepted timestamps. Rates use the common usable feature-valid roster; no combined execution policy is tested.")
    table("S2-T07", "geometry", "Geometry and acceptance remain separate", [col("product"), col("interval_minutes", True), col("dimension"), col("category"), col("count", True), col("eligible_count", True), col("scheduled_slots", True), col("eligible_slots", True)],
        {"direction": ["All"], "period_kind": ["all"]}, "Five geometric classes include undefined candles. Four accepted-membership classes reflect independent arm/gateway decisions.")
    table("S2-T09", "pairing", "Retrospective first-event episode membership", [col("product"), col("interval_minutes", True), col("summary_kind"), col("category"), col("count", True), col("episodes", True), col("descriptor_eligible", True), col("share", percent=True)],
        {"direction": ["All"], "summary_kind": ["pair_relation", "strictly_later_slow_contact"]}, "Episode relation counts include causal warmup counterparts where present; later-contact denominators include scoped first fast events only. Null absent contact is unresolved.")
    table("S2-T04", "annual", "Annual support and movement under the fixed rule", [col("product"), col("interval_minutes", True), col("touch_mode"), col("period"), col("completed", True), col("contributing_sessions", True), col("mean_mfe", True), col("mean_mae", True), col("mean_terminal_delta", True), col("sparse_warning"), col("eligible_slots", True)],
        {"direction": ["All"], "unit": ["points"], "period_kind": ["year"]}, "No annual, side or hour was selected. Small counts and changing mapped readiness limit stability interpretation.")
    sections.append(dict(id="episodes-method", kind="text", title="Overlap and episode interpretation", body=EPISODE_TEXT))
    figures, figure_bindings = render_figures(stage, paths)
    sections.extend(figures)
    baseline_text = (f"Slow parity is checked against the immutable Stage 1 run {BASELINE_RUN_ID}, protocol 0.1.0-stage1.2. "
        "Its pooled H15 four-week terminal intervals included zero, and mean adverse excursion exceeded mean favorable excursion in all six cells. "
        "Negative side/session findings and block sensitivities remain retained; Stage 2 does not replace that record. "
        "The baseline input release is same_contract_ema_cloud 1.0.0. Current maintained Stage 1 verifier/caption repairs are distinct from its frozen executed source. "
        "The slow scientific parity gate precedes fast outcome execution. Stage 3 requires a separate frozen instruction; later outcomes and all gateway optimization remain reserved.")
    sections.append(dict(id="baseline", kind="text", title="Preserved baseline and next-stage boundary", body=baseline_text))
    sections.append(dict(id="saved-evidence", kind="text", title="Detailed evidence and verification", body="Full saved S2-T00–S2-T10 tables, cohort/duration uncertainty, complete weekly sufficient statistics and episode metrics remain in the private research run. Numerical fixtures, exact slow parity, full scalar/path/table uncertainty reconciliation, input bytes and selected-source transfer are separately recorded. Publication validation checks selected content and assets; it does not establish research correctness."))
    download_specs = [
        ("S2-T02", "primary-branches", ["row_id", "product", "interval_minutes", "touch_mode", "accepted", "completed", "censored", "contributing_sessions", "mean_mfe", "mean_mae", "mean_terminal_delta", "session_mean_terminal_delta", "favorable_share", "mfe_gt_mae_share", "sparse_warning"], {"direction": ["All"], "unit": ["points"], "support": ["all"], "horizon": ["15"]}),
        ("S2-T08", "primary-effects", ["row_id", "product", "interval_minutes", "block_weeks", "interval_type", "estimate", "ci_low", "ci_high", "coverage", "fast_accepted", "fast_completed", "fast_censored", "slow_accepted", "slow_completed", "slow_censored", "defined_draws", "undefined_draws", "sparse_warning"], {"family_id": [PRIMARY_FAMILY_ID], "block_weeks": ["1", "4", "8"], "interval_type": ["pointwise95", "bonferroni"]}),
        ("S2-T04", "annual-side-session", ["row_id", "product", "interval_minutes", "direction", "touch_mode", "period_kind", "period", "completed", "contributing_sessions", "mean_mfe", "mean_mae", "mean_terminal_delta", "session_mean_terminal_delta", "eligible_slots", "sparse_warning"], {"unit": ["points"], "period_kind": ["year", "time_stratum"]}),
        ("S2-T09", "episode-diagnostics", ["row_id", "product", "interval_minutes", "direction", "summary_kind", "category", "count", "episodes", "descriptor_eligible", "share", "scoped_pairs", "mean_difference", "median_difference", "p10_difference", "p90_difference"], {"direction": ["All"], "summary_kind": ["pair_relation", "pair_scope", "same_bar_slow_contact", "strictly_later_slow_contact", "strictly_later_slow_signal", "pair_timing_reference"]})]
    for key, identity, columns, selector in download_specs:
        declaration, binding = project_download(stage, paths[key], columns=columns, selector=selector, run_id=run_id, download_id=identity,
            filename=identity + ".csv", description=identity.replace("-", " ").title())
        declaration.update(population="Fixed-rule independent fast/slow 2018–2020 development cohorts",
            units="Product-specific raw points, counts, shares and minutes as named; blanks retain undefined values.")
        downloads.append(declaration)
        download_bindings.append(binding)
    publication = dict(schemaVersion="1.1", id="ema-cloud-stage2-" + run_id.lower().replace("_", "-"),
        title="20/50 5minEMA Cloud Trend Follow Opportunity Study — Stage 2", summary=headline,
        publishedAt=datetime.strptime(run_id[:16], "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%dT%H:%M:%SZ"), source=dict(producer="Sahadeva", runId=run_id),
        sections=sections, downloads=downloads)
    (stage / "publication.json").write_text(json.dumps(publication, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    if (stage / "publication.json").stat().st_size > 96 * 1024:
        raise ValueError("private publication source exceeds96KiB")
    baseline_dir = Path(__file__).resolve().parents[3] / "runs" / STUDY_ID / BASELINE_RUN_ID
    baseline_sources = [dict(run_id=BASELINE_RUN_ID, path=str(baseline_dir / p), sha256=sha256(baseline_dir / p)) for p in
        ("manifest.json", "protocol.md", "config.json", "report.md", "advice.md", "tables/S1-T02_horizon_scorecard.csv", "tables/S1-bootstrap.csv")]
    save_json(stage / "source-bindings.json", dict(schema_version=2, run_id=run_id, publication_sha256=sha256(stage / "publication.json"), cells=bindings,
        downloads=download_bindings, claims=claim_bindings, figures=figure_bindings, baseline_sources=baseline_sources,
        qualification="Private baseline bindings are cross-run locators; no unsupported cross-run saved-artifact reference is exported."))
    md = ["# " + publication["title"], f"Run {run_id} · 2018–2020 development only"]
    body = ["<h1>" + html.escape(publication["title"]) + "</h1>", "<p>Run " + html.escape(run_id) + " · 2018–2020 development only</p>"]
    for section in sections:
        md.extend(["", "## " + section["title"], ""])
        body.append('<section id="' + section["id"] + '"><h2>' + html.escape(section["title"]) + "</h2>")
        if section["kind"] == "text":
            md.append(section["body"])
            body.extend("<p>" + html.escape(p) + "</p>" for p in section["body"].split("\n\n"))
        elif section["kind"] == "figure":
            md.extend([f"![{section['alt']}]({section['path']})", section["caption"]])
            body.append('<figure><img src="' + section["path"] + '" alt="' + html.escape(section["alt"], quote=True) + '"><figcaption>' + html.escape(section["caption"]) + "</figcaption></figure>")
        else:
            md.append(section["description"])
            keys = [c["key"] for c in section["columns"]]
            md.extend(["", "| " + " | ".join(c["label"] for c in section["columns"]) + " |", "| " + " | ".join("---" for _ in keys) + " |"])
            md.extend("| " + " | ".join("undefined" if r[k] is None else str(r[k]) for k in keys) + " |" for r in section["rows"])
            body.extend(["<p>" + html.escape(section["description"]) + "</p>", _html_table(section["columns"], section["rows"])])
        body.append("</section>")
    md.extend(["", "## Exact saved evidence", ""] + [f"- [{key}](tables/{name})" for key, name in TABLES.items()] +
        ["- [Cohort uncertainty](tables/S2-bootstrap.csv)", "- [Duration comparisons](tables/S2-duration-comparisons.csv)", "- [Weekly sufficient statistics](tables/S2-calendar-sufficient-statistics.csv)", "- [First-pair metrics](tables/S2-episode-pair-metrics.csv)"])
    body.append("<h2>Exact saved evidence</h2><ul>" + "".join('<li><a href="tables/' + name + '">' + key + "</a></li>" for key, name in TABLES.items()) + "</ul>")
    (stage / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (stage / "report.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EMA Cloud Stage 2</title><style>body{font:16px/1.55 system-ui;max-width:1250px;margin:auto;padding:30px;color:#17233b}h1{line-height:1.2}h2{margin-top:2em}.scroll{overflow-x:auto}table{border-collapse:collapse;font-size:13px;min-width:700px}th,td{padding:7px 10px;border-bottom:1px solid #dde3ec;text-align:left}th{background:#edf2f8}img{max-width:100%;height:auto}figcaption{font-size:14px;color:#526076}a{color:#1c55b2}</style><body>' + "\n".join(body) + "</body></html>\n", encoding="utf-8")
    (stage / "advice.md").write_text("# Stage 2 development advice\n\nRun " + run_id + " · baseline " + BASELINE_RUN_ID + "\n\n" + headline + "\n\n" + "\n\n".join(claims) + "\n\n" + EPISODE_TEXT + "\n\n" + QUALIFICATIONS + "\n\nNo side, hour, horizon or gateway was selected. Preserve both fixed branches as baselines for separately authorized Stage 3.\n", encoding="utf-8")
    return dict(status="rendered", publication_sha256=sha256(stage / "publication.json"), bindings_sha256=sha256(stage / "source-bindings.json"),
        sections=len(sections), figures=len(figures), claims=len(claims), downloads=len(downloads))
