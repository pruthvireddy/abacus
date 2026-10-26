"""Stage 1 presentation from explicitly saved evidence, with exact cell bindings.

This module never imports the study engine, re-scores paths, or reads market inputs.
Example selection is the predeclared descriptive projection of saved ledgers.
"""
from __future__ import annotations

import csv
import hashlib
import html
import importlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

STUDY = "21_ema_cloud_trend_follow_opportunity"
PRODUCTS = ("ES", "GC", "NQ")
INTERVALS = (3, 5)
TABLES = {
    "S1-T00": "S1-T00_coverage.csv",
    "S1-T01": "S1-T01_signal_flow.csv",
    "S1-T02": "S1-T02_horizon_scorecard.csv",
    "S1-T03": "S1-T03_quantiles.csv",
    "S1-T04": "S1-T04_stability.csv",
    "S1-T05": "S1-T05_calendar.csv",
    "S1-T06": "S1-T06_examples.csv",
}
EXAMPLE_CLASSES = ("typical", "high_adverse", "high_favorable", "rejected", "partial")
EXAMPLE_DEFINITION = {
    "horizon": 15, "direction": "All", "period": "2018–2020 development only",
    "typical": "completed H15 nearest pooled-side median signed terminal delta",
    "high_adverse": "completed H15 maximum MAE",
    "high_favorable": "completed H15 maximum MFE",
    "rejected": "earliest directed technical slow-touch candidate with accepted=false",
    "partial": "earliest accepted event with censored H15",
    "ties": "earliest signal open timestamp, then event_id; rejected uses signal_idx",
    "unavailable": "explicit unavailable row, with no replacement class",
}
LIMITS = (
    "2018–2020 development observations only; later-period outcomes remain reserved. "
    "Prior Abacus studies inspected some later market history, so this is not a pristine market holdout. "
    "Unadjusted same-contract prices; reference is confirmed signal close and the signal candle is excluded. "
    "MFE and MAE are path observations, not executable profits, stops or targets. "
    "Sparse cohorts have fewer than 100 completed events or 30 contributing sessions. "
    "Modeled completion is available_at; original vendor-receipt and mapping-arrival times are absent. "
    "Uncertified holiday/early-close sessions are excluded conservatively and reset feature history. "
    "Missing no-trade minutes cannot be distinguished reliably from source loss."
)
METHODS = (
    "EMA20/EMA50 cloud stays on five-minute closes. Fixed inclusive widths: ES 2.4, GC 2.0, NQ 10 points. "
    "Slow touches only, both directions, one signal per pullback, zero cooldown. "
    "A five-minute signal uses its current completed close-derived cloud; a three-minute signal freezes "
    "the latest scheduled cloud completed at its open. Missing latest features clear state. "
    "Features reset on rolls/unknown gaps and require 250 consecutive usable five-minute observations; "
    "known scheduled closures preserve same-contract state. Overlapping observations are retained. "
    "H counts scheduled active chart slots. H15 means 45 active minutes on 3m and 75 on 5m. "
    "Equal-active comparisons are 3m H20 versus 5m H12 (60 minutes), and 3m H50 versus 5m H30 (150). "
    "Actual elapsed minutes and closure-crossing support remain separate. "
    "Quantiles interpolate at p(n−1); top-tail cutoffs are percentiles, not tail averages. "
    "Terminal signs use strict zero; MFE>MAE uses epsilon 1e−10×max(1,MFE,MAE), with ties retained. "
    "Pointwise 95% uncertainty uses paired contiguous New York calendar-week blocks, four-week primary, "
    "10,000 resamples, seed 20261010; one/eight-week sensitivity remains descriptive. "
    "Event means and contributing-session balanced means have different denominators. "
    "Calendar labels use signal-open New York dates; weeks start Monday. Fixed time strata are "
    "Asia 18–03, Europe 03–09, US 09–16 and Late 16–18. Session balancing uses trading-session identity. "
    "No strategy selection or profitability estimate is implied."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        if not columns or len(columns) != len(set(columns)):
            raise ValueError(f"{path}: empty/duplicate CSV headers")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"{path}: malformed CSV row width")
    return columns, rows


def _numeric(raw: str):
    if raw == "":
        return None
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f"Non-finite saved numeric cell {raw!r}")
    return value


def _matches(row, selector):
    return all(str(row.get(key, "")) in [str(v) for v in values] for key, values in selector.items())


def _choose(path: Path, selector: dict) -> list[tuple[int, dict]]:
    _, rows = read_csv(path)
    chosen = [(i, row) for i, row in enumerate(rows, 1) if _matches(row, selector)]
    return chosen


