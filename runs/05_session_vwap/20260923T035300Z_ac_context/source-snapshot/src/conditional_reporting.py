"""Tables and offline report for prespecified A/C context questions."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd


def read_context(stage: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    files = sorted((stage / "context").glob("context_*.parquet"))
    reentry_files = sorted((stage / "context").glob("reentry_*.parquet"))
    if len(files) != 23 or len(reentry_files) != 23:
        raise ValueError("expected 23 context and re-entry partitions")
    context = pd.concat((pd.read_parquet(file) for file in files), ignore_index=True)
    reentry = pd.concat((pd.read_parquet(file) for file in reentry_files), ignore_index=True)
    if context.event_id.duplicated().any() or reentry.original_event_id.duplicated().any():
        raise ValueError("duplicate derived event ID")
    return context, reentry


def _sigma_bin(values: pd.Series, boundaries: tuple[float, float],
               labels: tuple[str, str, str]) -> np.ndarray:
    return np.select([values.isna(), values < boundaries[0], values < boundaries[1]],
                     ["unavailable", labels[0], labels[1]], default=labels[2])


def add_bins(context: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    context = context.copy()
    context["direction_label"] = np.where(context.direction > 0, "long", "short")
    context["anchor_age_bin"] = np.select(
        [context.anchor_age_minutes < 60, context.anchor_age_minutes < 120],
        ["30-59", "60-119"], default="120+")
    context["a_exit_strength_bin"] = _sigma_bin(
        context.a_exit_strength_sigma, (2.25, 2.75), ("2-2.25", "2.25-2.75", "2.75+"))
    context["a_trend_bin"] = np.select(
        [context.a_prior30_trend_sigma.isna(), context.a_prior30_trend_sigma <= 0,
         context.a_prior30_trend_sigma < 1],
        ["unavailable", "nonpositive", "0-1",], default="1+")
    context["a_close_location_bin"] = np.select(
        [context.a_outward_close_location.isna(), context.a_outward_close_location >= .75],
        ["zero_range", "outward_75pct+"], default="less_outward")
    context["a_last_near_bin"] = np.select(
        [context.a_minutes_since_near_vwap.isna(), context.a_minutes_since_near_vwap <= 30,
         context.a_minutes_since_near_vwap <= 120],
        ["none_in_window", "<=30", "31-120"], default="120+")
    context["c_departure_strength_bin"] = _sigma_bin(
        context.c_departure_strength_sigma, (1.5, 2), ("1-1.5", "1.5-2", "2+"))
    context["c_peak_close_bin"] = _sigma_bin(
        context.c_peak_close_sigma, (1.5, 2), ("1-1.5", "1.5-2", "2+"))
    context["c_departure_to_touch_bin"] = np.select(
        [context.c_departure_to_touch_minutes.isna(),
         context.c_departure_to_touch_minutes <= 15,
         context.c_departure_to_touch_minutes <= 45],
        ["unavailable", "<=15", "16-45"], default=">45")
    context["c_peak_to_touch_bin"] = np.select(
        [context.c_peak_to_touch_minutes.isna(), context.c_peak_to_touch_minutes <= 15],
        ["unavailable", "<=15"], default=">15")
    context["c_away_closes_bin"] = np.select(
        [context.c_away_closes_1sigma.isna(), context.c_away_closes_1sigma <= 2,
         context.c_away_closes_1sigma <= 5],
        ["unavailable", "1-2", "3-5"], default="6+")
    width_cutoffs = {}
    for (product, window), group in context[
        (context.split == "development") & context.opening_balance_width_atr.notna()
    ].drop_duplicates(["product", "session_date", "window"]).groupby(["product", "window"]):
        q1, q2 = group.opening_balance_width_atr.quantile([1 / 3, 2 / 3]).tolist()
        width_cutoffs[f"{product}/{window}"] = {"low_max": float(q1), "middle_max": float(q2)}
    width_bins = []
    for row in context.itertuples(index=False):
        value = row.opening_balance_width_atr
        cutoff = width_cutoffs.get(f"{row.product}/{row.window}")
        if pd.isna(value) or cutoff is None:
            width_bins.append("unavailable")
        elif value <= cutoff["low_max"]:
            width_bins.append("narrow")
        elif value <= cutoff["middle_max"]:
            width_bins.append("middle")
        else:
            width_bins.append("wide")
    context["opening_balance_width_bin"] = width_bins
    return context, width_cutoffs


def interval(group: pd.DataFrame, outcome: str = "h30_barrier_0p5",
             seed: int = 310733, reps: int = 600) -> tuple[float | None, float | None]:
    if len(group) == 0:
        return None, None
    dates = group.assign(_success=(group[outcome] == "favorable").astype(int)).groupby(
        "session_date")._success.agg(["sum", "count"]).to_numpy(dtype=float)
    if len(dates) < 2:
        return None, None
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, len(dates), size=(reps, len(dates)))
    selected = dates[picks].sum(axis=1)
    rates = selected[:, 0] / selected[:, 1]
    return float(np.quantile(rates, .025)), float(np.quantile(rates, .975))


def cell(group: pd.DataFrame, total: int, metric_id: str) -> dict:
    counts = group.h30_barrier_0p5.value_counts() if len(group) else {}
    fixed = group.h30_barrier_8ticks.value_counts() if len(group) else {}
    n = len(group)
    low, high = interval(group, seed=310733 + int(sha256(metric_id.encode()).hexdigest()[:6], 16))
    result = {"metric_id": metric_id, "events": n,
              "product_sessions": int(group[["product", "session_date"]].drop_duplicates().shape[0]) if n else 0,
              "calendar_dates": int(group.session_date.nunique()) if n else 0,
              "favorable": int(counts.get("favorable", 0)),
              "adverse": int(counts.get("adverse", 0)),
              "neither": int(counts.get("neither", 0)),
              "ambiguous": int(counts.get("ambiguous", 0)),
              "rate": int(counts.get("favorable", 0)) / n if n else None,
              "optimistic_rate": (int(counts.get("favorable", 0)) +
                                  int(counts.get("ambiguous", 0))) / n if n else None,
              "ci_low": low, "ci_high": high,
              "fixed8_favorable": int(fixed.get("favorable", 0)),
              "fixed8_adverse": int(fixed.get("adverse", 0)),
              "fixed8_neither": int(fixed.get("neither", 0)),
              "fixed8_ambiguous": int(fixed.get("ambiguous", 0)),
              "fixed8_rate": int(fixed.get("favorable", 0)) / n if n else None,
              "coverage": n / total if total else None,
              "sparse": n < 100 or (int(group[["product", "session_date"]].drop_duplicates().shape[0]) if n else 0) < 30,
              "median_pre_barrier_mfe_ticks": float(group.h30_pre_barrier_mfe_ticks.median()) if n else None,
              "median_pre_barrier_mae_ticks": float(group.h30_pre_barrier_mae_ticks.median()) if n else None}
    for split in ("development", "validation", "final"):
        part = group[group.split == split]
        result[f"{split}_events"] = len(part)
        result[f"{split}_rate"] = (float((part.h30_barrier_0p5 == "favorable").mean())
                                    if len(part) else None)
    return result


def cuts(context: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    primary = context[context.strategy.isin(["A", "C"]) & context.exclusion.isna() &
                      (context.h30_evaluable == True)].copy()
    totals = {s: len(primary[primary.strategy == s]) for s in ("A", "C")}
    dimensions = {
        "A": ["product", "window", "anchor", "timeframe", "direction_label",
              "window_clock_bin", "anchor_age_bin", "atr_regime",
              "opening_balance_location", "opening_balance_width_bin", "vwap_geometry",
              "a_exit_strength_bin", "a_trend_bin", "a_close_location_bin",
              "a_last_near_bin"],
        "C": ["product", "window", "anchor", "timeframe", "direction_label",
              "window_clock_bin", "anchor_age_bin", "atr_regime",
              "opening_balance_location", "opening_balance_width_bin", "vwap_geometry",
              "c_departure_strength_bin", "c_peak_close_bin",
              "c_departure_to_touch_bin", "c_peak_to_touch_bin", "c_away_closes_bin",
              "touch_close_class", "ordinal"]}
    rows = []
    for strategy in ("A", "C"):
        part = primary[primary.strategy == strategy]
        rows.append({"strategy": strategy, "scope": "ALL", "dimension": "ALL", "value": "ALL",
                     **cell(part, totals[strategy], f"{strategy.lower()}.all")})
        for dimension in dimensions[strategy]:
            for value, group in part.groupby(dimension, dropna=False):
                rows.append({"strategy": strategy, "scope": "ALL", "dimension": dimension,
                             "value": str(value), **cell(group, totals[strategy],
                             f"{strategy.lower()}.{dimension}.{value}")})
        selected = (["window_clock_bin", "anchor", "atr_regime", "a_exit_strength_bin",
                     "a_trend_bin", "opening_balance_location"] if strategy == "A" else
                    ["window_clock_bin", "anchor", "atr_regime", "c_peak_close_bin",
                     "c_departure_to_touch_bin", "opening_balance_location"])
        for product in ("ES", "NQ", "GC"):
            subset = part[part["product"] == product]
            for dimension in selected:
                for value, group in subset.groupby(dimension, dropna=False):
                    rows.append({"strategy": strategy, "scope": product,
                                 "dimension": dimension, "value": str(value),
                                 **cell(group, len(subset), f"{strategy.lower()}.{product}.{dimension}.{value}")})
    cut_table = pd.DataFrame(rows)
    ny_rows = []
    ny_all = primary[(primary.strategy == "A") & (primary.window == "ny")]
    for product in ("ALL", "ES", "NQ", "GC"):
        group = ny_all if product == "ALL" else ny_all[ny_all["product"] == product]
        for anchor in ("globex", "ny"):
            anchor_group = group[group.anchor == anchor]
            for clock in ("00-29", "30-59", "60-119", "120+"):
                subset = anchor_group[anchor_group.window_clock_bin == clock]
                ny_rows.append({"product": product, "anchor": anchor, "clock": clock,
                                "structurally_unavailable": anchor == "ny" and clock == "00-29",
                                **cell(subset, len(anchor_group), f"a.ny.{product}.{anchor}.{clock}")})
            for name, mask in (("first_hour", anchor_group.window_age_minutes < 60),
                               ("after_first_hour", anchor_group.window_age_minutes >= 60)):
                ny_rows.append({"product": product, "anchor": anchor, "clock": name,
                                "structurally_unavailable": False,
                                **cell(anchor_group[mask], len(anchor_group),
                                       f"a.ny.{product}.{anchor}.{name}")})
    interactions = []
    for strategy, name, cols, filter_fn in (
        ("A", "exit_strength_x_prior_trend", ["a_exit_strength_bin", "a_trend_bin"],
         lambda df: df),
        ("C", "peak_2plus_x_peak_to_touch", ["c_peak_close_bin", "c_peak_to_touch_bin"],
         lambda df: df[df.c_peak_close_bin == "2+"])):
        part = primary[primary.strategy == strategy]
        for product in ("ALL", "ES", "NQ", "GC"):
            group = part if product == "ALL" else part[part["product"] == product]
            for values, subset in filter_fn(group).groupby(cols, dropna=False):
                label = "/".join(str(x) for x in values)
                interactions.append({"strategy": strategy, "interaction": name,
                                     "product": product, "values": label,
                                     **cell(subset, len(group),
                                            f"{strategy.lower()}.{name}.{product}.{label}")})
    return cut_table, pd.DataFrame(ny_rows), pd.DataFrame(interactions)


def _matched_difference(left: pd.DataFrame, right: pd.DataFrame, keys: list[str],
                        outcome: str) -> dict:
    lgroups = left.groupby(keys, dropna=False)
    rgroups = right.groupby(keys, dropna=False)
    matching = set(lgroups.groups).intersection(rgroups.groups)
    treated_count = 0
    treated_success = control_expected = 0.0
    contribution = []
    for key in sorted(matching, key=str):
        a = lgroups.get_group(key)
        b = rgroups.get_group(key)
        treated_count += len(a)
        av = (a[outcome] == "favorable").astype(float)
        bv = (b[outcome] == "favorable").astype(float)
        treated_success += float(av.sum())
        control_expected += len(a) * float(bv.mean())
        contribution.extend((date, float(success), 1.0) for date, success in zip(a.session_date, av))
        weight = len(a) / len(b)
        contribution.extend((date, -weight * float(success), 0.0)
                            for date, success in zip(b.session_date, bv))
    low = high = None
    if treated_count and contribution:
        contributions = pd.DataFrame(contribution, columns=["date", "difference", "count"]).groupby(
            "date")[["difference", "count"]].sum().to_numpy(dtype=float)
        if len(contributions) >= 2:
            rng = np.random.default_rng(310734)
            picks = rng.integers(0, len(contributions), size=(600, len(contributions)))
            totals = contributions[picks].sum(axis=1)
            samples = totals[totals[:, 1] > 0, 0] / totals[totals[:, 1] > 0, 1]
            if len(samples):
                low, high = np.quantile(samples, [.025, .975]).tolist()
    return {"treated_events": len(left), "control_events": len(right),
            "matched_treated": treated_count, "unmatched_treated": len(left) - treated_count,
            "treated_rate_matched": treated_success / treated_count if treated_count else None,
            "control_rate_weighted": control_expected / treated_count if treated_count else None,
            "difference": (treated_success - control_expected) / treated_count if treated_count else None,
            "ci_low_conditional_overlap": low, "ci_high_conditional_overlap": high}


def controls(context: pd.DataFrame) -> pd.DataFrame:
    good = context[context.exclusion.isna() & (context.h30_evaluable == True)]
    rows = []
    keys = ["product", "timeframe", "anchor", "window", "direction",
            "window_clock_bin", "atr_regime", "split"]
    definitions = [("A", "A_control"), ("C", "C_near")]
    for treated, control in definitions:
        for scope, part in (("ALL", good), ("NY", good[good.window == "ny"])):
            for product in ("ALL", "ES", "NQ", "GC"):
                group = part if product == "ALL" else part[part["product"] == product]
                for clock in (("ALL", "00-29", "30-59", "60-119", "120+")
                              if scope == "NY" else ("ALL",)):
                    for anchor in (("ALL", "globex", "ny") if scope == "NY" else ("ALL",)):
                        subset = group
                        if clock != "ALL":
                            subset = subset[subset.window_clock_bin == clock]
                        if anchor != "ALL":
                            subset = subset[subset.anchor == anchor]
                        left = subset[subset.strategy == treated]
                        right = subset[subset.strategy == control]
                        for barrier, outcome in (("half_sigma", "h30_barrier_0p5"),
                                                 ("fixed_8_ticks", "h30_barrier_8ticks")):
                            rows.append({"treated": treated, "control": control,
                                         "scope": scope, "product": product,
                                         "clock": clock, "anchor": anchor,
                                         "barrier_definition": barrier,
                                         **_matched_difference(left, right, keys, outcome)})
    return pd.DataFrame(rows)


def reentry_table(reentry: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for product in ("ALL", "ES", "NQ", "GC"):
        part = reentry if product == "ALL" else reentry[reentry["product"] == product]
        for window in ("ALL", "globex", "asia", "london", "ny"):
            group = part if window == "ALL" else part[part.window == window]
            if group.empty:
                continue
            eligible = group[group.status == "evaluable"]
            counts = eligible.h30_barrier_0p5.value_counts()
            rows.append({"product": product, "window": window,
                         "original_a_events": len(group),
                         "confirmed": int(group.confirmed.sum()),
                         "confirmed_fraction": float(group.confirmed.mean()),
                         "evaluable_reentry": len(eligible),
                         "no_reentry": int((group.status == "no_reentry").sum()),
                         "late_for_30m": int((group.status == "late_for_30m").sum()),
                         "missing_or_discontinuous": int(group.status.isin(
                             ["missing_reference", "source_discontinuity", "contract_change"]).sum()),
                         "inside_without_true_flag": int((group.status == "inside_without_true_flag").sum()),
                         "already_past_vwap": int((group.already_past_vwap == True).sum()),
                         "favorable": int(counts.get("favorable", 0)),
                         "adverse": int(counts.get("adverse", 0)),
                         "neither": int(counts.get("neither", 0)),
                         "ambiguous": int(counts.get("ambiguous", 0)),
                         "conditional_rate": float((eligible.h30_barrier_0p5 == "favorable").mean()) if len(eligible) else None,
                         "median_minutes_to_reentry": float(group.minutes_to_reentry.median()),
                         "median_remaining_vwap_ticks": float(eligible.remaining_to_vwap_ticks.median()) if len(eligible) else None})
    return pd.DataFrame(rows)


def examples(context: pd.DataFrame) -> pd.DataFrame:
    primary = context[context.strategy.isin(["A", "C"]) & context.exclusion.isna() &
                      (context.h30_evaluable == True)]
    rows = []
    samples = [("A", "early_ny", lambda g: g[(g.window == "ny") & (g.window_clock_bin == "00-29")]),
               ("A", "later_ny", lambda g: g[(g.window == "ny") & (g.window_age_minutes >= 60)]),
               ("C", "peak_2plus", lambda g: g[g.c_peak_close_bin == "2+"]),
               ("C", "peak_below_1p5", lambda g: g[g.c_peak_close_bin == "1-1.5"])]
    for strategy, label, select in samples:
        for product in PRODUCTS_LOCAL:
            group = select(primary[(primary.strategy == strategy) & (primary["product"] == product)])
            for outcome in ("favorable", "adverse", "ambiguous", "neither"):
                candidate = group[group.h30_barrier_0p5 == outcome].sort_values("signal_ts")
                if len(candidate):
                    row = candidate.iloc[0]
                    rows.append({"strategy": strategy, "product": product, "segment": label,
                                 "outcome": outcome, "event_id": row.event_id,
                                 "signal_ts": row.signal_ts, "anchor": row.anchor,
                                 "window": row.window})
    return pd.DataFrame(rows)


PRODUCTS_LOCAL = ("ES", "NQ", "GC")


def fmt(value, percent: bool = False) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{100 * value:.1f}%" if percent else f"{value:,.0f}"


def write_figures(stage: Path, ny: pd.DataFrame, cut: pd.DataFrame) -> None:
    (stage / "figures").mkdir(exist_ok=True)
    def save(name: str, title: str, rows: list[tuple[str, float, int]], color: str) -> None:
        height = 90 + 52 * len(rows)
        parts = [f"<svg xmlns='http://www.w3.org/2000/svg' width='900' height='{height}' "
                 f"viewBox='0 0 900 {height}' role='img' aria-label='{escape(title, quote=True)}'>",
                 "<rect width='900' height='100%' fill='white'/>",
                 f"<text x='28' y='34' font-family='system-ui' font-size='21' fill='#17243b'>{escape(title)}</text>"]
        for idx, (label, rate, count) in enumerate(rows):
            y = 68 + idx * 52
            parts.append(f"<text x='28' y='{y + 20}' font-family='system-ui' font-size='14' fill='#17243b'>{escape(label)}</text>")
            parts.append(f"<rect x='275' y='{y}' width='500' height='28' fill='#edf1f6'/>")
            parts.append(f"<rect x='275' y='{y}' width='{max(0, min(500, 500 * rate)):.1f}' height='28' fill='{color}'/>")
            parts.append(f"<text x='790' y='{y + 20}' font-family='system-ui' font-size='14' fill='#17243b'>"
                         f"{100 * rate:.1f}% · n={count:,}</text>")
        parts.append("</svg>")
        (stage / "figures" / name).write_text("".join(parts))
    ny_rows = []
    for row in ny[(ny["product"] == "ALL") &
                  ny.clock.isin(["first_hour", "after_first_hour"])].itertuples(index=False):
        if pd.notna(row.rate):
            ny_rows.append((f"{row.anchor}: {row.clock.replace('_', ' ')}", float(row.rate), int(row.events)))
    save("ny-early.svg", "A exits in the NY observation window", ny_rows, "#bb7655")
    c_rows = []
    for row in cut[(cut.strategy == "C") & (cut.scope == "ALL") &
                   (cut.dimension == "c_peak_close_bin")].itertuples(index=False):
        if pd.notna(row.rate):
            c_rows.append((f"Pre-touch peak {row.value}σ", float(row.rate), int(row.events)))
    save("c-peak.svg", "C outcomes by pre-touch peak distance", c_rows, "#267f79")


def report(stage: Path, cut: pd.DataFrame, ny: pd.DataFrame,
           interaction: pd.DataFrame, compare: pd.DataFrame,
           reentry: pd.DataFrame, context: pd.DataFrame) -> None:
    all_a = cut[(cut.strategy == "A") & (cut.dimension == "ALL")].iloc[0]
    all_c = cut[(cut.strategy == "C") & (cut.dimension == "ALL")].iloc[0]
    lines = ["# VWAP A/C conditional-context study", "",
             "Exploratory price-path cuts on sealed parent run `20260923T015900Z_vwap3`, "
             "with new causal context from the same pinned Bhishma 1.0.0 release. "
             "The parent A/C outcomes and excluded-event identities are unchanged. "
             "Earlier aggregate and final-period outcomes were already viewed; newly selected segments "
             "are discovery evidence, not independent confirmation or net trading performance.", "",
             "## Scorecard and populations", "",
             "| Candidate | Full 30m events | Favorable first | Adverse first | Neither | Ambiguous | 95% shared-date interval |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for label, row in (("A: first outside-2σ fade", all_a), ("C: first causal VWAP retest", all_c)):
        lines.append(f"| {label} | {row.events:,} | {row.favorable:,} ({fmt(row.rate, True)}) | "
                     f"{row.adverse:,} | {row.neither:,} | {row.ambiguous:,} | "
                     f"{fmt(row.ci_low, True)}–{fmt(row.ci_high, True)} |")
    lines += ["", "These are correlated anchor/timeframe views across product-sessions. "
              "See `tables/cuts.csv` for every inspected cut, four barrier classes, common 8-tick results, "
              "coverage, distinct dates, and chronological rates. `context/` retains event-linked evidence. "
              "The 0.5σ and 8-tick outcomes are measured after signal availability from the following "
              "unadjusted one-minute open. Costs and fills are unspecified.", "",
              "## A: NY early 2σ exits", "",
              "The NY observation window starts at 09:30 America/New_York. Columns below compare "
              "the first 30 minutes, minutes 30–59, and later exits on a fixed 30-minute-capable cohort. "
              "The NY local anchor is structurally ineligible during the first 30 minutes because "
              "the original protocol requires 30 elapsed minutes of accumulation. Globex VWAP in the "
              "NY window can signal immediately.", "",
              "| Product | Anchor | NY clock | Events | Favorable first | 95% interval | 8-tick rate | Coverage within anchor |",
              "|---|---|---|---:|---:|---:|---:|---:|"]
    for row in ny[(ny.clock.isin(["00-29", "30-59", "60-119", "120+"])) &
                  (ny["product"].isin(["ALL", "ES", "NQ", "GC"]))].itertuples(index=False):
        lines.append(f"| {row.product} | {row.anchor} | {row.clock} | {row.events:,} | "
                     f"{fmt(row.rate, True)} | {fmt(row.ci_low, True)}–{fmt(row.ci_high, True)} | "
                     f"{fmt(row.fixed8_rate, True)} | {fmt(row.coverage, True)} |")
    lines += ["", "![NY early A outcomes](figures/ny-early.svg)", "",
              "The proposed early-NY weakness is not present in the primary 0.5σ result for "
              "Globex: first-hour exits are 48.7% favorable first (2,260 events), versus "
              "42.4% after the first hour (4,131). The fixed 8-tick result reverses that "
              "ordering (28.5% versus 35.2%). NY-local exits first become eligible at "
              "minute 30; their first-hour primary rate is 46.0% versus 45.8% later. "
              "These are descriptive probabilities, not an early-session trading rule.", "",
              "`tables/ny_early.csv` also compares the first hour with the later session. "
              "`tables/control_comparisons.csv` matches A's 1–2σ control within product, timeframe, "
              "anchor/window, direction, window-clock bin, ATR regime, and chronological split. "
              "A and its lesser-departure control still have disjoint starting-distance support. "
              "A higher conditional fade rate alone is not an incremental edge.", "",
              "## C: distance before first touch and return shape", "",
              "Peak excursion uses completed closes from departure through the bar before touch opens; "
              "the touching bar's extremes are excluded. The peak bins are 1–1.5σ, 1.5–2σ, and 2σ+. "
              "The prespecified interaction compares peak-to-touch time ≤15 versus >15 minutes "
              "within the 2σ+ peak group. Each outcome starts after the touch bar closes.", "",
              "| Product | Pre-touch peak | Events | Favorable first | 95% interval | 8-tick rate |",
              "|---|---|---:|---:|---:|---:|"]
    for row in cut[(cut.strategy == "C") & (cut.dimension == "c_peak_close_bin") &
                   (cut.scope.isin(["ALL", "ES", "NQ", "GC"]))].itertuples(index=False):
        lines.append(f"| {row.scope} | {row.value} | {row.events:,} | {fmt(row.rate, True)} | "
                     f"{fmt(row.ci_low, True)}–{fmt(row.ci_high, True)} | {fmt(row.fixed8_rate, True)} |")
    lines += ["", "![C outcomes by pre-touch peak distance](figures/c-peak.svg)", "",
              "A prior peak of 2σ+ is associated with a 45.6% primary bounce rate, versus "
              "47.2% at 1–1.5σ and 47.8% at 1.5–2σ. All three fixed 8-tick rates "
              "cluster near 40–41%. Within the 2σ+ group, a return from the peak in "
              "≤15 minutes has a 47.6% primary rate versus 45.0% for slower returns; "
              "the fixed 8-tick rates are 39.0% and 40.2%. Neither dimension yields a "
              "stable improvement across barrier definitions.", "",
              "`tables/interactions.csv` gives the peak-distance × return-time cells; "
              "`tables/cuts.csv` also shows departure strength, sustained away closes, time to touch, "
              "touch close class, local/Globex geometry, ATR, opening balance, and session clocks. "
              "The C near-approach baseline lacks the same saved departure link, so those peak/shape "
              "cuts are within-C associations; they do not yet prove that touching VWAP adds information "
              "over a comparable near approach.", "",
              "## A: exit strength, prior trend, and regime", "",
              "`tables/cuts.csv` includes signal-close distance past 2σ, prior 30-minute side-signed "
              "price trend, outward signal-bar close location, prior VWAP slope and sigma expansion, "
              "time since a near-VWAP close, prior ATR regime, opening-balance width/location, and "
              "local/Globex VWAP geometry. `tables/interactions.csv` records the prespecified "
              "exit-strength × prior-trend cells. Exits farther than 2.75σ are 46.7% "
              "favorable at the primary barrier and 36.6% at 8 ticks; the 2–2.25σ "
              "group is 46.3% and 40.3%. Stronger exit distance is not a consistent "
              "improvement. The outward frozen 3σ-before-return evidence remains "
              "in the event ledger, with already-passed and same-minute order bounds retained.", "",
              "## Re-entry is a later signal", "",
              "The first published close back inside the same 2σ band is evaluated from its own "
              "following open. Confirmed and never-confirmed original A episodes stay in the "
              "denominator. `tables/reentry.csv` separates conversion, full-follow-up eligibility, "
              "remaining VWAP distance, and conditional post-confirmation outcomes. Of 90,938 "
              "original A episodes, 89,475 (98.4%) confirm re-entry, but only 84,997 "
              "have a full 30-minute follow-up. Their conditional favorable-first rate is 45.8%. "
              "A selected "
              "post-confirmation rate is not a paired trading-policy result: entry time, barrier size, "
              "and missed opportunities differ from immediate A.", "",
              "## Validation and limitations", "",
              "Development ends in 2023, validation is 2024, and final chronological evaluation is "
              "2025–2026. The final period was already viewed in the parent study, so every new cut "
              "is exploratory. Whole shared dates are resampled for intervals; multiple anchor/timeframe "
              "views are correlated. Small cells are flagged. Do not rank a sparse cell as a discovery, "
              "and do not infer net profitability from a barrier rate. The complete-day eligibility "
              "filter is retrospective. Source checks, parent hashes, exact commands, and artifact "
              "hashes are in the manifest and audit files.", "",
              "## Evidence and reproduction", "",
              "[All cuts](tables/cuts.csv) · [NY early exits](tables/ny_early.csv) · "
              "[Interactions](tables/interactions.csv) · [Control comparisons](tables/control_comparisons.csv) · "
              "[Re-entry](tables/reentry.csv) · [Examples](tables/examples.csv) · "
              "[Metrics](metrics.json) · [Event manifest](events.manifest.json) · "
              "[Run manifest](manifest.json)", "",
              "From the workspace root, with the locked environment installed: "
              "`.venv/bin/python studies/05_session_vwap/conditional_run.py --run-id <new-id> --workers 3`, "
              "then `.venv/bin/python studies/05_session_vwap/conditional_summarize.py --run-id <same-id>`. "
              "Review audits before sealing a new unique ID.", ""]
    markdown = "\n".join(lines)
    (stage / "report.md").write_text(markdown)
    html = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>VWAP A/C conditional context</title>",
            "<style>body{font:16px/1.55 system-ui;max-width:1120px;margin:3rem auto;padding:0 1.5rem;color:#17243b}"
            "table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:.48rem;border-bottom:1px solid #cbd5e1;text-align:left}"
            "th{background:#eef2f7}h1,h2{margin-top:2rem}p{max-width:88ch}a{color:#126c91}</style><main>"]
    in_table = False
    for line in lines:
        if line.startswith("|"):
            values = [escape(x.strip()) for x in line.strip("|").split("|")]
            if all(set(x) <= {"-", ":"} for x in values):
                continue
            if not in_table:
                html.append("<table><thead><tr>" + "".join(f"<th>{x}</th>" for x in values) + "</tr></thead><tbody>")
                in_table = True
            else:
                html.append("<tr>" + "".join(f"<td>{x}</td>" for x in values) + "</tr>")
            continue
        if in_table:
            html.append("</tbody></table>")
            in_table = False
        if not line:
            continue
        if line.startswith("## "):
            html.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("# "):
            html.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("!["):
            import re
            match = re.fullmatch(r"!\[([^\]]+)\]\(([^)]+)\)", line)
            if not match:
                raise ValueError("invalid local figure reference")
            html.append(f"<figure><img src='{escape(match.group(2), quote=True)}' "
                        f"alt='{escape(match.group(1), quote=True)}' style='max-width:100%'></figure>")
        else:
            import re
            content = escape(line)
            content = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                             lambda m: f"<a href='{escape(m.group(2), quote=True)}'>{m.group(1)}</a>", content)
            html.append(f"<p>{content}</p>")
    if in_table:
        html.append("</tbody></table>")
    html.append("</main></html>\n")
    (stage / "report.html").write_text("\n".join(html))


def write_all(stage: Path) -> None:
    context, reentry = read_context(stage)
    raw_context_schema = {name: str(dtype) for name, dtype in context.dtypes.items()}
    context, width_cutoffs = add_bins(context)
    (stage / "tables").mkdir(exist_ok=True)
    cut, ny, interaction = cuts(context)
    compare = controls(context)
    reentry_summary = reentry_table(reentry)
    sample = examples(context)
    for name, table in (("cuts", cut), ("ny_early", ny), ("interactions", interaction),
                        ("control_comparisons", compare), ("reentry", reentry_summary),
                        ("examples", sample)):
        table.to_csv(stage / "tables" / f"{name}.csv", index=False)
    write_figures(stage, ny, cut)
    (stage / "opening-balance-cutoffs.json").write_text(json.dumps(width_cutoffs, indent=2) + "\n")
    metrics = [{"id": row.metric_id, "strategy": row.strategy,
                "scope": row.scope, "dimension": row.dimension, "value": row.value,
                "cohort": "full_30m_followup", "horizon": "30_minutes",
                "unit": "probability", "numerator": int(row.favorable),
                "denominator": int(row.events), "estimate": float(row.rate) if pd.notna(row.rate) else None,
                "ci_95": [float(row.ci_low) if pd.notna(row.ci_low) else None,
                          float(row.ci_high) if pd.notna(row.ci_high) else None],
                "uncertainty_unit": "shared_session_date"}
               for row in cut.itertuples(index=False)]
    (stage / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False) + "\n")
    report(stage, cut, ny, interaction, compare, reentry_summary, context)
    manifest = {"location": "context/", "format": "Parquet",
                "retention": "included_in_sealed_run", "context_rows": len(context),
                "reentry_rows": len(reentry),
                "context_schema": raw_context_schema,
                "reentry_schema": {name: str(dtype) for name, dtype in reentry.dtypes.items()},
                "partitions": [{"path": str(path.relative_to(stage)),
                                "sha256": sha256(path.read_bytes()).hexdigest()}
                               for path in sorted((stage / "context").glob("*.parquet"))]}
    (stage / "events.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    score = cut[(cut.scope == "ALL") & (cut.dimension == "ALL")]
    rows = [{"candidate": "A: first outside-2σ fade" if row.strategy == "A" else
             "C: first VWAP retest bounce", "events": int(row.events),
             "favorable": int(row.favorable), "adverse": int(row.adverse),
             "rate": float(row.rate), "ciLow": float(row.ci_low), "ciHigh": float(row.ci_high)}
            for row in score.itertuples(index=False)]
    publication = {"schemaVersion": "1.0", "id": f"vwap-ac-context-{stage.name.lower().replace('_','-')}",
                   "title": "VWAP A/C conditional context", "summary": "Exploratory early-session and pre-touch price-path cuts on pinned VWAP evidence.",
                   "publishedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "source": {"producer": "sahadeva", "runId": stage.name},
                   "sections": [{"id": "scorecard", "title": "A/C parent outcome scorecard", "kind": "table",
                                 "columns": [{"key": "candidate", "label": "Candidate"},
                                             {"key": "events", "label": "Events"},
                                             {"key": "favorable", "label": "Favorable first"},
                                             {"key": "adverse", "label": "Adverse first"},
                                             {"key": "rate", "label": "Rate", "format": "percent"},
                                             {"key": "ciLow", "label": "95% low", "format": "percent"},
                                             {"key": "ciHigh", "label": "95% high", "format": "percent"}],
                                 "rows": rows},
                                {"id": "scope", "title": "Scope and caution", "kind": "text",
                                 "body": "Exploratory A/C cuts on previously viewed dates. See the saved offline report for NY early exits, C pre-touch excursion, denominators, baselines, and limits. No net trading claim."}],
                   "notes": ["Local publication source only; hosted publication requires separate authorization."]}
    (stage / "publication.json").write_text(json.dumps(publication, indent=2) + "\n")
