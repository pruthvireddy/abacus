"""Prepare two bounded Narada reports from saved ranked summaries.

This presentation phase never reads market ledgers or computes estimates.  Its
projection receipt binds each displayed scalar, composed selection label, CSV
cell and raster asset to saved summary rows.  It does not publish or deploy.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import textwrap

from src.reporting import LIMITS, SID, clean, read_csv, require, sha, write_csv, write_json


SUMMARY = "tables/ranked_summary.csv"
SLUGS = ("pivot-statistics", "globex-vwap-statistics")
TITLES = {"pivot-statistics": "Pivot statistics", "globex-vwap-statistics": "Globex VWAP statistics"}
QUESTIONS = (
    "EMA6–VWAP crossing frequency", "EMA6–pivot crossing frequency",
    "Zero, one and multiple-cross days", "Crossings per observed hour",
    "Price versus EMA6 crossing counts", "Return before EMA confirmation",
    "Unconfirmed-break depth", "Confirmation delay and movement",
    "Post-cross directional movement", "Excursions and reach", "No-recross probability",
    "First-cross timing", "First versus later crossings", "Travel between pivot and VWAP",
    "Opening configuration and later path", "Cloud support versus opposition",
    "Opening pivot–VWAP separation", "Pivot retest after an EMA6 crossing",
    "Section-to-section persistence", "Recent versus earlier behavior",
)
VWAP_STATS = frozenset(("S01", "S03", "S04", "S05", "S09", "S10", "S11", "S12", "S13", "S16", "S19", "S20"))
CALENDAR_STATS = frozenset(("S01", "S02", "S03", "S04", "S05", "S09", "S11", "S12", "S20"))
SELECTION_KEYS = ("cohort", "reference", "series", "session_mode", "section", "direction", "panel", "horizon", "condition", "condition_value")
PUBLIC_KEYS = ("period", "selection", "metric", "value", "median", "share", "numerator", "denominator", "days", "unknown", "censored", "coverage")
SOURCE_KEYS = ("statistic_id", "cohort", "reference", "series", "session_mode", "section", "direction", "panel", "horizon", "condition", "condition_value", "metric", "unit", "estimate", "median", "numerator", "denominator", "days", "unknown", "censored", "earliest_session", "latest_session", "ci95_low", "ci95_high")


def identity(run_id, slug):
    suffix = re.sub(r"[^a-z0-9]+", "-", run_id.lower()).strip("-")
    value = f"verniman-es-{slug}-{suffix}"
    require(len(value) <= 80, "Publication ID exceeds 80 characters; use a shorter run ID")
    return value


def selection(row):
    labels = {
        "pivot_matched_rth": "Pivot-matched", "vwap_only_rth": "VWAP-only RTH", "vwap_only_globex": "VWAP-only Globex",
        "vwap_only_full_globex": "VWAP-only Globex", "rth": "RTH", "globex": "Globex", "ema6": "EMA6", "price": "Price",
        "opening_range": "Opening range", "new_york_am": "AM", "new_york_pm": "PM",
        "all_crosses": "All crosses", "first_per_day": "First/day", "first_per_section": "First/section",
    }
    label = lambda value: labels.get(value, str(value))
    parts = [label(row.get("cohort")), label(row.get("session_mode")),
             f"{label(row.get('series'))}/{label(row.get('reference'))}",
             "All sections" if row.get("section") in (None, "all") else label(row["section"]),
             "Both directions" if row.get("direction") in (None, "all") else f"{label(row['direction'])} direction",
             label(row.get("panel", "all_crosses"))]
    if row.get("horizon") not in (None, "", "none", "all"):
        parts.append(str(row["horizon"]))
    if row.get("condition") not in (None, "", "all"):
        parts.append(f"{row['condition']}={row.get('condition_value')}")
    return " · ".join(parts)


def projected(row):
    fraction = row.get("unit") in ("fraction", "ratio", "share", "probability")
    first, last = row.get("earliest_session", row.get("earliest")), row.get("latest_session", row.get("latest"))
    return dict(zip(PUBLIC_KEYS, (
        f"{row.get('period_kind', 'overall')}: {row.get('period', 'all')}", selection(row),
        f"{row.get('metric')} [{row.get('unit')}]", None if fraction else row.get("estimate"),
        None if fraction else row.get("median"), row.get("estimate") if fraction else None, row.get("numerator"), row.get("denominator"),
        row.get("days"), row.get("unknown"), row.get("censored"),
        f"{first}–{last}" if first is not None and last is not None else "No valid observations",
    )))


def baseline(row):
    return (row.get("direction") in (None, "all") and row.get("section") in (None, "all", "rth", "globex")
            and row.get("panel") in (None, "all", "all_crosses")
            and row.get("condition") in (None, "all"))


def selected_rows(rows, slug):
    """Authored, outcome-independent public scope; complete evidence stays private."""
    months = sorted({str(r.get("period")) for r in rows if r.get("period_kind") == "calendar_month" and r.get("denominator", 0) > 0})[-12:]
    result = []
    for index, row in enumerate(rows):
        if slug == "pivot-statistics":
            if row.get("cohort") != "pivot_matched_rth":
                continue
        elif row.get("cohort") not in ("vwap_only_rth", "vwap_only_globex", "vwap_only_full_globex") or row.get("reference") not in (None, "vwap") or row.get("statistic_id") not in VWAP_STATS:
            continue
        # The priority forward views concern actual EMA6 line crossings.
        # Complete price-cross outcomes remain in private evidence/baseline.
        if row.get("statistic_id") in ("S09", "S10", "S15", "S16", "S17", "S20") and row.get("series") not in (None, "ema6"):
            continue
        kind, horizon = row.get("period_kind"), row.get("horizon")
        if kind == "overall":
            # Vary at most one of direction/section/event-panel outside baseline.
            axes = sum((row.get("direction") not in (None, "all"),
                        row.get("section") not in (None, "all", "rth", "globex"),
                        row.get("panel") not in (None, "all", "all_crosses")))
            if axes > 1 or axes and horizon not in (None, "", "none", "30m", "30", "all"):
                continue
            if row.get("condition") not in (None, "all") and (axes or horizon not in (None, "", "none", "30m", "30", "all")):
                continue
        elif kind in ("year", "calendar_month", "recent", "earlier", "preceding"):
            if kind in ("year", "calendar_month") and row.get("statistic_id") not in CALENDAR_STATS:
                continue
            # Ranked conditional questions have no artificial unconditioned
            # counterpart: keep their authored single-condition baseline rows.
            intrinsic = row.get("statistic_id") in ("S03", "S08", "S12", "S13", "S14", "S15", "S16", "S17", "S18", "S19", "S20")
            support_baseline = baseline({**row, "condition": "all"}) if intrinsic else baseline(row)
            if not support_baseline or horizon not in (None, "", "none", "30m", "30", "all"):
                continue
            if kind == "calendar_month" and str(row.get("period")) not in months:
                continue
            if row.get("statistic_id") == "S12" and row.get("metric") == "first_cross_timing":
                continue
            if row.get("statistic_id") == "S19" and ("opening_range→new_york_pm:ema6_side:" not in str(row.get("condition_value"))):
                continue
        else:
            continue
        result.append((index, row))
    return result


def columns():
    labels = {"period": "Saved time period", "selection": "Population and event selection", "metric": "Measure",
              "value": "Mean estimate", "median": "Median", "share": "Percentage", "numerator": "Numerator / sum",
              "denominator": "Valid denominator", "days": "Distinct supporting days", "unknown": "Missing / unknown",
              "censored": "Censored", "coverage": "Actual valid date coverage"}
    return [{"key": key, "label": labels[key], **({"format": "percent", "precision": 1} if key == "share" else
             {"format": "number", "precision": 3 if key in ("value", "median", "numerator") else 0} if key in ("value", "median", "numerator", "denominator", "days", "unknown", "censored") else {})}
            for key in PUBLIC_KEYS]


def table_section(statistic, rows):
    require(len(rows) <= 1500, f"Public table {statistic} exceeds 1,500 rows; refine authored projection")
    require(bool(rows), f"No saved applicable rows for {statistic}")
    preferred = next((r for r in rows if r["period"].startswith("overall:") and "Both directions" in r["selection"] and "All sections" in r["selection"] and "All crosses" in r["selection"]), rows[0])
    filters = [{"key": key, "label": label, "defaultValue": preferred[key]}
               for key, label in (("period", "Time period"), ("selection", "Saved population and event view"), ("metric", "Measure"))]
    initial = [row for row in rows if all(row[f["key"]] == f["defaultValue"] for f in filters)]
    require(len(initial) <= 100, f"Too many default rows for {statistic}")
    return {"id": statistic.lower(), "title": f"{int(statistic[1:])}. {QUESTIONS[int(statistic[1:]) - 1]}", "kind": "table",
            "description": "Saved descriptive estimates. Select an existing population and measure; the browser performs no statistical calculation.",
            "columns": columns(), "rows": rows, "rowFilters": filters,
            "notes": ["Percentage is a typed ratio displayed as a percentage. Other mean/median estimates use the explicit units in the measure label. Numerator / sum is the success count for percentages and the sum of observed values for other means.",
                      "Denominator and distinct supporting days apply to that measure. Fewer than 30 days is sparse; null is unavailable and zero is observed zero. Censoring and missingness can overlap.",
                      "Selected frequency, movement, recross and timing calendars retain all years and the latest 12 available calendar months. Other ranked measures retain overall/recent comparisons here; complete annual/monthly evidence remains private. Forward views concern actual EMA6 crossings and emphasize 30 minutes outside overall baselines.",
                      "Opening range 09:30–10:30; AM 10:30–12:30; PM 12:30–16:00, New York time. Events use three-minute bar opens for section membership and become observable at the close."]
                     + (["First-cross minutes are measured from 09:30 for RTH and the preceding 18:00 for Globex, including section-selected views. Timing bins identify completion time; the final 30-minute bin includes the session endpoint. No-cross days remain an explicit category."] if statistic == "S12" else [])}


def _chart_svg(title, entries):
    """Lay out saved numeric values; no estimates or statistics are calculated."""
    width, height = 1440, 200 + 68 * max(len(entries), 1)
    values = [e["value"] for e in entries if isinstance(e["value"], (int, float))]
    low, high = min([0, *values]), max([0, *values])
    span = high - low or 1
    scale = lambda value: 620 + (value - low) / span * 510
    esc = lambda value: html.escape(str(value), quote=True)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             f"<title>{esc(title)}</title>", '<rect width="100%" height="100%" fill="#f7f9fc"/>',
             '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#193048}.title{font-size:29px;font-weight:700}.label{font-size:17px}.detail{font-size:15px;fill:#52677d}</style>',
             f'<text class="title" x="36" y="48">{esc(title)}</text>',
             '<text class="detail" x="36" y="80">Saved estimates only · each row retains its own population and denominator</text>']
    for n, item in enumerate(entries):
        y, value = 126 + n * 68, item["value"]
        wrapped = textwrap.wrap(item["label"], width=72, break_long_words=False, break_on_hyphens=False)
        require(len(wrapped) <= 2, "Saved chart label exceeds two readable lines")
        for line, text in enumerate(wrapped):
            parts.append(f'<text class="label" x="36" y="{y - 7 + line * 23}">{esc(text)}</text>')
        if isinstance(value, (int, float)):
            x0, x1 = sorted((scale(0), scale(value)))
            parts.extend((f'<rect data-value="{value}" x="{x0:.4f}" y="{y - 20}" width="{max(x1 - x0, 1):.4f}" height="28" fill="{"#9a6376" if value < 0 else "#356e91"}" rx="3"/>',
                          f'<text class="label" x="1150" y="{y}">{esc(f"{value:.3f}")} {esc(item["unit"])}</text>'))
        else:
            parts.append(f'<text class="label" x="1150" y="{y}">Unavailable</text>')
        parts.append(f'<text class="detail" x="620" y="{y + 28}">n={esc(item["denominator"])} · {esc(item["days"])} days · {esc(item["coverage"])}</text>')
    parts.extend((f'<text class="detail" x="36" y="{height - 25}">Exploratory behavior; no fills, costs or profitability claim. Sparse means fewer than 30 supporting days.</text>', '</svg>'))
    return "\n".join(parts)


def _chart_candidates(chosen, statistic):
    statistics = ("S01", "S02") if statistic == "S01" else (statistic,)
    candidates = [(i, r) for i, r in chosen if r.get("statistic_id") in statistics and baseline({**r, "condition": "all"})]
    if statistic == "S20":
        candidates = [(i, r) for i, r in candidates if r.get("period_kind") in ("recent", "earlier", "preceding")]
    else:
        candidates = [(i, r) for i, r in candidates if r.get("period_kind") == "overall"]
    desired = {"S01": "crosses", "S12": "first_cross_timing", "S19": "state_persists"}.get(statistic)
    if desired and any(r.get("metric") == desired for _, r in candidates):
        candidates = [(i, r) for i, r in candidates if r.get("metric") == desired]
    if statistic == "S12":
        matched = any(r.get("cohort") == "pivot_matched_rth" for _, r in candidates)
        cohort, reference, mode = (("pivot_matched_rth", "pivot", "rth") if matched else ("vwap_only_full_globex", "vwap", "globex"))
        candidates = [(i, r) for i, r in candidates if r.get("cohort") == cohort and r.get("reference") == reference
                      and r.get("session_mode") == mode and r.get("metric") == "first_cross_timing"
                      and r.get("condition") == "minutes_from_session_start"
                      and re.match(r"^\d+–", str(r.get("condition_value")))]
        candidates.sort(key=lambda item: int(str(item[1]["condition_value"]).split("–", 1)[0]))
    if candidates:
        # A single saved measure and unit per chart prevents incomparable bars.
        first = candidates[0][1]
        candidates = [(i, r) for i, r in candidates if r.get("metric") == first.get("metric") and r.get("unit") == first.get("unit")]
    return candidates[:12]


def _chart_entry(row):
    return {"label": " · ".join(str(row.get(k)) for k in ("cohort", "reference", "period", "condition_value") if row.get(k) not in (None, "", "all")),
            "value": row.get("estimate"), "unit": row.get("unit"), "denominator": row.get("denominator"), "days": row.get("days"),
            "coverage": f"{row.get('earliest_session', row.get('earliest'))}–{row.get('latest_session', row.get('latest'))}"}


def render_charts(stage, slug, chosen):
    stage = Path(stage)
    assets, sections = [], []
    for statistic, name in (("S01", "Crossing frequency"), ("S12", "First-cross timing"), ("S19", "Section persistence"), ("S20", "Recent and earlier history")):
        candidates = _chart_candidates(chosen, statistic)
        if not candidates:
            continue
        artifact = f"figures/{slug}-{statistic.lower()}"
        entries = [_chart_entry(row) for _, row in candidates]
        inputs = {"artifact": SUMMARY, "sha256": sha(stage / SUMMARY), "source_rows": [i for i, _ in candidates],
                  "rows": [r for _, r in candidates], "entries": entries, "title": name}
        write_json(stage / f"{artifact}-inputs.json", inputs)
        svg = stage / f"{artifact}.svg"
        require(not svg.exists(), "Refusing to overwrite saved chart")
        svg.write_text(_chart_svg(name, entries), encoding="utf-8")
        png = stage / f"{artifact}.png"
        script = "const s=require(process.argv[1]);s(process.argv[2]).png().toFile(process.argv[3]).then(()=>process.stdout.write(JSON.stringify(s.versions)))"
        app_module = Path(__file__).resolve().parents[2] / "apps/narada/node_modules/sharp"
        command = ["node", "-e", script, str(app_module), str(svg), str(png)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        require(result.returncode == 0, f"Saved chart rasterizer failed: {result.stderr}")
        write_json(stage / f"{artifact}-render.json", {"renderer": "sharp-svg", "command": command, "versions": json.loads(result.stdout),
                   "input_sha256": sha(stage / f"{artifact}-inputs.json"), "svg_sha256": sha(svg), "png_sha256": sha(png)})
        assets.append({"source": f"{artifact}.png", "target": f"{artifact}.png", "sha256": sha(png),
                       "inputs": f"{artifact}-inputs.json", "svg": f"{artifact}.svg", "receipt": f"{artifact}-render.json"})
        caption = "A bounded illustration of saved summary cells. Populations remain separate. Complete measures, horizons and missing/censored support are retained in the corresponding saved tables; no trading profitability is inferred."
        if statistic == "S12":
            row = candidates[0][1]
            origin = "09:30 New York" if row["session_mode"] == "rth" else "preceding 18:00 New York"
            reference = "VWAP" if row["reference"] == "vwap" else "pivot"
            caption = (f"First 12 chronological 30-minute bins after {origin}, for EMA6–{reference} crossings in {row['cohort']}. "
                       "The denominator remains all eligible days, including no-cross days. Later bins and the explicit no_cross category remain in the saved table; this selected figure is not the complete timing distribution. No profitability claim.")
        sections.append({"id": f"chart-{statistic.lower()}", "kind": "figure", "title": name, "path": f"{artifact}.png",
                         "alt": f"Saved {name.lower()} estimates, with measure units, valid denominator, distinct supporting days and actual coverage.",
                         "caption": caption})
    return assets, sections


def build(stage, *, run_id, published_at=None):
    stage = Path(stage)
    rows = read_csv(stage / SUMMARY)
    require(not (stage / "publications").exists(), "Refusing to overwrite publication sources")
    published_at = published_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    for slug in SLUGS:
        publication_id = identity(run_id, slug)
        directory = stage / "publications" / publication_id
        directory.mkdir(parents=True, exist_ok=False)
        chosen = selected_rows(rows, slug)
        require(bool(chosen), f"No saved rows for {slug}")
        maps, table_sections = [], []
        for rank in range(1, 21):
            statistic = f"S{rank:02d}"
            selected = [(i, r) for i, r in chosen if r.get("statistic_id") == statistic]
            if not selected:
                continue
            projection = f"tables/public-{slug}-{statistic.lower()}.csv"
            public_rows = [projected(r) for _, r in selected]
            require(not (stage / projection).exists(), "Refusing to overwrite public projection")
            write_csv(stage / projection, public_rows)
            table_sections.append(table_section(statistic, public_rows))
            maps.append({"artifact": projection, "sha256": sha(stage / projection), "summary_artifact": SUMMARY,
                         "summary_sha256": sha(stage / SUMMARY), "source_rows": [i for i, _ in selected], "columns": list(PUBLIC_KEYS),
                         "target": f"/sections/{len(table_sections)}/rows"})
        assets, charts = render_charts(stage, slug, chosen)
        scope = ("Pivot-matched RTH comparisons preserve the baseline source, exact quoted delivery contract and full-day quality rules. VWAP comparisons use this same cohort." if slug == "pivot-statistics" else
                 "VWAP-only RTH and VWAP-only full-Globex populations are separate. RTH eligibility does not require a complete late-session Globex tail. No pivot is required; pivot-dependent questions are omitted.")
        sections = [{"id": "scope", "kind": "text", "title": TITLES[slug], "body": scope + "\n\nRequested dates: 2020-01-01–2026-10-30. Actual valid coverage is recorded beside each saved measure. VWAP uses cumulative one-minute HLC3 × volume from 18:00 New York; EMA6 uses completed three-minute closes and the cloud uses completed five-minute closes.\n\nRanked questions appear below in the requested order. Priority forward views use actual EMA6 crossings; original price-cross outcomes remain in the accessible baseline and full private evidence. Whole-sample views preserve all horizons; conditional and calendar forward views emphasize 30 minutes. Public calendars select frequency, movement, recross and first timing measures, with all years and the latest 12 available months; every ranked measure retains full annual/monthly evidence privately."},
                    *table_sections, *charts,
                    {"id": "limits", "kind": "text", "title": "Evidence qualifications", "body": "\n\n".join(LIMITS) + "\n\nThis extends an already observed completed study and is not an untouched holdout. EMA–VWAP crossings use the moving difference, carry strict side through equality, clear unknown comparisons and exclude anchor initialization. EMA recrosses are separate from price reversals. Pivot retests remain fixed-pivot only. Five-observed-session moving-block intervals use 2,000 replicates, seed 20261031; within-day events remain together. Broad conditional slices are exploratory."}]
        require(len(sections) <= 30, "Report section budget")
        download_rows = [(i, r) for i, r in chosen if r.get("period_kind") == "overall" and baseline(r)]
        download_artifact = f"tables/publication-{slug}.csv"
        write_csv(stage / download_artifact, [{key: r.get(key) for key in SOURCE_KEYS} for _, r in download_rows])
        require(len(download_rows) <= 15000 and (stage / download_artifact).stat().st_size <= 4 * 1024 * 1024, "Selected download budget")
        target = f"downloads/{slug}.csv"
        (directory / "downloads").mkdir()
        shutil.copyfile(stage / download_artifact, directory / target)
        download = {"id": "summary", "path": target, "label": TITLES[slug] + " · selected overall saved summaries",
                    "description": "Saved overall baseline rows with original numeric values and denominator fields. Calendar and conditional detail remain in the source evidence.",
                    "population": scope, "units": "Each row declares units. Fraction means a ratio, e.g. 0.42 = 42%; points are unadjusted ES points; time is minutes. Blank is unavailable.",
                    "scope": "Selected descriptive summary evidence only. Populations, periods and event panels overlap and cannot be pooled. No raw market/event ledger or net P&L.",
                    "mediaType": "text/csv", "sha256": sha(directory / target), "rowCount": len(download_rows), "columns": list(SOURCE_KEYS),
                    "source": {"runId": run_id, "artifact": download_artifact, "sha256": sha(stage / download_artifact)}}
        for asset in assets:
            (directory / asset["target"]).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(stage / asset["source"], directory / asset["target"])
        report = {"schemaVersion": "1.1", "id": publication_id, "title": "Verniman Pivot Statistics — ES · " + TITLES[slug],
                  "summary": "Ranked saved ES crossing statistics with distinct pivot-matched, VWAP-only RTH and full-Globex populations. Historical pivot availability is unverified; no profitability claim.",
                  "publishedAt": published_at, "source": {"producer": "sahadeva", "runId": run_id}, "sections": sections, "notes": list(LIMITS), "downloads": [download]}
        write_json(directory / "publication.json", report)
        require((directory / "publication.json").stat().st_size <= 2 * 1024 * 1024, "Filtered report source budget")
        write_json(directory / "source-map.json", {"schema_version": "abacus.study30.ranked-publication-map/v1", "publication_id": publication_id,
                   "source_run_id": run_id, "table_projections": maps, "assets": assets,
                   "download": {"artifact": download_artifact, "sha256": sha(stage / download_artifact), "target": target,
                                "summary_artifact": SUMMARY, "summary_sha256": sha(stage / SUMMARY), "source_rows": [i for i, _ in download_rows], "columns": list(SOURCE_KEYS)}})
    counts = verify(stage, run_id=run_id)
    finalize(stage, run_id, counts)
    return counts


def _pointer(document, pointer):
    value = document
    for part in pointer.strip("/").split("/"):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def verify(stage, *, run_id=None):
    stage = Path(stage)
    rows = read_csv(stage / SUMMARY)
    publications, cells, assets = 0, 0, 0
    for directory in sorted((stage / "publications").iterdir()):
        require(directory.is_dir(), "Unexpected publication entry")
        report = json.loads((directory / "publication.json").read_text())
        mapping = json.loads((directory / "source-map.json").read_text())
        require(report["id"] == directory.name == mapping["publication_id"], "Publication identity mismatch")
        if run_id is not None:
            require(report["source"]["runId"] == run_id == mapping["source_run_id"], "Publication run mismatch")
        for item in mapping["table_projections"]:
            require(item["summary_artifact"] == SUMMARY and item["summary_sha256"] == sha(stage / SUMMARY), "Summary source hash changed")
            require(item["sha256"] == sha(stage / item["artifact"]), "Public projection hash changed")
            expected = [projected(rows[index]) for index in item["source_rows"]]
            require(read_csv(stage / item["artifact"]) == expected == _pointer(report, item["target"]), "Displayed source-cell mismatch")
            cells += len(expected) * len(PUBLIC_KEYS)
        item = mapping["download"]
        require(item["summary_sha256"] == sha(stage / SUMMARY), "Download summary source changed")
        expected = [{key: rows[index].get(key) for key in item["columns"]} for index in item["source_rows"]]
        require(expected == read_csv(stage / item["artifact"]), "Downloaded source-cell mismatch")
        require(sha(stage / item["artifact"]) == item["sha256"] == sha(directory / item["target"]), "Download byte mismatch")
        require(report["downloads"][0]["sha256"] == item["sha256"] and report["downloads"][0]["rowCount"] == len(expected), "Download declaration mismatch")
        cells += len(expected) * len(item["columns"])
        for item in mapping["assets"]:
            require(sha(stage / item["source"]) == item["sha256"] == sha(directory / item["target"]), "Selected asset mismatch")
            inputs = json.loads((stage / item["inputs"]).read_text())
            require(inputs["sha256"] == sha(stage / SUMMARY) and inputs["rows"] == [rows[i] for i in inputs["source_rows"]], "Saved chart source-cell mismatch")
            require(inputs["entries"] == [_chart_entry(row) for row in inputs["rows"]], "Saved chart value mismatch")
            require((stage / item["svg"]).read_text() == _chart_svg(inputs["title"], inputs["entries"]), "Saved chart layout changed")
            receipt = json.loads((stage / item["receipt"]).read_text())
            require(receipt["input_sha256"] == sha(stage / item["inputs"]) and receipt["svg_sha256"] == sha(stage / item["svg"]) and receipt["png_sha256"] == item["sha256"], "Saved chart receipt mismatch")
            assets += 1
        for section in report["sections"]:
            if section["kind"] != "table":
                continue
            require(len(section["rows"]) <= 1500 and len(section["columns"]) <= 12 and len(section["rowFilters"]) <= 3, "Public table budget")
            require(len([r for r in section["rows"] if all(r[f["key"]] == f["defaultValue"] for f in section["rowFilters"])]) <= 100, "Default table budget")
        publications += 1
    require(publications == 2, "Exactly two ranked publication sources required")
    return {"publications": publications, "checked_cells": cells, "checked_assets": assets}


def finalize(stage, run_id, counts):
    stage = Path(stage)
    root = f"runs/{SID}/{run_id}"
    for directory in sorted((stage / "publications").iterdir()):
        report = json.loads((directory / "publication.json").read_text())
        mapping = json.loads((directory / "source-map.json").read_text())
        write_json(directory / "publication-verification.json", {"schema_version": "abacus.study30.ranked-publication-checks/v1", "result": "passed",
                   "publication_id": report["id"], "source_run_id": run_id, "publication_sha256": sha(directory / "publication.json"),
                   "source_map_sha256": sha(directory / "source-map.json"), "counts": counts,
                   "checks": [{"name": "Exact displayed/downloaded saved-cell transfer", "passed": True}, {"name": "Exact saved chart inputs, receipts and selected asset bytes", "passed": True}],
                   "scope": "Presentation transfer integrity; scientific, app and browser verification are separate."})
        sources = {SUMMARY, mapping["download"]["artifact"]}
        sources.update(p["artifact"] for p in mapping["table_projections"])
        for asset in mapping["assets"]:
            sources.update(asset[key] for key in ("source", "inputs", "svg", "receipt"))
        outputs = [p for p in directory.rglob("*") if p.is_file() and p.name != "publication-manifest.json"]
        write_json(directory / "publication-manifest.json", {"publication_id": report["id"], "source_run_id": run_id, "study_id": SID,
                   "source_artifacts": [{"path": f"{root}/{name}", "sha256": sha(stage / name)} for name in sorted(sources)],
                   "outputs": [{"path": f"{root}/{p.relative_to(stage).as_posix()}", "sha256": sha(p)} for p in sorted(outputs)]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = verify(args.stage, run_id=args.run_id) if args.check else build(args.stage, run_id=args.run_id)
    print(json.dumps({"status": "passed", **clean(result)}, sort_keys=True))


if __name__ == "__main__":
    main()