def project_table(path: Path, *, columns: list[dict], selector: dict, section: str,
                  source_artifact: str) -> tuple[list[dict], list[dict]]:
    chosen = _choose(path, selector)
    if len(columns) > 12 or len(chosen) > 100:
        raise ValueError("Narada table exceeds 12-column/100-row bounds")
    output, bindings = [], []
    source_hash = sha256(path)
    for data_row, row in chosen:
        target = {}
        for column in columns:
            key = column["key"]
            if key not in row:
                raise ValueError(f"{path}: missing selected column {key}")
            raw = row[key]
            value = _numeric(raw) if "format" in column else (raw if raw != "" else None)
            target[key] = value
            bindings.append({"section": section, "output_row": len(output), "column": key,
                             "source_artifact": source_artifact, "source_sha256": source_hash,
                             "data_row_1_based": data_row, "row_id": row.get("row_id", ""),
                             "selector": selector, "source_raw": raw, "value": value,
                             "conversion": "finite_float_or_null" if "format" in column else "string_or_null"})
        output.append(target)
    return output, bindings


def project_download(stage: Path, table: Path, *, columns: list[str], selector: dict,
                     filename: str, run_id: str, download_id: str, description: str):
    chosen = _choose(table, selector)
    if not 1 <= len(chosen) <= 1000 or not 1 <= len(columns) <= 24:
        raise ValueError("Selected CSV exceeds allowed row/column bounds or is empty")
    target = stage / "downloads" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: row[key] for key in columns} for _, row in chosen)
    source_artifact = table.relative_to(stage).as_posix()
    declaration = {"id": download_id, "path": target.relative_to(stage).as_posix(),
                   "label": description, "description": "Exact saved summary strings selected before sealing.",
                   "population": "2018–2020 development, slow EMA touches under fixed gateways",
                   "units": "Raw points separately by product; shares remain ratios; blank cells are undefined.",
                   "scope": f"Selector {json.dumps(selector, sort_keys=True)}; ordered listed columns only.",
                   "mediaType": "text/csv", "columns": columns, "rowCount": len(chosen),
                   "sha256": sha256(target), "source": {"runId": run_id, "artifact": source_artifact,
                                                          "sha256": sha256(table)}}
    binding = {"download": download_id, "source_artifact": source_artifact,
               "source_sha256": sha256(table), "path": declaration["path"], "sha256": declaration["sha256"],
               "selector": selector, "columns": columns,
               "data_rows_1_based": [index for index, _ in chosen],
               "row_ids": [row.get("row_id", "") for _, row in chosen], "row_count": len(chosen)}
    return declaration, binding


