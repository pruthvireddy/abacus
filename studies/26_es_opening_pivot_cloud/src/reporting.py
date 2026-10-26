"""Saved-ledger statistics and a separate saved-statistics report producer.

``summarize`` reads outcome ledgers, writes numerical evidence, and never imports
the engine. ``report`` reads only those saved tables for numbers and charts. It
does not compute statistics or load price/feature authorities. See the prespecified
reporting-decisions.md for denominators, bins and inference qualifications.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

import numpy as np

SEED = 26021
RESAMPLES = 4000
ENTRY_POLICIES = ("early", "confirmed")
MASKS = ("A", "B", "C", "D")
EXIT_POLICIES = ("fixed_2r", "verne")
VARIANTS = tuple((e, m, x) for e in ENTRY_POLICIES for m in MASKS for x in EXIT_POLICIES)
PRIMARY = ("early", "A", "fixed_2r")
INSPIRED_DATE = "2026-09-15"
NUMERIC_FIELDS = {
    "net_dollars", "net_r", "optimistic_net_dollars", "optimistic_net_r",
    "entry_price", "stop_price", "initial_risk_points", "exit_price",
    "confirmation_delay", "mae_points", "mfe_points", "holding_minutes",
    "target_price", "target_ordinal", "target_distance_r", "pivot_lower",
    "pivot_upper", "pivot_width", "pivot_cloud_separation", "cloud_width_atr",
    "atr14", "entry_pivot_distance_points", "open", "high", "low", "close",
    "ema20", "ema50", "reaction_open", "reaction_high", "reaction_low",
    "reaction_close",
    "gross_dollars", "preopen_atr14", "first_touch_prior_atr14",
}
BOOL_FIELDS = {"candidate", "trade", "ambiguity", "ordering_pass", "slope_pass", "is_primary", "inspired_date"}
BINS = {
    "pivot_width": (0, 1, 2, 5, 10),
    "pivot_cloud_separation": (0, 1, 2, 5, 10),
    "cloud_width_atr": (0, .25, .5, 1, 2),
    "preopen_atr14": (0, 2, 4, 8, 16),
    "initial_risk_points": (0, 2, 4, 8, 16),
    "entry_pivot_distance_points": (0, 1, 2, 5, 10),
    "target_distance_r": (0, .5, 1, 2, 3, 5),
}


def _clean(value: Any) -> Any:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_clean(value), indent=2, sort_keys=True, allow_nan=False) + "\n")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key, value in row.items():
            if value == "" or value in ("None", "null", "nan"):
                row[key] = None
            elif key in BOOL_FIELDS:
                row[key] = value.lower() in ("true", "1", "yes")
            elif key in NUMERIC_FIELDS:
                row[key] = float(value)
    return rows


def write_rows(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: _clean(row.get(key)) for key in columns} for row in rows)


def variant(row: dict) -> tuple:
    return tuple(row[key] for key in ("entry_policy", "mask", "exit_policy"))


def _identity(v: tuple) -> dict:
    return dict(zip(("entry_policy", "mask", "exit_policy"), v))


def _mean(values: list) -> float | None:
    clean = [v for v in values if v is not None]
    return float(np.mean(clean)) if clean else None


def bootstrap(values: list, dates: list[str], *, week: bool = False,
              resamples: int = RESAMPLES, seed: int = SEED) -> dict:
    """Paired values are formed before resampling; undefined pairs stay absent.

    Week resamples use cluster totals/counts to retain the session-weighted
    estimand, rather than giving every week an equal contribution regardless of
    its observed day count. Exact ties are counted conservatively in both tails.
    """
    pairs = [(float(v), d) for v, d in zip(values, dates) if v is not None]
    if not pairs:
        return {"estimate": None, "ci_low": None, "ci_high": None, "tail_probability": None, "clusters": 0}
    val = np.asarray([v for v, _ in pairs])
    if week:
        clusters: dict[str, list] = {}
        for value, day in pairs:
            year, number, _ = datetime.fromisoformat(day[:10]).isocalendar()
            clusters.setdefault(f"{year}-{number:02}", []).append(value)
        totals = np.asarray([sum(items) for items in clusters.values()])
        counts = np.asarray([len(items) for items in clusters.values()])
    else:
        totals, counts = val, np.ones(len(val))
    n = len(totals)
    result = {"estimate": float(val.mean()), "ci_low": None, "ci_high": None,
              "tail_probability": None, "clusters": n}
    if n < 2:
        return result
    rng = np.random.default_rng(seed)
    samples = []
    for start in range(0, resamples, 256):
        indices = rng.integers(0, n, (min(256, resamples - start), n))
        samples.append(totals[indices].sum(axis=1) / counts[indices].sum(axis=1))
    draws = np.concatenate(samples)
    low, high = np.quantile(draws, [.025, .975])
    result.update(ci_low=float(low), ci_high=float(high),
                  tail_probability=min(1.0, 2 * min((np.sum(draws <= 0) + 1) / (resamples + 1),
                                                     (np.sum(draws >= 0) + 1) / (resamples + 1))))
    return result


def holm(probabilities: list[float | None]) -> list[float | None]:
    """Holm adjustment of the declared family; undefined members stay undefined."""
    result: list[float | None] = [None] * len(probabilities)
    order = sorted((p, i) for i, p in enumerate(probabilities) if p is not None)
    running = 0.0
    # The family size remains prespecified even if some contrasts are undefined.
    for rank, (p, i) in enumerate(order):
        running = max(running, min(1.0, p * (len(probabilities) - rank)))
        result[i] = running
    return result


def _drawdown(values: list[float]) -> float:
    equity = np.concatenate(([0.0], np.cumsum(values)))
    return float(np.max(np.maximum.accumulate(equity) - equity))


def summarize_group(rows: list[dict]) -> dict:
    ordered = sorted(rows, key=lambda row: row["date"])
    values = [r.get("net_dollars") for r in ordered]
    defined = [v for v in values if v is not None]
    trades = [r for r in ordered if r.get("trade") and r.get("net_dollars") is not None]
    dollars = [r["net_dollars"] for r in trades]
    rs = [r.get("net_r") for r in trades if r.get("net_r") is not None]
    dates = [r["date"] for r in ordered]
    ci = bootstrap(values, dates)
    week = bootstrap(values, dates, week=True)
    wins, losses = [v for v in dollars if v > 0], [v for v in dollars if v < 0]
    average_win, average_loss = _mean(wins), _mean(losses)
    complete = bool(ordered) and len(defined) == len(ordered)
    result = {
        "eligible_sessions": len(rows), "defined_sessions": len(defined),
        "start_date": ordered[0]["date"] if ordered else None,
        "end_date": ordered[-1]["date"] if ordered else None,
        "unavailable_sessions": len(rows) - len(defined),
        "candidates": sum(bool(r.get("candidate")) for r in rows), "trades": len(trades),
        "participation": len(trades) / len(rows) if rows else None,
        "net_dollars": sum(defined) if complete else None,
        "net_per_session": _mean(defined) if complete else None,
        "net_per_available_session": _mean(defined),
        "session_ci_low": ci["ci_low"] if complete else None,
        "session_ci_high": ci["ci_high"] if complete else None,
        "week_ci_low": week["ci_low"] if complete else None,
        "week_ci_high": week["ci_high"] if complete else None,
        "expectancy_dollars": _mean(dollars), "expectancy_r": _mean(rs),
        "win_rate": len(wins) / len(trades) if trades else None,
        "average_win_dollars": average_win, "average_loss_dollars": average_loss,
        "payoff_ratio": average_win / abs(average_loss) if average_win is not None and average_loss else None,
        "profit_factor": sum(wins) / abs(sum(losses)) if losses else None,
        "median_r": float(np.median(rs)) if rs else None,
        "p10_r": float(np.quantile(rs, .1)) if rs else None,
        "p90_r": float(np.quantile(rs, .9)) if rs else None,
        "max_drawdown_dollars": _drawdown(defined) if complete else None,
        "mean_stop_points": _mean([r.get("initial_risk_points") for r in trades]),
        "mean_target_r": _mean([r.get("target_distance_r") for r in trades]),
        "mean_achieved_reward_risk": _mean([r["gross_dollars"] / (50 * r["initial_risk_points"])
                                               for r in trades if r.get("gross_dollars") is not None and r.get("initial_risk_points")]),
        "mean_mae_points": _mean([r.get("mae_points") for r in trades]),
        "mean_mfe_points": _mean([r.get("mfe_points") for r in trades]),
        "mean_holding_minutes": _mean([r.get("holding_minutes") for r in trades]),
        "ambiguity_count": sum(bool(r.get("ambiguity")) for r in trades),
        "optimistic_net_dollars": sum(r.get("optimistic_net_dollars", r["net_dollars"]) or 0 for r in ordered) if complete else None,
        "weak_evidence": len(trades) < 30,
    }
    trade_ci = bootstrap(dollars, [r["date"] for r in trades])
    r_ci = bootstrap([r.get("net_r") for r in trades], [r["date"] for r in trades])
    result.update(trade_ci_low=trade_ci["ci_low"], trade_ci_high=trade_ci["ci_high"],
                  r_ci_low=r_ci["ci_low"], r_ci_high=r_ci["ci_high"])
    return result


def paired(left: list[dict], right: list[dict], *, both_filled: bool = False,
           require_complete: bool = False) -> dict:
    a, b = {r["date"]: r for r in left}, {r["date"]: r for r in right}
    dates = sorted(set(a) & set(b))
    pairs = [(day, a[day], b[day]) for day in dates]
    common = [(d, x, y) for d, x, y in pairs if x.get("net_dollars") is not None and y.get("net_dollars") is not None]
    selected = [(d, x, y) for d, x, y in common if not both_filled or (x.get("trade") and y.get("trade"))]
    differences = [x["net_dollars"] - y["net_dollars"] for _, x, y in selected]
    selected_dates = [d for d, _, _ in selected]
    day = bootstrap(differences, selected_dates)
    week = bootstrap(differences, selected_dates, week=True)
    both = [(x, y) for _, x, y in pairs if x.get("trade") and y.get("trade")]
    coincident = sum(x.get("entry_time") == y.get("entry_time") for x, y in both)
    candidate_count = sum(bool(x.get("candidate")) for _, x, _ in pairs)
    complete = len(common) == len(pairs)
    full_denominator = not require_complete or complete
    result = {
        "eligible_sessions": len(dates), "common_defined_sessions": len(common),
        "paired_sessions": len(selected), "unavailable_pairs": len(pairs) - len(common),
        "both_filled": len(both),
        "neither_filled": sum(not x.get("trade") and not y.get("trade") for _, x, y in pairs),
        "coincident_entries": coincident, "coincident_rate": coincident / len(both) if both else None,
        "confirmation_rate": sum(bool(y.get("trade")) for _, _, y in pairs) / candidate_count if candidate_count else None,
        "confirmed_fill_rate_per_candidate": sum(bool(y.get("trade")) for _, _, y in pairs) / candidate_count if candidate_count else None,
        "left_only": sum(bool(x.get("trade")) and not y.get("trade") for _, x, y in pairs),
        "right_only": sum(bool(y.get("trade")) and not x.get("trade") for _, x, y in pairs),
        "left_mean": _mean([x["net_dollars"] for _, x, _ in selected]) if full_denominator else None,
        "right_mean": _mean([y["net_dollars"] for _, _, y in selected]) if full_denominator else None,
        "difference_dollars": day["estimate"] if full_denominator else None,
        "available_pair_difference": day["estimate"],
        "ci_low": day["ci_low"] if full_denominator else None, "ci_high": day["ci_high"] if full_denominator else None,
        "week_ci_low": week["ci_low"] if full_denominator else None, "week_ci_high": week["ci_high"] if full_denominator else None,
        "bootstrap_tail_probability": day["tail_probability"],
        "weak_evidence": len(both) < 30, "population": "both_filled" if both_filled else "all_eligible_days" if require_complete else "common_defined_days",
    }
    return result


def _bin(value: Any, edges: tuple, *, zero: bool = False) -> str:
    if value is None:
        return "unknown"
    value = abs(float(value))
    if zero and value == 0:
        return "single_price"
    for low, high in zip(edges, (*edges[1:], math.inf)):
        if low <= value < high:
            return f"[{low:g}, {high:g})"
    return "unknown"


def _pivot_type(description: Any) -> str:
    if not description:
        return "unknown"
    matches = [key for key in ("HVE", "YPOC", "YVAL") if key in str(description).upper()]
    return "+".join(matches) if matches else "other"


def tags(row: dict) -> dict:
    date = datetime.fromisoformat(row["date"][:10])
    year = date.year
    entry_time = str(row.get("entry_time") or "")
    time = entry_time[11:16] if "T" in entry_time or " " in entry_time else entry_time[:5]
    delay = row.get("confirmation_delay")
    result = {
        "year": f"{year}" + (" (partial)" if year in (2022, 2026) else ""),
        "split": "development" if year <= 2024 else "validation" if year == 2025 else "temporal_test",
        "direction": row.get("direction") or "no_candidate",
        "entry_time": time or "no_fill", "weekday": date.strftime("%A"),
        "entry_policy": row["entry_policy"], "mask": row["mask"],
        "confirmation_delay": str(int(delay)) if delay is not None else "unavailable",
        "pivot_type": _pivot_type(row.get("pivot_description")),
        "pivot_kind": row.get("pivot_kind") or "unknown",
        "opening_pivot_position": row.get("opening_pivot_position") or "unknown",
        "opening_cloud_position": row.get("opening_cloud_position") or "unknown",
        "target_identity": (f"{int(row['target_ordinal'])}: {row.get('target_description') or 'unknown'}"
                            if row.get("target_ordinal") is not None else "fixed_2r" if row["exit_policy"] == "fixed_2r" else "unavailable"),
        "exit_reason": row.get("exit_reason") or "no_fill",
        "execution_ambiguity": "ambiguous" if row.get("ambiguity") else "unambiguous" if row.get("trade") else "no_fill",
    }
    result.update({("prior_known_volatility" if key == "preopen_atr14" else key): _bin(row.get(key), edges, zero=key == "pivot_width") for key, edges in BINS.items()})
    return result


def _load_daily(stage: Path) -> list[dict]:
    daily = read_rows(stage / "daily.csv")
    if not daily:
        raise ValueError("daily.csv must contain every eligible date × 16 variants")
    seen: set[tuple] = set()
    by_date: dict[str, set] = {}
    for row in daily:
        key = (row["date"], *variant(row))
        if key in seen:
            raise ValueError(f"duplicate daily identity: {key}")
        seen.add(key)
        by_date.setdefault(row["date"], set()).add(variant(row))
        if not row.get("trade") and row.get("net_dollars") not in (None, 0):
            raise ValueError("non-trades must be zero or unavailable")
    if any(variants != set(VARIANTS) for variants in by_date.values()):
        raise ValueError("every eligible session requires all sixteen variants")
    return daily


def summarize(stage: str | Path) -> dict:
    """Aggregate saved baseline ledgers once, after the executed protocol freeze."""
    stage = Path(stage)
    daily = _load_daily(stage)
    tables = stage / "tables"
    groups = {v: [r for r in daily if variant(r) == v] for v in VARIANTS}
    summary = [{**_identity(v), **summarize_group(rows)} for v, rows in groups.items()]
    write_rows(tables / "variant_summary.csv", summary)
    annual = []
    split_summary = []
    for v, rows in groups.items():
        for year in sorted({row["date"][:4] for row in rows}):
            chosen = [r for r in rows if r["date"].startswith(year)]
            annual.append({**_identity(v), "year": year, "partial_year": year in ("2022", "2026"),
                           "split": tags(chosen[0])["split"], **summarize_group(chosen)})
        for split in ("development", "validation", "temporal_test"):
            chosen = [r for r in rows if tags(r)["split"] == split]
            split_summary.append({**_identity(v), "split": split, **summarize_group(chosen)})
    write_rows(tables / "annual.csv", annual)
    write_rows(tables / "splits.csv", split_summary)
    comparisons = []
    for mask in MASKS:
        for exit_policy in EXIT_POLICIES:
            for both in (False, True):
                comparisons.append({"mask": mask, "exit_policy": exit_policy,
                                    **paired(groups[("early", mask, exit_policy)], groups[("confirmed", mask, exit_policy)], both_filled=both)})
    write_rows(tables / "paired_entries.csv", comparisons)
    primary = []
    early, confirmed = groups[PRIMARY], groups[("confirmed", "A", "fixed_2r")]
    for split in ("pooled_exploratory", "development", "validation", "temporal_test"):
        select = lambda row: split == "pooled_exploratory" or tags(row)["split"] == split
        primary.append({"cohort": split, **paired([r for r in early if select(r)], [r for r in confirmed if select(r)], require_complete=True)})
    write_rows(tables / "primary_comparison.csv", primary)
    secondary = []
    for v in VARIANTS:
        if v == PRIMARY:
            continue
        contrast = paired(groups[v], groups[PRIMARY])
        secondary.append({**_identity(v), **contrast, "contrast": "variant_minus_early_A_fixed_2r"})
    for row, adjusted in zip(secondary, holm([r["bootstrap_tail_probability"] for r in secondary])):
        row["holm_tail_probability"] = adjusted
    write_rows(tables / "secondary_comparisons.csv", secondary)
    targets = []
    for entry in ENTRY_POLICIES:
        for mask in MASKS:
            for both in (False, True):
                comparison = paired(groups[(entry, mask, "verne")], groups[(entry, mask, "fixed_2r")], both_filled=both)
                targets.append({"entry_policy": entry, "mask": mask, "contrast": "verne_minus_fixed_2r",
                                **comparison, "verne_unavailable": sum(r["net_dollars"] is None for r in groups[(entry, mask, "verne")])})
    write_rows(tables / "target_comparison.csv", targets)
    cut_rows = []
    for v, rows in groups.items():
        # Fixed named views only; no unrestricted cross product.
        cuts: dict[tuple, list] = {}
        for row in rows:
            row_tags = tags(row)
            for name, value in row_tags.items():
                cuts.setdefault((name, value), []).append(row)
            cuts.setdefault(("year_by_direction", row_tags["year"] + " | " + row_tags["direction"]), []).append(row)
            cuts.setdefault(("entry_by_mask", row["entry_policy"] + " | " + row["mask"]), []).append(row)
        for (cut, cell), chosen in sorted(cuts.items()):
            cut_rows.append({**_identity(v), "cut": cut, "cell": cell, **summarize_group(chosen)})
    write_rows(tables / "prespecified_cuts.csv", cut_rows)
    primary_cuts = [r for r in cut_rows if (r["entry_policy"], r["mask"], r["exit_policy"]) == PRIMARY]
    selected_cut_columns = ["cut", "cell", "eligible_sessions", "trades", "net_per_session", "expectancy_dollars", "trade_ci_low", "trade_ci_high", "expectancy_r", "weak_evidence"]
    write_rows(tables / "primary_cuts.csv", primary_cuts, selected_cut_columns)
    equity = []
    for v, rows in groups.items():
        cumulative, peak = 0., 0.
        undefined = False
        for row in sorted(rows, key=lambda r: r["date"]):
            value = row.get("net_dollars")
            undefined |= value is None
            if value is not None:
                cumulative += value
            peak = max(peak, cumulative)
            equity.append({**_identity(v), "date": row["date"], "net_dollars": value,
                           "equity_dollars": None if undefined else cumulative,
                           "drawdown_dollars": None if undefined else cumulative - peak})
    write_rows(tables / "equity.csv", equity)
    examples = []
    for label in ("win", "loss", "failed_confirmation", "invalidated"):
        eligible = []
        for row in daily:
            if row["mask"] != "A" or row["exit_policy"] != "fixed_2r":
                continue
            if label in ("win", "loss") and row["entry_policy"] == "early" and row.get("trade"):
                if (label == "win" and row["net_dollars"] > 0) or (label == "loss" and row["net_dollars"] < 0):
                    eligible.append(row)
            elif label == "failed_confirmation" and row["entry_policy"] == "confirmed" and row.get("reason") == "confirmation_expired" and not row.get("trade"):
                eligible.append(row)
            elif label == "invalidated" and row.get("reason") in ("structural_invalidation", "entry_open_beyond_stop") and not row.get("trade"):
                eligible.append(row)
        chosen = sorted(eligible, key=lambda r: (r["date"], r.get("candidate_id") or ""))
        examples.append({"example_class": label, "available": bool(chosen), **(chosen[0] if chosen else {})})
    write_rows(tables / "examples.csv", examples)
    sensitivities = read_rows(stage / "sensitivities.csv")
    robustness = []
    for name in sorted({row["sensitivity"] for row in sensitivities}):
        scenario = [row for row in sensitivities if row["sensitivity"] == name]
        a = [row for row in scenario if row["entry_policy"] == "early"]
        b = [row for row in scenario if row["entry_policy"] == "confirmed"]
        robustness.append({"sensitivity": name, **paired(a, b, require_complete=True),
                           "early_trades": sum(bool(row.get("trade")) for row in a),
                           "confirmed_trades": sum(bool(row.get("trade")) for row in b)})
    if robustness:
        write_rows(tables / "robustness.csv", robustness)
    metrics = {"schema": "es-opening-pivot-cloud-statistics/v1", "seed": SEED, "resamples": RESAMPLES,
               "primary": primary, "variants": summary,
               "qualification": "Conditional retrospective research; historical level available_at is unverified. Native TradingView parity is unestablished.",
               "tables": {p.name: _hash(p) for p in sorted(tables.glob("*.csv"))}}
    _write_json(stage / "metrics.json", metrics)
    return metrics


def _saved_table(stage: Path, name: str) -> list[dict]:
    return _saved_csv(stage / "tables" / name)


def _saved_csv(path: Path) -> list[dict]:
    # Aggregate CSV types are inferred by column value, preserving textual IDs.
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key, value in row.items():
            if value == "":
                row[key] = None
            elif value in ("True", "False"):
                row[key] = value == "True"
            elif key not in {"year", "date", "cell"}:
                try:
                    row[key] = float(value)
                except ValueError:
                    pass
    return rows


def verify_saved_projection(stage: str | Path) -> dict:
    """Re-read saved source bytes and output cells, without recalculating research."""
    stage = Path(stage)
    mapping = json.loads((stage / "source-map.json").read_text())
    publication = json.loads((stage / "publication.json").read_text())
    if mapping["publication_id"] != publication["id"] or mapping["source_run_id"] != publication["source"]["runId"]:
        raise ValueError("publication/source-map identity mismatch")
    for source in mapping["sources"]:
        if _hash(stage / source["artifact"]) != source["sha256"]:
            raise ValueError("saved source hash mismatch: " + source["artifact"])
    sections = {section["id"]: section for section in publication["sections"]}
    cache = {}
    for binding in mapping["bindings"]:
        artifact = binding["source_artifact"]
        if artifact not in cache:
            cache[artifact] = _saved_csv(stage / artifact)
        value = cache[artifact][binding["source_row"]].get(binding["source_column"])
        actual = sections[binding["section"]]["rows"][binding["row"]][binding["column"]]
        if actual != value or binding["value"] != value:
            raise ValueError("saved source-cell mismatch")
    for projection in mapping["download_projections"]:
        source = projection["source"]
        if _hash(stage / source["artifact"]) != source["sha256"]:
            raise ValueError("download source hash mismatch")
        rows = _saved_csv(stage / source["artifact"])
        selected = [{key: row.get(key) for key in projection["columns"]} for row in rows]
        if _saved_csv(stage / projection["path"]) != selected:
            raise ValueError("download source-cell mismatch")
    return {"status": "passed", "cells": len(mapping["bindings"]), "downloads": len(mapping["download_projections"])}


def _figures(stage: Path) -> list[dict]:
    """Render saved coordinates as SVG, then rasterize with installed Sharp.

    The Narada npm lock supplies this presentation dependency; neither rendering
    nor the website imports the numerical engine. SVG sources remain in evidence.
    """
    directory = stage / "figures"
    directory.mkdir(exist_ok=True)
    workspace = Path(__file__).resolve().parents[3]
    sharp = Path(os.environ.get("ABACUS_SHARP_PATH", str(workspace / "apps/narada/node_modules/sharp")))
    node = os.environ.get("ABACUS_CHART_NODE") or shutil.which("node")
    if not node or not (sharp / "package.json").exists():
        raise RuntimeError("Chart rendering requires Node 24 and installed Narada Sharp; set ABACUS_CHART_NODE/ABACUS_SHARP_PATH if needed")
    node_version = subprocess.check_output([node, "--version"], text=True).strip()
    if not node_version.startswith("v24."):
        raise RuntimeError("Chart rendering requires Node 24; found " + node_version)
    sharp_version = json.loads((sharp / "package.json").read_text())["version"]
    commands = []

    def text(x, y, value, size=16, color="#304158", anchor="start"):
        return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(value))}</text>'

    def line(x1, y1, x2, y2, color="#d9e0e9", width=1, dash=""):
        return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{width}"' + (f' stroke-dasharray="{dash}"' if dash else '') + '/>'

    def save(filename, elements, width, height):
        source = directory / (filename + ".svg")
        output = directory / (filename + ".png")
        source.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#fff"/><g font-family="Arial, Helvetica, sans-serif">' + "".join(elements) + '</g></svg>')
        script = "const sharp=require(process.argv[1]);sharp(process.argv[2]).png().toFile(process.argv[3]).catch(e=>{console.error(e);process.exit(1)});"
        command = [node, "-e", script, str(sharp), str(source), str(output)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        commands.append({"argv": command, "svg": source.relative_to(stage).as_posix(), "svg_sha256": _hash(source),
                         "png": output.relative_to(stage).as_posix(), "png_sha256": _hash(output)})

    saved = _saved_table(stage, "equity.csv")
    selected = {policy: [row for row in saved if row["entry_policy"] == policy and row["mask"] == "A" and row["exit_policy"] == "fixed_2r"] for policy in ENTRY_POLICIES}
    elements = [text(34, 38, "Primary model: saved equity and drawdown", 25),
                text(34, 65, "One ES contract · net dollars · EMA mask A · fixed 2R", 15)]
    for panel, key, title in ((0, "equity_dollars", "Cumulative net equity"), (1, "drawdown_dollars", "Drawdown from prior peak")):
        x0, x1, y0, y1 = 120, 1150, 110 + panel * 300, 340 + panel * 300
        values = [row[key] for rows in selected.values() for row in rows if row.get(key) is not None] + [0]
        low, high = min(values), max(values)
        span = max(high - low, 1)
        low, high = low - .08 * span, high + .08 * span
        py = lambda value: y1 - (value - low) / (high - low) * (y1 - y0)
        elements.append(text(x0, y0 - 18, title, 18))
        for tick in np.linspace(low, high, 5):
            y = py(tick)
            elements += [line(x0, y, x1, y), text(x0 - 12, y + 5, f"{tick:,.0f}", 13, anchor="end")]
        elements.append(line(x0, py(0), x1, py(0), "#9ca9b8"))
        for policy, color in (("early", "#276fbf"), ("confirmed", "#d27624")):
            rows = selected[policy]
            if not rows:
                continue
            points = [(x0, py(0))] + [(x0 + (index + 1) / max(len(rows), 1) * (x1 - x0), py(row[key])) for index, row in enumerate(rows) if row.get(key) is not None]
            elements.append('<polyline fill="none" stroke="' + color + '" stroke-width="2" points="' + ' '.join(f'{x:.2f},{y:.2f}' for x, y in points) + '"/>')
        rows = selected["early"]
        if rows:
            indices = sorted(set((0, len(rows) // 4, len(rows) // 2, 3 * len(rows) // 4, len(rows) - 1)))
            for index in indices:
                x = x0 + (index + 1) / len(rows) * (x1 - x0)
                elements.append(text(x, y1 + 23, rows[index]["date"], 12, anchor="middle"))
    elements += [line(785, 58, 815, 58, "#276fbf", 3), text(825, 63, "early", 15),
                 line(920, 58, 950, 58, "#d27624", 3), text(960, 63, "confirmed", 15),
                 text(35, 702, "Chronological saved session outcomes; initial equity peak is zero. Source: tables/equity.csv", 13)]
    save("primary-equity", elements, 1200, 725)
    figures = [{"id": "equity-figure", "kind": "figure", "title": "Equity and drawdown",
                "path": "figures/primary-equity.png", "alt": "Saved chronological net dollar equity and drawdown for early and confirmed primary variants.",
                "caption": "One ES contract, mask A, fixed 2R. Reference fees and slippage are included. Saved tables/equity.csv is the source.", "referenceIds": ["equity"]}]
    examples = read_rows(stage / "tables/examples.csv")
    bars = read_rows(stage / "chart_bars.csv")
    if bars:
        elements = [text(30, 35, "Deterministic audited examples", 25), text(30, 61, "Earliest saved date and candidate ID in each declared class; prices remain unadjusted", 14)]
        for panel, example in enumerate(examples):
            column, row = panel % 2, panel // 2
            left, top = 90 + column * 620, 125 + row * 395
            right, bottom = left + 480, top + 270
            all_daybars = [bar for bar in bars if bar["date"] == example.get("date")]
            daybars = sorted([bar for bar in all_daybars if all(bar.get(key) is not None and math.isfinite(float(bar[key])) for key in ("open", "high", "low", "close"))], key=lambda bar: str(bar.get("time", bar.get("timestamp", ""))))
            label = example["example_class"].replace("_", " ")
            elements.append(text(left, top - 26, label + (" — " + example["date"] if daybars else " — unavailable"), 19))
            if not daybars:
                elements.append(text(left + 120, top + 120, "No eligible saved example", 16))
                continue
            prices = [bar[key] for bar in daybars for key in ("high", "low")]
            prices += [example[key] for key in ("pivot_lower", "pivot_upper", "entry_price", "stop_price", "target_price") if example.get(key) is not None]
            low, high = min(prices), max(prices)
            span = max(high - low, 1)
            low, high = low - .08 * span, high + .08 * span
            py = lambda value: bottom - (value - low) / (high - low) * (bottom - top)
            step = (right - left) / len(daybars)
            px = lambda index: left + (index + .5) * step
            for tick in np.linspace(low, high, 5):
                y = py(tick)
                elements += [line(left, y, right, y), text(left - 8, y + 4, f"{tick:,.1f}", 12, anchor="end")]
            if example.get("pivot_lower") is not None:
                y = py(example["pivot_upper"])
                h = max(2, py(example["pivot_lower"]) - y)
                elements.append(f'<rect x="{left}" y="{y:.2f}" width="{right-left}" height="{h:.2f}" fill="#7857a8" opacity=".18"/>')
            for index, bar in enumerate(daybars):
                color = "#23936e" if bar["close"] >= bar["open"] else "#c74a49"
                x = px(index)
                elements.append(line(x, py(bar["low"]), x, py(bar["high"]), color, 1.2))
                body_top, body_bottom = py(max(bar["open"], bar["close"])), py(min(bar["open"], bar["close"]))
                elements.append(f'<rect x="{x-step*.25:.2f}" y="{body_top:.2f}" width="{step*.5:.2f}" height="{max(1.5,body_bottom-body_top):.2f}" fill="{color}"/>')
                timestamp = str(bar.get("time", bar.get("timestamp", "")))
                time = timestamp[11:16] if len(timestamp) > 10 else timestamp[:5]
                elements.append(text(x, bottom + 20, time, 11, anchor="middle"))
            for key, color in (("ema20", "#357abb"), ("ema50", "#b77628")):
                points = ' '.join(f'{px(i):.2f},{py(bar[key]):.2f}' for i, bar in enumerate(daybars) if bar.get(key) is not None)
                elements.append(f'<polyline fill="none" stroke="{color}" stroke-width="1.8" points="{points}"/>')
            for key, color in (("entry_price", "#262626"), ("stop_price", "#b42222"), ("target_price", "#24854b")):
                if example.get(key) is not None:
                    elements += [line(left, py(example[key]), right, py(example[key]), color, 1, "5,4"), text(right + 3, py(example[key]) + 4, key.replace("_price", ""), 10, color)]
            elements.append(text(left, bottom + 45, str(example.get("reason") or example.get("exit_reason") or "") + " · " + str(example.get("candidate_id") or ""), 11))
            if len(daybars) != len(all_daybars):
                elements.append(text(left, bottom + 62, f"{len(all_daybars)-len(daybars)} unavailable OHLC slots omitted; no interpolation", 11))
        save("audited-examples", elements, 1280, 890)
        figures.append({"id": "examples-figure", "kind": "figure", "title": "Deterministic audited examples",
                        "path": "figures/audited-examples.png", "alt": "Earliest saved win, loss, failed confirmation and invalidated setup with unadjusted candles, cloud and frozen levels.",
                        "caption": "Earliest date and candidate ID per declared class; absent classes remain absent. These examples describe paths and do not estimate performance.", "referenceIds": ["examples"]})
    _write_json(stage / "chart-renderer.json", {"schema": "es-opening-pivot-cloud-chart-renderer/v1", "node": node_version,
        "sharp": sharp_version, "narada_package_lock_sha256": _hash(workspace / "apps/narada/package-lock.json"), "commands": commands,
        "qualification": "Saved-coordinate SVG presentation only; no signal, feature or outcome recomputation."})
    return figures


def _number(value: Any, digits: int = 2) -> str:
    return "undefined" if value is None else f"{value:,.{digits}f}"


def report(stage: str | Path, study_id: str, run_id: str, *, publication_id: str | None = None,
           published_at: str | None = None) -> dict:
    """Render frozen saved statistics; does not re-execute signals or outcomes."""
    stage = Path(stage)
    if not (stage / "metrics.json").exists():
        raise ValueError("summarize(stage) must save statistics before report(stage,...)")
    compact = re.sub(r"[^a-z0-9]", "", run_id.lower())
    publication_id = publication_id or f"es-opening-pivot-cloud-26-v1-{compact}"
    summary = _saved_table(stage, "variant_summary.csv")
    primary = _saved_table(stage, "primary_comparison.csv")
    test = next(r for r in primary if r["cohort"] == "temporal_test")
    pooled = next(r for r in primary if r["cohort"] == "pooled_exploratory")
    early = next(r for r in summary if variant(r) == PRIMARY)
    confirmed = next(r for r in summary if variant(r) == ("confirmed", "A", "fixed_2r"))
    figures = _figures(stage)
    sections = []
    bindings = []
    source_files: set[str] = {"metrics.json", "tables/equity.csv", "tables/examples.csv"}
    if (stage / "chart_bars.csv").exists():
        source_files.add("chart_bars.csv")

    def text(identity: str, title: str, body: str, refs: list[str] | None = None) -> None:
        section = {"id": identity, "title": title, "kind": "text", "body": body}
        if refs:
            section["referenceIds"] = refs
        sections.append(section)

    def table(identity: str, title: str, filename: str, keys: list[str], *, where=None,
              description: str | None = None) -> None:
        rows = _saved_table(stage, filename)
        chosen = [(i, row) for i, row in enumerate(rows) if where is None or where(row)]
        path = f"tables/{filename}"
        source_files.add(path)
        section = {"id": identity, "kind": "table", "title": title,
                   "columns": [{"key": key, "label": key.replace("_", " "), **({"format": "number", "precision": 2} if any(isinstance(row.get(key), (int, float)) and not isinstance(row.get(key), bool) for _, row in chosen) else {})} for key in keys],
                   "rows": [{key: row.get(key) for key in keys} for _, row in chosen]}
        if description:
            section["description"] = description
        if len(chosen) > 100 and "cut" in keys:
            section["rowFilters"] = [{"key": "cut", "label": "Prespecified cut", "defaultValue": "direction"}]
        dollar_keys = {"net_per_session", "expectancy_dollars", "difference_dollars", "left_mean", "right_mean", "ci_low", "ci_high", "week_ci_low", "week_ci_high", "session_ci_low", "session_ci_high", "trade_ci_low", "trade_ci_high", "max_drawdown_dollars", "net_dollars"}
        proportions = {"participation", "win_rate", "coincident_rate", "confirmation_rate", "bootstrap_tail_probability", "holm_tail_probability"}
        for column in section["columns"]:
            if column["key"] in dollar_keys:
                column["unit"] = "USD"
            elif column["key"] in proportions:
                column["format"] = "percent"
                column["precision"] = 1
            elif column["key"] == "expectancy_r":
                column["unit"] = "R"
            if column["key"] == "confirmation_rate":
                column["label"] = "confirmation fill rate"
        sections.append(section)
        for public_row, (source_row, row) in enumerate(chosen):
            for key in keys:
                bindings.append({"section": identity, "row": public_row, "column": key,
                                 "source_artifact": path, "source_row": source_row,
                                 "source_column": key, "value": row.get(key)})

    overview = (
        "Standard ES 5-minute pivot/cloud reaction candidates between 09:30 and 10:00 New York; "
        "early next-open versus pivot-and-cloud-confirmed next-open entries, four frozen EMA masks and two exits. "
        "No CVD is used. Primary inference uses mask A, fixed 2R, one contract and the first daily candidate. "
        "All saved Verne historical available_at values are unverified/null: this is conditional retrospective research, "
        "not evidence that the levels were obtainable before each historical open. The verified availability cohort is empty. "
        "The inspiration chart date 2026-09-15 was visually exposed before this study. Regular input gates exclude it because its quoted contract does not match the stitched price contract and published feature readiness is below 250 bars; no date-specific exclusion is applied. "
        "Native TradingView parity has not been established."
    )
    text("tested", "What was tested and what the evidence means", overview)
    waterfall_source = stage / "waterfall.csv"
    if waterfall_source.exists():
        shutil.copyfile(waterfall_source, stage / "tables" / "coverage_waterfall.csv")
        waterfall = _saved_table(stage, "coverage_waterfall.csv")
        if waterfall:
            table("coverage-table", "Coverage and exclusion waterfall by year", "coverage_waterfall.csv", list(waterfall[0])[:12])
    text("coverage-context", "Actual eligible coverage", (
        f"The regular audited gates retain {int(early['eligible_sessions'])} input-eligible sessions from {early.get('start_date')} through {early.get('end_date')}. "
        "Partial years are 2022 and 2026. The waterfall preserves source-level coverage, unique plans, duplicate exclusions, contract matches, opening bars, readiness, execution completeness and final eligibility. "
        "All exclusion checks are retrospective input-quality rules; unverified historical level availability remains a separate qualification."
    ))
    text("primary-finding", "Primary comparison", (
        f"Input-eligible pooled sessions: {int(early['eligible_sessions'])}. Early trades: {int(early['trades'])}; "
        f"confirmed trades: {int(confirmed['trades'])}. Early net dollars/session: {_number(early['net_per_session'])}; "
        f"confirmed: {_number(confirmed['net_per_session'])}. Net dollars/trade: early {_number(early['expectancy_dollars'])}, "
        f"confirmed {_number(confirmed['expectancy_dollars'])}. Pooled exploratory early-minus-confirmed net dollars/session: "
        f"{_number(pooled['difference_dollars'])}, day bootstrap 95% interval [{_number(pooled['ci_low'])}, {_number(pooled['ci_high'])}]. "
        f"Locked 2026 temporal-test mean dollars/session: early {_number(test['left_mean'])}, confirmed {_number(test['right_mean'])}; "
        f"difference {_number(test['difference_dollars'])}, interval "
        f"[{_number(test['ci_low'])}, {_number(test['ci_high'])}]. "
        "Intervals use 4,000 fixed-seed session resamples; week-cluster intervals are saved separately. "
        "This comparison includes zero on genuine no-trade days. Undefined outcomes remain unavailable. "
        "A positive point estimate alone does not establish a profitable strategy; annual consistency, temporal test, costs and uncertainty must agree."
    ), ["primary"])
    table("primary-table", "Primary paired comparison and temporal splits", "primary_comparison.csv",
          ["cohort", "paired_sessions", "both_filled", "left_mean", "right_mean", "difference_dollars", "ci_low", "ci_high", "week_ci_low", "week_ci_high", "coincident_rate", "confirmation_rate"],
          description="Left is early; right is confirmed. Dollar means include genuine zero-trade days. Confirmation fill rate is confirmed-policy fills divided by common candidates; it includes filtering, invalidation, cutoff and availability attrition. It is not a raw confirmation-close event rate.")
    table("variants-table", "Sixteen declared variants", "variant_summary.csv",
          ["entry_policy", "mask", "exit_policy", "eligible_sessions", "unavailable_sessions", "trades", "participation", "net_per_session", "expectancy_r", "win_rate", "profit_factor", "max_drawdown_dollars"],
          description="Masks: A no trend filter; B ordering; C slope; D both. A filtered first candidate is never replaced. Verne availability is explicit; null is not zero.")
    table("filter-table", "EMA filters: participation and uncertainty", "variant_summary.csv",
          ["entry_policy", "mask", "trades", "participation", "net_per_session", "session_ci_low", "session_ci_high", "expectancy_dollars", "expectancy_r", "weak_evidence"],
          where=lambda r: r["exit_policy"] == "fixed_2r",
          description="Filter comparisons share the first daily candidate; higher per-trade expectancy can accompany lower daily participation and weaker daily evidence.")
    filter_sentences = []
    for policy in ENTRY_POLICIES:
        baseline = next(r for r in summary if variant(r) == (policy, "A", "fixed_2r"))
        cells = []
        for mask in ("B", "C", "D"):
            row = next(r for r in summary if variant(r) == (policy, mask, "fixed_2r"))
            delta = row["net_per_session"] - baseline["net_per_session"] if row["net_per_session"] is not None and baseline["net_per_session"] is not None else None
            cells.append(f"{mask}: {int(row['trades'])}/{int(row['eligible_sessions'])} sessions traded, {_number(row['net_per_session'])} dollars/session ({_number(delta)} versus A), 95% interval [{_number(row['session_ci_low'])}, {_number(row['session_ci_high'])}]")
        filter_sentences.append(policy + " — " + "; ".join(cells) + ".")
    text("filter-finding", "Do trend filters improve daily results?", " ".join(filter_sentences) +
         " These are observed pooled point estimates, not demonstrated filter superiority. Filtering always acts on the common first candidate, so participation and dollars/session must be assessed together. The temporal-test source table tables/splits.csv and the fifteen-contrast secondary Holm family qualify any apparent gain; no filter is selected from the most favorable cut. Held-out temporal results may differ from pooled results.")
    table("target-table", "Verne minus 2R on common defined days", "target_comparison.csv",
          ["entry_policy", "mask", "population", "paired_sessions", "verne_unavailable", "difference_dollars", "ci_low", "ci_high", "week_ci_low", "week_ci_high"],
          description="Both target policies are evaluated on their common defined daily population. Full-coverage figures and target-unavailable counts remain separate.")
    table("annual-table", "Annual results: partial 2022 and partial 2026", "annual.csv",
          ["entry_policy", "year", "split", "eligible_sessions", "trades", "net_per_session", "session_ci_low", "session_ci_high", "expectancy_r", "weak_evidence"],
          where=lambda r: r["mask"] == "A" and r["exit_policy"] == "fixed_2r")
    table("cuts-table", "Prespecified descriptive cuts: early, A, fixed 2R", "primary_cuts.csv",
          ["cut", "cell", "eligible_sessions", "trades", "net_per_session", "expectancy_dollars", "trade_ci_low", "trade_ci_high", "expectancy_r", "weak_evidence"],
          description="Fixed bins were declared before outcomes. Cells overlap and are correlated. Fewer than 30 trades is weak descriptive evidence; cells are not ranked as discoveries. Complete sixteen-variant cuts are retained in the source run.")
    table("secondary-table", "Secondary contrasts and multiplicity", "secondary_comparisons.csv",
          ["entry_policy", "mask", "exit_policy", "paired_sessions", "difference_dollars", "ci_low", "ci_high", "bootstrap_tail_probability", "holm_tail_probability"],
          description="Variant minus early/A/2R on common defined days. Holm family contains fifteen prespecified contrasts. These descriptive bootstrap sign-tail probabilities are not randomization-test p-values; cuts carry no inferential discovery claims.")
    if (stage / "tables" / "robustness.csv").exists():
        robust = _saved_table(stage, "robustness.csv")
        keys = ["sensitivity", "paired_sessions", "left_mean", "right_mean", "difference_dollars", "ci_low", "ci_high", "week_ci_low", "week_ci_high", "early_trades", "confirmed_trades"] if robust else []
        if keys:
            table("robustness-table", "One-factor primary sensitivities", "robustness.csv", keys)
    sections.extend(figures)
    table("examples-table", "Audited example identities", "examples.csv",
          ["example_class", "available", "date", "candidate_id", "direction", "entry_time", "exit_reason", "reason", "net_dollars"])
    text("rules", "Causal setup and execution rules", (
        "Reset setup state at 09:30. A prior close establishes approach direction. Freeze tick-rounded delta=max(1 point,0.10×prior ATR14) at first return touch. "
        "The return and next two bars must touch pivot and cloud, with separation no greater than delta on an interaction bar. "
        "A directional reaction closes beyond the cloud and creates the common candidate. Early fills next open; confirmed waits for a close beyond pivot and cloud, then fills next open before 10:00. "
        "Freeze the structural stop at reaction. Primary exit is 2R or stop with 11:00 flatten; saved Verne targets use the nearest profitable near edge among the first two targets. "
        "Use 1-minute sequencing, adverse first for unresolved stop/target ambiguity and worse-opening gap stop fills. "
        "Reference costs assume $5 round-trip fees, one adverse market/stop tick, and one tick target trade-through. Unadjusted ES tick=$12.50; point=$50."
    ))
    sections[-1]["patternId"] = "model-schematic"
    sections[-1]["patternFocus"] = "Mirrored long support and short rejection; early and confirmed may enter together when the reaction already closes beyond pivot and cloud."
    text("limitations", "Uncertainty, qualifications and reproduction", (
        "2022–2024 is development, 2025 validation and 2026 the locked retrospective temporal test. Parameters were hypotheses; no outcome optimization is claimed. "
        "Completeness through 11:00 is assessed retrospectively. Contract mismatches, duplicate daily plans and published feature unreadiness are excluded by the frozen audit, without replacing the price contract or weakening readiness. "
        "No data-readiness alternative is substituted for the primary release. Cost, stop-buffer and proximity checks are bounded one-factor sensitivities. "
        "Saved tables retain outcome distributions, stop distance, MAE, MFE, holding time, ambiguity optimistic bounds, all declared cuts and paired both-filled outcomes; "
        "the both-filled subset omits missed opportunities. Full-period pooled cuts are exploratory and correlated. Undefined ratios, absent targets and missing outcomes remain undefined. "
        f"Source run: {run_id}. Reproduce with the exact commands and frozen input/config hashes in manifest.json and the retained source snapshot. "
        "summarize(stage) creates saved statistical evidence; report(stage,study_id,run_id) only renders that saved evidence. "
        "Hosted deployment is a separate action."
    ))
    references = []
    for identity, filename, title in (("primary", "primary_comparison.csv", "Primary paired comparisons"),
                                      ("equity", "equity.csv", "Chronological saved equity"),
                                      ("examples", "examples.csv", "Deterministic audited examples")):
        references.append({"id": identity, "kind": "saved-artifact", "label": title, "title": title,
                           "runId": run_id, "artifact": f"tables/{filename}", "sha256": _hash(stage / "tables" / filename)})
    downloads = []
    download_columns = {
        "variant_summary.csv": ["entry_policy", "mask", "exit_policy", "eligible_sessions", "unavailable_sessions", "trades", "participation", "net_per_session", "session_ci_low", "session_ci_high", "expectancy_dollars", "expectancy_r", "win_rate", "profit_factor", "max_drawdown_dollars"],
        "primary_comparison.csv": list(primary[0])[:24],
        "annual.csv": ["entry_policy", "mask", "exit_policy", "year", "split", "eligible_sessions", "trades", "net_per_session", "session_ci_low", "session_ci_high", "expectancy_r", "weak_evidence"],
        "primary_cuts.csv": list(_saved_table(stage, "primary_cuts.csv")[0]),
    }
    for filename, columns in download_columns.items():
        path = stage / "downloads" / filename
        rows = _saved_table(stage, filename)
        write_rows(path, rows, columns)
        source_files.add(f"tables/{filename}")
        downloads.append({"id": filename.removesuffix(".csv").replace("_", "-"), "path": f"downloads/{filename}",
                          "label": filename.replace("_", " "), "description": "Explicit saved summary projection; source cells are pinned in source-map.json.",
                          "population": "Input-eligible sessions in the pinned retrospective ES sample, with subset labels retained.",
                          "units": "US dollars per one ES contract; R uses frozen initial risk; proportions are fractions.",
                          "scope": "Prespecified saved summary only; no raw event or workspace data.",
                          "mediaType": "text/csv", "sha256": _hash(path), "rowCount": len(rows), "columns": columns,
                          "source": {"runId": run_id, "artifact": f"tables/{filename}", "sha256": _hash(stage / "tables" / filename)}})
    publication = {"schemaVersion": "1.1", "id": publication_id, "title": "ES Opening Pivot–Cloud Rejection/Support",
                   "summary": "Conditional retrospective ES research comparing early and pivot-confirmed opening reactions, four EMA masks and two exits. Historical level availability is unverified; saved temporal results, uncertainty and participation remain explicit.",
                   "publishedAt": published_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "source": {"producer": "sahadeva", "runId": run_id}, "sections": sections,
                   "references": references, "downloads": downloads,
                   "notes": ["Research evidence is conditional on saved daily levels. No verified historical pre-open-availability cohort exists.",
                             "Weak cells, correlated cuts and prior chart exposure limit inference. No favorable subgroup establishes a profitable strategy."]}
    schematic = {"id": "model-schematic", "title": "Opening pivot/cloud model — causal schematic",
                 "description": "Authored geometry on a normalized 0–100 scale; this is a rule illustration, not an empirical price path. Both directions require a completed reaction after pivot/cloud interaction.", "variants": []}
    for direction, geometry in (("long", ((78, 84, 68, 70), (70, 73, 45, 49), (49, 70, 46, 67), (67, 76, 62, 72))),
                                ("short", ((22, 32, 16, 30), (30, 55, 27, 51), (51, 54, 30, 33), (33, 38, 24, 28)))):
        schematic["variants"].append({"id": direction, "title": direction.title() + (" support" if direction == "long" else " rejection"),
            "description": "Approach, return, completed reaction, next-open entry. Confirmation may coincide with the reaction; otherwise wait at most three bars before the fill cutoff.",
            "candles": [{"id": "c" + str(index), "label": label, "open": o, "high": h, "low": l, "close": c,
                         "role": role} for index, ((o, h, l, c), label, role) in enumerate(zip(geometry, ("approach", "return", "reaction", "next open"), ("context", "context", "signal", "measured")))],
            "marks": [{"kind": "band", "startCandle": "c0", "endCandle": "c3", "label": "pivot zone", "low": 46, "high": 54},
                      {"kind": "band", "startCandle": "c1", "endCandle": "c3", "label": "EMA20/50 cloud", "low": 43, "high": 60},
                      {"kind": "span", "startCandle": "c1", "endCandle": "c2", "label": "return → completed reaction"}]})
    publication["patterns"] = [schematic]
    publication["patternOverviewId"] = "model-schematic"
    _write_json(stage / "publication.json", publication)
    source_map = {"schema": "es-opening-pivot-cloud-source-map/v1", "publication_id": publication_id, "source_run_id": run_id,
                  "study_id": study_id, "bindings": bindings,
                  "sources": [{"artifact": filename, "sha256": _hash(stage / filename)} for filename in sorted(source_files)],
                  "download_projections": [{"path": d["path"], "source": d["source"], "columns": d["columns"], "rows": "all in saved order; exact cells; numeric parsing only"} for d in downloads]}
    _write_json(stage / "source-map.json", source_map)
    # Verify projection cells from retained source bytes, separately from Narada.
    projection_check = verify_saved_projection(stage)
    _write_json(stage / "publication-verification.json", {"schema": "es-opening-pivot-cloud-publication/v1", "status": "passed", "result": "passed",
        "study_id": study_id, "source_run_id": run_id, "publication_id": publication_id,
        "checks": [{"name": "saved-table-cell-projection", "status": projection_check["status"], "passed": projection_check["status"] == "passed", "cells": projection_check["cells"]},
                   {"name": "selected-download-source-projections", "status": projection_check["status"], "passed": projection_check["status"] == "passed", "files": projection_check["downloads"]}],
        "qualification": "Producer cell verification only. Narada contract, browser layout and scientific checks are separate."})
    report_md = ["# ES Opening Pivot–Cloud Rejection/Support", "", f"Run: `{run_id}`", ""]
    report_html = ["<!doctype html><html><head><meta charset='utf-8'><title>ES Opening Pivot–Cloud</title><style>body{font:16px system-ui;max-width:1200px;margin:2rem auto;padding:1rem;color:#152235}table{border-collapse:collapse;font-size:13px}td,th{padding:.4rem;border:1px solid #ccd2da}figure img{max-width:100%}.table{overflow:auto}h2{margin-top:2.5rem}</style></head><body><h1>ES Opening Pivot–Cloud Rejection/Support</h1>"]
    for section in sections:
        report_md += ["## " + section["title"], ""]
        report_html.append("<h2>" + html.escape(section["title"]) + "</h2>")
        if section["kind"] == "text":
            report_md += [section["body"], ""]
            report_html.append("<p>" + html.escape(section["body"]) + "</p>")
        elif section["kind"] == "figure":
            report_md += [f"![{section['alt']}]({section['path']})", section.get("caption", ""), ""]
            report_html.append(f"<figure><img src='{section['path']}' alt='{html.escape(section['alt'], quote=True)}'><figcaption>{html.escape(section.get('caption',''))}</figcaption></figure>")
        else:
            keys = [col["key"] for col in section["columns"]]
            report_md += ["| " + " | ".join(keys) + " |", "| " + " | ".join("---" for _ in keys) + " |"]
            report_html.append("<div class='table'><table><thead><tr>" + "".join("<th>" + html.escape(key) + "</th>" for key in keys) + "</tr></thead><tbody>")
            for row in section["rows"]:
                display = [str(row.get(key)) if row.get(key) is not None else "undefined" for key in keys]
                report_md.append("| " + " | ".join(text.replace("|", "/") for text in display) + " |")
                report_html.append("<tr>" + "".join("<td>" + html.escape(text) + "</td>" for text in display) + "</tr>")
            report_md.append("")
            report_html.append("</tbody></table></div>")
    (stage / "report.md").write_text("\n".join(report_md) + "\n")
    (stage / "report.html").write_text("\n".join(report_html) + "</body></html>\n")
    (stage / "advice.md").write_text(
        f"# Advice — {run_id}\n\nConditional retrospective evidence only. Primary temporal-test early-minus-confirmed dollars/session is "
        f"{_number(test['difference_dollars'])}, 95% day interval [{_number(test['ci_low'])}, {_number(test['ci_high'])}]. "
        "Read tables/primary_comparison.csv, tables/variant_summary.csv, tables/secondary_comparisons.csv and bounded robustness together. "
        "No favorable cut establishes a profitable strategy. Historical pre-open level availability and native TradingView parity remain unverified.\n")
    future = Path("runs") / study_id / run_id
    outputs = [stage / name for name in ("publication.json", "source-map.json", "publication-verification.json")]
    outputs += [stage / s["path"] for s in sections if s["kind"] == "figure"] + [stage / d["path"] for d in downloads]
    outputs += [stage / "chart-renderer.json", *sorted((stage / "figures").glob("*.svg"))]
    _write_json(stage / "publication-manifest.json", {"publication_id": publication_id, "source_run_id": run_id, "study_id": study_id,
        "source_artifacts": [{"path": (future / name).as_posix(), "sha256": _hash(stage / name)} for name in sorted(source_files)],
        "outputs": [{"path": (future / path.relative_to(stage)).as_posix(), "sha256": _hash(path)} for path in outputs]})
    return publication
