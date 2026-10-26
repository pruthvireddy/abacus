"""Author bounded Narada reports by projecting already saved per-future tables.

This module never reads price histories or calculates research statistics. The
compact source map records every selected row, column and conversion; --check
expands the map and compares every displayed, downloaded and plotted input cell.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SID = "25_forex_news_ema"
SYMBOLS = ("6E", "6B", "6J", "6A", "6C", "6S")
PRODUCTS = {"6E": "Euro", "6B": "British pound", "6J": "Japanese yen", "6A": "Australian dollar", "6C": "Canadian dollar", "6S": "Swiss franc"}
FAMILIES = ("overall", "by_type", "monthly", "weekly", "type_month", "type_week", "by_side", "type_side", "weekday", "hour", "year", "quarter")
GROUPS = {"overall": (), "by_type": ("news_type",), "monthly": ("month_chicago",), "weekly": ("week_chicago",),
          "type_month": ("news_type", "month_chicago"), "type_week": ("news_type", "week_chicago"),
          "by_side": ("side",), "type_side": ("news_type", "side"), "weekday": ("weekday_chicago",),
          "hour": ("hour_chicago",), "year": ("year",), "quarter": ("quarter",)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)+"\n", encoding="utf-8")


def csv_rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def value(raw, operation="identity"):
    if raw == "":
        return None
    if operation == "text":
        return raw
    try:
        result = float(raw)
    except ValueError:
        require(operation == "identity", "Non-numeric percentage source")
        return raw
    require(math.isfinite(result), "Non-finite saved number")
    if operation == "percent/100":
        return result / 100
    return int(result) if result.is_integer() else result


def col(key, label, source, fmt=None, precision=2, unit=None):
    result = {"key": key, "label": label}
    if fmt:
        result.update(format=fmt, precision=precision)
    if unit:
        result["unit"] = unit
    return result, {"column": source, "operation": "percent/100" if fmt == "percent" else "identity"}


BASE = [col("mode", "Calendar", "mode"), col("h", "Candles", "horizon_bars", "number", 0)]
N = col("n", "Completed N", "completed", "number", 0)
MEANS = [N, col("mfe", "Mean MFE", "average_mfe_ticks", "number", 2, "ticks"), col("mae", "Mean MAE", "average_mae_ticks", "number", 2, "ticks"),
         col("close", "Mean close", "average_close_ticks", "number", 2, "ticks"), col("med", "Median close", "median_close_ticks", "number", 2, "ticks"),
         col("fav", "Favorable close", "favorable_close_percent", "percent", 1), col("ratio", "MFE / MAE", "mfe_mae_ratio", "number", 2),
         col("support", "Sample support", "sample_support")]
T = col("type", "News type", "news_type")
DIMCOL = {"monthly": col("period", "Entry month (Chicago)", "month_chicago"), "weekly": col("period", "ISO week (Chicago)", "week_chicago"),
          "by_side": col("side", "EMA side", "side"), "weekday": col("day", "Weekday (Chicago)", "weekday_chicago"),
          "hour": col("hour", "Release hour (Chicago)", "hour_chicago"), "year": col("period", "Entry year (Chicago)", "year"),
          "quarter": col("period", "Entry quarter (Chicago)", "quarter")}


class Author:
    def __init__(self, stage, symbol, run_id):
        self.stage, self.symbol, self.run_id = stage, symbol, run_id
        self.pub_id = f"forex-news-{symbol.lower()}-20261017-v2"
        self.directory = stage / "publications" / self.pub_id
        require(not self.directory.exists(), f"Refusing to replace {self.directory}")
        self.directory.mkdir(parents=True)
        self.sections, self.projections, self.metrics, self.chart_bindings, self.filter_defaults = [], [], [], [], []
        self.tables = {family: csv_rows(stage / "tables" / f"{symbol}-{family}.csv")[1] for family in FAMILIES}
        require(all(self.tables.values()), "Every declared table family must have saved rows")
        self.sources = {family: f"tables/{symbol}-{family}.csv" for family in FAMILIES}

    def text(self, identity, title, body, refs=("overall",)):
        self.sections.append({"id": identity, "title": title, "kind": "text", "body": body, "referenceIds": list(refs)})

    def table(self, identity, title, family, columns, description, filters=True, notes=()):
        indices = list(range(len(self.tables[family])))
        schema = [item[0] for item in columns]
        mappings = {item[0]["key"]: item[1] for item in columns}
        projected = [{key: value(row[m["column"]], m["operation"]) for key, m in mappings.items()} for row in self.tables[family]]
        require(len(projected) <= 1500 and len(schema) <= 12, f"Table budget: {identity}")
        section = {"id": identity, "title": title, "kind": "table", "columns": schema, "rows": projected,
                   "description": description, "referenceIds": [family],
                   "notes": ["N is completed observations; pending outcomes are excluded from averages and rates. Positive close favors the frozen EMA side.",
                             "Groups are descriptive, can overlap across calendars, and are not independent trials. Small N has no reliability guarantee.", *notes]}
        if filters:
            section["rowFilters"] = [{"key": "mode", "label": "Calendar", "defaultValue": "combined"},
                                    {"key": "h", "label": "Following candles", "defaultValue": 5}]
            if any(c["key"] == "type" for c in schema):
                section["rowFilters"].append({"key": "type", "label": "News type"})
                if family in ("type_month", "type_week"):
                    initial = next(r for r in self.tables[family] if r["mode"] == "combined" and r["horizon_bars"] == "5" and r["type_code"] == "0")
                    section["rowFilters"][-1]["defaultValue"] = initial["news_type"]
                    section["description"] += " Starts with U.S. employment; choose All news types to browse every saved group."
        section_index = len(self.sections)
        self.sections.append(section)
        self.projections.append({"target": f"/sections/{section_index}/rows", "artifact": self.sources[family],
                                 "sha256": sha(self.stage / self.sources[family]), "sourceRows": indices, "columns": mappings})
        for filter_index, selected in enumerate(section.get("rowFilters", [])):
            if "defaultValue" in selected:
                cell = mappings[selected["key"]]
                source_row = next(i for i, r in enumerate(self.tables[family]) if value(r[cell["column"]], cell["operation"]) == selected["defaultValue"])
                self.filter_defaults.append({"pointer": f"/sections/{section_index}/rowFilters/{filter_index}/defaultValue", "artifact": self.sources[family],
                    "sha256": sha(self.stage / self.sources[family]), "row": source_row, "column": cell["column"], "operation": cell["operation"]})

    def metric(self, label, row_index, field, fmt="number", precision=2, note=None):
        index = len(self.sections[-1]["items"])
        item = {"label": label, "value": value(self.tables["overall"][row_index][field], "percent/100" if fmt == "percent" else "identity"), "format": fmt, "precision": precision}
        if note:
            item["note"] = note
        self.sections[-1]["items"].append(item)
        self.metrics.append({"pointer": f"/sections/{len(self.sections)-1}/items/{index}/value", "artifact": self.sources["overall"],
                             "sha256": sha(self.stage / self.sources["overall"]), "row": row_index, "column": field,
                             "operation": "percent/100" if fmt == "percent" else "identity"})

    def chart_value(self, family, row_index, column, pointer):
        self.chart_bindings.append({"pointer": pointer, "artifact": self.sources[family], "sha256": sha(self.stage / self.sources[family]),
                                    "row": row_index, "column": column, "operation": "identity"})
        return value(self.tables[family][row_index][column])

    def charts(self):
        chart = {"symbol": self.symbol, "horizons": {}, "types": [], "months": []}
        for mode in ("combined", "us_only", "local_only"):
            chart["horizons"][mode] = []
            for i, r in enumerate(self.tables["overall"]):
                if r["mode"] == mode:
                    p = len(chart["horizons"][mode])
                    chart["horizons"][mode].append({k: self.chart_value("overall", i, c, f"/horizons/{mode}/{p}/{k}") for k, c in [("h", "horizon_bars"), ("close", "average_close_percent"), ("n", "completed")]})
        for i, r in enumerate(self.tables["by_type"]):
            if r["mode"] == "combined" and r["horizon_bars"] == "5":
                p = len(chart["types"])
                chart["types"].append({k: self.chart_value("by_type", i, c, f"/types/{p}/{k}") for k, c in [("type", "news_type"), ("mfe", "average_mfe_ticks"), ("mae", "average_mae_ticks"), ("close", "average_close_ticks"), ("n", "completed")]})
        for i, r in enumerate(self.tables["monthly"]):
            if r["mode"] == "combined" and r["horizon_bars"] == "5":
                p = len(chart["months"])
                chart["months"].append({k: self.chart_value("monthly", i, c, f"/months/{p}/{k}") for k, c in [("period", "month_chicago"), ("close", "average_close_percent"), ("n", "completed")]})
        write(self.directory / "chart-spec.json", chart)

    def figure(self, identity, title, filename, alt, caption, refs):
        self.sections.append({"id": identity, "title": title, "kind": "figure", "path": f"figures/{filename}.png", "alt": alt, "caption": caption, "referenceIds": list(refs)})

    def downloads(self):
        # Every numeric value is a saved string. Group labels are source dimension
        # strings joined only for compact identification; no estimates are pooled.
        common = ["family", "mode", "horizon_bars", "group", "period"]
        metrics = ["signals", "completed", "pending", "long_signals", "short_signals",
                   "average_mfe_ticks", "average_mae_ticks", "average_close_ticks", "median_mfe_ticks", "median_mae_ticks", "median_close_ticks",
                   "average_mfe_percent", "average_mae_percent", "average_close_percent", "favorable_close_percent", "adverse_close_percent", "flat_close_percent", "mfe_above_mae_percent", "mfe_mae_ratio"]
        quantiles = ["completed", *[f"p{q}_{outcome}_ticks" for outcome in ("mfe", "mae", "close") for q in (10, 25, 75, 90)],
                     "median_mfe_ticks", "median_mae_ticks", "median_close_ticks", "min_close_ticks", "max_close_ticks", "sample_support"]
        plans = [("summary", ("overall", "by_type", "by_side", "type_side", "weekday", "hour"), metrics, "Contract, news type, EMA side, weekday and release-hour summaries"),
                 ("periods", ("monthly", "weekly", "year", "quarter"), metrics, "Month, ISO week, partial year and quarter summaries"),
                 ("event-periods", ("type_month", "type_week"), metrics, "Every saved news-type by month and news-type by ISO-week summary"),
                 ("distributions", FAMILIES, quantiles, "All saved groups: excursion and close quantiles, close extremes and support")]
        result = []
        for name, families, metric_columns, label in plans:
            columns = common + metric_columns
            require(len(columns) <= 24, "CSV column budget")
            target = self.stage / "tables" / f"{self.symbol}-download-{name}.csv"
            require(not target.exists(), f"Refusing to replace download projection {target}")
            records, mapping_rows = [], []
            for family in families:
                for row_index, row in enumerate(self.tables[family]):
                    dims = GROUPS[family]
                    period_key = next((c for c in dims if c in ("month_chicago", "week_chicago", "year", "quarter")), None)
                    group_cols = [c for c in dims if c != period_key]
                    group = " | ".join(row[c] for c in group_cols) if group_cols else "All events"
                    item = {"family": family, "mode": row["mode"], "horizon_bars": row["horizon_bars"], "group": group, "period": row[period_key] if period_key else ""}
                    item.update({c: row[c] for c in metric_columns})
                    records.append(item)
                    mapping_rows.append({"family": family, "row": row_index, "groupColumns": group_cols, "periodColumn": period_key})
            require(0 < len(records) <= 15000, "CSV row budget")
            with target.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns)
                writer.writeheader()
                writer.writerows(records)
            download_dir = self.directory / "downloads"
            download_dir.mkdir(exist_ok=True)
            dest = download_dir / f"{self.symbol.lower()}-{name}.csv"
            shutil.copyfile(target, dest)
            self.projections.append({"target": "downloads/"+dest.name, "artifact": str(target.relative_to(self.stage)), "sha256": sha(target),
                                     "downloadRows": mapping_rows, "metricColumns": metric_columns,
                                     "sources": {family: {"artifact": self.sources[family], "sha256": sha(self.stage / self.sources[family])} for family in families}})
            result.append({"id": name, "path": "downloads/"+dest.name, "label": f"{self.symbol} · {label}",
                           "description": "Exact saved summary strings across all three calendar modes and five candle horizons; no raw event or price ledger.",
                           "population": f"{self.symbol} selected releases in the fixed reconstructed year. N is completed outcomes; calendars overlap and cannot be added.",
                           "units": "Ticks use this futures contract. Percent columns are percentage points (57.4 means 57.4%). Blank is unavailable, including undefined ratios; zero is observed zero.",
                           "scope": "Descriptive saved group summaries. family identifies grouping; group contains its source label(s), period its Chicago month/ISO week/year/quarter. Small samples and partial boundary periods remain.",
                           "mediaType": "text/csv", "sha256": sha(dest), "rowCount": len(records), "columns": columns,
                           "source": {"runId": self.run_id, "artifact": str(target.relative_to(self.stage)), "sha256": sha(target)}})
        return result

    def build(self, figure_python):
        s = self.symbol
        self.text("guide", f"{s} · {PRODUCTS[s]} news calendar", "Explore this contract's own U.S. and domestic economic releases. Start with the combined calendar at five following candles, then use the saved-row selectors to change calendar, horizon or news type. Each contract tab has a different eligible release sample; comparisons across tabs are not a common-event ranking.\n\nThese are descriptive price-path statistics around a frozen pre-news EMA20/50 direction. Favorable movement, adverse movement and the eventual signed close answer different questions. Positive excursions alone do not establish a tradable edge.")
        h5 = next(i for i, r in enumerate(self.tables["overall"]) if r["mode"] == "combined" and r["horizon_bars"] == "5")
        self.sections.append({"id": "snapshot", "title": "Combined calendar · five-candle snapshot", "kind": "metrics", "items": [], "referenceIds": ["overall"]})
        for label, field, fmt, precision in [("Completed releases", "completed", "number", 0), ("Mean favorable excursion · ticks", "average_mfe_ticks", "number", 2), ("Mean adverse excursion · ticks", "average_mae_ticks", "number", 2), ("Mean directional close · ticks", "average_close_ticks", "number", 2), ("Favorable close frequency", "favorable_close_percent", "percent", 1), ("Mean MFE / mean MAE", "mfe_mae_ratio", "number", 2)]:
            self.metric(label, h5, field, fmt, precision, "Descriptive reconstructed-year outcome; costs and executable fills are not modeled.")
        self.text("method", "Entry, direction and denominators", "The entry benchmark is the close of the confirmed 15-minute candle ending at the scheduled release. EMA20 above EMA50 fixes a long side; EMA20 below EMA50 fixes a short side. Equal EMAs skip the signal. The candle opening at the release is the first measured candle; earlier candle ranges do not enter the outcome.\n\nH5/H10/H15/H50/H100 count actual following chart candles. Session gaps and weekends can make elapsed time much longer than candles × 15 minutes. The side never changes within an observation, and later releases do not truncate earlier windows. N means completed outcomes, which alone enter means, quantiles and rates.\n\nMFE is the largest favorable path distance; MAE is the largest adverse path distance. Both are nonnegative distances. Close is signed: positive favors the entry side. MFE / MAE divides average excursions; it is not profit factor. Each normalized outcome is divided by its own entry price before averaging. Ticks refer to this contract's outright quoted price; they are not dollar returns.")
        self.table("overview", "All calendars and horizons", "overall", BASE + [N, col("pending", "Pending", "pending", "number", 0), col("long", "Long signals", "long_signals", "number", 0), col("short", "Short signals", "short_signals", "number", 0), *MEANS[1:7]], "combined includes U.S. plus domestic; us_only selects U.S.; local_only selects domestic. All three are separately selected, overlapping cohorts.", False)
        self.figure("horizons", "Does the directional close persist?", "horizon-comparison", f"{s} average directional close by following candle horizon, separately for combined, U.S. and domestic calendars.", "Saved average close as percentage of each entry price. Horizon positions are categorical. Calendar samples overlap; no costs, uncertainty bands or portfolio returns are represented.", ("overall",))
        self.text("event-reading", "News types: read the sample size before the average", "A timestamp with several selected category types belongs exclusively to Mixed types (same timestamp), code 13. It is not repeated under each component type. U.S.-only and domestic-only selections can classify that timestamp differently, so their type rows must not be added to the combined rows.\n\nDomestic CPI and GDP labels can include different stages or multi-release packages, rather than one uniform announcement series. The tables expose sample size, means, medians, tails and normalized distances so that a large average or a high favorable frequency can be viewed alongside skew and adverse excursions. The n<10 support flag is a descriptive warning threshold, not a statistical significance test.", ("by_type",))
        self.table("news-type", "Every news type · central outcomes", "by_type", BASE + [T, N, col("mfe", "Mean MFE", "average_mfe_ticks", "number", 2, "ticks"), col("medmfe", "Median MFE", "median_mfe_ticks", "number", 2, "ticks"), col("mae", "Mean MAE", "average_mae_ticks", "number", 2, "ticks"), col("medmae", "Median MAE", "median_mae_ticks", "number", 2, "ticks"), col("close", "Mean close", "average_close_ticks", "number", 2, "ticks"), col("med", "Median close", "median_close_ticks", "number", 2, "ticks"), col("fav", "Favorable close", "favorable_close_percent", "percent", 1), col("ratio", "MFE / MAE", "mfe_mae_ratio", "number", 2)], "All saved news types for every calendar and horizon. Means and medians describe the same completed outcomes.")
        self.figure("type-chart", "News types · opportunity and adverse movement", "news-type-excursions", f"{s} paired average favorable and adverse excursions by news type at H5, with signed closes and completed sample sizes.", "Combined calendar, H5. Left: mean MFE and MAE in own-contract ticks. Right: mean signed close in ticks, labelled with completed N. Types keep source order rather than being selected for favorable performance.", ("by_type",))
        self.table("news-distribution", "Every news type · distribution and tails", "by_type", BASE + [T, N, col("mfe10", "MFE P10", "p10_mfe_ticks", "number", 2, "ticks"), col("mfe90", "MFE P90", "p90_mfe_ticks", "number", 2, "ticks"), col("mae50", "MAE median", "median_mae_ticks", "number", 2, "ticks"), col("mae90", "MAE P90", "p90_mae_ticks", "number", 2, "ticks"), col("cl10", "Close P10", "p10_close_ticks", "number", 2, "ticks"), col("cl25", "Close P25", "p25_close_ticks", "number", 2, "ticks"), col("cl75", "Close P75", "p75_close_ticks", "number", 2, "ticks"), col("cl90", "Close P90", "p90_close_ticks", "number", 2, "ticks")], "Saved empirical percentiles use linear interpolation between sorted completed outcomes. P10 and P90 are sample quantiles, not prediction bounds. The distribution CSV includes every outcome's P10/P25/median/P75/P90 and close extremes.")
        self.table("news-rates", "Every news type · normalized moves and outcome frequencies", "by_type", BASE + [T, N, col("mp", "Mean MFE / entry", "average_mfe_percent", "percent", 3), col("ap", "Mean MAE / entry", "average_mae_percent", "percent", 3), col("cp", "Mean close / entry", "average_close_percent", "percent", 3), col("fav", "Favorable", "favorable_close_percent", "percent", 1), col("adverse", "Adverse", "adverse_close_percent", "percent", 1), col("flat", "Flat", "flat_close_percent", "percent", 1), col("mabove", "MFE exceeds MAE", "mfe_above_mae_percent", "percent", 1), col("support", "Sample support", "sample_support")], "Favorable means signed close > 0; adverse < 0; flat = 0. These are benchmark close frequencies. MFE-exceeds-MAE uses the retained source's floating-point comparison tolerance.")
        for family, title in [("monthly", "Month by month"), ("weekly", "Week by week")]:
            self.table(family, title, family, BASE + [DIMCOL[family], *MEANS], "Entry time assigns ownership in America/Chicago. ISO weeks start Monday; first and last periods are partial. Empty periods have no saved estimate; they are not zero-return periods.", notes=("Month/week patterns mix news composition and changing market conditions; they are not seasonality estimates.",))
        self.figure("month-chart", "Monthly direction and sample support", "monthly-direction", f"{s} combined-calendar H5 mean directional closes by Chicago entry month with completed counts underneath.", "Top: saved H5 average close normalized by each entry price. Bottom: the corresponding completed N. First and last entry months are partial; positive and negative months remain visible. The view is descriptive and has no out-of-sample test.", ("monthly",))
        for family, title, period_col, label in [("type_month", "News type × month", "month_chicago", "Entry month (Chicago)"), ("type_week", "News type × week", "week_chicago", "ISO week (Chicago)")]:
            self.table(family.replace("_", "-"), title, family, BASE + [T, col("period", label, period_col), *MEANS], "Select a calendar, horizon and optionally a news type to inspect every saved period. Very small groups are retained. The same release can contribute to overlapping horizons and separately selected modes.", notes=("A missing type-period row means no selected completed/signal group was saved; it must not be interpreted as a zero effect.",))
        self.table("ema-side", "Long versus short pre-news EMA direction", "by_side", BASE + [DIMCOL["by_side"], *MEANS], "Side is fixed by the confirmed pre-release EMA20/50 relation, not by the news surprise or subsequent price move.")
        self.table("type-side", "News type × EMA side", "type_side", BASE + [T, col("side", "EMA side", "side"), *MEANS], "Both long and short source groups are retained when present. An absent side is no selected observation, not evidence that the side cannot occur.")
        for family, title in [("weekday", "Release weekday"), ("hour", "Release clock hour"), ("year", "Calendar-year slices"), ("quarter", "Calendar-quarter slices")]:
            self.table(family, title, family, BASE + [DIMCOL[family], *MEANS], "Ownership uses America/Chicago entry time. Hour groups can change with daylight-saving differences; weekday/hour effects also reflect which announcements occur then. Boundary years and quarters are partial.")
        self.table("elapsed", "Actual elapsed time behind each candle horizon", "overall", BASE + [N, col("mean", "Mean elapsed", "average_elapsed_minutes", "number", 1, "minutes"), col("median", "Median elapsed", "median_elapsed_minutes", "number", 1, "minutes"), col("max", "Longest elapsed", "max_elapsed_minutes", "number", 0, "minutes"), col("pending", "Pending", "pending", "number", 0)], "Elapsed minutes run from release/benchmark entry to the completed horizon candle's close. Chart gaps, breaks and weekends remain in this calendar-time duration. The clock duration is not fixed by H.", False)
        self.coverage()
        self.text("evidence", "Evidence, reconstruction and native checks", "The fixed analysis window starts October 17, 2025 at midnight New York and ends October 17, 2026 at midnight New York, exclusive. The last available price candle is October 16, 2026. The source price year is reconstructed from merged native OHLC with continued EMA seeds; it is not a direct full-year export of the six new indicators.\n\nThe source retains native-chart checks covering 621 selected events and 4,968 field comparisons. Those checks concern the native loaded windows, selected entry/type fields and completed five-candle type outcomes; they do not validate every reconstructed-year observation or the other horizons. Abacus retains those receipts and independently checks saved-table aggregation and report transfers; it does not claim a new native TradingView replay.\n\nThe new calendar, week, side, hour, year, quarter and distribution summaries group retained per-entry outcomes. They do not rerun price reconstruction or change the saved indicator's entry rule. The earlier report remains separate evidence from its shared U.S. event cohort.")
        self.text("limits", "Interpretation and practical limits", "The expanded contract calendars have different eligible dates and event mixes. They cannot rank currencies on a common experimental cohort. U.S., domestic and combined modes overlap. A U.S. and domestic announcement at one timestamp is one combined observation, while the separate modes can each contain it. Mixed-type rows are exclusive only within their own selected mode.\n\nCalendar archives include corrected historical schedules, not a point-in-time announcement vintage. Release availability and history selection are retrospective. Off-grid releases and unreliable/tentative times are excluded. Overlapping windows, shared macro shocks and repeated horizon views create dependence; small monthly, weekly and news-type groups can be dominated by one event.\n\nNo spread, commission, slippage, stop, target, contract sizing or executable entry/exit assumption is tested. Back-adjusted continuous prices and benchmark closes are analytical inputs. Favorable-close frequency is not a trading win rate, MFE/MAE is not profit factor, and normalized price changes are not account returns.\n\nNo confidence intervals, multiple-comparison adjustment, causal identification or independent holdout are claimed. The many saved breakdowns are descriptive exploration. Both negative and favorable outcomes belong to the evidence; an apparently strong small cell requires a separately specified follow-up study.")
        downloads = self.downloads()
        # Narada reference identities are slugs. Private table-family/source-map
        # keys retain their original underscores; public references use dashes.
        for section in self.sections:
            if "referenceIds" in section:
                section["referenceIds"] = [reference.replace("_", "-") for reference in section["referenceIds"]]
        references = [{"id": family.replace("_", "-"), "kind": "saved-artifact", "label": f"{s} saved {family.replace('_', ' ')}", "title": "Saved per-future descriptive outcome summary", "runId": self.run_id, "artifact": self.sources[family], "sha256": sha(self.stage / self.sources[family])} for family in FAMILIES]
        report = {"schemaVersion": "1.1", "id": self.pub_id, "title": f"{s} {PRODUCTS[s]} · news EMA research", "summary": f"U.S. and domestic news for {s}: five horizons, event types, weekly/monthly breakdowns, EMA sides, distributions and clock-time coverage. Descriptive reconstructed-year evidence with explicit sample sizes.",
                  "publishedAt": "2026-10-17T19:38:30Z", "source": {"producer": "Sahadeva · Abacus study 25", "runId": self.run_id}, "sections": self.sections,
                  "downloads": downloads, "references": references, "notes": ["Saved-row controls select existing summary rows; they do not pool samples or calculate new statistics.", "combined = U.S. plus domestic; us_only = U.S.; local_only = domestic. Cohorts overlap and are not additive.", "Every percent-formatted web value divides the saved percentage-point value by 100. CSVs and figure percent axes retain original percentage points.", "Null/blank means unavailable. Observed zero and no observations remain different. Empirical percentiles and n<10 flags are descriptive."]}
        require(len(self.sections) <= 30, "Section count budget")
        write(self.directory / "publication.json", report)
        require((self.directory / "publication.json").stat().st_size <= 2*1024*1024, "Source JSON budget")
        self.charts()
        write(self.directory / "source-map.json", {"schema_version": "forex25-perfuture-saved-cells/v1", "study_id": SID, "run_id": self.run_id, "publication_id": self.pub_id,
              "source_row_base": 0, "projections": self.projections, "metrics": self.metrics, "chart_bindings": self.chart_bindings, "filter_defaults": self.filter_defaults,
              "coverage": getattr(self, "coverage_mapping", None), "claims": [{"section": x["id"], "sources": x.get("referenceIds", []), "status": "Authored explanation of retained source protocol and saved descriptive summaries"} for x in self.sections if x["kind"] == "text"]})
        result = subprocess.run([str(figure_python), str(Path(__file__).with_name("per_future_figures.py")), str(self.directory)], check=True)
        require(result.returncode == 0, "Figure drawing failed")

    def coverage(self):
        path = self.stage / "tables" / f"{self.symbol}-coverage.csv"
        if path.exists():
            fields, rows = csv_rows(path)
            require(len(fields) <= 12 and len(rows) <= 100, "Coverage table bounds")
            index = len(self.sections)
            self.sections.append({"id": "coverage", "title": "Calendar coverage and exclusions", "kind": "table", "columns": [{"key": f"c{i}", "label": key.replace("_", " ").capitalize()} for i, key in enumerate(fields)],
                                  "rows": [{f"c{i}": value(r[k]) for i, k in enumerate(fields)} for r in rows], "description": "The retained category inventory includes zero-coverage types. No selected eligible release means unavailable evidence, not a zero effect.",
                                  "notes": ["Strict timing requires a known exact 15-minute release boundary. Missing entry bars and unfixed/tentative decision times are excluded.", "A domestic release can appear exclusively in Mixed types when another selected type shares its timestamp."]})
            self.coverage_mapping = {"target": f"/sections/{index}/rows", "artifact": str(path.relative_to(self.stage)), "sha256": sha(path), "sourceRows": list(range(len(rows))), "columns": {f"c{i}": {"column": key, "operation": "identity"} for i, key in enumerate(fields)}}
        else:
            self.text("coverage", "Calendar coverage and exclusions", "Eligibility requires a known exact 15-minute release boundary and a confirmed entry bar. Off-grid and tentative/unfixed timestamps remain excluded. BoJ decisions and outlook announcements have no reliable preannounced clock time and are excluded even if a vendor supplies a nominal time.\n\nBoE, BoJ and SNB press-conference categories have no eligible selected observations in the source coverage; that absence does not imply no economic effect. For 6E, the GDP components in this selected year occur inside Mixed types and do not create a standalone combined GDP group. Retained exclusions distinguish missing entry bars, off-grid times and unreliable decision times.")


def pointer(doc, path):
    for part in path.strip("/").split("/"):
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc


def verify(stage: Path) -> dict:
    counts = {"publications": 0, "table_cells": 0, "download_cells": 0, "metric_cells": 0, "chart_cells": 0}
    for directory in sorted((stage / "publications").iterdir()):
        report_path = directory / "publication.json"
        if not report_path.exists():
            continue
        report, mapping, chart = load(report_path), load(directory / "source-map.json"), load(directory / "chart-spec.json")
        require(report["id"] == mapping["publication_id"] == directory.name, "Publication identity differs")
        cache = {}
        def source(artifact, expected_hash):
            if artifact not in cache:
                actual_hash = sha(stage / artifact)
                require(actual_hash == expected_hash, f"Saved source changed: {artifact}")
                cache[artifact] = (actual_hash, csv_rows(stage / artifact))
            require(cache[artifact][0] == expected_hash, "Inconsistent source pins")
            return cache[artifact][1]
        mapped_tables = set()
        for projection in [*mapping["projections"], *([mapping["coverage"]] if mapping.get("coverage") else [])]:
            _, rows = source(projection["artifact"], projection["sha256"])
            if projection["target"].startswith("/"):
                actual = pointer(report, projection["target"])
                require(len(actual) == len(projection["sourceRows"]), "Mapped table length differs")
                for target_row, source_row in zip(actual, projection["sourceRows"]):
                    require(set(target_row) == set(projection["columns"]), "Unmapped displayed cell")
                    for key, cell in projection["columns"].items():
                        require(target_row[key] == value(rows[source_row][cell["column"]], cell["operation"]), f"Saved cell differs: {projection['target']} {source_row}/{key}")
                        counts["table_cells"] += 1
                mapped_tables.add(projection["target"])
            else:
                actual_file = directory / projection["target"]
                require(actual_file.read_bytes() == (stage / projection["artifact"]).read_bytes(), "Public CSV is not byte-identical projection")
                headers, downloaded = csv_rows(actual_file)
                require(len(downloaded) == len(projection["downloadRows"]), "Download projection row count")
                for row, selected in zip(downloaded, projection["downloadRows"]):
                    family = selected["family"]
                    pin = projection["sources"][family]
                    _, originals = source(pin["artifact"], pin["sha256"])
                    original = originals[selected["row"]]
                    expected = {"family": family, "mode": original["mode"], "horizon_bars": original["horizon_bars"], "group": " | ".join(original[c] for c in selected["groupColumns"]) if selected["groupColumns"] else "All events", "period": original[selected["periodColumn"]] if selected["periodColumn"] else ""}
                    expected.update({c: original[c] for c in projection["metricColumns"]})
                    require(row == expected, "Download saved-cell projection differs")
                    counts["download_cells"] += len(row)
                require(set(headers) == set(downloaded[0]), "CSV columns differ")
        expected_tables = {f"/sections/{i}/rows" for i, section in enumerate(report["sections"]) if section["kind"] == "table"}
        require(mapped_tables == expected_tables, "A displayed table has no complete map")
        for key, bindings, document in [("metric_cells", mapping["metrics"], report), ("chart_cells", mapping["chart_bindings"], chart)]:
            require(len({b["pointer"] for b in bindings}) == len(bindings), "Duplicate source-map value pointer")
            for binding in bindings:
                _, rows = source(binding["artifact"], binding["sha256"])
                require(pointer(document, binding["pointer"]) == value(rows[binding["row"]][binding["column"]], binding["operation"]), f"Mapped value differs: {binding['pointer']}")
                counts[key] += 1
        for binding in mapping.get("filter_defaults", []):
            _, rows = source(binding["artifact"], binding["sha256"])
            require(pointer(report, binding["pointer"]) == value(rows[binding["row"]][binding["column"]], binding["operation"]), "Saved filter default differs")
        expected_metrics = {f"/sections/{i}/items/{j}/value" for i, section in enumerate(report["sections"]) if section["kind"] == "metrics" for j in range(len(section["items"]))}
        require({b["pointer"] for b in mapping["metrics"]} == expected_metrics, "Unmapped metric")
        def leaf_pointers(node, prefix=""):
            if isinstance(node, dict):
                return {path for key, item in node.items() for path in leaf_pointers(item, prefix+"/"+key)}
            if isinstance(node, list):
                return {path for i, item in enumerate(node) for path in leaf_pointers(item, prefix+"/"+str(i))}
            return {prefix}
        require({b["pointer"] for b in mapping["chart_bindings"]} == leaf_pointers(chart)-{"/symbol"}, "Unmapped plotted input")
        for item in report["downloads"]:
            headers, rows = csv_rows(directory / item["path"])
            require(headers == item["columns"] and len(rows) == item["rowCount"], "Declared download shape")
            require(sha(directory / item["path"]) == item["sha256"] == item["source"]["sha256"] == sha(stage / item["source"]["artifact"]), "Declared download hash")
            require((directory / item["path"]).stat().st_size <= 4*1024*1024, "Individual CSV byte bound")
        for item in report["references"]:
            require(sha(stage / item["artifact"]) == item["sha256"], "Saved reference changed")
        for section in report["sections"]:
            if section["kind"] == "table":
                require(len(section["columns"]) <= 12 and len(section["rows"]) <= (1500 if section.get("rowFilters") else 100), "Report table bound")
                initial = section["rows"]
                for filter in section.get("rowFilters", []):
                    if "defaultValue" in filter:
                        initial = [r for r in initial if r.get(filter["key"]) == filter["defaultValue"]]
                # Narada's existing initialSavedTable applies the authored saved
                # defaults, then slices the first page to 100 rows. Further
                # matching rows remain available through its saved pagination.
                if section.get("rowFilters"):
                    initial = initial[:100]
                require(len(initial) <= 100, "Initial table exceeds page bound")
        require(report_path.stat().st_size <= 2*1024*1024, "Report source bound")
        require(sum((directory / d["path"]).stat().st_size for d in report["downloads"]) <= 8*1024*1024, "Downloads total bound")
        figures = [directory / section["path"] for section in report["sections"] if section["kind"] == "figure"]
        require(all(p.is_file() and p.stat().st_size <= 2*1024*1024 for p in figures), "Individual figure bound")
        require(sum(p.stat().st_size for p in figures) <= 8*1024*1024, "Figure total bound")
        counts["publications"] += 1
    require(counts["publications"] == 6, "Exactly six contract publications are required")
    return counts


def finalize_publications(stage, run_id, counts):
    root = f"runs/{SID}/{run_id}"
    for directory in sorted((stage / "publications").iterdir()):
        report = load(directory / "publication.json")
        receipt = {"schema_version": "forex25-perfuture-publication-checks/v1", "status": "passed", "result": "passed", "publication_id": report["id"], "source_run_id": run_id,
                   "publication_sha256": sha(directory / "publication.json"), "source_map_sha256": sha(directory / "source-map.json"),
                   "checks": [{"name": "Every displayed table cell and metric equals its saved source cell", "passed": True}, {"name": "Every selected CSV cell and copied byte equals its saved projection", "passed": True}, {"name": "Every plotted input equals its saved summary cell", "passed": True}, {"name": "Conditional source/table/download budgets and initial row limits", "passed": True}],
                   "scope": "Publication transfer integrity only. Numerical aggregation and native-chart validation have separate retained checks.", "all_publications_cell_counts": counts}
        write(directory / "publication-verification.json", receipt)
        mapping = load(directory / "source-map.json")
        sources = {m["artifact"] for m in [*mapping["projections"], *mapping["metrics"], *mapping["chart_bindings"], *([mapping["coverage"]] if mapping.get("coverage") else [])]}
        sources.update(pin["artifact"] for p in mapping["projections"] for pin in p.get("sources", {}).values())
        outputs = [p for p in directory.rglob("*") if p.is_file() and p.name != "publication-manifest.json"]
        write(directory / "publication-manifest.json", {"publication_id": report["id"], "source_run_id": run_id, "study_id": SID,
              "source_artifacts": [{"path": f"{root}/{name}", "sha256": sha(stage / name)} for name in sorted(sources)],
              "outputs": [{"path": f"{root}/{p.relative_to(stage).as_posix()}", "sha256": sha(p)} for p in sorted(outputs)]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--figure-python", default=sys.executable, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        for symbol in SYMBOLS:
            Author(args.stage, symbol, args.run_id).build(args.figure_python)
    counts = verify(args.stage)
    if not args.check:
        finalize_publications(args.stage, args.run_id, counts)
    print(json.dumps({"status": "passed", **counts}, sort_keys=True))


if __name__ == "__main__":
    main()
