"""Import byte-identical saved Forex News evidence and present selected cells."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

STUDY = Path(__file__).resolve().parent
ROOT = STUDY.parents[1]
SID = STUDY.name
PUB = "forex-news-ema-20261017-v1"
FINAL = "cross_currency_news_study/extended_year"
SYMBOLS = ["6E", "6B", "6J", "6S", "6C", "6A"]
NAMES = {"6E": "Euro", "6B": "British pound", "6J": "Japanese yen", "6S": "Swiss franc", "6C": "Canadian dollar", "6A": "Australian dollar"}
HORIZONS = [5, 10, 15, 50, 100]
CATEGORIES = ["us_cpi", "us_employment_report", "us_fomc_decision", "us_fomc_press_conference", "us_ism_manufacturing", "us_sp_pmi_flash"]
METRIC_COLUMNS = ["symbol", "horizon_bars", "complete", "average_mfe_ticks", "average_mae_ticks", "average_close_ticks", "favorable_close_percent", "mfe_mae_ratio", "average_close_percent", "median_close_ticks"]
DOWNLOAD_COLUMNS = ["scope", "symbol", "horizon_bars", "signals", "complete", "excluded_or_pending", "long_signals", "short_signals", "favorable_close_percent", "mfe_above_mae_percent", "average_mfe_ticks", "average_mae_ticks", "average_close_ticks", "median_mfe_ticks", "median_mae_ticks", "median_close_ticks", "average_mfe_percent", "average_mae_percent", "average_close_percent", "median_mfe_percent", "median_mae_percent", "median_close_percent", "mfe_mae_ratio"]


def fail(condition, message):
    if not condition:
        raise SystemExit(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def command(argv, cwd=ROOT, environment=None):
    result = {"argv": [str(x) for x in argv], "cwd": str(cwd)}
    if environment:
        result["environment"] = environment
    return result


def scalar(value, column, mode="table"):
    if mode == "csv" or column in {"symbol", "scope", "categories", "entry_month_chicago"}:
        return value
    if value == "":
        return None
    if column in {"signals", "complete", "horizon_bars", "excluded_or_pending", "long_signals", "short_signals"}:
        return int(value)
    number = float(value)
    return number / 100 if column.endswith("_percent") else number


def projection(stage, source, columns, where, target, mode, bindings):
    selected = []
    for original_row, row in enumerate(rows(stage / source)):
        if not all(row[k] == v for k, v in where.items()):
            continue
        output = {key: scalar(row[key], key, mode) for key in columns}
        bindings.append({"target": target, "output_row": len(selected), "source": source,
            "source_sha256": pin(stage / source)["sha256"], "source_row": original_row,
            "selector": where, "mode": mode, "cells": {key: {"source_column": key,
            "original": row[key], "value": output[key], "scale": .01 if mode != "csv" and key.endswith("_percent") else 1} for key in columns}})
        selected.append(output)
    return selected


def column(key):
    info = {"symbol": ("Currency futures", None, None), "horizon_bars": ("Horizon", "bars", 0),
        "complete": ("Complete events", None, 0), "average_mfe_ticks": ("Average MFE", "ticks", 2),
        "average_mae_ticks": ("Average MAE", "ticks", 2), "average_close_ticks": ("Average signed close", "ticks", 2),
        "median_close_ticks": ("Median signed close", "ticks", 2), "favorable_close_percent": ("Favorable close", None, 1),
        "mfe_mae_ratio": ("MFE / MAE", "ratio", 3), "average_close_percent": ("Average signed close", None, 3),
        "categories": ("News category", None, None), "entry_month_chicago": ("Entry month (Chicago)", None, None)}
    label, unit, precision = info[key]
    result = {"key": key, "label": label}
    if precision is not None:
        result.update({"format": "percent" if key.endswith("_percent") else "number", "precision": precision})
    if unit:
        result["unit"] = unit
    return result


def render(report, dest):
    esc = html.escape
    body, md, toc = [], ["# "+report["title"], report["summary"]], []
    for sec in report["sections"]:
        toc.append(f'<a href="#{sec["id"]}">{esc(sec["title"])}</a>')
        md.append("## "+sec["title"])
        if sec["kind"] == "text":
            content = "".join("<p>"+esc(p)+"</p>" for p in sec["body"].split("\n\n"))
            md.append(sec["body"])
        elif sec["kind"] == "metrics":
            content = '<div class="metrics">'+"".join(f'<div><strong>{item["value"]}</strong><span>{esc(item["label"])}</span><small>{esc(item.get("note", ""))}</small></div>' for item in sec["items"])+"</div>"
        elif sec["kind"] == "figure":
            content = f'<figure><a href="{sec["path"]}"><img src="{sec["path"]}" alt="{esc(sec["alt"])}"></a><figcaption>{esc(sec["caption"])}</figcaption></figure>'
            md.append(f'![{sec["alt"]}]({sec["path"]})\n\n{sec["caption"]}')
        else:
            selected = sec["rows"]
            for filt in sec.get("rowFilters", []):
                if "defaultValue" in filt:
                    selected = [r for r in selected if r[filt["key"]] == filt["defaultValue"]]
            description = sec.get("description", "")
            if sec.get("rowFilters"):
                description += " Offline view shows authored default rows. The published report can select all saved rows."
            head = "".join("<th>"+esc(c["label"])+"</th>" for c in sec["columns"])
            cells = []
            for row in selected:
                values = []
                for col in sec["columns"]:
                    val = row[col["key"]]
                    if val is None:
                        txt = "Not available"
                    elif col.get("format"):
                        txt = f'{val * (100 if col["format"] == "percent" else 1):.{col.get("precision", 2)}f}'+("%" if col["format"] == "percent" else "")
                    else:
                        txt = str(val)
                    values.append("<td>"+esc(txt)+"</td>")
                cells.append("<tr>"+"".join(values)+"</tr>")
            content = f'<p>{esc(description)}</p><div class="table" tabindex="0"><table><thead><tr>{head}</tr></thead><tbody>{"".join(cells)}</tbody></table></div>'+"".join("<p class=note>"+esc(n)+"</p>" for n in sec.get("notes", []))
            md.append(description+"\n\nSee publication.json for exact saved rows and filters.")
        body.append(f'<section id="{sec["id"]}"><h2>{esc(sec["title"])}</h2>{content}</section>')
    downloads = "".join(f'<li><a href="{d["path"]}" download>{esc(d["label"])}</a> — {esc(d["scope"])}</li>' for d in report["downloads"])
    template = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__ · Abacus</title><style>
*{box-sizing:border-box}body{margin:0;background:#f7faf9;color:#193b49;font:17px/1.65 system-ui,sans-serif}header,main,nav{max-width:1180px;margin:auto;padding:24px 30px}header{padding-top:60px}header .tag{font-size:13px;letter-spacing:.13em;color:#19766f;font-weight:700}h1{font-size:clamp(32px,5vw,55px);line-height:1.12;max-width:960px}header p{font-size:20px;max-width:900px;color:#526c78}nav{display:flex;flex-wrap:wrap;gap:10px 22px;border-block:1px solid #d4e2e1;font-size:13px}a{color:#116c72;text-underline-offset:4px}section{padding:25px 0;border-bottom:1px solid #d4e2e1}h2{font-size:26px;line-height:1.25}p{max-width:1000px}img{width:100%;height:auto;display:block;border:1px solid #d6e3e1;border-radius:14px}figure{margin:20px 0}figcaption,.note{color:#536e7a;font-size:14px}.table{overflow:auto;background:white;border:1px solid #d4e2e1;border-radius:12px}table{border-collapse:collapse;font-size:13px;white-space:nowrap;width:100%}th,td{padding:12px;text-align:left;border-bottom:1px solid #e6edec}th{background:#eef5f3}td:not(:first-child){font-variant-numeric:tabular-nums}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}.metrics>div{background:#eaf3ef;padding:22px;border-radius:12px}.metrics strong{display:block;font-size:32px}.metrics span,.metrics small{display:block}.metrics small{font-size:12px;color:#526c78}a:focus-visible,.table:focus-visible{outline:3px solid #cb9b36;outline-offset:4px}@media(max-width:700px){header,main,nav{padding-inline:18px}header{padding-top:30px}.metrics{grid-template-columns:repeat(2,1fr)}h2{font-size:23px}}
</style><header><div class=tag>ABACUS / FOREX NEWS / IMPORTED SAVED EVIDENCE</div><h1>__TITLE__</h1><p>__SUMMARY__</p></header><nav aria-label="Report contents">__TOC__</nav><main>__BODY__<section><h2>Selected summary downloads</h2><ul>__DOWNLOADS__</ul></section><p class=note>__NOTES__</p></main></html>'''
    for key, val in {"__TITLE__": esc(report["title"]), "__SUMMARY__": esc(report["summary"]), "__TOC__": "".join(toc), "__BODY__": "".join(body), "__DOWNLOADS__": downloads, "__NOTES__": esc(" ".join(report["notes"]))}.items():
        template = template.replace(key, val)
    (dest / "report.html").write_text(template, encoding="utf-8")
    (dest / "report.md").write_text("\n\n".join(md)+"\n", encoding="utf-8")


def prepare(args, stage):
    fail(not stage.exists(), "Refusing to replace an existing stage; use a fresh run ID.")
    source = args.source.resolve()
    fail((source / FINAL / "report.txt").is_file(), "Missing explicitly selected final report.")
    inventory, retained = [], []
    for original in sorted(source.rglob("*")):
        if not original.is_file():
            continue
        fail(not original.is_symlink(), "Source symlinks are not imported.")
        rel = original.relative_to(source).as_posix()
        keep = original.suffix in {".py", ".pine", ".json", ".md", ".txt", ".csv"} and original.stat().st_size < 1_200_000 and not original.name.startswith(("reconstructed_", "native_6", "prices_", "native_news_ema_move"))
        inventory.append({"source_path": rel, "locator": str(original), **pin(original), "retained": keep})
        if keep:
            retained.append((original, rel))
    fail(all(next(item for item in inventory if item["source_path"] == f"{FINAL}/{name}")["retained"] for name in ["report.txt", "summary.json", "validation.json", "reconstruction_audit.json", "events.csv", "horizons.csv", "overall.csv", "by_category.csv", "monthly.csv"]), "Final evidence must be retained.")
    source_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    source_status = subprocess.check_output(["git", "status", "--short", "--", "forex_news"], cwd=source.parent, text=True)
    stage.mkdir(parents=True)
    for original, rel in retained:
        target = stage / "source-original" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        fail(pin(original) == pin(target), "Copy changed source bytes.")
    for name in ["overall.csv", "by_category.csv", "monthly.csv", "events.csv", "horizons.csv"]:
        target = stage / "tables" / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(stage / "source-original" / FINAL / name, target)
    shutil.copyfile(stage / "source-original/cross_currency_news_study/native57/overall.csv", stage / "tables/native57-overall.csv")
    for name in ["summary.json", "validation.json", "reconstruction_audit.json"]:
        shutil.copyfile(stage / "source-original" / FINAL / name, stage / name)
    shutil.copyfile(stage / "source-original" / FINAL / "report.txt", stage / "source-report.txt")
    write(stage / "import-manifest.json", {"schema_version": "forex25-saved-evidence-import/v1", "source_project": "tv-indicators", "source_revision": source_revision, "source_status": source_status, "imported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "historical_execution_time": None, "historical_execution_time_note": "Not established; import time does not date the original research execution.", "source_files": inventory, "scope": "Copy and presentation only; original scripts and original numerical validation not executed."})
    lock = {"schema_version": "forex25-import-inputs/v1", "study_id": SID, "source_project_revision": source_revision, "publication_root": ".", "sources": inventory, "source_data_status": "Retained final saved evidence; large original histories remain external declared locators.", "numerical_revalidation": False}
    write(stage / "inputs.lock.json", lock)
    write(STUDY / "inputs.lock.json", lock)
    (stage / "source-project-status.txt").write_text(source_status, encoding="utf-8")
    subprocess.run(["git", "diff", "--binary", "--", "forex_news"], cwd=source.parent, stdout=(stage / "source-project-dirty.patch").open("w"), check=True)
    write(stage / "config.json", {"protocol": "saved-evidence-import-1", "analysis": "extended_year", "scope": "common_events", "symbols": SYMBOLS, "horizons_bars": HORIZONS, "no_numerical_rerun": True, "date_is_import_date": True, "entry": "15m completed bar ending at release; EMA20 vs EMA50 on that bar", "first_measured_candle": "bar opening at release, source bars[i+1:i+1+h]", "excluded_public_content": ["event ledgers", "raw and reconstructed histories", "private source paths", "indicator source code"], "exclusions": "Source common_events selection preserved; no new inclusion/exclusion rule."})
    for name in ["README.md", "plan.md", "notes.md", "study.yaml", "study.json", "import_report.py", "render_figures.py"]:
        target = stage / "producer" / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(STUDY / name, target)
    for name in ["uv.lock", "apps/narada/package-lock.json"]:
        shutil.copyfile(ROOT / name, stage / Path(name).name)
    (stage / "code-status.txt").write_text(subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True), encoding="utf-8")
    bindings, tables = [], []
    specs = [("h5-overview", "H5 overview: same 64 events, six different outcomes", "tables/overall.csv", {"scope": "common_events", "horizon_bars": "5"}, METRIC_COLUMNS, []),
        ("horizon-detail", "Inspect each saved horizon", "tables/overall.csv", {"scope": "common_events"}, METRIC_COLUMNS, [{"key": "symbol", "label": "Currency futures", "defaultValue": "6E"}]),
        ("category-detail", "Inspect the news categories", "tables/by_category.csv", {"scope": "common_events"}, ["categories", *METRIC_COLUMNS], [{"key": "symbol", "label": "Currency futures", "defaultValue": "6E"}, {"key": "horizon_bars", "label": "Horizon (bars)", "defaultValue": 5}]),
        ("monthly-detail", "Inspect monthly consistency", "tables/monthly.csv", {"scope": "common_events"}, ["entry_month_chicago", *METRIC_COLUMNS], [{"key": "symbol", "label": "Currency futures", "defaultValue": "6E"}, {"key": "horizon_bars", "label": "Horizon (bars)", "defaultValue": 5}])]
    for ident, title, src, where, cols, filters in specs:
        sec = {"id": ident, "title": title, "kind": "table", "columns": [column(k) for k in cols], "rows": projection(stage, src, cols, where, ident, "table", bindings), "description": "Exact saved common-event summary rows. H counts following 15-minute chart candles; positive signed close favors the frozen entry direction.", "notes": ["MFE and MAE are directional high/low excursions; their ratio is not profit factor. Ticks use each instrument's specification and are not dollar returns.", "Favorable close means signed horizon close above zero. No fees, slippage, stops, targets or uncertainty intervals are modeled.", "Category and monthly groups are small, exploratory and dependent. Month follows America/Chicago. Category keys match the saved source labels."], "referenceIds": ["overall" if "overall" in src else "category" if "category" in src else "monthly"]}
        if filters:
            sec["rowFilters"] = filters
        tables.append(sec)
    downloads = []
    descriptions = [("overall", "tables/overall.csv", "All-currency horizon summary", "30 final common-event symbol/horizon rows", None),
        ("category", "tables/by_category.csv", "News-category summary", "180 final common-event symbol/category/horizon rows", "categories"),
        ("monthly", "tables/monthly.csv", "Monthly summary", "390 final common-event symbol/month/horizon rows", "entry_month_chicago"),
        ("native57", "tables/native57-overall.csv", "Earlier native57 context", "30 earlier native57 common-event symbol/horizon rows; a different shorter cohort", None)]
    for ident, src, label, scope, extra in descriptions:
        cols = DOWNLOAD_COLUMNS if not extra else [*DOWNLOAD_COLUMNS, extra]
        path = f"downloads/{ident}-summary.csv"
        projected = projection(stage, src, cols, {"scope": "common_events"}, path, "csv", bindings)
        dest = stage / path
        dest.parent.mkdir(exist_ok=True)
        with dest.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=cols, lineterminator="\n")
            writer.writeheader(); writer.writerows(projected)
        downloads.append({"id": ident, "path": path, "label": label, "description": "Selected saved summary columns with original CSV strings and blank meanings. No event ledger or history data.", "population": "Earlier native57 common timestamp cohort, not pooled with final64." if ident == "native57" else "Final reconstructed common64 U.S. release cohort, six currency futures.", "units": "Ticks: own instrument outright minimum increment. Fields ending _percent are source percentage points, not ratios; blank fields remain unavailable. MFE/MAE ratio is not profit factor.", "scope": scope, "mediaType": "text/csv", "columns": cols, "rowCount": len(projected), "sha256": pin(dest)["sha256"], "source": {"runId": args.run_id, "artifact": src, "sha256": pin(stage / src)["sha256"]}})
    chart_rows = projection(stage, "tables/overall.csv", METRIC_COLUMNS, {"scope": "common_events"}, "chart-overall", "csv", bindings)
    cat_rows = projection(stage, "tables/by_category.csv", ["symbol", "categories", "average_close_percent"], {"scope": "common_events", "horizon_bars": "5"}, "chart-category", "csv", bindings)
    lookup = {(r["symbol"], int(r["horizon_bars"])): r for r in chart_rows}
    cat_lookup = {(r["symbol"], r["categories"]): r for r in cat_rows}
    chart = {"horizons": HORIZONS, "labels": [f"{s} · {NAMES[s]}" for s in SYMBOLS], "close_series": [{"label": f"{s} · {NAMES[s]}", "values": [float(lookup[s,h]["average_close_percent"]) for h in HORIZONS]} for s in SYMBOLS], "h5_mfe": [float(lookup[s,5]["average_mfe_ticks"]) for s in SYMBOLS], "h5_mae": [float(lookup[s,5]["average_mae_ticks"]) for s in SYMBOLS], "category_labels": ["CPI", "Employment", "FOMC\ndecision", "FOMC\nconference", "ISM mfg.", "Flash PMI"], "category_values": [[float(cat_lookup[s,c]["average_close_percent"]) for c in CATEGORIES] for s in SYMBOLS]}
    write(stage / "chart-spec.json", chart)
    figure_cmd = [str(args.figure_python), str(STUDY / "render_figures.py"), str(stage)]
    subprocess.run(figure_cmd, check=True, cwd=ROOT)
    result = subprocess.run([str(args.figure_python), "-m", "pip", "freeze", "--path", os.environ.get("PYTHONPATH", "")], capture_output=True, text=True)
    (stage / "figure-packages.txt").write_text(result.stdout+result.stderr, encoding="utf-8")
    summary, validation = read(stage / "summary.json"), read(stage / "validation.json")
    references = [{"id": ident, "kind": "saved-artifact", "label": label, "title": label, "runId": args.run_id, "artifact": artifact, "sha256": pin(stage / artifact)["sha256"]} for ident, label, artifact in [("overall", "Final common-event horizon summaries", "tables/overall.csv"), ("category", "Final news-category summaries", "tables/by_category.csv"), ("monthly", "Final monthly summaries", "tables/monthly.csv"), ("summary", "Original final analysis summary and definitions", "summary.json"), ("validation", "Original saved validation receipt, imported", "validation.json"), ("reconstruction", "Original reconstruction audit, imported", "reconstruction_audit.json"), ("native57", "Earlier native57 summaries, separate cohort", "tables/native57-overall.csv")]]
    def text(ident, title, body, refs):
        return {"id": ident, "title": title, "kind": "text", "body": body, "referenceIds": refs}
    report = {"schemaVersion": "1.1", "id": args.publication_id, "title": "Forex News: does the pre-release EMA direction carry through?", "summary": "Across 64 shared U.S. release timestamps, six currency futures show different directional paths. Swiss franc, euro and Canadian dollar have favorable H5 averages; Australian dollar is negative and longer horizons weaken several results. Imported descriptive evidence from a reconstructed year; costs and executable fills were not tested.", "publishedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source": {"producer": "sahadeva", "runId": args.run_id}, "sections": [
        text("reading-the-result", "A mixed result, not a general news-trading edge", "The saved final analysis follows EMA20/50 direction immediately before scheduled U.S. news. At H5, Swiss franc (6S), euro (6E), Canadian dollar (6C) and British pound (6B) have positive average signed closes. Japanese yen (6J) is slightly negative; Australian dollar (6A) is negative at every saved horizon. The horizon and category views preserve these contrary outcomes.\n\nThese are descriptive price paths around selected news timestamps. Favorable excursions are not realized profits, the MFE/MAE ratio is not profit factor, and these results do not establish event causality or future profitability. The Abacus work imported saved evidence and checked presentation transfers; it did not rerun the research.", ["overall", "summary"]),
        {"id": "sample", "title": "The same event clock across six currencies", "kind": "metrics", "items": [{"label": "Currency futures", "value": len(summary["symbols"]), "format": "number", "precision": 0, "note": "6E, 6B, 6J, 6S, 6C, 6A"}, {"label": "Shared release timestamps", "value": summary["comparison"]["common_signal_timestamps"], "format": "number", "precision": 0, "note": "October 24, 2025–October 14, 2026"}, {"label": "Saved horizons", "value": len(summary["comparison"]["common_complete_count_by_horizon"]), "format": "number", "precision": 0, "note": "H5, H10, H15, H50, H100"}, {"label": "Complete event/horizon rows", "value": 1920, "format": "number", "precision": 0, "note": "Original saved validation declares all complete."}], "referenceIds": ["summary", "validation"]},
        text("method", "One precise entry convention", "The 15-minute candle that closes exactly at the scheduled release supplies both the benchmark entry close and EMA direction: EMA20 above EMA50 means long; EMA20 below EMA50 means short. The side is then frozen. The next candle—the candle opening at the release—is the first measured candle. The entry candle's earlier high and low are excluded. The retained source code uses bars[i+1:i+1+h].\n\nH5, H10, H15, H50 and H100 count actual following chart candles, rather than fixed wall-clock intervals. H5 is 75 trading minutes when bars are contiguous; exchange breaks and weekends can extend elapsed time. Independent observations do not truncate one another. Simultaneous components count once per timestamp. Monthly rows use the release's America/Chicago month.\n\nMFE is the largest favorable price excursion from the entry benchmark; MAE is the largest adverse excursion. Signed close is the directional change at the last candle close; positive favors the frozen side. Each percentage distance is divided by its own entry price before averaging. A favorable-close percentage is a frequency, not a net trading win rate.", ["summary"]),
        tables[0],
        {"id": "excursions", "title": "H5: opportunity and risk in the same window", "kind": "figure", "path": "figures/h5-excursions.png", "alt": "Paired H5 average MFE and MAE bars for six futures. Favorable excursion exceeds adverse in 6E, 6B, 6S and 6C; adverse exceeds favorable in 6J and 6A.", "caption": "Exact saved average excursions for the common 64-event cohort at H5. Values use each instrument's own outright futures ticks, so lengths compare favorable versus adverse paths within an instrument; they do not rank dollar returns across currencies. No uncertainty intervals or executable exit rule were supplied.", "referenceIds": ["overall"]},
        {"id": "horizon-chart", "title": "Longer horizons do not guarantee a better close", "kind": "figure", "path": "figures/signed-close-horizons.png", "alt": "Six lines of saved average signed close as percentage of entry across five horizons. Australian dollar stays negative; several favorable H5 results weaken toward H100.", "caption": "Exact saved average signed close as a percentage of each entry price, on the same 64 timestamps for every currency and horizon. Horizon positions are categorical. These are signed benchmark price changes, without costs, portfolio sizing or confidence intervals; they are not account returns.", "referenceIds": ["overall"]},
        tables[1],
        text("category-reading", "The release type matters—and groups are small", "The source's six U.S. groups are CPI, the employment report, FOMC decision/projections, FOMC press conference, ISM manufacturing and flash PMI. They are U.S. releases applied to every supplied currency, rather than domestic-release studies for each country.\n\nAt H5, every currency's flash-PMI average signed close is negative. FOMC decisions are favorable on average in several currencies but adverse in 6J and 6A. Decisions and conferences have only eight observations each; the other selected category groups have twelve each. These exploratory contrasts have no multiple-comparison adjustment, independent holdout or uncertainty intervals in the supplied evidence. Decision and conference windows can overlap.", ["category", "summary"]),
        {"id": "category-chart", "title": "H5 news-category map", "kind": "figure", "path": "figures/h5-news-categories.png", "alt": "Heatmap of average signed-close percentages by currency and six news categories at H5, with signed values in every cell. All flash-PMI cells are negative.", "caption": "Saved common-event H5 category averages, normalized by each event's entry price. Both color and signed labels show direction. FOMC groups have eight events each; CPI, employment, ISM and flash PMI have twelve each. Small, dependent exploratory groups do not establish reliable category effects.", "referenceIds": ["category"]},
        tables[2], tables[3],
        text("reconstruction", "A reconstructed year with retained native-subset context", "The final year continues older native EMA20/50 seeds through merged native OHLC; overlap prices anchor constant adjustment offsets. The reconstructed CSVs are analytical inputs, rather than direct full-year native indicator exports. EMA values can differ from later exports even when selected directions agree.\n\nThe original saved validation states that all 1,920 event/horizon rows are complete, that the earlier native57 subset's 5,130 selected price-value comparisons have zero maximum difference, and that all its directions are unchanged. It also records agreement with an earlier full-year 6E aggregate check. These original receipts are retained as imported evidence; Abacus verified their bytes and relevant transfer identities without repeating those numerical checks.\n\nThe earlier native57 summary download remains a separate shorter cohort. It must not be pooled with or substituted for the final common64 results. Original indicator/native checks are retained privately as context; native subset agreement does not independently validate the reconstructed year's other observations.", ["validation", "reconstruction", "native57"]),
        text("limits", "What the evidence does and does not support", "No commissions, bid/ask spreads, slippage, financing, targets, stops or contract sizing were modeled. The pre-news close and back-adjusted continuous prices are analytical benchmarks; they do not guarantee a fill immediately before or at a news release. Tick distances are not dollar P&L. MFE/MAE is a ratio of average excursions, not profit factor.\n\nThe calendar is an audited corrected historical schedule, rather than an as-announced historical vintage. Event selection and available history are retrospective. Shared macro shocks link currencies; overlapping windows link observations. The 64 timestamps are not 384 independent macro experiments, and category/month rows should not be treated as independent confirmations.\n\nThe retained source provides no confidence intervals, prespecified holdout, event-causality design or cost-tested execution strategy. Positive sample averages therefore remain candidates for further investigation. Negative and inconclusive currency/category/horizon outcomes are part of the finding, not exclusions. The practical next step would require a separate frozen protocol, point-in-time timing and executable cost assumptions.", ["summary", "overall", "category"])
        ], "downloads": downloads, "references": references, "notes": ["Prepared in Abacus on October 17, 2026 from the saved final tv-indicators analysis. The import date is not the original research execution date.", "Original report wording is retained unchanged privately. Authored explanations clarify timing and units against retained code; numerical estimates are selected from saved CSV cells.", "Percentage values in CSVs retain source percentage-point units. Narada percent-formatted JSON divides those values by 100; the figure percent axes display original source values.", "Saved source category keys: us_cpi; us_employment_report; us_fomc_decision; us_fomc_press_conference; us_ism_manufacturing; us_sp_pmi_flash."]}
    write(stage / "publication.json", report)
    metric_bindings = [{"section": "sample", "item": 0, "source": "summary.json", "pointer": ["symbols"], "operation": "len", "value": 6}, {"section": "sample", "item": 1, "source": "summary.json", "pointer": ["comparison", "common_signal_timestamps"], "operation": "copy", "value": 64}, {"section": "sample", "item": 2, "source": "summary.json", "pointer": ["comparison", "common_complete_count_by_horizon"], "operation": "len", "value": 5}, {"section": "sample", "item": 3, "source": "validation.json", "pointer": ["all_1920_event_horizon_rows_complete"], "operation": "declared_row_count", "value": 1920}]
    write(stage / "source-map.json", {"schema_version": "forex25-saved-cells/v1", "study_id": SID, "run_id": args.run_id, "publication_id": args.publication_id, "source_row_base": 0, "bindings": bindings, "metrics": metric_bindings, "figure_inputs": {"chart-overall": "chart-spec.json close_series/h5_mfe/h5_mae; fixed SYMBOLS/HORIZONS order", "chart-category": "chart-spec.json category_values; fixed SYMBOLS/CATEGORIES order"}, "claims": [{"section": s["id"], "sources": s.get("referenceIds", []), "status": "authored explanation of saved evidence; numerical estimates not recalculated"} for s in report["sections"] if s["kind"] == "text"], "timing_source": "source-original/cross_currency_news_study/analyze.py: event == bar time + BAR; window = bars[i+1:i+1+h]", "presentation_units": "Table _percent fields divide source percentage points by 100; selected CSV strings and figure percent values are unchanged."})
    render(report, stage)
    write(stage / "advice.json", {"status": "descriptive_imported_evidence", "strategy_adopted": False, "reason": "Mixed outcomes without execution/cost testing, holdout or independent revalidation."})
    (stage / "advice.md").write_text("# Dated interpretation — 2026-10-17\n\nPreserve the mixed currency/category/horizon results as descriptive imported evidence. No strategy is adopted. The final report's costs, reconstruction, dependence and causality qualifications govern every saved table. Further empirical work needs a separate frozen protocol; no numerical rerun was performed for this import.\n", encoding="utf-8")
    write(stage / "commands.json", [command([sys.executable, *sys.argv], environment={"PYTHONPATH": os.environ.get("PYTHONPATH", "")}), command(figure_cmd, environment={"PYTHONPATH": os.environ.get("PYTHONPATH", "")})])
    # Confirm the original project bytes stayed fixed across the entire read/copy operation.
    fail(all(pin(Path(item["locator"])) == {k: item[k] for k in ["bytes", "sha256"]} for item in inventory), "Original source changed during import.")
    check_cells(stage)
    print(f"Prepared {stage.relative_to(ROOT)}; original bytes and mapped transfers passed.")


def check_cells(bundle):
    report, mapping = read(bundle / "publication.json"), read(bundle / "source-map.json")
    sections = {s["id"]: s for s in report["sections"]}
    cache, count = {}, 0
    for binding in mapping["bindings"]:
        source = binding["source"]
        fail(pin(bundle / source)["sha256"] == binding["source_sha256"], "Mapped source hash changed.")
        if source not in cache:
            cache[source] = rows(bundle / source)
        original = cache[source][binding["source_row"]]
        fail(all(original[k] == v for k,v in binding["selector"].items()), "Mapped source selector changed.")
        if binding["target"].startswith("downloads/"):
            target = binding["target"]
            if target not in cache:
                cache[target] = rows(bundle / target)
            output = cache[target][binding["output_row"]]
        elif binding["target"].startswith("chart-"):
            output = {k: scalar(original[k], k, "csv") for k in binding["cells"]}
        else:
            output = sections[binding["target"]]["rows"][binding["output_row"]]
        for key, cell in binding["cells"].items():
            fail(original[cell["source_column"]] == cell["original"], "Original cell mismatch.")
            expected = scalar(cell["original"], cell["source_column"], binding["mode"])
            fail(expected == cell["value"] == output[key], "Transferred cell mismatch.")
            count += 1
    for metric in mapping["metrics"]:
        value = read(bundle / metric["source"])
        for key in metric["pointer"]:
            value = value[key]
        if metric["operation"] == "len":
            value = len(value)
        elif metric["operation"] == "declared_row_count":
            fail(value is True, "Original completeness declaration is not true.")
            value = len(cache.get("tables/horizons.csv", rows(bundle / "tables/horizons.csv")))
        fail(value == metric["value"] == sections[metric["section"]]["items"][metric["item"]]["value"], "Metric source mismatch.")
    chart = read(bundle / "chart-spec.json")
    overall = {(r["symbol"],int(r["horizon_bars"])):r for r in rows(bundle / "tables/overall.csv") if r["scope"] == "common_events"}
    category = {(r["symbol"],r["categories"]):r for r in rows(bundle / "tables/by_category.csv") if r["scope"] == "common_events" and r["horizon_bars"] == "5"}
    for index,symbol in enumerate(SYMBOLS):
        fail(chart["close_series"][index]["values"] == [float(overall[symbol,h]["average_close_percent"]) for h in HORIZONS], "Figure horizon inputs differ.")
        for name, col in [("h5_mfe", "average_mfe_ticks"), ("h5_mae", "average_mae_ticks")]:
            fail(chart[name][index] == float(overall[symbol,5][col]), "Figure H5 inputs differ.")
        fail(chart["category_values"][index] == [float(category[symbol,c]["average_close_percent"]) for c in CATEGORIES], "Figure category inputs differ.")
    for item in report["downloads"]:
        fail(pin(bundle / item["path"])["sha256"] == item["sha256"], "Download bytes changed.")
        fail(pin(bundle / item["source"]["artifact"])["sha256"] == item["source"]["sha256"], "Download source bytes changed.")
        with (bundle / item["path"]).open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fail(reader.fieldnames == item["columns"] and len(list(reader)) == item["rowCount"], "Download shape differs.")
    validation = read(bundle / "validation.json")
    fail(validation["summary_sha256"] == pin(bundle / "summary.json")["sha256"], "Original validation summary pin differs.")
    fail(read(bundle / "summary.json")["history_reconstruction"]["audit_sha256"] == pin(bundle / "reconstruction_audit.json")["sha256"], "Original reconstruction-audit pin differs.")
    for ref in report["references"]:
        fail(pin(bundle / ref["artifact"])["sha256"] == ref["sha256"], "Saved reference hash differs.")
    originals = read(bundle / "import-manifest.json")["source_files"]
    for item in originals:
        if item["retained"]:
            fail(pin(bundle / "source-original" / item["source_path"])["sha256"] == item["sha256"], "Retained original source bytes differ.")
    fail((bundle / "source-report.txt").read_bytes() == (bundle / "source-original" / FINAL / "report.txt").read_bytes(), "Original report wording changed.")
    return count


def finalize(args, stage):
    fail(not (stage / "manifest.json").exists(), "Refusing to replace a finalized manifest.")
    count = check_cells(stage)
    report = read(stage / "publication.json")
    dry = [str(args.node), "scripts/publish.mjs", "--report", str(stage / "publication.json"), "--dry-run"]
    result = subprocess.run(dry, cwd=ROOT / "apps/narada", capture_output=True, text=True)
    (stage / "publisher-dry-run.log").write_text(result.stdout+result.stderr, encoding="utf-8")
    fail(result.returncode == 0, result.stderr or result.stdout)
    check_record = {"schema_version": "forex25-publication-checks/v1", "result": "passed", "scope": "Byte-identical retained source, original source validation pins, exact saved-cell projections, figure inputs, selected downloads and Narada dry-run. No numerical research/native checks rerun.", "checks": [{"name": "retained source byte identities", "passed": True}, {"name": f"{count} mapped source cells and four metric bindings", "passed": True}, {"name": "chart inputs equal exact saved values", "passed": True}, {"name": "selected CSV headers/row counts/content and source hashes", "passed": True}, {"name": "Narada source-contract dry-run", "passed": True}], "publication_sha256": pin(stage / "publication.json")["sha256"], "source_map_sha256": pin(stage / "source-map.json")["sha256"]}
    write(stage / "publication-verification.json", check_record)
    write(stage / "checks.json", [{"name": "import and presentation integrity", "status": "passed", "record": "publication-verification.json"}, {"name": "historical numerical reconstruction and validation", "status": "not_run", "reason": "Saved receipts retained; not repeated for this import."}, {"name": "native TradingView compilation/runtime", "status": "not_run", "reason": "Source-project native checks retained as historical context; not repeated."}])
    commands = read(stage / "commands.json")
    commands.extend([command([sys.executable, *sys.argv]), command(dry, ROOT / "apps/narada")])
    write(stage / "commands.json", commands)
    locator = f"runs/{SID}/{args.run_id}"
    assets = [s["path"] for s in report["sections"] if s["kind"] == "figure"]+[d["path"] for d in report["downloads"]]
    source_names = ["summary.json", "validation.json", "reconstruction_audit.json", "source-report.txt", *["tables/"+name for name in ["overall.csv", "by_category.csv", "monthly.csv", "events.csv", "horizons.csv", "native57-overall.csv"]]]
    output_names = ["publication.json", "source-map.json", "publication-verification.json", "chart-spec.json", *assets]
    write(stage / "publication-manifest.json", {"publication_id": report["id"], "source_run_id": args.run_id, "study_id": SID, "source_artifacts": [{"path": f"{locator}/{name}", **pin(stage / name)} for name in source_names], "outputs": [{"path": f"{locator}/{name}", **pin(stage / name)} for name in output_names]})
    files = sorted(p for p in stage.rglob("*") if p.is_file() and p.name != "manifest.json")
    external = [{"id": f"original-{i}", "locator": item["locator"], "bytes": item["bytes"], "sha256": item["sha256"]} for i,item in enumerate(read(stage / "import-manifest.json")["source_files"]) if not item["retained"]]
    write(stage / "manifest.json", {"contract": "abacus.evidence/v1", "bundle_kind": "research", "study_id": SID, "run_id": args.run_id, "inventory_scope": "declared_artifacts", "results": {"kind": "quantitative", "state": "computed", "reason": "Original saved descriptive calculations imported, not recomputed or scientifically revalidated by Abacus.", "artifacts": ["summary.json", "tables/overall.csv", "tables/by_category.csv", "tables/monthly.csv", "tables/events.csv", "tables/horizons.csv"]}, "provenance": {"settings": "config.json", "input_lock": "inputs.lock.json", "exclusions": "config.json", "commands": "commands.json", "checks": "checks.json", "environment_lock": "uv.lock", "code": {"revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "dirty": bool((stage / "code-status.txt").read_text()), "status": "code-status.txt", "source_snapshot": {"paths": ["producer/import_report.py", "producer/render_figures.py", "producer/plan.md", "producer/study.yaml", "source-original/cross_currency_news_study/analyze.py", "source-original/cross_currency_news_study/extend_history.py", "source-original/news_ema_move.pine", "source-original/forex_news.pine"], "scope": "Exact import/presentation producers and original numerical/indicator source; relevant original dirty/untracked bytes retained under source-original with source Git identity. This does not prove historical dependency completeness or installed lock agreement."}}}, "artifacts": [{"path": p.relative_to(stage).as_posix(), **pin(p)} for p in files], "external_artifacts": external})
    verify_bundle(stage)
    print(f"Finalized stage: {count} mapped source cells passed; ready for independent review before seal.")


def verify_bundle(bundle):
    check_cells(bundle)
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check-evidence-bundle.py"), str(bundle)], cwd=ROOT)
    fail(result.returncode == 0, "Declared evidence bundle verification failed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "finalize", "seal", "check"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--publication-id", default=PUB)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--figure-python", type=Path)
    parser.add_argument("--node", type=Path, default=Path("node"))
    args = parser.parse_args()
    fail(re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id), "Unsafe run ID.")
    stage = ROOT / "work" / SID / args.run_id
    dest = ROOT / "runs" / SID / args.run_id
    if args.action == "prepare":
        fail(args.source and args.figure_python, "Preparation requires source and plotting Python.")
        prepare(args, stage)
    elif args.action == "finalize":
        finalize(args, stage)
    elif args.action == "check":
        verify_bundle(dest if dest.exists() else stage)
    else:
        fail(not dest.exists(), "Refusing to overwrite a sealed run.")
        verify_bundle(stage)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, dest)
        verify_bundle(dest)
        print(f"Sealed {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
