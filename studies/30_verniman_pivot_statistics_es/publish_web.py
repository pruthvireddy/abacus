"""Prepare bounded Narada 1.1 sources from saved Study 30 summaries only.

This does not publish or deploy. ``--check`` compares every displayed/downloaded
cell with the saved summary and checks selected asset bytes without reanalysis.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil

from src.reporting import LIMITS, SID, clean, read_csv, require, sha, write_json

SLUGS = ("overview", "price-ema", "followthrough", "cloud-vwap", "calendar", "retests")
TITLES = {
    "overview": "Opening state and recurrence", "price-ema": "Price breaks and EMA6 crossings",
    "followthrough": "Followthrough and excursions", "cloud-vwap": "Cloud and Globex VWAP context",
    "calendar": "Years, months and recent sessions", "retests": "Pivot retests after EMA6 crossings",
}
COLUMN_LABELS = {
    "period_kind": "Time grouping", "period": "Time period", "section": "Market section",
    "metric": "Measure", "denominator": "Valid observations", "days": "Distinct days",
    "valid_days": "Distinct valid days", "ci95_low": "95% CI low", "ci95_high": "95% CI high",
    "sparse": "Fewer than 30 days", "condition": "Context", "condition_value": "State",
    "panel": "Event sample", "event_type": "Reference event", "horizon": "Observation window",
    "direction": "Crossing direction", "events": "Selected events", "unknown": "Unavailable",
    "estimate": "Average", "median": "Median", "p25": "25th percentile", "p75": "75th percentile",
    "p90": "90th percentile", "zero_share": "No-event share", "snapshot": "Observation time",
    "category": "State", "rate": "Share", "unit": "Units", "mean_points": "Mean signed movement",
    "median_points": "Median signed movement", "positive_rate": "Close in crossing direction",
    "mean_favorable_points": "Mean favorable movement", "mean_adverse_points": "Mean adverse movement",
    "mean_ci95_low": "Mean: 95% CI low", "mean_ci95_high": "Mean: 95% CI high",
    "mean_bps": "Mean signed movement", "returned_without_new_cross": "Returned before new EMA cross",
    "actual_confirmed": "Actual EMA confirmations", "return_censored": "Return not observed",
    "mean_penetration_points": "Mean episode depth", "mean_confirmation_lag_minutes": "Mean wait for EMA crossing",
    "confirmation_denominator": "Resolved confirmation observations",
    "returned_without_new_cross_rate": "Return before EMA crossing",
    "unknown_or_censored_confirmation": "Confirmation unresolved",
    "mean_returned_unconfirmed_penetration_points": "Mean returned-break depth",
    "requested_start": "Requested start", "requested_cutoff": "Requested cutoff",
    "retained_market_data_end": "Retained data through", "requested_calendar_dates": "Requested calendar dates",
    "eligible_sessions": "Eligible sessions", "actual_eligible_start": "First eligible session",
    "actual_eligible_end": "Last eligible session", "historical_availability": "Historical availability",
    "from_section": "Earlier market section", "to_section": "Later market section",
    "from_state": "Earlier state", "to_state": "Later state", "complete_windows": "Complete 30-minute windows",
    "complete_window_touches": "Touches in complete windows", "touch_rate": "Retest incidence",
    "hold_rate": "Retest held", "failed_rate": "Retest failed", "equal_rate": "Retest closed at pivot",
    "censored": "Incomplete windows",
}
for _side, _label in (("favorable", "Favorable"), ("adverse", "Adverse")):
    for _points in (5, 10, 20):
        COLUMN_LABELS[f"{_side}_reach_{_points}_rate"] = f"{_label}: reached {_points} points"


def column(key, label=None, fmt=None, precision=2, unit=None):
    result = {"key": key, "label": label or COLUMN_LABELS.get(key, key.replace("_", " ").capitalize())}
    if fmt:
        result.update(format=fmt, precision=precision)
    if unit:
        result["unit"] = unit
    return result


NUMBER = {"denominator", "valid_days", "events", "days", "unknown", "returned_without_new_cross",
          "actual_confirmed", "return_censored", "complete_windows", "complete_window_touches", "censored"}
PERCENT = {"positive_rate", "zero_share", "rate", "touch_rate", "hold_rate", "failed_rate", "equal_rate"}


def columns(keys):
    result = []
    for key in keys:
        if key in NUMBER:
            result.append(column(key, fmt="number", precision=0))
        elif key in PERCENT or key.endswith("_rate"):
            result.append(column(key, fmt="percent", precision=1))
        elif key.endswith("points") or key.startswith("mean_ci") or key in ("ci95_low", "ci95_high"):
            result.append(column(key, fmt="number", precision=2, unit="ES points" if key.endswith("points") or key.startswith("mean_ci") else None))
        elif key in ("estimate", "median", "p90", "mean_confirmation_lag_minutes"):
            result.append(column(key, fmt="number", precision=2))
        elif key.endswith("_bps"):
            result.append(column(key, fmt="number", precision=2, unit="basis points"))
        else:
            result.append(column(key))
    return result


class Author:
    def __init__(self, stage, run_id, slug, published_at):
        self.stage, self.run_id, self.slug = Path(stage), run_id, slug
        suffix = re.sub(r"[^a-z0-9]+", "-", run_id.lower()).strip("-")
        self.identity = f"verniman-es-{slug}-{suffix}"
        require(len(self.identity) <= 80, "Publication ID exceeds 80 characters; use a shorter run ID")
        self.directory = self.stage / "publications" / self.identity
        require(not self.directory.exists(), f"Refusing to replace {self.directory}")
        self.sections, self.maps, self.asset_maps = [], [], []
        self.published_at = published_at

    def text(self, identity, title, body):
        self.sections.append({"id": identity, "title": title, "kind": "text", "body": body})

    def table(self, identity, title, artifact, keys, predicate=lambda row: True, filters=(), notes=()):
        source = read_csv(self.stage / artifact)
        selected = [(i, row) for i, row in enumerate(source) if predicate(row)]
        require(len(selected) <= (1500 if filters else 100), f"Row budget for {identity}")
        require(len(keys) <= 12, "Table column budget")
        rows = [{key: row.get(key) for key in keys} for _, row in selected]
        section = {"id": identity, "title": title, "kind": "table", "columns": columns(keys), "rows": rows,
                   "description": "Saved descriptive summaries. Filters select existing rows; counts, denominators and estimates are never recomputed in the browser.",
                   "notes": ["Sparse means fewer than 30 supporting distinct days. Null means unavailable; zero is observed zero. Periods and event panels overlap and cannot be added.", *notes]}
        if "section" in keys or "from_section" in keys:
            section["notes"].append("Market sections in New York time: opening_range = 09:30–10:30; new_york_am = 10:30–12:30; new_york_pm = 12:30–16:00. All combines the three sections.")
        if "snapshot" in keys:
            section["notes"].append("Observation labels: 0925 = 09:25; 0930 = 09:30; opening_range_end = 10:30; new_york_am_end = 12:30; new_york_pm_end = 16:00, all New York time.")
        if filters:
            section["rowFilters"] = []
            for key, label, default in filters:
                item = {"key": key, "label": label}
                if any(row.get(key) == default for row in rows):
                    item["defaultValue"] = default
                section["rowFilters"].append(item)
            initial = [r for r in rows if all(r.get(f["key"]) == f["defaultValue"] for f in section["rowFilters"] if "defaultValue" in f)]
            require(len(initial) <= 100, f"Initial table rows exceed 100: {identity}")
        index = len(self.sections)
        self.sections.append(section)
        self.maps.append({"target": f"/sections/{index}/rows", "artifact": artifact, "sha256": sha(self.stage / artifact),
                          "source_rows": [i for i, _ in selected], "columns": keys})

    def build(self):
        self.text("scope", TITLES[self.slug], "Requested ES calendar: 2020-01-01–2026-10-30. This release uses only repository-retained pivots and exact-contract OHLCV; retained market data ends 2026-09-18. The actual eligible dates and coverage limits are saved in the source run.\n\n" + "\n\n".join(LIMITS))
        daily = "tables/daily_summary.csv"
        outcomes = "tables/outcome_summary.csv"
        episodes = "tables/episode_summary.csv"
        retests = "tables/retest_summary.csv"
        overall = lambda r: r.get("period_kind") == "overall"
        baseline = lambda r: r.get("condition") == "all"
        price30 = lambda r: r.get("event_type") == "price_cross" and r.get("horizon") == "30m"
        if self.slug == "overview":
            self.table("coverage", "Requested calendar and actual sample", "tables/coverage_summary.csv",
                       ["requested_start", "requested_cutoff", "retained_market_data_end", "requested_calendar_dates", "eligible_sessions", "actual_eligible_start", "actual_eligible_end", "historical_availability"],
                       notes=("Requested calendar-date count includes weekends/holidays. Eligible sessions are a selected retrospective sample; excluded dates/contracts retain reasons in the source run.",))
            self.table("recurrence", "Daily and section recurrence", daily,
                       ["period_kind", "period", "section", "metric", "denominator", "estimate", "median", "p90", "zero_share", "ci95_low", "ci95_high", "sparse"],
                       lambda r: r.get("metric") in ("price_crosses", "ema_crosses", "touch_bars"),
                       (("period_kind", "Calendar", "overall"), ("section", "Section", "all"), ("metric", "Measure", "price_crosses")),
                       ("Counts include eligible zero-event days. CI columns apply to overall daily means only; measure units are counts per day or day-section.",))
            self.table("recurrence-rates", "Crossings per observed hour", daily,
                       ["period_kind", "period", "section", "metric", "denominator", "estimate", "median", "p90", "zero_share", "ci95_low", "ci95_high", "sparse"],
                       lambda r: r.get("metric") in ("price_crosses_per_hour", "ema_crosses_per_hour"),
                       (("period_kind", "Calendar", "overall"), ("section", "Section", "all"), ("metric", "Measure", "price_crosses_per_hour")),
                       ("Units are crossings per observed hour. Exposure is the count of valid native three-minute price or ready-EMA observations × 3/60 hours; zero exposure is unavailable. Values shown are averages of per-day or per-section rates, retaining zero-cross observations.",))
            self.table("opening", "Pre-open and opening indicator states", "tables/opening_summary.csv",
                       ["snapshot", "metric", "category", "days", "denominator", "rate", "sparse"], overall,
                       (("snapshot", "Snapshot", "0930"), ("metric", "Indicator state", "cloud_order")),
                       ("09:25 and 09:30 are distinct as-of snapshots. Opening price uses the actual 09:30 open; indicators use only completed values.",))
            figure = self.stage / "figures/price-ema-30m.png"
            if figure.is_file():
                self.sections.append({"id": "ema-state-figure", "title": "EMA6 state at a price break", "kind": "figure", "path": "figures/price-ema-30m.png",
                                      "alt": "Saved mean 30-minute signed ES-point displacement by EMA6 state at the price cross, with event and distinct-day support.",
                                      "caption": "Saved 30-minute price-cross summaries. EMA6 already aligned and an actual same-close crossing are separate. Descriptive conditional differences do not establish a trading edge."})
                self.asset_maps.append({"source": "figures/price-ema-30m.png", "target": "figures/price-ema-30m.png", "sha256": sha(figure)})
        elif self.slug == "price-ema":
            self.text("reading", "Read signal-time state separately from later path", "An actual EMA6 pivot crossing requires a strict side change on a completed three-minute close. Already aligned is not a new crossing. Returned without a new EMA crossing is a label known only at the reverse price close. Censored episodes have not demonstrated a return. Measured penetration describes shallowness without a fitted shallow/deep cutoff.")
            self.table("episodes", "Price episodes: later confirmation and return", episodes,
                       ["period_kind", "period", "panel", "condition", "condition_value", "events", "days", "returned_without_new_cross", "actual_confirmed", "return_censored", "mean_penetration_points", "mean_confirmation_lag_minutes"],
                       lambda r: r.get("period_kind") in ("overall", "year", "recent") and r.get("direction") == "all" and r.get("section") == "all",
                       (("period_kind", "Calendar", "overall"), ("panel", "Event panel", "all_crosses"), ("condition", "Grouping", "ema_state_at_cross")),
                       ("Episode labels are future-conditioned descriptions. An initially aligned EMA6 must not be merged with initially opposite EMA6 merely because neither makes a new crossing before return.",
                        "Return-censored means no reverse price cross before the observed endpoint. The same episode may already be EMA-confirmed; return censoring and confirmation censoring differ and their counts can overlap."))
            self.table("initially-unconfirmed", "Initially unconfirmed breaks: return before actual EMA6 crossing", episodes,
                       ["panel", "condition_value", "events", "days", "returned_without_new_cross", "actual_confirmed", "confirmation_denominator", "returned_without_new_cross_rate", "unknown_or_censored_confirmation", "return_censored", "mean_returned_unconfirmed_penetration_points", "sparse"],
                       lambda r: overall(r) and r.get("direction") == "all" and r.get("section") == "all" and r.get("condition") == "initial_confirmation_state",
                       (("panel", "Event panel", "all_crosses"), ("condition_value", "Initial state", "initially_unconfirmed")),
                       ("The primary returned-break cohort initially has opposite/equal/uninitialized EMA6. Already-aligned and same-close actual EMA6 crossings remain separate. The return-before-EMA rate denominator is resolved actual confirmation OR reverse price close before confirmation; unresolved censored observations are not failures. Penetration describes shallowness without a fitted cutoff.",))
            self.table("ema-state", "30-minute outcomes by EMA6 state known at the price cross", outcomes,
                       ["panel", "condition_value", "denominator", "valid_days", "unknown", "mean_points", "positive_rate", "mean_favorable_points", "mean_adverse_points", "mean_ci95_low", "mean_ci95_high", "sparse"],
                       lambda r: overall(r) and price30(r) and r.get("condition") == "ema_state_at_cross",
                       (("panel", "Event panel", "all_crosses"),),
                       ("Positive close means displacement in the crossing direction, before costs. Unknown includes late or incomplete 30-minute paths.",))
        elif self.slug == "followthrough":
            self.text("horizons", "Fixed horizons and variable endpoints", "The primary outcome is 30 minutes; 15/60 minutes and section/16:00 endpoints provide context. Fixed horizons cannot extend past RTH. Excursions exclude the completed signal bar's earlier high/low. Delayed-confirmation outcomes start at the confirmation close. Favorable/adverse threshold touches do not establish executable fill order.")
            filters = (("event_type", "Event", "price_cross"), ("horizon", "Horizon", "30m"), ("panel", "Event panel", "all_crosses"))
            predicate = lambda r: overall(r) and baseline(r)
            self.table("outcomes", "Directional displacement and excursions", outcomes,
                       ["event_type", "horizon", "panel", "direction", "section", "denominator", "valid_days", "unknown", "mean_points", "positive_rate", "mean_favorable_points", "mean_adverse_points"], predicate, filters)
            self.table("reach", "Favorable and adverse ES-point reach", outcomes,
                       ["event_type", "horizon", "panel", "direction", "section", "denominator", "favorable_reach_5_rate", "favorable_reach_10_rate", "favorable_reach_20_rate", "adverse_reach_5_rate", "adverse_reach_10_rate", "adverse_reach_20_rate"], predicate, filters,
                       ("Thresholds are 5/10/20 ES points from the event reference close. Both favorable and adverse thresholds can occur in one horizon; their order is not inferred.",))
        elif self.slug == "cloud-vwap":
            self.text("features", "Indicator context available at the event", "The EMA20/50 cloud always uses completed five-minute bars. EMA6 uses three-minute bars. Globex VWAP accumulates one-minute HLC3/volume from 18:00 New York. Slopes are 15-minute changes; cloud width is the absolute EMA spread. Each grouping below changes one condition at a time rather than constructing an unrestricted small-cell cube.\n\nEMA-cloud alignment requires EMA6 strictly on the event side, cloud ordering in that direction and both EMA20/50 15-minute changes strictly in that direction. EMA-VWAP alignment requires EMA6 on the event side and price on that side of VWAP. Combined alignment requires both. Already-aligned EMA6 can satisfy these alignment conditions; an actual new EMA6 crossing is a separate condition. Missing required state/slope remains unknown. Confirmation references use their own later state.")
            self.table("conditions", "30-minute one-way indicator conditions", outcomes,
                       ["event_type", "panel", "condition", "condition_value", "denominator", "valid_days", "unknown", "mean_points", "positive_rate", "mean_favorable_points", "mean_adverse_points", "sparse"],
                       lambda r: overall(r) and r.get("horizon") == "30m" and r.get("condition") not in ("all", "ema_state_at_cross", "confirmation_kind"),
                       (("event_type", "Event", "price_cross"), ("panel", "Event panel", "all_crosses"), ("condition", "Context", "cloud_order")))
            self.table("numeric-context", "Opening and endpoint indicator distributions", "tables/snapshot_numeric_summary.csv",
                       ["snapshot", "metric", "unit", "denominator", "unknown", "estimate", "median", "p25", "p75", "p90", "sparse"], overall,
                       (("snapshot", "Snapshot", "0930"), ("unit", "Units", "points"), ("metric", "Measure", "cloud_width")),
                       ("Basis points of pivot are 10000 × distance / pivot. Width and slope changes retain signed/absolute definitions from the study protocol; source snapshots are completed-bar as-of values.",))
            self.table("transitions", "Section-to-section closing-state transitions", "tables/section_transitions.csv",
                       ["from_section", "to_section", "metric", "from_state", "to_state", "days", "denominator", "rate", "sparse"],
                       filters=(("metric", "State", "closing_side"),))
        elif self.slug == "calendar":
            self.text("calendar-guide", "Calendar support and recent windows", "Years and calendar months use session dates; month-of-year pools the same named month across years. Recent windows are the last 20/60/120 eligible observed sessions at the requested 2026-10-30 cutoff, with actual latest usable date saved in each source row. They do not imply market data exists through that requested date. Empty calendar periods are no sample. These panels are descriptive stability checks, not independent replications.")
            for panel in ("all_crosses", "first_per_day", "first_per_section"):
                self.table("calendar-" + panel.replace("_", "-"), panel.replace("_", " ").capitalize() + " · 30-minute price outcomes", outcomes,
                           ["period_kind", "period", "direction", "section", "denominator", "valid_days", "unknown", "mean_points", "median_points", "positive_rate", "mean_bps", "sparse"],
                           lambda r, p=panel: price30(r) and baseline(r) and r.get("panel") == p,
                           (("period_kind", "Calendar", "year"), ("direction", "Direction", "all"), ("section", "Section", "all")))
        else:
            self.text("retest-rule", "First subsequent exact-pivot touch", "After an actual EMA6 crossing, seek the first subsequent completed three-minute bar containing the exact pivot, completed within 30 minutes or by 16:00, whichever comes first. Exclude the signal bar. Hold/failed/equal describe the retest bar's close relative to crossing direction. Touch time is resolved to a three-minute bar; no intrabar order is inferred.")
            self.table("retests", "Retest incidence and touch-bar behavior", retests,
                       ["period_kind", "period", "direction", "section", "events", "complete_windows", "complete_window_touches", "touch_rate", "hold_rate", "failed_rate", "equal_rate", "censored"],
                       filters=(("period_kind", "Calendar", "overall"), ("direction", "Direction", "all"), ("section", "Section", "all")),
                       notes=("Touch incidence uses fully observed 30-minute windows only. Hold/failed/equal rates use all observed first touches, including an observed touch in a shorter available window; these denominators differ.",))
        self.text("limits", "Evidence qualifications", "\n\n".join(LIMITS) + "\n\nOverall daily means and overall 30-minute outcome mean/positive shares use 2,000 non-circular moving-block replicates of five observed sessions, seed 20261031. Whole-day records preserve repeated-event dependence. No multiple-testing or source-selection correction is implied. Negative and inconclusive cells are retained.")
        report = {"schemaVersion": "1.1", "id": self.identity, "title": "Verniman Pivot Statistics — ES · " + TITLES[self.slug],
                  "summary": "Repository-only descriptive ES pivot research with saved cohort filters. Historical pivot availability is unverified; price paths and excursions are not net trading returns.",
                  "publishedAt": self.published_at, "source": {"producer": "sahadeva", "runId": self.run_id},
                  "sections": self.sections, "notes": list(LIMITS)}
        self.directory.mkdir(parents=True)
        for item in self.asset_maps:
            destination = self.directory / item["target"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.stage / item["source"], destination)
        download = self.download()
        if download:
            report["downloads"] = [download]
        write_json(self.directory / "publication.json", report)
        require((self.directory / "publication.json").stat().st_size <= 2 * 1024 * 1024, "Filtered report source budget")
        write_json(self.directory / "source-map.json", {"schema_version": "abacus.study30.publication-map/v1", "publication_id": self.identity,
                  "source_run_id": self.run_id, "table_projections": self.maps, "assets": self.asset_maps,
                  "scope": "Every saved displayed/downloaded cell and selected asset byte. Does not establish numerical validity or pixel-level plot correctness."})
        return self.directory

    def download(self):
        if not self.maps:
            return None
        mapping = self.maps[0]
        with (self.stage / mapping["artifact"]).open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        selected = [{key: rows[i].get(key, "") for key in mapping["columns"]} for i in mapping["source_rows"]]
        if not selected:
            return None
        saved = self.stage / "tables" / f"publication-{self.slug}.csv"
        require(not saved.exists(), f"Refusing to replace download projection {saved}")
        with saved.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=mapping["columns"])
            writer.writeheader()
            writer.writerows(selected)
        require(saved.stat().st_size <= 256 * 1024, "CSV download byte budget")
        destination = self.directory / "downloads" / f"{self.slug}.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(saved, destination)
        mapping["download"] = {"saved_artifact": str(saved.relative_to(self.stage)), "target": f"downloads/{self.slug}.csv", "sha256": sha(saved)}
        return {"id": "summary", "path": f"downloads/{self.slug}.csv", "label": TITLES[self.slug] + " · selected saved summaries",
                "description": "Exact saved summary strings from this report's first table, across its saved filter choices; no raw event or market-price ledger.",
                "population": "Selected retrospectively eligible ES days and events using the source-quoted delivery contract. Repeated-event panels and calendar windows overlap.",
                "units": "ES points for distance/return fields; rate/share columns are ratios, where 0.42 means 42%. Blank is unavailable; zero is observed zero.",
                "scope": "Selected bounded summaries only. Counts and denominators retain their table-specific meaning; this is not net P&L or an independently verified trading edge.",
                "mediaType": "text/csv", "sha256": sha(destination), "rowCount": len(selected), "columns": mapping["columns"],
                "source": {"runId": self.run_id, "artifact": str(saved.relative_to(self.stage)), "sha256": sha(saved)}}


def pointer(document, path):
    value = document
    for part in path.strip("/").split("/"):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def verify(stage, *, run_id=None):
    stage = Path(stage)
    count, cells, assets = 0, 0, 0
    for directory in sorted((stage / "publications").iterdir()):
        if not directory.is_dir():
            continue
        report = json.loads((directory / "publication.json").read_text())
        mapping = json.loads((directory / "source-map.json").read_text())
        require(report["id"] == directory.name == mapping["publication_id"], "Publication identity mismatch")
        if run_id:
            require(report["source"]["runId"] == run_id == mapping["source_run_id"], "Source run mismatch")
        for projection in mapping["table_projections"]:
            source = stage / projection["artifact"]
            require(sha(source) == projection["sha256"], "Saved summary hash changed")
            rows = read_csv(source)
            expected = [{key: rows[i].get(key) for key in projection["columns"]} for i in projection["source_rows"]]
            require(pointer(report, projection["target"]) == expected, "Displayed source-cell mismatch")
            cells += len(expected) * len(projection["columns"])
            if projection.get("download"):
                download = projection["download"]
                require(sha(stage / download["saved_artifact"]) == download["sha256"] == sha(directory / download["target"]), "Download byte mismatch")
                with source.open(newline="", encoding="utf-8") as stream:
                    original = list(csv.DictReader(stream))
                with (directory / download["target"]).open(newline="", encoding="utf-8") as stream:
                    actual = list(csv.DictReader(stream))
                strings = [{key: original[i].get(key, "") for key in projection["columns"]} for i in projection["source_rows"]]
                require(actual == strings, "Downloaded source-cell mismatch")
                cells += len(actual) * len(projection["columns"])
        for asset in mapping["assets"]:
            require(sha(stage / asset["source"]) == asset["sha256"] == sha(directory / asset["target"]), "Selected asset mismatch")
            assets += 1
        for section in report["sections"]:
            if section["kind"] == "table":
                require(len(section["columns"]) <= 12 and len(section["rows"]) <= (1500 if section.get("rowFilters") else 100), "Table budget")
        count += 1
    require(count == 6, "Exactly six bounded publications required")
    return {"publications": count, "checked_cells": cells, "checked_assets": assets}


def finalize(stage, run_id, counts):
    stage = Path(stage)
    root = f"runs/{SID}/{run_id}"
    for directory in sorted((stage / "publications").iterdir()):
        if not directory.is_dir():
            continue
        report = json.loads((directory / "publication.json").read_text())
        mapping = json.loads((directory / "source-map.json").read_text())
        receipt = {"schema_version": "abacus.study30.publication-checks/v1", "result": "passed",
                   "publication_id": report["id"], "source_run_id": run_id,
                   "publication_sha256": sha(directory / "publication.json"), "source_map_sha256": sha(directory / "source-map.json"),
                   "checks": [{"name": "Every selected table/download cell matches saved evidence", "passed": True},
                              {"name": "Every selected asset byte and bounded table matches its declaration", "passed": True}],
                   "counts": counts, "scope": "Saved-content transfer integrity; numerical and application verification are separate."}
        write_json(directory / "publication-verification.json", receipt)
        sources = {p["artifact"] for p in mapping["table_projections"]}
        sources.update(p["download"]["saved_artifact"] for p in mapping["table_projections"] if p.get("download"))
        sources.update(p["source"] for p in mapping["assets"])
        outputs = [p for p in directory.rglob("*") if p.is_file() and p.name != "publication-manifest.json"]
        write_json(directory / "publication-manifest.json", {"publication_id": report["id"], "source_run_id": run_id, "study_id": SID,
                   "source_artifacts": [{"path": f"{root}/{name}", "sha256": sha(stage / name)} for name in sorted(sources)],
                   "outputs": [{"path": f"{root}/{p.relative_to(stage).as_posix()}", "sha256": sha(p)} for p in sorted(outputs)]})


def prepare(stage, run_id, published_at=None):
    stage = Path(stage)
    published_at = published_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    require(not (stage / "publications").exists(), "Refusing to overwrite publication sources")
    for slug in SLUGS:
        Author(stage, run_id, slug, published_at).build()
    counts = verify(stage, run_id=run_id)
    finalize(stage, run_id, counts)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = verify(args.stage, run_id=args.run_id) if args.check else prepare(args.stage, args.run_id)
    print(json.dumps({"status": "passed", **clean(result)}, sort_keys=True))


if __name__ == "__main__":
    main()