def select_examples(technical: pd.DataFrame, events: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    """Frozen selection rule; no additional outcome calculations or later dates."""
    rows = []
    for product in PRODUCTS:
        for interval in INTERVALS:
            def cell(frame):
                if frame.empty:
                    return frame.copy()
                part = frame[(frame["product"] == product) & (frame["interval_minutes"] == interval)].copy()
                if len(part):
                    times = pd.to_datetime(part["timestamp"], utc=True).dt.tz_convert("America/New_York")
                    part = part[times.dt.year.between(2018, 2020)].copy()
                return part
            technical_cell, event_cell, outcome_cell = cell(technical), cell(events), cell(outcomes)
            primary = outcome_cell[outcome_cell.horizon == 15] if len(outcome_cell) else outcome_cell
            complete = primary[primary.status == "completed"].copy() if len(primary) else primary
            for example_class in EXAMPLE_CLASSES:
                chosen = None
                if example_class in ("typical", "high_adverse", "high_favorable") and len(complete):
                    cohort = complete.copy()
                    if example_class == "typical":
                        cohort["selection_score"] = (cohort.terminal_delta - cohort.terminal_delta.median()).abs()
                    elif example_class == "high_adverse":
                        cohort["selection_score"] = -cohort.mae
                    else:
                        cohort["selection_score"] = -cohort.mfe
                    chosen = cohort.sort_values(["selection_score", "timestamp", "event_id"], kind="stable").iloc[0]
                elif example_class == "partial" and len(primary):
                    cohort = primary[primary.status == "censored"]
                    if len(cohort):
                        chosen = cohort.sort_values(["timestamp", "event_id"], kind="stable").iloc[0]
                elif example_class == "rejected" and len(technical_cell):
                    cohort = technical_cell[technical_cell.technical_candidate.astype(bool) & ~technical_cell.accepted.astype(bool)]
                    if len(cohort):
                        chosen = cohort.sort_values(["timestamp", "signal_idx"], kind="stable").iloc[0]
                selection_id = f"S1-T06|{product}|{interval}m|{example_class}"
                row = {"row_id": selection_id, "selection_id": selection_id, "product": product,
                       "interval_minutes": interval, "example_class": example_class, "horizon": 15,
                       "selection_status": "selected" if chosen is not None else "unavailable",
                       "selection_rule": EXAMPLE_DEFINITION[example_class]}
                for key in ("event_id", "signal_idx", "timestamp", "contract", "side", "reference_price",
                            "ema20", "ema50", "mfe", "mae", "terminal_delta", "status", "censor_reason", "suppression_reason"):
                    value = chosen.get(key, None) if chosen is not None else None
                    if key == "reference_price" and chosen is not None:
                        value = chosen.get("reference_price", chosen.get("close", None))
                    row[key] = None if pd.isna(value) else value
                rows.append(row)
    return pd.DataFrame(rows)


def _column(key, label=None, *, numeric=False, percent=False, unit=None):
    result = {"key": key, "label": label or key.replace("_", " ").capitalize()}
    if numeric or percent:
        result.update(format="percent" if percent else "number", precision=3 if not percent else 1)
    if unit:
        result["unit"] = unit
    return result


def _table_paths(stage: Path, table_paths=None):
    paths = {name: stage / "tables" / filename for name, filename in TABLES.items()}
    if table_paths:
        paths.update({name: (Path(path) if Path(path).is_absolute() else stage / path)
                      for name, path in table_paths.items()})
    for path in paths.values():
        path.resolve().relative_to(stage.resolve())
        if not path.is_file():
            raise FileNotFoundError(f"Required saved Stage 1 table absent: {path}")
    return paths


def _figure_environment():
    packages = []
    for name in ("matplotlib", "contourpy", "cycler", "fontTools", "kiwisolver", "PIL", "pyparsing", "numpy", "pandas"):
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        packages.append({"module": name, "version": str(getattr(module, "__version__", "unknown")),
                         "module_file": str(path), "module_sha256": sha256(path)})
    return {"purpose": "saved-evidence raster rendering only; numerical scoring uses the locked environment",
            "executable": sys.executable, "python": sys.version, "packages": packages}


def render_figures(stage: Path, paths: dict[str, Path], *, example_paths: Path | None = None):
    """Plot exact saved table rows and selected saved candles; no path scoring."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
    figures = stage / "figures"
    figures.mkdir(exist_ok=True)
    score = pd.read_csv(paths["S1-T02"])
    quantiles = pd.read_csv(paths["S1-T03"])
    stability = pd.read_csv(paths["S1-T04"])
    calendar = pd.read_csv(paths["S1-T05"])
    bindings, sections = [], []

    def base(frame):
        mask = pd.Series(True, index=frame.index)
        for key, value in (("direction", "All"), ("unit", "points"), ("support", "all")):
            if key in frame:
                mask &= frame[key] == value
        return frame[mask].copy()

    def publish_figure(fig, filename, title, caption, sources):
        output = figures / filename
        fig.savefig(output, dpi=110, facecolor="white", metadata={"Software": "Abacus Stage 1 saved-evidence renderer"})
        plt.close(fig)
        if output.stat().st_size > 2 * 1024 * 1024:
            raise ValueError(f"Figure exceeds Narada per-image budget: {output}")
        figure_id = filename[:-4].replace("_", "-")
        sections.append({"id": figure_id, "kind": "figure", "title": title,
                         "path": f"figures/{filename}", "alt": title + "; six product/candle panels.", "caption": caption})
        source_bindings = []
        for path, frame, columns, selector in sources:
            source_bindings.append({"source_artifact": path.relative_to(stage).as_posix(),
                                    "source_sha256": sha256(path), "row_ids": frame.row_id.astype(str).tolist(),
                                    "columns": columns, "selector": selector})
        bindings.append({"figure": figure_id, "path": f"figures/{filename}", "sha256": sha256(output),
                         "sources": source_bindings, "transform": "direct numeric plotting of declared saved columns"})

    h = base(score).sort_values(["product", "interval_minutes", "horizon"])
    fig, axes = plt.subplots(3, 2, figsize=(11, 8), constrained_layout=True)
    for i, product in enumerate(PRODUCTS):
        for j, interval in enumerate(INTERVALS):
            ax = axes[i, j]
            cell = h[(h["product"] == product) & (h.interval_minutes == interval)]
            for column, color, label in (("mean_mfe", "#087f5b", "MFE"), ("mean_mae", "#c92a2a", "MAE"),
                                          ("mean_terminal_delta", "#1864ab", "Signed close")):
                if column in cell:
                    ax.plot(cell.horizon, cell[column], marker="o", markersize=3, color=color, label=label)
            if {"ci95_low", "ci95_high"} <= set(cell):
                ax.fill_between(cell.horizon.to_numpy(float), cell.ci95_low.to_numpy(float),
                                cell.ci95_high.to_numpy(float), color="#1864ab", alpha=.12)
            ax.axhline(0, color="gray", lw=.7)
            ax.set(title=f"{product} · {interval}m", xlabel="Scheduled chart candles", ylabel="Mean raw points")
            ax.legend(fontsize=7)
    fig.suptitle("Fixed slow-touch horizon paths · 2018–2020 development")
    publish_figure(fig, "horizons.png", "Horizon paths", "Event-weighted means; 15 candles represents different active durations. Undefined paths are omitted from means, with counts retained in S1-T02.",
                   [(paths["S1-T02"], h, [key for key in ("horizon", "mean_mfe", "mean_mae", "mean_terminal_delta", "ci95_low", "ci95_high") if key in h], {"direction": ["All"], "unit": ["points"], "support": ["all"]})])

    q = base(quantiles)
    q = q[(q.horizon == 15) & q.metric.isin(("mfe", "mae"))].copy()
    fig, axes = plt.subplots(3, 2, figsize=(11, 8), constrained_layout=True)
    for i, product in enumerate(PRODUCTS):
        cell_product = q[q["product"] == product]
        maximum = cell_product.value.max()
        maximum = maximum * 1.05 if pd.notna(maximum) and maximum > 0 else 1
        for j, interval in enumerate(INTERVALS):
            ax = axes[i, j]
            cell = cell_product[cell_product.interval_minutes == interval]
            for metric, color in (("mfe", "#087f5b"), ("mae", "#c92a2a")):
                sub = cell[cell.metric == metric].sort_values("quantile")
                ax.plot(sub["quantile"] * 100, sub.value, marker="o", markersize=3, color=color, label=metric.upper())
            ax.set(title=f"{product} · {interval}m · H15", xlabel="Exact percentile", ylabel="Raw points", ylim=(0, maximum))
            ax.legend(fontsize=7)
    fig.suptitle("MAE/MFE distribution cutoffs · common scale within each product")
    publish_figure(fig, "distributions.png", "Common-scale MAE and MFE cutoffs", "Exact p(n−1) interpolation. Both metrics and both candle intervals share a product-specific scale; raw points are never pooled across products.",
                   [(paths["S1-T03"], q, ["metric", "quantile", "value"], {"direction": ["All"], "unit": ["points"], "horizon": ["15"], "metric": ["mfe", "mae"]})])

    annual = base(stability)
    annual = annual[(annual.horizon == 15) & (annual.period_kind.isin(("year", "annual")))].copy()
    fig, axes = plt.subplots(3, 2, figsize=(11, 8), constrained_layout=True)
    for i, product in enumerate(PRODUCTS):
        for j, interval in enumerate(INTERVALS):
            ax = axes[i, j]
            cell = annual[(annual["product"] == product) & (annual.interval_minutes == interval)].sort_values("period")
            ax.bar(cell.period.astype(str), cell.mean_terminal_delta, color="#4263eb", alpha=.65)
            ax.axhline(0, color="gray", lw=.7)
            ax.set(title=f"{product} · {interval}m · H15", xlabel="Signal calendar year", ylabel="Mean signed points")
    fig.suptitle("Annual stability under the fixed slow-touch rule")
    publish_figure(fig, "annual_stability.png", "Annual stability", "Every development year retained. These descriptive strata do not select a preferred year, side or session.",
                   [(paths["S1-T04"], annual, ["period", "mean_terminal_delta", "completed"], {"direction": ["All"], "unit": ["points"], "horizon": ["15"], "period_kind": ["year", "annual"]})])

    monthly = base(calendar)
    monthly = monthly[(monthly.horizon == 15) & (monthly.period_kind.isin(("month", "monthly")))].copy()
    fig, axes = plt.subplots(3, 2, figsize=(11, 8), constrained_layout=True)
    for i, product in enumerate(PRODUCTS):
        for j, interval in enumerate(INTERVALS):
            ax = axes[i, j]
            cell = monthly[(monthly["product"] == product) & (monthly.interval_minutes == interval)].sort_values("period")
            x = np.arange(len(cell))
            ax.plot(x, cell.mean_terminal_delta, color="#4263eb", lw=1)
            ax.axhline(0, color="gray", lw=.7)
            ticks = x[::6]
            ax.set_xticks(ticks, cell.period.astype(str).to_numpy()[::6], rotation=25)
            ax.set(title=f"{product} · {interval}m · H15", ylabel="Mean signed points")
    fig.suptitle("Monthly development stability · undefined months remain gaps")
    publish_figure(fig, "calendar_stability.png", "Calendar stability", "All modeled months remain on the axis, including zero-event support. Undefined averages remain gaps rather than zero price outcomes. Weekly rows are retained in S1-T05.",
                   [(paths["S1-T05"], monthly, ["period", "mean_terminal_delta", "accepted", "completed"], {"direction": ["All"], "unit": ["points"], "horizon": ["15"], "period_kind": ["month", "monthly"]})])

    examples = pd.read_csv(paths["S1-T06"])
    candles = pd.read_parquet(example_paths) if example_paths and example_paths.suffix == ".parquet" else (
        pd.read_csv(example_paths) if example_paths else pd.DataFrame())
    for interval in INTERVALS:
        fig, axes = plt.subplots(3, 5, figsize=(16, 9), constrained_layout=True)
        chosen = examples[examples.interval_minutes == interval]
        for i, product in enumerate(PRODUCTS):
            for j, example_class in enumerate(EXAMPLE_CLASSES):
                ax = axes[i, j]
                item = chosen[(chosen["product"] == product) & (chosen.example_class == example_class)].iloc[0]
                ax.set_title(f"{product} {interval}m · {example_class.replace('_', ' ')}", fontsize=8)
                path = candles[candles.selection_id == item.selection_id] if len(candles) else candles
                if item.selection_status != "selected" or path.empty:
                    ax.text(.5, .5, "Unavailable selection" if item.selection_status != "selected" else "Saved path unavailable", ha="center", va="center", transform=ax.transAxes)
                    ax.set_xticks([])
                    continue
                path = path.sort_values("relative_slot")
                if "timestamp" in path:
                    years = pd.to_datetime(path.timestamp, utc=True).dt.tz_convert("America/New_York").dt.year
                    if not years.between(2018, 2020).all():
                        raise ValueError("Example path would expose outcomes outside development")
                x = path.relative_slot
                ax.vlines(x, path.low, path.high, color="#999999", lw=.8)
                ax.plot(x, path.close, color="#333333", lw=.9, label="Close")
                for key, color in (("ema20", "#e67700"), ("ema50", "#1864ab")):
                    if key in path:
                        ax.plot(x, path[key], color=color, lw=.8, label=key)
                if pd.notna(item.reference_price):
                    ax.axhline(item.reference_price, color="#5f3dc4", lw=.8, ls="--")
                ax.axvline(0, color="#5f3dc4", lw=.8)
                ax.set_xlabel("Scheduled slot from signal", fontsize=7)
                ax.tick_params(labelsize=6)
        fig.suptitle(f"Frozen deterministic examples · {interval}m · signal candle is slot zero")
        sources = [(paths["S1-T06"], chosen, ["selection_id", "example_class", "event_id", "timestamp", "reference_price"], {"interval_minutes": [str(interval)]})]
        if example_paths:
            # Paths retain a stable row_id, assigned at extraction; their sources stay private.
            pathpart = candles[candles.interval_minutes == interval] if len(candles) else candles
            sources.append((example_paths, pathpart, ["relative_slot", "low", "high", "close", "ema20", "ema50"], {"interval_minutes": [str(interval)]}))
        publish_figure(fig, f"examples_{interval}m.png", f"Deterministic {interval}m event illustrations", "Typical, highest adverse, highest favorable, earliest rejected and earliest censored H15 cases. Ranking is frozen, ties use timestamp/event ID. OHLC does not establish intrabar ordering; unavailable cases are explicit.", sources)
    if sum((stage / item["path"]).stat().st_size for item in sections) > 8 * 1024 * 1024:
        raise ValueError("Combined figures exceed Narada budget")
    environment = _figure_environment()
    save_json(stage / "figure-environment.json", environment)
    return sections, bindings


def _format(raw):
    return "undefined" if raw == "" else raw


def _html_table(columns, rows):
    headers = "".join("<th>" + html.escape(column["label"]) + "</th>" for column in columns)
    body = "".join("<tr>" + "".join("<td>" + html.escape("Not available" if row.get(column["key"]) is None else str(row[column["key"]])) + "</td>" for column in columns) + "</tr>" for row in rows)
    return '<div class="scroll" tabindex="0"><table><thead><tr>' + headers + "</tr></thead><tbody>" + body + "</tbody></table></div>"


def render_bundle(stage: Path, run_id: str | None = None, *, table_paths=None,
                  example_paths: Path | None = None, published_at: str | None = None,
                  figures: bool = True) -> dict:
    """Write offline/Narada sources from immutable, explicitly selected saved evidence."""
    stage = Path(stage)
    run_id = run_id or stage.name
    paths = _table_paths(stage, table_paths)
    saved = {key: read_csv(path) for key, path in paths.items()}
    for key in ("S1-T02", "S1-T03", "S1-T04", "S1-T05"):
        for row in saved[key][1]:
            if row.get("split", "development") != "development":
                raise ValueError("Reserved-period outcome table rejected")
            if "year" in row and row["year"] and int(row["year"]) not in (2018, 2019, 2020):
                raise ValueError("Reserved-period outcome year rejected")
            if row.get("period_kind") in ("year", "month") and not str(row["period"]).startswith(("2018", "2019", "2020")):
                raise ValueError("Reserved-period calendar outcome rejected")
    selections = []
    def table(table_id, section_id, title, columns, selector, description):
        headers = saved[table_id][0]
        columns = [column for column in columns if column["key"] in headers]
        rows, bindings = project_table(paths[table_id], columns=columns, selector=selector,
                                       section=section_id, source_artifact=paths[table_id].relative_to(stage).as_posix())
        selections.extend(bindings)
        return {"id": section_id, "kind": "table", "title": title, "columns": columns, "rows": rows,
                "description": description, "referenceIds": [table_id.lower()],
                "notes": ["Blank numerical evidence remains Not available. Percent values are saved ratios.",
                          "Source table selectors and exact cells are reconciled in the private bindings."]}
    primary_selector = {"direction": ["All"], "horizon": ["15"], "unit": ["points"], "support": ["all"]}
    primary_columns = [_column("product"), _column("interval_minutes", "Candle minutes", numeric=True),
                       _column("accepted", numeric=True), _column("completed", numeric=True),
                       _column("censored", numeric=True), _column("contributing_sessions", "Sessions", numeric=True),
                       _column("mean_mfe", numeric=True, unit="points"), _column("mean_mae", numeric=True, unit="points"),
                       _column("mean_terminal_delta", "Mean signed close", numeric=True, unit="points"),
                       _column("favorable_share", percent=True), _column("ci95_low", "95% low", numeric=True),
                       _column("ci95_high", "95% high", numeric=True)]
    primary = table("S1-T02", "primary", "Primary H15 scorecard", primary_columns, primary_selector,
                    "Pooled Buy/Sell; event-weighted raw points separately by product. H15 is 45 active minutes on 3m and 75 on 5m.")
    claims, claim_bindings = [], []
    source_hash = sha256(paths["S1-T02"])
    for data_row, row in _choose(paths["S1-T02"], primary_selector):
        interval = row["interval_minutes"]
        low, high = row.get("ci95_low", ""), row.get("ci95_high", "")
        qualifier = "95% interval unavailable"
        if low != "" and high != "":
            qualifier = f"95% interval [{low}, {high}], " + ("includes zero" if float(low) <= 0 <= float(high) else "entirely positive" if float(low) > 0 else "entirely negative")
        claim = (f"{row['product']} {interval}m H15: {row['completed']} completed of {row['accepted']} accepted paths; "
                 f"{row['censored']} censored. Mean signed terminal movement {_format(row['mean_terminal_delta'])} points; "
                 f"{qualifier}. Mean MFE {_format(row['mean_mfe'])}, MAE {_format(row['mean_mae'])} points. "
                 f"Sparse support: {row.get('sparse_warning', 'not recorded')}. Evidence row {row['row_id']}.")
        claims.append(claim)
        claim_bindings.append({"claim_id": f"primary-{row['product'].lower()}-{interval}m", "claim": claim,
                               "source_artifact": paths["S1-T02"].relative_to(stage).as_posix(),
                               "source_sha256": source_hash, "row_id": row["row_id"], "data_row_1_based": data_row,
                               "selector": {"row_id": [row["row_id"]]},
                               "columns": [key for key in ("product", "interval_minutes", "completed", "accepted", "censored",
                                                            "mean_terminal_delta", "mean_mfe", "mean_mae", "ci95_low", "ci95_high", "sparse_warning") if key in row],
                               "source_raw": {key: row[key] for key in ("product", "interval_minutes", "completed", "accepted", "censored",
                                                                         "mean_terminal_delta", "mean_mfe", "mean_mae")},
                               "rule": "fixed H15 All points narrative, interval sign classification against zero"})
    sections = [{"id": "findings", "kind": "text", "title": "Stage 1 development findings",
                 "body": "\n\n".join(claims), "referenceIds": ["s1-t02"]}, primary,
                {"id": "definitions", "kind": "text", "title": "Frozen definitions and uncertainty", "body": METHODS},
                {"id": "limitations", "kind": "text", "title": "Coverage and interpretation limits", "body": LIMITS}]
    sections.append(table("S1-T00", "coverage", "Input coverage and quality", [
        _column("product"), _column("interval_minutes", numeric=True), _column("year", numeric=True),
        _column("scheduled_slots", numeric=True), _column("usable_slots", numeric=True),
        _column("feature_ready_slots", numeric=True), _column("missing_slots", numeric=True),
        _column("empty_slots", numeric=True), _column("mixed_slots", numeric=True),
        _column("calendar_invalid_slots", numeric=True), _column("expected_source_minutes", numeric=True),
        _column("observed_source_minutes", numeric=True)], {"split": ["development"]},
        "Primary buckets require every expected source minute and one contract. Feature readiness is recorded on native 5m; mapped decision eligibility is in signal flow. Unknown missingness is not compressed."))
    sections.append(table("S1-T01", "flow", "Signal flow before future exclusions", [
        _column("product"), _column("interval_minutes", numeric=True), _column("reason"), _column("count", numeric=True)],
        {"direction": ["All"], "flow_kind": ["signal"], "reason": ["scheduled_slots", "usable_slots", "feature_valid_slots", "eligible_slots", "technical_candidates", "setup_candidates", "accepted"]},
        "Technical candidates, pre-armed setups and accepted signals are saved before any future-path exclusions. Missing-path results do not change pullback state."))
    sections.append(table("S1-T04", "stability", "Annual and fixed session-time stability", [
        _column("product"), _column("interval_minutes", numeric=True), _column("period_kind"), _column("period"),
        _column("accepted", numeric=True), _column("completed", numeric=True), _column("censored", numeric=True),
        _column("mean_terminal_delta", numeric=True, unit="points"), _column("mean_mae", numeric=True, unit="points"),
        _column("favorable_share", percent=True), _column("contributing_sessions", numeric=True), _column("sparse_warning")],
        {"direction": ["All"], "unit": ["points"], "support": ["all"], "period_kind": ["year", "time_stratum"]},
        "All years and every prespecified time stratum retained. Individual trading-session and hour rows remain in the complete saved table; no favorable hour is selected."))
    side_columns = [_column("product"), _column("interval_minutes", numeric=True), _column("direction"),
                    _column("completed", numeric=True), _column("mean_terminal_delta", numeric=True, unit="points"),
                    _column("mean_mfe", numeric=True, unit="points"), _column("mean_mae", numeric=True, unit="points"),
                    _column("favorable_share", percent=True), _column("mfe_gt_mae_share", percent=True),
                    _column("session_mean_terminal_delta", "Session balanced close", numeric=True),
                    _column("contributing_sessions", numeric=True), _column("sparse_warning")]
    sections.append(table("S1-T02", "sides", "All, Buy and Sell", side_columns,
                          {"horizon": ["15"], "unit": ["points"], "support": ["all"]},
                          "Every fixed side view retained at H15; these strata do not choose a preferred side."))
    normalized_columns = [_column("product"), _column("interval_minutes", numeric=True), _column("completed", numeric=True),
                          _column("mean_mfe", numeric=True, unit="ATR"), _column("mean_mae", numeric=True, unit="ATR"),
                          _column("mean_terminal_delta", numeric=True, unit="ATR"),
                          _column("session_mean_terminal_delta", numeric=True, unit="ATR"), _column("sparse_warning")]
    sections.append(table("S1-T02", "atr", "Entry-ATR-normalized H15 paths", normalized_columns,
                          {"direction": ["All"], "horizon": ["15"], "unit": ["atr"], "support": ["all"]},
                          "Each path metric divided by its positive valid entry ATR14. No ratio of cohort averages."))
    equal_columns = [_column("product"), _column("interval_minutes", numeric=True), _column("horizon", numeric=True),
                     _column("horizon_minutes", numeric=True), _column("completed", numeric=True),
                     _column("mean_mfe", numeric=True, unit="points"), _column("mean_mae", numeric=True, unit="points"),
                     _column("mean_terminal_delta", numeric=True, unit="points"), _column("favorable_share", percent=True)]
    # Deterministic equal-active pairs, rather than all selected horizons at both intervals.
    equal = table("S1-T02", "equal-active", "Equal active durations", equal_columns,
                  {"direction": ["All"], "unit": ["points"], "support": ["all"], "horizon_minutes": ["60", "150"]},
                  "60 active minutes: 3m H20 and 5m H12; 150: 3m H50 and 5m H30. Closure-crossing paths can have longer clock elapsed time.")
    sections.append(equal)
    figure_sections, figure_bindings = render_figures(stage, paths, example_paths=example_paths) if figures else ([], [])
    sections.extend(figure_sections)
    downloads, download_bindings = [], []
    definitions = [
        ("S1-T02", "primary.csv", "primary-csv", primary_selector,
         ["row_id", "product", "interval_minutes", "direction", "horizon", "unit", "accepted", "completed", "censored", "contributing_sessions", "contributing_weeks", "mean_mfe", "mean_mae", "mean_terminal_delta", "ci95_low", "ci95_high", "favorable_share", "session_mean_terminal_delta", "sparse_warning"], "Primary H15 saved scorecard"),
        ("S1-T02", "horizons.csv", "horizons-csv", {"direction": ["All"], "unit": ["points"], "support": ["all"]},
         ["row_id", "product", "interval_minutes", "horizon", "horizon_minutes", "accepted", "completed", "censored", "mean_mfe", "mean_mae", "mean_terminal_delta", "ci95_low", "ci95_high", "favorable_share", "mfe_gt_mae_share", "sparse_warning"], "All fixed horizons in raw points"),
        ("S1-T03", "quantiles.csv", "quantiles-csv", {"direction": ["All"], "unit": ["points"], "support": ["all"], "horizon": ["15"]},
         ["row_id", "product", "interval_minutes", "horizon", "metric", "quantile", "value"], "H15 exact excursion and close quantiles"),
        ("S1-T05", "months.csv", "months-csv", {"direction": ["All"], "unit": ["points"], "support": ["all"], "horizon": ["15"], "period_kind": ["month", "monthly"]},
         ["row_id", "product", "interval_minutes", "period_kind", "period", "accepted", "completed", "censored", "mean_mfe", "mean_mae", "mean_terminal_delta", "favorable_share", "contributing_sessions", "sparse_warning"], "All development months including zero-support rows"),
    ]
    for table_id, filename, download_id, selector, columns, label in definitions:
        columns = [key for key in columns if key in saved[table_id][0]]
        if _choose(paths[table_id], selector):
            declaration, binding = project_download(stage, paths[table_id], columns=columns, selector=selector,
                                                     filename=filename, run_id=run_id, download_id=download_id, description=label)
            downloads.append(declaration)
            download_bindings.append(binding)
    stamp = published_at or (run_id[:8] + "T" + run_id[9:15] + "Z")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp):
        match = re.match(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z", run_id)
        if not match:
            raise ValueError("Provide an explicit published_at ISO UTC timestamp")
        year, month, day, hour, minute, second = match.groups()
        stamp = f"{year}-{month}-{day}T{hour}:{minute}:{second}Z"
    publication_id = "ema-cloud-slow-stage1-" + run_id.lower().replace("_", "-")
    report = {"schemaVersion": "1.1", "id": publication_id,
              "title": "20/50 5minEMA Cloud: Stage 1 slow-touch opportunity paths",
              "summary": "Fixed-width slow EMA touches in ES, GC and NQ on 3m and 5m candles; 2018–2020 development paths, censored counts and dependence-aware uncertainty. Path observations do not estimate profitability.",
              "publishedAt": stamp, "source": {"producer": "Sahadeva", "runId": run_id},
              "sections": sections, "notes": ["Private Narada-ready source prepared before sealing; no public staging or deployment.", LIMITS],
              "references": [{"id": key.lower(), "kind": "saved-artifact", "label": key,
                              "title": TABLES[key].replace(".csv", "").replace("_", " "),
                              "runId": run_id, "artifact": path.relative_to(stage).as_posix(), "sha256": sha256(path)}
                             for key, path in paths.items()], "downloads": downloads}
    save_json(stage / "publication.json", report)
    if (stage / "publication.json").stat().st_size > 96 * 1024:
        raise ValueError("Publication source exceeds 96 KiB")
    bindings = {"schema_version": 1, "run_id": run_id, "publication_sha256": sha256(stage / "publication.json"),
                "cells": selections, "claims": claim_bindings, "figures": figure_bindings,
                "downloads": download_bindings, "example_definition": EXAMPLE_DEFINITION,
                "source_tables": [{"table_id": key, "path": path.relative_to(stage).as_posix(), "sha256": sha256(path)}
                                  for key, path in paths.items()]}
    save_json(stage / "source-bindings.json", bindings)
    md = ["# 20/50 5minEMA Cloud Trend Follow Opportunity Study — Stage 1",
          f"Run {run_id} · 2018–2020 development only · prepared {stamp}", "## Findings", *claims,
          "## Definitions and uncertainty", METHODS, "## Coverage and limitations", LIMITS]
    body = ["<h1>20/50 5minEMA Cloud Trend Follow Opportunity Study — Stage 1</h1>",
            "<p>Run " + html.escape(run_id) + " · 2018–2020 development only</p>"]
    for section in sections:
        body.append("<section><h2>" + html.escape(section["title"]) + "</h2>")
        if section["kind"] == "text":
            body.extend("<p>" + html.escape(paragraph) + "</p>" for paragraph in section["body"].split("\n\n"))
        elif section["kind"] == "table":
            body.append("<p>" + html.escape(section["description"]) + "</p>" + _html_table(section["columns"], section["rows"]))
            md.extend(["## " + section["title"], section["description"],
                       "| " + " | ".join(column["label"] for column in section["columns"]) + " |",
                       "| " + " | ".join("---" for _ in section["columns"]) + " |"])
            md.extend("| " + " | ".join("undefined" if row[column["key"]] is None else str(row[column["key"]]) for column in section["columns"]) + " |" for row in section["rows"])
        elif section["kind"] == "figure":
            body.append('<figure><img src="' + section["path"] + '" alt="' + html.escape(section["alt"], quote=True) + '"><figcaption>' + html.escape(section["caption"]) + "</figcaption></figure>")
            md.extend(["## " + section["title"], f"![{section['alt']}]({section['path']})", section["caption"]])
        body.append("</section>")
    md.append("## Complete saved evidence")
    body.append("<h2>Complete saved evidence</h2><ul>")
    for key, path in paths.items():
        relative = path.relative_to(stage).as_posix()
        md.append(f"- [{key}: {path.stem}]({relative})")
        body.append(f'<li><a href="{relative}">{html.escape(key + ": " + path.stem)}</a></li>')
    body.append("</ul><p>Publication cells, claims, figures and selected downloads are bound in source-bindings.json. Scientific reconciliation is separate from Narada validation.</p>")
    md.extend(["## Stage 2 handoff", "Reuse the sealed slow baseline, frozen settings, reusable 1m→3m/5m aggregation and 5m EMA/ATR delivery. Stage 2 must reproduce these exact slow event IDs and outcomes before adding an independent fast branch.",
               "## Reproducibility", "Retain frozen config, inputs.lock.json, exact commands, execution snapshots, environment lock, check receipts and external-ledger hashes. Byte integrity, numerical fixtures and scientific reconciliation establish separate facts."])
    (stage / "report.md").write_text("\n\n".join(md) + "\n", encoding="utf-8")
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>EMA Cloud Stage 1</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1200px;margin:auto;padding:32px;color:#17233b}h1{line-height:1.2}h2{margin-top:2em}.scroll{overflow-x:auto}table{border-collapse:collapse;min-width:700px;font-size:13px}th,td{padding:8px 12px;border-bottom:1px solid #ddd;text-align:left}th{background:#eef2f7}img{max-width:100%;height:auto}figcaption{font-size:14px;color:#526076}a{color:#1c55b2}section{margin:28px 0}</style><body>' + "\n".join(body) + "</body></html>\n"
    (stage / "report.html").write_text(document, encoding="utf-8")
    advice = ["# Stage 1 development advice", f"Dated {stamp[:10]} · Run {run_id}",
              "Preserve this slow-touch baseline for Stage 2. This descriptive price-path evidence supports no profitability recommendation or optimized stop/target rule.", *claims,
              "Exact evidence: S1-T02 row IDs above; see all S1-T00–S1-T06 tables. Negative, inconclusive and sparse outcomes remain retained.", LIMITS]
    (stage / "advice.md").write_text("\n\n".join(advice) + "\n", encoding="utf-8")
    return {"status": "prepared", "publication": "publication.json", "publication_sha256": sha256(stage / "publication.json"),
            "table_count": len(paths), "cell_bindings": len(selections), "claim_count": len(claims),
            "figure_count": len(figure_sections), "download_count": len(downloads),
            "figure_path_qualification": "saved paths unavailable" if figures and not example_paths else None}
